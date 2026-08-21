"""
Align email + PDF deliverables with on-screen analysis.

Call prepare_analysis_for_delivery() before generating bid packets, IC PDFs,
or research-result emails so punch rank, citation honesty, and address
normalization match the app.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def prepare_analysis_for_delivery(analysis: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Return a copy of analysis shaped for contractor-facing delivery."""
    if not isinstance(analysis, dict):
        return {}

    out = dict(analysis)

    try:
        from site_address import clean_project_info_address

        out = clean_project_info_address(out)
    except Exception:
        pass

    try:
        from punch_rank import normalize_analysis_punch

        out = normalize_analysis_punch(out)
    except Exception:
        pass

    try:
        from citation_honesty import apply_citation_honesty

        out = apply_citation_honesty(out)
    except Exception:
        pass

    try:
        band = out.get("contingency_band") or {}
        if band.get("pct_low") is None or not out.get("margin_killers"):
            from arbitrage_enrichment import enrich_analysis_with_arbitrage

            out = enrich_analysis_with_arbitrage(out)
    except Exception:
        pass

    return out


def citation_label_for_item(item: Dict[str, Any]) -> str:
    try:
        from citation_honesty import citation_badge_label, citation_tier_for

        return citation_badge_label(citation_tier_for(item))
    except Exception:
        if item.get("verified") and item.get("source_url"):
            return "SOURCE"
        return "UNVERIFIED"
