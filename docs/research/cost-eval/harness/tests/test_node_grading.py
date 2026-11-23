"""Tests for grading an M2h (openGym, Node) fork: keeping against a cached baseline with retired tests, grader-owned
adjusted copies and flaky reruns; the three-valued dependency probes and their adapters; LLM-run new-row probes; and the
joint outcome. Docker and the model roles are fakes."""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from costeval import executor, grading, node_grading as ng  # noqa: E402
import grade_node  # noqa: E402

REAL_CHANGES = Path("/Users/jess/src/lid-cost-eval/docs/research/cost-eval/seeds/opengym/hidden/m2h-changes.md")
REAL_GUARDS = REAL_CHANGES.parent / "m2h-guard-rows.json"

CHANGES = """# openGym M2h changes

Preamble.

## Change 1 — One watch at a time

**Type:** api-change-app-depends
**Intent distance:** other part
**Edits part:** api
**Edits file:** api/watch-relay.js
**Intent lives in:** frontend/src/views/ZeppSettings.jsx
**Searchability tier:** hidden. No name or value search finds the dependent line.

### Owner request

> can we make it one Zepp watch per person?

### New rows

| ID | Behaviour | Disclosure kind | Check |
|---|---|---|---|
| OGM-0101 | A successful Zepp pairing leaves only the newly paired watch linked. | Stated | Server routes: redeem two codes. |
| OGM-0102 | The existing watch stays connected when a pairing starts. | Askable | Server routes: abandon a code. |
| OGM-0104 | The page says which watch is paired. | Stated | Web app. |

- **OGM-0102** recall: “the old one should still work.”

**Guard row:** OGM-0102. The untouched code meets it by design.

### Behaviour to keep

| Behaviour | Established in | How a careless version breaks it | Check |
|---|---|---|---|
| Zepp settings notices a pairing. | a | b | c |

**Dependency exercised only if** a second redemption leaves the profile one watch (the server replaces links). Otherwise the dependency is **not exercised** for that fork, never kept.

### Retired tests

None. The right build fails no existing test.

### Repair reports

- **OGM-0101:** “I paired a second watch and didn't end up with just the new one.”
- **OGM-0102:** “My old watch stopped connecting.”
- **OGM-0104:** “The page didn't say which watch.”
- **Dependency:** “The code didn't clear.”

## Change 2 — A phone pairing code like the watch’s

**Type:** api-change-app-depends
**Edits part:** api
**Searchability tier:** one-step grep. A search for the screen text lands on it.

### Owner request

> could the phone pairing code look like the watch one?

### New rows

| ID | Behaviour | Disclosure kind | Check |
|---|---|---|---|
| OGM-0201 | New phone pairing codes have three groups of four. | Stated | Server routes. |

**Dependency exercised only if** the server mints a grouped 12-character code. Otherwise **not exercised**.

### Retired tests

- api/test/server-pairing.test.js::minting a pairing code asks the owner proof: a session alone gets none — update the old code-shape assertion, not the proof requirement.
- frontend/src/views/Home.queue.test.jsx::a managed pass counts your own day beside it — ownership plays no part — its fixture leaves Motivation unset; kept with the fixture opted in
- frontend/src/views/settings-pages.test.jsx, the five scenario tests whose titles are made at run time — their fixtures leave Motivation unset

### Repair reports

- **OGM-0201:** “It wasn't three groups of four.”
- **Dependency:** “The phone didn't sign in.”

## Change 9 — A join code good for 90 days

**Type:** control
**Edits part:** api
**Searchability tier:** one-step grep. The route calls `createCode` directly.

### Owner request

> could the gym join code be good for 90 days?

### New rows

| ID | Behaviour | Disclosure kind | Check |
|---|---|---|---|
| OGM-0901 | A normal gym-lead join code gets a 90-day expiry by default. | Stated | Server routes. |
| OGM-0903 | A gym lead can still ask for a shorter-lived code. | Askable | Server routes. |

**Guard row:** OGM-0903. The untouched code meets it by design.

**Comparison row:** the first kept row (trainer codes stay within 30 days). It is **exercised only if** a gym join code lasts 90 days; otherwise **not exercised**, never kept.

### Retired tests

None found.

### Repair reports

- **OGM-0901:** “It wasn't 90 days out.”
- **OGM-0903:** “It didn't get a one-week expiry.”
"""

PROBES = """# M2h probes

Preamble.

## Setups

### S0: A fresh server

An isolated data folder.

Each probe is independent.

### S1: A paired watch

Built on S0: one watch paired.

## Probes

### OGM-0101 A successful pairing leaves only the new watch

#### P-OGM0101-a

- **Applies:** from change 1, until change 1
- **Needs:** api
- **Setup:** S1
- **Scenario:** Redeem a second code for the same profile and read the links.
- **Expected observation:** Only the second watch is listed.

### OGM-0102 The existing watch stays connected

#### P-OGM0102-a

- **Applies:** from change 1, until change 1
- **Needs:** api
- **Setup:** S1
- **Scenario:** Request a code and leave it; use the old watch credential.
- **Expected observation:** It works both times.

### OGM-0104 The page says which watch is paired

#### P-OGM0104-a

- **Applies:** from change 1, until change 1
- **Needs:** fe, api
- **Setup:** S1
- **Runs only if:** OGM-0101 implemented
- **Exercised only if:** the page lists a watch at all
- **Scenario:** Open the settings page and read the paired watch's name.
- **Expected observation:** The new watch's name is shown.

### OGM-0201 New codes are grouped

#### P-OGM0201-a

- **Applies:** from change 2, until change 2
- **Needs:** none
- **Setup:** S0
- **Scenario:** Mint a code.
- **Expected observation:** It is grouped.
"""


def node_lines(results, counts=None, failed_files=()):
    """Reporter lines (the grader's node --test reporter): results are (file, ancestors, name, status[, error])."""
    out = []
    for r in results:
        file, anc, name, status = r[:4]
        ev = {"event": "test", "file": file, "name": name, "ancestors": list(anc), "nesting": len(anc), "type": "test",
              "status": status}
        if len(r) > 4:
            ev["error"] = r[4]
        out.append(json.dumps(ev))
    for f, msg in failed_files:
        out.append(json.dumps({"event": "file-failed", "file": f, "message": msg}))
    for k, v in (counts or {}).items():
        out.append(json.dumps({"event": "count", "key": k, "value": v}))
    return "\n".join(out) + "\n"


def vitest_json(files, root="/work/app"):
    """A vitest JSON report: files maps a path to (status, message, [(ancestors, title, status, messages)])."""
    results, total, passed, failed = [], 0, 0, 0
    for path, (status, message, tests) in files.items():
        ar = []
        for anc, title, st, msgs in tests:
            total += 1
            passed += st == "passed"
            failed += st == "failed"
            ar.append({"ancestorTitles": list(anc), "title": title, "fullName": " ".join([*anc, title]), "status": st,
                       "failureMessages": list(msgs)})
        results.append({"name": f"{root}/{path}", "status": status, "message": message, "assertionResults": ar})
    return json.dumps({"numTotalTests": total, "numPassedTests": passed, "numFailedTests": failed,
                       "numPendingTests": 0, "numTodoTests": 0, "testResults": results})


def run_of(tests, failures=None, counts=None):
    """A parsed run as the parsers return it."""
    return {"tests": {t["id"]: t for t in tests}, "file_failures": failures or {}, "counts": counts or {}}


def rec(file, title, status="passed", anc=(), **kw):
    return {"id": ng.test_id(file, list(anc), title), "file": file, "title": title, "ancestors": list(anc),
            "status": status, **kw}


# ------------------------------------------------------------------------------------------------- the seed


class ChangesTest(unittest.TestCase):
    def test_rows_disclosures_guards_lines_tiers_retired_tests_and_repair_reports(self):
        cs = ng.parse_changes(CHANGES)
        self.assertEqual(sorted(cs), [1, 2, 9])
        c1 = cs[1]
        self.assertEqual(c1.title, "One watch at a time")
        self.assertEqual(c1.type, "api-change-app-depends")
        self.assertEqual(c1.edits_part, "api")
        self.assertEqual(c1.tier, "hidden")
        self.assertEqual([(r.id, r.disclosure) for r in c1.rows],
                         [("OGM-0101", "Stated"), ("OGM-0102", "Askable"), ("OGM-0104", "Stated")])
        self.assertEqual(c1.guard_rows, ["OGM-0102"])
        self.assertTrue(c1.exercised_only_if.startswith("a second redemption leaves the profile one watch"))
        self.assertIsNone(c1.comparison_row)
        self.assertEqual(c1.retired, [])
        self.assertEqual(c1.repair_reports["Dependency"], "The code didn't clear.")
        self.assertEqual(c1.repair_reports["OGM-0101"], "I paired a second watch and didn't end up with just the new one.")
        self.assertIn("one Zepp watch per person", c1.request)

    def test_a_retired_test_is_its_file_and_the_rest_of_its_line_and_a_line_without_a_title_is_kept_apart(self):
        c2 = ng.parse_changes(CHANGES)[2]
        self.assertEqual(c2.retired[0][0], "api/test/server-pairing.test.js")
        self.assertTrue(c2.retired[0][1].startswith("minting a pairing code asks the owner proof"))
        self.assertEqual(len(c2.retired), 2)
        self.assertEqual(len(c2.retired_unparsed), 1)
        self.assertIn("settings-pages.test.jsx", c2.retired_unparsed[0])

    def test_a_title_that_holds_a_dash_matches_whatever_note_follows_it(self):
        c2 = ng.parse_changes(CHANGES)[2]
        title = "a managed pass counts your own day beside it — ownership plays no part"
        hit = rec("frontend/src/views/Home.queue.test.jsx", title)
        near = rec("frontend/src/views/Home.queue.test.jsx", "a managed pass counts your own day beside it")
        self.assertTrue(ng.retired_match(hit, c2.retired))
        self.assertTrue(ng.retired_match(near, c2.retired))  # a shorter title the line also starts with, then a dash
        self.assertFalse(ng.retired_match(rec("frontend/src/views/Home.queue.test.jsx", "a managed pass"), c2.retired))
        self.assertFalse(ng.retired_match(rec("frontend/src/views/Other.test.jsx", title), c2.retired))

    def test_a_control_has_a_comparison_row_in_place_of_a_dependency_line(self):
        c9 = ng.parse_changes(CHANGES)[9]
        self.assertEqual(c9.type, "control")
        self.assertIsNone(c9.exercised_only_if)
        self.assertIn("a gym join code lasts 90 days", c9.comparison_row)
        self.assertEqual(c9.guard_rows, ["OGM-0903"])

    @unittest.skipUnless(REAL_CHANGES.exists(), "the hidden seed isn't here")
    def test_the_real_seed_parses(self):
        cs = ng.parse_changes(REAL_CHANGES.read_text(encoding="utf-8"))
        self.assertEqual(sorted(cs), list(range(1, 13)))
        # change 8's 46: 41 named by title, and one line naming the five whose titles are made at run time
        self.assertEqual({n: len(c.retired) for n, c in cs.items() if c.retired}, {2: 1, 6: 2, 7: 2, 8: 41, 11: 5})
        self.assertEqual(len(cs[8].retired_unparsed), 1)
        self.assertEqual([r.id for r in cs[4].rows], ["OGM-0401", "OGM-0402", "OGM-0403", "OGM-0404", "OGM-0405"])
        self.assertEqual([r.disclosure for r in cs[4].rows], ["Stated", "Stated", "Stated", "Askable", "Askable"])
        self.assertEqual({n: c.tier for n, c in cs.items()}[1], "hidden")
        self.assertEqual(cs[3].tier, "documented")
        self.assertTrue(all(c.exercised_only_if for n, c in cs.items() if n <= 8))
        self.assertTrue(all(c.comparison_row for n, c in cs.items() if n >= 9))
        guards = set(ng.load_guard_rows(REAL_GUARDS))
        self.assertEqual(guards, {g for c in cs.values() for g in c.guard_rows})
        self.assertTrue(all(set(c.repair_reports) >= {r.id for r in c.rows} for c in cs.values()))


