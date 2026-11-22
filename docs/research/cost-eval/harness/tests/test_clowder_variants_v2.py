"""Tests for the variant builder's M2f additions: the set's label apart from its draw seed, function-level forced
holdouts (and the Rust function remover under them), and the renaming dose.

The fixture is test_rust_seed's small made-up Cargo workspace, so nothing from a real seed appears here.
"""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import clowder_variants as cv  # noqa: E402
from test_rust_seed import make_repo  # noqa: E402

# ------------------------------------------------------------------------------------------- the fn remover

TRICKY = r'''//! A test module with every way a brace can hide.

use std::fmt;

/// A helper the tests share.
fn helper<'a>(s: &'a str) -> &'a str { s }

// #[test] fn commented_out() { }
const FAKE: &str = "#[test]\nfn in_a_string() { }";

/// Braces in strings, chars, comments and raw strings.
/// @spec WID-CORE-001
#[test]
fn tricky() {
    let a = "}}}{"; let b = '}'; let c = '{'; let q = '\''; let bs = '\\'; let dq = '"';
    let e = "an \"escaped\" } quote";
    // a } in a line comment
    /* a { in a block /* nested } */ comment } */
    let r = r#"a "} raw" string"#;
    let r2 = r##"two "# hashes }"##;
    let br = br"}";
    let u = '\u{1F600}';
    let label: &'static str = "x";
    'outer: loop { break 'outer; }
    fn nested(x: u8) -> u8 { if x > 0 { x } else { 0 } }
    assert_eq!(nested(1), 1, "{}", "}");
}

#[test]
fn plain() { assert!(true); }

#[should_panic(
    expected = "a } in the message"
)]
#[test]
fn panics() { panic!("a }} in the message"); }

#[ignore] #[test]
fn ignored_same_line() {}

fn not_a_test() -> u8 { 1 }

#[test]
fn last() {
    assert_eq!(not_a_test(), 1);
}
'''


class MaskTest(unittest.TestCase):
    def test_comments_strings_and_chars_go_blank_and_offsets_and_newlines_stay(self):
        m = cv.mask_rust(TRICKY)
        self.assertEqual(len(m), len(TRICKY))
        self.assertEqual([i for i, c in enumerate(m) if c == "\n"], [i for i, c in enumerate(TRICKY) if c == "\n"])
        self.assertNotIn("commented_out", m)
        self.assertNotIn("in_a_string", m)
        self.assertNotIn("nested }", m)
        self.assertIn("fn tricky()", m)
        self.assertIn("'outer: loop", m)  # a label stays code
        self.assertIn("&'a str", m)  # so does a lifetime
        body = m[m.index("fn tricky()"):m.index("fn plain()")]
        self.assertEqual(body.count("{"), body.count("}"))


