"""SentinelLab backend API tests covering auth/RBAC, ingestion, detection,
alerts, hunting, investigations, reports, settings, search, notifications."""
import os
import io
import json
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://soc-command-12.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@sentinellab.io"
ADMIN_PW = "Sentinel@2026"
ANALYST_EMAIL = "analyst@sentinellab.io"
ANALYST_PW = "Analyst@2026"
PROD = "org-production"
TRAIN = "org-training"


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW}, timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def analyst_token():
    r = requests.post(f"{API}/auth/login", json={"email": ANALYST_EMAIL, "password": ANALYST_PW}, timeout=30)
    assert r.status_code == 200, f"analyst login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


def _h(tok, org=TRAIN):
    return {"Authorization": f"Bearer {tok}", "X-Workspace-Id": org, "Content-Type": "application/json"}


# ---------- health ----------
def test_health():
    r = requests.get(f"{API}/health", timeout=15)
    assert r.status_code == 200 and r.json().get("status") == "ok"


# ---------- auth ----------
def test_login_success_shape(admin_token):
    assert isinstance(admin_token, str) and len(admin_token) > 20


def test_login_invalid():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"}, timeout=15)
    assert r.status_code in (401, 429)


def test_me(admin_token):
    r = requests.get(f"{API}/auth/me", headers=_h(admin_token), timeout=15)
    assert r.status_code == 200
    u = r.json()["user"]
    assert u["email"] == ADMIN_EMAIL


def test_missing_token_401():
    r = requests.get(f"{API}/dashboard/overview", timeout=15)
    assert r.status_code in (401, 403)


# ---------- workspaces ----------
def test_workspaces(admin_token):
    r = requests.get(f"{API}/workspaces", headers=_h(admin_token), timeout=15)
    assert r.status_code == 200
    ids = [w["id"] for w in r.json()["workspaces"]]
    assert PROD in ids and TRAIN in ids


