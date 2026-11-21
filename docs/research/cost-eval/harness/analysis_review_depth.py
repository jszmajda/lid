"""Owner reading by review depth (plan.md, M2e): from data already collected, no model calls.

    python3.12 analysis_review_depth.py                       # the default trajectories
    python3.12 analysis_review_depth.py --ids g-lid-full-1 g-bare-1

Each owner record (runs/<id>/change-*/owner-*.json) holds the words the owner was shown at one stop and the names of
the documents shown, but not the split between them. The split is rebuilt from the owner's main-call prompt, which
holds the agent's message between <agent_message> tags and each document, as shown, in a <document name="..."> block:
the whole text when the owner had not read it before, its added lines under a diff header when they had, or a line
saying it is unchanged. Words are counted the way the simulator counts them (whitespace-separated, passage marks
removed, a re-read document counting only its added lines), so the parts add up to the record's `words_shown`; each
stop's reconciliation is reported.

What was shown, by kind:

- hld: docs/high-level-design.md (any file named high-level-design.md);
- lld: design docs under docs/intent/ (`*-design.md`, sub-HLDs included) and decision docs (`decisions/*.md`);
- specs: EARS spec files (`*-specs.md`);
- tests, code: test and source files. The harness shows the owner only prose files the message names, so these stay
  at zero unless a prose file lives under tests/;
- code_in_chat: fenced blocks (code, diffs, command output) inside the agent's message;
- other_docs: any other prose file (README, AGENTS.md, NOTES.md, arrow docs, ...);
- plan: the plan a plan-mode turn presented (cheap discipline), shown beside the message;
- chat: the rest of the agent's message.

Owner-hours at 238 words a minute (costeval/growth.py), for three review depths:

- (a) everything: every word shown;
- (b) HLD and LLD documents plus chat: hld + lld + the message (chat and code_in_chat) + plan;
- (c) chat only: the message (chat and code_in_chat) + plan.

The plan counts as chat because a plan-mode turn presents it in the conversation. Code inside a message counts as
chat at every depth: whoever reads the message reads what is in it.

The arms' results all came from the bounded owner, who reads everything it is shown (with attention that fades as it
reads more). This is a costing of reading time only. It makes no claim about what a lighter reviewer would have
caught, and it doesn't change any graded result."""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

WPM = 238  # owner reading speed, words a minute (costeval/growth.py)

CATEGORIES = ("hld", "lld", "specs", "tests", "code", "code_in_chat", "other_docs", "plan", "chat")
DEPTHS = {
    "a_everything": set(CATEGORIES),
    "b_hld_lld_chat": {"hld", "lld", "chat", "code_in_chat", "plan"},
    "c_chat_only": {"chat", "code_in_chat", "plan"},
}
DEPTH_LABELS = {
    "a_everything": "(a) reads everything",
    "b_hld_lld_chat": "(b) HLD + LLD + chat",
    "c_chat_only": "(c) chat only",
}

DEFAULT_IDS = ["g-lid-full-1", "g-bare-1"] + [f"s3b-{arm}-{k}" for arm in ("bare", "cheap-discipline", "lid-full")
                                              for k in (1, 2, 3)]

# The simulator's own strings (costeval/simulator.py), copied so this script doesn't import code under active edit.
DIFF_HEADER = "Changes since you last read it (lines starting with - were removed, + were added):"
UNCHANGED = "(Unchanged since you last read it.)"
PLAN_NAME = "The agent's plan"
EMPTY_MESSAGE = "(The agent's message was empty.)"
DOCS_HEADING = "## Documents the agent asked you to read"

_MARK = re.compile(r"(?m)^(\+?)\[P\d+\] ")
_MESSAGE = re.compile(r"<agent_message>\n(.*?)\n</agent_message>", re.S)
_DOCUMENT = re.compile(r'<document name="([^"\n]*)">\n(.*?)\n</document>(?=\n\n<document name="|\s*\Z|\n\n## )', re.S)
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
_CODE_SUFFIXES = (".py", ".js", ".ts", ".rs", ".go", ".java", ".rb", ".sh", ".sql", ".toml", ".cfg", ".ini", ".json",
                  ".yaml", ".yml", ".txt")


