"""The simulated owner: what it may know at each change, what it is shown, and how its reply is made.

Design: "The user simulator" and "Redirects" in the notebook's design.md.

- **What the owner knows.** The seed's hidden oracle, released in stages: the narrative sections up to the
  current change, and the items in force, without the graders' check sketches. A pending change of mind is
  withheld (its narrative section and the items it introduces) until it is delivered.
- **What the owner is shown.** One rule for every arm: the agent's final message, the plan from plan mode if
  there is one, and the changed text of every prose file the message names.
- **One model call per stop, under every policy.** The stop's new text is split into numbered passages. The model
  classifies the agent's message, answers its targeted questions, lists the askable items each broad question
  covers, lists every contradiction with the passage it is in, and reports which passages touch each askable item
  the owner hasn't disclosed, and how.
- **Attention and recall are the harness's** ("Attention and recall" in design.md). Seeded draws, keyed on the
  replicate, the item, the kind of event, and the scope, decide which contradictions the policy keeps and which
  unsaid items a passage or a broad question brings back. A recalled item's line comes verbatim from the seed's
  owner-items.json, added after the trim. Targeted answers are always kept.
- **Redirect timing and words are the harness's.** An early redirect fires at the first approval request or
  completion report, a late one at the first stop after code exists, and the scripted words go in verbatim.
  The model only judges whether a pending clarification has already been settled.
- The harness puts the reply together from the parts, so a correction can't ask for another round.

The template is prompts/simulator.md; the leak judge's is prompts/leak-judge.md.
"""

from __future__ import annotations

import collections
import copy
import difflib
import json
import math
import random
import re
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"
TEMPLATE_PATH = PROMPTS / "simulator.md"
JUDGE_TEMPLATE_PATH = PROMPTS / "leak-judge.md"
TRIM_TEMPLATE_PATH = PROMPTS / "owner-trim.md"
TOUCH_TEMPLATE_PATH = PROMPTS / "owner-touches.md"
COMPLETION_TEMPLATE_PATH = PROMPTS / "owner-completion.md"

POLICIES = ("diligent", "bounded", "rubber-stamp")
NO_VIEW = "No preference, use your judgment."
SHOW_ME = "Show me what you have in mind and I'll tell you if it's wrong."
NOTHING_ELSE = "Nothing else comes to mind."  # a broad question's answer when no draw brings anything back
KINDS = ("completion", "approval", "questions", "stop")
FIRE_KINDS = ("approval", "completion")  # what an early redirect waits for
BREADTHS = ("targeted", "broad")
LEVELS = ("adjacent", "direct", "says")  # how a passage touches an unsaid askable item; "says" draws nothing
EVENTS = ("recall", "contradiction", "broad")  # the kinds of event a uniform is keyed on
# The pilot's placeholder: the bounded owner caught a contradiction with probability 1 / (1 + w / HALF), w being every
# word shown in the change through the end of the stop. OwnerModel.pilot() reproduces it; catch_probability keeps
# the original for reference.
HALF_ATTENTION_WORDS = 1500
PROSE_SUFFIXES = (".md", ".markdown", ".txt", ".rst", ".adoc")
ALL = "all"  # every item in force is in play

STUDY_WORDS = re.compile(r"\b(the owner|scripted|redirect|simulator|the study|graded|grader)\b", re.I)
PASSAGE_NUMBER = re.compile(r"\[P\d+\]")

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
                "required": ["question", "breadth", "answer", "items", "no_view", "in_scope"],
                "properties": {
                    "question": {"type": "string", "description": (
                        "The agent's own words for the question, quoted exactly: a short span copied from its message, "
                        "such as \"Is that fine?\". It labels your answer when you answer more than one question.")},
                    "breadth": {"type": "string", "enum": list(BREADTHS)},
                    "answer": {"type": "string"},
                    "items": {"type": "array", "items": {"type": "string"}},
                    "no_view": {"type": "boolean"},
                    "in_scope": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "corrections": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["item", "passage", "wrong", "text"],
                "properties": {"item": {"type": "string"}, "passage": {"type": "integer", "minimum": 0},
                               "wrong": {"type": "string"}, "text": {"type": "string"}},
            },
        },
        "clarification_settled": {"type": "boolean"},
    },
}

# The touch call's output: which numbered passages touch each askable item the owner hasn't disclosed, and how.
TOUCH_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["touches"],
    "properties": {"touches": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["item", "passage", "level"],
        "properties": {"item": {"type": "string"}, "passage": {"type": "integer", "minimum": 1},
                       "level": {"type": "string", "enum": list(LEVELS)}}}}},
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


FORK_SCOPE = "the start and this change only"  # what a fork's owner holds, as its record says


def released_narrative(oracle: Oracle, change: int, *, withhold_section: int | None = None,
                       only_change: bool = False) -> str:
    """The owner's own words by this change. only_change: a fork's owner, for whom no other change has happened, so
    the start's section and this change's only."""
    return "\n\n".join(body for n, body in sorted(oracle.narrative.items())
                       if (n in (0, change) if only_change else n <= change) and n != withhold_section)


def released_items(oracle: Oracle, change: int, *, withhold: Iterable[str] = (), only_change: bool = False) -> list[Item]:
    """The items the owner holds at this change. only_change: a fork's owner, for whom no other change has happened:
    the start's items and this change's own, retired only by this change."""
    held = set(withhold)
    if only_change:
        return [i for i in oracle.items
                if i.kind != "Dropped" and i.in_force in (0, change) and i.retired != change and i.id not in held]
    return [
        i for i in oracle.items
        if i.kind != "Dropped" and i.in_force is not None and i.in_force <= change
        and (i.retired is None or i.retired > change) and i.id not in held
    ]


def id_pattern(ids: Iterable[str]) -> re.Pattern:
    """A pattern for the oracle's own item identifiers: its prefixes followed by a number, so text such as "UTC-5"
    or "ISO-8601" isn't taken for one. With no identifiers it matches nothing."""
    prefixes = sorted({i.rsplit("-", 1)[0] for i in ids}, key=lambda p: (-len(p), p))
    if not prefixes:
        return re.compile(r"(?!)")
    return re.compile(r"\b(?:" + "|".join(re.escape(p) for p in prefixes) + r")-\d+\b")


def owner_text(behavior: str, ids: re.Pattern) -> str:
    """An item's behavior as the owner holds it. Sentences that cite another item (matching `ids`, the oracle's
    identifiers) are graders' notes, and the owner doesn't number changes."""
    sentences = re.split(r"(?<=[.!?])\s+", behavior.strip())
    kept = " ".join(s for s in sentences if not ids.search(s))
    return re.sub(r"\s+(?:from|after) change \d+(?: onward)?", "", kept)  # the owner doesn't number changes


def render_items(items: list[Item], in_play: set[str] | str, ids: re.Pattern | None = None) -> str:
    ids = ids if ids is not None else id_pattern(i.id for i in items)
    lines = []
    for i in items:
        label = i.share
        if label == "Askable" and (in_play == ALL or i.id in in_play):
            label += "; in play for this change"
        line = f"- [{i.id}] ({label}) {owner_text(i.behavior, ids)}"
        if i.response:
            line += (" You wouldn't say this unprompted. When the agent proposes the opposite, or offers it as one choice "
                     f'in a question, object: "{i.response}" When it asks an open question about this without saying what '
                     f'it has in mind, answer only: "{SHOW_ME}"')
        lines.append(line)
    return "\n".join(lines)


# ------------------------------------------------------------------------- what the owner may recall, and how well

TIERS = {"low": -1, "medium": 0, "high": 1}  # salience tiers, as the recall logit's tier term


