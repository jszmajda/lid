"""Tests for costeval.simulator: what the simulated owner knows and is shown, its prompt, and its replies.

The fixtures are made up, so no hidden seed material appears in this public file.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from costeval import simulator as sm  # noqa: E402

ORACLE = """# Oracle

## Owner narrative

The simulator receives sections by change. This paragraph is for the study, not the owner.

### What the owner knows from the start

I run a small bakery and need orders tracked.

### Learned at change 2: deliveries

Deliveries cost money, so they have a fee.

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
| BK-09 | Notes are kept as typed. Whether blank notes count is graded under BK-02. | Askable | Start | — | Grader-only sketch. |
| BK-10 | Moving an order from change 3 onward keeps its number. | Stated in change 3 | Change 3 | — | Grader-only sketch. |

## Recognized-on-sight responses

These are not volunteered as general advice.

- **BK-03**, if a plan deletes old orders:
  **"No, keep every order we've ever taken."**
"""

CHANGES = """# Change script

## Delivery rules

Not for the owner.

## Change 1 — Order notes

### Owner request

> Please let me add a note to an order.
>
> Keep it short.

**Introduces:** Nothing.
**Relies on:** BK-01, BK-09.

## Change 2 — Deliveries

### Initial owner request

> Add deliveries, free of charge.

### Early redirect: change of mind

Deliver at the first plan or approval question:

> Actually, deliveries should cost 3 pounds.
>
> Put the fee on the order.

**Redirect introduces:** BK-05.

**Introduces:** BK-05.
**Retires:** BK-04.
**Relies on:** BK-01 through BK-03.

## Change 3 — Move an order

### Owner request

> Let me move an order to another day.

### Late redirect: clarification

> By "move" I mean keep the same order number.

**Introduces:** BK-10.
**Relies on:** Every item already in force.

## Change 4 — Copy an order

### Owner request

> Let me copy an order.

### Emerging statement

> Also, one open order per customer from now on.

### Hidden owner guidance if asked

> A copy is a new order, so it gets today's prices.

**Introduces:** BK-06.

## Change 5 — Refunds go astray

### Scheduled diagnostic

Refund an order and check where it went.

### Owner symptom report

> A customer says their refund never arrived.

**Introduces:** BK-07.

## Probe request — separate and disposable

### Owner request

