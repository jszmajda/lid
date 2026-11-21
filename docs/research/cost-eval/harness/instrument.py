#!/usr/bin/env python3
"""The instrument gate's gradings (design.md, "The trial, and its gate"), as the seed's reference-builds.md tables
them: R+ is g-ref-correct, and C's stale fork S_C is g-ref-stale-cNN.

    ../plumbing/with-token.sh python3.12 instrument.py course --course 11     # every grading course change 11 calls for
    ../plumbing/with-token.sh python3.12 instrument.py checkpoint --change 20  # every probe that applies to R+ at 20

For a course change C with flip probes (a retirement, reversal, re-reversal or rescope; a one-sided rescope has one
side), both sides' flip probes are graded on R+ after C-1 (grading/pair-cNN-before), on R+ after C (pair-cNN-after), and
on S_C after C+L (pair-cNN). For every course change, emerging ones included, the follow-up pair P-RRCC-current and
-displaced is graded on R+'s reliance fork and on S_C's (course-forks/cNN-reliance-1, grading/reliance), and each fork
is discarded once graded. A checkpoint grades R+ on every probe that applies there. Each grading already recorded is
left alone; report.py --instrument reads them all against the spec's expectations.
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

from costeval import reference  # noqa: E402

PY = sys.executable
CORRECT = "g-ref-correct"


def stale_id(course: int) -> str:
    return f"g-ref-stale-c{course:02d}"


def verdicts(path: Path) -> dict[str, str] | None:
    f = path / "verdicts.json"
    if not f.exists():
        return None
    data = json.loads(f.read_text())
    if data.get("error"):  # a grading that failed (extraction, setup) gave no verdicts: not done
        return None
    return {p: (v if isinstance(v, str) else v.get("verdict")) for p, v in (data.get("probes") or {}).items()}


def course_gradings(runs: Path, spec: dict, course: int) -> list[dict]:
    """Every grading course change C calls for: where (a run id and change, a commit for a fork), on which probes, under
    which name, and the trajectory whose fork to discard after."""
    checks, lag = spec["checks"][str(course)], spec["stale"][str(course)]["lag"]
    flips = checks["flip_old"] + checks["flip_new"]
    out = []
    if flips:
        out += [{"point": "R+ after C-1", "id": CORRECT, "change": course - 1, "name": f"pair-c{course:02d}-before", "probes": flips},
                {"point": "R+ after C", "id": CORRECT, "change": course, "name": f"pair-c{course:02d}-after", "probes": flips},
                {"point": "S_C after C+L", "id": stale_id(course), "change": course + lag, "name": f"pair-c{course:02d}",
                 "probes": flips}]
    for point, tid in (("R+ reliance fork", CORRECT), ("S_C reliance fork", stale_id(course))):
        f = runs / tid / "course-forks" / f"c{course:02d}-reliance-1" / "trajectory.json"
        done = ((json.loads(f.read_text()).get("changes") or {}).get("reliance") or {}) if f.exists() else {}
        out.append({"point": point, "id": f"{tid}/course-forks/c{course:02d}-reliance-1", "change": course + lag,
                    "name": "reliance", "probes": checks["rr"], "commit": done.get("commit"), "fork_of": tid})
    return out


def where(runs: Path, g: dict) -> Path:
    return runs / g["id"] / "grading" / g["name"]


def pending_course(runs: Path, spec: dict, course: int) -> bool:
    return any(verdicts(where(runs, g)) is None for g in course_gradings(runs, spec, course))


def pending_checkpoint(runs: Path, change: int) -> bool:
    return verdicts(runs / CORRECT / "grading" / f"change-{change:02d}") is None


def main(argv=None, *, run: Callable[[list[str]], int] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=("course", "checkpoint"))
    ap.add_argument("--course", type=int)
    ap.add_argument("--change", type=int)
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    ap.add_argument("--seed-dir", type=Path, default=None, help="default: the seed R+ ran on")
    args = ap.parse_args(argv)
    run = run or (lambda cmd: subprocess.run(cmd, cwd=HERE).returncode)
    seed = json.loads((args.runs / CORRECT / "trajectory.json").read_text())["seed"]
    seed_dir = args.seed_dir or HERE.parent / "seeds" / seed

    def grade(rid: str, n: int, *extra: str) -> int:
        return run([PY, "grade_checkpoint.py", "--id", rid, "--change", str(n), "--seed", seed, *extra])

    if args.what == "checkpoint":
        if pending_checkpoint(args.runs, args.change):
            return grade(CORRECT, args.change)
        return 0
    rc = 0
    for g in course_gradings(args.runs, reference.load_spec(seed_dir), args.course):
        if verdicts(where(args.runs, g)) is not None:
            continue
        if "fork_of" in g and not g["commit"]:
            print(f"{g['id']}: the fork hasn't run")
            rc = 1
            continue
        extra = ["--probes", ",".join(g["probes"]), "--out-name", g["name"]] + (["--commit", g["commit"]] if g.get("commit") else [])
        if grade(g["id"], g["change"], *extra) != 0:
            rc = 1
        elif "fork_of" in g:
            run([PY, "run_course_forks.py", "--id", g["fork_of"], "--kind", "reliance", "--course", str(args.course),
                 "--fork", "1", "--discard"])
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