class RemoveTestFnsTest(unittest.TestCase):
    def test_the_named_test_goes_with_its_doc_comments_and_attributes_and_nothing_else(self):
        out = cv.remove_test_fns(TRICKY, ["tricky"])
        self.assertNotIn("fn tricky", out)
        self.assertNotIn("Braces in strings", out)
        self.assertNotIn("@spec WID-CORE-001", out)
        self.assertNotIn("let r2", out)
        for kept in ("fn helper<'a>", "// #[test] fn commented_out() { }", "const FAKE", "fn plain()", "fn panics()",
                     "fn not_a_test()", "fn last()", "/// A helper the tests share.", "use std::fmt;"):
            self.assertIn(kept, out, kept)
        self.assertEqual(out, TRICKY.replace(TRICKY[TRICKY.index("/// Braces"):TRICKY.index("#[test]\nfn plain")], ""))

    def test_a_multi_line_attribute_and_attributes_on_the_tests_own_line_go_too(self):
        out = cv.remove_test_fns(TRICKY, ["panics", "ignored_same_line"])
        self.assertNotIn("should_panic", out)
        self.assertNotIn("a } in the message", out)
        self.assertNotIn("#[ignore]", out)
        self.assertIn("fn plain() { assert!(true); }\n\nfn not_a_test()", out)

    def test_the_last_test_in_a_file_leaves_no_trailing_blank_line(self):
        out = cv.remove_test_fns(TRICKY, ["last"])
        self.assertTrue(out.endswith("fn not_a_test() -> u8 { 1 }\n"), out[-60:])
        self.assertNotIn("\n\n\n", out)

    def test_removing_tests_leaves_no_run_of_blank_lines(self):
        out = cv.remove_test_fns(TRICKY, ["tricky", "plain", "panics"])
        self.assertNotIn("\n\n\n", out)
        self.assertIn("const FAKE", out)

    def test_a_name_that_is_no_test_here_is_an_error(self):
        for name in ("commented_out", "in_a_string", "not_a_test", "nested", "absent"):
            with self.assertRaises(ValueError, msg=name):
                cv.remove_test_fns(TRICKY, [name])

    def test_keeping_only_some_tests_keeps_every_helper(self):
        out = cv.keep_test_fns(TRICKY, ["plain", "last"])
        self.assertEqual([n for n, _, _ in cv.rust_test_fns(out)], ["plain", "last"])
        for kept in ("fn helper<'a>", "const FAKE", "fn not_a_test()", "use std::fmt;"):
            self.assertIn(kept, out)
        self.assertNotIn("\n\n\n", out)

    def test_every_test_is_found_with_its_span(self):
        names = [n for n, _, _ in cv.rust_test_fns(TRICKY)]
        self.assertEqual(names, ["tricky", "plain", "panics", "ignored_same_line", "last"])
        for name, start, end in cv.rust_test_fns(TRICKY):
            chunk = TRICKY[start:end]
            self.assertTrue(chunk.endswith("}\n"), name)
            self.assertIn(f"fn {name}", chunk)


# ------------------------------------------------------- traces a removed test leaves: banners, imports, helpers

TRACES = '''//! A module of tests.

use std::collections::HashMap;
use std::path::{Path, PathBuf as Buf};
use crate::common::{fresh, only_gone, Shared};
use crate::common::lonely;

const KEPT: u8 = 1;
const GONE_LIMIT: u8 = 2;

/// Builds the map the gone tests read.
fn gone_map() -> HashMap<u8, u8> {
    let mut m = inner_gone();
    m.insert(GONE_LIMIT, 0);
    m
}

/// Only gone_map uses this.
fn inner_gone() -> HashMap<u8, u8> { HashMap::new() }

#[derive(Debug)]
struct GoneCase { n: u8 }

fn shared() -> u8 { KEPT + fresh() }

fn never_used() -> u8 { 0 }

pub fn exported() -> Buf { Buf::new() }

// ---------------------------------------------------------------------------
// FEAT-001 — helpers for everyone
// ---------------------------------------------------------------------------

fn helper_in_section() -> u8 { 3 }

// ---------------------------------------------------------------------------
// FEAT-002 — what stays
// ---------------------------------------------------------------------------

/// Stays.
#[test]
fn stays() {
    assert_eq!(shared(), 1);
    let _p: &Path = Path::new("x");
    let _s: Shared = Shared;
    assert_eq!(helper_in_section(), 3);
}

/// Goes, in a section that keeps a test.
#[test]
fn goes_beside() { let _m = gone_map(); }

// ---- FEAT-003 — all gone ----

#[test]
fn goes_alone() { only_gone(); lonely(); let _c = GoneCase { n: GONE_LIMIT }; }

// ---------------------------------------------------------------------------
// FEAT-004 — the last section, all gone
// ---------------------------------------------------------------------------

/// Goes at the end.
#[test]
fn goes_last() { let _m: HashMap<u8, u8> = gone_map(); }
'''

GONE = ["goes_beside", "goes_alone", "goes_last"]


