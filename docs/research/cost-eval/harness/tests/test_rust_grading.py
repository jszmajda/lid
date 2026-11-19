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
    def test_tests_not_built_are_counted_by_cause(self):
        r = rg.keeping_result([("core", "heldout_beta", KEEP_BROKEN), ("ui", "heldout_term", KEEP_BROKEN),
                               ("ui", "heldout_frame", KEEP_OK)],
                              {"heldout_beta": 5, "heldout_term": 3, "heldout_frame": 2},
                              {"heldout_beta": {"status": "not adapted", "reason": "E0382 at a.rs:3 is not one the rule adapts: borrow of moved value"},
                               "heldout_term": {"status": "not adapted", "reason": "E0063 at b.rs:4: no empty value for field `x` of type `Mood`"},
                               "heldout_frame": {"status": "built", "edits": []}})
        self.assertEqual(r["tests_not_built"], 8)
        self.assertEqual(r["tests_not_built_by_cause"], {"E0063 no empty value": 3, "E0382": 5})
        self.assertEqual(rg.not_built_cause("E0061 at x.rs:1 is not one the rule adapts: this enum variant takes 2 arguments"), "E0061")
        self.assertEqual(rg.not_built_cause("E0063 at x.rs:1: the literal has a base expression"), "E0063 base expression")
        self.assertEqual(rg.not_built_cause("still failing after 3 rounds"), "still failing after adaptation")
        self.assertEqual(rg.not_built_cause("E0063 at x.rs:2 is outside the held-out files"), "outside the held-out files")

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
        whole = "tick 1: catnip 3\n" * 8000 + "ALL-CASES: 8 of 8\n"  # 136k characters, as long as a real one
        self.assertEqual(rg.probe_log_lines({"P": {"source": "x", "output": whole}})[1]["text"], whole)

    def test_a_very_long_output_keeps_its_head_tail_and_every_deciding_line(self):
        ticks = [f"tick {i}: catnip {i}\n" for i in range(20000)]
        out = ("setup: 2 kittens\n" + "x" * 50000 + "\n" + "".join(ticks[:10000]) + "seed 3: joined 0, after removal close 2\n"
               + "CANNOT: no way to clear a nickname\n" + "".join(ticks[10000:]) + "ALL-CASES: no arrival in 8 of 8\n"
               + "y" * 50000 + "\nend\n")
        self.assertGreater(len(out), rg.MAX_OUTPUT)
        text = rg.probe_log_lines({"P": {"source": "x", "output": out}})[1]["text"]
        self.assertLess(len(text), len(out))
        self.assertTrue(text.startswith("setup: 2 kittens"))
        self.assertTrue(text.rstrip().endswith("end"))
        for line in ("seed 3: joined 0, after removal close 2", "CANNOT: no way to clear a nickname",
                     "ALL-CASES: no arrival in 8 of 8"):
            self.assertIn(line, text)
        self.assertIn("lines cut", text)


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
        self.assertIn("/work/out/arm.diff", extraction["prompt"])
        self.assertEqual(extraction["role"].model, g.extraction_model)
        self.assertEqual(execution["role"].model, g.execute_model)
        self.assertNotIn("Expected observation", ck.files["/work/out/probes-b01.md"])  # the executor never sees it
        self.assertIn("### S0: A new game\nStart a new game.", ck.files["/work/out/probes-b01.md"])  # the setups in full
        self.assertIn("Expected observation", judge["prompt"])
        self.assertIn("P-NEW01-a observed", judge["prompt"])
        for c in calls:
            self.assertEqual(c["role"].isolation, executor.Isolation.for_public_seed(window="1m"))
        self.assertTrue((out / "verdicts.json").exists())

    def test_a_grader_error_runs_once_more_blind_and_stays_missing_if_unresolved(self):
        import re
        probeset = grading.parse_probes(PROBES)
        applicable = [p for p in probeset.probes if p.applies(3)]
        ck, calls, state = FakeCk(), [], {}
        rulings = {  # batch -> probe -> (verdict, cause, fault)
            "b01": {"P-NEW01-a": ("couldn't exercise", "execution", "compile"),
                    "P-NEW01-b": ("couldn't exercise", "execution", "observation")},
            "x01": {"P-NEW01-a": ("couldn't exercise", "execution", "interface")},
            "x02": {"P-NEW01-b": ("met", "none", "none")}}
        usage = SimpleNamespace(reported_cost_usd=0.1, models={})

        def run_role(role, prompt, json_schema=None):
            calls.append({"role": role, "prompt": prompt, "schema": json_schema})
            if json_schema:
                return SimpleNamespace(structured={"verdicts": [
                    {"probe": pid, "verdict": v, "evidence": [] if v == "couldn't exercise" else [2],
                     "reason": "The output shows what this probe needed.", "cause": c, "fault": f}
                    for pid, (v, c, f) in rulings[state["bid"]].items()]}, text="", usage=usage, duration_s=1.0)
            m = re.search(r"probes-(\w+)\.md", prompt)
            if m:  # an execution batch writes each of its probes' test and output
                state["bid"] = m.group(1)
                for pid in re.findall(r"(?m)^## (P-\S+)", ck.files[f"/work/out/probes-{m.group(1)}.md"]):
                    t = rg.probe_target(pid)
                    ck.files[f"/work/out/probes/{t}.rs"] = f"// {pid}\nfn t() {{}}"
                    ck.files[f"/work/out/probes/{t}.log"] = f"{pid} observed in {m.group(1)}"
            else:
                ck.files["/work/out/reference.md"] = "use clowder_core::State;"
            return SimpleNamespace(structured=None, text="done", usage=usage, duration_s=1.0)

        g = rg.RustGraders(image="img", roles_volume="roles", claude_code="v")
        result = rg.grade_probes(ck, g, probeset, applicable, base="b0", out=Path(tempfile.mkdtemp()), volume="ckpt",
                                 run_role=run_role)
        executions = [re.search(r"probes-(\w+)\.md", c["prompt"]).group(1) for c in calls
                      if not c["schema"] and "probes-" in c["prompt"]]
        self.assertEqual(executions, ["b01", "x01", "x02"])  # each grader error once more, in a batch of its own
        self.assertNotIn("P-NEW01-b", ck.files["/work/out/probes-x01.md"])
        rerun = next(c for c in calls if "probes-x01.md" in c["prompt"])
        self.assertEqual(rerun["prompt"], rg.execution_prompt("x01"))  # the same instructions, nothing about the arm
        rm = [s for s in ck.scripts if s.startswith("rm -f") and "probe_p_new01_a" in s]
        self.assertEqual(len(rm), 1)  # the rerun starts from no test
        self.assertEqual(result["probes"], {"P-NEW01-a": "missing", "P-NEW01-b": "met"})
        self.assertEqual(result["missing"]["P-NEW01-a"]["fault"], "interface")
        self.assertEqual(result["missing"]["P-NEW01-a"]["first"]["fault"], "compile")
        self.assertEqual(result["reruns"]["P-NEW01-b"]["second"]["verdict"], "met")
        self.assertEqual(result["missing_by_fault"], {"interface": 1})
        self.assertEqual(result["items"]["NEW-01 Kittens can be renamed"]["verdict"], "missing")
        schema = json.loads(next(c["schema"] for c in calls if c["schema"]))
        fault = schema["properties"]["verdicts"]["items"]["properties"]["fault"]["enum"]
        self.assertEqual(fault, ["compile", "fixture", "interface", "observation", "none"])
        self.assertIn("confirmed", next(c["prompt"] for c in calls if c["schema"]))

    def test_a_ruling_must_name_the_grader_error_and_only_for_couldnt_exercise(self):
        batch = [p for p in grading.parse_probes(PROBES).probes if p.id == "P-NEW01-a"]
        lines = rg.probe_log_lines({"P-NEW01-a": {"source": "x", "output": "y"}})

        def problems(verdict, cause, fault, evidence=(2,)):
            return rg.check_verdicts({"verdicts": [{"probe": "P-NEW01-a", "verdict": verdict, "evidence": list(evidence),
                                                    "reason": "The output shows what this probe needed.", "cause": cause,
                                                    "fault": fault}]}, batch, lines)
        self.assertEqual(problems("couldn't exercise", "execution", "fixture", ()), [])
        self.assertTrue(problems("couldn't exercise", "execution", "none", ()))
        self.assertTrue(problems("not met", "none", "compile"))
        self.assertEqual(problems("not met", "none", "none"), [])

    def test_every_step_a_probe_is_about_is_the_builds_never_the_tests_own(self):
        execute = rg.execution_prompt("b01")
        self.assertIn("by calling the library's own API", execute)
        self.assertIn("never reproduce or simulate", execute)
        self.assertIn("print `CANNOT", execute)
        batch = [p for p in grading.parse_probes(PROBES).probes if p.id == "P-NEW01-a"]
        judge = rg.judge_prompt(batch, rg.probe_log_lines({"P-NEW01-a": {"source": "x", "output": "y"}}))
        self.assertIn("with its own logic", judge)
        self.assertIn("never \"met\" or \"not met\"", judge)

    def test_a_stand_in_for_what_the_build_cannot_show_is_cannot_never_a_reading(self):
        execute = rg.execution_prompt("b01")
        self.assertIn("no way to observe", execute)
        self.assertIn("rather than reading something else in its place", execute)
        batch = [p for p in grading.parse_probes(PROBES).probes if p.id == "P-NEW01-a"]
        judge = rg.judge_prompt(batch, rg.probe_log_lines({"P-NEW01-a": {"source": "x", "output": "y"}}))
        self.assertIn("stand-in", judge)
        self.assertIn("in place of what the probe asks about", judge)

    def test_the_prompts_exist_and_fill(self):
        for name in ("extraction-rust.md", "grade-execute-rust.md", "grade-judge-rust.md"):
            self.assertTrue((grading.PROMPTS / name).exists(), name)
        p = rg.execution_prompt("b01")
        self.assertIn("/work/out/probes-b01.md", p)
        self.assertIn("--nocapture", p)


