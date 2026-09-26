"""Test stand-in for the `docker` and `npx` commands used by run_eval.py.

Invoked as `stub_harness.py docker|npx|git <args...>`
through small wrapper scripts the tests put first on PATH. The wrappers set
STUB_STATE, a directory holding the call log, per-container pid files, and
these optional setting files (files rather than environment variables, because
the runner strips the harness's environment):

  mode              how the emulated harness behaves (default "ok"); a comma
                    list applies per harness call in order, the last repeating
  docker-info-fail  when present, `docker info` exits 1
  build-sleep       seconds `docker build` sleeps before succeeding
  mem-total         bytes `docker info --format {{.MemTotal}}` reports (default 8 GiB)

Every call appends one JSON object to $STUB_STATE/calls.jsonl. The `git` wrapper
logs each git invocation (argv, cwd, and whether the stub itself made it, marked
by STUB_INSIDE) and then executes the real git named by REAL_GIT.
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import time

STATE = os.environ["STUB_STATE"]
LOG = os.path.join(STATE, "calls.jsonl")


def log(entry):
    with open(LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def setting(name, default=None):
    path = os.path.join(STATE, name)
    return open(path).read().strip() if os.path.exists(path) else default


def next_mode():
    modes = setting("mode", "ok").split(",")
    counter = os.path.join(STATE, "mode-counter")
    n = int(open(counter).read()) if os.path.exists(counter) else 0
    with open(counter, "w") as f:
        f.write(str(n + 1))
    return modes[min(n, len(modes) - 1)]


def emit(event):
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()


def git(project, *args):
    subprocess.run(["git", "-C", project] + list(args), check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def list_tree(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        for d in dirnames:
            out.append(os.path.normpath(os.path.join(rel, d)) + "/")
        for f in filenames:
            out.append(os.path.normpath(os.path.join(rel, f)))
    return sorted(out)


def harness(project, plugins, config_path, argv, pidfile):
    """Emulate `opencode run` inside `project`."""
    mode = next_mode()
    stdin_data = sys.stdin.read()  # blocks forever if the runner left stdin open
    key = os.environ.get("OPENROUTER_API_KEY", "")
    log({
        "kind": "harness",
        "mode": mode,
        "argv": argv,
        "cwd": os.getcwd(),
        "stdin_len": len(stdin_data),
        "env": dict(os.environ),
        "config": open(config_path).read() if config_path and os.path.exists(config_path) else None,
        "plugins_listing": list_tree(plugins) if plugins and os.path.isdir(plugins) else None,
        "fixture_log": subprocess.run(
            ["git", "-C", project, "log", "--format=%an <%ae>|%s"],
            capture_output=True, text=True).stdout,
    })
    if pidfile:
        with open(pidfile, "w") as f:
            f.write(str(os.getpid()))

    if mode == "exit1":
        sys.stderr.write("harness crashed\n")
        sys.exit(1)
    if mode == "error_event":
        emit({"type": "error", "error": {"name": "APIError", "data": {"message": "Missing Authentication header"}}})
        sys.exit(0)
    if mode == "gitlink":
        # Replace .git with a symlink to a directory outside the project.
        decoy = os.path.join(STATE, "decoy-git")
        shutil.rmtree(os.path.join(project, ".git"))
        os.symlink(decoy, os.path.join(project, ".git"))
    if mode == "fifo":
        os.mkfifo(os.path.join(project, "pipe"))
    if mode == "sleep":
        with open(os.path.join(project, "partial.txt"), "w") as f:
            f.write("written before the hang\n")
        os.makedirs(os.path.join(project, ".git"), exist_ok=True)
        open(os.path.join(project, ".git", "index.lock"), "w").close()
        time.sleep(120)
        sys.exit(0)

    if mode == "gitlink":
        emit({"type": "text", "part": {"type": "text", "text": "swapped .git"}})
        sys.exit(0)
    emit({"type": "step_start", "part": {}})
    if mode != "empty":
        emit({"type": "text", "part": {"type": "text", "text": "thinking out loud"}})
    if mode == "toolfail":
        emit({"type": "tool_use", "part": {"tool": "read", "state": {"status": "error", "error": "no such file"}}})
    emit({"type": "tool_use", "part": {"tool": "write", "state": {"status": "completed", "input": {"filePath": "made.txt"}}}})

    # A committed change, an uncommitted new file, the key leaked into a file,
    # stdout, and stderr, an executable file, and a symlink.
    with open(os.path.join(project, "committed.txt"), "w") as f:
        f.write("committed by the model\n")
    git(project, "add", "committed.txt")
    git(project, "commit", "-m", "model commit")
    with open(os.path.join(project, "made.txt"), "w") as f:
        f.write("uncommitted\n")
    with open(os.path.join(project, "leak.sh"), "w") as f:
        f.write("#!/bin/sh\necho %s\n" % key)
    os.chmod(os.path.join(project, "leak.sh"), 0o755)
    os.symlink("made.txt", os.path.join(project, "link.txt"))
    sys.stderr.write("debug: key is %s\n" % key)

    if mode != "nocost":
        emit({"type": "step_finish", "part": {"cost": 0.25, "tokens": {"input": 10, "output": 5, "cache": {"read": 3, "write": 0}}}})
        emit({"type": "step_finish", "part": {"cost": 0.5, "tokens": {"input": 1, "output": 2, "cache": {"read": 0, "write": 1}}}})
    if mode == "plant":
        # Last act: a model trying to get code executed by whoever runs git here next.
        with open(os.path.join(project, ".git", "config"), "a") as f:
            f.write("[core]\n\tfsmonitor = touch %s\n" % os.path.join(STATE, "PWNED"))
    if mode == "empty":
        pass
    else:
        emit({"type": "text", "part": {"type": "text", "text": "FINAL ANSWER leaked %s" % key}})
    sys.exit(0)


def parse_docker_run(args):
    mounts, envs, opts, name, workdir = [], [], [], None, None
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-v", "--volume", "--mount", "-e", "--env", "--name", "-w", "--workdir",
                 "--user", "-u", "--tmpfs", "--memory", "--pids-limit", "--cap-drop",
                 "--security-opt", "--network"):
            val = args[i + 1]
            if a in ("-v", "--volume", "--mount"):
                mounts.append(val)
            elif a in ("-e", "--env"):
                envs.append(val)
            elif a == "--name":
                name = val
            elif a in ("-w", "--workdir"):
                workdir = val
            opts.append([a, val])
            i += 2
        elif a.startswith("-"):
            opts.append([a])
            i += 1
        else:
            return mounts, envs, opts, name, workdir, a, args[i + 1:]
    raise SystemExit("stub docker: no image in run args")


def docker(args):
    log({"kind": "docker", "argv": args})
    if args[0] == "info":
        if setting("docker-info-fail") is not None:
            sys.exit(1)
        if "--format" in args:
            print(setting("mem-total", str(8 * 1024 ** 3)))
        sys.exit(0)
    if args[:2] == ["image", "inspect"]:
        sys.exit(0 if os.path.exists(os.path.join(STATE, "image-built")) else 1)
    if args[0] == "build":
        time.sleep(float(setting("build-sleep", "0")))
        open(os.path.join(STATE, "image-built"), "w").close()
        sys.exit(0)
    if args[0] in ("stop", "kill"):
        name = args[-1]
        pidfile = os.path.join(STATE, name + ".pid")
        if os.path.exists(pidfile):
            try:
                os.kill(int(open(pidfile).read()), signal.SIGTERM)
            except ProcessLookupError:
                pass
        sys.exit(0)
    if args[0] == "rm":
        sys.exit(0)
    if args[0] == "run":
        mounts, envs, opts, name, workdir, image, cmd = parse_docker_run(args[1:])
        host = {}
        for m in mounts:
            parts = m.split(":")
            host[parts[1]] = parts[0]
        project = host["/work/project"]
        # The container sees only the -e names; emulate that environment.
        env = {}
        for e in envs:
            if "=" in e:
                k, v = e.split("=", 1)
                env[k] = v
            else:
                env[e] = os.environ.get(e, "")
        os.environ.clear()
        os.environ.update(env)
        os.environ["PATH"] = "/usr/bin:/bin"
        os.environ["STUB_STATE"] = STATE
        os.chdir(project)
        os.environ["STUB_INSIDE"] = "1"
        if cmd and cmd[0] != "opencode":
            # The capture container: run its command for real, container paths mapped to host.
            log({"kind": "docker-run", "mounts": mounts, "envs": envs, "opts": opts,
                 "name": name, "workdir": workdir, "image": image, "cmd": cmd, "passwd": None})
            mapped = [a.replace("/work/project", project).replace("/work/out", host["/work/out"])
                      for a in cmd]
            # In a real container a symlink to a host path outside the mounts dangles.
            # Emulate that so the host-side stub cannot reach what the container could not.
            gitdir = os.path.join(project, ".git")
            target = os.readlink(gitdir) if os.path.islink(gitdir) else None
            if target is not None:
                os.unlink(gitdir)
                os.symlink("/nonexistent-outside-container", gitdir)
            try:
                code = subprocess.run(mapped).returncode
            finally:
                if target is not None:
                    os.unlink(gitdir)
                    os.symlink(target, gitdir)
            sys.exit(code)
        passwd = host.get("/etc/passwd")
        log({"kind": "docker-run", "mounts": mounts, "envs": envs, "opts": opts,
             "name": name, "workdir": workdir, "image": image, "cmd": cmd,
             "passwd": open(passwd).read() if passwd and os.path.exists(passwd) else None})
        harness(project, host.get("/work/plugins"), host.get("/work/opencode.json"), cmd,
                os.path.join(STATE, name + ".pid") if name else None)
    raise SystemExit("stub docker: unhandled %r" % args)


def git_wrapper(args):
    log({"kind": "git", "argv": args, "cwd": os.getcwd(),
         "inside": bool(os.environ.get("STUB_INSIDE"))})
    real = os.environ["REAL_GIT"]
    os.execv(real, [real] + args)


def npx(args):
    log({"kind": "npx", "argv": args})
    os.environ["STUB_INSIDE"] = "1"
    config = os.environ.get("OPENCODE_CONFIG")
    # The staged plugins directory sits beside project/ in the scratch directory.
    plugins = os.path.join(os.path.dirname(os.getcwd()), "plugins")
    pidfile = os.path.join(STATE, "npx.pid")
    harness(os.getcwd(), plugins, config, args, pidfile)


if __name__ == "__main__":
    which, rest = sys.argv[1], sys.argv[2:]
    if which == "docker":
        docker(rest)
    elif which == "npx":
        npx(rest)
    elif which == "git":
        git_wrapper(rest)
    else:
        raise SystemExit("stub: unknown command " + which)
