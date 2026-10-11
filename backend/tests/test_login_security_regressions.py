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
                find_one_and_update=AsyncMock(),
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
                find_one_and_update=AsyncMock(),
            ),
        )
        with patch.object(server, "db", db):
            with self.assertRaises(HTTPException) as caught:
                await server.login(server.LoginReq(email="missing-user", password="wrong"),
                                   request(), Response())
        self.assertEqual(caught.exception.status_code, 401)
        self.assertEqual(caught.exception.detail, "Invalid credentials")

    async def test_duplicate_first_upsert_retries_without_another_insert(self):
        from pymongo.errors import DuplicateKeyError

        attempts = SimpleNamespace(
            find_one=AsyncMock(return_value=None),
            find_one_and_update=AsyncMock(side_effect=[
                DuplicateKeyError("simulated concurrent first insert"),
                {"identifier": "127.0.0.1:missing-user", "count": 2},
            ]),
        )
        db = SimpleNamespace(
            users=SimpleNamespace(find_one=AsyncMock(return_value=None)),
            login_attempts=attempts,
        )
        with patch.object(server, "db", db):
            with self.assertRaises(HTTPException) as caught:
                await server.login(server.LoginReq(email="missing-user", password="wrong"),
                                   request(), Response())
        self.assertEqual(caught.exception.status_code, 401)
        self.assertEqual(attempts.find_one_and_update.await_count, 2)
        self.assertTrue(attempts.find_one_and_update.await_args_list[0].kwargs["upsert"])
        self.assertFalse(attempts.find_one_and_update.await_args_list[1].kwargs["upsert"])

    async def test_locked_account_requires_correct_password_for_lock_message(self):
        user = {
            "id": "test-user", "email": "test@example.invalid", "username": "testuser",
            "login_locked_until": "2099-01-01T00:00:00+00:00",
            "enabled": True, "password_hash": "unused"
        }
        db = SimpleNamespace(
            users=SimpleNamespace(find_one=AsyncMock(return_value=user)),
            login_attempts=SimpleNamespace(find_one=AsyncMock(return_value=None)),
        )
        with patch.object(server, "db", db), patch.object(server, "verify_password", return_value=True) as verify:
            with self.assertRaises(HTTPException) as caught:
                await server.login(server.LoginReq(email="testuser", password="correct"),
                                   request(), Response())
        self.assertEqual(caught.exception.status_code, 423)
        verify.assert_called_once()

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
                                           find_one_and_update=AsyncMock()),
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
            login_attempts=SimpleNamespace(delete_many=AsyncMock(), update_one=AsyncMock()),
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


    async def test_second_failure_does_not_trigger_source_throttle(self):
        user = {"id": "u1", "email": "analyst@example.invalid",
                "username": "analyst", "enabled": True, "password_hash": "hashed"}
        db = SimpleNamespace(
            users=SimpleNamespace(
                find_one=AsyncMock(return_value=user),
                find_one_and_update=AsyncMock(return_value={"login_failed_count": 2}),
            ),
            login_attempts=SimpleNamespace(
                find_one=AsyncMock(return_value={"count": 1, "locked_until": "2099-01-01T00:00:00+00:00"}),
                find_one_and_update=AsyncMock(),
                delete_one=AsyncMock(),
            ),
        )
        with patch.object(server, "db", db), patch.object(server, "verify_password", return_value=False):
            with self.assertRaises(HTTPException) as caught:
                await server.login(server.LoginReq(email="analyst", password="wrong"), request(), Response())
        self.assertEqual(caught.exception.status_code, 401)
        self.assertEqual(caught.exception.detail, "Invalid credentials")
        db.login_attempts.find_one_and_update.assert_awaited_once()
        pipeline = db.login_attempts.find_one_and_update.await_args.args[1]
        self.assertIsNone(pipeline[1]["$set"]["locked_until"]["$cond"][2])


    async def test_five_concurrent_failures_create_one_lock_incident(self):
        user = {"id": "u1", "email": "analyst@example.invalid",
                "username": "analyst", "enabled": True, "password_hash": "hashed"}
        state = {"failures": 0, "locked": False, "incidents": 0}
        guard = asyncio.Lock()

        async def increment(*args, **kwargs):
            async with guard:
                if state["locked"]:
                    return None
                state["failures"] += 1
                return {"login_failed_count": state["failures"]}

        async def claim(*args, **kwargs):
            async with guard:
                if state["locked"] or state["failures"] < 5:
                    return SimpleNamespace(modified_count=0)
                state["locked"] = True
                return SimpleNamespace(modified_count=1)

        async def incident(*args, **kwargs):
            state["incidents"] += 1

        db = SimpleNamespace(
            users=SimpleNamespace(find_one=AsyncMock(return_value=user),
                                  find_one_and_update=AsyncMock(side_effect=increment),
                                  update_one=AsyncMock(side_effect=claim)),
            login_attempts=SimpleNamespace(find_one=AsyncMock(return_value=None),
                                           find_one_and_update=AsyncMock()),
            security_notifications=SimpleNamespace(insert_one=AsyncMock(side_effect=incident)),
        )
        with patch.object(server, "db", db), patch.object(server, "verify_password", return_value=False):
            async def fail():
                try:
                    await server.login(server.LoginReq(email="analyst", password="wrong"),
                                       request(), Response())
                except HTTPException as exc:
                    return exc.status_code
                return 200
            statuses = await asyncio.gather(*(fail() for _ in range(5)))
        self.assertEqual(len(statuses), 5)
        self.assertNotIn(200, statuses)
        self.assertTrue(state["locked"])
        self.assertEqual(state["failures"], 5)
        self.assertEqual(state["incidents"], 1)


    async def test_expired_account_lock_resets_failed_counter(self):
        user = {"id": "u1", "email": "analyst@example.invalid", "username": "analyst",
                "enabled": True, "role": "analyst", "password_hash": "hashed", "login_failed_count": 5,
                "login_locked_until": "2000-01-01T00:00:00+00:00"}
        db = SimpleNamespace(
            users=SimpleNamespace(
                find_one=AsyncMock(return_value=user),
                update_one=AsyncMock(return_value=SimpleNamespace(matched_count=1)),
            ),
            login_attempts=SimpleNamespace(
                find_one=AsyncMock(return_value=None), delete_one=AsyncMock(),
            ),
        )
        with patch.object(server, "db", db), patch.object(server, "verify_password", return_value=True), \
             patch.object(server, "create_access_token", return_value="test-token"), \
             patch.object(server, "audit", new_callable=AsyncMock):
            result = await server.login(server.LoginReq(email="analyst", password="correct"),
                                        request(), Response())
        self.assertEqual(result["access_token"], "test-token")
        self.assertEqual(db.users.update_one.await_count, 2)
        first_update = db.users.update_one.await_args_list[0].args[1]
        self.assertIn("login_failed_count", first_update["$unset"])

    async def test_disabled_account_correct_password_is_rejected(self):
        user = {"id": "u1", "email": "analyst@example.invalid", "username": "analyst",
                "enabled": False, "password_hash": "hashed"}
        db = SimpleNamespace(
            users=SimpleNamespace(find_one=AsyncMock(return_value=user)),
            login_attempts=SimpleNamespace(find_one=AsyncMock(return_value=None),
                                           delete_one=AsyncMock()),
        )
        with patch.object(server, "db", db), patch.object(server, "verify_password", return_value=True):
            with self.assertRaises(HTTPException) as caught:
                await server.login(server.LoginReq(email="analyst", password="correct"),
                                   request(), Response())
        self.assertEqual(caught.exception.status_code, 403)
        self.assertIn("disabled", caught.exception.detail.lower())


    async def test_existing_username_source_throttle_is_generic(self):
        user = {"id": "u1", "username": "analyst",
                "email": "analyst@example.invalid", "password_hash": "hashed",
                "enabled": True, "role": "analyst"}
        db = SimpleNamespace(
            users=SimpleNamespace(find_one=AsyncMock(return_value=user)),
            login_attempts=SimpleNamespace(find_one=AsyncMock(return_value={
                "count": 5, "locked_until": "2099-01-01T00:00:00+00:00"
            })),
        )
        with patch.object(server, "db", db):
            with self.assertRaises(HTTPException) as caught:
                await server.login(server.LoginReq(email="analyst", password="wrong"),
                                   request(), Response())
        self.assertEqual(caught.exception.status_code, 401)
        self.assertEqual(caught.exception.detail, "Invalid credentials")


    async def test_locked_account_wrong_password_does_not_reveal_lock(self):
        user = {"id": "test-user", "email": "test@example.invalid",
                "username": "testuser", "password_hash": "hashed",
                "login_locked_until": "2099-01-01T00:00:00+00:00"}
        db = SimpleNamespace(
            users=SimpleNamespace(find_one=AsyncMock(return_value=user)),
            login_attempts=SimpleNamespace(find_one=AsyncMock(return_value=None)),
        )
        with patch.object(server, "db", db), patch.object(server, "verify_password", return_value=False):
            with self.assertRaises(HTTPException) as caught:
                await server.login(server.LoginReq(email="testuser", password="wrong"),
                                   request(), Response())
        self.assertEqual(caught.exception.status_code, 401)
        self.assertEqual(caught.exception.detail, "Invalid credentials")



if __name__ == "__main__":
    unittest.main()
