"""Tests for costeval.executor: one turn of an executor session in its container."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from costeval import executor  # noqa: E402
from costeval.executor import ContainerSession, InitProblem  # noqa: E402

SECRET = "sk-ant-oat-not-a-real-token"


def session(**kw):
    base = dict(
        image="lid-cost-eval-executor:2.1.323",
        workspace_volume="bt-bare-s1-work",
        config_volume="bt-bare-s1-cfg",
        model="claude-sonnet-5-5",
        claude_code_version="2.1.323",
        expected_plugins={"cc-plugin-agents-md", "cc-plugin-telemetry"},
        timeout_s=60,
    )
    base.update(kw)
    return ContainerSession(**base)


def init_record(plugins, skills=(), model="claude-sonnet-5-5", version="2.1.323", memory=None, session_id="s1"):
    return {
        "type": "system", "subtype": "init", "session_id": session_id, "model": model,
        "claude_code_version": version, "memory_paths": memory,
        "plugins": [{"name": p, "path": "builtin", "source": p + "@builtin"} for p in plugins],
        "skills": list(skills),
    }


class CommandTest(unittest.TestCase):
    def test_runs_claude_headless_in_the_container_with_the_arm_volumes(self):
        cmd = executor.claude_command(session(), "Build it.", container_name="c1")
        self.assertEqual(cmd[:3], ["docker", "run", "--rm"])
        self.assertIn("bt-bare-s1-work:/work", cmd)
        self.assertIn("bt-bare-s1-cfg:/cfg", cmd)
        i = cmd.index("lid-cost-eval-executor:2.1.323")
        self.assertEqual(cmd[i + 1:i + 4], ["claude", "-p", "Build it."])
        for pair in (["--model", "claude-sonnet-5-5"], ["--effort", "medium"],
                     ["--permission-mode", "bypassPermissions"], ["--output-format", "stream-json"]):
            j = cmd.index(pair[0])
            self.assertEqual(cmd[j + 1], pair[1])
        self.assertIn("--verbose", cmd)

    def test_memory_is_off(self):
        cmd = executor.claude_command(session(), "x", container_name="c1")
        settings = json.loads(cmd[cmd.index("--settings") + 1])
        self.assertIs(settings["autoMemoryEnabled"], False)

    def test_the_token_enters_by_name_only(self):
        os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = SECRET
        self.addCleanup(os.environ.pop, "CLAUDE_CODE_OAUTH_TOKEN", None)
        cmd = executor.claude_command(session(), "x", container_name="c1")
        self.assertIn("CLAUDE_CODE_OAUTH_TOKEN", cmd)
        self.assertNotIn(SECRET, " ".join(cmd))
        self.assertEqual(cmd[cmd.index("CLAUDE_CODE_OAUTH_TOKEN") - 1], "-e")

    def test_nothing_from_the_host_is_mounted(self):
        cmd = executor.claude_command(session(), "x", container_name="c1")
        mounts = [cmd[i + 1] for i, a in enumerate(cmd) if a in ("-v", "--volume", "--mount")]
        self.assertTrue(mounts)
        for m in mounts:
            self.assertFalse(m.split(":")[0].startswith(("/", ".", "~")), m)

    def test_resume_and_plugin_dirs_are_passed(self):
        cmd = executor.claude_command(session(plugin_dirs=["/cfg/arm/plugins/linked-intent-dev"]), "Approved.",
                                      resume="abc", container_name="c1")
        self.assertEqual(cmd[cmd.index("--resume") + 1], "abc")
        self.assertEqual(cmd[cmd.index("--plugin-dir") + 1], "/cfg/arm/plugins/linked-intent-dev")

    def test_a_turn_can_run_in_plan_mode(self):
        cmd = executor.claude_command(session(), "Plan it.", container_name="c1", permission_mode="plan")
        self.assertEqual(cmd[cmd.index("--permission-mode") + 1], "plan")

    def test_only_plan_and_bypass_modes_are_allowed(self):
        with self.assertRaises(ValueError):
            executor.claude_command(session(), "x", container_name="c1", permission_mode="acceptEdits")

    def test_a_volume_name_that_looks_like_a_path_is_refused(self):
        with self.assertRaises(ValueError):
            executor.claude_command(session(workspace_volume="/Users/someone/work"), "x", container_name="c1")


class CheckInitTest(unittest.TestCase):
    def test_accepts_exactly_the_expected_plugins(self):
        executor.check_init(session(), init_record(["cc-plugin-agents-md", "cc-plugin-telemetry"], ["debug", "simplify"]))

    def test_an_extra_plugin_makes_the_session_invalid(self):
        rec = init_record(["cc-plugin-agents-md", "cc-plugin-telemetry", "linked-intent-dev"])
        with self.assertRaisesRegex(InitProblem, "linked-intent-dev"):
            executor.check_init(session(), rec)

    def test_a_missing_plugin_makes_the_session_invalid(self):
        s = session(expected_plugins={"cc-plugin-agents-md", "cc-plugin-telemetry", "linked-intent-dev"})
        with self.assertRaisesRegex(InitProblem, "linked-intent-dev"):
            executor.check_init(s, init_record(["cc-plugin-agents-md", "cc-plugin-telemetry"]))

    def test_a_skill_from_a_plugin_outside_the_arm_makes_it_invalid(self):
        rec = init_record(["cc-plugin-agents-md", "cc-plugin-telemetry"], ["arrow-maintenance:arrow-maintenance"])
        with self.assertRaisesRegex(InitProblem, "arrow-maintenance"):
            executor.check_init(session(), rec)

    def test_wrong_model_or_version_or_memory_on_makes_it_invalid(self):
        plugins = ["cc-plugin-agents-md", "cc-plugin-telemetry"]
        for rec in (init_record(plugins, model="claude-opus-5-5"),
                    init_record(plugins, version="2.1.400"),
                    init_record(plugins, memory={"auto": "/cfg/projects/x/memory/"})):
            with self.assertRaises(InitProblem):
                executor.check_init(session(), rec)


class RunTurnTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.dir))

    def fake_runner(self, lines, returncode=0, timeout=False):
        calls = []

        def run(cmd, stdout=None, stderr=None, timeout=None, **kw):
            calls.append(cmd)
            if cmd[:2] == ["docker", "kill"]:
                return subprocess.CompletedProcess(cmd, 0)
            if timeout_flag["on"]:
                stdout.write(("\n".join(lines[:1]) + "\n").encode())
                raise subprocess.TimeoutExpired(cmd, timeout)
            stdout.write(("\n".join(lines) + "\n").encode())
            return subprocess.CompletedProcess(cmd, returncode)
        timeout_flag = {"on": timeout}
        return run, calls

    def test_records_the_stream_and_reads_its_init_and_result(self):
        result = {"type": "result", "subtype": "success", "is_error": False, "session_id": "s1",
                  "total_cost_usd": 0.5, "modelUsage": {"claude-sonnet-5-5": {"inputTokens": 1, "outputTokens": 2,
                  "cacheReadInputTokens": 3, "cacheCreationInputTokens": 4,
                  "cacheCreationEphemeral5mInputTokens": 0, "cacheCreationEphemeral1hInputTokens": 4, "costUSD": 0.5}},
                  "result": "Done."}
        run, calls = self.fake_runner([json.dumps(init_record(["cc-plugin-agents-md", "cc-plugin-telemetry"])),
                                       json.dumps(result)])
        out = self.dir / "turn.jsonl"
        t = executor.run_turn(session(), "Build it.", out, runner=run)
        self.assertTrue(out.exists())
        self.assertEqual(t.session_id, "s1")
        self.assertEqual(t.final_text, "Done.")
        self.assertFalse(t.timed_out)
        self.assertIsNone(t.init_problem)
        self.assertEqual(t.summary.usage.total().cache_write_1h, 4)

    def test_an_unexpected_plugin_is_reported_not_hidden(self):
        run, _ = self.fake_runner([json.dumps(init_record(["cc-plugin-agents-md", "cc-plugin-telemetry", "x"]))])
        t = executor.run_turn(session(), "Build it.", self.dir / "t.jsonl", runner=run)
        self.assertIn("x", t.init_problem)

    def test_a_timeout_kills_the_container_and_keeps_what_was_written(self):
        run, calls = self.fake_runner([json.dumps(init_record(["cc-plugin-agents-md", "cc-plugin-telemetry"]))],
                                      timeout=True)
        out = self.dir / "t.jsonl"
        t = executor.run_turn(session(), "Build it.", out, runner=run)
        self.assertTrue(t.timed_out)
        self.assertIn(["docker", "kill", t.container_name], calls)
        self.assertIsNone(t.summary.usage)
        self.assertEqual(t.session_id, "s1")


if __name__ == "__main__":
    unittest.main()
