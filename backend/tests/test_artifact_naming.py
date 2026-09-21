"""Artifact naming: address + doc type in ALL CAPS."""

from artifact_naming import (
    document_display_title,
    document_download_filename,
    site_line_from_analysis,
    title_and_filename,
)


def test_display_title_all_caps():
    title = document_display_title("123 Main St, Fort Worth, TX 76126", "Bid Risk Receipt")
    assert title == "123 MAIN ST, FORT WORTH, TX 76126 — BID RISK RECEIPT"


def test_filename_slug():
    name = document_download_filename("123 Main St, Fort Worth, TX", "IC Diligence Package", "docx")
    assert name.endswith(".docx")
    assert "123_MAIN_ST" in name
    assert "IC_DILIGENCE_PACKAGE" in name
    assert " " not in name


def test_site_line_from_analysis():
    site = site_line_from_analysis(
        {"project_info": {"address": "10 Chapin Rd", "city": "Fort Worth", "state": "TX", "zip": "76126"}}
    )
    assert "Chapin" in site
    assert "Fort Worth" in site
    _s, title, fn = title_and_filename(
        {"project_info": {"address": "10 Chapin Rd", "city": "Fort Worth", "state": "TX", "zip": "76126"}},
        "FULL CITY PACK",
        ext="pdf",
    )
    assert title.startswith("10 CHAPIN")
    assert title.endswith("FULL CITY PACK")
    assert fn.endswith(".pdf")