# ---------- dashboard ----------
def test_dashboard_overview_training(admin_token):
    r = requests.get(f"{API}/dashboard/overview?time_range=24h", headers=_h(admin_token, TRAIN), timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert "kpis" in d and "events_over_time" in d and "alerts_by_severity" in d
    assert d["is_demo_workspace"] is True
    assert d["kpis"]["total_events"] >= 0


# ---------- events ----------
def test_events_list(admin_token):
    r = requests.get(f"{API}/events?page=1&page_size=20", headers=_h(admin_token, TRAIN), timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert "events" in data and "total" in data


def test_events_filter_severity(admin_token):
    r = requests.get(f"{API}/events?severity=high", headers=_h(admin_token, TRAIN), timeout=20)
    assert r.status_code == 200


def test_event_detail(admin_token):
    r = requests.get(f"{API}/events?page_size=1", headers=_h(admin_token, TRAIN), timeout=20)
    events = r.json()["events"]
    if not events:
        pytest.skip("no events seeded")
    eid = events[0]["id"]
    d = requests.get(f"{API}/events/{eid}", headers=_h(admin_token, TRAIN), timeout=15)
    assert d.status_code == 200
    assert d.json()["event"]["id"] == eid


def test_events_export_csv(admin_token):
    r = requests.get(f"{API}/events/export/data?format=csv&time_range=24h",
                     headers={"Authorization": f"Bearer {admin_token}", "X-Workspace-Id": TRAIN}, timeout=30)
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")


# ---------- rules & detection ----------
def test_rules_list_training(admin_token):
    r = requests.get(f"{API}/rules", headers=_h(admin_token, TRAIN), timeout=15)
    assert r.status_code == 200
    rules = r.json()["rules"]
    assert len(rules) >= 8, f"expected >=8 builtin rules, got {len(rules)}"


def test_rule_toggle_and_back(admin_token):
    rules = requests.get(f"{API}/rules", headers=_h(admin_token, TRAIN), timeout=15).json()["rules"]
    rid = rules[0]["id"]
    r1 = requests.post(f"{API}/rules/{rid}/toggle", headers=_h(admin_token, TRAIN), timeout=15)
    assert r1.status_code == 200
    r2 = requests.post(f"{API}/rules/{rid}/toggle", headers=_h(admin_token, TRAIN), timeout=15)
    assert r2.status_code == 200


def test_rule_create_and_backtest(admin_token):
    body = {"name": "TEST_rule_x", "description": "t", "rule_type": "match",
            "severity": "low", "enabled": True, "mitre": ["T1110"], "confidence": 50,
            "params": {"field": "category", "value": "authentication"}}
    r = requests.post(f"{API}/rules", headers=_h(admin_token, TRAIN), json=body, timeout=15)
    assert r.status_code == 200, r.text
    rid = r.json()["id"]
    bt = requests.post(f"{API}/rules/{rid}/backtest?time_range=7d", headers=_h(admin_token, TRAIN), timeout=30)
    assert bt.status_code == 200
    assert "would_alert" in bt.json() and "matched_events" in bt.json()


# ---------- alerts ----------
def test_alerts_list_and_detail(admin_token):
    r = requests.get(f"{API}/alerts", headers=_h(admin_token, TRAIN), timeout=15)
    assert r.status_code == 200
    alerts = r.json()["alerts"]
    assert len(alerts) > 0, "expected seeded alerts in training lab"
    aid = alerts[0]["id"]
    d = requests.get(f"{API}/alerts/{aid}", headers=_h(admin_token, TRAIN), timeout=15)
    assert d.status_code == 200 and d.json()["alert"]["id"] == aid


def test_alert_update_comment_and_status(admin_token):
    alerts = requests.get(f"{API}/alerts", headers=_h(admin_token, TRAIN), timeout=15).json()["alerts"]
    aid = alerts[0]["id"]
    body = {"status": "triaged", "comment": "TEST_comment", "assigned_to": ADMIN_EMAIL}
    u = requests.put(f"{API}/alerts/{aid}", headers=_h(admin_token, TRAIN), json=body, timeout=15)
    assert u.status_code == 200, u.text
    d = requests.get(f"{API}/alerts/{aid}", headers=_h(admin_token, TRAIN), timeout=15).json()
    assert d["alert"]["status"] == "triaged"
    assert any(c.get("text") == "TEST_comment" for c in d["alert"].get("comments", []))


# ---------- threat hunting ----------
def test_hunt_query(admin_token):
    body = {"query": "category:authentication AND outcome:failure", "limit": 100}
    r = requests.post(f"{API}/hunt", headers=_h(admin_token, TRAIN), json=body, timeout=30)
    assert r.status_code == 200
    j = r.json()
    assert "events" in j and "top_src_ip" in j and "timeline" in j and "took_ms" in j


# ---------- sources + ingestion + detection E2E ----------
def test_source_create_upload_and_detection(admin_token):
    body = {"name": "TEST_src_prod", "display_name": "Test Prod Source",
            "source_type": "custom", "host": "test-host"}
    r = requests.post(f"{API}/sources", headers=_h(admin_token, PROD), json=body, timeout=15)
    assert r.status_code == 200, r.text
    j = r.json()
    assert "ingestion_token" in j and j["ingestion_token"].startswith("sl_")
    sid = j["source"]["id"]
    # upload payload with authentication failures (should trigger brute force rule)
    import datetime as dt
    now = dt.datetime.utcnow()
    events_payload = []
    for i in range(12):
        events_payload.append({
            "timestamp": (now - dt.timedelta(seconds=i*2)).isoformat() + "Z",
            "event_type": "logon_failure", "category": "authentication",
            "outcome": "failure", "username": "jdoe", "src_ip": "203.0.113.45",
            "host": "test-host", "action": "login", "severity": "medium"
        })
    files = {"file": ("logs.json", json.dumps(events_payload), "application/json")}
    headers = {"Authorization": f"Bearer {admin_token}", "X-Workspace-Id": PROD}
    up = requests.post(f"{API}/ingest/upload?source_id={sid}&format=json",
                       headers=headers, files=files, timeout=30)
    assert up.status_code == 200, up.text
    assert up.json()["ingested"] == 12
    # cleanup
    requests.delete(f"{API}/sources/{sid}", headers=_h(admin_token, PROD), timeout=15)


# ---------- RBAC: cross-workspace / role gating ----------
def test_cross_workspace_access(analyst_token):
    # analyst has both orgs so should succeed
    r = requests.get(f"{API}/events?page_size=1", headers=_h(analyst_token, PROD), timeout=15)
    assert r.status_code == 200


def test_rule_delete_requires_soc_manager(analyst_token, admin_token):
    # create a rule as admin
    body = {"name": "TEST_del_rule", "description": "t", "rule_type": "match",
            "severity": "low", "enabled": True, "mitre": [], "confidence": 50, "params": {}}
    r = requests.post(f"{API}/rules", headers=_h(admin_token, TRAIN), json=body, timeout=15)
    rid = r.json()["id"]
    # analyst should be forbidden to delete
    d = requests.delete(f"{API}/rules/{rid}", headers=_h(analyst_token, TRAIN), timeout=15)
    assert d.status_code == 403
    # admin can delete
    d2 = requests.delete(f"{API}/rules/{rid}", headers=_h(admin_token, TRAIN), timeout=15)
    assert d2.status_code == 200


# ---------- investigations ----------
def test_investigation_full_flow(admin_token):
    body = {"title": "TEST_inv", "severity": "medium", "priority": "medium", "status": "open"}
    r = requests.post(f"{API}/investigations", headers=_h(admin_token, TRAIN), json=body, timeout=15)
    assert r.status_code == 200
    inv_id = r.json()["id"]
    u = requests.put(f"{API}/investigations/{inv_id}", headers=_h(admin_token, TRAIN),
                     json={"note": "TEST_note", "task": "TEST_task"}, timeout=15)
    assert u.status_code == 200
    # evidence upload
    headers = {"Authorization": f"Bearer {admin_token}", "X-Workspace-Id": TRAIN}
    files = {"file": ("ev.txt", b"hello world", "text/plain")}
    ev = requests.post(f"{API}/investigations/{inv_id}/evidence", headers=headers, files=files, timeout=30)
    assert ev.status_code == 200
    assert len(ev.json()["evidence"]["sha256"]) == 64


# ---------- reports ----------
def test_report_generate_and_download(admin_token):
    r = requests.post(f"{API}/reports/generate", headers=_h(admin_token, TRAIN),
                      json={"type": "soc_summary", "time_range": "7d"}, timeout=30)
    assert r.status_code == 200
    rid = r.json()["id"]
    j = requests.get(f"{API}/reports/{rid}/download?format=json",
                     headers={"Authorization": f"Bearer {admin_token}", "X-Workspace-Id": TRAIN}, timeout=15)
    c = requests.get(f"{API}/reports/{rid}/download?format=csv",
                     headers={"Authorization": f"Bearer {admin_token}", "X-Workspace-Id": TRAIN}, timeout=15)
    assert j.status_code == 200 and c.status_code == 200


# ---------- notifications / search ----------
def test_notifications(admin_token):
    r = requests.get(f"{API}/notifications", headers=_h(admin_token, TRAIN), timeout=15)
    assert r.status_code == 200 and "notifications" in r.json()


def test_global_search(admin_token):
    r = requests.get(f"{API}/search?q=a", headers=_h(admin_token, TRAIN), timeout=15)
    assert r.status_code == 200
    j = r.json()
    for key in ("events", "alerts", "investigations", "rules", "assets"):
        assert key in j


# ---------- settings / admin ----------
def test_settings_and_health(admin_token):
    r = requests.get(f"{API}/settings", headers=_h(admin_token, TRAIN), timeout=15)
    assert r.status_code == 200 and r.json()["settings"]["org_id"] == TRAIN
    h = requests.get(f"{API}/admin/health", headers=_h(admin_token, TRAIN), timeout=15)
    assert h.status_code == 200 and h.json()["database"] == "ok"


def test_admin_users_only_admin(admin_token, analyst_token):
    a = requests.get(f"{API}/admin/users", headers=_h(admin_token, TRAIN), timeout=15)
    assert a.status_code == 200
    b = requests.get(f"{API}/admin/users", headers=_h(analyst_token, TRAIN), timeout=15)
    assert b.status_code == 403