> List the orders due tomorrow.
"""

BRIEF = "# Bakery\n\nTrack our orders. Each order records its customer."


def oracle():
    return sm.parse_oracle(ORACLE)


def script():
    return sm.parse_change_script(CHANGES)


class OracleTest(unittest.TestCase):
    def setUp(self):
        self.o = oracle()

    def test_narrative_is_released_by_change_without_study_notes_or_headings(self):
        at3 = sm.released_narrative(self.o, 3)
        self.assertIn("small bakery", at3)
        self.assertIn("have a fee", at3)
        self.assertNotIn("original card", at3)
        self.assertNotIn("for the study", at3)
        self.assertNotIn("Learned at change", at3)
        self.assertIn("original card", sm.released_narrative(self.o, 5))
        self.assertNotIn("have a fee", sm.released_narrative(self.o, 3, withhold_section=2))

    def test_study_wording_inside_a_narrative_section_is_refused(self):
        bad = ORACLE.replace("Deliveries cost money", "At change 2 the owner changes their mind. Deliveries cost money")
        with self.assertRaisesRegex(ValueError, "study wording"):
            sm.parse_oracle(bad)

    def test_items_in_force_at_a_change(self):
        ids = lambda c, **kw: [i.id for i in sm.released_items(self.o, c, **kw)]
        self.assertEqual(ids(1), ["BK-01", "BK-02", "BK-03", "BK-04", "BK-09"])
        self.assertEqual(ids(2), ["BK-01", "BK-02", "BK-03", "BK-05", "BK-09"])  # BK-04 retired at change 2
        self.assertNotIn("BK-05", ids(2, withhold=["BK-05"]))
        self.assertIn("BK-06", ids(4))
        self.assertIn("BK-07", ids(5))
        self.assertNotIn("BK-08", ids(10))

    def test_how_each_kind_is_shared(self):
        share = {i.id: i.share for i in sm.released_items(self.o, 5)}
        self.assertEqual(share["BK-01"], "Stated")
        self.assertEqual(share["BK-02"], "Askable")
        self.assertEqual(share["BK-03"], "Recognized on sight")
        self.assertEqual(share["BK-06"], "Stated")  # emerging items are said aloud at their change
        self.assertEqual(share["BK-07"], "Askable")  # symptom items are known once released

    def test_recognized_items_carry_their_response(self):
        items = {i.id: i for i in sm.released_items(self.o, 1)}
        self.assertEqual(items["BK-03"].response, "No, keep every order we've ever taken.")
        self.assertIsNone(items["BK-02"].response)

    def test_graders_notes_never_reach_the_owner(self):
        text = sm.render_items(sm.released_items(self.o, 10), sm.ALL)
        self.assertNotIn("Grader-only", text)
        self.assertIn("Notes are kept as typed.", text)
        self.assertNotIn("graded under", text)
        self.assertIn("Moving an order keeps its number.", text)

    def test_askable_items_in_play_are_marked(self):
        text = sm.render_items(sm.released_items(self.o, 1), {"BK-09"})
        self.assertIn("[BK-09] (Askable; in play for this change)", text)
        self.assertIn("[BK-02] (Askable) ", text)

    def test_malformed_oracles_are_refused(self):
        cases = {
            "two narrative sections": ORACLE.replace("### Learned at change 5: refunds", "### Learned at change 2: refunds"),
            "In force": ORACLE.replace("| Askable | Start | — | Grader-only sketch. |\n| BK-03", "| Askable | Soon | — | Grader-only sketch. |\n| BK-03"),
            "no response": ORACLE.replace("- **BK-03**, if a plan deletes old orders:\n  **\"No, keep every order we've ever taken.\"**", ""),
            "in force from change": ORACLE.replace("| Stated in change 2 | Change 2 |", "| Stated in change 2 | Change 3 |"),
        }
        for why, text in cases.items():
            with self.subTest(why), self.assertRaisesRegex(ValueError, why):
                sm.parse_oracle(text)


class ChangeScriptTest(unittest.TestCase):
    def setUp(self):
        self.c = script()

    def test_requests_are_the_quoted_owner_words(self):
        self.assertEqual(self.c[1].request, "Please let me add a note to an order.\n\nKeep it short.")
        self.assertEqual(self.c[2].request, "Add deliveries, free of charge.")

    def test_redirects_carry_their_kind_timing_items_and_every_paragraph(self):
        r2, r3 = self.c[2].redirect, self.c[3].redirect
        self.assertEqual((r2.timing, r2.kind), ("early", "change of mind"))
        self.assertEqual(r2.text, "Actually, deliveries should cost 3 pounds.\n\nPut the fee on the order.")
        self.assertEqual(r2.introduces, ("BK-05",))
        self.assertEqual((r3.timing, r3.kind), ("late", "clarification"))
        self.assertIsNone(self.c[1].redirect)

    def test_unsupported_or_incomplete_redirects_are_refused(self):
        with self.assertRaisesRegex(ValueError, "unsupported redirect"):
            sm.parse_change_script(CHANGES.replace("### Late redirect: clarification", "### Interrupt redirect: clarification"))
        with self.assertRaisesRegex(ValueError, "must list the items"):
            sm.parse_change_script(CHANGES.replace("**Redirect introduces:** BK-05.", ""))

    def test_the_owners_request_includes_an_emerging_statement_or_a_symptom(self):
        self.assertEqual(self.c[4].owner_request, "Let me copy an order.\n\nAlso, one open order per customer from now on.")
        self.assertEqual(self.c[4].guidance, "A copy is a new order, so it gets today's prices.")
        self.assertIsNone(self.c[5].request)
        self.assertEqual(self.c[5].owner_request, "A customer says their refund never arrived.")
        with self.assertRaisesRegex(ValueError, "neither a request nor a symptom"):
            sm.parse_change_script(CHANGES.replace("> A customer says their refund never arrived.", ""))

    def test_item_lists_ranges_and_every_item(self):
        self.assertEqual(sm.parse_ids("BK-01 through BK-03, BK-09 as applicable"), ("BK-01", "BK-02", "BK-03", "BK-09"))
        self.assertEqual(sm.parse_ids("Every item already in force."), sm.ALL)
        self.assertEqual(sm.parse_ids("Nothing."), ())

    def test_items_in_play(self):
        self.assertEqual(self.c[1].in_play, {"BK-01", "BK-09"})
        self.assertEqual(self.c[2].in_play, {"BK-01", "BK-02", "BK-03", "BK-05"})
        self.assertEqual(self.c[3].in_play, sm.ALL)
        self.assertEqual(sm.first_build(BRIEF).in_play, sm.ALL)

    def test_the_first_build_and_the_probe(self):
        self.assertEqual(sm.first_build(BRIEF).owner_request, BRIEF)
        p = sm.parse_probe(CHANGES, 3)
        self.assertEqual((p.number, p.probe, p.request, p.in_play), (3, True, "List the orders due tomorrow.", sm.ALL))


class DocumentsTest(unittest.TestCase):
    FILES = {"docs/design.md": "a b c", "NOTES.md": "n", "app/main.py": "code", "docs/a/README.md": "x", "docs/b/README.md": "y"}

    def test_prose_files_named_in_the_message_by_path_or_unique_name_in_order(self):
        msg = "I updated NOTES.md and `./docs/design.md`; see also README.md and app/main.py."
        self.assertEqual(sm.mentioned_documents(msg, self.FILES), ["NOTES.md", "docs/design.md"])
        self.assertEqual(sm.mentioned_documents("Read /work/docs/a/README.md.", self.FILES), ["docs/a/README.md"])
        self.assertEqual(sm.mentioned_documents("Nothing to read.", self.FILES), [])

    def test_a_document_is_shown_whole_once_then_by_its_changes(self):
        first = sm.view_document("d.md", "one two\nthree", None)
        self.assertEqual((first.shown, first.words), ("one two\nthree", 3))
        same = sm.view_document("d.md", "one two\nthree", "one two\nthree")
        self.assertEqual(same.words, 0)
        changed = sm.view_document("d.md", "one two\nthree four five", "one two\nthree")
        self.assertIn("+three four five", changed.shown)
        self.assertIn("-three", changed.shown)
        self.assertEqual(changed.words, 3)


class PromptTest(unittest.TestCase):
    def setUp(self):
        self.o, self.c = oracle(), script()

    def prompt(self, change=1, **kw):
        args = dict(oracle=self.o, change=self.c[change], brief=BRIEF, message="Here is my plan. Shall I go ahead?",
                    redirect_state="pending" if self.c[change].redirect else None)
        args.update(kw)
        return sm.build_prompt(**args)

    def test_every_placeholder_is_filled_and_empty_sections_vanish(self):
        p = self.prompt()
        self.assertNotRegex(p, r"\{[A-Z_]+\}")
        self.assertIn("<agent_message>\nHere is my plan. Shall I go ahead?\n</agent_message>", p)
        self.assertIn("<brief>", p)
        for absent in ("## What you asked for in earlier changes", "## What you told the agent in earlier changes",
                       "## This change so far", "## Documents the agent asked you to read", "## You have changed your mind"):
            self.assertNotIn(absent, p)
        self.assertNotRegex(p, r"\n{3,}")

    def test_the_agents_message_is_inserted_untouched(self):
        msg = "Plan:\n\n\n\nStep {NARRATIVE} one."
        self.assertIn(msg, self.prompt(message=msg))

    def test_a_pending_change_of_mind_is_withheld(self):
        p = self.prompt(change=2)
        self.assertNotIn("have a fee", p)
        self.assertNotIn("[BK-05]", p)
        self.assertNotIn("3 pounds", p)
        self.assertNotIn("[BK-04]", p)  # retired by the change's own request

    def test_a_change_of_mind_being_delivered_releases_its_view(self):
        p = self.prompt(change=2, redirect_state="firing")
        self.assertIn("## You have changed your mind", p)
        self.assertIn("> Actually, deliveries should cost 3 pounds.\n>\n> Put the fee on the order.", p)
        self.assertIn("have a fee", p)
        self.assertIn("[BK-05]", p)
        later = self.prompt(change=2, redirect_state="delivered")
        self.assertNotIn("## You have changed your mind", later)
        self.assertIn("Later in this change you told the agent", later)

    def test_a_pending_clarification_is_shown_until_it_is_settled_or_delivered(self):
        self.assertIn("## Something you mean to make clear", self.prompt(change=3))
        self.assertNotIn("## Something you mean to make clear", self.prompt(change=3, redirect_state="settled"))

    def test_the_first_build_asks_with_the_brief(self):
        p = sm.build_prompt(oracle=self.o, change=sm.first_build(BRIEF), brief=BRIEF, message="Plan?")
        self.assertIn("This is the first build", p)
        self.assertNotIn("## What you told the agent at the start", p)

    def test_guidance_appears_with_its_reason(self):
        self.assertIn("If the agent asks why you want this", self.prompt(change=4))
        self.assertNotIn("If the agent asks why you want this", self.prompt(change=1))

    def test_earlier_requests_the_record_and_this_change_so_far(self):
        p = self.prompt(change=3, redirect_state="settled",
                        earlier_requests=[(1, "Please let me add a note.")],
                        record=[sm.Said(1, "Keep notes short.", "note length?", ("BK-09",)), sm.Said(1, "Never delete orders.")],
                        turns=[sm.Turn("Should moved orders keep the number?", (), "Yes, keep it.\n\nGo ahead.")])
        self.assertIn("Change 1:\n\n> Please let me add a note.", p)
        self.assertIn("- Change 1. Asked: note length? You answered: Keep notes short.", p)
        self.assertIn("- Change 1. You told the agent: Never delete orders.", p)
        self.assertIn("<earlier_agent_message>\nShould moved orders keep the number?", p)
        self.assertIn("> Yes, keep it.", p)
        self.assertNotIn("BK-09", p.split("## What you told the agent in earlier changes")[1].split("##")[0])

    def test_documents_are_shown_by_name(self):
        p = self.prompt(documents=[sm.Document("docs/design.md", "Orders are deleted after a year.", 6, "x")])
        self.assertIn('<document name="docs/design.md">\nOrders are deleted after a year.\n</document>', p)

    def test_redirect_state_must_match_the_change(self):
        with self.assertRaises(ValueError):
            self.prompt(change=1, redirect_state="pending")
        with self.assertRaises(ValueError):
            self.prompt(change=2, redirect_state=None)


def out(kind="approval", answers=(), corrections=(), settled=False):
    return {"message_kind": kind, "answers": list(answers), "corrections": list(corrections), "clarification_settled": settled}


def ans(q, a, items=(), no_view=False):
    return {"question": q, "answer": a, "items": list(items), "no_view": no_view}


def cor(item, text, wrong="the agent's words"):
    return {"item": item, "wrong": wrong, "text": text}


class FakeAsk:
    def __init__(self, *outputs):
        self.outputs, self.prompts = list(outputs), []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        return self.outputs.pop(0)


def owner(policy="diligent", *outputs, seed="s1"):
    ask = FakeAsk(*outputs)
    return sm.Owner(oracle=oracle(), brief=BRIEF, policy=policy, seed=seed, ask=ask), ask


class OwnerTest(unittest.TestCase):
    def setUp(self):
        self.c = script()

    def test_policies_differ_only_in_which_corrections_are_kept(self):
        o = out("approval", [ans("Closing time?", "We close at 18:00.", ["BK-02"])], [cor("BK-03", "No, keep every order we've ever taken.")])
        replies = {}
        for policy in ("diligent", "rubber-stamp"):
            w, ask = owner(policy, o)
            w.start_change(self.c[1])
            replies[policy] = w.respond("Plan: delete old orders. Closing time?", code_written=False)
            self.assertIn("Closing time?", ask.prompts[0])
        self.assertEqual(replies["diligent"].reply, "We close at 18:00.\n\nNo, keep every order we've ever taken.\n\nOtherwise, go ahead.")
        self.assertEqual(replies["rubber-stamp"].reply, "We close at 18:00.\n\nGo ahead.")
        self.assertEqual(len(replies["rubber-stamp"].dropped), 1)
        self.assertEqual(replies["rubber-stamp"].shared, [{"item": "BK-02", "reason": "asked"}])

    def test_the_bounded_owner_catches_less_as_reading_grows_and_its_draws_repeat(self):
        self.assertEqual(sm.catch_probability("bounded", 0), 1.0)
        self.assertAlmostEqual(sm.catch_probability("bounded", 1500), 0.5)
        self.assertLess(sm.catch_probability("bounded", 6000), sm.catch_probability("bounded", 600))
        many = [cor("BK-03", f"Correction {i}.") for i in range(40)]
        long_msg = "word " * 3000
        kept = []
        for _ in range(2):
            w, _ask = owner("bounded", out("approval", corrections=many), seed="fixed")
            w.start_change(self.c[1])
            r = w.respond(long_msg, code_written=False)
            kept.append([c["text"] for c in r.kept])
            self.assertAlmostEqual(r.catch_probability, 1 / 3)
        self.assertEqual(kept[0], kept[1])
        self.assertTrue(0 < len(kept[0]) < 40)

    def test_reading_counts_across_the_change(self):
        w, _ = owner("bounded", out("stop"), out("stop"))
        w.start_change(self.c[1])
        w.respond("one two three", code_written=False)
        r = w.respond("four five", [sm.Document("d.md", "six seven", 2, "six seven")], code_written=False)
        self.assertEqual((r.words_shown, r.words_this_change), (4, 7))

    def test_closing_words_and_finishing(self):
        cases = [
            (out("completion"), "", True),
            (out("approval"), "That looks fine. Go ahead.", False),
            (out("stop"), "Please continue.", False),
            (out("completion", [ans("Which zone?", "London time.")]), "London time.\n\nGo ahead.", False),
            (out("completion", corrections=[cor("BK-03", "Keep old orders.")]), "Keep old orders.\n\nOtherwise, go ahead.", False),
        ]
        for o, reply, finished in cases:
            with self.subTest(o):
                w, _ = owner("diligent", o)
                w.start_change(self.c[1])
                r = w.respond("msg", code_written=True)
                self.assertEqual((r.reply, r.finished), (reply, finished))
        w, _ = owner("rubber-stamp", out("completion", corrections=[cor("BK-03", "Keep old orders.")]))
        w.start_change(self.c[1])
        self.assertTrue(w.respond("Done.", code_written=True).finished)

    def test_show_me_answers_share_nothing(self):
        w, _ = owner("diligent", out("questions", [ans("Failed move?", sm.SHOW_ME, ["BK-03"])]))
        w.start_change(self.c[1])
        r = w.respond("What happens if a move fails?", code_written=False)
        self.assertEqual((r.answers[0]["items"], r.shared), ([], []))

    def test_no_view_answers_are_exact(self):
        w, _ = owner("diligent", out("questions", [ans("Colour?", "No preference really, you pick."), ans("Font?", "x", no_view=True)]))
        w.start_change(self.c[1])
        r = w.respond("Colour? Font?", code_written=False)
        self.assertEqual([a["answer"] for a in r.answers], [sm.NO_VIEW, sm.NO_VIEW])
        self.assertTrue(all(a["no_view"] for a in r.answers))

    def test_invalid_output_is_retried_then_fails(self):
        bad = out("questions", [ans("Fee?", "3 pounds.", ["BK-05"])])  # BK-05 isn't released at change 1
        w, ask = owner("diligent", bad, out("questions", [ans("Fee?", "No view.", no_view=True)]))
        w.start_change(self.c[1])
        r = w.respond("Fee?", code_written=False)
        self.assertEqual(len(ask.prompts), 2)
        self.assertEqual(len(r.calls), 2)
        self.assertTrue(r.calls[0]["problems"])
        for broken in (bad, out("questions"), out("approval", corrections=[cor("BK-03", "See BK-03.")])):
            with self.subTest(broken):
                w, _ = owner("diligent", broken, broken, broken)
                w.start_change(self.c[1])
                with self.assertRaises(sm.OwnerFailed):
                    w.respond("?", code_written=False)

    def test_an_early_change_of_mind_waits_for_a_plan_then_is_delivered_verbatim(self):
        w, ask = owner("diligent", out("questions", [ans("Free?", "Yes, free.")]),
                       out("approval"), out("approval", corrections=[cor("BK-05", "Charge it at checkout.")]))
        self.assertEqual(w.start_change(self.c[2]), "Add deliveries, free of charge.")
        r1 = w.respond("Should deliveries be free?", code_written=False)
        self.assertIsNone(r1.redirect_event)
        self.assertNotIn("3 pounds", ask.prompts[0])
        r2 = w.respond("Plan: free deliveries. OK?", code_written=False)
        self.assertEqual(r2.redirect_event, "delivered")
        self.assertEqual(len(ask.prompts), 3)  # the stop is answered again from the changed view
        self.assertIn("## You have changed your mind", ask.prompts[2])
        self.assertIn("[BK-05]", ask.prompts[2])
        self.assertTrue(r2.reply.startswith("Actually, deliveries should cost 3 pounds.\n\nPut the fee on the order.\n\n"))
        self.assertIn("Charge it at checkout.", r2.reply)
        self.assertEqual(w.end_change()["redirect"], {"kind": "change of mind", "timing": "early", "outcome": "delivered",
                                                      "point": "approval, code not written"})
        self.assertIn("Later in the change you said:\n\nActually, deliveries should cost 3 pounds.", w.requests[-1][1])

    def test_a_late_clarification_waits_for_code_unless_it_is_settled(self):
        w, ask = owner("diligent", out("approval"), out("completion"))
        w.start_change(self.c[3])
        self.assertIsNone(w.respond("Plan: move orders. OK?", code_written=False).redirect_event)
        r = w.respond("Done.", code_written=True)
        self.assertEqual(r.redirect_event, "delivered")
        self.assertFalse(r.finished)
        self.assertEqual(r.reply, 'By "move" I mean keep the same order number.\n\nOtherwise, go ahead.')

        w, ask = owner("diligent", out("questions", [ans("Keep the number?", "Yes.", ["BK-10"])], settled=True), out("completion"))
        w.start_change(self.c[3])
        self.assertEqual(w.respond("Should a moved order keep its number?", code_written=False).redirect_event, "settled")
        r = w.respond("Done.", code_written=True)
        self.assertTrue(r.finished)
        self.assertNotIn("## Something you mean to make clear", ask.prompts[1])
        self.assertEqual(w.end_change()["redirect"]["outcome"], "settled")

    def test_the_record_and_documents_carry_forward_and_a_fork_leaves_them_alone(self):
        w, ask = owner("diligent", out("questions", [ans("Note length?", "Keep it short.", ["BK-09"])]), out("completion"),
                       out("completion"), out("completion"))
        w.start_change(self.c[1])
        files = {"docs/design.md": "Design v1"}
        docs = w.documents("See docs/design.md.", files)
        w.respond("See docs/design.md. Note length?", docs, code_written=False)
        w.respond("Done.", code_written=True)
        w.end_change()
        self.assertEqual(w.record, [sm.Said(1, "Keep it short.", "Note length?", ("BK-09",))])
        self.assertEqual(w.documents("See docs/design.md.", files)[0].words, 0)
        probe = w.fork()
        probe.start_change(sm.parse_probe(CHANGES, 1))
        probe.respond("Done.", code_written=True)
        probe.end_change()
        self.assertEqual(len(w.requests), 1)
        w.start_change(self.c[4])
        w.respond("Done.", code_written=True)
        self.assertIn("You answered: Keep it short.", ask.prompts[-1])
        self.assertIn("Change 1:\n\n> Please let me add a note to an order.", ask.prompts[-1])


class TrimTest(unittest.TestCase):
    def test_answers_that_share_rules_and_corrections_are_trimmed_and_nothing_grows(self):
        c = script()
        trims = []
        def trim(prompt):
            trims.append(prompt)
            return {"parts": [{"index": 1, "text": "We close at 18:00."}, {"index": 2, "text": "Keep old orders, and also many more words than before."}]}
        o = out("approval", [ans("Closing time?", "We close at 18:00, and late orders go to tomorrow.", ["BK-02"]),
                             ans("Colour?", "x", no_view=True)],
                [cor("BK-03", "Keep old orders.", wrong="delete old orders")])
        w = sm.Owner(oracle=oracle(), brief=BRIEF, policy="diligent", seed="s", ask=FakeAsk(o), trim=trim)
        w.start_change(c[1])
        r = w.respond("Plan: delete old orders. Closing time? Colour?", code_written=False)
        self.assertIn('Part 1 (answer). The question it answers: "Closing time?"', trims[0])
        self.assertIn('Part 2 (correction). The agent\'s words it corrects: "delete old orders"', trims[0])
        self.assertNotIn("Colour", trims[0].split("</agent_message>")[1])
        self.assertEqual(r.answers[0]["answer"], "We close at 18:00.")
        self.assertEqual(r.kept[0]["text"], "Keep old orders.")  # a longer edit is refused
        self.assertEqual(r.calls[-1]["trim"], [{"part": 1, "before": "We close at 18:00, and late orders go to tomorrow.",
                                                "after": "We close at 18:00."}])

    def test_a_correction_trimmed_to_drop_is_removed_but_an_answer_never_is(self):
        c = script()
        o = out("approval", [ans("Closing time?", "We close at 18:00.", ["BK-02"])],
                [cor("BK-03", "Also keep old orders.", wrong="keep this week's orders")])
        w = sm.Owner(oracle=oracle(), brief=BRIEF, policy="diligent", seed="s", ask=FakeAsk(o),
                     trim=lambda p: {"parts": [{"index": 1, "text": "DROP"}, {"index": 2, "text": "DROP"}]})
        w.start_change(c[1])
        r = w.respond("Plan: keep this week's orders. Closing time?", code_written=False)
        self.assertEqual(r.answers[0]["answer"], "We close at 18:00.")
        self.assertEqual(r.kept + r.dropped, [])
        self.assertNotIn("old orders", r.reply)
        self.assertEqual(r.calls[-1]["trim"], [{"part": 2, "before": "Also keep old orders.", "after": None}])

    def test_a_drop_is_ignored_for_what_this_changes_request_asked_for(self):
        c = script()
        # BK-10 is stated in change 3: an omission from that request is still pointed out
        o = out("approval", [], [cor("BK-10", "A moved order also keeps its number.", wrong="move the order")])
        w = sm.Owner(oracle=oracle(), brief=BRIEF, policy="diligent", seed="s", ask=FakeAsk(o),
                     trim=lambda p: {"parts": [{"index": 1, "text": "DROP"}]})
        w.start_change(c[3])
        r = w.respond("Plan: move the order to the new day. OK?", code_written=False)
        self.assertEqual([k["item"] for k in r.kept], ["BK-10"])

    def test_nothing_to_trim_makes_no_call(self):
        w = sm.Owner(oracle=oracle(), brief=BRIEF, policy="diligent", seed="s", ask=FakeAsk(out("approval")),
                     trim=lambda p: self.fail("trim called"))
        w.start_change(script()[1])
        w.respond("Plan. OK?", code_written=False)


class JudgeTest(unittest.TestCase):
    def test_the_judge_sees_the_owner_prompt_the_reply_and_the_scripted_words(self):
        p = sm.judge_prompt("OWNER PROMPT HERE", "Reply here.", scripted="Actually, 3 pounds.")
        self.assertIn("<owner_prompt>\nOWNER PROMPT HERE\n</owner_prompt>", p)
        self.assertIn("<reply>\nReply here.\n</reply>", p)
        self.assertIn("> Actually, 3 pounds.", p)
        self.assertNotRegex(p, r"\{[A-Z_]+\}")
        self.assertNotIn("scheduled words", sm.judge_prompt("x", "y"))


if __name__ == "__main__":
    unittest.main()
