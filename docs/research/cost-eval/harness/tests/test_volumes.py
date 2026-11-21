"""Tests for releasing Docker volumes once results are recorded: a grading's checkpoint and tools volumes go as soon as
its verdicts are written (grade_checkpoint.py), and release_volumes.py removes those left by gradings recorded before
that; a main trajectory's checkpoint gradings (grading/change-NN) keep theirs, as its workspace is kept.

Run from the harness folder: python3.12 -m unittest discover -s tests
"""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import grade_checkpoint as gck  # noqa: E402
import release_volumes as rv  # noqa: E402


def ok(cmd, **kw):
    return subprocess.CompletedProcess(cmd, 0, "", "")


class ReleaseTest(unittest.TestCase):
    def test_only_a_main_trajectorys_checkpoint_grading_keeps_its_volumes(self):
        keeps = gck.keeps_volumes
        self.assertTrue(keeps("g-bare-1", "change-10", 10))
        self.assertTrue(keeps("g-ref-correct", "change-20", 20))
        for tid, name, change in (("g-bare-1", "flip-c11-after", 11), ("g-bare-1", "earlier-c05", 5),
                                  ("g-bare-1", "diagnostic-07", 6), ("g-bare-1", "change-10", 11),
                                  ("g-bare-1/course-forks/c11-course-1", "course", 11),
                                  ("g-bare-1/course-forks/c11-reliance-1", "change-14", 14),  # a fork's, whatever its folder
                                  ("g-bare-1/repair-forks/c10-RD-42", "repair", 10)):
            self.assertFalse(keeps(tid, name, change), (tid, name))

    def test_release_removes_the_gradings_checkpoint_and_tools_volumes(self):
        calls = []
        names = gck.release_volumes("g-bare-1/course-forks/c11-course-1", "course", 11,
                                    runner=lambda cmd, **kw: calls.append(cmd) or ok(cmd))
        self.assertEqual(names, ["ce-g-g-bare-1-course-forks-c11-course-1-course-c11-ckpt",
                                 "ce-g-g-bare-1-course-forks-c11-course-1-course-c11-tools"])
        self.assertEqual(calls, [["docker", "volume", "rm", "-f", *names]])
        self.assertEqual(names[0], gck.ckpt_volume("g-bare-1/course-forks/c11-course-1", "course", 11))
        calls.clear()
        self.assertEqual(gck.release_volumes("g-bare-1", "change-10", 10, runner=lambda cmd, **kw: calls.append(cmd)), [])
        self.assertEqual(calls, [])


def write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


class BackfillTest(unittest.TestCase):
    def setUp(self):
        self.runs = Path(tempfile.mkdtemp()) / "runs"
        t = self.runs / "g-bare-1"
        write(t / "trajectory.json", {"id": "g-bare-1"})
        write(t / "grading" / "change-10" / "verdicts.json", {"change": 10, "probes": {}})  # a checkpoint: kept
        write(t / "grading" / "flip-c11-after" / "verdicts.json", {"change": 11, "probes": {}})
        write(t / "grading" / "flip-c12-after" / "verdicts.json", {"change": 12, "error": "setup failed"})  # not recorded
        write(t / "grading" / "earlier-c16" / "earlier.json", {"prepared": ["P-a"], "observed": [], "failed": {}})
        write(t / "grading" / "earlier-c17" / "earlier.json", {"prepared": [], "observed": [], "failed": {"P-b": "x"}})
        write(t / "course-forks" / "c11-course-1" / "grading" / "course" / "verdicts.json", {"change": 11, "probes": {}})
        write(t / "course-forks" / "c11-course-1.before-x" / "grading" / "course" / "verdicts.json", {"change": 11})
        write(t / "repair-forks" / "c10-RD-62" / "grading" / "repair" / "verdicts.json", {"change": 10, "probes": {}})
        write(t / "repair-forks" / "c10-RD-42" / "grading" / "repair" / "verdicts.json", {"change": 10, "probes": {}})

    def test_recorded_gradings_release_their_volumes_and_the_rest_are_left(self):
        calls = []
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = rv.main(["--ids", "g-bare-1", "--runs", str(self.runs), "--keep-run", "g-bare-1/repair-forks/c10-RD-62",
                          "--apply"], runner=lambda cmd, **kw: calls.append(cmd) or ok(cmd))
        self.assertEqual(rc, 0)
        removed = sorted(v for c in calls for v in c[4:])
        self.assertEqual(removed, sorted([
            gck.ckpt_volume("g-bare-1", "flip-c11-after", 11), gck.ckpt_volume("g-bare-1", "flip-c11-after", 11)[:-4] + "tools",
            gck.ckpt_volume("g-bare-1", "earlier-c16", 16), gck.ckpt_volume("g-bare-1", "earlier-c16", 16)[:-4] + "tools",
            gck.ckpt_volume("g-bare-1/course-forks/c11-course-1", "course", 11),
            gck.ckpt_volume("g-bare-1/course-forks/c11-course-1", "course", 11)[:-4] + "tools",
            gck.ckpt_volume("g-bare-1/repair-forks/c10-RD-42", "repair", 10),
            gck.ckpt_volume("g-bare-1/repair-forks/c10-RD-42", "repair", 10)[:-4] + "tools"]))

    def test_without_apply_it_only_lists_them(self):
        calls = []
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rv.main(["--ids", "g-bare-1", "--runs", str(self.runs)], runner=lambda cmd, **kw: calls.append(cmd) or ok(cmd))
        self.assertEqual(calls, [])
        self.assertIn(gck.ckpt_volume("g-bare-1", "flip-c11-after", 11), out.getvalue())
        self.assertNotIn(gck.ckpt_volume("g-bare-1", "change-10", 10), out.getvalue())  # the checkpoint's stay


if __name__ == "__main__":
    unittest.main()
