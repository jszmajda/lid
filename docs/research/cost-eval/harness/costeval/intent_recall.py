"""What a fresh reader can recover of a system's current intent from its tests alone, or from its docs.

The hypothesis it tests: as intent changes course in a long-running system, tests keep passing but carry stale or
confusing intent, and without docs the tests are the main carrier of intent. So a fresh reader gets only a system's
tests (or only its docs, or only the seed's brief as a baseline) and writes down the system's current rules, and a
judge maps each rule to the intent known at that point:

- **agrees** with an item in force (recall counts the items in force that some rule agrees with);
- **contradicts** an item in force;
- **stale**: states retired or superseded intent;
- **incidental**: matches no item.

This module holds the parts where a quiet bug would bias the measure: which files make the input, what is stripped
from them (spec-ID pointers; in the neutral variant, test names, comments, and docstrings), the size cap (an input
over it is refused whole, never cut), the oracle at a change, the reader's and the judge's checks, scoring, and the
extraction of retired intent from a spec file's history. `intent_from_tests.py` runs it.
"""

from __future__ import annotations

import ast
import io
import json
import math
import re
import tokenize
from dataclasses import dataclass, replace
from pathlib import PurePosixPath
from typing import Any, Callable, Iterable

import clowder_variants as cv

from . import grading, simulator

MAX_TOKENS = 150_000
BYTES_PER_TOKEN = 4  # the estimate clowder_variants and context telemetry use
CLASSES = ("agrees", "contradicts", "stale", "incidental")
EXTENTS = ("whole", "part")
SKIP_DIRS = {".venv", "venv", "env", ".git", ".jj", "__pycache__", "node_modules", ".pytest_cache", "target",
             "site-packages", ".mypy_cache", ".ruff_cache", ".tox", ".claude"}
AGENT_FILES = {"AGENTS.md", "CLAUDE.md", "GEMINI.md"}
DOC_SUFFIXES = (".md", ".markdown", ".rst")
MIN_REASON_WORDS = 5
MIN_RULE_WORDS = 3
JUDGE_BATCH = 40
ATTEMPTS = 3
PLACEHOLDER = "…"  # what a neutralised comment or docstring says

ID_TOKEN = r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d{2,}[a-z]?"
SPEC_DEF = re.compile(r"\*\*([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*?)-\d{3,}[a-z]?\*\*")  # as clowder_variants reads specs
SPEC_LINE = re.compile(r"^\s*[-*]\s*\[(?P<status>[ xXD])\]\s*\*\*(?P<id>" + ID_TOKEN + r")\*\*:?\s*(?P<text>.*)$")
CITED = re.compile(r"@spec\b((?:[\s,/!*#&:]|\band\b|\b" + ID_TOKEN + r"\b)*)")


class TooLarge(ValueError):
    """An input over the size cap. It is refused whole; nothing is ever cut to fit."""


@dataclass(frozen=True)
class InputFile:
    path: str
    text: str
    note: str = ""


# ------------------------------------------------------------------------------------------ choosing the input


def skipped(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return any(p in SKIP_DIRS or p.endswith(".egg-info") for p in parts)


def _in_test_dir(path: str) -> bool:
    return any(p in ("tests", "test") for p in PurePosixPath(path).parts[:-1])


def is_test_path(path: str) -> bool:
    """Anything under a tests/ (or test/) directory, a Python test module (test_*.py, *_test.py), or conftest.py."""
    name = PurePosixPath(path).name
    return _in_test_dir(path) or (name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py")
                                                            or name == "conftest.py"))


def cfg_test_blocks(text: str) -> list[str]:
    """Each `#[cfg(test)]` item in a Rust source file, from the attribute's line to the item's end."""
    out, i = [], 0
    while (k := text.find("#[cfg(test)]", i)) >= 0:
        end = cv._item_end(text, k + len("#[cfg(test)]"))
        start = text.rfind("\n", 0, k) + 1
        out.append(text[start:end + 1])
        i = end + 1
    return out


def select_tests(files: dict[str, str]) -> list[InputFile]:
    """The test input: every text file under a tests/ directory, Python test modules, and, from Rust sources, their
    `#[cfg(test)]` blocks only."""
    out = []
    for p in sorted(files):
        if skipped(p):
            continue
        if is_test_path(p):
            out.append(InputFile(p, files[p]))
        elif p.endswith(".rs") and (blocks := cfg_test_blocks(files[p])):
            out.append(InputFile(p, "\n\n".join(blocks), "only its #[cfg(test)] blocks"))
    return out


