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
        self.assertIn(("cf-full-lid-full-1m-c11-r1", "CLW-1104", "not met", "Claude Fable"),
                      [(c["fork"], c["item"], c["ruling"], c["by"]) for c in seeded])


HERE_SEED = Path(__file__).resolve().parent.parent.parent / "seeds" / "clowder" / "hidden"


class GrowthReportTest(unittest.TestCase):
    """report.py --growth: per arm and checkpoint, items met (stated, latent, and latent disclosed in every arm of the
    replicate), keeping, reliance regressions, flip checks, the stale-intent audit, cost, owner time, and fidelity per
    owner-hour and per dollar."""

    def traj(self, runs, tid, arm, verdicts_by_c, shared_by_change, words=2380, agent=1.0):
        changes = {str(n): {"agent_cost_usd": agent, "owner_cost_usd": 0.5, "rounds": 1} for n in range(3)}
        write(runs / tid / "trajectory.json", {"id": tid, "arm": arm, "replicate": "g-r1", "changes": changes})
        for n in range(3):
            write(runs / tid / f"change-{n:02d}" / "owner-00.json",
                  {"words_shown": words, "shared": [{"item": i, "reason": "asked"} for i in shared_by_change.get(n, [])]})
        for c, pv in verdicts_by_c.items():
            write(runs / tid / "grading" / f"change-{c:02d}" / "verdicts.json", {"probes": {p: {"verdict": v} for p, v in pv.items()}})

    def test_a_symptom_row_is_graded_in_force_from_its_change_and_its_report_firing_is_reported_apart(self):
        root = Path(tempfile.mkdtemp())
        runs, seed = root / "runs", root / "seeds" / "bk"
        write(seed / "hidden" / "oracle.md", ORACLE)
        write(seed / "hidden" / "change-script.md", CHANGES)
        write(seed / "hidden" / "probes.md", PROBES + "\n### BK-07\n\n#### P-BK07-a\n- **Applies:** from change 5\n"
              "- **Setup:** S0\n- **Needs:** none\n- **Scenario:**\n  1. Refund an order.\n"
              "- **Expected observation:** The refund goes to the original card.\n")
        for tid, arm, symptom, verdict in (("g-bare-1", "bare", "not fired: diagnostic passed", "met"),
                                           ("g-lid-full-1", "lid-full", "fired", "not met")):
            changes = {str(n): {"agent_cost_usd": 1.0, "owner_cost_usd": 0.5, "rounds": 1} for n in range(5)}
            changes["5"] = {"symptom": symptom, "finished": True}
            write(runs / tid / "trajectory.json", {"id": tid, "arm": arm, "replicate": "g-r1", "changes": changes})
            write(runs / tid / "grading" / "change-05" / "verdicts.json",
                  {"probes": {"P-BK01-a": {"verdict": "met"}, "P-BK07-a": {"verdict": verdict}}})
        r = report.growth_report(runs, seed, "g", {"bare": ["1"], "lid-full": ["1"]}, [5])
        bare, lid = r["arms"]["bare"][0]["checkpoints"][0], r["arms"]["lid-full"][0]["checkpoints"][0]
        # graded in force from change 5 either way, as the oracle's lifetime says
        self.assertEqual((bare["latent"], lid["latent"]), ((1, 1), (0, 1)))
        # whether the report fired, apart
        self.assertEqual((bare["symptom_reports"], lid["symptom_reports"]), ((0, 1), (1, 1)))
        self.assertEqual((bare["graded_unreported"], lid["graded_unreported"]), (["BK-07"], []))
        text = report.render_growth(r)
        self.assertIn("## Symptom reports", text)
        self.assertIn("| bare | 5 | 0/1 | BK-07 |", text)
        self.assertIn("graded in force from its change", text)

    def test_repair_forks_per_arm_and_the_break_even_against_each_arms_premium_over_bare(self):
        root = Path(tempfile.mkdtemp())
        runs, seed = root / "runs", root / "seeds" / "bk"
        write(seed / "hidden" / "oracle.md", ORACLE)
        write(seed / "hidden" / "change-script.md", CHANGES)
        write(seed / "hidden" / "probes.md", PROBES + "\n### BK-03\n\n#### P-BK03-a\n- **Applies:** from change 0\n"
              "- **Setup:** S0\n- **Needs:** none\n- **Scenario:**\n  1. Look for last year's order.\n"
              "- **Expected observation:** It is still there.\n")
        self.traj(runs, "g-bare-1", "bare", {2: {"P-BK01-a": "met", "P-BK02-a": "not met", "P-BK03-a": "not met"}}, {})
        self.traj(runs, "g-lid-full-1", "lid-full", {2: {"P-BK01-a": "met", "P-BK02-a": "met", "P-BK03-a": "not met"}}, {},
                  agent=3.0)
        self.traj(runs, "g-checklist-1", "checklist", {2: {"P-BK01-a": "met", "P-BK02-a": "met", "P-BK03-a": "met"}}, {})

        def repair(tid, item, fixed, cost, broken=()):
            write(runs / tid / "repair-forks" / f"c02-{item}" / "repair.json", {
                "trajectory": tid, "run": f"{tid}/repair-forks/c02-{item}", "at": 2, "item": item, "kind": "askable",
                "fixed": fixed, "regrade": "full", "agent_cost_usd": cost, "owner_cost_usd": 0.1,
                "keeping": {"met_before": 1, "held": 1 - len(broken), "broken": list(broken), "undetermined": []},
                "measures": {"agent_cost_usd": cost, "turns": 2, "model_calls": 9, "minutes": 3.0, "files_read": ["a.py"]}})
        repair("g-bare-1", "BK-02", True, 0.5)
        repair("g-bare-1", "BK-03", False, 1.5, broken=["BK-01"])
        repair("g-lid-full-1", "BK-03", True, 0.8)
        # a repair set aside by a redo (graded on probes since revised) is no longer one of the run's repairs
        write(runs / "g-lid-full-1" / "repair-forks" / "c02-BK-03.v3" / "repair.json",
              {"item": "BK-03", "fixed": False, "agent_cost_usd": 9.0, "keeping": {"broken": ["BK-01"]}})
        r = report.growth_report(runs, seed, "g", {"bare": ["1"], "lid-full": ["1"], "checklist": ["1"]}, [2],
                                 notes=["The instrument gate validated probes version 3."])
        bare = r["repairs"]["bare"][0]
        self.assertEqual((bare["missed"], bare["graded"], bare["fixed"]), (["BK-02", "BK-03"], 2, 1))
        self.assertEqual((bare["fix_cost_mean"], bare["fix_cost_median"], bare["breaks"], bare["forks_breaking"]),
                         (0.5, 0.5, 1, 1))
        lid = next(x for x in r["break_even"] if x["arm"] == "lid-full")
        self.assertEqual((lid["repair_cost"], lid["cost_to_checkpoint"], lid["premium"], lid["bare_repair_less"]),
                         (0.8, 9.0, 6.0, 1.2))
        text = report.render_growth(r)
        self.assertIn("## Repair forks", text)
        self.assertIn("| bare | 2 | 2 | 2 | 1 | 50% | $0.50 | $0.50 | 1 item in 1 of 2 forks |", text)
        self.assertIn("| lid-full | 2 | 1 | 1 | 1 | 100% | $0.80 | $0.80 | none |", text)
        self.assertIn("| checklist | 2 | 0 | 0 | 0 | – | – | – | none |", text)
        self.assertIn("| bare | 2 | 2 | 1 | $2.00 | $3.00 | – | – |", text)
        self.assertIn("| lid-full | 2 | 1 | 1 | $0.80 | $9.00 | $6.00 | $1.20 |", text)
        self.assertIn("| checklist | 2 | 0 | 0 | $0.00 | $3.00 | $0.00 | $2.00 |", text)
        self.assertIn("full regrade", text)
        self.assertIn("- The instrument gate validated probes version 3.", text.split("## Change", 1)[0])  # a definitions note
        # the checklist arm is in every table bare and LID are in
        change_table = text.split("## Change 2", 1)[1].split("\n## ", 1)[0]
        for arm in ("bare", "lid-full", "checklist"):
            self.assertIn(f"| {arm} |", change_table)

    def test_the_break_even_waits_until_both_sides_have_repaired_every_miss(self):
        row = lambda tid, missed, graded, cost: {"id": tid, "checkpoint": 10, "missed": missed, "graded": graded,  # noqa: E731
                                                 "fixed": graded, "repair_cost": cost}
        costs = {("g-bare-1", 10): 3.0, ("g-lid-full-1", 10): 9.0}
        replicate = {"g-bare-1": "1", "g-lid-full-1": "1"}
        rows = report.break_even({"bare": [row("g-bare-1", ["A", "B"], 1, 0.5)], "lid-full": [row("g-lid-full-1", ["A"], 1, 0.4)]},
                                 costs, replicate)
        lid = next(x for x in rows if x["arm"] == "lid-full")
        self.assertEqual((lid["premium"], lid["bare_repair_less"]), (6.0, None))  # bare's second miss not yet repaired

    def test_working_around_rot_per_arm_with_r_plus_as_a_clean_build_on_its_own_codebase(self):
        import test_rot_cost as rc
        root = Path(tempfile.mkdtemp())
        runs, seed = root / "runs", root / "seeds" / "bk"
        write(seed / "hidden" / "oracle.md", ORACLE)
        write(seed / "hidden" / "change-script.md", CHANGES)
        write(seed / "hidden" / "probes.md", PROBES)
        self.traj(runs, "g-bare-1", "bare", {2: {"P-BK01-a": "met"}}, {})
        g = runs / "g-bare-1" / "growth" / "checkpoint-02"
        write(g / "stale-audit.json", {"checkpoint": 2, "courses": {"2": rc.audit_of(README_md="stale", docs__a_md="mixed")}})
        rc.reliance_fork(runs, "g-bare-1", 2, 1, at=4, cost=0.6, streams=[rc.stream(*rc.read("t1", "/work/README.md"))])
        rc.reliance_fork(runs, "g-bare-1", 2, 2, at=4, cost=0.2, streams=[rc.stream(*rc.read("t1", "/work/docs/a.md"))])
        rc.course_fork(runs, "g-bare-1", 2, 1, cost=2.0, streams=[rc.stream(*rc.read("t1", "/work/README.md"))],
                       audit=rc.audit_of(README_md="stale"))
        write(g / "reliance.json", [{"course": 2, "run": "g-bare-1/course-forks/c02-reliance-1", "outcome": "displaced"},
                                    {"course": 2, "run": "g-bare-1/course-forks/c02-reliance-2", "outcome": "current"}])
        write(g / "course-forks.json", [{"course": 2, "run": "g-bare-1/course-forks/c02-course-1", "behaves": False,
                                         "stale": 1}])
        rc.reliance_fork(runs, "g-ref-correct", 2, 1, at=4, cost=0.1, streams=[rc.stream(*rc.read("t1", "/work/a.md"))])
        r = report.growth_report(runs, seed, "g", {"bare": ["1"]}, [2])
        rot = r["rot"]["bare"]
        stale, either = rot["reliance"]["stale"], rot["reliance"]["stale or mixed"]  # both cuts, neither picked
        self.assertEqual(stale["read flagged"]["n"], 1)
        self.assertEqual(stale["read flagged"]["outcomes"], {"current": 0, "displaced": 1, "neither": 0, "other": 0})
        self.assertAlmostEqual(stale["read flagged"]["r_plus_ratio_median"], 6.0)
        self.assertEqual(stale["read none"]["outcomes"]["current"], 1)
        self.assertEqual((either["read flagged"]["n"], "read none" in either), (2, False))  # the second read a mixed file
        self.assertEqual(rot["course"]["stale"]["read flagged"]["outcomes"], {"behaved": 0, "didn't": 1, "undetermined": 0})
        self.assertEqual(r["rot_reference"]["2"]["agent_cost_usd"], 0.1)
        text = report.render_growth(r)
        self.assertIn("## Working around rot", text)
        self.assertIn("a different codebase", text)
        self.assertIn("several changes after the fork's snapshot", text)  # the audit is of the files at the checkpoint
        self.assertIn("| Turns, mean | Turns, median | Model calls, mean | Model calls, median |", text)
        self.assertIn("| read a stale file | 1 | $0.60 | $0.60 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 6.0× | 0 | 1 | 0 | 0 |", text)
        self.assertIn("| read no stale file | 1 | $0.20 | $0.20 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 2.0× | 1 | 0 | 0 | 0 |", text)
        self.assertIn("| read a stale or mixed file | 2 | $0.40 | $0.40 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 4.0× | 1 | 1 | 0 | 0 |",
                      text)
        self.assertIn("| read a stale file | 1 | $2.00 | $2.00 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0 | 1 | 0 |", text)  # course forks
        self.assertIn("| g-bare-1/c02-reliance-1 | 2 | checkpoint 2 (2 away) | 1 | 1 | 0 | $0.60 | 6.0× | 1 | 1 | 2.5 | 3 | "
                      "1,000 | displaced |", text)
        self.assertIn("| g-bare-1/c02-reliance-2 | 2 | checkpoint 2 (2 away) | 1 | 0 | 1 | $0.20 | 2.0× | 1 | 1 | 2.5 | 3 | "
                      "1,000 | current |", text)
        self.assertIn("| 2 | $0.10 | 1 | 1 |", text)  # R+'s own reliance fork per course change

    def test_intent_from_tests_and_docs_per_arm_and_checkpoint(self):
        root = Path(tempfile.mkdtemp())
        runs, seed = root / "runs", root / "seeds" / "bk"
        write(seed / "hidden" / "oracle.md", ORACLE)
        write(seed / "hidden" / "change-script.md", CHANGES)
        write(seed / "hidden" / "probes.md", PROBES)
        self.traj(runs, "g-lid-full-1", "lid-full", {2: {"P-BK01-a": "met"}}, {})
        cell = lambda r, m, lat, mb, st, ret: {"mean": {"recall": r, "recall_of_met": m, "by_group_of_met.latent.recall": lat,  # noqa: E731
                                                        "rates_per_rule.stale": st, "stale_items_share": ret},
                                               "minus_baseline": {"recall_of_met": mb}}
        write(runs / "intent-from-tests" / "growth-g-lid-full-1-c02" / "summary.json", {"cells": {
            "brief|brief": {"mean": {"recall": 0.49}},
            "lid-full|tests": cell(0.82, 0.83, 0.93, 0.35, 0.04, 0.29),
            "lid-full|tests-neutral": cell(0.79, 0.80, 0.93, 0.33, 0.04, 0.29),
            "lid-full|docs": cell(0.82, 0.83, 1.0, 0.36, 0.02, 0.29)}})
        r = report.growth_report(runs, seed, "g", {"lid-full": ["1"]}, [2])
        row = r["arms"]["lid-full"][0]["checkpoints"][0]
        self.assertEqual(row["intent_reads"]["tests"]["recall_of_met"], 0.83)
        self.assertEqual(row["intent_reads"]["docs"]["minus_baseline"], 0.36)
        text = report.render_growth(r)
        self.assertIn("## Intent from tests and docs", text)
        self.assertIn("| 2 | lid-full | tests, names replaced | 80% | 93% | 33% | 0.04 | 29% |", text)

    def test_growth_figures_per_arm_and_checkpoint(self):
        root = Path(tempfile.mkdtemp())
        runs, seed = root / "runs", root / "seeds" / "bk"
        write(seed / "hidden" / "oracle.md", ORACLE)
        write(seed / "hidden" / "change-script.md", CHANGES)
        write(seed / "hidden" / "probes.md", PROBES)
        self.traj(runs, "g-bare-1", "bare", {1: {"P-BK01-a": "met", "P-BK02-a": "not met"}, 2: {"P-BK01-a": "met", "P-BK02-a": "met"}},
                  {2: ["BK-02"]})
        self.traj(runs, "g-lid-full-1", "lid-full", {1: {"P-BK01-a": "met", "P-BK02-a": "met"}, 2: {"P-BK01-a": "not met", "P-BK02-a": "met"}},
                  {1: ["BK-02"]})
        g = runs / "g-bare-1" / "growth" / "checkpoint-02"
        write(g / "flips.json", [{"behaves": True}, {"behaves": False}, {"behaves": None, "anticipated": True}])
        write(g / "course-forks.json", [{"behaves": True, "stale": 0}, {"behaves": False, "stale": 2}, {"behaves": None, "stale": None}])
        write(g / "reliance.json", [{"course": 2, "run": "g-bare-1/course-forks/c02-reliance-1", "outcome": "current"},
                                    {"course": 2, "run": "g-bare-1/course-forks/c02-reliance-2", "outcome": "displaced"},
                                    {"course": 2, "run": "g-bare-1/course-forks/c02-reliance-3", "outcome": "undetermined"},
                                    {"course": 2, "run": "g-bare-1/course-forks/c02-reliance-4", "outcome": "both"},
                                    {"course": 2, "run": "g-bare-1/course-forks/c02-reliance-5", "outcome": "no probe"}])
        write(g / "stale-audit.json", {"courses": {"2": {"stale": 1, "current": 2, "mixed": 0, "unrelated": 0, "no_ruling": 0}}})
        r = report.growth_report(runs, seed, "g", {"bare": ["1"], "lid-full": ["1"]}, [1, 2])
        bare = {row["checkpoint"]: row for row in r["arms"]["bare"][0]["checkpoints"]}
        lid = {row["checkpoint"]: row for row in r["arms"]["lid-full"][0]["checkpoints"]}
        self.assertEqual((bare[1]["stated"], bare[1]["latent"]), ((1, 1), (0, 1)))
        self.assertEqual(bare[1]["latent_disclosed_everywhere"], None)  # bare hadn't asked about BK-02 by change 1
        self.assertEqual(bare[2]["latent_disclosed_everywhere"], (1, 1))
        self.assertEqual(lid[2]["keeping"], (1, 2))  # BK-01, met at change 1, no longer is
        self.assertEqual((bare[2]["reliance"], bare[2]["flips_behaving"], bare[2]["stale_files"]),
                         ({"current": 1, "displaced": 1, "neither": 0, "both": 1, "undetermined": 1, "no probe": 1},
                          (1, 2), (1, 3)))
        self.assertEqual(bare[2]["displaced_rate"], (1, 2))  # the rot consequence: displaced, of current/displaced/neither
        self.assertEqual(r["reliance_by_course"]["2"]["bare"], {"current": 1, "displaced": 1, "neither": 0, "both": 1,
                                                               "undetermined": 1, "no probe": 1})
        self.assertEqual(r["reliance_spot_checks"], ["g-bare-1/course-forks/c02-reliance-4"])  # "both" is inconsistent
        self.assertEqual(bare[2]["anticipated"], (1, 1))  # an emerging change's check, never a flip
        self.assertEqual((bare[2]["course_forks_behaving"], bare[2]["course_fork_stale_files"]), ((1, 2), 2))
        self.assertAlmostEqual(bare[2]["cost_per_change"], 1.5)
        self.assertAlmostEqual(bare[2]["owner_hours"], 3 * 2380 / 238 / 60)
        self.assertAlmostEqual(bare[2]["met_per_owner_hour"], 2 / bare[2]["owner_hours"])
        self.assertAlmostEqual(bare[2]["met_per_dollar"], 2 / 4.5)
        text = report.render_growth(r)
        self.assertIn("## Change 2", text)
        self.assertIn("## Reliance forks by course change", text)
        self.assertIn("| 2 | bare | 1 | 1 | 0 | 1 | 1 | 1 | 1/2 |", text)
        self.assertIn("## Reliance forks to spot-check", text)
        self.assertIn("- g-bare-1/course-forks/c02-reliance-4", text)
        for definition in ("Latent: every kind of item that isn't stated", "Keeping: items met at the previous checkpoint",
                           "count items met", "Displaced-rule rate"):
            self.assertIn(definition, text)
        self.assertIn("| bare |", text)