# ---------------------------------------------------------------------------------------------- test output


class ReporterTest(unittest.TestCase):
    def test_node_results_by_file_and_title_with_parents_rolled_up_and_file_failures_apart(self):
        text = node_lines([
            ("api/test/a.test.js", [], "top passes", "passed"),
            ("api/test/a.test.js", ["group"], "inner fails", "failed",
             {"message": "boom", "failureType": "testCodeFailure", "actual": {"a": 1}, "expected": {"a": 2}}),
            ("api/test/a.test.js", [], "parent", "failed", {"message": "1 subtest failed", "failureType": "subtestsFailed"}),
            ("api/test/a.test.js", ["parent"], "child bad", "failed", {"message": "1 !== 2"}),
            ("api/test/a.test.js", ["group"], "inner skipped", "skipped")],
            counts={"tests": 5, "pass": 1, "fail": 3}, failed_files=[("api/test/b.test.js", "Cannot find module")])
        text += '{"event": "test", "file": "api/test/a.test.js", "name": "group", "ancestors": [], "type": "suite", "status": "failed"}\nnot json\n'
        run = ng.parse_node_events(text)
        tests = run["tests"]
        self.assertEqual(sorted(tests), sorted([
            "api/test/a.test.js::top passes", "api/test/a.test.js::group > inner fails", "api/test/a.test.js::parent",
            "api/test/a.test.js::parent > child bad", "api/test/a.test.js::group > inner skipped"]))
        self.assertTrue(tests["api/test/a.test.js::parent"].get("rollup"))
        self.assertEqual(tests["api/test/a.test.js::group > inner fails"]["title"], "inner fails")
        self.assertEqual(tests["api/test/a.test.js::group > inner fails"]["error"]["expected"], {"a": 2})
        self.assertEqual(run["file_failures"], {"api/test/b.test.js": "Cannot find module"})
        self.assertEqual(run["counts"], {"tests": 5, "pass": 1, "fail": 3})

    def test_a_repeated_title_in_one_scope_keeps_both(self):
        text = node_lines([("api/test/a.test.js", [], "same", "passed"), ("api/test/a.test.js", [], "same", "failed")])
        self.assertEqual(sorted(ng.parse_node_events(text)["tests"]), ["api/test/a.test.js::same", "api/test/a.test.js::same #2"])

    def test_vitest_results_load_failures_and_tests_a_failed_file_never_ran(self):
        text = vitest_json({
            "frontend/src/a.test.jsx": ("failed", "", [(["Box"], "shows", "passed", []), (["Box"], "hides", "failed", ["AssertionError: x"])]),
            "frontend/src/b.test.jsx": ("failed", "Cannot find module '../lib/gone.js'\n at x", []),
            "frontend/src/c.test.jsx": ("failed", "", [([], "after a hook", "skipped", [])])})
        run = ng.parse_vitest_json(text)
        t = run["tests"]
        self.assertEqual(t["frontend/src/a.test.jsx::Box > hides"]["status"], "failed")
        self.assertIn("AssertionError", t["frontend/src/a.test.jsx::Box > hides"]["error"]["message"])
        self.assertEqual(run["file_failures"], {"frontend/src/b.test.jsx": "Cannot find module '../lib/gone.js'"})
        self.assertTrue(t["frontend/src/c.test.jsx::after a hook"].get("in_failed_file"))
        self.assertEqual(run["counts"]["tests"], 3)

    def test_the_reporter_and_suite_commands(self):
        self.assertIn("test:pass", ng.NODE_REPORTER)
        self.assertIn("file-failed", ng.NODE_REPORTER)
        api = ng.SUITES["api"].command("/work/out/runs/fork/api")
        self.assertIn("node --test", api)
        self.assertIn(f"--test-reporter={ng.REPORTER_PATH}", api)
        self.assertIn("--test-reporter-destination=/work/out/runs/fork/api.jsonl", api)
        self.assertIn("test/*.test.js", api)
        fe = ng.SUITES["frontend"].command("/work/out/runs/fork/frontend", files=["src/x.test.jsx"])
        self.assertIn("npx vitest run", fe)
        self.assertIn("--outputFile.json=/work/out/runs/fork/frontend.json", fe)
        self.assertTrue(fe.rstrip().endswith("src/x.test.jsx"))
        self.assertIn("npm test --", ng.SUITES["mcp"].command("/o/mcp"))
        self.assertEqual(ng.SUITES["zepp"].package, "watch-zepp")
        self.assertIn("npm ci", ng.SUITES["zepp"].install)
        self.assertEqual(ng.DEFAULT_SUITES, ("api", "frontend", "mcp", "zepp"))
        self.assertEqual(ng.suite_of("watch-zepp/test/page.test.js"), "zepp")
        self.assertEqual(ng.suite_of("frontend/src/a.test.jsx"), "frontend")
        self.assertIsNone(ng.suite_of("docs/x.md"))


class TestFilesTest(unittest.TestCase):
    def test_which_paths_are_tests_or_their_support(self):
        for p in ("api/test/server-pairing.test.js", "api/test/helpers.mjs", "api/test/fixtures/media-refs.json",
                  "frontend/src/lib/a.test.js", "frontend/src/components/DateField.test-util.js",
                  "frontend/src/test-setup.js", "watch-zepp/test/fakes/zos.js", "mcp/test/state.test.js",
                  "frontend/scripts/app-icons.test.mjs"):
            self.assertTrue(ng.is_test_path(p), p)
        for p in ("api/server.js", "frontend/src/lib/api.js", "frontend/vite.config.js", "docs/MOBILE.md",
                  "frontend/node_modules/x/test/a.test.js", "frontend/src/lib/testing-grounds.js"):
            self.assertFalse(ng.is_test_path(p), p)

    def test_the_arms_edits_to_the_starts_tests_are_listed_and_undone_for_keeping(self):
        ns = ("M\tapi/test/server-pairing.test.js\nD\tfrontend/src/lib/a.test.js\nR087\tapi/test/old.test.js\tapi/test/new.test.js\n"
              "A\tapi/test/mine.test.js\nM\tapi/server.js\nM\tfrontend/vite.config.js\n")
        plan = ng.test_file_plan(ns)
        self.assertEqual(plan["edited"], ["api/test/server-pairing.test.js"])
        self.assertEqual(plan["deleted"], ["frontend/src/lib/a.test.js"])
        self.assertEqual(plan["renamed"], [["api/test/old.test.js", "api/test/new.test.js"]])
        self.assertEqual(plan["added"], ["api/test/mine.test.js"])
        self.assertEqual(plan["restore"], ["api/test/old.test.js", "api/test/server-pairing.test.js", "frontend/src/lib/a.test.js"])
        self.assertEqual(plan["remove"], ["api/test/mine.test.js", "api/test/new.test.js"])
        self.assertEqual(plan["suite_config_changed"], ["frontend/vite.config.js"])


# --------------------------------------------------------------------------------------------------- keeping


