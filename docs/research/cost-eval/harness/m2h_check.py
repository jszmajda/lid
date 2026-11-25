"""The M2h null check and its positive control (plan.md, M2h; m2h-harness-needs.md, "Phases"), on grade_node.py's
gradings.

    python3.12 m2h_check.py --mode null --forks 'm2h-null-*'
    python3.12 m2h_check.py --mode right --forks 'm2h-right-c*'

null: each untouched start graded at a change (a null fork, m2h-null-<start>-cNN) is the state before it: the
dependency (or a control's comparison row) is not exercised, no non-guard new row is met (not met and not exercised
both pass), and every guard row checkable on the pin is met (one that isn't is named, not counted). right: each change's
right build (m2h-right-cNN) meets every row, guard rows too, and keeps the dependency. Grader faults are named per fork.
Writes ../runs/opengym-m2h/<mode>-check.json and exits 1 on any problem.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN = Path("/Users/jess/src/lid-cost-eval/docs/research/cost-eval")


def _json(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mode", choices=("null", "right"), required=True)
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    ap.add_argument("--forks", default=None, help="default: m2h-null-* (null) or m2h-right-c* (right)")
    ap.add_argument("--seed-files", type=Path, default=MAIN / "seeds" / "opengym" / "hidden" / "m2h")
    args = ap.parse_args(argv)
    where = "the untouched start" if args.mode == "null" else "the right build"
    kept = _json(args.seed_files / "kept-behaviour.json") or {}
    guards = (_json(args.seed_files / "guard-rows.json") or {}).get("rows") or {}
    out = {"mode": args.mode, "forks": {}, "problems": []}
    lines = ["| Fork | Change | Start | New rows met | Guard rows met | Dependency | Verdict |", "|---|---|---|---|---|---|---|"]
    notes = []
    for d in sorted(args.runs.glob(args.forks or ("m2h-null-*" if args.mode == "null" else "m2h-right-c*"))):
        meta = _json(d / "trajectory.json") or {}
        if "." in d.name or meta.get("arm") != "null" or meta.get("change") is None:
            continue
        n = int(meta["change"])
        s = _json(d / "grading" / f"change-{n:02d}" / "summary.json")
        if s is None:
            notes.append(f"{d.name}: not graded")
            continue
        m = re.fullmatch(r"m2h-null-(.+)-c\d+", d.name)
        start = m.group(1) if m else "bare"
        rows = (kept.get(str(n)) or {}).get("new_rows") or {}
        new = list(dict.fromkeys((rows.get("stated") or []) + (rows.get("askable") or [])))
        guard = [g for g in (rows.get("guard") or []) if g not in new] + [g for g in new if g in guards]
        new = [i for i in new if i not in guards]
        items = {k.split()[0]: v for k, v in (s.get("items") or {}).items()}
        dep = (s.get("dependency") or {}).get("result")
        problems = []
        if args.mode == "null":
            if dep != "not exercised":
                problems.append(f"the dependency {dep or 'without a result'} on {where}")
            problems += [f"{i} met on {where}" for i in new if items.get(i) == "met"]
            problems += [f"{i} {items.get(i) or 'without a verdict'} on {where}" for i in new
                         if items.get(i) not in ("met", "not met", "not exercised")]
            for g in guard:
                v = items.get(g)
                if not (guards.get(g) or {}).get("checkable_on_snapshot", True):
                    notes.append(f"{d.name}: {g} (guard) can't be checked on the pin: {v or 'no verdict'}")
                elif v != "met":
                    problems.append(f"{g} (guard) {v or 'without a verdict'} on {where}")
        else:
            if dep != "kept":
                problems.append(f"the dependency {dep or 'without a result'} on {where}")
            problems += [f"{i} {items.get(i) or 'without a verdict'} on {where}" for i in new if items.get(i) != "met"]
            problems += [f"{g} (guard) {items.get(g) or 'without a verdict'} on {where}" for g in guard
                         if items.get(g) != "met"]
        faults = {**(s.get("missing_by_fault") or {})}
        if faults:
            notes.append(f"{d.name}: grader faults {faults}")
        out["problems"] += [{"fork": d.name, "change": n, "what": p} for p in problems]
        out["forks"][d.name] = {"change": n, "start": start, "items": items, "dependency": dep, "grader_faults": faults,
                                "ok": not problems}

        def met_of(ids):
            decided = [i for i in ids if items.get(i) in ("met", "not met")]
            return f"{sum(items.get(i) == 'met' for i in decided)} of {len(decided)}" if ids else "–"
        lines.append(f"| {d.name} | {n} | {start} | {met_of(new)} | {met_of(guard)} | {dep or '–'} | "
                     f"{'ok' if not problems else 'PROBLEM'} |")
    print("\n".join(lines))
    for note in notes:
        print(note)
    for p in out["problems"]:
        print(f"problem, {p['fork']}: {p['what']}")
    dest = args.runs / "opengym-m2h" / f"{args.mode}-check.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1))
    return 1 if out["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
