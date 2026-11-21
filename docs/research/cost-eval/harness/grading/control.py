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
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FAKETIME_LIB = os.environ.get("FAKETIME_LIB", "/usr/lib/aarch64-linux-gnu/faketime/libfaketime.so.1")
CLOCK_FILE = os.environ.get("CLOCK_FILE", "/clock/faketime")
# Files a grader writes for the service to read, such as an import manifest. Beside the data, so restores keep them.
FIXTURES_DIR = os.environ.get("FIXTURES_DIR", "/cfg/fixtures")
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

    def _port_in_use(self) -> bool:
        with socket.socket() as s:
            s.settimeout(1)
            return s.connect_ex(("127.0.0.1", int(self.spec["port"]))) == 0

    def stop(self) -> None:
        # The process we started may be a shell whose child is the server. The shell dies at once while the server
        # shuts down at its own pace, still listening, so a readiness check right after would reach the old server.
        # Wait until the port is free, and kill the whole group if it doesn't free in time.
        if self.proc:
            pgid = self.proc.pid
            if self.proc.poll() is None:
                try:
                    os.killpg(pgid, signal.SIGTERM)
                    self.proc.wait(timeout=10)
                except Exception:
                    pass
            deadline = time.time() + 10
            while self._port_in_use() and time.time() < deadline:
                time.sleep(0.2)
            if self._port_in_use():
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except Exception:
                    pass
                deadline = time.time() + 5
                while self._port_in_use() and time.time() < deadline:
                    time.sleep(0.2)
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
        # the reference writes the data location as {DATA}; this instance's own takes its place
        command = command.replace("{DATA}", self.spec["data_path"])
        if not any(command == a or command.startswith(a + " ") for a in allowed):
            return {"ok": False, "error": "not a setup command named in the interface reference", "allowed": allowed}
        p = subprocess.run(command, shell=True, cwd=self.spec.get("workdir", "/app"), env=self.env(),
                           capture_output=True, text=True, timeout=120)
        return {"ok": True, "exit": p.returncode, "output": (p.stdout + p.stderr)[-MAX_BODY:]}


