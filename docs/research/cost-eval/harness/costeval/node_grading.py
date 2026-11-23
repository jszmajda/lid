"""Grading one change of an M2h fork (openGym, Node): keeping, three-valued dependency probes, new rows, joint outcome.

Design: M2h's harness note (seeds/opengym/hidden/m2h-harness-needs.md, "Grading" and "The joint-outcome report") and its
plan (m2h-plan.md, "Joint outcome"); the model is M2f's Rust grader (rust_grading.py, grade_rust.py), whose outputs this
keeps. The pieces, in the order grade_node.py runs them:

1. **Export.** The fork's commit is checked out of its workspace's .git into a checkpoint volume of its own (/work/app),
   with the start's installed dependencies (every `node_modules` the workspace holds; git ignores them) copied beside
   it. Suites run with no network, except `watch-zepp`'s `npm ci`, which installs its dev dependencies first.
2. **Keeping.** The existing suites (api: `node --test`; frontend: `npx vitest run`; mcp: `npm test`; zepp:
   `node --test` after `npm ci`) run on the fork's code with the start's own test files put back (the arm's edits to
   them undone and its new test files taken out: keeping is graded by the tests the project had), and are compared
   test by test with a baseline: the same suites on the untouched start, cached per start commit. A test counts when
   it passed on the start; each change's retired tests don't. Retired tests come back as grader-owned adjustments
   (graded.json, "Adjustments"): a patch or whole-file copies on the start's test files, applied before the suites
   run on the fork, and compared with the start under the same adjustment (those files alone, cached per change). An
   adjusted test that fails on the adjusted start pins the change's new behaviour itself: it is reported apart, never
   counted. Known flaky tests are rerun alone, up to a set number of times, before a failure stands. A test whose file
   didn't load on the fork, or that didn't run, is reported apart from the share, as M2f's tests not built were.
   Failures are classified "new state only" or "keeping failure" (prompts/keeping-classify-node.md).
3. **The graders' view.** After keeping, graders get a code-only checkout whatever the arm: docs/, .claude/, agent
   instruction files and every Markdown file go, `@spec` annotations and the arm's spec IDs leave code comments, and
   .git goes. The arm's diff of code and tests is written with the same annotations taken out.
4. **Dependency probes** (fixed in advance, graded.json, "Dependency probes"): one test file per probe, run alone in its
   package. Tests titled `precondition: …` check the change's "Dependency exercised only if" line; tests titled
   `dependency: …` check the dependent behaviour; tests titled `setup: …` (or `setup[OGM-NNkk]: …`) and failures whose
   message begins `setup:` or `fixture:` are setup steps. Precondition failed: not exercised. Preconditions passed and
   every dependency test passed: kept; a dependency test failed: broken. A setup failure, a file that didn't load, or
   a result that is missing: missing. An optional adapter, written per build by a model blind to the arm from a frozen
   interface and list of permitted operations, maps the probe to the build's own interface; a build without it gets
   an adapter that says so (the probe then reports not exercised), and an adapter that couldn't be written is missing.
   Controls go the same way through their comparison row.
5. **New rows.** Probes in M2f's format, turned into tests by an executor after interface extraction: each probe is
   routed by its Needs to a package and runner (fe: vitest with happy-dom; api: `node --test` with a `server.js`
   child; zepp: the page against the Zepp OS stand-ins; mcp: vitest). Extraction statuses, the absent-conflict rule,
   guard rows and the rerun of grader errors are M2f's. Added for M2h: a probe with an "Exercised only if" line may be
   judged "not exercised"; a probe or row may declare "Runs only if" (another row implemented or met), and doesn't
   run, "not exercised", when it fails; a probe whose setup step failed on another row's behaviour is "blocked" by
   that row, with that row's repair report.
6. **Joint outcome** (m2h-plan.md): implemented (yes, partly or no over the change's stated non-guard new rows; N/A
   with none), the dependent behaviour (kept, broken, not exercised or missing), the tier, and the plan's notes.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from . import executor, grading, rust_classify as rc, rust_grading as rg

IMAGE = "lid-cost-eval-executor-node:2.1.323"
APP = "/work/app"
RUNS = "/work/out/runs"
REPORTER_PATH = "/work/grader/node-reporter.mjs"
PROBE_TIMEOUT = 900

# ------------------------------------------------------------------------------------------------- the suites


@dataclass(frozen=True)
class Suite:
    name: str
    package: str  # the folder it runs in, relative to the checkout
    runner: str  # "node-test" or "vitest"
    glob: str  # what a whole run runs (node-test), or "" for the runner's own discovery
    timeout: int
    install: str | None = None  # run first, with the network (watch-zepp's dev dependencies)
    npm_test: bool = False  # run through `npm test --` (mcp), as the project's own command is

    def command(self, out_base: str, files: list[str] | None = None) -> str:
        """The run, with the grader's machine-readable report at out_base + .jsonl (node) or .json (vitest) beside the
        runner's own output. files: paths relative to the package, in place of a whole run."""
        what = " ".join(files) if files else self.glob
        if self.runner == "node-test":
            return (f"node --test --test-reporter=spec --test-reporter-destination=stdout --test-reporter={REPORTER_PATH} "
                    f"--test-reporter-destination={out_base}.jsonl {what}").rstrip()
        lead = "npm test --" if self.npm_test and not files else "npx vitest run"
        return f"{lead} --reporter=default --reporter=json --outputFile.json={out_base}.json {what}".rstrip()

    @property
    def report_ext(self) -> str:
        return ".jsonl" if self.runner == "node-test" else ".json"


SUITES = {
    "api": Suite("api", "api", "node-test", "test/*.test.js", 1800),
    "frontend": Suite("frontend", "frontend", "vitest", "", 3600),
    "mcp": Suite("mcp", "mcp", "vitest", "", 600, npm_test=True),
    "zepp": Suite("zepp", "watch-zepp", "node-test", "test/*.test.js", 600, install="npm ci --no-audit --no-fund"),
    # CI's routines job (needs the catalogue's media); not one of the plan's four suites
    "routines": Suite("routines", ".", "node-test", "scripts/routines/routines.test.mjs", 600),
}
DEFAULT_SUITES = ("api", "frontend", "mcp", "zepp")
FLAKY_DEFAULT = ({"suite": "frontend", "name": "useStore.stale-sync"},  # fails at the pin too (draws.txt)
                 {"suite": "api", "name": "server-origin-hint"})  # under load
FLAKY_RERUNS = 3


def suite_of(path: str) -> str | None:
    """The suite whose package holds a path in the checkout."""
    for s in sorted(SUITES.values(), key=lambda s: -len(s.package)):
        if s.package != "." and path.startswith(s.package + "/"):
            return s.name
    return "routines" if path.startswith("scripts/routines/") else None


def _in_package(suite: Suite, path: str) -> str:
    return path if suite.package == "." else path.removeprefix(suite.package + "/")


NODE_REPORTER = r"""// The grader's node --test reporter (costeval/node_grading.py): one JSON line per test result, one per test file
// that failed before any test in it ran, and one per count in the runner's own summary. Paths are relative to
// GRADER_ROOT (default /work/app).
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = process.env.GRADER_ROOT || '/work/app'
const abs = f => !f ? null : String(f).startsWith('file:') ? fileURLToPath(f) : path.resolve(String(f))
const rel = f => { const a = abs(f); return a ? path.relative(ROOT, a) : null }
const plain = v => {
  try {
    return JSON.parse(JSON.stringify(v, (k, x) => typeof x === 'bigint' ? `${x}n` : typeof x === 'function' ? '[function]'
      : typeof x === 'symbol' ? String(x) : x === undefined ? '[undefined]' : x))
  } catch { try { return String(v) } catch { return '[unprintable]' } }
}
const errorOf = e => {
  if (!e) return undefined
  const c = e.cause && typeof e.cause === 'object' ? e.cause : null
  const src = c || e
  const out = { message: String(c ? (c.message ?? '') : (e.cause !== undefined ? e.cause : (e.message ?? ''))),
    failureType: e.failureType, code: src.code }
  if (c && 'actual' in c) out.actual = plain(c.actual)
  if (c && 'expected' in c) out.expected = plain(c.expected)
  if (c && c.operator) out.operator = c.operator
  out.stack = String(src.stack || '').split('\n').slice(0, 12).join('\n')
  return out
}

export default async function * reporter (source) {
  const stacks = new Map()
  const stderr = new Map()
  for await (const ev of source) {
    const d = ev.data || {}
    if (ev.type === 'test:start') {
      const key = abs(d.file)
      const s = (stacks.get(key) || []).slice(0, d.nesting)
      s.push(d.name)
      stacks.set(key, s)
    } else if (ev.type === 'test:pass' || ev.type === 'test:fail') {
      const key = abs(d.file)
      const status = ev.type === 'test:fail' ? 'failed' : d.skip ? 'skipped' : d.todo ? 'todo' : 'passed'
      if (d.nesting === 0 && key && abs(d.name) === key) { // the file itself, run in its own process
        if (status === 'failed') {
          const lines = (stderr.get(key) || []).join('').split('\n').filter(Boolean)
          const msg = lines.find(l => /Error\b|error:/.test(l)) || lines.slice(-1)[0] || String(d.details?.error?.message || 'failed')
          yield JSON.stringify({ event: 'file-failed', file: rel(d.file), message: msg, stderr: lines.slice(-30).join('\n') }) + '\n'
        }
        continue
      }
      const out = { event: 'test', file: rel(d.file), name: d.name, ancestors: (stacks.get(key) || []).slice(0, d.nesting),
        nesting: d.nesting, type: d.details?.type || 'test', status }
      const err = errorOf(d.details?.error)
      if (err && status === 'failed') out.error = err
      yield JSON.stringify(out) + '\n'
    } else if (ev.type === 'test:stderr') {
      const key = abs(d.file)
      const a = stderr.get(key) || []
      a.push(String(d.message))
      if (a.length > 200) a.shift()
      stderr.set(key, a)
    } else if (ev.type === 'test:diagnostic' && d.nesting === 0 && !d.file) {
      const m = /^(tests|suites|pass|fail|cancelled|skipped|todo) (\d+)$/.exec(String(d.message || ''))
      if (m) yield JSON.stringify({ event: 'count', key: m[1], value: Number(m[2]) }) + '\n'
    }
  }
}
"""


# --------------------------------------------------------------------------------------------- the seed's text


@dataclass(frozen=True)
class Row:
    id: str
    behaviour: str
    disclosure: str  # "Stated" or "Askable"


@dataclass
class ChangeInfo:
    """What grading reads of one change in m2h-changes.md."""
    number: int
    title: str
    type: str = ""
    edits_part: str = ""
    tier: str = ""
    request: str = ""
    rows: list[Row] = field(default_factory=list)
    guard_rows: list[str] = field(default_factory=list)
    exercised_only_if: str | None = None  # a cross-component change's dependency line
    comparison_row: str | None = None  # a control's comparison row
    retired: list[tuple[str, str]] = field(default_factory=list)  # (file, the rest of the line after "::")
    retired_unparsed: list[str] = field(default_factory=list)  # a line naming tests without a title
    repair_reports: dict[str, str] = field(default_factory=dict)  # row ID or "Dependency" -> the report


def _section(text: str, name: str) -> str:
    m = re.search(rf"(?ms)^### {re.escape(name)}\s*$(.*?)(?=^### |^## |\Z)", text)
    return m.group(1) if m else ""


