"""Draw met verdicts from the final Rust-seed gradings for a blind spot-check, and write each as a packet.

    python3.12 spotcheck_sample.py --out <scratch>/spotcheck-sample --index <scratch>/spotcheck-sample-index.json

The draw is seeded and stratified: each of the six cells (variant, arm, window) gives an equal share of the n items, the
remainder going to cells chosen with the same seed, so 20 from six cells is 3 or 4 each. Only items the grading ruled
met are drawn, and none the extraction recorded as absent from the change's code (those are conflicts already). The
packets go in a shuffled order, NN/, each in the spot-check format: the item, the probes as the executor saw them, the
code diff the extraction read, each probe's test and full output, the judge's rulings, and the extraction's record. A
grading made before arm.diff was kept with it has its diff rebuilt from the fork's workspace (Docker, no model). The
index from NN to fork and item is written apart from the packets. A blindness scan lists every word in a packet that
could name an arm, LID, or specs, for a reader to clear.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import rust_grading as rg  # noqa: E402

CELLS = ("stripped-bare-1m", "full-bare-1m", "full-lid-full-1m", "stripped-bare-200k", "full-bare-200k",
         "full-lid-full-200k")
TELLS = re.compile(r"@spec\b|\bLID\b|linked[- ]intent|\bspecs?\b|\bdocs/|\bintent\b|\barrows?\b(?!\s+keys?\b)|\bEARS\b"
                   r"|\bHLD\b|\bLLD\b|AGENTS\.md|CLAUDE\.md|GEMINI\.md|\.claude\b|\bstripped\b|lid-full|\bcf-[a-z]"
                   r"|\b1m\b|\b200k\b|\bjj\b", re.I)
README = """# Spot-check: {item}

The grading ruled this item met. Decide whether that is right: does the change's code do what the item asks, and do the
probes' outputs show it, produced by the build rather than by the test?

| File | What it is |
|---|---|
| `01-item.md` | The item's row, the change's request, and the change script's lines naming the item |
| `02-probes-as-executor-saw-them.md` | The batch files the executor read: conventions, the setups in full, and the scenarios (no expected observations) |
| `03-code-diff.diff` | The change's code and tests, as the extraction read it: a diff between the starting and finished trees, both stripped the same way (no docs, no agent files, no spec IDs) |
| `04-executor-test-<probe>.rs` | The test the executor wrote for each probe |
| `05-executor-output-<probe>.log` | Each test's full output, as the harness ran it |
| `06-judge-rulings.json` | The judge's ruling on each probe, with the probe's text including its expected observation |
| `07-extraction-record.json` | The extraction's record for the item: its status, the files and symbols it cites, and its note |
"""


def probe_target(pid: str) -> str:
    return rg.probe_target(pid)


def _grading(runs: Path, fid: str, n: int) -> Path:
    return runs / fid / "grading" / f"change-{n:02d}"


def candidates(runs: Path, cells=CELLS) -> list[dict]:
    """Every met item in the cells' final gradings, less those the extraction recorded absent."""
    out = []
    for cell in cells:
        for run in sorted(runs.glob(f"cf-{cell}-c[0-9][0-9]-r1")):
            meta = json.loads((run / "trajectory.json").read_text())
            n = meta["change"]
            g = _grading(runs, run.name, n) / "summary.json"
            if not g.exists():
                continue
            s = json.loads(g.read_text())
            implementation = s.get("implementation") or {}
            for item, verdict in {**(s.get("items") or {}), **(s.get("kept_behaviour_checks") or {})}.items():
                if verdict == "met" and implementation.get(item.split()[0]) != "absent":
                    out.append({"fork": run.name, "cell": cell, "change": n, "item": item})
    return out


