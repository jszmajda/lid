"""The growth test's plain-data pieces (design.md, "The growth test"): which changes pair as a course change and its
reliance change, which probes check an item, the flip checks a course change calls for, and owner-hours."""

from __future__ import annotations

from . import grading, simulator

FLIP_KINDS = ("retirement", "reversal", "re-reversal", "rescope")  # a rescope retires the old version for a new one
WPM = 238  # owner reading speed, words a minute


def course_pairs(script: dict[int, simulator.Change], upto: int | None = None) -> list[tuple[int, int]]:
    """(course change, a reliance change on it), for every pair whose reliance change is at or before `upto`. A reliance
    change can serve several course changes."""
    pairs = []
    for n, c in script.items():
        for t in c.reliance_for:
            target = script.get(t)
            if target is not None and target.course_change is not None and (upto is None or n <= upto):
                pairs.append((t, n))
    return sorted(pairs)


def reliance_changes(script: dict[int, simulator.Change], upto: int | None = None) -> dict[int, list[int]]:
    """Each reliance change at or before `upto`, with the course changes it serves."""
    out: dict[int, list[int]] = {}
    for course, r in course_pairs(script, upto):
        out.setdefault(r, []).append(course)
    return dict(sorted(out.items()))


def item_id(name: str) -> str:
    return name.split()[0]


def probes_for(probeset: grading.ProbeSet, items) -> list[str]:
    """The probes that check these items, in the probe file's order."""
    want = set(items)
    return [p.id for p in probeset.probes if item_id(p.item) in want]


def reliance_probes(script: dict[int, simulator.Change], probeset: grading.ProbeSet, course: int) -> list[str]:
    """What a reliance change is graded on: the probes of the rule its course change put in force (it should hold)
    and of the rule it retired (it should stay retired)."""
    c = script[course]
    return probes_for(probeset, set(c.introduces) | set(c.retires))


def reliance_change_probes(script: dict[int, simulator.Change], probeset: grading.ProbeSet, reliance: int) -> list[str]:
    """What a reliance change is graded on: every rule it relies on, across the course changes it serves."""
    items = set()
    for course in script[reliance].reliance_for:
        if course in script:
            items |= set(script[course].introduces) | set(script[course].retires)
    return probes_for(probeset, items)


def flip_plan(script: dict[int, simulator.Change], probeset: grading.ProbeSet, upto: int) -> list[dict]:
    """The flip checks for every retirement, reversal, re-reversal, and rescope up to `upto`, beyond the probes' own
    ranges: the retired item's probes once after the course change, and the new item's probes once before it, both
    expected not met. An emerging change's new item is checked once before it for anticipation: it isn't expected
    to fail, so it isn't a flip."""
    plan = []
    for n, c in sorted(script.items()):
        if n > upto or c.course_change is None:
            continue
        kind = c.course_change.kind
        if kind == "emerging":
            if c.introduces and c.introduces != simulator.ALL:
                plan.append({"course": n, "kind": kind, "when": "before", "at_change": n - 1, "items": list(c.introduces),
                             "probes": probes_for(probeset, c.introduces), "expect": "anticipated?"})
            continue
        if kind not in FLIP_KINDS:
            continue
        if c.retires:
            plan.append({"course": n, "kind": kind, "when": "after", "at_change": n, "items": list(c.retires),
                         "probes": probes_for(probeset, c.retires), "expect": "not met"})
        if c.introduces and c.introduces != simulator.ALL:
            plan.append({"course": n, "kind": kind, "when": "before", "at_change": n - 1, "items": list(c.introduces),
                         "probes": probes_for(probeset, c.introduces), "expect": "not met"})
    return plan


def owner_hours(words: float, wpm: int = WPM) -> float:
    return words / wpm / 60
