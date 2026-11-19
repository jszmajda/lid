"""The growth test's checkpoint pipeline (design.md, "The growth test"), at changes 10, 20, 30 and 40 of a trajectory.

    ../plumbing/with-token.sh python3.12 growth_checkpoint.py --id g-bare-1 --change 10 [--steps grade,flips,...]

Steps, each skipped where its record exists:

- grade: grade_checkpoint.py at the change, every applicable probe;
- flips: for every retirement, reversal, re-reversal, and rescope so far, the retired item's probes once after it and
  the new item's probes once before it, beyond their ranges (grading/flip-cNN-after|before/), each expected not met; an
  emerging change's new item once before it, recorded as anticipated or not (not a flip). Then each course fork
  (course-forks/cNN-course-K/), graded at its end on the new rule (should hold) and the retired one (should not),
  audited for stale intent, and discarded;
- reliance: each reliance change so far, graded against every rule it relies on (each should still hold, and each
  retired one stay retired), on the trajectory (grading/reliance-rNN/) and on each reliance fork
  (course-forks/rNN-reliance-K/), which is discarded once graded;
- intent: intent from tests and docs, by intent_from_tests.py (another module): a plan of the tests as written, the
  tests with names and comments replaced, the docs where the build keeps any, and the brief as the baseline, read from
  a volume of the checkpoint's commit. If that tool can't run, the plan is left ready and the step marked pending;
- stale: the stale-intent audit, on each course change so far: the tests and docs its commits touched, and those
  mentioning a term for the area its rule lives in (hidden/stale-audit-terms.json, by course change), as they stand at
  the checkpoint, each judged blind on whether anything in it contradicts current intent (with the retired intent as
  context where there is one).

Results go to ../runs/<id>/growth/checkpoint-NN/: flips.json, course-forks.json, reliance.json, stale-audit.json, and
status.json.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import executor, grading, growth, simulator, stale_audit  # noqa: E402
from plant_stale_tests import VolumeShell  # noqa: E402
from run_trajectory import CLAUDE_CODE, IMAGE, ROLES_VOLUME  # noqa: E402

STEPS = ("grade", "flips", "reliance", "intent", "stale")
PY = sys.executable


def _verdicts(path: Path) -> dict[str, str] | None:
    f = path / "verdicts.json"
    if not f.exists():
        return None
    data = json.loads(f.read_text())
    return {p: (v if isinstance(v, str) else v.get("verdict")) for p, v in (data.get("probes") or {}).items()}


def _ask_default(model: str = "claude-sonnet-5-5") -> Callable:
    role = executor.RoleSession(image=IMAGE, config_volume=ROLES_VOLUME, model=model, claude_code_version=CLAUDE_CODE,
                                effort="medium")

    def ask(prompt: str):
        r = executor.run_role(role, prompt, json_schema=json.dumps(stale_audit.SCHEMA, separators=(",", ":")))
        return r.structured, r.usage.reported_cost_usd or 0.0
    return ask


def main(argv=None, *, run: Callable[[list[str]], int] | None = None, volume: Callable[[str], object] | None = None,
         ask: Callable | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True)
    ap.add_argument("--change", type=int, required=True)
    ap.add_argument("--steps", default=",".join(STEPS))
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    ap.add_argument("--seeds", type=Path, default=HERE.parent / "seeds")
    ap.add_argument("--repeats", type=int, default=3, help="intent-from-tests readers per input")
    args = ap.parse_args(argv)
    run = run or (lambda cmd: subprocess.run(cmd, cwd=HERE).returncode)
    volume = volume or VolumeShell
    steps = [s for s in args.steps.split(",") if s]
    t, c = args.id, args.change
    meta = json.loads((args.runs / t / "trajectory.json").read_text())
    seed = meta["seed"]
    seed_dir = args.seeds / seed
    script = simulator.parse_change_script((seed_dir / "hidden" / "change-script.md").read_text(encoding="utf-8"))
    probeset = grading.parse_probes((seed_dir / "hidden" / "probes.md").read_text(encoding="utf-8"))
    oracle = simulator.parse_oracle((seed_dir / "hidden" / "oracle.md").read_text(encoding="utf-8"))
    behavior = {i.id: i.behavior for i in oracle.items}
    out = args.runs / t / "growth" / f"checkpoint-{c:02d}"
    out.mkdir(parents=True, exist_ok=True)
    status_path = out / "status.json"
    status = json.loads(status_path.read_text()) if status_path.exists() else {}
    grading_dir = args.runs / t / "grading"

    def grade(fid: str, n: int, *extra: str) -> int:
        return run([PY, "grade_checkpoint.py", "--id", fid, "--change", str(n), "--seed", seed, *extra])

    if "grade" in steps:
        if _verdicts(grading_dir / f"change-{c:02d}") is None:
            status["grade"] = {"exit": grade(t, c)}

    terms_file = seed_dir / "hidden" / "stale-audit-terms.json"
    terms = json.loads(terms_file.read_text()) if terms_file.exists() else {}
    asker: list = [ask]

    def audit_course(n: int, ch, shell, before: str, after: str, at: str | None = None) -> dict:
        """The stale-intent audit of course change n on one workspace: the tests and docs the change touched (its own
        commits, before..after) and those mentioning its area's terms, as they stand at `at` (default: after), against
        current intent, with the retired intent as context where there is one."""
        if asker[0] is None:
            asker[0] = _ask_default()
        at = at or after
        listed = shell.sh(f"cd /work && git ls-tree -r --name-only {at}", check=False).split()
        texts = {p: shell.sh(f"cd /work && git show {at}:'{p}'", check=False) for p in listed if stale_audit.is_test_or_doc(p)}
        touched = shell.sh(f"cd /work && git diff --name-only {before} {after}", check=False).split()
        chosen = stale_audit.audit_files(touched, texts, terms.get(str(n), []))
        retired = " ".join(behavior.get(i, "") for i in ch.retires).strip() or None
        result = stale_audit.audit({p: texts[p] for p in chosen}, ask=asker[0], retired=retired,
                                   current=" ".join(behavior.get(i, "") for i in ch.introduces) or "(nothing in its place)")
        return {"kind": ch.course_change.kind, "retires": list(ch.retires), "introduces": list(ch.introduces), **result}

    if "flips" in steps:
        rows = []
        for e in growth.flip_plan(script, probeset, upto=c):
            name = f"flip-c{e['course']:02d}-{e['when']}"
            if e["probes"] and _verdicts(grading_dir / name) is None:
                grade(t, e["at_change"], "--probes", ",".join(e["probes"]), "--out-name", name)
            got = _verdicts(grading_dir / name) or {}
            row = {**e, "verdicts": {p: got.get(p) for p in e["probes"]}}
            if e["expect"] == "anticipated?":  # an emerging change: did the build already do it? Not a flip
                row.update(anticipated=bool(got) and all(got.get(p) == "met" for p in e["probes"]), behaves=None)
            else:
                row["behaves"] = bool(got) and all(got.get(p) == "not met" for p in e["probes"])
            rows.append(row)
        (out / "flips.json").write_text(json.dumps(rows, indent=1))
        # each course fork: the new rule (should hold) and the retired one (should not) at its end, audited, discarded
        forks = []
        for n, ch in sorted(script.items()):
            if n > c or ch.course_change is None:
                continue
            new = growth.probes_for(probeset, ch.introduces)
            old = [x for x in growth.probes_for(probeset, ch.retires) if x not in new]
            for fork in sorted((args.runs / t / "course-forks").glob(f"c{n:02d}-course-*")):
                fm = json.loads((fork / "trajectory.json").read_text()) if (fork / "trajectory.json").exists() else {}
                if str(n) not in fm.get("changes", {}):
                    continue
                fid, where = f"{t}/course-forks/{fork.name}", fork / "grading" / "course"
                graded_now = False
                if new + old and _verdicts(where) is None:
                    graded_now = grade(fid, n, "--probes", ",".join(new + old), "--out-name", "course") == 0
                audit_path = fork / "growth" / "stale-audit.json"
                if not audit_path.exists():
                    audit_path.parent.mkdir(parents=True, exist_ok=True)
                    audit_path.write_text(json.dumps(audit_course(n, ch, volume(fm["volumes"]["workspace"]), fm["commit"],
                                                                  fm["changes"][str(n)]["commit"]), indent=1))
                if graded_now:
                    run([PY, "run_course_forks.py", "--id", t, "--kind", "course", "--course", str(n), "--fork",
                         fork.name.rsplit("-", 1)[1], "--discard"])
                got = _verdicts(where) or {}
                forks.append({"course": n, "kind": ch.course_change.kind, "run": fid, "verdicts": got,
                              "behaves": (all(got.get(x) == "met" for x in new) and all(got.get(x) == "not met" for x in old))
                              if got else None, "stale": json.loads(audit_path.read_text()).get("stale")})
        (out / "course-forks.json").write_text(json.dumps(forks, indent=1))

    if "reliance" in steps:
        rows = []
        for r, courses in growth.reliance_changes(script, upto=c).items():
            probes = growth.reliance_change_probes(script, probeset, r)
            new = set().union(*(growth.probes_for(probeset, script[x].introduces) for x in courses))
            targets = [(t, f"reliance-r{r:02d}", None)]
            for fork in sorted((args.runs / t / "course-forks").glob(f"r{r:02d}-reliance-*")):
                fm = json.loads((fork / "trajectory.json").read_text()) if (fork / "trajectory.json").exists() else {}
                if str(r) in fm.get("changes", {}):
                    targets.append((f"{t}/course-forks/{fork.name}", "reliance", fork.name.rsplit("-", 1)[1]))
            for fid, name, k in targets:
                where = args.runs / fid / "grading" / name
                if probes and _verdicts(where) is None:
                    if grade(fid, r, "--probes", ",".join(probes), "--out-name", name) == 0 and k is not None:
                        run([PY, "run_course_forks.py", "--id", t, "--kind", "reliance", "--reliance", str(r), "--fork", k,
                             "--discard"])
                got = _verdicts(where) or {}
                per_course = {}
                for x in courses:  # each rule it relies on: still in force, and the retired one still gone
                    keep = growth.probes_for(probeset, script[x].introduces)
                    gone = [q for q in growth.probes_for(probeset, script[x].retires) if q not in keep]
                    per_course[str(x)] = (any(got.get(q) != "met" for q in keep) or any(got.get(q) == "met" for q in gone)) if got else None
                rows.append({"reliance": r, "courses": courses, "run": fid, "verdicts": got, "regressed_by_course": per_course,
                             "regressed": (any(v for v in per_course.values())) if got else None})
        (out / "reliance.json").write_text(json.dumps(rows, indent=1))

    if "intent" in steps or "stale" in steps:
        ws = volume(meta["volumes"]["workspace"])
        commit = meta["changes"][str(c)]["commit"]
        paths = ws.sh(f"cd /work && git ls-tree -r --name-only {commit}", check=False).split()

    if "intent" in steps:
        name = f"growth-{t.replace('/', '-')}-c{c:02d}"
        vol = f"ce-gc-{t.replace('/', '-')}-c{c:02d}"
        run(["docker", "run", "--rm", "-v", f"{meta['volumes']['workspace']}:/src:ro", "-v", f"{vol}:/work", IMAGE, "sh",
             "-c", f"rm -rf /work/app && git clone -q /src /work/app && cd /work/app && git checkout -q {commit}"])
        oracle_ref = {"kind": "benchtime", "seed": seed, "change": c}
        common = {"group": meta.get("arm"), "volume": vol, "root": "app", "oracle": oracle_ref,
                  "verdicts": f"runs/{t}/grading/change-{c:02d}", "baseline": "brief"}
        label = f"{t.replace('/', '-')}-c{c:02d}"
        inputs = [{"label": f"{label}-tests", "source": "tests", **common},
                  {"label": f"{label}-tests-neutral", "source": "tests", "neutral": True, **common}]
        if any(p.endswith(".md") and Path(p).name.lower() != "readme.md" for p in paths):
            inputs.append({"label": f"{label}-docs", "source": "docs", **common})
        inputs.append({"label": "brief", "group": "brief", "source": "brief", "brief": f"seeds/{seed}/brief.md",
                       "oracle": oracle_ref})
        plan_path = args.runs / "intent-from-tests" / name / "plan.json"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(json.dumps({"name": name, "inputs": inputs}, indent=1))
        rel = f"runs/intent-from-tests/{name}/plan.json"
        rc = run([PY, "intent_from_tests.py", "batch", "--plan", rel, "--repeats", str(args.repeats)])
        if rc == 0:
            rc = run([PY, "intent_from_tests.py", "summarize", "--name", name])
        status["intent"] = {"state": "done" if rc == 0 else "pending", "plan": rel, "exit": rc, "name": name}
        if rc == 0:  # the checkpoint's copy is only the readers' input; a pending one stays for the rerun
            run(["docker", "volume", "rm", "-f", vol])

    if "stale" in steps:
        courses = {}
        for n, ch in sorted(script.items()):
            if n > c or ch.course_change is None:
                continue
            before = meta["changes"].get(str(n - 1), {}).get("commit") or meta.get("start_commit")
            after = meta["changes"].get(str(n), {}).get("commit")
            if before and after:  # what the change itself touched, judged as the files stand at the checkpoint
                courses[str(n)] = audit_course(n, ch, ws, before, after, at=commit)
        (out / "stale-audit.json").write_text(json.dumps({"checkpoint": c, "courses": courses}, indent=1))

    status_path.write_text(json.dumps(status, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
