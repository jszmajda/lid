"""Each M2h change's right build as a patch (plan.md, M2h; m2h-harness-needs.md, "Phases"): the instrument's positive
control. m2h-validation/builds.mjs holds every build as exact edits on the pinned tree, by set, and declares each change's
right build (`node builds.mjs --declare`: changes 4 and 8 take their web-app halves, w4 and w8, with their API sets). Each is applied to a clone of the shared
start's tracked files (never the start itself), and written as a patch from the start's commit, which
run_fork.py --null --result-patch commits as a null fork's result so the build is graded exactly as a fork is.

    python3.12 m2h_right_builds.py --out ../runs/opengym-m2h/right                # from the start volume, in Docker
    python3.12 m2h_right_builds.py --list                                       # the changes with a right build

Writes <out>/change-NN.diff and <out>/right-builds.json ({"N": {"sets", "files", "sha256"}}). A set that doesn't apply
(builds.mjs exits non-zero) stops the run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
MAIN = Path("/Users/jess/src/lid-cost-eval/docs/research/cost-eval")  # git-ignored seed material lives here
BUILDS = MAIN / "seeds" / "opengym" / "hidden" / "m2h-validation" / "builds.mjs"
START_VOLUME = "ogmap-bare-ws"
IMAGE = "lid-cost-eval-executor-node:2.1.323"
def declared_right(builds: Path) -> dict[int, list[str]]:
    """Each change's right build as builds.mjs declares it (`node builds.mjs --declare`: {"<n>": {"right": [sets], ...}}),
    run with the local node, which reads the file and edits nothing."""
    p = subprocess.run(["node", str(builds), "--declare"], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"builds.mjs --declare failed: {(p.stderr or p.stdout)[-500:]}")
    return {int(n): list(e["right"]) for n, e in sorted(json.loads(p.stdout).items(), key=lambda kv: int(kv[0]))}


def script(changes: dict[int, list[str]], *, src: str, builds: str, out: str) -> str:
    """A shell script that clones the start's tracked files, then for each change applies its sets with builds.mjs
    and writes the patch from the start, resetting between changes."""
    lines = ["set -e", f"git clone -q {src} /tmp/m2h-right", "cd /tmp/m2h-right"]
    for n, sets in changes.items():
        lines += [f"node {builds} {' '.join(sets)} > /tmp/m2h-right-{n}.log 2>&1 || {{ cat /tmp/m2h-right-{n}.log; "
                  f"echo 'change {n}: a set did not apply' >&2; exit 3; }}",
                  "git add -A",
                  f"git diff --cached --binary HEAD > {out}/change-{n:02d}.diff",
                  f"git diff --cached --name-only HEAD > {out}/change-{n:02d}.files",
                  "git reset -q --hard HEAD", "git clean -fdq"]
    return "\n".join(lines)


def local_runner(repo: Path, builds: Path, out: Path, changes: dict[int, list[str]]) -> subprocess.CompletedProcess:
    """For tests: the same script on a local repository (needs node and git)."""
    s = script(changes, src=str(repo), builds=str(builds), out=str(out)).replace("/tmp/m2h-right", str(out / ".work"))
    return subprocess.run(["sh", "-c", s], capture_output=True, text=True)


def docker_runner(volume: str, image: str = IMAGE) -> Callable:
    """The script in the Node image, with the start volume mounted read-only."""
    def run(_repo, builds: Path, out: Path, changes: dict[int, list[str]]) -> subprocess.CompletedProcess:
        s = script(changes, src="/src", builds="/in/builds.mjs", out="/out")
        return subprocess.run(["docker", "run", "--rm", "-v", f"{volume}:/src:ro", "-v", f"{builds.resolve()}:/in/builds.mjs:ro",
                               "-v", f"{out.resolve()}:/out", image, "sh", "-c", s], capture_output=True, text=True)
    return run


def write_patches(repo, builds: Path, out: Path, *, runner: Callable) -> dict:
    changes = declared_right(builds)
    out.mkdir(parents=True, exist_ok=True)
    p = runner(repo, builds, out, changes)
    if p.returncode != 0:
        raise RuntimeError(f"right builds failed ({p.returncode}): {(p.stderr or p.stdout or '')[-800:]}")
    index = {}
    for n, sets in changes.items():
        patch = (out / f"change-{n:02d}.diff").read_bytes()
        files_path = out / f"change-{n:02d}.files"
        index[str(n)] = {"sets": sets, "files": files_path.read_text().split(), "sha256": hashlib.sha256(patch).hexdigest()}
        files_path.unlink()
    (out / "right-builds.json").write_text(json.dumps(index, indent=1))
    work = out / ".work"
    if work.exists():
        subprocess.run(["rm", "-rf", str(work)])
    return index


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--builds", type=Path, default=BUILDS)
    ap.add_argument("--start-volume", default=START_VOLUME)
    ap.add_argument("--image", default=IMAGE)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--list", action="store_true", help="print the changes that have a right build, and stop")
    args = ap.parse_args(argv)
    if args.list:
        print("\n".join(str(n) for n in declared_right(args.builds)))
        return 0
    if args.out is None:
        ap.error("--out is required unless --list")
    index = write_patches(None, args.builds, args.out, runner=docker_runner(args.start_volume, args.image))
    for n, e in index.items():
        print(f"change {n}: {' '.join(e['sets'])}; {len(e['files'])} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
