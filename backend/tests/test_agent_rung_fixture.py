"""Outside-Texas fixture plus the four beachhead addresses.

The fee table is written here. Nothing in this file calls Firecrawl.
"""

import csv
import io
import re
import zipfile

from pypdf import PdfReader

from arbitrage_enrichment import enrich_analysis_with_arbitrage
from bid_risk_receipt_pdf import generate_bid_risk_receipt_pdf_bytes
from bid_sheet_export import analysis_to_bid_csv
from city_pack_pdf import generate_city_pack_pdf_bytes
from habit_ladder_shape import shape_free_vs_estimator
from ic_diligence_bundle import build_ic_diligence_bundle_zip
from schedule_transcribe import apply_transcribed_schedule
from shortlist_scrape import clear_shortlist_cache, scrape_finder_shortlist
from site_finder import _DAY_CACHE, find_official_sites

FEE_PDF = "https://www.bendoregon.gov/development/commercial-fee-schedule.pdf"
TABLE = "\n".join(
    (
        "Commercial plan review base $40.50",
        "Trade permit base $18.25",
        "Building permit total $9,999.00 once square feet are on the application.",
        "The building permit is issued before a trade permit.",
    )
)
STATED = (18.25, 40.50)
_DOLLAR = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?")

BEACHHEAD = (
    ("1950 N Stemmons Fwy", "Dallas", "75207"),
    ("6565 Headquarters Dr", "Plano", "75024"),
    ("9020 Metric Blvd", "Austin", "78758"),
    ("13600 Heritage Pkwy", "Fort Worth", "76177"),
)


def setup_function():
    _DAY_CACHE.clear()
    clear_shortlist_cache()


def _pdf(raw: bytes) -> str:
    return "\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(raw)).pages)


def _dollars(text: str):
    return sorted(float(match.group(0).replace("$", "").replace(",", "").strip()) for match in _DOLLAR.finditer(text))


def _bend(depth: str = "pro") -> dict:
    return {
        "project_info": {
            "address": "710 NW Wall St",
            "city": "Bend",
            "state": "OR",
            "zip": "97701",
            "type": "commercial",
        },
        "project_type": "commercial",
        "research_depth": depth,
        "depth_tier": depth,
        "access_tier": "contractor_pro" if depth == "pro" else depth,
        "margin_killers": [
            {
                "title": "Permit sequence",
                "priority": "HIGH",
                "detail": "The building permit is issued before a trade permit.",
            }
        ],
    }


def _searcher(calls):
    def _search(query):
        calls.append(query)
        return [{"url": FEE_PDF, "title": "Bend commercial fee schedule"}]

    return _search


def _scraper(calls, markdown=TABLE):
    def _scrape(url):
        calls.append(url)
        return {"markdown": markdown, "status": 200}

    return _scrape


def _silence_zip_cache(monkeypatch):
    monkeypatch.setattr(
        "research_cache_interceptor.cache_firecrawl_result",
        lambda *args, **kwargs: True,
    )


