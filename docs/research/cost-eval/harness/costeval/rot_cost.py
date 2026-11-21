"""Working around rot (design.md, "The growth test"): what each reliance fork's and course fork's agent spent, which
repository files it read, and how many of those the stale-intent audit flagged as stale for the fork's course change.

A fork's own measures come from its record and its turns' transcripts, and are written once beside it as
`rot-cost.json` (run_course_forks.py, as the fork finishes; rot_cost.py for forks run before that). The audit is joined
when the report is made, since it comes later: a reliance fork takes the trajectory's audit at the checkpoint nearest
the fork's snapshot among those that cover its course change (a tie goes to the earlier); a course fork takes its own
audit. The trajectory's audit is of the files as they stand at that checkpoint, which can be several changes after the
fork's snapshot. Flagged files are counted in two cuts, neither preferred: the audit's verdict "stale" alone, and
"stale" or "mixed".

Files read are the distinct repository files a Read call returned or a Bash read named (cat, head, tail, sed -n and the
rest of context_telemetry's reading forms, a partial read included); searches don't count. No listing of the fork's
repository is kept (its workspace is discarded once graded), so a Bash glob read is kept as its pattern and counts the
files of the joined audit it matches. Turns are the fork's owner rounds, each one session turn; model
calls are the main thread's API calls over them."""

from __future__ import annotations

import fnmatch
import json
from pathlib import Path
from statistics import mean, median

import context_telemetry as ct

MEASURES = "rot-cost.json"
RELIANCE_OUTCOMES = ("current", "displaced", "neither")  # the rest ("both", "undetermined", "no probe"): "other"
COURSE_OUTCOMES = {True: "behaved", False: "didn't", None: "undetermined"}
GROUPS = ("read flagged", "read none", "no audit")
CUTS = ("stale", "stale or mixed")


def _change_dir(fork: Path, meta: dict) -> tuple[str, Path]:
    if meta.get("kind") == "reliance":
        return "reliance", fork / "change-reliance"
    return str(meta["change"]), fork / f"change-{int(meta['change']):02d}"


def files_read(turns: list[dict]) -> tuple[list[str], list[str]]:
    """The distinct repository files the turns read (Read results, and Bash reads of a named file), and the
    repository-relative patterns of their Bash glob reads."""
    if not turns:
        return [], []
    root = turns[0]["root"]
    out = {rel for t in turns for p in t["read_files"] if (rel := ct.repo_rel(p, root)) is not None}
    globs = set()
    for r in (r for t in turns for r in t["bash_reads"]):
        rel = ct.repo_rel(r["path"], root)
        if rel is not None and ct.GLOB_CHARS & set(rel):
            globs.add(rel)
        elif rel is not None:
            out.add(rel)
    return sorted(out), sorted(globs)


def glob_matches(patterns: list[str], files) -> set[str]:
    """The files a glob read's patterns match, segment by segment, as context_telemetry expands them."""
    return {f for pat in patterns for f in files if len(f.split("/")) == len(pat.split("/"))
            and all(fnmatch.fnmatchcase(a, b) for a, b in zip(f.split("/"), pat.split("/")))}


def measures(fork: Path, *, write: bool = False) -> dict | None:
    """A fork's agent cost, turns, model calls, wall minutes, input / cache-read / cache-write tokens, and files read.
    None when the fork recorded no change. Read back from rot-cost.json when it was written; `write` writes it."""
    cached = fork / MEASURES
    if cached.exists():
        return json.loads(cached.read_text())
    tj = fork / "trajectory.json"
    if not tj.exists():
        return None
    meta = json.loads(tj.read_text())
    key, cdir = _change_dir(fork, meta)
    ch = (meta.get("changes") or {}).get(key)
    if not ch:
        return None
    cj = json.loads((cdir / "change.json").read_text()) if (cdir / "change.json").exists() else {}
    models = [m for t in cj.get("turns", []) for m in ((t.get("usage") or {}).get("models") or {}).values()]
    tokens = lambda *ks: sum(m.get(k) or 0 for m in models for k in ks)  # noqa: E731
    turns = [ct.parse_stream(p) for p in (ct._turn_paths(cdir) if cdir.is_dir() else [])]
    files, globs = files_read(turns)
    rec = {"run": meta.get("id") or f"{fork.parent.parent.name}/course-forks/{fork.name}", "kind": meta.get("kind"),
           "course": meta.get("course"), "at": meta.get("at"), "lag": meta.get("lag"),
           "agent_cost_usd": ch.get("agent_cost_usd"), "turns": ch.get("rounds"),
           "model_calls": sum(t["api_calls"] for t in turns), "minutes": ch.get("minutes"),
           "input_tokens": tokens("input"), "cache_read_tokens": tokens("cache_read"),
           "cache_write_tokens": tokens("cache_write_5m", "cache_write_1h"),
           "transcripts": len(turns), "files_read": files, "globs_read": globs}
    if write:
        cached.write_text(json.dumps(rec, indent=1))
    return rec