@dataclass(frozen=True)
class OwnerItem:
    """An askable item's salience tier and recall line: the one sentence, in the owner's voice, that the harness
    adds to a reply when the item is recalled. Written with the oracle and frozen with it."""
    tier: str
    recall: str


def recall_eligible(oracle: Oracle) -> list[Item]:
    """Items recall can bring back: askable ones, including those realized on a symptom (askable once released).
    Stated items (and their unsaid details) and items recognized on sight are never recalled."""
    return [i for i in oracle.items if i.kind != "Dropped" and i.in_force is not None and i.share == "Askable"]


def complete_owner_items(oracle: Oracle, items: Mapping[str, OwnerItem],
                         default: OwnerItem | None = None) -> dict[str, OwnerItem]:
    """Every recall-eligible item's entry. A missing one is an error unless the caller passes a default."""
    eligible = [i.id for i in recall_eligible(oracle)]
    for iid in items:
        if iid not in eligible:
            raise ValueError(f"owner items: {iid} isn't an askable item of the oracle, so it has no recall")
    missing = [i for i in eligible if i not in items]
    if missing and default is None:
        raise ValueError(f"owner items: no tier and recall line for {', '.join(missing)}")
    return {i: items.get(i, default) for i in eligible}


def parse_owner_items(data: Mapping, oracle: Oracle, *, default: OwnerItem | None = None) -> dict[str, OwnerItem]:
    """owner-items.json: {"<item>": {"tier": "low" | "medium" | "high", "recall": "<one sentence>"}, ...}, one entry
    for every askable item. The entries may instead sit under an "items" key, beside a record of how the tiers were
    rated; that record is not read here."""
    if "items" in data:
        data = data["items"]
        if not isinstance(data, Mapping):
            raise ValueError("owner items: \"items\" must map each askable item to its tier and recall line")
    known = oracle.ids()
    out: dict[str, OwnerItem] = {}
    for iid, entry in data.items():
        if iid not in known:
            raise ValueError(f"owner items: {iid} isn't an item of the oracle")
        if not isinstance(entry, Mapping):
            raise ValueError(f"owner items: {iid}'s entry isn't an object")
        extra = sorted(set(entry) - {"tier", "recall"})
        if extra:
            raise ValueError(f"owner items: {iid} has unexpected keys {extra}")
        tier, line = entry.get("tier"), entry.get("recall")
        if tier not in TIERS:
            raise ValueError(f"owner items: {iid}'s tier must be low, medium, or high, not {tier!r}")
        if not isinstance(line, str) or not line.strip():
            raise ValueError(f"owner items: {iid}'s recall line is empty")
        if id_pattern(known).search(line):
            raise ValueError(f"owner items: {iid}'s recall line mentions an identifier")
        out[iid] = OwnerItem(tier, line.strip())
    return complete_owner_items(oracle, out, default)


def load_owner_items(path: Path | str, oracle: Oracle, *, default: OwnerItem | None = None) -> dict[str, OwnerItem]:
    return parse_owner_items(json.loads(Path(path).read_text(encoding="utf-8")), oracle, default=default)


SCOPES = ("stop", "change", "trajectory")  # how long one uniform lasts for an item and kind of event
COUNTINGS = ("stop", "change", "pilot")  # how w is counted; see OwnerModel
BROAD_UNIFORMS = ("broad", "recall")  # which uniform a broad question's draw uses; see OwnerModel


@dataclass(frozen=True)
class OwnerModel:
    """The constants of the owner's attention and recall, at the design's central values. Every field is swept or
    is a sensitivity case; a run records all of them.

    Attention: a = m · [floor + (1 − floor) / (1 + w / half_words)], with m = 1 − drag · (1 − e^(−t / drag_minutes))
    and t the minutes of new reading in this change before the passage, at words_per_minute. Recall:
    logit r = recall_intercept + tier_spacing · tier + direct_weight · direct − fan_weight · ln n.

    counting: how w is counted. "stop": new words before the passage in this stop. "change": new words before the
    passage in this change. "pilot": every word shown in the change through the end of the stop, one value per stop,
    as the pilot's placeholder counted it.
    scope: a uniform lasts one stop, one change, or the whole trajectory.
    dormancy: multiply adjacent-touch odds by dormancy_odds after the first build; dormancy_on_broad says whether a
    broad question's draw, made at the adjacent rate, is lowered too.
    broad_uniform: "broad" gives a broad question's draw its own uniform (design.md keys the uniform on "a broad
    question" as a kind of event); "recall" shares the item's review-recall uniform for the scope.
    """
    floor: float = 0.18  # f
    half_words: float = 500  # k
    drag: float = 0.15
    drag_minutes: float = 22
    words_per_minute: float = 238
    catch: float = 0.8  # q
    recall_intercept: float = -1.1
    tier_spacing: float = 1.1
    direct_weight: float = 2.2
    fan_weight: float = 1.0  # λ
    dormancy: bool = False
    dormancy_odds: float = 0.6
    dormancy_on_broad: bool = True
    scope: str = "change"
    counting: str = "stop"
    broad_uniform: str = "broad"
    # Label each of several answers with the agent's quoted question. Off by default: in the leak gate the owner
    # sometimes quoted one question and answered another, which turns "Yes." into the opposite of what it meant.
    label_answers: bool = False

    def __post_init__(self):
        problems = []
        for name, allowed in (("scope", SCOPES), ("counting", COUNTINGS), ("broad_uniform", BROAD_UNIFORMS)):
            if getattr(self, name) not in allowed:
                problems.append(f"{name} must be one of {allowed}, not {getattr(self, name)!r}")
        for name in ("floor", "drag", "catch"):
            if not 0 <= getattr(self, name) <= 1:
                problems.append(f"{name} must be between 0 and 1")
        for name in ("half_words", "drag_minutes", "words_per_minute", "dormancy_odds"):
            if not getattr(self, name) > 0:
                problems.append(f"{name} must be positive")
        if self.fan_weight < 0:
            problems.append("fan_weight can't be negative")
        if problems:
            raise ValueError("owner model: " + "; ".join(problems))

    @classmethod
    def from_config(cls, config: Mapping | None) -> "OwnerModel":
        """A preset ("central", the default, or "pilot") with any fields overridden."""
        cfg = dict(config or {})
        preset = cfg.pop("preset", "central")
        if preset not in OWNER_MODEL_PRESETS:
            raise ValueError(f"owner model: unknown preset {preset!r}")
        unknown = sorted(set(cfg) - {f.name for f in fields(cls)})
        if unknown:
            raise ValueError(f"owner model: unknown settings {unknown}")
        return cls(**{**OWNER_MODEL_PRESETS[preset], **cfg})

    @classmethod
    def pilot(cls) -> "OwnerModel":
        return cls.from_config({"preset": "pilot"})


# The pilot's placeholder curve, as one further case: no floor, every read contradiction caught, k = 1,500, no drag,
# and w as every word shown in the change through the end of the stop.
OWNER_MODEL_PRESETS = {"central": {}, "pilot": {"floor": 0, "catch": 1, "half_words": 1500, "drag": 0, "counting": "pilot"}}


def attention(model: OwnerModel, *, w: float, read_before: float) -> float:
    """The probability a passage is read: w new words come before it (as model.counting counts them), and
    read_before new words were shown earlier in this change (for the session drag)."""
    m = 1 - model.drag * (1 - math.exp(-(read_before / model.words_per_minute) / model.drag_minutes))
    return m * (model.floor + (1 - model.floor) / (1 + w / model.half_words))


