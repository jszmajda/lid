"""Module count and coupling at every snapshot (plan.md, M2e): from data already collected, no model calls.

    python3.12 analysis_structure.py              # every default run
    python3.12 analysis_structure.py --only g-bare-1

For each snapshot it reads the repository's files at that commit, from the run's Docker volume, read-only:

- the growth trial's trajectories g-bare-1 and g-lid-full-1, at every change 0-20, from the git history in their
  workspace volumes (each change's commit as trajectory.json records it; a symptom change that didn't fire leaves
  the commit before it, and is marked);
- the reference build g-ref-correct at changes 10, 20, 30 and 40, the same way;
- BenchTime stage 3b's nine trajectories at change 10, from the `app/` folder of each grading checkpoint volume
  (ce-g-s3b-<arm>-<k>-c10-ckpt), checked against the change-10 commit in the trajectory's workspace volume.

Measures, over the project's own Python source:

- modules: non-test source files (`.py` outside tests/, not test_*.py, *_test.py or conftest.py; `.venv`, caches and
  hidden folders excluded). Package `__init__.py` and `__main__.py` files count as modules;
- lines: non-blank lines per module, median and max, and the largest module's share of all source lines;
- coupling: import edges between the project's own modules, from each file's `import` and `from ... import`
  statements anywhere in it (relative imports resolved against the file's package, `from pkg import name` resolved to
  the submodule pkg.name when one exists, otherwise to pkg). An edge is a distinct (importer, imported) pair of two
  different source modules; imports of tests and third-party packages are ignored. Mean fan-out is edges over
  modules;
- for context, test files and their non-blank lines."""

from __future__ import annotations

import argparse
import ast
import io
import json
import statistics
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
IMAGE = "lid-cost-eval-executor-rust:2.1.323"
SKIP_DIRS = {".venv", "venv", "__pycache__", ".pytest_cache", ".git", "node_modules", ".mypy_cache", ".ruff_cache"}

Runner = Callable[[list[str]], bytes]


def docker_runner(cmd: list[str]) -> bytes:
    proc = subprocess.run(cmd, capture_output=True, timeout=300)
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:8])}... failed: {proc.stderr.decode(errors='replace')[-400:]}")
    return proc.stdout


# ------------------------------------------------------------------------------------------- reading snapshots


def _skipped(path: str) -> bool:
    parts = path.split("/")
    return any(p in SKIP_DIRS or (p.startswith(".") and p not in (".", "..")) for p in parts[:-1])


def files_from_tar(data: bytes) -> dict[str, str]:
    """The Python files in a tar stream, by path relative to the archive root."""
    out: dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            name = m.name[2:] if m.name.startswith("./") else m.name
            if not name.endswith(".py") or _skipped(name):
                continue
            f = tf.extractfile(m)
            if f is not None:
                out[name] = f.read().decode("utf-8", errors="replace")
    return out


def git_snapshot(volume: str, commit: str, runner: Runner = docker_runner, image: str = IMAGE) -> dict[str, str]:
    cmd = ["docker", "run", "--rm", "-v", f"{volume}:/ws:ro", "--entrypoint", "git", image,
           "-c", "safe.directory=*", "-C", "/ws", "archive", "--format=tar", commit]
    return files_from_tar(runner(cmd))


def dir_snapshot(volume: str, subdir: str, runner: Runner = docker_runner, image: str = IMAGE) -> dict[str, str]:
    excludes = [f"--exclude={d}" for d in sorted(SKIP_DIRS)]
    cmd = ["docker", "run", "--rm", "-v", f"{volume}:/ws:ro", "--entrypoint", "tar", image,
           "-C", f"/ws/{subdir}", "-c", *excludes, "."]
    return files_from_tar(runner(cmd))


# ------------------------------------------------------------------------------------------------- measures


def is_test_path(path: str) -> bool:
    p = path.lower()
    parts = p.split("/")
    name = parts[-1]
    return (any(seg in ("tests", "test") for seg in parts[:-1]) or name.startswith("test_")
            or name.endswith("_test.py") or name == "conftest.py")