if __name__ == "__main__":
    unittest.main()


BUILD_OK = '{"reason":"build-finished","success":true}\n'


class ProbeHelpersTest(unittest.TestCase):
    """Every executor gets the same tested fixture helpers: the snapshot's own test helper modules, placed beside the
    probe tests, built against the arm's code (with the compile-only adaptation) before they are offered."""

    def test_the_snapshots_own_helper_modules_are_found(self):
        self.assertEqual(rg.snapshot_helpers(held_dir()), {"core": {"common/mod.rs": "pub fn ok() -> bool { true }\n"}})

    def test_helpers_that_build_are_placed_and_offered_in_every_execution_prompt(self):
        class Ck(FakeCk):
            def sh(self, script, stdin=None, check=True):
                self.scripts.append(script)
                return BUILD_OK if "--no-run" in script else ""
        ck = Ck()
        rec = rg.place_probe_helpers(ck, rg.snapshot_helpers(held_dir()), sources=lambda: {})
        self.assertEqual(rec["core"]["status"], "built")
        self.assertEqual(ck.files["/work/app/crates/core/tests/probe_helpers/common/mod.rs"], "pub fn ok() -> bool { true }\n")
        self.assertIn("--test probe_helpers_check", next(s for s in ck.scripts if "--no-run" in s))
        self.assertTrue(any("rm -f" in s and "probe_helpers_check.rs" in s for s in ck.scripts))  # no stray target
        p = rg.execution_prompt("b01", rec)
        self.assertIn("crates/core/tests/probe_helpers/", p)
        self.assertIn('#[path = "probe_helpers/common/mod.rs"] mod common;', p)
        self.assertNotIn("probe_helpers", rg.execution_prompt("b01"))

    def test_helpers_that_dont_build_against_the_arms_code_are_withdrawn(self):
        broken = json.dumps({"reason": "compiler-message", "message": {
            "level": "error", "message": "cannot find function `wave`", "code": {"code": "E0425"}, "children": [],
            "spans": [{"is_primary": True, "file_name": "crates/core/tests/probe_helpers/common/mod.rs", "byte_start": 0,
                       "byte_end": 4, "line_start": 1, "expansion": None}]}}) + "\n"

        class Ck(FakeCk):
            def sh(self, script, stdin=None, check=True):
                self.scripts.append(script)
                return broken if "--no-run" in script else ""
        ck = Ck()
        rec = rg.place_probe_helpers(ck, rg.snapshot_helpers(held_dir()), sources=lambda: {})
        self.assertEqual(rec["core"]["status"], "not adapted")
        self.assertIn("E0425", rec["core"]["reason"])
        self.assertTrue(any("rm -rf" in s and "crates/core/tests/probe_helpers" in s for s in ck.scripts))
        self.assertNotIn("probe_helpers", rg.execution_prompt("b01", rec))


