"""Grade one checkpoint of a trajectory against the seed's probes.

    ../plumbing/with-token.sh python3.12 grade_checkpoint.py --id s0-bare --change 0 [--workers 4] [--probes <probe IDs>]

Reads the trajectory's record in ../runs/<id>/ for the change's commit, and writes everything under
../runs/<id>/grading/change-NN/: the interface reference and start spec, the setup log and identifiers, and for each
batch the probes as the executor saw them, the execution log, and the judgment. Verdicts per probe and per item go
to verdicts.json. Probes that need prior-data or prior-observations are listed as not run.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import queue
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import grading  # noqa: E402

IMAGE = "lid-cost-eval-executor:2.1.323"
CLAUDE_CODE = "2.1.323"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True)
    ap.add_argument("--change", type=int, required=True)
    ap.add_argument("--seed", default="benchtime")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--probes", default="", help="comma-separated probe IDs to run, whatever their range (default: every applicable probe)")
    ap.add_argument("--out-name", default=None, help="folder under grading/ (default: change-NN)")
    ap.add_argument("--commit", default=None, help="grade this commit of the trajectory's workspace instead of the change's")
    ap.add_argument("--execute-model", default="claude-haiku-5-5")
    ap.add_argument("--judge-model", default="claude-sonnet-5-5")
    ap.add_argument("--keep", action="store_true", help="leave the app containers running afterwards")
    args = ap.parse_args(argv)

    run_dir = HERE.parent / "runs" / args.id
    meta = json.loads((run_dir / "trajectory.json").read_text())
    commit = args.commit or meta["changes"][str(args.change)]["commit"]
    out = run_dir / "grading" / (args.out_name or f"change-{args.change:02d}")
    out.mkdir(parents=True, exist_ok=True)
    probeset = grading.parse_probes((HERE.parent / "seeds" / args.seed / "hidden" / "probes.md").read_text(encoding="utf-8"))
    chosen = set(filter(None, args.probes.split(",")))
    # Named probes run whatever their range, so a symptom diagnostic can run a later item's probes on the incoming version.
    applicable = [p for p in probeset.probes if (p.id in chosen if chosen else p.applies(args.change))]
    runnable = [p for p in applicable if not p.deferred]
    g = grading.Graders(image=IMAGE, roles_volume="ce-roles-cfg", claude_code=CLAUDE_CODE,
                        execute_model=args.execute_model, judge_model=args.judge_model)
    ck = grading.Checkpoint(trajectory=args.id + (f"-{args.out_name}" if args.out_name else ""), change=args.change,
                            commit=commit, image=IMAGE)
    started = time.monotonic()
    summary = {"trajectory": args.id, "change": args.change, "commit": commit, "workers": args.workers,
               "models": {"extraction": g.extraction_model, "setup": g.setup_model, "execute": g.execute_model,
                          "judge": g.judge_model},
               "not_run": [p.id for p in applicable if p.deferred]}

    print(f"exporting {commit[:10]} and extracting the interface", flush=True)
    ck.export(meta["volumes"]["workspace"])
    ex = grading.extract(ck, g, out)
    if ex["problems"]:
        print("extraction problems:", ex["problems"])
        summary["error"] = f"extraction: {ex['problems']}"
        (out / "verdicts.json").write_text(json.dumps(summary, indent=1))
        return 1
    workers = max(1, min(args.workers, len(runnable) // args.batch_size + 1))
    for k in range(workers):
        ck.put(ck.volume, f"/work/out/start-{k}.json", json.dumps(grading.worker_spec(ex["spec"], k)))
    try:
        ck.start_apps(workers)
        for k in range(workers):
            if not ck.wait_ready(k):
                raise RuntimeError(f"app worker {k} didn't start; see log/app-{k}.log in {ck.volume}")
        names = sorted({p.setup for p in runnable}, key=lambda s: int(s[1:]))
        print(f"preparing setups {names}", flush=True)
        reference = grading.grader_reference((out / "reference.md").read_text(), ex["spec"])
        (out / "grader-reference.md").write_text(reference)
        st = grading.prepare_setups(ck, g, probeset, names, reference, out)
        if st["problems"]:
            print("setup problems:", st["problems"])
            summary["error"] = f"setup: {st['problems']}"
            (out / "verdicts.json").write_text(json.dumps(summary, indent=1))
            return 1
        ck.put(ck.tools_volume, "/work/ids.md", (out / "ids.md").read_text())

        work: queue.Queue = queue.Queue()
        for n, b in enumerate(grading.batches(runnable, args.batch_size)):
            work.put((f"b{n:02d}", b))
        verdicts: dict[str, dict] = {}

        def worker(k: int):
            while True:
                try:
                    bid, batch = work.get_nowait()
                except queue.Empty:
                    return
                bdir = out / "batches" / bid
                lines = grading.execute_batch(ck, g, k, bid, batch, bdir)
                if "error" in json.loads((bdir / "execution.json").read_text()):
                    # A killed or failed session leaves a partial log: run the batch again under a new name.
                    bid = bid + "r"
                    bdir = out / "batches" / bid
                    lines = grading.execute_batch(ck, g, k, bid, batch, bdir)
                v = grading.judge_batch(g, batch, lines, bdir)
                verdicts.update(v)
                print(f"{bid} on worker {k}: " + ", ".join(f"{p.id} {v.get(p.id, {}).get('verdict', '?')}" for p in batch), flush=True)

        with cf.ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(worker, range(workers)))
    finally:
        if not args.keep:
            ck.stop(workers)

    probe_verdicts = {pid: v["verdict"] for pid, v in verdicts.items()}
    summary.update({"probes": verdicts, "items": grading.item_verdicts(probe_verdicts, runnable),
                    "setup": st["problems"], "minutes": round((time.monotonic() - started) / 60, 1)})
    (out / "verdicts.json").write_text(json.dumps(summary, indent=1))
    items = summary["items"]
    counts = {v: sum(1 for i in items.values() if i["verdict"] == v) for v in (*grading.VERDICTS, None)}
    print(f"items: {counts}; not run: {summary['not_run']}; {summary['minutes']} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
