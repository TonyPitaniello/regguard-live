"""
Unified Stripe Integration Service
Handles checkout sessions, webhooks, and order management for all customer segments.
Supports tiers: free, contractor_pro, ic_project, ic_annual, sponsor
"""

import os
import logging
import stripe
from typing import Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Tier pricing configuration
TIER_PRICING = {
    "free": {
        "name": "Contractor Free",
        "amount_cents": 0,
        "mode": None,
        "price_id": None,
    },
    "partner": {
        "name": "Partner / Permit Runner",
        "amount_cents": 7900,
        "mode": "subscription",
        "price_id": os.getenv("STRIPE_PRICE_PARTNER"),
    },
    "contractor_pro": {
        "name": "Contractor Pro",
        "amount_cents": 14900,
        "mode": "subscription",
        "price_id": os.getenv("STRIPE_PRICE_CONTRACTOR_PRO"),
    },
    "ic_project": {
        "name": "IC Project Report",
        "amount_cents": 150000,
        "mode": "payment",
        "price_id": os.getenv("STRIPE_PRICE_IC_PROJECT"),
    },
    "ic_annual": {
        "name": "IC Annual",
        "amount_cents": 1500000,
        "mode": "subscription",
        "price_id": os.getenv("STRIPE_PRICE_IC_ANNUAL"),
    },
    "sponsor": {
        "name": "Sponsor",
        "amount_cents": 150000,
        "mode": "subscription",
        "price_id": os.getenv("STRIPE_PRICE_SPONSOR"),
    },
}


class CheckoutRequest(BaseModel):
    """Request to create checkout session"""
    user_id: str
    tier: str
    success_url: str
    cancel_url: str


class OrderResponse(BaseModel):
    """Order representation"""
    id: str
    user_id: str
    stripe_session_id: Optional[str]
    stripe_payment_intent_id: Optional[str]
    amount: int
    currency: str
    status: str  # pending, completed, failed
    tier: str
    created_at: str
    updated_at: str


def is_stripe_configured() -> bool:
    """Check if Stripe is properly configured"""
    return bool(stripe.api_key and STRIPE_WEBHOOK_SECRET)


def _meta_trim(value: Optional[str], limit: int = 450) -> str:
    """Stripe metadata values max 500 chars."""
    return (value or "").strip()[:limit]


