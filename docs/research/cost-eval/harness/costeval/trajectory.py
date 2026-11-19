"""One arm's trajectory through a seed's changes: arms, workspaces, and the loop between agent and owner.

Design: "Arms", "Sessions and isolation", and "The harness" in the notebook's design.md.

- An arm is data (harness/arms/<name>.json): the plugins it loads, the files it adds to the project, the
  permission mode of each change's first turn, and any prefix to a change's first prompt.
- Every change runs in a fresh session in the executor container. Its first prompt is the owner's request plus
  one neutral sentence saying the owner can answer questions, the same for every arm.
- Whenever a turn ends, the simulated owner responds. A completion report it has nothing to say about ends the
  change; otherwise its reply resumes the session. A cap on rounds stops a change that never finishes.
- At the end of each change the harness commits whatever the arm left uncommitted, so every change has a
  checkpoint.
- Records are raw: every turn's stream, every owner call, and a summary per change with each turn's usage.
"""

from __future__ import annotations

import json
import shlex
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Protocol

from . import executor, simulator, usage

ARMS_DIR = Path(__file__).resolve().parent.parent / "arms"
NEUTRAL_SENTENCE = "I'm available to answer questions while you work."
ROUND_CAP = 15  # owner replies per change before the harness stops it
CODE_SUFFIXES = (".py", ".js", ".ts", ".tsx", ".jsx", ".sql", ".html", ".css", ".go", ".rs", ".java", ".rb", ".sh",
                 ".toml", ".cfg", ".ini", ".yaml", ".yml", ".json")
GIT_IDENTITY = ("Lab Owner", "owner@example.invalid")


# --------------------------------------------------------------------------------------------------- arms


@dataclass(frozen=True)
class Arm:
    name: str
    description: str
    plugins: tuple[str, ...]
    lid_release: str | None
    workspace_files: dict[str, str]  # path in the project -> file beside the arm's JSON
    first_turn_mode: str
    first_prompt_prefix: dict[int, str]

    @property
    def plugin_dirs(self) -> tuple[str, ...]:
        return tuple(f"/cfg/lid/plugins/{p}" for p in self.plugins)


def load_arm(name: str, arms_dir: Path = ARMS_DIR) -> Arm:
    d = json.loads((arms_dir / f"{name}.json").read_text(encoding="utf-8"))
    if d["first_turn_mode"] not in executor.PERMISSION_MODES:
        raise ValueError(f"{name}: unknown first-turn mode {d['first_turn_mode']!r}")
    if d["plugins"] and not d["lid_release"]:
        raise ValueError(f"{name}: plugins need a pinned release")
    return Arm(name=d["name"], description=d["description"], plugins=tuple(d["plugins"]), lid_release=d["lid_release"],
               workspace_files=dict(d["workspace_files"]), first_turn_mode=d["first_turn_mode"],
               first_prompt_prefix={int(k): v for k, v in d["first_prompt_prefix"].items()})


def change_prompt(arm: Arm, change: simulator.Change, owner_request: str) -> str:
    """The first prompt of a change: any prefix the arm gives this change, the owner's request, and the
    neutral sentence."""
    prefix = "" if change.probe else arm.first_prompt_prefix.get(change.number, "")
    return f"{prefix}{owner_request.strip()}\n\n{NEUTRAL_SENTENCE}"


def is_code_path(path: str) -> bool:
    """A source file other than documentation or tests: what makes a late redirect due."""
    p = path.lower()
    name = p.rsplit("/", 1)[-1]
    if not p.endswith(CODE_SUFFIXES):
        return False
    parts = p.split("/")
    if any(seg in ("tests", "test") for seg in parts[:-1]):
        return False
    return not (name.startswith("test_") or name.endswith(("_test.py", ".test.js", ".test.ts", ".spec.js", ".spec.ts"))
                or name == "conftest.py")


