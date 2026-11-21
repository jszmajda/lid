"""Repair forks for the growth test (plan.md, M2e; costeval/repair.py): what fixing a missed latent rule costs, and
whether the fix holds without breaking other rules.

    python3.12 run_repair_forks.py plan --ids g-bare-1 g-lid-full-1 g-checklist-1 --checkpoints 10 20
    ../plumbing/with-token.sh python3.12 run_repair_forks.py run --id g-bare-1 --at 10 --item RD-42
    ../plumbing/with-token.sh python3.12 run_repair_forks.py grade --id g-bare-1 --at 10 --item RD-42

plan prints "<id> <checkpoint> <item>" for each latent item (any kind but stated) a checkpoint's grading has as not met;
an item with no repair report yet is listed still, and named on stderr. run forks from the trajectory's snapshot after
that checkpoint's change, with its owner as it stood there, and runs one fresh session opened by the owner's repair
report for the item (the seed's hidden/repair-reports.json); the owner answers as in any change. A repair report for a
row realized on a symptom is that symptom, so the owner holds the row from then on, as if its report had been
delivered on the main line. grade regrades the fork in full at the checkpoint's change (every probe in force there),
records whether the item was fixed and whether every other item met at the checkpoint is still met, and removes the
fork's volumes.

Records go under the trajectory, ../runs/<id>/repair-forks/cNN-<item>/: trajectory.json (kind "repair", the item, the
checkpoint, the commit and costs), change-repair/ (its turns and owner records), owner-state-repair.json, rot-cost.json
(cost, turns, model calls, wall time, files read: costeval/rot_cost.py), grading/repair/, and repair.json. A fork
already recorded, or already graded, is left alone.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import report  # noqa: E402
import run_course_forks as rcf  # noqa: E402
from costeval import grading, repair, rot_cost, simulator  # noqa: E402
from costeval.repair import load_reports, report_for  # noqa: E402,F401  (for callers)

PY = sys.executable
FOLDER = "repair-forks"


def name(at: int, item: str) -> str:
    return f"c{at:02d}-{item}"


def tag(at: int, item: str) -> str:
    return f"repair{at:02d}-{item.lower()}"


def fork_dir(runs: Path, trajectory_id: str, at: int, item: str) -> Path:
    return runs / trajectory_id / FOLDER / name(at, item)


def _seed(runs: Path, trajectory_id: str, seed_dir: Path | None) -> Path:
    if seed_dir:
        return seed_dir
    return HERE.parent / "seeds" / json.loads((runs / trajectory_id / "trajectory.json").read_text())["seed"]


def _probes(seed_dir: Path) -> list[grading.Probe]:
    return grading.parse_probes((seed_dir / "hidden" / "probes.md").read_text(encoding="utf-8")).probes


def _oracle(seed_dir: Path) -> simulator.Oracle:
    return simulator.parse_oracle((seed_dir / "hidden" / "oracle.md").read_text(encoding="utf-8"))


def misses(runs: Path, seed_dir: Path, trajectory_id: str, c: int) -> list[str] | None:
    """The latent items checkpoint c's grading has as not met; None when that checkpoint hasn't been graded."""
    items = repair.item_verdicts(runs / trajectory_id / "grading" / f"change-{c:02d}", _probes(seed_dir))
    return None if items is None else repair.latent_misses(items, _oracle(seed_dir))


def plan(args) -> int:
    for tid in args.ids:
        seed_dir = args.seed_dir or _seed(args.runs, tid, None)
        reports = load_reports(seed_dir)
        for c in args.checkpoints:
            for item in misses(args.runs, seed_dir, tid, c) or []:
                print(f"{tid} {c} {item}")
                if report_for(reports, item) is None:
                    print(f"{tid} at {c}: no repair report for {item} yet", file=sys.stderr)
    return 0


def run_one(args, deps: rcf.Deps) -> int:
    seed_dir = _seed(args.runs, args.id, args.seed_dir)
    text = report_for(load_reports(seed_dir), args.item)
    if text is None:
        print(f"no repair report for {args.item} in {seed_dir / 'hidden' / repair.REPORTS}", file=sys.stderr)
        return 2
    script = simulator.parse_change_script((seed_dir / "hidden" / "change-script.md").read_text(encoding="utf-8"))
    change = simulator.Change(number=args.at, title=f"Repair report for {args.item} after change {args.at}", request=text,
                              relies_on=simulator.ALL, probe=True)

    def prepare(owner: simulator.Owner, oracle: simulator.Oracle) -> None:
        """A report of a symptom row's wrong behaviour is its symptom: the owner holds the row from here on."""
        held = owner.realized
        if held is None or args.item not in simulator.symptom_items(oracle) or args.item in held:
            return
        n = next(i.in_force for i in oracle.items if i.id == args.item)
        said = (script.get(n).symptom if script.get(n) else None) or text
        owner.requests = sorted([*owner.requests, (n, said)], key=lambda r: r[0])

    return rcf.run_fork(deps, runs=args.runs, trajectory_id=args.id, kind="repair", change=change, at=args.at, key="repair",
                        folder=FOLDER, name=name(args.at, args.item), tag=tag(args.at, args.item), fork=1,
                        seed_dir=seed_dir, lid_repo=args.lid_repo, no_isolate=args.no_isolate,
                        meta_extra={"item": args.item, "course": None, "at": args.at, "lag": None}, prepare_owner=prepare)


