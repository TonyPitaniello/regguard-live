"""IC Diligence Package paywall — client flags alone must never unlock."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient


def _client():
    from main import app

    return TestClient(app)


def test_ic_package_rejects_client_ic_pdfs_ready_without_entitlement():
    client = _client()
    with patch("entitlement.access_summary", return_value={"tiers": [], "ic_pdfs_ready": False}):
        res = client.post(
            "/ic-package/pdf",
            json={
                "email": "free@example.com",
                "generated_for": "free@example.com",
                "analysis_data": {
                    "ic_pdfs_ready": True,
                    "depth_tier": "free",
                    "research_depth": "free",
                    "research_incomplete": True,
                    "project_info": {"address": "1 Main", "city": "Dallas", "state": "TX", "zip": "75201"},
                    "contingency_band": {"pct_low": 5, "pct_mid": 8, "pct_high": 12},
                    "margin_killers": [{"title": "x", "priority": "HIGH"}],
                    "fee_card": {"fees": []},
                },
            },
        )
    assert res.status_code == 403
    assert "IC Project" in str(res.json().get("detail", ""))


def test_ic_package_rejects_forged_depth_tier_without_entitlement():
    client = _client()
    with patch("entitlement.access_summary", return_value={"tiers": [], "ic_pdfs_ready": False}):
        res = client.post(
            "/ic-package/pdf",
            json={
                "email": "free@example.com",
                "analysis_data": {
                    "depth_tier": "ic_full",
                    "research_depth": "ic",
                    "ic_pdfs_ready": True,
                    "project_info": {"address": "1 Main", "city": "Dallas", "state": "TX", "zip": "75201"},
                    "contingency_band": {"pct_low": 5, "pct_mid": 8, "pct_high": 12},
                    "margin_killers": [{"title": "x", "priority": "HIGH"}],
                    "fee_card": {"fees": []},
                },
            },
        )
    assert res.status_code == 403


def test_ic_package_rejects_missing_email():
    client = _client()
    res = client.post(
        "/ic-package/pdf",
        json={
            "analysis_data": {
                "depth_tier": "ic_full",
                "ic_pdfs_ready": True,
                "project_info": {"address": "1 Main"},
            }
        },
    )
    assert res.status_code == 403


def test_attach_stamp_does_not_freeze_comments():
    import uuid

    from war_room_store import attach_stamp_snapshot, add_comment, ensure_write_token, freeze_stamp

    rid = f"rg-premortem-stamp-{uuid.uuid4().hex[:10]}"
    out = attach_stamp_snapshot(
        rid,
        {"grade": "CAUTION", "fingerprint": "abc123"},
    )
    assert out.get("stamp_frozen") is False
    tok = ensure_write_token(rid)
    comment = add_comment(
        rid,
        text="Still open for war-room notes",
        author="GC",
        write_token=tok,
        client_key=f"test-premortem-{rid}",
    )
    assert comment.get("text")
    frozen = freeze_stamp(rid)
    assert frozen.get("stamp_frozen") is True
    try:
        add_comment(
            rid,
            text="Should fail",
            author="GC",
            write_token=tok,
            client_key=f"test-premortem-2-{rid}",
        )
        assert False, "expected freeze to block comments"
    except ValueError as e:
        assert "frozen" in str(e).lower()
