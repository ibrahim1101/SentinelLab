# SentinelLab — Project Handoff

> This document makes the project resumable from the repository alone, without prior conversation history.
> Update at the end of every development phase.

## 1. Current Architecture & Technology Stack
- **Frontend:** React 19 (CRA/craco), React Router 7, TanStack Query, Recharts, Tailwind (custom CSS-variable theming), Lucide icons, Sonner toasts.
- **Backend:** FastAPI (Python), Motor (async MongoDB), PyJWT, bcrypt, emergentintegrations (AI).
- **Database:** MongoDB (used as system-of-record AND search adapter; a clean interface is preserved so OpenSearch/Postgres can be swapped in).
- **Auth:** JWT (Bearer token in body + httpOnly cookie), bcrypt hashing, server-enforced RBAC, login rate-limit/lockout.
- **AI:** Provider-independent adapter (`ai_assistant.py`), default uses Emergent LLM key (OpenAI gpt-5.4). Disabled gracefully if unconfigured.

> NOTE: The spec's preferred stack (Postgres/OpenSearch/Redis/Celery/Alembic) is not the Emergent runtime. This build implements equivalent behavior on React/FastAPI/MongoDB. Service boundaries (parsers, detection, ingestion, search adapter) are modular so they can be containerized/swapped.

## 2. Implemented Features & Working Status
See `FEATURE_MATRIX.md`. Milestone 1 (5 core groups) implemented:
- Auth + RBAC + multi-workspace isolation — **Tested (backend)**
- Overview Dashboard (real computed KPIs/charts) — **Implemented**
- Event Ingestion (JSON/JSONL/CSV/Syslog/CEF) + normalization — **Tested (backend)**
- Events Explorer + Event Details (overview/raw/normalized/related) — **Implemented**
- Detection Engine (match/threshold/frequency/indicator) + 8 built-in rules — **Tested (backend: generates real alerts)**
- Alerts lifecycle (status/assign/comment/audit) — **Implemented**
- Threat Hunting (safe query parser, top entities, timeline) — **Implemented**
- Detection Rules mgmt (CRUD, toggle, backtest) — **Implemented**
- Sources & Ingestion (CRUD, token-once, upload) — **Implemented**
- Investigations (cases, notes, tasks, evidence + chain-of-custody) — **Implemented**
- Reports (generate + JSON/CSV download) — **Implemented**
- Settings (6 tabs, 4 themes, demo reset, admin users/audit/health) — **Implemented**
- AI Assistant (explain alert / ask) — **Implemented**
- Global search, notifications — **Implemented**

## 3. Database Schema (MongoDB collections)
`users, organizations, sources, events, detection_rules, alerts, investigations, indicators, reports, notifications, saved_searches, audit_logs, parser_errors, settings, login_attempts`.
Keyed by string `id` (uuid4). Everything org-scoped via `org_id`. See `DATABASE_SCHEMA.md`.
Indexes created on startup: users.email (unique), users.id, events(org_id+timestamp), events(org_id+category), alerts(org_id+status), login_attempts.identifier.

## 4. Important Files
- `backend/core.py` — db, auth, RBAC, audit.
- `backend/parsers.py` — multi-format parse + normalization.
- `backend/detection.py` — detection engine.
- `backend/seed.py` — built-in rules + synthetic Training Lab.
- `backend/ai_assistant.py` — AI adapter.
- `backend/server.py` — all API routes + startup seeding.
- `frontend/src/pages/*` — one page per SOC view.
- `frontend/src/components/Layout.jsx` — sidebar + topbar.
- `frontend/src/context/*` — Auth, Theme, Workspace.

## 5. API Endpoints
Prefix `/api`. Auth: `/auth/{register,login,logout,me}`. Core: `/dashboard/overview`, `/events*`, `/ingest*`, `/rules*`, `/alerts*`, `/hunt*`, `/sources*`, `/investigations*`, `/reports*`, `/notifications*`, `/search`, `/settings`, `/admin/*`, `/ai/ask`, `/demo/reset`, `/workspaces`, `/me/{theme,workspace}`. Health: `/api/health`, `/api/ready`.

