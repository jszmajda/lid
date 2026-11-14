"""The simulated owner: what it may know at each change, and the prompt it answers from.

Design: "The user simulator" and "Redirects" in the notebook's design.md. The owner
holds the seed's hidden oracle, released in stages:
- narrative sections up to the current change (headings and study notes removed);
- the items in force at the current change, each with how the owner shares it,
  without the graders' check sketches;
- recognized-on-sight responses, attached to their items.

Each call is a fresh, stateless session: the answer record carries what the owner
said before. The template is prompts/simulator.md.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "prompts" / "simulator.md"

POLICIES = {
    "diligent": (
        "You are a diligent owner. Read everything the agent shows you. When anything in it contradicts one of "
        "your rules that you can share (a stated rule, an askable rule whose topic the message addresses, or the "
        "trigger of a recognized-on-sight rule), say so and give the rule, then let the agent carry on. Approve "
        "only what you have no correction for. When the agent reports the change complete, review what it tells "
        "you the same way before accepting it."
    ),
    "bounded": (
        "You are a busy owner. You read the agent's message only as far as your attention lasts; if the message "
        "below is cut short, you didn't read the rest. Correct contradictions in what you did read, the way a "
        "careful owner would, and approve the rest."
    ),
    "rubber-stamp": (
        "You are an owner who trusts the agent and doesn't review its work. Approve every plan, design, step, or "
        "list of interpretations it shows you, and accept the change when it reports it complete, even if what it "
        "shows you contradicts your rules: you don't read it closely enough to notice. Answer only direct "
        "questions, as your rules allow."
    ),
}

ATTENTION_MARK = "[You stopped reading here.]"
NO_VIEW = "No preference, use your judgment."

OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["finished", "reply", "redirect_delivered", "redirect_preempted", "answers"],
    "properties": {
        "finished": {"type": "boolean"},
        "reply": {"type": "string"},
        "redirect_delivered": {"type": "boolean"},
        "redirect_preempted": {"type": "boolean"},
        "answers": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["question", "answer", "items"],
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                    "items": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
    },
}

_SHARE = {
    "stated": "Stated",
    "askable": "Askable",
    "recognized on sight": "Recognized on sight",
    "emerging": "Stated",  # the owner says it aloud at its change, then it is stated
    "realized on symptom": "Askable",  # known once its section is released
}


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


@dataclass(frozen=True)
class Redirect:
    timing: str  # "early" or "late"
    kind: str  # "change of mind" or "clarification"
    text: str


@dataclass(frozen=True)
class Change:
    number: int
    title: str
    request: str | None
    redirect: Redirect | None = None
    emerging: str | None = None
    guidance: str | None = None
    symptom: str | None = None
    diagnostic: str | None = None


@dataclass(frozen=True)
class Answer:
    change: int
    question: str
    answer: str
    items: list[str] = field(default_factory=list)


def _sections(text: str, level: str) -> list[tuple[str, str]]:
    """Split text into (heading, body) pairs at headings of exactly this level, e.g. '## '."""
    parts = re.split(rf"(?m)^{re.escape(level)}(?!#)", text)
    out = []
    for part in parts[1:]:
        heading, _, body = part.partition("\n")
        out.append((heading.strip(), body))
    return out


def _change_number(s: str) -> int | None:
    s = s.strip()
    if s == "Start":
        return 0
    m = re.search(r"[Cc]hange (\d+)", s)
    return int(m.group(1)) if m else None


def parse_oracle(text: str) -> Oracle:
    top = dict(_sections(text, "## "))
    narrative = {}
    for heading, body in _sections(top.get("Owner narrative", ""), "### "):
        n = 0 if "from the start" in heading else _change_number(heading)
        if n is None:
            raise ValueError(f"narrative section without a change: {heading!r}")
        narrative[n] = body.strip()
    responses = {}
    for m in re.finditer(r"\*\*(\w+-\d+)\*\*,[^\n]*\n\s*\*\*[“\"](.+?)[”\"]\*\*", top.get("Recognized-on-sight responses", "")):
        responses[m.group(1)] = m.group(2)
    items = []
    for line in top.get("Item table", "").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 6 or not re.fullmatch(r"\w+-\d+", cells[0]):
            continue
        iid, behavior, kind, force, retired = cells[:5]
        items.append(Item(iid, behavior, kind, _change_number(force), _change_number(retired), responses.get(iid)))
    return Oracle(narrative=narrative, items=items)


def released_narrative(oracle: Oracle, change: int) -> str:
    return "\n\n".join(body for n, body in sorted(oracle.narrative.items()) if n <= change)


def released_items(oracle: Oracle, change: int) -> list[Item]:
    return [
        i for i in oracle.items
        if i.kind != "Dropped" and i.in_force is not None and i.in_force <= change
        and (i.retired is None or i.retired > change)
    ]


def render_items(items: list[Item]) -> str:
    lines = []
    for i in items:
        line = f"- [{i.id}] ({i.share}) {i.behavior}"
        if i.response:
            line += f' Response: "{i.response}"'
        lines.append(line)
    return "\n".join(lines)


def _quote(body: str) -> str | None:
    paras, cur = [], []
    for line in body.splitlines():
        if line.startswith(">"):
            t = line[1:].strip()
            if t:
                cur.append(t)
            elif cur:
                paras.append(" ".join(cur))
                cur = []
    if cur:
        paras.append(" ".join(cur))
    return "\n\n".join(paras) if paras else None


def parse_change_script(text: str) -> dict[int, Change]:
    changes = {}
    for heading, body in _sections(text, "## "):
        m = re.match(r"Change (\d+)\s*[—-]\s*(.+)", heading)
        if not m:
            continue
        n, title = int(m.group(1)), m.group(2).strip()
        parts = {h: b for h, b in _sections(body, "### ")}
        request = next((_quote(b) for h, b in parts.items() if h.endswith("owner request") or h == "Owner request"), None)
        redirect = None
        for h, b in parts.items():
            rm = re.match(r"(Early|Late) redirect:\s*(.+)", h)
            if rm:
                redirect = Redirect(timing=rm.group(1).lower(), kind=rm.group(2).strip().lower(), text=_quote(b))
        diag = parts.get("Scheduled diagnostic")
        changes[n] = Change(
            number=n, title=title, request=request, redirect=redirect,
            emerging=_quote(parts.get("Emerging statement", "")),
            guidance=_quote(parts.get("Hidden owner guidance if asked", "")),
            symptom=_quote(parts.get("Owner symptom report", "")),
            diagnostic=diag.strip() if diag else None,
        )
    return changes


def attend(message: str, words: int | None) -> str:
    if words is None:
        return message
    toks = message.split()
    if len(toks) <= words:
        return message
    return " ".join(toks[:words]) + "\n\n" + ATTENTION_MARK


def _redirect_block(redirect: Redirect, code_written: bool) -> str:
    what = ("You have changed your mind about part of what you asked for." if redirect.kind == "change of mind"
            else "You want to make clear what you meant by part of what you asked for.")
    when = ("at the first plan, design, or spec the agent shows you in this change (a question on its own is not a "
            "plan); if the agent reports the change complete without showing you one, deliver it then"
            if redirect.timing == "early"
            else "in your first reply after code for this change exists (see below)")
    return (f"## A change of direction\n\n{what} Tell the agent this, in your own words but keeping its meaning:\n\n"
            f"> {redirect.text}\n\nDeliver it {when}. Until then, don't bring it up yourself. That doesn't stop you answering a question "
            f"or, if your policy has you review, correcting a contradiction on the same point; if the agent has already "
            f"settled what it says with you, in this message or before, don't deliver it, because it is no longer needed.\n\n"
            f"- Code for this change exists yet: {'yes' if code_written else 'no'}.")


def _record_block(record: list[Answer]) -> str:
    if not record:
        return "Nothing yet."
    return "\n".join(f"- Change {a.change}. Asked: {a.question} You answered: {a.answer}" for a in record)


def build_prompt(*, oracle: Oracle, change: Change, request: str, policy: str, message: str,
                 record: list[Answer], redirect_pending: bool, code_written: bool,
                 attention_words: int | None = None, template: str | None = None) -> str:
    """The owner's prompt for one reply. `request` is everything the owner has asked for in
    this change so far, including an emerging statement or a redirect already delivered."""
    if policy not in POLICIES:
        raise ValueError(f"policy must be one of {sorted(POLICIES)}, not {policy!r}")
    template = template if template is not None else TEMPLATE_PATH.read_text(encoding="utf-8")
    guidance = (f"If the agent asks why, this is your reasoning; share it only if asked:\n\n> {change.guidance}"
                if change.guidance else "")
    redirect = _redirect_block(change.redirect, code_written) if (redirect_pending and change.redirect) else ""
    fills = {
        "NARRATIVE": released_narrative(oracle, change.number),
        "ITEMS": render_items(released_items(oracle, change.number)),
        "POLICY": POLICIES[policy],
        "CHANGE": str(change.number),
        "REQUEST": request,
        "GUIDANCE": guidance,
        "REDIRECT": redirect,
        "RECORD": _record_block(record),
        "MESSAGE": attend(message, attention_words),
    }
    out = template
    for key, value in fills.items():
        out = out.replace("{" + key + "}", value)
    return re.sub(r"\n{3,}", "\n\n", out)


def schema_json() -> str:
    return json.dumps(OUTPUT_SCHEMA, separators=(",", ":"))
