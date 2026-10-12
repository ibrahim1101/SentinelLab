# Third-party license and redistribution review

SentinelLab's original code is offered under **GPL-3.0-only**; see [../LICENSE](../LICENSE). Copyright (C) 2026 Shaik Ibrahim for original work owned by that copyright holder.

This declaration does **not** transfer copyright in external components or automatically relicense code/assets the maintainer does not own. The application originated from an Emergent-generated prototype, and the frontend includes Emergent-specific packages; verify the relevant terms and ownership rights before redistribution.

## Known third-party components to review

- **Frontend:** React, Radix UI, Recharts, Lucide, CRACO, React Scripts and all npm dependencies, including transitive packages. In `frontend/package.json`, `@emergentbase/overlay` and `@emergentbase/visual-edits` are downloaded from `assets.emergent.sh`. Check whether these development dependencies or any associated assets are shipped in final bundles, and whether their terms permit redistribution.
- **Desktop:** Tauri 2, Rust crates, bundled platform resources and icon assets. Verify icon provenance and license.
- **Backend:** FastAPI, Starlette, Motor/PyMongo, cryptography, PyJWT, bcrypt, httpx and other Python packages. Preserve applicable notices and corresponding-source obligations.
- **MongoDB:** Not bundled in desktop installers. Users install MongoDB Community Server separately. Do not claim SentinelLab's GPL covers MongoDB itself.
- **AI models:** Ollama and any downloaded models are separately obtained and licensed. The app's GPL does not relicense model weights or hosted APIs.
- **External services:** Discord, Slack, Teams and other providers have their own API terms; using them does not imply endorsement.

## Before public release

1. Generate a third-party license inventory from the exact npm, Python and Cargo lockfiles used for packaging, including transitive dependencies.
2. Review licenses for compatibility with GPLv3 and check for missing copyright/notice obligations.
3. Review Emergent-origin generated source, artwork and proprietary dev dependencies. Replace any material that cannot be legally redistributed.
4. Bundle required license/notice texts and GPLv3 corresponding-source information with the downloadable binaries or their distribution page.
5. Ensure the source matching the shipped binaries is available, with build/install scripts and modifications where required.
6. Review whether a standalone `NOTICE` or `THIRD_PARTY_NOTICES` file is needed after inventory completion.

**Status: OPEN — legal and dependency-license audit is not complete.** This is a release-compliance checkpoint, not a legal opinion.


## 2026-10-12 source and build audit — actionable findings

**Completed:** The repository-root `LICENSE` contains GPL version 3; SPDX `GPL-3.0-only` metadata has now been added to `frontend/package.json`, `desktop/package.json` and `desktop/src-tauri/Cargo.toml`. These declarations describe original project code only; they do not override third-party terms.

**Confirmed gaps in the `main` tree:**
- No committed `frontend/yarn.lock`, `frontend/package-lock.json`, `desktop/package-lock.json`, or `desktop/src-tauri/Cargo.lock` was present during this audit. This means an exact transitive dependency/license inventory **cannot** be certified from committed source alone.
- Both desktop CI workflows currently run `npm install --no-audit --no-fund` for frontend and desktop, and Rust resolves dependencies during the Tauri build. There is no lockfile-enforced `npm ci`/equivalent path yet.
- The frontend manifest has two Emergent-hosted development packages: `@emergentbase/overlay` and `@emergentbase/visual-edits`. Their redistribution rights and actual inclusion in production bundles remain **unverified**.
- Python runtime dependencies are enumerated in `backend/requirements.runtime.txt`, but transitive versions are not fully pinned. `cryptography>=44,<47` is a range.
- Desktop CI invokes `pip install ... pyinstaller` without pinning PyInstaller, so build-tool provenance also varies.
- The branded image `frontend/public/Neon Global Shield Emblem.png` is used to generate installer icons. Its copyright/provenance and redistribution permission must be recorded.
- The existing draft release assets were built from an earlier source commit; updating license metadata on `main` does **not** update those already-uploaded binaries.

### Required evidence for a distributable alpha