def words(text: str) -> int:
    return len(text.split())


def strip_marks(text: str) -> str:
    return _MARK.sub(r"\1", text)


def doc_kind(name: str) -> str:
    """The kind of a document shown to the owner, from its path."""
    if name == PLAN_NAME:
        return "plan"
    p = name.lower().lstrip("./")
    base = p.rsplit("/", 1)[-1]
    parts = p.split("/")
    if base == "high-level-design.md":
        return "hld"
    if base.endswith("-specs.md"):
        return "specs"
    if base.endswith("-design.md") or "decisions" in parts[:-1]:
        return "lld"
    if any(seg in ("tests", "test") for seg in parts[:-1]) or base.startswith("test_") or base == "conftest.py":
        return "tests"
    if base.endswith(_CODE_SUFFIXES) and not base.endswith((".md", ".txt")):
        return "code"
    return "other_docs"


def parse_prompt(prompt: str) -> tuple[str, list[tuple[str, str]]]:
    """The agent's message and the documents (name, text as shown) from an owner main-call prompt."""
    m = _MESSAGE.search(prompt)
    if not m:
        raise ValueError("no <agent_message> block in the prompt")
    message = m.group(1)
    docs: list[tuple[str, str]] = []
    k = prompt.find(DOCS_HEADING, m.end())
    if k >= 0:
        section = prompt[k + len(DOCS_HEADING):]
        end = section.find("\n## What to return")
        if end >= 0:
            section = section[:end]
        docs = [(name, text) for name, text in _DOCUMENT.findall(section.rstrip() + "\n")]
        if not docs:
            docs = [(name, text) for name, text in _DOCUMENT.findall(section.rstrip())]
    return message, docs


def doc_words(text: str) -> int:
    """Words counted as read for one document as shown: all of a first read, the added lines of a re-read."""
    t = text.strip()
    if t == UNCHANGED:
        return 0
    if t.startswith(DIFF_HEADER):
        body = strip_marks(t[len(DIFF_HEADER):])
        return sum(words(line[1:]) for line in body.splitlines() if line.startswith("+"))
    return words(strip_marks(t))


def message_split(message: str) -> dict[str, int]:
    """The message's words: those inside fenced blocks (code_in_chat) and the rest (chat)."""
    text = strip_marks(message)
    if text.strip() == EMPTY_MESSAGE:
        return {"chat": 0, "code_in_chat": 0}
    chat = code = 0
    fence = None
    for line in text.splitlines():
        if fence is not None:
            code += words(line)
            if line.strip().startswith(fence):
                fence = None
            continue
        f = _FENCE.match(line)
        if f:
            fence = f.group(1)
            code += words(line)
        else:
            chat += words(line)
    return {"chat": chat, "code_in_chat": code}


def stop_split(record: dict) -> dict:
    """One owner record's words shown, by kind, with its reconciliation against `words_shown`."""
    out = {c: 0 for c in CATEGORIES}
    calls = record.get("calls") or []
    if not calls or "prompt" not in calls[0]:
        return {"split": out, "words_shown": record.get("words_shown", 0), "reconciled": False,
                "problem": "no main-call prompt", "documents": {}}
    message, docs = parse_prompt(calls[0]["prompt"])
    out.update(message_split(message))
    per_doc: dict[str, int] = {}
    for name, text in docs:
        w = doc_words(text)
        per_doc[name] = per_doc.get(name, 0) + w
        out[doc_kind(name)] += w
    total = sum(out.values())
    shown = record.get("words_shown", 0)
    problem = None
    if [n for n, _ in docs] != list(record.get("documents") or []):
        problem = f"documents parsed {[n for n, _ in docs]} != recorded {record.get('documents')}"
    elif total != shown:
        problem = f"parsed {total} words, recorded {shown}"
    return {"split": out, "words_shown": shown, "reconciled": problem is None, "problem": problem,
            "documents": per_doc}


