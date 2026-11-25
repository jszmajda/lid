"""Grade one change of an M2h fork (openGym, Node): keeping, the dependency probe, new rows, and the joint outcome.

    ../plumbing/with-token.sh python3.12 grade_node.py --id m2h-bare-c01-r1
    python3.12 grade_node.py --baseline-only --start-commit d96444e --start-volume ogmap-bare-ws --name m2h-baseline-bare

M2f's grade_rust.py, for M2h's Node subject (seeds/opengym/hidden/m2h-harness-needs.md, "Grading"); the pieces are
costeval/node_grading.py's. Reads the fork's trajectory.json: its start commit, the change's commit, its workspace
volume, its image (the Node executor image), and the start it was forked from (fork_of.volume, read-only, for the
baseline). The seed's files are named by --seed-dir (seeds/opengym) or one by one: the change text
(hidden/m2h-changes.md: rows, guard rows, dependency lines, retired tests, repair reports), the guard rows
(hidden/m2h-guard-rows.json), the probes (hidden/m2h/probes.md, M2f's format), and the grader-owned folder
(hidden/m2h-graded/graded.json: adjustments, dependency probes and their adapters, the flaky list, row conditions;
node_grading.load_graded gives the format). Writes under ../runs/<id>/grading/change-NN/:

- test_edits.json: test files the arm edited, deleted, renamed or added, and the suite configuration it changed;
- arm.diff: the arm's diff of code and tests as the extraction reads it, annotations taken out;
- keeping.json and keeping/: each suite's run on the fork (its log and report), with the start's test files put back
  and the change's adjustment applied, compared test by test with the start's baseline; failures with their
  classification (keeping/classify/ holds what the classifier read and answered);
- dependency.json and dependency/: each dependency probe (or a control's comparison row) with its adapter, its log
  and its result, and the change's roll-up;
- probes/: the reference, the extraction's implementation record, each batch's probes, tests, outputs and judgment,
  and verdicts.json;
- summary.json: the fork and seed files; test_edits, doc_changes, hidden_from_graders; keeping (counted, passed,
  failed, not_loaded, not_run, share_passed, keeping_failures, new_state_only, share_kept, the retired and adjusted
  tests, flaky reruns, each suite's counts, the baseline); dependency ({"result": kept | broken | not exercised |
  missing, "row", "exercised_only_if", "probes", "counting", "notes"}); items, items_met, new_rows_met,
  guard_rows_met, guard_rows, guard_exempt, implementation, conflicts, conditions, missing_by_fault,
  execution_faults; failed_setups; joint (implemented: yes | partly | no | N/A | null, the dependent behaviour, type,
  tier, the dependency line or comparison row, and the plan's notes); repair_reports (each miss's report).

Baselines are cached per start commit under ../runs/opengym-m2h/baselines/<commit>/ (baseline.json, logs/, and
adjusted/change-NN-<key>.json for each change's adjustment): --baseline-only fills one without a fork. Volumes are named
for the fork (`<id>-cNN-grade`, `<id>-baseline-grade`) and removed at the end unless --keep.

A repair fork (run_clowder_repairs.py; its trajectory.json names the fork it repairs) starts from that fork's result,
and is graded from that fork's start, as the fork was: the same cached baseline, the start's test files put back, its
diff from the start (so its keeping compares with the fork's, test by test). The summary names the fork and its commit.

The web app's whole suite takes a lock every grading shares (--suite-locks) before it runs, so gradings running at
once run it one at a time, within the VM's memory; the command is unchanged, so it matches the cached baselines.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import executor, grading, node_grading as node, rust_classify as rc  # noqa: E402
from run_trajectory import CLAUDE_CODE, ROLES_VOLUME  # noqa: E402

KEEPING_FIELDS = ("counted", "passed", "failed", "not_loaded", "not_loaded_by_cause", "not_run", "share_passed", "keeping_failures",
                  "new_state_only", "share_kept", "classified", "classification_cost_usd")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_json(path: Path, data) -> None:
    """Written whole or not at all: a baseline another grading reads at the same time is never half there."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def _sha(path: Path | None) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path and path.is_file() else None


