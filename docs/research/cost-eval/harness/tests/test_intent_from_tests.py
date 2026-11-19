"""intent_from_tests.py: reading a volume, the reader's single-sample rule, one input end to end with stand-in
models, refusal over the size cap, and the summary with its baseline subtraction."""

from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import intent_from_tests as itf  # noqa: E402
from costeval import intent_recall as ir  # noqa: E402
from test_intent_recall import ORACLE, SCRIPT  # noqa: E402


def tar_of(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as t:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class ReadVolumeTest(unittest.TestCase):
    def test_text_files_come_back_by_path_and_binaries_are_skipped(self):
        calls = []

        def runner(cmd, **kw):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, tar_of({"./tests/test_a.py": b"def test_a(): pass\n",
                                                               "./data/x.db": b"\xff\xfe\x00"}), b"")
        files = itf.read_volume("ce-g-x-c10-ckpt", "app", runner=runner)
        self.assertEqual(files, {"tests/test_a.py": "def test_a(): pass\n"})
        self.assertIn("ce-g-x-c10-ckpt:/src:ro", calls[0])
        self.assertIn("--exclude=.venv", calls[0])
        with self.assertRaises(ValueError):
            itf.read_volume("/host/path", "app", runner=runner)
        with self.assertRaises(ValueError):
            itf.read_volume("vol", "../etc", runner=runner)


class ReconstructTest(unittest.TestCase):
    INPUTS = [ir.InputFile("brief.md", "A book on loan can't be lent to a second member.\n")]

    def test_a_usable_first_answer_stands_even_with_a_dropped_rule(self):
        answers = iter([{"rules": [{"rule": "A book never goes to two members.", "evidence": ["brief.md"]},
                                   {"rule": "A guessed rule here.", "evidence": ["nowhere.md"]}]}])
        rec = itf.reconstruct("p", self.INPUTS, lambda p, s: (next(answers), {"cost_usd": 0.2}))
        self.assertEqual(len(rec["tries"]), 1)
        self.assertEqual([r["rule"] for r in rec["rules"]], ["A book never goes to two members."])
        self.assertEqual(rec["listed"], 2)

    def test_an_answer_with_no_usable_rules_is_asked_again(self):
        answers = iter([None, {"rules": []}, {"rules": [{"rule": "A book never goes to two members.", "evidence": ["brief.md"]}]}])
        rec = itf.reconstruct("p", self.INPUTS, lambda p, s: (next(answers), {"cost_usd": 0.1}))
        self.assertEqual(len(rec["tries"]), 3)
        self.assertEqual(len(rec["rules"]), 1)
        self.assertAlmostEqual(rec["cost_usd"], 0.3)


def fake_reader(prompt, schema):
    return {"rules": [{"rule": "Two members never hold the same book on loan.", "evidence": ["brief.md"]},
                      {"rule": "Every late return is fined.", "evidence": ["brief.md"]},
                      {"rule": "Refusals come back as HTTP 409.", "evidence": ["brief.md"]}]}, \
        {"cost_usd": 0.25, "models": {"claude-sonnet-5-5": {"input": 1000, "output": 200, "cache_read": 0,
                                                            "cache_write_5m": 0, "cache_write_1h": 0}}}


def fake_judge(prompt, schema):
    nums = [int(n) for n in re.findall(r"(?m)^R(\d+)\.", prompt)]
    table = {
        1: {"classification": "agrees", "items": ["LN-01"], "extent": "whole", "rule_quote": "never hold",
            "item_quotes": [{"item": "LN-01", "quote": "can't be lent"}]},
        2: {"classification": "stale", "items": ["SUP-02"], "extent": "none", "rule_quote": "Every late return",
            "item_quotes": [{"item": "SUP-02", "quote": "Start fining every late return"}]},
        3: {"classification": "incidental", "items": [], "extent": "none", "rule_quote": "HTTP 409", "item_quotes": []},
    }
    return {"mappings": [dict(table[n], rule=n, reason="The rule and the item describe this behaviour.") for n in nums]}, \
        {"cost_usd": 0.05, "models": {}}


class RunInputTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        nb = Path(self.tmp.name)
        hidden = nb / "seeds" / "toy" / "hidden"
        hidden.mkdir(parents=True)
        (hidden / "oracle.md").write_text(ORACLE)
        (hidden / "change-script.md").write_text(SCRIPT)
        (nb / "seeds" / "toy" / "brief.md").write_text("A book on loan can't be lent to a second member.\n")
        self.saved = itf.NOTEBOOK, itf.RUNS
        itf.NOTEBOOK, itf.RUNS = nb, nb / "runs" / "intent-from-tests"
        self.spec = {"label": "brief", "group": "brief", "source": "brief", "brief": "seeds/toy/brief.md",
                     "oracle": {"kind": "benchtime", "seed": "toy", "change": 5}}

    def tearDown(self):
        itf.NOTEBOOK, itf.RUNS = self.saved
        self.tmp.cleanup()

    def test_one_input_end_to_end_with_stand_in_models(self):
        out = itf.RUNS / "toy" / "brief"
        r = itf.run_input(self.spec, out, repeats=2, ask_reader=fake_reader, ask_judge=fake_judge)
        self.assertEqual(len(r["repeats"]), 2)
        s = r["repeats"][0]
        self.assertEqual(s["recovered"], ["LN-01"])
        self.assertEqual(s["counts"], {"agrees": 1, "contradicts": 0, "stale": 1, "incidental": 1})
        self.assertEqual(s["stale_items"], ["SUP-02"])
        self.assertAlmostEqual(r["cost_usd"], 2 * (0.25 + 0.05))
        self.assertEqual(r["tokens"]["input"], 2000)
        for f in ("input.md", "input.json", "oracle.json", "rep-1/reader.json", "rep-1/rules.md", "rep-1/judgment.json",
                  "rep-2/score.json", "result.json"):
            self.assertTrue((out / f).exists(), f)
        self.assertIn("A book on loan", (out / "input.md").read_text())
        # a second run resumes from the recorded repeats without calling a model
        boom = lambda p, s: (_ for _ in ()).throw(AssertionError("called"))  # noqa: E731
        again = itf.run_input(self.spec, out, repeats=2, ask_reader=boom, ask_judge=boom)
        self.assertEqual(again["repeats"], r["repeats"])
        # with the judgment gone, the recorded reader sample is judged again rather than drawn again
        (out / "rep-1" / "score.json").unlink()
        rejudged = itf.run_input(self.spec, out, repeats=2, ask_reader=boom, ask_judge=fake_judge)
        self.assertEqual(rejudged["repeats"], r["repeats"])

    def test_rescore_recomputes_scores_from_the_records_without_a_model(self):
        out = itf.RUNS / "toy" / "brief"
        r = itf.run_input(self.spec, out, repeats=2, ask_reader=fake_reader, ask_judge=fake_judge)
        saved = json.loads((out / "rep-1" / "score.json").read_text())
        saved["score"]["recall"] = 0.99  # as if scored by older code
        (out / "rep-1" / "score.json").write_text(json.dumps(saved))
        self.assertEqual(itf.rescore("toy"), 2)
        again = json.loads((out / "result.json").read_text())
        self.assertEqual(again["repeats"], r["repeats"])
        self.assertAlmostEqual(again["summary"]["recall"]["mean"], r["summary"]["recall"]["mean"])
        self.assertEqual(json.loads((out / "rep-1" / "score.json").read_text())["cost_usd"], saved["cost_usd"])

    def test_an_input_over_the_cap_is_refused_and_no_model_is_called(self):
        (itf.NOTEBOOK / "seeds" / "toy" / "brief.md").write_text("word " * 700_000)
        boom = lambda p, s: (_ for _ in ()).throw(AssertionError("called"))  # noqa: E731
        r = itf.run_input(self.spec, itf.RUNS / "toy" / "brief", ask_reader=boom, ask_judge=boom)
        self.assertIn("over the cap", r["refused"])
        self.assertFalse((itf.RUNS / "toy" / "brief" / "input.md").exists())

    def test_the_summary_subtracts_the_baseline_over_each_inputs_met_set(self):
        itf.run_input(self.spec, itf.RUNS / "toy" / "brief", repeats=1, ask_reader=fake_reader, ask_judge=fake_judge)

        def reader2(prompt, schema):
            rules = [{"rule": "Two members never hold the same book on loan.", "evidence": ["brief.md"]},
                     {"rule": "A reserved book is held for three days.", "evidence": ["brief.md"]}]
            return {"rules": rules}, {"cost_usd": 0.1}

        def judge2(prompt, schema):
            nums = [int(n) for n in re.findall(r"(?m)^R(\d+)\.", prompt)]
            table = {1: ("LN-01", "can't be lent", "never hold"), 2: ("LN-03", "held for three days", "held for three days")}
            return {"mappings": [{"rule": n, "classification": "agrees", "items": [table[n][0]], "extent": "whole",
                                  "rule_quote": table[n][2], "item_quotes": [{"item": table[n][0], "quote": table[n][1]}],
                                  "reason": "The rule states the item's behaviour exactly."} for n in nums]}, {"cost_usd": 0.1}
        gdir = itf.NOTEBOOK / "runs" / "t-1" / "grading" / "change-05"
        gdir.mkdir(parents=True)
        (gdir / "verdicts.json").write_text("{}")
        spec = dict(self.spec, label="t-1-brieflike", group="armx", baseline="brief")
        orig = itf.build_oracle

        def oracle_with_met(sp):
            items, _, meta = orig({k: v for k, v in sp.items() if k != "verdicts"})
            return items, {"LN-01", "LN-03", "LN-04"}, meta
        itf.build_oracle = oracle_with_met
        try:
            itf.run_input(spec, itf.RUNS / "toy" / "t-1-brieflike", repeats=1, ask_reader=reader2, ask_judge=judge2)
        finally:
            itf.build_oracle = orig
        s = itf.summarize("toy")
        cell = s["cells"]["armx|brief"]
        self.assertAlmostEqual(cell["mean"]["recall_of_met"], 2 / 3)
        self.assertAlmostEqual(cell["baseline"]["recall_of_met"], 1 / 3)  # the brief reader got LN-01 of the three
        self.assertAlmostEqual(cell["minus_baseline"]["recall_of_met"], 1 / 3)
        self.assertAlmostEqual(cell["minus_baseline"]["latent_of_met"], 0.5)  # LN-03 of LN-03, LN-04; baseline none
        self.assertIn("armx", (itf.RUNS / "toy" / "summary.md").read_text())


if __name__ == "__main__":
    unittest.main()