def _multipart(spec: dict) -> tuple[bytes, str]:
    """Build a multipart/form-data body from {"fields": {name: value}, "files": {name: {"name", "content", "type"}}}."""
    boundary = "----gtboundary7c3f"
    parts = []
    for name, value in (spec.get("fields") or {}).items():
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    for name, f in (spec.get("files") or {}).items():
        head = (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{f.get("name", "file.txt")}"\r\n'
                f'Content-Type: {f.get("type", "text/plain")}\r\n\r\n').encode()
        parts.append(head + str(f.get("content", "")).encode() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def describe_body(raw: bytes, content_type: str) -> dict:
    """A response body as the log keeps it: text when it is text; for anything else its size and type, and for a
    ZIP archive each member's name, size, and text."""
    out: dict = {}
    if raw[:4] == b"PK\x03\x04" or "zip" in content_type:
        import io
        import zipfile
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                members = []
                for info in z.infolist():
                    data = z.read(info) if info.file_size <= 20000 else b""
                    try:
                        text = data.decode("utf-8") if data else None
                    except UnicodeDecodeError:
                        text = None
                    members.append({"name": info.filename, "size": info.file_size, "text": text})
            out["body"] = f"(ZIP archive, {len(raw)} bytes, {len(members)} files)"
            out["zip"] = members
            return out
        except zipfile.BadZipFile:
            pass
    try:
        out["body"] = raw.decode("utf-8")
    except UnicodeDecodeError:
        out["body"] = f"(binary body, {len(raw)} bytes, content type {content_type or 'not given'})"
    return out


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    """Never follow a redirect: the 3xx response comes back as it is, so the log shows it."""

    def redirect_request(self, *a, **kw):
        return None


_OPENER = urllib.request.build_opener(_NoRedirects)
MAX_REDIRECTS = 10


def forward(port: int, req: dict) -> dict:
    """One request to the service. A redirect is never followed unless the request says `follow`: the 3xx response is
    the answer, and `redirects` records it (its status and Location). With `follow`, each hop is followed by hand,
    as a GET for 301, 302 and 303, and `redirects` lists every hop before the final response."""
    hops: list[dict] = []
    out = _forward_once(port, req)
    while req.get("follow") and out.get("status") in (301, 302, 303, 307, 308) and (out.get("headers") or {}).get("location"):
        hops.append({"status": out["status"], "location": out["headers"]["location"]})
        if len(hops) > MAX_REDIRECTS:
            return {"status": None, "error": f"redirect loop: more than {MAX_REDIRECTS} redirects", "redirects": hops,
                    "followed": True}
        nxt = dict(req, path=_local_path(out["headers"]["location"]))
        if out["status"] in (301, 302, 303):
            nxt.update(method="GET", body=None)
        out = _forward_once(port, nxt)
    if hops:
        out.update(redirects=hops, followed=True)
    elif 300 <= (out.get("status") or 0) < 400 and (out.get("headers") or {}).get("location"):
        out.update(redirects=[{"status": out["status"], "location": out["headers"]["location"]}], followed=False)
    return out


def _local_path(location: str) -> str:
    """A Location as a path on the service: an absolute URL loses its scheme and host."""
    if "://" in location:
        rest = location.split("://", 1)[1]
        return "/" + rest.split("/", 1)[1] if "/" in rest else "/"
    return location if location.startswith("/") else "/" + location


def _forward_once(port: int, req: dict) -> dict:
    method = (req.get("method") or "GET").upper()
    path = req.get("path") or "/"
    if not path.startswith("/"):
        path = "/" + path
    headers = dict(req.get("headers") or {})
    has_type = any(k.lower() == "content-type" for k in headers)
    body = req.get("body")
    data = None
    if isinstance(body, dict) and "__multipart__" in body:
        data, ctype = _multipart(body["__multipart__"])
        headers = {k: v for k, v in headers.items() if k.lower() != "content-type"}
        headers["Content-Type"] = ctype
    elif body not in (None, ""):
        data = json.dumps(body).encode() if isinstance(body, (dict, list)) else str(body).encode()
        if not has_type:
            headers["Content-Type"] = "application/json" if isinstance(body, (dict, list)) else "text/plain; charset=utf-8"
    keep = ("content-type", "content-disposition", "location")
    # A refused connection means the service never saw the request, so trying again a moment later is safe.
    for attempt in range(4):
        r = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method, headers=headers)
        try:
            with _OPENER.open(r, timeout=60) as resp:
                raw, rh = resp.read(MAX_BODY), resp.headers
                code = resp.status
            break
        except urllib.error.HTTPError as e:
            raw, rh, code = e.read(MAX_BODY), e.headers, e.code
            break
        except Exception as e:
            refused = isinstance(getattr(e, "reason", e), ConnectionRefusedError)
            if refused and attempt < 3:
                time.sleep(1)
                continue
            return {"status": None, "error": f"{type(e).__name__}: {e}"}
    out = {"status": code, **describe_body(raw, rh.get("content-type", "") if rh else "")}
    if raw and raw[0] >= 0x80:  # bytes before any text, which a decoded body hides: shown as they are
        out["starts_with"] = raw[:4].hex(" ")
    # Headers that can matter to a probe: where a download is named or redirected, and the type of anything not JSON.
    shown = {k: rh.get(k) for k in keep if rh and rh.get(k)}
    if rh and rh.get("content-length") and (method == "HEAD" or not raw):  # a size only the header gives
        shown["content-length"] = rh.get("content-length")
    if str(out.get("body", "")).lstrip().startswith(("{", "[")):
        shown.pop("content-type", None)
    if shown:
        out["headers"] = shown
    return out


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
                state.update({k: req[k] for k in ("batch", "allow_snapshot", "retain") if k in req})
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
                elif op == "retain":  # a preparation keeps its storage, under the name the harness gave it
                    if not state.get("retain"):
                        out = {"ok": False, "error": "nothing to retain now: only a preparation step retains storage"}
                    else:
                        out = {**service.snapshot(state["retain"]), "retained_as": state["retain"]}
                elif op == "run":
                    out = service.run(str(req.get("command", "")))
                elif op == "file":
                    name = os.path.basename(str(req.get("name", "")))
                    if not name or name.startswith("."):
                        out = {"ok": False, "error": "give a plain file name, such as records.json"}
                    else:
                        os.makedirs(FIXTURES_DIR, exist_ok=True)
                        path = os.path.join(FIXTURES_DIR, name)
                        data = str(req.get("content", "")).encode()
                        with open(path, "wb") as f:
                            f.write(data)
                        out = {"ok": True, "path": path, "bytes": len(data)}
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
    state = {"seq": 0, "batch": None, "allow_snapshot": False, "retain": None}
    handler = make_handler(service, args.log, os.environ.get("CONTROL_ADMIN_TOKEN", ""), state)
    with open(args.log, "a") as f:
        f.write(json.dumps({"seq": 0, "op": "start", "response": started}) + "\n")
    ThreadingHTTPServer(("0.0.0.0", args.port), handler).serve_forever()


if __name__ == "__main__":
    main()
