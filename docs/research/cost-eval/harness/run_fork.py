"""Run one change of a seed from a repository variant's snapshot, on a disposable fork (design.md, "Later seeds and
variants": each change is forked from the same final snapshot and discarded).

    ../plumbing/with-token.sh python3.12 run_fork.py --variants ../runs/clowder-variants/v1 --variant stripped \\
        --arm bare --change 3 --repeat 1 --replicate r1 --window 200k

The fork gets a fresh workspace volume copied from the variant's volume (built by clowder_variants.py), a fresh
configuration volume with the arm's own setup (the LID plugin for lid-full), and an owner with no history: the seed's
oracle, change script, owner items, and brief, from --seed-dir unless named one by one. Since no other change
happened in the fork, the owner holds the start's narrative and items and the forked change's own, and nothing of
any other change. If the change has a planted
bug (--patch, the change-script entry's **Planted bug:** path, or a sidecar hidden/patches/change-NN.diff), it is
applied to the variant and folded into the snapshot's one commit before the arm starts, so neither `git log` nor
`git show` shows it; a patch that doesn't apply cleanly stops the fork. The agent runs in the Rust executor image
with GitHub's hosts blocked and web search and fetch denied (--no-isolate lifts both), at the --window given.

Records go to ../runs/<id>/ the way run_trajectory.py writes them (trajectory.json with the change under "changes",
change-NN/, owner-state-NN.json), so grading and context_telemetry.py read a fork like a trajectory. The fork's
metadata records the variant, the isolation and window, the replicate, the owner model, the planted bug's hash, and
every input's hash. The workspace's target/ is deleted once the change is recorded.
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
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import clowder_variants as cv  # noqa: E402
from costeval import executor, simulator, trajectory  # noqa: E402
from run_trajectory import CLAUDE_CODE, IMAGE as ROLE_IMAGE, ROLES_VOLUME, owner_model_from_arg, sha256  # noqa: E402

IMAGE = "lid-cost-eval-executor-rust:2.1.323"


@dataclass
class Deps:
    """What a fork reaches outside itself; tests replace each part."""
    docker: Callable = subprocess.run
    turn_for: Callable | None = None  # session -> turn function; default: executor.run_turn in that session
    workspace_for: Callable | None = None  # (image, volume) -> workspace; default: trajectory.DockerWorkspace
    ask: Callable | None = None  # the owner's model calls; default: role sessions
    touch: Callable | None = None
    trim: Callable | None = None
    install_lid: Callable = trajectory.install_lid


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variants", type=Path, required=True, help="the folder clowder_variants.py wrote (its manifest.json)")
    ap.add_argument("--variant", required=True, help="full, lid, or stripped")
    ap.add_argument("--arm", required=True)
    ap.add_argument("--change", type=int, required=True)
    ap.add_argument("--repeat", type=int, required=True, help="the fork's number, for repeats of one change")
    ap.add_argument("--replicate", required=True, help="the seed the owner's draws are keyed on")
    ap.add_argument("--window", choices=sorted(executor.WINDOWS), required=True)
    ap.add_argument("--no-isolate", action="store_true", help="don't block GitHub or deny web tools")
    ap.add_argument("--seed-dir", type=Path, default=HERE.parent / "seeds" / "clowder")
    ap.add_argument("--oracle", type=Path, help="default: <seed-dir>/hidden/oracle.md")
    ap.add_argument("--change-script", type=Path, help="default: <seed-dir>/hidden/change-script.md")
    ap.add_argument("--owner-items", type=Path, help="default: <seed-dir>/hidden/owner-items.json")
    ap.add_argument("--brief", type=Path, help="default: <seed-dir>/brief.md")
    ap.add_argument("--patch", type=Path, help="a planted bug to apply, in place of the change script's or a sidecar")
    ap.add_argument("--id", help="default: cf-<variant>-<arm>-<window>-cNN-r<repeat>")
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--effort", default="medium")
    ap.add_argument("--policy", default="diligent", choices=simulator.POLICIES)
    ap.add_argument("--owner-model", default="claude-sonnet-5-5")
    ap.add_argument("--owner-model-config", default=None)
    ap.add_argument("--round-cap", type=int, default=trajectory.ROUND_CAP)
    ap.add_argument("--turn-timeout", type=int, default=3600)
    ap.add_argument("--lid-repo", type=Path, default=None)
    ap.add_argument("--image", default=IMAGE)
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    return ap


def fork_id(variant: str, arm: str, window: str, change: int, repeat: int) -> str:
    return f"cf-{variant}-{arm}-{window}-c{change:02d}-r{repeat}"


def planted_bug_path(args, change: simulator.Change, script_path: Path) -> Path | None:
    """The change's planted bug, if it has one: --patch, then the change script's field, then a sidecar."""
    if args.patch:
        return args.patch
    if change.planted_bug:
        return script_path.parent / change.planted_bug
    for ext in ("diff", "patch"):
        side = args.seed_dir / "hidden" / "patches" / f"change-{change.number:02d}.{ext}"
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
    return call(simulator.schema_json()), call(simulator.touch_schema_json()), call(simulator.trim_schema_json())


def main(argv=None, *, deps: Deps | None = None) -> int:
    deps = deps or Deps()
    args = build_parser().parse_args(argv)
    manifest = json.loads((args.variants / "manifest.json").read_text())
    if args.variant not in manifest["variants"]:
        print(f"no variant {args.variant!r} in {args.variants}")
        return 2
    variant = manifest["variants"][args.variant]
    if not variant.get("volume"):
        print(f"variant {args.variant!r} has no volume; build it with clowder_variants.py --volumes")
        return 2
    fid = args.id or fork_id(args.variant, args.arm, args.window, args.change, args.repeat)
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
    arm = trajectory.load_arm(args.arm)
    owner_model = owner_model_from_arg(args.owner_model_config)
    isolation = (executor.Isolation(window=args.window) if args.no_isolate
                 else executor.Isolation.for_public_seed(window=args.window))
    patch_path = planted_bug_path(args, change, script_path)
    patch = patch_path.read_text(encoding="utf-8") if patch_path else None
    ws_vol, cfg_vol = f"ce-{fid}-ws", f"ce-{fid}-cfg"

    copy_variant(deps, args.image, variant["volume"], ws_vol)
    if patch is not None:
        plant_bug(deps, args.image, ws_vol, patch, variant=args.variant, change=args.change)
    if variant.get("vcs") == "jj":
        init_jj(deps, args.image, ws_vol)
    if arm.lid_release:
        repo = args.lid_repo or Path(subprocess.run(["git", "-C", str(HERE), "rev-parse", "--show-toplevel"],
                                                    capture_output=True, text=True, check=True).stdout.strip())
        deps.install_lid(args.image, cfg_vol, repo, arm.lid_release)
    workspace = (deps.workspace_for or trajectory.DockerWorkspace)(args.image, ws_vol)
    if arm.workspace_files:
        add_arm_files(deps, args.image, ws_vol, arm)
        workspace.commit_all("Add the arm's files")
    base = workspace.head()

    out.mkdir(parents=True, exist_ok=True)
    meta = {
        "id": fid, "fork_of": {"variants": str(args.variants), "variant": args.variant, "volume": variant["volume"],
                               "commit": variant["commit"], "source_commit": manifest.get("source_commit"),
                               "variant_seed": manifest.get("seed"), "vcs": variant.get("vcs", "git")},
        "arm": arm.name, "seed": args.seed_dir.name, "change": args.change, "repeat": args.repeat, "model": args.model,
        "effort": args.effort, "claude_code": CLAUDE_CODE, "image": args.image, "policy": args.policy,
        "owner_model": args.owner_model, "replicate": args.replicate, "owner_model_config": asdict(owner_model),
        "isolation": isolation.record(), "window": args.window, "lid_release": arm.lid_release,
        "owner_scope": simulator.FORK_SCOPE,
        "round_cap": args.round_cap, "neutral_sentence": trajectory.NEUTRAL_SENTENCE,
        "planted_bug": ({"path": str(patch_path), "sha256": hashlib.sha256(patch.encode()).hexdigest()}
                        if patch is not None else None),
        "hashes": {"brief": sha256(brief_path), "oracle": sha256(oracle_path), "change_script": sha256(script_path),
                   "owner_items": sha256(items_path), "simulator_template": sha256(simulator.TEMPLATE_PATH),
                   "touch_template": sha256(simulator.TOUCH_TEMPLATE_PATH),
                   "trim_template": sha256(simulator.TRIM_TEMPLATE_PATH)},
        "volumes": {"workspace": ws_vol, "config": cfg_vol}, "start_commit": base,
        "started": datetime.now(timezone.utc).isoformat(timespec="seconds"), "changes": {},
    }
    meta_path.write_text(json.dumps(meta, indent=1))

    costs: list[float] = []
    ask, touch, trim = deps.ask, deps.touch, deps.trim
    if ask is None:
        ask, touch, trim = _role_calls(args.owner_model, costs)
    # Each change forks from the final snapshot, so no earlier change happened: the owner holds the start's narrative
    # and items and this change's own, never another change's.
    owner = simulator.Owner(oracle=oracle, brief=brief, policy=args.policy, replicate=args.replicate, ask=ask,
                            touch=touch, trim=trim, model=owner_model, owner_items=owner_items, only_change=True)
    session = executor.ContainerSession(image=args.image, workspace_volume=ws_vol, config_volume=cfg_vol,
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
        clean_target(deps, args.image, ws_vol)  # disk is short; a cold build takes about 40 seconds
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
