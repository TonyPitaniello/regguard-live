"""
End or restore paid access from Stripe billing events.

The live webhook records a completed checkout. These events are the rest of
the seat: a subscription that ended, a renewal that was denied, and a charge
that was fully refunded. One-time IC Diligence Bundles stay in place until
that charge itself is refunded.

Persisted statuses stay inside the orders check constraint (completed, failed,
refunded). A cancellation stores the subscription id as ended:<id> so a later
paid invoice cannot turn that seat back on. A denied renewal leaves the
subscription id in place so a successful retry restores the seat.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

try:
    import stripe
except ImportError:
    stripe = None  # type: ignore[misc,assignment]


def _stripe_client():
    if stripe is None:
        return None
    key = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
    if not key:
        return None
    stripe.api_key = key
    return stripe


def _as_dict(obj: Any) -> Dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict"):
        data = obj.to_dict()
        return data if isinstance(data, dict) else {}
    return {}


def _invoice_subscription_id(invoice: Dict[str, Any]) -> str:
    sub = invoice.get("subscription")
    if isinstance(sub, str):
        return sub
    if isinstance(sub, dict) and sub.get("id"):
        return str(sub["id"])
    parent = invoice.get("parent") if isinstance(invoice.get("parent"), dict) else {}
    details = parent.get("subscription_details") if isinstance(parent.get("subscription_details"), dict) else {}
    sub2 = details.get("subscription")
    if isinstance(sub2, str):
        return sub2
    if isinstance(sub2, dict) and sub2.get("id"):
        return str(sub2["id"])
    return ""


def _email_from_obj(obj: Dict[str, Any]) -> str:
    metadata = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {}
    email = str(metadata.get("email") or obj.get("customer_email") or "").strip().lower()
    if "@" in email:
        return email
    customer = obj.get("customer")
    if isinstance(customer, dict):
        email = str(customer.get("email") or "").strip().lower()
        if "@" in email:
            return email
    if isinstance(customer, str) and customer.startswith("cus_"):
        client = _stripe_client()
        if client is None:
            return ""
        try:
            cust = client.Customer.retrieve(customer)
            email = str(getattr(cust, "email", "") or "").strip().lower()
            return email if "@" in email else ""
        except Exception as e:
            logger.warning("Stripe customer lookup failed: %s", e)
    return ""


def _tier_from_obj(obj: Dict[str, Any]) -> str:
    metadata = obj.get("metadata") if isinstance(obj.get("metadata"), dict) else {}
    return str(metadata.get("tier") or "").strip().lower()


def _orders_for_subscription(obj: Dict[str, Any], subscription_id: str) -> List[Dict[str, Any]]:
    from order_service import (
        SUBSCRIPTION_TIERS,
        find_orders_by_stripe_field,
        get_raw_orders_for_email,
        normalize_tier,
    )

    found = find_orders_by_stripe_field("stripe_subscription_id", subscription_id) if subscription_id else []
    if found:
        return found
    email = _email_from_obj(obj)
    tier = _tier_from_obj(obj)
    if not email:
        return []
    matches: List[Dict[str, Any]] = []
    for order in get_raw_orders_for_email(email):
        order_tier = normalize_tier(str(order.get("tier") or ""))
        if order_tier not in SUBSCRIPTION_TIERS:
            continue
        if tier and normalize_tier(tier) != order_tier:
            continue
        existing = str(order.get("stripe_subscription_id") or "")
        if existing.startswith("ended:"):
            continue
        if existing and subscription_id and existing != subscription_id:
            continue
        matches.append(order)
    return matches


def _mark(orders: List[Dict[str, Any]], kind: str, subscription_id: str = "") -> List[str]:
    from order_service import billing_state_for, set_order_billing

    changed: List[str] = []
    for order in orders:
        state = billing_state_for(order)
        sub = str(order.get("stripe_subscription_id") or subscription_id or "")
        if kind == "canceled":
            if state == "refunded":
                continue
            raw = sub[6:] if sub.startswith("ended:") else sub
            stored = f"ended:{raw}" if raw else "ended:"
            set_order_billing(order, status="failed", stripe_subscription_id=stored)
        elif kind == "past_due":
            if state in ("canceled", "refunded"):
                continue
            current_sub = str(order.get("stripe_subscription_id") or "")
            stored = subscription_id if subscription_id and not current_sub else None
            set_order_billing(order, status="failed", stripe_subscription_id=stored)
        elif kind == "refunded":
            raw = sub[6:] if sub.startswith("ended:") else sub
            stored = f"ended:{raw}" if raw else (order.get("stripe_subscription_id") or None)
            set_order_billing(
                order,
                status="refunded",
                stripe_subscription_id=stored if isinstance(stored, str) and stored else None,
            )
        elif kind == "restored":
            if state != "past_due":
                continue
            set_order_billing(order, status="completed")
        else:
            continue
        changed.append(str(order.get("order_id") or order.get("stripe_session_id") or ""))
    if changed:
        logger.info("Billing %s updated %s order(s)", kind, len(changed))
    return changed


def _event_subscription_id(obj: Dict[str, Any]) -> str:
    object_name = str(obj.get("object") or "")
    object_id = str(obj.get("id") or "")
    if object_name == "subscription" or object_id.startswith("sub_"):
        return object_id
    return _invoice_subscription_id(obj)


def end_subscription(obj: Dict[str, Any]) -> Dict[str, Any]:
    subscription_id = _event_subscription_id(obj)
    orders = _orders_for_subscription(obj, subscription_id)
    changed = _mark(orders, "canceled", subscription_id)
    return {"status": "canceled" if changed else "no_matching_order", "orders": len(changed)}


def mark_past_due(obj: Dict[str, Any]) -> Dict[str, Any]:
    subscription_id = _event_subscription_id(obj)
    orders = _orders_for_subscription(obj, subscription_id)
    changed = _mark(orders, "past_due", subscription_id)
    return {"status": "past_due" if changed else "no_matching_order", "orders": len(changed)}


def restore_paid_subscription(obj: Dict[str, Any]) -> Dict[str, Any]:
    subscription_id = _event_subscription_id(obj)
    orders = _orders_for_subscription(obj, subscription_id)
    changed = _mark(orders, "restored", subscription_id)
    return {"status": "restored" if changed else "unchanged", "orders": len(changed)}


def _charge_is_full_refund(charge: Dict[str, Any]) -> bool:
    if charge.get("refunded") is True:
        return True
    amount = int(charge.get("amount") or 0)
    refunded = int(charge.get("amount_refunded") or 0)
    return amount > 0 and refunded >= amount


def _orders_for_charge(charge: Dict[str, Any]) -> List[Dict[str, Any]]:
    from order_service import find_orders_by_stripe_field

    payment_intent = charge.get("payment_intent")
    if isinstance(payment_intent, dict):
        payment_intent = payment_intent.get("id")
    payment_intent = str(payment_intent or "")
    found = find_orders_by_stripe_field("stripe_payment_intent_id", payment_intent) if payment_intent else []
    if found:
        return found
    invoice = charge.get("invoice")
    subscription_id = ""
    if isinstance(invoice, dict):
        subscription_id = _invoice_subscription_id(invoice)
    elif isinstance(invoice, str) and invoice:
        client = _stripe_client()
        if client is not None:
            try:
                loaded = _as_dict(client.Invoice.retrieve(invoice))
                subscription_id = _invoice_subscription_id(loaded)
            except Exception as e:
                logger.warning("Invoice lookup for refund failed: %s", e)
    if subscription_id:
        return find_orders_by_stripe_field("stripe_subscription_id", subscription_id)
    return []


def apply_refund(charge: Dict[str, Any]) -> Dict[str, Any]:
    if not _charge_is_full_refund(charge):
        return {"status": "partial_refund_kept", "orders": 0}
    orders = _orders_for_charge(charge)
    changed = _mark(orders, "refunded")
    return {"status": "refunded" if changed else "no_matching_order", "orders": len(changed)}


def apply_stripe_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Apply one Stripe event. Checkout completion is handled by the order webhook."""
    event_type = str(event.get("type") or "")
    obj = (event.get("data") or {}).get("object") or {}
    if not isinstance(obj, dict):
        obj = _as_dict(obj)
    if event_type == "customer.subscription.deleted":
        return end_subscription(obj)
    if event_type == "customer.subscription.updated":
        status = str(obj.get("status") or "").lower()
        if status in ("canceled", "unpaid", "incomplete_expired"):
            return end_subscription(obj)
        if status == "past_due":
            return mark_past_due(obj)
        if status in ("active", "trialing"):
            return restore_paid_subscription(obj)
        return {"status": "acknowledged", "orders": 0}
    if event_type == "invoice.payment_failed":
        return mark_past_due(obj)
    if event_type == "invoice.payment_succeeded":
        return restore_paid_subscription(obj)
    if event_type == "charge.refunded":
        return apply_refund(obj)
    return {"status": "acknowledged", "orders": 0}


