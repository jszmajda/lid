"""Convert openGym's M2h change set into the harness's seed formats (plan.md, M2h: the brownfield test).

m2h-changes.md holds changes 1 to 12, each applied on its own to its arm's start and discarded: eight cross-component
changes (api-change-app-depends or client-change-api-depends, intent distance "other part"), each with a dependency
row, and four controls (intent distance "other file, same part"), each with a comparison row. Each change gives its
fields (with a searchability tier), the owner's request, new rows OGM-NNkk (stated or askable, a recall line for each
askable row), guard rows, behaviour to keep (citations are paths, `path#symbol`, `path:lines` or `path::test title`),
the "Dependency exercised only if" line or the comparison row, the deliberate change, retired tests with their grading
treatment, why the other part is needed (1 to 8), and repair reports. This writes, in M2f's formats
(costeval/m2f_seed.py):

- change-script.md: each change in the change-script format, its **Introduces:** line naming its OGM rows;
- oracle.md: an empty start section (the brief reaches the owner as the brief), with no start items, then each change's request,
  verbatim, and its rows in the item table;
- owner-items.json: each askable row's recall line and salience tier (from m2h/salience.json when it exists, else a
  placeholder "medium"), and, beside the items, the recall lines given only on a condition (CONDITIONAL_RECALL);
- repair-reports.json: {"OGM-0101": {"report": ...}, ..., "DEP-1": {"report": ..., "change": 1}};
- kept-behaviour.json: per change, its rows to keep under IDs OGMK-NNkk in table order (the dependency row or the
  comparison row is the one the change names), its searchability tier (with the plan's signpost, where it gives one),
  its dependency precondition or comparison row, the rows the joint outcome counts, its retired tests, and its notes;
- guard-rows.json: m2h-guard-rows.json's rows, each with any condition it runs under (CONDITIONAL_GUARDS).

check_seed validates the written files with the harness's own parsers. Malformed source refuses to convert, naming
what's wrong.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import repair, simulator
from .m2f_seed import (COMMENT, KEEP_RULE, NUMBERS, Row, _blocks, _json, _labelled, _split_inline, _table, _unquote,
                       guard_problems, load_salience)

HARNESS = Path(__file__).resolve().parent.parent
HIDDEN = HARNESS.parent / "seeds" / "opengym" / "hidden"
SOURCE = "m2h-changes.md"
GUARDS = "m2h-guard-rows.json"
PLAN = "m2h-plan.md"
TEST_INDEX = "prompts-m2h/test-index.json"
PATHS = "prompts-m2h/paths.json"
BRIEFS = "prompts-m2h/briefs-m2h.json"
BRIEF = "brief.md"  # the owner's public brief, in the seed folder beside hidden/
OUT = "m2h"
PIN = "e4a68a9"
STARTS = ('bare: `d96444e` ("Start"); LID Full: one `/map-codebase` mapping per replicate, each committed on the same '
          'Start (`489e0e0`, `eaf96bf`, `320c3f6`)')

OUTPUTS = ("change-script.md", "oracle.md", "owner-items.json", "repair-reports.json", "kept-behaviour.json",
           "guard-rows.json")
PLACEHOLDER_TIERS = "placeholder: medium for every row (no salience rating yet)"
RATED_TIERS = "rated: from m2h/salience.json"
CROSS_TYPES = ("api-change-app-depends", "client-change-api-depends")
CONTROL = "control"
CROSS_DISTANCE, CONTROL_DISTANCE = "other part", "other file, same part"
FALLBACK_DISTANCE_FIELD = "Part distance"
TIERS = ("documented", "one-step grep", "hidden")
KINDS = ("Stated", "Askable")
FIELDS = ("Type", "Intent distance", "Edits part", "Edits file", "Intent lives in", "Searchability tier")
ROW_HEADER = ["ID", "Behaviour", "Disclosure kind", "Check"]
KEEP_HEADER = ["Behaviour", "Established in", "How a careless version breaks it", "Check"]
ROW_ID = re.compile(r"OGM-(\d\d)(\d\d)$")
OGM = re.compile(r"\bOGMK?-\d{4}\b")
QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})
DASH = " — "
CITE = re.compile(r"(?P<path>[\w./@+-]+?)(?:::(?P<test>.+)|:(?P<a>\d+)(?:-(?P<b>\d+))?|#(?P<sym>.+))?")
TEST_FILE = r"[\w./@+-]+\.(?:m?jsx?|cjs|tsx?)"
TEST_BULLET = re.compile(rf"^- `?(?P<path>{TEST_FILE})`?::(?P<rest>.+)$")
RUN_TIME = re.compile(rf"^- `?(?P<path>{TEST_FILE})`?, the (?P<count>\w+) (?:\w+ )?tests whose titles are made at run "
                      rf"time from its `(?P<var>[^`]+)` \(line (?P<line>\d+)\): (?P<titles>.+?){DASH}(?P<reason>.+)$")
GROUP = re.compile(r"^\*\*(?P<label>[^*\n]+?) \((?P<n>\d+)\):\*\*$")
DEP_MARK = "**Dependency exercised only if**"
ORDINALS = {w: i for i, w in enumerate("zeroth first second third fourth fifth sixth seventh eighth".split())}

# Rows whose check runs only on some builds: the guard is exempt from the absent-conflict rule like any other, but a
# build without what its condition names reports it not exercised (never met), and so does the pin.
CONDITIONAL_GUARDS = {
    "OGM-0403": {"runs_only_if": "the build has the cycle log", "otherwise": "not exercised",
                 "quote": "OGM-0403 is a conditional guard: it runs only on a build that has the log"},
}
# Recall lines the owner gives only on a condition. The simulator reads only "items", so these sit beside them in
# owner-items.json: the record travels with the seed, and the simulator ignores it until it acts on it.
CONDITIONAL_RECALL = {
    "OGM-0405": {"given_only": "in answer to a question about privacy",
                 "quote": "OGM-0405's recall line is given only in answer to a question about privacy"},
}
# What the joint-outcome report counts differently for a change (m2h-plan.md, "Joint outcome";
# m2h-harness-needs.md, "The joint-outcome report"). Each quote must still be in the change's text.
JOINT_NOTES = {
    3: {"new_row_score_excludes": ["OGM-0301", "OGM-0302"],
        "quotes": ["Without OGM-0301 and OGM-0302 no non-guard new row is left, so that score is N/A"]},
    4: {"new_row_score_excludes": ["OGM-0405"], "beside_dependency": ["OGM-0405"],
        "dependency_rate": {"primary": "over all forks",
                            "apart": "over forks whose build added a new key (each build's storage choice recorded)"},
        "quotes": ["OGM-0405 is reported beside the dependency rate, not inside the new-row score",
                   "The dependency rate over all forks is the primary figure"]},
    5: {"kept_only": ["OGMK-0504"],
        "quotes": ["This is a secondary kept check, graded as a kept row, not as a second dependency"]},
    6: {"kept_only": ["OGMK-0602"],
        "quotes": ["the phone's refusal sentence (the second kept row) is graded as a kept row only"]},
}


@dataclass(frozen=True)
class Expected:
    """The counts --check holds the change set to, read off m2h-changes.md, m2h-guard-rows.json and m2h-plan.md."""
    changes: tuple[int, ...] = tuple(range(1, 13))
    cross: tuple[int, ...] = tuple(range(1, 9))  # each with a dependency row; 9 to 12 are controls
    rows: int = 35
    stated: int = 20
    askable: int = 15
    guards: int = 10
    kept: int = 37
    retired: int = 56
    tiers: tuple = (("documented", (3, 8, 11)), ("one-step grep", (2, 4, 5, 6, 7, 9, 10, 12)), ("hidden", (1,)))


EXPECTED = Expected()


@dataclass
class Sources:
    """What the converter reads. Only the change set, the brief and the guard rows are required."""
    source: str  # m2h-changes.md
    brief: str  # ../brief.md
    guards: dict  # m2h-guard-rows.json
    plan: str | None = None  # m2h-plan.md: signposts and the tier cross-check
    test_index: dict | None = None  # {path: [test titles]} at the pin
    paths: set[str] | None = None  # the pinned tree's tracked paths
    briefs: dict | None = None  # briefs-m2h.json: each change's dependency or kept row anchor and known retired tests


@dataclass
class KeepRow:
    id: str
    role: str  # dependency, comparison or kept
    behaviour: str
    established_in: list[str]
    citations: list[dict]
    breaks: str
    check: str

    def record(self) -> dict:
        return {"id": self.id, "role": self.role, "dependency": self.role == "dependency", "behaviour": self.behaviour,
                "established_in": self.established_in, "citations": self.citations, "breaks": self.breaks,
                "check": self.check}


@dataclass
class M2hChange:
    number: int
    title: str
    type: str
    intent_distance: str
    edits_part: str
    edits_file: str
    intent_lives_in: str
    tier: str
    tier_why: str
    request_lines: list[str]
    request: str
    text: str  # the change's own text, comments removed
    rows: list[Row] = field(default_factory=list)
    guards_declared: list[str] = field(default_factory=list)  # its **Guard row:** lines
    row_preconditions: dict[str, str] = field(default_factory=dict)  # a row's "Exercised only if" in its check
    left_to_developer: str | None = None
    keep: list[KeepRow] = field(default_factory=list)
    dependency_if: str | None = None
    dependency_text: str | None = None
    comparison: dict | None = None
    deliberate_change: str | None = None
    retired_tests: list[str] = field(default_factory=list)
    retired: list[dict] = field(default_factory=list)  # {"test", "reason", "treatment", ["run_time_title", "from"]}
    retired_note: str | None = None
    why_other_part: str | None = None
    reports: dict[str, str] = field(default_factory=dict)
    notes: list[dict] = field(default_factory=list)

    @property
    def cross(self) -> bool:
        return self.type in CROSS_TYPES


# ------------------------------------------------------------------------------------------------ citations


def parse_citation(s: str) -> dict:
    """One citation: a path, `path#symbol`, `path:lines` or `path::test title` (a title may hold anything)."""
    c = s.strip().strip("`").strip()
    m = CITE.fullmatch(c)
    if not m or "." not in m.group("path"):
        raise ValueError(f"can't read the citation {s!r}")
    path = m.group("path")
    if m.group("test") is not None:
        return {"path": path, "kind": "test", "test": m.group("test").strip()}
    if m.group("a"):
        a = int(m.group("a"))
        return {"path": path, "kind": "lines", "from": a, "to": int(m.group("b") or a)}
    if m.group("sym") is not None:
        return {"path": path, "kind": "symbol", "symbol": m.group("sym").strip()}
    return {"path": path, "kind": "path"}


def is_citation(s: str) -> bool:
    try:
        parse_citation(s)
    except ValueError:
        return False
    return True


def split_citations(cell: str) -> list[str]:
    """An "Established in" cell's citations, split at semicolons. A test title may hold a semicolon, so a piece that
    isn't a citation is joined back onto the test citation before it, with its separator; one that follows anything
    else is refused."""
    parts = re.split(r"(;\s*)", cell.replace("<br>", ";"))
    out: list[str] = []
    for i in range(0, len(parts), 2):
        piece, sep_before = parts[i].strip(), parts[i - 1] if i else ""
        if not piece:
            continue
        if is_citation(piece):
            out.append(piece.strip("`").strip())
        elif out and parse_citation(out[-1])["kind"] == "test":
            out[-1] += sep_before + piece
        else:
            raise ValueError(f"can't read the citation {piece!r} in {cell!r}")
    return out


def split_test(path: str, rest: str, test_index: dict | None) -> tuple[str, str | None]:
    """A retired test's title and the reason after it, from what follows `path::`. The title runs to a " — " that
    starts the reason, and a title may hold " — " itself: with the pin's test index, the longest candidate that names
    a test of the file wins (spelled as the index spells it); without one, the title runs to the last " — "."""
    parts = rest.split(DASH)
    titles = (test_index or {}).get(path)
    if titles is not None:
        norm = {t.translate(QUOTES): t for t in titles}
        for k in range(len(parts), 0, -1):
            cand = DASH.join(parts[:k]).strip().strip("`").strip()
            if cand.translate(QUOTES) in norm:
                return norm[cand.translate(QUOTES)], DASH.join(parts[k:]).strip() or None
        raise ValueError(f"no test titled {DASH.join(parts[:1]).strip()!r} (or a longer title) in {path}")
    if len(parts) == 1:
        return rest.strip().strip("`"), None
    return DASH.join(parts[:-1]).strip().strip("`"), parts[-1].strip()


# ------------------------------------------------------------------------------------------------ parsing


def change_of(iid: str) -> int:
    m = ROW_ID.match(iid)
    if not m:
        raise ValueError(f"{iid}: not an OGM-<change><two digits> identifier")
    return int(m.group(1))


def _norm(s: str) -> str:
    return " ".join(s.translate(QUOTES).split())


def _number(word: str) -> int | None:
    return int(word) if word.isdigit() else NUMBERS.get(word.lower())


def _summary_table(text: str) -> tuple[str, list[list[str]]]:
    """The closing table (change, type, intent distance, edits part, files) and its heading, removed from the text."""
    lines, kept, rows, i = text.splitlines(), [], [], 0
    while i < len(lines):
        if lines[i].strip().startswith("| Change |"):
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            rows += _table("\n".join(lines[i:j]))[1]
            while kept and not kept[-1].strip():
                kept.pop()
            if kept and re.fullmatch(r"#{2,3} Summary", kept[-1].strip()):
                kept.pop()
            i = j
            continue
        kept.append(lines[i])
        i += 1
    return "\n".join(kept) + "\n", rows


def _retired(n: int, section: str, test_index: dict | None) -> list[dict]:
    """The retired tests, each with its reason and grading treatment, checked against the counts the section states."""
    out: list[dict] = []
    groups: dict[str, list[int]] = {}
    group = None
    for line in section.splitlines():
        s = line.rstrip()
        g = GROUP.match(s.strip())
        if g:
            group = g.group("label")
            groups[group] = [int(g.group("n")), 0]
            continue
        if not s.startswith("- "):
            continue
        before = len(out)
        if (m := RUN_TIME.match(s)):
            titles = [t.strip() for t in m.group("titles").split(";") if t.strip()]
            if _number(m.group("count")) != len(titles):
                raise ValueError(f"change {n}: {m.group('count')} run-time tests in {m.group('path')}, but it names "
                                 f"{len(titles)}")
            out += [{"test": f"{m.group('path')}::{t}", "reason": m.group("reason").strip(), "run_time_title": True,
                     "from": f"`{m.group('var')}` (line {m.group('line')})"} for t in titles]
        elif (m := TEST_BULLET.match(s)):
            try:
                title, reason = split_test(m.group("path"), m.group("rest"), test_index)
            except ValueError as e:
                raise ValueError(f"change {n}: retired test: {e}") from None
            out.append({"test": f"{m.group('path')}::{title}", "reason": reason})
        elif s.startswith("- **"):
            continue  # a note's bullet, kept with the section's text
        else:
            raise ValueError(f"change {n}: can't read the retired test in {s!r}")
        if group:
            groups[group][1] += len(out) - before

    text = _norm(section)
    if "grader-owned adjusted copy" in text:
        base = "adjusted copy"
    elif "grader-owned patch" in text:
        base = "patch"
    else:
        base = None
    for r in out:
        reason = _norm(r["reason"] or "")
        if base == "adjusted copy":
            r["treatment"] = "adjusted copy"
        elif base == "patch" and "pins the old default" in reason:
            r["treatment"] = "patch: default expectation"
        elif base == "patch" and "opted in" in reason:
            r["treatment"] = "patch: fixture opted in"
        else:
            raise ValueError(f"change {n}: retired test {r['test']} has no grading treatment (no grader-owned "
                             f"adjusted copy, or a patch its reason doesn't place)")

    def says(what: str, stated: int | None, got: int) -> None:
        if stated is not None and stated != got:
            raise ValueError(f"change {n}: the retired tests' text says {stated} {what}, but the section lists {got}")
    for m in re.finditer(r"\bfails (?:the )?(\d+|[a-z]+) (?:existing )?tests?\b", text):
        says("tests", 0 if m.group(1) == "no" else _number(m.group(1)), len(out))
    m = re.search(r"\b(\d+) in the API and (\d+) in (\d+) web-app files\b", text)
    if m:
        says("API tests", int(m.group(1)), sum(r["test"].startswith("api/") for r in out))
        says("web-app tests", int(m.group(2)), sum(r["test"].startswith("frontend/") for r in out))
        says("web-app files", int(m.group(3)),
             len({r["test"].split("::")[0] for r in out if r["test"].startswith("frontend/")}))
    for label, (stated, got) in groups.items():
        says(f"tests under {label}", stated, got)
    m = re.search(r"\*\*(\w+) default tests?\*\*", text)
    if m:
        says("default tests", _number(m.group(1)), sum(r["treatment"] == "patch: default expectation" for r in out))
    m = re.search(r"\*\*the other (\w+)\*\*", text)
    if m:
        says("opted-in tests", _number(m.group(1)), sum(r["treatment"] == "patch: fixture opted in" for r in out))
    return out


def _parse_change(n: int, title: str, body: str, test_index: dict | None) -> M2hChange:
    parts = re.split(r"(?m)^### ", body)
    head, sections = parts[0], []
    for p in parts[1:]:
        h, _, b = p.partition("\n")
        sections.append((h.strip(), b))
    secs = dict(sections)
    fields = {}
    for name in FIELDS:
        m = re.search(rf"(?m)^\*\*{re.escape(name)}:\*\*\s*(.+?)\s*$", head)
        if not m:
            raise ValueError(f"change {n}: no **{name}:** field")
        fields[name] = m.group(1)
    kind = fields["Type"]
    if kind not in (*CROSS_TYPES, CONTROL):
        raise ValueError(f"change {n}: type {kind!r}, not {', '.join(CROSS_TYPES)} or {CONTROL}")
    want = CONTROL_DISTANCE if kind == CONTROL else CROSS_DISTANCE
    if fields["Intent distance"] != want:
        what = "control" if kind == CONTROL else "cross-component change"
        raise ValueError(f"change {n}: a {what} at intent distance {fields['Intent distance']!r}, not {want!r}")
    tier, _, why = fields["Searchability tier"].partition(". ")
    tier = tier.strip().rstrip(".")
    if tier not in TIERS:
        raise ValueError(f"change {n}: searchability tier {tier!r}, not {', '.join(TIERS)}")
    req = secs.get("Owner request", "")
    request = simulator._quote(req)
    if not request:
        raise ValueError(f"change {n}: no quoted owner request")
    c = M2hChange(n, title, kind, fields["Intent distance"], fields["Edits part"], fields["Edits file"],
                  fields["Intent lives in"], tier, why.strip(), [l.rstrip() for l in req.splitlines() if l.startswith(">")],
                  request, body.strip())

    comparison_text = None
    for heading, text in sections:
        for block in _blocks(text):
            if block.startswith(("|", ">", "- ")):
                continue  # tables, the owner's words and bullets are each read with their section
            if block.startswith(DEP_MARK):
                c.dependency_text = block
                continue
            lab = _labelled(block)
            if lab is None:
                lead, inline = _split_inline(block)
                if heading not in ("Why the other part is needed", "Retired tests"):
                    c.notes.append({"section": heading, "label": None, "text": lead})
                c.notes += [{"section": heading, "label": label, "text": note} for label, note in inline]
                continue
            label, rest = lab
            if label in FIELDS or (heading == "Retired tests" and GROUP.match(block.splitlines()[0].strip())):
                continue
            if label == "Guard row":
                c.guards_declared += re.findall(r"OGM-\d{4}", rest.split(". ")[0])
                continue
            if label == "Comparison row":
                comparison_text = block
                continue
            value, inline = _split_inline(rest)
            if label == "Left to the developer":
                c.left_to_developer = value
            elif label == "Deliberate change":
                c.deliberate_change = value
            else:
                c.notes.append({"section": heading, "label": label, "text": value})
            c.notes += [{"section": heading, "label": note_label, "text": note} for note_label, note in inline]

    # new rows, their kinds, recall lines, and any row exercised only on a condition
    tables = [_table(b) for b in _blocks(secs.get("New rows", "")) if b.startswith("|")]
    if len(tables) != 1 or tables[0][0] != ROW_HEADER:
        raise ValueError(f"change {n}: no new-rows table headed {' | '.join(ROW_HEADER)}")
    for cells in tables[0][1]:
        if len(cells) != 4:
            raise ValueError(f"change {n}: a new row with {len(cells)} cells: {cells[:1]}")
        c.rows.append(Row(cells[0], cells[1], cells[2], cells[3]))
    ids = [r.id for r in c.rows]
    want_ids = [f"OGM-{n:02d}{k:02d}" for k in range(1, len(ids) + 1)]
    if not ids or ids != want_ids:
        raise ValueError(f"change {n}: new rows {ids} out of sequence, not {want_ids}")
    for r in c.rows:
        if r.kind not in KINDS:
            raise ValueError(f"{r.id}: disclosure kind {r.kind!r}; M2h rows are Stated or Askable")
        m = re.search(r"\bExercised only if (.+?)\.(?=\s|$)", r.check)
        if m:
            c.row_preconditions[r.id] = m.group(1).strip()
    by_id = {r.id: r for r in c.rows}
    for m in re.finditer(r"(?m)^- \*\*(OGM-\d+)\*\* (\w+)[^:\n]*:\s*(.+)$", secs.get("New rows", "")):
        rid, what, line = m.groups()
        if what != "recall":
            raise ValueError(f"{rid}: a {what} line; M2h rows are Stated or Askable, each askable one with a recall line")
        if rid not in by_id or by_id[rid].kind != "Askable":
            raise ValueError(f"{rid}: a recall line for a row that isn't an askable row of change {n}")
        if by_id[rid].recall is not None:
            raise ValueError(f"{rid}: two recall lines")
        by_id[rid].recall = _unquote(line)
    for r in c.rows:
        if r.kind == "Askable" and not r.recall:
            raise ValueError(f"{r.id}: an askable row with no recall line")
    for g in c.guards_declared:
        if g not in by_id:
            raise ValueError(f"change {n}: a **Guard row:** line for {g}, which isn't one of its rows")

    # behaviour to keep, with each row's citations
    tables = [_table(b) for b in _blocks(secs.get("Behaviour to keep", "")) if b.startswith("|")]
    if len(tables) != 1 or tables[0][0] != KEEP_HEADER:
        raise ValueError(f"change {n}: no behaviour-to-keep table headed {' | '.join(KEEP_HEADER)}")
    for k, cells in enumerate(tables[0][1], 1):
        if len(cells) != 4:
            raise ValueError(f"change {n}: a row to keep with {len(cells)} cells: {cells[:1]}")
        try:
            cites = split_citations(cells[1])
        except ValueError as e:
            raise ValueError(f"change {n}, kept row {k}: {e}") from None
        c.keep.append(KeepRow(f"OGMK-{n:02d}{k:02d}", "kept", cells[0], cites, [parse_citation(x) for x in cites],
                              cells[2], cells[3]))
    if not c.keep:
        raise ValueError(f"change {n}: no behaviour to keep")
    if c.deliberate_change is None:
        raise ValueError(f"change {n}: no **Deliberate change:** line")

    # the dependency row and its precondition, or the control's comparison row
    if c.cross:
        if c.dependency_text is None:
            raise ValueError(f"change {n}: a cross-component change with no 'Dependency exercised only if' line")
        m = re.match(rf"{re.escape(DEP_MARK)}\s*(.+?)\.\s+Otherwise\b", c.dependency_text, re.S)
        if not m:
            raise ValueError(f"change {n}: can't read the 'Dependency exercised only if' line: {c.dependency_text[:80]!r}")
        c.dependency_if = " ".join(m.group(1).split())
        if comparison_text:
            raise ValueError(f"change {n}: a cross-component change with a comparison row")
        c.keep[0].role = "dependency"
    else:
        if c.dependency_text is not None:
            raise ValueError(f"change {n}: a control with a 'Dependency exercised only if' line")
        if comparison_text is None:
            raise ValueError(f"change {n}: a control with no comparison row")
        m = re.match(r"\*\*Comparison row:\*\*\s*the (\w+) kept row \(([^)]*)\)", comparison_text)
        cond = re.search(r"\*\*exercised only if\*\*\s*(.+?);\s*otherwise\b", comparison_text, re.S)
        base = re.search(r"Baseline witness:\s*(.+)$", comparison_text, re.S)
        if not (m and cond and base):
            raise ValueError(f"change {n}: can't read the comparison row (its kept row, **exercised only if** and "
                             f"baseline witness): {comparison_text[:80]!r}")
        k = ORDINALS.get(m.group(1).lower())
        if not k or k > len(c.keep):
            raise ValueError(f"change {n}: the comparison row is the {m.group(1)} kept row, which doesn't exist")
        c.keep[k - 1].role = "comparison"
        c.comparison = {"row": c.keep[k - 1].id, "summary": m.group(2).strip(),
                        "exercised_only_if": " ".join(cond.group(1).split()),
                        "baseline_witness": " ".join(base.group(1).split()), "text": comparison_text}

    # retired tests
    if "Retired tests" not in secs:
        raise ValueError(f"change {n}: no retired-tests section")
    c.retired_note = secs["Retired tests"].strip() or None
    c.retired = _retired(n, secs["Retired tests"], test_index)
    c.retired_tests = [r["test"] for r in c.retired]

    # why the other part is needed: the section's prose, without its labelled notes
    if "Why the other part is needed" in secs:
        if not c.cross:
            raise ValueError(f"change {n}: a control with a 'Why the other part is needed' section")
        prose = [_split_inline(b)[0] for b in _blocks(secs["Why the other part is needed"])
                 if _labelled(b) is None and not b.startswith(("|", "- "))]
        c.why_other_part = "\n\n".join(p for p in prose if p) or None
    if c.cross and not c.why_other_part:
        raise ValueError(f"change {n}: a cross-component change with no 'Why the other part is needed'")

    # repair reports: one per row, and one for a cross-component change's dependency row
    for m in re.finditer(r"(?m)^- \*\*(.+?):\*\*\s*(.+)$", secs.get("Repair reports", "")):
        key, text = m.group(1).strip(), _unquote(m.group(2))
        if key not in by_id and key != "Dependency":
            raise ValueError(f"change {n}: a repair report under {key!r}, which isn't a row or Dependency")
        if key == "Dependency" and not c.cross:
            raise ValueError(f"change {n}: a Dependency report in a control, which has no dependency row")
        if key in c.reports:
            raise ValueError(f"change {n}: two repair reports for {key}")
        if not text:
            raise ValueError(f"change {n}: an empty repair report for {key}")
        c.reports[key] = text
    for rid in ids:
        if rid not in c.reports:
            raise ValueError(f"{rid}: no repair report")
    if c.cross and "Dependency" not in c.reports:
        raise ValueError(f"change {n}: a cross-component change with no Dependency repair report")
    return c


def parse_m2h(text: str, *, test_index: dict | None = None) -> dict[int, M2hChange]:
    """The change set, by change number. HTML comments are dropped first; the closing summary table is checked against
    each change's fields."""
    text, summary = _summary_table(COMMENT.sub("", text))
    changes: dict[int, M2hChange] = {}
    for part in re.split(r"(?m)^## ", text)[1:]:
        heading, _, body = part.partition("\n")
        m = re.match(r"Change (\d+)\s*[—-]\s*(.+)", heading.strip())
        if not m:
            continue
        n = int(m.group(1))
        if n in changes:
            raise ValueError(f"two changes numbered {n}")
        changes[n] = _parse_change(n, m.group(2).strip(), body, test_index)
    if not changes:
        raise ValueError("no '## Change N — title' sections")
    if summary:
        for cells in summary:
            n = int(re.match(r"\d+", cells[0]).group(0))
            c = changes.get(n)
            mine = c and [c.type, c.intent_distance, c.edits_part, f"{c.edits_file} → {c.intent_lives_in}"]
            theirs = [x.replace("`", "").strip() for x in cells[1:5]]
            if mine != theirs:
                raise ValueError(f"change {n}: the summary table says {theirs}, but the change says {mine}")
        if sorted(int(re.match(r"\d+", r[0]).group(0)) for r in summary) != sorted(changes):
            raise ValueError("the summary table doesn't list every change once")
    return changes


