"""costeval/intent_recall.py: what a fresh reader can recover of a system's intent from its tests (or docs).

Collecting the input, stripping spec-ID pointers, the neutral variant, the size cap, the oracle at a change, the
reader's and the judge's checks, scoring, and the retired-intent extraction from a spec file's history.
"""

from __future__ import annotations

import ast
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from costeval import intent_recall as ir  # noqa: E402
from costeval import simulator  # noqa: E402
import clowder_variants as cv  # noqa: E402

PY_TEST = '''"""Loans and reservations (LOAN-REC-001 .. LOAN-REC-003)."""
import pytest

from helpers import lend


# @spec LOAN-REC-001
def test_lending_makes_one_record(client):
    """A loan makes one open record. @spec LOAN-REC-001"""
    r = lend(client)  # the plain path, see LOAN-REC-002
    assert r.status_code == 201
    assert r.json()["status"] == "open", "a loan is open at once"


class TestReservations:
    # @spec LOAN-REC-002, LOAN-REC-003
    def test_reservation_lasts_three_days(self, client):
        url = "http://x/#frag"  # not a comment inside the string
        assert reserve(client)["days"] == 3
'''

RS_SRC = '''pub fn add(a: u32, b: u32) -> u32 {
    a + b // "not a string"
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Adding never loses a kitten.
    /// @spec SIM-KIT-001
    #[test]
    fn adding_keeps_every_kitten() {
        let s = "// not a comment"; // a real comment
        assert_eq!(add(1, 2), 3, "one plus two");
    }
}
'''

RS_TESTS = '''use clowder_core::*;

/* A block comment /* nested */ still a comment */

/// The theme paints no background.
/// @spec TUI-THEME-001
#[test]
fn frame_paints_no_background() {
    assert!(paint().bg_is_reset());
}

/// Coats never vary with stock.
/// @spec TUI-THEME-003,
/// TUI-THEME-004
#[test]
#[should_panic(expected = "no // coat change")]
fn coat_ignores_stock() {
    let c = coat('a'); // the lifetime-free char literal
    panic!("no // coat change");
}

/// Kittens wake at dawn.
/// @spec SIM-KIT-002
#[test]
fn kittens_wake() {
    assert!(true);
}
'''

SPECS = """---
prefix: TUI-THEME
---

# Theme Specs (TUI-THEME)

- [x] **TUI-THEME-001**: The system shall paint no background of its own.
- [ ] **TUI-THEME-002**: The system shall keep every colour mid-luminance.
- [D] **TUI-THEME-005**: The system shall render mood with no colour.
- [x] **TUI-THEME-003**: The system shall give each resource a coat that never varies with its stock (TUI-THEME-004).
"""

ORACLE = """# Oracle

## Owner narrative

### What the owner knows from the start

Loans.

## Item table

| ID | Checkable behavior | Disclosure kind | In force | Retired | External check sketch |
|---|---|---|---|---|---|
| LN-01 | A book on loan can't be lent to a second member. | Stated at start | Start | — | sketch |
| LN-02 | Late returns are never fined. | Stated at start | Start | Change 2 | sketch |
| LN-03 | A reserved book is held for three days. Graded under LN-01 when both apply. | Askable | Start | — | sketch |
| LN-04 | A damaged book is checked before it is lent again. | Recognized on sight | Start | — | sketch |
| LN-05 | Returns more than a week late are fined. | Stated in change 2 | Change 2 | — | sketch |
| LN-06 | Dropped: only an interface detail. | Dropped | — | — | Not graded. |
| LN-07 | Renewals extend a loan by two weeks. | Stated in change 8 | Change 8 | — | sketch |
| LN-08 | A return is accepted after the member's card expires. | Realized on symptom | Change 5 | — | sketch |
| LN-09 | Reservations lapse after three days from change 3 onward. | Emerging at change 3 | Change 3 | — | sketch |

## Recognized-on-sight responses

- **LN-04**, shown a damaged book going straight back out:
  **"No, someone has to look at it first."**
"""

