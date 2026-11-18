"""Grading one checkpoint of a trajectory: extraction, the app under a fake clock, setups, probe runs, judgment.

Design: "Graders", "Grading protocol", and "The harness" in the notebook's design.md.

1. **Export.** The arm's commit is copied out of its workspace into a checkpoint volume, beside the grading tools.
2. **Extraction.** A session reads the checkout, runs the service, and writes an interface reference (how to call
   things, never what they are for) and a start spec for the control server.
3. **App containers.** Each runs the control server (grading/control.py), which starts the service under a fake
   clock and is the graders' only way in. Several workers can run at once, each on its own data location.
4. **Setups.** One session loads every named setup through the reference and saves each as a snapshot; probes
   restore them.
5. **Execution.** Probe batches run in sessions that can reach the service only through `gt`, in a container
   without the source. The control server writes the execution log.
6. **Judgment.** A separate session per batch compares each probe's expected observation with its log.

An item is met when every one of its probes is met; "not met" wins over "couldn't exercise", which wins over
"missing": a grader error a rerun didn't resolve (Rust grading), which leaves the item out of the items-met share.
"""

from __future__ import annotations

import json
import re
import secrets
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from . import executor

HERE = Path(__file__).resolve().parent.parent
PROMPTS = HERE / "prompts"
TOOLS = HERE / "grading"
VERDICTS = ("met", "not met", "couldn't exercise")
MISSING = "missing"  # a probe the grader couldn't exercise even on a rerun: no verdict on the build, either way
DEFERRED_NEEDS = ("prior-data", "prior-observations")
MAX_JUDGE_BODY = 20000  # characters of one response body the judge sees; the full log stays on disk  # not implemented yet; such probes are reported as not run


# ---------------------------------------------------------------------------------------------- the probes


@dataclass(frozen=True)
class Probe:
    id: str
    item: str
    applies_from: int
    applies_until: int | None
    setup: str
    needs: tuple[str, ...]
    scenario: str
    expected: str

    def applies(self, checkpoint: int) -> bool:
        return self.applies_from <= checkpoint and (self.applies_until is None or checkpoint <= self.applies_until)

    @property
    def deferred(self) -> bool:
        return any(d in n for n in self.needs for d in DEFERRED_NEEDS)


@dataclass(frozen=True)
class ProbeSet:
    preamble: str
    setups: dict[str, str]  # "S0" -> its description
    setup_notes: str  # the conventions after the setups ("Each probe is independent...")
    probes: list[Probe]


def _field(body: str, name: str) -> str:
    m = re.search(rf"^- \*\*{re.escape(name)}:\*\*\s*(.*?)(?=^- \*\*|\Z)", body, re.S | re.M)
    if not m:
        raise ValueError(f"probe without {name}")
    return m.group(1).strip()


def parse_probes(text: str) -> ProbeSet:
    head, _, rest = text.partition("\n## Setups")
    setups_text, _, probes_text = rest.partition("\n## Probes")
    setups, notes = {}, ""
    for block in re.split(r"(?m)^### ", setups_text)[1:]:
        heading, _, body = block.partition("\n")
        m = re.match(r"(S\d+):", heading)
        if not m:
            raise ValueError(f"setup heading {heading!r}")
        if m.group(1) == "S0":
            parts = re.split(r"(?m)^(?=Each probe is independent)", body, maxsplit=1)
            body, notes = parts[0], (parts[1] if len(parts) > 1 else "")
        setups[m.group(1)] = f"### {heading}\n{body.strip()}"
    probes = []
    item = None
    for block in re.split(r"(?m)^(?=### |#### )", probes_text):
        if block.startswith("### "):
            item = block[4:].split("\n", 1)[0].strip()
            continue
        if not block.startswith("#### "):
            continue
        pid, _, body = block[5:].partition("\n")
        applies = _field(body, "Applies")
        m = re.fullmatch(r"from change (\d+)(?:, until change (\d+))?", applies)
        if not m:
            raise ValueError(f"{pid}: can't read Applies {applies!r}")
        needs = _field(body, "Needs")
        setup = _field(body, "Setup")
        if setup not in setups:
            raise ValueError(f"{pid}: unknown setup {setup}")
        probes.append(Probe(id=pid.strip(), item=item, applies_from=int(m.group(1)),
                            applies_until=int(m.group(2)) if m.group(2) else None, setup=setup,
                            needs=() if needs == "none" else tuple(n.strip() for n in needs.split(",")),
                            scenario=_field(body, "Scenario"), expected=_field(body, "Expected observation")))
    ids = [p.id for p in probes]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate probe IDs")
    return ProbeSet(preamble=head.strip(), setups=setups, setup_notes=notes.strip(), probes=probes)