## 6. Tests Executed & Results
- Backend smoke (curl): health, login, overview, alerts, rules verified. Detection engine produced 8 real alerts from seeded telemetry. See DEVELOPMENT_HISTORY.
- Full testing-agent run: see `TESTING_HISTORY.md`.

## 7. Bugs Discovered & Resolved
See `FAILURES_AND_FIXES.md`.

## 8. Outstanding Issues / Not Yet Built (later milestones)
MITRE ATT&CK explorer page, UEBA, network graph, vulnerability mgmt, playbooks/automation engine UI, STIX import, TOTP MFA UI, scheduled reports, PDF export (JSON/CSV done), Sigma YAML import UI, Docker/CI files.

## 9. External Services & Config
- `backend/.env`: MONGO_URL, DB_NAME, JWT_SECRET, ADMIN_EMAIL, ADMIN_PASSWORD, EMERGENT_LLM_KEY, CORS_ORIGINS.
- Optional TI/Slack/SMTP integrations are adapter-ready, disconnected until keys provided.

## 10. Git Branch / Commit
Not yet initialized in repo by agent. (Emergent-managed.)

## 11. Exact Next Implementation Tasks
1. MITRE ATT&CK coverage page (compute from enabled rules + alert mappings).
2. Threat Intelligence IOC management page + CSV/STIX import.
3. Playbooks & automation engine with approval gates.
4. Docker Compose + GitHub Actions CI + PDF report export.

## 12. Phase 1 security stabilization (2026-10-09)
Branch `fix/phase1-security-regressions` hardens AI supporting-event workspace filtering, bounds user-provided regex matching, escapes Events Explorer literal searches, and prevents nonpersistent detection runs from modifying event/rule records. Dedicated regression tests added. These changes require independent CI and integration verification before production deployment. Milestones 2 and 3 are implemented per development history; earlier sections 8 and 11 are historical and superseded by the feature matrix.


## 13. Current handoff — 2026-10-10 (supersedes historical backlog)
- **Repository/branch:** private `ibrahim1101/SentinelLab` on `fix/phase1-security-regressions`; PR #1 open and unmerged. The older “not initialized” branch note and milestone 2/3 pending lists above are historical, not current status.
- **CI:** verified green on `d2edbb5` in workflow runs 37991302420 and 37991298108. Changes made afterward need their own verification.
- **Local preview:** Docker Compose Mongo/API/React frontend. User successfully built all images using public ECR mirrors when Docker Hub auth timed out; port 8080 was occupied and local override to port 8081 was recommended. Local host URL `http://localhost:8081` depends on that override.
- **Runtime issue:** live manual Malware Alert Triage with approved EDR action yielded `NoneType` IOC enrichment failure; audit-only disconnected EDR action incorrectly said `ok`. Fixed in `backend/playbooks.py` commit `f1b7223`: no-indicator enrichment skips, disconnected external actions marked `simulated`, aggregate statuses improved. Tests/browser retest pending. No actual EDR isolation was performed.
- **Public documentation:** first-edition 9-page, 22-section `SentinelLab_Complete_User_Guide_v1.pdf` created for download. The public Portfolio repo `ibrahim1101/Portfolio` `main` commit `112e91b` updated `sentinellab.html` to describe the developer preview and link `docs/SentinelLab_Complete_User_Guide_v1.pdf` in project actions and journey section. **PDF binary upload to Portfolio is not confirmed**; links are pending publication and validation. Do not publicly expose private repo materials or secrets.
- **Immediate P0:** test the playbook null-alert, simulated action and aggregate statuses; validate frontend labels; add deterministic applying-state approval reconciliation tests including five-minute server guard.
- **P1:** 15-module browser QA; publish/verify guide; improve PDF with validated controls/screenshots; Docker onboarding.
- **P2/P3:** richer IOC enrichment, integration adapters and production hardening, then advanced SOC features.
- **Process:** keep `docs/ENGINEERING_JOURNEY.md` current with commits, failures, test evidence and limitations; never merge PR #1 without explicit authorization.


