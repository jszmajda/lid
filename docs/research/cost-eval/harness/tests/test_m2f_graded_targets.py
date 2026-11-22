"""Tests for m2f_graded_targets.py: the Rust test-function remover and keeper, and the graded targets it builds from a
snapshot (dependency probes appended to their host modules, held-out test functions kept alone), on synthetic Rust."""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS))

import m2f_graded_targets as gt  # noqa: E402

HIDDEN = HARNESS.parent / "seeds" / "clowder" / "hidden"

HOST = '''//! A host module.
use clowder_core::GameState;

const WIDE: u16 = 120;

/// A helper with braces in its literals: "}"
fn fresh() -> GameState {
    let _s = "}";
    let _c = '{';
    let _r = r#"} " {"#;
    /* a block comment with a } and /* a nested { */ */
    GameState::new(1)
}

fn longest<'a>(a: &'a str, b: &'a str) -> &'a str {
    if a.len() > b.len() { a } else { b }
}

// ---- a section header that stays ----

/// The first test.
/// It has two doc lines.
#[test]
fn first_test() {
    let s = fresh();
    assert_eq!(s.ticks, 0, "a brace }} in a message");
}

#[test]
#[should_panic(
    expected = "a ] bracket and a } brace"
)]
fn panics() {
    panic!("a ] bracket and a } brace");
}

struct Helper {
    x: u32,
}

impl Helper {
    fn new() -> Self { Helper { x: WIDE as u32 } }
}

#[test]
#[ignore]
fn ignored_test() {
    let _h = Helper::new();
    let _ = "#[test] fn fake() {}";
    // #[test]
    // fn commented_out() {}
}

mod inner {
    #[test]
    fn nested_test() {
        let _ = b'}';
        let _ = br"}";
    }

    pub fn kept_inner() {}
}
'''


def balanced(text: str) -> bool:
    depth = 0
    for c in gt.mask(text):
        depth += {"{": 1, "}": -1}.get(c, 0)
        if depth < 0:
            return False
    return depth == 0


class MaskTest(unittest.TestCase):
    def test_comments_strings_chars_and_raw_strings_hide_their_braces_and_keep_their_length(self):
        for text in ['let s = "a } b"; // }\n', "let c = '}'; let d = '\\''; let e = b'{';\n",
                     'let r = r##"a "# } b"##; let q = br#"{"#;\n', "/* } /* { */ } */ fn f() {}\n",
                     'let s = "an \\" escaped } quote";\n', "let s = c\"}\";\n"]:
            masked = gt.mask(text)
            self.assertEqual(len(masked), len(text))
            self.assertEqual(masked.count("\n"), text.count("\n"))
            self.assertEqual(masked.count("}"), masked.count("{"), text)

    def test_a_lifetime_is_not_a_char_literal(self):
        text = "fn f<'a>(x: &'a str) -> &'a str { x }\nfn g() { let c = 'x'; }\n"
        self.assertEqual(gt.mask(text).count("{"), 2)
        self.assertEqual(gt.mask(text).count("}"), 2)
        self.assertIn("fn g()", gt.mask(text))

    def test_a_raw_identifier_is_not_a_raw_string(self):
        text = 'fn r#type() { let r#match = "}"; }\n'
        self.assertEqual(gt.mask(text).count("}"), 1)


