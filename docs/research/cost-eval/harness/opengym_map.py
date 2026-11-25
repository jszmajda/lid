"""Map openGym with LID's own /map-codebase skill, run as an executor session (plan.md, M2h; decisions.md, 2026-11-22).

    ../plumbing/with-token.sh python3.12 opengym_map.py run --id ogmap-1
    python3.12 opengym_map.py check --id ogmap-1     # what the map changed, beyond docs
    python3.12 opengym_map.py test --id ogmap-1      # the project's suites on the bare and LID starts
    python3.12 opengym_map.py prepare --id ogmap-bare  # the shared bare start alone, in its own volume

The LID arm of the brownfield test starts from a snapshot mapped once; the mapping is a one-time adoption cost.

run:
  1. The workspace volume gets the whole pinned tree as a one-commit git repository, the way the Clowder variants
     are built: commit "Start" at the variants' fixed date, so every draw's "Start" is the same commit.
     That commit is the bare arm's start: the pinned tree as it is, with its own CLAUDE.md. The subject's
     dependencies are then installed into the workspace (git ignores node_modules), as the feasibility runs did.
  2. The configuration volume gets LID's plugins at the M2f LID arm's release, installed the way that arm's are;
     the session loads linked-intent-dev and arrow-maintenance (map-codebase lives in arrow-maintenance).
  3. One `claude -p` session in the Node executor image, with the M2f LID arm's model, effort, window and isolation
     (GitHub's hosts blocked, web search and fetch denied). Its first prompt is the skill invocation plus one added
     instruction: no owner is available; where the skill would ask, choose the most reasonable answer, note the
     question and the choice in /cfg/owner-questions.md (outside the project), and continue. Whenever a turn ends
     before the mapping is complete, the session is resumed with that same instruction and nothing else.
  4. The mapping is complete when the workspace holds docs/high-level-design.md, docs/arrows/index.yaml, and an
     agent-instructions file with a `## LID` block and a `- Mode:` bullet (the skill's terminal update-lid step).
     A turn that fails, a skill that never loaded, or the round cap stops the run as a misfire.
  5. The questions file, the session's transcripts (subagents' included) and anything else it left in /cfg are copied
     out, and whatever the session left in the workspace is committed after "Start" as the LID arm's start commit.
     Nothing in the map is edited.

Records go to ../runs/opengym-map/<id>/ (git ignores runs/): mapping.json (settings, every turn's usage, wall time and
workspace state, totals, both start commits), each turn's stream, the questions file, and the transcripts.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import executor, trajectory, usage  # noqa: E402

CLAUDE_CODE = "2.1.323"  # the pinned Claude Code version (run_trajectory.CLAUDE_CODE)
DATE = "2026-01-01T00:00:00+00:00"  # the variants' fixed commit date (clowder_variants.DATE)
PIN = "e4a68a94c42a3c17cbd560d66ce2e46a7048ab99"
REPO = Path("/private/tmp/claude-502/-Users-jess-src-lid/9c732225-b931-431e-a59e-640e6a6ca9e1/scratchpad/opengym/repo")
IMAGE = "lid-cost-eval-executor-node:2.1.323"
MODEL, EFFORT, WINDOW = "claude-sonnet-5-5", "medium", "1m"  # the M2f LID arm's (run_fork.py defaults, 1M window)
RELEASE = "v1.4.6"  # the M2f LID arm's release (arms/lid-full.json)
PLUGINS = ("linked-intent-dev", "arrow-maintenance")
OMIT: tuple[str, ...] = ()  # the whole pinned tree; catalogue/media (199 MB) is needed by scripts/routines' tests
INSTALLS = (("api", "npm ci --omit=optional --no-audit --no-fund"),
            ("frontend", "npm ci --ignore-scripts --no-audit --no-fund"),
            ("mcp", "npm ci --no-audit --no-fund"),
            (".", "npm ci --ignore-scripts --no-audit --no-fund"))
QUESTIONS = "/cfg/owner-questions.md"
INSTRUCTION = ("No owner is available to answer questions during this mapping. Wherever the skill would ask the owner "
               "a question or wait for the owner's approval, choose the most reasonable answer yourself, note the "
               f"question and your choice in {QUESTIONS} (outside the project), and continue.")
FIRST_PROMPT = f"/map-codebase {INSTRUCTION}"
CONTINUE_PROMPT = INSTRUCTION
SKILL_MARK = "Map Codebase (Brownfield Arrow Bootstrap)"  # the skill's heading, in the transcript once it loads
ROUND_CAP = 40
TURN_TIMEOUT = 6 * 3600
GIT_NAME, GIT_EMAIL = trajectory.GIT_IDENTITY
DOC_PREFIXES = ("docs/intent/", "docs/arrows/", "docs/decisions/")
DOC_FILES = ("docs/high-level-design.md", "CLAUDE.md", "AGENTS.md")


@dataclass
class Deps:
    """What the runner reaches outside itself; tests replace each part."""
    docker: Callable = subprocess.run
    turn_for: Callable | None = None  # session -> turn function; default executor.run_turn in that session
    pace: Callable | None = None  # the pacing gate before each turn; default pace.sh
    install_lid: Callable = trajectory.install_lid
    archive: Callable | None = None  # (repo, commit, paths) -> tar bytes; default git archive


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def volumes(run_id: str) -> dict:
    return {"workspace": f"{run_id}-ws", "config": f"{run_id}-cfg", "test": f"{run_id}-test"}


# ------------------------------------------------------------------------------------------------- the workspace


def archive_paths(entries: dict[str, list[str]], omit: tuple[str, ...] = OMIT) -> list[str]:
    """The paths to archive: every top-level entry, except that a top-level folder holding an omitted path is replaced
    by its own entries other than that path. entries maps "" to the top level and a folder to its entries (full
    paths, as `git ls-tree --name-only <commit> <folder>/` prints them)."""
    parents = {o.split("/", 1)[0] for o in omit}
    out = []
    for name in entries[""]:
        if name in parents:
            out += [p for p in entries[name] if p not in omit]
        else:
            out.append(name)
    return out


def git_archive(repo: Path, commit: str, paths: list[str]) -> bytes:
    p = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", commit, *paths], capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"git archive failed: {p.stderr[-500:]!r}")
    return p.stdout


def tree_entries(repo: Path, commit: str, omit: tuple[str, ...] = OMIT) -> dict[str, list[str]]:
    ls = lambda *a: subprocess.run(["git", "-C", str(repo), "ls-tree", "--name-only", commit, *a],  # noqa: E731
                                   capture_output=True, text=True, check=True).stdout.split()
    out = {"": ls()}
    for parent in sorted({o.split("/", 1)[0] for o in omit}):
        out[parent] = ls(f"{parent}/")
    return out


def _run(deps: Deps, cmd: list[str], *, input=None, what: str, text: bool = True) -> subprocess.CompletedProcess:
    p = deps.docker(cmd, input=input, capture_output=True, text=text)
    if p.returncode != 0:
        err = p.stderr if text else (p.stderr or b"").decode(errors="replace")
        raise RuntimeError(f"{what} failed ({p.returncode}): {(err or '')[-800:]}")
    return p


def start_script() -> str:
    """Unpack the tree into the empty workspace and commit it once, at the fixed date, as "Start"."""
    return ("set -e; find /work -mindepth 1 -delete; tar -x -C /work; cd /work; git init -q -b main;"
            f" git config user.name '{GIT_NAME}'; git config user.email '{GIT_EMAIL}'; git add -A;"
            f" GIT_AUTHOR_DATE='{DATE}' GIT_COMMITTER_DATE='{DATE}' git -c commit.gpgsign=false commit -q -m Start;"
            " git rev-parse HEAD")


def install_script(installs=INSTALLS) -> str:
    steps = " && ".join(f"(cd /work/{d} && {cmd})" for d, cmd in installs)
    return f"set -e; {steps}"


def prepare_workspace(deps: Deps, *, repo: Path, commit: str, image: str, volume: str) -> str:
    """The pinned tree as a one-commit repository with its dependencies installed; returns the "Start" commit."""
    paths = archive_paths(tree_entries(repo, commit))
    tar = (deps.archive or git_archive)(repo, commit, paths)
    p = _run(deps, ["docker", "run", "--rm", "-i", "-v", f"{volume}:/work", image, "sh", "-c", start_script()],
             input=tar, what="unpacking the tree", text=False)
    start = p.stdout.decode().strip().splitlines()[-1]
    _run(deps, ["docker", "run", "--rm", "-v", f"{volume}:/work", image, "sh", "-c", install_script()],
         what="installing the dependencies")
    p = _run(deps, ["docker", "run", "--rm", "-v", f"{volume}:/work", "-w", "/work", image, "git", "status",
                    "--porcelain"], what="checking the tree")
    dirty = [ln for ln in p.stdout.splitlines() if ln.strip()]
    if dirty:
        raise RuntimeError(f"installing left tracked changes: {dirty[:10]}")
    return start


_PY_STATE = r"""
import json, os, re
def has(p): return os.path.exists(p)
lid = {}
for f in ("CLAUDE.md", "AGENTS.md"):
    if has(f):
        t = open(f, encoding="utf-8", errors="replace").read()
        lid[f] = bool(re.search(r"^## LID\s*$", t, re.M)) and bool(re.search(r"^- Mode:", t, re.M))
