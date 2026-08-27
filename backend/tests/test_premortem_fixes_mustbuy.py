"""Tests for premortem reliability fixes + buildable must-buy gaps."""

import os

from dc_diligence import radar_stale_meta, stamp_dc_diligence
from diligence_webhook import sign_body
from receipt_attach import attach_receipt, list_attachments
from war_room_store import add_comment, ensure_write_token, list_comments, room_meta
from zip_watch import seed_dc_watches, watch_health


def test_radar_stale_meta_fresh_and_stale():
    fresh = radar_stale_meta({"updated": "2026-08-27"}, stale_after_days=14)
    assert fresh["is_stale"] is False
    stale = radar_stale_meta({"updated": "2026-01-01"}, stale_after_days=14)
    assert stale["is_stale"] is True
    assert "do not treat as current law" in (stale.get("stale_banner") or "")


def test_stamp_suppresses_high_alert_when_stale(monkeypatch):
    # Force stale by pointing updated far past
    import dc_diligence as dd

    monkeypatch.setattr(
        dd,
        "load_moratorium_radar",
        lambda: {
            "updated": "2025-01-01",
            "metros": [
                {
                    "metro": "Northern Virginia / Loudoun",
                    "state": "VA",
                    "status": "high_watch",
                    "summary": "test",
                }
            ],
        },
    )
    out = stamp_dc_diligence(
        {
            "project_info": {
                "type": "data_center",
                "city": "Ashburn",
                "state": "VA",
                "zip": "20147",
                "notes": "150 MW",
            }
        }
    )
    radar = out.get("moratorium_radar") or {}
    assert radar.get("is_stale") is True
    assert radar.get("high_alert_state") is False
    assert radar.get("high_alert_suppressed_stale") is True


def test_war_room_requires_token():
    rid = "rg-test-wr-token-1"
    token = ensure_write_token(rid)
    assert token
    meta = room_meta(rid)
    assert meta.get("token_required") is True
    try:
        add_comment(rid, author="A", text="no token", write_token="")
        assert False, "expected ValueError"
    except ValueError:
        pass
    c = add_comment(rid, author="A", role="ic", text="ok", write_token=token)
    assert c["id"].startswith("wr-")
    assert any(x["id"] == c["id"] for x in list_comments(rid))


def test_zip_watch_seed_and_health():
    os.environ["ZIP_WATCH_SELF_HEAL"] = "0"
    seeded = seed_dc_watches()
    assert seeded["watched_zip_count"] >= 10
    health = watch_health(stale_after_hours=26.0)
    assert "watched_zip_count" in health


def test_receipt_attach_and_webhook_sign():
    row = attach_receipt(
        research_id="rg-att-1",
        external_system="procore",
        external_project_id="proj-99",
        share_url="https://app.regguardagent.com/r/rg-att-1",
    )
    assert row["id"].startswith("att-")
    assert list_attachments("rg-att-1")
    sig = sign_body(b'{"a":1}', "secret")
    assert len(sig) == 64
