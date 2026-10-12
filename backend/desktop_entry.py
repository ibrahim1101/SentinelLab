"""Cross-platform local desktop entry point for SentinelLab."""
import os
import secrets
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import uvicorn


def configure_environment():
    if sys.platform == "win32":
        data = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "SentinelLab"
    elif sys.platform == "darwin":
        data = Path.home() / "Library" / "Application Support" / "SentinelLab"
    else:
        data = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "SentinelLab"
    data.mkdir(parents=True, exist_ok=True)
    secret_path = data / "jwt.secret"
    if "JWT_SECRET" not in os.environ:
        if not secret_path.exists():
            secret_path.write_text(secrets.token_urlsafe(48), encoding="utf-8")
        os.environ["JWT_SECRET"] = secret_path.read_text(encoding="utf-8").strip()
    os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017/?serverSelectionTimeoutMS=3000")
    os.environ.setdefault("DB_NAME", "sentinellab")
    os.environ.setdefault("ENABLE_DEMO_ACCOUNTS", "false")
    os.environ["SENTINELLAB_DESKTOP"] = "1"
    os.environ.setdefault("CORS_ORIGINS", "http://tauri.localhost,tauri://localhost,https://tauri.localhost")


class DesktopStatusHandler(BaseHTTPRequestHandler):
    """Read-only diagnostic endpoint; intentionally independent of FastAPI startup."""

    def do_GET(self):
        if self.path != "/status":
            self.send_error(404)
            return
        import json
        from pymongo import MongoClient
        from pymongo.errors import PyMongoError
        installed = None
        if sys.platform == "win32":
            import subprocess
            try:
                result = subprocess.run(["sc.exe", "query", "MongoDB"], capture_output=True,
                                        text=True, timeout=2, creationflags=0x08000000)
                installed = result.returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                installed = None
        reachable = False
        try:
            client = MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=1200,
                                 connectTimeoutMS=1200)
            try:
                client.admin.command("ping")
                reachable = True
            finally:
                client.close()
        except PyMongoError:
            pass
        payload = json.dumps({"backend": "running", "mongodb_installed": installed,
                              "mongodb_reachable": reachable,
                              "setup_available": reachable}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "http://tauri.localhost")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        pass


def start_diagnostics():
    server = ThreadingHTTPServer(("127.0.0.1", 18766), DesktopStatusHandler)
    threading.Thread(target=server.serve_forever, daemon=True, name="desktop-status").start()


if __name__ == "__main__":
    configure_environment()
    if "--self-test" in sys.argv:
        import server
        if server.app is None:
            raise RuntimeError("Bundled FastAPI application is unavailable")
        print("SentinelLab bundled backend import OK")
        sys.exit(0)
    start_diagnostics()
    uvicorn.run("server:app", host="127.0.0.1", port=18765, log_level="info")
