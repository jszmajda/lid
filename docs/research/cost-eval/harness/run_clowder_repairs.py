"""Repair forks for run_fork.py's forks (plan.md, M2f on Clowder variants and M2h on openGym's named starts; the
growth test's repair forks, costeval/repair.py): what it costs to fix a miss, and whether the fix holds without breaking
what the fork kept.

    python3.12 run_clowder_repairs.py plan --forks 'm2f-*'
    ../plumbing/with-token.sh python3.12 run_clowder_repairs.py run --of m2f-full-lid-full-c13-r1 --item CLX-1302
    python3.12 grade_rust.py --id m2f-full-lid-full-c13-r1-fix-CLX-1302 ...            # graded like any fork
    python3.12 run_clowder_repairs.py record --of m2f-full-lid-full-c13-r1 --item CLX-1302
    python3.12 run_clowder_repairs.py release --forks 'm2f-*'

plan prints "<fork> <item>" for every miss of each graded fork the glob names (never a repair fork): each of the
change's rows its grading has as not met, and DEP-NN when one of the change's dependency probes ran and failed
(dependency_met false, or grade_node's dependency broken; once, by that verdict: grade_node's per-build DEP-NN row
plans nothing of its own; a dependency left undecided because a probe is missing plans no repair). Only one run of a
repair goes at a time (a lock under ../runs/.locks/; a second stops before it touches anything). run forks
from that fork's own result: its workspace copied as it stands (its last commit is the change's result, and a jj
repository keeps its history), a fresh configuration with the arm's setup, and the fork's owner as it stood after its
change; one fresh session opens with the owner's repair report for the item (repair-reports.json in --seed-files: the
row's report, or DEP-NN's for the dependency), and the owner answers as in any change. The repair fork is graded with
grade_rust.py like any fork (its trajectory.json names the same variant set). record compares that grading with the
fork's: fixed is the row met (for DEP-NN, dependency_met: every dependency probe ran and passed; undetermined when
one is missing); keeping lists the fork's other rows met before and not met now, its held-out tests that passed and
now fail (the pilot's held-out files, and the graded held-out copies), and its dependency probes that passed and now
fail, with those that passed and are now missing (not built, not run, a settled precondition) apart as undetermined;
with cost, turns, model calls, wall time and files read (costeval/rot_cost.py). Then the repair fork's volumes
go. release removes a fork's own volumes once every miss it has is repaired and recorded (or it has none; a null fork's,
once graded).

settle-test settles a test the record has as broken by its reruns alone: load-sensitive (every rerun passed), so not
broken, or broken.

Records go to ../runs/<fork>-fix-<item>/ like a fork's (trajectory.json with "repair": {of, item}, change-NN/,
owner-state-NN.json, rot-cost.json, grading/), plus repair.json. A repair already recorded is left alone.

A repair takes everything else from the fork it repairs: its image (the Node executor image for M2h), its isolation and
npm setting, its arm (for M2h's LID arm, both plugins installed fresh and checked against the fork's own LID tree hash),
and its volume naming (ce-<id>-* for a Clowder fork, <id>-* for a named start's, so an M2h repair's are
m2h-...-fix-<item>-ws and -cfg). Its seed must be the fork's: --brief defaults to the brief the fork recorded and
--seed-files to the folder of the fork's oracle, and a brief, oracle or owner-items file that hashes otherwise than the
fork's record stops the repair before anything runs. For M2h, --seed-files is seeds/opengym/hidden/m2h/ (the converted
seed with its repair-reports.json) and grading is grade_node.py's.
"""

from __future__ import annotations

import argparse
import fcntl
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
from costeval import executor, repair, rot_cost, rust_grading, simulator, trajectory  # noqa: E402
from run_trajectory import CLAUDE_CODE, owner_model_from_arg, sha256  # noqa: E402

FIX = "-fix-"
SEED_FILES = HERE.parent / "seeds" / "clowder" / "hidden" / "m2f"
BRIEF = HERE.parent / "seeds" / "clowder" / "brief.md"


def fix_id(fork: str, item: str) -> str:
    return f"{fork}{FIX}{item}"


