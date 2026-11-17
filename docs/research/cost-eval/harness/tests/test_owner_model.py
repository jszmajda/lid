"""Tests for the owner's attention and recall (design.md, "The user simulator" and "Attention and recall"): numbered
passages, the attention and recall rates, seeded draws and their scopes, the three policies, broad questions, how a
reply is put together, and what the owner carries between stops.

The fixtures are the made-up bakery from test_simulator, so no hidden seed material appears here.
"""

import copy
import dataclasses
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from costeval import simulator as sm  # noqa: E402
from test_simulator import BRIEF, CHANGES, OWNER_ITEMS, FakeAsk, ans, cor, oracle, out, owner, script  # noqa: E402

M = sm.OwnerModel()
LOW_ADJ = sm.recall_rate(M, "low", direct=False)
LOW_DIRECT = sm.recall_rate(M, "low", direct=True)
MED_ADJ = sm.recall_rate(M, "medium", direct=False)
MED_DIRECT = sm.recall_rate(M, "medium", direct=True)
RECALL = {i: d["recall"] for i, d in OWNER_ITEMS.items()}


def touch(item, passage, level="direct"):
    return {"item": item, "passage": passage, "level": level}


def broad(question, in_scope=(), answer=""):
    return ans(question, answer, breadth="broad", in_scope=in_scope)


def key(change, scope="change", stop=0):
    return sm.scope_key(scope, change, stop)


def find_replicate(pred, *keys):
    """The first replicate seed whose uniforms for these (item, event, scope key) triples satisfy pred."""
    for i in range(50000):
        rep = f"rep{i}"
        if pred(*(sm.uniform(rep, *k) for k in keys)):
            return rep
    raise AssertionError("no replicate satisfies the condition")


def paragraphs(n, prefix="Passage"):
    return "\n\n".join(f"{prefix} {i}." for i in range(1, n + 1))


# ------------------------------------------------------------------------------------------------- passages