class TracesTest(unittest.TestCase):
    def test_a_banner_goes_once_no_test_is_left_under_it(self):
        out, traces = cv.remove_tests_and_traces(TRACES, GONE)
        self.assertNotIn("FEAT-003", out)
        self.assertNotIn("FEAT-004", out)
        self.assertIn("// FEAT-002 — what stays", out)  # a test is still under it
        self.assertIn("// FEAT-001 — helpers for everyone", out)  # it never headed a test
        self.assertEqual(traces["banners"], ["FEAT-003 — all gone", "FEAT-004 — the last section, all gone"])
        self.assertNotIn("\n\n\n", out)
        self.assertTrue(out.endswith("    assert_eq!(helper_in_section(), 3);\n}\n"), out[-80:])
        self.assertEqual(out.count("// -----"), 4)  # two whole three-line banners left

    def test_imports_only_the_removed_tests_used_go_and_the_rest_of_the_use_stays(self):
        out, traces = cv.remove_tests_and_traces(TRACES, GONE)
        self.assertNotIn("HashMap", out)
        self.assertNotIn("use crate::common::lonely;", out)
        self.assertIn("use crate::common::{fresh, Shared};\n", out)
        self.assertIn("use std::path::{Path, PathBuf as Buf};\n", out)
        self.assertEqual(traces["imports"], ["HashMap", "lonely", "only_gone"])

    def test_helpers_only_the_removed_tests_used_go_down_the_chain_and_others_stay(self):
        out, traces = cv.remove_tests_and_traces(TRACES, GONE)
        for gone in ("fn gone_map", "fn inner_gone", "GONE_LIMIT", "GoneCase", "derive(Debug)",
                     "Builds the map the gone tests read", "Only gone_map uses this"):
            self.assertNotIn(gone, out, gone)
        for kept in ("const KEPT", "fn shared()", "fn never_used()", "pub fn exported()", "fn helper_in_section()",
                     "fn stays()"):
            self.assertIn(kept, out, kept)
        self.assertEqual(traces["items"], ["const GONE_LIMIT", "fn gone_map", "fn inner_gone", "struct GoneCase"])

    def test_a_banner_with_a_test_left_under_it_stays_and_so_do_names_still_used(self):
        out, traces = cv.remove_tests_and_traces(TRACES, ["goes_beside"])  # gone_map is still goes_last's
        self.assertEqual(traces, {"banners": [], "imports": [], "items": []})
        self.assertEqual(out, cv.remove_test_fns(TRACES, ["goes_beside"]))
        out, traces = cv.remove_tests_and_traces(TRACES, ["stays"])  # goes_beside is still under FEAT-002
        self.assertIn("// FEAT-002 — what stays", out)
        # FEAT-001 headed only helper_in_section, which only stays used: a banner over nothing goes too
        self.assertNotIn("FEAT-001", out)
        self.assertEqual(traces, {"banners": ["FEAT-001 — helpers for everyone"], "imports": ["Path", "Shared", "fresh"],
                                  "items": ["const KEPT", "fn helper_in_section", "fn shared"]})
        self.assertNotIn("\n\n\n", out)
        self.assertIn("use std::path::{PathBuf as Buf};\n", out)
        self.assertIn("use crate::common::{only_gone};\n", out)

    def test_use_trees_lose_just_the_named_leaves(self):
        drop = cv.drop_use_names
        self.assertEqual(drop("use a::{b, c, D};", {"c"}), "use a::{b, D};")
        self.assertEqual(drop("use a::{b, c};", {"c"}), "use a::{b};")
        self.assertEqual(drop("use a::{b as e, c};", {"e"}), "use a::{c};")
        self.assertEqual(drop("use a::{b as e, c};", {"b"}), "use a::{b as e, c};")  # the local name is e
        self.assertEqual(drop("use a::{x::{p, q}, r};", {"p", "q"}), "use a::{r};")
        self.assertEqual(drop("use a::b;", {"b"}), "")
        self.assertEqual(drop("use a::{b, c};", {"b", "c"}), "")
        multi = "use core::{\n    load, save, Command, Event,\n    Report,\n};"
        self.assertEqual(drop(multi, {"load", "save"}), "use core::{\n    Command, Event,\n    Report,\n};")
        self.assertEqual(drop(multi, {"Report"}), "use core::{\n    load, save, Command, Event,\n};")


# ------------------------------------------------------------------------------------------- forced holdouts


