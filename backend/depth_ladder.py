"""
Depth ladder + persona-aware upgrade offers + Pro uniqueness delta.

Decisive fixes for desire premortem:
  F1 — one primary upgrade offer (UI shows it once)
  F2 — ``pro_delta`` proves what Pro added vs Free
  F4 — data-center / infra personas get IC+PDF pitch, not vague “fuller”
  F8 — never imply “more accurate”; sell citeable sources + PDFs
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


DEPTH_FREE = "free"
DEPTH_PRO_LOCAL = "pro_local"
DEPTH_PRO_LIGHT = "pro_light"
DEPTH_PRO_PARTIAL = "pro_partial"
DEPTH_IC_FULL = "ic_full"

# Personas for CTA split
PERSONA_BID_DESK = "bid_desk"  # GC / electrical / commercial habit → Pro
PERSONA_DC_INFRA = "dc_infra"  # data-center / utility / renewable → IC PDFs
PERSONA_IC_SHOP = "ic_shop"  # interconnection consult packaging → IC


def infer_persona(analysis: Optional[Dict[str, Any]]) -> str:
    """Map project type → buyer persona for CTA copy."""
    if not isinstance(analysis, dict):
        return PERSONA_BID_DESK
    pi = analysis.get("project_info") or {}
    raw = str(
        pi.get("type")
        or analysis.get("project_type")
        or ""
    ).strip().lower().replace("_", "-")
    if raw in ("data-center", "datacenter", "data_center"):
        return PERSONA_DC_INFRA
    if raw in ("renewable", "utility", "industrial"):
        return PERSONA_DC_INFRA
    if raw in ("interconnect", "interconnection", "ic"):
        return PERSONA_IC_SHOP
    return PERSONA_BID_DESK


def _project_type_label(analysis: Dict[str, Any]) -> str:
    pi = analysis.get("project_info") or {}
    return str(pi.get("type") or "commercial").replace("-", " ")


def stamp_pro_delta(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prove Pro uniqueness vs Free (F2).
    Counts paid-local pages, new scout URLs, fee rows — shown in UI as “What Pro added”.
    """
    if not isinstance(analysis, dict):
        return analysis

    pl = analysis.get("paid_local") or {}
    pages = int(pl.get("pages_scraped") or 0)
    if not pages and isinstance(pl.get("pages_cap"), int):
        # cache hit may omit scraped count — still note confirm method
        pages = 0
    fee_n = int(pl.get("fee_rows_extracted") or 0)
    if not fee_n:
        fee_n = len(((analysis.get("fee_card") or {}).get("fees") or []))

    sources = list(analysis.get("pro_source_urls") or [])
    punch = (analysis.get("punch_list") or {}).get("punch_list") or []
    verified_punch = sum(
        1
        for i in punch
        if isinstance(i, dict) and i.get("verified") and i.get("source_url")
    )

    bullets: List[str] = []
    method = str(pl.get("method") or pl.get("status") or "")
    if pl.get("cache_hit") or "cache" in method.lower():
        bullets.append("Reused a cached AHJ confirm for this jurisdiction (faster, same citeable pages).")
    elif pages > 0:
        bullets.append(f"Confirmed up to {pages} official AHJ page(s) beyond the free city pack.")
    elif pl.get("status") == "ok":
        bullets.append("Ran paid local AHJ confirm (portal / schedule pages) beyond the free pack.")

    if fee_n > 0:
        bullets.append(
            f"Extracted {fee_n} fee/timeline line(s) as planning aids — confirm on the official schedule."
        )
    if sources:
        bullets.append(f"Attached {len(sources)} scout source link(s) Free preview does not run.")
    if verified_punch > 0:
        bullets.append(f"Marked {verified_punch} punch-list line(s) with citeable Source links.")

    scout_mode = str(analysis.get("scout_mode") or "").lower()
    if scout_mode == "light":
        bullets.append(
            "Pro light scout: AHJ / building permits / adopted codes (3 passes). "
            "Not full federal/vertical depth — that is IC."
        )
    elif scout_mode == "full":
        bullets.append("Full Universal Scout passes ran for this site (IC-depth research).")

    if not bullets:
        bullets.append(
            "Paid deepen ran on this email. If this looks thin, the AHJ may be portal-only — "
            "try IC for a full scout + PDF package."
        )

    analysis["pro_delta"] = {
        "title": "What Pro added vs Free",
        "bullets": bullets[:6],
        "pages_scraped": pages,
        "fee_rows": fee_n,
        "scout_sources": len(sources),
        "verified_punch_lines": verified_punch,
        "scout_mode": scout_mode or "none",
        "honesty": (
            "More sources and deeper scout — not a guarantee fees match the live AHJ schedule."
        ),
    }
    return analysis