def plan_from_stream(path: Path) -> str | None:
    """The plan a plan-mode turn presented: the last ExitPlanMode input, or failing that the last plan file
    written (headless plan mode writes the plan to a file under the configuration folder's plans/)."""
    plan = written = None
    for rec in usage._json_lines(Path(path)):
        if rec.get("type") != "assistant":
            continue
        for block in (rec.get("message") or {}).get("content") or []:
            if block.get("type") != "tool_use":
                continue
            inp = block.get("input") or {}
            if block.get("name") == "ExitPlanMode" and inp.get("plan"):
                plan = inp["plan"]
            elif block.get("name") == "Write" and "/plans/" in str(inp.get("file_path", "")) and inp.get("content"):
                written = inp["content"]
    return plan or written


def skills_used(path: Path) -> list[str]:
    out = []
    for rec in usage._json_lines(Path(path)):
        if rec.get("type") == "assistant":
            for block in (rec.get("message") or {}).get("content") or []:
                if block.get("type") == "tool_use" and block.get("name") == "Skill":
                    out.append(str((block.get("input") or {}).get("skill") or (block.get("input") or {}).get("command")))
    return out


# ---------------------------------------------------------------------------------------------- workspace


class Workspace(Protocol):
    def commit_all(self, message: str) -> str | None: ...
    def head(self) -> str: ...
    def changed_paths(self, base: str) -> list[str]: ...
    def prose_paths(self) -> list[str]: ...
    def read(self, paths: list[str]) -> dict[str, str]: ...


_PY_CHANGED = r"""
import json, subprocess, sys
base = sys.argv[1]
run = lambda *a: subprocess.run(a, capture_output=True, text=True, check=True).stdout.splitlines()
paths = set(run('git', 'diff', '--name-only', base)) | set(run('git', 'ls-files', '--others', '--exclude-standard'))
print(json.dumps(sorted(paths)))
"""
_PY_PROSE = r"""
import json, subprocess
run = lambda *a: subprocess.run(a, capture_output=True, text=True, check=True).stdout.splitlines()
paths = set(run('git', 'ls-files')) | set(run('git', 'ls-files', '--others', '--exclude-standard'))
suff = ('.md', '.markdown', '.txt', '.rst', '.adoc')
import os
print(json.dumps(sorted(p for p in paths if p.lower().endswith(suff) and os.path.isfile(p))))
"""
_PY_READ = r"""
import json, sys
out = {}
for p in json.loads(sys.stdin.read()):
    try:
        out[p] = open(p, encoding='utf-8', errors='replace').read()
    except OSError:
        pass
print(json.dumps(out))
"""


@dataclass
class DockerWorkspace:
    """The arm's workspace volume, worked on through short-lived containers from the executor image."""
    image: str
    volume: str
    runner: Callable = subprocess.run

    def _run(self, args: list[str], stdin: str | None = None) -> str:
        cmd = ["docker", "run", "--rm", "-i", "-v", f"{executor._volume(self.volume)}:/work", "-w", "/work", self.image] + args
        proc = self.runner(cmd, input=stdin, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"workspace command failed ({proc.returncode}): {' '.join(args)[:200]}: {proc.stderr[-500:]}")
        return proc.stdout

    def init(self, files: dict[str, str]) -> str:
        """Start an empty repository with the arm's files, as one commit. Returns its hash."""
        script = ["set -e", "git init -q -b main",
                  f"git config user.name {shlex.quote(GIT_IDENTITY[0])}", f"git config user.email {shlex.quote(GIT_IDENTITY[1])}"]
        for path, text in files.items():
            script.append(f"mkdir -p \"$(dirname {shlex.quote(path)})\" && printf %s {shlex.quote(text)} > {shlex.quote(path)}")
        script += ["git add -A", "git commit -q --allow-empty -m 'Start'", "git rev-parse HEAD"]
        return self._run(["sh", "-c", "\n".join(script)]).strip()

    def commit_all(self, message: str) -> str | None:
        out = self._run(["sh", "-c", "git add -A && if git diff --cached --quiet; then echo NONE; else git commit -q -m "
                         + shlex.quote(message) + " && git rev-parse HEAD; fi"]).strip()
        return None if out == "NONE" else out

    def head(self) -> str:
        return self._run(["git", "rev-parse", "HEAD"]).strip()

    def changed_paths(self, base: str) -> list[str]:
        return json.loads(self._run(["python3", "-c", _PY_CHANGED, base]))

    def prose_paths(self) -> list[str]:
        return json.loads(self._run(["python3", "-c", _PY_PROSE]))

    def read(self, paths: list[str]) -> dict[str, str]:
        if not paths:
            return {}
        return json.loads(self._run(["python3", "-c", _PY_READ], stdin=json.dumps(paths)))


