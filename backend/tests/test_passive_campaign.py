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
    ):
        assert expected in slugs, expected
    assert metro_by_slug("fort-worth-permit-fees")["city"] == "Fort Worth"
    xml = sitemap_xml(base="https://app.regguardagent.com")
    assert "/frisco-permit-fees" in xml
    assert "/permit-fees" in xml
    robots = robots_txt()
    assert "Sitemap:" in robots
    assert "Disallow: /admin" in robots


def test_share_params_add_ref_and_utm():
    url = with_share_params("https://app.regguardagent.com/r/abc123", ref="patx")
    assert "ref=patx" in url
    assert "utm_source=receipt" in url
    assert "utm_campaign=bid_risk_receipt" in url


def test_drip_copy_has_ctas():
    subj, html = drip_email(
        "free_run_d2",
        {"email": "a@b.com", "research_id": "rid1", "address": "100 Main", "city": "Plano"},
    )
    assert "Forward" in subj or "forward" in html.lower()
    assert "/r/rid1" in html
    _, html5 = drip_email("free_run_d5", {"email": "a@b.com", "research_id": "rid1"})
    assert "checkout/partner" in html5
    _, htmlq = drip_email("quota_paywall", {"email": "a@b.com"})
    assert "79" in htmlq


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
    assert "123 Main" in html
    assert "Run my address" in html
    assert "ref=patx" in html
    assert "checkout/partner" in html
