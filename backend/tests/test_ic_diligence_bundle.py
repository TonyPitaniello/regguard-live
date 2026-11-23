"""IC Diligence Bundle — evidence binder + ZIP for $1,500 deliverable."""

import zipfile

import pytest

from ic_diligence_bundle import build_ic_diligence_bundle_zip
from ic_package_composer import PACKAGE_SCHEMA, compose_ic_package
from tests.test_ic_package_composer import RICH


def test_bare_beachhead_site_fills_the_diligence_brief():
    """A city and address, with no scout payload, still opens the sourced city pack."""
    from ic_package_composer import compose_ic_package

    pkg = compose_ic_package(
        {
            "project_info": {
                "address": "6565 Headquarters Dr",
                "city": "Plano",
                "state": "TX",
                "zip": "75024",
                "type": "commercial data-center-adjacent",
            },
            "project_type": "commercial data-center-adjacent",
            "research_depth": "ic",
        }
    )
    memo = pkg["decision_memo"]
    assert memo["stamp"]["display"] == "HOLD"
    band = memo["contingency"] or {}
    if band:
        assert "not a quote" in (band.get("plain") or band.get("disclaimer") or "").lower() or "planning" in str(band).lower()
    fees = pkg["site_findings"]["fees"]
    assert any("reinspection" in (f.get("name") or "").lower() for f in fees)
    assert any(f.get("amount") == "$75" for f in fees)
    assert any((f.get("amount") or "").lower() == "confirm on schedule" for f in fees)
    assert "250.50" not in " ".join(g.get("title") or "" for g in pkg["site_findings"]["gotcha_cards"])
    assert pkg["site_findings"]["inspection_sequence"] or pkg["site_findings"]["document_checklist"]
    clock_blob = " ".join(
        (c.get("name") or "") + " " + (c.get("detail") or "")
        for c in pkg.get("parallel_clocks_track", {}).get("clocks") or []
    ).lower()
    clocks = clock_blob
    assert "interconnect" in clocks or "ercot" in clocks or "utility" in clocks
    raw, _name = build_ic_diligence_bundle_zip(
        {
            "project_info": {
                "address": "6565 Headquarters Dr",
                "city": "Plano",
                "state": "TX",
                "zip": "75024",
                "type": "commercial data-center-adjacent",
            },
            "project_type": "commercial data-center-adjacent",
            "research_depth": "ic",
        },
        generated_for="desktop review",
    )
    import io
    from pypdf import PdfReader

    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        memo_pdf = zf.read("01_DECISION_MEMO.pdf")
    reader = PdfReader(io.BytesIO(memo_pdf))
    assert len(reader.pages) == 1
    memo_text = reader.pages[0].extract_text() or ""
    assert "REGGUARD STAMP: HOLD" in memo_text
    assert "STAMP: CLEAR" not in memo_text
    assert "FAIL" not in memo_text
    if band.get("pct_low") is not None:
        assert str(band["pct_low"]).rstrip("0").rstrip(".") in memo_text.replace(" ", "")


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
    assert memo["contingency"] is None
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


def test_confirm_on_schedule_note_prints_no_dollar():
    from ic_buyer_brief import _fee

    row = _fee(
        label="Permit total",
        trade="building",
        amount=None,
        note="Do not publish a single total of $75. Name the building first.",
        url="https://example.com/schedule.pdf",
        source_label="schedule page 1",
        status="confirm-on-schedule",
        owner="City desk",
    )
    assert "$" not in row["note"]
    assert "confirm-on-schedule" in row["note"]
    assert row["amount_usd"] is None


