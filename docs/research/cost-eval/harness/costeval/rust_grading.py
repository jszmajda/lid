"""Grading one checkpoint of a Rust library (Clowder): keeping, the arm's edits to existing tests, and new intent.

Design: "Later seeds and variants" (the falsification test's grading) and "Graders" in the notebook's design.md.

1. **Export.** The fork's commit is cloned out of its workspace into a checkpoint volume (/work/app), with build output
   at /work/target and grading output at /work/out. After the harness's own git steps (3), graders get a code-only
   checkout whatever the arm: what the variant builder strips (docs/, .claude/, agent instruction files, LID tooling)
   is removed, with the history that would show it; the arm's changes to docs are counted apart, as context.
2. **Keeping.** Each held-out test file goes back in as a test target of its own (`tests/heldout_<name>/`, beside the
   helper modules its directory had, as they were), so a file the arm's code no longer compiles against fails alone.
   Each target runs with `cargo test`, after the compile-only adaptation (rust_adapt.py) where it fails to build only
   on fields or variants the arm added; results are kept per test, compile failures apart, failing tests classified
   (rust_classify.py), and every test that reached an adapted wildcard arm named. This is held-out retention, reported
   apart from the kept-behaviour checks among the probes.
3. **Edits to existing tests.** `git diff` from the fork's starting commit: test files the arm edited, deleted, or
   renamed, the lines it changed in them, and the `#[test]` functions before and after; and, given the seed's list of
   still-valid assertions in tests the arm can see, each one kept, deleted, or weakened.
4. **New intent.** Probes in the probes.md format, as for the other seeds:
   - extraction (Sonnet) reads the arm's diff of code and tests and writes a reference for calling what it added from
     a Rust test; it also records, for each of the change's graded items, whether the diff implements anything
     addressing it (implemented, absent, or unclear, with files and symbols), which the executors never see;
   - execution (Haiku), per batch, writes one test target per probe, `tests/probe_<id>.rs`, that performs the scenario
     through the arm's own API and prints what it observes; it never sees the expected observations. Every executor
     gets the same tested fixture helpers (the snapshot's own test helper modules, built against the arm's code,
     beside the probe tests) as well as the arm's interface reference. The harness then runs each probe's test
     itself, so the judge reads real output;
   - judgment (Sonnet) compares each probe's expected observation with its test and output. Only a confirmed absence
     of the required observable behaviour is "not met". A test that doesn't compile, can't build its setup, can't
     find how to perform a step, or doesn't print the deciding observation is the grader's error ("couldn't
     exercise", cause execution, with that fault): the probe runs once more, in a batch of its own, from no test and
     with the same instructions; if it is still unresolved its verdict is "missing", which leaves its item out of
     the items-met share and is reported by fault and arm, except that an interface fault on an item the extraction
     found absent is a confirmed absence: "not met". Interface faults are reported beside the share either way. A
     step the test did with its own logic rather than the library's is an interface fault too, and a "met" on an
     item the extraction found absent is a conflict: "missing (conflict)", out of the share, flagged with both
     rulings for a spot-check.
   - a probe that needs `tui` drives the game's terminal shell (clowder-tui): the extraction covers the shell's
     surface as well (drawing a frame into a test backend, resolving keys, the shell's update), and its batch's
     executor is told to write its test in the shell's crate. Probes without that need are graded as before.
5. **Graded targets (M2f).** The variant set's graded/ folder (m2f_graded_targets.py) holds the dependency probes and
   the held-out test functions as test targets of their own, built from the snapshot. A change is graded on its own
   targets that are in force (graded_for_change), through the keeping step's machinery: each target goes into the
   arm's checkout, is built with the compile-only adaptation, run, tallied, and its failures classified: a held-out
   test's by keeping's rule, a probe's by its variant (settled precondition, or dependency failure). graded_tests
   gives each test's result and the change's roll-ups: met when every test ran and passed, not met when any ran and
   failed, and undecided when some are missing (a target not built after adaptation, a test that didn't run, a probe
   failing only on a precondition the change settles) and none failed; missing tests are reported by cause, outside
   the share, as keeping reports the held-out tests it couldn't build.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from . import executor, grading, rust_adapt

MAX_OUTPUT = 200_000  # characters of one probe's output the judge sees whole (real outputs run to ~135k)
KEEP_EDGE = 40_000  # past that, the head and tail kept, and every deciding line between them
DECIDING = re.compile(r"^\s*(?:ALL-CASES:|CANNOT\b|WITNESS\b|SUMMARY\b|(?:case|seed|branch|control|day)\b[^:\n]{0,60}:"
                      r"|thread '.*' panicked|error(?:\[|:))", re.I)
TEST_LINE = re.compile(r"(?m)^test (\S+) \.\.\. (ok|FAILED|ignored)\b")  # "ignored" may carry a reason


# ------------------------------------------------------------------------------------------------- keeping


def _module_dir(path: str) -> bool:
    return bool(re.fullmatch(r"crates/[^/]+/tests/[^/]+/[^/]+\.rs", path))


def held_out_target_names(held: list[str]) -> list[tuple[str, str]]:
    """(crate directory, test target) for each held-out file."""
    return [(p.split("/")[1], f"heldout_{Path(p).stem}") for p in held]


def held_out_targets(held_dir: Path, held: list[str]) -> dict[str, str]:
    """The files that put each held-out test back as a target of its own: a module file goes in its own directory
    with a main.rs declaring it and the helper modules its original directory declared (copied as they were), and the
    original main.rs's crate attributes; a file that was a target already comes back under a new name."""
    out: dict[str, str] = {}
    for path in held:
        crate, target = path.split("/")[1], f"heldout_{Path(path).stem}"
        text = (held_dir / path).read_text(encoding="utf-8")
        if not _module_dir(path):
            out[f"crates/{crate}/tests/{target}.rs"] = text
            continue
        src_dir = path.rsplit("/", 1)[0]
        main = (held_dir / src_dir / "main.rs")
        main_text = main.read_text(encoding="utf-8") if main.exists() else ""
        attrs = [l for l in main_text.splitlines() if l.startswith("#![")]
        declared = re.findall(r"(?m)^\s*(?:pub\s+)?mod\s+(\w+)\s*;", main_text)
        helpers = [m for m in declared if (held_dir / src_dir / m).is_dir() or
                   ((held_dir / src_dir / f"{m}.rs").exists() and f"{src_dir}/{m}.rs" not in held)]
        dest = f"crates/{crate}/tests/{target}"
        for h in helpers:
            hdir = held_dir / src_dir / h
            if hdir.is_dir():
                for f in sorted(hdir.rglob("*")):
                    if f.is_file():
                        out[f"{dest}/{h}/{f.relative_to(hdir)}"] = f.read_text(encoding="utf-8")
            else:
                out[f"{dest}/{h}.rs"] = (held_dir / src_dir / f"{h}.rs").read_text(encoding="utf-8")
        out[f"{dest}/main.rs"] = "\n".join(attrs + [""] + [f"mod {h};" for h in helpers] + [f"mod {Path(path).stem};", ""])
        out[f"{dest}/{Path(path).stem}.rs"] = text
    return out


def _target_result(output: str) -> dict:
    tests = {name: status for name, status in TEST_LINE.findall(output)}
    m = re.search(r"EXIT=(\d+)\s*$", output)
    code = int(m.group(1)) if m else None
    compile_failed = bool(re.search(r"(?m)^error: could not compile", output)) or (code not in (0, None) and not tests
                                                                                    and "test result:" not in output)
    return {"exit_code": code, "tests": tests, "compile_failed": compile_failed,
            "errors": re.findall(r"(?m)^error(?:\[E\d+\])?: .*$", output)[:20] if compile_failed else []}