def depth_words(split: dict[str, int]) -> dict[str, int]:
    return {d: sum(split.get(c, 0) for c in cats) for d, cats in DEPTHS.items()}


def hours(w: float) -> float:
    return w / WPM / 60


def change_number(path: Path) -> int:
    return int(path.name.split("-")[1])


def run_split(run: Path) -> dict:
    """A trajectory's words shown by kind, per change and overall, with owner-hours at each depth."""
    traj = json.loads((run / "trajectory.json").read_text())
    changes: dict[str, dict] = {}
    total = {c: 0 for c in CATEGORIES}
    stops = reconciled = 0
    problems = []
    doc_names: dict[str, int] = {}
    for cdir in sorted(run.glob("change-[0-9][0-9]")):
        split = {c: 0 for c in CATEGORIES}
        shown = 0
        n = 0
        for f in sorted(cdir.glob("owner-[0-9][0-9].json")):
            rec = json.loads(f.read_text())
            s = stop_split(rec)
            n += 1
            stops += 1
            reconciled += s["reconciled"]
            if not s["reconciled"]:
                problems.append(f"{cdir.name}/{f.name}: {s['problem']}")
            shown += s["words_shown"]
            for c in CATEGORIES:
                split[c] += s["split"][c]
            for name, w in s["documents"].items():
                doc_names[name] = doc_names.get(name, 0) + w
        if n == 0:
            continue
        for c in CATEGORIES:
            total[c] += split[c]
        changes[str(change_number(cdir))] = {"stops": n, "words_shown": shown, "split": split,
                                              "depth_words": depth_words(split)}
    dw = depth_words(total)
    return {"id": traj.get("id", run.name), "arm": traj.get("arm"), "seed": traj.get("seed"),
            "policy": traj.get("policy"), "changes": changes, "split": total,
            "words_shown": sum(c["words_shown"] for c in changes.values()),
            "depth_words": dw, "depth_hours": {d: round(hours(w), 3) for d, w in dw.items()},
            "stops": stops, "stops_reconciled": reconciled, "problems": problems,
            "top_documents": sorted(doc_names.items(), key=lambda kv: -kv[1])[:12]}


# ------------------------------------------------------------------------------------------------- reporting

COL_LABELS = {"hld": "HLD", "lld": "LLD", "specs": "Specs", "tests": "Tests", "code": "Code files",
              "code_in_chat": "Code in chat", "other_docs": "Other docs", "plan": "Plan", "chat": "Chat"}

LABEL = ("**Read this first.** Every arm's results came from the bounded owner, who reads everything it is shown. "
         "These figures cost the reading time of lighter review depths only. They don't say what a lighter reviewer "
         "would have caught or missed, and they change no graded result.")


def pct(part: float, whole: float) -> str:
    return f"{100 * part / whole:.0f}%" if whole else "–"


