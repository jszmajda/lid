"""Tests for guess_panel: option shuffling and parsing answers."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import guess_panel as gp  # noqa: E402


class PanelTest(unittest.TestCase):
    def test_shuffled_options_map_back_to_their_original_letters(self):
        opts = ["keep", "drop", "ask"]
        shown, back = gp.shuffled(opts, "model|R01")
        self.assertEqual(sorted(shown), sorted(opts))
        for letter, original in back.items():
            self.assertEqual(shown["ABC".index(letter)], opts["ABC".index(original)])
        self.assertEqual(gp.shuffled(opts, "model|R01"), (shown, back))  # the same key gives the same order

    def test_choices_are_parsed_from_json_in_free_text(self):
        self.assertEqual(gp.parse_choice('Sure. {"choice": "b", "reason": "simplest"}'), {"choice": "B", "reason": "simplest"})
        self.assertIsNone(gp.parse_choice("I would ask the owner."))
        self.assertIsNone(gp.parse_choice('{"choice": "Z"}'))

    def test_the_change_request_follows_the_brief(self):
        text = gp.context("Brief text.", {"change_request": "Add manifests."})
        self.assertLess(text.index("Brief text."), text.index("Add manifests."))
        self.assertNotIn("change_request", gp.context("Brief text.", None))


if __name__ == "__main__":
    unittest.main()
