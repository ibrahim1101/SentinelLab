"""SentinelLab Milestone 2 backend tests: MITRE coverage, Threat-Intel IOC
manager (CRUD + CSV/STIX import + scan + hits), and Incident-Response Playbooks
(list, dry-run, live run with approval gating, execution history)."""
import os
import json
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://soc-command-12.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@sentinellab.io", "password": "Sentinel@2026"}
ANALYST = {"email": "analyst@sentinellab.io", "password": "Analyst@2026"}
TRAIN = "org-training"


@pytest.fixture(scope="session")
def admin_tok():
    r = requests.post(f"{API}/auth/login", json=ADMIN, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def analyst_tok():
    r = requests.post(f"{API}/auth/login", json=ANALYST, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def H(tok, org=TRAIN):
    return {"Authorization": f"Bearer {tok}", "X-Workspace-Id": org, "Content-Type": "application/json"}


# ================================ MITRE ================================
class TestMitre:
    def test_coverage_shape(self, admin_tok):
        r = requests.get(f"{API}/mitre/coverage", headers=H(admin_tok), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("version", "tactics", "techniques", "coverage_pct",
                  "covered_count", "total", "gaps", "gap_count"):
            assert k in d, f"missing key {k}"
        assert d["total"] == len(d["techniques"]) == 36
        assert d["covered_count"] + d["gap_count"] == d["total"]
        assert 0 <= d["coverage_pct"] <= 100
        assert isinstance(d["tactics"], list) and len(d["tactics"]) == 12

    def test_coverage_known_techniques_covered(self, admin_tok):
        d = requests.get(f"{API}/mitre/coverage", headers=H(admin_tok), timeout=30).json()
        by_id = {t["id"]: t for t in d["techniques"]}
        # must be covered by enabled seeded rules
        for tid in ["T1110", "T1110.003", "T1046", "T1059.001", "T1078", "T1136", "T1071"]:
            assert tid in by_id, f"{tid} missing in techniques"
            assert by_id[tid]["covered"] is True, f"{tid} expected covered, got {by_id[tid]}"

    def test_coverage_includes_rule_mappings(self, admin_tok):
        d = requests.get(f"{API}/mitre/coverage", headers=H(admin_tok), timeout=30).json()
        by_id = {t["id"]: t for t in d["techniques"]}
        rules_for_t1110 = by_id["T1110"]["rules"]
        assert isinstance(rules_for_t1110, list) and len(rules_for_t1110) >= 1
        for r in rules_for_t1110:
            assert {"id", "name", "severity"}.issubset(r.keys())

    def test_coverage_gaps_are_uncovered(self, admin_tok):
        d = requests.get(f"{API}/mitre/coverage", headers=H(admin_tok), timeout=30).json()
        for g in d["gaps"]:
            assert g["covered"] is False
        assert d["gap_count"] == len(d["gaps"])


# ================================ THREAT INTEL ================================
class TestIndicatorsCRUD:
    def test_list_shape_and_stats(self, analyst_tok):
        r = requests.get(f"{API}/indicators", headers=H(analyst_tok), timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "indicators" in d and "stats" in d
        for t in ["ip", "domain", "url", "hash", "email"]:
            assert t in d["stats"]
            assert isinstance(d["stats"][t], int)

    def test_create_get_update_delete(self, analyst_tok):
        payload = {"ioc_type": "ip", "value": "TEST_203.0.113.77", "confidence": 85,
                   "source": "pytest", "tags": ["TEST_", "pytest"]}
        c = requests.post(f"{API}/indicators", headers=H(analyst_tok), json=payload, timeout=30)
        assert c.status_code == 200, c.text
        ind = c.json()
        assert ind["value"] == payload["value"]
        assert ind["ioc_type"] == "ip"
        assert ind["active"] is True
        assert ind["false_positive"] is False
        assert "_id" not in ind  # no mongo id leak
        ind_id = ind["id"]

        # GET verify persisted
        lst = requests.get(f"{API}/indicators?q=TEST_203", headers=H(analyst_tok), timeout=30).json()
        assert any(i["id"] == ind_id for i in lst["indicators"])

        # Update: mark false-positive
        up = requests.put(f"{API}/indicators/{ind_id}", headers=H(analyst_tok),
                          json={"false_positive": True, "active": False}, timeout=30)
        assert up.status_code == 200
        assert up.json()["false_positive"] is True
        assert up.json()["active"] is False

        # Delete
        de = requests.delete(f"{API}/indicators/{ind_id}", headers=H(analyst_tok), timeout=30)
        assert de.status_code == 200 and de.json()["ok"] is True
        after = requests.get(f"{API}/indicators?q=TEST_203", headers=H(analyst_tok), timeout=30).json()
        assert not any(i["id"] == ind_id for i in after["indicators"])

    def test_hits_endpoint(self, analyst_tok):
        # Create an IP indicator for a value that exists in Training Lab events
        # Fetch an event to borrow its src_ip
        ev = requests.get(f"{API}/events?page_size=1", headers=H(analyst_tok), timeout=30).json()
        src_ip = None
        for e in ev.get("events", []):
            if e.get("src_ip"):
                src_ip = e["src_ip"]; break
        if not src_ip:
            pytest.skip("no event with src_ip available")
        payload = {"ioc_type": "ip", "value": src_ip, "confidence": 90, "source": "pytest-hits", "tags": ["TEST_"]}
        c = requests.post(f"{API}/indicators", headers=H(analyst_tok), json=payload, timeout=30)
        if c.status_code == 200:
            ind_id = c.json()["id"]
        else:
            # already exists — look it up
            lst = requests.get(f"{API}/indicators?q={src_ip}", headers=H(analyst_tok), timeout=30).json()
            ind_id = lst["indicators"][0]["id"]
        try:
            hits = requests.get(f"{API}/indicators/{ind_id}/hits", headers=H(analyst_tok), timeout=30)
            assert hits.status_code == 200, hits.text
            dd = hits.json()
            assert "indicator" in dd and "hits" in dd and "count" in dd
            assert dd["indicator"]["value"] == src_ip
            assert dd["count"] >= 1
            # Each hit should contain src_ip or dest_ip matching
            assert any(h.get("src_ip") == src_ip or h.get("dest_ip") == src_ip for h in dd["hits"])
        finally:
            requests.delete(f"{API}/indicators/{ind_id}", headers=H(analyst_tok), timeout=30)


class TestIndicatorsImportAndScan:
    def test_import_csv(self, analyst_tok):
        text = ("type,value,confidence,source,tags\n"
                "ip,TEST_198.51.100.9,88,pytest-csv,csv;TEST_\n"
                "domain,TEST_evilexample.test,70,pytest-csv,TEST_\n")
        r = requests.post(f"{API}/indicators/import", headers=H(analyst_tok),
                          json={"format": "csv", "data": text}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["parsed"] == 2
        assert d["imported"] >= 1  # at least first run inserts; dedupe on re-run
        # verify
        lst = requests.get(f"{API}/indicators?q=TEST_198.51.100.9", headers=H(analyst_tok), timeout=30).json()
        assert any(i["value"] == "TEST_198.51.100.9" for i in lst["indicators"])
        # cleanup
        for v in ("TEST_198.51.100.9", "TEST_evilexample.test"):
            for i in requests.get(f"{API}/indicators?q={v}", headers=H(analyst_tok), timeout=30).json()["indicators"]:
                requests.delete(f"{API}/indicators/{i['id']}", headers=H(analyst_tok), timeout=30)

    def test_import_stix(self, analyst_tok):
        bundle = {
            "type": "bundle", "id": "bundle--test",
            "objects": [
                {"type": "indicator", "id": "indicator--1", "name": "pytest-stix",
                 "pattern": "[ipv4-addr:value = 'TEST_192.0.2.44']",
                 "confidence": 75, "labels": ["malicious-activity", "TEST_"]},
                {"type": "indicator", "id": "indicator--2", "name": "pytest-stix",
                 "pattern": "[domain-name:value = 'TEST_stix-bad.example']",
                 "confidence": 65, "labels": ["TEST_"]},
            ],
        }
        r = requests.post(f"{API}/indicators/import", headers=H(analyst_tok),
                          json={"format": "stix", "data": json.dumps(bundle)}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["parsed"] == 2
        # cleanup
        for v in ("TEST_192.0.2.44", "TEST_stix-bad.example"):
            for i in requests.get(f"{API}/indicators?q={v}", headers=H(analyst_tok), timeout=30).json()["indicators"]:
                requests.delete(f"{API}/indicators/{i['id']}", headers=H(analyst_tok), timeout=30)

    def test_scan(self, analyst_tok):
        r = requests.post(f"{API}/indicators/scan?time_range=7d", headers=H(analyst_tok), timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "alerts_generated" in d and "events_scanned" in d
        assert isinstance(d["alerts_generated"], int) and d["alerts_generated"] >= 0
        assert d["events_scanned"] >= 1


# ================================ PLAYBOOKS ================================
class TestPlaybooks:
    def test_list_7_builtin(self, admin_tok):
        r = requests.get(f"{API}/playbooks", headers=H(admin_tok), timeout=30)
        assert r.status_code == 200
        pbs = r.json()["playbooks"]
        assert len(pbs) == 7
        ids = {p["id"] for p in pbs}
        assert {"brute_force", "suspicious_process", "phishing", "malware_triage",
                "compromised_account", "suspicious_network", "data_exfiltration"} <= ids
        for p in pbs:
            assert isinstance(p["steps"], list) and len(p["steps"]) >= 3
            assert any(s["approval"] for s in p["steps"])  # at least one approval gate

    def test_dry_run_no_persistence(self, analyst_tok):
        # pick a brute force alert if any
        alerts = requests.get(f"{API}/alerts?page_size=20", headers=H(analyst_tok), timeout=30).json()["alerts"]
        bf = next((a for a in alerts if "brute" in (a.get("title") or "").lower()), alerts[0] if alerts else None)
        alert_id = bf["id"] if bf else None

        inv_before = len(requests.get(f"{API}/investigations", headers=H(analyst_tok), timeout=30).json()["investigations"])
        execs_before = len(requests.get(f"{API}/playbooks/executions", headers=H(analyst_tok), timeout=30).json()["executions"])

        r = requests.post(f"{API}/playbooks/run", headers=H(analyst_tok),
                          json={"playbook_id": "brute_force", "alert_id": alert_id,
                                "dry_run": True, "approvals": []}, timeout=30)
        assert r.status_code == 200, r.text
        rec = r.json()
        assert rec["dry_run"] is True
        assert rec["investigation_id"] is None
        # approval-gated external steps simulated
        notify = next((s for s in rec["steps"] if s["step_id"] == "notify"), None)
        assert notify and notify["status"] == "simulated"
        assert "simulated" in (notify["detail"] or "").lower()

        inv_after = len(requests.get(f"{API}/investigations", headers=H(analyst_tok), timeout=30).json()["investigations"])
        execs_after = len(requests.get(f"{API}/playbooks/executions", headers=H(analyst_tok), timeout=30).json()["executions"])
        assert inv_after == inv_before, "dry-run must NOT create investigation"
        assert execs_after == execs_before, "dry-run must NOT persist execution"

    def test_live_run_creates_investigation_and_honors_approval(self, analyst_tok):
        alerts = requests.get(f"{API}/alerts?page_size=20", headers=H(analyst_tok), timeout=30).json()["alerts"]
        bf = next((a for a in alerts if "brute" in (a.get("title") or "").lower()), None)
        if not bf:
            pytest.skip("no brute_force alert available")
        alert_id = bf["id"]

        # live run WITHOUT approvals -> notify should be pending_approval, no external side-effect "ok"
        r1 = requests.post(f"{API}/playbooks/run", headers=H(analyst_tok),
                           json={"playbook_id": "brute_force", "alert_id": alert_id,
                                 "dry_run": False, "approvals": []}, timeout=30)
        assert r1.status_code == 200, r1.text
        rec1 = r1.json()
        assert rec1["dry_run"] is False
        assert rec1["investigation_id"], "live run should create investigation"
        notify1 = next((s for s in rec1["steps"] if s["step_id"] == "notify"), None)
        assert notify1 and notify1["status"] == "pending_approval"
        assert rec1["status"] in ("needs_approval", "completed")

        # investigation really persisted with tasks
        inv_resp = requests.get(f"{API}/investigations/{rec1['investigation_id']}",
                                headers=H(analyst_tok), timeout=30).json()
        inv = inv_resp.get("investigation", inv_resp)
        assert inv["id"] == rec1["investigation_id"]
        assert len(inv.get("tasks", [])) >= 3

        # execution persisted
        execs = requests.get(f"{API}/playbooks/executions", headers=H(analyst_tok), timeout=30).json()["executions"]
        assert any(e["id"] == rec1["id"] for e in execs)

        # live run WITH approval -> notify ok
        r2 = requests.post(f"{API}/playbooks/run", headers=H(analyst_tok),
                           json={"playbook_id": "brute_force", "alert_id": alert_id,
                                 "dry_run": False, "approvals": ["notify"]}, timeout=30)
        assert r2.status_code == 200, r2.text
        rec2 = r2.json()
        notify2 = next((s for s in rec2["steps"] if s["step_id"] == "notify"), None)
        assert notify2 and notify2["status"] == "ok"
        assert rec2["status"] == "completed"

    def test_run_unknown_playbook_404(self, analyst_tok):
        r = requests.post(f"{API}/playbooks/run", headers=H(analyst_tok),
                          json={"playbook_id": "nope", "dry_run": True}, timeout=30)
        assert r.status_code == 404
