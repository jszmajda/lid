"""Convert the drafter's M2f change set into the Clowder harness's seed formats (plan.md, M2f: cross-crate changes).

m2f-changes-r2.md holds changes 13 to 24, each applied on its own to snapshot 86db995 and discarded, in the layout
prompts-m2f/framing-r2.md asks for: the change's fields, her request, new rows CLX-NNkk (stated or askable, with a
recall line for each askable row), behaviour to keep, the deliberate change, retired tests, why the other crate is
needed (13 to 20), and repair reports (one per row, plus one for the dependency row in 13 to 20). This writes what
run_fork.py and the repair forks read:

- change-script.md: each change in the pilot's change-script format, its **Introduces:** line naming its CLX rows;
- oracle.md: the pilot oracle's start section and start items, then each change's narrative section (her request,
  verbatim: M2f has no owner narrative) and its rows in the item table;
- owner-items.json: each askable row's recall line and salience tier (from m2f/salience.json when it exists, else
  a placeholder "medium");
- repair-reports.json: {"CLX-1301": {"report": ...}, ..., "DEP-13": {"report": ..., "change": 13}};
- kept-behaviour.json: each change's rows to keep, under IDs CLXK-NNkk in table order (in 13 to 20 the first is the
  cross-crate dependency row), with its deliberate change, retired tests and grading notes.

check_seed validates the written files with the harness's own parsers. Malformed source refuses to convert, naming
what's wrong.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import repair, simulator

HARNESS = Path(__file__).resolve().parent.parent
HIDDEN = HARNESS.parent / "seeds" / "clowder" / "hidden"
SOURCE = HIDDEN / "m2f-changes-r2.md"
PILOT_ORACLE = HIDDEN / "oracle.md"
TEST_INDEX = HIDDEN / "prompts-m2f" / "test-index.json"
BRIEFS = HIDDEN / "prompts-m2f" / "briefs-r2.json"
OUT = HIDDEN / "m2f"
SNAPSHOT = "86db995"

OUTPUTS = ("change-script.md", "oracle.md", "owner-items.json", "repair-reports.json", "kept-behaviour.json")
SALIENCE = "salience.json"
PLACEHOLDER_TIERS = "placeholder: medium for every row (no salience rating yet)"
RATED_TIERS = "rated: from m2f/salience.json"
CORE = "core-change-ui-depends"
CONTROL = "control"
KINDS = ("Stated", "Askable")
FIELDS = ("Type", "Intent distance", "Edits crate", "Edits component", "Intent lives in")
ROW_HEADER = ["ID", "Behaviour", "Disclosure kind", "Check"]
KEEP_HEADER = ["Behaviour", "Established in", "How a careless version breaks it", "Check"]
ROW_ID = re.compile(r"CLX-(\d+)(\d\d)$")
COMMENT = re.compile(r"<!--.*?-->", re.S)
LABEL = re.compile(r"\*\*([^*\n]+?):\*\*\s*")
TEST = re.compile(r"`(clowder-(?:core|tui)/tests/[\w/]+\.rs)::(\w+)`")
UNIT_TEST = re.compile(r"`(clowder-(?:core|tui)/src/[\w/]+\.rs)` unit test `([\w:]+)`")
WHOLE_FILE = re.compile(r"\ball (\w+) tests in `(clowder-(?:core|tui)/tests/[\w/]+\.rs)`")
REQ = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d{3}\b")
NUMBERS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve thirteen "
                                      "fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}


@dataclass(frozen=True)
class Expected:
    """The counts --check holds the change set to."""
    changes: tuple[int, ...] = tuple(range(13, 25))
    core: tuple[int, ...] = tuple(range(13, 21))  # core-change-ui-depends, each with a dependency row
    rows: int = 30
    stated: int = 14
    askable: int = 16


EXPECTED = Expected()


@dataclass
class Row:
    id: str
    behaviour: str
    kind: str  # Stated or Askable
    check: str
    recall: str | None = None


@dataclass
class KeepRow:
    id: str
    dependency: bool
    behaviour: str
    established_in: list[str]
    breaks: str
    check: str

    def record(self) -> dict:
        return {"id": self.id, "dependency": self.dependency, "behaviour": self.behaviour,
                "established_in": self.established_in, "breaks": self.breaks, "check": self.check}


@dataclass
class M2fChange:
    number: int
    title: str
    type: str
    intent_distance: str
    edits_crate: str
    edits_component: str
    intent_lives_in: str
    request_lines: list[str]  # the request's '>' lines as written
    request: str  # her words, as the harness reads them from the quote
    rows: list[Row] = field(default_factory=list)
    left_to_developer: str | None = None
    keep: list[KeepRow] = field(default_factory=list)
    deliberate_change: str | None = None
    retired_tests: list[str] = field(default_factory=list)
    retired_note: str | None = None  # the retired-tests section as written, reasons and all
    why_other_crate: str | None = None
    reports: dict[str, str] = field(default_factory=dict)  # row ID or "Dependency" -> her report
    notes: list[dict] = field(default_factory=list)  # other labelled paragraphs: grading notes and the like


# ------------------------------------------------------------------------------------------------ parsing


def change_of(iid: str) -> int:
    m = ROW_ID.match(iid)
    if not m:
        raise ValueError(f"{iid}: not a CLX-<change><two digits> identifier")
    return int(m.group(1))


def _unquote(s: str) -> str:
    s = s.strip()
    for a, b in (("“", "”"), ('"', '"')):
        if len(s) >= 2 and s.startswith(a) and s.endswith(b):
            return s[len(a):-len(b)].strip()
    return s


def _blocks(text: str) -> list[str]:
    return [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]


def _table(block: str) -> tuple[list[str], list[list[str]]]:
    lines = [[c.strip() for c in l.strip().strip("|").split("|")] for l in block.splitlines() if l.strip().startswith("|")]
    rows = [r for r in lines[1:] if not all(re.fullmatch(r":?-+:?", c) for c in r)]
    return lines[0], rows


def _labelled(block: str) -> tuple[str, str] | None:
    m = LABEL.match(block)
    return (m.group(1).strip(), block[m.end():].strip()) if m else None


def _split_inline(text: str) -> tuple[str, list[tuple[str, str]]]:
    """A known field's text up to its first inline label, and each inline-labelled part after it as a note."""
    marks = list(re.finditer(r"\s\*\*([^*\n]+?):\*\*\s*", text))
    if not marks:
        return text.strip(), []
    parts = [(m.group(1).strip(), text[m.end():(marks[i + 1].start() if i + 1 < len(marks) else len(text))].strip())
             for i, m in enumerate(marks)]
    return text[:marks[0].start()].strip(), parts