### 2026-10-10 — Active development: playbook simulation UI clarity
- Commit [86dfb06](https://github.com/ibrahim1101/SentinelLab/commit/86dfb0660f3080185946ac2578435bdb2ff1c88c) on `fix/phase1-security-regressions` changed the run button to **Record Run**, clarified disconnected EDR/firewall/email/IdP simulation, renamed persisted history labels, and added status-specific notifications for failed, pending-approval, skipped and simulated runs.
- GitHub accepted the commit. Browser/UI automated verification and post-commit CI are **not yet verified**; no external containment was performed.
- Next: locate active workflow file, include playbook regression tests in CI, run test suite, address tenant-scoped investigation writes and production-access applying-state reconciliation tests. PR #1 must remain unmerged.


### 2026-10-10 — CI recheck and playbook test discovery repair
- [Workflow run 38035266786](https://github.com/ibrahim1101/SentinelLab/actions/runs/38035266786): static-security and docker-smoke both **passed**. Static job log confirms **13 passed, 8 warnings**, but command only named security, detection and alert-tenant suites; playbook tests were **not** executed.
- Commit [88456cc](https://github.com/ibrahim1101/SentinelLab/commit/88456cc508ab82681d3a8aa8070e5e8367ef0fb6) adds explicit backend import path and isolated Mongo environment defaults to `backend/tests/test_playbook_regressions.py` to support standalone pytest collection. **Not yet tested in CI.**
- The active workflow file path was not located through attempted `.github/workflows/` filenames; do not claim playbook tests run until the actual workflow is updated and logs prove it. Continue with workflow discovery, tenant-scoping security fix and reconciliation tests. PR #1 stays unmerged.


### 2026-10-10 — Cross-tenant playbook regression assertions
- [Run 38036778445](https://github.com/ibrahim1101/SentinelLab/actions/runs/38036778445): static-security **success**, docker-smoke **failure** while pulling MongoDB image (`toomanyrequests: Rate exceeded`); smoke failure is registry infrastructure, not evidence of failed app assertions.
- Commit [739441c](https://github.com/ibrahim1101/SentinelLab/commit/739441c0e91b53a6008164918d34d81ef4a55494) adds two mocked async database-call regression tests for org-scoped alert linking and investigation assignment/task writes. Not yet observed executing in CI; explicit workflow test list still omits playbook tests.
- Pending: locate/update actual CI workflow, run new tests, add production-access reconciliation integration coverage, and verify Portfolio guide public URL. PR #1 remains unmerged.


### 2026-10-10 — Dedicated playbook CI workflow added
- Commit [94e5d1c](https://github.com/ibrahim1101/SentinelLab/commit/94e5d1cab39f092f49b01ece47ebde6ed9b1be1d) created `.github/workflows/playbook-regressions.yml` on `fix/phase1-security-regressions`, installing isolated dependencies and explicitly running `python -m pytest -q backend/tests/test_playbook_regressions.py`.
- Previous Phase 1 [run 38036818916](https://github.com/ibrahim1101/SentinelLab/actions/runs/38036818916) passed both jobs; its static test command still ran 13 other tests, not playbook regressions.
- Dedicated workflow execution result **not yet confirmed**. Next: verify new workflow appears and passes, fix any import/dependency/assertion errors, then extend production-access reconciliation tests. PR #1 stays unmerged.


### 2026-10-10 — Intermittent Docker registry failure and CI tenant guard
- [Phase 1 run 38037758618](https://github.com/ibrahim1101/SentinelLab/actions/runs/38037758618): static-security passed; docker-smoke failed before application assertions due to MongoDB image registry `toomanyrequests: Rate exceeded`. [Run 38037748002](https://github.com/ibrahim1101/SentinelLab/actions/runs/38037748002) passed both jobs. No Docker retry change has been deployed; intermittent registry failure remains open.
- Commit [35e8823](https://github.com/ibrahim1101/SentinelLab/commit/35e882361c6d5e5b3a4e295061aeaeeac8350f14) adds an AST-based playbook tenant-write guard to the **existing** static-security test file, which the Phase 1 workflow already runs. This is source-level regression coverage, not a substitute for mocked playbook execution tests.
- Dedicated playbook workflow file exists but its successful execution remains unconfirmed. Next: inspect its Actions registration/run and verify new static guard; implement reliable image-pull retries in actual CI workflow after identifying its path. PR #1 remains unmerged.
