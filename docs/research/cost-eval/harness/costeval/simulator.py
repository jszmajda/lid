"""The simulated owner: what it may know at each change, what it is shown, and how its reply is made.

Design: "The user simulator" and "Redirects" in the notebook's design.md.

- **What the owner knows.** The seed's hidden oracle, released in stages: the narrative sections up to the
  current change, and the items in force, without the graders' check sketches. A pending change of mind is
  withheld (its narrative section and the items it introduces) until it is delivered.
- **What the owner is shown.** One rule for every arm: the agent's final message, the plan from plan mode if
  there is one, and the changed text of every prose file the message names.
- **One model call per stop, under every policy.** The model classifies the agent's message, answers its direct
  questions, and lists every contradiction it finds. The harness then applies the reviewing policy: the
  diligent owner keeps every correction, the rubber-stamp owner keeps none, and the bounded owner keeps each
  with a probability that falls as the words read in this change grow. Answers are always kept.
- **Redirect timing and words are the harness's.** An early redirect fires at the first approval request or
  completion report, a late one at the first stop after code exists, and the scripted words go in verbatim.
  The model only judges whether a pending clarification has already been settled.
- The harness puts the reply together from the parts, so a correction can't ask for another round.

The template is prompts/simulator.md; the leak judge's is prompts/leak-judge.md.
"""

from __future__ import annotations

import copy
import difflib
import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"
TEMPLATE_PATH = PROMPTS / "simulator.md"
JUDGE_TEMPLATE_PATH = PROMPTS / "leak-judge.md"
TRIM_TEMPLATE_PATH = PROMPTS / "owner-trim.md"

POLICIES = ("diligent", "bounded", "rubber-stamp")
NO_VIEW = "No preference, use your judgment."
SHOW_ME = "Show me what you have in mind and I'll tell you if it's wrong."
KINDS = ("completion", "approval", "questions", "stop")
FIRE_KINDS = ("approval", "completion")  # what an early redirect waits for
# Placeholder: the bounded owner catches a contradiction with probability 1 / (1 + w / HALF), where w is the
# words read so far in this change. Calibrated later from trajectories in which the maintainer plays the owner.
HALF_ATTENTION_WORDS = 1500
PROSE_SUFFIXES = (".md", ".markdown", ".txt", ".rst", ".adoc")
ALL = "all"  # every item in force is in play

ITEM_ID = re.compile(r"\b[A-Z]{1,4}-\d+\b")
STUDY_WORDS = re.compile(r"\b(the owner|scripted|redirect|simulator|the study|graded|grader)\b", re.I)

OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["message_kind", "answers", "corrections", "clarification_settled"],
    "properties": {
        "message_kind": {"type": "string", "enum": list(KINDS)},
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["question", "answer", "items", "no_view"],
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                    "items": {"type": "array", "items": {"type": "string"}},
                    "no_view": {"type": "boolean"},
                },
            },
        },
        "corrections": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["item", "wrong", "text"],
                "properties": {"item": {"type": "string"}, "wrong": {"type": "string"}, "text": {"type": "string"}},
            },
        },
        "clarification_settled": {"type": "boolean"},
    },
}

_SHARE = {
    "stated": "Stated",
    "askable": "Askable",
    "recognized on sight": "Recognized on sight",
    "emerging": "Stated",  # said aloud with its change's request, then stated
    "realized on symptom": "Askable",  # known once its section is released
}


def words(text: str) -> int:
    return len(text.split())


# ---------------------------------------------------------------------------------------------- the oracle


@dataclass(frozen=True)
class Item:
    id: str
    behavior: str
    kind: str
    in_force: int | None  # 0 for the first build; None if dropped
    retired: int | None
    response: str | None = None

    @property
    def share(self) -> str:
        k = self.kind.lower()
        for prefix, label in _SHARE.items():
            if k.startswith(prefix):
                return label
        raise ValueError(f"{self.id}: unknown disclosure kind {self.kind!r}")


@dataclass(frozen=True)
class Oracle:
    narrative: dict[int, str]
    items: list[Item]

    def ids(self) -> set[str]:
        return {i.id for i in self.items}


def _sections(text: str, level: str) -> list[tuple[str, str]]:
    """Split text into (heading, body) pairs at headings of exactly this level, e.g. '## '."""
    parts = re.split(rf"(?m)^{re.escape(level)}(?!#)", text)
    out = []
    for part in parts[1:]:
        heading, _, body = part.partition("\n")
        out.append((heading.strip(), body))
    return out