def select_docs(files: dict[str, str]) -> list[InputFile]:
    """The docs input: prose files (Markdown, reStructuredText) outside the tests, without agent instruction files,
    which configure the agent rather than describe the system."""
    return [InputFile(p, files[p]) for p in sorted(files)
            if p.endswith(DOC_SUFFIXES) and not skipped(p) and not _in_test_dir(p)
            and PurePosixPath(p).name not in AGENT_FILES]


def spec_citations(text: str) -> set[str]:
    """The spec IDs `@spec` annotations in a text cite, including a list that wraps onto the next comment line."""
    out: set[str] = set()
    for m in CITED.finditer(text):
        out |= set(re.findall(r"\b" + ID_TOKEN + r"\b", m.group(1)))
    return out


def test_functions(text: str) -> list[tuple[str, int, int]]:
    """(name, start, end) of each `#[test]` function in Rust text, from its doc comments and attributes to its
    closing brace (end is exclusive)."""
    out = []
    for m in re.finditer(r"#\[test\]", text):
        fn = re.compile(r"\bfn\s+(\w+)").search(text, m.end())
        if fn is None:
            continue
        end = cv._item_end(text, fn.end())
        start = text.rfind("\n", 0, m.start()) + 1
        while start > 0:  # the doc comments and other attributes above it
            prev = text.rfind("\n", 0, start - 1) + 1
            if not text[prev:start].strip().startswith(("///", "#[", "//")):
                break
            start = prev
        out.append((fn.group(1), start, end + 1))
    return out


def segment_tests(files: dict[str, str], ids: set[str]) -> list[InputFile]:
    """A part of a Rust system's tests: the `#[test]` functions whose `@spec` annotations cite any of its spec IDs,
    each file's in their order, with their doc comments and attributes and nothing else of the file."""
    out = []
    for p in sorted(files):
        if not p.endswith(".rs") or skipped(p) or "#[test]" not in files[p]:
            continue
        text = files[p]
        chosen = [text[s:e] for _, s, e in test_functions(text) if spec_citations(text[s:e]) & ids]
        if chosen:
            out.append(InputFile(p, "\n\n".join(chosen) + "\n", "selected test functions"))
    return out


def spec_ids(spec_text: str) -> set[str]:
    return {m.group("id") for line in spec_text.splitlines() if (m := SPEC_LINE.match(line))}


# --------------------------------------------------------------------------------------- stripping pointers


def pointer_pattern(files: dict[str, str]) -> re.Pattern:
    """Spec-ID pointers: the prefixes the project's spec files define (**PREFIX-NNN**) and those its `@spec`
    annotations cite, each followed by its number."""
    prefixes = set()
    for p, t in files.items():
        if p.endswith("-specs.md"):
            prefixes |= set(SPEC_DEF.findall(t))
        if "@spec" in t:
            prefixes |= {i.rsplit("-", 1)[0] for i in spec_citations(t)}
    if not prefixes:
        return re.compile(r"(?!)")
    alt = "|".join(re.escape(p) for p in sorted(prefixes, key=lambda p: (-len(p), p)))
    return re.compile(rf"\b(?:{alt})-\d{{2,}}[a-z]?\b")


def strip_pointers(inputs: list[InputFile], pattern: re.Pattern) -> tuple[list[InputFile], dict[str, int]]:
    """Remove `@spec` annotations and bare spec-ID citations (pointers, not intent), keeping the test names,
    comments, and assertions around them. A range ("X-001 .. X-009") counts as one citation."""
    totals = {"annotation lines": 0, "lines changed": 0, "lines dropped": 0, "files": 0}
    ident = pattern.pattern
    out = []
    for f in inputs:
        text = re.sub(rf"({ident})\s*(?:\.\.\.?|…|–|—|\bto\b|\bthrough\b)\s*(?:(?:{ident})|\d{{2,}}\b)",
                      r"\1", f.text)
        new, counts = cv.strip_spec_ids(text, pattern, hash_comments=f.path.endswith(".py"))
        if f.path.endswith(DOC_SUFFIXES):
            new = re.sub(r"\*\*\s*\*\*:?[ \t]*", "", new)  # a spec's bold label left empty
        if new != f.text:
            totals["files"] += 1
            for k, v in counts.items():
                totals[k] += v
        out.append(replace(f, text=new))
    return out, totals


# -------------------------------------------------------------------------------------- the neutral variant


def _offsets(text: str) -> list[int]:
    starts = [0]
    for line in text.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    return starts


def _apply(text: str, edits: list[tuple[int, int, str]]) -> str:
    for start, end, new in sorted(edits, reverse=True):
        text = text[:start] + new + text[end:]
    return text


