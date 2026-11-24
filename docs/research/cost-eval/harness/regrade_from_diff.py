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

An M2h fork (openGym, Node; a named start's) is rebuilt as a null fork of its own start (rg-<id>, from a copy of the
starts file whose fork prefix is rg-m2h-, so no report's m2h-* glob takes it), from its diff made applicable
(applicable: the starts carry no annotations in code, but the LID arm's own @spec lines left its diff's content while
its hunk headers still count them, and an edit to an annotation alone leaves a hunk with no change, which git calls
corrupt). It is graded with grade_node.py. adopt compares the regrade's diff with the first byte for byte ("exact");
failing that, for M2h only, it applies each to the fork's start (in the start's volume, read-only) and accepts the
same git tree ("tree": every path and byte of the code and tests the same), which is the only check left once the LID
arm's annotation lines are gone from the rebuilt tree and the hunks fall otherwise. Either is recorded. adopt-keeping
takes only the keeping from a regrade graded with --no-dependency --no-probes (the web app's suite killed for lack of
memory, say), the first kept as keeping-v1.json and keeping-v1/. keep-v1 sets a fork's grading aside as grading-v1/
before it is graded again in place (its own volume still there).

    python3.12 regrade_from_diff.py rebuild --fork m2h-bare-c11-r2 --change 11 --seed-dir ../seeds/opengym --seed-files ../seeds/opengym/hidden/m2h
    python3.12 grade_node.py --id rg-m2h-bare-c11-r2 --no-dependency --no-probes ...
    python3.12 regrade_from_diff.py adopt-keeping --fork m2h-bare-c11-r2 --change 11 --reason "..."
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

PY = sys.executable
GS = "full-gs"
REGRADE = "regrade-"
NODE_REGRADE = "rg-"
START = "start"
SEED_FLAGS = ["--oracle", "{files}/oracle.md", "--change-script", "{files}/change-script.md",
              "--owner-items", "{files}/owner-items.json"]