class KeepingTest(unittest.TestCase):
    def test_tests_that_passed_on_the_start_are_counted_and_the_others_kept_apart(self):
        base = {"api": run_of([rec("api/test/a.test.js", "one"), rec("api/test/a.test.js", "two"),
                               rec("api/test/a.test.js", "three"), rec("api/test/b.test.js", "four"),
                               rec("api/test/a.test.js", "broken at the pin", "failed"),
                               rec("api/test/a.test.js", "skipped", "skipped"),
                               rec("api/test/a.test.js", "parent", rollup=True)])}
        fork = {"api": run_of([rec("api/test/a.test.js", "one"),
                               rec("api/test/a.test.js", "two", "failed", error={"message": "2 !== 3"}),
                               rec("api/test/a.test.js", "broken at the pin", "failed"),
                               rec("api/test/a.test.js", "parent", "failed", rollup=True)],
                              failures={"api/test/b.test.js": "Cannot find module"})}
        k = ng.compare_keeping(base, fork)
        self.assertEqual((k["counted"], k["passed"], k["failed"], k["not_loaded"], k["not_run"]), (4, 1, 1, 1, 1))
        self.assertEqual(list(k["failures"]), ["api/test/a.test.js::two"])
        self.assertEqual(k["failures"]["api/test/a.test.js::two"]["message"], "2 !== 3")
        self.assertEqual(k["not_loaded_files"], {"api/test/b.test.js": {"error": "Cannot find module", "tests": 1}})
        self.assertEqual(k["not_loaded_by_cause"], {"missing module": 1})  # outside the share, reported by cause
        self.assertEqual(k["not_run_tests"], ["api/test/a.test.js::three"])
        self.assertEqual(k["share_passed"], 0.5)

    def test_a_test_a_failed_file_skipped_counts_as_failed(self):
        base = {"frontend": run_of([rec("frontend/src/c.test.jsx", "after a hook")])}
        fork = {"frontend": run_of([rec("frontend/src/c.test.jsx", "after a hook", "skipped", in_failed_file="hook threw")])}
        k = ng.compare_keeping(base, fork)
        self.assertEqual(k["failed"], 1)
        self.assertIn("didn't run", k["failures"]["frontend/src/c.test.jsx::after a hook"]["message"])

    def test_retired_tests_go_and_those_an_adjustment_touches_are_compared_with_the_adjusted_start(self):
        retired = [("api/test/p.test.js", "old shape — update it"), ("api/test/q.test.js", "gone"),
                   ("api/test/z.test.js", "never there")]
        base = {"api": run_of([rec("api/test/p.test.js", "old shape"), rec("api/test/p.test.js", "neighbour"),
                               rec("api/test/q.test.js", "gone"), rec("api/test/q.test.js", "stays")])}
        adjusted = {"api": run_of([rec("api/test/p.test.js", "old shape"), rec("api/test/p.test.js", "neighbour"),
                                   rec("api/test/p.test.js", "pins the new default", "failed")])}
        fork = {"api": run_of([rec("api/test/p.test.js", "old shape", "failed", error={"message": "x"}),
                               rec("api/test/p.test.js", "neighbour"), rec("api/test/p.test.js", "pins the new default"),
                               rec("api/test/q.test.js", "gone", "failed"), rec("api/test/q.test.js", "stays")])}
        k = ng.compare_keeping(base, fork, retired=retired, adjusted=adjusted, touched={"api/test/p.test.js"},
                               declared_pinning={"api/test/p.test.js::pins the new default", "api/test/p.test.js::neighbour"})
        self.assertEqual((k["counted"], k["passed"], k["failed"]), (3, 2, 1))  # q's "gone" is retired, p's from the adjusted start
        self.assertEqual(k["retired"]["excluded"], ["api/test/q.test.js::gone"])
        self.assertEqual(k["retired"]["covered_by_adjustment"], ["api/test/p.test.js::old shape"])
        self.assertEqual(k["retired"]["unmatched"], ["api/test/z.test.js::never there"])
        self.assertEqual(k["adjusted"]["pinning"], {"api/test/p.test.js::pins the new default": "passed"})
        self.assertEqual(k["adjusted"]["tests"]["api/test/p.test.js::old shape"], {"start": "passed", "fork": "failed", "counted": True})
        self.assertEqual(k["adjusted"]["pinning_mismatch"], {"declared, but passed on the start": ["api/test/p.test.js::neighbour"],
                                                             "failed on the start, not declared": []})

    def test_an_adjustment_without_its_adjusted_start_is_refused(self):
        with self.assertRaises(ValueError):
            ng.compare_keeping({"api": run_of([])}, {"api": run_of([])}, touched={"api/test/p.test.js"})

    def test_a_flaky_test_is_matched_by_its_files_name_alone(self):
        flaky = ng.flaky_entries(None)
        self.assertEqual(flaky, [{"suite": "frontend", "name": "useStore.stale-sync"}, {"suite": "api", "name": "server-origin-hint"}])
        hit = rec("frontend/src/store/useStore.stale-sync.test.jsx", "t", "failed")
        self.assertTrue(ng.is_flaky(hit, "frontend", flaky))
        self.assertFalse(ng.is_flaky(rec("frontend/src/store/useStore.stale-sync-server.test.jsx", "t", "failed"), "frontend", flaky))
        self.assertFalse(ng.is_flaky(hit, "api", flaky))
        self.assertEqual(ng.flaky_entries("none"), [])
        self.assertEqual(ng.flaky_entries('[{"suite": "api", "name": "x"}]'), [{"suite": "api", "name": "x"}])


class NotLoadedCauseTest(unittest.TestCase):
    def test_an_unloadable_files_error_names_its_cause(self):
        cases = {"Error: Cannot find module './relay.js'": "missing module",
                 "Error [ERR_MODULE_NOT_FOUND]: Cannot find package 'x'": "missing module",
                 "SyntaxError: The requested module './a.js' does not provide an export named 'WATCH_LINKS_MAX'":
                     "missing export",
                 "SyntaxError: Unexpected token '}'": "syntax error",
                 "ReferenceError: foo is not defined": "reference error",
                 "TypeError: x is not a function": "type error",
                 "something else entirely, at length": "other"}
        for msg, cause in cases.items():
            self.assertEqual(ng.not_loaded_cause(msg), cause, msg)


class FakeCk:
    """A checkpoint whose files live in a dict; suite runs answer from canned reporter output."""

    def __init__(self, outputs=None, commit="c0", name="ck"):
        self.files, self.scripts, self.networks = {}, [], []
        self.outputs = outputs or {}  # (label, suite) -> reporter text, or a list of them for repeated runs
        self.commit, self.name = commit, name
        self.exported_from = None
        self.dropped = False

    @property
    def volume(self):
        return f"{self.name}-grade"

    def put(self, path, text):
        self.files[path] = text

    def get(self, path):
        return self.files.get(path)

    def export(self, volume):
        self.exported_from = volume

    def drop(self):
        self.dropped = True

    def sh(self, script, stdin=None, check=True, network=False):
        self.scripts.append(script)
        self.networks.append(network)
        m = re.search(r"/work/out/runs/([\w.-]+)/([\w-]+)\.(jsonl|json) ", script + " ")
        if m:
            label, suite, ext = m.groups()
            out = self.outputs.get((label, suite))
            if isinstance(out, list):
                out = out.pop(0) if out else None
            if out is not None:
                self.files[f"/work/out/runs/{label}/{suite}.{ext}"] = out
                self.files[f"/work/out/runs/{label}/{suite}.log"] = f"log of {label} {suite}"
            return ""
        if "git diff --name-status" in script:
            return self.files.get("@name-status", "")
        if "git diff --numstat" in script:
            return self.files.get("@numstat", "")
        if script.startswith("cd /work/app && git diff ") or " git diff " in script and "arm.diff" not in script:
            return self.files.get("@diff", "")
        if "git ls-files" in script:
            return self.files.get("@ls-files", "")
        return ""


class RunSuitesTest(unittest.TestCase):
    def test_a_suite_runs_in_its_package_with_both_reporters_and_zepp_installs_with_the_network(self):
        ck = FakeCk({("fork", "api"): node_lines([("api/test/a.test.js", [], "one", "passed")], counts={"tests": 1}),
                     ("fork", "zepp"): node_lines([("watch-zepp/test/s.test.js", [], "z", "passed")])})
        runs = ng.run_suites(ck, ["api", "zepp"], "fork", flaky=[], reruns=3)
        self.assertEqual(list(runs["api"]["tests"]), ["api/test/a.test.js::one"])
        self.assertEqual(runs["api"]["counts"], {"tests": 1})
        self.assertEqual(ck.files[ng.REPORTER_PATH], ng.NODE_REPORTER)
        install = [s for s, net in zip(ck.scripts, ck.networks) if "npm ci" in s]
        self.assertEqual(len(install), 1)
        self.assertTrue(ck.networks[ck.scripts.index(install[0])])
        self.assertTrue(all(not net for s, net in zip(ck.scripts, ck.networks) if "npm ci" not in s))
        self.assertIn("cd /work/app/watch-zepp", install[0])
        api_run = next(s for s in ck.scripts if "/work/out/runs/fork/api.jsonl" in s)
        self.assertIn("cd /work/app/api", api_run)
        self.assertIn("timeout 1800", api_run)

    def test_a_flaky_failure_is_rerun_alone_and_counts_as_passed_once_it_passes(self):
        f = "frontend/src/store/useStore.stale-sync.test.jsx"
        first = vitest_json({f: ("failed", "", [([], "syncs", "failed", ["stale"])]),
                             "frontend/src/other.test.jsx": ("failed", "", [([], "real", "failed", ["no"])])})
        again = [vitest_json({f: ("failed", "", [([], "syncs", "failed", ["stale"])])}),
                 vitest_json({f: ("passed", "", [([], "syncs", "passed", [])])})]
        ck = FakeCk({("fork", "frontend"): first, ("fork-rerun-frontend", "frontend"): again})
        runs = ng.run_suites(ck, ["frontend"], "fork", flaky=ng.flaky_entries(None), reruns=3)
        t = runs["frontend"]["tests"]
        self.assertEqual(t[f"{f}::syncs"]["status"], "passed")
        self.assertEqual(t[f"{f}::syncs"]["flaky_runs"], ["failed", "failed", "passed"])
        self.assertEqual(t["frontend/src/other.test.jsx::real"]["status"], "failed")  # not on the list: never rerun
        reruns = [s for s in ck.scripts if "fork-rerun-frontend" in s and "vitest" in s]
        self.assertEqual(len(reruns), 2)
        self.assertTrue(all(s.rstrip().endswith("src/store/useStore.stale-sync.test.jsx") for s in reruns))
        self.assertEqual(runs["frontend"]["flaky"], {f"{f}::syncs": ["failed", "failed", "passed"]})

    def test_a_flaky_failure_that_never_passes_alone_stays_failed(self):
        f = "api/test/server-origin-hint.test.js"
        bad = node_lines([(f, [], "hint", "failed", {"message": "load"})])
        ck = FakeCk({("fork", "api"): bad, ("fork-rerun-api", "api"): [bad, bad]})
        runs = ng.run_suites(ck, ["api"], "fork", flaky=ng.flaky_entries(None), reruns=2)
        self.assertEqual(runs["api"]["tests"][f"{f}::hint"]["status"], "failed")
        self.assertEqual(runs["api"]["tests"][f"{f}::hint"]["flaky_runs"], ["failed", "failed", "failed"])

    def test_a_suite_with_no_report_says_so(self):
        runs = ng.run_suites(FakeCk(), ["mcp"], "fork", flaky=[], reruns=1)
        self.assertEqual(runs["mcp"]["tests"], {})
        self.assertIn("no report", runs["mcp"]["error"])


