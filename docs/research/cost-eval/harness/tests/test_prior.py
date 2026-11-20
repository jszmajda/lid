"""prior-data and prior-observations (costeval/prior.py): an earlier run on the trajectory's own lineage, its record
carried to the checker and the judge, and the retained storage opened on a copy at its retained clock."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from costeval import grading, prior  # noqa: E402

PROBES = """# Probes

## Setups

### S0: Example archive

Start with empty data.

## Probes

### XX-01

#### P-XX01-b
- **Applies:** from change 23
- **Setup:** S0
- **Needs:** prior-data
- **Scenario:**
  1. At change 22, prepare S0. As Ada, add a note `Quill`. Retain the resulting storage. Then, on a copy of that storage, run step 2's requests; that log is the baseline.
  2. Open the retained storage on the build under test. As Ben, read Quill.
- **Expected observation:** The same as the change-22 baseline.

### XX-02

#### P-XX02-b
- **Applies:** from change 1, until change 1
- **Setup:** S0
- **Needs:** prior-data, prior-observations
- **Scenario:**
  1. At change 0, using that checkpoint's interface reference, prepare S0; as Visitor, look up Quill. Retain the resulting storage.
  2. Open that storage at the checkpoint under test, and repeat step 1's Visitor operations.
- **Expected observation:** The same answers.

### XX-03

#### P-XX03-a
- **Applies:** from change 20, until change 20
- **Setup:** S0
- **Needs:** prior-observations
- **Scenario:**
  1. At change 19, record the addresses used for step 2. Run it at both checkpoints.
  2. As Ada, add a note `Pebble`.
