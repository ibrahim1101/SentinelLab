# SentinelLab — Feature Matrix

Statuses: `Not Started` · `In Progress` · `Implemented` · `Tested` · `Blocked`
(Never mark `Tested` unless relevant tests passed.)

## Milestone 1 — Core (this build)
| Feature | Status |
|---|---|
| Email/password auth (JWT, bcrypt) | Tested |
| RBAC (5 roles, server-enforced) | Tested |
| Multi-workspace isolation | Tested |
| Login rate limit / lockout | Implemented |
| Overview Dashboard (real KPIs + charts) | Implemented |
| Event ingestion API (JSON/JSONL/CSV/Syslog/CEF) | Tested |
| File upload ingestion | Implemented |
| Event normalization (versioned schema) | Tested |
| Events Explorer (filter/sort/paginate/export) | Implemented |
| Event Details (overview/raw/normalized/related) | Implemented |
| Detection engine (match/threshold/frequency/indicator) | Tested |
| 8 built-in detection rules | Tested |
| Rule CRUD / toggle / backtest | Implemented |
| Alert lifecycle (status/assign/comment/audit) | Implemented |
| Alert details + supporting events | Implemented |
| Threat hunting (safe query parser, facets, timeline) | Implemented |
| Saved hunts | Implemented |
| Source management (CRUD, token-once) | Implemented |
| Investigations (cases/notes/tasks) | Implemented |
| Evidence upload + SHA256 chain-of-custody | Implemented |
| Reports (generate + JSON/CSV download) | Implemented |
| Settings (6 tabs) | Implemented |
| 4 themes (persisted) | Implemented |
| Global search | Implemented |
| Notifications | Implemented |
| AI assistant (adapter + explain) | Implemented |
| Demo mode reset / synthetic Training Lab | Tested |
| Audit logging | Implemented |

## Later Milestones
| Feature | Status |
|---|---|
| MITRE ATT&CK explorer + coverage | Tested |
| Threat intelligence IOC UI + STIX/CSV import | Tested |
| Network analytics + relationship graph | Not Started |
| Investigation graph (interactive node-link, pivots) | Tested |
| Detection Replay Lab (isolated, expected-vs-actual, regression) | Tested |
| Pipeline Observatory (live EPS, parser failures, source health) | Tested |
| UEBA | Not Started |
| Vulnerability management | Not Started |
| Incident response playbooks (dry-run + approval gates) | Tested |
| Security automation engine | Not Started |
| Sigma YAML import UI | Not Started |
| TOTP MFA + WebAuthn | Not Started |
| Scheduled reports + PDF export | Not Started |
| Docker Compose + GitHub Actions CI | Not Started |

## Phase 1 verification note (2026-10-09)
Milestone 2/3 `Tested` labels above reflect Emergent-reported API checks, not independent CI confirmation. Security stabilization is in progress on `fix/phase1-security-regressions`; do not interpret this matrix as a production certification.
