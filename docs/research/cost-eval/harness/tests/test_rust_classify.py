"""The pre-registered classification of failing held-out tests (costeval.rust_classify): "new state only" or
"keeping failure", ruled by a judge model (stubbed here) from the failure output, a key-by-key JSON difference the
harness computes first, the test's source, and the change request.

The failures come from the adaptation fixture crate (tests/fixtures/adapt-crate), run in the Rust executor image:
saves.rs fails twice on a nickname the arm added to a kitten's saved form, and cats.rs once on a wildcard arm."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from costeval import rust_classify as rc, rust_grading as rg  # noqa: E402
from test_rust_adapt import FIX, HELD  # noqa: E402

SAVES_LOG = (FIX / "diagnostics" / "heldout_saves.test.log").read_text()
CATS_LOG = (FIX / "diagnostics" / "heldout_cats.test.log").read_text()
FILES = rg.held_out_targets(FIX / "held-out", HELD)
SAVES = {p: t for p, t in FILES.items() if "/heldout_saves/" in p}
EXACT, SHAPE = "saves::a_saved_kitten_is_exact", "saves::a_resaved_kitten_keeps_its_shape"
CHANGE = "Nicknames\n\nLet me give each kitten a nickname, and keep it when I save."

MIGRATION = """thread 'm::kittens_survive' panicked at crates/x/tests/heldout_m/m.rs:40:9:
`kittens` changed across migration: [{"age":1,"name":"Plum"},{"age":2,"name":"Fig"}] -> [{"age":1,"name":"Plum","nickname":null,"profile":{"eyes":"Blue"}},{"age":3,"name":"Fig","nickname":null,"profile":{"eyes":"Green"}}]
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
"""


class FailureOutputTest(unittest.TestCase):
    def test_each_failing_tests_output_is_read_from_cargos_log(self):
        sections = rc.failure_sections(SAVES_LOG)
        self.assertEqual(sorted(sections), [SHAPE, EXACT])
        self.assertIn("panicked at crates/fixture/tests/heldout_saves/saves.rs:11:5", sections[EXACT])
        self.assertNotIn("RUST_BACKTRACE", sections[EXACT])
        self.assertEqual(rc.panic_site(sections[EXACT]), ("crates/fixture/tests/heldout_saves/saves.rs", 11))

    def test_an_assert_eq_on_strings_holding_json_is_compared_left_and_right(self):
        left, right, a, b = rc.compared_json(rc.failure_sections(SAVES_LOG)[EXACT])
        self.assertEqual((left, right), ("left", "right"))
        self.assertEqual(a, {"name": "Fern", "age": 2, "nickname": None})
        self.assertEqual(rc.json_difference(a, b, labels=(left, right)), ["nickname: only in left: null"])

    def test_json_written_into_a_message_is_compared_in_the_order_it_appears(self):
        first, second, a, b = rc.compared_json(rc.failure_sections(SAVES_LOG)[SHAPE])
        self.assertEqual((first, second), ("first", "second"))
        self.assertEqual(rc.json_difference(a, b, labels=(first, second)), ["nickname: only in second: null"])

    def test_the_difference_walks_arrays_and_objects_key_by_key(self):
        first, second, a, b = rc.compared_json(MIGRATION)
        self.assertEqual(rc.json_difference(a, b, labels=(first, second)), [
            "[0].nickname: only in second: null",
            '[0].profile: only in second: {"eyes":"Blue"}',
            "[1].age: first 2, second 3",
            "[1].nickname: only in second: null",
            '[1].profile: only in second: {"eyes":"Green"}'])
        self.assertEqual(rc.json_difference([1], [1, 2], labels=("left", "right")),
                         ["(top): 1 item in left, 2 in right", "[1]: only in right: 2"])

    def test_serde_json_values_debug_form_is_read_as_json(self):
        out = ("thread 't' panicked at a.rs:1:1:\nassertion `left == right` failed\n"
               '  left: Object {"a": Number(1), "b": Array [String("x)"), Null], "c": Bool(true)}\n'
               ' right: Object {"a": Number(2), "b": Array [String("x)")], "c": Bool(true)}\n')
        left, right, a, b = rc.compared_json(out)
        self.assertEqual(a, {"a": 1, "b": ["x)", None], "c": True})
        self.assertEqual(rc.json_difference(a, b, labels=(left, right)),
                         ["a: left 1, right 2", "b: 2 items in left, 1 in right", "b[1]: only in left: null"])

    def test_output_without_two_json_values_gives_no_difference(self):
        self.assertIsNone(rc.compared_json("thread 't' panicked at a.rs:1:1:\nassertion `left == right` failed\n  left: 3\n right: 4\n"))
        self.assertIsNone(rc.compared_json(rc.failure_sections(CATS_LOG)["cats::every_arrival_is_described"]))


class SourceTest(unittest.TestCase):
    def test_the_test_its_failing_statements_helpers_and_their_line_numbers(self):
        site = ("crates/fixture/tests/heldout_saves/saves.rs", 18)
        entries = rc.source_entries(SAVES, SHAPE, site)
        self.assertEqual([(e["kind"], e["file"].rsplit("/", 1)[1], e["from"], e["to"]) for e in entries],
                         [("test source", "saves.rs", 14, 22), ("helper source", "saves.rs", 4, 7)])
        self.assertIn("   18  ", entries[0]["text"])
        self.assertIn("same_shape(&was, &now)", entries[0]["text"])

    def test_a_helper_in_a_module_copied_beside_the_test_is_found(self):
        entries = rc.source_entries(SAVES, EXACT, ("crates/fixture/tests/heldout_saves/saves.rs", 11))
        self.assertEqual([(e["kind"], e["file"].rsplit("/", 2)[-2:], e["from"]) for e in entries],
                         [("test source", ["heldout_saves", "saves.rs"], 9), ("helper source", ["common", "mod.rs"], 3)])

    def test_a_failure_outside_the_test_function_shows_its_site(self):
        entries = rc.source_entries(SAVES, EXACT, ("crates/fixture/tests/heldout_saves/saves.rs", 6))
        self.assertEqual([e["kind"] for e in entries][:2], ["test source", "failure site"])


def keep_result() -> dict:
    return rg.keeping_result([("fixture", "heldout_saves", SAVES_LOG), ("fixture", "heldout_cats", CATS_LOG)])


def ruling(test, cls, seq, lines, reason="The only difference is the nickname the change adds, at null."):
    return {"test": test, "classification": cls, "reason": reason, "evidence": [{"seq": seq, "lines": lines}]}


class Ask:
    """A stub judge: answers each prompt from a queue, recording what it was shown."""

    def __init__(self, *answers):
        self.answers, self.prompts = list(answers), []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        a = self.answers.pop(0)
        return (a(prompt) if callable(a) else a), {"cost_usd": 0.01}


def seqs(prompt: str) -> dict[str, dict[str, int]]:
    """Each test's entries in a prompt, by kind: their seq numbers."""
    out: dict[str, dict[str, int]] = {}
    for line in prompt.splitlines():
        if line.startswith("[seq "):
            seq = int(line.split()[1].rstrip("]"))
            test = line.split("`")[1]
            kind = line.split("`: ")[1].split(",")[0]
            out.setdefault(test, {}).setdefault(kind, seq)
    return out