SCRIPT = """# Change script

## Change 2 — Late fines

### Initial owner request

> Start fining every late return.

### Early redirect: change of mind

> I've changed my mind. Only returns more than a week late are fined.

**Redirect introduces:** LN-05.

**Introduces:** LN-05.
**Retires:** LN-02.

## Change 3 — Reservations

### Owner request

> Reservations.

### Late redirect: clarification

> By three days I mean from when it's ready.

**Introduces:** LN-09.

## Change 5 — Returns

### Owner symptom report

> A return was refused.

**Introduces:** LN-08.

## Change 8 — Renewals

### Owner request

> Let members renew.

**Introduces:** LN-07.
"""


class SelectTest(unittest.TestCase):
    FILES = {
        "README.md": "# App\n",
        "AGENTS.md": "agent rules",
        "CLAUDE.md": "agent rules",
        "NOTES.md": "decisions",
        "docs/intent/loans/loans-specs.md": "- [x] **LOAN-REC-001**: x",
        ".claude/settings.md": "x",
        "app/main.py": "print()",
        "app/test_inline.py": "def test_x(): pass",
        "tests/test_api.py": "def test_y(): pass",
        "tests/conftest.py": "import pytest",
        "tests/fixtures/data.json": "{}",
        "tests/README.md": "how to run the tests",
        ".venv/lib/site-packages/x/tests/test_z.py": "def test_z(): pass",
        "pkg.egg-info/SOURCES.txt": "x",
        "crates/core/src/lib.rs": RS_SRC,
        "crates/core/src/plain.rs": "pub fn f() {}\n",
        "crates/core/tests/integration/main.rs": "mod a;",
    }

    def test_tests_are_test_dirs_and_test_files_and_cfg_test_blocks(self):
        got = {f.path: f for f in ir.select_tests(self.FILES)}
        self.assertEqual(sorted(got), ["app/test_inline.py", "crates/core/src/lib.rs",
                                       "crates/core/tests/integration/main.rs", "tests/README.md",
                                       "tests/conftest.py", "tests/fixtures/data.json", "tests/test_api.py"])
        lib = got["crates/core/src/lib.rs"]
        self.assertTrue(lib.text.startswith("#[cfg(test)]\nmod tests {"))
        self.assertTrue(lib.text.rstrip().endswith("}"))
        self.assertNotIn("pub fn add", lib.text)
        self.assertIn("#[cfg(test)]", lib.note)

    def test_docs_are_prose_outside_tests_without_agent_instruction_files(self):
        got = [f.path for f in ir.select_docs(self.FILES)]
        self.assertEqual(got, ["NOTES.md", "README.md", "docs/intent/loans/loans-specs.md"])

    def test_cfg_test_blocks_end_at_their_item_skipping_braces_in_strings(self):
        blocks = ir.cfg_test_blocks(RS_SRC)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].count("{"), blocks[0].count("}"))


class SegmentTestsTest(unittest.TestCase):
    def test_a_segment_takes_the_test_functions_citing_its_specs(self):
        files = {"crates/tui/tests/theme.rs": RS_TESTS, "crates/core/src/lib.rs": RS_SRC}
        got = ir.segment_tests(files, {"TUI-THEME-001", "TUI-THEME-004"})
        self.assertEqual([f.path for f in got], ["crates/tui/tests/theme.rs"])
        text = got[0].text
        self.assertIn("fn frame_paints_no_background", text)
        self.assertIn("fn coat_ignores_stock", text)  # its citation wraps to the next doc line
        self.assertIn("#[should_panic", text)
        self.assertNotIn("kittens_wake", text)
        self.assertIn("/// The theme paints no background.", text)
        kit = ir.segment_tests(files, {"SIM-KIT-001"})
        self.assertEqual([f.path for f in kit], ["crates/core/src/lib.rs"])
        self.assertIn("fn adding_keeps_every_kitten", kit[0].text)

    def test_spec_citations_read_wrapped_annotations(self):
        self.assertEqual(ir.spec_citations("/// @spec A-B-001,\n/// A-B-002 and A-C-010\nfn f() {}"),
                         {"A-B-001", "A-B-002", "A-C-010"})
        self.assertEqual(ir.spec_citations("/// See A-B-001.\nfn f() {}"), set())

    def test_spec_items_are_the_implemented_lines(self):
        items = ir.spec_items(SPECS)
        self.assertEqual([i.id for i in items], ["TUI-THEME-001", "TUI-THEME-003"])
        self.assertEqual(items[0].text, "The system shall paint no background of its own.")
        self.assertTrue(all(i.status == "in force" for i in items))
        self.assertEqual(ir.spec_ids(SPECS), {"TUI-THEME-001", "TUI-THEME-002", "TUI-THEME-003", "TUI-THEME-005"})