SCRIPT_KEPT = """## Change 3 — Reconsider a house rule

**Kept behaviour:** CLK-301, CLK-302.

## Change 4 — Let the party finish early

**Kept behaviour:** CLK-405.
"""


class KeptBehaviourTest(unittest.TestCase):
    def test_kept_behaviour_checks_are_reported_apart_from_new_intent(self):
        kept = rg.kept_behaviour_ids(SCRIPT_KEPT)
        self.assertEqual(kept, {"CLK-301", "CLK-302", "CLK-405"})
        new, checks = rg.split_items({"CLW-301 Switch rules": "met", "CLK-302 Charm is all or nothing": "not met"}, kept)
        self.assertEqual((new, checks), ({"CLW-301 Switch rules": "met"}, {"CLK-302 Charm is all or nothing": "not met"}))

    def test_items_met_leaves_missing_items_out(self):
        self.assertEqual(rg.items_met({"A": "met", "B": "not met", "C": "missing", "D": None}),
                         {"met": 1, "of": 2, "missing": 1, "conflicts": 0,
                          "interface_faults": {"not met (absent)": 0, "missing": 0}})
        self.assertEqual(rg.items_met({"B": "not met", "C": "missing"}, {"not met (absent)": ["B"], "missing": ["C", "Z"]}),
                         {"met": 0, "of": 1, "missing": 1, "conflicts": 0,
                          "interface_faults": {"not met (absent)": 1, "missing": 1}})


