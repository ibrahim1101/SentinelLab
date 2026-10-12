# SentinelLab

SentinelLab is an experimental SOC/SIEM application with a FastAPI backend, React frontend, MongoDB persistence, and a Tauri desktop project. **Pre-release software:** do not deploy as a production security monitoring system without further validation.

## Windows desktop prerequisite (alpha installer)

**MongoDB Community Server is required separately.** Install MongoDB Community Server for Windows using the [official MongoDB installation guide](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-windows/). Configure it as a Windows service and ensure it is running on `127.0.0.1:27017`. The Windows alpha installer bundles the FastAPI backend and has been manually tested for local startup and shutdown. MongoDB is **not** bundled; install and run it separately. Linux and macOS desktop packages have passed CI packaging and backend import smoke tests but have **not** been installed or tested on physical Linux/macOS machines. Keep MongoDB bound to localhost for local-only testing and never expose an unauthenticated database to a network.

## Quick start (Docker)

Prerequisites: Docker Desktop with Docker Compose.

1. Clone this repository and enter its directory.
2. Copy `.env.example` to `.env`. Set strong, unique `JWT_SECRET` and `ADMIN_PASSWORD` values. Keep `.env` private.
3. Run `docker compose up -d --build --wait`.
4. Open http://localhost:8080 in your browser. The backend is exposed locally at http://127.0.0.1:8000.

For diagnostics, use `docker compose ps` and `docker compose logs --tail=100`. To stop the stack without deleting stored MongoDB data, run `docker compose down`. **Do not use `docker compose down -v` unless you intend to delete the database volume.**

## Release validation

The GitHub Actions workflows include isolated login-security regressions, disposable MongoDB concurrency tests, Phase 1 security checks, and a Docker smoke test. CI success does not substitute for hands-on validation of log ingestion, detection rules, alerts, investigations, playbooks, and desktop packaging.

## Release status

Target: `v0.1.0-alpha`. The release is **not yet published**. Windows NSIS installation and basic authentication, MongoDB status, AI assistant, and Discord webhook behavior have been manually exercised. Linux x64 (.deb, .AppImage) and macOS Intel/Apple Silicon (.dmg) packages passed CI on 2026-10-12, but runtime behavior on those operating systems remains **untested**. These builds are unsigned; OS security prompts may appear. Full end-to-end SIEM testing is incomplete. See `docs/ALPHA_RELEASE_NOTES.md` for scope and limitations.

## Security

Use only synthetic or authorized test data. Never commit passwords, API keys, real customer logs, or incident evidence. Report vulnerabilities privately to the repository maintainer rather than publishing exploit details.
