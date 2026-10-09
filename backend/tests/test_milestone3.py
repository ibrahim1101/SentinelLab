"""
Milestone 3 backend tests:
- /api/graph (Investigation Graph): entity-centric node/edge building, pivots
- /api/replay + /api/replay/samples (Detection Replay Lab): isolated non-persistent evaluation
- /api/observatory (Pipeline Observatory): real pipeline metrics
"""
import os
import json
import pytest
import requests

from dotenv import load_dotenv
load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL not set"
API = f"{BASE_URL}/api"
ADMIN = {"email": "admin@sentinellab.io", "password": "Sentinel@2026"}
ORG = "org-training"


# ----- fixtures -----
@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{API}/auth/login", json=ADMIN, timeout=30)
    assert r.status_code == 200, r.text
    return r.json().get("access_token") or r.json()["token"]


@pytest.fixture(scope="session")
def H(token):
    return {"Authorization": f"Bearer {token}", "X-Workspace-Id": ORG,
            "Content-Type": "application/json"}


# ----- Investigation Graph -----
class TestGraph:
    def test_graph_default_seeds_latest_alert(self, H):
        r = requests.post(f"{API}/graph", headers=H, json={}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "nodes" in d and "edges" in d
        assert len(d["nodes"]) > 0
        assert d["seed"]["type"] == "alert"
        types = {n["type"] for n in d["nodes"]}
        # Should contain the seed alert plus some linked entities
        assert "alert" in types

    def test_graph_seed_specific_alert(self, H):
        # fetch an alert id
        a = requests.get(f"{API}/alerts?limit=1", headers=H).json()
        alerts = a if isinstance(a, list) else a.get("alerts", a.get("items", []))
        assert alerts, "no alerts in training workspace"
        aid = alerts[0]["id"]
        r = requests.post(f"{API}/graph", headers=H,
                          json={"seed_type": "alert", "seed_value": aid}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        node_ids = {n["id"] for n in d["nodes"]}
        assert f"alert:{aid}" in node_ids
        # edges only reference existing nodes
        for e in d["edges"]:
            assert e["source"] in node_ids and e["target"] in node_ids

    def test_graph_seed_ip_entity(self, H):
        r = requests.post(f"{API}/graph", headers=H,
                          json={"seed_type": "ip", "seed_value": "203.0.113.9"}, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["seed"]["type"] == "ip"
        # center node must be present
        assert any(n["id"] == "ip:203.0.113.9" for n in d["nodes"])

    def test_graph_alert_not_found(self, H):
        r = requests.post(f"{API}/graph", headers=H,
                          json={"seed_type": "alert", "seed_value": "does-not-exist"}, timeout=30)
        assert r.status_code == 404


# ----- Detection Replay Lab -----
class TestReplay:
    def test_samples_endpoint(self, H):
        r = requests.get(f"{API}/replay/samples", headers=H, timeout=30)
        assert r.status_code == 200
        samples = r.json()["samples"]
        assert len(samples) == 3
        names = [s["name"] for s in samples]
        assert any("Brute Force" in n for n in names)
        for s in samples:
            assert "payload" in s and "expected_rules" in s and "format" in s

    def test_replay_brute_force_triggers_expected_rule(self, H):
        samples = requests.get(f"{API}/replay/samples", headers=H).json()["samples"]
        bf = next(s for s in samples if "Brute Force" in s["name"])
        payload = json.loads(bf["payload"])
        r = requests.post(f"{API}/replay", headers=H, json={
            "format": "json", "payload": payload,
            "expected_rules": bf["expected_rules"]}, timeout=60)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["isolated"] is True
        assert d["parsed_events"] == len(payload)
        assert d["comparison"] is not None
        # expected rule must be matched (unexpected extras tolerated — other
        # workspace rules may legitimately also fire on this telemetry)
        assert "Brute Force Authentication" in d["comparison"]["matched"]
        assert d["comparison"]["missing"] == []

    def test_replay_does_not_persist_alerts_or_events(self, H):
        # alert count before
        before_alerts = requests.get(f"{API}/alerts?limit=1000", headers=H).json()
        before_count = len(before_alerts if isinstance(before_alerts, list)
                           else before_alerts.get("alerts", before_alerts.get("items", [])))
        before_events = requests.get(f"{API}/events?limit=1", headers=H).json()
        before_ev_total = before_events.get("total") if isinstance(before_events, dict) else None

        samples = requests.get(f"{API}/replay/samples", headers=H).json()["samples"]
        for s in samples:
            payload = json.loads(s["payload"])
            r = requests.post(f"{API}/replay", headers=H, json={
                "format": "json", "payload": payload,
                "expected_rules": s["expected_rules"]}, timeout=60)
            assert r.status_code == 200

        after_alerts = requests.get(f"{API}/alerts?limit=1000", headers=H).json()
        after_count = len(after_alerts if isinstance(after_alerts, list)
                          else after_alerts.get("alerts", after_alerts.get("items", [])))
        assert after_count == before_count, (
            f"Replay persisted alerts! before={before_count} after={after_count}")

        if before_ev_total is not None:
            after_events = requests.get(f"{API}/events?limit=1", headers=H).json()
            after_ev_total = after_events.get("total")
            assert after_ev_total == before_ev_total, "Replay persisted events!"

    def test_replay_comparison_detects_failure(self, H):
        # supplying nonsense expected rule should produce a failing comparison with missing
        r = requests.post(f"{API}/replay", headers=H, json={
            "format": "json", "payload": [],
            "expected_rules": ["Nonexistent Rule XYZ"]}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["comparison"]["passed"] is False
        assert "Nonexistent Rule XYZ" in d["comparison"]["missing"]


# ----- Pipeline Observatory -----
class TestObservatory:
    def test_observatory_shape(self, H):
        r = requests.get(f"{API}/observatory", headers=H, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ["eps_current", "total_indexed", "events_last_1h",
                  "parser_failures", "avg_ingest_delay_s", "eps_series",
                  "source_health", "recent_errors", "sources_total", "sources_online"]:
            assert k in d, f"missing key {k}"
        assert isinstance(d["eps_series"], list)
        assert isinstance(d["source_health"], list)
        # total indexed should be > 0 in synthetic workspace
        assert d["total_indexed"] > 0

    def test_source_health_rows_well_formed(self, H):
        d = requests.get(f"{API}/observatory", headers=H).json()
        for s in d["source_health"]:
            for k in ["id", "name", "status", "throughput_1h", "parse_errors"]:
                assert k in s
