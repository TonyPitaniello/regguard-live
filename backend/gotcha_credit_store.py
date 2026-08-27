"""Soft credit ledger for Partner-submitted gotchas + approve → account credit."""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from scraper import normalize_us_zip

_BACKEND_DIR = Path(__file__).resolve().parent
_PATH = _BACKEND_DIR / "gotcha_credits.jsonl"
_LOCK = threading.Lock()
CREDIT_USD = 20


def record_pending_credit(
    *,
    email: str,
    zip_code: str,
    note_text: str,
    partner_tier: str = "partner",
) -> Dict[str, Any]:
    email_l = (email or "").strip().lower()
    z = normalize_us_zip(zip_code)
    row = {
        "id": f"gc-{uuid.uuid4().hex[:12]}",
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "pending_review",
        "credit_usd": CREDIT_USD,
        "email": email_l,
        "zip": z,
        "tier": partner_tier,
        "note_preview": (note_text or "")[:160],
    }
    with _LOCK:
        with _PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def recent(limit: int = 50) -> List[Dict[str, Any]]:
    if not _PATH.is_file():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        for line in _PATH.read_text(encoding="utf-8").splitlines()[-500:]:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    return list(reversed(rows[-limit:]))


def _rewrite_all(rows: List[Dict[str, Any]]) -> None:
    with _PATH.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def approve_credit(credit_id: str, *, reviewer: str = "ops") -> Dict[str, Any]:
    """Mark pending credit approved and add account balance."""
    from account_credits import add_credit

    cid = (credit_id or "").strip()
    if not cid:
        raise ValueError("credit_id required")
    with _LOCK:
        rows: List[Dict[str, Any]] = []
        if _PATH.is_file():
            for line in _PATH.read_text(encoding="utf-8").splitlines():
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
        target: Optional[Dict[str, Any]] = None
        for row in rows:
            if str(row.get("id") or "") == cid:
                target = row
                break
        if not target:
            raise ValueError("credit not found")
        if target.get("status") == "approved":
            return target
        if target.get("status") == "rejected":
            raise ValueError("credit was rejected")
        target["status"] = "approved"
        target["reviewed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        target["reviewed_by"] = reviewer
        if not target.get("id"):
            target["id"] = f"gc-{uuid.uuid4().hex[:12]}"
        _rewrite_all(rows)

    add_credit(
        str(target.get("email") or ""),
        float(target.get("credit_usd") or CREDIT_USD),
        reason=f"gotcha_approved:{target.get('id')}:zip:{target.get('zip')}",
    )
    return target


def reject_credit(credit_id: str, *, reviewer: str = "ops") -> Dict[str, Any]:
    cid = (credit_id or "").strip()
    with _LOCK:
        rows: List[Dict[str, Any]] = []
        if _PATH.is_file():
            for line in _PATH.read_text(encoding="utf-8").splitlines():
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
        target = None
        for row in rows:
            if str(row.get("id") or "") == cid:
                target = row
                break
        if not target:
            raise ValueError("credit not found")
        target["status"] = "rejected"
        target["reviewed_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        target["reviewed_by"] = reviewer
        _rewrite_all(rows)
        return target
