"""Tests for LID's spend by phase (analysis_phase_spend.py): the files a call writes, phase announcements in working
calls and stop messages, the attribution rule, prices fitted from cost records, and tokens joined from transcripts.

Run from the harness folder: python3.12 -m unittest discover -s tests
"""

import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import analysis_phase_spend as ps  # noqa: E402

PRICES_PER_M = {"input": 2.0, "output": 10.0, "cache_read": 0.1, "cache_write_5m": 2.5, "cache_write_1h": 4.0}


def text(t):
    return {"type": "text", "text": t}


_ids = iter(range(10_000))


def tool(name, **inp):
    return {"type": "tool_use", "id": f"toolu_{next(_ids)}", "name": name, "input": inp}


def bash(command):
    return tool("Bash", command=command)


class Writes(unittest.TestCase):
    def test_path_phase(self):
        self.assertEqual(ps.path_phase("/work/docs/high-level-design.md"), 1)
        self.assertEqual(ps.path_phase("docs/intent/catalog/catalog-design.md"), 2)
        self.assertEqual(ps.path_phase("docs/intent/catalog/decisions/why.md"), 2)
        self.assertEqual(ps.path_phase("docs/intent/*/*-specs.md"), 3)
        self.assertEqual(ps.path_phase("/work/tests/helpers.py"), 5)
        self.assertEqual(ps.path_phase("test_x.py"), 5)
        self.assertEqual(ps.path_phase("releasedesk/app.py"), 6)
        self.assertIsNone(ps.path_phase("README.md"))
        self.assertIsNone(ps.path_phase("AGENTS.md"))
        self.assertIsNone(ps.path_phase("docs/arrows/index.yaml"))

    def test_inline_python_that_writes(self):
        cmd = "python3 - <<'EOF'\np='docs/high-level-design.md'\ns=open(p).read()\nopen(p,'w').write(s)\nEOF"
        self.assertEqual(ps.bash_writes(cmd), ["docs/high-level-design.md"])

    def test_inline_python_that_only_reads_is_no_write(self):
        cmd = "python3 - <<'EOF'\nprint(open('docs/high-level-design.md').read())\nEOF"
        self.assertEqual(ps.bash_writes(cmd), [])

    def test_cd_resolves_relative_targets(self):
        cmd = "cd /work/tests && cat > helpers.py <<'EOF'\nimport os\nx = 1 > 0\nEOF"
        self.assertEqual(ps.bash_writes(cmd), ["/work/tests/helpers.py"])
        cmd = "cd /work/docs/intent/a && python3 - <<'EOF'\np='a-specs.md'\nopen(p,'w').write('x')\nEOF"
        self.assertEqual(ps.bash_writes(cmd), ["/work/docs/intent/a/a-specs.md"])

    def test_shell_writes(self):
        self.assertEqual(ps.bash_writes("sed -i 's/a/b/' docs/intent/*/*-specs.md"), ["docs/intent/*/*-specs.md"])
        self.assertEqual(ps.bash_writes("sed -i -e 's/a/b/' -e 's/c/d/' x/app.py"), ["x/app.py"])
        self.assertEqual(ps.bash_writes("echo hi | tee -a README.md"), ["README.md"])
        self.assertEqual(ps.bash_writes("cp /tmp/x.py releasedesk/x.py"), ["releasedesk/x.py"])
        self.assertEqual(ps.bash_writes("cat >> tests/test_a.py <<'EOF'\ndef test(): pass\nEOF\npytest -q"),
                         ["tests/test_a.py"])

    def test_no_writes(self):
        self.assertEqual(ps.bash_writes(".venv/bin/python -m pytest -q 2>&1 | tail -3"), [])
        self.assertEqual(ps.bash_writes("grep -n x a.py > /tmp/out.txt; cat a.py >/dev/null"), [])
        self.assertEqual(ps.bash_writes("cat docs/high-level-design.md"), [])

    def test_call_writes_reads_write_and_edit_tools(self):
        blocks = [tool("Write", file_path="/work/tests/test_a.py", content="x"),
                  tool("Edit", file_path="/work/docs/intent/a/a-design.md", old_string="a", new_string="b"),
                  tool("Read", file_path="/work/releasedesk/app.py")]
        self.assertEqual(ps.call_writes(blocks), ["/work/tests/test_a.py", "/work/docs/intent/a/a-design.md"])


