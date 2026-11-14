"""Sort every request a trajectory's agent made of the owner into the kinds in "Human cost" (design.md), and count
the words the owner was shown, per change.

    ../plumbing/with-token.sh python3.12 classify_touchpoints.py --id s0-bare

The classifier sees what the owner saw at each stop (taken from the owner's own prompt), never the owner's reply.
Writes ../runs/<id>/touchpoints.json. Bug reports and end-of-change reviews come from the trajectory's structure,
not from this classifier.
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures as cf
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import executor  # noqa: E402

IMAGE = "lid-cost-eval-executor:2.1.323"
KINDS = ("acknowledgement", "lookup", "judgment", "origination", "completion report")
SCHEMA = {"type": "object", "additionalProperties": False, "required": ["requests"],
          "properties": {"requests": {"type": "array", "items": {
              "type": "object", "additionalProperties": False, "required": ["request", "kind", "items"],
              "properties": {"request": {"type": "string"}, "kind": {"type": "string", "enum": list(KINDS)},
                             "items": {"type": "array", "items": {"type": "string"}}}}}}}


def owner_view(prompt: str) -> str:
    """The owner's prompt without its instructions on how to respond: knowledge, the change, and the message."""
    cut = re.split(r"(?m)^## How you respond\b", prompt, maxsplit=1)
    head = cut[0]
    tail = re.split(r"(?m)^## This change\b", prompt, maxsplit=1)
    body = "## This change" + tail[1] if len(tail) > 1 else ""
    body = re.split(r"(?m)^## What to return\b", body, maxsplit=1)[0]
    return (head + body).strip()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True)
    ap.add_argument("--model", default="claude-sonnet-5-5")
    args = ap.parse_args(argv)
    run = HERE.parent / "runs" / args.id
    template = (HERE / "prompts" / "touchpoints.md").read_text(encoding="utf-8")
    role = executor.RoleSession(image=IMAGE, config_volume="ce-roles-cfg", model=args.model, claude_code_version="2.1.323")
    stops = []
    for path in sorted(run.glob("change-*/owner-*.json")):
        rec = json.loads(path.read_text())
        prompt = [c for c in rec["calls"] if "trim" not in c][0]["prompt"]
        stops.append((path, rec, template.replace("{OWNER_VIEW}", owner_view(prompt))))

    def go(stop):
        path, rec, prompt = stop
        r = executor.run_role(role, prompt, json_schema=json.dumps(SCHEMA))
        return {"stop": f"{path.parent.name}/{path.stem}", "change": int(path.parent.name.split("-")[1]),
                "words_shown": rec["words_shown"], "requests": (r.structured or {}).get("requests", []),
                "cost_usd": r.usage.reported_cost_usd}

    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(go, stops))
    per_change: dict[int, collections.Counter] = collections.defaultdict(collections.Counter)
    words: dict[int, int] = collections.Counter()
    for r in results:
        per_change[r["change"]].update(q["kind"] for q in r["requests"])
        words[r["change"]] += r["words_shown"]
    summary = {n: {"requests": dict(per_change[n]), "words_shown": words[n]} for n in sorted(words)}
    (run / "touchpoints.json").write_text(json.dumps({"summary": summary, "stops": results}, indent=1))
    for n, s in summary.items():
        print(f"{args.id} change {n}: {s['requests']}, words shown {s['words_shown']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
