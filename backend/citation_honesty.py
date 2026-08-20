"""Citation honesty: SOURCE (parcel/scout verified) vs LINK (portal URL) vs Unverified."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def citation_tier_for(item: Optional[Dict[str, Any]]) -> str:
    """
    verified — site/scout confirmed claim with URL
    link — catalog / portal URL present but not parcel-verified
    unverified — no defendable URL
    """
    if not isinstance(item, dict):
        return "unverified"
    explicit = str(item.get("citation_tier") or "").strip().lower()
    if explicit in ("verified", "link", "unverified", "source"):
        return "verified" if explicit == "source" else explicit

    url = str(item.get("source_url") or "").strip()
    if not url.lower().startswith("http"):
        return "unverified"

    layer = str(item.get("jurisdiction_layer") or item.get("layer") or "").lower()
    if layer in ("federal", "state", "state_pack", "portal", "catalog"):
        return "link"

    task = str(item.get("task") or item.get("title") or "")
    if task.startswith("[Federal]") or task.startswith("[State]"):
        return "link"

    if item.get("verified") is True:
        return "verified"
    return "link"


def citation_badge_label(tier: str) -> str:
    t = (tier or "").lower()
    if t == "verified":
        return "SOURCE"
    if t == "link":
        return "LINK"
    return "UNVERIFIED"


def apply_citation_honesty(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Stamp citation_tier on punch + margin killers; demote portal 'verified' theater."""
    if not isinstance(analysis, dict):
        return analysis

    punch = dict(analysis.get("punch_list") or {})
    items: List[Any] = list(punch.get("punch_list") or [])
    cleaned_items = []
    for it in items:
        if not isinstance(it, dict):
            cleaned_items.append(it)
            continue
        row = dict(it)
        tier = citation_tier_for(row)
        row["citation_tier"] = tier
        if tier == "link":
            row["verified"] = False
            if not row.get("source_label") or str(row.get("source_label")).lower() in (
                "source",
                "verified",
            ):
                row["source_label"] = "Portal link"
        elif tier == "verified":
            row["verified"] = True
            row.setdefault("source_label", "Source")
        else:
            row["verified"] = False
            row.setdefault("source_label", "Unverified")
        cleaned_items.append(row)
    punch["punch_list"] = cleaned_items
    analysis["punch_list"] = punch

    killers = analysis.get("margin_killers")
    if isinstance(killers, list):
        out_k = []
        for k in killers:
            if not isinstance(k, dict):
                out_k.append(k)
                continue
            row = dict(k)
            tier = citation_tier_for(row)
            row["citation_tier"] = tier
            if tier == "link":
                row["verified"] = False
                row["source_label"] = row.get("source_label") or "Portal link"
            elif tier == "verified":
                row["verified"] = True
                row["source_label"] = row.get("source_label") or "Source"
            else:
                row["verified"] = False
                row["source_label"] = "Unverified"
            out_k.append(row)
        analysis["margin_killers"] = out_k

    return analysis
