#!/usr/bin/env python3
"""Tests for run_eval.py. Run from the repository root:

    python3 tools/alt-model-evals/test_run_eval.py

End-to-end tests copy the runner into a throwaway fake repository and put stub
`docker` and `npx` commands first on PATH (testdata/stub_harness.py), so no
network, key, container runtime, or model is needed.
"""

import datetime
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_eval  # noqa: E402

STUB = HERE / "testdata" / "stub_harness.py"
RECORDED = HERE / "testdata"
REAL_GIT = shutil.which("git")
KEY = "sk-or-test-SENTINEL-7f3a9c"
TODAY = datetime.date.today().isoformat()


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd)] + list(args), check=True,
                          capture_output=True, text=True).stdout


def write(path, content, mode=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    if mode:
        path.chmod(mode)


SUITE = {
    "skill_name": "demo-skill",
    "evals": [
        {"id": 1, "eval_name": "first-eval", "prompt": "Do the first thing.",
         "files": [{"path": "CLAUDE.md", "content": "# Fixture\r\nno trailing newline"}],
         "assertions": [{"text": "ASSERTION-ONE-TEXT", "spec_ids": ["DEMO-001"]}]},
        {"id": 2, "eval_name": "second-eval", "prompt": "Do the second thing.",
         "files": [{"path": "docs/a.md", "content": "a\n"}],
         "assertions": [{"text": "ASSERTION-TWO-TEXT", "spec_ids": ["DEMO-002"]}]},
        {"id": 3, "eval_name": "empty-fixture", "prompt": "Start from nothing.",
         "files": [], "assertions": [{"text": "ASSERTION-THREE-TEXT", "spec_ids": []}]},
        {"id": 4242, "eval_name": "secret-name-flagged", "prompt": "Handle the special case.",
         "files": [{"path": "x.md", "content": "x\n"}],
         "assertions": [{"text": "ASSERTION-SECRET-TEXT", "spec_ids": ["DEMO-003"]}]},
    ],
}


class FakeRepo:
    """A throwaway git repository shaped like LID's, with the runner copied in."""

    def __init__(self, suite=SUITE):
        self.tmp = Path(tempfile.mkdtemp(prefix="alt-eval-test-"))
        self.root = self.tmp / "repo"
        self.state = self.tmp / "stub-state"
        self.bin = self.tmp / "bin"
        self.home = self.tmp / "home"
        self.cache = self.tmp / "cache"
        for d in (self.state, self.bin, self.home, self.cache):
            d.mkdir(parents=True)
        r = self.root
        write(r / ".gitignore", "plugins/*/skills/*-workspace/\n")
        write(r / "tools/alt-model-evals/run_eval.py", (HERE / "run_eval.py").read_text(), 0o755)
        write(r / "tools/alt-model-evals/Dockerfile", (HERE / "Dockerfile").read_text())
        p = r / "plugins/demo-plugin"
        write(p / ".claude-plugin/plugin.json", '{"name": "demo-plugin", "version": "9.9.9"}\n')
        write(p / "skills/demo-skill/SKILL.md", "# Demo skill\n")
        write(p / "skills/demo-skill/evals/evals.json", json.dumps(suite, indent=2))
        write(p / "skills/sibling/SKILL.md", "# Sibling\n")
        write(p / "skills/sibling/references/notes.md", "notes\n")
        write(p / "skills/sibling/references/evals/hidden.json", "{}\n")
        write(p / "skills/other-plugin-skill-workspace/old-run.txt", "earlier run\n")
        write(r / "plugins/other-plugin/skills/linked/SKILL.md", "see ../../../demo-plugin\n")
        git(r, "init", "-q")
        git(r, "add", "-A")
        git(r, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
        for name in ("docker", "npx", "git"):
            write(self.bin / name, '#!/bin/sh\nSTUB_STATE="%s" REAL_GIT="%s" exec "%s" "%s" %s "$@"\n'
                  % (self.state, REAL_GIT, sys.executable, STUB, name), 0o755)
        (self.state / "decoy-git").mkdir()
        (self.state / "decoy-git" / "index.lock").write_text("must survive\n")
        self.workspace = p / "skills/demo-skill-workspace"

    STUB_SETTINGS = {"STUB_MODE": "mode", "STUB_DOCKER_INFO_FAIL": "docker-info-fail",
                     "STUB_REASONING": "reasoning",
                     "STUB_BUILD_SLEEP": "build-sleep", "STUB_MEM_TOTAL": "mem-total"}

    def env(self, **extra):
        for var, fname in self.STUB_SETTINGS.items():
            if var in extra:
                (self.state / fname).write_text(extra.pop(var))
        env = {
            "PATH": "%s:%s" % (self.bin, os.environ["PATH"]),
            "HOME": str(self.home),
            "XDG_CACHE_HOME": str(self.cache),
            "OPENROUTER_API_KEY": KEY,
            "LANG": "C.UTF-8",
        }
        env.update({k: v for k, v in extra.items() if v is not None})
        for k, v in extra.items():
            if v is None:
                env.pop(k, None)
        return env

    def run(self, *args, cwd=None, timeout=120, stdin=subprocess.DEVNULL, **env):
        return subprocess.run(
            [sys.executable, str(self.root / "tools/alt-model-evals/run_eval.py")] + list(args),
            cwd=str(cwd or self.root), env=self.env(**env), capture_output=True, text=True,
            timeout=timeout, stdin=stdin)

    def popen(self, *args, **env):
        return subprocess.Popen(
            [sys.executable, str(self.root / "tools/alt-model-evals/run_eval.py")] + list(args),
            cwd=str(self.root), env=self.env(**env), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, stdin=subprocess.DEVNULL)

    def calls(self, kind=None):
        log = self.state / "calls.jsonl"
        if not log.exists():
            return []
        entries = [json.loads(l) for l in log.read_text().splitlines()]
        return [e for e in entries if kind is None or e["kind"] == kind]

    def batch_dirs(self):
        if not self.workspace.exists():
            return []
        return sorted(d for d in self.workspace.iterdir() if d.is_dir())

    def batch(self):
        dirs = self.batch_dirs()
        assert len(dirs) == 1, dirs
        return dirs[0]

    def run_dir(self, eval_dir_name, n=1):
        return self.batch() / eval_dir_name / "with_skill" / ("run-%d" % n)

    def scratch_root(self):
        return self.cache / "lid-alt-evals"

    def cleanup(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class RepoTest(unittest.TestCase):
    def setUp(self):
        self.repo = FakeRepo()

    def tearDown(self):
        self.repo.cleanup()

    def ok_run(self, *args, **env):
        res = self.repo.run(*args, **env)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        return res


# ---------------------------------------------------------------- unit tests

class SelectorTests(unittest.TestCase):
    IDS = [0, 1, 2, 5, 9]

    # @spec ALT-EVAL-CLI-003
    def test_selector_forms(self):
        self.assertEqual(run_eval.parse_selector("all", self.IDS), [0, 1, 2, 5, 9])
        self.assertEqual(run_eval.parse_selector("5", self.IDS), [5])
        self.assertEqual(run_eval.parse_selector("9,1", self.IDS), [1, 9])
        self.assertEqual(run_eval.parse_selector("0-2", self.IDS), [0, 1, 2])
        self.assertEqual(run_eval.parse_selector("0,2-9", self.IDS), [0, 2, 5, 9])

    # @spec ALT-EVAL-CLI-004
    def test_selector_errors(self):
        with self.assertRaises(run_eval.UsageError) as cm:
            run_eval.parse_selector("1,3,7", self.IDS)
        self.assertIn("3", str(cm.exception))
        self.assertIn("7", str(cm.exception))
        with self.assertRaises(run_eval.UsageError):
            run_eval.parse_selector("6-8", self.IDS)
        self.assertEqual(run_eval.parse_selector("1-6", self.IDS), [1, 2, 5])


class PureFunctionTests(unittest.TestCase):
    # @spec ALT-EVAL-OUT-001, ALT-EVAL-OUT-003
    def test_sanitize(self):
        self.assertEqual(run_eval.sanitize("z-ai/glm-5.3-flash:free"), "z-ai_glm-5.3-flash_free")
        self.assertEqual(run_eval.sanitize("a b/c"), "a_b_c")

    # @spec ALT-EVAL-STAGE-007
    def test_opencode_config(self):
        cfg = run_eval.opencode_config("/work/plugins", "z-ai/glm-5.3", "medium")
        self.assertEqual(sorted(cfg), ["agent", "autoupdate", "provider", "share", "skills"])
        self.assertEqual(cfg["agent"], {"title": {"disable": True}})
        self.assertEqual(cfg["provider"]["openrouter"]["models"],
                         {"z-ai/glm-5.3": {"options": {"reasoning": {"effort": "medium"}}}})
        bare = run_eval.opencode_config("/work/plugins", "z-ai/glm-5.3", "default")
        self.assertNotIn("models", bare["provider"]["openrouter"])
        self.assertEqual(cfg["skills"], {"paths": ["/work/plugins"]})
        self.assertIs(cfg["autoupdate"], False)
        self.assertEqual(cfg["share"], "disabled")
        self.assertEqual(bare["provider"], {"openrouter": {"options": {"apiKey": "{env:OPENROUTER_API_KEY}"}}})

    # @spec ALT-EVAL-BOX-001
    def test_harness_argv(self):
        self.assertEqual(
            run_eval.harness_argv("z-ai/glm-5.3-flash", "do $(rm -rf /) `x`"),
            ["opencode", "run", "--pure", "--auto", "--format", "json",
             "-m", "openrouter/z-ai/glm-5.3-flash", "do $(rm -rf /) `x`"])

    # @spec ALT-EVAL-CLI-011
    def test_harness_argv_variant(self):
        self.assertEqual(
            run_eval.harness_argv("z-ai/glm-5.3", "p", variant="high"),
            ["opencode", "run", "--pure", "--auto", "--format", "json",
             "-m", "openrouter/z-ai/glm-5.3", "--variant", "high", "p"])
        self.assertEqual(run_eval.harness_argv("z-ai/glm-5.3", "p", variant=None),
                         run_eval.harness_argv("z-ai/glm-5.3", "p"))

    # @spec ALT-EVAL-BOX-002
    def test_single_harness_version_constant(self):
        self.assertEqual(run_eval.HARNESS, "opencode-ai@" + run_eval.HARNESS_VERSION)
        source = (HERE / "run_eval.py").read_text()
        self.assertEqual(source.count(run_eval.HARNESS_VERSION), 1)

    # @spec ALT-EVAL-STAGE-008, ALT-EVAL-STAGE-009
    def test_prompt_template(self):
        prompt = run_eval.build_prompt("my-skill", "/work/plugins",
                                       "Run /thing on this.", "2026-09-26")
        self.assertNotIn("SKILL.md", prompt)
        parts = ["one eval run of an agent skill", "skill named `my-skill`", "skill tool",
                 "/work/plugins", '"Run /thing on this."', "non-interactive",
                 "final response which defaults", "2026-09-26", "exact user-facing response"]
        positions = [prompt.find(p) for p in parts]
        self.assertTrue(all(i >= 0 for i in positions), list(zip(parts, positions)))
        self.assertEqual(positions, sorted(positions))

    # @spec ALT-EVAL-RUN-001, ALT-EVAL-RUN-002, ALT-EVAL-RUN-003
    def test_classify(self):
        c = run_eval.classify
        self.assertEqual(c(0, False, False, False), "completed")
        self.assertEqual(c(1, False, False, False), "harness_error")
        self.assertEqual(c(0, True, False, False), "harness_error")
        self.assertEqual(c(None, False, True, False), "timeout")
        self.assertEqual(c(None, False, False, True), "interrupted")

    # @spec ALT-EVAL-OUT-006, ALT-EVAL-OUT-010, ALT-EVAL-RUN-003
    def test_summarize_events(self):
        lines = [
            json.dumps({"type": "text", "part": {"type": "text", "text": "early"}}),
            json.dumps({"type": "tool_use", "part": {"tool": "read", "state": {"status": "error"}}}),
            json.dumps({"type": "tool_use", "part": {"tool": "bash", "state": {"status": "completed"}}}),
            json.dumps({"type": "step_finish", "part": {"cost": 0.25, "tokens": {"input": 10, "cache": {"read": 3}}}}),
            json.dumps({"type": "step_finish", "part": {"cost": 0.5, "tokens": {"input": 1, "cache": {"read": 1}}}}),
            json.dumps({"type": "text", "part": {"type": "text", "text": "final"}}),
            "not json at all",
        ]
        s = run_eval.summarize_events(lines)
        self.assertEqual(s["response"], "final")
        self.assertEqual(s["tool_calls"], 2)
        self.assertAlmostEqual(s["total_cost_usd"], 0.75)
        self.assertEqual(s["tokens"], {"input": 11, "cache": {"read": 4}})
        self.assertFalse(s["has_error"])
        s = run_eval.summarize_events([json.dumps({"type": "error", "error": {"data": {"message": "boom"}}})])
        self.assertTrue(s["has_error"])
        self.assertEqual(s["error_message"], "boom")
        self.assertIsNone(s["total_cost_usd"])
        self.assertIsNone(s["tokens"])
        self.assertEqual(s["response"], "")

    # @spec ALT-EVAL-OUT-013
    def test_recorded_streams(self):
        lines = (RECORDED / "opencode-events-completed.jsonl").read_text().splitlines()
        events = [json.loads(l) for l in lines]
        s = run_eval.summarize_events(lines)
        self.assertEqual(s["response"], [e for e in events if e["type"] == "text"][-1]["part"]["text"])
        self.assertTrue(s["response"].startswith("**Defaults taken"))
        self.assertEqual(s["tool_calls"], 2)
        costs = [e["part"]["cost"] for e in events if e["type"] == "step_finish"]
        self.assertAlmostEqual(s["total_cost_usd"], sum(costs))
        self.assertEqual(set(s["tokens"]), {"total", "input", "output", "reasoning", "cache"})
        self.assertFalse(s["has_error"])
        s = run_eval.summarize_events((RECORDED / "opencode-events-auth-error.jsonl").read_text().splitlines())
        self.assertTrue(s["has_error"])
        self.assertEqual(s["error_message"], "Missing Authentication header")

    # @spec ALT-EVAL-RUN-002
    def test_only_top_level_error_events_count(self):
        lines = [json.dumps({"type": "tool_use", "part": {"type": "error", "state": {"status": "error"}}}),
                 json.dumps([{"type": "error"}]),
                 json.dumps({"type": "text", "part": {"type": "text", "text": "done"}})]
        self.assertFalse(run_eval.summarize_events(lines)["has_error"])

    # @spec ALT-EVAL-BOX-003
    def test_dockerfile(self):
        text = (HERE / "Dockerfile").read_text()
        m = re.search(r"^FROM\s+node:(\S+)", text, re.M)
        self.assertIsNotNone(m)
        self.assertRegex(m.group(1), r"^\d+\.\d+\.\d+")
        self.assertRegex(text, r"ARG\s+OPENCODE_VERSION")
        self.assertIn("opencode-ai@${OPENCODE_VERSION}", text)
        self.assertIn("git", text)
        self.assertIn("ripgrep", text)

    # @spec ALT-EVAL-CLI-009
    def test_stdlib_only(self):
        source = (HERE / "run_eval.py").read_text()
        imported = set(re.findall(r"^\s*(?:import|from)\s+([A-Za-z_][\w]*)", source, re.M))
        stdlib = {"argparse", "datetime", "hashlib", "json", "os", "pathlib", "re", "shutil",
                  "signal", "subprocess", "sys", "tempfile", "time", "uuid", "secrets",
                  "stat", "errno", "__future__", "typing", "contextlib"}
        self.assertLessEqual(imported, stdlib)


# --------------------------------------------------------- end-to-end tests

class CliTests(RepoTest):
    # @spec ALT-EVAL-CLI-001, ALT-EVAL-CLI-002
    def test_unknown_or_ambiguous_skill(self):
        res = self.repo.run("no-such-skill", "1", "m/x")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("no-such-skill", res.stderr)
        self.assertEqual(self.repo.calls("harness"), [])
        # A skill without evals/evals.json is not a match.
        res = self.repo.run("sibling", "1", "m/x")
        self.assertNotEqual(res.returncode, 0)
        write(self.repo.root / "plugins/other-plugin/skills/demo-skill/evals/evals.json", json.dumps(SUITE))
        res = self.repo.run("demo-skill", "1", "m/x")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("demo-plugin", res.stderr)
        self.assertIn("other-plugin", res.stderr)

    # @spec ALT-EVAL-CLI-004
    def test_missing_id_stops_before_running(self):
        res = self.repo.run("demo-skill", "1,77", "m/x")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("77", res.stderr)
        self.assertEqual(self.repo.calls("harness"), [])

    # @spec ALT-EVAL-CLI-005, ALT-EVAL-CLI-007
    def test_runs_are_eval_major_and_sequential(self):
        self.ok_run("demo-skill", "2,1", "m/x", "--runs", "2")
        prompts = [c["argv"][-1] for c in self.repo.calls("harness")]
        order = ["first" if "first thing" in p else "second" for p in prompts]
        self.assertEqual(order, ["first", "first", "second", "second"])
        b = self.repo.batch()
        for name in ("eval-1-first-eval", "eval-2-second-eval"):
            for n in (1, 2):
                self.assertTrue((b / name / "with_skill" / ("run-%d" % n) / "timing.json").exists())

    # @spec ALT-EVAL-CLI-006
    def test_timeout_excludes_image_build(self):
        res = self.ok_run("demo-skill", "1", "m/x", "--timeout", "2", STUB_BUILD_SLEEP="3")
        timing = json.loads((self.repo.run_dir("eval-1-first-eval") / "timing.json").read_text())
        self.assertEqual(timing["status"], "completed")

    # @spec ALT-EVAL-CLI-008
    def test_summary_output(self):
        res = self.ok_run("demo-skill", "1", "m/x", "--runs", "2")
        lines = [l for l in res.stdout.splitlines() if "completed" in l]
        self.assertEqual(len(lines), 2)
        for n, line in enumerate(lines, 1):
            self.assertIn("1", line)
            self.assertIn(str(n), line)
            self.assertIn("0.75", line)
        self.assertIn(str(self.repo.batch()), res.stdout)

    # @spec ALT-EVAL-CLI-011, ALT-EVAL-OUT-014
    def test_variant_passed_and_recorded(self):
        self.ok_run("demo-skill", "1", "m/x", "--runs", "2", "--variant", "minimal")
        harness_calls = [c for c in self.repo.calls("docker-run") if c["cmd"][:1] == ["opencode"]]
        self.assertEqual(len(harness_calls), 2)
        for call in harness_calls:
            i = call["cmd"].index("--variant")
            self.assertEqual(call["cmd"][i + 1], "minimal")
        b = self.repo.batch()
        self.assertTrue(b.name.endswith("-m_x-minimal"), b.name)
        self.assertEqual(json.loads((b / "batch.json").read_text())["variant"], "minimal")

    # @spec ALT-EVAL-CLI-011, ALT-EVAL-OUT-014
    def test_no_variant_by_default(self):
        self.ok_run("demo-skill", "1", "m/x")
        self.assertNotIn("--variant", self.repo.calls("docker-run")[0]["cmd"])
        b = self.repo.batch()
        self.assertTrue(b.name.endswith("-m_x"), b.name)
        self.assertIsNone(json.loads((b / "batch.json").read_text())["variant"])

    # @spec ALT-EVAL-CLI-012, ALT-EVAL-OUT-014
    def test_effort_default_is_medium(self):
        self.ok_run("demo-skill", "1", "m/x", STUB_REASONING="900")
        cfg = json.loads(self.repo.calls("harness")[0]["config"])
        self.assertEqual(cfg["provider"]["openrouter"]["models"]["m/x"]["options"]["reasoning"],
                         {"effort": "medium"})
        b = self.repo.batch()
        self.assertTrue(b.name.endswith("-m_x"), b.name)
        self.assertEqual(json.loads((b / "batch.json").read_text())["effort"], "medium")

    # @spec ALT-EVAL-CLI-012, ALT-EVAL-OUT-014
    def test_effort_level_and_default_keyword(self):
        self.ok_run("demo-skill", "1", "m/x", "--effort", "high", STUB_REASONING="900")
        cfg = json.loads(self.repo.calls("harness")[0]["config"])
        self.assertEqual(cfg["provider"]["openrouter"]["models"]["m/x"]["options"]["reasoning"],
                         {"effort": "high"})
        self.assertTrue(self.repo.batch().name.endswith("-m_x-high"))
        shutil.rmtree(self.repo.workspace)
        (self.repo.state / "calls.jsonl").unlink()
        self.ok_run("demo-skill", "1", "m/x", "--effort", "default")
        cfg = json.loads(self.repo.calls("harness")[0]["config"])
        self.assertNotIn("models", cfg["provider"]["openrouter"])
        b = self.repo.batch()
        self.assertTrue(b.name.endswith("-m_x-default"), b.name)
        self.assertEqual(json.loads((b / "batch.json").read_text())["effort"], "default")

    # @spec ALT-EVAL-OUT-015
    def test_reasoning_report_and_warning(self):
        res = self.ok_run("demo-skill", "1", "m/x", "--runs", "2")
        self.assertIn("median reasoning tokens: 0", res.stdout)
        self.assertIn("WARNING", res.stdout + res.stderr)
        shutil.rmtree(self.repo.workspace)
        res = self.ok_run("demo-skill", "1", "m/x", STUB_REASONING="900")
        self.assertIn("median reasoning tokens: 900", res.stdout)
        self.assertNotIn("WARNING", res.stdout + res.stderr)
        shutil.rmtree(self.repo.workspace)
        res = self.ok_run("demo-skill", "1", "m/x", "--effort", "default")
        self.assertNotIn("WARNING", res.stdout + res.stderr)

    # @spec ALT-EVAL-CLI-010
    def test_runs_from_any_directory(self):
        res = self.repo.run("demo-skill", "1", "m/x", cwd=self.repo.tmp)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(len(self.repo.batch_dirs()), 1)


class KeyTests(RepoTest):
    # @spec ALT-EVAL-KEY-001, ALT-EVAL-KEY-002
    def test_missing_key_stops_before_staging(self):
        write(self.repo.home / ".secrets.conf", "OPENROUTER_KEY=%s\n" % KEY)
        for value in (None, ""):
            res = self.repo.run("demo-skill", "1", "m/x", OPENROUTER_API_KEY=value)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("OPENROUTER_API_KEY", res.stderr)
        self.assertEqual(self.repo.calls("harness"), [])
        self.assertFalse(self.repo.scratch_root().exists() and any(self.repo.scratch_root().iterdir()))

    # @spec ALT-EVAL-KEY-003
    def test_key_only_in_environments(self):
        self.ok_run("demo-skill", "1", "m/x")
        for call in self.repo.calls():
            if "argv" in call:
                self.assertNotIn(KEY, json.dumps(call["argv"]))
        run_call = self.repo.calls("docker-run")[0]
        self.assertIn("OPENROUTER_API_KEY", run_call["envs"])
        harness = self.repo.calls("harness")[0]
        self.assertEqual(harness["env"]["OPENROUTER_API_KEY"], KEY)
        self.assertNotIn(KEY, harness["config"])

    # @spec ALT-EVAL-KEY-004
    def test_key_redacted_from_every_output(self):
        self.ok_run("demo-skill", "1", "m/x")
        batch = self.repo.batch()
        for path in batch.rglob("*"):
            if path.is_file() and not path.is_symlink():
                self.assertNotIn(KEY.encode(), path.read_bytes(), path)
        run = self.repo.run_dir("eval-1-first-eval")
        self.assertIn(b"[REDACTED]", (run / "events.jsonl").read_bytes())
        self.assertIn(b"[REDACTED]", (run / "stderr.log").read_bytes())
        self.assertIn("[REDACTED]", (run / "response.md").read_text())
        leak = run / "project" / "leak.sh"
        self.assertIn(b"[REDACTED]", leak.read_bytes())
        self.assertTrue(leak.stat().st_mode & stat.S_IXUSR)
        self.assertTrue((run / "project" / "link.txt").is_symlink())


class StagingTests(RepoTest):
    # @spec ALT-EVAL-STAGE-001, ALT-EVAL-STAGE-010
    def test_scratch_location_and_cleanup(self):
        self.ok_run("demo-skill", "4242", "m/x")
        run_call = self.repo.calls("docker-run")[0]
        project_mount = [m for m in run_call["mounts"] if ":/work/project" in m][0].split(":")[0]
        scratch = Path(project_mount).parent
        self.assertEqual(scratch.parent, self.repo.scratch_root())
        for word in ("demo", "skill", "4242", "secret", "flagged"):
            self.assertNotIn(word, scratch.name)
        self.assertFalse(scratch.exists())

    # @spec ALT-EVAL-STAGE-002
    def test_fixture_written_exactly(self):
        self.ok_run("demo-skill", "1", "m/x")
        captured = self.repo.run_dir("eval-1-first-eval") / "project" / "CLAUDE.md"
        self.assertEqual(captured.read_bytes(), b"# Fixture\r\nno trailing newline")

    # @spec ALT-EVAL-STAGE-003
    def test_bad_fixture_paths_stop_the_batch(self):
        for bad in ("/etc/evil", "docs/../../evil", ".git/config"):
            suite = json.loads(json.dumps(SUITE))
            suite["evals"][1]["files"].append({"path": bad, "content": "x"})
            path = self.repo.root / "plugins/demo-plugin/skills/demo-skill/evals/evals.json"
            path.write_text(json.dumps(suite))
            res = self.repo.run("demo-skill", "1,2", "m/x")
            self.assertNotEqual(res.returncode, 0)
            self.assertIn(bad, res.stderr)
            self.assertIn("2", res.stderr)
        self.assertEqual(self.repo.calls("harness"), [])

    # @spec ALT-EVAL-STAGE-004
    def test_fixture_commit(self):
        self.ok_run("demo-skill", "1,3", "m/x")
        logs = [c["fixture_log"].strip() for c in self.repo.calls("harness")]
        self.assertEqual(logs, ["eval <eval@localhost>|fixture"] * 2)
        empty = self.repo.run_dir("eval-3-empty-fixture") / "project"
        created_by_stub = {"committed.txt", "made.txt", "leak.sh", "link.txt"}
        self.assertEqual({p.name for p in empty.iterdir()}, created_by_stub)

    # @spec ALT-EVAL-STAGE-005, ALT-EVAL-STAGE-006
    def test_plugins_copy(self):
        self.ok_run("demo-skill", "1", "m/x")
        listing = self.repo.calls("harness")[0]["plugins_listing"]
        self.assertIn("demo-plugin/.claude-plugin/plugin.json", listing)
        self.assertIn("demo-plugin/skills/sibling/references/notes.md", listing)
        self.assertIn("other-plugin/skills/linked/SKILL.md", listing)
        for entry in listing:
            parts = entry.rstrip("/").split("/")
            self.assertNotIn("evals", parts, entry)
            self.assertFalse(any(p.endswith("-workspace") for p in parts), entry)

    # @spec ALT-EVAL-STAGE-007
    def test_config_file(self):
        self.ok_run("demo-skill", "1", "m/x")
        cfg = json.loads(self.repo.calls("harness")[0]["config"])
        self.assertEqual(cfg, run_eval.opencode_config("/work/plugins", "m/x", "medium"))

    # @spec ALT-EVAL-STAGE-008, ALT-EVAL-STAGE-009
    def test_prompt_sent(self):
        self.ok_run("demo-skill", "4242", "m/x")
        prompt = self.repo.calls("harness")[0]["argv"][-1]
        self.assertIn('"Handle the special case."', prompt)
        self.assertIn("skill named `demo-skill`", prompt)
        self.assertNotIn("SKILL.md", prompt)
        for leak in ("4242", "secret-name-flagged", "ASSERTION-SECRET-TEXT"):
            self.assertNotIn(leak, prompt)

    # @spec ALT-EVAL-STAGE-008
    def test_prompt_uses_frontmatter_name(self):
        write(self.repo.root / "plugins/demo-plugin/skills/demo-skill/SKILL.md",
              "---\nname: demo-renamed\ndescription: d\n---\n# Demo skill\n")
        self.ok_run("demo-skill", "1", "m/x")
        self.assertIn("skill named `demo-renamed`", self.repo.calls("harness")[0]["argv"][-1])

    # @spec ALT-EVAL-STAGE-011, ALT-EVAL-OUT-011
    def test_plugins_tree_id(self):
        r = self.repo.root
        write(r / "plugins/demo-plugin/skills/demo-skill/SKILL.md", "# Demo skill, edited\n")
        write(r / "plugins/demo-plugin/skills/demo-skill/references/new.md", "untracked\n")
        status_before = git(r, "status", "--porcelain")
        head_before = git(r, "rev-parse", "HEAD")
        self.ok_run("demo-skill", "1", "m/x")
        self.assertEqual(git(r, "status", "--porcelain"), status_before)
        self.assertEqual(git(r, "rev-parse", "HEAD"), head_before)
        batch = json.loads((self.repo.batch() / "batch.json").read_text())
        self.assertEqual(batch["head_commit"], head_before.strip())
        self.assertFalse(batch["plugins_tree_matches_head"])
        git(r, "add", "plugins")
        git(r, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "tested edit")
        self.assertEqual(batch["plugins_tree"], git(r, "rev-parse", "HEAD:plugins").strip())

    # @spec ALT-EVAL-STAGE-011, ALT-EVAL-OUT-011
    def test_plugins_tree_clean(self):
        self.ok_run("demo-skill", "1", "m/x")
        batch = json.loads((self.repo.batch() / "batch.json").read_text())
        self.assertTrue(batch["plugins_tree_matches_head"])
        self.assertEqual(batch["plugins_tree"], git(self.repo.root, "rev-parse", "HEAD:plugins").strip())


class ContainerTests(RepoTest):
    def run_call(self):
        self.ok_run("demo-skill", "1", "m/x")
        return self.repo.calls("docker-run")[0]

    # @spec ALT-EVAL-BOX-001
    def test_harness_command_and_closed_stdin(self):
        # stdin left open by the caller: the runner must still close the harness's stdin.
        res = self.repo.run("demo-skill", "1", "z-ai/glm-5.3-flash", stdin=subprocess.PIPE, timeout=60)
        self.assertEqual(res.returncode, 0, res.stderr)
        call = self.repo.calls("docker-run")[0]
        self.assertEqual(call["cmd"][:-1], run_eval.harness_argv("z-ai/glm-5.3-flash", "")[:-1])
        self.assertEqual(self.repo.calls("harness")[0]["stdin_len"], 0)

    # @spec ALT-EVAL-BOX-002, ALT-EVAL-BOX-004
    def test_image_tag_and_build_once(self):
        self.ok_run("demo-skill", "1", "m/x", "--runs", "2")
        builds = [c for c in self.repo.calls("docker") if c["argv"][0] == "build"]
        self.assertEqual(len(builds), 1)
        argv = builds[0]["argv"]
        self.assertIn("OPENCODE_VERSION=" + run_eval.HARNESS_VERSION, argv)
        tag = argv[argv.index("-t") + 1]
        self.assertIn(run_eval.HARNESS_VERSION, tag)
        dockerfile = (self.repo.root / "tools/alt-model-evals/Dockerfile").read_bytes()
        self.assertEqual(tag, run_eval.image_tag(dockerfile))
        images = {c["image"] for c in self.repo.calls("docker-run")}
        self.assertEqual(images, {tag})
        timing = json.loads((self.repo.run_dir("eval-1-first-eval") / "timing.json").read_text())
        self.assertEqual(timing["harness"], run_eval.HARNESS)

    # @spec ALT-EVAL-BOX-005, ALT-EVAL-BOX-007, ALT-EVAL-BOX-008
    def test_mounts(self):
        call = self.run_call()
        targets = {}
        for m in call["mounts"]:
            parts = m.split(":")
            targets[parts[1]] = parts[2:] if len(parts) > 2 else []
        self.assertEqual(set(targets), {"/work/project", "/work/plugins", "/work/opencode.json",
                                        "/etc/passwd", "/etc/group"})
        self.assertEqual(targets["/work/project"], [])
        for ro in ("/work/plugins", "/work/opencode.json", "/etc/passwd", "/etc/group"):
            self.assertEqual(targets[ro], ["ro"], ro)
        self.assertEqual(call["workdir"], "/work/project")
        self.assertIn("OPENCODE_CONFIG=/work/opencode.json", call["envs"])
        passwd = call["passwd"].strip().splitlines()
        self.assertEqual(len(passwd), 1)
        fields = passwd[0].split(":")
        self.assertEqual(fields[2:4], [str(os.getuid()), str(os.getgid())])
        self.assertEqual(fields[5], "/home/eval")

    # @spec ALT-EVAL-BOX-009, ALT-EVAL-BOX-010, ALT-EVAL-BOX-011
    def test_hardening(self):
        call = self.run_call()
        opts = [tuple(o) for o in call["opts"]]
        self.assertIn(("--read-only",), opts)
        tmpfs = [o[1] for o in opts if o[0] == "--tmpfs"]
        self.assertTrue(any(t.startswith("/home/eval") for t in tmpfs))
        self.assertTrue(any(t.startswith("/tmp") for t in tmpfs))
        self.assertIn(("--user", "%d:%d" % (os.getuid(), os.getgid())), opts)
        self.assertIn(("--cap-drop", "ALL"), opts)
        self.assertIn(("--security-opt", "no-new-privileges"), opts)
        self.assertIn(("--memory", "2g"), opts)
        self.assertIn(("--pids-limit", "512"), opts)

    # @spec ALT-EVAL-BOX-012
    def test_container_environment(self):
        call = self.run_call()
        names = {e.split("=", 1)[0] for e in call["envs"]}
        locale = {n for n in names if n in ("LANG", "LC_ALL")}
        self.assertEqual(names - locale, {"OPENROUTER_API_KEY", "HOME", "OPENCODE_CONFIG",
                                          "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL",
                                          "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"})
        self.assertIn("HOME=/home/eval", call["envs"])
        self.assertIn("GIT_AUTHOR_NAME=eval", call["envs"])
        self.assertIn("GIT_COMMITTER_EMAIL=eval@localhost", call["envs"])

    # @spec ALT-EVAL-BOX-016
    def test_runtime_too_small(self):
        res = self.repo.run("demo-skill", "1", "m/x", STUB_MEM_TOTAL=str(1900 * 1024 * 1024))
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("memory", res.stderr)
        self.assertIn("2.0 GiB", res.stderr)
        self.assertIn("1.9 GiB", res.stderr)
        self.assertEqual(self.repo.calls("harness"), [])
        self.assertEqual(self.repo.batch_dirs(), [])

    # @spec ALT-EVAL-BOX-006
    def test_no_runtime(self):
        res = self.repo.run("demo-skill", "1", "m/x", STUB_DOCKER_INFO_FAIL="1")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("--no-container", res.stderr)
        self.assertEqual(self.repo.calls("harness"), [])
        self.assertEqual(self.repo.batch_dirs(), [])


class CaptureTests(RepoTest):
    def capture_call(self):
        return [c for c in self.repo.calls("docker-run") if c["cmd"][0] != "opencode"][0]

    # @spec ALT-EVAL-BOX-017
    def test_capture_container(self):
        self.ok_run("demo-skill", "1", "m/x")
        runs = self.repo.calls("docker-run")
        self.assertEqual([c["cmd"][0] == "opencode" for c in runs], [True, False])
        cap, harness = runs[1], runs[0]
        self.assertEqual(cap["image"], harness["image"])
        targets = {m.split(":")[1]: m.split(":")[2:] for m in cap["mounts"]}
        self.assertEqual(set(targets), {"/work/project", "/work/out", "/etc/passwd", "/etc/group"})
        self.assertEqual(targets["/work/project"], [])
        self.assertEqual(targets["/work/out"], [])
        opts = [tuple(o) for o in cap["opts"]]
        self.assertIn(("--network", "none"), opts)
        for o in [("--read-only",), ("--cap-drop", "ALL"), ("--security-opt", "no-new-privileges"),
                  ("--memory", "2g"), ("--pids-limit", "512"),
                  ("--user", "%d:%d" % (os.getuid(), os.getgid()))]:
            self.assertIn(o, opts)
        tmpfs = [o[1] for o in opts if o[0] == "--tmpfs"]
        self.assertTrue(any(t.startswith("/home/eval") for t in tmpfs))
        self.assertTrue(any(t.startswith("/tmp") for t in tmpfs))
        self.assertFalse(any(e.split("=")[0] == "OPENROUTER_API_KEY" for e in cap["envs"]))
        run = self.repo.run_dir("eval-1-first-eval")
        self.assertIn("committed.txt", (run / "changes.patch").read_text())

    # @spec ALT-EVAL-BOX-019
    def test_capture_git_hardening(self):
        self.ok_run("demo-skill", "1", "m/x")
        script = " ".join(self.capture_call()["cmd"])
        for flag in ("core.fsmonitor=false", "core.hooksPath=/dev/null", "--no-ext-diff", "--no-textconv"):
            self.assertIn(flag, script)

    # @spec ALT-EVAL-BOX-018, ALT-EVAL-BOX-019
    def test_no_host_git_in_project_after_harness(self):
        self.ok_run("demo-skill", "1,2", "m/x", STUB_MODE="plant")
        started = set()  # projects whose harness has already started
        checked = 0
        for c in self.repo.calls():
            if c["kind"] == "docker-run" and c["cmd"][0] == "opencode":
                started.add([m for m in c["mounts"] if m.endswith(":/work/project")][0].split(":")[0])
            elif c["kind"] == "git" and not c["inside"]:
                touched = " ".join(c["argv"]) + " " + c["cwd"]
                for project in started:
                    self.assertNotIn(project, touched, c)
                checked += bool(started)
        self.assertEqual(len(started), 2)
        self.assertGreater(checked, 0)  # the second eval's staging ran after the first harness
        self.assertFalse((self.repo.state / "PWNED").exists())

    # @spec ALT-EVAL-BOX-018, ALT-EVAL-RUN-005
    def test_symlinked_git_dir_left_alone(self):
        self.repo.run("demo-skill", "1", "m/x", STUB_MODE="gitlink")
        self.assertEqual((self.repo.state / "decoy-git" / "index.lock").read_text(), "must survive\n")
        project = self.repo.run_dir("eval-1-first-eval") / "project"
        self.assertFalse((project / ".git").exists() or (project / ".git").is_symlink())

    # @spec ALT-EVAL-OUT-009
    def test_special_files_skipped(self):
        res = self.repo.run("demo-skill", "1", "m/x", STUB_MODE="fifo", timeout=90)
        self.assertEqual(res.returncode, 0, res.stderr)
        project = self.repo.run_dir("eval-1-first-eval") / "project"
        self.assertFalse((project / "pipe").exists())
        self.assertTrue((project / "committed.txt").exists())


class NoContainerTests(RepoTest):
    # @spec ALT-EVAL-BOX-013, ALT-EVAL-BOX-014, ALT-EVAL-BOX-015
    def test_no_container_mode(self):
        res = self.ok_run("demo-skill", "1", "m/x", "--no-container")
        self.assertIn("can read any file", res.stdout + res.stderr)
        self.assertEqual(self.repo.calls("docker"), [])
        npx = self.repo.calls("npx")[0]
        self.assertEqual(npx["argv"][:2], ["-y", run_eval.HARNESS])
        self.assertEqual(npx["argv"][2:-1], run_eval.harness_argv("m/x", "")[1:-1])
        h = self.repo.calls("harness")[0]
        env = h["env"]
        allowed = {"OPENROUTER_API_KEY", "PATH", "HOME", "OPENCODE_CONFIG", "npm_config_cache",
                   "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME",
                   "GIT_COMMITTER_EMAIL", "LANG", "LC_ALL",
                   # added by the stub's own wrapper, /bin/sh, and macOS python
                   "STUB_STATE", "STUB_INSIDE", "REAL_GIT", "PWD", "SHLVL", "_", "OLDPWD", "__CF_USER_TEXT_ENCODING"}
        self.assertEqual({k for k in env if k not in allowed and not k.startswith("XDG_")}, set())
        self.assertNotEqual(env["HOME"], str(self.repo.home))
        scratch = Path(h["cwd"]).parent
        self.assertFalse(Path(env["HOME"]).is_relative_to(scratch))
        for var in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
            self.assertTrue(env[var].startswith(env["HOME"]), var)
        self.assertEqual(env["npm_config_cache"], str(self.repo.home / ".npm"))
        self.assertFalse(Path(env["HOME"]).exists())
        prompt = h["argv"][-1]
        self.assertIn("skill named `demo-skill`", prompt)
        self.assertNotIn("/work/plugins", prompt)
        cfg = json.loads(h["config"])
        self.assertEqual([os.path.realpath(p) for p in cfg["skills"]["paths"]],
                         [os.path.realpath(scratch / "plugins")])
        batch = json.loads((self.repo.batch() / "batch.json").read_text())
        self.assertEqual(batch["sandbox"], "none")

    # @spec ALT-EVAL-BOX-014
    def test_no_leak_of_invoking_env(self):
        self.ok_run("demo-skill", "1", "m/x", "--no-container", GITHUB_TOKEN="ghp_should_not_leak",
                    ANTHROPIC_API_KEY="sk-ant-should-not-leak")
        env = self.repo.calls("harness")[0]["env"]
        self.assertNotIn("GITHUB_TOKEN", env)
        self.assertNotIn("ANTHROPIC_API_KEY", env)


class LifecycleTests(RepoTest):
    def timing(self, name="eval-1-first-eval", n=1):
        return json.loads((self.repo.run_dir(name, n) / "timing.json").read_text())

    # @spec ALT-EVAL-RUN-002
    def test_empty_final_message_is_completed(self):
        self.ok_run("demo-skill", "1", "m/x", STUB_MODE="empty")
        self.assertEqual(self.timing()["status"], "completed")
        self.assertEqual((self.repo.run_dir("eval-1-first-eval") / "response.md").read_text(), "")

    # @spec ALT-EVAL-RUN-003
    def test_failed_tool_call_is_not_harness_error(self):
        self.ok_run("demo-skill", "1", "m/x", STUB_MODE="toolfail")
        self.assertEqual(self.timing()["status"], "completed")

    # @spec ALT-EVAL-RUN-003
    def test_harness_errors(self):
        self.repo.run("demo-skill", "1", "m/x", STUB_MODE="error_event")
        t = self.timing()
        self.assertEqual(t["status"], "harness_error")
        self.assertEqual(t["error_message"], "Missing Authentication header")
        shutil.rmtree(self.repo.workspace)
        (self.repo.state / "mode-counter").unlink()
        self.repo.run("demo-skill", "1", "m/x", STUB_MODE="exit1")
        t = self.timing()
        self.assertEqual(t["status"], "harness_error")
        self.assertEqual(t["exit_code"], 1)

    # @spec ALT-EVAL-RUN-004, ALT-EVAL-RUN-005, ALT-EVAL-RUN-006
    def test_timeout(self):
        start = time.time()
        self.repo.run("demo-skill", "1", "m/x", "--timeout", "5", STUB_MODE="sleep")
        self.assertLess(time.time() - start, 60)
        self.assertEqual(self.timing()["status"], "timeout")
        stops = [c for c in self.repo.calls("docker") if c["argv"][0] in ("stop", "kill")]
        self.assertTrue(stops)
        self.assertEqual(stops[0]["argv"][0], "stop")
        self.assertIn("10", stops[0]["argv"])
        run = self.repo.run_dir("eval-1-first-eval")
        self.assertTrue((run / "project" / "partial.txt").exists())
        self.assertTrue((run / "git-log.txt").read_text().strip())
        self.assertEqual(list(self.repo.scratch_root().iterdir()), [])

    # @spec ALT-EVAL-RUN-005
    def test_timeout_no_container_kills_process_group(self):
        self.repo.run("demo-skill", "1", "m/x", "--timeout", "5", "--no-container", STUB_MODE="sleep")
        self.assertEqual(self.timing()["status"], "timeout")
        pid = int((self.repo.state / "npx.pid").read_text())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    # @spec ALT-EVAL-RUN-007, ALT-EVAL-OUT-012
    def test_abort_after_two_harness_errors_across_evals(self):
        res = self.repo.run("demo-skill", "1,2,3", "m/x", STUB_MODE="exit1")
        self.assertEqual(len(self.repo.calls("harness")), 2)
        batch = json.loads((self.repo.batch() / "batch.json").read_text())
        self.assertEqual(batch["state"], "aborted")

    # @spec ALT-EVAL-RUN-007
    def test_non_consecutive_errors_do_not_abort(self):
        self.repo.run("demo-skill", "1,2,3", "m/x", STUB_MODE="exit1,ok,exit1")
        self.assertEqual(len(self.repo.calls("harness")), 3)
        batch = json.loads((self.repo.batch() / "batch.json").read_text())
        self.assertEqual(batch["state"], "complete")

    # @spec ALT-EVAL-RUN-008
    def test_interrupt(self):
        proc = self.repo.popen("demo-skill", "1,2", "m/x", STUB_MODE="sleep")
        deadline = time.time() + 60
        while not list(self.repo.state.glob("*.pid")) and time.time() < deadline:
            time.sleep(0.2)
        time.sleep(0.5)
        proc.send_signal(signal.SIGINT)
        out, err = proc.communicate(timeout=60)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(self.timing()["status"], "interrupted")
        batch = json.loads((self.repo.batch() / "batch.json").read_text())
        self.assertEqual(batch["state"], "aborted")
        self.assertEqual(len(self.repo.calls("harness")), 1)
        self.assertEqual(list(self.repo.scratch_root().iterdir()), [])


class OutputTests(RepoTest):
    # @spec ALT-EVAL-OUT-001
    def test_batch_directory_name(self):
        self.ok_run("demo-skill", "1", "z-ai/glm-5.3-flash:free")
        self.assertEqual(self.repo.batch().name, "alt-model-%s-z-ai_glm-5.3-flash_free" % TODAY)

    # @spec ALT-EVAL-OUT-002
    def test_batch_directory_suffix(self):
        taken = self.repo.workspace / ("alt-model-%s-m_x" % TODAY)
        taken.mkdir(parents=True)
        (self.repo.workspace / ("alt-model-%s-m_x-2" % TODAY)).mkdir()
        self.ok_run("demo-skill", "1", "m/x")
        self.assertTrue((self.repo.workspace / ("alt-model-%s-m_x-3" % TODAY) / "batch.json").exists())
        self.assertFalse((taken / "batch.json").exists())

    # @spec ALT-EVAL-OUT-002
    def test_claim_is_atomic(self):
        ws = self.repo.tmp / "ws"
        a = run_eval.claim_batch_dir(ws, TODAY, "m_x")
        b = run_eval.claim_batch_dir(ws, TODAY, "m_x")
        self.assertNotEqual(a, b)
        self.assertTrue(a.is_dir() and b.is_dir())

    # @spec ALT-EVAL-OUT-003, ALT-EVAL-OUT-004, ALT-EVAL-OUT-005, ALT-EVAL-OUT-006
    def test_layout(self):
        self.ok_run("demo-skill", "4242", "m/x")
        eval_dir = self.repo.batch() / "eval-4242-secret-name-flagged"
        meta = json.loads((eval_dir / "eval_metadata.json").read_text())
        self.assertEqual(meta, {"eval_id": 4242, "eval_name": "secret-name-flagged",
                                "prompt": "Handle the special case.",
                                "assertions": SUITE["evals"][3]["assertions"]})
        run = eval_dir / "with_skill" / "run-1"
        for name in ("events.jsonl", "stderr.log", "response.md", "timing.json",
                     "changes.patch", "git-log.txt", "project"):
            self.assertTrue((run / name).exists(), name)
        self.assertEqual((run / "response.md").read_text(), "FINAL ANSWER leaked [REDACTED]")

    # @spec ALT-EVAL-OUT-007, ALT-EVAL-OUT-008
    def test_patch_and_log(self):
        self.ok_run("demo-skill", "1", "m/x")
        run = self.repo.run_dir("eval-1-first-eval")
        patch = (run / "changes.patch").read_text()
        self.assertIn("committed.txt", patch)
        self.assertIn("made.txt", patch)
        self.assertNotIn("CLAUDE.md", patch)
        log = (run / "git-log.txt").read_text()
        self.assertIn("model commit", log)
        self.assertIn("fixture", log)
        self.assertIn("Author:", log)
        self.assertIn("committed.txt", log)

    # @spec ALT-EVAL-OUT-009
    def test_project_capture(self):
        self.ok_run("demo-skill", "1", "m/x")
        project = self.repo.run_dir("eval-1-first-eval") / "project"
        self.assertFalse((project / ".git").exists())
        self.assertTrue((project / "link.txt").is_symlink())
        self.assertEqual(os.readlink(project / "link.txt"), "made.txt")
        self.assertTrue((project / "leak.sh").stat().st_mode & stat.S_IXUSR)

    # @spec ALT-EVAL-OUT-010
    def test_timing(self):
        self.ok_run("demo-skill", "1", "m/x")
        t = json.loads((self.repo.run_dir("eval-1-first-eval") / "timing.json").read_text())
        self.assertEqual(set(t), {"model", "harness", "status", "duration_ms", "total_cost_usd",
                                  "tokens", "tool_calls", "exit_code", "error_message"})
        self.assertEqual(t["model"], "m/x")
        self.assertAlmostEqual(t["total_cost_usd"], 0.75)
        self.assertEqual(t["tokens"], {"input": 11, "output": 7, "reasoning": 0, "cache": {"read": 3, "write": 1}})
        self.assertEqual(t["tool_calls"], 1)
        self.assertEqual(t["exit_code"], 0)
        self.assertIsInstance(t["duration_ms"], int)

    # @spec ALT-EVAL-OUT-010
    def test_timing_without_cost(self):
        self.ok_run("demo-skill", "1", "m/x", STUB_MODE="nocost")
        t = json.loads((self.repo.run_dir("eval-1-first-eval") / "timing.json").read_text())
        self.assertIsNone(t["total_cost_usd"])
        self.assertIsNone(t["tokens"])

    # @spec ALT-EVAL-OUT-011, ALT-EVAL-OUT-012
    def test_batch_record(self):
        self.ok_run("demo-skill", "1,2", "m/x", "--runs", "2", "--timeout", "30")
        b = json.loads((self.repo.batch() / "batch.json").read_text())
        for key in ("skill", "eval_ids", "model", "harness", "sandbox", "timeout", "runs",
                    "head_commit", "plugins_tree", "plugins_tree_matches_head", "state"):
            self.assertIn(key, b)
        self.assertEqual(b["skill"], "demo-skill")
        self.assertEqual(b["eval_ids"], [1, 2])
        self.assertEqual(b["sandbox"], "container")
        self.assertEqual(b["timeout"], 30)
        self.assertEqual(b["runs"], 2)
        self.assertEqual(b["state"], "complete")


if __name__ == "__main__":
    unittest.main(verbosity=1)
