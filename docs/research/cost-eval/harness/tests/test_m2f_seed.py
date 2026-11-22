"""Tests for the M2f seed converter (build_m2f_seed.py, costeval/m2f_seed.py): the drafter's M2f change set turned
into the Clowder harness's change script, oracle, owner items, repair reports and kept-behaviour record, and the
change script's two M2f intent distances.

The synthetic excerpt below follows m2f-changes-r2.md's layout: one core change whose shell depends on the rule (a
dependency row first under "Behaviour to keep", and a Dependency repair report), one control, and a repair-report
section carrying an HTML comment, as the real file's do. The last test converts the real file.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_m2f_seed  # noqa: E402
from costeval import m2f_seed as ms, repair, simulator as sm  # noqa: E402

M2F = """# Clowder M2f changes (a two-change excerpt)

## Change 13 — A faster top speed

**Type:** core-change-ui-depends
**Intent distance:** other crate
**Edits crate:** clowder-core
**Edits component:** sim/engine
**Intent lives in:** tui/navigation

### Owner request

> could the meadow go up to 16×? sometimes i want to see a few more seasons go by.

### New rows

| ID | Behaviour | Disclosure kind | Check |
|---|---|---|---|
| CLX-1301 | The meadow can run at 16×, and speeds above 16× are capped there. | Stated | **Core:** Apply `SetSpeed(16)` and then `SetSpeed(1000)`; check 16 after each. |
| CLX-1302 | The higher speed survives saving and reopening. | Askable | **Core + save:** Round-trip a meadow set to 16×. |

- **CLX-1302** recall: “yes, remember how fast i left it going, just like before.”

**Left to the developer:** How the available speeds are exposed to the shell. **For grading:** record how each build exposed them. **For grading:** count the builds.

### Behaviour to keep

| Behaviour | Established in | How a careless version breaks it | Check |
|---|---|---|---|
| The speed keys reach the core's bounds in both directions. | SIM-ENG-024; TUI-NAV-028 | The keys stop at 8×. | **Keys + core:** Press speed-up until it stops. |
| The default is 1×. | SIM-ENG-016; clowder-core/tests/integration/engine.rs::default_speed | Replacing the clamp changes the default. | **Core:** Check a fresh state. |

**Deliberate change:** SIM-ENG-024 raises the upper clamp from 8× to 16×.

**Shell requirement a right build rewrites:** TUI-NAV-028's notches gain the new top. **Invariants it keeps:** the existing notches.

### Retired tests

- `clowder-core/tests/integration/engine.rs::speed_is_clamped` — update the old ceiling assertion.
- `clowder-core/src/achievements.rs` unit test `tests::every_condition_holds` — its witness moves.
- all two tests in `clowder-tui/tests/integration/armed_summary.rs`, which share a fixture check.

The key-resolution test stays in force.

### Why the other crate is needed

The shell stops at the end of its own speed sequence, so raising only the core's ceiling leaves the key stopping at 8×.

**Search note, for grading:** the plain variant's sweep finds the shell line.

### Repair reports

<!-- CLX-1302: rewritten by Claude, not Sol; see the edit log. -->

- **CLX-1301:** “i tried running the meadow at 16× and then asking for more. it didn't settle at 16×.”
- **CLX-1302:** “i reopened the fast meadow and it wasn't at 16×.”
- **Dependency:** “i pressed faster until it wouldn't go any further. that's not what happened.”

## Change 21 — Forage for the space that's left

**Type:** control
**Intent distance:** other module, same crate
**Edits crate:** clowder-core
**Edits component:** sim/economy
**Intent lives in:** sim/engine

### Owner request

> when there's only a sliver of room for twigs, Forage still takes the whole handful of catnip.

### New rows