def test_beachhead_memo_is_the_page_they_forward():
    """Page one carries every fee line and the three desks, and it still fits."""
    import io

    from pypdf import PdfReader

    from bid_risk_receipt_pdf import generate_bid_risk_receipt_pdf
    from ic_pdf_enrichment import enrich_analysis_for_ic_pdfs

    sites = [
        ("1950 N Stemmons Fwy", "Dallas", "75207"),
        ("6565 Headquarters Dr", "Plano", "75024"),
        ("9020 Metric Blvd", "Austin", "78758"),
        ("13600 Heritage Pkwy", "Fort Worth", "76177"),
    ]
    for addr, city, zip_code in sites:
        data = enrich_analysis_for_ic_pdfs(
            {
                "project_info": {
                    "address": addr,
                    "city": city,
                    "state": "TX",
                    "zip": zip_code,
                    "type": "commercial",
                },
                "project_type": "commercial",
                "research_depth": "ic",
            }
        )
        path = generate_bid_risk_receipt_pdf(data, f"/tmp/rg-memo-{city.replace(' ', '')}.pdf")
        reader = PdfReader(path)
        assert len(reader.pages) == 1, city
        text = reader.pages[0].extract_text() or ""
        assert "REGGUARD STAMP: HOLD" in text
        assert "http" in text
        assert "marked done" not in text.lower()
        assert "stripe" not in text.lower()
        fees = (data.get("fee_card") or {}).get("fees") or []
        assert any(isinstance(f.get("amount_usd"), (int, float)) for f in fees), city
        assert any(f.get("amount_usd") is None for f in fees), city
        for fee in fees:
            label = str(fee.get("label") or "")
            assert label in text, (city, label)
            if fee.get("amount_usd") is None:
                assert "$" not in str(fee.get("note") or "")
                assert f"{label} — confirm-on-schedule" in text or "confirm-on-schedule" in text
        for clock in ((data.get("parallel_clocks") or {}).get("clocks") or [])[:3]:
            owner = str(clock.get("owner") or "")
            assert owner and owner in text, (city, owner)


def test_counsel_packet_is_forwardable_as_generated():
    """Counsel sees the full https URL and the driver through the last word."""
    import io
    import re
    import zipfile

    from lxml import etree
    from openpyxl import load_workbook
    from pypdf import PdfReader

    sites = [
        ("1950 N Stemmons Fwy", "Dallas", "75207", "Desk: DallasNow call center 214.948.4480."),
        ("6565 Headquarters Dr", "Plano", "75024", "Desk: Plano Building Inspections."),
        ("9020 Metric Blvd", "Austin", "78758", "Desk: Austin Development Services commercial plan review."),
        ("13600 Heritage Pkwy", "Fort Worth", "76177", "Desk: Fort Worth Development Services commercial permitting."),
    ]
    spaced = re.compile(r"(?:com|gov|net|org) / ")
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    for addr, city, zip_code, driver_end in sites:
        raw, _name = build_ic_diligence_bundle_zip(
            {
                "project_info": {
                    "address": addr,
                    "city": city,
                    "state": "TX",
                    "zip": zip_code,
                    "type": "commercial",
                },
                "project_type": "commercial",
                "research_depth": "ic",
            },
            generated_for="owner's rep",
        )
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            board = "\n".join(
                (p.extract_text() or "")
                for p in PdfReader(io.BytesIO(zf.read("02_IC_DILIGENCE_BOARDROOM.pdf"))).pages
            )
            assert "Still confirm dollar amounts" not in board, city
            assert not spaced.search(board), city
            flat = board.replace("\n", "")
            assert driver_end.replace(" ", "")[:40] in flat.replace(" ", "") or driver_end in board, (
                city,
                driver_end,
            )
            docx = zf.read("03_IC_DILIGENCE_COUNSEL.docx")
            root = etree.fromstring(zipfile.ZipFile(io.BytesIO(docx)).read("word/document.xml"))
            rels = etree.fromstring(
                zipfile.ZipFile(io.BytesIO(docx)).read("word/_rels/document.xml.rels")
            )
            targets = {rel.get("Id"): rel.get("Target") for rel in rels}
            for link in root.xpath(".//w:hyperlink", namespaces=ns):
                rid = link.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
                shown = "".join(t.text or "" for t in link.xpath(".//w:t", namespaces=ns))
                target = targets.get(rid) or ""
                assert shown == target, (city, shown, target)
                assert target.startswith("https://"), (city, target)
                assert " " not in target, (city, target)
            for name in ("04_FEE_PUNCH_EVIDENCE.xlsx", "05_EVIDENCE_INDEX.xlsx"):
                wb = load_workbook(io.BytesIO(zf.read(name)), data_only=True)
                blob = " ".join(
                    str(cell)
                    for ws in wb.worksheets
                    for row in ws.iter_rows(max_row=8, max_col=2, values_only=True)
                    for cell in row
                    if cell
                )
                assert "Confirm fees with the AHJ" not in blob, (city, name)


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
    assert "Large-load" in text or "High contingency" in text or "Grounding" in text

