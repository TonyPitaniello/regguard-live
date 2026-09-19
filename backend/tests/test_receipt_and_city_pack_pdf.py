"""Bid Risk Receipt + city pack PDF customer-facing copy."""

import pytest

from bid_risk_receipt_pdf import generate_bid_risk_receipt_pdf_bytes
from city_pack_pdf import generate_city_pack_pdf_bytes


SAMPLE = {
    "project_info": {"address": "100 Main", "city": "Plano", "state": "TX", "zip": "75074"},
    "coverage": {"badge": "Full city pack", "tier": "full_pack"},
    "regguard_stamp": {
        "grade": "FAIL",
        "headline": "FAIL — high pre-bid risk",
        "drivers": [{"severity": "HIGH", "label": "Grounding", "detail": "Two rods"}],
        "valid_until": "2026-09-25",
    },
    "contingency_band": {"pct_low": 8, "pct_high": 15, "pct_mid": 11},
    "ahj_card": {
        "name": "City of Plano Building Inspections",
        "portal_url": "https://www.plano.gov/350/Building-Inspections-Permits",
    },
    "fee_card": {
        "timeline": "8-12 weeks",
        "fees": [{"label": "Building permit", "amount_usd": 500, "verified": True}],
    },
    "gotcha_watchlist": {"items": [{"title": "Grounding ordinance", "priority": "HIGH"}]},
    "margin_killers": [{"title": "Large-load path", "priority": "HIGH", "detail": "Interconnection"}],
}


def _pdf_text(raw: bytes) -> str:
    fitz = pytest.importorskip("fitz")
    doc = fitz.open(stream=raw, filetype="pdf")
    return "".join(page.get_text() for page in doc)


def test_receipt_pdf_prints_hold_not_fail():
    raw = generate_bid_risk_receipt_pdf_bytes(SAMPLE)
    assert raw[:4] == b"%PDF"
    text = _pdf_text(raw)
    assert "HOLD" in text
    assert "REGGUARD STAMP" in text
    assert "FAIL" not in text


def test_city_pack_pdf_bytes_nonempty():
    raw = generate_city_pack_pdf_bytes(SAMPLE)
    assert raw[:4] == b"%PDF"
    assert len(raw) > 1500
    text = _pdf_text(raw)
    assert "FULL CITY PACK" in text
    assert "Plano" in text