| ID | Behaviour | Disclosure kind | Check |
|---|---|---|---|
| CLX-2101 | With room for less than one twig, Forage fills that space for the same fraction of its bill. | Stated | **Core:** Set twig headroom to 0.25 and apply `Forage`. |
| CLX-2102 | With less than the fractional bill, Forage refuses. | Askable | **Core:** Offer 2 catnip at 0.25 twig of room. |

- **CLX-2102** recall: “if not, leave the bowl alone.”

**Left to the developer:** Internal arithmetic.

### Behaviour to keep

| Behaviour | Established in | How a careless version breaks it | Check |
|---|---|---|---|
| With room for a twig, an application takes ten catnip. | SIM-ECO-005 | It buys everything that fits. | **Core:** Apply once with five twigs of room. |
| Full twigs produce `StorageFull`. | SIM-ECO-006; SIM-ENG-006 | A zero-sized purchase succeeds. | **Core:** Apply at full twigs. |

**Deliberate change:** SIM-ECO-005's bill is proportional when only a fraction of a twig fits.

### Retired tests

None. The tests the draft listed stay in force.

### Repair reports

<!-- CLX-2101: rewritten by Claude (Opus 5.5), not Sol; see m2f-edit-log.md, E1. -->

- **CLX-2101:** “i foraged with a quarter twig of space. that isn't what happened.”
- **CLX-2102:** “i tried with half a catnip less. it didn't turn it down cleanly.”

| Change | Type | Intent distance | Edits crate | Components |
|---|---|---|---|---|
| 13 — Faster top speed | core-change-ui-depends | other crate | clowder-core | sim/engine → tui/navigation |
| 21 — Partial Forage | control | other module, same crate | clowder-core | sim/economy → sim/engine |
"""

PILOT = """# Oracle

## Owner narrative

The simulated owner receives the start.

### What the owner knows from the start

Clowder is my game: a cozy incremental about raising kittens.

I play it from the keyboard.

### Learned at change 1: leaving some ingredients behind

Crafting everything is handy.

## Disclosure and grading conventions

- Background.

## Item table

