"""Tests for opengym_map: the /map-codebase session on openGym, its stopping rule, its records, and the check that the
map changed no code beyond annotations. Docker and the agent's turns are fakes."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import opengym_map as om  # noqa: E402
from costeval import executor, usage  # noqa: E402
from test_trajectory import write_stream  # noqa: E402

DONE = {"hld": True, "index": True, "lid_block": {"CLAUDE.md": True}, "designs": ["a"], "specs": ["b"], "ears": 3,
        "arrow_docs": ["c"]}
NOT_DONE = {"hld": False, "index": False, "lid_block": {"CLAUDE.md": False}, "designs": [], "specs": [], "ears": 0,
            "arrow_docs": []}


class Turns:
    """Plays the session: turn k's cumulative cost is 0.1 * (k + 1); fail_at makes one turn an error."""

    def __init__(self, fail_at=None, session="s1"):
        self.calls, self.fail_at, self.session = [], fail_at, session

    def __call__(self, prompt, stream_path, *, resume=None):
        k = len(self.calls)
        self.calls.append({"prompt": prompt, "resume": resume})
        write_stream(stream_path, session=self.session, text=f"turn {k}", cost=0.1 * (k + 1), out_tokens=100 * (k + 1),
                     is_error=(k == self.fail_at))
        return executor.TurnRecord(stream_path=stream_path, container_name="c", exit_code=0, timed_out=False,
                                   duration_s=60.0, session_id=self.session, init={}, init_problem=None,
                                   summary=usage.from_stream(stream_path), final_text=f"turn {k}")


