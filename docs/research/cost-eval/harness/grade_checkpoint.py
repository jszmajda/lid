"""Grade one checkpoint of a trajectory against the seed's probes.

    ../plumbing/with-token.sh python3.12 grade_checkpoint.py --id s0-bare --change 0 [--workers 4] [--probes <probe IDs>]

Reads the trajectory's record in ../runs/<id>/ for the change's commit, and writes everything under
../runs/<id>/grading/change-NN/: the interface reference and start spec, the setup log and identifiers, and for each
batch the probes as the executor saw them, the execution log, and the judgment. Verdicts per probe and per item go
to verdicts.json. A probe the judge couldn't decide because of an execution fault runs once more, and its first
verdict is kept under "reruns".

A probe that needs prior-data or prior-observations gets them from earlier runs on its lineage's builds
(costeval/prior.py), each run once by this same script in earlier mode, which writes grading/earlier-cNN/ and no
verdicts:

    python3.12 grade_checkpoint.py --id g-ref-correct --change 22 --seed releasedesk-growth --prepare P-XX01-a [--observe ...]

A probe whose earlier run can't be had is listed as not run, with why under "not_run_why".
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import queue
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import grading, prior  # noqa: E402

IMAGE = "lid-cost-eval-executor:2.1.323"
CLAUDE_CODE = "2.1.323"


def checkpoint_name(run_id: str, out_name: str | None = None) -> str:
    """The name the checkpoint's volumes and containers are made from: a fork recorded under its trajectory
    (g-bare-1/course-forks/c13-1) is named with dashes, since Docker names can't hold a slash."""
    return run_id.replace("/", "-") + (f"-{out_name}" if out_name else "")


def applicable(probeset: grading.ProbeSet, change: int, chosen: set[str]) -> list:
    """The probes a grading runs: the named ones whatever their range (so a symptom diagnostic can run a later item's
    probes on the incoming version), or else every probe in range at the change except the follow-up pairs under
    `### RR-CC`, which run only on a reliance fork's build and only when named."""
    if chosen:
        return [p for p in probeset.probes if p.id in chosen]
    return [p for p in probeset.probes if p.applies(change) and not p.item.startswith("RR-")]


def prior_inputs(runs: Path, tid: str, change: int, probes, *, seed: str, run: Callable[[list[str]], int]) -> dict:
    """For the probes that need an earlier run: run what's missing (prior.ensure), then each one's record for the
    checker and for the judge, and its retained storage; the probes still without one, with why."""
    wanting = [p for p in probes if prior.needs_prior_data(p) or prior.needs_prior_observations(p)]
    missing = prior.ensure(runs, tid, change, wanting, seed=seed, run=run) if wanting else {}
    out = {"checker": {}, "judge": {}, "storage": {}, "missing": missing}
    for p in wanting:
        if p.id in missing:
            continue
        rec, obs, storage = prior.records(runs, tid, change, p)
        out["checker"][p.id], out["judge"][p.id] = prior.for_checker(rec, obs), prior.for_judge(rec, obs)
        if storage is not None:
            out["storage"][p.id] = storage
    return out


