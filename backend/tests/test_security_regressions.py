"""Phase 1 security regressions. Run with pytest from backend/."""
import ast
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def test_safe_regex_rejects_unbounded_quantifiers(monkeypatch):
    monkeypatch.setenv("MONGO_URL", "mongodb://localhost:27017")
    monkeypatch.setenv("DB_NAME", "sentinellab_test")
    from detection import safe_regex_search
    assert safe_regex_search("aaaa", "(a+)+$") is False
    assert safe_regex_search("aaaa", "a+") is False
    assert safe_regex_search("admin", "^admin$") is True
    assert safe_regex_search("x" * 5000, "x") is False
    assert safe_regex_search("foo", "[") is False

def test_event_search_escapes_literal_input():
    source = Path(__file__).resolve().parents[1].joinpath("server.py").read_text()
    assert 're.escape(q[:128])' in source

def test_ai_alert_context_is_org_scoped():
    source = Path(__file__).resolve().parents[1].joinpath("ai_assistant.py").read_text()
    assert '"org_id": org_id, "id": {"$in": a.get("related_events", [])[:10]}' in source

def test_nonpersistent_detection_has_no_write_paths():
    source = Path(__file__).resolve().parents[1].joinpath("detection.py").read_text()
    assert "if matched and persist:" in source
    assert "if not persist:\n                continue" in source
    assert "if persist:\n            await db.detection_rules.update_one" in source
