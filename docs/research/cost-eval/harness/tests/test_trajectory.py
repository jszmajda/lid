"""Tests for costeval.trajectory: arms, first prompts, the change loop, and what counts as code."""

import contextlib
import io
import json
import sys
from dataclasses import asdict
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from costeval import executor, simulator as sm, trajectory as tj, usage  # noqa: E402
from test_simulator import BRIEF, CHANGES, ORACLE, OWNER_ITEMS, ans, out  # noqa: E402

import audit_owner as ao  # noqa: E402
import run_probe as rp  # noqa: E402
import run_trajectory as rt  # noqa: E402


class ArmTest(unittest.TestCase):
    def test_the_pilot_arms_load(self):
        bare, cheap, lid = (tj.load_arm(n) for n in ("bare", "cheap-discipline", "lid-full"))
        self.assertEqual((bare.plugins, bare.first_turn_mode, bare.workspace_files), ((), "bypassPermissions", {}))
        self.assertEqual(cheap.first_turn_mode, "plan")
        self.assertIn("AGENTS.md", cheap.workspace_files)
        self.assertTrue((tj.ARMS_DIR / cheap.workspace_files["AGENTS.md"]).is_file())
        self.assertEqual(lid.plugin_dirs, ("/cfg/lid/plugins/linked-intent-dev",))
        self.assertRegex(lid.lid_release, r"^v\d+\.\d+\.\d+$")

    def test_first_prompts_carry_the_request_and_the_neutral_sentence(self):
        lid, bare = tj.load_arm("lid-full"), tj.load_arm("bare")
        c0, c1 = sm.first_build(BRIEF), sm.parse_change_script(CHANGES)[1]
        self.assertEqual(tj.change_prompt(lid, c0, BRIEF), f"/linked-intent-dev {BRIEF}\n\n{tj.NEUTRAL_SENTENCE}")
        self.assertEqual(tj.change_prompt(lid, c1, "Add notes."), f"Add notes.\n\n{tj.NEUTRAL_SENTENCE}")
        self.assertEqual(tj.change_prompt(bare, c0, BRIEF), f"{BRIEF}\n\n{tj.NEUTRAL_SENTENCE}")
        probe = sm.parse_probe(CHANGES, 0)
        self.assertFalse(tj.change_prompt(lid, probe, "List orders.").startswith("/"))


class PlanTest(unittest.TestCase):
    def test_the_plan_is_the_last_plan_file_written_unless_a_plan_tool_was_used(self):
        tmp = Path(tempfile.mkdtemp())
        def stream(*blocks):
            path = tmp / f"s{len(list(tmp.iterdir()))}.jsonl"
            path.write_text("\n".join(json.dumps({"type": "assistant", "message": {"content": [b]}}) for b in blocks))
            return path
        w = lambda c, f="/cfg/plans/p.md": {"type": "tool_use", "name": "Write", "input": {"file_path": f, "content": c}}
        self.assertEqual(tj.plan_from_stream(stream(w("v1"), w("v2"), w("code", "/work/a.py"))), "v2")
        self.assertEqual(tj.plan_from_stream(stream(w("v1"), {"type": "tool_use", "name": "ExitPlanMode", "input": {"plan": "P"}})), "P")
        self.assertIsNone(tj.plan_from_stream(stream(w("code", "/work/a.py"))))


class CodePathTest(unittest.TestCase):
    def test_source_files_count_and_docs_and_tests_dont(self):
        for p in ("app/main.py", "benchtime/db.py", "static/app.js", "pyproject.toml"):
            self.assertTrue(tj.is_code_path(p), p)
        for p in ("README.md", "docs/intent/hld.md", "tests/test_booking.py", "app/test_main.py", "conftest.py",
                  "test/helpers.py", "NOTES.md", "data/lab.csv"):
            self.assertFalse(tj.is_code_path(p), p)


def write_stream(path, *, session="s1", text="Done.", plan=None, cost=0.5, is_error=False, out_tokens=100):
    recs = [{"type": "system", "subtype": "init", "session_id": session}]
    if plan:
        recs.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "ExitPlanMode", "input": {"plan": plan}}]}})
    recs.append({"type": "result", "session_id": session, "is_error": is_error, "result": text, "total_cost_usd": cost,
                 "modelUsage": {"claude-sonnet-5-5": {"inputTokens": 10, "outputTokens": out_tokens, "cacheReadInputTokens": 0,
                                                      "cacheCreationInputTokens": 0}}})
    path.write_text("\n".join(json.dumps(r) for r in recs))