def keeping_result(runs: list[tuple[str, str, str]], expected: dict[str, int] | None = None,
                   adaptations: dict[str, dict] | None = None) -> dict:
    """Per target and in total, from each (crate, target, cargo output). expected: #[test] count per target.
    adaptations: each target's record from the compile-only adaptation (rust_adapt). Keeping failures are tests that
    ran and failed; a target that didn't build, adapted or not, is a compile failure, kept apart with its reason."""
    targets = {t: {"crate": c, **_target_result(out), "reached_adaptation": rust_adapt.reached_adaptation(out)}
               for c, t, out in runs}
    for t, rec in (adaptations or {}).items():
        if t in targets:
            targets[t]["adaptation"] = rec
    if expected:
        for t, n in expected.items():
            if t in targets:
                targets[t]["tests_expected"] = n
    passed = sum(s == "ok" for r in targets.values() for s in r["tests"].values())
    failed = sum(s == "FAILED" for r in targets.values() for s in r["tests"].values())
    total_expected = sum(r.get("tests_expected", 0) for r in targets.values())
    broken = {t: r for t, r in targets.items() if r["compile_failed"]}
    return {"targets": targets, "passed": passed, "failed": failed,
            "compile_failed": sorted(broken),
            "compile_failed_not_adapted": {t: (r.get("adaptation") or {}).get("reason") or (r["errors"] or ["?"])[0]
                                           for t, r in sorted(broken.items())},
            "tests_not_built": sum(r.get("tests_expected", 0) for r in broken.values()),
            "tests_not_built_by_cause": _sum_by((not_built_cause((r.get("adaptation") or {}).get("reason")
                                                                 or (r["errors"] or [""])[0]), r.get("tests_expected", 0))
                                                for r in broken.values()),
            "adapted": sorted(t for t, r in targets.items()
                              if (r.get("adaptation") or {}).get("status") == "adapted" and not r["compile_failed"]),
            "reached_adaptation": sum(len(r["reached_adaptation"]) for r in targets.values()),
            # every held-out test that met a wildcard arm the adaptation added, by name: reported, never passed
            "reached_adaptation_tests": sorted(f"{t}/{n}" for t, r in targets.items() for n in r["reached_adaptation"]),
            "adaptations_by_code": _count(e["code"] for r in targets.values()
                                          for e in (r.get("adaptation") or {}).get("edits", [])),
            "share_passed": passed / (passed + failed) if passed + failed else None,
            "share_of_held_out_passed": passed / total_expected if total_expected else None}


def not_built_cause(reason: str) -> str:
    """Why a held-out target wasn't built, as a short cause: the error code the rule doesn't adapt (an API change,
    such as E0061 or E0382), or what stopped an adaptation the rule covers."""
    m = re.match(r"(E\d{4})\b", reason or "")
    for words, cause in (("outside the held-out files", "outside the held-out files"),
                         ("still failing after", "still failing after adaptation"),
                         ("no empty value", "no empty value"), ("base expression", "base expression"),
                         ("no single definition", "no definition found"), ("don't match", "fields don't match"),
                         ("inside a macro", "inside a macro")):
        if words in (reason or ""):
            return f"{m.group(1)} {cause}" if m and cause not in ("outside the held-out files", "still failing after adaptation") else cause
    return m.group(1) if m else ((reason or "unknown").split(":")[0][:60] or "unknown")


def _sum_by(pairs) -> dict[str, int]:
    out: dict[str, int] = {}
    for k, n in pairs:
        out[k] = out.get(k, 0) + n
    return dict(sorted(out.items()))


def _count(xs) -> dict[str, int]:
    out: dict[str, int] = {}
    for x in xs:
        out[x] = out.get(x, 0) + 1
    return dict(sorted(out.items()))


# ------------------------------------------------------------------------------------- M2f's graded targets


GRADED_JSON = "graded.json"  # the variant set's graded/ folder, from m2f_graded_targets.py
DEPENDENCY_PROBE, HELD_OUT_TEST = "dependency probe", "held-out test"


def load_graded(graded_dir: Path) -> list[dict]:
    return json.loads((graded_dir / GRADED_JSON).read_text(encoding="utf-8"))


def graded_for_change(entries: list[dict], n: int) -> list[dict]:
    """The targets that grade change n: its dependency probes and its held-out tests still in force (status
    "graded"). A retired held-out test grades nothing."""
    return [e for e in entries if e.get("change") == n and e.get("status") == "graded"]


def graded_files(graded_dir: Path, entries: list[dict]) -> dict[str, str]:
    """The targets' files by checkout path, as the snapshot gave them."""
    return {f: (graded_dir / f).read_text(encoding="utf-8") for e in entries for f in e["files"]}


def _graded_result(rec: dict | None, name: str) -> dict:
    if rec is None:
        return {"result": "not built", "cause": "target not run"}
    if rec["compile_failed"]:
        reason = (rec.get("adaptation") or {}).get("reason") or (rec["errors"] or [""])[0]
        return {"result": "not built", "cause": not_built_cause(reason)}
    adapted = {"adapted": True} if (rec.get("adaptation") or {}).get("status") == "adapted" else {}
    status = rec["tests"].get(name)
    if status == "ok":
        return {"result": "passed", **adapted}
    if status == "FAILED":
        failure = (rec.get("failures") or {}).get(name)
        return {"result": "failed", **({"class": failure["classification"]} if failure else {}), **adapted}
    cause = "ignored" if status == "ignored" else f"no result line (exit {rec.get('exit_code')})"
    return {"result": "not run", "cause": cause, **adapted}


# A failure in this class doesn't count against its kind: for a held-out test, keeping's "new state only" (counted as
# kept, as keeping counts it); for a probe, "settled precondition" (the probe couldn't decide: missing).
NOT_COUNTED = {HELD_OUT_TEST: ("new state only", "passed"), DEPENDENCY_PROBE: ("settled precondition", "missing")}


def graded_outcome(rec: dict, kind: str) -> str:
    """What one graded test's result counts as: "passed", "failed", or "missing" (not built, not run, or for a probe a
    failure only on a precondition the change settles). A held-out test failing on new state only is kept, as keeping
    counts it; a failure never classified counts as a failure."""
    result = (rec or {}).get("result")
    if result == "passed":
        return "passed"
    if result == "failed":
        cls, counts_as = NOT_COUNTED[kind]
        return counts_as if rec.get("class") == cls else "failed"
    return "missing"


def _missing_cause(rec: dict) -> str:
    if rec.get("result") == "failed":
        return rec.get("class") or "?"
    return rec.get("cause") or rec.get("result") or "?"


def graded_tests(result: dict, entries: list[dict]) -> dict:
    """Each graded test's result, by its cargo name (`<module>::<fn>`), from the targets' keeping result: "passed",
    "failed" (with the classifier's class when it ruled), "not built" (with the cause, as keeping counts it), or "not
    run" (ignored, or no result line in a target that built); "adapted" marks a test whose target built only after
    the compile-only adaptation. Probes and held-out tests apart, each with:

    - its roll-up (dependency_met, held_out_tests_met): true when every test ran and passed (graded_outcome), false
      when any ran and failed, and null when the change has none, or when some are missing and none failed;
    - the missing ones with their causes, outside the share, as keeping counts the held-out tests it couldn't build;
    - counts: passed, failed, missing (by cause), tests not built (by cause), the failures in the class that doesn't
      count (new state only; settled precondition), and the share passed of those that counted."""
    out: dict = {}
    for kind, key, met_key, prefix, not_counted in (
            (DEPENDENCY_PROBE, "dependency_probes", "dependency_met", "dependency", "settled_precondition"),
            (HELD_OUT_TEST, "held_out_tests", "held_out_tests_met", "held_out_tests", "new_state_only")):
        tests: dict[str, dict] = {}
        for e in entries:
            if e["kind"] != kind:
                continue
            rec = (result.get("targets") or {}).get(e["target"])
            for fn in e["tests"]:
                name = f"{e['module']}::{fn}" if e.get("module") else fn
                tests[name] = _graded_result(rec, name)
        outcome = {t: graded_outcome(r, kind) for t, r in tests.items()}
        missing = [{"test": t, "cause": _missing_cause(tests[t])} for t in tests if outcome[t] == "missing"]
        passed = sum(o == "passed" for o in outcome.values())
        failed = sum(o == "failed" for o in outcome.values())
        not_built = [r for r in tests.values() if r["result"] == "not built"]
        out[key] = tests
        out[met_key] = False if failed else None if missing or not tests else True
        out[f"{prefix}_missing"] = missing
        out[f"{prefix}_counts"] = {
            "passed": passed, "failed": failed, "missing": len(missing),
            "missing_by_cause": _count(m["cause"] for m in missing), "tests_not_built": len(not_built),
            "tests_not_built_by_cause": _count(r["cause"] for r in not_built),
            not_counted: sum(r["result"] == "failed" and r.get("class") == NOT_COUNTED[kind][0] for r in tests.values()),
            "of": len(tests), "share_passed": passed / (passed + failed) if passed + failed else None}
    return out


# ------------------------------------------------------------------------------------- edits to existing tests


def _is_test_path(path: str) -> bool:
    return "/tests/" in f"/{path}"