def neutralize_python(text: str) -> tuple[str, dict[str, int]]:
    """Test names (functions test*, classes Test*), comments, and docstrings become neutral placeholders; code,
    assertions, and their messages stay."""
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    starts = _offsets(text)

    def at(lineno: int, byte_col: int) -> int:
        return starts[lineno - 1] + len(lines[lineno - 1].encode()[:byte_col].decode(errors="ignore"))

    edits: list[tuple[int, int, str]] = []
    counts = {"test names": 0, "comments": 0, "docstrings": 0}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                v = first.value
                edits.append((at(v.lineno, v.col_offset), at(v.end_lineno, v.end_col_offset), f'"""{PLACEHOLDER}"""'))
                counts["docstrings"] += 1
    named = sorted((n for n in ast.walk(tree)
                    if (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"))
                    or (isinstance(n, ast.ClassDef) and n.name.startswith("Test"))), key=lambda n: (n.lineno, n.col_offset))
    k_fn = k_cls = 0
    for n in named:
        line_start = at(n.lineno, n.col_offset)
        word = "class" if isinstance(n, ast.ClassDef) else "def"
        m = re.compile(rf"{word}\s+({re.escape(n.name)})\b").search(text, line_start)
        if not m:
            raise ValueError(f"can't find the name of {n.name} at line {n.lineno}")
        if word == "class":
            k_cls += 1
            new = f"TestGroup{k_cls:02d}"
        else:
            k_fn += 1
            new = f"test_case_{k_fn:03d}"
        edits.append((m.start(1), m.end(1), new))
        counts["test names"] += 1
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type == tokenize.COMMENT:
            (r1, c1), (r2, c2) = tok.start, tok.end
            edits.append((starts[r1 - 1] + c1, starts[r2 - 1] + c2, f"# {PLACEHOLDER}"))
            counts["comments"] += 1
    out = _apply(text, edits)
    ast.parse(out)
    return out, counts


def _rust_comments(text: str) -> list[tuple[int, int, str]]:
    """(start, end, marker) of each comment in Rust text, skipping strings, raw strings, and character literals;
    block comments nest."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            marker = "///" if text.startswith("///", i) and not text.startswith("////", i) else (
                "//!" if text.startswith("//!", i) else "//")
            out.append((i, j, marker))
            i = j
            continue
        if text.startswith("/*", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if text.startswith("/*", j):
                    depth, j = depth + 1, j + 2
                elif text.startswith("*/", j):
                    depth, j = depth - 1, j + 2
                else:
                    j += 1
            out.append((i, j, "/*"))
            i = j
            continue
        m = re.match(r'b?r(#*)"', text[i:i + 12])
        if m and (i == 0 or not (text[i - 1].isalnum() or text[i - 1] == "_")):
            close = '"' + m.group(1)
            j = text.find(close, i + len(m.group(0)))
            i = n if j < 0 else j + len(close)
            continue
        if c == '"':
            j = i + 1
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
        i += 1
    return out


def neutralize_rust(text: str) -> tuple[str, dict[str, int]]:
    """Each `#[test]` function's name and every comment become neutral placeholders; code, assertions, and string
    literals (assertion messages and `expected` texts among them) stay."""
    comments = _rust_comments(text)
    edits = [(s, e, f"/* {PLACEHOLDER} */" if marker == "/*" else f"{marker} {PLACEHOLDER}") for s, e, marker in comments]
    inside = lambda k: any(s <= k < e for s, e, _ in comments)  # noqa: E731
    k = 0
    for m in re.finditer(r"#\[test\]", text):
        if inside(m.start()):
            continue
        fn = re.compile(r"\bfn\s+(\w+)").search(text, m.end())
        if fn is None:
            continue
        k += 1
        edits.append((fn.start(1), fn.end(1), f"test_case_{k:03d}"))
    return _apply(text, edits), {"test names": k, "comments": len(comments), "docstrings": 0}


def neutralize(inputs: list[InputFile]) -> tuple[list[InputFile], dict[str, int]]:
    totals = {"test names": 0, "comments": 0, "docstrings": 0, "files": 0}
    out = []
    for f in inputs:
        if f.path.endswith(".py"):
            new, counts = neutralize_python(f.text)
        elif f.path.endswith(".rs"):
            new, counts = neutralize_rust(f.text)
        else:
            out.append(f)
            continue
        totals["files"] += 1
        for key, v in counts.items():
            totals[key] += v
        out.append(replace(f, text=new))
    return out, totals


# ------------------------------------------------------------------------------------------ size and render


def estimate_tokens(text: str) -> int:
    return math.ceil(len(text.encode("utf-8")) / BYTES_PER_TOKEN)


def check_size(text: str, cap: int = MAX_TOKENS) -> int:
    n = estimate_tokens(text)
    if n > cap:
        raise TooLarge(f"the input is about {n:,} tokens, over the cap of {cap:,}; scope it down (one part of the "
                       "system, one crate, fewer files) rather than cutting it. Nothing was truncated.")
    return n


LANGS = {".py": "python", ".rs": "rust", ".md": "markdown", ".json": "json", ".toml": "toml", ".yaml": "yaml",
         ".yml": "yaml"}


def render_files(inputs: list[InputFile]) -> str:
    blocks = []
    for f in inputs:
        runs = [len(m.group(0)) for m in re.finditer(r"`+", f.text)]
        fence = "`" * max(3, max(runs, default=0) + 1)
        lang = LANGS.get(PurePosixPath(f.path).suffix, "")
        body = f.text if f.text.endswith("\n") else f.text + "\n"
        head = f"## {f.path}" + (f" ({f.note})" if f.note else "")
        blocks.append(f"{head}\n\n{fence}{lang}\n{body}{fence}")
    return "\n\n".join(blocks)


# ------------------------------------------------------------------------------------------------ the oracle


@dataclass(frozen=True)
class OracleItem:
    id: str
    text: str
    status: str  # "in force" or "retired"
    group: str  # stated, latent, symptom (BenchTime); spec (a spec file); retired, superseded
    source: str = ""  # where it came from: a disclosure kind, a spec ID, a change


def _group(kind: str) -> str:
    k = kind.lower()
    if k.startswith(("stated", "emerging")):
        return "stated"
    if k.startswith(("askable", "recognized on sight")):
        return "latent"
    if k.startswith("realized on symptom"):
        return "symptom"
    raise ValueError(f"unknown disclosure kind {kind!r}")


def benchtime_oracle(oracle: simulator.Oracle, changes: dict[int, simulator.Change], change: int) -> list[OracleItem]:
    """The intent known at a change. In force: introduced at or before it and not retired by it. Retired: retired
    at or before it. Superseded: the first request of each change of mind delivered by then (a clarification
    supersedes nothing: the owner meant it all along). Dropped items were never the owner's intent and are left
    out. Item text is the owner's own (graders' cross-references and change numbers removed)."""
    ids = simulator.id_pattern(oracle.ids())
    out = []
    for i in oracle.items:
        if i.kind == "Dropped" or i.in_force is None or i.in_force > change:
            continue
        text = simulator.owner_text(i.behavior, ids)
        if i.retired is not None and i.retired <= change:
            out.append(OracleItem(i.id, text, "retired", "retired", f"retired at change {i.retired}"))
        else:
            out.append(OracleItem(i.id, text, "in force", _group(i.kind), i.kind))
    for n in sorted(changes):
        c = changes[n]
        if n <= change and c.redirect and c.redirect.kind == "change of mind" and c.request:
            out.append(OracleItem(f"SUP-{n:02d}", f'First asked for: "{c.request}" Then replaced, before it was built, '
                                  f'by: "{c.redirect.text}"', "retired", "superseded", f"change {n}'s change of mind"))
    return out


def spec_items(spec_text: str) -> list[OracleItem]:
    """A spec file's intent in force: its implemented lines ([x]); gaps and deferred lines are neither in force nor
    retired."""
    return [OracleItem(m.group("id"), m.group("text").strip(), "in force", "spec", m.group("id"))
            for line in spec_text.splitlines() if (m := SPEC_LINE.match(line)) and m.group("status") in "xX"]


def render_oracle(items: list[OracleItem]) -> str:
    cur = [i for i in items if i.status == "in force"]
    old = [i for i in items if i.status == "retired"]
    text = "### Current items: what holds now\n\n" + "\n".join(f"- [{i.id}] {i.text}" for i in cur)
    text += "\n\n### Retired items: what held once and has since been dropped or replaced\n\n"
    text += "\n".join(f"- [{i.id}] {i.text}" for i in old) if old else "(none)"
    return text


# ------------------------------------------------------------------------------------------------ the reader

READER_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["rules"],
    "properties": {"rules": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["rule", "evidence"],
        "properties": {"rule": {"type": "string"}, "evidence": {"type": "array", "items": {"type": "string"}}}}}},
}

SOURCE_NOTES = {
    "tests": "The files are the system's tests.",
    "docs": "The files are the system's documentation.",
    "brief": "The file is the brief the system was built from.",
}
NEUTRAL_NOTE = (" In them, test names, comments, and docstrings have been replaced by placeholders; the code and its "
                "assertions are as written.")


def reader_prompt(source: str, inputs: list[InputFile], neutral: bool = False) -> str:
    note = SOURCE_NOTES[source] + (NEUTRAL_NOTE if neutral else "")
    return grading._template("intent-from-tests.md", SOURCE_NOTE=note, FILES=render_files(inputs))


def _citation_problem(e: str, files: dict[str, str]) -> str | None:
    path = next((p for p in sorted(files, key=len, reverse=True) if e == p or e.startswith((p + "::", p + " ", p + ":"))),
                None)
    if path is None:
        return f"cites `{e}`, which isn't one of the files"
    rest = e[len(path):]
    if rest.startswith("::"):
        name = re.split(r"[\s(\[]", rest[2:].split("::")[-1].strip(), maxsplit=1)[0]
        if name and not re.search(rf"\b{re.escape(name)}\b", files[path]):
            return f"cites `{e}`, but `{name}` isn't in {path}"
    return None


def check_reader(structured: Any, inputs: list[InputFile]) -> tuple[list[dict], list[str]]:
    """The reader's rules that hold up, and the problems: a rule needs at least three words and a citation of a
    given file (and, for `path::name`, a name that file holds). A bad citation is dropped from its rule; a rule left
    with none, or too short, is dropped."""
    listed = structured.get("rules") if isinstance(structured, dict) else None
    if not isinstance(listed, list) or not listed:
        return [], ["no rules"]
    files = {f.path: f.text for f in inputs}
    rules, problems = [], []
    for k, r in enumerate(listed, 1):
        text = str((r or {}).get("rule", "")).strip()
        if len(text.split()) < MIN_RULE_WORDS:
            problems.append(f"rule {k} is too short to be a rule: {text!r}")
            continue
        good, bad = [], []
        for e in (r.get("evidence") or []):
            e = str(e).strip()
            p = _citation_problem(e, files)
            (bad if p else good).append(e)
            if p:
                problems.append(f"rule {k} {p}")
        if not good:
            problems.append(f"rule {k} has no citation of a given file: {text[:80]!r}")
            continue
        rules.append({"rule": text, "evidence": good, **({"dropped_evidence": bad} if bad else {})})
    return rules, problems


# ------------------------------------------------------------------------------------------------- the judge

JUDGE_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["mappings"],
    "properties": {"mappings": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["rule", "classification", "items", "extent", "rule_quote", "item_quotes", "reason"],
        "properties": {
            "rule": {"type": "integer"}, "classification": {"type": "string", "enum": list(CLASSES)},
            "items": {"type": "array", "items": {"type": "string"}},
            "extent": {"type": "string", "enum": [*EXTENTS, "none"]},
            "rule_quote": {"type": "string"},
            "item_quotes": {"type": "array", "items": {
                "type": "object", "additionalProperties": False, "required": ["item", "quote"],
                "properties": {"item": {"type": "string"}, "quote": {"type": "string"}}}},
            "reason": {"type": "string"}}}}},
}


def judge_prompt(items: list[OracleItem], numbered: list[tuple[int, str]]) -> str:
    rules = "\n".join(f"R{n}. {text}" for n, text in numbered)
    return grading._template("intent-match.md", ITEMS=render_oracle(items), RULES=rules)


def _norm(s: str) -> str:
    s = s.lower().translate(str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-",
                                           "—": "-", "`": None, "*": None}))
    return re.sub(r"\s+", " ", s).strip(" .,;:\"'")


def quote_found(quote: str, text: str) -> bool:
    """A quote is found when each of its pieces (split at an ellipsis) appears in the text in order, ignoring case,
    spacing, typographic quotes and dashes, and Markdown emphasis."""
    pieces = [_norm(p) for p in re.split(r"\.\.\.|…", quote)]
    pieces = [p for p in pieces if p]
    if not pieces:
        return False
    hay, at = _norm(text), 0
    for p in pieces:
        k = hay.find(p, at)
        if k < 0:
            return False
        at = k + len(p)
    return True


def _mapping_problem(m: dict, rule_text: str, by_id: dict[str, OracleItem]) -> str | None:
    n, cls, ids = m.get("rule"), m.get("classification"), list(m.get("items") or [])
    if cls not in CLASSES:
        return f"rule {n}: classification {cls!r}"
    if len(str(m.get("reason", "")).split()) < MIN_REASON_WORDS:
        return f"rule {n}: a reason too short to explain the mapping"
    unknown = [i for i in ids if i not in by_id]
    if unknown:
        return f"rule {n}: items {unknown} aren't in the list"
    if cls == "incidental":
        if ids or m.get("item_quotes"):
            return f"rule {n}: incidental, yet it lists items"
    else:
        if not ids:
            return f"rule {n}: {cls} lists no items"
        want = "retired" if cls == "stale" else "in force"
        wrong = [i for i in ids if by_id[i].status != want]
        if wrong:
            return f"rule {n}: {cls} must list {'retired' if want == 'retired' else 'current'} items, not {wrong}"
    extent = m.get("extent")
    if cls == "agrees" and extent not in EXTENTS:
        return f"rule {n}: agrees needs extent whole or part, not {extent!r}"
    if cls != "agrees" and extent != "none":
        return f"rule {n}: extent is for agreement only"
    if not quote_found(str(m.get("rule_quote", "")), rule_text):
        return f"rule {n}: the rule quote {m.get('rule_quote')!r} isn't in the rule"
    quotes = {}
    for q in m.get("item_quotes") or []:
        quotes.setdefault(q.get("item"), []).append(str(q.get("quote", "")))
    for i in ids:
        if not quotes.get(i):
            return f"rule {n}: no quote of {i}"
        if not any(quote_found(q, by_id[i].text) for q in quotes[i]):
            return f"rule {n}: the quote of {i} isn't in its text"
    extra = set(quotes) - set(ids)
    if extra:
        return f"rule {n}: quotes items it doesn't list: {sorted(extra)}"
    return None


def check_mappings(structured: Any, numbers: list[int], rules: list[dict],
                   items: list[OracleItem]) -> list[tuple[int | None, str]]:
    """(rule number, problem) for each problem in the judge's answer, at most one per mapping; None for a problem
    with the answer as a whole. Rules are numbered from 1 in `rules`."""
    listed = structured.get("mappings") if isinstance(structured, dict) else None
    if not isinstance(listed, list):
        return [(None, "no mappings")]
    by_id = {i.id: i for i in items}
    seen: set[int] = set()
    problems: list[tuple[int | None, str]] = []
    for m in listed:
        n = m.get("rule")
        if n not in numbers:
            problems.append((None, f"a mapping for rule {n}, which isn't one of the rules"))
            continue
        if n in seen:
            problems.append((n, f"two mappings for rule {n}"))
            continue
        seen.add(n)
        p = _mapping_problem(m, rules[n - 1]["rule"], by_id)
        if p:
            problems.append((n, p))
    for n in numbers:
        if n not in seen:
            problems.append((n, f"no mapping for rule {n}"))
    return problems


Ask = Callable[[str, dict], tuple[Any, dict]]


def judge(rules: list[dict], items: list[OracleItem], *, ask: Ask, attempts: int = ATTEMPTS,
          batch_size: int = JUDGE_BATCH) -> dict:
    """Map every rule, in batches, each batch asked again (up to `attempts`) while any of its rules lacks a valid
    mapping. Each rule keeps its latest valid mapping; a rule with none is unjudged and left out of every rate.
    ask(prompt, schema) -> (structured answer, usage with cost_usd)."""
    numbers = list(range(1, len(rules) + 1))
    mappings: dict[int, dict] = {}
    batches, cost = [], 0.0
    for k in range(0, len(numbers), batch_size):
        batch = numbers[k:k + batch_size]
        prompt = judge_prompt(items, [(n, rules[n - 1]["rule"]) for n in batch])
        tries = []
        for _ in range(attempts):
            asked = prompt
            if tries and tries[-1]["problems"]:
                listed = tries[-1]["problems"][:30]
                asked += ("\n\nAn earlier answer to this had these problems, which this answer must avoid:\n"
                          + "\n".join(f"- {p}" for p in listed))
            structured, use = ask(asked, JUDGE_SCHEMA)
            cost += (use or {}).get("cost_usd") or 0.0
            problems = check_mappings(structured, batch, rules, items)
            broken = {n for n, _ in problems if n is not None}
            whole = any(n is None for n, _ in problems) and not isinstance((structured or {}).get("mappings"), list)
            if not whole:
                for m in structured["mappings"]:
                    n = m.get("rule")
                    if n in batch and n not in broken:
                        mappings[n] = m
            tries.append({"structured": structured, "problems": [p for _, p in problems], "usage": use})
            if all(n in mappings for n in batch):
                break
        batches.append({"rules": batch, "prompt": prompt, "tries": tries})
    return {"mappings": {n: mappings[n] for n in sorted(mappings)}, "unjudged": [n for n in numbers if n not in mappings],
            "batches": batches, "cost_usd": round(cost, 6)}


# --------------------------------------------------------------------------------------------------- scoring


def _ratio(a: int, b: int) -> float | None:
    return a / b if b else None


def _by_group(ids: Iterable[str], recovered: set[str], groups: dict[str, str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i in ids:
        g = out.setdefault(groups[i], {"of": 0, "recovered": 0})
        g["of"] += 1
        g["recovered"] += i in recovered
    for g in out.values():
        g["recall"] = _ratio(g["recovered"], g["of"])
    return dict(sorted(out.items()))


def recall_against(recovered: Iterable[str], met: set[str]) -> float | None:
    return _ratio(len(set(recovered) & met), len(met))


def score(n_rules: int, mappings: dict[int, dict], items: list[OracleItem], met: set[str] | None = None) -> dict:
    """One reconstruction's scores: rule classes as counts and rates per judged rule; recall of the items in force
    (raw, by group, and over the items the build meets where `met` is given); items contradicted; and stale claims
    per retired item."""
    cur = [i.id for i in items if i.status == "in force"]
    old = [i.id for i in items if i.status == "retired"]
    groups = {i.id: i.group for i in items}
    counts = {c: 0 for c in CLASSES}
    agreed, whole, contradicted, stale = set(), set(), set(), set()
    against_met = against_unmet = 0  # contradicting rules: against an item the build meets / only against unmet ones
    for m in mappings.values():
        counts[m["classification"]] += 1
        ids = set(m.get("items") or [])
        if m["classification"] == "agrees":
            agreed |= ids
            if m.get("extent") == "whole":
                whole |= ids
        elif m["classification"] == "contradicts":
            contradicted |= ids
            if met is not None:
                if ids & met:
                    against_met += 1
                else:
                    against_unmet += 1
        elif m["classification"] == "stale":
            stale |= ids
    judged = len(mappings)
    recovered = agreed & set(cur)
    out = {
        "rules": n_rules, "judged": judged, "unjudged": n_rules - judged, "counts": counts,
        "rates_per_rule": {c: _ratio(v, judged) for c, v in counts.items()},
        "in_force": len(cur), "recovered": sorted(recovered), "recall": _ratio(len(recovered), len(cur)),
        "recovered_whole": sorted(whole & set(cur)), "recall_whole": _ratio(len(whole & set(cur)), len(cur)),
        "by_group": _by_group(cur, recovered, groups),
        "contradicted": sorted(contradicted & set(cur)),
        "retired": len(old), "stale_items": sorted(stale & set(old)),
        "stale_items_share": _ratio(len(stale & set(old)), len(old)),
        "stale_rules_per_retired_item": _ratio(counts["stale"], len(old)),
        "met": None, "recall_of_met": None, "by_group_of_met": None, "contradicted_met": None,
        "contradicted_unmet": None, "contradicting_rules": None,
    }
    if met is not None:
        met_cur = [i for i in cur if i in met]
        out.update(met=len(met_cur), recall_of_met=_ratio(len(recovered & set(met_cur)), len(met_cur)),
                   by_group_of_met=_by_group(met_cur, recovered, groups),
                   # a contradiction of an item the build meets misleads; one of an item it doesn't may record the defect
                   contradicted_met=sorted(contradicted & set(met_cur)),
                   contradicted_unmet=sorted((contradicted & set(cur)) - set(met_cur)),
                   contradicting_rules={"against_met": against_met, "against_unmet_only": against_unmet,
                                        "against_met_per_rule": _ratio(against_met, judged),
                                        "against_unmet_only_per_rule": _ratio(against_unmet, judged)})
    return out


def _flat(d: dict, prefix: str = "") -> dict[str, float]:
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(_flat(v, key + "."))
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            out[key] = v
    return out


def summarize_repeats(scores: list[dict]) -> dict:
    """Every numeric score's mean, min, and max across a reconstruction's repeats."""
    flats = [_flat(s) for s in scores]
    keys = sorted({k for f in flats for k in f})
    out: dict[str, Any] = {"repeats": len(scores)}
    for k in keys:
        vs = [f[k] for f in flats if f.get(k) is not None]
        if vs:
            out[k] = {"mean": sum(vs) / len(vs), "min": min(vs), "max": max(vs)}
    return out


# ------------------------------------------------------------------------------------ retired intent (specs)


def _spec_text(line: str) -> tuple[str, str] | None:
    m = SPEC_LINE.match(line)
    return (m.group("id"), re.sub(r"\s+", " ", m.group("text")).strip()) if m else None


def removed_spec_lines(log: str) -> list[dict]:
    """Every spec line a commit removed, from `git log -p --format='COMMIT %h %cs'` output on a spec file: its ID,
    its text (without status marker or label), and the commit."""
    out, commit = [], None
    for line in log.splitlines():
        if line.startswith("COMMIT "):
            commit = line.split()[1]
            continue
        if not line.startswith("-") or re.match(r"^--- (?:a/|/dev/null)", line):
            continue
        got = _spec_text(line[1:])
        if got:
            out.append({"id": got[0], "text": got[1], "commit": commit})
    return out


def retired_candidates(removed: list[dict], current_spec: str) -> list[dict]:
    """The removed lines no current line says word for word (a status change or a move says the same), each
    distinct text once with every commit that removed it, numbered from 1 in the log's order."""
    current = {t for line in current_spec.splitlines() if (got := _spec_text(line)) for t in [got[1]]}
    out: dict[tuple[str, str], dict] = {}
    for r in removed:
        if r["text"] in current:
            continue
        c = out.setdefault((r["id"], r["text"]), {"id": r["id"], "text": r["text"], "commits": []})
        if r["commit"] not in c["commits"]:
            c["commits"].append(r["commit"])
    cands = list(out.values())
    for n, c in enumerate(cands, 1):
        c["n"] = n
    return cands


