"""M2h's named starts, written as the starts file run_fork.py --starts reads (plan.md, M2h; m2h-harness-needs.md,
"Starts and volumes"): the shared bare start, and one mapped LID start per replicate.

    python3.12 m2h_starts.py --maps ../runs/opengym-map --out ../runs/opengym-m2h/starts.json

From the mapping records (opengym_map.py's mapping.json): the bare start is ogmap-bare's "Start" commit in its volume,
and LID start r<k> is the k-th map's committed map in its own volume (r1 ogmap-2, r2 ogmap-3, r3 ogmap-4), with its
configuration volume, release and plugins for the record. Before anything is written, every map must share the bare
start's commit and be done, every start volume's HEAD must be its commit, and every map's installed LID tree must hash
the same; that hash (lid_sha256) is what a fork's fresh LID install must match. Volumes are only mounted read-only.

The file: {"maps", "written", "image", "fork_prefix": "m2h-", "starts": {"bare": {volume, commit, vcs, map},
"lid-r1": {volume, commit, vcs, map, config_volume, lid_release, plugins, lid_sha256}, ...}}.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import run_fork as rf  # noqa: E402

BARE = "ogmap-bare"
REPLICATES = (("lid-r1", "ogmap-2"), ("lid-r2", "ogmap-3"), ("lid-r3", "ogmap-4"))
FORK_PREFIX = "m2h-"


def head(docker: Callable, image: str, volume: str) -> str:
    p = docker(["docker", "run", "--rm", "-v", f"{volume}:/src:ro", image, "git", "-C", "/src", "rev-parse", "HEAD"],
               capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else f"(git failed: {(p.stderr or '').strip()[-200:]})"


def build(maps: Path, docker: Callable) -> dict:
    """The starts file's content; ValueError when a record or a volume isn't as the starts need."""
    records = {}
    for run_id in (BARE, *(m for _, m in REPLICATES)):
        path = maps / run_id / "mapping.json"
        if not path.exists():
            raise ValueError(f"no mapping record {path}")
        records[run_id] = json.loads(path.read_text())
    bare = records[BARE]
    if not bare.get("bare_start"):
        raise ValueError(f"{BARE} records no bare start")
    for _, m in REPLICATES:
        r = records[m]
        if r.get("bare_start") != bare["bare_start"]:
            raise ValueError(f"{m} starts from {r.get('bare_start')}, not the shared bare start {bare['bare_start']}")
        if not r.get("lid_start") or r.get("stop") != "done":
            raise ValueError(f"{m} isn't a finished map (stop {r.get('stop')!r}, lid_start {r.get('lid_start')!r})")
    images = {r.get("image") for r in records.values()}
    if len(images) != 1 or None in images:
        raise ValueError(f"the records name more than one image: {sorted(map(str, images))}")
    image = images.pop()
    starts = {"bare": {"volume": bare["volumes"]["workspace"], "commit": bare["bare_start"], "vcs": "git", "map": BARE}}
    for name, m in REPLICATES:
        r = records[m]
        starts[name] = {"volume": r["volumes"]["workspace"], "commit": r["lid_start"], "vcs": "git", "map": m,
                        "config_volume": r["volumes"]["config"], "lid_release": r.get("lid_release"),
                        "plugins": r.get("plugins")}
    for name, s in starts.items():
        got = head(docker, image, s["volume"])
        if got != s["commit"]:
            raise ValueError(f"{s['volume']} (start {name}) is at {got}, not {s['commit']}")
    trees = {name: rf.lid_tree_sha256(docker, image, s["config_volume"]) for name, s in starts.items()
             if s.get("config_volume")}
    if len(set(trees.values())) != 1:
        raise ValueError(f"the maps' LID trees differ: {trees}")
    for name, tree in trees.items():
        starts[name]["lid_sha256"] = tree
    return {"maps": str(maps), "written": datetime.now(timezone.utc).isoformat(timespec="seconds"), "image": image,
            "fork_prefix": FORK_PREFIX, "starts": starts}


def main(argv=None, *, docker: Callable = subprocess.run) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--maps", type=Path, default=HERE.parent / "runs" / "opengym-map",
                    help="opengym_map.py's records (<maps>/<id>/mapping.json)")
    ap.add_argument("--out", type=Path, default=HERE.parent / "runs" / "opengym-m2h" / "starts.json")
    args = ap.parse_args(argv)
    try:
        d = build(args.maps, docker)
    except ValueError as e:
        print(f"no starts written: {e}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(d, indent=1) + "\n")
    for name, s in d["starts"].items():
        print(f"{name}: {s['volume']} at {s['commit'][:12]}" + (f", LID tree {s['lid_sha256'][:12]}" if "lid_sha256" in s
                                                              else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
