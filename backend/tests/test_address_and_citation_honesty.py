"""Tests for address dedupe + SOURCE/LINK citation honesty."""

from citation_honesty import apply_citation_honesty, citation_tier_for
from site_address import compose_site_line, normalize_street_address


def test_normalize_strips_duplicated_place():
    raw = "7351 Meeting St, Bradenton, FL 34201, Bradenton, FL, 34201"
    cleaned = normalize_street_address(
        raw, city="Bradenton", state="FL", zip_code="34201"
    )
    assert cleaned.count("Bradenton") == 1
    assert cleaned.count("34201") <= 1
    assert "Meeting" in cleaned


def test_compose_does_not_double_place():
    line = compose_site_line(
        "7351 Meeting St, Bradenton, FL 34201",
        city="Bradenton",
        state="FL",
        zip_code="34201",
    )
    assert line.count("Bradenton") == 1


def test_federal_portal_is_link_not_source():
    tier = citation_tier_for(
        {
            "verified": True,
            "source_url": "https://msc.fema.gov/portal/home",
            "jurisdiction_layer": "federal",
        }
    )
    assert tier == "link"


def test_apply_citation_honesty_demotes_federal_punch():
    analysis = {
        "punch_list": {
            "punch_list": [
                {
                    "task": "[Federal] Check FEMA",
                    "verified": True,
                    "source_url": "https://msc.fema.gov/portal/home",
                    "source_label": "Source",
                    "jurisdiction_layer": "federal",
                }
            ]
        },
        "margin_killers": [
            {
                "title": "FEMA",
                "verified": True,
                "source_url": "https://msc.fema.gov/portal/home",
                "jurisdiction_layer": "federal",
            }
        ],
    }
    out = apply_citation_honesty(analysis)
    item = out["punch_list"]["punch_list"][0]
    assert item["citation_tier"] == "link"
    assert item["verified"] is False
    assert out["margin_killers"][0]["citation_tier"] == "link"