def test_phoenix_pro_pack_and_csv_print_only_the_fixture(monkeypatch):
    _silence_zip_cache(monkeypatch)
    searches = []
    scrapes = []
    analysis = _bend("pro")
    analysis["site_finder"] = find_official_sites(
        address="710 NW Wall St",
        city="Bend",
        state="OR",
        zip_code="97701",
        rung="pro",
        searcher=_searcher(searches),
    )
    fee_row = next(row for row in analysis["site_finder"]["rows"] if row["job"] == "fee_schedule")
    assert fee_row["url"] == FEE_PDF
    assert fee_row["url"].rstrip("/").lower() != "https://www.bendoregon.gov"
    scrape_finder_shortlist(
        analysis,
        rung="pro",
        city="Bend",
        state="OR",
        zip_code="97701",
        scraper=_scraper(scrapes),
    )
    assert scrapes == [FEE_PDF]
    assert apply_transcribed_schedule(analysis, city="Bend") is True
    fees = analysis["fee_card"]["fees"]
    stated = sorted(float(row["amount_usd"]) for row in fees if row.get("amount_usd") is not None)
    blank = next(row for row in fees if row["label"] == "Commercial permit total")
    assert stated == sorted(STATED)
    assert blank["amount_usd"] is None
    assert "$" not in str(blank["note"])
    assert "A blank line has no dollar" in str(blank["note"])
    assert "9999" not in str(fees)

    csv_text = analysis_to_bid_csv(analysis)
    pack = _pdf(generate_city_pack_pdf_bytes(analysis))
    flat = pack.replace("\n", "")
    reader = csv.DictReader(io.StringIO(csv_text))
    fee_lines = [row for row in reader if row["section"] == "fee"]
    csv_amounts = sorted(float(row["planning_usd"]) for row in fee_lines if row["planning_usd"])
    blank_csv = next(row for row in fee_lines if row["item"] == "Commercial permit total")
    assert csv_amounts == sorted(STATED)
    assert _dollars(pack) == sorted(STATED)
    assert csv_amounts == _dollars(pack)
    assert blank_csv["planning_usd"] == ""
    assert "$" not in blank_csv["notes"]
    assert "A blank line has no dollar" in blank_csv["notes"]
    assert "Commercial permit total" in pack
    total_at = pack.find("Commercial permit total")
    assert "$" not in pack[total_at : total_at + 80]
    assert "9999" not in csv_text and "9,999" not in pack
    assert FEE_PDF in flat or FEE_PDF in csv_text
    assert "bendoregon.gov / " not in flat and "bendoregon.gov / " not in csv_text
    assert "confirm with the city" not in pack.lower()
    assert "confirm with the city" not in csv_text.lower()
    assert "+2%" not in pack
    assert analysis["firecrawl_credits"]["scrapes"] <= 8
    assert analysis["site_finder"]["searches"] <= 1


def test_phoenix_estimator_receipt_prints_no_dollar_and_one_sourced_punch():
    searches = []
    scrapes = []
    found = find_official_sites(
        address="710 NW Wall St",
        city="Bend",
        state="OR",
        zip_code="97701",
        rung="estimator",
        searcher=_searcher(searches),
    )
    assert found["searches"] <= 1
    assert found["rows"][0]["url"] == FEE_PDF
    analysis = _bend("partner")
    analysis["site_finder"] = found
    analysis["ahj_card"] = {
        "name": "City of Bend",
        "portal_url": "https://www.bendoregon.gov/development/permits",
        "fees_url": FEE_PDF,
        "apply_url": "https://www.bendoregon.gov/development/commercial-permit-application",
    }
    analysis["contingency_band"] = {"pct_low": 0, "pct_mid": 0, "pct_high": 0}
    scrape_finder_shortlist(
        analysis,
        rung="estimator",
        city="Bend",
        state="OR",
        zip_code="97701",
        scraper=_scraper(scrapes),
    )
    analysis["shortlist_pages"] = [{"url": FEE_PDF, "markdown": TABLE}]
    assert scrapes == []
    assert analysis["firecrawl_credits"]["searches"] <= 1
    assert analysis["firecrawl_credits"]["scrapes"] == 0
    shaped = shape_free_vs_estimator(analysis, habit_paid=True)
    text = _pdf(generate_bid_risk_receipt_pdf_bytes(shaped, generated_for="est@example.com"))
    flat = text.replace("\n", "")
    assert "$" not in text
    assert "BID RISK RECEIPT - ESTIMATOR HABIT" in text
    assert "issued before" in text.lower()
    assert "Source" in text
    assert "Permit runner" in text
    assert "Before bid" in text
    assert text.count("Portal:") == 1
    assert text.count("Fee schedule:") == 1
    assert text.count("Apply:") == 1
    assert FEE_PDF in flat
    assert "bendoregon.gov / " not in flat
    assert "City Pack" not in text
    assert "confirm with the city" not in text.lower()


def test_free_makes_zero_firecrawl_calls():
    def _search(_query):
        raise AssertionError("free search")

    def _scrape(_url):
        raise AssertionError("free scrape")

    analysis = _bend("free")
    analysis["site_finder"] = find_official_sites(
        address="710 NW Wall St",
        city="Bend",
        state="OR",
        zip_code="97701",
        rung="free",
        searcher=_search,
    )
    scrape_finder_shortlist(
        analysis,
        rung="free",
        city="Bend",
        state="OR",
        zip_code="97701",
        scraper=_scrape,
    )
    credits = analysis["firecrawl_credits"]
    assert analysis["site_finder"]["searches"] == 0
    assert analysis["site_finder"]["rows"] == []
    assert credits["searches"] == 0
    assert credits["scrapes"] == 0


