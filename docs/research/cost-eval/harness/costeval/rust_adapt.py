"""The pre-registered compile-only adaptation of held-out tests to an arm's code.

A held-out test file was written against the code before the change. An arm may add a field to a struct the file
builds as a literal, or a variant to an enum the file matches on exhaustively; the file then fails to build, and
keeping would grade the arm's storage design rather than whether the old behaviour still holds. So, for every change:

- Where a held-out target fails to build only on errors E0063 (a struct literal, or a struct-like enum variant's
  literal, lacks fields) and E0004 (a match lacks variants), the grader edits the files it placed for that target,
  the held-out file and the helper modules copied beside it, and builds again.
- E0063: each missing field is added at an empty value, in the order the arm's definition declares them, with its
  name and type taken from that definition. The value is `Default::default()` where the arm's source shows the type
  implements Default (a derive or an impl, or a standard collection), and otherwise a typed empty value where one is
  obvious: `String::new()`, `Vec::new()`, `None`, `0`, `0.0`, `false`, `""`. A type alias is followed to its type.
  Any other field type means no adaptation.
- E0004: a wildcard arm, `_ => unreachable!("grader adaptation: ...")`, goes last in the match. A test that reaches it
  at run time fails, and is named as having reached an adapted arm.
- The edits come from rustc's JSON diagnostics and the arm's source, never from a model. They add no lines, so a
  failure's line number is the held-out file's own.
- Any other error, an error outside the target's own files, a definition that can't be found once, a field with no
  empty value, or a target still failing after the edits: compile failure, not adapted, and no edit is made in that
  round. Each edit is recorded.
"""

from __future__ import annotations

import functools
import json
import re
from dataclasses import dataclass
from typing import Callable, Iterable

ADAPTED = {"E0063": "a struct literal lacks fields", "E0004": "a match lacks variants"}
MARK = "grader adaptation: a variant the arm added"
WILDCARD = f'_ => unreachable!("{MARK}")'
SOURCE_MARK = "@@ce-arm-source@@"
MAX_ROUNDS = 3

INTS = {"u8", "u16", "u32", "u64", "u128", "usize", "i8", "i16", "i32", "i64", "i128", "isize"}
STD_DEFAULT = {"HashMap", "HashSet", "BTreeMap", "BTreeSet", "VecDeque", "BinaryHeap", "PathBuf", "Duration"}


# ------------------------------------------------------------------------------------------------ diagnostics


@dataclass(frozen=True)
class Error:
    code: str | None
    message: str
    file: str | None
    byte_start: int | None
    byte_end: int | None
    in_macro: bool
    line: int | None

    def brief(self) -> dict:
        return {"code": self.code, "file": self.file, "line": self.line, "message": self.message}


def _json_lines(output: str) -> Iterable[dict]:
    for line in output.splitlines():
        if line.startswith("{"):
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def built(output: str) -> bool:
    return any(m.get("reason") == "build-finished" and m.get("success") for m in _json_lines(output))


def errors(output: str) -> list[Error]:
    """The errors in cargo's JSON output, each with its primary span; the closing "aborting" summary is left out."""
    out = []
    for m in _json_lines(output):
        if m.get("reason") != "compiler-message":
            continue
        msg = m.get("message") or {}
        if msg.get("level") != "error":
            continue
        spans = [s for s in msg.get("spans") or [] if s.get("is_primary")]
        if not spans and re.match(r"aborting due to", msg.get("message", "")):
            continue
        s = spans[0] if spans else {}
        out.append(Error(code=(msg.get("code") or {}).get("code"), message=msg.get("message", ""),
                         file=s.get("file_name"), byte_start=s.get("byte_start"), byte_end=s.get("byte_end"),
                         in_macro=s.get("expansion") is not None, line=s.get("line_start")))
    return out


# --------------------------------------------------------------------------------------------- reading Rust


