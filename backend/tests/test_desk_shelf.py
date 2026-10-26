"""Desk fixes from the 26 Oct 2026 release premortem. Stripe is not in this file."""

from fee_shelf_watch import judge_text
from nurture_store import drip_desk_status, mark_sent, schedule_free_run_drip
from product_events import city_page_counts, track_event


def test_city_page_counts_ignore_other_events(tmp_path, monkeypatch):
    import product_events

    monkeypatch.setattr(product_events, "_PATH", tmp_path / "events.jsonl")
    monkeypatch.setattr(product_events, "_supabase_rows_for_event", lambda event, limit=1000: None)
    track_event("city_page_view", channel="Houston")
    track_event("pricing_view", channel="pricing")
    out = city_page_counts(hours=24)
    assert out["source"] == "local"
    assert out["total"] == 1
    assert out["by_city"] == {"houston": 1}
    assert "email" not in out


def test_city_page_view_rejects_unknown_slug(tmp_path, monkeypatch):
    import product_events

    monkeypatch.setattr(product_events, "_PATH", tmp_path / "events.jsonl")
    try:
        track_event("city_page_view", channel="georgetown")
        raise AssertionError("expected reject")
    except ValueError as e:
        assert "city" in str(e).lower()


def test_schedule_file_missing_a_phrase_is_moved():
    text = "Commercial building permit fee schedule. " * 40
    judged = judge_text(text + "80% of table. application 300.", ["80%", "300", "75"], schedule=True)
    assert judged["status"] == "moved"
    assert any("75" in m for m in judged["missing"])


def test_thin_page_stays_unread():
    judged = judge_text("loading", ["80%"], schedule=True)
    assert judged["status"] == "unread"


def test_portal_identity_is_not_a_dollar_check():
    text = "City of Plano Building Inspections. Confirm the permit path. " * 30
    judged = judge_text(text, ["building inspection"], schedule=False)
    assert judged["status"] == "portal"


def test_portal_without_the_dollar_stays_unread():
    text = "City of Plano Building Inspections. Confirm the permit path. " * 30
    judged = judge_text(text, ["$75"], schedule=False)
    assert judged["status"] == "unread"


def test_drip_status_has_no_email(tmp_path, monkeypatch):
    import nurture_store

    monkeypatch.setenv("REGGUARD_DATA_DIR", str(tmp_path))
    nurture_store._ITEMS = {}
    out = schedule_free_run_drip(
        email="est@example.com",
        research_id="r1",
        share_url="https://app.regguardagent.com/r/r1",
        city="Plano",
    )
    mark_sent(out["d2"]["id"])
    status = drip_desk_status()
    assert status["last_drip_sent_at"]
    assert status["pending_drip"] >= 1
    blob = str(status)
    assert "est@example.com" not in blob
    assert "@" not in blob