def recall_rate(model: OwnerModel, tier: str, *, direct: bool, n: int = 1, after_first_build: bool = False) -> float:
    """The probability that a passage the owner reads brings back an unsaid askable item: n unsaid items touch the
    same passage."""
    if tier not in TIERS:
        raise ValueError(f"unknown tier {tier!r}")
    if n < 1:
        raise ValueError("a touching passage touches at least its own item")
    logit = (model.recall_intercept + model.tier_spacing * TIERS[tier] + (model.direct_weight if direct else 0.0)
             - model.fan_weight * math.log(n))
    if model.dormancy and after_first_build and not direct:
        logit += math.log(model.dormancy_odds)
    return 1.0 / (1.0 + math.exp(-logit))


def uniform(replicate: str, item: str, event: str, scope_key: str) -> float:
    """The seeded uniform for one item and kind of event within one scope. Keyed on nothing else, so trajectories
    in the same replicate (other arms, other policies, a redirect's paired run) share it."""
    if event not in EVENTS:
        raise ValueError(f"unknown event {event!r}")
    return random.Random(f"{replicate}|{item}|{event}|{scope_key}").random()


def scope_key(scope: str, change: "Change", stop: int) -> str:
    """The scope a uniform lasts for. `stop` is the stop's place in its change, needed only to tell one stop from
    the next when each stop draws afresh."""
    unit = f"{'probe' if change.probe else 'change'}-{change.number}"
    if scope == "change":
        return unit
    if scope == "stop":
        return f"{unit}/stop-{stop}"
    if scope == "trajectory":
        return "trajectory"
    raise ValueError(f"unknown scope {scope!r}")


def contradiction_key(correction: dict) -> str:
    """What a contradiction's uniform is keyed on: its item; for one tied to no item, its quoted words (case and
    spacing aside); and for something left out that is tied to no item, a constant, since the words naming what is
    missing change from stop to stop."""
    if correction.get("item") != "none":
        return correction["item"]
    if correction.get("passage") == 0:
        return "none:missing"
    return "none:" + " ".join(str(correction.get("wrong", "")).lower().split())


# ---------------------------------------------------------------------------------------- the change script


@dataclass(frozen=True)
class Redirect:
    timing: str  # "early" or "late"
    kind: str  # "change of mind" or "clarification"
    text: str
    introduces: tuple[str, ...] = ()  # items a change of mind brings in, withheld until it is delivered
    settles: tuple[str, ...] = ()  # items a clarification's words share: disclosed once it is delivered or settled


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
    planted_bug: str | None = None  # a patch applied to the change's starting snapshot, relative to the change script

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
            settles_field = _field(b, "Redirect settles")
            if settles_field and kind != "clarification":
                raise ValueError(f"change {n}: only a clarification settles items")
            settles = parse_ids(settles_field) if settles_field else ()
            if settles == ALL:
                raise ValueError(f"change {n}: a clarification can't settle every item")
            redirect = Redirect(timing=rm.group(1).lower(), kind=kind, text=_quote(b) or "", introduces=ids, settles=settles)
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
            planted_bug=(_field(body, "Planted bug") or "").strip("` ") or None,
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
    diff: tuple[str, ...] | None = None  # the unified diff's lines when shown as changes; () when unchanged


DIFF_HEADER = "Changes since you last read it (lines starting with - were removed, + were added):"
UNCHANGED = "(Unchanged since you last read it.)"


def plan_document(plan: str) -> Document:
    return Document("The agent's plan", plan, words(plan))


def view_document(name: str, current: str, last_shown: str | None) -> Document:
    if last_shown is None:
        return Document(name, current, words(current), current)
    if last_shown == current:
        return Document(name, UNCHANGED, 0, current, ())
    diff = list(difflib.unified_diff(last_shown.splitlines(), current.splitlines(), lineterm="", n=2))[2:]
    added = sum(words(line[1:]) for line in diff if line.startswith("+"))
    return Document(name, DIFF_HEADER + "\n\n" + "\n".join(diff), added, current, tuple(diff))


# --------------------------------------------------------------------------------------------------- passages

MESSAGE_SOURCE = "The agent's message"


@dataclass(frozen=True)
class Passage:
    """One numbered unit of a stop's new text: a paragraph, list item, table row, heading, or fenced block."""
    number: int  # from 1, in the order shown: the message, the plan, then each named prose file
    source: str  # MESSAGE_SOURCE or the document's name
    text: str  # for a re-read file, the added lines without their '+'
    words: int
    offset: int  # new words in this stop before the passage's first word


@dataclass(frozen=True)
class StopText:
    passages: tuple[Passage, ...]
    message: str  # the message as the owner sees it, each passage marked with its number
    documents: tuple[tuple[str, str], ...]  # (name, text as shown, passages marked)


_HEADING = re.compile(r"^ {0,3}#{1,6}(?:\s|$)")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d{1,9}[.)])\s")
_TABLE_ROW = re.compile(r"^\s*\|")
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
_CONTENT = re.compile(r"[^\W_]")  # a letter or a digit
_TABLE_DIVIDER = re.compile(r"^\s*\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)+\|?\s*$")  # "--- | ---", "|:--|--:|"


def _table_rows(lines: Sequence[str]) -> set[int]:
    """Lines of tables written without leading pipes: a header row with a pipe, the divider under it, and the
    non-blank lines with a pipe that follow."""
    rows: set[int] = set()
    for i, line in enumerate(lines):
        if i == 0 or not _TABLE_DIVIDER.match(line) or "|" not in lines[i - 1] or not lines[i - 1].strip():
            continue
        rows.update((i - 1, i))
        j = i + 1
        while j < len(lines) and lines[j].strip() and "|" in lines[j]:
            rows.add(j)
            j += 1
    return rows


def _blocks(lines: Sequence[str]) -> list[list[int]]:
    """Group line indices into passages. A heading or table row is one line; a list item runs until the next item,
    block, or blank line; a paragraph until a blank line or another block; a fenced block until its closing fence,
    or the end of its document if it has none. A block without a letter or digit (a rule, a table's divider) joins
    the passage before it."""
    blocks: list[list[int]] = []
    cur: list[int] | None = None
    fence: str | None = None
    table = _table_rows(lines)
    for i, line in enumerate(lines):
        if fence is not None:
            cur.append(i)
            if line.strip().startswith(fence):
                fence, cur = None, None
            continue
        if not line.strip():
            cur = None
            continue
        f = _FENCE.match(line)
        if f:
            fence, cur = f.group(1), [i]
            blocks.append(cur)
        elif _HEADING.match(line) or _TABLE_ROW.match(line) or i in table:
            blocks.append([i])
            cur = None
        elif _LIST_ITEM.match(line) or cur is None:
            cur = [i]
            blocks.append(cur)
        else:
            cur.append(i)
    merged: list[list[int]] = []
    for b in blocks:
        if merged and not any(_CONTENT.search(lines[i]) for i in b):
            merged[-1] = merged[-1] + b
        else:
            merged.append(b)
    if len(merged) > 1 and not any(_CONTENT.search(lines[i]) for i in merged[0]):
        merged[:2] = [merged[0] + merged[1]]
    return merged


def _mark(n: int) -> str:
    return f"[P{n}] "