def _cell_change(cell: str, item: str, column: str, *, allow_none: bool) -> int | None:
    s = cell.strip()
    if s == "Start":
        return 0
    m = re.fullmatch(r"Change (\d+)", s)
    if m:
        return int(m.group(1))
    if allow_none and s in ("—", "-", ""):
        return None
    raise ValueError(f"{item}: can't read the {column} cell {cell!r}")


def _check_kind_against_force(item: Item) -> None:
    k = item.kind
    if k == "Dropped":
        if item.in_force is not None:
            raise ValueError(f"{item.id}: dropped but in force")
        return
    if item.in_force is None:
        raise ValueError(f"{item.id}: not dropped but has no change it comes into force")
    if k == "Stated at start" and item.in_force != 0:
        raise ValueError(f"{item.id}: stated at start but in force from change {item.in_force}")
    m = re.fullmatch(r"(?:Stated in|Emerging at) change (\d+)", k)
    if m and int(m.group(1)) != item.in_force:
        raise ValueError(f"{item.id}: {k!r} but in force from change {item.in_force}")
    item.share  # raises on an unknown kind


def parse_oracle(text: str) -> Oracle:
    top = dict(_sections(text, "## "))
    narrative: dict[int, str] = {}
    for heading, body in _sections(top.get("Owner narrative", ""), "### "):
        if "from the start" in heading:
            n = 0
        else:
            m = re.search(r"[Cc]hange (\d+)", heading)
            if not m:
                raise ValueError(f"narrative section without a change: {heading!r}")
            n = int(m.group(1))
        if n in narrative:
            raise ValueError(f"two narrative sections for change {n}")
        body = body.strip()
        if STUDY_WORDS.search(body):
            raise ValueError(f"narrative section for change {n} has study wording: {STUDY_WORDS.search(body).group(0)!r}")
        narrative[n] = body
    responses: dict[str, str] = {}
    for m in re.finditer(r"\*\*(\w+-\d+)\*\*,[^\n]*\n\s*\*\*[“\"](.+?)[”\"]\*\*", top.get("Recognized-on-sight responses", "")):
        responses[m.group(1)] = m.group(2)
    items = []
    for line in top.get("Item table", "").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 6 or not re.fullmatch(r"\w+-\d+", cells[0]):
            continue
        iid, behavior, kind, force, retired = cells[:5]
        item = Item(iid, behavior, kind,
                    _cell_change(force, iid, "In force", allow_none=kind == "Dropped"),
                    _cell_change(retired, iid, "Retired", allow_none=True),
                    responses.get(iid))
        _check_kind_against_force(item)
        if kind != "Dropped" and item.share == "Recognized on sight" and not item.response:
            raise ValueError(f"{iid}: recognized on sight but has no response")
        items.append(item)
    ids = [i.id for i in items]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate item IDs")
    for rid in responses:
        if rid not in ids:
            raise ValueError(f"response for unknown item {rid}")
    return Oracle(narrative=narrative, items=items)


def released_narrative(oracle: Oracle, change: int, *, withhold_section: int | None = None) -> str:
    return "\n\n".join(body for n, body in sorted(oracle.narrative.items())
                       if n <= change and n != withhold_section)


def released_items(oracle: Oracle, change: int, *, withhold: Iterable[str] = ()) -> list[Item]:
    held = set(withhold)
    return [
        i for i in oracle.items
        if i.kind != "Dropped" and i.in_force is not None and i.in_force <= change
        and (i.retired is None or i.retired > change) and i.id not in held
    ]


def owner_text(behavior: str) -> str:
    """An item's behavior as the owner holds it. Sentences that cite another item are graders' notes, and the
    owner doesn't number changes."""
    sentences = re.split(r"(?<=[.!?])\s+", behavior.strip())
    kept = " ".join(s for s in sentences if not ITEM_ID.search(s))
    return re.sub(r"\s+(?:from|after) change \d+(?: onward)?", "", kept)  # the owner doesn't number changes


def render_items(items: list[Item], in_play: set[str] | str) -> str:
    lines = []
    for i in items:
        label = i.share
        if label == "Askable" and (in_play == ALL or i.id in in_play):
            label += "; in play for this change"
        line = f"- [{i.id}] ({label}) {owner_text(i.behavior)}"
        if i.response:
            line += (" You wouldn't say this unprompted. When the agent proposes the opposite, or offers it as one choice "
                     f'in a question, object: "{i.response}" When it asks an open question about this without saying what '
                     f'it has in mind, answer only: "{SHOW_ME}"')
        lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------------------- the change script


