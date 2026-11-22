"""M2f's graded targets: each dependency probe and each held-out test function as a self-contained test target, built
from the snapshot and kept outside the arms' view (in the variant set's graded/ folder).

    python3.12 m2f_graded_targets.py --repo /Users/jess/src/clowder --commit 86db995 \\
        --probes ../seeds/clowder/hidden/m2f-dependency-probes --holdouts ../seeds/clowder/hidden/m2f-holdouts.json \\
        --out <variant-set>/graded

**Dependency probes.** Each probe file holds `#[test] fn probe_m2f_*` functions written to be appended to a host test
module, whose helpers they use (PROBES gives each file its change and host, as the seed's validate.sh and README do).
An arm's variant may thin the host or hold it out, so a probe's target is the host module as the snapshot has it, with
its own `#[test]` functions removed and its helpers kept, and the probe appended.

**Held-out tests.** m2f-holdouts.json lists test functions held out of every variant. Each change's tests from one file
make one target: the file as the snapshot has it, with only those tests kept.

**Layout,** as the keeping step's targets (costeval/rust_grading.held_out_targets): a module of a test directory goes
into a directory of its own, `crates/<crate>/tests/<target>/`, with a main.rs that carries the original main.rs's crate
attributes and declares the module, the directory's helper modules (those with no `#[test]`, copied as they are), and
any sibling module it reaches through `crate::` or `super::` (copied with its own tests removed). A file that was a
target of its own comes back as one file. Helpers left unused are allowed (dead_code, unused_imports), never removed.

graded.json lists the targets:
`[{"target", "kind": "dependency probe" | "held-out test", "change", "status": "graded" | "retired", "crate",
"module", "tests": [fn names], "files": [paths in the checkout], "source": {...}}]`. A probe's status is "graded"; a
held-out test's is m2f-holdouts.json's. `module` is the module the tests sit in (their cargo names are
`<module>::<fn>`), or null for a target of one file. grade_rust.py grades a fork's change on the targets with that
change and status "graded".

The remover reads Rust with its own masking of comments, strings (raw ones too) and char literals, so a brace or a
`#[test]` inside any of them is never taken for code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PROBE_HOST_DIR = "crates/clowder-tui/tests/integration"
PROBES: dict[str, tuple[int, str]] = {  # probe file -> (change, host module in the snapshot)
    "speed.rs": (13, f"{PROBE_HOST_DIR}/update.rs"),
    "mess.rs": (14, f"{PROBE_HOST_DIR}/readouts.rs"),
    "year.rs": (15, f"{PROBE_HOST_DIR}/achievements.rs"),
    "tinker.rs": (16, f"{PROBE_HOST_DIR}/bench.rs"),
    "odds.rs": (17, f"{PROBE_HOST_DIR}/pen_pals.rs"),
    "shortfall.rs": (18, f"{PROBE_HOST_DIR}/readouts.rs"),
    "idle.rs": (19, f"{PROBE_HOST_DIR}/chrome.rs"),
    "history.rs": (20, f"{PROBE_HOST_DIR}/report_queue.rs"),
}
ALLOW = "#![allow(dead_code, unused_imports)]"
GRADED_JSON = "graded.json"


# --------------------------------------------------------------------------------------------- reading Rust


_RAW = re.compile(r'[bc]?r(#*)"')
_CHAR = re.compile(r"'(?:\\(?:x[0-9a-fA-F]{2}|u\{[0-9a-fA-F]{1,6}\}|.)|[^\\'\n])'")


def _ident(c: str) -> bool:
    return c.isalnum() or c == "_"


def mask(text: str) -> str:
    """The text with comments blanked to spaces and string and char literals' contents filled with x, at the same
    length and on the same lines, so every brace, bracket, `#` and word left in it is code."""
    out, i, n = list(text), 0, len(text)

    def blank(a: int, b: int, ch: str) -> None:
        for k in range(a, min(b, n)):
            if out[k] != "\n":
                out[k] = ch
    while i < n:
        c = text[i]
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            blank(i, j, " ")
            i = j
        elif text.startswith("/*", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if text.startswith("/*", j):
                    depth, j = depth + 1, j + 2
                elif text.startswith("*/", j):
                    depth, j = depth - 1, j + 2
                else:
                    j += 1
            blank(i, j, " ")
            i = j
        elif c in "bcr" and (i == 0 or not _ident(text[i - 1])) and (m := _RAW.match(text, i)):
            close = '"' + m.group(1)
            j = text.find(close, m.end())
            j = n if j < 0 else j
            blank(m.end(), j, "x")
            i = j + len(close)
        elif c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            blank(i + 1, j, "x")
            i = j + 1
        elif c == "'" and (m := _CHAR.match(text, i)):
            blank(i + 1, m.end() - 1, "x")
            i = m.end()
        elif _ident(c):  # a whole word at once, so a `b`, `c` or `r` inside one never opens a literal
            j = i
            while j < n and _ident(text[j]):
                j += 1
            i = j
        else:
            i += 1
    return "".join(out)


@dataclass(frozen=True)
class TestFn:
    name: str
    start: int  # where its removal starts: its first doc-comment or attribute line
    end: int  # where it ends: past its closing brace and the rest of that line


_TEST_ATTR = re.compile(r"#\s*\[\s*(?:\w+\s*::\s*)*test\s*\]")
_ATTR_HEAD = re.compile(r"\s*#\s*\[")
_FN = re.compile(r"\s*(?:pub\s*(?:\([^)]*\))?\s*)?(?:(?:const|async|unsafe)\s+)*fn\s+(?:r#)?(\w+)")


def _close(masked: str, open_at: int, pair: str = "{}") -> int | None:
    depth = 0
    for k in range(open_at, len(masked)):
        if masked[k] == pair[0]:
            depth += 1
        elif masked[k] == pair[1]:
            depth -= 1
            if depth == 0:
                return k
    return None


def _past_attrs(masked: str, k: int) -> int:
    while m := _ATTR_HEAD.match(masked, k):
        close = _close(masked, m.end() - 1, "[]")
        if close is None:
            return k
        k = close + 1
    return k


def _attached_start(text: str, masked: str, at: int) -> int:
    """The start of the attributes and doc comments attached to the item whose attribute begins at `at`."""
    start = at
    while True:
        j = start - 1
        while j >= 0 and text[j].isspace():
            j -= 1
        if j < 0:
            return start
        if masked[j] == "]":  # an attribute, perhaps over several lines
            depth, k = 0, j
            while k >= 0:
                depth += {"]": 1, "[": -1}.get(masked[k], 0)
                if depth == 0:
                    break
                k -= 1
            h = k - 1
            while h >= 0 and masked[h].isspace():
                h -= 1
            if k > 0 and h >= 0 and masked[h] == "#":
                start = h
                continue
            return start
        ls = text.rfind("\n", 0, j) + 1
        line = text[ls:j + 1].lstrip()
        if line.startswith("///") and not line.startswith("////") and not masked[ls:j + 1].strip():
            start = j + 1 - len(line)
            continue
        return start


def test_functions(text: str) -> list[TestFn]:
    """Each `#[test]` function in a Rust file, at any depth, with the span that removes it whole: its doc comments,
    its attributes, and its body."""
    masked = mask(text)
    out: list[TestFn] = []
    for m in _TEST_ATTR.finditer(masked):
        if out and m.start() < out[-1].end:  # a second test attribute on a function already found
            continue
        f = _FN.match(masked, _past_attrs(masked, m.end()))
        if not f:
            continue
        k, depth = f.end(), 0
        while k < len(masked):
            c = masked[k]
            if c in "([":
                depth += 1
            elif c in ")]":
                depth -= 1
            elif depth == 0 and c in "{;":
                break
            k += 1
        if k >= len(masked) or masked[k] != "{" or (close := _close(masked, k)) is None:
            continue
        start = _attached_start(text, masked, m.start())
        ls = text.rfind("\n", 0, start) + 1
        if not text[ls:start].strip():
            start = ls
        end = close + 1
        nl = text.find("\n", end)
        if not masked[end:len(text) if nl < 0 else nl].strip():
            end = len(text) if nl < 0 else nl + 1
        out.append(TestFn(f.group(1), start, end))
    return out


def _cut(text: str, spans: list[tuple[int, int]]) -> str:
    """The text without these spans; a blank line left on both sides of a cut becomes one."""
    out, at = "", 0
    for s, e in sorted(spans):
        out += text[at:s]
        at = e
        while text.startswith("\n", at) and (out.endswith("\n\n") or out.endswith("{\n") or not out):
            at += 1
    out += text[at:]
    if at >= len(text) and spans:
        out = out.rstrip("\n") + "\n" if out.strip() else ""
    return out


def remove_tests(text: str, names: set[str] | None = None) -> str:
    """The file without its `#[test]` functions (or only those named), everything else kept as it is."""
    return _cut(text, [(t.start, t.end) for t in test_functions(text) if names is None or t.name in names])


def keep_tests(text: str, keep: set[str]) -> str:
    """The file with only the named `#[test]` functions left; a name the file doesn't have is refused."""
    found = test_functions(text)
    missing = sorted(set(keep) - {t.name for t in found})
    if missing:
        raise ValueError(f"no #[test] function named {', '.join(missing)}")
    return _cut(text, [(t.start, t.end) for t in found if t.name not in keep])


