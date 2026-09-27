#!/usr/bin/env python3
"""Run LID's behavioral eval suites on non-Claude models through OpenRouter.

    tools/alt-model-evals/run_eval.py <skill> <eval-ids> <model>
        [--runs N] [--timeout SECONDS] [--no-container]

Each run stages the eval's fixture and a copy of plugins/, executes the
opencode coding agent against the model inside a container, and captures the
transcript, final response, and resulting project state into the skill's
gitignored workspace, in the per-eval shape skill-creator's grader reads.
The runner does not grade.

Design: docs/intent/alt-model-evals/alt-model-evals-design.md
Specs:  docs/intent/alt-model-evals/alt-model-evals-specs.md
"""

# @spec ALT-EVAL-CLI-009 (standard library only)
import argparse
import datetime
import hashlib
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HARNESS_VERSION = "1.18.32"
HARNESS = "opencode-ai@" + HARNESS_VERSION

# @spec ALT-EVAL-CLI-010
RUNNER_DIR = Path(__file__).resolve().parent
REPO_ROOT = RUNNER_DIR.parent.parent
DOCKERFILE = RUNNER_DIR / "Dockerfile"

DEFAULT_TIMEOUT = 600
STOP_GRACE_SECONDS = 10
MEMORY_LIMIT_BYTES = 2 * 1024 ** 3  # docker's --memory 2g is 2 GiB
CONTAINER_HOME = "/home/eval"
GIT_NAME = "eval"
GIT_EMAIL = "eval@localhost"
REDACTED = b"[REDACTED]"

# Git commands the runner itself issues ignore the invoking user's global and
# system configuration (signing, hooks, templates), so staging and capture
# behave the same on every machine.
GIT_ENV_OVERRIDES = {
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": GIT_NAME,
    "GIT_AUTHOR_EMAIL": GIT_EMAIL,
    "GIT_COMMITTER_NAME": GIT_NAME,
    "GIT_COMMITTER_EMAIL": GIT_EMAIL,
    "GIT_TERMINAL_PROMPT": "0",
}


class UsageError(Exception):
    """A problem with the invocation or the suite, found before any run starts."""


# ------------------------------------------------------------ pure helpers

# @spec ALT-EVAL-CLI-003, ALT-EVAL-CLI-004
def parse_selector(selector, ids):
    """Resolve an eval-ID selector against the suite's IDs, ascending."""
    known = set(ids)
    if selector.strip() == "all":
        return sorted(known)
    chosen, bad = set(), []
    for item in selector.split(","):
        item = item.strip()
        span = re.fullmatch(r"(\d+)-(\d+)", item)
        if span:
            low, high = int(span.group(1)), int(span.group(2))
            hit = {i for i in known if low <= i <= high}
            if not hit:
                bad.append(item)
            chosen |= hit
        elif re.fullmatch(r"\d+", item):
            if int(item) in known:
                chosen.add(int(item))
            else:
                bad.append(item)
        else:
            raise UsageError("unrecognized eval selector item %r; use N, A-B, a comma list of those, or 'all'" % item)
    if bad:
        raise UsageError("no such eval id(s) in the suite: %s" % ", ".join(bad))
    return sorted(chosen)


# @spec ALT-EVAL-OUT-001, ALT-EVAL-OUT-003
def sanitize(text):
    return re.sub(r"[^A-Za-z0-9._-]", "_", text)


# @spec ALT-EVAL-STAGE-007
def opencode_config():
    return {
        "autoupdate": False,
        "share": "disabled",
        "provider": {"openrouter": {"options": {"apiKey": "{env:OPENROUTER_API_KEY}"}}},
    }


# @spec ALT-EVAL-BOX-001, ALT-EVAL-CLI-011
def harness_argv(model, prompt, variant=None):
    return (["opencode", "run", "--pure", "--auto", "--format", "json",
             "-m", "openrouter/" + model]
            + (["--variant", variant] if variant else []) + [prompt])


