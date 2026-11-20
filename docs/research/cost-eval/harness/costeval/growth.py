"""The growth test's plain-data pieces (design.md, "The growth test"): which changes pair as a course change and its
reliance change, which probes check an item, the flip checks a course change calls for, and owner-hours."""

from __future__ import annotations

from . import grading, simulator

FLIP_KINDS = ("retirement", "reversal", "re-reversal", "rescope")  # a rescope retires the old version for a new one
WPM = 238  # owner reading speed, words a minute


def reliance_requests(script: dict[int, simulator.Change], upto: int | None = None) -> list[tuple[int, int]]:
    """(course change, lag) for each course change whose reliance request runs at or before `upto`: after change
    course + lag, as a fork."""
    return [(n, c.reliance_request.lag) for n, c in sorted(script.items())
            if c.course_change is not None and c.reliance_request is not None
            and (upto is None or n + c.reliance_request.lag <= upto)]


def reliance_change(script: dict[int, simulator.Change], course: int) -> simulator.Change:
    """The reliance request as a change the owner answers: a fork-only request at the snapshot after course + lag,
    whose owner stands where the main line's does there (as a probe fork's does)."""
    r = script[course].reliance_request
    return simulator.Change(number=course + r.lag, title=f"Reliance request after change {course}", request=r.request,
                            relies_on=simulator.ALL, probe=True)


def reliance_probes(probeset: grading.ProbeSet, course: int) -> list[str] | None:
    """The reliance request's two frozen outcomes as the seed writes them under `### RR-CC`: P-RRCC-current (what the
    current rule gives) and P-RRCC-displaced (what the displaced rule would give), built by the probe drafter from the
    request's setup and scenario. None when the seed has no such pair: nothing is invented in their place."""
    ids = [f"P-RR{course:02d}-current", f"P-RR{course:02d}-displaced"]
    have = {p.id for p in probeset.probes}
    return ids if all(i in have for i in ids) else None


def current_rule_probes(script: dict[int, simulator.Change], probeset: grading.ProbeSet, course: int) -> list[str]:
    """The probes of the rule a course change brought in, in force where its reliance request runs (course + lag)."""
    at = course + script[course].reliance_request.lag
    want = set(script[course].introduces) if script[course].introduces != simulator.ALL else set()
    return [p.id for p in probeset.probes if item_id(p.item) in want and p.applies(at)]


def reliance_outcome(current: str | None, displaced: str | None) -> str:
    """Which rule a reliance fork followed, from its two frozen outcomes' verdicts."""
    if current not in ("met", "not met") or displaced not in ("met", "not met"):
        return "undetermined"
    return {("met", "not met"): "current", ("not met", "met"): "displaced", ("not met", "not met"): "neither",
            ("met", "met"): "both"}[(current, displaced)]


def item_id(name: str) -> str:
    return name.split()[0]


def probes_for(probeset: grading.ProbeSet, items) -> list[str]:
    """The probes that check these items, in the probe file's order."""
    want = set(items)
    return [p.id for p in probeset.probes if item_id(p.item) in want]


def transition_probes(probeset: grading.ProbeSet, items, course: int, side_of: int) -> tuple[list[str], dict[str, str]]:
    """The probes a flip check runs for these rows at course change `course`: each row's flip probe P-RDxx-flipCC where
    the seed has one (it shares its setup and scenario with its partner on the other row, so it fails across the change
    only because the rule did), and otherwise every probe of the row in force at change `side_of`, the row's side of
    the change. Where any row on the side has a flip probe, the side's rows without one are skipped: their probes can't
    flip (the seed says why under their headings). Returns the probes and, per row, which way was used ("flip", "all"
    or "skipped")."""
    flipped = {item: [p.id for p in probeset.probes if item_id(p.item) == item and p.id.endswith(f"-flip{course:02d}")]
               for item in items}
    any_flip = any(flipped.values())
    probes, choice = [], {}
    for item in items:
        if flipped[item]:
            choice[item] = "flip"
            probes += flipped[item]
        elif any_flip:
            choice[item] = "skipped"
        else:
            choice[item] = "all"
            probes += [p.id for p in probeset.probes if item_id(p.item) == item and p.applies(side_of)]
    return probes, choice