def parse_plan_tiers(text: str) -> tuple[dict[int, dict], dict[str, tuple[int, ...]]]:
    """The plan's tier table ({change: {"tier", "why", "signpost"}}) and its **Tier count:** line ({tier: changes})."""
    tiers: dict[int, dict] = {}
    for block in _blocks(text):
        if not block.startswith("| Change | Tier |"):
            continue
        for cells in _table(block)[1]:
            sp = re.search(r"\bSignpost:\s*(.+)$", cells[2])
            for n in (int(x) for x in re.findall(r"\d+", cells[0])):
                tiers[n] = {"tier": cells[1], "why": cells[2], "signpost": sp.group(1).strip() if sp else None}
    count: dict[str, tuple[int, ...]] = {}
    m = re.search(r"\*\*Tier count:\*\*\s*(.+)", text)
    if m:
        count = {t: () for t in TIERS}
        for k, word, listed in re.findall(r"(\d+) (documented|one-step|hidden)(?: \(([\d, ]+)\))?", m.group(1)):
            t = "one-step grep" if word == "one-step" else word
            got = tuple(int(x) for x in re.findall(r"\d+", listed))
            if len(got) != int(k):
                raise ValueError(f"the plan's tier count says {k} {word}, but lists {got}")
            count[t] = tuple(sorted(count[t] + got))
    return tiers, count


