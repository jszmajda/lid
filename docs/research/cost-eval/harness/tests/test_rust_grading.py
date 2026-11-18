"""Tests for grading a Rust library checkpoint: held-out tests for keeping, the arm's edits to existing tests, and
probes written as Rust tests against the arm's own API. Docker and the model roles are fakes."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from costeval import executor, grading, rust_grading as rg  # noqa: E402

MAIN = "//! one binary\n#![allow(clippy::all)]\n\nmod common;\n\nmod alpha;\nmod beta;\n"
PROBES = """# Probes

Preamble.

## Setups

### S0: A new game

Start a new game.

Each probe is independent.

## Probes

### NEW-01 Kittens can be renamed

#### P-NEW01-a

- **Applies:** from change 3
- **Needs:** none
- **Setup:** S0
- **Scenario:** Rename the first kitten to "Moss" and read its name back.
- **Expected observation:** The name reads "Moss".

#### P-NEW01-b

- **Applies:** from change 3
- **Needs:** none
- **Setup:** S0
- **Scenario:** Rename a kitten to an empty name.
- **Expected observation:** The rename is refused and the old name stays.

### NEW-02 Something later

#### P-NEW02-a

- **Applies:** from change 7
- **Needs:** none
- **Setup:** S0
- **Scenario:** Do something.
- **Expected observation:** It happens.
"""


def held_dir() -> Path:
    d = Path(tempfile.mkdtemp())
    files = {"crates/core/tests/integration/main.rs": MAIN,
             "crates/core/tests/integration/common/mod.rs": "pub fn ok() -> bool { true }\n",
             "crates/core/tests/integration/beta.rs": "use crate::common;\n#[test]\nfn b() { assert!(common::ok()); }\n",
             "crates/ui/tests/term.rs": "#[test]\nfn term() {}\n"}
    for p, t in files.items():
        (d / p).parent.mkdir(parents=True, exist_ok=True)
        (d / p).write_text(t)
    return d


class ExportTest(unittest.TestCase):
    def test_the_checkpoint_is_the_exact_commit_from_git_alone_without_jj_or_build_output(self):
        calls = []
        ck = rg.RustCheckpoint(name="cf-x-c03", commit="c1", image="img",
                               runner=lambda cmd, **kw: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0, "", ""))
        ck.export("ce-cf-x-ws")
        script = calls[0][-1]
        self.assertIn("cp -a /src/.git /work/app/.git", script)
        self.assertIn("git checkout -q -f --detach c1", script)
        self.assertIn("git clean -fdxq", script)
        self.assertNotIn("git clone", script)  # a commit the arm left on a detached HEAD is still found


class HeldOutTargetsTest(unittest.TestCase):
    def test_each_held_out_file_becomes_its_own_target_beside_the_original_helpers(self):
        files = rg.held_out_targets(held_dir(), ["crates/core/tests/integration/beta.rs", "crates/ui/tests/term.rs"])
        main = files["crates/core/tests/heldout_beta/main.rs"]
        self.assertIn("#![allow(clippy::all)]", main)
        self.assertIn("mod common;", main)
        self.assertIn("mod beta;", main)
        self.assertNotIn("mod alpha;", main)
        self.assertEqual(files["crates/core/tests/heldout_beta/beta.rs"], "use crate::common;\n#[test]\nfn b() { assert!(common::ok()); }\n")
        self.assertIn("crates/core/tests/heldout_beta/common/mod.rs", files)
        self.assertEqual(files["crates/ui/tests/heldout_term.rs"], "#[test]\nfn term() {}\n")
        self.assertEqual(rg.held_out_target_names(["crates/core/tests/integration/beta.rs", "crates/ui/tests/term.rs"]),
                         [("core", "heldout_beta"), ("ui", "heldout_term")])


KEEP_OK = """running 3 tests
test b ... ok
test c ... FAILED
test slow ... ignored, runs for minutes
test result: FAILED. 1 passed; 1 failed; 1 ignored; 0 measured; 0 filtered out
EXIT=101
"""
KEEP_BROKEN = "error[E0433]: failed to resolve: could not find `Kitten`\nerror: could not compile `core` (test \"heldout_term\")\nEXIT=101\n"


class KeepingTest(unittest.TestCase):
    def test_results_per_test_and_compile_failures_apart(self):
        r = rg.keeping_result([("core", "heldout_beta", KEEP_OK), ("ui", "heldout_term", KEEP_BROKEN)])
        self.assertEqual(r["targets"]["heldout_beta"]["tests"], {"b": "ok", "c": "FAILED", "slow": "ignored"})
        self.assertFalse(r["targets"]["heldout_beta"]["compile_failed"])
        self.assertTrue(r["targets"]["heldout_term"]["compile_failed"])
        self.assertIn("could not find `Kitten`", r["targets"]["heldout_term"]["errors"][0])
        self.assertEqual((r["passed"], r["failed"], r["compile_failed"]), (1, 1, ["heldout_term"]))
        self.assertAlmostEqual(r["share_passed"], 0.5)


NAME_STATUS = "M\tcrates/core/tests/integration/alpha.rs\nD\tcrates/core/tests/integration/gamma.rs\nA\tcrates/core/tests/integration/new.rs\nM\tcrates/core/src/lib.rs\nR087\tcrates/core/tests/integration/delta.rs\tcrates/core/tests/integration/delta2.rs\n"
NUMSTAT = "3\t10\tcrates/core/tests/integration/alpha.rs\n0\t40\tcrates/core/tests/integration/gamma.rs\n20\t0\tcrates/core/tests/integration/new.rs\n5\t5\tcrates/core/src/lib.rs\n1\t1\tcrates/core/tests/integration/delta.rs => crates/core/tests/integration/delta2.rs\n"


class TestEditsTest(unittest.TestCase):
    def test_pre_existing_test_files_edited_deleted_or_renamed_are_counted(self):
        counts = {("base", "crates/core/tests/integration/alpha.rs"): 6, ("head", "crates/core/tests/integration/alpha.rs"): 4,
                  ("base", "crates/core/tests/integration/gamma.rs"): 9,
                  ("base", "crates/core/tests/integration/delta.rs"): 2, ("head", "crates/core/tests/integration/delta2.rs"): 2}
        r = rg.test_edits(NAME_STATUS, NUMSTAT, lambda rev, path: counts.get((rev, path), 0))
        self.assertEqual(r["edited"], ["crates/core/tests/integration/alpha.rs"])
        self.assertEqual(r["deleted"], ["crates/core/tests/integration/gamma.rs"])
        self.assertEqual(r["renamed"], [["crates/core/tests/integration/delta.rs", "crates/core/tests/integration/delta2.rs"]])
        self.assertEqual(r["added"], ["crates/core/tests/integration/new.rs"])
        self.assertEqual((r["lines_removed"], r["lines_added"]), (51, 4))  # pre-existing test files only
        self.assertEqual((r["tests_before"], r["tests_after"], r["tests_removed"]), (17, 6, 11))


class ProbeTest(unittest.TestCase):
    def test_probe_files_and_names_are_safe_for_cargo(self):
        self.assertEqual(rg.probe_target("P-NEW01-a"), "probe_p_new01_a")

    def test_the_judge_reads_each_probes_test_and_its_output_as_numbered_entries(self):
        lines = rg.probe_log_lines({"P-NEW01-a": {"source": "fn t() {}", "output": "name: Moss"},
                                    "P-NEW01-b": {"source": None, "output": None}})
        self.assertEqual([(l["seq"], l["probe"], l["kind"]) for l in lines],
                         [(1, "P-NEW01-a", "test source"), (2, "P-NEW01-a", "test output"), (3, "P-NEW01-b", "missing")])
        text = rg.log_for_judge(lines)
        self.assertIn('"seq": 1', text)
        self.assertIn("name: Moss", text)
        long = rg.probe_log_lines({"P": {"source": "x", "output": "y" * (rg.MAX_OUTPUT + 50)}})
        self.assertIn("more characters", long[1]["text"])


class FakeCk:
    """A checkpoint whose files live in a dict, and whose shell commands are recorded."""

    def __init__(self):
        self.files, self.scripts = {}, []

    def put(self, path, text):
        self.files[path] = text

    def get(self, path):
        return self.files.get(path)

    def sh(self, script, stdin=None, check=True):
        self.scripts.append(script)
        return ""


class GradeProbesTest(unittest.TestCase):
    def test_extraction_execution_and_judgment_reuse_the_probe_format_and_verdicts(self):
        probeset = grading.parse_probes(PROBES)
        applicable = [p for p in probeset.probes if p.applies(3)]
        self.assertEqual([p.id for p in applicable], ["P-NEW01-a", "P-NEW01-b"])
        ck = FakeCk()
        calls = []

        def run_role(role, prompt, json_schema=None):
            calls.append({"role": role, "prompt": prompt, "schema": json_schema})
            if json_schema:  # the judge
                return SimpleNamespace(structured={"verdicts": [
                    {"probe": "P-NEW01-a", "verdict": "met", "evidence": [2], "reason": "The output shows the name Moss.", "cause": "none"},
                    {"probe": "P-NEW01-b", "verdict": "not met", "evidence": [4], "reason": "The empty name was accepted here.", "cause": "none"}]},
                    text="", usage=SimpleNamespace(reported_cost_usd=0.1, models={}), duration_s=1.0)
            if "reference.md" in prompt and "probes-" not in prompt:  # extraction
                ck.files["/work/out/reference.md"] = "use clowder_core::State;"
            else:  # an execution batch writes each probe's test and output
                for pid in ("P-NEW01-a", "P-NEW01-b"):
                    t = rg.probe_target(pid)
                    ck.files[f"/work/out/probes/{t}.rs"] = f"// {pid}\nfn t() {{}}"
                    ck.files[f"/work/out/probes/{t}.log"] = f"{pid} observed"
            return SimpleNamespace(structured=None, text="done", usage=SimpleNamespace(reported_cost_usd=0.2, models={}), duration_s=1.0)

        g = rg.RustGraders(image="img", roles_volume="roles", claude_code="v")
        out = Path(tempfile.mkdtemp())
        result = rg.grade_probes(ck, g, probeset, applicable, base="b0", out=out, volume="ckpt", run_role=run_role)
        self.assertEqual(result["items"]["NEW-01 Kittens can be renamed"]["verdict"], "not met")
        self.assertEqual(result["probes"], {"P-NEW01-a": "met", "P-NEW01-b": "not met"})
        extraction, execution, judge = calls[0], calls[1], calls[2]
        self.assertIn("git diff b0", extraction["prompt"])
        self.assertEqual(extraction["role"].model, g.extraction_model)
        self.assertEqual(execution["role"].model, g.execute_model)
        self.assertNotIn("Expected observation", ck.files["/work/out/probes-b01.md"])  # the executor never sees it
        self.assertIn("Expected observation", judge["prompt"])
        self.assertIn("P-NEW01-a observed", judge["prompt"])
        for c in calls:
            self.assertEqual(c["role"].isolation, executor.Isolation.for_public_seed(window="1m"))
        self.assertTrue((out / "verdicts.json").exists())

    def test_the_prompts_exist_and_fill(self):
        for name in ("extraction-rust.md", "grade-execute-rust.md", "grade-judge-rust.md"):
            self.assertTrue((grading.PROMPTS / name).exists(), name)
        p = rg.execution_prompt("b01")
        self.assertIn("/work/out/probes-b01.md", p)
        self.assertIn("--nocapture", p)


if __name__ == "__main__":
    unittest.main()


class GradeRustMainTest(unittest.TestCase):
    def test_a_fork_is_graded_for_keeping_test_edits_and_probes(self):
        import grade_rust
        root = Path(tempfile.mkdtemp())
        variants = root / "variants"
        hdir = held_dir()
        (variants).mkdir()
        import shutil
        shutil.copytree(hdir, variants / "held-out")
        (variants / "manifest.json").write_text(json.dumps({"held_out": ["crates/core/tests/integration/beta.rs"], "variants": {}}))
        seed = root / "seed"
        (seed / "hidden").mkdir(parents=True)
        (seed / "hidden" / "probes.md").write_text(PROBES)
        run = root / "runs" / "cf-x"
        run.mkdir(parents=True)
        (run / "trajectory.json").write_text(json.dumps({
            "id": "cf-x", "change": 3, "start_commit": "b0", "image": "img", "volumes": {"workspace": "ce-cf-x-ws"},
            "fork_of": {"variants": str(variants)}, "changes": {"3": {"commit": "c1"}}}))

        class Ck(FakeCk):
            def sh(self, script, stdin=None, check=True):
                self.scripts.append(script)
                if "--name-status" in script:
                    return NAME_STATUS
                if "--numstat" in script:
                    return NUMSTAT
                if "git show" in script:
                    return "2\n"
                if "--test heldout_beta" in script:
                    return KEEP_OK
                return ""

        ck = Ck()
        exported = []
        ck.export = lambda vol: exported.append(vol)
        ck.drop_target = lambda: None
        ck.volume = "ckpt"
        judged = []

        def run_role(role, prompt, json_schema=None):
            if json_schema:
                judged.append(prompt)
                return SimpleNamespace(structured={"verdicts": [
                    {"probe": p, "verdict": "couldn't exercise", "evidence": [], "reason": "No test was written for this probe.",
                     "cause": "execution"} for p in ("P-NEW01-a", "P-NEW01-b")]},
                    text="", usage=SimpleNamespace(reported_cost_usd=0.0, models={}), duration_s=0.1)
            return SimpleNamespace(structured=None, text="", usage=SimpleNamespace(reported_cost_usd=0.0, models={}), duration_s=0.1)

        rc = grade_rust.main(["--id", "cf-x", "--runs", str(root / "runs"), "--seed-dir", str(seed)],
                             checkpoint=lambda name, commit, image: ck, run_role=run_role)
        self.assertEqual(rc, 0)
        out = run / "grading" / "change-03"
        keeping = json.loads((out / "keeping.json").read_text())
        self.assertEqual(keeping["targets"]["heldout_beta"]["tests"], {"b": "ok", "c": "FAILED", "slow": "ignored"})
        self.assertEqual((out / "keeping" / "heldout_beta.log").read_text(), KEEP_OK)  # cargo's own output, for audit
        self.assertEqual(keeping["targets"]["heldout_beta"]["tests_expected"], 1)
        self.assertIn("/work/app/crates/core/tests/heldout_beta/main.rs", ck.files)
        edits = json.loads((out / "test_edits.json").read_text())
        self.assertEqual(edits["deleted"], ["crates/core/tests/integration/gamma.rs"])
        self.assertEqual(exported, ["ce-cf-x-ws"])
        verdicts = json.loads((out / "probes" / "verdicts.json").read_text())
        self.assertEqual(set(verdicts["probes"]), {"P-NEW01-a", "P-NEW01-b"})  # only the probes in force at change 3
        summary = json.loads((out / "summary.json").read_text())
        self.assertEqual(summary["keeping"]["passed"], 1)
        self.assertEqual(summary["items"], {"NEW-01 Kittens can be renamed": "couldn't exercise"})
