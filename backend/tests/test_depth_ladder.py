"""Tests for depth ladder upgrade offers + Pro delta + persona split."""

from depth_ladder import (
    DEPTH_FREE,
    DEPTH_IC_FULL,
    DEPTH_PRO_LIGHT,
    DEPTH_PRO_LOCAL,
    PERSONA_BID_DESK,
    PERSONA_DC_INFRA,
    infer_persona,
    stamp_pro_delta,
    stamp_upgrade_offer,
)


def test_free_bid_desk_points_to_pro():
    a = stamp_upgrade_offer(
        {"project_info": {"type": "commercial"}},
        depth_tier=DEPTH_FREE,
    )
    assert a["buyer_persona"] == PERSONA_BID_DESK
    assert a["upgrade_offer"]["cta_tier"] == "contractor_pro"
    assert "accurate" not in (a["upgrade_offer"]["message"] or "").lower()
    assert "accurate" not in (a["upgrade_offer"]["detail"] or "").lower() or "not" in (
        a["upgrade_offer"]["detail"] or ""
    ).lower()


def test_free_dc_points_to_ic_pdfs():
    a = stamp_upgrade_offer(
        {"project_info": {"type": "data-center"}},
        depth_tier=DEPTH_FREE,
    )
    assert a["buyer_persona"] == PERSONA_DC_INFRA
    assert a["upgrade_offer"]["cta_tier"] == "ic_project"
    assert "PDF" in (a["upgrade_offer"]["cta_label"] or "")


def test_pro_light_dc_warns_not_enough():
    a = stamp_upgrade_offer(
        {"project_info": {"type": "data-center"}},
        depth_tier=DEPTH_PRO_LIGHT,
    )
    assert a["upgrade_offer"]["cta_tier"] == "ic_project"
    assert "not enough" in (a["upgrade_offer"]["message"] or "").lower() or "IC" in (
        a["upgrade_offer"]["message"] or ""
    )


def test_pro_local_offer_points_to_ic():
    a = stamp_upgrade_offer(
        {"project_info": {"type": "commercial"}},
        depth_tier=DEPTH_PRO_LOCAL,
    )
    assert a["upgrade_offer"]["cta_tier"] == "ic_project"


def test_ic_full_offer_another_site():
    a = stamp_upgrade_offer({}, depth_tier=DEPTH_IC_FULL)
    assert a["upgrade_offer"]["cta_tier"] == "ic_project"
    assert a["upgrade_offer"]["next_label"] is None


def test_pro_delta_lists_uniqueness():
    a = stamp_pro_delta(
        {
            "paid_local": {"pages_scraped": 4, "fee_rows_extracted": 2, "status": "ok"},
            "pro_source_urls": ["https://example.gov/a", "https://example.gov/b"],
            "scout_mode": "light",
            "punch_list": {
                "punch_list": [
                    {"task": "x", "verified": True, "source_url": "https://example.gov/a"},
                    {"task": "y", "verified": False},
                ]
            },
        }
    )
    delta = a["pro_delta"]
    assert delta["pages_scraped"] == 4
    assert delta["scout_sources"] == 2
    assert delta["verified_punch_lines"] == 1
    assert any("light scout" in b.lower() or "3 passes" in b.lower() for b in delta["bullets"])
    assert "not a guarantee" in (delta["honesty"] or "").lower()


def test_infer_persona_renewable_is_dc_infra():
    assert infer_persona({"project_info": {"type": "renewable"}}) == PERSONA_DC_INFRA
    assert infer_persona({"project_info": {"type": "commercial"}}) == PERSONA_BID_DESK
