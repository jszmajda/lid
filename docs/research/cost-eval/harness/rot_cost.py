"""Write the working-around-rot records (costeval/rot_cost.py) for a trajectory's forks: each fork's own record where
it has none (forks run before run_course_forks.py wrote it), and the records joined with the stale-intent audit.

    python3.12 rot_cost.py --ids g-bare-1 g-lid-full-1 g-ref-correct

Makes no model calls: a fork's record comes from its trajectory.json, its change.json and its turns' transcripts.
Writes <fork>/rot-cost.json where it is missing, and ../runs/<id>/growth/rot-cost.json: every fork, the audit joined.
Folders a redo set aside (a suffix after the fork number) are left alone."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import rot_cost  # noqa: E402

FORK = re.compile(r"c\d{2}-(reliance|course)-\d+")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", nargs="+", required=True, help="trajectory ids under the runs folder")
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    args = ap.parse_args(argv)
    for tid in args.ids:
        forks = sorted(d for d in (args.runs / tid / "course-forks").glob("c*") if d.is_dir() and FORK.fullmatch(d.name))
        joined = []
        for fork in forks:
            if rot_cost.measures(fork, write=True) is None:
                print(f"{tid}/{fork.name}: no recorded change, no record")
                continue
            joined.append(rot_cost.record(fork))
        out = args.runs / tid / "growth" / "rot-cost.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(joined, indent=1))
        print(f"{tid}: {len(joined)} forks recorded, {sum(r['flagged_read'] is not None for r in joined)} with an audit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