SOCIETY_BASE = """use crate::common::*;

#[test]
fn adopt_rule_spends_charm() {
    let mut s = setup();
    assert_eq!(s.charm(), 0.0, "the price is paid");
    assert!(s.is_adopted(Rule::A));
    assert!(!s.is_adopted(Rule::B), "siblings exclude each other");
    assert_eq!(saved(&s).rules, vec![Rule::A]);
}

#[test]
fn rules_survive_save() {
    assert_eq!(load(save(&state())).rules, state().rules);
}

#[test]
fn a_gone_test() {
    assert_eq!(count(), 1);
}
"""
SOCIETY_HEAD = """use crate::common::*;

#[test]
fn adopt_rule_spends_charm() {
    let mut s = setup();
    assert_eq!(
        s.charm(),
        0.0,
        "the price is still paid"
    );
    assert!(s.is_adopted(Rule::A));
    // assert!(!s.is_adopted(Rule::B), "siblings exclude each other");
    assert!(saved(&s).rules.len() >= 1);
}

#[test]
#[ignore]
fn rules_survive_save() {
    assert_eq!(load(save(&state())).rules, state().rules);
}
"""
SOC = "crates/core/tests/integration/society.rs"
KEPT_ASSERTIONS = {"changes": {"3": [
    {"keeps": "CLK-302", "file": SOC, "test": "adopt_rule_spends_charm", "assert": 'assert_eq!(s.charm(), 0.0, "the price is paid");'},
    {"keeps": "CLK-301", "file": SOC, "test": "adopt_rule_spends_charm", "assert": "assert!(s.is_adopted(Rule::A))"},
    {"keeps": "CLK-301", "file": SOC, "test": "adopt_rule_spends_charm", "assert": 'assert!(!s.is_adopted(Rule::B), "siblings exclude each other")'},
    {"keeps": "CLK-305", "file": SOC, "test": "adopt_rule_spends_charm", "assert": "assert_eq!(saved(&s).rules, vec![Rule::A])"},
    {"keeps": "CLK-305", "file": SOC, "test": "rules_survive_save", "assert": "assert_eq!(load(save(&state())).rules, state().rules)"},
    {"keeps": "CLK-303", "file": SOC, "test": "a_gone_test", "assert": "assert_eq!(count(), 1)"},
    {"keeps": "CLK-303", "file": SOC, "test": "adopt_rule_spends_charm", "assert": "assert_eq!(s.pep(), 3)"},
    {"keeps": "CLK-304", "file": "crates/core/tests/integration/old.rs", "test": "rules_survive_save",
     "assert": "assert_eq!(load(save(&state())).rules, state().rules)"},
    {"keeps": "CLK-506", "file": "crates/core/tests/integration/thinned.rs", "test": "t", "assert": "assert!(x)"}]}}


class VisibleAssertionsTest(unittest.TestCase):
    """Still-valid assertions in tests the arm can see: each one kept, deleted, or weakened at the change's end."""

    def audit(self):
        texts = {("b0", SOC): SOCIETY_BASE, ("c1", SOC): SOCIETY_HEAD,
                 ("b0", "crates/core/tests/integration/old.rs"): SOCIETY_BASE,
                 ("c1", "crates/core/tests/integration/new.rs"): SOCIETY_BASE}
        d = Path(tempfile.mkdtemp())
        (d / "kept-assertions.json").write_text(json.dumps(KEPT_ASSERTIONS))
        entries = rg.load_kept_assertions(d / "kept-assertions.json")[3]
        return rg.audit_visible_assertions(entries, lambda rev, path: texts.get((rev, path)), base="b0", head="c1",
                                           renamed={"crates/core/tests/integration/old.rs": "crates/core/tests/integration/new.rs"})

    def test_each_assertion_is_kept_deleted_or_weakened(self):
        a = self.audit()
        self.assertEqual([(x["status"], x["detail"]) for x in a["assertions"]], [
            ("kept", "present (layout and message aside)"),
            ("kept", "present (layout and message aside)"),
            ("deleted", "the assertion is gone from the test"),
            ("weakened", "the assertion changed: check what it now asserts"),
            ("weakened", "the test is now #[ignore]"),
            ("deleted", "the test is gone"),
            ("not found at the start", "the assertion isn't in the test at the change's start"),
            ("kept", "present (layout and message aside)"),
            ("not found at the start", "the file isn't in this checkout at the change's start (a variant without it)")])
        self.assertEqual(a["assertions"][3]["now"], ["assert!(saved(&s).rules.len() >= 1);"])
        self.assertEqual((a["kept"], a["deleted"], a["weakened"], a["not_found_at_start"]), (3, 2, 2, 2))
        self.assertEqual([(f["keeps"], f["status"]) for f in a["flagged"]],
                         [("CLK-301", "deleted"), ("CLK-305", "weakened"), ("CLK-305", "weakened"), ("CLK-303", "deleted")])

    def test_the_input_names_each_assertion_in_full(self):
        d = Path(tempfile.mkdtemp())
        (d / "k.json").write_text(json.dumps({"changes": {"3": [{"file": SOC, "test": "t"}]}}))
        with self.assertRaisesRegex(ValueError, "assert"):
            rg.load_kept_assertions(d / "k.json")


