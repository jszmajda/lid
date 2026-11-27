"""M2f's graded targets: each dependency probe and each held-out test function as a self-contained test target, built
from the snapshot and kept outside the arms' view (in the variant set's graded/ folder).

    python3.12 m2f_graded_targets.py --repo /path/to/clowder --commit 86db995 \\
        --probes ../seeds/clowder/hidden/m2f-dependency-probes --holdouts ../seeds/clowder/hidden/m2f-holdouts.json \\
        --out <variant-set>/graded

**Dependency probes.** Each probe file holds `#[test] fn probe_m2f_*` functions written to be appended to a host test
module, whose helpers they use (PROBES gives each file its change and host, as the seed's validate.sh and README do).
An arm's variant may thin the host or hold it out, so a probe's target is the host module as the snapshot has it, with
its own `#[test]` functions removed and the probe appended, pruned to what the probe reaches.

**Held-out tests.** m2f-holdouts.json lists test functions held out of every variant. Each change's tests from one file
make one target: the file as the snapshot has it, with only those tests kept, pruned to what they reach.

**Pruning** (prune), so that drift in an API only an unrelated helper used can't stop a target building: a target keeps
its tests and, transitively, the top-level items whose names they use (functions, constants, statics, types, macros),
an impl whose type or trait is kept or that defines a method something kept calls with method syntax, a trait
likewise, and every inner attribute, macro call and item it doesn't recognise (what those name is reached too). A
name a format string captures inline counts as used. Imports from the workspace's own crates that nothing kept names
go; std's and other crates' stay (they can't drift with an arm, and may bring a trait into scope), as do glob and
`as _` imports.

**Layout,** as the keeping step's targets (costeval/rust_grading.held_out_targets): a module of a test directory goes
into a directory of its own, `crates/<crate>/tests/<target>/`, with a main.rs that carries the original main.rs's crate
attributes and declares the module, the directory's helper modules (those with no `#[test]`, copied as they are), and
any sibling module it reaches through `crate::` or `super::` (copied with its own tests removed). A file that was a
target of its own comes back as one file. The directory's helper modules and the siblings are copied whole, not
pruned (clowder-tui's integration tests have neither). Anything pruning leaves unused is allowed (dead_code,
unused_imports).

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
        start, end = _whole_lines(text, masked, m.start(), close + 1)
        out.append(TestFn(f.group(1), start, end))
    return out


def _whole_lines(text: str, masked: str, at: int, end: int) -> tuple[int, int]:
    """The span that removes an item whose code runs from `at` (its first attribute or keyword) to `end`: from its
    attached doc comments and attributes, at the start of their line, to the end of its last line when nothing but a
    comment follows it there."""
    start = _attached_start(text, masked, at)
    ls = text.rfind("\n", 0, start) + 1
    if not text[ls:start].strip():
        start = ls
    nl = text.find("\n", end)
    if not masked[end:len(text) if nl < 0 else nl].strip():
        end = len(text) if nl < 0 else nl + 1
    return start, end


def _splice(text: str, edits: list[tuple[int, int, str]]) -> str:
    """The text with each span replaced by its text; where a span is removed, a blank line left on both sides of the
    cut becomes one."""
    out, at = "", 0
    for s, e, new in sorted(edits):
        out += text[at:s] + new
        at = e
        while not new and text.startswith("\n", at) and (out.endswith("\n\n") or out.endswith("{\n") or not out):
            at += 1
    out += text[at:]
    if edits and at >= len(text):
        out = out.rstrip("\n") + "\n" if out.strip() else ""
    return out


def _cut(text: str, spans: list[tuple[int, int]]) -> str:
    """The text without these spans; a blank line left on both sides of a cut becomes one."""
    return _splice(text, [(s, e, "") for s, e in spans])


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


# ------------------------------------------------------------------------------------------------- pruning


@dataclass(frozen=True)
class Item:
    kind: str  # use, fn, const, static, struct, enum, union, type, trait, impl, mod, macro (macro_rules!), other
    name: str | None
    start: int  # its removal span: attached doc comments and attributes through the end of its last line
    end: int
    code: tuple[int, int]  # its own text: first attribute or keyword through its closing brace or semicolon
    header: frozenset = frozenset()  # an impl's words before its body; a trait's name
    methods: frozenset = frozenset()  # the functions an impl or trait defines


_VIS_KIND = re.compile(r"(?:pub\s*(?:\([^)]*\))?\s*)?(?:(?:unsafe|async|default)\s+)*(?:const\s+(?=(?:unsafe\s+|async\s+)*fn\b))?"
                       r"(?:(?:unsafe|async)\s+)*(use|fn|const|static|struct|enum|union|type|trait|impl|mod|macro_rules\s*!)"
                       r"(?![\w!])")
_ITEM_NAME = re.compile(r"\s*(?:mut\s+)?(?:r#)?([A-Za-z_]\w*)")
_WORD = re.compile(r"[A-Za-z_]\w*")


def _item_end(masked: str, k: int, semicolon_only: bool) -> int:
    """The index of an item's last character: its first `;` at depth 0, or (unless semicolon_only) the brace closing
    its first `{` at depth 0, with a `;` straight after it."""
    depth = 0
    for j in range(k, len(masked)):
        c = masked[j]
        if c == "{" and depth == 0 and not semicolon_only:
            close = _close(masked, j)
            if close is None:
                return len(masked) - 1
            after = re.compile(r"\s*;").match(masked, close + 1)
            return after.end() - 1 if after else close
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == ";" and depth == 0:
            return j
    return len(masked) - 1


def top_items(text: str) -> list[Item]:
    """A file's top-level items, in order. Inner attributes, macro calls, `extern crate` and anything else
    unrecognised are "other"."""
    masked, items, k = mask(text), [], 0
    while True:
        while k < len(masked) and masked[k].isspace():
            k += 1
        if k >= len(masked):
            return items
        first = k
        if inner := re.compile(r"#\s*!\s*\[").match(masked, k):
            close = _close(masked, inner.end() - 1, "[]")
            end = len(masked) - 1 if close is None else close
            kind, name, header, methods = "other", None, frozenset(), frozenset()
        else:
            k = _past_attrs(masked, k)
            while k < len(masked) and masked[k].isspace():
                k += 1
            m = _VIS_KIND.match(masked, k)
            kind = "macro" if m and m.group(1).startswith("macro_rules") else m.group(1) if m else "other"
            end = _item_end(masked, m.end() if m else k, kind in ("use", "const", "static", "type"))
            name, header, methods = None, frozenset(), frozenset()
            if kind not in ("use", "impl", "other"):
                nm = _ITEM_NAME.match(masked, m.end())
                name = nm.group(1) if nm else None
            if kind in ("impl", "trait"):
                body = masked.find("{", m.end(), end + 1)
                body = end if body < 0 else body
                header = frozenset(_WORD.findall(masked[m.end():body])) if kind == "impl" else frozenset({name})
                methods = frozenset(re.findall(r"\bfn\s+(?:r#)?([A-Za-z_]\w*)", masked[body:end + 1]))
        start, stop = _whole_lines(text, masked, first, end + 1)
        items.append(Item(kind, name, start, stop, (first, end + 1), header, methods))
        k = end + 1


def _words(text: str, masked: str, a: int, b: int) -> set[str]:
    """The names a stretch of code uses: its words outside comments and strings, and those a format string captures
    inline (`{name}`)."""
    return set(_WORD.findall(masked[a:b])) | set(re.findall(r"\{([A-Za-z_]\w*)", text[a:b]))


def _use_leaves(tree: str, prefix: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], str | None]] | None:
    """Each path a use tree imports, with its alias: `a::{b, c::d as e}` gives (a, b) and (a, c, d) as e. None for a
    tree it can't read."""
    tree = " ".join(tree.split())
    if tree.endswith("}") and "{" in tree:
        i = tree.index("{")
        head = tree[:i].strip()
        if head and not head.endswith("::"):
            return None
        segs = tuple(s.strip() for s in head[:-2].split("::")) if head else ()
        parts, depth, cur = [], 0, ""
        for ch in tree[i + 1:-1]:
            depth += {"{": 1, "}": -1}.get(ch, 0)
            if ch == "," and depth == 0:
                parts.append(cur)
                cur = ""
            else:
                cur += ch
        parts.append(cur)
        out = []
        for part in parts:
            if part.strip():
                sub = _use_leaves(part, prefix + segs)
                if sub is None:
                    return None
                out += sub
        return out
    m = re.fullmatch(r"\s*([\w:* ]+?)(?:\s+as\s+(\w+))?\s*", tree)
    if not m:
        return None
    return [(prefix + tuple(s.strip() for s in m.group(1).split("::")), m.group(2))]


