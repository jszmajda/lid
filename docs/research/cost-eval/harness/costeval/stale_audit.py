"""The stale-intent audit (design.md, "The growth test"): a blind reader judges each test and doc that a course change
touched, or should have touched (it mentions a term for the area the rule lives in), asking whether anything in its
names, comments, or assertions contradicts current intent. The retired intent is shown as context where there is one
(for a rescope, the old version); an emerging change is audited against current intent alone. Arm labels never reach
the reader, and methodology vocabulary (spec IDs, `@spec` annotations, EARS, HLD, LLD, the docs/intent tree) is stripped
from what it reads, with "spec" reading as "requirement" in comments, docstrings and docs, so a LID arm's files read
like any other arm's."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable

TEMPLATE = Path(__file__).resolve().parent.parent / "prompts" / "stale-intent-audit.md"
PARTS = ("name", "comments", "assertions")
PART_RULINGS = ("current", "contradicts", "mixed", "silent")
VERDICTS = ("current", "stale", "mixed", "unrelated")
SCHEMA = {
    "type": "object", "additionalProperties": False, "required": [*PARTS, "verdict", "evidence", "reason"],
    "properties": {**{p: {"type": "string", "enum": list(PART_RULINGS)} for p in PARTS},
                   "verdict": {"type": "string", "enum": list(VERDICTS)},
                   "evidence": {"type": "array", "items": {"type": "integer"}}, "reason": {"type": "string"}},
}
TEST_OR_DOC = re.compile(r"(^|/)(tests?|spec|__tests__)/|(^|/)test_[^/]*$|_test\.[a-z]+$|\.(test|spec)\.[a-z]+$|"
                         r"(^|/)docs?/|\.md$", re.I)
SPEC_ID = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d{3,}[a-z]?\b")
VOCABULARY = re.compile(r"@spec\b|\bEARS\b|\bHLD\b|\bLLD\b|\bLID\b|linked[- ]intent|arrows? of intent|"
                        r"\bdocs/intent/[^\s)]*|\bsub-HLD\b|\b[\w-]*specs?\.md\b", re.I)
FILLER = {"see", "per", "the", "in", "spec", "specs", "and", "cf", "also", "its", "as", "under", "amended"}


def _citation(m: re.Match) -> str:
    """A parenthetical that cites the methodology goes whole when nothing but filler is left of it."""
    inner = m.group(2)
    if not (SPEC_ID.search(inner) or VOCABULARY.search(inner)):
        return m.group(0)
    rest = VOCABULARY.sub(" ", SPEC_ID.sub(" ", inner))
    words = [w for w in re.findall(r"[A-Za-z0-9]+", rest) if w.lower() not in FILLER]
    return f"{m.group(1)}({' '.join(rest.split())})" if words else ""


def _spans_python(text: str) -> list[tuple[int, int]]:
    """Comments and docstrings (any triple-quoted string) in Python source, as character spans."""
    spans, i, n = [], 0, len(text)
    while i < n:
        if text.startswith(('"""', "'''"), i):
            q = text[i:i + 3]
            j = text.find(q, i + 3)
            j = n if j < 0 else j + 3
            spans.append((i, j))
            i = j
        elif text[i] in "\"'":
            q, j = text[i], i + 1
            while j < n and text[j] not in (q, "\n"):
                j += 2 if text[j] == "\\" else 1
            i = j + 1
        elif text[i] == "#":
            j = text.find("\n", i)
            j = n if j < 0 else j
            spans.append((i, j))
            i = j
        else:
            i += 1
    return spans


def _spans_c(text: str) -> list[tuple[int, int]]:
    """Comments in C-like source (JavaScript, TypeScript, Go, Rust, Java): `//` to the line's end and `/* */`."""
    spans, i, n = [], 0, len(text)
    while i < n:
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            spans.append((i, j))
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            spans.append((i, j))
            i = j
        elif text[i] in "\"'`":
            q, j = text[i], i + 1
            while j < n and text[j] != q and (q == "`" or text[j] != "\n"):
                j += 2 if text[j] == "\\" else 1
            i = j + 1
        else:
            i += 1
    return spans


def _requirement(m: re.Match) -> str:
    word = "requirement" + ("s" if m.group(1) else "")
    return word.capitalize() if m.group(0)[0].isupper() else word


def _requirements_in_prose(text: str, path: str) -> str:
    """"spec" and "specs" as "requirement" and "requirements" in comments, docstrings, and docs, never in code."""
    word = re.compile(r"\b[Ss]pec(s)?\b")
    if not path or re.search(r"\.(md|txt|rst|adoc)$", path, re.I):
        return word.sub(_requirement, text)
    spans = _spans_python(text) if path.endswith(".py") else _spans_c(text)
    out, at = [], 0
    for a, b in spans:
        out += [text[at:a], word.sub(_requirement, text[a:b])]
        at = b
    return "".join(out + [text[at:]])