def baseline(make: Callable, *, name: str, commit: str, image: str, volume: str, suites: list[str], flaky: list[dict],
             reruns: int, cache: Path, graded_dir: Path | None = None, adjustment: dict | None = None,
             change: int | None = None) -> tuple[dict, dict | None, dict]:
    """The start's suites (cached per commit: only suites not cached yet run) and, for a change with an adjustment, the
    start's files that adjustment touches run again with it applied (cached per change and adjustment). The start is
    exported read-only from its own volume into `<name>-baseline-grade`, removed afterwards. Returns (runs, adjusted
    runs or None, what was cached and computed). Graders sharing a start take a lock on its cache first, so the first
    computes and the rest read what it wrote."""
    cdir = cache / commit
    cdir.mkdir(parents=True, exist_ok=True)
    with open(cache / f"{commit}.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            return _baseline(make, name=name, commit=commit, image=image, volume=volume, suites=suites, flaky=flaky,
                             reruns=reruns, cdir=cdir, graded_dir=graded_dir, adjustment=adjustment, change=change)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _baseline(make: Callable, *, name: str, commit: str, image: str, volume: str, suites: list[str], flaky: list[dict],
              reruns: int, cdir: Path, graded_dir: Path | None, adjustment: dict | None,
              change: int | None) -> tuple[dict, dict | None, dict]:
    bpath = cdir / "baseline.json"
    cached = json.loads(bpath.read_text()) if bpath.exists() else {"commit": commit, "suites": {}}
    todo = [s for s in suites if s not in cached["suites"]]
    akey = apath = adj_runs = None
    if adjustment:
        akey = node.adjustment_key(graded_dir, adjustment)
        apath = cdir / "adjusted" / f"change-{change:02d}-{akey}.json"
        wanted = {node.suite_of(f) for f in node.adjustment_touched(graded_dir, adjustment)} & set(suites)
        if apath.exists():
            adj_runs = json.loads(apath.read_text())["suites"]
            if not wanted <= set(adj_runs):  # cached with fewer suites selected: run it again
                adj_runs = None
    info = {"dir": str(cdir), "computed": bool(todo), "adjusted_key": akey,
            "adjusted_computed": bool(adjustment) and adj_runs is None}
    if todo or info["adjusted_computed"]:
        ck = make(f"{name}-baseline", commit, image)
        try:
            ck.export(volume)
            if todo:
                runs = node.run_suites(ck, todo, "baseline", flaky=flaky, reruns=reruns, out_dir=cdir / "logs")
                cached["suites"].update({s: node.compact_run(r) for s, r in runs.items()})
                cached.update({"volume": volume, "image": image, "at": _now(), "flaky": flaky, "flaky_reruns": reruns})
                _write_json(bpath, cached)
            if info["adjusted_computed"]:
                touched = node.apply_adjustment(ck, graded_dir, adjustment)
                by_suite: dict[str, list[str]] = {}
                for f in touched:
                    if node.suite_of(f) in suites:
                        by_suite.setdefault(node.suite_of(f), []).append(f)
                ck.put(node.REPORTER_PATH, node.NODE_REPORTER)
                label = f"adjusted-c{change:02d}"
                adj_runs = {}
                for s, files in sorted(by_suite.items()):
                    suite = node.SUITES[s]
                    node.install(ck, suite, label)
                    run = node.rerun_flaky(ck, suite, node.run_suite(ck, suite, label, files=files), label, flaky, reruns)
                    run.pop("log", None)
                    adj_runs[s] = node.compact_run(run)
                _write_json(apath, {"commit": commit, "change": change, "key": akey, "touched": touched,
                                    "suites": adj_runs, "at": _now()})
        finally:
            ck.drop()
    return {s: cached["suites"][s] for s in suites}, adj_runs, info