def is_source_path(path: str) -> bool:
    return path.endswith(".py") and not _skipped(path) and not is_test_path(path)


def module_name(path: str) -> str:
    parts = path[:-3].split("/")
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) or "__init__"


def nonblank_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def _package_of(path: str) -> str:
    """The package a file's relative imports resolve against."""
    parts = path[:-3].split("/")
    return ".".join(parts[:-1])


def imports_of(path: str, text: str) -> list[tuple[str, list[str]]]:
    """Each import in a file as (base module, names imported from it), relative bases made absolute. `import a.b`
    gives ("a.b", [])."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [(a.name, []) for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                pkg = _package_of(path).split(".") if _package_of(path) else []
                up = node.level - 1
                if up > len(pkg):
                    continue
                base_parts = pkg[:len(pkg) - up] if up else pkg
                base = ".".join(base_parts + ([node.module] if node.module else []))
            else:
                base = node.module or ""
            out.append((base, [a.name for a in node.names]))
    return out


def resolve(base: str, names: list[str], modules: set[str], by_tail: dict[str, list[str]]) -> set[str]:
    """The project modules an import reaches."""
    def find(dotted: str) -> str | None:
        if not dotted:
            return None
        if dotted in modules:
            return dotted
        hits = by_tail.get(dotted, [])
        return hits[0] if len(hits) == 1 else None

    hit: set[str] = set()
    if names:
        base_mod = find(base)
        for n in names:
            sub = find(f"{base}.{n}" if base else n)
            if sub:
                hit.add(sub)
            elif base_mod:
                hit.add(base_mod)
        return hit
    parts = base.split(".")
    for k in range(len(parts), 0, -1):  # the deepest existing module of a dotted import
        m = find(".".join(parts[:k]))
        if m:
            hit.add(m)
            break
    return hit


def measure(files: dict[str, str]) -> dict:
    """Module count, lines per module and import coupling for one snapshot's Python files."""
    src = {p: t for p, t in files.items() if is_source_path(p)}
    tests = {p: t for p, t in files.items() if p.endswith(".py") and not _skipped(p) and is_test_path(p)}
    names = {p: module_name(p) for p in src}
    modules = set(names.values())
    by_tail: dict[str, list[str]] = {}
    for m in modules:  # dotted suffixes, for imports written as if run from inside a package
        parts = m.split(".")
        for k in range(1, len(parts)):
            by_tail.setdefault(".".join(parts[k:]), []).append(m)
    lines = {names[p]: nonblank_lines(t) for p, t in src.items()}
    edges: set[tuple[str, str]] = set()
    for p, t in src.items():
        me = names[p]
        for base, imported in imports_of(p, t):
            for dst in resolve(base, imported, modules, by_tail):
                if dst != me:
                    edges.add((me, dst))
    total = sum(lines.values())
    largest = max(lines, key=lambda m: (lines[m], m)) if lines else None
    fan_in: dict[str, int] = {}
    for _, d in edges:
        fan_in[d] = fan_in.get(d, 0) + 1
    return {
        "modules": len(modules),
        "source_lines": total,
        "median_lines": statistics.median(lines.values()) if lines else 0,
        "max_lines": lines[largest] if largest else 0,
        "largest_module": largest,
        "largest_share": round(lines[largest] / total, 3) if total else None,
        "edges": len(edges),
        "mean_fan_out": round(len(edges) / len(modules), 2) if modules else None,
        "max_fan_in": max(fan_in.values()) if fan_in else 0,
        "test_files": len(tests),
        "test_lines": sum(nonblank_lines(t) for t in tests.values()),
        "module_lines": dict(sorted(lines.items())),
        "edge_list": sorted(f"{a} -> {b}" for a, b in edges),
    }


# --------------------------------------------------------------------------------------------- the snapshots


def trajectory(runs: Path, tid: str) -> dict:
    return json.loads((runs / tid / "trajectory.json").read_text())


