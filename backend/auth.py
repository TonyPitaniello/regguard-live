"""
Reg Guard — User authentication, onboarding, and payment gateway via Stripe.

Handles:
- Stripe Checkout Session creation for 14-day free trial signups
- Webhook listener for checkout.session.completed events
- Supabase account creation + profile population on successful payment
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from typing import Any, Dict, Optional

try:
    import stripe
except ImportError:
    stripe = None  # type: ignore[misc,assignment]

try:
    from supabase import create_client
except ImportError:
    create_client = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def _stripe_key() -> str:
    """Get Stripe secret key from environment."""
    key = (os.environ.get("STRIPE_SECRET_KEY") or "").strip()
    if not key:
        raise ValueError(
            "STRIPE_SECRET_KEY is not set. "
            "Set this environment variable to enable Stripe payment processing."
        )
    return key


def _stripe_webhook_secret() -> str:
    """Get Stripe webhook signing secret from environment."""
    secret = (os.environ.get("STRIPE_WEBHOOK_SECRET") or "").strip()
    if not secret:
        raise ValueError(
            "STRIPE_WEBHOOK_SECRET is not set. "
            "Set this environment variable to verify Stripe webhook signatures."
        )
    return secret


def _supabase_client():
    """Get initialized Supabase client."""
    if create_client is None:
        raise ImportError("supabase package not installed")
    
    url = (os.environ.get("SUPABASE_URL") or "").strip()
    key = (os.environ.get("SUPABASE_KEY") or "").strip()
    
    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY are required. "
            "Set these environment variables to enable Supabase integration."
        )
    
    return create_client(url, key)


def stripe_configured() -> bool:
    """Check if Stripe is properly configured."""
    return (
        stripe is not None
        and (os.environ.get("STRIPE_SECRET_KEY") or "").strip() != ""
        and (os.environ.get("STRIPE_WEBHOOK_SECRET") or "").strip() != ""
    )


async def create_checkout_session(
    email: str,
    password: str,
    company_name: str,
    success_url: str = "https://app.regguardagent.com/checkout/success",
    cancel_url: str = "https://app.regguardagent.com/pricing",
) -> Dict[str, Any]:
    """
    Create a Stripe Checkout Session for the 14-day free trial.
    
    Returns a dict with the checkout session URL.
    Raises ValueError or stripe exceptions on failure.
    """
    if not stripe_configured():
        raise ValueError("Stripe is not configured. Set STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET.")
    
    if not email or not password or not company_name:
        raise ValueError("Email, password, and company_name are required.")
    
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    
    if not create_client:
        raise ValueError("Supabase integration is not available.")
    
    try:
        stripe.api_key = _stripe_key()
        
        # Create Checkout Session with 14-day free trial
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            line_items=[
                {
                    "price": (os.environ.get("STRIPE_PRICE_ID") or "").strip(),
                    "quantity": 1,
                }
            ],
            subscription_data={
                "trial_period_days": 14,
                "items": [
                    {
                        "price": (os.environ.get("STRIPE_PRICE_ID") or "").strip(),
                    }
                ],
            },
            metadata={
                "email": email,
                "password_hash": hashlib.sha256(password.encode()).hexdigest(),
                "company_name": company_name,
            },
        )
        
        return {
            "checkout_url": session.url,
            "session_id": session.id,
        }
    
    except stripe.error.CardError as e:
        logger.error(f"Stripe card error: {e}")
        raise ValueError(f"Card error: {e.user_message}") from e
    except stripe.error.RateLimitError as e:
        logger.error(f"Stripe rate limit: {e}")
        raise ValueError("Stripe service temporarily unavailable. Please try again.") from e
    except stripe.error.InvalidRequestError as e:
        logger.error(f"Stripe invalid request: {e}")
        raise ValueError(f"Invalid checkout request: {e.user_message}") from e
    except stripe.error.AuthenticationError as e:
        logger.error(f"Stripe authentication error: {e}")
        raise ValueError("Stripe authentication failed. Contact support.") from e
    except stripe.error.APIConnectionError as e:
        logger.error(f"Stripe API connection error: {e}")
        raise ValueError("Cannot connect to Stripe. Please try again.") from e
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        raise ValueError(f"Checkout failed: {str(e)}") from e


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


async def handle_checkout_session_completed(session_id: str) -> Dict[str, Any]:
    """
    Handle checkout.session.completed webhook event.
    
    1. Retrieve the session from Stripe
    2. Extract email, company_name from metadata
    3. Create Supabase auth user
    4. Populate public.profiles row with company_name
    5. Return success status
    """
    if not stripe_configured():
        raise ValueError("Stripe is not configured.")
    
    try:
        stripe.api_key = _stripe_key()
        session = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.StripeError as e:
        logger.error(f"Failed to retrieve Stripe session: {e}")
        raise ValueError(f"Failed to retrieve checkout session: {str(e)}") from e
    
    # Extract metadata
    metadata = session.metadata or {}
    email = metadata.get("email", "")
    company_name = metadata.get("company_name", "")
    password_hash = metadata.get("password_hash", "")
    
    if not email or not company_name:
        raise ValueError("Email or company_name missing from Stripe session metadata.")
    
    # Create Supabase auth user
    try:
        sb = _supabase_client()
        
        # Auth signup (this will fail if user already exists)
        auth_response = sb.auth.sign_up(
            {"email": email, "password": password_hash[:20]}  # Use truncated hash for now
        )
        
        user_id = auth_response.user.id if auth_response.user else None
        if not user_id:
            raise ValueError("Failed to create Supabase user.")
        
        # Create profile entry with company_name
        profile_response = sb.table("profiles").insert(
            {
                "id": user_id,
                "email": email,
                "company_name": company_name,
                "trial_active": True,
                "trial_expires_at": None,  # Calculated by Stripe
            }
        ).execute()
        
        logger.info(f"Successfully created user {user_id} with company {company_name}")
        
        return {
            "success": True,
            "user_id": user_id,
            "email": email,
            "company_name": company_name,
        }
    
    except Exception as e:
        logger.error(f"Failed to create Supabase user: {e}")
        raise ValueError(f"Account creation failed: {str(e)}") from e