def _pruned_use(text: str, masked: str, item: Item, refs: set[str], workspace: set[str]) -> str | None:
    """A use item with the imports nothing kept names taken out: its replacement ("" for none left), or None to keep it
    as it is. Only imports from the workspace's own crates (and crate::, super::, self::) go; std's and other crates'
    can't drift with an arm and may bring traits into scope, and a glob or `as _` import stays."""
    a, b = item.code
    m = re.fullmatch(r"((?:pub\s*(?:\([^)]*\))?\s*)?)use\s+(.*?)\s*;", masked[a:b], re.S)
    if not m:  # attributes, or a shape this doesn't read
        return None
    leaves = _use_leaves(m.group(2))
    if not leaves:
        return None
    kept = []
    for path, alias in leaves:
        root = next((s for s in path if s), "")
        bound = alias or (path[-2] if path[-1] == "self" and len(path) > 1 else path[-1])
        if path[-1] == "*" or alias == "_" or root not in workspace | {"crate", "super", "self"} or bound in refs:
            kept.append((path, alias))
    if len(kept) == len(leaves):
        return None
    vis = " ".join(m.group(1).split())
    lines = [f"{vis + ' ' if vis else ''}use {'::'.join(p[:-1] if p[-1] == 'self' and len(p) > 1 else p)}"
             f"{' as ' + al if al else ''};" for p, al in kept]
    return "".join(line + "\n" for line in lines)