class Announcements(unittest.TestCase):
    def test_working_call(self):
        self.assertEqual(ps.announcement("Phase 3: writing the EARS specs."), 3)
        self.assertEqual(ps.announcement("Starting Phase 2. I'll read the LLDs."), 2)
        self.assertEqual(ps.announcement("Phase 1 is done. The HLD has a new section. Now Phase 2: the LLDs."), 2)
        self.assertEqual(ps.announcement("Phase 6: I'll implement it, then bring the LLD in line with the Phase 4 edits"), 6)
        self.assertIsNone(ps.announcement("All tests pass. I'll add the migration test I deferred in Phase 5."))
        self.assertIsNone(ps.announcement("Phases 1 to 3 are about intent."))
        self.assertIsNone(ps.announcement("No phase words here."))

    def test_stop_message(self):
        self.assertEqual(ps.stop_announcement("I haven't edited anything. This is the Phase 1 stop: questions."), 1)
        self.assertEqual(ps.stop_announcement("**Phase 1 (HLD) is done and needs your review.**"), 1)
        self.assertEqual(ps.stop_announcement("Intro.\n\n**Phase 4 (edge audit):** I found one fork."), 4)
        self.assertEqual(ps.stop_announcement("Here are the Phase 4 audit results."), 4)
        self.assertEqual(ps.stop_announcement("I'm in Phase 1 of the LID workflow, the HLD check."), 1)
        self.assertEqual(ps.stop_announcement("Phases 1 and 2 are drafted; review the docs."), 2)
        self.assertEqual(ps.stop_announcement("This is the Phase 2 and 3 stop."), 3)
        self.assertEqual(ps.stop_announcement("I've drafted the Phase 3 specs. Next is Phase 4."), 3)
        self.assertEqual(ps.stop_announcement("The HLD is written. If it reads right, I'll move to Phase 2."), 1)
        self.assertEqual(ps.stop_announcement("Do you approve these specs? If so, I'll run the Phase 4 edge audit."), 3)
        self.assertIsNone(ps.stop_announcement("All tests pass. The ordering matches the Phase 4 edits."))
        self.assertIsNone(ps.stop_announcement("It is a design choice (Phase 2), so here are options."))
        self.assertIsNone(ps.stop_announcement("Committed as abc123."))


def change(*turns):
    """Calls for one change: each turn is a list of (text, blocks); the last of each turn is its stop."""
    out = []
    for k, turn in enumerate(turns):
        out.append([ps.Call(f"m{k}-{i}", ([text(t)] if t else []) + list(blocks), k) for i, (t, blocks) in enumerate(turn)])
    return out


