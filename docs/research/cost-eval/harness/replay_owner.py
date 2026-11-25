"""Replay recorded owner stops under the current owner prompt, to test a change to the owner's instructions on the
real messages that showed a problem.

    ../plumbing/with-token.sh python3.12 replay_owner.py --before ../runs/stage2/simulator-before.md --repeats 4 \\
        --name leak-fix-1 s2-cheap-discipline-4:change-00/owner-00:-BT-19 s2-lid-full-1:change-00/owner-01:+BT-19

Each stop is `trajectory:change-NN/owner-MM` followed by expectations: `-BT-19` means the reply must not share BT-19,
`+BT-19` means it must still share it (a correction that was earned), and `!words` means the reply must not contain
those words. The recorded prompt is taken from the owner record, and only the lines of the owner's instructions that
differ between `--before` and the current `prompts/simulator.md` are swapped, so the knowledge, the change, and the
agent's message are exactly what the owner saw. The answer then goes through the current trim prompt and the leak
judge. A replay replays the main call only: it makes no touch call and no recall draws. A broad question's text from
the model is discarded, as a run discards it, and its scope is recorded for inspection. Several answers are shown with
their questions, as in a run. Writes ../runs/stage2/replay-<name>/ and prints a summary.

With --completion-check, it replays the owner's completion check instead (prompts/owner-completion.md: does a message
the main call read as a completion report the change done, or announce work still to do?), on stops named as
`trajectory:change-NN/owner-MM:=work` or `:=done`, and on every change's finished last stop in the runs that
--completions globs match (expected done; --exclude leaves runs out, --sample takes a seeded sample of them):

    ../plumbing/with-token.sh python3.12 replay_owner.py --completion-check --name completion-1 \
        cf-full-lid-full-200k-c01-r1:change-01/owner-04:=work --completions 'cf-*-r1' --exclude cf-full-lid-full-200k-c01-r1
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import random
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
    """The agent's message as the agent wrote it, without the passage numbers the owner was shown."""
    return simulator.strip_passage_marks(prompt.split("<agent_message>\n", 1)[1].split("\n</agent_message>", 1)[0])


def parse_stop(spec: str) -> dict:
    tid, stop, *expect = spec.split(":")
    return {"id": tid, "stop": stop, "must": [e[1:] for e in expect if e.startswith("+")],
            "must_not": [e[1:] for e in expect if e.startswith("-")], "text_not": [e[1:] for e in expect if e.startswith("!")]}


EXPECT = {"work": "work to do", "done": "done"}


def completion_jobs(runs: Path, specs: list[str], globs: list[str], *, exclude=(), sample: int | None = None,
                    seed: str = "replay") -> list[dict]:
    """The stops to check: those named (`tid:change-NN/owner-MM:=work`), then each change's finished last stop in the
    runs the globs match (expected done), less the excluded runs and those named; optionally a seeded sample."""
    def job(tid: str, stop: str, expect: str) -> dict:
        rec = json.loads((runs / tid / f"{stop}.json").read_text())
        return {"stop": f"{tid}:{stop}", "expect": expect, "message": agent_message(rec["calls"][0]["prompt"])}
    jobs = []
    for spec in specs:
        tid, stop, want = spec.split(":")
        jobs.append(job(tid, stop, EXPECT[want.lstrip("=")]))
    named = {s.split(":")[0] for s in specs}
    found = []
    for g in globs:
        for run in sorted(runs.glob(g)):
            if not run.is_dir() or run.name in named or run.name in exclude:
                continue
            for change in sorted(run.glob("change-*")):
                recs = sorted(change.glob("owner-*.json"))
                if not recs:
                    continue
                last = json.loads(recs[-1].read_text())
                if last.get("finished") and last.get("message_kind") == "completion":
                    found.append((run.name, f"{change.name}/{recs[-1].stem}"))
    if sample is not None and sample < len(found):
        found = sorted(random.Random(seed).sample(found, sample))
    return jobs + [job(t, s, "done") for t, s in found]


def run_completion_checks(jobs: list[dict], check, attempts: int = 3) -> tuple[list[dict], dict]:
    """The check on each stop's message, as the owner makes it, and agreement with what each should be."""
    rows, summary = [], {"work to do": {"agree": 0, "of": 0}, "done": {"agree": 0, "of": 0}, "invalid": 0, "cost_usd": 0.0}
    for j in jobs:
        prompt = simulator.completion_check_prompt(j["message"])
        verdict, tries = None, []
        for _ in range(attempts):
            raw, cost = simulator._result(check(prompt))
            summary["cost_usd"] += cost or 0.0
            verdict, problems = simulator.check_completion(raw, j["message"])
            tries.append({"output": raw, "problems": problems})
            if verdict:
                break
        summary[j["expect"]]["of"] += 1
        summary[j["expect"]]["agree"] += verdict == j["expect"]
        summary["invalid"] += verdict is None
        rows.append({**j, "verdict": verdict, "tries": tries})
    summary["cost_usd"] = round(summary["cost_usd"], 4)
    return rows, summary


