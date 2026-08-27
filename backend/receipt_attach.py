"""Receipt attach metadata for Procore / bid-software style integrations."""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_BACKEND = Path(__file__).resolve().parent
_PATH = _BACKEND / "data" / "receipt_attachments.json"
_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load() -> Dict[str, Any]:
    if not _PATH.is_file():
        return {"attachments": []}
    try:
        return json.loads(_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"attachments": []}


def _save(data: Dict[str, Any]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def attach_receipt(
    *,
    research_id: str,
    external_system: str,
    external_project_id: str,
    share_url: str = "",
    note: str = "",
    requester_email: str = "",
) -> Dict[str, Any]:
    rid = (research_id or "").strip()
    system = (external_system or "").strip().lower()[:40] or "generic"
    proj = (external_project_id or "").strip()[:120]
    if not rid:
        raise ValueError("research_id required")
    if not proj:
        raise ValueError("external_project_id required")
    row = {
        "id": f"att-{uuid.uuid4().hex[:10]}",
        "ts": _now(),
        "research_id": rid,
        "external_system": system,
        "external_project_id": proj,
        "share_url": (share_url or "")[:400],
        "note": (note or "")[:400],
        "requester_email": (requester_email or "").strip().lower()[:120],
        "status": "recorded",
        "hint": (
            "RegGuard records the attach intent. Push into Procore/Autodesk via "
            "your integration using share_url + diligence-export JSON."
        ),
    }
    with _LOCK:
        data = _load()
        atts = list(data.get("attachments") or [])
        atts.append(row)
        data["attachments"] = atts[-500:]
        _save(data)
    return row


def list_attachments(research_id: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = list(_load().get("attachments") or [])
    if research_id:
        rid = research_id.strip()
        return [r for r in rows if r.get("research_id") == rid]
    return rows
