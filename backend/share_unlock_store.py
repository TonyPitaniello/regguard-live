"""Persist share-unlock across devices (research_id + optional email)."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

_BACKEND_DIR = Path(__file__).resolve().parent
_DIR = _BACKEND_DIR / "data" / "share_unlocks"
_LOCK = threading.Lock()
_FORWARDS_PATH = _BACKEND_DIR / "data" / "forward_events.jsonl"


def _path(research_id: str) -> Path:
    rid = "".join(c for c in (research_id or "") if c.isalnum() or c in "-_")[:80]
    _DIR.mkdir(parents=True, exist_ok=True)
    return _DIR / f"{rid}.json"


def is_unlocked(research_id: str, email: str = "") -> bool:
    rid = (research_id or "").strip()
    if not rid:
        return False
    p = _path(rid)
    if not p.is_file():
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return False
    if data.get("unlocked"):
        return True
    email_l = (email or "").strip().lower()
    if email_l and email_l in (data.get("emails") or []):
        return True
    return False


def grant_unlock(
    research_id: str,
    *,
    email: str = "",
    channel: str = "share",
) -> Dict[str, Any]:
    rid = (research_id or "").strip()
    if not rid:
        raise ValueError("research_id required")
    email_l = (email or "").strip().lower()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _LOCK:
        p = _path(rid)
        data: Dict[str, Any] = {"research_id": rid, "unlocked": True, "emails": [], "events": []}
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
        data["unlocked"] = True
        data["updated_at"] = now
        emails = list(data.get("emails") or [])
        if email_l and email_l not in emails:
            emails.append(email_l)
        data["emails"] = emails[-20:]
        ev = list(data.get("events") or [])
        ev.append({"ts": now, "channel": channel, "email": email_l})
        data["events"] = ev[-50:]
        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            _FORWARDS_PATH.parent.mkdir(parents=True, exist_ok=True)
            with _FORWARDS_PATH.open("a", encoding="utf-8") as f:
                f.write(
                    json.dumps(
                        {"ts": now, "research_id": rid, "channel": channel, "email": email_l}
                    )
                    + "\n"
                )
        except Exception:
            pass
    return data


def forward_count(limit_scan: int = 5000) -> int:
    if not _FORWARDS_PATH.is_file():
        return 0
    try:
        n = 0
        for _ in _FORWARDS_PATH.read_text(encoding="utf-8").splitlines()[-limit_scan:]:
            n += 1
        return n
    except Exception:
        return 0
