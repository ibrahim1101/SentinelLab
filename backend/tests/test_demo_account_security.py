import unittest
from demo_account import seed_demo_account

class Users:
    def __init__(self, existing=None): self.existing, self.inserted = existing, []
    async def find_one(self, query): return self.existing
    async def insert_one(self, document): self.inserted.append(document)

class Logger:
    def __init__(self): self.warnings = []
    def warning(self, message): self.warnings.append(message)

class DemoAccountTests(unittest.IsolatedAsyncioTestCase):
    async def seed(self, users, enabled, password, logger=None):
        logger = logger or Logger()
        await seed_demo_account(users, enabled, password, "org-training", lambda: "id", lambda: "now", lambda p: "hash:" + p, logger)
        return logger

    async def test_enabled_account_is_training_only(self):
        users = Users()
        await self.seed(users, True, "a unique password")
        self.assertEqual(users.inserted[0]["org_ids"], ["org-training"])
        self.assertEqual(users.inserted[0]["password_hash"], "hash:a unique password")

    async def test_weak_missing_and_legacy_passwords_rejected(self):
        for password in (None, "short", "Analyst@2026"):
            users = Users()
            with self.subTest(password=password), self.assertRaises(RuntimeError):
                await self.seed(users, True, password)
            self.assertEqual(users.inserted, [])

    async def test_disabled_does_not_create(self):
        users = Users()
        await self.seed(users, False, None)
        self.assertEqual(users.inserted, [])

    async def test_existing_production_account_warns_even_when_demo_disabled(self):
        existing = {"org_ids": ["org-production", "org-training"]}
        users = Users(existing)
        logger = await self.seed(users, False, None)
        self.assertTrue(logger.warnings)
        self.assertEqual(existing["org_ids"], ["org-production", "org-training"])
        self.assertEqual(users.inserted, [])

if __name__ == "__main__":
    unittest.main()
