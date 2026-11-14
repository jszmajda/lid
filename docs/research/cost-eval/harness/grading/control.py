"""The grading control server. It runs inside an arm's app container, starts the arm's service under a fake clock,
and is the graders' only way to reach it.

Graders call it through `gt`. It forwards requests to the service, sets the clock, restarts the service, restores
named setups, and runs only the setup commands the interface reference names. It writes every operation to the
execution log itself, so the log doesn't depend on what a grader chooses to record, and it never serves the
service's source.

Standard library only: it runs with whatever Python the container has.

    python3 control.py --spec /grade/start.json --port 9000 --log /log/exec.jsonl --snapshots /snap

The spec (written by interface extraction, checked by the harness):
    {"workdir": "/app", "command": "...", "env": {...}, "port": 8000, "data_path": "/data",
     "ready_path": "/docs", "setup_commands": ["..."]}
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FAKETIME_LIB = os.environ.get("FAKETIME_LIB", "/usr/lib/aarch64-linux-gnu/faketime/libfaketime.so.1")
CLOCK_FILE = os.environ.get("CLOCK_FILE", "/clock/faketime")
MAX_BODY = 200_000


class Service:
    def __init__(self, spec: dict, snapshots: str, app_log: str):
        self.spec, self.snapshots, self.app_log = spec, snapshots, app_log
        self.proc: subprocess.Popen | None = None
        self.lock = threading.Lock()
        self.clock = "2026-01-05 08:00:00"

    # -- environment
    def env(self) -> dict:
        env = dict(os.environ)
        env.update({k: str(v) for k, v in (self.spec.get("env") or {}).items()})
        if os.path.exists(FAKETIME_LIB):
            env.update({"LD_PRELOAD": FAKETIME_LIB, "FAKETIME_DONT_FAKE_MONOTONIC": "1", "FAKETIME_NO_CACHE": "1",
                        "FAKETIME_TIMESTAMP_FILE": CLOCK_FILE, "TZ": "UTC"})
        return env

    def set_clock(self, utc: str) -> str:
        t = datetime.strptime(utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        self.clock = t.strftime("%Y-%m-%d %H:%M:%S")
        os.makedirs(os.path.dirname(CLOCK_FILE), exist_ok=True)
        with open(CLOCK_FILE, "w") as f:
            f.write(self.clock + "\n")
        return self.clock

    # -- process
    def start(self) -> dict:
        log = open(self.app_log, "ab")
        self.proc = subprocess.Popen(self.spec["command"], shell=True, cwd=self.spec.get("workdir", "/app"),
                                     env=self.env(), stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.time() + float(self.spec.get("ready_timeout_s", 120))
        url = f"http://127.0.0.1:{self.spec['port']}{self.spec.get('ready_path', '/')}"
        while time.time() < deadline:
            if self.proc.poll() is not None:
                return {"ok": False, "error": f"service exited with {self.proc.returncode}"}
            try:
                urllib.request.urlopen(url, timeout=2)
                return {"ok": True}
            except urllib.error.HTTPError as e:
                if e.code < 500:
                    return {"ok": True}
            except Exception:
                pass
            time.sleep(0.3)
        return {"ok": False, "error": "service not ready in time"}

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, signal.SIGTERM)
                self.proc.wait(timeout=10)
            except Exception:
                try:
                    os.killpg(self.proc.pid, signal.SIGKILL)
                except Exception:
                    pass
        self.proc = None

    # -- data
    def _clear(self, path: str) -> None:
        if os.path.isdir(path):
            for name in os.listdir(path):
                p = os.path.join(path, name)
                shutil.rmtree(p) if os.path.isdir(p) and not os.path.islink(p) else os.remove(p)
        elif os.path.exists(path):
            os.remove(path)

    def reset(self) -> dict:
        self.stop()
        path = self.spec["data_path"]
        self._clear(path)
        if path.endswith("/") or not os.path.splitext(path)[1]:
            os.makedirs(path, exist_ok=True)
        return self.start()

    def snapshot(self, name: str) -> dict:
        self.stop()
        dest = os.path.join(self.snapshots, name)
        shutil.rmtree(dest, ignore_errors=True)
        os.makedirs(dest)
        src = self.spec["data_path"]
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(dest, "data"), symlinks=True)
        elif os.path.exists(src):
            shutil.copy2(src, os.path.join(dest, "data"))
        with open(os.path.join(dest, "clock"), "w") as f:
            f.write(self.clock)
        return self.start()

    def restore(self, name: str) -> dict:
        src = os.path.join(self.snapshots, name)
        if not os.path.isdir(src):
            return {"ok": False, "error": f"no setup named {name}"}
        self.stop()
        dest = self.spec["data_path"]
        self._clear(dest)
        if os.path.isdir(os.path.join(src, "data")):
            shutil.copytree(os.path.join(src, "data"), dest, symlinks=True, dirs_exist_ok=True)
        elif os.path.exists(os.path.join(src, "data")):
            shutil.copy2(os.path.join(src, "data"), dest)
        clock = open(os.path.join(src, "clock")).read().strip()
        self.set_clock(datetime.strptime(clock, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%dT%H:%M:%SZ"))
        return self.start()

    def run(self, command: str) -> dict:
        allowed = self.spec.get("setup_commands") or []
        if not any(command == a or command.startswith(a + " ") for a in allowed):
            return {"ok": False, "error": "not a setup command named in the interface reference", "allowed": allowed}
        p = subprocess.run(command, shell=True, cwd=self.spec.get("workdir", "/app"), env=self.env(),
                           capture_output=True, text=True, timeout=120)
        return {"ok": True, "exit": p.returncode, "output": (p.stdout + p.stderr)[-MAX_BODY:]}


def forward(port: int, req: dict) -> dict:
    method = (req.get("method") or "GET").upper()
    path = req.get("path") or "/"
    if not path.startswith("/"):
        path = "/" + path
    headers = dict(req.get("headers") or {})
    body = req.get("body")
    data = None
    if body not in (None, ""):
        if isinstance(body, (dict, list)):
            data = json.dumps(body).encode()
        else:
            data = str(body).encode()
        headers.setdefault("content-type", "application/json")
    r = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return {"status": resp.status, "body": resp.read(MAX_BODY).decode("utf-8", "replace")}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "body": e.read(MAX_BODY).decode("utf-8", "replace")}
    except Exception as e:
        return {"status": None, "error": f"{type(e).__name__}: {e}"}


def make_handler(service: Service, log_path: str, admin_token: str, state: dict):
    log_lock = threading.Lock()

    def log(entry: dict) -> int:
        with log_lock:
            state["seq"] += 1
            entry = {"seq": state["seq"], "batch": state["batch"], "clock": service.clock, **entry}
            with open(log_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
            return state["seq"]

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _reply(self, obj: dict, code: int = 200):
            data = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            try:
                n = int(self.headers.get("content-length") or 0)
                req = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return self._reply({"ok": False, "error": "bad request"}, 400)
            op = self.path.strip("/")
            admin = self.headers.get("x-admin-token") == admin_token
            if op == "admin":
                if not admin:
                    return self._reply({"ok": False, "error": "forbidden"}, 403)
                state.update({k: req[k] for k in ("batch", "allow_snapshot") if k in req})
                return self._reply({"ok": True, "seq": state["seq"]})
            with service.lock:
                if op == "clock":
                    try:
                        out = {"ok": True, "clock": service.set_clock(req.get("utc", ""))}
                    except ValueError:
                        out = {"ok": False, "error": "use a UTC time like 2026-01-05T08:00:00Z"}
                elif op == "http":
                    out = forward(service.spec["port"], req)
                elif op == "concurrent":
                    reqs = req.get("requests") or []
                    results: list = [None] * len(reqs)
                    barrier = threading.Barrier(len(reqs)) if reqs else None

                    def go(i, r):
                        barrier.wait()
                        results[i] = forward(service.spec["port"], r)
                    threads = [threading.Thread(target=go, args=(i, r)) for i, r in enumerate(reqs)]
                    for t in threads:
                        t.start()
                    for t in threads:
                        t.join()
                    out = {"ok": True, "results": results}
                elif op == "restart":
                    service.stop()
                    out = service.start()
                elif op == "reset":
                    out = service.reset()
                elif op == "restore":
                    out = service.restore(str(req.get("name", "")))
                elif op == "snapshot":
                    if not (admin or state["allow_snapshot"]):
                        out = {"ok": False, "error": "snapshots are not available now"}
                    else:
                        out = service.snapshot(str(req.get("name", "")))
                elif op == "run":
                    out = service.run(str(req.get("command", "")))
                elif op == "mark":
                    out = {"ok": True}
                else:
                    return self._reply({"ok": False, "error": f"unknown operation {op}"}, 404)
            seq = log({"op": op, "request": req, "response": out, "admin": admin or None})
            return self._reply({**out, "log_line": seq})

    return Handler


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--log", required=True)
    ap.add_argument("--snapshots", required=True)
    ap.add_argument("--app-log", default="/log/app.log")
    ap.add_argument("--clock", default="2026-01-05T08:00:00Z")
    args = ap.parse_args()
    spec = json.load(open(args.spec))
    os.makedirs(args.snapshots, exist_ok=True)
    os.makedirs(os.path.dirname(args.log), exist_ok=True)
    service = Service(spec, args.snapshots, args.app_log)
    service.set_clock(args.clock)
    started = service.reset()
    state = {"seq": 0, "batch": None, "allow_snapshot": False}
    handler = make_handler(service, args.log, os.environ.get("CONTROL_ADMIN_TOKEN", ""), state)
    with open(args.log, "a") as f:
        f.write(json.dumps({"seq": 0, "op": "start", "response": started}) + "\n")
    ThreadingHTTPServer(("0.0.0.0", args.port), handler).serve_forever()


if __name__ == "__main__":
    main()