_RAW = re.compile(r'b?r(#*)"')
_CHAR = re.compile(r"'(?:\\(?:x[0-9a-fA-F]{2}|u\{[0-9a-fA-F]+\}|.)|[^\\'\n])'")


def _ident(c: str) -> bool:
    return c.isalnum() or c == "_"


def mask(text: str) -> str:
    """The text with comments blanked and string and char literals' contents filled with x, same length and lines,
    so braces, commas, and words found in it are code."""
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
        elif c in "br" and (i == 0 or not _ident(text[i - 1])) and (m := _RAW.match(text, i)):
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
        else:
            i += 1
    return "".join(out)


def _close(masked: str, open_at: int) -> int | None:
    """The index of the brace closing the one at open_at."""
    depth = 0
    for k in range(open_at, len(masked)):
        if masked[k] == "{":
            depth += 1
        elif masked[k] == "}":
            depth -= 1
            if depth == 0:
                return k
    return None


def _split_top(masked: str, a: int, b: int, *, types: bool = True) -> list[tuple[int, int]]:
    """(start, end) of each comma-separated piece of masked[a:b] at the top level of its brackets. types: angle
    brackets nest (a definition's types); in expressions they are comparisons and don't."""
    pieces, depth, start, k = [], 0, a, a
    while k < b:
        c = masked[k]
        if c in "([{" or (types and c == "<" and k + 1 < b and masked[k + 1] != "="):
            depth += 1
        elif c in ")]}" or (types and c == ">" and masked[k - 1] != "-" and masked[k - 1] != "="):
            depth -= 1
        elif c == "," and depth == 0:
            pieces.append((start, k))
            start = k + 1
        k += 1
    pieces.append((start, b))
    return [(s, e) for s, e in pieces if masked[s:e].strip()]


_ATTR_HEAD = re.compile(r"\s*#\s*\[")


def _strip_attrs(masked: str, s: int, e: int) -> tuple[int, list[str]]:
    """Skip the attributes at the start of masked[s:e]; returns the new start and the attributes' text."""
    attrs = []
    while (m := _ATTR_HEAD.match(masked, s)) and m.end() <= e:
        depth, k = 1, m.end()
        while k < e and depth:
            depth += {"[": 1, "]": -1}.get(masked[k], 0)
            k += 1
        attrs.append(masked[m.end():k - 1])
        s = k
    return s, attrs


_VIS = re.compile(r"\s*(?:pub\s*(?:\([^)]*\))?\s*)?")


def _named_fields(masked: str, open_at: int) -> list[tuple[str, str]] | None:
    """The (name, type) fields of the braced body opening at open_at; None if a field is cfg-gated."""
    close = _close(masked, open_at)
    if close is None:
        return None
    fields = []
    for s, e in _split_top(masked, open_at + 1, close):
        s, attrs = _strip_attrs(masked, s, e)
        if any(re.match(r"\s*cfg\b", a) for a in attrs):
            return None
        m = re.match(r"(?:r#)?(\w+)\s*:\s*", masked[_VIS.match(masked, s).end():e])
        if not m:
            return None
        start = _VIS.match(masked, s).end() + m.end()
        fields.append((m.group(1), " ".join(masked[start:e].split())))
    return fields


def _definitions(masked_sources: dict[str, str], kind: str, name: str) -> list[tuple[str, int]]:
    """(path, index just after the name) of each `struct name` or `enum name` definition."""
    pat = re.compile(rf"(?<![\w:]){kind}\s+{re.escape(name)}\b")
    return [(p, m.end()) for p, t in masked_sources.items() for m in pat.finditer(t)]


def _body_open(masked: str, k: int) -> int | None:
    """The `{` opening a definition's body after its name, past generics and a where clause; None for a tuple or
    unit struct."""
    depth = 0
    while k < len(masked):
        c = masked[k]
        if c == "<":
            depth += 1
        elif c == ">" and masked[k - 1] != "-":
            depth -= 1
        elif depth == 0 and c in "(;":
            return None
        elif depth == 0 and c == "{":
            return k
        k += 1
    return None