1. **Dependency snapshots:** Generate and commit or archive verified lockfiles for frontend, desktop and Rust. Record exact Python transitive versions from the packaging environment. Do not fabricate an inventory from direct dependencies alone.
2. **License inventory:** Generate package name, resolved version, SPDX license and notice/source URL for each distributed npm, Python and Cargo component; manually review unknown/multiple/proprietary entries and actual packaging contents.
3. **Asset provenance:** Confirm legal rights for Emergent-origin code and the shield image; replace or exclude anything not redistributable.
4. **Binary compliance:** Provide GPLv3 license and required third-party notices in a location accessible to recipients. Provide the corresponding source and build/install scripts for the exact binaries conveyed; document where recipients can retrieve them.
5. **Release provenance:** Select the final release commit, rerun platform builds, download and checksum the actual artifacts, compare with release `SHA256SUMS.txt`, and document commit-to-asset mapping.
6. **Alpha truthfulness:** Preserve warnings for unsigned packages, separate MongoDB installation, CI-only Linux/macOS verification and incomplete SOC end-to-end testing.

**Gate decision: BLOCKED for compliance sign-off.** The project may continue technical prerelease preparation, but do not mark dependency licensing or exact binary/source correspondence verified until the above evidence exists. This is an engineering checklist, not legal advice.


## 2026-10-12 follow-up: auditable declaration export

Added `scripts/export_dependency_declarations.py` and the **Dependency Declaration Inventory** GitHub Actions workflow. It exports a downloadable CSV of *direct* npm, Python runtime and Cargo manifest declarations, explicitly marking each license `UNVERIFIED`. This is a first-stage review input, **not** a resolved transitive SBOM or license compatibility certification. It does not change runtime dependency resolution or existing desktop packaging. The next stage is to produce committed lockfiles, resolved inventories, actual license notices and matching release binary provenance.


## 2026-10-12 — CI result and lockfile gate

