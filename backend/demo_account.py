"""Safe creation of the optional training-only demo analyst."""

DEMO_EMAIL = "analyst@sentinellab.io"
LEGACY_PASSWORD = "Analyst@2026"

async def seed_demo_account(users, enabled, password, training_org, new_id, now_iso, hash_password, logger):
    existing = await users.find_one({"email": DEMO_EMAIL})
    if existing:
        if "org-production" in existing.get("org_ids", []):
            logger.warning("Existing demo analyst has production access; revoke it and rotate its password through administration.")
        return
    if not enabled:
        return
    if not password or len(password) < 12 or password == LEGACY_PASSWORD:
        raise RuntimeError("Set a unique DEMO_ACCOUNT_PASSWORD of at least 12 characters before enabling demo accounts")
    await users.insert_one({
        "id": new_id(), "email": DEMO_EMAIL, "name": "SOC Analyst",
        "password_hash": hash_password(password), "role": "analyst",
        "org_ids": [training_org], "default_org": training_org,
        "theme": "obsidian_dark", "created_at": now_iso(),
    })
