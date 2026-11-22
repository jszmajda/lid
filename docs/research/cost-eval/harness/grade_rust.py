"""Grade one change of a Rust-seed fork (or trajectory): keeping, the arm's edits to existing tests, and new intent.

    ../plumbing/with-token.sh python3.12 grade_rust.py --id cf-stripped-bare-200k-c03-r1

Reads the run's trajectory.json for the change's commit and starting commit, and the variant manifest it was forked
from for the held-out slice. Writes under ../runs/<id>/grading/change-NN/:

- keeping.json: each held-out test file run as a test target of its own against the arm's code, results per test,
  and compile failures apart (keeping/<target>.log holds cargo's output). A target that fails to build only because
  a struct literal or pattern lacks fields the arm added (E0063, E0027) or a match lacks variants it added (E0004)
  is adapted first,
  by the pre-registered rule in costeval/rust_adapt.py: each edit is recorded under the target's "adaptation", and
  the edited files are kept in keeping/adapted/. A target that still doesn't build is a compile failure, not
  adapted, with its reason; tests that reached an adapted wildcard arm are named. Each failing test is then
  classified by the pre-registered rule in costeval/rust_classify.py: "new state only" (the only difference its
  failure reports is state the change adds, at its empty value: reported, not counted against keeping) or "keeping
  failure", with the judge model's reason and evidence lines (keeping/classify/ holds what it read and answered);
  without the seed's change script (or with --no-classify) the failures stay unclassified. Compare it with the variant's
  keeping-baseline-<variant>.json, the same run on the untouched variant, for tests that never run (ignored, or
  gated off) and so never count;
- graded-targets.json: with a variant set's graded targets (M2f; m2f_graded_targets.py writes them to
  <variants>/graded, or --graded-dir), the change's own dependency probes and held-out tests still in force, each
  target put into the arm's checkout and built, adapted, run, and its failures classified exactly as keeping does
  (graded-targets/ holds the logs, adapted files, and the classifier's record); retired held-out tests and other
  changes' targets aren't run. Without a graded folder (the pilot's variant sets) the step is skipped, and the
  summary says why;
- test_edits.json: test files that existed at the start and that the arm edited, deleted, or renamed, with lines and
  #[test] functions before and after;
- probes/: the interface reference, each batch's probes as the executor saw them, each probe's test and output, the
  judgments, and verdicts.json (per probe and per item);
- visible_assertions.json: with the seed's hidden/kept-assertions.json (or --kept-assertions), each still-valid
  assertion listed for the change in a test the arm can see, kept, deleted, or weakened, with what replaced it;
- probes/implementation.json: the extraction's record, per graded item of the change (the oracle's live items with
  probes here), of whether the arm's diff implements anything addressing it;
- summary.json: the arm; the arm's changes to docs and instruction files (doc_changes: context for cost and
  attention, never graded, since graders see code and tests only); held-out retention (held_out_retention: passed, failed, keeping failures and new-state-only
  failures, compile failures not adapted, adaptations by error code, and the tests that reached a wildcard arm);
  new-intent items and kept-behaviour checks apart (the change script's "Kept behaviour" IDs), each with items met
  out of those with a verdict, "missing" ones counted apart and by fault, and beside them the items an interface
  fault left after the rerun, "not met (absent)" or missing; the probe helpers offered; and the visible-assertion
  audit. With graded targets: dependency_probes and held_out_tests, each test by its cargo name with its result
  ("passed", "failed" with the classifier's "class", "not built" with its "cause", or "not run"); dependency_met and
  held_out_tests_met (true when every one of the change's ran and passed, false when any ran and failed, null when
  some are missing and none failed, or the change has none); dependency_missing and held_out_tests_missing (each
  missing test with its cause: a target not built after adaptation, a test that didn't run, or a probe failing only
  on a precondition the change settles), outside the share, as keeping counts held-out tests it couldn't build;
  dependency_counts and held_out_tests_counts (passed, failed, missing and tests not built by cause, and the
  failures that don't count: settled preconditions, new state only); and graded_targets (the folder, the targets
  run, compile failures, adaptations), or graded_targets.skipped with the reason. A held-out test's failure is
  classified by keeping's rule; a probe's by its variant (prompts/keeping-classify-probe-rust.md). probes_skipped says why
  the LLM-executed probes didn't run when their file is absent; classification_skipped, when the change script
  doesn't have the change.

The probes are the seed's hidden/probes.md, in the format the other seeds use; those in force at the change run.
The seed files can each be named instead (--probes, --change-script, --kept-assertions, --oracle), as M2f's are
(seeds/clowder/hidden/m2f/). The checkpoint volume's build output is deleted at the end, and the volume too unless
--keep.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import executor, grading, rust_adapt as ra, rust_classify as rc, rust_grading as rg, simulator  # noqa: E402
from run_trajectory import CLAUDE_CODE, ROLES_VOLUME  # noqa: E402


def _held_out_test_counts(held_dir: Path, held: list[str]) -> dict[str, int]:
    return {f"heldout_{Path(p).stem}": len(re.findall(r"#\[test\]", (held_dir / p).read_text(encoding="utf-8")))
            for p in held}


Classify = Callable[[dict, dict[str, str], dict[str, dict[str, str]]], None]


def keeping(ck, held_dir: Path, held: list[str], out: Path | None = None, *, classify: Classify | None = None) -> dict:
    """Each held-out file as a target of its own against the arm's code, after the compile-only adaptation
    (costeval/rust_adapt.py) where the target fails to build only on what the rule covers. classify(result, logs,
    files), given, rules on the failing tests (costeval/rust_classify.py), with each target's log and files as run."""
    return run_targets(ck, rg.held_out_targets(held_dir, held), rg.held_out_target_names(held),
                       _held_out_test_counts(held_dir, held), out, classify=classify)