def stamp_upgrade_offer(
    analysis: Dict[str, Any],
    *,
    depth_tier: str,
    ic_pending: bool = False,
) -> Dict[str, Any]:
    """
    Mutate analysis with depth_tier + single upgrade_offer (F1: one primary CTA).
    Persona-split copy (F3/F4). Honest depth language (F8).
    """
    if not isinstance(analysis, dict):
        return analysis

    tier = (depth_tier or DEPTH_FREE).strip().lower()
    analysis["depth_tier"] = tier
    persona = infer_persona(analysis)
    analysis["buyer_persona"] = persona
    ptype = _project_type_label(analysis)

    # --- Free ---
    if tier == DEPTH_FREE:
        if persona == PERSONA_DC_INFRA:
            analysis["upgrade_offer"] = {
                "message": "Need a site package you can attach?",
                "detail": (
                    f"This free preview is a first look for a {ptype} site. "
                    "For FAST-41 / utility / moratorium-depth research plus Research Memo, "
                    "Punch List, and Permit Package PDFs, get an IC Project Report. "
                    "More citeable sources — not a certified fee quote."
                ),
                "cta_label": "Get IC Project Report — $1,500 (PDFs)",
                "cta_tier": "ic_project",
                "secondary_cta_label": "Or Contractor Pro — $149/mo for bid-week habit",
                "secondary_cta_tier": "contractor_pro",
                "current_label": "Free preview",
                "next_label": "IC full scout + PDFs",
                "primary_once": True,
                "honesty_note": (
                    "Deeper research adds sources and packaging. Always confirm fees on the official AHJ schedule."
                ),
            }
        else:
            analysis["upgrade_offer"] = {
                "message": "Get more citeable sources on your next bid-week sites",
                "detail": (
                    "Free is a forwardable preview. Contractor Pro adds bounded local AHJ confirm "
                    "plus light scout (permits / codes) — metered for weekly lookups. "
                    "More sources, not guaranteed fee accuracy."
                ),
                "cta_label": "Upgrade to Contractor Pro — $149/mo",
                "cta_tier": "contractor_pro",
                "secondary_cta_label": "Need PDFs for one big site? IC — $1,500",
                "secondary_cta_tier": "ic_project",
                "current_label": "Free preview",
                "next_label": "Pro (local confirm + light scout)",
                "primary_once": True,
                "honesty_note": (
                    "Deeper research adds sources and packaging. Always confirm fees on the official AHJ schedule."
                ),
            }

    # --- Pro local / partial ---
    elif tier in (DEPTH_PRO_LOCAL, DEPTH_PRO_PARTIAL):
        partial = " (partial / timed out)" if tier == DEPTH_PRO_PARTIAL else ""
        if persona == PERSONA_DC_INFRA:
            analysis["upgrade_offer"] = {
                "message": "Data-center / infra depth needs IC — not Pro light",
                "detail": (
                    f"Pro finished paid local confirm{partial}. Light scout skips FAST-41, water, "
                    "and moratorium passes. IC Project runs the full Universal Scout for this site "
                    "and delivers three PDFs you can forward."
                ),
                "cta_label": "Get IC Project Report — $1,500 (full scout + PDFs)",
                "cta_tier": "ic_project",
                "secondary_cta_label": None,
                "secondary_cta_tier": None,
                "current_label": "Pro local confirm",
                "next_label": "IC full scout + PDFs",
                "primary_once": True,
                "honesty_note": (
                    "IC adds depth and PDFs — still a planning aid; confirm with AHJ / RTO before decisions."
                ),
            }
        else:
            analysis["upgrade_offer"] = {
                "message": "Need a forwardable PDF package for this site?",
                "detail": (
                    f"Pro finished local confirm{partial}. "
                    "IC Project adds full Universal Scout plus Research Memo, Punch List, "
                    "and Permit Package PDFs for this address."
                ),
                "cta_label": "Get IC Project Report — $1,500 (PDFs)",
                "cta_tier": "ic_project",
                "secondary_cta_label": None,
                "secondary_cta_tier": None,
                "current_label": "Pro local confirm",
                "next_label": "IC full scout + PDFs",
                "primary_once": True,
                "honesty_note": (
                    "More sources and PDFs — not a guarantee fees match the live schedule."
                ),
            }

    # --- Pro light ---
    elif tier == DEPTH_PRO_LIGHT:
        if persona == PERSONA_DC_INFRA:
            analysis["upgrade_offer"] = {
                "message": "Pro light is not enough for this project type",
                "detail": (
                    f"You got AHJ / permits / codes light scout for a {ptype} site. "
                    "FAST-41, water-use, and local moratorium depth require IC full Universal Scout "
                    "plus the three PDF deliverables."
                ),
                "cta_label": "Upgrade to IC — full scout + PDFs ($1,500)",
                "cta_tier": "ic_project",
                "secondary_cta_label": None,
                "secondary_cta_tier": None,
                "current_label": "Pro light scout",
                "next_label": "IC full scout + PDFs",
                "primary_once": True,
                "honesty_note": (
                    "IC is deeper packaging for one site — still confirm official schedules and utility rules."
                ),
            }
        else:
            analysis["upgrade_offer"] = {
                "message": "Need PDFs + full scout for this one site?",
                "detail": (
                    "Pro light covered core AHJ / permits / codes. "
                    "IC Project runs the remaining federal/state/vertical passes and gives you "
                    "Research Memo, Punch List, and Permit Package PDFs."
                ),
                "cta_label": "Get IC Project Report — $1,500 (PDFs)",
                "cta_tier": "ic_project",
                "secondary_cta_label": None,
                "secondary_cta_tier": None,
                "current_label": "Pro light scout",
                "next_label": "IC full scout + PDFs",
                "primary_once": True,
                "honesty_note": (
                    "More sources and PDFs — not a certified fee quote."
                ),
            }

    # --- IC full ---
    elif tier == DEPTH_IC_FULL:
        analysis["upgrade_offer"] = {
            "message": "Need the same package for another site?",
            "detail": (
                "This is the fullest Reg Guard run for one bound address (full scout + PDFs). "
                "Buy another IC Project Report for a new site, or IC Annual after your first project."
            ),
            "cta_label": "IC Project for another site — $1,500",
            "cta_tier": "ic_project",
            "secondary_cta_label": "IC Annual — $15,000/yr",
            "secondary_cta_tier": "ic_annual",
            "current_label": "IC full depth",
            "next_label": None,
            "primary_once": True,
            "honesty_note": (
                "Planning diligence package — not an official AHJ or RTO filing."
            ),
        }
    else:
        analysis["upgrade_offer"] = {
            "message": "Get more citeable sources or a PDF package",
            "detail": (
                "Contractor Pro for metered bid-week deepen, or IC Project for full scout + PDFs. "
                "Deeper ≠ automatically more accurate fees."
            ),
            "cta_label": "Upgrade to Contractor Pro — $149/mo",
            "cta_tier": "contractor_pro",
            "secondary_cta_label": "IC Project Report — $1,500",
            "secondary_cta_tier": "ic_project",
            "current_label": "Current results",
            "next_label": "Paid deepen",
            "primary_once": True,
            "honesty_note": (
                "Always confirm fees and rules on official sources before you bid."
            ),
        }

    if ic_pending and tier.startswith("pro"):
        offer = dict(analysis["upgrade_offer"])
        offer["detail"] = (
            (offer.get("detail") or "")
            + " You already purchased IC — confirm Generate IC Report on the next run to attach PDFs."
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