- **Expected observation:** The same outcome as at change 19.
"""


def runs_with_lineage() -> Path:
    runs = Path(tempfile.mkdtemp())

    def traj(tid, meta):
        (runs / tid).mkdir(parents=True, exist_ok=True)
        (runs / tid / "trajectory.json").write_text(json.dumps(meta))
    traj("g-ref-correct", {"changes": {str(n): {"commit": f"r{n}"} for n in range(0, 41)}})
    traj("g-ref-stale-c36", {"fork_of": "g-ref-correct", "from_change": 35,
                             "changes": {str(n): {"commit": f"s{n}"} for n in range(36, 40)}})
    traj("g-ref-stale-c36/course-forks/c36-reliance-1", {"kind": "reliance", "fork_of": "g-ref-stale-c36", "change": 39,
                                                         "changes": {"reliance": {"commit": "f39"}}})
    traj("g-bare-1/course-forks/c27-course-1", {"kind": "course", "fork_of": "g-bare-1", "change": 27,
                                                "changes": {"27": {"commit": "k27"}}})
    traj("g-bare-1", {"changes": {str(n): {"commit": f"b{n}"} for n in range(0, 41)}})
    return runs


class PreparationTest(unittest.TestCase):
    def test_a_prior_data_probe_names_its_preparation_change_setup_and_step(self):
        ps = {p.id: p for p in grading.parse_probes(PROBES).probes}
        prep = prior.preparation(ps["P-XX01-b"])
        self.assertEqual((prep.change, prep.setup), (22, "S0"))
        self.assertTrue(prep.step.startswith("1. At change 22, prepare S0."))
        self.assertTrue(prior.check_steps(ps["P-XX01-b"]).startswith("2. Open the retained storage"))
        self.assertEqual(prior.preparation(ps["P-XX02-b"]).change, 0)  # "At change 0, using ..., prepare S0"
        self.assertIsNone(prior.preparation(ps["P-XX03-a"]))  # observations only
        self.assertFalse(any(p.deferred for p in ps.values()))  # both needs are provided now

    def test_the_build_that_owns_an_earlier_change_is_found_up_the_lineage(self):
        runs = runs_with_lineage()
        own = prior.lineage_owner
        self.assertEqual(own(runs, "g-ref-correct", 35), ("g-ref-correct", "r35"))
        self.assertEqual(own(runs, "g-ref-stale-c36", 35), ("g-ref-correct", "r35"))  # before the fork: R+'s
        self.assertEqual(own(runs, "g-ref-stale-c36", 37), ("g-ref-stale-c36", "s37"))
        self.assertEqual(own(runs, "g-ref-stale-c36/course-forks/c36-reliance-1", 35), ("g-ref-correct", "r35"))
        self.assertEqual(own(runs, "g-ref-stale-c36/course-forks/c36-reliance-1", 39),
                         ("g-ref-stale-c36/course-forks/c36-reliance-1", "f39"))
        self.assertEqual(own(runs, "g-bare-1/course-forks/c27-course-1", 26), ("g-bare-1", "b26"))
        self.assertIsNone(own(runs, "g-ref-stale-c36", 99))

    def test_the_earlier_runs_a_grading_needs(self):
        runs = runs_with_lineage()
        ps = {p.id: p for p in grading.parse_probes(PROBES).probes}
        need = prior.requirements(runs, "g-ref-stale-c36", 23, [ps["P-XX01-b"]])
        self.assertEqual(need, {("g-ref-correct", 22): {"prepare": ["P-XX01-b"], "observe": []}})
        need = prior.requirements(runs, "g-bare-1", 1, [ps["P-XX02-b"]])  # prepared at 0, observed at 0 (the change before)
        self.assertEqual(need, {("g-bare-1", 0): {"prepare": ["P-XX02-b"], "observe": ["P-XX02-b"]}})
        need = prior.requirements(runs, "g-bare-1", 20, [ps["P-XX03-a"]])
        self.assertEqual(need, {("g-bare-1", 19): {"prepare": [], "observe": ["P-XX03-a"]}})
        # recorded already: nothing to run
        d = prior.earlier_dir(runs, "g-bare-1", 19) / "observations"
        d.mkdir(parents=True)
        (d / "P-XX03-a.json").write_text("{}")
        self.assertEqual(prior.requirements(runs, "g-bare-1", 20, [ps["P-XX03-a"]]), {})

    def test_prerequisites_run_once_under_a_lock_each(self):
        runs = runs_with_lineage()
        ps = {p.id: p for p in grading.parse_probes(PROBES).probes}
        calls = []

        def run(cmd):
            calls.append(cmd)
            owner, change = cmd[cmd.index("--id") + 1], int(cmd[cmd.index("--change") + 1])
            for pid in cmd[cmd.index("--prepare") + 1].split(",") if "--prepare" in cmd else []:
                d = prior.earlier_dir(runs, owner, change) / "prior" / pid
                d.mkdir(parents=True)
                (d / "record.json").write_text("{}")
                (d / "storage.tar").write_bytes(b"tar")
            return 0
        problems = prior.ensure(runs, "g-ref-stale-c36", 23, [ps["P-XX01-b"]], seed="rd", run=run)
        self.assertEqual(problems, {})
        self.assertEqual(len(calls), 1)
        self.assertIn("--id g-ref-correct --change 22 --seed rd --prepare P-XX01-b", " ".join(calls[0]))
        prior.ensure(runs, "g-ref-correct", 24, [ps["P-XX01-b"]], seed="rd", run=run)
        self.assertEqual(len(calls), 1)  # recorded already

        def failing(cmd):
            return 1
        problems = prior.ensure(runs, "g-bare-1", 20, [ps["P-XX03-a"]], seed="rd", run=failing)
        self.assertEqual(list(problems), ["P-XX03-a"])  # reported as not run, with why

    def test_the_record_a_preparation_leaves(self):
        lines = [{"seq": 4, "op": "mark", "request": {"text": "PROBE P-XX01-b START"}},
                 {"seq": 5, "op": "http", "clock": "2026-01-05 08:00:00", "request": {"method": "POST", "path": "/notes"},
                  "response": {"status": 201, "body": "{\"id\": 17}"}},
                 {"seq": 6, "op": "mark", "request": {"text": "KEEP Quill's record id: 17"}},
                 {"seq": 7, "op": "retain", "admin": None, "clock": "2026-01-05 08:00:00", "request": {}, "response": {"ok": True}},
                 {"seq": 8, "op": "http", "clock": "2026-01-12 08:00:00", "request": {"method": "GET", "path": "/notes/17/text"},
                  "response": {"status": 200, "body": "QUILL note.\n"}}]
        rec = prior.prep_record("P-XX01-b", 22, "c22", "S0", lines, reply="Prepared Quill.", retained_by="the executor")
        self.assertEqual((rec["clock"], rec["keep"], rec["retained"]), ("2026-01-05 08:00:00", ["Quill's record id: 17"],
                                                                         "the executor"))
        self.assertEqual(len(rec["log"]), 5)  # the whole preparation, the baseline after the retain included
        checker = prior.for_checker(rec, None)
        self.assertIn("Quill's record id: 17", checker)
        self.assertIn("Prepared Quill.", checker)
        self.assertIn("POST /notes -> 201", checker)
        self.assertIn("gt restore PRIOR-P-XX01-b", checker)
        judge = prior.for_judge(rec, None)
        self.assertIn('"path": "/notes/17/text"', judge)  # the baseline's requests and responses
        self.assertIn("QUILL note.", judge)
        self.assertIn("change 22", judge)

    def test_an_executor_that_never_retains_is_retained_at_the_end_and_says_so(self):
        lines = [{"seq": 1, "op": "http", "clock": "2026-01-05 09:00:00", "request": {"method": "GET", "path": "/"},
                  "response": {"status": 200, "body": "[]"}}]
        rec = prior.prep_record("P-X", 3, "c3", "S0", lines, reply="", retained_by="the harness, at the end")
        self.assertEqual((rec["clock"], rec["retained"]), ("2026-01-05 09:00:00", "the harness, at the end"))


class RenderTest(unittest.TestCase):
    def test_the_checker_and_the_judge_get_the_earlier_record_and_the_checker_opens_the_retained_storage(self):
        ps = {p.id: p for p in grading.parse_probes(PROBES).probes}
        p = ps["P-XX01-b"]
        text = grading.render_for_execution([p], earlier={p.id: "RECORD OF THE PREPARATION"})
        self.assertIn("RECORD OF THE PREPARATION", text)
        self.assertIn("2. Open the retained storage", text)
        self.assertNotIn("At change 22, prepare S0", text)  # done already: not for this checker to repeat
        plain = grading.render_for_execution([ps["P-XX03-a"]])
        self.assertIn("At change 19", plain)
        judged = grading.render_for_judgment([p], earlier={p.id: "THE BASELINE LOG"})
        self.assertIn("THE BASELINE LOG", judged)
        self.assertIn("At change 22, prepare S0", judged)  # the judge reads the whole scenario
        prep = grading.render_for_preparation(p)
        self.assertIn("1. At change 22, prepare S0.", prep)
        self.assertNotIn("2. Open the retained storage", prep)
        self.assertIn("gt retain", prep)
        self.assertIn("gt mark 'KEEP", prep)


class CheckpointStorageTest(unittest.TestCase):
    def test_retained_storage_goes_out_as_a_tar_and_comes_back_under_its_prior_name(self):
        calls = []

        class P:
            returncode, stdout, stderr = 0, b"TARBYTES", b""

        def runner(cmd, **kw):
            calls.append((cmd, kw.get("input")))
            return P()
        ck = grading.Checkpoint(trajectory="t", change=22, commit="c", image="img", runner=runner)
        self.assertEqual(ck.tar_out("PREP-P-XX01-b"), b"TARBYTES")
        self.assertIn("tar -C /work/snap -cf - PREP-P-XX01-b", " ".join(calls[0][0]))
        ck.tar_in("PRIOR-P-XX01-b", b"TARBYTES")
        cmd, stdin = calls[1]
        self.assertEqual(stdin, b"TARBYTES")
        self.assertIn("mkdir -p /work/snap/PRIOR-P-XX01-b && tar -C /work/snap/PRIOR-P-XX01-b -xf - --strip-components=1",
                      " ".join(cmd))


if __name__ == "__main__":
    unittest.main()


class FakeCk:
    """The checkpoint's storage moves, recorded."""

    def __init__(self):
        self.snap, self.calls = {}, []

    def admin(self, worker, payload):
        self.calls.append(("admin", dict(payload)))
        if payload.get("_op") == "snapshot":
            self.snap[payload["name"]] = b"end-of-step"
        return {"ok": True}

    def tar_out(self, name):
        return self.snap[name]

    def tar_in(self, name, data):
        self.calls.append(("tar_in", name, data))
        self.snap[name] = data


