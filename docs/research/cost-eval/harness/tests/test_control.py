"""Tests for grading/control.py and grading/gt against a tiny stand-in service, run locally."""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

GRADING = Path(__file__).resolve().parent.parent / "grading"

SERVICE = r'''
import json, os, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
DATA = os.path.join(os.environ["DATA_DIR"], "items.json")
def load():
    return json.load(open(DATA)) if os.path.exists(DATA) else []
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code); self.send_header("content-length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path in ("/old", "/hop"):  # a redirect, to a notice page by way of a second hop
            self.send_response(302 if self.path == "/old" else 301)
            self.send_header("location", "/hop" if self.path == "/old" else "/notice")
            self.send_header("content-length", "0"); self.end_headers(); return
        if self.path == "/loop":
            self.send_response(307); self.send_header("location", "/loop"); self.send_header("content-length", "0"); self.end_headers(); return
        if self.path == "/notice":
            b = b"This letter was taken down."; self.send_response(200); self.send_header("content-type", "text/plain")
            self.send_header("content-length", str(len(b))); self.end_headers(); self.wfile.write(b); return
        if self.path == "/lead":
            b = b"\xef\xbb\xbftitle,id\n"; self.send_response(200); self.send_header("content-type", "text/csv")
            self.send_header("content-length", str(len(b))); self.end_headers(); self.wfile.write(b); return
        if self.path == "/bundle":
            import io, zipfile
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("RD-0007.txt", "hello archive")
            raw = buf.getvalue()
            self.send_response(200); self.send_header("content-type", "application/zip")
            self.send_header("content-disposition", 'attachment; filename="bundle-1.zip"')
            self.send_header("content-length", str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        self.send(200, load())
    def do_POST(self):
        n = int(self.headers.get("content-length") or 0); raw = self.rfile.read(n)
        if self.path == "/echo":
            return self.send(200, {"content_type": self.headers.get("content-type"), "body": raw.decode()})
        item = json.loads(raw)
        items = load()
        if item in items: return self.send(409, {"error": "duplicate"})
        items.append(item); json.dump(items, open(DATA, "w")); self.send(201, item)
HTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
'''


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


class ControlTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        (cls.tmp / "app").mkdir()
        (cls.tmp / "app" / "service.py").write_text(SERVICE)
        (cls.tmp / "app" / "load.py").write_text("print('loaded')")
        cls.svc_port, cls.port = free_port(), free_port()
        spec = {"workdir": str(cls.tmp / "app"), "command": f"{sys.executable} service.py {cls.svc_port}",
                "env": {"DATA_DIR": str(cls.tmp / "data")}, "port": cls.svc_port, "data_path": str(cls.tmp / "data"),
                "ready_path": "/", "setup_commands": [f"{sys.executable} load.py"]}
        (cls.tmp / "spec.json").write_text(json.dumps(spec))
        env = dict(os.environ, CLOCK_FILE=str(cls.tmp / "clock" / "faketime"), FAKETIME_LIB="/nonexistent",
                   CONTROL_ADMIN_TOKEN="secret", FIXTURES_DIR=str(cls.tmp / "fixtures"))
        cls.log = cls.tmp / "log" / "exec.jsonl"
        cls.proc = subprocess.Popen([sys.executable, str(GRADING / "control.py"), "--spec", str(cls.tmp / "spec.json"),
                                     "--port", str(cls.port), "--log", str(cls.log), "--snapshots", str(cls.tmp / "snap"),
                                     "--app-log", str(cls.tmp / "app.log")], env=env)
        for _ in range(100):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{cls.port}/", timeout=1)
            except urllib.error.HTTPError:
                break
            except Exception:
                time.sleep(0.1)
        cls.genv = dict(os.environ, GT_CONTROL=f"http://127.0.0.1:{cls.port}")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(5)
        subprocess.run(["pkill", "-f", f"service.py {cls.svc_port}"])

    def gt(self, *args):
        return subprocess.run([sys.executable, str(GRADING / "gt"), *args], capture_output=True, text=True, env=self.genv).stdout

    def admin(self, op, payload):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/{op}", data=json.dumps(payload).encode(), method="POST",
                                     headers={"x-admin-token": "secret"})
        return json.loads(urllib.request.urlopen(req).read())

    def lines(self):
        return [json.loads(l) for l in self.log.read_text().splitlines()]

    def test_requests_restarts_setups_and_the_log(self):
        self.gt("reset")
        self.assertIn("status 201", self.gt("http", "POST", "/items", '{"name": "a"}'))
        self.assertIn("status 409", self.gt("http", "POST", "/items", '{"name": "a"}'))
        self.gt("restart")
        self.assertIn('"name": "a"', self.gt("http", "GET", "/items"))
        # snapshots only when the harness allows them, or by the harness itself
        self.assertIn("not available", self.gt("snapshot", "S0"))
        self.admin("admin", {"allow_snapshot": True, "batch": "setup"})
        self.gt("clock", "2026-01-05T09:30:00Z")
        self.assertIn('"ok": true', self.gt("snapshot", "S0"))
        self.admin("admin", {"allow_snapshot": False, "batch": "b1"})
        self.gt("reset")
        self.gt("clock", "2026-02-01T00:00:00Z")
        self.assertIn("[]", self.gt("http", "GET", "/items"))
        self.gt("restore", "S0")
        self.assertIn('"name": "a"', self.gt("http", "GET", "/items"))
        self.assertEqual((self.tmp / "clock" / "faketime").read_text().strip(), "2026-01-05 09:30:00")
        log = self.lines()
        self.assertTrue(any(e.get("op") == "http" and e["response"].get("status") == 409 for e in log))
        self.assertEqual(log[-1]["batch"], "b1")
        self.assertEqual(log[-1]["clock"], "2026-01-05 09:30:00")
        self.assertEqual([e["seq"] for e in log], list(range(len(log))))

    def test_a_redirect_is_never_followed_unless_asked_and_every_hop_is_logged(self):
        out = self.gt("http", "GET", "/old")
        self.assertIn("status 302", out)
        self.assertIn("location: /hop", out)
        self.assertNotIn("taken down", out)  # not followed: the redirect itself is the answer
        entry = [e for e in self.lines() if e.get("op") == "http"][-1]
        self.assertEqual((entry["response"]["status"], entry["response"]["redirects"], entry["response"]["followed"]),
                         (302, [{"status": 302, "location": "/hop"}], False))
        out = self.gt("http", "--follow", "GET", "/old")
        self.assertIn("redirected: 302 to /hop, 301 to /notice", out)
        self.assertIn("status 200", out)
        self.assertIn("taken down", out)
        entry = [e for e in self.lines() if e.get("op") == "http"][-1]
        self.assertTrue(entry["request"]["follow"])
        self.assertEqual((entry["response"]["status"], entry["response"]["followed"], entry["response"]["redirects"]),
                         (200, True, [{"status": 302, "location": "/hop"}, {"status": 301, "location": "/notice"}]))
        self.assertIn("redirect loop", self.gt("http", "--follow", "GET", "/loop"))
        self.gt("http", "GET", "/notice")
        self.assertNotIn("redirects", [e for e in self.lines() if e.get("op") == "http"][-1]["response"])

    def test_a_preparation_retains_its_storage_and_clock_where_it_says_to(self):
        self.assertIn("only a preparation step", self.gt("retain"))
        self.admin("admin", {"batch": "p00", "retain": "PREP-P-X"})
        self.gt("reset")
        self.gt("clock", "2026-01-05T08:00:00Z")
        self.gt("http", "POST", "/items", '{"name": "kept"}')
        self.assertIn('"retained_as": "PREP-P-X"', self.gt("retain"))
        self.gt("clock", "2026-01-12T08:00:00Z")  # a baseline afterwards, on the live copy
        self.gt("http", "POST", "/items", '{"name": "after"}')
        self.admin("admin", {"batch": None, "retain": None})
        snap = self.tmp / "snap" / "PREP-P-X"
        self.assertEqual((snap / "clock").read_text().strip(), "2026-01-05 08:00:00")
        self.assertIn("kept", (snap / "data" / "items.json").read_text())
        self.assertNotIn("after", (snap / "data" / "items.json").read_text())
        self.assertIn("only a preparation step", self.gt("retain"))

    def test_a_body_that_starts_with_bytes_outside_ascii_shows_them(self):
        out = self.gt("http", "GET", "/lead")
        self.assertIn("the body's first bytes: ef bb bf 74", out)
        self.assertEqual([e for e in self.lines() if e.get("op") == "http"][-1]["response"]["starts_with"], "ef bb bf 74")
        self.gt("http", "GET", "/notice")
        self.assertNotIn("starts_with", [e for e in self.lines() if e.get("op") == "http"][-1]["response"])

    def test_zip_responses_list_their_files_and_text(self):
        out = self.gt("http", "GET", "/bundle")
        self.assertIn("ZIP archive", out)
        self.assertIn("--- file in archive: RD-0007.txt", out)
        self.assertIn("hello archive", out)
        self.assertIn('filename="bundle-1.zip"', out)

    def test_uploads_and_content_types(self):
        out = self.gt("http", "POST", "/echo", "plain words", "Content-Type: text/plain")
        self.assertIn('"content_type": "text/plain"', out)
        out = self.gt("http", "POST", "/echo", json.dumps({"__multipart__": {"fields": {"title": "A letter"},
                      "files": {"file": {"name": "upload-7.txt", "content": "dear sir", "type": "text/plain"}}}}))
        self.assertIn("multipart/form-data", out)
        self.assertIn('filename=\\"upload-7.txt\\"', out)
        self.assertIn("dear sir", out)

    def test_a_grader_can_write_a_file_for_the_service_but_only_in_the_fixtures_folder(self):
        out = json.loads(self.gt("file", "../../escape.json", '[{"title": "Marigold"}]'))
        self.assertEqual(out["path"], str(self.tmp / "fixtures" / "escape.json"))
        self.assertEqual((self.tmp / "fixtures" / "escape.json").read_text(), '[{"title": "Marigold"}]')
        self.assertIn("plain file name", self.gt("file", ".hidden", "x"))

    def test_only_named_setup_commands_run(self):
        self.assertIn("loaded", self.gt("run", f"{sys.executable} load.py"))
        self.assertIn("not a setup command", self.gt("run", "cat service.py"))

    def test_concurrent_requests_both_get_answers(self):
        self.gt("reset")
        reqs = [{"method": "POST", "path": "/items", "body": {"name": "z"}}] * 2
        out = self.gt("concurrent", json.dumps(reqs))
        self.assertEqual(out.count("--- request"), 2)
        self.assertIn("status 201", out)

    def test_admin_needs_the_token_and_bad_input_is_refused(self):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}/admin", data=b'{"batch":"x"}', method="POST")
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(req)
        self.assertIn("UTC time", self.gt("clock", "tomorrow"))
        self.assertIn("Usage", self.gt())