@functools.lru_cache(maxsize=512)
def _mask_cached(text: str) -> str:
    return mask(text)


def _masked(sources: dict[str, str]) -> dict[str, str]:
    return {p: _mask_cached(t) for p, t in sources.items()}


def _pick(defs: list[tuple[str, int]], crate: str | None) -> tuple[str, int] | None:
    if len(defs) > 1 and crate:
        defs = [d for d in defs if f"/{crate}/" in f"/{d[0]}" or f"/{crate.replace('_', '-')}/" in f"/{d[0]}"]
    return defs[0] if len(defs) == 1 else None


def fields_of(sources: dict[str, str], type_path: str, written: str) -> list[tuple[str, str]] | None:
    """The fields, in declared order, of the struct or struct-like variant a literal builds. type_path is the type
    rustc names (an enum, for a variant); written is the path at the literal (the variant is its last segment)."""
    ms = _masked(sources)
    segs = re.sub(r"<.*", "", type_path).split("::")
    name, crate = segs[-1], (segs[0] if len(segs) > 1 else None)
    variant = re.sub(r"<.*", "", written).split("::")[-1].strip()
    enums = [d for d in _definitions(ms, "enum", name) if _body_open(ms[d[0]], d[1]) is not None]
    if variant not in (name, "Self") and enums:  # rustc names the enum, the literal its variant
        hit = _pick(enums, crate)
        if hit is None:
            return None
        text = ms[hit[0]]
        open_at = _body_open(text, hit[1])
        close = _close(text, open_at)
        for s, e in _split_top(text, open_at + 1, close):
            s, _ = _strip_attrs(text, s, e)
            m = re.match(rf"\s*{re.escape(variant)}\s*\{{", text[s:e])
            if m:
                return _named_fields(text, s + m.end() - 1)
        return None
    hit = _pick([d for d in _definitions(ms, "struct", name) if _body_open(ms[d[0]], d[1]) is not None], crate)
    if hit is None:
        return None
    return _named_fields(ms[hit[0]], _body_open(ms[hit[0]], hit[1]))


def _implements_default(ms: dict[str, str], name: str) -> bool:
    if any(re.search(rf"\bimpl\b[^{{;]*?\bDefault\s+for\s+(?:\w+::)*{re.escape(name)}\b", t) for t in ms.values()):
        return True
    for kind in ("struct", "enum"):
        for p, end in _definitions(ms, kind, name):
            text = ms[p]
            k = text.rfind(kind, 0, end)
            before = text[:k]
            before = re.sub(r"pub\s*(?:\([^)]*\))?\s*$", "", before.rstrip()).rstrip()
            # the attributes immediately above the definition
            while before.endswith("]"):
                depth, j = 0, len(before) - 1
                while j >= 0:
                    depth += {"]": 1, "[": -1}.get(before[j], 0)
                    if depth == 0:
                        break
                    j -= 1
                attr = before[j:]
                if re.search(r"\bderive\s*\([^)]*\bDefault\b", attr):
                    return True
                before = before[:j].rstrip()
                if before.endswith("#"):
                    before = before[:-1].rstrip()
    return False


def empty_value(type_text: str, sources: dict[str, str], _depth: int = 0) -> str | None:
    """The empty value the rule gives a missing field of this type, or None where there is none."""
    t = re.sub(r"\s+", "", type_text)
    t = re.sub(r"^(?:::)?(?:std|core|alloc)::(?:\w+::)*", "", t)
    if t == "String":
        return "String::new()"
    if t.startswith("Vec<"):
        return "Vec::new()"
    if t.startswith("Option<"):
        return "None"
    if t in INTS:
        return "0"
    if t in ("f32", "f64"):
        return "0.0"
    if t == "bool":
        return "false"
    if t in ("&str", "&'staticstr"):
        return '""'
    m = re.fullmatch(r"(?:\w+::)*(\w+)(<.*>)?", t)
    if not m or _depth > 4:
        return None
    head = m.group(1)
    if head in STD_DEFAULT:
        return "Default::default()"
    ms = _masked(sources)
    aliases = [a for p, text in ms.items()
               for a in re.finditer(rf"(?<![\w:])type\s+{re.escape(head)}\s*=\s*([^;]+);", text)]
    if len(aliases) == 1 and not m.group(2):
        return empty_value(aliases[0].group(1), sources, _depth + 1)
    if _implements_default(ms, head):
        return "Default::default()"
    return None


