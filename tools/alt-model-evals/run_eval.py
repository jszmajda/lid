#!/usr/bin/env python3
"""Run LID's behavioral eval suites on non-Claude models through OpenRouter.

    tools/alt-model-evals/run_eval.py <skill> <eval-ids> <model> [--runs N] [options]
    tools/alt-model-evals/run_eval.py --roster <preset> <model> [<model> ...] [--lanes N] [options]

    options: [--estimate] [--max-cost USD] [--timeout SECONDS] [--idle-timeout SECONDS]
             [--effort LEVEL] [--variant NAME] [--no-container]

Each run stages the eval's fixture and a snapshot of plugins/, executes the
opencode coding agent against the model inside a container, and captures the
transcript, final response, and resulting project state into the skill's
gitignored workspace, in the per-eval shape skill-creator's grader reads.
Every run is priced from OpenRouter's published prices. A roster runs one of
the presets in rosters.json across several suites, in lanes; --estimate runs a
small cost probe and prints the projected cost instead. The runner does not grade.

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
import threading
import time
import traceback
import urllib.request
from pathlib import Path

HARNESS_VERSION = "1.18.32"
HARNESS = "opencode-ai@" + HARNESS_VERSION
DEFAULT_EFFORT = "medium"
REASONING_WARN_BELOW = 500

# @spec ALT-EVAL-CLI-010
RUNNER_DIR = Path(__file__).resolve().parent
REPO_ROOT = RUNNER_DIR.parent.parent
DOCKERFILE = RUNNER_DIR / "Dockerfile"

ROSTERS_FILE = RUNNER_DIR / "rosters.json"
# @spec ALT-EVAL-COST-001
MODELS_URL = "https://openrouter.ai/api/v1/models"
MODELS_URL_ENV = "LID_ALT_EVALS_MODELS_URL"  # tests point this at a local file
PRICE_FIELDS = ("prompt", "completion", "internal_reasoning", "input_cache_read", "input_cache_write")
DEFAULT_TIMEOUT = 1800
DEFAULT_IDLE_TIMEOUT = 600
POLL_SECONDS = 1
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
# @spec ALT-EVAL-CLI-012
def opencode_config(plugins_dir, model, effort):
    openrouter = {"options": {"apiKey": "{env:OPENROUTER_API_KEY}"}}
    if effort != "default":
        # Pinned as the model's own option: opencode's variant tables skip some model families.
        openrouter["models"] = {model: {"options": {"reasoning": {"effort": effort}}}}
    return {
        "autoupdate": False,
        "share": "disabled",
        # The title agent calls a second "small model"; a headless run has no use for a title.
        "agent": {"title": {"disable": True}},
        "provider": {"openrouter": openrouter},
        # The harness's own skill tool delivers SKILL.md whole; its file-read tool cuts long lines.
        "skills": {"paths": [plugins_dir]},
    }


# @spec ALT-EVAL-BOX-001, ALT-EVAL-CLI-011
def harness_argv(model, prompt, variant=None, cont=False):
    return (["opencode", "run", "--pure", "--auto", "--format", "json",
             "-m", "openrouter/" + model]
            + (["--variant", variant] if variant else [])
            + (["--continue"] if cont else []) + [prompt])


# @spec ALT-EVAL-STAGE-008
def skill_name(skill_dir):
    """The frontmatter `name` of the skill's SKILL.md, else its directory name."""
    text = (skill_dir / "SKILL.md").read_text()
    if text.startswith("---\n"):
        for line in text[4:].split("\n---", 1)[0].splitlines():
            key, _, value = line.partition(":")
            if key.strip() == "name" and value.strip():
                return value.strip().strip("'\"")
    return skill_dir.name


# @spec ALT-EVAL-STAGE-008, ALT-EVAL-STAGE-009
NON_INTERACTIVE = (
    "3. This run is non-interactive. Where the skill would ask the user, take the skill's "
    "stated default, and state in your final response which defaults you took. "
)
# @spec ALT-EVAL-STAGE-013
CONVERSATIONAL = (
    "3. The user will read your final message and reply. Where the skill directs you to ask "
    "the user, ask in your final message and stop; do not answer for them. "
)


def build_prompt(name, plugins_dir, prompt, date, conversational=False):
    return (
        "You are executing one eval run of an agent skill. The current directory is the "
        "project root; treat it as the entire repository.\n"
        "\n"
        "1. Load the skill named `%s` with your skill tool, and read any references/ files it "
        "directs you to. "
        "Sibling skills live under %s.\n"
        "2. The user's request: \"%s\"\n"
        "   Execute it per the skill against the current directory, making any file changes yourself.\n"
        "%s"
        "Today's date is %s.\n"
        "4. Your final message must be the exact user-facing response and nothing else.\n"
    ) % (name, plugins_dir, prompt, CONVERSATIONAL if conversational else NON_INTERACTIVE, date)


# @spec ALT-EVAL-RUN-004, ALT-EVAL-RUN-012
def wait_with_limits(proc, events, run_limit, idle_limit, started, poll=POLL_SECONDS, stop=None):
    """Wait for the harness to exit. Returns None when it does, "stopped" once the
    stop event is set (an interrupt or a runner failure), or the limit that stopped
    it: "run" once it has lasted run_limit seconds, "inactivity" once it has written
    nothing to its event stream for idle_limit seconds. The run limit is checked
    first, so a turn that reaches both at once records "run"."""
    last, size = started, 0
    while True:
        try:
            proc.wait(timeout=poll)
            return None
        except subprocess.TimeoutExpired:
            pass
        if stop is not None and stop.is_set():
            return "stopped"
        now = time.monotonic()
        try:
            current = os.path.getsize(events)
        except OSError:
            current = size
        if current != size:
            size, last = current, now
        if now - started >= run_limit:
            return "run"
        if now - last >= idle_limit:
            return "inactivity"


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


