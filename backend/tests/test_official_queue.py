"""Queue lookup must not invent an ordinal position."""

from interconnect.official_queue import cited_queue_lookup


def test_ercot_lookup_prints_no_position():
    row = cited_queue_lookup("ERCOT", "24INR0041")
    assert row["queue_position"] is None
    assert row["source_url"].startswith("https://www.ercot.com/")
    assert "42" not in row["note"]
    assert "position" in row["note"].lower()


def test_unknown_rto_prints_no_position():
    row = cited_queue_lookup("NOT-AN-RTO", "1")
    assert row["queue_position"] is None
    assert row["source_url"] == ""
