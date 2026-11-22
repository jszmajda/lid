"""Build the falsification test's repository variants from one Clowder commit (design.md, "Later seeds and variants").

    python3.12 clowder_variants.py --repo /Users/jess/src/clowder --commit 86db995 --seed v1 \\
        --out ../runs/clowder-variants/v1 --volumes --cargo-test

Each variant is a single-commit git repository with fresh history, so no arm can recover what was removed from
`git log`. Three are built:

- **held-out slice** (removed from all three): a seeded random share (15%) of the test files under crates/*/tests/,
  drawn per directory, saved aside under `held-out/` for grading keeping. A removed module's `mod` line goes from its
  directory's `main.rs`, so the build stays green.
- **full**: everything else, docs and agent instruction files included.
- **lid**: the same files as full. The LID arm's plugin is installed by the arm's own setup, as for other seeds; the
  repository's AGENTS.md already carries its LID directives. Full and lid are loaded as colocated jj repositories,
  since the project's instructions ask for jj; stripped stays plain git.
- **stripped**: no docs/, no agent instruction files (AGENTS.md, CLAUDE.md, GEMINI.md, .claude/), no LID tooling
  (a script outside crates/ that reads `@spec` annotations or docs/intent), no README paragraph about LID or linking
  into docs/, no `@spec` annotations and no other citation of a spec ID (the IDs' prefixes are read from the specs),
  and tests thinned at random, whole files, per directory, until test lines are about `--ratio` (0.6) times the
  non-test source lines.

Writes, under --out: `<variant>/` (each repository), `held-out/` (the removed test files at their paths, and the
original helper modules they use), and `manifest.json` (what was removed and stripped, sizes in bytes and estimated
tokens by class, each variant's commit and volume, and with --cargo-test each variant's build and test results).
--volumes loads each repository into a Docker volume (`ce-cv-<seed>-<variant>`) for fork runs.

--seed names the set (its folder's manifest, its volumes); --draw-seed (default: --seed) seeds the held-out draw and the
thinning, so a later set can take exactly an earlier set's files:

    python3.12 clowder_variants.py --repo /Users/jess/src/clowder --commit 86db995 --seed v2 --draw-seed v1 \\
        --holdouts ../seeds/clowder/hidden/m2f-holdouts.json --out ../runs/clowder-variants/v2 --volumes --cargo-test

--holdouts holds out single test functions (`{"tests": [{"change", "status", "test": "<crate>/tests/.../<file>.rs::<fn>"}]}`)
from every variant, whatever the draw: each `#[test] fn` goes with its attributes and doc comments, and the rest of its
file stays, helpers included (a helper left unused only warns). It goes after the draw and the thinning, so neither
moves. A test whose file the draw or the thinning already took is recorded as absent there. Its held-out copy is its
file with only the listed tests left in it (or the whole file, when the draw held the file out).

--renames applies a renaming dose (`{"renames": [{"d", "kind", "file", "old", "new", "count", "line"?}]}`) to the
snapshot before the variants are planned: entries in order, each replacing exactly `count` occurrences (with `line`,
only on the one line containing it), and any other count stops the build. Doc entries drop out of stripped with docs/.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGE = "lid-cost-eval-executor-rust:2.1.323"
IDENTITY = ("Lab Owner", "owner@example.invalid")  # the workspaces' neutral git identity (trajectory.GIT_IDENTITY)
DATE = "2026-01-01T00:00:00+00:00"  # a fixed date, so a variant's commit hash depends only on its files
HELD_OUT_SHARE = 0.15
RATIO = 0.6
AGENT_FILES = ("AGENTS.md", "CLAUDE.md", "GEMINI.md")
LID_MARKERS = ("@spec", "docs/intent")


# --------------------------------------------------------------------------------------------- the source tree


@dataclass
class Tree:
    commit: str
    files: dict[str, bytes]
    symlinks: dict[str, str] = field(default_factory=dict)
    executables: set[str] = field(default_factory=set)


@dataclass
class Variant:
    name: str
    files: dict[str, bytes]
    symlinks: dict[str, str]
    executables: set[str]
    report: dict = field(default_factory=dict)
    vcs: str = "git"  # "jj": loaded as a colocated jj repository, as the project's own instructions expect


def _git(repo: Path, *args: str, stdin: bytes | None = None) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], input=stdin, check=True, capture_output=True).stdout


def read_tree(repo: Path | str, commit: str) -> Tree:
    """Every tracked file at the commit: regular files, symlinks (as their targets), and which are executable."""
    repo = Path(repo)
    commit = _git(repo, "rev-parse", commit).decode().strip()
    entries = []
    for rec in _git(repo, "ls-tree", "-r", "-z", commit).split(b"\0"):
        if not rec:
            continue
        meta, path = rec.split(b"\t", 1)
        mode, kind, sha = meta.decode().split()
        if kind == "blob":
            entries.append((mode, sha, path.decode()))
    out = _git(repo, "cat-file", "--batch", stdin="".join(f"{sha}\n" for _, sha, _ in entries).encode())
    tree, i = Tree(commit=commit, files={}), 0
    for mode, sha, path in entries:
        nl = out.index(b"\n", i)
        size = int(out[i:nl].split()[2])
        data = out[nl + 1:nl + 1 + size]
        i = nl + 1 + size + 1
        if mode == "120000":
            tree.symlinks[path] = data.decode()
        else:
            tree.files[path] = data
            if mode == "100755":
                tree.executables.add(path)
    return tree


def _text(data: bytes) -> str | None:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _lines(data: bytes) -> int:
    return data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)


# ------------------------------------------------------------------------------------------------- spec IDs


def spec_id_pattern(tree: Tree) -> re.Pattern:
    """Spec IDs as the project's specs write them (**PREFIX-NNN**): their prefixes, then three or more digits and an
    optional letter."""
    prefixes = set()
    for path, data in tree.files.items():
        if path.endswith("-specs.md") and (text := _text(data)):
            prefixes |= {m.group(1) for m in re.finditer(r"\*\*([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*?)-\d{3,}[a-z]?\*\*", text)}
    if not prefixes:
        return re.compile(r"(?!)")
    alt = "|".join(re.escape(p) for p in sorted(prefixes, key=lambda p: (-len(p), p)))
    return re.compile(rf"\b(?:{alt})-\d{{3,}}[a-z]?\b")


_COMMENT = ("//", "/*", "*")


def strip_spec_ids(text: str, pattern: re.Pattern, *, hash_comments: bool = False) -> tuple[str, dict[str, int]]:
    """Remove `@spec` annotations and every other citation of a spec ID, keeping the prose around them.

    A line that is only an annotation goes. An annotation at the end of prose or code goes, and the rest stays. A
    citation goes with what only frames it: parentheses around it ("(X-001)", "(X-001 amended)"), a lead-in ("see",
    "per"), a label colon ("X-001: ..."); "X-001's rule" becomes "the rule". A comment left with no words goes.
    With hash_comments (Python), comments start with `#`, and a docstring line that is only an annotation goes too."""
    ident = pattern.pattern
    lst = rf"(?:{ident})(?:\s*(?:,|\band\b|&|/)\s*(?:{ident}))*"
    counts = {"annotation lines": 0, "lines changed": 0, "lines dropped": 0}
    out = []
    for line in text.splitlines(keepends=True):
        if "@spec" not in line and not pattern.search(line):
            out.append(line)
            continue
        body, nl = (line[:-1], "\n") if line.endswith("\n") else (line, "")
        stripped = body.strip()
        if re.match(r"^(?:#+:?\s*)?@spec\b" if hash_comments else r"^(?:///|//!|//)\s*@spec\b", stripped):
            counts["annotation lines"] += 1
            continue
        new = re.sub(rf"\s*@spec\s+{lst}", "", body)
        new = re.sub(r"\s*@spec\b\s*$", "", new)  # its IDs wrapped to the next line, which goes as a citation

        def paren(m: re.Match) -> str:
            rest = re.sub(r"[^\w\s]", " ", m.group("rest") or "").split()
            return "" if len(rest) <= 2 else m.group(0).replace(m.group("ids"), "").replace("( ", "(")

        new = re.sub(rf"\s*\(\s*(?:see\s+|per\s+|cf\.?\s+)?(?P<ids>{lst})(?P<rest>[^()]*)\)", paren, new)
        new = re.sub(rf"{lst}'s\b", "the", new)
        new = re.sub(rf"{lst}\s*:\s*", "", new)
        new = re.sub(rf"\b(?:[Ss]ee|[Pp]er|cf\.?|as in|under)\s+{lst}", "", new)
        new = re.sub(lst, "", new)
        lead = len(new) - len(new.lstrip())
        rest = re.sub(r" {2,}", " ", new[lead:])
        rest = re.sub(r" +([,.;:)])", r"\1", rest).replace("()", "").replace("( )", "")
        new = (new[:lead] + rest).rstrip()
        is_comment = stripped.startswith("#" if hash_comments else _COMMENT)
        if is_comment:
            m = re.match(r"^(\s*#+:?)\s*(.*)$" if hash_comments else r"^(\s*(?:///|//!|//|/\*|\*))\s*(.*)$", new)
            head, words = m.group(1), m.group(2)
            words = re.sub(r"[\s\u2014\u2013:;,]+$", "", re.sub(r"^[\s\u2014\u2013:;,.]+", "", words))
            if not re.search(r"\w", words):
                counts["lines dropped"] += 1
                continue
            new = f"{head} {words}"
        if not is_comment:
            # a trailing comment left empty
            new = re.sub(r"\s*#+\s*[.,;:]*\s*$" if hash_comments else r"\s*//[!/]?\s*[.,;:]*\s*$", "", new)
            if not new.strip() and stripped:
                counts["lines dropped"] += 1
                continue
        counts["lines changed"] += 1
        out.append(new + nl)
    return "".join(out), counts


# ------------------------------------------------------------------------------------------------ test files


def cfg_test_lines(text: str) -> int:
    """Lines of `#[cfg(test)]` items in a source file: from the attribute to the item's end (its closing brace, or
    its semicolon), skipping braces inside strings, character literals, and comments."""
    total, i = 0, 0
    while (k := text.find("#[cfg(test)]", i)) >= 0:
        end = _item_end(text, k + len("#[cfg(test)]"))
        total += text.count("\n", k, end) + 1
        i = end
    return total


def _item_end(text: str, i: int) -> int:
    depth, n = 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith("//", i):
            i = text.find("\n", i)
            i = n if i < 0 else i
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        m = re.match(r'b?r(#*)"', text[i:i + 12])
        if m:
            close = '"' + m.group(1)
            j = text.find(close, i + len(m.group(0)))
            i = n if j < 0 else j + len(close)
            continue
        if c == '"' or text.startswith('b"', i):
            j = i + (2 if c == "b" else 1)
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            i = j + 1
            continue
        if c == "'":
            if text.startswith("'\\", i):
                j = text.find("'", i + 2)
                i = n if j < 0 else j + 1
                continue
            if i + 2 < n and text[i + 2] == "'":
                i += 3
                continue
            i += 1  # a lifetime
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        elif c == ";" and depth == 0:
            return i
        i += 1
    return n


def _is_test_file(path: str) -> bool:
    return bool(re.fullmatch(r"crates/[^/]+/tests/[^/]+\.rs", path)
                or re.fullmatch(r"crates/[^/]+/tests/[^/]+/(?!main\.rs$)[^/]+\.rs", path))


def test_files(files) -> list[str]:
    """Test files that can be removed whole: a test target of its own under crates/*/tests/, or a module directly in
    one of its directories (not that directory's main.rs, and not a helper module's own folder, such as common/)."""
    return sorted(p for p in files if _is_test_file(p))


def _stratum(path: str) -> str:
    return path.rsplit("/", 1)[0]


def _by_stratum(paths) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for p in sorted(paths):
        out.setdefault(_stratum(p), []).append(p)
    return out


READS_DOCS = re.compile(r'(?:include_(?:str|bytes)!|read_to_string)\s*\(\s*"[^"]*\bdocs/')


def reads_docs(text: str) -> bool:
    """A test that reads the project's docs (checking a design table against the code, say) can't build without them."""
    return bool(READS_DOCS.search(text))


def choose_held_out(tree: Tree, *, share: float = HELD_OUT_SHARE, seed: str) -> list[str]:
    """A seeded random share of each directory's test files, rounded half up. Files that read the docs are never
    held out: they would fail to build against the stripped variant for want of the docs, not of the behaviour."""
    held = []
    eligible = [p for p in test_files(tree.files) if not reads_docs(tree.files[p].decode(errors="replace"))]
    for stratum, paths in _by_stratum(eligible).items():
        k = int(share * len(paths) + 0.5)
        held += random.Random(f"{seed}|held-out|{stratum}").sample(paths, k)
    return sorted(held)


def _drop_modules(files: dict[str, bytes], removed: list[str]) -> None:
    """Take each removed module's `mod` line (and attributes just above it) out of its directory's main.rs."""
    for path in removed:
        if not re.fullmatch(r"crates/[^/]+/tests/[^/]+/[^/]+\.rs", path):
            continue  # a test target of its own: nothing declares it
        main = f"{_stratum(path)}/main.rs"
        if main not in files:
            continue
        stem = Path(path).stem
        lines = files[main].decode().splitlines(keepends=True)
        for k, line in enumerate(lines):
            if re.fullmatch(rf"\s*(?:pub\s+)?mod\s+{re.escape(stem)}\s*;\s*", line.rstrip("\n")):
                j = k
                while j > 0 and lines[j - 1].strip().startswith("#["):
                    j -= 1
                del lines[j:k + 1]
                break
        files[main] = "".join(lines).encode()


def drop_doc_tests(files: dict[str, bytes]) -> list[str]:
    """Remove the tests that read the docs: whole test files, and single `#[test]` functions in source files (with
    their doc comments and attributes). Returns what went, as paths or path::function."""
    gone = []
    for p in test_files(files):
        if reads_docs(files[p].decode(errors="replace")):
            gone.append(p)
            del files[p]
    _drop_modules(files, list(gone))
    for p in sorted(files):
        if not p.endswith(".rs") or not p.startswith("crates/"):
            continue
        text = files[p].decode(errors="replace")
        while (m := READS_DOCS.search(text)):
            attr = text.rfind("#[test]", 0, m.start())
            fn = re.compile(r"\bfn\s+(\w+)").search(text, attr) if attr >= 0 else None
            if fn is None or fn.start() > m.start():
                raise ValueError(f"{p}: reads the docs outside a test function")
            end = _item_end(text, fn.end())
            start = text.rfind("\n", 0, attr) + 1
            while start > 0:  # the item's doc comments and other attributes above it
                prev = text.rfind("\n", 0, start - 1) + 1
                if not text[prev:start].strip().startswith(("///", "#[", "//")):
                    break
                start = prev
            stop = text.find("\n", end)
            text = text[:start] + text[(len(text) if stop < 0 else stop + 1):]
            gone.append(f"{p}::{fn.group(1)}")
        files[p] = text.encode()
    return sorted(gone)


# ------------------------------------------------------------------------------------- single test functions


_RAW_STRING = re.compile(r'[bc]?r(#*)"')


def mask_rust(text: str, *, comments_only: bool = False) -> str:
    """The text with every comment (nested block comments too), string (raw and byte strings too), and character
    literal blanked to spaces, keeping newlines, so what is left is the code at the same offsets. Lifetimes and loop
    labels stay code. With comments_only, strings and characters stay (a name in a format string is a use of it)."""
    out, n, i = list(text), len(text), 0

    def blank(a: int, b: int) -> None:
        for k in range(a, b):
            if out[k] != "\n":
                out[k] = " "

    while i < n:
        c = text[i]
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
        elif text.startswith("/*", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if text.startswith("/*", j):
                    depth, j = depth + 1, j + 2
                elif text.startswith("*/", j):
                    depth, j = depth - 1, j + 2
                else:
                    j += 1
        elif c in "rbc" and (i == 0 or not (text[i - 1].isalnum() or text[i - 1] == "_")) and (m := _RAW_STRING.match(text, i)):
            close = '"' + m.group(1)
            j = text.find(close, m.end())
            j = n if j < 0 else j + len(close)
        elif c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            j = min(n, j + 1)
        elif c == "'" and text.startswith("'\\", i):
            j = text.find("'", i + 3)  # past the escaped character, which may itself be a quote
            j = n if j < 0 else j + 1
        elif c == "'" and i + 2 < n and text[i + 2] == "'" and text[i + 1] != "\n":
            j = i + 3
        else:
            i += 1  # code, a lifetime, or a label
            continue
        if not comments_only or text.startswith(("//", "/*"), i):
            blank(i, j)
        i = j
    return "".join(out)