# ------------------------------------------------------------ cost

def _price(value):
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    return price if price >= 0 else None


# @spec ALT-EVAL-COST-004, ALT-EVAL-COST-006
def effective_prices(pricing):
    """The per-token prices to charge, from a model-list entry's `pricing`, or None
    when it lists no usable prompt or completion price. A listed price is used as
    listed, zero included; an unlisted reasoning price falls back to the completion
    price, and unlisted cache prices to the prompt price, which errs high."""
    pricing = pricing if isinstance(pricing, dict) else {}
    prompt, completion = _price(pricing.get("prompt")), _price(pricing.get("completion"))
    if prompt is None or completion is None:
        return None
    prices = {"prompt": prompt, "completion": completion, "fallbacks": []}
    for field, fallback in (("internal_reasoning", completion), ("input_cache_read", prompt),
                            ("input_cache_write", prompt)):
        value = _price(pricing.get(field))
        if value is None:
            value = fallback
            prices["fallbacks"].append(field)
        prices[field] = value
    return prices


# @spec ALT-EVAL-COST-005, ALT-EVAL-COST-007
def turn_price(tokens, prices):
    """A turn's priced cost from the token counts summed from its event stream. The
    harness reports the five counts disjointly, so each token is priced once."""
    if not isinstance(tokens, dict):
        return 0.0
    cache = tokens.get("cache") if isinstance(tokens.get("cache"), dict) else {}

    def n(d, k):
        v = d.get(k)
        return v if isinstance(v, (int, float)) and not isinstance(v, bool) else 0

    return (n(tokens, "input") * prices["prompt"]
            + n(cache, "read") * prices["input_cache_read"]
            + n(cache, "write") * prices["input_cache_write"]
            + n(tokens, "output") * prices["completion"]
            + n(tokens, "reasoning") * prices["internal_reasoning"])


# @spec ALT-EVAL-COST-001
def fetch_model_list(url):
    """OpenRouter's public model list keyed by model ID, or None when it cannot be
    fetched or parsed. The request carries no key."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "lid-alt-model-evals"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return {m["id"]: m for m in data["data"] if isinstance(m, dict) and "id" in m}
    except (OSError, ValueError, KeyError, TypeError):
        return None


# @spec ALT-EVAL-COST-001, ALT-EVAL-COST-002, ALT-EVAL-COST-003, ALT-EVAL-COST-004
def model_prices(models, need_prices, url=None):
    """Check every model against OpenRouter's list and return {model: prices or None}."""
    url = url or os.environ.get(MODELS_URL_ENV) or MODELS_URL
    listing = fetch_model_list(url)
    if listing is None:
        if need_prices:
            raise UsageError("OpenRouter's model list could not be read from %s; --estimate and "
                             "--max-cost need its prices" % url)
        sys.stderr.write("WARNING: OpenRouter's model list could not be read from %s; running without "
                         "prices, so summaries show the harness's own cost figures.\n" % url)
        return {m: None for m in models}
    read_at = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    out = {}
    for model in models:
        entry = listing.get(model)
        if entry is None:
            raise UsageError("OpenRouter lists no model %r; check the model ID" % model)
        if "tools" not in (entry.get("supported_parameters") or []):
            raise UsageError("OpenRouter lists %r without tool calling; the harness needs tool calling, "
                             "so every run would fail" % model)
        prices = effective_prices(entry.get("pricing"))
        if prices is None:
            if need_prices:
                raise UsageError("OpenRouter lists no prompt or completion price for %r; --estimate and "
                                 "--max-cost need its prices" % model)
            sys.stderr.write("WARNING: OpenRouter lists no prompt or completion price for %r; running it "
                             "without prices.\n" % model)
        else:
            prices["read_at"] = read_at
        out[model] = prices
    return out


# @spec ALT-EVAL-COST-014
def makespan(durations, lanes):
    """Wall-clock time to run batches of these durations, in queue order, each on the lane that frees first."""
    free = [0.0] * max(1, lanes)
    for d in durations:
        i = min(range(len(free)), key=lambda k: free[k])
        free[i] += d
    return max(free) if durations else 0