_ITEM = re.compile(r"\b(fn|const|static|struct|enum|type|trait|mod|union)\s+(?:mut\s+)?(?:r#)?([A-Za-z_]\w*)"
                   r"|\bmacro_rules\s*!\s*([A-Za-z_]\w*)")


def top_level_names(text: str) -> set[str]:
    """The names a file's top-level items define (functions, constants, types, modules, macros)."""
    masked = mask(text)
    depth, at, names = 0, 0, set()
    for m in _ITEM.finditer(masked):
        depth += sum({"{": 1, "}": -1}.get(c, 0) for c in masked[at:m.start()])
        at = m.start()
        name = m.group(2) or m.group(3)
        if depth == 0 and name not in ("fn", "unsafe", "async", "extern"):
            names.add(name)
    return names


# ------------------------------------------------------------------------------------------------ snapshot


class GitSnapshot:
    """The repository's files at one commit, read with git."""

    def __init__(self, repo: Path, commit: str):
        self.repo = repo
        self.commit = self._git("rev-parse", "--verify", f"{commit}^{{commit}}").strip()
        self._listing: list[str] | None = None

    def _git(self, *args: str) -> str:
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True, text=True).stdout

    def read(self, path: str) -> str | None:
        p = subprocess.run(["git", "-C", str(self.repo), "show", f"{self.commit}:{path}"], capture_output=True, text=True)
        return p.stdout if p.returncode == 0 else None

    def list(self, directory: str) -> list[str]:
        if self._listing is None:
            self._listing = self._git("ls-tree", "-r", "--name-only", self.commit).split("\n")
        return [p for p in self._listing if p.startswith(directory.rstrip("/") + "/")]


