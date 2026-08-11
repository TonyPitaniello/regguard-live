"""Paid-tier entitlement checks for deeper research routing."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)

PAID_TIERS: Set[str] = {
    "contractor_pro",
    "ic_project",
    "ic_annual",
    "ic_consultant",
    "sponsor",
}


def _normalize_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()


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
    """True if this email has a completed paid order (Pro / IC / etc.)."""
    email_l = _normalize_email(email)
    if not email_l or "@" not in email_l:
        return False
    try:
        from order_service import list_orders_for_email

        for order in list_orders_for_email(email_l):
            tier = (order.get("tier") or "").strip().lower()
            status = (order.get("status") or "").strip().lower()
            if tier in PAID_TIERS and status in ("completed", "active", "paid", ""):
                return True
    except Exception as e:
        logger.warning("entitlement check failed for %s: %s", email_l, e)

    # Survive Render restarts when in-memory orders were cleared
    if _stripe_paid_for_email(email_l):
        return True
    return False


def access_summary(email: Optional[str]) -> Dict[str, Any]:
    email_l = _normalize_email(email)
    paid = has_paid_access(email_l)
    tiers: list[str] = []
    ic_report_pending = False
    if email_l:
        try:
            from order_service import list_orders_for_email
            from ic_project_fulfillment import is_ic_tier, pdfs_are_ready

            for order in list_orders_for_email(email_l):
                tier = (order.get("tier") or "").strip().lower()
                if tier in PAID_TIERS and tier not in tiers:
                    tiers.append(tier)
                if is_ic_tier(tier) and not pdfs_are_ready(order.get("pdfs")):
                    ic_report_pending = True
        except Exception:
            pass
    return {
        "email": email_l,
        "paid": paid,
        "deep_research": paid,
        "tiers": tiers,
        "primary_tier": tiers[0] if tiers else ("free" if email_l else "anonymous"),
        "ic_report_pending": ic_report_pending,
    }