class Mapping(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def run_with(self, states, turns=None, loaded=True, cap=om.ROUND_CAP):
        states = list(states)
        turns = turns or Turns()
        res = om.run_mapping(turn=turns, state=lambda: states.pop(0), loaded=lambda sid: loaded, out_dir=self.tmp,
                             round_cap=cap)
        return res, turns

    def test_first_prompt_is_the_invocation_plus_one_instruction(self):
        self.assertTrue(om.FIRST_PROMPT.startswith("/map-codebase "))
        self.assertEqual(om.FIRST_PROMPT, f"/map-codebase {om.INSTRUCTION}")
        self.assertIn(om.QUESTIONS, om.INSTRUCTION)
        self.assertEqual(om.CONTINUE_PROMPT, om.INSTRUCTION)

    def test_resumes_with_the_instruction_until_the_terminal_state(self):
        res, turns = self.run_with([NOT_DONE, NOT_DONE, DONE])
        self.assertEqual(res.stop, "done")
        self.assertEqual([c["prompt"] for c in turns.calls], [om.FIRST_PROMPT, om.CONTINUE_PROMPT, om.CONTINUE_PROMPT])
        self.assertEqual([c["resume"] for c in turns.calls], [None, "s1", "s1"])
        self.assertEqual((self.tmp / "prompt-00.txt").read_text(), om.FIRST_PROMPT)

    def test_each_turn_records_its_own_usage_and_the_totals_are_cumulative(self):
        res, _ = self.run_with([NOT_DONE, DONE])
        self.assertAlmostEqual(res.turns[0]["usage"]["reported_cost_usd"], 0.1)
        self.assertAlmostEqual(res.turns[1]["usage"]["reported_cost_usd"], 0.1)
        self.assertEqual(res.turns[1]["usage"]["models"]["claude-sonnet-5-5"]["output"], 100)
        t = om.totals(res.cumulative)
        self.assertEqual(t["output"], 200)
        self.assertAlmostEqual(t["reported_cost_usd"], 0.2)
        self.assertEqual(res.turns[1]["state"]["ears"], 3)

    def test_a_failed_turn_stops_as_a_misfire(self):
        res, turns = self.run_with([NOT_DONE, NOT_DONE], turns=Turns(fail_at=1))
        self.assertEqual(res.stop, "failed")
        self.assertEqual(len(turns.calls), 2)

    def test_a_skill_that_never_loaded_stops_after_the_first_turn(self):
        res, turns = self.run_with([DONE], loaded=False)
        self.assertEqual(res.stop, "skill-not-loaded")
        self.assertEqual(len(turns.calls), 1)

    def test_the_cap_stops_a_session_that_never_completes(self):
        res, turns = self.run_with([NOT_DONE] * 3, cap=3)
        self.assertEqual(res.stop, "capped")
        self.assertEqual(len(turns.calls), 3)

    def test_done_needs_the_hld_the_index_and_the_lid_block(self):
        self.assertTrue(om.is_done(DONE))
        for k, v in (("hld", False), ("index", False), ("lid_block", {"CLAUDE.md": False, "AGENTS.md": False})):
            self.assertFalse(om.is_done({**DONE, k: v}), k)
        self.assertTrue(om.is_done({**DONE, "lid_block": {"CLAUDE.md": False, "AGENTS.md": True}}))


class Workspace(unittest.TestCase):
    def test_archive_paths_drop_only_the_omitted_folder(self):
        entries = {"": ["CLAUDE.md", "api", "catalogue"], "catalogue": ["catalogue/data", "catalogue/media"]}
        self.assertEqual(om.archive_paths(entries), ["CLAUDE.md", "api", "catalogue/data"])

    def test_start_is_one_commit_at_the_fixed_date(self):
        s = om.start_script()
        self.assertIn("commit -q -m Start", s)
        self.assertIn(om.DATE, s)

    def test_state_script_reads_a_real_tree(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "docs/intent/auth").mkdir(parents=True)
            (root / "docs/arrows").mkdir(parents=True)
            (root / "docs/high-level-design.md").write_text("# HLD\n")
            (root / "docs/arrows/index.yaml").write_text("arrows: {}\n")
            (root / "docs/arrows/auth.md").write_text("# auth\n")
            (root / "docs/intent/auth/auth-design.md").write_text("# auth\n")
            (root / "docs/intent/auth/auth-specs.md").write_text(
                "- [x] **AUTH-001**: a\n- [ ] **AUTH-002**: b\n- [D] AUTH-SUB-003: c\nnot a spec AUTH-004\n")
            (root / "CLAUDE.md").write_text("# Project\n\n## LID\n- Mode: Full\n")
            p = subprocess.run([sys.executable, "-c", om._PY_STATE], cwd=root, capture_output=True, text=True, check=True)
            s = json.loads(p.stdout)
        self.assertTrue(om.is_done(s))
        self.assertEqual(s["ears"], 3)
        self.assertEqual(len(s["designs"]), 1)
        self.assertEqual(s["arrow_docs"], ["docs/arrows/auth.md"])


DIFF = """diff --git a/api/server.js b/api/server.js
index 1..2 100644
--- a/api/server.js
+++ b/api/server.js
@@ -10,0 +11 @@
+// @spec AUTH-001, AUTH-002
@@ -20 +21 @@
-function pair() { // pairs a watch
+function pair() { // pairs a watch @spec ZEPP-003
diff --git a/frontend/src/x.js b/frontend/src/x.js
index 1..2 100644
--- a/frontend/src/x.js
+++ b/frontend/src/x.js
@@ -5 +5 @@
-const LIMIT = 6;
+const LIMIT = 8;
diff --git a/docs/intent/auth/auth-design.md b/docs/intent/auth/auth-design.md
new file mode 100644
--- /dev/null
+++ b/docs/intent/auth/auth-design.md
@@ -0,0 +1 @@
+# Auth
diff --git a/CLAUDE.md b/CLAUDE.md
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -1,0 +2 @@
+## LID
"""


class Check(unittest.TestCase):
    def test_annotations_pass_and_code_edits_are_flagged(self):
        r = om.classify_diff(DIFF)
        self.assertEqual(r["doc_files"], ["CLAUDE.md", "docs/intent/auth/auth-design.md"])
        self.assertEqual(r["annotated_files"], ["api/server.js"])
        self.assertEqual(r["annotation_lines"], 2)
        self.assertEqual(sorted(r["non_annotation_edits"]["frontend/src/x.js"]), ["+const LIMIT = 8;", "-const LIMIT = 6;"])
        self.assertEqual(list(r["non_annotation_edits"]), ["frontend/src/x.js"])

    def test_comment_styles(self):
        for line in ("// @spec A-1", "# @spec A-1", " * @spec A-1", "/* @spec A-1 */", "{/* @spec A-1 */}", ""):
            self.assertTrue(om.is_annotation(line), line)
        for line in ("// just a comment", "const x = 1; // @spec A-1"):
            self.assertFalse(om.is_annotation(line), line)

    def test_suite_counts(self):
        node = "# tests 1084\n# pass 1081\n# fail 0\n# skipped 3\n"
        self.assertEqual(om.parse_counts(node), {"pass": 1081, "fail": 0, "skipped": 3})
        spec = "ℹ tests 1084\nℹ pass 1084\nℹ fail 0\nℹ cancelled 0\nℹ skipped 0\nℹ todo 0\n"
        self.assertEqual(om.parse_counts(spec), {"pass": 1084, "fail": 0, "skipped": 0, "todo": 0, "cancelled": 0})
        vitest = " Test Files  898 passed (898)\n      Tests  10100 passed | 1 skipped (10101)\n"
        coloured = "\x1b[2m      Tests \x1b[22m \x1b[1m\x1b[32m153 passed\x1b[39m\x1b[22m\x1b[90m (153)\x1b[39m\n"
        self.assertEqual(om.parse_counts(coloured), {"pass": 153})
        self.assertEqual(om.parse_counts(vitest), {"pass": 10100, "skipped": 1, "files": "898 passed (898)"})


if __name__ == "__main__":
    unittest.main()
