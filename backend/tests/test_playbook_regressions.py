"""Regression coverage for manual playbook execution and disconnected response actions."""
import asyncio
from unittest.mock import AsyncMock, patch
import os
import sys
from pathlib import Path

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "sentinellab_test")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import playbooks


def run(pb, *, alert=None, dry_run=True, approvals=()):
    return asyncio.run(playbooks.execute(
        pb, "org-training", alert, {"email": "analyst@example.com"},
        dry_run=dry_run, approvals=approvals,
    ))


def test_manual_malware_enrichment_skips_without_alert():
    result = run(playbooks.PLAYBOOK_MAP["malware_triage"])
    enrich = next(step for step in result["steps"] if step["action"] == "enrich_iocs")
    assert enrich["status"] == "skipped"
    assert result["status"] == "completed_with_skips"
    assert not any(step["status"] == "error" for step in result["steps"])


def test_approved_edr_action_is_simulated_not_containment():
    pb = {"id": "edr-test", "name": "EDR test", "severity": "high", "steps": [
        {"id": "isolate", "name": "Isolate", "action": "isolate_host", "approval": True}
    ]}
    with patch.object(playbooks.db.automation_executions, "insert_one", new_callable=AsyncMock):
        result = run(pb, dry_run=False, approvals=["isolate"])
    assert result["steps"][0]["status"] == "simulated"
    assert "no live system connected" in result["steps"][0]["detail"]
    assert result["status"] == "completed"


def test_unapproved_action_requires_approval():
    pb = {"id": "approval-test", "name": "Approval", "severity": "high", "steps": [
        {"id": "isolate", "name": "Isolate", "action": "isolate_host", "approval": True}
    ]}
    with patch.object(playbooks.db.automation_executions, "insert_one", new_callable=AsyncMock):
        result = run(pb, dry_run=False)
    assert result["status"] == "needs_approval"
    assert result["steps"][0]["status"] == "pending_approval"
