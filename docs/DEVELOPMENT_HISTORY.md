# Development History

## 2026-10-09 — Milestone 1: Core SOC platform
(see entry below — initial 5 core groups)

## 2026-10-09 — Milestone 2: MITRE coverage, Threat Intel IOCs, Playbooks
**Features added:**
- **MITRE ATT&CK Coverage** (`mitre_data.py`, `/api/mitre/coverage`, `pages/Mitre.jsx`): curated ATT&CK subset (12 tactics / 36 techniques). Coverage computed live from *enabled* rules' technique mappings (sub-techniques roll up to parents) and alert counts per technique. Heatmap matrix (covered / active-alerts / gap), technique detail with mapped rules, and gap list. No fabricated percentages.
- **Threat Intelligence IOCs** (`/api/indicators*`, `pages/ThreatIntel.jsx`): manual add, CSV import, STIX 2.1 bundle import (pattern parser), per-type stats, false-positive handling, delete, and `GET /indicators/{id}/hits` showing real matching events. `POST /indicators/scan` evaluates active indicators (via the indicator detection rule) against stored events and generates real alerts. New IOCs auto-match incoming events through the existing ingest-time indicator rule.
- **Incident Response Playbooks** (`playbooks.py`, `/api/playbooks*`, `pages/Playbooks.jsx`): 7 built-in playbooks. Execution engine supports **dry-run** (zero side effects, external steps simulated) and **live** runs. External/impactful steps (notify, isolate_host, block_indicator, disable_account) are **approval-gated** — they only execute when their step id is in the approvals list on a live run. Live runs create investigations, assign analysts, add tasks, enrich IOCs, and generate summaries; persisted to `automation_executions` with full step audit.

**Files changed:** backend `server.py` (imports + ~230 lines of routes), new `mitre_data.py`, `playbooks.py`; frontend new `Mitre.jsx`, `ThreatIntel.jsx`, `Playbooks.jsx`; `Layout.jsx` (nav), `App.js` (routes).

**Design decisions:**
- Playbook external actions are recorded in the audit trail but NOT executed against real systems (no live EDR/firewall/IdP connected) — safe by default; adapter-ready.
- IOC scan reuses the detection engine's `evaluate_rule` so matching logic is identical to ingest-time detection (no divergent code path).
- MITRE coverage is purely derived from persisted rules/alerts — reproducible and attributed.

**Tests (curl):** MITRE coverage 22% (8/36, 28 gaps); IOC import parsed+inserted 2; IOC scan generated 1 real alert over 467 events; playbook dry-run made no changes; live brute_force run created investigation + 3 tasks + honored the `notify` approval; executions persisted. Frontend compiles.

**Limitations / next:** Advanced roadmap (investigation graph, detection replay lab, endpoint telemetry adapters, pipeline observatory, UEBA, SOC performance analytics, integration hub) tracked as Milestone 3 backlog. Docker/CI intentionally deferred per user.

---

## 2026-10-09 — Milestone 1 (original)
**Features:** Auth+RBAC+workspaces, ingestion+normalization, detection engine, alerts, hunting, rules, sources, investigations, reports, settings, AI assistant, dashboard.
**Tests:** 26/26 backend passed; detection produced 8 real alerts from synthetic telemetry.