def graded(ck, graded_dir: Path, entries: list[dict], out: Path | None = None, *,
           classify: Classify | None = None, classify_probes: Classify | None = None) -> tuple[dict, dict]:
    """M2f's graded targets (graded.json's entries, as rg.graded_for_change picks them for the change) against the
    arm's code, through the keeping step's machinery: the held-out tests' failures classified by classify (keeping's
    rule), the dependency probes' by classify_probes (its probe variant). Returns the keeping result, both kinds
    together, and each test's result with the change's roll-ups (rg.graded_tests)."""
    results = []
    for kind, how in ((rg.DEPENDENCY_PROBE, classify_probes), (rg.HELD_OUT_TEST, classify)):
        chosen = [e for e in entries if e["kind"] == kind]
        if chosen:
            results.append(run_targets(ck, rg.graded_files(graded_dir, chosen), [(e["crate"], e["target"]) for e in chosen],
                                       {e["target"]: len(e["tests"]) for e in chosen}, out, classify=how))
    result = _merged(results)
    return result, rg.graded_tests(result, entries)


def _merged(results: list[dict]) -> dict:
    """Keeping results of separate runs as one: targets together, lists joined, counts added."""
    if not results:
        return {"targets": {}, "passed": 0, "failed": 0, "compile_failed": [], "compile_failed_not_adapted": {},
                "adapted": [], "adaptations_by_code": {}, "reached_adaptation_tests": [], "classified": False,
                "classification_cost_usd": None}
    out: dict = {"targets": {}, "compile_failed_not_adapted": {}, "adaptations_by_code": {}}
    for r in results:
        out["targets"].update(r["targets"])
        out["compile_failed_not_adapted"].update(r.get("compile_failed_not_adapted") or {})
        for code, k in (r.get("adaptations_by_code") or {}).items():
            out["adaptations_by_code"][code] = out["adaptations_by_code"].get(code, 0) + k
    for k in ("passed", "failed", "tests_not_built"):
        out[k] = sum(r.get(k) or 0 for r in results)
    for k in ("compile_failed", "adapted", "reached_adaptation_tests"):
        out[k] = sorted(x for r in results for x in r.get(k) or [])
    out["classified"] = all(r.get("classified") for r in results)
    costs = [r.get("classification_cost_usd") for r in results if r.get("classification_cost_usd") is not None]
    out["classification_cost_usd"] = round(sum(costs), 6) if costs else None
    return out


