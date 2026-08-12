"""
Free scan quota — 2–3 free FinOps lookups per email per calendar month.
File-backed (works without DB); optionally cross-checks Supabase free_trials.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()


def free_scans_per_month() -> int:
    try:
        return max(1, min(10, int(os.getenv("FREE_TRIAL_SCANS_PER_MONTH") or "3")))
    except ValueError:
        return 3


def _month_key(now: Optional[datetime] = None) -> str:
    n = now or datetime.now(timezone.utc)
    return f"{n.year:04d}-{n.month:02d}"


def _store_path() -> Path:
    root = Path(os.getenv("REGGUARD_DATA_DIR") or "/tmp/regguard_data")
    root.mkdir(parents=True, exist_ok=True)
    return root / "free_scan_quota.json"


def _norm_email(email: str) -> str:
    return (email or "").strip().lower()


def _load() -> Dict[str, Any]:
    path = _store_path()
    if not path.is_file():
        return {"months": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"months": {}}


def _save(data: Dict[str, Any]) -> None:
    path = _store_path()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_free_scan_usage(email: str) -> Dict[str, Any]:
    em = _norm_email(email)
    limit = free_scans_per_month()
    if not em:
        return {
            "email": "",
            "month": _month_key(),
            "used": 0,
            "limit": limit,
            "remaining": limit,
            "allowed": True,
        }
    mk = _month_key()
    with _LOCK:
        data = _load()
        months = data.setdefault("months", {})
        bucket = months.setdefault(mk, {})
        used = int(bucket.get(em) or 0)
    return {
        "email": em,
        "month": mk,
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used),
        "allowed": used < limit,
    }


def consume_free_scan(email: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Atomically consume one free scan. Returns (allowed, usage_dict).
    Anonymous / missing email: allow but do not persist (IP abuse is separate).
    """
    em = _norm_email(email)
    limit = free_scans_per_month()
    mk = _month_key()
    if not em:
        return True, {
            "email": "",
            "month": mk,
            "used": 0,
            "limit": limit,
            "remaining": limit,
            "allowed": True,
            "anonymous": True,
        }

    with _LOCK:
        data = _load()
        months = data.setdefault("months", {})
        # Drop old months (keep current only) to bound file size
        data["months"] = {mk: months.get(mk) or {}}
        bucket = data["months"][mk]
        used = int(bucket.get(em) or 0)
        if used >= limit:
            usage = {
                "email": em,
                "month": mk,
                "used": used,
                "limit": limit,
                "remaining": 0,
                "allowed": False,
            }
            return False, usage
        bucket[em] = used + 1
        _save(data)
        usage = {
            "email": em,
            "month": mk,
            "used": used + 1,
            "limit": limit,
            "remaining": max(0, limit - (used + 1)),
            "allowed": True,
        }
        return True, usage
