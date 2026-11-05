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
    from pypdf import PdfReader

    text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(raw)).pages)
    assert "does not unlock" in text
    assert "to unlock the rest" not in text
    assert "until forward" not in text


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
    assert "02_BID_PACKET_SAMPLE.pdf" in names
    assert "03_FEE_PUNCH_SCHEDULE_SAMPLE.csv" in names
    assert "04_CITY_PACK_SAMPLE.pdf" in names


def _pdf_text(raw: bytes) -> str:
    from pypdf import PdfReader

    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(raw)).pages)


def _docx_text(raw: bytes) -> str:
    import xml.etree.ElementTree as ET

    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        root = ET.fromstring(zf.read("word/document.xml"))
    return " ".join(
        t.text or ""
        for t in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
    )


def test_chapin_artifacts_match_the_ladder():
    """Free hides the percent and fee dollars. Pro holds the desk. IC holds the counsel ZIP."""
    import json

    from email_service import build_research_result_html
    from report_email import build_forwardable_plaintext
    from research_store import redact_for_public_share
    from sample_dc_fixture import analysis_for_tier
    from share_html import render_share_html
    from sms_service import TwilioSMSService

    free_t = _pdf_text(generate_free_preview_pdf_bytes())
    est_t = _pdf_text(generate_partner_receipt_pdf_bytes())
    assert "Hidden on Free" in free_t
    assert "+21%" not in free_t
    assert "1,406" not in free_t
    assert "FAIL" not in free_t
    assert "Partner" not in free_t
    assert "ic_consultant" not in free_t
    assert "+21%" in est_t
    assert "ESTIMATOR" in est_t
    assert "1,406" not in est_t
    assert "946" not in est_t
    assert "FAIL" not in est_t
    assert "Partner" not in est_t

    pro_raw, _ = generate_pro_desk_zip_bytes()
    with zipfile.ZipFile(io.BytesIO(pro_raw)) as zf:
        packet = _pdf_text(zf.read("02_BID_PACKET_SAMPLE.pdf"))
        city = _pdf_text(zf.read("04_CITY_PACK_SAMPLE.pdf"))
        csv_text = zf.read("03_FEE_PUNCH_SCHEDULE_SAMPLE.csv").decode("utf-8")
    assert "946" not in packet
    assert "not guaranteed savings" not in packet
    assert "current rollup" not in packet
    assert "FAIL" not in packet
    assert "1,406" in city or "1406" in city
    assert "fortworthtexas.gov" in city.lower()
    assert "1,406.25" in csv_text or "1406.25" in csv_text
    assert "https://" in csv_text

    ic_raw, _ = generate_ic_bundle_sample_zip_bytes()
    with zipfile.ZipFile(io.BytesIO(ic_raw)) as zf:
        names = set(zf.namelist())
        counsel = _docx_text(zf.read("03_IC_DILIGENCE_COUNSEL.docx"))
        board = _pdf_text(zf.read("02_IC_DILIGENCE_BOARDROOM.pdf"))
    assert "03_IC_DILIGENCE_COUNSEL.docx" in names
    assert "04_FEE_PUNCH_EVIDENCE.xlsx" in names
    assert "Chapin" in counsel or "Fort Worth" in counsel
    assert "FAIL" not in board
    assert "946" not in board
    assert "ic_consultant" not in counsel

    from share_html import share_html_for_id

    free_share = share_html_for_id("rg-sample-chapin-free") or ""
    est_share = share_html_for_id("rg-sample-chapin-partner") or ""
    assert "Hidden on Free" in free_share
    assert "+21" not in free_share
    assert "1,406" not in free_share
    assert "FAIL" not in free_share
    assert "+21" in est_share
    assert "1,406" not in est_share

    sms = TwilioSMSService("test", "test", "+15555550100")
    for tier, rid in (
        ("free", "rg-sample-chapin-free"),
        ("partner", "rg-sample-chapin-partner"),
        ("pro", "rg-sample-chapin-pro"),
        ("ic", "rg-sample-chapin-ic"),
    ):
        data = analysis_for_tier(tier)
        data["research_id"] = rid
        data.setdefault("summary", {})
        data["summary"]["estimated_total_cost"] = 125000
        data.setdefault("honesty", {"permit_total_stated": False})
        red = redact_for_public_share(data)
        share = render_share_html(red, research_id=rid)
        forward = build_forwardable_plaintext(red)
        mailed = build_research_result_html(red)
        text_msg = sms._format_sms_message(red)
        assert "FAIL" not in share
        assert "FAIL" not in json.dumps(red)
        assert '"PASS"' not in json.dumps(red)
        assert "ic_consultant" not in share
        assert "Partner" not in share
        assert "125,000" not in text_msg
        assert "No permit total" in text_msg
        assert ".zip" not in share.lower()
        if tier == "free":
            assert "Hidden on Free" in share
            assert "+21" not in share
            assert "1,406" not in forward
            assert "289" not in forward
            assert "1,406" not in mailed
        elif tier == "partner":
            assert "+21" in share or "21" in share
            assert "1,406" not in share
            assert "1,406" not in forward
            assert "1,406" not in mailed
        else:
            assert "1,406" in forward or "1406" in forward


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