def guard_rows(data: dict) -> dict[str, dict]:
    rows = (data or {}).get("rows")
    if not isinstance(rows, dict):
        raise ValueError(f"{GUARDS} has no \"rows\" object")
    return rows


def brief_body(text: str) -> str:
    """The brief as the owner says it: its title line and any comment dropped."""
    lines = COMMENT.sub("", text or "").strip().splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).strip()


def distance_field() -> str:
    """The change script's label for a change's intent distance: "Intent distance" when the harness's change-script
    parser reads M2h's two distances, and otherwise FALLBACK_DISTANCE_FIELD, which it leaves alone (it refuses an
    intent distance it doesn't know)."""
    for kind in (CROSS_DISTANCE, CONTROL_DISTANCE):
        try:
            s = simulator.parse_change_script(f"## Change 1 — t\n\n**Intent distance:** {kind}\n\n### Owner request\n\n> x\n")
        except ValueError:
            return FALLBACK_DISTANCE_FIELD
        if s[1].intent_distance is None or s[1].intent_distance.kind != kind:
            return FALLBACK_DISTANCE_FIELD
    return "Intent distance"


def _index(data) -> dict[str, list[str]]:
    return {p: (v.get("tests") or [] if isinstance(v, dict) else list(v)) for p, v in data.items()}


