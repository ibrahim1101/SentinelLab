# SentinelLab Desktop — platform-first proof of concept

**Status: engineering spike, not a packaged installer.** The product target is a standalone Windows/Linux/macOS application. MongoDB Community Server is a **separate user-installed prerequisite**, not bundled or embedded.

## Current baseline

- Frontend: React 19, CRACO / Create React App (not Vite).
- Backend: Python FastAPI / Uvicorn.
- Persistence: MongoDB via Motor/PyMongo.
- Desktop shell: Tauri 2 alpha scaffold; Windows development window successfully launched on 2026-10-10.
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

Windows Tauri development window launch has been verified; no installer, authentication flow or bundled backend has been verified.

## Tauri 2 shell scaffold (2026-10-10)

A minimal Tauri 2 desktop window now lives in `desktop/src-tauri/`. **Experimental:** the Windows development window launched successfully, but no sidecar lifecycle, installer or release artifact exists yet. Bundling is intentionally disabled; the CSP is currently unset for the spike and MUST be hardened before distribution.

On Windows, install Rust toolchain, Node.js and Tauri system prerequisites (including WebView2 and Microsoft C++ build tools). With the existing frontend dependencies installed:

```powershell
cd "$HOME\SentinelLab\desktop"
npm install
npm run tauri:dev
```

The Tauri dev command starts React on localhost:3100 and sets `REACT_APP_BACKEND_URL=http://127.0.0.1:18765` for the development frontend. **The backend is NOT automatically started yet**; separately start the existing FastAPI backend and MongoDB. The frontend currently uses `REACT_APP_BACKEND_URL` at build time; configure it to match the running backend (the desktop launcher defaults to 127.0.0.1:18765). If login fails due to CORS/cookies, that is an expected unresolved integration issue, not a passing desktop test.

Do not run `tauri:build` expecting an installer: bundling is intentionally disabled until lifecycle, authentication and clean-host checks pass.

## Windows desktop alpha integration status (2026-10-10)

User-verified FastAPI `GET /api/health` returned `{ "status": "ok", "service": "sentinellab" }` and `GET /api/ready` returned `{ "ready": true }` with local MongoDB reachable. The development shell previously showed login HTTP 404 because the CRA frontend lacked `REACT_APP_BACKEND_URL`. Tauri dev configuration now supplies the loopback API origin; login, CORS and cookie behavior still require verification. Restart the Tauri dev process after pulling the change.

On Windows, backend dependencies were installed into a local `.venv` after excluding unavailable `emergentintegrations` and an Emergent-hosted LiteLLM wheel from a temporary dev requirements copy. This is not a vetted production dependency solution. Backend startup requires `MONGO_URL`, `DB_NAME`, `JWT_SECRET` and a unique `ADMIN_PASSWORD` of at least 12 characters; never commit secrets. Local frontend dependency compatibility edits and generated Tauri icons also need reproducible repository changes. Keep PR #1 unmerged and release NO-GO until gates pass.