def _match_forward(m: str, i: int, open_: str, close: str) -> int:
    depth = 0
    for j in range(i, len(m)):
        if m[j] == open_:
            depth += 1
        elif m[j] == close:
            depth -= 1
            if depth == 0:
                return j
    raise ValueError(f"unbalanced {open_!r} at offset {i}")


def _match_back(m: str, i: int, open_: str, close: str) -> int:
    depth = 0
    for j in range(i, -1, -1):
        if m[j] == close:
            depth += 1
        elif m[j] == open_:
            depth -= 1
            if depth == 0:
                return j
    return -1


_TEST_ATTR = re.compile(r"#\s*\[\s*test\s*\]")
_FN_HEAD = re.compile(r"(?:pub(?:\s*\([^)]*\))?\s+)?(?:(?:const|async|unsafe)\s+)*(?:extern\s+)?fn\s+(\w+)")


def _attribute_before(m: str, p: int) -> int:
    """The start of an attribute that ends just before p (only spaces between), or -1."""
    before = m[:p].rstrip()
    if not before.endswith("]"):
        return -1
    o = _match_back(m, len(before) - 1, "[", "]")
    if o < 0:
        return -1
    hash_ = m[:o].rstrip()
    return len(hash_) - 1 if hash_.endswith("#") else -1