def _summary_table(text: str) -> tuple[str, list[list[str]]]:
    """The closing table (change, type, intent distance, edits crate, components), removed from the text."""
    lines, kept, rows, i = text.splitlines(), [], [], 0
    while i < len(lines):
        if lines[i].strip().startswith("| Change |"):
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            rows += _table("\n".join(lines[i:j]))[1]
            i = j
            continue
        kept.append(lines[i])
        i += 1
    return "\n".join(kept) + "\n", rows


def _retired(n: int, bullet: str, test_index: dict | None) -> list[str]:
    m = WHOLE_FILE.search(bullet)
    if m:
        word, path = m.group(1), m.group(2)
        count = NUMBERS.get(word.lower(), int(word) if word.isdigit() else None)
        if test_index is None:
            raise ValueError(f"change {n}: expanding all {word} tests in {path} needs the snapshot's test index")
        tests = (test_index.get(path) or {}).get("tests") or []
        if count is None or len(tests) != count:
            raise ValueError(f"change {n}: all {word} tests in {path}, but the test index lists {len(tests)}")
        return [f"{path}::{t}" for t in tests]
    m = UNIT_TEST.search(bullet)
    if m:
        return [f"{m.group(1)}::{m.group(2)}"]
    found = [f"{p}::{f}" for p, f in TEST.findall(bullet)]
    if not found:
        raise ValueError(f"change {n}: can't read the retired test in {bullet!r}")
    return found