def _suite_summary(run: dict) -> dict:
    return {"exit": run.get("exit"), "counts": run.get("counts") or {}, "minutes": run.get("minutes"),
            "files_not_loaded": len(run.get("file_failures") or {}), "flaky": run.get("flaky") or {},
            **({"install": {k: run["install"][k] for k in ("command", "exit")}} if run.get("install") else {}),
            **({"error": run["error"][:300]} if run.get("error") else {})}


def keeping(ck, *, args, meta: dict, n: int, base: str, image: str, change: node.ChangeInfo, graded: dict,
            graded_dir: Path, plan: dict, suites: list[str], flaky: list[dict], reruns: int, make: Callable, out: Path,
            classify: Callable | None) -> tuple[dict, dict]:
    """Keeping on the fork: the baseline, the start's test files put back, the adjustment, the suites, the comparison,
    and the classification of failures. Returns (keeping.json, the summary's keeping)."""
    start_volume = args.baseline_volume or (meta.get("fork_of") or {}).get("volume") or meta["volumes"]["workspace"]
    adj = node.adjustment_for(graded, n) if graded else None
    base_runs, adj_runs, info = baseline(make, name=args.id, commit=base, image=image,
                                         volume=start_volume, suites=suites, flaky=flaky, reruns=reruns,
                                         cache=args.baselines or args.runs / "opengym-m2h" / "baselines",
                                         graded_dir=graded_dir, adjustment=adj, change=n)
    quoted = lambda ps: " ".join(f"'{p}'" for p in ps)  # noqa: E731
    if plan["restore"]:
        ck.sh(f"cd {node.APP} && git checkout {base} -- {quoted(plan['restore'])}")
    if plan["remove"]:
        ck.sh(f"cd {node.APP} && rm -f {quoted(plan['remove'])}")
    touched = node.apply_adjustment(ck, graded_dir, adj) if adj else []
    touched = {t for t in touched if node.suite_of(t) in suites}
    fork_runs = node.run_suites(ck, suites, "fork", flaky=flaky, reruns=reruns, out_dir=out / "keeping")
    keep = node.compare_keeping(base_runs, fork_runs, retired=change.retired, adjusted=adj_runs if touched else None,
                                touched=touched, declared_pinning=set((adj or {}).get("pinning") or []))
    keep["retired"]["unparsed"] = change.retired_unparsed
    if classify is not None:
        sources = {f: ck.get(f"{node.APP}/{f}") for f in sorted({x["file"] for x in keep["failures"].values()})}
        classify(keep, sources)
    else:
        keep.update({"classified": False, "new_state_only": None, "keeping_failures": None, "share_kept": None,
                     "classification_cost_usd": None})
    suites_summary = {s: _suite_summary(r) for s, r in fork_runs.items()}
    record = {**keep, "suites": suites_summary, "baseline": info,
              "adjustment": ({"kind": adj.get("kind"), "touched": sorted(touched), "key": info["adjusted_key"]} if adj else None)}
    summary = {**{k: keep.get(k) for k in KEEPING_FIELDS}, "not_loaded_files": keep["not_loaded_files"],
               "failures": {t: {"message": f["message"][:300], "class": (f.get("classification") or {}).get("classification")}
                            for t, f in keep["failures"].items()},
               "retired": keep["retired"], "adjusted": keep["adjusted"], "suites": suites_summary,
               "test_files_restored": len(plan["restore"]), "test_files_removed": len(plan["remove"]),
               "suite_config_changed": plan["suite_config_changed"],
               "baseline": {**info, "suites": {s: {"counts": r.get("counts"), "exit": r.get("exit"),
                                                   **({"error": r["error"][:300]} if r.get("error") else {})}
                                               for s, r in base_runs.items()}}}
    return record, summary


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", help="the fork (its runs/<id>/trajectory.json)")
    ap.add_argument("--change", type=int, help="default: the fork's change")
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    ap.add_argument("--seed-dir", type=Path, default=HERE.parent / "seeds" / "opengym")
    ap.add_argument("--changes", type=Path, help="default: <seed-dir>/hidden/m2h-changes.md")
    ap.add_argument("--guard-rows", type=Path, help="default: <seed-dir>/hidden/m2h-guard-rows.json")
    ap.add_argument("--probes", type=Path, help="default: <seed-dir>/hidden/m2h/probes.md")
    ap.add_argument("--graded-dir", type=Path, help="default: <seed-dir>/hidden/m2h-graded")
    ap.add_argument("--baselines", type=Path, help="default: <runs>/opengym-m2h/baselines")
    ap.add_argument("--baseline-volume", help="the start's volume; default: the fork's fork_of.volume")
    ap.add_argument("--suite-locks", type=Path,
                    help="where the lock files every grading shares live (a whole web-app run takes one, so only one "
                         "runs at a time); default: <runs>/opengym-m2h/locks")
    ap.add_argument("--suites", default=",".join(node.DEFAULT_SUITES), help="of " + ", ".join(node.SUITES))
    ap.add_argument("--flaky", help="known flaky tests: 'none', a JSON list or file; default: graded.json's, else "
                                    "useStore.stale-sync (frontend) and server-origin-hint (api)")
    ap.add_argument("--flaky-reruns", type=int, help=f"default: graded.json's, else {node.FLAKY_RERUNS}")
    ap.add_argument("--joint-rules", type=Path, help="a JSON file in place of node_grading.JOINT_RULES")
    ap.add_argument("--no-keeping", action="store_true")
    ap.add_argument("--no-classify", action="store_true", help="leave keeping failures unclassified")
    ap.add_argument("--no-dependency", action="store_true")
    ap.add_argument("--no-adapters", action="store_true", help="dependency probes run with the pin's adapters")
    ap.add_argument("--adapter-note", action="append", default=[], metavar="ID=TEXT",
                    help="a note for one probe's adapter writer on this build (repeatable); recorded in the summary")
    ap.add_argument("--no-probes", action="store_true")
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--extraction-model", default="claude-sonnet-5-5")
    ap.add_argument("--execute-model", default="claude-haiku-5-5")
    ap.add_argument("--judge-model", default="claude-sonnet-5-5")
    ap.add_argument("--adapter-model", default="claude-sonnet-5-5")
    ap.add_argument("--image", help="default: the fork's image, else " + node.IMAGE)
    ap.add_argument("--keep", action="store_true", help="keep the checkpoint volume afterwards")
    ap.add_argument("--baseline-only", action="store_true",
                    help="run (and cache) a start's baseline alone: needs --start-commit, --start-volume and --name")
    ap.add_argument("--start-commit")
    ap.add_argument("--start-volume")
    ap.add_argument("--name", help="--baseline-only: names the volume (<name>-baseline-grade)")
    return ap