def draw(cands: list[dict], n: int, seed: str, cells=CELLS) -> list[dict]:
    """n items, an equal share per cell and the remainder to cells chosen by the seed, in a shuffled order."""
    rng = random.Random(seed)
    cells = sorted(cells)
    base, extra = divmod(n, len(cells))
    more = set(rng.sample(cells, extra))
    picked = []
    for cell in cells:
        pool = sorted((c for c in cands if c["cell"] == cell), key=lambda c: (c["fork"], c["item"]))
        picked += rng.sample(pool, min(base + (cell in more), len(pool)))
    rng.shuffle(picked)
    return picked


def rebuild_diff(runs: Path, fid: str) -> str:
    """The code diff the extraction read, rebuilt from the fork's workspace: the same stripping, a scratch checkpoint."""
    meta = json.loads((runs / fid / "trajectory.json").read_text())
    manifest = json.loads((Path(meta["fork_of"]["variants"]) / "manifest.json").read_text())
    n = meta["change"]
    ck = rg.RustCheckpoint(name=f"spot-{fid}", commit=meta["changes"][str(n)]["commit"],
                           image=meta.get("image") or "lid-cost-eval-executor-rust:2.1.323")
    try:
        ck.export(meta["volumes"]["workspace"])
        rg.prepare_for_graders(ck, meta["start_commit"], meta["changes"][str(n)]["commit"],
                               spec_pattern=manifest["variants"]["stripped"]["report"]["spec_id_pattern"])
        return ck.get("/work/out/arm.diff") or ""
    finally:
        subprocess.run(["docker", "volume", "rm", "-f", ck.volume], capture_output=True)


def _item_text(seed_dir: Path, item: str, change: int) -> str:
    iid = item.split()[0]
    rows = []
    for name in ("oracle.md", "kept-behaviour.md"):
        f = seed_dir / "hidden" / name
        if f.exists():
            text = f.read_text(encoding="utf-8")
            hit = [l for l in text.splitlines() if l.startswith(f"| {iid} ")]
            if hit:
                header = next((l for l in text.splitlines() if l.startswith("| ID ")), "")
                rows = [header, "|---" * max(1, header.count("|") - 1) + "|", *hit]
                break
    script = (seed_dir / "hidden" / "change-script.md").read_text(encoding="utf-8")
    sec = re.search(rf"(?ms)^## Change {change}\b.*?(?=^## |\Z)", script)
    sec = sec.group(0) if sec else ""
    request = re.search(r"(?ms)^### Owner request\s*\n(.*?)(?=^\*\*|^### |\Z)", sec)
    lines = [l.strip() for l in sec.splitlines() if iid in l]
    return ("# The item\n\n## Its row\n\n" + ("\n".join(rows) or "(no row found)") + "\n\n## The change's request\n\n"
            + (request.group(1).strip() if request else "(none found)") + "\n\n## Change script lines naming the item\n\n"
            + ("\n".join(f"- {l}" for l in lines) or "(none)") + "\n")


