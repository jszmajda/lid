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
    def reader(self, d: Path, name: str, readings) -> tuple[Path, Path]:
        seq = d / f"{name}.readings"
        seq.write_text("\n".join(readings) + ("\n" if readings else ""))
        fake = d / f"{name}.sh"
        fake.write_text(f"#!/bin/sh\nhead -1 '{seq}'\ntail -n +2 '{seq}' > '{seq}.next' && mv '{seq}.next' '{seq}'\n")
        return fake, seq

    def gate(self, readings, *, host=("100",), env=None):
        d = Path(tempfile.mkdtemp())
        fake, seq = self.reader(d, "docker", readings)
        hfake, _ = self.reader(d, "host", list(host) * 10)
        self.trims = d / "trims"
        trim = d / "trim.sh"
        trim.write_text(f"#!/bin/sh\necho trimmed >> '{self.trims}'\n")
        log = d / "disk.log"
        e = {**os.environ, "DISK_CMD": str(fake), "HOST_DF_CMD": str(hfake), "TRIM_CMD": str(trim), "DISK_SLEEP": "0",
             "DISK_LOG": str(log), **(env or {})}
        p = subprocess.run(["sh", "disk_gate.sh"], cwd=HARNESS, env=e, capture_output=True, text=True, timeout=30)
        return p.returncode, (log.read_text() if log.exists() else ""), seq

    def trim_count(self):
        return len(self.trims.read_text().split()) if self.trims.exists() else 0

    def test_the_macs_own_free_space_is_checked_too_with_a_trim_before_waiting(self):
        # Colima's disk image doesn't shrink until the VM is trimmed: trim first, then wait while the Mac is still low
        d = Path(tempfile.mkdtemp())
        hfake, hseq = self.reader(d, "host", ["10", "12", "30"])
        rc, log, _ = self.gate(["50"] * 5, env={"HOST_DF_CMD": str(hfake)})
        self.assertEqual(rc, 0)
        self.assertIn("the Mac has 10 GB free, under 25", log)
        self.assertGreaterEqual(self.trim_count(), 1)
        self.assertEqual(hseq.read_text().split(), [])  # it read until the Mac had 25 GB or more

    def test_a_mac_with_room_and_a_docker_disk_with_room_go_straight_on_with_no_trim(self):
        rc, log, _ = self.gate(["50"], host=("80",))
        self.assertEqual((rc, log, self.trim_count()), (0, "", 0))

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
        self.assertIn("no Docker disk reading", log)


if __name__ == "__main__":
    unittest.main()