# ------------------------------------------------------------------------------------------------- edits


def _char_index(text: str, byte: int) -> int:
    return len(text.encode("utf-8")[:byte].decode("utf-8", errors="ignore"))


def _insert_at(masked: str, close: int) -> tuple[int, bool]:
    """Where to insert before the closing brace at close (just after the last token), and whether a comma is
    needed first."""
    k = close - 1
    while k >= 0 and masked[k].isspace():
        k -= 1
    return k + 1, masked[k] not in ",{"


@dataclass
class Edit:
    file: str
    at: int  # character index in the file's current text
    text: str
    record: dict


def _brace_after(masked: str, k: int) -> int | None:
    while k < len(masked) and masked[k].isspace():
        k += 1
    return k if k < len(masked) and masked[k] == "{" else None


def edit_for(err: Error, text: str, sources: dict[str, str]) -> Edit | str:
    """The edit the rule makes for one error, or why it makes none."""
    if err.in_macro:
        return f"{err.code} at {err.file}:{err.line} is inside a macro"
    masked = mask(text)
    start, end = _char_index(text, err.byte_start), _char_index(text, err.byte_end)
    open_at = _brace_after(masked, end)
    if err.code == "E0063":
        m = re.search(r"in initializer of `([^`]+)`", err.message)
        if not m or open_at is None:
            return f"E0063 at {err.file}:{err.line}: no struct literal found"
        type_path, written = m.group(1), text[start:end]
        fields = fields_of(sources, type_path, written)
        if fields is None:
            return f"E0063 at {err.file}:{err.line}: no single definition of `{written}` ({type_path}) in the arm's source"
        close = _close(masked, open_at)
        present = set()
        for s, e in _split_top(masked, open_at + 1, close, types=False):
            piece = masked[s:e].strip()
            if piece.startswith(".."):
                return f"E0063 at {err.file}:{err.line}: the literal has a base expression"
            fm = re.match(r"(?:r#)?(\w+)\s*(?::(?!:)|$)", piece)
            if fm:
                present.add(fm.group(1))
        missing = [(f, ty) for f, ty in fields if f not in present]
        named = re.findall(r"`(\w+)`", err.message.split(" in initializer of ")[0])
        others = re.search(r"and (\d+) other fields?", err.message)
        if not set(named) <= {f for f, _ in missing} or len(missing) != len(named) + (int(others.group(1)) if others else 0):
            return f"E0063 at {err.file}:{err.line}: the fields rustc names don't match the arm's definition of `{written}`"
        values = {}
        for f, ty in missing:
            v = empty_value(ty, sources)
            if v is None:
                return f"E0063 at {err.file}:{err.line}: no empty value for field `{f}` of type `{ty}`"
            values[f] = v
        at, comma = _insert_at(masked, close)
        ins = (", " if comma else " ") + ", ".join(f"{f}: {v}" for f, v in values.items())
        return Edit(err.file, at, ins, {"code": "E0063", "edit": "fields", "type": type_path, "literal": written,
                                        "fields": values})
    if err.code == "E0004":
        if not re.search(r"(?<!\w)match\s*$", masked[:start]) or open_at is None:
            return f"E0004 at {err.file}:{err.line}: not a match expression"
        close = _close(masked, open_at)
        at, comma = _insert_at(masked, close)
        uncovered = re.sub(r"^non-exhaustive patterns: ", "", err.message)
        return Edit(err.file, at, (", " if comma else " ") + WILDCARD,
                    {"code": "E0004", "edit": "wildcard arm", "uncovered": uncovered})
    return f"{err.code or 'an error'} at {err.file}:{err.line} is not one the rule adapts: {err.message}"


