"""Tests for order-attached local packs, promote, and demand ranking."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture()
def pack_root(tmp_path, monkeypatch):
    monkeypatch.setenv("REGGUARD_DATA_DIR", str(tmp_path))
    # Clear LRU after env change
    try:
        from ahj_catalog import load_ahj_catalog

        load_ahj_catalog.cache_clear()
    except Exception:
        pass
    yield tmp_path
    try:
        from ahj_catalog import load_ahj_catalog

        load_ahj_catalog.cache_clear()
    except Exception:
        pass


def _sample_analysis(**kwargs):
    base = {
        "project_info": {
            "address": "7351 Meeting St",
            "city": "Bradenton",
            "state": "FL",
            "zip": "34201",
            "type": "data_center",
        },
        "ahj_card": {
            "name": "Bradenton Building",
            "portal_url": "https://example.com/bradenton-building",
            "fees_url": "https://example.com/bradenton-building/fees",
            "notes": "Confirm fees",
        },
        "fee_card": {
            "timeline": "11-15 weeks",
            "fees": [
                {
                    "label": "Electrical permit",
                    "amount_usd": 125,
                    "detail": "From page scrape",
                    "source_url": "https://example.com/bradenton-building/fees",
                }
            ],
        },
        "gotcha_watchlist": {
            "items": [
                {
                    "id": "nec_cycle",
                    "title": "Confirm NEC edition",
                    "detail": "Verify adopted NEC with AHJ",
                    "priority": "HIGH",
                    "source_url": "https://example.com/bradenton-building",
                }
            ]
        },
        "document_checklist": {"items": [{"task": "Single-line diagram"}]},
        "paid_local": {"status": "ok", "portal_url": "https://example.com/bradenton-building"},
        "coverage": {"tier": "paid_local"},
    }
    base.update(kwargs)
    return base


def test_attach_persists_zip_pack(pack_root):
    from local_pack_store import attach_local_pack_from_analysis, load_zip_pack

    analysis = attach_local_pack_from_analysis(
        _sample_analysis(),
        city="Bradenton",
        state="FL",
        zip_code="34201",
        persist=True,
        record_hit=True,
    )
    lp = analysis["local_pack"]
    assert lp["tier"] == "paid_local"
    assert lp["citeable"] is False
    assert (lp.get("ahj") or {}).get("portal_url")
    cached = load_zip_pack("34201")
    assert cached is not None
    assert cached["tier"] == "paid_local"
    hits = (pack_root / "local_pack_hits.jsonl").read_text(encoding="utf-8")
    assert "34201" in hits


def test_promote_creates_citeable_library(pack_root):
    from local_pack_store import (
        attach_local_pack_from_analysis,
        load_promoted_record,
        promote_zip_pack,
    )
    from ahj_catalog import lookup_ahj, load_ahj_catalog

    attach_local_pack_from_analysis(
        _sample_analysis(),
        city="Bradenton",
        state="FL",
        zip_code="34201",
        persist=True,
        record_hit=True,
    )
    out = promote_zip_pack(
        "34201",
        reviewer="tony",
        edits={"city": "Bradenton", "state": "FL", "ahj_id": "bradenton_fl"},
    )
    assert out["status"] == "ok"
    assert out["record"]["citeable"] is True
    assert out["record"]["ahj_id"] == "bradenton_fl"
    load_ahj_catalog.cache_clear()
    rec = load_promoted_record(zip_code="34201")
    assert rec is not None
    hit = lookup_ahj("Bradenton", "FL", "34201")
    assert hit is not None
    assert hit.get("ahj_id") == "bradenton_fl"


def test_promote_never_without_portal(pack_root):
    from local_pack_store import save_zip_pack, promote_zip_pack

    save_zip_pack(
        "99999",
        {
            "tier": "order_draft",
            "city": "Nowhere",
            "state": "FL",
            "zip": "99999",
            "ahj": {"name": "X", "portal_url": ""},
            "fees": [],
            "gotchas": [],
        },
    )
    with pytest.raises(ValueError):
        promote_zip_pack("99999", reviewer="ops")


def test_demand_ranking(pack_root):
    from local_pack_store import (
        attach_local_pack_from_analysis,
        log_pack_hit,
        rank_zips_by_demand,
    )

    attach_local_pack_from_analysis(
        _sample_analysis(),
        city="Bradenton",
        state="FL",
        zip_code="34201",
        persist=True,
        record_hit=True,
    )
    for _ in range(5):
        log_pack_hit("34201", "Bradenton", "FL", tier="paid_local")
    log_pack_hit("75075", "Plano", "TX", tier="full_pack")  # should be skipped if promoted/full
    ranked = rank_zips_by_demand(limit=10)
    assert ranked
    assert ranked[0]["zip"] == "34201"
    assert ranked[0]["hits"] >= 5


def test_delivery_includes_local_pack(pack_root):
    from delivery_parity import prepare_analysis_for_delivery
    from local_pack_store import attach_local_pack_from_analysis

    analysis = attach_local_pack_from_analysis(
        _sample_analysis(),
        persist=True,
        record_hit=False,
    )
    out = prepare_analysis_for_delivery(analysis)
    assert out.get("local_pack")
    assert (out.get("ahj_card") or {}).get("portal_url")
