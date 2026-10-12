"""Outgoing SentinelLab webhook delivery: workspace-scoped, secret-safe and bounded."""
import asyncio
import base64
import hashlib
import ipaddress
import json
import logging
import os
import socket
from urllib.parse import urlsplit
import httpx
from cryptography.fernet import Fernet
from core import db, new_id, now_iso

log = logging.getLogger("sentinellab.webhooks")
PROVIDERS = {"generic", "slack", "discord", "teams"}
EVENTS = {"critical_alert", "alert", "investigation", "ingestion", "security", "system", "test"}
HOSTS = {
    "slack": {"hooks.slack.com", "hooks.slack-gov.com"},
    "discord": {"discord.com", "discordapp.com", "canary.discord.com", "ptb.discord.com"},
}
# The desktop secret is persisted across restarts. Production requires a stable JWT_SECRET.
def _cipher():
    secret = os.environ.get("WEBHOOK_ENCRYPTION_KEY") or os.environ["JWT_SECRET"]
    key = base64.urlsafe_b64encode(hashlib.sha256(("sentinellab-webhooks-v1:" + secret).encode()).digest())
    return Fernet(key)

def encrypt_url(url):
    return _cipher().encrypt(url.encode()).decode()

def decrypt_url(token):
    return _cipher().decrypt(token.encode()).decode()

def safe_target(url, provider):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment or parsed.port not in (None, 443):
        raise ValueError("Webhook URL must be an HTTPS URL without credentials, fragment or custom port")
    host = parsed.hostname.lower().rstrip(".")
    if provider in HOSTS and host not in HOSTS[provider]:
        raise ValueError("Webhook host does not match selected provider")
    if provider == "teams" and not (host.endswith(".logic.azure.com") or host.endswith(".webhook.office.com") or host.endswith(".powerautomate.com") or host.endswith(".api.powerplatform.com")):
        raise ValueError("Use a Microsoft Teams Workflows webhook URL")
    if not host or host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise ValueError("Local webhook destinations are not allowed")
    try:
        ips = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError("Webhook hostname cannot be resolved") from exc
    if not ips or any(not ipaddress.ip_address(item[4][0]).is_global for item in ips):
        raise ValueError("Webhook destination must resolve only to public addresses")
    return url

def payload_for(provider, event):
    title = str(event["title"])[:180]
    detail = str(event.get("detail", ""))[:1500]
    if provider == "slack":
        return {"text": f"*SentinelLab · {title}*\n{detail}"}
    if provider == "discord":
        return {"content": f"**SentinelLab · {title}**\n{detail}"[:1900], "allowed_mentions": {"parse": []}}
    if provider == "teams":
        return {"type": "message", "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "content": {"type": "AdaptiveCard", "version": "1.2", "body": [{"type": "TextBlock", "text": "SentinelLab · " + title, "weight": "Bolder", "wrap": True}, {"type": "TextBlock", "text": detail or event["type"], "wrap": True}]}}]}
    return {"source": "SentinelLab", "id": event["id"], "event": event["type"], "title": title, "detail": detail, "workspace": event["org_id"], "timestamp": event["timestamp"]}

def public_doc(doc):
    return {key: doc.get(key) for key in ("id", "name", "provider", "events", "enabled", "created_at", "last_status", "last_sent")}

async def send_one(hook, event):
    try:
        url = decrypt_url(hook["url_encrypted"])
        # Resolve and validate again at delivery time, not only during configuration.
        await asyncio.to_thread(safe_target, url, hook["provider"])
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0), follow_redirects=False, trust_env=False) as client:
            response = await client.post(url, json=payload_for(hook["provider"], event), headers={"User-Agent": "SentinelLab-Webhooks/1"})
            if response.status_code == 429 or response.status_code >= 500:
                await asyncio.sleep(1)
                response = await client.post(url, json=payload_for(hook["provider"], event))
            response.raise_for_status()
        status = "delivered"
    except Exception as exc:
        status = "failed"
        log.warning("Webhook delivery failed for id %s: %s", hook["id"], type(exc).__name__)
    await db.webhooks.update_one({"id": hook["id"], "org_id": hook["org_id"]}, {"$set": {"last_status": status, "last_sent": now_iso()}})
    return status

async def emit(org, kind, title, detail=""):
    if kind not in EVENTS:
        return
    event = {"id": new_id(), "org_id": org, "type": kind, "title": title, "detail": detail, "timestamp": now_iso()}
    hooks = await db.webhooks.find({"org_id": org, "enabled": True, "events": kind}).to_list(50)
    if hooks:
        await asyncio.gather(*(send_one(hook, event) for hook in hooks), return_exceptions=True)
