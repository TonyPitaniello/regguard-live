"""IC Project PDF fulfillment smoke tests."""

from __future__ import annotations

import pytest

from ic_project_fulfillment import (
    analysis_for_pdfs,
    build_pdf_meta,
    generate_ic_pdf_bytes,
    pdfs_are_ready,
)
from order_service import remember_order, update_order_artifacts, get_raw_order_by_id


SAMPLE_ANALYSIS = {
    "project_info": {
        "address": "123 Main St, Plano, TX 75024",
        "city": "Plano",
        "state": "TX",
        "zip": "75024",
        "type": "commercial",
    },
    "environmental_screening": {
        "risk_level": "MEDIUM",
        "findings": [
            {
                "category": "floodplain",
                "description": "Verify FEMA flood zone with AHJ before bid.",
            }
        ],
        "action_plan": ["Confirm zoning", "Pull trade permit fees"],
    },
    "punch_list": {
        "timeline_summary": "6-10 weeks",
        "estimated_total_cost": 12000,
        "punch_list": [
            {
                "priority": "HIGH",
                "task": "Confirm Plano building permit fees",
                "timeline": "Pre-bid",
                "estimated_cost": 500,
            }
        ],
    },
    "pro_summary_markdown": "- [ ] Confirm AHJ trade registration\n- [ ] Verify utility capacity",
}


def test_analysis_for_pdfs_sets_ic_flags():
    shaped = analysis_for_pdfs(SAMPLE_ANALYSIS)
    assert shaped["skip_upgrade_cta"] is True
    assert shaped["project_info"]["city"] == "Plano"
    assert len(shaped["punch_list"]["punch_list"]) >= 1


def test_generate_ic_pdf_bytes():
    byte_map = generate_ic_pdf_bytes(SAMPLE_ANALYSIS)
    assert set(byte_map.keys()) == {"research_memo", "punch_list", "permits"}
    for name, raw in byte_map.items():
        assert raw[:4] == b"%PDF", f"{name} is not a PDF"
        assert len(raw) > 500


def test_pdf_meta_and_ready_flag():
    meta = build_pdf_meta(
        "order-123",
        "buyer@example.com",
        {
            "research_memo": b"%PDF-1.4 x",
            "punch_list": b"%PDF-1.4 y",
            "permits": b"%PDF-1.4 z",
        },
        download_token="tok123",
    )
    assert pdfs_are_ready(meta)
    assert all("/orders/order-123/pdfs/" in p["url"] for p in meta)
    assert "email=buyer@example.com" in meta[0]["url"]
    assert "token=tok123" in meta[0]["url"]


def test_update_order_artifacts_roundtrip():
    order = remember_order(
        {
            "order_id": "ic-test-order-1",
            "tier": "ic_project",
            "email": "icbuyer@example.com",
            "stripe_session_id": "cs_test_ic_1",
            "amount": 150000,
        }
    )
    meta = build_pdf_meta(
        "ic-test-order-1",
        "icbuyer@example.com",
        {"research_memo": b"%PDF", "punch_list": b"%PDF", "permits": b"%PDF"},
    )
    updated = update_order_artifacts(
        "ic-test-order-1",
        pdfs=meta,
        analysis_json=SAMPLE_ANALYSIS,
        address="123 Main St",
    )
    assert updated is not None
    assert pdfs_are_ready(updated["pdfs"])
    raw = get_raw_order_by_id("ic-test-order-1")
    assert raw is not None
    assert raw.get("analysis_json")