def _parse_change(n: int, title: str, body: str, test_index: dict | None) -> M2fChange:
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
    if fields["Type"] not in (CORE, CONTROL):
        raise ValueError(f"change {n}: type {fields['Type']!r}, not {CORE} or {CONTROL}")
    core = fields["Type"] == CORE
    if core != (fields["Intent distance"] == "other crate"):
        raise ValueError(f"change {n}: a {fields['Type']} change at intent distance {fields['Intent distance']!r}")
    req = secs.get("Owner request", "")
    request_lines = [l.rstrip() for l in req.splitlines() if l.startswith(">")]
    request = simulator._quote(req)
    if not request:
        raise ValueError(f"change {n}: no quoted owner request")
    c = M2fChange(n, title, fields["Type"], fields["Intent distance"], fields["Edits crate"], fields["Edits component"],
                  fields["Intent lives in"], request_lines, request)

    for heading, text in sections:
        blocks = _blocks(text)
        for i, block in enumerate(blocks):
            if block.startswith("|") or block.startswith(">") or block.startswith("- "):
                continue  # tables, her words and bullets are each read with their section
            lab = _labelled(block)
            if lab is None:
                if heading not in ("Why the other crate is needed", "Retired tests"):
                    c.notes.append({"section": heading, "label": None, "text": block})
                continue
            label, rest = lab
            if label in ("Left to the developer", "Deliberate change"):
                value, inline = _split_inline(rest)
                if label == "Left to the developer":
                    c.left_to_developer = value
                else:
                    c.deliberate_change = value
                c.notes += [{"section": heading, "label": note_label, "text": note} for note_label, note in inline]
                continue
            if label in FIELDS:
                continue
            following = blocks[i + 1] if i + 1 < len(blocks) else ""
            if following.startswith("- ") and heading not in ("Retired tests", "Repair reports", "New rows"):
                rest += "\n\n" + following  # a note's list of tests
            c.notes.append({"section": heading, "label": label, "text": rest})

    # new rows, their kinds, and the recall line of each askable row
    tables = [_table(b) for b in _blocks(secs.get("New rows", "")) if b.startswith("|")]
    if len(tables) != 1 or tables[0][0] != ROW_HEADER:
        raise ValueError(f"change {n}: no new-rows table headed {' | '.join(ROW_HEADER)}")
    for cells in tables[0][1]:
        if len(cells) != 4:
            raise ValueError(f"change {n}: a new row with {len(cells)} cells: {cells[:1]}")
        c.rows.append(Row(cells[0], cells[1], cells[2], cells[3]))
    ids = [r.id for r in c.rows]
    want = [f"CLX-{n:02d}{k:02d}" for k in range(1, len(ids) + 1)]
    if not ids or ids != want:
        raise ValueError(f"change {n}: new rows {ids} out of sequence, not {want}")
    for r in c.rows:
        if r.kind not in KINDS:
            raise ValueError(f"{r.id}: disclosure kind {r.kind!r}; M2f rows are Stated or Askable")
    by_id = {r.id: r for r in c.rows}
    for m in re.finditer(r"(?m)^- \*\*(CLX-\d+)\*\* (\w+)[^:\n]*:\s*(.+)$", secs.get("New rows", "")):
        rid, what, line = m.groups()
        if what != "recall":
            raise ValueError(f"{rid}: a {what} line; M2f rows are Stated or Askable, each askable one with a recall line")
        if rid not in by_id or by_id[rid].kind != "Askable":
            raise ValueError(f"{rid}: a recall line for a row that isn't an askable row of change {n}")
        if by_id[rid].recall is not None:
            raise ValueError(f"{rid}: two recall lines")
        by_id[rid].recall = _unquote(line)
    for r in c.rows:
        if r.kind == "Askable" and not r.recall:
            raise ValueError(f"{r.id}: an askable row with no recall line")

    # behaviour to keep, numbered in table order; a core change's first row is its dependency row
    tables = [_table(b) for b in _blocks(secs.get("Behaviour to keep", "")) if b.startswith("|")]
    if len(tables) != 1 or tables[0][0] != KEEP_HEADER:
        raise ValueError(f"change {n}: no behaviour-to-keep table headed {' | '.join(KEEP_HEADER)}")
    for k, cells in enumerate(tables[0][1], 1):
        if len(cells) != 4:
            raise ValueError(f"change {n}: a row to keep with {len(cells)} cells: {cells[:1]}")
        c.keep.append(KeepRow(f"CLXK-{n:02d}{k:02d}", core and k == 1, cells[0],
                              [s.strip() for s in cells[1].split(";") if s.strip()], cells[2], cells[3]))
    if not c.keep:
        raise ValueError(f"change {n}: no behaviour to keep")
    if c.deliberate_change is None:
        raise ValueError(f"change {n}: no **Deliberate change:** line")

    # retired tests
    if "Retired tests" not in secs:
        raise ValueError(f"change {n}: no retired-tests section")
    c.retired_note = secs["Retired tests"].strip() or None
    for line in secs["Retired tests"].splitlines():
        if line.startswith("- "):
            c.retired_tests += _retired(n, line, test_index)

    # why the other crate is needed: the section's prose, without its labelled notes
    if "Why the other crate is needed" in secs:
        prose = [b for b in _blocks(secs["Why the other crate is needed"])
                 if _labelled(b) is None and not b.startswith(("|", "- "))]
        c.why_other_crate = "\n\n".join(prose) or None

    # repair reports: one per row, and one for a core change's dependency row
    for m in re.finditer(r"(?m)^- \*\*(.+?):\*\*\s*(.+)$", secs.get("Repair reports", "")):
        key, text = m.group(1).strip(), _unquote(m.group(2))
        if key not in by_id and key != "Dependency":
            raise ValueError(f"change {n}: a repair report under {key!r}, which isn't a row or Dependency")
        if key == "Dependency" and not core:
            raise ValueError(f"change {n}: a Dependency report in a control, which has no dependency row")
        if key in c.reports:
            raise ValueError(f"change {n}: two repair reports for {key}")
        if not text:
            raise ValueError(f"change {n}: an empty repair report for {key}")
        c.reports[key] = text
    for rid in ids:
        if rid not in c.reports:
            raise ValueError(f"{rid}: no repair report")
    if core and "Dependency" not in c.reports:
        raise ValueError(f"change {n}: a core change with no Dependency repair report")
    return c


