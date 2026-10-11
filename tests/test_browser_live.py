"""Optional live Playwright test: set SETUP_START_BROWSER_E2E=1.

CI stays dependency-free. This test starts one ephemeral loopback server and
uses a browser binary already available on the host; never downloads anything.
"""
import importlib.util
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import tempfile
from threading import Thread
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "setup-and-start" / "scripts" / "browser_audit.py"
spec = importlib.util.spec_from_file_location("browser_audit_live", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestPage(BaseHTTPRequestHandler):
    def do_GET(self):
        body = '<!doctype html><html lang="ar" dir="rtl"><title>Test</title><body><main><h1>مرحبا</h1><label for="q">بحث</label><input id="q"><button>بحث</button></main></body></html>'.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class BrowserIntegrationTest(unittest.TestCase):
    @unittest.skipUnless(os.getenv("SETUP_START_BROWSER_E2E") == "1",
                         "Requires explicitly enabled local Playwright + browser binary")
    def test_local_rtl_page(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), TestPage)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temp:
                report = mod.capture(f"http://127.0.0.1:{server.server_port}/", Path(temp))
                self.assertTrue(report["pass"], report)
                self.assertEqual(report["viewports"]["mobile"]["direction"], "rtl")
                self.assertTrue((Path(temp) / "mobile.png").exists())
                self.assertTrue((Path(temp) / "desktop.png").exists())
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