def load_sources(hidden: Path, *, brief: Path | None = None) -> Sources:
    hidden = Path(hidden)

    def need(p: Path, what: str) -> str:
        if not p.exists():
            raise ValueError(f"no {what} at {p}")
        return p.read_text(encoding="utf-8")

    def opt(p: Path):
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    index, paths = opt(hidden / TEST_INDEX), opt(hidden / PATHS)
    return Sources(
        source=need(hidden / SOURCE, "change set"),
        brief=need(Path(brief) if brief else hidden.parent / BRIEF, "owner's brief"),
        guards=json.loads(need(hidden / GUARDS, "guard rows")),
        plan=(hidden / PLAN).read_text(encoding="utf-8") if (hidden / PLAN).exists() else None,
        test_index=_index(index) if index is not None else None,
        paths=set(paths) if paths is not None else None,
        briefs=opt(hidden / BRIEFS))


# ----------------------------------------------------------------------------------------------- writing


def _tiers(changes: dict[int, M2hChange], salience: dict | None) -> dict[str, str]:
    askable = [r.id for c in changes.values() for r in c.rows if r.kind == "Askable"]
    if salience is None:
        return {rid: "medium" for rid in askable}
    rows = {r.id for c in changes.values() for r in c.rows}
    for rid in salience:
        if rid not in rows:
            raise ValueError(f"salience.json names {rid}, which isn't an M2h row")
    out = {}
    for rid in askable:
        tier = salience.get(rid)
        if tier is None:
            raise ValueError(f"salience.json has no tier for {rid}")
        if tier not in simulator.TIERS:
            raise ValueError(f"salience.json: {rid}'s tier {tier!r} isn't low, medium or high")
        out[rid] = tier
    return out


def _kept_line(c: M2hChange) -> str:
    return ", ".join(k.id + (f" (the {k.role} row)" if k.role != "kept" else "") for k in c.keep)


