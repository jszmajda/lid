"""Grading one checkpoint of a Rust library (Clowder): keeping, the arm's edits to existing tests, and new intent.

Design: "Later seeds and variants" (the falsification test's grading) and "Graders" in the notebook's design.md.

1. **Export.** The fork's commit is cloned out of its workspace into a checkpoint volume (/work/app), with build output
   at /work/target and grading output at /work/out.
2. **Keeping.** Each held-out test file goes back in as a test target of its own (`tests/heldout_<name>/`, beside the
   helper modules its directory had, as they were), so a file the arm's code no longer compiles against fails alone.
   Each target runs with `cargo test`; results are kept per test, and compile failures apart.
3. **Edits to existing tests.** `git diff` from the fork's starting commit: test files the arm edited, deleted, or
   renamed, the lines it changed in them, and the `#[test]` functions before and after.
4. **New intent.** Probes in the probes.md format, as for the other seeds:
   - extraction (Sonnet) reads the arm's diff and writes a reference for calling what it added from a Rust test;
   - execution (Haiku), per batch, writes one test target per probe, `tests/probe_<id>.rs`, that performs the scenario
     through the arm's own API and prints what it observes; it never sees the expected observations. The harness
     then runs each probe's test itself, so the judge reads real output;
   - judgment (Sonnet) compares each probe's expected observation with its test and output, with the verdict schema
     and checks of the other seeds. A probe the software can't do is "couldn't exercise" with cause "service" (the
     software under test); one the executor got wrong, cause "execution".
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from . import executor, grading

MAX_OUTPUT = 20000  # characters of one probe's output the judge sees; the whole output stays on disk
TEST_LINE = re.compile(r"(?m)^test (\S+) \.\.\. (ok|FAILED|ignored)\b")  # "ignored" may carry a reason


# ------------------------------------------------------------------------------------------------- keeping


def _module_dir(path: str) -> bool:
    return bool(re.fullmatch(r"crates/[^/]+/tests/[^/]+/[^/]+\.rs", path))


def held_out_target_names(held: list[str]) -> list[tuple[str, str]]:
    """(crate directory, test target) for each held-out file."""
    return [(p.split("/")[1], f"heldout_{Path(p).stem}") for p in held]


def held_out_targets(held_dir: Path, held: list[str]) -> dict[str, str]:
    """The files that put each held-out test back as a target of its own: a module file goes in its own directory
    with a main.rs declaring it and the helper modules its original directory declared (copied as they were), and the
    original main.rs's crate attributes; a file that was a target already comes back under a new name."""
    out: dict[str, str] = {}
    for path in held:
        crate, target = path.split("/")[1], f"heldout_{Path(path).stem}"
        text = (held_dir / path).read_text(encoding="utf-8")
        if not _module_dir(path):
            out[f"crates/{crate}/tests/{target}.rs"] = text
            continue
        src_dir = path.rsplit("/", 1)[0]
        main = (held_dir / src_dir / "main.rs")
        main_text = main.read_text(encoding="utf-8") if main.exists() else ""
        attrs = [l for l in main_text.splitlines() if l.startswith("#![")]
        declared = re.findall(r"(?m)^\s*(?:pub\s+)?mod\s+(\w+)\s*;", main_text)
        helpers = [m for m in declared if (held_dir / src_dir / m).is_dir() or
                   ((held_dir / src_dir / f"{m}.rs").exists() and f"{src_dir}/{m}.rs" not in held)]
        dest = f"crates/{crate}/tests/{target}"
        for h in helpers:
            hdir = held_dir / src_dir / h
            if hdir.is_dir():
                for f in sorted(hdir.rglob("*")):
                    if f.is_file():
                        out[f"{dest}/{h}/{f.relative_to(hdir)}"] = f.read_text(encoding="utf-8")
            else:
                out[f"{dest}/{h}.rs"] = (held_dir / src_dir / f"{h}.rs").read_text(encoding="utf-8")
        out[f"{dest}/main.rs"] = "\n".join(attrs + [""] + [f"mod {h};" for h in helpers] + [f"mod {Path(path).stem};", ""])
        out[f"{dest}/{Path(path).stem}.rs"] = text
    return out