@dataclass(frozen=True)
class Redirect:
    timing: str  # "early" or "late"
    kind: str  # "change of mind" or "clarification"
    text: str
    introduces: tuple[str, ...] = ()  # items a change of mind brings in, withheld until it is delivered


@dataclass(frozen=True)
class Change:
    number: int  # for a probe, the snapshot it forks from
    title: str
    request: str | None
    redirect: Redirect | None = None
    emerging: str | None = None
    guidance: str | None = None
    symptom: str | None = None
    diagnostic: str | None = None
    introduces: tuple[str, ...] = ()
    relies_on: tuple[str, ...] | str = ()
    probe: bool = False

    @property
    def owner_request(self) -> str:
        """What the owner asks for at the start of the change: the request (or, for a bug report, the
        symptom), with any emerging statement as a further paragraph."""
        base = self.request or self.symptom
        if not base:
            raise ValueError(f"change {self.number} has neither a request nor a symptom report")
        return base + (f"\n\n{self.emerging}" if self.emerging else "")

    @property
    def in_play(self) -> set[str] | str:
        if self.number == 0 or self.probe or self.relies_on == ALL:
            return ALL
        return set(self.introduces) | set(self.relies_on)


def _quote(body: str) -> str | None:
    """The quoted owner words in a section: every '>' paragraph, joined."""
    paras, cur = [], []
    for line in body.splitlines():
        if line.startswith(">"):
            t = line[1:].strip()
            if t:
                cur.append(t)
            elif cur:
                paras.append(" ".join(cur))
                cur = []
        elif cur and not line.strip():
            paras.append(" ".join(cur))
            cur = []
    if cur:
        paras.append(" ".join(cur))
    return "\n\n".join(paras) if paras else None


def parse_ids(text: str) -> tuple[str, ...] | str:
    """Item IDs from a script line such as 'BK-02 through BK-09, BK-12', or ALL for 'every item'."""
    if re.search(r"\bevery item\b", text, re.I):
        return ALL
    out: list[str] = []
    for m in re.finditer(r"\b([A-Z]{1,4})-(\d+)(?:\s+through\s+\1-(\d+))?", text):
        prefix, lo, hi = m.group(1), int(m.group(2)), m.group(3)
        width = len(m.group(2))
        for n in range(lo, (int(hi) if hi else lo) + 1):
            out.append(f"{prefix}-{n:0{width}d}")
    return tuple(out)


def _field(body: str, name: str) -> str | None:
    m = re.search(rf"\*\*{re.escape(name)}:\*\*\s*(.+)", body)
    return m.group(1).strip() if m else None


def parse_change_script(text: str) -> dict[int, Change]:
    changes = {}
    for heading, body in _sections(text, "## "):
        m = re.match(r"Change (\d+)\s*[—-]\s*(.+)", heading)
        if not m:
            continue
        n, title = int(m.group(1)), m.group(2).strip()
        parts = dict(_sections(body, "### "))
        request = next((_quote(b) for h, b in parts.items() if h.endswith("owner request") or h == "Owner request"), None)
        redirect = None
        for h, b in parts.items():
            if "redirect" not in h.lower():
                continue
            rm = re.fullmatch(r"(Early|Late) redirect:\s*(change of mind|clarification)", h, re.I)
            if not rm:
                raise ValueError(f"change {n}: unsupported redirect heading {h!r}")
            kind = rm.group(2).lower()
            intro = _field(b, "Redirect introduces")
            if kind == "change of mind" and not intro:
                raise ValueError(f"change {n}: a change of mind must list the items it introduces")
            ids = parse_ids(intro) if intro else ()
            if ids == ALL:
                raise ValueError(f"change {n}: a redirect can't introduce every item")
            redirect = Redirect(timing=rm.group(1).lower(), kind=kind, text=_quote(b) or "", introduces=ids)
            if not redirect.text:
                raise ValueError(f"change {n}: redirect has no quoted words")
        diag = parts.get("Scheduled diagnostic")
        ch = Change(
            number=n, title=title, request=request, redirect=redirect,
            emerging=_quote(parts.get("Emerging statement", "")),
            guidance=_quote(parts.get("Hidden owner guidance if asked", "")),
            symptom=_quote(parts.get("Owner symptom report", "")),
            diagnostic=diag.strip() if diag else None,
            introduces=parse_ids(_field(body, "Introduces") or "") or (),
            relies_on=parse_ids(_field(body, "Relies on") or ""),
        )
        ch.owner_request  # raises if the change has neither a request nor a symptom report
        changes[n] = ch
    return changes


