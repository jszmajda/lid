"""Repair forks (plan.md, M2e): what it costs to fix a latent rule a run missed, and whether the fix holds without
breaking other rules. For each latent item (any kind but stated) a checkpoint's grading has as not met, a fork from
that checkpoint's snapshot runs one fresh session opened by the owner's repair report for the item (the seed's
hidden/repair-reports.json, keyed by item), with the trajectory's owner as it stood there. The fork is then regraded in
full at the checkpoint's change: the item's own probes say whether it was fixed, and every item met at the checkpoint
is checked again for keeping."""

from __future__ import annotations

import json
from pathlib import Path

from . import grading, simulator

REPORTS = "repair-reports.json"


def load_reports(seed_dir: Path) -> dict:
    """The seed's repair reports by item; empty while the file hasn't been written."""
    f = seed_dir / "hidden" / REPORTS
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def report_for(reports: dict, item: str) -> str | None:
    """An item's repair report: the entry itself when it is text, else its "report" field."""
    e = reports.get(item)
    if isinstance(e, dict):
        e = e.get("report")
    return e.strip() if isinstance(e, str) and e.strip() else None


def item_verdicts(gdir: Path, probes: list[grading.Probe]) -> dict[str, str] | None:
    """Item id -> verdict from one grading's verdicts.json; None when it hasn't run, or failed."""
    f = gdir / "verdicts.json"
    if not f.exists():
        return None
    data = json.loads(f.read_text())
    if data.get("error"):
        return None
    pv = {p: (v if isinstance(v, str) else v.get("verdict")) for p, v in (data.get("probes") or {}).items()}
    pv = {p: v for p, v in pv.items() if v}
    items = grading.item_verdicts(pv, [p for p in probes if p.id in pv])
    return {i: v["verdict"] for i, v in items.items() if v["verdict"]}


def latent(oracle: simulator.Oracle) -> set[str]:
    return {i.id for i in oracle.items if not i.kind.lower().startswith("stated")}


def latent_misses(items: dict[str, str], oracle: simulator.Oracle) -> list[str]:
    """The latent items a grading has as not met (one the grader couldn't exercise isn't a miss)."""
    lat = latent(oracle)
    return sorted(i for i, v in items.items() if v == "not met" and i in lat)


def outcome(before: dict[str, str], after: dict[str, str], item: str) -> dict:
    """Whether the repair fixed the item (its verdict after: met, not met, or undetermined), and keeping: of the other
    items met at the checkpoint, those still met, those now not met (broken), and those left without a verdict."""
    got = after.get(item)
    kept = sorted(i for i, v in before.items() if v == "met" and i != item)
    return {"item_verdict": got, "fixed": True if got == "met" else False if got == "not met" else None,
            "keeping": {"met_before": len(kept), "held": sum(after.get(i) == "met" for i in kept),
                        "broken": [i for i in kept if after.get(i) == "not met"],
                        "undetermined": [i for i in kept if after.get(i) not in ("met", "not met")]}}
