"""Product event instrumentation — stamp funnel + zip-watch re-run (72h)."""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_BACKEND = Path(__file__).resolve().parent
_PATH = _BACKEND / "data" / "product_events.jsonl"
_LOCK = threading.Lock()

ALLOWED_EVENTS = frozenset(
    {
        "stamp_share_copy",
        "stamp_share_whatsapp",
        "stamp_share_facebook",
        "stamp_receipt_download",
        "stamp_packet_download",
        "stamp_view",
        "zip_watch_alert_sent",
        "zip_watch_sms_sent",
        "research_rerun_same_zip",
        "partner_mandate_copy",
        "partner_mandate_outreach_logged",
        "job_saved_with_phone",
        "war_room_stamp_attached",
        "refund_case_stamp_attached",
    }
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime] = None) -> str:
    d = dt or _utcnow()
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def track_event(
    event: str,
    *,
    research_id: str = "",
    zip_code: str = "",
    stamp_grade: str = "",
    stamp_fingerprint: str = "",
    channel: str = "",
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    name = (event or "").strip()
    if name not in ALLOWED_EVENTS:
        raise ValueError(f"Unknown event: {name}")
    row: Dict[str, Any] = {
        "ts": _iso(),
        "event": name,
        "research_id": (research_id or "")[:80],
        "zip": str(zip_code or "")[:10],
        "stamp_grade": str(stamp_grade or "")[:16],
        "stamp_fingerprint": str(stamp_fingerprint or "")[:40],
        "channel": str(channel or "")[:40],
        "meta": meta or {},
    }
    try:
        with _LOCK:
            _PATH.parent.mkdir(parents=True, exist_ok=True)
            with _PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("product_events append failed: %s", e)
    return row


def _read_rows(limit: int = 5000) -> List[Dict[str, Any]]:
    if not _PATH.is_file():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        lines = _PATH.read_text(encoding="utf-8").splitlines()[-limit:]
        for line in lines:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    return rows


def recent(limit: int = 50) -> List[Dict[str, Any]]:
    rows = _read_rows(3000)
    return list(reversed(rows[-limit:]))


def stamp_funnel_stats(*, hours: int = 168) -> Dict[str, Any]:
    """Counts by event + zip-watch → re-run within 72h conversion."""
    cutoff = _utcnow() - timedelta(hours=max(1, hours))
    rows = _read_rows(8000)
    counts: Dict[str, int] = {}
    alerts: List[Dict[str, Any]] = []
    reruns: List[Dict[str, Any]] = []

    def _parse_ts(s: str) -> Optional[datetime]:
        try:
            return datetime.strptime(str(s).replace("Z", ""), "%Y-%m-%dT%H:%M:%S").replace(
                tzinfo=timezone.utc
            )
        except Exception:
            return None

    for r in rows:
        ts = _parse_ts(r.get("ts") or "")
        if not ts or ts < cutoff:
            continue
        ev = r.get("event") or ""
        counts[ev] = counts.get(ev, 0) + 1
        if ev in ("zip_watch_alert_sent", "zip_watch_sms_sent"):
            alerts.append(r)
        if ev == "research_rerun_same_zip":
            reruns.append(r)

    converted = 0
    window = timedelta(hours=72)
    for a in alerts:
        z = str(a.get("zip") or "")
        ats = _parse_ts(a.get("ts") or "")
        if not z or not ats:
            continue
        for rr in reruns:
            if str(rr.get("zip") or "") != z:
                continue
            rts = _parse_ts(rr.get("ts") or "")
            if rts and ats <= rts <= ats + window:
                converted += 1
                break

    alert_n = len(alerts)
    return {
        "window_hours": hours,
        "counts": counts,
        "zip_watch_alerts": alert_n,
        "reruns_same_zip": len(reruns),
        "rerun_within_72h": converted,
        "rerun_within_72h_rate": round(converted / alert_n, 3) if alert_n else None,
        "disclaimer": "Planning metrics only — not billing or legal evidence.",
    }