class CodeOnlyCheckoutTest(unittest.TestCase):
    """Graders read the same kind of checkout whatever the arm: code and tests, no docs or instruction files, and no
    history to find them in."""

    def test_what_the_variant_builder_strips_is_hidden_from_graders(self):
        paths = ["Cargo.toml", "README.md", "AGENTS.md", "CLAUDE.md", "crates/core/AGENTS.md", "docs/intent/a.md",
                 ".claude/settings.json", "tools/check.py", "tools/build.sh", "crates/core/src/lib.rs", "notes/plan.md"]
        hidden = rg.hidden_paths(paths, marked={"tools/check.py"}, symlinks={"GEMINI.md": "AGENTS.md", "link": "src"})
        self.assertEqual(hidden, [".claude/settings.json", "AGENTS.md", "CLAUDE.md", "GEMINI.md", "crates/core/AGENTS.md",
                                  "docs/intent/a.md", "tools/check.py"])

    def test_readme_and_spec_ids_are_stripped_as_the_variant_builder_strips_them(self):
        import re
        pattern = re.compile(r"\b(?:SIM-ENG)-\d{3,}[a-z]?\b")
        changed = rg.strip_texts({"crates/core/src/lib.rs": HEAD_LIB, "README.md": README, "crates/core/src/x.rs": "fn x() {}\n"},
                                 pattern)
        self.assertEqual(changed["crates/core/src/lib.rs"], "pub fn tick() {}\n/// Ticks.\npub fn t2() {}\n")
        self.assertNotIn("Linked-Intent", changed["README.md"])
        self.assertIn("A game.", changed["README.md"])
        self.assertNotIn("crates/core/src/x.rs", changed)  # nothing to strip, nothing rewritten
        # code tokens are never changed: comments and string contents are stripped as the builder strips them
        code = ('let id = "the tick (SIM-ENG-009)"; // the rule (SIM-ENG-009)\nfoo(bar(), 1)  ; // @spec SIM-ENG-009\n'
                '    assert!(ok,\n        "held as a set (SIM-ENG-009)"\n    );\n')
        self.assertEqual(rg.strip_texts({"a.rs": code}, pattern)["a.rs"],
                         'let id = "the tick"; // the rule\nfoo(bar(), 1)  ;\n    assert!(ok,\n        "held as a set"\n    );\n')

    def test_tests_that_read_the_docs_go_as_the_variant_builder_drops_them(self):
        import re
        pattern = re.compile(r"\b(?:SIM-ENG)-\d{3,}[a-z]?\b")
        texts = {"crates/core/tests/integration/main.rs": "mod common;\nmod tables;\nmod rules;\n",
                 "crates/core/tests/integration/tables.rs":
                     '#[test]\nfn rows() {\n    let d = include_str!("../../../../docs/intent/x.md");\n    assert!(!d.is_empty());\n}\n',
                 "crates/core/src/ach.rs": ('pub fn a() {}\n\n#[cfg(test)]\nmod tests {\n    /// The table.\n    #[test]\n'
                                            '    fn matches() {\n        let d = include_str!("../../../docs/intent/a.md");\n'
                                            '        assert!(d.len() > 0);\n    }\n}\n')}
        changed, removed, dropped = rg.transform_texts(texts, pattern)
        self.assertEqual(removed, ["crates/core/tests/integration/tables.rs"])
        self.assertEqual(changed["crates/core/tests/integration/main.rs"], "mod common;\nmod rules;\n")
        self.assertNotIn("include_str", changed["crates/core/src/ach.rs"])
        self.assertIn("pub fn a() {}", changed["crates/core/src/ach.rs"])
        self.assertEqual(dropped, ["crates/core/src/ach.rs::matches", "crates/core/tests/integration/tables.rs"])

    def test_the_extraction_reads_a_stripped_code_and_tests_diff_and_doc_changes_are_counted_apart(self):
        class Ck(FakeCk):
            def __init__(self):
                super().__init__()
                self.writes = []

            def sh(self, script, stdin=None, check=True):
                self.scripts.append(script)
                if "awk" in script:
                    self.writes.append((script.split("&&")[0], stdin))
                    return ""
                if rg.STREAM_MARK in script:  # fetch the files named on stdin
                    root = "base" if "/work/strip-base" in script else "head"
                    texts = {"head": {"docs/intent/x-specs.md": "- **SIM-ENG-009** a rule\n", "crates/core/src/lib.rs": HEAD_LIB,
                                      "README.md": README},
                             "base": {"crates/core/src/lib.rs": "pub fn tick() {} // @spec SIM-ENG-009\n"}}[root]
                    return "".join(f"{rg.STREAM_MARK} {f}\n{texts[f]}" for f in stdin.split() if f in texts)
                if "ls-files" in script and "specs" in script:
                    return "docs/intent/x-specs.md\n"
                if "ls-files" in script:
                    return "Cargo.toml\nAGENTS.md\ndocs/intent/x.md\ndocs/intent/x-specs.md\ncrates/core/src/lib.rs\nREADME.md\n"
                if "--numstat" in script:
                    return "5\t1\tdocs/intent/x.md\n2\t0\tREADME.md\n3\t3\tAGENTS.md\n10\t2\tcrates/core/src/lib.rs\n"
                if "grep -rlI" in script:
                    return "./crates/core/src/lib.rs\n"
                if "git grep -lI" in script and "docs/intent" not in script:
                    return "crates/core/src/lib.rs\ndocs/intent/x-specs.md\n"
                if "wc -c" in script:
                    return "1234\n"
                return ""
        import re
        ck = Ck()
        r = rg.prepare_for_graders(ck, "b0", "c1", spec_pattern=None)
        self.assertEqual(r["doc_changes"], {"files": 3, "lines_added": 10, "lines_removed": 4,
                                            "paths": ["AGENTS.md", "README.md", "docs/intent/x.md"]})
        self.assertEqual(r["hidden"], ["AGENTS.md", "docs/intent/x-specs.md", "docs/intent/x.md"])
        self.assertTrue(re.search(r["spec_id_pattern"], "SIM-ENG-009"))  # from the arm's own specs: new prefixes go too
        head, base = dict((w[0].strip(), w[1]) for w in ck.writes)["cd /work/app"], dict((w[0].strip(), w[1]) for w in ck.writes)["cd /work/strip-base"]
        self.assertIn("pub fn tick() {}\n/// Ticks.\n", head)
        self.assertNotIn("@spec", head + base)
        self.assertNotIn("Linked-Intent", head)
        self.assertNotIn("x-specs.md", head)  # hidden files are removed, not stripped
        self.assertIn("git archive b0", next(s for s in ck.scripts if "/work/strip-base" in s and "archive" in s))
        diff = next(s for s in ck.scripts if "/work/out/arm.diff" in s)
        self.assertIn("write-tree", diff)
        self.assertIn('git diff "$b" "$h"', diff)  # the two stripped trees, not the commits
        for excluded in (":(exclude,glob)**/*.md", ":(exclude)docs", ":(exclude).claude", ":(exclude,glob)**/AGENTS.md"):
            self.assertIn(excluded, diff)
        removal = next(s for s in ck.scripts if s.startswith("cd /work/app && rm -rf"))
        self.assertIn("'AGENTS.md'", removal)
        self.assertIn(".git", removal)  # no history to read docs from
        self.assertIn("'docs' '.claude'", removal)  # the directories too, not left empty
        self.assertIn("-type d -empty -delete", removal)
        self.assertIn("/work/strip-base", removal)
        self.assertIn("/work/out/arm.diff", rg.extraction_prompt([]))
        self.assertNotIn("git diff", rg.extraction_prompt([]))