class StripTest(unittest.TestCase):
    def setUp(self):
        self.files = {"docs/intent/loans/loans-specs.md": "- [x] **LOAN-REC-001**: a\n- [x] **LOAN-REC-002**: b\n"
                                                         "- [x] **LOAN-REC-003**: c\n", "tests/test_x.py": PY_TEST}
        self.pattern = ir.pointer_pattern(self.files)

    def test_the_pattern_comes_from_the_specs_and_the_annotations(self):
        p = ir.pointer_pattern({"t.py": "# @spec LAB-CAL-01\n"})
        self.assertTrue(p.search("LAB-CAL-07"))
        self.assertTrue(self.pattern.search("LOAN-REC-009"))
        self.assertIsNone(self.pattern.search("ISO-8601"))
        self.assertIsNone(ir.pointer_pattern({"a.py": "x = 1"}).search("LOAN-REC-001"))

    def test_python_annotations_and_citations_go_and_the_test_stays(self):
        out, counts = ir.strip_pointers([ir.InputFile("tests/test_x.py", PY_TEST)], self.pattern)
        text = out[0].text
        self.assertIsNone(self.pattern.search(text))
        self.assertNotIn("@spec", text)
        self.assertIn('"""A loan makes one open record."""', text)
        self.assertIn("r = lend(client) # the plain path", text)
        self.assertIn('"""Loans and reservations."""', text)
        self.assertIn("def test_lending_makes_one_record(client):", text)
        self.assertIn('assert r.json()["status"] == "open", "a loan is open at once"', text)
        self.assertGreaterEqual(counts["annotation lines"], 2)
        ast.parse(text)

    def test_rust_annotations_go(self):
        p = re.compile(r"\b(?:TUI-THEME|SIM-KIT)-\d{3}\b")
        out, _ = ir.strip_pointers([ir.InputFile("crates/tui/tests/theme.rs", RS_TESTS)], p)
        self.assertNotIn("@spec", out[0].text)
        self.assertIn("/// The theme paints no background.\n#[test]", out[0].text)

    def test_markdown_spec_labels_leave_no_empty_bold(self):
        out, _ = ir.strip_pointers([ir.InputFile("docs/intent/loans/loans-specs.md", self.files["docs/intent/loans/loans-specs.md"])],
                                   self.pattern)
        self.assertEqual(out[0].text, "- [x] a\n- [x] b\n- [x] c\n")