class PassageTest(unittest.TestCase):
    MESSAGE = ("## Plan\n"
               "I will add notes to orders.\nNotes are stored as typed.\n\n"
               "- Notes are optional\n- Notes show on the receipt\n  and on the invoice\n\n"
               "| Field | Rule |\n|---|---|\n| note | optional |\n\n"
               "Shall I go ahead?")

    def test_a_stop_splits_into_headings_paragraphs_list_items_and_table_rows(self):
        ps = sm.split_stop(self.MESSAGE).passages
        self.assertEqual([p.text for p in ps], [
            "## Plan",
            "I will add notes to orders.\nNotes are stored as typed.",
            "- Notes are optional",
            "- Notes show on the receipt\n  and on the invoice",
            "| Field | Rule |\n|---|---|",  # a table's divider row belongs to the row before it
            "| note | optional |",
            "Shall I go ahead?"])
        self.assertEqual([p.number for p in ps], [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual([p.words for p in ps], [2, 11, 4, 10, 6, 5, 4])
        self.assertEqual([p.offset for p in ps], [0, 2, 13, 17, 27, 33, 38])  # new words before each passage
        self.assertEqual(sum(p.words for p in ps), sm.words(self.MESSAGE))

    def test_numbering_runs_through_the_message_then_the_plan_then_named_files(self):
        docs = [sm.plan_document("Plan para one.\n\nPlan para two."), sm.view_document("docs/a.md", "# A\n\nAlpha text.", None)]
        ps = sm.split_stop("See docs/a.md.", docs).passages
        self.assertEqual([(p.number, p.source, p.text) for p in ps], [
            (1, sm.MESSAGE_SOURCE, "See docs/a.md."), (2, "The agent's plan", "Plan para one."),
            (3, "The agent's plan", "Plan para two."), (4, "docs/a.md", "# A"), (5, "docs/a.md", "Alpha text.")])
        self.assertEqual([p.offset for p in ps], [0, 2, 5, 8, 10])

    def test_a_reread_file_contributes_only_its_added_lines(self):
        old = "# Notes\n\nNotes are optional.\n\n- one\n- two"
        new = "# Notes\n\nNotes are optional and short.\nThey are kept as typed.\n\n- one\n- two\n- three"
        d = sm.view_document("docs/n.md", new, old)
        ps = sm.split_stop("Updated docs/n.md.", [d]).passages
        self.assertEqual([p.text for p in ps], ["Updated docs/n.md.", "Notes are optional and short.\nThey are kept as typed.",
                                                "- three"])
        self.assertEqual([p.offset for p in ps], [0, 2, 12])
        self.assertEqual(sum(p.words for p in ps), sm.words("Updated docs/n.md.") + d.words)

    def test_an_unchanged_file_adds_no_passages(self):
        d = sm.view_document("d.md", "Same text.", "Same text.")
        self.assertEqual([p.text for p in sm.split_stop("Look at d.md.", [d]).passages], ["Look at d.md."])
        self.assertEqual(sm.split_stop("", []).passages, ())

    def test_a_fenced_block_is_one_passage_and_a_rule_joins_the_passage_before_it(self):
        msg = "Intro.\n\n```\ndef f():\n\n    return 1\n```\n\n---\n\nEnd."
        ps = sm.split_stop(msg).passages
        self.assertEqual([p.text for p in ps], ["Intro.", "```\ndef f():\n\n    return 1\n```\n---", "End."])
        self.assertEqual(sum(p.words for p in ps), sm.words(msg))

    def test_a_table_without_leading_pipes_splits_by_row(self):
        msg = "Fields:\n\nField | Rule\n--- | ---\nnote | optional\nprice | required\n\nOK?"
        ps = sm.split_stop(msg).passages
        self.assertEqual([p.text for p in ps], ["Fields:", "Field | Rule\n--- | ---", "note | optional", "price | required", "OK?"])
        self.assertEqual(sum(p.words for p in ps), sm.words(msg))
        # A pipe in an ordinary sentence doesn't make a table.
        self.assertEqual(len(sm.split_stop("Use a | b for either.\nThen continue.").passages), 1)

    def test_an_unclosed_fence_ends_with_its_own_document(self):
        ps = sm.split_stop("Here:\n\n```\ncode\n\nmore code", [sm.plan_document("Plan one.\n\nPlan two.")]).passages
        self.assertEqual([(p.source, p.text) for p in ps], [
            (sm.MESSAGE_SOURCE, "Here:"), (sm.MESSAGE_SOURCE, "```\ncode\n\nmore code"),
            ("The agent's plan", "Plan one."), ("The agent's plan", "Plan two.")])

    def test_the_prompt_shows_each_passage_number_at_its_start_and_only_on_new_lines(self):
        old = "# Notes\n\nNotes are optional.\n\n- one\n- two"
        new = "# Notes\n\nNotes are optional and short.\nThey are kept as typed.\n\n- one\n- two\n- three"
        d = sm.view_document("docs/n.md", new, old)
        p = sm.build_prompt(oracle=oracle(), change=script()[1], brief=BRIEF, message="Updated docs/n.md.", documents=[d])
        self.assertIn("<agent_message>\n[P1] Updated docs/n.md.\n</agent_message>", p)
        self.assertIn("+[P2] Notes are optional and short.\n+They are kept as typed.", p)
        self.assertIn("\n-Notes are optional.\n", p)  # a removed line is shown, unnumbered
        self.assertIn("\n # Notes\n", p)  # so is a line of context
        self.assertIn("+[P3] - three", p)
        self.assertEqual(sm.strip_passage_marks("[P1] Updated.\n+[P2] Added."), "Updated.\n+Added.")


# ---------------------------------------------------------------------------------------------- the rates


class RateTest(unittest.TestCase):
    def test_the_recall_table(self):
        cells = {("low", False): .10, ("low", True): .50, ("medium", False): .25, ("medium", True): .75,
                 ("high", False): .50, ("high", True): .90}
        for (tier, direct), want in cells.items():
            with self.subTest(tier=tier, direct=direct):
                self.assertAlmostEqual(sm.recall_rate(M, tier, direct=direct), want, delta=0.005)
        self.assertAlmostEqual(MED_DIRECT, 1 / (1 + math.exp(-1.1)), places=12)

    def test_one_passage_touching_more_unsaid_items_reminds_less_of_each(self):
        cells = {("low", 2): .33, ("medium", 2): .60, ("high", 2): .82, ("low", 3): .25, ("medium", 3): .50, ("high", 3): .75}
        for (tier, n), want in cells.items():
            with self.subTest(tier=tier, n=n):
                self.assertAlmostEqual(sm.recall_rate(M, tier, direct=True, n=n), want, delta=0.005)
        self.assertEqual(sm.recall_rate(sm.OwnerModel(fan_weight=0), "low", direct=True, n=3), LOW_DIRECT)

    def test_dormancy_lowers_adjacent_odds_after_the_first_build_only(self):
        on = sm.OwnerModel(dormancy=True)
        self.assertAlmostEqual(sm.recall_rate(on, "medium", direct=False, after_first_build=True), 0.17, delta=0.005)
        self.assertEqual(sm.recall_rate(on, "medium", direct=False, after_first_build=False), MED_ADJ)
        self.assertEqual(sm.recall_rate(on, "medium", direct=True, after_first_build=True), MED_DIRECT)
        self.assertEqual(sm.recall_rate(M, "medium", direct=False, after_first_build=True), MED_ADJ)  # off by default

    def test_attention_falls_with_the_words_before_a_passage_toward_the_floor(self):
        rows = {500: [1.00, .59, .39, .30, .24], 1500: [1.00, .80, .59, .45, .34], 100: [1.00, .32, .23, .21, .19]}
        for k, want in rows.items():
            mk = sm.OwnerModel(drag=0, half_words=k)
            for w, x in zip((0, 500, 1500, 3000, 6000), want):
                with self.subTest(k=k, w=w):
                    self.assertAlmostEqual(sm.attention(mk, w=w, read_before=0), x, delta=0.006)
        self.assertAlmostEqual(sm.attention(sm.OwnerModel(drag=0), w=10**9, read_before=0), 0.18, places=5)
        kept = [.80, .47, .31, .24, .19]  # a contradiction kept: attention times q = 0.8
        for w, x in zip((0, 500, 1500, 3000, 6000), kept):
            self.assertAlmostEqual(0.8 * sm.attention(sm.OwnerModel(drag=0), w=w, read_before=0), x, delta=0.006)

    def test_session_drag_is_mild(self):
        self.assertAlmostEqual(sm.attention(M, w=0, read_before=0), 1.0, places=12)
        self.assertAlmostEqual(sm.attention(M, w=0, read_before=22 * 238), 1 - 0.15 * (1 - math.exp(-1)), places=12)
        self.assertAlmostEqual(sm.attention(M, w=0, read_before=10**8), 0.85, places=6)


# ------------------------------------------------------------------------------------------- the constants


class OwnerModelTest(unittest.TestCase):
    def test_the_defaults_are_the_designs_central_values(self):
        self.assertEqual(
            (M.floor, M.half_words, M.drag, M.drag_minutes, M.words_per_minute, M.catch, M.recall_intercept, M.tier_spacing,
             M.direct_weight, M.fan_weight, M.dormancy, M.dormancy_odds, M.scope, M.counting),
            (0.18, 500, 0.15, 22, 238, 0.8, -1.1, 1.1, 2.2, 1.0, False, 0.6, "change", "stop"))

    def test_the_pilot_preset(self):
        p = sm.OwnerModel.pilot()
        self.assertEqual((p.floor, p.catch, p.half_words, p.drag, p.counting), (0, 1, 1500, 0, "pilot"))
        self.assertEqual(sm.OwnerModel.from_config({"preset": "pilot"}), p)

    def test_configs_choose_presets_and_override_fields(self):
        self.assertEqual(sm.OwnerModel.from_config(None), M)
        self.assertEqual(sm.OwnerModel.from_config({"preset": "pilot", "scope": "stop"}).scope, "stop")
        m = sm.OwnerModel.from_config({"half_words": 100, "catch": 0.6, "counting": "change", "scope": "trajectory"})
        self.assertEqual((m.half_words, m.catch, m.counting, m.scope, m.floor), (100, 0.6, "change", "trajectory", 0.18))
        self.assertEqual(sm.OwnerModel.from_config(json.loads(json.dumps(dataclasses.asdict(m)))), m)  # what a run records
        for bad in ({"k": 3}, {"scope": "week"}, {"counting": "page"}, {"preset": "nope"}, {"catch": 1.5},
                    {"broad_uniform": "other"}):
            with self.subTest(bad), self.assertRaises(ValueError):
                sm.OwnerModel.from_config(bad)


# ------------------------------------------------------------------------------------------------- the draws


class DrawTest(unittest.TestCase):
    def setUp(self):
        self.c = script()

    def test_a_uniform_is_keyed_on_the_replicate_item_event_and_scope(self):
        u = sm.uniform("rep", "BK-02", "recall", "change-1")
        self.assertEqual(u, sm.uniform("rep", "BK-02", "recall", "change-1"))
        self.assertTrue(0 <= u < 1)
        for other in (("rep2", "BK-02", "recall", "change-1"), ("rep", "BK-09", "recall", "change-1"),
                      ("rep", "BK-02", "contradiction", "change-1"), ("rep", "BK-02", "broad", "change-1"),
                      ("rep", "BK-02", "recall", "change-2")):
            self.assertNotEqual(u, sm.uniform(*other))

    def test_scope_keys_name_the_stop_change_or_trajectory_and_nothing_else(self):
        c1 = self.c[1]
        self.assertEqual(sm.scope_key("change", c1, 4), sm.scope_key("change", c1, 0))
        self.assertNotEqual(sm.scope_key("stop", c1, 4), sm.scope_key("stop", c1, 0))
        self.assertEqual(sm.scope_key("trajectory", c1, 4), sm.scope_key("trajectory", self.c[4], 0))
        self.assertNotEqual(sm.scope_key("change", sm.parse_probe(CHANGES, 1), 0), sm.scope_key("change", c1, 0))

    def test_draws_dont_depend_on_the_turn_or_the_text(self):
        o = out("approval", touches=[touch("BK-02", 1, "adjacent")])
        a, _ = owner("diligent", copy.deepcopy(o), replicate="same")
        a.start_change(self.c[1])
        ra = a.respond("Orders are taken all day.", code_written=False)
        b, _ = owner("diligent", out("stop"), out("stop"), copy.deepcopy(o), replicate="same")
        b.start_change(self.c[1])
        b.respond("Working.", code_written=False)
        b.respond("Still working on it.", code_written=False)
        rb = b.respond("Here is quite different text about when orders arrive. OK?", code_written=False)
        ua = [d["u"] for d in ra.draws if d["item"] == "BK-02"]
        self.assertEqual(ua, [d["u"] for d in rb.draws if d["item"] == "BK-02"])
        self.assertEqual(ua, [sm.uniform("same", "BK-02", "recall", key(self.c[1]))])

    def test_a_correction_tied_to_no_item_is_keyed_on_its_quoted_words(self):
        k = sm.contradiction_key
        none = lambda wrong, passage=1: {"item": "none", "passage": passage, "wrong": wrong}
        self.assertEqual(k(none("Orders  are\nkept a Week")), k(none("orders are kept a week")))
        self.assertNotEqual(k(none("orders are kept a week")), k(none("orders are kept a month")))
        self.assertEqual(k({"item": "BK-03", "passage": 1, "wrong": "anything"}), k({"item": "BK-03", "passage": 2, "wrong": "else"}))

    def test_something_left_out_and_tied_to_no_item_is_keyed_on_a_constant(self):
        k = sm.contradiction_key
        self.assertEqual(k({"item": "none", "passage": 0, "wrong": "the note field"}),
                         k({"item": "none", "passage": 0, "wrong": "notes, which I asked for"}))
        self.assertNotEqual(k({"item": "none", "passage": 0, "wrong": "x"}), k({"item": "none", "passage": 1, "wrong": "x"}))

    def test_one_item_contradicted_at_two_stops_and_passages_shares_one_uniform(self):
        w, _ = owner("bounded", out("approval", corrections=[cor("BK-03", "Keep every order.", passage=1)]),
                     out("approval", corrections=[cor("BK-03", "Keep them all.", wrong="purge", passage=2)]))
        w.start_change(self.c[1])
        u1 = w.respond("Delete old orders.", code_written=False).draws[0]["u"]
        u2 = w.respond("More words here.\n\nPurge orders yearly.", code_written=False).draws[0]["u"]
        self.assertEqual(u1, u2)
        self.assertEqual(u1, sm.uniform("s1", "BK-03", "contradiction", key(self.c[1])))

    def test_n_counts_the_unsaid_items_touching_the_same_passage(self):
        both = out("approval", touches=[touch("BK-02", 1), touch("BK-09", 1)])
        w, _ = owner("diligent", both, replicate="fan")
        w.start_change(self.c[1])
        rates = {d["item"]: d["r"] for d in w.respond("Orders and notes.", code_written=False).draws}
        self.assertEqual(rates, {"BK-02": sm.recall_rate(M, "medium", direct=True, n=2),
                                 "BK-09": sm.recall_rate(M, "low", direct=True, n=2)})
        # An item the passage already states doesn't count, and neither does one the owner has disclosed.
        w, _ = owner("diligent", out("approval", touches=[touch("BK-02", 1, "says"), touch("BK-09", 1)]))
        w.start_change(self.c[1])
        self.assertEqual([d["r"] for d in w.respond("Orders and notes.", code_written=False).draws], [LOW_DIRECT])
        w, _ = owner("diligent", copy.deepcopy(both))
        w.disclosed.add("BK-02")
        w.start_change(self.c[1])
        self.assertEqual([(d["item"], d["r"]) for d in w.respond("Orders and notes.", code_written=False).draws],
                         [("BK-09", LOW_DIRECT)])

    def test_bounded_recall_is_attention_times_the_capped_rate(self):
        msg = "\n\n".join(["filler " * 300] * 5 + ["Refunds go through the till.", "Notes go in a text field."])
        o = out("approval", touches=[touch("BK-07", 6), touch("BK-09", 7)])
        w, _ = owner("bounded", o)
        w.start_change(self.c[5])
        draws = {d["item"]: d for d in w.respond(msg, code_written=False).draws}
        a6 = sm.attention(M, w=1500, read_before=1500)
        a7 = sm.attention(M, w=1505, read_before=1505)
        self.assertAlmostEqual(draws["BK-07"]["p"], a6 * min(sm.recall_rate(M, "high", direct=True), 0.8))  # the cap binds
        self.assertAlmostEqual(draws["BK-09"]["p"], a7 * LOW_DIRECT)  # it doesn't
        self.assertLess(draws["BK-07"]["p"], 0.5)

    def test_dormancy_applies_on_review_after_the_first_build_and_at_a_probe(self):
        on = sm.OwnerModel(dormancy=True)
        o = out("approval", touches=[touch("BK-02", 1, "adjacent"), touch("BK-09", 2, "direct")])
        dormant = sm.recall_rate(on, "medium", direct=False, after_first_build=True)
        for change, adjacent in ((sm.first_build(BRIEF), MED_ADJ), (self.c[1], dormant), (sm.parse_probe(CHANGES, 0), dormant)):
            with self.subTest(change.number, probe=change.probe):
                w, _ = owner("diligent", copy.deepcopy(o), model=on, replicate="never")
                w.start_change(change)
                rates = {d["item"]: d["r"] for d in w.respond("Orders all day.\n\nNotes in a field.", code_written=False).draws}
                self.assertEqual(rates, {"BK-02": adjacent, "BK-09": LOW_DIRECT})

    def test_dormancy_on_broad_questions_follows_its_setting(self):
        q = out("questions", [broad("Anything else?", ["BK-09"])])
        dormant = sm.recall_rate(sm.OwnerModel(dormancy=True), "low", direct=False, after_first_build=True)
        for setting, want in ((True, dormant), (False, LOW_ADJ)):
            with self.subTest(setting):
                w, _ = owner("diligent", copy.deepcopy(q), model=sm.OwnerModel(dormancy=True, dormancy_on_broad=setting))
                w.start_change(self.c[1])
                self.assertEqual(w.respond("Anything else?", code_written=False).draws[0]["r"], want)

    def test_an_item_a_passage_states_gets_no_recall_draw_at_that_stop(self):
        w, _ = owner("diligent", out("approval", touches=[touch("BK-09", 1, "says"), touch("BK-09", 2, "direct")]))
        w.start_change(self.c[1])
        self.assertEqual(w.respond("Notes are kept as typed.\n\nNotes go in a field.", code_written=False).draws, [])

    def test_a_correction_repeated_word_for_word_is_said_once(self):
        o = out("approval", corrections=[cor("BK-03", "Keep every order.", passage=1), cor("BK-03", "Keep every order.", passage=2),
                                         cor("BK-03", "Never purge orders.", passage=2)])
        w, _ = owner("diligent", o)
        w.start_change(self.c[1])
        r = w.respond("Delete old orders.\n\nAlso delete them yearly.", code_written=False)
        self.assertEqual([c["text"] for c in r.kept], ["Keep every order.", "Never purge orders."])
        self.assertEqual(r.reply, "Keep every order.\n\nNever purge orders.\n\nOtherwise, go ahead.")

    def test_recall_happens_at_the_first_passage_whose_probability_exceeds_u(self):
        rep = find_replicate(lambda u: MED_ADJ < u < MED_DIRECT, ("BK-02", "recall", key(self.c[1])))
        o = out("approval", touches=[touch("BK-02", 1, "adjacent"), touch("BK-02", 2, "adjacent"),
                                     touch("BK-02", 3, "direct"), touch("BK-02", 4, "direct")])
        w, _ = owner("diligent", o, replicate=rep)
        w.start_change(self.c[1])
        r = w.respond(paragraphs(4), code_written=False)
        self.assertEqual([(x["item"], x["passage"]) for x in r.recalled], [("BK-02", 3)])
        self.assertEqual([(d["passage"], d["fired"]) for d in r.draws if d["item"] == "BK-02"], [(1, False), (2, False), (3, True)])

    def test_more_passages_of_the_same_strength_buy_nothing(self):
        rep = find_replicate(lambda u: MED_ADJ < u, ("BK-02", "recall", key(self.c[1])))
        many = out("approval", touches=[touch("BK-02", i, "adjacent") for i in range(1, 21)])
        w, _ = owner("diligent", copy.deepcopy(many), copy.deepcopy(many), replicate=rep)
        w.start_change(self.c[1])
        self.assertEqual(w.respond(paragraphs(20), code_written=False).recalled, [])
        self.assertEqual(w.respond(paragraphs(20, "Again"), code_written=False).recalled, [])  # nor does showing it again

    def test_a_stop_scope_draws_afresh_at_each_stop_and_a_change_scope_once_per_change(self):
        c1 = self.c[1]
        rep = find_replicate(lambda s0, s1, ch: s0 > MED_ADJ > s1 and ch > MED_ADJ,
                             ("BK-02", "recall", key(c1, "stop", 0)), ("BK-02", "recall", key(c1, "stop", 1)),
                             ("BK-02", "recall", key(c1)))
        o = out("approval", touches=[touch("BK-02", 1, "adjacent")])
        for scope, second in (("stop", ["BK-02"]), ("change", [])):
            with self.subTest(scope):
                w, _ = owner("diligent", copy.deepcopy(o), copy.deepcopy(o), replicate=rep, model=sm.OwnerModel(scope=scope))
                w.start_change(c1)
                self.assertEqual(w.respond("Orders come in all day.", code_written=False).recalled, [])
                self.assertEqual([x["item"] for x in w.respond("Orders come in all day.", code_written=False).recalled], second)

    def test_a_trajectory_scope_draws_once_for_the_whole_trajectory(self):
        c1, c4 = self.c[1], self.c[4]
        rep = find_replicate(lambda a, b, t: a > MED_ADJ > b and t > MED_ADJ, ("BK-02", "recall", key(c1)),
                             ("BK-02", "recall", key(c4)), ("BK-02", "recall", key(c1, "trajectory")))
        o = out("approval", touches=[touch("BK-02", 1, "adjacent")])
        for scope, at_change_4 in (("change", ["BK-02"]), ("trajectory", [])):
            with self.subTest(scope):
                w, _ = owner("diligent", copy.deepcopy(o), copy.deepcopy(o), replicate=rep, model=sm.OwnerModel(scope=scope))
                w.start_change(c1)
                self.assertEqual(w.respond("Orders come in all day.", code_written=False).recalled, [])
                w.end_change()
                w.start_change(c4)
                self.assertEqual([x["item"] for x in w.respond("Orders come in all day.", code_written=False).recalled], at_change_4)

    def test_diligent_keeps_at_least_what_bounded_keeps_and_bounded_at_least_what_rubber_stamp_keeps(self):
        msg = "\n\n".join(["filler " * 300] * 5 + ["Delete old orders.", "Orders close at five.", "Notes go in a text field."])
        o = out("approval", corrections=[cor("BK-03", "Keep every order.", passage=6), cor("BK-02", "We close at six.", passage=7)],
                touches=[touch("BK-09", 8, "direct")])
        differ = 0
        for i in range(60):
            got = {}
            for policy in sm.POLICIES:
                w, _ = owner(policy, copy.deepcopy(o), replicate=f"p{i}")
                w.start_change(self.c[1])
                r = w.respond(msg, code_written=False)
                got[policy] = {c["item"] for c in r.kept} | {x["item"] for x in r.recalled}
            self.assertEqual(got["rubber-stamp"], set())
            self.assertLessEqual(got["bounded"], got["diligent"])
            self.assertIn("BK-03", got["diligent"])  # the diligent owner keeps every contradiction
            differ += got["bounded"] != got["diligent"]
        self.assertGreater(differ, 0)

    def test_the_bounded_owner_never_recalls_likelier_than_it_catches(self):
        o = out("approval", touches=[touch("BK-07", 1, "direct")])  # BK-07 is high tier: 0.90 on a direct touch
        ps = {}
        for policy in ("diligent", "bounded"):
            w, _ = owner(policy, copy.deepcopy(o))
            w.start_change(self.c[5])
            ps[policy] = w.respond("Refunds are sent by the payment service.", code_written=False).draws[0]["p"]
        self.assertAlmostEqual(ps["diligent"], sm.recall_rate(M, "high", direct=True))
        self.assertAlmostEqual(ps["bounded"], 0.8)

    def test_disclosure_ends_drawing(self):
        w, ask = owner("diligent", out("questions", [ans("Closing time?", "Six in the evening.", ["BK-02"])]),
                       out("approval", touches=[touch("BK-02", 1, "direct")]), replicate="any")
        w.start_change(self.c[1])
        w.respond("When do you stop taking orders?", code_written=False)
        self.assertIn("BK-02", w.disclosed)
        r = w.respond("Orders are accepted until closing.", code_written=False)
        self.assertEqual(r.draws, [])
        self.assertIn("[BK-02] (Askable; mentioned to the agent)", ask.prompts[1])

    def test_a_recalled_item_is_never_drawn_for_again(self):
        c1, c4 = self.c[1], self.c[4]
        rep = find_replicate(lambda u: u < MED_DIRECT, ("BK-02", "recall", key(c1)))
        o = out("approval", touches=[touch("BK-02", 1, "direct")])
        w, _ = owner("diligent", copy.deepcopy(o), copy.deepcopy(o), copy.deepcopy(o), replicate=rep)
        w.start_change(c1)
        self.assertEqual([x["item"] for x in w.respond("Orders come in all day.", code_written=False).recalled], ["BK-02"])
        self.assertEqual(w.respond("Orders come in all day.", code_written=False).draws, [])
        w.end_change()
        w.start_change(c4)
        self.assertEqual(w.respond("Orders come in all day.", code_written=False).draws, [])

    def test_the_rubber_stamp_owner_keeps_no_contradiction_and_recalls_nothing_on_review(self):
        o = out("approval", corrections=[cor("BK-03", "Keep every order.")], touches=[touch("BK-09", 2, "direct")])
        for i in range(20):
            w, _ = owner("rubber-stamp", copy.deepcopy(o), replicate=f"rs{i}")
            w.start_change(self.c[1])
            r = w.respond("Delete old orders.\n\nNotes go in a text field.", code_written=False)
            self.assertEqual((r.kept, r.recalled, r.reply), ([], [], "That looks fine. Go ahead."))

    def test_how_w_is_counted(self):
        o2 = out("approval", corrections=[cor("BK-03", "Keep every order.", passage=2),
                                          cor("none", "Notes are part of what I asked for.", wrong="notes", passage=0)])
        for counting, want in (("stop", [3, 6]), ("change", [303, 306]), ("pilot", [306, 306])):
            with self.subTest(counting):
                w, _ = owner("bounded", out("stop"), copy.deepcopy(o2), model=sm.OwnerModel(counting=counting))
                w.start_change(self.c[1])
                w.respond("alpha " * 300, code_written=False)
                r = w.respond("Intro words here.\n\nDelete old orders.", code_written=False)
                self.assertEqual([d["w"] for d in r.draws], want)
                self.assertEqual([d["read_before"] for d in r.draws], [303, 306])

    def test_the_pilot_reproduces_the_placeholders_bounded_probabilities_exactly(self):
        msgs = ["word " * 700 + "\n\nDelete old orders.", "Plan:\n\nDelete orders after a year.\n\n" + "more " * 2000]
        outs = [out("approval", corrections=[cor("BK-03", "Keep every order.", passage=2)]),
                out("approval", corrections=[cor("BK-03", "Keep every order.", passage=1),
                                             cor("none", "Keep the notes too.", wrong="drop notes", passage=3)])]
        w, _ = owner("bounded", *outs, model=sm.OwnerModel.pilot())
        w.start_change(self.c[1])
        for m in msgs:
            r = w.respond(m, code_written=False)
            for c in r.kept + r.dropped:
                self.assertEqual(c["p"], sm.catch_probability("bounded", w.words_this_change))


# ----------------------------------------------------------------------------------------- broad questions


class BroadQuestionTest(unittest.TestCase):
    def setUp(self):
        self.c = script()

    def test_a_broad_question_is_answered_by_recall_draws_the_same_under_every_policy(self):
        rep = find_replicate(lambda u: u < LOW_ADJ, ("BK-09", "broad", key(self.c[1])))
        for policy in sm.POLICIES:
            with self.subTest(policy):
                w, _ = owner(policy, out("questions", [broad("Anything else about notes?", ["BK-09"])]), replicate=rep)
                w.start_change(self.c[1])
                r = w.respond("Anything else about notes I should know?", code_written=False)
                self.assertEqual(r.reply, RECALL["BK-09"] + "\n\nGo ahead.")
                self.assertEqual(r.answers[0]["items"], ["BK-09"])
                self.assertEqual(r.shared, [{"item": "BK-09", "reason": "recalled", "via": "question"}])
                self.assertEqual(w.said_now, [sm.Said(1, RECALL["BK-09"], "Anything else about notes?", ("BK-09",))])
                self.assertIn("BK-09", w.disclosed)

    def test_when_nothing_is_recalled_the_answer_is_nothing_else_comes_to_mind(self):
        rep = find_replicate(lambda u: u > LOW_ADJ, ("BK-09", "broad", key(self.c[1])))
        w, _ = owner("diligent", out("questions", [broad("Anything else?", ["BK-09"]), broad("Any edge cases?")]), replicate=rep)
        w.start_change(self.c[1])
        r = w.respond("Anything else? Any edge cases?", code_written=False)
        self.assertEqual([a["answer"] for a in r.answers], [sm.NOTHING_ELSE, sm.NOTHING_ELSE])
        self.assertEqual(r.shared, [])
        self.assertEqual(w.said_now, [sm.Said(1, sm.NOTHING_ELSE, "Anything else?", ()), sm.Said(1, sm.NOTHING_ELSE, "Any edge cases?", ())])
        self.assertNotIn("BK-09", w.disclosed)

    def test_attention_doesnt_apply_and_each_item_draws_alone(self):
        probe = sm.parse_probe(CHANGES, 1)  # every item is in play at a probe
        w, _ = owner("bounded", out("questions", [broad("Anything else I should know?", ["BK-02", "BK-09"])]))
        w.start_change(probe)
        r = w.respond("filler " * 5000 + "\n\nAnything else I should know?", code_written=False)
        self.assertEqual({d["item"]: d["p"] for d in r.draws}, {"BK-02": MED_ADJ, "BK-09": LOW_ADJ})
        self.assertTrue(all(d["event"] == "broad" for d in r.draws))

    def test_asking_again_in_the_same_change_buys_nothing(self):
        rep = find_replicate(lambda u: u > LOW_ADJ, ("BK-09", "broad", key(self.c[1])))
        q = out("questions", [broad("Anything else?", ["BK-09"])])
        w, _ = owner("diligent", copy.deepcopy(q), copy.deepcopy(q), replicate=rep)
        w.start_change(self.c[1])
        first, second = (w.respond("Anything else?", code_written=False) for _ in range(2))
        self.assertEqual((first.answers[0]["answer"], second.answers[0]["answer"]), (sm.NOTHING_ELSE, sm.NOTHING_ELSE))
        self.assertEqual(first.draws[0]["u"], second.draws[0]["u"])

    def test_the_models_own_words_for_a_broad_question_are_discarded(self):
        rep = find_replicate(lambda u: u > LOW_ADJ, ("BK-09", "broad", key(self.c[1])))
        o = out("questions", [broad("Anything about notes?", ["BK-09"], answer="Notes are kept exactly as typed, spaces too.")])
        o["answers"][0]["items"] = ["BK-09"]
        w, _ = owner("diligent", o, replicate=rep)
        w.start_change(self.c[1])
        r = w.respond("Anything about notes?", code_written=False)
        self.assertNotIn("spaces", r.reply)
        self.assertEqual(r.reply, sm.NOTHING_ELSE + "\n\nGo ahead.")

    def test_review_recall_is_drawn_before_a_broad_question_in_the_same_stop(self):
        rep = find_replicate(lambda r, b: r < LOW_DIRECT and b < LOW_ADJ,
                             ("BK-09", "recall", key(self.c[1])), ("BK-09", "broad", key(self.c[1])))
        o = out("questions", [broad("Anything else?", ["BK-09"])], touches=[touch("BK-09", 1, "direct")])
        w, _ = owner("diligent", o, replicate=rep)
        w.start_change(self.c[1])
        r = w.respond("Notes go in a text field.\n\nAnything else?", code_written=False)
        self.assertEqual([(x["item"], x["via"]) for x in r.recalled], [("BK-09", "review")])
        self.assertEqual(r.answers[0]["answer"], sm.NOTHING_ELSE)
        self.assertEqual(r.reply, f"{sm.NOTHING_ELSE}\n\n{RECALL['BK-09']}\n\nOtherwise, go ahead.")


# --------------------------------------------------------------------------------------------- the reply


class RecallReplyTest(unittest.TestCase):
    def setUp(self):
        self.c = script()
        self.rep = find_replicate(lambda u: u < LOW_DIRECT, ("BK-09", "recall", key(self.c[1])))

    def test_recall_lines_are_added_verbatim_after_the_trim_which_never_sees_them(self):
        trims = []

        def trim(prompt):
            trims.append(prompt)
            return {"parts": [{"index": 1, "text": "Keep every order."}]}
        o = out("approval", corrections=[cor("BK-03", "Keep every order we have ever taken.", wrong="delete old orders")],
                touches=[touch("BK-09", 2, "direct")])
        w, _ = owner("diligent", o, replicate=self.rep, trim=trim)
        w.start_change(self.c[1])
        r = w.respond("Plan: delete old orders.\n\nNotes go in a text field.", code_written=False)
        self.assertEqual(r.reply, f"Keep every order.\n\n{RECALL['BK-09']}\n\nOtherwise, go ahead.")
        self.assertNotIn(RECALL["BK-09"], trims[0])
        self.assertEqual(r.recalled, [{"item": "BK-09", "line": RECALL["BK-09"], "via": "review", "passage": 2, "question": None}])
        self.assertIn({"item": "BK-09", "reason": "recalled", "via": "review"}, r.shared)
        self.assertIn(sm.Said(1, RECALL["BK-09"], None, ("BK-09",)), w.said_now)
        self.assertEqual(w.disclosed, {"BK-03", "BK-09"})

    def test_a_recall_at_a_completion_report_keeps_the_change_open(self):
        w, _ = owner("diligent", out("completion", touches=[touch("BK-09", 1, "direct")]), replicate=self.rep)
        w.start_change(self.c[1])
        r = w.respond("Done: notes go in a text field.", code_written=True)
        self.assertFalse(r.finished)
        self.assertEqual(r.reply, f"{RECALL['BK-09']}\n\nOtherwise, go ahead.")

    def test_at_a_redirect_stop_touches_and_contradictions_come_from_the_second_call(self):
        c2 = self.c[2]
        rep = find_replicate(lambda u: u < MED_DIRECT, ("BK-02", "recall", key(c2)))
        first = out("approval", corrections=[cor("BK-03", "Keep every order.")], touches=[touch("BK-02", 2, "direct")])
        w, ask = owner("diligent", first, out("approval"), replicate=rep)
        w.start_change(c2)
        r = w.respond("Plan: free deliveries, and delete old orders.\n\nOrders are taken until late. OK?", code_written=False)
        self.assertEqual(len(ask.prompts), 2)
        self.assertEqual(r.redirect_event, "delivered")
        self.assertEqual((r.kept, r.recalled, r.draws), ([], [], []))
        self.assertEqual(r.reply, "Actually, deliveries should cost 3 pounds.\n\nPut the fee on the order.\n\nOtherwise, go ahead.")


# ---------------------------------------------------------------------------------------- checking output


class CheckOutputTest(unittest.TestCase):
    def failure(self, o, change=1, message="One.\n\nTwo."):
        w, _ = owner("diligent", o, o, o)
        w.start_change(script()[change])
        with self.assertRaises(sm.OwnerFailed) as cm:
            w.respond(message, code_written=False)
        return str(cm.exception)

    def test_structural_faults_are_retried_and_then_refused(self):
        cases = {
            "passage 3": out("approval", corrections=[cor("BK-03", "Keep every order.", passage=3)]),
            "passage 5": out("approval", touches=[touch("BK-02", 5)]),
            "passage 0": out("approval", touches=[touch("BK-02", 0)]),
            "level 'strong'": out("approval", touches=[touch("BK-02", 1, "strong")]),
            "passage number": out("approval", corrections=[cor("BK-03", "See [P1]: keep every order.")]),
            "rule identifier": out("approval", corrections=[cor("BK-03", "As BK-03 says, keep every order.")]),
            "empty correction": out("approval", corrections=[cor("BK-03", "  ")]),
            "breadth": out("questions", [ans("Closing time?", "Six.", ["BK-02"], breadth="wide")]),
        }
        for why, o in cases.items():
            with self.subTest(why):
                self.assertIn(why, self.failure(o))

    def test_a_correction_without_a_passage_is_refused(self):
        o = out("approval", corrections=[{"item": "BK-03", "wrong": "delete", "text": "Keep every order."}])
        self.assertIn("passage", self.failure(o))

    def test_valid_output_passes_and_a_bad_one_is_retried(self):
        bad = out("approval", touches=[touch("BK-02", 9)])
        good = out("approval", corrections=[cor("none", "Notes are what I asked for.", wrong="notes", passage=0)],
                   touches=[touch("BK-02", 1, "says"), touch("BK-09", 2, "adjacent"), touch("BK-09", 2, "adjacent")])
        w, ask = owner("diligent", bad, good)
        w.start_change(script()[1])
        r = w.respond("One.\n\nTwo.", code_written=False)
        self.assertEqual(len(ask.prompts), 2)
        self.assertTrue(r.calls[0]["problems"])
        self.assertEqual((r.calls[1]["problems"], r.calls[1]["repairs"]), ([], []))

    def repaired(self, o, change=1, message="One.\n\nTwo."):
        """Respond once with o; it must be repaired, not retried. Returns (reply, repairs)."""
        w, ask = owner("diligent", o, o, o)
        w.start_change(script()[change])
        r = w.respond(message, code_written=False)
        self.assertEqual(len(ask.prompts), 1)
        self.assertEqual(r.calls[0]["problems"], [])
        self.assertTrue(r.calls[0]["repairs"])
        return r, r.calls[0]["repairs"]

    def test_deterministic_slips_are_repaired_and_logged_without_a_retry(self):
        for item in ("BK-01", "BK-03", "BK-07"):  # stated, recognized on sight, not yet held
            with self.subTest(item):
                r, repairs = self.repaired(out("approval", touches=[touch(item, 1)]))
                self.assertEqual(r.draws, [])
                self.assertIn(item, repairs[0])
        r, repairs = self.repaired(out("approval", corrections=[cor("BK-02", "We close at six.", passage=2)],
                                       touches=[touch("BK-02", 2), touch("BK-02", 1, "adjacent")]))
        self.assertEqual([(d["event"], d["passage"]) for d in r.draws], [("contradiction", 2)])  # passage 1's touch stays,
        self.assertEqual([c["item"] for c in r.kept], ["BK-02"])  # but the item is disclosed by its correction
        r, repairs = self.repaired(out("questions", [broad("Anything else?", ["BK-02", "BK-01", "BK-09"])]))
        self.assertEqual(r.answers[0]["in_scope"], ["BK-09"])  # BK-02 isn't in play at change 1; BK-01 isn't askable
        self.assertEqual(len(repairs), 2)
        r, repairs = self.repaired(out("approval", corrections=[cor("BK-02", "We close at six.", passage=0)]))
        self.assertEqual((r.kept, r.dropped, r.reply), ([], [], "That looks fine. Go ahead."))

    def test_two_levels_for_one_item_and_passage_keep_the_weaker(self):
        for levels, kept in ((("direct", "adjacent"), "adjacent"), (("says", "direct"), "says"), (("adjacent", "says"), "says")):
            with self.subTest(levels):
                r, repairs = self.repaired(out("approval", touches=[touch("BK-09", 1, levels[0]), touch("BK-09", 1, levels[1])]))
                if kept == "says":
                    self.assertEqual(r.draws, [])
                else:
                    self.assertEqual(r.draws[0]["r"], LOW_ADJ)

    def test_a_left_out_correction_may_cite_only_this_changes_request_or_none(self):
        # Change 3 asked for BK-10: kept. BK-01 was stated at the start, not in this change's request: dropped, logged.
        w, ask = owner("diligent", out("approval", corrections=[cor("BK-10", "Keep the order number.", wrong="number", passage=0),
                                                                cor("BK-01", "Record the customer.", wrong="customer", passage=0)]))
        w.start_change(script()[3])
        r = w.respond("Plan: move the order. OK?", code_written=False)
        self.assertEqual([c["item"] for c in r.kept], ["BK-10"])
        self.assertEqual(len(ask.prompts), 1)
        self.assertTrue(any("BK-01" in x for x in r.calls[0]["repairs"]))
        # At the first build the request is the brief, so its stated items may be pointed out as missing.
        w, _ = owner("diligent", out("approval", corrections=[cor("BK-01", "Record the customer.", wrong="customer", passage=0)]))
        w.start_change(sm.first_build(BRIEF))
        self.assertEqual([c["item"] for c in w.respond("Plan: orders. OK?", code_written=False).kept], ["BK-01"])
        # A probe's request names no oracle item.
        w, _ = owner("diligent", out("approval", corrections=[cor("BK-01", "Record the customer.", wrong="customer", passage=0)]))
        w.start_change(sm.parse_probe(CHANGES, 1))
        self.assertEqual(w.respond("Plan: list orders. OK?", code_written=False).kept, [])

    def test_a_trim_drop_is_ignored_for_a_requested_item_even_at_the_first_build(self):
        o = out("approval", corrections=[cor("BK-01", "Record the customer.", wrong="customer", passage=0)])
        w, _ = owner("diligent", o, trim=lambda p: {"parts": [{"index": 1, "text": "DROP"}]})
        w.start_change(sm.first_build(BRIEF))
        self.assertEqual([c["item"] for c in w.respond("Plan: orders. OK?", code_written=False).kept], ["BK-01"])

    def test_the_trim_still_guards_a_left_out_correction_tied_to_no_item(self):
        o = out("approval", corrections=[cor("none", "Also keep it short.", wrong="length", passage=0)])
        w, _ = owner("diligent", o, trim=lambda p: {"parts": [{"index": 1, "text": "DROP"}]})
        w.start_change(script()[1])
        r = w.respond("Plan: notes. OK?", code_written=False)
        self.assertEqual((r.kept, r.reply), ([], "That looks fine. Go ahead."))

    def test_identifiers_are_the_oracles_own(self):
        pattern = sm.id_pattern(oracle().ids())
        self.assertTrue(pattern.search("as BK-12 says"))
        for text in ("UTC-5", "ISO-8601", "Room B-12"):
            self.assertIsNone(pattern.search(text), text)
        w, ask = owner("diligent", out("questions", [ans("Which zone?", "We work in UTC-5, dates in ISO-8601.", ["BK-02"])]))
        w.start_change(script()[1])
        self.assertEqual(w.respond("Which zone?", code_written=False).calls[0]["problems"], [])
        self.assertIn("Ships at UTC-5.", sm.owner_text("Ships at UTC-5. Graded under BK-02.", pattern))
        self.assertNotIn("Graded", sm.owner_text("Ships at UTC-5. Graded under BK-02.", pattern))
        data = {**OWNER_ITEMS, "BK-02": {"tier": "medium", "recall": "We stop at six, UTC-5."}}
        self.assertEqual(sm.parse_owner_items(data, oracle())["BK-02"].recall, "We stop at six, UTC-5.")


# ---------------------------------------------------------------------------- clarifications settle items


class ClarificationSettlesTest(unittest.TestCase):
    """Change 3's late clarification settles BK-02 in the fixture: once it is delivered, or found already settled, the
    item is disclosed and no recall line for it can follow, in that reply or later."""

    def setUp(self):
        self.c3 = script()[3]
        # Draws that would recall BK-02 both on review and from a broad question, if they were made.
        self.rep = find_replicate(lambda r, b: r < MED_DIRECT and b < MED_ADJ,
                                  ("BK-02", "recall", key(self.c3)), ("BK-02", "broad", key(self.c3)))

    def test_a_delivered_clarification_discloses_what_it_settles(self):
        done = out("completion", [broad("Anything else?", ["BK-02"])], touches=[touch("BK-02", 1)])
        w, _ = owner("diligent", out("approval"), done, out("approval", touches=[touch("BK-02", 1)]), replicate=self.rep)
        w.start_change(self.c3)
        w.respond("Plan: move orders. OK?", code_written=False)
        r = w.respond("Done: orders are taken until late. Anything else?", code_written=True)
        self.assertEqual(r.redirect_event, "delivered")
        self.assertIn("BK-02", w.disclosed)
        self.assertEqual([d for d in r.draws if d["item"] == "BK-02"], [])
        self.assertNotIn(RECALL["BK-02"], r.reply)
        self.assertEqual(r.reply, f'By "move" I mean keep the same order number.\n\n{sm.NOTHING_ELSE}\n\nOtherwise, go ahead.')
        self.assertIn({"item": "BK-02", "reason": "redirect"}, r.shared)
        self.assertEqual(w.respond("Orders are taken until late.", code_written=True).draws, [])  # nor later

    def test_a_clarification_found_already_settled_discloses_what_it_settles(self):
        o = out("questions", [ans("Keep the number?", "Yes.", ["BK-10"])], settled=True, touches=[touch("BK-02", 1)])
        w, _ = owner("diligent", o, replicate=self.rep)
        w.start_change(self.c3)
        r = w.respond("Orders are taken until late. Should a moved order keep its number?", code_written=False)
        self.assertEqual(r.redirect_event, "settled")
        self.assertIn("BK-02", w.disclosed)
        self.assertEqual(r.draws, [])
        self.assertIn({"item": "BK-02", "reason": "settled"}, r.shared)

    def test_a_clarification_must_settle_items_the_oracle_has(self):
        bad = sm.parse_change_script(CHANGES.replace("**Redirect settles:** BK-02.", "**Redirect settles:** BK-99."))
        w, _ = owner()
        with self.assertRaisesRegex(ValueError, "BK-99"):
            w.start_change(bad[3])


# ------------------------------------------------------------------------------------------- owner items


class OwnerItemsTest(unittest.TestCase):
    def test_owner_items_load_from_the_seeds_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "owner-items.json"
            path.write_text(json.dumps(OWNER_ITEMS))
            items = sm.load_owner_items(path, oracle())
        self.assertEqual(items["BK-09"], sm.OwnerItem("low", "Keep notes exactly as they were typed."))
        self.assertEqual(set(items), {"BK-02", "BK-07", "BK-09"})

    def test_the_items_may_sit_under_an_items_key_beside_the_ratings_record(self):
        wrapped = {"_note": "Tiers from four raters.", "rating_prompt_sha256": "ab12", "share_high": 0.33, "items": OWNER_ITEMS}
        self.assertEqual(sm.parse_owner_items(wrapped, oracle()), sm.parse_owner_items(OWNER_ITEMS, oracle()))
        with self.assertRaisesRegex(ValueError, "BK-07"):
            sm.parse_owner_items({**wrapped, "items": {k: v for k, v in OWNER_ITEMS.items() if k != "BK-07"}}, oracle())
        with self.assertRaisesRegex(ValueError, "items"):
            sm.parse_owner_items({**wrapped, "items": ["BK-02"]}, oracle())

    def test_a_missing_askable_item_is_an_error_unless_a_default_is_given(self):
        data = {k: v for k, v in OWNER_ITEMS.items() if k != "BK-07"}
        with self.assertRaisesRegex(ValueError, "BK-07"):
            sm.parse_owner_items(data, oracle())
        default = sm.OwnerItem("low", "Something I forgot.")
        self.assertEqual(sm.parse_owner_items(data, oracle(), default=default)["BK-07"], default)

    def test_malformed_entries_are_refused(self):
        cases = {
            "BK-99": {**OWNER_ITEMS, "BK-99": {"tier": "low", "recall": "x"}},
            "BK-01": {**OWNER_ITEMS, "BK-01": {"tier": "low", "recall": "x"}},
            "tier": {**OWNER_ITEMS, "BK-02": {"tier": "huge", "recall": "x"}},
            "recall": {**OWNER_ITEMS, "BK-02": {"tier": "low", "recall": "  "}},
            "identifier": {**OWNER_ITEMS, "BK-02": {"tier": "low", "recall": "As BK-09 says."}},
            "keys": {**OWNER_ITEMS, "BK-02": {"tier": "low", "recall": "x", "teir": "high"}},
        }
        for why, data in cases.items():
            with self.subTest(why), self.assertRaisesRegex(ValueError, why):
                sm.parse_owner_items(data, oracle())

    def test_an_owner_needs_an_entry_for_every_askable_item(self):
        args = dict(oracle=oracle(), brief=BRIEF, policy="diligent", replicate="r", ask=FakeAsk())
        with self.assertRaises(ValueError):
            sm.Owner(**args)
        with self.assertRaisesRegex(ValueError, "BK-07"):
            sm.Owner(**args, owner_items={"BK-02": sm.OwnerItem("low", "a"), "BK-09": sm.OwnerItem("low", "b")})
        w = sm.Owner(**args, owner_items={}, default_owner_item=sm.OwnerItem("medium", "Something I forgot."))
        self.assertEqual(w.owner_items["BK-07"].tier, "medium")


# --------------------------------------------------------------------------------------------- the prompt


class PromptTest(unittest.TestCase):
    def test_the_owner_is_told_about_passages_touches_and_question_breadth(self):
        t = sm.TEMPLATE_PATH.read_text(encoding="utf-8")
        for phrase in ("[P3]", "`touches`", "`adjacent`", "`direct`", "`says`", "`targeted`", "`broad`", "`in_scope`",
                       "`passage`", "added to your reply for you"):
            self.assertIn(phrase, t)
        self.assertIn("Silence is not a contradiction", t)
        self.assertIn("Show me what you have in mind", t)

    def test_rule_3_draws_the_line_between_targeted_and_broad_with_an_example_each_side(self):
        t = sm.TEMPLATE_PATH.read_text(encoding="utf-8")
        rule3 = t.split("\n3. ", 1)[1].split("\n4. ", 1)[0]
        self.assertIn("one decision", rule3)
        self.assertIn('"Can a customer spend loyalty points on the delivery fee?"', rule3)  # targeted
        for broad_example in ('"How should loyalty points work?"', '"Anything about loyalty points?"', '"Any other edge cases?"'):
            self.assertIn(broad_example, rule3)

    def test_the_prompts_examples_stay_out_of_the_seeds_domains(self):
        t = sm.TEMPLATE_PATH.read_text(encoding="utf-8").lower()
        for word in ("cancel", "booking", "time zone", "release", "approval of"):
            self.assertNotIn(word, t, word)

    def test_a_recognized_rule_shown_wrong_is_a_correction_and_touches_replace_no_correction(self):
        t = sm.TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertIn("opposite of a rule you recognize on sight is a correction, with that rule's response, never a touch", t)
        self.assertIn("Touches never replace a correction", t)

    def test_a_question_put_to_the_owner_is_never_a_touch(self):
        t = sm.TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertIn("never for a question the agent puts to you", t)

    def test_askable_items_already_told_are_marked(self):
        text = sm.render_items(sm.released_items(oracle(), 1), {"BK-09"}, disclosed={"BK-09", "BK-01"})
        self.assertIn("[BK-09] (Askable; mentioned to the agent)", text)
        self.assertIn("[BK-02] (Askable) ", text)
        self.assertIn("[BK-01] (Stated) ", text)

    def test_a_fork_copies_the_disclosed_set(self):
        w, _ = owner()
        w.disclosed.add("BK-02")
        twin = w.fork()
        twin.disclosed.add("BK-09")
        self.assertEqual((w.disclosed, twin.disclosed), ({"BK-02"}, {"BK-02", "BK-09"}))


if __name__ == "__main__":
    unittest.main()