def main(argv=None, *, checkpoint: Callable | None = None, run_role: Callable = executor.run_role) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    make = checkpoint or (lambda name, c, img: node.NodeCheckpoint(name=name, commit=c, image=img))
    node.SUITE_LOCKS = args.suite_locks or args.runs / "opengym-m2h" / "locks"
    suites = [s for s in args.suites.split(",") if s]
    unknown = [s for s in suites if s not in node.SUITES]
    if unknown:
        ap.error(f"unknown suites {unknown}")
    seed = args.seed_dir / "hidden"
    graded_dir = args.graded_dir or seed / "m2h-graded"
    graded = node.load_graded(graded_dir) if (graded_dir / node.GRADED_JSON).is_file() else {}
    flaky = node.flaky_entries(args.flaky) if args.flaky else ([dict(e) for e in graded["flaky"]] if graded.get("flaky")
                                                                else node.flaky_entries(None))
    reruns = args.flaky_reruns if args.flaky_reruns is not None else graded.get("flaky_reruns", node.FLAKY_RERUNS)
    if args.baseline_only:
        if not (args.start_commit and args.start_volume and args.name):
            ap.error("--baseline-only needs --start-commit, --start-volume and --name")
        runs, _, info = baseline(make, name=args.name, commit=args.start_commit, image=args.image or node.IMAGE,
                                 volume=args.start_volume, suites=suites, flaky=flaky, reruns=reruns,
                                 cache=args.baselines or args.runs / "opengym-m2h" / "baselines")
        print(json.dumps({"baseline": info, "suites": {s: {"counts": r.get("counts"), "exit": r.get("exit"),
                                                           "files_not_loaded": r.get("file_failures"),
                                                           "flaky": r.get("flaky")} for s, r in runs.items()}}, indent=1))
        return 0
    if not args.id:
        ap.error("--id is needed (or --baseline-only)")
    run = args.runs / args.id
    meta = json.loads((run / "trajectory.json").read_text())
    n = args.change if args.change is not None else meta.get("change")
    if n is None:
        ap.error("--change is needed")
    commit, base = meta["changes"][str(n)]["commit"], meta["start_commit"]
    repair = None
    if meta.get("repair"):  # a repair starts from its fork's result, and is graded from its fork's start, as the fork was
        of = json.loads((args.runs / meta["repair"]["of"] / "trajectory.json").read_text())
        repair = {"of": meta["repair"]["of"], "item": meta["repair"].get("item"), "fork_commit": base}
        base = of["start_commit"]
    image = args.image or meta.get("image") or node.IMAGE
    out = run / "grading" / f"change-{n:02d}"
    out.mkdir(parents=True, exist_ok=True)
    changes_path = args.changes or seed / "m2h-changes.md"
    guards_path = args.guard_rows or seed / "m2h-guard-rows.json"
    probes_path = args.probes or seed / "m2h" / "probes.md"
    changes = node.parse_changes(changes_path.read_text(encoding="utf-8")) if changes_path.is_file() else {}
    change = changes.get(n) or node.ChangeInfo(number=n, title="")
    guards = set(node.load_guard_rows(guards_path)) if guards_path.is_file() else set()
    rules = ({int(k): v for k, v in json.loads(args.joint_rules.read_text()).items()} if args.joint_rules
             else node.JOINT_RULES)
    g = node.NodeGraders(image=image, roles_volume=ROLES_VOLUME, claude_code=CLAUDE_CODE,
                         extraction_model=args.extraction_model, execute_model=args.execute_model,
                         judge_model=args.judge_model, adapter_model=args.adapter_model)
    summary: dict = {"id": args.id, "change": n, "arm": meta.get("arm"), "commit": commit, "start_commit": base,
                     "start": (meta.get("fork_of") or {}).get("start"), "image": image,
                     "seed_files": {"changes_sha256": _sha(changes_path), "guard_rows_sha256": _sha(guards_path),
                                    "probes_sha256": _sha(probes_path),
                                    "graded_sha256": _sha(graded_dir / node.GRADED_JSON)}}
    if repair:
        summary["repair"] = repair
    adapter_notes = dict(x.split("=", 1) for x in args.adapter_note)
    if adapter_notes:
        summary["adapter_notes"] = adapter_notes
    if not changes.get(n):
        summary["change_text_missing"] = f"no change {n} in {changes_path}"
    classify = None
    if not args.no_classify:
        def classify(keep: dict, sources: dict) -> None:
            def ask(prompt: str):
                rec = run_role(g.role(g.judge_model, timeout_s=1200), prompt, json_schema=json.dumps(rc.SCHEMA, separators=(",", ":")))
                return rec.structured, node._usage(rec)
            node.classify_keeping(keep, sources, node.change_text(change), ask=ask, out=out / "keeping" / "classify")
    ck = make(f"{args.id}-c{n:02d}", commit, image)
    try:
        ck.export(meta["volumes"]["workspace"])
        plan = node.test_file_plan(ck.sh(f"cd {node.APP} && git diff --name-status -M {base} {commit}", check=False) or "")
        (out / "test_edits.json").write_text(json.dumps(plan, indent=1))
        summary["test_edits"] = {k: (v if k == "suite_config_changed" else len(v)) for k, v in plan.items()
                                 if k not in ("restore", "remove")}
        summary["doc_changes"] = node.doc_changes(ck.sh(f"cd {node.APP} && git diff --numstat {base} {commit}", check=False) or "")
        ids = node.grader_ids(ck)
        (out / "arm.diff").write_text(node.write_arm_diff(ck, base, commit, ids), encoding="utf-8")
        if args.no_keeping:
            summary["keeping"] = {"skipped": "--no-keeping"}
        else:
            record, summary["keeping"] = keeping(ck, args=args, meta=meta, n=n, base=base, image=image, change=change, graded=graded,
                                                 graded_dir=graded_dir, plan=plan, suites=suites, flaky=flaky,
                                                 reruns=reruns, make=make, out=out, classify=classify)
            (out / "keeping.json").write_text(json.dumps(record, indent=1))
        # from here on graders read code and tests only, whatever the arm, and no history
        prepared = node.prepare_for_graders(ck, ids)
        summary["hidden_from_graders"] = len(prepared["hidden"])
        summary["annotations_stripped"] = len(prepared["annotations_stripped"])
        if args.no_dependency:
            summary["dependency"] = {"result": None, "skipped": "--no-dependency"}
        else:
            dep = node.grade_dependency(ck, None if args.no_adapters else g, node.dependency_entries(graded, n) if graded else [],
                                        graded_dir, change, run_role=run_role, out=out / "dependency",
                                        adapter_notes=adapter_notes)
            (out / "dependency.json").write_text(json.dumps(dep, indent=1))
            summary["dependency"] = dep
        ck.sh("rm -rf /work/out/runs /work/grader", check=False)  # the grader's own runs stay out of the graders' view
        if args.no_probes:
            summary["probes_skipped"] = "--no-probes"
        elif not probes_path.is_file():
            summary["probes_skipped"] = f"no probes file at {probes_path}: the LLM-run probes didn't run"
        else:
            text = probes_path.read_text(encoding="utf-8")
            probeset = grading.parse_probes(text)
            applicable = [p for p in probeset.probes if p.applies(n) and not p.deferred]
            if not applicable:
                summary["probes_skipped"] = f"no probe in {probes_path} applies to change {n}"
            else:
                result = node.grade_probes(ck, g, probeset, applicable, change=change, out=out / "probes", volume=ck.volume,
                                           batch_size=args.batch_size, run_role=run_role, guards=guards,
                                           conditions=graded.get("row_conditions") or {}, options=node.probe_options(text))
                items = {item: v["verdict"] for item, v in result["items"].items()}
                summary["items"] = items
                summary["items_met"] = node.items_met(items, result["interface_faults"])
                summary.update(node.items_met_by_kind(items, result["interface_faults"], guards=guards))
                for k in ("guard_exempt", "implementation", "conflicts", "conditions", "missing_by_fault", "execution_faults"):
                    summary[k] = result[k]
                summary["probe_failed_setups"] = result["failed_setups"]
        dep = summary["dependency"]
        failed = [*({"kind": "probe", **f} for f in summary.get("probe_failed_setups") or []),
                  *({"kind": "dependency", **f} for f in dep.get("failed_setups") or [])]
        summary["failed_setups"] = failed
        items = summary.get("items") or {}
        summary["joint"] = node.joint_outcome(change, items, dep, guards=guards, rules=rules)
        summary["repair_reports"] = node.repair_reports(change, items, dep, failed)
    finally:
        if not args.keep:
            ck.drop()
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    k = summary.get("keeping") or {}
    print(f"{args.id} change {n}: implemented {summary['joint']['implemented']}, dependent behaviour "
          f"{summary['joint']['dependent_behaviour']}, keeping {k.get('passed')}/{k.get('counted')} "
          f"({k.get('failed')} failed, {k.get('not_loaded')} not loaded)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
