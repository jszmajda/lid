"""run_opengym_m2h.sh, dry: the null and right checks, bare against LID Full from each replicate's map, and the repairs
it would queue (plan.md, M2h; m2h-harness-needs.md, "Phases")."""

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
CHANGES = list(range(1, 13))


def dry(*args: str, runs: Path, env: dict | None = None) -> list[str]:
    e = {**os.environ, "DRY": "1", "RUNS": str(runs), "PY": sys.executable, "JOBS": "1", **(env or {})}
    p = subprocess.run(["sh", "run_opengym_m2h.sh", *args], cwd=HARNESS, env=e, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return [line for line in p.stdout.splitlines() if ".py" in line or line.startswith("mv ")]


def ids(cmds: list[str], script: str) -> list[str]:
    return [re.search(r"--id (\S+)", c).group(1) for c in cmds if script in c]


class M2hRunnerTest(unittest.TestCase):
    def setUp(self):
        self.runs = Path(tempfile.mkdtemp())

    def test_main_is_bare_from_the_shared_start_against_lid_from_each_replicates_map(self):
        cmds = dry("main", runs=self.runs)
        forks = [c for c in cmds if "run_fork.py" in c]
        self.assertEqual(len(forks), 12 * 2 * 3)
        self.assertEqual(set(ids(cmds, "run_fork.py")), {f"m2h-{a}-c{n:02d}-r{k}" for a in ("bare", "lid") for n in CHANGES
                                                          for k in (1, 2, 3)})
        for c in forks:
            k = re.search(r"--repeat (\d)", c).group(1)
            self.assertIn(f"--replicate m2h-r{k} ", c)  # fork k of every change and both arms shares the owner's draws
            self.assertIn("--window 1m", c)
            self.assertIn("--policy bounded", c)
            self.assertIn("/opengym-m2h/starts.json", c)
            self.assertIn("/seeds/opengym/hidden/m2h/oracle.md", c)
            self.assertNotIn("--no-isolate", c)
            if "-bare-" in c:
                self.assertIn("--start bare --arm bare ", c)
            else:
                self.assertIn(f"--start lid-r{k} --arm lid-full-arrows ", c)  # the replicate's own map
        grades = [c for c in cmds if "grade_node.py" in c]
        self.assertEqual(set(ids(cmds, "grade_node.py")), set(ids(cmds, "run_fork.py")))
        self.assertTrue(all("--guard-rows" in c and "m2h-probes.md" in c for c in grades))

    def test_null_grades_the_bare_start_and_one_map_at_every_change_then_checks_it(self):
        cmds = dry("null", runs=self.runs)
        self.assertEqual(set(ids(cmds, "run_fork.py")),
                         {f"m2h-null-{s}-c{n:02d}" for s in ("bare", "lid-r1") for n in CHANGES})  # the maps change no code
        self.assertTrue(all("--null" in c for c in cmds if "run_fork.py" in c))
        self.assertIn("m2h_check.py", cmds[-1])
        self.assertIn("--mode null", cmds[-1])
        only_bare = dry("null", runs=self.runs, env={"NULL_STARTS": "bare"})  # still configurable
        self.assertEqual(len([c for c in only_bare if "run_fork.py" in c]), 12)

    def test_right_commits_each_right_build_after_the_bare_start_and_grades_it(self):
        cmds = dry("right", runs=self.runs)
        self.assertTrue(any("m2h_right_builds.py" in c and "--out" in c for c in cmds))
        forks = [c for c in cmds if "run_fork.py" in c]
        self.assertEqual(ids(cmds, "run_fork.py"), [f"m2h-right-c{n:02d}" for n in CHANGES])
        for c in forks:
            n = re.search(r"--change (\d+)", c).group(1)
            for part in ("--null", "--start bare ", "--result-patch ", f"/right/change-{int(n):02d}.diff"):
                self.assertIn(part, c)
        self.assertIn("--mode right", cmds[-1])

    def test_a_recorded_fork_is_not_run_again_and_one_stopped_partway_is_moved_aside(self):
        d = self.runs / "m2h-bare-c01-r1"
        (d / "grading" / "change-01").mkdir(parents=True)
        (d / "trajectory.json").write_text(json.dumps({"changes": {"1": {"commit": "c1"}}}))
        (d / "grading" / "change-01" / "summary.json").write_text("{}")
        e = self.runs / "m2h-lid-c01-r1"
        e.mkdir()
        (e / "trajectory.json").write_text(json.dumps({"changes": {}}))
        cmds = dry("main", runs=self.runs)
        self.assertEqual([c for c in cmds if "m2h-bare-c01-r1" in c and "release" not in c], [])  # only its release
        self.assertTrue(any(c.startswith("mv ") and "m2h-lid-c01-r1" in c for c in cmds))

    def test_repairs_queue_a_repair_for_each_miss_then_release(self):
        d = self.runs / "m2h-lid-c01-r1"
        (d / "grading" / "change-01").mkdir(parents=True)
        (d / "trajectory.json").write_text(json.dumps({"arm": "lid-full-arrows", "change": 1,
                                                       "changes": {"1": {"commit": "c1"}}}))
        (d / "grading" / "change-01" / "summary.json").write_text(json.dumps(
            {"items": {"OGM-0101": "met", "OGM-0102": "not met"}, "dependency_met": False}))
        cmds = dry("repairs", runs=self.runs)
        runs_ = [c for c in cmds if "run_clowder_repairs.py run" in c]
        self.assertEqual(sorted(re.search(r"--item (\S+)", c).group(1) for c in runs_), ["DEP-01", "OGM-0102"])
        self.assertEqual(set(ids(cmds, "grade_node.py")), {"m2h-lid-c01-r1-fix-OGM-0102", "m2h-lid-c01-r1-fix-DEP-01"})
        self.assertIn("run_clowder_repairs.py release", cmds[-1])

    def test_report_writes_the_joint_outcome(self):
        cmds = dry("report", runs=self.runs)
        self.assertTrue(any("m2h_report.py" in c for c in cmds))

    def test_with_no_python312_on_path_the_runners_use_the_uv_interpreter(self):
        # a fresh shell has no python3.12 on PATH; PY defaults to uv's, so the queued commands still run
        uv = str(Path.home() / ".local/share/uv/python/cpython-3.12-macos-aarch64-none/bin/python3.12")
        for script, phase in (("run_opengym_m2h.sh", "main"), ("run_clowder_m2f.sh", "main"), ("run_growth.sh", "trial"),
                              ("run_clowder_pilot.sh", "phase1")):
            env = {k: v for k, v in os.environ.items() if k != "PY"}
            env.update({"DRY": "1", "RUNS": str(self.runs), "JOBS": "1", "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"})
            p = subprocess.run(["sh", script, phase], cwd=HARNESS, env=env, capture_output=True, text=True)
            first = next((line for line in p.stdout.splitlines() if ".py " in line), "")
            self.assertTrue(first.startswith(uv) or f" {uv} " in first or first.startswith(f"if {uv} "), (script, first[:120]))

    def test_every_job_waits_at_the_pacing_gate_when_live(self):
        self.assertIn("sh pace.sh", (HARNESS / "run_opengym_m2h.sh").read_text())

    def test_every_fork_waits_at_the_disk_gate_when_live(self):
        text = (HARNESS / "run_opengym_m2h.sh").read_text()
        self.assertIn("sh disk_gate.sh", text.split("disk() {", 1)[1].split("\n}\n", 1)[0])
        body = text.split("fork_and_grade() {", 1)[1].split("\n}\n", 1)[0]
        self.assertLess(body.index("disk && pace"), body.index("run_fork.py"))
        repair = text.split("repair_one() {", 1)[1].split("\n}\n", 1)[0]
        self.assertLess(repair.index("disk && pace"), repair.index("run_clowder_repairs.py run"))

    def test_a_fork_with_no_miss_to_repair_releases_its_volumes_right_after_grading(self):
        cmds = dry("main", runs=self.runs)
        for fid in ("m2h-bare-c01-r1", "m2h-lid-c12-r3"):
            grade = next(i for i, c in enumerate(cmds) if "grade_node.py" in c and f"--id {fid} " in c)
            self.assertIn(f"run_clowder_repairs.py release --forks '{fid}'", cmds[grade + 1])
        null = dry("null", runs=self.runs)
        self.assertTrue(any("run_clowder_repairs.py release --forks 'm2h-null-bare-c01'" in c for c in null))

    def test_each_release_is_followed_by_a_trim_so_the_mac_gets_the_space_back(self):
        text = (HARNESS / "run_opengym_m2h.sh").read_text()
        body = text.split("release() {", 1)[1].split("\n}\n", 1)[0]
        self.assertLess(body.index("run_clowder_repairs.py release"), body.index("trim.sh"))
        repairs = text.split("repairs() {", 1)[1].split("\n}\n", 1)[0]
        self.assertLess(repairs.index("run_clowder_repairs.py release"), repairs.index("trim.sh"))
        m2f = (HARNESS / "run_clowder_m2f.sh").read_text().split("repairs() {", 1)[1].split("\n}\n", 1)[0]
        self.assertLess(m2f.index("run_clowder_repairs.py release"), m2f.index("trim.sh"))


if __name__ == "__main__":
    unittest.main()