def first_build(brief: str) -> Change:
    return Change(number=0, title="First build", request=brief.strip(), relies_on=ALL)


def parse_probe(text: str, at_change: int) -> Change:
    """The probe request, as asked of a fork of the snapshot after `at_change`."""
    for heading, body in _sections(text, "## "):
        if heading.startswith("Probe request"):
            req = next((_quote(b) for h, b in _sections(body, "### ") if h == "Owner request"), None)
            if not req:
                raise ValueError("probe section has no owner request")
            return Change(number=at_change, title="Probe", request=req, relies_on=ALL, probe=True)
    raise ValueError("no probe request in the change script")


# ------------------------------------------------------------------------------------------ what is shown


@dataclass(frozen=True)
class Document:
    name: str
    shown: str  # what the owner sees: the whole text, or its changes since they last saw it
    words: int  # words counted as read: only text new to the owner
    current: str | None = None  # the document's full text now, remembered as last shown


def plan_document(plan: str) -> Document:
    return Document("The agent's plan", plan, words(plan))


def view_document(name: str, current: str, last_shown: str | None) -> Document:
    if last_shown is None:
        return Document(name, current, words(current), current)
    if last_shown == current:
        return Document(name, "(Unchanged since you last read it.)", 0, current)
    diff = list(difflib.unified_diff(last_shown.splitlines(), current.splitlines(), lineterm="", n=2))[2:]
    added = sum(words(line[1:]) for line in diff if line.startswith("+"))
    shown = "Changes since you last read it (lines starting with - were removed, + were added):\n\n" + "\n".join(diff)
    return Document(name, shown, added, current)


def _mention(path: str) -> re.Pattern:
    return re.compile(r"(?<![\w/.-])(?:\./|/work/)?" + re.escape(path) + r"(?![\w/-])")


def mentioned_documents(message: str, paths: Iterable[str]) -> list[str]:
    """Prose files the message names, by path or by a file name no other prose file shares, in order."""
    prose = [p for p in paths if p.lower().endswith(PROSE_SUFFIXES)]
    by_name: dict[str, list[str]] = {}
    for p in prose:
        by_name.setdefault(Path(p).name, []).append(p)
    found: dict[str, int] = {}
    for p in prose:
        m = _mention(p).search(message)
        if m:
            found[p] = m.start()
    for name, ps in by_name.items():
        if len(ps) == 1 and ps[0] not in found:
            m = _mention(name).search(message)
            if m:
                found[ps[0]] = m.start()
    return sorted(found, key=found.__getitem__)


# ----------------------------------------------------------------------------------------------- the prompt


@dataclass(frozen=True)
class Said:
    """Something the owner told the agent, kept for the rest of the trajectory."""
    change: int
    said: str
    question: str | None = None
    items: tuple[str, ...] = ()


@dataclass(frozen=True)
class Turn:
    message: str
    documents: tuple[str, ...]
    reply: str


def _blockquote(text: str) -> str:
    return "\n".join("> " + line if line.strip() else ">" for line in text.strip().splitlines())


def _fill(template: str, fills: dict[str, str]) -> str:
    """Fill {NAME} placeholders in one pass, so inserted text is never rescanned. An empty fill removes its
    placeholder and the blank line after it."""
    def repl(m: re.Match) -> str:
        key = m.group(1)
        if key not in fills:
            raise KeyError(f"template placeholder {{{key}}} has no fill")
        value = fills[key]
        return value + (m.group(2) or "") if value else ""
    out = re.sub(r"\{([A-Z_]+)\}(\n+)?", repl, template)
    return out