def completion_main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--completion-check", action="store_true")
    ap.add_argument("stops", nargs="*")
    ap.add_argument("--completions", action="append", default=[], help="a glob of run folders under ../runs")
    ap.add_argument("--exclude", action="append", default=[])
    ap.add_argument("--sample", type=int)
    ap.add_argument("--sample-seed", default="replay")
    ap.add_argument("--name", required=True)
    ap.add_argument("--owner-model", default="claude-sonnet-5-5")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)
    runs = HERE.parent / "runs"
    jobs = completion_jobs(runs, args.stops, args.completions, exclude=args.exclude, sample=args.sample,
                           seed=args.sample_seed)
    role = executor.RoleSession(image=IMAGE, config_volume="ce-roles-cfg", model=args.owner_model,
                                claude_code_version="2.1.323", effort="medium")

    def check(prompt):
        r = executor.run_role(role, prompt, json_schema=simulator.completion_schema_json())
        return r.structured, r.usage.reported_cost_usd or 0.0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:  # one stop each, in parallel
        parts = list(pool.map(lambda j: run_completion_checks([j], check), jobs))
    rows = [r for rs, _ in parts for r in rs]
    summary = {"work to do": {"agree": 0, "of": 0}, "done": {"agree": 0, "of": 0}, "invalid": 0, "cost_usd": 0.0}
    for _, s in parts:
        for k in ("work to do", "done"):
            summary[k]["agree"] += s[k]["agree"]
            summary[k]["of"] += s[k]["of"]
        summary["invalid"] += s["invalid"]
        summary["cost_usd"] = round(summary["cost_usd"] + s["cost_usd"], 4)
    out_dir = runs / "stage2" / f"replay-{args.name}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "completion-check.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1))
    for r in rows:
        if r["verdict"] != r["expect"]:
            print(f"DISAGREE {r['stop']}: expected {r['expect']}, got {r['verdict']}: {(r['tries'][-1]['output'] or {}).get('quote')!r}")
    print(json.dumps(summary, indent=1))
    return 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--completion-check" in argv:
        return completion_main(argv)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stops", nargs="+")
    ap.add_argument("--before", required=True)
    ap.add_argument("--repeats", type=int, default=4)
    ap.add_argument("--name", required=True)
    ap.add_argument("--seed", default="benchtime", help="the seed whose oracle names the item identifiers")
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
    oracle = simulator.parse_oracle((HERE.parent / "seeds" / args.seed / "hidden" / "oracle.md").read_text(encoding="utf-8"))
    ids = simulator.id_pattern(oracle.ids())  # a trimmed part that gains an identifier keeps its old wording
    scripted = {i.id for i in oracle.items if i.response}  # recognized-on-sight responses are never trimmed
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
        broad = [a for a in out.get("answers", []) if a.get("breadth") == "broad"]
        out = {**out, "answers": [a for a in out.get("answers", []) if a.get("breadth", "targeted") != "broad"]}
        calls: list[dict] = []
        simulator.trim_reply(lambda p: executor.run_role(owner, p, json_schema=simulator.trim_schema_json()).structured,
                             message, out, calls, ids=ids, scripted=scripted)
        labels = simulator.label_answers(out["answers"], message)  # only the agent's own words label an answer
        reply = "\n\n".join(simulator.answer_lines(out["answers"]) + [c["text"] for c in out["corrections"]])
        shared = sorted({i for a in out["answers"] for i in a["items"]} | {c["item"] for c in out["corrections"] if c["item"] != "none"})
        j = executor.run_role(judge, simulator.judge_prompt(prompt, reply, None), json_schema=simulator.judge_schema_json()).structured or {}
        leaks = [d for d in j.get("disclosures", []) if not d["licensed"]]
        problems = [f"lost {i}" for i in st["must"] if i not in shared]
        problems += [f"shared {i}" for i in st["must_not"] if i in shared]
        problems += [f"says {t!r}" for t in st["text_not"] if t.lower() in reply.lower()]
        result = {"stop": f"{st['id']}:{st['stop']}", "k": k, "reply": reply, "shared": shared, "problems": problems,
                  "leaks": leaks, "invented": j.get("invented", []), "trim": calls[0]["trim"] if calls else [],
                  "label_repairs": labels, "broad": [{"question": a.get("question"), "in_scope": a.get("in_scope", [])}
                                                               for a in broad],
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