def _strip_quotes(s: str) -> str:
    return s.strip().strip("“”\"").strip()


def parse_changes(text: str) -> dict[int, ChangeInfo]:
    out: dict[int, ChangeInfo] = {}
    parts = re.split(r"(?m)^## Change (\d+) — (.*)$", text)
    for k in range(1, len(parts) - 2, 3):
        n, title, body = int(parts[k]), parts[k + 1].strip(), parts[k + 2]
        c = ChangeInfo(number=n, title=title)
        fields = dict(re.findall(r"(?m)^\*\*([^*]+):\*\*\s*(.*?)\s*$", body))
        c.type = fields.get("Type", "")
        c.edits_part = fields.get("Edits part", "")
        c.tier = fields.get("Searchability tier", "").split(".")[0].strip()
        c.request = "\n".join(l[1:].strip() for l in _section(body, "Owner request").splitlines() if l.startswith(">"))
        for line in _section(body, "New rows").splitlines():
            cells = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(cells) >= 3 and re.fullmatch(r"OGM-\d{4}", cells[0]):
                c.rows.append(Row(id=cells[0], behaviour=cells[1], disclosure=cells[2]))
        c.guard_rows = re.findall(r"\*\*Guard row:\*\*\s*(OGM-\d{4})", body)
        m = re.search(r"\*\*Dependency exercised only if\*\*\s+(.+?)\.\s+Otherwise", body, re.S)
        c.exercised_only_if = " ".join(m.group(1).split()) if m else None
        m = re.search(r"(?m)^\*\*Comparison row:\*\*\s*(.+)$", body)
        c.comparison_row = m.group(1).strip() if m else None
        for line in _section(body, "Retired tests").splitlines():
            if not line.startswith("- "):
                continue
            item = line[2:].strip()
            m = re.match(r"(\S+\.test\.\w+)::(.+)$", item)
            if m:
                c.retired.append((m.group(1), m.group(2).strip()))
            elif re.search(r"\S+\.test\.\w+", item):
                c.retired_unparsed.append(item)
        for m in re.finditer(r"(?m)^- \*\*(OGM-\d{4}|Dependency):\*\*\s*(.+)$", _section(body, "Repair reports")):
            c.repair_reports[m.group(1)] = _strip_quotes(m.group(2))
        out[n] = c
    return out


def change_text(c: ChangeInfo) -> str:
    """What a classifier reads of the change: its title and the owner's request."""
    return f"{c.title}\n\n{c.request}"


def load_guard_rows(path: Path) -> dict[str, dict]:
    return json.loads(Path(path).read_text(encoding="utf-8")).get("rows") or {}


# ----------------------------------------------------------------------------------------------- test files

TEST_DIRS = {"test", "tests", "__tests__", "fixtures", "__fixtures__", "fakes", "__mocks__"}
SUITE_CONFIG = re.compile(r"(^|/)(vite|vitest)\.config\.[cm]?[jt]s$|(^|/)package\.json$")


def is_test_path(path: str) -> bool:
    """A test file, or a file only tests use: `*.test.*`, `*.spec.*`, `*.test-util.*`, `test-setup.*`, or anything
    under a test, fixtures or fakes folder; never inside node_modules."""
    parts = path.split("/")
    if "node_modules" in parts:
        return False
    base = parts[-1]
    if re.search(r"\.(test|spec)\.[^.]+$|\.test-util\.[^.]+$|^test-setup\.[^.]+$", base):
        return True
    return any(p in TEST_DIRS for p in parts[:-1])


def test_file_plan(name_status: str) -> dict:
    """What the arm did to test files, from `git diff --name-status -M <start> <commit>`, and what keeping undoes: the
    start's test files the arm edited, deleted or renamed are put back ("restore"), and test files it added or renamed
    to are taken out ("remove"). Suite configuration it changed is listed, and left as it is."""
    edited, deleted, renamed, added, config = [], [], [], [], []
    for line in name_status.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, paths = parts[0], parts[1:]
        if any(SUITE_CONFIG.search(p) for p in paths):
            config.append(paths[-1])
        if not any(is_test_path(p) for p in paths):
            continue
        if status.startswith("M") and is_test_path(paths[0]):
            edited.append(paths[0])
        elif status.startswith("D"):
            deleted.append(paths[0])
        elif status.startswith("R") and len(paths) == 2:
            renamed.append([paths[0], paths[1]])
        elif status.startswith(("A", "C")):
            added.append(paths[-1])
    restore = sorted({*edited, *deleted, *(r[0] for r in renamed if is_test_path(r[0]))})
    remove = sorted({*added, *(r[1] for r in renamed if is_test_path(r[1]))} - set(restore))
    return {"edited": sorted(edited), "deleted": sorted(deleted), "renamed": sorted(renamed), "added": sorted(added),
            "restore": restore, "remove": remove, "suite_config_changed": sorted(config)}


# -------------------------------------------------------------------------------------------- the test output


def test_id(file: str, ancestors: list[str], title: str) -> str:
    return f"{file}::{' > '.join([*ancestors, title])}"


def _unique(tests: dict, tid: str) -> str:
    if tid not in tests:
        return tid
    k = 2
    while f"{tid} #{k}" in tests:
        k += 1
    return f"{tid} #{k}"


def parse_node_events(text: str) -> dict:
    """The grader's node reporter's lines: {"tests": {id: record}, "file_failures": {file: message}, "counts": {...}}.
    A test whose subtests ran is a roll-up of them, marked so and never counted itself; suites aren't tests."""
    tests, failures, counts, parents = {}, {}, {}, set()
    for line in (text or "").splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if not isinstance(ev, dict):
            continue
        kind = ev.get("event")
        if kind == "count":
            counts[ev["key"]] = ev["value"]
        elif kind == "file-failed":
            failures[ev["file"]] = ev.get("message") or "failed before any test ran"
        elif kind == "test":
            anc = list(ev.get("ancestors") or [])
            if anc:
                parents.add(test_id(ev["file"], anc[:-1], anc[-1]))
            if ev.get("type") == "suite":
                continue
            tid = _unique(tests, test_id(ev["file"], anc, ev["name"]))
            r = {"id": tid, "file": ev["file"], "title": ev["name"], "ancestors": anc, "status": ev.get("status")}
            if ev.get("error"):
                r["error"] = ev["error"]
            tests[tid] = r
    for p in parents:
        if p in tests:
            tests[p]["rollup"] = True
    return {"tests": tests, "file_failures": failures, "counts": counts}


VITEST_STATUS = {"passed": "passed", "failed": "failed", "skipped": "skipped", "pending": "skipped", "todo": "todo",
                 "disabled": "skipped"}


def parse_vitest_json(text: str, root: str = APP) -> dict:
    """A vitest JSON report, as parse_node_events returns its own. A file that failed with no tests collected didn't
    load; a test skipped in a file that failed didn't run because of it (a hook that threw), and is marked so."""
    data = json.loads(text)
    tests, failures = {}, {}
    for f in data.get("testResults") or []:
        file = f["name"].removeprefix(root.rstrip("/") + "/")
        results = f.get("assertionResults") or []
        message = str(f.get("message") or "").strip()
        failed = f.get("status") == "failed"
        if failed and not results:
            failures[file] = (message.splitlines() or ["failed before any test ran"])[0]
            continue
        for a in results:
            anc = list(a.get("ancestorTitles") or [])
            tid = _unique(tests, test_id(file, anc, a["title"]))
            status = VITEST_STATUS.get(a.get("status"), a.get("status"))
            r = {"id": tid, "file": file, "title": a["title"], "ancestors": anc, "status": status}
            if status == "failed":
                r["error"] = {"message": "\n".join(a.get("failureMessages") or [])[:20000]}
            if status == "skipped" and failed:
                r["in_failed_file"] = (message.splitlines() or ["the file failed"])[0]
            tests[tid] = r
    counts = {"tests": data.get("numTotalTests"), "pass": data.get("numPassedTests"), "fail": data.get("numFailedTests"),
              "skipped": data.get("numPendingTests"), "todo": data.get("numTodoTests")}
    return {"tests": tests, "file_failures": failures, "counts": {k: v for k, v in counts.items() if v is not None}}


def parse_report(suite: Suite, text: str | None) -> dict | None:
    if not text or not text.strip():
        return None
    try:
        return parse_node_events(text) if suite.runner == "node-test" else parse_vitest_json(text)
    except (ValueError, KeyError, TypeError):
        return None


# ----------------------------------------------------------------------------------------------- flaky tests


def flaky_entries(arg: str | None) -> list[dict]:
    """The known flaky tests: the default list (None), none ("none"), a JSON list, or a JSON file. Each entry names a
    suite and a test file's name before `.test.` (or a "file" path in the checkout)."""
    if arg is None:
        return [dict(e) for e in FLAKY_DEFAULT]
    if arg.strip() == "none":
        return []
    text = arg if arg.lstrip().startswith("[") else Path(arg).read_text(encoding="utf-8")
    return list(json.loads(text))


def _file_name(path: str) -> str:
    return path.rsplit("/", 1)[-1].split(".test.")[0]


def is_flaky(r: dict, suite: str, flaky: list[dict]) -> bool:
    return any(e.get("suite") == suite and (e.get("file") == r["file"] or e.get("name") == _file_name(r["file"]))
               for e in flaky)


# ---------------------------------------------------------------------------------------------- running suites


def run_suite(ck, suite: Suite, label: str, *, files: list[str] | None = None) -> dict:
    """One run of a suite (or of some of its files, paths in the checkout) in the checkpoint, with no network. Returns
    the parsed run with "exit", "minutes" and "log"; "error" when the runner wrote no report."""
    base = f"{RUNS}/{label}/{suite.name}"
    rel = [_in_package(suite, f) for f in files] if files else None
    # the run is the script's last command; the trap records its exit
    script = (f"mkdir -p {RUNS}/{label} && rm -f {RUNS}/{label}/{suite.name}.* && exec > {base}.log 2>&1 && "
              f"trap 'echo $? > {base}.exit' EXIT && cd {APP}/{suite.package} && "
              f"NO_COLOR=1 GRADER_ROOT={APP} timeout {suite.timeout} {suite.command(base, rel)}")
    t0 = time.monotonic()
    ck.sh(script, check=False)
    m = re.search(r"\d+", ck.get(f"{base}.exit") or "")
    log = ck.get(f"{base}.log") or ""
    report = ck.get(f"{base}{suite.report_ext}")
    run = parse_report(suite, report)
    if run is None:
        run = {"tests": {}, "file_failures": {}, "counts": {}, "error": "no report from the runner: " + log[-1500:]}
    run.update({"exit": int(m.group(0)) if m else None, "minutes": round((time.monotonic() - t0) / 60, 2), "log": log})
    return run


def install(ck, suite: Suite, label: str) -> dict | None:
    """A suite's install step (watch-zepp's `npm ci`), with the network."""
    if not suite.install:
        return None
    log = f"{RUNS}/{label}/{suite.name}-install.log"
    marker = f"{RUNS}/installed-{suite.package}"  # ensure_installed's record: a probe later needn't install again
    out = ck.sh(f"mkdir -p {RUNS}/{label} && cd {APP}/{suite.package} && {suite.install} > {log} 2>&1; e=$?; "
                f"[ $e -eq 0 ] && touch {marker}; echo EXIT=$e", check=False, network=True) or ""
    m = re.search(r"EXIT=(\d+)", out)
    return {"command": suite.install, "exit": int(m.group(1)) if m else None, "log_tail": (ck.get(log) or "")[-1500:]}