def growth_snapshots(runs: Path, tid: str, changes: list[int]) -> list[dict]:
    t = trajectory(runs, tid)
    out, prev = [], None
    for n in changes:
        c = t["changes"].get(str(n))
        if c is None:
            out.append({"change": n, "commit": None, "note": "no such change"})
            continue
        note = None
        if c.get("symptom"):
            note = f"symptom change: {c['symptom']}"
        elif c.get("commit") == prev:
            note = "no new commit"
        out.append({"change": n, "commit": c.get("commit"), "note": note})
        prev = c.get("commit")
    return out


def run_growth(runs: Path, tid: str, changes: list[int], runner: Runner) -> dict:
    t = trajectory(runs, tid)
    vol = t["volumes"]["workspace"]
    rows = []
    for snap in growth_snapshots(runs, tid, changes):
        if not snap["commit"]:
            rows.append({**snap, "error": "no commit"})
            continue
        try:
            rows.append({**snap, **measure(git_snapshot(vol, snap["commit"], runner))})
        except Exception as e:  # noqa: BLE001 - a snapshot that can't be read is reported, not fatal
            rows.append({**snap, "error": str(e)[:300]})
    return {"id": tid, "arm": t.get("arm"), "seed": t.get("seed"), "source": f"git history in {vol}", "rows": rows}


def run_s3b(runs: Path, arm: str, k: int, runner: Runner, change: int = 10) -> dict:
    tid = f"s3b-{arm}-{k}"
    ckpt = f"ce-g-s3b-{arm}-{k}-c{change:02d}-ckpt"
    row: dict = {"change": change, "commit": None, "note": None}
    try:
        files = dir_snapshot(ckpt, "app", runner)
        row.update(measure(files))
        source = f"{ckpt}:/app"
    except Exception as e:  # noqa: BLE001
        files, source = None, None
        row["error"] = f"checkpoint unreadable: {str(e)[:200]}"
    # Check against (or fall back to) the change's commit in the trajectory's workspace history.
    try:
        t = trajectory(runs, tid)
        commit = t["changes"][str(change)]["commit"]
        row["commit"] = commit
        from_git = git_snapshot(t["volumes"]["workspace"], commit, runner)
        if files is None:
            row.pop("error", None)
            row.update(measure(from_git))
            source = f"git history in {t['volumes']['workspace']}"
            row["note"] = "checkpoint unreadable; read from the workspace history"
        else:
            a = {p: x for p, x in files.items() if is_source_path(p) or is_test_path(p)}
            b = {p: x for p, x in from_git.items() if is_source_path(p) or is_test_path(p)}
            row["matches_commit"] = a == b
            if a != b:
                row["note"] = (f"checkpoint differs from commit {commit[:8]}: "
                               f"{sorted(set(a) ^ set(b))[:5] or [p for p in a if a[p] != b.get(p)][:5]}")
    except Exception as e:  # noqa: BLE001
        row.setdefault("note", f"no workspace check: {str(e)[:200]}")
    return {"id": tid, "arm": arm, "seed": "benchtime", "source": source, "rows": [row]}


# ------------------------------------------------------------------------------------------------- reporting

COLS = [("change", "Change"), ("modules", "Modules"), ("source_lines", "Source lines"), ("median_lines", "Median lines"),
        ("max_lines", "Max lines"), ("largest_module", "Largest module"), ("largest_share", "Largest share"),
        ("edges", "Import edges"), ("mean_fan_out", "Mean fan-out"), ("max_fan_in", "Max fan-in"),
        ("test_files", "Test files"), ("test_lines", "Test lines")]


def _cell(row: dict, key: str) -> str:
    v = row.get(key)
    if v is None:
        return "–"
    if key == "largest_share":
        return f"{100 * v:.0f}%"
    if key == "median_lines" and isinstance(v, float):
        return f"{v:.0f}" if v.is_integer() else f"{v:.1f}"
    if isinstance(v, int):
        return f"{v:,}"
    return str(v)


def table(run: dict) -> list[str]:
    lines = ["| " + " | ".join(label for _, label in COLS) + " | Note |", "|" + "---|" * (len(COLS) + 1)]
    for r in run["rows"]:
        if "error" in r:
            lines.append(f"| {r['change']} | " + " | ".join("–" for _ in COLS[1:]) + f" | {r['error']} |")
            continue
        note = r.get("note") or ""
        if r.get("matches_commit"):
            note = (note + "; " if note else "") + "checkpoint matches the change's commit"
        lines.append("| " + " | ".join(_cell(r, k) for k, _ in COLS) + f" | {note} |")
    return lines


