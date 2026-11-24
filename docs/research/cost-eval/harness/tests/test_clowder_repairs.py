"""Tests for repair forks (run_clowder_repairs.py): for each miss in a graded fork (a Clowder variant's, M2f, or a named
start's, M2h), a fork from that fork's own result, opened by the owner's repair report, then graded and recorded against
the fork it repairs.

Docker, the agent's turns and the owner's model calls are fakes; the seed is test_simulator's made-up bakery.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_clowder_repairs as rcr  # noqa: E402
import run_fork as rf  # noqa: E402
from costeval import trajectory as tj  # noqa: E402
from test_run_fork import BOTH, LID_TREE, NODE, Docker, Fixture, HashDocker, StartFixture  # noqa: E402
from test_simulator import FakeAsk, out  # noqa: E402

ARM = "m2f-lid-lid-full-c01-r2"


def write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


class Base(unittest.TestCase):
    def setUp(self):
        self.f = Fixture()
        self.f.ask = FakeAsk(*[out("completion") for _ in range(8)])  # the fork and its repairs, one reply each
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(rf.main(self.f.argv("--id", ARM, variant="lid", arm="lid-full"), deps=self.f.deps()), 0)
        self.arm = self.f.runs / ARM
        self.meta = json.loads((self.arm / "trajectory.json").read_text())
        self.files = self.f.seed / "hidden"
        write(self.files / "repair-reports.json", {"BK-02": {"report": "An order came in after six."},
                                                   "DEP-01": {"report": "The list and the count disagree.", "change": 1}})
        self.grading(self.arm, items={"BK-02": "not met", "BK-03": "met"}, dependency_met=False,
                     tests={"x::a": "ok", "x::b": "ok"}, probes={"t::probe_m2f_a": "passed"}, held={"q::kept": "passed"})

    def grading(self, run: Path, *, items, dependency_met, tests, probes, held=None):
        g = run / "grading" / "change-01"

        def rec(r):  # a result, or (result, extra fields)
            return {"result": r} if isinstance(r, str) else {"result": r[0], **r[1]}
        write(g / "summary.json", {"items": items, "dependency_met": dependency_met,
                                   "dependency_probes": {t: rec(r) for t, r in probes.items()},
                                   "held_out_tests": {t: rec(r) for t, r in (held or {}).items()}})
        write(g / "keeping.json", {"targets": {"heldout_x": {"tests": tests}}})

    def argv(self, what, *extra):
        return [what, "--runs", str(self.f.runs), "--seed-files", str(self.files), "--brief", str(self.f.seed / "brief.md"),
                "--lid-repo", str(self.f.root), *extra]


class PlanTest(Base):
    def test_every_miss_of_a_graded_fork_is_listed_with_its_dependency(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(rcr.main(self.argv("plan", "--forks", "m2f-*")), 0)
        self.assertEqual(out.getvalue().split("\n"), [f"{ARM} BK-02", f"{ARM} DEP-01", ""])

    def test_a_dependency_whose_probes_are_missing_plans_no_repair(self):
        self.assertEqual(rcr.misses({"items": {}, "dependency_met": None,
                                     "dependency_missing": [{"test": "t::probe_m2f_a", "cause": "E0061"}]}, 1), [])
        self.assertEqual(rcr.misses({"items": {}, "dependency_met": False}, 1), ["DEP-01"])

    def test_the_node_graders_dependency_plans_a_repair_only_when_broken(self):
        # grade_node.py (M2h): the dependency's result is kept, broken, not exercised or missing
        for result, want in (("broken", ["DEP-01"]), ("kept", []), ("not exercised", []), ("missing", [])):
            self.assertEqual(rcr.misses({"items": {}, "dependency": {"result": result}}, 1), want, result)

    def test_a_dependency_is_planned_once_and_only_by_its_dependency_verdict(self):
        # grade_node.py's items carry the per-build dependency probe's row (DEP-05) beside the change's own rows; that
        # row never plans a repair of its own, so a broken dependency is one repair fork, not two run at once
        s = {"items": {"DEP-05": "not met", "OGM-0501": "not met", "OGM-0502": "met"}, "dependency": {"result": "broken"}}
        self.assertEqual(rcr.misses(s, 5), ["OGM-0501", "DEP-05"])
        self.assertEqual(rcr.misses({"items": {"DEP-05": "not met"}, "dependency": {"result": "kept"}}, 5), [])

    def test_node_keeping_and_dependency_compare_by_their_own_records(self):
        arm = {"dependency": {"result": "kept", "probes": {"P1": {"result": "kept"}, "P2": {"result": "kept"}}}}
        fix = {"dependency": {"result": "broken", "probes": {"P1": {"result": "broken"}, "P2": {"result": "missing"}}}}
        self.assertEqual(rcr._dependency_change(arm, fix), (["P1"], ["P2"]))
        self.assertEqual(rcr._dependency_fixed({"dependency": {"result": "kept"}}), True)
        self.assertEqual(rcr._dependency_fixed({"dependency": {"result": "broken"}}), False)
        self.assertIsNone(rcr._dependency_fixed({"dependency": {"result": "not exercised"}}))
        # keeping: the tests failing on the repair (against the start's baseline) that didn't fail on the fork
        self.assertEqual(rcr._broken_tests({"failures": {"a.test.js::x": {}}},
                                           {"failures": {"a.test.js::x": {}, "b.test.js::y": {}}}), ["b.test.js::y"])

    def test_a_dependency_report_is_found_under_the_change_number_written_either_way(self):
        # M2h's seed keys its dependency reports DEP-1 ... DEP-8; planning names them DEP-01
        self.assertEqual(rcr.report_text({"DEP-1": {"report": "It broke."}}, "DEP-01"), "It broke.")
        self.assertEqual(rcr.report_text({"DEP-13": {"report": "x"}}, "DEP-13"), "x")
        self.assertIsNone(rcr.report_text({"DEP-2": {"report": "x"}}, "DEP-01"))

    def test_a_fork_not_yet_graded_and_a_repair_fork_are_not_planned(self):
        (self.arm / "grading" / "change-01" / "summary.json").unlink()
        write(self.f.runs / f"{ARM}-fix-BK-02" / "trajectory.json", {"repair": {"of": ARM}})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rcr.main(self.argv("plan", "--forks", "m2f-*"))
        self.assertEqual(out.getvalue(), "")


class NullTest(Base):
    def test_a_null_fork_is_never_repaired_and_its_volumes_go_once_graded(self):
        null = self.f.runs / "m2f-null-c01"
        write(null / "trajectory.json", {"arm": "null", "change": 1, "changes": {"1": {"commit": "base", "null": True}},
                                         "volumes": {"workspace": "ce-m2f-null-c01-ws", "config": "ce-m2f-null-c01-cfg"}})
        self.grading(null, items={"BK-02": "not met"}, dependency_met=True, tests={}, probes={})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rcr.main(self.argv("plan", "--forks", "m2f-null-*"))
        self.assertEqual(out.getvalue(), "")
        removed = []
        with contextlib.redirect_stdout(io.StringIO()):
            rcr.main(self.argv("release", "--forks", "m2f-null-*"), docker=lambda cmd, **kw: removed.append(cmd))
        self.assertTrue(any("ce-m2f-null-c01-ws" in c for c in removed))


class RunTest(Base):
    def run_repair(self, item, docker=None):
        self.f.sessions.clear()
        docker = docker or Docker()
        with contextlib.redirect_stdout(io.StringIO()):
            rc = rcr.main(self.argv("run", "--of", ARM, "--item", item), deps=self.f.deps(docker))
        return rc, docker

    def test_a_repair_fork_starts_from_the_forks_result_with_its_owner_and_the_report(self):
        rc, docker = self.run_repair("BK-02")
        self.assertEqual(rc, 0)
        fid = f"{ARM}-fix-BK-02"
        meta = json.loads((self.f.runs / fid / "trajectory.json").read_text())
        self.assertEqual(meta["repair"]["of"], ARM)
        self.assertEqual(meta["repair"]["item"], "BK-02")
        self.assertEqual(meta["fork_of"], self.meta["fork_of"])  # the same variant set, for grading
        self.assertEqual(meta["start_commit"], self.meta["changes"]["1"]["commit"])  # the fork's own result
        self.assertEqual((meta["change"], meta["arm"], meta["window"]), (1, "lid-full", "200k"))
        self.assertEqual(meta["replicate"], "r1-fix-BK-02")
        # the workspace is a copy of the fork's, never the variant's, and jj isn't set up again over its history
        first = docker.calls[0]["cmd"]
        self.assertIn(f"ce-{ARM}-ws:/src:ro", first)
        self.assertIn(f"ce-{fid}-ws:/work", first)
        self.assertFalse(any("jj git init" in str(c["cmd"]) for c in docker.calls))
        self.assertEqual(self.f.installed[-1], (f"ce-{fid}-cfg", "v1.4.6"))  # the LID arm's plugin, fresh
        self.assertTrue(json.loads((self.f.runs / fid / "change-01" / "change.json").read_text())["finished"])
        first_prompt = (self.f.runs / fid / "change-01" / "prompt-00.txt").read_text()
        self.assertTrue(first_prompt.startswith("An order came in after six."))
        self.assertTrue(first_prompt.rstrip().endswith(tj.NEUTRAL_SENTENCE))
        self.assertTrue((self.f.runs / fid / "rot-cost.json").exists())  # cost, turns, model calls, time, files read

    def test_the_dependency_has_its_own_report_and_a_missing_report_stops_the_fork(self):
        self.assertEqual(self.run_repair("DEP-01")[0], 0)
        first_prompt = (self.f.runs / f"{ARM}-fix-DEP-01" / "change-01" / "prompt-00.txt").read_text()
        self.assertTrue(first_prompt.startswith("The list and the count disagree."))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc, docker = self.run_repair("BK-03")
        self.assertEqual((rc, docker.calls), (2, []))
        self.assertIn("no repair report for BK-03", err.getvalue())

    def test_a_recorded_repair_is_left_alone(self):
        self.run_repair("BK-02")
        rc, docker = self.run_repair("BK-02")
        self.assertEqual((rc, docker.calls), (0, []))

    def test_a_repair_already_running_is_refused_before_it_touches_anything(self):
        # two runs of one repair at once would copy into one volume and write one record: the second stops at once
        import fcntl
        lock = rcr.repair_lock_path(self.f.runs, f"{ARM}-fix-BK-02")
        lock.parent.mkdir(parents=True, exist_ok=True)
        with open(lock, "w") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                rc, docker = self.run_repair("BK-02")
        self.assertEqual((rc, docker.calls), (2, []))
        self.assertIn("already running", err.getvalue())
        self.assertFalse((self.f.runs / f"{ARM}-fix-BK-02").exists())
        self.assertEqual(self.run_repair("BK-02")[0], 0)  # once the other run lets go, it runs


class RecordTest(Base):
    def setUp(self):
        super().setUp()
        with contextlib.redirect_stdout(io.StringIO()):
            rcr.main(self.argv("run", "--of", ARM, "--item", "BK-02"), deps=self.f.deps())
        self.fix = self.f.runs / f"{ARM}-fix-BK-02"
        self.removed = []

    def record(self, item="BK-02"):
        with contextlib.redirect_stdout(io.StringIO()):
            return rcr.main(self.argv("record", "--of", ARM, "--item", item),
                            docker=lambda cmd, **kw: self.removed.append(cmd))

    def test_a_graded_repair_records_the_fix_keeping_against_the_fork_and_what_it_cost(self):
        self.grading(self.fix, items={"BK-02": "met", "BK-03": "not met"}, dependency_met=False,
                     tests={"x::a": "ok", "x::b": "FAILED"}, probes={"t::probe_m2f_a": "failed"}, held={"q::kept": "failed"})
        self.assertEqual(self.record(), 0)
        rec = json.loads((self.fix / "repair.json").read_text())
        self.assertEqual((rec["of"], rec["item"], rec["fixed"]), (ARM, "BK-02", True))
        self.assertEqual(rec["keeping"]["items_broken"], ["BK-03"])
        self.assertEqual(rec["keeping"]["tests_broken"], ["x::b"])
        self.assertEqual(rec["keeping"]["dependency_probes_broken"], ["t::probe_m2f_a"])
        self.assertEqual(rec["keeping"]["held_out_tests_broken"], ["q::kept"])  # change 20's graded held-out copies
        self.assertIn("agent_cost_usd", rec)
        self.assertIn("turns", rec["measures"])
        self.assertTrue(any(f"ce-{ARM}-fix-BK-02-ws" in c for c in self.removed))  # the repair fork's volumes go

    def test_a_probe_or_held_out_test_missing_after_the_repair_is_undetermined_not_broken(self):
        self.grading(self.fix, items={"BK-02": "met", "BK-03": "met"}, dependency_met=None,
                     tests={"x::a": "ok", "x::b": "ok"}, probes={"t::probe_m2f_a": ("not built", {"cause": "E0061"})},
                     held={"q::kept": ("failed", {"class": "new state only"})})
        self.assertEqual(self.record(), 0)
        rec = json.loads((self.fix / "repair.json").read_text())
        self.assertEqual(rec["keeping"]["dependency_probes_broken"], [])
        self.assertEqual(rec["keeping"]["dependency_probes_undetermined"], ["t::probe_m2f_a"])
        self.assertEqual(rec["keeping"]["held_out_tests_broken"], [])  # new state only: kept, as keeping counts it
        self.assertEqual(rec["keeping"]["held_out_tests_undetermined"], [])

    def test_a_dependency_repair_whose_probes_are_missing_is_undetermined(self):
        with contextlib.redirect_stdout(io.StringIO()):
            rcr.main(self.argv("run", "--of", ARM, "--item", "DEP-01"), deps=self.f.deps())
        fix = self.f.runs / f"{ARM}-fix-DEP-01"
        self.grading(fix, items={"BK-02": "not met", "BK-03": "met"}, dependency_met=None,
                     tests={"x::a": "ok", "x::b": "ok"}, probes={"t::probe_m2f_a": ("not built", {"cause": "E0061"})})
        self.assertEqual(self.record("DEP-01"), 0)
        self.assertIsNone(json.loads((fix / "repair.json").read_text())["fixed"])

    def test_removing_a_forks_volumes_trims_the_vm_disk_after(self):
        self.grading(self.fix, items={"BK-02": "met", "BK-03": "met"}, dependency_met=False,
                     tests={"x::a": "ok", "x::b": "ok"}, probes={"t::probe_m2f_a": "passed"})
        trims = []
        with contextlib.redirect_stdout(io.StringIO()):
            rcr.main(self.argv("record", "--of", ARM, "--item", "BK-02"),
                     docker=lambda cmd, **kw: self.removed.append(cmd), trim=lambda: trims.append(1))
        self.assertEqual(len(trims), 1)

    def test_the_dependency_is_fixed_when_its_probes_pass(self):
        with contextlib.redirect_stdout(io.StringIO()):
            rcr.main(self.argv("run", "--of", ARM, "--item", "DEP-01"), deps=self.f.deps())
        fix = self.f.runs / f"{ARM}-fix-DEP-01"
        self.grading(fix, items={"BK-02": "not met", "BK-03": "met"}, dependency_met=True,
                     tests={"x::a": "ok", "x::b": "ok"}, probes={"t::probe_m2f_a": "passed"})
        self.assertEqual(self.record("DEP-01"), 0)
        rec = json.loads((fix / "repair.json").read_text())
        self.assertEqual((rec["fixed"], rec["keeping"]["items_broken"]), (True, []))

    def test_an_ungraded_repair_records_nothing(self):
        self.assertEqual(self.record(), 1)
        self.assertFalse((self.fix / "repair.json").exists())

    def test_release_removes_a_forks_volumes_once_every_miss_has_its_repair_recorded(self):
        self.grading(self.fix, items={"BK-02": "met", "BK-03": "met"}, dependency_met=False,
                     tests={"x::a": "ok", "x::b": "ok"}, probes={"t::probe_m2f_a": "passed"})
        self.record()
        with contextlib.redirect_stdout(io.StringIO()):
            rcr.main(self.argv("release", "--forks", "m2f-*"), docker=lambda cmd, **kw: self.removed.append(cmd))
        self.assertFalse(any(f"ce-{ARM}-ws" in c for c in self.removed))  # DEP-01 isn't repaired yet: kept
        with contextlib.redirect_stdout(io.StringIO()):
            rcr.main(self.argv("run", "--of", ARM, "--item", "DEP-01"), deps=self.f.deps())
        fix = self.f.runs / f"{ARM}-fix-DEP-01"
        self.grading(fix, items={"BK-02": "not met", "BK-03": "met"}, dependency_met=True,
                     tests={"x::a": "ok", "x::b": "ok"}, probes={"t::probe_m2f_a": "passed"})
        self.record("DEP-01")
        with contextlib.redirect_stdout(io.StringIO()):
            rcr.main(self.argv("release", "--forks", "m2f-*"), docker=lambda cmd, **kw: self.removed.append(cmd))
        self.assertTrue(any(f"ce-{ARM}-ws" in c and f"ce-{ARM}-cfg" in c for c in self.removed))


M2H = "m2h-lid-full-arrows-c01-r2"


class M2hBase(unittest.TestCase):
    """An M2h LID fork from a mapped start, graded with misses; its seed is synthetic (the bakery), in the place of
    seeds/opengym/hidden/m2h/."""

    npm = "on"

    def setUp(self):
        self.f = StartFixture()
        self.f.ask = FakeAsk(*[out("completion") for _ in range(8)])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(rf.main(self.f.start_argv("--id", M2H, "--npm-network", self.npm, start="lid-r1",
                                                       arm="lid-full-arrows"), deps=self.f.deps(HashDocker())), 0)
        self.arm = self.f.runs / M2H
        self.meta = json.loads((self.arm / "trajectory.json").read_text())
        self.files = self.f.seed / "hidden"
        write(self.files / "repair-reports.json", {"BK-02": {"report": "An order came in after six."},
                                                   "DEP-01": {"report": "The list and the count disagree.", "change": 1}})
        g = self.arm / "grading" / "change-01"
        write(g / "summary.json", {"items": {"BK-02": "not met", "BK-03": "met"}, "dependency_met": False,
                                   "dependency_probes": {"t::dep": {"result": "passed"}}, "held_out_tests": {}})
        write(g / "keeping.json", {"targets": {}})
        self.removed = []

    def argv(self, what, *extra):  # no --brief: a repair takes the brief its fork recorded
        return [what, "--runs", str(self.f.runs), "--seed-files", str(self.files), "--lid-repo", str(self.f.root), *extra]

    def run_repair(self, item="BK-02", *extra, docker=None):
        self.f.sessions.clear()
        docker = docker or HashDocker()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = rcr.main(self.argv("run", "--of", M2H, "--item", item, *extra), deps=self.f.deps(docker))
        return rc, docker


class M2hRepairTest(M2hBase):
    def test_a_repair_copies_the_arm_forks_own_volume_with_its_lid_setup_image_and_isolation(self):
        rc, docker = self.run_repair()
        self.assertEqual(rc, 0)
        fid = f"{M2H}-fix-BK-02"
        meta = json.loads((self.f.runs / fid / "trajectory.json").read_text())
        self.assertEqual(meta["volumes"], {"workspace": f"{fid}-ws", "config": f"{fid}-cfg"})
        self.assertEqual(meta["fork_of"], self.meta["fork_of"])
        self.assertEqual((meta["image"], meta["arm"], meta["start_commit"]),
                         (NODE, "lid-full-arrows", self.meta["changes"]["1"]["commit"]))
        self.assertEqual((meta["npm_network"], meta["isolation"]), (True, self.meta["isolation"]))
        self.assertEqual(meta["lid_install_sha256"], LID_TREE)
        copy = docker.calls[0]["cmd"]
        self.assertIn(f"{M2H}-ws:/src:ro", copy)  # the arm fork's own workspace, never the start
        self.assertIn(f"{fid}-ws:/work", copy)
        every = [" ".join(c["cmd"]) for c in docker.calls]
        self.assertFalse(any("ce-" in s or "ogmap-" in s or "rm -rf /work/target" in s for s in every))
        self.assertEqual(self.f.installed[-1], (f"{fid}-cfg", "v1.4.6"))
        session = self.f.sessions[0]
        self.assertEqual((session.image, session.plugin_dirs, session.config_volume), (NODE, BOTH, f"{fid}-cfg"))
        self.assertEqual(session.isolation.record(), self.meta["isolation"])
        first_prompt = (self.f.runs / fid / "change-01" / "prompt-00.txt").read_text()
        self.assertTrue(first_prompt.startswith("An order came in after six."))

    def test_a_dependency_repair_opens_with_its_own_report(self):
        self.assertEqual(self.run_repair("DEP-01")[0], 0)
        first_prompt = (self.f.runs / f"{M2H}-fix-DEP-01" / "change-01" / "prompt-00.txt").read_text()
        self.assertTrue(first_prompt.startswith("The list and the count disagree."))

    def test_a_repairs_lid_install_must_match_its_forks(self):
        with self.assertRaisesRegex(RuntimeError, "LID install"):
            self.run_repair(docker=HashDocker(tree="0ther"))
        self.assertEqual(self.f.sessions, [])

    def test_a_brief_or_oracle_other_than_the_forks_is_refused(self):
        other = self.f.root / "other-brief.md"
        other.write_text("# Some other project\n")
        rc, docker = self.run_repair("BK-02", "--brief", str(other))
        self.assertEqual((rc, docker.calls), (2, []))
        oracle = self.files / "oracle.md"
        oracle.write_text(oracle.read_text() + "\nA line added later.\n")
        rc, docker = self.run_repair()
        self.assertEqual((rc, docker.calls), (2, []))

    def test_record_and_release_remove_the_volumes_named_for_each_fork(self):
        self.assertEqual(self.run_repair()[0], 0)
        fix = self.f.runs / f"{M2H}-fix-BK-02"
        g = fix / "grading" / "change-01"
        write(g / "summary.json", {"items": {"BK-02": "met", "BK-03": "met"}, "dependency_met": False,
                                   "dependency_probes": {"t::dep": {"result": "passed"}}, "held_out_tests": {}})
        write(g / "keeping.json", {"targets": {}})
        drop = lambda cmd, **kw: self.removed.append(cmd)  # noqa: E731
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(rcr.main(self.argv("record", "--of", M2H, "--item", "BK-02"), docker=drop), 0)
        self.assertIn(["docker", "volume", "rm", "-f", f"{M2H}-fix-BK-02-ws", f"{M2H}-fix-BK-02-cfg"], self.removed)
        self.assertTrue(json.loads((fix / "repair.json").read_text())["fixed"])
        self.assertEqual(self.run_repair("DEP-01")[0], 0)
        fix = self.f.runs / f"{M2H}-fix-DEP-01"
        write(fix / "grading" / "change-01" / "summary.json",
              {"items": {"BK-02": "not met", "BK-03": "met"}, "dependency_met": True,
               "dependency_probes": {"t::dep": {"result": "passed"}}, "held_out_tests": {}})
        write(fix / "grading" / "change-01" / "keeping.json", {"targets": {}})
        with contextlib.redirect_stdout(io.StringIO()):
            rcr.main(self.argv("record", "--of", M2H, "--item", "DEP-01"), docker=drop)
            rcr.main(self.argv("release", "--forks", "m2h-*"), docker=drop)
        self.assertIn(["docker", "volume", "rm", "-f", f"{M2H}-ws", f"{M2H}-cfg"], self.removed)
        self.assertFalse(any("ogmap-" in " ".join(c) for c in self.removed))  # the starts are never released

    def test_plan_lists_an_m2h_forks_misses(self):
        out_ = io.StringIO()
        with contextlib.redirect_stdout(out_):
            rcr.main(self.argv("plan", "--forks", "m2h-*"))
        self.assertEqual(out_.getvalue().split("\n"), [f"{M2H} BK-02", f"{M2H} DEP-01", ""])


class M2hOfflineRepairTest(M2hBase):
    npm = "off"

    def test_a_repair_keeps_its_forks_npm_setting(self):
        rc, _ = self.run_repair()
        self.assertEqual(rc, 0)
        meta = json.loads((self.f.runs / f"{M2H}-fix-BK-02" / "trajectory.json").read_text())
        self.assertIs(meta["npm_network"], False)
        self.assertTrue(set(rf.NPM_HOSTS) <= set(self.f.sessions[0].isolation.blocked_hosts))
        self.assertEqual(meta["isolation"], self.meta["isolation"])


if __name__ == "__main__":
    unittest.main()
