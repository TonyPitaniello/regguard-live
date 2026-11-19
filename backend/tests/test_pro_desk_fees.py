"""Pro desk: the CSV and the City Pack share each schedule figure, and print no other number."""

import io
import re

from arbitrage_enrichment import enrich_analysis_with_arbitrage
from bid_packet_pdf import generate_bid_packet_pdf_bytes
from bid_sheet_export import analysis_to_bid_csv
from bid_sheet_pdf import analysis_to_bid_sheet_pdf
from city_pack_pdf import generate_city_pack_pdf_bytes
from pypdf import PdfReader

_DOLLAR = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?")


def _text(raw: bytes) -> str:
    return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(raw)).pages)


def _pro(address: str, city: str, zip_code: str) -> dict:
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
            "research_depth": "pro",
            "depth_tier": "pro",
            "access_tier": "contractor_pro",
        }
    )


def test_beachhead_pack_and_csv_share_stated_dollars():
    sites = [
        ("1950 N Stemmons Fwy", "Dallas", "75207", ["$175", "$125"], ["175", "125"], "feesummary_725.pdf"),
        ("6565 Headquarters Dr", "Plano", "75024", ["$75", "$130"], ["75", "130"], "civicplus.com"),
        ("9020 Metric Blvd", "Austin", "78758", ["$145.89", "$247.77", "$3,204.30"], ["145.89", "247.77", "3204.3"], "fees_commercial"),
        ("13600 Heritage Pkwy", "Fort Worth", "76177", ["$291", "$33.08", "$19,026.04"], ["291", "33.08", "19026.04"], "fee-schedule-oct-2026.pdf"),
    ]
    for address, city, zip_code, pack_bits, csv_bits, url_bit in sites:
        data = _pro(address, city, zip_code)
        csv_text = analysis_to_bid_csv(data)
        pack = _text(generate_city_pack_pdf_bytes(data))
        sheet = _text(analysis_to_bid_sheet_pdf(data))
        packet = _text(generate_bid_packet_pdf_bytes(data))
        flat = pack.replace("\n", "")
        assert url_bit in flat or url_bit in csv_text
        for bit in pack_bits:
            assert bit in pack, (city, bit, pack[:500])
            assert bit in sheet
        for bit in csv_bits:
            assert bit in csv_text, (city, bit)
        assert "+2%" not in pack and "+2%" not in sheet and "+2%" not in packet
        assert "2.0%-6.0%" not in csv_text
        assert "default.aspx" not in pack and "default.aspx" not in csv_text
        assert "$167" not in pack and "1406" not in csv_text and "$289" not in pack
        if city != "Fort Worth":
            blank = [
                line
                for line in csv_text.splitlines()
                if "New commercial construction permit" in line
                or "Electrical permit total" in line
                or "Commercial permit total" in line
                or "Commercial building permit" in line
            ]
            assert blank
            for line in blank:
                assert _DOLLAR.search(line) is None


def test_chapin_does_not_inherit_the_heritage_table():
    data = _pro("9999 Chapin School Road", "Fort Worth", "76126")
    csv_text = analysis_to_bid_csv(data)
    pack = _text(generate_city_pack_pdf_bytes(data))
    assert "$291" in pack
    assert "19026" not in csv_text
    assert "$19,026" not in pack
    assert "1406" not in csv_text
    assert "$289" not in pack
