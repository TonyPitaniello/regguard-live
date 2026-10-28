"""Forwardable artifact: persist research, full punch email, shareable /r/{id}."""

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from instant_analysis import build_instant_fallback_analysis  # noqa: E402
from report_email import build_forwardable_plaintext, build_forwardable_result_html  # noqa: E402
from research_store import (  # noqa: E402
    extract_sources,
    get_analysis,
    public_analysis,
    save_research,
    share_url_for,
)


@pytest.fixture
def sample_analysis():
    a = build_instant_fallback_analysis(
        "100 Main St, Plano, TX 75074",
        project_type="electrical",
        zip_code="75074",
        city="Plano",
        state="TX",
    )
    a["source_urls"] = [
        "https://www.plano.gov/permits",
        {"title": "Municode Plano", "url": "https://library.municode.com/tx/plano"},
    ]
    a["email"] = "secret@example.com"
    a["phone"] = "2145551212"
    return a


def test_persist_and_retrieve_roundtrip(sample_analysis, tmp_path, monkeypatch):
    monkeypatch.setenv("REG_GUARD_REPORT_DIR", str(tmp_path))
    meta = save_research(sample_analysis, research_id="ft-testpersist01")
    assert meta["research_id"] == "ft-testpersist01"
    assert "/r/ft-testpersist01" in meta["share_url"]
    loaded = get_analysis("ft-testpersist01")
    assert loaded is not None
    assert loaded["project_info"]["city"] == "Plano"
    assert "email" not in loaded  # PII stripped
    assert "phone" not in loaded
    assert loaded["share_url"] == share_url_for("ft-testpersist01")


def test_public_analysis_strips_pii(sample_analysis):
    clean = public_analysis(sample_analysis)
    assert "email" not in clean
    assert "phone" not in clean
    assert clean["project_info"]["address"]


def test_public_share_free_hides_paid_numbers():
    from research_store import redact_for_public_share

    raw = {
        "research_depth": "free",
        "receipt_mode": "free_preview",
        "email": "buyer@example.com",
        "contingency_band": {"pct_low": 12.5, "pct_mid": 14, "pct_high": 18},
        "fee_card": {"fees": [{"label": "Building permit", "amount_usd": 2400}]},
        "regguard_stamp": {"grade": "FAIL", "headline": "FAIL — high pre-bid risk"},
        "punch_list": {"punch_list": [{"task": f"line {i}"} for i in range(8)]},
    }
    out = redact_for_public_share(raw)
    assert out["share_tier"] == "free"
    assert out["contingency_band"]["pct_low"] is None
    assert out["contingency_band"]["share_frosted"] is True
    assert "amount_usd" not in out["fee_card"]["fees"][0]
    assert "FAIL" not in out["regguard_stamp"]["headline"]
    assert out["regguard_stamp"]["display_grade"] == "HOLD"
    assert len(out["punch_list"]["punch_list"]) == 5
    assert raw["contingency_band"]["pct_low"] == 12.5


def test_public_share_pro_keeps_fee_dollars():
    from research_store import redact_for_public_share

    raw = {
        "research_depth": "pro",
        "contingency_band": {"pct_low": 8, "pct_mid": 10, "pct_high": 12},
        "fee_card": {"fees": [{"label": "Building permit", "amount_usd": 500}]},
        "regguard_stamp": {"grade": "FAIL", "headline": "FAIL"},
    }
    out = redact_for_public_share(raw)
    assert out["share_tier"] == "pro"
    assert out["contingency_band"]["pct_low"] == 8
    assert out["fee_card"]["fees"][0]["amount_usd"] == 500
    assert "FAIL" not in out["regguard_stamp"]["headline"]


def test_forwardable_email_includes_punch_and_sources(sample_analysis, tmp_path, monkeypatch):
    monkeypatch.setenv("REG_GUARD_REPORT_DIR", str(tmp_path))
    meta = save_research(sample_analysis, research_id="ft-emailpunch01")
    analysis = get_analysis(meta["research_id"])
    html = build_forwardable_result_html(analysis)
    assert "Full punch list" in html
    assert "Sources" in html
    assert "plano.gov" in html.lower() or "municode" in html.lower()
    assert meta["share_url"] in html
    text = build_forwardable_plaintext(analysis)
    assert "PUNCH LIST:" in text
    assert "Shareable report:" in text