def batches(probes: list[Probe], size: int = 4) -> list[list[Probe]]:
    """Group probes into execution batches of at most `size`, keeping each item's probes together where they fit."""
    out, cur = [], []
    for p in probes:
        if cur and (len(cur) >= size):
            out.append(cur)
            cur = []
        cur.append(p)
    if cur:
        out.append(cur)
    return out


def setups_used(batch: list[Probe], setups: dict[str, str]) -> list[str]:
    """The setups a batch's probes use, and every setup their descriptions name (S1 built on S0), in order."""
    want, todo = set(), [p.setup for p in batch]
    while todo:
        s = todo.pop()
        if s in want or s not in setups:
            continue
        want.add(s)
        body = setups[s].split("\n", 1)[1] if "\n" in setups[s] else ""
        todo += re.findall(r"\bS\d+\b", body)
    return sorted(want, key=lambda s: int(s[1:]))


def render_for_execution(batch: list[Probe], conventions: str = "", setups: dict[str, str] | None = None) -> str:
    """The probes as the executor sees them: the probe set's conventions, the full description of each setup the
    batch uses (and of each setup those build on), then scenarios only, never expected observations."""
    head = f"## Conventions for every probe\n\n{conventions.strip()}\n\n" if conventions.strip() else ""
    used = setups_used(batch, setups or {})
    if used:
        head += "## Setups these probes use\n\n" + "\n\n".join(setups[s] for s in used) + "\n\n"
    return head + "\n\n".join(f"## {p.id}\n\n- **Setup:** {p.setup}\n- **Needs:** {', '.join(p.needs) or 'none'}\n"
                       f"- **Scenario:**\n{p.scenario}" for p in batch)


def render_for_judgment(batch: list[Probe], conventions: str = "") -> str:
    head = f"## Conventions for every probe\n\n{conventions.strip()}\n\n" if conventions.strip() else ""
    return head + "\n\n".join(f"## {p.id}\n\n- **Setup:** {p.setup}\n- **Scenario:**\n{p.scenario}\n"
                       f"- **Expected observation:** {p.expected}" for p in batch)


def item_verdicts(probe_verdicts: dict[str, str], probes: list[Probe]) -> dict[str, dict]:
    """met only if every probe is met; any "not met" makes it not met; otherwise couldn't exercise, and otherwise
    missing (a probe left unresolved by a grader error). Probes with no verdict (not run) leave the item without one
    unless another probe decided it."""
    by_item: dict[str, list[Probe]] = {}
    for p in probes:
        by_item.setdefault(p.item, []).append(p)
    out = {}
    for item, ps in by_item.items():
        vs = [probe_verdicts.get(p.id) for p in ps]
        given = [v for v in vs if v]
        if "not met" in given:
            v = "not met"
        elif "couldn't exercise" in given:
            v = "couldn't exercise"
        elif MISSING in given:
            v = MISSING
        elif not given or len(given) < len(vs):
            v = None
        else:
            v = "met"
        out[item] = {"verdict": v, "probes": {p.id: probe_verdicts.get(p.id) for p in ps},
                     "share_met": sum(x == "met" for x in given) / len(ps)}
    return out


# ------------------------------------------------------------------------------------------ docker plumbing

Runner = Callable[..., subprocess.CompletedProcess]


def _run(runner: Runner, cmd: list[str], *, stdin: bytes | str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    p = runner(cmd, input=stdin, capture_output=True, text=not isinstance(stdin, bytes))
    if check and p.returncode != 0:
        err = p.stderr if isinstance(p.stderr, str) else p.stderr.decode(errors="replace")
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(cmd)[:200]}: {err[-500:]}")
    return p