def run_targets(ck, files: dict[str, str], names: list[tuple[str, str]], expected: dict[str, int],
                out: Path | None = None, *, classify: Classify | None = None) -> dict:
    """Put these files into the arm's checkout, then build each (crate, target), adapting it where the rule covers
    what stops it, run it, and tally the results (rg.keeping_result), classifying failures when classify is given.
    expected: #[test] count per target. out, given, holds each target's log and its adapted files."""
    for path, text in files.items():
        ck.put(f"/work/app/{path}", text)
    sources: dict[str, str] = {}

    def arm_sources() -> dict[str, str]:
        if not sources:
            sources.update(ra.arm_sources(ck))
        return sources
    runs, adaptations, logs, files_run = [], {}, {}, {}
    for crate, target in names:
        own = {p: t for p, t in files.items()
               if p.startswith(f"crates/{crate}/tests/{target}/") or p == f"crates/{crate}/tests/{target}.rs"}
        cargo = (f"cd /work/app && CARGO_TARGET_DIR=/work/target timeout 1800 cargo test --offline "
                 f"--manifest-path crates/{crate}/Cargo.toml --test {target}")
        record, adapted = ra.adapt_target(lambda: ck.sh(f"{cargo} --no-run --message-format=json 2>&1", check=False),
                                          own, arm_sources, lambda p, t: ck.put(f"/work/app/{p}", t))
        adaptations[target], files_run[target] = record, adapted
        log = ck.sh(f"{cargo} --no-fail-fast 2>&1; echo EXIT=$?", check=False)
        runs.append((crate, target, log))
        logs[target] = log
        if out is not None:
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{target}.log").write_text(log)
            for path in sorted({e["file"] for e in record["edits"]}):
                dest = out / "adapted" / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(adapted[path])
    result = rg.keeping_result(runs, expected, adaptations)
    if classify is not None:
        classify(result, logs, files_run)
    else:
        result.update({"classified": False, "new_state_only": None, "keeping_failures": None, "share_kept": None})
    return result


def test_edits(ck, base: str, commit: str) -> dict:
    ns = ck.sh(f"cd /work/app && git diff --name-status -M {base} {commit}")
    num = ck.sh(f"cd /work/app && git diff --numstat -M {base} {commit}")
    revs = {"base": base, "head": commit}

    def count(rev: str, path: str) -> int:
        text = ck.sh(f"cd /work/app && (git show {revs[rev]}:'{path}' 2>/dev/null || true) | grep -c '#\\[test\\]' || true",
                     check=False)
        m = re.search(r"\d+", text or "")
        return int(m.group(0)) if m else 0
    return rg.test_edits(ns, num, count)


def graded_items(seed_dir: Path, n: int, meta: dict, probes: list, oracle: Path | None = None) -> list[tuple[str, str]]:
    """(ID, statement) for the change's graded items whose implementation the extraction records: the oracle's items
    live at the change that have probes here. A fork's diff starts from the snapshot, so the start's items, which the
    snapshot already has, are left out. oracle: the oracle's path (default <seed-dir>/hidden/oracle.md)."""
    oracle_path = oracle or seed_dir / "hidden" / "oracle.md"
    if not oracle_path.exists():
        return []
    oracle = simulator.parse_oracle(oracle_path.read_text(encoding="utf-8"))
    fork = meta.get("owner_scope") == simulator.FORK_SCOPE
    ids = {p.item.split()[0] for p in probes}
    return [(i.id, i.behavior) for i in simulator.released_items(oracle, n, only_change=fork)
            if i.id in ids and not (fork and i.in_force == 0)]


