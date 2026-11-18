"""Tests for costeval.grading's parts that need no Docker: probes, specs, batches, judgments, and item verdicts.

The fixture is made up, so no hidden probe appears in this public file.
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from costeval import grading  # noqa: E402

PROBES = """# Probes: Bakery

Version 1. A probe applies at every graded checkpoint in its range.

## Setups

### S0: Example shop

Start with empty data and load the shop.

**Starting clock:** 2026-01-05T08:00:00Z, frozen.

Each probe is independent. "Restore" means restore the named setup.

### S1: No delivery

Identical to S0, except deliveries are off.

## Probes

### BK-01

#### P-BK01-a
- **Applies:** from change 0
- **Setup:** S0
- **Needs:** none
- **Scenario:**
  1. Place an order.
  2. Inspect it.
- **Expected observation:** The order records its customer.

#### P-BK01-b
- **Applies:** from change 0, until change 1
- **Setup:** S1
- **Needs:** restart
- **Scenario:**
  1. Place an order and restart.
- **Expected observation:** The order is still there.

### BK-02

#### P-BK02-a
- **Applies:** from change 2
- **Setup:** S0
- **Needs:** prior-data, restart
- **Scenario:**
  1. Carry storage forward.
- **Expected observation:** Old orders open.
"""


class ProbeTest(unittest.TestCase):
    def setUp(self):
        self.ps = grading.parse_probes(PROBES)

    def test_setups_and_probes_parse(self):
        self.assertEqual(list(self.ps.setups), ["S0", "S1"])
        self.assertIn("Each probe is independent", self.ps.setup_notes)
        self.assertNotIn("Each probe is independent", self.ps.setups["S0"])
        a, b, c = self.ps.probes
        self.assertEqual((a.id, a.item, a.setup, a.needs), ("P-BK01-a", "BK-01", "S0", ()))
        self.assertEqual((b.applies_from, b.applies_until, b.needs), (0, 1, ("restart",)))
        self.assertTrue(c.deferred)
        self.assertIn("2. Inspect it.", a.scenario)

    def test_applicability(self):
        ids = lambda n: [p.id for p in self.ps.probes if p.applies(n)]
        self.assertEqual(ids(0), ["P-BK01-a", "P-BK01-b"])
        self.assertEqual(ids(2), ["P-BK01-a", "P-BK02-a"])

    def test_executors_never_see_expected_observations(self):
        text = grading.render_for_execution(self.ps.probes)
        self.assertNotIn("Expected", text)
        self.assertNotIn("records its customer", text)
        self.assertIn("records its customer", grading.render_for_judgment(self.ps.probes))

    def test_batches(self):
        self.assertEqual([len(b) for b in grading.batches(self.ps.probes * 3, 4)], [4, 4, 1])

    def test_unknown_setup_is_refused(self):
        with self.assertRaisesRegex(ValueError, "unknown setup"):
            grading.parse_probes(PROBES.replace("- **Setup:** S1", "- **Setup:** S9"))


class ItemVerdictTest(unittest.TestCase):
    def test_an_item_is_met_only_when_every_probe_is(self):
        ps = grading.parse_probes(PROBES).probes[:2]
        v = lambda a, b: grading.item_verdicts({"P-BK01-a": a, "P-BK01-b": b}, ps)["BK-01"]["verdict"]
        self.assertEqual(v("met", "met"), "met")
        self.assertEqual(v("met", "not met"), "not met")
        self.assertEqual(v("couldn't exercise", "not met"), "not met")
        self.assertEqual(v("met", "couldn't exercise"), "couldn't exercise")
        self.assertEqual(v("met", None), None)
        self.assertEqual(grading.item_verdicts({"P-BK01-a": "met"}, ps)["BK-01"]["share_met"], 0.5)

    def test_a_grader_error_left_unresolved_makes_the_item_missing_unless_a_probe_decides_it(self):
        ps = grading.parse_probes(PROBES).probes[:2]
        v = lambda a, b: grading.item_verdicts({"P-BK01-a": a, "P-BK01-b": b}, ps)["BK-01"]["verdict"]
        self.assertEqual(v("met", "missing"), "missing")
        self.assertEqual(v("missing", "missing"), "missing")
        self.assertEqual(v("not met", "missing"), "not met")  # a confirmed absence decides it
        self.assertEqual(v("couldn't exercise", "missing"), "couldn't exercise")
        self.assertEqual(v("missing", None), "missing")
        self.assertEqual(grading.MISSING, "missing")


class SpecTest(unittest.TestCase):
    SPEC = {"workdir": "/work/app", "command": "uv run app --data {DATA}", "env": {"APP_DIR": "{DATA}/x"},
            "port": 8000, "data_path": "{DATA}", "ready_path": "/docs", "setup_commands": []}

    def test_a_good_spec_passes_and_each_worker_gets_its_own_data(self):
        self.assertEqual(grading.check_spec(self.SPEC), [])
        w = grading.worker_spec(self.SPEC, 2)
        self.assertEqual((w["command"], w["env"]["APP_DIR"], w["data_path"]), ("uv run app --data /cfg/data", "/cfg/data/x", "/cfg/data"))
        w = grading.worker_spec({**self.SPEC, "setup_commands": ["cat {DATA}/token"]}, 1)
        self.assertEqual(w["setup_commands"], ["cat /cfg/data/token"])

    def test_bad_specs_are_caught(self):
        self.assertTrue(grading.check_spec({**self.SPEC, "data_path": "/tmp/db", "command": "x", "env": {}}))
        self.assertTrue(grading.check_spec({**self.SPEC, "workdir": "/elsewhere"}))
        self.assertTrue(grading.check_spec({k: v for k, v in self.SPEC.items() if k != "port"}))
        self.assertTrue(grading.check_spec({**self.SPEC, "command": "/tmp/venv/bin/python -m app --data {DATA}"}))


class SetupTest(unittest.TestCase):
    def test_graders_get_the_instances_settings_but_not_its_data_location(self):
        ref = grading.grader_reference("# Ref", {"env": {"TOKEN": "t1", "DIR": "{DATA}"}})
        self.assertIn("`TOKEN` = `t1`", ref)
        self.assertNotIn("DIR", ref)
        self.assertEqual(grading.grader_reference("# Ref", {"env": {}}), "# Ref")

    def test_a_broken_setup_is_named_so_only_its_probes_skip(self):
        problems = ["no snapshot for S1", "CANNOT S2: no researchers yet", "CANNOT S0 qualifications missing"]
        self.assertEqual(grading.broken_setups(problems, ["S0", "S1", "S2", "S3"]), {"S0", "S1", "S2"})
        self.assertEqual(grading.broken_setups(["no identifier list"], ["S0"]), set())

    def test_needs_written_as_sentences_still_defer(self):
        text = PROBES.replace("- **Needs:** prior-data, restart", "- **Needs:** prior-data: records made at change 0, restart")
        self.assertTrue(grading.parse_probes(text).probes[2].deferred)

    def test_conventions_reach_the_executor_and_the_judge(self):
        ps = grading.parse_probes(PROBES)
        self.assertIn("Each probe is independent", grading.render_for_execution(ps.probes[:1], ps.setup_notes))
        self.assertIn("Each probe is independent", grading.render_for_judgment(ps.probes[:1], ps.setup_notes))
        self.assertNotIn("Conventions", grading.render_for_execution(ps.probes[:1]))

    def test_the_executor_reads_the_full_description_of_each_setup_its_probes_use(self):
        ps = grading.parse_probes(PROBES)
        uses_s1 = [p for p in ps.probes if p.setup == "S1"]
        text = grading.render_for_execution(uses_s1, ps.setup_notes, ps.setups)
        self.assertIn("deliveries are off", text)  # S1's own description
        self.assertIn("### S0: Example shop", text)  # S1 names S0, so S0 comes too
        self.assertLess(text.index("### S0"), text.index("### S1"))
        self.assertLess(text.index("### S1"), text.index("## P-"))
        only_s0 = [p for p in ps.probes if p.setup == "S0"][:1]
        self.assertNotIn("deliveries are off", grading.render_for_execution(only_s0, ps.setup_notes, ps.setups))

    def test_the_service_executor_gets_the_setups_too(self):
        from types import SimpleNamespace
        from unittest import mock
        ps = grading.parse_probes(PROBES)
        put = {}
        ck = SimpleNamespace(tools_volume="tools", network="net", put=lambda vol, path, text: put.__setitem__(path, text),
                             admin=lambda worker, payload: {}, log_lines=lambda worker, bid: [])
        g = SimpleNamespace(execute_model="m", role=lambda *a, **k: "role")
        with mock.patch.object(grading.executor, "run_role",
                               return_value=SimpleNamespace(text="", usage=SimpleNamespace(reported_cost_usd=0, models={}),
                                                            duration_s=0.1)):
            grading.execute_batch(ck, g, 0, "b01", [p for p in ps.probes if p.setup == "S1"], Path(tempfile.mkdtemp()),
                                  ps.setup_notes, setups=ps.setups)
        self.assertIn("deliveries are off", put["/work/probes-b01.md"])

    def test_setup_problems_are_missing_snapshots_and_cannot_marks(self):
        lines = [{"op": "mark", "request": {"text": "CANNOT S0: no token"}}, {"op": "http", "request": {}}]
        self.assertEqual(grading.setup_problems(lines, ["S0", "S1"], {"S0"}), ["no snapshot for S1", "CANNOT S0: no token"])
        self.assertEqual(grading.setup_problems([], ["S0"], {"S0"}), [])


class JudgmentTest(unittest.TestCase):
    LINES = [{"seq": 4, "batch": "b00", "clock": "c", "op": "mark", "request": {"text": "PROBE P-BK01-a START"}, "response": {"ok": True}},
             {"seq": 5, "batch": "b00", "clock": "c", "op": "http", "request": {}, "response": {"status": 201}},
             {"seq": 6, "batch": "b00", "op": "admin", "admin": True}]

    def test_the_judges_log_numbers_entries_and_leaves_admin_out(self):
        text = grading.log_for_judge(self.LINES)
        self.assertEqual(len(text.splitlines()), 2)
        self.assertIn('"seq": 5', text)

    def test_long_response_bodies_are_cut_for_the_judge(self):
        n = grading.MAX_JUDGE_BODY
        line = {"seq": 9, "op": "http", "request": {}, "response": {"status": 200, "body": "x" * (n + 3000)}}
        text = grading.log_for_judge([line])
        self.assertIn("[cut: 3000 more characters]", text)
        self.assertLess(len(text), n + 1000)

    def test_verdicts_must_cover_every_probe_and_cite_real_lines(self):
        ps = grading.parse_probes(PROBES).probes[:1]
        ok = {"verdicts": [{"probe": "P-BK01-a", "verdict": "met", "evidence": [5], "reason": "The order shows its customer."}]}
        self.assertEqual(grading.check_verdicts(ok, ps, self.LINES), [])
        for bad in ({"verdicts": []},
                    {"verdicts": [{"probe": "P-BK01-a", "verdict": "met", "evidence": [], "reason": "r"}]},
                    {"verdicts": [{"probe": "P-BK01-a", "verdict": "not met", "evidence": [5], "reason": "Placeholder"}]},
                    {"verdicts": [{"probe": "P-BK01-a", "verdict": "not met", "evidence": [99], "reason": "r"}]}):
            self.assertTrue(grading.check_verdicts(bad, ps, self.LINES))
        cx = {"verdicts": [{"probe": "P-BK01-a", "verdict": "couldn't exercise", "evidence": [], "reason": "The executor never placed the order.", "cause": "execution"}]}
        self.assertEqual(grading.check_verdicts(cx, ps, self.LINES), [])
        # "couldn't exercise" must say whether a rerun could settle it
        cx["verdicts"][0]["cause"] = "none"
        self.assertTrue(grading.check_verdicts(cx, ps, self.LINES))

    def test_a_setup_brings_the_setups_it_is_built_on(self):
        ps = grading.ProbeSet(preamble="", setup_notes="", probes=[], setups={
            "S0": "A lab.", "S1": "Identical to S0, plus Rhea.", "S2": "Identical to S0, plus Cedar; Noel is in S1 only.", "S3": "Other."})
        self.assertEqual(grading.setups_needed(ps, {"S2"}), ["S0", "S1", "S2"])
        self.assertEqual(grading.setups_needed(ps, {"S3", "S0"}), ["S0", "S3"])

    def test_only_execution_faults_are_run_again(self):
        v = {"P-1": {"verdict": "couldn't exercise", "cause": "execution"},
             "P-2": {"verdict": "couldn't exercise", "cause": "service"},
             "P-3": {"verdict": "not met", "cause": "none"},
             "P-4": {"verdict": "couldn't exercise"}}  # judged before causes were recorded
        self.assertEqual(grading.execution_faults(v), ["P-1"])

    def test_prompts_fill_in_one_pass(self):
        p = grading._template("grade-judge.md", PROBES="P {LOG}", LOG='{"x": "{PROBES}"}')
        self.assertIn('P {LOG}', p)
        self.assertIn('{"x": "{PROBES}"}', p)
        with self.assertRaises(KeyError):
            grading._template("grade-judge.md", PROBES="x")


if __name__ == "__main__":
    unittest.main()