class DictSnapshot:
    """A snapshot held in a dict, path -> text."""

    def __init__(self, files: dict[str, str], commit: str = ""):
        self.files, self.commit = dict(files), commit

    def read(self, path: str) -> str | None:
        return self.files.get(path)

    def list(self, directory: str) -> list[str]:
        return sorted(p for p in self.files if p.startswith(directory.rstrip("/") + "/"))


# ------------------------------------------------------------------------------------------------- targets


_MODULE_FILE = re.compile(r"crates/([^/]+)/tests/([^/]+)/([^/]+)\.rs")
_TARGET_FILE = re.compile(r"crates/([^/]+)/tests/([^/]+)\.rs")
_DECLARED = re.compile(r"(?m)^\s*(?:pub\s+)?mod\s+(\w+)\s*;")
_REACH = re.compile(r"\b(?:crate|super)\s*::\s*(?:(\w+)|\{([^}]*)\})")


def _reached(text: str) -> set[str]:
    out = set()
    for m in _REACH.finditer(mask(text)):
        if m.group(1):
            out.add(m.group(1))
        else:
            out.update(re.findall(r"(?:^|[{,])\s*(\w+)", m.group(2)))
    return out


def _module_files(snap, src_dir: str, m: str) -> dict[str, str]:
    """A declared module's files, by path relative to the test directory: `m.rs`, or `m/` whole."""
    listing = snap.list(src_dir)
    if f"{src_dir}/{m}.rs" in listing:
        return {f"{m}.rs": snap.read(f"{src_dir}/{m}.rs")}
    return {p[len(src_dir) + 1:]: snap.read(p) for p in listing if p.startswith(f"{src_dir}/{m}/")}


