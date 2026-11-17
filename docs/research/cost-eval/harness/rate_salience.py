"""Rate the salience of every recall-eligible item in a seed, blind, with several model families, and draft each
item's recall line.

    python3.12 rate_salience.py --seed benchtime --samples 3            # ratings
    python3.12 rate_salience.py --seed benchtime --recall-lines          # recall-line drafts (GPT-6.1 Sol)

Raters see only the owner's narrative and each item's text: no probes, no arms, no results. Calls go through
OpenRouter with ~/bin/call-openrouter (real dollars). Writes seeds/<seed>/hidden/salience/: each raw reply,
ratings.json (every sample, each rater's median, the item's median tier, and quadratic-weighted kappa between
raters), and recall-lines.json. The tiers and lines become owner-items.json only after review.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import re
import statistics as st
import subprocess
import sys
from itertools import combinations
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import simulator  # noqa: E402

RATERS = ["openai/gpt-6.1-sol", "google/gemini-4-carbon", "deepseek/deepseek-v4-pro", "mistralai/mistral-large-4-0"]
TIERS = {"low": 0, "medium": 1, "high": 2}
CALL = str(Path.home() / "bin" / "call-openrouter")

RUBRIC = """You are helping set up a study in which a model plays the owner of a software project. Below is what the owner knows about their own project, in their words, and a list of rules the owner holds but has not said to the developer.

For each rule, answer one question: **how often, in this owner's ordinary work, does a situation come up in which this rule decides what should happen?**

Count how often the rule itself matters, not how often the feature it belongs to is used. A rule about what happens when something is edited after it was published matters only when that happens, even if publishing happens every day.

- **high:** weekly or more. The rule decides something in the owner's routine, so it comes to mind without prompting.
- **medium:** occasionally. The rule matters in some cases that come up now and then.
- **low:** rarely. An edge case, a sequence of events that seldom happens, a process step, an auxiliary mechanic, or a non-functional or style concern.

Examples from an unrelated business, a bakery taking online orders:
- "Orders close at 18:00" is **high**: it decides something every day.
- "A cancelled order frees its oven slot" is **medium**: cancellations happen some days.
- "An order edited after it was baked keeps its original price" is **low**: that sequence is rare.

Rate how readily the rule comes to the owner's mind, not how much it matters. A high-stakes background assumption can be low: people often never think of the things they take for granted.

## What the owner knows, in their own words

{NARRATIVE}

## The rules to rate

{ITEMS}

Return only JSON, with no other text before or after it, and no line breaks inside strings: {"ratings": [{"item": "<identifier>", "tier": "low" | "medium" | "high", "why": "<one short sentence>"}]}, one entry per rule, in the order given."""

RECALL = """You are helping set up a study in which a model plays the owner of a software project. Below is what the owner knows about their own project, in their words, and a list of rules the owner holds but has not said to the developer.

During a review, something the developer shows may remind the owner of one of these rules. For each rule, write the one sentence the owner would say on being reminded, in a reply to the developer.

Write it the way a busy person who runs this place would say it:
- plain words, in the owner's voice, about their own work ("we", "our staff", "visitors");
- the main point of the rule, as the owner would put it. Leave out fine boundaries and exceptions unless they are the point. The developer can ask about details;
- nothing the rule doesn't say: no added cases, no examples of what follows from it, no numbers or boundaries the rule doesn't state;
- true as far as it goes: it must not suggest anything the rule contradicts;
- no mention of other rules, no identifiers, and no reference to the developer's document.

Example from an unrelated business, a bakery taking online orders. For the rule "A cancelled order frees its oven slot unless it is cancelled within an hour of baking", a good sentence is "When someone cancels, their oven slot should open up again." A bad one is "I free the oven slot of any cancelled order, inclusive of all order types, except within one hour of baking": it isn't how a person talks, and it hands over the boundary.

## What the owner knows, in their own words

{NARRATIVE}

## The rules

{ITEMS}