class Attribution(unittest.TestCase):
    def test_a_full_change(self):
        turns = change(
            [("", [tool("Skill", skill="lid")]), ("", [bash("cat docs/high-level-design.md")]),
             ("This is the Phase 1 stop: the HLD change I propose.", [])],
            [("Understood.", [tool("Edit", file_path="/work/docs/high-level-design.md")]),
             ("Starting Phase 2.", [tool("Edit", file_path="/work/docs/intent/a/a-design.md")]),
             ("If this reads right, I'll move to Phase 3.", [])],
            [("", [bash("grep -n X docs/intent/a/a-specs.md")]),
             ("", [tool("Edit", file_path="/work/docs/intent/a/a-specs.md")]), ("Phase 3 is drafted.", [])],
            [("", [tool("Edit", file_path="/work/docs/intent/a/a-specs.md")]),
             ("Phase 4 is done. I narrowed one spec.", [])],
            [("Phase 5: tests first.", [tool("Write", file_path="/work/tests/test_a.py")]),
             ("", [tool("Write", file_path="/work/pkg/__init__.py")]),
             ("", [tool("Write", file_path="/work/tests/test_b.py")]),
             ("Phase 5 is done. The tests fail as expected.", [])],
            [("Phase 6: code.", [tool("Edit", file_path="/work/pkg/a.py")]),
             ("", [tool("Edit", file_path="/work/tests/test_a.py")]),
             ("", [bash("sed -i 's/- \\[ \\]/- [x]/' docs/intent/a/a-specs.md")]),
             ("Done. All tests pass.", [])],
        )
        ps.classify_calls(turns)
        got = [[c.phase for c in t] for t in turns]
        self.assertEqual(got, [
            ["hld", "hld", "stops"],             # read-only turn: its stop names Phase 1
            ["hld", "lld", "stops"],             # the HLD edit before the announcement moves nothing back
            ["ears", "ears", "stops"],           # no announcement: the stop says Phase 3
            ["edge_audit", "stops"],             # spec edits in a turn that closes Phase 4
            ["tests", "tests", "tests", "stops"],  # a stub module doesn't push past the Phase 5 the stop closes
            ["code", "code", "code", "stops"],   # Phase 6 fixing a test and ticking a spec stays code
        ])
        # the second stop looks ahead to Phase 3, so it closes Phase 2
        self.assertEqual([t[-1].stop_phase for t in turns], ["hld", "lld", "ears", "edge_audit", "tests", "code"])
        # as written: the writing calls take what they write
        self.assertEqual(turns[5][1].phase_written, {"tests": 1.0})
        self.assertEqual(turns[5][2].phase_written, {"ears": 1.0})
        self.assertEqual(turns[1][0].phase_written, {"hld": 1.0})

    def test_reads_take_the_phase_of_the_first_evidence_in_their_turn(self):
        turns = change(
            [("", [bash("cat a")]), ("", [bash("cat b")]), ("Phase 2 starts now.", [bash("cat c")]),
             ("Here is the draft.", [])])
        ps.classify_calls(turns)
        self.assertEqual([c.phase for c in turns[0]], ["lld", "lld", "lld", "stops"])

    def test_writes_move_forward_without_a_closing_stop(self):
        turns = change(
            [("Phase 5: tests.", [tool("Write", file_path="/work/tests/test_a.py")]),
             ("", [tool("Edit", file_path="/work/pkg/a.py")]), ("", [tool("Edit", file_path="/work/tests/test_a.py")]),
             ("All green.", [])])
        ps.classify_calls(turns)
        self.assertEqual([c.phase for c in turns[0]], ["tests", "code", "code", "stops"])

    def test_no_evidence_is_no_phase(self):
        turns = change([("", [bash("cat README.md")]), ("", [tool("Edit", file_path="/work/README.md")]),
                        ("I updated the README.", [])])
        ps.classify_calls(turns)
        self.assertEqual([c.phase for c in turns[0]], ["no_phase", "no_phase", "stops"])
        self.assertEqual(turns[0][-1].stop_phase, "no_phase")

    def test_a_turn_without_evidence_keeps_the_phase_before_it(self):
        turns = change([("Phase 6: code.", [tool("Edit", file_path="/work/pkg/a.py")]), ("Done?", [])],
                       [("", [bash("pytest -q")]), ("Committed.", [])])
        ps.classify_calls(turns)
        self.assertEqual(turns[1][0].phase, "code")