def install_lid(image: str, config_volume: str, lid_repo: Path, release: str, runner: Callable = subprocess.run) -> None:
    """Put LID's plugins, as of a release tag, into the arm's configuration volume at /cfg/lid/plugins."""
    archive = runner(["git", "-C", str(lid_repo), "archive", "--format=tar", release, "plugins"], capture_output=True)
    if archive.returncode != 0:
        raise RuntimeError(f"git archive {release} failed: {archive.stderr[-300:]!r}")
    proc = runner(["docker", "run", "--rm", "-i", "-v", f"{executor._volume(config_volume)}:/cfg", image,
                   "sh", "-c", "rm -rf /cfg/lid && mkdir -p /cfg/lid && tar -x -C /cfg/lid"], input=archive.stdout, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"installing LID failed: {proc.stderr[-300:]!r}")


# ------------------------------------------------------------------------------------------- the change loop


class TrajectoryStopped(RuntimeError):
    """A change couldn't go on: a failed or invalid turn, or an owner that couldn't reply."""


@dataclass
class ChangeResult:
    change: int
    title: str
    rounds: int
    finished: bool
    capped: bool
    session_id: str | None
    turns: list[dict] = field(default_factory=list)
    owner: list[dict] = field(default_factory=list)
    redirect: dict | None = None
    commit: str | None = None
    base: str | None = None
    error: str | None = None


TurnFn = Callable[..., executor.TurnRecord]


def _turn_summary(t: executor.TurnRecord, previous: usage.Usage | None, mode: str) -> tuple[dict, usage.Usage | None]:
    u = t.summary.usage
    delta = None
    if u is not None:
        delta = u if previous is None else usage.turn_delta(previous, u)
    rec = {
        "stream": t.stream_path.name, "mode": mode, "exit_code": t.exit_code, "timed_out": t.timed_out,
        "duration_s": round(t.duration_s, 1), "session_id": t.session_id, "init_problem": t.init_problem,
        "is_error": t.summary.is_error, "final_words": simulator.words(t.final_text or ""),
        "usage": None if delta is None else usage_dict(delta),
        "skills": skills_used(t.stream_path), "builtin_plugins": executor.builtin_plugins(t.init),
    }
    return rec, (u if u is not None else previous)


def usage_dict(u: usage.Usage) -> dict:
    return {"models": {m: asdict(c) for m, c in u.models.items()}, "reported_cost_usd": u.reported_cost_usd}


