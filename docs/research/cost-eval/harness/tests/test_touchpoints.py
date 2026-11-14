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


if __name__ == "__main__":
    unittest.main()