class NeutralTest(unittest.TestCase):
    def test_python_names_comments_and_docstrings_become_placeholders(self):
        out, counts = ir.neutralize_python(PY_TEST)
        ast.parse(out)
        for gone in ("lending_makes_one_record", "reservation_lasts_three_days", "TestReservations", "A loan makes one",
                     "the plain path", "Loans and reservations", "@spec LOAN-REC-002"):
            self.assertNotIn(gone, out)
        self.assertIn("def test_case_001(client):", out)
        self.assertIn("def test_case_002(self, client):", out)
        self.assertIn("class TestGroup01:", out)
        self.assertIn('assert r.json()["status"] == "open", "a loan is open at once"', out)
        self.assertIn('url = "http://x/#frag"  # …', out)
        self.assertIn("r = lend(client)", out)
        self.assertEqual(counts, {"test names": 3, "comments": 4, "docstrings": 2})

    def test_rust_names_and_comments_become_placeholders_and_strings_stay(self):
        out, counts = ir.neutralize_rust(RS_TESTS)
        for gone in ("frame_paints_no_background", "coat_ignores_stock", "kittens_wake", "paints no background",
                     "nested", "lifetime-free"):
            self.assertNotIn(gone, out)
        self.assertIn("fn test_case_001()", out)
        self.assertIn("fn test_case_003()", out)
        self.assertIn('#[should_panic(expected = "no // coat change")]', out)
        self.assertIn('panic!("no // coat change");', out)
        self.assertIn("let c = coat('a'); // …", out)
        self.assertIn("/* … */", out)
        self.assertEqual(counts["test names"], 3)
        out2, _ = ir.neutralize_rust(RS_SRC)
        self.assertIn('a + b // …', out2)
        self.assertIn('let s = "// not a comment"; // …', out2)
        self.assertIn('assert_eq!(add(1, 2), 3, "one plus two");', out2)

    def test_neutralize_dispatches_by_language_and_leaves_other_files(self):
        files = [ir.InputFile("tests/test_x.py", PY_TEST), ir.InputFile("tests/t.rs", RS_TESTS),
                 ir.InputFile("tests/fixtures/data.json", '{"a": "# b"}')]
        out, counts = ir.neutralize(files)
        self.assertIn("test_case_001", out[0].text)
        self.assertIn("test_case_001", out[1].text)
        self.assertEqual(out[2].text, '{"a": "# b"}')
        self.assertEqual(counts["test names"], 6)


class SizeTest(unittest.TestCase):
    def test_an_input_over_the_cap_is_refused_whole(self):
        with self.assertRaises(ir.TooLarge) as e:
            ir.check_size("x" * 4001, cap=1000)
        self.assertIn("1,001", str(e.exception))
        self.assertIn("scope it down", str(e.exception))
        self.assertEqual(ir.check_size("x" * 4000, cap=1000), 1000)

    def test_rendered_files_keep_every_byte_and_fence_safely(self):
        text = "a\n```\nb\n"
        out = ir.render_files([ir.InputFile("README.md", text, "note")])
        self.assertIn("## README.md (note)", out)
        self.assertIn("````", out)
        self.assertIn(text, out)


class BenchtimeOracleTest(unittest.TestCase):
    def setUp(self):
        self.items = ir.benchtime_oracle(simulator.parse_oracle(ORACLE), simulator.parse_change_script(SCRIPT), 5)
        self.by = {i.id: i for i in self.items}

    def test_in_force_retired_and_superseded_at_a_change(self):
        self.assertEqual(sorted(i.id for i in self.items if i.status == "in force"),
                         ["LN-01", "LN-03", "LN-04", "LN-05", "LN-08", "LN-09"])
        self.assertEqual(sorted(i.id for i in self.items if i.status == "retired"), ["LN-02", "SUP-02"])
        self.assertNotIn("LN-06", self.by)  # dropped: never the owner's intent
        self.assertNotIn("LN-07", self.by)  # not yet introduced

    def test_groups_follow_disclosure(self):
        self.assertEqual({i: self.by[i].group for i in ("LN-01", "LN-03", "LN-04", "LN-05", "LN-08", "LN-09")},
                         {"LN-01": "stated", "LN-03": "latent", "LN-04": "latent", "LN-05": "stated",
                          "LN-08": "symptom", "LN-09": "stated"})

    def test_item_text_drops_graders_notes_and_change_numbers(self):
        self.assertEqual(self.by["LN-03"].text, "A reserved book is held for three days.")
        self.assertEqual(self.by["LN-09"].text, "Reservations lapse after three days.")

    def test_a_change_of_mind_supersedes_the_first_request_and_a_clarification_does_not(self):
        sup = self.by["SUP-02"]
        self.assertIn("Start fining every late return", sup.text)
        self.assertIn("Only returns more than a week late are fined", sup.text)
        self.assertFalse(any(i.id.startswith("SUP-03") for i in self.items))

    def test_the_oracle_render_shows_ids_and_text_not_disclosure(self):
        out = ir.render_oracle(self.items)
        self.assertIn("[LN-01] A book on loan can't be lent to a second member.", out)
        self.assertNotIn("Askable", out)
        self.assertLess(out.index("[LN-09]"), out.index("[LN-02]"))


