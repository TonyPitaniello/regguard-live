"""
Free scan quota — 2–3 free FinOps lookups per email per calendar month.

The count is mirrored onto one non-customer orders row per month so a Render
disk wipe cannot hand the same email a fresh allowance. The cap itself does
not change. That row is not an order and cannot grant a paid desk.
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
_ARCHIVE_EMAIL = "quota-archive@regguard.invalid"
# None until a durable read or write has been attempted this process.
_durable_ok: Optional[bool] = None


def data_dir_is_ephemeral() -> bool:
    raw = (os.getenv("REGGUARD_DATA_DIR") or "/tmp/regguard_data").strip()
    return raw.startswith("/tmp") or raw.startswith("/var/tmp")


def quota_store_status() -> Dict[str, Any]:
    """No emails and no counts. Safe for the public health probe."""
    configured = bool(
        (os.getenv("SUPABASE_URL") or "").strip() and (os.getenv("SUPABASE_KEY") or "").strip()
    )
    return {
        "backend": "supabase" if configured else "disk",
        "last_durable_ok": _durable_ok,
    }


def _session_id(month: str) -> str:
    return f"quota_{month}"


def _mark_durable(ok: Optional[bool]) -> None:
    global _durable_ok
    _durable_ok = ok


def _durable_load(month: str) -> Optional[Dict[str, int]]:
    """None when the durable store cannot be read. Empty when the month row is absent."""
    try:
        from urllib.parse import quote

        from order_service import _supabase_rest
    except Exception as e:
        logger.warning("Quota durable import failed: %s", e)
        _mark_durable(False)
        return None
    rows = _supabase_rest(
        f"orders?stripe_session_id=eq.{quote(_session_id(month), safe='-_')}&select=analysis_json&limit=1",
        method="GET",
    )
    if rows is None:
        _mark_durable(False)
        return None
    _mark_durable(True)
    if not rows or not isinstance(rows[0], dict):
        return {}
    stored = rows[0].get("analysis_json")
    counts = stored.get("counts") if isinstance(stored, dict) else None
    if not isinstance(counts, dict):
        return {}
    out: Dict[str, int] = {}
    for key, value in counts.items():
        email = _norm_email(str(key))
        if not email:
            continue
        try:
            out[email] = max(0, int(value))
        except (TypeError, ValueError):
            continue
    return out


def _durable_save(month: str, counts: Dict[str, int]) -> bool:
    try:
        from urllib.parse import quote

        from order_service import _supabase_rest, email_to_user_uuid
    except Exception as e:
        logger.warning("Quota durable import failed: %s", e)
        _mark_durable(False)
        return False
    sid = _session_id(month)
    body = {
        "analysis_json": {"counts": counts, "kind": "free_scan_quota"},
        "email": _ARCHIVE_EMAIL,
        "tier": "free",
        "amount": 0,
        "status": "completed",
        "pdf_status": "quota",
        "address": "",
    }
    existing = _supabase_rest(
        f"orders?stripe_session_id=eq.{quote(sid, safe='-_')}&select=id&limit=1",
        method="GET",
    )
    if existing is None:
        _mark_durable(False)
        return False
    if existing:
        result = _supabase_rest(
            f"orders?stripe_session_id=eq.{quote(sid, safe='-_')}",
            method="PATCH",
            json_body=body,
            prefer="return=minimal",
        )
        ok = result is not None
        _mark_durable(ok)
        return ok
    row = {
        **body,
        "user_id": email_to_user_uuid(_ARCHIVE_EMAIL),
        "stripe_session_id": sid,
        "currency": "usd",
        "project_type": "commercial",
    }
    result = _supabase_rest("orders", method="POST", json_body=row, prefer="return=minimal")
    ok = result is not None
    _mark_durable(ok)
    return ok


def _merged_used(local_used: int, durable: Optional[Dict[str, int]], email: str) -> int:
    if not durable:
        return local_used
    return max(local_used, int(durable.get(email) or 0))


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
    durable = _durable_load(mk)
    with _LOCK:
        data = _load()
        months = data.setdefault("months", {})
        bucket = months.setdefault(mk, {})
        used = _merged_used(int(bucket.get(em) or 0), durable, em)
        if used != int(bucket.get(em) or 0):
            bucket[em] = used
            _save(data)
    if durable is not None and int(durable.get(em) or 0) < used:
        durable[em] = used
        _durable_save(mk, durable)
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

    durable = _durable_load(mk)
    with _LOCK:
        data = _load()
        months = data.setdefault("months", {})
        # Drop old months (keep current only) to bound file size
        data["months"] = {mk: months.get(mk) or {}}
        bucket = data["months"][mk]
        used = _merged_used(int(bucket.get(em) or 0), durable, em)
        if used >= limit:
            bucket[em] = used
            _save(data)
            usage = {
                "email": em,
                "month": mk,
                "used": used,
                "limit": limit,
                "remaining": 0,
                "allowed": False,
            }
        else:
            used = used + 1
            bucket[em] = used
            _save(data)
            usage = {
                "email": em,
                "month": mk,
                "used": used,
                "limit": limit,
                "remaining": max(0, limit - used),
                "allowed": True,
            }
    if durable is not None:
        durable[em] = used
        _durable_save(mk, durable)
    return bool(usage["allowed"]), usage
