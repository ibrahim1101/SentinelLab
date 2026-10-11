# SentinelLab

SentinelLab is an experimental SOC/SIEM application with a FastAPI backend, React frontend, MongoDB persistence, and a Tauri desktop project. **Pre-release software:** do not deploy as a production security monitoring system without further validation.

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

Target: `v0.1.0-alpha`. The release is **not yet published**. Desktop installer availability and full end-to-end SIEM testing are not yet verified. Known limitations and actual test results must be recorded before publishing release notes.

## Security

Use only synthetic or authorized test data. Never commit passwords, API keys, real customer logs, or incident evidence. Report vulnerabilities privately to the repository maintainer rather than publishing exploit details.