def create_billing_portal_url(email: str) -> str:
    """Stripe Customer Portal for cancel, card update, and invoices."""
    email_l = (email or "").strip().lower()
    if "@" not in email_l:
        raise ValueError("Email is required")
    client = _stripe_client()
    if client is None:
        raise ValueError("Billing is not configured")
    customers = client.Customer.list(email=email_l, limit=1)
    data = getattr(customers, "data", None) or []
    if not data:
        raise ValueError("No billing account for this email yet")
    customer_id = str(getattr(data[0], "id", "") or "")
    if not customer_id:
        raise ValueError("No billing account for this email yet")
    return_url = f"https://app.regguardagent.com/orders?email={quote(email_l)}"
    try:
        session = client.billing_portal.Session.create(customer=customer_id, return_url=return_url)
    except Exception as first_error:
        message = str(first_error).lower()
        if "configuration" not in message and "portal" not in message:
            logger.warning("Billing portal session failed: %s", first_error)
            raise ValueError(
                "Billing portal is unavailable. Email support@regguardagent.com to cancel or update the card."
            ) from first_error
        config = client.billing_portal.Configuration.create(
            business_profile={"headline": "Manage your Reg Guard plan"},
            features={
                "invoice_history": {"enabled": True},
                "payment_method_update": {"enabled": True},
                "subscription_cancel": {
                    "enabled": True,
                    "mode": "at_period_end",
                    "proration_behavior": "none",
                },
            },
        )
        session = client.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
            configuration=str(getattr(config, "id", "") or ""),
        )
    url = getattr(session, "url", None)
    if not url and isinstance(session, dict):
        url = session.get("url")
    if not url:
        raise ValueError("Billing portal is unavailable. Email support@regguardagent.com")
    return str(url)