# @spec ALT-EVAL-STAGE-008, ALT-EVAL-STAGE-009
def build_prompt(skill_md, plugins_dir, prompt, date):
    return (
        "You are executing one eval run of an agent skill. The current directory is the "
        "project root; treat it as the entire repository.\n"
        "\n"
        "1. Read the skill at %s and any references/ files it directs you to. "
        "Sibling skills live under %s.\n"
        "2. The user's request: \"%s\"\n"
        "   Execute it per the skill against the current directory, making any file changes yourself.\n"
        "3. This run is non-interactive. Where the skill would ask the user, take the skill's "
        "stated default, and state in your final response which defaults you took. "
        "Today's date is %s.\n"
        "4. Your final message must be the exact user-facing response and nothing else.\n"
    ) % (skill_md, plugins_dir, prompt, date)


# @spec ALT-EVAL-RUN-001, ALT-EVAL-RUN-002, ALT-EVAL-RUN-003, ALT-EVAL-RUN-004
def classify(exit_code, has_error, timed_out, interrupted):
    if interrupted:
        return "interrupted"
    if timed_out:
        return "timeout"
    if exit_code != 0 or has_error:
        return "harness_error"
    return "completed"


def _add_counts(total, more):
    for key, value in more.items():
        if isinstance(value, dict):
            total[key] = _add_counts(total.get(key, {}), value)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            total[key] = total.get(key, 0) + value
    return total


def _error_message(event):
    err = event.get("error")
    if isinstance(err, dict):
        data = err.get("data")
        if isinstance(data, dict) and data.get("message"):
            return str(data["message"])
        for key in ("message", "name"):
            if err.get(key):
                return str(err[key])
    return json.dumps(err if err is not None else event)


# @spec ALT-EVAL-OUT-006, ALT-EVAL-OUT-010, ALT-EVAL-OUT-013, ALT-EVAL-RUN-003
def summarize_events(lines):
    """Summarize the harness's JSON event stream (one event per line)."""
    summary = {"response": "", "total_cost_usd": None, "tokens": None,
               "tool_calls": 0, "has_error": False, "error_message": None}
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        kind, part = event.get("type"), event.get("part")
        part = part if isinstance(part, dict) else {}
        if kind == "text":
            summary["response"] = part.get("text") or ""
        elif kind == "tool_use":
            summary["tool_calls"] += 1
        elif kind == "step_finish":
            cost = part.get("cost")
            if isinstance(cost, (int, float)) and not isinstance(cost, bool):
                summary["total_cost_usd"] = (summary["total_cost_usd"] or 0) + cost
            if isinstance(part.get("tokens"), dict):
                summary["tokens"] = _add_counts(summary["tokens"] or {}, part["tokens"])
        elif kind == "error":
            summary["has_error"] = True
            summary["error_message"] = _error_message(event)
    return summary


# @spec ALT-EVAL-BOX-004
def image_tag(dockerfile_bytes):
    digest = hashlib.sha256(dockerfile_bytes).hexdigest()[:12]
    return "lid-alt-eval:opencode-%s-%s" % (HARNESS_VERSION, digest)


# @spec ALT-EVAL-OUT-002
def claim_batch_dir(workspace, date, slug):
    """Create and return the first free batch directory; mkdir makes the claim atomic."""
    workspace.mkdir(parents=True, exist_ok=True)
    base = "alt-model-%s-%s" % (date, slug)
    n = 1
    while True:
        candidate = workspace / (base if n == 1 else "%s-%d" % (base, n))
        try:
            candidate.mkdir()
            return candidate
        except FileExistsError:
            n += 1


# ------------------------------------------------------------ repository

def git(cwd, *args, env=None, check=True):
    full_env = dict(os.environ)
    full_env.update(GIT_ENV_OVERRIDES)
    if env:
        full_env.update(env)
    return subprocess.run(["git", "--no-pager", "-C", str(cwd)] + list(args), env=full_env,
                          check=check, capture_output=True, text=True)


# @spec ALT-EVAL-CLI-002
def find_skill(repo_root, name):
    matches = sorted(p.parent.parent for p in repo_root.glob("plugins/*/skills/%s/evals/evals.json" % name))
    if not matches:
        raise UsageError("no skill named %r with an evals/evals.json under plugins/*/skills/" % name)
    if len(matches) > 1:
        raise UsageError("skill name %r is ambiguous: %s" % (
            name, ", ".join(str(m.relative_to(repo_root)) for m in matches)))
    return matches[0]


# @spec ALT-EVAL-KEY-001, ALT-EVAL-KEY-002
def read_key(environ):
    key = environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise UsageError("OPENROUTER_API_KEY is not set; export your OpenRouter key under that name")
    return key