def _change_script(changes: dict[int, M2hChange], guards: dict) -> str:
    dist = distance_field()
    first, last = min(changes), max(changes)
    out = [
        f"# Change script: openGym M2h (changes {first} to {last})",
        "",
        "<!-- Written by build_m2h_seed.py from ../m2h-changes.md. Edit that file and rerun; don't edit this one. -->",
        "",
        "## Delivery rules",
        "",
        f"openGym is pinned at `{PIN}`. Each change is forked from its arm's start ({STARTS}), run in a fresh session, "
        "and discarded. No change sees another's work. A fork's owner holds the start and that change only: "
        "`run_fork.py --oracle m2h/oracle.md --change-script m2h/change-script.md --owner-items m2h/owner-items.json`, "
        "whose fork scope gives the owner the start's narrative and that change's own section and rows.",
        "",
        "Deliver the quoted owner request. M2h has no redirects, emerging statements, planted bugs or symptom reports, "
        "and there are no accompanying interface specifications. Askable rows keep their disclosure rules.",
        "",
        "Each change's behaviour to keep (IDs OGMK-NNkk, in the source table's order, naming the cross-component "
        "dependency row or the control's comparison row), its searchability tier, its dependency precondition or "
        "comparison row, the rows its joint outcome counts, its deliberate change, its retired tests, why the other "
        "part is needed, and its grading notes are in `kept-behaviour.json`. Guard rows are in `guard-rows.json`, "
        "repair reports in `repair-reports.json`.",
        "",
    ]
    if dist != "Intent distance":
        out += [f"The intent distance is written as **{dist}:**, which the harness's change-script parser doesn't read: "
                "it doesn't know M2h's two distances yet.", ""]
    for n, c in sorted(changes.items()):
        g = [r.id for r in c.rows if r.id in guards]
        out += [
            f"## Change {n} — {c.title}",
            "",
            f"**Type:** {c.type}  ",
            f"**{dist}:** {c.intent_distance}  ",
            f"**Edits part:** {c.edits_part}  ",
            f"**Edits file:** {c.edits_file}  ",
            f"**Intent lives in:** {c.intent_lives_in}  ",
            f"**Searchability tier:** {c.tier}",
            "",
            "### Owner request",
            "",
            *c.request_lines,
            "",
            f"**Introduces:** {', '.join(r.id for r in c.rows)}.  ",
            "**Retires:** Nothing in the oracle.  ",
            "**Relies on:** Nothing in the oracle.  ",
            f"**Guard rows:** {', '.join(g) + ' (`guard-rows.json`)' if g else 'None'}.  ",
            f"**Kept behaviour:** {_kept_line(c)} (`kept-behaviour.json`).  ",
            f"**Left to the agent (not graded):** {c.left_to_developer or 'Nothing named.'}",
            "",
            "No redirect, emerging statement, planted bug, or symptom report.",
            "",
        ]
    out += ["## Summary", "",
            "| Change | Title | Type | Intent distance | Tier | Edits part | Files: edit → intent | Stated | Askable | "
            "Guard | Dependency or comparison row |",
            "|---|---|---|---|---|---|---|---|---|---|---|"]
    for n, c in sorted(changes.items()):
        anchor = next((f"{k.id} ({k.role})" for k in c.keep if k.role != "kept"), "None")
        stated = ", ".join(r.id for r in c.rows if r.kind == "Stated") or "None"
        askable = ", ".join(r.id for r in c.rows if r.kind == "Askable") or "None"
        guard = ", ".join(r.id for r in c.rows if r.id in guards) or "None"
        out.append(f"| {n} | {c.title} | {c.type} | {c.intent_distance} | {c.tier} | {c.edits_part} | "
                   f"{c.edits_file} → {c.intent_lives_in} | {stated} | {askable} | {guard} | {anchor} |")
    return "\n".join(out) + "\n"


def _oracle(changes: dict[int, M2hChange], brief: str, rated: bool) -> str:
    first, last = min(changes), max(changes)
    tiers = ("salience tiers rated in `salience.json`" if rated else
             "a placeholder tier, medium, for every row: M2h has no salience rating yet")
    out = [
        "# Oracle: openGym M2h",
        "",
        "<!-- Written by build_m2h_seed.py from ../m2h-changes.md (the changes). Edit it and rerun; don't edit this "
        "one. -->",
        "",
        "## Owner narrative",
        "",
        "The simulated owner receives \"What the owner knows from the start\", plus the section for the change being "
        "run. Each change is forked from its arm's start and run on its own, so a fork's owner holds only the start "
        "section and that change's section and items, through `run_fork.py`'s fork scope on this file.",
        "",
        "### What the owner knows from the start",
        "",
    ]
    for n, c in sorted(changes.items()):
        out += [f"### Learned at change {n}: {c.title}", "", c.request, ""]
    out += [
        "## Disclosure and grading conventions",
        "",
        f"- Each change, {first} to {last}, is forked from its arm's start ({STARTS}), run once, and discarded.",
        "- A fork's owner holds the start section, that change's section, and that change's rows, through `run_fork.py "
        "--oracle`, `--change-script` and `--owner-items` pointed at this folder.",
        "- The start section is empty: the owner's brief (`../../brief.md`) reaches the owner as the brief, and M2h has "
        "no owner narrative beyond it. Each \"Learned at change N\" section is the owner's request for that change, quoted verbatim from "
        "`m2h-changes.md`; nothing else is written into it.",
        "- No item is in force at the start: the start section is background.",
        "- Every OGM row comes into force at its own change and none is retired. Its behaviour is the source's row as "
        "written, and its external check sketch is the source's check, verbatim.",
        "- Askable answers disclose the row when the agent asks about its topic, or when the agent shows something that "
        f"touches it and the row is recalled. Recall lines are in `owner-items.json`, with {tiers}. A recall line given "
        "only on a condition is recorded there beside the items, under \"conditional_recall\".",
        "- M2h rows are stated or askable: none is recognized on sight. There are no Dropped rows, redirects, planted "
        "bugs or symptom reports.",
        "- Guard rows (keep-it-as-it-was rows the untouched code meets) are in `guard-rows.json`. Each change's "
        "behaviour to keep is in `kept-behaviour.json`, under IDs OGMK-NNkk numbered in the source table's order. Kept "
        "rows are not oracle items, and the owner doesn't hold them.",
        "- Repair reports are in `repair-reports.json`: one per row, and DEP-N for the dependency row of each "
        "cross-component change.",
        "",
        "## Item table",
        "",
        "| ID | Checkable behavior | Disclosure kind | In force | Retired | External check sketch |",
        "|---|---|---|---|---|---|",
    ]
    for n, c in sorted(changes.items()):
        for r in c.rows:
            kind = f"Stated in change {n}" if r.kind == "Stated" else "Askable"
            out.append(f"| {r.id} | {r.behaviour} | {kind} | Change {n} | — | {r.check} |")
    return "\n".join(out) + "\n"


def _record(c: M2hChange, plan_tiers: dict[int, dict], guards: dict) -> dict:
    ids = {r.id for r in c.rows}
    guard = [r.id for r in c.rows if r.id in guards]
    notes = JOINT_NOTES.get(c.number, {})
    implemented = [r.id for r in c.rows if r.kind == "Stated" and r.id not in guard]
    score = [r.id for r in c.rows if r.id not in guard and r.id not in notes.get("new_row_score_excludes", [])]
    pre = dict(c.row_preconditions)
    pre.update({g: v["runs_only_if"] for g, v in CONDITIONAL_GUARDS.items() if g in ids})
    dep = next((k for k in c.keep if k.role == "dependency"), None)
    return {
        "title": c.title, "type": c.type, "cross_component": c.cross, "intent_distance": c.intent_distance,
        "edits_part": c.edits_part, "edits_file": c.edits_file, "intent_lives_in": c.intent_lives_in,
        "searchability": {"tier": c.tier, "why": c.tier_why, "signpost": (plan_tiers.get(c.number) or {}).get("signpost"),
                          "pooled_with_and_without": c.cross and c.tier == "documented"},
        "rows": [k.record() for k in c.keep],
        "dependency": ({"row": dep.id, "exercised_only_if": c.dependency_if, "otherwise": "not exercised",
                        "text": c.dependency_text} if dep else None),
        "comparison": {**c.comparison, "otherwise": "not exercised"} if c.comparison else None,
        "new_rows": {"stated": [r.id for r in c.rows if r.kind == "Stated"],
                     "askable": [r.id for r in c.rows if r.kind == "Askable"], "guard": guard,
                     "preconditions": dict(sorted(pre.items()))},
        "joint": {"implemented_rows": implemented, "new_row_score_rows": score,
                  "new_row_score": "scored" if score else "N/A",
                  "beside_dependency": notes.get("beside_dependency", []), "kept_only": notes.get("kept_only", []),
                  "dependency_rate": notes.get("dependency_rate"), "sources": notes.get("quotes", [])},
        "deliberate_change": c.deliberate_change, "retired_tests": c.retired_tests, "retired": c.retired,
        "retired_note": c.retired_note, "why_other_part": c.why_other_part, "left_to_developer": c.left_to_developer,
        "notes": c.notes,
    }