class EarlierRunTest(unittest.TestCase):
    def setUp(self):
        self.runs = runs_with_lineage()
        self.ps = grading.parse_probes(PROBES)
        self.ck, self.executed = FakeCk(), []

    def execute(self, retains=True):
        def run(bid, batch, *, text=None, earlier=None, retain=None):
            self.executed.append({"bid": bid, "probes": [p.id for p in batch], "text": text, "earlier": earlier, "retain": retain})
            lines = [{"seq": 1, "op": "mark", "clock": "2026-01-05 08:00:00", "request": {"text": f"PROBE {batch[0].id} START"}},
                     {"seq": 2, "op": "mark", "clock": "2026-01-05 08:00:00", "request": {"text": "KEEP Quill id: 17"}}]
            if retain and retains:
                self.ck.snap[retain] = b"as-retained"
                lines.append({"seq": 3, "op": "retain", "clock": "2026-01-05 08:00:00", "request": {}, "response": {"ok": True}})
            lines.append({"seq": 4, "op": "http", "clock": "2026-01-12 08:00:00", "request": {"method": "GET", "path": "/x"},
                          "response": {"status": 200, "body": "baseline"}})
            return lines, "notes"
        return run

    def test_a_preparation_keeps_the_storage_as_retained_and_its_record(self):
        import grade_checkpoint as gck
        out = prior.earlier_dir(self.runs, "g-ref-correct", 22)
        s = gck.run_earlier(self.ck, out, self.runs, "g-ref-correct", 22, "r22", self.ps, ["P-XX01-b"], [],
                            execute=self.execute(), seed="rd", run=lambda cmd: 0)
        self.assertEqual(self.executed[0]["retain"], "PREP-P-XX01-b")
        self.assertIn("gt retain", self.executed[0]["text"])
        d = prior.prep_dir(self.runs, "g-ref-correct", 22, "P-XX01-b")
        self.assertEqual((d / "storage.tar").read_bytes(), b"as-retained")  # before the baseline ran on its copy
        rec = json.loads((d / "record.json").read_text())
        self.assertEqual((rec["retained"], rec["keep"], rec["clock"]), ("the executor", ["Quill id: 17"], "2026-01-05 08:00:00"))
        self.assertTrue(any(r.get("op") == "http" and r["response"]["body"] == "baseline" for r in rec["log"]))  # the baseline
        self.assertEqual(s["prepared"], ["P-XX01-b"])

    def test_without_a_retain_the_harness_keeps_the_storage_at_the_end(self):
        import grade_checkpoint as gck
        out = prior.earlier_dir(self.runs, "g-ref-correct", 22)
        gck.run_earlier(self.ck, out, self.runs, "g-ref-correct", 22, "r22", self.ps, ["P-XX01-b"], [],
                        execute=self.execute(retains=False), seed="rd", run=lambda cmd: 0)
        self.assertIn(("admin", {"_op": "snapshot", "name": "PREP-P-XX01-b"}), self.ck.calls)
        rec = json.loads((prior.prep_dir(self.runs, "g-ref-correct", 22, "P-XX01-b") / "record.json").read_text())
        self.assertEqual(rec["retained"], "the harness, at the end")

    def test_an_earlier_observation_runs_the_later_steps_on_a_copy_of_the_storage_prepared_first(self):
        import grade_checkpoint as gck
        out = prior.earlier_dir(self.runs, "g-bare-1", 0)
        gck.run_earlier(self.ck, out, self.runs, "g-bare-1", 0, "b0", self.ps, ["P-XX02-b"], ["P-XX02-b"],
                        execute=self.execute(), seed="rd", run=lambda cmd: 0)
        self.assertEqual([e["retain"] for e in self.executed], ["PREP-P-XX02-b", None])  # prepared, then observed
        self.assertIn(("tar_in", "PRIOR-P-XX02-b", b"as-retained"), self.ck.calls)
        self.assertIn("gt restore PRIOR-P-XX02-b", self.executed[1]["earlier"]["P-XX02-b"])
        obs = json.loads(prior.obs_path(self.runs, "g-bare-1", 0, "P-XX02-b").read_text())
        self.assertEqual((obs["change"], obs["notes"]), (0, "notes"))

    def test_an_observation_needing_another_builds_preparation_asks_for_it_first(self):
        import grade_checkpoint as gck
        calls = []

        def run(cmd):
            calls.append(" ".join(cmd))
            d = prior.prep_dir(self.runs, "g-ref-correct", 22, "P-XX01-b")
            d.mkdir(parents=True, exist_ok=True)
            (d / "record.json").write_text(json.dumps(prior.prep_record("P-XX01-b", 22, "r22", "S0", [], reply="",
                                                                         retained_by="the executor")))
            (d / "storage.tar").write_bytes(b"prepared-at-22")
            return 0
        out = prior.earlier_dir(self.runs, "g-ref-correct", 24)
        gck.run_earlier(self.ck, out, self.runs, "g-ref-correct", 24, "r24", self.ps, [], ["P-XX01-b"],
                        execute=self.execute(), seed="rd", run=run)
        self.assertTrue(any("--id g-ref-correct --change 22 --seed rd --prepare P-XX01-b" in c for c in calls))
        self.assertIn(("tar_in", "PRIOR-P-XX01-b", b"prepared-at-22"), self.ck.calls)