def _target_result(output: str) -> dict:
    tests = {name: status for name, status in TEST_LINE.findall(output)}
    m = re.search(r"EXIT=(\d+)\s*$", output)
    code = int(m.group(1)) if m else None
    compile_failed = bool(re.search(r"(?m)^error: could not compile", output)) or (code not in (0, None) and not tests
                                                                                    and "test result:" not in output)
    return {"exit_code": code, "tests": tests, "compile_failed": compile_failed,
            "errors": re.findall(r"(?m)^error(?:\[E\d+\])?: .*$", output)[:20] if compile_failed else []}


def keeping_result(runs: list[tuple[str, str, str]], expected: dict[str, int] | None = None) -> dict:
    """Per target and in total, from each (crate, target, cargo output). expected: #[test] count per target."""
    targets = {t: {"crate": c, **_target_result(out)} for c, t, out in runs}
    if expected:
        for t, n in expected.items():
            if t in targets:
                targets[t]["tests_expected"] = n
    passed = sum(s == "ok" for r in targets.values() for s in r["tests"].values())
    failed = sum(s == "FAILED" for r in targets.values() for s in r["tests"].values())
    total_expected = sum(r.get("tests_expected", 0) for r in targets.values())
    return {"targets": targets, "passed": passed, "failed": failed,
            "compile_failed": sorted(t for t, r in targets.items() if r["compile_failed"]),
            "share_passed": passed / (passed + failed) if passed + failed else None,
            "share_of_held_out_passed": passed / total_expected if total_expected else None}


# ------------------------------------------------------------------------------------- edits to existing tests


def _is_test_path(path: str) -> bool:
    return "/tests/" in f"/{path}"


def _numstat_paths(path: str) -> list[str]:
    m = re.fullmatch(r"(.*)\{(.*) => (.*)\}(.*)", path)
    if m:
        return [f"{m.group(1)}{m.group(2)}{m.group(4)}".replace("//", "/"), f"{m.group(1)}{m.group(3)}{m.group(4)}".replace("//", "/")]
    if " => " in path:
        return path.split(" => ", 1)
    return [path]


def test_edits(name_status: str, numstat: str, count_tests: Callable[[str, str], int]) -> dict:
    """What the arm did to test files that existed when it started, from `git diff --name-status -M` and `--numstat`.
    count_tests(rev, path) counts #[test] functions in a file at "base" or "head"."""
    edited, deleted, renamed, added = [], [], [], []
    for line in name_status.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, paths = parts[0], parts[1:]
        if not any(_is_test_path(p) for p in paths):
            continue
        if status.startswith("M"):
            edited.append(paths[0])
        elif status.startswith("D"):
            deleted.append(paths[0])
        elif status.startswith("R"):
            renamed.append([paths[0], paths[1]])
        elif status.startswith("A"):
            added.append(paths[0])
    pre = set(edited) | set(deleted) | {r[0] for r in renamed}
    added_lines = removed_lines = 0
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) < 3 or parts[0] == "-":
            continue
        if _numstat_paths(parts[2])[0] in pre:
            added_lines += int(parts[0])
            removed_lines += int(parts[1])
    before = sum(count_tests("base", p) for p in sorted(pre))
    after = sum(count_tests("head", p) for p in edited) + sum(count_tests("head", r[1]) for r in renamed)
    return {"edited": sorted(edited), "deleted": sorted(deleted), "renamed": sorted(renamed), "added": sorted(added),
            "lines_added": added_lines, "lines_removed": removed_lines, "tests_before": before, "tests_after": after,
            "tests_removed": max(0, before - after)}


# --------------------------------------------------------------------------------------------------- probes


def probe_target(pid: str) -> str:
    return "probe_" + re.sub(r"[^a-z0-9]+", "_", pid.lower()).strip("_")