def _attached_start(text: str, m: str, p: int) -> int:
    """Where the item whose `#[test]` is at p begins: back over the attributes, doc comments and comment lines
    attached to it, stopping at a blank line or code."""
    while True:
        line_start = m.rfind("\n", 0, p) + 1
        if m[line_start:p].strip():
            a = _attribute_before(m, p)  # another attribute earlier on the same line
            if a < 0 or a < line_start:
                return p
            p = a
            continue
        if line_start == 0:
            return 0
        prev = m.rfind("\n", 0, line_start - 1) + 1
        if not text[prev:line_start - 1].strip():
            return line_start  # a blank line
        if not m[prev:line_start - 1].strip():
            p = prev  # a comment line
            continue
        a = _attribute_before(m, line_start - 1)
        if a < 0:
            return line_start  # code
        p = a


def rust_test_fns(text: str) -> list[tuple[str, int, int]]:
    """Each `#[test]` function in a Rust file, in order: its name and the span that removes it whole, from its
    first attached attribute, doc comment or comment line to the end of its closing brace's line. Braces, `#[test]`
    and `fn` inside strings, character literals, comments and raw strings don't count."""
    m = mask_rust(text)
    out = []
    for a in _TEST_ATTR.finditer(m):
        k = a.end()
        while True:  # past any later attributes
            while k < len(m) and m[k].isspace():
                k += 1
            h = re.match(r"#\s*\[", m[k:])
            if not h:
                break
            k = _match_forward(m, k + h.end() - 1, "[", "]") + 1
        head = _FN_HEAD.match(m, k)
        if not head:
            continue
        body, semi = m.find("{", head.end()), m.find(";", head.end())
        if body < 0 or 0 <= semi < body:
            continue
        close = _match_forward(m, body, "{", "}")
        eol = m.find("\n", close)
        eol = len(m) if eol < 0 else eol
        end = (eol + 1 if eol < len(m) else eol) if not m[close + 1:eol].strip() else close + 1
        out.append((head.group(1), _attached_start(text, m, a.start()), end))
    return out


