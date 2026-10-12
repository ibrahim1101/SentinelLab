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
