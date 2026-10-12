"""Local Windows desktop entry point for SentinelLab."""
import os
import secrets
from pathlib import Path

import uvicorn


def configure_environment():
    data = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "SentinelLab"
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
    os.environ.setdefault("CORS_ORIGINS", "http://tauri.localhost,tauri://localhost")


if __name__ == "__main__":
    configure_environment()
    uvicorn.run("server:app", host="127.0.0.1", port=18765, log_level="info")
