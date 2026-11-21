"""The growth test's harness pieces (design.md, "The growth test"; plan.md, M2d): the one-line arm, the change script's
course-change fields, and their validation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from costeval import simulator as sm, trajectory as tj  # noqa: E402


def change(n, *fields, title="A change"):
    body = "\n".join(f"**{k}:** {v}  " for k, v in fields)
    return f"## Change {n} — {title}\n\n### Owner request\n\n> Please do change {n}.\n\n**Introduces:** RD-{100 + n}.  \n{body}\n"


def script(*changes):
    return "# Change script\n\n" + "\n".join(changes)


def reliance(lag=3, *, setup="S0", outcomes=True, request=True):
    lines = ["### Reliance request", "", f"**Lag:** {lag}  ", f"**Setup:** {setup}  " if setup else "",
             "**Scenario:** Export this week's releases and read the file.  " if setup else ""]
    if outcomes:
        lines += ["**Current-rule outcome:** The export leaves embargoed titles out.  ",
                  "**Displaced-rule outcome:** The export lists embargoed titles.  "]
    if request:
        lines += ["", "> Can I get this week's releases as a file?"]
    return "\n".join(lines) + "\n"


def course(n, of, distance, lag=3, **kw):
    return (change(n, ("Course change", f"retirement of change {of} (distance {distance})"), ("Retires", f"RD-{100 + of}"))
            + "\n" + reliance(lag, **kw))


class OneLineArmTest(unittest.TestCase):
    def test_bare_with_one_sentence_at_the_repository_root(self):
        arm = tj.load_arm("bare-one-line")
        bare = tj.load_arm("bare")
        self.assertEqual((arm.plugins, arm.lid_release, arm.first_turn_mode), (bare.plugins, None, bare.first_turn_mode))
        self.assertEqual(list(arm.workspace_files), ["AGENTS.md"])  # read by the agent, as cheap discipline's is
        text = (tj.ARMS_DIR / arm.workspace_files["AGENTS.md"]).read_text()
        self.assertEqual(text.strip(), "When a rule changes, update its tests and their names.")


class CourseChangeFieldsTest(unittest.TestCase):
    def test_the_growth_fields_parse(self):
        s = sm.parse_change_script(script(
            change(3, ("Retires", "Nothing")),
            course(11, 3, 8, lag=4).replace("**Retires:** RD-103", "**Retires:** RD-103  \n**Intent distance:** set at change 3"),
            change(14, ("Intent distance", "same module")), change(15)))
        c = s[11].course_change
        self.assertEqual((c.kind, c.of_change, c.distance), ("retirement", 3, 8))
        self.assertEqual(s[11].retires, ("RD-103",))
        self.assertEqual((s[11].intent_distance.kind, s[11].intent_distance.set_at), ("set at change", 3))
        r = s[11].reliance_request
        self.assertEqual((r.lag, r.setup), (4, "S0"))
        self.assertEqual(r.request, "Can I get this week's releases as a file?")
        self.assertIn("leaves embargoed titles out", r.current_outcome)
        self.assertIn("lists embargoed titles", r.displaced_outcome)
        self.assertIn("Export this week's releases", r.scenario)
        self.assertEqual(s[14].intent_distance.kind, "same module")
        self.assertIsNone(s[14].course_change)
        self.assertIsNone(s[14].reliance_request)
        self.assertEqual(s[3].retires, ())
        self.assertEqual(sm.validate_growth_fields(s), [])

    def test_every_kind_of_course_change(self):
        for kind in ("retirement", "reversal", "rescope", "emerging", "re-reversal"):
            s = sm.parse_change_script(script(change(2), change(9, ("Course change", f"{kind} of change 2 (distance 7)"))
                                              + "\n" + reliance()))
            self.assertEqual(s[9].course_change.kind, kind)

    def test_a_malformed_field_is_refused(self):
        with self.assertRaisesRegex(ValueError, "Course change"):
            sm.parse_change_script(script(change(9, ("Course change", "a big change"))))
        with self.assertRaisesRegex(ValueError, "Intent distance"):
            sm.parse_change_script(script(change(9, ("Intent distance", "far away"))))
        with self.assertRaisesRegex(ValueError, "Lag"):
            sm.parse_change_script(script(change(9, ("Course change", "retirement of change 2 (distance 7)"))
                                          + "\n" + reliance().replace("**Lag:** 3", "**Lag:** soon")))

    def test_links_resolve_and_distances_hold(self):
        s = sm.parse_change_script(script(
            change(2), course(6, 2, 4), change(7, ("Course change", "reversal of change 40 (distance 1)")) + "\n" + reliance(),
            change(8, ("Course change", "rescope of change 2 (distance 6)")) + "\n" + reliance(),
            change(12, ("Intent distance", "set at change 15")), change(13)))
        problems = sm.validate_growth_fields(s)
        self.assertTrue(any("change 6" in p and "at least 5" in p for p in problems))       # a retirement 4 back
        self.assertTrue(any("change 7" in p and "change 40" in p for p in problems))         # no such earlier change
        self.assertTrue(any("change 7" in p and "distance" in p for p in problems))          # 1 isn't 7 - 40
        self.assertTrue(any("change 12" in p and "change 15" in p for p in problems))       # set later than it
        self.assertFalse(any("change 8" in p and "at least 5" in p for p in problems))       # a rescope has no floor

    def test_each_course_change_has_one_reliance_request_with_a_lag_of_2_to_5_and_two_outcomes(self):
        s = sm.parse_change_script(script(
            change(1), change(2),
            change(8, ("Course change", "retirement of change 1 (distance 7)")),                   # none
            course(9, 2, 7, lag=6),                                                                 # too late
            course(10, 2, 8, outcomes=False),                                                       # no outcomes
            course(11, 2, 9, setup=None),                                                           # no scenario
            course(12, 2, 10, request=False),                                                       # no request
            change(14) + "\n" + reliance()))                                                         # not a course change
        problems = sm.validate_growth_fields(s)
        self.assertTrue(any("change 8" in p and "no reliance request" in p for p in problems))
        self.assertTrue(any("change 9" in p and "2 to 5" in p for p in problems))
        self.assertTrue(any("change 10" in p and "outcome" in p for p in problems))
        self.assertTrue(any("change 11" in p and "setup" in p for p in problems))
        self.assertTrue(any("change 12" in p and "request" in p for p in problems))
        self.assertTrue(any("change 14" in p and "isn't a course change" in p for p in problems))
        self.assertTrue(any("change 12" in p and "change 15" in p for p in problems))  # 12 + 3 is past the script

    def test_the_old_reliance_field_still_parses(self):
        s = sm.parse_change_script(script(change(2), change(13, ("Reliance for", "change 9, change 10"))))
        self.assertEqual(s[13].reliance_for, (9, 10))

    def test_the_drafters_growth_script_validates(self):
        hidden = Path(__file__).resolve().parent.parent.parent / "seeds" / "releasedesk" / "hidden"
        f = hidden / "change-script-growth.md"
        if not f.exists() or "### Reliance request" not in f.read_text():
            self.skipTest("no growth script with reliance requests yet (round 2)")
        first = (hidden / "change-script.md").read_text().split("\n## Probe request", 1)[0]
        s = sm.parse_change_script(first + "\n\n" + f.read_text())
        self.assertEqual(sm.validate_growth_fields(s), [])

    def test_the_existing_scripts_still_parse_and_validate(self):
        for seed in ("benchtime", "releasedesk"):
            text = (Path(__file__).resolve().parent.parent.parent / "seeds" / seed / "hidden" / "change-script.md").read_text()
            s = sm.parse_change_script(text)
            self.assertEqual(sm.validate_growth_fields(s), [], seed)


# ----------------------------------------------------------------------------------------- course and reliance forks

import contextlib  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import tempfile  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from costeval import grading, growth  # noqa: E402
from test_grading import PROBES  # noqa: E402
from test_simulator import BRIEF, ORACLE, OWNER_ITEMS, FakeAsk, out  # noqa: E402
from test_trajectory import FakeTurns, FakeWorkspace  # noqa: E402

GROWTH_SCRIPT = script(
    "## Change 1 — Fees\n\n### Owner request\n\n> Add fees.\n\n**Introduces:** BK-05.\n",
    "## Change 2 — Drop fees\n\n### Owner request\n\n> Drop the fees.\n\n**Introduces:** BK-06.  \n**Retires:** BK-05.  \n"
    "**Course change:** retirement of change 1 (distance 1)\n\n" + reliance(2),
    "## Change 3 — Refunds\n\n### Owner request\n\n> Refunds.\n\n**Introduces:** BK-07.\n",
    "## Change 4 — Receipts\n\n### Owner request\n\n> Receipts.\n\n**Introduces:** BK-08.\n")


def probe(pid, applies, setup, steps, expected):
    return (f"#### {pid}\n- **Applies:** {applies}\n- **Setup:** {setup}\n- **Needs:** none\n- **Scenario:**\n"
            + "".join(f"  {i}. {x}\n" for i, x in enumerate(steps, 1)) + f"- **Expected observation:** {expected}\n")


SHARED = ["As Ada Vale, place an order in the second shop.", "Try to read its charges."]
GROWTH_PROBES = "\n".join([
    "# Probes: Bakery, growth", "", "Version 3.", "", "## Setups", "", "### S0: Example shop", "",
    "Start with empty data and load the shop.", "", "### S20: Two shops", "", "Identical to S0, plus a second shop.", "",
    "## Probes", "",
    "### RD-01", "", probe("P-RD01-a", "from change 2, until change 11", "S0", ["Place an order."], "It has a fee."),
    probe("P-RD01-flip12", "from change 2, until change 11", "S20", SHARED, "Step 2 shows a fee."),
    "### RD-02", "", probe("P-RD02-a", "from change 12", "S0", ["Place an order."], "It has no fee."),
    probe("P-RD02-flip12", "from change 12", "S20", SHARED, "Step 2 shows no fee."),
    "### RD-03", "", probe("P-RD03-a", "from change 3, until change 10", "S0", ["Copy an order."], "The copy keeps its price."),
    probe("P-RD03-a-r11", "from change 11, until change 12", "S0", ["Copy an order today."], "The copy keeps its price."),
    "### RD-04", "", probe("P-RD04-a", "from change 13", "S0", ["Copy an order."], "The copy takes today's price."),
    "### RD-05", "", probe("P-RD05-a", "from change 4, until change 13", "S0", ["Refund a cake."], "Cakes are refunded."),
    "### RD-06", "", probe("P-RD06-a", "from change 14", "S0", ["Refund a cake."], "Cakes are refunded."),
    probe("P-RD06-flip14", "from change 14", "S20", ["Try to refund bread."], "Bread is refunded."),
    "### RD-07", "", probe("P-RD07-a", "from change 5, until change 14", "S0", ["Refund an order."], "Orders are refunded."),
    probe("P-RD07-flip15", "from change 5, until change 14", "S20", ["Try to refund a gift card."], "The gift card is refunded."),
    "### RD-08", "", probe("P-RD08-a", "from change 15", "S0", ["Refund an order."], "Orders are refunded."),
    "### RD-09", "", probe("P-RD09-flip16", "from change 6, until change 15", "S20", ["Try a late return."], "It is taken."),
    "### RD-10", "", probe("P-RD10-flip16", "from change 16", "S20", ["Try a late return."], "It is refused."),
    "### RR-12", "", probe("P-RR12-current", "from change 0", "S20", ["Export this week's orders."], "No fees are listed."),
    probe("P-RR12-displaced", "from change 0", "S20", ["Export this week's orders."], "Fees are listed."),
])


def growth_change(n, title, retires, introduces, course):
    return (f"## Change {n} — {title}\n\n### Owner request\n\n> Please do change {n}.\n\n**Introduces:** {introduces}.  \n"
            f"**Retires:** {retires}.  \n**Course change:** {course}\n\n" + reliance(2))


FLIP_SCRIPT = script(change(2), change(3), *[change(n) for n in range(4, 12)],
                     growth_change(12, "Drop fees", "RD-01", "RD-02", "reversal of change 2 (distance 10)"),
                     growth_change(13, "Copies at today's price", "RD-03", "RD-04", "retirement of change 3 (distance 10)"),
                     growth_change(14, "Refund every item", "RD-05", "RD-06", "rescope of change 4 (distance 10)"),
                     growth_change(15, "No refunds on gift cards", "RD-07", "RD-08", "rescope of change 5 (distance 10)"),
                     growth_change(16, "Late returns", "RD-09", "RD-10", "rescope of change 6 (distance 10)"),
                     change(17), change(18))


class GrowthHelpersTest(unittest.TestCase):
    def test_each_course_changes_reliance_request_runs_once_its_lag_has_passed(self):
        s = sm.parse_change_script(GROWTH_SCRIPT)
        self.assertEqual(growth.reliance_requests(s), [(2, 2)])  # (course change, lag): run after change 4
        self.assertEqual(growth.reliance_requests(s, upto=3), [])

    def test_the_reliance_outcomes_are_the_seeds_own_follow_up_probes(self):
        ps = grading.parse_probes(GROWTH_PROBES)
        self.assertEqual(growth.reliance_probes(ps, 12), ["P-RR12-current", "P-RR12-displaced"])
        self.assertIsNone(growth.reliance_probes(ps, 13))  # none in the seed: nothing invented

    def test_the_current_rules_probes_are_those_in_force_where_the_request_runs(self):
        ps = grading.parse_probes(GROWTH_PROBES)
        s = sm.parse_change_script(FLIP_SCRIPT)
        self.assertEqual(growth.current_rule_probes(s, ps, 12), ["P-RD02-a", "P-RD02-flip12"])  # run after change 14
        self.assertEqual(growth.current_rule_probes(s, ps, 13), ["P-RD04-a"])

    def test_a_course_fork_is_judged_by_the_flip_pair_where_the_seed_has_one(self):
        ps = grading.parse_probes(GROWTH_PROBES)
        s = sm.parse_change_script(FLIP_SCRIPT)
        self.assertEqual(growth.course_fork_probes(s, ps, 12),
                         (["P-RD02-flip12"], ["P-RD01-flip12"], {"RD-01": "flip", "RD-02": "flip"}))
        # no flip pair: each row's probes in force on its side of the change
        self.assertEqual(growth.course_fork_probes(s, ps, 13),
                         (["P-RD04-a"], ["P-RD03-a-r11"], {"RD-03": "all", "RD-04": "all"}))

    def test_a_rescope_states_whether_it_widens_or_narrows(self):
        s = sm.parse_change_script(script(change(2), change(9, ("Course change", "rescope of change 2 (distance 7), widening"))))
        self.assertEqual((s[9].course_change.kind, s[9].course_change.reach), ("rescope", "widening"))
        s = sm.parse_change_script(script(change(2), change(9, ("Course change", "rescope of change 2 (distance 7)"))))
        self.assertIsNone(s[9].course_change.reach)
        with self.assertRaisesRegex(ValueError, "widens or narrows"):
            sm.parse_change_script(script(change(2), change(9, ("Course change", "retirement of change 2 (distance 7), narrowing"))))

    def test_a_rescopes_flip_is_one_sided_by_its_reach_inferred_from_the_flip_probes_when_unstated(self):
        ps = grading.parse_probes(GROWTH_PROBES)
        s = sm.parse_change_script(FLIP_SCRIPT)
        plan = growth.flip_plan(s, ps, upto=16)
        sides = lambda n: [(e["when"], e["probes"], e["reach"], e["reach_source"]) for e in plan if e["course"] == n]  # noqa: E731
        # widening: the narrower old row still holds after it, so only the new row is checked, before the change
        self.assertEqual(sides(14), [("before", ["P-RD06-flip14"], "widening", "flip probes")])
        # narrowing: only the old row, after the change
        self.assertEqual(sides(15), [("after", ["P-RD07-flip15"], "narrowing", "flip probes")])
        # flip probes on both sides: two-sided
        self.assertEqual(sides(16), [("after", ["P-RD09-flip16"], "both", "flip probes"),
                                     ("before", ["P-RD10-flip16"], "both", "flip probes")])
        self.assertTrue(all("reach" not in e for e in plan if e["kind"] != "rescope"))
        # the course fork: the same sides
        self.assertEqual(growth.course_fork_probes(s, ps, 14)[:2], (["P-RD06-flip14"], []))
        self.assertEqual(growth.course_fork_probes(s, ps, 15)[:2], ([], ["P-RD07-flip15"]))
        self.assertEqual(growth.course_fork_probes(s, ps, 16)[:2], (["P-RD10-flip16"], ["P-RD09-flip16"]))
        self.assertEqual(growth.rescope_reach(s, ps, 14), ("widening", "flip probes"))

    def test_a_widening_rescopes_before_check_is_read_as_anticipated_not_as_an_expected_failure(self):
        ps = grading.parse_probes(GROWTH_PROBES)
        s = sm.parse_change_script(FLIP_SCRIPT)
        plan = {(e["course"], e["when"]): e for e in growth.flip_plan(s, ps, upto=16)}
        self.assertEqual(plan[14, "before"]["expect"], "anticipated?")  # widening: the narrower build may already pass
        self.assertEqual(plan[15, "after"]["expect"], "not met")  # narrowing: the old row must fail after
        self.assertEqual((plan[16, "after"]["expect"], plan[16, "before"]["expect"]), ("not met", "not met"))

    def test_the_change_scripts_word_for_a_rescope_wins_over_the_flip_probes(self):
        ps = grading.parse_probes(GROWTH_PROBES)
        s = sm.parse_change_script(FLIP_SCRIPT.replace("rescope of change 4 (distance 10)", "rescope of change 4 (distance 10), narrowing"))
        plan = [e for e in growth.flip_plan(s, ps, upto=14) if e["course"] == 14]
        # narrowing as stated: the old row, after; it has no flip probe, so its probes in force at change 13
        self.assertEqual([(e["when"], e["probes"], e["choice"], e["reach"], e["reach_source"]) for e in plan],
                         [("after", ["P-RD05-a"], {"RD-05": "all"}, "narrowing", "change script")])

    def test_a_rescope_without_flip_probes_or_a_stated_reach_stays_two_sided(self):
        ps = grading.parse_probes(PROBES)
        s = sm.parse_change_script(GROWTH_SCRIPT.replace("BK-05", "BK-01").replace("BK-06", "BK-02")
                                   .replace("retirement of change 1", "rescope of change 1"))
        self.assertEqual([(e["when"], e["reach"], e["reach_source"]) for e in growth.flip_plan(s, ps, upto=3)],
                         [("after", "unknown", "no flip probes"), ("before", "unknown", "no flip probes")])

    def test_a_row_without_a_flip_probe_is_skipped_when_another_row_on_its_side_has_one(self):
        # change 27 retires three rows and only one has a flip probe: the other two, which can't flip, aren't run
        ps = grading.parse_probes(GROWTH_PROBES.replace("### RD-04", "### RD-11\n\n" + probe(
            "P-RD11-a", "from change 2, until change 11", "S0", ["Count orders."], "Counted.") + "\n### RD-04"))
        s = sm.parse_change_script(FLIP_SCRIPT.replace("**Retires:** RD-01.", "**Retires:** RD-01, RD-11."))
        after = next(e for e in growth.flip_plan(s, ps, upto=12) if e["course"] == 12 and e["when"] == "after")
        self.assertEqual((after["probes"], after["choice"]), (["P-RD01-flip12"], {"RD-01": "flip", "RD-11": "skipped"}))
        self.assertEqual(growth.course_fork_probes(s, ps, 12)[1:], (["P-RD01-flip12"], {"RD-01": "flip", "RD-11": "skipped",
                                                                                       "RD-02": "flip"}))

    def test_flip_checks_run_only_the_flip_probe_where_the_seed_has_one(self):
        ps = grading.parse_probes(GROWTH_PROBES)
        s = sm.parse_change_script(FLIP_SCRIPT)
        plan = {(e["course"], e["when"]): e for e in growth.flip_plan(s, ps, upto=13)}
        self.assertEqual((plan[12, "after"]["probes"], plan[12, "after"]["choice"]), (["P-RD01-flip12"], {"RD-01": "flip"}))
        self.assertEqual((plan[12, "before"]["probes"], plan[12, "before"]["choice"]), (["P-RD02-flip12"], {"RD-02": "flip"}))
        # no flip probe: every probe of the row in force beside the change (not the one a replacement ended earlier)
        self.assertEqual((plan[13, "after"]["probes"], plan[13, "after"]["choice"]), (["P-RD03-a-r11"], {"RD-03": "all"}))
        self.assertEqual((plan[13, "before"]["probes"], plan[13, "before"]["choice"]), (["P-RD04-a"], {"RD-04": "all"}))
        self.assertEqual(plan[12, "after"]["at_change"], 12)
        self.assertEqual(plan[12, "before"]["at_change"], 11)

    def test_a_reliance_fork_follows_the_current_rule_the_displaced_one_neither_or_both(self):
        o = growth.reliance_outcome
        self.assertEqual(o("met", "not met"), "current")
        self.assertEqual(o("not met", "met"), "displaced")
        self.assertEqual(o("not met", "not met"), "neither")
        self.assertEqual(o("met", "met"), "both")
        self.assertEqual(o("missing", "not met"), "undetermined")
        self.assertEqual(o(None, None), "undetermined")

    def test_probes_by_item_and_the_flip_checks_of_a_retirement(self):
        ps = grading.parse_probes(PROBES)
        self.assertEqual(growth.probes_for(ps, {"BK-01"}), ["P-BK01-a", "P-BK01-b"])
        s = sm.parse_change_script(GROWTH_SCRIPT.replace("BK-05", "BK-01").replace("BK-06", "BK-02"))
        self.assertEqual(growth.flip_plan(s, ps, upto=3), [
            {"course": 2, "kind": "retirement", "when": "after", "at_change": 2, "items": ["BK-01"],
             "probes": ["P-BK01-a", "P-BK01-b"], "choice": {"BK-01": "all"}, "expect": "not met"},
            {"course": 2, "kind": "retirement", "when": "before", "at_change": 1, "items": ["BK-02"],
             "probes": ["P-BK02-a"], "choice": {"BK-02": "all"}, "expect": "not met"}])

    def test_a_rescope_flips_as_a_reversal_and_an_emerging_change_is_checked_for_anticipation(self):
        ps = grading.parse_probes(PROBES)
        base = GROWTH_SCRIPT.replace("BK-05", "BK-01").replace("BK-06", "BK-02")
        rescope = sm.parse_change_script(base.replace("retirement of change 1", "rescope of change 1"))
        self.assertEqual([(e["when"], e["expect"]) for e in growth.flip_plan(rescope, ps, upto=3)],
                         [("after", "not met"), ("before", "not met")])
        emerging = sm.parse_change_script(base.replace("retirement of change 1", "emerging of change 1")
                                          .replace("**Retires:** BK-01.  \n", ""))
        self.assertEqual(growth.flip_plan(emerging, ps, upto=3), [
            {"course": 2, "kind": "emerging", "when": "before", "at_change": 1, "items": ["BK-02"], "probes": ["P-BK02-a"],
             "choice": {"BK-02": "all"}, "expect": "anticipated?"}])

    def test_owner_hours_at_238_words_a_minute(self):
        self.assertAlmostEqual(growth.owner_hours(238 * 60), 1.0)


class DriftFloorTest(unittest.TestCase):
    def test_the_owners_draws_depend_on_the_replicate_alone(self):
        # a drift-floor trajectory shares bare-1's replicate, so its owner draws the same numbers whatever its id
        self.assertEqual(sm.uniform("g-r1", "RD-04", "recall", "c03"), sm.uniform("g-r1", "RD-04", "recall", "c03"))
        self.assertNotEqual(sm.uniform("g-r1", "RD-04", "recall", "c03"), sm.uniform("g-r2", "RD-04", "recall", "c03"))


EMPTY_STATE = {"record": [], "requests": [], "seen": {}, "disclosed": []}


class CourseForkTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.seed = self.root / "seed"
        (self.seed / "hidden").mkdir(parents=True)
        (self.seed / "brief.md").write_text(BRIEF)
        (self.seed / "hidden" / "oracle.md").write_text(ORACLE)
        (self.seed / "hidden" / "change-script.md").write_text(GROWTH_SCRIPT)
        (self.seed / "hidden" / "owner-items.json").write_text(json.dumps(OWNER_ITEMS))
        self.runs = self.root / "runs"
        base = self.runs / "g-bare-1"
        base.mkdir(parents=True)
        (base / "trajectory.json").write_text(json.dumps({
            "id": "g-bare-1", "arm": "bare", "seed": "seed", "model": "m", "effort": "medium", "policy": "bounded",
            "owner_model": "o", "replicate": "g-r1", "isolation": {"window": "1m"}, "round_cap": 6,
            "volumes": {"workspace": "ce-g-bare-1-ws", "config": "ce-g-bare-1-cfg"},
            "changes": {str(n): {"commit": f"c-after-{n}"} for n in range(1, 5)}}))
        for n in (1, 4):
            (base / f"owner-state-{n:02d}.json").write_text(json.dumps({**EMPTY_STATE, "disclosed": ["BK-02"]}))

    def fork(self, kind, *turn_texts):
        import run_course_forks as rcf
        docker, ws = [], FakeWorkspace()
        turns = FakeTurns(ws, *[(t, None, ["src/app.py"]) for t in turn_texts])
        ask = FakeAsk(*[out("completion") for _ in turn_texts])
        deps = rcf.Deps(docker=lambda cmd, **kw: docker.append(cmd) or subprocess_ok(cmd), turn_for=lambda s: turns,
                        workspace_for=lambda image, vol: ws, ask=ask, touch=ask.touch, trim=None)
        argv = ["--id", "g-bare-1", "--kind", kind, "--course", "2", "--fork", "1", "--runs", str(self.runs),
                "--seed-dir", str(self.seed)]
        return rcf.main(argv, deps=deps), docker, turns, argv, deps, ask

    def test_a_course_fork_runs_the_course_change_alone_from_the_snapshot_before_it(self):
        rc, docker, turns, argv, deps, ask = self.fork("course", "Done: fees dropped.")
        self.assertEqual(rc, 0)
        meta = json.loads((self.runs / "g-bare-1" / "course-forks" / "c02-course-1" / "trajectory.json").read_text())
        self.assertEqual((meta["kind"], meta["fork_of"], meta["course"]), ("course", "g-bare-1", 2))
        self.assertEqual((meta["change"], meta["commit"]), (2, "c-after-1"))
        self.assertEqual(sorted(meta["changes"]), ["2"])  # one change long
        self.assertEqual(meta["replicate"], "g-r1-course02-fork-1")
        self.assertTrue(all("agent_cost_usd" in c and "owner_cost_usd" in c for c in meta["changes"].values()))
        self.assertIn("c-after-1", " ".join(docker[0]))
        self.assertEqual(meta["volumes"]["workspace"], "ce-g-bare-1-course02-1-ws")
        self.assertEqual(turns.calls[0]["resume"], None)
        import run_course_forks as rcf
        self.assertEqual(rcf.main(argv, deps=deps), 0)  # recorded already: left alone
        self.assertEqual(len(docker), 1)

    def test_a_reliance_fork_runs_the_request_from_the_trajectorys_snapshot_after_the_lag(self):
        rc, docker, turns, argv, deps, ask = self.fork("reliance", "Done: the file is ready.")
        self.assertEqual(rc, 0)
        meta = json.loads((self.runs / "g-bare-1" / "course-forks" / "c02-reliance-1" / "trajectory.json").read_text())
        self.assertEqual((meta["kind"], meta["course"], meta["lag"], meta["at"]), ("reliance", 2, 2, 4))
        self.assertEqual(meta["commit"], "c-after-4")  # after change 2 + 2: the changes in between included
        self.assertIn("c-after-4", " ".join(docker[0]))
        self.assertEqual(meta["replicate"], "g-r1-reliance02-fork-1")
        self.assertEqual(list(meta["changes"]), ["reliance"])
        self.assertIn("Can I get this week's releases as a file?", turns.calls[0]["prompt"])  # the request, fresh session
        self.assertEqual(turns.calls[0]["resume"], None)

    def test_a_growth_forks_owner_holds_the_main_lines_state_never_the_clowder_forks_scope(self):
        # the reliance fork's owner stands at change 4 as the main line's does: every item in force by then, the retired
        # ones gone, and what it had told the agent by then
        rc, docker, turns, argv, deps, ask = self.fork("reliance", "Done.")
        o = sm.parse_oracle(ORACLE)
        main_line = {i.id for i in sm.released_items(o, 4)}
        clowder = {i.id for i in sm.released_items(o, 4, only_change=True)}
        self.assertNotEqual(main_line, clowder)  # the two scopes differ here, so the check means something
        prompt = ask.prompts[0]
        for i in main_line:
            self.assertIn(f"[{i}]", prompt)
        for i in {x.id for x in o.items} - main_line:  # retired by change 4, or not yet in force
            self.assertNotIn(f"[{i}]", prompt)
        import run_course_forks as rcf
        self.assertFalse(rcf.LAST_OWNER.only_change)
        self.assertIn("BK-02", rcf.LAST_OWNER.disclosed)  # the trajectory's owner state at that point

    def test_discarding_removes_the_forks_volumes(self):
        import run_course_forks as rcf
        docker = []
        rcf.main(["--id", "g-bare-1", "--kind", "reliance", "--course", "2", "--fork", "1", "--runs", str(self.runs), "--discard"],
                 deps=rcf.Deps(docker=lambda cmd, **kw: docker.append(cmd) or subprocess_ok(cmd)))
        self.assertEqual(docker, [["docker", "volume", "rm", "-f", "ce-g-bare-1-reliance02-1-ws", "ce-g-bare-1-reliance02-1-cfg"]])


class PendingTest(unittest.TestCase):
    """pending.py: whether a queued job has work left, so the pacing gate never holds up one that doesn't."""

    def setUp(self):
        self.runs = Path(tempfile.mkdtemp())
        base = self.runs / "g-bare-1"
        (base / "course-forks" / "c02-reliance-1").mkdir(parents=True)
        (base / "trajectory.json").write_text(json.dumps({"changes": {
            "0": {"finished": "t", "commit": "a"}, "1": {"finished": "t", "commit": "b"},
            "2": {"finished": "t", "error": "stopped"}}}))
        (base / "course-forks" / "c02-reliance-1" / "trajectory.json").write_text(json.dumps(
            {"kind": "reliance", "course": 2, "at": 4, "changes": {"reliance": {"commit": "f4"}}}))

    def left(self, *argv):
        import pending
        return pending.main([*argv, "--runs", str(self.runs)]) == 0

    def test_a_batch_has_work_left_until_each_change_finished_without_error(self):
        self.assertFalse(self.left("batch", "--id", "g-bare-1", "--changes", "0,1"))
        self.assertTrue(self.left("batch", "--id", "g-bare-1", "--changes", "0,1,2"))  # stopped: run again
        self.assertTrue(self.left("batch", "--id", "g-bare-1", "--changes", "3,4"))
        self.assertTrue(self.left("batch", "--id", "g-new-1", "--changes", "0"))

    def test_a_fork_has_work_left_until_it_is_recorded(self):
        self.assertFalse(self.left("fork", "--id", "g-bare-1", "--kind", "reliance", "--course", "2", "--fork", "1"))
        self.assertTrue(self.left("fork", "--id", "g-bare-1", "--kind", "reliance", "--course", "2", "--fork", "2"))
        self.assertTrue(self.left("fork", "--id", "g-bare-1", "--kind", "course", "--course", "2", "--fork", "1"))

    def test_a_checkpoint_has_work_left_until_it_finished_with_every_fork_it_should_grade(self):
        self.assertTrue(self.left("checkpoint", "--id", "g-bare-1", "--change", "4"))
        g = self.runs / "g-bare-1" / "growth" / "checkpoint-04"
        g.mkdir(parents=True)
        (g / "status.json").write_text(json.dumps({"finished": True, "left": [], "forks": ["c02-reliance-1"]}))
        self.assertFalse(self.left("checkpoint", "--id", "g-bare-1", "--change", "4"))