@dataclass
class Checkpoint:
    """One checkpoint being graded: its volume (checkout at /work/app, tools at /work/grading, extraction output at
    /work/out, logs at /work/log, snapshots at /work/snap) and the graders' tools volume."""
    trajectory: str
    change: int
    commit: str
    image: str
    runner: Runner = subprocess.run
    admin_token: str = field(default_factory=lambda: secrets.token_hex(16))

    @property
    def tag(self) -> str:
        return f"ce-g-{self.trajectory}-c{self.change:02d}"

    @property
    def volume(self) -> str:
        return f"{self.tag}-ckpt"

    @property
    def tools_volume(self) -> str:
        return f"{self.tag}-tools"

    @property
    def network(self) -> str:
        return f"{self.tag}-net"

    def sh(self, volume: str, script: str, stdin=None, check=True) -> str:
        p = _run(self.runner, ["docker", "run", "--rm", "-i", "-v", f"{executor._volume(volume)}:/work", "-w", "/work",
                               self.image, "sh", "-c", script], stdin=stdin, check=check)
        return p.stdout if isinstance(p.stdout, str) else p.stdout.decode(errors="replace")

    def put(self, volume: str, path: str, text: str) -> None:
        self.sh(volume, f"mkdir -p \"$(dirname {path})\" && cat > {path}", stdin=text)

    def get(self, volume: str, path: str) -> str | None:
        p = _run(self.runner, ["docker", "run", "--rm", "-v", f"{executor._volume(volume)}:/work", self.image,
                               "cat", f"/work/{path}"], check=False)
        return p.stdout if p.returncode == 0 else None

    def export(self, workspace_volume: str) -> None:
        """Copy the commit's tree into the checkpoint volume, and the grading tools beside it."""
        _run(self.runner, ["docker", "run", "--rm", "-v", f"{executor._volume(workspace_volume)}:/src:ro",
                           "-v", f"{executor._volume(self.volume)}:/work", self.image, "sh", "-c",
                           f"rm -rf /work/app /work/out /work/log /work/snap /work/data-* && mkdir -p /work/app /work/out /work/log /work/snap && "
                           f"git -C /src archive {self.commit} | tar -x -C /work/app"])
        self.put(self.volume, "/work/grading/control.py", (TOOLS / "control.py").read_text())
        self.sh(self.tools_volume, "rm -rf /work/* 2>/dev/null; true")
        self.put(self.tools_volume, "/work/bin/gt", (TOOLS / "gt").read_text())
        self.sh(self.tools_volume, "chmod +x /work/bin/gt")

    def start_apps(self, workers: int) -> list[str]:
        _run(self.runner, ["docker", "network", "create", self.network], check=False)
        names = []
        for k in range(workers):
            name = f"{self.tag}-app{k}"
            _run(self.runner, ["docker", "rm", "-f", name], check=False)
            _run(self.runner, ["docker", "volume", "rm", f"{self.tag}-data{k}"], check=False)
            _run(self.runner, ["docker", "run", "-d", "--name", name, "--network", self.network, "--network-alias", f"app{k}",
                               "--tmpfs", "/clock:mode=1777", "-e", "TZ=UTC", "-e", f"CONTROL_ADMIN_TOKEN={self.admin_token}",
                               "-v", f"{executor._volume(self.volume)}:/work", "-v", f"{self.tag}-data{k}:/cfg",
                               self.image, "python3",
                               "/work/grading/control.py", "--spec", f"/work/out/start-{k}.json", "--port", "9000",
                               "--log", f"/work/log/exec-{k}.jsonl", "--snapshots", "/work/snap",
                               "--app-log", f"/work/log/app-{k}.log"])
            names.append(name)
        return names

    def admin(self, worker: int, payload: dict) -> dict:
        p = _run(self.runner, ["docker", "exec", f"{self.tag}-app{worker}", "python3", "-c",
                               "import json,sys,urllib.request;"
                               "r=urllib.request.Request('http://127.0.0.1:9000/'+sys.argv[1],data=sys.argv[2].encode(),"
                               "method='POST',headers={'x-admin-token':sys.argv[3]});"
                               "print(urllib.request.urlopen(r,timeout=300).read().decode())",
                               payload.pop("_op", "admin"), json.dumps(payload), self.admin_token])
        return json.loads(p.stdout)

    def wait_ready(self, worker: int, timeout_s: float = 300) -> bool:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            log = self.get(self.volume, f"log/exec-{worker}.jsonl") or ""
            for line in log.splitlines():
                rec = json.loads(line)
                if rec.get("op") == "start":
                    return bool((rec.get("response") or {}).get("ok"))
            time.sleep(1)
        return False

    def log_lines(self, worker: int, batch: str) -> list[dict]:
        text = self.get(self.volume, f"log/exec-{worker}.jsonl") or ""
        return [r for r in (json.loads(l) for l in text.splitlines() if l.strip()) if r.get("batch") == batch]

    def stop(self, workers: int) -> None:
        for k in range(workers):
            _run(self.runner, ["docker", "rm", "-f", f"{self.tag}-app{k}"], check=False)
            _run(self.runner, ["docker", "volume", "rm", f"{self.tag}-data{k}"], check=False)
        _run(self.runner, ["docker", "network", "rm", self.network], check=False)


