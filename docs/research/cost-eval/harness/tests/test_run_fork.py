"""Tests for run_fork: one change run from a repository variant's snapshot, recorded like a trajectory.

Docker, the agent's turns, and the owner's model calls are all fakes; the oracle and change script are the made-up
bakery from test_simulator.
"""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import context_telemetry as ctel  # noqa: E402
import run_fork as rf  # noqa: E402
from costeval import executor, simulator as sm  # noqa: E402
from test_simulator import BRIEF, CHANGES, ORACLE, OWNER_ITEMS, FakeAsk, out  # noqa: E402
from test_trajectory import FakeTurns, FakeWorkspace  # noqa: E402

PATCH = """--- a/crates/core/src/lib.rs
+++ b/crates/core/src/lib.rs
@@ -1,3 +1,3 @@
 pub fn price() -> u32 {
-    3
+    4
 }
"""


class Docker:
    """Records docker commands; a planted-bug apply prints a new commit, or fails when told to."""

    def __init__(self, fail_apply=False):
        self.calls, self.fail_apply = [], fail_apply

    def __call__(self, cmd, **kw):
        self.calls.append({"cmd": cmd, "input": kw.get("input")})
        script = cmd[-1] if cmd and isinstance(cmd[-1], str) else ""
        if "git apply" in script:
            if self.fail_apply:
                return subprocess.CompletedProcess(cmd, 1, "", "error: patch failed: crates/core/src/lib.rs:2")
            return subprocess.CompletedProcess(cmd, 0, "f00d\n", "")
        return subprocess.CompletedProcess(cmd, 0, "", "")


class Fixture:
    def __init__(self, change_script=CHANGES, sidecar=None):
        self.root = Path(tempfile.mkdtemp())
        self.seed = self.root / "seed"
        (self.seed / "hidden").mkdir(parents=True)
        (self.seed / "brief.md").write_text(BRIEF)
        (self.seed / "hidden" / "oracle.md").write_text(ORACLE)
        (self.seed / "hidden" / "change-script.md").write_text(change_script)
        (self.seed / "hidden" / "owner-items.json").write_text(json.dumps(OWNER_ITEMS))
        if sidecar:
            (self.seed / "hidden" / "patches").mkdir()
            (self.seed / "hidden" / "patches" / "change-01.diff").write_text(sidecar)
        self.variants = self.root / "variants"
        self.variants.mkdir()
        (self.variants / "manifest.json").write_text(json.dumps({
            "source_commit": "abc123", "seed": "v1", "held_out": ["crates/core/tests/integration/x.rs"],
            "variants": {"stripped": {"commit": "c0ffee", "volume": "ce-cv-v1-stripped", "vcs": "git"},
                         "lid": {"commit": "beef", "volume": "ce-cv-v1-lid", "vcs": "jj"}}}))
        self.runs = self.root / "runs"
        self.sessions, self.installed = [], []
        self.ws = FakeWorkspace()
        self.ask = FakeAsk(out("completion"), out("completion"))

    def argv(self, *extra, variant="stripped", arm="bare"):
        return ["--variants", str(self.variants), "--variant", variant, "--arm", arm, "--change", "1", "--repeat", "2",
                "--replicate", "r1", "--window", "200k", "--seed-dir", str(self.seed), "--runs", str(self.runs), *extra]

    def deps(self, docker=None):
        def turn_for(session):
            self.sessions.append(session)
            return FakeTurns(self.ws, ("Done.", None, ["crates/core/src/lib.rs"]))
        return rf.Deps(docker=docker or Docker(), turn_for=turn_for, workspace_for=lambda image, volume: self.ws,
                       ask=self.ask, touch=self.ask.touch, trim=None,
                       install_lid=lambda image, vol, repo, release: self.installed.append((vol, release)))


class ForkTest(unittest.TestCase):
    def test_a_fork_runs_one_change_from_the_variant_and_records_it_like_a_trajectory(self):
        f = Fixture()
        docker = Docker()
        self.assertEqual(rf.main(f.argv(), deps=f.deps(docker)), 0)
        fid = "cf-stripped-bare-200k-c01-r2"
        run = f.runs / fid
        meta = json.loads((run / "trajectory.json").read_text())
        self.assertEqual(meta["id"], fid)
        self.assertEqual(meta["fork_of"], {"variants": str(f.variants), "variant": "stripped", "volume": "ce-cv-v1-stripped",
                                           "commit": "c0ffee", "source_commit": "abc123", "variant_seed": "v1", "vcs": "git"})
        self.assertEqual((meta["change"], meta["repeat"], meta["replicate"], meta["arm"]), (1, 2, "r1", "bare"))
        self.assertEqual(meta["isolation"], executor.Isolation.for_public_seed(window="200k").record())
        self.assertEqual(meta["window"], "200k")
        self.assertIsNone(meta["planted_bug"])
        self.assertTrue(meta["changes"]["1"]["finished"])
        self.assertEqual(meta["start_commit"], "base")
        self.assertTrue((run / "change-01" / "change.json").exists())
        self.assertTrue((run / "owner-state-01.json").exists())
        # the workspace starts as a copy of the variant's volume, and its build output is cleared at the end
        first, last = docker.calls[0]["cmd"], docker.calls[-1]["cmd"]
        self.assertIn("ce-cv-v1-stripped:/src:ro", first)
        self.assertIn(f"ce-{fid}-ws:/work", first)
        self.assertIn("rm -rf /work/target", last[-1])
        session = f.sessions[0]
        self.assertEqual(session.image, rf.IMAGE)
        self.assertEqual(session.isolation, executor.Isolation.for_public_seed(window="200k"))
        self.assertEqual(f.installed, [])

    def test_the_lid_arm_gets_its_plugin_and_an_existing_fork_is_refused(self):
        f = Fixture()
        self.assertEqual(rf.main(f.argv(variant="lid", arm="lid-full"), deps=f.deps()), 0)
        fid = "cf-lid-lid-full-200k-c01-r2"
        self.assertEqual(f.installed, [(f"ce-{fid}-cfg", "v1.4.6")])
        self.assertEqual(f.sessions[0].plugin_dirs, ("/cfg/lid/plugins/linked-intent-dev",))
        self.assertEqual(rf.main(f.argv(variant="lid", arm="lid-full"), deps=f.deps()), 2)

    def test_telemetry_reads_a_fork_and_takes_its_window_from_the_record(self):
        f = Fixture()
        rf.main(f.argv(), deps=f.deps())
        t = ctel.trajectory_telemetry(f.runs / "cf-stripped-bare-200k-c01-r2", window=None, fetch=None)
        self.assertEqual([c["change"] for c in t["changes"]], [1])
        self.assertEqual(t["window"], 200_000)