# @spec ALT-EVAL-STAGE-003
def validate_fixture_paths(evals):
    for ev in evals:
        for entry in ev.get("files", []):
            path = entry["path"]
            parts = Path(path).parts
            if os.path.isabs(path) or ".." in parts or (parts and parts[0] == ".git"):
                raise UsageError("eval %s has a fixture path outside its project: %s" % (ev["id"], path))


# @spec ALT-EVAL-STAGE-011
def plugins_tree(repo_root):
    """Git tree ID of plugins/ as it is on disk, via a throwaway index."""
    with tempfile.TemporaryDirectory() as tmp:
        index = {"GIT_INDEX_FILE": os.path.join(tmp, "index")}
        git(repo_root, "read-tree", "--empty", env=index)
        git(repo_root, "add", "-A", "--", "plugins", env=index)
        return git(repo_root, "write-tree", "--prefix=plugins/", env=index).stdout.strip()


def head_info(repo_root):
    head = git(repo_root, "rev-parse", "--verify", "-q", "HEAD", check=False).stdout.strip() or None
    tree = None
    if head:
        tree = git(repo_root, "rev-parse", "--verify", "-q", "HEAD:plugins", check=False).stdout.strip() or None
    return head, tree


# ------------------------------------------------------------ staging

def scratch_root():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return Path(base) / "lid-alt-evals"


# @spec ALT-EVAL-STAGE-001
def make_scratch():
    root = scratch_root()
    root.mkdir(parents=True, exist_ok=True)
    while True:
        path = root / secrets.token_hex(8)
        try:
            path.mkdir()
            return path
        except FileExistsError:
            continue


# @spec ALT-EVAL-STAGE-002, ALT-EVAL-STAGE-004
def stage_fixture(files, project):
    project.mkdir()
    for entry in files:
        target = project / entry["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as f:
            f.write(entry["content"].encode("utf-8"))
    git(project, "-c", "init.defaultBranch=main", "init", "-q", "--template=")
    git(project, "add", "-A")
    git(project, "commit", "-q", "--allow-empty", "--no-verify", "-m", "fixture")
    return git(project, "rev-parse", "HEAD").stdout.strip()


# @spec ALT-EVAL-STAGE-005, ALT-EVAL-STAGE-006
def stage_plugins(repo_root, dest):
    def skip(directory, names):
        return [n for n in names
                if (n == "evals" or n.endswith("-workspace")) and os.path.isdir(os.path.join(directory, n))]
    shutil.copytree(repo_root / "plugins", dest, symlinks=True, ignore=skip)


# ------------------------------------------------------------ harness

# @spec ALT-EVAL-BOX-006
def check_docker():
    try:
        ok = subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL).returncode == 0
    except FileNotFoundError:
        ok = False
    if not ok:
        raise UsageError("no container runtime is reachable (`docker info` failed). Start one "
                         "(colima, Docker Desktop, OrbStack, ...) or pass --no-container to run "
                         "the harness unsandboxed on this machine.")


# @spec ALT-EVAL-BOX-016
def check_runtime_memory():
    out = subprocess.run(["docker", "info", "--format", "{{.MemTotal}}"],
                         capture_output=True, text=True)
    try:
        total = int(out.stdout.strip())
    except ValueError:
        return  # the runtime did not report its memory; let the run find out
    if total < MEMORY_LIMIT_BYTES:
        raise UsageError(
            "the container runtime has %.1f GiB of memory, less than the %.1f GiB each run's "
            "container may use; give the runtime more memory (e.g. `colima start --memory 4`, "
            "or Docker Desktop's Resources settings) and try again"
            % (total / 1024 ** 3, MEMORY_LIMIT_BYTES / 1024 ** 3))


# @spec ALT-EVAL-BOX-002, ALT-EVAL-BOX-003, ALT-EVAL-BOX-004
def ensure_image():
    tag = image_tag(DOCKERFILE.read_bytes())
    exists = subprocess.run(["docker", "image", "inspect", tag], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL).returncode == 0
    if not exists:
        sys.stderr.write("building image %s ...\n" % tag)
        built = subprocess.run(["docker", "build", "-t", tag, "--build-arg",
                                "OPENCODE_VERSION=" + HARNESS_VERSION, "-f", str(DOCKERFILE),
                                str(RUNNER_DIR)], stdout=sys.stderr)
        if built.returncode != 0:
            raise UsageError("building the harness image failed")
    return tag