def rerun_flaky(ck, suite: Suite, run: dict, label: str, flaky: list[dict], reruns: int) -> dict:
    """Each failing test on the flaky list, its file run alone up to `reruns` times until it passes; it then counts as
    passed. Records every result under the test's "flaky_runs" and the run's "flaky"."""
    todo: dict[str, list[str]] = {}
    for tid, r in run["tests"].items():
        if r["status"] == "failed" and not r.get("rollup") and is_flaky(r, suite.name, flaky):
            todo.setdefault(r["file"], []).append(tid)
    record: dict[str, list[str]] = {}
    for file, tids in sorted(todo.items()):
        history = {t: ["failed"] for t in tids}
        pending = set(tids)
        for _ in range(reruns):
            if not pending:
                break
            again = run_suite(ck, suite, f"{label}-rerun-{suite.name}", files=[file])
            for t in sorted(pending):
                st = (again["tests"].get(t) or {}).get("status") or "not run"
                history[t].append(st)
                if st == "passed":
                    pending.discard(t)
        for t in tids:
            run["tests"][t]["flaky_runs"] = history[t]
            if t not in pending:
                run["tests"][t]["status"] = "passed"
            record[t] = history[t]
    run["flaky"] = record
    return run


def run_suites(ck, names: list[str], label: str, *, flaky: list[dict], reruns: int,
               out_dir: Path | None = None) -> dict[str, dict]:
    """The named suites in the checkpoint, each after its install step, with flaky failures rerun. out_dir, given, gets
    each suite's log and report as <out_dir>/<suite>.log and .json(l)."""
    ck.put(REPORTER_PATH, NODE_REPORTER)
    runs = {}
    for name in names:
        suite = SUITES[name]
        inst = install(ck, suite, label)
        run = run_suite(ck, suite, label)
        if inst is not None:
            run["install"] = inst
        run = rerun_flaky(ck, suite, run, label, flaky, reruns)
        log = run.pop("log", "")
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / f"{name}.log").write_text(log, encoding="utf-8")
            report = ck.get(f"{RUNS}/{label}/{name}{suite.report_ext}")
            if report:
                (out_dir / f"{name}{suite.report_ext}").write_text(report, encoding="utf-8")
        runs[name] = run
    return runs


def compact_run(run: dict) -> dict:
    """A run as the baseline cache keeps it: each test's file, title and status (and its marks), no messages."""
    keep = ("file", "title", "status", "rollup", "in_failed_file", "flaky_runs")
    return {"exit": run.get("exit"), "counts": run.get("counts") or {}, "file_failures": run.get("file_failures") or {},
            "flaky": run.get("flaky") or {}, "minutes": run.get("minutes"), "install": run.get("install"),
            **({"error": run["error"]} if run.get("error") else {}),
            "tests": {t: {k: r[k] for k in keep if k in r} for t, r in run["tests"].items()}}


# --------------------------------------------------------------------------------------------------- keeping


def retired_match(r: dict, retired) -> bool:
    """Whether a test is one of the retired: its file, and the line's text after "::" is its title, or starts with its
    title and then a dash and a note (a title may hold " — " itself)."""
    names = {r["title"], " > ".join([*r.get("ancestors", []), r["title"]])}
    return any(r["file"] == f and any(rest == n or rest.startswith(n + " — ") for n in names) for f, rest in retired)


def _outcome(tid: str, b: dict, frun: dict) -> tuple[str, str | None]:
    f = frun["tests"].get(tid)
    if f is None:
        return ("not loaded", (frun.get("file_failures") or {})[b["file"]]) if b["file"] in (frun.get("file_failures") or {}) \
            else ("not run", None)
    if f["status"] == "passed":
        return "passed", None
    if f["status"] == "failed":
        return "failed", (f.get("error") or {}).get("message") or ""
    if f.get("in_failed_file"):
        return "failed", f"didn't run: its file failed ({f['in_failed_file']})"
    return "not run", None


def compare_keeping(baseline: dict[str, dict], fork: dict[str, dict], *, retired=(), adjusted: dict[str, dict] | None = None,
                    touched=frozenset(), declared_pinning=frozenset()) -> dict:
    """Keeping, test by test. Each run maps a suite to a parsed run. A test counts when it passed on the start and isn't
    retired; tests in files an adjustment touches are taken from the adjusted start (`adjusted`) instead, and those
    that fail there pin the change itself: reported apart, never counted. Counted tests are passed, failed, not loaded
    (their file didn't load on the fork) or not run; only passed and failed make the share."""
    touched = set(touched)
    if touched and adjusted is None:
        raise ValueError("an adjustment needs its adjusted start")
    tally = {"counted": 0, "passed": 0, "failed": 0, "not_loaded": 0, "not_run": 0}
    failures, not_loaded, not_run = {}, {}, []
    excluded, covered, matched = [], [], set()
    adj_tests, pinning, failed_on_start = {}, {}, set()

    def count(suite: str, tid: str, b: dict, frun: dict) -> str:
        tally["counted"] += 1
        outcome, msg = _outcome(tid, b, frun)
        key = outcome.replace(" ", "_")
        tally[key] += 1
        if outcome == "failed":
            f = frun["tests"].get(tid) or {}
            failures[tid] = {"suite": suite, "file": b["file"], "title": b["title"], "message": msg or "",
                             **({"error": f["error"]} if f.get("error") else {}),
                             **({"flaky_runs": f["flaky_runs"]} if f.get("flaky_runs") else {})}
        elif outcome == "not loaded":
            e = not_loaded.setdefault(b["file"], {"error": msg, "tests": 0})
            e["tests"] += 1
        elif outcome == "not run":
            not_run.append(tid)
        return outcome

    def note_retired(r: dict) -> bool:
        hits = [(f, rest) for f, rest in retired if retired_match(r, [(f, rest)])]
        matched.update(hits)
        return bool(hits)
    for suite, brun in baseline.items():
        frun = fork.get(suite) or {"tests": {}, "file_failures": {}}
        for tid, b in brun["tests"].items():
            if b.get("rollup"):
                continue
            if b["file"] in touched:
                if note_retired(b):
                    covered.append(tid)
                continue
            if note_retired(b):
                excluded.append(tid)
                continue
            if b["status"] == "passed":
                count(suite, tid, b, frun)
    for suite, arun in (adjusted or {}).items():
        frun = fork.get(suite) or {"tests": {}, "file_failures": {}}
        for tid, a in arun["tests"].items():
            if a.get("rollup") or a["file"] not in touched:
                continue
            if a["status"] == "passed":
                adj_tests[tid] = {"start": "passed", "fork": count(suite, tid, a, frun), "counted": True}
            elif a["status"] == "failed":
                failed_on_start.add(tid)
                pinning[tid] = _outcome(tid, a, frun)[0]
                adj_tests[tid] = {"start": "failed", "fork": pinning[tid], "counted": False}
    declared = set(declared_pinning)
    passed_on_start = {t for t, x in adj_tests.items() if x["start"] == "passed"}
    shared = tally["passed"] + tally["failed"]
    return {**tally, "share_passed": tally["passed"] / shared if shared else None,
            "failures": failures, "not_loaded_files": not_loaded, "not_run_tests": sorted(not_run),
            "not_loaded_by_cause": _by_cause(not_loaded),
            "retired": {"listed": len(retired), "excluded": sorted(excluded), "covered_by_adjustment": sorted(covered),
                        "unmatched": sorted(f"{f}::{rest}" for f, rest in retired if (f, rest) not in matched)},
            "adjusted": {"touched": sorted(touched), "tests": adj_tests, "pinning": pinning,
                         "pinning_mismatch": {"declared, but passed on the start": sorted(declared & passed_on_start),
                                              "failed on the start, not declared": sorted(failed_on_start - declared)}}}


# ------------------------------------------------------------------------------------------ the graded folder

GRADED_JSON = "graded.json"


