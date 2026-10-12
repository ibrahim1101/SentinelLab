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
