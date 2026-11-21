"""prior-data and prior-observations: a probe that needs something from an earlier change gets it from an earlier
run on the build the graded one descends from (its lineage: a fork's earlier changes are its parent's).

- prior-data: step 1 says "At change N, ... prepare SX" and what to do, then "Retain the resulting storage". That
  step runs once, on the lineage's build after change N, in a grading of its own (grading/earlier-cNN/). The executor
  runs `gt retain` where the step says to retain the storage (the harness retains it at the end if it never does), so
  the storage is kept exactly as prepared, with the clock at that moment, before anything the step does afterwards on
  a copy (such as a baseline's requests). Kept, in prior/<probe>/: the storage (storage.tar: the data and its clock)
  and record.json: the preparation's whole execution log, its KEEP marks (identifiers, addresses and request forms the
  step kept) and the executor's notes. The checker gets the record's notes, marks and requests with the scenario; the
  judge gets its whole log with the run's.
- The storage then reaches the build under test as an owner's data would: opened in turn by the build of every change
  after the preparation, up to and including the build under test (open_in_turn), each starting its service on it at
  the retained clock (running any upgrade of its own), then stopping. Each result is kept (grading/opened/<probe>/cNN
  under the lineage trajectory that owns change NN), so a later grading carries on from the last one. The check runs on
  a copy of the result (`gt restore PRIOR-<probe>`), so nothing a probe does carries forward. A build whose service
  doesn't come up on the storage is the arm's fault, recorded at that build: the build under test failing fails the
  probe there; an earlier one is recorded and the chain carries on with what it left. A build no start spec can start
  at all is the grader's fault: the chain stops and the probe isn't run.
- prior-observations: the probe also runs on the lineage's build at the change before the one graded, in that
  change's earlier grading (observations/<probe>.json: its log and notes; for a prior-data probe, its later steps on
  a copy of the retained storage). The checker and the judge get that run too.

"""

from __future__ import annotations

import fcntl
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

PRIOR_DATA, PRIOR_OBSERVATIONS = "prior-data", "prior-observations"
_PREP = re.compile(r"At change (\d+)\b[^\n]*?\bprepare (S\d+)")
_STEP = re.compile(r"(?m)^\s*(?=\d+\.\s)")


@dataclass(frozen=True)
class Preparation:
    change: int
    setup: str
    step: str


def needs_prior_data(probe) -> bool:
    return any(n.startswith(PRIOR_DATA) for n in probe.needs)


def needs_prior_observations(probe) -> bool:
    return any(n.startswith(PRIOR_OBSERVATIONS) for n in probe.needs)


def steps(scenario: str) -> list[str]:
    return [s.strip() for s in _STEP.split(scenario.strip()) if s.strip()]


def preparation(probe) -> Preparation | None:
    """A prior-data probe's preparation: its first step, at the change and on the setup it names."""
    if not needs_prior_data(probe):
        return None
    first = steps(probe.scenario)[0] if probe.scenario.strip() else ""
    m = _PREP.search(first)
    return Preparation(int(m.group(1)), m.group(2), first) if m else None


def check_steps(probe) -> str:
    """The steps after a prior-data probe's preparation, as the build under test runs them."""
    return "\n".join(f"  {s}" for s in steps(probe.scenario)[1:]).strip()


def _meta(runs: Path, tid: str) -> dict:
    return json.loads((runs / tid / "trajectory.json").read_text())


def lineage_owner(runs: Path, tid: str, change: int) -> tuple[str, str] | None:
    """The trajectory whose build after `change` the graded one descends from, and that build's commit: the run
    itself where the change is its own, else its parent's (a course or reliance fork's earlier changes, or a forked
    trajectory's changes up to the one it was forked after)."""
    meta = _meta(runs, tid)
    if meta.get("kind") in ("course", "reliance"):  # a fork of one change (run_course_forks.py)
        if change == meta.get("change"):
            key = "reliance" if meta["kind"] == "reliance" else str(change)
            commit = (meta.get("changes", {}).get(key) or {}).get("commit")
            return (tid, commit) if commit else None
        return lineage_owner(runs, meta["fork_of"], change)
    if meta.get("fork_of") and meta.get("from_change") is not None and change <= meta["from_change"]:
        return lineage_owner(runs, meta["fork_of"], change)
    commit = (meta.get("changes", {}).get(str(change)) or {}).get("commit")
    return (tid, commit) if commit else None


