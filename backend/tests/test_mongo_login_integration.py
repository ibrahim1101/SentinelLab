"""MongoDB-backed login lockout integration test. Requires disposable CI MongoDB."""
import asyncio
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
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


if __name__ == "__main__":
    unittest.main()
