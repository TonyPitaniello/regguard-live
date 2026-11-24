"""San Antonio prints a dollar only when the FY 2027 schedule states it."""

import io
import re
import zipfile

from openpyxl import load_workbook
from pypdf import PdfReader

from arbitrage_enrichment import enrich_analysis_with_arbitrage
from bid_sheet_export import analysis_to_bid_csv
from city_pack_pdf import generate_city_pack_pdf_bytes
from ic_diligence_bundle import build_ic_diligence_bundle_zip
from schedule_transcribe import transcribe_page

SA_PDF = "https://docsonline.sanantonio.gov/DSDUploads/CurrentFeeSchedule.pdf"
_DOLLAR = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?")
_PRODUCT = re.compile(r"\$\s?79\b|\$\s?149\b|\$\s?1,500\b|\$\s?15,000\b")


def _pro() -> dict:
    return enrich_analysis_with_arbitrage(
        {
            "project_info": {
                "address": "14720 Omicron Drive",
                "city": "San Antonio",
                "state": "TX",
                "zip": "78245",
                "type": "commercial data center",
            },
            "project_type": "commercial data center",
            "research_depth": "pro",
            "depth_tier": "pro",
            "access_tier": "contractor_pro",
        }
    )


def _pdf(raw: bytes) -> str:
    return "\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(raw)).pages)


def test_stated_flat_lines_match_on_the_pack_and_the_csv():
    data = _pro()
    csv_text = analysis_to_bid_csv(data)
    pack = _pdf(generate_city_pack_pdf_bytes(data)).replace("\n", "")
    assert "CurrentFeeSchedule.pdf" in pack
    assert "$57.50" in pack
    assert "$230" in pack or "$230.00" in pack
    assert "57.5" in csv_text
    assert "230" in csv_text
    blank = [line for line in csv_text.splitlines() if "Commercial permit total" in line]
    assert blank
    for line in blank:
        assert _DOLLAR.search(line) is None
    assert "175" not in csv_text
    assert "feesummary_725" not in pack
    assert "19026" not in csv_text


def test_a_valuation_bracket_is_not_the_permit_and_a_homepage_is_empty():
    text = "\n".join(
        [
            "Revised: October 2026",
            "Commercial and existing residential building plan review and permit fees are based on valuation.",
            "Valuation $0 to $1,000 is $115.00",
            "Electrical - Permit Base Fee $57.50",
            "Commercial Certificate of Occupancy - No Construction Fee $230.00",
        ]
    )
    rows = transcribe_page(text, SA_PDF, city="San Antonio")
    amounts = [row["amount_usd"] for row in rows]
    assert 57.50 in amounts
    assert 230.00 in amounts
    assert 115.00 not in amounts
    blank = [row for row in rows if row["amount_usd"] is None]
    assert blank
    assert all("$" not in (row.get("note") or "") for row in blank)
    assert transcribe_page("Permit fee $500", "https://www.sanantonio.gov/", city="San Antonio") == []


def test_omicron_zip_names_the_three_desks_and_keeps_product_prices_out():
    raw, _name = build_ic_diligence_bundle_zip(
        {
            "project_info": {
                "address": "14720 Omicron Drive",
                "city": "San Antonio",
                "state": "TX",
                "zip": "78245",
                "type": "commercial data center",
            },
            "project_type": "commercial data center",
            "research_depth": "ic",
        },
        generated_for="desktop review",
    )
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = set(zf.namelist())
        assert {
            "01_DECISION_MEMO.pdf",
            "02_IC_DILIGENCE_BOARDROOM.pdf",
            "03_IC_DILIGENCE_COUNSEL.docx",
            "04_FEE_PUNCH_EVIDENCE.xlsx",
            "05_EVIDENCE_INDEX.xlsx",
        } <= names
        assert "README.txt" not in names
        memo = _pdf(zf.read("01_DECISION_MEMO.pdf"))
        board = _pdf(zf.read("02_IC_DILIGENCE_BOARDROOM.pdf"))
        with zipfile.ZipFile(io.BytesIO(zf.read("03_IC_DILIGENCE_COUNSEL.docx"))) as doc:
            counsel = doc.read("word/document.xml").decode("utf-8", errors="replace")
        wb = load_workbook(io.BytesIO(zf.read("04_FEE_PUNCH_EVIDENCE.xlsx")), data_only=True)
        csv_text = zf.read("optional/FEE_PUNCH_SCHEDULE.csv").decode("utf-8")

    flat = " ".join((memo, board, counsel, csv_text))
    assert "HOLD until the commercial permit stays on the valuation table" in memo
    assert "$57.50 is only the electrical permit base fee" in memo.replace("\n", "")
    assert "FAIL" not in memo
    assert "CPS Energy" in memo
    assert "210-353-3333" in memo
    assert "San Antonio Water" in memo
    assert "Development Services" in memo
    assert "57.50" in memo.replace(",", "") or "$57.50" in memo
    assert "MW" not in memo
    assert "queue position" not in memo.lower() or "does not state an ordinal" in memo.lower()
    assert "done" not in memo.lower()
    assert _PRODUCT.search(flat) is None
    assert "confirm with the city" not in flat.lower()
    assert "confirm with the ahj" not in flat.lower()
    assert "$15,000" not in flat and "15000" not in csv_text

    sheet = wb["Fees"]
    headers = [sheet.cell(5, col).value for col in range(1, 20)]
    usd_col = headers.index("Planning USD") + 1
    item_col = headers.index("Item") + 1
    found = {}
    for row in range(6, sheet.max_row + 1):
        label = str(sheet.cell(row, item_col).value or "")
        found[label] = sheet.cell(row, usd_col).value
    assert found.get("Electrical - Permit Base Fee") in (57.5, 57.50)
    assert any(value in (None, "") for label, value in found.items() if "Commercial permit total" in label or "valuation" in label.lower())
