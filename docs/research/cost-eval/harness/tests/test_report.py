"""Tests for report.py: item shares, the split by disclosure kind and band, costs, and skipped changes."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import report  # noqa: E402
from test_grading import PROBES  # noqa: E402
from test_simulator import CHANGES, ORACLE  # noqa: E402


def write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(obj if isinstance(obj, str) else json.dumps(obj))


class ReportTest(unittest.TestCase):
    def setUp(self):
        root = Path(tempfile.mkdtemp())
        self.runs, self.seed = root / "runs", root / "seeds" / "bk"
        write(self.seed / "hidden" / "oracle.md", ORACLE)
        write(self.seed / "hidden" / "change-script.md", CHANGES)
        write(self.seed / "hidden" / "probes.md", PROBES)
        write(self.seed / "hidden" / "bands.json", {"_note": "x", "BK-02": "low", "BK-03": "high"})
        run = self.runs / "s9-bare-1"
        write(run / "trajectory.json", {"id": "s9-bare-1", "arm": "bare", "changes": {
            "0": {"agent_cost_usd": 1.0, "owner_cost_usd": 0.5, "rounds": 2},
            "1": {"agent_cost_usd": 0.5, "owner_cost_usd": 0.1, "rounds": 1},
            "2": {"symptom": "not fired: diagnostic passed", "finished": True}}})
        write(run / "change-00" / "owner-00.json", {"words_shown": 100})
        write(run / "change-00" / "owner-01.json", {"words_shown": 50})
        write(run / "change-01" / "owner-00.json", {"words_shown": 10})
        g = run / "grading" / "change-01"
        # first grading: BK-01 has one probe met and one couldn't exercise, so it isn't met; BK-02 is met
        write(g / "verdicts.json", {"probes": {"P-BK01-a": {"verdict": "met"}, "P-BK01-b": {"verdict": "couldn't exercise"},
                                               "P-BK02-a": {"verdict": "met"}}})
        # a re-judgment reverses both
        write(g / "rejudge-x.json", {"rows": {"P-BK01-a": {"original": "met", "new": "met"},
                                              "P-BK01-b": {"original": "couldn't exercise", "new": "met"},
                                              "P-BK02-a": {"original": "met", "new": "not met"}}})

    def build(self, verdicts):
        return report.build(self.runs, self.seed, "s9", {"bare": ["1"]}, verdicts)

    def test_couldnt_exercise_counts_against_and_items_split_by_kind_and_band(self):
        f = self.build("verdicts")["arms"]["bare"][0]["fidelity"][1]
        self.assertEqual(f["all"], (1, 2))
        self.assertEqual(f["couldn't exercise"], 1)
        self.assertEqual(f["by kind"]["stated"], (0, 1))   # BK-01
        self.assertEqual(f["by kind"]["askable"], (1, 1))  # BK-02
        self.assertEqual(f["by band"]["low"], (1, 1))
        self.assertIsNone(f["by band"]["high"])            # BK-03 not graded here

    def test_a_rejudgment_uses_the_new_verdicts(self):
        f = self.build("rejudge-x")["arms"]["bare"][0]["fidelity"][1]
        self.assertEqual(f["all"], (1, 2))
        self.assertEqual(f["by kind"]["stated"], (1, 1))
        self.assertEqual(f["not met"], 1)

    def test_costs_attention_and_skipped_changes(self):
        r = self.build("verdicts")
        t = r["arms"]["bare"][0]
        self.assertEqual(sum(c["agent_usd"] for c in t["changes"].values()), 1.5)
        self.assertEqual(sum(c["replies"] for c in t["changes"].values()), 3)
        self.assertEqual(sum(c["words_shown"] for c in t["changes"].values()), 160)
        self.assertTrue(t["changes"][2]["skipped"])
        md = report.render(r)
        self.assertIn("| skipped |", md)
        self.assertIn("$1.50", md)


if __name__ == "__main__":
    unittest.main()
