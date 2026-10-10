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


### 2026-10-10 — Playbook regression collection through established CI
- Commit [7f61dfb](https://github.com/ibrahim1101/SentinelLab/commit/7f61dfbf52ad0936c3024f2b3f6e3f7acf9e9780) imports all five playbook behavioral tests into `backend/tests/test_security_regressions.py`, which the established Phase 1 workflow explicitly runs. This is an interim collection bridge while the dedicated workflow execution remains unconfirmed.
- **Validation pending:** no successful run for commit 7f61dfb confirmed at time of entry; do not count five tests as passing until logs prove collection and execution. The previous static-security suite passed 14 tests.
- Docker smoke remains intermittently blocked by upstream MongoDB registry `toomanyrequests` errors. No reliable image-pull retry/fallback has yet been installed in the existing workflow; actual workflow filename must be identified before editing.
- PR #1 remains unmerged.


### 2026-10-10 — Playbook tenant regression mock correction
- [Run 38038794945](https://github.com/ibrahim1101/SentinelLab/actions/runs/38038794945) static-security failed with **17 passed, 2 failed**. The event-loop fix eliminated the prior closed-loop failures, but both tenant-scoping tests failed because patching a Motor collection object's method did not reliably intercept subsequent `db.collection` accesses.
- Commit [56f5d39](https://github.com/ibrahim1101/SentinelLab/commit/56f5d39fda93d3c5d301c6640549fdc4c59adcef) patches `playbooks.db` with a stable `SimpleNamespace` fake, including explicit `AsyncMock` collection methods, so database mutation assertions can observe the calls.
- CI validation of this change is pending. Continue checking test results; do not claim green until confirmed. PR #1 remains unmerged.


### 2026-10-10 — Playbook CI green; production reconciliation safety guards
- [Run 38038905653](https://github.com/ibrahim1101/SentinelLab/actions/runs/38038905653) completed successfully: **19 passed, 8 warnings** in static-security; docker-smoke succeeded. Five playbook behavioral regressions now run in established Phase 1 CI.
- Commit [2ad793b](https://github.com/ibrahim1101/SentinelLab/commit/2ad793b58f55dba51770e4f64e72c3265461a3ad) adds three source-level production-access reconciliation regression guards: reconciliation cannot write memberships, must require stale `applying` requests, and must derive terminal status from actual membership with compare-and-set protection.
- New reconciliation guards are **not yet CI-verified**; they are source-level checks, not simulated interruption integration tests. Next: verify CI, add behavior tests for present/absent membership, fresh guard and malformed timestamps, and harden intermittent Docker Hub pull rate limits. PR #1 stays unmerged.


### 2026-10-10 — Reconciliation guard CI passed; Docker Hub rate-limit recurrence
- [Run 38039377419](https://github.com/ibrahim1101/SentinelLab/actions/runs/38039377419) passed both jobs, static-security **22 passed, 8 warnings** (including three new source-level reconciliation guards).
- Later [run 38039386230](https://github.com/ibrahim1101/SentinelLab/actions/runs/38039386230) passed static-security but failed docker-smoke because Docker Hub returned `toomanyrequests: Rate exceeded` while pulling MongoDB. The failed jobs were re-run through GitHub Actions; rerun result pending.
- Durable fix still needed: identify active Phase 1 workflow filename and implement image pull retry / authenticated or alternate registry strategy without weakening tests. PR #1 remains unmerged.


### 2026-10-10 — Repeat Docker Hub rate limiting
- [Run 38040276134](https://github.com/ibrahim1101/SentinelLab/actions/runs/38040276134) failed docker-smoke (`toomanyrequests: Rate exceeded`), while static-security succeeded. The prior failed run 38039386230 passed on rerun.
- Requested rerun of failed jobs for run 38040276134; outcome pending. This is only temporary recovery, **not a permanent registry mitigation**.
- Active workflow path has not been identified; do not claim retry/backoff or registry mirror is implemented. Next: locate workflow in GitHub Actions UI, add bounded pull retries or authenticated/alternate image registry, verify CI. PR #1 remains unmerged.


### 2026-10-10 — Runtime reconciliation edge-case coverage
- [Run 38043331144](https://github.com/ibrahim1101/SentinelLab/actions/runs/38043331144) passed both jobs: **24 passed, 8 warnings** in static-security, docker-smoke success.
- Commit [a3727cf](https://github.com/ibrahim1101/SentinelLab/commit/a3727cf567b85dc3788bed1415cc0140681129da) extends runtime reconciliation tests for fresh approvals (409 without DB mutation), malformed or missing approval timestamps (reconcile using actual membership), and compare-and-set concurrent state change (409, no audit).
- New edge-case test CI pending. Remaining: integrate bounded Docker image pull retries into active workflow, browser verify simulated-action UI. PR #1 stays unmerged.


### 2026-10-10 — v0.9.0 Public Beta release preparation
- [CI run 38043724553](https://github.com/ibrahim1101/SentinelLab/actions/runs/38043724553) verified **25 passed, 8 warnings**, docker-smoke success.
- Commit [df39de5](https://github.com/ibrahim1101/SentinelLab/commit/df39de52fdc0c7d2ffaf6f115f199ce02f3b9e6c) created `docs/BETA_RELEASE_GATES.md` with P0 release blockers, P1 distribution tasks, simulation disclosures, and explicit go/no-go requirements. **No public release has been tagged or published.**
- Immediate next: resolve Docker CI retry integration, browser QA, end-to-end SOC and clean-host deployment evidence, backup/restore, guide download verification. PR #1 remains unmerged.


### 2026-10-10 — Post-deployment release smoke tool
- Added `scripts/smoke_release.py` (commit `4e83bd1`): read-only health, readiness, and unauthenticated `/api/auth/me` + `/api/dashboard/overview` denial checks. Run `python scripts/smoke_release.py --base-url http://127.0.0.1:8000` against a **running** stack.
- Added source regression guard in commit `8cd474c`; CI verification pending. This is not yet evidence of a clean-host installation or a live smoke run.
- P0 deployment/browser/end-to-end/backup gates remain unchecked; PR #1 stays unmerged.


### 2026-10-10 — Release smoke checker behavioral regression
- [Run 38045119571](https://github.com/ibrahim1101/SentinelLab/actions/runs/38045119571) green: **26 passed, 8 warnings**, docker-smoke success.
- Commit [0675759](https://github.com/ibrahim1101/SentinelLab/commit/067575977b1e1957919bdddf644f9c460f13ef9f) adds dependency-free behavioral regression tests executing `scripts/smoke_release.py` with mocked HTTP results. Scenarios: healthy/readiness success, readiness failure, malformed health JSON, auth bypass on either protected endpoint, and network outage. CI pending; no live-host run claimed.
- PR #1 unmerged; P0 browser, clean install, real backup/restore, and Docker retry workflow integration remain open.


### 2026-10-10 — Docker Compose beta security baseline
- [Run 38045681744](https://github.com/ibrahim1101/SentinelLab/actions/runs/38045681744) succeeded: **27 passed, 8 warnings**, docker-smoke success.
- Added `scripts/check_compose_security.py` (commit `8f95642`) to check mandatory JWT/admin secrets, demo accounts disabled by default, loopback API/web bindings, Mongo persistence, readiness dependency and no published MongoDB port. Added runtime regression against unsafe edits in commit `710a64f`.
- This is a static baseline, **not** an external penetration test or TLS/firewall verification. New CI pending. PR #1 remains unmerged.


### 2026-10-10 — Fail-closed public beta checklist checker
- [Run 38047331311](https://github.com/ibrahim1101/SentinelLab/actions/runs/38047331311) succeeded: **28 passed, 8 warnings**, Docker smoke success.
- Added `scripts/check_release_gates.py` (commit `8102c55`): lists pending P0 requirements from this release checklist and exits nonzero (NO-GO) until completed. Missing/empty P0 sections also fail closed. Regression test commit `f0de1de`; CI pending.
- Run `python scripts/check_release_gates.py` before release. This checks checklist state, **not independent truth of evidence**. Existing P0 gates still open; PR #1 unmerged.


### 2026-10-10 — Docker registry retry CI gate closed
- [Run 38048195479](https://github.com/ibrahim1101/SentinelLab/actions/runs/38048195479) succeeded: **30 passed, 8 warnings**, docker-smoke success. Docker logs explicitly show `bash scripts/pull-mongo-with-retry.sh` executing before Compose and successfully pulling `public.ecr.aws/docker/library/mongo:7`.
- Beta checklist now marks this P0 gate complete (3 complete, 6 pending). This confirms normal-path execution, not an induced rate-limit recovery scenario. Remaining P0 include browser UI, end-to-end SOC workflows, clean install, security review, backup/restore, and final bug triage. PR #1 unmerged.


### 2026-10-10 — Login input/icon overlap found during browser QA
- User screenshot showed email and password values visually colliding with leading icons on the login screen.
- Commit [15c3579](https://github.com/ibrahim1101/SentinelLab/commit/15c3579726236e6adaac2471bf34e28c35ef00dc) changed Login.jsx input padding to explicit inline left/right values and added browser autocomplete hints. Browser recheck pending; this does not close the Playbooks UI P0 gate.


### 2026-10-10 — Playbooks overview browser QA evidence
- User-provided screenshot confirms the Playbooks overview renders seven playbook cards, severity/step/approval badges, and execution-history empty state. This does **not** establish that the approval modal, simulated actions or persisted run details behave correctly.
- Source review confirmed `backend/playbooks.py` persists only non-dry-run executions; UI `frontend/src/pages/Playbooks.jsx` already labels external actions as simulated in the run modal and uses `Record Run` rather than `Execute Live`.
- Commit [d4e1897](https://github.com/ibrahim1101/SentinelLab/commit/d4e1897182ecc773ac9a071d58c3beef126799f3) improves history wording to `recorded runs` / `No recorded runs yet — dry-runs are not saved`. Rebuild and browser recheck pending. P0 browser gate remains open pending modal screenshots and actual action checks.


### 2026-10-10 — Playbooks Malware Alert Triage dry-run browser evidence
- User screenshot: selected `Known Malicious IOC Match — IOC match (64) (critical)`, approval checkbox **unchecked**, clicked **Dry Run**.
- UI displayed 64 collected events; IOC enrichment checked one indicator and reported one known-bad match; investigation creation and containment tasks described as hypothetical; EDR isolation step status **Simulated** with `DRY-RUN: external action simulated, no changes made.` Summary rendered. This supports UI rendering and dry-run simulation labeling only; database immutability and external action absence have not been independently instrumented.
- Next: recorded run with approval unchecked must show `pending_approval` and no EDR execution; then explicit approval must still show `simulated` (disconnected EDR), with persisted execution history. P0 Playbooks browser gate remains open pending these checks.


### 2026-10-10 — Dedicated playbook CI missing pytest plugin
- [Run 38050487796](https://github.com/ibrahim1101/SentinelLab/actions/runs/38050487796) failed before test collection: `ERROR: Missing required plugins: pytest-xdist`, exit code 4. This is a CI dependency configuration issue; not evidence of failed playbook runtime behavior.
- Commit [3727153](https://github.com/ibrahim1101/SentinelLab/commit/3727153d63478ab4f93e7446ab5dc4cceff8fc64) adds `pytest-xdist` and `pytest-asyncio` to `.github/workflows/playbook-regressions.yml` dependency installation. CI verification pending; preserve PR #1 unmerged.


### 2026-10-10 — Dedicated Playbooks CI MongoDB test isolation
- [Run 38050793821](https://github.com/ibrahim1101/SentinelLab/actions/runs/38050793821) failed **1 failed, 4 passed** after pytest plugins were installed. The unapproved-action test patched a collection method on a live Motor client; execution instead attempted to write to `localhost:27017` and timed out with `ServerSelectionTimeoutError`.
- Commit [9a86d15](https://github.com/ibrahim1101/SentinelLab/commit/9a86d15f0c8b3df3089b8fa56dca0f0be58b4b33) replaces the entire `playbooks.db` object with a fake containing `AsyncMock` for execution persistence, preventing unintended real database access. Dedicated workflow CI result pending. No production playbook behavior changed.


### 2026-10-10 — Dedicated Playbooks CI recovered; broadened external-action regressions
- [Playbooks run 38053947679](https://github.com/ibrahim1101/SentinelLab/actions/runs/38053947679) green: **5 passed**. [Phase 1 run 38053947643](https://github.com/ibrahim1101/SentinelLab/actions/runs/38053947643) green: **30 passed, 8 warnings**, Docker smoke success.
- Commit [2691885](https://github.com/ibrahim1101/SentinelLab/commit/2691885cce5976c2ace89b145ea8d646b056a55d) adds mocked behavior tests covering all four disconnected external actions (`notify`, `isolate_host`, `block_indicator`, `disable_account`): approved actions are simulated/audit-only and persisted as such; unapproved actions remain pending. CI pending; browser approved EDR simulation and execution history still need user verification.


### 2026-10-10 — Browser evidence: approved EDR action remains simulated
- User-supplied local Playbooks screenshot of **Malware Alert Triage**, target **Known Malicious IOC Match — IOC match (64) (critical)**, EDR approval checkbox selected and **Record Run** result displayed.
- UI reported 64 related events, 1 known-bad IOC, investigation created (prefix `53dcd a7f` displayed without space: `53dcda7f`), 3 containment tasks added, and EDR `Isolate affected host` status **Simulated** with `APPROVED external action 'isolate_host' recorded in audit trail (no live system connected).` This is browser UI evidence, not an independently verified assertion of zero external side effects.
- Prior screenshot had EDR **Pending Approval** without approval. Dedicated Playbooks CI run 38054238824 green (7 passed); Phase 1 run 38054242988 green (30 passed, 8 warnings; Docker smoke passed).
- **Next required browser evidence:** close run modal, verify `Execution History (recorded runs)` shows persisted recorded executions; open a row and confirm saved step status and correct org context. Do not close Playbooks P0 browser gate until this is verified.
