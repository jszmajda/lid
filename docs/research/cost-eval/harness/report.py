"""Summarize a stage's trajectories: fidelity, cost, and the owner's attention, per arm.

    python3.12 report.py --seed benchtime --prefix s2 --verdicts rejudge-v4 \\
        --arms bare:1,2,3 bare-aa:1,2,3 cheap-discipline:4,5,6 lid-full:1,2,3 positive-control:1,2,3 \\
        --out ../runs/stage2/report.md

Reads only what the runs recorded: each trajectory's trajectory.json and owner records, its touchpoints.json and
owner-audit.json where they exist, the verdicts of each graded checkpoint, and its probe-request forks
(`<id>-probeNN-1`). Writes a Markdown report and the same numbers as JSON beside it.

Items met is the share of items with a verdict that are met; "couldn't exercise" counts against it, and probes not
run (deferred needs) leave their items out. A "missing" item (a grader error a rerun didn't resolve) is neither met
nor counted against: it is left out of the share and reported by cause and arm. Beside each share, the items an
interface fault left after the rerun: counted "not met" where the extraction found nothing addressing them in the
arm's diff (absent), and missing otherwise. Items are split by how the owner discloses them (stated, askable,
recognized on sight, emerging) and, where the seed has `hidden/bands.json`, latent items by guessability band.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import grading, growth, rust_grading, simulator  # noqa: E402

KINDS = ("stated", "askable", "recognized on sight", "emerging")


def kind_of(item: simulator.Item) -> str:
    k = item.kind.lower()
    for name in KINDS:
        if k.startswith(name):
            return name
    return "other"


def checkpoint_items(gdir: Path, verdicts: str, probes: list[grading.Probe]) -> dict[str, str] | None:
    """Item id -> verdict for one graded checkpoint, or None if it has no verdicts under that name."""
    f = gdir / f"{verdicts}.json"
    if not f.exists():
        return None
    data = json.loads(f.read_text())
    if "rows" in data:  # a re-judgment: each probe's new verdict
        pv = {p: r["new"] for p, r in data["rows"].items() if r.get("new")}
    else:  # a Rust grading writes each verdict as text
        pv = {p: (v if isinstance(v, str) else v.get("verdict")) for p, v in data.get("probes", {}).items()}
        pv = {p: v for p, v in pv.items() if v}
    items = grading.item_verdicts(pv, [p for p in probes if p.id in pv])
    return {i: v["verdict"] for i, v in items.items() if v["verdict"]}


def missing_causes(gdir: Path, verdicts: str) -> dict[str, int]:
    """Probes left missing in one graded checkpoint, counted by the grader error that left them so."""
    f = gdir / f"{verdicts}.json"
    data = json.loads(f.read_text()) if f.exists() else {}
    out: dict[str, int] = {}
    for m in (data.get("missing") or {}).values():
        out[m.get("fault") or m.get("cause") or "unknown"] = out.get(m.get("fault") or m.get("cause") or "unknown", 0) + 1
    return out


def interface_faults(gdir: Path, verdicts: str) -> dict[str, int]:
    """Items an interface fault left after the rerun: "not met (absent)" where the extraction found nothing in the
    diff addressing them, and "missing" otherwise (Rust grading)."""
    f = gdir / f"{verdicts}.json"
    data = json.loads(f.read_text()) if f.exists() else {}
    got = data.get("interface_faults") or {}
    return {k: len(got.get(k) or []) for k in ("not met (absent)", "missing")}


def share_met(verdicts: dict[str, str], keep=lambda i: True) -> tuple[int, int] | None:
    vs = [v for i, v in verdicts.items() if keep(i) and v not in (grading.MISSING, grading.CONFLICT)]
    return (sum(v == "met" for v in vs), len(vs)) if vs else None


def trajectory_summary(run: Path) -> dict:
    t = json.loads((run / "trajectory.json").read_text())
    changes = {int(n): c for n, c in t["changes"].items()}
    per_change = {}
    for n, c in sorted(changes.items()):
        owners = [json.loads(p.read_text()) for p in sorted((run / f"change-{n:02d}").glob("owner-*.json"))]
        per_change[n] = {"agent_usd": c.get("agent_cost_usd") or 0.0, "owner_usd": c.get("owner_cost_usd") or 0.0,
                         "rounds": c.get("rounds"), "replies": len(owners),
                         "words_shown": sum(o.get("words_shown") or 0 for o in owners),
                         "finished": c.get("finished"), "error": c.get("error"),
                         # a symptom-only change whose diagnostic passed is never delivered: the build never had the bug
                         "skipped": str(c.get("symptom") or "").startswith("not fired"),
                         "symptom": c.get("symptom")}
    out = {"id": t["id"], "arm": t["arm"], "model": t.get("model"), "policy": t.get("policy"), "changes": per_change}
    tp = run / "touchpoints.json"
    if tp.exists():
        kinds: dict[str, int] = {}
        for s in json.loads(tp.read_text())["summary"].values():
            for k, v in s["requests"].items():
                kinds[k] = kinds.get(k, 0) + v
        out["touchpoints"] = kinds
    au = run / "owner-audit.json"
    if au.exists():
        a = json.loads(au.read_text())
        out["audit"] = {"judged": a["judged"], "flagged": a["flagged"],
                        "leaked_items": sorted({l["item"] for r in a["results"] for l in r["leaks"]})}
    return out


def mean(xs):
    xs = [x for x in xs if x is not None]
    return st.mean(xs) if xs else None


def pct(x):
    return "–" if x is None else f"{x:.0%}"


def usd(x):
    return "–" if x is None else f"${x:.2f}"


def build(runs: Path, seed_dir: Path, prefix: str, arms: dict[str, list[str]], verdicts: str,
          exclude: tuple[str, ...] = ()) -> dict:
    """exclude: "trajectory:change:item" entries, items left out of one checkpoint for a recorded harness fault."""
    left_out = {(t, int(c), i) for t, c, i in (e.split(":") for e in exclude)}
    oracle = simulator.parse_oracle((seed_dir / "hidden" / "oracle.md").read_text(encoding="utf-8"))
    kinds = {i.id: kind_of(i) for i in oracle.items}
    bands_file = seed_dir / "hidden" / "bands.json"
    bands = {k: v for k, v in json.loads(bands_file.read_text()).items() if not k.startswith("_")} if bands_file.exists() else {}
    script = simulator.parse_change_script((seed_dir / "hidden" / "change-script.md").read_text(encoding="utf-8"))
    types = {}
    for n, body in re.findall(r"(?m)^## Change (\d+)[^\n]*\n(.*?)(?=^## |\Z)", (seed_dir / "hidden" / "change-script.md").read_text(encoding="utf-8"), re.S):
        m = re.search(r"\*\*Type:\*\*\s*(.+)", body)
        types[int(n)] = m.group(1).strip().split(". ")[0].rstrip(".") if m else ""
    probes = [p for p in grading.parse_probes((seed_dir / "hidden" / "probes.md").read_text(encoding="utf-8")).probes]

    report = {"prefix": prefix, "verdicts": verdicts, "excluded": sorted(exclude), "arms": {}, "changes": {n: {"title": c.title, "type": types.get(n, "")}
                                                                            for n, c in script.items()}}
    for arm, ks in arms.items():
        trajs = []
        for k in ks:
            run = runs / f"{prefix}-{arm}-{k}"
            if not (run / "trajectory.json").exists():
                continue
            s = trajectory_summary(run)
            s["fidelity"] = {}
            for gdir in sorted((run / "grading").glob("change-*")) if (run / "grading").exists() else []:
                v = checkpoint_items(gdir, verdicts, probes)
                if v is None:
                    continue
                n = int(gdir.name.split("-")[1])
                v = {i: x for i, x in v.items() if (f"{arm}-{k}", n, i) not in left_out}
                f = {"all": share_met(v), "not met": sum(x == "not met" for x in v.values()),
                     "couldn't exercise": sum(x == "couldn't exercise" for x in v.values()),
                     "missing": sum(x == grading.MISSING for x in v.values()), "missing by cause": missing_causes(gdir, verdicts),
                     "interface faults": interface_faults(gdir, verdicts),
                     "conflicts": sum(x == grading.CONFLICT for x in v.values()),
                     "by kind": {kd: share_met(v, lambda i, kd=kd: kinds.get(i) == kd) for kd in KINDS},
                     "by band": {b: share_met(v, lambda i, b=b: bands.get(i) == b) for b in ("low", "medium", "high")} if bands else {},
                     "latent items": {i: v.get(i) for i in bands}}
                s["fidelity"][n] = f
            s["probe_forks"] = {}
            for fork in sorted(runs.glob(f"{prefix}-{arm}-{k}-probe*-1")):
                ft = json.loads((fork / "trajectory.json").read_text())
                c = ft["changes"].get("probe", {})
                owners = list((fork / "change-probe").glob("owner-*.json"))
                s["probe_forks"][int(re.search(r"probe(\d+)", fork.name).group(1))] = {
                    "agent_usd": c.get("agent_cost_usd"), "replies": len(owners),
                    "words_shown": sum(json.loads(o.read_text()).get("words_shown") or 0 for o in owners)}
            trajs.append(s)
        report["arms"][arm] = trajs
    return report


def render(r: dict) -> str:
    arms = {a: ts for a, ts in r["arms"].items() if ts}
    lines = [f"# Report: {r['prefix']}", "", f"Verdicts: `{r['verdicts']}.json` in each graded checkpoint. Means over trajectories; "
             "per-trajectory values in brackets. Pilot numbers unless a stage says otherwise.", ""]
    if r.get("excluded"):
        lines += ["Left out for recorded harness faults (trajectory:change:item): " + ", ".join(f"`{e}`" for e in r["excluded"]), ""]

    # fidelity
    graded = sorted({n for ts in arms.values() for t in ts for n in t["fidelity"]})
    lines += ["## Items met", "", "| Arm | " + " | ".join(f"Change {n}" for n in graded) + " |", "|---|" + "---|" * len(graded)]
    for a, ts in arms.items():
        cells = []
        for n in graded:
            xs = [t["fidelity"][n]["all"] for t in ts if n in t["fidelity"] and t["fidelity"][n]["all"]]
            vals = [m / d for m, d in xs]
            cell = f"{pct(mean(vals))} [{', '.join(pct(v) for v in vals)}]" if vals else "–"
            iface = [t["fidelity"][n].get("interface faults") or {} for t in ts if n in t["fidelity"]]
            absent, gone = sum(i.get("not met (absent)", 0) for i in iface), sum(i.get("missing", 0) for i in iface)
            if absent or gone:  # beside the share, whichever way the interface faults went
                cell += f" · interface: {absent} absent, {gone} missing"
            cells.append(cell)
        lines.append(f"| {a} | " + " | ".join(cells) + " |")
    last = graded[-1] if graded else None
    if last is not None:
        lines += ["", f"### At change {last}, by how the owner discloses an item", "",
                  "| Arm | " + " | ".join(KINDS) + " | not met | couldn't exercise |", "|---|" + "---|" * (len(KINDS) + 2)]
        for a, ts in arms.items():
            fs = [t["fidelity"][last] for t in ts if last in t["fidelity"]]
            cells = []
            for kd in KINDS:
                xs = [f["by kind"][kd] for f in fs if f["by kind"][kd]]
                cells.append(f"{pct(mean([m / d for m, d in xs]))} (of {xs[0][1]})" if xs else "–")
            cells.append(f"{mean([f['not met'] for f in fs]):.1f}" if fs else "–")
            cells.append(f"{mean([f['couldn' + chr(39) + 't exercise'] for f in fs]):.1f}" if fs else "–")
            lines.append(f"| {a} | " + " | ".join(cells) + " |")
        if any(f["by band"] for ts in arms.values() for t in ts for f in t["fidelity"].values()):
            lines += ["", f"### At change {last}, latent items by guessability band", "",
                      "| Arm | low | medium | high | stated items |", "|---|---|---|---|---|"]
            for a, ts in arms.items():
                fs = [t["fidelity"][last] for t in ts if last in t["fidelity"]]
                cells = []
                for b in ("low", "medium", "high"):
                    xs = [f["by band"][b] for f in fs if f["by band"].get(b)]
                    cells.append(f"{pct(mean([m / d for m, d in xs]))} ({sum(m for m, _ in xs)}/{sum(d for _, d in xs)})" if xs else "–")
                xs = [f["by kind"]["stated"] for f in fs if f["by kind"]["stated"]]
                cells.append(pct(mean([m / d for m, d in xs])) if xs else "–")
                lines.append(f"| {a} | " + " | ".join(cells) + " |")
            lines += ["", "Each latent item at the last graded change (met ✓ / not met ✗ / couldn't exercise ? / missing ○, per trajectory):", ""]
            items = sorted({i for ts in arms.values() for t in ts for f in t["fidelity"].values() for i in f["latent items"]})
            lines += ["| Arm | " + " | ".join(items) + " |", "|---|" + "---|" * len(items)]
            short = {"met": "✓", "not met": "✗", "couldn't exercise": "?", grading.MISSING: "○", grading.CONFLICT: "!",
                     None: "·"}
            for a, ts in arms.items():
                fs = [t["fidelity"][last] for t in ts if last in t["fidelity"]]
                lines.append(f"| {a} | " + " | ".join("".join(short[f["latent items"].get(i)] for f in fs) for i in items) + " |")

    if any(f.get("missing") or f.get("conflicts") for ts in arms.values() for t in ts for f in t["fidelity"].values()):
        lines += ["", "## Missing items", "",
                  "Items the grader couldn't exercise even on a rerun blind to the arm: left out of items met. "
                  "Totals over trajectories and graded changes; causes count probes.", "",
                  "| Arm | Missing items | Probes by cause | Conflicts (met on an item found absent) |", "|---|---|---|---|"]
        for a, ts in arms.items():
            fs = [f for t in ts for f in t["fidelity"].values()]
            causes: dict[str, int] = {}
            for f in fs:
                for c, k in f.get("missing by cause", {}).items():
                    causes[c] = causes.get(c, 0) + k
            lines.append(f"| {a} | {sum(f.get('missing', 0) for f in fs)} | "
                         + (", ".join(f"{c} {k}" for c, k in sorted(causes.items())) or "–")
                         + f" | {sum(f.get('conflicts', 0) for f in fs)} |")

    # cost and attention
    lines += ["", "## Cost and attention, build plus every change", "",
              "| Arm | Agent cost | Owner (simulator) cost | Owner replies | Words shown to the owner | Leak flags (judged) |",
              "|---|---|---|---|---|---|"]
    base = None
    for a, ts in arms.items():
        agent = [sum(c["agent_usd"] for c in t["changes"].values()) for t in ts]
        owner = [sum(c["owner_usd"] for c in t["changes"].values()) for t in ts]
        replies = [sum(c["replies"] for c in t["changes"].values()) for t in ts]
        words = [sum(c["words_shown"] for c in t["changes"].values()) for t in ts]
        audits = [t.get("audit") for t in ts if t.get("audit")]
        flags = f"{sum(x['flagged'] for x in audits)} ({sum(x['judged'] for x in audits)})" if audits else "–"
        if base is None:
            base = mean(agent)
        lines.append(f"| {a} | {usd(mean(agent))} [{', '.join(usd(x) for x in agent)}] | {usd(mean(owner))} | "
                     f"{mean(replies):.1f} | {mean(words):,.0f} | {flags} |")
    if any(t.get("touchpoints") for ts in arms.values() for t in ts):
        kinds = ("acknowledgement", "lookup", "judgment", "origination", "completion report")
        lines += ["", "### What the agent asked of the owner (mean requests per trajectory)", "",
                  "| Arm | " + " | ".join(kinds) + " |", "|---|" + "---|" * len(kinds)]
        for a, ts in arms.items():
            tps = [t["touchpoints"] for t in ts if t.get("touchpoints")]
            lines.append(f"| {a} | " + " | ".join(f"{mean([tp.get(k, 0) for tp in tps]):.1f}" if tps else "–" for k in kinds) + " |")

    # by change
    numbers = sorted({n for ts in arms.values() for t in ts for n in t["changes"]})
    lines += ["", "## Agent cost by change (mean)", "", "| Change | Type | " + " | ".join(arms) + " |", "|---|---|" + "---|" * len(arms)]
    for n in numbers:
        title = r["changes"].get(n, {}).get("title", "first build" if n == 0 else "")
        typ = r["changes"].get(n, {}).get("type", "")
        cells = []
        for ts in arms.values():
            here = [t["changes"][n] for t in ts if n in t["changes"]]
            ran = [c for c in here if not c["skipped"]]
            if here and not ran:
                why = {"inconclusive" if "inconclusive" in str(c["symptom"]) else "passed" for c in here}
                cells.append("skipped" + ("" if why == {"passed"} else f" ({sum('inconclusive' in str(c['symptom']) for c in here)} inconclusive)"))
            else:
                note = f" ({len(ran)} of {len(here)} ran)" if len(ran) < len(here) else ""
                cells.append(usd(mean([c["agent_usd"] for c in ran])) + note)
        lines.append(f"| {n} {title} | {typ} | " + " | ".join(cells) + " |")
    lines += ["", "\"skipped\": a symptom-only bug report is delivered only if a diagnostic finds the symptom in the build. "
              "\"Passed\" means it found none; \"inconclusive\" means it couldn't tell, and the report wasn't delivered either. "
              "Means are over the trajectories where a change ran."]

    forks = sorted({n for ts in arms.values() for t in ts for n in t["probe_forks"]})
    if forks:
        lines += ["", "## The probe request, forked after each change (mean agent cost; owner replies)", "",
                  "| Arm | " + " | ".join(f"After change {n}" for n in forks) + " |", "|---|" + "---|" * len(forks)]
        for a, ts in arms.items():
            cells = []
            for n in forks:
                fs = [t["probe_forks"][n] for t in ts if n in t["probe_forks"]]
                cells.append(f"{usd(mean([f['agent_usd'] for f in fs]))}; {mean([f['replies'] for f in fs]):.1f}" if fs else "–")
            lines.append(f"| {a} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


SPOT_RULINGS = (*grading.VERDICTS, grading.MISSING)


def load_spot_checks(path: Path) -> list[dict]:
    """Blind spot-check rulings: [{fork, item, ruling, by, note}], each resolving a conflict or overriding a verdict."""
    checks = json.loads(path.read_text(encoding="utf-8"))
    for c in checks:
        for k in ("fork", "item", "ruling"):
            if not c.get(k):
                raise ValueError(f"{path}: a spot-check without {k!r}: {c}")
        if c["ruling"] not in SPOT_RULINGS:
            raise ValueError(f"{path}: ruling {c['ruling']!r} for {c['item']} isn't one of {SPOT_RULINGS}")
    return checks


def _recount(items: dict) -> dict:
    decided = [v for v in items.values() if v and v not in (grading.MISSING, grading.CONFLICT)]
    return {"met": sum(v == "met" for v in decided), "of": len(decided),
            "missing": sum(v == grading.MISSING for v in items.values()),
            "conflicts": sum(v == grading.CONFLICT for v in items.values())}


def fork_report(runs: Path, pattern: str, spot_checks: list[dict] = ()) -> dict:
    """The Rust seed's forks by cell (variant, arm, window): per change, items met of those with a verdict, missing,
    conflicts, held-out retention, tests not built by cause, and the probes version graded under; and per cell, the
    totals."""
    cells: dict[str, dict] = {}
    for run in sorted(runs.glob(pattern)):
        meta_path = run / "trajectory.json"
        if not run.is_dir() or not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text())
        n = meta.get("change")
        g = run / "grading" / f"change-{n:02d}" / "summary.json" if n is not None else None
        if g is None or not g.exists():
            continue
        s = json.loads(g.read_text())
        cell = f"{(meta.get('fork_of') or {}).get('variant')}-{meta.get('arm')}-{meta.get('window')}"
        m, h = s.get("items_met") or {}, s.get("held_out_retention") or {}
        if "tests_not_built_by_cause" not in h and (g.parent / "keeping.json").exists():  # an older summary
            targets = json.loads((g.parent / "keeping.json").read_text()).get("targets") or {}
            h = {**h, "tests_not_built_by_cause": {}}
            for t in targets.values():
                if t.get("compile_failed"):
                    cause = rust_grading.not_built_cause((t.get("adaptation") or {}).get("reason") or (t.get("errors") or [""])[0])
                    h["tests_not_built_by_cause"][cause] = h["tests_not_built_by_cause"].get(cause, 0) + (t.get("tests_expected") or 0)
        items = dict(s.get("items") or {})
        applied = []
        for c in (c for c in spot_checks if c["fork"] == run.name):
            applied.append({"item": c["item"], "was": items.get(c["item"]), "now": c["ruling"], "by": c.get("by"),
                            "note": c.get("note")})
            items[c["item"]] = c["ruling"]
        if applied:
            m = {**m, **_recount(items)}
        row = {"change": n, "met": m.get("met", 0), "of": m.get("of", 0), "missing": m.get("missing", 0),
               "conflicts": m.get("conflicts", 0), "passed": h.get("passed"), "run": (h.get("passed") or 0) + (h.get("failed") or 0),
               "not_built": h.get("tests_not_built_by_cause") or {}, "missing_by_fault": s.get("missing_by_fault") or {},
               "probes": ((s.get("seed_files") or {}).get("probes_sha256") or "")[:7], "items": items,
               "spot_checks": applied}
        c = cells.setdefault(cell, {"changes": [], "total": {"met": 0, "of": 0, "missing": 0, "conflicts": 0,
                                                            "tests_not_built_by_cause": {}, "missing_by_fault": {}}})
        c["changes"].append(row)
        t = c["total"]
        for k in ("met", "of", "missing", "conflicts"):
            t[k] += row[k]
        for k, src in (("tests_not_built_by_cause", row["not_built"]), ("missing_by_fault", row["missing_by_fault"])):
            for cause, x in src.items():
                t[k][cause] = t[k].get(cause, 0) + x
    for c in cells.values():
        c["changes"].sort(key=lambda r: r["change"])
    return {"pattern": pattern, "cells": dict(sorted(cells.items()))}


def render_forks(r: dict) -> str:
    lines = [f"# Forks: {r['pattern']}", "", "Items met counts items with a verdict; missing and conflicts are left out of it. "
             "Retention is held-out tests passed of those run; tests not built are counted by cause.", ""]
    for name, c in r["cells"].items():
        t = c["total"]
        lines += [f"## {name}", "", f"Items met {t['met']}/{t['of']}, missing {t['missing']}"
                  + (f" ({', '.join(f'{k} {x}' for k, x in t['missing_by_fault'].items())})" if t["missing_by_fault"] else "")
                  + f", conflicts {t['conflicts']}; tests not built: "
                  + (", ".join(f"{k} {x}" for k, x in t["tests_not_built_by_cause"].items()) or "none"), "",
                  "| Change | Items met | Missing | Conflicts | Retention | Tests not built | Probes | Spot-checked |",
                  "|---|---|---|---|---|---|---|---|"]
        notes = []
        for row in c["changes"]:
            checked = "; ".join(f"{x['item']}: {x['was']} → {x['now']} ({x['by']})" for x in row.get("spot_checks") or [])
            notes += [f"- Change {row['change']}, {x['item']}: {x['note']}" for x in row.get("spot_checks") or [] if x.get("note")]
            lines.append(f"| {row['change']} | {row['met']}/{row['of']} | {row['missing']} | {row['conflicts']} | "
                         f"{row['passed']}/{row['run']} | {', '.join(f'{k} {x}' for k, x in row['not_built'].items()) or '–'} | "
                         f"{row['probes'] or '–'} | {checked or '–'} |")
        lines += ["", "Spot-checks:", *notes, ""] if notes else [""]
    return "\n".join(lines)


def _json(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


RELIANCE_OUTCOMES = ("current", "displaced", "neither", "both", "undetermined", "no probe")


def _displaced(rows: list[dict]) -> tuple[int, int]:
    """Reliance forks that followed the displaced rule, of those that followed one rule or neither. A fork that met both
    frozen outcomes is inconsistent: counted apart and sent for a spot-check, like a grading conflict."""
    decided = [r for r in rows if r.get("outcome") in ("current", "displaced", "neither")]
    return sum(r["outcome"] == "displaced" for r in decided), len(decided)


INTENT_SOURCES = {"tests": "tests", "tests-neutral": "tests, names replaced", "docs": "docs"}


def intent_reads(runs: Path, tid: str, c: int, arm: str) -> dict | None:
    """A checkpoint's intent from tests and docs (intent_from_tests.py's summary): per source, recall of the items
    the build meets, latent recall of them, recall of met minus the brief-only baseline, stale claims per rule, and
    the share of retired items the reader still states."""
    s = _json(runs / "intent-from-tests" / f"growth-{tid.replace('/', '-')}-c{c:02d}" / "summary.json")
    if not s:
        return None
    out = {}
    for src in INTENT_SOURCES:
        cell = (s.get("cells") or {}).get(f"{arm}|{src}")
        if cell:
            m = cell.get("mean") or {}
            out[src] = {"recall_of_met": m.get("recall_of_met"), "latent_of_met": m.get("by_group_of_met.latent.recall"),
                        "minus_baseline": (cell.get("minus_baseline") or {}).get("recall_of_met"),
                        "stale_per_rule": m.get("rates_per_rule.stale"), "retired_stated": m.get("stale_items_share")}
    return out or None


def growth_report(runs: Path, seed_dir: Path, prefix: str, arms: dict[str, list[str]], checkpoints: list[int]) -> dict:
    """The growth test per trajectory and checkpoint (design.md, "The growth test"). Trajectories are
    <prefix>-<arm>-<k>; a replicate k that isn't a number (the drift floor, g-bare-drift) is its own row and joins no
    replicate's intersection."""
    oracle = simulator.parse_oracle((seed_dir / "hidden" / "oracle.md").read_text(encoding="utf-8"))
    kinds = {i.id: kind_of(i) for i in oracle.items}
    latent = {i for i, k in kinds.items() if k != "stated"}
    probes = grading.parse_probes((seed_dir / "hidden" / "probes.md").read_text(encoding="utf-8")).probes
    script = simulator.parse_change_script((seed_dir / "hidden" / "change-script.md").read_text(encoding="utf-8"))
    symptom_changes = [n for n, ch in sorted(script.items()) if ch.request is None and ch.symptom is not None]
    trajs = {(arm, k): runs / f"{prefix}-{arm}-{k}" for arm, ks in arms.items() for k in ks
             if (runs / f"{prefix}-{arm}-{k}" / "trajectory.json").exists()}
    disclosed: dict[tuple, dict[int, set]] = {}
    for key, run in trajs.items():
        seen, by_change = set(), {}
        for d in sorted(run.glob("change-[0-9][0-9]")):
            n = int(d.name.split("-")[1])
            for o in sorted(d.glob("owner-*.json")):
                seen |= {x["item"] for x in json.loads(o.read_text()).get("shared") or [] if x.get("item")}
            by_change[n] = set(seen)
        disclosed[key] = by_change

    def by(key, c):
        known = [n for n in disclosed[key] if n <= c]
        return disclosed[key][max(known)] if known else set()

    out = {"prefix": prefix, "checkpoints": checkpoints, "arms": {}, "reliance_by_course": {}, "reliance_spot_checks": []}
    seen_forks: set[str] = set()
    for (arm, k), run in trajs.items():
        s, rows, prev_met = trajectory_summary(run), [], None
        for c in checkpoints:
            v = checkpoint_items(run / "grading" / f"change-{c:02d}", "verdicts", probes)
            if v is None:
                continue
            met = {i for i, x in v.items() if x == "met"}
            common = None
            if k.isdigit():
                peers = [key for key in trajs if key[1] == k]
                everywhere = latent & set.intersection(*(by(p, c) for p in peers))
                common = share_met(v, lambda i: i in everywhere) if everywhere else None
            g = run / "growth" / f"checkpoint-{c:02d}"
            rel, flips, stale = _json(g / "reliance.json") or [], _json(g / "flips.json") or [], _json(g / "stale-audit.json")
            cforks = _json(g / "course-forks.json") or []
            real_flips = [f for f in flips if f.get("behaves") is not None]
            anticipations = [f for f in flips if f.get("anticipated") is not None]  # undetermined ones apart
            courses = (stale or {}).get("courses", {}).values()
            spent = [x for n, x in s["changes"].items() if n <= c]
            dollars = sum(x["agent_usd"] + x["owner_usd"] for x in spent)
            hours = growth.owner_hours(sum(x["words_shown"] for x in spent))
            # symptom rows are graded in force from their change whatever happened; whether each report fired is apart
            ran = [n for n in symptom_changes if n <= c and n in s["changes"]]
            unfired = [n for n in ran if s["changes"][n]["skipped"]]
            rows.append({
                "symptom_reports": (len(ran) - len(unfired), len(ran)) if ran else None,
                "graded_unreported": sorted(i for n in unfired for i in simulator.symptom_items(oracle, n) if i in v),
                "checkpoint": c, "stated": share_met(v, lambda i: kinds.get(i) == "stated"),
                "latent": share_met(v, lambda i: i in latent), "latent_disclosed_everywhere": common,
                "keeping": (len(prev_met & met), len(prev_met & set(v))) if prev_met else None,
                "reliance": {o: sum(r.get("outcome") == o for r in rel) for o in RELIANCE_OUTCOMES} if rel else None,
                "displaced_rate": _displaced(rel) if rel else None,
                "flips_behaving": (sum(bool(f.get("behaves")) for f in real_flips), len(real_flips)) if real_flips else None,
                "anticipated": (sum(bool(f["anticipated"]) for f in anticipations), len(anticipations)) if anticipations else None,
                "course_forks_behaving": (sum(f.get("behaves") is True for f in cforks),
                                          sum(f.get("behaves") is not None for f in cforks)) if cforks else None,
                "course_fork_stale_files": sum(f.get("stale") or 0 for f in cforks) if cforks else None,
                "stale_files": (sum(x.get("stale", 0) for x in courses),
                                sum(x.get("stale", 0) + x.get("current", 0) + x.get("mixed", 0) for x in courses)) if stale else None,
                "intent": ((_json(g / "status.json") or {}).get("intent") or {}).get("state"),
                "intent_reads": intent_reads(runs, run.name, c, arm),
                "cost_usd": round(dollars, 4), "cost_per_change": dollars / len(spent) if spent else None,
                "owner_words": sum(x["words_shown"] for x in spent), "owner_hours": hours,
                "met_per_owner_hour": len(met) / hours if hours else None,
                "met_per_dollar": len(met) / dollars if dollars else None})
            prev_met = met
            for row in rel:  # each reliance fork once, under its course change and arm
                if row.get("run") in seen_forks:
                    continue
                seen_forks.add(row.get("run"))
                cell = out["reliance_by_course"].setdefault(str(row.get("course")), {}).setdefault(
                    arm if k.isdigit() else f"{arm} ({k})", {o: 0 for o in RELIANCE_OUTCOMES})
                cell[row.get("outcome") if row.get("outcome") in RELIANCE_OUTCOMES else "undetermined"] += 1
                if row.get("outcome") == "both":
                    out["reliance_spot_checks"].append(row.get("run"))
        label = arm if k.isdigit() else f"{arm} ({k})"
        out["arms"].setdefault(label, []).append({"id": run.name, "replicate": k, "checkpoints": rows})
    return out