def write_packets(drawn: list[dict], out: Path, index: Path, *, runs: Path, seed_dir: Path,
                  diff_for: Callable[[str], str] | None = None) -> dict[str, list[dict]]:
    """One packet per drawn item under out/NN/, the index apart, and the blindness scan's hits by packet."""
    out.mkdir(parents=True, exist_ok=True)
    probes_md = (seed_dir / "hidden" / "probes.md").read_text(encoding="utf-8")
    mapping, hits = {}, {}
    for k, c in enumerate(drawn, start=1):
        nn = f"{k:02d}"
        d = out / nn
        d.mkdir(parents=True, exist_ok=True)
        g = _grading(runs, c["fork"], c["change"])
        verdicts = json.loads((g / "probes" / "verdicts.json").read_text())
        pids = sorted((verdicts["items"].get(c["item"]) or {}).get("probes") or {})
        details = verdicts.get("details") or {}
        (d / "README.md").write_text(README.format(item=c["item"]))
        (d / "01-item.md").write_text(_item_text(seed_dir, c["item"], c["change"]))
        batches = sorted({details.get(pid, {}).get("batch") for pid in pids} - {None})
        (d / "02-probes-as-executor-saw-them.md").write_text("\n\n".join(
            f"<!-- A batch file the executor read; the probes under check: {', '.join(pids)}. -->\n\n"
            + (g / "probes" / b / "probes.md").read_text() for b in batches))
        diff = g / "arm.diff"
        (d / "03-code-diff.diff").write_text(diff.read_text() if diff.exists() else (diff_for or (lambda f: rebuild_diff(runs, f)))(c["fork"]))
        rulings = []
        for pid in pids:
            b = details.get(pid, {}).get("batch")
            t = probe_target(pid)
            for src, dest in ((f"{t}.rs", f"04-executor-test-{pid}.rs"), (f"{t}.log", f"05-executor-output-{pid}.log")):
                if b and (g / "probes" / b / src).exists():
                    (d / dest).write_text((g / "probes" / b / src).read_text())
            text = re.search(rf"(?ms)^#### {re.escape(pid)}\n.*?(?=^#### |^### |\Z)", probes_md)
            rulings.append({"probe": pid, "ruling": {k2: v for k2, v in details.get(pid, {}).items() if k2 != "batch"},
                            "probe_with_expected_observation": text.group(0) if text else None})
        (d / "06-judge-rulings.json").write_text(json.dumps(rulings, indent=1))
        impl = json.loads((g / "probes" / "implementation.json").read_text()) if (g / "probes" / "implementation.json").exists() else {}
        rec = next((e for e in (impl.get("record") or {}).get("items", []) if e.get("item") == c["item"].split()[0]), None)
        (d / "07-extraction-record.json").write_text(json.dumps({"status": (impl.get("statuses") or {}).get(c["item"].split()[0]),
                                                                 "record": rec}, indent=1))
        mapping[nn] = {"fork": c["fork"], "item": c["item"], "cell": c["cell"]}
        found = blindness_scan(d)
        if found:
            hits[nn] = found
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(json.dumps(mapping, indent=1))
    return hits


def blindness_scan(packet: Path, spec_pattern: str | None = None) -> list[dict]:
    """Every word in a packet's files that could name an arm, LID, or specs: for a reader to clear or redact."""
    pattern = re.compile(TELLS.pattern + (f"|{spec_pattern}" if spec_pattern else ""), re.I)
    hits = []
    for f in sorted(packet.iterdir()):
        if f.name == "README.md":
            continue
        for k, line in enumerate(f.read_text(errors="replace").splitlines(), start=1):
            for m in pattern.finditer(line):
                hits.append({"file": f.name, "line": k, "word": m.group(0), "text": line.strip()[:160]})
    return hits


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    ap.add_argument("--seed-dir", type=Path, default=HERE.parent / "seeds" / "clowder")
    ap.add_argument("--out", type=Path, required=True, help="the packets' folder (NN/ inside it)")
    ap.add_argument("--index", type=Path, required=True, help="where the NN-to-fork map goes, apart from the packets")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", default="spotcheck-1")
    args = ap.parse_args(argv)
    if args.index.resolve().is_relative_to(args.out.resolve()):
        ap.error("the index must live outside the packets' folder")
    drawn = draw(candidates(args.runs), args.n, args.seed)
    manifest = json.loads((args.runs / "clowder-variants" / "v1" / "manifest.json").read_text())
    hits = write_packets(drawn, args.out, args.index, runs=args.runs, seed_dir=args.seed_dir)
    pattern = manifest["variants"]["stripped"]["report"]["spec_id_pattern"]
    for nn in sorted(p.name for p in args.out.iterdir() if p.is_dir()):
        more = [h for h in blindness_scan(args.out / nn, pattern) if h not in hits.get(nn, [])]
        if more:
            hits.setdefault(nn, []).extend(more)
    print(json.dumps({"drawn": len(drawn), "per_cell": {c: sum(d["cell"] == c for d in drawn) for c in CELLS},
                      "scan_hits": hits}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