class TestFunctionsTest(unittest.TestCase):
    def test_every_test_function_is_found_with_its_doc_comments_and_attributes(self):
        found = gt.test_functions(HOST)
        self.assertEqual([t.name for t in found], ["first_test", "panics", "ignored_test", "nested_test"])
        first = HOST[found[0].start:found[0].end]
        self.assertTrue(first.startswith("/// The first test."))
        self.assertTrue(first.rstrip().endswith("}"))
        self.assertIn("#[should_panic(", HOST[found[1].start:found[1].end])
        self.assertIn("#[ignore]", HOST[found[2].start:found[2].end])

    def test_a_test_attribute_in_a_string_or_a_comment_is_not_a_test(self):
        self.assertEqual(gt.test_functions('fn f() { let _ = "#[test] fn fake() {}"; }\n// #[test]\n// fn c() {}\n'), [])

    def test_removing_every_test_keeps_the_helpers_and_balances_the_braces(self):
        out = gt.remove_tests(HOST)
        for kept in ("fn fresh()", "fn longest<'a>", "struct Helper", "impl Helper", "pub fn kept_inner() {}",
                     "// ---- a section header that stays ----", "use clowder_core::GameState;", "const WIDE"):
            self.assertIn(kept, out)
        for gone in ("first_test", "panics", "ignored_test", "nested_test", "The first test.", "should_panic",
                     "#[ignore]", "#[test]"):
            self.assertNotIn(gone, out)
        self.assertTrue(balanced(out))
        self.assertNotIn("\n\n\n", out)
        self.assertEqual(gt.test_functions(out), [])

    def test_keeping_named_tests_removes_the_rest_and_an_unknown_name_is_refused(self):
        out = gt.keep_tests(HOST, {"panics", "nested_test"})
        self.assertEqual([t.name for t in gt.test_functions(out)], ["panics", "nested_test"])
        self.assertIn('expected = "a ] bracket and a } brace"', out)
        self.assertIn("fn fresh()", out)
        self.assertNotIn("The first test.", out)
        self.assertTrue(balanced(out))
        with self.assertRaises(ValueError):
            gt.keep_tests(HOST, {"panics", "no_such_test"})

    def test_a_file_with_no_tests_is_unchanged(self):
        text = "fn a() {}\n\nfn b() {}\n"
        self.assertEqual(gt.remove_tests(text), text)


MAIN = "//! The suite.\n#![allow(clippy::all)]\n\nmod common;\nmod host;\nmod other;\nmod uses_other;\n"
INTEGRATION = "crates/tui/tests/integration"
SNAP = {
    f"{INTEGRATION}/main.rs": MAIN,
    f"{INTEGRATION}/common/mod.rs": "pub fn ok() -> bool { true }\n",
    f"{INTEGRATION}/host.rs": HOST,
    f"{INTEGRATION}/other.rs": "pub fn shared() -> u32 { 1 }\n\n#[test]\nfn other_test() {}\n",
    f"{INTEGRATION}/uses_other.rs": ("use crate::other::shared;\n\n#[test]\nfn a() {\n    assert_eq!(shared(), 1);\n}\n\n"
                                     "#[test]\nfn b() {}\n"),
    "crates/tui/tests/term.rs": "fn helper() -> u8 { 2 }\n\n#[test]\nfn term() {}\n",
}
PROBE_P = "\n// ---- probe ----\n#[test]\nfn probe_m2f_p() {\n    assert!(fresh().ticks == 0);\n}\n"
PROBE_Q = "\n#[test]\nfn probe_m2f_q() {\n    assert_eq!(helper(), 2);\n}\n"
MAP = {"p.rs": (13, f"{INTEGRATION}/host.rs"), "q.rs": (14, "crates/tui/tests/term.rs")}
HOLDOUTS = {"tests": [
    {"change": 20, "status": "graded", "test": "tui/tests/integration/uses_other.rs::a"},
    {"change": 14, "status": "retired", "test": "tui/tests/integration/host.rs::first_test"},
    {"change": 14, "status": "retired", "test": "tui/tests/integration/host.rs::panics"}]}


def probes_dir(files: dict[str, str] | None = None) -> Path:
    d = Path(tempfile.mkdtemp())
    for name, text in (files or {"p.rs": PROBE_P, "q.rs": PROBE_Q}).items():
        (d / name).write_text(text)
    (d / "run.sh").write_text("#!/bin/sh\n")  # not a probe
    return d