# ------------------------------------------------------------------------------------- rows realized on a symptom

from test_simulator import CHANGES as SYMPTOM_SCRIPT  # noqa: E402  (change 5: a symptom report bringing BK-07)

LATER = sm.Change(number=6, title="Gift cards", request="Add gift cards.")


class SymptomRealizationTest(unittest.TestCase):
    """A row realized on a symptom (BK-07, change 5) comes into force for the owner only once its report was delivered
    on that trajectory: the report fires only if the build gets the rule wrong."""

    def owner(self, delivered):
        o = sm.parse_oracle(ORACLE)
        owner = sm.Owner(oracle=o, brief=BRIEF, policy="bounded", replicate="g-r1", ask=FakeAsk(),
                         touch=lambda p: {"touches": []}, owner_items=sm.parse_owner_items(OWNER_ITEMS, o))
        tj.restore_owner_state(owner, {**EMPTY_STATE, "requests": [[n, f"request {n}"] for n in delivered]})
        return owner

    def held(self, owner, change=LATER):
        owner.start_change(change)
        prompt = owner._prompt("Done.", [], None)
        touchable = sm.touch_items(owner.oracle, change, disclosed=set(), realized=owner.realized)
        return "[BK-07]" in prompt, "original card" in prompt, "BK-07" in touchable

    def test_an_owner_holds_a_symptom_row_only_once_its_report_was_delivered(self):
        self.assertEqual(self.held(self.owner([1, 2, 3, 4])), (False, False, False))  # change 5's diagnostic passed
        self.assertEqual(self.held(self.owner([1, 2, 3, 4, 5])), (True, True, True))  # its report was delivered

    def test_the_report_brings_the_row_in_force_while_it_is_delivered_and_after(self):
        owner = self.owner([1, 2, 3, 4])
        self.assertEqual(self.held(owner, sm.parse_change_script(SYMPTOM_SCRIPT)[5]), (True, True, True))
        owner.end_change()
        self.assertEqual(self.held(owner), (True, True, True))

    def test_a_reliance_forks_owner_never_gets_a_symptom_row_whose_report_had_not_fired_by_its_snapshot(self):
        import run_course_forks as rcf
        seed = Path(tempfile.mkdtemp())
        (seed / "hidden").mkdir()
        (seed / "brief.md").write_text(BRIEF)
        (seed / "hidden" / "oracle.md").write_text(ORACLE)
        (seed / "hidden" / "owner-items.json").write_text(json.dumps(OWNER_ITEMS))
        symptom = "## Change 5" + SYMPTOM_SCRIPT.split("## Change 5", 1)[1].split("## Probe request", 1)[0]
        (seed / "hidden" / "change-script.md").write_text(GROWTH_SCRIPT.replace("**Lag:** 2", "**Lag:** 3") + "\n" + symptom)
        for fired in (False, True):
            runs = Path(tempfile.mkdtemp())
            base = runs / "g-bare-1"
            base.mkdir()
            changes = {str(n): {"commit": f"c-after-{n}"} for n in range(1, 6)}
            changes["5"]["symptom"] = "fired" if fired else "not fired: diagnostic passed"
            (base / "trajectory.json").write_text(json.dumps({
                "id": "g-bare-1", "arm": "bare", "seed": "seed", "model": "m", "effort": "medium", "policy": "bounded",
                "owner_model": "o", "replicate": "g-r1", "isolation": {"window": "1m"}, "round_cap": 6,
                "volumes": {"workspace": "ce-g-bare-1-ws", "config": "ce-g-bare-1-cfg"}, "changes": changes}))
            (base / "owner-state-05.json").write_text(json.dumps(
                {**EMPTY_STATE, "requests": [[n, "r"] for n in (range(1, 6) if fired else range(1, 5))]}))
            ws = FakeWorkspace()
            turns = FakeTurns(ws, ("Done: the file is ready.", None, ["src/app.py"]))
            ask = FakeAsk(out("completion"))
            deps = rcf.Deps(docker=lambda cmd, **kw: subprocess_ok(cmd), turn_for=lambda s: turns,
                            workspace_for=lambda image, vol: ws, ask=ask, touch=ask.touch, trim=None)
            rc = rcf.main(["--id", "g-bare-1", "--kind", "reliance", "--course", "2", "--fork", "1", "--runs", str(runs),
                           "--seed-dir", str(seed)], deps=deps)
            self.assertEqual(rc, 0)
            meta = json.loads((base / "course-forks" / "c02-reliance-1" / "trajectory.json").read_text())
            self.assertEqual((meta["at"], meta["commit"]), (5, "c-after-5"))
            self.assertEqual(("[BK-07]" in ask.prompts[0], "original card" in ask.prompts[0]), (fired, fired))
            self.assertEqual("BK-07" in rcf.LAST_OWNER.realized, fired)

    def test_a_symptom_report_never_runs_as_a_course_fork(self):
        # a report is delivered only after its diagnostic fires, on the main line; a fork would deliver it regardless
        import run_course_forks as rcf
        root = Path(tempfile.mkdtemp())
        (root / "seed" / "hidden").mkdir(parents=True)
        for name, text in (("brief.md", BRIEF), ("hidden/oracle.md", ORACLE), ("hidden/owner-items.json", json.dumps(OWNER_ITEMS))):
            (root / "seed" / name).write_text(text)
        symptom = "## Change 5" + SYMPTOM_SCRIPT.split("## Change 5", 1)[1].split("## Probe request", 1)[0].replace(
            "**Introduces:** BK-07.", "**Introduces:** BK-07.  \n**Course change:** reversal of change 1 (distance 4)")
        (root / "seed" / "hidden" / "change-script.md").write_text(script(change(1)) + "\n" + symptom)
        (root / "runs" / "g-bare-1").mkdir(parents=True)
        (root / "runs" / "g-bare-1" / "trajectory.json").write_text(json.dumps({"seed": "seed", "changes": {"4": {"commit": "c4"}}}))
        (root / "runs" / "g-bare-1" / "owner-state-04.json").write_text(json.dumps(EMPTY_STATE))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = rcf.main(["--id", "g-bare-1", "--kind", "course", "--course", "5", "--fork", "1", "--runs", str(root / "runs"),
                           "--seed-dir", str(root / "seed")], deps=rcf.Deps(docker=lambda cmd, **kw: subprocess_ok(cmd)))
        self.assertEqual(rc, 2)
        self.assertIn("symptom report", out.getvalue())