def _json(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def _grading(runs: Path, fid: str) -> tuple[dict | None, dict | None]:
    meta = _json(runs / fid / "trajectory.json") or {}
    g = runs / fid / "grading" / f"change-{int(meta.get('change', 0)):02d}"
    return _json(g / "summary.json"), _json(g / "keeping.json")


def report_text(reports: dict, item: str) -> str | None:
    """An item's repair report; a dependency's is found under its change number however it is written (DEP-01, DEP-1)."""
    text = repair.report_for(reports, item)
    if text is None and item.startswith("DEP-") and item[4:].isdigit():
        text = repair.report_for(reports, f"DEP-{int(item[4:])}")
    return text


def misses(summary: dict, change: int) -> list[str]:
    """The rows a fork's grading has as not met, and DEP-NN when its dependency probes didn't all pass. A DEP-NN row
    among the items (grade_node.py's per-build dependency probe) plans nothing of its own: the dependency is planned
    once, by its verdict."""
    out = sorted(i for i, v in (summary.get("items") or {}).items() if v == "not met" and not i.startswith("DEP-"))
    node_dep = (summary.get("dependency") or {}).get("result") if isinstance(summary.get("dependency"), dict) else None
    if summary.get("dependency_met") is False or node_dep == "broken":  # grade_rust's, or grade_node's (M2h)
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


def repair_lock_path(runs: Path, fid: str) -> Path:
    return runs / ".locks" / f"{fid}.lock"


def run_one(args, deps: rf.Deps) -> int:
    """One repair, while no other run of it holds its lock: two at once would copy into one volume and write one
    record, each undoing the other's."""
    lock_path = repair_lock_path(args.runs, fix_id(args.of, args.item))
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(f"{fix_id(args.of, args.item)} is already running", file=sys.stderr)
            return 2
        try:
            return _run_one(args, deps)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _run_one(args, deps: rf.Deps) -> int:
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
    recorded = arm_meta.get("paths") or {}
    seed_files = args.seed_files or (Path(recorded["oracle"]).parent if recorded.get("oracle") else SEED_FILES)
    reports_path = seed_files / repair.REPORTS
    text = report_text(_json(reports_path) or {}, args.item)
    if text is None:
        print(f"no repair report for {args.item} in {reports_path}", file=sys.stderr)
        return 2
    oracle_path, script_path, items_path = (seed_files / "oracle.md", seed_files / "change-script.md",
                                            seed_files / "owner-items.json")
    brief_path = args.brief or (Path(recorded["brief"]) if recorded.get("brief") else BRIEF)
    for name, path in (("brief", brief_path), ("oracle", oracle_path), ("owner_items", items_path)):
        want = (arm_meta.get("hashes") or {}).get(name)
        if want and sha256(path) != want:
            print(f"{args.of} ran with another {name} than {path} ({want[:12]}, not {sha256(path)[:12]}); a repair "
                  "runs with its fork's own seed", file=sys.stderr)
            return 2
    oracle = simulator.parse_oracle(oracle_path.read_text(encoding="utf-8"))
    owner_items = simulator.load_owner_items(items_path, oracle)
    brief = brief_path.read_text(encoding="utf-8")
    state_path = args.runs / args.of / f"owner-state-{n:02d}.json"
    arm = trajectory.load_arm(arm_meta["arm"])
    window = arm_meta.get("window") or "1m"
    npm_network = arm_meta.get("npm_network", True)
    isolation = rf.isolation_for(window, isolate=not args.no_isolate, npm_network=npm_network)
    image = arm_meta.get("image") or rf.IMAGE
    named = rf.is_named_start(arm_meta.get("fork_of"))
    ws_vol, cfg_vol = rf.fork_volumes(fid, named)
    if meta_path.exists():
        import shutil
        shutil.rmtree(out)  # a repair that stopped partway runs again from its start

    # the fork's workspace as it stands: its HEAD is the change's result (checked), its jj history kept
    rf._run(deps, ["docker", "run", "--rm", "-v", f"{arm_meta['volumes']['workspace']}:/src:ro", "-v", f"{ws_vol}:/work",
                   image, "sh", "-c", f"find /work -mindepth 1 -delete && cp -a /src/. /work/ && cd /work && "
                   f"test \"$(git rev-parse HEAD)\" = '{done['commit']}'"], what="copying the fork's workspace")
    lid_tree = None
    if arm.lid_release:
        repo = args.lid_repo or Path(subprocess.run(["git", "-C", str(HERE), "rev-parse", "--show-toplevel"],
                                                    capture_output=True, text=True, check=True).stdout.strip())
        deps.install_lid(image, cfg_vol, repo, arm.lid_release)
        if named:  # the same LID tree as the fork it repairs
            lid_tree = rf.check_lid_tree(deps.docker, image, cfg_vol, arm_meta.get("lid_install_sha256"))
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
            "replicate": replicate, "isolation": isolation.record(), "npm_network": npm_network,
            **({"lid_install_sha256": lid_tree} if lid_tree is not None else {}),
            "paths": {"brief": str(brief_path.resolve()), "oracle": str(oracle_path.resolve()),
                      "change_script": str(script_path.resolve()), "owner_items": str(items_path.resolve()),
                      "repair_reports": str(reports_path.resolve())},
            "hashes": {"brief": sha256(brief_path), "oracle": sha256(oracle_path), "change_script": sha256(script_path),
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
        if not named:
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


def _dependency_fixed(summary: dict):
    """grade_node.py (M2h): the dependency kept is fixed, broken is not, anything else undetermined."""
    r = (summary.get("dependency") or {}).get("result")
    return True if r == "kept" else False if r == "broken" else None


def _dependency_change(before: dict, after: dict) -> tuple[list[str], list[str]]:
    """grade_node.py (M2h): (broken, undetermined): the dependency probes kept before and broken after, and those kept
    before and neither kept nor broken after."""
    was = {t: (r or {}).get("result") for t, r in ((before.get("dependency") or {}).get("probes") or {}).items()}
    now = {t: (r or {}).get("result") for t, r in ((after.get("dependency") or {}).get("probes") or {}).items()}
    kept = [t for t, r in sorted(was.items()) if r == "kept"]
    return [t for t in kept if now.get(t) == "broken"], [t for t in kept if now.get(t) not in ("kept", "broken")]


def _broken_tests(before: dict | None, after: dict | None) -> list[str]:
    """Keeping tests that broke: grade_rust's targets that passed and don't, or grade_node's failures (each against
    the start's baseline) on the repair that weren't failures on the fork."""
    if (after or {}).get("failures") is not None or (before or {}).get("failures") is not None:
        return sorted(set((after or {}).get("failures") or {}) - set((before or {}).get("failures") or {}))
    return sorted(_ok_tests(before) - _ok_tests(after))


def _ok_tests(keeping: dict | None) -> set[str]:
    return {t for target in ((keeping or {}).get("targets") or {}).values()
            for t, r in (target.get("tests") or {}).items() if r == "ok"}


def _graded_change(before: dict, after: dict, key: str) -> tuple[list[str], list[str]]:
    """(broken, undetermined): the graded targets' tests (grade_rust.py: dependency_probes, held_out_tests) that passed
    before and failed after, and those that passed before and are missing after (rust_grading.graded_outcome)."""
    kind = rust_grading.DEPENDENCY_PROBE if key == "dependency_probes" else rust_grading.HELD_OUT_TEST
    was = {t: rust_grading.graded_outcome(r, kind) for t, r in (before.get(key) or {}).items()}
    now = {t: rust_grading.graded_outcome(r, kind) for t, r in (after.get(key) or {}).items()}
    passed = [t for t, o in sorted(was.items()) if o == "passed"]
    return [t for t in passed if now.get(t) == "failed"], [t for t in passed if now.get(t) not in ("passed", "failed")]


def trim_vm() -> None:
    """Give removed volumes' space back to macOS (trim.sh): Colima's disk image shrinks only once trimmed."""
    subprocess.run(["sh", str(HERE / "trim.sh")], capture_output=True)


def record(args, docker: Callable, trim: Callable = trim_vm) -> int:
    fid = fix_id(args.of, args.item)
    meta = _json(args.runs / fid / "trajectory.json") or {}
    n = int(meta.get("change") or 0)
    fixed_summary, fixed_keeping = _grading(args.runs, fid)
    arm_summary, arm_keeping = _grading(args.runs, args.of)
    if fixed_summary is None or arm_summary is None:
        print(f"{fid}: {'the repair' if fixed_summary is None else 'the fork'} isn't graded yet")
        return 1
    node = isinstance(fixed_summary.get("dependency"), dict)  # grade_node.py's summary (M2h)
    if args.item.startswith("DEP-"):
        fixed = _dependency_fixed(fixed_summary) if node else fixed_summary.get("dependency_met")
    else:
        v = (fixed_summary.get("items") or {}).get(args.item)
        fixed = True if v == "met" else False if v == "not met" else None
    before_items = {i for i, v in (arm_summary.get("items") or {}).items() if v == "met" and i != args.item}
    after_items = fixed_summary.get("items") or {}
    done = (meta.get("changes") or {}).get(str(n)) or {}
    rec = {"of": args.of, "run": fid, "change": n, "item": args.item, "fixed": fixed,
           "keeping": {"items_broken": sorted(i for i in before_items if after_items.get(i) == "not met"),
                       "items_undetermined": sorted(i for i in before_items if after_items.get(i) not in ("met", "not met")),
                       "tests_broken": _broken_tests(arm_keeping, fixed_keeping),
                       **({f"dependency_probes_{what}": tests for what, tests in
                           zip(("broken", "undetermined"), _dependency_change(arm_summary, fixed_summary))} if node else
                          {f"{key}_{what}": tests
                           for key in ("dependency_probes", "held_out_tests")
                           for what, tests in zip(("broken", "undetermined"),
                                                  _graded_change(arm_summary, fixed_summary, key))})},
           "start_commit": meta.get("start_commit"), "commit": done.get("commit"),
           "agent_cost_usd": done.get("agent_cost_usd"), "owner_cost_usd": done.get("owner_cost_usd"),
           "rounds": done.get("rounds"), "minutes": done.get("minutes"),
           "measures": rot_cost.measures(args.runs / fid, write=True)}
    (args.runs / fid / "repair.json").write_text(json.dumps(rec, indent=1))
    _remove_volumes(docker, fid, meta)
    trim()
    print(f"{fid}: {'fixed' if fixed else 'not fixed' if fixed is False else 'undetermined'}; "
          f"broke {len(rec['keeping']['items_broken'])} rows, {len(rec['keeping']['tests_broken'])} tests, "
          f"{len(rec['keeping']['dependency_probes_broken'])} dependency probes")
    return 0


def settle_test(args) -> int:
    """A test the record has as broken, rerun alone (--results, each rerun's status in order): load-sensitive, not
    broken, when every rerun passed; broken otherwise. Both kept under keeping.tests_rerun."""
    path = args.runs / fix_id(args.of, args.item) / "repair.json"
    rec = _json(path)
    k = (rec or {}).get("keeping") or {}
    if args.test not in (k.get("tests_broken") or []):
        print(f"{path}: {args.test} isn't among its broken tests", file=sys.stderr)
        return 2
    results = [x.strip() for x in args.results.split(",") if x.strip()]
    settled = "load-sensitive" if results and all(x == "passed" for x in results) else "broken"
    k.setdefault("tests_rerun", []).append({"test": args.test, "reruns": results, "settled": settled})
    if settled == "load-sensitive":
        k["tests_broken"] = [t for t in k["tests_broken"] if t != args.test]
        k.setdefault("tests_load_sensitive", []).append({"test": args.test, "reruns": results})
    rec["keeping"] = k
    path.write_text(json.dumps(rec, indent=1))
    print(f"{fix_id(args.of, args.item)}: {args.test}: {settled} ({', '.join(results)})")
    return 0


def _remove_volumes(docker: Callable, fid: str, meta: dict) -> None:
    """A fork's own volumes, as its record names them (else by its naming: ce-<id>-* for Clowder, <id>-* for a named
    start's); never a start's, which no fork records as its own."""
    ws, cfg = rf.fork_volumes(fid, rf.is_named_start(meta.get("fork_of")))
    vols = meta.get("volumes") or {}
    docker(["docker", "volume", "rm", "-f", vols.get("workspace", ws), vols.get("config", cfg)], capture_output=True,
           text=True)


def release(args, docker: Callable, trim: Callable = trim_vm) -> int:
    """A graded fork's volumes go once every miss it has is repaired and recorded; the VM's disk is trimmed after."""
    removed = False
    for fid in forks(args.runs, args.forks):
        meta = _json(args.runs / fid / "trajectory.json")
        summary, _ = _grading(args.runs, fid)
        if summary is None:
            continue
        left = [] if meta.get("arm") == "null" else [
            i for i in misses(summary, int(meta["change"])) if not (args.runs / fix_id(fid, i) / "repair.json").exists()]
        if left:
            continue
        _remove_volumes(docker, fid, meta)
        removed = True
        print(f"{fid}: volumes removed")
    if removed:
        trim()
    return 0


def main(argv=None, *, deps: rf.Deps | None = None, docker: Callable = subprocess.run, trim: Callable | None = None) -> int:
    if trim is None:  # the real trim with real Docker; a stand-in Docker (tests) trims nothing unless given one
        trim = trim_vm if docker is subprocess.run else (lambda: None)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=("plan", "run", "record", "release", "settle-test"))
    ap.add_argument("--test", help="settle-test: the test id the record has as broken")
    ap.add_argument("--results", help="settle-test: each rerun's status, in order (passed,failed,...)")
    ap.add_argument("--forks", help="plan, release: a glob of fork ids under --runs")
    ap.add_argument("--of", help="run, record: the fork repaired")
    ap.add_argument("--item", help="run, record: the missed row, or DEP-NN for the change's dependency")
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    ap.add_argument("--seed-files", type=Path, default=None,
                    help="oracle.md, change-script.md, owner-items.json and repair-reports.json (default: the folder of "
                         "the fork's recorded oracle, else seeds/clowder/hidden/m2f; M2h: seeds/opengym/hidden/m2h)")
    ap.add_argument("--brief", type=Path, default=None,
                    help="default: the brief the fork recorded, else seeds/clowder/brief.md")
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
        return record(args, docker, trim)
    if args.what == "settle-test":
        return settle_test(args)
    return release(args, docker, trim)


if __name__ == "__main__":
    sys.exit(main())