def parse_m2f(text: str, *, test_index: dict | None = None) -> dict[int, M2fChange]:
    """The change set, by change number. HTML comments are dropped first; the closing summary table is checked against
    each change's fields."""
    text, summary = _summary_table(COMMENT.sub("", text))
    changes: dict[int, M2fChange] = {}
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
        raise ValueError("no '## Change NN — title' sections")
    if summary:
        for cells in summary:
            n = int(re.match(r"\d+", cells[0]).group(0))
            c = changes.get(n)
            mine = c and [c.type, c.intent_distance, c.edits_crate, f"{c.edits_component} → {c.intent_lives_in}"]
            if mine != cells[1:5]:
                raise ValueError(f"change {n}: the summary table says {cells[1:5]}, but the change says {mine}")
        if sorted(int(re.match(r"\d+", r[0]).group(0)) for r in summary) != sorted(changes):
            raise ValueError("the summary table doesn't list every change once")
    return changes


# ----------------------------------------------------------------------------------------------- writing


def start_of(pilot_text: str) -> tuple[str, list[str], list[str]]:
    """The pilot oracle's start section, its start items' IDs (in force at the start and not retired there), and
    those items' table rows as written."""
    oracle = simulator.parse_oracle(pilot_text)
    if 0 not in oracle.narrative:
        raise ValueError("the pilot oracle has no 'What the owner knows from the start' section")
    start = [i for i in oracle.items if i.kind != "Dropped" and i.in_force == 0 and i.retired != 0]
    for i in start:
        if i.response:
            raise ValueError(f"{i.id}: a start item recognized on sight; copying its response isn't supported")
    ids = [i.id for i in start]
    table = pilot_text.split("## Item table", 1)[1].split("\n## ", 1)[0]
    rows = [l for l in table.splitlines() if l.startswith("|") and l.strip("|").split("|")[0].strip() in ids]
    return oracle.narrative[0], ids, rows


def load_salience(out_dir: Path) -> dict | None:
    f = Path(out_dir) / SALIENCE
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def _tiers(changes: dict[int, M2fChange], salience: dict | None) -> dict[str, str]:
    askable = [r.id for c in changes.values() for r in c.rows if r.kind == "Askable"]
    if salience is None:
        return {rid: "medium" for rid in askable}
    rows = {r.id for c in changes.values() for r in c.rows}
    for rid in salience:
        if rid not in rows:
            raise ValueError(f"salience.json names {rid}, which isn't an M2f row")
    out = {}
    for rid in askable:
        tier = salience.get(rid)
        if tier is None:
            raise ValueError(f"salience.json has no tier for {rid}")
        if tier not in simulator.TIERS:
            raise ValueError(f"salience.json: {rid}'s tier {tier!r} isn't low, medium or high")
        out[rid] = tier
    return out


