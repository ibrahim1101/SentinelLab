#!/usr/bin/env python3
"""Dependency-free post-deployment SentinelLab smoke checks.

Usage: python scripts/smoke_release.py --base-url http://127.0.0.1:8000
Exits nonzero if health/readiness fail or unauthenticated access is permitted.
Does not write records or require credentials.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request


def probe(base, path, timeout):
    request = urllib.request.Request(base.rstrip("/") + path,
                                     headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(65536)
    except urllib.error.HTTPError as error:
        return error.code, error.read(65536)


def run(base, timeout):
    failures = []
    for path in ("/api/health", "/api/ready"):
        try:
            status, body = probe(base, path, timeout)
            parsed = json.loads(body)
            ok = status == 200 and isinstance(parsed, dict)
            if path.endswith("/ready"):
                ok = ok and parsed.get("ready") is True
            print(f"{path}: HTTP {status}, {'PASS' if ok else 'FAIL'}")
            if not ok:
                failures.append(path)
        except (OSError, ValueError) as error:
            print(f"{path}: FAIL ({error})")
            failures.append(path)

    for path in ("/api/auth/me", "/api/dashboard/overview"):
        try:
            status, _ = probe(base, path, timeout)
            ok = status in (401, 403)
            print(f"{path} without credentials: HTTP {status}, {'PASS' if ok else 'FAIL'}")
            if not ok:
                failures.append(path)
        except OSError as error:
            print(f"{path}: FAIL ({error})")
            failures.append(path)
    return not failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=float, default=8)
    args = parser.parse_args()
    sys.exit(0 if run(args.base_url, args.timeout) else 1)
