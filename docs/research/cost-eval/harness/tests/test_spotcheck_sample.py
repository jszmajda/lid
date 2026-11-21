"""spotcheck_sample.py: a seeded, stratified draw of met verdicts for a blind spot-check, written as packets."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import spotcheck_sample as ss  # noqa: E402

CELLS = ["stripped-bare-1m", "full-bare-1m", "full-lid-full-1m", "stripped-bare-200k", "full-bare-200k",
         "full-lid-full-200k"]
ORACLE = """# Oracle

| ID | Checkable behavior | Disclosure kind | In force | Retired | External check sketch |
|---|---|---|---|---|---|
| CLW-101 | Crafting leaves a chosen reserve. | Stated in change 1 | Change 1 | — | sketch |
| CLW-102 | The reserve shows. | Askable | Change 1 | — | sketch |
| CLW-103 | Nothing else changes. | Askable | Change 1 | — | sketch |
"""
SCRIPT = """# Change script

## Change 1 — Leave some in the cupboard

### Owner request

> leave some twigs for me

**Introduces:** CLW-101, CLW-102, CLW-103.
"""
PROBES = """# Probes

## Probes

### CLW-101

#### P-CLW101-a
- **Applies:** from change 1
- **Setup:** S0
- **Needs:** none
- **Scenario:** Craft leaving 5.
- **Expected observation:** 5 stay.
"""


def fork(runs: Path, cell: str, n: int, items: dict, implementation: dict) -> str:
    variant, rest = cell.split("-", 1)
    arm, window = rest.rsplit("-", 1)
    fid = f"cf-{cell}-c{n:02d}-r1"
    g = runs / fid / "grading" / f"change-{n:02d}"
    (g / "probes" / "b01").mkdir(parents=True)
    (runs / fid / "trajectory.json").write_text(json.dumps({"id": fid, "arm": arm, "window": window, "change": n,
                                                            "fork_of": {"variant": variant}}))
    (g / "summary.json").write_text(json.dumps({"items": items, "implementation": implementation}))
    probes = {f"P-{i.replace('-', '')}-a": i for i in items}
    (g / "probes" / "verdicts.json").write_text(json.dumps({
        "items": {i: {"verdict": v, "probes": {f"P-{i.replace('-', '')}-a": v}} for i, v in items.items()},
        "details": {pid: {"verdict": items[i], "reason": "The output shows it.", "evidence": [2], "batch": "b01"}
                    for pid, i in probes.items()}}))
    (g / "probes" / "b01" / "probes.md").write_text("## Conventions\n\n" + "".join(f"## {pid}\n\n- **Scenario:** do it\n\n" for pid in probes))
    for pid in probes:
        t = ss.probe_target(pid)
        (g / "probes" / "b01" / f"{t}.rs").write_text(f"// {pid}\n#[test] fn t() {{}}\n")
        (g / "probes" / "b01" / f"{t}.log").write_text(f"{pid} observed\nALL-CASES: 1 of 1\n")
    (g / "probes" / "b01" / "judgment.json").write_text(json.dumps({"verdicts": {
        pid: {"probe": pid, "verdict": items[i], "reason": "The output shows it."} for pid, i in probes.items()}}))
    (g / "probes" / "implementation.json").write_text(json.dumps({"statuses": implementation, "record": {"items": [
        {"item": i, "status": s, "evidence": [{"file": "src/a.rs", "symbols": ["f"]}], "note": "x"}
        for i, s in implementation.items()]}}))
    (g / "arm.diff").write_text("diff --git a/src/a.rs b/src/a.rs\n+fn f() {}\n")
    return fid


class SamplerTest(unittest.TestCase):
    def setUp(self):
        self.runs, self.seed = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
        (self.seed / "hidden").mkdir()
        (self.seed / "hidden" / "oracle.md").write_text(ORACLE)
        (self.seed / "hidden" / "change-script.md").write_text(SCRIPT)
        body = PROBES.split("## Probes\n\n", 1)[1]
        (self.seed / "hidden" / "probes.md").write_text(PROBES + "\n" + body.replace("101", "102") + "\n"
                                                        + body.replace("101", "103"))
        for cell in CELLS:
            fork(self.runs, cell, 1, {"CLW-101": "met", "CLW-102": "met", "CLW-103": "met"},
                 {"CLW-101": "implemented", "CLW-102": "implemented", "CLW-103": "absent"})
            fork(self.runs, cell, 2, {"CLW-101": "met", "CLW-102": "not met", "CLW-103": "met"},
                 {"CLW-101": "implemented", "CLW-102": "implemented", "CLW-103": "unclear"})
        fork(self.runs, "stripped-null-200k", 1, {"CLW-101": "met"}, {"CLW-101": "unclear"})

    def test_met_items_less_those_found_absent_from_the_six_cells_only(self):
        c = ss.candidates(self.runs, CELLS)
        self.assertEqual(len(c), 6 * 4)  # per cell: 101 and 102 at change 1; 101 and 103 at change 2
        self.assertFalse(any(x["item"] == "CLW-103" and x["change"] == 1 for x in c))  # found absent
        self.assertFalse(any("null" in x["fork"] for x in c))

    def test_twenty_drawn_three_or_four_per_cell_the_same_for_the_same_seed(self):
        c = ss.candidates(self.runs, CELLS)
        a, b = ss.draw(c, 20, "s1"), ss.draw(c, 20, "s1")
        self.assertEqual(a, b)
        self.assertEqual(len(a), 20)
        per = {cell: sum(x["cell"] == cell for x in a) for cell in CELLS}
        self.assertEqual(sorted(per.values()), [3, 3, 3, 3, 4, 4])
        self.assertNotEqual(ss.draw(c, 20, "s2"), a)

    def test_each_packet_is_blind_and_the_index_lives_outside_the_packets(self):
        out, index = Path(tempfile.mkdtemp()) / "spotcheck-sample", Path(tempfile.mkdtemp()) / "index.json"
        drawn = ss.draw(ss.candidates(self.runs, CELLS), 20, "s1")
        hits = ss.write_packets(drawn, out, index, runs=self.runs, seed_dir=self.seed, diff_for=lambda fid: "")
        self.assertEqual(sorted(p.name for p in out.iterdir()), [f"{k:02d}" for k in range(1, 21)])
        first = out / "01"
        names = sorted(p.name for p in first.iterdir())
        self.assertEqual(names[:4], ["01-item.md", "02-probes-as-executor-saw-them.md", "03-code-diff.diff", "04-executor-test-P-"
                                     + drawn[0]["item"].replace("-", "") + "-a.rs"])
        self.assertIn("README.md", names)
        self.assertIn("07-extraction-record.json", names)
        self.assertIn(drawn[0]["item"], (first / "01-item.md").read_text())
        mapping = json.loads(index.read_text())
        self.assertEqual(mapping["01"], {"fork": drawn[0]["fork"], "item": drawn[0]["item"], "cell": drawn[0]["cell"]})
        self.assertFalse(any("cf-" in p.read_text() for p in first.iterdir()))  # no fork id in a packet
        self.assertEqual(hits, {})

    def test_the_blindness_scan_finds_a_tell(self):
        d = Path(tempfile.mkdtemp())
        (d / "04-executor-test.rs").write_text("// see the LID spec\n// @spec SIM-ENG-009\nfn t() {}\n")
        (d / "03-code-diff.diff").write_text("+ arrow keys move the cursor\n")
        hits = ss.blindness_scan(d)
        self.assertEqual(sorted({h["word"].lower() for h in hits}), ["@spec", "lid", "spec"])
        self.assertFalse(any(h["file"] == "03-code-diff.diff" for h in hits))  # arrow keys are a keyboard's, not a tell


if __name__ == "__main__":
    unittest.main()
