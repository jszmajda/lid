"""Judge a graded checkpoint's execution logs again, with the same or another model, without running the service.

    ../plumbing/with-token.sh python3.12 rejudge.py --id s0-bare --change 2 --model claude-sonnet-5-5 --name sonnet

For test-retest of judgment and for comparing judges. Writes ../runs/<id>/grading/change-NN/rejudge-<name>.json with
each probe's new verdict beside the original, and prints the agreement.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import grading  # noqa: E402

IMAGE = "lid-cost-eval-executor:2.1.323"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True)
    ap.add_argument("--change", type=int, required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--seed", default="benchtime")
    args = ap.parse_args(argv)
    gdir = HERE.parent / "runs" / args.id / "grading" / f"change-{args.change:02d}"
    probeset = grading.parse_probes((HERE.parent / "seeds" / args.seed / "hidden" / "probes.md").read_text())
    probes = {p.id: p for p in probeset.probes}
    original = json.loads((gdir / "verdicts.json").read_text())["probes"]
    g = grading.Graders(image=IMAGE, roles_volume="ce-roles-cfg", claude_code="2.1.323", judge_model=args.model)

    def one(bdir: Path):
        batch = [probes[h[3:].strip()] for h in (bdir / "probes.md").read_text().splitlines()
                 if h.startswith("## ") and h[3:].strip() in probes]  # skip the conventions heading
        lines = [json.loads(l) for l in (bdir / "log.jsonl").read_text().splitlines() if l.strip()]
        out = bdir / f"rejudge-{args.name}"
        out.mkdir(exist_ok=True)
        return grading.judge_batch(g, batch, lines, out, conventions=probeset.setup_notes)

    new: dict[str, dict] = {}
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        for v in pool.map(one, sorted(p for p in (gdir / "batches").iterdir() if p.is_dir())):
            new.update(v)
    rows = {pid: {"original": original.get(pid, {}).get("verdict"), "new": new.get(pid, {}).get("verdict"),
                  "new_reason": new.get(pid, {}).get("reason")} for pid in sorted(set(original) | set(new))}
    agree = sum(r["original"] == r["new"] for r in rows.values())
    (gdir / f"rejudge-{args.name}.json").write_text(json.dumps({"model": args.model, "agree": agree, "of": len(rows), "rows": rows}, indent=1))
    print(f"{args.id} change {args.change}, {args.model}: {agree}/{len(rows)} agree with the original verdicts")
    for pid, r in rows.items():
        if r["original"] != r["new"]:
            print(f"  {pid}: {r['original']} -> {r['new']}: {(r['new_reason'] or '')[:180]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