def good(prompt: str) -> dict:
    s = seqs(prompt)
    return {"rulings": [ruling(EXACT, "new state only", s[EXACT]["json difference"], [1]),
                        ruling(SHAPE, "new state only", s[SHAPE]["test source"], [18, 19, 20])]}


class ClassifyTest(unittest.TestCase):
    def files(self):
        return {"heldout_saves": SAVES, "heldout_cats": {p: t for p, t in FILES.items() if "/heldout_cats/" in p}}

    def test_failures_are_ruled_with_reasons_and_evidence_and_counted_apart(self):
        r, ask = keep_result(), Ask(good)
        out = Path(tempfile.mkdtemp())
        rc.classify(r, {"heldout_saves": SAVES_LOG, "heldout_cats": CATS_LOG}, self.files(), CHANGE, ask=ask, out=out)
        self.assertEqual(len(ask.prompts), 1)  # the wildcard failure is ruled by the harness
        prompt = ask.prompts[0]
        self.assertIn("keep it when I save", prompt)
        self.assertIn("nickname: only in left: null", prompt)
        self.assertIn("   18      assert!(", prompt)
        self.assertNotIn("every_arrival", prompt)
        f = r["targets"]["heldout_saves"]["failures"]
        self.assertEqual(f[EXACT]["classification"], "new state only")
        self.assertEqual(f[EXACT]["by"], "grader")
        self.assertEqual(f[EXACT]["json_difference"], ["nickname: only in left: null"])
        self.assertEqual(f[EXACT]["evidence"][0]["text"], ["nickname: only in left: null"])
        self.assertEqual(f[SHAPE]["evidence"][0]["text"][0], "    assert!(")
        cats = r["targets"]["heldout_cats"]["failures"]["cats::every_arrival_is_described"]
        self.assertEqual((cats["classification"], cats["by"]), ("keeping failure", "harness"))
        self.assertIn("wildcard", cats["reason"])
        self.assertEqual((r["new_state_only"], r["keeping_failures"], r["classified"]), (2, 1, True))
        self.assertAlmostEqual(r["share_kept"], (2 + 2) / (2 + 3))
        self.assertAlmostEqual(r["classification_cost_usd"], 0.01)
        saved = json.loads((out / "heldout_saves-b01.json").read_text())
        self.assertEqual(saved["prompt"], prompt)
        self.assertEqual(len(saved["tries"]), 1)

    def test_a_ruling_citing_another_tests_entry_or_a_line_outside_it_is_asked_again(self):
        def bad(prompt):
            s = seqs(prompt)
            return {"rulings": [ruling(EXACT, "new state only", s[SHAPE]["failure output"], [1]),
                                ruling(SHAPE, "new state only", s[SHAPE]["test source"], [99])]}
        r, ask = keep_result(), Ask(bad, good)
        rc.classify(r, {"heldout_saves": SAVES_LOG, "heldout_cats": CATS_LOG}, self.files(), CHANGE, ask=ask)
        self.assertEqual(len(ask.prompts), 2)
        self.assertEqual(r["new_state_only"], 2)

    def test_a_test_with_no_valid_ruling_counts_as_a_keeping_failure(self):
        def half(prompt):
            s = seqs(prompt)
            return {"rulings": [ruling(EXACT, "new state only", s[EXACT]["json difference"], [1])]}
        r, ask = keep_result(), Ask(half, half, half)
        rc.classify(r, {"heldout_saves": SAVES_LOG, "heldout_cats": CATS_LOG}, self.files(), CHANGE, ask=ask)
        f = r["targets"]["heldout_saves"]["failures"]
        self.assertEqual(f[EXACT]["classification"], "new state only")
        self.assertEqual((f[SHAPE]["classification"], f[SHAPE]["by"]), ("keeping failure", "harness"))
        self.assertIn("No valid ruling", f[SHAPE]["reason"])
        self.assertEqual((r["new_state_only"], r["keeping_failures"]), (1, 2))

    def test_the_schema_offers_the_two_classifications(self):
        props = rc.SCHEMA["properties"]["rulings"]["items"]["properties"]
        self.assertEqual(props["classification"]["enum"], ["new state only", "keeping failure"])
        self.assertEqual(rc.change_text(SimpleNamespace(title="Nicknames", owner_request="Give them nicknames.",
                                                        redirect=SimpleNamespace(text="Only for the kittens, though."))),
                         "Nicknames\n\nGive them nicknames.\n\nLater in the change, the owner said:\n\nOnly for the kittens, though.")