def load_graded(graded_dir: Path) -> dict:
    """The grader-owned material (seeds/opengym/hidden/m2h-graded/graded.json), frozen before any run:

    {"version": 1,
     "flaky": [{"suite": "frontend", "name": "useStore.stale-sync"}, ...],      optional; else the default list
     "flaky_reruns": 3,                                                          optional
     "adjustments": {"<n>": {"kind": "adjusted copies" | "fixture patch",
                             "patch": "<path in the folder>",                    a unified diff on the start's test files
                             "files": {"<path in the checkout>": "<path in the folder>"},   whole-file copies
                             "tests": ["<file>::<title>", ...],                  the tests it adjusts
                             "pinning": ["<file>::<title>", ...]}},              those that pin the new behaviour
     "dependency_probes": [{"id", "change", "row": "dependency" | "comparison", "suite", "file", "dest",
                            "support": {"<dest>": "<path in the folder>"}, "counts": true,
                            "adapter": {"dest", "default", "interface", "operations": [...], "forbid": [...]}}],
     "row_conditions": {"OGM-0403": "OGM-0401 implemented"}}"""
    data = json.loads((Path(graded_dir) / GRADED_JSON).read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ValueError(f"{graded_dir}/{GRADED_JSON}: version {data.get('version')!r}, expected 1")
    for e in data.get("dependency_probes") or []:
        for k in ("id", "change", "suite", "file", "dest"):
            if k not in e:
                raise ValueError(f"{graded_dir}/{GRADED_JSON}: a dependency probe without {k!r}: {e}")
        if e["suite"] not in SUITES:
            raise ValueError(f"{graded_dir}/{GRADED_JSON}: {e['id']}: unknown suite {e['suite']!r}")
        if suite_of(e["dest"]) != e["suite"]:
            raise ValueError(f"{graded_dir}/{GRADED_JSON}: {e['id']}: {e['dest']} isn't in the {e['suite']} package")
    return data


def adjustment_for(graded: dict, n: int) -> dict | None:
    return (graded.get("adjustments") or {}).get(str(n))


def _patch_paths(patch: str) -> list[str]:
    paths = re.findall(r"(?m)^\+\+\+ b/(\S+)", patch) + re.findall(r"(?m)^--- a/(\S+)", patch)
    return sorted(set(paths))


def adjustment_touched(graded_dir: Path, adj: dict) -> list[str]:
    """The test files an adjustment changes; it may touch only test files."""
    paths = set((adj.get("files") or {}).keys())
    if adj.get("patch"):
        paths |= set(_patch_paths((Path(graded_dir) / adj["patch"]).read_text(encoding="utf-8")))
    bad = sorted(p for p in paths if not is_test_path(p))
    if bad:
        raise ValueError(f"an adjustment may touch only test files, not {bad}")
    return sorted(paths)


def adjustment_key(graded_dir: Path, adj: dict) -> str:
    h = hashlib.sha256(json.dumps(adj, sort_keys=True).encode())
    for p in ([adj["patch"]] if adj.get("patch") else []) + sorted((adj.get("files") or {}).values()):
        h.update((Path(graded_dir) / p).read_bytes())
    return h.hexdigest()[:12]


def apply_adjustment(ck, graded_dir: Path, adj: dict) -> list[str]:
    """The adjustment on the checkout's test files (the start's, put back first): its patch, then its copies."""
    touched = adjustment_touched(graded_dir, adj)
    if adj.get("patch"):
        ck.put("/work/grader/adjust.patch", (Path(graded_dir) / adj["patch"]).read_text(encoding="utf-8"))
        ck.sh(f"cd {APP} && git apply --whitespace=nowarn /work/grader/adjust.patch")
    for dest, src in sorted((adj.get("files") or {}).items()):
        ck.put(f"{APP}/{dest}", (Path(graded_dir) / src).read_text(encoding="utf-8"))
    return touched


def dependency_entries(graded: dict, n: int) -> list[dict]:
    return [e for e in graded.get("dependency_probes") or [] if e["change"] == n]


# ----------------------------------------------------------------------------------------- dependency probes

ROLE = re.compile(r"^\s*(precondition|dependency|setup)(?:\[(OGM-\d{4})\])?\s*:\s*(.*)$", re.I | re.S)
SETUP_MESSAGE = re.compile(r"^\s*(?:Error:\s*|AssertionError:\s*)?(?:setup|fixture)(?:\[(OGM-\d{4})\])?\s*:\s*(.*)$", re.I)


def test_role(r: dict) -> tuple[str | None, str | None, str]:
    """(role, the row a setup step names, the rest of the title) from the test's title, else its nearest describe."""
    for name in [r["title"], *reversed(r.get("ancestors") or [])]:
        m = ROLE.match(name)
        if m:
            return m.group(1).lower(), m.group(2), m.group(3).strip()
    return None, None, r["title"]


def _first_line(s: str) -> str:
    return (str(s or "").strip().splitlines() or [""])[0]


def dependency_outcome(run: dict, *, repair_reports: dict[str, str] | None = None) -> dict:
    """One dependency probe's result from its run: kept, broken, not exercised, or missing (with a cause)."""
    tests = [t for t in run["tests"].values() if not t.get("rollup")]
    roles = [(t, *test_role(t)) for t in tests]
    listed = [{"title": test_id("", t.get("ancestors") or [], t["title"]).removeprefix("::"), "role": role,
               "status": t["status"], **({"message": _first_line((t.get("error") or {}).get("message"))} if t.get("error") else {})}
              for t, role, _, _ in roles]

    def done(result: str, **kw) -> dict:
        return {"result": result, **kw, "tests": listed}
    if not tests:
        failure = next(iter((run.get("file_failures") or {}).values()), None)
        return done("missing", cause=f"the probe's file didn't load: {failure}" if failure else
                    (run.get("error") or "no test results")[:500])

    def setup_failed(postcondition: str, row: str | None) -> dict:
        return done("missing", cause="a setup step failed",
                    failed_setup={"postcondition": postcondition, "row": row,
                                  "repair_report": (repair_reports or {}).get(row) if row else None})
    for t, role, row, text in roles:
        if t["status"] != "failed":
            continue
        if role == "setup":
            return setup_failed(text, row)
        m = SETUP_MESSAGE.match(_first_line((t.get("error") or {}).get("message")))
        if m:
            return setup_failed(m.group(2).strip(), m.group(1))
    pre = [t for t, role, _, _ in roles if role == "precondition"]
    dep = [t for t, role, _, _ in roles if role == "dependency"]
    witness = {"dependency_passed": all(t["status"] == "passed" for t in dep) if dep else None}
    if not pre:
        return done("missing", cause="no precondition test")
    if any(t["status"] == "failed" for t in pre):
        return done("not exercised", witness=witness)
    if not all(t["status"] == "passed" for t in pre):
        return done("missing", cause="a precondition test didn't run")
    if not dep:
        return done("missing", cause="no dependency test")
    if any(t["status"] == "failed" for t in dep):
        return done("broken")
    if all(t["status"] == "passed" for t in dep):
        return done("kept")
    return done("missing", cause="a dependency test didn't run")


NOT_LOADED_CAUSES = (("missing export", r"does not provide an export named|is not exported|has no exported member"),
                     ("missing module", r"Cannot find (module|package)|ERR_MODULE_NOT_FOUND"),
                     ("syntax error", r"SyntaxError"), ("reference error", r"ReferenceError|is not defined"),
                     ("type error", r"TypeError"))


def not_loaded_cause(message: str) -> str:
    """Why a test file didn't load on the fork, as M2f counts tests not built by cause."""
    for cause, pattern in NOT_LOADED_CAUSES:
        if re.search(pattern, message or ""):
            return cause
    return "other"


def _by_cause(not_loaded: dict) -> dict[str, int]:
    out: dict[str, int] = {}
    for e in not_loaded.values():
        c = not_loaded_cause(e.get("error") or "")
        out[c] = out.get(c, 0) + (e.get("tests") or 0)
    return out


def dependency_rollup(results: dict[str, dict], counting: list[str]) -> dict:
    """A change's dependent behaviour over its counting probes: broken if any is broken, else missing if any is missing,
    kept if all are kept, else not exercised (a mix of kept and not exercised is never kept)."""
    rs = [results[i]["result"] for i in counting if i in results]
    if not rs:
        return {"result": "missing", "cause": "no counting probe ran"}
    for r in ("broken", "missing"):
        if r in rs:
            return {"result": r}
    if all(r == "kept" for r in rs):
        return {"result": "kept"}
    return {"result": "not exercised", **({"mixed": True} if "kept" in rs else {})}


ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def probe_notes(log: str) -> dict[str, str]:
    """`NOTE <key>: <value>` lines a probe printed (a build's storage choice, say), colour codes aside."""
    return {m.group(1).strip(): m.group(2).strip()
            for m in re.finditer(r"(?m)^\s*NOTE ([^:\n]{1,40}):\s*(.*?)\s*$", ANSI.sub("", log or ""))}


def ensure_installed(ck, paths: list[str]) -> None:
    """Each package these paths reach whose suite installs first (watch-zepp: npm ci, with the network), installed if
    no earlier step on this checkout has (a marker under the run folder records it)."""
    for package in sorted({p.split("/", 1)[0] for p in paths}):
        suite = next((x for x in SUITES.values() if x.package == package and x.install), None)
        if suite is None:
            continue
        marker = f"{RUNS}/installed-{package}"
        ck.sh(f"mkdir -p {RUNS} && (test -f {marker} || (cd {APP}/{package} && {suite.install} > {RUNS}/install-{package}.log "
              f"2>&1 && touch {marker}))", check=False, network=True)


def run_dependency_probe(ck, entry: dict, graded_dir: Path, *, repair_reports: dict[str, str] | None = None,
                         out: Path | None = None) -> dict:
    """Put a probe (and its support files) in its package, run it alone, and read its result. A package the probe's
    files reach whose suite has an install step (watch-zepp's npm ci) is installed first, once per checkout."""
    ensure_installed(ck, [entry["dest"], *(entry.get("support") or {})])
    ck.put(f"{APP}/{entry['dest']}", (Path(graded_dir) / entry["file"]).read_text(encoding="utf-8"))
    for dest, src in sorted((entry.get("support") or {}).items()):
        ck.put(f"{APP}/{dest}", (Path(graded_dir) / src).read_text(encoding="utf-8"))
    suite = SUITES[entry["suite"]]
    ck.put(REPORTER_PATH, NODE_REPORTER)
    run = run_suite(ck, suite, f"dep-{entry['id']}", files=[entry["dest"]])
    log = run.pop("log", "")
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{entry['id']}.log").write_text(log, encoding="utf-8")
    result = dependency_outcome(run, repair_reports=repair_reports)
    result["notes"] = probe_notes(log)
    # the probe's checks leave the checkout: no later grader (another probe's adapter, the extraction) reads them
    placed = [entry["dest"], *(entry.get("support") or {}), *([entry["adapter"]["dest"]] if entry.get("adapter") else [])]
    ck.sh(f"cd {APP} && rm -f " + " ".join(f"'{p}'" for p in placed), check=False)
    return result


# ------------------------------------------------------------------------------------------------- adapters


def absent_module(reason: str) -> str:
    return ("// Written by the grader: this build has nothing that provides the adapter's functions.\n"
            f"export const available = false\nexport const reason = {json.dumps(reason)}\n")


def adapter_prompt(entry: dict, graded_dir: Path) -> str:
    a = entry["adapter"]
    d = Path(graded_dir)
    default = (d / a["default"]).read_text(encoding="utf-8") if a.get("default") else "// (none)\n"
    ops = "\n".join(f"- {o}" for o in a.get("operations") or []) or "- (none listed)"
    return grading._template("dependency-adapter-node.md", INTERFACE=(d / a["interface"]).read_text(encoding="utf-8").strip(),
                             OPERATIONS=ops, DEFAULT=default.rstrip(), ID=entry["id"], DEST=a["dest"])


ADAPTER_STATUSES = ("adapted", "absent", "unclear")


def check_adapter(raw: str | None, source: str | None, forbid: list[str]) -> tuple[str, list[str], dict]:
    """The adapter writer's record and module: ("adapted" | "absent" | "unusable", problems, record)."""
    try:
        record = json.loads(raw) if raw else None
    except ValueError:
        record = None
    if not isinstance(record, dict):
        return "unusable", ["no adapter record"], {}
    status = record.get("status")
    if status not in ADAPTER_STATUSES:
        return "unusable", [f"status {status!r}"], record
    if status == "unclear":
        return "unusable", ["the adapter writer couldn't tell"], record
    if status == "absent":
        return "absent", [], record
    problems = []
    if not (source or "").strip():
        problems.append("adapted, but no module")
    if not [e for e in record.get("evidence") or [] if isinstance(e, dict) and e.get("file")]:
        problems.append("adapted, but cites nothing")
    for pat in forbid or []:
        if source and re.search(pat, source):
            problems.append(f"uses a forbidden operation: {pat}")
    return ("unusable" if problems else "adapted"), problems, record


def adapt(ck, g: "NodeGraders | None", entry: dict, graded_dir: Path, *, run_role: Callable | None,
          out: Path | None = None) -> dict | None:
    """Put the probe's adapter in place. With no adapter step (g None), the pin's adapter; else a model, blind to the
    arm (the code-only checkout, a neutral prompt), writes one for this build from the frozen interface and permitted
    operations, keeping the pin's where the build still fits it. Returns the status: default, adapted, absent (the
    grader's own module saying so), or unusable (the probe is then missing)."""
    a = entry.get("adapter")
    if not a:
        return None
    dest = f"{APP}/{a['dest']}"
    d = Path(graded_dir)
    if g is None:
        if not a.get("default"):
            return {"status": "unusable", "problems": ["no adapter step and no default adapter"]}
        ck.put(dest, (d / a["default"]).read_text(encoding="utf-8"))
        return {"status": "default", "problems": []}
    prompt = adapter_prompt(entry, d)
    ck.sh(f"mkdir -p /work/out/adapters && rm -f /work/out/adapters/{entry['id']}.*", check=False)
    session: dict = {}
    try:
        rec = run_role(g.role(g.adapter_model, tools=("Bash", "Read", "Write", "Edit", "Glob", "Grep"),
                              workspace_volume=ck.volume, timeout_s=2400), prompt)
        session = {"usage": _usage(rec), "reply": rec.text}
    except executor.RoleFailed as e:
        session = {"error": str(e)}
    raw, source = ck.get(f"/work/out/adapters/{entry['id']}.json"), ck.get(f"/work/out/adapters/{entry['id']}.js")
    status, problems, record = check_adapter(raw, source, a.get("forbid") or [])
    if status == "adapted":
        ck.put(dest, source)
    elif status == "absent":
        ck.put(dest, absent_module(record.get("note") or "absent"))
    result = {"status": status, "problems": problems, "record": record, "notes": record.get("notes") or {}, "session": session}
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{entry['id']}.adapter.json").write_text(json.dumps({**result, "prompt": prompt}, indent=1), encoding="utf-8")
        if source:
            (out / f"{entry['id']}.adapter.js").write_text(source, encoding="utf-8")
    return result


def grade_dependency(ck, g, entries: list[dict], graded_dir: Path, change: ChangeInfo | None, *, run_role: Callable | None,
                     out: Path | None = None) -> dict:
    """Every dependency probe (or comparison row) of the change, adapted and run, and the change's roll-up over those
    that count (a probe with "counts": false is a kept-row extra, recorded but not in the rate)."""
    probes: dict[str, dict] = {}
    for e in entries:
        ad = adapt(ck, g, e, graded_dir, run_role=run_role, out=out)
        if ad is not None and ad["status"] == "unusable":
            probes[e["id"]] = {"result": "missing", "cause": "adapter: " + "; ".join(ad["problems"]), "adapter": ad["status"]}
            continue
        r = run_dependency_probe(ck, e, graded_dir, repair_reports=change.repair_reports if change else None, out=out)
        if ad is not None:
            r["adapter"] = ad["status"]
            r["notes"] = {**(ad.get("notes") or {}), **r.get("notes", {})}
        r["counts"] = e.get("counts", True)
        probes[e["id"]] = r
    counting = [e["id"] for e in entries if e.get("counts", True)]
    row = (entries[0].get("row") if entries else None) or ("comparison" if change and change.type == "control" else "dependency")
    roll = dependency_rollup(probes, counting) if entries else {
        "result": "missing", "cause": f"no dependency probes for change {change.number if change else '?'}"}
    return {**roll, "row": row,
            "exercised_only_if": (change.exercised_only_if or change.comparison_row) if change else None,
            "probes": probes, "counting": counting,
            "notes": {k: v for p in probes.values() for k, v in (p.get("notes") or {}).items()},
            "failed_setups": [{"probe": i, **p["failed_setup"]} for i, p in probes.items() if p.get("failed_setup")]}


# --------------------------------------------------------------------------------------------- new-row probes

NEEDS = {
    "fe": {"package": "frontend", "runner": "vitest", "dir": "frontend/src/__probes__", "ext": ".test.jsx", "suite": "frontend"},
    "zepp": {"package": "watch-zepp", "runner": "node-test", "dir": "watch-zepp/test/__probes__", "ext": ".test.js", "suite": "zepp"},
    "api": {"package": "api", "runner": "node-test", "dir": "api/test/__probes__", "ext": ".test.js", "suite": "api"},
    "mcp": {"package": "mcp", "runner": "vitest", "dir": "mcp/test/__probes__", "ext": ".test.js", "suite": "mcp"},
}
ALIASES = {"web": "fe", "web app": "fe", "frontend": "fe", "app": "fe", "page": "fe", "browser": "fe", "phone": "fe",
           "server": "api", "watch": "zepp", "watch-zepp": "zepp", "zepp watch": "zepp"}
PRIORITY = ("fe", "zepp", "api", "mcp")  # a probe across parts runs where the richest of them lives
EDITS_PART_NEED = {"api": "api", "frontend": "fe", "watch-zepp": "zepp", "mcp": "mcp"}
PACKAGE_NOTES = {
    "api": "the API (`api/`): node's own test runner; a test starts `server.js` as a child process on a data folder "
           "of its own",
    "frontend": "the web app (`frontend/`): vitest, with happy-dom for anything that renders (a first line "
                "`// @vitest-environment happy-dom`, as the project's own tests have)",
    "watch-zepp": "the Zepp watch app (`watch-zepp/`): node's own test runner, with the page loaded against the "
                  "project's stand-ins for the Zepp OS modules",
    "mcp": "the MCP bridge (`mcp/`): vitest",
}
HELPERS = {
    "api": "`api/test/helpers.mjs` (starting `server.js` and the port it bound), `api/test/fake-clock.mjs`, "
           "`api/test/soft-passkey.mjs` (a software authenticator), `api/test/mock-oidc.mjs`",
    "frontend": "`frontend/src/test-setup.js` (run before every test file), React's `act` and `createRoot` as the "
                "project's own view tests use them, vitest's fake timers",
    "watch-zepp": "`watch-zepp/test/fakes/zos.js` (the stand-ins), loaded the way `watch-zepp/test/page.test.js` "
                  "bundles a page with esbuild",
    "mcp": "the project's own tests in `mcp/test/` show how the bridge is driven",
}


def route(needs, edits_part: str) -> dict:
    """Where a probe's test lives and how it runs, from its Needs: fe (the web app, vitest with happy-dom), api
    (`node --test`, with a server.js child), zepp (the watch page against its stand-ins), mcp; aliases accepted. A probe
    across parts runs in the first of fe, zepp, api, mcp it needs; one that needs nothing, in the change's edited part."""
    keys = []
    for n in needs or ():
        k = n.strip().lower()
        k = ALIASES.get(k, k)
        if k not in NEEDS:
            raise ValueError(f"unknown need {n!r}: expected one of {sorted(NEEDS)} (or {sorted(ALIASES)})")
        keys.append(k)
    if not keys:
        keys = [EDITS_PART_NEED.get(edits_part, "api")]
    need = next(k for k in PRIORITY if k in keys)
    return {"need": need, "needs": keys, **NEEDS[need]}


def probe_stem(pid: str) -> str:
    return rg.probe_target(pid)


def probe_path(pid: str, r: dict) -> str:
    return f"{r['dir']}/{probe_stem(pid)}{r['ext']}"


def probe_ext(path: str) -> str:
    base = path.rsplit("/", 1)[-1]
    return base[base.index(".test."):] if ".test." in base else Path(base).suffix


def run_command(r: dict, path: str, timeout: int | None = None) -> str:
    rel = path.removeprefix(r["package"] + "/")
    lead = "NO_COLOR=1 " + (f"timeout {timeout} " if timeout else "")
    if r["runner"] == "vitest":
        return f"cd {APP}/{r['package']} && {lead}npx vitest run --reporter=verbose {rel}"
    return f"cd {APP}/{r['package']} && {lead}node --test --test-reporter=spec {rel}"


def probe_options(text: str) -> dict[str, dict]:
    """Each probe's optional fields: "Runs only if" (a condition on other rows, checked before it runs) and "Exercised
    only if" (a precondition the judge reads from its output)."""
    _, _, probes_text = text.partition("\n## Probes")
    out = {}
    for block in re.split(r"(?m)^(?=#### )", probes_text):
        if not block.startswith("#### "):
            continue
        pid, _, body = block[5:].partition("\n")

        def opt(name: str) -> str | None:
            m = re.search(rf"(?m)^- \*\*{re.escape(name)}:\*\*\s*(.+?)\s*$", body)
            return m.group(1) if m else None
        out[pid.strip()] = {"runs_only_if": opt("Runs only if"),
                            "exercised_only_if": opt("Exercised only if") or opt("Precondition")}  # either name
    return out


def condition_holds(cond: str, statuses: dict[str, str], verdicts: dict[str, str | None]) -> bool | None:
    """A condition like "OGM-0401 implemented" or "OGM-0401 met and OGM-0402 implemented": implemented from the
    extraction (implemented or inherited), met from that row's verdict. None when it can't be told."""
    vals = []
    for part in re.split(r"\s+and\s+", cond.strip()):
        m = re.fullmatch(r"(OGM-\d{4})\s+(implemented|met)", part.strip())
        if not m:
            raise ValueError(f"can't read the condition {cond!r}: expected '<row> implemented' or '<row> met', joined by 'and'")
        row, kind = m.groups()
        if kind == "implemented":
            st = statuses.get(row)
            vals.append(True if st in ("implemented", "inherited") else False if st == "absent" else None)
        else:
            v = verdicts.get(row)
            vals.append(True if v == "met" else None if v in (None, grading.MISSING, grading.CONFLICT, "blocked") else False)
    return False if False in vals else None if None in vals else True


@dataclass(frozen=True)
class NodeGraders:
    image: str
    roles_volume: str
    claude_code: str
    extraction_model: str = "claude-sonnet-5-5"
    execute_model: str = "claude-haiku-5-5"
    judge_model: str = "claude-sonnet-5-5"
    adapter_model: str = "claude-sonnet-5-5"
    effort: str = "medium"

    def role(self, model: str, **kw) -> executor.RoleSession:
        # graders reach npm but not the subject's public repository, like the arms
        return executor.RoleSession(image=self.image, config_volume=self.roles_volume, model=model,
                                    claude_code_version=self.claude_code, effort=self.effort,
                                    isolation=executor.Isolation.for_public_seed(window="1m"), **kw)


def _usage(rec) -> dict:
    return {"cost_usd": rec.usage.reported_cost_usd, "duration_s": round(rec.duration_s, 1),
            "models": {m: (asdict(c) if hasattr(c, "__dataclass_fields__") else c) for m, c in (rec.usage.models or {}).items()}}


def _packages_note(packages) -> str:
    lines = []
    for pkg in [n["package"] for n in NEEDS.values() if n["package"] in set(packages)]:
        n = next(v for v in NEEDS.values() if v["package"] == pkg)
        lines.append(f"   - {PACKAGE_NOTES[pkg]}. Tests go in `/work/app/{n['dir']}/`, run as "
                     f"`{run_command(n, n['dir'] + '/<file>' + n['ext'])}`.")
    return "\n".join(lines)


def extraction_prompt(items: list[tuple[str, str]], packages) -> str:
    note = ""
    if items:
        note = ("5. For each item below, record whether the build provides it and how, in "
                "/work/out/implementation.json: `{\"items\": [{\"item\": \"<ID>\", \"status\": \"implemented\" | "
                "\"inherited\" | \"absent\" | \"unclear\", \"evidence\": [{\"file\": \"<path>\", \"symbols\": "
                "[\"<function, component, route, or key>\"]}], \"note\": \"<one sentence>\"}]}`, one entry per item.\n"
                "   - implemented: the diff adds or changes code that does something toward the item; cite the files "
                "and symbols.\n"
                "   - inherited: the build has the behaviour through code the diff didn't need to touch: existing code "
                "the change relies on, or that already did this; cite the code that provides it.\n"
                "   - absent: the behaviour isn't produced: nothing in the diff addresses it and no existing code "
                "provides it; cite the files and symbols you checked.\n"
                "   - unclear: you can't tell.\n\n"
                "   This record is separate from the reference: don't mention the items in reference.md.\n\n"
                "   The items:\n" + "\n".join(f"   - {i}: {text}" for i, text in items) + "\n\n")
    return grading._template("extraction-node.md", PACKAGES=_packages_note(packages), ITEMS=note)


def _routes_note(routes: dict[str, dict]) -> str:
    return "\n".join(f"- {pid}: `/work/app/{probe_path(pid, r)}`, run with `{run_command(r, probe_path(pid, r))}`"
                     for pid, r in routes.items())


def execution_prompt(bid: str, routes: dict[str, dict]) -> str:
    pkgs = sorted({r["package"] for r in routes.values()})
    helpers = ("The project's own test helpers are there for building setups; use them where they fit (the reference "
               "says how to call the project):\n" + "\n".join(f"- {HELPERS[p]}" for p in pkgs) + "\n\n") if pkgs else ""
    return grading._template("grade-execute-node.md", BATCH=bid, HELPERS=helpers, ROUTES=_routes_note(routes))


def render_for_execution(batch: list, conventions: str, setups: dict[str, str], options: dict[str, dict]) -> str:
    """The probes as the executor sees them: conventions, setups in full, each scenario and its precondition line, never
    an expected observation."""
    head = f"## Conventions for every probe\n\n{conventions.strip()}\n\n" if conventions.strip() else ""
    used = grading.setups_used(batch, setups or {})
    if used:
        head += "## Setups these probes use\n\n" + "\n\n".join(setups[s] for s in used) + "\n\n"
    parts = []
    for p in batch:
        pre = (options.get(p.id) or {}).get("exercised_only_if")
        parts.append(f"## {p.id}\n\n- **Setup:** {p.setup}\n- **Needs:** {', '.join(p.needs) or 'none'}\n"
                     + (f"- **Exercised only if:** {pre}\n" if pre else "") + f"- **Scenario:**\n{p.scenario}")
    return head + "\n\n".join(parts)


def render_for_judgment(batch: list, conventions: str, options: dict[str, dict]) -> str:
    head = f"## Conventions for every probe\n\n{conventions.strip()}\n\n" if conventions.strip() else ""
    parts = []
    for p in batch:
        pre = (options.get(p.id) or {}).get("exercised_only_if")
        parts.append(f"## {p.id}\n\n- **Setup:** {p.setup}\n" + (f"- **Exercised only if:** {pre}\n" if pre else "")
                     + f"- **Scenario:**\n{p.scenario}\n- **Expected observation:** {p.expected}")
    return head + "\n\n".join(parts)


FAULTS = rg.FAULTS
VERDICTS = ("met", "not met", "couldn't exercise", "not exercised")
JUDGE_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["verdicts"],
    "properties": {"verdicts": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["probe", "verdict", "evidence", "reason", "cause", "fault", "failed_postcondition", "postcondition_row"],
        "properties": {"probe": {"type": "string"}, "verdict": {"type": "string", "enum": list(VERDICTS)},
                       "evidence": {"type": "array", "items": {"type": "integer"}}, "reason": {"type": "string"},
                       "cause": {"type": "string", "enum": ["execution", "none"]},
                       "fault": {"type": "string", "enum": [*FAULTS, "none"]},
                       "failed_postcondition": {"type": "string"}, "postcondition_row": {"type": "string"}}}}},
}


