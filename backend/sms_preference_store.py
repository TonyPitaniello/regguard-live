"""SMS preference store — optional consent; never required for service use."""
from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_BACKEND = Path(__file__).resolve().parent
_PATH = _BACKEND / "data" / "sms_preferences.jsonl"
_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record_preference(
    *,
    research_id: str = "",
    phone_number: str = "",
    consent: bool,
    user_id: str = "",
    source: str = "results",
) -> Dict[str, Any]:
    rid = (research_id or "").strip()[:80]
    phone = (phone_number or "").strip()[:40]
    row = {
        "id": f"sp-{uuid.uuid4().hex[:10]}",
        "ts": _now(),
        "research_id": rid,
        "phone": phone,
        "consent": bool(consent),
        "user_id": (user_id or "")[:80],
        "source": (source or "")[:60],
        "status": "recorded",
    }
    with _LOCK:
        _PATH.parent.mkdir(parents=True, exist_ok=True)
        with _PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def latest_for_research(research_id: str) -> Optional[Dict[str, Any]]:
    rid = (research_id or "").strip()
    if not rid:
        return None
    try:
        for line in reversed(_PATH.read_text(encoding="utf-8").splitlines()[-500:]):
            try:
                row = json.loads(line)
            except Exception:
                continue
            if row.get("research_id") == rid:
                return row
    except Exception:
        return None
    return None


def list_recent(limit: int = 50) -> List[Dict[str, Any]]:
    if not _PATH.is_file():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        for line in _PATH.read_text(encoding="utf-8").splitlines()[-2000:]:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    return list(reversed(rows[-limit:]))


def has_consent(phone_number: str = "") -> bool:
    """True if any recorded preference for this phone is true."""
    if not phone_number.strip():
        return False
    for row in list_recent(200):
        if str(row.get("phone") or "") == phone_number.strip():
            if row.get("consent"):
                return True
    return False