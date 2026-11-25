"""Remove the Docker volumes of gradings whose results are already recorded, left by runs from before
grade_checkpoint.py released them itself (keeps_volumes, release_volumes there). A main trajectory's checkpoint
gradings (grading/change-NN) keep theirs, and the trajectories' workspaces are never touched.

    python3.12 release_volumes.py --ids g-bare-1 g-lid-full-1 g-checklist-1            # list what would go
    python3.12 release_volumes.py --ids g-bare-1 --keep-run g-lid-full-1/repair-forks/c10-RD-62 --apply

A grading counts as recorded when its verdicts.json has no error, or, for an earlier-mode grading (earlier-cNN), when
its earlier.json lists no failure. Gradings of a trajectory and of its course, reliance and repair forks are covered;
folders a redo set aside are left alone. --keep-run leaves one run's gradings (a trajectory or a fork) in place.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import grade_checkpoint as gck  # noqa: E402

FORK = re.compile(r"c\d{2}-(course|reliance)-\d+|c\d{2}-[A-Z]+-\d+[a-z]?")


def runs_of(runs: Path, trajectory_id: str) -> list[str]:
    """The trajectory and its forks, as grading ids."""
    out = [trajectory_id]
    for folder in ("course-forks", "repair-forks"):
        d = runs / trajectory_id / folder
        if d.exists():
            out += [f"{trajectory_id}/{folder}/{f.name}" for f in sorted(d.iterdir()) if f.is_dir() and FORK.fullmatch(f.name)]
    return out


def recorded(gdir: Path) -> int | None:
    """The change a recorded grading graded, or None while it isn't recorded."""
    v, e = gdir / "verdicts.json", gdir / "earlier.json"
    if v.exists():
        d = json.loads(v.read_text())
        return None if d.get("error") or d.get("change") is None else int(d["change"])
    m = re.fullmatch(r"earlier-c(\d+)", gdir.name)
    if m and e.exists() and not json.loads(e.read_text()).get("failed"):
        return int(m.group(1))
    return None


def main(argv=None, *, runner: Callable = subprocess.run) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", nargs="+", required=True)
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    ap.add_argument("--keep-run", action="append", default=[], help="a run whose gradings keep their volumes")
    ap.add_argument("--apply", action="store_true", help="remove them (default: list them)")
    args = ap.parse_args(argv)
    for tid in args.ids:
        for rid in runs_of(args.runs, tid):
            if rid in args.keep_run:
                continue
            for gdir in sorted((args.runs / rid / "grading").glob("*/")):
                change = recorded(gdir)
                if change is None or gck.keeps_volumes(rid, gdir.name, change):
                    continue
                if args.apply:
                    names = gck.release_volumes(rid, gdir.name, change, runner=runner)
                else:
                    ckpt = gck.ckpt_volume(rid, gdir.name, change)
                    names = [ckpt, ckpt[: -len("ckpt")] + "tools"]
                print(("removed " if args.apply else "would remove ") + " ".join(names))
    return 0


if __name__ == "__main__":
    sys.exit(main())
