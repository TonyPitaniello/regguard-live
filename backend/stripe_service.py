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


async def create_checkout_session(
    user_id: str,
    tier: str,
    success_url: str = "https://localhost:5173/checkout/success",
    cancel_url: str = "https://localhost:5173/checkout/cancel",
    email: Optional[str] = None,
    name: Optional[str] = None,
    trial_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a Stripe Checkout Session for the specified tier.

    Uses mode from tier config (`payment` vs `subscription`).
    For payment mode without price_id, falls back to price_data with unit_amount.
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
        price_id = tier_config.get("price_id")
        amount_cents = tier_config["amount_cents"]

        if price_id:
            line_items = [{"price": price_id, "quantity": 1}]
        else:
            # One-time payment (or missing price_id): use inline price_data
            if mode == "subscription":
                raise ValueError(
                    f"Missing Stripe price_id for subscription tier '{tier}'. "
                    "Set the corresponding STRIPE_PRICE_* env var."
                )
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

        create_kwargs: Dict[str, Any] = {
            "payment_method_types": ["card"],
            "mode": mode,
            "line_items": line_items,
            "success_url": success_url + "?session_id={CHECKOUT_SESSION_ID}",
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