designs, specs = [], []
for root, dirs, files in os.walk("docs/intent"):
    for n in files:
        p = os.path.join(root, n)
        if n.endswith("-design.md"): designs.append(p)
        if n.endswith("-specs.md"): specs.append(p)
ears = 0
for p in specs:
    ears += len(re.findall(r"^\s*-\s*\[[ xXD]\]\s*\*{0,2}[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+", open(p, encoding="utf-8", errors="replace").read(), re.M))
arrows = []
for root, dirs, files in os.walk("docs/arrows"):
    if "_map-codebase" in root: continue
    arrows += [os.path.join(root, n) for n in files if n.endswith(".md")]
print(json.dumps({"hld": has("docs/high-level-design.md"), "index": has("docs/arrows/index.yaml"),
                  "lid_block": lid, "sweep_dir": has("docs/arrows/_map-codebase"),
                  "designs": sorted(designs), "specs": sorted(specs), "ears": ears, "arrow_docs": sorted(arrows)}))
"""


def workspace_state(deps: Deps, image: str, volume: str) -> dict:
    p = _run(deps, ["docker", "run", "--rm", "-v", f"{volume}:/work", "-w", "/work", image, "python3", "-c", _PY_STATE],
             what="reading the workspace state")
    return json.loads(p.stdout)


def is_done(state: dict) -> bool:
    """The skill's terminal state: the skeleton HLD, the overlay's index, and update-lid's LID block."""
    return bool(state.get("hld") and state.get("index") and any((state.get("lid_block") or {}).values()))