def report(results: list[dict]) -> str:
    lines = ["# Owner reading by review depth", "", LABEL, "",
             f"Owner-hours at {WPM} words a minute. Words count as the simulator counts them: new text only, so a "
             "re-read document counts only its added lines. The harness shows the owner the agent's message and the "
             "prose files the message names; it never shows source or test files, so code reaches the owner only "
             "inside messages (\"Code in chat\").", "",
             "Depths: (a) reads everything shown; (b) reads only HLD and LLD documents plus the chat (the message, "
             "with any code in it, and a plan-mode plan); (c) reads only the chat.", "",
             "## Words shown, by what was shown", "",
             "| Trajectory | Arm | Changes | Stops | Words shown | " + " | ".join(COL_LABELS[c] for c in CATEGORIES) + " |",
             "|---|---|---|---|---|" + "---|" * len(CATEGORIES)]
    for r in results:
        w = r["words_shown"]
        cells = [f"{r['split'][c]:,} ({pct(r['split'][c], w)})" if r["split"][c] else "0" for c in CATEGORIES]
        lines.append(f"| {r['id']} | {r['arm']} | {len(r['changes'])} | {r['stops']} | {w:,} | " + " | ".join(cells) + " |")
    lines += ["", "## Owner-hours by review depth", "",
              "| Trajectory | Arm | " + " | ".join(DEPTH_LABELS[d] for d in DEPTHS) + " | (b) ÷ (a) | (c) ÷ (a) |",
              "|---|---|" + "---|" * (len(DEPTHS) + 2)]
    for r in results:
        h = r["depth_hours"]
        lines.append(f"| {r['id']} | {r['arm']} | " + " | ".join(f"{h[d]:.2f}" for d in DEPTHS)
                     + f" | {pct(h['b_hld_lld_chat'], h['a_everything'])} | {pct(h['c_chat_only'], h['a_everything'])} |")
    # BenchTime arm means
    by_arm: dict[str, list[dict]] = {}
    for r in results:
        if r["id"].startswith("s3b-"):
            by_arm.setdefault(r["arm"], []).append(r)
    if by_arm:
        lines += ["", "## BenchTime stage 3b, mean per trajectory (build plus ten changes)", "",
                  "| Arm | Trajectories | " + " | ".join(DEPTH_LABELS[d] for d in DEPTHS) + " |",
                  "|---|---|" + "---|" * len(DEPTHS)]
        for arm, rs in by_arm.items():
            lines.append(f"| {arm} | {len(rs)} | " + " | ".join(
                f"{statistics.mean(x['depth_hours'][d] for x in rs):.2f} "
                f"[{', '.join(f'{x['depth_hours'][d]:.2f}' for x in rs)}]" for d in DEPTHS) + " |")
    lines += ["", "## Per change (owner-hours at depths a / b / c)", ""]
    for r in results:
        lines += [f"### {r['id']}", "", "| Change | Stops | Words shown | HLD | LLD | Specs | Other docs | Chat (with code, plan) | a | b | c |",
                  "|---|---|---|---|---|---|---|---|---|---|---|"]
        for n, c in sorted(r["changes"].items(), key=lambda kv: int(kv[0])):
            s, dw = c["split"], c["depth_words"]
            lines.append(f"| {n} | {c['stops']} | {c['words_shown']:,} | {s['hld']:,} | {s['lld']:,} | {s['specs']:,} | "
                         f"{s['other_docs']:,} | {s['chat'] + s['code_in_chat'] + s['plan']:,} | "
                         + " | ".join(f"{hours(dw[d]):.2f}" for d in DEPTHS) + " |")
        lines.append("")
    lines += ["## Reconciliation", "",
              "Each stop's parsed words are checked against the record's `words_shown`, and its parsed document names "
              "against the record's `documents`.", ""]
    for r in results:
        lines.append(f"- {r['id']}: {r['stops_reconciled']} of {r['stops']} stops reconcile exactly"
                     + (f"; {len(r['problems'])} don't: " + "; ".join(r["problems"][:5]) if r["problems"] else "") + ".")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", nargs="+", default=DEFAULT_IDS)
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    ap.add_argument("--out", type=Path, default=None, help="output folder (default: <runs>/analysis)")
    args = ap.parse_args(argv)
    out = args.out or args.runs / "analysis"
    results = []
    for tid in args.ids:
        run = args.runs / tid
        if not (run / "trajectory.json").exists():
            print(f"{tid}: no trajectory.json, skipped", file=sys.stderr)
            continue
        results.append(run_split(run))
    out.mkdir(parents=True, exist_ok=True)
    (out / "review_depth.json").write_text(json.dumps(results, indent=1))
    (out / "review_depth.md").write_text(report(results))
    for r in results:
        h = r["depth_hours"]
        print(f"{r['id']}: words {r['words_shown']:,}; hours a {h['a_everything']:.2f} b {h['b_hld_lld_chat']:.2f} "
              f"c {h['c_chat_only']:.2f}; reconciled {r['stops_reconciled']}/{r['stops']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