def split_stop(message: str, documents: Sequence[Document] = ()) -> StopText:
    """Number the stop's new text in the order the owner is shown it: the agent's message, then each document (the
    plan first, then each named prose file). A document read before contributes only its added lines."""
    passages: list[Passage] = []
    offset = 0

    def number(lines: Sequence[str], source: str) -> dict[int, int]:
        nonlocal offset
        starts = {}
        for b in _blocks(lines):
            n = len(passages) + 1
            wc = sum(words(lines[i]) for i in b)
            passages.append(Passage(n, source, "\n".join(lines[i] for i in b), wc, offset))
            offset += wc
            starts[b[0]] = n
        return starts

    def marked(lines: Sequence[str], starts: dict[int, int]) -> str:
        return "\n".join(_mark(starts[i]) + line if i in starts else line for i, line in enumerate(lines))

    mlines = message.strip().splitlines()
    shown_message = marked(mlines, number(mlines, MESSAGE_SOURCE))
    shown_docs = []
    for d in documents:
        if d.diff is None:
            lines = d.shown.strip().splitlines()
            shown_docs.append((d.name, marked(lines, number(lines, d.name))))
        elif not d.diff:
            shown_docs.append((d.name, d.shown.strip()))
        else:
            out = list(d.diff)
            i = 0
            while i < len(d.diff):
                if not d.diff[i].startswith("+"):
                    i += 1
                    continue
                j = i
                while j < len(d.diff) and d.diff[j].startswith("+"):
                    j += 1
                run = [line[1:] for line in d.diff[i:j]]
                for k, n in number(run, d.name).items():
                    out[i + k] = "+" + _mark(n) + run[k]
                i = j
            shown_docs.append((d.name, DIFF_HEADER + "\n\n" + "\n".join(out)))
    return StopText(tuple(passages), shown_message, tuple(shown_docs))


def strip_passage_marks(text: str) -> str:
    """The text without the passage numbers the harness put at the start of lines."""
    return re.sub(r"(?m)^(\+?)\[P\d+\] ", r"\1", text)


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
                 template: str | None = None, only_change: bool = False) -> str:
    """The owner's prompt for one stop. The message and documents are shown with their passages numbered.
    only_change: a fork's owner, who holds the start and this change only.

    redirect_state: None (no redirect), "pending", "firing" (a change of mind being delivered with this reply),
    "delivered", or "settled".
    """
    template = template if template is not None else TEMPLATE_PATH.read_text(encoding="utf-8")
    r = change.redirect
    if (r is None) != (redirect_state is None):
        raise ValueError("redirect_state must be given exactly when the change has a redirect")
    withholding = r is not None and r.kind == "change of mind" and redirect_state == "pending"
    items = released_items(oracle, change.number, withhold=r.introduces if withholding else (), only_change=only_change)

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
    stop = split_stop(message, documents)
    docs = ""
    if documents:
        docs = "## Documents the agent asked you to read\n\n" + "\n\n".join(
            f'<document name="{name}">\n{text}\n</document>' for name, text in stop.documents)

    return _fill(template, {
        "NARRATIVE": released_narrative(oracle, change.number, withhold_section=change.number if withholding else None,
                                        only_change=only_change),
        "ITEMS": render_items(items, change.in_play, ids=id_pattern(oracle.ids())),
        "REQUEST": request,
        "GUIDANCE": guidance,
        "CHANGE_OF_MIND": change_of_mind,
        "CLARIFICATION": clarification,
        "BRIEF_SECTION": brief_section,
        "EARLIER_SECTION": earlier,
        "RECORD_SECTION": rec,
        "EXCHANGE_SECTION": exchange,
        "MESSAGE": stop.message or "(The agent's message was empty.)",
        "DOCUMENTS_SECTION": docs,
    })


def schema_json() -> str:
    return json.dumps(OUTPUT_SCHEMA, separators=(",", ":"))


def touch_schema_json() -> str:
    return json.dumps(TOUCH_SCHEMA, separators=(",", ":"))


# A completion that announces work: the main call can read "Phase 6 is next. I'll add the command…" as a completion
# report. A separate small call, on the message alone, says whether it reports the change done or announces work
# still to do; work to do makes the stop an approval request, answered with a go-ahead.
COMPLETION_VERDICTS = ("done", "work to do")
COMPLETION_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["verdict", "quote"],
    "properties": {"verdict": {"type": "string", "enum": list(COMPLETION_VERDICTS)}, "quote": {"type": "string"}},
}


def completion_schema_json() -> str:
    return json.dumps(COMPLETION_SCHEMA, separators=(",", ":"))


def completion_check_prompt(message: str, template: str | None = None) -> str:
    text = template if template is not None else COMPLETION_TEMPLATE_PATH.read_text(encoding="utf-8")
    return _fill(text, {"MESSAGE": message.strip()})


def check_completion(raw, message: str) -> tuple[str | None, list[str]]:
    """The check's verdict, and its problems: an unknown verdict, or a quote that isn't the message's own words."""
    if not isinstance(raw, dict) or raw.get("verdict") not in COMPLETION_VERDICTS:
        return None, [f"verdict {raw.get('verdict') if isinstance(raw, dict) else raw!r}"]
    if not quoted_in(raw.get("quote") or "", message):
        return None, [f"the quote isn't the message's own words: {raw.get('quote')!r}"]
    return raw["verdict"], []


def _withholding(change: Change, redirect_state: str | None) -> bool:
    r = change.redirect
    return r is not None and r.kind == "change of mind" and redirect_state == "pending"


def touch_items(oracle: Oracle, change: Change, *, disclosed: Iterable[str] = (), redirect_state: str | None = None,
                only_change: bool = False) -> list[str]:
    """The items the touch call asks about: askable items the owner holds at this state and hasn't disclosed."""
    r, told = change.redirect, set(disclosed)
    held = released_items(oracle, change.number, withhold=r.introduces if _withholding(change, redirect_state) else (),
                          only_change=only_change)
    return [i.id for i in held if i.share == "Askable" and i.id not in told]


def touch_prompt(*, oracle: Oracle, change: Change, message: str, documents: Sequence[Document] = (),
                 disclosed: Iterable[str] = (), redirect_state: str | None = None, template: str | None = None,
                 only_change: bool = False) -> str:
    """The touch call's prompt: the owner's own words (for meaning), the askable rules it hasn't told the agent, and
    the stop's numbered text. It asks for nothing but touches."""
    template = template if template is not None else TOUCH_TEMPLATE_PATH.read_text(encoding="utf-8")
    ids = id_pattern(oracle.ids())
    wanted = set(touch_items(oracle, change, disclosed=disclosed, redirect_state=redirect_state, only_change=only_change))
    rules = "\n".join(f"- [{i.id}] {owner_text(i.behavior, ids)}" for i in oracle.items if i.id in wanted)
    stop = split_stop(message, documents)
    docs = ""
    if documents:
        docs = "Documents the agent asked you to read:\n\n" + "\n\n".join(
            f'<document name="{name}">\n{text}\n</document>' for name, text in stop.documents)
    return _fill(template, {
        "NARRATIVE": released_narrative(oracle, change.number,
                                        withhold_section=change.number if _withholding(change, redirect_state) else None,
                                        only_change=only_change),
        "ITEMS": rules,
        "MESSAGE": stop.message or "(The agent's message was empty.)",
        "DOCUMENTS_SECTION": docs,
    })


# ------------------------------------------------------------------------------------------ checking output


def _passage_number(n) -> bool:
    return isinstance(n, int) and not isinstance(n, bool)


LEVEL_STRENGTH = {"says": 0, "adjacent": 1, "direct": 2}  # two levels for one item and passage keep the weaker


_QUOTE_MARKS = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})


def _label_text(question: str) -> str:
    """A question as it labels an answer: without passage numbers or the quote marks around it, spaced simply."""
    q = " ".join(re.sub(r"\[P\d+\]\s*", "", question).split())
    return q.strip("\"'\u2018\u2019\u201c\u201d").strip()


def quoted_in(question: str, message: str) -> bool:
    """Whether the question is the agent's own words: a non-empty span of its message, ignoring passage numbers,
    spacing, and the kind of quote marks."""
    q = _label_text(question).translate(_QUOTE_MARKS)
    text = " ".join(strip_passage_marks(message).translate(_QUOTE_MARKS).split())
    return bool(q) and q in text


