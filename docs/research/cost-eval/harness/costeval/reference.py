"""The instrument gate's reference runs (design.md, "The trial, and its gate"), as the seed's reference-builds.md says
them, from the data its reference-builds.json holds (written by the seed's build_reference.py). Neither is a study arm.

- R+ (arm ref-correct): one trajectory through change 40. At every change its owner delivers the request (or the
  symptom report, whether or not a diagnostic would fire) with any emerging statement and no redirect, and adds in the
  same opening message every row in force there, in the spec's owner text, under INTRO. It answers from those rows
  alone and withholds nothing: every row is stated, so there is no latent row, no recall and no narrative.
- S_C (arm ref-stale), one per course change C: forked from R+'s snapshot after C-1. At C the course change is
  declined: skipped (no session), or for an emerging change, one stand-in session stating the displaced choice. Then
  C+1 to C+L run as on the main line, with an owner holding R+'s rows less C's new rows, plus C's retired rows and any
  stand-in rule (the spec's `hold`).

Each runs C's reliance request as a fork after C+L with the same owner.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from . import simulator

KINDS = ("correct", "stale")
SPEC_FILE = "reference-builds.json"
INTRO = "These are all the rules the service must follow from now on. Follow every one; ask if one is unclear."
STAND_IN_REQUEST = "Please make sure of this: {rule}"


def load_spec(seed_dir: Path) -> dict:
    return json.loads((Path(seed_dir) / "hidden" / SPEC_FILE).read_text(encoding="utf-8"))


def stale_forks(spec: dict) -> list[tuple[int, int]]:
    """(course change, lag) for each stale fork, in change order."""
    return sorted((int(c), e["lag"]) for c, e in spec["stale"].items())


def stand_in_id(course: int) -> str:
    return f"SI-{course:02d}"


def held(spec: dict, n: int, stale_of: int | None = None) -> list[str]:
    """The rows the owner holds at change n: R+'s, or S_C's (the stand-in rule apart)."""
    return spec["correct"][str(n)] if stale_of is None else spec["stale"][str(stale_of)]["hold"][str(n)]


def statement(spec: dict, n: int, stale_of: int | None = None) -> str:
    """The rows stated in change n's opening message, in the spec's owner text, after INTRO."""
    texts = [spec["owner_text"][i] for i in held(spec, n, stale_of)]
    rule = spec["stale"][str(stale_of)]["stand_in"] if stale_of is not None else None
    return INTRO + "\n\n" + "\n".join(f"- {t}" for t in texts + ([rule] if rule else []))


def owner_view(oracle: simulator.Oracle, spec: dict, stale_of: int | None = None) -> simulator.Oracle:
    """The oracle a reference owner answers from: the rows the spec lists, by their lifetimes, every one stated in the
    spec's owner text, and no narrative. For S_C, C's new rows never come into force, the rows it retires stay, and
    the stand-in rule (an emerging change's displaced choice) is a stated row from C."""
    ever = {i for rows in spec["correct"].values() for i in rows}
    drops, keeps = set(), set()
    if stale_of is not None:
        e = spec["stale"][str(stale_of)]
        drops, keeps = set(e["drops"]), set(e["keeps"])
        ever |= keeps
    items = []
    for i in oracle.items:
        if i.id not in ever or i.id in drops:
            items.append(replace(i, kind="Stated", in_force=None))
            continue
        items.append(replace(i, kind="Stated", behavior=spec["owner_text"].get(i.id, i.behavior),
                             retired=None if i.id in keeps else i.retired))
    if stale_of is not None and spec["stale"][str(stale_of)]["stand_in"]:
        items.append(simulator.Item(id=stand_in_id(stale_of), behavior=spec["stale"][str(stale_of)]["stand_in"],
                                    kind="Stated", in_force=stale_of, retired=None))
    return simulator.Oracle(narrative={}, items=items)


def plan_change(spec: dict, script: dict[int, simulator.Change], n: int,
                stale_of: int | None = None) -> tuple[str, simulator.Change | None]:
    """What a reference runs at change n: ("run", the change, without a redirect), or for S_C at C, ("skip", None) or
    ("run", the stand-in session)."""
    if stale_of is not None and n == stale_of:
        e = spec["stale"][str(n)]
        if e["decline"] == "skip":
            return "skip", None
        return "run", simulator.Change(number=n, title=f"Stand-in for change {n}",
                                       request=STAND_IN_REQUEST.format(rule=e["stand_in"]), relies_on=simulator.ALL)
    c = script[n]
    return "run", (replace(c, redirect=None) if c.redirect is not None else c)
