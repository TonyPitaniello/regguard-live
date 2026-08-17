"""Tests for depth ladder upgrade offers."""

from depth_ladder import (
    DEPTH_FREE,
    DEPTH_IC_FULL,
    DEPTH_PRO_LIGHT,
    DEPTH_PRO_LOCAL,
    stamp_upgrade_offer,
)


def test_free_offer_points_to_pro():
    a = stamp_upgrade_offer({}, depth_tier=DEPTH_FREE)
    assert a["depth_tier"] == DEPTH_FREE
    assert "fuller" in (a["upgrade_offer"]["message"] or "").lower()
    assert a["upgrade_offer"]["cta_tier"] == "contractor_pro"


def test_pro_light_offer_points_to_ic():
    a = stamp_upgrade_offer({}, depth_tier=DEPTH_PRO_LIGHT)
    assert a["upgrade_offer"]["cta_tier"] == "ic_project"


def test_pro_local_offer_points_to_ic():
    a = stamp_upgrade_offer({}, depth_tier=DEPTH_PRO_LOCAL)
    assert a["upgrade_offer"]["cta_tier"] == "ic_project"


def test_ic_full_offer_another_site():
    a = stamp_upgrade_offer({}, depth_tier=DEPTH_IC_FULL)
    assert a["upgrade_offer"]["cta_tier"] == "ic_project"
    assert a["upgrade_offer"]["next_label"] is None
