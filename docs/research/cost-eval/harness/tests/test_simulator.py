"""Tests for costeval.simulator: what the simulated owner may know at each change, and its prompt.

The fixtures are made up, so no hidden seed material appears in this public file.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from costeval import simulator  # noqa: E402

ORACLE = """# Oracle

## Owner narrative

The simulator receives sections by change. This paragraph is for the study, not the owner.

### What the owner knows from the start

I run a small bakery and need orders tracked.

### Learned at change 2: deliveries

Some customers want delivery now.

### Learned at change 5: refunds

Refunds have to go back to the original card.

## Disclosure and grading conventions

- Not for the owner.

## Item table

| ID | Checkable behavior | Disclosure kind | In force | Retired | External check sketch |
|---|---|---|---|---|---|
| BK-01 | An order records its customer. | Stated at start | Start | — | Grader-only sketch. |
| BK-02 | Orders close at 18:00. | Askable | Start | — | Grader-only sketch. |
| BK-03 | Old orders are never deleted. | Recognized on sight | Start | — | Grader-only sketch. |
| BK-04 | Same-day orders are free. | Stated at start | Start | Change 2 | Grader-only sketch. |
| BK-05 | Deliveries cost 3 pounds. | Stated in change 2 | Change 2 | — | Grader-only sketch. |
| BK-06 | One open order per customer. | Emerging at change 4 | Change 4 | — | Grader-only sketch. |
| BK-07 | A refund goes to the original card. | Realized on symptom | Change 5 | — | Grader-only sketch. |
| BK-08 | Dropped: only validation. | Dropped | — | — | Not graded. |

## Recognized-on-sight responses

These are not volunteered as general advice.

- **BK-03**, if a plan deletes old orders:
  **"No, keep every order we've ever taken."**
"""

CHANGES = """# Change script

## Delivery rules

Not for the owner.

## Change 1 — Order notes

**Type:** Ordinary local feature.

### Owner request

> Please let me add a note to an order.
>
> Keep it short.

**Introduces:** Nothing.

## Change 2 — Deliveries

### Initial owner request

> Add deliveries.

### Early redirect: change of mind

Deliver at the first plan or approval question, before implementation:

> Actually, deliveries should cost 3 pounds.

## Change 3 — Move an order

### Owner request

> Let me move an order to another day.

### Late redirect: clarification

Deliver after code for moving exists:

> By "move" I mean keep the same order number.

## Change 4 — Copy an order

### Owner request

> Let me copy an order.

### Emerging statement

Deliver with the request, as an additional owner paragraph:

> Also, one open order per customer from now on.

### Hidden owner guidance if asked

> A copy is a new order, so it gets today's prices.

## Change 5 — Refunds go astray

### Scheduled diagnostic

Refund an order and check where it went.

### Owner symptom report

Deliver only if the diagnostic fails:

