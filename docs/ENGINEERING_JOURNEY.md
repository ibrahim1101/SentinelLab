# SentinelLab — Engineering Journey & Decision Log

> **Living document.** Update this file with every meaningful feature, design decision, test, failure, fix, and release milestone. Preserve failures and their root causes rather than rewriting history. Dates and claims below are limited to verified project context; the early Emergent phase is summarized, not reconstructed step-by-step.

## Project vision

SentinelLab is a SOC/SIEM-oriented cybersecurity application, initially generated using Emergent and now being engineered into a maintainable, secure, independently deployable full-stack project. Development happens in [ibrahim1101/SentinelLab](https://github.com/ibrahim1101/SentinelLab).

**Engineering policy:** work in feature branches, run automated tests, document regressions, and do not merge pull requests without explicit approval.

## Phase 0 — Emergent prototype

- The initial UI and application functionality were built with Emergent. The user reported that Emergent credits ran out during testing and requested independent verification and continued engineering in GitHub.
- Existing application includes a React frontend, FastAPI backend, MongoDB storage, authentication/workspaces, events, alerts, rules, investigations, reports, threat hunting, and additional SOC-oriented features.
- **Limitation:** This log cannot claim every original Emergent feature has been independently validated. The original build history and any unverified implementation claims should be audited separately.

## Phase 1 — Security stabilization and reproducible deployment

Working branch: `fix/phase1-security-regressions`. Pull request: [#1](https://github.com/ibrahim1101/SentinelLab/pull/1), intentionally unmerged.

### Security fixes

- Restricted AI assistant context retrieval to the active organization.
- Ensured detection replay with `persist=False` does not modify events, alerts, or rule metadata.
- Scoped detection persistence and rule updates by organization; added MongoDB-backed isolation tests.
- Escaped and bounded user-controlled regular expressions.
- Removed default hardcoded administrator credentials; made demo accounts opt-in.
- Added live authentication, role-based access control, and workspace authorization smoke tests.
- Scoped linked event and rule lookups in alert details to the active tenant (commits `b692422`, `8576b81`).
- Added MongoDB-backed cross-tenant alert tests (commits `ba1088c`, `d5ff2a5`).
- Scoped linked alerts in investigation details to the active tenant, with a MongoDB regression test (commits `7ec55fc`, `573bbcb`).

### Build and infrastructure

- Added portable runtime dependencies in `backend/requirements.runtime.txt` and a non-root backend Docker image.
- Added `compose.yaml` for MongoDB, FastAPI API, and the React frontend served by Nginx on localhost.
- Added `.env.example`, Docker ignore files, and `docs/LOCAL_DOCKER.md`.
- Added GitHub Actions security and Docker smoke workflows, including anonymous access, administrator login, JWT checks, role restrictions, and workspace boundary tests.

### CI failures and lessons learned

| Stage | Symptom | Root cause | Resolution | Verification |
|---|---|---|---|---|
| Expanded role tests, commit `3d991ed` | Docker smoke failed with HTTP 422 on account registration | Test email used `@example.invalid`, rejected by email validation | Changed to a syntactically acceptable `@example.com` test address in `ae48bf3` | Both workflows passed: runs [37973059921](https://github.com/ibrahim1101/SentinelLab/actions/runs/37973059921), [37973055184](https://github.com/ibrahim1101/SentinelLab/actions/runs/37973055184) |
| Alert-detail tenant join hardening, `8576b81` | Regression risk: linked records were not tenant-filtered | Alert's own query was scoped, but linked events/rules weren't | Scoped joins and added regression test | Both workflows passed: runs [37974511197](https://github.com/ibrahim1101/SentinelLab/actions/runs/37974511197), [37974504326](https://github.com/ibrahim1101/SentinelLab/actions/runs/37974504326) |
| MongoDB tenant integration, `d5ff2a5` | Need to verify behavior with actual cross-linked tenant records | Source-level assertions alone are insufficient | Added isolated MongoDB integration tests | Both workflows passed: runs [37975092843](https://github.com/ibrahim1101/SentinelLab/actions/runs/37975092843), [37975085607](https://github.com/ibrahim1101/SentinelLab/actions/runs/37975085607) |
| Investigation linked-alert hardening, `573bbcb` | Potential cross-tenant data disclosure | Investigation was scoped, linked alert query was not | Added `org_id` filter and integration test | CI running when this entry was authored; verify latest Actions run |

**Note:** Earlier trial-and-error details not captured in available verified history must be appended from actual commits, CI logs, or original development notes; do not invent them.

## Outstanding risks / next engineering milestones

1. Verify the latest investigation-isolation CI run and fix any failure.
2. Audit all other joins, exports, mutations, and background jobs for organization scoping.
3. Self-registration now grants training-only membership; design administrator-approved production tenant onboarding before public deployment. Review previously registered users for overbroad access.
4. Expand RBAC coverage across auditor, analyst, SOC manager, administrator, and super administrator actions.
5. Audit security-sensitive user input, file uploads, session handling, and secrets.
6. Add production-readiness controls (TLS, secure cookie configuration, rate limiting, monitoring, backups, migration and deployment guidance).
7. Verify full-stack usability and functionality end-to-end, including any features inherited from Emergent.

## 2026-10-10 — Tenant-safe bulk alert mutation accounting

- **Goal:** ensure bulk alert updates cannot affect other tenants and return an accurate update count.
- **Change:** replaced the requested-ID count with MongoDB `modified_count`, retaining the `org_id` filter (commit `8331353`).
- **Regression:** MongoDB integration test submits local, foreign, and nonexistent alert IDs and asserts only the local record changes (commit `f7402dd`).
- **Verification:** CI triggered; results must be checked before claiming success.
- **Next:** audit remaining mutation paths, especially related IDs and organization membership onboarding.

## 2026-10-10 — Self-registration tenant privilege fix

- **Finding:** anonymous registration automatically granted both production and training memberships, enabling newly created accounts to access production SOC data.
- **Fix:** self-registered accounts now receive training-only membership and training as their default workspace (commit `7732ffc`).
- **Regression:** authenticated Compose smoke test asserts restricted membership and a 403 when a new account requests production data (commit `be6f8ac`).
- **Compatibility note:** existing user memberships are not automatically migrated; administrators must review and remediate historical memberships. A controlled invitation/approval workflow for production access remains to be built.
- **Verification:** CI pending when documented.

## 2026-10-10 — Administrator-managed workspace membership

- **Goal:** allow explicit review and remediation of legacy production access, with no automatic revocations.
- **Implementation:** added super-admin-only `GET /api/admin/membership-review` listing current production members and `PUT /api/admin/users/{user_id}/workspaces` for controlled grants and revocations (commit `62c2b51`).
- **Safeguards:** validates built-in workspace IDs, keeps a valid default workspace, prevents self-removal of production access and removal of production access from super administrators, and records old/new membership in the audit log.
- **Important:** the review endpoint lists all production members; membership changes must be explicitly authorized. No automatic migration or revocation was executed.
- **Remaining:** add dedicated API integration tests, verify CI, improve administrative review UI and approval workflow, and consider multi-admin safeguards.

## 2026-10-10 — Membership approval/revocation live API regression

- **Goal:** validate administrator-controlled membership changes through the running Docker stack, not only code inspection.
- **Change:** expanded `backend/tests/compose_auth_smoke.py` with checks for read-only membership review, denied auditor grants, rejected unknown workspace IDs, super-admin production grant, immediate production read access, revocation, subsequent 403, and self-protection of super-admin production membership.
- **Commit:** `43979a4`.
- **Verification:** CI pending at time of writing; record workflow links and results after completion.
- **Remaining:** build an administrative review interface and multi-admin approval process, and review legacy production memberships before public exposure.

## 2026-10-10 — Production membership review UI

- **Goal:** expose administrator-controlled production workspace access in the existing application rather than requiring raw API requests.
- **Implementation:** added super-admin-only membership review controls under Settings → Security, displaying user membership status and offering confirmation-gated grant/revoke actions, with loading and error feedback. The server enforces authorization and audits changes (commit `dd3db57`).
- **Prior verification:** membership grant/revoke API integration tests passed on commit `af4e270`, runs [37978184860](https://github.com/ibrahim1101/SentinelLab/actions/runs/37978184860) and [37978175892](https://github.com/ibrahim1101/SentinelLab/actions/runs/37978175892).
- **Verification:** frontend build/CI pending; manual browser validation remains outstanding.
- **Next:** consider a two-person approval flow for high-risk grants, audit legacy accounts, and add UI interaction tests.

## 2026-10-10 — Idempotent membership management

- **Goal:** avoid redundant database writes and audit entries when an administrator submits an unchanged membership set.
- **Implementation:** workspace updates compare requested and existing membership sets; unchanged requests return `unchanged: true` without a write or audit event (commit `211ca75`).
- **Regression:** Docker API smoke test repeats a grant with reordered workspace IDs and asserts the idempotent response (commit `c99c752`).
- **Verification:** CI pending at time of entry. UI browser interaction still needs manual verification.

## 2026-10-10 — Two-person production access approval

- **Security policy:** direct production workspace grants now return HTTP 409. A super administrator submits a production access request; a **different** super administrator must approve before production membership is added.
- **Backend:** added pending-request collection, list/create/approve APIs, distinct-approver check, atomic claim of pending requests, membership add-to-set, and audit logging (commit `2870eaf`).
- **Tests:** Compose smoke now rejects direct grants, rejects self-approval, verifies no access before approval and checks queue authorization (commit `51ef0b5`).
- **UI:** Settings → Security submits requests and displays pending requests with approval buttons disabled for the original requester (commits `5450211`, `057b623`).
- **Verification:** CI pending; full two-admin approval happy path and browser validation still require dedicated tests. No migration of legacy access was performed.
- **Known hardening work:** approval and membership writes are separate MongoDB operations; a transaction or recovery procedure would strengthen failure handling. Request expiry and cancellation are not yet implemented.

## Update template (append on every milestone)

### YYYY-MM-DD — Short milestone name
- **Goal:**
- **Changes / files:**
- **Commit / PR:**
- **Tests and CI evidence:**
- **Failures / root cause / remediation:**
- **Remaining risks and next step:**

## Documentation maintenance rules

- Keep this file editable Markdown and version-controlled.
- Update after substantive changes, including failed experiments and abandoned approaches.
- Link commits, issues, PRs, and workflow runs when available.
- Distinguish *implemented*, *tested*, *passed in CI*, and *not yet validated*.
- Never erase historical failures when later fixed.