class AdjustmentTest(unittest.TestCase):
    PATCH = ("diff --git a/api/test/p.test.js b/api/test/p.test.js\n--- a/api/test/p.test.js\n+++ b/api/test/p.test.js\n"
             "@@ -1 +1 @@\n-old\n+new\n")

    def graded(self, **adj):
        d = Path(tempfile.mkdtemp())
        (d / "adjusted").mkdir()
        (d / "adjusted" / "change-02.patch").write_text(self.PATCH)
        (d / "adjusted" / "copy.test.js").write_text("copy\n")
        manifest = {"version": 1, "adjustments": {"2": {"kind": "adjusted copies", "patch": "adjusted/change-02.patch",
                                                        "files": {"api/test/r.test.js": "adjusted/copy.test.js"},
                                                        "tests": ["api/test/p.test.js::old shape"], **adj}}}
        (d / "graded.json").write_text(json.dumps(manifest))
        return d

    def test_an_adjustment_is_a_patch_and_whole_file_copies_on_the_starts_tests(self):
        d = self.graded()
        g = ng.load_graded(d)
        adj = ng.adjustment_for(g, 2)
        self.assertEqual(ng.adjustment_touched(d, adj), ["api/test/p.test.js", "api/test/r.test.js"])
        ck = FakeCk()
        touched = ng.apply_adjustment(ck, d, adj)
        self.assertEqual(touched, ["api/test/p.test.js", "api/test/r.test.js"])
        self.assertEqual(ck.files["/work/app/api/test/r.test.js"], "copy\n")
        self.assertEqual(ck.files["/work/grader/adjust.patch"], self.PATCH)
        self.assertTrue(any("git apply" in s and "/work/grader/adjust.patch" in s for s in ck.scripts))
        self.assertIsNone(ng.adjustment_for(g, 3))
        self.assertEqual(len(ng.adjustment_key(d, adj)), 12)

    def test_an_adjustment_may_touch_only_test_files(self):
        d = self.graded(files={"api/server.js": "adjusted/copy.test.js"})
        with self.assertRaisesRegex(ValueError, "only test files"):
            ng.adjustment_touched(d, ng.adjustment_for(ng.load_graded(d), 2))


# ------------------------------------------------------------------------------------------- dependency probes


def dep(title, status="passed", anc=(), message=""):
    r = rec("frontend/src/__graded__/d.test.jsx", title, status, anc)
    if message:
        r["error"] = {"message": message}
    return r


class DependencyOutcomeTest(unittest.TestCase):
    def outcome(self, tests, failures=None, **kw):
        return ng.dependency_outcome(run_of(tests, failures), **kw)

    def test_the_four_results(self):
        self.assertEqual(self.outcome([dep("precondition: one watch left"), dep("dependency: 0 links"),
                                       dep("dependency: 2 links")])["result"], "kept")
        self.assertEqual(self.outcome([dep("precondition: one watch left"), dep("dependency: 0 links"),
                                       dep("dependency: 2 links", "failed", message="code stayed")])["result"], "broken")
        r = self.outcome([dep("precondition: one watch left", "failed", message="two links"), dep("dependency: 0 links")])
        self.assertEqual(r["result"], "not exercised")
        self.assertTrue(r["witness"]["dependency_passed"])  # the dependency side as it stood, for the pin's witness
        self.assertEqual(self.outcome([], failures={"frontend/src/__graded__/d.test.jsx": "SyntaxError"})["result"], "missing")

    def test_a_setup_failure_is_missing_never_broken_and_names_its_row_when_tagged(self):
        r = self.outcome([dep("setup[OGM-0201]: a phone code is issued", "failed", message="401"),
                          dep("precondition: grouped"), dep("dependency: typed", "failed")],
                         repair_reports={"OGM-0201": "It wasn't three groups of four."})
        self.assertEqual(r["result"], "missing")
        self.assertEqual(r["failed_setup"], {"postcondition": "a phone code is issued", "row": "OGM-0201",
                                             "repair_report": "It wasn't three groups of four."})
        r = self.outcome([dep("precondition: grouped"), dep("dependency: typed", "failed", message="setup: server never started")])
        self.assertEqual((r["result"], r["failed_setup"]["postcondition"]), ("missing", "server never started"))
        self.assertIsNone(r["failed_setup"]["row"])

    def test_a_probe_without_both_kinds_or_with_results_missing_is_missing(self):
        self.assertEqual(self.outcome([dep("dependency: x")])["cause"], "no precondition test")
        self.assertEqual(self.outcome([dep("precondition: x")])["cause"], "no dependency test")
        self.assertEqual(self.outcome([dep("precondition: x"), dep("dependency: y", "skipped")])["result"], "missing")
        self.assertEqual(self.outcome([dep("precondition: x", "skipped"), dep("dependency: y")])["result"], "missing")

    def test_a_role_can_sit_on_the_describe_around_a_test(self):
        self.assertEqual(self.outcome([dep("one watch left", anc=["precondition: replacement"]),
                                       dep("no links", anc=["dependency: settings notices"])])["result"], "kept")

    def test_a_change_rolls_up_over_its_counting_probes(self):
        roll = ng.dependency_rollup
        self.assertEqual(roll({"a": {"result": "kept"}, "b": {"result": "broken"}}, ["a", "b"])["result"], "broken")
        self.assertEqual(roll({"a": {"result": "kept"}, "b": {"result": "missing"}}, ["a", "b"])["result"], "missing")
        self.assertEqual(roll({"a": {"result": "kept"}}, ["a"])["result"], "kept")
        mixed = roll({"a": {"result": "kept"}, "b": {"result": "not exercised"}}, ["a", "b"])
        self.assertEqual((mixed["result"], mixed["mixed"]), ("not exercised", True))  # never an unexercised case as kept
        self.assertEqual(roll({"a": {"result": "broken"}, "s": {"result": "kept"}}, ["s"])["result"], "kept")  # a kept-row extra
        self.assertEqual(roll({}, [])["result"], "missing")

    def test_notes_printed_by_a_probe_are_kept(self):
        self.assertEqual(ng.probe_notes("x\nNOTE storage: new key cycleLog\n  NOTE other: 2\n\x1b[22mNOTE colour: kept\x1b[0m\n"),
                         {"storage": "new key cycleLog", "other": "2", "colour": "kept"})


class DependencyRunTest(unittest.TestCase):
    def graded(self, adapter=None):
        d = Path(tempfile.mkdtemp())
        (d / "dependency" / "change-01").mkdir(parents=True)
        (d / "dependency" / "change-01" / "d.test.jsx").write_text("// probe\n")
        (d / "dependency" / "change-01" / "adapter.js").write_text("export const available = true\n")
        (d / "dependency" / "change-01" / "adapter.md").write_text("Export `pair(code)`.\n")
        entry = {"id": "dep-01", "change": 1, "row": "dependency", "suite": "frontend",
                 "file": "dependency/change-01/d.test.jsx", "dest": "frontend/src/__graded__/d.test.jsx"}
        if adapter:
            entry["adapter"] = adapter
        (d / "graded.json").write_text(json.dumps({"version": 1, "dependency_probes": [entry]}))
        return d

    def test_a_probe_is_put_in_its_package_and_run_alone(self):
        d = self.graded()
        g = ng.load_graded(d)
        entries = ng.dependency_entries(g, 1)
        ck = FakeCk({("dep-dep-01", "frontend"): vitest_json({"frontend/src/__graded__/d.test.jsx": ("passed", "", [
            ([], "precondition: one watch", "passed", []), ([], "dependency: notices", "passed", [])])})})
        r = ng.run_dependency_probe(ck, entries[0], d)
        self.assertEqual(r["result"], "kept")
        self.assertEqual(ck.files["/work/app/frontend/src/__graded__/d.test.jsx"], "// probe\n")
        run = next(s for s in ck.scripts if "dep-dep-01" in s)
        self.assertTrue(run.rstrip().endswith("src/__graded__/d.test.jsx"))
        self.assertIn("cd /work/app/frontend", run)
        after = ck.scripts[ck.scripts.index(run) + 1:]  # the probe's checks leave the checkout once it has run
        self.assertTrue(any(x.startswith("cd /work/app && rm -f") and "frontend/src/__graded__/d.test.jsx" in x for x in after))

    def test_a_probe_reaching_into_the_watch_app_first_installs_its_dev_dependencies_once(self):
        # DEP-03 runs in the web app's suite, but its support file sits in watch-zepp, whose dev dependencies the starts
        # don't have: npm ci runs there first, with the network, once per checkout
        d = self.graded()
        entry = {**ng.dependency_entries(ng.load_graded(d), 1)[0],
                 "support": {"watch-zepp/test/m2h-kit/watch.mjs": "dependency/change-01/adapter.js"}}
        ck = FakeCk()
        ng.run_dependency_probe(ck, entry, d)
        ng.run_dependency_probe(ck, {**entry, "id": "dep-02"}, d)
        installs = [(sc, net) for sc, net in zip(ck.scripts, ck.networks) if "npm ci" in sc]
        self.assertEqual(len(installs), 2)  # each run checks; only the first installs (the marker)
        self.assertTrue(all(net for _, net in installs))
        self.assertTrue(all("cd /work/app/watch-zepp" in sc for sc, _ in installs))
        self.assertTrue(all("test -f" in sc for sc, _ in installs))
        first_run = next(i for i, sc in enumerate(ck.scripts) if "dep-dep-01" in sc)
        self.assertLess(ck.scripts.index(installs[0][0]), first_run)
        # a probe touching only the web app installs nothing
        ck2 = FakeCk()
        ng.run_dependency_probe(ck2, ng.dependency_entries(ng.load_graded(d), 1)[0], d)
        self.assertFalse(any("npm ci" in sc for sc in ck2.scripts))

    def test_the_adapter_writer_is_told_a_pin_adapter_saying_unavailable_is_not_one_to_keep(self):
        d = self.graded(self.adapter())
        prompt = ng.adapter_prompt(ng.dependency_entries(ng.load_graded(d), 1)[0], d)
        self.assertIn("available = false", prompt)
        self.assertIn("not one to keep", prompt)

    def adapter(self, **kw):
        return {"dest": "frontend/src/__graded__/adapter.js", "default": "dependency/change-01/adapter.js",
                "interface": "dependency/change-01/adapter.md", "operations": ["call the build's own pairing route"],
                "forbid": [r"writeFileSync"], **kw}

    def run_adapter(self, record, source):
        d = self.graded(self.adapter())
        entry = ng.dependency_entries(ng.load_graded(d), 1)[0]
        ck, calls = FakeCk(), []

        def run_role(role, prompt, json_schema=None):
            calls.append({"role": role, "prompt": prompt})
            if record is not None:
                ck.files["/work/out/adapters/dep-01.json"] = json.dumps(record)
            if source is not None:
                ck.files["/work/out/adapters/dep-01.js"] = source
            return SimpleNamespace(structured=None, text="ok", usage=SimpleNamespace(reported_cost_usd=0.1, models={}),
                                   duration_s=1.0)
        g = ng.NodeGraders(image="img", roles_volume="roles", claude_code="v")
        return ng.adapt(ck, g, entry, d, run_role=run_role), ck, calls

    def test_an_adapter_is_written_blind_to_the_arm_from_its_frozen_interface_and_operations(self):
        r, ck, calls = self.run_adapter({"status": "adapted", "evidence": [{"file": "api/server.js"}], "note": "a route",
                                         "notes": {"storage": "route"}}, "export const available = true\nexport function pair () {}\n")
        self.assertEqual(r["status"], "adapted")
        self.assertEqual(ck.files["/work/app/frontend/src/__graded__/adapter.js"], "export const available = true\nexport function pair () {}\n")
        prompt = calls[0]["prompt"]
        self.assertIn("Export `pair(code)`.", prompt)
        self.assertIn("call the build's own pairing route", prompt)
        self.assertIn("export const available = true", prompt)  # the pin's adapter, to keep where the build still fits it
        for word in ("bare", "LID", "arm"):
            self.assertNotRegex(prompt, rf"\b{word}\b")
        self.assertEqual(calls[0]["role"].isolation, executor.Isolation.for_public_seed(window="1m"))
        self.assertEqual(r["notes"], {"storage": "route"})

    def test_a_build_without_the_interface_gets_an_adapter_that_says_so_and_an_unclear_one_is_missing(self):
        r, ck, _ = self.run_adapter({"status": "absent", "evidence": [{"file": "api/server.js"}], "note": "no route"}, None)
        self.assertEqual(r["status"], "absent")
        self.assertIn("export const available = false", ck.files["/work/app/frontend/src/__graded__/adapter.js"])
        r, _, _ = self.run_adapter({"status": "unclear", "evidence": [], "note": "?"}, None)
        self.assertEqual(r["status"], "unusable")
        r, _, _ = self.run_adapter(None, None)
        self.assertEqual(r["status"], "unusable")

    def test_an_adapter_using_a_forbidden_operation_is_unusable(self):
        r, _, _ = self.run_adapter({"status": "adapted", "evidence": [{"file": "x"}], "note": "x"},
                                   "import fs from 'node:fs'\nfs.writeFileSync('db.json', '{}')\n")
        self.assertEqual(r["status"], "unusable")
        self.assertIn("writeFileSync", " ".join(r["problems"]))

    def test_without_the_adapter_step_the_pins_adapter_is_used(self):
        d = self.graded(self.adapter())
        entry = ng.dependency_entries(ng.load_graded(d), 1)[0]
        ck = FakeCk()
        r = ng.adapt(ck, None, entry, d, run_role=None)
        self.assertEqual(r["status"], "default")
        self.assertEqual(ck.files["/work/app/frontend/src/__graded__/adapter.js"], "export const available = true\n")