def _json(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def is_node(meta: dict) -> bool:
    """A named start's fork (M2h, openGym), not a Clowder variant's."""
    return bool((meta.get("fork_of") or {}).get("start"))


def regrade_id(fid: str, meta: dict) -> str:
    return f"{NODE_REGRADE}{fid}" if is_node(meta) else f"{REGRADE}{fid}"


def base_for(meta: dict) -> tuple:
    """The variant set and variant a fork is rebuilt on (M2h: its start's name, and "start")."""
    fo = meta.get("fork_of") or {}
    if is_node(meta):
        return fo["start"], START
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
    # mounted at the image's own /work, a new volume takes that directory's owner (the image's user), as
    # clowder_variants.load_volume's volumes do
    subprocess.run(["docker", "run", "--rm", "-v", f"{ck.volume}:/from:ro", "-v", f"{volume}:/work", image, "sh", "-c",
                    "find /work -mindepth 1 -delete && cp -a /from/app/. /work/"], check=True, capture_output=True)
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


HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")


def _span(start: str, count: int) -> str:
    return start if count == 1 else f"{start},{count}"


def recount(diff: str) -> str:
    """The diff with each hunk header's line counts taken from its lines (grade_node's diff dropped the arm's
    annotation lines from the content and left the headers counting them); every other line as it was."""
    trailing = diff.endswith("\n")
    out: list[str] = []
    header, old, new = None, 0, 0

    def close():
        if header is not None:
            m = HUNK.match(out[header])
            out[header] = f"@@ -{_span(m[1], old)} +{_span(m[3], new)} @@{m[5]}"
    for line in (diff[:-1] if trailing else diff).split("\n"):
        if HUNK.match(line):
            close()
            header, old, new = len(out), 0, 0
        elif line.startswith("diff "):
            close()
            header = None
        elif header is not None:
            if line.startswith("+"):
                new += 1
            elif line.startswith("-"):
                old += 1
            elif not line.startswith("\\"):
                old, new = old + 1, new + 1
        out.append(line)
    close()
    return "\n".join(out) + ("\n" if trailing else "")


def applicable(diff: str) -> str:
    """The grader's diff as git applies it: each hunk left with no change (an edit to an annotation alone, taken out)
    goes, and a file left with none goes too, but a new file stays as a new empty one and a rename or mode change as
    one; then each hunk's counts are taken from its lines (recount)."""
    lines = diff.split("\n")
    trailing = diff.endswith("\n")
    if trailing:
        lines = lines[:-1]
    out: list[str] = []
    i = 0
    while i < len(lines) and not lines[i].startswith("diff --git "):
        out.append(lines[i])
        i += 1
    while i < len(lines):
        j = i + 1
        while j < len(lines) and not lines[j].startswith("diff --git "):
            j += 1
        section = lines[i:j]
        k = next((x for x, line in enumerate(section) if HUNK.match(line)), len(section))
        header, hunks, cur = section[:k], [], None
        for line in section[k:]:
            if HUNK.match(line):
                cur = [line]
                hunks.append(cur)
            else:
                cur.append(line)
        kept = [h for h in hunks if any(x[:1] in ("+", "-") for x in h[1:])]
        if hunks and not kept:
            if any(x.startswith("new file mode") for x in header):
                out += [header[0], next(x for x in header if x.startswith("new file mode")), "index 0000000..e69de29"]
            elif any(x.startswith(("rename from", "rename to", "old mode", "new mode")) for x in header):
                out += [x for x in header if not x.startswith(("index ", "--- ", "+++ "))]
        else:
            out += header + [x for h in kept for x in h]
        i = j
    return recount("\n".join(out) + ("\n" if trailing and out else ""))


def tree_script(base: str, repo: str = "/src") -> str:
    """A shell script that applies the diff on its stdin to the commit base of the repository at repo (read-only: a
    shared bare clone takes the writes) in an index of its own, and prints the tree that gives."""
    return ("set -e; t=$(mktemp -d); "
            f"git -c safe.directory='*' clone -q --bare --shared '{repo}' \"$t/r\"; cat > \"$t/d\"; cd \"$t/r\"; "
            f"GIT_INDEX_FILE=\"$t/i\" git read-tree {base}; "
            "GIT_INDEX_FILE=\"$t/i\" git apply --cached --recount \"$t/d\"; "
            "GIT_INDEX_FILE=\"$t/i\" git write-tree")


def node_trees(runs: Path, meta: dict):
    """For an M2h fork: the tree a diff gives on its start (the start's volume, mounted read-only), or None when it
    doesn't apply."""
    start = meta.get("start_commit")
    if meta.get("repair"):  # graded from its fork's start
        start = (_json(runs / meta["repair"]["of"] / "trajectory.json") or {}).get("start_commit")
    volume, image = meta["fork_of"]["volume"], meta.get("image") or "lid-cost-eval-executor-node:2.1.323"

    def tree(diff: str):
        p = subprocess.run(["docker", "run", "--rm", "-i", "--network", "none", "-v", f"{volume}:/src:ro", image, "sh", "-c",
                            tree_script(start)], input=applicable(diff), capture_output=True, text=True)
        return p.stdout.strip() if p.returncode == 0 and p.stdout.strip() else None
    return tree


def match_kind(first: str, new: str, trees) -> str | None:
    """"exact" when the two diffs are the same bytes; "tree" when, applied each to the start, they give the same tree
    (git's tree hash: every path and byte the same), which the LID arm's annotation lines, gone from a rebuilt tree,
    make the only way to check; else None. trees None (a Clowder fork): the same bytes or nothing."""
    if first == new:
        return "exact"
    if trees is None:
        return None
    a = trees(first)
    return "tree" if a is not None and a == trees(new) else None


def regrade_starts(runs: Path, meta: dict) -> Path:
    """A copy of the fork's starts file whose fork prefix is rg- before its own (rg-m2h-), for the rebuilt forks."""
    src = Path(meta["fork_of"]["starts"])
    src = src if src.is_absolute() else (HERE / src).resolve()
    starts = json.loads(src.read_text())
    out = runs / "opengym-m2h" / "regrade" / "starts.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({**starts, "fork_prefix": NODE_REGRADE + (starts.get("fork_prefix") or "")}, indent=1))
    return out


def node_rebuild_argv(runs: Path, fid: str, change: int, *, seed_dir: Path, files: Path) -> list[str]:
    """run_fork.py's arguments for an M2h fork rebuilt as a null fork of its own start, its diff recounted."""
    meta = _json(runs / fid / "trajectory.json") or {}
    starts = regrade_starts(runs, meta)
    done = (meta.get("changes") or {}).get(str(change)) or {}
    result = []
    if not (done.get("null") and not done.get("result_patch")):  # a null control's result is its start alone
        patch = runs / "opengym-m2h" / "regrade" / "patches" / f"{fid}-c{change:02d}.diff"
        patch.parent.mkdir(parents=True, exist_ok=True)
        patch.write_text(applicable(_patch(runs, fid, change).read_text(encoding="utf-8")), encoding="utf-8")
        result = ["--result-patch", str(patch)]
    return ["--starts", str(starts), "--start", meta["fork_of"]["start"], "--null", *result,
            "--change", str(change), "--repeat", str(meta.get("repeat") or 1), "--replicate", meta.get("replicate") or "m2h-r1",
            "--window", meta.get("window") or "1m", "--seed-dir", str(seed_dir),
            *[f.format(files=files) for f in SEED_FLAGS], "--brief", str(seed_dir / "brief.md"),
            "--id", regrade_id(fid, meta), "--runs", str(runs)]


def rebuild(runs: Path, fid: str, change: int, files: Path, seed_dir: Path | None = None) -> int:
    meta = _json(runs / fid / "trajectory.json") or {}
    if is_node(meta):
        if seed_dir is None:
            raise ValueError("an M2h fork's rebuild needs --seed-dir (seeds/opengym)")
        return subprocess.run([PY, "run_fork.py", *node_rebuild_argv(runs, fid, change, seed_dir=seed_dir, files=files)],
                              cwd=HERE).returncode
    variants, variant = base_for(meta)
    flags = [f.format(files=files) for f in SEED_FLAGS]
    return subprocess.run([PY, "run_fork.py", "--variants", str(variants), "--variant", variant, "--null", "--result-patch",
                           str(_patch(runs, fid, change)), "--change", str(change), "--repeat", str(meta.get("repeat") or 1),
                           "--replicate", meta.get("replicate") or "m2f-r1", "--window", meta.get("window") or "1m",
                           *flags, "--id", f"{REGRADE}{fid}", "--runs", str(runs)], cwd=HERE).returncode


def _first_diff(fork: Path, nn: str) -> Path:
    first_dir = fork / "grading-v1" if (fork / "grading-v1").exists() else fork / "grading"
    return first_dir / nn / "arm.diff"


def _matched(runs: Path, fid: str, meta: dict, first_diff: Path, new_diff: Path, trees=None) -> str:
    """How the regrade's diff matches the first: exact, or for M2h the same tree on the start; refused otherwise."""
    a, b = first_diff.read_bytes(), new_diff.read_bytes()
    if trees is None and is_node(meta) and a != b:
        trees = node_trees(runs, meta)
    match = match_kind(a.decode("utf-8"), b.decode("utf-8"), trees if is_node(meta) else None)
    if match is None:
        raise ValueError(f"{fid}: the regrade's diff isn't the one first graded; the rebuilt tree differs")
    return match


def _on(base: tuple) -> str:
    if base[1] == START:
        return f"its own start ({base[0]}), from the diff its grading saved"
    return "its own stripped variant" if base[1] == "stripped" else "a grader-stripped copy of its full variant (stripped base)"


def adopt(runs: Path, fid: str, *, change: int, base: tuple, trees=None) -> dict:
    """The regrade's grading in the fork's place, the first kept as grading-v1/, refused unless the regrade graded the
    tree the first grading saw (the same arm.diff; for M2h, or the same tree on its start)."""
    meta = _json(runs / fid / "trajectory.json") or {}
    fork, regrade = runs / fid, runs / regrade_id(fid, meta)
    nn = f"change-{change:02d}"
    first_diff, new_diff = _first_diff(fork, nn), regrade / "grading" / nn / "arm.diff"
    match = _matched(runs, fid, meta, first_diff, new_diff, trees)
    if not (fork / "grading-v1").exists():
        (fork / "grading").rename(fork / "grading-v1")
    if (fork / "grading").exists():
        shutil.rmtree(fork / "grading")
    shutil.copytree(regrade / "grading", fork / "grading")
    spath = fork / "grading" / nn / "summary.json"
    s = json.loads(spath.read_text())
    s["rebuilt"] = {"from": f"grading-v1/{nn}/arm.diff", "sha256": hashlib.sha256(first_diff.read_bytes()).hexdigest(),
                    "on": _on(base), "base": {"variants": str(base[0]), "variant": base[1]}, "regrade_fork": regrade.name,
                    "diff_match": match, "tree_matches_first_grading": True}
    spath.write_text(json.dumps(s, indent=1))
    return s


def adopt_keeping(runs: Path, fid: str, *, change: int, reason: str | None = None, trees=None) -> dict:
    """The keeping a regrade measured on the rebuilt tree (graded with --no-dependency --no-probes) in place of the
    fork's, the first kept as keeping-v1.json and keeping-v1/; the rest of the fork's grading stays as it was."""
    meta = _json(runs / fid / "trajectory.json") or {}
    fork, regrade = runs / fid, runs / regrade_id(fid, meta)
    nn = f"change-{change:02d}"
    g, new = fork / "grading" / nn, regrade / "grading" / nn
    first_diff = _first_diff(fork, nn)
    match = _matched(runs, fid, meta, first_diff, new / "arm.diff", trees)
    s = json.loads((g / "summary.json").read_text())
    previous = (s.get("keeping_rebuilt") or {}).get("previous") or s.get("keeping")
    if not (g / "keeping-v1.json").exists():
        (g / "keeping.json").rename(g / "keeping-v1.json")
        if (g / "keeping").exists():
            (g / "keeping").rename(g / "keeping-v1")
    for old in (g / "keeping.json", g / "keeping"):
        if old.is_dir():
            shutil.rmtree(old)
        elif old.exists():
            old.unlink()
    shutil.copy2(new / "keeping.json", g / "keeping.json")
    if (new / "keeping").exists():
        shutil.copytree(new / "keeping", g / "keeping")
    s["keeping"] = json.loads((new / "summary.json").read_text())["keeping"]
    s["keeping_rebuilt"] = {"reason": reason, "from": f"{first_diff.parent.parent.name}/{nn}/arm.diff",
                            "sha256": hashlib.sha256(first_diff.read_bytes()).hexdigest(), "on": _on(base_for(meta)),
                            "regrade_fork": regrade.name, "diff_match": match, "tree_matches_first_grading": True,
                            "previous": previous}
    (g / "summary.json").write_text(json.dumps(s, indent=1))
    return s


def keep_v1(runs: Path, fid: str) -> bool:
    """The fork's grading set aside as grading-v1/ before it is graded again in place; False when one is already."""
    fork = runs / fid
    if (fork / "grading-v1").exists() or not (fork / "grading").exists():
        return False
    (fork / "grading").rename(fork / "grading-v1")
    return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=("plan", "gs-base", "rebuild", "adopt", "adopt-keeping", "keep-v1"))
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    ap.add_argument("--change", type=int)
    ap.add_argument("--forks", nargs="+", default=[])
    ap.add_argument("--fork")
    ap.add_argument("--variants", type=Path)
    ap.add_argument("--seed-files", type=Path, default=HERE.parent / "seeds" / "clowder" / "hidden" / "m2f",
                    help="M2h: seeds/opengym/hidden/m2h")
    ap.add_argument("--seed-dir", type=Path, help="M2h's rebuild: seeds/opengym")
    ap.add_argument("--reason", help="adopt-keeping: why the keeping was measured again")
    args = ap.parse_args(argv)
    if args.what == "plan":
        for j in plan(args.runs, args.change, args.forks):
            print(j["fork"], j["variant"])
        return 0
    if args.what == "gs-base":
        print(gs_base(args.variants))
        return 0
    if args.what == "rebuild":
        return rebuild(args.runs, args.fork, args.change, args.seed_files, args.seed_dir)
    if args.what == "keep-v1":
        print(f"{args.fork}: {'grading set aside as grading-v1' if keep_v1(args.runs, args.fork) else 'grading-v1 already kept'}")
        return 0
    meta = _json(args.runs / args.fork / "trajectory.json") or {}
    if args.what == "adopt-keeping":
        s = adopt_keeping(args.runs, args.fork, change=args.change, reason=args.reason)
        k = s["keeping"] or {}
        print(f"{args.fork}: keeping measured again ({s['keeping_rebuilt']['diff_match']} diff): {k.get('passed')}/"
              f"{k.get('counted')} passed, {k.get('failed')} failed")
        return 0
    s = adopt(args.runs, args.fork, change=args.change, base=base_for(meta))
    print(f"{args.fork}: adopted the regrade ({s['rebuilt']['on']}, {s['rebuilt']['diff_match']} diff); items {s.get('items')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
