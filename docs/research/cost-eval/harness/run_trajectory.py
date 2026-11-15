"""Run one arm's trajectory through a seed's changes, or continue one that stopped.

    ../plumbing/with-token.sh python3.12 run_trajectory.py --arm bare --id t-bare-1 --changes 0,1,2

Records go to ../runs/<id>/, which git ignores: they hold the seed's hidden oracle in the owner's prompts, so they
stay private until the runs that use the seed are finished. The arm's workspace and configuration live in Docker
volumes named after the trajectory (ce-<id>-ws and ce-<id>-cfg); its commits are the checkpoints.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import executor, simulator, trajectory  # noqa: E402

IMAGE = "lid-cost-eval-executor:2.1.323"
CLAUDE_CODE = "2.1.323"
ROLES_VOLUME = "ce-roles-cfg"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def diagnose(trajectory: str, n: int, change: simulator.Change, seed: str, name: str | None = None) -> str:
    """Run a symptom change's diagnostic, the probes of the items it introduces, against the incoming checkpoint.
    Returns "fired" (a probe not met), "passed", or "inconclusive" (it couldn't be run or judged)."""
    from costeval import grading
    probes = grading.parse_probes((HERE.parent / "seeds" / seed / "hidden" / "probes.md").read_text(encoding="utf-8")).probes
    ids = [p.id for p in probes if p.item in change.introduces]
    if not ids:
        return "inconclusive"
    name = name or f"diagnostic-{n:02d}"
    rc = subprocess.run([sys.executable, str(HERE / "grade_checkpoint.py"), "--id", trajectory, "--change", str(n - 1),
                         "--probes", ",".join(ids), "--out-name", name, "--workers", "1"]).returncode
    path = HERE.parent / "runs" / trajectory / "grading" / name / "verdicts.json"
    if rc != 0 or not path.exists():
        return "inconclusive"
    verdicts = [v.get("verdict") for v in json.loads(path.read_text()).get("probes", {}).values()]
    if "not met" in verdicts:
        return "fired"
    if len(verdicts) < len(ids) or "couldn't exercise" in verdicts:
        return "inconclusive"
    return "passed"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--id", required=True, help="trajectory ID: letters, digits and dashes")
    ap.add_argument("--seed", default="benchtime")
    ap.add_argument("--changes", default="0,1,2", help="comma-separated change numbers, 0 being the first build")
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--effort", default="medium")
    ap.add_argument("--policy", default="diligent", choices=simulator.POLICIES)
    ap.add_argument("--owner-model", default="claude-sonnet-5-5")
    ap.add_argument("--round-cap", type=int, default=trajectory.ROUND_CAP)
    ap.add_argument("--turn-timeout", type=int, default=3600)
    ap.add_argument("--lid-repo", type=Path, default=None, help="a LID checkout with release tags (default: this one)")
    args = ap.parse_args(argv)

    if not all(c.isalnum() or c == "-" for c in args.id):
        ap.error("--id may hold only letters, digits and dashes")
    seed_dir = HERE.parent / "seeds" / args.seed
    oracle_path, script_path, brief_path = seed_dir / "hidden" / "oracle.md", seed_dir / "hidden" / "change-script.md", seed_dir / "brief.md"
    out = HERE.parent / "runs" / args.id
    out.mkdir(parents=True, exist_ok=True)
    arm = trajectory.load_arm(args.arm)
    ws_vol, cfg_vol = f"ce-{args.id}-ws", f"ce-{args.id}-cfg"
    meta_path, state_path = out / "trajectory.json", out / "owner-state.json"

    oracle = simulator.parse_oracle(oracle_path.read_text(encoding="utf-8"))
    script = simulator.parse_change_script(script_path.read_text(encoding="utf-8"))
    brief = brief_path.read_text(encoding="utf-8")
    meta = {
        "id": args.id, "arm": arm.name, "seed": args.seed, "model": args.model, "effort": args.effort,
        "claude_code": CLAUDE_CODE, "image": IMAGE, "policy": args.policy, "owner_model": args.owner_model,
        "lid_release": arm.lid_release, "round_cap": args.round_cap, "neutral_sentence": trajectory.NEUTRAL_SENTENCE,
        "hashes": {"brief": sha256(brief_path), "oracle": sha256(oracle_path), "change_script": sha256(script_path),
                   "simulator_template": sha256(simulator.TEMPLATE_PATH), "trim_template": sha256(simulator.TRIM_TEMPLATE_PATH)},
        "volumes": {"workspace": ws_vol, "config": cfg_vol},
    }
    workspace = trajectory.DockerWorkspace(IMAGE, ws_vol)
    if meta_path.exists():
        old = json.loads(meta_path.read_text())
        for k in ("arm", "seed", "model", "effort", "policy", "hashes"):
            if old.get(k) != meta.get(k):
                ap.error(f"trajectory {args.id} exists with a different {k}: {old.get(k)!r}")
        meta = old
    else:
        meta["started"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        files = {dest: (trajectory.ARMS_DIR / src).read_text(encoding="utf-8") for dest, src in arm.workspace_files.items()}
        meta["start_commit"] = workspace.init(files)
        if arm.lid_release:
            repo = args.lid_repo or Path(subprocess.run(["git", "-C", str(HERE), "rev-parse", "--show-toplevel"],
                                                        capture_output=True, text=True, check=True).stdout.strip())
            trajectory.install_lid(IMAGE, cfg_vol, repo, arm.lid_release)
        meta["changes"] = {}
        meta_path.write_text(json.dumps(meta, indent=1))

    session = executor.ContainerSession(image=IMAGE, workspace_volume=ws_vol, config_volume=cfg_vol, model=args.model,
                                        claude_code_version=CLAUDE_CODE, expected_plugins=frozenset(arm.plugins),
                                        effort=args.effort, plugin_dirs=arm.plugin_dirs, timeout_s=args.turn_timeout)
    role = executor.RoleSession(image=IMAGE, config_volume=ROLES_VOLUME, model=args.owner_model,
                                claude_code_version=CLAUDE_CODE, effort="medium")
    owner_costs: list[float] = []

    def ask(prompt: str) -> dict:
        r = executor.run_role(role, prompt, json_schema=simulator.schema_json())
        owner_costs.append(r.usage.reported_cost_usd or 0.0)
        return r.structured

    def trim(prompt: str) -> dict:
        r = executor.run_role(role, prompt, json_schema=simulator.trim_schema_json())
        owner_costs.append(r.usage.reported_cost_usd or 0.0)
        return r.structured

    owner = simulator.Owner(oracle=oracle, brief=brief, policy=args.policy, seed=args.id, ask=ask, trim=trim)
    if state_path.exists():
        trajectory.restore_owner_state(owner, json.loads(state_path.read_text()))

    def turn(prompt, stream_path, *, resume=None, permission_mode="bypassPermissions"):
        return executor.run_turn(session, prompt, stream_path, resume=resume, permission_mode=permission_mode)

    for n in (int(x) for x in args.changes.split(",")):
        if str(n) in meta["changes"] and meta["changes"][str(n)].get("finished") is not None and not meta["changes"][str(n)].get("error"):
            print(f"change {n}: already run, skipping")
            continue
        prev_state = out / f"owner-state-{n - 1:02d}.json"
        if n > 0 and prev_state.exists():
            # Start each change from the owner as it stood after the previous one, so a failed attempt at this
            # change leaves nothing behind in the owner's record.
            trajectory.restore_owner_state(owner, json.loads(prev_state.read_text()))
        change = simulator.first_build(brief) if n == 0 else script[n]
        if change.request is None and change.symptom is not None:
            fired = diagnose(args.id, n, change, args.seed)
            if fired == "inconclusive":
                # Grading can fail for its own reasons (a lost credential, say); try once more before deciding.
                fired = diagnose(args.id, n, change, args.seed, name=f"diagnostic-{n:02d}-retry")
            if fired != "fired":
                # Passed, or couldn't be judged: no symptom report and no change. An inconclusive diagnostic is
                # recorded as such and checked by hand before the trajectory counts.
                meta["changes"][str(n)] = {"title": change.title, "symptom": f"not fired: diagnostic {fired}",
                                           "finished": True, "error": None, "commit": workspace.head()}
                meta_path.write_text(json.dumps(meta, indent=1))
                (out / f"owner-state-{n:02d}.json").write_text(json.dumps(trajectory.owner_state(owner), indent=1))
                print(f"change {n}: diagnostic {fired}, so no symptom report and no change", flush=True)
                continue
        start = time.monotonic()
        before = len(owner_costs)
        res = trajectory.run_change(arm=arm, change=change, owner=owner, turn=turn, workspace=workspace,
                                    out_dir=out / f"change-{n:02d}", round_cap=args.round_cap)
        agent_cost = sum((t["usage"] or {}).get("reported_cost_usd") or 0 for t in res.turns)
        meta["changes"][str(n)] = {"title": res.title, "rounds": res.rounds, "finished": res.finished, "capped": res.capped,
                                   "error": res.error, "commit": res.commit, "redirect": res.redirect,
                                   "agent_cost_usd": round(agent_cost, 4), "owner_cost_usd": round(sum(owner_costs[before:]), 4),
                                   "minutes": round((time.monotonic() - start) / 60, 1)}
        meta_path.write_text(json.dumps(meta, indent=1))
        state_path.write_text(json.dumps(trajectory.owner_state(owner), indent=1))
        (out / f"owner-state-{n:02d}.json").write_text(state_path.read_text())  # for forks from this checkpoint
        print(f"change {n}: rounds {res.rounds}, finished {res.finished}, capped {res.capped}, agent ${agent_cost:.2f}, "
              f"error {res.error}", flush=True)
        if res.error:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