def subprocess_ok(cmd):
    import subprocess
    return subprocess.CompletedProcess(cmd, 0, "", "")


# ------------------------------------------------------------------------------------------- the stale-intent audit

from costeval import stale_audit as sa  # noqa: E402


class StaleAuditTest(unittest.TestCase):
    def test_methodology_vocabulary_and_spec_ids_are_stripped(self):
        text = ("// @spec REL-PUB-003\n# Publishing (see the EARS spec in docs/intent/pub-specs.md)\n"
                "def test_publish_needs_review():  # REL-PUB-003: per the HLD\n    assert publish(r) == 'refused'\n")
        out = sa.neutralize(text)
        for gone in ("@spec", "REL-PUB-003", "EARS", "HLD", "docs/intent"):
            self.assertNotIn(gone, out)
        self.assertIn("def test_publish_needs_review():", out)
        self.assertIn("assert publish(r) == 'refused'", out)

    def test_spec_reads_as_requirement_in_comments_docstrings_and_docs_but_never_in_code(self):
        py = 'def test_spec_runner():\n    """The spec says a release needs review."""\n    spec = load()  # the specs agree\n'
        out = sa.neutralize(py, "tests/test_review.py")
        self.assertIn("def test_spec_runner():", out)       # an identifier stays
        self.assertIn("spec = load()", out)
        self.assertIn('"""The requirement says a release needs review."""', out)
        self.assertIn("# the requirements agree", out)
        js = "// Spec: publish needs review\nconst spec = require('./spec');\n/* the specs */\n"
        out = sa.neutralize(js, "test/review.test.js")
        self.assertIn("// Requirement: publish needs review", out)
        self.assertIn("const spec = require('./spec');", out)
        self.assertIn("/* the requirements */", out)
        self.assertIn("The requirement for publishing", sa.neutralize("The spec for publishing.\n", "docs/publishing.md"))
        self.assertIn("requirement", sa.prompt(path="a.py", text="x = 1\n", current="A rule.", retired=None).lower())

    def test_the_files_a_course_change_touched_or_should_have(self):
        touched = ["src/app.py", "tests/test_fees.py", "docs/fees.md", "README.md"]
        files = {"tests/test_fees.py": "...", "tests/test_refunds.py": "late fee waived", "tests/test_other.py": "nothing",
                 "docs/fees.md": "...", "src/app.py": "late fee"}
        self.assertEqual(sa.audit_files(touched, files, terms=["late fee"]),
                         ["docs/fees.md", "tests/test_fees.py", "tests/test_refunds.py"])

    def test_a_ruling_on_each_file_with_checked_evidence(self):
        prompt = sa.prompt(path="tests/test_fees.py", text="def test_late_fee():\n    assert fee(r) == 5\n",
                           current="No late fee is charged.", retired="A late fee of 5 is charged.")
        self.assertIn("No late fee is charged.", prompt)
        self.assertIn("A late fee of 5 is charged.", prompt)
        self.assertIn("contradicts", prompt)  # the core question: does anything contradict current intent?
        self.assertIn("    2  ", prompt)  # the file's lines are numbered
        emerging = sa.prompt(path="tests/test_fees.py", text="x\n", current="Fees are waived for staff.", retired=None)
        self.assertNotIn("<retired>", emerging)  # an emerging change has no retired intent: current intent only
        good = {"name": "contradicts", "comments": "silent", "assertions": "contradicts", "verdict": "stale",
                "evidence": [1, 2], "reason": "The test still charges the retired late fee."}
        self.assertEqual(sa.check(good, lines=2), [])
        self.assertTrue(sa.check({**good, "evidence": [9]}, lines=2))
        self.assertTrue(sa.check({**good, "verdict": "fine"}, lines=2))

    def test_the_audit_asks_once_per_file_and_records_every_ruling(self):
        calls = []

        def ask(prompt):
            calls.append(prompt)
            return {"name": "current", "comments": "current", "assertions": "current", "verdict": "current",
                    "evidence": [1], "reason": "It checks that no late fee is charged."}, 0.01
        result = sa.audit({"tests/test_fees.py": "def test_no_late_fee():\n    assert fee(r) == 0\n"},
                          current="No late fee is charged.", retired="A late fee of 5 is charged.", ask=ask)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["files"]["tests/test_fees.py"]["verdict"], "current")
        self.assertEqual((result["stale"], result["current"], result["cost_usd"]), (0, 1, 0.01))