RULES = [{"rule": "Two members can never hold the same book on loan at once.", "evidence": ["tests/test_x.py::test_a"]},
         {"rule": "Every late return is fined.", "evidence": ["tests/test_x.py"]},
         {"rule": "A book on loan may go to a second member if a librarian approves.", "evidence": ["tests/test_x.py"]},
         {"rule": "The API returns HTTP 409 for refusals.", "evidence": ["tests/test_x.py"]}]


def mapping(n, cls, items=(), quotes=None, extent=None, reason="The rule says the same thing as the item does.",
            rule_quote=None):
    rule = RULES[n - 1]["rule"]
    return {"rule": n, "classification": cls, "items": list(items),
            "extent": extent or ("whole" if cls == "agrees" else "none"),
            "rule_quote": rule_quote if rule_quote is not None else rule.split()[0] + " " + rule.split()[1],
            "item_quotes": quotes if quotes is not None else [], "reason": reason}


class JudgeCheckTest(unittest.TestCase):
    def setUp(self):
        self.items = ir.benchtime_oracle(simulator.parse_oracle(ORACLE), simulator.parse_change_script(SCRIPT), 5)
        self.good = {"mappings": [
            mapping(1, "agrees", ["LN-01"], [{"item": "LN-01", "quote": "can't be lent to a second member"}]),
            mapping(2, "stale", ["SUP-02"], [{"item": "SUP-02", "quote": "Start fining every late return"}]),
            mapping(3, "contradicts", ["LN-01"], [{"item": "LN-01", "quote": "can’t be lent"}]),
            mapping(4, "incidental")]}

    def problems(self, answer, numbers=(1, 2, 3, 4)):
        return ir.check_mappings(answer, list(numbers), RULES, self.items)

    def test_a_good_answer_passes(self):
        self.assertEqual(self.problems(self.good), [])

    def test_every_rule_once_and_no_others(self):
        bad = {"mappings": self.good["mappings"][:3] + [mapping(1, "incidental"), dict(mapping(4, "incidental"), rule=9)]}
        got = " ".join(p for _, p in self.problems(bad))
        self.assertIn("rule 4", got)
        self.assertIn("two mappings for rule 1", got)
        self.assertIn("rule 9", got)

    def test_reasons_need_five_words(self):
        bad = {"mappings": [dict(m, reason="Same.") if m["rule"] == 1 else m for m in self.good["mappings"]]}
        self.assertEqual([r for r, _ in self.problems(bad)], [1])

    def test_ids_must_exist_and_fit_the_class(self):
        cases = [
            mapping(1, "agrees", ["LN-99"], [{"item": "LN-99", "quote": "x"}]),
            mapping(1, "agrees", ["LN-02"], [{"item": "LN-02", "quote": "Late returns are"}]),  # retired
            mapping(1, "stale", ["LN-01"], [{"item": "LN-01", "quote": "A book on loan"}]),  # in force
            mapping(1, "agrees", [], []),
            mapping(1, "incidental", ["LN-01"], [{"item": "LN-01", "quote": "A book on loan"}]),
            mapping(1, "agrees", ["LN-07"], [{"item": "LN-07", "quote": "Renewals extend"}]),  # not in this oracle
        ]
        for m in cases:
            answer = {"mappings": [m] + self.good["mappings"][1:]}
            self.assertEqual([r for r, _ in self.problems(answer)], [1], m)

    def test_quotes_must_be_found_in_the_rule_and_the_item(self):
        bad_item = mapping(1, "agrees", ["LN-01"], [{"item": "LN-01", "quote": "members share books"}])
        bad_rule = mapping(1, "agrees", ["LN-01"], [{"item": "LN-01", "quote": "can't be lent"}], rule_quote="never collide")
        no_quote = mapping(1, "agrees", ["LN-01"], [])
        for m in (bad_item, bad_rule, no_quote):
            self.assertEqual([r for r, _ in self.problems({"mappings": [m] + self.good["mappings"][1:]})], [1])
        elided = mapping(1, "agrees", ["LN-01"], [{"item": "LN-01", "quote": "A book ... can't be lent"}])
        self.assertEqual(self.problems({"mappings": [elided] + self.good["mappings"][1:]}), [])

    def test_extent_is_for_agreement_only(self):
        m = dict(self.good["mappings"][0], extent="none")
        self.assertEqual([r for r, _ in self.problems({"mappings": [m] + self.good["mappings"][1:]})], [1])
        m = dict(self.good["mappings"][3], extent="part")
        self.assertEqual([r for r, _ in self.problems({"mappings": self.good["mappings"][:3] + [m]})], [4])

    def test_judge_keeps_each_rules_latest_valid_mapping_and_marks_the_rest_unjudged(self):
        broken = {"mappings": [dict(m, reason="No.") if m["rule"] in (1, 2) else m for m in self.good["mappings"]]}
        fixed_one = {"mappings": [dict(m, reason="No.") if m["rule"] == 2 else m for m in self.good["mappings"]]}
        answers = iter([broken, fixed_one, broken])
        prompts = []

        def ask(prompt, schema):
            prompts.append(prompt)
            return next(answers), {"cost_usd": 0.5}
        out = ir.judge(RULES, self.items, ask=ask, attempts=3)
        self.assertNotIn("earlier answer", prompts[0])
        self.assertIn("rule 1: a reason too short", prompts[1])  # a retry names the problems to avoid
        self.assertIn("rule 2: a reason too short", prompts[2])
        self.assertEqual(sorted(out["mappings"]), [1, 3, 4])
        self.assertEqual(out["unjudged"], [2])
        self.assertEqual(out["cost_usd"], 1.5)
        self.assertEqual(len(out["batches"][0]["tries"]), 3)

    def test_judge_batches_rules_and_numbers_them_globally(self):
        prompts = []

        def ask(prompt, schema):
            prompts.append(prompt)
            nums = [int(n) for n in re.findall(r"(?m)^R(\d+)\.", prompt)]
            return {"mappings": [mapping(n, "incidental") for n in nums]}, {"cost_usd": 0.1}
        out = ir.judge(RULES, self.items, ask=ask, batch_size=3)
        self.assertEqual(len(prompts), 2)
        self.assertIn("R4.", prompts[1])
        self.assertEqual(sorted(out["mappings"]), [1, 2, 3, 4])


