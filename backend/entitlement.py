"""Paid-tier entitlement checks for deeper research routing."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)

PAID_TIERS: Set[str] = {
    "partner",
    "contractor_pro",
    "ic_project",
    "ic_annual",
    "ic_consultant",
    "sponsor",
}

# Research depth / paid_local_confirm — Estimator ($79) deliberately excluded.
# $79 buys habit unlocks (Receipt + punch + Saved Jobs); $149 buys deep scout + desk PDFs.
PRO_RESEARCH_TIERS: Set[str] = {
    "contractor_pro",
    "ic_project",
    "ic_annual",
    "ic_consultant",
    "sponsor",
}


def _normalize_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()


def _order_tiers_for_email(email_l: str) -> list[str]:
    tiers: list[str] = []
    try:
        from order_service import list_orders_for_email

        for order in list_orders_for_email(email_l):
            tier = (order.get("tier") or "").strip().lower()
            status = (order.get("status") or "").strip().lower()
            if tier in PAID_TIERS and status in ("completed", "active", "paid", ""):
                if tier not in tiers:
                    tiers.append(tier)
    except Exception as e:
        logger.warning("order tier list failed for %s: %s", email_l, e)
    return tiers


def _stripe_paid_for_email(email_l: str) -> bool:
    """Fallback: active Stripe subscription or recent paid Checkout for this email."""
    import os

    key = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
    if not key:
        return False
    try:
        import stripe

        stripe.api_key = key
        customers = stripe.Customer.list(email=email_l, limit=5)
        for cust in customers.data:
            subs = stripe.Subscription.list(customer=cust.id, status="all", limit=10)
            for sub in subs.data:
                if getattr(sub, "status", "") in ("active", "trialing", "past_due"):
                    return True
            sessions = stripe.checkout.Session.list(customer=cust.id, limit=10)
            for sess in sessions.data:
                if getattr(sess, "payment_status", "") == "paid":
                    return True
                if getattr(sess, "status", "") == "complete":
                    return True
    except Exception as e:
        logger.warning("Stripe entitlement fallback failed for %s: %s", email_l, e)
    return False


def has_paid_access(email: Optional[str]) -> bool:
    """True if this email has any paid habit tier (Estimator / Pro / IC)."""
    email_l = _normalize_email(email)
    if not email_l or "@" not in email_l:
        return False
    if _order_tiers_for_email(email_l):
        return True
    # Survive Render restarts when in-memory orders were cleared
    if _stripe_paid_for_email(email_l):
        return True
    return False


def has_pro_research_access(email: Optional[str]) -> bool:
    """
    True only for Contractor Pro / IC / Sponsor — NOT Estimator ($79).

    Premortem: Estimator must not get paid_local_confirm / light Universal Scout
    or $149 collapses to “file formats only.”
    """
    email_l = _normalize_email(email)
    if not email_l or "@" not in email_l:
        return False
    for tier in _order_tiers_for_email(email_l):
        if tier in PRO_RESEARCH_TIERS:
            return True
    return False


def has_partner_habit_access(email: Optional[str]) -> bool:
    """Estimator / Permit Runner or higher — habit unlocks without Pro research."""
    return has_paid_access(email)


def analysis_is_ic_depth(analysis: Optional[Dict[str, Any]]) -> bool:
    """True only for a completed IC Project run — not free Instant Preview."""
    if not isinstance(analysis, dict):
        return False
    if analysis.get("preview") is True:
        return False
    if analysis.get("research_incomplete") is True:
        return False
    if analysis.get("depth_claim_honest") is False:
        return False
    honesty = analysis.get("honesty") if isinstance(analysis.get("honesty"), dict) else {}
    source = str(honesty.get("source") or "").strip().lower()
    if source in ("instant", "preview", "client_instant"):
        return False
    depth_tier = str(analysis.get("depth_tier") or "").strip().lower()
    research_depth = str(analysis.get("research_depth") or "").strip().lower()
    return depth_tier == "ic_full" or research_depth in ("ic", "ic_full")


def assert_ic_artifact_access(email: Optional[str], analysis: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Hard paywall for IC Diligence Bundle / boardroom / DOCX / evidence exports.

    Requires:
      1) This analysis is IC-depth (not free Instant Preview)
      2) Email has IC Project access for THIS site ($1,500 per site)
    """
    from fastapi import HTTPException

    from ic_project_fulfillment import evaluate_ic_site_access

    email_l = _normalize_email(email)
    if not email_l or "@" not in email_l:
        raise HTTPException(
            status_code=403,
            detail="IC Diligence Bundle requires the purchase email on the request.",
        )
    if not analysis_is_ic_depth(analysis):
        raise HTTPException(
            status_code=403,
            detail=(
                "IC Diligence Bundle requires a completed IC Project run for this site. "
                "Free Instant Preview cannot download the $1,500 counsel ZIP — "
                "confirm the pin, purchase IC Project if needed, and re-run with Generate IC Report."
            ),
        )

    pi = analysis.get("project_info") if isinstance(analysis, dict) else None
    pi = pi if isinstance(pi, dict) else {}
    access = evaluate_ic_site_access(
        email_l,
        address=str(pi.get("address") or ""),
        city=str(pi.get("city") or ""),
        state=str(pi.get("state") or ""),
        zip_code=str(pi.get("zip") or ""),
    )
    if not access.get("allowed"):
        raise HTTPException(
            status_code=403,
            detail=str(
                access.get("message")
                or (
                    "IC Project is $1,500 per site. This email has no unused credit for this address."
                )
            ),
        )
    return access


def access_summary(
    email: Optional[str],
    *,
    address: str = "",
    city: str = "",
    state: str = "",
    zip_code: str = "",
) -> Dict[str, Any]:
    email_l = _normalize_email(email)
    paid = has_paid_access(email_l)
    deep_research = has_pro_research_access(email_l)
    tiers: list[str] = []
    ic_report_pending = False
    has_ic = False
    has_ic_pdfs = False
    ic_site: Dict[str, Any] = {
        "allowed": False,
        "mode": "need_purchase",
        "order_id": None,
        "bound_site": "",
        "site_fingerprint": "",
        "message": "IC Project is $1,500 per site.",
    }
    if email_l:
        try:
            from order_service import list_orders_for_email
            from ic_project_fulfillment import (
                evaluate_ic_site_access,
                is_ic_tier,
                pdfs_are_ready,
            )

            for order in list_orders_for_email(email_l):
                tier = (order.get("tier") or "").strip().lower()
                if tier in PAID_TIERS and tier not in tiers:
                    tiers.append(tier)
                if is_ic_tier(tier):
                    has_ic = True
                    if pdfs_are_ready(order.get("pdfs")):
                        has_ic_pdfs = True
            # Pending only when IC purchased and PDFs not ready yet
            ic_report_pending = has_ic and not has_ic_pdfs
            if address or city or zip_code:
                ic_site = evaluate_ic_site_access(
                    email_l,
                    address=address,
                    city=city,
                    state=state,
                    zip_code=zip_code,
                )
            elif has_ic:
                # No site in query — report generic pending / bound status only
                ic_site = evaluate_ic_site_access(email_l)
        except Exception:
            pass
    return {
        "email": email_l,
        "paid": paid,
        "deep_research": deep_research,
        "habit_access": paid,
        "pro_research": deep_research,
        "tiers": tiers,
        "primary_tier": tiers[0] if tiers else ("free" if email_l else "anonymous"),
        "ic_report_pending": ic_report_pending,
        "ic_pdfs_ready": has_ic_pdfs,
        "ic_site": ic_site,
    }