def summary(results: list[dict]) -> list[str]:
    by = {r["id"]: r for r in results}
    ok = lambda run: [x for x in run["rows"] if "error" not in x]  # noqa: E731
    out = ["## Summary", ""]

    def at(tid: str, n: int) -> dict | None:
        return next((x for x in ok(by[tid]) if x["change"] == n), None) if tid in by else None

    def describe(tid: str, n: int) -> str:
        x = at(tid, n)
        if not x:
            return f"{tid} at change {n}: not read"
        return (f"{x['modules']} modules, {x['source_lines']:,} source lines (median {_cell(x, 'median_lines')}, "
                f"max {x['max_lines']:,} in {x['largest_module']}, {_cell(x, 'largest_share')} of all), "
                f"{x['edges']} import edges (mean fan-out {x['mean_fan_out']})")

    for n in (0, 10, 20):
        for tid in ("g-bare-1", "g-lid-full-1"):
            out.append(f"- **{tid}, change {n}:** {describe(tid, n)}.")
    for n in (10, 20, 30, 40):
        out.append(f"- **g-ref-correct, change {n}:** {describe('g-ref-correct', n)}.")
    s3b = [r for r in results if r["id"].startswith("s3b-")]
    if s3b:
        out.append("- **BenchTime stage 3b at change 10** (modules; source lines; largest share; edges; mean fan-out):")
        for arm in ("bare", "cheap-discipline", "lid-full"):
            rows = [x for r in s3b if r["arm"] == arm for x in ok(r)]
            if not rows:
                out.append(f"  - {arm}: not read")
                continue
            out.append(f"  - {arm}: " + "; ".join(
                f"{x['modules']} / {x['source_lines']:,} / {_cell(x, 'largest_share')} / {x['edges']} / {x['mean_fan_out']}"
                for x in rows))
    return out


def report(results: list[dict]) -> str:
    lines = ["# Module count and coupling by snapshot", "",
             "Python source only, from each snapshot's files. Modules are non-test source files (package `__init__.py` "
             "and `__main__.py` included); lines are non-blank lines; an import edge is a distinct (importer, imported) "
             "pair of two of the project's own source modules, from `import` and `from ... import` anywhere in a file. "
             "Mean fan-out is edges over modules. Test files are shown for context only.", ""]
    lines += summary(results)
    for r in results:
        lines += ["", f"## {r['id']} ({r['arm']}, {r['seed']})", "", f"Read from {r['source']}.", ""] + table(r)
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    ap.add_argument("--out", type=Path, default=None, help="output folder (default: <runs>/analysis)")
    ap.add_argument("--only", nargs="*", default=None, help="run ids to include (default: all)")
    args = ap.parse_args(argv)
    out = args.out or args.runs / "analysis"
    want = lambda tid: args.only is None or tid in args.only  # noqa: E731
    results = []
    for tid in ("g-bare-1", "g-lid-full-1"):
        if want(tid):
            results.append(run_growth(args.runs, tid, list(range(21)), docker_runner))
    if want("g-ref-correct"):
        results.append(run_growth(args.runs, "g-ref-correct", [10, 20, 30, 40], docker_runner))
    for arm in ("bare", "cheap-discipline", "lid-full"):
        for k in (1, 2, 3):
            if want(f"s3b-{arm}-{k}"):
                results.append(run_s3b(args.runs, arm, k, docker_runner))
    out.mkdir(parents=True, exist_ok=True)
    (out / "structure.json").write_text(json.dumps(results, indent=1))
    (out / "structure.md").write_text(report(results))
    for r in results:
        last = [x for x in r["rows"] if "error" not in x]
        errs = len(r["rows"]) - len(last)
        tail = last[-1] if last else {}
        print(f"{r['id']}: {len(last)} snapshots read, {errs} unreadable; last: modules {tail.get('modules')}, "
              f"edges {tail.get('edges')}, largest share {tail.get('largest_share')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
