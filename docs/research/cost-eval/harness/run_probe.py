"""Run the seed's probe request on a disposable fork of a trajectory's checkpoint.

    ../plumbing/with-token.sh python3.12 run_probe.py --id s2-bare-1 --at 3 --fork 1

The fork gets a new workspace holding a clean checkout of the trajectory's commit after change `at` (files git
ignores, such as a virtualenv, aren't carried over, the same for every arm and age), a fresh configuration volume,
and the owner as it stood after that change. The probe runs as one change, with the arm's usual first prompt, under
the trajectory's model, effort, policy, and owner model. Records go to ../runs/<id>-probe<at>-<fork>/; the original
trajectory is untouched.

The owner's draws are keyed on --replicate, by default <the trajectory's replicate>-probe-<at>-fork-<fork>, so fork n
at one checkpoint shares draws across every arm in a replicate, while repeated forks, and forks at other checkpoints,
don't. A trajectory that recorded no replicate can be probed only with --replicate. One that recorded no owner model is
probed at the central values, and the fork's trajectory.json says so ("owner_model_assumed"). The fork records the
current hashes of the inputs that could have changed since the trajectory ran ("..._now") beside the trajectory's.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import executor, simulator, trajectory  # noqa: E402
from run_trajectory import CLAUDE_CODE, IMAGE, ROLES_VOLUME, sha256  # noqa: E402


def probe_replicate(base: dict, at: int, fork: int, given: str | None) -> str:
    """The fork's replicate: as given, or the base trajectory's with the checkpoint and fork number added."""
    if given:
        return given
    if not base.get("replicate"):
        raise ValueError("the trajectory recorded no replicate; give one with --replicate")
    return f"{base['replicate']}-probe-{at}-fork-{fork}"


def probe_only_change(base: dict) -> bool:
    """Whether the base run's owner held the start and its own change only (a fork), which the probe's owner keeps."""
    return base.get("owner_scope") == simulator.FORK_SCOPE


def probe_owner_model(base: dict) -> tuple[simulator.OwnerModel, bool]:
    """The base trajectory's owner model, and whether it had to be assumed (a trajectory that predates one)."""
    if "owner_model_config" not in base:
        return simulator.OwnerModel(), True
    return simulator.OwnerModel.from_config(base["owner_model_config"]), False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True, help="the trajectory to fork")
    ap.add_argument("--at", type=int, required=True, help="fork from the checkpoint after this change")
    ap.add_argument("--fork", type=int, required=True, help="the fork's number, for repeated runs from one checkpoint")
    ap.add_argument("--lid-repo", type=Path, default=None)
    ap.add_argument("--replicate", default=None, help="the seed the owner's draws are keyed on (default: the "
                                                      "trajectory's replicate, then -probe-<at>-fork-<fork>)")
    args = ap.parse_args(argv)
    base_dir = HERE.parent / "runs" / args.id
    base = json.loads((base_dir / "trajectory.json").read_text())
    try:
        replicate = probe_replicate(base, args.at, args.fork, args.replicate)
    except ValueError as e:
        print(f"{args.id}: {e}")
        return 2
    commit = base["changes"][str(args.at)]["commit"]
    state_path = base_dir / f"owner-state-{args.at:02d}.json"
    if not state_path.exists():
        print(f"no saved owner state after change {args.at}")
        return 2
    fid = f"{args.id}-probe{args.at:02d}-{args.fork}"
    out = HERE.parent / "runs" / fid
    if (out / "trajectory.json").exists():
        print(f"{fid} already exists")
        return 2
    out.mkdir(parents=True)
    seed_dir = HERE.parent / "seeds" / base["seed"]
    script_path = seed_dir / "hidden" / "change-script.md"
    arm = trajectory.load_arm(base["arm"])
    ws_vol, cfg_vol = f"ce-{fid}-ws", f"ce-{fid}-cfg"

    subprocess.run(["docker", "run", "--rm", "-v", f"{base['volumes']['workspace']}:/src:ro", "-v", f"{ws_vol}:/work", IMAGE,
                    "sh", "-c", f"git clone -q /src /work && cd /work && git checkout -q -B main {commit} && "
                    f"git config user.name '{trajectory.GIT_IDENTITY[0]}' && git config user.email '{trajectory.GIT_IDENTITY[1]}'"],
                   check=True, capture_output=True)
    if arm.lid_release:
        repo = args.lid_repo or Path(subprocess.run(["git", "-C", str(HERE), "rev-parse", "--show-toplevel"],
                                                    capture_output=True, text=True, check=True).stdout.strip())
        trajectory.install_lid(IMAGE, cfg_vol, repo, arm.lid_release)

    oracle = simulator.parse_oracle((seed_dir / "hidden" / "oracle.md").read_text(encoding="utf-8"))
    items_path = seed_dir / "hidden" / "owner-items.json"
    owner_items = simulator.load_owner_items(items_path, oracle)
    owner_model, assumed = probe_owner_model(base)
    if assumed:
        print(f"{args.id} recorded no owner model (it predates one); the probe uses the central values")
    brief = (seed_dir / "brief.md").read_text(encoding="utf-8")
    change = simulator.parse_probe(script_path.read_text(encoding="utf-8"), args.at)
    role = executor.RoleSession(image=IMAGE, config_volume=ROLES_VOLUME, model=base["owner_model"],
                                claude_code_version=CLAUDE_CODE, effort="medium")
    costs: list[float] = []

    def call(schema: str):
        def run(prompt: str) -> tuple[dict, float]:
            r = executor.run_role(role, prompt, json_schema=schema)
            cost = r.usage.reported_cost_usd or 0.0
            costs.append(cost)
            return r.structured, cost
        return run

    owner = simulator.Owner(oracle=oracle, brief=brief, policy=base["policy"], replicate=replicate,
                            ask=call(simulator.schema_json()), touch=call(simulator.touch_schema_json()),
                            trim=call(simulator.trim_schema_json()), check=call(simulator.completion_schema_json()),
                            model=owner_model, owner_items=owner_items, only_change=probe_only_change(base))
    trajectory.restore_owner_state(owner, json.loads(state_path.read_text()))
    session = executor.ContainerSession(image=IMAGE, workspace_volume=ws_vol, config_volume=cfg_vol, model=base["model"],
                                        claude_code_version=CLAUDE_CODE, expected_plugins=frozenset(arm.plugins),
                                        effort=base["effort"], plugin_dirs=arm.plugin_dirs)
    meta = {"id": fid, "fork_of": args.id, "at": args.at, "commit": commit, "arm": arm.name, "seed": base["seed"],
            "model": base["model"], "effort": base["effort"], "policy": base["policy"], "owner_model": base["owner_model"],
            "replicate": replicate, "owner_model_config": asdict(owner_model), "owner_model_assumed": assumed,
            "lid_release": arm.lid_release, "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            **({"owner_scope": base["owner_scope"]} if "owner_scope" in base else {}),
            "hashes": {**base["hashes"], "change_script_now": sha256(script_path), "owner_items_now": sha256(items_path),
                       "oracle_now": sha256(seed_dir / "hidden" / "oracle.md"),
                       "simulator_template_now": sha256(simulator.TEMPLATE_PATH),
                       "touch_template_now": sha256(simulator.TOUCH_TEMPLATE_PATH),
                       "trim_template_now": sha256(simulator.TRIM_TEMPLATE_PATH)},
            "volumes": {"workspace": ws_vol, "config": cfg_vol}, "changes": {}}

    def turn(prompt, stream_path, *, resume=None, permission_mode="bypassPermissions"):
        return executor.run_turn(session, prompt, stream_path, resume=resume, permission_mode=permission_mode)

    res = trajectory.run_change(arm=arm, change=change, owner=owner, turn=turn,
                                workspace=trajectory.DockerWorkspace(IMAGE, ws_vol), out_dir=out / "change-probe",
                                round_cap=base.get("round_cap", trajectory.ROUND_CAP))
    agent_cost = sum((t["usage"] or {}).get("reported_cost_usd") or 0 for t in res.turns)
    meta["changes"]["probe"] = {"rounds": res.rounds, "finished": res.finished, "capped": res.capped, "error": res.error,
                                "commit": res.commit, "agent_cost_usd": round(agent_cost, 4),
                                "owner_cost_usd": round(sum(costs), 4)}
    (out / "trajectory.json").write_text(json.dumps(meta, indent=1))
    print(f"{fid}: rounds {res.rounds}, finished {res.finished}, agent ${agent_cost:.2f}, error {res.error}")
    return 0 if not res.error else 1


if __name__ == "__main__":
    sys.exit(main())