class GradeRustClassifiesTest(unittest.TestCase):
    def test_grading_a_change_classifies_its_failures_with_the_judge_model_and_reports_both_counts(self):
        import shutil
        import grade_rust
        from test_rust_adapt import FakeCk
        from test_simulator import CHANGES
        root = Path(tempfile.mkdtemp())
        shutil.copytree(FIX / "held-out", root / "variants" / "held-out")
        held = ["crates/fixture/tests/integration/saves.rs"]
        (root / "variants" / "manifest.json").write_text(json.dumps({"held_out": held, "variants": {}}))
        (root / "seed" / "hidden").mkdir(parents=True)
        (root / "seed" / "hidden" / "change-script.md").write_text(CHANGES)
        run = root / "runs" / "cf-x"
        run.mkdir(parents=True)
        (run / "trajectory.json").write_text(json.dumps({
            "id": "cf-x", "change": 3, "start_commit": "b0", "image": "img", "volumes": {"workspace": "ws"},
            "fork_of": {"variants": str(root / "variants")}, "changes": {"3": {"commit": "c1"}}}))

        class Ck(FakeCk):
            volume = "ckpt"

            def sh(self, script, stdin=None, check=True):
                if "git " in script:
                    return ""
                return super().sh(script, stdin, check)

            def export(self, vol):
                pass

            def drop_target(self):
                pass
        ck = Ck({"heldout_saves": SAVES_LOG})
        calls = []

        def run_role(role, prompt, json_schema=None):
            calls.append((role.model, json.loads(json_schema)))
            return SimpleNamespace(structured=good(prompt), text="", duration_s=0.1,
                                   usage=SimpleNamespace(reported_cost_usd=0.02, models={}))
        rc_ = grade_rust.main(["--id", "cf-x", "--runs", str(root / "runs"), "--seed-dir", str(root / "seed")],
                              checkpoint=lambda name, commit, image: ck, run_role=run_role)
        self.assertEqual(rc_, 0)
        self.assertEqual([(m, list(s["properties"])) for m, s in calls], [("claude-sonnet-5-5", ["rulings"])])
        out = run / "grading" / "change-03"
        keeping = json.loads((out / "keeping.json").read_text())
        self.assertEqual({t: f["classification"] for t, f in keeping["targets"]["heldout_saves"]["failures"].items()},
                         {EXACT: "new state only", SHAPE: "new state only"})
        summary = json.loads((out / "summary.json").read_text())["held_out_retention"]
        self.assertEqual((summary["failed"], summary["keeping_failures"], summary["new_state_only"], summary["classified"]),
                         (2, 0, 2, True))
        self.assertTrue((out / "keeping" / "classify" / "heldout_saves-b01.json").exists())
        # without a change script there is nothing to rule against: the failures stay unclassified
        (root / "seed" / "hidden" / "change-script.md").unlink()
        calls.clear()
        grade_rust.main(["--id", "cf-x", "--runs", str(root / "runs"), "--seed-dir", str(root / "seed")],
                        checkpoint=lambda name, commit, image: Ck({"heldout_saves": SAVES_LOG}), run_role=run_role)
        summary = json.loads((out / "summary.json").read_text())["held_out_retention"]
        self.assertEqual((calls, summary["classified"], summary["keeping_failures"]), ([], False, None))


if __name__ == "__main__":
    unittest.main()
