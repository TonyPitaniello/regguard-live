"""War-room comments on a shared research_id (multiplayer deal team)."""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

_BACKEND = Path(__file__).resolve().parent
_DIR = _BACKEND / "data" / "war_rooms"
_LOCK = threading.Lock()
_ROLES = ("owner", "ic", "gc", "utility", "counsel", "other")


def _path(research_id: str) -> Path:
    rid = "".join(c for c in (research_id or "") if c.isalnum() or c in "-_")[:80]
    _DIR.mkdir(parents=True, exist_ok=True)
    return _DIR / f"{rid}.json"


def list_comments(research_id: str) -> List[Dict[str, Any]]:
    p = _path(research_id)
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return list(data.get("comments") or [])
    except Exception:
        return []


def add_comment(
    research_id: str,
    *,
    author: str,
    role: str = "other",
    text: str,
) -> Dict[str, Any]:
    rid = (research_id or "").strip()
    body = (text or "").strip()
    name = (author or "").strip()[:80] or "Anonymous"
    if not rid:
        raise ValueError("research_id required")
    if not body:
        raise ValueError("text required")
    if len(body) > 2000:
        raise ValueError("text too long")
    role_l = (role or "other").strip().lower()
    if role_l not in _ROLES:
        role_l = "other"
    comment = {
        "id": f"wr-{uuid.uuid4().hex[:10]}",
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "author": name,
        "role": role_l,
        "text": body,
    }
    with _LOCK:
        p = _path(rid)
        data: Dict[str, Any] = {"research_id": rid, "comments": []}
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
        comments = list(data.get("comments") or [])
        comments.append(comment)
        data["comments"] = comments[-200:]
        data["updated_at"] = comment["ts"]
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return comment
