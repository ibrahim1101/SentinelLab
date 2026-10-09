"""Black-box authentication and workspace boundary smoke tests for Compose."""
import os
import urllib.error
import urllib.request
import json

BASE = os.environ.get("SENTINELLAB_TEST_URL", "http://127.0.0.1:8080")

def request(method, path, data=None, token=None, workspace=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if workspace:
        headers["X-Workspace-Id"] = workspace
    payload = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(BASE + path, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())

status, _ = request("GET", "/api/workspaces")
assert status == 401, f"Anonymous workspace access returned {status}"
status, login = request("POST", "/api/auth/login", {"email": os.environ.get("ADMIN_EMAIL", "admin@sentinellab.io"), "password": os.environ["ADMIN_PASSWORD"]})
assert status == 200, f"Admin login returned {status}: {login}"
token = login["access_token"]
status, me = request("GET", "/api/auth/me", token=token)
assert status == 200 and me["user"]["email"] == os.environ.get("ADMIN_EMAIL", "admin@sentinellab.io"), f"Authenticated identity failed: {status}"
status, workspaces = request("GET", "/api/workspaces", token=token)
assert status == 200 and len(workspaces["workspaces"]) >= 1, f"Workspace listing failed: {status}"
status, _ = request("GET", "/api/workspaces", token="invalid-token")
assert status == 401, f"Invalid token returned {status}"
status, _ = request("GET", "/api/events", token=token, workspace="org-does-not-exist")
assert status == 403, f"Unauthorized workspace returned {status}; expected 403"
print("PASS: anonymous access, admin login, identity, workspace listing, invalid token, workspace isolation")