def nearest_audit(run: Path, course: int, at: int) -> tuple[int, dict] | None:
    """The trajectory's audit of `course` at the checkpoint nearest `at`, of those whose audit covers it."""
    found = []
    for p in run.glob("growth/checkpoint-[0-9][0-9]/stale-audit.json"):
        a = json.loads(p.read_text())
        x = (a.get("courses") or {}).get(str(course))
        if x is not None:
            found.append((int(a.get("checkpoint") or p.parent.name.split("-")[1]), x))
    if not found:
        return None
    return min(found, key=lambda e: (abs(e[0] - at), e[0]))


def _verdict_files(audit: dict, verdict: str) -> set[str]:
    return {p for p, f in (audit.get("files") or {}).items() if f.get("verdict") == verdict}


def record(fork: Path) -> dict | None:
    """A fork's measures joined with the audit for its course change: which of the files it read were flagged."""
    m = measures(fork)
    if m is None:
        return None
    audit, source = None, None
    if m["kind"] == "reliance":
        found = nearest_audit(fork.parent.parent, m["course"], m["at"])
        if found:
            cp, audit = found
            source = {"source": f"checkpoint {cp}", "distance": abs(cp - m["at"])}
    elif (fork / "growth" / "stale-audit.json").exists():
        audit, source = json.loads((fork / "growth" / "stale-audit.json").read_text()), {"source": "own", "distance": 0}
    out = {**m, "files_read_count": len(m["files_read"]), "files_read_via_glob": [], "audit": None, "flagged_read": None,
           "mixed_read": None}
    if audit is not None:
        stale, mixed = _verdict_files(audit, "stale"), _verdict_files(audit, "mixed")
        via_glob = glob_matches(m.get("globs_read") or [], audit.get("files") or {}) - set(m["files_read"])
        read = set(m["files_read"]) | via_glob
        out.update(audit={**source, "stale": len(stale), "mixed": len(mixed)}, files_read_count=len(read),
                   files_read_via_glob=sorted(via_glob), flagged_read=sorted(read & stale), mixed_read=sorted(read & mixed))
    return out


def group_of(rec: dict, cut: str = "stale") -> str:
    if rec.get("flagged_read") is None:
        return "no audit"
    flagged = rec["flagged_read"] + ((rec.get("mixed_read") or []) if cut == "stale or mixed" else [])
    return "read flagged" if flagged else "read none"


def groups(recs: list[dict], outcomes, cut: str = "stale") -> dict:
    """Forks that read at least one flagged file (by `cut`, one of CUTS), forks that read none, and forks with no audit
    to join: count, mean and median cost, turns, model calls and files read, the median cost over R+'s, and the
    outcomes. Reliance outcomes are current, displaced, neither and other; a course fork's (given as COURSE_OUTCOMES)
    whether it behaved."""
    out = {}
    for g in GROUPS:
        rs = [r for r in recs if group_of(r, cut) == g]
        if not rs:
            continue
        vals = lambda k: [r[k] for r in rs if r.get(k) is not None]  # noqa: E731
        stat = lambda f, k: f(vals(k)) if vals(k) else None  # noqa: E731
        if isinstance(outcomes, dict):
            counts = {name: sum(r.get("outcome") is key for r in rs) for key, name in outcomes.items()}
        else:
            counts = {o: sum(r.get("outcome") == o for r in rs) for o in outcomes}
            counts["other"] = len(rs) - sum(counts.values())
        out[g] = {"n": len(rs), "cost_mean": stat(mean, "agent_cost_usd"), "cost_median": stat(median, "agent_cost_usd"),
                  "turns_mean": stat(mean, "turns"), "turns_median": stat(median, "turns"),
                  "calls_mean": stat(mean, "model_calls"), "calls_median": stat(median, "model_calls"),
                  "files_mean": stat(mean, "files_read_count"), "files_median": stat(median, "files_read_count"),
                  "r_plus_ratio_median": stat(median, "r_plus_ratio"), "outcomes": counts}
    return out
