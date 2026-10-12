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
    assert "FREE LOOKUPS PREVIEW" in free_t
    assert "+##%" in free_t or "+##%  to  +##%" in free_t
    assert "LOCKED" in free_t
    assert "ESTIMATOR" in partner_t
    assert "+21%" in partner_t
    assert "UNLOCKED PUNCH" in partner_t
    assert "FREE LOOKUPS PREVIEW" not in partner_t
