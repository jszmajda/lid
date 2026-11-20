"""Run one arm's trajectory through a seed's changes, or continue one that stopped.

    ../plumbing/with-token.sh python3.12 run_trajectory.py --arm bare --id t-bare-1 --changes 0,1,2 \\
        --replicate r1 --owner-model-config '{"scope": "stop"}'

Records go to ../runs/<id>/, which git ignores: they hold the seed's hidden oracle in the owner's prompts, so they
stay private until the runs that use the seed are finished. The arm's workspace and configuration live in Docker
volumes named after the trajectory (ce-<id>-ws and ce-<id>-cfg); its commits are the checkpoints.

--replicate is required: the seed every owner draw is keyed on. Give the same value to every trajectory being
compared (each arm and policy in a replicate, and a redirect's paired runs); draws are never keyed on the trajectory
itself, so a forgotten value can't quietly make one arm's draws independent of the others'. --owner-model-config picks the
owner's attention and recall constants: a preset ("central" or "pilot"), a JSON object of settings (with an optional
"preset"), or a path to a JSON file holding one. Both are recorded in trajectory.json. The seed's
hidden/owner-items.json must give every askable item a tier and recall line.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from costeval import executor, reference, simulator, trajectory  # noqa: E402

IMAGE = "lid-cost-eval-executor:2.1.323"
CLAUDE_CODE = "2.1.323"
ROLES_VOLUME = "ce-roles-cfg"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def owner_model_from_arg(value: str | None) -> simulator.OwnerModel:
    """--owner-model-config: nothing (the design's central values), a preset name, a JSON object, or a JSON file."""
    if not value:
        return simulator.OwnerModel()
    if value in simulator.OWNER_MODEL_PRESETS:
        return simulator.OwnerModel.from_config({"preset": value})
    text = value if value.lstrip().startswith("{") else Path(value).read_text(encoding="utf-8")
    config = json.loads(text)
    if not isinstance(config, dict):
        raise ValueError("the owner model config must be a JSON object")
    return simulator.OwnerModel.from_config(config)


EMPTY_OWNER_STATE = {"record": [], "requests": [], "seen": {}, "disclosed": []}


def change_done(meta: dict, n: int) -> bool:
    """Whether change n has run to its end without an error (one that stopped runs again)."""
    c = (meta.get("changes") or {}).get(str(n)) or {}
    return c.get("finished") is not None and not c.get("error")


def fork_start(runs: Path, fork_of: str, first: int) -> tuple[str, dict, str]:
    """Where a trajectory forked from another starts: that trajectory's commit and owner state after change first - 1,
    and its workspace volume (an instrument gate's stale fork S_C starts from R+ after C - 1)."""
    src = runs / fork_of
    meta = json.loads((src / "trajectory.json").read_text())
    commit = (meta["changes"].get(str(first - 1)) or {}).get("commit")
    state = src / f"owner-state-{first - 1:02d}.json"
    if not commit or not state.exists():
        raise RuntimeError(f"{fork_of} has no snapshot and owner state after change {first - 1}")
    return commit, json.loads(state.read_text()), meta["volumes"]["workspace"]


def prepare_owner(owner: simulator.Owner, out: Path, n: int) -> None:
    """Set the owner as it stood before change n: empty for the first build, so a retried first build carries nothing
    from a failed attempt; otherwise as saved after change n - 1. A later change with no saved state can't start."""
    if n == 0:
        trajectory.restore_owner_state(owner, EMPTY_OWNER_STATE)
        return
    prev = out / f"owner-state-{n - 1:02d}.json"
    if not prev.exists():
        raise RuntimeError(f"no {prev.name}: change {n} needs the owner as it stood after change {n - 1}")
    trajectory.restore_owner_state(owner, json.loads(prev.read_text()))


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
                         "--seed", seed, "--probes", ",".join(ids), "--out-name", name, "--workers", "1"]).returncode
    path = HERE.parent / "runs" / trajectory / "grading" / name / "verdicts.json"
    if rc != 0 or not path.exists():
        return "inconclusive"
    verdicts = [v.get("verdict") for v in json.loads(path.read_text()).get("probes", {}).values()]
    if "not met" in verdicts:
        return "fired"
    if len(verdicts) < len(ids) or "couldn't exercise" in verdicts:
        return "inconclusive"
    return "passed"


