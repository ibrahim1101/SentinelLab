#!/usr/bin/env python3
"""Produce a source-manifest dependency inventory (NOT a resolved license audit)."""
import csv
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dependency-inventory.csv"
rows = []
for part in ("frontend", "desktop"):
    manifest = json.loads((ROOT / part / "package.json").read_text(encoding="utf-8"))
    for kind in ("dependencies", "devDependencies"):
        for name, spec in sorted(manifest.get(kind, {}).items()):
            rows.append((part, "npm", kind, name, spec, "UNVERIFIED", "direct manifest declaration only"))
req = ROOT / "backend/requirements.runtime.txt"
for line in req.read_text(encoding="utf-8").splitlines():
    value = line.split("#", 1)[0].strip()
    if not value:
        continue
    match = re.match(r"^([A-Za-z0-9_.-]+)\s*(.*)$", value)
    if match:
        rows.append(("backend", "pip", "runtime", match.group(1), match.group(2).strip() or "*", "UNVERIFIED", "direct runtime requirement only"))
cargo = (ROOT / "desktop/src-tauri/Cargo.toml").read_text(encoding="utf-8")
section = ""
for line in cargo.splitlines():
    line = line.strip()
    if line.startswith("[") and line.endswith("]"):
        section = line.strip("[]")
    elif section in ("dependencies", "build-dependencies") and "=" in line and not line.startswith("#"):
        name, spec = line.split("=", 1)
        rows.append(("desktop", "cargo", section, name.strip(), spec.strip(), "UNVERIFIED", "direct Cargo manifest declaration only"))
OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(("component", "ecosystem", "scope", "package", "declared_spec", "license_status", "evidence"))
    writer.writerows(rows)
print(f"Wrote {len(rows)} direct declarations to {OUT}")
print("WARNING: NOT a transitive SBOM or verified license inventory; do not use as release compliance sign-off.")
