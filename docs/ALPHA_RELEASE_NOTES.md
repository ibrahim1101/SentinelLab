# SentinelLab v0.1.0-alpha — release candidate notes

> **Experimental prerelease.** Not recommended for production security operations or exposure to untrusted networks. Use only synthetic or authorized test data.

## Packages

- **Windows x64:** unsigned NSIS `.exe` installer; Windows has received hands-on installation and basic functional testing.
- **Linux x64:** unsigned `.deb` and `.AppImage`; GitHub Actions packaging and bundled-backend import smoke tests passed, but no hands-on Linux runtime test has been performed.
- **macOS Intel:** unsigned `.dmg`; GitHub Actions packaging and bundled-backend import smoke tests passed, but no hands-on macOS runtime test has been performed.
- **macOS Apple Silicon:** unsigned `.dmg`; same CI-only validation and runtime caveat.

Build evidence: [Linux and macOS workflow run #38260680147](https://github.com/ibrahim1101/SentinelLab/actions/runs/38260680147). Windows installer workflow: [Windows Desktop Alpha Installer](https://github.com/ibrahim1101/SentinelLab/actions/workflows/windows-desktop-alpha.yml).

**Important:** Workflow artifacts expire; copy the verified installer files into GitHub Release assets rather than using workflow artifact links as permanent download links.

## Prerequisites

- **MongoDB Community Server is a separate installation** and must be running. For a local-only evaluation, bind MongoDB to `127.0.0.1:27017` and do not expose an unauthenticated MongoDB instance to the internet.
- Local AI via Ollama requires a separately installed/running Ollama service and a compatible model. Cloud AI provider keys are optional.
- Webhook integrations require a reachable HTTPS destination; only share data with endpoints you trust.
- On macOS and Windows, unsigned alpha applications may trigger operating-system security warnings. Do not disable system-wide security protections to install this build.

## Included in the alpha

- Tauri desktop UI with bundled FastAPI backend sidecar.
- React SOC/SIEM interface backed by MongoDB.
- Role-aware authentication, temporary lockouts, audit logging, and related regression tests.
- Configurable OpenAI-compatible AI assistant, including local Ollama.
- Outgoing webhook integration with Discord and other configured provider formats.
- Existing ingestion, alerting, investigations, and SOC/SIEM capabilities are **experimental**; comprehensive end-to-end validation is still in progress.

## Validation status

- Windows: manually checked installer, MongoDB connection indicator, admin/non-admin login, desktop close behavior, AI assistant, and Discord webhook delivery.
- Linux x64: CI built `.deb` and `.AppImage`; backend self-test passed. **Installation/runtime untested.**
- macOS Intel and Apple Silicon: CI built `.dmg`; backend self-test passed. **Installation/runtime untested.**
- Automated security workflows have passed on the consolidated main branch. This is not an independent security audit.

## Known limitations

- MongoDB is not bundled; desktop packages are **not** zero-dependency installers.
- Linux/macOS behavior may differ from Windows; please report installation and startup bugs with OS version, package type, and redacted logs.
- Packages are unsigned; no macOS notarization or Windows code signing.
- Production-grade hardening, complete SOC detection accuracy, full integration testing, and advanced third-party threat-intelligence integrations are outside the initial alpha scope.
- Do not paste secrets, tokens, personal information, or sensitive incident evidence into public GitHub issues.

## Bug reports

Use [GitHub Issues](https://github.com/ibrahim1101/SentinelLab/issues) with your OS/version, package name, reproduction steps, expected vs actual behavior, and **sanitized** error logs. For suspected vulnerabilities, contact the maintainer privately rather than opening a public issue.

## Release checklist

- [x] Linux x64 and macOS Intel/Apple Silicon packaging and bundled-backend import checks passed.
- [x] Basic Windows hands-on desktop and integration checks completed.
- [x] Confirm a current Windows installer artifact passes CI on main (run 38265416099).
- [x] Initial release draft contains five installer packages and SHA256SUMS.txt; **re-verify checksums if replacing assets with newer main builds**.
- [ ] Publish `v0.1.0-alpha` as a **GitHub prerelease**, with the untested-platform warnings prominently visible.
- [ ] Download-test the published release assets and monitor bug reports.


## Consolidated main branch and asset provenance (2026-10-12)

- PR #1 merged at `35a2456`; repository has one branch, `main`.
- Windows desktop packaging on main: [run 38265416099](https://github.com/ibrahim1101/SentinelLab/actions/runs/38265416099), passed.
- Linux/macOS desktop packaging on main: [run 38265421720](https://github.com/ibrahim1101/SentinelLab/actions/runs/38265421720), passed.
- Login security and Phase 1 security workflows passed on main: [38265992950](https://github.com/ibrahim1101/SentinelLab/actions/runs/38265992950), [38265992719](https://github.com/ibrahim1101/SentinelLab/actions/runs/38265992719).
- Existing draft release assets originate from earlier passing CI builds at `4f9b1b6`, before the merge. The post-merge source comparison found no application-source changes; only CI workflow changes. The newer main artifacts have **not** been substituted into the draft.
- Release is still a **draft**, not published. User accepts Linux/macOS CI-only packages for an experimental alpha and will address OS-specific bugs reported by testers.