def holdouts_file(tests: list[dict]) -> Path:
    p = Path(tempfile.mkdtemp()) / "holdouts.json"
    p.write_text(json.dumps({"note": "x", "tests": tests, "for_the_builder": "remove the functions"}))
    return p


class ForcedHoldoutsTest(unittest.TestCase):
    def setUp(self):
        self.repo, self.commit = make_repo()
        self.tree = cv.read_tree(self.repo, self.commit)
        self.held = ["crates/widgets/tests/integration/beta.rs"]
        plain = cv.plan_variants(self.tree, held_out=self.held, seed="s1")
        self.thinned = plain["stripped"].report["tests_thinned"]
        self.thin_file = next(p for p in self.thinned if p not in self.held and "widgets/tests/integration/" in p
                              and p.rsplit("/", 1)[1] in ("alpha.rs", "gamma.rs", "delta.rs"))
        self.kept_file = next(f"crates/widgets/tests/integration/{n}.rs" for n in ("alpha", "gamma", "delta")
                              if f"crates/widgets/tests/integration/{n}.rs" not in self.thinned)
        self.tests = [
            {"change": 1, "status": "graded", "test": self.kept_file.removeprefix("crates/") + "::t3"},
            {"change": 1, "status": "retired", "test": self.kept_file.removeprefix("crates/") + "::t5"},
            {"change": 2, "status": "graded", "test": "widgets/tests/integration/beta.rs::t1"},
            {"change": 3, "status": "graded", "test": self.thin_file.removeprefix("crates/") + "::t0"},
        ]
        self.holdouts = cv.load_holdouts(holdouts_file(self.tests))

    def test_paths_gain_the_crates_prefix_and_split_into_file_and_function(self):
        h = self.holdouts[0]
        self.assertEqual((h["path"], h["fn"], h["test"], h["change"], h["status"]),
                         (self.kept_file, "t3", self.tests[0]["test"], 1, "graded"))

    def test_each_listed_test_leaves_every_variant_and_the_rest_of_its_file_stays(self):
        plans = cv.plan_variants(self.tree, held_out=self.held, seed="s1")
        record = cv.remove_forced_holdouts(plans, self.holdouts, tree=self.tree, held_out=self.held)
        for name in ("full", "lid", "stripped"):
            text = plans[name].files[self.kept_file].decode()
            self.assertNotRegex(text, r"\bfn t3\b")
            self.assertNotRegex(text, r"\bfn t5\b")
            for k in (0, 1, 2, 4, 6, 9):
                self.assertRegex(text, rf"\bfn t{k}\b", (name, k))
            self.assertIn("use crate::common;", text)
            stem = Path(self.kept_file).stem
            self.assertIn(f"mod {stem};", plans[name].files["crates/widgets/tests/integration/main.rs"].decode())
        self.assertEqual(plans["full"].files, plans["lid"].files)
        by_test = {r["test"]: r for r in record}
        self.assertEqual(by_test[self.tests[0]["test"]],
                         {"test": self.tests[0]["test"], "change": 1, "status": "graded",
                          "removed_from": ["full", "lid", "stripped"], "absent_in": [], "absent_why": {},
                          "held_out_copy": f"held-out/{self.kept_file}"})

    def test_a_test_whose_file_was_already_removed_is_recorded_not_failed(self):
        plans = cv.plan_variants(self.tree, held_out=self.held, seed="s1")
        record = {r["test"]: r for r in cv.remove_forced_holdouts(plans, self.holdouts, tree=self.tree, held_out=self.held)}
        drawn = record["widgets/tests/integration/beta.rs::t1"]
        self.assertEqual((drawn["removed_from"], drawn["absent_in"]), ([], ["full", "lid", "stripped"]))
        self.assertEqual(set(drawn["absent_why"].values()), {"held out by the draw"})
        self.assertEqual(drawn["held_out_copy"], "held-out/crates/widgets/tests/integration/beta.rs")
        thin = record[self.tests[3]["test"]]
        self.assertEqual((thin["removed_from"], thin["absent_in"], thin["absent_why"]),
                         (["full", "lid"], ["stripped"], {"stripped": "thinned"}))
        self.assertNotRegex(plans["full"].files[self.thin_file].decode(), r"\bfn t0\b")

    def test_the_draw_and_the_thinning_do_not_move_and_the_reports_count_what_is_left(self):
        plans = cv.plan_variants(self.tree, held_out=self.held, seed="s1")
        before = {n: v.report["test_lines"] for n, v in plans.items()}
        cv.remove_forced_holdouts(plans, self.holdouts, tree=self.tree, held_out=self.held)
        self.assertEqual(plans["stripped"].report["tests_thinned"], self.thinned)
        self.assertEqual(plans["stripped"].report["held_out"], self.held)
        for name, v in plans.items():
            self.assertEqual(v.report["test_lines"], cv._test_lines(v.files))
            self.assertLess(v.report["test_lines"], before[name])
            self.assertEqual(v.report["ratio"], round(v.report["test_lines"] / v.report["source_lines"], 3))

    def test_each_variants_report_lists_the_traces_removed_with_the_tests(self):
        path = "crates/widgets/tests/integration/alpha.rs"
        self.tree.files[path] = TRACES.encode()
        holdouts = cv.load_holdouts(holdouts_file([{"change": 5, "status": "graded",
                                                    "test": f"widgets/tests/integration/alpha.rs::{n}"} for n in GONE]))
        plans = cv.plan_variants(self.tree, held_out=self.held, seed="s1", ratio=10.0)  # a ratio that thins nothing
        cv.remove_forced_holdouts(plans, holdouts, tree=self.tree, held_out=self.held)
        for name in ("full", "lid", "stripped"):
            traces = plans[name].report["forced_holdout_traces"]
            self.assertEqual(set(traces), {path})  # only files that lost more than their tests are listed
            self.assertEqual(traces[path]["banners"], ["FEAT-003 — all gone", "FEAT-004 — the last section, all gone"])
            self.assertEqual(traces[path]["imports"], ["HashMap", "lonely", "only_gone"])
            self.assertNotIn("gone_map", plans[name].files[path].decode())

    def test_a_listed_test_missing_from_the_snapshot_is_an_error(self):
        plans = cv.plan_variants(self.tree, held_out=self.held, seed="s1")
        for bad in ("widgets/tests/integration/alpha.rs::no_such_test", "widgets/tests/integration/nope.rs::t0"):
            with self.assertRaises(ValueError, msg=bad):
                cv.remove_forced_holdouts(plans, cv.load_holdouts(holdouts_file([{"change": 9, "status": "graded",
                                                                                   "test": bad}])),
                                           tree=self.tree, held_out=self.held)

    def test_the_held_out_copy_is_the_listed_tests_with_their_files_helpers(self):
        out = cv.held_out_helpers(self.tree, self.held, self.holdouts)
        copy = out[self.kept_file].decode()
        self.assertEqual([n for n, _, _ in cv.rust_test_fns(copy)], ["t3", "t5"])
        self.assertIn("use crate::common;", copy)
        self.assertEqual(out[self.thin_file].decode().count("#[test]"), 1)
        self.assertEqual(out["crates/widgets/tests/integration/beta.rs"], self.tree.files["crates/widgets/tests/integration/beta.rs"])
        self.assertIn("crates/widgets/tests/integration/main.rs", out)
        self.assertIn("crates/widgets/tests/integration/common/mod.rs", out)


