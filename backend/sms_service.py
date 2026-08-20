"""
SMS Service: Sends research results via Twilio SMS
Handles validation, formatting, and rate limiting
"""

import os
import logging
import re
import asyncio
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)

# Common Twilio Messaging error codes → contractor-facing copy
_TWILIO_USER_HINTS: Dict[int, str] = {
    20003: "Twilio auth failed — check TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN on the server.",
    21211: "That phone number looks invalid. Use a 10-digit US mobile number.",
    21408: "SMS is not enabled for this region on the Twilio account.",
    21608: "Twilio trial can only text verified numbers. Verify this phone in Twilio Console, or upgrade the account.",
    21610: "This number has opted out of SMS (STOP). Ask them to reply START, or use email.",
    21614: "That number cannot receive SMS (landline or invalid mobile).",
    30003: "Carrier could not reach the handset (unreachable).",
    30005: "Unknown handset — number may be disconnected.",
    30006: "Landline or unreachable carrier — try a mobile number.",
    30007: "Carrier filtered the message (spam/A2P). Register US A2P 10DLC or use Open in Messages.",
    30008: "Carrier reported an unknown delivery error.",
    30034: "US A2P 10DLC not registered — carriers often block these texts until brand/campaign approval.",
}


class SMSValidationError(Exception):
    """Raised when SMS validation fails"""
    pass


class SMSRateLimitError(Exception):
    """Raised when SMS rate limit is exceeded"""
    pass


class SMSDeliveryError(Exception):
    """Twilio (or config) rejected the send — includes optional numeric error code."""

    def __init__(
        self,
        message: str,
        *,
        twilio_code: Optional[int] = None,
        user_message: Optional[str] = None,
    ):
        super().__init__(message)
        self.twilio_code = twilio_code
        self.user_message = user_message or message


def _strip_emoji(text: str) -> str:
    """Remove emoji / pictographs so carriers don't filter plain SMS bodies."""
    if not text:
        return ""
    # BMP symbols + supplemental emoji ranges + variation selectors / ZWJ
    cleaned = re.sub(
        r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U00002600-\U000026FF"
        r"\U0001F1E0-\U0001F1FF\U0000FE00-\U0000FE0F\U0000200D\U000020E3]",
        "",
        text,
    )
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def twilio_user_message(code: Optional[int], raw: str = "") -> str:
    """Map Twilio error code to a clear user-facing sentence."""
    if code is not None and code in _TWILIO_USER_HINTS:
        hint = _TWILIO_USER_HINTS[code]
        return f"Twilio error {code}: {hint}"
    if code is not None:
        base = (raw or "delivery failed").strip()
        return f"Twilio error {code}: {base}"
    return (raw or "SMS delivery failed").strip()


def _extract_twilio_code(exc: BaseException) -> Tuple[Optional[int], str]:
    """Pull numeric code + message from Twilio RestException or plain Exception."""
    code = getattr(exc, "code", None)
    if code is None:
        code = getattr(exc, "status", None)
    try:
        code_i = int(code) if code is not None else None
    except (TypeError, ValueError):
        code_i = None
    msg = str(getattr(exc, "msg", None) or getattr(exc, "message", None) or exc).strip()
    # Also parse "Twilio rejected SMS (code 21608): ..."
    if code_i is None:
        m = re.search(r"(?:code|error)\s*[:=]?\s*(\d{4,5})", msg, re.I)
        if m:
            code_i = int(m.group(1))
    return code_i, msg


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
        try:
            total_cost = float(summary.get("estimated_total_cost") or 0)
        except (TypeError, ValueError):
            total_cost = 0.0
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
            f"{high_risk} High Risks\n"
            if risk_verified
            else "Risk score: unavailable (preview)\n"
        )
        share = research_data.get("share_url") or ""
        if not share and research_data.get("research_id"):
            try:
                from research_store import resolve_forward_share_url, share_url_for

                share = resolve_forward_share_url(research_data) or share_url_for(
                    str(research_data["research_id"])
                )
            except Exception:
                share = ""

        # Prefer share link + short receipt (Twilio concatenates; keep under ~480)
        killers = research_data.get("margin_killers") or []
        killer_bits = []
        for k in killers[:2]:
            if isinstance(k, dict) and k.get("title"):
                killer_bits.append(_strip_emoji(str(k["title"]))[:48])
        killer_line = ("; ".join(killer_bits) + "\n") if killer_bits else ""

        report_line = f"Report: {share}" if share else "Report: open Reg Guard results (share link missing)"
        message = (
            f"RegGuard Bid Risk: {city}, {state} {zip_code}\n"
            f"{risk_line}"
            f"{killer_line}"
            f"{cost_tag}${total_cost:,.0f}"
            f"{' (est.)' if unverified else ''}\n"
            f"{report_line}"
        )

        if len(message) > 480:
            message = (
                f"RegGuard {city}, {state}\n"
                f"{'Est ' if unverified else ''}{cost_tag}${total_cost:,.0f}\n"
                f"{share or 'app.regguardagent.com'}"
            )

        return _strip_emoji(message)

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
            SMSDeliveryError: If Twilio rejects / fails the send
        """
        if not self.twilio_client:
            raise SMSDeliveryError(
                "Twilio client not initialized",
                user_message=(
                    "SMS not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and "
                    "TWILIO_FROM_NUMBER on the server."
                ),
            )

        # Validate and normalize phone number
        normalized_phone = self._validate_phone_number(phone_number)

        # Format message (plain text — no emoji)
        message_body = self._format_sms_message(research_data)

        logger.info(f"Sending SMS to {normalized_phone} for user {user_id}")

        try:
            message = await asyncio.to_thread(
                self.twilio_client.messages.create,
                body=message_body,
                from_=self.from_number,
                to=normalized_phone,
            )

            logger.info(f"SMS accepted by Twilio: {message.sid}")

            err_code = getattr(message, "error_code", None)
            err_msg = getattr(message, "error_message", None) or ""
            if err_code:
                try:
                    code_i = int(err_code)
                except (TypeError, ValueError):
                    code_i = None
                user = twilio_user_message(code_i, err_msg)
                raise SMSDeliveryError(
                    f"Twilio rejected SMS (code {err_code}): {err_msg or 'delivery failed'}",
                    twilio_code=code_i,
                    user_message=user,
                )

            return {
                "status": "accepted",  # Twilio queued — not handset-confirmed
                "message_id": message.sid,
                "phone": normalized_phone,
                "twilio_status": getattr(message, "status", None) or "queued",
            }

        except SMSDeliveryError:
            raise
        except SMSValidationError:
            raise
        except Exception as e:
            code_i, raw = _extract_twilio_code(e)
            user = twilio_user_message(code_i, raw)
            logger.error(f"Failed to send SMS to {normalized_phone}: {user}")
            raise SMSDeliveryError(raw or str(e), twilio_code=code_i, user_message=user) from e


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
        raise SMSDeliveryError(
            "SMS not configured",
            user_message=(
                "SMS not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and "
                "TWILIO_FROM_NUMBER (or TWILIO_PHONE_NUMBER) on the server."
            ),
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
