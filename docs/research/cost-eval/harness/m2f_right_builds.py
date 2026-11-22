"""Each M2f change's right build as a patch (plan.md, M2f): the instrument's positive control. The right builds are
m2f-validation/builds.py's core and shell edits for each change (exact replacements checked for their counts); this
writes each as a unified diff against the snapshot, which run_fork.py --null --patch applies to the v2 full variant
(source files only, which the variant keeps as the snapshot has them), so the build is graded exactly as a fork is.

    python3.12 m2f_right_builds.py --builds ../seeds/clowder/hidden/m2f-validation/builds.py --out ../runs/clowder-m2f/right
    python3.12 m2f_right_builds.py --builds ... --list          # the changes that have a right build, one per line

Writes <out>/change-NN.diff and <out>/right-builds.json ({"NN": {"files", "sha256"}}). A change's right build is its
CORE and SHELL edits together (a control may have one of the two only); builds.py may also give RIGHT[n], which then
stands for the change's whole right build.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
BUILDS = HERE.parent / "seeds" / "clowder" / "hidden" / "m2f-validation" / "builds.py"


def load_builds(path: Path):
    spec = importlib.util.spec_from_file_location("m2f_validation_builds", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def right_edits(builds) -> dict[int, list[tuple[str, str, str, int]]]:
    """Each change's right-build edits, (path, old, new, count), in order: core, then shell."""
    core, shell, right = getattr(builds, "CORE", {}), getattr(builds, "SHELL", {}), getattr(builds, "RIGHT", {})
    return {n: list(right[n]) if n in right else list(core.get(n, [])) + list(shell.get(n, []))
            for n in sorted(set(core) | set(shell) | set(right))}


def patch_for(edits: list[tuple[str, str, str, int]], read: Callable[[str], str]) -> str:
    """The edits as one unified diff against the files `read` gives (a/ and b/ prefixes, for git apply)."""
    before: dict[str, str] = {}
    after: dict[str, str] = {}
    for path, old, new, count in edits:
        if path not in after:
            before[path] = after[path] = read(path)
        got = after[path].count(old)
        if got != count:
            raise ValueError(f"{path}: {old[:60]!r} found {got} times, not {count}")
        after[path] = after[path].replace(old, new)
    out = []
    for path in before:
        if not before[path].endswith("\n") or not after[path].endswith("\n"):
            raise ValueError(f"{path}: doesn't end in a newline")
        out += difflib.unified_diff(before[path].splitlines(keepends=True), after[path].splitlines(keepends=True),
                                    fromfile=f"a/{path}", tofile=f"b/{path}")
    return "".join(out)


def snapshot_reader(repo: Path, commit: str) -> Callable[[str], str]:
    def read(path: str) -> str:
        return subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{path}"], capture_output=True, text=True,
                              check=True).stdout
    return read


def main(argv=None, *, read: Callable[[str], str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--builds", type=Path, default=BUILDS)
    ap.add_argument("--repo", type=Path, default=Path("/Users/jess/src/clowder"))
    ap.add_argument("--commit", default="86db995")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--list", action="store_true", help="print the changes that have a right build, and stop")
    args = ap.parse_args(argv)
    edits = right_edits(load_builds(args.builds))
    if args.list:
        print("\n".join(str(n) for n in edits))
        return 0
    if args.out is None:
        ap.error("--out is required unless --list")
    read = read or snapshot_reader(args.repo, args.commit)
    args.out.mkdir(parents=True, exist_ok=True)
    index = {}
    for n, e in edits.items():
        patch = patch_for(e, read)
        (args.out / f"change-{n:02d}.diff").write_text(patch, encoding="utf-8")
        index[str(n)] = {"files": list(dict.fromkeys(p for p, *_ in e)), "sha256": hashlib.sha256(patch.encode()).hexdigest()}
        print(f"change {n}: {len(index[str(n)]['files'])} files")
    (args.out / "right-builds.json").write_text(json.dumps(index, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