# --------------------------------------------------------------------------------------------- the positive control

import plant_stale_tests as pst  # noqa: E402


class PositiveControlTest(unittest.TestCase):
    def test_stale_tests_in_the_builds_own_language_with_the_index_kept_apart(self):
        tests = {"tests/test_publish.py": "import pytest\n\ndef test_publish():\n    assert True\n",
                 "tests/test_review.py": "def test_review():\n    pass\n"}
        retired = {"RD-12": "A release may be published without review.", "RD-19": "Embargoed releases show their title."}
        planted, index = pst.plant(tests, retired, seed="pc-1")
        self.assertEqual(set(tests) <= set(planted), True)  # the build's own tests, unchanged
        new = sorted(set(planted) - set(tests))
        self.assertEqual(len(new), 2)
        self.assertTrue(all(p.startswith("tests/") and p.endswith(".py") for p in new))
        body = "\n".join(planted[p] for p in new)
        self.assertIn("published without review", body)
        self.assertNotIn("RD-12", body)  # no oracle IDs, and nothing says it was planted
        self.assertNotIn("planted", body.lower())
        self.assertEqual(sorted(index["planted"]), new)
        self.assertEqual({v["item"] for v in index["planted"].values()}, {"RD-12", "RD-19"})

    def test_a_names_only_plant_leaves_nothing_of_its_rule_once_names_comments_and_docstrings_are_replaced(self):
        from costeval import intent_recall as ir
        tests = {"tests/test_publish.py": "def test_publish():\n    assert True\n"}
        rule = "Embargoed releases show their title."
        planted, index = pst.plant(tests, {"RD-19": rule}, seed="pc-1")
        (path,) = set(planted) - set(tests)
        words = {"embargoed", "releases", "show", "title"}
        self.assertFalse(words & set(Path(path).stem.lower().split("_")), path)  # the file name says nothing of it
        self.assertIn("embargoed releases show their title", planted[path].lower())  # as written, the reader can see it
        (neutral,), _ = ir.neutralize([ir.InputFile(path=path, text=planted[path])])
        self.assertFalse(any(w in neutral.text.lower() for w in words), neutral.text)  # names replaced: nothing left

    def test_an_assertions_plant_gets_a_file_name_that_says_nothing_of_its_rule(self):
        tests = {"tests/test_publish.py": "def test_publish():\n    assert True\n"}

        def write(prompt):
            return {"file_name": "test_embargoed_titles_show.py",
                    "text": "def test_embargoed():\n    assert listing(embargoed=True).titles == ['Reed']\n"}, 0.0
        planted, index = pst.plant_assertions(tests, {"RD-19": "Embargoed releases show their title."}, seed="pc-1",
                                              write=write)
        (path,) = set(planted) - set(tests)
        self.assertNotIn("embargoed", path)

    def test_the_language_follows_the_builds_tests(self):
        js = {"test/publish.test.js": "test('publishes', () => { expect(1).toBe(1) })\n"}
        planted, _ = pst.plant(js, {"RD-12": "A release may be published without review."}, seed="pc-1")
        self.assertTrue(any(p.endswith(".test.js") and "test(" in planted[p] for p in set(planted) - set(js)))


