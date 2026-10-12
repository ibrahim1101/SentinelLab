"""SentinelLab desktop backend entry point (development/packaging spike).

Run from the repository root:
    python desktop/backend_launcher.py
The future desktop shell should own this process and terminate it on exit.
MongoDB must be installed/configured separately.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    backend = root / "backend"
    sys.path.insert(0, str(backend))

    host = os.environ.get("SENTINELLAB_DESKTOP_HOST", "127.0.0.1")
    if host not in ("127.0.0.1", "::1"):
        raise SystemExit("Desktop API must bind to loopback only")

    port_raw = os.environ.get("SENTINELLAB_DESKTOP_PORT", "18765")
    try:
        port = int(port_raw)
    except ValueError as exc:
        raise SystemExit("Invalid desktop API port") from exc
    if not 1024 <= port <= 65535:
        raise SystemExit("Desktop API port must be between 1024 and 65535")

    import uvicorn

    uvicorn.run("server:app", host=host, port=port, reload=False, workers=1,
                access_log=False)


if __name__ == "__main__":
    main()
