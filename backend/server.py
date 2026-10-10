import re
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env")

import os
import io
import csv
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import FastAPI, APIRouter, Depends, HTTPException, Request, Response, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

from core import (db, new_id, now_iso, hash_password, verify_password, create_access_token,
                  get_current_user, require_role, active_org, audit, clean,
                  ROLE_LEVELS, ROLE_LABELS, role_level)
from parsers import parse_payload, normalize
from detection import run_detection, evaluate_rule
import seed as seedmod
import ai_assistant
import playbooks as pbmod
from mitre_data import TACTICS, TECHNIQUES, ATTACK_VERSION

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("sentinellab")

app = FastAPI(title="SentinelLab API")
api = APIRouter(prefix="/api")

PROD_ORG = "org-production"
TRAIN_ORG = "org-training"


# ============================= MODELS =============================
class RegisterReq(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str

class LoginReq(BaseModel):
    email: str = Field(min_length=1, max_length=254)
    password: str

USERNAME_RE = re.compile(r"^[a-z][a-z0-9_.-]{2,31}$")

class IngestReq(BaseModel):
    source_id: str
    format: str = "json"
    payload: object

class RuleReq(BaseModel):
    name: str
    description: str = ""
    rule_type: str = "match"
    severity: str = "medium"
    enabled: bool = True
    mitre: List[str] = []
    confidence: int = 80
    params: dict = {}

class AlertUpdate(BaseModel):
    status: Optional[str] = None
    severity: Optional[str] = None
    assigned_to: Optional[str] = None
    comment: Optional[str] = None
    tags: Optional[List[str]] = None
    investigation_id: Optional[str] = None

class InvestigationReq(BaseModel):
    title: str
    severity: str = "medium"
    priority: str = "medium"
    status: str = "open"
    lead: Optional[str] = None

class InvUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    findings: Optional[str] = None
    note: Optional[str] = None
    task: Optional[str] = None
    related_alerts: Optional[List[str]] = None
    related_events: Optional[List[str]] = None

class SourceReq(BaseModel):
    name: str
    display_name: str = ""
    source_type: str = "custom"
    host: str = ""

class HuntReq(BaseModel):
    query: str = ""
    conditions: List[dict] = []
    limit: int = 200

class AIReq(BaseModel):
    message: str
    ctx_type: Optional[str] = None
    ctx_id: Optional[str] = None

class SettingsReq(BaseModel):
    app_name: Optional[str] = None
    timezone: Optional[str] = None
    default_time_range: Optional[str] = None
    retention_days: Optional[int] = None
    demo_mode: Optional[bool] = None


# ============================= AUTH =============================
def _set_cookie(response: Response, token: str):
    response.set_cookie("access_token", token, httponly=True, secure=True,
                        samesite="none", max_age=480 * 60, path="/")


@api.post("/auth/register")
async def register(body: RegisterReq, response: Response):
    raise HTTPException(status_code=403, detail="Registration requires administrator approval")
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(400, "Email already registered")
    uid = new_id()
    user = {"id": uid, "email": email, "name": body.name,
            "password_hash": hash_password(body.password), "role": "analyst",
            "org_ids": [TRAIN_ORG], "default_org": TRAIN_ORG,
            "theme": "obsidian_dark", "created_at": now_iso()}
    await db.users.insert_one(dict(user))
    token = create_access_token(uid, email, "analyst")
    _set_cookie(response, token)
    user.pop("password_hash")
    return {"user": clean(user), "access_token": token}


@api.post("/auth/login")
async def login(body: LoginReq, request: Request, response: Response):
    identifier = body.email.strip().lower()
    ip = request.client.host if request.client else "?"
    now = datetime.now(timezone.utc)
    ident = f"{ip}:{identifier}"
    user = await db.users.find_one({"email": identifier} if "@" in identifier else {"username": identifier})
    # Keep a separate IP/identifier throttle for unknown accounts and credential stuffing.
    attempt = await db.login_attempts.find_one({"identifier": ident})
    if attempt and attempt.get("locked_until") and attempt.get("count", 0) >= 5:
        until = datetime.fromisoformat(attempt["locked_until"])
        if now < until:
            # An unknown identifier must never be described as a locked account.
            if not user:
                raise HTTPException(401, "Invalid credentials")
            raise HTTPException(429, "Too many login attempts from this source. Try again later.")
        await db.login_attempts.delete_one({"identifier": ident})
        attempt = None

    if user and user.get("login_locked_until"):
        until = datetime.fromisoformat(user["login_locked_until"])
        if now < until:
            raise HTTPException(423, "Account temporarily locked due to repeated failed sign-ins. Contact your administrator for recovery.")
        await db.users.update_one({"id": user["id"]}, {"$unset": {"login_locked_until": "", "login_failed_count": ""}})
        user.pop("login_locked_until", None)
        user.pop("login_failed_count", None)

    if not user or not verify_password(body.password, user["password_hash"]):
        count = (attempt.get("count", 0) if attempt else 0) + 1
        await db.login_attempts.update_one(
            {"identifier": ident},
            {"$set": {"identifier": ident, "count": count,
                      "locked_until": (now + timedelta(minutes=15)).isoformat() if count >= 5 else None}},
            upsert=True)
        if user and user.get("enabled", True):
            # Atomic increment prevents concurrent failures from losing counts.
            updated = await db.users.find_one_and_update(
                {"id": user["id"], "enabled": {"$ne": False},
                 "login_locked_until": {"$exists": False}},
                {"$inc": {"login_failed_count": 1}},
                return_document=True,
            )
            if updated is None:
                raise HTTPException(423, "Account temporarily locked. Contact your administrator.")
            failures = updated.get("login_failed_count", 0)
            if failures >= 5:
                until = (now + timedelta(minutes=15)).isoformat()
                # Only one concurrent request can create the lock incident.
                claimed = await db.users.update_one(
                    {"id": user["id"], "login_locked_until": {"$exists": False},
                     "login_failed_count": {"$gte": 5}},
                    {"$set": {"login_locked_until": until}},
                )
                if claimed.modified_count:
                    await db.security_notifications.insert_one({
                        "id": new_id(), "type": "account_login_locked", "user_id": user["id"],
                        "email": user["email"], "source_ip": ip, "failed_count": failures,
                        "created_at": now.isoformat(), "locked_until": until,
                        "status": "open",
                    })
                raise HTTPException(423, "Account temporarily locked after repeated failed sign-ins. Contact your administrator.")
            raise HTTPException(401, f"Invalid credentials. {5 - failures} attempts remaining before account lock.")
        # Do not expose a lockout state or account existence for unknown identifiers.
        raise HTTPException(401, "Invalid credentials")

    await db.login_attempts.delete_one({"identifier": ident})
    if user.get("enabled", True) is False:
        raise HTTPException(status_code=403, detail="This account has been disabled. Contact your SentinelLab administrator.")
    # A concurrent fifth failure must not be bypassed by a successful password check.
    cleared = await db.users.update_one(
        {"id": user["id"], "login_locked_until": {"$exists": False}},
        {"$unset": {"login_failed_count": ""}},
    )
    if not cleared.matched_count:
        raise HTTPException(423, "Account temporarily locked. Contact your administrator.")
    token = create_access_token(user["id"], user["email"], user["role"], user.get("session_version", 0))
    _set_cookie(response, token)
    await audit(user.get("default_org"), user, "login", "session")
    user.pop("password_hash", None)
    return {"user": clean(user), "access_token": token}


@api.post("/auth/logout")
async def logout(response: Response, user=Depends(get_current_user)):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(user=Depends(get_current_user)):
    return {"user": user, "roles": ROLE_LABELS}


# ============================= WORKSPACES =============================
@api.get("/workspaces")
async def workspaces(user=Depends(get_current_user)):
    orgs = await db.organizations.find({"id": {"$in": user.get("org_ids", [])}}, {"_id": 0}).to_list(50)
    return {"workspaces": orgs}


# ============================= DASHBOARD =============================
def _range_seconds(tr):
    return {"15m": 900, "1h": 3600, "24h": 86400, "7d": 604800, "30d": 2592000}.get(tr, 86400)


def _range_to_iso(tr):
    return (datetime.now(timezone.utc) - timedelta(seconds=_range_seconds(tr))).isoformat()


async def _events_over_time(org, since):
    pipeline = [
        {"$match": {"org_id": org, "timestamp": {"$gte": since}}},
        {"$project": {"hour": {"$substr": ["$timestamp", 0, 13]}}},
        {"$group": {"_id": "$hour", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    rows = await db.events.aggregate(pipeline).to_list(500)
    return [{"time": r["_id"], "count": r["count"]} for r in rows]


@api.get("/dashboard/overview")
async def overview(request: Request, time_range: str = "24h", user=Depends(get_current_user)):
    org = active_org(user, request)
    since = _range_to_iso(time_range)
    q = {"org_id": org, "timestamp": {"$gte": since}}
    total_events = await db.events.count_documents(q)
    all_events_cnt = await db.events.count_documents({"org_id": org})
    open_alerts = await db.alerts.count_documents({"org_id": org, "status": {"$in": ["new", "triaged", "investigating"]}})
    crit = await db.alerts.count_documents({"org_id": org, "severity": "critical", "status": {"$ne": "resolved"}})
    high = await db.alerts.count_documents({"org_id": org, "severity": "high", "status": {"$ne": "resolved"}})
    sources = await db.sources.find({"org_id": org}, {"_id": 0}).to_list(200)
    active_sources = sum(1 for s in sources if s.get("status") == "online")
    investigations = await db.investigations.count_documents({"org_id": org, "status": {"$nin": ["closed", "resolved"]}})
    rules_triggered = await db.detection_rules.count_documents({"org_id": org, "match_count": {"$gt": 0}})
    assets = await db.events.distinct("host", {"org_id": org})

    buckets = await _events_over_time(org, since)
    sev_counts = {s: await db.alerts.count_documents({"org_id": org, "severity": s}) for s in ["critical", "high", "medium", "low"]}
    by_source = []
    for s in sources:
        c = await db.events.count_documents({"org_id": org, "source_id": s["id"], "timestamp": {"$gte": since}})
        by_source.append({"source": s.get("display_name") or s["name"], "count": c})
    by_source = sorted(by_source, key=lambda x: -x["count"])[:8]
    cats = {}
    async for e in db.events.find(q, {"category": 1, "_id": 0}):
        cats[e.get("category", "other")] = cats.get(e.get("category", "other"), 0) + 1
    top_cats = sorted([{"category": k, "count": v} for k, v in cats.items()], key=lambda x: -x["count"])[:6]
    mitre = {}
    async for a in db.alerts.find({"org_id": org}, {"mitre": 1, "_id": 0}):
        for m in a.get("mitre", []):
            mitre[m] = mitre.get(m, 0) + 1
    mitre_dist = sorted([{"technique": k, "count": v} for k, v in mitre.items()], key=lambda x: -x["count"])[:8]
    recent = await db.alerts.find({"org_id": org}, {"_id": 0}).sort("created_at", -1).limit(6).to_list(6)
    eps = round(total_events / max(_range_seconds(time_range), 1), 3)
    return {
        "kpis": {"total_events": total_events, "all_events": all_events_cnt, "eps": eps,
                 "open_alerts": open_alerts, "critical_alerts": crit, "high_alerts": high,
                 "active_sources": active_sources, "inactive_sources": len(sources) - active_sources,
                 "active_investigations": investigations, "rules_triggered": rules_triggered,
                 "monitored_assets": len([a for a in assets if a])},
        "events_over_time": buckets, "alerts_by_severity": sev_counts,
        "events_by_source": by_source, "top_categories": top_cats,
        "mitre_distribution": mitre_dist, "recent_alerts": recent,
        "is_demo_workspace": org == TRAIN_ORG,
    }


# ============================= EVENTS / INGESTION =============================
async def _notify(org, ntype, text, ref=None):
    await db.notifications.insert_one({"id": new_id(), "org_id": org, "type": ntype, "text": text,
                                       "ref": ref, "read": False, "created_at": now_iso()})


@api.post("/ingest")
async def ingest(body: IngestReq, request: Request, user=Depends(require_role("analyst"))):
    org = active_org(user, request)
    source = await db.sources.find_one({"id": body.source_id, "org_id": org}, {"_id": 0})
    if not source:
        raise HTTPException(404, "Source not found")
    try:
        records = parse_payload(body.payload, body.format)
    except Exception as ex:
        await db.sources.update_one({"id": source["id"], "org_id": org}, {"$inc": {"parse_errors": 1}})
        await db.parser_errors.insert_one({"id": new_id(), "org_id": org, "source_id": source["id"],
                                           "error": str(ex), "timestamp": now_iso()})
        raise HTTPException(400, f"Parse error: {ex}")
    docs = [normalize(r, org, source, is_synthetic=(org == TRAIN_ORG)) for r in records]
    if docs:
        await db.events.insert_many([dict(d) for d in docs])
        await db.sources.update_one({"id": source["id"], "org_id": org},
                                    {"$inc": {"events_received": len(docs)},
                                     "$set": {"last_received": now_iso(), "status": "online"}})
    alerts = await run_detection(org, docs, persist=True)
    for a in alerts:
        await _notify(org, "critical_alert" if a["severity"] in ("critical", "high") else "alert",
                      f"Alert: {a['title']}", a["id"])
    await audit(org, user, "ingest", "events", details={"count": len(docs), "source": source["id"]})
    return {"ingested": len(docs), "alerts_generated": len(alerts)}


@api.post("/ingest/upload")
async def ingest_upload(request: Request, source_id: str = Query(...), format: str = Query("json"),
                        file: UploadFile = File(...), user=Depends(require_role("analyst"))):
    content = (await file.read()).decode("utf-8", errors="replace")
    return await ingest(IngestReq(source_id=source_id, format=format, payload=content), request, user)


@api.get("/events")
async def list_events(request: Request, q: Optional[str] = None, severity: Optional[str] = None,
                      category: Optional[str] = None, source_id: Optional[str] = None,
                      host: Optional[str] = None, username: Optional[str] = None, ip: Optional[str] = None,
                      time_range: str = "24h", page: int = 1, page_size: int = 50,
                      sort: str = "timestamp", order: int = -1, user=Depends(get_current_user)):
    org = active_org(user, request)
    filt = {"org_id": org, "timestamp": {"$gte": _range_to_iso(time_range)}}
    if severity: filt["severity"] = severity
    if category: filt["category"] = category
    if source_id: filt["source_id"] = source_id
    if host: filt["host"] = host
    if username: filt["username"] = username
    if ip: filt["$or"] = [{"src_ip": ip}, {"dest_ip": ip}]
    if q:
        filt["$or"] = [{"host": {"$regex": re.escape(q[:128]), "$options": "i"}},
                       {"username": {"$regex": re.escape(q[:128]), "$options": "i"}},
                       {"src_ip": {"$regex": re.escape(q[:128]), "$options": "i"}},
                       {"dest_ip": {"$regex": re.escape(q[:128]), "$options": "i"}},
                       {"process_name": {"$regex": re.escape(q[:128]), "$options": "i"}},
                       {"event_type": {"$regex": re.escape(q[:128]), "$options": "i"}}]
    total = await db.events.count_documents(filt)
    skip = (page - 1) * page_size
    rows = await db.events.find(filt, {"_id": 0, "raw": 0}).sort(sort, order).skip(skip).limit(page_size).to_list(page_size)
    return {"total": total, "page": page, "page_size": page_size, "events": rows}


@api.get("/events/export/data")
async def export_events(request: Request, format: str = "json", time_range: str = "24h",
                        severity: Optional[str] = None, user=Depends(get_current_user)):
    org = active_org(user, request)
    filt = {"org_id": org, "timestamp": {"$gte": _range_to_iso(time_range)}}
    if severity: filt["severity"] = severity
    rows = await db.events.find(filt, {"_id": 0, "raw": 0}).limit(5000).to_list(5000)
    if format == "csv":
        buf = io.StringIO()
        if rows:
            w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow({k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in r.items()})
        return StreamingResponse(io.BytesIO(buf.getvalue().encode()), media_type="text/csv",
                                 headers={"Content-Disposition": "attachment; filename=events.csv"})
    return StreamingResponse(io.BytesIO(json.dumps(rows, indent=2).encode()), media_type="application/json",
                             headers={"Content-Disposition": "attachment; filename=events.json"})


@api.get("/events/{event_id}")
async def event_detail(event_id: str, request: Request, user=Depends(get_current_user)):
    org = active_org(user, request)
    e = await db.events.find_one({"id": event_id, "org_id": org}, {"_id": 0})
    if not e:
        raise HTTPException(404, "Event not found")
    related_alerts = await db.alerts.find({"org_id": org, "related_events": event_id}, {"_id": 0}).to_list(50)
    related_events = await db.events.find(
        {"org_id": org, "id": {"$ne": event_id},
         "$or": [{"src_ip": e.get("src_ip")}, {"host": e.get("host")}]},
        {"_id": 0, "raw": 0}).limit(10).to_list(10)
    return {"event": e, "related_alerts": related_alerts, "related_events": related_events}


# ============================= DETECTION RULES =============================
@api.get("/rules")
async def list_rules(request: Request, user=Depends(get_current_user)):
    org = active_org(user, request)
    rows = await db.detection_rules.find({"org_id": org}, {"_id": 0}).sort("name", 1).to_list(500)
    return {"rules": rows}


@api.post("/rules")
async def create_rule(body: RuleReq, request: Request, user=Depends(require_role("analyst"))):
    org = active_org(user, request)
    rule = {"id": new_id(), "org_id": org, "version": "1.0", "match_count": 0,
            "last_run": None, "last_error": None, "author": user["email"],
            "created_at": now_iso(), "updated_at": now_iso(), **body.model_dump()}
    await db.detection_rules.insert_one(dict(rule))
    await audit(org, user, "create", "rule", rule["id"], {"name": rule["name"]})
    return clean(rule)


@api.put("/rules/{rule_id}")
async def update_rule(rule_id: str, body: RuleReq, request: Request, user=Depends(require_role("analyst"))):
    org = active_org(user, request)
    r = await db.detection_rules.find_one({"id": rule_id, "org_id": org})
    if not r:
        raise HTTPException(404, "Rule not found")
    upd = body.model_dump()
    upd["updated_at"] = now_iso()
    try:
        upd["version"] = f"{float(r.get('version', '1.0')) + 0.1:.1f}"
    except ValueError:
        upd["version"] = "1.1"
    await db.detection_rules.update_one({"id": rule_id, "org_id": org}, {"$set": upd})
    await audit(org, user, "update", "rule", rule_id)
    return clean(await db.detection_rules.find_one({"id": rule_id, "org_id": org}, {"_id": 0}))


@api.post("/rules/{rule_id}/toggle")
async def toggle_rule(rule_id: str, request: Request, user=Depends(require_role("analyst"))):
    org = active_org(user, request)
    r = await db.detection_rules.find_one({"id": rule_id, "org_id": org}, {"_id": 0})
    if not r:
        raise HTTPException(404, "Rule not found")
    await db.detection_rules.update_one({"id": rule_id, "org_id": org}, {"$set": {"enabled": not r["enabled"]}})
    return {"enabled": not r["enabled"]}


@api.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, request: Request, user=Depends(require_role("soc_manager"))):
    org = active_org(user, request)
    await db.detection_rules.delete_one({"id": rule_id, "org_id": org})
    await audit(org, user, "delete", "rule", rule_id)
    return {"ok": True}


@api.post("/rules/{rule_id}/backtest")
async def backtest_rule(rule_id: str, request: Request, time_range: str = "7d", user=Depends(require_role("analyst"))):
    org = active_org(user, request)
    r = await db.detection_rules.find_one({"id": rule_id, "org_id": org}, {"_id": 0})
    if not r:
        raise HTTPException(404, "Rule not found")
    events = await db.events.find({"org_id": org, "timestamp": {"$gte": _range_to_iso(time_range)}},
                                  {"_id": 0}).limit(10000).to_list(10000)
    alerts, matched = await evaluate_rule(r, events, org)
    return {"would_alert": len(alerts), "matched_events": len(matched),
            "sample": [{"title": a["title"], "severity": a["severity"], "event_count": a["event_count"]} for a in alerts[:10]]}


# ============================= ALERTS =============================
@api.get("/alerts")
async def list_alerts(request: Request, status: Optional[str] = None, severity: Optional[str] = None,
                      q: Optional[str] = None, page: int = 1, page_size: int = 50, user=Depends(get_current_user)):
    org = active_org(user, request)
    filt = {"org_id": org}
    if status: filt["status"] = status
    if severity: filt["severity"] = severity
    if q: filt["title"] = {"$regex": re.escape(q[:128]), "$options": "i"}
    total = await db.alerts.count_documents(filt)
    rows = await db.alerts.find(filt, {"_id": 0}).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size).to_list(page_size)
    return {"total": total, "alerts": rows, "page": page, "page_size": page_size}


@api.get("/alerts/{alert_id}")
async def alert_detail(alert_id: str, request: Request, user=Depends(get_current_user)):
    org = active_org(user, request)
    a = await db.alerts.find_one({"id": alert_id, "org_id": org}, {"_id": 0})
    if not a:
        raise HTTPException(404, "Alert not found")
    events = await db.events.find({"id": {"$in": a.get("related_events", [])}, "org_id": org}, {"_id": 0, "raw": 0}).limit(50).to_list(50)
    rule = await db.detection_rules.find_one({"id": a.get("rule_id"), "org_id": org}, {"_id": 0})
    return {"alert": a, "events": events, "rule": rule}


@api.put("/alerts/{alert_id}")
async def update_alert(alert_id: str, body: AlertUpdate, request: Request, user=Depends(require_role("analyst"))):
    org = active_org(user, request)
    a = await db.alerts.find_one({"id": alert_id, "org_id": org}, {"_id": 0})
    if not a:
        raise HTTPException(404, "Alert not found")
    upd, audit_entries = {"updated_at": now_iso()}, []
    for field in ("status", "severity", "assigned_to", "investigation_id"):
        v = getattr(body, field)
        if v is not None and v != a.get(field):
            upd[field] = v
            audit_entries.append({"ts": now_iso(), "action": f"set {field}={v}", "by": user["email"]})
    if body.tags is not None:
        upd["tags"] = body.tags
    push = {}
    if body.comment:
        push["comments"] = {"id": new_id(), "text": body.comment, "by": user["email"], "ts": now_iso()}
        audit_entries.append({"ts": now_iso(), "action": "comment", "by": user["email"]})
    mongo_upd = {"$set": upd}
    if audit_entries:
        mongo_upd["$push"] = {"audit": {"$each": audit_entries}}
    if push:
        mongo_upd.setdefault("$push", {}).update(push)
    await db.alerts.update_one({"id": alert_id, "org_id": org}, mongo_upd)
    await audit(org, user, "update", "alert", alert_id, upd)
    return clean(await db.alerts.find_one({"id": alert_id, "org_id": org}, {"_id": 0}))


@api.post("/alerts/bulk")
async def bulk_alerts(request: Request, body: dict, user=Depends(require_role("analyst"))):
    org = active_org(user, request)
    ids = body.get("ids", [])
    status = body.get("status")
    result = await db.alerts.update_many({"id": {"$in": ids}, "org_id": org},
                                         {"$set": {"status": status, "updated_at": now_iso()}})
    return {"updated": result.modified_count}


# ============================= THREAT HUNTING =============================
def _parse_query(query: str):
    conds = []
    if not query:
        return conds
    for tok in query.split(" AND "):
        tok = tok.strip()
        matched = None
        for op_text, op in [(">", "gt"), ("<", "lt"), ("!=", "ne"), (":", "eq"), ("=", "eq")]:
            if op_text in tok:
                field, val = tok.split(op_text, 1)
                conds.append({"field": field.strip(), "op": op, "value": val.strip().strip('"')})
                matched = True
                break
        if not matched and tok:
            conds.append({"field": "host", "op": "contains", "value": tok})
    return conds


def _apply_conditions(filt, conds):
    op_map = {"eq": "$eq", "ne": "$ne", "gt": "$gt", "lt": "$lt"}
    allowed = ("src_ip", "dest_ip", "host", "username", "process_name", "category",
               "severity", "outcome", "action", "event_type", "dest_port", "protocol", "dns_query")
    for c in conds:
        field, op, value = c.get("field"), c.get("op", "eq"), c.get("value")
        if field not in allowed:
            continue
        if op == "contains":
            filt[field] = {"$regex": re.escape(str(value)[:128]), "$options": "i"}
        elif op in op_map:
            if op in ("gt", "lt"):
                try: value = float(value)
                except (ValueError, TypeError): pass
            filt.setdefault(field, {})[op_map[op]] = value
        else:
            filt[field] = value


@api.post("/hunt")
async def hunt(body: HuntReq, request: Request, user=Depends(get_current_user)):
    org = active_org(user, request)
    t0 = datetime.now(timezone.utc)
    filt = {"org_id": org}
    conds = body.conditions or _parse_query(body.query)
    _apply_conditions(filt, conds)
    limit = min(body.limit, 1000)
    rows = await db.events.find(filt, {"_id": 0, "raw": 0}).sort("timestamp", -1).limit(limit).to_list(limit)
    total = await db.events.count_documents(filt)

    def topn(field):
        c = {}
        for r in rows:
            v = r.get(field)
            if v: c[v] = c.get(v, 0) + 1
        return sorted([{"value": k, "count": v} for k, v in c.items()], key=lambda x: -x["count"])[:5]
    hist = {}
    for r in rows:
        h = r.get("timestamp", "")[:13]
        hist[h] = hist.get(h, 0) + 1
    timeline = sorted([{"time": k, "count": v} for k, v in hist.items()], key=lambda x: x["time"])
    took = (datetime.now(timezone.utc) - t0).total_seconds() * 1000
    return {"total": total, "returned": len(rows), "events": rows, "took_ms": round(took, 1),
            "top_src_ip": topn("src_ip"), "top_host": topn("host"), "top_process": topn("process_name"),
            "timeline": timeline, "conditions": conds}


@api.get("/hunt/saved")
async def saved_hunts(request: Request, user=Depends(get_current_user)):
    org = active_org(user, request)
    rows = await db.saved_searches.find({"org_id": org}, {"_id": 0}).to_list(100)
    return {"saved": rows}


@api.post("/hunt/saved")
async def save_hunt(request: Request, body: dict, user=Depends(get_current_user)):
    org = active_org(user, request)
    doc = {"id": new_id(), "org_id": org, "name": body.get("name"), "query": body.get("query"),
           "by": user["email"], "created_at": now_iso()}
    await db.saved_searches.insert_one(dict(doc))
    return clean(doc)


# ============================= SOURCES =============================
@api.get("/sources")
async def list_sources(request: Request, user=Depends(get_current_user)):
    org = active_org(user, request)
    rows = await db.sources.find({"org_id": org}, {"_id": 0, "token_hash": 0}).to_list(200)
    return {"sources": rows}


@api.post("/sources")
async def create_source(body: SourceReq, request: Request, user=Depends(require_role("analyst"))):
    org = active_org(user, request)
    import secrets
    token = "sl_" + secrets.token_urlsafe(24)
    doc = {"id": new_id(), "org_id": org, "name": body.name,
           "display_name": body.display_name or body.name, "source_type": body.source_type,
           "host": body.host, "status": "inactive", "enabled": True, "events_received": 0,
           "last_received": None, "parse_errors": 0, "token_hint": token[:11] + "…",
           "token_hash": hash_password(token), "created_at": now_iso(),
           "is_synthetic": org == TRAIN_ORG}
    await db.sources.insert_one(dict(doc))
    await audit(org, user, "create", "source", doc["id"], {"name": body.name})
    doc.pop("token_hash")
    return {"source": clean(doc), "ingestion_token": token}


@api.delete("/sources/{source_id}")
async def delete_source(source_id: str, request: Request, user=Depends(require_role("soc_manager"))):
    org = active_org(user, request)
    await db.sources.delete_one({"id": source_id, "org_id": org})
    await audit(org, user, "delete", "source", source_id)
    return {"ok": True}


# ============================= INVESTIGATIONS =============================
@api.get("/investigations")
async def list_investigations(request: Request, user=Depends(get_current_user)):
    org = active_org(user, request)
    rows = await db.investigations.find({"org_id": org}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return {"investigations": rows}


@api.post("/investigations")
async def create_investigation(body: InvestigationReq, request: Request, user=Depends(require_role("analyst"))):
    org = active_org(user, request)
    doc = {"id": new_id(), "org_id": org, "related_alerts": [], "related_events": [],
           "related_assets": [], "notes": [], "tasks": [], "evidence": [], "findings": "",
           "created_at": now_iso(), "updated_at": now_iso(), "is_synthetic": org == TRAIN_ORG,
           "lead": body.lead or user["email"], **body.model_dump(exclude={"lead"})}
    await db.investigations.insert_one(dict(doc))
    await audit(org, user, "create", "investigation", doc["id"], {"title": body.title})
    return clean(doc)


@api.get("/investigations/{inv_id}")
async def investigation_detail(inv_id: str, request: Request, user=Depends(get_current_user)):
    org = active_org(user, request)
    inv = await db.investigations.find_one({"id": inv_id, "org_id": org}, {"_id": 0})
    if not inv:
        raise HTTPException(404, "Investigation not found")
    alerts = await db.alerts.find({"id": {"$in": inv.get("related_alerts", [])}, "org_id": org}, {"_id": 0}).to_list(100)
    return {"investigation": inv, "alerts": alerts}


@api.put("/investigations/{inv_id}")
async def update_investigation(inv_id: str, body: InvUpdate, request: Request, user=Depends(require_role("analyst"))):
    org = active_org(user, request)
    inv = await db.investigations.find_one({"id": inv_id, "org_id": org}, {"_id": 0})
    if not inv:
        raise HTTPException(404, "Investigation not found")
    upd = {"updated_at": now_iso()}
    for f in ("status", "priority", "findings", "related_alerts", "related_events"):
        v = getattr(body, f)
        if v is not None:
            upd[f] = v
    push = {}
    if body.note:
        push["notes"] = {"id": new_id(), "text": body.note, "by": user["email"], "ts": now_iso()}
    if body.task:
        push["tasks"] = {"id": new_id(), "text": body.task, "done": False, "ts": now_iso()}
    mu = {"$set": upd}
    if push: mu["$push"] = push
    await db.investigations.update_one({"id": inv_id, "org_id": org}, mu)
    await audit(org, user, "update", "investigation", inv_id)
    return clean(await db.investigations.find_one({"id": inv_id, "org_id": org}, {"_id": 0}))


@api.post("/investigations/{inv_id}/evidence")
async def add_evidence(inv_id: str, request: Request, file: UploadFile = File(...), user=Depends(require_role("analyst"))):
    import hashlib
    org = active_org(user, request)
    inv = await db.investigations.find_one({"id": inv_id, "org_id": org})
    if not inv:
        raise HTTPException(404, "Investigation not found")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "Evidence file too large (max 10MB)")
    ev = {"id": new_id(), "filename": file.filename, "size": len(content),
          "sha256": hashlib.sha256(content).hexdigest(), "content_type": file.content_type,
          "uploaded_by": user["email"], "uploaded_at": now_iso(),
          "chain_of_custody": [{"by": user["email"], "action": "uploaded", "ts": now_iso()}]}
    await db.investigations.update_one({"id": inv_id, "org_id": org}, {"$push": {"evidence": ev}})
    await audit(org, user, "add_evidence", "investigation", inv_id, {"filename": file.filename, "sha256": ev["sha256"]})
    return {"evidence": ev}


# ============================= REPORTS =============================
@api.get("/reports")
async def list_reports(request: Request, user=Depends(get_current_user)):
    org = active_org(user, request)
    rows = await db.reports.find({"org_id": org}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"reports": rows}


@api.post("/reports/generate")
async def generate_report(request: Request, body: dict, user=Depends(require_role("analyst"))):
    org = active_org(user, request)
    rtype = body.get("type", "soc_summary")
    time_range = body.get("time_range", "7d")
    since = _range_to_iso(time_range)
    data = {
        "events": await db.events.count_documents({"org_id": org, "timestamp": {"$gte": since}}),
        "alerts": await db.alerts.count_documents({"org_id": org, "created_at": {"$gte": since}}),
        "critical": await db.alerts.count_documents({"org_id": org, "severity": "critical"}),
        "investigations": await db.investigations.count_documents({"org_id": org}),
        "sources": await db.sources.count_documents({"org_id": org}),
    }
    top_alerts = await db.alerts.find({"org_id": org}, {"_id": 0}).sort("created_at", -1).limit(20).to_list(20)
    doc = {"id": new_id(), "org_id": org, "type": rtype, "title": body.get("title", rtype.replace("_", " ").title()),
           "time_range": time_range, "summary": data, "top_alerts": top_alerts,
           "generated_by": user["email"], "created_at": now_iso(), "status": "ready"}
    await db.reports.insert_one(dict(doc))
    await audit(org, user, "generate", "report", doc["id"], {"type": rtype})
    return clean(doc)


@api.get("/reports/{report_id}/download")
async def download_report(report_id: str, request: Request, format: str = "json", user=Depends(get_current_user)):
    org = active_org(user, request)
    r = await db.reports.find_one({"id": report_id, "org_id": org}, {"_id": 0})
    if not r:
        raise HTTPException(404, "Report not found")
    if format == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["metric", "value"])
        for k, v in r["summary"].items():
            w.writerow([k, v])
        return StreamingResponse(io.BytesIO(buf.getvalue().encode()), media_type="text/csv",
                                 headers={"Content-Disposition": f"attachment; filename=report-{report_id}.csv"})
    return StreamingResponse(io.BytesIO(json.dumps(r, indent=2).encode()), media_type="application/json",
                             headers={"Content-Disposition": f"attachment; filename=report-{report_id}.json"})


# ============================= NOTIFICATIONS =============================
@api.get("/notifications")
async def notifications(request: Request, user=Depends(get_current_user)):
    org = active_org(user, request)
    rows = await db.notifications.find({"org_id": org}, {"_id": 0}).sort("created_at", -1).limit(30).to_list(30)
    unread = await db.notifications.count_documents({"org_id": org, "read": False})
    return {"notifications": rows, "unread": unread}


@api.post("/notifications/read")
async def read_notifications(request: Request, user=Depends(get_current_user)):
    org = active_org(user, request)
    await db.notifications.update_many({"org_id": org}, {"$set": {"read": True}})
    return {"ok": True}


# ============================= GLOBAL SEARCH =============================
@api.get("/search")
async def global_search(request: Request, q: str, user=Depends(get_current_user)):
    org = active_org(user, request)
    rx = {"$regex": re.escape(q[:128]), "$options": "i"}
    events = await db.events.find({"org_id": org, "$or": [{"host": rx}, {"src_ip": rx}, {"username": rx}]},
                                  {"_id": 0, "raw": 0}).limit(5).to_list(5)
    alerts = await db.alerts.find({"org_id": org, "title": rx}, {"_id": 0}).limit(5).to_list(5)
    invs = await db.investigations.find({"org_id": org, "title": rx}, {"_id": 0}).limit(5).to_list(5)
    rules = await db.detection_rules.find({"org_id": org, "name": rx}, {"_id": 0}).limit(5).to_list(5)
    assets = await db.events.distinct("host", {"org_id": org, "host": rx})
    return {"events": events, "alerts": alerts, "investigations": invs, "rules": rules,
            "assets": [{"host": a} for a in assets[:5]]}


# ============================= SETTINGS / ADMIN =============================
@api.get("/settings")
async def get_settings(request: Request, user=Depends(get_current_user)):
    org = active_org(user, request)
    s = await db.settings.find_one({"org_id": org}, {"_id": 0})
    if not s:
        s = {"org_id": org, "app_name": "SentinelLab", "timezone": "UTC",
             "default_time_range": "24h", "retention_days": 90, "demo_mode": False}
        await db.settings.insert_one(dict(s))
        s.pop("_id", None)
    s["ai_configured"] = ai_assistant.is_configured()
    return {"settings": s}


@api.put("/settings")
async def update_settings(body: SettingsReq, request: Request, user=Depends(require_role("soc_manager"))):
    org = active_org(user, request)
    upd = {k: v for k, v in body.model_dump().items() if v is not None}
    await db.settings.update_one({"org_id": org}, {"$set": upd}, upsert=True)
    await audit(org, user, "update", "settings", details=upd)
    return clean(await db.settings.find_one({"org_id": org}, {"_id": 0}))


class AdminCreateUserReq(BaseModel):
    username: Optional[str] = None
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=12, max_length=128)