def _numstat_paths(path: str) -> list[str]:
    m = re.fullmatch(r"(.*)\{(.*) => (.*)\}(.*)", path)
    if m:
        return [f"{m.group(1)}{m.group(2)}{m.group(4)}".replace("//", "/"), f"{m.group(1)}{m.group(3)}{m.group(4)}".replace("//", "/")]
    if " => " in path:
        return path.split(" => ", 1)
    return [path]


def test_edits(name_status: str, numstat: str, count_tests: Callable[[str, str], int]) -> dict:
    """What the arm did to test files that existed when it started, from `git diff --name-status -M` and `--numstat`.
    count_tests(rev, path) counts #[test] functions in a file at "base" or "head"."""
    edited, deleted, renamed, added = [], [], [], []
    for line in name_status.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, paths = parts[0], parts[1:]
        if not any(_is_test_path(p) for p in paths):
            continue
        if status.startswith("M"):
            edited.append(paths[0])
        elif status.startswith("D"):
            deleted.append(paths[0])
        elif status.startswith("R"):
            renamed.append([paths[0], paths[1]])
        elif status.startswith("A"):
            added.append(paths[0])
    pre = set(edited) | set(deleted) | {r[0] for r in renamed}
    added_lines = removed_lines = 0
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) < 3 or parts[0] == "-":
            continue
        if _numstat_paths(parts[2])[0] in pre:
            added_lines += int(parts[0])
            removed_lines += int(parts[1])
    before = sum(count_tests("base", p) for p in sorted(pre))
    after = sum(count_tests("head", p) for p in edited) + sum(count_tests("head", r[1]) for r in renamed)
    return {"edited": sorted(edited), "deleted": sorted(deleted), "renamed": sorted(renamed), "added": sorted(added),
            "lines_added": added_lines, "lines_removed": removed_lines, "tests_before": before, "tests_after": after,
            "tests_removed": max(0, before - after)}


# --------------------------------------------------------------------------------------------------- probes


def probe_target(pid: str) -> str:
    return "probe_" + re.sub(r"[^a-z0-9]+", "_", pid.lower()).strip("_")


def probe_log_lines(results: dict[str, dict]) -> list[dict]:
    """The judge's evidence, numbered: each probe's test source and its output, or a note that there is none."""
    lines, seq = [], 0
    for pid, r in results.items():
        if r.get("source") is None and r.get("output") is None:
            seq += 1
            lines.append({"seq": seq, "probe": pid, "kind": "missing", "text": "The executor wrote no test for this probe."})
            continue
        out = for_judge(r.get("output") or "(no output)")
        seq += 1
        lines.append({"seq": seq, "probe": pid, "kind": "test source", "text": r.get("source") or "(none)"})
        seq += 1
        lines.append({"seq": seq, "probe": pid, "kind": "test output", "text": out})
    return lines


def for_judge(out: str) -> str:
    """A probe's output as the judge reads it: whole up to MAX_OUTPUT; past that, the first and last KEEP_EDGE
    characters and every deciding line between them (the ALL-CASES line, each case's labelled summary line, CANNOT
    and WITNESS lines, panics and errors), with the cuts marked. The whole output stays on disk."""
    if len(out) <= MAX_OUTPUT:
        return out
    head_end = out.rfind("\n", 0, KEEP_EDGE) + 1 or KEEP_EDGE
    tail_start = out.find("\n", len(out) - KEEP_EDGE) + 1 or len(out) - KEEP_EDGE
    middle, kept, cut = out[head_end:tail_start].splitlines(), [], 0
    for line in middle:
        if DECIDING.match(line):
            if cut:
                kept.append(f"...[{cut} lines cut]")
                cut = 0
            kept.append(line)
        else:
            cut += 1
    if cut:
        kept.append(f"...[{cut} lines cut]")
    return out[:head_end] + "\n".join(kept) + "\n" + out[tail_start:]


def log_for_judge(lines: list[dict]) -> str:
    return "\n".join(json.dumps(l) for l in lines)


@dataclass(frozen=True)
class RustGraders:
    image: str
    roles_volume: str
    claude_code: str
    extraction_model: str = "claude-sonnet-5-5"
    execute_model: str = "claude-haiku-5-5"
    judge_model: str = "claude-sonnet-5-5"
    effort: str = "medium"

    def role(self, model: str, **kw) -> executor.RoleSession:
        # Graders reach crates.io but not the seed's public repository, like the arms.
        return executor.RoleSession(image=self.image, config_volume=self.roles_volume, model=model,
                                    claude_code_version=self.claude_code, effort=self.effort,
                                    isolation=executor.Isolation.for_public_seed(window="1m"), **kw)


# implemented: the diff adds or changes code toward the item; inherited: the build has the behaviour through code the
# diff didn't need to touch (existing code the change relies on), named in the record; absent: the behaviour isn't
# produced. Only "absent" can void a probe's "met" (a conflict); "inherited" is evidence for it, as "implemented" is.
IMPLEMENTATION = ("implemented", "inherited", "absent", "unclear")
SHELL_NEED, SHELL_CRATE = "tui", "clowder-tui"  # a probe that needs "tui" drives the game's terminal shell


def _drives_shell(needs) -> bool:
    return SHELL_NEED in set(needs or ())


def extraction_prompt(items: list[tuple[str, str]] = (), needs=()) -> str:
    """items: (ID, statement) for each graded item of the change, whose implementation the extraction records.
    needs: what the change's probes need; where one needs the shell, the reference covers the shell's surface too."""
    note = ""
    if _drives_shell(needs):
        note += (f"Some graders will also drive the game's terminal shell, the `{SHELL_CRATE}` crate, from a test. Cover "
                 f"it in step 2 too, and check its examples in `crates/{SHELL_CRATE}/tests/zz_reference_check.rs` "
                 "(step 3): how to build the shell's view state, draw a frame into a `ratatui::backend::TestBackend` of "
                 "a given size and read the buffer back as text, one string per row, resolve a key against the view "
                 "and pass the action to the shell's update, and apply what the update returns to the state. Include "
                 "every key, overlay, row, and drawn element the change added to the shell or altered, and how to "
                 "reach each one.\n\n")
    if items:
        note += ("5. For each item below, record whether the build provides it and how, in "
                "/work/out/implementation.json: `{\"items\": [{\"item\": \"<ID>\", \"status\": \"implemented\" | "
                "\"inherited\" | \"absent\" | \"unclear\", \"evidence\": [{\"file\": \"<path>\", \"symbols\": "
                "[\"<function, type, or variant>\"]}], \"note\": \"<one sentence>\"}]}`, one entry per item.\n"
                "   - implemented: the diff adds or changes code that does something toward the item; cite the files "
                "and symbols.\n"
                "   - inherited: the build has the behaviour through code the diff didn't need to touch: existing code "
                "the change relies on, or that already did this; cite the code that provides it.\n"
                "   - absent: the behaviour isn't produced: nothing in the diff addresses it and no existing code "
                "provides it; cite the files and symbols you checked.\n"
                "   - unclear: you can't tell.\n\n"
                "   This record is separate from the reference: don't mention the items in reference.md.\n\n"
                "   The items:\n" + "\n".join(f"   - {i}: {text}" for i, text in items) + "\n\n")
    return grading._template("extraction-rust.md", ITEMS=note)


def check_implementation(data, graded: list[str]) -> tuple[dict[str, str], list[str]]:
    """Each graded item's status from the extraction's record; an item with no valid record is "unclear"."""
    statuses = {i: "unclear" for i in graded}
    entries = data.get("items") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return statuses, ["no implementation record"]
    problems, seen = [], set()
    for e in entries:
        i = e.get("item") if isinstance(e, dict) else None
        if i not in statuses:
            problems.append(f"{i!r} isn't a graded item")
            continue
        seen.add(i)
        st = e.get("status")
        ev = [x for x in e.get("evidence") or [] if isinstance(x, dict) and x.get("file")]
        if st not in IMPLEMENTATION:
            problems.append(f"{i}: status {st!r}")
        elif st != "unclear" and not ev:
            problems.append(f"{i}: {st} but cites nothing")
        else:
            statuses[i] = st
    problems += [f"{i}: no record" for i in graded if i not in seen]
    return statuses, problems


HELPERS_DIR = "probe_helpers"
HELPERS_CHECK = "probe_helpers_check"


def _module_lines(mods: list[str]) -> list[str]:
    return [f'#[path = "{HELPERS_DIR}/{m}"] mod {m.split("/")[0].removesuffix(".rs")};' for m in mods]