HEAD_LIB = "pub fn tick() {} // @spec SIM-ENG-009\n/// Ticks (SIM-ENG-009).\npub fn t2() {}\n"
README = "# Clowder\n\nA game.\n\nBuilt with Linked-Intent Development; see AGENTS.md.\n"


IMPLEMENTATION_ITEMS = [("NEW-01", "Kittens can be renamed."), ("NEW-02", "Something later happens.")]


class ImplementationTest(unittest.TestCase):
    """The extraction records, per graded item, whether the arm's diff implements anything addressing it; an
    interface fault left after the rerun on an item it found absent is a confirmed absence."""

    def test_the_extraction_is_asked_about_each_graded_item(self):
        p = rg.extraction_prompt(IMPLEMENTATION_ITEMS)
        self.assertIn("NEW-01: Kittens can be renamed.", p)
        self.assertIn("/work/out/implementation.json", p)
        self.assertNotIn("implementation.json", rg.extraction_prompt([]))

    def test_each_items_record_is_checked_and_a_bad_one_is_unclear(self):
        statuses, problems = rg.check_implementation({"items": [
            {"item": "NEW-01", "status": "implemented", "evidence": [{"file": "src/a.rs", "symbols": ["rename"]}], "note": "x"},
            {"item": "NEW-02", "status": "absent", "evidence": [], "note": "nothing"},
            {"item": "NEW-09", "status": "absent", "evidence": [{"file": "a", "symbols": []}], "note": "x"}]},
            ["NEW-01", "NEW-02", "NEW-03"])
        self.assertEqual(statuses, {"NEW-01": "implemented", "NEW-02": "unclear", "NEW-03": "unclear"})
        self.assertEqual(len(problems), 3)  # NEW-02 cites nothing, NEW-09 isn't graded, NEW-03 has no record
        self.assertEqual(rg.check_implementation(None, ["NEW-01"])[0], {"NEW-01": "unclear"})

    def test_an_interface_fault_on_an_absent_item_is_not_met_and_on_an_implemented_one_missing(self):
        import re
        probeset = grading.parse_probes(PROBES)
        applicable = [p for p in probeset.probes if p.applies(7)]
        ck, calls = FakeCk(), []
        usage = SimpleNamespace(reported_cost_usd=0.1, models={})
        record = {"items": [
            {"item": "NEW-01", "status": "implemented", "evidence": [{"file": "crates/core/src/lib.rs", "symbols": ["rename"]}], "note": "rename"},
            {"item": "NEW-02", "status": "absent", "evidence": [{"file": "crates/core/src/lib.rs", "symbols": []}], "note": "nothing new"}]}

        def run_role(role, prompt, json_schema=None):
            calls.append({"prompt": prompt, "schema": json_schema})
            if json_schema:
                ids = sorted(set(re.findall(r"## (P-NEW\d+-[a-z])", prompt)))
                return SimpleNamespace(structured={"verdicts": [
                    {"probe": pid, "verdict": "couldn't exercise", "evidence": [], "reason": "No way to perform the step was found.",
                     "cause": "execution", "fault": "interface"} for pid in ids]}, text="", usage=usage, duration_s=1.0)
            if "probes-" not in prompt:
                ck.files["/work/out/reference.md"] = "use core::State;"
                ck.files["/work/out/implementation.json"] = json.dumps(record)
            return SimpleNamespace(structured=None, text="done", usage=usage, duration_s=1.0)

        out = Path(tempfile.mkdtemp())
        g = rg.RustGraders(image="img", roles_volume="roles", claude_code="v")
        result = rg.grade_probes(ck, g, probeset, applicable, base="b0", out=out, volume="ckpt", run_role=run_role,
                                 items=IMPLEMENTATION_ITEMS)
        self.assertIn("NEW-02: Something later happens.", calls[0]["prompt"])
        self.assertTrue(any(s.startswith("rm -f /work/out/implementation.json") for s in ck.scripts))  # executors never read it
        self.assertEqual(json.loads((out / "implementation.json").read_text())["statuses"], {"NEW-01": "implemented", "NEW-02": "absent"})
        self.assertEqual(result["probes"], {"P-NEW01-a": "missing", "P-NEW01-b": "missing", "P-NEW02-a": "not met"})
        self.assertIn("P-NEW02-a", result["absent"])
        self.assertEqual(result["items"]["NEW-02 Something later"]["verdict"], "not met")
        self.assertEqual(result["items"]["NEW-01 Kittens can be renamed"]["verdict"], "missing")
        self.assertEqual(result["interface_faults"], {"not met (absent)": ["NEW-02 Something later"],
                                                      "missing": ["NEW-01 Kittens can be renamed"]})