class BuildTest(unittest.TestCase):
    def build(self, **kw):
        args = {"snapshot": gt.DictSnapshot(SNAP, commit="abc123"), "probes_dir": probes_dir(), "holdouts": HOLDOUTS,
                "probe_map": MAP}
        args.update(kw)
        return gt.build(**args)

    def test_a_probe_goes_into_its_host_module_stripped_of_its_own_tests_beside_the_directorys_helpers(self):
        files, entries = self.build()
        by = {e["target"]: e for e in entries}
        e = by["m2f_c13_probe_p"]
        self.assertEqual((e["kind"], e["change"], e["status"], e["tests"], e["module"], e["crate"]),
                         ("dependency probe", 13, "graded", ["probe_m2f_p"], "host", "tui"))
        dest = "crates/tui/tests/m2f_c13_probe_p"
        self.assertEqual(sorted(e["files"]), sorted([f"{dest}/main.rs", f"{dest}/common/mod.rs", f"{dest}/host.rs"]))
        main = files[f"{dest}/main.rs"]
        self.assertIn("#![allow(clippy::all)]", main)  # the original main.rs's crate attributes
        self.assertIn("#![allow(dead_code, unused_imports)]", main)
        self.assertIn("mod common;", main)
        self.assertIn("mod host;", main)
        self.assertNotIn("mod other;", main)
        host = files[f"{dest}/host.rs"]
        self.assertEqual([t.name for t in gt.test_functions(host)], ["probe_m2f_p"])
        self.assertIn("fn fresh()", host)
        self.assertTrue(host.rstrip().endswith(PROBE_P.rstrip()))
        self.assertEqual(files[f"{dest}/common/mod.rs"], SNAP[f"{INTEGRATION}/common/mod.rs"])
        self.assertEqual(e["source"]["host"], f"{INTEGRATION}/host.rs")
        self.assertEqual(e["source"]["probe"], "p.rs")
        self.assertEqual(e["source"]["commit"], "abc123")

    def test_a_probe_whose_host_is_a_target_of_its_own_becomes_one_file(self):
        files, entries = self.build()
        e = {x["target"]: x for x in entries}["m2f_c14_probe_q"]
        self.assertEqual(e["files"], ["crates/tui/tests/m2f_c14_probe_q.rs"])
        text = files["crates/tui/tests/m2f_c14_probe_q.rs"]
        self.assertEqual([t.name for t in gt.test_functions(text)], ["probe_m2f_q"])
        self.assertIn("fn helper()", text)
        self.assertEqual(e["module"], None)

    def test_held_out_tests_are_kept_alone_with_their_files_helpers_and_the_modules_they_reach(self):
        files, entries = self.build()
        by = {e["target"]: e for e in entries}
        e = by["m2f_c20_heldout_uses_other"]
        self.assertEqual((e["kind"], e["change"], e["status"], e["tests"], e["module"]),
                         ("held-out test", 20, "graded", ["a"], "uses_other"))
        dest = "crates/tui/tests/m2f_c20_heldout_uses_other"
        main = files[f"{dest}/main.rs"]
        self.assertIn("mod other;", main)  # the module reaches crate::other
        self.assertIn("mod uses_other;", main)
        self.assertEqual([t.name for t in gt.test_functions(files[f"{dest}/uses_other.rs"])], ["a"])
        self.assertEqual(gt.test_functions(files[f"{dest}/other.rs"]), [])  # a sibling's own tests don't come along
        self.assertIn("pub fn shared()", files[f"{dest}/other.rs"])
        retired = by["m2f_c14_heldout_host"]
        self.assertEqual((retired["status"], sorted(retired["tests"])), ("retired", ["first_test", "panics"]))
        self.assertEqual(len(entries), 4)

    def test_what_the_seed_doesnt_match_is_refused(self):
        with self.assertRaisesRegex(ValueError, "extra.rs"):
            self.build(probes_dir=probes_dir({"p.rs": PROBE_P, "q.rs": PROBE_Q, "extra.rs": PROBE_Q}))
        with self.assertRaisesRegex(ValueError, "q.rs"):
            self.build(probes_dir=probes_dir({"p.rs": PROBE_P}))
        with self.assertRaisesRegex(ValueError, "no #\\[test\\]"):
            self.build(probes_dir=probes_dir({"p.rs": "fn nothing() {}\n", "q.rs": PROBE_Q}))
        with self.assertRaisesRegex(ValueError, "no_such"):
            self.build(holdouts={"tests": [{"change": 20, "status": "graded",
                                            "test": "tui/tests/integration/uses_other.rs::no_such"}]})
        with self.assertRaisesRegex(ValueError, "missing.rs"):
            self.build(probe_map={**MAP, "p.rs": (13, f"{INTEGRATION}/missing.rs")})
        with self.assertRaisesRegex(ValueError, "p.rs.*fresh"):  # a probe defining an item its host already has
            self.build(probes_dir=probes_dir({"p.rs": PROBE_P + "\nfn fresh() {}\n", "q.rs": PROBE_Q}))

    def test_graded_json_lists_every_target_and_a_rebuild_replaces_the_last(self):
        files, entries = self.build()
        out = Path(tempfile.mkdtemp()) / "graded"
        gt.write(out, files, entries)
        listed = json.loads((out / "graded.json").read_text())
        self.assertIsInstance(listed, list)
        self.assertEqual({tuple(sorted(e)) for e in listed},
                         {("change", "crate", "files", "kind", "module", "source", "status", "target", "tests")})
        for e in listed:
            for f in e["files"]:
                self.assertEqual((out / f).read_text(), files[f])
        (out / "crates" / "stale.rs").write_text("old")
        gt.write(out, files, entries)
        self.assertFalse((out / "crates" / "stale.rs").exists())
        foreign = Path(tempfile.mkdtemp())
        (foreign / "something.txt").write_text("not ours")
        with self.assertRaises(SystemExit):
            gt.write(foreign, files, entries)

    def test_the_command_line_builds_from_a_snapshot_and_writes_the_dir(self):
        out = Path(tempfile.mkdtemp()) / "graded"
        holdouts = Path(tempfile.mkdtemp()) / "holdouts.json"
        holdouts.write_text(json.dumps(HOLDOUTS))
        rc = gt.main(["--repo", "/nowhere", "--commit", "abc123", "--probes", str(probes_dir()), "--holdouts",
                      str(holdouts), "--out", str(out)], snapshot=gt.DictSnapshot(SNAP, commit="abc123"), probe_map=MAP)
        self.assertEqual(rc, 0)
        self.assertEqual(len(json.loads((out / "graded.json").read_text())), 4)


