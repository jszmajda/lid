#!/usr/bin/env python3
"""Restructure config dirs into the run-1/ layout the aggregator expects,
and add the `summary` block to grading.json. Idempotent.

Target: eval-<name>/<config>/run-1/{outputs/, grading.json, timing.json}
"""
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).parent

for eval_dir in sorted(ROOT.glob("eval-*")):
    if not eval_dir.is_dir():
        continue
    for cfg in ("with_skill", "without_skill"):
        cfg_dir = eval_dir / cfg
        if not cfg_dir.is_dir():
            continue
        run_dir = cfg_dir / "run-1"
        run_dir.mkdir(exist_ok=True)

        # Move outputs/ under run-1/ (so viewer discovers run-1 as the run)
        src_out = cfg_dir / "outputs"
        dst_out = run_dir / "outputs"
        if src_out.is_dir() and not dst_out.exists():
            shutil.move(str(src_out), str(dst_out))

        # Move timing.json into run-1/
        src_t = cfg_dir / "timing.json"
        if src_t.exists():
            shutil.move(str(src_t), str(run_dir / "timing.json"))

        # Rewrite grading.json with a summary block, into run-1/
        src_g = cfg_dir / "grading.json"
        if src_g.exists():
            g = json.loads(src_g.read_text())
            passed = g.get("passed", sum(
                1 for e in g.get("expectations", []) if e.get("passed")))
            total = g.get("total", len(g.get("expectations", [])))
            g["summary"] = {"passed": passed, "total": total,
                            "pass_rate": round(passed / total, 4) if total else 0}
            (run_dir / "grading.json").write_text(json.dumps(g, indent=2))
            src_g.unlink()

        # project/ stays at config level (unused by aggregator/viewer)

print("Restructured. Layout sample:")
for p in sorted((ROOT / "eval-0-unconfigured-project-recommends-setup").rglob("*")):
    if p.is_file():
        print("  " + str(p.relative_to(ROOT)))