def earlier_dir(runs: Path, owner: str, change: int) -> Path:
    return runs / owner / "grading" / f"earlier-c{change:02d}"


def prep_dir(runs: Path, owner: str, change: int, pid: str) -> Path:
    return earlier_dir(runs, owner, change) / "prior" / pid


def obs_path(runs: Path, owner: str, change: int, pid: str) -> Path:
    return earlier_dir(runs, owner, change) / "observations" / f"{pid}.json"


def _have_prep(runs, owner, change, pid) -> bool:
    d = prep_dir(runs, owner, change, pid)
    return (d / "record.json").exists() and (d / "storage.tar").exists()


def _wants(runs: Path, tid: str, change: int, probe) -> list[tuple[str, int, str, str]]:
    """(owner, change, "prepare" or "observe", why-if-unresolvable) for each earlier run this grading needs."""
    out = []
    prep = preparation(probe)
    if needs_prior_data(probe):
        if prep is None:
            out.append(("", -1, "prepare", "its first step names no change and setup to prepare"))
        else:
            o = lineage_owner(runs, tid, prep.change)
            out.append((o[0], prep.change, "prepare", "") if o else ("", prep.change, "prepare",
                                                                      f"no build after change {prep.change} in its lineage"))
    if needs_prior_observations(probe):
        o = lineage_owner(runs, tid, change - 1)
        out.append((o[0], change - 1, "observe", "") if o else ("", change - 1, "observe",
                                                                 f"no build after change {change - 1} in its lineage"))
    return out


def requirements(runs: Path, tid: str, change: int, probes,
                 kinds=("prepare", "observe")) -> dict[tuple[str, int], dict[str, list[str]]]:
    """The earlier runs not yet recorded that grading these probes at `change` on `tid` needs, by lineage build."""
    need: dict[tuple[str, int], dict[str, list[str]]] = {}
    for p in probes:
        for owner, n, what, why in _wants(runs, tid, change, p):
            if why or what not in kinds:
                continue
            done = _have_prep(runs, owner, n, p.id) if what == "prepare" else obs_path(runs, owner, n, p.id).exists()
            if not done:
                cell = need.setdefault((owner, n), {"prepare": [], "observe": []})
                cell[what].append(p.id)
    return need


