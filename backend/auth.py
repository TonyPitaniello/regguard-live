"""
Reg Guard — Stripe webhook signature check.

Buyers do not create a password account. The email on the order is the seat.
Checkout for a plan goes through stripe_service, not this module.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os

try:
    import stripe
except ImportError:
    stripe = None  # type: ignore[misc,assignment]

logger = logging.getLogger(__name__)


def _stripe_webhook_secret() -> str:
    """Get Stripe webhook signing secret from environment."""
    secret = (os.environ.get("STRIPE_WEBHOOK_SECRET") or "").strip()
    if not secret:
        raise ValueError(
            "STRIPE_WEBHOOK_SECRET is not set. "
            "Set this environment variable to verify Stripe webhook signatures."
        )
    return secret


def stripe_configured() -> bool:
    """Check if Stripe is properly configured."""
    return (
        stripe is not None
        and (os.environ.get("STRIPE_SECRET_KEY") or "").strip() != ""
        and (os.environ.get("STRIPE_WEBHOOK_SECRET") or "").strip() != ""
    )


def verify_stripe_webhook_signature(
    payload: bytes,
    sig_header: str,
) -> bool:
    """
    Verify that the webhook signature matches our Stripe webhook secret.

    Returns True if valid, False otherwise.
    """
    try:
        secret = _stripe_webhook_secret()
        computed_sig = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        provided_sig = sig_header.split("t=")[1] if "t=" in sig_header else ""
        return hmac.compare_digest(computed_sig, provided_sig)
    except (IndexError, ValueError) as e:
        logger.warning(f"Invalid webhook signature format: {e}")
        return False