def build_parser() -> argparse.ArgumentParser:
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
    ap.add_argument("--replicate", required=True,
                    help="the seed the owner's draws are keyed on, the same for every trajectory being compared")
    ap.add_argument("--owner-model-config", default=None,
                    help="the owner's attention and recall constants: a preset (central, pilot), a JSON object, or a JSON file")
    ap.add_argument("--window", choices=sorted(executor.WINDOWS), default="1m",
                    help="the agent's context window: 1m (the model's own) or 200k (CLAUDE_CODE_DISABLE_1M_CONTEXT=1)")
    ap.add_argument("--stale-of", type=int, default=None,
                    help="ref-stale only: the course change C this stale fork S_C declines (seed's reference-builds.json)")
    ap.add_argument("--fork-of", default=None,
                    help="start from this trajectory's snapshot and owner state just before the first change listed")
    ap.add_argument("--isolate", action="store_true",
                    help="block GitHub's hosts and deny web search and fetch, for a seed whose repository is public")
    return ap


def isolation_from_args(args) -> executor.Isolation:
    """Isolated (GitHub's hosts blocked, web search and fetch denied) with --isolate, and always for a growth seed
    (a name ending -growth), whose rules the public repository must not give away."""
    if args.isolate or str(getattr(args, "seed", "")).endswith("-growth"):
        return executor.Isolation.for_public_seed(window=args.window)
    return executor.Isolation(window=args.window)