def build_prompt(*, oracle: Oracle, change: Change, brief: str, message: str,
                 documents: Sequence[Document] = (), earlier_requests: Sequence[tuple[int, str]] = (),
                 record: Sequence[Said] = (), turns: Sequence[Turn] = (), redirect_state: str | None = None,
                 template: str | None = None) -> str:
    """The owner's prompt for one stop.

    redirect_state: None (no redirect), "pending", "firing" (a change of mind being delivered with this reply),
    "delivered", or "settled".
    """
    template = template if template is not None else TEMPLATE_PATH.read_text(encoding="utf-8")
    r = change.redirect
    if (r is None) != (redirect_state is None):
        raise ValueError("redirect_state must be given exactly when the change has a redirect")
    withholding = r is not None and r.kind == "change of mind" and redirect_state == "pending"
    items = released_items(oracle, change.number, withhold=r.introduces if withholding else ())

    if change.number == 0 and not change.probe:
        request = "This is the first build. Your request to the agent was your brief:\n\n<brief>\n" + brief.strip() + "\n</brief>"
        brief_section = ""
    else:
        request = ("Here is what you asked the agent for this time, in your own words:\n\n"
                   + _blockquote(change.owner_request))
        brief_section = "## What you told the agent at the start\n\n<brief>\n" + brief.strip() + "\n</brief>"
    if r is not None and redirect_state == "delivered":
        request += "\n\nLater in this change you told the agent:\n\n" + _blockquote(r.text)

    guidance = (f"If the agent asks why you want this, this is your reasoning. Share it only if asked:\n\n{_blockquote(change.guidance)}"
                if change.guidance else "")
    change_of_mind = clarification = ""
    if r is not None and redirect_state == "firing":
        change_of_mind = ("## You have changed your mind\n\nYou have changed your mind about part of this request. Your reply "
                          "opens by telling the agent so, in exactly these words, which are added to your reply for you:\n\n"
                          f"{_blockquote(r.text)}\n\nDon't repeat them, and don't correct anything those words already tell the agent. Respond to the rest of the agent's message in the light of what you want now.")
    if r is not None and r.kind == "clarification" and redirect_state == "pending":
        clarification = ("## Something you mean to make clear\n\nBy part of this request you meant the following, though you "
                         f"haven't said it:\n\n{_blockquote(r.text)}\n\nDon't bring it up on your own: it will be said for you at "
                         "the right moment if it is still needed. But if the agent asks about this point, answer it, and if what "
                         "it shows contradicts it, correct it, as you would any rule. Set `clarification_settled` to true if the "
                         "agent has already settled this point with you: it asked you about it, earlier in this change or in "
                         "this message; or what it shows already says the same thing; or you told it so in an earlier reply. "
                         "Otherwise set it to false.")

    earlier = ""
    if earlier_requests:
        earlier = "## What you asked for in earlier changes\n\n" + "\n\n".join(
            f"Change {n}:\n\n{_blockquote(text)}" for n, text in earlier_requests)
    rec = ""
    if record:
        lines = [f"- Change {s.change}. Asked: {s.question} You answered: {s.said}" if s.question
                 else f"- Change {s.change}. You told the agent: {s.said}" for s in record]
        rec = "## What you told the agent in earlier changes\n\n" + "\n".join(lines)
    exchange = ""
    if turns:
        blocks = []
        for t in turns:
            b = f"The agent said:\n\n<earlier_agent_message>\n{t.message.strip()}\n</earlier_agent_message>"
            if t.documents:
                b += f"\n\nYou also read: {', '.join(t.documents)}."
            b += "\n\nYou replied:\n\n" + (_blockquote(t.reply) if t.reply else "> (nothing: you accepted the change)")
            blocks.append(b)
        exchange = "## This change so far\n\n" + "\n\n".join(blocks)
    docs = ""
    if documents:
        docs = "## Documents the agent asked you to read\n\n" + "\n\n".join(
            f'<document name="{d.name}">\n{d.shown.strip()}\n</document>' for d in documents)

    return _fill(template, {
        "NARRATIVE": released_narrative(oracle, change.number, withhold_section=change.number if withholding else None),
        "ITEMS": render_items(items, change.in_play),
        "REQUEST": request,
        "GUIDANCE": guidance,
        "CHANGE_OF_MIND": change_of_mind,
        "CLARIFICATION": clarification,
        "BRIEF_SECTION": brief_section,
        "EARLIER_SECTION": earlier,
        "RECORD_SECTION": rec,
        "EXCHANGE_SECTION": exchange,
        "MESSAGE": message.strip() or "(The agent's message was empty.)",
        "DOCUMENTS_SECTION": docs,
    })


def schema_json() -> str:
    return json.dumps(OUTPUT_SCHEMA, separators=(",", ":"))


# ------------------------------------------------------------------------------------------ checking output