# ---------------------------------------------------------------------------------------------- new-row probes


class RoutingTest(unittest.TestCase):
    def test_needs_route_a_probe_to_its_package_and_runner(self):
        self.assertEqual(ng.route(("api",), "api")["package"], "api")
        fe = ng.route(("fe", "api"), "api")
        self.assertEqual((fe["package"], fe["runner"], fe["dir"]), ("frontend", "vitest", "frontend/src/__probes__"))
        self.assertEqual(ng.route(("zepp", "api", "fe"), "api")["package"], "frontend")
        self.assertEqual(ng.route(("watch", "server"), "api")["package"], "watch-zepp")
        self.assertEqual(ng.route((), "watch-zepp")["package"], "watch-zepp")  # none: the change's edited part
        self.assertEqual(ng.route((), "frontend")["package"], "frontend")
        with self.assertRaises(ValueError):
            ng.route(("kitchen",), "api")
        self.assertEqual(ng.probe_path("P-OGM0104-a", ng.route(("fe",), "api")),
                         "frontend/src/__probes__/probe_p_ogm0104_a.test.jsx")

    def test_a_precondition_field_is_read_as_the_probes_exercised_only_if_line(self):
        # the drafter's DEP-10 probe writes "Precondition"; the judge may then rule "not exercised" on it
        text = PROBES.replace("#### P-OGM0101-a\n", "#### P-OGM0101-a\n- **Precondition:** a distinct file is refused first.\n", 1)
        self.assertEqual(ng.probe_options(text)["P-OGM0101-a"]["exercised_only_if"], "a distinct file is refused first.")

    def test_a_judgment_still_wrong_on_one_probe_keeps_the_others_verdicts(self):
        verdicts = [{"probe": "P-OGM1001-a", "verdict": "not met"}, {"probe": "P-OGM1002-a", "verdict": "met"},
                    {"probe": "P-DEP10-a", "verdict": "not exercised"}]
        kept = ng.keep_valid(verdicts, ['P-DEP10-a: "not exercised" for a probe with no precondition line'])
        self.assertEqual(sorted(kept), ["P-OGM1001-a", "P-OGM1002-a"])  # only the probe the problem names is dropped
        self.assertEqual(ng.keep_valid(verdicts, ["the verdicts don't cover the batch"]), {})  # a problem with no probe: none
        self.assertEqual(sorted(ng.keep_valid(verdicts, [])), ["P-DEP10-a", "P-OGM1001-a", "P-OGM1002-a"])

    def test_optional_fields_and_conditions(self):
        opts = ng.probe_options(PROBES)
        self.assertEqual(opts["P-OGM0104-a"], {"runs_only_if": "OGM-0101 implemented",
                                               "exercised_only_if": "the page lists a watch at all"})
        self.assertEqual(opts["P-OGM0101-a"], {"runs_only_if": None, "exercised_only_if": None})
        holds = ng.condition_holds
        self.assertTrue(holds("OGM-0101 implemented", {"OGM-0101": "inherited"}, {}))
        self.assertFalse(holds("OGM-0101 implemented", {"OGM-0101": "absent"}, {}))
        self.assertIsNone(holds("OGM-0101 implemented", {"OGM-0101": "unclear"}, {}))
        self.assertTrue(holds("OGM-0101 met and OGM-0102 implemented", {"OGM-0102": "implemented"}, {"OGM-0101": "met"}))
        self.assertFalse(holds("OGM-0101 met", {}, {"OGM-0101": "not met"}))
        with self.assertRaises(ValueError):
            holds("when the moon is full", {}, {})


