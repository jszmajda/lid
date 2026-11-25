"""Tests for repair forks (run_repair_forks.py): for each latent item a checkpoint's grading has as not met, a fork from
that checkpoint's snapshot whose opening message is the owner's repair report, graded in full afterwards for the fix
and for keeping.

Run from the harness folder: python3.12 -m unittest discover -s tests
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

import run_course_forks as rcf  # noqa: E402
import run_repair_forks as rrf  # noqa: E402
from costeval import prior  # noqa: E402
from test_grading import PROBES  # noqa: E402
from test_growth import EMPTY_STATE, GROWTH_SCRIPT, subprocess_ok  # noqa: E402
from test_simulator import BRIEF, CHANGES as SYMPTOM_SCRIPT, ORACLE, OWNER_ITEMS, FakeAsk, out  # noqa: E402
from test_trajectory import FakeTurns, FakeWorkspace  # noqa: E402

MORE_PROBES = PROBES + ("\n### BK-03\n\n#### P-BK03-a\n- **Applies:** from change 0\n- **Setup:** S0\n- **Needs:** none\n"
                        "- **Scenario:**\n  1. Look for last year's order.\n- **Expected observation:** It is still there.\n"
                        "\n### BK-07\n\n#### P-BK07-a\n- **Applies:** from change 5\n- **Setup:** S0\n- **Needs:** none\n"
                        "- **Scenario:**\n  1. Refund an order.\n- **Expected observation:** The refund goes to the card.\n")
REPORTS = {"BK-02": "An order came in at 19:30 last night and went through. We close at six.",
           "BK-03": {"report": "Last year's orders are gone from the list."},
           "BK-07": "A refund went to cash instead of the card it was paid with."}


def verdicts(**by_probe):
    return {"probes": {p.replace("_", "-"): {"verdict": v.replace("_", " ")} for p, v in by_probe.items()}}


class Fixture(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.seed = self.root / "seed"
        (self.seed / "hidden").mkdir(parents=True)
        (self.seed / "brief.md").write_text(BRIEF)
        (self.seed / "hidden" / "oracle.md").write_text(ORACLE)
        (self.seed / "hidden" / "probes.md").write_text(MORE_PROBES)
        (self.seed / "hidden" / "owner-items.json").write_text(json.dumps(OWNER_ITEMS))
        symptom = "## Change 5" + SYMPTOM_SCRIPT.split("## Change 5", 1)[1].split("## Probe request", 1)[0]
        (self.seed / "hidden" / "change-script.md").write_text(GROWTH_SCRIPT + "\n" + symptom)
        (self.seed / "hidden" / "repair-reports.json").write_text(json.dumps(REPORTS))
        self.runs = self.root / "runs"
        self.base = self.runs / "g-bare-1"
        self.base.mkdir(parents=True)
        changes = {str(n): {"commit": f"c-after-{n}", "agent_cost_usd": 1.0, "owner_cost_usd": 0.2} for n in range(1, 6)}
        changes["5"]["symptom"] = "not fired: diagnostic passed"
        (self.base / "trajectory.json").write_text(json.dumps({
            "id": "g-bare-1", "arm": "bare", "seed": "seed", "model": "m", "effort": "medium", "policy": "bounded",
            "owner_model": "o", "replicate": "g-r1", "isolation": {"window": "1m"}, "round_cap": 6,
            "volumes": {"workspace": "ce-g-bare-1-ws", "config": "ce-g-bare-1-cfg"}, "changes": changes}))
        for n in (2, 5):
            (self.base / f"owner-state-{n:02d}.json").write_text(json.dumps(
                {**EMPTY_STATE, "disclosed": ["BK-02"], "requests": [[k, f"request {k}"] for k in range(1, min(n, 4) + 1)]}))
        self.grading(self.base / "grading" / "change-02", verdicts(P_BK01_a="met", P_BK02_a="not_met", P_BK03_a="not_met"))

    def grading(self, d: Path, data: dict) -> None:
        d.mkdir(parents=True, exist_ok=True)
        (d / "verdicts.json").write_text(json.dumps(data))

    def fork(self, at, item, *texts):
        docker, ws = [], FakeWorkspace()
        turns = FakeTurns(ws, *[(t, None, ["src/app.py"]) for t in texts])
        ask = FakeAsk(*[out("completion") for _ in texts])
        deps = rcf.Deps(docker=lambda cmd, **kw: docker.append(cmd) or subprocess_ok(cmd), turn_for=lambda s: turns,
                        workspace_for=lambda image, vol: ws, ask=ask, touch=ask.touch, trim=None)
        argv = ["run", "--id", "g-bare-1", "--at", str(at), "--item", item, "--runs", str(self.runs),
                "--seed-dir", str(self.seed)]
        with contextlib.redirect_stdout(io.StringIO()):
            rc = rrf.main(argv, deps=deps)
        return rc, docker, turns, argv, deps, ask


class MissesTest(Fixture):
    def test_the_latent_items_a_checkpoints_grading_has_as_not_met(self):
        self.assertEqual(rrf.misses(self.runs, self.seed, "g-bare-1", 2), ["BK-02", "BK-03"])
        # a stated item isn't latent; a latent one the grader couldn't exercise isn't a miss
        self.grading(self.base / "grading" / "change-02",
                     verdicts(P_BK01_a="not_met", P_BK02_a="couldn't_exercise", P_BK03_a="not_met"))
        self.assertEqual(rrf.misses(self.runs, self.seed, "g-bare-1", 2), ["BK-03"])
        self.assertIsNone(rrf.misses(self.runs, self.seed, "g-bare-1", 4))  # not graded there

    def test_a_report_is_the_items_text_or_its_report_field(self):
        reports = rrf.load_reports(self.seed)
        self.assertEqual(rrf.report_for(reports, "BK-02"), REPORTS["BK-02"])
        self.assertEqual(rrf.report_for(reports, "BK-03"), REPORTS["BK-03"]["report"])
        self.assertIsNone(rrf.report_for(reports, "BK-06"))
        (self.seed / "hidden" / "repair-reports.json").unlink()
        self.assertEqual(rrf.load_reports(self.seed), {})  # the drafter hasn't written it yet

    def test_the_plan_lists_each_runs_checkpoint_and_missed_item(self):
        out_, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out_), contextlib.redirect_stderr(err):
            rc = rrf.main(["plan", "--ids", "g-bare-1", "g-lid-full-1", "--checkpoints", "2", "4", "--runs", str(self.runs),
                           "--seed-dir", str(self.seed)])
        self.assertEqual(rc, 0)
        self.assertEqual(out_.getvalue().split("\n"), ["g-bare-1 2 BK-02", "g-bare-1 2 BK-03", ""])
        (self.seed / "hidden" / "repair-reports.json").write_text(json.dumps({"BK-02": "late order"}))
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            rrf.main(["plan", "--ids", "g-bare-1", "--checkpoints", "2", "--runs", str(self.runs), "--seed-dir", str(self.seed)])
        self.assertIn("no repair report for BK-03", err.getvalue())  # listed still; its fork stops until the report exists


class RepairForkTest(Fixture):
    def test_a_repair_fork_runs_the_report_from_the_checkpoints_snapshot_with_the_trajectorys_owner(self):
        rc, docker, turns, argv, deps, ask = self.fork(2, "BK-02", "Fixed: orders after six are refused.")
        self.assertEqual(rc, 0)
        fork = self.base / "repair-forks" / "c02-BK-02"
        meta = json.loads((fork / "trajectory.json").read_text())
        self.assertEqual((meta["kind"], meta["fork_of"], meta["item"], meta["at"], meta["change"]),
                         ("repair", "g-bare-1", "BK-02", 2, 2))
        self.assertEqual(meta["commit"], "c-after-2")  # the checkpoint's own snapshot
        self.assertIn("c-after-2", " ".join(docker[0]))
        self.assertEqual(list(meta["changes"]), ["repair"])
        self.assertEqual(meta["replicate"], "g-r1-repair02-bk-02-fork-1")
        # a fresh session opened by the report, with the neutral sentence every change's prompt ends with
        from costeval import trajectory as tj
        self.assertEqual(turns.calls[0]["prompt"], f"{REPORTS['BK-02']}\n\n{tj.NEUTRAL_SENTENCE}")
        self.assertIsNone(turns.calls[0]["resume"])
        self.assertIn("BK-02", rcf.LAST_OWNER.disclosed)  # the trajectory's owner as it stood at the checkpoint
        self.assertTrue((fork / "change-repair" / "change.json").exists())
        rot = json.loads((fork / "rot-cost.json").read_text())  # cost, turns, model calls, time, files read
        self.assertEqual((rot["kind"], rot["turns"]), ("repair", 1))
        rc, docker, *_ = self.fork(2, "BK-02", "again")
        self.assertEqual((rc, docker), (0, []))  # recorded: left alone

    def test_no_report_no_fork(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc, docker, *_ = self.fork(2, "BK-06", "x")
        self.assertEqual((rc, docker), (2, []))
        self.assertFalse((self.base / "repair-forks").exists())

    def test_a_symptom_items_report_brings_the_item_to_the_owner_whose_diagnostic_had_passed(self):
        # BK-07 is realized on change 5's symptom, which never fired on this trajectory; the repair report is that symptom
        self.grading(self.base / "grading" / "change-05", verdicts(P_BK01_a="met", P_BK07_a="not_met"))
        rc, *_ = self.fork(5, "BK-07", "Fixed: refunds go to the card.")
        self.assertEqual(rc, 0)
        self.assertIn("BK-07", rcf.LAST_OWNER.realized)


class CaptureTest(Fixture):
    """Every kind of fork commits what the agent left in the working tree as its change's commit, as the main line's
    changes do; the fork's own "commit" is the snapshot it started from."""

    def deps(self):
        ws = FakeWorkspace()
        turns = FakeTurns(ws, ("Done: the code is changed. I haven't committed anything.", None, ["src/app.py"]))
        ask = FakeAsk(out("completion"))
        return ws, rcf.Deps(docker=lambda cmd, **kw: subprocess_ok(cmd), turn_for=lambda s: turns,
                            workspace_for=lambda image, vol: ws, ask=ask, touch=ask.touch, trim=None)

    def test_course_reliance_and_repair_forks_each_record_the_harness_commit_of_the_working_tree(self):
        for n in (1, 4):
            (self.base / f"owner-state-{n:02d}.json").write_text(json.dumps(EMPTY_STATE))
        common = ["--id", "g-bare-1", "--runs", str(self.runs), "--seed-dir", str(self.seed)]
        cases = [(rcf.main, ["--kind", "course", "--course", "2", "--fork", "1"], "course-forks/c02-course-1", "2", "c-after-1"),
                 (rcf.main, ["--kind", "reliance", "--course", "2", "--fork", "1"], "course-forks/c02-reliance-1", "reliance",
                  "c-after-4"),
                 (lambda argv, deps: rrf.main(["run", *argv], deps=deps), ["--at", "2", "--item", "BK-02"],
                  "repair-forks/c02-BK-02", "repair", "c-after-2")]
        for main, extra, where, key, start in cases:
            ws, deps = self.deps()
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main([*common, *extra], deps=deps), 0, where)
            meta = json.loads((self.base / where / "trajectory.json").read_text())
            self.assertEqual((meta["commit"], meta["changes"][key]["commit"]), (start, "c1"), where)  # FakeWorkspace's commit
            self.assertEqual(len(ws.commits), 1, where)
            self.assertIn("committed by the harness", ws.commits[0])


