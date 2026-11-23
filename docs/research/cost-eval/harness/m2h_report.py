"""The M2h joint-outcome report (seeds/opengym/hidden/m2h-plan.md, "Joint outcome"; m2h-harness-needs.md): for every
graded main fork (m2h-<arm>-cNN-rK; never a null, right or repair fork), whether the change was implemented (yes:
every stated non-guard new row met; partly; no; N/A where the plan says so) against what became of the dependent
behaviour (kept, broken, not exercised, or missing), from grade_node.py's summary.

    python3.12 m2h_report.py --forks 'm2h-*-r[0-9]' --out ../runs/opengym-m2h/m2h.md

Per fork, per change and arm, pooled per arm, and by searchability tier (documented, one-step grep, hidden; the
changes the seed reports both ways, 3 and 8, are also left out of the documented tier in a row of their own), the joint
counts over all forks and breakage among implemented forks: broken / (kept + broken), over "implemented: yes". A
dependency that wasn't exercised is never counted as kept. With each, the forks' agent cost and turns. Writes the
Markdown report and the same numbers as JSON beside it.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN = Path("/Users/jess/src/lid-cost-eval/docs/research/cost-eval")
IMPLEMENTED = ("yes", "partly", "no", "N/A", "undecided")
DEPENDENT = ("kept", "broken", "not exercised", "missing")
TIERS = ("documented", "one-step grep", "hidden")
FORK = re.compile(r"m2h-(bare|lid)-c(\d\d)-r(\d+)")


def _json(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def _arm(meta: dict, fid: str) -> str:
    m = FORK.fullmatch(fid)
    return m.group(1) if m else ("bare" if meta.get("arm") == "bare" else "lid")


def tally(forks: list[dict]) -> dict:
    joint = {i: {d: 0 for d in DEPENDENT} for i in IMPLEMENTED}
    for f in forks:
        joint[f["implemented"]][f["dependent"]] += 1
    yes = joint["yes"]
    costs = [f["agent_cost_usd"] for f in forks if f["agent_cost_usd"] is not None]
    turns = [f["turns"] for f in forks if f["turns"] is not None]
    return {"forks": len(forks), "joint": joint, "breakage_among_implemented": [yes["broken"], yes["kept"] + yes["broken"]],
            "agent_cost_mean": st.mean(costs) if costs else None, "turns_mean": st.mean(turns) if turns else None}


def build(runs: Path, pattern: str, kept: dict) -> dict:
    forks = []
    for d in sorted(runs.glob(pattern)):
        m = FORK.fullmatch(d.name)
        meta = _json(d / "trajectory.json") or {}
        if not m or meta.get("arm") == "null":
            continue
        n = int(m.group(2))
        s = _json(d / "grading" / f"change-{n:02d}" / "summary.json")
        if s is None:
            continue
        joint = s.get("joint") or {}
        change = kept.get(str(n)) or {}
        done = (meta.get("changes") or {}).get(str(n)) or {}
        implemented = joint.get("implemented")
        forks.append({"id": d.name, "arm": _arm(meta, d.name), "change": n, "repeat": int(m.group(3)),
                      "tier": joint.get("tier") or (change.get("searchability") or {}).get("tier"),
                      "implemented": implemented if implemented in IMPLEMENTED else "undecided",
                      "dependent": joint.get("dependent_behaviour") if joint.get("dependent_behaviour") in DEPENDENT
                      else ((s.get("dependency") or {}).get("result") if (s.get("dependency") or {}).get("result")
                            in DEPENDENT else "missing"),
                      "agent_cost_usd": done.get("agent_cost_usd"), "turns": done.get("rounds"),
                      "notes": {k: v for k, v in joint.items() if k in ("implemented_without_coupled", "beside_dependency",
                                                                        "storage") and v is not None}})
    both_ways = sorted(int(n) for n, c in kept.items() if (c.get("searchability") or {}).get("pooled_with_and_without"))
    out = {"pattern": pattern, "forks": forks, "both_ways": both_ways, "arms": {}, "changes": {}}
    for arm in sorted({f["arm"] for f in forks}):
        mine = [f for f in forks if f["arm"] == arm]
        a = tally(mine)
        a["by_tier"] = {}
        for tier in TIERS:
            in_tier = [f for f in mine if f["tier"] == tier]
            a["by_tier"][tier] = tally(in_tier)
            left_out = [n for n in both_ways if any(f["change"] == n for f in in_tier)]
            if left_out:
                a["by_tier"][f"{tier} (without {', '.join(map(str, left_out))})"] = tally(
                    [f for f in in_tier if f["change"] not in left_out])
        out["arms"][arm] = a
    for n in sorted({f["change"] for f in forks}):
        out["changes"][str(n)] = {arm: tally([f for f in forks if f["change"] == n and f["arm"] == arm])
                                  for arm in sorted({f["arm"] for f in forks if f["change"] == n})}
    return out


def render(r: dict, kept: dict) -> str:
    rate = lambda b: f"{b[0]}/{b[1]}" if b[1] else "–"  # noqa: E731
    money = lambda x: f"${x:.2f}" if x is not None else "–"  # noqa: E731
    lines = [f"# M2h: joint outcome ({r['pattern']})", "",
             "- Implemented: yes when every stated non-guard new row is met, partly when some are, no when none are; N/A "
             "where the plan says so (change 3's score without OGM-0301 and OGM-0302).",
             "- Dependent behaviour: kept, broken or not exercised, from the change's dependency probes (a control's, its "
             "comparison row); missing when a probe's setup failed. A dependency that wasn't exercised is never counted "
             "as kept.",
             "- Breakage among implemented forks: broken / (kept + broken), over the forks implemented: yes.",
             f"- Changes reported with and without in their tier: {', '.join(map(str, r['both_ways'])) or 'none'}.", "",
             "## Joint outcome, pooled", "",
             "| Arm | Breakage among implemented | Forks | " + " | ".join(f"yes, {d}" for d in DEPENDENT)
             + " | Partly | No | N/A | Undecided | Agent cost, mean | Turns, mean |", "|---" * 13 + "|"]
    for arm, a in r["arms"].items():
        j = a["joint"]
        turns = "–" if a["turns_mean"] is None else f"{a['turns_mean']:.1f}"
        lines.append(f"| {arm} | {rate(a['breakage_among_implemented'])} | {a['forks']} | "
                     + " | ".join(str(j["yes"][d]) for d in DEPENDENT)
                     + f" | {sum(j['partly'].values())} | {sum(j['no'].values())} | {sum(j['N/A'].values())} | "
                       f"{sum(j['undecided'].values())} | {money(a['agent_cost_mean'])} | {turns} |")
    lines += ["", "## By searchability tier", "", "| Arm | Tier | Forks | Breakage among implemented | Kept | Broken | "
              "Not exercised | Missing |", "|---|---|---|---|---|---|---|---|"]
    for arm, a in r["arms"].items():
        for tier, t in a["by_tier"].items():
            if not t["forks"]:
                continue
            tot = {d: sum(t["joint"][i][d] for i in IMPLEMENTED) for d in DEPENDENT}
            lines.append(f"| {arm} | {tier} | {t['forks']} | {rate(t['breakage_among_implemented'])} | "
                         + " | ".join(str(tot[d]) for d in DEPENDENT) + " |")
    lines += ["", "## By change", "", "| Change | Title | Arm | Forks | Breakage among implemented | Implemented yes / "
              "partly / no | Kept | Broken | Not exercised | Missing |", "|---|---|---|---|---|---|---|---|---|---|"]
    for n, by_arm in r["changes"].items():
        for arm, t in by_arm.items():
            j = t["joint"]
            tot = {d: sum(j[i][d] for i in IMPLEMENTED) for d in DEPENDENT}
            lines.append(f"| {n} | {(kept.get(n) or {}).get('title', '')} | {arm} | {t['forks']} | "
                         f"{rate(t['breakage_among_implemented'])} | {sum(j['yes'].values())} / {sum(j['partly'].values())} / "
                         f"{sum(j['no'].values())} | " + " | ".join(str(tot[d]) for d in DEPENDENT) + " |")
    lines += ["", "## Forks", "", "| Fork | Arm | Change | Repeat | Tier | Implemented | Dependent behaviour | Agent cost | "
              "Turns | Notes |", "|---|---|---|---|---|---|---|---|---|---|"]
    for f in r["forks"]:
        notes = "; ".join(f"{k}: {v}" for k, v in f["notes"].items())
        lines.append(f"| {f['id']} | {f['arm']} | {f['change']} | {f['repeat']} | {f['tier'] or '–'} | {f['implemented']} | "
                     f"{f['dependent']} | {money(f['agent_cost_usd'])} | {f['turns'] if f['turns'] is not None else '–'} | "
                     f"{notes or '–'} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    ap.add_argument("--forks", default="m2h-*-r[0-9]")
    ap.add_argument("--seed-files", type=Path, default=MAIN / "seeds" / "opengym" / "hidden" / "m2h")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    kept = _json(args.seed_files / "kept-behaviour.json") or {}
    r = build(args.runs, args.forks, kept)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(r, kept), encoding="utf-8")
    args.out.with_suffix(".json").write_text(json.dumps(r, indent=1), encoding="utf-8")
    print(args.out.read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