# @spec ALT-EVAL-BOX-009, ALT-EVAL-BOX-010, ALT-EVAL-BOX-011
def hardening_argv(scratch):
    """Container settings shared by the harness and capture containers."""
    uid, gid = os.getuid(), os.getgid()
    (scratch / "passwd").write_text("eval:x:%d:%d:eval:%s:/bin/sh\n" % (uid, gid, CONTAINER_HOME))
    (scratch / "group").write_text("eval:x:%d:\n" % gid)
    return [
        "-v", "%s:/etc/passwd:ro" % (scratch / "passwd"),
        "-v", "%s:/etc/group:ro" % (scratch / "group"),
        "--user", "%d:%d" % (uid, gid),
        "--read-only",
        "--tmpfs", "%s:rw,exec,uid=%d,gid=%d,mode=0700" % (CONTAINER_HOME, uid, gid),
        "--tmpfs", "/tmp:rw,exec,mode=1777",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--memory", "%dg" % (MEMORY_LIMIT_BYTES // 1024 ** 3),
        "--pids-limit", "512",
    ]


# @spec ALT-EVAL-BOX-005, ALT-EVAL-BOX-007, ALT-EVAL-BOX-008, ALT-EVAL-BOX-012, ALT-EVAL-KEY-003
def docker_run_argv(name, image, scratch, model, prompt, variant=None):
    return [
        "docker", "run", "--rm", "--name", name,
        "-v", "%s:/work/project" % (scratch / "project"),
        "-v", "%s:/work/plugins:ro" % (scratch / "plugins"),
        "-v", "%s:/work/opencode.json:ro" % (scratch / "opencode.json"),
        "-w", "/work/project",
    ] + hardening_argv(scratch) + [
        "-e", "OPENROUTER_API_KEY",
        "-e", "HOME=%s" % CONTAINER_HOME,
        "-e", "OPENCODE_CONFIG=/work/opencode.json",
        "-e", "GIT_AUTHOR_NAME=%s" % GIT_NAME,
        "-e", "GIT_AUTHOR_EMAIL=%s" % GIT_EMAIL,
        "-e", "GIT_COMMITTER_NAME=%s" % GIT_NAME,
        "-e", "GIT_COMMITTER_EMAIL=%s" % GIT_EMAIL,
        "-e", "LANG=C.UTF-8",
        image,
    ] + harness_argv(model, prompt, variant)


# @spec ALT-EVAL-BOX-014
def bare_env(key, home, config):
    env = {
        "OPENROUTER_API_KEY": key,
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_STATE_HOME": str(home / ".local" / "state"),
        "OPENCODE_CONFIG": str(config),
        "GIT_AUTHOR_NAME": GIT_NAME,
        "GIT_AUTHOR_EMAIL": GIT_EMAIL,
        "GIT_COMMITTER_NAME": GIT_NAME,
        "GIT_COMMITTER_EMAIL": GIT_EMAIL,
        "LANG": os.environ.get("LANG") or "C.UTF-8",
        "npm_config_cache": os.environ.get("npm_config_cache") or os.path.join(os.path.expanduser("~"), ".npm"),
    }
    return env