class PlantedBugTest(unittest.TestCase):
    def test_a_planted_bug_is_folded_into_the_starting_snapshot_and_its_hash_recorded(self):
        script = CHANGES.replace("**Introduces:** Nothing.", "**Planted bug:** `patches/price.diff`\n\n**Introduces:** Nothing.")
        f = Fixture(change_script=script)
        (f.seed / "hidden" / "patches").mkdir()
        (f.seed / "hidden" / "patches" / "price.diff").write_text(PATCH)
        docker = Docker()
        self.assertEqual(rf.main(f.argv(), deps=f.deps(docker)), 0)
        meta = json.loads((f.runs / "cf-stripped-bare-200k-c01-r2" / "trajectory.json").read_text())
        self.assertEqual(meta["planted_bug"]["sha256"], hashlib.sha256(PATCH.encode()).hexdigest())
        apply = next(c for c in docker.calls if "git apply" in c["cmd"][-1])
        self.assertEqual(apply["input"], PATCH)
        script_text = apply["cmd"][-1]
        self.assertIn("git apply --check", script_text)
        self.assertIn("--amend", script_text)  # one commit, so `git show` can't reveal the planted change
        # and nothing still reaches the snapshot before the bug: no reflog, no jj state or jj keep refs, main moved
        for step in ("rm -rf .jj", "refs/jj", "update-ref refs/heads/main HEAD", "reflog expire --expire=now --all",
                     "gc -q --prune=now"):
            self.assertIn(step, script_text)
        self.assertLess(script_text.index("rm -rf .jj"), script_text.index("git apply --check"))
        self.assertIn(rf.cv.DATE, script_text)
        copy_at = next(i for i, c in enumerate(docker.calls) if "/src:ro" in " ".join(c["cmd"]))
        self.assertLess(copy_at, docker.calls.index(apply))

    def test_a_jj_variant_gets_a_fresh_colocated_jj_repository_after_any_planted_bug(self):
        f = Fixture(sidecar=PATCH)
        docker = Docker()
        self.assertEqual(rf.main(f.argv(variant="lid", arm="lid-full"), deps=f.deps(docker)), 0)
        scripts = [c["cmd"][-1] for c in docker.calls]
        init = next(i for i, s in enumerate(scripts) if "jj git init --colocate" in s)
        plant = next(i for i, s in enumerate(scripts) if "git apply" in s)
        self.assertLess(plant, init)
        self.assertIn("rm -rf .jj", scripts[init])
        meta = json.loads((f.runs / "cf-lid-lid-full-200k-c01-r2" / "trajectory.json").read_text())
        self.assertEqual(meta["fork_of"]["vcs"], "jj")
        g = Fixture()
        docker = Docker()
        rf.main(g.argv(), deps=g.deps(docker))
        self.assertFalse(any("jj git init" in c["cmd"][-1] for c in docker.calls))

    def test_a_sidecar_patch_counts_and_an_explicit_one_wins(self):
        self.assertIsNotNone(json.loads(self._run_with(sidecar=PATCH))["planted_bug"])
        other = PATCH.replace("4", "5")
        path = Path(tempfile.mkdtemp()) / "explicit.diff"
        path.write_text(other)
        meta = json.loads(self._run_with(sidecar=PATCH, extra=("--patch", str(path))))
        self.assertEqual(meta["planted_bug"]["sha256"], hashlib.sha256(other.encode()).hexdigest())

    def _run_with(self, sidecar=None, extra=()):
        f = Fixture(sidecar=sidecar)
        self.assertEqual(rf.main(f.argv(*extra), deps=f.deps()), 0)
        return (f.runs / "cf-stripped-bare-200k-c01-r2" / "trajectory.json").read_text()

    def test_a_patch_that_doesnt_apply_cleanly_stops_the_fork_loudly(self):
        f = Fixture(sidecar=PATCH)
        with self.assertRaisesRegex(RuntimeError, "doesn't apply cleanly to the stripped variant"):
            rf.main(f.argv(), deps=f.deps(Docker(fail_apply=True)))
        self.assertFalse((f.runs / "cf-stripped-bare-200k-c01-r2" / "change-01").exists())

    def test_the_change_script_can_name_a_planted_bug(self):
        script = CHANGES.replace("**Introduces:** Nothing.", "**Planted bug:** `patches/price.diff`\n\n**Introduces:** Nothing.")
        self.assertEqual(sm.parse_change_script(script)[1].planted_bug, "patches/price.diff")
        self.assertIsNone(sm.parse_change_script(CHANGES)[1].planted_bug)


if __name__ == "__main__":
    unittest.main()