class GradingInputsTest(unittest.TestCase):
    def test_a_grading_gets_each_probes_earlier_records_and_storage_or_reports_it_not_run(self):
        import grade_checkpoint as gck
        runs = runs_with_lineage()
        ps = grading.parse_probes(PROBES)
        d = prior.prep_dir(runs, "g-ref-correct", 22, "P-XX01-b")
        d.mkdir(parents=True)
        (d / "record.json").write_text(json.dumps(prior.prep_record("P-XX01-b", 22, "r22", "S0", [
            {"seq": 9, "op": "http", "clock": "2026-01-13 09:00:00", "request": {"method": "GET", "path": "/quill"},
             "response": {"status": 200, "body": "QUILL"}}], reply="kept Quill", retained_by="the executor")))
        (d / "storage.tar").write_bytes(b"tar")
        got = gck.prior_inputs(runs, "g-ref-stale-c36", 37, ps.probes, seed="rd", run=lambda cmd: 1)
        self.assertEqual(set(got["checker"]), {"P-XX01-b"})
        self.assertIn("kept Quill", got["checker"]["P-XX01-b"])
        self.assertIn('"path": "/quill"', got["judge"]["P-XX01-b"])  # the baseline, at every checkpoint
        self.assertEqual(got["storage"], {"P-XX01-b": d / "storage.tar"})
        self.assertEqual(set(got["missing"]), {"P-XX02-b", "P-XX03-a"})  # their earlier runs failed: not run, with why