def grade(args, run: Callable[[list[str]], int]) -> int:
    fork = fork_dir(args.runs, args.id, args.at, args.item)
    fid = f"{args.id}/{FOLDER}/{fork.name}"
    meta = json.loads((fork / "trajectory.json").read_text()) if (fork / "trajectory.json").exists() else {}
    done = (meta.get("changes") or {}).get("repair")
    if not done:
        print(f"{fid} hasn't run to its record")
        return 2
    if (fork / "repair.json").exists():
        print(f"{fid} already graded")
        return 0
    seed_dir = _seed(args.runs, args.id, args.seed_dir)
    probes = _probes(seed_dir)
    where = fork / "grading" / "repair"
    if repair.item_verdicts(where, probes) is None:  # a full regrade at the checkpoint's change: no --probes
        run([PY, "grade_checkpoint.py", "--id", fid, "--change", str(args.at), "--seed", meta["seed"],
             "--commit", done["commit"], "--out-name", "repair"])
    after = repair.item_verdicts(where, probes)
    if after is None:
        print(f"{fid}: the regrade left no verdicts; it runs again next time")
        return 1
    before = repair.item_verdicts(args.runs / args.id / "grading" / f"change-{args.at:02d}", probes) or {}
    item = next((i for i in _oracle(seed_dir).items if i.id == args.item), None)
    graded = json.loads((where / "verdicts.json").read_text()).get("commit")
    rec = {"trajectory": args.id, "run": fid, "at": args.at, "item": args.item,
           "kind": report.kind_of(item) if item else None, **repair.outcome(before, after, args.item), "regrade": "full",
           # where the fork started, the commit the harness made of the agent's working tree, and the one graded
           "start_commit": meta.get("commit"), "commit": done["commit"], "graded_commit": graded,
           "agent_cost_usd": done.get("agent_cost_usd"), "owner_cost_usd": done.get("owner_cost_usd"),
           "measures": rot_cost.measures(fork, write=True)}
    (fork / "repair.json").write_text(json.dumps(rec, indent=1))
    run(["docker", "volume", "rm", "-f", *rcf.fork_volumes(args.id, tag(args.at, args.item), 1)])
    print(f"{fid}: {'fixed' if rec['fixed'] else 'not fixed' if rec['fixed'] is False else 'undetermined'}, "
          f"{len(rec['keeping']['broken'])} broken of {rec['keeping']['met_before']} kept")
    return 0


def main(argv=None, *, deps: rcf.Deps | None = None, run: Callable[[list[str]], int] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=("plan", "run", "grade"))
    ap.add_argument("--ids", nargs="+", help="plan: the trajectories")
    ap.add_argument("--checkpoints", nargs="+", type=int, default=[10, 20], help="plan: the checkpoints")
    ap.add_argument("--id", help="run, grade: the trajectory")
    ap.add_argument("--at", type=int, help="run, grade: the checkpoint whose snapshot the fork starts from")
    ap.add_argument("--item", help="run, grade: the missed item")
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    ap.add_argument("--seed-dir", type=Path, help="default: ../seeds/<the trajectory's seed>")
    ap.add_argument("--lid-repo", type=Path, default=None)
    ap.add_argument("--isolate", action="store_true", help="isolated (the default): GitHub's hosts blocked, web tools denied")
    ap.add_argument("--no-isolate", action="store_true", help="lift the isolation")
    args = ap.parse_args(argv)
    if args.what == "plan":
        return plan(args)
    if args.what == "run":
        return run_one(args, deps or rcf.Deps())
    return grade(args, run or (lambda cmd: subprocess.run(cmd, cwd=HERE).returncode))


if __name__ == "__main__":
    sys.exit(main())
