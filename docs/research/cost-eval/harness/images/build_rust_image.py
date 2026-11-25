"""Build the executor image for a Rust seed: the pinned executor image plus Rust, with the seed's locked crates
fetched into the image's cargo home.

    python3.12 images/build_rust_image.py --repo /Users/jess/src/clowder --commit 86db995
    python3.12 images/build_rust_image.py --check            # versions, and a build of the fetch set with no network

The build context holds only the seed's workspace manifests and Cargo.lock, with empty stand-ins for the targets
cargo would discover, so `cargo fetch --locked` can resolve every crate without any of the seed's code.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCKERFILE = HERE / "executor-rust.Dockerfile"
TAG = "lid-cost-eval-executor-rust:2.1.323"
BASE = "lid-cost-eval-executor:2.1.323"
RUST_VERSION = "1.89.0"


def _git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True).stdout


def _members(root_manifest: str) -> list[str]:
    m = re.search(r"members\s*=\s*\[(.*?)\]", root_manifest, re.S)
    return re.findall(r'"([^"]+)"', m.group(1)) if m else []


def _declared_targets(manifest: str) -> list[str]:
    """Target paths a crate manifest names ([lib], [[bin]], [[test]], [[example]], [[bench]] sections)."""
    return re.findall(r'(?m)^\s*path\s*=\s*"([^"]+)"', manifest)


def fetch_files(repo: Path | str, commit: str) -> dict[str, bytes]:
    """The fetch context: the workspace's Cargo.toml and Cargo.lock, each member's Cargo.toml, and an empty stand-in
    for each library or binary target the member has (by convention or by its manifest). Nothing else."""
    repo = Path(repo)
    tracked = set(_git(repo, "ls-tree", "-r", "--name-only", commit).decode().splitlines())
    root = _git(repo, "show", f"{commit}:Cargo.toml")
    files = {"Cargo.toml": root, "Cargo.lock": _git(repo, "show", f"{commit}:Cargo.lock")}
    for member in _members(root.decode()):
        manifest = _git(repo, "show", f"{commit}:{member}/Cargo.toml")
        files[f"{member}/Cargo.toml"] = manifest
        bins = {"src/main.rs", *_bin_paths(manifest.decode())}
        targets = [t for t in ("src/lib.rs", "src/main.rs") if f"{member}/{t}" in tracked]
        targets += [t for t in _declared_targets(manifest.decode()) if f"{member}/{t}" in tracked]
        for t in dict.fromkeys(targets):
            if t.startswith(("tests/", "benches/", "examples/")):
                continue  # cargo fetch needs only the targets that make a member a package
            files[f"{member}/{t}"] = b"fn main() {}\n" if t in bins else b""
    return files


def _bin_paths(manifest: str) -> list[str]:
    out = []
    for block in re.split(r"(?m)^\[", manifest):
        if block.startswith("[bin]]"):
            out += re.findall(r'(?m)^\s*path\s*=\s*"([^"]+)"', block)
    return out


def build(repo: Path, commit: str, tag: str = TAG, base: str = BASE, runner=subprocess.run) -> None:
    ctx = Path(tempfile.mkdtemp(prefix="rust-image-"))
    try:
        for path, data in fetch_files(repo, commit).items():
            f = ctx / "fetch" / path
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(data)
        shutil.copy(DOCKERFILE, ctx / "Dockerfile")
        runner(["docker", "build", "-t", tag, "--build-arg", f"BASE={base}", "--build-arg", f"RUST_VERSION={RUST_VERSION}",
                str(ctx)], check=True)
    finally:
        shutil.rmtree(ctx, ignore_errors=True)


def check(tag: str = TAG, runner=subprocess.run) -> str:
    """Versions inside the image, run with no network."""
    p = runner(["docker", "run", "--rm", "--network", "none", tag, "sh", "-c",
                "rustc --version && cargo --version && ps --version | head -1 && cc --version | head -1 && "
                "du -sh $CARGO_HOME/registry 2>/dev/null"], capture_output=True, text=True, check=True)
    return p.stdout


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", type=Path)
    ap.add_argument("--commit", default="HEAD")
    ap.add_argument("--tag", default=TAG)
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--check", action="store_true", help="only report what the built image holds")
    args = ap.parse_args(argv)
    if not args.check:
        if not args.repo:
            ap.error("--repo is needed to build")
        build(args.repo, _git(args.repo, "rev-parse", args.commit).decode().strip(), args.tag, args.base)
    print(check(args.tag))
    return 0


if __name__ == "__main__":
    sys.exit(main())
