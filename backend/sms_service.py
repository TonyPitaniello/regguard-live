"""
SMS Service: Sends research results via Twilio SMS
Handles validation, formatting, and rate limiting
"""

import os
import logging
import re
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)


class SMSValidationError(Exception):
    """Raised when SMS validation fails"""
    pass


class SMSRateLimitError(Exception):
    """Raised when SMS rate limit is exceeded"""
    pass


class SMSService:
    """Base SMS service"""

    async def send_sms(
        self,
        phone_number: str,
        research_data: Dict[str, Any],
        user_id: str,
    ) -> Dict[str, str]:
        """Send research result via SMS"""
        raise NotImplementedError


class TwilioSMSService(SMSService):
    """Twilio SMS service for research result delivery"""

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.twilio_client = None

        try:
            from twilio.rest import Client
            self.twilio_client = Client(account_sid, auth_token)
        except ImportError:
            logger.error("twilio package not installed")
            self.twilio_client = None

    def _validate_phone_number(self, phone_number: str) -> str:
        """
        Validate and normalize phone number to E.164 format.
        Only accepts US numbers for now.

        Args:
            phone_number: Phone number in various formats

        Returns:
            Normalized phone number in E.164 format (+1XXXXXXXXXX)

        Raises:
            SMSValidationError: If phone number is invalid
        """
        # Remove all non-digit characters
        digits = re.sub(r"\D", "", phone_number)

        # Handle 10-digit US number (add country code)
        if len(digits) == 10:
            digits = "1" + digits
        # Handle 11-digit number starting with 1 (US)
        elif len(digits) == 11 and digits.startswith("1"):
            pass
        # Handle already formatted E.164 (remove leading +)
        elif phone_number.startswith("+1") and len(digits) == 11:
            pass
        else:
            raise SMSValidationError(
                f"Invalid phone number: {phone_number}. "
                "Please provide a valid US phone number (10 digits)."
            )

        # Return in E.164 format
        return f"+{digits}"

    def _format_sms_message(self, research_data: Dict[str, Any]) -> str:
        """
        Format research data into concise SMS message (≤160 chars for single SMS).

        Args:
            research_data: Research result data

        Returns:
            Formatted SMS message
        """
        project_info = research_data.get("project_info", {})
        summary = research_data.get("summary", {})
        punch_list = research_data.get("punch_list", {})

        zip_code = project_info.get("zip", "")
        city = project_info.get("city", "")
        state = project_info.get("state", "")

        high_risk = summary.get("high_risk_count", 0)
        total_cost = summary.get("estimated_total_cost", 0)
        timeline = summary.get("estimated_timeline", "TBD")
        honesty = research_data.get("honesty") or {}
        unverified = (
            research_data.get("preview")
            or summary.get("estimates_unverified")
            or not honesty.get("cost_verified")
        )
        risk_verified = honesty.get("risk_verified") is True
        cost_tag = "~" if unverified else ""
        risk_line = (
            f"⚠️  {high_risk} High Risks\n"
            if risk_verified
            else "Risk score: unavailable (preview)\n"
        )
        share = research_data.get("share_url") or ""
        if not share and research_data.get("research_id"):
            try:
                from research_store import share_url_for

                share = share_url_for(str(research_data["research_id"]))
            except Exception:
                share = "https://app.regguardagent.com/"

        # Prefer share link + short receipt (Twilio concatenates; keep under ~480)
        killers = research_data.get("margin_killers") or []
        killer_bits = []
        for k in killers[:2]:
            if isinstance(k, dict) and k.get("title"):
                killer_bits.append(str(k["title"])[:48])
        killer_line = ("; ".join(killer_bits) + "\n") if killer_bits else ""

        message = (
            f"RegGuard Bid Risk: {city}, {state} {zip_code}\n"
            f"{risk_line}"
            f"{killer_line}"
            f"💰 {cost_tag}${total_cost:,.0f}"
            f"{' (est.)' if unverified else ''}\n"
            f"Report: {share or 'https://app.regguardagent.com/'}"
        )

        if len(message) > 480:
            message = (
                f"RegGuard {city}, {state}\n"
                f"{'Est ' if unverified else ''}{cost_tag}${total_cost:,.0f}\n"
                f"{share or 'https://app.regguardagent.com/'}"
            )

        return message

    async def send_sms(
        self,
        phone_number: str,
        research_data: Dict[str, Any],
        user_id: str,
    ) -> Dict[str, str]:
        """
        Send research result via SMS using Twilio.

        Args:
            phone_number: Destination phone number
            research_data: Research result data to format
            user_id: User ID (for rate limiting checks - assumed done by caller)

        Returns:
            {
                "status": "sent",
                "message_id": "SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "phone": "+1XXXXXXXXXX"
            }

        Raises:
            SMSValidationError: If validation fails
            Exception: If Twilio API fails
        """
        if not self.twilio_client:
            raise Exception("Twilio client not initialized")

        # Validate and normalize phone number
        normalized_phone = self._validate_phone_number(phone_number)

        # Format message
        message_body = self._format_sms_message(research_data)

        logger.info(f"Sending SMS to {normalized_phone} for user {user_id}")

        try:
            # Send message via Twilio
            message = await asyncio.to_thread(
                self.twilio_client.messages.create,
                body=message_body,
                from_=self.from_number,
                to=normalized_phone,
            )

            logger.info(f"SMS sent successfully: {message.sid}")

            err_code = getattr(message, "error_code", None)
            err_msg = getattr(message, "error_message", None) or ""
            if err_code:
                raise Exception(
                    f"Twilio rejected SMS (code {err_code}): {err_msg or 'delivery failed'}. "
                    "If this is a Twilio trial account, verify the destination number in Twilio Console "
                    "or upgrade the account."
                )

            return {
                "status": "sent",
                "message_id": message.sid,
                "phone": normalized_phone,
            }

        except Exception as e:
            logger.error(f"Failed to send SMS to {normalized_phone}: {str(e)}")
            raise


