"""Passive campaign: metros, share params, drip, crawlable /share HTML."""

from __future__ import annotations

from nurture_store import (
    cancel_free_run_for_email,
    due_nurture,
    schedule_free_run_drip,
    schedule_quota_paywall,
)
from passive_campaign import (
    drip_email,
    metro_by_slug,
    metro_pages,
    robots_txt,
    sitemap_xml,
    with_share_params,
)
from share_html import render_share_html


def test_metros_cover_city_packs():
    pages = metro_pages()
    slugs = {m["slug"] for m in pages}
    for expected in (
        "plano",
        "dallas",
        "austin",
        "frisco",
        "fort-worth",
        "round-rock",
        "arlington",
        "irving",
        "garland",
        "mckinney",
        "richardson",
        "carrollton",
        "houston",
        "san-antonio",
    ):
        assert expected in slugs, expected
    assert metro_by_slug("fort-worth-permit-fees")["city"] == "Fort Worth"
    by_slug = {m["slug"]: m for m in pages}
    dallas = " ".join(by_slug["dallas"]["bullets"])
    austin = " ".join(by_slug["austin"]["bullets"])
    irving = " ".join(by_slug["irving"]["bullets"])
    plano_fees = " ".join(by_slug["plano"]["fee_summary"])
    assert "ERCOT" not in dallas and "TDSP" not in dallas
    assert "Estimator" in dallas and "Estimator" in austin
    assert "$1,500" in austin and "not this page" in austin
    assert "sales force" not in irving.lower()
    frisco_fees = " ".join(by_slug["frisco"]["fee_summary"]).lower()
    irving_fees = " ".join(by_slug["irving"]["fee_summary"]).lower()
    houston_fees = " ".join(by_slug["houston"]["fee_summary"]).lower()
    sa_fees = " ".join(by_slug["san-antonio"]["fee_summary"]).lower()
    assert "80%" in frisco_fees and "reinspection" in frisco_fees
    assert "not the permit total" in frisco_fees
    assert "$0.45" in irving_fees and "not a permit total" in irving_fees
    assert "valuation" in houston_fees and "permit total" in houston_fees
    assert "fy 2027" in sa_fees and "permit total" in sa_fees
    assert "reinspection" in plano_fees.lower()
    assert "$75" not in " ".join(
        bit for bit in by_slug["plano"]["fee_summary"] if "reinspection" not in bit.lower()
    )
    xml = sitemap_xml(base="https://app.regguardagent.com")
    assert "/frisco-permit-fees" in xml
    assert "/permit-fees" in xml
    assert "/how-it-works" in xml
    assert "/install" in xml
    assert "/privacy" in xml
    robots = robots_txt()
    assert "Sitemap:" in robots
    assert "Disallow: /admin" in robots
    from pathlib import Path

    public = Path(__file__).resolve().parents[2] / "frontend" / "public" / "sitemap.xml"
    static_xml = public.read_text(encoding="utf-8")
    for path in (
        "/",
        "/pricing",
        "/how-it-works",
        "/install",
        "/fort-worth-permit-fees",
        "/austin-permit-fees",
        "/privacy",
        "/terms",
    ):
        assert f"https://app.regguardagent.com{path}<" in static_xml.replace("\n", "") or (
            f"https://app.regguardagent.com{path}</loc>" in static_xml
        )


def test_free_share_hides_band_percent_and_keeps_campaign():
    import json

    from sample_dc_fixture import analysis_for_tier
    from research_store import redact_for_public_share

    url = with_share_params("https://app.regguardagent.com/r/rg-sample-chapin-free", ref="patx")
    assert "ref=patx" in url
    assert "utm_campaign=rg_passive_beachhead_2026" in url
    assert "/r/rg-sample-chapin-free" in url

    red = redact_for_public_share(analysis_for_tier("free"))
    blob = json.dumps(red)
    assert "23%" not in blob
    assert "mid 23" not in blob
    assert red["contingency_band"]["share_frosted"] is True
    assert red["contingency_band"]["pct_mid"] is None
    html = render_share_html(analysis_for_tier("free"), research_id="rg-sample-chapin-free", ref="patx")
    assert "Hidden on Free" in html
    assert "FAIL" not in html
    assert "PASS" not in html
    assert "Partner" not in html
    assert ".zip" not in html
    assert "utm_campaign=rg_passive_beachhead_2026" in html
    for kind in ("free_run_d2", "free_run_d5", "quota_paywall"):
        _, drip = drip_email(kind, {"email": "a@b.com", "research_id": "rid1", "city": "Fort Worth"})
        assert "Start Estimator" not in drip


def test_share_params_add_ref_and_utm():
    url = with_share_params("https://app.regguardagent.com/r/abc123", ref="patx")
    assert "ref=patx" in url
    assert "utm_source=receipt" in url
    assert "utm_campaign=rg_passive_beachhead_2026" in url


