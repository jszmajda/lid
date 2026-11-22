"""Repair forks for Clowder forks (plan.md, M2f; the growth test's repair forks, costeval/repair.py, on Clowder): what
it costs to fix a miss, and whether the fix holds without breaking what the fork kept.

    python3.12 run_clowder_repairs.py plan --forks 'm2f-*'
    ../plumbing/with-token.sh python3.12 run_clowder_repairs.py run --of m2f-full-lid-full-c13-r1 --item CLX-1302
    python3.12 grade_rust.py --id m2f-full-lid-full-c13-r1-fix-CLX-1302 ...            # graded like any fork
    python3.12 run_clowder_repairs.py record --of m2f-full-lid-full-c13-r1 --item CLX-1302
    python3.12 run_clowder_repairs.py release --forks 'm2f-*'

plan prints "<fork> <item>" for every miss of each graded fork the glob names (never a repair fork): each of the
change's rows its grading has as not met, and DEP-NN when the change's dependency probes didn't all pass. run forks
from that fork's own result: its workspace copied as it stands (its last commit is the change's result, and a jj
repository keeps its history), a fresh configuration with the arm's setup, and the fork's owner as it stood after its
change; one fresh session opens with the owner's repair report for the item (repair-reports.json in --seed-files: the
row's report, or DEP-NN's for the dependency), and the owner answers as in any change. The repair fork is graded with
grade_rust.py like any fork (its trajectory.json names the same variant set). record compares that grading with the
fork's: fixed is the row met (for DEP-NN, every dependency probe passing); keeping lists the fork's other rows met
before and not met now, its held-out tests that passed and now don't, and its dependency probes that passed and now
don't; with cost, turns, model calls, wall time and files read (costeval/rot_cost.py). Then the repair fork's volumes
go. release removes a fork's own volumes once every miss it has is repaired and recorded (or it has none; a null fork's,
once graded).

Records go to ../runs/<fork>-fix-<item>/ like a fork's (trajectory.json with "repair": {of, item}, change-NN/,
owner-state-NN.json, rot-cost.json, grading/), plus repair.json. A repair already recorded is left alone.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_fork as rf  # noqa: E402
from costeval import executor, repair, rot_cost, simulator, trajectory  # noqa: E402
from run_trajectory import CLAUDE_CODE, owner_model_from_arg, sha256  # noqa: E402

FIX = "-fix-"
SEED_FILES = HERE.parent / "seeds" / "clowder" / "hidden" / "m2f"


def fix_id(fork: str, item: str) -> str:
    return f"{fork}{FIX}{item}"


def _json(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def _grading(runs: Path, fid: str) -> tuple[dict | None, dict | None]:
    meta = _json(runs / fid / "trajectory.json") or {}
    g = runs / fid / "grading" / f"change-{int(meta.get('change', 0)):02d}"
    return _json(g / "summary.json"), _json(g / "keeping.json")


def misses(summary: dict, change: int) -> list[str]:
    """The rows a fork's grading has as not met, and DEP-NN when its dependency probes didn't all pass."""
    out = sorted(i for i, v in (summary.get("items") or {}).items() if v == "not met")
    if summary.get("dependency_met") is False:
        out.append(f"DEP-{change:02d}")
    return out


def forks(runs: Path, pattern: str) -> list[str]:
    """The graded-or-not arm forks a glob names: never a repair fork, nor a folder set aside."""
    out = []
    for d in sorted(runs.glob(pattern)):
        meta = _json(d / "trajectory.json")
        if d.is_dir() and meta and not meta.get("repair") and FIX not in d.name and fnmatch.fnmatchcase(d.name, pattern) \
                and "." not in d.name:
            out.append(d.name)
    return out


def plan(args) -> int:
    for fid in forks(args.runs, args.forks):
        meta = _json(args.runs / fid / "trajectory.json")
        summary, _ = _grading(args.runs, fid)
        if summary is None or meta.get("arm") == "null":  # the null arm's misses are the check, not something to repair
            continue
        for item in misses(summary, int(meta["change"])):
            print(f"{fid} {item}")
    return 0


def run_one(args, deps: rf.Deps) -> int:
    arm_meta = _json(args.runs / args.of / "trajectory.json")
    if not arm_meta:
        print(f"no fork {args.of}", file=sys.stderr)
        return 2
    n = int(arm_meta["change"])
    done = (arm_meta.get("changes") or {}).get(str(n)) or {}
    if not done.get("commit"):
        print(f"{args.of} hasn't recorded change {n}", file=sys.stderr)
        return 2
    fid = fix_id(args.of, args.item)
    out = args.runs / fid
    meta_path = out / "trajectory.json"
    if (_json(meta_path) or {}).get("changes", {}).get(str(n), {}).get("commit"):
        print(f"{fid} already recorded")
        return 0
    reports_path = args.seed_files / repair.REPORTS
    text = repair.report_for(_json(reports_path) or {}, args.item)
    if text is None:
        print(f"no repair report for {args.item} in {reports_path}", file=sys.stderr)
        return 2
    oracle_path, script_path, items_path = (args.seed_files / "oracle.md", args.seed_files / "change-script.md",
                                            args.seed_files / "owner-items.json")
    oracle = simulator.parse_oracle(oracle_path.read_text(encoding="utf-8"))
    owner_items = simulator.load_owner_items(items_path, oracle)
    brief = args.brief.read_text(encoding="utf-8")
    state_path = args.runs / args.of / f"owner-state-{n:02d}.json"
    arm = trajectory.load_arm(arm_meta["arm"])
    window = arm_meta.get("window") or "1m"
    isolation = (executor.Isolation(window=window) if args.no_isolate else executor.Isolation.for_public_seed(window=window))
    image = arm_meta.get("image") or rf.IMAGE
    ws_vol, cfg_vol = f"ce-{fid}-ws", f"ce-{fid}-cfg"
    if meta_path.exists():
        import shutil
        shutil.rmtree(out)  # a repair that stopped partway runs again from its start

    # the fork's workspace as it stands: its HEAD is the change's result (checked), its jj history kept
    rf._run(deps, ["docker", "run", "--rm", "-v", f"{arm_meta['volumes']['workspace']}:/src:ro", "-v", f"{ws_vol}:/work",
                   image, "sh", "-c", f"find /work -mindepth 1 -delete && cp -a /src/. /work/ && cd /work && "
                   f"test \"$(git rev-parse HEAD)\" = '{done['commit']}'"], what="copying the fork's workspace")
    if arm.lid_release:
        repo = args.lid_repo or Path(subprocess.run(["git", "-C", str(HERE), "rev-parse", "--show-toplevel"],
                                                    capture_output=True, text=True, check=True).stdout.strip())
        deps.install_lid(image, cfg_vol, repo, arm.lid_release)
    workspace = (deps.workspace_for or trajectory.DockerWorkspace)(image, ws_vol)
    change = simulator.Change(number=n, title=f"Repair report for {args.item} after change {n}", request=text,
                              relies_on=simulator.ALL, probe=True)
    owner_model = owner_model_from_arg(None) if not arm_meta.get("owner_model_config") else \
        simulator.OwnerModel.from_config(arm_meta["owner_model_config"])
    costs: list[float] = []
    ask, touch, trim, check = deps.ask, deps.touch, deps.trim, deps.check
    if ask is None:
        ask, touch, trim, check = rf._role_calls(arm_meta["owner_model"], costs)
    replicate = f"{arm_meta['replicate']}{FIX}{args.item}"
    owner = simulator.Owner(oracle=oracle, brief=brief, policy=arm_meta["policy"], replicate=replicate, ask=ask,
                            touch=touch, trim=trim, model=owner_model, owner_items=owner_items, only_change=True,
                            check=check)
    trajectory.restore_owner_state(owner, json.loads(state_path.read_text()))
    out.mkdir(parents=True, exist_ok=True)
    meta = {**{k: arm_meta.get(k) for k in ("fork_of", "arm", "seed", "change", "repeat", "model", "effort", "claude_code",
                                            "image", "policy", "owner_model", "owner_model_config", "window",
                                            "lid_release", "owner_scope", "round_cap", "neutral_sentence")},
            "id": fid, "repair": {"of": args.of, "item": args.item, "report_sha256": hashlib.sha256(text.encode()).hexdigest()},
            "replicate": replicate, "isolation": isolation.record(),
            "hashes": {"oracle": sha256(oracle_path), "change_script": sha256(script_path),
                       "owner_items": sha256(items_path), "repair_reports": sha256(reports_path)},
            "volumes": {"workspace": ws_vol, "config": cfg_vol}, "start_commit": done["commit"],
            "started": datetime.now(timezone.utc).isoformat(timespec="seconds"), "changes": {}}
    meta_path.write_text(json.dumps(meta, indent=1))
    session = executor.ContainerSession(image=image, workspace_volume=ws_vol, config_volume=cfg_vol,
                                        model=arm_meta["model"], claude_code_version=CLAUDE_CODE,
                                        expected_plugins=frozenset(arm.plugins), effort=arm_meta["effort"],
                                        plugin_dirs=arm.plugin_dirs, timeout_s=args.turn_timeout, isolation=isolation)
    if deps.turn_for is not None:
        turn = deps.turn_for(session)
    else:
        def turn(prompt, stream_path, *, resume=None, permission_mode="bypassPermissions"):
            return executor.run_turn(session, prompt, stream_path, resume=resume, permission_mode=permission_mode)
    start = time.monotonic()
    try:
        res = trajectory.run_change(arm=arm, change=change, owner=owner, turn=turn, workspace=workspace,
                                    out_dir=out / f"change-{n:02d}", round_cap=int(arm_meta.get("round_cap") or
                                                                                   trajectory.ROUND_CAP))
    finally:
        rf.clean_target(deps, image, ws_vol)
    agent_cost = sum((t["usage"] or {}).get("reported_cost_usd") or 0 for t in res.turns)
    meta["changes"][str(n)] = {"title": res.title, "rounds": res.rounds, "finished": res.finished, "capped": res.capped,
                               "error": res.error, "commit": res.commit, "redirect": res.redirect,
                               "agent_cost_usd": round(agent_cost, 4), "owner_cost_usd": round(sum(costs), 4),
                               "minutes": round((time.monotonic() - start) / 60, 1)}
    meta_path.write_text(json.dumps(meta, indent=1))
    state = json.dumps(trajectory.owner_state(owner), indent=1)
    (out / f"owner-state-{n:02d}.json").write_text(state)
    try:
        rot_cost.measures(out, write=True)
    except (OSError, ValueError, KeyError) as exc:
        print(f"{fid}: no cost record yet ({exc})")
    print(f"{fid}: rounds {res.rounds}, finished {res.finished}, agent ${agent_cost:.2f}, error {res.error}", flush=True)
    return 0 if not res.error else 1


def _ok_tests(keeping: dict | None) -> set[str]:
    return {t for target in ((keeping or {}).get("targets") or {}).values()
            for t, r in (target.get("tests") or {}).items() if r == "ok"}


def _passed_probes(summary: dict) -> set[str]:
    return {t for t, r in (summary.get("dependency_probes") or {}).items() if r.get("result") == "passed"}


def record(args, docker: Callable) -> int:
    fid = fix_id(args.of, args.item)
    meta = _json(args.runs / fid / "trajectory.json") or {}
    n = int(meta.get("change") or 0)
    fixed_summary, fixed_keeping = _grading(args.runs, fid)
    arm_summary, arm_keeping = _grading(args.runs, args.of)
    if fixed_summary is None or arm_summary is None:
        print(f"{fid}: {'the repair' if fixed_summary is None else 'the fork'} isn't graded yet")
        return 1
    if args.item.startswith("DEP-"):
        fixed = fixed_summary.get("dependency_met")
    else:
        v = (fixed_summary.get("items") or {}).get(args.item)
        fixed = True if v == "met" else False if v == "not met" else None
    before_items = {i for i, v in (arm_summary.get("items") or {}).items() if v == "met" and i != args.item}
    after_items = fixed_summary.get("items") or {}
    done = (meta.get("changes") or {}).get(str(n)) or {}
    rec = {"of": args.of, "run": fid, "change": n, "item": args.item, "fixed": fixed,
           "keeping": {"items_broken": sorted(i for i in before_items if after_items.get(i) == "not met"),
                       "items_undetermined": sorted(i for i in before_items if after_items.get(i) not in ("met", "not met")),
                       "tests_broken": sorted(_ok_tests(arm_keeping) - _ok_tests(fixed_keeping)),
                       "dependency_probes_broken": sorted(_passed_probes(arm_summary) - _passed_probes(fixed_summary))},
           "start_commit": meta.get("start_commit"), "commit": done.get("commit"),
           "agent_cost_usd": done.get("agent_cost_usd"), "owner_cost_usd": done.get("owner_cost_usd"),
           "rounds": done.get("rounds"), "minutes": done.get("minutes"),
           "measures": rot_cost.measures(args.runs / fid, write=True)}
    (args.runs / fid / "repair.json").write_text(json.dumps(rec, indent=1))
    vols = meta.get("volumes") or {}
    docker(["docker", "volume", "rm", "-f", vols.get("workspace", f"ce-{fid}-ws"), vols.get("config", f"ce-{fid}-cfg")],
           capture_output=True, text=True)
    print(f"{fid}: {'fixed' if fixed else 'not fixed' if fixed is False else 'undetermined'}; "
          f"broke {len(rec['keeping']['items_broken'])} rows, {len(rec['keeping']['tests_broken'])} tests, "
          f"{len(rec['keeping']['dependency_probes_broken'])} dependency probes")
    return 0


def release(args, docker: Callable) -> int:
    """A graded fork's volumes go once every miss it has is repaired and recorded."""
    for fid in forks(args.runs, args.forks):
        meta = _json(args.runs / fid / "trajectory.json")
        summary, _ = _grading(args.runs, fid)
        if summary is None:
            continue
        left = [] if meta.get("arm") == "null" else [
            i for i in misses(summary, int(meta["change"])) if not (args.runs / fix_id(fid, i) / "repair.json").exists()]
        if left:
            continue
        vols = meta.get("volumes") or {}
        docker(["docker", "volume", "rm", "-f", vols.get("workspace", f"ce-{fid}-ws"), vols.get("config", f"ce-{fid}-cfg")],
               capture_output=True, text=True)
        print(f"{fid}: volumes removed")
    return 0


def main(argv=None, *, deps: rf.Deps | None = None, docker: Callable = subprocess.run) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=("plan", "run", "record", "release"))
    ap.add_argument("--forks", help="plan, release: a glob of fork ids under --runs")
    ap.add_argument("--of", help="run, record: the fork repaired")
    ap.add_argument("--item", help="run, record: the missed row, or DEP-NN for the change's dependency")
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    ap.add_argument("--seed-files", type=Path, default=SEED_FILES,
                    help="oracle.md, change-script.md, owner-items.json and repair-reports.json")
    ap.add_argument("--brief", type=Path, default=HERE.parent / "seeds" / "clowder" / "brief.md")
    ap.add_argument("--lid-repo", type=Path, default=None)
    ap.add_argument("--turn-timeout", type=int, default=3600)
    ap.add_argument("--isolate", action="store_true", help="isolated (the default)")
    ap.add_argument("--no-isolate", action="store_true", help="don't block GitHub or deny web tools")
    args = ap.parse_args(argv)
    if args.what == "plan":
        return plan(args)
    if args.what == "run":
        return run_one(args, deps or rf.Deps())
    if args.what == "record":
        return record(args, docker)
    return release(args, docker)


if __name__ == "__main__":
    sys.exit(main())