class MockSMSService(SMSService):
    """Mock SMS service for testing and development"""

    def __init__(self):
        self.sent_messages = []

    def _validate_phone_number(self, phone_number: str) -> str:
        """Validate phone number format"""
        digits = re.sub(r"\D", "", phone_number)

        if len(digits) == 10:
            digits = "1" + digits
        elif len(digits) == 11 and digits.startswith("1"):
            pass
        else:
            raise SMSValidationError(
                f"Invalid phone number: {phone_number}. "
                "Please provide a valid US phone number."
            )

        return f"+{digits}"

    async def send_sms(
        self,
        phone_number: str,
        research_data: Dict[str, Any],
        user_id: str,
    ) -> Dict[str, str]:
        """Mock SMS send - returns success without actually sending"""
        normalized_phone = self._validate_phone_number(phone_number)

        message_id = f"SM{uuid.uuid4().hex[:30].upper()}"
        self.sent_messages.append(
            {
                "phone": normalized_phone,
                "user_id": user_id,
                "message_id": message_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        return {
            "status": "sent",
            "message_id": message_id,
            "phone": normalized_phone,
        }


class UnconfiguredSMSService(SMSService):
    """Fail closed when Twilio is not fully configured (never fake success in prod)."""

    def _validate_phone_number(self, phone_number: str) -> str:
        digits = re.sub(r"\D", "", phone_number)
        if len(digits) == 10:
            digits = "1" + digits
        elif len(digits) == 11 and digits.startswith("1"):
            pass
        else:
            raise SMSValidationError(
                f"Invalid phone number: {phone_number}. "
                "Please provide a valid US phone number."
            )
        return f"+{digits}"

    async def send_sms(
        self,
        phone_number: str,
        research_data: Dict[str, Any],
        user_id: str,
    ) -> Dict[str, str]:
        raise Exception(
            "SMS not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and "
            "TWILIO_FROM_NUMBER (or TWILIO_PHONE_NUMBER) on the server."
        )


def get_sms_service() -> SMSService:
    """Get SMS service instance based on environment configuration"""
    twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_from_number = (
        os.getenv("TWILIO_FROM_NUMBER") or os.getenv("TWILIO_PHONE_NUMBER") or ""
    ).strip()

    if twilio_account_sid and twilio_auth_token and twilio_from_number:
        return TwilioSMSService(twilio_account_sid, twilio_auth_token, twilio_from_number)

    allow_mock = (os.getenv("REG_GUARD_ALLOW_MOCK_SMS") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    if allow_mock:
        logger.warning("Twilio incomplete — using mock SMS (REG_GUARD_ALLOW_MOCK_SMS=1)")
        return MockSMSService()

    logger.warning(
        "Twilio incomplete (need SID + AUTH + FROM/PHONE_NUMBER) — SMS fail-closed"
    )
    return UnconfiguredSMSService()