# --------------------------------------------------------------------------------------------- the renames


def renames_file(entries: list[dict]) -> Path:
    p = Path(tempfile.mkdtemp()) / "renames.json"
    p.write_text(json.dumps({"note": "x", "renames": entries}))
    return p


RENAMES = [
    {"d": "D1", "kind": "identifier", "file": "crates/widgets/src/lib.rs", "old": "label", "new": "caption", "count": 2},
    {"d": "D1", "kind": "comment", "file": "crates/widgets/src/lib.rs", "old": "keeping nothing else",
     "new": "and nothing more", "count": 1},
    {"d": "D1", "kind": "injected-mirrored-constant", "file": "crates/widgets/src/lib.rs",
     "old": "pub struct Widget", "new": "const BRACE: char = '{';\n\npub struct Widget", "count": 1},
    {"d": "D1", "kind": "doc", "file": "docs/intent/core/core-specs.md", "line": "**UI-DRAW-010**", "old": "widget",
     "new": "gadget", "count": 1},
]


class RenamesTest(unittest.TestCase):
    def setUp(self):
        self.repo, self.commit = make_repo()
        self.tree = cv.read_tree(self.repo, self.commit)

    def test_entries_apply_in_order_with_their_counts_and_are_recorded(self):
        applied = cv.apply_renames(self.tree, cv.load_renames(renames_file(RENAMES)))
        lib = self.tree.files["crates/widgets/src/lib.rs"].decode()
        self.assertNotIn("label", lib)
        self.assertEqual(lib.count("caption"), 2)
        self.assertIn("const BRACE: char = '{';\n\npub struct Widget", lib)
        self.assertEqual(applied, [{"d": r["d"], "kind": r["kind"], "file": r["file"], "count": r["count"]} for r in RENAMES])

    def test_a_line_anchor_confines_the_rename_to_its_line(self):
        cv.apply_renames(self.tree, cv.load_renames(renames_file(RENAMES[3:])))
        specs = self.tree.files["docs/intent/core/core-specs.md"].decode()
        self.assertIn("**UI-DRAW-010** The list shows every gadget.", specs)
        self.assertIn("**WID-CORE-001** A widget has a name.", specs)  # the same word on another line stays
        self.assertIn("**WID-CORE-002** A widget can be renamed.", specs)

    def test_a_count_mismatch_fails_loudly(self):
        for bad in ({**RENAMES[0], "count": 3}, {**RENAMES[3], "count": 2}, {**RENAMES[3], "line": "**NOPE-001**"},
                    {**RENAMES[3], "line": "widget"}, {**RENAMES[0], "file": "crates/widgets/src/nope.rs"}):
            tree = cv.read_tree(self.repo, self.commit)
            with self.assertRaises(ValueError, msg=bad):
                cv.apply_renames(tree, [bad])

    def test_a_later_entry_sees_the_earlier_ones(self):
        chained = [RENAMES[0], {"d": "D1", "kind": "identifier", "file": "crates/widgets/src/lib.rs",
                                "old": "pub fn caption", "new": "pub fn title", "count": 1}]
        cv.apply_renames(self.tree, chained)
        self.assertIn("pub fn title(&self)", self.tree.files["crates/widgets/src/lib.rs"].decode())

    def test_doc_renames_reach_the_variants_that_keep_docs_and_drop_out_of_stripped(self):
        cv.apply_renames(self.tree, cv.load_renames(renames_file(RENAMES)))
        plans = cv.plan_variants(self.tree, held_out=[], seed="s1")
        for name in ("full", "lid"):
            self.assertIn("every gadget", plans[name].files["docs/intent/core/core-specs.md"].decode())
        self.assertFalse(any("gadget" in d.decode(errors="replace") for d in plans["stripped"].files.values()))
        self.assertIn("pub fn caption", plans["stripped"].files["crates/widgets/src/lib.rs"].decode())


