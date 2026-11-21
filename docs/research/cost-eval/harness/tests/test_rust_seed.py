"""Tests for the Rust seed's tooling: the executor image's fetch context and the repository variants.

The fixture is a small made-up Cargo workspace built in a temporary git repository, so nothing from a real seed
appears here.
"""

import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS))
sys.path.insert(0, str(HARNESS / "images"))

import build_rust_image as bri  # noqa: E402
import clowder_variants as cv  # noqa: E402

SPECS = """# Widgets specs

- [x] **WID-CORE-001** A widget has a name.
- [x] **WID-CORE-002** A widget can be renamed.
- [ ] **UI-DRAW-010** The list shows every widget.
"""

LIB = """//! The widget library.

/// A widget. @spec WID-CORE-001
pub struct Widget { pub name: String }

/// @spec WID-CORE-002
// @spec UI-DRAW-010
impl Widget {
    /// Rename it (WID-CORE-002), keeping nothing else.
    pub fn rename(&mut self, to: &str) { self.name = to.to_string(); } // WID-CORE-002
    // See WID-CORE-001, WID-CORE-002 and UI-DRAW-010.
    pub fn label(&self) -> String { format!("{{{}}}", self.name) }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn braces() { assert_eq!(Widget { name: "a".into() }.label(), "{a}"); }
}
"""

DOC_TEST = """
#[cfg(test)]
mod doc_tests {
    /// Every row of the design's table stands in the code.
    /// @spec WID-CORE-001
    #[test]
    fn matches_the_design() {
        const DESIGN: &str = include_str!("../../../docs/hld.md");
        assert!(DESIGN.contains("HLD"), "{}", "}");
    }

    #[test]
    fn stays() { assert!(true); }
}
"""

MAIN_RS = """//! Every file here is a module of one binary.

mod common;

mod alpha;
mod beta;
mod gamma;
mod delta;
mod tables;
"""


def test_file(name: str, n: int) -> str:
    body = "\n".join(f"#[test]\nfn t{k}() {{ assert!(common::ok(), \"WID-CORE-001: holds\"); }}" for k in range(n))
    return f"use crate::common;\n\n// @spec WID-CORE-001\n{body}\n"


FILES = {
    "Cargo.toml": '[workspace]\nmembers = ["crates/widgets", "crates/widgets-ui"]\nresolver = "2"\n',
    "Cargo.lock": "# lockfile\nversion = 4\n",
    "README.md": ("# Widgets\n\nA widget tool.\n\nBuilt with [Linked-Intent Development](https://example.invalid/lid). "
                  "See [the design](docs/hld.md).\n\n## Using it\n\nRun it.\n\n- Use the arrow keys.\n- Read `AGENTS.md` first.\n"
                  "- Press q to quit.\n\n## Reading the arrow\n\n"
                  "Requirement IDs are cited in `// @spec` comments.\n\n```sh\ncargo test   # everything\n"
                  "python3 scripts/spec-test-coverage.py   # every spec has a test\n```\n\n"
                  "## Contributing\n\n```\n/plugin install linked-intent-dev\n```\n\nThen start from [`AGENTS.md`](AGENTS.md).\n\n"
                  "## License\n\nMIT\n"),
    "AGENTS.md": "# AGENTS.md\n\n## LID\n- Mode: Full\n- Version: 1.3.0\n",
    "CHANGELOG.md": "# Changelog\n\n- Widgets can be renamed (WID-CORE-002).\n",
    ".claude/settings.json": "{}\n",
    ".gitignore": "target/\n",
    "docs/intent/core/core-specs.md": SPECS,
    "docs/hld.md": "# HLD\n",
    "scripts/spec-test-coverage.py": "print('every @spec has a test')\n",
    "scripts/tool.py": "print('tool')\n",
    "crates/widgets/Cargo.toml": '[package]\nname = "widgets"\nversion = "0.1.0"\nedition = "2021"\n',
    "crates/widgets/src/lib.rs": LIB,
    "crates/widgets/src/more.rs": "pub fn more() -> u32 { 1 }\n" * 40 + DOC_TEST,
    "crates/widgets/tests/integration/tables.rs": 'const DESIGN: &str = include_str!("../../../../docs/hld.md");\n#[test]\nfn rows() { assert!(!DESIGN.is_empty()); }\n',
    "crates/widgets/tests/integration/main.rs": MAIN_RS,
    "crates/widgets/tests/integration/common/mod.rs": "pub fn ok() -> bool { true }\n",
    "crates/widgets/tests/integration/alpha.rs": test_file("alpha", 30),
    "crates/widgets/tests/integration/beta.rs": test_file("beta", 20),
    "crates/widgets/tests/integration/gamma.rs": test_file("gamma", 25),
    "crates/widgets/tests/integration/delta.rs": test_file("delta", 10),
    "crates/widgets/tests/fixtures/save.json": '{"v": 1}\n',
    "crates/widgets-ui/Cargo.toml": '[package]\nname = "widgets-ui"\nversion = "0.1.0"\nedition = "2021"\n\n[lib]\npath = "src/lib.rs"\n\n[[bin]]\nname = "wui"\npath = "src/app.rs"\n',
    "crates/widgets-ui/src/lib.rs": "pub fn ui() {}\n" * 30,
    "crates/widgets-ui/src/app.rs": "fn main() {}\n",
    "crates/widgets-ui/tests/integration/main.rs": "mod one;\nmod two;\n",
    "crates/widgets-ui/tests/integration/one.rs": test_file("one", 15).replace("use crate::common;\n", "mod common { pub fn ok() -> bool { true } }\n"),
    "crates/widgets-ui/tests/integration/two.rs": test_file("two", 15).replace("use crate::common;\n", "mod common { pub fn ok() -> bool { true } }\n"),
    "crates/widgets-ui/tests/solo.rs": "#[test]\nfn solo() {}\n",
}