def test_credit_log_caps_and_same_day_repeat_is_zero(monkeypatch):
    _silence_zip_cache(monkeypatch)
    monkeypatch.delenv("PAID_LOCAL_CONFIRM_MAX_PAGES", raising=False)
    monkeypatch.delenv("IC_PAID_LOCAL_CONFIRM_MAX_PAGES", raising=False)

    free = _bend("free")
    free["site_finder"] = find_official_sites(
        address="720 NW Wall St",
        city="Bend",
        state="OR",
        zip_code="97701",
        rung="free",
        searcher=lambda _query: (_ for _ in ()).throw(AssertionError("free search")),
    )
    scrape_finder_shortlist(
        free,
        rung="free",
        scraper=lambda _url: (_ for _ in ()).throw(AssertionError("free scrape")),
    )
    assert free["site_finder"]["searches"] == 0
    assert free["firecrawl_credits"]["scrapes"] == 0

    searches = []
    estimator = find_official_sites(
        address="730 NW Wall St",
        city="Bend",
        state="OR",
        zip_code="97701",
        rung="estimator",
        searcher=_searcher(searches),
    )
    again = find_official_sites(
        address="730 NW Wall St",
        city="Bend",
        state="OR",
        zip_code="97701",
        rung="estimator",
        searcher=_searcher(searches),
    )
    assert estimator["searches"] == 1
    assert again["searches"] == 0
    assert len(searches) == 1
    estimate = _bend("partner")
    estimate["site_finder"] = estimator
    scrape_finder_shortlist(
        estimate,
        rung="estimator",
        scraper=lambda _url: (_ for _ in ()).throw(AssertionError("estimator scrape")),
    )
    assert estimate["firecrawl_credits"]["scrapes"] == 0

    pro_urls = [f"https://www.bendoregon.gov/fees/page-{index}" for index in range(10)]
    pro = _bend("pro")
    pro["site_finder"] = {
        "searches": 1,
        "rows": [{"job": "fee_schedule", "url": url, "status": "Source"} for url in pro_urls],
    }
    scrape_finder_shortlist(
        pro,
        rung="pro",
        city="Bend",
        state="OR",
        zip_code="97701",
        scraper=_scraper([]),
    )
    assert pro["firecrawl_credits"]["scrapes"] <= 8
    assert pro["firecrawl_credits"]["scrapes"] == 8
    scrape_finder_shortlist(
        pro,
        rung="pro",
        city="Bend",
        state="OR",
        zip_code="97701",
        scraper=lambda _url: (_ for _ in ()).throw(AssertionError("same-day scrape")),
    )
    assert pro["firecrawl_credits"]["scrapes"] == 0
    assert pro["firecrawl_credits"]["cache_hits"] == 8

    ic_urls = [f"https://www.bendoregon.gov/ordinance/page-{index}" for index in range(14)]
    ic = _bend("pro")
    ic["research_depth"] = "ic"
    ic["site_finder"] = {
        "searches": 1,
        "rows": [{"job": "ordinance", "url": url, "status": "Source"} for url in ic_urls],
    }
    scrape_finder_shortlist(
        ic,
        rung="ic",
        city="Bend",
        state="OR",
        zip_code="97701",
        scraper=_scraper([]),
    )
    assert ic["firecrawl_credits"]["scrapes"] <= 12
    assert ic["firecrawl_credits"]["scrapes"] == 12


def _pack(address: str, city: str, zip_code: str, depth: str) -> dict:
    tier = {
        "free": "free",
        "partner": "partner",
        "pro": "contractor_pro",
        "ic": "ic",
    }[depth]
    return enrich_analysis_with_arbitrage(
        {
            "project_info": {
                "address": address,
                "city": city,
                "state": "TX",
                "zip": zip_code,
                "type": "commercial",
            },
            "project_type": "commercial",
            "research_depth": "ic" if depth == "ic" else depth,
            "depth_tier": "ic_full" if depth == "ic" else depth,
            "access_tier": tier,
        }
    )


def _zip_text(raw: bytes) -> str:
    parts = []
    with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
        for name in bundle.namelist():
            if name.lower().endswith(".pdf"):
                parts.append(_pdf(bundle.read(name)))
    return "\n".join(parts)


def _csv_planning(csv_text: str, label: str) -> str:
    for row in csv.DictReader(io.StringIO(csv_text)):
        if row["section"] == "fee" and row["item"] == label:
            return row["planning_usd"]
    raise AssertionError(label)


