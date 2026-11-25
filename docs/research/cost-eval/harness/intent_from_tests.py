"""Intent from tests: give a fresh reader only a system's tests (or its docs, or the seed's brief) and score the
rules it writes down against the intent known at that point. The measure and its checks are in
costeval/intent_recall.py.

    ../plumbing/with-token.sh python3.12 intent_from_tests.py batch --plan ../runs/intent-from-tests/<name>/plan.json
    python3.12 intent_from_tests.py summarize --name <name>
    ../plumbing/with-token.sh python3.12 intent_from_tests.py retired --dir /path/to/repo --segment docs/intent/x \\
        --out ../runs/intent-from-tests/<name>/retired-x.json

A plan is {"name": ..., "inputs": [spec, ...]}; each spec names one input:

- `label`, and `group` (the arm, or the part of the system) for the summary;
- `source`: tests, docs, or brief; `neutral`: true for the tests with names, comments, and docstrings replaced;
- where it comes from: `volume` (a Docker volume) and `root` (the folder in it), or `dir` (a git repository, read
  at `commit`, default HEAD), or `brief` (a file);
- `segment` (with `dir`): a part of the system, as its folder under docs/intent/. Its tests are the test functions
  whose `@spec` annotations cite its specs; its docs are its design doc alone (its specs are the oracle);
- `oracle`: {"kind": "benchtime", "seed": ..., "change": N} or {"kind": "segment", "retired": path to the
  `retired` command's output}; `verdicts`: a graded checkpoint's folder, whose met items normalize recall;
- `baseline`: the label of the brief-only input its recall is compared with.

Each input's records go to ../runs/intent-from-tests/<name>/<label>/: the input as the reader saw it, the oracle,
and per repeat the reader's answer, the rules, the judgment, and the scores; result.json gathers them, and
`summarize` writes summary.json and summary.md for the whole plan. An input over the size cap is refused whole
and reported, never cut. Paths in a plan are relative to the notebook (the folder above harness/).
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import time
from dataclasses import asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTEBOOK = HERE.parent
sys.path.insert(0, str(HERE))

import clowder_variants as cv  # noqa: E402
import report  # noqa: E402
from costeval import executor, grading, simulator  # noqa: E402
from costeval import intent_recall as ir  # noqa: E402

IMAGE = "lid-cost-eval-executor:2.1.323"
CLAUDE_CODE = "2.1.323"
ROLES_VOLUME = "ce-roles-cfg"
MODEL = "claude-sonnet-5-5"
EFFORT = "medium"
RUNS = NOTEBOOK / "runs" / "intent-from-tests"
REPEATS = 2
RETIRED_BATCH = 30


# ------------------------------------------------------------------------------------------- reading files


def read_volume(volume: str, root: str, image: str = IMAGE, runner=subprocess.run) -> dict[str, str]:
    """Every text file under a folder of a Docker volume, skipping dependency and cache folders."""
    if ".." in Path(root).parts or root.startswith("/"):
        raise ValueError(f"root must be a folder inside the volume, not {root!r}")
    excludes = [f"--exclude={d}" for d in sorted(ir.SKIP_DIRS)] + ["--exclude=*.egg-info"]
    p = runner(["docker", "run", "--rm", "-v", f"{executor._volume(volume)}:/src:ro", image,
                "tar", *excludes, "-C", f"/src/{root}", "-cf", "-", "."], capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"reading {volume}/{root} failed: {p.stderr.decode(errors='replace')[-300:]}")
    files = {}
    with tarfile.open(fileobj=io.BytesIO(p.stdout), mode="r:") as tar:
        for m in tar.getmembers():
            if not m.isfile():
                continue
            data = tar.extractfile(m).read()
            try:
                files[m.name.removeprefix("./")] = data.decode("utf-8")
            except UnicodeDecodeError:
                continue
    return files


def read_repo(path: str, commit: str = "HEAD") -> tuple[dict[str, str], str]:
    tree = cv.read_tree(path, commit)
    files = {}
    for p, d in tree.files.items():
        try:
            files[p] = d.decode("utf-8")
        except UnicodeDecodeError:
            continue
    return files, tree.commit


def _path(p: str) -> Path:
    q = Path(p)
    return q if q.is_absolute() else NOTEBOOK / q


def segment_spec(files: dict[str, str], segment: str) -> tuple[str, str]:
    """The segment's own spec file (not a child's): <segment>/<name>-specs.md."""
    seg = segment.rstrip("/")
    hits = [p for p in files if p.startswith(seg + "/") and p.count("/") == seg.count("/") + 1 and p.endswith("-specs.md")]
    if len(hits) != 1:
        raise ValueError(f"{segment}: expected one spec file directly in it, found {hits}")
    return hits[0], files[hits[0]]


# ------------------------------------------------------------------------------------------------ the input


def build_input(spec: dict) -> dict:
    """The files the reader gets, stripped of spec-ID pointers (and neutralised when asked), with what was done."""
    source, origin = spec["source"], {}
    if source == "brief":
        text = _path(spec["brief"]).read_text(encoding="utf-8")
        inputs, all_files = [ir.InputFile("brief.md", text)], {}
        origin = {"brief": spec["brief"]}
    else:
        if spec.get("volume"):
            all_files = read_volume(spec["volume"], spec.get("root", "app"))
            origin = {"volume": spec["volume"], "root": spec.get("root", "app")}
        else:
            all_files, commit = read_repo(spec["dir"], spec.get("commit", "HEAD"))
            origin = {"dir": spec["dir"], "commit": commit}
        if spec.get("segment"):
            seg = spec["segment"].rstrip("/")
            origin["segment"] = seg
            _, spec_text = segment_spec(all_files, seg)
            if source == "tests":
                inputs = ir.segment_tests(all_files, ir.spec_ids(spec_text))
            else:
                inputs = [ir.InputFile(p, all_files[p]) for p in sorted(all_files)
                          if p.startswith(seg + "/") and p.count("/") == seg.count("/") + 1 and p.endswith("-design.md")]
        else:
            inputs = ir.select_tests(all_files) if source == "tests" else ir.select_docs(all_files)
    if not inputs:
        raise ValueError(f"{spec['label']}: no {source} files")
    pattern = ir.pointer_pattern(all_files)
    inputs, stripped = ir.strip_pointers(inputs, pattern)
    neutral = None
    if spec.get("neutral"):
        inputs, neutral = ir.neutralize(inputs)
    return {"inputs": inputs, "origin": origin, "pointer_pattern": pattern.pattern, "stripped": stripped,
            "neutralized": neutral, "files": [{"path": f.path, "bytes": len(f.text.encode()), "note": f.note}
                                              for f in inputs]}


def build_oracle(spec: dict) -> tuple[list[ir.OracleItem], set[str] | None, dict]:
    o = spec["oracle"]
    if o["kind"] == "benchtime":
        hidden = NOTEBOOK / "seeds" / o["seed"] / "hidden"
        items = ir.benchtime_oracle(simulator.parse_oracle((hidden / "oracle.md").read_text(encoding="utf-8")),
                                    simulator.parse_change_script((hidden / "change-script.md").read_text(encoding="utf-8")),
                                    o["change"])
        meta = {"kind": "benchtime", "seed": o["seed"], "change": o["change"]}
    elif o["kind"] == "segment":
        files, commit = read_repo(spec["dir"], spec.get("commit", "HEAD"))
        path, text = segment_spec(files, spec["segment"])
        retired = json.loads(_path(o["retired"]).read_text(encoding="utf-8"))
        items = ir.spec_items(text) + ir.items_from_json(retired["items"])
        meta = {"kind": "segment", "spec": path, "commit": commit, "retired": o["retired"]}
    else:
        raise ValueError(f"unknown oracle kind {o['kind']!r}")
    met = None
    if spec.get("verdicts"):
        probes = grading.parse_probes((NOTEBOOK / "seeds" / o["seed"] / "hidden" / "probes.md").read_text(encoding="utf-8"))
        verdicts = report.checkpoint_items(_path(spec["verdicts"]), "verdicts", probes.probes)
        if verdicts is None:
            raise ValueError(f"no verdicts in {spec['verdicts']}")
        met = {i for i, v in verdicts.items() if v == "met"}
        meta["verdicts"] = spec["verdicts"]
    return items, met, meta


# ------------------------------------------------------------------------------------------------ the calls


def role(timeout_s: int) -> executor.RoleSession:
    return executor.RoleSession(image=IMAGE, config_volume=ROLES_VOLUME, model=MODEL, claude_code_version=CLAUDE_CODE,
                                effort=EFFORT, tools=(), timeout_s=timeout_s)


def _usage(rec: executor.RoleRecord) -> dict:
    return {"cost_usd": rec.usage.reported_cost_usd, "duration_s": round(rec.duration_s, 1),
            "models": {m: asdict(c) for m, c in rec.usage.models.items()}}


def make_ask(timeout_s: int):
    r = role(timeout_s)

    def ask(prompt: str, schema: dict):
        try:
            rec = executor.run_role(r, prompt, json_schema=json.dumps(schema, separators=(",", ":")))
        except executor.RoleFailed as e:
            return None, {"error": str(e), "cost_usd": 0.0}
        return rec.structured, _usage(rec)
    return ask


def reconstruct(prompt: str, inputs: list[ir.InputFile], ask, attempts: int = ir.ATTEMPTS) -> dict:
    """The reader's rules. Asked again only when an answer has no usable rules or the call failed; otherwise the
    first answer stands, with bad citations and rules dropped and recorded (no choosing among samples)."""
    tries = []
    for _ in range(attempts):
        structured, use = ask(prompt, ir.READER_SCHEMA)
        rules, problems = ir.check_reader(structured, inputs)
        tries.append({"structured": structured, "problems": problems, "usage": use})
        if rules:
            break
    return {"rules": rules, "problems": problems, "tries": tries,
            "listed": len(((tries[-1]["structured"] or {}).get("rules") or [])),
            "cost_usd": round(sum((t["usage"] or {}).get("cost_usd") or 0.0 for t in tries), 6)}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _tokens(uses: list[dict]) -> dict[str, int]:
    out = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    for u in uses:
        for c in ((u or {}).get("models") or {}).values():
            out["input"] += c.get("input", 0)
            out["output"] += c.get("output", 0)
            out["cache_read"] += c.get("cache_read", 0)
            out["cache_write"] += c.get("cache_write_5m", 0) + c.get("cache_write_1h", 0)
    return out


def run_input(spec: dict, out: Path, *, repeats: int = REPEATS, ask_reader=None, ask_judge=None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    (out / "spec.json").write_text(ir.dumps(spec), encoding="utf-8")
    try:
        built = build_input(spec)
        rendered = ir.render_files(built["inputs"])
        prompt = ir.reader_prompt(spec["source"], built["inputs"], neutral=bool(spec.get("neutral")))
        tokens_est = ir.check_size(prompt)
    except ir.TooLarge as e:
        result = {"label": spec["label"], "refused": str(e)}
        (out / "result.json").write_text(ir.dumps(result), encoding="utf-8")
        print(f"{spec['label']}: refused: {e}", flush=True)
        return result
    (out / "input.md").write_text(rendered, encoding="utf-8")
    (out / "input.json").write_text(ir.dumps({k: v for k, v in built.items() if k != "inputs"} | {"tokens_est": tokens_est}),
                                    encoding="utf-8")
    items, met, oracle_meta = build_oracle(spec)
    (out / "oracle.json").write_text(ir.dumps({"meta": oracle_meta, "items": ir.items_json(items),
                                               "met": sorted(met) if met is not None else None}), encoding="utf-8")
    ask_reader = ask_reader or make_ask(2400)
    ask_judge = ask_judge or make_ask(1500)
    scores, costs, uses = [], [], []
    for k in range(1, repeats + 1):
        rdir = out / f"rep-{k}"
        rdir.mkdir(exist_ok=True)
        if (rdir / "score.json").exists():
            done = json.loads((rdir / "score.json").read_text())
            scores.append(done["score"])
            costs.append(done["cost_usd"])
            uses += done["uses"]
            continue
        started = time.monotonic()
        saved = json.loads((rdir / "reader.json").read_text()) if (rdir / "reader.json").exists() else None
        if saved and saved.get("rules") and saved.get("prompt_sha256") == _sha(prompt):
            rec = saved  # the repeat's sample stands; only the judgment is redone
        else:
            rec = reconstruct(prompt, built["inputs"], ask_reader) | {"prompt_sha256": _sha(prompt)}
            (rdir / "reader.json").write_text(ir.dumps(rec), encoding="utf-8")
        (rdir / "rules.md").write_text("\n".join(f"R{n}. {r['rule']}  [{'; '.join(r['evidence'])}]"
                                                 for n, r in enumerate(rec["rules"], 1)) + "\n", encoding="utf-8")
        if not rec["rules"]:
            print(f"{spec['label']} rep {k}: no usable rules: {rec['problems'][:3]}", flush=True)
            continue
        j = ir.judge(rec["rules"], items, ask=ask_judge)
        (rdir / "judgment.json").write_text(ir.dumps(j), encoding="utf-8")
        s = ir.score(len(rec["rules"]), j["mappings"], items, met)
        s["reader_rules_listed"] = rec["listed"]
        s["reader_rules_dropped"] = rec["listed"] - len(rec["rules"])
        rep_uses = [t["usage"] for t in rec["tries"]] + [t["usage"] for b in j["batches"] for t in b["tries"]]
        cost = {"reader_usd": rec["cost_usd"], "judge_usd": j["cost_usd"], "reader_calls": len(rec["tries"]),
                "judge_calls": sum(len(b["tries"]) for b in j["batches"]),
                "reader_tokens": _tokens([t["usage"] for t in rec["tries"]]),
                "judge_tokens": _tokens([t["usage"] for b in j["batches"] for t in b["tries"]]),
                "minutes": round((time.monotonic() - started) / 60, 1)}
        (rdir / "score.json").write_text(ir.dumps({"score": s, "cost_usd": cost, "uses": rep_uses}), encoding="utf-8")
        scores.append(s)
        costs.append(cost)
        uses += rep_uses
        print(f"{spec['label']} rep {k}: {len(rec['rules'])} rules, recall {s['recall']:.2f}"
              + (f", of met {s['recall_of_met']:.2f}" if s["recall_of_met"] is not None else "")
              + f", stale {s['counts']['stale']}, contradicts {s['counts']['contradicts']}, incidental "
              f"{s['counts']['incidental']}, unjudged {s['unjudged']}, ${cost['reader_usd'] + cost['judge_usd']:.2f}",
              flush=True)
    result = {"label": spec["label"], "group": spec.get("group"), "source": spec["source"],
              "neutral": bool(spec.get("neutral")), "baseline": spec.get("baseline"), "tokens_est": tokens_est,
              "files": len(built["inputs"]), "oracle": oracle_meta, "repeats": scores,
              "summary": ir.summarize_repeats(scores) if scores else None, "costs": costs,
              "cost_usd": round(sum(c["reader_usd"] + c["judge_usd"] for c in costs), 4),
              "tokens": _tokens(uses)}
    (out / "result.json").write_text(ir.dumps(result), encoding="utf-8")
    return result


# ------------------------------------------------------------------------------------------- the summary


def variant(r: dict) -> str:
    return r["source"] + ("-neutral" if r.get("neutral") else "")


def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _m(r: dict, key: str):
    v = (r.get("summary") or {}).get(key)
    return v["mean"] if v else None


def _spread(r: dict, key: str):
    v = (r.get("summary") or {}).get(key)
    return v["max"] - v["min"] if v else None


METRICS = ("recall", "recall_whole", "recall_of_met", "by_group.stated.recall", "by_group.latent.recall",
           "by_group_of_met.stated.recall", "by_group_of_met.latent.recall", "rates_per_rule.agrees",
           "rates_per_rule.contradicts", "rates_per_rule.stale", "rates_per_rule.incidental", "stale_items_share",
           "stale_rules_per_retired_item", "rules", "judged", "unjudged", "reader_rules_dropped",
           "contradicting_rules.against_met_per_rule", "contradicting_rules.against_unmet_only_per_rule")


def baseline_against(base: dict, oracle_items: list[dict], met: list[str] | None) -> dict:
    """A brief-only input's recall over another input's oracle and met set: raw, of met, and by group."""
    groups = {i["id"]: i["group"] for i in oracle_items}
    cur = [i["id"] for i in oracle_items if i["status"] == "in force"]
    out = {"recall": [], "recall_of_met": [], "stated_of_met": [], "latent_of_met": [], "stated": [], "latent": []}
    for s in base["repeats"]:
        rec = set(s["recovered"])
        out["recall"].append(ir.recall_against(rec, set(cur)))
        for g in ("stated", "latent"):
            out[g].append(ir.recall_against(rec, {i for i in cur if groups[i] == g}))
        if met is not None:
            m = set(met) & set(cur)
            out["recall_of_met"].append(ir.recall_against(rec, m))
            for g in ("stated", "latent"):
                out[f"{g}_of_met"].append(ir.recall_against(rec, {i for i in m if groups[i] == g}))
    return {k: _mean(v) for k, v in out.items()}


def summarize(name: str) -> dict:
    root = RUNS / name
    results = {}
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        f = d / "result.json"
        if f.exists():
            results[d.name] = json.loads(f.read_text())
    cells: dict[str, dict] = {}
    for label, r in results.items():
        if r.get("refused"):
            continue
        cells.setdefault(f"{r['group']}|{variant(r)}", []).append(label)
    out_cells = {}
    for cell, labels in sorted(cells.items()):
        rs = [results[l] for l in labels]
        row = {"inputs": labels, "mean": {k: _mean([_m(r, k) for r in rs]) for k in METRICS},
               "repeat_spread": {k: _mean([_spread(r, k) for r in rs]) for k in ("recall", "recall_of_met",
                                                                               "rates_per_rule.incidental")},
               "cost_usd": round(sum(r["cost_usd"] for r in rs), 4)}
        deltas = []
        for label, r in zip(labels, rs):
            base = results.get(r.get("baseline") or "")
            if not base or base.get("refused") or not base.get("repeats"):
                continue
            o = json.loads((root / label / "oracle.json").read_text())
            b = baseline_against(base, o["items"], o["met"])
            deltas.append({"recall": (_m(r, "recall") or 0) - (b["recall"] or 0),
                           "recall_of_met": None if b["recall_of_met"] is None else _m(r, "recall_of_met") - b["recall_of_met"],
                           "latent_of_met": None if b["latent_of_met"] is None or _m(r, "by_group_of_met.latent.recall") is None
                           else _m(r, "by_group_of_met.latent.recall") - b["latent_of_met"],
                           "stated_of_met": None if b["stated_of_met"] is None or _m(r, "by_group_of_met.stated.recall") is None
                           else _m(r, "by_group_of_met.stated.recall") - b["stated_of_met"],
                           "baseline": b})
        if deltas:
            row["minus_baseline"] = {k: _mean([d[k] for d in deltas]) for k in ("recall", "recall_of_met",
                                                                                 "stated_of_met", "latent_of_met")}
            row["baseline"] = {k: _mean([d["baseline"][k] for d in deltas]) for k in deltas[0]["baseline"]}
        out_cells[cell] = row
    summary = {"name": name, "model": MODEL, "effort": EFFORT, "claude_code": CLAUDE_CODE, "cells": out_cells,
               "refused": {l: r["refused"] for l, r in results.items() if r.get("refused")},
               "inputs": {l: {k: r.get(k) for k in ("group", "source", "neutral", "tokens_est", "files", "cost_usd",
                                                     "tokens", "baseline")}
                          | {"means": {k: _m(r, k) for k in METRICS}, "spread": {k: _spread(r, k) for k in METRICS}}
                          for l, r in results.items() if not r.get("refused")},
               "cost_usd": round(sum(r.get("cost_usd") or 0 for r in results.values()), 4),
               "tokens": {k: sum((r.get("tokens") or {}).get(k, 0) for r in results.values())
                          for k in ("input", "output", "cache_read", "cache_write")}}
    (root / "summary.json").write_text(ir.dumps(summary), encoding="utf-8")
    (root / "summary.md").write_text(render_summary(summary), encoding="utf-8")
    return summary


def _pct(x):
    return "–" if x is None else f"{100 * x:.0f}%"


def _num(x, d=2):
    return "–" if x is None else f"{x:.{d}f}"


def render_summary(s: dict) -> str:
    lines = [f"# Intent from tests: {s['name']}", "",
             f"Reader and judge: {s['model']}, effort {s['effort']}, Claude Code {s['claude_code']}. Means over inputs "
             "of each input's mean over its repeats; ± is the mean spread (max − min) between repeats.", "",
             "| Group | Source | n | Rules | Recall | Recall of met | Stated (met) | Latent (met) | Minus baseline (met) "
             "| Latent minus baseline | Contradicts /rule (of a met item) | Incidental /rule | Stale /rule "
             "| Retired implied | Cost |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for cell, row in s["cells"].items():
        g, v = cell.split("|")
        m, sp, mb = row["mean"], row["repeat_spread"], row.get("minus_baseline") or {}
        lines.append(f"| {g} | {v} | {len(row['inputs'])} | {_num(m['rules'], 0)} | {_pct(m['recall'])} ±{_pct(sp['recall'])} "
                     f"| {_pct(m['recall_of_met'])} ±{_pct(sp['recall_of_met'])} | {_pct(m['by_group_of_met.stated.recall'])} "
                     f"| {_pct(m['by_group_of_met.latent.recall'])} | {_pct(mb.get('recall_of_met'))} "
                     f"| {_pct(mb.get('latent_of_met'))} | {_num(m['rates_per_rule.contradicts'])} "
                     f"({_num(m['contradicting_rules.against_met_per_rule'])}) "
                     f"| {_num(m['rates_per_rule.incidental'])} | {_num(m['rates_per_rule.stale'])} "
                     f"| {_pct(m['stale_items_share'])} | ${row['cost_usd']:.2f} |")
    if s["refused"]:
        lines += ["", "Refused (over the size cap):", ""] + [f"- {l}: {why}" for l, why in s["refused"].items()]
    lines += ["", f"Total notional cost ${s['cost_usd']:.2f}; tokens {s['tokens']}.", ""]
    return "\n".join(lines)


def rescore(name: str) -> int:
    """Recompute every recorded repeat's scores from its reader answer, judgment, and oracle, with no model call, and
    rebuild each input's result (for a change to scoring)."""
    n = 0
    for d in sorted(p for p in (RUNS / name).iterdir() if p.is_dir()):
        rf = d / "result.json"
        if not rf.exists() or not (d / "oracle.json").exists():
            continue
        result = json.loads(rf.read_text())
        if result.get("refused"):
            continue
        o = json.loads((d / "oracle.json").read_text())
        items, met = ir.items_from_json(o["items"]), (set(o["met"]) if o["met"] is not None else None)
        scores = []
        for rdir in sorted(d.glob("rep-*")):
            if not (rdir / "judgment.json").exists() or not (rdir / "score.json").exists():
                continue
            rec = json.loads((rdir / "reader.json").read_text())
            j = json.loads((rdir / "judgment.json").read_text())
            s = ir.score(len(rec["rules"]), {int(k): v for k, v in j["mappings"].items()}, items, met)
            s["reader_rules_listed"] = rec["listed"]
            s["reader_rules_dropped"] = rec["listed"] - len(rec["rules"])
            saved = json.loads((rdir / "score.json").read_text())
            saved["score"] = s
            (rdir / "score.json").write_text(ir.dumps(saved), encoding="utf-8")
            scores.append(s)
            n += 1
        result["repeats"] = scores
        result["summary"] = ir.summarize_repeats(scores) if scores else None
        rf.write_text(ir.dumps(result), encoding="utf-8")
    return n