def check_verdicts(result: dict, batch: list, lines: list[dict], options: dict[str, dict]) -> list[str]:
    """The other seeds' checks; a grader error names its fault and nothing else does; "not exercised" only where the
    probe has a precondition line."""
    problems = grading.check_verdicts(result, batch, lines)
    for v in result.get("verdicts", []):
        pid, verdict, fault = v.get("probe"), v.get("verdict"), v.get("fault") or "none"
        if verdict == "couldn't exercise" and (v.get("cause") != "execution" or fault not in FAULTS):
            problems.append(f"{pid}: \"couldn't exercise\" without naming the grader's fault")
        elif verdict in ("met", "not met", "not exercised") and fault != "none":
            problems.append(f"{pid}: a {verdict!r} verdict naming a grader fault")
        if verdict == "not exercised" and not (options.get(pid) or {}).get("exercised_only_if"):
            problems.append(f"{pid}: \"not exercised\" for a probe with no precondition line")
    return problems


def judge_prompt(batch: list, lines: list[dict], conventions: str, options: dict[str, dict], rows: list[Row]) -> str:
    return grading._template("grade-judge-node.md", PROBES=render_for_judgment(batch, conventions, options),
                             LOG=rg.log_for_judge(lines),
                             ROWS="\n".join(f"- {r.id}: {r.behaviour}" for r in rows) or "(none)")