# ------------------------------------------------------------------------------------------ the checkpoint pipeline

import growth_checkpoint as gc  # noqa: E402


class FakeVolumes:
    """Docker volumes as dicts: the workspace's files at each commit, and what each change's commit touched."""

    def __init__(self, at, touched):
        self.at, self.touched, self.scripts = at, touched, []

    def __call__(self, volume):
        outer = self

        class Shell:
            def sh(self, script, stdin=None, check=True):
                outer.scripts.append((volume, script))
                if "ls-tree" in script:
                    commit = script.split("ls-tree -r --name-only ")[1].split()[0]
                    return "\n".join(outer.at[commit]) + "\n"
                if "git show" in script:
                    commit, path = script.split("git show ")[1].split(":", 1)
                    return outer.at[commit].get(path.strip("'"), "")
                if "diff --name-only" in script:
                    return "\n".join(outer.touched) + "\n"
                return ""
        return Shell()


class GrowthCheckpointTest(unittest.TestCase):
    TESTS = {"tests/test_fees.py": "def test_late_fee_is_waived():\n    assert fee(r) == 0\n", "src/app.py": "x",
             "docs/rules.md": "Fees: none.", "tests/test_refunds.py": "def test_refund():\n    # no late fee on refunds\n    assert 1\n"}

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.seed = self.root / "seeds" / "bk"
        (self.seed / "hidden").mkdir(parents=True)
        (self.seed / "brief.md").write_text(BRIEF)
        (self.seed / "hidden" / "oracle.md").write_text(ORACLE)
        (self.seed / "hidden" / "change-script.md").write_text(GROWTH_SCRIPT.replace("BK-05", "BK-01").replace("BK-06", "BK-02"))
        (self.seed / "hidden" / "probes.md").write_text(PROBES)
        (self.seed / "hidden" / "stale-audit-terms.json").write_text(json.dumps({"2": ["late fee"]}))
        self.runs = self.root / "runs"
        t = self.runs / "g-bare-1"
        t.mkdir(parents=True)
        (t / "trajectory.json").write_text(json.dumps({
            "id": "g-bare-1", "arm": "bare", "seed": "bk", "replicate": "g-r1",
            "volumes": {"workspace": "ce-g-bare-1-ws"},
            "changes": {str(n): {"commit": f"c{n}"} for n in range(1, 5)}}))
        for name, meta in (("c02-course-1", {"kind": "course", "change": 2, "course": 2, "commit": "c1",
                                             "volumes": {"workspace": "ce-g-bare-1-course02-1-ws"}, "changes": {"2": {"commit": "f2"}}}),
                           ("c02-reliance-1", {"kind": "reliance", "change": 4, "course": 2, "lag": 2, "at": 4, "commit": "c4",
                                               "volumes": {"workspace": "ce-g-bare-1-reliance02-1-ws"},
                                               "changes": {"reliance": {"commit": "f4"}}})):
            (t / "course-forks" / name).mkdir(parents=True)
            (t / "course-forks" / name / "trajectory.json").write_text(json.dumps(meta))
        self.commands = []

    def run_pipeline(self, *steps, ask=None):
        vols = FakeVolumes({"c4": self.TESTS, "f2": self.TESTS}, touched=["tests/test_fees.py", "src/app.py"])
        rc = gc.main(["--id", "g-bare-1", "--change", "4", "--runs", str(self.runs), "--seeds", str(self.root / "seeds"),
                      *(["--steps", ",".join(steps)] if steps else [])],
                     run=lambda cmd: self.commands.append(cmd) or 0, volume=vols,
                     ask=ask or (lambda p: ({"name": "current", "comments": "silent", "assertions": "current",
                                              "verdict": "current", "evidence": [1], "reason": "It waives the fee as intended."}, 0.01)))
        return rc, vols

    def grading_writes_verdicts(self, cmd):
        """A grading run that leaves verdicts where grade_checkpoint.py would."""
        self.commands.append(cmd)
        if "grade_checkpoint.py" in cmd:
            fid, n = cmd[cmd.index("--id") + 1], int(cmd[cmd.index("--change") + 1])
            name = cmd[cmd.index("--out-name") + 1] if "--out-name" in cmd else f"change-{n:02d}"
            probes = cmd[cmd.index("--probes") + 1].split(",") if "--probes" in cmd else ["P-BK01-a"]
            g = self.runs / fid / "grading" / name
            g.mkdir(parents=True, exist_ok=True)
            (g / "verdicts.json").write_text(json.dumps({"probes": {x: "met" for x in probes}}))
        return 0

    def test_a_checkpoint_is_finished_once_every_step_ran_and_nothing_is_left(self):
        vols = FakeVolumes({"c4": self.TESTS, "f2": self.TESTS}, touched=["tests/test_fees.py"])
        argv = ["--id", "g-bare-1", "--change", "4", "--runs", str(self.runs), "--seeds", str(self.root / "seeds")]
        ask = lambda p: ({"name": "current", "comments": "silent", "assertions": "current", "verdict": "current",  # noqa: E731
                          "evidence": [1], "reason": "As intended."}, 0.01)
        gc.main(argv, run=lambda cmd: self.commands.append(cmd) or 0, volume=vols, ask=ask)  # gradings that left nothing
        status = json.loads((self.runs / "g-bare-1" / "growth" / "checkpoint-04" / "status.json").read_text())
        self.assertFalse(status["finished"])
        self.assertIn("grade", status["left"])
        self.assertTrue(gc.pending(self.runs, "g-bare-1", 4))
        gc.main(argv, run=self.grading_writes_verdicts, volume=vols, ask=ask)
        status = json.loads((self.runs / "g-bare-1" / "growth" / "checkpoint-04" / "status.json").read_text())
        self.assertEqual((status["finished"], status["left"]), (True, []))
        self.assertEqual(sorted(status["forks"]), ["c02-course-1", "c02-reliance-1"])
        self.assertFalse(gc.pending(self.runs, "g-bare-1", 4))
        # a fork recorded after the checkpoint finished still needs it
        late = self.runs / "g-bare-1" / "course-forks" / "c02-reliance-2"
        late.mkdir(parents=True)
        (late / "trajectory.json").write_text(json.dumps({"kind": "reliance", "course": 2, "at": 4,
                                                          "changes": {"reliance": {"commit": "f9"}}}))
        self.assertTrue(gc.pending(self.runs, "g-bare-1", 4))
        g3 = self.runs / "g-bare-1" / "growth" / "checkpoint-03"
        g3.mkdir(parents=True)
        (g3 / "status.json").write_text(json.dumps({"finished": True, "left": [], "forks": ["c02-course-1"]}))
        self.assertFalse(gc.pending(self.runs, "g-bare-1", 3))  # the reliance forks at change 4 aren't checkpoint 3's

    def test_grading_flip_checks_and_course_forks(self):
        rc, _ = self.run_pipeline("grade", "flips")
        self.assertEqual(rc, 0)
        cmds = [" ".join(c) for c in self.commands]
        self.assertTrue(any("grade_checkpoint.py --id g-bare-1 --change 4 --seed bk" in c and "--probes" not in c for c in cmds))
        self.assertTrue(any("--change 2" in c and "--probes P-BK01-a,P-BK01-b" in c and "--out-name flip-c02-after" in c for c in cmds))
        self.assertTrue(any("--change 1" in c and "--probes P-BK02-a" in c and "--out-name flip-c02-before" in c for c in cmds))
        # each course fork: the new rule and the retired one at its end, then audited, then discarded
        self.assertTrue(any("--id g-bare-1/course-forks/c02-course-1 --change 2" in c and "--out-name course" in c
                            and "P-BK01-a" in c and "P-BK02-a" in c for c in cmds))
        self.assertTrue(any("run_course_forks.py --id g-bare-1 --kind course --course 2 --fork 1 --discard" in c for c in cmds))
        rows = json.loads((self.runs / "g-bare-1" / "growth" / "checkpoint-04" / "course-forks.json").read_text())
        self.assertEqual(rows[0]["choice"], {"BK-01": "all", "BK-02": "all"})  # the fixture has no flip pair
        audit = json.loads((self.runs / "g-bare-1" / "course-forks" / "c02-course-1" / "growth" / "stale-audit.json").read_text())
        self.assertIn("tests/test_fees.py", audit["files"])

    RR02 = ("\n### RR-02\n\n#### P-RR02-current\n- **Applies:** from change 0\n- **Setup:** S0\n- **Needs:** none\n"
            "- **Scenario:**\n  1. Export this week's orders.\n- **Expected observation:** No fees are listed.\n\n"
            "#### P-RR02-displaced\n- **Applies:** from change 0\n- **Setup:** S0\n- **Needs:** none\n"
            "- **Scenario:**\n  1. Export this week's orders.\n- **Expected observation:** Fees are listed.\n")

    def test_a_reliance_fork_without_the_seeds_follow_up_probes_is_recorded_as_no_probe(self):
        self.run_pipeline("reliance")
        self.assertFalse(any("grade_checkpoint.py" in " ".join(c) or "--discard" in c for c in self.commands))  # kept to grade later
        rows = json.loads((self.runs / "g-bare-1" / "growth" / "checkpoint-04" / "reliance.json").read_text())
        self.assertEqual([(r["course"], r["fork"], r["outcome"]) for r in rows], [(2, "1", "no probe")])

    def test_a_flip_check_whose_grading_left_no_verdict_is_undetermined_not_a_failed_flip(self):
        self.assertIsNone(gc.flip_behaves({}, ["P-a"], "not met"))
        self.assertIsNone(gc.flip_behaves({"P-a": "not met"}, ["P-a", "P-b"], "not met"))
        self.assertTrue(gc.flip_behaves({"P-a": "not met", "P-b": "not met"}, ["P-a", "P-b"], "not met"))
        self.assertFalse(gc.flip_behaves({"P-a": "met", "P-b": None}, ["P-a", "P-b"], "not met"))  # decided
        self.assertIsNone(gc.flip_behaves({}, ["P-a"], "anticipated?"))
        self.assertTrue(gc.flip_behaves({"P-a": "met"}, ["P-a"], "anticipated?"))

    def test_a_grading_that_errored_counts_as_not_done(self):
        d = Path(tempfile.mkdtemp())
        (d / "verdicts.json").write_text(json.dumps({"error": "setup: ['no identifier list']", "probes": {}}))
        self.assertIsNone(gc._verdicts(d))
        import instrument
        self.assertIsNone(instrument.verdicts(d))

    def test_the_current_rule_held_is_undetermined_where_a_probe_has_no_verdict(self):
        f = gc.current_rule_held
        self.assertTrue(f({"P-a": "met", "P-b": "met"}, ["P-a", "P-b"]))
        self.assertIsNone(f({"P-a": "met"}, ["P-a", "P-b"]))  # P-b not run (prior-data, a broken setup): undetermined
        self.assertIsNone(f({"P-a": "met", "P-b": "couldn't exercise"}, ["P-a", "P-b"]))
        self.assertFalse(f({"P-a": "not met"}, ["P-a", "P-b"]))  # a decided failure is a failure whatever else
        self.assertIsNone(f({}, ["P-a"]))
        self.assertIsNone(f({"P-a": "met"}, []))

    def test_each_reliance_fork_is_graded_on_its_two_frozen_outcomes_and_the_current_rule(self):
        (self.seed / "hidden" / "probes.md").write_text(PROBES + self.RR02)
        fork = self.runs / "g-bare-1" / "course-forks" / "c02-reliance-1"
        graded = []

        def run(cmd):
            self.commands.append(cmd)
            if "grade_checkpoint.py" in cmd:  # the grading the fork would get: it followed the displaced rule
                g = fork / "grading" / "reliance"
                g.mkdir(parents=True, exist_ok=True)
                (g / "verdicts.json").write_text(json.dumps({"probes": {"P-RR02-current": "not met", "P-RR02-displaced": "met",
                                                                        "P-BK02-a": "met"}}))
                graded.append(cmd)
            return 0
        gc.main(["--id", "g-bare-1", "--change", "4", "--runs", str(self.runs), "--seeds", str(self.root / "seeds"),
                 "--steps", "reliance"], run=run, volume=FakeVolumes({}, touched=[]), ask=None)
        cmd = " ".join(graded[0])
        self.assertIn("--id g-bare-1/course-forks/c02-reliance-1", cmd)
        self.assertIn("--commit f4", cmd)
        self.assertIn("--probes P-RR02-current,P-RR02-displaced,P-BK02-a", cmd)  # the outcomes and the current rule
        self.assertNotIn("--probes-file", cmd)  # the seed's own probes
        self.assertTrue(any("run_course_forks.py --id g-bare-1 --kind reliance --course 2 --fork 1 --discard" in " ".join(c)
                            for c in self.commands))
        rows = json.loads((self.runs / "g-bare-1" / "growth" / "checkpoint-04" / "reliance.json").read_text())
        self.assertEqual([(r["course"], r["fork"], r["outcome"], r["current_rule_held"]) for r in rows],
                         [(2, "1", "displaced", True)])
        self.assertFalse(any("--id g-bare-1 --change" in " ".join(c) for c in graded))  # nothing on the main line

    def test_an_emerging_change_is_checked_for_anticipation_not_counted_as_a_flip(self):
        (self.seed / "hidden" / "change-script.md").write_text(
            GROWTH_SCRIPT.replace("BK-05", "BK-01").replace("BK-06", "BK-02").replace("retirement of change 1", "emerging of change 1")
            .replace("**Retires:** BK-01.  \n", ""))
        g = self.runs / "g-bare-1" / "grading" / "flip-c02-before"
        g.mkdir(parents=True)
        (g / "verdicts.json").write_text(json.dumps({"probes": {"P-BK02-a": "met"}}))
        self.run_pipeline("flips")
        flips = json.loads((self.runs / "g-bare-1" / "growth" / "checkpoint-04" / "flips.json").read_text())
        self.assertEqual([(f["kind"], f["anticipated"], f["behaves"]) for f in flips], [("emerging", True, None)])

    def test_intent_from_tests_and_docs_through_the_other_cli_with_a_plan(self):
        rc, vols = self.run_pipeline("intent")
        plan = json.loads((self.runs / "intent-from-tests" / "growth-g-bare-1-c04" / "plan.json").read_text())
        labels = {i["label"]: i for i in plan["inputs"]}
        self.assertEqual(sorted(labels), ["brief", "g-bare-1-c04-docs", "g-bare-1-c04-tests", "g-bare-1-c04-tests-neutral"])
        self.assertTrue(labels["g-bare-1-c04-tests-neutral"]["neutral"])
        self.assertEqual(labels["g-bare-1-c04-tests"]["oracle"], {"kind": "benchtime", "seed": "bk", "change": 4})
        self.assertEqual(labels["g-bare-1-c04-tests"]["baseline"], "brief")
        self.assertEqual(labels["g-bare-1-c04-tests"]["verdicts"], "runs/g-bare-1/grading/change-04")
        cmds = [" ".join(c) for c in self.commands]
        self.assertTrue(any("intent_from_tests.py batch --plan" in c for c in cmds))
        self.assertTrue(any("intent_from_tests.py summarize --name growth-g-bare-1-c04" in c for c in cmds))
        self.assertIn("docker volume rm -f ce-gc-g-bare-1-c04", cmds)  # the readers' copy goes once they're done

    def test_the_stale_intent_audit_on_what_each_course_change_touched_or_should_have(self):
        seen = []

        def ask(prompt):
            seen.append(prompt)
            return {"name": "contradicts", "comments": "silent", "assertions": "contradicts", "verdict": "stale",
                    "evidence": [1], "reason": "It still expects the retired fee."}, 0.02
        rc, _ = self.run_pipeline("stale", ask=ask)
        out = json.loads((self.runs / "g-bare-1" / "growth" / "checkpoint-04" / "stale-audit.json").read_text())
        # touched by the change, and mentioning the area's terms
        self.assertEqual(sorted(out["courses"]["2"]["files"]), ["tests/test_fees.py", "tests/test_refunds.py"])
        self.assertEqual(out["courses"]["2"]["stale"], 2)
        self.assertNotIn("g-bare-1", seen[0])  # nothing names the arm or the trajectory
        self.assertNotIn("bare", seen[0])

    def test_a_missing_intent_cli_leaves_a_hook(self):
        vols = FakeVolumes({"c4": {"tests/test_fees.py": "x"}}, touched=[])
        gc.main(["--id", "g-bare-1", "--change", "4", "--runs", str(self.runs), "--seeds", str(self.root / "seeds"),
                 "--steps", "intent"], run=lambda cmd: 2, volume=vols, ask=None)
        status = json.loads((self.runs / "g-bare-1" / "growth" / "checkpoint-04" / "status.json").read_text())
        self.assertEqual(status["intent"]["state"], "pending")
        self.assertIn("plan.json", status["intent"]["plan"])


