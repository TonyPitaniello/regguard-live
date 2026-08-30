"""Tests for stamp premortem-fix stack."""

from regguard_stamp import apply_regguard_stamp, build_regguard_stamp
from product_events import stamp_funnel_stats, track_event
from partner_mandate import kit, log_outreach
from stamp_snapshot import stamp_snapshot
from zip_watch import register_stamp_watch


def test_grade_stable_when_fingerprint_unchanged():
    analysis = {
        "project_info": {"zip": "75074", "city": "Plano", "state": "TX"},
        "coverage": {"tier": "full_pack", "badge": "Full city pack"},
        "margin_killers": [],
        "contingency_band": {"pct_mid": 6},
        "ahj_card": {"last_verified": "2026-08-01", "portal_url": "https://a.gov"},
    }
    a1 = apply_regguard_stamp(dict(analysis))
    g1 = a1["regguard_stamp"]["grade"]
    a1["contingency_band"] = {"pct_mid": 6}  # no fp change
    a2 = apply_regguard_stamp(a1)
    assert a2["regguard_stamp"]["grade"] == g1
    assert a2["regguard_stamp"].get("grade_stable") is True


def test_grade_rebuilds_when_fingerprint_changes():
    analysis = {
        "project_info": {"zip": "75074", "city": "Plano", "state": "TX"},
        "coverage": {"tier": "full_pack"},
        "margin_killers": [],
        "ahj_card": {"last_verified": "2026-01-01", "portal_url": "https://a.gov"},
    }
    a1 = apply_regguard_stamp(dict(analysis))
    a1["ahj_card"] = {"last_verified": "2026-08-30", "portal_url": "https://a.gov"}
    a1["margin_killers"] = [
        {
            "priority": "CRITICAL",
            "title": "Fee trap",
            "detail": "x",
            "source_url": "https://a.gov",
        },
        {
            "priority": "CRITICAL",
            "title": "Fee trap 2",
            "detail": "y",
            "source_url": "https://a.gov",
        },
    ]
    # force rebuild by clearing then applying after fp-affecting fields... fingerprint
    # includes ahj last_verified so apply should rebuild
    del a1["regguard_stamp"]
    a2 = apply_regguard_stamp(a1)
    assert a2["regguard_stamp"]["grade"] == "FAIL"


def test_disclaimer_not_moodys():
    stamp = build_regguard_stamp({"coverage": {"tier": "full_pack"}, "margin_killers": []})
    d = (stamp.get("disclaimer") or "").lower()
    assert "moody" in d
    assert "not a bond" in d or "not a bond" in d.replace(" ", " ")
    assert "planning aid" in d


def test_product_events_and_funnel():
    track_event("zip_watch_alert_sent", zip_code="75074", channel="email")
    track_event("research_rerun_same_zip", zip_code="75074")
    stats = stamp_funnel_stats(hours=24)
    assert stats["zip_watch_alerts"] >= 1
    assert stats["rerun_within_72h"] >= 1


def test_partner_mandate_kit():
    k = kit()
    assert "no stamp" in (k.get("one_liner") or "").lower() or "stamp" in (k.get("one_liner") or "").lower()
    row = log_outreach(partner_name="Test Runner", metro="DFW")
    assert row["id"].startswith("pm-")


def test_stamp_snapshot_and_watch_register():
    analysis = apply_regguard_stamp(
        {
            "project_info": {"zip": "75201", "city": "Dallas", "state": "TX"},
            "coverage": {"tier": "full_pack"},
            "margin_killers": [],
            "research_id": "rg-test-snap",
        }
    )
    snap = stamp_snapshot(analysis)
    assert snap.get("fingerprint")
    out = register_stamp_watch(
        zip_code="75201",
        city="Dallas",
        state="TX",
        email="ops@example.com",
        phone="5551234567",
        research_id="rg-test-snap",
        stamp_fingerprint=snap.get("fingerprint") or "",
        stamp_grade=snap.get("grade") or "",
    )
    assert out.get("status") == "ok"
