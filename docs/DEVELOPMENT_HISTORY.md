# Development History

## 2026-10-09 — Milestone 1: Core SOC platform
**Features:** Auth+RBAC+workspaces, ingestion+normalization, detection engine, alerts, hunting, rules, sources, investigations, reports, settings, AI assistant, dashboard.
**Files added:** backend/{core,parsers,detection,seed,ai_assistant,server}.py; frontend/src/{lib/api, context/*, components/*, pages/*}.
**Design decisions:**
- MongoDB used as both record store and search adapter (Emergent runtime has no Postgres/OpenSearch). Modular parser/detection/ingestion boundaries preserved for future swap.
- String uuid `id` keys everywhere (no ObjectId) → clean JSON serialization.
- Auth uses Bearer token (localStorage) as primary + httpOnly cookie; avoids cross-site cookie pitfalls in proxied preview.
- Detection engine is declarative-only (no code execution); supports match/threshold(sliding-window)/frequency/indicator.
- Synthetic Training Lab seeded on startup; crafted to genuinely trigger built-in rules via the real engine (not hardcoded alerts).
**Tests performed (curl):** health OK; admin login returns user+token; dashboard overview returns computed KPIs (467 events, 8 open alerts); detection produced 8 alerts (brute force, password spray, port scan, PowerShell, IOC, outbound) from seeded telemetry; 8 rules present with match_count>0.
**Failures/fixes:** server.py first write blocked (file existed) → re-created with overwrite. python-dateutil added for detection timestamp parsing.
**Remaining limitations:** MITRE page, TI UI, UEBA, network graph, vuln mgmt, playbooks, automation, PDF export, Docker/CI not yet built (later milestones).
**Next steps:** MITRE ATT&CK coverage; Threat Intelligence IOC UI; playbooks/automation; Docker + CI.
