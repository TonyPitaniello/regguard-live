"""
Result Delivery Service: Handles SMS and Email delivery of research results
Includes rate limiting, validation, and database tracking
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from uuid import UUID
import uuid

from sms_service import (
    get_sms_service,
    SMSValidationError,
    SMSRateLimitError,
    SMSDeliveryError,
)
from email_service import get_email_service

logger = logging.getLogger(__name__)


class DeliveryRateLimitError(Exception):
    """Raised when delivery rate limit is exceeded"""
    pass


class ResultDeliveryService:
    """Service for delivering research results via SMS and email"""

    def __init__(self, db_pool=None):
        """
        Initialize delivery service

        Args:
            db_pool: Optional database connection pool (Supabase)
        """
        self.db_pool = db_pool
        self.sms_service = get_sms_service()
        self.email_service = get_email_service()

        # Rate limits (per hour)
        self.SMS_RATE_LIMIT = 3  # 3 SMS per hour
        self.EMAIL_RATE_LIMIT = 5  # 5 emails per hour

    async def check_rate_limit(
        self,
        user_id: str,
        delivery_method: str,
    ) -> None:
        """
        Check if user has exceeded rate limit for delivery method

        Args:
            user_id: User ID
            delivery_method: 'sms' or 'email'

        Raises:
            DeliveryRateLimitError: If rate limit exceeded
        """
        if not self.db_pool:
            logger.warning("Database pool not available, skipping rate limit check")
            return

        try:
            # Get current hour slot
            now = datetime.utcnow()
            hour_slot = now.replace(minute=0, second=0, microsecond=0)

            # Query rate limit tracking
            query = """
                SELECT count FROM delivery_rate_limits
                WHERE user_id = %s AND delivery_method = %s AND hour_slot = %s
            """

            async with self.db_pool.acquire() as conn:
                result = await conn.fetchrow(query, UUID(user_id), delivery_method, hour_slot)

            current_count = result["count"] if result else 0

            # Check limit
            limit = self.SMS_RATE_LIMIT if delivery_method == "sms" else self.EMAIL_RATE_LIMIT
            if current_count >= limit:
                reset_time = hour_slot + timedelta(hours=1)
                minutes_until_reset = int((reset_time - now).total_seconds() / 60)
                raise DeliveryRateLimitError(
                    f"Rate limit exceeded. Try again in {minutes_until_reset} minutes."
                )

        except DeliveryRateLimitError:
            raise
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            # Don't fail the delivery if rate limit check fails
            pass

    async def increment_rate_limit(
        self,
        user_id: str,
        delivery_method: str,
    ) -> None:
        """
        Increment rate limit counter

        Args:
            user_id: User ID
            delivery_method: 'sms' or 'email'
        """
        if not self.db_pool:
            return

        try:
            now = datetime.utcnow()
            hour_slot = now.replace(minute=0, second=0, microsecond=0)

            # Upsert rate limit record
            query = """
                INSERT INTO delivery_rate_limits (user_id, delivery_method, hour_slot, count, created_at, updated_at)
                VALUES (%s, %s, %s, 1, now(), now())
                ON CONFLICT(user_id, delivery_method, hour_slot)
                DO UPDATE SET count = count + 1, updated_at = now()
            """

            async with self.db_pool.acquire() as conn:
                await conn.execute(query, UUID(user_id), delivery_method, hour_slot)

        except Exception as e:
            logger.error(f"Error incrementing rate limit: {str(e)}")

    async def track_delivery(
        self,
        research_id: Optional[str],
        user_id: str,
        delivery_method: str,
        destination: str,
        status: str,
        service_message_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Track delivery in database

        Args:
            research_id: Research result ID (optional)
            user_id: User ID
            delivery_method: 'sms' or 'email'
            destination: Phone number or email address
            status: 'pending', 'sent', or 'failed'
            service_message_id: Message ID from service (Twilio SID, SendGrid ID)
            error_message: Error details if failed

        Returns:
            Delivery record
        """
        if not self.db_pool:
            logger.warning("Database pool not available, skipping delivery tracking")
            return {"id": str(uuid.uuid4()), "status": status}

        try:
            delivery_id = str(uuid.uuid4())

            query = """
                INSERT INTO result_deliveries
                (id, research_id, user_id, delivery_method, destination, status, service_message_id, error_message, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now(), now())
                RETURNING id, research_id, status, created_at
            """

            async with self.db_pool.acquire() as conn:
                result = await conn.fetchrow(
                    query,
                    UUID(delivery_id),
                    UUID(research_id) if research_id else None,
                    UUID(user_id),
                    delivery_method,
                    destination,
                    status,
                    service_message_id,
                    error_message,
                )

            return {
                "id": str(result["id"]),
                "research_id": str(result["research_id"]) if result["research_id"] else None,
                "status": result["status"],
                "created_at": result["created_at"].isoformat() if result["created_at"] else None,
            }

        except Exception as e:
            logger.error(f"Error tracking delivery: {str(e)}")
            return {"id": delivery_id, "status": status, "error": str(e)}

    async def send_sms(
        self,
        phone_number: str,
        research_data: Dict[str, Any],
        user_id: str,
        research_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send research result via SMS

        Args:
            phone_number: Destination phone number
            research_data: Research result data
            user_id: User ID
            research_id: Research ID (optional)

        Returns:
            {
                "status": "sent" | "failed",
                "message_id": "...",
                "phone": "...",
                "error": "..." (if failed)
            }
        """
        try:
            # Check rate limit
            await self.check_rate_limit(user_id, "sms")

            # Send SMS
            result = await self.sms_service.send_sms(phone_number, research_data, user_id)

            # Increment rate limit
            await self.increment_rate_limit(user_id, "sms")

            # Track delivery
            delivery = await self.track_delivery(
                research_id=research_id,
                user_id=user_id,
                delivery_method="sms",
                destination=result["phone"],
                status="sent",
                service_message_id=result.get("message_id"),
            )

            return {
                "status": "sent",
                "message_id": result.get("message_id"),
                "phone": result.get("phone"),
                "delivery_id": delivery.get("id"),
            }

        except DeliveryRateLimitError as e:
            logger.warning(f"SMS rate limit: {str(e)}")
            await self.track_delivery(
                research_id=research_id,
                user_id=user_id,
                delivery_method="sms",
                destination=phone_number,
                status="failed",
                error_message=str(e),
            )
            return {
                "status": "failed",
                "error": str(e),
            }

        except SMSValidationError as e:
            logger.error(f"SMS validation error: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
            }

        except SMSDeliveryError as e:
            logger.error(f"SMS delivery error: {e.user_message}")
            await self.track_delivery(
                research_id=research_id,
                user_id=user_id,
                delivery_method="sms",
                destination=phone_number,
                status="failed",
                error_message=e.user_message,
            )
            out: Dict[str, Any] = {
                "status": "failed",
                "error": e.user_message,
            }
            if e.twilio_code is not None:
                out["twilio_code"] = e.twilio_code
            return out

        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            await self.track_delivery(
                research_id=research_id,
                user_id=user_id,
                delivery_method="sms",
                destination=phone_number,
                status="failed",
                error_message=str(e),
            )
            return {
                "status": "failed",
                "error": f"Failed to send SMS: {str(e)}",
            }

    async def send_email(
        self,
        email_address: str,
        research_data: Dict[str, Any],
        user_id: str,
        research_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send research result via email

        Args:
            email_address: Destination email address
            research_data: Research result data
            user_id: User ID
            research_id: Research ID (optional)

        Returns:
            {
                "status": "sent" | "failed",
                "email_id": "...",
                "email": "...",
                "error": "..." (if failed)
            }
        """
        try:
            # Check rate limit
            await self.check_rate_limit(user_id, "email")

            # Validate email format (basic)
            if not self._validate_email(email_address):
                raise ValueError("Invalid email format")

            if not self.email_service:
                raise Exception(
                    "Email service not configured. Set RESEND_API_KEY or SENDGRID_API_KEY on the server."
                )

            # Send email
            result = await self.email_service.send_research_result(email_address, research_data)

            # Increment rate limit
            await self.increment_rate_limit(user_id, "email")

            # Track delivery
            delivery = await self.track_delivery(
                research_id=research_id,
                user_id=user_id,
                delivery_method="email",
                destination=result.get("email"),
                status="sent",
                service_message_id=result.get("email_id"),
            )

            return {
                "status": "sent",
                "email_id": result.get("email_id"),
                "email": result.get("email"),
                "delivery_id": delivery.get("id"),
            }

        except DeliveryRateLimitError as e:
            logger.warning(f"Email rate limit: {str(e)}")
            await self.track_delivery(
                research_id=research_id,
                user_id=user_id,
                delivery_method="email",
                destination=email_address,
                status="failed",
                error_message=str(e),
            )
            return {
                "status": "failed",
                "error": str(e),
            }

        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            await self.track_delivery(
                research_id=research_id,
                user_id=user_id,
                delivery_method="email",
                destination=email_address,
                status="failed",
                error_message=str(e),
            )
            return {
                "status": "failed",
                "error": f"Failed to send email: {str(e)}",
            }

    @staticmethod
    def _validate_email(email: str) -> bool:
        """Basic email validation"""
        import re
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None


def get_delivery_service(db_pool=None) -> ResultDeliveryService:
    """Get result delivery service instance"""
    return ResultDeliveryService(db_pool)
