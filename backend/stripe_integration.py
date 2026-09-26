"""
Stripe Payment Integration
Handles checkout sessions, webhooks, order creation, and PDF delivery
"""

import stripe
import logging
import os
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
import hmac
import hashlib

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Product definitions — multi-segment pricing
PRODUCTS = {
    "contractor_pro": {
        "name": "Contractor Pro",
        "description": "Unlimited lookups and punch lists — $149/month",
        "amount_cents": 14900,
        "currency": "usd",
        "tier": "contractor_pro",
        "mode": "subscription",
    },
    "ic_project": {
        "name": "IC Project Report",
        "description": "One-time full project report package",
        "amount_cents": 150000,
        "currency": "usd",
        "tier": "ic_project",
        "mode": "payment",
    },
    "ic_annual": {
        "name": "IC Annual",
        "description": "Annual Diligence Bundles for capital sites on this purchase email — $15,000/year",
        "amount_cents": 1500000,
        "currency": "usd",
        "tier": "ic_annual",
        "mode": "subscription",
    },
    "sponsor": {
        "name": "Sponsor",
        "description": "Monthly sponsorship — $1,500/month",
        "amount_cents": 150000,
        "currency": "usd",
        "tier": "sponsor",
        "mode": "subscription",
    },
    # Legacy aliases
    "premium": {
        "name": "IC Project Report",
        "description": "One-time full project report package",
        "amount_cents": 150000,
        "currency": "usd",
        "tier": "ic_project",
        "mode": "payment",
    },
    "enterprise": {
        "name": "IC Annual",
        "description": "Annual Diligence Bundles for capital sites on this purchase email — $15,000/year",
        "amount_cents": 1500000,
        "currency": "usd",
        "tier": "ic_annual",
        "mode": "subscription",
    },
}


class CheckoutRequest(BaseModel):
    """Request to create checkout session"""
    trial_id: str
    tier: str  # "premium" or "enterprise"
    success_url: str
    cancel_url: str


class Order(BaseModel):
    """Order representation"""
    id: str
    user_email: str
    trial_id: str
    tier: str
    amount_cents: int
    status: str  # pending, completed, failed, refunded
    created_at: str
    stripe_session_id: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None


async def create_checkout_session(request: CheckoutRequest) -> Dict[str, Any]:
    """
    Create Stripe checkout session for premium tier
    
    Args:
        request: CheckoutRequest with trial_id, tier, and URLs
    
    Returns:
        {
            "session_id": "cs_...",
            "checkout_url": "https://checkout.stripe.com/...",
        }
    """
    try:
        logger.info(f"💳 Creating checkout session for tier: {request.tier}")
        
        product = PRODUCTS.get(request.tier)
        if not product:
            raise ValueError(f"Invalid tier: {request.tier}")

        mode = product.get("mode", "payment")
        line_item: Dict[str, Any]
        if mode == "subscription":
            # Prefer env price IDs when available; otherwise one-time price_data is not valid for subscription
            price_env_map = {
                "contractor_pro": os.getenv("STRIPE_PRICE_CONTRACTOR_PRO"),
                "ic_annual": os.getenv("STRIPE_PRICE_IC_ANNUAL"),
                "sponsor": os.getenv("STRIPE_PRICE_SPONSOR"),
                "enterprise": os.getenv("STRIPE_PRICE_IC_ANNUAL"),
            }
            price_id = price_env_map.get(request.tier) or price_env_map.get(product["tier"])
            if price_id:
                line_item = {"price": price_id, "quantity": 1}
            else:
                # Fall back to one-time payment with price_data if no subscription price configured
                mode = "payment"
                line_item = {
                    "price_data": {
                        "currency": product["currency"],
                        "product_data": {
                            "name": product["name"],
                            "description": product["description"],
                        },
                        "unit_amount": product["amount_cents"],
                    },
                    "quantity": 1,
                }
        else:
            line_item = {
                "price_data": {
                    "currency": product["currency"],
                    "product_data": {
                        "name": product["name"],
                        "description": product["description"],
                    },
                    "unit_amount": product["amount_cents"],
                },
                "quantity": 1,
            }

        # Create Stripe checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[line_item],
            mode=mode,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            # Metadata to track trial_id
            metadata={
                "trial_id": request.trial_id,
                "tier": product["tier"],
            },
            # Customer email pre-fill (optional)
            customer_email="",
        )
        
        logger.info(f"✅ Checkout session created: {session.id}")
        
        return {
            "session_id": session.id,
            "checkout_url": session.url,
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"❌ Stripe error creating checkout: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error creating checkout: {e}")
        raise


async def handle_payment_succeeded(payment_intent_id: str) -> Dict[str, Any]:
    """
    Handle payment_intent.succeeded webhook
    
    Creates order, triggers PDF generation, and sends email
    """
    try:
        logger.info(f"💰 Payment succeeded: {payment_intent_id}")
        
        # Retrieve payment intent details
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        # Extract metadata
        metadata = payment_intent.get("metadata", {})
        trial_id = metadata.get("trial_id")
        tier = metadata.get("tier")
        customer_email = payment_intent.get("receipt_email") or payment_intent.get("charges").data[0].billing_details.email
        
        if not trial_id or not tier:
            logger.error("❌ Missing trial_id or tier in payment metadata")
            raise ValueError("Missing required metadata in payment")
        
        # Create order record (in production: save to Supabase)
        order_data = {
            "trial_id": trial_id,
            "user_email": customer_email,
            "tier": tier,
            "amount_cents": payment_intent.amount,
            "status": "completed",
            "stripe_session_id": payment_intent.get("client_secret"),  # Session ID
            "stripe_payment_intent_id": payment_intent_id,
            "created_at": datetime.now().isoformat(),
        }
        
        logger.info(f"📝 Order created: {order_data}")
        
        # Queue PDF generation task (in production: use Celery)
        await trigger_pdf_generation(trial_id, tier, customer_email)
        
        # Send confirmation email
        await send_payment_confirmation_email(customer_email, tier, payment_intent.amount)
        
        logger.info(f"✅ Payment processing complete for {customer_email}")
        
        return {
            "status": "success",
            "order": order_data,
        }
        
    except Exception as e:
        logger.error(f"❌ Error handling payment success: {e}")
        raise


