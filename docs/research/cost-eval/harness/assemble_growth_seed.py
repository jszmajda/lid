#!/usr/bin/env python3
"""Assemble the growth test's seed, ../seeds/releasedesk-growth/, so the harness reads one oracle, change script and
probe set at their usual names. It merges ReleaseDesk's block-1 files with their growth additions the way the seed's
own tools merge them (hidden/prompts-growth/split_growth.py's merged_oracle; build_reference.py's change script):

- brief.md: ReleaseDesk's;
- hidden/oracle.md: oracle.md with oracle-growth.md merged in;
- hidden/change-script.md: change-script.md's changes 1-10, then change-script-growth.md's changes 11-40, then block 1's
  probe request;
- hidden/probes.md: probes-growth.md, the full growth probe set;
- hidden/owner-items.json: block 1's, with the growth rows' salience tiers and recall lines merged in from
  salience-growth/hidden/salience/: the current round, round 2 for RD-104 alone, and round 1 for the rows it rated
  (a later round wins). Nothing is invented: a row no round gave a tier or line is a gap that --check lists;
- hidden/stale-audit-terms.json and reference-builds.json: as they are;
- hidden/assembled.json: each source file and its SHA-256.

    python3.12 assemble_growth_seed.py [--check]

The folder is derived (git-ignored) and rebuilt whenever a source changes. --check rebuilds it and checks that it
parses, that the growth fields validate, that the reference owners hold exactly the rows reference-builds.json lists,
and that every row the owner can recall (askable, or realized on a symptom) has a tier and a recall line.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import grading, reference, simulator  # noqa: E402

SRC = HERE.parent / "seeds" / "releasedesk"
DEST = HERE.parent / "seeds" / "releasedesk-growth"
COPIED = ("stale-audit-terms.json", "reference-builds.json")
SALIENCE = SRC / "hidden" / "salience-growth" / "hidden" / "salience"
ROUND2_ONLY = {"RD-104"}  # round 2's other rows were rated again in the current round


def _round(d: Path) -> tuple[dict, dict]:
    tiers = json.loads((d / "ratings.json").read_text())["tier"] if (d / "ratings.json").exists() else {}
    lines = json.loads((d / "recall-lines.json").read_text())["lines"] if (d / "recall-lines.json").exists() else {}
    return tiers, lines


def merge_owner_items(base: dict, salience: Path = SALIENCE, round2_only=ROUND2_ONLY) -> dict:
    """Block 1's owner items with the growth salience rounds over them: round 1, then round 2's named rows, then the
    current round, each later one winning for the rows it rated or wrote a line for."""
    out = dict(base)
    items = {k: dict(v) for k, v in (base["items"] if "items" in base else base).items() if not k.startswith("_")}
    for d, only in ((salience / "round1", None), (salience / "round2", set(round2_only)), (salience, None)):
        tiers, lines = _round(d)
        for row in sorted(set(tiers) | set(lines)):
            if only is not None and row not in only:
                continue
            entry = items.setdefault(row, {})
            if row in tiers:
                entry["tier"] = tiers[row]
            if row in lines:
                entry["recall"] = lines[row]
    out["_growth"] = ("growth salience merged by assemble_growth_seed.py: round 1, round 2 for "
                      + ", ".join(sorted(round2_only)) + ", then the current round")
    if "items" in base:
        out["items"] = items
        return out
    return {**{k: v for k, v in out.items() if k.startswith("_")}, **items}


def owner_item_gaps(oracle: simulator.Oracle, items: dict) -> list[str]:
    """Every row the owner can recall (askable, or realized on a symptom, in force at some change) without a tier or a
    recall line."""
    gaps = []
    for i in simulator.recall_eligible(oracle):
        e = items.get(i.id) or {}
        if not e:
            gaps.append(f"{i.id}: no tier or recall line")
        elif e.get("tier") not in simulator.TIERS:
            gaps.append(f"{i.id}: no tier" + ("" if (e.get("recall") or "").strip() else " or recall line"))
        elif not (e.get("recall") or "").strip():
            gaps.append(f"{i.id}: no recall line")
    return sorted(gaps, key=lambda g: int(g.split(":")[0].split("-")[1]))


def merged_change_script(first: str, growth: str) -> str:
    head, sep, probe = first.partition("\n## Probe request")
    changes = growth[growth.index("\n## Delivery rules"):].partition("\n## Plan")[0]
    return head + "\n\n" + changes.strip() + "\n" + (sep + probe if sep else "")


def assemble(src: Path = SRC, dest: Path = DEST) -> dict[str, str]:
    hidden = src / "hidden"
    sys.path.insert(0, str(hidden / "prompts-growth"))
    from split_growth import merged_oracle  # the seed's own merge
    b = (hidden / "oracle-growth.md").read_text(encoding="utf-8")
    oracle = merged_oracle((hidden / "oracle.md").read_text(encoding="utf-8"), b[b.index("\n## Owner narrative"):])
    script = merged_change_script((hidden / "change-script.md").read_text(encoding="utf-8"),
                                  (hidden / "change-script-growth.md").read_text(encoding="utf-8"))
    (dest / "hidden").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src / "brief.md", dest / "brief.md")
    (dest / "hidden" / "oracle.md").write_text(oracle, encoding="utf-8")
    (dest / "hidden" / "change-script.md").write_text(script, encoding="utf-8")
    shutil.copyfile(hidden / "probes-growth.md", dest / "hidden" / "probes.md")
    for name in COPIED:
        if (hidden / name).exists():
            shutil.copyfile(hidden / name, dest / "hidden" / name)
    base = json.loads((hidden / "owner-items.json").read_text(encoding="utf-8"))
    (dest / "hidden" / "owner-items.json").write_text(json.dumps(merge_owner_items(base), indent=1, ensure_ascii=False),
                                                      encoding="utf-8")
    sources = ["brief.md"] + [f"hidden/{n}" for n in ("oracle.md", "oracle-growth.md", "change-script.md",
                                                      "change-script-growth.md", "probes-growth.md", "owner-items.json",
                                                      *COPIED)]
    sources += [str(p.relative_to(src)) for d in (SALIENCE, SALIENCE / "round2", SALIENCE / "round1")
                for p in (d / "ratings.json", d / "recall-lines.json") if p.exists()]
    record = {s: hashlib.sha256((src / s).read_bytes()).hexdigest() for s in sources if (src / s).exists()}
    (dest / "hidden" / "assembled.json").write_text(json.dumps({"from": str(src.name), "sources": record}, indent=1))
    return record


def check(dest: Path = DEST) -> list[str]:
    problems = []
    oracle = simulator.parse_oracle((dest / "hidden" / "oracle.md").read_text(encoding="utf-8"))
    script = simulator.parse_change_script((dest / "hidden" / "change-script.md").read_text(encoding="utf-8"))
    grading.parse_probes((dest / "hidden" / "probes.md").read_text(encoding="utf-8"))
    problems += simulator.validate_growth_fields(script)
    items = json.loads((dest / "hidden" / "owner-items.json").read_text(encoding="utf-8"))
    problems += [f"owner items: {g}" for g in owner_item_gaps(oracle, items.get("items", items))]
    if sorted(script) != list(range(1, 41)):
        problems.append(f"the change script has changes {sorted(script)[:3]}...{sorted(script)[-3:]}, not 1-40")
    if (dest / "hidden" / reference.SPEC_FILE).exists():
        spec = reference.load_spec(dest)
        view = reference.owner_view(oracle, spec)
        for n in range(41):
            if [i.id for i in simulator.released_items(view, n)] != spec["correct"][str(n)]:
                problems.append(f"R+'s owner at change {n} doesn't hold the spec's rows")
        for c, e in spec["stale"].items():
            v = reference.owner_view(oracle, spec, int(c))
            for n, rows in e["hold"].items():
                want = rows + ([reference.stand_in_id(int(c))] if e["stand_in"] else [])
                if [i.id for i in simulator.released_items(v, int(n))] != want:
                    problems.append(f"S_{c}'s owner at change {n} doesn't hold the spec's rows")
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    record = assemble()
    print(f"assembled {DEST} from {len(record)} files")
    if args.check:
        problems = check()
        for p in problems:
            print("problem:", p)
        print("ok" if not problems else f"{len(problems)} problems")
        return 1 if problems else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