def _change_script(changes: dict[int, M2fChange]) -> str:
    out = [
        "# Change script: Clowder M2f (changes 13 to 24)",
        "",
        "<!-- Written by build_m2f_seed.py from ../m2f-changes-r2.md. Edit that file and rerun; don't edit this one. -->",
        "",
        "## Delivery rules",
        "",
        f"Each change is forked from the arm's repository variant of snapshot {SNAPSHOT}, run in a fresh session, and "
        "discarded. No change sees another's work. A fork's owner holds the start and that change only: `run_fork.py "
        "--oracle m2f/oracle.md --change-script m2f/change-script.md --owner-items m2f/owner-items.json`, whose fork "
        "scope gives the owner the start's narrative and items and the forked change's own.",
        "",
        "Deliver the quoted owner request. M2f has no redirects, emerging statements, planted bugs or symptom reports, "
        "and there are no accompanying interface specifications. Askable rows keep their disclosure rules.",
        "",
        "Each change's behaviour to keep (IDs CLXK-NNkk, in the source table's order; in changes 13 to 20 the first is "
        "the cross-crate dependency row), its deliberate change, its retired tests, why the other crate is needed, and "
        "its grading notes are in `kept-behaviour.json`. Repair reports are in `repair-reports.json`.",
        "",
    ]
    for n, c in sorted(changes.items()):
        kept = ", ".join(k.id + (" (the dependency row)" if k.dependency else "") for k in c.keep)
        out += [
            f"## Change {n} — {c.title}",
            "",
            f"**Type:** {c.type}  ",
            f"**Intent distance:** {c.intent_distance}  ",
            f"**Edits crate:** {c.edits_crate}  ",
            f"**Edits component:** {c.edits_component}  ",
            f"**Intent lives in:** {c.intent_lives_in}",
            "",
            "### Owner request",
            "",
            *c.request_lines,
            "",
            f"**Introduces:** {', '.join(r.id for r in c.rows)}.  ",
            "**Retires:** Nothing in the oracle.  ",
            "**Relies on:** Nothing in the oracle.  ",
            f"**Kept behaviour:** {kept} (`kept-behaviour.json`).  ",
            f"**Left to the agent (not graded):** {c.left_to_developer or 'Nothing named.'}",
            "",
            "No redirect, emerging statement, planted bug, or symptom report.",
            "",
        ]
    out += ["## Summary", "",
            "| Change | Title | Type | Intent distance | Edits crate | Components | Stated | Askable | Dependency row |",
            "|---|---|---|---|---|---|---|---|---|"]
    for n, c in sorted(changes.items()):
        dep = next((k.id for k in c.keep if k.dependency), "None")
        stated = ", ".join(r.id for r in c.rows if r.kind == "Stated") or "None"
        askable = ", ".join(r.id for r in c.rows if r.kind == "Askable") or "None"
        out.append(f"| {n} | {c.title} | {c.type} | {c.intent_distance} | {c.edits_crate} | "
                   f"{c.edits_component} → {c.intent_lives_in} | {stated} | {askable} | {dep} |")
    return "\n".join(out) + "\n"


def _oracle(changes: dict[int, M2fChange], pilot_text: str, rated: bool) -> str:
    start, start_ids, start_rows = start_of(pilot_text)
    first, last = min(changes), max(changes)
    out = [
        "# Oracle: Clowder M2f",
        "",
        "<!-- Written by build_m2f_seed.py from ../m2f-changes-r2.md (the changes) and ../oracle.md (the start). Edit "
        "those and rerun; don't edit this one. -->",
        "",
        "## Owner narrative",
        "",
        "The simulated owner receives \"What the owner knows from the start\", plus the section for the change being "
        f"run. Each change is forked from snapshot {SNAPSHOT} and run on its own, so a fork's owner holds only the start "
        "section and that change's section and items, through `run_fork.py`'s fork scope on this file.",
        "",
        "### What the owner knows from the start",
        "",
        start,
        "",
    ]
    for n, c in sorted(changes.items()):
        out += [f"### Learned at change {n}: {c.title}", "", c.request, ""]
    start_line = (f"- The rows in force at the start are the pilot oracle's start items, copied as written: "
                  f"{', '.join(start_ids)}. Every fork's owner holds them." if start_ids else
                  "- No item is in force at the start: the start section is background, as in the pilot oracle.")
    tiers = ("salience tiers rated in `salience.json`" if rated else
             "a placeholder tier, medium, for every row: M2f has no salience rating yet")
    out += [
        "## Disclosure and grading conventions",
        "",
        f"- Each change, {first} to {last}, is forked from the arm's repository variant of snapshot {SNAPSHOT}, run "
        "once, and discarded. Every pilot change (1 to 12) was also a fork from that snapshot, so none of the pilot's "
        "change items is part of its state, and none is carried here.",
        "- A fork's owner holds the start section, that change's section, and that change's rows, through `run_fork.py "
        "--oracle`, `--change-script` and `--owner-items` pointed at this folder.",
        "- M2f has no owner narrative. The start section is the pilot oracle's, as written. Each \"Learned at change N\" "
        "section is her request for that change, quoted verbatim from `m2f-changes-r2.md`; nothing else is written "
        "into it.",
        start_line,
        "- Every CLX row comes into force at its own change and none is retired. Its behaviour is the source's row as "
        "written, and its external check sketch is the source's check, verbatim.",
        "- Askable answers disclose the row when the agent asks about its topic, or when the agent shows something that "
        f"touches it and the row is recalled. Recall lines are in `owner-items.json`, with {tiers}.",
        "- M2f rows are stated or askable: none is recognized on sight. There are no Dropped rows, redirects, planted "
        "bugs or symptom reports.",
        "- Each change's behaviour to keep is in `kept-behaviour.json`, under IDs CLXK-NNkk numbered in the source "
        "table's order; in changes 13 to 20, CLXK-NN01 is the cross-crate dependency row. Kept rows are not oracle "
        "items, and the owner doesn't hold them.",
        "- Repair reports are in `repair-reports.json`: one per row, and DEP-NN for the dependency row of each change "
        "13 to 20.",
        "",
        "## Item table",
        "",
        "| ID | Checkable behavior | Disclosure kind | In force | Retired | External check sketch |",
        "|---|---|---|---|---|---|",
        *start_rows,
    ]
    for n, c in sorted(changes.items()):
        for r in c.rows:
            kind = f"Stated in change {n}" if r.kind == "Stated" else "Askable"
            out.append(f"| {r.id} | {r.behaviour} | {kind} | Change {n} | — | {r.check} |")
    return "\n".join(out) + "\n"