@api.post("/admin/users", status_code=201)
async def admin_create_user(body: AdminCreateUserReq, user=Depends(require_role("admin"))):
    """Provision an analyst with Training Lab access only."""
    email = body.email.strip().lower()
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "Name is required")
    if await db.users.find_one({"email": email}):
        raise HTTPException(409, "Email already registered")
    username = (body.username or email.split("@")[0]).strip().lower()
    if not USERNAME_RE.fullmatch(username):
        raise HTTPException(422, "Username must be 3–32 characters, start with a letter, and use letters, numbers, dots, underscores or hyphens")
    if await db.users.find_one({"username": username}):
        raise HTTPException(409, "Username already registered")
    entry = {"id": new_id(), "email": email, "username": username, "name": name,
             "password_hash": hash_password(body.password), "role": "analyst",
             "org_ids": [TRAIN_ORG], "default_org": TRAIN_ORG,
             "theme": "obsidian_dark", "created_at": now_iso()}
    from pymongo.errors import DuplicateKeyError
    try:
        await db.users.insert_one(dict(entry))
    except DuplicateKeyError as exc:
        raise HTTPException(409, "Email or username already registered") from exc
    await audit(user.get("default_org"), user, "create_user", "user", entry["id"],
                {"email": email, "role": "analyst"})
    return {"user": {k: v for k, v in entry.items() if k != "password_hash"}}


