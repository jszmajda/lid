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
- test_edits.json: test files that existed at the start and that the arm edited, deleted, or renamed, with lines and
  #[test] functions before and after;
- probes/: the interface reference, each batch's probes as the executor saw them, each probe's test and output, the
  judgments, and verdicts.json (per probe and per item);
- visible_assertions.json: with the seed's hidden/kept-assertions.json (or --kept-assertions), each still-valid
  assertion listed for the change in a test the arm can see, kept, deleted, or weakened, with what replaced it;
- summary.json: the arm; held-out retention (held_out_retention: passed, failed, keeping failures and new-state-only
  failures, compile failures not adapted, adaptations by error code, and the tests that reached a wildcard arm);
  new-intent items and kept-behaviour checks apart (the change script's "Kept behaviour" IDs), each with items met
  out of those with a verdict, "missing" ones counted apart and by fault; the probe helpers offered; and the
  visible-assertion audit.

The probes are the seed's hidden/probes.md, in the format the other seeds use; those in force at the change run.
The checkpoint volume's build output is deleted at the end, and the volume too unless --keep.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import executor, grading, rust_adapt as ra, rust_classify as rc, rust_grading as rg, simulator  # noqa: E402
from run_trajectory import CLAUDE_CODE, ROLES_VOLUME  # noqa: E402


def _held_out_test_counts(held_dir: Path, held: list[str]) -> dict[str, int]:
    return {f"heldout_{Path(p).stem}": len(re.findall(r"#\[test\]", (held_dir / p).read_text(encoding="utf-8")))
            for p in held}


def keeping(ck, held_dir: Path, held: list[str], out: Path | None = None, *,
            classify: Callable[[dict, dict[str, str], dict[str, dict[str, str]]], None] | None = None) -> dict:
    """Each held-out file as a target of its own against the arm's code, after the compile-only adaptation
    (costeval/rust_adapt.py) where the target fails to build only on what the rule covers. classify(result, logs,
    files), given, rules on the failing tests (costeval/rust_classify.py), with each target's log and files as run."""
    files = rg.held_out_targets(held_dir, held)
    for path, text in files.items():
        ck.put(f"/work/app/{path}", text)
    sources: dict[str, str] = {}

    def arm_sources() -> dict[str, str]:
        if not sources:
            sources.update(ra.arm_sources(ck))
        return sources
    runs, adaptations, logs, files_run = [], {}, {}, {}
    for crate, target in rg.held_out_target_names(held):
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
    result = rg.keeping_result(runs, _held_out_test_counts(held_dir, held), adaptations)
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
    out.mkdir(parents=True, exist_ok=True)
    image = meta.get("image") or "lid-cost-eval-executor-rust:2.1.323"
    make = checkpoint or (lambda name, c, img: rg.RustCheckpoint(name=name, commit=c, image=img))
    ck = make(f"{args.id}-c{n:02d}", commit, image)
    ck.export(meta["volumes"]["workspace"])
    summary: dict = {"id": args.id, "change": n, "arm": meta.get("arm"), "commit": commit, "start_commit": base}
    g = rg.RustGraders(image=image, roles_volume=ROLES_VOLUME, claude_code=CLAUDE_CODE,
                       execute_model=args.execute_model, judge_model=args.judge_model)
    script_path = args.change_script or args.seed_dir / "hidden" / "change-script.md"
    classify = None
    if not args.no_classify and script_path.exists():
        change = rc.change_text(simulator.parse_change_script(script_path.read_text(encoding="utf-8"))[n])

        def ask(prompt: str):
            rec = run_role(g.role(g.judge_model, timeout_s=1200), prompt,
                           json_schema=json.dumps(rc.SCHEMA, separators=(",", ":")))
            return rec.structured, rg._usage(rec)

        def classify(result, logs, files):
            rc.classify(result, logs, files, change, ask=ask, out=out / "keeping" / "classify")
    try:
        edits = test_edits(ck, base, commit)
        (out / "test_edits.json").write_text(json.dumps(edits, indent=1))
        summary["test_edits"] = {k: edits[k] if isinstance(edits[k], int) else len(edits[k]) for k in edits}
        kept_path = args.kept_assertions or args.seed_dir / "hidden" / "kept-assertions.json"
        entries = rg.load_kept_assertions(kept_path).get(n, []) if kept_path.exists() else []
        if entries:
            def show(rev: str, path: str) -> str | None:
                return ck.sh(f"cd /work/app && git show {rev}:'{path}' 2>/dev/null", check=False) or None
            audit = rg.audit_visible_assertions(entries, show, base=base, head=commit,
                                                renamed={a: b for a, b in edits["renamed"]})
            (out / "visible_assertions.json").write_text(json.dumps(audit, indent=1))
            summary["visible_assertions"] = {k: audit[k] for k in ("kept", "deleted", "weakened", "not_found_at_start",
                                                                   "flagged")}
        variants = Path((meta.get("fork_of") or {}).get("variants") or "")
        if not args.no_keeping and (variants / "manifest.json").exists():
            held = json.loads((variants / "manifest.json").read_text()).get("held_out") or []
            keep = keeping(ck, variants / "held-out", held, out / "keeping", classify=classify)
            (out / "keeping.json").write_text(json.dumps(keep, indent=1))
            summary["held_out_retention"] = {k: keep.get(k) for k in (
                "passed", "failed", "keeping_failures", "new_state_only", "classified", "compile_failed",
                "compile_failed_not_adapted", "tests_not_built", "adapted", "adaptations_by_code",
                "reached_adaptation", "reached_adaptation_tests", "share_passed", "share_kept",
                "share_of_held_out_passed", "classification_cost_usd")}
        probes_path = args.probes or args.seed_dir / "hidden" / "probes.md"
        if not args.no_probes and probes_path.exists():
            probeset = grading.parse_probes(probes_path.read_text(encoding="utf-8"))
            applicable = [p for p in probeset.probes if p.applies(n) and not p.deferred]
            if applicable:
                held_dir = variants / "held-out"
                helpers = (rg.place_probe_helpers(ck, rg.snapshot_helpers(held_dir), sources=lambda: ra.arm_sources(ck))
                           if held_dir.is_dir() else {})
                summary["probe_helpers"] = {c: h["status"] for c, h in helpers.items()}
                result = rg.grade_probes(ck, g, probeset, applicable, base=base, out=out / "probes", volume=ck.volume,
                                         batch_size=args.batch_size, run_role=run_role, helpers=helpers)
                items = {item: v["verdict"] for item, v in result["items"].items()}
                kept = rg.kept_behaviour_ids(script_path.read_text(encoding="utf-8")) if script_path.exists() else set()
                summary["items"], summary["kept_behaviour_checks"] = rg.split_items(items, kept)
                summary["items_met"] = rg.items_met(summary["items"])
                summary["kept_behaviour_met"] = rg.items_met(summary["kept_behaviour_checks"])
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