class GradeTest(Fixture):
    def setUp(self):
        super().setUp()
        self.fork(2, "BK-02", "Fixed: orders after six are refused.")
        self.fid = "g-bare-1/repair-forks/c02-BK-02"
        self.where = self.runs / self.fid / "grading" / "repair"
        self.cmds = []

    def grade(self, data):
        def run(cmd):
            self.cmds.append(cmd)
            if "grade_checkpoint.py" in cmd[1]:  # what grade_checkpoint.py records: the commit it graded, with the verdicts
                self.grading(self.where, data if "error" in data else {**data, "commit": cmd[cmd.index("--commit") + 1]})
            return 0
        with contextlib.redirect_stdout(io.StringIO()):
            return rrf.main(["grade", "--id", "g-bare-1", "--at", "2", "--item", "BK-02", "--runs", str(self.runs),
                             "--seed-dir", str(self.seed)], run=run)

    def test_the_fork_is_regraded_in_full_for_the_fix_and_for_keeping(self):
        rc = self.grade(verdicts(P_BK01_a="not_met", P_BK02_a="met", P_BK03_a="not_met"))
        self.assertEqual(rc, 0)
        g = " ".join(next(c for c in self.cmds if "grade_checkpoint.py" in c[1]))
        commit = json.loads((self.runs / self.fid / "trajectory.json").read_text())["changes"]["repair"]["commit"]
        for part in (f"--id {self.fid} ", "--change 2 ", "--seed seed", f"--commit {commit}", "--out-name repair"):
            self.assertIn(part, g)
        self.assertNotIn("--probes", g)  # every probe in force at the checkpoint: a full regrade
        rec = json.loads((self.runs / self.fid / "repair.json").read_text())
        self.assertEqual((rec["item"], rec["at"], rec["kind"], rec["fixed"], rec["regrade"]), ("BK-02", 2, "askable", True, "full"))
        self.assertEqual(rec["keeping"], {"met_before": 1, "held": 0, "broken": ["BK-01"], "undetermined": []})
        self.assertEqual((rec["start_commit"], rec["commit"]), ("c-after-2", commit))  # graded: the change's own commit
        self.assertEqual(rec["measures"]["kind"], "repair")
        self.assertTrue(any(c[:3] == ["docker", "volume", "rm"] and "ce-g-bare-1-repair02-bk-02-1-ws" in c for c in self.cmds))
        self.assertEqual(rec["graded_commit"], commit)

    def test_an_unfixed_item_and_a_kept_build(self):
        self.grade(verdicts(P_BK01_a="met", P_BK02_a="not_met", P_BK03_a="not_met"))
        rec = json.loads((self.runs / self.fid / "repair.json").read_text())
        self.assertEqual((rec["fixed"], rec["keeping"]["broken"], rec["keeping"]["held"]), (False, [], 1))

    def test_a_grading_that_failed_records_nothing_and_runs_again(self):
        self.assertEqual(self.grade({"error": "extraction failed"}), 1)
        self.assertFalse((self.runs / self.fid / "repair.json").exists())
        self.assertFalse(any(c[:3] == ["docker", "volume", "rm"] for c in self.cmds))  # the fork is kept for the rerun

    def test_pending_until_the_repair_is_graded(self):
        import pending
        args = ["repair", "--id", "g-bare-1", "--at", "2", "--item", "BK-02", "--runs", str(self.runs)]
        self.assertEqual(pending.main(args), 0)
        self.grade(verdicts(P_BK01_a="met", P_BK02_a="met", P_BK03_a="not_met"))
        self.assertEqual(pending.main(args), 1)

    def test_grading_finds_the_repair_forks_build_and_its_parents_earlier_ones(self):
        commit = json.loads((self.runs / self.fid / "trajectory.json").read_text())["changes"]["repair"]["commit"]
        self.assertEqual(prior.lineage_owner(self.runs, self.fid, 2), (self.fid, commit))
        self.assertEqual(prior.lineage_owner(self.runs, self.fid, 1), ("g-bare-1", "c-after-1"))


if __name__ == "__main__":
    unittest.main()
