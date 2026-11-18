"""Summarize a stage's trajectories: fidelity, cost, and the owner's attention, per arm.

    python3.12 report.py --seed benchtime --prefix s2 --verdicts rejudge-v4 \\
        --arms bare:1,2,3 bare-aa:1,2,3 cheap-discipline:4,5,6 lid-full:1,2,3 positive-control:1,2,3 \\
        --out ../runs/stage2/report.md

Reads only what the runs recorded: each trajectory's trajectory.json and owner records, its touchpoints.json and
owner-audit.json where they exist, the verdicts of each graded checkpoint, and its probe-request forks
(`<id>-probeNN-1`). Writes a Markdown report and the same numbers as JSON beside it.

Items met is the share of items with a verdict that are met; "couldn't exercise" counts against it, and probes not
run (deferred needs) leave their items out. A "missing" item (a grader error a rerun didn't resolve) is neither met
nor counted against: it is left out of the share and reported by cause and arm. Items are split by how the owner discloses them (stated, askable,
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

from costeval import grading, simulator  # noqa: E402

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


def share_met(verdicts: dict[str, str], keep=lambda i: True) -> tuple[int, int] | None:
    vs = [v for i, v in verdicts.items() if keep(i) and v != grading.MISSING]
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
            cells.append(f"{pct(mean(vals))} [{', '.join(pct(v) for v in vals)}]" if vals else "–")
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
            short = {"met": "✓", "not met": "✗", "couldn't exercise": "?", grading.MISSING: "○", None: "·"}
            for a, ts in arms.items():
                fs = [t["fidelity"][last] for t in ts if last in t["fidelity"]]
                lines.append(f"| {a} | " + " | ".join("".join(short[f["latent items"].get(i)] for f in fs) for i in items) + " |")

    if any(f.get("missing") for ts in arms.values() for t in ts for f in t["fidelity"].values()):
        lines += ["", "## Missing items", "",
                  "Items the grader couldn't exercise even on a rerun blind to the arm: left out of items met. "
                  "Totals over trajectories and graded changes; causes count probes.", "",
                  "| Arm | Missing items | Probes by cause |", "|---|---|---|"]
        for a, ts in arms.items():
            fs = [f for t in ts for f in t["fidelity"].values()]
            causes: dict[str, int] = {}
            for f in fs:
                for c, k in f.get("missing by cause", {}).items():
                    causes[c] = causes.get(c, 0) + k
            lines.append(f"| {a} | {sum(f.get('missing', 0) for f in fs)} | "
                         + (", ".join(f"{c} {k}" for c, k in sorted(causes.items())) or "–") + " |")

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


def main(argv=None) -> int:
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
