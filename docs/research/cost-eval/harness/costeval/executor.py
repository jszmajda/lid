"""One turn of an executor session, run with `claude -p` in the executor container.

Every session follows "Sessions and isolation" in the notebook's design.md:
- the container is the permission boundary, so the agent runs with permissions bypassed;
- nothing from the host enters except the arm's two volumes (its workspace at
  /work and its configuration at /cfg) and the subscription token, passed by name;
- memory is off;
- the session's start-up record is checked against the arm's plugin list and the
  pinned model and Claude Code version, and a mismatch makes the session invalid.

This module runs one turn. Starting a session, resuming it with an answer, and
deciding when a change is finished belong to the trajectory layer.
"""

from __future__ import annotations

import json
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from . import usage

TOKEN_ENV = "CLAUDE_CODE_OAUTH_TOKEN"
# Plan mode is how the cheap-discipline arm opens a change; every other turn bypasses permissions.
PERMISSION_MODES = ("bypassPermissions", "plan")


class InitProblem(ValueError):
    """The session's start-up record doesn't match its arm and pins."""


@dataclass(frozen=True)
class ContainerSession:
    image: str
    workspace_volume: str
    config_volume: str
    model: str
    claude_code_version: str
    expected_plugins: frozenset[str] | set[str]
    effort: str = "medium"
    plugin_dirs: tuple[str, ...] | list[str] = ()
    extra_settings: dict = field(default_factory=dict)
    timeout_s: int = 3600


@dataclass(frozen=True)
class TurnRecord:
    stream_path: Path
    container_name: str
    exit_code: int | None
    timed_out: bool
    duration_s: float
    session_id: str | None
    init: dict | None
    init_problem: str | None
    summary: usage.StreamSummary
    final_text: str | None


def _volume(name: str) -> str:
    if not name or name.startswith(("/", ".", "~")) or "/" in name:
        raise ValueError(f"expected a Docker volume name, not a host path: {name!r}")
    return name


def settings_json(s: ContainerSession) -> str:
    return json.dumps({**s.extra_settings, "autoMemoryEnabled": False}, sort_keys=True)


def claude_command(s: ContainerSession, prompt: str, *, container_name: str, resume: str | None = None,
                   permission_mode: str = "bypassPermissions") -> list[str]:
    if permission_mode not in PERMISSION_MODES:
        raise ValueError(f"permission mode must be one of {PERMISSION_MODES}, not {permission_mode!r}")
    cmd = [
        "docker", "run", "--rm", "--name", container_name,
        "-e", TOKEN_ENV,
        "-v", f"{_volume(s.workspace_volume)}:/work",
        "-v", f"{_volume(s.config_volume)}:/cfg",
        "-w", "/work",
        s.image,
        "claude", "-p", prompt,
        "--model", s.model,
        "--effort", s.effort,
        "--permission-mode", permission_mode,
        "--settings", settings_json(s),
        "--output-format", "stream-json", "--verbose",
    ]
    for d in s.plugin_dirs:
        cmd += ["--plugin-dir", d]
    if resume:
        cmd += ["--resume", resume]
    return cmd


def check_init(s: ContainerSession, init: dict) -> None:
    """Raise InitProblem unless the session loaded exactly its arm's plugins under the pinned versions."""
    problems = []
    loaded = {p.get("name") for p in init.get("plugins") or []}
    expected = set(s.expected_plugins)
    if loaded - expected:
        problems.append(f"unexpected plugins: {sorted(loaded - expected)}")
    if expected - loaded:
        problems.append(f"missing plugins: {sorted(expected - loaded)}")
    stray = sorted(k for k in init.get("skills") or [] if ":" in k and k.split(":", 1)[0] not in expected)
    if stray:
        problems.append(f"skills from plugins outside the arm: {stray}")
    if init.get("model") != s.model:
        problems.append(f"model {init.get('model')!r}, pinned {s.model!r}")
    if init.get("claude_code_version") != s.claude_code_version:
        problems.append(f"Claude Code {init.get('claude_code_version')!r}, pinned {s.claude_code_version!r}")
    if init.get("memory_paths"):
        problems.append(f"memory is on: {init.get('memory_paths')}")
    if problems:
        raise InitProblem("; ".join(problems))


