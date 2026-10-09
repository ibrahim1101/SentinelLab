"""Black-box authentication and workspace boundary smoke tests for Compose."""
import os
import urllib.error
import urllib.request
import json
import uuid

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

# Create a disposable account and verify role-based access using live API calls.
email = "ci-" + uuid.uuid4().hex[:16] + "@example.com"
status, registered = request("POST", "/api/auth/register", {"email": email, "password": "ci-temporary-strong-password", "name": "CI Security Analyst"})
assert status == 200, f"Account registration failed: {status}: {registered}"
analyst_token = registered["access_token"]
analyst_id = registered["user"]["id"]
assert registered["user"]["org_ids"] == ["org-training"], "Self-registration granted unexpected tenant access"
assert registered["user"]["default_org"] == "org-training", "Self-registration selected privileged workspace"
status, _ = request("GET", "/api/events", token=analyst_token, workspace="org-production")
assert status == 403, f"Self-registered user accessed production: {status}"
status, _ = request("GET", "/api/admin/users", token=analyst_token)
assert status == 403, f"Analyst accessed admin users: {status}"
status, _ = request("DELETE", "/api/rules/nonexistent-rule", token=analyst_token)
assert status == 403, f"Analyst bypassed manager-only deletion: {status}"
status, _ = request("GET", "/api/events", token=analyst_token, workspace="org-foreign-tenant")
assert status == 403, f"Analyst accessed foreign tenant: {status}"
status, _ = request("PUT", "/api/admin/users/" + analyst_id + "/role", {"role": "auditor"}, token=token)
assert status == 200, f"Admin role update failed: {status}"
status, me = request("GET", "/api/auth/me", token=analyst_token)
assert status == 200 and me["user"]["role"] == "auditor", "Role update not reflected in identity"
status, _ = request("POST", "/api/rules", {"name": "forbidden-auditor-write"}, token=analyst_token)
assert status == 403, f"Auditor created rule: {status}"
status, _ = request("GET", "/api/events", token=analyst_token, workspace="org-foreign-tenant")
assert status == 403, f"Auditor accessed foreign tenant: {status}"
print("PASS: analyst/admin RBAC, manager-only mutation, auditor read-only, updated role, tenant boundaries")

# Exercise explicit membership review, grant, revoke and super-admin safeguards.
status, review = request("GET", "/api/admin/membership-review", token=analyst_token)
assert status == 403, f"Auditor accessed production membership review: {status}"
status, review = request("GET", "/api/admin/membership-review", token=token)
assert status == 200 and "production_members" in review, f"Super-admin membership review failed: {status}"
endpoint = "/api/admin/users/" + analyst_id + "/workspaces"
status, _ = request("PUT", endpoint, {"org_ids": ["org-training", "org-production"]}, token=analyst_token)
assert status == 403, f"Auditor changed workspace memberships: {status}"
status, _ = request("PUT", endpoint, {"org_ids": ["org-invalid"]}, token=token)
assert status == 400, f"Unknown workspace was accepted: {status}"
status, _ = request("PUT", endpoint, {"org_ids": ["org-training", "org-production"]}, token=token)
assert status == 409, f"Direct production grant bypassed approval: {status}"
status, pending = request("POST", "/api/admin/users/" + analyst_id + "/production-access-requests", token=token)
assert status == 200 and pending["status"] == "pending", f"Approval request failed: {status}: {pending}"
status, _ = request("POST", "/api/admin/production-access-requests/" + pending["id"] + "/approve", token=token)
assert status == 403, f"Requester approved their own production grant: {status}"
status, _ = request("GET", "/api/events", token=analyst_token, workspace="org-production")
assert status == 403, f"Pending production request prematurely granted access: {status}"
status, requests = request("GET", "/api/admin/production-access-requests", token=token)
assert status == 200 and any(x["id"] == pending["id"] for x in requests["requests"]), "Pending approval not listed"
status, _ = request("GET", "/api/admin/production-access-requests", token=analyst_token)
assert status == 403, f"Auditor read approval queue: {status}"
# Create a distinct second administrator to verify the successful approval path.
second_email = "ci-approver-" + uuid.uuid4().hex[:12] + "@example.com"
status, second = request("POST", "/api/auth/register", {"email": second_email, "password": "ci-temporary-strong-password", "name": "CI Second Approver"})
assert status == 200, f"Second approver registration failed: {status}: {second}"
second_id, second_token = second["user"]["id"], second["access_token"]
status, _ = request("PUT", "/api/admin/users/" + second_id + "/role", {"role": "admin"}, token=token)
assert status == 200, f"Admin role provisioning failed: {status}"
status, _ = request("PUT", "/api/admin/users/" + analyst_id + "/role", {"role": "super_admin"}, token=second_token)
assert status == 403, f"Ordinary admin escalated a user to super admin: {status}"
status, _ = request("PUT", "/api/admin/users/" + second_id + "/role", {"role": "super_admin"}, token=second_token)
assert status == 403, f"Ordinary admin self-promoted: {status}"
status, _ = request("PUT", "/api/admin/users/" + second_id + "/role", {"role": "super_admin"}, token=token)
assert status == 200, f"Super-admin provisioning failed: {status}"
status, _ = request("POST", "/api/admin/production-access-requests/" + pending["id"] + "/approve", token=second_token)
assert status == 200, f"Independent second administrator could not approve production access: {status}"
status, _ = request("GET", "/api/events", token=analyst_token, workspace="org-production")
assert status == 200, f"Approved production membership did not take effect: {status}"
status, _ = request("POST", "/api/admin/production-access-requests/" + pending["id"] + "/approve", token=second_token)
assert status == 404, f"Already approved request was reusable: {status}"
status, _ = request("POST", "/api/admin/production-access-requests/" + pending["id"] + "/reconcile", token=second_token)
assert status == 404, f"Completed approval could be reconciled again: {status}"
status, queue = request("GET", "/api/admin/production-access-requests", token=token)
assert status == 200 and any(x["id"] == pending["id"] and x["status"] == "approved" for x in queue["requests"]), "Approval did not reach terminal approved state"
status, revoked = request("PUT", endpoint, {"org_ids": ["org-training"]}, token=token)
assert status == 200 and revoked["default_org"] == "org-training", f"Production revocation failed: {status}: {revoked}"
status, _ = request("GET", "/api/events", token=analyst_token, workspace="org-production")
assert status == 403, f"Revoked production membership still worked: {status}"
status, _ = request("PUT", "/api/admin/users/" + second_id + "/workspaces", {"org_ids": ["org-training"]}, token=token)
assert status == 400, f"Super-admin production guard did not trigger: {status}"
print("PASS: independent second-admin approval, single-use request and production revocation")
admin_id = login["user"]["id"]
status, _ = request("PUT", "/api/admin/users/" + admin_id + "/workspaces", {"org_ids": ["org-training"]}, token=token)
assert status == 400, f"Super-admin production access was removable: {status}"
print("PASS: super-admin membership review, grant, revoke, invalid input and role protections")