WORKER_DATA = "/cfg/data"  # every worker's data sits at the same path, in its own volume, so restored snapshots
                           # that hold absolute paths stay valid on any worker


def worker_spec(spec: dict, worker: int) -> dict:
    """The extraction's start spec with {DATA} pointed at the worker's data location, the same path on every worker."""
    data = WORKER_DATA

    def sub(v):
        if isinstance(v, str):
            return v.replace("{DATA}", data)
        if isinstance(v, list):
            return [sub(x) for x in v]
        return v
    out = {k: sub(v) for k, v in spec.items() if k != "env"}
    out["env"] = {k: sub(v) for k, v in (spec.get("env") or {}).items()}
    out["data_path"] = sub(spec.get("data_path", "{DATA}"))
    return out


def grader_reference(reference: str, spec: dict) -> str:
    """The reference as graders get it: extraction's text, plus the settings the grading instance runs with, so a
    secret the service needs (such as an admin token) is the one graders use."""
    env = {k: v for k, v in (spec.get("env") or {}).items() if "{DATA}" not in str(v)}
    if not env:
        return reference
    lines = "\n".join(f"- `{k}` = `{v}`" for k, v in env.items())
    return (reference.rstrip() + "\n\n## The instance you are operating\n\nThe service you reach through `gt` was started with "
            f"these settings. Where the reference's examples use a different value, use these:\n\n{lines}\n")


def setup_problems(lines: list[dict], names: list[str], snapshots: set[str]) -> list[str]:
    problems = [f"no snapshot for {n}" for n in names if n not in snapshots]
    problems += [r["request"].get("text", "") for r in lines
                 if r.get("op") == "mark" and str(r.get("request", {}).get("text", "")).startswith("CANNOT")]
    return problems


def broken_setups(problems: list[str], names: list[str]) -> set[str]:
    """The setups a problem names: "no snapshot for S1", or a CANNOT mark naming the setup ("CANNOT S1: ...")."""
    broken = set()
    for p in problems:
        for n in names:
            if p == f"no snapshot for {n}" or p.startswith(f"CANNOT {n}:") or p.startswith(f"CANNOT {n} "):
                broken.add(n)
    return broken


def check_spec(spec: dict) -> list[str]:
    problems = []
    for key in ("workdir", "command", "port", "data_path"):
        if key not in spec:
            problems.append(f"start spec has no {key}")
    if "{DATA}" not in json.dumps(spec):
        problems.append("start spec never uses {DATA} for the data location")
    if not str(spec.get("workdir", "")).startswith("/work/app"):
        problems.append("workdir must be inside /work/app")
    text = json.dumps({k: spec.get(k) for k in ("command", "env", "setup_commands")})
    if "/tmp/" in text or '"/tmp"' in text:
        problems.append("the start spec points under /tmp, which the app containers can't see")
    return problems


# ------------------------------------------------------------------------------------------------- prompts


def _template(name: str, **fills: str) -> str:
    """Fill a prompt's {NAME} placeholders in one pass, so filled-in text (such as a log) is never rescanned."""
    text = (PROMPTS / name).read_text(encoding="utf-8")
    missing = set(re.findall(r"\{([A-Z_]+)\}", text)) - set(fills)
    if missing:
        raise KeyError(f"{name}: no fill for {sorted(missing)}")
    return re.sub(r"\{([A-Z_]+)\}", lambda m: fills[m.group(1)], text)


JUDGE_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["verdicts"],
    "properties": {"verdicts": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["probe", "verdict", "evidence", "reason", "cause"],
        "properties": {"probe": {"type": "string"}, "verdict": {"type": "string", "enum": list(VERDICTS)},
                       "evidence": {"type": "array", "items": {"type": "integer"}}, "reason": {"type": "string"},
                       # why a probe couldn't be exercised: a rerun can settle "execution", not "service"
                       "cause": {"type": "string", "enum": ["execution", "service", "none"]}}}}},
}


