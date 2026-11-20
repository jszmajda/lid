"""Judge a graded checkpoint's execution logs again, with the same or another model, without running the service.

    ../plumbing/with-token.sh python3.12 rejudge.py --id s0-bare --change 2 --model claude-sonnet-5-5 --name sonnet

For test-retest of judgment and for comparing judges. Writes ../runs/<id>/grading/change-NN/rejudge-<name>.json with
each probe's new verdict beside the original, and prints the agreement. The judge gets the grading's identifier list
(ids.md), as a grading's own judge does.

To redo the judgment of named probes in place, after a fault in judging alone (their logs stand):

    python3.12 rejudge.py --id g-ref-correct --out-name pair-c13-after --seed releasedesk-growth --model claude-sonnet-5-5 \
        --name ids --only P-RR13-current,P-RR13-displaced --replace

--replace puts the new verdicts of the --only probes in verdicts.json (the old ones kept under "rejudged"), and
recomputes the item verdicts.
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


def main(argv=None, *, judge=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True)
    ap.add_argument("--change", type=int, default=None)
    ap.add_argument("--model", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--seed", default="benchtime")
    ap.add_argument("--probes", help="probe file to judge against, if not the seed's current one (use the version the logs "
                                     "were executed under, e.g. hidden/archive/probes-v4.md)")
    ap.add_argument("--out-name", default=None, help="the grading folder (default: change-NN)")
    ap.add_argument("--only", default="", help="judge only the batches holding these probes, and report only them")
    ap.add_argument("--replace", action="store_true", help="put the --only probes' new verdicts in verdicts.json")
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    ap.add_argument("--seed-dir", type=Path, default=None)
    args = ap.parse_args(argv)
    if args.change is None and not args.out_name:
        ap.error("give --change or --out-name")
    if args.replace and not args.only:
        ap.error("--replace needs --only")
    gdir = args.runs / args.id / "grading" / (args.out_name or f"change-{args.change:02d}")
    pfile = (args.seed_dir or HERE.parent / "seeds" / args.seed) / "hidden" / (args.probes or "probes.md")
    probeset = grading.parse_probes(pfile.read_text())
    probes = {p.id: p for p in probeset.probes}
    summary = json.loads((gdir / "verdicts.json").read_text())
    original = summary["probes"]
    only = set(filter(None, args.only.split(",")))
    ids = (gdir / "ids.md").read_text() if (gdir / "ids.md").exists() else ""
    g = grading.Graders(image=IMAGE, roles_volume="ce-roles-cfg", claude_code="2.1.323", judge_model=args.model)
    judge = judge or grading.judge_batch

    def batch_of(bdir: Path):
        return [probes[h[3:].strip()] for h in (bdir / "probes.md").read_text().splitlines()
                if h.startswith("## ") and h[3:].strip() in probes]  # skip the conventions heading

    def one(bdir: Path):
        lines = [json.loads(l) for l in (bdir / "log.jsonl").read_text().splitlines() if l.strip()]
        out = bdir / f"rejudge-{args.name}"
        out.mkdir(exist_ok=True)
        return judge(g, batch_of(bdir), lines, out, conventions=probeset.setup_notes, ids=ids)

    # the latest batch run of each probe (a rerun after an execution fault is named after its first, plus "r" or "x")
    dirs = sorted(p for p in (gdir / "batches").iterdir() if p.is_dir())
    if only:
        latest: dict[str, Path] = {}
        for d in dirs:
            for p in batch_of(d):
                if p.id in only:
                    latest[p.id] = d
        dirs = sorted(set(latest.values()))
    new: dict[str, dict] = {}
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        for v in pool.map(one, dirs):
            new.update(v)
    if only:
        new = {pid: v for pid, v in new.items() if pid in only}
    if args.replace:
        rejudged = summary.setdefault("rejudged", {})
        for pid, v in new.items():
            rejudged[pid] = {"was": original.get(pid), "by": f"rejudge.py --name {args.name}"}
            original[pid] = v
        graded = [probes[pid] for pid in original if pid in probes]
        summary["items"] = grading.item_verdicts({pid: v["verdict"] for pid, v in original.items()}, graded)
        (gdir / "verdicts.json").write_text(json.dumps(summary, indent=1))
    before = {pid: (summary.get("rejudged", {}).get(pid, {}).get("was") if args.replace and pid in new else v)
              for pid, v in original.items()}
    rows = {pid: {"original": (before.get(pid) or {}).get("verdict"), "new": new.get(pid, {}).get("verdict"),
                  "new_reason": new.get(pid, {}).get("reason")} for pid in sorted(set(before) | set(new))
            if not only or pid in only}
    agree = sum(r["original"] == r["new"] for r in rows.values())
    (gdir / f"rejudge-{args.name}.json").write_text(json.dumps({"model": args.model, "agree": agree, "of": len(rows), "rows": rows}, indent=1))
    print(f"{args.id} {gdir.name}, {args.model}: {agree}/{len(rows)} agree with the original verdicts")
    for pid, r in rows.items():
        if r["original"] != r["new"]:
            print(f"  {pid}: {r['original']} -> {r['new']}: {(r['new_reason'] or '')[:180]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
