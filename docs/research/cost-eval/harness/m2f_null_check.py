"""The M2f null-arm check (plan.md, M2f): the untouched v2 snapshot, graded at every change as a null fork
(run_fork.py --null), is the state before each change, so it must meet none of the change's new rows, and pass every
dependency probe and every held-out test graded at that change.

    python3.12 m2f_null_check.py --forks 'm2f-null-c*'

Reads each null fork's grading summary (grade_rust.py: items, dependency_probes, held_out_tests) and the M2f change
script's Introduces lines. Prints a table, names every problem and every row left without a verdict (the LLM probes
for the new rows, until they exist), and writes ../runs/clowder-m2f/null-check.json. Exits 1 if anything fails.
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
    ap.add_argument("--forks", default="m2f-null-c*")
    ap.add_argument("--seed-files", type=Path, default=HERE.parent / "seeds" / "clowder" / "hidden" / "m2f")
    args = ap.parse_args(argv)
    script = simulator.parse_change_script((args.seed_files / "change-script.md").read_text(encoding="utf-8"))
    graded = {}
    for d in sorted(args.runs.glob(args.forks)):
        meta = _json(d / "trajectory.json") or {}
        if meta.get("arm") != "null" or "." in d.name:
            continue
        n = int(meta["change"])
        summary = _json(d / "grading" / f"change-{n:02d}" / "summary.json")
        if summary is not None:
            graded[n] = summary
    out = {"changes": {}, "problems": [], "not_graded": []}
    lines = ["| Change | New rows met | Dependency probes passing | Held-out tests passing | Verdict |", "|---|---|---|---|---|"]
    notes = []
    for n, ch in sorted(script.items()):
        if n not in graded:
            out["not_graded"].append(n)
            notes.append(f"change {n}: not graded")
            continue
        s = graded[n]
        rows = list(ch.introduces) if ch.introduces != simulator.ALL else []
        items = s.get("items") or {}
        met = [i for i in rows if items.get(i) == "met"]
        no_verdict = [i for i in rows if items.get(i) not in ("met", "not met")]
        probes = {t: (r or {}).get("result") for t, r in (s.get("dependency_probes") or {}).items()}
        held = {t: (r or {}).get("result") for t, r in (s.get("held_out_tests") or {}).items()}
        problems = [f"{i} met on the snapshot" for i in met]
        problems += [f"{t} {r} on the snapshot" for t, r in {**probes, **held}.items() if r != "passed"]
        out["problems"] += [{"change": n, "what": p} for p in problems]
        out["changes"][str(n)] = {"rows": rows, "met": met, "rows_without_verdict": no_verdict, "dependency_probes": probes,
                                  "held_out_tests": held, "ok": not problems}
        count = lambda d: f"{sum(r == 'passed' for r in d.values())} of {len(d)}" if d else "–"  # noqa: E731
        lines.append(f"| {n} | {len(met)} of {len(rows) - len(no_verdict)} | {count(probes)} | {count(held)} | "
                     f"{'ok' if not problems else 'PROBLEM'} |")
        if no_verdict:
            notes.append(f"change {n}: {', '.join(no_verdict)} have no verdict")
    print("\n".join(lines))
    for note in notes:
        print(note)
    for p in out["problems"]:
        print(f"problem, change {p['change']}: {p['what']}")
    dest = args.runs / "clowder-m2f" / "null-check.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1))
    return 1 if out["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
