"""Site finder: one search, beachhead URLs, no neighbor fee rows."""

from site_finder import _DAY_CACHE, beachhead_rows, find_official_sites
from ic_buyer_brief import (
    AUSTIN_APPLY,
    AUSTIN_ENERGY,
    AUSTIN_FEE_PDF,
    AUSTIN_WATER,
    DALLAS_APPLY,
    DALLAS_FEE_PDF,
    DALLAS_WW,
    FW_APPLY,
    FW_FEE,
    FW_WATER,
    ONCOR_INTAKE,
    PLANO_APPLY,
    PLANO_DRAIN,
    PLANO_FEE_PDF,
)


BEACHHEADS = [
    (
        "1950 N Stemmons Fwy",
        "Dallas",
        "TX",
        "75207",
        [DALLAS_FEE_PDF, DALLAS_FEE_PDF, DALLAS_APPLY, DALLAS_WW, ONCOR_INTAKE],
    ),
    (
        "6565 Headquarters Dr",
        "Plano",
        "TX",
        "75024",
        [PLANO_FEE_PDF, PLANO_FEE_PDF, PLANO_APPLY, PLANO_DRAIN, ONCOR_INTAKE],
    ),
    (
        "9020 Metric Blvd",
        "Austin",
        "TX",
        "78758",
        [AUSTIN_FEE_PDF, AUSTIN_FEE_PDF, AUSTIN_APPLY, AUSTIN_WATER, AUSTIN_ENERGY],
    ),
    (
        "13600 Heritage Pkwy",
        "Fort Worth",
        "TX",
        "76177",
        [FW_FEE, FW_FEE, FW_APPLY, FW_WATER, ONCOR_INTAKE],
    ),
]

PHOENIX_PDF = "https://www.phoenix.gov/development/commercial-fee-schedule.pdf"
DALLAS_PDF = DALLAS_FEE_PDF


def setup_function():
    _DAY_CACHE.clear()


def test_beachhead_addresses_use_stored_urls_and_do_not_search():
    def _boom(_query):
        raise AssertionError("beachhead lookup must not search")

    for address, city, state, zip_code, urls in BEACHHEADS:
        found = find_official_sites(
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            county="",
            rung="pro",
            searcher=_boom,
        )
        assert found["searches"] == 0
        assert [row["url"] for row in found["rows"]] == urls
        assert all(row["url"].startswith("https://") for row in found["rows"])
        assert all(row["host"] for row in found["rows"])


def test_second_lookup_same_day_makes_zero_searches():
    calls = {"n": 0}

    def _search(_query):
        calls["n"] += 1
        return [{"url": PHOENIX_PDF, "title": "Phoenix commercial fee schedule"}]

    kwargs = dict(
        address="200 W Washington St",
        city="Phoenix",
        state="AZ",
        zip_code="85003",
        county="Maricopa",
        rung="pro",
        searcher=_search,
    )
    first = find_official_sites(**kwargs)
    second = find_official_sites(**kwargs)
    assert calls["n"] == 1
    assert first["searches"] == 1
    assert second["searches"] == 0
    assert second["cache_hit"] is True
    assert first["rows"][0]["url"] == PHOENIX_PDF


def test_outside_city_does_not_copy_a_beachhead_fee_row():
    def _search(_query):
        return [
            {"url": DALLAS_PDF, "title": "Dallas fee summary"},
            {"url": PHOENIX_PDF, "title": "Phoenix commercial fee schedule"},
            {"url": "https://www.phoenix.gov/", "title": "City of Phoenix home"},
        ]

    found = find_official_sites(
        address="200 W Washington St",
        city="Phoenix",
        state="AZ",
        zip_code="85003",
        county="Maricopa",
        rung="pro",
        searcher=_search,
    )
    urls = [row["url"] for row in found["rows"]]
    assert DALLAS_PDF not in urls
    assert PLANO_FEE_PDF not in urls
    assert AUSTIN_FEE_PDF not in urls
    assert FW_FEE not in urls
    assert found["rows"][0]["job"] == "fee_schedule"
    assert found["rows"][0]["url"] == PHOENIX_PDF
    assert found["rows"][0]["url"] != "https://www.phoenix.gov/"
    assert len(found["rows"]) <= 5


def test_homepage_is_not_the_fee_schedule():
    def _search(_query):
        return [{"url": "https://www.phoenix.gov/", "title": "City of Phoenix"}]

    found = find_official_sites(
        address="200 W Washington St",
        city="Phoenix",
        state="AZ",
        zip_code="85003",
        rung="estimator",
        searcher=_search,
    )
    assert found["rows"] == [
        {
            "job": "fee_schedule",
            "url": "",
            "host": "",
            "why": "No official page for this city.",
            "status": "Unverified",
        }
    ]
    assert len(found["rows"]) == 1


def test_estimator_searches_only_the_fee_job_and_free_does_not():
    calls = {"n": 0}

    def _search(_query):
        calls["n"] += 1
        return [{"url": PHOENIX_PDF, "title": "Phoenix commercial fee schedule"}]

    free = find_official_sites(
        address="200 W Washington St",
        city="Phoenix",
        state="AZ",
        zip_code="85003",
        rung="free",
        searcher=_search,
    )
    assert free["searches"] == 0
    assert free["rows"] == []
    assert calls["n"] == 0

    est = find_official_sites(
        address="200 W Washington St",
        city="Phoenix",
        state="AZ",
        zip_code="85003",
        rung="estimator",
        searcher=_search,
    )
    assert calls["n"] == 1
    assert [row["job"] for row in est["rows"]] == ["fee_schedule"]


def test_pro_daily_cap_blocks_the_search(monkeypatch):
    monkeypatch.setattr(
        "paid_local_confirm.get_paid_local_usage",
        lambda email="": {"allowed": False, "used": 25, "limit": 25},
    )

    def _boom(_query):
        raise AssertionError("capped pro lookup must not search")

    found = find_official_sites(
        address="200 W Washington St",
        city="Phoenix",
        state="AZ",
        zip_code="85003",
        rung="pro",
        email="pro@example.com",
        searcher=_boom,
    )
    assert found["searches"] == 0
    assert all(row["status"] == "Unverified" for row in found["rows"])
    assert beachhead_rows("Phoenix") is None