def skill_loaded(deps: Deps, image: str, cfg_volume: str, session_id: str) -> bool:
    """Whether the session's transcript holds the skill's text (stream-json doesn't echo a slash command's expansion)."""
    p = deps.docker(["docker", "run", "--rm", "-v", f"{cfg_volume}:/cfg", image, "sh", "-c",
                     f"grep -l -F '{SKILL_MARK}' /cfg/projects/*/{session_id}.jsonl"],
                    capture_output=True, text=True)
    return p.returncode == 0 and bool(p.stdout.strip())


# ------------------------------------------------------------------------------------------------- the session


@dataclass
class MappingResult:
    turns: list
    states: list
    session_id: str | None
    stop: str  # done, capped, failed, skill-not-loaded
    error: str | None
    cumulative: usage.Usage | None
    skill_loaded: bool | None


def run_mapping(*, turn: Callable, state: Callable[[], dict], loaded: Callable[[str], bool], out_dir: Path,
                round_cap: int = ROUND_CAP, pace: Callable | None = None) -> MappingResult:
    """The first prompt, then the fixed instruction whenever a turn ends before the mapping is complete."""
    out_dir.mkdir(parents=True, exist_ok=True)
    turns, states, session, previous, ok = [], [], None, None, None
    prompt, k = FIRST_PROMPT, 0
    while True:
        if pace:
            pace()
        (out_dir / f"prompt-{k:02d}.txt").write_text(prompt, encoding="utf-8")
        began = datetime.now(timezone.utc).isoformat(timespec="seconds")
        t = turn(prompt, out_dir / f"turn-{k:02d}.stream.jsonl", resume=session)
        rec, previous = trajectory._turn_summary(t, previous, "bypassPermissions")
        rec["started"] = began
        rec["final_text"] = t.final_text
        turns.append(rec)
        session = session or t.session_id
        if t.timed_out or t.init_problem or t.summary.is_error or t.exit_code not in (0, None) or t.session_id is None:
            return MappingResult(turns, states, session, "failed", f"turn {k} failed: exit {t.exit_code}, timed out "
                                 f"{t.timed_out}, init {t.init_problem}, error {t.summary.is_error}", previous, ok)
        if k == 0:
            ok = loaded(t.session_id)
            if not ok:
                return MappingResult(turns, states, session, "skill-not-loaded",
                                     "the first turn's transcript doesn't hold the skill's text", previous, ok)
        s = state()
        states.append(s)
        rec["state"] = {"hld": s.get("hld"), "index": s.get("index"), "lid_block": s.get("lid_block"),
                        "designs": len(s.get("designs") or []), "specs": len(s.get("specs") or []),
                        "ears": s.get("ears"), "arrow_docs": len(s.get("arrow_docs") or [])}
        if is_done(s):
            return MappingResult(turns, states, session, "done", None, previous, ok)
        if len(turns) >= round_cap:
            return MappingResult(turns, states, session, "capped", f"no terminal state after {round_cap} turns",
                                 previous, ok)
        prompt, k = CONTINUE_PROMPT, k + 1