def render_growth(r: dict) -> str:
    def ratio(xs):
        xs = [x for x in xs if x]
        return f"{sum(m for m, _ in xs)}/{sum(d for _, d in xs)}" if xs else "–"

    def share(xs):
        vals = [m / d for m, d in (x for x in xs if x) if d]
        return f"{pct(mean(vals))} [{', '.join(pct(v) for v in vals)}]" if vals else "–"

    def num(xs, f="{:.2f}"):
        vals = [x for x in xs if x is not None]
        return f.format(mean(vals)) if vals else "–"
    lines = [f"# Growth: {r['prefix']}", "", "Means over trajectories (per trajectory in brackets); counts summed.", "",
             "- Latent: every kind of item that isn't stated (askable, recognized on sight, emerging, realized on a "
             "symptom). \"Latent disclosed "
             "in every arm\" keeps to the latent items every arm of the replicate had heard by then.",
             "- Keeping: items met at the previous checkpoint that are still graded and still met.",
             "- Flips: each retirement, reversal, re-reversal and rescope, the retired rule failing after it and the new "
             "rule before it. An emerging change's new rule, checked before it, counts as anticipated, never as a flip.",
             "- Course forks behave when the new rule holds and the retired one fails at the fork's end.",
             "- Reliance forks run each course change's reliance request from the trajectory's snapshot after its lag. "
             "Displaced-rule rate: forks that followed the displaced rule, of those that followed the current rule, "
             "the displaced one, or neither. A fork that met both frozen outcomes is inconsistent: counted apart, "
             "outside the rate, and listed for a spot-check.",
             "- Owner-hours at 238 words a minute; fidelity per owner-hour and per dollar count items met.",
             "- A row realized on a symptom is graded in force from its change, as the oracle's lifetime says, whether "
             "or not its report fired; the owner holds it only once the report was delivered. Symptom reports: the "
             "scheduled reports that fired by each checkpoint, and the rows graded though their report never fired.", ""]
    for c in r["checkpoints"]:
        lines += [f"## Change {c}", "", "| Arm | Stated | Latent | Latent disclosed in every arm | Keeping | Displaced-rule rate | "
                  "Flips behaving | Anticipated | Course forks behaving | Stale files (forks) | Cost per change | Owner-hours | "
                  "Met per owner-hour | Met per $ |", "|---|" + "---|" * 14]
        for arm, ts in r["arms"].items():
            rows = [next((x for x in t["checkpoints"] if x["checkpoint"] == c), None) for t in ts]
            rows = [x for x in rows if x]
            if not rows:
                continue
            col = lambda k: [x[k] for x in rows]
            lines.append(f"| {arm} | {share(col('stated'))} | {share(col('latent'))} | {share(col('latent_disclosed_everywhere'))} | "
                         f"{ratio(col('keeping'))} | {ratio(col('displaced_rate'))} | {ratio(col('flips_behaving'))} | "
                         f"{ratio(col('anticipated'))} | {ratio(col('course_forks_behaving'))} | {ratio(col('stale_files'))} "
                         f"({sum(x or 0 for x in col('course_fork_stale_files'))}) | ${num(col('cost_per_change'))} | {num(col('owner_hours'))} | "
                         f"{num(col('met_per_owner_hour'), '{:.1f}')} | {num(col('met_per_dollar'))} |")
        lines.append("")
    symptoms = [(arm, c, rows) for c in r["checkpoints"] for arm, ts in r["arms"].items()
                if (rows := [x for t in ts for x in t["checkpoints"] if x["checkpoint"] == c and x.get("symptom_reports")])]
    if symptoms:
        lines += ["## Symptom reports", "", "| Arm | Checkpoint | Reports fired | Graded though never reported |", "|---|---|---|---|"]
        for arm, c, rows in symptoms:
            unreported = sorted({i for x in rows for i in x.get("graded_unreported") or []})
            lines.append(f"| {arm} | {c} | {ratio([x['symptom_reports'] for x in rows])} | {', '.join(unreported) or '–'} |")
        lines.append("")
    reads = [(c, arm, src, [x["intent_reads"][src] for t in ts for x in t["checkpoints"]
                            if x["checkpoint"] == c and (x.get("intent_reads") or {}).get(src)])
             for c in r["checkpoints"] for arm, ts in r["arms"].items() for src in INTENT_SOURCES]
    reads = [x for x in reads if x[3]]
    if reads:
        lines += ["## Intent from tests and docs", "",
                  "A fresh reader given only the build's tests (as written, or with names, comments and docstrings "
                  "replaced) or its docs, scored against the intent in force (intent_from_tests.py). Means over "
                  "trajectories.", "",
                  "| Change | Arm | Source | Recall of met | Latent of met | Minus brief baseline | Stale claims /rule | "
                  "Retired stated |", "|---|---|---|---|---|---|---|---|"]
        for c, arm, src, xs in reads:
            def m(k, xs=xs):
                return mean([x.get(k) for x in xs])
            stale = m("stale_per_rule")
            lines.append(f"| {c} | {arm} | {INTENT_SOURCES[src]} | {pct(m('recall_of_met'))} | {pct(m('latent_of_met'))} | "
                         f"{pct(m('minus_baseline'))} | {'–' if stale is None else f'{stale:.2f}'} | {pct(m('retired_stated'))} |")
        lines.append("")
    if r.get("reliance_by_course"):
        lines += ["## Reliance forks by course change", "", "| Course change | Arm | Current | Displaced | Neither | Both | "
                  "Undetermined | No probe | Displaced-rule rate |", "|---|---|---|---|---|---|---|---|---|"]
        for course, by_arm in sorted(r["reliance_by_course"].items(), key=lambda kv: int(kv[0])):
            for arm, n in by_arm.items():
                decided = n["current"] + n["displaced"] + n["neither"]
                lines.append(f"| {course} | {arm} | {n['current']} | {n['displaced']} | {n['neither']} | {n['both']} | "
                             f"{n['undetermined']} | {n['no probe']} | {n['displaced']}/{decided} |")
        lines.append("")
    if r.get("reliance_spot_checks"):
        lines += ["## Reliance forks to spot-check", "", "Each met both frozen outcomes, which can't both hold.", ""]
        lines += [f"- {run}" for run in r["reliance_spot_checks"]] + [""]
    return "\n".join(lines)