def _rerun_script(pid: str, r: dict) -> str:
    path, stem = probe_path(pid, r), probe_stem(pid)
    ext = probe_ext(path)
    return (f"mkdir -p /work/out/probes; f={APP}/{path}; if [ -f \"$f\" ]; then cp \"$f\" /work/out/probes/{stem}{ext}; "
            f"( {run_command(r, path, PROBE_TIMEOUT)} ) "
            f"> /work/out/probes/{stem}.log 2>&1; echo \"EXIT=$?\" >> /work/out/probes/{stem}.log; fi; true")


def _judge_batch(ck, g: NodeGraders, batch: list, bid: str, out: Path, *, volume: str, conventions: str, setups: dict,
                 options: dict, routes: dict, rows: list[Row], run_role: Callable, attempts: int, sessions: dict) -> dict:
    bdir = out / bid
    bdir.mkdir(parents=True, exist_ok=True)
    rendered = render_for_execution(batch, conventions, setups, options)
    ck.put(f"/work/out/probes-{bid}.md", rendered)
    (bdir / "probes.md").write_text(rendered, encoding="utf-8")
    broutes = {p.id: routes[p.id] for p in batch}
    try:
        rec = run_role(g.role(g.execute_model, tools=("Bash", "Read", "Write", "Edit"), workspace_volume=volume,
                              timeout_s=2400), execution_prompt(bid, broutes))
        sessions[bid] = {"usage": _usage(rec), "reply": rec.text}
    except executor.RoleFailed as e:
        sessions[bid] = {"error": str(e)}
    results = {}
    for p in batch:
        r = routes[p.id]
        stem, ext = probe_stem(p.id), probe_ext(probe_path(p.id, r))
        ck.sh(_rerun_script(p.id, r), check=False)
        results[p.id] = {"source": ck.get(f"/work/out/probes/{stem}{ext}"), "output": ck.get(f"/work/out/probes/{stem}.log")}
        for kind, suffix in (("source", ext), ("output", ".log")):
            if results[p.id][kind] is not None:
                (bdir / f"{stem}{suffix}").write_text(results[p.id][kind], encoding="utf-8")
    lines = rg.probe_log_lines(results)
    tries = []
    for _ in range(attempts):
        rec = run_role(g.role(g.judge_model, timeout_s=1200), judge_prompt(batch, lines, conventions, options, rows),
                       json_schema=json.dumps(JUDGE_SCHEMA, separators=(",", ":")))
        problems = check_verdicts(rec.structured or {}, batch, lines, options)
        tries.append({"structured": rec.structured, "problems": problems, "usage": _usage(rec)})
        if not problems:
            break
    final = {pid: {**v, "batch": bid} for pid, v in
             keep_valid((tries[-1]["structured"] or {}).get("verdicts", []), tries[-1]["problems"]).items()}
    (bdir / "judgment.json").write_text(json.dumps({"tries": tries, "verdicts": final, "lines": lines}, indent=1),
                                       encoding="utf-8")
    return final


def keep_valid(verdicts: list[dict], problems: list[str]) -> dict[str, dict]:
    """The verdicts of a judgment's last try that no problem names: a problem naming one probe ("P-…: …") drops that
    probe's verdict only, so it reruns as a grader error; a problem naming none drops them all."""
    named = set()
    for p in problems:
        m = re.match(r"(P-[\w-]+):", p)
        if not m:
            return {}
        named.add(m.group(1))
    return {v["probe"]: v for v in verdicts if v.get("probe") and v["probe"] not in named}


def batches_by_package(probes: list, routes: dict[str, dict], size: int) -> list[list]:
    """Batches of at most `size`, each in one package, in the probes' order."""
    groups: dict[str, list] = {}
    for p in probes:
        groups.setdefault(routes[p.id]["package"], []).append(p)
    out = []
    for ps in groups.values():
        out += grading.batches(ps, size)
    return out


def _item_id(p) -> str:
    return p.item.split()[0]