def run_change(*, arm: Arm, change: simulator.Change, owner: simulator.Owner, turn: TurnFn, workspace: Workspace,
               out_dir: Path, round_cap: int = ROUND_CAP, commit: bool = True) -> ChangeResult:
    """Run one change: the first prompt, then owner replies until the owner accepts or the cap is reached."""
    out_dir.mkdir(parents=True, exist_ok=True)
    base = workspace.head()
    request = owner.start_change(change)
    prompt = change_prompt(arm, change, request)
    res = ChangeResult(change=change.number, title=change.title, rounds=0, finished=False, capped=False,
                       session_id=None, base=base)
    (out_dir / "prompt-00.txt").write_text(prompt, encoding="utf-8")
    mode, resume, previous = arm.first_turn_mode, None, None
    try:
        k = 0
        while True:
            t = turn(prompt, out_dir / f"turn-{k:02d}.stream.jsonl", resume=resume, permission_mode=mode)
            rec, previous = _turn_summary(t, previous, mode)
            res.turns.append(rec)
            res.session_id = res.session_id or t.session_id
            if t.timed_out or t.init_problem or t.summary.is_error or t.exit_code not in (0, None) or t.session_id is None:
                raise TrajectoryStopped(f"turn {k} failed: exit {t.exit_code}, timed out {t.timed_out}, "
                                        f"init {t.init_problem}, error {t.summary.is_error}")
            message = t.final_text or ""
            plan = plan_from_stream(t.stream_path) if mode == "plan" else None
            if plan and plan.strip()[:200] in message:
                plan = None  # already in the message
            changed = workspace.changed_paths(base)
            prose = workspace.prose_paths()
            named = simulator.mentioned_documents(message, prose)
            docs = owner.documents(message, workspace.read(named), plan)
            try:
                rep = owner.respond(message, docs, code_written=any(is_code_path(p) for p in changed))
            except simulator.OwnerFailed as e:
                raise TrajectoryStopped(f"owner failed after turn {k}: {e}") from e
            orec = {"turn": k, "message_kind": rep.message_kind, "reply": rep.reply, "finished": rep.finished,
                    "answers": rep.answers, "kept": rep.kept, "dropped": rep.dropped, "redirect_event": rep.redirect_event,
                    "words_shown": rep.words_shown, "words_this_change": rep.words_this_change, "passages": rep.passages,
                    "shared": rep.shared, "recalled": rep.recalled, "draws": rep.draws, "documents": [d.name for d in docs],
                    "code_written": any(is_code_path(p) for p in changed), "costs": simulator.call_costs(rep)}
            res.owner.append(orec)
            (out_dir / f"owner-{k:02d}.json").write_text(
                json.dumps({**orec, "calls": rep.calls, "touch_calls": rep.touch_calls, "check_calls": rep.check_calls},
                           indent=1), encoding="utf-8")
            res.rounds = k + 1
            if rep.finished:
                res.finished = True
                break
            if res.rounds >= round_cap:
                res.capped = True
                break
            prompt, resume, mode = rep.reply, t.session_id, "bypassPermissions"
            k += 1
    except TrajectoryStopped as e:
        res.error = str(e)
    finally:
        res.redirect = owner.end_change()["redirect"] if owner.change is not None else None
        if commit:
            res.commit = workspace.commit_all(f"Change {change.number}: {change.title} (committed by the harness)") or workspace.head()
        (out_dir / "change.json").write_text(json.dumps(asdict(res), indent=1), encoding="utf-8")
    return res


def owner_state(owner: simulator.Owner) -> dict:
    """What the owner carries between changes, saved so a trajectory can resume after a change. The draws need no
    state of their own: each uniform is a function of the replicate, the item, the kind of event, and the scope, and
    the disclosed set says which items are never drawn for again. The replicate and owner model are saved for the
    record; the run's settings, not the state, decide them on restore."""
    return {"record": [asdict(s) for s in owner.record], "requests": owner.requests, "seen": owner.seen,
            "disclosed": sorted(owner.disclosed), "policy": owner.policy, "replicate": owner.replicate,
            "owner_model": asdict(owner.model)}


def restore_owner_state(owner: simulator.Owner, state: dict) -> None:
    owner.record = [simulator.Said(s["change"], s["said"], s["question"], tuple(s["items"])) for s in state["record"]]
    owner.requests = [tuple(r) for r in state["requests"]]
    owner.seen = dict(state["seen"])
    # A state saved before disclosure was tracked: everything the record shows the owner sharing is disclosed.
    owner.disclosed = (set(state["disclosed"]) if "disclosed" in state
                       else {i for s in owner.record for i in s.items})
