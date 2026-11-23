"""regrade_from_diff.py: a graded Clowder fork whose volumes are gone, rebuilt from the diff its grading saved
(grading/change-NN/arm.diff) and graded again: a bare fork on its own stripped variant, a LID fork on a grader-stripped
copy of its full variant, so the graded tree is the one the first grading saw."""

from __future__ import annotations

import json
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


if __name__ == "__main__":
    unittest.main()