def grade_probes(ck, g: NodeGraders, probeset: grading.ProbeSet, probes: list, *, change: ChangeInfo, out: Path, volume: str,
                 batch_size: int = 4, run_role: Callable = executor.run_role, attempts: int = 3, guards=frozenset(),
                 conditions: dict[str, str] | None = None, options: dict[str, dict] | None = None) -> dict:
    """Extraction, then batches of execution, the harness's own run of each probe's test, and judgment, as M2f's
    rust_grading.grade_probes, with M2h's additions (see the module's docstring): routing by Needs, "Runs only if"
    conditions (the probe's own, or its row's in `conditions`), "not exercised", and setups blocked by another row."""
    out.mkdir(parents=True, exist_ok=True)
    options = options or {}
    conditions = conditions or {}
    routes = {p.id: route(p.needs, change.edits_part) for p in probes}
    rows = {r.id: r for r in change.rows}
    item_ids = sorted({_item_id(p) for p in probes})
    items = [(i, rows[i].behaviour if i in rows else next(p.item for p in probes if _item_id(p) == i)) for i in item_ids]
    rec = run_role(g.role(g.extraction_model, tools=("Bash", "Read", "Write", "Edit", "Glob", "Grep"),
                          workspace_volume=volume, timeout_s=2400),
                   extraction_prompt(items, {r["package"] for r in routes.values()}))
    reference = ck.get("/work/out/reference.md") or ""
    (out / "reference.md").write_text(reference, encoding="utf-8")
    sessions = {"extraction": {"usage": _usage(rec), "problems": [] if reference.strip() else ["no reference"]}}
    raw = ck.get("/work/out/implementation.json")
    try:
        data = json.loads(raw) if raw else None
    except ValueError:
        data = None
    statuses, problems = rg.check_implementation(data, item_ids)
    records = {e.get("item"): e for e in (data or {}).get("items") or [] if isinstance(e, dict)} if isinstance(data, dict) else {}
    (out / "implementation.json").write_text(json.dumps({"statuses": statuses, "problems": problems, "record": data},
                                                        indent=1), encoding="utf-8")
    ck.sh("rm -f /work/out/implementation.json", check=False)  # the executors never read the items
    sessions["extraction"]["implementation_problems"] = problems
    kw = dict(volume=volume, conventions=probeset.setup_notes, setups=probeset.setups, options=options, routes=routes,
              rows=change.rows, run_role=run_role, attempts=attempts, sessions=sessions)

    def cond_of(p) -> str | None:
        return (options.get(p.id) or {}).get("runs_only_if") or conditions.get(_item_id(p))
    verdicts: dict[str, dict] = {}
    cond_record: dict[str, dict] = {}
    first = [p for p in probes if not cond_of(p) or " met" not in f" {cond_of(p)}"]
    later = [p for p in probes if p not in first]
    k = 0
    for phase in (first, later):
        run = []
        decided = {i.split()[0]: v["verdict"] for i, v in item_verdicts({pid: v["verdict"] for pid, v in verdicts.items()},
                                                                        [p for p in probes if p.id in verdicts]).items()}
        for p in phase:
            c = cond_of(p)
            if c:
                holds = condition_holds(c, statuses, decided)
                cond_record[p.id] = {"condition": c, "holds": holds}
                if holds is False:
                    verdicts[p.id] = {"probe": p.id, "verdict": "not exercised", "by": "harness",
                                      "reason": f"the condition doesn't hold on this build: {c}"}
                    continue
            run.append(p)
        for batch in batches_by_package(run, routes, batch_size):
            k += 1
            verdicts.update(_judge_batch(ck, g, batch, f"b{k:02d}", out, **kw))
    faults = grading.execution_faults(verdicts)
    by_id = {p.id: p for p in probes}
    reruns, missing, absent, failed_setups = {}, {}, {}, []
    for n, pid in enumerate(faults, start=1):
        r = routes[pid]
        ck.sh(f"rm -f {APP}/{probe_path(pid, r)} /work/out/probes/{probe_stem(pid)}.*", check=False)
        second = _judge_batch(ck, g, [by_id[pid]], f"x{n:02d}", out, **kw).get(pid)
        reruns[pid] = {"first": verdicts[pid], "second": second}
        if second is None or second.get("verdict") == "couldn't exercise":
            last = second or verdicts[pid]
            item = _item_id(by_id[pid])
            post, prow = (last.get("failed_postcondition") or "").strip(), (last.get("postcondition_row") or "none").strip()
            if last.get("fault") == "fixture" and post and prow in rows and prow != item:
                verdicts[pid] = {**last, "verdict": "blocked", "blocked_by": prow}
                failed_setups.append({"probe": pid, "item": item, "postcondition": post, "blocked_by": prow,
                                      "repair_report": change.repair_reports.get(prow)})
                continue
            if last.get("fault") == "interface" and statuses.get(item) == "absent":
                verdicts[pid] = {**last, "verdict": "not met", "absent": True}
                absent[pid] = {"fault": "interface", "reason": last.get("reason"), "implementation": "absent"}
                continue
            verdicts[pid] = {**last, "verdict": grading.MISSING}
            f1 = reruns[pid]["first"]
            missing[pid] = {"cause": "execution", "fault": last.get("fault"), "reason": last.get("reason"),
                            "first": {"fault": f1.get("fault"), "reason": f1.get("reason")}}
            if post:
                failed_setups.append({"probe": pid, "item": item, "postcondition": post, "blocked_by": None,
                                      "repair_report": None})
        else:
            verdicts[pid] = second
    conflicts: dict[str, dict] = {}
    guard_exempt: list[str] = []
    for pid, v in verdicts.items():
        item = _item_id(by_id[pid])
        if v.get("verdict") == "met" and statuses.get(item) == "absent":
            if item in guards:
                guard_exempt.append(pid)
                continue
            verdicts[pid] = {**v, "verdict": grading.CONFLICT}
            c = conflicts.setdefault(by_id[pid].item, {"probes": {}, "extraction": records.get(item)})
            c["probes"][pid] = {"verdict": "met", "reason": v.get("reason"), "evidence": v.get("evidence"), "batch": v.get("batch")}
    probe_verdicts = {pid: verdicts[pid]["verdict"] for pid in [p.id for p in probes] if pid in verdicts}
    by_fault: dict[str, int] = {}
    for m in missing.values():
        by_fault[m["fault"] or "unknown"] = by_fault.get(m["fault"] or "unknown", 0) + 1
    item_of = {p.id: p.item for p in probes}
    result = {"probes": probe_verdicts, "items": item_verdicts(probe_verdicts, probes), "details": verdicts,
              "sessions": sessions, "execution_faults": faults, "reruns": reruns, "missing": missing,
              "missing_by_fault": by_fault, "absent": absent,
              "interface_faults": {"not met (absent)": sorted({item_of[p] for p in absent}),
                                   "missing": sorted({item_of[p] for p, m in missing.items() if m["fault"] == "interface"})},
              "implementation": statuses, "conflicts": conflicts, "guard_exempt": sorted(guard_exempt),
              "conditions": cond_record, "failed_setups": failed_setups,
              "routes": {pid: probe_path(pid, r) for pid, r in routes.items()}}
    (out / "verdicts.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    return result


# ----------------------------------------------------------------------------------------- what is counted

RANK = ("not met", "not exercised", "couldn't exercise", "blocked", grading.CONFLICT, grading.MISSING)


def item_verdicts(probe_verdicts: dict[str, str], probes: list) -> dict[str, dict]:
    """As grading.item_verdicts, with M2h's verdicts: not met, then not exercised, couldn't exercise, blocked, a
    conflict, missing; met only when every probe is met."""
    by_item: dict[str, list] = {}
    for p in probes:
        by_item.setdefault(p.item, []).append(p)
    out = {}
    for item, ps in by_item.items():
        vs = [probe_verdicts.get(p.id) for p in ps]
        given = [v for v in vs if v]
        v = next((r for r in RANK if r in given), None)
        if v is None:
            v = "met" if given and len(given) == len(vs) else None
        out[item] = {"verdict": v, "probes": {p.id: probe_verdicts.get(p.id) for p in ps},
                     "share_met": sum(x == "met" for x in given) / len(ps)}
    return out


UNDECIDED = (grading.MISSING, grading.CONFLICT, "blocked", "not exercised")


def items_met(items: dict[str, str | None], interface: dict[str, list[str]] | None = None) -> dict:
    """Items met of those decided on the build; missing, conflicts, blocked and not exercised counted apart."""
    decided = [v for v in items.values() if v and v not in UNDECIDED]
    vals = list(items.values())
    return {"met": sum(v == "met" for v in decided), "of": len(decided),
            "missing": vals.count(grading.MISSING), "conflicts": vals.count(grading.CONFLICT),
            "blocked": vals.count("blocked"), "not_exercised": vals.count("not exercised"),
            "interface_faults": {k: sum(i in items for i in (interface or {}).get(k, []))
                                 for k in ("not met (absent)", "missing")}}


def items_met_by_kind(items: dict[str, str | None], interface: dict[str, list[str]] | None = None, *, guards=frozenset()) -> dict:
    key = lambda i: i.split()[0]  # noqa: E731
    new = {i: v for i, v in items.items() if key(i) not in guards}
    guard = {i: v for i, v in items.items() if key(i) in guards}
    return {"new_rows_met": items_met(new, interface), "guard_rows_met": items_met(guard, interface),
            "guard_rows": sorted(guard)}


# ---------------------------------------------------------------------------------------------- joint outcome

# The plan's change-specific notes (m2h-plan.md, "Joint outcome"; m2h-harness-needs.md, "The joint-outcome report"):
# - change 3: a watch-only build fails OGM-0301, OGM-0302 and the dependency for one fault; its new-row score without
#   them is N/A (implemented_without_coupled);
# - change 4: OGM-0405 sits beside the dependency rate, not in the new-row score; each build's storage choice is
#   recorded (a probe's or adapter's `storage` note) and new-key builds are reported apart;
# - change 6: only the pairing sheet counts toward the dependency rate (the graded manifest's "counts").
JOINT_RULES: dict[int, dict] = {
    3: {"coupled_with_dependency": ["OGM-0301", "OGM-0302"]},
    4: {"beside_dependency": ["OGM-0405"], "excluded": ["OGM-0405"], "notes": ["storage"]},
}


def implemented(change: ChangeInfo, verdicts: dict[str, str | None], *, guards=frozenset(), excluded=frozenset()) -> dict:
    """Implemented: yes when every stated non-guard new row is met, partly when some are, no when none is; N/A when the
    change has none (after `excluded`). A stated row not exercised counts as not met. With rows undecided (missing, a
    conflict, blocked, no verdict) it is partly where some are met and some not, else undecided (None)."""
    rows = [r.id for r in change.rows if r.disclosure.lower() == "stated" and r.id not in guards and r.id not in excluded]
    if not rows:
        return {"value": "N/A", "rows": [], "met": [], "not_met": [], "undecided": []}
    met = [r for r in rows if verdicts.get(r) == "met"]
    not_met = [r for r in rows if verdicts.get(r) in ("not met", "not exercised")]
    undecided = [r for r in rows if r not in met and r not in not_met]
    if not undecided:
        value = "yes" if not not_met else "no" if not met else "partly"
    else:
        value = "partly" if met and not_met else None
    return {"value": value, "rows": rows, "met": met, "not_met": not_met, "undecided": undecided}


def joint_outcome(change: ChangeInfo, items: dict[str, str | None], dependency: dict, *, guards=frozenset(),
                  rules: dict[int, dict] | None = None) -> dict:
    """What the joint-outcome report needs of one fork: implemented and the dependent behaviour (kept, broken, not
    exercised or missing), with the change's type, tier, its dependency line or comparison row, and the plan's notes."""
    verdicts = {name.split()[0]: v for name, v in items.items()}
    rule = (rules if rules is not None else JOINT_RULES).get(change.number, {})
    excluded = set(rule.get("excluded") or [])
    imp = implemented(change, verdicts, guards=guards, excluded=excluded)
    out = {"implemented": imp["value"], "implemented_rows": imp, "dependent_behaviour": dependency.get("result"),
           "dependency_row": dependency.get("row"), "type": change.type, "tier": change.tier,
           "exercised_only_if": change.exercised_only_if, "comparison_row": change.comparison_row}
    if rule.get("coupled_with_dependency"):
        out["implemented_without_coupled"] = implemented(change, verdicts, guards=guards,
                                                         excluded=excluded | set(rule["coupled_with_dependency"]))
    if rule.get("beside_dependency"):
        out["beside_dependency"] = {i: verdicts.get(i) for i in rule["beside_dependency"]}
    for note in rule.get("notes") or []:
        out[note] = (dependency.get("notes") or {}).get(note)
    return out


def repair_reports(change: ChangeInfo, items: dict[str, str | None], dependency: dict, failed_setups: list[dict]) -> dict:
    """The repair report for each miss: each row not met, each row a blocked setup failed on, and the dependency when
    it is broken."""
    out = {}
    for name, v in items.items():
        rid = name.split()[0]
        if v == "not met" and rid in change.repair_reports:
            out[rid] = change.repair_reports[rid]
    for f in failed_setups:
        row = f.get("blocked_by") or f.get("row")
        if row and (f.get("repair_report") or change.repair_reports.get(row)):
            out[row] = f.get("repair_report") or change.repair_reports[row]
    if dependency.get("result") == "broken" and "Dependency" in change.repair_reports:
        out["Dependency"] = change.repair_reports["Dependency"]
    return out


# ----------------------------------------------------------------------------------------- keeping's classifier

CLASSES = rc.CLASSES
CLASSIFY_TEMPLATE = "keeping-classify-node.md"


def _test_block(source: str, title: str) -> tuple[int, int] | None:
    """The lines (1-based, inclusive) of the test with this title in a file's source."""
    lines = source.splitlines()
    for k, line in enumerate(lines):
        if any(q + title + q in line for q in ("'", '"', "`")):
            indent = len(line) - len(line.lstrip())
            for j in range(k + 1, min(len(lines), k + rc.MAX_TEST_LINES)):
                l = lines[j]
                if re.match(r"^\s*\}\s*\)", l) and len(l) - len(l.lstrip()) <= indent:
                    return k + 1, j + 1
            return k + 1, min(len(lines), k + rc.MAX_TEST_LINES)
    return None


def evidence_entries(tests: list[str], failures: dict[str, dict], sources: dict[str, str | None]) -> list[dict]:
    entries: list[dict] = []

    def add(test: str, kind: str, lines: list[str], *, first: int = 1, file: str | None = None, label: str = ""):
        e = {"seq": len(entries) + 1, "test": test, "kind": kind, "from": first, "to": first + max(len(lines), 1) - 1,
             "lines": lines or [""], "label": label}
        if file:
            e["file"] = file
        entries.append(e)
    for t in tests:
        f = failures[t]
        err = f.get("error") or {}
        text = f.get("message") or err.get("message") or "(no message)"
        if "actual" in err or "expected" in err:
            text += f"\nactual: {json.dumps(err.get('actual'))[:3000]}\nexpected: {json.dumps(err.get('expected'))[:3000]}"
        if err.get("stack"):
            text += "\n" + err["stack"]
        if len(text) > rc.MAX_OUTPUT:
            text = text[:rc.MAX_OUTPUT] + f" ...[cut: {len(text) - rc.MAX_OUTPUT} more characters]"
        add(t, "failure output", text.rstrip("\n").splitlines())
        if isinstance(err.get("actual"), (dict, list)) and isinstance(err.get("expected"), (dict, list)):
            add(t, "json difference", rc.json_difference(err["actual"], err["expected"], labels=("actual", "expected")),
                label="actual and expected")
        src = sources.get(f["file"])
        span = _test_block(src, f["title"]) if src else None
        if span:
            add(t, "test source", src.splitlines()[span[0] - 1:span[1]], first=span[0], file=f["file"],
                label=f"{f['file']} lines {span[0]}-{span[1]}")
    return entries


def classify_keeping(keep: dict, sources: dict[str, str | None], change: str, *, ask: Callable, out: Path | None = None,
                     attempts: int = rc.ATTEMPTS, batch_size: int = rc.BATCH) -> dict:
    """Each failing counted test, "new state only" or "keeping failure", by the judge (prompts/keeping-classify-node.md),
    in place in keep["failures"]; and in total new_state_only, keeping_failures, share_kept, classification_cost_usd."""
    cost = 0.0
    failures = keep["failures"]
    pending = sorted(failures)
    for k in range(0, len(pending), batch_size):
        batch = pending[k:k + batch_size]
        entries = evidence_entries(batch, failures, sources)
        text = grading._template(CLASSIFY_TEMPLATE, CHANGE=change, EVIDENCE=rc.render(entries))
        tries, problems = [], []
        for _ in range(attempts):
            structured, usage = ask(text)
            cost += (usage or {}).get("cost_usd") or 0.0
            problems = rc.check_rulings(structured, batch, entries, CLASSES)
            tries.append({"structured": structured, "problems": [p for _, p in problems], "usage": usage})
            if not problems:
                break
        answer = tries[-1]["structured"]
        listed = answer.get("rulings") if isinstance(answer, dict) else None
        rulings = {r.get("test"): r for r in listed} if isinstance(listed, list) else {}
        broken = {t for t, _ in problems if t is not None}
        for t in batch:
            if t in rulings and t not in broken:
                r = rulings[t]
                failures[t]["classification"] = {"classification": r["classification"], "by": "grader", "reason": r["reason"],
                                                 "evidence": rc._resolve(r["evidence"], entries)}
            else:
                failures[t]["classification"] = rc._harness("No valid ruling from the grader: " + "; ".join(
                    p for b, p in problems if b in (t, None)))
        if out is not None:
            out.mkdir(parents=True, exist_ok=True)
            (out / f"b{k // batch_size + 1:02d}.json").write_text(json.dumps({"prompt": text, "entries": entries,
                                                                             "tries": tries}, indent=1))
    nso = sum(f["classification"]["classification"] == CLASSES[0] for f in failures.values() if f.get("classification"))
    ran = keep["passed"] + keep["failed"]
    keep.update({"classified": True, "new_state_only": nso, "keeping_failures": keep["failed"] - nso,
                 "share_kept": (keep["passed"] + nso) / ran if ran else None, "classification_cost_usd": round(cost, 6)})
    return keep


# --------------------------------------------------------------------------------- the checkpoint and the view


@dataclass
class NodeCheckpoint:
    """A fork's commit checked out at /work/app in a volume of its own (`<name>-grade`), with the dependencies its
    source volume installed beside it; grader files at /work/grader, outputs at /work/out."""
    name: str
    commit: str
    image: str
    runner: Callable = subprocess.run

    @property
    def volume(self) -> str:
        return f"{self.name}-grade"

    def sh(self, script: str, stdin: str | None = None, check: bool = True, network: bool = False) -> str:
        cmd = ["docker", "run", "--rm", "-i", *([] if network else ["--network", "none"]),
               "-v", f"{executor._volume(self.volume)}:/work", "-w", "/work", self.image, "sh", "-c", script]
        p = self.runner(cmd, input=stdin, capture_output=True, text=True)
        if check and p.returncode != 0:
            raise RuntimeError(f"checkpoint command failed ({p.returncode}): {script[:200]}: {(p.stderr or '')[-800:]}")
        return p.stdout

    def put(self, path: str, text: str) -> None:
        self.sh(f"mkdir -p \"$(dirname '{path}')\" && cat > '{path}'", stdin=text)

    def get(self, path: str) -> str | None:
        p = self.runner(["docker", "run", "--rm", "--network", "none", "-v", f"{executor._volume(self.volume)}:/work",
                         self.image, "cat", path], capture_output=True, text=True)
        return p.stdout if p.returncode == 0 else None

    def export(self, source_volume: str) -> None:
        """.git alone, checked out at the exact commit (a detached HEAD is found too), cleaned of anything untracked;
        then each `node_modules` the source holds (three levels down at most), copied as it is."""
        script = (f"find /work -mindepth 1 -delete && mkdir -p /work/app /work/out /work/grader && cp -a /src/.git /work/app/.git && "
                  f"cd /work/app && git checkout -q -f --detach {self.commit} && git clean -fdxq && "
                  "cd /src && for d in $(find . -maxdepth 3 -type d -name node_modules -prune); do "
                  "mkdir -p \"/work/app/$(dirname \"$d\")\" && cp -a \"$d\" \"/work/app/$d\"; done")
        p = self.runner(["docker", "run", "--rm", "-v", f"{executor._volume(source_volume)}:/src:ro",
                         "-v", f"{executor._volume(self.volume)}:/work", self.image, "sh", "-c", script],
                        capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"exporting {self.commit} from {source_volume} failed: {(p.stderr or '')[-800:]}")

    def drop(self) -> None:
        self.runner(["docker", "volume", "rm", "-f", self.volume], capture_output=True, text=True)


AGENT_FILES = rg.AGENT_FILES
HIDDEN_DIRS = ("docs", ".claude")
SPEC_ID = re.compile(r"(?m)^\s*-\s*\[[ xXD]\]\s*\*{0,2}([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d{3,})\b")
DIFF_EXCLUDES = [":(exclude)docs", ":(exclude).claude", ":(exclude,glob)**/*.md", *(f":(exclude,glob)**/{f}" for f in AGENT_FILES)]


def spec_ids(text: str) -> set[str]:
    """The IDs a specs file gives its requirements (an EARS line: `- [x] **ID**: …`)."""
    return set(SPEC_ID.findall(text or ""))


def hidden_paths(paths: list[str]) -> list[str]:
    """What graders don't see, whatever the arm: docs/, .claude/, agent instruction files, and every Markdown file."""
    def hide(p: str) -> bool:
        return p.split("/", 1)[0] in HIDDEN_DIRS or p.rsplit("/", 1)[-1] in AGENT_FILES or p.endswith(".md")
    return sorted(p for p in paths if p and hide(p))


def _ids_re(ids) -> re.Pattern | None:
    return re.compile(r"\b(?:" + "|".join(sorted(map(re.escape, ids), key=len, reverse=True)) + r")\b") if ids else None


def strip_annotations(text: str, ids=frozenset()) -> str:
    """Code with the arm's annotations gone: a comment line carrying `@spec` goes whole, a trailing `@spec` comment
    goes, and the arm's spec IDs leave comment text (a code line's strings are left alone)."""
    pat = _ids_re(ids)
    out = []
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\n")
        nl = line[len(body):]
        s = body.strip()
        if "@spec" in body:
            if s.startswith(("//", "*", "#")) or (s.startswith("/*") and s.endswith("*/")) or (s.startswith("{/*") and s.endswith("*/}")):
                continue
            body = re.sub(r"\s*//\s*@spec\b.*$", "", body)
            body = re.sub(r"\s*\{/\*\s*@spec\b.*?\*/\}", "", body)
            body = re.sub(r"\s*/\*\s*@spec\b.*?\*/", "", body)
        if pat and pat.search(body):
            s = body.strip()
            if s.startswith(("//", "*", "/*", "{/*", "#")):
                body = pat.sub("", body)
            else:
                m = re.search(r"(?<=\s)//", body)
                if m:
                    body = body[:m.start()] + pat.sub("", body[m.start():])
        out.append(body + nl)
    return "".join(out)


def strip_diff(diff: str, ids=frozenset()) -> str:
    """A diff as the extraction reads it, with strip_annotations applied to every content line (a line it drops goes)."""
    out = []
    for line in diff.splitlines():
        if line.startswith(("diff ", "index ", "@@", "--- ", "+++ ", "new file", "deleted file", "similarity", "rename ",
                            "old mode", "new mode", "\\")) or not line:
            out.append(line)
            continue
        kept = strip_annotations(line[1:] + "\n", ids)
        if kept:
            out.append(line[0] + kept.rstrip("\n"))
    return "\n".join(out) + ("\n" if out else "")


def grader_ids(ck) -> set[str]:
    """The spec IDs the build's own specs files give (none on a bare build)."""
    listed = [p for p in (ck.sh(f"cd {APP} && git ls-files '*-specs.md'", check=False) or "").split() if p.endswith("-specs.md")]
    texts = rg._fetch(ck, APP, listed) if listed else {}
    return set().union(*(spec_ids(t) for t in texts.values())) if texts else set()


def write_arm_diff(ck, base: str, commit: str, ids) -> str:
    """The arm's diff of code and tests, annotations taken out, at /work/out/arm.diff (and change.diff, its neutral
    name for the adapter writer)."""
    raw = ck.sh(f"cd {APP} && git diff --no-color {base} {commit} -- . " + " ".join(f"'{x}'" for x in DIFF_EXCLUDES),
                check=False) or ""
    text = strip_diff(raw, ids)
    ck.put("/work/out/arm.diff", text)
    ck.put("/work/out/change.diff", text)
    return text


def doc_changes(numstat: str) -> dict:
    docs = {"files": 0, "lines_added": 0, "lines_removed": 0, "paths": []}
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and hidden_paths([parts[2]]):
            docs["files"] += 1
            docs["lines_added"] += int(parts[0]) if parts[0].isdigit() else 0
            docs["lines_removed"] += int(parts[1]) if parts[1].isdigit() else 0
            docs["paths"].append(parts[2])
    docs["paths"].sort()
    return docs


def prepare_for_graders(ck, ids) -> dict:
    """The code-only checkout graders get, whatever the arm: annotations out of the code, the hidden paths gone, and
    .git with them (run after keeping, whose tests may read the docs)."""
    paths = (ck.sh(f"cd {APP} && git ls-files", check=False) or "").split("\n")
    hidden = hidden_paths(paths)
    terms = " ".join(f"-e '{i}'" for i in sorted(ids))
    marked = [p for p in (ck.sh(f"cd {APP} && git grep -lI -e '@spec' {terms} -- . " + " ".join(f"'{x}'" for x in DIFF_EXCLUDES)
                                + " 2>/dev/null", check=False) or "").split() if p and p not in hidden]
    changed = {}
    if marked:
        for p, t in rg._fetch(ck, APP, marked).items():
            new = strip_annotations(t, ids)
            if new != t:
                changed[p] = new
        rg._write(ck, APP, changed)
    quoted = " ".join(f"'{p}'" for p in [*hidden, *HIDDEN_DIRS])
    ck.sh(f"cd {APP} && rm -rf {quoted} .git && find . -mindepth 1 -depth -type d -empty -not -path '*/node_modules/*' "
          "-delete 2>/dev/null; true", check=False)
    return {"hidden": hidden, "annotations_stripped": sorted(changed), "spec_ids": len(ids)}
