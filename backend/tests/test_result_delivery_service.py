"""
Tests for Result Delivery Service
Tests rate limiting, delivery tracking, and end-to-end flow
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta
import asyncio

os.environ["REG_GUARD_ALLOW_MOCK_SMS"] = "1"

from result_delivery_service import ResultDeliveryService, DeliveryRateLimitError
from sms_service import MockSMSService


@pytest.fixture(autouse=True)
def _allow_mock_sms(monkeypatch):
    monkeypatch.setenv("REG_GUARD_ALLOW_MOCK_SMS", "1")
    # Force delivery service to pick MockSMSService even if Twilio envs exist in shell
    monkeypatch.setattr(
        "result_delivery_service.get_sms_service",
        lambda: MockSMSService(),
    )


class MockDatabase:
    """Mock database for testing"""

    def __init__(self):
        self.rate_limits = {}
        self.deliveries = []

    async def fetchrow(self, query: str, *args):
        """Mock fetchrow"""
        if "delivery_rate_limits" in query and "SELECT count" in query:
            user_id, method, hour_slot = args[0], args[1], args[2]
            key = f"{user_id}:{method}:{hour_slot}"
            if key in self.rate_limits:
                return {"count": self.rate_limits[key]}
            return None
        return None

    async def execute(self, query: str, *args):
        """Mock execute"""
        if "INSERT INTO delivery_rate_limits" in query:
            user_id, method, hour_slot = args[0], args[1], args[2]
            key = f"{user_id}:{method}:{hour_slot}"
            if key in self.rate_limits:
                self.rate_limits[key] += 1
            else:
                self.rate_limits[key] = 1

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockDatabasePool:
    """Mock database pool"""

    def __init__(self, db=None):
        self.db = db or MockDatabase()

    async def acquire(self):
        return self.db


class TestRateLimiting:
    """Test rate limiting functionality"""

    @pytest.mark.asyncio
    async def test_sms_rate_limit_not_exceeded(self):
        """Test that rate limit check passes when under limit"""
        pool = MockDatabasePool()
        service = ResultDeliveryService(db_pool=pool)

        # Should not raise - under limit
        await service.check_rate_limit("user-123", "sms")

    @pytest.mark.asyncio
    async def test_sms_rate_limit_increment(self):
        """Test rate limit counter increments"""
        pool = MockDatabasePool()
        service = ResultDeliveryService(db_pool=pool)

        user_id = "user-123"
        method = "sms"

        # Increment once
        await service.increment_rate_limit(user_id, method)

        # Check it was incremented
        db = pool.db
        now = datetime.utcnow()
        hour_slot = now.replace(minute=0, second=0, microsecond=0)
        key = f"{user_id}:{method}:{hour_slot}"

        assert key in db.rate_limits
        assert db.rate_limits[key] == 1

    @pytest.mark.asyncio
    async def test_email_rate_limit_not_exceeded(self):
        """Test that email rate limit check passes when under limit"""
        pool = MockDatabasePool()
        service = ResultDeliveryService(db_pool=pool)

        # Should not raise - under limit
        await service.check_rate_limit("user-456", "email")

    @pytest.mark.asyncio
    async def test_rate_limit_multiple_increments(self):
        """Test rate limit increments multiple times"""
        pool = MockDatabasePool()
        service = ResultDeliveryService(db_pool=pool)

        user_id = "user-789"
        method = "sms"

        # Increment 3 times
        for _ in range(3):
            await service.increment_rate_limit(user_id, method)

        # Check final count
        db = pool.db
        now = datetime.utcnow()
        hour_slot = now.replace(minute=0, second=0, microsecond=0)
        key = f"{user_id}:{method}:{hour_slot}"

        assert db.rate_limits[key] == 3


class TestDeliveryTracking:
    """Test delivery tracking"""

    @pytest.mark.asyncio
    async def test_track_delivery_sms_sent(self):
        """Test tracking SMS delivery"""
        pool = MockDatabasePool()
        service = ResultDeliveryService(db_pool=pool)

        delivery = await service.track_delivery(
            research_id="research-123",
            user_id="user-123",
            delivery_method="sms",
            destination="+15551234567",
            status="sent",
            service_message_id="SM123456",
        )

        assert delivery["status"] == "sent"
        assert "id" in delivery

    @pytest.mark.asyncio
    async def test_track_delivery_email_failed(self):
        """Test tracking failed email delivery"""
        pool = MockDatabasePool()
        service = ResultDeliveryService(db_pool=pool)

        delivery = await service.track_delivery(
            research_id="research-456",
            user_id="user-456",
            delivery_method="email",
            destination="user@example.com",
            status="failed",
            error_message="Invalid email address",
        )

        assert delivery["status"] == "failed"
        assert "id" in delivery


class TestSMSDeliveryFlow:
    """Test end-to-end SMS delivery"""

    @pytest.mark.asyncio
    async def test_send_sms_success(self):
        """Test successful SMS delivery"""
        pool = MockDatabasePool()
        service = ResultDeliveryService(db_pool=pool)

        research_data = {
            "project_info": {
                "zip": "75001",
                "city": "Arlington",
                "state": "TX",
            },
            "summary": {
                "high_risk_count": 2,
                "estimated_total_cost": 100000,
                "estimated_timeline": "30 days",
            },
            "punch_list": {},
        }

        result = await service.send_sms(
            phone_number="5551234567",
            research_data=research_data,
            user_id="user-123",
            research_id="research-123",
        )

        assert result["status"] == "sent"
        assert result["phone"] == "+15551234567"
        assert "message_id" in result
        assert "delivery_id" in result

    @pytest.mark.asyncio
    async def test_send_sms_invalid_phone(self):
        """Test SMS with invalid phone number"""
        pool = MockDatabasePool()
        service = ResultDeliveryService(db_pool=pool)

        research_data = {
            "project_info": {
                "zip": "75001",
                "city": "Arlington",
                "state": "TX",
            },
            "summary": {
                "high_risk_count": 2,
                "estimated_total_cost": 100000,
                "estimated_timeline": "30 days",
            },
            "punch_list": {},
        }

        result = await service.send_sms(
            phone_number="invalid",
            research_data=research_data,
            user_id="user-123",
            research_id="research-123",
        )

        assert result["status"] == "failed"
        assert "error" in result


class TestEmailDeliveryFlow:
    """Test end-to-end email delivery"""

    @pytest.mark.asyncio
    async def test_send_email_invalid_email(self):
        """Test email with invalid address"""
        pool = MockDatabasePool()
        service = ResultDeliveryService(db_pool=pool)

        research_data = {
            "project_info": {
                "zip": "75001",
                "city": "Arlington",
                "state": "TX",
            },
            "summary": {
                "high_risk_count": 2,
                "estimated_total_cost": 100000,
                "estimated_timeline": "30 days",
            },
            "punch_list": {},
        }

        result = await service.send_email(
            email_address="invalid-email",
            research_data=research_data,
            user_id="user-456",
            research_id="research-456",
        )

        assert result["status"] == "failed"
        assert "error" in result


class TestValidation:
    """Test validation utilities"""

    def test_validate_email_formats(self):
        """Test email validation helper"""
        service = ResultDeliveryService()

        # Valid emails
        assert service._validate_email("user@example.com")
        assert service._validate_email("user.name@example.com")
        assert service._validate_email("user+tag@example.co.uk")

        # Invalid emails
        assert not service._validate_email("invalid")
        assert not service._validate_email("user@")
        assert not service._validate_email("@example.com")
        assert not service._validate_email("user @example.com")
