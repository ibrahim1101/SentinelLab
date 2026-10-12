#!/usr/bin/env python3
"""List nonstandard npm lockfile sources for manual provenance review."""
import csv
import json
import pathlib
import sys
from urllib.parse import urlparse

root = pathlib.Path(__file__).resolve().parents[1]
output = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("dependency-source-review.csv")
rows = []
for part in ("frontend", "desktop"):
    path = root / part / "package-lock.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for name, record in data.get("packages", {}).items():
        if not name:
            continue
        resolved = record.get("resolved", "")
        if not resolved:
            continue
        parsed = urlparse(resolved)
        if parsed.scheme in ("http", "https") and parsed.hostname == "registry.npmjs.org":
            continue
        rows.append((part, name, record.get("version", ""), resolved, "REVIEW"))
output.parent.mkdir(parents=True, exist_ok=True)
with output.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(("component", "package_path", "version", "resolved_source", "status"))
    writer.writerows(rows)
print(f"Found {len(rows)} nonstandard resolved npm sources requiring review; report: {output}")
print("This does not certify licensing, vulnerability status or source authenticity.")
