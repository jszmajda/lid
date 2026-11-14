"""Tests for costeval.usage: reading token usage from Claude Code sessions.

Run from the harness folder: python3.12 -m unittest discover -s tests
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from costeval import usage  # noqa: E402
from costeval.usage import NotCumulative, TokenCounts  # noqa: E402


def model_usage(inp, out, read, write_5m, write_1h, cost):
    """One model's entry in a result record's modelUsage, in Claude Code's field names."""
    return {
        "inputTokens": inp,
        "outputTokens": out,
        "cacheReadInputTokens": read,
        "cacheCreationInputTokens": write_5m + write_1h,
        "cacheCreationEphemeral5mInputTokens": write_5m,
        "cacheCreationEphemeral1hInputTokens": write_1h,
        "costUSD": cost,
        "contextWindow": 1000000,
    }


def result_record(models, session_id="s1", is_error=False):
    return {
        "type": "result",
        "subtype": "success",
        "is_error": is_error,
        "session_id": session_id,
        "total_cost_usd": sum(m["costUSD"] for m in models.values()),
        # The top-level usage field covers only the main thread; it must not be used.
        "usage": {"input_tokens": 1, "output_tokens": 1, "cache_read_input_tokens": 1, "cache_creation_input_tokens": 1},
        "modelUsage": models,
    }


def assistant_line(msg_id, model, inp, out, read, write_5m, write_1h):
    return json.dumps({
        "type": "assistant",
        "message": {
            "id": msg_id,
            "model": model,
            "usage": {
                "input_tokens": inp,
                "output_tokens": out,
                "cache_read_input_tokens": read,
                "cache_creation_input_tokens": write_5m + write_1h,
                "cache_creation": {"ephemeral_5m_input_tokens": write_5m, "ephemeral_1h_input_tokens": write_1h},
            },
        },
    })


class TokenCountsTest(unittest.TestCase):
    def test_add_and_subtract_every_class(self):
        a = TokenCounts(input=1, output=2, cache_read=3, cache_write_5m=4, cache_write_1h=5)
        b = TokenCounts(input=10, output=20, cache_read=30, cache_write_5m=40, cache_write_1h=50)
        self.assertEqual(a + b, TokenCounts(11, 22, 33, 44, 55))
        self.assertEqual(b - a, TokenCounts(9, 18, 27, 36, 45))

    def test_cache_write_is_the_sum_of_both_lifetimes(self):
        self.assertEqual(TokenCounts(cache_write_5m=4, cache_write_1h=5).cache_write, 9)


class FromResultTest(unittest.TestCase):
    def test_reads_every_token_class_for_every_model(self):
        rec = result_record({
            "claude-sonnet-5-5": model_usage(10, 1000, 50000, 0, 20000, 0.20),
            "claude-haiku-5-5": model_usage(4, 300, 9000, 500, 0, 0.01),
        })
        u = usage.from_result(rec)
        self.assertEqual(u.models["claude-sonnet-5-5"], TokenCounts(10, 1000, 50000, 0, 20000))
        self.assertEqual(u.models["claude-haiku-5-5"], TokenCounts(4, 300, 9000, 500, 0))
        self.assertAlmostEqual(u.reported_cost_usd, 0.21)

    def test_ignores_the_main_thread_only_usage_field(self):
        rec = result_record({"claude-sonnet-5-5": model_usage(10, 1000, 50000, 0, 20000, 0.20)})
        self.assertEqual(usage.from_result(rec).total(), TokenCounts(10, 1000, 50000, 0, 20000))

    def test_a_split_missing_from_an_older_record_counts_as_five_minute_writes(self):
        entry = model_usage(1, 2, 3, 0, 0, 0.0)
        entry["cacheCreationInputTokens"] = 700
        del entry["cacheCreationEphemeral5mInputTokens"]
        del entry["cacheCreationEphemeral1hInputTokens"]
        u = usage.from_result(result_record({"m": entry}))
        self.assertEqual(u.models["m"].cache_write_5m, 700)
        self.assertEqual(u.models["m"].cache_write_1h, 0)


