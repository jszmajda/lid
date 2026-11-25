"""Tests for m2h_starts: M2h's named starts (the shared bare start and one mapped LID start per replicate) written as the
starts file run_fork.py --starts reads, from the mapping records, with each start's volume checked at its commit and each
map's LID tree hashed, read-only. Docker is a fake.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import m2h_starts as ms  # noqa: E402

NODE = "lid-cost-eval-executor-node:2.1.323"
BARE = "d96444e6434447e5c502e7645a8cb4fa957b7a91"
MAPS = {"ogmap-2": "489e0e0db9f1b6f6af9cfaeba63e066764a84918", "ogmap-3": "eaf96bfe0d3669945b80f99d615232b28f78f92b",
        "ogmap-4": "320c3f6ee08bd3615eff1cb77af5e24d6dcb0e93"}


class FakeDocker:
    """Answers a start volume's HEAD with its commit and a configuration volume's LID tree with a hash."""

    def __init__(self, heads, trees):
        self.heads, self.trees, self.calls = heads, trees, []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        mount = next(a for a in cmd if ":/" in a)
        vol = mount.split(":", 1)[0]
        if "sha256sum" in cmd[-1]:
            return subprocess.CompletedProcess(cmd, 0, f"{self.trees[vol]}  -\n", "")
        return subprocess.CompletedProcess(cmd, 0, f"{self.heads[vol]}\n", "")


class StartsTest(unittest.TestCase):
    def setUp(self):
        self.maps = Path(tempfile.mkdtemp())
        self.write("ogmap-bare", {"id": "ogmap-bare", "bare_start": BARE, "lid_start": None, "image": NODE,
                                  "volumes": {"workspace": "ogmap-bare-ws", "config": "ogmap-bare-cfg"}})
        for m, c in MAPS.items():
            self.write(m, {"id": m, "bare_start": BARE, "lid_start": c, "image": NODE, "stop": "done",
                           "lid_release": "v1.4.6", "plugins": ["linked-intent-dev", "arrow-maintenance"],
                           "volumes": {"workspace": f"{m}-ws", "config": f"{m}-cfg"}})
        self.heads = {"ogmap-bare-ws": BARE, **{f"{m}-ws": c for m, c in MAPS.items()}}
        self.trees = {f"{m}-cfg": "feedface" for m in MAPS}
        self.out = self.maps / "out" / "starts.json"

    def write(self, run_id, meta):
        (self.maps / run_id).mkdir(parents=True, exist_ok=True)
        (self.maps / run_id / "mapping.json").write_text(json.dumps(meta))

    def main(self, docker=None):
        docker = docker or FakeDocker(self.heads, self.trees)
        return ms.main(["--maps", str(self.maps), "--out", str(self.out)], docker=docker), docker

    def test_the_starts_are_the_bare_start_and_one_map_per_replicate_checked_read_only(self):
        rc, docker = self.main()
        self.assertEqual(rc, 0)
        d = json.loads(self.out.read_text())
        self.assertEqual((d["image"], d["fork_prefix"], d["maps"]), (NODE, "m2h-", str(self.maps)))
        self.assertEqual(d["starts"]["bare"], {"volume": "ogmap-bare-ws", "commit": BARE, "vcs": "git", "map": "ogmap-bare"})
        self.assertEqual(d["starts"]["lid-r1"], {"volume": "ogmap-2-ws", "commit": MAPS["ogmap-2"], "vcs": "git",
                                                 "map": "ogmap-2", "config_volume": "ogmap-2-cfg", "lid_release": "v1.4.6",
                                                 "plugins": ["linked-intent-dev", "arrow-maintenance"],
                                                 "lid_sha256": "feedface"})
        self.assertEqual([d["starts"][f"lid-r{k}"]["map"] for k in (1, 2, 3)], ["ogmap-2", "ogmap-3", "ogmap-4"])
        self.assertTrue(all(any(a.endswith(":ro") for a in c) for c in docker.calls))  # nothing is mounted writable
        self.assertEqual(len(docker.calls), 4 + 3)  # each start's HEAD, each map's LID tree

    def test_a_start_volume_not_at_its_commit_is_refused(self):
        self.heads["ogmap-3-ws"] = "0" * 40
        self.assertEqual(self.main()[0], 2)
        self.assertFalse(self.out.exists())

    def test_a_map_from_another_bare_start_or_unfinished_is_refused(self):
        self.write("ogmap-4", {**json.loads((self.maps / "ogmap-4" / "mapping.json").read_text()), "bare_start": "f" * 40})
        self.assertEqual(self.main()[0], 2)
        self.setUp()
        self.write("ogmap-2", {**json.loads((self.maps / "ogmap-2" / "mapping.json").read_text()), "lid_start": None,
                               "stop": "capped"})
        self.assertEqual(self.main()[0], 2)
        self.assertFalse(self.out.exists())

    def test_maps_whose_lid_trees_differ_are_refused(self):
        self.trees["ogmap-3-cfg"] = "0ther"
        self.assertEqual(self.main()[0], 2)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
