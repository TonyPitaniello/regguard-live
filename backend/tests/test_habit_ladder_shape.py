"""Free vs Estimator deliverable shape + Receipt PDF differentiation."""

import pytest

from habit_ladder_shape import (
    ESTIMATOR_RECEIPT_MODE,
    FREE_RECEIPT_MODE,
    is_free_preview_receipt,
    shape_free_vs_estimator,
)
from bid_risk_receipt_pdf import generate_bid_risk_receipt_pdf_bytes
from research_store import stamp_depth_badge


BASE = {
    "project_info": {
        "address": "9999 Chapin School Road",
        "city": "Fort Worth",
        "state": "TX",
        "zip": "76126",
        "latitude": 32.6758,
        "longitude": -97.4612,
    },
    "contingency_band": {"pct_low": 21, "pct_mid": 23, "pct_high": 26},
    "ahj_card": {"name": "Fort Worth Development Services", "portal_url": "https://example.com"},
    "fee_card": {"fees": [{"label": "Building permit", "amount_usd": 500}]},
    "margin_killers": [
        {"title": "ERCOT timing", "priority": "HIGH", "detail": "Parallel clock"},
        {"title": "Fee schedule moves", "priority": "HIGH", "detail": "Recheck"},
        {"title": "Trade type", "priority": "MEDIUM", "detail": "Confirm Accela"},
    ],
    "punch_list": {
        "punch_list": [
            {"task": "Pull fee schedule", "priority": "HIGH"},
            {"task": "Confirm Accela type", "priority": "MEDIUM"},
            {"task": "Flag ERCOT clock", "priority": "HIGH", "verified": True, "source_url": "https://x"},
        ]
    },
    "honesty": {"source": "option_a", "risk_verified": False},
    "preview": True,
}


def test_shape_free_vs_estimator_not_twins():
    free = shape_free_vs_estimator(dict(BASE), habit_paid=False)
    partner = shape_free_vs_estimator(dict(BASE), habit_paid=True)
    assert free["research_depth"] == "free"
    assert free["receipt_mode"] == FREE_RECEIPT_MODE
    assert free["soft_lock_contingency"] is True
    assert free["preview"] is True
    assert partner["research_depth"] == "partner"
    assert partner["depth_tier"] == "partner"
    assert partner["receipt_mode"] == ESTIMATOR_RECEIPT_MODE
    assert partner["preview"] is False
    assert partner["soft_lock_contingency"] is False
    assert is_free_preview_receipt(free) is True
    assert is_free_preview_receipt(partner) is False


def test_stamp_depth_badge_keeps_partner_habit():
    shaped = shape_free_vs_estimator(dict(BASE), habit_paid=True)
    stamped = stamp_depth_badge(shaped)
    assert stamped["research_depth"] == "partner"
    assert stamped["depth_tier"] == "partner"
    assert stamped["preview"] is False
    assert "Estimator" in str(stamped.get("depth_badge") or "")
    assert "Estimator habit" in str(stamped.get("depth_claim_note") or "")


def test_stamp_depth_badge_keeps_free_habit_not_instant():
    # Honesty preview source used to demote Free → Instant incomplete.
    shaped = shape_free_vs_estimator(
        {**BASE, "honesty": {"source": "preview", "risk_verified": False}},
        habit_paid=False,
    )
    stamped = stamp_depth_badge(shaped)
    assert stamped["research_depth"] == "free"
    assert stamped["receipt_mode"] == FREE_RECEIPT_MODE
    assert stamped.get("research_incomplete") is not True
    assert "Free Lookups" in str(stamped.get("depth_badge") or "")
    assert "Instant preview" not in str(stamped.get("depth_badge") or "")
    assert "Estimator" in str(stamped.get("depth_claim_note") or "")