def model_usage(t):
    cost = sum(t[c] * PRICES_PER_M[c] / 1e6 for c in ps.CLASSES)
    return {"m": {"inputTokens": t["input"], "outputTokens": t["output"], "cacheReadInputTokens": t["cache_read"],
                  "cacheCreationInputTokens": t["cache_write_5m"] + t["cache_write_1h"],
                  "cacheCreationEphemeral5mInputTokens": t["cache_write_5m"],
                  "cacheCreationEphemeral1hInputTokens": t["cache_write_1h"], "costUSD": cost}}, cost


class Prices(unittest.TestCase):
    def records(self, n, five_minute=True):
        rng = random.Random(7)
        recs = []
        for _ in range(n):
            t = {"input": rng.randint(5, 80), "output": rng.randint(1_000, 90_000), "cache_read": rng.randint(10_000, 2_000_000),
                 "cache_write_5m": rng.randint(0, 30_000) if five_minute else 0, "cache_write_1h": rng.randint(5_000, 120_000)}
            mu, cost = model_usage(t)
            recs.append({"modelUsage": mu, "total_cost_usd": cost})
        return recs

    def test_fit_recovers_prices(self):
        prices = ps.fit_prices(self.records(40))
        for c in ps.CLASSES:
            self.assertAlmostEqual(prices[c] * 1e6, PRICES_PER_M[c], places=6)

    def test_unused_class_prices_at_zero(self):
        self.assertEqual(ps.fit_prices(self.records(20, five_minute=False))["cache_write_5m"], 0.0)

    def test_too_few_records_refuse(self):
        with self.assertRaises(ValueError):
            ps.fit_prices(self.records(3))

    def test_nonlinear_costs_refuse(self):
        recs = self.records(30)
        recs[4]["modelUsage"]["m"]["costUSD"] += 0.5
        with self.assertRaises(ValueError):
            ps.fit_prices(recs)


def usage(inp=0, out=0, read=0, w1=0):
    return {"input_tokens": inp, "output_tokens": out, "cache_read_input_tokens": read,
            "cache_creation_input_tokens": w1, "cache_creation": {"ephemeral_5m_input_tokens": 0,
                                                                  "ephemeral_1h_input_tokens": w1}}


def tokens(inp=0, out=0, read=0, w1=0):
    return {"input": inp, "output": out, "cache_read": read, "cache_write_5m": 0, "cache_write_1h": w1}


def assistant(mid, blocks, u, parent=None):
    return {"type": "assistant", "session_id": "s1", "parent_tool_use_id": parent,
            "message": {"id": mid, "role": "assistant", "content": blocks, "usage": u}}


def result(cum):
    mu, cost = model_usage(cum)
    return {"type": "result", "session_id": "s1", "modelUsage": mu, "total_cost_usd": cost, "is_error": False}


def add(*ts):
    return {c: sum(t[c] for t in ts) for c in ps.CLASSES}


