"""run_growth.sh, dry: the trajectories, course-change forks, and checkpoints each phase would run."""

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
RELIANCE = """### Reliance request

**Lag:** {lag}  
**Setup:** S0  
**Scenario:** Export this week's releases.  
**Current-rule outcome:** Embargoed titles are left out.  
**Displaced-rule outcome:** Embargoed titles are listed.

> Can I get this week's releases as a file?
"""
SCRIPT = """# Change script

## Change 3 — Fees

### Owner request

> Add fees.

**Introduces:** RD-50.

## Change 11 — Drop fees

### Owner request

> Drop the fees.

**Introduces:** RD-51.  
**Retires:** RD-50.  
**Course change:** retirement of change 3 (distance 8)

""" + RELIANCE.format(lag=2) + """
## Change 25 — Bring fees back

### Owner request

> Fees again.

**Introduces:** RD-53.  
**Course change:** re-reversal of change 11 (distance 14)

""" + RELIANCE.format(lag=3)


def dry(*args: str, runs: str | None = None, files: dict | None = None) -> list[str]:
    seed = Path(tempfile.mkdtemp())
    (seed / "hidden").mkdir()
    (seed / "hidden" / "change-script.md").write_text(SCRIPT)
    (seed / "hidden" / "reference-builds.json").write_text(json.dumps(SPEC))
    for name, text in (files or {}).items():
        (seed / name).write_text(text)
    env = {**os.environ, "DRY": "1", "RUNS": runs or tempfile.mkdtemp(), "SEED_DIR": str(seed), "PY": sys.executable,
           "JOBS": "1"}
    p = subprocess.run(["sh", "run_growth.sh", *args], cwd=HARNESS, env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return [l for l in p.stdout.splitlines() if ".py" in l]


class GrowthRunnerTest(unittest.TestCase):
    def test_the_trial_is_bare_1_and_lid_1_through_change_20_in_batches_with_forks_and_two_checkpoints(self):
        cmds = dry("trial")
        trajs = [c for c in cmds if "run_trajectory.py" in c]
        self.assertEqual(len(trajs), 2)
        for c in trajs:
            for part in ("--seed releasedesk", "--replicate g-r1", "--policy bounded --owner-model-config central",
                         "--changes " + ",".join(str(n) for n in range(11)) + " ",
                         "--changes " + ",".join(str(n) for n in range(11, 21)) + " "):
                self.assertIn(part, c)
            self.assertEqual(c.count("sh pace.sh"), 2)  # the gate before each batch of changes with work left
            self.assertEqual(len(re.findall(r"if \S+ pending.py batch --id \S+ --changes [\d,]+; then sh pace.sh && ", c)), 2)
        self.assertEqual(sorted(re.search(r"--id (\S+)", c).group(1) for c in trajs), ["g-bare-1", "g-lid-full-1"])
        forks = [c for c in cmds if "run_course_forks.py" in c]
        self.assertTrue(all(re.match(r"if \S+ pending.py fork --id \S+ --kind \w+ --course \d+ --fork \d+; "
                                     r"then sh pace.sh && ", c) for c in forks))
        kinds = sorted(re.search(r"--kind (\w+) --course (\d+)", c).groups() for c in forks)
        # replicate 1 of each arm: three course forks of change 11, and three reliance forks of it (lag 2: after change 13)
        self.assertEqual(kinds, [("course", "11")] * 6 + [("reliance", "11")] * 6)
        checks = [c for c in cmds if "growth_checkpoint.py" in c]
        self.assertTrue(all(re.match(r"if \S+ pending.py checkpoint --id \S+ --change \d+; then sh pace.sh && ", c)
                            for c in checks))
        self.assertEqual(sorted(re.search(r"--id (\S+) --change (\d+)", c).groups() for c in checks),
                         [("g-bare-1", "10"), ("g-bare-1", "20"), ("g-lid-full-1", "10"), ("g-lid-full-1", "20")])
        self.assertLess(max(cmds.index(c) for c in trajs), min(cmds.index(c) for c in forks))  # trajectories first
        self.assertLess(max(cmds.index(c) for c in forks), min(cmds.index(c) for c in checks))  # forks before grading

    def test_the_full_run_is_fourteen_trajectories_through_change_40_sharing_seeds_by_replicate(self):
        cmds = dry("full")
        trajs = {re.search(r"--id (\S+)", c).group(1): c for c in cmds if "run_trajectory.py" in c}
        self.assertEqual(sorted(trajs), sorted([f"g-bare-{k}" for k in range(1, 6)] + ["g-bare-drift"]
                                               + [f"g-lid-full-{k}" for k in range(1, 6)] + [f"g-bare-one-line-{k}" for k in range(1, 4)]))
        self.assertIn("--replicate g-r1", trajs["g-bare-drift"])  # the drift floor shares bare-1's seed
        self.assertIn("--arm bare ", trajs["g-bare-drift"])
        self.assertIn("--replicate g-r3", trajs["g-bare-one-line-3"])
        self.assertIn("--arm bare-one-line", trajs["g-bare-one-line-3"])
        self.assertIn("--replicate g-r4", trajs["g-lid-full-4"])
        self.assertTrue(all(c.count("sh pace.sh") == 4 and "--changes " + ",".join(str(n) for n in range(31, 41)) + " " in c
                            for c in trajs.values()))
        forks = [c for c in cmds if "run_course_forks.py" in c]
        course = [c for c in forks if "--kind course" in c]
        reliance = [c for c in forks if "--kind reliance" in c]
        self.assertEqual(len(course), 3 * 2 * 3)  # each arm's first replicate: both course changes, three forks each
        # every trajectory one reliance fork per course change; each arm's first replicate two more
        self.assertEqual(len(reliance), 14 * 2 + 3 * 2 * 2)
        self.assertTrue(any("--id g-bare-drift --kind reliance" in c for c in reliance))
        self.assertFalse(any("--id g-bare-drift --kind course" in c for c in course))
        checks = [c for c in cmds if "growth_checkpoint.py" in c]
        self.assertEqual(len(checks), 14 * 4)


class M2eRunnerTest(unittest.TestCase):
    def test_m2e_is_the_checklist_arm_on_replicate_1_through_change_20_with_the_trials_forks_and_checkpoints(self):
        cmds = dry("m2e")
        trajs = [c for c in cmds if "run_trajectory.py" in c]
        self.assertEqual(len(trajs), 1)
        for part in ("--arm checklist", "--id g-checklist-1", "--replicate g-r1", "--policy bounded --owner-model-config central",
                     "--isolate", "--changes " + ",".join(str(n) for n in range(11)) + " ",
                     "--changes " + ",".join(str(n) for n in range(11, 21)) + " "):
            self.assertIn(part, trajs[0])
        self.assertEqual(trajs[0].count("sh pace.sh"), 2)
        forks = [c for c in cmds if "run_course_forks.py" in c]
        self.assertTrue(all("--id g-checklist-1 " in c and " --isolate" in c for c in forks))
        # as the trial's replicate 1: three course forks of each course change, and three reliance forks
        self.assertEqual(sorted(re.search(r"--kind (\w+) --course (\d+)", c).groups() for c in forks),
                         [("course", "11")] * 3 + [("reliance", "11")] * 3)
        checks = [c for c in cmds if "growth_checkpoint.py" in c]
        self.assertEqual(sorted(re.search(r"--id (\S+) --change (\d+)", c).groups() for c in checks),
                         [("g-checklist-1", "10"), ("g-checklist-1", "20")])
        self.assertTrue(all("growth_checkpoint.py --id g-checklist-1 --change" in c and "--steps" not in c for c in checks))


class RepairRunnerTest(unittest.TestCase):
    def test_repairs_queue_one_fork_per_latent_miss_of_each_runs_checkpoints_paced_isolated_then_graded(self):
        from test_grading import PROBES
        from test_simulator import ORACLE
        runs = Path(tempfile.mkdtemp())
        for tid, c, verdicts in (("g-bare-1", 10, {"P-BK01-a": "met", "P-BK02-a": "not met"}),
                                 ("g-bare-1", 20, {"P-BK01-a": "not met", "P-BK02-a": "not met"}),  # BK-01 is stated
                                 ("g-lid-full-1", 10, {"P-BK01-a": "met", "P-BK02-a": "met"}),
                                 ("g-checklist-1", 20, {"P-BK01-a": "met", "P-BK02-a": "not met"})):
            g = runs / tid / "grading" / f"change-{c:02d}"
            g.mkdir(parents=True)
            (g / "verdicts.json").write_text(json.dumps({"probes": {p: {"verdict": v} for p, v in verdicts.items()}}))
        cmds = dry("repairs", runs=str(runs), files={"hidden/oracle.md": ORACLE, "hidden/probes.md": PROBES,
                                                     "hidden/repair-reports.json": json.dumps({"BK-02": "Orders came in late."})})
        jobs = [c for c in cmds if "run_repair_forks.py run" in c]
        self.assertEqual(sorted(re.search(r"repair_forks.py run --id (\S+) --at (\d+) --item (\S+)", c).groups() for c in jobs),
                         [("g-bare-1", "10", "BK-02"), ("g-bare-1", "20", "BK-02"), ("g-checklist-1", "20", "BK-02")])
        for c in jobs:
            self.assertTrue(re.match(r"if \S+ pending.py repair --id \S+ --at \d+ --item \S+; then sh pace.sh && ", c), c)
            self.assertIn(" --isolate", c.split("run_repair_forks.py run", 1)[1].split("&&")[0])
            self.assertIn("run_repair_forks.py grade --id", c)  # graded in the same job, after the fork
            self.assertLess(c.index("run_repair_forks.py run"), c.index("run_repair_forks.py grade"))


# the stale forks of the reference spec (seed's reference-builds.json): course changes 11 (lag 2) and 25 (lag 3)
SPEC = {"stale": {"11": {"lag": 2, "decline": "skip"}, "25": {"lag": 3, "decline": "stand-in"}}}


class InstrumentRunnerTest(unittest.TestCase):
    """run_growth.sh instrument: R+ through change 40, a stale fork S_C per course change, every reliance fork, the
    spec's gradings, the positive control on R+ at 20 and 40, and the gate report."""

    def test_r_plus_its_stale_forks_their_reliance_forks_the_gradings_the_control_and_the_report(self):
        cmds = dry("instrument")
        trajs = {re.search(r"--id (\S+)", c).group(1): c for c in cmds if "run_trajectory.py" in c}
        self.assertEqual(sorted(trajs), ["g-ref-correct", "g-ref-stale-c11", "g-ref-stale-c25"])
        r = trajs["g-ref-correct"]
        self.assertIn("--arm ref-correct ", r)
        self.assertIn("--replicate g-ref --policy diligent", r)
        self.assertEqual(r.count("sh pace.sh"), 4)  # batches to 10, 20, 30 and 40
        self.assertIn("--changes " + ",".join(str(n) for n in range(31, 41)) + " ", r)
        s11 = trajs["g-ref-stale-c11"]
        self.assertTrue(s11.startswith(f"if {sys.executable} pending.py batch --id g-ref-stale-c11 --changes 11,12,13; then sh pace.sh"))
        for part in ("--arm ref-stale ", "--stale-of 11 --fork-of g-ref-correct", "--changes 11,12,13 "):
            self.assertIn(part, s11)
        self.assertIn("--changes 25,26,27,28 ", trajs["g-ref-stale-c25"])
        forks = sorted(re.search(r"run_course_forks.py --id (\S+) --kind reliance --course (\d+) --fork 1", c).groups()
                       for c in cmds if "run_course_forks.py" in c)
        self.assertEqual(forks, [("g-ref-correct", "11"), ("g-ref-correct", "25"), ("g-ref-stale-c11", "11"),
                                 ("g-ref-stale-c25", "25")])
        grades = [c for c in cmds if "instrument.py" in c]
        self.assertEqual(sorted(re.search(r"instrument.py (\w+) --\w+ (\d+)", c).groups() for c in grades),
                         [("checkpoint", "10"), ("checkpoint", "20"), ("checkpoint", "30"), ("checkpoint", "40"),
                          ("course", "11"), ("course", "25")])
        self.assertTrue(all(re.match(rf"if {re.escape(sys.executable)} pending.py gate --\w+ \d+; then sh pace.sh", c) for c in grades))
        controls = [c for c in cmds if "plant_stale_tests.py" in c]
        self.assertEqual(len(controls), 2)
        for n, c in zip((20, 40), controls):
            self.assertTrue(c.startswith(f"if {sys.executable} pending.py control --id g-ref-correct --change {n}; then sh pace.sh"))
            self.assertIn(f"plant_stale_tests.py --id g-ref-correct --change {n} --items retired", c)
            self.assertIn(f"intent_from_tests.py batch --plan runs/intent-from-tests/pc-g-ref-correct-c{n}/plan.json", c)
            self.assertIn(f"intent_from_tests.py summarize --name pc-g-ref-correct-c{n}", c)
        self.assertTrue(any("report.py --instrument" in c for c in cmds))
        first = lambda k: next(i for i, c in enumerate(cmds) if k in c)  # noqa: E731
        self.assertLess(first("--id g-ref-correct --replicate"), first("--id g-ref-stale-c11"))  # R+ before its forks
        order = [first(k) for k in ("run_trajectory.py", "run_course_forks.py", "instrument.py", "plant_stale_tests.py",
                                    "report.py")]
        self.assertEqual(order, sorted(order))


class IsolationTest(unittest.TestCase):
    """Every growth session runs isolated, as Clowder's do: GitHub's hosts blocked, web search and fetch denied."""

    def test_every_trajectory_and_fork_the_runner_queues_is_isolated(self):
        for phase in ("trial", "full", "instrument", "m2e"):
            cmds = dry(phase)
            sessions = [part for c in cmds for part in c.split(" && ")
                        if "run_trajectory.py" in part or "run_course_forks.py" in part]
            self.assertTrue(sessions, phase)
            for part in sessions:
                self.assertIn(" --isolate", part, (phase, part[:120]))


class PacingTest(unittest.TestCase):
    """pace.sh: before each job, wait while the subscription's weekly usage is at or above USAGE_PAUSE, until it falls
    below USAGE_RESUME; with no reading, log once and carry on."""

    def pace(self, readings, *, missing=False):
        d = Path(tempfile.mkdtemp())
        seq = d / "readings"
        seq.write_text("\n".join(readings) + ("\n" if readings else ""))
        fake = d / "usage.sh"
        fake.write_text(f"#!/bin/sh\nhead -1 '{seq}'\ntail -n +2 '{seq}' > '{seq}.next' && mv '{seq}.next' '{seq}'\n")
        fake.chmod(0o755)
        log = d / "pacing.log"
        env = {**os.environ, "USAGE_CMD": str(d / "absent.sh") if missing else str(fake), "USAGE_PAUSE": "90",
               "USAGE_RESUME": "50", "PACE_SLEEP": "0", "PACE_LOG": str(log), "PACE_MARK": str(d / "unread")}
        p = subprocess.run(["sh", "pace.sh"], cwd=HARNESS, env=env, capture_output=True, text=True, timeout=30)
        return p.returncode, (log.read_text() if log.exists() else ""), env, seq

    def test_a_high_reading_waits_until_usage_falls_below_the_resume_line(self):
        rc, log, _, seq = self.pace(["95", "80", "51", "40", "10"])
        self.assertEqual(rc, 0)
        self.assertIn("95%", log)
        self.assertIn("resuming at 40%", log)
        self.assertEqual(seq.read_text().split(), ["10"])  # it stopped reading once below the line

    def test_a_low_reading_goes_straight_on(self):
        rc, log, _, seq = self.pace(["30"])
        self.assertEqual((rc, log), (0, ""))

    def test_no_reading_is_logged_once_and_the_gate_is_skipped(self):
        rc, log, env, _ = self.pace([], missing=True)
        self.assertEqual(rc, 0)
        self.assertEqual(log.count("no usage reading"), 1)
        subprocess.run(["sh", "pace.sh"], cwd=HARNESS, env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(Path(env["PACE_LOG"]).read_text().count("no usage reading"), 1)  # once, not every job
        rc, log, _, _ = self.pace([""])  # a command that prints nothing
        self.assertIn("no usage reading", log)


if __name__ == "__main__":
    unittest.main()