def test_beachhead_free_estimator_pro_and_ic_keep_the_schedule():
    free_needles = {
        "Dallas": ("DallasNow record type", "Commercial%20New%20Construction"),
        "Plano": ("Electronic submittal", "civicplus.com"),
        "Austin": ("commercial plan review", "commercial-plan-review"),
        "Fort Worth": ("building permit is issued before a trade", "permits/commercial"),
    }
    for address, city, zip_code in BEACHHEAD:
        needle, url_bit = free_needles[city]
        free = _pdf(
            generate_bid_risk_receipt_pdf_bytes(
                {
                    "project_info": {
                        "address": address,
                        "city": city,
                        "state": "TX",
                        "zip": zip_code,
                        "type": "commercial",
                    },
                    "research_depth": "free",
                    "receipt_mode": "free_preview",
                },
                generated_for="free@example.com",
            )
        )
        assert needle in free
        assert url_bit in free.replace("\n", "")
        assert "$175" not in free and "$291" not in free and "$75" not in free

        receipt = _pdf(
            generate_bid_risk_receipt_pdf_bytes(
                shape_free_vs_estimator(
                    {
                        "project_info": {
                            "address": address,
                            "city": city,
                            "state": "TX",
                            "zip": zip_code,
                            "type": "commercial",
                        },
                        "project_type": "commercial",
                        "research_depth": "partner",
                    },
                    habit_paid=True,
                ),
                generated_for="est@example.com",
            )
        )
        assert needle in receipt
        assert "Source" in receipt
        assert "Permit runner" in receipt
        assert "$175" not in receipt
        assert "confirm with the city" not in receipt.lower()

        pro = _pack(address, city, zip_code, "pro")
        csv_text = analysis_to_bid_csv(pro)
        pack = _pdf(generate_city_pack_pdf_bytes(pro))
        flat = pack.replace("\n", "")
        if city == "Dallas":
            assert "$175" in pack and "$125" in pack
            assert "175" in csv_text and "125" in csv_text
            assert "feesummary_725.pdf" in flat or "feesummary_725.pdf" in csv_text
            assert _csv_planning(csv_text, "New commercial construction permit") == ""
        elif city == "Plano":
            for bit in ("$70", "$90", "$110", "$130", "$75"):
                assert bit in pack, bit
            for bit in ("70", "90", "110", "130", "75"):
                assert bit in csv_text
            assert _csv_planning(csv_text, "Electrical permit total") == ""
        elif city == "Austin":
            for bit in ("$145.89", "$250", "$3,204.30", "$247.77", "$339.52", "$276.16", "$378.11", "$70.98"):
                assert bit in pack, bit
            assert _csv_planning(csv_text, "Commercial permit total") == ""
        else:
            for bit in ("$291", "$113", "$33.08", "$16.87", "$19,026.04"):
                assert bit in pack, bit
            for bit in ("291", "113", "33.08", "16.87", "19026.04"):
                assert bit in csv_text
        assert "+2%" not in pack
        assert "confirm with the city" not in pack.lower()
        assert "gov / " not in flat and "com / " not in flat

        ic_raw, _name = build_ic_diligence_bundle_zip(
            {
                "project_info": {
                    "address": address,
                    "city": city,
                    "state": "TX",
                    "zip": zip_code,
                    "type": "commercial",
                },
                "project_type": "commercial",
                "research_depth": "ic",
            }
        )
        ic_text = _zip_text(ic_raw)
        if city == "Dallas":
            assert "$175" in ic_text and "$125" in ic_text
            assert "feesummary_725.pdf" in ic_text.replace("\n", "")
        elif city == "Plano":
            for bit in ("$70", "$90", "$110", "$130", "$75"):
                assert bit in ic_text, bit
        elif city == "Austin":
            for bit in ("$145.89", "$247.77", "$3,204.30"):
                assert bit in ic_text, bit
        else:
            for bit in ("$291", "$113", "$33.08", "$16.87", "$19,026.04"):
                assert bit in ic_text, bit

    chapin = _pack("9999 Chapin School Road", "Fort Worth", "76126", "pro")
    chapin_csv = analysis_to_bid_csv(chapin)
    chapin_pack = _pdf(generate_city_pack_pdf_bytes(chapin))
    assert "$291" in chapin_pack
    assert "19026" not in chapin_csv
    assert "$19,026" not in chapin_pack
