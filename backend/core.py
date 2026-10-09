"""Core: DB client, serialization, auth (bcrypt + JWT), RBAC, audit logging."""
import os
import jwt
import bcrypt
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Request, Depends
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

JWT_ALGORITHM = "HS256"
ACCESS_TTL_MIN = 480  # 8h analyst session


# ---------- helpers ----------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TTL_MIN),
        "type": "access",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def clean(doc: dict) -> dict:
    """Strip Mongo _id for JSON responses."""
    if doc is None:
        return None
    doc.pop("_id", None)
    return doc


# ---------- RBAC ----------
ROLE_LEVELS = {
    "super_admin": 100,
    "admin": 80,
    "soc_manager": 60,
    "analyst": 40,
    "auditor": 20,
}
ROLE_LABELS = {
    "super_admin": "Super Administrator",
    "admin": "Administrator",
    "soc_manager": "SOC Manager",
    "analyst": "Security Analyst",
    "auditor": "Read-Only Auditor",
}


def role_level(role: str) -> int:
    return ROLE_LEVELS.get(role, 0)


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"id": payload["sub"]})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user.pop("password_hash", None)
        return clean(user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_role(min_role: str):
    """Dependency factory enforcing a minimum role."""
    async def checker(user: dict = Depends(get_current_user)) -> dict:
        if role_level(user.get("role", "")) < role_level(min_role):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker


def active_org(user: dict, request: Request) -> str:
    """Resolve the active workspace from header, falling back to user default."""
    org = request.headers.get("X-Workspace-Id") or user.get("default_org")
    allowed = user.get("org_ids", [])
    if org not in allowed:
        # auditors/analysts cannot access workspaces they're not members of
        raise HTTPException(status_code=403, detail="Workspace access denied")
    return org


async def audit(org_id, user, action, resource_type, resource_id=None, details=None):
    await db.audit_logs.insert_one({
        "id": new_id(),
        "org_id": org_id,
        "user_id": user.get("id") if user else None,
        "user_email": user.get("email") if user else None,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details or {},
        "timestamp": now_iso(),
    })
