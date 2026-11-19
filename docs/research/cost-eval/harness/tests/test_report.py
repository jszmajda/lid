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

    def test_a_missing_item_is_left_out_of_items_met_and_counted_by_cause(self):
        g = self.runs / "s9-bare-1" / "grading" / "change-01"
        # a Rust grading writes each probe's verdict as text, and the unresolved grader errors apart
        write(g / "verdicts-m.json", {"probes": {"P-BK01-a": "met", "P-BK01-b": "missing", "P-BK02-a": "met"},
                                      "missing": {"P-BK01-b": {"fault": "interface", "cause": "execution"}}})
        r = self.build("verdicts-m")
        f = r["arms"]["bare"][0]["fidelity"][1]
        self.assertEqual(f["all"], (1, 1))  # BK-01 is missing: neither met nor counted against
        self.assertEqual((f["missing"], f["missing by cause"]), (1, {"interface": 1}))
        text = report.render(r)
        self.assertIn("## Missing items", text)
        self.assertIn("| bare | 1 | interface 1 | 0 |", text)

    def test_a_conflict_is_left_out_of_items_met_and_counted(self):
        g = self.runs / "s9-bare-1" / "grading" / "change-01"
        write(g / "verdicts-c.json", {"probes": {"P-BK01-a": "met", "P-BK01-b": "missing (conflict)", "P-BK02-a": "met"},
                                      "conflicts": {"BK-01 x": {"probes": {"P-BK01-b": {"verdict": "met"}}}}})
        r = self.build("verdicts-c")
        f = r["arms"]["bare"][0]["fidelity"][1]
        self.assertEqual((f["all"], f["conflicts"]), ((1, 1), 1))
        self.assertIn("| bare | 0 | – | 1 |", report.render(r))

    def test_interface_faults_are_reported_next_to_the_share_whether_absent_or_missing(self):
        g = self.runs / "s9-bare-1" / "grading" / "change-01"
        write(g / "verdicts-i.json", {"probes": {"P-BK01-a": "not met", "P-BK01-b": "met", "P-BK02-a": "missing"},
                                      "missing": {"P-BK02-a": {"fault": "interface", "cause": "execution"}},
                                      "absent": {"P-BK01-a": {"fault": "interface"}},
                                      "interface_faults": {"not met (absent)": ["BK-01 x"], "missing": ["BK-02 y"]}})
        r = self.build("verdicts-i")
        f = r["arms"]["bare"][0]["fidelity"][1]
        self.assertEqual((f["all"], f["interface faults"]), ((0, 1), {"not met (absent)": 1, "missing": 1}))
        self.assertIn("0% [0%] · interface: 1 absent, 1 missing", report.render(r))

    def test_a_rejudgment_uses_the_new_verdicts(self):
        f = self.build("rejudge-x")["arms"]["bare"][0]["fidelity"][1]
        self.assertEqual(f["all"], (1, 2))
        self.assertEqual(f["by kind"]["stated"], (1, 1))
        self.assertEqual(f["not met"], 1)

    def test_an_excluded_item_leaves_one_checkpoint_only(self):
        f = report.build(self.runs, self.seed, "s9", {"bare": ["1"]}, "verdicts", ("bare-1:1:BK-01",))["arms"]["bare"][0]["fidelity"][1]
        self.assertEqual(f["all"], (1, 1))

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


