"""Tests for classify_touchpoints: what the classifier is shown."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import classify_touchpoints as ct  # noqa: E402
from costeval import simulator as sm  # noqa: E402
from test_simulator import BRIEF, CHANGES, ORACLE  # noqa: E402


class OwnerViewTest(unittest.TestCase):
    def test_the_classifier_sees_knowledge_change_and_message_but_not_how_to_respond(self):
        p = sm.build_prompt(oracle=sm.parse_oracle(ORACLE), change=sm.parse_change_script(CHANGES)[1], brief=BRIEF,
                            message="Should notes be limited? OK to go ahead?")
        view = ct.owner_view(p)
        self.assertIn("[BK-09]", view)
        self.assertIn("Please let me add a note", view)
        self.assertIn("Should notes be limited?", view)
        for gone in ("## How you respond", "## What counts as what", "## What to return", "clarification_settled"):
            self.assertNotIn(gone, view)

    def test_the_classifier_sees_the_message_without_passage_numbers(self):
        p = sm.build_prompt(oracle=sm.parse_oracle(ORACLE), change=sm.parse_change_script(CHANGES)[1], brief=BRIEF,
                            message="Plan.\n\nShould notes be limited?")
        view = ct.owner_view(p)
        self.assertIn("Plan.\n\nShould notes be limited?", view)
        self.assertNotIn("[P1]", view)

    def test_a_broad_question_is_origination(self):
        t = (Path(ct.__file__).resolve().parent / "prompts" / "touchpoints.md").read_text(encoding="utf-8")
        self.assertRegex(t, r"A broad question[^.]*is origination")

    def test_recall_on_review_is_counted_apart_from_requests(self):
        shared = [{"item": "BK-02", "reason": "asked"}, {"item": "BK-09", "reason": "recalled", "via": "review"},
                  {"item": "BK-07", "reason": "recalled", "via": "question"}]
        self.assertEqual(ct.recalled_on_review({"shared": shared}), ["BK-09"])
        self.assertEqual(ct.recalled_on_review({"shared": []}), [])
        self.assertEqual(ct.recalled_on_review({}), [])


if __name__ == "__main__":
    unittest.main()