def neutralize(text: str, path: str = "") -> str:
    """The file without methodology vocabulary: annotation-only lines go, citations of the methodology go whole,
    spec IDs and the methodology's words are removed, a comment left with nothing to say goes, and "spec" reads as
    "requirement" in comments, docstrings, and docs. Code is never rewritten beyond those words."""
    return _requirements_in_prose(_neutral_lines(text), path)


def _neutral_lines(text: str) -> str:
    out = []
    for line in text.splitlines():
        if re.match(r"^\s*(//+|#+|\*|--)\s*@spec\b", line):
            continue
        new = re.sub(r"(\s*)\(([^()]*)\)", _citation, line)
        new = VOCABULARY.sub("", SPEC_ID.sub("", new))
        new = re.sub(r"\b(?:see|per|under) the\s*(?=[).,;:]|$)", "", new)
        new = re.sub(r"\s*(#|//)\s*[:;,.]?\s*$", "", new)
        if new != line:
            new = re.sub(r"(?<=\S)[ \t]{2,}", " ", new)
        out.append(new.rstrip())
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def is_test_or_doc(path: str) -> bool:
    return bool(TEST_OR_DOC.search(path))


def audit_files(touched: list[str], files: dict[str, str], terms: list[str] = ()) -> list[str]:
    """The tests and docs a course change touched (its commit's paths), and those it should have touched: tests and
    docs at the checkpoint that mention one of the retired rule's terms."""
    want = {p for p in touched if is_test_or_doc(p) and p in files and Path(p).name.lower() != "readme.md"}
    for p, text in files.items():
        if is_test_or_doc(p) and any(t.lower() in text.lower() for t in terms if t):
            want.add(p)
    return sorted(want)


def prompt(*, path: str, text: str, current: str, retired: str | None) -> str:
    numbered = "\n".join(f"{k:>5}  {line}" for k, line in enumerate(neutralize(text, path).splitlines(), start=1))
    retired_block = (f"What was intended before, and is no longer (context only: a part that describes it contradicts "
                     f"what is intended now):\n\n<retired>\n{retired.strip()}\n</retired>\n\n" if retired else "")
    fills = {"CURRENT": current.strip(), "RETIRED_BLOCK": retired_block, "PATH": path, "FILE": numbered}
    return re.sub(r"\{([A-Z_]+)\}", lambda m: fills[m.group(1)], TEMPLATE.read_text(encoding="utf-8"))


def check(ruling, *, lines: int) -> list[str]:
    if not isinstance(ruling, dict):
        return ["no ruling"]
    problems = [f"{p}: {ruling.get(p)!r}" for p in PARTS if ruling.get(p) not in PART_RULINGS]
    if ruling.get("verdict") not in VERDICTS:
        problems.append(f"verdict {ruling.get('verdict')!r}")
    ev = ruling.get("evidence") or []
    if ruling.get("verdict") != "unrelated" and not ev:
        problems.append("no evidence")
    if any(not 1 <= n <= lines for n in ev):
        problems.append(f"evidence lines outside 1-{lines}")
    if len((ruling.get("reason") or "").split()) < 4:
        problems.append("a reason too short to explain the verdict")
    return problems


def audit(files: dict[str, str], *, current: str, retired: str | None, ask: Callable[[str], tuple], attempts: int = 3) -> dict:
    """One ruling per file; ask(prompt) -> (structured ruling, cost). A file with no valid ruling is recorded so."""
    out, cost = {}, 0.0
    for path, text in sorted(files.items()):
        p = prompt(path=path, text=text, current=current, retired=retired)
        n = len(neutralize(text, path).splitlines())
        tries = []
        for _ in range(attempts):
            ruling, c = ask(p)
            cost += c or 0.0
            problems = check(ruling, lines=n)
            tries.append({"ruling": ruling, "problems": problems})
            if not problems:
                break
        out[path] = {**(tries[-1]["ruling"] if not tries[-1]["problems"] else {"verdict": None}), "tries": len(tries),
                     "problems": tries[-1]["problems"]}
    count = lambda v: sum(r.get("verdict") == v for r in out.values())
    return {"files": out, "current": count("current"), "stale": count("stale"), "mixed": count("mixed"),
            "unrelated": count("unrelated"), "no_ruling": count(None), "cost_usd": round(cost, 4)}