def run_earlier(ck, out: Path, runs: Path, tid: str, change: int, commit: str, probeset: grading.ProbeSet,
                prepare: list[str], observe: list[str], *, execute: Callable, seed: str,
                run: Callable[[list[str]], int], open_storage: Callable | None = None) -> dict:
    """Earlier mode, on this build: each prior-data probe's preparation (its first step, the storage retained where
    the executor runs `gt retain`, or else at the end), then each prior-observations probe's run (its later steps on a
    copy of the retained storage, for a prior-data probe). execute(bid, batch, text=, earlier=, retain=) runs one batch
    and returns its log lines and the executor's reply. open_storage(probe) gives a storage prepared on an earlier
    build as this build receives it, opened in turn by every build between (default: as prepared)."""
    by_id = {p.id: p for p in probeset.probes}
    summary: dict = {"prepared": [], "observed": [], "failed": {}}
    for n, pid in enumerate(prepare):
        p = by_id[pid]
        prep = prior.preparation(p)
        name = f"PREP-{pid}"
        lines, reply = execute(f"p{n:02d}", [p], text=grading.render_for_preparation(p, probeset.setup_notes, probeset.setups),
                               retain=name)
        if reply is None:
            summary["failed"][pid] = "the preparation session failed"
            continue
        by = "the executor" if any(r.get("op") == "retain" and (r.get("response") or {}).get("ok") for r in lines) else None
        if by is None:
            ck.admin(0, {"_op": "snapshot", "name": name})
            by = "the harness, at the end"
        d = prior.prep_dir(runs, tid, change, pid)
        d.mkdir(parents=True, exist_ok=True)
        (d / "storage.tar").write_bytes(ck.tar_out(name))
        (d / "record.json").write_text(json.dumps(prior.prep_record(pid, change, commit, prep.setup, lines, reply=reply,
                                                                    retained_by=by), indent=1))
        summary["prepared"].append(pid)
    # an observation of a probe prepared on another build (or at another change) needs that preparation first
    elsewhere = [by_id[pid] for pid in observe if prior.preparation(by_id[pid])
                 and not (prior.preparation(by_id[pid]).change == change and pid in prepare)]
    lacking = prior.ensure(runs, tid, change, elsewhere, seed=seed, run=run, kinds=("prepare",)) if elsewhere else {}
    for n, pid in enumerate(observe):
        p = by_id[pid]
        if pid in lacking:
            summary["failed"][pid] = lacking[pid]
            continue
        rec = None
        if prior.preparation(p):
            rec, _, storage = prior.records(runs, tid, change + 1, p)  # the preparation as the next change would see it
            data, why = (storage.read_bytes() if storage else None), None
            if storage is not None and open_storage is not None and prior.preparation(p).change < change:
                data, why = open_storage(p)
            if data is None:
                summary["failed"][pid] = why or "no retained storage to observe on"
                continue
            ck.tar_in(f"PRIOR-{pid}", data)
        lines, reply = execute(f"o{n:02d}", [p], earlier={pid: prior.for_checker(rec, None)} if rec else None)
        if reply is None:
            summary["failed"][pid] = "the observation session failed"
            continue
        f = prior.obs_path(runs, tid, change, pid)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"probe": pid, "change": change, "commit": commit, "notes": reply,
                                 "log": [r for r in lines if not r.get("admin")]}, indent=1))
        summary["observed"].append(pid)
    out.mkdir(parents=True, exist_ok=True)
    (out / "earlier.json").write_text(json.dumps(summary, indent=1))
    return summary


HOP_LOCK = HERE.parent / "runs" / ".hops.lock"  # one build's hop at a time: hops share Docker names per build


def _spec_of(run_dir: Path, change: int) -> dict | None:
    """The start spec an extraction of this build already found, if any grading of it has one."""
    for d in sorted((run_dir / "grading").glob("*/")):
        ex = d / "extraction.json"
        if not ex.exists():
            continue
        v = d / "verdicts.json"
        same = json.loads(v.read_text()).get("change") == change if v.exists() else d.name in (
            f"change-{change:02d}", f"earlier-c{change:02d}")
        e = json.loads(ex.read_text())
        if same and e.get("spec") and not e.get("problems"):
            return e["spec"]
    return None