def convert(src: Sources, *, salience: dict | None = None) -> dict[str, str]:
    """Each output file's text, by name."""
    changes = parse_m2h(src.source, test_index=src.test_index)
    plan_tiers = parse_plan_tiers(src.plan)[0] if src.plan else {}
    rows = {r.id for c in changes.values() for r in c.rows}
    guards = {g: v for g, v in guard_rows(src.guards).items() if ROW_ID.match(g) and change_of(g) in changes}
    tiers = _tiers(changes, salience)
    owner = {
        "_note": "Recall lines for every askable M2h row, from m2h-changes.md, written by build_m2h_seed.py (edit the "
                 "source, or m2h/salience.json for the tiers, and rerun). Tiers come from m2h/salience.json when it "
                 "exists, and are otherwise medium for every row.",
        "tiers": RATED_TIERS if salience is not None else PLACEHOLDER_TIERS,
        "items": {r.id: {"tier": tiers[r.id], "recall": r.recall}
                  for _, c in sorted(changes.items()) for r in c.rows if r.kind == "Askable"},
    }
    conditional = {g: {"given_only": v["given_only"], "source": v["quote"]}
                   for g, v in sorted(CONDITIONAL_RECALL.items()) if g in rows}
    if conditional:
        owner["conditional_recall"] = {
            "_note": "Recall lines the owner gives only on a condition: the row's line in \"items\" is said only then, "
                     "never on review recall or another question. The simulator reads only \"items\", so it doesn't "
                     "act on this yet.",
            **conditional}
    reports: dict[str, dict] = {}
    kept: dict[str, dict] = {}
    for n, c in sorted(changes.items()):
        for r in c.rows:
            reports[r.id] = {"report": c.reports[r.id]}
        if "Dependency" in c.reports:
            reports[f"DEP-{n}"] = {"report": c.reports["Dependency"], "change": n}
        kept[str(n)] = _record(c, plan_tiers, guards)
    guard_out = {}
    for g, v in sorted(guards.items()):
        entry = {"change": change_of(g), "why": v.get("why"), "checkable_on_snapshot": v.get("checkable_on_snapshot", True)}
        if "uncheckable_why" in v:
            entry["uncheckable_why"] = v["uncheckable_why"]
        if g in CONDITIONAL_GUARDS:
            entry["conditional"] = {k: CONDITIONAL_GUARDS[g][k] for k in ("runs_only_if", "otherwise")}
        guard_out[g] = entry
    return {
        "change-script.md": _change_script(changes, guards),
        "oracle.md": _oracle(changes, src.brief, rated=salience is not None),
        "owner-items.json": _json(owner),
        "repair-reports.json": _json(reports),
        "kept-behaviour.json": _json(kept),
        "guard-rows.json": _json({
            "note": "Keep-it-as-it-was rows, from m2h-guard-rows.json (costeval/m2h_seed.py): exempt from grading's "
                    "absent-conflict rule, expected met on the pinned tree where their check can run there, and counted "
                    "apart from the new-behaviour rows. A conditional row runs only on a build that meets its condition; "
                    "otherwise it is not exercised, never met.",
            "rows": guard_out}),
    }


def write_seed(src: Sources, out_dir: Path) -> dict[str, str]:
    """Convert and write every output into out_dir, taking tiers from out_dir/salience.json if it exists."""
    out_dir = Path(out_dir)
    files = convert(src, salience=load_salience(out_dir))
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (out_dir / name).write_text(text, encoding="utf-8")
    return files


# ---------------------------------------------------------------------------------------------- checking


def _guard_problems(changes: dict[int, M2hChange], guards: dict[str, dict]) -> list[str]:
    rows = {r.id: r for c in changes.values() for r in c.rows}
    mine = {g: v for g, v in guards.items() if not ROW_ID.match(g) or change_of(g) in changes}
    out = guard_problems(rows, {g: v.get("why") for g, v in mine.items()})
    declared = {g: n for n, c in changes.items() for g in c.guards_declared}
    for g, v in sorted(mine.items()):
        if ROW_ID.match(g) and v.get("change") != change_of(g):
            out.append(f"{g}: {GUARDS} files it under change {v.get('change')}, but it is change {change_of(g)}'s")
        if g in rows and g not in declared:
            out.append(f"{g}: in {GUARDS}, but change {change_of(g)} has no **Guard row:** line for it")
        if not isinstance(v.get("checkable_on_snapshot", True), bool):
            out.append(f"{g}: checkable_on_snapshot isn't true or false")
        if v.get("checkable_on_snapshot") is False and not v.get("uncheckable_why"):
            out.append(f"{g}: not checkable on the pinned tree, with no uncheckable_why")
    for g, n in sorted(declared.items()):
        if g not in mine:
            out.append(f"{g}: a **Guard row:** line in change {n}, but not in {GUARDS}")
    for g in CONDITIONAL_GUARDS:
        if g in rows and mine.get(g, {}).get("checkable_on_snapshot") is not False:
            out.append(f"{g}: a conditional guard that {GUARDS} doesn't mark uncheckable on the pinned tree")
    return out


def _table_problems(changes: dict[int, M2hChange]) -> list[str]:
    """Each hard-coded table entry must name rows of its change, and its quote must still be in the change's text."""
    out = []
    rows = {r.id: r for c in changes.values() for r in c.rows}
    entries = [(g, change_of(g), "conditional guard", [v["quote"]], [g]) for g, v in CONDITIONAL_GUARDS.items()]
    entries += [(g, change_of(g), "conditional recall", [v["quote"]], [g]) for g, v in CONDITIONAL_RECALL.items()]
    entries += [(f"change {n}", n, "joint-outcome note", v["quotes"],
                 [*v.get("new_row_score_excludes", []), *v.get("beside_dependency", []), *v.get("kept_only", [])])
                for n, v in JOINT_NOTES.items()]
    for name, n, what, quotes, named in entries:
        c = changes.get(n)
        if c is None:
            continue
        for q in quotes:
            if _norm(q) not in _norm(c.text):
                out.append(f"{name}: the {what}'s source text is no longer in change {n}: {q!r}")
        kept_ids = {k.id for k in c.keep}
        for i in named:
            if i not in kept_ids and (i not in rows or change_of(i) != n):
                out.append(f"{name}: the {what} names {i}, which isn't a row or kept row of change {n}")
    for g in CONDITIONAL_RECALL:
        if g in rows and rows[g].kind != "Askable":
            out.append(f"{g}: a conditional recall line for a row that isn't askable")
    return out