def check_output(out: dict, released: set[str], *, clarification_pending: bool) -> tuple[dict, list[str]]:
    """Normalize the model's output and list what is wrong with it. Returns (normalized, problems)."""
    problems = []
    out = copy.deepcopy(out)
    if out.get("message_kind") not in KINDS:
        problems.append(f"message_kind {out.get('message_kind')!r}")
    for a in out.get("answers", []):
        if not a.get("no_view") and a.get("answer", "").strip().lower().startswith("no preference"):
            a["no_view"] = True
        if a.get("answer", "").strip().startswith(SHOW_ME[:30]):
            a["answer"], a["items"] = SHOW_ME, []  # an open question on a recognized-on-sight topic shares nothing
        if a.get("no_view"):
            if a.get("items"):
                problems.append(f"a no-view answer shares items {a['items']}")
            a["answer"] = NO_VIEW
        for i in a.get("items", []):
            if i not in released:
                problems.append(f"answer shares {i}, which the owner doesn't hold")
        if ITEM_ID.search(a.get("answer", "")):
            problems.append("an answer mentions a rule identifier")
    for c in out.get("corrections", []):
        if c.get("item") != "none" and c.get("item") not in released:
            problems.append(f"correction cites {c.get('item')}, which the owner doesn't hold")
        if ITEM_ID.search(c.get("text", "")):
            problems.append("a correction mentions a rule identifier")
        if not c.get("text", "").strip():
            problems.append("an empty correction")
    if out.get("message_kind") == "questions" and not out.get("answers"):
        problems.append("message_kind is questions but nothing is answered")
    if not clarification_pending:
        out["clarification_settled"] = False
    return out, problems


# ------------------------------------------------------------------------------------------------ the owner


class OwnerFailed(RuntimeError):
    pass


@dataclass
class OwnerReply:
    reply: str
    finished: bool
    message_kind: str
    answers: list[dict]
    kept: list[dict]
    dropped: list[dict]
    redirect_event: str | None  # "delivered" or "settled" at this stop
    words_shown: int
    words_this_change: int
    catch_probability: float
    shared: list[dict]
    calls: list[dict] = field(default_factory=list)  # each model call: prompt, output, problems


def catch_probability(policy: str, words_read: int, half: int = HALF_ATTENTION_WORDS) -> float:
    if policy == "diligent":
        return 1.0
    if policy == "rubber-stamp":
        return 0.0
    return 1.0 / (1.0 + words_read / half)


