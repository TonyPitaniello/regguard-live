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


def mark_cancelled(item_id: str) -> bool:
    _load()
    with _LOCK:
        row = _ITEMS.get(item_id)
        if not row:
            return False
        row["status"] = "cancelled"
        row["cancelled_at"] = _iso()
    _persist()
    return True


def _pending_same(email_n: str, kind: str) -> Optional[Dict[str, Any]]:
    for item in _ITEMS.values():
        if (
            item.get("email") == email_n
            and item.get("kind") == kind
            and item.get("status") == "pending"
        ):
            return deepcopy(item)
    return None


def schedule_item(
    *,
    kind: str,
    email: str,
    delay_hours: float = 0,
    payload: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Generic nurture row (free-run drip, quota paywall, etc.)."""
    email_n = (email or "").strip().lower()
    kind_n = (kind or "").strip().lower()
    if not email_n or "@" not in email_n or not kind_n:
        return None
    _load()
    due = datetime.now(timezone.utc) + timedelta(hours=max(0.0, float(delay_hours)))
    with _LOCK:
        existing = None
        for item in _ITEMS.values():
            if (
                item.get("email") == email_n
                and item.get("kind") == kind_n
                and item.get("status") == "pending"
            ):
                existing = item
                break
        if existing:
            if payload:
                merged = dict(existing.get("payload") or {})
                merged.update(payload)
                existing["payload"] = merged
            return deepcopy(existing)
        nid = uuid.uuid4().hex
        row = {
            "id": nid,
            "kind": kind_n,
            "email": email_n,
            "tier": "",
            "order_id": "",
            "due_at": _iso(due),
            "status": "pending",
            "created_at": _iso(),
            "sent_at": None,
            "payload": dict(payload or {}),
        }
        _ITEMS[nid] = row
    _persist()
    logger.info("Scheduled nurture %s for %s due=%s", kind_n, email_n, row["due_at"])
    return deepcopy(row)


def schedule_free_run_drip(
    *,
    email: str,
    research_id: str = "",
    share_url: str = "",
    zip_code: str = "",
    city: str = "",
    address: str = "",
    referral_code: str = "",
) -> Dict[str, Any]:
    """Day-2 forward nudge + Day-5 pay CTA. Day-0 is the research memo already sent."""
    payload = {
        "research_id": research_id,
        "share_url": share_url,
        "zip": zip_code,
        "city": city,
        "address": address,
        "referral_code": referral_code,
        "email": (email or "").strip().lower(),
    }
    d2 = schedule_item(kind="free_run_d2", email=email, delay_hours=48, payload=payload)
    d5 = schedule_item(kind="free_run_d5", email=email, delay_hours=120, payload=payload)
    return {"d2": d2, "d5": d5}


def schedule_quota_paywall(
    *,
    email: str,
    research_id: str = "",
    share_url: str = "",
    referral_code: str = "",
) -> Optional[Dict[str, Any]]:
    return schedule_item(
        kind="quota_paywall",
        email=email,
        delay_hours=0,
        payload={
            "research_id": research_id,
            "share_url": share_url,
            "referral_code": referral_code,
            "email": (email or "").strip().lower(),
        },
    )


def due_nurture(now: Optional[datetime] = None, kinds: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    _load()
    now = now or datetime.now(timezone.utc)
    allow = {k.lower() for k in (kinds or [])} if kinds else None
    out: List[Dict[str, Any]] = []
    with _LOCK:
        for item in _ITEMS.values():
            if item.get("status") != "pending":
                continue
            if allow is not None and str(item.get("kind") or "").lower() not in allow:
                continue
            try:
                due = datetime.fromisoformat(str(item.get("due_at") or "").replace("Z", "+00:00"))
            except Exception:
                continue
            if due <= now:
                out.append(deepcopy(item))
    return out


def cancel_free_run_for_email(email: str) -> int:
    """Stop unpaid drips after checkout."""
    email_n = (email or "").strip().lower()
    if not email_n:
        return 0
    _load()
    n = 0
    with _LOCK:
        for item in _ITEMS.values():
            if (
                item.get("email") == email_n
                and item.get("status") == "pending"
                and str(item.get("kind") or "").startswith("free_run")
            ):
                item["status"] = "cancelled"
                item["cancelled_at"] = _iso()
                n += 1
    if n:
        _persist()
    return n
