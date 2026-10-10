"""Dependency-light security regression checks."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_all_backend_modules_compile():
    for path in ROOT.glob("*.py"):
        ast.parse(path.read_text(), filename=str(path))

def test_search_regex_inputs_are_escaped():
    source = (ROOT / "server.py").read_text()
    assert '{"$regex": q, "$options": "i"}' not in source
    assert '{"$regex": str(value), "$options": "i"}' not in source
    assert 'f"^{v}$"' not in source
    assert 're.escape(q[:128])' in source
    assert 're.escape(str(value)[:128])' in source
    assert 're.escape(v[:256])' in source

def test_ai_context_is_scoped():
    source = (ROOT / "ai_assistant.py").read_text()
    assert '"org_id": org_id, "id": {"$in": a.get("related_events", [])[:10]}' in source

def test_detection_replay_is_read_only():
    source = (ROOT / "detection.py").read_text()
    assert "if matched and persist:" in source
    assert "if not persist:\\n                continue".replace("\\n", "\n") in source
    assert "if persist:\\n            await db.detection_rules.update_one".replace("\\n", "\n") in source
    assert '"org_id": org_id, "id": {"$in": list(matched)}' in source

def test_regex_policy_is_bounded():
    source = (ROOT / "detection.py").read_text()
    assert "len(pattern) > 128" in source
    assert "len(str(value)) > 4096" in source


def test_alert_detail_joins_are_tenant_scoped():
    source = (ROOT / "server.py").read_text()
    alert_detail = source.split('async def alert_detail(', 1)[1].split('@api.put("/alerts/{alert_id}")', 1)[0]
    assert '"org_id": org' in alert_detail
    assert 'db.events.find({"id": {"$in": a.get("related_events", [])}, "org_id": org}' in alert_detail
    assert 'db.detection_rules.find_one({"id": a.get("rule_id"), "org_id": org}' in alert_detail


def test_playbook_mutations_include_tenant_scope():
    """Fail the existing CI suite if playbook writes lose org_id isolation."""
    tree = ast.parse((ROOT / "playbooks.py").read_text())
    collection_names = {"alerts", "investigations"}
    checked = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "update_one" or not node.args:
            continue
        collection = node.func.value
        if not isinstance(collection, ast.Attribute) or collection.attr not in collection_names:
            continue
        if not isinstance(collection.value, ast.Name) or collection.value.id != "db":
            continue
        selector = node.args[0]
        assert isinstance(selector, ast.Dict), "Playbook mutation must use a literal scoped selector"
        keys = [key.value for key in selector.keys if isinstance(key, ast.Constant)]
        assert "org_id" in keys, f"Playbook {collection.attr} update_one is missing org_id"
        checked.append(collection.attr)
    assert checked.count("alerts") >= 1
    assert checked.count("investigations") >= 2


# Include the behavioral playbook regressions in the existing Phase 1 security
# pytest invocation until the dedicated workflow is independently verified.
# Pytest collects imported test_* functions from this module.
from test_playbook_regressions import (
    test_manual_malware_enrichment_skips_without_alert,
    test_approved_edr_action_is_simulated_not_containment,
    test_unapproved_action_requires_approval,
    test_playbook_alert_link_is_tenant_scoped,
    test_playbook_investigation_mutations_are_tenant_scoped,
)


def _production_reconciliation_source():
    source = (ROOT / "server.py").read_text()
    return source.split('async def reconcile_production_access(', 1)[1].split('\n@api.', 1)[0]


def test_production_reconciliation_is_read_only_for_membership():
    """Recovery may finalize request state, but must never grant membership."""
    source = _production_reconciliation_source()
    tree = ast.parse("async def reconcile_production_access(" + source)
    writes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in {"update_one", "update_many", "replace_one", "insert_one", "find_one_and_update"}:
                writes.append(ast.unparse(node.func.value))
    assert writes == ["db.production_access_requests"], (
        "Reconciliation must not write user memberships or other collections"
    )


def test_production_reconciliation_requires_stale_applying_state():
    source = _production_reconciliation_source()
    assert '{"id": request_id, "status": "applying"}' in source
    assert 'timedelta(minutes=5)' in source
    assert 'HTTPException(409, "Approval may still be in progress' in source
    assert 'HTTPException(404, "Applying request not found")' in source


def test_production_reconciliation_checks_membership_and_cas():
    source = _production_reconciliation_source()
    assert 'PROD_ORG in target.get("org_ids", [])' in source
    assert 'final_status = "approved" if granted else "failed"' in source
    assert '"failure_reason": None if granted else "membership_not_present"' in source
    assert 'result.modified_count != 1' in source
    assert '"status": "applying"' in source


def test_docker_registry_retry_helper_is_bounded_and_configurable():
    """Prevent accidental removal of the Docker Hub transient-failure workaround."""
    script = (ROOT.parent / "scripts" / "pull-mongo-with-retry.sh").read_text()
    assert 'set -euo pipefail' in script
    assert 'MONGO_IMAGE:-mongo:7' in script
    assert 'for attempt in 1 2 3 4 5' in script
    assert 'docker pull "$image"' in script
    assert 'exit 1' in script
