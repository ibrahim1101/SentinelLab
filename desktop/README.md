# SentinelLab Desktop — platform-first proof of concept

**Status: engineering spike, not a packaged installer.** The product target is a standalone Windows/Linux/macOS application. MongoDB Community Server is a **separate user-installed prerequisite**, not bundled or embedded.

## Current baseline

- Frontend: React 19, CRACO / Create React App (not Vite).
- Backend: Python FastAPI / Uvicorn.
- Persistence: MongoDB via Motor/PyMongo.
- Desktop shell candidate: Tauri; not installed or configured in this spike.
- This directory contains a loopback-only backend launcher to establish the future sidecar contract. It is **not** yet a self-contained binary, and requires Python and the backend dependencies for development.

## Development-only launcher

From repository root, with the existing backend environment configured and MongoDB available:

```powershell
python desktop/backend_launcher.py
```

Defaults to `127.0.0.1:18765`. Optional environment variables:
`SENTINELLAB_DESKTOP_HOST=127.0.0.1` (or `::1`) and
`SENTINELLAB_DESKTOP_PORT=18765`. Non-loopback binding is rejected.

Test `http://127.0.0.1:18765/api/health` only after configuring backend secrets and MongoDB according to the existing project environment. Do not treat this as proof of a packaged app.

## Next implementation steps

1. Build Tauri shell around existing CRACO production build (avoid assuming Vite).
2. Define secure origin, API proxy, CORS and authentication-cookie behavior for a desktop webview; existing `Secure; SameSite=None` cookie settings require special attention with localhost HTTP.
3. Package backend with PyInstaller or equivalent **per OS**; manage process startup, readiness, shutdown, port collisions and crash handling. Avoid spawning arbitrary user-controlled executables.
4. Verify user-installed MongoDB connection and authenticated database access; add first-run connection wizard later.
5. Test Windows first, then Linux, then macOS; verify clean-host installation and platform-specific signing/packaging.

No platform is yet verified, and no installer should be published from this spike.
