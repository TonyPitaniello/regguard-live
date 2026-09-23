"""IC artifact downloads require IC-depth analysis + site-bound purchase."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from entitlement import analysis_is_ic_depth, assert_ic_artifact_access


def test_free_preview_is_not_ic_depth():
    assert (
        analysis_is_ic_depth(
            {
                "preview": True,
                "research_incomplete": True,
                "depth_tier": "free",
                "honesty": {"source": "instant"},
            }
        )
        is False
    )


def test_ic_full_completed_is_ic_depth():
    assert (
        analysis_is_ic_depth(
            {
                "preview": False,
                "research_incomplete": False,
                "depth_tier": "ic_full",
                "research_depth": "ic",
                "honesty": {"source": "option_a"},
            }
        )
        is True
    )


def test_assert_rejects_free_preview_even_with_ic_email(monkeypatch):
    monkeypatch.setattr(
        "ic_project_fulfillment.evaluate_ic_site_access",
        lambda *a, **k: {"allowed": True, "mode": "bind_unused"},
    )
    with pytest.raises(HTTPException) as ei:
        assert_ic_artifact_access(
            "buyer@example.com",
            {
                "preview": True,
                "research_incomplete": True,
                "depth_tier": "free",
                "honesty": {"source": "instant"},
                "project_info": {
                    "address": "9999 Chapin School Road",
                    "city": "Fort Worth",
                    "state": "TX",
                    "zip": "76126",
                },
            },
        )
    assert ei.value.status_code == 403
    assert "Instant Preview" in str(ei.value.detail) or "completed IC" in str(ei.value.detail)


def test_assert_rejects_when_site_needs_purchase(monkeypatch):
    monkeypatch.setattr(
        "ic_project_fulfillment.evaluate_ic_site_access",
        lambda *a, **k: {
            "allowed": False,
            "mode": "need_purchase",
            "message": "IC Project is $1,500 per site.",
        },
    )
    with pytest.raises(HTTPException) as ei:
        assert_ic_artifact_access(
            "buyer@example.com",
            {
                "preview": False,
                "depth_tier": "ic_full",
                "research_depth": "ic",
                "project_info": {
                    "address": "100 Main",
                    "city": "Plano",
                    "state": "TX",
                    "zip": "75074",
                },
            },
        )
    assert ei.value.status_code == 403


def test_assert_allows_ic_depth_with_site_credit(monkeypatch):
    monkeypatch.setattr(
        "ic_project_fulfillment.evaluate_ic_site_access",
        lambda *a, **k: {"allowed": True, "mode": "same_site_refresh"},
    )
    access = assert_ic_artifact_access(
        "buyer@example.com",
        {
            "preview": False,
            "depth_tier": "ic_full",
            "research_depth": "ic",
            "project_info": {
                "address": "9999 Chapin School Road",
                "city": "Fort Worth",
                "state": "TX",
                "zip": "76126",
            },
        },
    )
    assert access["allowed"] is True