def rescope_reach(script: dict[int, simulator.Change], probeset: grading.ProbeSet, course: int) -> tuple[str, str]:
    """Which way a rescope goes, and where that came from. A widening rescope keeps the old row's behaviour inside the
    new one, so only the new row can fail across the change; a narrowing one, only the old row. The change script's
    word wins ("change script"); without one, the seed's flip probes say it ("flip probes"): on the new row only,
    widening; on the old row only, narrowing; on both, "both" (two-sided). With neither, "unknown", checked on both
    sides ("no flip probes")."""
    c = script[course]
    if c.course_change.reach:
        return c.course_change.reach, "change script"
    flipped = {item_id(p.item) for p in probeset.probes if p.id.endswith(f"-flip{course:02d}")}
    old = bool(flipped & set(c.retires))
    new = bool(flipped & (set(c.introduces) if c.introduces != simulator.ALL else set()))
    if old and new:
        return "both", "flip probes"
    if new or old:
        return ("widening" if new else "narrowing"), "flip probes"
    return "unknown", "no flip probes"


def _sides(script: dict[int, simulator.Change], probeset: grading.ProbeSet, course: int) -> tuple[bool, bool]:
    """Whether a course change is checked on the old row's side (after it) and on the new row's (before it)."""
    if script[course].course_change.kind != "rescope":
        return True, True
    reach, _ = rescope_reach(script, probeset, course)
    return reach != "widening", reach != "narrowing"


def course_fork_probes(script: dict[int, simulator.Change], probeset: grading.ProbeSet,
                       course: int) -> tuple[list[str], list[str], dict[str, str]]:
    """What a course fork is judged by at its end: the new rule's probes (should hold) and the retired rule's (should
    fail), each row by its flip probe where the seed has one and otherwise by its probes in force on its side of the
    change (transition_probes). Returns the new, the retired (less any shared with the new), and the choice per row."""
    c = script[course]
    old_side, new_side = _sides(script, probeset, course)  # a rescope's reach leaves one side unchecked
    introduces = c.introduces if c.introduces != simulator.ALL and new_side else ()
    new, new_choice = transition_probes(probeset, introduces, course, course)
    old, old_choice = transition_probes(probeset, c.retires if old_side else (), course, course - 1)
    return new, [x for x in old if x not in new], {**old_choice, **new_choice}


def flip_plan(script: dict[int, simulator.Change], probeset: grading.ProbeSet, upto: int) -> list[dict]:
    """The flip checks for every retirement, reversal, re-reversal, and rescope up to `upto`, beyond the probes' own
    ranges: the retired row once after the course change, and the new row once before it, both expected not met,
    each by its flip probe where the seed has one (transition_probes). A rescope is checked on one side only, as its
    reach says (rescope_reach), and records its reach and where that came from. An emerging change's new row is
    checked once before it for anticipation: it isn't expected to fail, so it isn't a flip."""
    plan = []

    def entry(n, kind, when, items, expect):
        at = n if when == "after" else n - 1
        probes, choice = transition_probes(probeset, items, n, n - 1 if when == "after" else n)
        e = {"course": n, "kind": kind, "when": when, "at_change": at, "items": list(items), "probes": probes,
             "choice": choice, "expect": expect}
        if kind == "rescope":
            e["reach"], e["reach_source"] = rescope_reach(script, probeset, n)
        return e
    for n, c in sorted(script.items()):
        if n > upto or c.course_change is None:
            continue
        kind = c.course_change.kind
        if kind == "emerging":
            if c.introduces and c.introduces != simulator.ALL:
                plan.append(entry(n, kind, "before", c.introduces, "anticipated?"))
            continue
        if kind not in FLIP_KINDS:
            continue
        old_side, new_side = _sides(script, probeset, n)  # a rescope is checked on its reach's side only
        if c.retires and old_side:
            plan.append(entry(n, kind, "after", c.retires, "not met"))
        if c.introduces and c.introduces != simulator.ALL and new_side:
            plan.append(entry(n, kind, "before", c.introduces, "not met"))
    return plan


def owner_hours(words: float, wpm: int = WPM) -> float:
    return words / wpm / 60