def make_hop(runs: Path, fallback: list[tuple[str, dict]]) -> Callable:
    """prior.open_in_turn's hop on Docker: change k's build exported from its trajectory's workspace, its service
    started with its own extracted start spec where one exists, or else the fallbacks (the build under test's, the
    preparation's), each storage restored on it (the service comes up on it at the retained clock, upgrading it if
    it does), then saved as it stands."""
    def hop(k: int, owner: str, commit: str, storages: dict[str, bytes]) -> dict[str, dict]:
        meta = json.loads((runs / owner / "trajectory.json").read_text())
        own = _spec_of(runs / owner, k)
        specs = ([("its own extraction", own)] if own else []) + fallback
        ck = grading.Checkpoint(trajectory=checkpoint_name(owner, "hop"), change=k, commit=commit, image=IMAGE)
        try:
            ck.export(meta["volumes"]["workspace"])
            started = None
            for name, spec in specs:
                ck.sh(ck.volume, "rm -f /work/log/exec-0.jsonl")
                ck.put(ck.volume, "/work/out/start-0.json", json.dumps(grading.worker_spec(spec, 0)))
                ck.start_apps(1)
                if ck.wait_ready(0, timeout_s=180):
                    started = name
                    break
                ck.stop(1)
            if started is None:
                return {pid: {"came_up": None, "error": "no start spec brings this build's service up on empty data"}
                        for pid in storages}
            out = {}
            for pid, data in storages.items():
                name = f"HOP-{pid}"
                ck.tar_in(name, data)
                r = ck.admin(0, {"_op": "restore", "name": name})
                ck.admin(0, {"_op": "snapshot", "name": name})
                out[pid] = {"came_up": bool(r.get("ok")), "error": r.get("error"), "storage": ck.tar_out(name),
                            "spec_from": started}
            return out
        except RuntimeError as e:
            return {pid: {"came_up": None, "error": f"harness: {e}"} for pid in storages}
        finally:
            ck.stop(1)
            subprocess.run(["docker", "volume", "rm", "-f", ck.volume, ck.tools_volume], capture_output=True)
    return hop


