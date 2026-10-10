#!/usr/bin/env python3
"""Release gate report. Unchecked P0 items always block publication.

Usage: python scripts/check_release_gates.py
Exit code 1 means NO-GO. This cannot independently verify checked evidence.
"""
from pathlib import Path
import re
import sys


def evaluate(document):
    match = re.search(r"^## P0 — mandatory before public beta\s*$([\s\S]*?)(?=^## |\Z)", document, re.M)
    if not match:
        return ["P0 section missing"], []
    section = match.group(1)
    pending = re.findall(r"^- \[ \] (.+)$", section, re.M)
    checked = re.findall(r"^- \[[xX]\] (.+)$", section, re.M)
    if not pending and not checked:
        return ["No P0 checklist items found"], []
    return pending, checked


if __name__ == "__main__":
    path = Path(__file__).resolve().parents[1] / "docs" / "BETA_RELEASE_GATES.md"
    pending, checked = evaluate(path.read_text(encoding="utf-8"))
    print(f"P0 complete: {len(checked)}; P0 outstanding: {len(pending)}")
    for item in pending:
        print(f"BLOCKER: {item}")
    if pending:
        print("NO-GO: v0.9.0 public beta release gates are not complete")
        sys.exit(1)
    print("Checklist complete; independently verify evidence before tagging")