def label_answers(answers: Sequence[dict], message: str) -> list[str]:
    """Set each answer's label: its question when that is the agent's own words, else none, so a paraphrase (which
    can name the alternative the agent didn't propose) never labels an answer. Returns a repair for each dropped."""
    repairs = []
    for a in answers:
        if quoted_in(a.get("question", ""), message):
            a["label"] = _label_text(a["question"])
        else:
            a["label"] = None
            repairs.append(f"the question {a.get('question', '')!r} isn't the agent's own words, so its answer is shown "
                           "without a label")
    return repairs


def check_output(out: dict, items: Sequence[Item], *, clarification_pending: bool, passages: int = 0,
                 in_play: set[str] | str = ALL, requested: Iterable[str] = (),
                 ids: re.Pattern | None = None, message: str | None = None) -> tuple[dict, list[str], list[str]]:
    """Normalize the model's output. Returns (normalized, problems, repairs).

    Problems are structural faults, which a fresh call may fix: unknown kinds, passage numbers that don't exist,
    identifiers or passage numbers in the owner's words, an empty correction, a no-view answer that shares something.
    Repairs are slips with one right answer, made here and logged instead of retried: a broad question's scope naming
    an item that isn't askable or in play; a correction for something left out that cites an item this change's
    request didn't ask for; a correction of an item a targeted answer in the same reply shares (the answer gives the
    decision, so it isn't said twice); and, when `message` is given, a question that isn't the agent's own words,
    whose answer then goes without a label. Touches come from their own call; see check_touches.

    items: the items the owner holds at this call; passages: how many numbered passages the stop has; in_play: the
    change's items in play, which bound a broad question's scope; requested: the items this change's own request asks
    for (at the first build, the brief's); ids: the oracle's identifier pattern."""
    problems, repairs = [], []
    out = copy.deepcopy(out)
    released = {i.id: i for i in items}
    ids = ids if ids is not None else id_pattern(released)
    askable = {i for i, it in released.items() if it.share == "Askable"}
    may_be_missing = set(requested) & set(released)
    if out.get("message_kind") not in KINDS:
        problems.append(f"message_kind {out.get('message_kind')!r}")
    for a in out.get("answers", []):
        breadth = a.get("breadth")
        if breadth not in BREADTHS:
            problems.append(f"an answer's breadth is {breadth!r}")
            continue
        if breadth == "broad":
            # The owner doesn't answer a broad question from its rules: recall draws make the answer, so whatever
            # the model wrote for it is discarded.
            a["answer"], a["items"], a["no_view"] = "", [], False
            scope: list[str] = []
            for i in a.get("in_scope") or []:
                if i in scope:
                    continue
                if i not in askable or (in_play != ALL and i not in in_play):
                    repairs.append(f"dropped {i} from a broad question's scope: it isn't an Askable rule in play for this change")
                    continue
                scope.append(i)
            a["in_scope"] = scope
            continue
        a["in_scope"] = []
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
        if ids.search(a.get("answer", "")):
            problems.append("an answer mentions a rule identifier")
        if PASSAGE_NUMBER.search(a.get("answer", "")):
            problems.append("an answer mentions a passage number")
    corrections = []
    for c in out.get("corrections", []):
        item, n = c.get("item"), c.get("passage")
        if n == 0 and _passage_number(n) and item != "none" and item not in may_be_missing:
            # Only part of this change's own request can be pointed out as missing: an earlier stated item the agent
            # leaves out is its own to keep, and an askable one left out is a touch at most.
            repairs.append(f"dropped a correction for something left out that cites {item}: only what this change's "
                           "request asked for can be pointed out as missing")
            continue
        if item != "none" and item not in released:
            problems.append(f"correction cites {item}, which the owner doesn't hold")
        if not _passage_number(n):
            problems.append(f"a correction has no passage number: {n!r}")
        elif not 0 <= n <= passages:
            problems.append(f"a correction cites passage {n}, which doesn't exist")
        if ids.search(c.get("text", "")):
            problems.append("a correction mentions a rule identifier")
        if PASSAGE_NUMBER.search(c.get("text", "")):
            problems.append("a correction mentions a passage number")
        if not c.get("text", "").strip():
            problems.append("an empty correction")
        corrections.append(c)
    answered = {i for a in out.get("answers", []) if a.get("breadth") == "targeted" and not a.get("no_view")
                for i in a.get("items", [])}
    for c in corrections:
        if c.get("item") in answered:
            repairs.append(f"dropped the correction of {c['item']}: an answer in the same reply gives that decision")
    out["corrections"] = [c for c in corrections if c.get("item") not in answered]
    out.pop("touches", None)  # touches come from their own call
    if message is not None:
        repairs += label_answers([a for a in out.get("answers", []) if a.get("breadth") in BREADTHS], message)
    if out.get("message_kind") == "questions" and not out.get("answers"):
        problems.append("message_kind is questions but nothing is answered")
    if not clarification_pending:
        out["clarification_settled"] = False
    return out, problems, repairs


def contradicted_in(corrections: Iterable[dict]) -> set[tuple[str, int]]:
    """(item, passage) for each contradiction the main call reported in a numbered passage."""
    return {(c.get("item"), c.get("passage")) for c in corrections if _passage_number(c.get("passage")) and c.get("passage")}


def check_touches(out: dict, eligible: Iterable[str], *, passages: int,
                  contradicted: set[tuple[str, int]] = frozenset()) -> tuple[list[dict], list[str], list[str]]:
    """Normalize the touch call's output. Returns (touches, problems, repairs).

    eligible: the items the call was asked about (askable, held, not disclosed). Problems, retried: passage numbers
    that don't exist and unknown levels. Repairs, logged: a touch on any other item, a touch where the main call
    reported a contradiction of the same item in the same passage, and two levels for one item in one passage (the
    weaker is kept)."""
    problems, repairs = [], []
    asked = set(eligible)
    touches: list[dict] = []
    where: dict[tuple, dict] = {}
    raw = (out or {}).get("touches")
    if not isinstance(raw, list):
        return [], [f"touches isn't a list: {raw!r}"], []
    for t in raw:
        item, n, level = t.get("item"), t.get("passage"), t.get("level")
        if item not in asked:
            repairs.append(f"dropped a touch on {item}, which isn't an Askable rule the owner holds and hasn't told the agent")
        elif not _passage_number(n) or not 1 <= n <= passages:
            problems.append(f"a touch cites passage {n!r}, which doesn't exist")
        elif level not in LEVELS:
            problems.append(f"a touch has level {level!r}")
        elif (item, n) in contradicted:
            repairs.append(f"dropped a touch on {item} in passage {n}, where it is contradicted: a contradiction is not a touch")
        elif (item, n) not in where:
            where[(item, n)] = {"item": item, "passage": n, "level": level}
            touches.append(where[(item, n)])
        elif where[(item, n)]["level"] != level:
            weaker = min(level, where[(item, n)]["level"], key=LEVEL_STRENGTH.__getitem__)
            repairs.append(f"{item} had two levels in passage {n}; kept the weaker, {weaker}")
            where[(item, n)]["level"] = weaker
    return touches, problems, repairs


# ------------------------------------------------------------------------------------------------ the owner


class OwnerFailed(RuntimeError):
    pass


