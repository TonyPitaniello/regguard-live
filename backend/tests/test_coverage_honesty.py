"""Tests for coverage honesty + SERP scoring (premortem kill risks)."""

from __future__ import annotations


def test_coverage_tier_and_fee_strip():
    from coverage_honesty import apply_coverage_honesty, coverage_tier_for

    assert coverage_tier_for(citeable_local=True) == "full_pack"
    assert coverage_tier_for(portal_only=True) == "portal_seed"
    assert coverage_tier_for() == "federal_state"

    analysis = {
        "fee_card": {
            "fees": [{"label": "Electrical", "amount_usd": 75}],
            "disclaimer": "old",
        },
        "punch_list": {
            "punch_list": [
                {"task": "Confirm AHJ fee extract: Electrical (~$75)", "priority": "HIGH"},
                {"task": "[Federal] FEMA", "source_url": "https://msc.fema.gov", "priority": "HIGH"},
            ]
        },
        "jurisdiction": {"portal_only_local": True, "coverage_note": "Portal seed note"},
    }
    out = apply_coverage_honesty(analysis, pack={"portal_only": True, "pack_key": "portal:x"})
    assert out["coverage"]["tier"] == "portal_seed"
    assert out["coverage"]["fees_allowed"] is False
    assert out["fee_card"]["fees"] == []
    assert out["fee_card"].get("fees_stripped") is True
    tasks = [i.get("task") for i in out["punch_list"]["punch_list"]]
    assert not any("fee extract" in str(t).lower() for t in tasks)
    assert any("FEMA" in str(t) for t in tasks)


def test_full_pack_keeps_fees():
    from coverage_honesty import apply_coverage_honesty

    analysis = {
        "fee_card": {"fees": [{"label": "Electrical", "amount_usd": 75}]},
        "punch_list": {"punch_list": []},
        "jurisdiction": {"citeable_local": True},
    }
    out = apply_coverage_honesty(
        analysis, resolved={"citeable_local": True, "coverage_note": "Citeable"}, pack={"citeable": True}
    )
    assert out["coverage"]["tier"] == "full_pack"
    assert out["fee_card"]["fees"][0]["amount_usd"] == 75


def test_serp_scoring_prefers_city_building():
    from coverage_honesty import filter_gov_serp_hits, score_gov_serp_hit

    good = {
        "url": "https://www.seattle.gov/sdci/permits",
        "title": "Seattle SDCI Building Permits",
        "snippet": "Apply for a building permit",
    }
    bad_fed = {
        "url": "https://www.epa.gov/nepa",
        "title": "EPA NEPA",
        "snippet": "environmental",
    }
    weak = {
        "url": "https://www.wa.gov/",
        "title": "Washington State",
        "snippet": "welcome",
    }
    assert score_gov_serp_hit(good, city="Seattle", state="WA") >= 30
    assert score_gov_serp_hit(bad_fed, city="Seattle", state="WA") < 30
    assert score_gov_serp_hit(weak, city="Seattle", state="WA") < 30
    filtered = filter_gov_serp_hits(
        [bad_fed, weak, good], city="Seattle", state="WA", limit=1
    )
    assert len(filtered) == 1
    assert "seattle.gov" in filtered[0]["url"]


def test_free_pack_emits_coverage_block():
    from free_pack_confirm import build_free_pack_confirm_analysis

    ad = build_free_pack_confirm_analysis(
        address="400 Broad",
        city="Seattle",
        state="WA",
        zip_code="98109",
        project_type="commercial",
    )
    assert ad.get("coverage", {}).get("tier") == "portal_seed"
    assert ad["coverage"]["fees_allowed"] is False
    assert (ad.get("fee_card") or {}).get("fees") in ([], None) or ad["fee_card"].get(
        "fees_stripped"
    )
    assert "Portal" in (ad["coverage"].get("badge") or "")
