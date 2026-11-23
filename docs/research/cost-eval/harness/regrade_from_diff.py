"""Regrade graded Clowder forks whose volumes are gone, from the diff their grading saved (grading/change-NN/arm.diff,
the graders' view of the change: code and tests, with spec IDs and @spec comments stripped). Each fork is rebuilt as a
null fork whose result is that diff, then graded again (grade_rust.py) with the current probes and graded targets:

- a bare fork on its own stripped variant, which the diff applies to as it is;
- a LID fork on a grader-stripped copy of its full variant (the graders' own stripping, rust_grading.prepare_for_graders,
  committed as a variant of its own, `full-gs`, in <set>-gs/), since its diff's context lost the spec IDs the full
  variant still has. Grading strips again, and the stripping is idempotent, so the graded tree is the one the first
  grading saw; adopt checks that by comparing the regrade's arm.diff with the first's, and refuses a mismatch.

    python3.12 regrade_from_diff.py plan --change 15 --forks 'm2f-*-c15-r*' 'm2f-dose-*-c15-r*'
    python3.12 regrade_from_diff.py gs-base --variants ../runs/clowder-variants/v2               # once per variant set
    python3.12 regrade_from_diff.py rebuild --fork m2f-full-lid-full-c15-r1 --change 15            # a null fork: regrade-<id>
    python3.12 grade_rust.py --id regrade-m2f-full-lid-full-c15-r1 ...                            # graded like any fork
    python3.12 regrade_from_diff.py adopt --fork m2f-full-lid-full-c15-r1 --change 15

adopt moves the fork's grading to grading-v1/ (once; never overwritten), puts the regrade's grading in its place, and
records in its summary that it was rebuilt from the diff on a stripped base.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

PY = sys.executable
GS = "full-gs"
REGRADE = "regrade-"
SEED_FLAGS = ["--oracle", "{files}/oracle.md", "--change-script", "{files}/change-script.md",
              "--owner-items", "{files}/owner-items.json"]


def _json(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def base_for(meta: dict) -> tuple[Path, str]:
    """The variant set and variant a fork is rebuilt on."""
    fo = meta.get("fork_of") or {}
    variants = Path(fo["variants"])
    if fo.get("variant") == "stripped":
        return variants, "stripped"
    return variants.parent / f"{variants.name}-gs", GS


def write_gs_manifest(variants: Path, *, commit: str, volume: str, source_variant: str = "full") -> Path:
    """<set>-gs/: a manifest naming the grader-stripped variant, keeping the first set's held-out files, graded targets and
    spec-ID pattern (for grading), which it links rather than copies."""
    src = json.loads((variants / "manifest.json").read_text())
    out = variants.parent / f"{variants.name}-gs"
    out.mkdir(parents=True, exist_ok=True)
    stripped = (src.get("variants") or {}).get("stripped") or {}
    m = {**{k: v for k, v in src.items() if k != "variants"},
         "variants": {GS: {"commit": commit, "volume": volume, "vcs": "git",
                           "built_from": {"variants": str(variants), "variant": source_variant,
                                          "commit": src["variants"][source_variant]["commit"],
                                          "stripped_as": "the graders' code-only checkout"}},
                      "stripped": {"report": stripped.get("report") or {}}}}
    (out / "manifest.json").write_text(json.dumps(m, indent=1))
    for name in ("held-out", "graded"):
        link = out / name
        if not link.exists() and (variants / name).exists():
            link.symlink_to((variants / name).resolve())
    return out


def gs_base(variants: Path, *, image: str = "lid-cost-eval-executor-rust:2.1.323", source_variant: str = "full") -> Path:
    """Build <set>-gs: the full variant checked out, stripped as the graders strip it, committed, in a volume of its own."""
    from costeval import rust_grading as rgr
    src = json.loads((variants / "manifest.json").read_text())
    v = src["variants"][source_variant]
    pattern = ((src["variants"].get("stripped") or {}).get("report") or {}).get("spec_id_pattern")
    ck = rgr.RustCheckpoint(name=f"gs-{src.get('seed')}-{source_variant}", commit=v["commit"],
                            image=image)
    ck.export(v["volume"])
    rgr.prepare_for_graders(ck, v["commit"], v["commit"], spec_pattern=pattern)
    commit = ck.sh("cd /work/app && git init -q -b main && git add -A && GIT_COMMITTER_DATE='2026-01-01T00:00:00+00:00' "
                   "git -c user.name=Harness -c user.email=harness@example.invalid commit -q "
                   "--date='2026-01-01T00:00:00+00:00' -m Start && git rev-parse HEAD").strip()
    volume = f"ce-cv-{src.get('seed')}-gs-{source_variant}"
    subprocess.run(["docker", "volume", "rm", "-f", volume], capture_output=True)
    subprocess.run(["docker", "run", "--rm", "-v", f"{ck.volume}:/from:ro", "-v", f"{volume}:/to", image, "sh", "-c",
                    "cp -a /from/app/. /to/"], check=True, capture_output=True)
    subprocess.run(["docker", "volume", "rm", "-f", ck.volume], capture_output=True)
    return write_gs_manifest(variants, commit=commit, volume=volume, source_variant=source_variant)


def _patch(runs: Path, fid: str, change: int) -> Path:
    first = runs / fid / "grading-v1" / f"change-{change:02d}" / "arm.diff"
    return first if first.exists() else runs / fid / "grading" / f"change-{change:02d}" / "arm.diff"


def plan(runs: Path, change: int, patterns: list[str]) -> list[dict]:
    jobs = []
    for d in sorted({d for p in patterns for d in runs.glob(p)}):
        meta = _json(d / "trajectory.json") or {}
        if "." in d.name or d.name.startswith(REGRADE) or meta.get("change") != change or meta.get("arm") == "null":
            continue
        if not any(fnmatch.fnmatchcase(d.name, p) for p in patterns) or not _patch(runs, d.name, change).exists():
            continue
        variants, variant = base_for(meta)
        jobs.append({"fork": d.name, "variants": str(variants), "variant": variant, "patch": str(_patch(runs, d.name, change)),
                     "repeat": meta.get("repeat") or 1, "replicate": meta.get("replicate") or "m2f-r1"})
    return jobs


def rebuild(runs: Path, fid: str, change: int, files: Path) -> int:
    meta = _json(runs / fid / "trajectory.json") or {}
    variants, variant = base_for(meta)
    flags = [f.format(files=files) for f in SEED_FLAGS]
    return subprocess.run([PY, "run_fork.py", "--variants", str(variants), "--variant", variant, "--null", "--result-patch",
                           str(_patch(runs, fid, change)), "--change", str(change), "--repeat", str(meta.get("repeat") or 1),
                           "--replicate", meta.get("replicate") or "m2f-r1", "--window", meta.get("window") or "1m",
                           *flags, "--id", f"{REGRADE}{fid}", "--runs", str(runs)], cwd=HERE).returncode


def adopt(runs: Path, fid: str, *, change: int, base: tuple) -> dict:
    """The regrade's grading in the fork's place, the first kept as grading-v1/, refused unless the regrade graded the
    tree the first grading saw (the same arm.diff)."""
    fork, regrade = runs / fid, runs / f"{REGRADE}{fid}"
    nn = f"change-{change:02d}"
    first_dir = fork / "grading-v1" if (fork / "grading-v1").exists() else fork / "grading"
    first_diff, new_diff = first_dir / nn / "arm.diff", regrade / "grading" / nn / "arm.diff"
    if first_diff.read_bytes() != new_diff.read_bytes():
        raise ValueError(f"{fid}: the regrade's diff isn't the one first graded; the rebuilt tree differs")
    if not (fork / "grading-v1").exists():
        (fork / "grading").rename(fork / "grading-v1")
    if (fork / "grading").exists():
        shutil.rmtree(fork / "grading")
    shutil.copytree(regrade / "grading", fork / "grading")
    spath = fork / "grading" / nn / "summary.json"
    s = json.loads(spath.read_text())
    s["rebuilt"] = {"from": f"grading-v1/{nn}/arm.diff", "sha256": hashlib.sha256(first_diff.read_bytes()).hexdigest(),
                    "on": ("its own stripped variant" if base[1] == "stripped" else
                           "a grader-stripped copy of its full variant (stripped base)"),
                    "base": {"variants": str(base[0]), "variant": base[1]}, "regrade_fork": regrade.name,
                    "tree_matches_first_grading": True}
    spath.write_text(json.dumps(s, indent=1))
    return s


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=("plan", "gs-base", "rebuild", "adopt"))
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    ap.add_argument("--change", type=int)
    ap.add_argument("--forks", nargs="+", default=[])
    ap.add_argument("--fork")
    ap.add_argument("--variants", type=Path)
    ap.add_argument("--seed-files", type=Path, default=HERE.parent / "seeds" / "clowder" / "hidden" / "m2f")
    args = ap.parse_args(argv)
    if args.what == "plan":
        for j in plan(args.runs, args.change, args.forks):
            print(j["fork"], j["variant"])
        return 0
    if args.what == "gs-base":
        print(gs_base(args.variants))
        return 0
    if args.what == "rebuild":
        return rebuild(args.runs, args.fork, args.change, args.seed_files)
    meta = _json(args.runs / args.fork / "trajectory.json") or {}
    s = adopt(args.runs, args.fork, change=args.change, base=base_for(meta))
    print(f"{args.fork}: adopted the regrade ({s['rebuilt']['on']}); items {s.get('items')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
