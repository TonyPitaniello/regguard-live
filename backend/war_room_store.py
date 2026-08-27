"""
War-room comments on a shared research_id (multiplayer deal team).

Local JSON primary + best-effort Supabase ``war_rooms`` dual-write.
Rate-limited writes; optional write_token for public share links.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_BACKEND = Path(__file__).resolve().parent
_DIR = _BACKEND / "data" / "war_rooms"
_LOCK = threading.Lock()
_ROLES = ("owner", "ic", "gc", "utility", "counsel", "other")

# Sliding-window rate limits (in-process; good enough for single API instance)
_RATE: Dict[str, deque] = defaultdict(deque)
_RATE_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _path(research_id: str) -> Path:
    rid = "".join(c for c in (research_id or "") if c.isalnum() or c in "-_")[:80]
    _DIR.mkdir(parents=True, exist_ok=True)
    return _DIR / f"{rid}.json"


def durable_backend() -> str:
    if _supabase_ok():
        return "supabase"
    if (os.getenv("WAR_ROOM_DURABLE_REQUIRED") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        return "required_missing"
    return "local_ephemeral"


def writes_enabled() -> bool:
    return durable_backend() != "required_missing"


def _supabase_ok() -> bool:
    return bool(
        (os.getenv("SUPABASE_URL") or "").strip()
        and (os.getenv("SUPABASE_KEY") or "").strip()
    )


def _supabase_upsert(payload: Dict[str, Any]) -> bool:
    if not _supabase_ok():
        return False
    try:
        from supabase import create_client

        sb = create_client(
            os.environ["SUPABASE_URL"].strip(),
            os.environ["SUPABASE_KEY"].strip(),
        )
        sb.table("war_rooms").upsert(
            {
                "research_id": payload["research_id"],
                "comments": payload.get("comments") or [],
                "write_token": payload.get("write_token") or "",
                "updated_at": payload.get("updated_at") or _now(),
            }
        ).execute()
        return True
    except Exception as e:
        logger.warning("Supabase war_rooms upsert failed (local still used): %s", e)
        return False


def _supabase_get(research_id: str) -> Optional[Dict[str, Any]]:
    if not _supabase_ok():
        return None
    try:
        from supabase import create_client

        sb = create_client(
            os.environ["SUPABASE_URL"].strip(),
            os.environ["SUPABASE_KEY"].strip(),
        )
        resp = (
            sb.table("war_rooms")
            .select("*")
            .eq("research_id", research_id)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return None
        row = rows[0]
        return {
            "research_id": row.get("research_id") or research_id,
            "comments": list(row.get("comments") or []),
            "write_token": row.get("write_token") or "",
            "updated_at": row.get("updated_at"),
        }
    except Exception as e:
        logger.warning("Supabase war_rooms get failed: %s", e)
        return None


def _load(research_id: str) -> Dict[str, Any]:
    rid = (research_id or "").strip()
    remote = _supabase_get(rid)
    p = _path(rid)
    local: Dict[str, Any] = {"research_id": rid, "comments": [], "write_token": ""}
    if p.is_file():
        try:
            local = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    if remote:
        # Prefer whichever has more comments / newer token
        remote_n = len(remote.get("comments") or [])
        local_n = len(local.get("comments") or [])
        if remote_n >= local_n:
            return remote
        if not remote.get("write_token") and local.get("write_token"):
            remote["write_token"] = local["write_token"]
        if remote_n < local_n:
            return local
        return remote
    return local


def _save(data: Dict[str, Any]) -> None:
    rid = str(data.get("research_id") or "")
    p = _path(rid)
    with _LOCK:
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    _supabase_upsert(data)


def ensure_write_token(research_id: str) -> str:
    """Mint a write token if missing; persist."""
    data = _load(research_id)
    token = str(data.get("write_token") or "").strip()
    if not token:
        token = secrets.token_urlsafe(16)
        data["write_token"] = token
        data["research_id"] = (research_id or "").strip()
        data.setdefault("comments", [])
        data["updated_at"] = _now()
        _save(data)
    return token


def verify_write_token(research_id: str, token: Optional[str]) -> bool:
    data = _load(research_id)
    expected = str(data.get("write_token") or "").strip()
    if not expected:
        # Lazy mint path: first authenticated open should call ensure_write_token
        return False
    got = (token or "").strip()
    return bool(got) and secrets.compare_digest(expected, got)


def check_rate_limit(
    *,
    research_id: str,
    client_key: str,
    per_room_per_hour: int = 40,
    per_client_per_hour: int = 20,
) -> Tuple[bool, str]:
    now = time.time()
    window = 3600.0

    def _ok(key: str, limit: int) -> bool:
        with _RATE_LOCK:
            q = _RATE[key]
            while q and (now - q[0]) > window:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True

    rid = (research_id or "unknown")[:80]
    ck = hashlib.sha256((client_key or "anon").encode("utf-8")).hexdigest()[:16]
    if not _ok(f"room:{rid}", per_room_per_hour):
        return False, "Too many war-room posts for this report. Try again later."
    if not _ok(f"client:{ck}", per_client_per_hour):
        return False, "Too many war-room posts from this client. Try again later."
    return True, ""


def list_comments(research_id: str) -> List[Dict[str, Any]]:
    data = _load(research_id)
    return list(data.get("comments") or [])


def room_meta(research_id: str) -> Dict[str, Any]:
    data = _load(research_id)
    backend = durable_backend()
    return {
        "research_id": research_id,
        "comment_count": len(data.get("comments") or []),
        "updated_at": data.get("updated_at"),
        "durable_backend": backend,
        "writes_enabled": writes_enabled(),
        "token_required": True,
        "has_token": bool(str(data.get("write_token") or "").strip()),
    }


def add_comment(
    research_id: str,
    *,
    author: str,
    role: str = "other",
    text: str,
    write_token: Optional[str] = None,
    client_key: str = "",
) -> Dict[str, Any]:
    if not writes_enabled():
        raise ValueError(
            "War room writes disabled until durable storage is configured "
            "(set SUPABASE_URL/KEY or unset WAR_ROOM_DURABLE_REQUIRED)."
        )
    rid = (research_id or "").strip()
    body = (text or "").strip()
    name = (author or "").strip()[:80] or "Anonymous"
    if not rid:
        raise ValueError("research_id required")
    if not body:
        raise ValueError("text required")
    if len(body) > 2000:
        raise ValueError("text too long")
    if not verify_write_token(rid, write_token):
        raise ValueError("Invalid or missing war-room write token")
    ok, msg = check_rate_limit(research_id=rid, client_key=client_key)
    if not ok:
        raise ValueError(msg)
    role_l = (role or "other").strip().lower()
    if role_l not in _ROLES:
        role_l = "other"
    comment = {
        "id": f"wr-{uuid.uuid4().hex[:10]}",
        "ts": _now(),
        "author": name,
        "role": role_l,
        "text": body,
    }
    data = _load(rid)
    comments = list(data.get("comments") or [])
    comments.append(comment)
    data["research_id"] = rid
    data["comments"] = comments[-200:]
    data["updated_at"] = comment["ts"]
    if not data.get("write_token"):
        data["write_token"] = write_token
    _save(data)
    return comment
