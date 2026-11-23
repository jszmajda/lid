"""m2h_right_builds.py: each M2h change's right build (m2h-validation/builds.mjs, all of the change's r<n>-* sets) as a
patch against the shared start, for a null fork's --result-patch (the instrument's positive control)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import m2h_right_builds as rb  # noqa: E402

BUILDS = r"""
import fs from 'node:fs'
const rep = (f, a, b) => {
  const s = fs.readFileSync(f, 'utf8'); const n = s.split(a).length - 1
  if (n !== 1) { console.error(`PATCH FAILED ${f}`); process.exit(1) }
  fs.writeFileSync(f, s.replace(a, () => b)); console.log('patched', f)
}
const add = (f, text) => { fs.writeFileSync(f, text); console.log('added', f) }
const sets = {
  'r1-api': () => rep('api/relay.js', 'MAX = 5', 'MAX = 1'),
  'r1-fe': () => rep('frontend/view.jsx', 'old view', 'new view'),
  'r2-fe': () => add('frontend/new.js', 'export const x = 1\n'),
  'w2': () => add('frontend/w2.js', 'export const w = 2\n'),
}
const BUILDS = { 1: { right: ['r1-api', 'r1-fe'], one_sided: ['r1-api'] }, 2: { right: ['w2', 'r2-fe'], one_sided: ['w2'] } }
if (process.argv[2] === '--declare') { console.log(JSON.stringify(BUILDS, null, 1)); process.exit(0) }
for (const k of process.argv.slice(2)) { if (!sets[k]) { console.error('no set ' + k); process.exit(1) } sets[k]() }
"""


def start_repo() -> Path:
    d = Path(tempfile.mkdtemp())
    (d / "api").mkdir()
    (d / "frontend").mkdir()
    (d / "api" / "relay.js").write_text("export const MAX = 5\n")
    (d / "frontend" / "view.jsx").write_text("old view\n")
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "Start"]):
        subprocess.run(cmd, cwd=d, check=True)
    return d


@unittest.skipUnless(shutil.which("node"), "no node")
class RightBuildsTest(unittest.TestCase):
    def setUp(self):
        self.builds = Path(tempfile.mkdtemp()) / "builds.mjs"
        self.builds.write_text(BUILDS)

    def test_each_changes_right_build_is_the_one_builds_mjs_declares(self):
        # builds.mjs --declare: {"<n>": {"right": [sets], "one_sided": [...], ...}}; changes 4 and 8 take a w-set too
        self.assertEqual(rb.declared_right(self.builds), {1: ["r1-api", "r1-fe"], 2: ["w2", "r2-fe"]})

    def test_each_patch_applies_to_the_start_and_gives_the_right_build(self):
        repo, out = start_repo(), Path(tempfile.mkdtemp())
        rb.write_patches(repo, self.builds, out, runner=rb.local_runner)
        self.assertEqual(sorted(p.name for p in out.glob("change-*.diff")), ["change-01.diff", "change-02.diff"])
        index = json.loads((out / "right-builds.json").read_text())
        self.assertEqual(index["1"]["sets"], ["r1-api", "r1-fe"])
        self.assertEqual(index["2"]["files"], ["frontend/new.js", "frontend/w2.js"])  # added files are in the patch too
        self.assertEqual(index["2"]["sets"], ["w2", "r2-fe"])
        check = start_repo()
        for name in ("change-01.diff", "change-02.diff"):
            subprocess.run(["git", "apply", "--check", str(out / name)], cwd=check, check=True)
        subprocess.run(["git", "apply", str(out / "change-01.diff")], cwd=check, check=True)
        self.assertEqual((check / "api" / "relay.js").read_text(), "export const MAX = 1\n")
        self.assertEqual((repo / "api" / "relay.js").read_text(), "export const MAX = 5\n")  # the start is untouched

    def test_a_set_that_fails_stops(self):
        self.builds.write_text(BUILDS.replace("'MAX = 5'", "'MAX = 9'"))
        with self.assertRaises(RuntimeError):
            rb.write_patches(start_repo(), self.builds, Path(tempfile.mkdtemp()), runner=rb.local_runner)

    def test_the_real_builds_declare_twelve_right_builds(self):
        real = Path("/Users/jess/src/lid-cost-eval/docs/research/cost-eval/seeds/opengym/hidden/m2h-validation/builds.mjs")
        if not real.exists():
            self.skipTest("no builds.mjs")
        declared = rb.declared_right(real)
        self.assertEqual(sorted(declared), list(range(1, 13)))
        self.assertEqual((declared[4], declared[8]), (["w4", "r4-api"], ["w8", "r8-api"]))


if __name__ == "__main__":
    unittest.main()