def log_for_judge(lines: list[dict]) -> str:
    """The execution log as the judge reads it: one numbered entry per line, admin entries left out."""
    out = []
    for r in lines:
        if r.get("admin"):
            continue
        entry = {k: r[k] for k in ("seq", "clock", "op", "request", "response") if k in r}
        body = (entry.get("response") or {}).get("body") if isinstance(entry.get("response"), dict) else None
        if isinstance(body, str) and len(body) > MAX_JUDGE_BODY:
            entry["response"] = {**entry["response"],
                                 "body": body[:MAX_JUDGE_BODY] + f" ...[cut: {len(body) - MAX_JUDGE_BODY} more characters]"}
        out.append(json.dumps(entry))
    return "\n".join(out)


def execution_faults(verdicts: dict[str, dict]) -> list[str]:
    """Probes the judge couldn't decide because the executor (or the harness) left out or got wrong a step the service
    could have performed. A rerun can settle these; a "couldn't exercise" caused by the service can't be."""
    return sorted(pid for pid, v in verdicts.items()
                  if v.get("verdict") == "couldn't exercise" and v.get("cause") == "execution")


def check_verdicts(result: dict, batch: list[Probe], lines: list[dict]) -> list[str]:
    seqs = {r["seq"] for r in lines}
    problems = []
    got = {v["probe"]: v for v in result.get("verdicts", [])}
    for p in batch:
        v = got.get(p.id)
        if v is None:
            problems.append(f"no verdict for {p.id}")
        elif v["verdict"] != "couldn't exercise" and not v["evidence"]:
            problems.append(f"{p.id}: a verdict without evidence")
        elif any(e not in seqs for e in v["evidence"]):
            problems.append(f"{p.id}: evidence cites lines not in the log")
        elif len(v.get("reason", "").split()) < 5:
            # a stub such as "Placeholder" means the judge never reasoned about this probe
            problems.append(f"{p.id}: a reason too short to explain the verdict")
        elif v["verdict"] == "couldn't exercise" and v.get("cause") not in ("execution", "service"):
            problems.append(f"{p.id}: \"couldn't exercise\" without saying whether the executor or the service was the cause")
    return problems


# --------------------------------------------------------------------------------------------- the sessions

TOOL_PATH = "/work/bin:/home/agent/.local/bin:/usr/local/bin:/usr/bin:/bin"


@dataclass(frozen=True)
class Graders:
    image: str
    roles_volume: str
    claude_code: str
    extraction_model: str = "claude-sonnet-5-5"
    setup_model: str = "claude-haiku-5-5"
    execute_model: str = "claude-haiku-5-5"
    judge_model: str = "claude-sonnet-5-5"
    effort: str = "medium"

    def role(self, model: str, **kw) -> executor.RoleSession:
        return executor.RoleSession(image=self.image, config_volume=self.roles_volume, model=model,
                                    claude_code_version=self.claude_code, effort=self.effort, **kw)


def _usage(rec: executor.RoleRecord) -> dict:
    return {"cost_usd": rec.usage.reported_cost_usd, "duration_s": round(rec.duration_s, 1),
            "models": {m: asdict(c) for m, c in rec.usage.models.items()}}