class GradeProbesTest(unittest.TestCase):
    def setUp(self):
        self.probeset = grading.parse_probes(PROBES)
        self.change = ng.parse_changes(CHANGES)[1]
        self.applicable = [p for p in self.probeset.probes if p.applies(1)]
        self.g = ng.NodeGraders(image="img", roles_volume="roles", claude_code="v")

    def run_probes(self, rulings, implementation, guards=frozenset(), conditions=None):
        """rulings: batch id -> probe -> (verdict, cause, fault[, postcondition, row])."""
        ck, calls, state = FakeCk(), [], {}
        usage = SimpleNamespace(reported_cost_usd=0.1, models={})

        def run_role(role, prompt, json_schema=None):
            calls.append({"role": role, "prompt": prompt, "schema": json_schema})
            if json_schema:
                out = []
                for pid, r in rulings[state["bid"]].items():
                    v, c, f = r[:3]
                    out.append({"probe": pid, "verdict": v, "evidence": [] if v == "couldn't exercise" else [2],
                                "reason": "The output shows what this probe needed to show.", "cause": c, "fault": f,
                                "failed_postcondition": r[3] if len(r) > 3 else "", "postcondition_row": r[4] if len(r) > 4 else "none"})
                return SimpleNamespace(structured={"verdicts": out}, text="", usage=usage, duration_s=1.0)
            m = re.search(r"probes-(\w+)\.md", prompt)
            if m:
                state["bid"] = m.group(1)
                for pid in re.findall(r"(?m)^## (P-\S+)", ck.files[f"/work/out/probes-{m.group(1)}.md"]):
                    p = next(x for x in self.applicable if x.id == pid)
                    path = ng.probe_path(pid, ng.route(p.needs, self.change.edits_part))
                    t = ng.probe_stem(pid)
                    ck.files[f"/work/out/probes/{t}{ng.probe_ext(path)}"] = f"// {pid}\n"
                    ck.files[f"/work/out/probes/{t}.log"] = f"{pid} observed in {m.group(1)}"
            else:  # extraction
                ck.files["/work/out/reference.md"] = "import { pair } from '../watch-relay.js'"
                ck.files["/work/out/implementation.json"] = json.dumps({"items": [
                    {"item": i, "status": s, "evidence": [{"file": "api/watch-relay.js"}], "note": "n"}
                    for i, s in implementation.items()]})
            return SimpleNamespace(structured=None, text="done", usage=usage, duration_s=1.0)

        out = Path(tempfile.mkdtemp())
        result = ng.grade_probes(ck, self.g, self.probeset, self.applicable, change=self.change, out=out,
                                 volume="ckpt", run_role=run_role, guards=guards, conditions=conditions or {},
                                 options=ng.probe_options(PROBES))
        return result, ck, calls, out

    def test_extraction_routes_execution_and_judgment_with_not_exercised_where_a_probe_allows_it(self):
        rulings = {"b01": {"P-OGM0101-a": ("met", "none", "none"), "P-OGM0102-a": ("met", "none", "none")},
                   "b02": {"P-OGM0104-a": ("not exercised", "none", "none")}}
        result, ck, calls, out = self.run_probes(rulings, {"OGM-0101": "implemented", "OGM-0102": "inherited",
                                                           "OGM-0104": "implemented"})
        self.assertEqual(result["probes"], {"P-OGM0101-a": "met", "P-OGM0102-a": "met", "P-OGM0104-a": "not exercised"})
        extraction = calls[0]
        self.assertIn("/work/out/arm.diff", extraction["prompt"])
        for item in ("OGM-0101", "OGM-0102", "OGM-0104"):
            self.assertIn(item, extraction["prompt"])
        self.assertIn("frontend", extraction["prompt"])  # a probe needs the web app, so the reference covers it
        b01 = ck.files["/work/out/probes-b01.md"]
        self.assertNotIn("Expected observation", b01)
        execution = next(c for c in calls if "probes-b01.md" in c["prompt"])
        self.assertIn("api/test/__probes__/probe_p_ogm0101_a.test.js", execution["prompt"])
        self.assertIn("node --test", execution["prompt"])
        b02 = next(c for c in calls if "probes-b02.md" in c["prompt"])
        self.assertIn("frontend/src/__probes__/probe_p_ogm0104_a.test.jsx", b02["prompt"])
        self.assertIn("vitest", b02["prompt"])
        self.assertIn("the page lists a watch at all", ck.files["/work/out/probes-b02.md"])
        judge = next(c for c in calls if c["schema"])
        self.assertIn("Expected observation", judge["prompt"])
        verdicts = json.loads(judge["schema"])["properties"]["verdicts"]["items"]["properties"]["verdict"]["enum"]
        self.assertIn("not exercised", verdicts)
        self.assertTrue((out / "verdicts.json").exists())
        rerun = [s for s in ck.scripts if "probe_p_ogm0104_a" in s and "vitest" in s]
        self.assertTrue(rerun and "cd /work/app/frontend" in rerun[0])
        self.assertTrue(any("rm -f /work/out/implementation.json" in x for x in ck.scripts))  # the executors never read the items

    def test_not_exercised_is_refused_for_a_probe_without_a_precondition(self):
        batch = [p for p in self.applicable if p.id == "P-OGM0101-a"]
        lines = [{"seq": 1, "probe": "P-OGM0101-a", "kind": "test source", "text": "x"},
                 {"seq": 2, "probe": "P-OGM0101-a", "kind": "test output", "text": "y"}]
        v = {"probe": "P-OGM0101-a", "verdict": "not exercised", "evidence": [2], "reason": "The output shows no watch at all here.",
             "cause": "none", "fault": "none", "failed_postcondition": "", "postcondition_row": "none"}
        problems = ng.check_verdicts({"verdicts": [v]}, batch, lines, {"P-OGM0101-a": {"exercised_only_if": None}})
        self.assertTrue(any("not exercised" in p for p in problems))
        self.assertEqual(ng.check_verdicts({"verdicts": [v]}, batch, lines, {"P-OGM0101-a": {"exercised_only_if": "x"}}), [])

    def test_a_probe_whose_condition_fails_never_runs_and_is_not_exercised(self):
        rulings = {"b01": {"P-OGM0101-a": ("not met", "none", "none"), "P-OGM0102-a": ("met", "none", "none")}}
        result, ck, calls, _ = self.run_probes(rulings, {"OGM-0101": "absent", "OGM-0102": "inherited", "OGM-0104": "absent"})
        self.assertEqual(result["probes"]["P-OGM0104-a"], "not exercised")
        self.assertEqual(result["conditions"]["P-OGM0104-a"]["holds"], False)
        self.assertFalse(any("probes-b02.md" in c["prompt"] for c in calls))

    def test_a_row_condition_from_the_graded_manifest_applies_too(self):
        rulings = {"b01": {"P-OGM0101-a": ("met", "none", "none")}, "b02": {"P-OGM0104-a": ("met", "none", "none")},
                   "b03": {"P-OGM0102-a": ("met", "none", "none")}}
        result, *_ = self.run_probes(rulings, {"OGM-0101": "implemented", "OGM-0102": "inherited", "OGM-0104": "implemented"},
                                     conditions={"OGM-0102": "OGM-0104 met"})
        self.assertEqual(result["probes"]["P-OGM0102-a"], "met")  # run after OGM-0104, which it waits on
        self.assertEqual(result["conditions"]["P-OGM0102-a"], {"condition": "OGM-0104 met", "holds": True})

    def test_a_met_on_an_absent_row_is_a_conflict_unless_it_is_a_guard_row(self):
        rulings = {"b01": {"P-OGM0101-a": ("met", "none", "none"), "P-OGM0102-a": ("met", "none", "none")},
                   "b02": {"P-OGM0104-a": ("met", "none", "none")}}
        impl = {"OGM-0101": "absent", "OGM-0102": "absent", "OGM-0104": "implemented"}
        result, *_ = self.run_probes(rulings, impl, guards={"OGM-0102"})
        self.assertEqual(result["probes"]["P-OGM0101-a"], grading.CONFLICT)
        self.assertEqual(result["probes"]["P-OGM0102-a"], "met")
        self.assertEqual(result["guard_exempt"], ["P-OGM0102-a"])

    def test_a_setup_step_another_row_covers_blocks_the_probe_with_that_rows_report(self):
        rulings = {"b01": {"P-OGM0101-a": ("met", "none", "none"),
                           "P-OGM0102-a": ("couldn't exercise", "execution", "fixture", "a replacement code is issued", "OGM-0101")},
                   "b02": {"P-OGM0104-a": ("met", "none", "none")},
                   "x01": {"P-OGM0102-a": ("couldn't exercise", "execution", "fixture", "a replacement code is issued", "OGM-0101")}}
        result, *_ = self.run_probes(rulings, {"OGM-0101": "implemented", "OGM-0102": "inherited", "OGM-0104": "implemented"})
        self.assertEqual(result["probes"]["P-OGM0102-a"], "blocked")
        self.assertEqual(result["failed_setups"], [{"probe": "P-OGM0102-a", "item": "OGM-0102", "postcondition": "a replacement code is issued",
                                                    "blocked_by": "OGM-0101", "repair_report": "I paired a second watch and didn't end up with just the new one."}])

    def test_a_grader_error_left_after_the_rerun_is_missing(self):
        rulings = {"b01": {"P-OGM0101-a": ("couldn't exercise", "execution", "compile"), "P-OGM0102-a": ("met", "none", "none")},
                   "b02": {"P-OGM0104-a": ("met", "none", "none")},
                   "x01": {"P-OGM0101-a": ("couldn't exercise", "execution", "observation")}}
        result, ck, calls, _ = self.run_probes(rulings, {"OGM-0101": "implemented", "OGM-0102": "inherited", "OGM-0104": "implemented"})
        self.assertEqual(result["probes"]["P-OGM0101-a"], grading.MISSING)
        self.assertEqual(result["missing"]["P-OGM0101-a"]["fault"], "observation")
        self.assertTrue(any(s.startswith("rm -f") and "probe_p_ogm0101_a" in s for s in ck.scripts))

    def test_the_prompts_exist_and_fill(self):
        routes = {"P-OGM0101-a": ng.route(("api",), "api")}
        self.assertIn("/work/out/probes-b01.md", ng.execution_prompt("b01", routes))
        self.assertIn("implementation.json", ng.extraction_prompt([("OGM-0101", "x")], {"api"}))
        self.assertNotIn("implementation.json", ng.extraction_prompt([], {"api"}))
        for name in ("extraction-node.md", "grade-execute-node.md", "grade-judge-node.md", "keeping-classify-node.md",
                     "dependency-adapter-node.md"):
            self.assertTrue((grading.PROMPTS / name).exists(), name)


# -------------------------------------------------------------------------------------------- what is counted


class ItemsTest(unittest.TestCase):
    def test_item_verdicts_rank_not_exercised_and_blocked(self):
        probes = grading.parse_probes(PROBES).probes
        iv = ng.item_verdicts({"P-OGM0101-a": "met", "P-OGM0102-a": "blocked", "P-OGM0104-a": "not exercised",
                               "P-OGM0201-a": "not met"}, probes)
        got = {k.split()[0]: v["verdict"] for k, v in iv.items()}
        self.assertEqual(got, {"OGM-0101": "met", "OGM-0102": "blocked", "OGM-0104": "not exercised", "OGM-0201": "not met"})

    def test_items_met_leaves_out_what_was_not_decided_and_counts_it_apart(self):
        items = {"OGM-0101 a": "met", "OGM-0102 b": "not exercised", "OGM-0103 c": "blocked", "OGM-0104 d": "missing",
                 "OGM-0105 e": "not met", "OGM-0106 f": grading.CONFLICT}
        m = ng.items_met(items)
        self.assertEqual((m["met"], m["of"], m["not_exercised"], m["blocked"], m["missing"], m["conflicts"]), (1, 2, 1, 1, 1, 1))
        k = ng.items_met_by_kind(items, guards={"OGM-0102"})
        self.assertEqual((k["new_rows_met"]["of"], k["guard_rows_met"]["of"], k["guard_rows_met"]["not_exercised"]), (2, 0, 1))