class ForkReportTest(unittest.TestCase):
    """report.py --forks: the Rust seed's forks by cell (variant, arm, window), one row per change."""

    def fork(self, runs, variant, arm, window, n, **summary):
        fid = f"cf-{variant}-{arm}-{window}-c{n:02d}-r1"
        write(runs / fid / "trajectory.json", {"id": fid, "arm": arm, "window": window, "change": n,
                                               "fork_of": {"variant": variant}, "changes": {str(n): {"commit": "c"}}})
        write(runs / fid / "grading" / f"change-{n:02d}" / "summary.json", summary)

    def test_each_cell_shows_items_retention_and_tests_not_built_by_cause(self):
        runs = Path(tempfile.mkdtemp())
        self.fork(runs, "full", "bare", "200k", 1,
                  items_met={"met": 2, "of": 3, "missing": 1, "conflicts": 0}, missing_by_fault={"fixture": 1},
                  held_out_retention={"passed": 232, "failed": 0, "tests_not_built": 91,
                                      "tests_not_built_by_cause": {"E0063 no empty value": 91}},
                  seed_files={"probes_sha256": "abcdef0123"})
        self.fork(runs, "full", "bare", "200k", 2, items_met={"met": 4, "of": 4, "missing": 0, "conflicts": 1},
                  conflicts={"CLW-201": {}}, held_out_retention={"passed": 323, "failed": 0, "tests_not_built": 0,
                                                                  "tests_not_built_by_cause": {}})
        self.fork(runs, "stripped", "null", "200k", 1, items_met={"met": 0, "of": 3, "missing": 0, "conflicts": 0},
                  held_out_retention={"passed": 323, "failed": 0})
        r = report.fork_report(runs, "cf-*-r1")
        cell = r["cells"]["full-bare-200k"]
        self.assertEqual(cell["total"], {"met": 6, "of": 7, "missing": 1, "conflicts": 1,
                                         "tests_not_built_by_cause": {"E0063 no empty value": 91},
                                         "missing_by_fault": {"fixture": 1}})
        text = report.render_forks(r)
        self.assertIn("## full-bare-200k", text)
        self.assertIn("| 1 | 2/3 | 1 | 0 | 232/232 | E0063 no empty value 91 | abcdef0 |", text)
        self.assertIn("## stripped-null-200k", text)

    def test_an_older_summary_takes_its_tests_not_built_from_keeping(self):
        runs = Path(tempfile.mkdtemp())
        self.fork(runs, "full", "lid-full", "1m", 7, items_met={"met": 4, "of": 4},
                  held_out_retention={"passed": 244, "failed": 0, "tests_not_built": 79})
        write(runs / "cf-full-lid-full-1m-c07-r1" / "grading" / "change-07" / "keeping.json", {"targets": {
            "heldout_chrome": {"compile_failed": True, "tests_expected": 79,
                               "adaptation": {"status": "not adapted", "reason": "E0382 at c.rs:5260 is not one the rule adapts"}},
            "heldout_frame": {"compile_failed": False, "tests_expected": 44}}})
        r = report.fork_report(runs, "cf-*-r1")
        self.assertEqual(r["cells"]["full-lid-full-1m"]["total"]["tests_not_built_by_cause"], {"E0382": 79})


class SpotCheckTest(unittest.TestCase):
    """--spot-checks: a ruling from a blind spot-check resolves a conflict, or overrides a verdict, and the row says so."""

    def test_a_spot_check_resolves_a_conflict_and_the_row_names_its_source(self):
        runs = Path(tempfile.mkdtemp())
        ForkReportTest.fork(None, runs, "full", "lid-full", "1m", 11,
                            items={"CLW-1101": "met", "CLW-1104": "missing (conflict)"},
                            items_met={"met": 1, "of": 1, "missing": 0, "conflicts": 1}, conflicts={"CLW-1104": {}},
                            held_out_retention={"passed": 321, "failed": 2})
        checks = Path(tempfile.mkdtemp()) / "spot-checks.json"
        checks.write_text(json.dumps([{"fork": "cf-full-lid-full-1m-c11-r1", "item": "CLW-1104", "ruling": "not met",
                                       "by": "Claude Fable", "note": "read a tally in place of the report"}]))
        r = report.fork_report(runs, "cf-*-r1", spot_checks=report.load_spot_checks(checks))
        row = r["cells"]["full-lid-full-1m"]["changes"][0]
        self.assertEqual((row["met"], row["of"], row["conflicts"]), (1, 2, 0))
        self.assertEqual(row["spot_checks"], [{"item": "CLW-1104", "was": "missing (conflict)", "now": "not met",
                                               "by": "Claude Fable", "note": "read a tally in place of the report"}])
        text = report.render_forks(r)
        self.assertIn("CLW-1104: missing (conflict) → not met (Claude Fable)", text)
        self.assertEqual(r["cells"]["full-lid-full-1m"]["total"]["conflicts"], 0)

    def test_a_spot_check_names_a_fork_and_item_that_exist(self):
        checks = Path(tempfile.mkdtemp()) / "s.json"
        checks.write_text(json.dumps([{"fork": "cf-x", "item": "CLW-1", "ruling": "sort of"}]))
        with self.assertRaisesRegex(ValueError, "ruling"):
            report.load_spot_checks(checks)

    def test_the_seed_holds_the_change_11_ruling(self):
        seeded = report.load_spot_checks(HERE_SEED / "spot-checks.json")
        self.assertEqual([(c["fork"], c["item"], c["ruling"], c["by"]) for c in seeded],
                         [("cf-full-lid-full-1m-c11-r1", "CLW-1104", "not met", "Claude Fable")])


HERE_SEED = Path(__file__).resolve().parent.parent.parent / "seeds" / "clowder" / "hidden"
