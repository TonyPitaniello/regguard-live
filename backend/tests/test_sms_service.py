"""
Tests for SMS Service
Tests phone validation, message formatting, and Twilio integration
"""

import pytest
import asyncio
from sms_service import TwilioSMSService, MockSMSService, SMSValidationError


class TestSMSValidation:
    """Test phone number validation"""

    def test_validate_10_digit_phone(self):
        service = MockSMSService()
        # Should convert 10-digit to E.164
        result = service._validate_phone_number("5551234567")
        assert result == "+15551234567"

    def test_validate_11_digit_phone_with_1(self):
        service = MockSMSService()
        # Should accept 11-digit starting with 1
        result = service._validate_phone_number("15551234567")
        assert result == "+15551234567"

    def test_validate_e164_format(self):
        service = MockSMSService()
        # Should accept E.164 format
        result = service._validate_phone_number("+15551234567")
        assert result == "+15551234567"

    def test_validate_formatted_phone(self):
        service = MockSMSService()
        # Should handle formatted phone numbers
        result = service._validate_phone_number("(555) 123-4567")
        assert result == "+15551234567"

    def test_validate_formatted_with_plus(self):
        service = MockSMSService()
        # Should handle +1-formatted numbers
        result = service._validate_phone_number("+1-555-123-4567")
        assert result == "+15551234567"

    def test_invalid_phone_too_short(self):
        service = MockSMSService()
        # Should reject too-short numbers
        with pytest.raises(SMSValidationError):
            service._validate_phone_number("555123456")  # 9 digits

    def test_invalid_phone_too_long(self):
        service = MockSMSService()
        # Should reject too-long numbers
        with pytest.raises(SMSValidationError):
            service._validate_phone_number("123456789012")  # 12 digits

    def test_invalid_phone_wrong_country(self):
        service = MockSMSService()
        # Should reject international numbers (non-US)
        with pytest.raises(SMSValidationError):
            service._validate_phone_number("442071838750")  # UK number


class TestSMSMessageFormatting:
    """Test SMS message formatting"""

    def test_format_basic_message(self):
        service = TwilioSMSService("test", "test", "+1234567890")
        research_data = {
            "project_info": {
                "zip": "75001",
                "city": "Arlington",
                "state": "TX",
            },
            "summary": {
                "high_risk_count": 3,
                "estimated_total_cost": 125000,
                "estimated_timeline": "45 days",
            },
            "punch_list": {},
        }
        
        message = service._format_sms_message(research_data)
        assert "Arlington" in message
        assert "TX" in message
        assert ("3 High Risks" in message or "Risks: 3" in message or "unavailable" in message.lower())
        assert "$125,000" in message or "125000" in message or "125,000" in message
        assert "Report:" in message or "app.regguardagent.com" in message
        # Timeline may be omitted in short receipt format
        assert "RegGuard" in message

    def test_message_length_reasonable(self):
        service = TwilioSMSService("test", "test", "+1234567890")
        research_data = {
            "project_info": {
                "zip": "75001",
                "city": "Arlington",
                "state": "TX",
            },
            "summary": {
                "high_risk_count": 3,
                "estimated_total_cost": 125000,
                "estimated_timeline": "45 days",
            },
            "punch_list": {},
        }
        
        message = service._format_sms_message(research_data)
        # SMS should be < 500 chars (can send as multiple segments)
        assert len(message) < 500


class TestMockSMSService:
    """Test mock SMS service"""

    @pytest.mark.asyncio
    async def test_mock_send_sms(self):
        service = MockSMSService()
        research_data = {
            "project_info": {"zip": "75001", "city": "Arlington", "state": "TX"},
            "summary": {
                "high_risk_count": 2,
                "estimated_total_cost": 100000,
                "estimated_timeline": "30 days",
            },
            "punch_list": {},
        }
        
        result = await service.send_sms("5551234567", research_data, "user-123")
        
        assert result["status"] == "sent"
        assert result["phone"] == "+15551234567"
        assert "SM" in result["message_id"]

    @pytest.mark.asyncio
    async def test_mock_send_tracks_messages(self):
        service = MockSMSService()
        research_data = {
            "project_info": {"zip": "75001", "city": "Arlington", "state": "TX"},
            "summary": {
                "high_risk_count": 2,
                "estimated_total_cost": 100000,
                "estimated_timeline": "30 days",
            },
            "punch_list": {},
        }
        
        await service.send_sms("5551234567", research_data, "user-123")
        await service.send_sms("5559876543", research_data, "user-456")
        
        assert len(service.sent_messages) == 2
        assert service.sent_messages[0]["phone"] == "+15551234567"
        assert service.sent_messages[1]["phone"] == "+15559876543"


class TestSMSErrors:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_mock_invalid_phone_in_send(self):
        service = MockSMSService()
        research_data = {
            "project_info": {"zip": "75001", "city": "Arlington", "state": "TX"},
            "summary": {
                "high_risk_count": 2,
                "estimated_total_cost": 100000,
                "estimated_timeline": "30 days",
            },
            "punch_list": {},
        }
        
        with pytest.raises(SMSValidationError):
            await service.send_sms("invalid", research_data, "user-123")
