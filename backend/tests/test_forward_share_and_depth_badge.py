"""Tests for forward share URL resolution + honest depth badges."""

from research_store import (
    has_usable_coords,
    is_instant_preview_payload,
    is_valid_forward_share_url,
    resolve_forward_share_url,
    stamp_depth_badge,
)


def test_rejects_homepage_and_utm_landing():
    assert not is_valid_forward_share_url("https://app.regguardagent.com/")
    assert not is_valid_forward_share_url("https://app.regguardagent.com/?utm_source=bid_receipt")
    assert not is_valid_forward_share_url("https://app.regguardagent.com/r/")
    assert is_valid_forward_share_url(
        "https://app.regguardagent.com/r/4012f963-cd71-4e84-9bda-c062bdcd4b89"
    )


def test_resolve_never_returns_homepage():
    assert resolve_forward_share_url({"share_url": "https://app.regguardagent.com/"}) == ""
    assert (
        resolve_forward_share_url(
            {"share_url": "https://app.regguardagent.com/?utm_source=bid_receipt"}
        )
        == ""
    )
    rid = "4012f963-cd71-4e84-9bda-c062bdcd4b89"
    url = resolve_forward_share_url({"research_id": rid})
    assert url.endswith(f"/r/{rid}")
    assert "utm_source" not in url


def test_null_island_not_usable_coords():
    assert not has_usable_coords({"project_info": {"lat": 0, "lng": 0}})
    assert has_usable_coords({"project_info": {"lat": 27.5, "lng": -82.5}})


def test_instant_preview_demotes_pro_badge():
    a = stamp_depth_badge(
        {
            "research_depth": "pro_partial",
            "preview": True,
            "honesty": {"source": "instant"},
            "project_info": {},
        }
    )
    assert "not full Pro" in a["depth_badge"]
    assert a.get("depth_claim_honest") is False


def test_pro_with_coords_keeps_badge():
    a = stamp_depth_badge(
        {
            "research_depth": "pro",
            "preview": False,
            "honesty": {"source": "pro_deep"},
            "project_info": {"lat": 32.7, "lng": -96.8},
        }
    )
    assert "Contractor Pro" in a["depth_badge"]
    assert a.get("depth_claim_honest") is True
    assert not is_instant_preview_payload(a)
