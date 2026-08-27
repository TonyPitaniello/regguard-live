"""Crowdsourced inspector field notes keyed by U.S. ZIP (Community Scout Moat)."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from scraper import normalize_us_zip

_BACKEND_DIR = Path(__file__).resolve().parent
COMMUNITY_GOTCHAS_PATH = _BACKEND_DIR / "community_gotchas.json"
_FILE_LOCK = threading.Lock()
_MAX_NOTE_LEN = 2000
_MAX_NOTES_PER_ZIP = 50


def _read_store() -> Dict[str, List[Dict[str, Any]]]:
    if not COMMUNITY_GOTCHAS_PATH.is_file():
        return {}
    try:
        with COMMUNITY_GOTCHAS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data  # type: ignore[return-value]


def _write_store(store: Dict[str, List[Dict[str, Any]]]) -> None:
    COMMUNITY_GOTCHAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with COMMUNITY_GOTCHAS_PATH.open("w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def append_note(
    zip_code: str,
    text: str,
    *,
    email: str = "",
    status: str = "published",
    source: str = "community",
) -> Dict[str, Any]:
    """Append one note; raises ValueError on bad input."""
    oz = normalize_us_zip(zip_code)
    t = (text or "").strip()
    if not t:
        raise ValueError("Inspector note text is required.")
    if len(t) > _MAX_NOTE_LEN:
        raise ValueError(f"Inspector note is too long (max {_MAX_NOTE_LEN} characters).")
    note: Dict[str, Any] = {
        "text": t,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": (status or "published").strip().lower(),
        "source": source or "community",
    }
    email_l = (email or "").strip().lower()
    if email_l:
        note["email"] = email_l
    with _FILE_LOCK:
        store = _read_store()
        bucket = store.get(oz)
        if not isinstance(bucket, list):
            bucket = []
        bucket = [*bucket, note]
        store[oz] = bucket[-_MAX_NOTES_PER_ZIP:]
        _write_store(store)
    return note


def list_notes_for_zip(zip_code: str) -> List[Dict[str, Any]]:
    """Return sanitized note dicts for a ZIP (newest last). Skips pending Partner reviews."""
    oz = normalize_us_zip(zip_code)
    with _FILE_LOCK:
        store = _read_store()
    raw_list = store.get(oz)
    if not isinstance(raw_list, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        if str(item.get("status") or "published").lower() == "pending_review":
            continue
        t = str(item.get("text") or "").strip()
        if not t:
            continue
        out.append({"text": t, "created_at": str(item.get("created_at") or "")})
    return out
