"""Tests for run_fork: one change run from a repository variant's snapshot, or from a named start (M2h's bare and mapped
starts), recorded like a trajectory.

Docker, the agent's turns, and the owner's model calls are all fakes; the oracle and change script are the made-up
bakery from test_simulator.
"""

import contextlib
import hashlib
import io
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
                "--replicate", "r1", "--window", "200k", "--seed-dir", str(self.seed), "--runs", str(self.runs),
                "--lid-repo", str(self.root), *extra]

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

    def test_a_forks_owner_holds_only_the_start_and_its_own_change(self):
        f = Fixture()
        argv = f.argv()
        argv[argv.index("--change") + 1] = "4"
        self.assertEqual(rf.main(argv, deps=f.deps()), 0)
        prompt = f.ask.prompts[0]
        for absent in ("[BK-05]", "[BK-10]", "have a fee"):  # changes 2 and 3 never happened in this fork
            self.assertNotIn(absent, prompt)
        for present in ("[BK-06]", "[BK-04]", "small bakery"):
            self.assertIn(present, prompt)
        meta = json.loads((f.runs / "cf-stripped-bare-200k-c04-r2" / "trajectory.json").read_text())
        self.assertEqual(meta["owner_scope"], sm.FORK_SCOPE)

    def test_a_null_fork_can_record_a_patch_as_its_changes_result_for_grading_from_the_snapshot(self):
        # a right build (the instrument's positive control): committed after the snapshot, never folded into it, so the
        # graders' diff from the start commit shows it as an arm's change would
        f = Fixture()
        patch = f.root / "right.diff"
        patch.write_text(PATCH)

        class Committing(Docker):
            def __call__(self, cmd, **kw):
                self.calls.append({"cmd": cmd, "input": kw.get("input")})
                if "commit -q" in (cmd[-1] if cmd and isinstance(cmd[-1], str) else ""):
                    return subprocess.CompletedProcess(cmd, 0, "r1ght\n", "")
                return subprocess.CompletedProcess(cmd, 0, "", "")
        docker = Committing()
        argv = f.argv()
        argv[argv.index("--arm"):argv.index("--arm") + 2] = []
        self.assertEqual(rf.main([*argv, "--null", "--result-patch", str(patch)], deps=f.deps(docker)), 0)
        meta = json.loads((f.runs / "cf-stripped-null-200k-c01-r2" / "trajectory.json").read_text())
        self.assertEqual(meta["start_commit"], "base")  # the snapshot the fork started from
        self.assertEqual(meta["changes"]["1"]["commit"], "r1ght")  # the patch, committed as the change's result
        self.assertEqual(meta["result_patch"]["sha256"], hashlib.sha256(PATCH.encode()).hexdigest())
        script = next(c for c in docker.calls if "commit -q" in str(c["cmd"]))
        self.assertNotIn("--amend", script["cmd"][-1])
        self.assertEqual(script["input"], PATCH)
        self.assertIsNone(meta["planted_bug"])

    def test_a_result_patch_is_only_for_a_null_fork(self):
        f = Fixture()
        patch = f.root / "right.diff"
        patch.write_text(PATCH)
        with self.assertRaises(SystemExit):
            rf.main([*f.argv(), "--result-patch", str(patch)], deps=f.deps())

    def test_a_null_fork_prepares_the_snapshot_and_records_it_unchanged_with_no_session(self):
        f = Fixture()
        argv = [a for a in f.argv() if a not in ("--arm", "bare")]
        self.assertEqual(rf.main([*argv, "--null"], deps=f.deps()), 0)
        meta = json.loads((f.runs / "cf-stripped-null-200k-c01-r2" / "trajectory.json").read_text())
        self.assertEqual((meta["arm"], meta["lid_release"]), ("null", None))
        self.assertEqual(meta["changes"]["1"]["commit"], meta["start_commit"])  # its result is where it started
        self.assertTrue(meta["changes"]["1"]["null"])
        self.assertEqual((f.sessions, f.installed, f.ask.prompts), ([], [], []))  # no agent, no LID, no owner
        self.assertEqual(meta["owner_scope"], sm.FORK_SCOPE)
        with self.assertRaises(SystemExit):
            rf.main(argv, deps=f.deps())  # a real fork names its arm

    def test_telemetry_reads_a_fork_and_takes_its_window_from_the_record(self):
        f = Fixture()
        rf.main(f.argv(), deps=f.deps())
        t = ctel.trajectory_telemetry(f.runs / "cf-stripped-bare-200k-c01-r2", window=None, fetch=None)
        self.assertEqual([c["change"] for c in t["changes"]], [1])
        self.assertEqual(t["window"], 200_000)


