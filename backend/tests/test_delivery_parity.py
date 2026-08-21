"""Tests for email/PDF delivery parity and jurisdiction bleed guards."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_filter_demotes_sarasota_for_bradenton():
    from main import _filter_reference_urls_for_locality

    urls = [
        "https://www.sarasotafl.gov/Department-Pages/Development-Services/Building-Permitting",
        "https://library.municode.com/fl/bradenton",
        "https://www.permitting.gov/",
        "https://cityofbradenton.com/building",
    ]
    out = _filter_reference_urls_for_locality(urls, city="Bradenton", state="FL")
    assert any("municode.com/fl/bradenton" in u for u in out)
    assert any("bradenton" in u.lower() for u in out)
    # Sarasota should not lead when Bradenton links exist
    assert not out[0].lower().startswith("https://www.sarasotafl.gov")


def test_sanitize_plano_bottom_line_bleed():
    from main import sanitize_action_plan_jurisdiction_bleed

    md = (
        "### The Bottom Line\n\n"
        "🚧 Red Alert Summary: Hold electrical layouts immediately. Plano has a strict structural "
        "property setback rule and a massive local noise-barrier mandate for large power systems. "
        "We are running parallel tracks."
    )
    out = sanitize_action_plan_jurisdiction_bleed(md, city="Bradenton", state="FL")
    assert "Plano has a strict structural" not in out
    assert "Bradenton" in out or "this site" in out.lower() or "Hold electrical" in out


def test_industrial_fallback_no_plano_or_ercot_for_fl():
    from main import _research_action_plan_fallback_markdown

    raw = {
        "zip": "34201",
        "site_address": "7351 Meeting St",
        "city": "Bradenton",
        "jurisdiction": {"city": "Bradenton", "state": "FL", "label": "Bradenton, FL"},
        "project_type": "data_center",
        "scout_profile": {"vertical": "data_center"},
    }
    md = _research_action_plan_fallback_markdown(
        raw,
        [
            "https://library.municode.com/fl/bradenton",
            "https://www.sarasotafl.gov/Department-Pages/Development-Services/Building-Permitting",
        ],
        "data center bradenton",
        job_description="100MW data center interconnection",
    )
    assert "Plano has a strict" not in md
    assert "ERCOT" not in md
    assert "Bradenton" in md
    assert "Virginia HB 1515" not in md
    assert "Ohio 2026" not in md
    assert "utility interconnection" in md
    # Sarasota demoted when Bradenton municode present
    assert "sarasotafl.gov" not in md.split("### Reference Links")[1].split("### The Bottom Line")[0]

def test_delivery_parity_ranks_critical_first():
    from delivery_parity import prepare_analysis_for_delivery

    analysis = {
        "project_info": {
            "address": "7351 Meeting St, Bradenton, FL 34201, Bradenton, FL, 34201",
            "city": "Bradenton",
            "state": "FL",
            "zip": "34201",
            "type": "data_center",
        },
        "punch_list": {
            "punch_list": [
                {"task": "Confirm business / SOS filings if needed", "priority": "LOW", "verified": True, "source_url": "https://example.com"},
                {
                    "task": "Contact municipal permitting office for preliminary consultation",
                    "priority": "CRITICAL",
                    "verified": True,
                    "source_url": "https://example.com",
                    "jurisdiction_layer": "federal",
                },
                {
                    "task": "Coordinate AHJ permits and utility interconnection for Bradenton",
                    "priority": "HIGH",
                    "verified": True,
                    "source_url": "https://cityofbradenton.com",
                },
            ]
        },
    }
    out = prepare_analysis_for_delivery(analysis)
    items = out["punch_list"]["punch_list"]
    assert "Bradenton, FL, 34201" not in str(out["project_info"].get("address"))
    # Hygiene CRITICAL demoted; schedule killer stays high
    pris = [str(i.get("priority")).upper() for i in items]
    assert pris == sorted(pris, key=lambda p: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(p, 9))


def test_bid_packet_uses_ranked_punch(tmp_path):
    from bid_packet_pdf import generate_bid_packet_pdf

    analysis = {
        "project_info": {
            "address": "7351 Meeting St",
            "city": "Bradenton",
            "state": "FL",
            "zip": "34201",
            "type": "data_center",
        },
        "contingency_band": {"pct_low": 20.5, "pct_mid": 22.5, "pct_high": 25.5},
        "margin_killers": [
            {
                "title": "Confirm AHJ fee schedule",
                "detail": "No curated city pack",
                "priority": "CRITICAL",
                "verified": False,
            }
        ],
        "ahj_card": {"name": "Bradenton, FL AHJ (confirm locally)", "notes": "Federal + state layers"},
        "fee_card": {"timeline": "11-15 weeks", "fees": []},
        "document_checklist": {"items": [{"task": "Single-line diagram"}]},
        "gotcha_watchlist": {"items": []},
        "punch_list": {
            "punch_list": [
                {"task": "Low SOS filings", "priority": "LOW"},
                {"task": "**Verify AHJ** for Bradenton", "priority": "HIGH", "source_url": "https://x.com", "verified": True},
                {"task": "Mandatory code adoption schedule", "priority": "CRITICAL", "source_url": "https://y.com", "verified": True},
            ]
        },
    }
    path = generate_bid_packet_pdf(analysis, output_path=str(tmp_path / "packet.pdf"))
    assert os.path.exists(path)
    assert os.path.getsize(path) > 2000