def extract(ck: Checkpoint, g: Graders, out: Path, seed_notes: str = "") -> dict:
    role = g.role(g.extraction_model, tools=("Bash", "Read", "Write", "Edit", "Glob", "Grep"),
                  workspace_volume=ck.volume, timeout_s=2400)
    prompt = _template("extraction.md", TEMPLATE=(PROMPTS / "extraction-template.md").read_text(encoding="utf-8"),
                       DATA="{DATA}")
    if seed_notes.strip():
        prompt += "\n\n## Notes for this project\n\n" + seed_notes.strip() + "\n"
    rec = executor.run_role(role, prompt)
    reference, spec_text = ck.get(ck.volume, "out/reference.md"), ck.get(ck.volume, "out/start.json")
    out.mkdir(parents=True, exist_ok=True)
    (out / "reference.md").write_text(reference or "", encoding="utf-8")
    (out / "start.json").write_text(spec_text or "", encoding="utf-8")
    try:
        spec = json.loads(spec_text or "")
        problems = check_spec(spec)
    except json.JSONDecodeError:
        spec, problems = None, ["no readable start spec"]
    if not reference:
        problems.append("no reference")
    result = {"spec": spec, "problems": problems, "usage": _usage(rec), "reply": rec.text}
    (out / "extraction.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    return result


def setups_needed(probeset: ProbeSet, wanted: set[str]) -> list[str]:
    """The setups the wanted ones need, with every setup their descriptions refer to ("Identical to S0, plus…"),
    so a setup session never gets a description whose base it can't see. In order: S0, S1, …"""
    need, todo = set(), list(wanted)
    while todo:
        name = todo.pop()
        if name in need or name not in probeset.setups:
            continue
        need.add(name)
        todo += re.findall(r"\bS\d+\b", probeset.setups[name])
    return sorted(need, key=lambda n: int(n[1:]))


def prepare_setups(ck: Checkpoint, g: Graders, probeset: ProbeSet, names: list[str], reference: str, out: Path) -> dict:
    ck.put(ck.tools_volume, "/work/reference.md", reference)
    setups = "\n\n".join(probeset.setups[n] for n in names) + "\n\n" + probeset.setup_notes
    ck.put(ck.tools_volume, "/work/setups.md", setups)
    ck.admin(0, {"batch": "setup", "allow_snapshot": True})
    role = g.role(g.setup_model, tools=("Bash", "Read", "Write"), workspace_volume=ck.tools_volume,
                  network=ck.network, env=(("GT_CONTROL", "http://app0:9000"), ("PATH", TOOL_PATH)), timeout_s=2400)
    rec = executor.run_role(role, _template("grade-setup.md"))
    ck.admin(0, {"batch": None, "allow_snapshot": False})
    ids = ck.get(ck.tools_volume, "ids.md") or ""
    have = set(ck.sh(ck.volume, "ls /work/snap 2>/dev/null || true").split())
    out.mkdir(parents=True, exist_ok=True)
    (out / "ids.md").write_text(ids, encoding="utf-8")
    lines = ck.log_lines(0, "setup")
    (out / "setup-log.jsonl").write_text("\n".join(json.dumps(r) for r in lines), encoding="utf-8")
    problems = setup_problems(lines, names, have)
    if not ids.strip():
        problems.append("no identifier list")
    elif "## Credentials" not in ids:
        problems.append("the identifier list has no Credentials section")
    result = {"problems": problems, "usage": _usage(rec), "reply": rec.text}
    (out / "setup.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    return result


def execute_batch(ck: Checkpoint, g: Graders, worker: int, bid: str, batch: list[Probe], out: Path,
                  conventions: str = "", setups: dict[str, str] | None = None) -> list[dict]:
    ck.put(ck.tools_volume, f"/work/probes-{bid}.md", render_for_execution(batch, conventions, setups))
    ck.admin(worker, {"batch": bid})
    role = g.role(g.execute_model, tools=("Bash", "Read"), workspace_volume=ck.tools_volume, network=ck.network,
                  env=(("GT_CONTROL", f"http://app{worker}:9000"), ("PATH", TOOL_PATH)), timeout_s=2400)
    prompt = _template("grade-execute.md").replace("/work/probes.md", f"/work/probes-{bid}.md")
    try:
        rec = executor.run_role(role, prompt)
        session = {"usage": _usage(rec), "reply": rec.text}
    except executor.RoleFailed as e:
        session = {"error": str(e)}
    ck.admin(worker, {"batch": None})
    lines = ck.log_lines(worker, bid)
    out.mkdir(parents=True, exist_ok=True)
    (out / "probes.md").write_text(render_for_execution(batch, conventions, setups), encoding="utf-8")
    (out / "log.jsonl").write_text("\n".join(json.dumps(r) for r in lines), encoding="utf-8")
    (out / "execution.json").write_text(json.dumps(session, indent=1), encoding="utf-8")
    return lines


def judge_batch(g: Graders, batch: list[Probe], lines: list[dict], out: Path, attempts: int = 3,
                conventions: str = "") -> dict[str, dict]:
    role = g.role(g.judge_model, timeout_s=1200)
    prompt = _template("grade-judge.md", PROBES=render_for_judgment(batch, conventions), LOG=log_for_judge(lines))
    tries = []
    for _ in range(attempts):
        rec = executor.run_role(role, prompt, json_schema=json.dumps(JUDGE_SCHEMA, separators=(",", ":")))
        problems = check_verdicts(rec.structured or {}, batch, lines)
        tries.append({"structured": rec.structured, "problems": problems, "usage": _usage(rec)})
        if not problems:
            break
    final = {v["probe"]: v for v in (tries[-1]["structured"] or {}).get("verdicts", [])} if not tries[-1]["problems"] else {}
    (out / "judgment.json").write_text(json.dumps({"tries": tries, "verdicts": final}, indent=1), encoding="utf-8")
    return final
