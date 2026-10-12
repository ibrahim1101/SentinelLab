#!/usr/bin/env python3
"""Verify dependency lockfiles are present and structurally match the manifests."""
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
errors = []
for part in ("frontend", "desktop"):
    manifest = json.loads((root / part / "package.json").read_text(encoding="utf-8"))
    lock_path = root / part / "package-lock.json"
    if not lock_path.exists():
        errors.append(f"{lock_path.relative_to(root)} missing; generate with npm install --package-lock-only")
        continue
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    top = lock.get("packages", {}).get("", {})
    for section in ("dependencies", "devDependencies"):
        for name, spec in manifest.get(section, {}).items():
            if top.get(section, {}).get(name) != spec:
                errors.append(f"{part}: {section} {name} differs from lockfile")
cargo = root / "desktop/src-tauri/Cargo.lock"
if not cargo.exists():
    errors.append("desktop/src-tauri/Cargo.lock missing; generate using cargo generate-lockfile")
else:
    import tomllib
    parsed = tomllib.loads(cargo.read_text(encoding="utf-8"))
    if not parsed.get("package"):
        errors.append("Cargo.lock has no package records")
if errors:
    print("LOCKFILE VERIFICATION FAILED:")
    for issue in errors:
        print(" -", issue)
    sys.exit(1)
print("Dependency lockfile structure verified; this is NOT a license compliance audit.")