> A customer says their refund never arrived.
"""


class OracleTest(unittest.TestCase):
    def setUp(self):
        self.o = simulator.parse_oracle(ORACLE)

    def test_narrative_is_released_by_change_without_study_notes_or_headings(self):
        at3 = simulator.released_narrative(self.o, 3)
        self.assertIn("small bakery", at3)
        self.assertIn("delivery now", at3)
        self.assertNotIn("original card", at3)
        self.assertNotIn("for the study", at3)
        self.assertNotIn("Learned at change", at3)
        self.assertIn("original card", simulator.released_narrative(self.o, 5))

    def test_items_in_force_at_a_change(self):
        ids = lambda c: [i.id for i in simulator.released_items(self.o, c)]
        self.assertEqual(ids(1), ["BK-01", "BK-02", "BK-03", "BK-04"])
        self.assertEqual(ids(2), ["BK-01", "BK-02", "BK-03", "BK-05"])  # BK-04 retired at change 2
        self.assertEqual(ids(4), ["BK-01", "BK-02", "BK-03", "BK-05", "BK-06"])
        self.assertIn("BK-07", ids(5))
        self.assertNotIn("BK-08", ids(10))

    def test_how_each_kind_is_shared(self):
        share = {i.id: i.share for i in simulator.released_items(self.o, 5)}
        self.assertEqual(share["BK-01"], "Stated")
        self.assertEqual(share["BK-02"], "Askable")
        self.assertEqual(share["BK-03"], "Recognized on sight")
        self.assertEqual(share["BK-06"], "Stated")  # emerging items are said aloud at their change
        self.assertEqual(share["BK-07"], "Askable")  # symptom items are known once released

    def test_recognized_items_carry_their_response(self):
        items = {i.id: i for i in simulator.released_items(self.o, 1)}
        self.assertEqual(items["BK-03"].response, "No, keep every order we've ever taken.")
        self.assertIsNone(items["BK-02"].response)

    def test_grading_sketches_never_reach_the_owner(self):
        text = simulator.render_items(simulator.released_items(self.o, 10))
        self.assertNotIn("Grader-only", text)


class ChangeScriptTest(unittest.TestCase):
    def setUp(self):
        self.c = simulator.parse_change_script(CHANGES)

    def test_requests_are_the_quoted_owner_words(self):
        self.assertEqual(self.c[1].request, "Please let me add a note to an order.\n\nKeep it short.")
        self.assertEqual(self.c[2].request, "Add deliveries.")

    def test_redirects_carry_their_kind_timing_and_words(self):
        r2, r3 = self.c[2].redirect, self.c[3].redirect
        self.assertEqual((r2.timing, r2.kind, r2.text), ("early", "change of mind", "Actually, deliveries should cost 3 pounds."))
        self.assertEqual((r3.timing, r3.kind), ("late", "clarification"))
        self.assertIsNone(self.c[1].redirect)

    def test_emerging_statement_guidance_and_symptom(self):
        self.assertEqual(self.c[4].emerging, "Also, one open order per customer from now on.")
        self.assertEqual(self.c[4].guidance, "A copy is a new order, so it gets today's prices.")
        self.assertEqual(self.c[5].symptom, "A customer says their refund never arrived.")
        self.assertIsNone(self.c[5].request)


class PromptTest(unittest.TestCase):
    def setUp(self):
        self.o = simulator.parse_oracle(ORACLE)
        self.c = simulator.parse_change_script(CHANGES)

    def prompt(self, **kw):
        args = dict(oracle=self.o, change=self.c[2], request="Add deliveries.", policy="diligent",
                    message="Here is my plan. Shall I go ahead?", record=[], redirect_pending=True,
                    code_written=False)
        args.update(kw)
        return simulator.build_prompt(**args)

    def test_every_placeholder_is_filled(self):
        p = self.prompt()
        self.assertNotRegex(p, r"\{[A-Z_]+\}")
        self.assertIn("Here is my plan.", p)
        self.assertIn("change 2", p)

    def test_the_pending_redirect_and_code_flag_appear_only_while_pending(self):
        self.assertIn("Actually, deliveries should cost 3 pounds.", self.prompt())
        self.assertIn("Code for this change exists yet: no", self.prompt())
        self.assertNotIn("Actually, deliveries", self.prompt(redirect_pending=False))

    def test_policies_differ(self):
        texts = {p: self.prompt(policy=p) for p in simulator.POLICIES}
        self.assertEqual(len(set(texts.values())), 3)
        with self.assertRaises(ValueError):
            self.prompt(policy="careless")

    def test_bounded_attention_cuts_the_message(self):
        long = " ".join(f"w{i}" for i in range(1000))
        p = self.prompt(policy="bounded", message=long, attention_words=100)
        self.assertIn("w99", p)
        self.assertNotIn("w100 ", p)
        self.assertIn("[You stopped reading here.]", p)

    def test_the_record_is_shown_and_an_empty_one_says_so(self):
        self.assertIn("Nothing yet.", self.prompt())
        rec = [simulator.Answer(change=1, question="note length?", answer="short", items=["BK-02"])]
        p = self.prompt(record=rec)
        self.assertIn("note length?", p)
        self.assertNotIn("BK-02", p.split("## What you've told the agent before")[1])

    def test_the_schema_requires_every_field(self):
        self.assertEqual(set(simulator.OUTPUT_SCHEMA["required"]), {"finished", "reply", "redirect_delivered", "redirect_preempted", "answers"})


if __name__ == "__main__":
    unittest.main()