# ------------------------------------------------------------------------------------------------ the instrument gate

GATE_POINTS = {  # each point's key in the spec's checks, and its expectation where the spec gives none:
    "R+ after C-1": ("r_plus_before", ("met", "not met")),  # (old-row flip, new-row flip)
    "R+ after C": ("r_plus_after", ("not met", "met")),
    "S_C after C+L": ("stale_after_lag", ("met", "not met")),
    "R+ reliance fork": ("rr_r_plus", ("met", "not met")),  # (current, displaced)
    "S_C reliance fork": ("rr_stale", ("not met", "met"))}


def instrument_report(runs: Path, seed_dir: Path, checkpoints=(10, 20, 30, 40), controls=(20, 40)) -> dict:
    """The instrument gate (the seed's reference-builds.md, "How to grade"): for each course change, every grading
    instrument.py makes, each probe's verdict against what the spec expects there; a course change separates the
    builds only when every expectation holds (undecided while a grading is missing). Then R+'s unmet probes at each
    checkpoint, and the positive control's catch rate: of the stale tests planted in R+'s tests, the share each
    reader named as stale, averaged over repeats, per kind and as written or with names replaced."""
    import instrument
    from costeval import reference
    spec = reference.load_spec(seed_dir)
    out = {"courses": [], "outside": [], "mismatches": [], "checkpoints": [], "control": []}
    for c in sorted(int(x) for x in spec["checks"]):
        checks = spec["checks"][str(c)]
        inside = checks.get("gate", True) is not False  # a change the spec puts outside the gate: run, described
        points = []
        for g in instrument.course_gradings(runs, spec, c):
            key, (first, second) = GATE_POINTS[g["point"]]
            if key in checks:  # the spec marks each check's expected verdicts; None: not graded at this point
                if checks[key] is None:
                    continue
                first, second = (checks[key]["old"], checks[key]["new"]) if "reliance" not in g["point"] else (
                    checks[key]["current"], checks[key]["displaced"])
            sides = (checks["flip_old"], checks["flip_new"]) if "reliance" not in g["point"] else (
                [p for p in checks["rr"] if p.endswith("-current")], [p for p in checks["rr"] if p.endswith("-displaced")])
            expected = {p: first for p in sides[0]} | {p: second for p in sides[1]}
            got = instrument.verdicts(instrument.where(runs, g))
            why = (_json(instrument.where(runs, g) / "verdicts.json") or {}).get("not_run_why") or {}
            holds = None if got is None else all(got.get(p) == e for p, e in expected.items())
            points.append({"point": g["point"], "run": g["id"], "expected": expected, "verdicts": got, "holds": holds,
                           "not_run": {p: why[p] for p in expected if p in why}})
            for p, e in expected.items():
                if inside and got is not None and got.get(p) != e:
                    out["mismatches"].append({"course": c, "point": g["point"], "probe": p, "expected": e,
                                              "verdict": "not run" if p in why and p not in got else got.get(p),
                                              "why": why.get(p)})
        held = [x["holds"] for x in points]
        separates = False if False in held else (None if None in held else True)
        row = {"course": c, "kind": spec["stale"][str(c)]["kind"], "lag": spec["stale"][str(c)]["lag"], "points": points}
        if inside:
            out["courses"].append({**row, "separates": separates})
        else:
            out["outside"].append({**row, "note": checks.get("gate_note") or ""})
    for n in checkpoints:
        got = instrument.verdicts(runs / instrument.CORRECT / "grading" / f"change-{n:02d}")
        if got is not None:
            summary = _json(runs / instrument.CORRECT / "grading" / f"change-{n:02d}" / "verdicts.json") or {}
            out["checkpoints"].append({"change": n, "graded": len(got), "unmet": {p: v for p, v in got.items() if v != "met"},
                                       "not_run": dict(summary.get("not_run_why") or {})})
    for n in controls:
        base = runs / instrument.CORRECT / "growth" / f"positive-control-c{n:02d}"
        res = runs / "intent-from-tests" / f"pc-{instrument.CORRECT}-c{n:02d}"
        for kind in ("names", "assertions"):
            idx = _json(base / kind / "index.json")
            if not idx:
                continue
            planted = {v["item"] for v in idx["planted"].values()}
            for neutral in (False, True):
                r = _json(res / (f"pc-{kind}" + ("-neutral" if neutral else "")) / "result.json")
                if not r or not planted:
                    continue
                caught = [len(set(x.get("stale_items") or []) & planted) / len(planted) for x in r.get("repeats") or []]
                out["control"].append({"change": n, "kind": kind, "neutral": neutral, "planted": len(planted),
                                       "catch": sum(caught) / len(caught) if caught else None, "repeats": caught})
    return out