def _first_init(path: Path) -> dict | None:
    for rec in usage._json_lines(path):
        if rec.get("type") == "system" and rec.get("subtype") == "init":
            return rec
    return None


def run_turn(s: ContainerSession, prompt: str, stream_path: Path, *, resume: str | None = None,
             permission_mode: str = "bypassPermissions", runner=subprocess.run) -> TurnRecord:
    """Run one `claude -p` turn, writing its stream-json output to stream_path."""
    stream_path = Path(stream_path)
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    name = f"costeval-{uuid.uuid4().hex[:12]}"
    cmd = claude_command(s, prompt, container_name=name, resume=resume, permission_mode=permission_mode)
    start = time.monotonic()
    timed_out = False
    exit_code = None
    with open(stream_path, "wb") as out:
        try:
            exit_code = runner(cmd, stdout=out, stderr=subprocess.STDOUT, timeout=s.timeout_s).returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            runner(["docker", "kill", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    duration = time.monotonic() - start
    init = _first_init(stream_path)
    problem = None
    if init is None:
        problem = "no start-up record"
    else:
        try:
            check_init(s, init)
        except InitProblem as e:
            problem = str(e)
    summary = usage.from_stream(stream_path)
    final = summary.result.get("result") if summary.result else None
    return TurnRecord(
        stream_path=stream_path, container_name=name, exit_code=exit_code, timed_out=timed_out,
        duration_s=duration, session_id=summary.session_id or (init or {}).get("session_id"), init=init,
        init_problem=problem, summary=summary, final_text=final,
    )


class RoleFailed(RuntimeError):
    """A harness role's session ended without a usable result."""


@dataclass(frozen=True)
class RoleSession:
    """A harness role (the simulator, interface extraction, a grader) run with `claude -p` in the container.

    Roles aren't arms: they get no arm workspace unless given one, only the tools they name,
    and their sessions live in the roles' own configuration volume.
    """

    image: str
    config_volume: str
    model: str
    claude_code_version: str
    effort: str = "medium"
    tools: tuple[str, ...] = ()
    workspace_volume: str | None = None
    timeout_s: int = 900


@dataclass(frozen=True)
class RoleRecord:
    session_id: str | None
    structured: dict | None
    text: str | None
    usage: usage.Usage
    raw: dict
    duration_s: float


def role_command(r: RoleSession, prompt: str, *, container_name: str, json_schema: str | None = None) -> list[str]:
    cmd = ["docker", "run", "--rm", "--name", container_name, "-e", TOKEN_ENV,
           "-v", f"{_volume(r.config_volume)}:/cfg"]
    if r.workspace_volume:
        cmd += ["-v", f"{_volume(r.workspace_volume)}:/work"]
    cmd += ["-w", "/work", r.image, "claude", "-p", prompt,
            "--model", r.model, "--effort", r.effort,
            "--tools", ",".join(r.tools),
            "--settings", json.dumps({"autoMemoryEnabled": False}),
            "--output-format", "json"]
    if r.tools:
        cmd += ["--permission-mode", "bypassPermissions"]
    if json_schema is not None:
        cmd += ["--json-schema", json_schema]
    return cmd


def run_role(r: RoleSession, prompt: str, *, json_schema: str | None = None, runner=subprocess.run) -> RoleRecord:
    """Run one role turn and return its structured output (when a schema is given) and usage."""
    name = f"costeval-role-{uuid.uuid4().hex[:12]}"
    start = time.monotonic()
    try:
        proc = runner(role_command(r, prompt, container_name=name, json_schema=json_schema),
                      capture_output=True, text=True, timeout=r.timeout_s)
    except subprocess.TimeoutExpired as e:
        runner(["docker", "kill", name], capture_output=True, text=True)
        raise RoleFailed(f"timed out after {r.timeout_s}s") from e
    try:
        raw = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RoleFailed(f"exit {proc.returncode}, no JSON result: {proc.stderr[-500:]}") from e
    if raw.get("is_error") or (json_schema is not None and raw.get("structured_output") is None):
        raise RoleFailed(f"role session failed: {str(raw.get('result'))[:500]}")
    return RoleRecord(session_id=raw.get("session_id"), structured=raw.get("structured_output"),
                      text=raw.get("result"), usage=usage.from_result(raw), raw=raw,
                      duration_s=time.monotonic() - start)