def _helpers(snap, src_dir: str, module: str, module_text: str) -> dict[str, dict[str, str]]:
    """The modules a target of this test directory declares beside its own, in main.rs's order: every helper module
    (no #[test] in it), as it is, and every sibling the module reaches through crate:: or super::, with its own tests
    removed (and, in turn, what that sibling reaches)."""
    declared = _DECLARED.findall(snap.read(f"{src_dir}/main.rs") or "")
    chosen: dict[str, dict[str, str]] = {}
    for m in declared:
        files = _module_files(snap, src_dir, m) if m != module else {}
        if files and not any(test_functions(t) for t in files.values()):
            chosen[m] = files
    pending = _reached(module_text).union(*(_reached(t) for fs in chosen.values() for t in fs.values()))
    while pending:
        m = pending.pop()
        if m in chosen or m == module or m not in declared:
            continue
        chosen[m] = {rel: remove_tests(t) for rel, t in _module_files(snap, src_dir, m).items()}
        pending |= set().union(*(_reached(t) for t in chosen[m].values()))
    return {m: chosen[m] for m in declared if m in chosen}


def _target(snap, target: str, path: str, text: str) -> tuple[dict[str, str], str, str | None]:
    """The files that make `text` (a test file at `path` in the snapshot, as edited) a target of its own:
    (files by checkout path, crate, module or None)."""
    if m := _MODULE_FILE.fullmatch(path):
        crate, src_dir, module = m.group(1), path.rsplit("/", 1)[0], m.group(3)
        if module == "main":
            raise ValueError(f"{path}: a test directory's main.rs can't be a host")
        main = snap.read(f"{src_dir}/main.rs") or ""
        attrs = [line for line in main.splitlines() if line.startswith("#![")]
        helpers = _helpers(snap, src_dir, module, text)
        dest = f"crates/{crate}/tests/{target}"
        files = {f"{dest}/{rel}": t for fs in helpers.values() for rel, t in fs.items()}
        files[f"{dest}/main.rs"] = "\n".join(attrs + [ALLOW, ""] + [f"mod {h};" for h in helpers] + [f"mod {module};", ""])
        files[f"{dest}/{module}.rs"] = text
        return files, crate, module
    if m := _TARGET_FILE.fullmatch(path):
        return {f"crates/{m.group(1)}/tests/{target}.rs": text}, m.group(1), None
    raise ValueError(f"{path}: not a test file directly under a crate's tests/ or one of its directories")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def build(snapshot, probes_dir: Path, holdouts: dict, *,
          probe_map: dict[str, tuple[int, str]] = PROBES) -> tuple[dict[str, str], list[dict]]:
    """Every graded target's files (by checkout path) and graded.json's entries. Anything the seed and the table don't
    agree on, or that the snapshot lacks, is refused."""
    names = sorted(p.name for p in probes_dir.glob("*.rs"))
    if extra := sorted(set(names) - set(probe_map)):
        raise ValueError(f"probe files the table doesn't place: {', '.join(extra)}")
    if missing := sorted(set(probe_map) - set(names)):
        raise ValueError(f"probes the table names with no file in {probes_dir}: {', '.join(missing)}")
    files: dict[str, str] = {}
    entries: list[dict] = []

    def add(target_files: dict[str, str], entry: dict) -> None:
        if any(e["target"] == entry["target"] for e in entries) or set(target_files) & set(files):
            raise ValueError(f"{entry['target']}: two targets with one name")
        files.update(target_files)
        entries.append({**entry, "files": sorted(target_files)})
    for name in sorted(probe_map, key=lambda p: (probe_map[p][0], p)):
        change, host = probe_map[name]
        probe = (probes_dir / name).read_text(encoding="utf-8")
        tests = [t.name for t in test_functions(probe)]
        if not tests:
            raise ValueError(f"{name}: no #[test] function in it")
        host_text = snapshot.read(host)
        if host_text is None:
            raise ValueError(f"{name}: its host {host} isn't in the snapshot")
        stripped = remove_tests(host_text)
        if clash := sorted(top_level_names(stripped) & top_level_names(probe)):
            raise ValueError(f"{name}: defines {', '.join(clash)}, which its host {host} already has")
        text = stripped.rstrip("\n") + "\n" + ("" if probe.startswith("\n") else "\n") + probe.rstrip("\n") + "\n"
        target = f"m2f_c{change}_probe_{Path(name).stem}"
        target_files, crate, module = _target(snapshot, target, host, text)
        add(target_files, {"target": target, "kind": "dependency probe", "change": change, "status": "graded",
                           "crate": crate, "module": module, "tests": tests,
                           "source": {"commit": snapshot.commit, "host": host, "probe": name, "probe_sha256": _sha(probe)}})
    groups: dict[tuple[int, str], dict] = {}
    for t in holdouts.get("tests") or []:
        path, fn = t["test"].rsplit("::", 1)
        path = path if path.startswith("crates/") else f"crates/{path}"
        g = groups.setdefault((int(t["change"]), path), {"status": t["status"], "tests": []})
        if g["status"] != t["status"]:
            raise ValueError(f"change {t['change']}, {path}: held-out tests with two statuses")
        g["tests"].append(fn)
    for (change, path), g in sorted(groups.items()):
        text = snapshot.read(path)
        if text is None:
            raise ValueError(f"held-out tests for change {change}: {path} isn't in the snapshot")
        try:
            kept = keep_tests(text, set(g["tests"]))
        except ValueError as e:
            raise ValueError(f"{path}: {e}") from None
        target = f"m2f_c{change}_heldout_{Path(path).stem}"
        target_files, crate, module = _target(snapshot, target, path, kept)
        add(target_files, {"target": target, "kind": "held-out test", "change": change, "status": g["status"],
                           "crate": crate, "module": module, "tests": g["tests"],
                           "source": {"commit": snapshot.commit, "file": path}})
    return files, entries