NODE = "lid-cost-eval-executor-node:2.1.323"
LID_TREE = "feedface"  # the map's /cfg/lid hash the starts file records, which a fresh install must match
STARTS = {"image": NODE, "fork_prefix": "m2h-",
          "starts": {"bare": {"volume": "ogmap-bare-ws", "commit": "d96444e", "vcs": "git", "map": "ogmap-bare"},
                     "lid-r1": {"volume": "ogmap-2-ws", "commit": "489e0e0", "vcs": "git", "map": "ogmap-2",
                                "config_volume": "ogmap-2-cfg", "lid_release": "v1.4.6", "lid_sha256": LID_TREE}}}
BOTH = ("/cfg/lid/plugins/linked-intent-dev", "/cfg/lid/plugins/arrow-maintenance")


class HashDocker(Docker):
    """Docker that answers the LID tree hash with a fixed value, and commits a result patch as r1ght."""

    def __init__(self, tree=LID_TREE, **kw):
        super().__init__(**kw)
        self.tree = tree

    def __call__(self, cmd, **kw):
        script = cmd[-1] if cmd and isinstance(cmd[-1], str) else ""
        if "sha256sum" in script:
            self.calls.append({"cmd": cmd, "input": kw.get("input")})
            return subprocess.CompletedProcess(cmd, 0, f"{self.tree}  -\n", "")
        if "commit -q" in script and "result.diff" in script:
            self.calls.append({"cmd": cmd, "input": kw.get("input")})
            return subprocess.CompletedProcess(cmd, 0, "r1ght\n", "")
        return super().__call__(cmd, **kw)


class StartFixture(Fixture):
    """A starts file beside the seed: a bare start and one mapped LID start, as runs/opengym-m2h/starts.json holds."""

    def __init__(self, starts=None, **kw):
        super().__init__(**kw)
        self.starts = self.root / "starts.json"
        self.starts.write_text(json.dumps(STARTS if starts is None else starts))

    def start_argv(self, *extra, start="bare", arm="bare"):
        who = ["--null"] if arm is None else ["--arm", arm]
        return ["--starts", str(self.starts), "--start", start, *who, "--change", "1", "--repeat", "2",
                "--replicate", "m2h-r2", "--window", "1m", "--seed-dir", str(self.seed), "--runs", str(self.runs),
                "--lid-repo", str(self.root), *extra]

    def meta(self, fid):
        return json.loads((self.runs / fid / "trajectory.json").read_text())


def scripts(docker):
    return [" ".join(c["cmd"]) for c in docker.calls]


