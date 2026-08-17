"""
Depth ladder + upgrade offers for Free → Pro light → IC full.

Attaches ``upgrade_offer`` and ``depth_tier`` so the UI can show
"Upgrade for fuller, more in-depth results" at every layer.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


DEPTH_FREE = "free"
DEPTH_PRO_LOCAL = "pro_local"
DEPTH_PRO_LIGHT = "pro_light"
DEPTH_PRO_PARTIAL = "pro_partial"
DEPTH_IC_FULL = "ic_full"


def stamp_upgrade_offer(
    analysis: Dict[str, Any],
    *,
    depth_tier: str,
    ic_pending: bool = False,
) -> Dict[str, Any]:
    """Mutate analysis with depth_tier + upgrade_offer for the next paid layer."""
    if not isinstance(analysis, dict):
        return analysis

    tier = (depth_tier or DEPTH_FREE).strip().lower()
    analysis["depth_tier"] = tier

    if tier == DEPTH_FREE:
        analysis["upgrade_offer"] = {
            "message": "Upgrade for fuller, more in-depth results",
            "detail": (
                "Free shows a Bid Risk preview. Contractor Pro adds bounded local fee confirm "
                "plus light federal/state/local scout — metered for bid week."
            ),
            "cta_label": "Upgrade to Contractor Pro — $149/mo",
            "cta_tier": "contractor_pro",
            "secondary_cta_label": "IC Project Report — $1,500",
            "secondary_cta_tier": "ic_project",
            "current_label": "Free preview",
            "next_label": "Pro deepen (local + light scout)",
        }
    elif tier in (DEPTH_PRO_LOCAL, DEPTH_PRO_PARTIAL):
        analysis["upgrade_offer"] = {
            "message": "Upgrade for fuller, more in-depth results",
            "detail": (
                "This run used paid local confirm"
                + (" (partial / timed out)" if tier == DEPTH_PRO_PARTIAL else "")
                + ". IC Project adds full Universal Scout (federal + state + local passes) "
                "and three downloadable PDFs for this site."
            ),
            "cta_label": "Get IC Project Report — $1,500",
            "cta_tier": "ic_project",
            "secondary_cta_label": None,
            "secondary_cta_tier": None,
            "current_label": "Pro local confirm",
            "next_label": "IC full scout + PDFs",
        }
    elif tier == DEPTH_PRO_LIGHT:
        analysis["upgrade_offer"] = {
            "message": "Upgrade for fuller, more in-depth results",
            "detail": (
                "Pro light scout covered core AHJ / permits / codes. "
                "IC Project runs the full Universal Scout (FAST-41, vertical passes when relevant) "
                "and delivers Research Memo, Punch List, and Permit Package PDFs."
            ),
            "cta_label": "Get IC Project Report — $1,500",
            "cta_tier": "ic_project",
            "secondary_cta_label": None,
            "secondary_cta_tier": None,
            "current_label": "Pro light scout",
            "next_label": "IC full scout + PDFs",
        }
    elif tier == DEPTH_IC_FULL:
        analysis["upgrade_offer"] = {
            "message": "Need another site’s full package?",
            "detail": (
                "This IC depth is the fullest Reg Guard run for one bound site. "
                "Buy another IC Project Report for a new address, or use IC Annual after your first project."
            ),
            "cta_label": "IC Project for another site — $1,500",
            "cta_tier": "ic_project",
            "secondary_cta_label": "IC Annual — $15,000/yr",
            "secondary_cta_tier": "ic_annual",
            "current_label": "IC full depth",
            "next_label": None,
        }
    else:
        analysis["upgrade_offer"] = {
            "message": "Upgrade for fuller, more in-depth results",
            "detail": "Choose Contractor Pro for metered deepen or IC Project for full scout + PDFs.",
            "cta_label": "Upgrade to Contractor Pro — $149/mo",
            "cta_tier": "contractor_pro",
            "secondary_cta_label": "IC Project Report — $1,500",
            "secondary_cta_tier": "ic_project",
            "current_label": "Current results",
            "next_label": "Deeper paid research",
        }

    if ic_pending and tier.startswith("pro"):
        offer = dict(analysis["upgrade_offer"])
        offer["detail"] = (
            (offer.get("detail") or "")
            + " Your IC purchase can generate PDFs — confirm Generate IC Report on the next run."
        )
        analysis["upgrade_offer"] = offer

    return analysis


def infer_depth_tier(
    analysis: Optional[Dict[str, Any]],
    *,
    paid: bool = False,
    force_scout: bool = False,
    scout_mode: str = "",
) -> str:
    if not isinstance(analysis, dict):
        return DEPTH_FREE
    explicit = str(analysis.get("depth_tier") or "").strip().lower()
    if explicit in (
        DEPTH_FREE,
        DEPTH_PRO_LOCAL,
        DEPTH_PRO_LIGHT,
        DEPTH_PRO_PARTIAL,
        DEPTH_IC_FULL,
    ):
        return explicit
    mode = (scout_mode or analysis.get("scout_mode") or "").strip().lower()
    depth = str(analysis.get("research_depth") or "").strip().lower()
    if force_scout or mode == "full" or analysis.get("ic_package"):
        return DEPTH_IC_FULL
    if mode == "light":
        return DEPTH_PRO_LIGHT
    if depth == "pro_partial":
        return DEPTH_PRO_PARTIAL
    if paid or depth == "pro":
        return DEPTH_PRO_LOCAL
    return DEPTH_FREE