def write(out: Path, files: dict[str, str], entries: list[dict]) -> None:
    """Write the targets and graded.json under out, replacing an earlier build there."""
    if out.exists():
        if (out / GRADED_JSON).exists():
            shutil.rmtree(out)
        elif any(out.iterdir()):
            raise SystemExit(f"{out} holds files that aren't graded targets; not writing over them")
    for path, text in files.items():
        (out / path).parent.mkdir(parents=True, exist_ok=True)
        (out / path).write_text(text, encoding="utf-8")
    out.mkdir(parents=True, exist_ok=True)
    (out / GRADED_JSON).write_text(json.dumps(entries, indent=1) + "\n", encoding="utf-8")


def main(argv=None, *, snapshot=None, probe_map: dict[str, tuple[int, str]] = PROBES) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", type=Path, required=True, help="the seed's repository (Clowder)")
    ap.add_argument("--commit", required=True, help="the snapshot (86db995)")
    ap.add_argument("--probes", type=Path, required=True, help="the dependency probes' folder")
    ap.add_argument("--holdouts", type=Path, required=True, help="m2f-holdouts.json")
    ap.add_argument("--out", type=Path, required=True, help="<variant-set>/graded")
    args = ap.parse_args(argv)
    snap = snapshot or GitSnapshot(args.repo, args.commit)
    holdouts = json.loads(args.holdouts.read_text(encoding="utf-8"))
    try:
        files, entries = build(snap, args.probes, holdouts, probe_map=probe_map)
    except ValueError as e:
        raise SystemExit(f"m2f_graded_targets: {e}") from None
    write(args.out, files, entries)
    for e in entries:
        print(f"{e['target']}: {e['kind']}, change {e['change']}, {e['status']}, {len(e['tests'])} test(s)")
    print(f"{len(entries)} targets in {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
