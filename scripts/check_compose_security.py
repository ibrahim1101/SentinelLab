#!/usr/bin/env python3
"""Fail closed on unsafe defaults in the public beta Compose configuration.

Dependency-free static checks. Run: python scripts/check_compose_security.py
This checks the repository's default compose.yaml, not runtime firewall or TLS.
"""
from pathlib import Path
import sys


def check(compose_text):
    problems = []
    required = (
        "JWT_SECRET: ${JWT_SECRET:?Set JWT_SECRET in .env}",
        "ADMIN_PASSWORD: ${ADMIN_PASSWORD:?Set ADMIN_PASSWORD in .env}",
        "ENABLE_DEMO_ACCOUNTS: ${ENABLE_DEMO_ACCOUNTS:-false}",
        "127.0.0.1:8000:8000",
        "127.0.0.1:8080:80",
        "condition: service_healthy",
        "mongo_data:/data/db",
    )
    for marker in required:
        if marker not in compose_text:
            problems.append(f"Missing secure Compose marker: {marker}")
    if "27017:27017" in compose_text:
        problems.append("MongoDB port must not be published to the host")
    return problems


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    errors = check((root / "compose.yaml").read_text())
    for error in errors:
        print(f"FAIL: {error}")
    if errors:
        sys.exit(1)
    print("PASS: baseline Compose security markers")