def snapshot_helpers(held_dir: Path) -> dict[str, dict[str, str]]:
    """The snapshot's own test helper modules, per crate: what each test directory's main.rs declares that is a
    directory, or a file with no #[test] in it, as the held-out copy of the snapshot has them (the same for every
    arm). Paths are relative to the helper's own directory (common/mod.rs)."""
    out: dict[str, dict[str, str]] = {}
    for main in sorted(held_dir.glob("crates/*/tests/*/main.rs")):
        crate, src = main.parts[-4], main.parent
        for m in re.findall(r"(?m)^\s*(?:pub\s+)?mod\s+(\w+)\s*;", main.read_text(encoding="utf-8")):
            if (src / m).is_dir():
                for f in sorted((src / m).rglob("*.rs")):
                    out.setdefault(crate, {})[f"{m}/{f.relative_to(src / m)}"] = f.read_text(encoding="utf-8")
            elif (src / f"{m}.rs").exists() and "#[test]" not in (src / f"{m}.rs").read_text(encoding="utf-8"):
                out.setdefault(crate, {})[f"{m}.rs"] = (src / f"{m}.rs").read_text(encoding="utf-8")
    return out


def _entry_modules(files: dict[str, str]) -> list[str]:
    """The path each helper module is declared by: a directory's mod.rs, or a file."""
    return sorted({f.split("/")[0] + "/mod.rs" if "/" in f else f for f in files
                   if "/" not in f or f.count("/") == 1 and f.endswith("/mod.rs")})


def place_probe_helpers(ck, helpers: dict[str, dict[str, str]], *, sources: Callable[[], dict[str, str]]) -> dict:
    """Put each crate's snapshot helpers beside the probe tests (crates/<crate>/tests/probe_helpers/), and build them
    against the arm's code through a check target, with the compile-only adaptation; helpers that still don't build
    are withdrawn. Returns, per crate, the status, the module declarations a probe test uses, and any edits."""
    out = {}
    for crate, files in sorted(helpers.items()):
        base = f"crates/{crate}/tests/{HELPERS_DIR}"
        placed = {f"{base}/{rel}": text for rel, text in files.items()}
        for path, text in placed.items():
            ck.put(f"/work/app/{path}", text)
        mods = _entry_modules(files)
        check = f"crates/{crate}/tests/{HELPERS_CHECK}.rs"
        check_text = "#![allow(dead_code, unused_imports)]\n" + "\n".join(_module_lines(mods)) + "\n\n#[test]\nfn helpers_build() {}\n"
        ck.put(f"/work/app/{check}", check_text)
        cargo = (f"cd /work/app && CARGO_TARGET_DIR=/work/target timeout 1800 cargo test --offline "
                 f"--manifest-path crates/{crate}/Cargo.toml --test {HELPERS_CHECK} --no-run --message-format=json 2>&1")
        record, _ = rust_adapt.adapt_target(lambda: ck.sh(cargo, check=False), {**placed, check: check_text}, sources,
                                            lambda p, t: ck.put(f"/work/app/{p}", t))
        ck.sh(f"rm -f /work/app/{check}", check=False)
        entry = {"status": record["status"], "modules": mods, "declare": _module_lines(mods), "edits": record["edits"]}
        if record["status"] == "not adapted":
            ck.sh(f"rm -rf /work/app/{base}", check=False)
            entry["reason"] = record.get("reason")
        out[crate] = entry
    return out


def helpers_note(helpers: dict | None) -> str:
    offered = {c: h for c, h in (helpers or {}).items() if h["status"] != "not adapted"}
    if not offered:
        return ""
    parts = ["The project's own test helpers, built against this library, are in place for building setups. Use them "
             "where they fit; the reference still tells you how to call the library. To use a crate's helpers, put "
             "the lines given for it at the top of your test file:", ""]
    for crate, h in sorted(offered.items()):
        parts.append(f"- `crates/{crate}/tests/{HELPERS_DIR}/`:")
        parts += [f"  `{line}`" for line in h["declare"]]
    return "\n".join(parts) + "\n\n"


def execution_prompt(bid: str, helpers: dict | None = None, needs=()) -> str:
    """needs: what the batch's probes need; a probe that needs the shell gets its test in the shell's crate."""
    shell = (f"Probes marked **Needs:** {SHELL_NEED} drive the game's terminal shell: write each such probe's test "
             f"file in `/work/app/crates/{SHELL_CRATE}/tests/` and run it with `-p {SHELL_CRATE}`, whatever crate "
             "the batch's other probes use.\n\n") if _drives_shell(needs) else ""
    return grading._template("grade-execute-rust.md", BATCH=bid, HELPERS=helpers_note(helpers) + shell)


FAULTS = ("compile", "fixture", "interface", "observation")
JUDGE_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["verdicts"],
    "properties": {"verdicts": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["probe", "verdict", "evidence", "reason", "cause", "fault"],
        "properties": {"probe": {"type": "string"}, "verdict": {"type": "string", "enum": list(grading.VERDICTS)},
                       "evidence": {"type": "array", "items": {"type": "integer"}}, "reason": {"type": "string"},
                       # couldn't exercise is always the grader's error here: which part of the instrument broke
                       "cause": {"type": "string", "enum": ["execution", "none"]},
                       "fault": {"type": "string", "enum": [*FAULTS, "none"]}}}}},
}


def check_verdicts(result: dict, batch: list, lines: list[dict]) -> list[str]:
    """The other seeds' checks, and that a grader error names its fault and nothing else does."""
    problems = grading.check_verdicts(result, batch, lines)
    for v in result.get("verdicts", []):
        fault = v.get("fault") or "none"
        if v.get("verdict") == "couldn't exercise" and (v.get("cause") != "execution" or fault not in FAULTS):
            problems.append(f"{v.get('probe')}: \"couldn't exercise\" without naming the grader's fault")
        elif v.get("verdict") in ("met", "not met") and fault != "none":
            problems.append(f"{v.get('probe')}: a {v.get('verdict')!r} verdict naming a grader fault")
    return problems


def judge_prompt(batch, lines: list[dict], conventions: str = "") -> str:
    return grading._template("grade-judge-rust.md", PROBES=grading.render_for_judgment(batch, conventions),
                             LOG=log_for_judge(lines))


def _usage(rec) -> dict:
    return {"cost_usd": rec.usage.reported_cost_usd, "duration_s": round(rec.duration_s, 1),
            "models": {m: asdict(c) for m, c in (rec.usage.models or {}).items()}}


RERUN = ("cd /work/app && mkdir -p /work/out/probes && for f in crates/*/tests/{t}.rs; do [ -f \"$f\" ] || continue; "
         "cp \"$f\" /work/out/probes/{t}.rs; crate=$(echo \"$f\" | cut -d/ -f2); "
         "CARGO_TARGET_DIR=/work/target timeout 900 cargo test --offline --manifest-path crates/$crate/Cargo.toml "
         "--test {t} -- --nocapture --test-threads=1 > /work/out/probes/{t}.log 2>&1; "
         "echo \"EXIT=$?\" >> /work/out/probes/{t}.log; done; true")


def _judge_batch(ck, g: RustGraders, batch: list, bid: str, out: Path, *, volume: str, conventions: str,
                 run_role: Callable, attempts: int, helpers: dict | None, sessions: dict,
                 setups: dict[str, str] | None = None) -> dict[str, dict]:
    """Execution, the harness's own run of each probe's test, and judgment, for one batch."""
    bdir = out / bid
    bdir.mkdir(parents=True, exist_ok=True)
    rendered = grading.render_for_execution(batch, conventions, setups)
    ck.put(f"/work/out/probes-{bid}.md", rendered)
    (bdir / "probes.md").write_text(rendered, encoding="utf-8")
    try:
        rec = run_role(g.role(g.execute_model, tools=("Bash", "Read", "Write", "Edit"), workspace_volume=volume,
                              timeout_s=2400), execution_prompt(bid, helpers, needs={n for p in batch for n in p.needs}))
        sessions[bid] = {"usage": _usage(rec), "reply": rec.text}
    except executor.RoleFailed as e:
        sessions[bid] = {"error": str(e)}
    results = {}
    for p in batch:
        t = probe_target(p.id)
        ck.sh(RERUN.replace("{t}", t), check=False)
        results[p.id] = {"source": ck.get(f"/work/out/probes/{t}.rs"), "output": ck.get(f"/work/out/probes/{t}.log")}
        for kind in ("source", "output"):
            if results[p.id][kind] is not None:
                (bdir / f"{t}.{'rs' if kind == 'source' else 'log'}").write_text(results[p.id][kind], encoding="utf-8")
    lines = probe_log_lines(results)
    tries = []
    for _ in range(attempts):
        rec = run_role(g.role(g.judge_model, timeout_s=1200), judge_prompt(batch, lines, conventions),
                       json_schema=json.dumps(JUDGE_SCHEMA, separators=(",", ":")))
        problems = check_verdicts(rec.structured or {}, batch, lines)
        tries.append({"structured": rec.structured, "problems": problems, "usage": _usage(rec)})
        if not problems:
            break
    final = ({v["probe"]: {**v, "batch": bid} for v in (tries[-1]["structured"] or {}).get("verdicts", [])}
             if not tries[-1]["problems"] else {})
    (bdir / "judgment.json").write_text(json.dumps({"tries": tries, "verdicts": final, "lines": lines}, indent=1),
                                       encoding="utf-8")
    return final