# Claude Code's own entries in its configuration folder; anything else there was left by the session or the harness.
CLAUDE_CFG = (".claude.json", ".last-cleanup", "backups", "lid", "plugins", "projects", "sessions", "session-env",
              "shell-snapshots", "statsig", "todos", "cache", "ide", "telemetry")
CLAUDE_CFG_GLOBS = ("policy-limits*", "remote-settings*", ".claude.json.*", ".credentials*")


def transcripts_script(session_id: str) -> str:
    """Run in /cfg/projects: a tar of the session's transcript and its folder (subagents' transcripts, tool results).
    The paths start with ./ because the project folder for /work is named "-work", which ls and tar read as an option."""
    return f"tar -c $(ls -d ./*/{session_id}.jsonl ./*/{session_id} 2>/dev/null)"


def extras_script() -> str:
    """Run in /cfg: a tar of everything there that isn't Claude Code's own, such as the questions file and notes the
    session moved out of the project."""
    skip = " ".join(f"! -name '{n}'" for n in CLAUDE_CFG + CLAUDE_CFG_GLOBS)
    return f"tar -c $(find . -mindepth 1 -maxdepth 1 {skip} | sort)"


def collect(deps: Deps, image: str, cfg_volume: str, session_id: str | None, out_dir: Path) -> dict:
    """Copy the questions file, the session's transcripts (with its subagents'), and anything else the session left in
    the configuration volume (cfg-extras/) out of it."""
    found = {}
    p = deps.docker(["docker", "run", "--rm", "-v", f"{cfg_volume}:/cfg", image, "sh", "-c", f"cat {QUESTIONS}"],
                    capture_output=True, text=True)
    if p.returncode == 0:
        (out_dir / "owner-questions.md").write_text(p.stdout, encoding="utf-8")
        found["owner_questions"] = "owner-questions.md"
    else:
        found["owner_questions"] = None
    if session_id:
        p = deps.docker(["docker", "run", "--rm", "-v", f"{cfg_volume}:/cfg", "-w", "/cfg/projects", image, "sh", "-c",
                         transcripts_script(session_id)], capture_output=True)
        found["transcripts"] = _unpack(p, out_dir / "transcripts.tar", out_dir / "transcripts")
    p = deps.docker(["docker", "run", "--rm", "-v", f"{cfg_volume}:/cfg", "-w", "/cfg", image, "sh", "-c",
                     extras_script()], capture_output=True)
    found["cfg_extras"] = _unpack(p, out_dir / "cfg-extras.tar", out_dir / "cfg-extras")
    return found