class OpenInTurnTest(unittest.TestCase):
    """N1: the prepared storage reaches the build under test the way an owner's data would, opened in turn by the
    build of every change after its preparation, at the retained clock, each result kept for later gradings."""

    def setUp(self):
        self.runs = runs_with_lineage()
        self.ps = {p.id: p for p in grading.parse_probes(PROBES).probes}
        d = prior.prep_dir(self.runs, "g-ref-correct", 22, "P-XX01-b")
        d.mkdir(parents=True)
        (d / "record.json").write_text(json.dumps(prior.prep_record("P-XX01-b", 22, "r22", "S0", [], reply="",
                                                                     retained_by="the executor")))
        (d / "storage.tar").write_bytes(b"s22")
        self.hops = []

    def hop(self, fail_at=(), grader_fault_at=()):
        def run(k, owner, commit, storages):
            self.hops.append((k, owner, commit, sorted(storages)))
            if k in grader_fault_at:
                return {pid: {"came_up": None, "error": "no start spec brings this build's service up"} for pid in storages}
            return {pid: {"came_up": k not in fail_at, "storage": data + f">{k}".encode(), "spec_from": "own",
                          "error": None if k not in fail_at else "service exited with 1"} for pid, data in storages.items()}
        return run

    def test_each_build_from_the_preparation_to_the_one_under_test_opens_it_in_turn(self):
        got = prior.open_in_turn(self.runs, "g-ref-correct", 25, [self.ps["P-XX01-b"]], hop=self.hop())
        self.assertEqual([h[0] for h in self.hops], [23, 24, 25])
        self.assertEqual([h[2] for h in self.hops], ["r23", "r24", "r25"])  # each change's own commit
        r = got["P-XX01-b"]
        self.assertEqual((r["storage"], r["final_came_up"], r["grader_fault"]), (b"s22>23>24>25", True, None))
        self.assertEqual([h["change"] for h in r["hops"]], [23, 24, 25])
        # a later grading carries on from the copy kept at 25
        self.hops.clear()
        got = prior.open_in_turn(self.runs, "g-ref-correct", 27, [self.ps["P-XX01-b"]], hop=self.hop())
        self.assertEqual([h[0] for h in self.hops], [26, 27])
        self.assertEqual(got["P-XX01-b"]["storage"], b"s22>23>24>25>26>27")

    def test_a_fork_opens_its_parents_builds_then_its_own(self):
        prior.open_in_turn(self.runs, "g-ref-stale-c36", 37, [self.ps["P-XX01-b"]], hop=self.hop())
        owners = {h[0]: h[1] for h in self.hops}
        self.assertEqual((owners[35], owners[36], owners[37]), ("g-ref-correct", "g-ref-stale-c36", "g-ref-stale-c36"))
        self.assertEqual(len(self.hops), 15)  # 23 to 37

    def test_a_build_that_doesnt_come_up_on_the_storage_is_the_arms_fault_recorded_at_that_build(self):
        got = prior.open_in_turn(self.runs, "g-ref-correct", 25, [self.ps["P-XX01-b"]], hop=self.hop(fail_at={24}))
        r = got["P-XX01-b"]
        self.assertEqual([(h["change"], h["came_up"]) for h in r["hops"]], [(23, True), (24, False), (25, True)])
        self.assertEqual((r["final_came_up"], r["grader_fault"]), (True, None))  # carried on with what 24 left
        got = prior.open_in_turn(self.runs, "g-bare-1", 0, [], hop=self.hop())  # nothing asked, nothing done
        self.assertEqual(got, {})

    def test_the_build_under_test_failing_to_come_up_fails_the_probe(self):
        r = prior.open_in_turn(self.runs, "g-ref-correct", 24, [self.ps["P-XX01-b"]], hop=self.hop(fail_at={24}))["P-XX01-b"]
        self.assertFalse(r["final_came_up"])
        v = prior.unopened_verdict(r, 24)
        self.assertEqual((v["verdict"], v["cause"]), ("not met", "none"))
        self.assertIn("didn't come up", v["reason"])

    def test_a_build_no_start_spec_can_start_is_the_graders_fault_and_the_probe_isnt_run(self):
        r = prior.open_in_turn(self.runs, "g-ref-correct", 25, [self.ps["P-XX01-b"]],
                               hop=self.hop(grader_fault_at={24}))["P-XX01-b"]
        self.assertIn("change 24", r["grader_fault"])
        self.assertIsNone(r["storage"])
        self.assertEqual([h[0] for h in self.hops], [23, 24])  # the chain stops there