def main(argv=None, *, checkpoint=None, run_role=executor.run_role) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True)
    ap.add_argument("--change", type=int, help="default: the fork's change")
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    ap.add_argument("--seed-dir", type=Path, default=HERE.parent / "seeds" / "clowder")
    ap.add_argument("--probes", type=Path, help="default: <seed-dir>/hidden/probes.md")
    ap.add_argument("--change-script", type=Path, help="default: <seed-dir>/hidden/change-script.md")
    ap.add_argument("--no-classify", action="store_true", help="leave failing held-out tests unclassified")
    ap.add_argument("--kept-assertions", type=Path, help="default: <seed-dir>/hidden/kept-assertions.json")
    ap.add_argument("--guard-rows", type=Path, default=None,
                    help="guard-rows.json (M2f): keep-it-as-it-was rows, exempt from the absent-conflict rule and "
                         "counted apart from the new-behaviour rows")
    ap.add_argument("--reapply-guards", action="store_true",
                    help="give an existing grading the guard rows' exemption (needs --guard-rows), with no model call")
    ap.add_argument("--oracle", type=Path,
                    help="the oracle whose items the extraction is asked about; default: <seed-dir>/hidden/oracle.md")
    ap.add_argument("--graded-dir", type=Path,
                    help="the graded targets (M2f, from m2f_graded_targets.py); default: <variants>/graded when the run "
                         "was forked from a variant set")
    ap.add_argument("--no-graded", action="store_true", help="don't run the graded targets")
    ap.add_argument("--keeping-only", action="store_true",
                    help="run the held-out keeping step (and the graded targets) alone again, keeping the rest of the "
                         "change's summary; the earlier keeping.json and keeping/ stay beside it as keeping.<tag>, and "
                         "graded-targets.json and graded-targets/ as graded-targets.<tag>")
    ap.add_argument("--keeping-tag", default="before-rerun")
    ap.add_argument("--audit-only", action="store_true",
                    help="run the visible-assertion audit alone again, keeping the rest of the change's summary; the "
                         "earlier visible_assertions.json stays beside it as visible_assertions.<tag>.json")
    ap.add_argument("--audit-tag", default="before-content")
    ap.add_argument("--no-keeping", action="store_true")
    ap.add_argument("--no-probes", action="store_true")
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--execute-model", default="claude-haiku-5-5")
    ap.add_argument("--judge-model", default="claude-sonnet-5-5")
    ap.add_argument("--keep", action="store_true", help="keep the checkpoint volume afterwards")
    args = ap.parse_args(argv)

    run = args.runs / args.id
    meta = json.loads((run / "trajectory.json").read_text())
    n = args.change if args.change is not None else meta.get("change")
    if n is None:
        ap.error("--change is needed for a trajectory")
    commit, base = meta["changes"][str(n)]["commit"], meta["start_commit"]
    out = run / "grading" / f"change-{n:02d}"
    if args.reapply_guards:  # an earlier grading given the guard rows' exemption, with no new model call
        if not args.guard_rows or not (out / "summary.json").exists():
            ap.error("--reapply-guards needs --guard-rows and a grading to reapply them to")
        guards = set((json.loads(args.guard_rows.read_text()).get("rows") or {}))
        probes_path = args.probes or args.seed_dir / "hidden" / "probes.md"
        probes = [p for p in grading.parse_probes(probes_path.read_text(encoding="utf-8")).probes if p.applies(n)]
        script_path = args.change_script or args.seed_dir / "hidden" / "change-script.md"
        kept = rg.kept_behaviour_ids(script_path.read_text(encoding="utf-8")) if script_path.exists() else set()
        s = rg.reapply_guards(out, probes, guards=guards, kept=kept)
        print(f"{args.id}: guard exemption reapplied to {s['guard_exempt'] or 'no probe'}; items {s['items']}")
        return 0
    out.mkdir(parents=True, exist_ok=True)
    image = meta.get("image") or "lid-cost-eval-executor-rust:2.1.323"
    make = checkpoint or (lambda name, c, img: rg.RustCheckpoint(name=name, commit=c, image=img))
    ck = make(f"{args.id}-c{n:02d}", commit, image)
    ck.export(meta["volumes"]["workspace"])
    summary: dict = {"id": args.id, "change": n, "arm": meta.get("arm"), "commit": commit, "start_commit": base}

    def sha(path: Path) -> str | None:
        return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    probes_file = args.probes or args.seed_dir / "hidden" / "probes.md"
    summary["seed_files"] = {"probes_sha256": sha(probes_file),
                             "kept_assertions_sha256": sha(args.kept_assertions or args.seed_dir / "hidden" / "kept-assertions.json"),
                             "change_script_sha256": sha(args.change_script or args.seed_dir / "hidden" / "change-script.md")}
    if args.oracle:
        summary["seed_files"]["oracle_sha256"] = sha(args.oracle)
    g = rg.RustGraders(image=image, roles_volume=ROLES_VOLUME, claude_code=CLAUDE_CODE,
                       execute_model=args.execute_model, judge_model=args.judge_model)
    script_path = args.change_script or args.seed_dir / "hidden" / "change-script.md"
    # a classify writing its record under the folder given; probe=True: the dependency probes' variant of the rule
    classifier: Callable[..., Classify] | None = None
    if not args.no_classify and script_path.exists():
        script = simulator.parse_change_script(script_path.read_text(encoding="utf-8"))
        if n in script:
            change = rc.change_text(script[n])

            def classifier(dest: Path, probe: bool = False) -> Classify:
                classes, template = (rc.PROBE_CLASSES, rc.PROBE_TEMPLATE) if probe else (rc.CLASSES, rc.TEMPLATE)
                schema = json.dumps(rc.schema(classes), separators=(",", ":"))

                def ask(prompt: str):
                    rec = run_role(g.role(g.judge_model, timeout_s=1200), prompt, json_schema=schema)
                    return rec.structured, rg._usage(rec)
                return lambda result, logs, files: rc.classify(result, logs, files, change, ask=ask, out=dest,
                                                               template=template, classes=classes)
        else:
            summary["classification_skipped"] = f"no change {n} in {script_path}"
    classify = classifier(out / "keeping" / "classify") if classifier else None
    try:
        if not args.keeping_only:
            edits = test_edits(ck, base, commit)
            (out / "test_edits.json").write_text(json.dumps(edits, indent=1))
            summary["test_edits"] = {k: edits[k] if isinstance(edits[k], int) else len(edits[k]) for k in edits}
            kept_path = args.kept_assertions or args.seed_dir / "hidden" / "kept-assertions.json"
            entries = rg.load_kept_assertions(kept_path).get(n, []) if kept_path.exists() else []
            if entries:
                shown: dict[tuple[str, str], str | None] = {}  # each file once per commit: the search reads a crate's tests

                def show(rev: str, path: str) -> str | None:
                    if (rev, path) not in shown:
                        shown[(rev, path)] = ck.sh(f"cd /work/app && git show {rev}:'{path}' 2>/dev/null", check=False) or None
                    return shown[(rev, path)]
                listed_tests: dict[tuple[str, str], list[str]] = {}

                def list_tests(rev: str, crate: str) -> list[str]:
                    if (rev, crate) not in listed_tests:
                        listed = ck.sh(f"cd /work/app && git ls-tree -r --name-only {rev} -- '{crate}/tests'", check=False)
                        listed_tests[(rev, crate)] = [f for f in listed.split() if f.endswith(".rs")]
                    return listed_tests[(rev, crate)]
                audit = rg.audit_visible_assertions(entries, show, base=base, head=commit,
                                                    renamed={a: b for a, b in edits["renamed"]}, list_tests=list_tests)
                if args.audit_only and (out / "visible_assertions.json").exists() \
                        and not (out / f"visible_assertions.{args.audit_tag}.json").exists():
                    (out / "visible_assertions.json").rename(out / f"visible_assertions.{args.audit_tag}.json")
                (out / "visible_assertions.json").write_text(json.dumps(audit, indent=1))
                summary["visible_assertions"] = {k: audit[k] for k in ("kept", "moved", "moved_sharing_nothing_else",
                                                                       "deleted", "weakened", "not_found_at_start",
                                                                       "flagged", "moves")}
        if args.audit_only:  # the rest of the earlier summary stands
            earlier = json.loads((out / "summary.json").read_text()) if (out / "summary.json").exists() else {}
            earlier["visible_assertions"] = summary.get("visible_assertions")
            earlier["audit_rerun"] = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                      "earlier_kept_as": f"visible_assertions.{args.audit_tag}.json",
                                      "seed_files": summary["seed_files"]}
            summary = earlier
        else:
            # from here on graders read code and tests only, whatever the arm, and no history
            manifest_path = Path((meta.get("fork_of") or {}).get("variants") or "") / "manifest.json"
            manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
            pattern = (((manifest.get("variants") or {}).get("stripped") or {}).get("report") or {}).get("spec_id_pattern")
            prepared = rg.prepare_for_graders(ck, base, commit, spec_pattern=pattern)
            summary["stripped_for_graders"] = prepared["stripped"]
            summary["doc_changes"] = prepared["doc_changes"]
            summary["hidden_from_graders"] = len(prepared["hidden"])
            (out / "arm.diff").write_text(ck.get("/work/out/arm.diff") or "", encoding="utf-8")  # what the extraction read
            variants = Path((meta.get("fork_of") or {}).get("variants") or "")
            if not args.no_keeping and (variants / "manifest.json").exists():
                if args.keeping_only:  # the earlier keeping stays beside the new one
                    for name, kept_as in (("keeping.json", f"keeping.{args.keeping_tag}.json"), ("keeping", f"keeping.{args.keeping_tag}")):
                        if (out / name).exists() and not (out / kept_as).exists():
                            (out / name).rename(out / kept_as)
                        elif (out / name).is_dir():
                            shutil.rmtree(out / name)
                held = json.loads((variants / "manifest.json").read_text()).get("held_out") or []
                keep = keeping(ck, variants / "held-out", held, out / "keeping", classify=classify)
                (out / "keeping.json").write_text(json.dumps(keep, indent=1))
                summary["held_out_retention"] = {k: keep.get(k) for k in (
                    "passed", "failed", "keeping_failures", "new_state_only", "classified", "compile_failed",
                    "compile_failed_not_adapted", "tests_not_built", "tests_not_built_by_cause", "adapted", "adaptations_by_code",
                    "reached_adaptation", "reached_adaptation_tests", "share_passed", "share_kept",
                    "share_of_held_out_passed", "classification_cost_usd")}
            forked = bool((meta.get("fork_of") or {}).get("variants"))
            graded_dir = args.graded_dir or (variants / "graded" if forked else None)
            if args.no_graded:
                summary["graded_targets"] = {"skipped": "--no-graded"}
            elif graded_dir is None:
                summary["graded_targets"] = {"skipped": "no graded targets: the run wasn't forked from a variant set, "
                                                        "and no --graded-dir"}
            elif not (graded_dir / rg.GRADED_JSON).is_file():
                summary["graded_targets"] = {"skipped": f"no graded targets: {graded_dir / rg.GRADED_JSON} doesn't exist"}
            else:
                if args.keeping_only:  # the earlier run stays beside the new one
                    for name, kept_as in (("graded-targets.json", f"graded-targets.{args.keeping_tag}.json"),
                                          ("graded-targets", f"graded-targets.{args.keeping_tag}")):
                        if (out / name).exists() and not (out / kept_as).exists():
                            (out / name).rename(out / kept_as)
                        elif (out / name).is_dir():
                            shutil.rmtree(out / name)
                chosen = rg.graded_for_change(rg.load_graded(graded_dir), n)
                dest = out / "graded-targets" / "classify"
                result, fields = graded(ck, graded_dir, chosen, out / "graded-targets",
                                        classify=classifier(dest) if classifier else None,
                                        classify_probes=classifier(dest, probe=True) if classifier else None)
                (out / "graded-targets.json").write_text(json.dumps({"dir": str(graded_dir), "entries": chosen, **result},
                                                                    indent=1))
                summary.update(fields)
                summary["graded_targets"] = {
                    "dir": str(graded_dir), "graded_sha256": sha(graded_dir / rg.GRADED_JSON),
                    "targets": [e["target"] for e in chosen],
                    **{k: result.get(k) for k in ("compile_failed", "compile_failed_not_adapted", "adapted",
                                                  "adaptations_by_code", "reached_adaptation_tests", "classified",
                                                  "classification_cost_usd")}}
            if args.keeping_only:  # the rest of the earlier summary stands
                earlier = json.loads((out / "summary.json").read_text()) if (out / "summary.json").exists() else {}
                for k in ("dependency_probes", "dependency_met", "dependency_missing", "dependency_counts",
                          "held_out_tests", "held_out_tests_met", "held_out_tests_missing", "held_out_tests_counts",
                          "graded_targets", "classification_skipped"):
                    if k in summary:
                        earlier[k] = summary[k]
                earlier["held_out_retention"] = summary.get("held_out_retention")
                earlier["keeping_rerun"] = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                            "earlier_kept_as": f"keeping.{args.keeping_tag}.json",
                                            "seed_files": summary["seed_files"]}
                summary = earlier
            probes_path = args.probes or args.seed_dir / "hidden" / "probes.md"
            guards = set((json.loads(args.guard_rows.read_text()).get("rows") or {})) if args.guard_rows else set()
            if not args.no_probes and not args.keeping_only and not probes_path.exists():
                summary["probes_skipped"] = f"no probes file at {probes_path}: the LLM-executed probes didn't run"
            if not args.no_probes and not args.keeping_only and probes_path.exists():
                probeset = grading.parse_probes(probes_path.read_text(encoding="utf-8"))
                applicable = [p for p in probeset.probes if p.applies(n) and not p.deferred]
                if applicable:
                    held_dir = variants / "held-out"
                    helpers = (rg.place_probe_helpers(ck, rg.snapshot_helpers(held_dir), sources=lambda: ra.arm_sources(ck))
                               if held_dir.is_dir() else {})
                    summary["probe_helpers"] = {c: h["status"] for c, h in helpers.items()}
                    result = rg.grade_probes(ck, g, probeset, applicable, base=base, out=out / "probes", volume=ck.volume,
                                             batch_size=args.batch_size, run_role=run_role, helpers=helpers,
                                             items=graded_items(args.seed_dir, n, meta, applicable, oracle=args.oracle),
                                             guards=guards)
                    items = {item: v["verdict"] for item, v in result["items"].items()}
                    kept = rg.kept_behaviour_ids(script_path.read_text(encoding="utf-8")) if script_path.exists() else set()
                    summary["items"], summary["kept_behaviour_checks"] = rg.split_items(items, kept)
                    summary["items_met"] = rg.items_met(summary["items"], result["interface_faults"])
                    if guards:  # the new-behaviour rows and the guard rows apart, beside the total
                        summary.update(rg.items_met_by_kind(summary["items"], result["interface_faults"], guards=guards))
                        summary["guard_exempt"] = result.get("guard_exempt", [])
                    summary["kept_behaviour_met"] = rg.items_met(summary["kept_behaviour_checks"], result["interface_faults"])
                    summary["implementation"] = result["implementation"]
                    summary["conflicts"] = result["conflicts"]  # both rulings, for a spot-check
                    summary["missing_by_fault"] = result["missing_by_fault"]
                    summary["execution_faults"] = result["execution_faults"]
    finally:
        ck.drop_target()
        if not args.keep and checkpoint is None:
            subprocess.run(["docker", "volume", "rm", "-f", ck.volume], capture_output=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