def _unpack(p: subprocess.CompletedProcess, tar_path: Path, dest: Path) -> list[str] | None:
    """Keep a tar a collection script wrote, and unpack it beside itself; the member names, or None if it failed."""
    if p.returncode != 0 or not p.stdout:
        return None
    tar_path.write_bytes(p.stdout)
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(p.stdout)) as tf:
        names = sorted(m.name.removeprefix("./") for m in tf.getmembers() if m.isfile())
        tf.extractall(dest, filter="data")
    return names


def commit_map(deps: Deps, image: str, volume: str) -> str:
    """Commit whatever the session left, after "Start", as the LID arm's start commit."""
    script = (f"cd /work && git add -A && GIT_AUTHOR_DATE='{DATE}' GIT_COMMITTER_DATE='{DATE}' git -c user.name='{GIT_NAME}'"
              f" -c user.email='{GIT_EMAIL}' -c commit.gpgsign=false commit -q"
              " -m 'Map the codebase with /map-codebase (LID v1.4.6)' ; git rev-parse HEAD")
    return _run(deps, ["docker", "run", "--rm", "-v", f"{volume}:/work", image, "sh", "-c", script],
                what="committing the map").stdout.strip().splitlines()[-1]


def totals(u: usage.Usage | None) -> dict:
    if u is None:
        return {}
    t = u.total()
    return {"by_model": trajectory.usage_dict(u)["models"], "input": t.input, "output": t.output,
            "cache_read": t.cache_read, "cache_write": t.cache_write,
            "all_tokens": t.input + t.output + t.cache_read + t.cache_write, "reported_cost_usd": u.reported_cost_usd}


