"""Stamp snapshot helpers for war room / refund / receipt attach proof."""
from __future__ import annotations

from typing import Any, Dict, Optional


def stamp_snapshot(analysis: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Freeze stamp fields at attach/purchase/war-room time for dispute proof."""
    a = analysis if isinstance(analysis, dict) else {}
    rg = a.get("regguard_stamp") if isinstance(a.get("regguard_stamp"), dict) else {}
    pi = a.get("project_info") if isinstance(a.get("project_info"), dict) else {}
    return {
        "schema": "regguard.stamp_snapshot.v1",
        "grade": rg.get("grade") or a.get("stamp_grade"),
        "label": rg.get("label") or a.get("stamp_label"),
        "fingerprint": rg.get("fingerprint") or a.get("stamp_fingerprint"),
        "valid_until": rg.get("valid_until") or a.get("stamp_valid_until"),
        "stamped_at": rg.get("stamped_at"),
        "is_stale": bool(rg.get("is_stale")),
        "stale_reason": rg.get("stale_reason") or "",
        "drivers": list(rg.get("drivers") or [])[:3],
        "disclaimer": rg.get("disclaimer")
        or (
            "Planning aid only. Not a bond, insurance quote, legal opinion, "
            "or interconnection study."
        ),
        "site": {
            "address": pi.get("address"),
            "city": pi.get("city"),
            "state": pi.get("state"),
            "zip": pi.get("zip"),
        },
        "research_id": a.get("research_id"),
    }