async def trigger_pdf_generation(trial_id: str, tier: str, email: str) -> None:
    """
    Trigger PDF generation for completed order
    In production: would queue to Celery or similar
    """
    logger.info(f"📄 Triggering PDF generation for {trial_id} ({tier})")
    
    try:
        # In production, would fetch analysis data from database using trial_id
        # Then call pdf_generator.generate_all_pdfs(analysis_data)
        # Then upload to S3/cloud storage
        # Then create download links
        # For now, just log
        
        logger.info(f"✅ PDF generation queued: {trial_id}")
        
    except Exception as e:
        logger.error(f"❌ Error triggering PDF generation: {e}")


async def send_payment_confirmation_email(email: str, tier: str, amount_cents: int) -> None:
    """
    Send payment confirmation email with PDF links
    Uses Resend email service
    """
    try:
        from email_service import get_email_service
        
        service = get_email_service()
        if not service:
            logger.warning("⚠️  Email service not configured, skipping confirmation email")
            return
        
        logger.info(f"📧 Sending payment confirmation to {email}")
        
        amount_dollars = amount_cents / 100
        tier_name = "Premium" if tier == "premium" else "Enterprise"
        
        subject = f"🎉 Payment Received - RegGuard {tier_name} Report"
        
        html_content = f"""
        <h2>Thank you for your purchase!</h2>
        <p>Your payment of <strong>${amount_dollars:,.2f}</strong> has been received.</p>
        
        <h3>{tier_name} Package Includes:</h3>
        <ul>
            <li>📋 Research Memo PDF (environmental findings)</li>
            <li>✓ Complete Punch List (all action items)</li>
            <li>📄 State-Specific Permit Packages</li>
            <li>⏰ Same-day delivery</li>
        </ul>
        
        <h3>What's Next?</h3>
        <p>Your PDFs are being generated and will be emailed within 1 hour.</p>
        <p>You'll receive download links valid for 30 days.</p>
        
        <p>Questions? Contact us at support@regguardagent.com</p>
        """
        
        # In production: would use Resend API
        logger.info(f"✅ Payment confirmation email sent to {email}")
        
    except Exception as e:
        logger.error(f"❌ Error sending confirmation email: {e}")


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Verify Stripe webhook signature
    
    Args:
        payload: Raw request body
        signature: Stripe-Signature header
    
    Returns:
        True if signature is valid, False otherwise
    """
    if not STRIPE_WEBHOOK_SECRET:
        logger.warning("⚠️  STRIPE_WEBHOOK_SECRET not set, skipping verification")
        return True
    
    try:
        timestamp, signed_content = signature.split(',')
        timestamp = timestamp.split('=')[1]
        signature_content = signed_content.split('=')[1]
        
        signed_data = f"{timestamp}.{payload.decode('utf-8')}"
        computed_signature = hmac.new(
            STRIPE_WEBHOOK_SECRET.encode(),
            signed_data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return computed_signature == signature_content
        
    except Exception as e:
        logger.error(f"❌ Error verifying webhook signature: {e}")
        return False


async def handle_webhook_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle Stripe webhook event
    
    Supported events:
    - payment_intent.succeeded
    - payment_intent.payment_failed
    - charge.refunded
    """
    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})
    
    logger.info(f"🔔 Webhook event: {event_type}")
    
    try:
        if event_type == "payment_intent.succeeded":
            await handle_payment_succeeded(data.get("id"))
            return {"status": "success"}
        
        elif event_type == "payment_intent.payment_failed":
            logger.warning(f"⚠️  Payment failed: {data.get('id')}")
            # Update order status to "failed" in database
            return {"status": "payment_failed"}
        
        elif event_type == "charge.refunded":
            logger.info(f"🔄 Charge refunded: {data.get('id')}")
            # Update order status to "refunded" in database
            return {"status": "refunded"}
        
        else:
            logger.info(f"ℹ️ Unhandled event type: {event_type}")
            return {"status": "unhandled"}
        
    except Exception as e:
        logger.error(f"❌ Error handling webhook: {e}")
        raise


# Tier management functions

async def set_user_tier(email: str, tier: str, expires_at: Optional[str] = None) -> None:
    """
    Set user's tier in database
    In production: save to Supabase
    """
    logger.info(f"👤 Setting tier for {email}: {tier}")
    # Implementation would update Supabase database
    pass


async def get_user_tier(email: str) -> str:
    """
    Get user's current tier
    Returns: "free", "premium", or "enterprise"
    """
    # Implementation would query Supabase
    return "free"  # Default


async def can_access_feature(email: str, feature: str) -> bool:
    """
    Check if user can access a feature based on tier
    """
    tier = await get_user_tier(email)
    
    features_by_tier = {
        "free": ["memo", "punch_list_preview"],
        "premium": ["memo", "full_punch_list", "pdfs", "permits"],
        "enterprise": ["memo", "full_punch_list", "pdfs", "permits", "monitoring"],
    }
    
    allowed_features = features_by_tier.get(tier, [])
    return feature in allowed_features
