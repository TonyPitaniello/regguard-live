"""Pack quality gate + promote reject tests."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture()
def pack_root(tmp_path, monkeypatch):
    monkeypatch.setenv("REGGUARD_DATA_DIR", str(tmp_path))
    try:
        from ahj_catalog import load_ahj_catalog

        load_ahj_catalog.cache_clear()
    except Exception:
        pass
    yield tmp_path


def test_validate_pack_for_promote_ok():
    from pack_quality import validate_pack_for_promote

    pack = {
        "city": "Bradenton",
        "state": "FL",
        "ahj": {"portal_url": "https://example.com/portal"},
        "fees": [
            {
                "label": "Electrical permit",
                "amount_usd": 100,
                "source_url": "https://example.com/fees",
            }
        ],
        "gotchas": [{"title": "Confirm NEC", "source_url": "https://example.com/portal"}],
    }
    ok, errors = validate_pack_for_promote(pack)
    assert ok, errors


def test_promote_rejects_thin_pack(pack_root):
    from local_pack_store import promote_zip_pack, save_zip_pack

    save_zip_pack(
        "88888",
        {
            "tier": "paid_local",
            "city": "Thin",
            "state": "FL",
            "zip": "88888",
            "ahj": {"name": "X", "portal_url": "https://example.com/portal"},
            "fees": [],
            "gotchas": [],
        },
    )
    with pytest.raises(ValueError, match="fee or gotcha"):
        promote_zip_pack("88888", reviewer="ops")


def test_sms_delivery_store_roundtrip(pack_root):
    from sms_delivery_store import latest_for_sid, record_outbound, record_status_callback, recent

    record_outbound(message_sid="SMtest123", to_phone="+15551212", status="queued")
    out = record_status_callback(
        {
            "MessageSid": "SMtest123",
            "MessageStatus": "delivered",
            "To": "+15551212",
        }
    )
    assert out["delivery_status"] == "delivered"
    last = latest_for_sid("SMtest123")
    assert last and last.get("status") == "delivered"
    assert recent(limit=5)


def test_metro_seeds_include_gulf_tx():
    from metro_portal_seeds import resolve_metro_portal_pack

    for city, state in (
        ("Clearwater", "FL"),
        ("Fort Myers", "FL"),
        ("Frisco", "TX"),
        ("Arlington", "TX"),
        ("Midlothian", "TX"),
        ("Boise", "ID"),
    ):
        pack = resolve_metro_portal_pack(city, state)
        assert pack is not None, f"missing seed {city}, {state}"
        assert str(pack["ahj"]["portal_url"]).startswith("http")


def test_gis_risk_verified_when_flood_verified(monkeypatch):
    """Pin + verified flood/wetlands → risk_verified True."""
    import asyncio

    from option_a_integration import run_option_a_analysis

    async def fake_screen(**kwargs):
        return {
            "risk_level": "MEDIUM",
            "findings": [
                {
                    "category": "flood_zones",
                    "risk_level": "MEDIUM",
                    "description": "Zone AE",
                    "verified": True,
                    "source_url": "https://msc.fema.gov/",
                    "action_items": [],
                    "data_sources": ["FEMA"],
                    "research_cost_usd": 0,
                }
            ],
            "total_research_cost": 0,
            "action_plan": [],
        }

    class FakeEngine:
        async def screen_site(self, **kwargs):
            return await fake_screen(**kwargs)

    class FakePunch:
        def generate_punch_list(self, **kwargs):
            return {
                "punch_list": [{"task": "Confirm AHJ", "priority": "HIGH"}],
                "critical_path": ["Confirm AHJ"],
                "timeline_summary": "6-10 weeks",
                "estimated_total_cost": 5000,
            }

    monkeypatch.setattr(
        "real_environmental_screening.get_environmental_screening_engine",
        lambda: FakeEngine(),
    )
    monkeypatch.setattr(
        "punch_list_generator.get_punch_list_generator",
        lambda: FakePunch(),
    )

    result = asyncio.run(
        run_option_a_analysis(
            address="1 Main",
            city="Plano",
            state="TX",
            zip_code="75074",
            latitude=33.0,
            longitude=-96.7,
            project_type="commercial",
        )
    )
    assert result["honesty"]["risk_verified"] is True