class Owner:
    """One trajectory's simulated owner. `ask(prompt)` runs one stateless model call and returns its
    structured output; tests pass a fake."""

    def __init__(self, *, oracle: Oracle, brief: str, policy: str, seed: str, ask: Callable[[str], dict],
                 trim: Callable[[str], dict] | None = None, template: str | None = None, max_attempts: int = 3,
                 half_attention_words: int = HALF_ATTENTION_WORDS):
        if policy not in POLICIES:
            raise ValueError(f"policy must be one of {POLICIES}, not {policy!r}")
        self.oracle, self.brief, self.policy, self.seed, self.ask, self.trim = oracle, brief, policy, seed, ask, trim
        self.template = template if template is not None else TEMPLATE_PATH.read_text(encoding="utf-8")
        self.max_attempts, self.half = max_attempts, half_attention_words
        self.record: list[Said] = []
        self.requests: list[tuple[int, str]] = []
        self.seen: dict[str, str] = {}
        self.change: Change | None = None
        self.turns: list[Turn] = []
        self.said_now: list[Said] = []
        self.words_this_change = 0
        self.redirect_state: str | None = None
        self.redirect_point: str | None = None

    def fork(self) -> "Owner":
        """A copy for a disposable fork such as a probe; the original is untouched."""
        twin = copy.copy(self)
        for name in ("record", "requests", "seen", "turns", "said_now"):
            setattr(twin, name, copy.copy(getattr(self, name)))
        return twin

    def start_change(self, change: Change) -> str:
        """Begin a change; returns the owner's request for the agent's first prompt."""
        if self.change is not None:
            raise RuntimeError(f"change {self.change.number} hasn't ended")
        self.change, self.turns, self.said_now, self.words_this_change = change, [], [], 0
        self.redirect_state = "pending" if change.redirect else None
        self.redirect_point = None
        return change.owner_request

    def documents(self, message: str, files: dict[str, str], plan: str | None = None) -> list[Document]:
        """What the owner reads besides the message: the plan, then each prose file the message names."""
        docs = [plan_document(plan)] if plan else []
        for p in mentioned_documents(message, files):
            docs.append(view_document(p, files[p], self.seen.get(p)))
        return docs

    def _prompt(self, message: str, documents: Sequence[Document], state: str | None) -> str:
        return build_prompt(oracle=self.oracle, change=self.change, brief=self.brief, message=message,
                            documents=documents, earlier_requests=self.requests, record=self.record,
                            turns=self.turns, redirect_state=state, template=self.template)

    def _call(self, prompt: str, state: str | None, calls: list[dict]) -> dict:
        r = self.change.redirect
        withheld = r.introduces if (r and r.kind == "change of mind" and state == "pending") else ()
        released = {i.id for i in released_items(self.oracle, self.change.number, withhold=withheld)}
        pending_cl = bool(r and r.kind == "clarification" and state == "pending")
        for _ in range(self.max_attempts):
            raw = self.ask(prompt)
            out, problems = check_output(raw, released, clarification_pending=pending_cl)
            calls.append({"prompt": prompt, "output": raw, "problems": problems})
            if not problems:
                return out
        raise OwnerFailed(f"no valid reply after {self.max_attempts} attempts: {problems}")

    def _trim(self, message: str, out: dict, calls: list[dict]) -> None:
        """Cut each answer that shares a rule, and each correction, down to what the question or the quoted words
        need, with a separate call that sees only the agent's message and the draft parts."""
        if self.trim is None:
            return
        parts = [("answer", a, a["question"]) for a in out["answers"] if a["items"] and not a["no_view"]]
        parts += [("correction", c, c.get("wrong", "")) for c in out["corrections"]]
        if not parts:
            return
        prompt = trim_prompt(message, [(kind, about, d["answer" if kind == "answer" else "text"]) for kind, d, about in parts])
        raw = self.trim(prompt)
        edited = {p.get("index"): p.get("text", "") for p in (raw or {}).get("parts", [])}
        changes = []
        for n, (kind, d, _about) in enumerate(parts, start=1):
            key = "answer" if kind == "answer" else "text"
            new = (edited.get(n) or "").strip()
            old = d[key]
            if new and not ITEM_ID.search(new) and words(new) <= words(old):
                d[key] = new
                if new != old:
                    changes.append({"part": n, "before": old, "after": new})
        calls.append({"prompt": prompt, "output": raw, "problems": [], "trim": changes})

    def respond(self, message: str, documents: Sequence[Document] = (), *, code_written: bool) -> OwnerReply:
        """The owner's response to the agent's stop. `code_written`: this change has changed a source file
        other than documentation or tests."""
        ch = self.change
        if ch is None:
            raise RuntimeError("no change in progress")
        shown = words(message) + sum(d.words for d in documents)
        self.words_this_change += shown
        r, pending = ch.redirect, self.redirect_state == "pending"
        change_of_mind = pending and r.kind == "change of mind"
        late_fires = pending and r.timing == "late" and code_written
        calls: list[dict] = []
        event = None
        if change_of_mind and late_fires:
            out = self._call(self._prompt(message, documents, "firing"), "firing", calls)
            event = "delivered"
        else:
            out = self._call(self._prompt(message, documents, self.redirect_state), self.redirect_state, calls)
            fires = pending and (late_fires or (r.timing == "early" and out["message_kind"] in FIRE_KINDS))
            if pending and r.kind == "clarification" and out["clarification_settled"]:
                event = "settled"
            elif fires and change_of_mind:
                # Answer again from the view the owner holds once they have changed their mind.
                out = self._call(self._prompt(message, documents, "firing"), "firing", calls)
                event = "delivered"
            elif fires:
                event = "delivered"
        if event:
            self.redirect_state = event
            self.redirect_point = f"{out['message_kind']}, code {'written' if code_written else 'not written'}"

        self._trim(message, out, calls)
        p = catch_probability(self.policy, self.words_this_change, self.half)
        kept, dropped = [], []
        for i, c in enumerate(out["corrections"]):
            draw = random.Random(f"{self.seed}|{ch.number}|{len(self.turns)}|{i}").random()
            (kept if draw < p else dropped).append({**c, "draw": round(draw, 6)})

        parts = ([r.text] if event == "delivered" else []) + [a["answer"] for a in out["answers"]] + [c["text"] for c in kept]
        kind = out["message_kind"]
        finished = kind == "completion" and not parts
        if finished:
            reply = ""
        elif kept or event == "delivered":
            reply = "\n\n".join(parts + ["Otherwise, go ahead."])
        elif parts:
            reply = "\n\n".join(parts + ["Go ahead."])
        elif kind == "stop":
            reply = "Please continue."
        else:
            reply = "That looks fine. Go ahead."

        shared = [{"item": i, "reason": "asked"} for a in out["answers"] for i in a["items"]]
        shared += [{"item": c["item"], "reason": "contradiction"} for c in kept if c["item"] != "none"]
        if event == "delivered":
            shared.append({"item": None, "reason": "redirect"})
        for a in out["answers"]:
            self.said_now.append(Said(ch.number, a["answer"], a["question"], tuple(a["items"])))
        for c in kept:
            self.said_now.append(Said(ch.number, c["text"], None, () if c["item"] == "none" else (c["item"],)))
        self.turns.append(Turn(message, tuple(d.name for d in documents), reply))
        for d in documents:
            if d.current is not None:
                self.seen[d.name] = d.current
        return OwnerReply(reply=reply, finished=finished, message_kind=kind, answers=out["answers"], kept=kept,
                          dropped=dropped, redirect_event=event, words_shown=shown,
                          words_this_change=self.words_this_change, catch_probability=p, shared=shared, calls=calls)

    def end_change(self) -> dict:
        """Close the change: what the owner asked for and said joins the record. Returns the change's
        redirect outcome."""
        ch = self.change
        if ch is None:
            raise RuntimeError("no change in progress")
        text = ch.owner_request
        if ch.redirect and self.redirect_state == "delivered":
            text += "\n\nLater in the change you said:\n\n" + ch.redirect.text
        if not ch.probe:
            self.requests.append((ch.number, text))
            self.record.extend(self.said_now)
        outcome = {"redirect": None if ch.redirect is None else
                   {"kind": ch.redirect.kind, "timing": ch.redirect.timing,
                    "outcome": "not delivered" if self.redirect_state == "pending" else self.redirect_state,
                    "point": self.redirect_point}}
        self.change = None
        return outcome