class FakeTurns:
    """Plays the agent: each scripted turn is (final text, plan or None, paths it changes)."""

    def __init__(self, ws, *script, fail_at=None):
        self.ws, self.script, self.calls, self.fail_at = ws, list(script), [], fail_at

    def __call__(self, prompt, stream_path, *, resume=None, permission_mode="bypassPermissions"):
        k = len(self.calls)
        self.calls.append({"prompt": prompt, "resume": resume, "mode": permission_mode})
        text, plan, changes = self.script[k]
        self.ws.changed |= set(changes)
        write_stream(stream_path, text=text, plan=plan, cost=0.1 * (k + 1), out_tokens=100 * (k + 1),
                     is_error=(k == self.fail_at))
        s = usage.from_stream(stream_path)
        return executor.TurnRecord(stream_path=stream_path, container_name="c", exit_code=0, timed_out=False, duration_s=1.0,
                                   session_id="s1", init={}, init_problem=None, summary=s, final_text=text)


class FakeWorkspace:
    def __init__(self, files=None):
        self.changed, self.files, self.commits = set(), dict(files or {}), []

    def head(self):
        return "base"

    def commit_all(self, message):
        self.commits.append(message)
        return "c1"

    def changed_paths(self, base):
        return sorted(self.changed)

    def prose_paths(self):
        return [p for p in self.files if p.endswith(".md")]

    def read(self, paths):
        return {p: self.files[p] for p in paths}


class Ask:
    def __init__(self, *outputs):
        self.outputs, self.prompts = list(outputs), []

    def __call__(self, prompt):
        self.prompts.append(prompt)
        return self.outputs.pop(0)


def make_owner(*outputs, policy="diligent", replicate="t"):
    ask = Ask(*outputs)
    o = sm.parse_oracle(ORACLE)
    return sm.Owner(oracle=o, brief=BRIEF, policy=policy, replicate=replicate, ask=ask,
                    owner_items=sm.parse_owner_items(OWNER_ITEMS, o)), ask


class ChangeLoopTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.c = sm.parse_change_script(CHANGES)

    def test_a_change_ends_when_the_owner_accepts_and_is_committed(self):
        ws = FakeWorkspace()
        turns = FakeTurns(ws, ("Done.", None, ["app/notes.py"]))
        owner, _ = make_owner(out("completion"))
        r = tj.run_change(arm=tj.load_arm("bare"), change=self.c[1], owner=owner, turn=turns, workspace=ws, out_dir=self.tmp)
        self.assertEqual((r.rounds, r.finished, r.capped, r.error, r.commit), (1, True, False, None, "c1"))
        self.assertEqual(len(ws.commits), 1)
        self.assertTrue(turns.calls[0]["prompt"].endswith(tj.NEUTRAL_SENTENCE))
        self.assertIsNone(owner.change)
        saved = json.loads((self.tmp / "change.json").read_text())
        self.assertEqual(saved["turns"][0]["usage"]["reported_cost_usd"], 0.1)

    def test_plan_mode_opens_the_change_and_the_owner_reads_the_plan(self):
        ws = FakeWorkspace()
        turns = FakeTurns(ws, ("Here's my plan. OK?", "PLAN: notes are stored verbatim.", []), ("Done.", None, ["app/notes.py"]))
        owner, ask = make_owner(out("approval"), out("completion"))
        r = tj.run_change(arm=tj.load_arm("cheap-discipline"), change=self.c[1], owner=owner, turn=turns, workspace=ws, out_dir=self.tmp)
        self.assertEqual([c["mode"] for c in turns.calls], ["plan", "bypassPermissions"])
        self.assertEqual([c["resume"] for c in turns.calls], [None, "s1"])
        self.assertEqual(turns.calls[1]["prompt"], "That looks fine. Go ahead.")
        self.assertIn('<document name="The agent\'s plan">\n[P2] PLAN: notes are stored verbatim.', ask.prompts[0])
        self.assertTrue(r.finished)
        # usage per turn is the difference between consecutive cumulative results
        self.assertAlmostEqual(r.turns[1]["usage"]["reported_cost_usd"], 0.1)
        self.assertEqual(r.turns[1]["usage"]["models"]["claude-sonnet-5-5"]["output"], 100)

    def test_documents_the_message_names_are_shown(self):
        ws = FakeWorkspace({"docs/design.md": "Design text.", "README.md": "readme"})
        turns = FakeTurns(ws, ("Please review docs/design.md.", None, []), ("Done.", None, []))
        owner, ask = make_owner(out("approval"), out("completion"))
        tj.run_change(arm=tj.load_arm("lid-full"), change=self.c[1], owner=owner, turn=turns, workspace=ws, out_dir=self.tmp)
        self.assertIn('<document name="docs/design.md">\n[P2] Design text.', ask.prompts[0])
        self.assertNotIn("readme", ask.prompts[0])

    def test_a_late_redirect_waits_for_source_code(self):
        ws = FakeWorkspace()
        turns = FakeTurns(ws, ("I wrote tests first. OK?", None, ["tests/test_move.py"]), ("Done.", None, ["app/move.py"]),
                          ("Done again.", None, []))
        owner, _ = make_owner(out("approval"), out("completion"), out("completion"))
        r = tj.run_change(arm=tj.load_arm("bare"), change=self.c[3], owner=owner, turn=turns, workspace=ws, out_dir=self.tmp)
        self.assertEqual([o["redirect_event"] for o in r.owner], [None, "delivered", None])
        self.assertEqual(r.redirect["outcome"], "delivered")
        self.assertTrue(turns.calls[2]["prompt"].startswith('By "move" I mean keep the same order number.'))

    def test_the_round_cap_stops_a_change(self):
        ws = FakeWorkspace()
        turns = FakeTurns(ws, *[("Still going.", None, [])] * 3)
        owner, _ = make_owner(*[out("stop")] * 3)
        r = tj.run_change(arm=tj.load_arm("bare"), change=self.c[1], owner=owner, turn=turns, workspace=ws, out_dir=self.tmp,
                          round_cap=3)
        self.assertEqual((r.rounds, r.finished, r.capped), (3, False, True))
        self.assertEqual(turns.calls[1]["prompt"], "Please continue.")

    def test_a_failed_turn_stops_the_change_but_still_records_and_commits(self):
        ws = FakeWorkspace()
        turns = FakeTurns(ws, ("Oops.", None, []), fail_at=0)
        owner, _ = make_owner()
        r = tj.run_change(arm=tj.load_arm("bare"), change=self.c[1], owner=owner, turn=turns, workspace=ws, out_dir=self.tmp)
        self.assertIn("turn 0 failed", r.error)
        self.assertEqual(len(ws.commits), 1)
        self.assertIsNone(owner.change)

    def test_owner_state_round_trips(self):
        owner, _ = make_owner(out("questions", [ans("Length?", "Short.", ["BK-09"])]), out("completion"))
        ws = FakeWorkspace()
        tj.run_change(arm=tj.load_arm("bare"), change=self.c[1], owner=owner,
                      turn=FakeTurns(ws, ("Length?", None, []), ("Done.", None, [])), workspace=ws, out_dir=self.tmp)
        state = json.loads(json.dumps(tj.owner_state(owner)))
        self.assertEqual((state["disclosed"], state["replicate"]), (["BK-09"], "t"))
        self.assertEqual(state["owner_model"], json.loads(json.dumps(asdict(sm.OwnerModel()))))
        twin, _ = make_owner(replicate="t")
        tj.restore_owner_state(twin, state)
        self.assertEqual((twin.record, twin.requests, twin.disclosed), (owner.record, owner.requests, {"BK-09"}))

    def test_a_state_saved_before_disclosure_was_tracked_takes_it_from_the_record(self):
        state = {"record": [{"change": 1, "said": "Short.", "question": "Length?", "items": ["BK-09"]},
                            {"change": 1, "said": "No preference, use your judgment.", "question": "Colour?", "items": []}],
                 "requests": [[1, "Please let me add a note."]], "seen": {}, "policy": "diligent", "seed": "old-id"}
        twin, _ = make_owner()
        tj.restore_owner_state(twin, state)
        self.assertEqual(twin.disclosed, {"BK-09"})

    def test_each_owner_record_carries_its_draws_and_recall(self):
        ws = FakeWorkspace()
        turns = FakeTurns(ws, ("Done. Orders are accepted all day.", None, ["app/notes.py"]), ("Done.", None, []))
        owner, _ = make_owner(out("completion", touches=[{"item": "BK-02", "passage": 1, "level": "direct"}]),
                              out("completion"))
        r = tj.run_change(arm=tj.load_arm("bare"), change=self.c[1], owner=owner, turn=turns, workspace=ws, out_dir=self.tmp)
        rec = json.loads((self.tmp / "owner-00.json").read_text())
        self.assertEqual([d["item"] for d in rec["draws"]], ["BK-02"])
        self.assertEqual(rec["passages"], 1)
        self.assertNotIn("catch_probability", rec)
        self.assertEqual(r.owner[0]["draws"], rec["draws"])
        fired = rec["draws"][0]["fired"]
        self.assertEqual([x["item"] for x in rec["recalled"]], ["BK-02"] if fired else [])
        self.assertEqual(r.rounds, 2 if fired else 1)  # a recall at a completion report keeps the change open