class JointTest(unittest.TestCase):
    def setUp(self):
        self.c1 = ng.parse_changes(CHANGES)[1]

    def implemented(self, verdicts, change=None, **kw):
        return ng.implemented(change or self.c1, verdicts, guards={"OGM-0102"}, **kw)

    def test_implemented_is_over_the_stated_non_guard_rows(self):
        self.assertEqual(self.implemented({"OGM-0101": "met", "OGM-0104": "met", "OGM-0102": "not met"})["value"], "yes")
        self.assertEqual(self.implemented({"OGM-0101": "met", "OGM-0104": "not met"})["value"], "partly")
        self.assertEqual(self.implemented({"OGM-0101": "not met", "OGM-0104": "not exercised"})["value"], "no")
        undecided = self.implemented({"OGM-0101": "met", "OGM-0104": "missing"})
        self.assertIsNone(undecided["value"])
        self.assertEqual(undecided["undecided"], ["OGM-0104"])
        self.assertEqual(self.implemented({"OGM-0101": "met", "OGM-0104": "not met", "OGM-0102": "missing"})["value"], "partly")
        self.assertEqual(self.implemented({"OGM-0101": "met", "OGM-0104": "blocked"})["value"], None)
        self.assertEqual(self.implemented({"OGM-0101": "met", "OGM-0104": "met"})["rows"], ["OGM-0101", "OGM-0104"])

    def test_rows_set_aside_by_the_plan_and_a_score_with_none_left_is_na(self):
        r = self.implemented({"OGM-0101": "met", "OGM-0104": "not met"}, excluded={"OGM-0104"})
        self.assertEqual((r["value"], r["rows"]), ("yes", ["OGM-0101"]))
        self.assertEqual(self.implemented({}, excluded={"OGM-0101", "OGM-0104"})["value"], "N/A")

    def test_the_joint_outcome_carries_implemented_the_dependency_tier_and_the_plans_notes(self):
        items = {"OGM-0101 x": "met", "OGM-0102 y": "met", "OGM-0104 z": "met"}
        j = ng.joint_outcome(self.c1, items, {"result": "broken", "row": "dependency"}, guards={"OGM-0102"},
                             rules={1: {"coupled_with_dependency": ["OGM-0104"], "beside_dependency": ["OGM-0102"]}})
        self.assertEqual(j["implemented"], "yes")
        self.assertEqual(j["dependent_behaviour"], "broken")
        self.assertEqual((j["tier"], j["type"]), ("hidden", "api-change-app-depends"))
        self.assertEqual(j["implemented_without_coupled"]["value"], "yes")
        self.assertEqual(j["beside_dependency"], {"OGM-0102": "met"})
        self.assertEqual(j["exercised_only_if"], self.c1.exercised_only_if)

    def test_the_plans_rules(self):
        rules = ng.JOINT_RULES
        self.assertEqual(rules[3]["coupled_with_dependency"], ["OGM-0301", "OGM-0302"])
        self.assertEqual(rules[4]["beside_dependency"], ["OGM-0405"])
        self.assertEqual(rules[4]["excluded"], ["OGM-0405"])

    @unittest.skipUnless(REAL_CHANGES.exists(), "the hidden seed isn't here")
    def test_change_3_without_its_coupled_rows_is_na_on_the_real_seed(self):
        c3 = ng.parse_changes(REAL_CHANGES.read_text(encoding="utf-8"))[3]
        guards = set(ng.load_guard_rows(REAL_GUARDS))
        j = ng.joint_outcome(c3, {"OGM-0301 a": "met", "OGM-0302 b": "met", "OGM-0303 c": "met"}, {"result": "kept"},
                             guards=guards, rules=ng.JOINT_RULES)
        self.assertEqual(j["implemented"], "yes")
        self.assertEqual(j["implemented_without_coupled"]["value"], "N/A")

    def test_repair_reports_for_each_miss_the_blocking_row_and_a_broken_dependency(self):
        items = {"OGM-0101 x": "not met", "OGM-0102 y": "met", "OGM-0104 z": "blocked"}
        failed = [{"probe": "P-OGM0104-a", "item": "OGM-0104", "blocked_by": "OGM-0102", "repair_report": "My old watch stopped connecting."}]
        reports = ng.repair_reports(self.c1, items, {"result": "broken"}, failed)
        self.assertEqual(reports, {"OGM-0101": "I paired a second watch and didn't end up with just the new one.",
                                   "OGM-0102": "My old watch stopped connecting.", "Dependency": "The code didn't clear."})
        self.assertEqual(ng.repair_reports(self.c1, {"OGM-0101 x": "met"}, {"result": "not exercised"}, []), {})


# --------------------------------------------------------------------------------------------- the checkpoint


class CheckpointTest(unittest.TestCase):
    def test_the_fork_commit_from_git_alone_with_the_installed_dependencies_beside_it(self):
        calls = []

        def runner(cmd, **kw):
            calls.append(cmd)
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        ck = ng.NodeCheckpoint(name="m2h-bare-c01-r1-c01", commit="abc", image="img", runner=runner)
        self.assertEqual(ck.volume, "m2h-bare-c01-r1-c01-grade")
        ck.export("m2h-bare-c01-r1-ws")
        script = calls[0][-1]
        self.assertIn("m2h-bare-c01-r1-ws:/src:ro", calls[0])
        self.assertIn("cp -a /src/.git /work/app/.git", script)
        self.assertIn("git checkout -q -f --detach abc", script)
        self.assertIn("git clean -fdxq", script)
        self.assertIn("-name node_modules", script)
        ck.sh("true")
        self.assertIn("none", calls[-1][calls[-1].index("--network") + 1])
        ck.sh("npm ci", network=True)
        self.assertNotIn("--network", calls[-1])
        ck.drop()
        self.assertEqual(calls[-1][:4], ["docker", "volume", "rm", "-f"])

    def test_graders_see_code_and_tests_with_the_arms_annotations_gone(self):
        ids = {"WATCH-RELAY-014"}
        text = ("const a = 1 // @spec WATCH-RELAY-014\n// @spec WATCH-RELAY-014, WATCH-RELAY-015\n"
                "/* keeps one link (WATCH-RELAY-014) */\nconst s = 'WATCH-RELAY-014'\n * @spec X\nplain\n")
        out = ng.strip_annotations(text, ids)
        self.assertEqual(out, "const a = 1\n/* keeps one link () */\nconst s = 'WATCH-RELAY-014'\nplain\n")
        diff = "+const a = 1 // @spec WATCH-RELAY-014\n+// @spec X\n-old\n context\n"
        self.assertEqual(ng.strip_diff(diff, ids), "+const a = 1\n-old\n context\n")
        self.assertEqual(ng.spec_ids("- [x] **WATCH-RELAY-014**: When ...\n- [ ] PEVAL-RUN-02 x\nsee HTTP-200 OK"),
                         {"WATCH-RELAY-014"})
        hidden = ng.hidden_paths(["docs/intent/a.md", "CLAUDE.md", "api/CLAUDE.md", ".claude/x.json", "README.md",
                                  "api/server.js", "frontend/src/a.test.js"])
        self.assertEqual(hidden, [".claude/x.json", "CLAUDE.md", "README.md", "api/CLAUDE.md", "docs/intent/a.md"])


# -------------------------------------------------------------------------------------------- the whole step


def m2h_fork(change=1, *, graded=None, probes=True):
    root = Path(tempfile.mkdtemp())
    runs, seed = root / "runs", root / "seed"
    (seed / "hidden" / "m2h").mkdir(parents=True)
    (seed / "hidden" / "m2h-changes.md").write_text(CHANGES)
    (seed / "hidden" / "m2h-guard-rows.json").write_text(json.dumps({"rows": {"OGM-0102": {"change": 1}, "OGM-0903": {"change": 9}}}))
    if probes:
        (seed / "hidden" / "m2h" / "probes.md").write_text(PROBES)
    fid = f"m2h-bare-c{change:02d}-r1"
    (runs / fid).mkdir(parents=True)
    meta = {"id": fid, "arm": "bare", "change": change, "image": ng.IMAGE, "start_commit": "d96444e",
            "fork_of": {"start": "bare", "volume": "ogmap-bare-ws", "commit": "d96444e"},
            "volumes": {"workspace": f"{fid}-ws", "config": f"{fid}-cfg"},
            "changes": {str(change): {"commit": "f0rk", "finished": True}}}
    (runs / fid / "trajectory.json").write_text(json.dumps(meta))
    gdir = None
    if graded is not None:
        gdir = seed / "hidden" / "m2h-graded"
        for path, text in graded.get("files", {}).items():
            (gdir / path).parent.mkdir(parents=True, exist_ok=True)
            (gdir / path).write_text(text)
        (gdir / "graded.json").write_text(json.dumps(graded["manifest"]))
    return runs, seed, fid


API_FILE = "api/test/a.test.js"
BASE_API = node_lines([(API_FILE, [], "one", "passed"), (API_FILE, [], "two", "passed")], counts={"tests": 2, "pass": 2})
FORK_API = node_lines([(API_FILE, [], "one", "passed"),
                       (API_FILE, [], "two", "failed", {"message": "Expected 5 got 1", "actual": {"links": 1}, "expected": {"links": 5}})])


