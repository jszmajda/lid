"""Convert the drafter's M2f change set into the Clowder harness's seed files (plan.md, M2f: cross-crate changes).

    python3.12 build_m2f_seed.py            (writes ../seeds/clowder/hidden/m2f/)
    python3.12 build_m2f_seed.py --check    (writes, then validates what it wrote)

Reads ../seeds/clowder/hidden/m2f-changes-r2.md (changes 13 to 24), the pilot oracle's start section and start items
(hidden/oracle.md), and the snapshot's test index (hidden/prompts-m2f/test-index.json, to expand "all N tests in a
file"), and writes hidden/m2f/: change-script.md, oracle.md, owner-items.json, repair-reports.json and
kept-behaviour.json (costeval/m2f_seed.py says what each holds). The tiers in owner-items.json come from
hidden/m2f/salience.json ({"CLX-1302": "low|medium|high", ...}) when it exists, and are otherwise a placeholder
"medium". Rerun after editing the source; the output depends on nothing else.

--check then reads the written files with the harness's own parsers and checks: each change's **Introduces:** equals its
CLX rows; each fork (run_fork.py's fork scope, the start and that change only) releases exactly the start items and that
change's rows, and its owner's prompt shows no other change's; every askable row has a recall line naming no ID; every
row, and the dependency row of every core change, has a repair report; each core change's first kept row is its
dependency row and cites what its brief (prompts-m2f/briefs-r2.json) requires; the counts (12 changes, 30 rows: 14
stated and 16 askable; 13 to 20 core); and that run_fork.py's --oracle, --change-script and --owner-items flags load
these files for every change, with no sidecar planted bug. It prints a summary, then every WARNING (placeholder tiers,
an owner-held row naming a requirement ID or code, an unindexed unit test) and PROBLEM; it exits 1 on a problem.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import m2f_seed as ms, simulator  # noqa: E402


def check_run_fork(out_dir: Path) -> list[str]:
    """Problems with run_fork.py loading these files: its flags, the loads its main() makes from the paths they give,
    and no planted bug (from the change script or a sidecar patch) for any change. No fork is run."""
    try:
        import run_fork
        from costeval import executor
    except Exception as e:  # noqa: BLE001  (a module run_fork imports may be mid-edit)
        return [f"can't import run_fork.py to confirm it loads these files: {e!r}"]
    paths = {"oracle": out_dir / "oracle.md", "change_script": out_dir / "change-script.md",
             "owner_items": out_dir / "owner-items.json"}
    problems = []
    script = simulator.parse_change_script(paths["change_script"].read_text(encoding="utf-8"))
    for n in sorted(script):
        argv = ["--variants", str(out_dir), "--variant", "plain", "--arm", "bare", "--change", str(n), "--repeat", "1",
                "--replicate", "r1", "--window", sorted(executor.WINDOWS)[0], "--oracle", str(paths["oracle"]),
                "--change-script", str(paths["change_script"]), "--owner-items", str(paths["owner_items"])]
        try:
            args = run_fork.build_parser().parse_args(argv)
        except SystemExit:
            return [f"run_fork.py's arguments refuse {' '.join(argv)}"]
        for name, path in paths.items():
            if getattr(args, name) != path:
                problems.append(f"run_fork.py reads --{name.replace('_', '-')} as {getattr(args, name)}, not {path}")
        oracle = simulator.parse_oracle(args.oracle.read_text(encoding="utf-8"))
        forked = simulator.parse_change_script(args.change_script.read_text(encoding="utf-8"))
        if args.change not in forked:
            problems.append(f"run_fork.py wouldn't find change {n} in {args.change_script}")
            continue
        simulator.load_owner_items(args.owner_items, oracle)
        bug = run_fork.planted_bug_path(args, forked[n], args.change_script)
        if bug is not None:
            problems.append(f"run_fork.py would plant {bug} in change {n}'s fork")
    return problems


def main(argv=None, *, expected: ms.Expected = ms.EXPECTED) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="validate the written files")
    ap.add_argument("--source", type=Path, default=ms.SOURCE)
    ap.add_argument("--pilot-oracle", type=Path, default=ms.PILOT_ORACLE)
    ap.add_argument("--test-index", type=Path, default=ms.TEST_INDEX)
    ap.add_argument("--briefs", type=Path, default=ms.BRIEFS)
    ap.add_argument("--out", type=Path, default=ms.OUT)
    args = ap.parse_args(argv)
    source = args.source.read_text(encoding="utf-8")
    pilot = args.pilot_oracle.read_text(encoding="utf-8")
    index = json.loads(args.test_index.read_text(encoding="utf-8")) if args.test_index.exists() else None
    try:
        files = ms.write_seed(source, pilot, args.out, test_index=index)
    except ValueError as e:
        print(f"PROBLEM: {args.source.name} doesn't convert: {e}")
        return 1
    print(f"wrote {', '.join(sorted(files))} to {args.out}")
    if not args.check:
        return 0
    briefs = json.loads(args.briefs.read_text(encoding="utf-8")) if args.briefs.exists() else None
    problems, warnings, summary = ms.check_seed(args.out, source, pilot, test_index=index, expected=expected,
                                                briefs=briefs)
    problems += check_run_fork(args.out)
    for line in summary:
        print(line)
    if not problems:
        print("run_fork.py: --oracle, --change-script and --owner-items load these files for every change")
    for w in warnings:
        print("WARNING:", w)
    for p in problems:
        print("PROBLEM:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
