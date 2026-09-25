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
    depth = str(analysis.get("depth_tier") or "").lower()
    is_ic = depth == "ic_full" or scout_mode == "full" or bool(analysis.get("ic_package"))
    if scout_mode == "light":
        bullets.append(
            "Pro light scout: AHJ / building permits / adopted codes (3 passes). "
            "Not full federal/vertical depth — that is IC Diligence Bundle."
        )
    elif scout_mode == "full" or is_ic:
        bullets.append("Full Universal Scout passes ran for this site (IC-depth research).")
        ultra = analysis.get("ultralocal_scout") if isinstance(analysis.get("ultralocal_scout"), dict) else {}
        if ultra.get("enabled") or str(analysis.get("scout_locality_depth") or "") == "local_ultralocal":
            bullets.append("IC local + ultralocal scout (HOA / MUD / township / neighborhood) merged into killers.")

    if not bullets:
        bullets.append(
            "Paid deepen ran on this email. If this looks thin, the AHJ may be portal-only — "
            "try IC Diligence Bundle for full scout + counsel ZIP."
        )

    if not is_ic:
        bullets.append(
            "Pro desk formats unlocked: fee/punch CSV, full city pack PDF, bid packet "
            "(not on Free or Estimator / Permit Runner)."
        )

    analysis["pro_delta"] = {
        "title": (
            "What IC-depth research added on this run"
            if is_ic
            else "What Contractor Pro added vs Free / Estimator"
        ),
        "bullets": bullets[:7],
        "pages_scraped": pages,
        "fee_rows": fee_n,
        "scout_sources": len(sources),
        "verified_punch_lines": verified_punch,
        "scout_mode": scout_mode or "none",
        "honesty": (
            "Research depth and citeable sources — not the Diligence Bundle file contents, and not a "
            "guarantee fees match the live AHJ schedule."
            if is_ic
            else "More sources and deeper scout — not a guarantee fees match the live AHJ schedule."
        ),
    }
    return analysis


def _offer_free_next(ptype: str) -> Dict[str, Any]:
    """Free → Estimator (never skip to IC). Pain-first voice."""
    site = f" for a {ptype} site" if ptype else ""
    return {
        "message": "Stop re-sending screenshots that fall apart in the GC thread",
        "detail": (
            f"You're still on Free{site}: shape of risk, nothing the GC can file. "
            "Estimator / Permit Runner ($79/mo) gives you the full Bid Risk Receipt you can forward, "
            "the rest of the punch list, and Saved Jobs — stamp every client site without rebuilding the story."
        ),
        "cta_label": "Start Estimator / Permit Runner — $79/mo",
        "cta_tier": "partner",
        "secondary_cta_label": None,
        "secondary_cta_tier": None,
        "current_label": "Free Lookups",
        "next_label": "Estimator — forwardable Receipt · full punch · Saved Jobs",
        "primary_once": True,
        "honesty_note": (
            "Planning aid — confirm fees on the official AHJ schedule before you bid."
        ),
    }


def _offer_partner_next(ptype: str) -> Dict[str, Any]:
    """Estimator → Contractor Pro."""
    site = f" on this {ptype} site" if ptype else ""
    return {
        "message": "Still hunting fee dollars and city schedules by hand?",
        "detail": (
            f"Estimator got you a Receipt the GC can file{site}. "
            "You're still the one scraping portals for fee lines before every bid. "
            "Contractor Pro ($149/mo) puts fee dollars, Full City Pack PDF, paste-ready CSV, "
            "and bid packet on the desk — for jobs where your number has to hold."
        ),
        "cta_label": "Upgrade to Contractor Pro — $149/mo",
        "cta_tier": "contractor_pro",
        "secondary_cta_label": None,
        "secondary_cta_tier": None,
        "current_label": "Estimator / Permit Runner",
        "next_label": "Pro bid desk — fee dollars · City Pack PDF · CSV · bid packet",
        "primary_once": True,
        "honesty_note": (
            "Pro arms the estimate — still confirm dollars on the live AHJ schedule."
        ),
    }


def _offer_pro_next(ptype: str, *, partial: str = "", light: bool = False) -> Dict[str, Any]:
    """Contractor Pro → IC Diligence Bundle."""
    desk = "Pro light scout" if light else "Contractor Pro"
    site = f" for a {ptype} site" if ptype else ""
    return {
        "message": "Counsel won’t mark up a City Pack PDF",
        "detail": (
            f"{desk} is the bid desk{partial}{site}. "
            "For one capital-sensitive address — LOI, IC call, owner’s rep, lender — "
            "IC Diligence Bundle ($1,500) ships the counsel ZIP: decision memo, boardroom brief, "
            "editable Word with exhibits, Excel evidence map. Same AHJ facts in counsel format — "
            "not a bigger City Pack."
        ),
        "cta_label": "Get IC Diligence Bundle — $1,500",
        "cta_tier": "ic_project",
        "secondary_cta_label": "Or IC Annual — $15,000/yr multi-site",
        "secondary_cta_tier": "ic_annual",
        "current_label": desk,
        "next_label": "Counsel ZIP — memo · boardroom · Word · Excel exhibits",
        "primary_once": True,
        "honesty_note": (
            "IC is counsel packaging for one site — still a planning aid; confirm with AHJ / utility."
        ),
    }


