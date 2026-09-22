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
        # Exact Pricing contract — no README, boardroom required
        assert names == {
            "01_DECISION_MEMO.pdf",
            "02_IC_DILIGENCE_BOARDROOM.pdf",
            "03_IC_DILIGENCE_COUNSEL.docx",
            "04_FEE_PUNCH_SCHEDULE.csv",
            "05_EVIDENCE_INDEX.csv",
        }
        memo = zf.read("01_DECISION_MEMO.pdf")
        assert memo[:4] == b"%PDF"
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
        csv_text = zf.read("04_FEE_PUNCH_SCHEDULE.csv").decode("utf-8")
        assert "exhibit_id" in csv_text
        assert "source_url" in csv_text
        idx = zf.read("05_EVIDENCE_INDEX.csv").decode("utf-8")
        assert "EX-" in idx or "exhibit" in idx.lower()
        assert "whitehouse.gov" not in csv_text.lower()
        assert "whitehouse.gov" not in idx.lower()
