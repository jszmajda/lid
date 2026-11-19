"""Run one fork for the growth test (design.md, "The growth test"), one change long, discarded once graded as redirect
twins and probe forks are. Two kinds:

- a course fork (--kind course --course C) runs course change C from the arm's snapshot just before it: graded for
  the flip checks, and audited for stale intent, it samples how the change is handled;
- a reliance fork (--kind reliance --reliance R) runs reliance change R from the trajectory's own snapshot just before
  it, the changes in between included: graded for regression against every rule R relies on, it samples the
  consequence, given the codebase the trajectory actually has.

    ../plumbing/with-token.sh python3.12 run_course_forks.py --id g-bare-1 --kind course --course 13 --fork 1
    python3.12 run_course_forks.py --id g-bare-1 --kind reliance --reliance 16 --fork 1 --discard     # after grading

Records go under the trajectory, ../runs/<id>/course-forks/cNN-course-K/ or rNN-reliance-K/: trajectory.json (its kind,
the change, its commit and costs), the change's turns and owner records, and the owner's state after it. The owner
starts as it stood before the change, and the fork draws on its own replicate, <the trajectory's>-<kind>NN-fork-K, so
three forks are three draws. A fork already recorded is left alone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import executor, growth, simulator, trajectory  # noqa: E402
from run_trajectory import CLAUDE_CODE, IMAGE, ROLES_VOLUME  # noqa: E402


@dataclass
class Deps:
    """What a fork reaches outside itself; tests replace each part."""
    docker: Callable = subprocess.run
    turn_for: Callable | None = None  # session -> turn function; default: executor.run_turn in that session
    workspace_for: Callable | None = None  # (image, volume) -> workspace; default: trajectory.DockerWorkspace
    ask: Callable | None = None  # the owner's model calls; default: role sessions
    touch: Callable | None = None
    trim: Callable | None = None
    check: Callable | None = None
    install_lid: Callable = trajectory.install_lid


def _role_calls(owner_model: str, costs: list[float]):
    role = executor.RoleSession(image=IMAGE, config_volume=ROLES_VOLUME, model=owner_model,
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
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", required=True, help="the growth trajectory")
    ap.add_argument("--kind", choices=("course", "reliance"), required=True)
    ap.add_argument("--course", type=int, help="the course change (a course fork)")
    ap.add_argument("--reliance", type=int, help="the reliance change (a reliance fork)")
    ap.add_argument("--fork", type=int, required=True, help="the fork's number (1-3)")
    ap.add_argument("--runs", type=Path, default=HERE.parent / "runs")
    ap.add_argument("--seed-dir", type=Path, help="default: ../seeds/<the trajectory's seed>")
    ap.add_argument("--lid-repo", type=Path, default=None)
    ap.add_argument("--discard", action="store_true", help="only remove the fork's volumes (after grading)")
    args = ap.parse_args(argv)
    n = args.course if args.kind == "course" else args.reliance
    if n is None:
        ap.error(f"a {args.kind} fork needs --{args.kind}")
    tag = f"{args.kind}{n:02d}"
    ws_vol, cfg_vol = f"ce-{args.id}-{tag}-{args.fork}-ws", f"ce-{args.id}-{tag}-{args.fork}-cfg"
    if args.discard:
        deps.docker(["docker", "volume", "rm", "-f", ws_vol, cfg_vol], capture_output=True, text=True)
        return 0
    base_dir = args.runs / args.id
    base = json.loads((base_dir / "trajectory.json").read_text())
    seed_dir = args.seed_dir or HERE.parent / "seeds" / base["seed"]
    script_path = seed_dir / "hidden" / "change-script.md"
    script = simulator.parse_change_script(script_path.read_text(encoding="utf-8"))
    if args.kind == "course":
        if script.get(n) is None or script[n].course_change is None:
            print(f"change {n} isn't a course change")
            return 2
        courses = [n]
        reliance = [r for c, r in growth.course_pairs(script) if c == n]
    else:
        courses = growth.reliance_changes(script).get(n)
        if not courses:
            print(f"change {n} isn't a reliance change")
            return 2
        reliance = [n]
    start = base["changes"].get(str(n - 1), {}).get("commit") if n > 1 else base.get("start_commit")
    state_path = base_dir / f"owner-state-{n - 1:02d}.json"
    if not start or not state_path.exists():
        print(f"{args.id} has no snapshot or owner state after change {n - 1}")
        return 2
    name = f"c{n:02d}-course-{args.fork}" if args.kind == "course" else f"r{n:02d}-reliance-{args.fork}"
    fid = f"{args.id}/course-forks/{name}"
    out = args.runs / fid
    meta_path = out / "trajectory.json"
    if meta_path.exists():
        if str(n) in json.loads(meta_path.read_text()).get("changes", {}):
            print(f"{fid} already recorded")
            return 0
        shutil.rmtree(out)  # a fork that stopped partway runs again from its start
    out.mkdir(parents=True)

    arm = trajectory.load_arm(base["arm"])
    p = deps.docker(["docker", "run", "--rm", "-v", f"{base['volumes']['workspace']}:/src:ro", "-v", f"{ws_vol}:/work", IMAGE,
                     "sh", "-c", f"find /work -mindepth 1 -delete; git clone -q /src /work && cd /work && "
                     f"git checkout -q -B main {start} && git config user.name '{trajectory.GIT_IDENTITY[0]}' && "
                     f"git config user.email '{trajectory.GIT_IDENTITY[1]}'"], capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"copying the snapshot failed: {(p.stderr or '')[-500:]}")
    if arm.lid_release:
        repo = args.lid_repo or Path(subprocess.run(["git", "-C", str(HERE), "rev-parse", "--show-toplevel"],
                                                    capture_output=True, text=True, check=True).stdout.strip())
        deps.install_lid(IMAGE, cfg_vol, repo, arm.lid_release)

    oracle = simulator.parse_oracle((seed_dir / "hidden" / "oracle.md").read_text(encoding="utf-8"))
    owner_items = simulator.load_owner_items(seed_dir / "hidden" / "owner-items.json", oracle)
    owner_model = (simulator.OwnerModel.from_config(base["owner_model_config"]) if base.get("owner_model_config")
                   else simulator.OwnerModel())
    costs: list[float] = []
    ask, touch, trim, check = deps.ask, deps.touch, deps.trim, deps.check
    if ask is None:
        ask, touch, trim, check = _role_calls(base["owner_model"], costs)
    replicate = f"{base['replicate']}-{tag}-fork-{args.fork}"
    owner = simulator.Owner(oracle=oracle, brief=(seed_dir / "brief.md").read_text(encoding="utf-8"), policy=base["policy"],
                            replicate=replicate, ask=ask, touch=touch, trim=trim, model=owner_model,
                            owner_items=owner_items, check=check)
    trajectory.restore_owner_state(owner, json.loads(state_path.read_text()))
    isolation = executor.Isolation(window=(base.get("isolation") or {}).get("window", "1m"))
    session = executor.ContainerSession(image=IMAGE, workspace_volume=ws_vol, config_volume=cfg_vol, model=base["model"],
                                        claude_code_version=CLAUDE_CODE, expected_plugins=frozenset(arm.plugins),
                                        effort=base["effort"], plugin_dirs=arm.plugin_dirs, isolation=isolation)
    if deps.turn_for is not None:
        turn = deps.turn_for(session)
    else:
        def turn(prompt, stream_path, *, resume=None, permission_mode="bypassPermissions"):
            return executor.run_turn(session, prompt, stream_path, resume=resume, permission_mode=permission_mode)
    workspace = (deps.workspace_for or trajectory.DockerWorkspace)(IMAGE, ws_vol)
    meta = {"id": fid, "kind": args.kind, "fork_of": args.id, "change": n, "courses": courses,
            "course": courses[0] if args.kind == "course" else None, "reliance": reliance[0] if len(reliance) == 1 else reliance,
            "fork": args.fork, "commit": start, "arm": arm.name, "seed": base["seed"], "model": base["model"],
            "effort": base["effort"], "policy": base["policy"], "owner_model": base["owner_model"], "replicate": replicate,
            "owner_model_config": asdict(owner_model), "isolation": isolation.record(), "lid_release": arm.lid_release,
            "round_cap": base.get("round_cap", trajectory.ROUND_CAP),
            "change_script_sha256": hashlib.sha256(script_path.read_bytes()).hexdigest(),
            "started": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "volumes": {"workspace": ws_vol, "config": cfg_vol}, "changes": {}}
    meta_path.write_text(json.dumps(meta, indent=1))
    began = time.monotonic()
    res = trajectory.run_change(arm=arm, change=script[n], owner=owner, turn=turn, workspace=workspace,
                                out_dir=out / f"change-{n:02d}", round_cap=meta["round_cap"])
    agent_cost = sum((t["usage"] or {}).get("reported_cost_usd") or 0 for t in res.turns)
    meta["changes"][str(n)] = {"title": res.title, "rounds": res.rounds, "finished": res.finished, "capped": res.capped,
                               "error": res.error, "commit": res.commit, "agent_cost_usd": round(agent_cost, 4),
                               "owner_cost_usd": round(sum(costs), 4), "minutes": round((time.monotonic() - began) / 60, 1)}
    meta_path.write_text(json.dumps(meta, indent=1))
    (out / f"owner-state-{n:02d}.json").write_text(json.dumps(trajectory.owner_state(owner), indent=1))
    print(f"{fid}: change {n} {'stopped: ' + res.error if res.error else 'done'}")
    return 1 if res.error else 0


if __name__ == "__main__":
    sys.exit(main())