- [Dependency Declaration Inventory workflow](https://github.com/ibrahim1101/SentinelLab/actions/runs/38280984240) **PASSED**. The resulting CSV is an input to audit, not license clearance.
- [Windows desktop alpha](https://github.com/ibrahim1101/SentinelLab/actions/runs/38280161331) **PASSED** and [Linux/macOS desktop alpha](https://github.com/ibrahim1101/SentinelLab/actions/runs/38280160969) **PASSED** at commit `1fdc8f88`. These are not the final release source commit.
- Added `scripts/verify_dependency_lockfiles.py` to enforce that committed frontend/desktop npm lockfiles reflect their manifests and that a Cargo lockfile exists. **Not yet enabled as a required CI gate**, because the repository still lacks those lockfiles. This avoids breaking the working installer workflows before the files are generated.
- Required follow-up: run `npm install --package-lock-only --ignore-scripts` separately in `frontend` and `desktop`, then `cargo generate-lockfile` in `desktop/src-tauri`, inspect dependency changes, commit generated lockfiles, and run `python scripts/verify_dependency_lockfiles.py`. Prefer isolated builds and check proprietary package accessibility. Only then change CI to `npm ci` and `cargo --locked`.
- Lockfiles improve reproducibility but **do not prove** license compliance, binary integrity or supply-chain safety.


## Lockfile generation workflow (manual review stage)

A manually triggered [Generate Dependency Lockfiles (Review Required)](../.github/workflows/generate-dependency-lockfiles.yml) workflow now exists. It checks out `main`, uses Node 22 and Rust stable, runs `npm install --package-lock-only --ignore-scripts --no-audit --no-fund` in `frontend/` and `desktop/`, runs `cargo generate-lockfile` in `desktop/src-tauri/`, then validates all three using `python scripts/verify_dependency_lockfiles.py`. If successful, it uploads the three lockfiles plus SHA-256 hashes as an artifact named `SentinelLab-Generated-Lockfiles-Review-Only`.

**Operator action:** GitHub → Actions → **Generate Dependency Lockfiles (Review Required)** → **Run workflow** (select `main`). Download the artifact and review package changes, external registries, licensing and vulnerabilities before committing files to their corresponding directories. This workflow does **not** push commits, update installers, or publish releases. If npm fails because of the Emergent-hosted tarballs, document the failure and review whether those dependencies are needed for production before changing them. Do not remove packages solely to make the workflow pass.

**Status:** workflow committed; execution and resulting lockfiles **not yet verified**. The existing installer workflows remain unchanged until reviewed lockfiles are committed.


## 2026-10-12 — Generated lockfiles verified in CI

The [manual lockfile generation run #38283628307](https://github.com/ibrahim1101/SentinelLab/actions/runs/38283628307) **PASSED** and uploaded artifact `SentinelLab-Generated-Lockfiles-Review-Only` (artifact ID `11762596650`, SHA-256 digest `2ee1d7def99ebaab9749c801c799aaf2e9f7e1bd52184a078544c1f8dc49684a`). Its archive contains npm lockfile v3 for frontend (1,553 package records), npm lockfile v3 for desktop (13 package records), a Rust `Cargo.lock`, and manifest/lockfile SHA-256 hashes. These are **generated**, not yet merged into `main`, and their license obligations remain unaudited.

Updated the manual workflow to **attempt opening a review pull request** for generated lockfiles on branch `chore/review-generated-dependency-lockfiles` after validation. It still uploads artifacts. The PR step needs repository Actions permission to create pull requests; if GitHub disables that permission, enable **Settings → Actions → General → Allow GitHub Actions to create and approve pull requests** or review and commit the artifact files manually. The new PR behavior has **not yet been tested**. Do not switch desktop packaging to `npm ci` / `cargo --locked` until reviewed lockfiles merge.


## 2026-10-12 — Follow-up after generated-lockfile run

Checked open pull requests after workflow run #38283628307: **none were open**. That successful run used the earlier artifact-only workflow revision; it did not test the later PR creation step. No lockfiles have been committed to `main` yet. Added `scripts/audit_lockfile_sources.py` to flag npm packages whose resolved source is not `registry.npmjs.org`; subsequent manual lockfile runs include `dependency-source-review.csv` in their artifact. Treat flagged sources as review targets, not automatically malicious. The next run must validate both PR creation and source report; if PR creation fails due repository policy, use the downloaded artifact and a reviewed manual commit.


## 2026-10-12 — Lockfile merge and reproducible build gate

PR [#2](https://github.com/ibrahim1101/SentinelLab/pull/2) merged as `33f8c051`: committed frontend npm lockfile (1,553 package records), desktop npm lockfile (13 package records), and Cargo lockfile (431 packages). Both npm lockfiles have integrity hashes for resolved dependencies. The only nonstandard npm resolved sources found in review are `@emergentbase/overlay` and `@emergentbase/visual-edits`, from `assets.emergent.sh`; their redistribution status remains **OPEN**.

Windows and Linux/macOS packaging workflows now run `scripts/verify_dependency_lockfiles.py`, use `npm ci`, and request Tauri `--locked` builds. **These updated desktop workflows have not yet been observed passing.** A successful older desktop run does not verify these changes. If any new workflow fails, fix it before releasing; do not revert to floating installs silently. This improves deterministic resolution, not third-party license clearance or guaranteed bit-for-bit identical binaries.


## 2026-10-13 — Emergent output rights and logo provenance review

**Emergent-generated application source:** Official Emergent documentation at https://help.emergent.sh/your-data-ownership and Terms at https://app.emergentagent.com/terms-of-service (sections 7.2–7.3) expressly state that users own generated application code and may modify, distribute, commercialize and open-source it, subject to third-party licenses. Thus, the fact that SentinelLab began as an Emergent-generated app is **not by itself a redistribution blocker**. These permissions do not extend to Emergent's proprietary platform components or override dependencies' own licenses.

**Emergent dev-only packages:** `@emergentbase/overlay` and `@emergentbase/visual-edits` remain in frontend devDependencies. The overlay in `frontend/craco.config.js` is conditionally loaded only for development, not production. Actual shipped binary inspection is still required to rule out other proprietary inclusions; do not assume package installation implies redistribution.

**Artwork:** The owner reports the SentinelLab shield/logo was generated for this project by ChatGPT. Record as user-commissioned AI-generated artwork, not Emergent-provided artwork, based on owner attestation. No third-party stock image origin was reported. AI-generated artwork may not be uniquely copyrightable; ownership/uniqueness guarantees are not inferred.

**Open issues for public binary distribution:** (1) complete resolved npm/Python/Rust license and notice inventory, (2) identify which notices/license files are conveyed with the five installers, (3) document GPLv3 corresponding-source access for exact binary source commit `b9b7958e720d93db6191614c07d2c01e7945643d`, and (4) confirm whether any Emergent proprietary runtime component is actually bundled. Current review is a technical compliance audit, not a legal opinion.

**Revised finding:** Emergent-generated code rights are supported by published vendor terms. **Overall third-party notice/binary compliance remains OPEN**, and publication is not certified as fully compliant.


## 2026-10-13 — Consolidated single-pass frozen-lockfile audit

**Scope:** Inspected the exact release candidate commit `b9b7958e720d93db6191614c07d2c01e7945643d`, including both npm lockfiles, the Cargo lockfile, frontend build configuration and Python runtime requirements. This is a consolidated audit of accessible metadata; **not a completed binary-level license clearance**.

- **Frontend npm:** 1,552 resolved package records: 1,292 MIT; 75 ISC; 43 CC0-1.0; 42 BSD-3-Clause; 41 Apache-2.0; 41 BSD-2-Clause; 2 Unlicense; 2 0BSD; 12 other SPDX expressions; 1 UNLICENSED; 3 without license metadata. The unusual-license count is based on the frozen npm lockfile, not an assertion of infringement.
- **Desktop npm:** 12 resolved package records; all declare `Apache-2.0 OR MIT`.
- **Cargo:** frozen lockfile available with package names, versions, checksums; Cargo.lock does **not** include license metadata, so the Rust license inventory is not independently certified by this check.
- **Python:** `backend/requirements.runtime.txt` has 14 declared runtime packages, but `cryptography>=44,<47` is not exact, and no resolved transitive wheel/license inventory for the frozen CI sidecar was available in this audit.
- **Non-registry npm sources:** exactly two, `@emergentbase/overlay@0.1.31` (lockfile license `UNLICENSED`) and `@emergentbase/visual-edits@1.0.12` (no license metadata). Both are declared devDependencies; overlay configuration gates its use to nonproduction. **No proof that neither package is present in the shipped binary was obtained.** Do not bundle or redistribute these proprietary packages absent permission.
- **Other frontend exceptions:** `axe-core@4.14.0` MPL-2.0; `harmony-reflect@1.6.2` (Apache-2.0 OR MPL-1.1); `node-forge@1.4.0` (BSD-3-Clause OR GPL-2.0); missing lockfile license metadata for `exit@0.1.2` and `esprima@1.2.5` (nested jsonpath dependency). Verify applicable license texts and whether these development/transitive packages are conveyed.
- **Generated source:** Emergent's official terms grant the user rights to distribute and open-source generated application code, subject to third-party licenses. The logo was reported by the owner as ChatGPT-generated.
- **GPL source:** repository has GPLv3 `LICENSE` and frozen release source commit; actual compliance with binary-distribution corresponding-source and notice requirements has not been demonstrated.
- **Actual release assets:** five uploaded installers match recorded candidate SHA-256 digests; a checksum manifest is uploaded, but manifest content and shipped notices have not been fully independently audited.

**Final finding:** No evidence from package manifests alone that the shipped binaries contain a forbidden proprietary Emergent component; equally, no proof of exclusion. **Compliance sign-off is NOT GRANTED** because the shipped binary composition, Rust/Python transitive license inventories, and delivery of notices/corresponding source remain unverified. Do not present this metadata-only audit as a completed legal clearance. These are the concrete remaining evidence gaps, not additional feature-development tasks.