def ensure(runs: Path, tid: str, change: int, probes, *, seed: str, run: Callable[[list[str]], int],
           kinds=("prepare", "observe")) -> dict[str, str]:
    """Run every earlier run these probes need and lack, each once (under a lock, so two gradings needing the same
    one don't both run it). Returns the probes that still lack one, with why: they are reported as not run."""
    probes = [p for p in probes if needs_prior_data(p) or needs_prior_observations(p)]
    for (owner, n), what in sorted(requirements(runs, tid, change, probes, kinds).items(), key=lambda kv: kv[0][1]):
        lock = earlier_dir(runs, owner, n).with_suffix(".lock")
        lock.parent.mkdir(parents=True, exist_ok=True)
        with open(lock, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            again = requirements(runs, tid, change, [p for p in probes if p.id in what["prepare"] + what["observe"]], kinds)
            what = again.get((owner, n))
            if what:
                cmd = [sys.executable, "grade_checkpoint.py", "--id", owner, "--change", str(n), "--seed", seed]
                cmd += ["--prepare", ",".join(what["prepare"])] if what["prepare"] else []
                cmd += ["--observe", ",".join(what["observe"])] if what["observe"] else []
                run(cmd)
    missing = {}
    for p in probes:
        for owner, n, kind, why in _wants(runs, tid, change, p):
            if kind not in kinds:
                continue
            if why:
                missing[p.id] = why
            elif kind == "prepare" and not _have_prep(runs, owner, n, p.id):
                missing[p.id] = f"its preparation at change {n} on {owner} didn't complete"
            elif kind == "observe" and not obs_path(runs, owner, n, p.id).exists():
                missing[p.id] = f"its earlier run at change {n} on {owner} didn't complete"
    return missing


def records(runs: Path, tid: str, change: int, probe) -> tuple[dict | None, dict | None, Path | None]:
    """The probe's preparation record, its earlier observations, and the retained storage's tar, where there are."""
    rec = obs = storage = None
    for owner, n, kind, why in _wants(runs, tid, change, probe):
        if why:
            continue
        if kind == "prepare" and _have_prep(runs, owner, n, probe.id):
            d = prep_dir(runs, owner, n, probe.id)
            rec, storage = json.loads((d / "record.json").read_text()), d / "storage.tar"
        elif kind == "observe" and obs_path(runs, owner, n, probe.id).exists():
            obs = json.loads(obs_path(runs, owner, n, probe.id).read_text())
    return rec, obs, storage


def opened_path(runs: Path, owner: str, change: int, pid: str) -> Path:
    return runs / owner / "grading" / "opened" / pid / f"c{change:02d}.tar"


def open_in_turn(runs: Path, tid: str, change: int, probes, *,
                 hop: Callable[[int, str, str, dict[str, bytes]], dict[str, dict]]) -> dict[str, dict]:
    """Each prior-data probe's prepared storage, opened in turn by the build of every change from the one after its
    preparation up to `change`, starting from the latest copy already kept along the lineage. hop(k, owner, commit,
    {probe: storage}) opens the storages on change k's build and returns, per probe, whether its service came up
    ("came_up": True, False, or None when no start spec could start the build at all), the storage as it left it, and
    any error. Returns per probe: the storage for the build under test, every hop, whether the last came up, and a
    grader fault, if any, that stopped the chain."""
    state: dict[str, dict] = {}
    for p in probes:
        prep = preparation(p)
        if prep is None or prep.change > change:
            continue
        o = lineage_owner(runs, tid, prep.change)
        if not o or not _have_prep(runs, o[0], prep.change, p.id):
            continue
        start, data = prep.change, (prep_dir(runs, o[0], prep.change, p.id) / "storage.tar").read_bytes()
        for k in range(change, prep.change, -1):  # the latest copy kept along this lineage
            ok = lineage_owner(runs, tid, k)
            if ok and opened_path(runs, ok[0], k, p.id).exists():
                start, data = k, opened_path(runs, ok[0], k, p.id).read_bytes()
                break
        state[p.id] = {"storage": data, "at": start, "hops": [], "final_came_up": True if start == change else None,
                       "grader_fault": None}
    for k in range(min((s["at"] for s in state.values()), default=change) + 1, change + 1):
        owner = lineage_owner(runs, tid, k)
        todo = {pid: s["storage"] for pid, s in state.items() if s["at"] < k and not s["grader_fault"]}
        if not todo:
            continue
        if owner is None:
            for pid in todo:
                state[pid].update(grader_fault=f"no build for change {k} in the lineage", storage=None)
            continue
        got = hop(k, owner[0], owner[1], todo)
        for pid in todo:
            r = got.get(pid) or {"came_up": None, "error": "no result"}
            entry = {"change": k, "owner": owner[0], "came_up": r.get("came_up"), "error": r.get("error"),
                     "spec_from": r.get("spec_from")}
            state[pid]["hops"].append(entry)
            if r.get("came_up") is None:  # no start spec could start this build: the grader's fault
                state[pid].update(grader_fault=f"change {k}'s build couldn't be started: {r.get('error')}", storage=None)
                continue
            state[pid].update(storage=r["storage"], at=k, final_came_up=bool(r["came_up"]))
            f = opened_path(runs, owner[0], k, pid)
            f.parent.mkdir(parents=True, exist_ok=True)
            tmp = f.with_suffix(".tmp")
            tmp.write_bytes(r["storage"])
            tmp.replace(f)
            f.with_suffix(".json").write_text(json.dumps(entry, indent=1))
    return {pid: {k: v for k, v in s.items() if k != "at"} for pid, s in state.items()}


def unopened_verdict(result: dict, change: int) -> dict:
    """The verdict for a probe whose build under test didn't come up on the storage carried to it: the arm's fault."""
    last = result["hops"][-1] if result.get("hops") else {}
    return {"verdict": "not met", "cause": "none", "evidence": [],
            "reason": f"The build of change {change} didn't come up on the storage prepared earlier and opened in turn by "
                      f"each build since ({last.get('error') or 'its service failed to start'}), so the probe couldn't "
                      "continue: the build fails the owner's existing data."}


def keep_marks(lines: list[dict]) -> list[str]:
    out = []
    for r in lines:
        text = str((r.get("request") or {}).get("text", "")) if r.get("op") == "mark" else ""
        if text.startswith("KEEP "):
            out.append(text[5:].strip())
    return out


def prep_record(pid: str, change: int, commit: str, setup: str, lines: list[dict], *, reply: str, retained_by: str) -> dict:
    """What a preparation leaves beside its storage: the clock the storage was retained at, the KEEP marks, the
    executor's notes, and its whole log (whatever it did after retaining, on a copy, included)."""
    retained = [r for r in lines if r.get("op") in ("retain", "snapshot")]
    clock = (retained[0] if retained else (lines[-1] if lines else {})).get("clock")
    return {"probe": pid, "change": change, "commit": commit, "setup": setup, "clock": clock, "retained": retained_by,
            "keep": keep_marks(lines), "notes": reply, "log": [r for r in lines if not r.get("admin")]}


def _requests(lines: list[dict]) -> list[str]:
    out = []
    for r in lines:
        if r.get("op") == "http":
            q, a = r.get("request") or {}, r.get("response") or {}
            out.append(f"- at {r.get('clock')}: {q.get('method', 'GET')} {q.get('path')} -> {a.get('status')}")
        elif r.get("op") == "clock":
            out.append(f"- clock set to {(r.get('request') or {}).get('utc')}")
    return out


def for_checker(rec: dict | None, obs: dict | None) -> str:
    """What the checker gets with the scenario: the preparation's notes, kept identifiers and requests, and how to open
    its storage; and an earlier run's notes and requests."""
    parts = []
    if rec:
        parts += [f"Step 1 was done at change {rec['change']}'s checkpoint, on setup {rec['setup']}, and its storage was "
                  f"retained at {rec['clock']} UTC. Open that storage with `gt restore PRIOR-{rec['probe']}`: it brings back "
                  "the retained data and clock, on a copy, so nothing you do changes what was retained.",
                  "What step 1 kept (identifiers, addresses, request forms):\n" + ("\n".join(f"- {k}" for k in rec["keep"])
                                                                                   or "- (no KEEP marks)"),
                  "Its executor's notes:\n" + (rec.get("notes") or "(none)").strip(),
                  "Its requests:\n" + ("\n".join(_requests(rec["log"])) or "- (none)")]
    if obs:
        parts += [f"This probe also ran at change {obs['change']}. Its executor's notes:\n" + (obs.get("notes") or "(none)").strip(),
                  "Its requests:\n" + ("\n".join(_requests(obs["log"])) or "- (none)")]
    return "\n\n".join(parts)


def _log(lines: list[dict]) -> str:
    keep = ("clock", "op", "request", "response")
    return "\n".join(json.dumps({"earlier_seq": r.get("seq"), **{k: r[k] for k in keep if k in r}}) for r in lines)


def for_judge(rec: dict | None, obs: dict | None) -> str:
    """What the judge gets with the run's log: the preparation's whole log (any baseline it ran on a copy after
    retaining included) and an earlier run's log, as context. Its entries carry `earlier_seq`, not `seq`."""
    parts = []
    if rec:
        parts.append(f"Step 1 (the preparation) ran at change {rec['change']}'s checkpoint; its storage was retained at "
                     f"{rec['clock']} UTC (by {rec['retained']}). Its KEEP marks: {', '.join(rec['keep']) or 'none'}. Its "
                     f"whole execution log:\n<earlier-log>\n{_log(rec['log'])}\n</earlier-log>")
    if obs:
        parts.append(f"This probe's run at change {obs['change']}, the change before:\n<earlier-log>\n{_log(obs['log'])}\n"
                     "</earlier-log>")
    return "\n\n".join(parts)