_METHOD_CALL = re.compile(r"\.\s*([A-Za-z_]\w*)\s*(?:::\s*<[^>]*>\s*)?\(")


def prune(text: str, roots: set[str], workspace: set[str]) -> str:
    """The file with only what its test functions named in roots reach: the items whose names they use, then what
    those use, and so on; an impl when its type or trait is kept, or when it defines a method something kept calls
    with method syntax (`x.name(`); a trait likewise. Inner attributes, macro calls and anything unrecognised stay,
    and what they name is reached too. Imports from the workspace's own crates that nothing kept names go
    (_pruned_use)."""
    items = top_items(text)
    masked = mask(text)
    words = [_words(text, masked, *it.code) for it in items]
    method_calls = [set(_METHOD_CALL.findall(masked[it.code[0]:it.code[1]])) for it in items]
    keep = {k for k, it in enumerate(items) if it.kind == "other" or (it.kind == "fn" and it.name in roots)}
    refs = set().union(*(words[k] for k in keep))
    calls = set().union(*(method_calls[k] for k in keep))
    local = {it.name for it in items if it.name}
    changed = True
    while changed:
        changed = False
        kept_names = {items[k].name for k in keep if items[k].name}
        for k, it in enumerate(items):
            if k in keep or it.kind == "use":
                continue
            hit = bool(it.name and it.name in refs)
            if it.kind == "impl":
                hit = bool(it.header & kept_names) or bool(it.methods & calls and it.header & local)
            elif it.kind == "trait":
                hit = hit or bool(it.methods & calls)
            if hit:
                keep.add(k)
                refs |= words[k]
                calls |= method_calls[k]
                changed = True
    edits = []
    for k, it in enumerate(items):
        if it.kind == "use":
            new = _pruned_use(text, masked, it, refs, workspace)
            if new is not None:
                edits.append((it.start, it.end, new))
        elif k not in keep:
            edits.append((it.start, it.end, ""))
    return _splice(text, edits) if edits else text


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


def workspace_crates(snap) -> set[str]:
    """The workspace's own crates as Rust names them (clowder-core is clowder_core): what an arm's change can reach."""
    return {m.group(1).replace("-", "_") for p in snap.list("crates")
            if (m := re.fullmatch(r"crates/([^/]+)/Cargo\.toml", p))}


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
    workspace = workspace_crates(snapshot)

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
        text = prune(text, set(tests), workspace)
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
            kept = prune(keep_tests(text, set(g["tests"])), set(g["tests"]), workspace)
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