class AdminUsernameReq(BaseModel):
    username: str = Field(min_length=3, max_length=32)

class AdminPasswordReq(BaseModel):
    password: str = Field(min_length=12, max_length=128)

@api.put("/admin/users/{user_id}/username")
async def admin_set_username(user_id: str, body: AdminUsernameReq, actor=Depends(require_role("super_admin"))):
    username = body.username.strip().lower()
    if not USERNAME_RE.fullmatch(username):
        raise HTTPException(422, "Invalid username format")
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(404, "User not found")
    if await db.users.find_one({"username": username, "id": {"$ne": user_id}}):
        raise HTTPException(409, "Username already in use")
    from pymongo.errors import DuplicateKeyError
    try:
        await db.users.update_one({"id": user_id}, {"$set": {"username": username}})
    except DuplicateKeyError as exc:
        raise HTTPException(409, "Username already in use") from exc
    await audit(actor.get("default_org"), actor, "set_username", "user", user_id)
    return {"ok": True, "username": username}

@api.put("/admin/users/{user_id}/password")
async def admin_reset_password(user_id: str, body: AdminPasswordReq, actor=Depends(require_role("super_admin"))):
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(404, "User not found")
    if target["id"] == actor["id"]:
        raise HTTPException(400, "Use your own password-change flow")
    await db.users.update_one({"id": user_id}, {"$set": {"password_hash": hash_password(body.password)}, "$inc": {"session_version": 1}})
    await audit(actor.get("default_org"), actor, "reset_password", "user", user_id)
    return {"ok": True}