def _cut(text: str, spans: list[tuple[int, int]]) -> str:
    """Remove the spans, last first, leaving no run of blank lines where one was taken out between two."""
    for start, end in sorted(spans, reverse=True):
        before, after = text[:start], text[end:]
        blank_before = not before or re.search(r"(?:^|\n)[ \t]*\n$", before)
        if blank_before and (b := re.match(r"[ \t]*\n", after)):
            after = after[b.end():]
        elif blank_before and before and not after.strip():
            before = re.sub(r"\n[ \t]*\n$", "\n", before)
        text = before + after
    return text


def remove_test_fns(text: str, names) -> str:
    """The file without the named `#[test]` functions (each with its attributes and doc comments) and with all
    else as it was. A name that isn't a test function here is an error."""
    fns = rust_test_fns(text)
    found = {name: (s, e) for name, s, e in fns}
    missing = [n for n in names if n not in found]
    if missing:
        raise ValueError(f"no #[test] fn {', '.join(missing)}")
    twice = [n for n in set(names) if [f[0] for f in fns].count(n) > 1]
    if twice:
        raise ValueError(f"more than one #[test] fn {', '.join(sorted(twice))}")
    return _cut(text, [found[n] for n in set(names)])


_RULE = re.compile(r"\s*//\s*[-=*#~]{4,}")
_RULE_ENDS = re.compile(r"^\s*[-=*#~]{2,}\s*|\s*[-=*#~]{2,}\s*$")


def _plain_comment(line: str) -> bool:
    s = line.strip()
    return s.startswith("//") and not s.startswith("//!") and not (s.startswith("///") and not s.startswith("////"))


def _line_starts(text: str) -> list[int]:
    return [0] + [i + 1 for i, c in enumerate(text) if c == "\n"]


def rust_banners(text: str) -> list[dict]:
    """The section banners of a Rust file: free-standing blocks of plain `//` lines (a blank line, the file's start or
    an opening brace above; a blank line or the end below) with a rule line (`// ----`, `// ====`) in them. Each has
    its span, its title (its first line that isn't only a rule, without the rule), and where the group it heads ends:
    at the next banner at its depth, the end of the block it sits in, or the end of the file."""
    m = mask_rust(text)
    starts = _line_starts(text)
    lines, mlines = text.split("\n"), m.split("\n")
    depth_at, d = [], 0
    for line in mlines:
        depth_at.append(d)
        d += line.count("{") - line.count("}")

    def comment_line(k: int) -> bool:
        return _plain_comment(lines[k]) and not mlines[k].strip()

    found, k = [], 0
    while k < len(lines):
        if not comment_line(k):
            k += 1
            continue
        j = k
        while j < len(lines) and comment_line(j):
            j += 1
        above = k == 0 or not lines[k - 1].strip() or mlines[k - 1].rstrip().endswith("{")
        below = j >= len(lines) or not lines[j].strip()
        if above and below and any(_RULE.match(lines[i]) for i in range(k, j)):
            titles = [_RULE_ENDS.sub("", lines[i].strip()[2:]).strip() for i in range(k, j)]
            found.append({"line": k, "start": starts[k], "end": starts[j] if j < len(starts) else len(text),
                          "title": next((t for t in titles if t), ""), "depth": depth_at[k]})
        k = j
    for b in found:
        end = next((starts[i] for i in range(b["line"] + 1, len(depth_at)) if depth_at[i] < b["depth"]), len(text))
        later = [o["start"] for o in found if o["start"] > b["start"] and o["depth"] == b["depth"]]
        b["group_end"] = min([end, *later])
    return found


_ITEM = re.compile(r"(?m)^[ \t]*(pub(?:\s*\([^)]*\))?\s+)?(?:(?:const|async|unsafe|extern)\s+)*"
                   r"(fn|const|static|struct|enum|type|union)\s+(?:mut\s+)?(\w+)")
_USE = re.compile(r"(?m)^[ \t]*(pub(?:\s*\([^)]*\))?\s+)?use\s")


def _item_close(m: str, i: int, kind: str) -> int:
    depth = 0
    for j in range(i, len(m)):
        c = m[j]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0 and c == "}" and kind in ("fn", "struct", "enum", "union"):
                return j
        elif c == ";" and depth == 0:
            return j
    raise ValueError(f"no end to the {kind} at offset {i}")


def _whole_lines(m: str, close: int) -> int:
    """Where a span whose last character is at `close` stops: past its line's end when only whitespace follows."""
    eol = m.find("\n", close)
    eol = len(m) if eol < 0 else eol
    return (eol + 1 if eol < len(m) else eol) if not m[close + 1:eol].strip() else close + 1


def _use_tree(s: str, i: int) -> tuple[dict, int]:
    start, segs = i, []
    while True:
        while i < len(s) and s[i].isspace():
            i += 1
        if s.startswith("{", i):
            close = _match_forward(s, i, "{", "}")
            children, j = [], i + 1
            while True:
                while j < close and (s[j].isspace() or s[j] == ","):
                    j += 1
                if j >= close:
                    break
                child, j = _use_tree(s, j)
                children.append(child)
            return {"kind": "group", "start": start, "end": close + 1, "children": children}, close + 1
        if s.startswith("*", i):
            return {"kind": "glob", "start": start, "end": i + 1}, i + 1
        seg = re.compile(r"r#\w+|\w+").match(s, i)
        if not seg:
            raise ValueError(f"can't read the use tree at {s[i:i + 20]!r}")
        segs.append(seg.group(0))
        i = j = seg.end()
        while j < len(s) and s[j].isspace():
            j += 1
        if s.startswith("::", j):
            i = j + 2
            continue
        alias = re.compile(r"\s+as\s+(\w+)").match(s, i)
        if alias:
            return {"kind": "leaf", "start": start, "end": alias.end(), "name": alias.group(1)}, alias.end()
        name = segs[-2] if segs[-1] == "self" and len(segs) > 1 else segs[-1]
        return {"kind": "leaf", "start": start, "end": i, "name": name}, i


def _use_root(stmt: str) -> dict:
    m = mask_rust(stmt)
    return _use_tree(m, re.search(r"\buse\s", m).end())[0]


def _use_leaves(node: dict) -> list[str]:
    if node["kind"] == "leaf":
        return [node["name"]] if node["name"] not in ("self", "_") else []
    return [n for c in node.get("children", []) for n in _use_leaves(c)]


