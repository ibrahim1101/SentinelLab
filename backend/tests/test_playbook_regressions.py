"""Regression coverage for manual playbook execution and disconnected response actions."""
import asyncio
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace
import os
import sys
from pathlib import Path

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "sentinellab_test")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import playbooks


# Reuse one loop: Motor binds its client to the first active event loop.
_TEST_LOOP = asyncio.new_event_loop()


def run(pb, *, alert=None, dry_run=True, approvals=()):
    return _TEST_LOOP.run_until_complete(playbooks.execute(
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
    with patch.object(playbooks, "db", SimpleNamespace(automation_executions=SimpleNamespace(insert_one=AsyncMock()))):
        result = run(pb, dry_run=False, approvals=["isolate"])
    assert result["steps"][0]["status"] == "simulated"
    assert "no live system connected" in result["steps"][0]["detail"]
    assert result["status"] == "completed"


def test_unapproved_action_requires_approval():
    pb = {"id": "approval-test", "name": "Approval", "severity": "high", "steps": [
        {"id": "isolate", "name": "Isolate", "action": "isolate_host", "approval": True}
    ]}
    with patch.object(playbooks, "db", SimpleNamespace(automation_executions=SimpleNamespace(insert_one=AsyncMock()))):
        result = run(pb, dry_run=False)
    assert result["status"] == "needs_approval"
    assert result["steps"][0]["status"] == "pending_approval"


def test_playbook_alert_link_is_tenant_scoped():
    """Linking a case must never update a matching alert in another workspace."""
    pb = {"id": "case-test", "name": "Case test", "severity": "high", "steps": [
        {"id": "case", "name": "Open case", "action": "create_investigation", "approval": False}
    ]}
    alert = {"id": "shared-alert-id", "title": "Suspicious login", "severity": "high"}
    update_alert = AsyncMock()
    fake_db = SimpleNamespace(
        investigations=SimpleNamespace(insert_one=AsyncMock()),
        alerts=SimpleNamespace(update_one=update_alert),
        automation_executions=SimpleNamespace(insert_one=AsyncMock()),
    )
    with patch.object(playbooks, "db", fake_db):
        result = run(pb, alert=alert, dry_run=False)
    assert result["status"] == "completed"
    assert update_alert.await_args.args[0] == {
        "id": "shared-alert-id", "org_id": "org-training"
    }


def test_playbook_investigation_mutations_are_tenant_scoped():
    pb = {"id": "case-tasks-test", "name": "Case tasks", "severity": "high", "steps": [
        {"id": "case", "name": "Open case", "action": "create_investigation", "approval": False},
        {"id": "assign", "name": "Assign analyst", "action": "assign_analyst", "approval": False},
        {"id": "tasks", "name": "Add tasks", "action": "add_tasks", "approval": False,
         "tasks": ["Review evidence"]},
    ]}
    update_inv = AsyncMock()
    fake_db = SimpleNamespace(
        investigations=SimpleNamespace(insert_one=AsyncMock(), update_one=update_inv),
        automation_executions=SimpleNamespace(insert_one=AsyncMock()),
    )
    with patch.object(playbooks, "db", fake_db):
        result = run(pb, dry_run=False)
    assert result["status"] == "completed"
    assert update_inv.await_count == 2
    for call in update_inv.await_args_list:
        assert call.args[0]["org_id"] == "org-training"
        assert call.args[0]["id"] == result["investigation_id"]


def test_approved_external_actions_are_audit_only_and_persisted():
    """Every disconnected external action remains simulated even when approved."""
    actions = ("notify", "isolate_host", "block_indicator", "disable_account")
    pb = {"id": "external-simulation", "name": "External simulation", "severity": "high",
          "steps": [{"id": action, "name": action, "action": action, "approval": True}
                    for action in actions]}
    saved = AsyncMock()
    fake_db = SimpleNamespace(automation_executions=SimpleNamespace(insert_one=saved))
    with patch.object(playbooks, "db", fake_db):
        result = run(pb, dry_run=False, approvals=actions)
    assert result["status"] == "completed"
    assert [step["status"] for step in result["steps"]] == ["simulated"] * len(actions)
    assert all("no live system connected" in step["detail"] for step in result["steps"])
    saved.assert_awaited_once()
    persisted = saved.await_args.args[0]
    assert persisted["org_id"] == "org-training"
    assert persisted["dry_run"] is False
    assert [step["status"] for step in persisted["steps"]] == ["simulated"] * len(actions)


def test_unapproved_external_actions_never_execute_and_are_recorded_pending():
    """Every external action must remain pending without explicit approval."""
    actions = ("notify", "isolate_host", "block_indicator", "disable_account")
    pb = {"id": "external-pending", "name": "External pending", "severity": "high",
          "steps": [{"id": action, "name": action, "action": action, "approval": True}
                    for action in actions]}
    saved = AsyncMock()
    with patch.object(playbooks, "db", SimpleNamespace(
        automation_executions=SimpleNamespace(insert_one=saved)
    )):
        result = run(pb, dry_run=False)
    assert result["status"] == "needs_approval"
    assert all(step["status"] == "pending_approval" for step in result["steps"])
    saved.assert_awaited_once()
    assert all(step["status"] == "pending_approval"
               for step in saved.await_args.args[0]["steps"])
