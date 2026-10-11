"""MongoDB-backed login lockout integration test. Requires disposable CI MongoDB."""
import asyncio
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock
from uuid import uuid4

os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "sentinellab_ci_auth")
os.environ.setdefault("JWT_SECRET", "ci-integration-secret")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import HTTPException, Response
from motor.motor_asyncio import AsyncIOMotorClient
import server


class MongoLoginLockoutIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Hard safety gate: never run against an existing user database.
        self.assertEqual(os.environ.get("SENTINELLAB_TEST_DISPOSABLE_MONGO"), "yes")
        self.assertEqual(os.environ.get("DB_NAME"), "sentinellab_ci_auth")
        self.client = AsyncIOMotorClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=5000)
        await self.client.admin.command("ping")
        self.db = self.client["sentinellab_ci_auth"]
        # Match production startup: every concurrent-upsert test needs the unique index.
        await server.ensure_unique_login_throttle_index(self.db.login_attempts)
        self.username = "integration_" + uuid4().hex[:16]
        self.user_id = str(uuid4())
        await self.db.users.insert_one({
            "id": self.user_id, "username": self.username,
            "email": self.username + "@example.invalid",
            "password_hash": "unused", "enabled": True, "role": "analyst",
            "login_failed_count": 0,
        })

    async def asyncTearDown(self):
        await self.db.users.delete_many({"id": self.user_id})
        await self.db.login_attempts.delete_many({"identifier": {"$regex": ":" + self.username + "$"}})
        await self.db.security_notifications.delete_many({"user_id": self.user_id})
        self.client.close()

    async def test_five_concurrent_failures_lock_once(self):
        req = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))
        with patch.object(server, "db", self.db), patch.object(server, "verify_password", return_value=False):
            async def attempt():
                try:
                    await server.login(server.LoginReq(email=self.username, password="incorrect"), req, Response())
                except HTTPException as exc:
                    return exc.status_code
                return 200
            codes = await asyncio.gather(*(attempt() for _ in range(5)))
        self.assertNotIn(200, codes)
        user = await self.db.users.find_one({"id": self.user_id})
        self.assertEqual(user["login_failed_count"], 5)
        self.assertTrue(user.get("login_locked_until"))
        self.assertEqual(await self.db.security_notifications.count_documents({
            "user_id": self.user_id, "type": "account_login_locked"
        }), 1)

    async def test_concurrent_unknown_source_failures_are_not_lost(self):
        """Real MongoDB should retain every source identifier failure."""
        username = "unknown_" + uuid4().hex[:16]
        ident = "127.0.0.1:" + username
        req = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))
        with patch.object(server, "db", self.db):
            async def fail():
                try:
                    await server.login(server.LoginReq(email=username, password="bad"), req, Response())
                except HTTPException as exc:
                    return exc.status_code
                return 200
            statuses = await asyncio.gather(*(fail() for _ in range(5)))
        self.assertEqual(statuses, [401] * 5)
        record = await self.db.login_attempts.find_one({"identifier": ident})
        self.assertIsNotNone(record)
        self.assertEqual(record["count"], 5)
        self.assertTrue(record["locked_until"])
        await self.db.login_attempts.delete_many({"identifier": ident})

    async def test_legacy_nonunique_index_migrates_without_losing_records(self):
        """Upgrade a disposable legacy index while preserving throttle evidence."""
        collection = self.db["throttle_upgrade_" + uuid4().hex[:16]]
        identifier = "127.0.0.1:legacy_" + uuid4().hex[:16]
        try:
            await collection.create_index("identifier")
            await collection.insert_one({"identifier": identifier, "count": 4})
            await server.ensure_unique_login_throttle_index(collection)
            indexes = await collection.index_information()
            self.assertTrue(indexes["identifier_1"]["unique"])
            record = await collection.find_one({"identifier": identifier})
            self.assertEqual(record["count"], 4)
            from pymongo.errors import DuplicateKeyError
            with self.assertRaises(DuplicateKeyError):
                await collection.insert_one({"identifier": identifier, "count": 1})
            await server.ensure_unique_login_throttle_index(collection)
            self.assertEqual(await collection.count_documents({"identifier": identifier}), 1)
        finally:
            await collection.drop()

    async def test_duplicate_migration_refuses_without_mutating_records(self):
        """Migration must preserve duplicate evidence and the legacy index."""
        collection = self.db["throttle_migration_" + uuid4().hex[:16]]
        ident = "127.0.0.1:duplicate_" + uuid4().hex[:16]
        try:
            await collection.create_index("identifier")
            await collection.insert_many([
                {"identifier": ident, "count": 2},
                {"identifier": ident, "count": 3},
            ])
            with self.assertRaisesRegex(RuntimeError, "Duplicate login throttle identifiers"):
                await server.ensure_unique_login_throttle_index(collection)
            rows = await collection.find({"identifier": ident}).to_list(10)
            self.assertEqual(sorted(row["count"] for row in rows), [2, 3])
            self.assertFalse((await collection.index_information())["identifier_1"].get("unique", False))
        finally:
            await collection.drop()

    async def test_unique_identifier_index_rejects_duplicate_throttle_records(self):
        """Enforce first-insert uniqueness in disposable MongoDB."""
        ident = "127.0.0.1:unique_" + uuid4().hex[:16]
        await self.db.login_attempts.create_index("identifier", unique=True)
        try:
            await self.db.login_attempts.insert_one({"identifier": ident, "count": 1})
            from pymongo.errors import DuplicateKeyError
            with self.assertRaises(DuplicateKeyError):
                await self.db.login_attempts.insert_one({"identifier": ident, "count": 2})
            self.assertEqual(await self.db.login_attempts.count_documents({"identifier": ident}), 1)
        finally:
            await self.db.login_attempts.delete_many({"identifier": ident})

    async def test_concurrent_first_insert_requires_unique_identifier_index(self):
        """Document the first-insert race without touching persistent throttle data."""
        username = "first_insert_" + uuid4().hex[:16]
        ident = "127.0.0.1:" + username
        req = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))
        try:
            with patch.object(server, "db", self.db):
                async def fail():
                    try:
                        await server.login(server.LoginReq(email=username, password="bad"), req, Response())
                    except HTTPException as exc:
                        return exc.status_code
                    return 200
                statuses = await asyncio.gather(*(fail() for _ in range(12)), return_exceptions=True)
            self.assertEqual(statuses, [401] * 12)
            rows = await self.db.login_attempts.find({"identifier": ident}).to_list(20)
            self.assertEqual(len(rows), 1, "Concurrent upserts must not create duplicate throttle records")
            self.assertEqual(rows[0]["count"], 12)
        finally:
            await self.db.login_attempts.delete_many({"identifier": ident})

    async def test_expired_lock_allows_valid_login_and_resets_counter(self):
        await self.db.users.update_one(
            {"id": self.user_id},
            {"$set": {"login_failed_count": 5,
                      "login_locked_until": "2000-01-01T00:00:00+00:00"}},
        )
        req = SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))
        with patch.object(server, "db", self.db), \
             patch.object(server, "verify_password", return_value=True), \
             patch.object(server, "audit", new_callable=AsyncMock):
            result = await server.login(
                server.LoginReq(email=self.username, password="correct"), req, Response()
            )
        self.assertTrue(result["access_token"])
        user = await self.db.users.find_one({"id": self.user_id})
        self.assertNotIn("login_locked_until", user)
        self.assertNotIn("login_failed_count", user)


    async def test_admin_unlock_resolves_incident_and_source_throttle(self):
        await self.db.users.update_one(
            {"id": self.user_id},
            {"$set": {"login_failed_count": 5,
                      "login_locked_until": "2099-01-01T00:00:00+00:00"}},
        )
        await self.db.login_attempts.insert_one({
            "identifier": "127.0.0.1:" + self.username,
            "count": 5, "locked_until": "2099-01-01T00:00:00+00:00",
        })
        await self.db.security_notifications.insert_one({
            "id": str(uuid4()), "type": "account_login_locked",
            "user_id": self.user_id, "status": "open",
        })
        actor = {"id": "ci-super-admin", "role": "super_admin", "default_org": None}
        with patch.object(server, "db", self.db), \
             patch.object(server, "audit", new_callable=AsyncMock):
            result = await server.admin_unlock_login(self.user_id, actor=actor)
        self.assertEqual(result, {"ok": True})
        user = await self.db.users.find_one({"id": self.user_id})
        self.assertNotIn("login_locked_until", user)
        self.assertNotIn("login_failed_count", user)
        self.assertEqual(await self.db.login_attempts.count_documents({
            "identifier": "127.0.0.1:" + self.username
        }), 0)
        incident = await self.db.security_notifications.find_one({
            "user_id": self.user_id, "type": "account_login_locked"
        })
        self.assertEqual(incident["status"], "resolved")
        self.assertEqual(incident["resolved_by"], actor["id"])



if __name__ == "__main__":
    unittest.main()