@api.put("/admin/users/{user_id}/status")
async def admin_set_status(user_id: str, body: dict, actor=Depends(require_role("super_admin"))):
    enabled = body.get("enabled")
    if not isinstance(enabled, bool):
        raise HTTPException(422, "enabled must be boolean")
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(404, "User not found")
    if target["id"] == actor["id"]:
        raise HTTPException(400, "Cannot disable your own account")
    if target.get("role") == "super_admin":
        raise HTTPException(403, "Cannot disable a super administrator")
    await db.users.update_one({"id": user_id}, {"$set": {"enabled": enabled}, "$inc": {"session_version": 1}})
    await audit(actor.get("default_org"), actor, "enable_user" if enabled else "disable_user", "user", user_id)
    return {"ok": True, "enabled": enabled}

@api.get("/admin/login-security-events")
async def admin_login_security_events(actor=Depends(require_role("super_admin"))):
    rows = await db.security_notifications.find(
        {"type": "account_login_locked"}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return {"events": rows, "open_count": sum(e.get("status") == "open" for e in rows)}


@api.post("/admin/users/{user_id}/unlock-login")
async def admin_unlock_login(user_id: str, actor=Depends(require_role("super_admin"))):
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(404, "User not found")
    await db.users.update_one({"id": user_id}, {"$unset": {"login_locked_until": "", "login_failed_count": ""}})
    # Clear throttles for this user's known identifiers, not other users.
    identifiers = [target.get("email", ""), target.get("username", "")]
    for identifier in filter(None, identifiers):
        await db.login_attempts.delete_many({"identifier": {"$regex": ":" + re.escape(identifier) + "$"}})
    await db.security_notifications.update_many(
        {"type": "account_login_locked", "user_id": user_id, "status": "open"},
        {"$set": {"status": "resolved", "resolved_at": now_iso(), "resolved_by": actor["id"]}}
    )
    await audit(actor.get("default_org"), actor, "unlock_login", "user", user_id)
    return {"ok": True}


@api.get("/admin/users")
async def admin_users(request: Request, user=Depends(require_role("admin"))):
    rows = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(500)
    return {"users": rows, "roles": ROLE_LABELS}


@api.put("/admin/users/{user_id}/role")
async def set_role(user_id: str, body: dict, request: Request, user=Depends(require_role("admin"))):
    role = body.get("role")
    if role not in ROLE_LEVELS:
        raise HTTPException(400, "Invalid role")
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(404, "User not found")
    if (role == "super_admin" or target.get("role") == "super_admin") and user.get("role") != "super_admin":
        raise HTTPException(403, "Only super administrators can manage super-admin roles")
    if target["id"] == user["id"] and role != target.get("role"):
        raise HTTPException(400, "Cannot change your own administrator role")
    await db.users.update_one({"id": user_id}, {"$set": {"role": role}})
    await audit(user.get("default_org"), user, "set_role", "user", user_id, {"role": role})
    return {"ok": True}


@api.get("/admin/membership-review")
async def membership_review(user=Depends(require_role("super_admin"))):
    """Read-only review of legacy production memberships; no automatic revocation."""
    rows = await db.users.find({"org_ids": PROD_ORG}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return {"production_members": rows, "count": len(rows), "requires_manual_review": True}


@api.put("/admin/users/{user_id}/workspaces")
async def set_user_workspaces(user_id: str, body: dict, user=Depends(require_role("super_admin"))):
    """Explicit super-admin approval or revocation of built-in workspace access."""
    org_ids = body.get("org_ids")
    if not isinstance(org_ids, list) or not org_ids or len(org_ids) != len(set(str(v) for v in org_ids)) or any(not isinstance(v, str) or v not in (PROD_ORG, TRAIN_ORG) for v in org_ids):
        raise HTTPException(400, "Specify a nonempty, unique list of known workspace IDs")
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(404, "User not found")
    if target["id"] == user["id"] and PROD_ORG not in org_ids:
        raise HTTPException(400, "Cannot remove your own production access")
    if target.get("role") == "super_admin" and PROD_ORG not in org_ids:
        raise HTTPException(400, "Cannot remove production access from a super administrator")
    if set(org_ids) == set(target.get("org_ids", [])):
        return {"ok": True, "org_ids": target.get("org_ids", []), "default_org": target.get("default_org"), "unchanged": True}
    if PROD_ORG in org_ids and PROD_ORG not in target.get("org_ids", []):
        raise HTTPException(409, "Production grants require a separate super-admin approval request")
    default_org = target.get("default_org") if target.get("default_org") in org_ids else org_ids[0]
    result = await db.users.update_one({"id": user_id}, {"$set": {"org_ids": org_ids, "default_org": default_org}})
    await audit(user.get("default_org"), user, "set_workspaces", "user", user_id,
                {"old_org_ids": target.get("org_ids", []), "new_org_ids": org_ids})
    return {"ok": result.matched_count == 1, "org_ids": org_ids, "default_org": default_org}


@api.post("/admin/users/{user_id}/production-access-requests")
async def request_production_access(user_id: str, user=Depends(require_role("super_admin"))):
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(404, "User not found")
    if PROD_ORG in target.get("org_ids", []):
        raise HTTPException(409, "User already has production access")
    if target["id"] == user["id"]:
        raise HTTPException(400, "Cannot request production access for yourself")
    existing = await db.production_access_requests.find_one({"target_id": user_id, "status": "pending"})
    if existing:
        raise HTTPException(409, "A production access request is already pending")
    entry = {"id": new_id(), "target_id": user_id, "requester_id": user["id"],
             "status": "pending", "created_at": now_iso()}
    await db.production_access_requests.insert_one(dict(entry))
    await audit(user.get("default_org"), user, "request_production_access", "user", user_id, {"request_id": entry["id"]})
    return clean(entry)


@api.get("/admin/production-access-requests")
async def list_production_access_requests(user=Depends(require_role("super_admin"))):
    rows = await db.production_access_requests.find({}, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    for entry in rows:
        if entry.get("status") != "applying":
            continue
        raw = entry.get("approved_at")
        try:
            timestamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            entry["needs_reconciliation"] = timestamp <= cutoff
        except (ValueError, TypeError, AttributeError):
            entry["needs_reconciliation"] = True
    return {"requests": rows, "stale_after_minutes": 5}


@api.post("/admin/production-access-requests/{request_id}/approve")
async def approve_production_access(request_id: str, user=Depends(require_role("super_admin"))):
    entry = await db.production_access_requests.find_one({"id": request_id, "status": "pending"})
    if not entry:
        raise HTTPException(404, "Pending request not found")
    if entry["requester_id"] == user["id"]:
        raise HTTPException(403, "A different super administrator must approve this request")
    target = await db.users.find_one({"id": entry["target_id"]})
    if not target:
        raise HTTPException(404, "Target user not found")
    if PROD_ORG in target.get("org_ids", []):
        raise HTTPException(409, "Target already has production access")
    claim = await db.production_access_requests.update_one(
        {"id": request_id, "status": "pending"},
        {"$set": {"status": "applying", "approver_id": user["id"], "approved_at": now_iso()}})
    if claim.modified_count != 1:
        raise HTTPException(409, "Request already processed")
    result = await db.users.update_one({"id": target["id"], "org_ids": {"$ne": PROD_ORG}},
                                       {"$addToSet": {"org_ids": PROD_ORG}})
    if result.modified_count != 1:
        await db.production_access_requests.update_one({"id": request_id, "status": "applying"},
            {"$set": {"status": "failed", "failure_reason": "membership_update_not_applied", "failed_at": now_iso()}})
        raise HTTPException(409, "Production grant could not be applied; review account state")
    await db.production_access_requests.update_one({"id": request_id, "status": "applying"},
        {"$set": {"status": "approved", "completed_at": now_iso()}})
    await audit(user.get("default_org"), user, "approve_production_access", "user", target["id"],
                {"request_id": request_id, "requester_id": entry["requester_id"]})
    return {"ok": True, "target_id": target["id"], "request_id": request_id}


@api.post("/admin/production-access-requests/{request_id}/reconcile")
async def reconcile_production_access(request_id: str, user=Depends(require_role("super_admin"))):
    """Resolve a request left in applying after a process interruption; never grant access here."""
    entry = await db.production_access_requests.find_one({"id": request_id, "status": "applying"})
    if not entry:
        raise HTTPException(404, "Applying request not found")
    raw = entry.get("approved_at")
    try:
        approved_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if approved_at.tzinfo is None:
            approved_at = approved_at.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError, AttributeError):
        approved_at = None
    if approved_at is not None and approved_at > datetime.now(timezone.utc) - timedelta(minutes=5):
        raise HTTPException(409, "Approval may still be in progress; wait five minutes before reconciling")
    target = await db.users.find_one({"id": entry["target_id"]})
    granted = bool(target and PROD_ORG in target.get("org_ids", []))
    final_status = "approved" if granted else "failed"
    result = await db.production_access_requests.update_one({"id": request_id, "status": "applying"},
        {"$set": {"status": final_status, "reconciled_at": now_iso(),
                  "failure_reason": None if granted else "membership_not_present"}})
    if result.modified_count != 1:
        raise HTTPException(409, "Request state changed; reload before reconciling")
    await audit(user.get("default_org"), user, "reconcile_production_access", "user", entry["target_id"],
                {"request_id": request_id, "final_status": final_status})
    return {"ok": True, "status": final_status, "request_id": request_id}


@api.get("/admin/audit")
async def admin_audit(request: Request, user=Depends(require_role("soc_manager"))):
    org = active_org(user, request)
    rows = await db.audit_logs.find({"org_id": org}, {"_id": 0}).sort("timestamp", -1).limit(100).to_list(100)
    return {"audit": rows}


@api.get("/admin/health")
async def admin_health(user=Depends(get_current_user)):
    try:
        await db.command("ping")
        dbok = True
    except Exception:
        dbok = False
    return {"database": "ok" if dbok else "down", "search_backend": "mongo-adapter",
            "ai_assistant": "configured" if ai_assistant.is_configured() else "disabled"}


# ============================= USER PREFS =============================
@api.put("/me/theme")
async def set_theme(body: dict, user=Depends(get_current_user)):
    await db.users.update_one({"id": user["id"]}, {"$set": {"theme": body.get("theme", "obsidian_dark")}})
    return {"ok": True}


@api.put("/me/workspace")
async def set_workspace(body: dict, user=Depends(get_current_user)):
    wid = body.get("workspace_id")
    if wid not in user.get("org_ids", []):
        raise HTTPException(403, "No access to workspace")
    await db.users.update_one({"id": user["id"]}, {"$set": {"default_org": wid}})
    return {"ok": True}


# ============================= AI ASSISTANT =============================
@api.post("/ai/ask")
async def ai_ask(body: AIReq, request: Request, user=Depends(get_current_user)):
    org = active_org(user, request)
    res = await ai_assistant.ask(org, body.message, body.ctx_type, body.ctx_id, session_id=user["id"])
    return res


# ============================= DEMO MODE =============================
@api.post("/demo/reset")
async def demo_reset(request: Request, user=Depends(require_role("soc_manager"))):
    for coll in ["events", "alerts", "detection_rules", "sources", "investigations",
                 "indicators", "notifications", "reports"]:
        await db[coll].delete_many({"org_id": TRAIN_ORG})
    await seedmod.seed_training_workspace(TRAIN_ORG)
    return {"ok": True}


# ============================= THREAT INTELLIGENCE (IOCs) =============================
class IndicatorReq(BaseModel):
    ioc_type: str  # ip, domain, url, hash, email
    value: str
    confidence: int = 70
    source: str = "manual"
    tags: List[str] = []


@api.get("/indicators")
async def list_indicators(request: Request, ioc_type: Optional[str] = None, active: Optional[bool] = None,
                          q: Optional[str] = None, user=Depends(get_current_user)):
    org = active_org(user, request)
    filt = {"org_id": org}
    if ioc_type: filt["ioc_type"] = ioc_type
    if active is not None: filt["active"] = active
    if q: filt["value"] = {"$regex": re.escape(q[:128]), "$options": "i"}
    rows = await db.indicators.find(filt, {"_id": 0}).sort("created_at", -1).limit(1000).to_list(1000)
    stats = {}
    for t in ["ip", "domain", "url", "hash", "email"]:
        stats[t] = await db.indicators.count_documents({"org_id": org, "ioc_type": t})
    return {"indicators": rows, "stats": stats}


@api.post("/indicators")
async def create_indicator(body: IndicatorReq, request: Request, user=Depends(require_role("analyst"))):
    org = active_org(user, request)
    doc = {"id": new_id(), "org_id": org, "ioc_type": body.ioc_type, "value": body.value.strip(),
           "confidence": body.confidence, "source": body.source, "tags": body.tags,
           "active": True, "false_positive": False, "hits": 0,
           "created_at": now_iso(), "is_synthetic": org == TRAIN_ORG}
    await db.indicators.insert_one(dict(doc))
    await audit(org, user, "create", "indicator", doc["id"], {"value": body.value})
    return clean(doc)


@api.put("/indicators/{ind_id}")
async def update_indicator(ind_id: str, request: Request, body: dict, user=Depends(require_role("analyst"))):
    org = active_org(user, request)
    upd = {k: v for k, v in body.items() if k in ("active", "false_positive", "confidence", "tags")}
    await db.indicators.update_one({"id": ind_id, "org_id": org}, {"$set": upd})
    return clean(await db.indicators.find_one({"id": ind_id, "org_id": org}, {"_id": 0}))


@api.delete("/indicators/{ind_id}")
async def delete_indicator(ind_id: str, request: Request, user=Depends(require_role("analyst"))):
    org = active_org(user, request)
    await db.indicators.delete_one({"id": ind_id, "org_id": org})
    await audit(org, user, "delete", "indicator", ind_id)
    return {"ok": True}


@api.get("/indicators/{ind_id}/hits")
async def indicator_hits(ind_id: str, request: Request, user=Depends(get_current_user)):
    org = active_org(user, request)
    ind = await db.indicators.find_one({"id": ind_id, "org_id": org}, {"_id": 0})
    if not ind:
        raise HTTPException(404, "Indicator not found")
    v = str(ind["value"]).lower()
    fields = {"ip": ["src_ip", "dest_ip"], "domain": ["dns_query"], "hash": ["file_hash"],
              "url": ["dns_query"], "email": ["username"]}.get(ind["ioc_type"], [])
    ors = [{f: {"$regex": f"^{re.escape(v[:256])}$", "$options": "i"}} for f in fields]
    events = await db.events.find({"org_id": org, "$or": ors or [{"id": "__none__"}]},
                                  {"_id": 0, "raw": 0}).limit(100).to_list(100) if ors else []
    return {"indicator": ind, "hits": events, "count": len(events)}


def _parse_stix_pattern(pattern: str):
    """Extract (ioc_type, value) pairs from a STIX 2.1 indicator pattern."""
    out = []
    m = {"ipv4-addr:value": "ip", "ipv6-addr:value": "ip", "domain-name:value": "domain",
         "url:value": "url", "email-addr:value": "email",
         "file:hashes.'SHA-256'": "hash", "file:hashes.MD5": "hash", "file:hashes.'SHA-1'": "hash"}
    import re as _re
    for mm in _re.finditer(r"([\w:\-\.'`]+)\s*=\s*'([^']+)'", pattern or ""):
        key, val = mm.group(1).strip(), mm.group(2).strip()
        for k, t in m.items():
            if key.lower().replace("`", "'") == k.lower():
                out.append((t, val)); break
        else:
            if "hashes" in key.lower():
                out.append(("hash", val))
    return out


@api.post("/indicators/import")
async def import_indicators(request: Request, body: dict, user=Depends(require_role("analyst"))):
    """Import IOCs from CSV text (type,value,confidence,source,tags) or STIX 2.1 bundle JSON."""
    org = active_org(user, request)
    fmt = body.get("format", "csv")
    data = body.get("data", "")
    docs = []
    if fmt == "csv":
        reader = csv.DictReader(io.StringIO(data)) if "," in data.split("\n", 1)[0] else None
        if reader and reader.fieldnames and "value" in [f.lower() for f in reader.fieldnames]:
            for r in reader:
                r = {k.lower().strip(): v for k, v in r.items() if k}
                if not r.get("value"): continue
                docs.append((r.get("type", "ip"), r["value"], int(r.get("confidence") or 70),
                             r.get("source", "csv-import"),
                             [t for t in (r.get("tags", "") or "").split(";") if t]))
        else:
            for line in data.splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2 and parts[1]:
                    docs.append((parts[0] or "ip", parts[1], int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 70,
                                 parts[3] if len(parts) > 3 else "csv-import",
                                 parts[4].split(";") if len(parts) > 4 else []))
    elif fmt == "stix":
        try:
            bundle = json.loads(data)
        except Exception as ex:
            raise HTTPException(400, f"Invalid STIX JSON: {ex}")
        for obj in bundle.get("objects", []):
            if obj.get("type") == "indicator":
                for t, v in _parse_stix_pattern(obj.get("pattern", "")):
                    conf = obj.get("confidence", 70)
                    docs.append((t, v, conf, obj.get("name", "stix-import"), obj.get("labels", [])))
    inserted = 0
    for t, v, conf, src, tags in docs:
        if await db.indicators.find_one({"org_id": org, "value": v, "ioc_type": t}):
            continue
        await db.indicators.insert_one({"id": new_id(), "org_id": org, "ioc_type": t, "value": str(v).strip(),
                                        "confidence": conf, "source": src, "tags": tags, "active": True,
                                        "false_positive": False, "hits": 0, "created_at": now_iso(),
                                        "is_synthetic": org == TRAIN_ORG})
        inserted += 1
    await audit(org, user, "import", "indicator", details={"count": inserted, "format": fmt})
    return {"imported": inserted, "parsed": len(docs)}


@api.post("/indicators/scan")
async def scan_indicators(request: Request, time_range: str = "7d", user=Depends(require_role("analyst"))):
    """Match all active indicators against recent events and generate alerts for hits."""
    org = active_org(user, request)
    events = await db.events.find({"org_id": org, "timestamp": {"$gte": _range_to_iso(time_range)}},
                                  {"_id": 0}).limit(10000).to_list(10000)
    rules = await db.detection_rules.find({"org_id": org, "rule_type": "indicator", "enabled": True},
                                          {"_id": 0}).to_list(50)
    total = 0
    for rule in rules:
        alerts, matched = await evaluate_rule(rule, events, org)
        for a in alerts:
            existing = await db.alerts.find_one({"org_id": org, "rule_id": rule["id"], "title": a["title"],
                                                 "status": {"$in": ["new", "triaged", "investigating"]}})
            if not existing:
                await db.alerts.insert_one(dict(a)); total += 1
    return {"alerts_generated": total, "events_scanned": len(events)}


# ============================= MITRE ATT&CK =============================
@api.get("/mitre/coverage")
async def mitre_coverage(request: Request, user=Depends(get_current_user)):
    org = active_org(user, request)
    rules = await db.detection_rules.find({"org_id": org}, {"_id": 0}).to_list(500)
    covered, rule_map = set(), {}
    for r in rules:
        if not r.get("enabled"):
            continue
        for tech in r.get("mitre", []):
            covered.add(tech)
            if "." in tech:
                covered.add(tech.split(".")[0])
            rule_map.setdefault(tech, []).append({"id": r["id"], "name": r["name"], "severity": r["severity"]})
    alert_counts = {}
    async for a in db.alerts.find({"org_id": org}, {"mitre": 1, "_id": 0}):
        for m in a.get("mitre", []):
            alert_counts[m] = alert_counts.get(m, 0) + 1
            if "." in m:
                p = m.split(".")[0]
                alert_counts[p] = alert_counts.get(p, 0) + 1
    techs = []
    for t in TECHNIQUES:
        tid = t["id"]
        techs.append({**t, "covered": tid in covered, "alerts": alert_counts.get(tid, 0),
                      "rules": rule_map.get(tid, [])})
    gap = [t for t in techs if not t["covered"]]
    total = len(TECHNIQUES)
    return {"version": ATTACK_VERSION, "tactics": TACTICS, "techniques": techs,
            "coverage_pct": round(100 * sum(1 for t in techs if t["covered"]) / max(total, 1)),
            "covered_count": sum(1 for t in techs if t["covered"]), "total": total,
            "gaps": gap, "gap_count": len(gap)}


# ============================= INCIDENT RESPONSE PLAYBOOKS =============================
@api.get("/playbooks")
async def list_playbooks(user=Depends(get_current_user)):
    return {"playbooks": pbmod.BUILTIN}


@api.post("/playbooks/run")
async def run_playbook(request: Request, body: dict, user=Depends(require_role("analyst"))):
    org = active_org(user, request)
    pb = pbmod.PLAYBOOK_MAP.get(body.get("playbook_id"))
    if not pb:
        raise HTTPException(404, "Playbook not found")
    alert = None
    if body.get("alert_id"):
        alert = await db.alerts.find_one({"id": body["alert_id"], "org_id": org}, {"_id": 0})
        if not alert:
            raise HTTPException(404, "Alert not found")
    dry_run = body.get("dry_run", True)
    record = await pbmod.execute(pb, org, alert, user, dry_run=dry_run, approvals=body.get("approvals", []))
    if not dry_run:
        await audit(org, user, "run_playbook", "playbook", pb["id"],
                    {"alert_id": body.get("alert_id"), "dry_run": dry_run})
    return record


@api.get("/playbooks/executions")
async def playbook_executions(request: Request, user=Depends(get_current_user)):
    org = active_org(user, request)
    rows = await db.automation_executions.find({"org_id": org}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return {"executions": rows}


# ============================= INVESTIGATION GRAPH =============================
_GRAPH_FIELDS = [("host", "host"), ("src_ip", "ip"), ("dest_ip", "ip"),
                 ("username", "user"), ("process_name", "process")]


async def _build_graph(org, stype, sval):
    nodes, edges, seen = {}, [], set()

    def add_node(nid, label, ntype, meta=None):
        if nid not in nodes:
            nodes[nid] = {"id": nid, "label": str(label), "type": ntype, "meta": meta or {}}

    def add_edge(a, b, label):
        if a == b:
            return
        key = tuple(sorted([a, b])) + (label,)
        if key in seen:
            return
        seen.add(key)
        edges.append({"source": a, "target": b, "label": label})

    def link_entities(center, evs):
        for e in evs:
            for field, ntype in _GRAPH_FIELDS:
                v = e.get(field)
                if not v:
                    continue
                nid = f"{ntype}:{v}"
                add_node(nid, v, ntype)
                add_edge(center, nid, field)

    center = f"{stype}:{sval}"
    if stype == "alert":
        a = await db.alerts.find_one({"id": sval, "org_id": org}, {"_id": 0})
        if not a:
            raise HTTPException(404, "Alert not found")
        add_node(center, a["title"], "alert", {"severity": a["severity"]})
        evs = await db.events.find({"id": {"$in": a.get("related_events", [])[:300]}},
                                   {"_id": 0, "raw": 0}).to_list(300)
        link_entities(center, evs)
        if a.get("investigation_id"):
            inv = await db.investigations.find_one({"id": a["investigation_id"], "org_id": org}, {"_id": 0}) \
                or await db.investigations.find_one({"org_id": org, "title": a["investigation_id"]}, {"_id": 0})
            if inv:
                invid = f"investigation:{inv['id']}"
                add_node(invid, inv["title"], "investigation")
                add_edge(invid, center, "contains")
    else:
        label = sval
        if stype == "indicator":
            ind = await db.indicators.find_one({"id": sval, "org_id": org}, {"_id": 0})
            if not ind:
                raise HTTPException(404, "Indicator not found")
            sval = ind["value"]
            center = f"indicator:{ind['id']}"
            label = ind["value"]
        add_node(center, label, stype)
        qmap = {"host": {"host": sval}, "user": {"username": sval}, "process": {"process_name": sval},
                "ip": {"$or": [{"src_ip": sval}, {"dest_ip": sval}]},
                "indicator": {"$or": [{"src_ip": sval}, {"dest_ip": sval}, {"file_hash": sval}, {"dns_query": sval}]}}
        evs = await db.events.find({"org_id": org, **qmap.get(stype, {})},
                                   {"_id": 0, "raw": 0}).limit(300).to_list(300)
        link_entities(center, evs)
        # alerts referencing this entity
        afilt = {"host": {"host": sval}, "ip": {"src_ip": sval}, "user": {"username": sval}}.get(stype)
        if afilt:
            als = await db.alerts.find({"org_id": org, **afilt}, {"_id": 0}).limit(40).to_list(40)
            for al in als:
                aid = f"alert:{al['id']}"
                add_node(aid, al["title"], "alert", {"severity": al["severity"]})
                add_edge(aid, center, "alerts")

    # enrich ip nodes with indicator matches
    ip_nodes = [n for n in list(nodes.values()) if n["type"] == "ip"]
    for n in ip_nodes:
        ind = await db.indicators.find_one({"org_id": org, "value": n["label"], "active": True}, {"_id": 0})
        if ind:
            iid = f"indicator:{ind['id']}"
            add_node(iid, ind["value"], "indicator", {"confidence": ind["confidence"]})
            add_edge(n["id"], iid, "ioc")
    return {"nodes": list(nodes.values())[:70], "edges": edges, "seed": {"type": stype, "value": sval}}


@api.post("/graph")
async def graph(request: Request, body: dict, user=Depends(get_current_user)):
    org = active_org(user, request)
    stype = body.get("seed_type", "alert")
    sval = body.get("seed_value")
    if not sval:
        a = await db.alerts.find_one({"org_id": org}, {"_id": 0}, sort=[("created_at", -1)])
        if not a:
            return {"nodes": [], "edges": [], "seed": None}
        stype, sval = "alert", a["id"]
    return await _build_graph(org, stype, sval)


# ============================= DETECTION REPLAY LAB =============================
class ReplayReq(BaseModel):
    format: str = "json"
    payload: object
    expected_rules: List[str] = []


@api.post("/replay")
async def replay(body: ReplayReq, request: Request, user=Depends(require_role("analyst"))):
    """Replay telemetry against enabled rules WITHOUT persisting events or alerts (isolated)."""
    org = active_org(user, request)
    try:
        records = parse_payload(body.payload, body.format)
    except Exception as ex:
        raise HTTPException(400, f"Parse error: {ex}")
    stub = {"id": "replay", "name": "Replay Lab"}
    docs = [normalize(r, org, stub, is_synthetic=True) for r in records]
    rules = await db.detection_rules.find({"org_id": org, "enabled": True}, {"_id": 0}).to_list(500)
    t0 = datetime.now(timezone.utc)
    results, triggered = [], set()
    for rule in rules:
        alerts, matched = await evaluate_rule(rule, docs, org)
        if alerts:
            triggered.add(rule["name"])
            results.append({"rule_id": rule["id"], "rule_name": rule["name"], "severity": rule["severity"],
                            "rule_type": rule["rule_type"], "would_alert": len(alerts),
                            "matched_events": len(matched), "mitre": rule.get("mitre", [])})
    took = (datetime.now(timezone.utc) - t0).total_seconds() * 1000
    expected = set(body.expected_rules)
    comparison = None
    if expected:
        comparison = {"matched": sorted(expected & triggered), "missing": sorted(expected - triggered),
                      "unexpected": sorted(triggered - expected),
                      "passed": expected.issubset(triggered) and not (triggered - expected)}
    return {"parsed_events": len(docs), "took_ms": round(took, 1), "rules_evaluated": len(rules),
            "triggered_count": len(triggered), "results": results, "comparison": comparison, "isolated": True}


@api.get("/replay/samples")
async def replay_samples(user=Depends(get_current_user)):
    import json as _j
    base = datetime.now(timezone.utc)
    def ts(m): return (base - timedelta(minutes=m)).isoformat()
    brute = [{"timestamp": ts(4 - i * 0.3), "category": "authentication", "event_type": "Authentication",
              "action": "login", "outcome": "failure", "src_ip": "203.0.113.9", "username": "admin",
              "host": "auth-01", "severity": "medium"} for i in range(7)]
    ps = [{"timestamp": ts(2), "category": "process", "event_type": "Process", "action": "process-create",
           "process_name": "powershell.exe", "parent_process": "winword.exe", "host": "WKS-22",
           "username": "jdoe", "command_line": "powershell.exe -nop -w hidden -enc ZQBjAGgAbwA=", "severity": "high"}]
    scan = [{"timestamp": ts(1.5 - i * 0.05), "category": "network", "event_type": "Connection",
             "action": "connect", "src_ip": "198.51.100.7", "dest_ip": "10.0.0.50", "dest_port": 20 + i,
             "protocol": "TCP", "host": "10.0.0.50", "severity": "low"} for i in range(13)]
    return {"samples": [
        {"name": "Brute Force (7 failed logins)", "format": "json", "payload": _j.dumps(brute, indent=2),
         "expected_rules": ["Brute Force Authentication"]},
        {"name": "Suspicious PowerShell (encoded)", "format": "json", "payload": _j.dumps(ps, indent=2),
         "expected_rules": ["Suspicious PowerShell Execution"]},
        {"name": "Port Scan (13 ports)", "format": "json", "payload": _j.dumps(scan, indent=2),
         "expected_rules": ["Port Scan Detected"]},
    ]}


# ============================= PIPELINE OBSERVATORY =============================
@api.get("/observatory")
async def observatory(request: Request, user=Depends(get_current_user)):
    from dateutil import parser as _dtp
    org = active_org(user, request)
    now = datetime.now(timezone.utc)
    since1h = (now - timedelta(hours=1)).isoformat()
    # eps per minute (last 60 min)
    pipeline = [
        {"$match": {"org_id": org, "ingested_at": {"$gte": since1h}}},
        {"$project": {"minute": {"$substr": ["$ingested_at", 0, 16]}}},
        {"$group": {"_id": "$minute", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    eps_rows = await db.events.aggregate(pipeline).to_list(120)
    eps_series = [{"time": r["_id"], "eps": round(r["count"] / 60, 2)} for r in eps_rows]
    total = await db.events.count_documents({"org_id": org})
    last1h = await db.events.count_documents({"org_id": org, "ingested_at": {"$gte": since1h}})
    parser_total = await db.parser_errors.count_documents({"org_id": org})
    recent_errors = await db.parser_errors.find({"org_id": org}, {"_id": 0}).sort("timestamp", -1).limit(10).to_list(10)
    # avg ingest delay from recent events
    sample = await db.events.find({"org_id": org}, {"_id": 0, "timestamp": 1, "ingested_at": 1}).sort("ingested_at", -1).limit(200).to_list(200)
    delays = []
    for e in sample:
        try:
            d = (_dtp.parse(e["ingested_at"]) - _dtp.parse(e["timestamp"])).total_seconds()
            if 0 <= d < 86400 * 3:
                delays.append(d)
        except Exception:
            pass
    avg_delay = round(sum(delays) / len(delays), 1) if delays else 0
    # per-source health
    sources = await db.sources.find({"org_id": org}, {"_id": 0, "token_hash": 0}).to_list(200)
    src_health = []
    for s in sources:
        tp = await db.events.count_documents({"org_id": org, "source_id": s["id"], "ingested_at": {"$gte": since1h}})
        src_health.append({"id": s["id"], "name": s.get("display_name") or s["name"], "status": s.get("status"),
                           "events_received": s.get("events_received", 0), "parse_errors": s.get("parse_errors", 0),
                           "throughput_1h": tp, "last_received": s.get("last_received")})
    online = sum(1 for s in sources if s.get("status") == "online")
    return {
        "eps_current": round(last1h / 3600, 3), "eps_series": eps_series,
        "total_indexed": total, "events_last_1h": last1h,
        "parser_failures": parser_total, "recent_errors": recent_errors,
        "avg_ingest_delay_s": avg_delay, "retry_queue_depth": 0, "dropped_events": parser_total,
        "index_backlog": 0, "sources_total": len(sources), "sources_online": online,
        "source_health": sorted(src_health, key=lambda x: -x["throughput_1h"]),
    }


# ============================= HEALTH =============================
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "sentinellab"}


@app.get("/api/ready")
async def ready():
    try:
        await db.command("ping")
        return {"ready": True}
    except Exception:
        raise HTTPException(503, "not ready")


# ============================= STARTUP =============================
@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("username", unique=True, sparse=True)
    await db.users.create_index("id", unique=True)
    await db.events.create_index([("org_id", 1), ("timestamp", -1)])
    await db.events.create_index([("org_id", 1), ("category", 1)])
    await db.alerts.create_index([("org_id", 1), ("status", 1)])
    await db.login_attempts.create_index("identifier")

    for oid, name, demo in [(PROD_ORG, "SentinelLab Production", False),
                            (TRAIN_ORG, "Training Lab (Synthetic)", True)]:
        await db.organizations.update_one({"id": oid},
            {"$setOnInsert": {"id": oid, "name": name, "is_demo": demo, "created_at": now_iso()}}, upsert=True)

    admin_email = os.environ.get("ADMIN_EMAIL", "admin@sentinellab.io").lower()
    admin_username = os.environ.get("ADMIN_USERNAME", "socadmin").strip().lower()
    if not USERNAME_RE.fullmatch(admin_username):
        raise RuntimeError("ADMIN_USERNAME must be a valid 3–32 character username")
    admin_pw = os.environ.get("ADMIN_PASSWORD")
    if not admin_pw or len(admin_pw) < 12:
        raise RuntimeError("ADMIN_PASSWORD must be configured with at least 12 characters")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({"id": new_id(), "email": admin_email, "username": admin_username, "name": "SOC Administrator",
                                   "password_hash": hash_password(admin_pw), "role": "super_admin",
                                   "org_ids": [PROD_ORG, TRAIN_ORG], "default_org": TRAIN_ORG,
                                   "theme": "obsidian_dark", "created_at": now_iso()})
    elif not existing.get("username") and not await db.users.find_one({"username": admin_username}):
        await db.users.update_one({"id": existing["id"]}, {"$set": {"username": admin_username}})
    if existing and not verify_password(admin_pw, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_pw)}})
    if os.environ.get("ENABLE_DEMO_ACCOUNTS") == "true" and not await db.users.find_one({"email": "analyst@sentinellab.io"}):
        await db.users.insert_one({"id": new_id(), "email": "analyst@sentinellab.io", "name": "SOC Analyst",
                                   "password_hash": hash_password("Analyst@2026"), "role": "analyst",
                                   "org_ids": [PROD_ORG, TRAIN_ORG], "default_org": TRAIN_ORG,
                                   "theme": "obsidian_dark", "created_at": now_iso()})
    if await db.detection_rules.count_documents({"org_id": PROD_ORG}) == 0:
        for r in seedmod.builtin_rules(PROD_ORG):
            await db.detection_rules.insert_one(r)
    await seedmod.seed_training_workspace(TRAIN_ORG)
    logger.info("SentinelLab startup complete")


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown():
    from core import client
    client.close()