def _plan_use(node: dict, names: set, s: str, cuts: list) -> bool:
    """Whether the node goes whole; if not, the cuts that take the named leaves out of it, with their commas."""
    if node["kind"] == "leaf":
        return node["name"] in names
    if node["kind"] == "glob":
        return False
    kids, gone = node["children"], []
    for c in kids:
        sub: list = []
        gone.append(_plan_use(c, names, s, sub))
        if not gone[-1]:
            cuts.extend(sub)
    if all(gone):
        return bool(kids)
    last_kept = max(i for i, g in enumerate(gone) if not g)
    for i, c in enumerate(kids[:last_kept]):
        if gone[i]:  # up to the next element on its line, past its comma
            k = c["end"]
            while k < len(s) and s[k] in " \t":
                k += 1
            if s.startswith(",", k):
                k += 1
                while k < len(s) and s[k] in " \t":
                    k += 1
            cuts.append((c["start"], k))
    if last_kept < len(kids) - 1:  # a run at the end: from the last kept element's end
        cuts.append((kids[last_kept]["end"], kids[-1]["end"]))
    return False


def drop_use_names(stmt: str, names) -> str:
    """A `use` statement without the leaves that bring the given local names in (an alias's name, not its
    target's), with their commas; a group left empty goes, and a statement left empty becomes ''."""
    cuts: list = []
    if _plan_use(_use_root(stmt), set(names), stmt, cuts):
        return ""
    for a, b in sorted(cuts, reverse=True):
        stmt = stmt[:a] + stmt[b:]
    return "\n".join(line for line in stmt.split("\n") if line.strip())


def _top_level_names(text: str) -> list[tuple[str, str, tuple[int, int]]]:
    """What a file defines or imports at its top level that a dead-code or unused-import warning could name: its
    private items (fn, const, static, struct, enum, type) and the names its private `use` statements bring in, each
    with the span that defines it (an item from its attached docs and attributes; a use, its statement)."""
    m = mask_rust(text)
    marks = sorted([(x.start(), "item", x) for x in _ITEM.finditer(m)] + [(x.start(), "use", x) for x in _USE.finditer(m)],
                   key=lambda t: t[0])
    out, depth, at = [], 0, 0
    for pos, what, x in marks:
        depth += m.count("{", at, pos) - m.count("}", at, pos)
        at = pos
        if depth != 0 or x.group(1):
            continue
        if what == "use":
            span = (x.start() + len(x.group(0)) - len(x.group(0).lstrip()), m.find(";", x.end()) + 1)
            out += [("use", name, span) for name in _use_leaves(_use_root(text[span[0]:span[1]]))]
        else:
            kind, name = x.group(2), x.group(3)
            kw = x.start() + len(x.group(0)) - len(x.group(0).lstrip())
            close = _item_close(m, x.end(), kind)
            out.append((kind, name, (_attached_start(text, m, kw), _whole_lines(m, close))))
    return out


def _refs(code: str, name: str, span: tuple[int, int]) -> int:
    word = re.compile(rf"(?<!\w){re.escape(name)}(?!\w)")
    return sum(1 for w in word.finditer(code) if not span[0] <= w.start() < span[1])


def _edit(text: str, ops: list) -> str:
    """Apply cuts ((start, end, None)) and replacements ((start, end, new)), last first."""
    for start, end, new in sorted(ops, key=lambda o: o[0], reverse=True):
        text = _cut(text, [(start, end)]) if new is None else text[:start] + new + text[end:]
    return text


def remove_tests_and_traces(text: str, names) -> tuple[str, dict]:
    """The file without the named `#[test]` functions and without what only they left behind, so nothing in it
    points at them and the compiler warns of nothing new: a section banner that headed tests and has none left under
    it (or headed code and has none left), an imported name only they used (the rest of its `use` stays), and a
    private helper item only they, or helpers going with them, used. Returns the file and the traces, by kind."""
    remove_test_fns(text, names)  # each name must be one test here
    names, fns = set(names), rust_test_fns(text)
    traces = {"banners": [], "imports": [], "items": []}
    spans = [(s, e) for n, s, e in fns if n in names]
    m = mask_rust(text)
    had_code = {}
    for b in rust_banners(text):
        under = [n for n, s, _ in fns if b["end"] <= s < b["group_end"]]
        had_code[b["title"]] = bool(m[b["end"]:b["group_end"]].strip())
        if under and all(n in names for n in under):
            spans.append((b["start"], b["end"]))
            traces["banners"].append(b["title"])
    out = _cut(text, spans)
    code = mask_rust(text, comments_only=True)
    baseline = {name: _refs(code, name, span) for _, name, span in _top_level_names(text)}
    while True:
        code = mask_rust(out, comments_only=True)
        dead = [(kind, name, span) for kind, name, span in _top_level_names(out)
                if baseline.get(name, 0) > 0 and _refs(code, name, span) == 0]
        if not dead:
            break
        ops, uses = [], {}
        for kind, name, span in dead:
            if kind == "use":
                uses.setdefault(span, set()).add(name)
                traces["imports"].append(name)
            else:
                ops.append((span[0], span[1], None))
                traces["items"].append(f"{kind} {name}")
        mo = mask_rust(out)
        for (s, e), gone in uses.items():
            new = drop_use_names(out[s:e], gone)
            ops.append((out.rfind("\n", 0, s) + 1, _whole_lines(mo, e - 1), None) if not new else (s, e, new))
        out = _edit(out, ops)
    mo = mask_rust(out)
    empty = [b for b in rust_banners(out) if had_code.get(b["title"]) and not mo[b["end"]:b["group_end"]].strip()]
    if empty:
        out = _cut(out, [(b["start"], b["end"]) for b in empty])
        traces["banners"] += [b["title"] for b in empty]
    return out, {k: sorted(v) for k, v in traces.items()}


def keep_test_fns(text: str, names) -> str:
    """The file with every `#[test]` function but the named ones taken out: those tests and the file's helpers."""
    found = rust_test_fns(text)
    missing = [n for n in names if n not in {f[0] for f in found}]
    if missing:
        raise ValueError(f"no #[test] fn {', '.join(missing)}")
    return _cut(text, [(s, e) for name, s, e in found if name not in names])


# ------------------------------------------------------------------------------------------ forced holdouts


def load_holdouts(path: Path | str) -> list[dict]:
    """The forced holdouts: each test as listed, its file (with the `crates/` its listing leaves off) and function."""
    out = []
    for t in json.loads(Path(path).read_text(encoding="utf-8"))["tests"]:
        file, fn = t["test"].split("::")
        out.append({"test": t["test"], "change": t["change"], "status": t["status"],
                    "path": file if file.startswith("crates/") else f"crates/{file}", "fn": fn})
    return out


