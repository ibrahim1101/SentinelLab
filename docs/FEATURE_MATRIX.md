# SentinelLab — Feature Matrix

## Reading this matrix as of 30 October 2026

The early milestone tables are historical. Their `Tested` labels and `Not Started` entries are not a current release certification; use the dated alpha override and exact source branch/commit.

- `backend/server.py` implements summary downloads as JSON and CSV in this default snapshot. Do not claim native PDF export from that API; a separately authored investigation PDF is a different artifact.
- `backend/playbooks.py` records external isolation, blocking, account-disable and notification steps as simulated without a live system, including after approval. Local indicator lookup is not a live reputation-provider integration.
- Full installed-desktop ingest-to-report and tenant-boundary acceptance remain separate gates. Narrow tests, historical manual checks and packaging jobs do not establish complete SOC readiness.
- CI outcomes are branch-specific. Review current Actions and the exact SHA rather than treating historical green status as a current repository-wide result.


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


## 2026-10-12 — Current alpha status override

**Important:** Historical labels above reflect the original prototype and some Emergent-reported tests. The current evidence below supersedes obsolete "Not Started" statuses for features that were subsequently implemented. "CI passed" is not the same as end-to-end desktop validation.

| Capability | Current status | Evidence / caveat |
| --- | --- | --- |
| Windows Tauri installer and bundled FastAPI sidecar | CI passed + basic manual test | Windows workflow `38265416099`; MongoDB installed separately |
| Linux DEB and AppImage | CI packaged, runtime untested | `38265421720` |
| macOS Intel and Apple Silicon DMG | CI packaged, runtime untested | `38265421720` |
| Login hardening, disabled accounts, lockouts | CI passed + selected manual tests | `38265992950`; broader threat modeling remains |
| Organization/workspace security | Automated regressions | `38265992719`; full packaged multi-tenant tests outstanding |
| Local and cloud OpenAI-compatible model configuration | Implemented; Ollama manually verified | Local `qwen3:14b` response confirmed |
| AI product guidance | Implemented | Built-in guide; complete in-app manual retrieval not yet implemented |
| Discord outgoing webhooks | Implemented + manually delivered | Line breaks and contextual audit event fixes included |
| Generic/Slack/Teams webhook payload adapters | Implemented; no full physical delivery proof | Provider-specific external service testing pending |
| VirusTotal, AbuseIPDB, SMTP integration | Planned UI placeholders only | No functional provider integration |
| MITRE ATT&CK coverage, IOC import/scan, playbooks | Implemented; historical targeted API tests | Full desktop SOC workflow verification pending |
| Docker Compose + GitHub Actions CI | Implemented | Phase 1 security and desktop packaging jobs pass |
| Signing/notarization | Not started | All alpha installers unsigned |
| Full end-to-end SOC regression on installed desktop | Pending | Must not imply full production readiness |

See `docs/ENGINEERING_JOURNEY.md` for the dated decision log and `docs/RELEASE_GATE_V0.1.0_ALPHA.md` for release blockers and explicit exceptions.
