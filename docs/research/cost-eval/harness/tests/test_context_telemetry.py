"""Tests for context_telemetry: context occupancy, compaction, reading, and repository size per change.

Run from the harness folder: python3.12 -m unittest discover -s tests
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import context_telemetry as ct  # noqa: E402


def usage(inp, read, write, out=5):
    return {"input_tokens": inp, "cache_read_input_tokens": read, "cache_creation_input_tokens": write, "output_tokens": out}


def assistant(msg_id, blocks, u, parent=None, agent=None):
    """One stream-json assistant event. Claude Code emits one event per content block, each repeating the usage."""
    e = {"type": "assistant", "message": {"id": msg_id, "role": "assistant", "content": blocks, "usage": u, "context_management": None},
         "parent_tool_use_id": parent, "session_id": "s1"}
    if agent:
        e["agent_id"] = agent
    return e


def tool_use(tid, name, inp):
    return {"type": "tool_use", "id": tid, "name": name, "input": inp}


def tool_result(tid, content, extra=None, parent=None, is_error=False):
    e = {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tid, "content": content, "is_error": is_error}]},
         "parent_tool_use_id": parent, "session_id": "s1"}
    if extra is not None:
        e["tool_use_result"] = extra
    return e


def read_result(tid, path, lines, start=1, total=None, parent=None):
    numbered = "\n".join(f"{start + i}\t{line}" for i, line in enumerate(lines))
    extra = {"type": "text", "file": {"filePath": path, "content": "\n".join(lines), "startLine": start,
                                      "numLines": len(lines), "totalLines": total or len(lines)}}
    return tool_result(tid, numbered, extra, parent=parent)


BASH_CMD = "cat docs/hld.md tests/test_a.py | head -5; grep -n foo app.py; sed -n 1,3p README.md"
BASH_OUT = "x" * 100
SKILL_BODY = "Base directory for this skill: /cfg/lid/plugins/x\n\n# Skill\n" + "s" * 40


def synthetic_turn():
    """A small turn: a split assistant message, Read, Grep, Glob, a Bash read, a compaction, a subagent, a skill."""
    return [
        {"type": "system", "subtype": "init", "cwd": "/work", "session_id": "s1", "tools": ["Bash", "Read"]},
        # m1 arrives as two events (thinking, then tool_use) with the same usage: one API call.
        assistant("m1", [{"type": "thinking", "thinking": ""}], usage(10, 1000, 500)),
        assistant("m1", [tool_use("t1", "Read", {"file_path": "/work/app.py"})], usage(10, 1000, 500)),
        read_result("t1", "/work/app.py", ["line one", "line two"]),
        assistant("m2", [tool_use("t2", "Bash", {"command": BASH_CMD}),
                         tool_use("t3", "Grep", {"pattern": "foo"}),
                         tool_use("t4", "Glob", {"pattern": "**/*.py"})], usage(2, 140000, 10000)),
        tool_result("t2", BASH_OUT, {"stdout": BASH_OUT, "stderr": "", "interrupted": False}),
        tool_result("t3", "app.py:1:foo"),
        tool_result("t4", "app.py"),
        {"type": "system", "subtype": "compact_boundary", "session_id": "s1",
         "compact_metadata": {"trigger": "auto", "pre_tokens": 150000}},
        assistant("m3", [tool_use("t5", "Skill", {"skill": "x"})], usage(3, 20000, 10000)),
        tool_result("t5", "Launching skill: x"),
        {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": SKILL_BODY}]}, "session_id": "s1"},
        # A subagent: its own context, which must not count toward the main session's occupancy.
        assistant("sa1", [tool_use("t6", "Read", {"file_path": "/work/docs/hld.md", "offset": 2, "limit": 1})],
                  usage(1, 0, 5000), parent="tA", agent="a1"),
        read_result("t6", "/work/docs/hld.md", ["second line"], start=2, total=3, parent="tA"),
        assistant("m4", [{"type": "text", "text": "done"}], usage(1, 30000, 100)),
        {"type": "result", "subtype": "success", "session_id": "s1",
         "modelUsage": {"claude-sonnet-5-5": {"contextWindow": 1000000}}},
    ]


class ContextSize(unittest.TestCase):
    def test_sums_uncached_cache_read_and_cache_write(self):
        self.assertEqual(ct.context_size(usage(10, 1000, 500, out=999)), 1510)

    def test_missing_fields_count_as_zero(self):
        self.assertEqual(ct.context_size({"input_tokens": 7}), 7)


class ParseStream(unittest.TestCase):
    def setUp(self):
        self.t = ct.parse_stream(synthetic_turn())

    def test_split_message_counts_as_one_call(self):
        self.assertEqual(self.t["api_calls"], 4)
        self.assertEqual(self.t["contexts"], [1510, 150002, 30003, 30101])

    def test_peak_and_first_context_main_thread_only(self):
        self.assertEqual(self.t["peak_context"], 150002)
        self.assertEqual(self.t["first_context"], 1510)
        self.assertEqual(self.t["subagent_api_calls"], 1)
        self.assertEqual(self.t["subagent_peak_context"], 5001)

    def test_compaction_event(self):
        self.assertEqual(len(self.t["compactions"]), 1)
        self.assertEqual(self.t["compactions"][0]["trigger"], "auto")
        self.assertEqual(self.t["compactions"][0]["pre_tokens"], 150000)

    def test_context_drop_is_flagged(self):
        self.assertEqual(self.t["context_drops"], [{"from": 150002, "to": 30003}])

    def test_reported_window(self):
        self.assertEqual(self.t["reported_context_window"], 1000000)

    def test_read_counts_and_chars(self):
        self.assertEqual(self.t["read_calls"], 2)
        self.assertEqual(self.t["read_files"], {"/work/app.py", "/work/docs/hld.md"})
        expected_chars = len("1\tline one\n2\tline two") + len("2\tsecond line")
        self.assertEqual(self.t["read_chars"], expected_chars)
        self.assertEqual(self.t["read_chars_by_class"], {"code": len("1\tline one\n2\tline two"), "docs": len("2\tsecond line")})

    def test_read_line_coverage_in_bytes(self):
        self.assertEqual(self.t["read_lines"]["/work/app.py"], {1: 9, 2: 9})
        self.assertEqual(self.t["read_lines"]["/work/docs/hld.md"], {2: 12})

    def test_grep_and_glob_tools(self):
        self.assertEqual(self.t["grep_calls"], 1)
        self.assertEqual(self.t["glob_calls"], 1)

    def test_bash_reading(self):
        self.assertEqual(self.t["bash_calls"], 1)
        self.assertEqual(self.t["bash_read_calls"], 1)
        self.assertEqual(self.t["bash_search_calls"], 1)
        self.assertEqual(self.t["bash_read_chars"], 100)
        # A call reading several classes splits its output evenly across the files it names (two docs, one test).
        self.assertEqual(self.t["bash_read_chars_by_class"], {"docs": 67, "tests": 33})
        self.assertEqual(self.t["bash_read_chars_split"], 100)
        reads = {(r["path"], r["mode"]) for r in self.t["bash_reads"]}
        self.assertEqual(reads, {("/work/docs/hld.md", "partial"), ("/work/tests/test_a.py", "partial"),
                                 ("/work/README.md", "partial")})

    def test_skill_content(self):
        self.assertEqual(self.t["skill_calls"], 1)
        self.assertEqual(self.t["skill_chars"], len(SKILL_BODY))

    def test_tool_counts(self):
        self.assertEqual(self.t["tool_calls"], {"Read": 2, "Bash": 1, "Grep": 1, "Glob": 1, "Skill": 1})

    def test_reads_a_file_path(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "turn-00.stream.jsonl"
            p.write_text("\n".join(json.dumps(e) for e in synthetic_turn()) + "\nnot json\n")
            self.assertEqual(ct.parse_stream(p)["api_calls"], 4)


class BashReads(unittest.TestCase):
    def test_cd_sed_cat(self):
        b = ct.bash_reads("cd /cfg/lid/x; sed -n 10,40p SKILL.md; cat references/a.md", cwd="/work", root="/work")
        self.assertEqual(b.reads, [("/cfg/lid/x/SKILL.md", "partial"), ("/cfg/lid/x/references/a.md", "full")])
        self.assertEqual(b.cwd, "/work")  # a cd outside the project does not carry to the next call

    def test_cd_inside_project_carries(self):
        b = ct.bash_reads("cd /work/docs && cat hld.md", cwd="/work", root="/work")
        self.assertEqual(b.reads, [("/work/docs/hld.md", "full")])
        self.assertEqual(b.cwd, "/work/docs")
        self.assertEqual(ct.bash_reads("cat a.md", cwd=b.cwd, root="/work").reads, [("/work/docs/a.md", "full")])

    def test_pipe_filters_are_not_reads_or_searches(self):
        b = ct.bash_reads('python -m pytest -q 2>&1 | grep -E "Error|error" | head', cwd="/work", root="/work")
        self.assertEqual((b.reads, b.searches, b.lists), ([], 0, 0))

    def test_heredoc_bodies_are_ignored(self):
        self.assertEqual(ct.bash_reads("cat > tests/x.py <<'EOF'\nprint(1)\nEOF", cwd="/work", root="/work").reads, [])
        cmd = "python3 - <<'EOF'\np='a.py'\ns=open(p).read()\ncat b.py\nEOF\ncat c.py"
        self.assertEqual(ct.bash_reads(cmd, cwd="/work", root="/work").reads, [("/work/c.py", "full")])

    def test_grep_with_files_is_a_search_not_a_read(self):
        b = ct.bash_reads("grep -rn foo benchtime/ ; grep -n confirm tests/*.py | head -30", cwd="/work", root="/work")
        self.assertEqual((b.reads, b.searches), ([], 2))

    def test_for_loop_and_braces_expand(self):
        b = ct.bash_reads('for d in a b; do echo "== $d"; cat docs/$d.md; done; cat src/{x,y}.py', cwd="/work", root="/work")
        self.assertEqual(b.reads, [("/work/docs/a.md", "full"), ("/work/docs/b.md", "full"),
                                   ("/work/src/x.py", "full"), ("/work/src/y.py", "full")])

    def test_head_and_tail_options(self):
        b = ct.bash_reads("head -n 20 x.py; tail -20 y.py; head -c 300 z.py", cwd="/work", root="/work")
        self.assertEqual(b.reads, [("/work/x.py", "partial"), ("/work/y.py", "partial"), ("/work/z.py", "partial")])

    def test_listing_and_unresolved(self):
        # Three listing commands: git ls-files, the wc, and the git ls-files inside the substitution.
        b = ct.bash_reads("git ls-files && wc -l $(git ls-files)", cwd="/work", root="/work")
        self.assertEqual((b.reads, b.lists), ([], 3))
        b = ct.bash_reads("cat $(git ls-files '*.md')", cwd="/work", root="/work")
        self.assertEqual((b.reads, b.unresolved, b.read_segments), ([], 1, 1))

    def test_sed_without_n_and_in_place_are_not_reads(self):
        self.assertEqual(ct.bash_reads("sed -i 's/a/b/' x.py; sed 's/a/b/' y.py", cwd="/work", root="/work").reads, [])

    def test_unbalanced_quotes_do_not_crash(self):
        b = ct.bash_reads("echo it's; cat a.md", cwd="/work", root="/work")
        self.assertIsInstance(b.reads, list)


LS_TREE = (
    "100644 blob aaa      51\t.gitignore\n"
    "100644 blob bbb    4314\tAGENTS.md\n"
    "120000 blob ccc       9\tCLAUDE.md\n"
    "100644 blob ddd      18\tapp.py\n"
    "100644 blob ddd    1441\tbenchtime/app.py\n"
    "100644 blob eee   18290\tdocs/hld.md\n"
    "100644 blob fff    2113\ttests/conftest.py\n"
    "100644 blob ggg    8945\ttests/test_copy.py\n"
    "160000 commit hhh       -\tvendor/sub\n"
    "100644 blob iii     500\tsrc/foo_test.go\n"
)


class RepoSize(unittest.TestCase):
    def test_parse_skips_submodules(self):
        entries = ct.parse_ls_tree(LS_TREE)
        self.assertEqual(len(entries), 9)
        self.assertIn(("docs/hld.md", 18290), entries)
        self.assertNotIn("vendor/sub", [p for p, _ in entries])

    def test_classification(self):
        self.assertEqual(ct.classify_path("docs/intent/x/x-specs.md"), "docs")
        self.assertEqual(ct.classify_path("tests/README.md"), "docs")
        self.assertEqual(ct.classify_path("tests/conftest.py"), "tests")
        self.assertEqual(ct.classify_path("src/pkg/test_rules.py"), "tests")
        self.assertEqual(ct.classify_path("src/foo_test.go"), "tests")
        self.assertEqual(ct.classify_path("web/a.spec.ts"), "tests")
        self.assertEqual(ct.classify_path("benchtime/rules.py"), "code")
        self.assertEqual(ct.classify_path("requirements.txt"), "code")

    def test_sizes_by_class(self):
        r = ct.repo_size(ct.parse_ls_tree(LS_TREE))
        self.assertEqual(r["docs"], 4314 + 9 + 18290)
        self.assertEqual(r["tests"], 2113 + 8945 + 500)
        self.assertEqual(r["code"], 51 + 18 + 1441)
        self.assertEqual(r["bytes"], r["docs"] + r["tests"] + r["code"])
        self.assertEqual(r["files"], 9)
        self.assertEqual(r["tokens_est"], round(r["bytes"] / 4))

    def test_fetch_splits_one_docker_call_by_commit(self):
        calls = []

        def run(cmd, **kw):
            calls.append(cmd)
            out = f"@@@ c1\n{LS_TREE}@@@ c2\n100644 blob x 7\ta.py\n" if cmd[:2] == ["docker", "run"] else ""
            return SimpleNamespace(returncode=0, stdout=out, stderr="")

        got = ct.fetch_listings("vol", ["c1", "c2"], "img:1", run=run)
        runs = [c for c in calls if c[:2] == ["docker", "run"]]
        self.assertEqual(len(runs), 1)
        self.assertIn("vol:/w:ro", runs[0])
        self.assertEqual(got["c2"], "100644 blob x 7\ta.py\n")
        self.assertEqual(len(ct.parse_ls_tree(got["c1"])), 9)

    def test_fetch_refuses_a_missing_volume(self):
        def run(cmd, **kw):
            return SimpleNamespace(returncode=1, stdout="", stderr="no such volume")

        with self.assertRaises(ct.RepoUnavailable):
            ct.fetch_listings("gone", ["c1"], "img:1", run=run)


class Rollup(unittest.TestCase):
    def test_change_rollup_with_repo(self):
        turn = ct.parse_stream(synthetic_turn())
        entries = ct.parse_ls_tree(LS_TREE)
        c = ct.rollup_change([turn], entries, window=200000, root="/work")
        self.assertEqual(c["peak_context"], 150002)
        self.assertAlmostEqual(c["peak_share"], 150002 / 200000)
        self.assertEqual(c["compactions"], 1)
        self.assertEqual(c["read_unique_repo_files"], 2)
        cov = c["coverage"]
        # app.py read whole by Read (18 bytes); one 12-byte line of docs/hld.md read by the subagent.
        self.assertEqual(cov["read_tool_bytes"], 18 + 12)
        self.assertAlmostEqual(cov["read_tool_share"], 30 / c["repo"]["bytes"])
        # Bash reads were all partial (piped cat, sed -n), so the estimate adds nothing beyond Read.
        self.assertEqual(cov["est_bytes"], 30)
        # Touched counts every file any read form reached: app.py, docs/hld.md, tests/test_a.py (absent), README.md (absent).
        self.assertEqual(cov["touched_bytes"], 18 + 18290)
        self.assertEqual(c["files_read_any"], 4)

    def test_full_bash_cat_and_persisted_output(self):
        events = [
            {"type": "system", "subtype": "init", "cwd": "/work", "session_id": "s1"},
            assistant("m1", [tool_use("b1", "Bash", {"command": "cat benchtime/app.py"}),
                             tool_use("b2", "Bash", {"command": "cat docs/hld.md"})], usage(1, 100, 100)),
            tool_result("b1", "x" * 50, {"stdout": "x" * 50}),
            tool_result("b2", "<persisted-output>\nOutput too large (18KB). Full output saved to: /cfg/projects/-work/s/tool-results/r1.txt\n...",
                        {"stdout": "", "persistedOutputPath": "/cfg/projects/-work/s/tool-results/r1.txt", "persistedOutputSize": 18290}),
        ]
        entries = ct.parse_ls_tree(LS_TREE)
        c = ct.rollup_change([ct.parse_stream(events)], entries, window=200000, root="/work")
        self.assertEqual(c["bash_persisted"], 1)
        self.assertEqual(c["coverage"]["est_bytes"], 1441)  # the persisted cat was only seen as a preview
        events.append(assistant("m2", [tool_use("r1", "Read", {"file_path": "/cfg/projects/-work/s/tool-results/r1.txt"})], usage(1, 200, 100)))
        events.append(read_result("r1", "/cfg/projects/-work/s/tool-results/r1.txt", ["whole doc"]))
        c = ct.rollup_change([ct.parse_stream(events)], entries, window=200000, root="/work")
        self.assertEqual(c["coverage"]["est_bytes"], 1441 + 18290)
        self.assertEqual(c["read_chars_by_class"], {"harness": len("1\twhole doc")})

    def test_rollup_without_repo(self):
        c = ct.rollup_change([ct.parse_stream(synthetic_turn())], None, window=200000, root="/work")
        self.assertIsNone(c["repo"])
        self.assertIsNone(c["coverage"])

    def test_peak_across_turns(self):
        a = ct.parse_stream(synthetic_turn())
        b = ct.parse_stream([assistant("z", [{"type": "text", "text": "hi"}], usage(1, 160000, 0))])
        c = ct.rollup_change([a, b], None, window=200000, root="/work")
        self.assertEqual((c["peak_context"], c["peak_turn"]), (160001, 1))
        self.assertEqual(c["api_calls"], 5)


class Trajectory(unittest.TestCase):
    def make_run(self, root: Path):
        run = root / "t-arm-1"
        (run / "change-00").mkdir(parents=True)
        (run / "trajectory.json").write_text(json.dumps({
            "id": "t-arm-1", "arm": "arm", "image": "img:1", "volumes": {"workspace": "ws"}, "start_commit": "c0",
            "changes": {"0": {"title": "First", "commit": "c1"}, "1": {"title": "Skipped", "commit": "c1", "symptom": "not fired"}},
        }))
        (run / "change-00" / "change.json").write_text(json.dumps({"turns": [{"stream": "turn-00.stream.jsonl"}]}))
        (run / "change-00" / "turn-00.stream.jsonl").write_text("\n".join(json.dumps(e) for e in synthetic_turn()))
        return run

    def test_trajectory_with_fake_fetch(self):
        with tempfile.TemporaryDirectory() as d:
            run = self.make_run(Path(d))
            seen = {}

            def fetch(volume, commits, image):
                seen.update(volume=volume, commits=list(commits), image=image)
                return {"c0": "", "c1": LS_TREE}

            t = ct.trajectory_telemetry(run, window=200000, fetch=fetch)
            self.assertEqual(seen["volume"], "ws")
            self.assertEqual(set(seen["commits"]), {"c0", "c1"})
            self.assertEqual([c["change"] for c in t["changes"]], [0])
            self.assertEqual(t["skipped"], [{"change": 1, "title": "Skipped", "reason": "not fired"}])
            self.assertEqual(t["changes"][0]["repo"]["files"], 9)
            self.assertEqual(t["changes"][0]["repo_start"]["files"], 0)

    def test_trajectory_without_repo(self):
        with tempfile.TemporaryDirectory() as d:
            t = ct.trajectory_telemetry(self.make_run(Path(d)), window=200000, fetch=None)
            self.assertIsNone(t["changes"][0]["repo"])


class Summary(unittest.TestCase):
    def traj(self, tid, arm, peaks, shares, c10_bytes):
        changes = []
        for i, (p, s) in enumerate(zip(peaks, shares)):
            changes.append({"change": i if i < len(peaks) - 1 else 10, "peak_context": p, "peak_share": p / 200000, "compactions": 0,
                            "read_unique_repo_files": 2, "files_read_any": 4,
                            "coverage": {"read_tool_share": s, "est_share": s * 2},
                            "repo": {"bytes": c10_bytes, "tokens_est": c10_bytes // 4, "tests": 1, "code": 1, "docs": 1}})
        return {"id": tid, "arm": arm, "window": 200000, "changes": changes}

    def test_arm_means(self):
        s = ct.summarize([self.traj("a1", "bare", [100, 300], [0.1, 0.3], 1000),
                          self.traj("a2", "bare", [200, 400], [0.2, 0.4], 3000)])
        bare = s["bare"]
        self.assertEqual(bare["n"], 2)
        self.assertAlmostEqual(bare["peak_context_mean"], 250)
        self.assertAlmostEqual(bare["peak_context_max"], 350)  # mean over trajectories of each one's max
        self.assertAlmostEqual(bare["read_tool_share_mean"], 0.25)
        self.assertAlmostEqual(bare["repo_bytes_c10"], 2000)
        self.assertEqual(bare["compactions"], 0)
        self.assertIsNone(bare["method_chars_mean"])  # absent from these minimal change records


if __name__ == "__main__":
    unittest.main()