def remove_forced_holdouts(variants: dict[str, Variant], holdouts: list[dict], *, tree: Tree,
                           held_out: list[str]) -> list[dict]:
    """Take each listed test function out of every variant that still has its file, with the traces only those
    tests left (a banner over no test, an import or helper only they used; see remove_tests_and_traces), after the
    draw and the thinning (so neither moves), and count the variants' test lines again. Each variant's report lists
    the traces taken, per file, as `forced_holdout_traces`. Returns the record: per test, the variants it was
    removed from, those whose file was already gone and why, and where its held-out copy is."""
    for h in holdouts:
        if h["path"] not in tree.files:
            raise ValueError(f"{h['test']}: {h['path']} isn't in the snapshot")
        if h["fn"] not in {n for n, _, _ in rust_test_fns(tree.files[h["path"]].decode())}:
            raise ValueError(f"{h['test']}: no #[test] fn {h['fn']} in {h['path']}")
    record = []
    present = {name: {p: {n for n, _, _ in rust_test_fns(v.files[p].decode())} for p in {h["path"] for h in holdouts}
                      if p in v.files} for name, v in variants.items()}
    for h in holdouts:
        r = {"test": h["test"], "change": h["change"], "status": h["status"], "removed_from": [], "absent_in": [],
             "absent_why": {}, "held_out_copy": f"held-out/{h['path']}"}
        for name, v in variants.items():
            tests = present[name].get(h["path"])
            if tests is not None and h["fn"] in tests:
                r["removed_from"].append(name)
                continue
            r["absent_in"].append(name)
            r["absent_why"][name] = ("test already removed" if tests is not None
                                     else "held out by the draw" if h["path"] in held_out
                                     else "thinned" if h["path"] in v.report.get("tests_thinned", [])
                                     else "reads the docs" if h["path"] in v.report.get("tests_reading_docs", [])
                                     else "removed")
        record.append(r)
    for name, v in variants.items():
        v.report["forced_holdout_traces"] = {}
        for path, tests in sorted(present[name].items()):
            gone = [h["fn"] for h in holdouts if h["path"] == path and h["fn"] in tests]
            if not gone:
                continue
            text, traces = remove_tests_and_traces(v.files[path].decode(), gone)
            v.files[path] = text.encode()
            if any(traces.values()):
                v.report["forced_holdout_traces"][path] = traces
    for v in variants.values():
        v.report.update(source_lines=_source_lines(v.files), test_lines=_test_lines(v.files))
        v.report["ratio"] = round(v.report["test_lines"] / max(1, v.report["source_lines"]), 3)
    return record


# --------------------------------------------------------------------------------------------- the renames


def load_renames(path: Path | str) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["renames"]


def apply_renames(tree: Tree, renames: list[dict]) -> list[dict]:
    """Apply a renaming dose to the snapshot, in order: each entry replaces `old` with `new` in its file exactly
    `count` times, or, with `line`, on the one line that contains that text. Any other count, an anchor on other
    than one line, or a missing file stops it. Returns what was applied."""
    applied = []
    for k, r in enumerate(renames):
        where = f"rename {k} ({r['d']}, {r['kind']}, {r['file']})"
        if r["file"] not in tree.files:
            raise ValueError(f"{where}: no such file in the snapshot")
        text = tree.files[r["file"]].decode("utf-8")
        if "line" in r:
            lines = text.split("\n")
            at = [i for i, line in enumerate(lines) if r["line"] in line]
            if len(at) != 1:
                raise ValueError(f"{where}: the line anchor {r['line']!r} is on {len(at)} lines, not one")
            got = lines[at[0]].count(r["old"])
            lines[at[0]] = lines[at[0]].replace(r["old"], r["new"])
            new = "\n".join(lines)
        else:
            got = text.count(r["old"])
            new = text.replace(r["old"], r["new"])
        if got != r["count"]:
            raise ValueError(f"{where}: {r['old'][:60]!r} found {got} times, not {r['count']}")
        tree.files[r["file"]] = new.encode("utf-8")
        applied.append({"d": r["d"], "kind": r["kind"], "file": r["file"], "count": r["count"]})
    return applied


def _source_lines(files: dict[str, bytes]) -> int:
    n = 0
    for p, d in files.items():
        if p.endswith(".rs") and "/tests/" not in p and p.startswith("crates/"):
            n += _lines(d) - cfg_test_lines(d.decode(errors="replace"))
    return n


def _test_lines(files: dict[str, bytes]) -> int:
    n = sum(_lines(d) for p, d in files.items() if p.endswith(".rs") and "/tests/" in p and p.startswith("crates/"))
    return n + sum(cfg_test_lines(d.decode(errors="replace")) for p, d in files.items()
                   if p.endswith(".rs") and "/tests/" not in p and p.startswith("crates/"))


def thin_tests(files: dict[str, bytes], *, ratio: float, seed: str) -> list[str]:
    """Test files to remove so test lines come to about `ratio` times the non-test source lines. Each directory's
    test files get a share of the budget in proportion to their lines, and are taken in a seeded random order, each
    kept if it brings the directory closer to its share."""
    candidates = test_files(files)
    fixed = _test_lines(files) - sum(_lines(files[p]) for p in candidates)
    budget = max(0.0, ratio * _source_lines(files) - fixed)
    total = sum(_lines(files[p]) for p in candidates) or 1
    removed = []
    for stratum, paths in _by_stratum(candidates).items():
        share = budget * sum(_lines(files[p]) for p in paths) / total
        order = list(paths)
        random.Random(f"{seed}|thin|{stratum}").shuffle(order)
        kept = 0
        for p in order:
            n = _lines(files[p])
            if abs(kept + n - share) < abs(kept - share):
                kept += n
            else:
                removed.append(p)
    return sorted(removed)


# ---------------------------------------------------------------------------------------------- the variants


README_LID = re.compile(r"Linked-Intent|linked-intent|\bLID\b|jszmajda/lid|@spec|docs/intent|\]\(docs/|AGENTS\.md|CLAUDE\.md"
                        r"|spec-test-coverage|\barrow\b(?!\s+keys?\b)", re.I)


def _readme(text: str) -> tuple[str, int]:
    """The README without what describes LID: each paragraph that mentions it, LID, its specs, the docs, or the agent
    instruction files, and each such line of a code block; then any heading left with nothing under it. A section
    named for the arrow keeps its remaining content under "Testing"."""
    blocks = [b for b in re.split(r"\n\s*\n", text.strip("\n"))]
    kept, dropped = [], 0
    for b in blocks:
        if b.startswith("```"):
            lines = b.split("\n")
            inner = [l for l in lines[1:-1] if not README_LID.search(l)]
            dropped += len(lines) - 2 - len(inner)
            if inner:
                kept.append("\n".join([lines[0], *inner, lines[-1]]))
        elif b.startswith("#"):
            kept.append("## Testing" if README_LID.search(b) and b.startswith("## ") else b)
        elif re.match(r"\s*(?:[-*+]|\d+\.)\s", b):
            # a list: each item on its own, with any lines that continue it
            items = re.split(r"\n(?=\s*(?:[-*+]|\d+\.)\s)", b)
            left = [i for i in items if not README_LID.search(i)]
            dropped += len(items) - len(left)
            if left:
                kept.append("\n".join(left))
        elif README_LID.search(b):
            dropped += 1
        else:
            kept.append(b)
    out = []
    for k, b in enumerate(kept):
        level = len(b) - len(b.lstrip("#")) if b.startswith("#") else 0
        nxt = kept[k + 1] if k + 1 < len(kept) else None
        nxt_level = len(nxt) - len(nxt.lstrip("#")) if nxt and nxt.startswith("#") else 0
        if level and (nxt is None or (nxt_level and nxt_level <= level)):
            continue  # a heading with nothing left under it
        out.append(b)
    return "\n\n".join(out) + "\n", dropped


