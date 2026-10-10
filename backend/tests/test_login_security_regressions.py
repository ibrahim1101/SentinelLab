"""Isolated login regression tests; no real MongoDB or account data required."""
import asyncio
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "sentinellab_test")
os.environ.setdefault("JWT_SECRET", "ci-only-test-secret-not-for-production")
os.environ.setdefault("ADMIN_PASSWORD", "ci-only-test-password")

from fastapi import HTTPException, Response
import server


def request():
    return SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))


class LoginSecurityRegressions(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_username_never_reports_account_locked(self):
        db = SimpleNamespace(
            users=SimpleNamespace(find_one=AsyncMock(return_value=None)),
            login_attempts=SimpleNamespace(
                find_one=AsyncMock(return_value={
                    "count": 5, "locked_until": "2099-01-01T00:00:00+00:00"
                }),
                delete_one=AsyncMock(),
                update_one=AsyncMock(),
            ),
        )
        with patch.object(server, "db", db):
            with self.assertRaises(HTTPException) as caught:
                await server.login(server.LoginReq(email="nonexistent-user", password="wrong"),
                                   request(), Response())
        self.assertEqual(caught.exception.status_code, 401)
        self.assertEqual(caught.exception.detail, "Invalid credentials")

    async def test_unknown_username_first_failure_is_generic(self):
        db = SimpleNamespace(
            users=SimpleNamespace(find_one=AsyncMock(return_value=None)),
            login_attempts=SimpleNamespace(
                find_one=AsyncMock(return_value=None),
                update_one=AsyncMock(),
            ),
        )
        with patch.object(server, "db", db):
            with self.assertRaises(HTTPException) as caught:
                await server.login(server.LoginReq(email="missing-user", password="wrong"),
                                   request(), Response())
        self.assertEqual(caught.exception.status_code, 401)
        self.assertEqual(caught.exception.detail, "Invalid credentials")

    async def test_locked_account_rejected_before_password_verification(self):
        user = {
            "id": "test-user", "email": "test@example.invalid", "username": "testuser",
            "login_locked_until": "2099-01-01T00:00:00+00:00",
            "enabled": True, "password_hash": "unused"
        }
        db = SimpleNamespace(
            users=SimpleNamespace(find_one=AsyncMock(return_value=user)),
            login_attempts=SimpleNamespace(find_one=AsyncMock(return_value=None)),
        )
        with patch.object(server, "db", db), patch.object(server, "verify_password") as verify:
            with self.assertRaises(HTTPException) as caught:
                await server.login(server.LoginReq(email="testuser", password="correct"),
                                   request(), Response())
        self.assertEqual(caught.exception.status_code, 423)
        verify.assert_not_called()

    async def test_fifth_failure_locks_once_and_creates_incident(self):
        user = {"id": "u1", "email": "analyst@example.invalid", "username": "analyst",
                "enabled": True, "password_hash": "hashed"}
        users = SimpleNamespace(
            find_one=AsyncMock(return_value=user),
            find_one_and_update=AsyncMock(return_value={"login_failed_count": 5}),
            update_one=AsyncMock(return_value=SimpleNamespace(modified_count=1)),
        )
        db = SimpleNamespace(
            users=users,
            login_attempts=SimpleNamespace(find_one=AsyncMock(return_value=None),
                                           update_one=AsyncMock()),
            security_notifications=SimpleNamespace(insert_one=AsyncMock()),
        )
        with patch.object(server, "db", db), patch.object(server, "verify_password", return_value=False):
            with self.assertRaises(HTTPException) as caught:
                await server.login(server.LoginReq(email="analyst", password="wrong"), request(), Response())
        self.assertEqual(caught.exception.status_code, 423)
        db.security_notifications.insert_one.assert_awaited_once()

    async def test_unlock_resolves_incident_and_clears_attempts(self):
        db = SimpleNamespace(
            users=SimpleNamespace(find_one=AsyncMock(return_value={
                "id": "u1", "email": "analyst@example.invalid", "username": "analyst"
            }), update_one=AsyncMock()),
            login_attempts=SimpleNamespace(delete_many=AsyncMock()),
            security_notifications=SimpleNamespace(update_many=AsyncMock()),
        )
        with patch.object(server, "db", db), patch.object(server, "audit", new_callable=AsyncMock) as audit:
            result = await server.admin_unlock_login("u1", actor={"id": "admin", "default_org": "org-training"})
        self.assertEqual(result, {"ok": True})
        self.assertEqual(db.login_attempts.delete_many.await_count, 2)
        db.security_notifications.update_many.assert_awaited_once()
        audit.assert_awaited_once()

    async def test_password_recovery_revokes_existing_sessions(self):
        db = SimpleNamespace(users=SimpleNamespace(
            find_one=AsyncMock(return_value={"id": "u1"}),
            update_one=AsyncMock(),
        ))
        with patch.object(server, "db", db), patch.object(server, "hash_password", return_value="new-hash"), patch.object(server, "audit", new_callable=AsyncMock):
            result = await server.admin_reset_password(
                "u1", server.AdminPasswordReq(password="new-test-password-123"),
                actor={"id": "admin", "default_org": "org-training"})
        self.assertEqual(result, {"ok": True})
        args = db.users.update_one.await_args.args
        self.assertEqual(args[1]["$inc"]["session_version"], 1)



if __name__ == "__main__":
    unittest.main()
