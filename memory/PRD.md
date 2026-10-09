# SentinelLab — PRD

## Original Problem Statement
Build SentinelLab: a real, self-hostable Security Operations Center (SIEM), detection engineering, threat hunting and incident-response platform with real backend logic, persistent data, auth, event ingestion, a detection engine, investigations, analytics and reporting. Full 37-section spec; deliver in milestones. Adapted to the Emergent runtime (React + FastAPI + MongoDB) while keeping modular, swappable service boundaries.

## Architecture
- React (CRA) SPA with custom CSS-variable theming (4 themes), Recharts, Lucide.
- FastAPI backend, Motor/MongoDB, JWT + bcrypt auth, server-enforced RBAC (5 roles), audit logging.
- Modular backend: core (auth/db/rbac), parsers (multi-format normalization), detection (declarative engine), seed (synthetic Training Lab + built-in rules), ai_assistant (provider-independent adapter).
- Two isolated workspaces: Production + synthetic Training Lab. Everything org-scoped.

## User Personas
- SOC Analyst (triage alerts, hunt, investigate), SOC Manager (oversight, settings, reports), Administrator (users/roles), Auditor (read-only), Security researcher/student (Training Lab).

## Core Requirements (static)
Auth+RBAC, ingestion+normalization, searchable events, detection engine generating real alerts, alert lifecycle, threat hunting, investigations+evidence, reports, sources, settings, demo isolation, visual fidelity to Obsidian Security Command Center reference.

## Implemented (2026-10-09, Milestone 1)
- Auth (JWT/bcrypt), RBAC, multi-workspace isolation — tested.
- Overview dashboard with real computed metrics/charts.
- Event ingestion (JSON/JSONL/CSV/Syslog/CEF) + normalization — tested.
- Events Explorer + Event Details (overview/raw/normalized/related).
- Detection engine (match/threshold/frequency/indicator) + 8 built-in rules generating REAL alerts — tested.
- Alerts lifecycle, Threat Hunting, Detection Rules CRUD+backtest, Sources, Investigations+evidence(SHA256 chain), Reports (JSON/CSV), Settings(6 tabs/4 themes), AI assistant, global search, notifications, audit log.
- Backend tests: 26/26 passed. Frontend E2E: ~98%.

## Backlog (prioritized)
- P0: MITRE ATT&CK coverage page; Threat Intelligence IOC UI + CSV/STIX import.
- P1: Incident response playbooks + automation engine (approval gates); UEBA; network analytics graph; vulnerability management; Sigma YAML import UI; scheduled reports + PDF export.
- P2: TOTP MFA + WebAuthn UI; Docker Compose + GitHub Actions CI; load-testing scripts.

## Next Tasks
1. MITRE ATT&CK explorer/coverage computed from enabled rules + alert mappings.
2. Threat Intelligence IOC management + import.
3. Playbooks & automation with dry-run/approval.
4. Docker + CI + PDF export.
