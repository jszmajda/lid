"""Convert openGym's M2h change set into the harness's seed files (plan.md, M2h: the brownfield test).

    python3.12 build_m2h_seed.py            (writes ../seeds/opengym/hidden/m2h/)
    python3.12 build_m2h_seed.py --check    (writes, then validates what it wrote)
    python3.12 build_m2h_seed.py --hidden <seed folder's hidden/> [--check]   (the seed material lives elsewhere)

Reads, from the hidden seed folder: m2h-changes.md (changes 1 to 12), m2h-guard-rows.json, and, when present,
m2h-plan.md (each change's signpost and the tier cross-check) and prompts-m2h/ (test-index.json, paths.json and
briefs-m2h.json, for checking citations, retired tests and each change's anchor row); and the owner's public brief,
../brief.md, which becomes the oracle's start section. Writes hidden/m2h/: change-script.md, oracle.md,
owner-items.json, repair-reports.json, kept-behaviour.json and guard-rows.json (costeval/m2h_seed.py says what each
holds). The tiers in owner-items.json come from hidden/m2h/salience.json ({"OGM-0102": "low|medium|high", ...}) when it
exists, and are otherwise a placeholder "medium". Rerun after editing a source.

--check then reads the written files with the harness's own parsers and checks: each change's **Introduces:** equals its
OGM rows; each fork (run_fork.py's fork scope, the start and that change only) releases exactly that change's rows, and
its owner's prompt shows no other change's; every askable row has a recall line naming no ID, and OGM-0405's condition
is recorded; every row, and the dependency row of every cross-component change, has a repair report; each
cross-component change's first kept row is its dependency row, with a precondition, and each control names a comparison
row with a precondition and a baseline witness, each citing what its brief's anchor row cites; every change has a
searchability tier matching the plan's; the guard rows agree with the changes' **Guard row:** lines and read as keep
rules; cited paths and test titles exist at the pin; and the counts (12 changes, 8 cross-component; 35 rows: 20 stated,
15 askable; 10 guard rows; 37 kept rows; 56 retired tests; the tiers). It also confirms run_fork.py's --oracle,
--change-script and --owner-items flags load these files for every change. It prints a summary, then every WARNING and
PROBLEM; it exits 1 on a problem.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import m2h_seed as ms  # noqa: E402


def check_run_fork(out_dir: Path) -> list[str]:
    """run_fork.py loading these files for every change (build_m2f_seed.py's check, which is seed-agnostic)."""
    try:
        from build_m2f_seed import check_run_fork as check
    except Exception as e:  # noqa: BLE001  (a module it imports may be mid-edit)
        return [f"can't import build_m2f_seed.py's run_fork check: {e!r}"]
    return check(out_dir)


def main(argv=None, *, expected: ms.Expected = ms.EXPECTED, run_fork_check: bool = True) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="validate the written files")
    ap.add_argument("--hidden", type=Path, default=ms.HIDDEN, help="the seed's hidden folder (default: %(default)s)")
    ap.add_argument("--brief", type=Path, default=None, help="the owner's brief (default: <hidden>/../brief.md)")
    ap.add_argument("--out", type=Path, default=None, help="where to write (default: <hidden>/m2h)")
    args = ap.parse_args(argv)
    out = args.out or args.hidden / ms.OUT
    try:
        src = ms.load_sources(args.hidden, brief=args.brief)
    except ValueError as e:
        print(f"PROBLEM: {e}")
        return 1
    try:
        files = ms.write_seed(src, out)
    except ValueError as e:
        print(f"PROBLEM: {ms.SOURCE} doesn't convert: {e}")
        return 1
    print(f"wrote {', '.join(sorted(files))} to {out}")
    brief = args.brief or args.hidden.parent / ms.BRIEF
    print(f"owner's brief: {brief} ({len(ms.brief_body(src.brief).split())} words)")
    if not args.check:
        return 0
    problems, warnings, summary = ms.check_seed(out, src, expected=expected)
    if run_fork_check and not problems:
        problems += check_run_fork(out)
    for line in summary:
        print(line)
    if run_fork_check and not problems:
        print("run_fork.py: --oracle, --change-script and --owner-items load these files for every change")
    for w in warnings:
        print("WARNING:", w)
    for p in problems:
        print("PROBLEM:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