Return only JSON, with no other text before or after it: {"lines": [{"item": "<identifier>", "line": "<the sentence>"}]}, one entry per rule, in the order given."""


def eligible(oracle: simulator.Oracle) -> list[simulator.Item]:
    out = []
    for i in oracle.items:
        if i.in_force is None:
            continue
        try:
            if i.share == "Askable":
                out.append(i)
        except ValueError:
            continue
    return out


def narrative(oracle: simulator.Oracle) -> str:
    return "\n\n".join(oracle.narrative[n] for n in sorted(oracle.narrative))


def prompt(template: str, oracle: simulator.Oracle, items: list[simulator.Item]) -> str:
    listing = "\n".join(f"- **{i.id}:** {i.behavior}" for i in items)
    return template.replace("{NARRATIVE}", narrative(oracle)).replace("{ITEMS}", listing)


def call(model: str, prompt_file: Path, out_json: Path) -> str:
    p = subprocess.run([CALL, "-m", model, "-f", str(prompt_file), "--reasoning-max-tokens", "8000", "--max-tokens", "24000",
                        "--no-stream", "--out", str(out_json)], capture_output=True, text=True, timeout=900)
    return p.stdout


def parse(text: str, key: str) -> list[dict]:
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0))[key] if m else []


def weighted_kappa(a: list[int], b: list[int], k: int = 3) -> float:
    """Cohen's kappa with quadratic weights for ordinal ratings 0..k-1."""
    n = len(a)
    obs = [[0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[x][y] += 1
    ra = [sum(obs[i]) for i in range(k)]
    rb = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    w = [[(i - j) ** 2 / (k - 1) ** 2 for j in range(k)] for i in range(k)]
    po = sum(w[i][j] * obs[i][j] for i in range(k) for j in range(k)) / n
    pe = sum(w[i][j] * ra[i] * rb[j] for i in range(k) for j in range(k)) / (n * n)
    return 1.0 if pe == 0 else 1 - po / pe


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", required=True)
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--recall-lines", action="store_true")
    args = ap.parse_args(argv)
    seed_dir = HERE.parent / "seeds" / args.seed / "hidden"
    out = seed_dir / "salience"
    out.mkdir(exist_ok=True)
    oracle = simulator.parse_oracle((seed_dir / "oracle.md").read_text(encoding="utf-8"))
    items = eligible(oracle)
    ids = [i.id for i in items]

    if args.recall_lines:
        pf = out / "recall-prompt.md"
        pf.write_text(prompt(RECALL, oracle, items))
        text = call(RATERS[0], pf, out / "recall-raw.json")
        (out / "recall-reply.txt").write_text(text)
        lines = {d["item"]: d["line"] for d in parse(text, "lines")}
        missing = [i for i in ids if i not in lines]
        (out / "recall-lines.json").write_text(json.dumps({"drafted_by": RATERS[0], "lines": lines, "missing": missing}, indent=1))
        print(json.dumps(lines, indent=1), "\nmissing:", missing)
        return 0

    pf = out / "rating-prompt.md"
    pf.write_text(prompt(RUBRIC, oracle, items))
    jobs = [(m, s) for m in RATERS for s in range(args.samples)]

    def one(job):
        m, s = job
        tag = f"{m.split('/')[1]}-{s}"
        err = None
        for attempt in range(2):
            text = call(m, pf, out / f"raw-{tag}.json")
            (out / f"reply-{tag}.txt").write_text(text)
            try:
                return m, s, {d["item"]: d["tier"].lower() for d in parse(text, "ratings")}
            except Exception as e:
                err = str(e)
        return m, s, {"_error": err}

    with cf.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(one, jobs))
    samples = {m: [r for mm, _, r in results if mm == m and "_error" not in r] for m in RATERS}
    per_rater = {}
    for m, rs in samples.items():
        per_rater[m] = {i: int(st.median_low([TIERS[r[i]] for r in rs if r.get(i) in TIERS])) for i in ids
                        if any(r.get(i) in TIERS for r in rs)}
    item_tier = {}
    for i in ids:
        vals = [per_rater[m][i] for m in RATERS if i in per_rater[m]]
        item_tier[i] = [k for k, v in TIERS.items() if v == int(st.median_low(vals))][0] if vals else None
    pairs = {}
    for a, b in combinations([m for m in RATERS if per_rater[m]], 2):
        common = [i for i in ids if i in per_rater[a] and i in per_rater[b]]
        if common:
            pairs[f"{a} vs {b}"] = round(weighted_kappa([per_rater[a][i] for i in common], [per_rater[b][i] for i in common]), 3)
    summary = {"seed": args.seed, "raters": RATERS, "samples": args.samples,
               "errors": [(m, s, r["_error"]) for m, s, r in results if "_error" in r],
               "per_rater_median": per_rater, "tier": item_tier, "pairwise_weighted_kappa": pairs,
               "mean_weighted_kappa": round(st.mean(pairs.values()), 3) if pairs else None,
               "share_high": round(sum(t == "high" for t in item_tier.values()) / len(ids), 3)}
    (out / "ratings.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps({k: summary[k] for k in ("tier", "pairwise_weighted_kappa", "mean_weighted_kappa", "share_high", "errors")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