@dataclass
class OwnerReply:
    reply: str
    finished: bool
    message_kind: str
    answers: list[dict]
    kept: list[dict]  # corrections kept, each with its probability p and uniform u
    dropped: list[dict]
    redirect_event: str | None  # "delivered" or "settled" at this stop
    words_shown: int
    words_this_change: int
    shared: list[dict]  # {"item", "reason"}: asked, contradiction, redirect, or recalled (with "via": review or question)
    recalled: list[dict] = field(default_factory=list)  # {"item", "line", "via", "passage", "question"}
    draws: list[dict] = field(default_factory=list)  # every draw made at this stop, fired or not
    passages: int = 0
    calls: list[dict] = field(default_factory=list)  # each main and trim call: prompt, output, problems, repairs, cost
    touch_calls: list[dict] = field(default_factory=list)  # each touch call, recorded the same way
    check_calls: list[dict] = field(default_factory=list)  # each completion check, recorded the same way


def call_costs(reply: OwnerReply) -> dict[str, float]:
    """What the reply's model calls cost, by role, counting only calls whose cost was reported."""
    costs = {"main": 0.0, "touch": 0.0, "trim": 0.0, "check": 0.0}
    for role, calls in (("call", reply.calls), ("touch", reply.touch_calls), ("check", reply.check_calls)):
        for c in calls:
            key = "check" if role == "check" else "trim" if "trim" in c else ("main" if role == "call" else "touch")
            costs[key] += c.get("cost_usd") or 0.0
    return costs


def answer_lines(answers: Sequence[dict], label: bool = False) -> list[str]:
    """The answers as they go into the reply. With more than one, each carries its label, the agent's own words for
    its question, so a run of "Yes." answers can't be read against the wrong question: "Is that fine? Yes.", or
    "How long can notes be: Yes." for words without a question mark. An answer whose question wasn't quoted goes
    without a label. One answer stands alone. Without `label`, answers go in their order, unlabelled."""
    if len(answers) < 2 or not label:
        return [a["answer"] for a in answers]
    lines = []
    for a in answers:
        q = a.get("label", _label_text(a["question"]))  # no label when the question wasn't the agent's own words
        q = q.rstrip(":").strip() if q else q
        lines.append(a["answer"] if not q else f"{q} {a['answer']}" if q.endswith("?") else f"{q}: {a['answer']}")
    return lines


def _result(r) -> tuple[dict | None, float | None]:
    """A model callable returns its structured output, or (output, cost in dollars)."""
    return r if isinstance(r, tuple) else (r, None)


def catch_probability(policy: str, words_read: int, half: int = HALF_ATTENTION_WORDS) -> float:
    if policy == "diligent":
        return 1.0
    if policy == "rubber-stamp":
        return 0.0
    return 1.0 / (1.0 + words_read / half)


def trim_reply(trim: Callable[[str], dict] | None, message: str, out: dict, calls: list[dict], *,
               requested: Iterable[str] = (), ids: re.Pattern | None = None, scripted: Iterable[str] = ()) -> None:
    """Cut each targeted answer that shares a rule, and each correction, down to what the question or the quoted
    words need, with a separate call that sees only the agent's message and the draft parts. `requested`: items this
    change's own request asked for, whose omission the owner may still point out, so a DROP is ignored for them (one
    tied to no item keeps the trim as its guard). `ids`: the oracle's identifier pattern; an edit that adds an
    identifier is refused. `scripted`: items whose correction is a scripted response (recognized on sight), said in
    nearly the response's words, so the trim never sees or shortens it. Recall lines are added after this, so the trim
    never sees them."""
    if trim is None:
        return
    keep_whole = set(scripted)
    parts = [("answer", a, a["question"]) for a in out["answers"]
             if a["items"] and not a["no_view"] and a.get("breadth", "targeted") == "targeted"]
    parts += [("correction", c, c.get("wrong", "")) for c in out["corrections"] if c.get("item") not in keep_whole]
    if not parts:
        return
    prompt = trim_prompt(message, [(kind, about, d["answer" if kind == "answer" else "text"]) for kind, d, about in parts])
    raw, cost = _result(trim(prompt))
    edited = {p.get("index"): p.get("text", "") for p in (raw or {}).get("parts", [])}
    changes, dropped = [], []
    keep_anyway = set(requested)
    for n, (kind, d, _about) in enumerate(parts, start=1):
        key = "answer" if kind == "answer" else "text"
        new = (edited.get(n) or "").strip()
        old = d[key]
        if kind == "correction" and new == "DROP":
            # The quoted words were right as far as they went: an addition, not a correction. The trim can't see
            # this change's request, so the owner's own exception stands: something the request asked for and the
            # agent left out is still pointed out.
            if d.get("item") not in keep_anyway:
                dropped.append(d)
                changes.append({"part": n, "before": old, "after": None})
        elif new and new != "DROP" and not (ids is not None and ids.search(new)) and words(new) <= words(old):
            d[key] = new
            if new != old:
                changes.append({"part": n, "before": old, "after": new})
    out["corrections"] = [c for c in out["corrections"] if not any(c is x for x in dropped)]
    calls.append({"prompt": prompt, "output": raw, "problems": [], "trim": changes, "cost_usd": cost})