class TurnDeltaTest(unittest.TestCase):
    def test_first_turn_is_the_whole_result(self):
        cur = usage.from_result(result_record({"m": model_usage(10, 100, 1000, 0, 500, 0.10)}))
        self.assertEqual(usage.turn_delta(None, cur), cur)

    def test_resumed_turn_is_the_difference_from_the_previous_result(self):
        # Values from the plumbing test: a resumed session's totals are cumulative.
        prev = usage.from_result(result_record({"claude-sonnet-5-5": model_usage(12, 4164, 221189, 0, 23784, 0.1589189)}))
        cur = usage.from_result(result_record({"claude-sonnet-5-5": model_usage(16, 8002, 323668, 0, 32327, 0.2417268)}))
        d = usage.turn_delta(prev, cur)
        self.assertEqual(d.models["claude-sonnet-5-5"], TokenCounts(4, 3838, 102479, 0, 8543))
        self.assertAlmostEqual(d.reported_cost_usd, 0.0828079)

    def test_a_model_that_first_appears_in_this_turn_counts_whole(self):
        prev = usage.from_result(result_record({"a": model_usage(1, 1, 1, 0, 1, 0.01)}))
        cur = usage.from_result(result_record({"a": model_usage(2, 2, 2, 0, 2, 0.02), "b": model_usage(5, 5, 5, 5, 0, 0.05)}))
        d = usage.turn_delta(prev, cur)
        self.assertEqual(d.models["a"], TokenCounts(1, 1, 1, 0, 1))
        self.assertEqual(d.models["b"], TokenCounts(5, 5, 5, 5, 0))

    def test_a_counter_that_goes_down_is_refused(self):
        prev = usage.from_result(result_record({"a": model_usage(5, 5, 5, 0, 5, 0.05)}))
        cur = usage.from_result(result_record({"a": model_usage(6, 4, 6, 0, 6, 0.06)}))
        with self.assertRaises(NotCumulative):
            usage.turn_delta(prev, cur)

    def test_a_model_missing_from_the_later_result_is_refused(self):
        prev = usage.from_result(result_record({"a": model_usage(5, 5, 5, 0, 5, 0.05)}))
        cur = usage.from_result(result_record({"b": model_usage(6, 6, 6, 0, 6, 0.06)}))
        with self.assertRaises(NotCumulative):
            usage.turn_delta(prev, cur)


class FromStreamTest(unittest.TestCase):
    def write(self, lines):
        f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        f.write("\n".join(lines) + "\n")
        f.close()
        self.addCleanup(Path(f.name).unlink)
        return Path(f.name)

    def test_takes_the_last_result_and_skips_lines_that_are_not_json(self):
        path = self.write([
            "Warning: no stdin data received in 3s, proceeding without it.",
            json.dumps({"type": "system", "subtype": "init", "session_id": "s9"}),
            json.dumps(result_record({"m": model_usage(1, 1, 1, 0, 1, 0.01)}, session_id="s9")),
            json.dumps(result_record({"m": model_usage(2, 2, 2, 0, 2, 0.02)}, session_id="s9")),
        ])
        s = usage.from_stream(path)
        self.assertEqual(s.session_id, "s9")
        self.assertEqual(s.usage.models["m"], TokenCounts(2, 2, 2, 0, 2))
        self.assertFalse(s.is_error)

    def test_a_run_without_a_result_record_reports_no_usage(self):
        path = self.write([json.dumps({"type": "system", "subtype": "init", "session_id": "s3"})])
        s = usage.from_stream(path)
        self.assertEqual(s.session_id, "s3")
        self.assertIsNone(s.usage)


class FromTranscriptsTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.dir))

    def test_sums_main_and_subagent_transcripts_counting_each_message_once(self):
        main = self.dir / "s1.jsonl"
        sub = self.dir / "s1" / "subagents"
        sub.mkdir(parents=True)
        main.write_text("\n".join([
            json.dumps({"type": "user", "message": {"content": "hi"}}),
            assistant_line("m1", "claude-sonnet-5-5", 2, 100, 1000, 0, 500),
            assistant_line("m1", "claude-sonnet-5-5", 2, 100, 1000, 0, 500),  # same message written twice
            assistant_line("m2", "claude-sonnet-5-5", 2, 156, 29064, 0, 5184),
            "not json",
        ]) + "\n")
        (sub / "agent-a.jsonl").write_text(assistant_line("m3", "claude-haiku-5-5", 6, 767, 25041, 13745, 0) + "\n")
        u = usage.from_transcripts(main)
        self.assertEqual(u.models["claude-sonnet-5-5"], TokenCounts(4, 256, 30064, 0, 5684))
        self.assertEqual(u.models["claude-haiku-5-5"], TokenCounts(6, 767, 25041, 13745, 0))
        self.assertIsNone(u.reported_cost_usd)

    def test_transcripts_reconcile_with_the_result_record(self):
        main = self.dir / "s1.jsonl"
        (self.dir / "s1" / "subagents").mkdir(parents=True)
        main.write_text(assistant_line("m1", "m", 4, 256, 30064, 0, 5684) + "\n")
        (self.dir / "s1" / "subagents" / "agent-x.jsonl").write_text(assistant_line("m2", "m", 6, 767, 25041, 13745, 0) + "\n")
        from_disk = usage.from_transcripts(main)
        from_result = usage.from_result(result_record({"m": model_usage(10, 1023, 55105, 13745, 5684, 0.07)}))
        self.assertEqual(from_disk.total(), from_result.total())


if __name__ == "__main__":
    unittest.main()