def make_repo() -> tuple[Path, str]:
    d = Path(tempfile.mkdtemp())
    for path, text in FILES.items():
        f = d / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
    (d / "CLAUDE.md").symlink_to("AGENTS.md")
    run = lambda *a: subprocess.run(a, cwd=d, check=True, capture_output=True, text=True).stdout.strip()  # noqa: E731
    run("git", "init", "-q", "-b", "main")
    run("git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "add", "-A")
    run("git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "fixture")
    return d, run("git", "rev-parse", "HEAD")


class FetchContextTest(unittest.TestCase):
    def test_the_fetch_context_holds_manifests_lockfile_and_stub_targets_only(self):
        repo, commit = make_repo()
        files = bri.fetch_files(repo, commit)
        self.assertEqual(files["Cargo.lock"], FILES["Cargo.lock"].encode())
        self.assertEqual(files["crates/widgets/Cargo.toml"], FILES["crates/widgets/Cargo.toml"].encode())
        # every target cargo would discover or the manifest names, as a stub
        for stub in ("crates/widgets/src/lib.rs", "crates/widgets-ui/src/lib.rs", "crates/widgets-ui/src/app.rs"):
            self.assertIn(stub, files)
        self.assertIn(b"fn main", files["crates/widgets-ui/src/app.rs"])
        self.assertNotIn(b"Widget", files["crates/widgets/src/lib.rs"])  # none of the seed's code
        self.assertFalse(any("/tests/" in p or p.startswith("docs/") for p in files))


class ImageTest(unittest.TestCase):
    def test_the_image_pins_jj_and_gives_it_the_workspaces_identity(self):
        text = bri.DOCKERFILE.read_text()
        self.assertIn("ARG JJ_VERSION=0.46.0", text)
        self.assertIn("jj-vcs/jj/releases/download", text)
        self.assertIn('jj config set --user user.name "Lab Owner"', text)
        self.assertIn("jj config set --user user.email owner@example.invalid", text)


class SpecIdTest(unittest.TestCase):
    def test_the_spec_id_pattern_comes_from_the_specs(self):
        repo, commit = make_repo()
        tree = cv.read_tree(repo, commit)
        pattern = cv.spec_id_pattern(tree)
        for ok in ("WID-CORE-001", "UI-DRAW-010", "WID-CORE-002"):
            self.assertTrue(pattern.fullmatch(ok), ok)
        for no in ("UTC-5", "ISO-8601", "WID-CORE", "CORE-001"):
            self.assertIsNone(pattern.fullmatch(no), no)


class StripSpecCommentsTest(unittest.TestCase):
    def setUp(self):
        import re
        self.p = re.compile(r"\b(?:WID-CORE|UI-DRAW)-\d{3}[a-z]?\b")

    def strip(self, text):
        return cv.strip_spec_ids(text, self.p)

    def test_spec_annotation_lines_go_whole(self):
        out, n = self.strip("/// @spec WID-CORE-002\n// @spec UI-DRAW-010\n//! @spec WID-CORE-001, UI-DRAW-010\nfn f() {}\n")
        self.assertEqual(out, "fn f() {}\n")
        self.assertEqual(n["annotation lines"], 3)

    def test_an_annotation_at_the_end_of_prose_or_code_goes_and_the_rest_stays(self):
        out, _ = self.strip("/// A widget. @spec WID-CORE-001\nconst X: u8 = 1; // @spec WID-CORE-001, UI-DRAW-010\n")
        self.assertEqual(out, "/// A widget.\nconst X: u8 = 1;\n")

    def test_citations_go_from_comments_and_strings_and_the_prose_stays(self):
        src = ("    /// Rename it (WID-CORE-002), keeping nothing else.\n"
               "    let a = 1; // WID-CORE-002\n"
               "    // See WID-CORE-001, WID-CORE-002 and UI-DRAW-010.\n"
               "    // The order follows WID-CORE-001's rule.\n"
               '    assert!(ok, "WID-CORE-001: a widget has a name (UI-DRAW-010 amended)");\n')
        out, n = self.strip(src)
        self.assertEqual(out, "    /// Rename it, keeping nothing else.\n"
                              "    let a = 1;\n"
                              "    // The order follows the rule.\n"
                              '    assert!(ok, "a widget has a name");\n')
        self.assertEqual(n["lines dropped"], 1)
        self.assertIsNone(self.p.search(out))

    def test_a_rewritten_comment_loses_the_punctuation_that_only_framed_the_id(self):
        out, _ = self.strip("// WID-CORE-001 \u2014 keys while waking\n/// (WID-CORE-001): the copies\n"
                            "// The prompt's own field \u2014 WID-CORE-001, UI-DRAW-010\n// - a bullet citing WID-CORE-002\n")
        self.assertEqual(out, "// keys while waking\n/// the copies\n// The prompt's own field\n// - a bullet citing\n")

    def test_an_annotation_whose_ids_wrap_to_the_next_line_goes_too(self):
        out, _ = self.strip("/// Built afresh on every call. @spec\n/// WID-CORE-001, UI-DRAW-010\nfn f() {}\n")
        self.assertEqual(out, "/// Built afresh on every call.\nfn f() {}\n")

    def test_text_without_ids_is_untouched(self):
        src = 'let s = "{a}"; // a plain comment\n/// Docs.\n'
        self.assertEqual(self.strip(src), (src, {"annotation lines": 0, "lines changed": 0, "lines dropped": 0}))


class TestModuleLinesTest(unittest.TestCase):
    def test_a_cfg_test_module_is_counted_to_its_closing_brace(self):
        self.assertEqual(cv.cfg_test_lines(LIB), 5 + 1)  # the attribute line and the module's five lines
        self.assertEqual(cv.cfg_test_lines("fn f() {}\n"), 0)
        tricky = '#[cfg(test)]\nmod t {\n    const S: &str = "}}}";\n    const C: char = \'}\';\n    // }\n    fn r() -> &\'static str { r#"}"# }\n}\nfn after() {}\n'
        self.assertEqual(cv.cfg_test_lines(tricky), 7)


class VariantPlanTest(unittest.TestCase):
    def setUp(self):
        self.repo, self.commit = make_repo()
        self.tree = cv.read_tree(self.repo, self.commit)

    def test_held_out_tests_are_a_seeded_stratified_share_of_integration_test_files(self):
        held = cv.choose_held_out(self.tree, share=0.5, seed="s1")
        self.assertEqual(held, cv.choose_held_out(self.tree, share=0.5, seed="s1"))  # seeded
        by_dir = {}
        for p in held:
            by_dir.setdefault(p.rsplit("/", 1)[0], []).append(p)
        # half of each directory's test files, rounded half up: 4 -> 2, 2 -> 1, 1 -> 1
        self.assertEqual({d: len(v) for d, v in by_dir.items()},
                         {"crates/widgets/tests/integration": 2, "crates/widgets-ui/tests/integration": 1,
                          "crates/widgets-ui/tests": 1})
        for never in ("main.rs", "common/mod.rs", "fixtures/save.json", "tables.rs"):  # tables.rs reads the docs
            self.assertFalse(any(p.endswith(never) for p in held), never)
        self.assertGreater(len({tuple(cv.choose_held_out(self.tree, share=0.5, seed=f"s{k}")) for k in range(8)}), 1)
        small = cv.choose_held_out(self.tree, share=0.15, seed="s1")  # 15% of 4 rounds to 1; of 2 and 1, to 0
        self.assertEqual([p.rsplit("/", 1)[0] for p in small], ["crates/widgets/tests/integration"])

    def test_full_and_lid_are_jj_repositories_and_stripped_stays_plain_git(self):
        plans = cv.plan_variants(self.tree, held_out=[], seed="s1")
        self.assertEqual({n: v.vcs for n, v in plans.items()}, {"full": "jj", "lid": "jj", "stripped": "git"})
        calls = []
        runner = lambda cmd, **kw: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0, b"", b"")  # noqa: E731
        repo = Path(tempfile.mkdtemp())
        cv.load_volume(repo, "ce-cv-x-full", jj=True, runner=runner)
        self.assertIn("jj git init --colocate", calls[-1][-1])
        cv.load_volume(repo, "ce-cv-x-stripped", jj=False, runner=runner)
        self.assertNotIn("jj", calls[-1][-1])

    def test_the_variants_differ_only_as_designed(self):
        held = ["crates/widgets/tests/integration/beta.rs"]
        plans = cv.plan_variants(self.tree, held_out=held, seed="s1", ratio=0.6)
        full, lid, stripped = plans["full"], plans["lid"], plans["stripped"]
        self.assertEqual(full.files, lid.files)
        for v in (full, stripped):
            self.assertNotIn(held[0], v.files)
            self.assertNotIn("mod beta;", v.files["crates/widgets/tests/integration/main.rs"].decode())
        self.assertIn("docs/intent/core/core-specs.md", full.files)
        self.assertIn("AGENTS.md", full.files)
        self.assertEqual(full.symlinks, {"CLAUDE.md": "AGENTS.md"})
        for gone in ("docs/hld.md", "AGENTS.md", ".claude/settings.json", "scripts/spec-test-coverage.py"):
            self.assertNotIn(gone, stripped.files, gone)
        self.assertEqual(stripped.symlinks, {})
        self.assertIn("scripts/tool.py", stripped.files)
        lib = stripped.files["crates/widgets/src/lib.rs"].decode()
        self.assertNotIn("@spec", lib)
        self.assertNotRegex(lib, r"WID-CORE-\d")
        readme = stripped.files["README.md"].decode()
        for gone in ("Linked-Intent", "docs/", "@spec", "spec-test-coverage", "linked-intent", "AGENTS.md",
                     "## Contributing", "## Reading the arrow"):
            self.assertNotIn(gone, readme)
        for kept in ("## Using it", "## Testing", "cargo test   # everything", "## License",
                     "- Use the arrow keys.\n- Press q to quit."):
            self.assertIn(kept, readme)
        self.assertNotIn("\n\n\n", readme)

    def test_stripped_drops_the_tests_that_read_the_docs_and_keeps_the_build_whole(self):
        st = cv.plan_variants(self.tree, held_out=[], seed="s1", ratio=10.0)["stripped"]  # a ratio that thins nothing
        self.assertNotIn("crates/widgets/tests/integration/tables.rs", st.files)
        self.assertNotIn("mod tables;", st.files["crates/widgets/tests/integration/main.rs"].decode())
        more = st.files["crates/widgets/src/more.rs"].decode()
        self.assertNotIn("matches_the_design", more)
        self.assertNotIn("Every row of the design", more)
        self.assertIn("fn stays()", more)
        self.assertEqual(more.count("{"), more.count("}"))
        self.assertEqual(st.report["tests_reading_docs"],
                         ["crates/widgets/src/more.rs::matches_the_design", "crates/widgets/tests/integration/tables.rs"])
        self.assertIn("crates/widgets/tests/integration/tables.rs", cv.plan_variants(self.tree, held_out=[], seed="s1")["full"].files)

    def test_stripped_tests_are_thinned_toward_the_ratio_and_main_rs_follows(self):
        plans = cv.plan_variants(self.tree, held_out=[], seed="s1", ratio=0.6)
        st = plans["stripped"]
        report = st.report
        self.assertAlmostEqual(report["test_lines"] / report["source_lines"], 0.6, delta=0.25)
        kept = [p for p in st.files if p.startswith("crates/widgets/tests/integration/") and p.endswith(".rs")
                and not p.endswith(("main.rs", "common/mod.rs"))]
        main = st.files["crates/widgets/tests/integration/main.rs"].decode()
        for name in ("alpha", "beta", "gamma", "delta"):
            path = f"crates/widgets/tests/integration/{name}.rs"
            self.assertEqual(f"mod {name};" in main, path in st.files, name)
        self.assertIn("crates/widgets/tests/integration/common/mod.rs", st.files)
        self.assertIn("crates/widgets/tests/fixtures/save.json", st.files)
        self.assertEqual(sorted(report["tests_thinned"]), sorted(set(report["tests_thinned"])))
        self.assertTrue(report["tests_thinned"])
        self.assertLess(len(kept), 4)

    def test_sizes_are_counted_by_class(self):
        plans = cv.plan_variants(self.tree, held_out=[], seed="s1", ratio=0.6)
        sizes = cv.variant_sizes(plans["full"])
        self.assertEqual(set(sizes), {"source", "tests", "docs", "other"})
        self.assertGreater(sizes["docs"]["bytes"], 0)
        self.assertEqual(cv.variant_sizes(plans["stripped"])["docs"]["bytes"], len(plans["stripped"].files["README.md"])
                         + len(plans["stripped"].files["CHANGELOG.md"]))
        self.assertEqual(sizes["source"]["tokens_est"], sizes["source"]["bytes"] // 4)


class BuildRepoTest(unittest.TestCase):
    def test_a_variant_is_one_commit_with_no_history_from_the_source(self):
        repo, commit = make_repo()
        plans = cv.plan_variants(cv.read_tree(repo, commit), held_out=[], seed="s1", ratio=0.6)
        out = Path(tempfile.mkdtemp()) / "v"
        head = cv.write_repo(plans["stripped"], out)
        log = subprocess.run(["git", "-C", str(out), "log", "--format=%H %an %s"], capture_output=True, text=True).stdout.splitlines()
        self.assertEqual(len(log), 1)
        self.assertTrue(log[0].startswith(head))
        self.assertIn("Lab Owner", log[0])
        self.assertFalse((out / "docs").exists())
        self.assertEqual(head, cv.write_repo(plans["stripped"], Path(tempfile.mkdtemp()) / "v2"))  # deterministic
        full = Path(tempfile.mkdtemp()) / "f"
        cv.write_repo(plans["full"], full)
        self.assertTrue((full / "CLAUDE.md").is_symlink())


if __name__ == "__main__":
    unittest.main()


CARGO_OUT = """   Compiling widgets v0.1.0
    Finished `test` profile [optimized + debuginfo] target(s) in 41.2s
     Running unittests src/lib.rs (target/debug/deps/widgets-1)
running 2 tests
test tests::a ... ok
test tests::b ... ok
test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
     Running tests/integration/main.rs (target/debug/deps/integration-2)
running 3 tests
test alpha::t0 ... ok
test alpha::t1 ... FAILED
test beta::t0 ... ignored
test result: FAILED. 1 passed; 1 failed; 1 ignored; 0 measured; 0 filtered out; finished in 0.10s
"""


class CargoTestTest(unittest.TestCase):
    def test_totals_failures_and_whether_it_ran(self):
        r = cv.parse_cargo_test(CARGO_OUT, 101)
        self.assertEqual((r["passed"], r["failed"], r["ignored"], r["targets"], r["failing"]), (3, 1, 1, 2, ["alpha::t1"]))
        self.assertFalse(r["compile_failed"])
        self.assertFalse(r["ok"])
        self.assertTrue(cv.parse_cargo_test(CARGO_OUT.replace("FAILED", "ok").replace("1 failed", "0 failed"), 0)["ok"])
        broken = cv.parse_cargo_test("error[E0425]: cannot find value `x`\nerror: could not compile `widgets`\n", 101)
        self.assertTrue(broken["compile_failed"])
        self.assertEqual(broken["compile_errors"][0], "error[E0425]: cannot find value `x`")
        nothing = cv.parse_cargo_test("error: failed to create directory `/target/debug`\n", 101)
        self.assertFalse(nothing["ok"])
        self.assertEqual(nothing["targets"], 0)

    def test_the_shared_target_volume_is_handed_to_the_images_user_first(self):
        calls = []

        def runner(cmd, **kw):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, "test result: ok. 1 passed; 0 failed; 0 ignored\nEXIT=0\n", "")
        r, _ = cv.cargo_test("ce-cv-x-full", runner=runner)
        self.assertTrue(r["ok"])
        self.assertIn("--user", calls[0])
        self.assertIn("chown", " ".join(calls[0]))
        self.assertIn("--network", calls[1])
        self.assertIn("ce-cv-x-full:/src:ro", calls[1])