def probe_log_lines(results: dict[str, dict]) -> list[dict]:
    """The judge's evidence, numbered: each probe's test source and its output, or a note that there is none."""
    lines, seq = [], 0
    for pid, r in results.items():
        if r.get("source") is None and r.get("output") is None:
            seq += 1
            lines.append({"seq": seq, "probe": pid, "kind": "missing", "text": "The executor wrote no test for this probe."})
            continue
        out = r.get("output") or "(no output)"
        if len(out) > MAX_OUTPUT:
            out = out[:MAX_OUTPUT] + f" ...[cut: {len(out) - MAX_OUTPUT} more characters]"
        seq += 1
        lines.append({"seq": seq, "probe": pid, "kind": "test source", "text": r.get("source") or "(none)"})
        seq += 1
        lines.append({"seq": seq, "probe": pid, "kind": "test output", "text": out})
    return lines


def log_for_judge(lines: list[dict]) -> str:
    return "\n".join(json.dumps(l) for l in lines)


@dataclass(frozen=True)
class RustGraders:
    image: str
    roles_volume: str
    claude_code: str
    extraction_model: str = "claude-sonnet-5-5"
    execute_model: str = "claude-haiku-5-5"
    judge_model: str = "claude-sonnet-5-5"
    effort: str = "medium"

    def role(self, model: str, **kw) -> executor.RoleSession:
        # Graders reach crates.io but not the seed's public repository, like the arms.
        return executor.RoleSession(image=self.image, config_volume=self.roles_volume, model=model,
                                    claude_code_version=self.claude_code, effort=self.effort,
                                    isolation=executor.Isolation.for_public_seed(window="1m"), **kw)


def extraction_prompt(base: str) -> str:
    return grading._template("extraction-rust.md", BASE=base)


def execution_prompt(bid: str) -> str:
    return grading._template("grade-execute-rust.md", BATCH=bid)


def judge_prompt(batch, lines: list[dict], conventions: str = "") -> str:
    return grading._template("grade-judge-rust.md", PROBES=grading.render_for_judgment(batch, conventions),
                             LOG=log_for_judge(lines))


def _usage(rec) -> dict:
    return {"cost_usd": rec.usage.reported_cost_usd, "duration_s": round(rec.duration_s, 1),
            "models": {m: asdict(c) for m, c in (rec.usage.models or {}).items()}}


RERUN = ("cd /work/app && mkdir -p /work/out/probes && for f in crates/*/tests/{t}.rs; do [ -f \"$f\" ] || continue; "
         "cp \"$f\" /work/out/probes/{t}.rs; crate=$(echo \"$f\" | cut -d/ -f2); "
         "CARGO_TARGET_DIR=/work/target timeout 900 cargo test --offline --manifest-path crates/$crate/Cargo.toml "
         "--test {t} -- --nocapture --test-threads=1 > /work/out/probes/{t}.log 2>&1; "
         "echo \"EXIT=$?\" >> /work/out/probes/{t}.log; done; true")