class StartForkTest(unittest.TestCase):
    def test_a_fork_from_a_named_start_copies_it_read_only_into_volumes_named_for_the_fork(self):
        f = StartFixture()
        docker = HashDocker()
        self.assertEqual(rf.main(f.start_argv(), deps=f.deps(docker)), 0)
        fid = "m2h-bare-c01-r2"  # the starts file's prefix, the arm, the change and the repeat
        meta = f.meta(fid)
        self.assertEqual(meta["fork_of"], {"starts": str(f.starts), "start": "bare", "volume": "ogmap-bare-ws",
                                           "commit": "d96444e", "vcs": "git", "map": "ogmap-bare", "config_volume": None,
                                           "lid_sha256": None, "starts_sha256": rf.sha256(f.starts)})
        self.assertEqual(meta["volumes"], {"workspace": f"{fid}-ws", "config": f"{fid}-cfg"})
        self.assertEqual((meta["image"], meta["replicate"], meta["window"], meta["seed"]), (NODE, "m2h-r2", "1m", "seed"))
        self.assertEqual(meta["isolation"], executor.Isolation.for_public_seed(window="1m").record())
        # the start is only ever mounted read-only, and the copy proves it is at the start's commit with a clean tree
        every = scripts(docker)
        self.assertTrue(all("ogmap-bare-ws:/src:ro" in s for s in every if "ogmap-bare-ws" in s))
        copy = docker.calls[0]["cmd"]
        self.assertIn(f"{fid}-ws:/work", copy)
        self.assertIn("rev-parse --verify 'd96444e^{commit}'", copy[-1])
        self.assertIn("git status --porcelain", copy[-1])
        self.assertFalse(any("ce-" in s for s in every))
        self.assertFalse(any("rm -rf /work/target" in s for s in every))  # a Node start builds nothing into target/
        self.assertEqual(f.sessions[0].image, NODE)
        self.assertEqual(f.sessions[0].isolation, executor.Isolation.for_public_seed(window="1m"))
        self.assertEqual(f.installed, [])

    def test_the_lid_arm_loads_both_plugins_from_a_fresh_install_that_matches_the_maps(self):
        f = StartFixture()
        docker = HashDocker()
        self.assertEqual(rf.main(f.start_argv(start="lid-r1", arm="lid-full-arrows"), deps=f.deps(docker)), 0)
        fid = "m2h-lid-full-arrows-c01-r2"
        self.assertEqual(f.installed, [(f"{fid}-cfg", "v1.4.6")])
        session = f.sessions[0]
        self.assertEqual(session.plugin_dirs, BOTH)
        self.assertEqual(session.expected_plugins, frozenset({"linked-intent-dev", "arrow-maintenance"}))
        self.assertEqual(session.config_volume, f"{fid}-cfg")
        meta = f.meta(fid)
        self.assertEqual((meta["arm"], meta["lid_release"], meta["lid_install_sha256"]), ("lid-full-arrows", "v1.4.6",
                                                                                          LID_TREE))
        tree = next(c["cmd"] for c in docker.calls if "sha256sum" in c["cmd"][-1])
        self.assertIn(f"{fid}-cfg:/cfg:ro", tree)
        self.assertFalse(any("ogmap-2-cfg" in s for s in scripts(docker)))  # the map's own configuration stays out

    def test_the_arm_file_names_both_plugins_at_the_maps_release(self):
        from costeval import trajectory
        arm = trajectory.load_arm("lid-full-arrows")
        self.assertEqual((arm.plugins, arm.lid_release, arm.plugin_dirs), (("linked-intent-dev", "arrow-maintenance"),
                                                                           "v1.4.6", BOTH))
        self.assertEqual((arm.workspace_files, arm.first_prompt_prefix), ({}, {}))

    def test_a_lid_install_that_differs_from_the_maps_stops_the_fork_before_any_session(self):
        f = StartFixture()
        with self.assertRaisesRegex(RuntimeError, "LID install"):
            rf.main(f.start_argv(start="lid-r1", arm="lid-full-arrows"), deps=f.deps(HashDocker(tree="0ther")))
        self.assertEqual(f.sessions, [])
        self.assertFalse((f.runs / "m2h-lid-full-arrows-c01-r2" / "change-01").exists())

    def test_a_fork_id_without_the_prefix_or_that_would_reuse_a_starts_volume_is_refused(self):
        f = StartFixture()
        docker = HashDocker()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(rf.main(f.start_argv("--id", "x-bare-c01-r2"), deps=f.deps(docker)), 2)
        g = StartFixture(starts={k: v for k, v in STARTS.items() if k != "fork_prefix"})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(rf.main(g.start_argv("--id", "ogmap-2"), deps=g.deps(docker)), 2)  # ogmap-2-ws, ogmap-2-cfg
        self.assertEqual(docker.calls, [])

    def test_a_named_start_needs_its_seed_dir_and_exactly_one_source(self):
        f = StartFixture()
        argv = f.start_argv()
        no_seed = argv[:argv.index("--seed-dir")] + argv[argv.index("--seed-dir") + 2:]
        both = [*argv, "--variants", str(f.variants), "--variant", "stripped"]
        neither = argv[4:]
        half = argv[2:]  # --start without --starts
        for bad in (no_seed, both, neither, half):
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                rf.main(bad, deps=f.deps())
        argv[argv.index("--start") + 1] = "lid-r9"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(rf.main(argv, deps=f.deps()), 2)

    def test_a_null_fork_and_a_right_build_work_from_a_named_start(self):
        f = StartFixture()
        self.assertEqual(rf.main(f.start_argv(arm=None), deps=f.deps(HashDocker())), 0)
        meta = f.meta("m2h-null-c01-r2")
        self.assertEqual((meta["arm"], meta["fork_of"]["start"]), ("null", "bare"))
        self.assertEqual(meta["changes"]["1"]["commit"], meta["start_commit"])
        self.assertEqual(meta["volumes"]["workspace"], "m2h-null-c01-r2-ws")
        self.assertEqual((f.sessions, f.installed), ([], []))
        patch = f.root / "right.diff"
        patch.write_text(PATCH)
        docker = HashDocker()
        self.assertEqual(rf.main(f.start_argv("--result-patch", str(patch), "--id", "m2h-right-c01", start="lid-r1",
                                              arm=None), deps=f.deps(docker)), 0)
        meta = f.meta("m2h-right-c01")
        self.assertEqual(meta["changes"]["1"]["commit"], "r1ght")
        self.assertEqual(meta["result_patch"]["sha256"], hashlib.sha256(PATCH.encode()).hexdigest())
        self.assertIn("m2h-right-c01-ws:/work", next(c["cmd"] for c in docker.calls if "result.diff" in c["cmd"][-1]))
        self.assertEqual(f.installed, [])  # a null fork loads nothing, from a LID start too

    def test_npm_network_is_an_explicit_recorded_setting_on_by_default(self):
        f = StartFixture()
        rf.main(f.start_argv(), deps=f.deps(HashDocker()))
        self.assertIs(f.meta("m2h-bare-c01-r2")["npm_network"], True)
        rf.main(f.start_argv("--npm-network", "off", "--id", "m2h-bare-c01-r2-offline"), deps=f.deps(HashDocker()))
        meta = f.meta("m2h-bare-c01-r2-offline")
        self.assertIs(meta["npm_network"], False)
        blocked = set(f.sessions[-1].isolation.blocked_hosts)
        self.assertTrue(set(executor.GITHUB_HOSTS) <= blocked and set(rf.NPM_HOSTS) <= blocked)
        self.assertEqual(set(meta["isolation"]["blocked_hosts"]), blocked)
        self.assertEqual(f.sessions[-1].isolation.denied_tools, executor.WEB_TOOLS)

    def test_the_image_flag_overrides_the_starts_image(self):
        f = StartFixture()
        rf.main(f.start_argv("--image", "other:1"), deps=f.deps(HashDocker()))
        self.assertEqual((f.sessions[0].image, f.meta("m2h-bare-c01-r2")["image"]), ("other:1", "other:1"))

    def test_a_clowder_fork_keeps_its_volumes_image_and_target_cleanup_and_records_npm_network(self):
        f = Fixture()
        docker = Docker()
        self.assertEqual(rf.main(f.argv(), deps=f.deps(docker)), 0)
        meta = json.loads((f.runs / "cf-stripped-bare-200k-c01-r2" / "trajectory.json").read_text())
        self.assertEqual(meta["volumes"]["workspace"], "ce-cf-stripped-bare-200k-c01-r2-ws")
        self.assertEqual((meta["image"], meta["npm_network"]), (rf.IMAGE, True))
        self.assertNotIn("lid_install_sha256", meta)
        self.assertIn("rm -rf /work/target", docker.calls[-1]["cmd"][-1])

    def test_the_lid_tree_hash_is_read_from_the_configuration_volume(self):
        docker = HashDocker(tree="abc123")
        self.assertEqual(rf.lid_tree_sha256(docker, NODE, "m2h-x-cfg"), "abc123")
        self.assertIn("m2h-x-cfg:/cfg:ro", docker.calls[0]["cmd"])


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
