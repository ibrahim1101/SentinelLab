#!/usr/bin/env python3
"""Verify installer artifact filenames and nonempty payloads; not a runtime test."""
import argparse
import pathlib
import sys
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument("artifact_zip", type=pathlib.Path)
parser.add_argument("--platform", required=True, choices=["windows", "linux", "macos"])
args = parser.parse_args()
expected = {"windows": (".exe",), "linux": (".deb", ".AppImage"), "macos": (".dmg",)}[args.platform]
with zipfile.ZipFile(args.artifact_zip) as archive:
    names = [i for i in archive.infolist() if not i.is_dir()]
    matching = [i for i in names if i.filename.endswith(expected)]
    if not matching:
        sys.exit(f"No {expected} installer found in {args.artifact_zip}")
    for item in matching:
        if item.file_size < 100_000:
            sys.exit(f"Suspiciously small installer: {item.filename} ({item.file_size} bytes)")
        print(f"OK: {item.filename} ({item.file_size:,} bytes)")
    if args.platform == "linux":
        present = {suffix for suffix in expected if any(i.filename.endswith(suffix) for i in matching)}
        if len(present) != len(expected):
            sys.exit(f"Linux artifact missing format: {set(expected) - present}")
print("Artifact structure checks passed. This does not validate execution, signatures, or malware safety.")