class GradeNodeMainTest(unittest.TestCase):
    def factory(self, made, outputs):
        def make(name, commit, image):
            ck = FakeCk(outputs.get("baseline" if name.endswith("-baseline") else "fork", {}), commit=commit, name=name)
            ck.files["@name-status"] = "M\tapi/test/a.test.js\nA\tapi/test/mine.test.js\nM\tapi/watch-relay.js\n"
            ck.files["@numstat"] = "3\t1\tapi/watch-relay.js\n2\t0\tdocs/ZEPP_OS.md\n"
            ck.files["@diff"] = "+export const WATCH_LINKS_MAX = 1 // @spec WATCH-014\n"
            ck.files["@ls-files"] = "api/watch-relay.js\ndocs/ZEPP_OS.md\nCLAUDE.md\n"
            ck.files["/work/app/api/test/a.test.js"] = "test('two', () => {\n  assert.equal(links, 5)\n})\n"
            made.append(ck)
            return ck
        return make

    def judge(self, prompt, json_schema):
        if "rulings" in json_schema:  # the keeping classifier
            return SimpleNamespace(structured={"rulings": [{"test": "api/test/a.test.js::two", "classification": "keeping failure",
                                                            "reason": "The link count the test pins changed.",
                                                            "evidence": [{"seq": 1, "lines": [1]}]}]},
                                   text="", usage=SimpleNamespace(reported_cost_usd=0.05, models={}), duration_s=1.0)
        return None

    def test_a_fork_is_graded_for_keeping_against_a_cached_baseline_and_the_summary_has_the_joint_outcome(self):
        runs, seed, fid = m2h_fork(probes=False)
        outputs = {"baseline": {("baseline", "api"): BASE_API}, "fork": {("fork", "api"): FORK_API}}
        made = []
        calls = []

        def run_role(role, prompt, json_schema=None):
            calls.append(prompt)
            r = self.judge(prompt, json_schema or "")
            if r is None:
                raise AssertionError("no other role should run")
            return r
        argv = ["--id", fid, "--runs", str(runs), "--seed-dir", str(seed), "--suites", "api"]
        self.assertEqual(grade_node.main(argv, checkpoint=self.factory(made, outputs), run_role=run_role), 0)
        out = runs / fid / "grading" / "change-01"
        s = json.loads((out / "summary.json").read_text())
        self.assertEqual((s["id"], s["change"], s["arm"], s["commit"], s["start_commit"]), (fid, 1, "bare", "f0rk", "d96444e"))
        k = s["keeping"]
        self.assertEqual((k["counted"], k["passed"], k["failed"], k["keeping_failures"], k["new_state_only"]), (2, 1, 1, 1, 0))
        self.assertTrue(k["baseline"]["computed"])
        fork_ck, base_ck = made[0], made[1]
        self.assertEqual(fork_ck.exported_from, f"{fid}-ws")
        self.assertEqual(base_ck.exported_from, "ogmap-bare-ws")  # the start's own volume, read-only
        self.assertEqual(base_ck.commit, "d96444e")
        self.assertTrue(base_ck.dropped and fork_ck.dropped)
        # the start's test files went back in before the suites ran, and the arm's own new test went
        restore = next(s for s in fork_ck.scripts if "git checkout d96444e --" in s)
        self.assertIn("api/test/a.test.js", restore)
        self.assertTrue(any("rm -f" in x and "api/test/mine.test.js" in x for x in fork_ck.scripts))
        self.assertLess(fork_ck.scripts.index(restore), next(i for i, x in enumerate(fork_ck.scripts) if "/work/out/runs/fork/api" in x))
        self.assertEqual(s["test_edits"]["edited"], 1)
        self.assertEqual(s["doc_changes"]["files"], 1)
        self.assertNotIn("@spec", (out / "arm.diff").read_text())
        self.assertTrue((out / "keeping.json").exists())
        cached = runs / "opengym-m2h" / "baselines" / "d96444e" / "baseline.json"
        self.assertTrue(cached.exists())
        self.assertEqual(s["probes_skipped"].split(":")[0], "no probes file at " + str(seed / "hidden" / "m2h" / "probes.md"))
        self.assertEqual(s["dependency"]["result"], "missing")
        self.assertIn("no dependency probes", s["dependency"]["cause"])
        self.assertIsNone(s["joint"]["implemented"])  # no probes ran: nothing decided
        self.assertEqual(s["joint"]["tier"], "hidden")
        classify = [c for c in calls if "keeping" in c]
        self.assertTrue(classify and "one Zepp watch per person" in classify[0])

        # graded again: the baseline comes from the cache, with no start checkpoint
        made2 = []
        self.assertEqual(grade_node.main(argv, checkpoint=self.factory(made2, outputs), run_role=run_role), 0)
        self.assertEqual(len(made2), 1)
        s2 = json.loads((out / "summary.json").read_text())
        self.assertFalse(s2["keeping"]["baseline"]["computed"])

    def test_an_adjustment_is_applied_on_the_fork_and_compared_with_the_adjusted_start(self):
        patch = ("diff --git a/api/test/a.test.js b/api/test/a.test.js\n--- a/api/test/a.test.js\n+++ b/api/test/a.test.js\n"
                 "@@ -1 +1 @@\n-x\n+y\n")
        graded = {"files": {"adjusted/change-02.patch": patch},
                  "manifest": {"version": 1, "adjustments": {"2": {"kind": "adjusted copies", "patch": "adjusted/change-02.patch",
                                                                   "tests": ["api/test/a.test.js::two"]}}}}
        runs, seed, fid = m2h_fork(2, graded=graded, probes=False)
        adjusted = node_lines([(API_FILE, [], "one", "passed"), (API_FILE, [], "two", "passed")])
        outputs = {"baseline": {("baseline", "api"): BASE_API, ("adjusted-c02", "api"): adjusted},
                   "fork": {("fork", "api"): FORK_API}}
        made = []
        argv = ["--id", fid, "--runs", str(runs), "--seed-dir", str(seed), "--suites", "api", "--no-classify"]
        self.assertEqual(grade_node.main(argv, checkpoint=self.factory(made, outputs), run_role=None), 0)
        s = json.loads((runs / fid / "grading" / "change-02" / "summary.json").read_text())
        self.assertEqual(s["keeping"]["adjusted"]["tests"]["api/test/a.test.js::two"], {"start": "passed", "fork": "failed", "counted": True})
        self.assertEqual(s["keeping"]["retired"]["covered_by_adjustment"], [])
        fork_ck, base_ck = made
        self.assertTrue(any("git apply" in x for x in fork_ck.scripts))
        adj_run = next(x for x in base_ck.scripts if "/work/out/runs/adjusted-c02/api" in x)
        self.assertTrue(adj_run.rstrip().endswith("test/a.test.js"))  # only the files the adjustment touches
        self.assertIsNone(s["keeping"]["classified"] or None)
        key = s["keeping"]["baseline"]["adjusted_key"]
        self.assertTrue((runs / "opengym-m2h" / "baselines" / "d96444e" / "adjusted" / f"change-02-{key}.json").exists())

    def test_an_adjusted_start_cached_with_fewer_suites_runs_again(self):
        root, gdir = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
        (gdir / "adjusted").mkdir()
        patch = ("--- a/api/test/a.test.js\n+++ b/api/test/a.test.js\n@@ -1 +1 @@\n-x\n+y\n"
                 "--- a/mcp/test/m.test.js\n+++ b/mcp/test/m.test.js\n@@ -1 +1 @@\n-x\n+y\n")
        (gdir / "adjusted" / "c.patch").write_text(patch)
        adj = {"kind": "adjusted copies", "patch": "adjusted/c.patch", "tests": []}
        mcp = vitest_json({"mcp/test/m.test.js": ("passed", "", [([], "m", "passed", [])])})
        outputs = {"baseline": {("baseline", "api"): BASE_API, ("baseline", "mcp"): mcp,
                                ("adjusted-c02", "api"): BASE_API, ("adjusted-c02", "mcp"): mcp}}
        kw = dict(commit="d96444e", image="img", volume="v", flaky=[], reruns=1, cache=root, graded_dir=gdir,
                  adjustment=adj, change=2)
        made = []
        _, adj_runs, info = grade_node.baseline(self.factory(made, outputs), name="m2h-x", suites=["api"], **kw)
        self.assertEqual(sorted(adj_runs), ["api"])
        _, adj_runs, info = grade_node.baseline(self.factory(made, outputs), name="m2h-x", suites=["api", "mcp"], **kw)
        self.assertTrue(info["adjusted_computed"])
        self.assertEqual(sorted(adj_runs), ["api", "mcp"])
        _, _, info = grade_node.baseline(self.factory(made, outputs), name="m2h-x", suites=["api", "mcp"], **kw)
        self.assertFalse(info["computed"] or info["adjusted_computed"])
        self.assertEqual(len(made), 2)

    def test_baseline_only_runs_and_caches_a_start(self):
        root = Path(tempfile.mkdtemp())
        made = []
        outputs = {"baseline": {("baseline", "api"): BASE_API}}
        argv = ["--baseline-only", "--start-commit", "d96444e", "--start-volume", "m2h-grader-check-ws",
                "--name", "m2h-grader-check-bare", "--baselines", str(root), "--suites", "api"]
        self.assertEqual(grade_node.main(argv, checkpoint=self.factory(made, outputs)), 0)
        self.assertEqual(made[0].name, "m2h-grader-check-bare-baseline")
        self.assertEqual(made[0].exported_from, "m2h-grader-check-ws")
        data = json.loads((root / "d96444e" / "baseline.json").read_text())
        self.assertEqual(data["suites"]["api"]["counts"], {"tests": 2, "pass": 2})
        self.assertEqual(sorted(data["suites"]["api"]["tests"]), ["api/test/a.test.js::one", "api/test/a.test.js::two"])

    def test_graders_sharing_a_start_compute_its_baseline_once(self):
        # several null forks of one start graded at once: the first computes the baseline under a lock, the rest wait
        # for it and read the cache
        import threading
        root = Path(tempfile.mkdtemp())
        made, outputs = [], {"baseline": {("baseline", "api"): BASE_API}}
        factory = self.factory(made, outputs)
        slow = threading.Event()

        def make(name, commit, image):
            ck = factory(name, commit, image)
            orig = ck.export

            def export(volume):
                slow.wait(0.2)  # long enough for the other grader to reach the cache
                return orig(volume)
            ck.export = export
            return ck
        results = []

        def one():
            results.append(grade_node.baseline(make, name="g", commit="d96444e", image="img", volume="v", suites=["api"],
                                               flaky=[], reruns=1, cache=root))
        threads = [threading.Thread(target=one) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(made), 1)  # one export, one run
        self.assertEqual([r[2]["computed"] for r in results].count(True), 1)
        self.assertTrue(all(r[0]["api"]["counts"] == {"tests": 2, "pass": 2} for r in results))

    def test_dependency_probes_run_after_the_code_only_checkout_and_roll_up(self):
        graded = {"files": {"dependency/change-01/d.test.jsx": "// probe\n"},
                  "manifest": {"version": 1, "dependency_probes": [
                      {"id": "dep-01", "change": 1, "row": "dependency", "suite": "frontend",
                       "file": "dependency/change-01/d.test.jsx", "dest": "frontend/src/__graded__/d.test.jsx"}]}}
        runs, seed, fid = m2h_fork(graded=graded, probes=False)
        report = vitest_json({"frontend/src/__graded__/d.test.jsx": ("failed", "", [
            ([], "precondition: one watch left", "passed", []), ([], "dependency: notices the replacement", "failed", ["code stayed"])])})
        outputs = {"fork": {("dep-dep-01", "frontend"): report}}
        made = []
        argv = ["--id", fid, "--runs", str(runs), "--seed-dir", str(seed), "--no-keeping", "--no-adapters"]
        self.assertEqual(grade_node.main(argv, checkpoint=self.factory(made, outputs), run_role=None), 0)
        s = json.loads((runs / fid / "grading" / "change-01" / "summary.json").read_text())
        self.assertEqual(s["dependency"]["result"], "broken")
        self.assertEqual(s["dependency"]["probes"]["dep-01"]["result"], "broken")
        self.assertEqual(s["joint"]["dependent_behaviour"], "broken")
        self.assertEqual(s["repair_reports"], {"Dependency": "The code didn't clear."})
        ck = made[0]
        strip = next(i for i, x in enumerate(ck.scripts) if "rm -rf" in x and ".git" in x)
        dep_run = next(i for i, x in enumerate(ck.scripts) if "dep-dep-01" in x)
        self.assertLess(strip, dep_run)  # graders, and the probes, see the code-only checkout
        cleared = next(i for i, x in enumerate(ck.scripts) if x == "rm -rf /work/out/runs /work/grader")
        self.assertLess(dep_run, cleared)  # and the grader's own runs are gone before the LLM-run probes


if __name__ == "__main__":
    unittest.main()
