#!/usr/bin/env python3
"""Materialize the lid-coach iteration-1 eval projects from evals.json.

For each eval, creates eval-<id>-<name>/{with_skill,without_skill}/{project,outputs}/
and writes the eval's `files` into each project/ tree, plus eval_metadata.json.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).parent
EVALS = json.loads(
    (ROOT.parent.parent / "lid-coach" / "evals" / "evals.json").read_text()
)

for ev in EVALS["evals"]:
    name = f"eval-{ev['id']}-{ev['eval_name']}"
    eval_dir = ROOT / name
    eval_dir.mkdir(exist_ok=True)
    (eval_dir / "eval_metadata.json").write_text(
        json.dumps(
            {
                "eval_id": ev["id"],
                "eval_name": ev["eval_name"],
                "prompt": ev["prompt"],
                "assertions": ev["assertions"],
            },
            indent=2,
        )
    )
    for cfg in ("with_skill", "without_skill"):
        proj = eval_dir / cfg / "project"
        out = eval_dir / cfg / "outputs"
        proj.mkdir(parents=True, exist_ok=True)
        out.mkdir(parents=True, exist_ok=True)
        for f in ev.get("files", []):
            fp = proj / f["path"]
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(f["content"])

print(f"Materialized {len(EVALS['evals'])} evals under {ROOT}")
for ev in EVALS["evals"]:
    print(f"  eval-{ev['id']}-{ev['eval_name']}  ({len(ev.get('files', []))} files)")