def fmt_duration(seconds):
    seconds = int(round(seconds))
    return "%dh %02dm %02ds" % (seconds // 3600, seconds % 3600 // 60, seconds % 60)


# @spec ALT-EVAL-BOX-004
def image_tag(dockerfile_bytes):
    digest = hashlib.sha256(dockerfile_bytes).hexdigest()[:12]
    return "lid-alt-eval:opencode-%s-%s" % (HARNESS_VERSION, digest)


# @spec ALT-EVAL-OUT-002
# @spec ALT-EVAL-OUT-020
def claim_batch_dir(workspace, date, slug, prefix="alt-model"):
    """Create and return the first free batch directory; mkdir makes the claim atomic."""
    workspace.mkdir(parents=True, exist_ok=True)
    base = "%s-%s-%s" % (prefix, date, slug)
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


# @spec ALT-EVAL-STAGE-005, ALT-EVAL-STAGE-006, ALT-EVAL-STAGE-011
def snapshot_plugins(repo_root, dest):
    """The tree ID of plugins/ as it is on disk, and a copy in `dest` of exactly the
    files that tree covers, minus evals/ and *-workspace/ directories, links kept as links."""
    with tempfile.TemporaryDirectory() as tmp:
        index = {"GIT_INDEX_FILE": os.path.join(tmp, "index")}
        git(repo_root, "read-tree", "--empty", env=index)
        git(repo_root, "add", "-A", "--", "plugins", env=index)
        tree = git(repo_root, "write-tree", "--prefix=plugins/", env=index).stdout.strip()
        listed = git(repo_root, "ls-files", "-z", "--", "plugins", env=index).stdout
    dest.mkdir(parents=True)
    for rel in listed.split("\0"):
        if not rel:
            continue
        parts = Path(rel).parts[1:]
        if any(p == "evals" or p.endswith("-workspace") for p in parts[:-1]):
            continue
        src, dst = repo_root / rel, dest.joinpath(*parts)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_symlink():
            os.symlink(os.readlink(src), dst)
        elif src.is_file():
            shutil.copy2(src, dst)
    return tree


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


# @spec ALT-EVAL-STAGE-006
def stage_plugins(repo_root, dest):
    """A copy of repo_root's plugins/ minus evals/ and *-workspace/ directories. The packaging
    checks stage a tree this way; the runner's own runs stage from its snapshot instead."""
    def skip(directory, names):
        return [n for n in names
                if (n == "evals" or n.endswith("-workspace")) and os.path.isdir(os.path.join(directory, n))]
    shutil.copytree(repo_root / "plugins", dest, symlinks=True, ignore=skip)


# @spec ALT-EVAL-STAGE-005, ALT-EVAL-STAGE-006
def stage_snapshot(snapshot, dest):
    """A run's plugins/: a copy of the invocation's snapshot, never of the repository."""
    shutil.copytree(snapshot, dest, symlinks=True)


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
def check_runtime_memory(lanes=1):
    out = subprocess.run(["docker", "info", "--format", "{{.MemTotal}}"],
                         capture_output=True, text=True)
    try:
        total = int(out.stdout.strip())
    except ValueError:
        return  # the runtime did not report its memory; let the run find out
    need = MEMORY_LIMIT_BYTES * max(1, lanes)
    if total < need:
        who = "each run's container" if lanes <= 1 else "%d lanes' containers" % lanes
        raise UsageError(
            "the container runtime has %.1f GiB of memory, less than the %.1f GiB %s may use; "
            "give the runtime more memory (e.g. `colima start --memory %d`, or Docker Desktop's "
            "Resources settings), or run fewer lanes, and try again"
            % (total / 1024 ** 3, need / 1024 ** 3, who, need // 1024 ** 3 + 2))


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
# @spec ALT-EVAL-STAGE-012
def docker_run_argv(name, image, scratch, model, prompt, variant=None, cont=False):
    return [
        "docker", "run", "--rm", "--name", name,
        "-v", "%s:/work/project" % (scratch / "project"),
        "-v", "%s:/work/plugins:ro" % (scratch / "plugins"),
        "-v", "%s:/work/opencode.json:ro" % (scratch / "opencode.json"),
        "-v", "%s:/work/state" % (scratch / "state"),
        "-w", "/work/project",
    ] + hardening_argv(scratch) + [
        "-e", "OPENROUTER_API_KEY",
        "-e", "HOME=%s" % CONTAINER_HOME,
        "-e", "OPENCODE_CONFIG=/work/opencode.json",
        "-e", "XDG_DATA_HOME=/work/state",
        "-e", "GIT_AUTHOR_NAME=%s" % GIT_NAME,
        "-e", "GIT_AUTHOR_EMAIL=%s" % GIT_EMAIL,
        "-e", "GIT_COMMITTER_NAME=%s" % GIT_NAME,
        "-e", "GIT_COMMITTER_EMAIL=%s" % GIT_EMAIL,
        "-e", "LANG=C.UTF-8",
        image,
    ] + harness_argv(model, prompt, variant, cont)


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
    capture_out = Path(tempfile.mkdtemp(prefix="capture-", dir=str(scratch)))
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


class Invocation:
    """State one invocation's lanes share: why it is stopping, each model's spend,
    and which models no further run may start for."""

    def __init__(self, max_cost=None):
        self.lock = threading.Lock()
        self.stop = threading.Event()      # set on an interrupt or a runner failure
        self.cause = None                  # "interrupted" or "runner_error"
        self.interrupted_at = None
        self.max_cost = max_cost
        self.spent = {}
        self.model_stop = {}               # model -> "harness_errors" or "max_cost"
        self.out_lock = threading.Lock()

    # @spec ALT-EVAL-RUN-008
    def interrupt(self, *_):
        with self.lock:
            self.cause = "interrupted"     # an interrupt is the reason, whenever it comes
            if self.interrupted_at is None:
                self.interrupted_at = time.monotonic()
        self.stop.set()

    # @spec ALT-EVAL-ROSTER-008
    def fail(self):
        with self.lock:
            if self.cause is None:
                self.cause = "runner_error"
        self.stop.set()

    def add_spend(self, model, cost):
        with self.lock:
            self.spent[model] = self.spent.get(model, 0.0) + (cost or 0.0)

    def stop_model(self, model, reason):
        with self.lock:
            self.model_stop.setdefault(model, reason)

    # @spec ALT-EVAL-COST-017, ALT-EVAL-COST-018, ALT-EVAL-COST-019, ALT-EVAL-ROSTER-007
    # (checked only before a run starts, so a run in progress always finishes)
    def stop_reason_for(self, model):
        """Why no further run of `model` may start, or None. The first stop to reach a model is kept."""
        with self.lock:
            if self.cause:
                return self.cause
            if model in self.model_stop:
                return self.model_stop[model]
            if self.max_cost is not None and self.spent.get(model, 0.0) >= self.max_cost:
                self.model_stop[model] = "max_cost"
                return "max_cost"
            return None

    def say(self, text):
        with self.out_lock:
            print(text, flush=True)


# @spec ALT-EVAL-OUT-009
def run_one(ctx, ev, n, run_dir):
    """Stage, execute, capture, and clean up one run.
    Returns (status, timing, priced cost or None, elapsed seconds)."""
    t0 = time.monotonic()
    stop = ctx["inv"].stop
    prices = ctx["prices"]
    scratch = make_scratch()
    home = None
    status, harness, interrupted = None, None, False
    out = scratch / "out"
    out.mkdir()
    exit_code, started, finished = None, None, None
    try:
        fixture_sha = stage_fixture(ev.get("files", []), scratch / "project")
        stage_snapshot(ctx["snapshot"], scratch / "plugins")
        # @spec ALT-EVAL-BOX-015
        plugins_dir = str(scratch / "plugins") if ctx["bare"] else "/work/plugins"
        (scratch / "opencode.json").write_text(json.dumps(opencode_config(plugins_dir, ctx["model"], ctx["effort"]), indent=2) + "\n")
        prompt = build_prompt(skill_name(ctx["skill_dir"]), plugins_dir, ev["prompt"], ctx["date"],
                              conversational=bool(ev.get("follow_up")))

        (scratch / "state").mkdir()
        if ctx["bare"]:
            home = Path(tempfile.mkdtemp(prefix="lid-alt-eval-home-"))

        def turn(text, cont, suffix):
            """Run the harness once; returns (status, summary, exit_code, (start, end), error, interrupted, limit)."""
            nonlocal harness
            with open(out / ("events%s.jsonl" % suffix), "wb") as stdout, \
                    open(out / ("stderr%s.log" % suffix), "wb") as stderr:
                if ctx["bare"]:
                    argv = ["npx", "-y", HARNESS] + harness_argv(ctx["model"], text, ctx["variant"], cont)[1:]
                    harness = Harness(argv, stdout, stderr, cwd=str(scratch / "project"),
                                      env=bare_env(ctx["key"], home, scratch / "opencode.json"))
                else:
                    name = "lid-alt-eval-" + secrets.token_hex(6)
                    argv = docker_run_argv(name, ctx["image"], scratch, ctx["model"], text,
                                           ctx["variant"], cont)
                    harness = Harness(argv, stdout, stderr, container=name)
                begun, timed_out, stopped, limit = harness.started, False, False, None
                try:
                    limit = wait_with_limits(harness.proc, out / ("events%s.jsonl" % suffix),
                                             ctx["timeout"], ctx["idle_timeout"], begun, stop=stop)
                    if limit == "stopped":
                        stopped, limit = True, None
                        harness.stop()
                    elif limit:
                        timed_out = True
                        harness.stop()
                except KeyboardInterrupt:
                    stopped = True
                    harness.stop()
                ended = time.monotonic()
                code = harness.proc.returncode
            with open(out / ("events%s.jsonl" % suffix), encoding="utf-8", errors="replace") as f:
                summ = summarize_events(f)
            st = classify(code, summ["has_error"], timed_out, stopped)
            err = summ["error_message"]
            if st == "harness_error" and not err:
                # @spec ALT-EVAL-RUN-013: a container that fails to start is the harness's non-zero exit
                err = "harness exited with code %s" % code
            return st, summ, code, (begun, ended), err, stopped, (limit if st == "timeout" else None)

        status, summary, exit_code, (started, finished), error_message, interrupted, limit = turn(prompt, False, "")
        (out / "response.md").write_text(summary["response"])
        # @spec ALT-EVAL-COST-007, ALT-EVAL-OUT-021
        first_cost = turn_price(summary["tokens"], prices) if prices else None
        run_cost = first_cost

        def capture(dest):
            if ctx["bare"]:
                capture_on_host(scratch / "project", fixture_sha, dest)
            else:
                capture_in_container(ctx["image"], scratch, fixture_sha, dest)

        follow_up = None
        if ev.get("follow_up"):
            # @spec ALT-EVAL-RUN-009, ALT-EVAL-RUN-010, ALT-EVAL-OUT-016
            if status == "completed" and not interrupted and not stop.is_set():
                # @spec ALT-EVAL-OUT-017
                first = Path(tempfile.mkdtemp(prefix="turn1-", dir=str(scratch)))
                capture(first)
                shutil.move(str(first / "changes.patch"), str(out / "changes1.patch"))
                st2, summ2, code2, (b2, e2), err2, interrupted, limit2 = turn(ev["follow_up"]["prompt"], True, "2")
                (out / "response2.md").write_text(summ2["response"])
                second_cost = turn_price(summ2["tokens"], prices) if prices else None
                follow_up = {"status": st2, "duration_ms": int(round((e2 - b2) * 1000)),
                             "total_cost_usd": summ2["total_cost_usd"], "tokens": summ2["tokens"],
                             "tool_calls": summ2["tool_calls"], "exit_code": code2, "error_message": err2,
                             "timeout_limit": limit2,  # @spec ALT-EVAL-OUT-019
                             "priced_cost_usd": second_cost}  # @spec ALT-EVAL-OUT-021
                if prices:
                    run_cost = first_cost + second_cost  # @spec ALT-EVAL-COST-008
            else:
                follow_up = {"status": "skipped"}
                if status == "completed" and stop.is_set():
                    interrupted = True  # stopped between its turns
        if interrupted:
            # @spec ALT-EVAL-RUN-008: an interrupt in either turn makes the whole run interrupted
            status = "interrupted"
        # @spec ALT-EVAL-OUT-017
        capture(out)
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
            "timeout_limit": limit,  # @spec ALT-EVAL-OUT-019
            "priced_cost_usd": first_cost,
        }
        if follow_up is not None:
            timing["follow_up"] = follow_up  # @spec ALT-EVAL-RUN-011: status stays the first turn's
        (out / "timing.json").write_text(json.dumps(timing, indent=2) + "\n")
        redact_tree(out, ctx["key"])
        run_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(out), str(run_dir))
        return status, timing, run_cost, time.monotonic() - t0
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
    os.replace(tmp, path)


def harness_figure(timing):
    """A run's own harness cost figure: its turns' total_cost_usd, or None when none reported one."""
    figures = [t.get("total_cost_usd") for t in (timing, timing.get("follow_up") or {}) if t]
    figures = [f for f in figures if isinstance(f, (int, float))]
    return sum(figures) if figures else None


# @spec ALT-EVAL-OUT-011, ALT-EVAL-OUT-012, ALT-EVAL-OUT-022, ALT-EVAL-RUN-007, ALT-EVAL-ROSTER-003,
#       ALT-EVAL-ROSTER-010
def run_batch(inv, common, spec):
    """Run one batch. Returns its result, or None when it never started."""
    model = spec["model"]
    # A batch starts only when its first run is about to start.
    if inv.stop_reason_for(model):
        return None
    skill_dir, by_id = spec["skill_dir"], spec["by_id"]
    workspace = skill_dir.parent / (skill_dir.name + "-workspace")
    # @spec ALT-EVAL-OUT-014
    slug = (sanitize(model)
            + ("-" + sanitize(common["effort"]) if common["effort"] != DEFAULT_EFFORT else "")
            + ("-" + sanitize(common["variant"]) if common["variant"] else ""))
    batch_dir = claim_batch_dir(workspace, common["date"], slug,
                                prefix="cost-probe" if spec["probe"] else "alt-model")
    started_at = time.monotonic()
    prices = common["prices"].get(model)
    batch = {
        "skill": spec["skill"],
        "eval_ids": spec["eval_ids"],
        "model": model,
        "effort": common["effort"],
        "variant": common["variant"],
        "harness": HARNESS,
        "sandbox": "none" if common["bare"] else "container",
        "timeout": common["timeout"],
        "idle_timeout": common["idle_timeout"],
        "runs": spec["runs"],
        "head_commit": common["head"],
        "plugins_tree": common["tree"],
        "plugins_tree_matches_head": common["tree"] == common["head_tree"],
        "prices": prices,
        "max_cost": inv.max_cost,
        "probe": spec["probe"],
        "roster": spec["roster"],
        "state": "running",
        "stop_reason": None,
    }
    write_json(batch_dir / "batch.json", batch)
    ctx = {"key": common["key"], "model": model, "effort": common["effort"], "variant": common["variant"],
           "skill_dir": skill_dir, "date": common["date"], "timeout": common["timeout"],
           "idle_timeout": common["idle_timeout"], "bare": common["bare"], "image": common["image"],
           "snapshot": common["snapshot"], "prices": prices, "inv": inv}
    result = {"spec": spec, "dir": batch_dir, "runs": [], "priced": prices is not None, "failed": False}
    plan = [(eval_id, n) for eval_id in spec["eval_ids"] for n in range(1, spec["runs"] + 1)]
    state, reason, consecutive, current = "complete", None, 0, None
    try:
        for i, (eval_id, n) in enumerate(plan):
            stop = inv.stop_reason_for(model)
            if stop:
                state, reason = "aborted", stop
                break
            ev = by_id[eval_id]
            # @spec ALT-EVAL-OUT-004, ALT-EVAL-OUT-005
            eval_dir = batch_dir / ("eval-%s-%s" % (eval_id, sanitize(ev["eval_name"])))
            if not (eval_dir / "eval_metadata.json").exists():
                eval_dir.mkdir(parents=True, exist_ok=True)
                write_json(eval_dir / "eval_metadata.json", {
                    "eval_id": eval_id, "eval_name": ev["eval_name"],
                    "prompt": ev["prompt"], "assertions": ev["assertions"],
                    # @spec ALT-EVAL-OUT-018
                    **({"follow_up": ev["follow_up"]} if ev.get("follow_up") else {})})
            current = (eval_id, n)
            status, timing, cost, elapsed = run_one(ctx, ev, n, eval_dir / "with_skill" / ("run-%d" % n))
            current = None
            inv.add_spend(model, cost)
            fu = timing.get("follow_up") or {}
            result["runs"].append({"eval": eval_id, "n": n, "status": status, "cost": cost,
                                   "harness": harness_figure(timing), "elapsed": elapsed,
                                   "reasoning": (timing.get("tokens") or {}).get("reasoning", 0) or 0,
                                   "follow_up": fu.get("status"), "error": timing.get("error_message")
                                   or fu.get("error_message")})
            if status == "interrupted":
                state, reason = "aborted", inv.cause or "interrupted"
                break
            consecutive = consecutive + 1 if status == "harness_error" else 0
            if consecutive >= 2:
                # @spec ALT-EVAL-ROSTER-007: stops the model's other batches, runs left here or not
                inv.stop_model(model, "harness_errors")
                if i < len(plan) - 1:
                    state, reason = "aborted", "harness_errors"
                    sys.stderr.write("run_eval: two harness errors in a row; stopping %s\n" % model)
                break
    except BaseException:
        state, reason = "aborted", "runner_error"
        result["failed"] = True
        if current is not None:
            result["runs"].append({"eval": current[0], "n": current[1], "status": "interrupted", "cost": None,
                                   "harness": None, "elapsed": 0, "reasoning": 0, "follow_up": None,
                                   "error": "runner failure"})
        sys.stderr.write("run_eval: runner failure in %s %s:\n%s" % (model, spec["skill"], traceback.format_exc()))
        inv.fail()
    finally:
        if state == "aborted" and inv.interrupted_at is not None and inv.interrupted_at >= started_at:
            reason = "interrupted"
        if state == "aborted" and reason == "runner_error" and inv.cause == "interrupted":
            reason = "interrupted"
        batch["state"], batch["stop_reason"] = state, reason
        write_json(batch_dir / "batch.json", batch)
    result["state"], result["stop_reason"] = state, reason
    return result


def money(value):
    return "n/a" if value is None else "$%.4f" % value


# @spec ALT-EVAL-CLI-008, ALT-EVAL-CLI-017, ALT-EVAL-OUT-015
def print_batch_summary(result, effort):
    lines = []
    for r in result["runs"]:
        if result["priced"]:
            cost = money(r["cost"])
        else:
            cost = money(r["harness"]) + (" (harness)" if r["harness"] is not None else "")
        lines.append("eval %s run %d: %s  cost %s" % (r["eval"], r["n"], r["status"], cost))
    for line in lines:
        print(line)
    reasoning = sorted(r["reasoning"] for r in result["runs"] if r["status"] == "completed")
    if reasoning:
        mid = len(reasoning) // 2
        median = reasoning[mid] if len(reasoning) % 2 else (reasoning[mid - 1] + reasoning[mid]) / 2
        print("median reasoning tokens: %g" % median)
        if effort != "default" and median < REASONING_WARN_BELOW:
            print("WARNING: effort %r was requested but the model barely reasoned (median %g "
                  "reasoning tokens, under %d); the provider may be ignoring the setting."
                  % (effort, median, REASONING_WARN_BELOW))
    print("total: %s" % total_text(result["runs"], result["priced"]))
    print("batch: %s" % result["dir"])


def total_text(runs, priced):
    if priced:
        return money(sum(r["cost"] or 0 for r in runs))
    figures = [r["harness"] for r in runs if r["harness"] is not None]
    missing = len(runs) - len(figures)
    note = "harness figures" + ("; %d run%s reported none" % (missing, "" if missing == 1 else "s") if missing else "")
    return "%s (%s)" % (money(sum(figures)), note)


# ------------------------------------------------------------ queue

# @spec ALT-EVAL-ROSTER-005, ALT-EVAL-ROSTER-008, ALT-EVAL-ROSTER-011
def run_queue(inv, common, specs, lanes, roster):
    """Run batches in queue order, up to `lanes` at once. Returns one result (or None) per spec."""
    results = [None] * len(specs)
    nxt = [0]
    pick = threading.Lock()

    def lane():
        while True:
            with pick:
                if nxt[0] >= len(specs):
                    return
                i = nxt[0]
                nxt[0] += 1
            if inv.stop.is_set():
                continue  # no further batch starts after an interrupt or a runner failure
            try:
                res = run_batch(inv, common, specs[i])
            except BaseException:
                # A failure before the batch could record itself (claiming its directory, say).
                sys.stderr.write("run_eval: runner failure starting %s %s:\n%s" % (
                    specs[i]["model"], specs[i]["skill"], traceback.format_exc()))
                inv.fail()
                res = None
            results[i] = res
            if res is not None and roster:
                spec = res["spec"]
                inv.say("batch done: %s %s evals %s %s %s" % (
                    spec["model"], spec["skill"], ",".join(map(str, spec["eval_ids"])), res["state"],
                    total_text(res["runs"], res["priced"])))

    threads = [threading.Thread(target=lane, daemon=True) for _ in range(max(1, min(lanes, len(specs))))]
    for t in threads:
        t.start()
    while any(t.is_alive() for t in threads):
        for t in threads:
            t.join(0.2)
    return results


# ------------------------------------------------------------ planning

def load_presets():
    try:
        return json.loads(ROSTERS_FILE.read_text())
    except (OSError, ValueError) as e:
        raise UsageError("cannot read the roster presets in %s: %s" % (ROSTERS_FILE, e))


class Suites:
    """Each suite's evals.json, read once at the start of the invocation."""

    def __init__(self):
        self.cache = {}

    # @spec ALT-EVAL-CLI-002, ALT-EVAL-STAGE-015
    def get(self, skill):
        if skill not in self.cache:
            skill_dir = find_skill(REPO_ROOT, skill)
            suite = json.loads((skill_dir / "evals" / "evals.json").read_text())
            self.cache[skill] = (skill_dir, {ev["id"]: ev for ev in suite["evals"]})
        return self.cache[skill]


def make_spec(suites, skill, selector, runs, model, probe=False, roster=None):
    # @spec ALT-EVAL-CLI-004, ALT-EVAL-STAGE-003
    skill_dir, by_id = suites.get(skill)
    if isinstance(selector, list):
        selector = ",".join(str(i) for i in selector)
    eval_ids = parse_selector(selector, list(by_id))
    validate_fixture_paths([by_id[i] for i in eval_ids])
    return {"skill": skill, "skill_dir": skill_dir, "by_id": by_id, "eval_ids": eval_ids, "runs": runs,
            "model": model, "probe": probe, "roster": roster}


# @spec ALT-EVAL-ROSTER-001, ALT-EVAL-ROSTER-004, ALT-EVAL-ROSTER-006
def plan_roster(suites, preset, models, roster):
    batches = preset["batches"]
    return [make_spec(suites, b["skill"], b["evals"], b["runs"], m, roster=roster)
            for b in batches for m in models]


# @spec ALT-EVAL-COST-010, ALT-EVAL-COST-011, ALT-EVAL-ROSTER-002
# (probe batches are ordinary batches, run through the same queue and lanes)
def plan_probe(suites, args, models, preset, roster):
    if preset is None:
        skill_dir, by_id = suites.get(args.skill)
        lowest = parse_selector(args.eval_ids, list(by_id))[0]
        return [make_spec(suites, args.skill, [lowest], 1, models[0], probe=True)]
    by_skill = []
    for entry in preset["probe"]:
        group = next((g for g in by_skill if g[0] == entry["skill"]), None)
        if group is None:
            by_skill.append((entry["skill"], [entry["eval"]]))
        else:
            group[1].append(entry["eval"])
    return [make_spec(suites, skill, ids, 1, m, probe=True, roster=roster)
            for skill, ids in by_skill for m in models]


# ------------------------------------------------------------ estimate

# @spec ALT-EVAL-COST-012, ALT-EVAL-COST-013, ALT-EVAL-COST-014, ALT-EVAL-COST-015
def print_estimate(models, probe_specs, probe_results, real_specs, prices, lanes, roster):
    """Print each model's projection; returns the models that got one."""
    projected = {}
    for model in models:
        planned = [(s, e) for s in probe_specs if s["model"] == model for e in s["eval_ids"]]
        done = {}
        for spec, res in zip(probe_specs, probe_results):
            if res is not None and spec["model"] == model:
                for r in res["runs"]:
                    done[(spec["skill"], r["eval"])] = r
        rows, ok = [], True
        for spec, eval_id in planned:
            r = done.get((spec["skill"], eval_id))
            if r is None:
                ok = False
                rows.append("    %s eval %s: not started" % (spec["skill"], eval_id))
                continue
            fine = r["status"] == "completed" and r["follow_up"] in (None, "completed")
            ok = ok and fine
            label = r["status"] if r["follow_up"] in (None, "completed", "skipped") else \
                "%s, follow-up %s" % (r["status"], r["follow_up"])
            rows.append("    %s eval %s: %s%s" % (spec["skill"], eval_id, label,
                                                  "" if fine else " (%s)" % (r["error"] or "no error message")))
        total_runs = sum(len(s["eval_ids"]) * s["runs"] for s in real_specs if s["model"] == model)
        p = prices.get(model)
        print("estimate for %s" % model)
        if p:
            print("  prices per million tokens: prompt $%.2f, completion $%.2f, reasoning $%.2f, "
                  "cache read $%.2f, cache write $%.2f" % tuple(p[f] * 1e6 for f in PRICE_FIELDS))
        runs = [done[(s["skill"], e)] for s, e in planned if (s["skill"], e) in done]
        print("  probe: %d run%s, %s" % (len(runs), "" if len(runs) == 1 else "s",
                                          money(sum(r["cost"] or 0 for r in runs))))
        if ok and runs:
            mean_cost = sum(r["cost"] for r in runs) / len(runs)
            mean_elapsed = sum(r["elapsed"] for r in runs) / len(runs)
            projected[model] = mean_elapsed
            print("  projected cost: $%.2f for %d runs" % (mean_cost * total_runs, total_runs))
            print("  projected run time: %s for %d runs" % (fmt_duration(mean_elapsed * total_runs), total_runs))
        else:
            print("  no projection; probe runs:")
            for row in rows:
                print(row)
    if roster:
        durations = [projected[s["model"]] * len(s["eval_ids"]) * s["runs"]
                     for s in real_specs if s["model"] in projected]
        left_out = [m for m in models if m not in projected]
        print("projected wall-clock time with %d lane%s: %s%s" % (
            lanes, "" if lanes == 1 else "s", fmt_duration(makespan(durations, lanes)),
            " (leaves out %s: no projection)" % ", ".join(left_out) if left_out else ""))
    return set(projected)


# ------------------------------------------------------------ main

def parse_args(argv):
    def positive(text):
        value = int(text)
        if value < 1:
            raise argparse.ArgumentTypeError("must be a positive integer")
        return value

    p = argparse.ArgumentParser(
        prog="tools/alt-model-evals/run_eval.py",
        usage="%(prog)s <skill> <eval-ids> <model> [--runs N] [options]\n"
              "       %(prog)s --roster <preset> <model> [<model> ...] [--lanes N] [options]",
        description="Run a skill's eval suite, or a roster preset across several suites, on "
                    "OpenRouter models through opencode.")
    p.add_argument("args", nargs="*", metavar="ARG",
                   help="<skill> <eval-ids> <model>; with --roster, one or more model IDs")
    p.add_argument("--roster", default=None, help="run the named preset from rosters.json")
    p.add_argument("--lanes", type=positive, default=None, help="with --roster, batches run at once (default 1)")
    p.add_argument("--estimate", action="store_true",
                   help="run a small cost probe and print the projected cost instead of running")
    # @spec ALT-EVAL-COST-016
    p.add_argument("--max-cost", type=float, default=None, metavar="USD",
                   help="stop starting runs of a model once its priced spend reaches USD")
    p.add_argument("--runs", type=positive, default=None, help="runs per eval (default 1)")
    p.add_argument("--timeout", type=positive, default=DEFAULT_TIMEOUT,
                   help="run limit: the longest each turn may run, in seconds (default %d)" % DEFAULT_TIMEOUT)
    p.add_argument("--idle-timeout", type=positive, default=DEFAULT_IDLE_TIMEOUT,
                   help="inactivity limit: the longest each turn may go without writing to its "
                        "event stream, in seconds (default %d)" % DEFAULT_IDLE_TIMEOUT)
    p.add_argument("--effort", default=DEFAULT_EFFORT,
                   help="reasoning effort pinned for the model, e.g. low, medium, high, max; "
                        "'default' leaves the model's own default (default: %s)" % DEFAULT_EFFORT)
    p.add_argument("--variant", default=None,
                   help="reasoning-effort variant passed through to the harness's --variant, "
                        "e.g. high or minimal (default: the model's own)")
    p.add_argument("--no-container", action="store_true",
                   help="run the harness directly on this machine, without a sandbox")
    args = p.parse_args(argv)
    # @spec ALT-EVAL-CLI-001, ALT-EVAL-CLI-014, ALT-EVAL-CLI-016
    if args.roster is not None:
        if not args.args:
            p.error("--roster needs at least one model ID")
        if args.runs is not None:
            p.error("--runs does not apply to a roster; its preset sets each batch's runs")
        args.models = list(args.args)
    else:
        if len(args.args) != 3:
            p.error("expected <skill> <eval-ids> <model>")
        if args.lanes is not None:
            p.error("--lanes applies only with --roster")
        args.skill, args.eval_ids, model = args.args
        args.models = [model]
    if len(set(args.models)) != len(args.models):
        p.error("a model ID is named more than once")
    if args.max_cost is not None and not args.max_cost > 0:
        p.error("--max-cost must be above zero")
    args.runs = args.runs or 1
    args.lanes = args.lanes or 1
    return args


# @spec ALT-EVAL-CLI-007, ALT-EVAL-CLI-008, ALT-EVAL-CLI-018, ALT-EVAL-COST-009, ALT-EVAL-COST-020,
#       ALT-EVAL-ROSTER-009, ALT-EVAL-ROSTER-012, ALT-EVAL-STAGE-014
def main(argv):
    args = parse_args(argv)
    roster, preset = None, None
    try:
        key = read_key(os.environ)
        suites = Suites()
        if args.roster is not None:
            presets = load_presets()
            if args.roster not in presets:
                # @spec ALT-EVAL-CLI-015
                raise UsageError("no roster preset named %r; defined presets: %s"
                                 % (args.roster, ", ".join(sorted(presets))))
            preset = presets[args.roster]
            roster = {"preset": args.roster, "id": datetime.datetime.now().strftime("%Y%m%dT%H%M%S-")
                      + secrets.token_hex(3)}
            real = plan_roster(suites, preset, args.models, roster)
        else:
            real = [make_spec(suites, args.skill, args.eval_ids, args.runs, args.models[0])]
        specs = plan_probe(suites, args, args.models, preset, roster) if args.estimate else real
        prices = model_prices(args.models, need_prices=args.estimate or args.max_cost is not None)
        image = None
        if args.no_container:
            # @spec ALT-EVAL-BOX-013
            sys.stderr.write("WARNING: --no-container runs the harness directly on this machine. "
                             "The model can read any file you can read.\n")
        else:
            check_docker()
            check_runtime_memory(min(args.lanes, len(specs)))
            image = ensure_image()
    except UsageError as e:
        sys.stderr.write("run_eval: %s\n" % e)
        return 2

    inv = Invocation(max_cost=args.max_cost)
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, inv.interrupt)
    head, head_tree = head_info(REPO_ROOT)
    snapshot = make_scratch() / "plugins"
    try:
        tree = snapshot_plugins(REPO_ROOT, snapshot)
        common = {"key": key, "effort": args.effort, "variant": args.variant,
                  "date": datetime.date.today().isoformat(), "timeout": args.timeout,
                  "idle_timeout": args.idle_timeout, "bare": args.no_container, "image": image,
                  "snapshot": snapshot, "head": head, "head_tree": head_tree, "tree": tree, "prices": prices}
        results = run_queue(inv, common, specs, args.lanes, roster is not None)
    finally:
        shutil.rmtree(snapshot.parent, ignore_errors=True)

    started = [r for r in results if r is not None]
    for res in started:
        print_batch_summary(res, args.effort)
    never = [s for s, r in zip(specs, results) if r is None]
    if roster is not None:
        for model in args.models:
            mine = [r for r in started if r["spec"]["model"] == model]
            runs = [run for r in mine for run in r["runs"]]
            print("model total: %s %s" % (model, total_text(runs, prices.get(model) is not None)))
        if not args.estimate:
            for s in never:
                print("not started: %s %s evals %s" % (s["model"], s["skill"], ",".join(map(str, s["eval_ids"]))))
    if args.estimate:
        got = print_estimate(args.models, specs, results, real, prices, args.lanes, roster is not None)
        if inv.cause == "interrupted":
            return 130
        return 0 if len(got) == len(args.models) and inv.cause is None else 1
    if inv.cause == "interrupted":
        return 130
    if inv.cause or never or any(r["state"] == "aborted" for r in started):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