def check_seed(out_dir: Path, src: Sources, *, expected: Expected = EXPECTED) -> tuple[list[str], list[str], list[str]]:
    """(problems, warnings, summary lines) for the files in out_dir, read with the harness's own parsers."""
    out_dir = Path(out_dir)
    problems: list[str] = []
    warnings: list[str] = []
    try:
        changes = parse_m2h(src.source, test_index=src.test_index)
        fresh = convert(src, salience=load_salience(out_dir))
        guards = {g: v for g, v in guard_rows(src.guards).items()}
        plan_tiers, plan_count = parse_plan_tiers(src.plan) if src.plan else ({}, {})
    except ValueError as e:
        return [f"the source doesn't convert: {e}"], warnings, []
    if not brief_body(src.brief):
        problems.append("the owner's brief (../brief.md) is empty or missing")
    problems += _guard_problems(changes, guards)
    problems += _table_problems(changes)
    for name in OUTPUTS:
        f = out_dir / name
        if not f.exists():
            problems.append(f"{name} is missing; run build_m2h_seed.py")
        elif f.read_text(encoding="utf-8") != fresh[name]:
            problems.append(f"{name} is out of date with the source; rerun build_m2h_seed.py")
    if any(not (out_dir / n).exists() for n in OUTPUTS):
        return problems, warnings, []

    def read(name):
        return (out_dir / name).read_text(encoding="utf-8")
    try:
        oracle = simulator.parse_oracle(read("oracle.md"))
        script = simulator.parse_change_script(read("change-script.md"))
    except ValueError as e:
        return problems + [f"the harness can't read the oracle or change script: {e}"], warnings, []
    try:
        owner = simulator.load_owner_items(out_dir / "owner-items.json", oracle)
    except ValueError as e:
        problems.append(f"owner-items.json: {e}")
        owner = {}
    owner_data = json.loads(read("owner-items.json"))
    reports = json.loads(read("repair-reports.json"))
    kept = json.loads(read("kept-behaviour.json"))
    guard_file = json.loads(read("guard-rows.json")).get("rows") or {}
    script_text = read("change-script.md")

    # the changes, their rows, what each introduces, and its distance
    nums = sorted(script)
    if nums != sorted(expected.changes) or sorted(changes) != sorted(expected.changes):
        problems.append(f"changes {nums} (source {sorted(changes)}), expected {list(expected.changes)}")
    rows: dict[int, set[str]] = {}
    live = [i for i in oracle.items if ROW_ID.match(i.id)]
    if len(live) != len(oracle.items):
        problems.append(f"the oracle holds items that aren't OGM rows: {sorted(oracle.ids() - {i.id for i in live})}")
    for i in live:
        n = change_of(i.id)
        rows.setdefault(n, set()).add(i.id)
        if i.in_force != n or i.retired is not None or i.kind not in {f"Stated in change {n}", "Askable"}:
            problems.append(f"{i.id}: {i.kind!r}, in force {i.in_force}, retired {i.retired}; expected stated in or "
                            f"askable at change {n}, never retired")
    dist = distance_field()
    if dist != "Intent distance":
        warnings.append(f"simulator.py doesn't read M2h's intent distances ({CROSS_DISTANCE}; {CONTROL_DISTANCE}), so the "
                        f"change script writes them as **{dist}:**, which it leaves alone")
    for n in nums:
        intro, own = set(script[n].introduces), rows.get(n, set())
        src_rows = {r.id for r in changes[n].rows} if n in changes else set()
        if intro != own or own != src_rows:
            problems.append(f"change {n}: introduces {sorted(intro)}, but its rows are {sorted(own)} (source {sorted(src_rows)})")
        if n not in changes:
            continue
        if dist == "Intent distance":
            got = script[n].intent_distance.kind if script[n].intent_distance else None
        else:
            section = script_text.split(f"## Change {n} —", 1)[1].split("\n## ", 1)[0]
            m = re.search(rf"\*\*{re.escape(dist)}:\*\*\s*(.+?)\s*$", section, re.M)
            got = m.group(1) if m else None
        if got != changes[n].intent_distance:
            problems.append(f"change {n}: intent distance {got!r} in the change script, the source says "
                            f"{changes[n].intent_distance!r}")

    # each fork releases its own rows, and its owner's prompt shows them and nothing else
    if sorted(oracle.narrative) != [0, *nums]:
        problems.append(f"narrative sections for {sorted(oracle.narrative)}, expected the start and {nums}")
    if (oracle.narrative.get(0) or "").strip():
        problems.append("the oracle's start section isn't empty (the brief reaches the owner as the brief)")
    every = {iid for s in rows.values() for iid in s}
    for n in nums:
        released = {i.id for i in simulator.released_items(oracle, n, only_change=True)}
        if released != rows.get(n, set()):
            problems.append(f"change {n}'s fork releases {sorted(released)}, expected {sorted(rows.get(n, set()))}")
        if oracle.narrative.get(n) != script[n].request:
            problems.append(f"change {n}: its narrative section isn't the owner's request verbatim")
        if simulator.released_narrative(oracle, n, only_change=True) != f"{oracle.narrative.get(0)}\n\n{oracle.narrative.get(n)}":
            problems.append(f"change {n}'s fork releases narrative beyond the start and its own section")
        prompt = simulator.build_prompt(oracle=oracle, change=script[n], brief="(brief)", message="(plan)", only_change=True)
        for iid in sorted(rows.get(n, ())):
            tag = f"[{iid}] (Askable; in play for this change)" if iid in owner else f"[{iid}]"
            if tag not in prompt:
                problems.append(f"change {n}: the owner's prompt doesn't show {tag}")
        shown = sorted(iid for iid in every - rows.get(n, set()) if f"[{iid}]" in prompt)
        if shown:
            problems.append(f"change {n}: the owner's prompt shows other changes' rows {shown}")

    # owner items: every askable row, its recall line from the source, and the conditional ones beside them
    askable = {r.id: r for c in changes.values() for r in c.rows if r.kind == "Askable"}
    if owner and set(owner) != set(askable):
        problems.append(f"owner-items.json covers {sorted(owner)}, the askable rows are {sorted(askable)}")
    for rid, item in owner.items():
        if rid in askable and item.recall != askable[rid].recall:
            problems.append(f"{rid}: its recall line differs from the source's")
    if str(owner_data.get("tiers", "")).startswith("placeholder"):
        warnings.append("owner-items.json: the tiers are a placeholder (medium for every row); write m2h/salience.json "
                        "({\"OGM-0102\": \"low|medium|high\", ...}) from the four-model panel and rerun")
    conditional = owner_data.get("conditional_recall") or {}
    for g, v in CONDITIONAL_RECALL.items():
        if g not in askable:
            continue
        if (conditional.get(g) or {}).get("given_only") != v["given_only"]:
            problems.append(f"{g}: owner-items.json doesn't record its conditional recall ({v['given_only']})")
        elif "given_only" not in getattr(simulator.OwnerItem, "__dataclass_fields__", {}):
            warnings.append(f"owner-items.json: {g} has a conditional recall (given only {v['given_only']}), recorded "
                            "beside the items; simulator.py reads only \"items\", so it would still give the line on "
                            "review recall or on a broad question that covers the row")

    # repair reports: every row, and the dependency row of every cross-component change
    cross = [n for n in nums if changes.get(n) and changes[n].cross]
    want_reports = every | {f"DEP-{n}" for n in cross}
    for key in sorted(want_reports - set(reports)):
        problems.append(f"{key}: no repair report")
    for key in sorted(set(reports) - want_reports):
        problems.append(f"repair-reports.json: {key} isn't a row or the dependency row of a cross-component change")
    for key in sorted(want_reports & set(reports)):
        text = repair.report_for(reports, key)
        if text is None:
            problems.append(f"{key}: an empty repair report")
        elif "<!--" in text or "-->" in text:
            problems.append(f"{key}: its repair report holds an HTML comment")
        if key.startswith("DEP-") and (not isinstance(reports[key], dict) or reports[key].get("change") != int(key[4:])):
            problems.append(f"{key}: its change field isn't {key[4:]}")

    # the per-change record: kept rows in order, the dependency or comparison row, the tier and precondition
    if sorted(kept, key=int) != [str(n) for n in nums]:
        problems.append(f"kept-behaviour.json covers changes {sorted(kept, key=int)}, not {nums}")
    briefs = {b.get("n"): b for b in (src.briefs or {}).get("changes", [])}
    for n in nums:
        k, c = kept.get(str(n)), changes.get(n)
        if not k or not c:
            continue
        ids = [r["id"] for r in k["rows"]]
        if ids != [f"OGMK-{n:02d}{j:02d}" for j in range(1, len(ids) + 1)]:
            problems.append(f"change {n}: kept rows {ids} aren't OGMK-{n:02d}01 onwards")
        deps = [r["id"] for r in k["rows"] if r.get("dependency")]
        cmps = [r["id"] for r in k["rows"] if r.get("role") == "comparison"]
        if c.cross:
            if deps != [f"OGMK-{n:02d}01"] or cmps:
                problems.append(f"change {n}: dependency rows {deps} and comparison rows {cmps}, expected "
                                f"OGMK-{n:02d}01 alone as its dependency row")
            dep = k.get("dependency") or {}
            if dep.get("row") != f"OGMK-{n:02d}01" or not dep.get("exercised_only_if"):
                problems.append(f"change {n}: no 'Dependency exercised only if' precondition for its dependency row")
            if not k.get("why_other_part"):
                problems.append(f"change {n}: a cross-component change with no 'why the other part is needed'")
        else:
            cmp = k.get("comparison") or {}
            if deps or len(cmps) != 1 or cmp.get("row") != (cmps or [None])[0]:
                problems.append(f"change {n}: a control with dependency rows {deps} and comparison rows {cmps}")
            if not cmp.get("exercised_only_if") or not cmp.get("baseline_witness"):
                problems.append(f"change {n}: its comparison row has no precondition or baseline witness")
        tier = (k.get("searchability") or {}).get("tier")
        if tier not in TIERS:
            problems.append(f"change {n}: no searchability tier ({tier!r})")
        if (k["type"], k["intent_distance"], k["edits_part"]) != (c.type, c.intent_distance, c.edits_part):
            problems.append(f"change {n}: the kept record's type, distance or part differs from the source's")
        section = script_text.split(f"## Change {n} —", 1)[1].split("\n## ", 1)[0] if f"## Change {n} —" in script_text else ""
        line = re.search(r"\*\*Kept behaviour:\*\*\s*(.+)", section)
        listed = list(simulator.parse_ids(line.group(1))) if line else []
        if listed != ids:
            problems.append(f"change {n}: the change script's Kept behaviour line names {listed}, the record {ids}")
        # against its brief: the anchor row's citations and the known retired tests
        b = briefs.get(n)
        if b:
            anchor_name = "dependency row" if "dependency_row" in b else "kept row"
            anchor = b.get("dependency_row") or b.get("kept_row") or {}
            row = next((r for r in k["rows"] if r.get("role") in ("dependency", "comparison")), None)
            missing = [x for x in anchor.get("cites", []) if row is None or x not in row["established_in"]]
            if missing:
                problems.append(f"change {n}: the {row['role'] if row else 'anchor'} row {row['id'] if row else '-'} "
                                f"doesn't cite {missing}, which its brief's {anchor_name} cites")
            if b.get("type") and b["type"] != c.type:
                problems.append(f"change {n}: type {c.type!r}, its brief says {b['type']!r}")
            retired = {t.translate(QUOTES) for t in c.retired_tests}
            for t in b.get("known_retired", []):
                if t.translate(QUOTES) not in retired:
                    problems.append(f"change {n}: 'Retired tests' leaves out {t}, which its brief names")
        # against the pinned tree: cited paths and test titles
        index = {p: {t.translate(QUOTES) for t in ts} for p, ts in (src.test_index or {}).items()}
        for r in c.keep:
            for cite in r.citations:
                if src.paths is not None and cite["path"] not in src.paths:
                    problems.append(f"change {n}: {r.id} cites {cite['path']}, which isn't in the pinned tree")
                if (src.test_index is not None and cite["kind"] == "test"
                        and cite["test"].translate(QUOTES) not in index.get(cite["path"], set())):
                    problems.append(f"change {n}: {r.id} cites {cite['path']}::{cite['test']!r}: no test titled so in "
                                    f"the test index")
        for r in c.retired:
            path, _, title = r["test"].partition("::")
            if src.test_index is None:
                continue
            if r.get("run_time_title"):
                warnings.append(f"change {n}: retired test {r['test']} has a title made at run time from {r['from']}, "
                                "which the test index can't hold; not checked")
            elif title.translate(QUOTES) not in index.get(path, set()):
                problems.append(f"change {n}: retired test {r['test']} isn't in the test index")
        # against the plan: the tier, and the signpost the joint-outcome report carries
        if src.plan:
            p = plan_tiers.get(n)
            if p is None:
                problems.append(f"change {n}: the plan's tier table doesn't list it")
            elif p["tier"] != c.tier:
                problems.append(f"change {n}: tier {c.tier!r}, but the plan says {p['tier']!r}")
    if src.plan:
        for t in TIERS:
            have = tuple(n for n in nums if n in changes and changes[n].tier == t)
            if plan_count and tuple(x for x in plan_count.get(t, ()) if x in changes) != have:
                problems.append(f"the plan's tier count has {t} for changes {list(plan_count.get(t, ()))}, the changes "
                                f"say {list(have)}")
    else:
        warnings.append(f"no {PLAN}: no signposts, and the tiers aren't checked against the plan")

    # guard rows as written
    if sorted(guard_file) != sorted(g for g in guards if ROW_ID.match(g) and change_of(g) in changes):
        problems.append(f"guard-rows.json holds {sorted(guard_file)}, the source's for these changes differ")
    for g, v in CONDITIONAL_GUARDS.items():
        if g in guard_file and not (guard_file[g].get("conditional") or {}).get("runs_only_if"):
            problems.append(f"{g}: guard-rows.json doesn't record its condition ({v['runs_only_if']})")

    # what the owner holds: identifiers or code in a row's behaviour reach the owner as written
    for i in live:
        hits = OGM.findall(i.behavior) + re.findall(r"`[^`]+`", i.behavior)
        if hits:
            warnings.append(f"{i.id}: the owner holds this row's behaviour as written, and it names {', '.join(hits)}")

    # counts
    all_rows = [r for c in changes.values() for r in c.rows]
    stated = sum(r.kind == "Stated" for r in all_rows)
    n_ask = sum(r.kind == "Askable" for r in all_rows)
    n_guard = len(guard_file)
    n_kept = sum(len(c.keep) for c in changes.values())
    n_retired = sum(len(c.retired_tests) for c in changes.values())
    if (len(all_rows), stated, n_ask) != (expected.rows, expected.stated, expected.askable):
        problems.append(f"{len(all_rows)} rows ({stated} stated, {n_ask} askable), expected {expected.rows} "
                        f"({expected.stated} stated, {expected.askable} askable)")
    if n_guard != expected.guards:
        problems.append(f"{n_guard} guard rows, expected {expected.guards}")
    if n_kept != expected.kept:
        problems.append(f"{n_kept} kept rows, expected {expected.kept}")
    if n_retired != expected.retired:
        problems.append(f"{n_retired} retired tests, expected {expected.retired}")
    if sorted(cross) != sorted(expected.cross):
        problems.append(f"cross-component changes {cross}, expected {list(expected.cross)}")
    have_tiers = {t: tuple(n for n in sorted(changes) if changes[n].tier == t) for t in TIERS}
    if have_tiers != dict(expected.tiers):
        problems.append(f"tiers {have_tiers}, expected {dict(expected.tiers)}")

    controls = len(nums) - len(cross)
    treatments: dict[str, int] = {}
    for c in changes.values():
        for r in c.retired:
            treatments[r["treatment"]] = treatments.get(r["treatment"], 0) + 1
    summary = [
        f"change-script.md: {len(nums)} changes ({len(cross)} cross-component, {controls} control"
        f"{'s' if controls != 1 else ''}); distance field **{dist}:**",
        f"oracle.md: {len(live)} rows ({stated} stated, {n_ask} askable); the start section is empty",
        f"owner-items.json: {len(owner)} askable rows with recall lines; tiers {owner_data.get('tiers')!r}; conditional "
        f"recall {sorted(k for k in conditional if not k.startswith('_')) or 'none'}",
        f"repair-reports.json: {len(every & set(reports))} row reports, "
        f"{len([k for k in reports if k.startswith('DEP-')])} dependency reports",
        f"kept-behaviour.json: {n_kept} kept rows, {sum(r['dependency'] for k in kept.values() for r in k['rows'])} "
        f"dependency rows, {sum(r.get('role') == 'comparison' for k in kept.values() for r in k['rows'])} comparison "
        f"rows; {n_retired} retired tests ({', '.join(f'{v} {t}' for t, v in sorted(treatments.items())) or 'none'})",
        "tiers: " + "; ".join(f"{t} {list(v)}" for t, v in have_tiers.items()),
        f"guard-rows.json: {n_guard} guard rows ({sum(not v.get('checkable_on_snapshot', True) for v in guard_file.values())} "
        f"not checkable on the pin; conditional {sorted(g for g, v in guard_file.items() if v.get('conditional'))})",
        f"forks: each of changes {nums[0] if nums else '-'} to {nums[-1] if nums else '-'} releases its own rows only",
    ]
    return problems, warnings, summary
