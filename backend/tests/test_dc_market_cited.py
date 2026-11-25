"""Data-center markets print a dollar only when that city's schedule states it."""

import io
import re

from pypdf import PdfReader

from arbitrage_enrichment import enrich_analysis_with_arbitrage
from bid_sheet_export import analysis_to_bid_csv
from city_pack_pdf import generate_city_pack_pdf_bytes
from city_packs import resolve_city_pack

_DOLLAR = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?")

SITES = [
    ("Phoenix", "AZ", "195", "fee-schedule.pdf"),
    ("Mesa", "AZ", "263", "development-services-fees.pdf"),
    ("Atlanta", "GA", "25", "zd-p-services"),
    ("Loudoun County", "VA", "65", "Fee-Schedule_2022-Update"),
    ("Prince William County", "VA", "368.45", "12288.pdf"),
    ("New Albany", "OH", "250", "Commercial-Fees-Schedule.pdf"),
    ("Columbus", "OH", "550", "2026-combined-development-related-fee-schedule.pdf"),
    ("Hillsboro", "OR", "64.90", "30163"),
]


def _pro(city: str, state: str) -> dict:
    return enrich_analysis_with_arbitrage(
        {
            "project_info": {
                "address": "1 Commercial Way",
                "city": city,
                "state": state,
                "zip": "",
                "type": "commercial",
            },
            "project_type": "commercial",
            "research_depth": "pro",
            "depth_tier": "pro",
            "access_tier": "contractor_pro",
        }
    )


def test_each_market_prints_its_own_stated_dollar_and_a_blank_permit():
    for city, state, bit, url_bit in SITES:
        data = _pro(city, state)
        csv_text = analysis_to_bid_csv(data)
        pack = "\n".join(
            (page.extract_text() or "") for page in PdfReader(io.BytesIO(generate_city_pack_pdf_bytes(data))).pages
        ).replace("\n", "")
        assert url_bit in pack or url_bit in csv_text, city
        assert bit in csv_text, (city, bit)
        assert bit in pack.replace(",", ""), (city, bit)
        blank = [line for line in csv_text.splitlines() if "Commercial permit total" in line]
        assert blank, city
        for line in blank:
            assert _DOLLAR.search(line) is None, (city, line)
        assert "175" not in csv_text or city == "Atlanta"
        assert "57.50" not in csv_text
        if city == "Atlanta":
            assert "1860" not in csv_text and "1,860" not in pack
        if city == "Loudoun County":
            assert "$70" not in csv_text and "$70" not in pack
        if city == "New Albany":
            assert "$75" not in csv_text and "$30" not in csv_text
        if city == "Columbus":
            assert "225" not in csv_text and "700" not in csv_text


def test_elk_grove_village_stays_off_the_cited_packs():
    assert resolve_city_pack("Elk Grove Village", "IL") is None


def test_a_beachhead_dollar_is_not_copied_onto_phoenix():
    csv_text = analysis_to_bid_csv(_pro("Phoenix", "AZ"))
    assert "feesummary_725" not in csv_text
    assert "19026" not in csv_text