def plan_variants(tree: Tree, *, held_out: list[str], seed: str, ratio: float = RATIO) -> dict[str, Variant]:
    base = {p: d for p, d in tree.files.items() if p not in held_out}
    _drop_modules(base, held_out)
    full = Variant("full", dict(base), dict(tree.symlinks), set(tree.executables) - set(held_out),
                   {"held_out": sorted(held_out)}, vcs="jj")
    lid = Variant("lid", dict(base), dict(tree.symlinks), set(full.executables), dict(full.report), vcs="jj")

    files = dict(base)
    gone = {"docs": [], "agent files": [], "lid tooling": []}
    for p in list(files):
        top = p.split("/", 1)[0]
        if top == "docs":
            gone["docs"].append(p)
        elif p in AGENT_FILES or top == ".claude":
            gone["agent files"].append(p)
        elif not p.startswith("crates/") and not p.endswith(".md") and (t := _text(files[p])) and any(m in t for m in LID_MARKERS):
            gone["lid tooling"].append(p)
        else:
            continue
        del files[p]
    symlinks = {}
    for p, target in tree.symlinks.items():
        resolved = os.path.normpath(os.path.join(os.path.dirname(p), target))
        if p in AGENT_FILES or resolved in AGENT_FILES or resolved.split("/", 1)[0] in ("docs", ".claude"):
            gone["agent files"].append(p)
        else:
            symlinks[p] = target
    pattern = spec_id_pattern(tree)
    stripped_counts = {"annotation lines": 0, "lines changed": 0, "lines dropped": 0, "files": 0}
    readme_paragraphs = 0
    for p, d in list(files.items()):
        t = _text(d)
        if t is None:
            continue
        if p == "README.md":
            t, readme_paragraphs = _readme(t)
        new, counts = strip_spec_ids(t, pattern)
        if new != _text(d):
            stripped_counts["files"] += 1
            for k, v in counts.items():
                stripped_counts[k] += v
            files[p] = new.encode()
    reading_docs = drop_doc_tests(files)
    thinned = thin_tests(files, ratio=ratio, seed=seed)
    for p in thinned:
        del files[p]
    _drop_modules(files, thinned)
    stripped = Variant("stripped", files, symlinks, set(tree.executables) & set(files),
                       {"held_out": sorted(held_out), "removed": {k: sorted(v) for k, v in gone.items()},
                        "readme_paragraphs_removed": readme_paragraphs, "spec_ids": stripped_counts,
                        "spec_id_pattern": pattern.pattern, "tests_reading_docs": reading_docs, "tests_thinned": thinned,
                        "source_lines": _source_lines(files), "test_lines": _test_lines(files), "ratio_target": ratio})
    stripped.report["ratio"] = round(stripped.report["test_lines"] / max(1, stripped.report["source_lines"]), 3)
    for v in (full, lid):
        v.report.update(source_lines=_source_lines(v.files), test_lines=_test_lines(v.files))
        v.report["ratio"] = round(v.report["test_lines"] / max(1, v.report["source_lines"]), 3)
    return {"full": full, "lid": lid, "stripped": stripped}


def _class(path: str) -> str:
    if "/tests/" in f"/{path}":
        return "tests"
    if path.endswith(".md") or path.startswith("docs/"):
        return "docs"
    if path.endswith(".rs"):
        return "source"
    return "other"


def variant_sizes(v: Variant) -> dict[str, dict]:
    """Bytes, lines, files, and tokens (estimated as bytes / 4, as context telemetry does) by class: source (Rust
    outside tests/), tests (anything under a tests/ directory), docs (Markdown and docs/), and other."""
    out = {k: {"bytes": 0, "lines": 0, "files": 0} for k in ("source", "tests", "docs", "other")}
    for p, d in v.files.items():
        c = out[_class(p)]
        c["bytes"] += len(d)
        c["lines"] += _lines(d)
        c["files"] += 1
    for c in out.values():
        c["tokens_est"] = c["bytes"] // 4
    return out