| ID | Checkable behavior | Disclosure kind | In force | Retired | External check sketch |
|---|---|---|---|---|---|
| CLW-001 | Kittens never die. | Stated at start | Start | — | Run a long meadow. |
| CLW-101 | Dropped: a first draft. | Dropped | — | — | Not graded. |
| CLW-104 | A crafting action accepts reserve amounts. | Stated in change 1 | Change 1 | — | Craft with a reserve. |
| CLW-107 | Each ingredient takes its own amount. | Askable | Change 1 | — | Brass from buttons. |
"""

PILOT_NO_START = PILOT.replace("| CLW-001 | Kittens never die. | Stated at start | Start | — | Run a long meadow. |\n", "")

TEST_INDEX = {
    "clowder-core/tests/integration/engine.rs": {"tests": ["speed_is_clamped", "default_speed"]},
    "clowder-tui/tests/integration/armed_summary.rs": {"tests": ["the_summary_names_the_row", "the_summary_fits"]},
}

EXPECTED = ms.Expected(changes=(13, 21), core=(13,), rows=4, stated=2, askable=2)


def script_of(*changes):
    return "# Change script\n\n" + "\n".join(
        f"## Change {n} — A change\n\n**Intent distance:** {d}  \n\n### Owner request\n\n> Please do change {n}.\n"
        for n, d in changes)


class IntentDistanceTest(unittest.TestCase):
    def test_the_two_m2f_distances_parse(self):
        s = sm.parse_change_script(script_of((13, "other crate"), (21, "other module, same crate"), (22, "other crate.")))
        self.assertEqual(s[13].intent_distance, sm.IntentDistance("other crate"))
        self.assertEqual(s[21].intent_distance, sm.IntentDistance("other module, same crate"))
        self.assertEqual(s[22].intent_distance.kind, "other crate")
        self.assertEqual(sm.validate_growth_fields(s), [])

    def test_the_pilot_and_growth_distances_still_parse(self):
        s = sm.parse_change_script(script_of((2, "same module"), (3, "another module"), (9, "set at change 2")))
        self.assertEqual(s[2].intent_distance.kind, "same module")
        self.assertEqual(s[3].intent_distance.kind, "another module")
        self.assertEqual((s[9].intent_distance.kind, s[9].intent_distance.set_at), ("set at change", 2))

    def test_anything_else_is_still_refused(self):
        for bad in ("other crates", "other module", "same crate", "other module same crate", "far away"):
            with self.assertRaisesRegex(ValueError, "Intent distance", msg=bad):
                sm.parse_change_script(script_of((13, bad)))


class ParseTest(unittest.TestCase):
    def setUp(self):
        self.changes = ms.parse_m2f(M2F, test_index=TEST_INDEX)

    def test_each_changes_fields_and_request(self):
        c = self.changes[13]
        self.assertEqual(sorted(self.changes), [13, 21])
        self.assertEqual((c.title, c.type, c.intent_distance, c.edits_crate, c.edits_component, c.intent_lives_in),
                         ("A faster top speed", "core-change-ui-depends", "other crate", "clowder-core", "sim/engine",
                          "tui/navigation"))
        self.assertEqual(c.request, "could the meadow go up to 16×? sometimes i want to see a few more seasons go by.")
        self.assertEqual(self.changes[21].intent_distance, "other module, same crate")

    def test_new_rows_with_their_kinds_checks_and_recall_lines(self):
        rows = self.changes[13].rows
        self.assertEqual([(r.id, r.kind) for r in rows], [("CLX-1301", "Stated"), ("CLX-1302", "Askable")])
        self.assertTrue(rows[0].check.startswith("**Core:** Apply `SetSpeed(16)`"))
        self.assertIsNone(rows[0].recall)
        self.assertEqual(rows[1].recall, "yes, remember how fast i left it going, just like before.")  # no quote marks

    def test_kept_rows_are_numbered_in_table_order_with_the_dependency_first_in_a_core_change(self):
        keep = self.changes[13].keep
        self.assertEqual([(k.id, k.dependency) for k in keep], [("CLXK-1301", True), ("CLXK-1302", False)])
        self.assertEqual(keep[0].established_in, ["SIM-ENG-024", "TUI-NAV-028"])
        self.assertEqual(keep[1].established_in, ["SIM-ENG-016", "clowder-core/tests/integration/engine.rs::default_speed"])
        self.assertEqual(keep[0].breaks, "The keys stop at 8×.")
        self.assertEqual([(k.id, k.dependency) for k in self.changes[21].keep], [("CLXK-2101", False), ("CLXK-2102", False)])

    def test_repair_reports_lose_html_comments_and_quote_marks(self):
        self.assertEqual(self.changes[13].reports, {
            "CLX-1301": "i tried running the meadow at 16× and then asking for more. it didn't settle at 16×.",
            "CLX-1302": "i reopened the fast meadow and it wasn't at 16×.",
            "Dependency": "i pressed faster until it wouldn't go any further. that's not what happened."})
        self.assertEqual(sorted(self.changes[21].reports), ["CLX-2101", "CLX-2102"])
        for c in self.changes.values():
            for text in c.reports.values():
                self.assertNotIn("<!--", text)

    def test_retired_tests_including_a_unit_test_and_a_whole_file_expanded_from_the_index(self):
        self.assertEqual(self.changes[13].retired_tests, [
            "clowder-core/tests/integration/engine.rs::speed_is_clamped",
            "clowder-core/src/achievements.rs::tests::every_condition_holds",
            "clowder-tui/tests/integration/armed_summary.rs::the_summary_names_the_row",
            "clowder-tui/tests/integration/armed_summary.rs::the_summary_fits"])
        self.assertIn("The key-resolution test stays in force.", self.changes[13].retired_note)
        self.assertEqual(self.changes[21].retired_tests, [])

    def test_the_deliberate_change_the_other_crate_and_the_grading_notes(self):
        c = self.changes[13]
        self.assertEqual(c.deliberate_change, "SIM-ENG-024 raises the upper clamp from 8× to 16×.")
        self.assertEqual(c.left_to_developer, "How the available speeds are exposed to the shell.")
        self.assertTrue(c.why_other_crate.startswith("The shell stops at the end"))
        self.assertNotIn("Search note", c.why_other_crate)
        self.assertEqual([n["label"] for n in c.notes],
                         ["For grading", "For grading", "Shell requirement a right build rewrites", "Search note, for grading"])
        self.assertEqual([n["text"] for n in c.notes[:2]], ["record how each build exposed them.", "count the builds."])
        self.assertIn("**Invariants it keeps:** the existing notches.", c.notes[2]["text"])  # a note keeps its own labels
        self.assertIsNone(self.changes[21].why_other_crate)
        self.assertEqual(self.changes[21].notes, [])

    def test_malformed_sources_are_refused(self):
        cases = {
            "out of sequence": M2F.replace("| CLX-1302 |", "| CLX-1303 |").replace("**CLX-1302** recall", "**CLX-1303** recall"),
            "Recognized on sight": M2F.replace("| Askable | **Core + save:**", "| Recognized on sight | **Core + save:**"),
            "no recall line": M2F.replace("- **CLX-1302** recall: “yes, remember how fast i left it going, just like before.”\n", ""),
            "isn't a row": M2F.replace("- **CLX-1302:** “i reopened", "- **CLX-1302, save:** “i reopened"),
            "no Dependency": M2F.replace("- **Dependency:** “i pressed faster until it wouldn't go any further. that's not what happened.”\n", ""),
            "Dependency report in a control": M2F.replace("- **CLX-2102:** “i tried", "- **Dependency:** “a report.”\n- **CLX-2102:** “i tried"),
            "summary table": M2F.replace("| 21 — Partial Forage | control |", "| 21 — Partial Forage | core-change-ui-depends |"),
            "can't read": M2F.replace("- `clowder-core/tests/integration/engine.rs::speed_is_clamped`", "- the speed test"),
            "fifteen": M2F.replace("all two tests", "all fifteen tests"),
        }
        for what, text in cases.items():
            with self.assertRaisesRegex(ValueError, what, msg=what):
                ms.parse_m2f(text, test_index=TEST_INDEX)


class Converted:
    """The synthetic excerpt converted into a temporary folder."""

    def __init__(self, pilot=PILOT, salience=None):
        self.out = Path(tempfile.mkdtemp())
        if salience is not None:
            (self.out / "salience.json").write_text(json.dumps(salience))
        self.files = ms.write_seed(M2F, pilot, self.out, test_index=TEST_INDEX)

    def read(self, name):
        return (self.out / name).read_text(encoding="utf-8")

    def json(self, name):
        return json.loads(self.read(name))

    def check(self, pilot=PILOT):
        return ms.check_seed(self.out, M2F, pilot, test_index=TEST_INDEX, expected=EXPECTED)


class ConvertTest(unittest.TestCase):
    def test_it_writes_the_five_files(self):
        c = Converted()
        self.assertEqual(sorted(c.files), sorted(ms.OUTPUTS))
        for name in ms.OUTPUTS:
            self.assertTrue((c.out / name).exists(), name)

    def test_the_change_script_parses_with_the_harness(self):
        c = Converted()
        script = sm.parse_change_script(c.read("change-script.md"))
        self.assertEqual(sorted(script), [13, 21])
        self.assertEqual(script[13].title, "A faster top speed")
        self.assertEqual(script[13].request, "could the meadow go up to 16×? sometimes i want to see a few more seasons go by.")
        self.assertEqual(script[13].introduces, ("CLX-1301", "CLX-1302"))
        self.assertEqual(script[21].introduces, ("CLX-2101", "CLX-2102"))
        self.assertEqual(script[13].intent_distance.kind, "other crate")
        self.assertEqual(script[21].intent_distance.kind, "other module, same crate")
        for ch in script.values():
            self.assertEqual((ch.redirect, ch.symptom, ch.planted_bug, ch.retires, ch.relies_on), (None, None, None, (), ()))
        text = c.read("change-script.md")
        self.assertIn("**Kept behaviour:** CLXK-1301 (the dependency row), CLXK-1302", text)
        self.assertIn("**Edits crate:** clowder-core", text)
        self.assertIn("**Left to the agent (not graded):** How the available speeds are exposed to the shell.", text)

    def test_the_oracle_holds_the_start_its_start_items_and_each_changes_request_and_rows(self):
        c = Converted()
        oracle = sm.parse_oracle(c.read("oracle.md"))
        self.assertEqual(sorted(oracle.narrative), [0, 13, 21])
        self.assertEqual(oracle.narrative[0], "Clowder is my game: a cozy incremental about raising kittens.\n\nI play it from the keyboard.")
        self.assertEqual(oracle.narrative[13], "could the meadow go up to 16×? sometimes i want to see a few more seasons go by.")
        self.assertIn("### Learned at change 13: A faster top speed", c.read("oracle.md"))
        items = {i.id: i for i in oracle.items}
        self.assertEqual(sorted(items), ["CLW-001", "CLX-1301", "CLX-1302", "CLX-2101", "CLX-2102"])  # no pilot change items
        self.assertEqual((items["CLW-001"].kind, items["CLW-001"].in_force), ("Stated at start", 0))
        self.assertEqual((items["CLX-1301"].kind, items["CLX-1301"].in_force, items["CLX-1301"].retired),
                         ("Stated in change 13", 13, None))
        self.assertEqual((items["CLX-1302"].kind, items["CLX-1302"].in_force), ("Askable", 13))
        self.assertEqual(items["CLX-1301"].behavior, "The meadow can run at 16×, and speeds above 16× are capped there.")
        self.assertIn("| **Core:** Apply `SetSpeed(16)` and then `SetSpeed(1000)`; check 16 after each. |", c.read("oracle.md"))
        self.assertIn("quoted verbatim", c.read("oracle.md"))  # the conventions say where each section comes from

    def test_a_fork_releases_the_start_items_and_its_own_rows_only(self):
        c = Converted()
        oracle = sm.parse_oracle(c.read("oracle.md"))
        self.assertEqual({i.id for i in sm.released_items(oracle, 13, only_change=True)}, {"CLW-001", "CLX-1301", "CLX-1302"})
        self.assertEqual({i.id for i in sm.released_items(oracle, 21, only_change=True)}, {"CLW-001", "CLX-2101", "CLX-2102"})
        narrative = sm.released_narrative(oracle, 21, only_change=True)
        self.assertIn("raising kittens", narrative)
        self.assertIn("sliver of room", narrative)
        self.assertNotIn("16×", narrative)

    def test_without_start_items_the_oracle_still_parses(self):
        c = Converted(pilot=PILOT_NO_START)
        oracle = sm.parse_oracle(c.read("oracle.md"))
        self.assertEqual({i.id for i in sm.released_items(oracle, 13, only_change=True)}, {"CLX-1301", "CLX-1302"})
        self.assertIn("No item is in force at the start", c.read("oracle.md"))

    def test_owner_items_default_to_a_medium_placeholder(self):
        c = Converted()
        data = c.json("owner-items.json")
        self.assertEqual(data["tiers"], "placeholder: medium for every row (no salience rating yet)")
        owner = sm.load_owner_items(c.out / "owner-items.json", sm.parse_oracle(c.read("oracle.md")))
        self.assertEqual(owner, {"CLX-1302": sm.OwnerItem("medium", "yes, remember how fast i left it going, just like before."),
                                 "CLX-2102": sm.OwnerItem("medium", "if not, leave the bowl alone.")})

    def test_owner_items_take_their_tiers_from_salience_json_when_it_exists(self):
        c = Converted(salience={"CLX-1302": "high", "CLX-2102": "low", "CLX-1301": "medium"})  # a stated row's is ignored
        data = c.json("owner-items.json")
        self.assertEqual({k: v["tier"] for k, v in data["items"].items()}, {"CLX-1302": "high", "CLX-2102": "low"})
        self.assertNotIn("placeholder", data["tiers"])

    def test_a_salience_file_that_misses_a_row_or_names_a_bad_tier_is_refused(self):
        for salience, what in (({"CLX-1302": "high"}, "CLX-2102"), ({"CLX-1302": "high", "CLX-2102": "huge"}, "huge"),
                               ({"CLX-1302": "high", "CLX-2102": "low", "CLX-9901": "low"}, "CLX-9901")):
            with self.assertRaisesRegex(ValueError, what):
                Converted(salience=salience)

    def test_repair_reports_are_keyed_by_row_and_by_dependency(self):
        c = Converted()
        reports = c.json("repair-reports.json")
        self.assertEqual(sorted(reports), ["CLX-1301", "CLX-1302", "CLX-2101", "CLX-2102", "DEP-13"])
        self.assertEqual(reports["DEP-13"], {"report": "i pressed faster until it wouldn't go any further. that's not what happened.",
                                             "change": 13})
        self.assertEqual(repair.report_for(reports, "CLX-1302"), "i reopened the fast meadow and it wasn't at 16×.")
        self.assertNotIn("<!--", c.read("repair-reports.json"))

    def test_the_kept_behaviour_record(self):
        c = Converted()
        kept = c.json("kept-behaviour.json")
        self.assertEqual(sorted(kept), ["13", "21"])
        k13 = kept["13"]
        self.assertEqual((k13["type"], k13["intent_distance"], k13["edits_crate"]),
                         ("core-change-ui-depends", "other crate", "clowder-core"))
        self.assertEqual(k13["rows"][0], {"id": "CLXK-1301", "dependency": True,
                                          "behaviour": "The speed keys reach the core's bounds in both directions.",
                                          "established_in": ["SIM-ENG-024", "TUI-NAV-028"], "breaks": "The keys stop at 8×.",
                                          "check": "**Keys + core:** Press speed-up until it stops."})
        self.assertEqual(k13["deliberate_change"], "SIM-ENG-024 raises the upper clamp from 8× to 16×.")
        self.assertEqual(len(k13["retired_tests"]), 4)
        self.assertTrue(k13["why_other_crate"].startswith("The shell stops"))
        self.assertEqual([r["dependency"] for r in kept["21"]["rows"]], [False, False])
        self.assertEqual(kept["21"]["retired_tests"], [])
        self.assertIsNone(kept["21"]["why_other_crate"])

    def test_rerunning_rewrites_the_same_files(self):
        c = Converted()
        before = {n: c.read(n) for n in ms.OUTPUTS}
        ms.write_seed(M2F, PILOT, c.out, test_index=TEST_INDEX)
        self.assertEqual({n: c.read(n) for n in ms.OUTPUTS}, before)


class CheckTest(unittest.TestCase):
    def test_the_converted_files_pass_with_a_warning_for_placeholder_tiers(self):
        problems, warnings, summary = Converted().check()
        self.assertEqual(problems, [])
        self.assertEqual(len([w for w in warnings if "placeholder" in w]), 1)
        self.assertTrue(any("2 changes" in s for s in summary))

    def test_rated_tiers_draw_no_warning(self):
        problems, warnings, _ = Converted(salience={"CLX-1302": "high", "CLX-2102": "low"}).check()
        self.assertEqual(problems, [])
        self.assertFalse(any("placeholder" in w for w in warnings))

    def edited(self, name, old, new, pilot=PILOT):
        c = Converted()
        text = c.read(name)
        self.assertIn(old, text)
        (c.out / name).write_text(text.replace(old, new), encoding="utf-8")
        return c.check(pilot)[0]

    def test_an_introduces_line_that_misses_a_row(self):
        problems = self.edited("change-script.md", "**Introduces:** CLX-1301, CLX-1302.", "**Introduces:** CLX-1301.")
        self.assertTrue(any("change 13" in p and "introduces" in p for p in problems), problems)

    def test_a_missing_repair_report(self):
        problems = self.edited("repair-reports.json", '"DEP-13"', '"DEP-99"')
        self.assertTrue(any("DEP-13" in p for p in problems), problems)

    def test_a_recall_line_naming_an_identifier(self):
        problems = self.edited("owner-items.json", "just like before.", "just like CLX-1301.")
        self.assertTrue(any("identifier" in p for p in problems), problems)

    def test_a_fork_that_releases_another_changes_row(self):
        problems = self.edited("oracle.md", "| Askable | Change 21 |", "| Askable | Change 13 |")
        self.assertTrue(any("change 13" in p and "releases" in p for p in problems), problems)

    def test_a_kept_record_without_its_dependency_row(self):
        problems = self.edited("kept-behaviour.json", '"dependency": true', '"dependency": false')
        self.assertTrue(any("dependency" in p and "13" in p for p in problems), problems)

    def test_files_out_of_date_with_the_source(self):
        problems = self.edited("change-script.md", "go up to 16×?", "go up to 32×?")
        self.assertTrue(any("out of date" in p for p in problems), problems)

    def test_the_dependency_row_cites_what_its_brief_must_cite(self):
        c = Converted()
        good = {"changes": [{"n": 13, "type": "core-change-ui-depends", "must_cite": ["SIM-ENG-024", "TUI-NAV-028"]},
                            {"n": 21, "type": "control", "must_cite": ["SIM-ECO-006"]}]}
        bad = {"changes": [{"n": 13, "type": "core-change-ui-depends", "must_cite": ["SIM-ENG-016", "TUI-NAV-028"]}]}
        ok = ms.check_seed(c.out, M2F, PILOT, test_index=TEST_INDEX, expected=EXPECTED, briefs=good)[0]
        self.assertEqual(ok, [])
        problems = ms.check_seed(c.out, M2F, PILOT, test_index=TEST_INDEX, expected=EXPECTED, briefs=bad)[0]
        self.assertTrue(any("CLXK-1301" in p and "SIM-ENG-016" in p for p in problems), problems)

    def test_counts_that_differ_from_the_expected(self):
        c = Converted()
        problems = ms.check_seed(c.out, M2F, PILOT, test_index=TEST_INDEX,
                                 expected=ms.Expected(changes=(13, 21), core=(13,), rows=5, stated=2, askable=3))[0]
        self.assertTrue(any("rows" in p for p in problems), problems)


class RunForkLoadsTest(unittest.TestCase):
    def test_run_fork_runs_a_change_from_the_converted_files_with_an_owner_holding_that_change_only(self):
        import run_fork as rf
        from test_run_fork import Docker
        from test_simulator import FakeAsk, out
        from test_trajectory import FakeTurns, FakeWorkspace

        c = Converted()
        root = Path(tempfile.mkdtemp())
        (root / "brief.md").write_text("# Clowder\n\nA cozy incremental.")
        variants = root / "variants"
        variants.mkdir()
        (variants / "manifest.json").write_text(json.dumps({
            "source_commit": "86db995", "seed": "v1",
            "variants": {"plain": {"commit": "c0ffee", "volume": "ce-cv-v1-plain", "vcs": "git"}}}))
        ws, ask = FakeWorkspace(), FakeAsk(out("completion"), out("completion"))
        deps = rf.Deps(docker=Docker(), turn_for=lambda s: FakeTurns(ws, ("Done.", None, ["src/lib.rs"])),
                       workspace_for=lambda image, volume: ws, ask=ask, touch=ask.touch, trim=None,
                       install_lid=lambda *a: None)
        argv = ["--variants", str(variants), "--variant", "plain", "--arm", "bare", "--change", "21", "--repeat", "1",
                "--replicate", "r1", "--window", "200k", "--seed-dir", str(root), "--runs", str(root / "runs"),
                "--brief", str(root / "brief.md"), "--oracle", str(c.out / "oracle.md"),
                "--change-script", str(c.out / "change-script.md"), "--owner-items", str(c.out / "owner-items.json")]
        self.assertEqual(rf.main(argv, deps=deps), 0)
        prompt = ask.prompts[0]
        for present in ("[CLX-2101]", "[CLX-2102] (Askable; in play for this change)", "[CLW-001]", "sliver of room"):
            self.assertIn(present, prompt)
        for absent in ("[CLX-1301]", "[CLX-1302]", "16×"):
            self.assertNotIn(absent, prompt)


class CliTest(unittest.TestCase):
    def files(self):
        d = Path(tempfile.mkdtemp())
        (d / "m2f.md").write_text(M2F, encoding="utf-8")
        (d / "oracle.md").write_text(PILOT, encoding="utf-8")
        (d / "index.json").write_text(json.dumps(TEST_INDEX))
        return d, ["--source", str(d / "m2f.md"), "--pilot-oracle", str(d / "oracle.md"), "--test-index",
                   str(d / "index.json"), "--out", str(d / "m2f")]

    def test_it_writes_and_with_check_validates(self):
        d, argv = self.files()
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(build_m2f_seed.main(argv), 0)
        self.assertTrue((d / "m2f" / "oracle.md").exists())
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = build_m2f_seed.main([*argv, "--check"], expected=EXPECTED)
        self.assertEqual(code, 0, buf.getvalue())
        self.assertIn("WARNING", buf.getvalue())
        self.assertNotIn("PROBLEM", buf.getvalue())

    def test_check_fails_on_a_problem(self):
        d, argv = self.files()
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = build_m2f_seed.main([*argv, "--check"])  # the real counts: twelve changes, thirty rows
        self.assertEqual(code, 1)
        self.assertIn("PROBLEM", buf.getvalue())


class RealSourceTest(unittest.TestCase):
    def test_the_real_change_set_converts_and_checks(self):
        source = ms.HIDDEN / "m2f-changes-r2.md"
        pilot = ms.HIDDEN / "oracle.md"
        if not source.exists():
            self.skipTest("no m2f-changes-r2.md")
        text, pilot_text = source.read_text(encoding="utf-8"), pilot.read_text(encoding="utf-8")
        index = json.loads(ms.TEST_INDEX.read_text(encoding="utf-8"))
        changes = ms.parse_m2f(text, test_index=index)
        self.assertEqual(sorted(changes), list(range(13, 25)))
        rows = [r for c in changes.values() for r in c.rows]
        self.assertEqual(len(rows), 30)
        self.assertEqual(sum(r.kind == "Stated" for r in rows), 14)
        self.assertEqual(sum(r.kind == "Askable" for r in rows), 16)
        for n in range(13, 21):
            self.assertEqual([k.dependency for k in changes[n].keep][:1], [True], n)
            self.assertEqual(changes[n].keep[0].id, f"CLXK-{n}01")
            self.assertIn("Dependency", changes[n].reports)
        for n in range(21, 25):
            self.assertFalse(any(k.dependency for k in changes[n].keep), n)
        out = Path(tempfile.mkdtemp())
        ms.write_seed(text, pilot_text, out, test_index=index)
        briefs = json.loads(ms.BRIEFS.read_text(encoding="utf-8")) if ms.BRIEFS.exists() else None
        problems, warnings, _ = ms.check_seed(out, text, pilot_text, test_index=index, briefs=briefs)
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
