# SentinelLab

**Experimental cross-platform SOC/SIEM desktop alpha** — React + FastAPI + MongoDB + Tauri 2. SentinelLab provides security-event ingestion, detection, alerts, investigations, threat hunting, IOC workflows, MITRE ATT&CK coverage, playbooks, reporting, AI assistance, and outgoing notifications. Features have different levels of test coverage; this is **not a production-certified SIEM**.

[Release draft / releases](https://github.com/ibrahim1101/SentinelLab/releases) · [Engineering journey](docs/ENGINEERING_JOURNEY.md) · [Alpha release notes](docs/ALPHA_RELEASE_NOTES.md) · [Release gate](docs/RELEASE_GATE_V0.1.0_ALPHA.md) · [Bug reports](https://github.com/ibrahim1101/SentinelLab/issues)

## v0.1.0-alpha platform matrix

| Platform | Package | Evidence |
| --- | --- | --- |
| Windows x64 | Unsigned NSIS `.exe` | CI packaging passed; user manually verified installation, login, MongoDB status, AI, Discord webhook and shutdown |
| Linux x64 | Unsigned `.deb`, `.AppImage` | CI packaging and backend import smoke passed; **runtime not tested** |
| macOS Intel | Unsigned `.dmg` | CI packaging and backend import smoke passed; **runtime not tested** |
| macOS Apple Silicon | Unsigned `.dmg` | CI packaging and backend import smoke passed; **runtime not tested** |

**MongoDB Community Server is required separately on desktop.** The desktop package bundles the Python API backend, **not** MongoDB. For local evaluation, run MongoDB bound to `127.0.0.1:27017`. Do not expose an unauthenticated MongoDB database to a network. The installers are unsigned and macOS packages are not notarized.

## Current functionality

- **SOC workflows:** dashboards, events explorer, JSON/JSONL/CSV/Syslog/CEF ingestion, normalization, detection rules, alert triage, investigations, evidence, threat hunting, saved hunts, reports and notifications.
- **Threat intelligence and response:** manually managed indicators, CSV/STIX IOC imports, ATT&CK technique coverage, investigation graph, detection replay, pipeline observatory, and approval-gated incident response playbooks. External containment adapters are **not** live EDR/firewall actions.
- **Security:** organization-scoped access, role-aware authentication, account lockout/disable/recovery, audit trail and CI security regressions.
- **AI:** configurable local Ollama/LM Studio or OpenAI-compatible providers; product guidance and alert assistance. Ollama/model installation is optional and separate.
- **Outgoing notifications:** generic HTTPS webhooks and Discord, Slack, Teams payload formats; actual Discord delivery has been manually confirmed. VirusTotal, AbuseIPDB and SMTP currently appear as **planned provider placeholders**, not working integrations.

## Desktop alpha quick start

1. Install and start MongoDB Community Server. For Windows, use the [official MongoDB Windows guide](https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-windows/).
2. When the prerelease is published, download the installer matching your OS/CPU from [GitHub Releases](https://github.com/ibrahim1101/SentinelLab/releases). Verify the attached `SHA256SUMS.txt`.
3. Install and launch SentinelLab. Configure your local database and initial administrator account according to the app's setup prompts. Do not expose the local API or database to the public internet.
4. Optionally configure AI and webhooks in Settings → Integrations. Never post credentials or unredacted incident data in public issues.

**Status:** `v0.1.0-alpha` is a **draft prerelease**, not publicly published as of the latest repository audit (2026-10-12). The draft contains Windows, Linux and macOS packages and a checksum manifest. The draft packages were built from the verified development tip; successful `main` rebuilds also exist. See [release notes](docs/ALPHA_RELEASE_NOTES.md) for caveats.

## Developer / Docker quick start

Requires Docker Desktop with Compose. Clone `main`, copy `.env.example` to `.env`, set strong unique `JWT_SECRET` and `ADMIN_PASSWORD`, and keep `.env` private.

```bash
git clone https://github.com/ibrahim1101/SentinelLab.git
cd SentinelLab
cp .env.example .env
# Edit .env to set strong secrets
docker compose up -d --build --wait
docker compose ps
docker compose logs --tail=100
# Open http://localhost:8080
docker compose down
```

The backend is available locally at `http://127.0.0.1:8000` for the Docker stack. **Never run `docker compose down -v` unless you intend to delete database volumes.**

## Verification and development history

The single active branch is `main`; PR #1 was merged. [Windows CI #38265416099](https://github.com/ibrahim1101/SentinelLab/actions/runs/38265416099) and [Linux/macOS CI #38265421720](https://github.com/ibrahim1101/SentinelLab/actions/runs/38265421720) passed. Login security [#38265992950](https://github.com/ibrahim1101/SentinelLab/actions/runs/38265992950) and Phase 1 security [#38265992719](https://github.com/ibrahim1101/SentinelLab/actions/runs/38265992719) passed. CI does not prove every feature works end to end.

Read [Engineering Journey](docs/ENGINEERING_JOURNEY.md), [Development History](docs/DEVELOPMENT_HISTORY.md), [Feature Matrix](docs/FEATURE_MATRIX.md), and [Alpha Release Notes](docs/ALPHA_RELEASE_NOTES.md) for detailed features, fixes, known issues and next steps.

## Security and reporting

Use only synthetic or authorized data. Do not deploy as a production security monitoring system without further validation. Report vulnerabilities privately to the maintainer, not as public exploit details. When reporting bugs, include OS, package type, reproduction steps and **redacted** logs.