def run(args, deps: Deps) -> int:
    out = args.runs / "opengym-map" / args.id
    if (out / "mapping.json").exists():
        print(f"{out} already exists; a rerun starts from scratch under a new --id")
        return 2
    out.mkdir(parents=True, exist_ok=True)
    vols = volumes(args.id)
    isolation = executor.Isolation.for_public_seed(window=WINDOW)
    meta = {"id": args.id, "pin": PIN, "repo": str(args.repo), "omitted": list(OMIT), "image": args.image,
            "model": args.model, "effort": args.effort, "claude_code": CLAUDE_CODE, "lid_release": args.release,
            "plugins": list(PLUGINS), "isolation": isolation.record(), "window": WINDOW, "volumes": vols,
            "installs": [list(i) for i in INSTALLS], "round_cap": args.round_cap, "turn_timeout_s": args.turn_timeout,
            "prompts": {"first": FIRST_PROMPT, "continue": CONTINUE_PROMPT, "first_sha256": sha256_text(FIRST_PROMPT),
                        "continue_sha256": sha256_text(CONTINUE_PROMPT)},
            "started": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (out / "mapping.json").write_text(json.dumps(meta, indent=1))
    t0 = time.monotonic()
    meta["bare_start"] = prepare_workspace(deps, repo=args.repo, commit=PIN, image=args.image, volume=vols["workspace"])
    meta["prepare_minutes"] = round((time.monotonic() - t0) / 60, 1)
    repo = args.lid_repo or Path(subprocess.run(["git", "-C", str(HERE), "rev-parse", "--show-toplevel"],
                                                capture_output=True, text=True, check=True).stdout.strip())
    deps.install_lid(args.image, vols["config"], repo, args.release)
    (out / "mapping.json").write_text(json.dumps(meta, indent=1))
    session = executor.ContainerSession(image=args.image, workspace_volume=vols["workspace"],
                                        config_volume=vols["config"], model=args.model, claude_code_version=CLAUDE_CODE,
                                        expected_plugins=frozenset(PLUGINS), effort=args.effort,
                                        plugin_dirs=tuple(f"/cfg/lid/plugins/{p}" for p in PLUGINS),
                                        timeout_s=args.turn_timeout, isolation=isolation)
    if deps.turn_for is not None:
        turn = deps.turn_for(session)
    else:
        def turn(prompt, stream_path, *, resume=None):
            return executor.run_turn(session, prompt, stream_path, resume=resume)
    pace = deps.pace
    if pace is None:
        def pace():
            subprocess.run(["sh", str(HERE / "pace.sh")], check=False,
                           env={**os.environ, "PACE_LOG": str(out.parent / "pacing.log"),
                                "PACE_MARK": str(out.parent / ".pacing-unread")})
    t1 = time.monotonic()
    res = run_mapping(turn=turn, state=lambda: workspace_state(deps, args.image, vols["workspace"]),
                      loaded=lambda sid: skill_loaded(deps, args.image, vols["config"], sid), out_dir=out,
                      round_cap=args.round_cap, pace=pace)
    meta.update({"session_id": res.session_id, "stop": res.stop, "error": res.error, "skill_loaded": res.skill_loaded,
                 "turns": res.turns, "final_state": res.states[-1] if res.states else None,
                 "session_minutes": round((time.monotonic() - t1) / 60, 1),
                 "turn_minutes": round(sum(t["duration_s"] for t in res.turns) / 60, 1),
                 "totals": totals(res.cumulative), "collected": collect(deps, args.image, vols["config"],
                                                                         res.session_id, out)})
    if res.stop == "done":
        meta["lid_start"] = commit_map(deps, args.image, vols["workspace"])
    meta["finished"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (out / "mapping.json").write_text(json.dumps(meta, indent=1))
    tt = meta["totals"]
    print(f"{args.id}: {res.stop}, {len(res.turns)} turns, {meta['turn_minutes']} min in turns, "
          f"${(tt.get('reported_cost_usd') or 0):.2f} reported, lid_start {meta.get('lid_start')}", flush=True)
    return 0 if res.stop == "done" else 1


# ------------------------------------------------------------------------------------------------- checks


_COMMENT = re.compile(r"^\s*(//|#|/\*|\*|<!--|\{/\*|--|;)")


def is_annotation(line: str) -> bool:
    """A comment line that cites EARS IDs, or a blank line."""
    s = line.strip()
    return not s or (bool(_COMMENT.match(s)) and "@spec" in s)


def is_doc_path(path: str) -> bool:
    return path.startswith(DOC_PREFIXES) or path in DOC_FILES


def classify_diff(diff: str) -> dict:
    """From `git diff -U0 --no-color base head`: per changed file outside the map's own docs, the lines that aren't
    @spec annotations. A removed line that comes back with an @spec citation appended counts as an annotation."""
    files: dict[str, dict] = {}
    cur = None
    removed: list[str] = []
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            if cur is not None:
                files[cur]["other"] += [f"-{r}" for r in removed]
            m = re.match(r"diff --git a/(.*) b/(.*)", line)
            cur = m.group(2) if m else None
            if cur is not None:
                files[cur] = {"new": False, "deleted": False, "other": [], "annotations": 0}
            removed = []
        elif cur is None:
            continue
        elif line.startswith("new file mode"):
            files[cur]["new"] = True
        elif line.startswith("deleted file mode"):
            files[cur]["deleted"] = True
        elif line.startswith(("--- ", "+++ ", "index ", "similarity", "rename ", "old mode", "new mode")):
            continue
        elif line.startswith("@@"):
            files[cur]["other"] += [f"-{r}" for r in removed]
            removed = []
        elif line.startswith("-"):
            removed.append(line[1:])
        elif line.startswith("+"):
            added = line[1:]
            match = next((r for r in removed if added.startswith(r.rstrip()) and "@spec" in added[len(r.rstrip()):]), None)
            if match is not None:
                removed.remove(match)
                files[cur]["annotations"] += 1
            elif is_annotation(added):
                files[cur]["annotations"] += 1
            else:
                files[cur]["other"].append(f"+{added}")
    if cur is not None and removed:
        files[cur]["other"] += [f"-{r}" for r in removed]
    docs = sorted(p for p in files if is_doc_path(p))
    code = {p: f for p, f in files.items() if not is_doc_path(p)}
    return {"doc_files": docs, "code_files": sorted(code),
            "annotated_files": sorted(p for p, f in code.items() if f["annotations"] and not f["other"]),
            "non_annotation_edits": {p: f["other"][:20] for p, f in code.items() if f["other"]},
            "annotation_lines": sum(f["annotations"] for f in code.values())}


def check(args, deps: Deps) -> int:
    out = args.runs / "opengym-map" / args.id
    meta = json.loads((out / "mapping.json").read_text())
    vol = meta["volumes"]["workspace"]
    base, head = meta["bare_start"], meta["lid_start"]
    git = lambda *a: _run(deps, ["docker", "run", "--rm", "-v", f"{vol}:/work", "-w", "/work", args.image,  # noqa: E731
                                 "git", *a], what="git").stdout
    report = classify_diff(git("diff", "-U0", "--no-color", base, head))
    report["name_status"] = git("diff", "--name-status", base, head).splitlines()
    report["modified_existing"] = [ln.split("\t", 1)[1] for ln in report["name_status"] if ln.startswith("M\t")]
    report["deleted"] = [ln.split("\t", 1)[1] for ln in report["name_status"] if ln.startswith("D\t")]
    report["state"] = workspace_state(deps, args.image, vol)
    (out / "check.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({k: (v if not isinstance(v, list) or len(v) < 15 else f"{len(v)} entries") for k, v in report.items()
                      if k != "state"}, indent=1))
    return 0