def _offer_ic_next() -> Dict[str, Any]:
    """IC → Annual (shop rate) or another Project."""
    return {
        "message": "Still cutting a $1,500 PO every time a new address hits the pipeline?",
        "detail": (
            "IC Project is one bound site. If your shop regenerates this Diligence Bundle across "
            "addresses all year, IC Annual ($15,000/yr) pays for itself around the 10th site — "
            "same counsel ZIP, new address, no rebuying the package shape."
        ),
        "cta_label": "IC Annual — $15,000/yr",
        "cta_tier": "ic_annual",
        "secondary_cta_label": "Or another site IC Bundle — $1,500",
        "secondary_cta_tier": "ic_project",
        "current_label": "IC Diligence Bundle",
        "next_label": "Shop rate — regenerate across sites (~10× to break even)",
        "primary_once": True,
        "honesty_note": (
            "You already have IC full depth on this site — planning diligence, not an AHJ filing."
        ),
    }


def stamp_ladder_access_offer(
    analysis: Dict[str, Any],
    *,
    access_tier: str,
    ic_pending: bool = False,
) -> Dict[str, Any]:
    """
    Stepwise entitlement ladder (authoritative for CTA):
      Free → Estimator → Contractor Pro → IC Project → IC Annual
    Never skip Free straight to IC — even on data-center persona.
    """
    if not isinstance(analysis, dict):
        return analysis
    ptype = _project_type_label(analysis)
    t = (access_tier or "free").strip().lower()
    if t in ("ic", "ic_project", "ic_consultant", "ic_annual", "sponsor"):
        analysis["upgrade_offer"] = _offer_ic_next()
    elif t in ("pro", "contractor_pro"):
        analysis["upgrade_offer"] = _offer_pro_next(ptype)
        if ic_pending:
            offer = dict(analysis["upgrade_offer"])
            offer["detail"] = (
                (offer.get("detail") or "")
                + " You already purchased IC — confirm Generate IC Report on the next run "
                "to unlock the Diligence Bundle ZIP."
            )
            analysis["upgrade_offer"] = offer
    elif t in ("partner", "estimator", "permit_runner"):
        analysis["upgrade_offer"] = _offer_partner_next(ptype)
    else:
        analysis["upgrade_offer"] = _offer_free_next(ptype)
    return analysis


def stamp_upgrade_offer(
    analysis: Dict[str, Any],
    *,
    depth_tier: str,
    ic_pending: bool = False,
    access_tier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Mutate analysis with depth_tier + single upgrade_offer (F1: one primary CTA).
    Stepwise Free → Estimator → Pro → IC (never Free→IC skip).
    When access_tier is set, entitlement ladder wins over research depth.
    """
    if not isinstance(analysis, dict):
        return analysis

    tier = (depth_tier or DEPTH_FREE).strip().lower()
    analysis["depth_tier"] = tier
    persona = infer_persona(analysis)
    analysis["buyer_persona"] = persona
    ptype = _project_type_label(analysis)

    # Entitlement ladder is authoritative when known (samples + live stamp)
    if access_tier:
        return stamp_ladder_access_offer(
            analysis, access_tier=access_tier, ic_pending=ic_pending
        )

    # --- Free (all personas — climb habit ladder first) ---
    if tier == DEPTH_FREE:
        analysis["upgrade_offer"] = _offer_free_next(ptype)

    # --- Estimator-depth alias (samples / stamped partner runs) ---
    elif tier in ("partner", "estimator"):
        analysis["upgrade_offer"] = _offer_partner_next(ptype)

    # --- Pro local / partial / light → IC ---
    elif tier in (DEPTH_PRO_LOCAL, DEPTH_PRO_PARTIAL, DEPTH_PRO_LIGHT, "pro", "contractor_pro"):
        partial = " (partial / timed out)" if tier == DEPTH_PRO_PARTIAL else ""
        light = tier == DEPTH_PRO_LIGHT
        analysis["upgrade_offer"] = _offer_pro_next(ptype, partial=partial, light=light)

    # --- IC full ---
    elif tier == DEPTH_IC_FULL:
        analysis["upgrade_offer"] = _offer_ic_next()
    else:
        analysis["upgrade_offer"] = _offer_free_next(ptype)

    if ic_pending and tier.startswith("pro"):
        offer = dict(analysis["upgrade_offer"])
        offer["detail"] = (
            (offer.get("detail") or "")
            + " You already purchased IC — confirm Generate IC Report on the next run to unlock the Diligence Bundle ZIP."
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