# ------------------------------------------------------------------------------------------ retired intent


def extract_retired(repo: str, segment: str, out: Path, commit: str = "HEAD", ask=None) -> dict:
    files, sha = read_repo(repo, commit)
    path, current = segment_spec(files, segment)
    log = subprocess.run(["git", "--no-optional-locks", "-C", repo, "log", "--follow", "-p", "--format=COMMIT %h %cs",
                          sha, "--", path], capture_output=True, text=True, check=True).stdout
    removed = ir.removed_spec_lines(log)
    cands = ir.retired_candidates(removed, current)
    ids = ir.spec_ids(current)
    ask = ask or make_ask(1500)
    answers: dict[int, dict] = {}
    calls = []
    for k in range(0, len(cands), RETIRED_BATCH):
        batch = cands[k:k + RETIRED_BATCH]
        prompt = ir.retired_prompt(current, batch)
        for _ in range(ir.ATTEMPTS):
            structured, use = ask(prompt, ir.RETIRED_SCHEMA)
            problems = ir.check_retired(structured, batch, ids)
            calls.append({"candidates": [c["n"] for c in batch], "structured": structured, "problems": problems,
                          "usage": use})
            bad = {int(n) for p in problems for n in re.findall(r"candidate (\d+)", p)}
            whole = not isinstance((structured or {}).get("candidates"), list)
            if not whole:
                for a in structured["candidates"]:
                    if a.get("candidate") in {c["n"] for c in batch} and a["candidate"] not in bad:
                        answers[a["candidate"]] = a
            if all(c["n"] in answers for c in batch):
                break
    # a duplicate whose original went unanswered stands on its own
    for a in answers.values():
        if a.get("duplicate_of") and a["duplicate_of"] not in answers:
            a["duplicate_of"] = 0
    merged = {"candidates": [answers[n] for n in sorted(answers)]}
    items = ir.retired_items([c for c in cands if c["n"] in answers], merged)
    result = {"repo_commit": sha, "spec": path, "removed_lines": len(removed), "candidates": cands,
              "answers": merged["candidates"], "unresolved": [c["n"] for c in cands if c["n"] not in answers],
              "items": ir.items_json(items), "calls": calls,
              "cost_usd": round(sum((c["usage"] or {}).get("cost_usd") or 0 for c in calls), 4),
              "tokens": _tokens([c["usage"] for c in calls])}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(ir.dumps(result), encoding="utf-8")
    print(f"{path}: {len(removed)} removed spec lines, {len(cands)} candidates, {len(items)} retired items, "
          f"{len(result['unresolved'])} unresolved, ${result['cost_usd']:.2f}", flush=True)
    return result