class Owner:
    """One trajectory's simulated owner. `ask(prompt)` runs the main model call (the reply's parts) and `touch(prompt)`
    the touch call (which passages touch the askable items not yet disclosed); `trim(prompt)` cuts the reply. Each is
    one stateless call returning its structured output, or (output, cost in dollars); tests pass fakes. Only a
    rubber-stamp owner, which never recalls on review, may go without `touch`.

    replicate: the seed shared by the trajectories being compared (other arms, other policies, a redirect's paired
    run), which every draw is keyed on. owner_items: each askable item's tier and recall line; an askable item
    without one is an error unless default_owner_item is given."""

    def __init__(self, *, oracle: Oracle, brief: str, policy: str, replicate: str, ask: Callable[[str], dict],
                 trim: Callable[[str], dict] | None = None, template: str | None = None, max_attempts: int = 3,
                 model: OwnerModel | None = None, owner_items: Mapping[str, OwnerItem] | None = None,
                 default_owner_item: OwnerItem | None = None, touch: Callable[[str], dict] | None = None,
                 touch_template: str | None = None, only_change: bool = False,
                 check: Callable[[str], dict] | None = None, check_template: str | None = None):
        if policy not in POLICIES:
            raise ValueError(f"policy must be one of {POLICIES}, not {policy!r}")
        if owner_items is None and default_owner_item is None:
            raise ValueError("the owner needs every askable item's tier and recall line (the seed's owner-items.json)")
        self.oracle, self.brief, self.policy, self.replicate, self.ask, self.trim = oracle, brief, policy, replicate, ask, trim
        self.touch = touch
        self.only_change = only_change  # a fork's owner: the start and the change being run, and nothing else
        self.check = check  # the completion check: does a "completion" report the change done, or announce work?
        self.check_template = check_template
        self.touch_template = touch_template if touch_template is not None else TOUCH_TEMPLATE_PATH.read_text(encoding="utf-8")
        self.model = model if model is not None else OwnerModel()
        self.owner_items = complete_owner_items(oracle, owner_items or {}, default_owner_item)
        if touch is None and policy != "rubber-stamp":
            raise ValueError("the owner needs a touch call (touch=...) under every policy but rubber-stamp")
        self.template = template if template is not None else TEMPLATE_PATH.read_text(encoding="utf-8")
        self.max_attempts = max_attempts
        self.ids = id_pattern(oracle.ids())
        self.record: list[Said] = []
        self.requests: list[tuple[int, str]] = []
        self.seen: dict[str, str] = {}
        self.disclosed: set[str] = set()  # items an answer, a correction, or a recall line has shared
        self.change: Change | None = None
        self.turns: list[Turn] = []
        self.said_now: list[Said] = []
        self.words_this_change = 0
        self.redirect_state: str | None = None
        self.redirect_point: str | None = None

    def fork(self) -> "Owner":
        """A copy for a disposable fork such as a probe; the original is untouched."""
        twin = copy.copy(self)
        for name in ("record", "requests", "seen", "disclosed", "turns", "said_now"):
            setattr(twin, name, copy.copy(getattr(self, name)))
        return twin

    def start_change(self, change: Change) -> str:
        """Begin a change; returns the owner's request for the agent's first prompt."""
        if self.change is not None:
            raise RuntimeError(f"change {self.change.number} hasn't ended")
        unknown = [i for i in (change.redirect.settles if change.redirect else ()) if i not in self.oracle.ids()]
        if unknown:
            raise ValueError(f"change {change.number}: the clarification settles {', '.join(unknown)}, which the oracle doesn't have")
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
                            turns=self.turns, redirect_state=state, template=self.template, only_change=self.only_change)

    def _call(self, prompt: str, state: str | None, calls: list[dict], passages: int, message: str) -> dict:
        r = self.change.redirect
        withheld = r.introduces if (r and r.kind == "change of mind" and state == "pending") else ()
        items = released_items(self.oracle, self.change.number, withhold=withheld, only_change=self.only_change)
        pending_cl = bool(r and r.kind == "clarification" and state == "pending")
        for _ in range(self.max_attempts):
            raw, cost = _result(self.ask(prompt))
            out, problems, repairs = check_output(raw, items, clarification_pending=pending_cl, passages=passages,
                                                  in_play=self.change.in_play, requested=self._requested_now(), ids=self.ids,
                                                  message=message)
            calls.append({"prompt": prompt, "output": raw, "problems": problems, "repairs": repairs, "cost_usd": cost})
            if not problems:
                return out
        raise OwnerFailed(f"no valid reply after {self.max_attempts} attempts: {problems}")

    def _touches(self, message: str, documents: Sequence[Document], state: str | None, passages: int,
                 disclosed: set[str], contradicted: set, calls: list[dict]) -> list[dict]:
        """The touch call, on the stop as the last main call saw it: which passages touch each askable item the owner
        holds and hasn't disclosed. Made only when there is such an item and a passage to touch it."""
        eligible = touch_items(self.oracle, self.change, disclosed=disclosed, redirect_state=state,
                               only_change=self.only_change)
        if not eligible or not passages:
            return []
        prompt = touch_prompt(oracle=self.oracle, change=self.change, message=message, documents=documents,
                              disclosed=disclosed, redirect_state=state, template=self.touch_template,
                              only_change=self.only_change)
        for _ in range(self.max_attempts):
            raw, cost = _result(self.touch(prompt))
            touches, problems, repairs = check_touches(raw, eligible, passages=passages, contradicted=contradicted)
            calls.append({"prompt": prompt, "output": raw, "problems": problems, "repairs": repairs, "cost_usd": cost})
            if not problems:
                return touches
        raise OwnerFailed(f"no valid touches after {self.max_attempts} attempts: {problems}")

    def _announces_work(self, message: str, calls: list[dict]) -> bool:
        """The completion check on the message alone. A check that never answers validly leaves the main call's
        reading, as before the check existed."""
        prompt = completion_check_prompt(message, self.check_template)
        for _ in range(self.max_attempts):
            raw, cost = _result(self.check(prompt))
            verdict, problems = check_completion(raw, message)
            calls.append({"prompt": prompt, "output": raw, "problems": problems, "cost_usd": cost,
                          "reclassified": "approval" if verdict == "work to do" else None})
            if verdict:
                return verdict == "work to do"
        return False

    def _requested_now(self) -> set[str]:
        """Items this change's own request asks for: those stated in it or emerging with it, and at the first build,
        the brief's. A probe's request names no item."""
        ch = self.change
        if ch is None or ch.probe:
            return set()
        if ch.number == 0:
            return {i.id for i in self.oracle.items if i.kind == "Stated at start"}
        return {i.id for i in self.oracle.items if i.in_force == ch.number
                and i.kind.lower().startswith(("stated in change", "emerging"))}

    def _trim(self, message: str, out: dict, calls: list[dict]) -> None:
        scripted = {i.id for i in self.oracle.items if i.response}  # recognized on sight: said in the response's words
        trim_reply(self.trim, message, out, calls, requested=self._requested_now(), ids=self.ids, scripted=scripted)

    def _read(self, offset: int, before: int, shown: int) -> tuple[float, float, int]:
        """(a, w, read_before) for a position `offset` new words into this stop: the policy's attention there, w as
        the model counts it, and the new words shown earlier in this change (for the session drag)."""
        w = {"stop": offset, "change": before + offset, "pilot": before + shown}[self.model.counting]
        read_before = before + offset
        if self.policy == "diligent":
            return 1.0, w, read_before
        if self.policy == "rubber-stamp":
            return 0.0, w, read_before
        return attention(self.model, w=w, read_before=read_before), w, read_before

    def _probability(self, event: str, a: float, r: float | None = None) -> float:
        """The chance a read-and-noticed event happens on review, under this owner's policy."""
        if self.policy == "diligent":
            return 1.0 if event == "contradiction" else r
        if self.policy == "rubber-stamp":
            return 0.0
        return a * self.model.catch if event == "contradiction" else a * min(r, self.model.catch)

    def respond(self, message: str, documents: Sequence[Document] = (), *, code_written: bool) -> OwnerReply:
        """The owner's response to the agent's stop. `code_written`: this change has changed a source file
        other than documentation or tests."""
        ch = self.change
        if ch is None:
            raise RuntimeError("no change in progress")
        stop = split_stop(message, documents)
        shown = words(message) + sum(d.words for d in documents)
        before = self.words_this_change
        self.words_this_change += shown
        redirect, pending = ch.redirect, self.redirect_state == "pending"
        change_of_mind = pending and redirect.kind == "change of mind"
        late_fires = pending and redirect.timing == "late" and code_written
        calls: list[dict] = []
        touch_calls: list[dict] = []
        event = None
        npass = len(stop.passages)
        state = self.redirect_state  # the redirect state the last main call saw
        if change_of_mind and late_fires:
            state = "firing"
            out = self._call(self._prompt(message, documents, state), state, calls, npass, message)
            event = "delivered"
        else:
            out = self._call(self._prompt(message, documents, state), state, calls, npass, message)
            fires = pending and (late_fires or (redirect.timing == "early" and out["message_kind"] in FIRE_KINDS))
            if pending and redirect.kind == "clarification" and out["clarification_settled"]:
                event = "settled"
            elif fires and change_of_mind:
                # Answer again from the view the owner holds once they have changed their mind. Contradictions come
                # from this second call, and the touch call sees the same view.
                state = "firing"
                out = self._call(self._prompt(message, documents, state), state, calls, npass, message)
                event = "delivered"
            elif fires:
                event = "delivered"
        check_calls: list[dict] = []
        if out["message_kind"] == "completion" and self.check is not None:
            if self._announces_work(message, check_calls):
                out["message_kind"] = "approval"  # what it will do next is a plan to approve, not a report
        if event:
            self.redirect_state = event
            self.redirect_point = f"{out['message_kind']}, code {'written' if code_written else 'not written'}"

        disclosed_before = set(self.disclosed)  # what the touch call asks about is decided against this view
        # A clarification delivered with this reply, or found already settled, shares the items it settles: they are
        # disclosed before any draw, so no recall line for them can follow in this reply or later.
        settled = list(redirect.settles) if event in ("delivered", "settled") and redirect.kind == "clarification" else []
        self.disclosed.update(settled)
        # The touch call: never under rubber-stamp, which doesn't recall on review. A touch where the main call
        # reported a contradiction of the same item in the same passage is dropped.
        out["touches"] = ([] if self.policy == "rubber-stamp" else
                          self._touches(message, documents, state, npass, disclosed_before | set(settled),
                                        contradicted_in(out["corrections"]), touch_calls))

        self._trim(message, out, calls)
        scope = scope_key(self.model.scope, ch, len(self.turns))
        offsets = {p.number: p.offset for p in stop.passages}
        after_first_build = ch.number > 0 or ch.probe
        draws: list[dict] = []

        # Contradictions: one uniform per item (or per quoted words) and scope; a correction is kept when the policy's
        # probability at its passage exceeds it. Something left out of this change's request has no passage and is
        # noticed, if at all, at the end of the stop.
        kept, dropped = [], []
        for c in out["corrections"]:
            a, w, read_before = self._read(offsets.get(c["passage"], shown), before, shown)
            p = self._probability("contradiction", a)
            u = uniform(self.replicate, contradiction_key(c), "contradiction", scope)
            draws.append({"event": "contradiction", "item": c["item"], "passage": c["passage"], "w": w,
                          "read_before": read_before, "a": a, "r": None, "p": p, "u": u, "fired": p > u})
            (kept if p > u else dropped).append({**c, "p": p, "u": u})
        # The same correction for the same item, word for word, is said once.
        kept = [c for k, c in enumerate(kept) if (c["item"], c["text"]) not in {(x["item"], x["text"]) for x in kept[:k]}]
        for ans in out["answers"]:
            if ans["breadth"] == "targeted":
                self.disclosed.update(ans["items"])
        self.disclosed.update(c["item"] for c in kept if c["item"] != "none")

        # Recall on review: each unsaid askable item the passages touch, at the first touching passage whose
        # probability exceeds the item's uniform. n counts the unsaid items touching the same passage. An item some
        # passage of this stop already states is not drawn for at this stop, and doesn't count in n.
        said_here = {t["item"] for t in out["touches"] if t["level"] == "says"}
        touches = sorted((t for t in out["touches"] if t["item"] not in disclosed_before and t["item"] not in said_here),
                         key=lambda t: t["passage"])
        fan = collections.Counter(t["passage"] for t in touches)
        recalled: list[dict] = []
        for item in dict.fromkeys(t["item"] for t in touches):
            if item in self.disclosed:
                continue
            u = uniform(self.replicate, item, "recall", scope)
            for t in (t for t in touches if t["item"] == item):
                a, w, read_before = self._read(offsets[t["passage"]], before, shown)
                r = recall_rate(self.model, self.owner_items[item].tier, direct=t["level"] == "direct", n=fan[t["passage"]],
                                after_first_build=after_first_build)
                p = self._probability("recall", a, r)
                draws.append({"event": "recall", "item": item, "passage": t["passage"], "w": w, "read_before": read_before,
                              "a": a, "r": r, "p": p, "u": u, "fired": p > u})
                if p > u:
                    recalled.append({"item": item, "line": self.owner_items[item].recall, "via": "review",
                                     "passage": t["passage"], "question": None})
                    self.disclosed.add(item)
                    break
        recalled.sort(key=lambda x: x["passage"])

        # Broad questions: under every policy, each in-scope item still unsaid is drawn at its adjacent rate, with
        # n = 1 and no attention. What is recalled is the answer.
        for ans in out["answers"]:
            if ans["breadth"] != "broad":
                continue
            got = []
            for item in ans["in_scope"]:
                if item in self.disclosed:
                    continue
                r = recall_rate(self.model, self.owner_items[item].tier, direct=False,
                                after_first_build=after_first_build and self.model.dormancy_on_broad)
                u = uniform(self.replicate, item, self.model.broad_uniform, scope)
                draws.append({"event": "broad", "item": item, "passage": None, "w": None, "read_before": None, "a": None,
                              "r": r, "p": r, "u": u, "fired": r > u})
                if r > u:
                    got.append(item)
                    self.disclosed.add(item)
                    recalled.append({"item": item, "line": self.owner_items[item].recall, "via": "question",
                                     "passage": None, "question": ans["question"]})
            ans["answer"] = " ".join(self.owner_items[i].recall for i in got) or NOTHING_ELSE
            ans["items"] = got

        review_lines = [x["line"] for x in recalled if x["via"] == "review"]
        parts = (([redirect.text] if event == "delivered" else []) + answer_lines(out["answers"], self.model.label_answers)
                 + [c["text"] for c in kept] + review_lines)
        kind = out["message_kind"]
        finished = kind == "completion" and not parts
        if finished:
            reply = ""
        elif kept or review_lines or event == "delivered":
            reply = "\n\n".join(parts + ["Otherwise, go ahead."])
        elif parts:
            reply = "\n\n".join(parts + ["Go ahead."])
        elif kind == "stop":
            reply = "Please continue."
        else:
            reply = "That looks fine. Go ahead."

        shared = []
        for a in out["answers"]:
            shared += ([{"item": i, "reason": "asked"} for i in a["items"]] if a["breadth"] == "targeted"
                       else [{"item": i, "reason": "recalled", "via": "question"} for i in a["items"]])
        shared += [{"item": c["item"], "reason": "contradiction"} for c in kept if c["item"] != "none"]
        shared += [{"item": x["item"], "reason": "recalled", "via": "review"} for x in recalled if x["via"] == "review"]
        if event == "delivered":
            shared.append({"item": None, "reason": "redirect"})
        shared += [{"item": i, "reason": "redirect" if event == "delivered" else "settled"} for i in settled]
        for a in out["answers"]:
            self.said_now.append(Said(ch.number, a["answer"], a["question"], tuple(a["items"])))
        for c in kept:
            self.said_now.append(Said(ch.number, c["text"], None, () if c["item"] == "none" else (c["item"],)))
        for x in recalled:
            if x["via"] == "review":
                self.said_now.append(Said(ch.number, x["line"], None, (x["item"],)))
        self.turns.append(Turn(message, tuple(d.name for d in documents), reply))
        for d in documents:
            if d.current is not None:
                self.seen[d.name] = d.current
        return OwnerReply(reply=reply, finished=finished, message_kind=kind, answers=out["answers"], kept=kept,
                          dropped=dropped, redirect_event=event, words_shown=shown,
                          words_this_change=self.words_this_change, shared=shared, recalled=recalled, draws=draws,
                          passages=npass, calls=calls, touch_calls=touch_calls, check_calls=check_calls)

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