async def create_checkout_session(
    user_id: str,
    tier: str,
    success_url: str = "https://localhost:5173/checkout/success",
    cancel_url: str = "https://localhost:5173/checkout/cancel",
    email: Optional[str] = None,
    name: Optional[str] = None,
    trial_id: Optional[str] = None,
    referral_code: Optional[str] = None,
    site_address: Optional[str] = None,
    site_city: Optional[str] = None,
    site_state: Optional[str] = None,
    site_zip: Optional[str] = None,
    site_project_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a Stripe Checkout Session for the specified tier.

    Uses mode from tier config (`payment` vs `subscription`).
    Without price_id: one-time uses price_data; subscriptions use recurring price_data.
    Optional site_* fields bind the researched address into session metadata so
    IC auto-run survives cross-device / cleared sessionStorage (premortem F1/F10).
    """
    if not is_stripe_configured():
        raise ValueError("Stripe is not configured. Set STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET.")

    if tier not in TIER_PRICING:
        raise ValueError(f"Invalid tier: {tier}")

    if tier == "free":
        return {
            "checkout_url": None,
            "session_id": None,
            "message": "Free tier - no payment required",
        }

    try:
        tier_config = TIER_PRICING[tier]
        mode = tier_config.get("mode") or "subscription"
        price_id = (tier_config.get("price_id") or "").strip() or None
        amount_cents = tier_config["amount_cents"]

        if price_id:
            line_items = [{"price": price_id, "quantity": 1}]
        elif mode == "subscription":
            # Works without Dashboard Price ID (Partner / fallback)
            line_items = [
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": amount_cents,
                        "recurring": {"interval": "month"},
                        "product_data": {"name": tier_config["name"]},
                    },
                    "quantity": 1,
                }
            ]
        else:
            line_items = [
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": amount_cents,
                        "product_data": {
                            "name": tier_config["name"],
                        },
                    },
                    "quantity": 1,
                }
            ]
            mode = "payment"

        email_clean = (email or "").strip().lower()
        metadata = {
            "user_id": user_id,
            "tier": tier,
        }
        if email_clean:
            metadata["email"] = email_clean
        if name:
            metadata["name"] = name.strip()
        if trial_id:
            metadata["trial_id"] = trial_id
        if referral_code:
            metadata["referral_code"] = str(referral_code).strip().lower()[:64]

        sa = _meta_trim(site_address)
        sc = _meta_trim(site_city, 120)
        ss = _meta_trim(site_state, 32)
        sz = _meta_trim(site_zip, 16)
        spt = _meta_trim(site_project_type, 64)
        if sa:
            metadata["site_address"] = sa
        if sc:
            metadata["site_city"] = sc
        if ss:
            metadata["site_state"] = ss
        if sz:
            metadata["site_zip"] = sz
        if spt:
            metadata["site_project_type"] = spt
        if sa and sc and ss and sz:
            metadata["site_label"] = _meta_trim(f"{sa}, {sc}, {ss} {sz}")

        # success_url may already include ?unlock=&email= — never append a second "?"
        sep = "&" if "?" in (success_url or "") else "?"
        success_with_session = f"{success_url}{sep}session_id={{CHECKOUT_SESSION_ID}}"

        create_kwargs: Dict[str, Any] = {
            "payment_method_types": ["card"],
            "mode": mode,
            "line_items": line_items,
            "success_url": success_with_session,
            "cancel_url": cancel_url,
            "metadata": metadata,
        }
        if email_clean:
            create_kwargs["customer_email"] = email_clean

        session = stripe.checkout.Session.create(**create_kwargs)

        logger.info(f"✅ Checkout session created: {session.id} for user {user_id} tier={tier} mode={mode}")

        return {
            "checkout_url": session.url,
            "session_id": session.id,
        }

    except stripe.error.StripeError as e:
        logger.error(f"❌ Stripe error creating checkout: {e}")
        raise ValueError(f"Failed to create checkout session: {str(e)}") from e
    except Exception as e:
        logger.error(f"❌ Unexpected error creating checkout: {e}")
        raise ValueError(f"Unexpected error: {str(e)}") from e


async def get_order(order_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve an order from the database."""
    logger.info(f"📋 Retrieving order: {order_id}")
    return None


async def get_user_orders(user_id: str, limit: int = 10) -> list:
    """Retrieve all orders for a user."""
    logger.info(f"📋 Retrieving orders for user: {user_id}")
    return []


async def handle_webhook(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle Stripe webhook events."""
    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})

    logger.info(f"🔔 Processing webhook: {event_type}")

    try:
        if event_type == "checkout.session.completed":
            return await handle_checkout_session_completed(data)
        elif event_type == "invoice.payment_succeeded":
            return await handle_invoice_payment_succeeded(data)
        elif event_type == "invoice.payment_failed":
            return await handle_invoice_payment_failed(data)
        elif event_type == "customer.subscription.deleted":
            return await handle_subscription_deleted(data)
        else:
            logger.info(f"ℹ️ Unhandled event type: {event_type}")
            return {"status": "unhandled"}
    except Exception as e:
        logger.error(f"❌ Error handling webhook: {e}")
        raise


async def handle_checkout_session_completed(session_data: Dict[str, Any]) -> Dict[str, Any]:
    session_id = session_data.get("id")
    metadata = session_data.get("metadata", {})
    user_id = metadata.get("user_id")
    tier = metadata.get("tier")

    logger.info(f"✅ Checkout session completed: {session_id} for user {user_id}")

    return {
        "status": "success",
        "session_id": session_id,
        "user_id": user_id,
        "tier": tier,
    }


async def handle_invoice_payment_succeeded(invoice_data: Dict[str, Any]) -> Dict[str, Any]:
    invoice_id = invoice_data.get("id")
    logger.info(f"💰 Invoice payment succeeded: {invoice_id}")
    return {"status": "success", "invoice_id": invoice_id}


async def handle_invoice_payment_failed(invoice_data: Dict[str, Any]) -> Dict[str, Any]:
    invoice_id = invoice_data.get("id")
    logger.warning(f"⚠️ Invoice payment failed: {invoice_id}")
    return {"status": "failed", "invoice_id": invoice_id}


async def handle_subscription_deleted(subscription_data: Dict[str, Any]) -> Dict[str, Any]:
    subscription_id = subscription_data.get("id")
    logger.info(f"🔄 Subscription deleted: {subscription_id}")
    return {"status": "deleted", "subscription_id": subscription_id}


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify Stripe webhook signature."""
    if not STRIPE_WEBHOOK_SECRET:
        logger.warning("⚠️ STRIPE_WEBHOOK_SECRET not set, skipping verification")
        return True

    try:
        stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)
        return True
    except ValueError:
        logger.warning("⚠️ Invalid webhook signature format")
        return False
    except stripe.error.SignatureVerificationError:
        logger.warning("⚠️ Webhook signature verification failed")
        return False
    except Exception as e:
        logger.error(f"❌ Error verifying webhook signature: {e}")
        return False