# ------------------------------------------------------------------------------------------------- the suites


SUITES = (("api", "cd api && node --test test/*.test.js", 1800),
          ("frontend", "cd frontend && npx vitest run", 3600),
          ("mcp", "cd mcp && npm test", 600),
          ("zepp", "cd watch-zepp && node --test test/*.test.js", 600),
          ("routines", "node --test scripts/routines/routines.test.mjs", 600))  # CI's routines job; needs the media


def parse_counts(log: str) -> dict:
    """Pass, fail and skip counts from node --test's summary or vitest's (colour codes stripped first)."""
    log = re.sub(r"\x1b\[[0-9;]*m", "", log)
    out = {}
    for key in ("pass", "fail", "skipped", "todo", "cancelled"):  # TAP ("# pass 3") or the spec reporter ("ℹ pass 3")
        pat = rf"^(?:#|ℹ) {key} (\d+)"
        m = re.findall(pat, log, re.M)
        if m:
            out[key] = int(m[-1])
    m = re.findall(r"^\s*Tests\s+(.*)$", log, re.M)
    if m:
        for n, word in re.findall(r"(\d+) (passed|failed|skipped|todo)", m[-1]):
            out[{"passed": "pass", "failed": "fail", "skipped": "skipped", "todo": "todo"}[word]] = int(n)
    m = re.findall(r"^\s*Test Files\s+(.*)$", log, re.M)
    if m:
        out["files"] = m[-1].strip()
    return out