def grade_probes(ck, g: RustGraders, probeset: grading.ProbeSet, probes: list, *, base: str, out: Path, volume: str,
                 batch_size: int = 4, run_role: Callable = executor.run_role, attempts: int = 3,
                 helpers: dict | None = None, items: list[tuple[str, str]] = (), guards=frozenset()) -> dict:
    """Extraction, then for each batch: execution, the harness's own run of each probe's test, and judgment. A probe
    the judge couldn't exercise is a grader error: it runs once more in a batch of its own, from no test, with the
    same instructions (nothing about the arm), and if it is still unresolved its verdict is "missing", with the fault.
    helpers: the snapshot's test helpers as placed (place_probe_helpers), offered to every executor. items: the change's
    graded items, (ID, statement), whose implementation the extraction records from the diff; an interface fault left
    after the rerun on an item it found absent is a confirmed absence: "not met". A probe that needs `tui` drives the
    terminal shell: the extraction then covers the shell's surface too, and its batch's executor is told the shell's
    crate. guards: the item IDs of keep-it-as-it-was rows, which untouched code meets: a "met" on one stays met though
    the extraction found it absent (recorded under guard_exempt), since an arm that rightly leaves that code alone gives
    the extraction nothing new to find."""
    out.mkdir(parents=True, exist_ok=True)
    rec = run_role(g.role(g.extraction_model, tools=("Bash", "Read", "Write", "Edit", "Glob", "Grep"),
                          workspace_volume=volume, timeout_s=2400),
                   extraction_prompt(items, needs={n for p in probes for n in p.needs}))
    reference = ck.get("/work/out/reference.md") or ""
    (out / "reference.md").write_text(reference, encoding="utf-8")
    sessions = {"extraction": {"usage": _usage(rec), "problems": [] if reference.strip() else ["no reference"]}}
    statuses: dict[str, str] = {}
    records: dict[str, dict] = {}
    if items:
        raw = ck.get("/work/out/implementation.json")
        try:
            data = json.loads(raw) if raw else None
        except ValueError:
            data = None
        statuses, problems = check_implementation(data, [i for i, _ in items])
        records = {e.get("item"): e for e in (data or {}).get("items") or [] if isinstance(e, dict)} if isinstance(data, dict) else {}
        (out / "implementation.json").write_text(json.dumps({"statuses": statuses, "problems": problems, "record": data},
                                                            indent=1), encoding="utf-8")
        ck.sh("rm -f /work/out/implementation.json", check=False)  # the executors never read the items
        sessions["extraction"]["implementation_problems"] = problems
    conventions = probeset.setup_notes
    kw = dict(volume=volume, conventions=conventions, run_role=run_role, attempts=attempts, helpers=helpers,
              sessions=sessions, setups=probeset.setups)
    verdicts: dict[str, dict] = {}
    for k, batch in enumerate(grading.batches(probes, batch_size), start=1):
        verdicts.update(_judge_batch(ck, g, batch, f"b{k:02d}", out, **kw))
    faults = grading.execution_faults(verdicts)
    by_id = {p.id: p for p in probes}
    reruns, missing, absent = {}, {}, {}
    for n, pid in enumerate(faults, start=1):
        t = probe_target(pid)
        ck.sh(f"rm -f /work/app/crates/*/tests/{t}.rs /work/out/probes/{t}.rs /work/out/probes/{t}.log", check=False)
        second = _judge_batch(ck, g, [by_id[pid]], f"x{n:02d}", out, **kw).get(pid)
        reruns[pid] = {"first": verdicts[pid], "second": second}
        if second is None or second.get("verdict") == "couldn't exercise":
            last = second or verdicts[pid]
            if last.get("fault") == "interface" and statuses.get(by_id[pid].item.split()[0]) == "absent":
                verdicts[pid] = {**last, "verdict": "not met", "absent": True}
                absent[pid] = {"fault": "interface", "reason": last.get("reason"), "implementation": "absent"}
                continue
            verdicts[pid] = {**last, "verdict": grading.MISSING}
            first = reruns[pid]["first"]
            missing[pid] = {"cause": "execution", "fault": last.get("fault"), "reason": last.get("reason"),
                            "first": {"fault": first.get("fault"), "reason": first.get("reason")}}
        else:
            verdicts[pid] = second
    # a "met" on an item the extraction found nothing addressing is a conflict between the two: neither counts
    conflicts: dict[str, dict] = {}
    guard_exempt: list[str] = []
    for pid, v in verdicts.items():
        if v.get("verdict") == "met" and statuses.get(by_id[pid].item.split()[0]) == "absent":
            if by_id[pid].item.split()[0] in guards:
                guard_exempt.append(pid)
                continue
            verdicts[pid] = {**v, "verdict": grading.CONFLICT}
            c = conflicts.setdefault(by_id[pid].item, {"probes": {}, "extraction": records.get(by_id[pid].item.split()[0])})
            c["probes"][pid] = {"verdict": "met", "reason": v.get("reason"), "evidence": v.get("evidence"),
                                "batch": v.get("batch")}
    probe_verdicts = {pid: v["verdict"] for pid, v in verdicts.items()}
    verdict_items = grading.item_verdicts(probe_verdicts, probes)
    by_fault: dict[str, int] = {}
    for m in missing.values():
        by_fault[m["fault"] or "unknown"] = by_fault.get(m["fault"] or "unknown", 0) + 1
    item_of = {p.id: p.item for p in probes}
    interface = {"not met (absent)": sorted({item_of[pid] for pid in absent}),
                 "missing": sorted({item_of[pid] for pid, m in missing.items() if m["fault"] == "interface"})}
    result = {"probes": probe_verdicts, "items": verdict_items, "details": verdicts, "sessions": sessions,
              "execution_faults": faults, "reruns": reruns, "missing": missing, "missing_by_fault": by_fault,
              "absent": absent, "interface_faults": interface, "implementation": statuses, "conflicts": conflicts,
              "guard_exempt": sorted(guard_exempt), "helpers": helpers or {}}
    (out / "verdicts.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    return result


# -------------------------------------------------------------------------------- a code-only grading checkout


AGENT_FILES = ("AGENTS.md", "CLAUDE.md", "GEMINI.md")  # as the variant builder strips them (clowder_variants.py)
HIDDEN_DIRS = ("docs", ".claude")
LID_MARKERS = ("@spec", "docs/intent")


def hidden_paths(paths: list[str], *, marked: set[str], symlinks: dict[str, str]) -> list[str]:
    """What graders don't see, whatever the arm: what the variant builder strips (docs/, .claude/, the agent
    instruction files, and LID tooling: files outside crates/ and not Markdown that carry LID markers, given as
    marked), agent files at any depth, and symlinks to any of these."""
    def hide(p: str) -> bool:
        return (p.split("/", 1)[0] in HIDDEN_DIRS or p.rsplit("/", 1)[-1] in AGENT_FILES
                or (p in marked and not p.startswith("crates/") and not p.endswith(".md")))
    out = {p for p in paths if hide(p)}
    for p, target in symlinks.items():
        resolved = os.path.normpath(os.path.join(os.path.dirname(p), target))
        if hide(p) or hide(resolved):
            out.add(p)
    return sorted(out)


def _is_doc(path: str) -> bool:
    return path.endswith(".md") or path.split("/", 1)[0] in HIDDEN_DIRS or path.rsplit("/", 1)[-1] in AGENT_FILES


STREAM_MARK = "@@ce-file@@"
CANDIDATES = "-e '@spec' -e '-[0-9][0-9][0-9]' -e 'docs/'"  # a superset of the files the builder's stripping changes


def _strip_prose(text: str, pattern: re.Pattern) -> str:
    import clowder_variants as cv
    return cv.strip_spec_ids(text + "\n", pattern)[0].rstrip("\n")


def _strip_rust(text: str, pattern: re.Pattern) -> str:
    """The variant builder's spec-ID stripping, on comments and string contents only: a comment line as the builder
    strips it, and on a code line the comment and each string's contents stripped as prose, with every code token
    left exactly as it was. The builder's own pass tidies a whole line, code included, which can break it
    ("fn f() {} // @spec X" loses its "()")."""
    import clowder_variants as cv
    masked = rust_adapt.mask(text, string_fill="\x00")
    out, at = [], 0
    for line in text.splitlines(keepends=True):
        m = masked[at:at + len(line)]
        at += len(line)
        if "@spec" not in line and not pattern.search(line):
            out.append(line)
            continue
        body, nl = (line[:-1], "\n") if line.endswith("\n") else (line, "")
        mb = m[:len(body)]
        starts = [k for k, (c, mc) in enumerate(zip(body, mb)) if mc == " " and not c.isspace()]
        c = starts[0] if starts else len(body)
        if starts and not body[:c].strip():  # a comment line, as the builder strips it
            out.append(cv.strip_spec_ids(line, pattern)[0])
            continue
        code, pieces, k = body[:c], [], 0
        for run in re.finditer("\x00+", mb[:c]):  # each string's contents, as prose
            content = code[run.start():run.end()]
            if "@spec" in content or pattern.search(content):
                content = _strip_prose(content, pattern)
            pieces += [code[k:run.start()], content]
            k = run.end()
        code = "".join(pieces + [code[k:]])
        comment = _strip_prose(body[c:], pattern).strip() if starts else ""
        out.append((code.rstrip() + " " + comment if comment else code.rstrip() if starts else code) + nl)
    return "".join(out)


def strip_texts(texts: dict[str, str], pattern: re.Pattern) -> dict[str, str]:
    """The files the variant builder's own stripping changes (clowder_variants.py), changed as it changes them:
    README.md without the paragraphs that describe LID, and every file without `@spec` annotations and spec-ID
    citations, in Rust in comments and strings only."""
    import clowder_variants as cv
    out = {}
    for path, text in texts.items():
        new = cv._readme(text)[0] if path == "README.md" else text
        new = _strip_rust(new, pattern) if path.endswith(".rs") else cv.strip_spec_ids(new, pattern)[0]
        if new != text:
            out[path] = new
    return out


def transform_texts(texts: dict[str, str], pattern: re.Pattern) -> tuple[dict[str, str], list[str], list[str]]:
    """The variant builder's stripping of a tree, given the files it can change: the tests that read the docs go
    (whole files, with their `mod` lines, and single test functions), then README and spec IDs are stripped.
    Returns (files changed, files removed, what went as tests)."""
    import clowder_variants as cv
    files = {p: t.encode() for p, t in texts.items()}
    try:
        dropped = cv.drop_doc_tests(files)
    except ValueError:  # code outside a test reads the docs: leave the tests as they are
        files, dropped = {p: t.encode() for p, t in texts.items()}, []
    after = {p: b.decode() for p, b in files.items()}
    after.update(strip_texts(after, pattern))
    removed = sorted(p for p in texts if p not in after)
    return {p: t for p, t in after.items() if t != texts[p]}, removed, dropped


def _fetch(ck, root: str, paths: list[str]) -> dict[str, str]:
    """The text of these files under root, in one call."""
    if not paths:
        return {}
    out = ck.sh(f"cd {root} && while read -r f; do [ -f \"$f\" ] || continue; printf '%s %s\\n' '{STREAM_MARK}' \"$f\"; "
                f"cat \"$f\"; [ -z \"$(tail -c1 \"$f\")\" ] || echo; done", stdin="\n".join(paths) + "\n", check=False)
    files, path, buf = {}, None, []
    for line in out.split("\n"):
        if line.startswith(STREAM_MARK + " "):
            if path is not None:
                files[path] = "\n".join(buf) + "\n"
            path, buf = line[len(STREAM_MARK) + 1:], []
        elif path is not None:
            buf.append(line)
    if path is not None:
        files[path] = "\n".join(buf).rstrip("\n") + "\n"
    return files


def _write(ck, root: str, files: dict[str, str]) -> None:
    """Write these files under root, in one call."""
    if not files:
        return
    stream = "".join(f"{STREAM_MARK} {p}\n{t if t.endswith(chr(10)) else t + chr(10)}" for p, t in sorted(files.items()))
    ck.sh(f"cd {root} && awk 'index($0, \"{STREAM_MARK} \") == 1 {{ if (f != \"\") close(f); "
          f"f = substr($0, {len(STREAM_MARK) + 2}); printf \"\" > f; next }} {{ print > f }}'", stdin=stream, check=False)


def grading_spec_pattern(ck, manifest_pattern: str | None) -> re.Pattern:
    """Spec IDs as the variant builder found them in the snapshot (the manifest's pattern) and as the arm's own
    specs write them, so a prefix an arm adds is stripped too."""
    import clowder_variants as cv
    specs = _fetch(ck, "/work/app", ck.sh("cd /work/app && git ls-files '*-specs.md'", check=False).split())
    own = cv.spec_id_pattern(cv.Tree(commit="", files={p: t.encode() for p, t in specs.items()})).pattern
    parts = [x for x in (manifest_pattern, own) if x and x != "(?!)"]
    return re.compile("|".join(f"(?:{x})" for x in parts)) if parts else re.compile("(?!)")


def prepare_for_graders(ck, base: str, commit: str, *, spec_pattern: str | None = None) -> dict:
    """Make the checkpoint a code-only checkout, after the harness's own git steps, the same for every arm:

    - count the arm's changes to docs and instruction files (context for cost and attention, never graded);
    - strip README.md and spec IDs as the variant builder strips the stripped variant, in the arm's checkout and in a
      copy of the starting commit, and write the diff the extraction reads, /work/out/arm.diff, between the two
      stripped trees, of code and tests only, so an `@spec` comment the arm added doesn't show either;
    - remove what the variant builder strips (docs/, .claude/, agent instruction files, LID tooling), and the history
      (.git) that would show it.
    spec_pattern: the variant manifest's spec-ID pattern, if the run was forked from a variant."""
    paths = ck.sh("cd /work/app && git ls-files", check=False).split()
    links = {}
    for line in ck.sh("cd /work/app && find . -path ./.git -prune -o -type l -exec sh -c "
                      "'printf \"%s\\t%s\\n\" \"$1\" \"$(readlink \"$1\")\"' _ {} \\;", check=False).splitlines():
        if "\t" in line:
            p, t = line.split("\t", 1)
            links[p.removeprefix("./")] = t
    marked = set(ck.sh("cd /work/app && git grep -lI -e '@spec' -e 'docs/intent' -- . ':(exclude)crates' "
                       "':(exclude,glob)**/*.md' 2>/dev/null", check=False).split())
    hidden = hidden_paths(paths, marked=marked, symlinks=links)
    docs = {"files": 0, "lines_added": 0, "lines_removed": 0, "paths": []}
    for line in ck.sh(f"cd /work/app && git diff --numstat {base} {commit}", check=False).splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and _is_doc(parts[2]):
            docs["files"] += 1
            docs["lines_added"] += int(parts[0]) if parts[0].isdigit() else 0
            docs["lines_removed"] += int(parts[1]) if parts[1].isdigit() else 0
            docs["paths"].append(parts[2])
    docs["paths"].sort()
    pattern = grading_spec_pattern(ck, spec_pattern)
    gone = set(hidden)
    # the arm's checkout, stripped in place
    head = [f for f in ck.sh(f"cd /work/app && git grep -lI {CANDIDATES} 2>/dev/null", check=False).split() if f not in gone]
    mains = {f for f in paths if re.fullmatch(r"crates/[^/]+/tests/[^/]+/main\.rs", f)}
    head_changed, head_removed, head_dropped = transform_texts(
        _fetch(ck, "/work/app", sorted((set(head) | mains | ({"README.md"} & set(paths))) - gone)), pattern)
    _write(ck, "/work/app", head_changed)
    if head_removed:
        ck.sh("cd /work/app && rm -f " + " ".join(f"'{p}'" for p in head_removed), check=False)
    # the starting commit, copied out and stripped the same way
    ck.sh(f"rm -rf /work/strip-base && mkdir -p /work/strip-base && cd /work/app && git archive {base} | tar -x -C /work/strip-base",
          check=False)
    listed = [f.removeprefix("./") for f in ck.sh(f"cd /work/strip-base && grep -rlI {CANDIDATES} . 2>/dev/null; "
                                                  "find . -path './crates/*/tests/*/main.rs'", check=False).split()]
    base_paths = sorted({f for f in listed if f not in gone and not f.startswith(("docs/", ".claude/"))
                         and f.rsplit("/", 1)[-1] not in AGENT_FILES} | {"README.md"})
    base_changed, base_removed, _ = transform_texts(_fetch(ck, "/work/strip-base", base_paths), pattern)
    _write(ck, "/work/strip-base", base_changed)
    if base_removed:
        ck.sh("cd /work/strip-base && rm -f " + " ".join(f"'{p}'" for p in base_removed), check=False)
    excludes = [":(exclude)docs", ":(exclude).claude", ":(exclude,glob)**/*.md",
                *(f":(exclude,glob)**/{f}" for f in AGENT_FILES), *(f":(exclude){p}" for p in sorted(marked))]
    size = ck.sh("mkdir -p /work/out && cd /work/app && "
                 "GIT_INDEX_FILE=/work/idx-head git add -A . && h=$(GIT_INDEX_FILE=/work/idx-head git write-tree) && "
                 "GIT_INDEX_FILE=/work/idx-base git --work-tree=/work/strip-base -C /work/strip-base "
                 "--git-dir=/work/app/.git add -A . && "
                 "b=$(GIT_INDEX_FILE=/work/idx-base git --git-dir=/work/app/.git write-tree) && "
                 "git diff \"$b\" \"$h\" -- . " + " ".join(f"'{x}'" for x in excludes)
                 + " > /work/out/arm.diff; wc -c < /work/out/arm.diff", check=False)
    # a clean checkout has no empty directories (git tracks none), so any left now held only hidden files
    ck.sh("cd /work/app && rm -rf " + " ".join(f"'{p}'" for p in [*hidden, *HIDDEN_DIRS]) + " .git"
          " /work/strip-base /work/idx-head /work/idx-base && find . -mindepth 1 -type d -empty -delete", check=False)
    return {"hidden": hidden, "doc_changes": docs, "diff_bytes": int(size.strip()) if size.strip().isdigit() else None,
            "spec_id_pattern": pattern.pattern,
            "stripped": {"files": len(head_changed), "start_files": len(base_changed), "doc_tests_dropped": head_dropped}}


# ------------------------------------------------------------------------------- items, and what they count


def kept_behaviour_ids(script_text: str) -> set[str]:
    """The IDs the change script lists as kept behaviour (`**Kept behaviour:** CLK-301, CLK-302.`), any change."""
    return {i for line in re.findall(r"\*\*Kept behaviour:\*\*([^\n]*)", script_text)
            for i in re.findall(r"\b[A-Z]+-\d+\b", line)}


def split_items(items: dict[str, str | None], kept: set[str]) -> tuple[dict, dict]:
    """(new-intent items, kept-behaviour checks), by the item's ID (its name's first word)."""
    new, checks = {}, {}
    for name, v in items.items():
        (checks if name.split()[0] in kept else new)[name] = v
    return new, checks


def items_met(items: dict[str, str | None], interface: dict[str, list[str]] | None = None) -> dict:
    """Items met, of the items with a verdict on the build: "missing" (a grader error a rerun didn't resolve) and
    items with no verdict are left out, and missing ones counted apart. Beside it, the items an interface fault left
    after the rerun: "not met (absent)" where the extraction found nothing addressing them, else missing."""
    decided = [v for v in items.values() if v and v not in (grading.MISSING, grading.CONFLICT)]
    return {"met": sum(v == "met" for v in decided), "of": len(decided),
            "missing": sum(v == grading.MISSING for v in items.values()),
            "conflicts": sum(v == grading.CONFLICT for v in items.values()),
            "interface_faults": {k: sum(i in items for i in (interface or {}).get(k, []))
                                 for k in ("not met (absent)", "missing")}}


def items_met_by_kind(items: dict[str, str | None], interface: dict[str, list[str]] | None = None, *, guards=frozenset()) -> dict:
    """items_met apart for the new-behaviour rows and the guard rows (keep-it-as-it-was rules), by item ID."""
    key = lambda i: i.split()[0]  # noqa: E731
    new = {i: v for i, v in items.items() if key(i) not in guards}
    guard = {i: v for i, v in items.items() if key(i) in guards}
    return {"new_rows_met": items_met(new, interface), "guard_rows_met": items_met(guard, interface),
            "guard_rows": sorted(guard)}


def reapply_guards(gdir: Path, probes: list, *, guards, kept: set[str]) -> dict:
    """Give a grading made before the guard rows were known their exemption, with no new model call: each conflict on a
    guard row goes back to the probes' own "met" (recorded under guard_exempt), the item verdicts and tallies are
    recounted, and the new-behaviour and guard rows are counted apart. The earlier summary is kept beside it as
    summary.before-guards.json. Returns the new summary."""
    vpath, spath = gdir / "probes" / "verdicts.json", gdir / "summary.json"
    v, summary = json.loads(vpath.read_text()), json.loads(spath.read_text())
    exempt = []
    for item, c in list((v.get("conflicts") or {}).items()):
        if item.split()[0] not in guards:
            continue
        for pid, ruling in c["probes"].items():
            v["probes"][pid] = ruling["verdict"]
            v.setdefault("details", {})[pid] = {**(v.get("details") or {}).get(pid, {}), "verdict": ruling["verdict"]}
            exempt.append(pid)
        del v["conflicts"][item]
    v["guard_exempt"] = sorted(set(v.get("guard_exempt") or []) | set(exempt))
    v["items"] = grading.item_verdicts(v["probes"], [p for p in probes if p.id in v["probes"]])
    vpath.write_text(json.dumps(v, indent=1), encoding="utf-8")
    if not (gdir / "summary.before-guards.json").exists():
        (gdir / "summary.before-guards.json").write_text(spath.read_text())
    items = {item: x["verdict"] for item, x in v["items"].items()}
    summary["items"], summary["kept_behaviour_checks"] = split_items(items, kept)
    summary["items_met"] = items_met(summary["items"], v.get("interface_faults"))
    summary["kept_behaviour_met"] = items_met(summary["kept_behaviour_checks"], v.get("interface_faults"))
    summary.update(items_met_by_kind(summary["items"], v.get("interface_faults"), guards=guards))
    summary["conflicts"] = v.get("conflicts") or {}
    summary["guard_exempt"] = v["guard_exempt"]
    spath.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return summary


# -------------------------------------------------------------------------- still-valid visible assertions


_ASSERT = re.compile(r"(?<![\w!])((?:debug_)?assert(?:_eq|_ne)?)\s*!\s*\(")


def load_kept_assertions(path: Path) -> dict[int, list[dict]]:
    """The still-valid assertions in tests the arm can see, per change: a JSON file
    {"changes": {"<n>": [{"keeps": "CLK-302", "file": "<path in the repository>", "test": "<fn name>",
    "assert": "<the assertion as written>"}]}}. An arm may change what a change retires in these tests, but not these."""
    data = json.loads(path.read_text(encoding="utf-8"))
    out: dict[int, list[dict]] = {}
    for n, entries in (data.get("changes") or {}).items():
        for e in entries:
            for k in ("file", "test", "assert"):
                if not e.get(k):
                    raise ValueError(f"{path}: an entry for change {n} has no {k!r}: {e}")
            if not _assertions(e["assert"]):
                raise ValueError(f"{path}: change {n}: not an assertion: {e['assert']!r}")
        out[int(n)] = entries
    return out


def _strip_comments(text: str) -> str:
    masked = rust_adapt._mask_cached(text)
    return "".join(" " if m == " " and not c.isspace() else c for c, m in zip(text, masked))


def _norm(text: str) -> str:
    return re.sub(r",([)\]}])", r"\1", re.sub(r"\s+", "", text)).rstrip(";")


def _assertions(code: str) -> list[tuple[str, list[str], str]]:
    """(macro, arguments, statement) for each assertion in code whose comments are already stripped."""
    masked = rust_adapt.mask(code)
    out = []
    for m in _ASSERT.finditer(masked):
        depth, k = 0, m.end() - 1
        for k in range(m.end() - 1, len(masked)):
            depth += {"(": 1, ")": -1}.get(masked[k], 0)
            if depth == 0:
                break
        args = [code[a:b] for a, b in rust_adapt._split_top(masked, m.end(), k, types=False)]
        end = k + 1
        rest = masked[end:].lstrip()
        stmt = code[m.start():end] + (";" if rest.startswith(";") else "")
        out.append((m.group(1), args, stmt))
    return out


def _core(macro: str, args: list[str]) -> tuple:
    return (macro.removeprefix("debug_"), *(_norm(a) for a in args[:2 if macro.endswith(("_eq", "_ne")) else 1]))


def _subject(macro: str, args: list[str]) -> str:
    first = _norm(args[0]) if args else ""
    if not macro.endswith(("_eq", "_ne")):
        first = re.split(r"==|!=|>=|<=|<|>", first)[0]
    return first.lstrip("!&*")


def _tests_in(path: str, text: str) -> list[tuple[str, str, str]]:
    """(name, attributes, body) of each test function in a file, comments stripped."""
    from . import rust_classify
    masked = rust_adapt._mask_cached(text)
    out, seen = [], set()
    for m in re.finditer(r"#\s*\[\s*(?:\w+::)*test\b[^\]]*\]", masked):
        f = re.compile(r"\bfn\s+(\w+)").search(masked, m.end())
        if not f or f.group(1) in seen:
            continue
        seen.add(f.group(1))
        span = rust_classify._fn_span(path, text, f.group(1))
        if not span:
            continue
        lines = _strip_comments(text).splitlines()[span[0] - 1:span[1]]
        at = next((k for k, l in enumerate(lines) if re.search(rf"\bfn\s+{re.escape(f.group(1))}\b", l)), 0)
        out.append((f.group(1), "\n".join(lines[:at]), "\n".join(lines[at:])))
    return out


def audit_visible_assertions(entries: list[dict], show: Callable[[str, str], str | None], *, base: str, head: str,
                             renamed: dict[str, str] | None = None,
                             list_tests: Callable[[str, str], list[str]] | None = None) -> dict:
    """Each still-valid assertion at the change's end, found by its content (layout and message aside) wherever it
    now sits: in the test the input names, in any other test in the same file, or in another test file of the same
    crate (list_tests(rev, "crates/<crate>") gives them).

    - kept: in the test the input names;
    - moved: in a test with another name, or in another file (a rename is good hygiene): recorded with where it is;
    - weakened: the test it sits in is now ignored or expects a panic, or no copy is left but an assertion about the
      same subject replaced it (flagged with its new text for a reader);
    - deleted: found in no test in the crate (one commented out is gone).
    An entry not in its test at the change's start is reported apart: the input is wrong, not the arm."""
    from . import rust_classify
    rows = []
    for e in entries:
        row = {k: e.get(k) for k in ("keeps", "file", "test", "assert")}
        want = _assertions(e["assert"])[0]
        core = _core(*want[:2])
        start = show(base, e["file"])
        if not start:
            rows.append({**row, "status": "not found at the start",
                         "detail": "the file isn't in this checkout at the change's start (a variant without it)"})
            continue
        was = {n: (a, b) for n, a, b in _tests_in(e["file"], start)}.get(e["test"])
        if was is None or not any(_core(m, a) == core for m, a, _ in _assertions(was[1])):
            rows.append({**row, "status": "not found at the start",
                         "detail": "the assertion isn't in the test at the change's start"})
            continue
        path_now = (renamed or {}).get(e["file"], e["file"])
        crate = "/".join(e["file"].split("/")[:2])
        files = [path_now] + [f for f in (list_tests(head, crate) if list_tests else []) if f != path_now]
        tests = []  # (file, name, attrs, body), the named test first
        for f in files:
            text = show(head, f)
            if text:
                tests += [(f, n, a, b) for n, a, b in _tests_in(f, text)]
        # Where several tests hold it, the likeliest successor of the named test: the named test itself, then the test
        # sharing the most of its assertions at the start (a renamed test keeps most of them), then the same file,
        # then the name sharing the most words.
        before = {_core(m, a) for m, a, _ in _assertions(was[1])}
        words = set(e["test"].split("_"))

        def rank(t):
            cores = {_core(m, a) for m, a, _ in _assertions(t[3])}
            return (not (t[0] == path_now and t[1] == e["test"]), -len(before & cores), t[0] != path_now,
                    -len(words & set(t[1].split("_"))))
        holding = [t for t in tests if any(_core(m, a) == core for m, a, _ in _assertions(t[3]))]
        hit = min(holding, key=rank) if holding else None
        if hit:
            f, n, attrs, body = hit
            where = {"file": f, "test": n}
            shared = len(before & {_core(m, a) for m, a, _ in _assertions(body)}) - 1  # besides this one
            if "#[ignore" in attrs and "#[ignore" not in was[0]:
                rows.append({**row, "status": "weakened", "now_in": where,
                             "detail": "the test is now #[ignore]" if n == e["test"] and f == path_now
                             else "it now sits in a test that is #[ignore]"})
            elif "#[should_panic" in attrs and "#[should_panic" not in was[0]:
                rows.append({**row, "status": "weakened", "now_in": where,
                             "detail": "the test now expects a panic" if n == e["test"] and f == path_now
                             else "it now sits in a test that expects a panic"})
            elif n == e["test"] and f == path_now:
                rows.append({**row, "status": "kept", "now_in": where, "detail": "present (layout and message aside)"})
            else:
                rows.append({**row, "status": "moved", "now_in": where, "shared_with_original": shared,
                             "detail": "present in a test with another name" if f == path_now
                             else "present in another test file of the crate"})
            continue
        subject = _subject(*want[:2])
        same = [t for t in tests if t[0] == path_now and t[1] == e["test"]] or [t for t in tests if t[0] == path_now]
        near = [stmt for t in same for m, a, stmt in _assertions(t[3]) if subject and subject in _norm(stmt)]
        if near:
            rows.append({**row, "status": "weakened", "detail": "the assertion changed: check what it now asserts",
                         "now": [" ".join(x.split()) for x in near]})
        else:
            rows.append({**row, "status": "deleted", "detail": "not found in any test in the crate"})
    count = lambda st: sum(r["status"] == st for r in rows)
    return {"assertions": rows, "kept": count("kept"), "moved": count("moved"), "deleted": count("deleted"),
            "weakened": count("weakened"), "not_found_at_start": count("not found at the start"),
            "flagged": [r for r in rows if r["status"] in ("deleted", "weakened")],
            # a move to a test sharing nothing else with the original may be a generic assertion found elsewhere: check
            "moved_sharing_nothing_else": sum(r["status"] == "moved" and r["shared_with_original"] == 0 for r in rows),
            "moves": [{"keeps": r["keeps"], "item_test": r["test"], **r["now_in"],
                       "shared_with_original": r["shared_with_original"]} for r in rows if r["status"] == "moved"]}


# ---------------------------------------------------------------------------------------------- the checkpoint


@dataclass
class RustCheckpoint:
    """A fork's commit checked out at /work/app in its own volume, with build output at /work/target."""
    name: str
    commit: str
    image: str
    runner: Callable = subprocess.run

    @property
    def volume(self) -> str:
        return f"ce-gr-{self.name}-ckpt"

    def sh(self, script: str, stdin: str | None = None, check: bool = True) -> str:
        p = self.runner(["docker", "run", "--rm", "-i", "--network", "none", "-v", f"{executor._volume(self.volume)}:/work",
                         "-w", "/work", self.image, "sh", "-c", script], input=stdin, capture_output=True, text=True)
        if check and p.returncode != 0:
            raise RuntimeError(f"checkpoint command failed ({p.returncode}): {script[:160]}: {p.stderr[-500:]}")
        return p.stdout

    def put(self, path: str, text: str) -> None:
        self.sh(f"mkdir -p \"$(dirname '{path}')\" && cat > '{path}'", stdin=text)

    def get(self, path: str) -> str | None:
        p = self.runner(["docker", "run", "--rm", "-v", f"{executor._volume(self.volume)}:/work", self.image, "cat", path],
                        capture_output=True, text=True)
        return p.stdout if p.returncode == 0 else None

    def export(self, workspace_volume: str) -> None:
        self.runner(["docker", "run", "--rm", "-v", f"{executor._volume(workspace_volume)}:/src:ro",
                     "-v", f"{executor._volume(self.volume)}:/work", self.image, "sh", "-c",
                     # .git alone, checked out at the exact commit: a commit on a detached HEAD (jj leaves one, and
                     # so does the harness's own) is found, and no jj state, build output, or untracked file comes along
                     f"find /work -mindepth 1 -delete && mkdir -p /work/app /work/out && cp -a /src/.git /work/app/.git && "
                     f"cd /work/app && git checkout -q -f --detach {self.commit} && git clean -fdxq"],
                    check=True, capture_output=True, text=True)

    def drop_target(self) -> None:
        self.sh("rm -rf /work/target", check=False)