def render_instrument(r: dict) -> str:
    decided = [c for c in r["courses"] if c["separates"] is not None]
    lines = ["# Instrument gate", "",
             "From the seed's reference-builds.md: R+ is the correct build; S_C declines course change C and runs to "
             "C+lag. Each course change separates the builds only when every expected verdict holds at every point. "
             "Any other verdict, \"couldn't exercise\" included, goes to probe review with its execution logs.", "",
             f"Separating: {sum(c['separates'] for c in decided)} of {len(r['courses'])} course changes"
             + (f" ({len(r['courses']) - len(decided)} not yet graded)" if len(decided) < len(r["courses"]) else "") + ".", "",
             "## Course changes", "", "| C | Kind | Lag | Points | Separates |", "|---|---|---|---|---|"]
    for c in r["courses"]:
        pts = "; ".join(f"{p['point']}: {'ok' if p['holds'] else '–' if p['holds'] is None else 'MISMATCH'}" for p in c["points"])
        lines.append(f"| {c['course']} | {c['kind']} | {c['lag']} | {pts} | "
                     f"{'yes' if c['separates'] else 'not yet' if c['separates'] is None else 'NO'} |")
    if r.get("outside"):
        lines += ["", "## Outside the gate", "",
                  "Changes the reference spec leaves out of the gate. Their probes and reliance pairs still run; the "
                  "verdicts are described here and count toward nothing.", ""]
        for c in r["outside"]:
            lines += [f"**Change {c['course']}** ({c['kind']}, lag {c['lag']}). {c['note']}", "",
                      "| C | Point | Probe | Expected | Verdict |", "|---|---|---|---|---|"]
            for p in c["points"]:
                for pid, e in p["expected"].items():
                    v = (p["verdicts"] or {}).get(pid)
                    v = v or ("not run (" + p["not_run"][pid] + ")" if pid in p.get("not_run", {}) else "none")
                    lines.append(f"| {c['course']} | {p['point']} | {pid} | {e} | {v} |")
            lines.append("")
    lines += ["", "## Mismatches, for probe review", ""]
    if r["mismatches"]:
        lines += ["| C | Point | Probe | Expected | Verdict |", "|---|---|---|---|---|"]
        lines += [f"| {m['course']} | {m['point']} | {m['probe']} | {m['expected']} | "
                  f"{(m['verdict'] or 'none') + (' (' + m['why'] + ')' if m.get('why') else '')} |"
                  for m in r["mismatches"]]
    else:
        lines.append("None.")
    lines += ["", "## R+ at the checkpoints", "",
              "Every probe that applies to R+ should be met. An unmet one is a probe a correct build fails, or an R+ "
              "build that missed a stated row: read the run to tell which.", "",
              "| Change | Probes graded | Unmet |", "|---|---|---|"]
    lines += [f"| {x['change']} | {x['graded']} | "
              + (", ".join([f"{p} ({v})" for p, v in sorted(x["unmet"].items())]
                           + [f"{p} (not run: {w})" for p, w in sorted((x.get("not_run") or {}).items())]) or "–") + " |"
              for x in r["checkpoints"]]
    lines += ["", "## Positive control", "",
              "Stale tests planted in R+'s tests; the share of planted rules each intent reader named as stale.", "",
              "| Change | Kind | Reader | Planted | Caught |", "|---|---|---|---|---|"]
    lines += [f"| {x['change']} | {x['kind']} | {'names replaced' if x['neutral'] else 'as written'} | {x['planted']} | "
              f"{pct(x['catch'])} |" for x in r["control"]]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--instrument" in argv:  # report.py --instrument --seed releasedesk-growth --out ../runs/growth/instrument.md
        ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
        ap.add_argument("--instrument", action="store_true")
        ap.add_argument("--seed", default="releasedesk-growth")
        ap.add_argument("--out", required=True)
        args = ap.parse_args(argv)
        r = instrument_report(HERE.parent / "runs", HERE.parent / "seeds" / args.seed)
        out = Path(args.out)
        out.write_text(render_instrument(r), encoding="utf-8")
        out.with_suffix(".json").write_text(json.dumps(r, indent=1), encoding="utf-8")
        print(out.read_text())
        return 0
    if "--growth" in argv:  # report.py --growth --prefix g --seed releasedesk --arms bare:1,2 lid-full:1,2 --checkpoints 10,20
        ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
        ap.add_argument("--growth", action="store_true")
        ap.add_argument("--prefix", default="g")
        ap.add_argument("--seed", default="releasedesk")
        ap.add_argument("--arms", nargs="+", required=True, help="arm:k1,k2 (run ids are <prefix>-<arm>-<k>)")
        ap.add_argument("--checkpoints", default="10,20,30,40")
        ap.add_argument("--out", required=True)
        args = ap.parse_args(argv)
        arms: dict[str, list[str]] = {}
        for a in args.arms:
            name, ks = a.split(":")
            arms.setdefault(name, []).extend(ks.split(","))
        r = growth_report(HERE.parent / "runs", HERE.parent / "seeds" / args.seed, args.prefix, arms,
                          [int(x) for x in args.checkpoints.split(",")])
        out = Path(args.out)
        out.write_text(render_growth(r), encoding="utf-8")
        out.with_suffix(".json").write_text(json.dumps(r, indent=1), encoding="utf-8")
        print(out.read_text())
        return 0
    if "--forks" in argv:  # the Rust seed's forks: report.py --forks 'cf-*-r1' --out ../runs/clowder-pilot/report.md
        ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
        ap.add_argument("--forks", required=True, help="a glob of fork folders under ../runs")
        ap.add_argument("--spot-checks", type=Path, help="blind spot-check rulings: [{fork, item, ruling, by, note}]")
        ap.add_argument("--out", required=True)
        args = ap.parse_args(argv)
        r = fork_report(HERE.parent / "runs", args.forks,
                        spot_checks=load_spot_checks(args.spot_checks) if args.spot_checks else ())
        out = Path(args.out)
        out.write_text(render_forks(r), encoding="utf-8")
        out.with_suffix(".json").write_text(json.dumps(r, indent=1), encoding="utf-8")
        print(out.read_text())
        return 0
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", required=True)
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--arms", nargs="+", required=True, help="arm:1,2,3 (the arm's name in run ids, and trajectory numbers)")
    ap.add_argument("--verdicts", default="verdicts")
    ap.add_argument("--out", required=True)
    ap.add_argument("--exclude", nargs="*", default=[], help="trajectory:change:item entries left out for a recorded harness fault")
    args = ap.parse_args(argv)
    arms = {a.split(":")[0]: a.split(":")[1].split(",") for a in args.arms}
    r = build(HERE.parent / "runs", HERE.parent / "seeds" / args.seed, args.prefix, arms, args.verdicts, tuple(args.exclude))
    out = Path(args.out)
    out.write_text(render(r), encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(r, indent=1, default=str), encoding="utf-8")
    print(out.read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