def judge_prompt(owner_prompt: str, reply: str, scripted: str | None = None, recalled: Sequence[dict] = (),
                 template: str | None = None) -> str:
    """The leak judge's prompt for one stop: everything the owner was given, and the reply that was sent.
    `scripted` is the redirect text the harness inserted, which the judge doesn't judge. `recalled` is the recall
    lines the harness drew ({"item", "line"}), which are licensed for their items."""
    template = template if template is not None else JUDGE_TEMPLATE_PATH.read_text(encoding="utf-8")
    note = (f"The reply includes these scheduled words, which the owner was required to say. Don't judge them:\n\n{_blockquote(scripted)}"
            if scripted else "")
    drawn = ""
    if recalled:
        drawn = ("These are the recall lines the harness drew and added to the reply after the owner wrote it, each for "
                 "the rule named with it. Each is licensed for that rule, whether it answers a broad question or follows "
                 "something the agent showed: don't count these lines as leaks. Judge the rest of the reply as usual, "
                 "including anything else it says about the same rules:\n\n"
                 + "\n".join(f'- [{x["item"]}] "{x["line"]}"' for x in recalled))
    return _fill(template, {"OWNER_PROMPT": owner_prompt.strip(), "REPLY": reply.strip() or "(empty: the owner accepted the change)",
                            "SCRIPTED": note, "RECALLED": drawn})


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