# -------------------------------------------------------------------------------------------------- the CLI


class CliTest(unittest.TestCase):
    def setUp(self):
        self.repo, self.commit = make_repo()
        self.out = Path(tempfile.mkdtemp()) / "set"

    def run_main(self, *extra):
        loads = []
        with mock.patch.object(cv, "load_volume", lambda repo, volume, image, jj=False: loads.append(volume)):
            cv.main(["--repo", str(self.repo), "--commit", self.commit, "--out", str(self.out),
                     "--held-out-share", "0.5", *extra])
        return json.loads((self.out / "manifest.json").read_text()), loads

    def test_the_label_names_the_set_and_the_draw_seed_draws_it(self):
        manifest, loads = self.run_main("--seed", "lab", "--draw-seed", "s1", "--volumes")
        tree = cv.read_tree(self.repo, self.commit)
        self.assertEqual(manifest["held_out"], cv.choose_held_out(tree, share=0.5, seed="s1"))
        plain = cv.plan_variants(tree, held_out=manifest["held_out"], seed="s1")
        self.assertEqual(manifest["variants"]["stripped"]["report"]["tests_thinned"],
                         plain["stripped"].report["tests_thinned"])
        self.assertEqual((manifest["seed"], manifest["draw_seed"]), ("lab", "s1"))
        self.assertEqual(loads, ["ce-cv-lab-full", "ce-cv-lab-lid", "ce-cv-lab-stripped"])
        self.assertEqual([manifest["variants"][n]["volume"] for n in ("full", "lid", "stripped")], loads)
        self.assertEqual((manifest["forced_holdouts"], manifest["renames_applied"]), ([], []))

    def test_the_draw_seed_defaults_to_the_seed(self):
        manifest, _ = self.run_main("--seed", "s1")
        self.assertEqual(manifest["draw_seed"], "s1")
        self.assertEqual(manifest["held_out"], cv.choose_held_out(cv.read_tree(self.repo, self.commit), share=0.5, seed="s1"))

    def test_holdouts_and_renames_are_applied_and_recorded(self):
        tree = cv.read_tree(self.repo, self.commit)
        held = cv.choose_held_out(tree, share=0.5, seed="s1")
        kept = next(f"crates/widgets/tests/integration/{n}.rs" for n in ("alpha", "gamma", "delta")
                    if f"crates/widgets/tests/integration/{n}.rs" not in held)
        hfile = holdouts_file([{"change": 4, "status": "graded", "test": kept.removeprefix("crates/") + "::t2"}])
        manifest, _ = self.run_main("--seed", "dose", "--draw-seed", "s1", "--holdouts", str(hfile),
                                    "--renames", str(renames_file(RENAMES)))
        self.assertEqual(manifest["held_out"], held)
        [forced] = manifest["forced_holdouts"]
        self.assertEqual(forced["held_out_copy"], f"held-out/{kept}")
        self.assertIn("full", forced["removed_from"])
        copy = (self.out / forced["held_out_copy"]).read_text()
        self.assertEqual([n for n, _, _ in cv.rust_test_fns(copy)], ["t2"])
        self.assertNotRegex((self.out / "full" / kept).read_text(), r"\bfn t2\b")
        self.assertEqual([(r["d"], r["kind"], r["file"], r["count"]) for r in manifest["renames_applied"]],
                         [(r["d"], r["kind"], r["file"], r["count"]) for r in RENAMES])
        doc = manifest["renames_applied"][3]
        self.assertEqual(doc["variants"], ["full", "lid"])
        self.assertEqual(manifest["renames_applied"][0]["variants"], ["full", "lid", "stripped"])
        self.assertIn("every gadget", (self.out / "lid/docs/intent/core/core-specs.md").read_text())
        self.assertIn("pub fn caption", (self.out / "stripped/crates/widgets/src/lib.rs").read_text())
        self.assertTrue(manifest["holdouts_file"].endswith("holdouts.json"))
        self.assertTrue(manifest["renames_file"].endswith("renames.json"))

    def test_rebuilding_a_set_keeps_what_others_wrote_beside_it(self):
        (self.out / "graded" / "probes").mkdir(parents=True)
        (self.out / "graded" / "probes" / "x.rs").write_text("kept")
        self.run_main("--seed", "s1")
        self.run_main("--seed", "s1")
        self.assertEqual((self.out / "graded" / "probes" / "x.rs").read_text(), "kept")

    def test_a_rename_count_mismatch_stops_the_build_before_anything_is_written(self):
        with self.assertRaises(SystemExit) as e, mock.patch("sys.stderr"):
            self.run_main("--seed", "dose", "--renames", str(renames_file([{**RENAMES[0], "count": 5}])))
        self.assertNotEqual(e.exception.code, 0)
        self.assertFalse((self.out / "manifest.json").exists())
        self.assertFalse((self.out / "full").exists())


if __name__ == "__main__":
    unittest.main()