class RunOptionsTest(unittest.TestCase):
    def test_the_owner_model_comes_from_a_preset_a_json_object_or_a_file(self):
        self.assertEqual(rt.owner_model_from_arg(None), sm.OwnerModel())
        self.assertEqual(rt.owner_model_from_arg("pilot"), sm.OwnerModel.pilot())
        self.assertEqual(rt.owner_model_from_arg('{"scope": "stop", "half_words": 100}'),
                         sm.OwnerModel(scope="stop", half_words=100))
        path = Path(tempfile.mkdtemp()) / "corner.json"
        path.write_text(json.dumps({"preset": "pilot", "counting": "change"}))
        self.assertEqual(rt.owner_model_from_arg(str(path)), sm.OwnerModel(**{**asdict(sm.OwnerModel.pilot()), "counting": "change"}))
        with self.assertRaises(ValueError):
            rt.owner_model_from_arg('{"k": 1}')

    def test_a_trajectory_needs_a_replicate(self):
        parser = rt.build_parser()
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            parser.parse_args(["--arm", "bare", "--id", "t-bare-1"])
        self.assertEqual(parser.parse_args(["--arm", "bare", "--id", "t-bare-1", "--replicate", "r7"]).replicate, "r7")
        self.assertNotIn("defaults to the trajectory ID", rt.__doc__)


class OwnerBeforeChangeTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.owner, _ = make_owner()
        self.owner.record = [sm.Said(0, "Left from a failed attempt.", None, ("BK-02",))]
        self.owner.requests = [(0, "the brief")]
        self.owner.seen = {"docs/a.md": "old"}
        self.owner.disclosed = {"BK-02"}

    def test_the_first_build_starts_from_an_empty_owner(self):
        rt.prepare_owner(self.owner, self.dir, 0)
        self.assertEqual((self.owner.record, self.owner.requests, self.owner.seen, self.owner.disclosed), ([], [], {}, set()))

    def test_a_later_change_starts_from_the_owner_after_the_change_before(self):
        clean, _ = make_owner()
        clean.requests = [(0, "the brief")]
        (self.dir / "owner-state-00.json").write_text(json.dumps(tj.owner_state(clean)))
        rt.prepare_owner(self.owner, self.dir, 1)
        self.assertEqual((self.owner.record, self.owner.disclosed, self.owner.seen), ([], set(), {}))
        self.assertEqual(self.owner.requests, [(0, "the brief")])

    def test_a_later_change_without_the_state_before_it_stops(self):
        (self.dir / "owner-state.json").write_text(json.dumps(tj.owner_state(self.owner)))
        with self.assertRaisesRegex(RuntimeError, "owner-state-01.json"):
            rt.prepare_owner(self.owner, self.dir, 2)


class ProbeOptionsTest(unittest.TestCase):
    def test_a_probe_keys_its_draws_on_the_base_replicate_checkpoint_and_fork(self):
        self.assertEqual(rp.probe_replicate({"replicate": "r1"}, 3, 2, None), "r1-probe-3-fork-2")
        self.assertEqual(rp.probe_replicate({"replicate": "r1"}, 3, 2, "x"), "x")
        self.assertEqual(rp.probe_replicate({}, 3, 2, "x"), "x")
        with self.assertRaisesRegex(ValueError, "replicate"):
            rp.probe_replicate({}, 3, 2, None)

    def test_a_probe_of_a_trajectory_with_no_owner_model_says_it_assumed_one(self):
        self.assertEqual(rp.probe_owner_model({"owner_model_config": asdict(sm.OwnerModel.pilot())}), (sm.OwnerModel.pilot(), False))
        self.assertEqual(rp.probe_owner_model({}), (sm.OwnerModel(), True))


class AuditTest(unittest.TestCase):
    def test_the_audit_counts_repairs_in_every_owner_call(self):
        rec = {"calls": [{"problems": ["x"], "repairs": []}, {"problems": [], "repairs": ["a", "b"]}, {"trim": []}]}
        self.assertEqual(ao.repairs_in(rec), 2)
        self.assertEqual(ao.repairs_in({"calls": []}), 0)


if __name__ == "__main__":
    unittest.main()
