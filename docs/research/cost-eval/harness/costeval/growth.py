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


def reliance_probes(probes_text: str, script: dict[int, simulator.Change], course: int) -> tuple[str, list[str]]:
    """The seed's probes with the reliance request's two frozen outcomes beside them, as probes sharing its setup and
    scenario: P-RRnn-current (what the current rule gives) and P-RRnn-displaced (what the displaced rule would give)."""
    r = script[course].reliance_request
    ids = [f"P-RR{course:02d}-current", f"P-RR{course:02d}-displaced"]
    blocks = [f"### RR-{course:02d}"]
    for pid, expected in zip(ids, (r.current_outcome, r.displaced_outcome)):
        blocks.append(f"#### {pid}\n- **Applies:** from change 0\n- **Needs:** none\n- **Setup:** {r.setup}\n"
                      f"- **Scenario:** {r.scenario}\n- **Expected observation:** {expected}")
    return probes_text.rstrip("\n") + "\n\n" + "\n\n".join(blocks) + "\n", ids


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
