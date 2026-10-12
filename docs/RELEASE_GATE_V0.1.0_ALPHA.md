# SentinelLab v0.1.0-alpha — Release Gate

Target: October 13, 2026. This checklist is a **release gate**, not evidence of passing tests.

## Required before publishing
- [ ] Windows installer GitHub Actions build succeeds; download and install on a clean Windows machine.
- [ ] Confirm whether the installer starts/owns the API and MongoDB or requires the separate Docker desktop stack. **Current Tauri project is a frontend shell; do not advertise a standalone all-in-one EXE.**
- [ ] Confirm sign-in, account lock/unlock, disabled users, password recovery, and session revocation with synthetic accounts.
- [ ] Import synthetic logs, verify ingestion and event search.
- [ ] Trigger a detection rule; verify alert creation, severity, timestamps and evidence.
- [ ] Create an investigation, assign/triage alert, record findings and close it.
- [ ] Exercise one safe playbook with test data; confirm execution and audit trail.
- [ ] Verify roles, organization/tenant separation and unauthorized API access.
- [ ] Restart application and confirm persistence; test clean shutdown and safe reinstall without data deletion.
- [ ] Run login-security and Phase 1 workflows on release commit.
- [ ] Write tested installation instructions, supported OS, dependencies, known limitations, screenshots and SIEM test results.
- [ ] Publish GitHub prerelease `v0.1.0-alpha` only after all claimed features are verified.

## Hands-on SIEM test record

| Scenario | Expected result | Actual result | Evidence |
| --- | --- | --- | --- |
| Import synthetic security events | Events appear and are searchable | NOT TESTED | |
| Detection rule | Matching events trigger alert | NOT TESTED | |
| Alert triage | Status/assignment persist | NOT TESTED | |
| Investigation | Evidence and findings persist | NOT TESTED | |
| Safe playbook | Recorded action and audit trail | NOT TESTED | |
| Tenant isolation | Cross-tenant access denied | NOT TESTED | |
| Desktop installer | Launches and reaches backend | NOT TESTED | |
| Restart persistence | Existing data retained | NOT TESTED | |

## Release decision

If Windows installer builds but depends on Docker, document Docker Desktop as a prerequisite. Do not imply the installer embeds the backend or MongoDB. If essential SIEM paths fail, fix them before publishing or explicitly remove them from release claims. Never test against real customer data or reset existing volumes.


---

## 2026-10-12 — Release candidate audit (current state; supersedes stale desktop claims above)

The original checklist above was written before the desktop sidecar existed. Its statement that the Tauri project is only a frontend shell is now **obsolete**. The Windows alpha installer bundles the FastAPI backend; MongoDB remains separately installed. User accepted shipping **experimental Linux/macOS builds without physical runtime testing**, with prominent limitations. This is an alpha exception, **not** a claim that beta or production gates are complete.