class SeedAgreementTest(unittest.TestCase):
    """The probe table agrees with the seed's own runners: validate.sh appends each probe to the same host, and the
    seed's README gives each probe the same change."""

    def test_each_probe_has_the_host_and_change_the_seed_gives_it(self):
        validate = HIDDEN / "m2f-validation" / "validate.sh"
        readme = HIDDEN / "prompts-m2f" / "README.md"
        if not validate.exists() or not readme.exists():
            self.skipTest("the M2f seed isn't here")
        hosts = dict(re.findall(r"cat /in/probes/(\w+\.rs) >> \$I/(\w+)\.rs", validate.read_text()))
        changes = {p: int(n) for p, n in re.findall(r"^\| `(\w+\.rs)` \| (\d+) \|", readme.read_text(), re.M)}
        self.assertEqual(set(hosts), set(gt.PROBES))
        for probe, (change, host) in gt.PROBES.items():
            self.assertEqual(host, f"crates/clowder-tui/tests/integration/{hosts[probe]}.rs", probe)
            self.assertEqual(change, changes[probe], probe)
        self.assertEqual(sorted(p.name for p in (HIDDEN / "m2f-dependency-probes").glob("*.rs")), sorted(gt.PROBES))


if __name__ == "__main__":
    unittest.main()
