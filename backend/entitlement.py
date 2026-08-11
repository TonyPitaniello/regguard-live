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
    return False


def access_summary(email: Optional[str]) -> Dict[str, Any]:
    email_l = _normalize_email(email)
    paid = has_paid_access(email_l)
    tiers: list[str] = []
    if email_l:
        try:
            from order_service import list_orders_for_email

            for order in list_orders_for_email(email_l):
                tier = (order.get("tier") or "").strip().lower()
                if tier in PAID_TIERS and tier not in tiers:
                    tiers.append(tier)
        except Exception:
            pass
    return {
        "email": email_l,
        "paid": paid,
        "deep_research": paid,
        "tiers": tiers,
        "primary_tier": tiers[0] if tiers else ("free" if email_l else "anonymous"),
    }
