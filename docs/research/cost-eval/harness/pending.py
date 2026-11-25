#!/usr/bin/env python3
"""Whether a queued job still has work, so a runner waits at the pacing gate (pace.sh) only for a job that does.
Exits 0 when work is left, 1 when there is none.

    python3.12 pending.py batch --id g-bare-1 --changes 11,12,13      # a change not yet run to its end without error
    python3.12 pending.py fork --id g-bare-1 --kind reliance --course 11 --fork 1    # a fork not yet recorded
    python3.12 pending.py checkpoint --id g-bare-1 --change 20 [--steps grade,pairs,reliance]   # steps not done
    python3.12 pending.py control --id g-ref-correct --change 20      # the positive control's readers not summarized
    python3.12 pending.py gate --course 11 | --change 20              # an instrument gate grading not yet recorded
    python3.12 pending.py repair --id g-bare-1 --at 10 --item RD-42   # a repair fork not yet run and graded
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import growth_checkpoint
import instrument
import run_course_forks
import run_repair_forks
import run_trajectory

HERE = Path(__file__).resolve().parent


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=("batch", "fork", "checkpoint", "control", "gate", "repair"))
    ap.add_argument("--id", help="the trajectory (all but gate)")
    ap.add_argument("--seed-dir", type=Path, default=None, help="gate: the seed R+ ran on, by default")
    ap.add_argument("--changes", help="batch: comma-separated change numbers")
    ap.add_argument("--kind", choices=("course", "reliance"), help="fork")
    ap.add_argument("--course", type=int, help="fork or gate: the course change")
    ap.add_argument("--fork", help="fork: its number")
    ap.add_argument("--change", type=int, help="checkpoint or control: its change")
    ap.add_argument("--at", type=int, help="repair: the checkpoint the fork starts from")
    ap.add_argument("--item", help="repair: the missed item")
    ap.add_argument("--steps", default=",".join(growth_checkpoint.STEPS), help="checkpoint: the steps to have done")
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    args = ap.parse_args(argv)
    if args.what == "batch":
        f = args.runs / args.id / "trajectory.json"
        meta = json.loads(f.read_text()) if f.exists() else {}
        left = any(not run_trajectory.change_done(meta, int(n)) for n in args.changes.split(","))
    elif args.what == "fork":
        left = not run_course_forks.recorded(args.runs, args.id, args.kind, args.course, args.fork)
    elif args.what == "gate":
        if args.course is None:
            left = instrument.pending_checkpoint(args.runs, args.change)
        else:
            seed = json.loads((args.runs / instrument.CORRECT / "trajectory.json").read_text())["seed"]
            spec = instrument.reference.load_spec(args.seed_dir or HERE.parent / "seeds" / seed)
            left = instrument.pending_course(args.runs, spec, args.course)
    elif args.what == "repair":
        left = not (run_repair_forks.fork_dir(args.runs, args.id, args.at, args.item) / "repair.json").exists()
    elif args.what == "checkpoint":
        left = growth_checkpoint.pending(args.runs, args.id, args.change, steps=tuple(args.steps.split(",")))
    else:
        left = not (args.runs / "intent-from-tests" / f"pc-{args.id}-c{args.change:02d}" / "summary.json").exists()
    return 0 if left else 1


if __name__ == "__main__":
    raise SystemExit(main())