RETIRED_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["candidates"],
    "properties": {"candidates": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["candidate", "verdict", "current", "retired_claim", "quote", "duplicate_of", "reason"],
        "properties": {"candidate": {"type": "integer"}, "verdict": {"type": "string", "enum": ["still said", "retired"]},
                       "current": {"type": "array", "items": {"type": "string"}}, "retired_claim": {"type": "string"},
                       "quote": {"type": "string"}, "duplicate_of": {"type": "integer"}, "reason": {"type": "string"}}}}},
}


def retired_prompt(current_spec: str, cands: list[dict]) -> str:
    listed = "\n".join(f"C{c['n']}. (was {c['id']}) {c['text']}" for c in cands)
    return grading._template("intent-retired.md", CURRENT=current_spec.strip(), CANDIDATES=listed)


def check_retired(structured: Any, cands: list[dict], current_ids: set[str]) -> list[str]:
    listed = structured.get("candidates") if isinstance(structured, dict) else None
    if not isinstance(listed, list):
        return ["no candidates"]
    by_n = {c["n"]: c for c in cands}
    verdicts = {a.get("candidate"): a.get("verdict") for a in listed}
    problems, seen = [], set()
    for a in listed:
        n = a.get("candidate")
        if n not in by_n:
            problems.append(f"candidate {n} isn't one of the candidates")
            continue
        if n in seen:
            problems.append(f"candidate {n} answered twice")
            continue
        seen.add(n)
        unknown = [i for i in a.get("current") or [] if i not in current_ids]
        if len(str(a.get("reason", "")).split()) < MIN_REASON_WORDS:
            problems.append(f"candidate {n}: a reason too short to explain the verdict")
        elif unknown:
            problems.append(f"candidate {n}: current lines {unknown} aren't in the spec file")
        elif a.get("verdict") == "still said" and not a.get("current"):
            problems.append(f"candidate {n}: still said, but by no current line")
        elif a.get("verdict") == "retired" and len(str(a.get("retired_claim", "")).split()) < MIN_REASON_WORDS:
            problems.append(f"candidate {n}: retired, without a claim saying what no longer holds")
        elif a.get("verdict") == "retired" and not quote_found(str(a.get("quote", "")), by_n[n]["text"]):
            problems.append(f"candidate {n}: the quote isn't in the old line")
        elif a.get("duplicate_of") and not (a["duplicate_of"] < n and verdicts.get(a["duplicate_of"]) == "retired"
                                            and a.get("verdict") == "retired"):
            problems.append(f"candidate {n}: duplicate_of must name an earlier retired candidate")
    for n in by_n:
        if n not in seen:
            problems.append(f"candidate {n} has no verdict")
    return problems


def retired_items(cands: list[dict], structured: dict) -> list[OracleItem]:
    """One retired item per retired claim (a duplicate folds into the claim it repeats), its text the claim and the
    old line it came from."""
    by_n = {c["n"]: c for c in cands}
    out = []
    for a in sorted(structured["candidates"], key=lambda a: a["candidate"]):
        if a["verdict"] != "retired" or a.get("duplicate_of"):
            continue
        c = by_n[a["candidate"]]
        out.append(OracleItem(f"RET-{len(out) + 1:02d}", f'{a["retired_claim"].strip()} (Formerly {c["id"]}: '
                              f'"{c["text"]}")', "retired", "retired", f"{c['id']} @ {','.join(c['commits'])}"))
    return out


def items_json(items: list[OracleItem]) -> list[dict]:
    return [i.__dict__.copy() for i in items]


def items_from_json(data: list[dict]) -> list[OracleItem]:
    return [OracleItem(**d) for d in data]


def dumps(obj: Any) -> str:
    return json.dumps(obj, indent=1, ensure_ascii=False)