def _json(data) -> str:
    return json.dumps(data, indent=1, ensure_ascii=False) + "\n"


def convert(source_text: str, pilot_text: str, *, salience: dict | None = None,
            test_index: dict | None = None) -> dict[str, str]:
    """Each output file's text, by name."""
    changes = parse_m2f(source_text, test_index=test_index)
    tiers = _tiers(changes, salience)
    owner = {
        "_note": "Recall lines for every askable M2f row, from m2f-changes-r2.md, written by build_m2f_seed.py (edit the "
                 "source, or m2f/salience.json for the tiers, and rerun). M2f has no salience tiers of its own: they "
                 "come from m2f/salience.json when it exists, and are otherwise medium for every row.",
        "tiers": RATED_TIERS if salience is not None else PLACEHOLDER_TIERS,
        "items": {r.id: {"tier": tiers[r.id], "recall": r.recall}
                  for _, c in sorted(changes.items()) for r in c.rows if r.kind == "Askable"},
    }
    reports: dict[str, dict] = {}
    kept: dict[str, dict] = {}
    for n, c in sorted(changes.items()):
        for r in c.rows:
            reports[r.id] = {"report": c.reports[r.id]}
        if "Dependency" in c.reports:
            reports[f"DEP-{n}"] = {"report": c.reports["Dependency"], "change": n}
        kept[str(n)] = {
            "title": c.title, "type": c.type, "intent_distance": c.intent_distance, "edits_crate": c.edits_crate,
            "edits_component": c.edits_component, "intent_lives_in": c.intent_lives_in,
            "rows": [k.record() for k in c.keep],
            "deliberate_change": c.deliberate_change, "retired_tests": c.retired_tests, "retired_note": c.retired_note,
            "why_other_crate": c.why_other_crate, "left_to_developer": c.left_to_developer, "notes": c.notes,
        }
    return {
        "change-script.md": _change_script(changes),
        "oracle.md": _oracle(changes, pilot_text, rated=salience is not None),
        "owner-items.json": _json(owner),
        "repair-reports.json": _json(reports),
        "kept-behaviour.json": _json(kept),
    }


def write_seed(source_text: str, pilot_text: str, out_dir: Path, *, test_index: dict | None = None) -> dict[str, str]:
    """Convert and write every output into out_dir, taking tiers from out_dir/salience.json if it exists."""
    out_dir = Path(out_dir)
    files = convert(source_text, pilot_text, salience=load_salience(out_dir), test_index=test_index)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (out_dir / name).write_text(text, encoding="utf-8")
    return files


# ---------------------------------------------------------------------------------------------- checking


