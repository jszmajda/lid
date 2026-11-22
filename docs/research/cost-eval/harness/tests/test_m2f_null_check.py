"""m2f_null_check.py: the untouched snapshot graded at every M2f change must meet no new row, and pass every
dependency probe and held-out test, since it is the state before each change."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import m2f_null_check as nc  # noqa: E402

SCRIPT = """# Change script

## Change 13 — A faster top speed

### Owner request

> Faster, please.

**Introduces:** CLX-1301, CLX-1302.

## Change 20 — Put the away entry where the absence began

### Owner request

> The away entry is in the wrong place.

**Introduces:** CLX-2001, CLX-2002.
"""


def null_fork(runs: Path, n: int, *, items, probes, held=None, graded_targets=None):
    d = runs / f"m2f-null-c{n:02d}"
    g = d / "grading" / f"change-{n:02d}"
    g.mkdir(parents=True)
    (d / "trajectory.json").write_text(json.dumps({"arm": "null", "change": n, "changes": {str(n): {"commit": "c0"}}}))

    def rec(r):  # a result, or (result, extra fields)
        return {"result": r} if isinstance(r, str) else {"result": r[0], **r[1]}
    (g / "summary.json").write_text(json.dumps({
        "items": items, "dependency_probes": {t: rec(r) for t, r in probes.items()},
        "held_out_tests": {t: rec(r) for t, r in (held or {}).items()},
        "graded_targets": graded_targets or {"targets": ["m2f_target"]}}))


class NullCheckTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.runs, self.files = self.root / "runs", self.root / "m2f"
        self.files.mkdir()
        (self.files / "change-script.md").write_text(SCRIPT)

    def check(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = nc.main(["--runs", str(self.runs), "--forks", "m2f-null-c*", "--seed-files", str(self.files)])
        return rc, out.getvalue(), json.loads((self.runs / "clowder-m2f" / "null-check.json").read_text())

    def test_the_snapshot_meets_no_new_row_and_passes_every_dependency_probe_and_held_out_test(self):
        null_fork(self.runs, 13, items={"CLX-1301": "not met", "CLX-1302": "not met"},
                  probes={"update::probe_m2f_speed": "passed"})
        null_fork(self.runs, 20, items={"CLX-2001": "not met", "CLX-2002": "not met"},
                  probes={"report_queue::probe_m2f_history": "passed"}, held={"report_queue::a": "passed"})
        rc, text, rec = self.check()
        self.assertEqual(rc, 0)
        self.assertEqual(rec["problems"], [])
        self.assertIn("| 13 | 0 of 2 | 1 of 1 | – | ok |", text)
        self.assertIn("| 20 | 0 of 2 | 1 of 1 | 1 of 1 | ok |", text)

    def test_a_row_met_or_a_probe_failing_on_the_snapshot_is_a_problem(self):
        null_fork(self.runs, 13, items={"CLX-1301": "met", "CLX-1302": "not met"},
                  probes={"update::probe_m2f_speed": "failed"})
        rc, text, rec = self.check()
        self.assertEqual(rc, 1)
        self.assertEqual(sorted(p["what"] for p in rec["problems"]),
                         ["CLX-1301 met on the snapshot", "update::probe_m2f_speed failed on the snapshot"])
        self.assertIn("change 20: not graded", text)  # a change with no null grading is named

    def test_a_target_missing_on_the_snapshot_is_a_problem_with_its_cause(self):
        null_fork(self.runs, 13, items={"CLX-1301": "not met", "CLX-1302": "not met"},
                  probes={"update::probe_m2f_speed": ("not built", {"cause": "E0425"})})
        null_fork(self.runs, 20, items={"CLX-2001": "not met", "CLX-2002": "not met"},
                  probes={"report_queue::probe_m2f_history": ("not run", {"cause": "ignored"})},
                  held={"report_queue::a": ("failed", {"class": "new state only"})})
        rc, text, rec = self.check()
        self.assertEqual(rc, 1)
        self.assertEqual(sorted(p["what"] for p in rec["problems"]), [
            "report_queue::a failed on the snapshot",  # the snapshot must pass outright
            "report_queue::probe_m2f_history missing on the snapshot (not run: ignored)",
            "update::probe_m2f_speed missing on the snapshot (not built: E0425)"])

    def test_graded_targets_skipped_on_the_snapshot_is_a_problem(self):
        null_fork(self.runs, 13, items={"CLX-1301": "not met", "CLX-1302": "not met"}, probes={},
                  graded_targets={"skipped": "no graded targets: v2/graded/graded.json doesn't exist"})
        rc, text, rec = self.check()
        self.assertEqual(rc, 1)
        self.assertEqual([p["what"] for p in rec["problems"]],
                         ["graded targets not run: no graded targets: v2/graded/graded.json doesn't exist"])

    def test_rows_without_llm_probes_yet_are_named_not_counted_as_passing(self):
        null_fork(self.runs, 13, items={}, probes={"update::probe_m2f_speed": "passed"})
        rc, text, rec = self.check()
        self.assertIn("CLX-1301, CLX-1302 have no verdict", text)
        self.assertEqual(rec["changes"]["13"]["rows_without_verdict"], ["CLX-1301", "CLX-1302"])


if __name__ == "__main__":
    unittest.main()
