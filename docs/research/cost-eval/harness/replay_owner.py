"""Replay recorded owner stops under the current owner prompt, to test a change to the owner's instructions on the
real messages that showed a problem.

    ../plumbing/with-token.sh python3.12 replay_owner.py --before ../runs/stage2/simulator-before.md --repeats 4 \\
        --name leak-fix-1 s2-cheap-discipline-4:change-00/owner-00:-BT-19 s2-lid-full-1:change-00/owner-01:+BT-19

Each stop is `trajectory:change-NN/owner-MM` followed by expectations: `-BT-19` means the reply must not share BT-19,
`+BT-19` means it must still share it (a correction that was earned), and `!words` means the reply must not contain
those words. The recorded prompt is taken from the owner record, and only the lines of the owner's instructions that
differ between `--before` and the current `prompts/simulator.md` are swapped, so the knowledge, the change, and the
agent's message are exactly what the owner saw. The answer then goes through the current trim prompt and the leak
judge. Writes ../runs/stage2/replay-<name>/ and prints a summary.
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


def swap_instructions(prompt: str, before: str, after: str) -> str:
    """Replace each instruction line that changed between the two templates. The templates must have the same
    number of lines, and every changed line must appear in the recorded prompt."""
    b, a = before.splitlines(), after.splitlines()
    if len(b) != len(a):
        raise ValueError("the templates differ in line count; replay needs edits within lines")
    for old, new in zip(b, a):
        if old != new:
            if old not in prompt:
                raise ValueError(f"changed line not in the recorded prompt: {old[:80]}")
            prompt = prompt.replace(old, new)
    return prompt


def agent_message(prompt: str) -> str:
    return prompt.split("<agent_message>\n", 1)[1].split("\n</agent_message>", 1)[0]


def parse_stop(spec: str) -> dict:
    tid, stop, *expect = spec.split(":")
    return {"id": tid, "stop": stop, "must": [e[1:] for e in expect if e.startswith("+")],
            "must_not": [e[1:] for e in expect if e.startswith("-")], "text_not": [e[1:] for e in expect if e.startswith("!")]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stops", nargs="+")
    ap.add_argument("--before", required=True)
    ap.add_argument("--repeats", type=int, default=4)
    ap.add_argument("--name", required=True)
    ap.add_argument("--seed", default="benchtime")
    ap.add_argument("--owner-model", default="claude-sonnet-5-5")
    ap.add_argument("--judge-model", default="claude-opus-5-5")
    ap.add_argument("--after", help="owner template to swap in (default: the current prompts/simulator.md); pass the "
                                    "same file as --before, with --trim-template, for a baseline under the old prompts")
    ap.add_argument("--trim-template", help="trim template (default: the current prompts/owner-trim.md)")
    args = ap.parse_args(argv)
    before = Path(args.before).read_text(encoding="utf-8")
    after = Path(args.after).read_text(encoding="utf-8") if args.after else (HERE / "prompts" / "simulator.md").read_text(encoding="utf-8")
    if args.trim_template:
        simulator.TRIM_TEMPLATE_PATH = Path(args.trim_template).resolve()
    seed = HERE.parent / "seeds" / args.seed
    oracle = simulator.parse_oracle((seed / "hidden" / "oracle.md").read_text(encoding="utf-8"))
    brief = (seed / "brief.md").read_text(encoding="utf-8")
    owner = executor.RoleSession(image=IMAGE, config_volume="ce-roles-cfg", model=args.owner_model,
                                 claude_code_version="2.1.323", effort="medium")
    judge = executor.RoleSession(image=IMAGE, config_volume="ce-roles-cfg", model=args.judge_model,
                                 claude_code_version="2.1.323", effort="medium")
    out_dir = HERE.parent / "runs" / "stage2" / f"replay-{args.name}"
    out_dir.mkdir(parents=True, exist_ok=True)
    stops = [parse_stop(s) for s in args.stops]

    def one(job):
        st, k = job
        rec = json.loads((HERE.parent / "runs" / st["id"] / f"{st['stop']}.json").read_text())
        recorded = [c for c in rec["calls"] if "trim" not in c][-1]["prompt"]
        prompt = swap_instructions(recorded, before, after)
        message = agent_message(prompt)
        r = executor.run_role(owner, prompt, json_schema=simulator.schema_json())
        out = r.structured or {"answers": [], "corrections": []}
        w = simulator.Owner(oracle=oracle, brief=brief, policy="diligent", seed="replay",
                            ask=lambda p: None,
                            trim=lambda p: executor.run_role(owner, p, json_schema=simulator.trim_schema_json()).structured)
        calls: list[dict] = []
        w._trim(message, out, calls)
        reply = "\n\n".join([a["answer"] for a in out["answers"]] + [c["text"] for c in out["corrections"]])
        shared = sorted({i for a in out["answers"] for i in a["items"]} | {c["item"] for c in out["corrections"] if c["item"] != "none"})
        j = executor.run_role(judge, simulator.judge_prompt(prompt, reply, None), json_schema=simulator.judge_schema_json()).structured or {}
        leaks = [d for d in j.get("disclosures", []) if not d["licensed"]]
        problems = [f"lost {i}" for i in st["must"] if i not in shared]
        problems += [f"shared {i}" for i in st["must_not"] if i in shared]
        problems += [f"says {t!r}" for t in st["text_not"] if t.lower() in reply.lower()]
        result = {"stop": f"{st['id']}:{st['stop']}", "k": k, "reply": reply, "shared": shared, "problems": problems,
                  "leaks": leaks, "invented": j.get("invented", []), "trim": calls[0]["trim"] if calls else [],
                  "recorded_reply": rec["reply"]}
        (out_dir / f"{st['id']}--{st['stop'].replace('/', '-')}--{k}.json").write_text(json.dumps(result, indent=1))
        return result

    jobs = [(st, k) for st in stops for k in range(args.repeats)]
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(one, jobs))
    print(f"{'stop':58s} runs  checks failed  judge leaks")
    for st in stops:
        rs = [r for r in results if r["stop"] == f"{st['id']}:{st['stop']}"]
        print(f"{rs[0]['stop']:58s} {len(rs):4d}  {sum(bool(r['problems']) for r in rs):13d}  {sum(bool(r['leaks']) for r in rs):11d}"
              f"   {sorted({p for r in rs for p in r['problems']})} {sorted({l['item'] for r in rs for l in r['leaks']})}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
