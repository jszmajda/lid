"""run_clowder_pilot.sh, dry: the forks and gradings each phase would run, and what a resumed run skips."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent


def dry(*args: str, runs: Path) -> tuple[int, list[str]]:
    env = {**os.environ, "DRY": "1", "RUNS": str(runs), "PY": sys.executable, "JOBS": "1"}
    p = subprocess.run(["sh", "run_clowder_pilot.sh", *args], cwd=HARNESS, env=env, capture_output=True, text=True)
    return p.returncode, [l for l in p.stdout.splitlines() if "run_fork.py" in l or "grade_rust.py" in l or l.startswith("mv ")]


def record(runs: Path, fid: str, change: int, *, done: bool, graded: bool = False) -> None:
    d = runs / fid
    d.mkdir(parents=True)
    (d / "trajectory.json").write_text(json.dumps({"id": fid, "changes": {str(change): {"commit": "c1"}} if done else {}}))
    if graded:
        g = d / "grading" / f"change-{change:02d}"
        g.mkdir(parents=True)
        (g / "summary.json").write_text("{}")


class PilotRunnerTest(unittest.TestCase):
    def setUp(self):
        self.runs = Path(tempfile.mkdtemp())

    def test_phase1_is_the_ceiling_check_each_fork_graded_right_after_it(self):
        rc, cmds = dry("phase1", runs=self.runs)
        self.assertEqual(rc, 0)
        self.assertEqual(len(cmds), 24)
        for n in range(1, 13):
            fork, grade = cmds[2 * (n - 1)], cmds[2 * (n - 1) + 1]
            fid = f"cf-stripped-bare-1m-c{n:02d}-r1"
            for part in ("run_fork.py", "--variant stripped", "--arm bare", f"--change {n} ", "--window 1m",
                         "--replicate cp-r1", "--repeat 1", f"clowder-pilot/{fid}.fork.log"):
                self.assertIn(part, fork)
            self.assertIn(f"grade_rust.py --id {fid}", grade)
            self.assertIn(f"clowder-pilot/{fid}.grade.log", grade)

    def test_phase2_runs_three_arms_at_both_windows_and_a_resumed_run_skips_what_is_done(self):
        record(self.runs, "cf-full-lid-full-200k-c03-r1", 3, done=True, graded=True)   # done: nothing to run
        record(self.runs, "cf-full-bare-1m-c04-r1", 4, done=True)                     # forked, not graded
        record(self.runs, "cf-stripped-bare-200k-c05-r1", 5, done=False)             # stopped partway
        rc, cmds = dry("phase2", runs=self.runs)
        self.assertEqual(rc, 0)
        forks = [c for c in cmds if "run_fork.py" in c]
        grades = [c for c in cmds if "grade_rust.py" in c]
        self.assertEqual((len(forks), len(grades)), (70, 71))
        self.assertEqual({tuple(p for p in ("--variant full", "--variant stripped", "--arm bare", "--arm lid-full")
                                if p in c) for c in forks},
                         {("--variant stripped", "--arm bare"), ("--variant full", "--arm bare"),
                          ("--variant full", "--arm lid-full")})
        self.assertFalse(any("cf-full-lid-full-200k-c03-r1" in c for c in cmds))
        self.assertTrue(any("grade_rust.py --id cf-full-bare-1m-c04-r1" in c for c in grades))
        self.assertFalse(any("--variant full --arm bare --change 4 --repeat 1 --replicate cp-r1 --window 1m" in c for c in forks))
        moved = [c for c in cmds if c.startswith("mv ")]
        self.assertEqual(len(moved), 1)
        self.assertIn("cf-stripped-bare-200k-c05-r1.stopped-", moved[0])
        self.assertTrue(all("--replicate cp-r1" in c for c in forks))

    def test_phase0_rechecks_the_changes_given_with_the_null_arm(self):
        rc, cmds = dry("phase0", "1,12", runs=self.runs)
        self.assertEqual(rc, 0)
        forks = [c for c in cmds if "run_fork.py" in c]
        self.assertEqual(len(forks), 2)
        self.assertTrue(all("--null" in c and "--variant stripped" in c and "--arm" not in c for c in forks))
        self.assertTrue(any("grade_rust.py --id cf-stripped-null-200k-c01-r2" in c for c in cmds))
        self.assertTrue(any("grade_rust.py --id cf-stripped-null-200k-c12-r2" in c for c in cmds))
        rc, cmds = dry("phase0", "1", "3", runs=self.runs)
        self.assertTrue(any("cf-stripped-null-200k-c01-r3" in c for c in cmds))

    def test_usage(self):
        rc, _ = dry("phase9", runs=self.runs)
        self.assertNotEqual(rc, 0)
        rc, _ = dry("phase0", runs=self.runs)  # the changes are required
        self.assertNotEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
