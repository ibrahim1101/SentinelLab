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
