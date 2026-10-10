# SentinelLab v0.9.0 Public Beta — Release Gates

Status: **candidate planning, NOT approved for public release**. Working branch: `fix/phase1-security-regressions`. PR #1 must remain unmerged until review.

## P0 — mandatory before public beta

- [x] Existing security suite including playbook and production-access reconciliation regressions: **25 passed, 8 warnings** in [CI run 38043724553](https://github.com/ibrahim1101/SentinelLab/actions/runs/38043724553).
- [x] Docker smoke passed in that run.
- [x] Bounded MongoDB image-pull retry integrated into active Phase 1 workflow (`.github/workflows/security-phase1.yml`), verified in [CI run 38048195479](https://github.com/ibrahim1101/SentinelLab/actions/runs/38048195479): 30 passed, 8 warnings, docker-smoke green; logs confirm retry helper invoked before Compose.
- [x] Browser-verify Playbooks labels, approval gates, and `simulated` status for disconnected external actions: user-provided browser screenshots on 2026-10-10 verified unapproved `Pending Approval`, approved `Simulated` with no live EDR connected, persisted execution detail, and corrected local history timestamps. CI: Playbooks [38054238824](https://github.com/ibrahim1101/SentinelLab/actions/runs/38054238824) 7 passed; Phase 1 [38054242988](https://github.com/ibrahim1101/SentinelLab/actions/runs/38054242988) 30 passed, 8 warnings and Docker smoke green. Browser evidence is manual and does not replace live integration/security testing.
- [ ] Run and record end-to-end ingest → detect → alert → investigation → playbook → report smoke, including tenant boundaries.
- [ ] Verify installation from a clean host using documented environment variables, safe secrets, and non-public default bind addresses.
- [ ] Security review: secrets, JWT/cookie settings, demo accounts disabled by default, least-privilege workspace access, dependency findings, and authentication throttling.
- [ ] Verify database persistence, backup, restore, restart recovery, and interrupted production-access approval behavior against a running stack.
- [ ] Confirm no release-blocking P0 bugs; explicitly review unresolved CI warnings and limitations.

## P1 — documentation and distribution

- [ ] Validate public Portfolio download for `docs/SentinelLab_Complete_User_Guide_v1.pdf` and accuracy of each supported workflow.
- [ ] Update README with installation, environment setup, ports, upgrade and rollback, known limitations, and support route.
- [ ] Produce a tested v0.9.0 changelog and release notes distinguishing simulation from live response actions.
- [ ] Record supported platforms, resource requirements, and installation method; do not promise standalone installers without tested artifacts.
- [ ] Tag a reviewed immutable release commit only after all P0 gates pass.

## Explicit limitations to disclose

- Disconnected EDR/notification actions are **simulated/audit-only**, not real endpoint containment.
- The current stack is React/FastAPI/MongoDB; future integrations are not automatically production-ready.
- Docker Hub rate limiting has intermittently failed smoke CI; bounded Mongo image-pull retry is now wired into the active workflow and verified on the normal successful path (not under an induced rate limit).
- Source-level reconciliation guards and mocked runtime tests do not replace real interruption/recovery testing.

## Go/no-go process

1. Run security suite and Docker smoke on the **exact candidate SHA**.
2. Complete browser and clean-install evidence; log every failure and fix in `ENGINEERING_JOURNEY.md`.
3. Review P0 checklist and known limitations. Any unchecked P0 means **NO-GO**.
4. After approval, create v0.9.0 release notes/tag; leave PR #1 unmerged unless separately authorized.

Last evidence checked: 2026-10-10, workflow 38043724553.


### 2026-10-10 — Post-deployment release smoke tool
- Added `scripts/smoke_release.py` (commit `4e83bd1`): read-only health, readiness, and unauthenticated `/api/auth/me` + `/api/dashboard/overview` denial checks. Run `python scripts/smoke_release.py --base-url http://127.0.0.1:8000` against a **running** stack.
- Added source regression guard in commit `8cd474c`; CI verification pending. This is not yet evidence of a clean-host installation or a live smoke run.
- P0 deployment/browser/end-to-end/backup gates remain unchecked; PR #1 stays unmerged.


### 2026-10-10 — Docker Compose beta security baseline
- [Run 38045681744](https://github.com/ibrahim1101/SentinelLab/actions/runs/38045681744) succeeded: **27 passed, 8 warnings**, docker-smoke success.
- Added `scripts/check_compose_security.py` (commit `8f95642`) to check mandatory JWT/admin secrets, demo accounts disabled by default, loopback API/web bindings, Mongo persistence, readiness dependency and no published MongoDB port. Added runtime regression against unsafe edits in commit `710a64f`.
- This is a static baseline, **not** an external penetration test or TLS/firewall verification. New CI pending. PR #1 remains unmerged.


### 2026-10-10 — Fail-closed public beta checklist checker
- [Run 38047331311](https://github.com/ibrahim1101/SentinelLab/actions/runs/38047331311) succeeded: **28 passed, 8 warnings**, Docker smoke success.
- Added `scripts/check_release_gates.py` (commit `8102c55`): lists pending P0 requirements from this release checklist and exits nonzero (NO-GO) until completed. Missing/empty P0 sections also fail closed. Regression test commit `f0de1de`; CI pending.
- Run `python scripts/check_release_gates.py` before release. This checks checklist state, **not independent truth of evidence**. Existing P0 gates still open; PR #1 unmerged.


## Product delivery requirement — standalone cross-platform application (2026-10-10)

The owner explicitly requires SentinelLab to ship as a **standalone desktop application on Windows, Linux, and macOS**, with an install-and-launch experience. Docker is a development/test/deployment option, **not** the intended primary end-user installation path.

**Release decision:** The existing 9 P0 gates cover security/functional readiness of the current stack only. **9/9 does not authorize a public desktop release** until the additional packaging and per-platform gates below are satisfied. Keep status NO-GO until both sets are complete. Do not check a gate based solely on a CI green build or a mock.

### Desktop packaging and compatibility gates — mandatory for standalone public release
- [ ] Choose and document desktop shell (evaluate Tauri), backend packaging, secure loopback IPC, process lifecycle and crash recovery; produce a working proof of concept on Windows, then validate Linux and macOS.
- [ ] Support a separately installed MongoDB Community Server (local authenticated connection) and an optional configured remote MongoDB server; verify connectivity, credential handling, failure states and data integrity on each supported OS. Bundling MongoDB is deferred and NOT a release requirement.
- [ ] Package backend and frontend with no visible console and no external Python/Node runtime prerequisite; provide secure first-run setup, secrets handling, local-only binding and update strategy.
- [ ] Produce and test Windows installer on a clean Windows machine, including install, launch, uninstall, restart, backup and upgrade.
- [ ] Produce and test Linux distribution packages (at least one documented supported distribution), including dependencies, desktop integration, permissions and upgrade.
- [ ] Produce and test macOS app/DMG on supported hardware, including architecture coverage, signing/notarization where applicable, permissions and upgrade.
- [ ] Run end-to-end SOC and security regression tests on the **packaged desktop artifacts** for all claimed platforms, including offline behavior, tenant isolation, persistence and recovery.
- [ ] Publish platform-specific installation docs, supported OS/CPU matrix, hashes/signatures, known limitations and release notes; review licensing and redistribution of all bundled components.

Do not advertise untested platforms as supported. CI builds alone are not evidence of clean-host compatibility.


### 2026-10-10 — Approved sequencing: platform support before MongoDB integration
- Product owner explicitly chose **user-installed MongoDB Community Server** as an acceptable prerequisite for the standalone SentinelLab desktop application. No embedded/bundled MongoDB or database migration is required for the initial desktop release.
- **Order:** Windows Tauri/React/FastAPI sidecar proof of concept → Linux compatibility → macOS compatibility → guided MongoDB configuration (local authenticated / optional remote) → clean-host packaging and release validation.
- Keep existing MongoDB driver and persistence code during the platform work. Desktop must manage its own backend startup/shutdown; users should not need Docker, Python or Node.js installed. Clearly document the separate MongoDB prerequisite.
- Release remains NO-GO until core P0 and revised desktop gates are evidenced; PR #1 remains unmerged.