def test_drip_copy_has_ctas():
    subj, html = drip_email(
        "free_run_d2",
        {"email": "a@b.com", "research_id": "rid1", "address": "100 Main", "city": "Plano"},
    )
    assert "HOLD" in subj or "HOLD" in html
    assert "does not unlock" in html
    assert "/r/rid1" in html
    assert "Stop these notes" in html
    assert "/email/opt-out" in html
    assert "Partner" not in html
    _, html5 = drip_email("free_run_d5", {"email": "a@b.com", "research_id": "rid1"})
    assert "checkout/" not in html5
    assert "Start Estimator" not in html5
    assert "a card is not charged" in html5
    assert "/r/rid1" in html5
    assert "Estimator" in html5
    assert "Partner" not in html5
    _, htmlq = drip_email("quota_paywall", {"email": "a@b.com"})
    assert "79" in htmlq
    assert "149" in htmlq
    assert "1,500" in htmlq
    assert "Estimator" in htmlq
    assert "checkout/" not in htmlq
    assert "Start Estimator" not in htmlq
    assert "a card is not charged" in htmlq
    assert "Free Lookups" in htmlq


def test_live_drip_opens_estimator_checkout(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_example")
    _, html5 = drip_email("free_run_d5", {"email": "a@b.com", "research_id": "rid1"})
    assert "checkout/partner" in html5
    assert "$79/month" in html5
    assert "a card is not charged" not in html5.lower()
    assert "Partner" not in html5
    _, htmlq = drip_email("quota_paywall", {"email": "a@b.com"})
    assert "checkout/partner" in htmlq
    assert "did not charge you for the blocked run" in htmlq
    assert "a card is not charged" not in htmlq.lower()
    _, html2 = drip_email("free_run_d2", {"email": "a@b.com", "research_id": "rid1"})
    assert "checkout/" not in html2
    assert "No card" in html2


def test_nurture_drip_schedule_and_cancel(tmp_path, monkeypatch):
    import nurture_store

    monkeypatch.setenv("REGGUARD_DATA_DIR", str(tmp_path))
    nurture_store._ITEMS = {}
    out = schedule_free_run_drip(
        email="est@example.com",
        research_id="r1",
        share_url="https://app.regguardagent.com/r/r1",
        city="Plano",
    )
    assert out["d2"] and out["d5"]
    qp = schedule_quota_paywall(email="est@example.com")
    assert qp
    due_now = due_nurture(kinds=["quota_paywall"])
    assert any(i["kind"] == "quota_paywall" for i in due_now)
    n = cancel_free_run_for_email("est@example.com")
    assert n >= 2


def test_opt_out_stops_later_drip(tmp_path, monkeypatch):
    import nurture_store
    from nurture_store import opt_out_marketing, schedule_free_run_drip

    monkeypatch.setenv("REGGUARD_DATA_DIR", str(tmp_path))
    nurture_store._ITEMS = {}
    opt_out_marketing("stop@example.com")
    out = schedule_free_run_drip(email="stop@example.com", research_id="r2", city="Plano")
    assert out["d2"] is None
    assert out["d5"] is None


def test_share_html_og_tags():
    html = render_share_html(
        {
            "project_info": {"address": "123 Main", "city": "Plano", "state": "TX", "zip": "75074"},
            "regguard_stamp": {"grade": "CAUTION"},
            "contingency_band": {"pct_low": 8, "pct_high": 15, "pct_mid": 11},
            "margin_killers": [{"title": "Plano grounding rods", "priority": "CRITICAL"}],
            "ahj_card": {"name": "City of Plano Building Inspections"},
        },
        research_id="rg-testshare",
        ref="patx",
    )
    assert "og:title" in html
    assert "material bid risk" in html
    assert "FAIL" not in html
    html_fail = render_share_html(
        {
            "project_info": {"address": "123 Main", "city": "Plano", "state": "TX", "zip": "75074"},
            "regguard_stamp": {"grade": "FAIL"},
            "contingency_band": {"pct_low": 8, "pct_high": 15, "pct_mid": 11},
            "margin_killers": [{"title": "Plano grounding rods", "priority": "CRITICAL"}],
            "ahj_card": {"name": "City of Plano Building Inspections"},
        },
        research_id="rg-testshare-fail",
    )
    assert "Hold — Bid Risk Receipt" in html_fail
    assert "REGGUARD STAMP: HOLD" in html_fail
    assert "FAIL" not in html_fail
    assert 'content="Hold — Bid Risk Receipt' in html_fail
    assert "Run my address" in html
    assert "ref=patx" in html
    assert "checkout/partner" in html
    assert "Re-run before you submit the bid" in html
