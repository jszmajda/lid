"""Tests for owner reading by review depth (analysis_review_depth.py): rebuilding the split of words shown from an
owner record's prompt, by what was shown, and owner-hours at three review depths.

Run from the harness folder: python3.12 -m unittest discover -s tests
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import analysis_review_depth as rd  # noqa: E402


def prompt(message: str, docs: list[tuple[str, str]] = ()) -> str:
    """An owner prompt shaped like the simulator's: the message, then the documents section, then the return rules."""
    out = "## Your situation\n\nSome narrative.\n\n<agent_message>\n" + message + "\n</agent_message>\n\n"
    if docs:
        out += rd.DOCS_HEADING + "\n\n" + "\n\n".join(f'<document name="{n}">\n{t}\n</document>' for n, t in docs)
    return out + "\n\n## What to return\n\nReturn JSON.\n"


def record(message: str, docs=(), words_shown=None) -> dict:
    split = rd.message_split(message)
    total = split["chat"] + split["code_in_chat"] + sum(rd.doc_words(t) for _, t in docs)
    return {"words_shown": total if words_shown is None else words_shown, "documents": [n for n, _ in docs],
            "calls": [{"prompt": prompt(message, docs)}]}


DIFF = rd.DIFF_HEADER + "\n\n@@ -1,2 +1,3 @@\n context line\n-old words here\n+[P4] three new words\n+[P5] and two"


class DocKind(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(rd.doc_kind("docs/high-level-design.md"), "hld")
        self.assertEqual(rd.doc_kind("docs/intent/catalog/catalog-design.md"), "lld")
        self.assertEqual(rd.doc_kind("docs/intent/catalog/decisions/why-flags.md"), "lld")
        self.assertEqual(rd.doc_kind("docs/intent/catalog/catalog-specs.md"), "specs")
        self.assertEqual(rd.doc_kind("tests/README.md"), "tests")
        self.assertEqual(rd.doc_kind("README.md"), "other_docs")
        self.assertEqual(rd.doc_kind("NOTES.md"), "other_docs")
        self.assertEqual(rd.doc_kind("requirements.txt"), "other_docs")
        self.assertEqual(rd.doc_kind(rd.PLAN_NAME), "plan")


class Words(unittest.TestCase):
    def test_first_read_counts_everything_without_marks(self):
        self.assertEqual(rd.doc_words("[P2] # Title\n\n[P3] Two words"), 4)

    def test_reread_counts_only_added_lines(self):
        self.assertEqual(rd.doc_words(DIFF), 5)

    def test_unchanged_counts_nothing(self):
        self.assertEqual(rd.doc_words(rd.UNCHANGED), 0)

    def test_message_split_separates_fenced_blocks(self):
        msg = "[P1] Here is the diff:\n\n[P2] ```diff\n+ added line\n```\n\n[P3] Approve?"
        self.assertEqual(rd.message_split(msg), {"chat": 5, "code_in_chat": 5})  # fences count as words

    def test_empty_message(self):
        self.assertEqual(rd.message_split(rd.EMPTY_MESSAGE), {"chat": 0, "code_in_chat": 0})


class StopSplit(unittest.TestCase):
    def test_parses_message_and_documents(self):
        docs = [("docs/high-level-design.md", "[P2] # HLD\n\n[P3] one two three"),
                ("docs/intent/a/a-design.md", DIFF),
                ("docs/intent/a/a-specs.md", rd.UNCHANGED),
                ("README.md", "[P6] readme words")]
        s = rd.stop_split(record("[P1] Please review these four documents.", docs))
        self.assertTrue(s["reconciled"], s["problem"])
        self.assertEqual(s["split"]["chat"], 5)
        self.assertEqual(s["split"]["hld"], 5)
        self.assertEqual(s["split"]["lld"], 5)
        self.assertEqual(s["split"]["specs"], 0)
        self.assertEqual(s["split"]["other_docs"], 2)
        self.assertEqual(s["words_shown"], 17)

    def test_document_holding_a_closing_tag_line_still_parses(self):
        docs = [("README.md", "[P2] Example:\n\n[P3] ```\n</document>\n```"), ("NOTES.md", "[P4] note")]
        s = rd.stop_split(record("[P1] Hi", docs))
        self.assertTrue(s["reconciled"], s["problem"])

    def test_mismatch_is_flagged(self):
        s = rd.stop_split(record("[P1] Hello there", words_shown=99))
        self.assertFalse(s["reconciled"])
        self.assertIn("recorded 99", s["problem"])

    def test_missing_prompt(self):
        s = rd.stop_split({"words_shown": 3, "documents": [], "calls": []})
        self.assertFalse(s["reconciled"])

    def test_plan_counts_as_chat_at_lighter_depths(self):
        split = {c: 0 for c in rd.CATEGORIES}
        split.update(chat=100, plan=50, hld=20, lld=30, specs=40, other_docs=10, code_in_chat=5)
        d = rd.depth_words(split)
        self.assertEqual(d["a_everything"], 255)
        self.assertEqual(d["b_hld_lld_chat"], 205)
        self.assertEqual(d["c_chat_only"], 155)


class RunSplit(unittest.TestCase):
    def test_trajectory_totals_and_hours(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "t-1"
            (run / "change-00").mkdir(parents=True)
            (run / "change-01").mkdir(parents=True)
            (run / "trajectory.json").write_text(json.dumps({"id": "t-1", "arm": "lid-full", "seed": "s"}))
            chat = " ".join(["word"] * 238)
            (run / "change-00" / "owner-00.json").write_text(json.dumps(record(chat)))
            (run / "change-00" / "owner-01.json").write_text(json.dumps(record(
                "[P1] ok", [("docs/high-level-design.md", " ".join(["h"] * 238 * 2))])))
            (run / "change-01" / "owner-00.json").write_text(json.dumps(record(
                "[P1] specs", [("docs/intent/x/x-specs.md", " ".join(["s"] * 238 * 3))])))
            r = rd.run_split(run)
        self.assertEqual(r["stops"], 3)
        self.assertEqual(r["stops_reconciled"], 3)
        self.assertEqual(r["split"]["hld"], 476)
        self.assertEqual(r["split"]["specs"], 714)
        self.assertEqual(r["split"]["chat"], 240)
        self.assertAlmostEqual(r["depth_hours"]["a_everything"], (240 + 476 + 714) / 238 / 60, places=3)
        self.assertAlmostEqual(r["depth_hours"]["b_hld_lld_chat"], (240 + 476) / 238 / 60, places=3)
        self.assertAlmostEqual(r["depth_hours"]["c_chat_only"], 240 / 238 / 60, places=3)
        self.assertEqual(set(r["changes"]), {"0", "1"})
        self.assertIn("bounded owner", rd.report([r]))


if __name__ == "__main__":
    unittest.main()