class ReaderCheckTest(unittest.TestCase):
    INPUTS = [ir.InputFile("tests/test_x.py", "def test_a():\n    pass\n"), ir.InputFile("docs/a.md", "# Heading\n")]

    def test_rules_need_words_and_citations_of_given_files_and_tests(self):
        answer = {"rules": [
            {"rule": "A book never goes to two members at once.", "evidence": ["tests/test_x.py::test_a"]},
            {"rule": "Reservations lapse after three days.", "evidence": ["docs/a.md § Heading", "tests/test_x.py::test_zz"]},
            {"rule": "Guessed rule with no basis here.", "evidence": ["src/app.py"]},
            {"rule": "Short.", "evidence": ["docs/a.md"]}]}
        rules, problems = ir.check_reader(answer, self.INPUTS)
        self.assertEqual([r["rule"] for r in rules], ["A book never goes to two members at once.",
                                                      "Reservations lapse after three days."])
        self.assertEqual(rules[1]["evidence"], ["docs/a.md § Heading"])  # the unknown test is dropped
        self.assertEqual(rules[1]["dropped_evidence"], ["tests/test_x.py::test_zz"])
        joined = " ".join(problems)
        for bit in ("test_zz", "src/app.py", "Short."):
            self.assertIn(bit, joined)

    def test_no_rules_is_a_problem(self):
        self.assertEqual(ir.check_reader({"rules": []}, self.INPUTS)[1], ["no rules"])