def opened_in_turn(runs: Path, tid: str, change: int, probes, hop: Callable) -> dict[str, dict]:
    import fcntl
    HOP_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with open(HOP_LOCK, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        return prior.open_in_turn(runs, tid, change, probes, hop=hop)


def _open_one(runs: Path, tid: str, change: int, probe, hop: Callable) -> tuple[bytes | None, str | None]:
    r = opened_in_turn(runs, tid, change, [probe], hop).get(probe.id)
    if r is None:
        return None, "no preparation to open"
    if r["grader_fault"]:
        return None, r["grader_fault"]
    if r["final_came_up"] is False:
        return None, f"change {change}'s build didn't come up on the storage (the arm's fault)"
    return r["storage"], None


def broken_ids(by_id: dict, ids: list[str], broken: set[str]) -> set[str]:
    """The probes whose setup couldn't be loaded."""
    return {x for x in ids if by_id[x].setup in broken}


def _reuse_extraction(run_dir: Path, change: int, out: Path) -> bool:
    """Copy an extraction already made for this build (another grading of the same change) into out."""
    for d in sorted((run_dir / "grading").glob("*/")):
        ex = d / "extraction.json"
        if d == out or not ex.exists():
            continue
        v = d / "verdicts.json"
        same = json.loads(v.read_text()).get("change") == change if v.exists() else d.name == f"change-{change:02d}"
        if same and not json.loads(ex.read_text()).get("problems"):
            out.mkdir(parents=True, exist_ok=True)
            for name in ("extraction.json", "reference.md", "start.json"):
                shutil.copyfile(d / name, out / name)
            return True
    return False


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
    ap.add_argument("--no-rerun", action="store_true", help="don't run probes again after an execution fault")
    ap.add_argument("--prepare", default="", help="earlier mode: prior-data probes whose preparation runs on this build")
    ap.add_argument("--observe", default="", help="earlier mode: prior-observations probes to run on this build")
    args = ap.parse_args(argv)

    runs = HERE.parent / "runs"
    run_dir = runs / args.id
    meta = json.loads((run_dir / "trajectory.json").read_text())
    earlier_mode = bool(args.prepare or args.observe)
    if earlier_mode:
        owned = prior.lineage_owner(runs, args.id, args.change)
        commit = args.commit or (owned[1] if owned else None)
        out = prior.earlier_dir(runs, args.id, args.change) if not args.out_name else run_dir / "grading" / args.out_name
        args.out_name = args.out_name or out.name
    else:
        commit = args.commit or meta["changes"][str(args.change)]["commit"]
        out = run_dir / "grading" / (args.out_name or f"change-{args.change:02d}")
    out.mkdir(parents=True, exist_ok=True)
    probeset = grading.parse_probes((HERE.parent / "seeds" / args.seed / "hidden" / "probes.md").read_text(encoding="utf-8"))
    chosen = set(filter(None, args.probes.split(",")))
    selected = [] if earlier_mode else applicable(probeset, args.change, chosen)
    runnable = [p for p in selected if not p.deferred]
    pi = prior_inputs(runs, args.id, args.change, runnable, seed=args.seed,
                      run=lambda cmd: subprocess.run(cmd, cwd=HERE).returncode)
    runnable = [p for p in runnable if p.id not in pi["missing"]]
    by_id = {p.id: p for p in probeset.probes}
    prepare = [x for x in args.prepare.split(",") if x]
    observe = [x for x in args.observe.split(",") if x]
    if earlier_mode:
        runnable = [by_id[x] for x in dict.fromkeys(prepare + observe)]
    g = grading.Graders(image=IMAGE, roles_volume="ce-roles-cfg", claude_code=CLAUDE_CODE,
                        execute_model=args.execute_model, judge_model=args.judge_model)
    ck = grading.Checkpoint(trajectory=checkpoint_name(args.id, args.out_name), change=args.change,
                            commit=commit, image=IMAGE)
    started = time.monotonic()
    summary = {"trajectory": args.id, "change": args.change, "commit": commit, "workers": args.workers,
               "models": {"extraction": g.extraction_model, "setup": g.setup_model, "execute": g.execute_model,
                          "judge": g.judge_model},
               "not_run": [p.id for p in selected if p.deferred] + sorted(pi["missing"]), "not_run_why": pi["missing"]}

    print(f"exporting {commit[:10]} and extracting the interface", flush=True)
    ck.export(meta["volumes"]["workspace"])
    notes_path = HERE.parent / "seeds" / args.seed / "grading-notes.md"
    notes = notes_path.read_text(encoding="utf-8") if notes_path.exists() else ""
    if earlier_mode and _reuse_extraction(run_dir, args.change, out):  # the build's interface, as already extracted
        ex = json.loads((out / "extraction.json").read_text())
        ck.put(ck.volume, "/work/out/reference.md", (out / "reference.md").read_text())
        ck.put(ck.volume, "/work/out/start.json", (out / "start.json").read_text())
    else:
        ex = grading.extract(ck, g, out, notes)
    if ex["problems"]:
        print("extraction problems, trying once more:", ex["problems"])
        ex = grading.extract(ck, g, out, notes + "\n\nAn earlier attempt's start spec had these problems, which this one must avoid: "
                             + "; ".join(ex["problems"]))
    if ex["problems"]:
        print("extraction problems:", ex["problems"])
        summary["error"] = f"extraction: {ex['problems']}"
        (out / "verdicts.json").write_text(json.dumps(summary, indent=1))
        return 1
    # each prior-data probe's storage, opened in turn by every build from its preparation's to this one
    fallback = [("the build under test's", ex["spec"])]
    for p in runnable:
        prep = prior.preparation(p)
        o = prior.lineage_owner(runs, args.id, prep.change) if prep else None
        spec = _spec_of(runs / o[0], prep.change) if o else None
        if spec and all(spec != s for _, s in fallback):
            fallback.append((f"change {prep.change}'s, where {p.id} was prepared", spec))
    hop = make_hop(runs, fallback)
    opened, injected = {}, {}
    if not earlier_mode:
        chain = opened_in_turn(runs, args.id, args.change, [p for p in runnable if prior.preparation(p)], hop)
        summary["prior_hops"] = {pid: r["hops"] for pid, r in chain.items()}
        for pid, r in chain.items():
            if r["grader_fault"]:  # the grader couldn't start a build on the way: not run
                summary["not_run"].append(pid)
                summary["not_run_why"][pid] = r["grader_fault"]
            elif r["final_came_up"] is False:  # this build fails the owner's data: the arm's fault, the probe not met
                injected[pid] = prior.unopened_verdict(r, args.change)
            else:
                opened[pid] = r["storage"]
        runnable = [p for p in runnable if p.id not in injected and p.id not in summary["not_run_why"]]
    workers = 1 if earlier_mode else max(1, min(args.workers, len(runnable) // args.batch_size + 1))
    for k in range(workers):
        ck.put(ck.volume, f"/work/out/start-{k}.json", json.dumps(grading.worker_spec(ex["spec"], k)))
    try:
        ck.start_apps(workers)
        for k in range(workers):
            if not ck.wait_ready(k):
                raise RuntimeError(f"app worker {k} didn't start; see log/app-{k}.log in {ck.volume}")
        names = grading.setups_needed(probeset, {p.setup for p in runnable})
        print(f"preparing setups {names}", flush=True)
        reference = grading.grader_reference((out / "reference.md").read_text(), ex["spec"])
        (out / "grader-reference.md").write_text(reference)
        st = grading.prepare_setups(ck, g, probeset, names, reference, out)
        broken = grading.broken_setups(st["problems"], names)
        if st["problems"]:
            print("setup problems:", st["problems"])
        if "no identifier list" in st["problems"] or "the identifier list has no Credentials section" in st["problems"] \
                or broken >= set(names):
            summary["error"] = f"setup: {st['problems']}"
            (out / "verdicts.json").write_text(json.dumps(summary, indent=1))
            return 1
        # Probes on a setup that couldn't be loaded are not run; the rest go ahead.
        summary["not_run"] += [p.id for p in runnable if p.setup in broken]
        runnable = [p for p in runnable if p.setup not in broken]
        ck.put(ck.tools_volume, "/work/ids.md", (out / "ids.md").read_text())

        if earlier_mode:
            def execute(bid, batch, *, text=None, earlier=None, retain=None):
                bdir = out / "batches" / bid
                lines = grading.execute_batch(ck, g, 0, bid, batch, bdir, probeset.setup_notes, setups=probeset.setups,
                                              earlier=earlier, text=text, retain=retain)
                session = json.loads((bdir / "execution.json").read_text())
                return lines, (None if "error" in session else session.get("reply") or "")
            done = run_earlier(ck, out, runs, args.id, args.change, commit, probeset,
                               [x for x in prepare if x not in broken_ids(by_id, prepare, broken)],
                               [x for x in observe if x not in broken_ids(by_id, observe, broken)],
                               execute=execute, seed=args.seed, run=lambda cmd: subprocess.run(cmd, cwd=HERE).returncode,
                               open_storage=lambda p: _open_one(runs, args.id, args.change, p, hop))
            print(f"earlier runs: prepared {done['prepared']}, observed {done['observed']}, failed {done['failed']}")
            return 0 if not done["failed"] else 1
        for pid, data in opened.items():  # each prior-data probe's storage as this build received it, run on a copy
            if pid in {p.id for p in runnable}:
                ck.tar_in(f"PRIOR-{pid}", data)

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
                lines = grading.execute_batch(ck, g, k, bid, batch, bdir, probeset.setup_notes, setups=probeset.setups,
                                              earlier=pi["checker"])
                if "error" in json.loads((bdir / "execution.json").read_text()):
                    # A killed or failed session leaves a partial log: run the batch again under a new name.
                    bid = bid + "r"
                    bdir = out / "batches" / bid
                    lines = grading.execute_batch(ck, g, k, bid, batch, bdir, probeset.setup_notes, setups=probeset.setups,
                                                  earlier=pi["checker"])
                v = grading.judge_batch(g, batch, lines, bdir, conventions=probeset.setup_notes, earlier=pi["judge"])
                verdicts.update(v)
                print(f"{bid} on worker {k}: " + ", ".join(f"{p.id} {v.get(p.id, {}).get('verdict', '?')}" for p in batch), flush=True)

        with cf.ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(worker, range(workers)))

        # Probes left undecided by an execution fault get one more run, each in a batch of its own, so a verdict
        # reflects the build rather than the executor. The first verdict is kept beside the new one.
        again = grading.execution_faults(verdicts)
        if again and not args.no_rerun:
            print(f"running again after execution faults: {again}", flush=True)
            first = {pid: verdicts[pid] for pid in again}
            by_id = {p.id: p for p in runnable}
            for n, pid in enumerate(again):
                work.put((f"x{n:02d}", [by_id[pid]]))
            with cf.ThreadPoolExecutor(max_workers=workers) as pool:
                list(pool.map(worker, range(workers)))
            summary["reruns"] = {pid: {"first": first[pid], "second": verdicts.get(pid)} for pid in again}
    finally:
        if not args.keep:
            ck.stop(workers)

    verdicts.update(injected)
    runnable += [by_id[pid] for pid in injected]
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