def main(argv=None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)

    if not all(c.isalnum() or c == "-" for c in args.id):
        ap.error("--id may hold only letters, digits and dashes")
    try:
        owner_model = owner_model_from_arg(args.owner_model_config)
    except (ValueError, OSError) as e:
        ap.error(f"--owner-model-config: {e}")
    replicate = args.replicate
    seed_dir = HERE.parent / "seeds" / args.seed
    oracle_path, script_path, brief_path = seed_dir / "hidden" / "oracle.md", seed_dir / "hidden" / "change-script.md", seed_dir / "brief.md"
    items_path = seed_dir / "hidden" / "owner-items.json"
    out = HERE.parent / "runs" / args.id
    arm = trajectory.load_arm(args.arm)
    ws_vol, cfg_vol = f"ce-{args.id}-ws", f"ce-{args.id}-cfg"
    meta_path, state_path = out / "trajectory.json", out / "owner-state.json"

    oracle = simulator.parse_oracle(oracle_path.read_text(encoding="utf-8"))
    script = simulator.parse_change_script(script_path.read_text(encoding="utf-8"))
    brief = brief_path.read_text(encoding="utf-8")
    if (args.stale_of is not None) != (arm.reference == "stale"):
        ap.error("--stale-of goes with the ref-stale arm, and it needs one")
    spec = reference.load_spec(seed_dir) if arm.reference else None
    # every askable item needs one, with no default; a reference owner states every row, so needs none
    owner_items = {} if arm.reference else simulator.load_owner_items(items_path, oracle)
    out.mkdir(parents=True, exist_ok=True)
    meta = {
        "id": args.id, "arm": arm.name, "seed": args.seed, "model": args.model, "effort": args.effort,
        "claude_code": CLAUDE_CODE, "image": IMAGE, "policy": args.policy, "owner_model": args.owner_model,
        "replicate": replicate, "owner_model_config": asdict(owner_model), "isolation": isolation_from_args(args).record(),
        "lid_release": arm.lid_release, "reference": arm.reference, "stale_of": args.stale_of, "fork_of": args.fork_of,
        "round_cap": args.round_cap,
        "neutral_sentence": trajectory.NEUTRAL_SENTENCE,
        "hashes": {"brief": sha256(brief_path), "oracle": sha256(oracle_path), "change_script": sha256(script_path),
                   "owner_items": sha256(items_path), "simulator_template": sha256(simulator.TEMPLATE_PATH),
                   "touch_template": sha256(simulator.TOUCH_TEMPLATE_PATH), "trim_template": sha256(simulator.TRIM_TEMPLATE_PATH)},
        "volumes": {"workspace": ws_vol, "config": cfg_vol},
    }
    workspace = trajectory.DockerWorkspace(IMAGE, ws_vol)
    if meta_path.exists():
        old = json.loads(meta_path.read_text())
        for k in ("arm", "seed", "model", "effort", "policy", "replicate", "owner_model_config", "isolation", "hashes"):
            if old.get(k) != meta.get(k):
                ap.error(f"trajectory {args.id} exists with a different {k}: {old.get(k)!r}")
        meta = old
    else:
        meta["started"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if args.fork_of:  # a copy of another trajectory's snapshot, its owner as it stood there
            first = min(int(x) for x in args.changes.split(","))
            try:
                commit, state, src_vol = fork_start(HERE.parent / "runs", args.fork_of, first)
            except RuntimeError as e:
                ap.error(str(e))
            p = subprocess.run(trajectory.clone_command(src_vol, ws_vol, commit, IMAGE), capture_output=True, text=True)
            if p.returncode != 0:
                raise RuntimeError(f"copying {args.fork_of}'s snapshot failed: {(p.stderr or '')[-500:]}")
            (out / f"owner-state-{first - 1:02d}.json").write_text(json.dumps(state, indent=1))
            meta["start_commit"], meta["from_change"] = commit, first - 1
        else:
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
                                        effort=args.effort, plugin_dirs=arm.plugin_dirs, timeout_s=args.turn_timeout,
                                        isolation=isolation_from_args(args))
    role = executor.RoleSession(image=IMAGE, config_volume=ROLES_VOLUME, model=args.owner_model,
                                claude_code_version=CLAUDE_CODE, effort="medium")
    owner_costs: list[float] = []

    def call(schema: str):
        """One owner role call: its structured output and cost, which the owner records with the call."""
        def run(prompt: str) -> tuple[dict, float]:
            r = executor.run_role(role, prompt, json_schema=schema)
            cost = r.usage.reported_cost_usd or 0.0
            owner_costs.append(cost)
            return r.structured, cost
        return run

    # a reference run (the instrument gate's, never a study arm): its owner holds the spec's rows and states them all
    view = reference.owner_view(oracle, spec, args.stale_of) if arm.reference else oracle
    owner = simulator.Owner(oracle=view, brief=brief, policy=args.policy, replicate=meta["replicate"], full_oracle=bool(arm.reference),
                            ask=call(simulator.schema_json()), touch=call(simulator.touch_schema_json()),
                            trim=call(simulator.trim_schema_json()), check=call(simulator.completion_schema_json()),
                            model=simulator.OwnerModel.from_config(meta["owner_model_config"]), owner_items=owner_items)

    def turn(prompt, stream_path, *, resume=None, permission_mode="bypassPermissions"):
        return executor.run_turn(session, prompt, stream_path, resume=resume, permission_mode=permission_mode)

    for n in (int(x) for x in args.changes.split(",")):
        if change_done(meta, n):
            print(f"change {n}: already run, skipping")
            continue
        try:
            # Start each change from the owner as it stood before it, so a failed attempt at this change leaves
            # nothing behind in the owner's record.
            prepare_owner(owner, out, n)
        except RuntimeError as e:
            print(f"change {n}: {e}", flush=True)
            return 1
        change = simulator.first_build(brief) if n == 0 else script[n]
        rules = None
        if arm.reference:
            if n > 0:
                what, change = reference.plan_change(spec, script, n, args.stale_of)
                if what == "skip":  # S_C declines its course change: no session, the snapshot unchanged
                    meta["changes"][str(n)] = {"title": script[n].title, "declined": "skip", "finished": True,
                                               "error": None, "commit": workspace.head()}
                    meta_path.write_text(json.dumps(meta, indent=1))
                    (out / f"owner-state-{n:02d}.json").write_text(json.dumps(trajectory.owner_state(owner), indent=1))
                    print(f"change {n}: declined, so no session", flush=True)
                    continue
            rules = reference.statement(spec, n, args.stale_of)
        if change.request is None and change.symptom is not None and not arm.reference:  # a reference always reports
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
        symptom = ({"symptom": "delivered (reference)" if arm.reference else "fired"}
                   if change.request is None and change.symptom is not None else {})
        start = time.monotonic()
        before = len(owner_costs)
        res = trajectory.run_change(arm=arm, change=change, owner=owner, turn=turn, workspace=workspace,
                                    out_dir=out / f"change-{n:02d}", round_cap=args.round_cap, rules=rules)
        agent_cost = sum((t["usage"] or {}).get("reported_cost_usd") or 0 for t in res.turns)
        meta["changes"][str(n)] = {"title": res.title, "rounds": res.rounds, "finished": res.finished, "capped": res.capped,
                                   "error": res.error, "commit": res.commit, "redirect": res.redirect,
                                   "agent_cost_usd": round(agent_cost, 4), "owner_cost_usd": round(sum(owner_costs[before:]), 4),
                                   "minutes": round((time.monotonic() - start) / 60, 1), **symptom}
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