class ScoreTest(unittest.TestCase):
    def setUp(self):
        self.items = ir.benchtime_oracle(simulator.parse_oracle(ORACLE), simulator.parse_change_script(SCRIPT), 5)
        self.mappings = {
            1: {"classification": "agrees", "items": ["LN-01", "LN-03"], "extent": "part"},
            2: {"classification": "stale", "items": ["SUP-02"], "extent": "none"},
            3: {"classification": "contradicts", "items": ["LN-04"], "extent": "none"},
            4: {"classification": "incidental", "items": [], "extent": "none"},
            5: {"classification": "agrees", "items": ["LN-01"], "extent": "whole"},
            6: {"classification": "stale", "items": ["SUP-02"], "extent": "none"},
        }

    def test_recall_rates_and_stale_per_retired_item(self):
        s = ir.score(7, self.mappings, self.items, met={"LN-01", "LN-04", "LN-05"})
        self.assertEqual(s["rules"], 7)
        self.assertEqual(s["judged"], 6)
        self.assertEqual(s["counts"], {"agrees": 2, "contradicts": 1, "stale": 2, "incidental": 1})
        self.assertAlmostEqual(s["rates_per_rule"]["incidental"], 1 / 6)
        self.assertEqual(s["in_force"], 6)
        self.assertEqual(s["recovered"], ["LN-01", "LN-03"])
        self.assertAlmostEqual(s["recall"], 2 / 6)
        self.assertEqual(s["recovered_whole"], ["LN-01"])
        self.assertEqual(s["by_group"]["stated"], {"of": 3, "recovered": 1, "recall": 1 / 3})
        self.assertEqual(s["by_group"]["latent"], {"of": 2, "recovered": 1, "recall": 0.5})
        self.assertEqual(s["met"], 3)
        self.assertAlmostEqual(s["recall_of_met"], 1 / 3)
        self.assertEqual(s["by_group_of_met"]["latent"], {"of": 1, "recovered": 0, "recall": 0.0})
        self.assertEqual(s["contradicted"], ["LN-04"])
        self.assertEqual(s["contradicted_met"], ["LN-04"])  # the build meets it: the rule misleads
        self.assertEqual(s["contradicted_unmet"], [])
        self.assertEqual(s["contradicting_rules"]["against_met"], 1)
        self.assertAlmostEqual(s["contradicting_rules"]["against_met_per_rule"], 1 / 6)
        unmet = ir.score(7, self.mappings, self.items, met={"LN-01"})
        self.assertEqual(unmet["contradicted_unmet"], ["LN-04"])  # the build fails it: the rule may record the defect
        self.assertEqual(unmet["contradicting_rules"]["against_unmet_only"], 1)
        self.assertEqual(s["retired"], 2)
        self.assertEqual(s["stale_items"], ["SUP-02"])
        self.assertAlmostEqual(s["stale_items_share"], 0.5)
        self.assertAlmostEqual(s["stale_rules_per_retired_item"], 1.0)

    def test_without_a_met_set_recall_of_met_is_absent(self):
        s = ir.score(6, self.mappings, self.items)
        self.assertIsNone(s["recall_of_met"])

    def test_repeats_summarize_as_mean_and_spread(self):
        a = ir.score(6, self.mappings, self.items)
        b = ir.score(6, {1: self.mappings[1]}, self.items)
        out = ir.summarize_repeats([a, b])
        self.assertAlmostEqual(out["recall"]["mean"], (2 / 6 + 2 / 6) / 2)
        self.assertAlmostEqual(out["rates_per_rule.incidental"]["max"], 1 / 6)
        self.assertAlmostEqual(out["rates_per_rule.incidental"]["min"], 0.0)
        self.assertEqual(out["repeats"], 2)

    def test_recall_against_a_met_set_for_a_baseline(self):
        self.assertAlmostEqual(ir.recall_against(["LN-01", "LN-03"], {"LN-01", "LN-04"}), 0.5)
        self.assertIsNone(ir.recall_against(["LN-01"], set()))


LOG = """COMMIT bbb 2026-02-01
diff --git a/docs/intent/tui/theme/theme-specs.md b/docs/intent/tui/theme/theme-specs.md
--- a/docs/intent/tui/theme/theme-specs.md
+++ b/docs/intent/tui/theme/theme-specs.md
@@ -1,3 +1,3 @@
-- [ ] **TUI-THEME-003**: The system shall give each resource a coat that never varies with its stock (TUI-THEME-004).
+- [x] **TUI-THEME-003**: The system shall give each resource a coat that never varies with its stock (TUI-THEME-004).
-- [x] **TUI-THEME-001**: The system shall paint a dark background.
+- [x] **TUI-THEME-001**: The system shall paint no background of its own.
COMMIT aaa 2026-01-01
@@ -1,1 +1,1 @@
-- [x] **TUI-THEME-001**: The system shall paint a dark background.
+- [x] **TUI-THEME-001**: The system shall paint a dark background.
-- [x] **TUI-THEME-001**: The system shall paint a black background.
"""