def grade_probes(ck, g: RustGraders, probeset: grading.ProbeSet, probes: list, *, base: str, out: Path, volume: str,
                 batch_size: int = 4, run_role: Callable = executor.run_role, attempts: int = 3) -> dict:
    """Extraction, then for each batch: execution, the harness's own run of each probe's test, and judgment."""
    out.mkdir(parents=True, exist_ok=True)
    rec = run_role(g.role(g.extraction_model, tools=("Bash", "Read", "Write", "Edit", "Glob", "Grep"),
                          workspace_volume=volume, timeout_s=2400), extraction_prompt(base))
    reference = ck.get("/work/out/reference.md") or ""
    (out / "reference.md").write_text(reference, encoding="utf-8")
    sessions = {"extraction": {"usage": _usage(rec), "problems": [] if reference.strip() else ["no reference"]}}
    conventions = probeset.setup_notes
    verdicts: dict[str, dict] = {}
    for k, batch in enumerate(grading.batches(probes, batch_size), start=1):
        bid = f"b{k:02d}"
        bdir = out / bid
        bdir.mkdir(parents=True, exist_ok=True)
        rendered = grading.render_for_execution(batch, conventions)
        ck.put(f"/work/out/probes-{bid}.md", rendered)
        (bdir / "probes.md").write_text(rendered, encoding="utf-8")
        try:
            rec = run_role(g.role(g.execute_model, tools=("Bash", "Read", "Write", "Edit"), workspace_volume=volume,
                                  timeout_s=2400), execution_prompt(bid))
            sessions[bid] = {"usage": _usage(rec), "reply": rec.text}
        except executor.RoleFailed as e:
            sessions[bid] = {"error": str(e)}
        results = {}
        for p in batch:
            t = probe_target(p.id)
            ck.sh(RERUN.replace("{t}", t), check=False)
            results[p.id] = {"source": ck.get(f"/work/out/probes/{t}.rs"), "output": ck.get(f"/work/out/probes/{t}.log")}
            for kind in ("source", "output"):
                if results[p.id][kind] is not None:
                    (bdir / f"{t}.{'rs' if kind == 'source' else 'log'}").write_text(results[p.id][kind], encoding="utf-8")
        lines = probe_log_lines(results)
        tries = []
        for _ in range(attempts):
            rec = run_role(g.role(g.judge_model, timeout_s=1200), judge_prompt(batch, lines, conventions),
                           json_schema=json.dumps(grading.JUDGE_SCHEMA, separators=(",", ":")))
            problems = grading.check_verdicts(rec.structured or {}, batch, lines)
            tries.append({"structured": rec.structured, "problems": problems, "usage": _usage(rec)})
            if not problems:
                break
        final = {v["probe"]: v for v in (tries[-1]["structured"] or {}).get("verdicts", [])} if not tries[-1]["problems"] else {}
        (bdir / "judgment.json").write_text(json.dumps({"tries": tries, "verdicts": final, "lines": lines}, indent=1),
                                           encoding="utf-8")
        verdicts.update(final)
    probe_verdicts = {pid: v["verdict"] for pid, v in verdicts.items()}
    items = grading.item_verdicts(probe_verdicts, probes)
    result = {"probes": probe_verdicts, "items": items, "details": verdicts, "sessions": sessions,
              "execution_faults": grading.execution_faults(verdicts)}
    (out / "verdicts.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    return result


# ---------------------------------------------------------------------------------------------- the checkpoint


@dataclass
class RustCheckpoint:
    """A fork's commit checked out at /work/app in its own volume, with build output at /work/target."""
    name: str
    commit: str
    image: str
    runner: Callable = subprocess.run

    @property
    def volume(self) -> str:
        return f"ce-gr-{self.name}-ckpt"

    def sh(self, script: str, stdin: str | None = None, check: bool = True) -> str:
        p = self.runner(["docker", "run", "--rm", "-i", "--network", "none", "-v", f"{executor._volume(self.volume)}:/work",
                         "-w", "/work", self.image, "sh", "-c", script], input=stdin, capture_output=True, text=True)
        if check and p.returncode != 0:
            raise RuntimeError(f"checkpoint command failed ({p.returncode}): {script[:160]}: {p.stderr[-500:]}")
        return p.stdout

    def put(self, path: str, text: str) -> None:
        self.sh(f"mkdir -p \"$(dirname '{path}')\" && cat > '{path}'", stdin=text)

    def get(self, path: str) -> str | None:
        p = self.runner(["docker", "run", "--rm", "-v", f"{executor._volume(self.volume)}:/work", self.image, "cat", path],
                        capture_output=True, text=True)
        return p.stdout if p.returncode == 0 else None

    def export(self, workspace_volume: str) -> None:
        self.runner(["docker", "run", "--rm", "-v", f"{executor._volume(workspace_volume)}:/src:ro",
                     "-v", f"{executor._volume(self.volume)}:/work", self.image, "sh", "-c",
                     # .git alone, checked out at the exact commit: a commit on a detached HEAD (jj leaves one, and
                     # so does the harness's own) is found, and no jj state, build output, or untracked file comes along
                     f"find /work -mindepth 1 -delete && mkdir -p /work/app /work/out && cp -a /src/.git /work/app/.git && "
                     f"cd /work/app && git checkout -q -f --detach {self.commit} && git clean -fdxq"],
                    check=True, capture_output=True, text=True)

    def drop_target(self) -> None:
        self.sh("rm -rf /work/target", check=False)