def test_extract_sources(sample_analysis):
    sources = extract_sources(sample_analysis)
    assert len(sources) >= 2
    urls = " ".join(s.get("url") or s.get("label") or "" for s in sources)
    assert "plano.gov" in urls or "municode" in urls


def test_missing_report_returns_none(tmp_path, monkeypatch):
    monkeypatch.setenv("REG_GUARD_REPORT_DIR", str(tmp_path))
    assert get_analysis("does-not-exist-xyz") is None


def test_report_survives_disk_wipe(sample_analysis, tmp_path, monkeypatch):
    store = {}

    def fake_rest(path, method="GET", json_body=None, prefer=""):
        if method == "POST" and isinstance(json_body, dict):
            store["row"] = json_body
            return []
        if method == "GET" and "share_" in path and store.get("row"):
            return [{"analysis_json": store["row"]["analysis_json"]}]
        return None

    monkeypatch.setattr("order_service._supabase_rest", fake_rest)
    monkeypatch.setenv("REG_GUARD_REPORT_DIR", str(tmp_path))
    save_research(sample_analysis, research_id="ft-durable01")
    assert str(store["row"]["stripe_session_id"]).startswith("share_")
    assert store["row"]["amount"] == 0
    assert store["row"]["tier"] == "contractor_pro"
    assert store["row"]["email"] == "share-archive@regguard.invalid"
    for path in tmp_path.glob("*.json"):
        path.unlink()
    from research_store import _MEMORY

    _MEMORY.pop("ft-durable01", None)
    loaded = get_analysis("ft-durable01")
    assert loaded is not None
    assert loaded["project_info"]["city"] == "Plano"


def test_share_archive_is_not_listed_as_a_purchase(monkeypatch):
    from order_service import list_orders_for_email

    def fake_rest(path, method="GET", json_body=None, prefer=""):
        if "email=eq." in path:
            return [
                {
                    "id": "ord-real",
                    "stripe_session_id": "cs_test_real",
                    "tier": "partner",
                    "status": "completed",
                    "amount": 7900,
                    "email": "buyer@example.com",
                    "created_at": "2026-10-28T00:00:00Z",
                },
                {
                    "id": "ord-share",
                    "stripe_session_id": "share_abc",
                    "tier": "partner",
                    "status": "completed",
                    "amount": 0,
                    "email": "buyer@example.com",
                    "created_at": "2026-10-28T00:00:00Z",
                    "analysis_json": {"id": "abc", "analysis": {}},
                },
            ]
        return None

    monkeypatch.setattr("order_service._supabase_rest", fake_rest)
    monkeypatch.setattr("order_service._ORDERS_BY_EMAIL", {})
    monkeypatch.setattr("order_service._ORDERS_BY_SESSION", {})
    rows = list_orders_for_email("buyer@example.com")
    sessions = [str(r.get("stripe_session_id") or "") for r in rows]
    assert "cs_test_real" in sessions
    assert "share_abc" not in sessions


def test_resolve_prefers_full_analysis(tmp_path, monkeypatch):
    monkeypatch.setenv("REG_GUARD_REPORT_DIR", str(tmp_path))
    # Import after env so store dir is respected on first write inside resolve
    from main import ResearchDeliverySummary, _resolve_research_data

    analysis = build_instant_fallback_analysis("9 Oak, Austin, TX 78704", city="Austin", state="TX")
    data = _resolve_research_data("ft-resolve01", None, analysis)
    assert data["research_id"] == "ft-resolve01"
    assert "/r/ft-resolve01" in data["share_url"]
    assert len((data.get("punch_list") or {}).get("punch_list") or []) >= 1

    # Summary-only still works
    summary = ResearchDeliverySummary(
        city="Austin",
        state="TX",
        zip="78704",
        preview=True,
        estimates_unverified=True,
        risk_unavailable=True,
        cost=100,
        timeline="30 days",
    )
    thin = _resolve_research_data("ft-thin01", summary, None)
    assert thin["summary"]["estimated_total_cost"] == 100
