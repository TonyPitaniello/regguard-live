"""SAMPLE multi-tier Fort Worth DC site deliverables."""

import io
import zipfile

import pytest

from sample_dc_fixture import SAMPLE_SITE_LINE, analysis_for_tier
from sample_tier_deliverables import (
    generate_free_preview_pdf_bytes,
    generate_ic_bundle_sample_zip_bytes,
    generate_partner_receipt_pdf_bytes,
    generate_pro_desk_zip_bytes,
    generate_tier_ladder_pdf_bytes,
)


def test_sample_fixture_is_fort_worth_dc():
    data = analysis_for_tier("ic")
    pi = data["project_info"]
    assert pi["city"] == "Fort Worth"
    assert pi["type"] == "data-center"
    assert "Chapin" in pi["address"]
    assert "fortworth" in (data["ahj_card"]["fees_url"] or "").lower()
    assert SAMPLE_SITE_LINE.startswith("9999")


def test_tier_ladder_pdf():
    raw = generate_tier_ladder_pdf_bytes()
    assert raw[:4] == b"%PDF"
    assert len(raw) > 2000


def test_free_and_partner_receipts():
    free = generate_free_preview_pdf_bytes()
    partner = generate_partner_receipt_pdf_bytes()
    assert free[:4] == b"%PDF"
    assert partner[:4] == b"%PDF"
    from pypdf import PdfReader

    assert len(PdfReader(io.BytesIO(partner)).pages) == 1


def test_pro_desk_zip():
    raw, name = generate_pro_desk_zip_bytes()
    assert name.endswith(".zip")
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = set(zf.namelist())
    assert "01_BID_RISK_RECEIPT_SAMPLE.pdf" in names
    assert "02_FEE_PUNCH_SCHEDULE_SAMPLE.csv" in names


def test_ic_sample_bundle_matches_pricing_contract():
    pytest.importorskip("docx")
    pytest.importorskip("openpyxl")
    raw, name = generate_ic_bundle_sample_zip_bytes()
    assert "SAMPLE" in name.upper()
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        names = set(zf.namelist())
    assert "01_DECISION_MEMO.pdf" in names
    assert "04_FEE_PUNCH_EVIDENCE.xlsx" in names
    assert "05_EVIDENCE_INDEX.xlsx" in names
    assert "optional/FEE_PUNCH_SCHEDULE.csv" in names
