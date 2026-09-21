"""Honesty layer unit tests — stub risk hidden, estimates flagged, IC demo gated."""

import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from honesty import (  # noqa: E402
    UNAVAILABLE,
    apply_honesty_layer,
    analysis_shows_risk_score,
    is_ic_demo_enabled,
)
from instant_analysis import build_instant_fallback_analysis  # noqa: E402


def test_instant_fallback_hides_stub_risk_level():
    analysis = build_instant_fallback_analysis(
        "100 Main St, Plano, TX 75074",
        project_type="electrical",
        zip_code="75074",
        city="Plano",
        state="TX",
    )
    assert analysis["preview"] is True
    assert analysis["honesty"]["risk_verified"] is False
    # Plano AHJ catalog may verify the $75 fee line; env risk remains stub-hidden
    assert analysis["honesty"].get("ahj_catalog") == "plano_tx" or analysis["summary"].get("ahj_id") == "plano_tx"
    assert analysis["honesty"]["cost_verified"] is True
    assert analysis["environmental_screening"]["risk_level"] == UNAVAILABLE
    assert analysis["summary"]["high_risk_count"] == 0
    assert "unverified" in analysis["summary"]["estimated_timeline"].lower()
    assert analysis_shows_risk_score(analysis) is False
    for finding in analysis["environmental_screening"]["findings"]:
        assert finding["risk_level"] == "PRELIMINARY"


def test_instant_fallback_non_catalog_city_cost_unverified():
    analysis = build_instant_fallback_analysis(
        "100 Main St, Frisco, TX 75034",
        project_type="electrical",
        zip_code="75034",
        city="Frisco",
        state="TX",
    )
    assert analysis["honesty"]["risk_verified"] is False
    assert analysis["honesty"]["cost_verified"] is False
    assert analysis_shows_risk_score(analysis) is False


def test_apply_honesty_layer_preserves_verified_risk():
    raw = {
        "preview": False,
        "environmental_screening": {
            "risk_level": "HIGH",
            "findings": [
                {
                    "category": "flood_zones",
                    "risk_level": "HIGH",
                    "description": "Zone AE",
                    "verified": True,
                    "source_url": "https://msc.fema.gov/",
                },
                {
                    "category": "wetlands",
                    "risk_level": "LOW",
                    "description": "No NWI hit",
                    "verified": True,
                    "source_url": "https://www.fws.gov/program/national-wetlands-inventory/wetlands-mapper",
                },
            ],
        },
        "summary": {"high_risk_count": 1, "estimated_timeline": "60 days", "estimated_total_cost": 1000},
        "punch_list": {"punch_list": [{"task": "a", "estimated_cost": 100}]},
    }
    stamped = apply_honesty_layer(
        raw,
        source="research",
        risk_verified=True,
        cost_verified=True,
        timeline_verified=True,
        hide_stub_risk=False,
    )
    assert stamped["environmental_screening"]["risk_level"] == "HIGH"
    assert stamped["honesty"]["risk_verified"] is True
    assert analysis_shows_risk_score(stamped) is True


def test_ic_demo_disabled_by_default(monkeypatch):
    monkeypatch.delenv("REG_GUARD_IC_DEMO", raising=False)
    assert is_ic_demo_enabled() is False
    monkeypatch.setenv("REG_GUARD_IC_DEMO", "1")
    assert is_ic_demo_enabled() is True
    monkeypatch.setenv("REG_GUARD_IC_DEMO", "0")
    assert is_ic_demo_enabled() is False


def test_queue_endpoints_reject_when_demo_off(monkeypatch):
    monkeypatch.setenv("REG_GUARD_IC_DEMO", "0")
    from fastapi import HTTPException
    from interconnect.endpoints import _require_ic_demo_enabled

    with pytest.raises(HTTPException) as exc:
        _require_ic_demo_enabled()
    assert exc.value.status_code == 403


def test_delivery_summary_does_not_invent_high_risk():
    from main import ResearchDeliverySummary, _research_data_from_summary

    data = _research_data_from_summary(
        ResearchDeliverySummary(
            city="Dallas",
            state="TX",
            zip="75201",
            risk_unavailable=True,
            estimates_unverified=True,
            preview=True,
            cost=1000,
            timeline="30 days",
        )
    )
    assert data["environmental_screening"]["risk_level"] == UNAVAILABLE
    assert data["summary"]["high_risk_count"] == 0
    assert data["honesty"]["risk_verified"] is False


def test_sms_format_omits_stub_high_risk_count():
    from sms_service import TwilioSMSService

    analysis = build_instant_fallback_analysis("1 Main, Dallas, TX 75201", city="Dallas", state="TX")
    svc = object.__new__(TwilioSMSService)
    msg = TwilioSMSService._format_sms_message(svc, analysis)
    assert "unavailable" in msg.lower() or "Preview" in msg
    assert "⚠️  0 High Risks" not in msg and "⚠️  1 High Risks" not in msg and "⚠️  2 High Risks" not in msg
    assert "3 High Risks" not in msg