SLOW_STOP = r'''
import json, signal, sys, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        b = b"{}"; self.send_response(200)
        self.send_header("content-length", str(len(b))); self.end_headers(); self.wfile.write(b)
srv = HTTPServer(("127.0.0.1", int(sys.argv[1])), H)
def slow_exit(*a):
    def go():
        time.sleep(1.5); srv.shutdown(); srv.server_close(); sys.exit(0)
    threading.Thread(target=go).start()
signal.signal(signal.SIGTERM, slow_exit)
srv.serve_forever()
'''


class SlowStopTest(unittest.TestCase):
    """A service started through a shell keeps listening for a while after it's told to stop. A restore must not report
    ready until the new process answers, and the first request after it must reach the service."""

    def test_the_first_request_after_a_restore_reaches_the_new_service(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "app").mkdir()
        (tmp / "app" / "slow.py").write_text(SLOW_STOP)
        svc_port, port = free_port(), free_port()
        # the trailing "; true" keeps the shell alive as the parent, as many start commands do
        spec = {"workdir": str(tmp / "app"), "command": f"{sys.executable} slow.py {svc_port}; true",
                "env": {}, "port": svc_port, "data_path": str(tmp / "data"), "ready_path": "/"}
        (tmp / "spec.json").write_text(json.dumps(spec))
        env = dict(os.environ, CLOCK_FILE=str(tmp / "clock" / "faketime"), FAKETIME_LIB="/nonexistent",
                   CONTROL_ADMIN_TOKEN="secret")
        proc = subprocess.Popen([sys.executable, str(GRADING / "control.py"), "--spec", str(tmp / "spec.json"),
                                 "--port", str(port), "--log", str(tmp / "log" / "exec.jsonl"), "--snapshots",
                                 str(tmp / "snap"), "--app-log", str(tmp / "app.log")], env=env)
        try:
            genv = dict(os.environ, GT_CONTROL=f"http://127.0.0.1:{port}")
            gt = lambda *a: subprocess.run([sys.executable, str(GRADING / "gt"), *a], capture_output=True, text=True,
                                           env=genv).stdout
            for _ in range(100):
                if "status 200" in gt("http", "GET", "/"):
                    break
                time.sleep(0.1)
            req = urllib.request.Request(f"http://127.0.0.1:{port}/admin", data=json.dumps(
                {"allow_snapshot": True, "batch": "setup"}).encode(), method="POST", headers={"x-admin-token": "secret"})
            urllib.request.urlopen(req).read()
            self.assertIn('"ok": true', gt("snapshot", "S0"))
            self.assertIn('"ok": true', gt("restore", "S0"))
            time.sleep(2)  # past the old server's slow exit, so only the new one can answer
            self.assertIn("status 200", gt("http", "GET", "/"))
        finally:
            proc.terminate()
            proc.wait(5)
            subprocess.run(["pkill", "-f", f"slow.py {svc_port}"])


if __name__ == "__main__":
    unittest.main()
