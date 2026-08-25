"""Persist Twilio SMS delivery status callbacks (delivered / failed)."""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
_LOCK = threading.Lock()


def _root() -> Path:
    root = Path(os.getenv("REGGUARD_DATA_DIR") or "/tmp/regguard_data")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _path() -> Path:
    return _root() / "sms_delivery_log.jsonl"


def status_callback_url() -> str:
    """Public URL Twilio should POST to — set TWILIO_STATUS_CALLBACK_URL or derive from API base."""
    explicit = (os.getenv("TWILIO_STATUS_CALLBACK_URL") or "").strip()
    if explicit:
        return explicit
    base = (
        os.getenv("REG_GUARD_API_PUBLIC_URL")
        or os.getenv("API_PUBLIC_BASE")
        or os.getenv("RENDER_EXTERNAL_URL")
        or ""
    ).rstrip("/")
    if not base:
        return ""
    return f"{base}/webhooks/twilio/sms-status"


def record_outbound(
    *,
    message_sid: str,
    to_phone: str = "",
    research_id: str = "",
    status: str = "queued",
) -> None:
    if not message_sid:
        return
    row = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event": "outbound",
        "message_sid": message_sid,
        "to": to_phone,
        "research_id": research_id,
        "status": status,
    }
    _append(row)


def record_status_callback(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Twilio posts MessageSid, MessageStatus, ErrorCode, To, From, etc."""
    sid = str(payload.get("MessageSid") or payload.get("SmsSid") or "").strip()
    status = str(payload.get("MessageStatus") or payload.get("SmsStatus") or "").strip().lower()
    err = payload.get("ErrorCode") or payload.get("ErrorCode")
    row = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event": "status",
        "message_sid": sid,
        "status": status,
        "error_code": int(err) if str(err or "").isdigit() else err,
        "to": payload.get("To") or "",
        "from": payload.get("From") or "",
        "raw": {k: payload.get(k) for k in ("MessageStatus", "ErrorCode", "ErrorMessage") if payload.get(k)},
    }
    _append(row)
    logger.info("SMS status sid=%s status=%s err=%s", sid, status, row.get("error_code"))
    return {"status": "ok", "message_sid": sid, "delivery_status": status}


def latest_for_sid(message_sid: str) -> Optional[Dict[str, Any]]:
    sid = (message_sid or "").strip()
    if not sid or not _path().is_file():
        return None
    last = None
    try:
        for line in _path().read_text(encoding="utf-8").splitlines()[-5000:]:
            try:
                row = json.loads(line)
            except Exception:
                continue
            if row.get("message_sid") == sid:
                last = row
    except Exception:
        return None
    return last


def recent(limit: int = 50) -> List[Dict[str, Any]]:
    if not _path().is_file():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        for line in _path().read_text(encoding="utf-8").splitlines()[-2000:]:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    return list(reversed(rows[-limit:]))


def _append(row: Dict[str, Any]) -> None:
    try:
        with _LOCK:
            with _path().open("a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
    except Exception as e:
        logger.warning("sms delivery log append failed: %s", e)
