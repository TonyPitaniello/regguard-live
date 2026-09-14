"""Demand scoreboard + weekly pain-scout digest."""

from __future__ import annotations

from pain_scout_digest import build_weekly_digest, latest_digest, list_digests
from product_events import demand_scoreboard, track_event


def test_demand_scoreboard_verdicts(tmp_path, monkeypatch):
    import product_events

    monkeypatch.setattr(product_events, "_PATH", tmp_path / "events.jsonl")

    empty = demand_scoreboard(hours=24)
    assert empty["verdict"] == "NO_SIGNAL"
    assert empty["funnel"]["research_runs"] == 0

    for i in range(10):
        track_event("research_run", research_id=f"r{i}", zip_code="75074")
        track_event("stamp_receipt_download", research_id=f"r{i}", zip_code="75074")
    for i in range(3):
        track_event("stamp_share_copy", research_id=f"r{i}", zip_code="75074")
        track_event("shared_report_open", research_id=f"r{i}", zip_code="75074")
    track_event("checkout_complete", research_id="r0", zip_code="75074", channel="pro")
    track_event(
        "demand_feedback",
        research_id="r0",
        zip_code="75074",
        meta={"answer": "would_forward"},
    )

    board = demand_scoreboard(hours=24)
    assert board["funnel"]["research_runs"] == 10
    assert board["funnel"]["receipt_downloads"] == 10
    assert board["funnel"]["shares"] >= 3
    assert board["funnel"]["shared_report_opens"] == 3
    assert board["funnel"]["checkout_completes"] == 1
    assert board["demand_feedback"].get("would_forward") == 1
    assert board["verdict"] in ("EARLY_DEMAND", "VIRAL_WEAK_PAY", "HYPOTHESIS_ONLY")
    assert board["top_zips"] and board["top_zips"][0]["zip"] == "75074"


def test_useful_not_forwardable(tmp_path, monkeypatch):
    import product_events

    monkeypatch.setattr(product_events, "_PATH", tmp_path / "events.jsonl")
    for i in range(20):
        track_event("research_run", research_id=f"u{i}", zip_code="75201")
        track_event("stamp_receipt_download", research_id=f"u{i}", zip_code="75201")
    board = demand_scoreboard(hours=24)
    assert board["verdict"] == "USEFUL_NOT_FORWARDABLE"


def test_pain_scout_digest_persists(tmp_path, monkeypatch):
    import pain_scout_digest
    import product_events

    monkeypatch.setattr(product_events, "_PATH", tmp_path / "events.jsonl")
    monkeypatch.setattr(pain_scout_digest, "_PATH", tmp_path / "digests.jsonl")

    track_event("research_run", research_id="p1", zip_code="78701")
    digest = build_weekly_digest(hours=24, persist=True)
    assert digest["generated_at"]
    assert digest["verdict"]
    assert isinstance(digest["recommended_actions"], list)
    assert digest["market_pain_themes"]
    assert latest_digest() is not None
    assert len(list_digests(5)) >= 1