def write_repo(v: Variant, out: Path) -> str:
    """Write the variant as a one-commit git repository at `out`; returns the commit. The same files give the same
    commit."""
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for p, d in v.files.items():
        f = out / p
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(d)
        if p in v.executables:
            f.chmod(0o755)
    for p, target in v.symlinks.items():
        (out / p).parent.mkdir(parents=True, exist_ok=True)
        os.symlink(target, out / p)
    env = {**os.environ, "GIT_AUTHOR_NAME": IDENTITY[0], "GIT_AUTHOR_EMAIL": IDENTITY[1], "GIT_COMMITTER_NAME": IDENTITY[0],
           "GIT_COMMITTER_EMAIL": IDENTITY[1], "GIT_AUTHOR_DATE": DATE, "GIT_COMMITTER_DATE": DATE}
    git = lambda *a: subprocess.run(["git", "-C", str(out), "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *a],  # noqa: E731
                                    check=True, capture_output=True, env=env, text=True).stdout.strip()
    git("init", "-q", "-b", "main")
    git("add", "-A")
    git("commit", "-q", "-m", "Start")
    return git("rev-parse", "HEAD")


def held_out_helpers(tree: Tree, held_out: list[str], holdouts: list[dict] = ()) -> dict[str, bytes]:
    """The held-out files and, beside them, each test directory's helper modules as they were (main.rs's other
    modules, such as common/), so grading can build them against the original helpers. A forced holdout's copy is
    its file with only the listed tests left in it, beside its file's helpers; a file the draw held out stays whole."""
    out = {p: tree.files[p] for p in held_out}
    forced: dict[str, list[str]] = {}
    for h in holdouts:
        forced.setdefault(h["path"], []).append(h["fn"])
    for path, fns in forced.items():
        if path not in held_out:
            out[path] = keep_test_fns(tree.files[path].decode(), fns).encode()
    dirs = {_stratum(p) for p in [*held_out, *forced]}
    for p, d in tree.files.items():
        if any(p.startswith(d_ + "/") for d_ in dirs) and p not in test_files(tree.files):
            out[p] = d
    return out


# -------------------------------------------------------------------------------------------- docker and cargo


def load_volume(repo_dir: Path, volume: str, image: str = IMAGE, *, jj: bool = False, runner=subprocess.run) -> None:
    """Replace the volume's contents with the repository (its working tree and .git), owned by the image's user. With
    jj, the repository becomes a colocated jj repository, made by the image's own jj."""
    tar = subprocess.run(["tar", "-C", str(repo_dir), "-cf", "-", "."], check=True, capture_output=True).stdout
    script = "find /work -mindepth 1 -delete && tar -x -C /work"
    if jj:
        script += " && cd /work && jj git init --colocate >/dev/null 2>&1"
    runner(["docker", "run", "--rm", "-i", "-v", f"{volume}:/work", image, "sh", "-c", script],
           input=tar, check=True, capture_output=True)


TEST_RESULT = re.compile(r"test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored")


def parse_cargo_test(output: str, exit_code: int) -> dict:
    """Totals from `cargo test` output, the failing tests' names, and whether anything failed to compile."""
    passed = failed = ignored = 0
    for m in TEST_RESULT.finditer(output):
        passed, failed, ignored = passed + int(m.group(2)), failed + int(m.group(3)), ignored + int(m.group(4))
    failing = sorted(set(re.findall(r"(?m)^test (\S+) \.\.\. FAILED$", output)))
    compile_errors = re.findall(r"(?m)^error(?:\[E\d+\])?: .*$", output)
    compile_failed = bool(re.search(r"(?m)^error: could not compile", output))
    targets = len(TEST_RESULT.findall(output))
    return {"ok": exit_code == 0 and failed == 0 and targets > 0, "exit_code": exit_code, "passed": passed,
            "failed": failed, "ignored": ignored, "failing": failing, "compile_failed": compile_failed,
            "compile_errors": compile_errors[:20], "targets": targets}


def cargo_test(volume: str, *, image: str = IMAGE, target_volume: str = "ce-cv-target", runner=subprocess.run,
               args: str = "--workspace") -> tuple[dict, str]:
    """Run the variant's tests in a copy of the volume (so no target/ lands in it), with no network. The build output
    goes to a target volume shared across variants, handed to the image's user first (Docker creates it root-owned)."""
    runner(["docker", "run", "--rm", "--user", "root", "-v", f"{target_volume}:/target", image, "chown", "agent:agent",
            "/target"], capture_output=True, text=True)
    script = (f"cp -a /src /tmp/w && cd /tmp/w && CARGO_TARGET_DIR=/target timeout 3000 cargo test --offline {args} 2>&1; "
              "echo EXIT=$?")
    p = runner(["docker", "run", "--rm", "--network", "none", "-v", f"{volume}:/src:ro", "-v", f"{target_volume}:/target",
                image, "sh", "-c", script], capture_output=True, text=True)
    out = p.stdout + p.stderr
    m = re.search(r"EXIT=(\d+)\s*$", out)
    return parse_cargo_test(out, int(m.group(1)) if m else p.returncode), out


# ------------------------------------------------------------------------------------------------------ main


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--commit", default="HEAD")
    ap.add_argument("--seed", required=True, help="names the set and its volumes; seeds the draw unless --draw-seed")
    ap.add_argument("--draw-seed", help="the seed for the held-out draw and the thinning (default: --seed)")
    ap.add_argument("--holdouts", type=Path, help="test functions to hold out of every variant (JSON)")
    ap.add_argument("--renames", type=Path, help="a renaming dose to apply to the snapshot first (JSON)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--held-out-share", type=float, default=HELD_OUT_SHARE)
    ap.add_argument("--ratio", type=float, default=RATIO)
    ap.add_argument("--volumes", action="store_true", help="load each variant into a Docker volume")
    ap.add_argument("--cargo-test", action="store_true", help="run each variant's tests in the Rust image")
    ap.add_argument("--image", default=IMAGE)
    args = ap.parse_args(argv)
    draw = args.draw_seed or args.seed
    tree = read_tree(args.repo, args.commit)
    try:
        renames = apply_renames(tree, load_renames(args.renames)) if args.renames else []
        holdouts = load_holdouts(args.holdouts) if args.holdouts else []
        held = choose_held_out(tree, share=args.held_out_share, seed=draw)
        variants = plan_variants(tree, held_out=held, seed=draw, ratio=args.ratio)
        forced = remove_forced_holdouts(variants, holdouts, tree=tree, held_out=held)
    except ValueError as e:
        ap.error(str(e))
    for r in renames:
        r["variants"] = [name for name, v in variants.items() if r["file"] in v.files]
    args.out.mkdir(parents=True, exist_ok=True)
    hdir = args.out / "held-out"
    shutil.rmtree(hdir, ignore_errors=True)
    for p, d in held_out_helpers(tree, held, holdouts).items():
        (hdir / p).parent.mkdir(parents=True, exist_ok=True)
        (hdir / p).write_bytes(d)
    manifest = {"source_commit": tree.commit, "seed": args.seed, "draw_seed": draw, "held_out_share": args.held_out_share,
                "held_out": held, "holdouts_file": str(args.holdouts) if args.holdouts else None,
                "forced_holdouts": forced, "renames_file": str(args.renames) if args.renames else None,
                "renames_applied": renames, "variants": {}}
    target = f"ce-cv-target-{args.seed}"  # the set's own build cache, so two sets never share one
    for name, v in variants.items():
        head = write_repo(v, args.out / name)
        entry = {"commit": head, "vcs": v.vcs, "report": v.report, "sizes": variant_sizes(v), "files": len(v.files)}
        if args.volumes or args.cargo_test:
            entry["volume"] = f"ce-cv-{args.seed}-{name}"
            load_volume(args.out / name, entry["volume"], args.image, jj=v.vcs == "jj")
        if args.cargo_test:
            result, log = cargo_test(entry["volume"], image=args.image, target_volume=target)
            (args.out / f"cargo-test-{name}.log").write_text(log)
            entry["cargo_test"] = result
            print(f"{name}: {result['passed']} passed, {result['failed']} failed, compile failed {result['compile_failed']}",
                  flush=True)
        manifest["variants"][name] = entry
    if args.cargo_test:
        subprocess.run(["docker", "volume", "rm", "-f", target], capture_output=True)
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    for name, e in manifest["variants"].items():
        s = e["sizes"]
        print(f"{name}: {e['commit'][:12]} files {e['files']}, tokens source {s['source']['tokens_est']:,} tests "
              f"{s['tests']['tokens_est']:,} docs {s['docs']['tokens_est']:,}, test/source lines {e['report']['ratio']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