class HopOnDockerTest(unittest.TestCase):
    """make_hop: one build's service started with a spec that brings it up, each storage restored on it and saved."""

    def fake_checkpoint(self, ready_specs, restore_ok):
        test = self

        class Ck:
            def __init__(self, trajectory, change, commit, image):
                self.volume, self.tools_volume = f"v-{change}", f"t-{change}"
                test.made.append((trajectory, change, commit))
                self.spec = None
                self.snap = {}

            def export(self, ws):
                test.ops.append(("export", ws))

            def sh(self, vol, script, **kw):
                return ""

            def put(self, vol, path, text):
                if path.endswith("start-0.json"):
                    self.spec = json.loads(text)

            def start_apps(self, n):
                test.ops.append(("start", self.spec["command"]))

            def wait_ready(self, k, timeout_s=0):
                return self.spec["command"] in ready_specs

            def stop(self, n):
                test.ops.append(("stop",))

            def tar_in(self, name, data):
                self.snap[name] = data

            def admin(self, k, payload):
                test.ops.append((payload["_op"], payload["name"]))
                if payload["_op"] == "snapshot":
                    self.snap[payload["name"]] += b"+opened"
                return {"ok": restore_ok} if payload["_op"] == "restore" else {"ok": True}

            def tar_out(self, name):
                return self.snap[name]
        return Ck

    def setUp(self):
        import grade_checkpoint as gck
        self.gck, self.made, self.ops = gck, [], []
        self.runs = runs_with_lineage()
        (self.runs / "g-bare-1" / "trajectory.json").write_text(json.dumps(
            {"volumes": {"workspace": "ce-g-bare-1-ws"}, "changes": {str(n): {"commit": f"b{n}"} for n in range(41)}}))
        self.saved = (gck.grading.Checkpoint, gck.subprocess.run)
        gck.subprocess.run = lambda *a, **kw: None

    def tearDown(self):
        self.gck.grading.Checkpoint, self.gck.subprocess.run = self.saved

    def spec(self, cmd):
        return {"workdir": "/work/app", "command": cmd, "port": 8000, "data_path": "{DATA}"}

    def test_the_first_spec_that_brings_the_build_up_opens_each_storage(self):
        self.gck.grading.Checkpoint = self.fake_checkpoint({"fallback-b"}, restore_ok=True)
        hop = self.gck.make_hop(self.runs, [("a", self.spec("fallback-a")), ("b", self.spec("fallback-b"))])
        got = hop(24, "g-bare-1", "b24", {"P-1": b"s"})
        self.assertEqual(self.made[0][1:], (24, "b24"))
        self.assertIn(("export", "ce-g-bare-1-ws"), self.ops)
        self.assertEqual([o for o in self.ops if o[0] in ("restore", "snapshot")], [("restore", "HOP-P-1"), ("snapshot", "HOP-P-1")])
        self.assertEqual(got["P-1"], {"came_up": True, "error": None, "storage": b"s+opened", "spec_from": "b"})

    def test_a_service_that_starts_empty_but_not_on_the_storage_didnt_come_up(self):
        self.gck.grading.Checkpoint = self.fake_checkpoint({"fallback-a"}, restore_ok=False)
        got = self.gck.make_hop(self.runs, [("a", self.spec("fallback-a"))])(24, "g-bare-1", "b24", {"P-1": b"s"})
        self.assertFalse(got["P-1"]["came_up"])

    def test_no_spec_that_starts_the_build_is_the_graders_fault(self):
        self.gck.grading.Checkpoint = self.fake_checkpoint(set(), restore_ok=True)
        got = self.gck.make_hop(self.runs, [("a", self.spec("fallback-a"))])(24, "g-bare-1", "b24", {"P-1": b"s"})
        self.assertIsNone(got["P-1"]["came_up"])
