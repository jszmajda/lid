"""Build spot-check packets for verdicts, for whoever checks the graders in the maintainer's place.

    python3.12 sample_verdicts.py --out <folder> --n 36 s0-bare:2 s0-cheap-discipline:2 s0-lid-full:2

Each argument is a trajectory and change (and optionally :rejudge-name, to use a re-judgment's verdicts). The sample
keeps every "not met" and "couldn't exercise" verdict up to half of n, then fills with "met" verdicts, favouring
latent items (askable and recognized on sight). Each packet holds the probe's scenario and expected observation, the
probe's slice of the execution log, and the judge's verdict, evidence, and reason. The packets name hidden probes, so
write them under the seed's hidden folder.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import grading, simulator  # noqa: E402


def probe_slice(lines: list[dict], pid: str) -> list[dict]:
    """The log entries from this probe's START marker to the next probe's, plus the restore just before it."""
    out, inside = [], False
    for i, r in enumerate(lines):
        text = str((r.get("request") or {}).get("text", "")) if r.get("op") == "mark" else ""
        if text.startswith("PROBE ") and len(text.split()) > 1:
            if inside and text.split()[1] != pid:
                break  # the next probe; a repeated START for this probe stays inside
            if not inside and text.split()[1] == pid:
                inside = True
                if i and lines[i - 1].get("op") == "restore":
                    out.append(lines[i - 1])
        if inside:
            out.append(r)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("checkpoints", nargs="+")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--n", type=int, default=36)
    ap.add_argument("--seed", default="benchtime")
    ap.add_argument("--random-seed", default="spot-check")
    args = ap.parse_args(argv)
    seed_dir = HERE.parent / "seeds" / args.seed
    probes = {p.id: p for p in grading.parse_probes((seed_dir / "hidden" / "probes.md").read_text()).probes}
    kinds = {i.id: i.share for i in simulator.parse_oracle((seed_dir / "hidden" / "oracle.md").read_text()).items if i.kind != "Dropped"}
    pool = []
    for spec in args.checkpoints:
        parts = spec.split(":")
        tid, change = parts[0], int(parts[1])
        gdir = HERE.parent / "runs" / tid / "grading" / f"change-{change:02d}"
        rejudge = parts[2] if len(parts) > 2 else None
        for bdir in sorted((gdir / "batches").iterdir()):
            jpath = bdir / (f"rejudge-{rejudge}" if rejudge else "") / "judgment.json"
            if not jpath.exists():
                continue
            verdicts = json.loads(jpath.read_text())["verdicts"]
            lines = [json.loads(l) for l in (bdir / "log.jsonl").read_text().splitlines() if l.strip()]
            for pid, v in verdicts.items():
                pool.append({"checkpoint": f"{tid} change {change}", "probe": pid, "item": probes[pid].item,
                             "kind": kinds.get(probes[pid].item), "verdict": v["verdict"], "evidence": v["evidence"],
                             "reason": v["reason"], "log": probe_slice(lines, pid)})
    rng = random.Random(args.random_seed)
    rng.shuffle(pool)
    doubtful = [c for c in pool if c["verdict"] != "met"][: args.n // 2]
    met = sorted((c for c in pool if c["verdict"] == "met"), key=lambda c: c["kind"] == "Stated")
    sample = doubtful + met[: args.n - len(doubtful)]
    rng.shuffle(sample)
    args.out.mkdir(parents=True, exist_ok=True)
    for k, c in enumerate(sample, start=1):
        p = probes[c["probe"]]
        log = "\n".join(json.dumps({x: r[x] for x in ("seq", "clock", "op", "request", "response") if x in r}) for r in c["log"])
        (args.out / f"case-{k:02d}.md").write_text(
            f"# Case {k}: {c['probe']} ({c['item']}, {c['kind']}) at {c['checkpoint']}\n\n"
            f"## The probe\n\n- **Setup:** {p.setup}\n- **Scenario:**\n{p.scenario}\n- **Expected observation:** {p.expected}\n\n"
            f"## The judge's verdict\n\n- **Verdict:** {c['verdict']}\n- **Evidence (log seq):** {c['evidence']}\n- **Reason:** {c['reason']}\n\n"
            f"## The probe's execution log\n\n```\n{log}\n```\n", encoding="utf-8")
    (args.out / "index.json").write_text(json.dumps([{k: c[k] for k in ("checkpoint", "probe", "item", "kind", "verdict")}
                                                     for c in sample], indent=1))
    counts = {v: sum(c["verdict"] == v for c in sample) for v in grading.VERDICTS}
    print(f"{len(sample)} cases from a pool of {len(pool)}: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