def check_seed(out_dir: Path, source_text: str, pilot_text: str, *, test_index: dict | None = None,
               expected: Expected = EXPECTED, briefs: dict | None = None) -> tuple[list[str], list[str], list[str]]:
    """(problems, warnings, summary lines) for the files in out_dir, read with the harness's own parsers."""
    out_dir = Path(out_dir)
    problems: list[str] = []
    warnings: list[str] = []
    try:
        changes = parse_m2f(source_text, test_index=test_index)
        fresh = convert(source_text, pilot_text, salience=load_salience(out_dir), test_index=test_index)
    except ValueError as e:
        return [f"the source doesn't convert: {e}"], warnings, []
    for name in OUTPUTS:
        f = out_dir / name
        if not f.exists():
            problems.append(f"{name} is missing; run build_m2f_seed.py")
        elif f.read_text(encoding="utf-8") != fresh[name]:
            problems.append(f"{name} is out of date with the source; rerun build_m2f_seed.py")
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

    # the changes, their rows, and what each introduces
    nums = sorted(script)
    if nums != sorted(expected.changes) or sorted(changes) != sorted(expected.changes):
        problems.append(f"changes {nums} (source {sorted(changes)}), expected {list(expected.changes)}")
    rows: dict[int, set[str]] = {}
    live = [i for i in oracle.items if ROW_ID.match(i.id)]
    for i in live:
        n = change_of(i.id)
        rows.setdefault(n, set()).add(i.id)
        want_kind = {f"Stated in change {n}", "Askable"}
        if i.in_force != n or i.retired is not None or i.kind not in want_kind:
            problems.append(f"{i.id}: {i.kind!r}, in force {i.in_force}, retired {i.retired}; expected stated in or "
                            f"askable at change {n}, never retired")
    for n in nums:
        intro = set(script[n].introduces)
        own = rows.get(n, set())
        src = {r.id for r in changes[n].rows} if n in changes else set()
        if intro != own or own != src:
            problems.append(f"change {n}: introduces {sorted(intro)}, but its rows are {sorted(own)} (source {sorted(src)})")
        dist = script[n].intent_distance
        if n in changes and (dist is None or dist.kind != changes[n].intent_distance):
            problems.append(f"change {n}: intent distance {dist}, the source says {changes[n].intent_distance!r}")

    # each fork releases the start items and its own rows, and its owner's prompt shows them and nothing else
    try:
        _, start_ids, _ = start_of(pilot_text)
    except ValueError as e:
        problems.append(f"the pilot oracle: {e}")
        start_ids = []
    missing_start = [s for s in start_ids if s not in oracle.ids()]
    if missing_start:
        problems.append(f"start items {missing_start} aren't in the oracle")
    if sorted(oracle.narrative) != [0, *nums]:
        problems.append(f"narrative sections for {sorted(oracle.narrative)}, expected the start and {nums}")
    every = {iid for s in rows.values() for iid in s}
    for n in nums:
        released = {i.id for i in simulator.released_items(oracle, n, only_change=True)}
        want = set(start_ids) | rows.get(n, set())
        if released != want:
            problems.append(f"change {n}'s fork releases {sorted(released)}, expected {sorted(want)}")
        if oracle.narrative.get(n) != script[n].request:
            problems.append(f"change {n}: its narrative section isn't her request verbatim")
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

    # owner items: every askable row, with its recall line from the source
    askable = {r.id: r for c in changes.values() for r in c.rows if r.kind == "Askable"}
    if owner and set(owner) != set(askable):
        problems.append(f"owner-items.json covers {sorted(owner)}, the askable rows are {sorted(askable)}")
    for rid, item in owner.items():
        if rid in askable and item.recall != askable[rid].recall:
            problems.append(f"{rid}: its recall line differs from the source's")
    if str(owner_data.get("tiers", "")).startswith("placeholder"):
        warnings.append("owner-items.json: the tiers are a placeholder (medium for every row); write m2f/salience.json "
                        "({\"CLX-1302\": \"low|medium|high\", ...}) and rerun")

    # repair reports: every row, and the dependency row of every core change
    core = [n for n in nums if changes.get(n) and changes[n].type == CORE]
    want_reports = every | {f"DEP-{n}" for n in core}
    for key in sorted(want_reports - set(reports)):
        problems.append(f"{key}: no repair report")
    for key in sorted(set(reports) - want_reports):
        problems.append(f"repair-reports.json: {key} isn't a row or the dependency row of a core change")
    for key in sorted(want_reports & set(reports)):
        text = repair.report_for(reports, key)
        if text is None:
            problems.append(f"{key}: an empty repair report")
        elif "<!--" in text or "-->" in text:
            problems.append(f"{key}: its repair report holds an HTML comment")
        if key.startswith("DEP-") and (not isinstance(reports[key], dict) or reports[key].get("change") != int(key[4:])):
            problems.append(f"{key}: its change field isn't {key[4:]}")

    # kept behaviour: IDs in order, one dependency row first in each core change, none in a control
    if sorted(kept, key=int) != [str(n) for n in nums]:
        problems.append(f"kept-behaviour.json covers changes {sorted(kept, key=int)}, not {nums}")
    script_text = read("change-script.md")
    for n in nums:
        k = kept.get(str(n))
        if not k:
            continue
        ids = [r["id"] for r in k["rows"]]
        if ids != [f"CLXK-{n:02d}{j:02d}" for j in range(1, len(ids) + 1)]:
            problems.append(f"change {n}: kept rows {ids} aren't CLXK-{n:02d}01 onwards")
        deps = [r["id"] for r in k["rows"] if r["dependency"]]
        is_core = changes.get(n) is not None and changes[n].type == CORE
        if is_core and deps != [f"CLXK-{n:02d}01"]:
            problems.append(f"change {n}: dependency rows {deps}, expected CLXK-{n:02d}01 alone")
        if not is_core and deps:
            problems.append(f"change {n}: a control with dependency rows {deps}")
        section = script_text.split(f"## Change {n} —", 1)[1].split("\n## ", 1)[0] if f"## Change {n} —" in script_text else ""
        line = re.search(r"\*\*Kept behaviour:\*\*\s*(.+)", section)
        listed = list(simulator.parse_ids(line.group(1))) if line else []
        if listed != ids:
            problems.append(f"change {n}: the change script's Kept behaviour line names {listed}, the record {ids}")
        c = changes.get(n)
        if c and (k["type"], k["intent_distance"], k["edits_crate"]) != (c.type, c.intent_distance, c.edits_crate):
            problems.append(f"change {n}: the kept record's type, distance or crate differs from the source's")
        if is_core and not k.get("why_other_crate"):
            problems.append(f"change {n}: a core change with no 'why the other crate is needed'")
        if test_index is not None:
            for t in k["retired_tests"]:
                path, _, fn = t.partition("::")
                if "/tests/" in path:
                    if fn not in ((test_index.get(path) or {}).get("tests") or []):
                        problems.append(f"change {n}: retired test {t} isn't in the snapshot's test index")
                else:
                    warnings.append(f"change {n}: retired test {t} is a unit test the test index doesn't cover; not checked")
    for b in (briefs or {}).get("changes", []):
        n, k = b.get("n"), kept.get(str(b.get("n")))
        if b.get("type") != CORE or not k or not k["rows"]:
            continue
        missing = [x for x in b.get("must_cite", []) if x not in k["rows"][0]["established_in"]]
        if missing:
            problems.append(f"change {n}: the dependency row CLXK-{n:02d}01 doesn't cite {missing}, which its brief requires")

    # what the owner holds: requirement IDs or code in a row's behaviour reach her as written
    for i in live:
        hits = REQ.findall(i.behavior) + re.findall(r"`[^`]+`", i.behavior)
        if hits:
            warnings.append(f"{i.id}: the owner holds this row's behaviour as written, and it names {', '.join(hits)}")

    # counts
    all_rows = [r for c in changes.values() for r in c.rows]
    stated = sum(r.kind == "Stated" for r in all_rows)
    n_ask = sum(r.kind == "Askable" for r in all_rows)
    if (len(all_rows), stated, n_ask) != (expected.rows, expected.stated, expected.askable):
        problems.append(f"{len(all_rows)} rows ({stated} stated, {n_ask} askable), expected {expected.rows} "
                        f"({expected.stated} stated, {expected.askable} askable)")
    if sorted(core) != sorted(expected.core):
        problems.append(f"core changes {core}, expected {list(expected.core)}")

    controls = len(nums) - len(core)
    summary = [
        f"change-script.md: {len(nums)} changes ({len(core)} core, {controls} control{'s' if controls != 1 else ''})",
        f"oracle.md: {len(live)} rows ({stated} stated, {n_ask} askable); {len(start_ids)} start items",
        f"owner-items.json: {len(owner)} askable rows with recall lines; tiers {owner_data.get('tiers')!r}",
        f"repair-reports.json: {len(every & set(reports))} row reports, "
        f"{len([k for k in reports if k.startswith('DEP-')])} dependency reports",
        f"kept-behaviour.json: {sum(len(k['rows']) for k in kept.values())} kept rows, "
        f"{sum(r['dependency'] for k in kept.values() for r in k['rows'])} dependency rows",
        f"forks: each of changes {nums[0] if nums else '-'} to {nums[-1] if nums else '-'} releases the start items "
        f"and its own rows",
    ]
    return problems, warnings, summary