class NestedForkGradingTest(unittest.TestCase):
    def test_a_fork_under_its_trajectory_grades_with_docker_safe_names(self):
        import grade_checkpoint
        self.assertEqual(grade_checkpoint.checkpoint_name("g-bare-1/course-forks/c13-1", "reliance"),
                         "g-bare-1-course-forks-c13-1-reliance")
        self.assertEqual(grade_checkpoint.checkpoint_name("s3b-bare-1"), "s3b-bare-1")


class PositiveControlAssertionsTest(unittest.TestCase):
    """The second kind of planted test: assertions that encode the retired behaviour, written by a model in the build's
    own style, so even the reader that sees no names or comments can catch them."""

    TESTS = {"tests/test_publish.py": "from app import publish\n\ndef test_publish_ok():\n    assert publish('r1').status == 200\n"}

    def test_a_model_writes_each_in_the_builds_style_and_a_bad_answer_is_asked_again(self):
        prompts = []
        answers = iter([
            ({"file_name": "test_review.py", "text": "def test_x():\n    # RD-12, planted\n    assert True\n"}, 0.01),   # names the item
            ({"file_name": "test_review.py", "text": "def test_publish_without_review():\n"
                                                     "    assert publish('r2', reviewed=False).status == 200\n"}, 0.01)])

        def write(prompt):
            prompts.append(prompt)
            return next(answers)
        planted, index = pst.plant_assertions(self.TESTS, {"RD-12": "A release may be published without review."},
                                              seed="pc-1", write=write)
        self.assertIn("A release may be published without review.", prompts[0])
        self.assertIn("def test_publish_ok", prompts[0])  # a sample of the build's tests, for style
        self.assertNotIn("RD-12", prompts[0])
        self.assertEqual(len(prompts), 2)
        new = sorted(set(planted) - set(self.TESTS))
        self.assertEqual(len(new), 1)
        self.assertTrue(new[0].startswith("tests/test_") and new[0].endswith(".py") and "review" not in new[0])
        self.assertIn("reviewed=False", planted[new[0]])
        self.assertEqual(index["kind"], "assertions")
        self.assertEqual(index["planted"][new[0]]["item"], "RD-12")
        self.assertAlmostEqual(index["cost_usd"], 0.02)

    def test_an_item_with_no_valid_answer_is_left_out_and_recorded(self):
        planted, index = pst.plant_assertions(self.TESTS, {"RD-12": "A rule."}, seed="pc-1",
                                              write=lambda p: ({"file_name": "x.py", "text": ""}, 0.0))
        self.assertEqual(set(planted), set(self.TESTS))
        self.assertEqual(index["failed"], ["RD-12"])

    def test_the_names_kind_is_labelled_too(self):
        _, index = pst.plant(self.TESTS, {"RD-12": "A rule."}, seed="pc-1")
        self.assertEqual(index["kind"], "names")
