"""IC boardroom package composer + PDF smoke tests."""

from __future__ import annotations

from ic_boardroom_pdf import generate_ic_boardroom_pdf_bytes
from ic_package_composer import PACKAGE_SCHEMA, compose_ic_package
from ic_project_fulfillment import generate_ic_pdf_bytes, pdfs_are_ready, build_pdf_meta


RICH = {
    "project_info": {
        "address": "1404 Vontress Dr",
        "city": "Plano",
        "state": "TX",
        "zip": "75074",
        "type": "data-center",
    },
    "depth_tier": "ic_full",
    "ic_package": True,
    "depth_badge": "IC PROJECT",
    "coverage": {"badge": "Full city pack", "warning": "Confirm on AHJ schedule."},
    "regguard_stamp": {
        "grade": "FAIL",
        "drivers": [{"severity": "FAIL", "label": "High contingency", "detail": "mid 23.5%"}],
        "valid_until": "2026-09-15T00:00:00Z",
        "fingerprint": "fp1",
    },
    "contingency_band": {"pct_low": 21.5, "pct_mid": 23.5, "pct_high": 26.5},
    "margin_killers": [
        {
            "priority": "HIGH",
            "title": "Large-load path",
            "detail": "Interconnection",
            "source_url": "https://www.plano.gov/1648/Development-Services",
        }
    ],
    "gotcha_watchlist": {
        "items": [
            {
                "priority": "HIGH",
                "title": "Grounding ordinance",
                "detail": "Two rods",
                "source_url": "https://www.plano.gov/350/Building-Inspections-Permits",
            }
        ]
    },
    "ahj_card": {
        "name": "Plano",
        "portal_url": "https://www.plano.gov/350/Building-Inspections-Permits",
        "fees_url": "https://www.plano.gov/1648/Development-Services",
    },
    "fee_card": {"fees": [{"name": "Building permit", "amount": "Confirm", "note": "Planning aid"}]},
    "environmental_screening": {
        "risk_level": "MEDIUM",
        "findings": [{"category": "floodplain", "description": "Verify FEMA"}],
        "action_plan": ["Confirm zoning"],
    },
    "punch_list": {
        "timeline_summary": "8-12 weeks",
        "punch_list": [
            {
                "priority": "CRITICAL",
                "task": "Confirm fees",
                "timeline": "Pre-bid",
                "estimated_cost": 500,
                "source_url": "https://www.plano.gov/building-permits",
            }
        ],
    },
    "pro_summary_markdown": "- Confirm AHJ\n- Verify utility",
    "pro_source_urls": ["https://www.plano.gov/350/Building-Inspections-Permits"],
    "share_url": "https://app.regguardagent.com/r/test",
}


def test_compose_ic_package_hold_stamp():
    pkg = compose_ic_package(RICH, generated_for="buyer@example.com")
    assert pkg["schema"] == PACKAGE_SCHEMA
    assert pkg["executive_summary"]["stamp"]["display"] == "HOLD"
    assert pkg["executive_summary"]["contingency"]["pct_low"] == 21.5
    assert pkg["cover"]["city"] == "Plano"
    assert len(pkg["sources"]) >= 1


def test_boardroom_pdf_bytes():
    raw = generate_ic_boardroom_pdf_bytes(RICH, generated_for="buyer@example.com")
    assert raw[:4] == b"%PDF"
    assert len(raw) > 4000


def test_generate_ic_pdf_bytes_includes_package():
    byte_map = generate_ic_pdf_bytes(RICH)
    assert "ic_package" in byte_map
    assert set(byte_map.keys()) >= {"ic_package", "research_memo", "punch_list", "permits"}
    for name, raw in byte_map.items():
        assert raw[:4] == b"%PDF", name


def test_pdfs_are_ready_with_package_only():
    meta = build_pdf_meta(
        "order-x",
        "buyer@example.com",
        {"ic_package": b"%PDF-1.4 x", "research_memo": b"%PDF", "punch_list": b"%PDF", "permits": b"%PDF"},
        download_token="tok",
    )
    assert meta[0]["type"] == "ic_package"
    assert meta[0].get("primary") is True
    assert pdfs_are_ready(meta)