def adapt_target(build: Callable[[], str], files: dict[str, str], sources: Callable[[], dict[str, str]],
                 put: Callable[[str, str], None], *, max_rounds: int = MAX_ROUNDS) -> tuple[dict, dict[str, str]]:
    """Build a held-out target; while it fails only on errors the rule covers, edit its files (put back through put)
    and build again. Returns the record and the files as they stand. The record's status is "built" (nothing
    needed), "adapted" (built after edits), or "not adapted" (a compile failure the rule doesn't cover)."""
    files, edits = dict(files), []
    for rnd in range(1, max_rounds + 1):
        output = build()
        if built(output):
            return {"status": "adapted" if edits else "built", "rounds": rnd, "edits": edits}, files
        errs = errors(output)
        brief = [e.brief() for e in errs][:20]

        def fail(reason: str) -> tuple[dict, dict[str, str]]:
            return {"status": "not adapted", "rounds": rnd, "edits": edits, "reason": reason, "errors": brief}, files
        if not errs:
            return fail("cargo reported no build result: " + output.strip()[-300:])
        if rnd == max_rounds:
            return fail(f"still failing after {max_rounds} rounds")
        planned: list[Edit] = []
        for e in errs:
            if e.code not in ADAPTED:
                return fail(f"{e.code or 'an error'} at {e.file}:{e.line} is not one the rule adapts: {e.message}")
        for e in errs:
            if e.file not in files:
                return fail(f"{e.code} at {e.file}:{e.line} is outside the held-out files")
            got = edit_for(e, files[e.file], sources())
            if isinstance(got, str):
                return fail(got)
            planned.append(got)
        seen = set()
        for ed in planned:
            if (ed.file, ed.at) in seen:
                continue
            seen.add((ed.file, ed.at))
            text = files[ed.file]
            edits.append({"file": ed.file, "line": text.count("\n", 0, ed.at) + 1, **ed.record, "text": ed.text})
        for path in sorted({ed.file for ed in planned}):
            text = files[path]
            done = set()
            for ed in sorted((x for x in planned if x.file == path), key=lambda x: -x.at):
                if ed.at in done:
                    continue
                done.add(ed.at)
                text = text[:ed.at] + ed.text + text[ed.at:]
            files[path] = text
            put(path, text)
    return {"status": "not adapted", "rounds": max_rounds, "edits": edits,
            "reason": f"still failing after {max_rounds} rounds"}, files


def reached_adaptation(log: str) -> list[str]:
    """The tests in a cargo test log that panicked in an adapted wildcard arm."""
    out = []
    for m in re.finditer(r"(?ms)^---- (\S+) stdout ----\n(.*?)(?=^---- \S+ stdout ----|^failures:\s*$|\Z)", log):
        if MARK in m.group(2):
            out.append(m.group(1))
    return sorted(out)


# ------------------------------------------------------------------------------------------- the arm's source


SOURCES_SCRIPT = (f"cd /work/app && find . \\( -path ./target -o -path ./.git -o -path ./.jj -o -path '*/tests' \\) -prune "
                  f"-o -name '*.rs' -type f -print | sort | while read -r f; do printf '\\n%s %s\\n' '{SOURCE_MARK}' \"$f\"; "
                  f"cat \"$f\"; done")


def arm_sources(ck) -> dict[str, str]:
    """The arm's Rust source outside test directories, by path from the workspace root."""
    out, path, buf = {}, None, []
    for line in ck.sh(SOURCES_SCRIPT, check=False).split("\n"):
        if line.startswith(SOURCE_MARK + " "):
            if path:
                out[path] = "\n".join(buf)
            path, buf = line[len(SOURCE_MARK) + 1:].removeprefix("./"), []
        elif path is not None:
            buf.append(line)
    if path:
        out[path] = "\n".join(buf)
    return out
