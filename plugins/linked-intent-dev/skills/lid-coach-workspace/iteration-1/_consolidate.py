#!/usr/bin/env python3
"""Write timing.json + grading.json for all 16 lid-coach iteration-1 runs.

Verdicts are graded from the captured subagent report text against the
assertions in evals/evals.json. with_skill verdicts are authoritative for
the spec-flip analysis; baseline (without_skill) verdicts feed the delta.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).parent

# (tokens, duration_ms) keyed by (eval_id, config)
TIMING = {
    (0, "with_skill"): (35313, 56091), (0, "without_skill"): (21195, 56586),
    (1, "with_skill"): (39128, 83354), (1, "without_skill"): (24100, 82789),
    (2, "with_skill"): (36326, 57468), (2, "without_skill"): (24806, 90970),
    (3, "with_skill"): (38818, 88194), (3, "without_skill"): (25334, 108004),
    (4, "with_skill"): (41524, 124868), (4, "without_skill"): (44064, 159791),
    (6, "with_skill"): (40004, 92232), (6, "without_skill"): (26140, 109114),
    (7, "with_skill"): (39073, 75514), (7, "without_skill"): (41978, 123756),
    (5, "with_skill"): (42292, 143120), (5, "without_skill"): (44674, 163382),
}

# passed-bool list per (eval_id, config), index-aligned to evals.json assertions
VERDICTS = {
    (0, "with_skill"): [True, True, True],
    (0, "without_skill"): [True, True, True],
    (1, "with_skill"): [True, True, True, True, True, True, True, True, True, True, True, True, True],
    (1, "without_skill"): [False, False, False, False, True, False, True, True, False, True, True, True, True],
    (2, "with_skill"): [True, True, True],
    (2, "without_skill"): [True, False, True],
    (3, "with_skill"): [True, True, True],
    (3, "without_skill"): [True, True, True],
    (4, "with_skill"): [True, True, True],
    (4, "without_skill"): [True, True, True],
    (6, "with_skill"): [True, True, True, True, True, True],
    (6, "without_skill"): [True, True, False, False, True, True],
    (7, "with_skill"): [True, True, True, True, True],
    (7, "without_skill"): [True, True, False, True, True],
    (5, "with_skill"): [True, True],
    (5, "without_skill"): [True, True],
}

EV = {
    (0, "with_skill"): ["Refused principle review, declared project not LID-configured (empty dir).",
                        "Recommended /update-lid and /linked-intent-dev; no /lid-setup.",
                        "Reported NONE; project dir untouched."],
    (0, "without_skill"): ["Stated project not started/empty; no principle review attempted.",
                           "Recommended /linked-intent-dev; no /lid-setup mention.",
                           "Reported NONE."],
    (1, "with_skill"): ["Single inline report: exec summary -> findings inventory -> what audited -> offer-to-help.",
                        "Inventory entries are one-line bullets, no detail paragraphs.",
                        "F1..F5 one line each: priority+title+principle.",
                        "Offer-to-help has review-followup line AND broader-LID-usage line.",
                        "Posture 'Healthy bootstrap' — categorical, no number.",
                        "'Scorecard' section, bulleted, OK/WARN markers + word labels.",
                        "'dimensional strip' absent.",
                        "Headline leads with 'intent layers you've authored are genuinely clean'.",
                        "What-was-audited carries counts (1 HLD/1 LLD/2 EARS/0 code).",
                        "No numeric grades anywhere.",
                        "No out-of-scope section (Full mode).",
                        "No 'violation/failure/wrong/broken/fails to'.",
                        "Reported NONE."],
    (1, "without_skill"): ["Verdict+table+Strengths+Findings(paragraphs) — not the prescribed section set / no offer-to-help.",
                           "Renders multi-line finding paragraphs.",
                           "Findings are numbered paragraphs, not one-line inventory.",
                           "No offer-to-help with two pathways.",
                           "'Verdict: Healthy' categorical, no number.",
                           "No 'Scorecard' section.",
                           "'dimensional strip' absent (trivial).",
                           "Strengths/positive verdict precede issues.",
                           "No what-was-audited section with counts.",
                           "No numeric grades.",
                           "No out-of-scope section.",
                           "Coach-ish voice; no banned words.",
                           "Reported NONE."],
    (2, "with_skill"): ["F1 flags HLD schema/API/function bloat.",
                        "Cites '*HLD is architecture and rationale*' by name.",
                        "Headline + offer recommend lifting detail into LLDs/EARS."],
    (2, "without_skill"): ["Flags HLD bloat (schema/API/function) strongly.",
                           "Explains 'HLD answers why' but does not cite a named LID principle.",
                           "Recommends moving detail into LLDs/specs/code."],
    (3, "with_skill"): ["F1/F2/F3 flag History/Changelog, was-X-now-Y, [obsolete].",
                        "Cites principle by new name '*docs carry current intent...*' with inline gloss (NOTE: assertion text says 'mutation-not-accumulation' — principle was renamed this session; semantically correct).",
                        "F3 'delete obsolete specs'; constructive 'accumulation sweep' phrasing; no banned words."],
    (3, "without_skill"): ["Flags all accumulation residue across HLD/LLD/spec.",
                           "Cites 'Mutation, not accumulation' by name with gloss.",
                           "Recommends deleting obsolete content; phrasing acceptably constructive."],
    (4, "with_skill"): ["F1 high: Scoped declared, no ## LID Scope.",
                        "Recommends /update-lid to add scope section.",
                        "Ran conservative project-wide review, not refused."],
    (4, "without_skill"): ["Flagged missing ## LID Scope as high priority.",
                           "Recommended /update-lid.",
                           "Proceeded with project-wide review."],
    (6, "with_skill"): ["Explicit dispatch note: 'drift to surface, not a reason to refuse'.",
                        "F1 high names precursor 'Design-Driven Development' / missing directives.",
                        "Headline recommends /update-lid to install directive block.",
                        "Posture categorical, no numeric.",
                        "Acknowledges populated HLD/LLD/spec/index as 'doing LID' before drift.",
                        "Reported NONE."],
    (6, "without_skill"): ["Did not refuse; reviewed the LID-shaped project.",
                           "Flags CLAUDE.md 'thin and mislabeled' (precursor naming).",
                           "No /update-lid recommendation (says walk arrow forward).",
                           "No categorical posture line (coherence-list format).",
                           "'What's here' acknowledges LID-shaped first.",
                           "Reported NONE."],
    (7, "with_skill"): ["What-was-audited: 'Read fully: ... docs/arrows/index.yaml'; index read first.",
                        "F2 high cites the index.yaml ingestion drift (ING-001 [x], no test).",
                        "One-line inventory only; no detailed finding paragraphs.",
                        "No numeric grades; counts in what-was-audited.",
                        "Reported NONE."],
    (7, "without_skill"): ["Read index.yaml; what-was-audited lists it.",
                           "Heavily flags ingestion drift from index.yaml.",
                           "Includes a long 'Detail on the load-bearing finding' paragraph — violates one-line-inventory.",
                           "No numeric grades.",
                           "Reported NONE."],
    (5, "with_skill"): ["Produced review, explicitly declined edits (NONE).",
                        "Dedicated 'On your request to fix' section; points at /linked-intent-dev + /update-lid."],
    (5, "without_skill"): ["Produced review, declined edits (NONE).",
                           "Explained advisory posture; pointed at /update-lid + /linked-intent-dev."],
}

EVALS = {e["id"]: e for e in json.loads(
    (ROOT.parent.parent / "lid-coach" / "evals" / "evals.json").read_text())["evals"]}

dir_by_id = {}
for p in ROOT.iterdir():
    if p.is_dir() and p.name.startswith("eval-"):
        eid = int(p.name.split("-")[1])
        dir_by_id[eid] = p

for (eid, cfg), (tokens, dur) in TIMING.items():
    rundir = dir_by_id[eid] / cfg
    (rundir / "timing.json").write_text(json.dumps(
        {"total_tokens": tokens, "duration_ms": dur,
         "total_duration_seconds": round(dur / 1000, 1)}, indent=2))
    assertions = EVALS[eid]["assertions"]
    verdicts = VERDICTS[(eid, cfg)]
    ev = EV[(eid, cfg)]
    exps = [{"text": a["text"], "passed": v, "evidence": e}
            for a, v, e in zip(assertions, verdicts, ev)]
    (rundir / "grading.json").write_text(json.dumps(
        {"run_id": f"eval-{eid}-{cfg}",
         "expectations": exps,
         "passed": sum(verdicts), "total": len(verdicts)}, indent=2))

ws = [(eid, sum(VERDICTS[(eid, "with_skill")]), len(VERDICTS[(eid, "with_skill")]))
      for eid in sorted(dir_by_id)]
wos = [(eid, sum(VERDICTS[(eid, "without_skill")]), len(VERDICTS[(eid, "without_skill")]))
       for eid in sorted(dir_by_id)]
tw, nw = sum(p for _, p, _ in ws), sum(n for _, _, n in ws)
tb, nb = sum(p for _, p, _ in wos), sum(n for _, _, n in wos)
print("eval | with_skill | baseline")
for (eid, pw, nwt), (_, pb, nbt) in zip(ws, wos):
    print(f"  {eid}: {pw}/{nwt}   vs   {pb}/{nbt}")
print(f"TOTAL with_skill {tw}/{nw}  baseline {tb}/{nb}")
