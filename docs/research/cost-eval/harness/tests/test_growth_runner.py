"""run_growth.sh, dry: the trajectories, course-change forks, and checkpoints each phase would run."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
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

## Change 13 — Refunds

### Owner request

> Refunds.

**Introduces:** RD-52.
**Reliance for:** change 11

## Change 25 — Bring fees back

### Owner request

> Fees again.

**Introduces:** RD-53.
**Course change:** re-reversal of change 11 (distance 14)

## Change 28 — Invoices

### Owner request

> Invoices.

**Introduces:** RD-54.
**Reliance for:** change 25
"""


def dry(*args: str) -> list[str]:
    seed = Path(tempfile.mkdtemp())
    (seed / "hidden").mkdir()
    (seed / "hidden" / "change-script.md").write_text(SCRIPT)
    env = {**os.environ, "DRY": "1", "RUNS": tempfile.mkdtemp(), "SEED_DIR": str(seed), "PY": sys.executable, "JOBS": "1"}
    p = subprocess.run(["sh", "run_growth.sh", *args], cwd=HARNESS, env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    return [l for l in p.stdout.splitlines() if ".py" in l]


class GrowthRunnerTest(unittest.TestCase):
    def test_the_trial_is_bare_1_and_lid_1_through_change_20_with_forks_and_two_checkpoints(self):
        cmds = dry("trial")
        trajs = [c for c in cmds if "run_trajectory.py" in c]
        self.assertEqual(len(trajs), 2)
        for c in trajs:
            self.assertIn("--seed releasedesk", c)
            self.assertIn("--replicate g-r1", c)
            self.assertIn("--policy bounded --owner-model-config central", c)
            self.assertIn("--changes " + ",".join(str(n) for n in range(21)) + " ", c)
        self.assertEqual(sorted(re.search(r"--id (\S+)", c).group(1) for c in trajs), ["g-bare-1", "g-lid-full-1"])
        forks = [c for c in cmds if "run_course_forks.py" in c]
        # for each trajectory: three course forks of change 11 and three reliance forks of change 13 (25 and 28 come later)
        self.assertEqual(sorted({re.search(r"--kind (\w+) --(course|reliance) (\d+)", c).groups() for c in forks}),
                         [("course", "course", "11"), ("reliance", "reliance", "13")])
        self.assertEqual(len(forks), 2 * (3 + 3))
        checks = [c for c in cmds if "growth_checkpoint.py" in c]
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
        self.assertTrue(all("--changes " + ",".join(str(n) for n in range(41)) + " " in c for c in trajs.values()))
        forks = [c for c in cmds if "run_course_forks.py" in c]
        # by default from each arm's first replicate only (FORK_REPLICATES), not the drift floor: both course changes,
        # three forks each
        self.assertEqual(len(forks), 3 * (2 * 3 + 2 * 3))  # two course changes and two reliance changes, three forks each
        self.assertEqual(sorted({re.search(r"--id (\S+)", c).group(1) for c in forks}),
                         ["g-bare-1", "g-bare-one-line-1", "g-lid-full-1"])
        checks = [c for c in cmds if "growth_checkpoint.py" in c]
        self.assertEqual(len(checks), 14 * 4)


if __name__ == "__main__":
    unittest.main()
