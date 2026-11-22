"""run_clowder_m2f.sh, dry: the variants, the null-arm check, the stripped-against-LID forks, the renaming dose and
the repairs it would queue (plan.md, M2f)."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
CHANGES = list(range(13, 25))


def dry(*args: str, runs: Path) -> list[str]:
    env = {**os.environ, "DRY": "1", "RUNS": str(runs), "PY": sys.executable, "JOBS": "1"}
    p = subprocess.run(["sh", "run_clowder_m2f.sh", *args], cwd=HARNESS, env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return [line for line in p.stdout.splitlines() if ".py" in line or line.startswith("mv ")]


def ids(cmds: list[str], script: str) -> list[str]:
    return [re.search(r"--id (\S+)", c).group(1) for c in cmds if script in c]


class M2fRunnerTest(unittest.TestCase):
    def setUp(self):
        self.runs = Path(tempfile.mkdtemp())

    def test_main_is_stripped_bare_against_lid_full_three_forks_a_change_at_1m_each_graded_after_it(self):
        cmds = dry("main", runs=self.runs)
        forks = [c for c in cmds if "run_fork.py" in c]
        self.assertEqual(len(forks), 12 * 2 * 3)
        expected = {f"m2f-{v}-{a}-c{n:02d}-r{k}" for v, a in (("stripped", "bare"), ("full", "lid-full"))
                    for n in CHANGES for k in (1, 2, 3)}
        self.assertEqual(set(ids(cmds, "run_fork.py")), expected)
        for c in forks:
            for part in ("/clowder-variants/v2 ", "--window 1m",
                         "--policy bounded", "/m2f/oracle.md", "/m2f/change-script.md", "/m2f/owner-items.json"):
                self.assertIn(part, c)
            self.assertNotIn("--no-isolate", c)  # isolated, as every fork is by default
            k = re.search(r"--repeat (\d)", c).group(1)
            self.assertIn(f"--replicate m2f-r{k} ", c)  # repeat k's owner draws are shared by the two arms
        self.assertIn("--variant stripped --arm bare", " ".join(forks))
        self.assertIn("--variant full --arm lid-full", " ".join(forks))
        grades = [c for c in cmds if "grade_rust.py" in c]
        self.assertEqual(set(ids(cmds, "grade_rust.py")), expected)
        self.assertTrue(all("/m2f/oracle.md" in c and "/m2f-probes.md" in c for c in grades))
        self.assertLess(cmds.index(next(c for c in cmds if "m2f-stripped-bare-c13-r1" in c and "run_fork" in c)),
                        cmds.index(next(c for c in cmds if "m2f-stripped-bare-c13-r1" in c and "grade_rust" in c)))

    def test_every_job_waits_at_the_pacing_gate_when_live(self):
        text = (HARNESS / "run_clowder_m2f.sh").read_text()
        self.assertIn("sh pace.sh", text)

    def test_the_dose_runs_changes_14_15_and_19_on_the_renamed_variants(self):
        cmds = dry("dose", runs=self.runs)
        expected = {f"m2f-dose-{v}-{a}-c{n:02d}-r{k}" for v, a in (("stripped", "bare"), ("full", "lid-full"))
                    for n in (14, 15, 19) for k in (1, 2, 3)}
        self.assertEqual(set(ids(cmds, "run_fork.py")), expected)
        self.assertTrue(all("/clowder-variants/v2-dose " in c for c in cmds if "run_fork.py" in c))

    def test_null_grades_the_untouched_snapshot_at_each_change_then_checks_it(self):
        cmds = dry("null", runs=self.runs)
        self.assertEqual(ids(cmds, "run_fork.py"), [f"m2f-null-c{n:02d}" for n in CHANGES])
        self.assertTrue(all("--null" in c and "--variant full" in c for c in cmds if "run_fork.py" in c))
        self.assertEqual(ids(cmds, "grade_rust.py"), [f"m2f-null-c{n:02d}" for n in CHANGES])
        self.assertIn("m2f_null_check.py", cmds[-1])

    def test_a_recorded_fork_is_not_run_again_and_one_stopped_partway_is_moved_aside(self):
        d = self.runs / "m2f-stripped-bare-c13-r1"
        d.mkdir(parents=True)
        (d / "trajectory.json").write_text(json.dumps({"changes": {"13": {"commit": "c1"}}}))
        (d / "grading" / "change-13").mkdir(parents=True)
        (d / "grading" / "change-13" / "summary.json").write_text("{}")
        e = self.runs / "m2f-full-lid-full-c13-r1"
        e.mkdir()
        (e / "trajectory.json").write_text(json.dumps({"changes": {}}))
        cmds = dry("main", runs=self.runs)
        self.assertNotIn("m2f-stripped-bare-c13-r1", " ".join(cmds))
        self.assertTrue(any(c.startswith("mv ") and "m2f-full-lid-full-c13-r1" in c for c in cmds))

    def test_repairs_queue_a_repair_for_each_miss_then_grade_and_record_it_then_release(self):
        d = self.runs / "m2f-full-lid-full-c13-r1"
        (d / "grading" / "change-13").mkdir(parents=True)
        (d / "trajectory.json").write_text(json.dumps({"arm": "lid-full", "change": 13, "changes": {"13": {"commit": "c1"}}}))
        (d / "grading" / "change-13" / "summary.json").write_text(json.dumps(
            {"items": {"CLX-1301": "met", "CLX-1302": "not met"}, "dependency_met": False}))
        cmds = dry("repairs", runs=self.runs)
        runs_ = [c for c in cmds if "run_clowder_repairs.py run" in c]
        self.assertEqual(sorted(re.search(r"--item (\S+)", c).group(1) for c in runs_), ["CLX-1302", "DEP-13"])
        self.assertTrue(all("--of m2f-full-lid-full-c13-r1" in c for c in runs_))
        self.assertEqual(set(ids(cmds, "grade_rust.py")), {"m2f-full-lid-full-c13-r1-fix-CLX-1302",
                                                            "m2f-full-lid-full-c13-r1-fix-DEP-13"})
        self.assertEqual(len([c for c in cmds if "run_clowder_repairs.py record" in c]), 2)
        self.assertIn("run_clowder_repairs.py release", cmds[-1])

    def test_variants_builds_v2_and_the_dose_from_the_pilots_draw_with_the_holdouts_and_their_graded_targets(self):
        cmds = dry("variants", runs=self.runs)
        builds = [c for c in cmds if "clowder_variants.py" in c]
        self.assertEqual(len(builds), 2)
        for c in builds:
            for part in ("--commit 86db995", "--draw-seed v1", "--holdouts", "m2f-holdouts.json", "--volumes", "--cargo-test"):
                self.assertIn(part, c)
        self.assertIn("--seed v2 ", builds[0])
        self.assertIn("--seed v2-dose ", builds[1])
        self.assertIn("--renames", builds[1])
        self.assertNotIn("--renames", builds[0])
        self.assertEqual(len([c for c in cmds if "m2f_graded_targets.py" in c]), 2)


if __name__ == "__main__":
    unittest.main()
