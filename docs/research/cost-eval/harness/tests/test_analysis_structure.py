"""Tests for module count and coupling by snapshot (analysis_structure.py): which files are modules, lines per
module, import edges between the project's own modules, and reading snapshots from a volume.

Run from the harness folder: python3.12 -m unittest discover -s tests
"""

import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import analysis_structure as st  # noqa: E402

PKG = {
    "pkg/__init__.py": "",
    "pkg/__main__.py": "from pkg.app import main\n\nmain()\n",
    "pkg/app.py": "import json\nfrom . import db\nfrom .rules import check\nimport pkg.util\n\n\ndef main():\n"
                  "    from pkg import extra\n    return db, check, extra\n",
    "pkg/db.py": "import sqlite3\n\n\n\nCONN = None\n",
    "pkg/rules.py": "from .db import CONN\nfrom pkg import db\n\n\ndef check():\n    return CONN\n",
    "pkg/util.py": "X = 1\n",
    "pkg/extra.py": "from .. import nothing_above\n",
    "pkg/broken.py": "def oops(:\n    pass\n",
    "tests/test_app.py": "from pkg import app\n\n\ndef test_it():\n    assert app\n",
    "tests/conftest.py": "import pkg.db\n",
    "pkg/test_inline.py": "import pkg.app\n",
}


class Paths(unittest.TestCase):
    def test_test_and_source(self):
        self.assertTrue(st.is_test_path("tests/test_app.py"))
        self.assertTrue(st.is_test_path("pkg/test_inline.py"))
        self.assertTrue(st.is_test_path("conftest.py"))
        self.assertTrue(st.is_source_path("pkg/app.py"))
        self.assertFalse(st.is_source_path("tests/helpers.py"))
        self.assertFalse(st.is_source_path(".venv/lib/x.py"))
        self.assertFalse(st.is_source_path("README.md"))

    def test_module_names(self):
        self.assertEqual(st.module_name("pkg/__init__.py"), "pkg")
        self.assertEqual(st.module_name("pkg/sub/mod.py"), "pkg.sub.mod")


class Measure(unittest.TestCase):
    def setUp(self):
        self.m = st.measure(PKG)

    def test_modules_exclude_tests(self):
        self.assertEqual(self.m["modules"], 8)  # __init__, __main__, app, db, rules, util, extra, broken
        self.assertEqual(self.m["test_files"], 3)

    def test_nonblank_lines(self):
        self.assertEqual(self.m["module_lines"]["pkg.db"], 2)
        self.assertEqual(self.m["module_lines"]["pkg.app"], 7)
        self.assertEqual(self.m["largest_module"], "pkg.app")
        total = sum(self.m["module_lines"].values())
        self.assertEqual(self.m["source_lines"], total)
        self.assertAlmostEqual(self.m["largest_share"], round(7 / total, 3))

    def test_edges(self):
        self.assertEqual(set(self.m["edge_list"]), {
            "pkg.__main__ -> pkg.app",
            "pkg.app -> pkg.db", "pkg.app -> pkg.rules", "pkg.app -> pkg.util", "pkg.app -> pkg.extra",
            "pkg.rules -> pkg.db",
        })
        self.assertEqual(self.m["edges"], 6)
        self.assertEqual(self.m["mean_fan_out"], round(6 / 8, 2))
        self.assertEqual(self.m["max_fan_in"], 2)  # pkg.db

    def test_src_layout_resolves_by_tail(self):
        files = {"src/benchtime/__init__.py": "", "src/benchtime/app.py": "from benchtime import service\n",
                 "src/benchtime/service.py": "import benchtime.db\n", "src/benchtime/db.py": "X = 1\n"}
        m = st.measure(files)
        self.assertEqual(set(m["edge_list"]), {"src.benchtime.app -> src.benchtime.service",
                                               "src.benchtime.service -> src.benchtime.db"})

    def test_flat_layout(self):
        m = st.measure({"app.py": "import db\nimport os\n", "db.py": "x = 1\n"})
        self.assertEqual(m["edge_list"], ["app -> db"])

    def test_empty_snapshot(self):
        m = st.measure({})
        self.assertEqual(m["modules"], 0)
        self.assertIsNone(m["largest_share"])


def tar_of(files: dict[str, str], prefix: str = "") -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for name, text in files.items():
            data = text.encode()
            info = tarfile.TarInfo(prefix + name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class Reading(unittest.TestCase):
    def test_tar_keeps_python_outside_skipped_folders(self):
        data = tar_of({"pkg/a.py": "x=1\n", ".venv/lib/b.py": "y\n", "pkg/__pycache__/a.py": "z\n",
                       "README.md": "hi\n", ".hidden/c.py": "w\n"}, prefix="./")
        self.assertEqual(st.files_from_tar(data), {"pkg/a.py": "x=1\n"})

    def test_git_snapshot_mounts_read_only_and_archives_the_commit(self):
        seen = []

        def runner(cmd):
            seen.append(cmd)
            return tar_of({"pkg/a.py": "x=1\n"})

        files = st.git_snapshot("vol-ws", "abc123", runner)
        self.assertEqual(files, {"pkg/a.py": "x=1\n"})
        self.assertIn("vol-ws:/ws:ro", seen[0])
        self.assertEqual(seen[0][-1], "abc123")
        self.assertIn("archive", seen[0])


def trajectory_dir(tmp: str, tid: str, changes: dict) -> Path:
    runs = Path(tmp)
    (runs / tid).mkdir(parents=True)
    (runs / tid / "trajectory.json").write_text(json.dumps(
        {"id": tid, "arm": "bare", "seed": "s", "volumes": {"workspace": f"ce-{tid}-ws"}, "changes": changes}))
    return runs


class Snapshots(unittest.TestCase):
    def test_growth_snapshot_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs = trajectory_dir(tmp, "g-x-1", {"0": {"commit": "a"}, "1": {"commit": "a"},
                                                 "2": {"commit": "a", "symptom": "not fired"}, "3": {"commit": "b"}})
            snaps = st.growth_snapshots(runs, "g-x-1", [0, 1, 2, 3, 4])
        self.assertEqual([s["note"] for s in snaps],
                         [None, "no new commit", "symptom change: not fired", None, "no such change"])

    def test_s3b_checks_checkpoint_against_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs = trajectory_dir(tmp, "s3b-bare-1", {"10": {"commit": "c10"}})
            same = tar_of({"benchtime/app.py": "import benchtime.db\n", "benchtime/db.py": "x=1\n"})
            r = st.run_s3b(runs, "bare", 1, lambda cmd: same)
        row = r["rows"][0]
        self.assertTrue(row["matches_commit"])
        self.assertEqual(row["edges"], 1)
        self.assertEqual(r["source"], "ce-g-s3b-bare-1-c10-ckpt:/app")

    def test_s3b_falls_back_to_the_workspace_history(self):
        def runner(cmd):
            if any("ckpt" in c for c in cmd):
                raise RuntimeError("no such volume")
            return tar_of({"benchtime/app.py": "x=1\n"})

        with tempfile.TemporaryDirectory() as tmp:
            runs = trajectory_dir(tmp, "s3b-bare-1", {"10": {"commit": "c10"}})
            r = st.run_s3b(runs, "bare", 1, runner)
        row = r["rows"][0]
        self.assertNotIn("error", row)
        self.assertEqual(row["modules"], 1)
        self.assertIn("workspace history", row["note"])


if __name__ == "__main__":
    unittest.main()
