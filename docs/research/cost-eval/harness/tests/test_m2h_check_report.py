"""m2h_check.py (the null and right checks) and m2h_report.py (the joint-outcome report), on synthetic gradings in
grade_node.py's summary shape."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import m2h_check as chk  # noqa: E402
import m2h_report as rep  # noqa: E402

KEPT = {"1": {"title": "Pair one watch", "searchability": {"tier": "hidden", "pooled_with_and_without": False},
              "new_rows": {"stated": ["OGM-0101"], "askable": ["OGM-0102"], "guard": []}},
        "3": {"title": "Rest on the watch", "searchability": {"tier": "documented", "pooled_with_and_without": True},
              "new_rows": {"stated": ["OGM-0301"], "askable": [], "guard": ["OGM-0303"]}},
        "9": {"title": "Join codes", "searchability": {"tier": "one-step grep", "pooled_with_and_without": False},
              "new_rows": {"stated": ["OGM-0901"], "askable": [], "guard": []}}}
GUARDS = {"rows": {"OGM-0303": {"change": 3, "checkable_on_snapshot": True},
                   "OGM-0403": {"change": 4, "checkable_on_snapshot": False}}}


def write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


def fork(runs: Path, fid: str, n: int, *, arm="bare", items, dep, implemented=None, cost=1.0, rounds=3, tier=None,
         faults=None):
    write(runs / fid / "trajectory.json", {"id": fid, "arm": arm, "change": n, "repeat": 1,
                                           "changes": {str(n): {"commit": "c", "agent_cost_usd": cost, "rounds": rounds,
                                                                "minutes": 2.0}}})
    write(runs / fid / "grading" / f"change-{n:02d}" / "summary.json", {
        "items": items, "dependency": {"result": dep}, "missing_by_fault": faults or {},
        "joint": {"implemented": implemented, "dependent_behaviour": dep, "tier": tier}})


class Base(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.runs, self.files = self.root / "runs", self.root / "m2h"
        write(self.files / "kept-behaviour.json", KEPT)
        write(self.files / "guard-rows.json", GUARDS)


class CheckTest(Base):
    def check(self, mode, forks):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = chk.main(["--mode", mode, "--runs", str(self.runs), "--forks", forks, "--seed-files", str(self.files)])
        return rc, out.getvalue(), json.loads((self.runs / "opengym-m2h" / f"{mode}-check.json").read_text())

    def test_on_an_untouched_start_no_dependency_is_exercised_no_new_row_is_met_and_guards_are_met(self):
        fork(self.runs, "m2h-null-bare-c01", 1, arm="null", items={"OGM-0101": "not met", "OGM-0102": "not exercised"},
             dep="not exercised")
        fork(self.runs, "m2h-null-lid-r1-c03", 3, arm="null", items={"OGM-0301": "not met", "OGM-0303": "met"},
             dep="not exercised")
        rc, text, rec = self.check("null", "m2h-null-*")
        self.assertEqual((rc, rec["problems"]), (0, []))
        self.assertIn("| m2h-null-lid-r1-c03 | 3 | lid-r1 | 0 of 1 | 1 of 1 | not exercised | ok |", text)

    def test_on_an_untouched_start_an_exercised_dependency_or_a_met_new_row_is_a_problem(self):
        fork(self.runs, "m2h-null-bare-c01", 1, arm="null", items={"OGM-0101": "met", "OGM-0102": "not met"}, dep="kept",
             faults={"observation": 1})
        rc, text, rec = self.check("null", "m2h-null-*")
        self.assertEqual(rc, 1)
        whats = sorted(p["what"] for p in rec["problems"])
        self.assertEqual(whats, ["OGM-0101 met on the untouched start", "the dependency kept on the untouched start"])
        self.assertIn("grader faults {'observation': 1}", text)

    def test_on_a_right_build_every_row_is_met_and_the_dependency_kept(self):
        fork(self.runs, "m2h-right-c01", 1, arm="null", items={"OGM-0101": "met", "OGM-0102": "met"}, dep="kept")
        fork(self.runs, "m2h-right-c03", 3, arm="null", items={"OGM-0301": "met", "OGM-0303": "not met"}, dep="broken")
        rc, text, rec = self.check("right", "m2h-right-c*")
        self.assertEqual(rc, 1)
        self.assertEqual(sorted(p["what"] for p in rec["problems"]),
                         ["OGM-0303 (guard) not met on the right build", "the dependency broken on the right build"])


class ReportTest(Base):
    def report(self):
        out = self.root / "m2h.md"
        with contextlib.redirect_stdout(io.StringIO()):
            rc = rep.main(["--runs", str(self.runs), "--forks", "m2h-*-r[0-9]", "--seed-files", str(self.files),
                           "--out", str(out)])
        return rc, out.read_text(), json.loads(out.with_suffix(".json").read_text())

    def test_the_joint_outcome_per_fork_change_arm_and_tier_with_breakage_among_implemented(self):
        for k, (imp, dep) in enumerate((("yes", "kept"), ("yes", "broken"), ("partly", "not exercised")), 1):
            fork(self.runs, f"m2h-bare-c01-r{k}", 1, items={}, dep=dep, implemented=imp, cost=1.0 * k, tier="hidden")
        for k, (imp, dep) in enumerate((("yes", "kept"), ("yes", "kept"), ("no", "not exercised")), 1):
            fork(self.runs, f"m2h-lid-c01-r{k}", 1, arm="lid-full-arrows", items={}, dep=dep, implemented=imp, tier="hidden")
        fork(self.runs, "m2h-bare-c03-r1", 3, items={}, dep="broken", implemented="yes", tier="documented")
        fork(self.runs, "m2h-null-bare-c01", 1, arm="null", items={}, dep="not exercised")  # never in the report
        fork(self.runs, "m2h-bare-c01-r1-fix-DEP-01", 1, items={}, dep="kept", implemented="yes")  # nor a repair
        rc, text, rec = self.report()
        self.assertEqual(rc, 0)
        bare, lid = rec["arms"]["bare"], rec["arms"]["lid"]
        self.assertEqual(bare["joint"]["yes"]["kept"], 1)
        self.assertEqual(bare["joint"]["yes"]["broken"], 2)  # changes 1 and 3
        self.assertEqual(bare["breakage_among_implemented"], [2, 3])  # broken / (kept + broken), implemented: yes
        self.assertEqual(lid["breakage_among_implemented"], [0, 2])
        self.assertEqual(bare["by_tier"]["hidden"]["breakage_among_implemented"], [1, 2])
        # documented, with and without the changes reported both ways (3 here)
        self.assertEqual(bare["by_tier"]["documented"]["breakage_among_implemented"], [1, 1])
        self.assertEqual(bare["by_tier"]["documented (without 3)"]["breakage_among_implemented"], [0, 0])
        self.assertEqual(rec["forks"][0]["id"], "m2h-bare-c01-r1")
        self.assertEqual(len(rec["forks"]), 7)
        self.assertIn("## Joint outcome, pooled", text)
        self.assertIn("| bare | 2/3 |", text)  # breakage among implemented forks
        self.assertIn("never counted as kept", text)
        self.assertIn("| m2h-bare-c01-r3 | bare | 1 | 3 | hidden | partly | not exercised |", text)


if __name__ == "__main__":
    unittest.main()
