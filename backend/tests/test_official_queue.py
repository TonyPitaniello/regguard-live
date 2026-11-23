"""Queue lookup prints a GIS row only when the official workbook states the INR."""

from io import BytesIO

import interconnect.official_queue as official_queue
from interconnect.official_queue import (
    QueueFileError,
    cited_queue_lookup,
    parse_gis_workbook,
)


def _workbook() -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Project Details - Large Gen"
    ws["A1"] = "GIS Report October 2026"
    headers = ["INR", "Project Name", "County", "GIM Study Phase", "Capacity (MW)", "Projected COD"]
    for col, header in enumerate(headers, start=1):
        ws.cell(6, col, header)
    ws.cell(7, 1, "24INR0031")
    ws.cell(7, 2, "North Solar")
    ws.cell(7, 3, "Dallas")
    ws.cell(7, 4, "SS Completed")
    ws.cell(7, 5, 150)
    ws.cell(7, 6, None)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _loaded():
    rows, printed = parse_gis_workbook(_workbook())
    return {
        "rows": rows,
        "report_date": printed,
        "report_name": "GIS_Report_October2026",
        "fresh": True,
    }


def test_parser_reads_the_stated_row_and_the_printed_date():
    rows, printed = parse_gis_workbook(_workbook())
    assert printed == "October 2026"
    assert rows["24INR0031"]["Project Name"] == "North Solar"
    assert rows["24INR0031"]["Capacity (MW)"] == 150
    assert "queue_position" not in rows["24INR0031"]


def test_ercot_row_cites_the_file_and_prints_no_rank(monkeypatch):
    monkeypatch.setattr(official_queue, "_load_ercot_rows", _loaded)
    row = cited_queue_lookup("ERCOT", "24inr0031")
    assert row["queue_position"] is None
    assert row["project_name"] == "North Solar"
    assert row["phase"] == "SS Completed"
    assert row["source_url"].startswith("https://www.ercot.com/")
    assert "Capacity (MW) stated on the file: 150." in row["note"]
    assert "Report date printed in the file: October 2026." in row["note"]
    assert "does not state an ordinal queue position" in row["note"]
    assert "42" not in row["note"]


def test_missing_id_is_a_miss_only_after_the_file_is_read(monkeypatch):
    monkeypatch.setattr(official_queue, "_load_ercot_rows", _loaded)
    row = cited_queue_lookup("ERCOT", "00INR0000")
    assert row["queue_position"] is None
    assert row["project_name"] is None
    assert "did not return a row" in row["note"]
    assert "October 2026" in row["note"]
    assert "42" not in row["note"]


def test_unread_file_does_not_pretend_the_id_was_absent(monkeypatch):
    def _boom():
        raise QueueFileError("official file denied the download")

    monkeypatch.setattr(official_queue, "_load_ercot_rows", _boom)
    row = cited_queue_lookup("ERCOT", "24INR0031")
    assert row["queue_position"] is None
    assert "could not be read" in row["note"]
    assert "did not return a row" not in row["note"]
    assert row["source_url"].startswith("https://www.ercot.com/")


def test_unknown_rto_prints_no_position():
    row = cited_queue_lookup("NOT-AN-RTO", "1")
    assert row["queue_position"] is None
    assert row["source_url"] == ""