| Gate | Status | Evidence |
| --- | --- | --- |
| Windows desktop CI | PASS | [38265416099](https://github.com/ibrahim1101/SentinelLab/actions/runs/38265416099) |
| Linux and macOS package CI | PASS | [38265421720](https://github.com/ibrahim1101/SentinelLab/actions/runs/38265421720) |
| Login Security Tests | PASS | [38265992950](https://github.com/ibrahim1101/SentinelLab/actions/runs/38265992950) |
| Phase 1 Security Checks | PASS | [38265992719](https://github.com/ibrahim1101/SentinelLab/actions/runs/38265992719) |
| Windows installer basic user acceptance | PARTIAL PASS | Windows launch, MongoDB indicator, admin/non-admin login, AI, Discord, shutdown manually observed |
| Linux/macOS runtime installation | NOT TESTED | CI-only packaging; accepted alpha limitation |
| Full synthetic SOC end-to-end packaged test | NOT TESTED | Must not advertise production reliability |
| Release artifact checksums | PREPARED | Draft includes `SHA256SUMS.txt`; recheck after any asset replacement |
| Draft prerelease | CREATED | `v0.1.0-alpha` draft with six assets |
| Public prerelease | PENDING | Owner must approve publishing |
| Single-branch consolidation | PASS | PR #1 merged, only `main` branch; comparison showed no app-source deletions |

**Release decision:** Suitable to *prepare* an explicitly experimental alpha with the above disclosures. Do not treat unchecked full SOC gates as passed. Publish only after verifying actual attached assets and checksum consistency and owner confirmation. For beta/production, use `docs/BETA_RELEASE_GATES.md` with no alpha exceptions.


---

## 2026-10-12 — Current release-readiness checkpoint

This checkpoint supersedes older CI/build claims above. The original pre-sidecar wording in the first checklist is obsolete: FastAPI is now bundled as a desktop sidecar, while MongoDB remains an external prerequisite.

| Gate | Status | Evidence |
| --- | --- | --- |
| Windows desktop installer with locked npm/Cargo dependencies | **PASS (CI packaging)** | [Windows run 38289907035](https://github.com/ibrahim1101/SentinelLab/actions/runs/38289907035) |
| Linux x64 + macOS Intel/Apple Silicon locked-dependency packages | **PASS (CI packaging)** | [Linux/macOS run 38289916624](https://github.com/ibrahim1101/SentinelLab/actions/runs/38289916624) |
| Downloaded artifact structure | **PASS (file presence and sizes only)** | See `docs/ENGINEERING_JOURNEY.md` for five installer files and artifact IDs |
| Login Security Tests and Phase 1 Security Checks | **PASS on documentation commit 29c741ac** | GitHub Actions run history |
| Windows hands-on smoke test | **PARTIAL PASS** | Previously observed sign-in and application operations; not a full fresh-install regression |
| Linux/macOS real installation and runtime | **NOT TESTED** | CI-only alpha limitation accepted by owner |
| Synthetic SOC ingestion, detection, triage, investigation, playbooks, tenant isolation | **NOT TESTED END TO END** | Do not advertise these as fully validated |
| Third-party licenses, Emergent code/assets provenance, corresponding source obligations | **BLOCKED** | `docs/THIRD_PARTY_LICENSE_REVIEW.md` |
| Release-asset SHA-256 match and exact source commit mapping | **PENDING** | Existing draft assets predate locked-dependency builds; do not treat as matching |
| Draft `v0.1.0-alpha` | **EXISTS; UNPUBLISHED** | GitHub release currently has five installer assets and `SHA256SUMS.txt` |
| Release approval | **NOT GRANTED** | Owner approval required before publication |

### Immediate release sequence
1. Record SHA-256 hashes of the five **new** unsigned installer files and the corresponding build commit(s). Ideally rebuild all targets from **one** frozen release commit.
2. Compare actual candidate release assets against the checksum manifest; replace stale draft assets only after provenance is verified.
3. Review third-party license obligations, GPL corresponding-source delivery, and rights to Emergent-origin code/artwork. **No compliance sign-off yet.**
4. Complete a clean Windows installation/upgrade and data-preservation smoke test using synthetic data. Keep the accepted Linux/macOS CI-only limitation explicit.
5. Run and record synthetic SOC workflows, or narrow release claims to what has actually been tested.
6. Request explicit owner approval before publishing. **Do not publish automatically.**


## 2026-10-13 — Unified source build result

**Unified Alpha Candidate Build [#38294692191](https://github.com/ibrahim1101/SentinelLab/actions/runs/38294692191) PASSED all five jobs**, including the source gate, Windows installer, Linux x64, macOS Intel, and macOS Apple Silicon. All jobs checked out the **same source commit** `b9b7958e720d93db6191614c07d2c01e7945643d`.

| Platform | Actions artifact ID | Compressed artifact size |
| --- | --- | ---: |
| Windows x64 | `11768026703` | 26,534,393 bytes |
| Linux x64 | `11767666946` | 163,282,382 bytes |
| macOS Intel | `11767862517` | 32,086,612 bytes |
| macOS Apple Silicon | `11768520700` | 30,910,965 bytes |

**Still pending:** download and SHA-256 verify installer payloads from this unified run; ensure the draft release carries these exact binaries and matching checksums; clear third-party source/artwork license rights; and complete or explicitly limit untested runtime claims. The draft release remains unpublished. The source SHA above is the build candidate, not a claim that later documentation commits were included in those binaries.


## 2026-10-13 — Final prerelease audit (owner Windows acceptance)

- **Windows acceptance:** Owner confirms the unified Windows installer worked on their PC. This is an owner-reported runtime PASS, not an independently observed clean-install regression or full SOC end-to-end test.
- **Linux/macOS:** Owner explicitly defers physical tests to future testers; CI build PASS does not mean runtime PASS. Keep this limitation visible in release notes and bug reporting.
- **Unified candidate:** [run #38294692191](https://github.com/ibrahim1101/SentinelLab/actions/runs/38294692191) PASS; all four platform build jobs plus source gate used `b9b7958e720d93db6191614c07d2c01e7945643d`.
- **Release metadata checked:** GitHub draft release ID `410702970`, tag `v0.1.0-alpha`, `target_commitish=b9b7958e720d93db6191614c07d2c01e7945643d`, `draft=true`, `prerelease=true`.
- **Attached binary digests:** All five installer asset SHA-256 digests match the hashes documented in `docs/ALPHA_CANDIDATE_ARTIFACT_SHA256_2026-10-13.md`. `SHA256SUMS.txt` is attached; the manifest's exact content should also be checked if not already done.
- **Licensing:** **BLOCKED / NOT SIGNED OFF.** The two Emergent packages are listed as frontend dev dependencies; `frontend/craco.config.js` only loads its overlay for nonproduction builds. This reduces concern about bundling that overlay but does **not** prove that the original generated source, branded artwork, third-party dependencies, or required notices are redistributable.
- **SOC end-to-end validation:** Not completed; experimental claims only.
- **Decision:** Technical alpha candidate assembled; publication remains on hold pending license/provenance rights and explicit owner approval. Do not publish automatically. No additional release branch or rebuild required unless a blocker is discovered.
