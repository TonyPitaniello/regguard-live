"""
Lightweight nurture queue: Day-7 win emails after Partner / Pro checkout.
File-backed for cron pickup (POST /cron/day7-win-emails).
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_ITEMS: Dict[str, Dict[str, Any]] = {}


def _iso(dt: Optional[datetime] = None) -> str:
    d = dt or datetime.now(timezone.utc)
    return d.isoformat().replace("+00:00", "Z")


def _store_path() -> Path:
    root = Path(os.getenv("REGGUARD_DATA_DIR") or "/tmp/regguard_data")
    root.mkdir(parents=True, exist_ok=True)
    return root / "nurture_queue.json"


def _load() -> None:
    global _ITEMS
    with _LOCK:
        if _ITEMS:
            return
        try:
            p = _store_path()
            if p.exists():
                _ITEMS = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("nurture load failed: %s", e)
            _ITEMS = {}


def _persist() -> None:
    with _LOCK:
        try:
            _store_path().write_text(json.dumps(_ITEMS, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("nurture persist failed: %s", e)


def schedule_day7_win(
    *,
    email: str,
    tier: str,
    order_id: str = "",
    days: int = 7,
) -> Optional[Dict[str, Any]]:
    email_n = (email or "").strip().lower()
    if not email_n or "@" not in email_n:
        return None
    tier_n = (tier or "").strip().lower()
    if tier_n not in ("partner", "contractor_pro"):
        return None

    _load()
    due = datetime.now(timezone.utc) + timedelta(days=max(1, days))
    with _LOCK:
        # One pending day-7 per email
        for item in _ITEMS.values():
            if (
                item.get("email") == email_n
                and item.get("kind") == "day7_win"
                and item.get("status") == "pending"
            ):
                return deepcopy(item)
        nid = uuid.uuid4().hex
        row = {
            "id": nid,
            "kind": "day7_win",
            "email": email_n,
            "tier": tier_n,
            "order_id": order_id,
            "due_at": _iso(due),
            "status": "pending",
            "created_at": _iso(),
            "sent_at": None,
        }
        _ITEMS[nid] = row
    _persist()
    logger.info("Scheduled day7 win for %s tier=%s due=%s", email_n, tier_n, row["due_at"])
    return deepcopy(row)


def due_day7_wins(now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    _load()
    now = now or datetime.now(timezone.utc)
    out: List[Dict[str, Any]] = []
    with _LOCK:
        for item in _ITEMS.values():
            if item.get("kind") != "day7_win" or item.get("status") != "pending":
                continue
            try:
                due = datetime.fromisoformat(
                    str(item.get("due_at") or "").replace("Z", "+00:00")
                )
            except Exception:
                continue
            if due <= now:
                out.append(deepcopy(item))
    return out


def mark_sent(item_id: str) -> bool:
    _load()
    with _LOCK:
        row = _ITEMS.get(item_id)
        if not row:
            return False
        row["status"] = "sent"
        row["sent_at"] = _iso()
    _persist()
    return True
