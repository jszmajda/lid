"""The pre-registered compile-only adaptation of held-out tests (costeval.rust_adapt), from a small fixture crate.

tests/fixtures/adapt-crate is a one-crate workspace laid out like Clowder: original-lib.rs is the crate the held-out
tests were written against, crates/fixture/src/lib.rs the crate as an arm left it, held-out/ the held-out files, and
diagnostics/ what `cargo test --no-run --message-format=json` said of each held-out target against the arm's crate
in the Rust executor image. The live test (CE_LIVE_DOCKER=1) runs the whole keeping step on the fixture in Docker.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from costeval import rust_adapt as ra, rust_grading as rg  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures" / "adapt-crate"
ARM_LIB = (FIX / "crates/fixture/src/lib.rs").read_text()
SOURCES = {"crates/fixture/src/lib.rs": ARM_LIB}
HELD = sorted(str(p.relative_to(FIX / "held-out")) for p in (FIX / "held-out").rglob("*.rs")
              if p.parent.name == "integration" and p.name != "main.rs")
BUILD_OK = '{"reason":"build-finished","success":true}\n'
WILD = 'unreachable!("grader adaptation: a variant the arm added")'
KITTEN = ("nickname: None, tags: Vec::new(), collar: Default::default(), naps: 0, friends: Default::default(), "
          "weight: 0.0, indoor: false")


def diagnostics(target: str) -> str:
    return (FIX / "diagnostics" / f"{target}.json").read_text()


def target_files(target: str) -> dict[str, str]:
    return {p: t for p, t in rg.held_out_targets(FIX / "held-out", HELD).items()
            if p.startswith(f"crates/fixture/tests/{target}/")}


def run(target: str, *builds: str, max_rounds: int = 3):
    outputs, put = list(builds), {}
    record, files = ra.adapt_target(lambda: outputs.pop(0) if outputs else BUILD_OK, target_files(target),
                                    lambda: SOURCES, lambda p, t: put.__setitem__(p, t), max_rounds=max_rounds)
    return record, files, put


class DiagnosticsTest(unittest.TestCase):
    def test_errors_come_from_cargos_json_with_their_primary_span(self):
        errs = ra.errors(diagnostics("heldout_events"))
        self.assertEqual([e.code for e in errs], ["E0063", "E0063"])
        self.assertEqual(errs[1].file, "crates/fixture/tests/heldout_events/events.rs")
        self.assertEqual(errs[1].message, "missing field `by` in initializer of `fixture::Event`")
        self.assertFalse(ra.built(diagnostics("heldout_events")))
        self.assertTrue(ra.built("Compiling fixture\n" + BUILD_OK))

    def test_comments_and_literals_are_masked_so_their_braces_never_count(self):
        text = 'let s = "a { b"; // c }\nlet c = \'{\'; /* d { /* e */ } */ let r = r#"}"#; fn f<\'a>(x: &\'a str) {}'
        m = ra.mask(text)
        self.assertEqual(len(m), len(text))
        self.assertEqual(m.count("{") - m.count("}"), 0)
        self.assertEqual(m.count("{"), 1)  # only f's body
        self.assertEqual(m.count("\n"), 1)
        self.assertIn("'a", m)  # a lifetime is not a char literal


class DefinitionsTest(unittest.TestCase):
    def test_a_structs_fields_and_types_come_from_the_arms_definition(self):
        fields = ra.fields_of(SOURCES, "fixture::Kitten", "Kitten")
        self.assertEqual([f for f, _ in fields],
                         ["name", "age", "nickname", "tags", "collar", "naps", "friends", "weight", "indoor"])
        self.assertEqual(dict(fields)["friends"], "HashMap<String, u32>")
        self.assertEqual(ra.fields_of(SOURCES, "Kitten", "Kitten"), fields)  # rustc sometimes trims the path

    def test_an_enum_variants_fields_come_from_the_variant_written_at_the_literal(self):
        # rustc names the enum; the literal names the variant
        self.assertEqual(ra.fields_of(SOURCES, "fixture::Event", "Event::Moved"), [("to", "u32"), ("by", "Option<String>")])

    def test_self_and_an_alias_name_the_struct_rustc_names(self):
        fields = ra.fields_of(SOURCES, "fixture::Kitten", "Kitten")
        self.assertEqual(ra.fields_of(SOURCES, "fixture::Kitten", "Self"), fields)
        self.assertEqual(ra.fields_of(SOURCES, "fixture::Kitten", "Cat"), fields)  # use fixture::Kitten as Cat
        self.assertEqual(ra.fields_of(SOURCES, "fixture::Event", "Self::Moved"), [("to", "u32"), ("by", "Option<String>")])

    def test_an_empty_value_is_default_where_the_type_implements_it_else_typed_where_obvious(self):
        self.assertEqual(ra.empty_value("String", SOURCES), "String::new()")
        self.assertEqual(ra.empty_value("Vec<String>", SOURCES), "Vec::new()")
        self.assertEqual(ra.empty_value("Option<String>", SOURCES), "None")
        self.assertEqual(ra.empty_value("u32", SOURCES), "0")
        self.assertEqual(ra.empty_value("f32", SOURCES), "0.0")
        self.assertEqual(ra.empty_value("bool", SOURCES), "false")
        self.assertEqual(ra.empty_value("Collar", SOURCES), "Default::default()")  # derives Default
        self.assertEqual(ra.empty_value("HashMap<String, u32>", SOURCES), "Default::default()")
        self.assertEqual(ra.empty_value("Ticks", SOURCES), "0")  # an alias of u64
        self.assertIsNone(ra.empty_value("Mood", SOURCES))  # no Default, no obvious empty value
        self.assertIsNone(ra.empty_value("(u32, Mood)", SOURCES))
        # an array takes Default when its element has an empty value; the rebuild checks the length allows it
        self.assertEqual(ra.empty_value("[String; clowder_core::MAX_RECIPE_INPUTS]", SOURCES), "Default::default()")
        self.assertEqual(ra.empty_value("[f64; 8]", SOURCES), "Default::default()")
        self.assertIsNone(ra.empty_value("[Mood; 3]", SOURCES))
        impl = {"lib.rs": "pub struct Leash(u8);\nimpl Default for Leash { fn default() -> Self { Leash(1) } }"}
        self.assertEqual(ra.empty_value("Leash", impl), "Default::default()")


class AdaptTest(unittest.TestCase):
    def test_missing_fields_get_empty_values_and_matches_a_wildcard_arm_without_moving_a_line(self):
        record, files, put = run("heldout_cats", diagnostics("heldout_cats"))
        self.assertEqual(record["status"], "adapted")
        self.assertEqual(record["rounds"], 2)  # built on the second
        common = files["crates/fixture/tests/heldout_cats/common/mod.rs"]
        self.assertIn(f"        age: 2, {KITTEN} /* a closing }} in a comment */\n", common)
        cats = files["crates/fixture/tests/heldout_cats/cats.rs"]
        self.assertIn(f'let k = Kitten {{ name: "Moss {{".to_string(), age: 1, {KITTEN} }};', cats)
        self.assertIn(f'Event::Moved {{ .. }} => "moved", _ => {WILD}\n', cats)
        self.assertIn(f"Event::Moved {{ .. }} => {{}}, _ => {WILD}\n", cats)
        original = target_files("heldout_cats")
        for path, text in files.items():
            self.assertEqual(text.count("\n"), original[path].count("\n"))  # failures still point at the held-out lines
        self.assertEqual(set(put), {"crates/fixture/tests/heldout_cats/common/mod.rs", "crates/fixture/tests/heldout_cats/cats.rs"})
        edits = record["edits"]
        self.assertEqual([(e["code"], e["file"].rsplit("/", 1)[1], e["line"]) for e in edits],
                         [("E0063", "mod.rs", 6), ("E0063", "cats.rs", 14), ("E0004", "cats.rs", 8), ("E0004", "cats.rs", 33)])
        self.assertEqual(edits[0]["fields"]["collar"], "Default::default()")
        self.assertEqual(edits[0]["type"], "fixture::Kitten")
        self.assertEqual(edits[2]["edit"], "wildcard arm")
        self.assertIn("Event::Renamed", edits[2]["uncovered"])

    def test_a_comparison_in_a_fields_value_hides_no_field(self):
        text = 'fn k() -> Kitten {\n    Kitten { name: if 1 < 2 { "a" } else { "b" }.to_string(), age: 1 }\n}\n'
        at = text.index("    Kitten {") + 4
        err = ra.Error(code="E0063", message="missing fields `collar`, `friends`, `indoor` and 4 other fields in "
                       "initializer of `fixture::Kitten`", file="t.rs", byte_start=at, byte_end=at + 6, in_macro=False, line=2)
        got = ra.edit_for(err, text, SOURCES)
        self.assertIsInstance(got, ra.Edit)
        self.assertEqual(got.text, ", " + KITTEN)

    def test_an_enum_variant_literal_gets_its_missing_field(self):
        record, files, _ = run("heldout_events", diagnostics("heldout_events"))
        self.assertEqual(record["status"], "adapted")
        self.assertIn("let e = Event::Moved { to: 3, by: None };", files["crates/fixture/tests/heldout_events/events.rs"])
        self.assertEqual(record["edits"][1]["fields"], {"by": "None"})

    def test_a_field_with_no_empty_value_is_a_compile_failure_not_adapted_and_nothing_is_edited(self):
        record, files, put = run("heldout_litters", diagnostics("heldout_litters"))
        self.assertEqual(record["status"], "not adapted")
        self.assertIn("`mood`", record["reason"])
        self.assertIn("Mood", record["reason"])
        self.assertEqual((record["edits"], put), ([], {}))
        self.assertEqual(files, target_files("heldout_litters"))

    def test_a_struct_pattern_missing_fields_gets_a_rest_pattern(self):
        record, files, _ = run("heldout_patterns", diagnostics("heldout_patterns"))
        self.assertEqual(record["status"], "adapted")
        self.assertIn("        Some(Event::Moved { to, .. }) => to,\n", files["crates/fixture/tests/heldout_patterns/patterns.rs"])
        edit = next(e for e in record["edits"] if e["code"] == "E0027")
        self.assertEqual((edit["edit"], edit["fields"], edit["line"]), ("rest pattern", ["by"], 6))

    def test_any_error_the_rule_doesnt_cover_means_no_adaptation(self):
        record, _, put = run("heldout_waves", diagnostics("heldout_waves"))
        self.assertEqual(record["status"], "not adapted")
        self.assertIn("E0425", record["reason"])
        self.assertEqual(put, {})
        self.assertIn("E0425", [e["code"] for e in record["errors"]])

    def test_an_error_outside_the_held_out_files_is_not_adapted(self):
        lib = diagnostics("heldout_events").replace("crates/fixture/tests/heldout_events/events.rs", "crates/fixture/src/lib.rs")
        record, _, put = run("heldout_events", lib)
        self.assertEqual(record["status"], "not adapted")
        self.assertIn("outside", record["reason"])
        self.assertEqual(put, {})

    def test_a_target_that_builds_is_left_alone(self):
        record, files, put = run("heldout_events", BUILD_OK)
        self.assertEqual(record, {"status": "built", "rounds": 1, "edits": []})
        self.assertEqual(put, {})

    def test_rounds_are_bounded(self):
        record, _, _ = run("heldout_events", *[diagnostics("heldout_events")] * 5, max_rounds=2)
        self.assertEqual(record["status"], "not adapted")
        self.assertIn("2 rounds", record["reason"])

    def test_a_test_that_reaches_an_adapted_arm_is_named(self):
        log = (FIX / "diagnostics" / "heldout_cats.test.log").read_text()
        self.assertEqual(ra.reached_adaptation(log), ["cats::every_arrival_is_described"])
        self.assertEqual(ra.reached_adaptation("test cats::x ... ok\n"), [])


class SourcesTest(unittest.TestCase):
    def test_the_arms_sources_come_back_by_path_without_tests(self):
        class Ck:
            def sh(self, script, stdin=None, check=True):
                self.script = script
                return f"\n{ra.SOURCE_MARK} ./crates/fixture/src/lib.rs\n{ARM_LIB}\n{ra.SOURCE_MARK} ./src/a.rs\nfn a() {{}}\n"
        ck = Ck()
        got = ra.arm_sources(ck)
        self.assertEqual(set(got), {"crates/fixture/src/lib.rs", "src/a.rs"})
        self.assertIn("pub struct Kitten", got["crates/fixture/src/lib.rs"])
        self.assertIn("-prune", ck.script)


class FakeCk:
    """A checkpoint that answers each held-out build with the captured diagnostics first and a clean build after."""

    def __init__(self, logs: dict[str, str]):
        self.files, self.scripts, self.logs, self.builds = {}, [], logs, {}

    def put(self, path, text):
        self.files[path] = text

    def get(self, path):
        return self.files.get(path)

    def sh(self, script, stdin=None, check=True):
        self.scripts.append(script)
        if ra.SOURCE_MARK in script:
            return f"{ra.SOURCE_MARK} ./crates/fixture/src/lib.rs\n{ARM_LIB}"
        if "--test " not in script:
            return ""
        target = script.split("--test ")[1].split()[0]
        if "--no-run" in script:
            self.builds[target] = self.builds.get(target, 0) + 1
            return diagnostics(target) if self.builds[target] == 1 else BUILD_OK
        return self.logs.get(target, "error: could not compile `fixture`\nEXIT=101\n")


class KeepingAdaptsTest(unittest.TestCase):
    def test_keeping_adapts_records_each_edit_and_keeps_failures_not_adapted_apart(self):
        import grade_rust
        cats_log = (FIX / "diagnostics" / "heldout_cats.test.log").read_text()
        events_log = "running 1 test\ntest events::a_move_has_a_destination ... ok\n\ntest result: ok. 1 passed; 0 failed\nEXIT=0\n"
        patterns_log = "running 1 test\ntest patterns::a_move_is_read_back ... ok\n\ntest result: ok. 1 passed; 0 failed\nEXIT=0\n"
        saves_log = (FIX / "diagnostics" / "heldout_saves.test.log").read_text()
        ck = FakeCk({"heldout_cats": cats_log, "heldout_events": events_log, "heldout_patterns": patterns_log,
                     "heldout_saves": saves_log})
        out = Path(tempfile.mkdtemp()) / "keeping"
        r = grade_rust.keeping(ck, FIX / "held-out", HELD, out)
        self.assertEqual(r["targets"]["heldout_cats"]["adaptation"]["status"], "adapted")
        self.assertEqual(len(r["targets"]["heldout_cats"]["adaptation"]["edits"]), 4)
        self.assertEqual(r["targets"]["heldout_cats"]["reached_adaptation"], ["cats::every_arrival_is_described"])
        self.assertEqual(r["adapted"], ["heldout_cats", "heldout_events", "heldout_patterns", "heldout_saves"])
        self.assertEqual(sorted(r["compile_failed_not_adapted"]), ["heldout_litters", "heldout_waves"])
        self.assertIn("E0425", r["compile_failed_not_adapted"]["heldout_waves"])
        self.assertEqual(r["tests_not_built"], 2)
        self.assertEqual((r["passed"], r["failed"]), (4, 3))  # tests that ran and failed, apart from those not built
        self.assertEqual(r["reached_adaptation"], 1)
        self.assertEqual(r["reached_adaptation_tests"], ["heldout_cats/cats::every_arrival_is_described"])
        self.assertEqual(r["adaptations_by_code"], {"E0004": 2, "E0027": 1, "E0063": 6})
        self.assertIn(KITTEN, ck.files["/work/app/crates/fixture/tests/heldout_cats/cats.rs"])
        self.assertIn(KITTEN, (out / "adapted" / "crates/fixture/tests/heldout_cats/cats.rs").read_text())
        self.assertFalse((out / "adapted" / "crates/fixture/tests/heldout_litters").exists())
        self.assertEqual(sum(ra.SOURCE_MARK in s for s in ck.scripts), 1)  # the arm's sources are read once
        build = next(s for s in ck.scripts if "--no-run" in s)
        self.assertIn("--message-format=json", build)


@unittest.skipUnless(os.environ.get("CE_LIVE_DOCKER") == "1", "runs cargo in the Rust executor image; set CE_LIVE_DOCKER=1")
class LiveFixtureCrateTest(unittest.TestCase):
    """The fixture crate in the Rust executor image: the held-out tests build and pass against the original crate
    with nothing adapted, and against the arm's crate the rule adapts what it covers and nothing else."""

    IMAGE = "lid-cost-eval-executor-rust:2.1.323"

    def keep(self, lib: str) -> dict:
        import subprocess
        import grade_rust
        ck = rg.RustCheckpoint(name="adapt-fixture", commit="-", image=self.IMAGE)
        self.addCleanup(subprocess.run, ["docker", "volume", "rm", "-f", ck.volume], capture_output=True)
        ck.sh("rm -rf /work/app /work/target && mkdir -p /work/app")
        for p in ("Cargo.toml", "crates/fixture/Cargo.toml"):
            ck.put(f"/work/app/{p}", (FIX / p).read_text())
        ck.put("/work/app/crates/fixture/src/lib.rs", lib)
        out = Path(tempfile.mkdtemp()) / "keeping"
        self.addCleanup(shutil.rmtree, out.parent, True)
        return grade_rust.keeping(ck, FIX / "held-out", HELD, out)

    def test_the_original_crate_needs_no_adaptation(self):
        r = self.keep((FIX / "original-lib.rs").read_text())
        self.assertEqual({t: v["adaptation"]["status"] for t, v in r["targets"].items()},
                         {t: "built" for t in r["targets"]})
        self.assertEqual((r["passed"], r["failed"], r["compile_failed"]), (9, 0, []))

    def test_the_arms_crate_is_adapted_where_the_rule_covers_it(self):
        r = self.keep(ARM_LIB)
        status = {t: v["adaptation"]["status"] for t, v in r["targets"].items()}
        self.assertEqual(status, {"heldout_cats": "adapted", "heldout_events": "adapted", "heldout_litters": "not adapted",
                                  "heldout_patterns": "adapted", "heldout_saves": "adapted", "heldout_waves": "not adapted"})
        self.assertEqual(r["targets"]["heldout_cats"]["tests"], {"cats::a_helper_kitten_is_two": "ok",
                                                                 "cats::a_kitten_is_greeted": "ok",
                                                                 "cats::every_arrival_is_described": "FAILED"})
        self.assertEqual(r["targets"]["heldout_cats"]["reached_adaptation"], ["cats::every_arrival_is_described"])
        self.assertEqual(r["targets"]["heldout_events"]["tests"], {"events::a_move_has_a_destination": "ok"})
        self.assertEqual(r["targets"]["heldout_patterns"]["tests"], {"patterns::a_move_is_read_back": "ok"})
        self.assertEqual(r["targets"]["heldout_saves"]["tests"], {"saves::a_resaved_kitten_keeps_its_shape": "FAILED",
                                                                  "saves::a_saved_kitten_is_exact": "FAILED"})
        self.assertEqual(r["compile_failed"], ["heldout_litters", "heldout_waves"])
        print(json.dumps(r["targets"]["heldout_cats"]["adaptation"], indent=1))

    def test_the_snapshots_helpers_are_built_against_the_arms_crate_before_an_executor_gets_them(self):
        import subprocess
        ck = rg.RustCheckpoint(name="adapt-helpers", commit="-", image=self.IMAGE)
        self.addCleanup(subprocess.run, ["docker", "volume", "rm", "-f", ck.volume], capture_output=True)
        ck.sh("rm -rf /work/app /work/target && mkdir -p /work/app")
        for p in ("Cargo.toml", "crates/fixture/Cargo.toml"):
            ck.put(f"/work/app/{p}", (FIX / p).read_text())
        ck.put("/work/app/crates/fixture/src/lib.rs", ARM_LIB)
        rec = rg.place_probe_helpers(ck, rg.snapshot_helpers(FIX / "held-out"), sources=lambda: ra.arm_sources(ck))
        self.assertEqual(rec["fixture"]["status"], "adapted")  # common builds a Kitten, which gained fields
        self.assertIn("nickname: None", ck.get("/work/app/crates/fixture/tests/probe_helpers/common/mod.rs"))
        self.assertIsNone(ck.get("/work/app/crates/fixture/tests/probe_helpers_check.rs"))


if __name__ == "__main__":
    unittest.main()
