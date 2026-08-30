"""Tests for RegGuard Stamp v2 — PASS/CAUTION/FAIL + staleness."""

from datetime import datetime, timedelta, timezone

from regguard_stamp import (
    apply_regguard_stamp,
    build_regguard_stamp,
    compute_ground_truth_fingerprint,
    evaluate_stamp_freshness,
    zip_watch_stamp_notice,
)


def test_stamp_pass_on_clean_pack():
    stamp = build_regguard_stamp(
        {
            "project_info": {"city": "Plano", "state": "TX", "zip": "75074"},
            "coverage": {"tier": "full_pack", "badge": "Full city pack"},
            "margin_killers": [],
            "contingency_band": {"pct_mid": 6},
            "ahj_card": {"name": "Plano", "portal_url": "https://example.gov", "last_verified": "2026-08-01"},
        }
    )
    assert stamp["grade"] == "PASS"
    assert stamp["fingerprint"]
    assert stamp["valid_until"]


def test_stamp_fail_on_moratorium_high_alert():
    stamp = build_regguard_stamp(
        {
            "project_info": {"city": "Ashburn", "state": "VA", "zip": "20147"},
            "moratorium_radar": {"high_alert_state": True, "headline": "HIGH ALERT VA"},
            "margin_killers": [],
            "coverage": {"tier": "full_pack"},
        }
    )
    assert stamp["grade"] == "FAIL"


def test_stamp_caution_on_one_critical():
    stamp = build_regguard_stamp(
        {
            "project_info": {"zip": "75201", "city": "Dallas", "state": "TX"},
            "margin_killers": [
                {
                    "priority": "CRITICAL",
                    "title": "Trade fee schedule",
                    "detail": "Confirm electrical min",
                    "source_url": "https://example.gov/fees",
                }
            ],
            "coverage": {"tier": "full_pack"},
            "contingency_band": {"pct_mid": 8},
        }
    )
    assert stamp["grade"] == "CAUTION"
    assert stamp["drivers"]


def test_stamp_stale_on_fingerprint_change():
    analysis = {
        "project_info": {"zip": "75074", "city": "Plano", "state": "TX"},
        "ahj_card": {"last_verified": "2026-01-01", "portal_url": "https://a.gov"},
        "coverage": {"tier": "full_pack"},
        "margin_killers": [],
    }
    stamped = apply_regguard_stamp(dict(analysis))
    stamp = stamped["regguard_stamp"]
    analysis2 = dict(analysis)
    analysis2["ahj_card"] = {"last_verified": "2026-08-29", "portal_url": "https://a.gov"}
    fresh = evaluate_stamp_freshness(stamp, analysis=analysis2)
    assert fresh["is_stale"] is True
    assert "fingerprint" in (fresh.get("stale_reason") or "").lower() or "ground truth" in (
        fresh.get("stale_reason") or ""
    ).lower()


def test_stamp_stale_on_expiry():
    stamp = build_regguard_stamp({"coverage": {"tier": "full_pack"}, "margin_killers": []})
    past = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    stamp["valid_until"] = past
    fresh = evaluate_stamp_freshness(stamp)
    assert fresh["is_stale"] is True


def test_stamp_no_pass_on_thin_coverage():
    stamp = build_regguard_stamp(
        {
            "project_info": {"zip": "99999", "city": "Nowhere", "state": "XX"},
            "margin_killers": [],
            "coverage": {"tier": "thin", "badge": "Thin / Unverified"},
            "contingency_band": {"pct_mid": 5},
        }
    )
    assert stamp["grade"] == "CAUTION"
    assert stamp["grade"] != "PASS"


def test_zip_watch_notice_and_fp_stable():
    notice = zip_watch_stamp_notice({"zip": "75074"})
    assert "75074" in notice
    assert "outdated" in notice.lower() or "PASS" in notice
    a = {
        "project_info": {"zip": "75074"},
        "ahj_card": {"last_verified": "2026-08-01"},
        "coverage": {"tier": "full_pack"},
    }
    assert compute_ground_truth_fingerprint(a) == compute_ground_truth_fingerprint(a)
