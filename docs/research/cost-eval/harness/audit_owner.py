"""Run the leak judge over a trajectory's owner replies, so leaks are measured in real runs, not only in the
simulator's fixed scenarios.

    ../plumbing/with-token.sh python3.12 audit_owner.py --id s0-bare [--all]

By default only replies that shared something or answered a question are judged; --all judges every reply.
Also counts, over every owner reply, the slips in the model's output that the harness repaired instead of retrying.
Writes ../runs/<id>/owner-audit.json.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import executor, simulator  # noqa: E402

IMAGE = "lid-cost-eval-executor:2.1.323"


def repairs_in(rec: dict) -> int:
    """How many slips the harness repaired, instead of retrying, across one owner record's model calls (the main and
    trim calls, and the touch calls)."""
    return sum(len(c.get("repairs") or []) for c in (rec.get("calls") or []) + (rec.get("touch_calls") or []))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True)
    ap.add_argument("--seed", default="benchtime")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--judge-model", default="claude-opus-5-5")
    args = ap.parse_args(argv)
    run = HERE.parent / "runs" / args.id
    script = simulator.parse_change_script((HERE.parent / "seeds" / args.seed / "hidden" / "change-script.md").read_text(encoding="utf-8"))
    judge = executor.RoleSession(image=IMAGE, config_volume="ce-roles-cfg", model=args.judge_model,
                                 claude_code_version="2.1.323", effort="medium")
    jobs = []
    repairs: dict[str, int] = {}  # every owner record's repairs, judged or not
    for path in sorted(run.glob("change-*/owner-*.json")):
        rec = json.loads(path.read_text())
        if repairs_in(rec):
            repairs[f"{path.parent.name}/{path.stem}"] = repairs_in(rec)
        if not (args.all or rec["shared"] or rec["answers"]):
            continue
        prompt = [c for c in rec["calls"] if "trim" not in c][-1]["prompt"]
        n = int(path.parent.name.split("-")[1])
        scripted = script[n].redirect.text if rec.get("redirect_event") == "delivered" and n in script and script[n].redirect else None
        # The judge is told which recall lines the harness drew, and for which items, so it licenses them.
        jobs.append((path, rec, simulator.judge_prompt(prompt, rec["reply"], scripted, recalled=rec.get("recalled") or [])))

    def go(job):
        path, rec, prompt = job
        r = executor.run_role(judge, prompt, json_schema=simulator.judge_schema_json())
        j = r.structured or {}
        return {"stop": f"{path.parent.name}/{path.stem}", "reply": rec["reply"], "shared": rec["shared"],
                "repairs": repairs_in(rec),
                "leaks": [d for d in j.get("disclosures", []) if not d["licensed"]], "invented": j.get("invented", []),
                "judge": j, "cost_usd": r.usage.reported_cost_usd}

    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(go, jobs))
    flagged = [r for r in results if r["leaks"] or r["invented"]]
    out = {"judged": len(results), "flagged": len(flagged), "repairs": sum(repairs.values()), "repairs_by_stop": repairs,
           "results": results}
    (run / "owner-audit.json").write_text(json.dumps(out, indent=1))
    print(f"{args.id}: judged {len(results)} replies, {len(flagged)} flagged, {sum(repairs.values())} repairs "
          f"in {len(repairs)} owner replies")
    for r in flagged:
        print(f"  {r['stop']}: leaks {[l['item'] for l in r['leaks']]} invented {len(r['invented'])}")
        for l in r["leaks"]:
            print(f"     {l['item']}: {l['why'][:200]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
