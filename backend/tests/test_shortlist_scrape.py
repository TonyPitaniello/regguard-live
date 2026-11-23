"""Firecrawl runs only on the finder shortlist."""

from datetime import datetime, timedelta, timezone

import shortlist_scrape
from shortlist_scrape import scrape_finder_shortlist


FEE = "https://www.phoenix.gov/development/commercial-fee-schedule.pdf"
APPLY = "https://www.phoenix.gov/development/apply"
OTHER = "https://example.com/not-on-the-list"


def _analysis():
    return {
        "research_depth": "pro",
        "fee_card": {"fees": [{"label": "kept", "amount_usd": 10}]},
        "site_finder": {
            "searches": 1,
            "rows": [
                {"job": "fee_schedule", "url": FEE, "status": "Source"},
                {"job": "permit_application", "url": APPLY, "status": "Source"},
                {"job": "water_desk", "url": "", "status": "Unverified"},
            ],
        },
    }


def setup_function():
    shortlist_scrape.clear_shortlist_cache()


def test_free_and_estimator_scrape_nothing():
    def _boom(_url):
        raise AssertionError("this rung must not scrape")

    for rung in ("free", "estimator"):
        out = scrape_finder_shortlist(
            _analysis(),
            rung=rung,
            city="Phoenix",
            state="AZ",
            zip_code="85003",
            scraper=_boom,
        )
        assert out["firecrawl_credits"]["scrapes"] == 0
        assert out["shortlist_pages"] == []


def test_pro_scrapes_only_the_shortlist_and_caches_the_day(monkeypatch):
    monkeypatch.setattr(
        "research_cache_interceptor.cache_firecrawl_result",
        lambda *args, **kwargs: True,
    )
    calls = []

    def _scrape(url):
        calls.append(url)
        if url == FEE:
            return {"markdown": "Fee schedule $40", "status": 200, "url": url}
        return {"markdown": "Apply here", "status": 200, "url": url}

    first = scrape_finder_shortlist(
        _analysis(),
        rung="pro",
        city="Phoenix",
        state="AZ",
        zip_code="85003",
        scraper=_scrape,
    )
    second = scrape_finder_shortlist(
        _analysis(),
        rung="pro",
        city="Phoenix",
        state="AZ",
        zip_code="85003",
        scraper=_scrape,
    )
    assert calls == [FEE, APPLY]
    assert OTHER not in calls
    assert first["firecrawl_credits"]["scrapes"] == 2
    assert first["firecrawl_credits"]["searches"] == 1
    assert second["firecrawl_credits"]["scrapes"] == 0
    assert second["firecrawl_credits"]["cache_hits"] == 2


def test_403_is_unverified_and_is_not_retried():
    calls = {"n": 0}

    def _scrape(url):
        calls["n"] += 1
        if url == FEE:
            raise RuntimeError("HTTP 403 from the host")
        return {"markdown": "Apply here", "status": 200, "url": url}

    out = scrape_finder_shortlist(
        _analysis(),
        rung="pro",
        city="Phoenix",
        state="AZ",
        zip_code="85003",
        scraper=_scrape,
    )
    fee = next(page for page in out["shortlist_pages"] if page["url"] == FEE)
    assert fee["verified"] == "Unverified"
    assert fee["status"] == 403
    assert fee["markdown"] == ""
    assert calls["n"] == 2


def test_timeout_retries_once():
    calls = {"n": 0}

    def _scrape(url):
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("timed out")
        return {"markdown": "Fee schedule", "status": 200, "url": url}

    out = scrape_finder_shortlist(
        {
            "site_finder": {
                "searches": 0,
                "rows": [{"job": "fee_schedule", "url": FEE}],
            }
        },
        rung="pro",
        city="Phoenix",
        state="AZ",
        zip_code="85003",
        scraper=_scrape,
    )
    assert calls["n"] == 2
    assert out["shortlist_pages"][0]["verified"] == "Source"


def test_credit_ceiling_stops_and_keeps_the_cached_page(monkeypatch):
    monkeypatch.setattr(shortlist_scrape, "PRO_CREDIT_CEILING", 17)
    monkeypatch.setattr(
        "research_cache_interceptor.cache_firecrawl_result",
        lambda *args, **kwargs: True,
    )
    calls = []

    def _scrape(url):
        calls.append(url)
        return {"markdown": "page", "status": 200, "url": url}

    out = scrape_finder_shortlist(
        _analysis(),
        rung="pro",
        city="Phoenix",
        state="AZ",
        zip_code="85003",
        scraper=_scrape,
    )
    assert calls == [FEE]
    assert out["firecrawl_credits"]["stopped_for_ceiling"] is True
    assert out["firecrawl_credits"]["scrapes"] == 1


def test_recheck_uses_a_week_old_cache_and_scrapes_only_after_seven_days():
    moment = datetime(2026, 11, 1, tzinfo=timezone.utc)

    def _scrape(url):
        return {"markdown": "Fee schedule", "status": 200, "url": url}

    scrape_finder_shortlist(
        _analysis(),
        rung="pro",
        city="Phoenix",
        state="AZ",
        zip_code="85003",
        scraper=_scrape,
        now=moment,
    )
    calls = {"n": 0}

    def _later(url):
        calls["n"] += 1
        return {"markdown": "new fee 999", "status": 200, "url": url}

    within = scrape_finder_shortlist(
        _analysis(),
        rung="pro",
        city="Phoenix",
        state="AZ",
        zip_code="85003",
        recheck=True,
        scraper=_later,
        now=moment + timedelta(days=6),
    )
    assert calls["n"] == 0
    assert within["firecrawl_credits"]["cache_hits"] == 2

    after = scrape_finder_shortlist(
        _analysis(),
        rung="pro",
        city="Phoenix",
        state="AZ",
        zip_code="85003",
        recheck=True,
        scraper=_later,
        now=moment + timedelta(days=8),
    )
    assert calls["n"] == 2
    assert after["firecrawl_credits"]["scrapes"] == 2


def test_page_cap_stops_the_pro_scrape(monkeypatch):
    monkeypatch.setattr("paid_local_confirm.max_pages", lambda ic_deepen=False: 1)
    calls = []

    def _scrape(url):
        calls.append(url)
        return {"markdown": "page", "status": 200, "url": url}

    out = scrape_finder_shortlist(
        _analysis(),
        rung="pro",
        city="Phoenix",
        state="AZ",
        zip_code="85003",
        scraper=_scrape,
    )
    assert calls == [FEE]
    assert out["firecrawl_credits"]["scrapes"] == 1