# ------------------------------------------------------------------------------------------- the leak judge

JUDGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["disclosures", "invented"],
    "properties": {
        "disclosures": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["item", "licensed", "why"],
                "properties": {"item": {"type": "string"}, "licensed": {"type": "boolean"}, "why": {"type": "string"}},
            },
        },
        "invented": {"type": "array", "items": {"type": "string"}},
    },
}


def judge_prompt(owner_prompt: str, reply: str, scripted: str | None = None, template: str | None = None) -> str:
    """The leak judge's prompt for one stop: everything the owner was given, and the reply that was sent.
    `scripted` is the redirect text the harness inserted, which the judge doesn't judge."""
    template = template if template is not None else JUDGE_TEMPLATE_PATH.read_text(encoding="utf-8")
    note = (f"The reply includes these scheduled words, which the owner was required to say. Don't judge them:\n\n{_blockquote(scripted)}"
            if scripted else "")
    return _fill(template, {"OWNER_PROMPT": owner_prompt.strip(), "REPLY": reply.strip() or "(empty: the owner accepted the change)",
                            "SCRIPTED": note})


TRIM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["parts"],
    "properties": {"parts": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["index", "text"],
        "properties": {"index": {"type": "integer"}, "text": {"type": "string"}}}}},
}


def trim_prompt(message: str, parts: Sequence[tuple[str, str, str]], template: str | None = None) -> str:
    """parts: (kind, what it is about, text), kind being "answer" (about: the question) or "correction" (about:
    the agent's words it corrects, or the missing thing it names)."""
    template = template if template is not None else TRIM_TEMPLATE_PATH.read_text(encoding="utf-8")
    blocks = []
    for n, (kind, about, text) in enumerate(parts, start=1):
        label = "The question it answers" if kind == "answer" else "The agent's words it corrects"
        blocks.append(f"Part {n} ({kind}). {label}: \"{about.strip()}\"\n\n{_blockquote(text)}")
    return _fill(template, {"MESSAGE": message.strip(), "PARTS": "\n\n".join(blocks)})


def trim_schema_json() -> str:
    return json.dumps(TRIM_SCHEMA, separators=(",", ":"))


def judge_schema_json() -> str:
    return json.dumps(JUDGE_SCHEMA, separators=(",", ":"))
