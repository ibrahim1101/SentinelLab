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
