"""Tests for paid_local_confirm FinOps mode."""

from __future__ import annotations

import json
from pathlib import Path


def test_quota_consume_and_cap(tmp_path, monkeypatch):
    monkeypatch.setenv("REGGUARD_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PAID_LOCAL_CONFIRM_MAX_PER_DAY", "2")
    monkeypatch.setenv("PAID_LOCAL_CONFIRM", "1")

    from paid_local_confirm import consume_paid_local_lookup, get_paid_local_usage

    ok1, u1 = consume_paid_local_lookup("pro@example.com")
    ok2, u2 = consume_paid_local_lookup("pro@example.com")
    ok3, u3 = consume_paid_local_lookup("pro@example.com")
    assert ok1 and ok2
    assert not ok3
    assert u3.get("capped") is True
    assert u3.get("remaining") == 0
    usage = get_paid_local_usage("pro@example.com")
    assert usage["used"] == 2
    assert usage["allowed"] is False


def test_result_cache_roundtrip(monkeypatch):
    monkeypatch.setenv("PAID_LOCAL_CONFIRM_CACHE_TTL_SEC", "3600")
    from paid_local_confirm import _cache_get, _cache_key, _cache_set

    k = _cache_key("Seattle", "WA", "98109", "https://www.seattle.gov/sdci")
    _cache_set(k, {"fee_rows": [{"label": "Electrical", "amount_usd": 99}], "scraped_url": "https://x"})
    hit = _cache_get(k)
    assert hit and hit["fee_rows"][0]["amount_usd"] == 99


def test_run_paid_local_sets_finops_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("REGGUARD_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PAID_LOCAL_CONFIRM", "1")
    monkeypatch.setenv("PAID_LOCAL_CONFIRM_MAX_PER_DAY", "10")
    monkeypatch.setenv("FIRECRAWL_API_KEY", "")  # force cheap/no map path

    import paid_local_confirm as plc

    plc._RESULT_CACHE.clear()

    from paid_local_confirm import run_paid_local_confirm

    analysis = {
        "project_info": {
            "address": "400 Broad",
            "city": "Seattle",
            "state": "WA",
            "zip": "98109",
            "type": "commercial",
        },
        "punch_list": {"punch_list": []},
    }

    def fake_cheap(portal, pack_urls=None, use_llm=True):
        return {
            "status": "ok",
            "fees": [
                {
                    "label": "Building permit base",
                    "amount_usd": 120.0,
                    "verified": True,
                    "source_url": portal,
                    "source_label": "test",
                }
            ],
            "notes": ["Confirm online"],
            "markdown_chars": 500,
        }

    import cheap_page_confirm as cpc

    monkeypatch.setattr(cpc, "run_cheap_page_confirm", fake_cheap)

    def merge(a, c):
        a = dict(a)
        a["fee_card"] = {"fees": c.get("fees") or [], "paid_local_confirm": True}
        return a

    monkeypatch.setattr(cpc, "merge_cheap_confirm_into_analysis", merge)

    out = run_paid_local_confirm(
        analysis,
        city="Seattle",
        state="WA",
        zip_code="98109",
        email="pro-finops@example.com",
    )
    assert out.get("finops_mode") == "paid_local_confirm"
    assert out.get("paid_local", {}).get("status") == "ok"
    assert out["paid_local"].get("method") in ("cheap_page_confirm", "result_cache")
    assert out.get("coverage", {}).get("tier") in ("paid_local", "portal_seed", "full_pack")


def test_ahj_smart_confirm_delegates(monkeypatch, tmp_path):
    monkeypatch.setenv("REGGUARD_DATA_DIR", str(tmp_path))
    called = {}

    def fake_run(analysis, **kwargs):
        called["yes"] = True
        analysis = dict(analysis)
        analysis["finops_mode"] = "paid_local_confirm"
        return analysis

    monkeypatch.setattr("paid_local_confirm.run_paid_local_confirm", fake_run)
    from ahj_smart_confirm import run_paid_ahj_smart_confirm

    out = run_paid_ahj_smart_confirm({"punch_list": {"punch_list": []}}, city="X", state="TX")
    assert called.get("yes")
    assert out["finops_mode"] == "paid_local_confirm"