# ------------------------------------------------------------------------------------------------------ main


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("batch", help="run every input in a plan, resumably")
    b.add_argument("--plan", required=True)
    b.add_argument("--workers", type=int, default=2)
    b.add_argument("--repeats", type=int, default=REPEATS)
    b.add_argument("--only", default="", help="comma-separated labels to run")
    s = sub.add_parser("summarize")
    s.add_argument("--name", required=True)
    s.add_argument("--rescore", action="store_true", help="recompute every repeat's scores from its records first")
    r = sub.add_parser("retired", help="extract a segment's retired intent from its spec file's history")
    r.add_argument("--dir", required=True)
    r.add_argument("--segment", required=True)
    r.add_argument("--commit", default="HEAD")
    r.add_argument("--out", required=True)
    i = sub.add_parser("input", help="build one plan input and print its size, without calling a model")
    i.add_argument("--plan", required=True)
    i.add_argument("--label", required=True)
    args = ap.parse_args(argv)

    if args.cmd == "summarize":
        if args.rescore:
            print(f"rescored {rescore(args.name)} repeats")
        print(render_summary(summarize(args.name)))
        return 0
    if args.cmd == "retired":
        extract_retired(args.dir, args.segment, _path(args.out), args.commit)
        return 0
    plan = json.loads(_path(args.plan).read_text())
    if args.cmd == "input":
        spec = next(x for x in plan["inputs"] if x["label"] == args.label)
        built = build_input(spec)
        prompt = ir.reader_prompt(spec["source"], built["inputs"], neutral=bool(spec.get("neutral")))
        print(json.dumps({k: v for k, v in built.items() if k != "inputs"}, indent=1))
        print(f"{len(built['inputs'])} files, about {ir.estimate_tokens(prompt):,} tokens with the prompt")
        return 0
    if not os.environ.get(executor.TOKEN_ENV):
        print("run under ../plumbing/with-token.sh", file=sys.stderr)
        return 2
    only = set(filter(None, args.only.split(",")))
    specs = [x for x in plan["inputs"] if not only or x["label"] in only]
    root = RUNS / plan["name"]

    def one(spec):
        try:
            return run_input(spec, root / spec["label"], repeats=args.repeats)
        except Exception as e:  # one input's failure doesn't stop the batch; it is recorded and printed
            (root / spec["label"]).mkdir(parents=True, exist_ok=True)
            (root / spec["label"] / "error.txt").write_text(repr(e), encoding="utf-8")
            print(f"{spec['label']}: error: {e!r}", flush=True)
            return None
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(one, specs))
    print(render_summary(summarize(plan["name"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