class RetiredTest(unittest.TestCase):
    def test_removed_lines_become_candidates_unless_a_current_line_says_the_same(self):
        removed = ir.removed_spec_lines(LOG)
        self.assertEqual(len(removed), 4)
        cands = ir.retired_candidates(removed, SPECS)
        self.assertEqual([(c["id"], c["text"]) for c in cands],
                         [("TUI-THEME-001", "The system shall paint a dark background."),
                          ("TUI-THEME-001", "The system shall paint a black background.")])
        self.assertEqual(cands[0]["commits"], ["bbb", "aaa"])
        self.assertEqual([c["n"] for c in cands], [1, 2])

    def test_the_extraction_check(self):
        cands = ir.retired_candidates(ir.removed_spec_lines(LOG), SPECS)
        good = {"candidates": [
            {"candidate": 1, "verdict": "retired", "current": ["TUI-THEME-001"], "retired_claim":
             "The game paints a dark background behind everything.", "quote": "paint a dark background",
             "duplicate_of": 0, "reason": "The current spec paints no background at all."},
            {"candidate": 2, "verdict": "retired", "current": ["TUI-THEME-001"], "retired_claim":
             "The game paints a black background behind everything.", "quote": "black background",
             "duplicate_of": 1, "reason": "Same retired claim as the first, a dark ground."}]}
        self.assertEqual(ir.check_retired(good, cands, ir.spec_ids(SPECS)), [])
        bad = json.loads(json.dumps(good))
        bad["candidates"][0]["quote"] = "a light ground"
        bad["candidates"][1]["duplicate_of"] = 2
        bad["candidates"].append(dict(good["candidates"][0], candidate=3))
        got = " ".join(ir.check_retired(bad, cands, ir.spec_ids(SPECS)))
        for bit in ("candidate 1", "candidate 2", "candidate 3"):
            self.assertIn(bit, got)
        still = {"candidates": [dict(good["candidates"][0], verdict="still said", current=[]), good["candidates"][1]]}
        self.assertIn("candidate 1", " ".join(ir.check_retired(still, cands, ir.spec_ids(SPECS))))
        items = ir.retired_items(cands, good)
        self.assertEqual(len(items), 1)  # the duplicate folds into the first
        self.assertEqual(items[0].status, "retired")
        self.assertIn("dark background behind everything", items[0].text)
        self.assertIn("paint a dark background", items[0].text)


class PromptTest(unittest.TestCase):
    def test_the_reader_prompt_says_nothing_about_a_study_or_grading(self):
        p = ir.reader_prompt("tests", [ir.InputFile("tests/test_x.py", "def test_a(): pass\n")])
        self.assertIn("def test_a(): pass", p)
        for word in ("study", "oracle", "grade", "graded", "judge", "eval", "arm", "LID", "benchmark", "owner"):
            self.assertIsNone(re.search(rf"\b{word}\b", p, re.I), word)
        self.assertNotIn("placeholder", p)
        self.assertIn("placeholder", ir.reader_prompt("tests", [ir.InputFile("t.py", "x")], neutral=True))

    def test_the_judge_prompt_shows_rules_and_items_but_no_arm(self):
        items = ir.benchtime_oracle(simulator.parse_oracle(ORACLE), simulator.parse_change_script(SCRIPT), 5)
        p = ir.judge_prompt(items, [(1, RULES[0]["rule"]), (2, RULES[1]["rule"])])
        self.assertIn("R1. Two members can never hold the same book on loan at once.", p)
        self.assertIn("[SUP-02]", p)
        for word in ("bare", "cheap", "LID", "discipline", "tests"):
            self.assertIsNone(re.search(rf"\b{word}\b", p), word)


if __name__ == "__main__":
    unittest.main()
