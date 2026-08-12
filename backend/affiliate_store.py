"""
Lightweight affiliate / referral ledger.
File-backed (and optional Supabase) so checkout ?ref= codes can earn commission.
Admin marks commissions paid via ADMIN_SECRET-protected endpoints.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_AFFILIATES: Dict[str, Dict[str, Any]] = {}  # code -> affiliate
_COMMISSIONS: List[Dict[str, Any]] = []

_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{2,31}$")
DEFAULT_COMMISSION_RATE = 0.20  # 20% of order amount


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _store_dir() -> Path:
    root = Path(os.getenv("REGGUARD_DATA_DIR") or "/tmp/regguard_data")
    d = root / "affiliates"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _affiliates_path() -> Path:
    return _store_dir() / "affiliates.json"


def _commissions_path() -> Path:
    return _store_dir() / "commissions.json"


def _load() -> None:
    global _AFFILIATES, _COMMISSIONS
    with _LOCK:
        if _AFFILIATES:
            return
        try:
            if _affiliates_path().exists():
                _AFFILIATES = json.loads(_affiliates_path().read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("affiliate load failed: %s", e)
            _AFFILIATES = {}
        try:
            if _commissions_path().exists():
                _COMMISSIONS = json.loads(_commissions_path().read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("commission load failed: %s", e)
            _COMMISSIONS = []


def _persist() -> None:
    with _LOCK:
        try:
            _affiliates_path().write_text(
                json.dumps(_AFFILIATES, indent=2), encoding="utf-8"
            )
            _commissions_path().write_text(
                json.dumps(_COMMISSIONS, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.warning("affiliate persist failed: %s", e)


def normalize_code(code: Optional[str]) -> str:
    return (code or "").strip().lower()


def register_affiliate(
    *,
    email: str,
    name: str = "",
    code: Optional[str] = None,
) -> Dict[str, Any]:
    _load()
    email_n = (email or "").strip().lower()
    if not email_n or "@" not in email_n:
        raise ValueError("Valid email is required")

    raw = normalize_code(code) if code else ""
    if not raw:
        base = re.sub(r"[^a-z0-9]", "", email_n.split("@")[0].lower())[:12] or "partner"
        raw = f"{base}{uuid.uuid4().hex[:4]}"
    if not _CODE_RE.match(raw):
        raise ValueError(
            "Referral code must be 3–32 chars: lowercase letters, numbers, _ or -"
        )

    with _LOCK:
        if raw in _AFFILIATES:
            existing = _AFFILIATES[raw]
            if existing.get("email") != email_n:
                raise ValueError("Referral code already taken")
            return deepcopy(existing)
        # One active code per email
        for a in _AFFILIATES.values():
            if a.get("email") == email_n:
                return deepcopy(a)

        aff = {
            "code": raw,
            "email": email_n,
            "name": (name or "").strip(),
            "commission_rate": DEFAULT_COMMISSION_RATE,
            "created_at": _iso(),
            "active": True,
        }
        _AFFILIATES[raw] = aff
    _persist()
    logger.info("Registered affiliate code=%s email=%s", raw, email_n)
    return deepcopy(aff)


def get_affiliate(code: Optional[str]) -> Optional[Dict[str, Any]]:
    _load()
    c = normalize_code(code)
    if not c:
        return None
    with _LOCK:
        a = _AFFILIATES.get(c)
        return deepcopy(a) if a and a.get("active") else None


def record_click(code: Optional[str]) -> bool:
    aff = get_affiliate(code)
    if not aff:
        return False
    _load()
    with _LOCK:
        a = _AFFILIATES.get(aff["code"])
        if not a:
            return False
        a["clicks"] = int(a.get("clicks") or 0) + 1
        a["last_click_at"] = _iso()
    _persist()
    return True


def attribute_sale(
    *,
    referral_code: Optional[str],
    order_id: str,
    customer_email: str,
    amount_cents: int,
    tier: str,
) -> Optional[Dict[str, Any]]:
    """Create a commission row when a checkout has referral_code metadata."""
    aff = get_affiliate(referral_code)
    if not aff:
        return None
    cust = (customer_email or "").strip().lower()
    if cust and cust == aff.get("email"):
        logger.info("Skip self-referral for %s", cust)
        return None

    _load()
    with _LOCK:
        for c in _COMMISSIONS:
            if c.get("order_id") == order_id:
                return deepcopy(c)
        # First paid order only per referred customer (not recurring / repeat checkouts)
        if cust:
            for c in _COMMISSIONS:
                if (c.get("customer_email") or "").strip().lower() == cust:
                    logger.info("Skip affiliate — customer %s already attributed once", cust)
                    return None

        rate = float(aff.get("commission_rate") or DEFAULT_COMMISSION_RATE)
        amount = max(0, int(amount_cents or 0))
        commission_cents = int(round(amount * rate))
        row = {
            "id": uuid.uuid4().hex,
            "affiliate_code": aff["code"],
            "affiliate_email": aff["email"],
            "order_id": order_id,
            "customer_email": cust,
            "tier": (tier or "").strip().lower(),
            "sale_amount_cents": amount,
            "commission_cents": commission_cents,
            "commission_rate": rate,
            "paid": False,
            "created_at": _iso(),
            "paid_at": None,
        }
        _COMMISSIONS.append(row)
    _persist()
    logger.info(
        "Affiliate commission %s code=%s order=%s cents=%s",
        row["id"],
        aff["code"],
        order_id,
        commission_cents,
    )
    return deepcopy(row)


def list_affiliates() -> List[Dict[str, Any]]:
    _load()
    with _LOCK:
        return [deepcopy(a) for a in _AFFILIATES.values()]


def list_commissions(*, unpaid_only: bool = False) -> List[Dict[str, Any]]:
    _load()
    with _LOCK:
        rows = list(_COMMISSIONS)
    if unpaid_only:
        rows = [r for r in rows if not r.get("paid")]
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return [deepcopy(r) for r in rows]


def mark_commission_paid(commission_id: str) -> Optional[Dict[str, Any]]:
    _load()
    cid = (commission_id or "").strip()
    with _LOCK:
        for row in _COMMISSIONS:
            if row.get("id") == cid:
                row["paid"] = True
                row["paid_at"] = _iso()
                out = deepcopy(row)
                break
        else:
            return None
    _persist()
    return out


def frontend_referral_url(code: str) -> str:
    base = (
        os.getenv("FRONTEND_APP_URL")
        or os.getenv("FRONTEND_URL")
        or "https://app.regguardagent.com"
    ).rstrip("/")
    return f"{base}/?ref={normalize_code(code)}"