class EndToEnd(unittest.TestCase):
    """One change of two turns: a Phase 1 turn that launches a subagent, and a Phase 2 turn."""

    def build(self, tmp, result_extra=None):
        agent = tool("Agent", description="probe", prompt="read the docs")
        final = {"m1": tokens(2, 40, 1000, 500), "m2": tokens(1, 300, 1500, 200), "m3": tokens(1, 500, 1700, 100),
                 "m4": tokens(1, 80, 2000, 50), "m5": tokens(1, 120, 2100, 60)}
        sub = tokens(3, 900, 4000, 700)
        t0 = [assistant("m1", [text("I'll start with Phase 1."), agent], usage(2, 1, 1000, 500)),
              assistant("m2", [bash("cat docs/high-level-design.md")], usage(1, 2, 1500, 200)),
              assistant("m3", [text("This is the Phase 1 stop.")], usage(1, 3, 1700, 100))]
        t1 = [assistant("m4", [tool("Edit", file_path="/work/docs/intent/a/a-design.md")], usage(1, 1, 2000, 50)),
              assistant("m5", [text("Phase 2 is drafted.")], usage(1, 1, 2100, 60))]
        cum0 = add(final["m1"], final["m2"], final["m3"], sub)
        cum1 = add(cum0, final["m4"], final["m5"], result_extra or tokens())
        run = Path(tmp) / "g-lid-full-1"
        cdir = run / "change-00"
        cdir.mkdir(parents=True)
        (run / "trajectory.json").write_text(json.dumps({"id": "g-lid-full-1", "arm": "lid-full", "seed": "s",
                                                          "volumes": {"config": "cfg"}}))
        (cdir / "turn-00.stream.jsonl").write_text("\n".join(json.dumps(r) for r in t0 + [result(cum0)]) + "\n")
        (cdir / "turn-01.stream.jsonl").write_text("\n".join(json.dumps(r) for r in t1 + [result(cum1)]) + "\n")
        main = "\n".join(json.dumps(assistant(m, [], usage(t["input"], t["output"], t["cache_read"], t["cache_write_1h"])))
                         for m, t in final.items())
        subfile = json.dumps(assistant("sub1", [], usage(sub["input"], sub["output"], sub["cache_read"], sub["cache_write_1h"])))
        files = {"./-work/s1.jsonl": main.encode(), "./-work/s1/subagents/agent-x.jsonl": subfile.encode(),
                 "./-work/s1/subagents/agent-x.meta.json": json.dumps({"toolUseId": agent["id"]}).encode()}
        return run, ps.transcripts_from_files(files), final, sub

    def test_tokens_join_and_reconcile(self):
        with tempfile.TemporaryDirectory() as tmp:
            run, tr, final, sub = self.build(tmp)
            r = ps.run_spend(run, tr, {c: v / 1e6 for c, v in PRICES_PER_M.items()})
        rec = r["reconciliation"][0]
        self.assertEqual(rec["found_tokens"], rec["recorded_tokens"])
        self.assertEqual(rec["residual"], {})
        self.assertEqual(rec["fallback_calls"], 0)
        p = r["changes"]["0"]["primary"]
        hld = ps.total_tokens(final["m1"]) + ps.total_tokens(final["m2"]) + ps.total_tokens(sub)
        self.assertEqual(p["hld"]["tokens"], hld)  # the subagent counts in the phase of the call that launched it
        self.assertEqual(p["lld"]["tokens"], ps.total_tokens(final["m4"]))
        self.assertEqual(p["stops"]["tokens"], ps.total_tokens(final["m3"]) + ps.total_tokens(final["m5"]))
        for c in ps.CLASSES:
            self.assertAlmostEqual(r["prices_per_mtok"][c], PRICES_PER_M[c], places=4)
        self.assertAlmostEqual(rec["priced_cost"], rec["recorded_cost"], places=9)

    def test_tokens_missing_from_transcripts_are_unattributed(self):
        with tempfile.TemporaryDirectory() as tmp:
            run, tr, _, _ = self.build(tmp, result_extra=tokens(0, 0, 5000, 0))
            r = ps.run_spend(run, tr, {c: v / 1e6 for c, v in PRICES_PER_M.items()})
        self.assertEqual(r["reconciliation"][0]["residual"], {"cache_read": 5000})
        self.assertEqual(r["changes"]["0"]["primary"]["unattributed"]["tokens"], 5000)

    def test_without_transcripts_output_is_spread_by_length(self):
        with tempfile.TemporaryDirectory() as tmp:
            run, _, final, sub = self.build(tmp)
            r = ps.run_spend(run, None, {c: v / 1e6 for c, v in PRICES_PER_M.items()})
        rec = r["reconciliation"][0]
        self.assertEqual(rec["fallback_calls"], 5)
        # input-side tokens are exact in the stream; output is filled up to the recorded total
        self.assertEqual(rec["residual"].get("output", 0), 0)
        self.assertEqual(rec["residual"].get("cache_read", 0), sub["cache_read"])  # the subagent is unseen


if __name__ == "__main__":
    unittest.main()
