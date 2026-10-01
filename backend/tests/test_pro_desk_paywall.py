"""Pro desk paywall — Free / Estimator cannot download City Pack / CSV / bid sheet."""

from entitlement import analysis_is_pro_desk_depth, assert_pro_desk_access


def test_free_depth_blocks_pro_desk():
    assert analysis_is_pro_desk_depth({"research_depth": "free", "preview": True}) is False
    assert analysis_is_pro_desk_depth({"research_depth": "instant"}) is False
    assert analysis_is_pro_desk_depth({"access_tier": "free"}) is False


def test_partner_depth_blocks_pro_desk():
    assert analysis_is_pro_desk_depth({"research_depth": "partner"}) is False
    assert analysis_is_pro_desk_depth({"depth_tier": "partner", "access_tier": "partner"}) is False


def test_pro_and_ic_depth_allow_pro_desk():
    assert analysis_is_pro_desk_depth({"research_depth": "pro"}) is True
    assert analysis_is_pro_desk_depth({"research_depth": "pro_partial"}) is True
    assert analysis_is_pro_desk_depth({"depth_tier": "pro_light"}) is True
    assert analysis_is_pro_desk_depth({"research_depth": "ic", "preview": False}) is True


def test_assert_raises_on_free():
    from fastapi import HTTPException
    import pytest

    with pytest.raises(HTTPException) as ei:
        assert_pro_desk_access({"research_depth": "free"}, artifact="Full City Pack PDF")
    assert ei.value.status_code == 403
    assert "Free" in str(ei.value.detail) or "not included" in str(ei.value.detail).lower()


def test_assert_raises_on_partner():
    from fastapi import HTTPException
    import pytest

    with pytest.raises(HTTPException) as ei:
        assert_pro_desk_access({"research_depth": "partner"}, artifact="Full City Pack PDF")
    assert ei.value.status_code == 403
    assert "Estimator" in str(ei.value.detail) or "Pro" in str(ei.value.detail)


def test_assert_allows_pro():
    assert_pro_desk_access({"research_depth": "pro"}, artifact="Full City Pack PDF")
