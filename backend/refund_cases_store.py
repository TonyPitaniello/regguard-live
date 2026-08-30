"""Refund / guarantee cases with optional stamp fingerprint proof."""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_BACKEND = Path(__file__).resolve().parent
_PATH = _BACKEND / "refund_cases.json"
_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load() -> Dict[str, Any]:
    if not _PATH.is_file():
        return {"updated": "", "disclaimer": "", "cases": []}
    try:
        return json.loads(_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"updated": "", "disclaimer": "", "cases": []}


def _save(data: Dict[str, Any]) -> None:
    data["updated"] = _now()[:10]
    _PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_cases() -> Dict[str, Any]:
    return _load()


def record_case_with_stamp(
    *,
    title: str,
    research_id: str = "",
    stamp_snapshot: Optional[Dict[str, Any]] = None,
    what_happened: str = "",
    resolution: str = "",
    status: str = "recorded",
    stripe_refund_id: str = "",
) -> Dict[str, Any]:
    snap = stamp_snapshot if isinstance(stamp_snapshot, dict) else {}
    if research_id and not snap:
        try:
            from research_store import get_research
            from stamp_snapshot import stamp_snapshot as build_snap

            rec = get_research(research_id)
            if rec:
                snap = build_snap(rec.get("analysis") or {})
        except Exception:
            snap = {}
    row = {
        "id": f"case-{uuid.uuid4().hex[:10]}",
        "title": (title or "Stamp / diligence dispute").strip()[:200],
        "status": (status or "recorded")[:40],
        "promise": (
            "If a Critical SOURCE fee/gotcha was wrong vs the official schedule on the "
            "stamp date, we refund that paid run — proof requires stamp fingerprint."
        ),
        "what_happened": (what_happened or "").strip()[:2000],
        "resolution": (resolution or "").strip()[:2000],
        "proof_required": [
            "Official fee schedule URL + archive date",
            "RegGuard receipt with stamp grade + fingerprint",
            "Stripe refund id",
        ],
        "research_id": (research_id or "").strip()[:80],
        "stamp_snapshot": snap,
        "stamp_grade": snap.get("grade"),
        "stamp_fingerprint": snap.get("fingerprint"),
        "stripe_refund_id": (stripe_refund_id or "").strip()[:80],
        "recorded_at": _now(),
    }
    with _LOCK:
        data = _load()
        cases = list(data.get("cases") or [])
        cases.insert(0, row)
        data["cases"] = cases[:100]
        if not data.get("disclaimer"):
            data["disclaimer"] = (
                "Guarantee narratives for trust. Stamp fingerprint freezes the grade "
                "at dispute time. Planning aid only — not a bond or legal opinion."
            )
        _save(data)
    return row
