"""Run one change of a seed from a repository variant's snapshot, or from a named start, on a disposable fork
(design.md, "Later seeds and variants": each change is forked from the same final snapshot and discarded).

    ../plumbing/with-token.sh python3.12 run_fork.py --variants ../runs/clowder-variants/v1 --variant stripped \\
        --arm bare --change 3 --repeat 1 --replicate r1 --window 200k
    ../plumbing/with-token.sh python3.12 run_fork.py --starts ../runs/opengym-m2h/starts.json --start lid-r1 \\
        --arm lid-full-arrows --seed-dir ../seeds/opengym --change 3 --repeat 1 --replicate m2h-r1 --window 1m

A Clowder fork starts from a variant in a manifest clowder_variants.py wrote (--variants, --variant); its volumes are
ce-<id>-ws and ce-<id>-cfg. A fork from a named start (--starts, --start; M2h) starts from a volume a starts file names
(m2h_starts.py writes M2h's: the shared bare start and one mapped LID start per replicate), at the commit it names:
the copy is checked at that commit with nothing uncommitted, the start is only ever mounted read-only, and the fork's
volumes are <id>-ws and <id>-cfg, where the id carries the file's fork prefix (m2h-) and never names a start's volume.
The starts file gives the image (the Node executor image for openGym) unless --image does, and --seed-dir is required.
For a LID arm the plugins are installed fresh at the arm's release, as for a Clowder fork; when the start names its
map's LID tree hash (lid_sha256), the fresh install must hash the same or the fork stops before any session.

The fork gets a fresh workspace volume copied from the variant's volume (built by clowder_variants.py), a fresh
configuration volume with the arm's own setup (the LID plugin for lid-full), and an owner with no history: the seed's
oracle, change script, owner items, and brief, from --seed-dir unless named one by one. Since no other change
happened in the fork, the owner holds the start's narrative and items and the forked change's own, and nothing of
any other change. If the change has a planted
bug (--patch, the change-script entry's **Planted bug:** path, or a sidecar hidden/patches/change-NN.diff), it is
applied to the variant and folded into the snapshot's one commit before the arm starts, so neither `git log` nor
`git show` shows it; a patch that doesn't apply cleanly stops the fork. The agent runs in the Rust executor image
(or the starts file's) with GitHub's hosts blocked and web search and fetch denied (--no-isolate lifts both), at the
--window given. npm's registries stay reachable unless --npm-network off blocks them too (the openGym mapping sessions
had them); the setting is recorded as npm_network.

Records go to ../runs/<id>/ the way run_trajectory.py writes them (trajectory.json with the change under "changes",
change-NN/, owner-state-NN.json), so grading and context_telemetry.py read a fork like a trajectory. The fork's
metadata records the variant or start, the isolation and window, the replicate, the owner model, the planted bug's
hash, every input's path and hash, and for a named start's LID arm the installed LID tree's hash. A Clowder fork's
target/ is deleted once the change is recorded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import clowder_variants as cv  # noqa: E402
from costeval import executor, simulator, trajectory  # noqa: E402
from run_trajectory import CLAUDE_CODE, IMAGE as ROLE_IMAGE, ROLES_VOLUME, owner_model_from_arg, sha256  # noqa: E402

IMAGE = "lid-cost-eval-executor-rust:2.1.323"
SEED_DIR = HERE.parent / "seeds" / "clowder"
# npm's registries, blocked as GitHub's hosts are only under --npm-network off.
NPM_HOSTS = ("registry.npmjs.org", "registry.npmjs.com", "registry.yarnpkg.com")
# One hash over every file of the installed LID tree (paths and contents), comparable across volumes.
LID_TREE_SCRIPT = "cd /cfg/lid && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum"


@dataclass
class Deps:
    """What a fork reaches outside itself; tests replace each part."""
    docker: Callable = subprocess.run
    turn_for: Callable | None = None  # session -> turn function; default: executor.run_turn in that session
    workspace_for: Callable | None = None  # (image, volume) -> workspace; default: trajectory.DockerWorkspace
    ask: Callable | None = None  # the owner's model calls; default: role sessions
    touch: Callable | None = None
    trim: Callable | None = None
    check: Callable | None = None  # the owner's completion check
    install_lid: Callable = trajectory.install_lid


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variants", type=Path, help="the folder clowder_variants.py wrote (its manifest.json)")
    ap.add_argument("--variant", help="full, lid, or stripped")
    ap.add_argument("--starts", type=Path,
                    help="a starts file (m2h_starts.py): {image, fork_prefix, starts: {name: {volume, commit, vcs, ...}}}; "
                         "in place of --variants")
    ap.add_argument("--start", help="the start's name in --starts (M2h: bare, lid-r1, lid-r2, lid-r3)")
    ap.add_argument("--npm-network", choices=("on", "off"), default="on",
                    help="off blocks npm's registries as GitHub's hosts are (default on, as the openGym mapping had it)")
    ap.add_argument("--arm", help="required unless --null")
    ap.add_argument("--null", action="store_true",
                    help="no agent and no owner: prepare the fork's snapshot as for any arm (planted bug and all) and "
                         "record it unchanged as the change's result, to dry-run grading on a build with no change")
    ap.add_argument("--change", type=int, required=True)
    ap.add_argument("--repeat", type=int, required=True, help="the fork's number, for repeats of one change")
    ap.add_argument("--replicate", required=True, help="the seed the owner's draws are keyed on")
    ap.add_argument("--window", choices=sorted(executor.WINDOWS), required=True)
    ap.add_argument("--no-isolate", action="store_true", help="don't block GitHub or deny web tools")
    ap.add_argument("--seed-dir", type=Path, default=None,
                    help="default seeds/clowder for a Clowder fork; required for a named start")
    ap.add_argument("--oracle", type=Path, help="default: <seed-dir>/hidden/oracle.md")
    ap.add_argument("--change-script", type=Path, help="default: <seed-dir>/hidden/change-script.md")
    ap.add_argument("--owner-items", type=Path, help="default: <seed-dir>/hidden/owner-items.json")
    ap.add_argument("--brief", type=Path, help="default: <seed-dir>/brief.md")
    ap.add_argument("--patch", type=Path, help="a planted bug to apply, in place of the change script's or a sidecar")
    ap.add_argument("--result-patch", type=Path,
                    help="null forks only: a patch committed after the snapshot as the change's result (a right build, "
                         "the instrument's positive control), so the graders' diff from the start shows it")
    ap.add_argument("--id", help="default: cf-<variant>-<arm>-<window>-cNN-r<repeat>, or from a named start "
                                 "<fork prefix><arm>-cNN-r<repeat>")
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--effort", default="medium")
    ap.add_argument("--policy", default="diligent", choices=simulator.POLICIES)
    ap.add_argument("--owner-model", default="claude-sonnet-5-5")
    ap.add_argument("--owner-model-config", default=None)
    ap.add_argument("--round-cap", type=int, default=trajectory.ROUND_CAP)
    ap.add_argument("--turn-timeout", type=int, default=3600)
    ap.add_argument("--lid-repo", type=Path, default=None)
    ap.add_argument("--image", default=None, help=f"default: the starts file's image, else {IMAGE}")
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    return ap


def fork_id(variant: str, arm: str, window: str, change: int, repeat: int) -> str:
    return f"cf-{variant}-{arm}-{window}-c{change:02d}-r{repeat}"


def is_named_start(fork_of: dict | None) -> bool:
    """Whether a fork (by its record's fork_of) started from a named start rather than a Clowder variant."""
    return bool((fork_of or {}).get("start"))


def fork_volumes(fid: str, named: bool) -> tuple[str, str]:
    """A fork's own workspace and configuration volumes: ce-<id>-* for a Clowder fork, <id>-* for a named start's (its
    id carries the starts file's prefix, as m2h-)."""
    return (f"{fid}-ws", f"{fid}-cfg") if named else (f"ce-{fid}-ws", f"ce-{fid}-cfg")


def isolation_for(window: str, *, isolate: bool = True, npm_network: bool = True) -> executor.Isolation:
    """GitHub's hosts blocked and web tools denied unless not isolated; npm's registries blocked too when npm_network is
    off. Isolated with npm on is executor.Isolation.for_public_seed."""
    hosts = (executor.GITHUB_HOSTS if isolate else ()) + (() if npm_network else NPM_HOSTS)
    return executor.Isolation(blocked_hosts=hosts, denied_tools=executor.WEB_TOOLS if isolate else (), window=window)


def lid_tree_sha256(docker: Callable, image: str, config_volume: str) -> str:
    """The hash of the LID tree installed at /cfg/lid in a configuration volume, mounted read-only."""
    p = docker(["docker", "run", "--rm", "-v", f"{config_volume}:/cfg:ro", image, "sh", "-c", LID_TREE_SCRIPT],
               capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"hashing the LID tree in {config_volume} failed ({p.returncode}): {(p.stderr or '')[-400:]}")
    return (p.stdout.split() or [""])[0]


def check_lid_tree(docker: Callable, image: str, config_volume: str, want: str | None) -> str:
    """Hash a fresh LID install; when there is a hash to match (the start's map's, or the repaired fork's), a different
    tree stops the fork before any session."""
    got = lid_tree_sha256(docker, image, config_volume)
    if want and got != want:
        raise RuntimeError(f"the LID install in {config_volume} hashes {got}, not {want} (the tree it must match); "
                           "the release tag or the install differs")
    return got


def load_start(path: Path, name: str) -> tuple[dict, dict] | None:
    """The starts file and the named start in it, or None when it has no such start."""
    starts = json.loads(path.read_text())
    start = (starts.get("starts") or {}).get(name)
    if not start or not start.get("volume") or not start.get("commit"):
        return None
    return starts, start


def planted_bug_path(args, change: simulator.Change, script_path: Path) -> Path | None:
    """The change's planted bug, if it has one: --patch, then the change script's field, then a sidecar (in --seed-dir,
    which for arguments parsed without it is the Clowder seed's, as before named starts)."""
    if args.patch:
        return args.patch
    if change.planted_bug:
        return script_path.parent / change.planted_bug
    for ext in ("diff", "patch"):
        side = (args.seed_dir or SEED_DIR) / "hidden" / "patches" / f"change-{change.number:02d}.{ext}"
        if side.exists():
            return side
    return None


def _run(deps: Deps, cmd: list[str], *, input: str | None = None, what: str) -> subprocess.CompletedProcess:
    p = deps.docker(cmd, input=input, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"{what} failed ({p.returncode}): {(p.stderr or '')[-800:]}")
    return p


def copy_variant(deps: Deps, image: str, variant_volume: str, workspace_volume: str) -> None:
    _run(deps, ["docker", "run", "--rm", "-v", f"{variant_volume}:/src:ro", "-v", f"{workspace_volume}:/work", image,
                "sh", "-c", "find /work -mindepth 1 -delete && cp -a /src/. /work/"], what="copying the variant")


def copy_start_script(commit: str) -> str:
    """Copy /src into the empty /work, then check the copy: HEAD is the start's commit, and nothing is uncommitted
    (ignored files such as node_modules come along and don't count)."""
    return ("find /work -mindepth 1 -delete && cp -a /src/. /work/ && cd /work"
            f" && head=$(git rev-parse HEAD) && want=$(git rev-parse --verify '{commit}^{{commit}}')"
            " && { [ \"$head\" = \"$want\" ] || { echo \"the copy is at $head, not the start's $want\" >&2; exit 3; }; }"
            " && dirty=$(git status --porcelain)"
            " && { [ -z \"$dirty\" ] || { echo \"the start has uncommitted changes: $(echo \"$dirty\" | head -5)\" >&2;"
            " exit 3; }; }")


def copy_start(deps: Deps, image: str, start_volume: str, workspace_volume: str, commit: str) -> None:
    """A named start copied into the fork's own volume; the start is mounted read-only, so it stays as it was."""
    _run(deps, ["docker", "run", "--rm", "-v", f"{start_volume}:/src:ro", "-v", f"{workspace_volume}:/work", image,
                "sh", "-c", copy_start_script(commit)], what=f"copying the start {start_volume} at {commit}")


# Nothing may still reach the snapshot as it was before the bug: jj's own state and the refs it keeps commits alive
# with go first (a jj variant gets a fresh jj repository afterwards), then the amend, main moved onto it, the reflog
# expired, and the old commit pruned.
_FORGET = ("rm -rf .jj && (git for-each-ref --format='%(refname)' refs/jj | xargs -r -n1 git update-ref -d)")
_PRUNE = ("git update-ref refs/heads/main HEAD && git reflog expire --expire=now --all && git gc -q --prune=now")


def plant_bug(deps: Deps, image: str, workspace_volume: str, patch: str, *, variant: str, change: int) -> str:
    """Apply the patch and amend it into the snapshot's commit, at the variants' fixed date, leaving no trace of the
    commit before it. Returns the new commit."""
    date = cv.DATE
    script = (f"cd /work && {_FORGET} && cat > /tmp/planted.diff && git apply --check /tmp/planted.diff"
              " && git apply /tmp/planted.diff"
              f" && git add -A && GIT_COMMITTER_DATE='{date}' git commit -q --amend --no-edit --date='{date}'"
              f" && rm /tmp/planted.diff && {_PRUNE} && git rev-parse HEAD")
    p = deps.docker(["docker", "run", "--rm", "-i", "-v", f"{workspace_volume}:/work", image, "sh", "-c", script],
                    input=patch, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"the planted bug for change {change} doesn't apply cleanly to the {variant} variant: "
                           f"{(p.stderr or '')[-800:]}")
    return p.stdout.strip()


def commit_result_patch(deps: Deps, image: str, workspace_volume: str, patch: str, *, change: int) -> str:
    """Apply a patch and commit it after the snapshot, as a change's result; returns the new commit."""
    name, email = trajectory.GIT_IDENTITY
    script = (f"cd /work && cat > /tmp/result.diff && git apply --check /tmp/result.diff && git apply /tmp/result.diff"
              f" && git add -A && git -c user.name='{name}' -c user.email='{email}' commit -q"
              f" -m 'Change {change}: the right build (the instrument positive control)'"
              f" && rm /tmp/result.diff && git rev-parse HEAD")
    p = deps.docker(["docker", "run", "--rm", "-i", "-v", f"{workspace_volume}:/work", image, "sh", "-c", script],
                    input=patch, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"the result patch for change {change} doesn't apply cleanly: {(p.stderr or '')[-800:]}")
    return p.stdout.strip()


def init_jj(deps: Deps, image: str, workspace_volume: str) -> None:
    """A fresh colocated jj repository over the snapshot, so jj's history starts at the commit the arm starts from."""
    _run(deps, ["docker", "run", "--rm", "-v", f"{workspace_volume}:/work", image, "sh", "-c",
                f"cd /work && {_FORGET} && jj git init --colocate >/dev/null 2>&1"], what="setting up jj")


def add_arm_files(deps: Deps, image: str, workspace_volume: str, arm: trajectory.Arm) -> None:
    for dest, src in arm.workspace_files.items():
        _run(deps, ["docker", "run", "--rm", "-i", "-v", f"{workspace_volume}:/work", image, "sh", "-c",
                    f"mkdir -p \"$(dirname '/work/{dest}')\" && cat > '/work/{dest}'"],
             input=(trajectory.ARMS_DIR / src).read_text(encoding="utf-8"), what=f"adding the arm's {dest}")


def clean_target(deps: Deps, image: str, workspace_volume: str) -> None:
    deps.docker(["docker", "run", "--rm", "-v", f"{workspace_volume}:/work", image, "sh", "-c", "rm -rf /work/target"],
                capture_output=True, text=True)


def _role_calls(owner_model: str, costs: list[float]):
    role = executor.RoleSession(image=ROLE_IMAGE, config_volume=ROLES_VOLUME, model=owner_model,
                                claude_code_version=CLAUDE_CODE, effort="medium")

    def call(schema: str):
        def run(prompt: str):
            r = executor.run_role(role, prompt, json_schema=schema)
            cost = r.usage.reported_cost_usd or 0.0
            costs.append(cost)
            return r.structured, cost
        return run
    return (call(simulator.schema_json()), call(simulator.touch_schema_json()), call(simulator.trim_schema_json()),
            call(simulator.completion_schema_json()))


def main(argv=None, *, deps: Deps | None = None) -> int:
    deps = deps or Deps()
    ap = build_parser()
    args = ap.parse_args(argv)
    if args.null:
        args.arm = "null"
    elif not args.arm:
        ap.error("--arm is required (or --null)")
    if args.result_patch and not args.null:
        ap.error("--result-patch is for a null fork only")
    named = args.starts is not None or args.start is not None
    if named == (args.variants is not None or args.variant is not None):
        ap.error("name one source: a start (--starts and --start) or a Clowder variant (--variants and --variant)")
    if named and not (args.starts and args.start):
        ap.error("--starts and --start go together")
    if not named and not (args.variants and args.variant):
        ap.error("--variants and --variant go together")
    if named and args.seed_dir is None:
        ap.error("--seed-dir is required for a named start (the Clowder default would bring its patches and brief)")
    args.seed_dir = args.seed_dir or SEED_DIR
    if named:
        found = load_start(args.starts, args.start)
        if found is None:
            print(f"no start {args.start!r} with a volume and a commit in {args.starts}")
            return 2
        starts, source = found
        image = args.image or starts.get("image") or IMAGE
        prefix = starts.get("fork_prefix") or ""
        fid = args.id or f"{prefix}{args.arm}-c{args.change:02d}-r{args.repeat}"
    else:
        manifest = json.loads((args.variants / "manifest.json").read_text())
        if args.variant not in manifest["variants"]:
            print(f"no variant {args.variant!r} in {args.variants}")
            return 2
        source = manifest["variants"][args.variant]
        if not source.get("volume"):
            print(f"variant {args.variant!r} has no volume; build it with clowder_variants.py --volumes")
            return 2
        image = args.image or IMAGE
        fid = args.id or fork_id(args.variant, args.arm, args.window, args.change, args.repeat)
    ws_vol, cfg_vol = fork_volumes(fid, named)
    if named:
        if prefix and not fid.startswith(prefix):
            print(f"{fid}: forks from {args.starts} have ids starting {prefix!r}")
            return 2
        taken = {v for s in starts["starts"].values() for v in (s.get("volume"), s.get("config_volume")) if v}
        if {ws_vol, cfg_vol} & taken:
            print(f"{fid}: its volumes would be a start's own ({sorted({ws_vol, cfg_vol} & taken)})")
            return 2
    out = args.runs / fid
    meta_path = out / "trajectory.json"
    if meta_path.exists():
        print(f"{fid} already exists")
        return 2
    oracle_path = args.oracle or args.seed_dir / "hidden" / "oracle.md"
    script_path = args.change_script or args.seed_dir / "hidden" / "change-script.md"
    items_path = args.owner_items or args.seed_dir / "hidden" / "owner-items.json"
    brief_path = args.brief or args.seed_dir / "brief.md"
    oracle = simulator.parse_oracle(oracle_path.read_text(encoding="utf-8"))
    script = simulator.parse_change_script(script_path.read_text(encoding="utf-8"))
    if args.change not in script:
        print(f"change {args.change} isn't in {script_path}")
        return 2
    change = script[args.change]
    owner_items = simulator.load_owner_items(items_path, oracle)
    brief = brief_path.read_text(encoding="utf-8")
    arm = (SimpleNamespace(name="null", lid_release=None, workspace_files={}, plugins=(), plugin_dirs=()) if args.null
           else trajectory.load_arm(args.arm))
    if named and arm.lid_release and source.get("lid_release") and arm.lid_release != source["lid_release"]:
        print(f"{fid}: the arm's LID release {arm.lid_release} isn't the {source['lid_release']} the start's map used")
        return 2
    owner_model = owner_model_from_arg(args.owner_model_config)
    npm_network = args.npm_network == "on"
    isolation = isolation_for(args.window, isolate=not args.no_isolate, npm_network=npm_network)
    patch_path = planted_bug_path(args, change, script_path)
    patch = patch_path.read_text(encoding="utf-8") if patch_path else None

    if named:
        copy_start(deps, image, source["volume"], ws_vol, source["commit"])
    else:
        copy_variant(deps, image, source["volume"], ws_vol)
    if patch is not None:
        plant_bug(deps, image, ws_vol, patch, variant=args.start if named else args.variant, change=args.change)
    if source.get("vcs") == "jj":
        init_jj(deps, image, ws_vol)
    lid_tree = None
    if arm.lid_release:
        repo = args.lid_repo or Path(subprocess.run(["git", "-C", str(HERE), "rev-parse", "--show-toplevel"],
                                                    capture_output=True, text=True, check=True).stdout.strip())
        deps.install_lid(image, cfg_vol, repo, arm.lid_release)
        if named:  # the same LID tree the start's map ran with, checked before any session
            lid_tree = check_lid_tree(deps.docker, image, cfg_vol, source.get("lid_sha256"))
    workspace = (deps.workspace_for or trajectory.DockerWorkspace)(image, ws_vol)
    if arm.workspace_files:
        add_arm_files(deps, image, ws_vol, arm)
        workspace.commit_all("Add the arm's files")
    base = workspace.head()

    out.mkdir(parents=True, exist_ok=True)
    if named:
        fork_of = {"starts": str(args.starts), "start": args.start, "volume": source["volume"],
                   "commit": source["commit"], "vcs": source.get("vcs", "git"), "map": source.get("map"),
                   "config_volume": source.get("config_volume"), "lid_sha256": source.get("lid_sha256"),
                   "starts_sha256": sha256(args.starts)}
    else:
        fork_of = {"variants": str(args.variants), "variant": args.variant, "volume": source["volume"],
                   "commit": source["commit"], "source_commit": manifest.get("source_commit"),
                   "variant_seed": manifest.get("seed"), "vcs": source.get("vcs", "git")}
    meta = {
        "id": fid, "fork_of": fork_of,
        "arm": arm.name, "seed": args.seed_dir.name, "change": args.change, "repeat": args.repeat, "model": args.model,
        "effort": args.effort, "claude_code": CLAUDE_CODE, "image": image, "policy": args.policy,
        "owner_model": args.owner_model, "replicate": args.replicate, "owner_model_config": asdict(owner_model),
        "isolation": isolation.record(), "npm_network": npm_network, "window": args.window,
        "lid_release": arm.lid_release, **({"lid_install_sha256": lid_tree} if lid_tree is not None else {}),
        "owner_scope": simulator.FORK_SCOPE,
        "round_cap": args.round_cap, "neutral_sentence": trajectory.NEUTRAL_SENTENCE,
        "planted_bug": ({"path": str(patch_path), "sha256": hashlib.sha256(patch.encode()).hexdigest()}
                        if patch is not None else None),
        "paths": {"brief": str(brief_path.resolve()), "oracle": str(oracle_path.resolve()),
                  "change_script": str(script_path.resolve()), "owner_items": str(items_path.resolve())},
        "hashes": {"brief": sha256(brief_path), "oracle": sha256(oracle_path), "change_script": sha256(script_path),
                   "owner_items": sha256(items_path), "simulator_template": sha256(simulator.TEMPLATE_PATH),
                   "touch_template": sha256(simulator.TOUCH_TEMPLATE_PATH),
                   "trim_template": sha256(simulator.TRIM_TEMPLATE_PATH)},
        "volumes": {"workspace": ws_vol, "config": cfg_vol}, "start_commit": base,
        "started": datetime.now(timezone.utc).isoformat(timespec="seconds"), "changes": {},
    }
    meta_path.write_text(json.dumps(meta, indent=1))
    if args.null:  # the change's result is the snapshot it started from, or the result patch committed after it
        result = base
        if args.result_patch:
            text = args.result_patch.read_text(encoding="utf-8")
            result = commit_result_patch(deps, image, ws_vol, text, change=args.change)
            meta["result_patch"] = {"path": str(args.result_patch), "sha256": hashlib.sha256(text.encode()).hexdigest()}
        meta["changes"][str(args.change)] = {"title": change.title, "null": True, "rounds": 0, "finished": True,
                                             "capped": False, "error": None, "commit": result, "redirect": None,
                                             "agent_cost_usd": 0.0, "owner_cost_usd": 0.0, "minutes": 0.0,
                                             **({"result_patch": True} if args.result_patch else {})}
        meta_path.write_text(json.dumps(meta, indent=1))
        print(f"{fid}: null fork at {base}", flush=True)
        return 0

    costs: list[float] = []
    ask, touch, trim, check = deps.ask, deps.touch, deps.trim, deps.check
    if ask is None:
        ask, touch, trim, check = _role_calls(args.owner_model, costs)
    # Each change forks from the final snapshot, so no earlier change happened: the owner holds the start's narrative
    # and items and this change's own, never another change's.
    owner = simulator.Owner(oracle=oracle, brief=brief, policy=args.policy, replicate=args.replicate, ask=ask,
                            touch=touch, trim=trim, model=owner_model, owner_items=owner_items, only_change=True,
                            check=check)
    session = executor.ContainerSession(image=image, workspace_volume=ws_vol, config_volume=cfg_vol,
                                        model=args.model, claude_code_version=CLAUDE_CODE,
                                        expected_plugins=frozenset(arm.plugins), effort=args.effort,
                                        plugin_dirs=arm.plugin_dirs, timeout_s=args.turn_timeout, isolation=isolation)
    if deps.turn_for is not None:
        turn = deps.turn_for(session)
    else:
        def turn(prompt, stream_path, *, resume=None, permission_mode="bypassPermissions"):
            return executor.run_turn(session, prompt, stream_path, resume=resume, permission_mode=permission_mode)

    start = time.monotonic()
    try:
        res = trajectory.run_change(arm=arm, change=change, owner=owner, turn=turn, workspace=workspace,
                                    out_dir=out / f"change-{args.change:02d}", round_cap=args.round_cap)
    finally:
        if not named:
            clean_target(deps, image, ws_vol)  # disk is short; a cold build takes about 40 seconds
    agent_cost = sum((t["usage"] or {}).get("reported_cost_usd") or 0 for t in res.turns)
    meta["changes"][str(args.change)] = {"title": res.title, "rounds": res.rounds, "finished": res.finished,
                                         "capped": res.capped, "error": res.error, "commit": res.commit,
                                         "redirect": res.redirect, "agent_cost_usd": round(agent_cost, 4),
                                         "owner_cost_usd": round(sum(costs), 4),
                                         "minutes": round((time.monotonic() - start) / 60, 1)}
    meta_path.write_text(json.dumps(meta, indent=1))
    state = json.dumps(trajectory.owner_state(owner), indent=1)
    (out / f"owner-state-{args.change:02d}.json").write_text(state)
    (out / "owner-state.json").write_text(state)
    print(f"{fid}: rounds {res.rounds}, finished {res.finished}, agent ${agent_cost:.2f}, error {res.error}", flush=True)
    return 0 if not res.error else 1


if __name__ == "__main__":
    sys.exit(main())
