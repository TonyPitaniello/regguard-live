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


def test_unverified_fast41_gets_confirm_link():
    out = apply_citation_honesty(
        {
            "punch_list": {
                "punch_list": [
                    {
                        "task": "Confirm FAST-41 covered-project gate",
                        "verified": False,
                        "source_label": "Confirm",
                    }
                ]
            }
        }
    )
    item = out["punch_list"]["punch_list"][0]
    assert item["citation_tier"] == "link"
    assert str(item.get("source_url") or "").startswith("https://www.permits.performance.gov")
    assert item["verified"] is False


def test_env_noise_nepa_state_get_confirm_links():
    """Screenshot UNVERIFIED cards become LINK with official confirm URLs."""
    out = apply_citation_honesty(
        {
            "project_info": {"city": "Fort Worth", "state": "TX", "zip": "76126"},
            "environmental_screening": {
                "findings": [
                    {
                        "category": "noise_ordinances",
                        "risk_level": "LOW",
                        "description": "Standard municipal noise ordinance applies.",
                        "data_sources": ["Municipal Code"],
                        "verified": False,
                    },
                    {
                        "category": "nepa",
                        "risk_level": "LOW",
                        "description": "NEPA likely not applicable (no federal funding/permits).",
                        "data_sources": ["Project scope analysis"],
                        "verified": False,
                    },
                    {
                        "category": "state_requirements",
                        "risk_level": "LOW",
                        "description": "Standard state environmental review applies.",
                        "data_sources": ["State Environmental Code"],
                        "verified": False,
                    },
                ]
            },
        }
    )
    findings = {f["category"]: f for f in out["environmental_screening"]["findings"]}
    noise = findings["noise_ordinances"]
    assert noise["citation_tier"] == "link"
    assert noise["verified"] is False
    assert "municode.com" in str(noise["source_url"]) or str(noise["source_url"]).startswith("http")
    nepa = findings["nepa"]
    assert nepa["citation_tier"] == "link"
    assert "epa.gov/nepa" in str(nepa["source_url"])
    assert nepa["verified"] is False
    state = findings["state_requirements"]
    assert state["citation_tier"] == "link"
    assert "tceq.texas.gov" in str(state["source_url"])
    assert state["verified"] is False
