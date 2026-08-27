"""Soft credit ledger for Partner-submitted gotchas (ops honors manually)."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

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
