"""disk_gate.sh: before each fork, wait while Docker's free disk is under MIN_FREE_GB (default 20) until it isn't;
with no reading, log once and carry on."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent


class DiskGateTest(unittest.TestCase):
    def gate(self, readings, *, env=None):
        d = Path(tempfile.mkdtemp())
        seq = d / "readings"
        seq.write_text("\n".join(readings) + ("\n" if readings else ""))
        fake = d / "free.sh"
        fake.write_text(f"#!/bin/sh\nhead -1 '{seq}'\ntail -n +2 '{seq}' > '{seq}.next' && mv '{seq}.next' '{seq}'\n")
        log = d / "disk.log"
        e = {**os.environ, "DISK_CMD": str(fake), "DISK_SLEEP": "0", "DISK_LOG": str(log), **(env or {})}
        p = subprocess.run(["sh", "disk_gate.sh"], cwd=HARNESS, env=e, capture_output=True, text=True, timeout=30)
        return p.returncode, (log.read_text() if log.exists() else ""), seq

    def test_enough_free_disk_goes_straight_on(self):
        rc, log, seq = self.gate(["35", "10"])
        self.assertEqual((rc, log), (0, ""))
        self.assertEqual(seq.read_text().split(), ["10"])  # one reading

    def test_too_little_waits_until_there_is_enough(self):
        rc, log, seq = self.gate(["12", "19", "20", "5"])
        self.assertEqual(rc, 0)
        self.assertIn("12 GB free", log)
        self.assertIn("19 GB free", log)
        self.assertEqual(seq.read_text().split(), ["5"])  # it stopped reading at 20

    def test_the_threshold_is_configurable(self):
        rc, log, _ = self.gate(["25", "40"], env={"MIN_FREE_GB": "30"})
        self.assertIn("25 GB free, under 30", log)

    def test_no_reading_is_logged_and_the_gate_is_skipped(self):
        rc, log, _ = self.gate([""])
        self.assertEqual(rc, 0)
        self.assertIn("no disk reading", log)


if __name__ == "__main__":
    unittest.main()