class GradedItemsTest(unittest.TestCase):
    def test_the_extraction_is_asked_about_live_items_with_probes_and_a_fork_leaves_out_the_start(self):
        import grade_rust
        from costeval import simulator
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from test_simulator import ORACLE
        seed = Path(tempfile.mkdtemp())
        (seed / "hidden").mkdir()
        (seed / "hidden" / "oracle.md").write_text(ORACLE)
        probes = [SimpleNamespace(item="BK-01 Orders"), SimpleNamespace(item="BK-10 Moving keeps the number"),
                  SimpleNamespace(item="CLK-1 Kept")]
        fork = grade_rust.graded_items(seed, 3, {"owner_scope": simulator.FORK_SCOPE}, probes)
        self.assertEqual([i for i, _ in fork], ["BK-10"])
        self.assertIn("keeps its number", fork[0][1])
        self.assertEqual([i for i, _ in grade_rust.graded_items(seed, 3, {}, probes)], ["BK-01", "BK-10"])
        self.assertEqual(grade_rust.graded_items(Path(tempfile.mkdtemp()), 3, {}, probes), [])


class ConflictTest(unittest.TestCase):
    """A "met" on an item the extraction found absent from the diff is a conflict: missing, flagged with both rulings."""

    def test_a_met_on_an_absent_item_is_a_conflict_out_of_the_share_with_both_rulings(self):
        import re
        probeset = grading.parse_probes(PROBES)
        applicable = [p for p in probeset.probes if p.applies(7)]
        ck = FakeCk()
        usage = SimpleNamespace(reported_cost_usd=0.1, models={})
        record = {"items": [
            {"item": "NEW-01", "status": "implemented", "evidence": [{"file": "crates/core/src/lib.rs", "symbols": ["rename"]}], "note": "rename"},
            {"item": "NEW-02", "status": "absent", "evidence": [{"file": "crates/core/src/lib.rs", "symbols": []}], "note": "nothing new"}]}

        def run_role(role, prompt, json_schema=None):
            if json_schema:
                ids = sorted(set(re.findall(r"## (P-NEW\d+-[a-z])", prompt)))
                return SimpleNamespace(structured={"verdicts": [
                    {"probe": pid, "verdict": "met", "evidence": [2], "reason": "The output shows what this probe needed.",
                     "cause": "none", "fault": "none"} for pid in ids]}, text="", usage=usage, duration_s=1.0)
            if "probes-" not in prompt:
                ck.files["/work/out/reference.md"] = "use core::State;"
                ck.files["/work/out/implementation.json"] = json.dumps(record)
            else:
                bid = re.search(r"probes-(\w+)\.md", prompt).group(1)
                for pid in re.findall(r"(?m)^## (P-\S+)", ck.files[f"/work/out/probes-{bid}.md"]):
                    ck.files[f"/work/out/probes/{rg.probe_target(pid)}.log"] = "observed"
            return SimpleNamespace(structured=None, text="done", usage=usage, duration_s=1.0)

        g = rg.RustGraders(image="img", roles_volume="roles", claude_code="v")
        result = rg.grade_probes(ck, g, probeset, applicable, base="b0", out=Path(tempfile.mkdtemp()), volume="ckpt",
                                 run_role=run_role, items=IMPLEMENTATION_ITEMS)
        self.assertEqual(result["probes"], {"P-NEW01-a": "met", "P-NEW01-b": "met", "P-NEW02-a": "missing (conflict)"})
        self.assertEqual(result["items"]["NEW-02 Something later"]["verdict"], "missing (conflict)")
        self.assertEqual(result["items"]["NEW-01 Kittens can be renamed"]["verdict"], "met")
        c = result["conflicts"]["NEW-02 Something later"]
        self.assertEqual(c["probes"]["P-NEW02-a"]["verdict"], "met")
        self.assertEqual(c["probes"]["P-NEW02-a"]["batch"], "b01")  # where to spot-check the judgment
        self.assertEqual((c["extraction"]["status"], c["extraction"]["note"]), ("absent", "nothing new"))
        met = rg.items_met({i: v["verdict"] for i, v in result["items"].items()}, result["interface_faults"])
        self.assertEqual((met["met"], met["of"], met["missing"], met["conflicts"]), (1, 1, 0, 1))

    def test_a_conflict_ranks_with_missing_below_a_decided_verdict(self):
        ps = [p for p in grading.parse_probes(PROBES).probes if p.item.startswith("NEW-01")]
        v = lambda a, b: grading.item_verdicts({"P-NEW01-a": a, "P-NEW01-b": b}, ps)["NEW-01 Kittens can be renamed"]["verdict"]
        self.assertEqual(v("met", grading.CONFLICT), grading.CONFLICT)
        self.assertEqual(v("not met", grading.CONFLICT), "not met")
        self.assertEqual(v("missing", grading.CONFLICT), grading.CONFLICT)


