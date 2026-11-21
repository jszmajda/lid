"""Measure how guessable each candidate owner rule is, with a cold panel of models from several families.

    ../plumbing/with-token.sh python3.12 guess_panel.py --seed releasedesk --runs 2

Inputs, in the seed's hidden folder: the brief arms will receive (`--brief`, default `../brief-draft.md` beside
`hidden/`, or any path), and `panel-candidates.json`: `{"open_prompts": {stage: prompt}, "candidates": [...]}`,
each candidate with `id`, `rule`, `stage`, `area`, `question`, `options`, `rule_option`, `judge_note`, and, for a
later change the brief doesn't cover, `change_request`.

Each panel model is asked two ways, cold, in separate calls:
- **open design:** the brief (plus the later change, if any) and an open prompt for that stage, never naming a
  candidate. A Sonnet judge then reads each answer and decides, per candidate in that stage, whether the design
  matches the rule, contradicts it, or is silent on it;
- **forced choice:** the brief, the change if any, and one candidate's question, with its options in an order
  shuffled per model, answered as JSON.

Claude models run through `claude -p` in the executor container (on the subscription); others through
call-openrouter (OpenRouter dollars). Everything goes to `hidden/panel/`, and `hidden/panel/summary.json` gives
each candidate's guess rates: how often an open design matched it unprompted, and how often the forced choice
picked the rule's value.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import executor  # noqa: E402

IMAGE = "lid-cost-eval-executor:2.1.323"
PANEL = ["claude:claude-opus-5-5", "claude:claude-sonnet-5-5", "openrouter:openai/gpt-6.1-sol",
         "openrouter:google/gemini-4-carbon", "openrouter:deepseek/deepseek-v4-pro", "openrouter:mistralai/mistral-large-4-0"]
CALL_OPENROUTER = os.environ.get("CALL_OPENROUTER", os.path.expanduser("~/bin/call-openrouter"))
LETTERS = "ABCDEFGH"

JUDGE_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["verdicts"],
                "properties": {"verdicts": {"type": "array", "items": {
                    "type": "object", "additionalProperties": False, "required": ["id", "verdict", "quote"],
                    "properties": {"id": {"type": "string"}, "verdict": {"type": "string", "enum": ["matches", "contradicts", "silent"]},
                                   "quote": {"type": "string"}}}}}}
CHOICE_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["choice", "reason"],
                 "properties": {"choice": {"type": "string"}, "reason": {"type": "string"}}}

ROLE_FRAME = ("You are the developer who will build this service. The owner's brief follows. You have no one to ask: "
              "where the brief leaves something open, decide it the way you would by default.")


def shuffled(options: list[str], key: str) -> tuple[list[str], dict[str, str]]:
    """The options in an order fixed by `key`, and a map from shown letter back to the original letter."""
    order = list(range(len(options)))
    random.Random(key).shuffle(order)
    shown = [options[i] for i in order]
    back = {LETTERS[k]: LETTERS[i] for k, i in enumerate(order)}
    return shown, back


def parse_choice(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    choice = str(d.get("choice", "")).strip().upper()[:1]
    return {"choice": choice, "reason": d.get("reason", "")} if choice in LETTERS else None


def context(brief: str, cand_or_stage: dict | None) -> str:
    text = f"{ROLE_FRAME}\n\n<brief>\n{brief.strip()}\n</brief>"
    if cand_or_stage and cand_or_stage.get("change_request"):
        text += ("\n\nYou built the service from that brief, and it is in use. Now the owner asks for a change:\n\n"
                 f"<change_request>\n{cand_or_stage['change_request'].strip()}\n</change_request>")
    return text


def ask(model: str, prompt: str, schema: dict | None, out: Path) -> str:
    """One cold call. Returns the text (or JSON text) of the answer and keeps the raw record."""
    out.parent.mkdir(parents=True, exist_ok=True)
    kind, name = model.split(":", 1)
    if kind == "claude":
        role = executor.RoleSession(image=IMAGE, config_volume="ce-roles-cfg", model=name, claude_code_version="2.1.323",
                                    effort="medium")
        rec = executor.run_role(role, prompt, json_schema=json.dumps(schema) if schema else None)
        text = json.dumps(rec.structured) if schema else (rec.text or "")
        out.write_text(json.dumps({"model": model, "text": text, "cost_usd": rec.usage.reported_cost_usd}, indent=1))
        return text
    if schema:
        prompt += "\n\nReply with only a JSON object: " + json.dumps({k: "..." for k in schema["required"]})
    for max_tokens in ("16000", "48000"):  # some models ignore the reasoning cap and spend everything on hidden reasoning
        p = subprocess.run([CALL_OPENROUTER, "-m", name, "-f", "-", "--no-stream", "--max-tokens", max_tokens,
                            "--reasoning-max-tokens", "4000", "--out", str(out.with_suffix(".envelope.json"))],
                           input=prompt, capture_output=True, text=True, timeout=1200)
        if p.stdout.strip():
            break
    out.write_text(json.dumps({"model": model, "text": p.stdout, "stderr": p.stderr[-500:]}, indent=1))
    return p.stdout


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", default="releasedesk")
    ap.add_argument("--brief", type=Path, default=None)
    ap.add_argument("--runs", type=int, default=2, help="open-design answers per model and stage")
    ap.add_argument("--models", default=",".join(PANEL))
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)
    hidden = HERE.parent / "seeds" / args.seed / "hidden"
    brief = (args.brief or hidden / "brief-draft.md").read_text(encoding="utf-8")
    spec = json.loads((hidden / "panel-candidates.json").read_text(encoding="utf-8"))
    cands = spec["candidates"]
    models = args.models.split(",")
    out = hidden / "panel"
    jobs = []
    for m in models:
        tag = m.split(":", 1)[1].replace("/", "_")
        for stage, op in spec["open_prompts"].items():
            stage_cands = [c for c in cands if c["stage"] == stage]
            if not stage_cands:
                continue
            ctx = context(brief, None)  # an open prompt for a later change carries its own change request
            for r in range(args.runs):
                jobs.append(("open", m, stage, r, f"{ctx}\n\n{op}", out / "open" / tag / f"{stage.replace(' ', '-')}-{r}.json"))
        for c in cands:
            options = [c["options"][k] for k in sorted(c["options"])] if isinstance(c["options"], dict) else c["options"]
            shown, back = shuffled(options, f"{m}|{c['id']}")
            opts = "\n".join(f"{LETTERS[k]}. {o}" for k, o in enumerate(shown))
            q = (f"{context(brief, c)}\n\n{c['question']}\n\n{opts}\n\nChoose the option your implementation would follow "
                 "by default, and give your reason in one sentence. The `choice` is the option's letter.")
            jobs.append(("choice", m, c["id"], back, q, out / "choice" / tag / f"{c['id']}.json"))

    def run(job):
        kind, m, key, extra, prompt, path = job
        if path.exists():
            return job, json.loads(path.read_text())["text"]
        return job, ask(m, prompt, CHOICE_SCHEMA if kind == "choice" else None, path)

    results = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for job, text in pool.map(run, jobs):
            results.append((job, text))
            print(f"{job[0]:6s} {job[1]:40s} {job[2]}", flush=True)

    judge = executor.RoleSession(image=IMAGE, config_volume="ce-roles-cfg", model="claude-sonnet-5-5",
                                 claude_code_version="2.1.323", effort="medium")
    open_verdicts: dict[str, dict[str, list[str]]] = {c["id"]: {} for c in cands}
    choice_hits: dict[str, dict[str, str | None]] = {c["id"]: {} for c in cands}

    def judge_one(item):
        (kind, m, stage, r, _prompt, path), text = item
        if not (text or "").strip():
            return m, None  # an empty answer is a failed call, not silence, so it is left out
        stage_cands = [c for c in cands if c["stage"] == stage]
        listing = "\n".join(f"- {c['id']}: {c['rule']} (Judge: {c['judge_note']})" for c in stage_cands)
        jpath = path.with_name(path.stem + ".judged.json")
        if jpath.exists():
            return m, json.loads(jpath.read_text())
        prompt = ("Below is a developer's description of how their implementation of a service behaves, and a list of "
                  "owner rules. For each rule, decide whether the description matches it (it states or clearly implies "
                  "the rule's behaviour), contradicts it (it states or clearly implies a different behaviour), or is "
                  "silent on it. Quote the words you rely on, or leave the quote empty if silent.\n\n"
                  f"<description>\n{text.strip()}\n</description>\n\n<rules>\n{listing}\n</rules>")
        rec = executor.run_role(judge, prompt, json_schema=json.dumps(JUDGE_SCHEMA))
        jpath.write_text(json.dumps(rec.structured, indent=1))
        return m, rec.structured

    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for m, judged in pool.map(judge_one, [x for x in results if x[0][0] == "open"]):
            for v in (judged or {}).get("verdicts", []):
                if v["id"] in open_verdicts:
                    open_verdicts[v["id"]].setdefault(m, []).append(v["verdict"])
    for (kind, m, cid, back, _p, _path), text in results:
        if kind != "choice":
            continue
        d = parse_choice(text)
        choice_hits[cid][m] = None if d is None else back.get(d["choice"])
    summary = []
    for c in cands:
        ov = [v for vs in open_verdicts[c["id"]].values() for v in vs]
        ch = [v for v in choice_hits[c["id"]].values() if v]
        rule_opts = set(c["rule_option"]) if isinstance(c["rule_option"], list) else set(str(c["rule_option"]).replace(" ", "").split(","))
        summary.append({"id": c["id"], "title": c.get("title"), "stage": c["stage"],
                        "open": {"matches": ov.count("matches"), "contradicts": ov.count("contradicts"), "silent": ov.count("silent")},
                        "open_match_rate": round(ov.count("matches") / len(ov), 2) if ov else None,
                        "choice": choice_hits[c["id"]], "choice_rule_rate": round(sum(x in rule_opts for x in ch) / len(ch), 2) if ch else None})
    (out / "summary.json").write_text(json.dumps({"models": models, "runs": args.runs, "candidates": summary}, indent=1))
    print(f"\n{'id':5s} {'open match':>10s} {'contra':>6s} {'silent':>6s} {'choice=rule':>11s}  title")
    for s in summary:
        print(f"{s['id']:5s} {str(s['open_match_rate']):>10s} {s['open']['contradicts']:>6d} {s['open']['silent']:>6d} "
              f"{str(s['choice_rule_rate']):>11s}  {s['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
