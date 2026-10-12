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