def test(args, deps: Deps) -> int:
    out = args.runs / "opengym-map" / args.id
    meta = json.loads((out / "mapping.json").read_text())
    ws, tv = meta["volumes"]["workspace"], meta["volumes"]["test"]
    results = json.loads((out / "tests.json").read_text()) if (out / "tests.json").exists() else {}
    labels = [(label, c) for label, c in (("lid", meta.get("lid_start")), ("bare", meta["bare_start"])) if c]
    only = set(filter(None, (args.only or "").split(",")))
    suites = [s for s in SUITES if not only or s[0] in only]
    for label, commit in labels:
        if args.label and label not in args.label.split(","):
            continue
        _run(deps, ["docker", "run", "--rm", "-v", f"{ws}:/src:ro", "-v", f"{tv}:/work", args.image, "sh", "-c",
                    f"find /work -mindepth 1 -delete && cp -a /src/. /work/ && cd /work && git checkout -q --detach {commit}"
                    " && git status --porcelain | head"], what=f"copying the {label} start")
        logs = out / "tests" / label
        logs.mkdir(parents=True, exist_ok=True)
        for name, cmd, timeout in suites:
            t0 = time.monotonic()
            try:
                p = deps.docker(["docker", "run", "--rm", "-v", f"{tv}:/work", "-w", "/work", args.image, "sh", "-c",
                                 f"{cmd} 2>&1"], capture_output=True, text=True, timeout=timeout)
                log, code = p.stdout, p.returncode
            except subprocess.TimeoutExpired as e:
                log, code = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or ""), "timeout"
            (logs / f"{name}.log").write_text(log, encoding="utf-8")
            results.setdefault(label, {})[name] = {"commit": commit, "exit": code, **parse_counts(log),
                                                   "minutes": round((time.monotonic() - t0) / 60, 1)}
            print(label, name, results[label][name], flush=True)
            (out / "tests.json").write_text(json.dumps(results, indent=1))
    return 0


def prepare(args, deps: Deps) -> int:
    """The bare arm's start alone: the workspace step of run, with no session, in <id>-ws."""
    out = args.runs / "opengym-map" / args.id
    if (out / "mapping.json").exists():
        print(f"{out} already exists")
        return 2
    out.mkdir(parents=True, exist_ok=True)
    vols = volumes(args.id)
    t0 = time.monotonic()
    start = prepare_workspace(deps, repo=args.repo, commit=PIN, image=args.image, volume=vols["workspace"])
    meta = {"id": args.id, "kind": "bare start", "pin": PIN, "repo": str(args.repo), "omitted": list(OMIT),
            "image": args.image, "volumes": vols, "installs": [list(i) for i in INSTALLS], "bare_start": start,
            "lid_start": None, "prepare_minutes": round((time.monotonic() - t0) / 60, 1),
            "finished": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    (out / "mapping.json").write_text(json.dumps(meta, indent=1))
    print(f"{args.id}: bare start {start} in {vols['workspace']}", flush=True)
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("run", "check", "test", "prepare"))
    ap.add_argument("--id", required=True, help="names the records folder and the volumes (<id>-ws, <id>-cfg)")
    ap.add_argument("--repo", type=Path, default=REPO)
    ap.add_argument("--image", default=IMAGE)
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--effort", default=EFFORT)
    ap.add_argument("--release", default=RELEASE)
    ap.add_argument("--lid-repo", type=Path, default=None)
    ap.add_argument("--round-cap", type=int, default=ROUND_CAP)
    ap.add_argument("--turn-timeout", type=int, default=TURN_TIMEOUT)
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    ap.add_argument("--only", help="test: suites to run (api,frontend,mcp,zepp)")
    ap.add_argument("--label", help="test: which starts (lid,bare)")
    return ap


def main(argv=None, *, deps: Deps | None = None) -> int:
    deps = deps or Deps()
    args = build_parser().parse_args(argv)
    return {"run": run, "check": check, "test": test, "prepare": prepare}[args.command](args, deps)


if __name__ == "__main__":
    sys.exit(main())
