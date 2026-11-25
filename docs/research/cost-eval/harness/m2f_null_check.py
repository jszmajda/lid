"""The M2f null-arm check and its positive control (plan.md, M2f). The untouched v2 snapshot, graded at every change
as a null fork (run_fork.py --null), is the state before each change: it must meet none of the change's new-behaviour
rows, meet its guard rows (keep-it-as-it-was rules, m2f/guard-rows.json, which untouched code meets; one whose probes
can't run on the snapshot is named, not counted), and pass every dependency probe and held-out test graded there.
--mode right checks each change's right build (m2f-validation/builds.py, applied as a null fork's patch): every row
met, every dependency probe and held-out test passing, so a probe that never says met on a right build shows.

    python3.12 m2f_null_check.py --forks 'm2f-null-c*'

Reads each null fork's grading summary (grade_rust.py: items, dependency_probes, held_out_tests, graded_targets) and
the M2f change script's Introduces lines. The snapshot must pass every graded test outright: a test that failed is a
problem whatever its class, and so is one missing (its target not built, the test not run), with its cause, and
graded targets that didn't run at all. Prints a table, names every problem and every row left without a verdict (the
LLM probes for the new rows, until they exist), and writes ../runs/clowder-m2f/null-check.json. Exits 1 if anything
fails.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import simulator  # noqa: E402


def _json(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    ap.add_argument("--forks", default=None, help="default: m2f-null-c* (null) or m2f-right-c* (right)")
    ap.add_argument("--mode", choices=("null", "right"), default="null",
                    help="null: the untouched snapshot; right: each change's right build (the positive control)")
    ap.add_argument("--seed-files", type=Path, default=HERE.parent / "seeds" / "clowder" / "hidden" / "m2f")
    args = ap.parse_args(argv)
    where = "the snapshot" if args.mode == "null" else "the right build"
    pattern = args.forks or ("m2f-null-c*" if args.mode == "null" else "m2f-right-c*")
    script = simulator.parse_change_script((args.seed_files / "change-script.md").read_text(encoding="utf-8"))
    guards = (_json(args.seed_files / "guard-rows.json") or {}).get("rows") or {}
    graded = {}
    for d in sorted(args.runs.glob(pattern)):
        meta = _json(d / "trajectory.json") or {}
        if meta.get("arm") != "null" or "." in d.name:
            continue
        n = int(meta["change"])
        summary = _json(d / "grading" / f"change-{n:02d}" / "summary.json")
        if summary is not None:
            graded[n] = summary
    out = {"mode": args.mode, "changes": {}, "problems": [], "not_graded": []}
    lines = ["| Change | New rows met | Guard rows met | Dependency probes passing | Held-out tests passing | Verdict |",
             "|---|---|---|---|---|---|"]
    notes = []
    for n, ch in sorted(script.items()):
        if n not in graded:
            out["not_graded"].append(n)
            notes.append(f"change {n}: not graded")
            continue
        s = graded[n]
        rows = list(ch.introduces) if ch.introduces != simulator.ALL else []
        items = s.get("items") or {}
        result = {i: items.get(i) for i in rows}
        problems = []
        for i in rows:
            v, guard = result[i], i in guards
            label = f"{i} (guard)" if guard else i
            want = "met" if (guard or args.mode == "right") else "not met"
            if v == want:
                continue
            if args.mode == "null" and guard and not guards[i].get("checkable_on_snapshot", True) and v != "not met":
                notes.append(f"change {n}: {label} can't be checked on the snapshot: {v or 'no verdict'}")
                continue
            if v in ("met", "not met"):
                problems.append(f"{label} {v} on {where}")
            elif args.mode == "right" or guard:
                problems.append(f"{label} {v or 'without a verdict'} on {where}")
            else:  # a new row with no decided verdict on the snapshot: named, not counted as a pass
                notes.append(f"change {n}: {label} has no verdict ({v or 'none'})")
        recs = {**(s.get("dependency_probes") or {}), **(s.get("held_out_tests") or {})}
        probes = {t: (r or {}).get("result") for t, r in (s.get("dependency_probes") or {}).items()}
        held = {t: (r or {}).get("result") for t, r in (s.get("held_out_tests") or {}).items()}
        if (s.get("graded_targets") or {}).get("skipped"):
            problems.append(f"graded targets not run: {s['graded_targets']['skipped']}")
        for t, r in {**probes, **held}.items():
            if r == "failed":
                problems.append(f"{t} failed on {where}")
            elif r != "passed":  # not built, not run: missing, which here is a problem, not a pass
                problems.append(f"{t} missing on {where} ({r}: {(recs[t] or {}).get('cause') or '?'})")
        out["problems"] += [{"change": n, "what": p} for p in problems]
        new_rows = [i for i in rows if i not in guards]
        guard_rows = [i for i in rows if i in guards]
        out["changes"][str(n)] = {"rows": rows, "guard_rows": guard_rows, "rows_result": result,
                                  "met": [i for i in rows if result[i] == "met"],
                                  "rows_without_verdict": [i for i in rows if result[i] not in ("met", "not met")],
                                  "dependency_probes": probes, "held_out_tests": held,
                                  "grader_faults": s.get("missing_by_fault") or {}, "conflicts": sorted(s.get("conflicts") or {}),
                                  "ok": not problems}
        count = lambda d: f"{sum(r == 'passed' for r in d.values())} of {len(d)}" if d else "–"  # noqa: E731

        def met_of(ids):
            decided = [i for i in ids if result[i] in ("met", "not met")]
            return f"{sum(result[i] == 'met' for i in decided)} of {len(decided)}" if ids else "–"
        lines.append(f"| {n} | {met_of(new_rows)} | {met_of(guard_rows)} | {count(probes)} | {count(held)} | "
                     f"{'ok' if not problems else 'PROBLEM'} |")
        if s.get("missing_by_fault"):
            notes.append(f"change {n}: grader faults {s['missing_by_fault']}")
    print("\n".join(lines))
    for note in notes:
        print(note)
    for p in out["problems"]:
        print(f"problem, change {p['change']}: {p['what']}")
    dest = args.runs / "clowder-m2f" / f"{args.mode}-check.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1))
    return 1 if out["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
