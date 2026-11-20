#!/usr/bin/env python3
"""Whether a queued job still has work, so a runner waits at the pacing gate (pace.sh) only for a job that does.
Exits 0 when work is left, 1 when there is none.

    python3.12 pending.py batch --id g-bare-1 --changes 11,12,13      # a change not yet run to its end without error
    python3.12 pending.py fork --id g-bare-1 --kind reliance --course 11 --fork 1    # a fork not yet recorded
    python3.12 pending.py checkpoint --id g-bare-1 --change 20        # a checkpoint not finished, or a fork it owes
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import growth_checkpoint
import run_course_forks
import run_trajectory

HERE = Path(__file__).resolve().parent


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=("batch", "fork", "checkpoint"))
    ap.add_argument("--id", required=True)
    ap.add_argument("--changes", help="batch: comma-separated change numbers")
    ap.add_argument("--kind", choices=("course", "reliance"), help="fork")
    ap.add_argument("--course", type=int, help="fork: the course change")
    ap.add_argument("--fork", help="fork: its number")
    ap.add_argument("--change", type=int, help="checkpoint: its change")
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    args = ap.parse_args(argv)
    if args.what == "batch":
        f = args.runs / args.id / "trajectory.json"
        meta = json.loads(f.read_text()) if f.exists() else {}
        left = any(not run_trajectory.change_done(meta, int(n)) for n in args.changes.split(","))
    elif args.what == "fork":
        left = not run_course_forks.recorded(args.runs, args.id, args.kind, args.course, args.fork)
    else:
        left = growth_checkpoint.pending(args.runs, args.id, args.change)
    return 0 if left else 1


if __name__ == "__main__":
    raise SystemExit(main())
