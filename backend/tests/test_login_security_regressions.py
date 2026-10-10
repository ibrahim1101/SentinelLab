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


if __name__ == "__main__":
    unittest.main()