def test_free_preview_shows_one_sequence_and_hides_the_rest():
    from pypdf import PdfReader
    import io

    sites = [
        ("1950 N Stemmons Fwy", "Dallas", "75207", "DallasNow record type", "Commercial%20New%20Construction"),
        ("6565 Headquarters Dr", "Plano", "75024", "Electronic submittal", "civicplus.com"),
        ("9020 Metric Blvd", "Austin", "78758", "commercial plan review", "commercial-plan-review"),
        ("13600 Heritage Pkwy", "Fort Worth", "76177", "building permit is issued before a trade", "permits/commercial"),
    ]
    for addr, city, zip_code, needle, url_bit in sites:
        raw = generate_bid_risk_receipt_pdf_bytes(
            {
                "project_info": {
                    "address": addr,
                    "city": city,
                    "state": "TX",
                    "zip": zip_code,
                    "type": "commercial",
                },
                "research_depth": "free",
                "receipt_mode": "free_preview",
            },
            generated_for="runner@example.com",
        )
        text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(raw)).pages)
        flat = text.replace("\n", "")
        assert "BID RISK RECEIPT - FREE PREVIEW" in text
        assert needle in text
        assert url_bit in flat
        assert "default.aspx" not in text
        assert " / " not in text
        assert "confirm with the city" not in text.lower()
        assert "Hidden on Free" in text
        assert "LOCKED" in text
        assert "Text this preview" not in text
        assert "AHJ LINKS" not in text
        assert "City Pack" not in text
        assert text.count("$") == 1
        assert "$79/mo" in text
        assert "$175" not in text
        assert "$291" not in text
        assert "$75" not in text


def test_estimator_receipt_forwards_one_sourced_punch():
    from pypdf import PdfReader
    import io

    sites = [
        ("1950 N Stemmons Fwy", "Dallas", "75207", "DallasNow record type", "Commercial%20New%20Construction"),
        ("6565 Headquarters Dr", "Plano", "75024", "Electronic submittal", "civicplus.com"),
        ("9020 Metric Blvd", "Austin", "78758", "commercial plan review", "commercial-plan-review"),
        ("13600 Heritage Pkwy", "Fort Worth", "76177", "building permit is issued before a trade", "permits/commercial"),
    ]
    for addr, city, zip_code, needle, url_bit in sites:
        raw = generate_bid_risk_receipt_pdf_bytes(
            shape_free_vs_estimator(
                {
                    "project_info": {
                        "address": addr,
                        "city": city,
                        "state": "TX",
                        "zip": zip_code,
                        "type": "commercial",
                    },
                    "project_type": "commercial",
                    "research_depth": "partner",
                    "receipt_mode": "estimator_habit",
                },
                habit_paid=True,
            ),
            generated_for="runner@example.com",
        )
        text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(raw)).pages)
        flat = text.replace("\n", "")
        assert "BID RISK RECEIPT - ESTIMATOR HABIT" in text
        assert "AHJ LINKS" in text
        assert text.count("Portal:") == 1
        assert text.count("Fee schedule:") == 1
        assert text.count("Apply:") == 1
        assert needle in text
        assert url_bit in flat
        assert "Permit runner" in text
        assert "Before bid" in text
        assert "Source" in text
        assert "No schedule states a contingency percent" in text
        assert "default.aspx" not in text
        assert " / " not in text
        assert "confirm with the city" not in text.lower()
        assert "confirm on AHJ schedule" not in text.lower()
        assert "FEMA" not in text
        assert "TDLR" not in text
        assert "+2%" not in text
        assert "mid 3%" not in text
        assert "$" not in text
        assert "City Pack" not in text
        assert "planning_usd" not in text
        assert "bid packet" not in text.lower()


def test_receipt_pdf_free_and_estimator_differ():
    fitz = pytest.importorskip("fitz")

    free = shape_free_vs_estimator(dict(BASE), habit_paid=False)
    partner = shape_free_vs_estimator(dict(BASE), habit_paid=True)
    free_pdf = generate_bid_risk_receipt_pdf_bytes(free, generated_for="free@example.com")
    partner_pdf = generate_bid_risk_receipt_pdf_bytes(partner, generated_for="est@example.com")
    assert free_pdf[:4] == b"%PDF"
    assert partner_pdf[:4] == b"%PDF"
    assert free_pdf != partner_pdf

    def text(raw: bytes) -> str:
        doc = fitz.open(stream=raw, filetype="pdf")
        return "".join(page.get_text() for page in doc)

    free_t = text(free_pdf)
    partner_t = text(partner_pdf)
    assert "BID RISK RECEIPT - FREE PREVIEW" in free_t
    assert "+##%" not in free_t
    assert "+21%" not in free_t
    assert "Hidden on Free" in free_t
    assert "LOCKED" in free_t
    assert "BID RISK RECEIPT - ESTIMATOR HABIT" in partner_t
    assert "+21%" not in partner_t
    assert "No schedule states a contingency percent" in partner_t
    assert "confirm on AHJ schedule" not in partner_t
    assert "Permit runner" in partner_t
    assert "Before bid" in partner_t
    assert "BID RISK RECEIPT - FREE PREVIEW" not in partner_t
    assert "FAIL" not in partner_t
    assert "AHJ LINKS" in partner_t
    assert "Not a quote, a permit total, or a filing." in partner_t
