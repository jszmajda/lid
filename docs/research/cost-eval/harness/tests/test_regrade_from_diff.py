"""regrade_from_diff.py: a graded Clowder fork whose volumes are gone, rebuilt from the diff its grading saved
(grading/change-NN/arm.diff) and graded again: a bare fork on its own stripped variant, a LID fork on a grader-stripped
copy of its full variant, so the graded tree is the one the first grading saw."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import regrade_from_diff as rg  # noqa: E402


def write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(obj if isinstance(obj, str) else json.dumps(obj))


class Fixture(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.runs = self.root / "runs"
        self.v2 = self.runs / "clowder-variants" / "v2"
        write(self.v2 / "manifest.json", {"seed": "v2", "source_commit": "86db995", "held_out": ["crates/a/tests/x.rs"],
                                          "variants": {"full": {"commit": "f1", "volume": "ce-cv-v2-full", "vcs": "jj"},
                                                       "stripped": {"commit": "s1", "volume": "ce-cv-v2-stripped", "vcs": "git",
                                                                    "report": {"spec_id_pattern": "(SIM|TUI)-[A-Z]+-\\\\d{3}"}}}})
        (self.v2 / "held-out").mkdir()
        (self.v2 / "graded").mkdir()
        for fid, variant, arm in (("m2f-stripped-bare-c15-r1", "stripped", "bare"), ("m2f-full-lid-full-c15-r2", "full", "lid-full")):
            write(self.runs / fid / "trajectory.json", {"id": fid, "arm": arm, "change": 15, "repeat": int(fid[-1]),
                                                        "replicate": f"m2f-r{fid[-1]}",
                                                        "fork_of": {"variants": str(self.v2), "variant": variant}})
            write(self.runs / fid / "grading" / "change-15" / "arm.diff", f"diff for {fid}\n")
            write(self.runs / fid / "grading" / "change-15" / "summary.json", {"items": {"CLX-1501": "met"}})


class BaseTest(Fixture):
    def test_a_bare_fork_rebuilds_on_its_own_stripped_variant_and_a_lid_fork_on_a_grader_stripped_full_one(self):
        bare = rg.base_for(json.loads((self.runs / "m2f-stripped-bare-c15-r1" / "trajectory.json").read_text()))
        lid = rg.base_for(json.loads((self.runs / "m2f-full-lid-full-c15-r2" / "trajectory.json").read_text()))
        self.assertEqual(bare, (self.v2, "stripped"))
        self.assertEqual(lid, (self.v2.parent / "v2-gs", "full-gs"))

    def test_the_grader_stripped_variant_set_keeps_the_first_sets_held_out_files_and_graded_targets(self):
        out = rg.write_gs_manifest(self.v2, commit="g1", volume="ce-cv-v2-gs-full", source_variant="full")
        m = json.loads((out / "manifest.json").read_text())
        self.assertEqual(m["variants"]["full-gs"], {"commit": "g1", "volume": "ce-cv-v2-gs-full", "vcs": "git",
                                                    "built_from": {"variants": str(self.v2), "variant": "full", "commit": "f1",
                                                                   "stripped_as": "the graders' code-only checkout"}})
        self.assertEqual(m["held_out"], ["crates/a/tests/x.rs"])
        self.assertEqual(m["variants"]["stripped"]["report"]["spec_id_pattern"], "(SIM|TUI)-[A-Z]+-\\\\d{3}")  # for grading
        self.assertTrue((out / "held-out").resolve() == (self.v2 / "held-out").resolve())
        self.assertTrue((out / "graded").resolve() == (self.v2 / "graded").resolve())


class AdoptTest(Fixture):
    def regraded(self, fid, diff=None):
        r = self.runs / f"regrade-{fid}"
        write(r / "grading" / "change-15" / "summary.json", {"items": {"CLX-1501": "not met"}})
        write(r / "grading" / "change-15" / "arm.diff", diff if diff is not None else f"diff for {fid}\n")
        return r

    def test_the_regrade_takes_the_forks_grading_place_with_the_first_kept_beside_it_and_says_how_it_was_built(self):
        fid = "m2f-full-lid-full-c15-r2"
        self.regraded(fid)
        rg.adopt(self.runs, fid, change=15, base=("v2-gs", "full-gs"))
        f = self.runs / fid
        self.assertEqual(json.loads((f / "grading-v1" / "change-15" / "summary.json").read_text())["items"]["CLX-1501"], "met")
        s = json.loads((f / "grading" / "change-15" / "summary.json").read_text())
        self.assertEqual(s["items"]["CLX-1501"], "not met")
        self.assertEqual(s["rebuilt"]["from"], "grading-v1/change-15/arm.diff")
        self.assertIn("stripped", s["rebuilt"]["on"])
        self.assertEqual(s["rebuilt"]["regrade_fork"], f"regrade-{fid}")
        self.assertTrue(s["rebuilt"]["tree_matches_first_grading"])  # the regrade's diff equals the one first graded
        rg.adopt(self.runs, fid, change=15, base=("v2-gs", "full-gs"))  # again: the first grading isn't overwritten
        self.assertEqual(json.loads((f / "grading-v1" / "change-15" / "summary.json").read_text())["items"]["CLX-1501"], "met")

    def test_a_regrade_whose_tree_differs_from_the_first_grading_is_refused(self):
        fid = "m2f-stripped-bare-c15-r1"
        self.regraded(fid, diff="something else\n")
        with self.assertRaises(ValueError):
            rg.adopt(self.runs, fid, change=15, base=("v2", "stripped"))
        self.assertFalse((self.runs / fid / "grading-v1").exists())


class PlanTest(Fixture):
    def test_the_plan_lists_each_fork_of_the_change_with_its_base(self):
        jobs = rg.plan(self.runs, 15, ["m2f-*-c15-r*"])
        self.assertEqual([(j["fork"], j["variant"]) for j in jobs],
                         [("m2f-full-lid-full-c15-r2", "full-gs"), ("m2f-stripped-bare-c15-r1", "stripped")])
        self.assertTrue(all(j["patch"].endswith("grading/change-15/arm.diff") for j in jobs))


# ------------------------------------------------------------------------------------------- M2h (openGym, Node)

# the arm's diff as grade_node wrote it: an annotation line the LID arm added is gone from the content, while the hunk
# header still counts it, and the index line names the blob that had it
FIRST = ("diff --git a/api/watch-relay.js b/api/watch-relay.js\n"
         "index 1111111..2222222 100644\n"
         "--- a/api/watch-relay.js\n+++ b/api/watch-relay.js\n"
         "@@ -1,3 +1,5 @@ import x\n const a = 1\n+const b = 2\n const c = 3\n-const d = 4\n+const d = 5\n"
         "@@ -10,2 +12,3 @@ function f\n keep\n+added\n tail\n"
         "diff --git a/api/new.js b/api/new.js\nnew file mode 100644\nindex 0000000..3333333\n"
         "--- /dev/null\n+++ b/api/new.js\n@@ -0,0 +1,2 @@\n+one\n")


def git(repo: Path, *args, input=None) -> str:
    p = subprocess.run(["git", "-C", str(repo), *args], input=input, capture_output=True, text=True)
    if p.returncode:
        raise AssertionError(f"git {args}: {p.stderr}")
    return p.stdout


def git_repo(files: dict) -> Path:
    repo = Path(tempfile.mkdtemp()) / "start"
    repo.mkdir()
    git(repo, "init", "-q")
    for name, text in files.items():
        (repo / name).write_text(text)
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "start")
    return repo


def run_tree_script(repo: Path, base: str, diff: str):
    p = subprocess.run(["sh", "-c", rg.tree_script(base, repo=str(repo))], input=diff, capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else None


class NodeFixture(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.runs = self.root / "runs"
        self.starts = self.runs / "opengym-m2h" / "starts.json"
        write(self.starts, {"image": "lid-cost-eval-executor-node:2.1.323", "fork_prefix": "m2h-",
                            "starts": {"bare": {"volume": "ogmap-bare-ws", "commit": "d96444e"},
                                       "lid-r1": {"volume": "ogmap-2-ws", "commit": "489e0e0"}}})
        for fid, start in (("m2h-bare-c11-r2", "bare"), ("m2h-lid-c01-r1", "lid-r1")):
            n = int(fid.split("-c")[1][:2])
            write(self.runs / fid / "trajectory.json", {
                "id": fid, "arm": "bare" if "bare" in fid else "lid-full-arrows", "change": n, "repeat": int(fid[-1]),
                "replicate": f"m2h-r{fid[-1]}", "window": "1m", "image": "lid-cost-eval-executor-node:2.1.323",
                "fork_of": {"starts": str(self.starts), "start": start, "volume": "v", "commit": "c"},
                "volumes": {"workspace": f"{fid}-ws", "config": f"{fid}-cfg"}})
            g = self.runs / fid / "grading" / f"change-{n:02d}"
            write(g / "arm.diff", FIRST)
            write(g / "summary.json", {"items": {"OGM-0101": "met"}, "keeping": {"failed": None, "suites": {
                "frontend": {"exit": 137, "error": "no report from the runner"}}}, "joint": {"implemented": "yes"}})
            write(g / "keeping.json", {"failures": {}, "suites": {"frontend": {"exit": 137}}})
            write(g / "keeping" / "frontend.log", "Killed\n")


class NodeRebuildTest(NodeFixture):
    def test_an_m2h_forks_diff_is_recounted_so_it_applies_where_lines_were_taken_out(self):
        fixed = rg.recount(FIRST)
        self.assertIn("@@ -1,3 +1,4 @@ import x\n", fixed)  # three old lines, four new
        self.assertIn("@@ -10,2 +12,3 @@ function f\n", fixed)  # already right: unchanged
        self.assertIn("@@ -0,0 +1 @@\n", fixed)
        self.assertEqual(rg.recount(fixed), fixed)
        self.assertEqual([x for x in fixed.splitlines() if not x.startswith("@@")],
                         [x for x in FIRST.splitlines() if not x.startswith("@@")])

    def test_an_m2h_fork_rebuilds_as_a_null_fork_of_its_own_start_under_the_regrade_prefix(self):
        files = self.root / "seed" / "hidden" / "m2h"
        argv = rg.node_rebuild_argv(self.runs, "m2h-lid-c01-r1", 1, seed_dir=self.root / "seed", files=files)
        starts = self.runs / "opengym-m2h" / "regrade" / "starts.json"
        s = json.loads(starts.read_text())
        self.assertEqual(s["fork_prefix"], "rg-m2h-")  # never matched by the reports' m2h-* globs
        self.assertEqual(s["starts"], json.loads(self.starts.read_text())["starts"])  # the same starts, read-only
        get = lambda flag: argv[argv.index(flag) + 1]  # noqa: E731
        self.assertEqual((get("--starts"), get("--start"), get("--id")), (str(starts), "lid-r1", "rg-m2h-lid-c01-r1"))
        self.assertIn("--null", argv)
        self.assertEqual((get("--change"), get("--repeat"), get("--replicate"), get("--window")), ("1", "1", "m2h-r1", "1m"))
        self.assertEqual(Path(get("--result-patch")).read_text(), rg.applicable(FIRST))
        self.assertEqual((get("--seed-dir"), get("--oracle")), (str(self.root / "seed"), str(files / "oracle.md")))
        self.assertEqual(rg.regrade_id("m2h-lid-c01-r1", {"fork_of": {"start": "lid-r1"}}), "rg-m2h-lid-c01-r1")
        self.assertEqual(rg.regrade_id("m2f-x-c15-r1", {"fork_of": {"variants": "v"}}), "regrade-m2f-x-c15-r1")

    def test_a_hunk_left_with_no_change_goes_so_the_diff_applies_and_gives_the_tree_the_first_diff_describes(self):
        # a LID fork that only edited an annotation leaves a hunk of context alone in the grader's diff (git apply calls
        # that corrupt); a new file of annotations alone leaves a new empty file
        repo = git_repo({"f": "a\nb\nc\nd\n", "g": "x\ny\n"})
        first = ("diff --git a/f b/f\nindex 1111111..2222222 100644\n--- a/f\n+++ b/f\n@@ -1,3 +1,3 @@\n a\n b\n c\n"
                 "diff --git a/g b/g\nindex 3333333..4444444 100644\n--- a/g\n+++ b/g\n@@ -1,2 +1,4 @@\n x\n-y\n+z\n"
                 "diff --git a/h b/h\nnew file mode 100644\nindex 0000000..5555555\n--- /dev/null\n+++ b/h\n@@ -0,0 +1 @@\n")
        patch = rg.applicable(first)
        self.assertNotIn("diff --git a/f b/f", patch)
        self.assertIn("@@ -1,2 +1,2 @@\n x\n-y\n+z\n", patch)
        self.assertIn("diff --git a/h b/h\nnew file mode 100644\nindex 0000000..e69de29\n", patch)
        self.assertNotIn("+++ b/h", patch)
        git(repo, "apply", "--check", input=patch)
        git(repo, "apply", input=patch)
        self.assertEqual((repo / "g").read_text(), "x\nz\n")
        self.assertEqual((repo / "h").read_text(), "")
        # the first diff and the rebuilt tree's own diff, each applied to the start, give one tree: the rebuilt one
        base = git(repo, "rev-parse", "HEAD").strip()
        git(repo, "add", "-A")
        git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "rebuilt")
        regrade = git(repo, "diff", "--no-color", base, "HEAD")
        tree = lambda d: run_tree_script(repo, base, d)  # noqa: E731
        self.assertIsNotNone(tree(first))
        self.assertEqual(tree(first), tree(regrade))
        self.assertEqual(tree(first), git(repo, "rev-parse", "HEAD^{tree}").strip())
        self.assertNotEqual(tree(first), tree(regrade.replace("+z", "+w")))

    def test_two_diffs_match_exactly_or_by_the_tree_each_gives_on_the_start(self):
        self.assertEqual(rg.match_kind(FIRST, FIRST, None), "exact")
        rebuilt = rg.recount(FIRST).replace("2222222", "4444444")
        self.assertIsNone(rg.match_kind(FIRST, rebuilt, None))  # a Clowder fork: the same bytes or nothing
        self.assertEqual(rg.match_kind(FIRST, rebuilt, lambda d: "t1"), "tree")
        self.assertIsNone(rg.match_kind(FIRST, rebuilt, lambda d: d))
        self.assertIsNone(rg.match_kind(FIRST, rebuilt, lambda d: None))  # a diff that doesn't apply matches nothing


class NodeAdoptTest(NodeFixture):
    def regraded(self, fid, n, diff, keeping_only=False):
        r = self.runs / f"rg-{fid}"
        g = r / "grading" / f"change-{n:02d}"
        write(g / "arm.diff", diff)
        write(g / "summary.json", {"items": {} if keeping_only else {"OGM-0101": "not met"},
                                   "keeping": {"failed": 2, "suites": {"frontend": {"exit": 1}}},
                                   **({"probes_skipped": "--no-probes"} if keeping_only else {"joint": {"implemented": "no"}})})
        write(g / "keeping.json", {"failures": {"a::x": {}, "b::y": {}}, "suites": {"frontend": {"exit": 1}}})
        write(g / "keeping" / "frontend.log", "ok\n")
        return r

    def test_a_rebuilt_m2h_fork_is_adopted_with_how_its_diff_matched(self):
        fid = "m2h-lid-c01-r1"
        self.regraded(fid, 1, rg.recount(FIRST).replace("2222222", "4444444"))
        s = rg.adopt(self.runs, fid, change=1, base=rg.base_for(json.loads((self.runs / fid / "trajectory.json").read_text())),
                     trees=lambda d: "same tree")
        f = self.runs / fid
        self.assertEqual(json.loads((f / "grading-v1" / "change-01" / "summary.json").read_text())["items"]["OGM-0101"], "met")
        self.assertEqual(s["items"]["OGM-0101"], "not met")
        self.assertEqual(s["rebuilt"]["diff_match"], "tree")
        self.assertEqual(s["rebuilt"]["regrade_fork"], "rg-m2h-lid-c01-r1")
        self.assertEqual(s["rebuilt"]["on"], "its own start (lid-r1), from the diff its grading saved")
        self.assertTrue(s["rebuilt"]["tree_matches_first_grading"])

    def test_a_rebuilt_m2h_fork_with_another_diff_is_refused(self):
        fid = "m2h-bare-c11-r2"
        self.regraded(fid, 11, FIRST.replace("+one", "+two"))
        with self.assertRaises(ValueError):
            rg.adopt(self.runs, fid, change=11, base=("bare", "start"), trees=lambda d: d)
        with self.assertRaises(ValueError):
            rg.adopt_keeping(self.runs, fid, change=11, trees=lambda d: d)
        self.assertFalse((self.runs / fid / "grading-v1").exists())

    def test_keeping_measured_again_on_the_rebuilt_tree_replaces_only_the_keeping(self):
        fid = "m2h-bare-c11-r2"
        self.regraded(fid, 11, FIRST, keeping_only=True)
        s = rg.adopt_keeping(self.runs, fid, change=11, reason="the web app's suite was killed for lack of memory")
        g = self.runs / fid / "grading" / "change-11"
        self.assertEqual(s["keeping"]["failed"], 2)
        self.assertEqual(s["items"], {"OGM-0101": "met"})  # the rest of the grading stays
        self.assertEqual(s["joint"], {"implemented": "yes"})
        self.assertEqual(s["keeping_rebuilt"]["diff_match"], "exact")
        self.assertEqual(s["keeping_rebuilt"]["reason"], "the web app's suite was killed for lack of memory")
        self.assertEqual(s["keeping_rebuilt"]["previous"]["suites"]["frontend"]["exit"], 137)
        self.assertEqual(json.loads((g / "keeping.json").read_text())["failures"], {"a::x": {}, "b::y": {}})
        self.assertEqual((g / "keeping-v1" / "frontend.log").read_text(), "Killed\n")
        self.assertEqual(json.loads((g / "keeping-v1.json").read_text())["suites"]["frontend"]["exit"], 137)
        self.assertEqual((g / "keeping" / "frontend.log").read_text(), "ok\n")

    def test_a_grading_set_aside_for_a_regrade_in_place_keeps_the_first_once(self):
        fid = "m2h-lid-c01-r1"
        self.assertTrue(rg.keep_v1(self.runs, fid))
        self.assertTrue((self.runs / fid / "grading-v1" / "change-01" / "arm.diff").exists())
        self.assertFalse((self.runs / fid / "grading").exists())
        write(self.runs / fid / "grading" / "change-01" / "summary.json", {"items": {}})
        self.assertFalse(rg.keep_v1(self.runs, fid))  # already kept: the first stays, the new grading too
        self.assertTrue((self.runs / fid / "grading" / "change-01" / "summary.json").exists())


if __name__ == "__main__":
    unittest.main()