class Harness:
    """One running harness process, in a container or directly on the host."""

    def __init__(self, argv, stdout, stderr, cwd=None, env=None, container=None):
        self.container = container
        self.proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                     cwd=cwd, env=env, start_new_session=container is None)
        self.started = time.monotonic()

    # @spec ALT-EVAL-RUN-005
    def stop(self):
        if self.proc.poll() is not None:
            return
        if self.container:
            subprocess.run(["docker", "stop", "-t", str(STOP_GRACE_SECONDS), self.container],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            try:
                os.killpg(self.proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            self.proc.wait(timeout=STOP_GRACE_SECONDS + 5)
        except subprocess.TimeoutExpired:
            if not self.container:
                try:
                    os.killpg(self.proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            self.proc.kill()
            self.proc.wait()
        if not self.container:
            # Reap anything the harness left behind in its process group.
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass


# ------------------------------------------------------------ capture

# Runs inside the capture container. $1 is the fixture commit. Git is told to
# ignore anything in the repository's own configuration that would run a program.
CAPTURE_SCRIPT = r"""
cd /work/project || exit 0
rm -f .git/index.lock
export GIT_INDEX_FILE=/tmp/capture-index
g() { git --no-pager -c core.fsmonitor=false -c core.hooksPath=/dev/null "$@"; }
if ! { g read-tree HEAD && g add -A -f && g diff --cached --binary --no-ext-diff --no-textconv "$1"; } \
    > /work/out/changes.patch 2> /work/out/changes.err; then
  cat /work/out/changes.err > /work/out/changes.patch
fi
rm -f /work/out/changes.err
g log --stat > /work/out/git-log.txt 2>&1
exit 0
"""
CAPTURE_TIMEOUT = 120


# @spec ALT-EVAL-BOX-017, ALT-EVAL-BOX-018, ALT-EVAL-BOX-019, ALT-EVAL-OUT-007, ALT-EVAL-OUT-008
def capture_in_container(image, scratch, fixture_sha, out):
    """Produce changes.patch and git-log.txt without running git on the host."""
    capture_out = scratch / "capture"
    capture_out.mkdir()
    name = "lid-alt-eval-capture-" + secrets.token_hex(6)
    argv = [
        "docker", "run", "--rm", "--name", name, "--network", "none",
        "-v", "%s:/work/project" % (scratch / "project"),
        "-v", "%s:/work/out" % capture_out,
        "-w", "/work/project",
    ] + hardening_argv(scratch) + [
        "-e", "HOME=%s" % CONTAINER_HOME,
        "-e", "LANG=C.UTF-8",
        image, "sh", "-c", CAPTURE_SCRIPT, "capture", fixture_sha,
    ]
    try:
        subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=CAPTURE_TIMEOUT)
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "kill", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for fname in ("changes.patch", "git-log.txt"):
        src = capture_out / fname
        if src.is_file() and not src.is_symlink():
            shutil.move(str(src), str(out / fname))
        else:
            (out / fname).write_text("capture step produced no %s\n" % fname)


# @spec ALT-EVAL-OUT-009
def copy_project(project, out):
    """Copy the final project: links kept as links, special files and the top .git dropped."""
    def skip(directory, names):
        dropped = []
        for n in names:
            path = os.path.join(directory, n)
            if Path(directory) == project and n == ".git":
                dropped.append(n)
            elif not os.path.islink(path) and not (os.path.isfile(path) or os.path.isdir(path)):
                dropped.append(n)
        return dropped
    shutil.copytree(project, out / "project", symlinks=True, ignore=skip)


# Used only under --no-container, where the host is already inside the model's reach.
def capture_on_host(project, fixture_sha, out):
    lock = project / ".git" / "index.lock"
    if lock.exists():
        lock.unlink()
    with tempfile.TemporaryDirectory() as tmp:
        index = {"GIT_INDEX_FILE": os.path.join(tmp, "index")}
        steps = [git(project, "read-tree", "HEAD", env=index, check=False),
                 git(project, "add", "-A", "-f", env=index, check=False)]
        diff = git(project, "diff", "--cached", "--binary", fixture_sha, env=index, check=False)
        failed = [s for s in steps + [diff] if s.returncode != 0]
        (out / "changes.patch").write_text(diff.stdout if not failed else
                                           "".join(s.stderr for s in failed))
    log = git(project, "log", "--stat", check=False)
    (out / "git-log.txt").write_text(log.stdout if log.returncode == 0 else log.stderr)


# @spec ALT-EVAL-KEY-004
def redact_tree(root, key):
    needle = key.encode("utf-8")
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            path = os.path.join(dirpath, name)
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            with open(path, "rb") as f:
                data = f.read()
            if needle not in data:
                continue
            mode = os.stat(path).st_mode
            os.chmod(path, mode | 0o200)
            with open(path, "wb") as f:
                f.write(data.replace(needle, REDACTED))
            os.chmod(path, mode)


# ------------------------------------------------------------ one run

class Interrupted(Exception):
    pass


# @spec ALT-EVAL-RUN-006, ALT-EVAL-STAGE-010
def run_one(ctx, ev, n, run_dir):
    """Stage, execute, capture, and clean up one run. Returns (status, timing)."""
    scratch = make_scratch()
    home = None
    status, harness, interrupted = None, None, False
    out = scratch / "out"
    out.mkdir()
    exit_code, started, finished = None, None, None
    try:
        fixture_sha = stage_fixture(ev.get("files", []), scratch / "project")
        stage_plugins(REPO_ROOT, scratch / "plugins")
        (scratch / "opencode.json").write_text(json.dumps(opencode_config(), indent=2) + "\n")

        rel_skill = ctx["skill_dir"].relative_to(REPO_ROOT / "plugins")
        # @spec ALT-EVAL-BOX-015
        plugins_dir = str(scratch / "plugins") if ctx["bare"] else "/work/plugins"
        prompt = build_prompt("%s/%s/SKILL.md" % (plugins_dir, rel_skill.as_posix()), plugins_dir,
                              ev["prompt"], ctx["date"])

        with open(out / "events.jsonl", "wb") as stdout, open(out / "stderr.log", "wb") as stderr:
            if ctx["bare"]:
                home = Path(tempfile.mkdtemp(prefix="lid-alt-eval-home-"))
                argv = ["npx", "-y", HARNESS] + harness_argv(ctx["model"], prompt, ctx["variant"])[1:]
                harness = Harness(argv, stdout, stderr, cwd=str(scratch / "project"),
                                  env=bare_env(ctx["key"], home, scratch / "opencode.json"))
            else:
                name = "lid-alt-eval-" + secrets.token_hex(6)
                argv = docker_run_argv(name, ctx["image"], scratch, ctx["model"], prompt, ctx["variant"])
                harness = Harness(argv, stdout, stderr, container=name)
            started = harness.started
            timed_out = False
            try:
                harness.proc.wait(timeout=ctx["timeout"])
            except subprocess.TimeoutExpired:
                timed_out = True
                harness.stop()
            except KeyboardInterrupt:
                interrupted = True
                signal.signal(signal.SIGINT, signal.SIG_IGN)
                harness.stop()
            finished = time.monotonic()
            exit_code = harness.proc.returncode

        with open(out / "events.jsonl", encoding="utf-8", errors="replace") as f:
            summary = summarize_events(f)
        status = classify(exit_code, summary["has_error"], timed_out, interrupted)
        error_message = summary["error_message"]
        if status == "harness_error" and not error_message:
            error_message = "harness exited with code %s" % exit_code
        (out / "response.md").write_text(summary["response"])
        if ctx["bare"]:
            capture_on_host(scratch / "project", fixture_sha, out)
        else:
            capture_in_container(ctx["image"], scratch, fixture_sha, out)
        copy_project(scratch / "project", out)
        timing = {
            "model": ctx["model"],
            "harness": HARNESS,
            "status": status,
            "duration_ms": int(round((finished - started) * 1000)),
            "total_cost_usd": summary["total_cost_usd"],
            "tokens": summary["tokens"],
            "tool_calls": summary["tool_calls"],
            "exit_code": exit_code,
            "error_message": error_message,
        }
        (out / "timing.json").write_text(json.dumps(timing, indent=2) + "\n")
        redact_tree(out, ctx["key"])
        run_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(out), str(run_dir))
        if interrupted:
            raise Interrupted()
        return status, timing
    except KeyboardInterrupt:
        if harness is not None:
            harness.stop()
        raise Interrupted()
    finally:
        if harness is not None and harness.proc.poll() is None:
            harness.stop()
        shutil.rmtree(scratch, ignore_errors=True)
        if home is not None:
            shutil.rmtree(home, ignore_errors=True)


# ------------------------------------------------------------ batch

def write_json(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    os.replace(str(tmp), str(path))


def parse_args(argv):
    def positive(text):
        value = int(text)
        if value < 1:
            raise argparse.ArgumentTypeError("must be a positive integer")
        return value

    p = argparse.ArgumentParser(
        prog="tools/alt-model-evals/run_eval.py",
        description="Run a skill's eval suite on an OpenRouter model through opencode.")
    p.add_argument("skill", help="skill directory name, e.g. lid-coach")
    p.add_argument("eval_ids", help="'all', or a comma list of IDs and A-B ranges, e.g. 1,3-5")
    p.add_argument("model", help="OpenRouter model ID, e.g. z-ai/glm-5.3-flash")
    p.add_argument("--runs", type=positive, default=1, help="runs per eval (default 1)")
    p.add_argument("--timeout", type=positive, default=DEFAULT_TIMEOUT,
                   help="per-run limit on the harness, in seconds (default %d)" % DEFAULT_TIMEOUT)
    p.add_argument("--variant", default=None,
                   help="reasoning-effort variant passed through to the harness's --variant, "
                        "e.g. high or minimal (default: the model's own)")
    p.add_argument("--no-container", action="store_true",
                   help="run the harness directly on this machine, without a sandbox")
    return p.parse_args(argv)


# @spec ALT-EVAL-CLI-001, ALT-EVAL-CLI-005, ALT-EVAL-CLI-006, ALT-EVAL-CLI-007,
#       ALT-EVAL-CLI-008, ALT-EVAL-RUN-007, ALT-EVAL-RUN-008, ALT-EVAL-OUT-011, ALT-EVAL-OUT-012
def main(argv):
    args = parse_args(argv)
    try:
        key = read_key(os.environ)
        skill_dir = find_skill(REPO_ROOT, args.skill)
        suite = json.loads((skill_dir / "evals" / "evals.json").read_text())
        by_id = {ev["id"]: ev for ev in suite["evals"]}
        eval_ids = parse_selector(args.eval_ids, list(by_id))
        validate_fixture_paths([by_id[i] for i in eval_ids])
        image = None
        if args.no_container:
            # @spec ALT-EVAL-BOX-013
            sys.stderr.write("WARNING: --no-container runs the harness directly on this machine. "
                             "The model can read any file you can read.\n")
        else:
            check_docker()
            check_runtime_memory()
            image = ensure_image()
    except UsageError as e:
        sys.stderr.write("run_eval: %s\n" % e)
        return 2

    date = datetime.date.today().isoformat()
    workspace = skill_dir.parent / (skill_dir.name + "-workspace")
    # @spec ALT-EVAL-OUT-014
    slug = sanitize(args.model) + ("-" + sanitize(args.variant) if args.variant else "")
    batch_dir = claim_batch_dir(workspace, date, slug)
    head, head_tree = head_info(REPO_ROOT)
    tree = plugins_tree(REPO_ROOT)
    batch = {
        "skill": args.skill,
        "eval_ids": eval_ids,
        "model": args.model,
        "variant": args.variant,
        "harness": HARNESS,
        "sandbox": "none" if args.no_container else "container",
        "timeout": args.timeout,
        "runs": args.runs,
        "head_commit": head,
        "plugins_tree": tree,
        "plugins_tree_matches_head": tree == head_tree,
        "state": "running",
    }
    write_json(batch_dir / "batch.json", batch)

    ctx = {"key": key, "model": args.model, "variant": args.variant, "skill_dir": skill_dir, "date": date,
           "timeout": args.timeout, "bare": args.no_container, "image": image}
    results, consecutive_errors, state = [], 0, "complete"
    try:
        for eval_id in eval_ids:
            ev = by_id[eval_id]
            # @spec ALT-EVAL-OUT-004, ALT-EVAL-OUT-005
            eval_dir = batch_dir / ("eval-%s-%s" % (eval_id, sanitize(ev["eval_name"])))
            if not (eval_dir / "eval_metadata.json").exists():
                eval_dir.mkdir(parents=True, exist_ok=True)
                write_json(eval_dir / "eval_metadata.json", {
                    "eval_id": eval_id, "eval_name": ev["eval_name"],
                    "prompt": ev["prompt"], "assertions": ev["assertions"]})
            for n in range(1, args.runs + 1):
                status, timing = run_one(ctx, ev, n, eval_dir / "with_skill" / ("run-%d" % n))
                results.append((eval_id, n, status, timing["total_cost_usd"]))
                consecutive_errors = consecutive_errors + 1 if status == "harness_error" else 0
                if consecutive_errors >= 2:
                    state = "aborted"
                    sys.stderr.write("run_eval: two harness errors in a row; stopping the batch\n")
                    raise StopIteration
    except StopIteration:
        pass
    except Interrupted:
        state = "aborted"
        results.append((eval_id, n, "interrupted", None))
    except BaseException:
        state = "aborted"
        raise
    finally:
        batch["state"] = state
        write_json(batch_dir / "batch.json", batch)

    for eval_id, n, status, cost in results:
        print("eval %s run %d: %s  cost %s" % (
            eval_id, n, status, "n/a" if cost is None else "$%.4f" % cost))
    print("batch: %s" % batch_dir)
    if state == "aborted":
        return 130 if results and results[-1][2] == "interrupted" else 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