class KeepingOnlyTest(unittest.TestCase):
    def test_keeping_alone_is_run_again_and_the_rest_of_the_summary_kept(self):
        import grade_rust
        root = Path(tempfile.mkdtemp())
        import shutil
        shutil.copytree(held_dir(), root / "variants" / "held-out")
        (root / "variants" / "manifest.json").write_text(json.dumps({"held_out": ["crates/core/tests/integration/beta.rs"], "variants": {}}))
        run = root / "runs" / "cf-x"
        out = run / "grading" / "change-03"
        out.mkdir(parents=True)
        (run / "trajectory.json").write_text(json.dumps({
            "id": "cf-x", "change": 3, "start_commit": "b0", "image": "img", "volumes": {"workspace": "ws"},
            "fork_of": {"variants": str(root / "variants")}, "changes": {"3": {"commit": "c1"}}}))
        (out / "summary.json").write_text(json.dumps({"items": {"NEW-01": "met"}, "held_out_retention": {"passed": 0}}))
        (out / "keeping.json").write_text('{"old": true}')

        class Ck(FakeCk):
            volume = "ckpt"

            def sh(self, script, stdin=None, check=True):
                self.scripts.append(script)
                if "--no-run" in script:
                    return '{"reason":"build-finished","success":true}\n'
                return KEEP_OK if "--test heldout_beta" in script else ""

            def export(self, vol):
                pass

            def drop_target(self):
                pass
        calls = []
        rc = grade_rust.main(["--id", "cf-x", "--runs", str(root / "runs"), "--seed-dir", str(root), "--keeping-only",
                              "--no-classify"], checkpoint=lambda name, commit, image: Ck(),
                             run_role=lambda *a, **k: calls.append(a))
        self.assertEqual(rc, 0)
        self.assertEqual(calls, [])  # no extraction, execution, or judgment
        summary = json.loads((out / "summary.json").read_text())
        self.assertEqual(summary["items"], {"NEW-01": "met"})  # the probes' results stand
        self.assertEqual(summary["held_out_retention"]["passed"], 1)
        self.assertIn("keeping_rerun", summary)
        self.assertEqual(json.loads((out / "keeping.before-rerun.json").read_text()), {"old": True})
        self.assertNotIn("old", json.loads((out / "keeping.json").read_text()))


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
        (seed / "hidden" / "kept-assertions.json").write_text(json.dumps({"changes": {"3": [
            {"keeps": "CLK-1", "file": "crates/core/tests/integration/beta.rs", "test": "b", "assert": "assert!(common::ok())"}]}}))
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
                if "--no-run" in script:
                    return '{"reason":"build-finished","success":true}\n'
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
                     "cause": "execution", "fault": "observation"} for p in ("P-NEW01-a", "P-NEW01-b")]},
                    text="", usage=SimpleNamespace(reported_cost_usd=0.0, models={}), duration_s=0.1)
            executed.append(prompt)
            return SimpleNamespace(structured=None, text="", usage=SimpleNamespace(reported_cost_usd=0.0, models={}), duration_s=0.1)

        executed = []
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
        self.assertEqual(summary["held_out_retention"]["passed"], 1)
        self.assertNotIn("keeping", summary)
        # still couldn't exercise on the rerun: missing, out of the items-met share
        self.assertEqual(summary["items"], {"NEW-01 Kittens can be renamed": "missing"})
        self.assertEqual(summary["items_met"], {"met": 0, "of": 0, "missing": 1, "conflicts": 0,
                                                "interface_faults": {"not met (absent)": 0, "missing": 0}})
        self.assertEqual(summary["conflicts"], {})
        self.assertEqual(summary["doc_changes"]["files"], 0)  # the fake diff touches source and tests only
        self.assertTrue((out / "arm.diff").exists())  # the code diff the extraction read, kept for spot-checks
        self.assertTrue(any(".git" in s and s.startswith("cd /work/app && rm -rf") for s in ck.scripts))
        self.assertEqual(summary["missing_by_fault"], {"observation": 2})
        self.assertEqual(summary["kept_behaviour_checks"], {})
        self.assertEqual(summary["arm"], None)
        import hashlib
        self.assertEqual(summary["seed_files"]["probes_sha256"], hashlib.sha256(PROBES.encode()).hexdigest())
        self.assertIn("kept_assertions_sha256", summary["seed_files"])
        self.assertEqual(summary["probe_helpers"], {"core": "built"})  # the snapshot's helpers, offered to the executor
        self.assertTrue(any('#[path = "probe_helpers/common/mod.rs"] mod common;' in p for p in executed))
        self.assertTrue((out / "visible_assertions.json").exists())
        self.assertEqual(summary["visible_assertions"]["not_found_at_start"], 1)  # this fake git shows no source
