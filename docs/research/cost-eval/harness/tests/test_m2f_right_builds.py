"""m2f_right_builds.py: each change's right build (m2f-validation/builds.py's core and shell edits) as a patch a null
fork applies to the v2 variant, so the build can be graded exactly as a fork is (the instrument's positive control)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import m2f_right_builds as rb  # noqa: E402

BUILDS = '''
C = "crates/core/src/"
T = "crates/tui/src/"
CORE = {13: [(C + "lib.rs", "const MAX: u32 = 8;", "const MAX: u32 = 16;", 1)],
        14: [(C + "lib.rs", "fn level() {}", "fn level() { step(); }", 1)]}
SHELL = {13: [(T + "keys.rs", "notches(8)", "notches(16)", 2)],
         23: [(T + "card.rs", "draw_card();", "draw_compact_card();", 1)]}
'''
FILES = {"crates/core/src/lib.rs": "const MAX: u32 = 8;\nfn level() {}\n",
         "crates/tui/src/keys.rs": "fn a() { notches(8) }\nfn b() { notches(8) }\n",
         "crates/tui/src/card.rs": "fn c() { draw_card(); }\n"}


def repo(files: dict[str, str]) -> Path:
    d = Path(tempfile.mkdtemp())
    for p, t in files.items():
        (d / p).parent.mkdir(parents=True, exist_ok=True)
        (d / p).write_text(t)
    subprocess.run(["git", "init", "-q"], cwd=d, check=True)
    return d


class RightBuildsTest(unittest.TestCase):
    def setUp(self):
        self.builds_path = Path(tempfile.mkdtemp()) / "builds.py"
        self.builds_path.write_text(BUILDS)
        self.builds = rb.load_builds(self.builds_path)

    def test_a_right_build_is_its_changes_core_and_shell_edits(self):
        edits = rb.right_edits(self.builds)
        self.assertEqual(sorted(edits), [13, 14, 23])  # a control may edit one crate only
        self.assertEqual([e[0] for e in edits[13]], ["crates/core/src/lib.rs", "crates/tui/src/keys.rs"])

    def test_each_patch_applies_to_the_snapshot_and_gives_the_right_builds_files(self):
        for n, edits in rb.right_edits(self.builds).items():
            patch = rb.patch_for(edits, FILES.__getitem__)
            d = repo(FILES)
            (d / "p.diff").write_text(patch)
            subprocess.run(["git", "apply", "p.diff"], cwd=d, check=True, capture_output=True)
            if n == 13:
                self.assertEqual((d / "crates/core/src/lib.rs").read_text(), "const MAX: u32 = 16;\nfn level() {}\n")
                self.assertEqual((d / "crates/tui/src/keys.rs").read_text(), "fn a() { notches(16) }\nfn b() { notches(16) }\n")

    def test_an_edit_whose_count_doesnt_match_stops(self):
        with self.assertRaises(ValueError):
            rb.patch_for([("crates/tui/src/keys.rs", "notches(8)", "notches(16)", 1)], FILES.__getitem__)

    def test_the_cli_writes_a_patch_per_change_and_lists_them(self):
        out = Path(tempfile.mkdtemp())
        self.assertEqual(rb.main(["--builds", str(self.builds_path), "--out", str(out)], read=FILES.__getitem__), 0)
        self.assertEqual(sorted(p.name for p in out.glob("change-*.diff")), ["change-13.diff", "change-14.diff", "change-23.diff"])
        index = json.loads((out / "right-builds.json").read_text())
        self.assertEqual(index["13"]["files"], ["crates/core/src/lib.rs", "crates/tui/src/keys.rs"])

    def test_the_real_right_builds_apply_to_the_snapshot(self):
        builds = Path(__file__).resolve().parents[2] / "seeds" / "clowder" / "hidden" / "m2f-validation" / "builds.py"
        clowder = Path("/Users/jess/src/clowder")
        if not builds.exists() or not (clowder / ".git").exists():
            self.skipTest("no builds.py or Clowder repository")
        edits = rb.right_edits(rb.load_builds(builds))
        self.assertTrue(set(range(13, 21)) <= set(edits))
        read = rb.snapshot_reader(clowder, "86db995")
        for n, e in edits.items():
            patch = rb.patch_for(e, read)
            self.assertTrue(patch.startswith("--- a/crates/"), n)


if __name__ == "__main__":
    unittest.main()
