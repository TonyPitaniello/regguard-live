"""IC Diligence Bundle — evidence binder + ZIP for $1,500 deliverable."""

import zipfile

import pytest

from ic_diligence_bundle import build_ic_diligence_bundle_zip
from ic_package_composer import PACKAGE_SCHEMA, compose_ic_package
from tests.test_ic_package_composer import RICH


def test_evidence_binder_maps_claims_to_exhibits():
    pkg = compose_ic_package(RICH, generated_for="buyer@example.com")
    assert pkg["schema"] == PACKAGE_SCHEMA
    binder = pkg["evidence_binder"]
    assert binder["summary"]["exhibit_count"] >= 1
    assert any(c.get("claim_type") == "hold_driver" for c in binder["claims"])
    exhibited = [c for c in binder["claims"] if c.get("exhibit_id")]
    assert exhibited
    assert exhibited[0]["exhibit_id"].startswith("EX-")
    # Decision memo present with stamp + contingency
    memo = pkg["decision_memo"]
    assert memo["stamp"]["display"] == "HOLD"
    assert memo["contingency"]["pct_low"] == 21.5
    assert len(memo["top_drivers"]) >= 1


def test_dc_parallel_clocks_include_water_track():
    data = dict(RICH)
    data["project_info"] = {**RICH["project_info"], "type": "data-center"}
    data["project_type"] = "data-center"
    data["dc_positioning"] = {"headline": "Large-load / ERCOT path"}
    data["parallel_clocks"] = {"clocks": []}
    pkg = compose_ic_package(data, generated_for="buyer@example.com")
    track = pkg["parallel_clocks_track"]
    assert track["enabled"] is True
    names = " ".join(c.get("name", "") + " " + c.get("track", "") for c in track["clocks"]).lower()
    assert "ahj" in names or "permit" in names
    assert "interconnect" in names or "utility" in names or "ercot" in names
    assert "water" in names or "npdes" in names


def test_ic_diligence_bundle_zip_contents():
    pytest.importorskip("docx")
    pytest.importorskip("openpyxl")
    raw, filename = build_ic_diligence_bundle_zip(
        RICH,
        generated_for="buyer@example.com",
        share_url="https://app.regguardagent.com/r/rg-test",
    )
    assert filename.endswith(".zip")
    assert "IC_DILIGENCE" in filename.upper()
    assert raw[:2] == b"PK"
    with zipfile.ZipFile(__import__("io").BytesIO(raw)) as zf:
        names = set(zf.namelist())
        # Exact Pricing contract — Excel primary; CSVs optional; no README
        assert names == {
            "01_DECISION_MEMO.pdf",
            "02_IC_DILIGENCE_BOARDROOM.pdf",
            "03_IC_DILIGENCE_COUNSEL.docx",
            "04_FEE_PUNCH_EVIDENCE.xlsx",
            "05_EVIDENCE_INDEX.xlsx",
            "optional/FEE_PUNCH_SCHEDULE.csv",
            "optional/EVIDENCE_INDEX.csv",
        }
        memo = zf.read("01_DECISION_MEMO.pdf")
        assert memo[:4] == b"%PDF"
        # Hard 1-page stamp — no continuation page
        assert memo.count(b"/Type /Page") == 1 or b"/Count 1" in memo
        boardroom = zf.read("02_IC_DILIGENCE_BOARDROOM.pdf")
        assert boardroom[:4] == b"%PDF"
        assert len(boardroom) > 10_000
        docx = zf.read("03_IC_DILIGENCE_COUNSEL.docx")
        assert docx[:2] == b"PK"
        # Parallel clocks section required in counsel DOCX
        import zipfile as zfmod

        with zfmod.ZipFile(__import__("io").BytesIO(docx)) as dz:
            xml = dz.read("word/document.xml").decode("utf-8", errors="replace")
        assert "Parallel clocks" in xml or "parallel clocks" in xml.lower()

        xlsx = zf.read("04_FEE_PUNCH_EVIDENCE.xlsx")
        assert xlsx[:2] == b"PK"
        from openpyxl import load_workbook

        wb = load_workbook(__import__("io").BytesIO(xlsx))
        assert "Cover" in wb.sheetnames
        assert set(wb.sheetnames) >= {"Cover", "Fees", "Punch", "Evidence"}
        assert wb["Fees"]["A5"].value == "Trade"

        ev_xlsx = zf.read("05_EVIDENCE_INDEX.xlsx")
        assert ev_xlsx[:2] == b"PK"
        ev_wb = load_workbook(__import__("io").BytesIO(ev_xlsx))
        assert set(ev_wb.sheetnames) >= {"Cover", "Exhibits", "Claims", "Index"}

        csv_text = zf.read("optional/FEE_PUNCH_SCHEDULE.csv").decode("utf-8")
        assert "exhibit_id" in csv_text
        assert "source_url" in csv_text
        idx = zf.read("optional/EVIDENCE_INDEX.csv").decode("utf-8")
        assert "EX-" in idx or "exhibit" in idx.lower()
        assert "whitehouse.gov" not in csv_text.lower()
        assert "whitehouse.gov" not in idx.lower()


def test_bid_risk_receipt_is_one_page_no_orphan_cut():
    """Dense Chapin-style payload must stay on one page and never end with '?'."""
    from bid_risk_receipt_pdf import generate_bid_risk_receipt_pdf_bytes
    from pypdf import PdfReader
    import io

    payload = dict(RICH)
    payload["project_info"] = {
        **(RICH.get("project_info") or {}),
        "address": "9999 Chapin School Road",
        "city": "Fort Worth",
        "state": "TX",
        "zip": "76126",
        "type": "data-center",
    }
    payload["dc_positioning"] = {"headline": "Large-load / ERCOT path"}
    payload["parallel_clocks"] = {
        "clocks": [
            {"name": "AHJ permits", "detail": "Confirm portal + hearings before bid"},
            {"name": "Utility interconnect", "detail": "TDSP parallel — not run by RegGuard"},
            {"name": "Water / NPDES", "detail": "Independent track"},
        ]
    }
    raw = generate_bid_risk_receipt_pdf_bytes(
        payload,
        generated_for="buyer@example.com",
        share_url="https://app.regguardagent.com/r/rg-test",
    )
    reader = PdfReader(io.BytesIO(raw))
    assert len(reader.pages) == 1
    text = "\n".join((p.extract_text() or "") for p in reader.pages)
    assert "the?" not in text
    assert "BID RISK RECEIPT - continued" not in text
    assert "- :" not in text
    assert "AHJ permits" in text or "PARALLEL CLOCKS" in text
    assert "STALE STAMP" in text  # RICH valid_until is in the past
    assert "REGGUARD STAMP" in text or "HOLD" in text or "CLEAR" in text
    # Top flags filled from killers + stamp drivers + gotchas
    assert "Large-load" in text or "High contingency" in text or "Grounding" in text

