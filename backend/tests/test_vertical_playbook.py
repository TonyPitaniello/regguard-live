"""Data-center vertical playbook + top-5 beachhead packs."""

from __future__ import annotations

from ahj_catalog import load_ahj_catalog, lookup_ahj
from arbitrage_enrichment import enrich_analysis_with_arbitrage
from city_packs import resolve_city_pack
from vertical_playbooks import apply_vertical_playbook, playbook_completeness, resolve_playbook


def test_resolve_playbook_data_center():
    assert resolve_playbook("data-center") is not None
    assert resolve_playbook("data_center") is not None
    assert resolve_playbook("commercial") is None


def test_beachhead_city_packs():
    for city, z in (
        ("Dallas", "75201"),
        ("Plano", "75074"),
        ("Austin", "78701"),
        ("Frisco", "75034"),
        ("Fort Worth", "76102"),
        ("Round Rock", "78664"),
    ):
        pack = resolve_city_pack(city, "TX", z)
        assert pack is not None, city
        assert pack.get("citeable") is True
        assert (pack.get("gotchas") or []), city


def test_ahj_catalog_includes_new_metros():
    load_ahj_catalog.cache_clear()
    ids = {r.get("ahj_id") for r in load_ahj_catalog()}
    assert "frisco_tx" in ids
    assert "fort_worth_tx" in ids
    assert "round_rock_tx" in ids
    assert lookup_ahj("Frisco", "TX", "75034") is not None
    assert lookup_ahj("", "TX", "76102") is not None


def test_playbook_fills_on_dallas_dc():
    analysis = {
        "project_info": {
            "address": "100 Main St",
            "city": "Dallas",
            "state": "TX",
            "zip": "75201",
            "type": "data-center",
        },
        "punch_list": {"punch_list": []},
        "summary": {},
    }
    out = enrich_analysis_with_arbitrage(analysis)
    assert out.get("vertical_playbook"), "playbook missing"
    stats = out["vertical_playbook"]["stats"]
    assert stats["total"] >= 8
    assert stats["cited"] >= 1
    completeness, cited, confirm = playbook_completeness(out)
    assert completeness > 0
    assert cited + confirm == stats["total"]
    # Punch should include playbook CRITICAL/HIGH lines
    tasks = [i.get("task") for i in (out.get("punch_list") or {}).get("punch_list") or []]
    assert any(tasks), "expected playbook punch injection"


def test_playbook_confirm_outside_beachhead():
    analysis = {
        "project_info": {
            "city": "Nowhere",
            "state": "OR",
            "zip": "97001",
            "type": "data-center",
        },
        "punch_list": {"punch_list": []},
    }
    out = apply_vertical_playbook(analysis)
    assert out.get("vertical_playbook")
    # Thin locality → more Confirm than Cited
    stats = out["vertical_playbook"]["stats"]
    assert stats["confirm"] >= stats["cited"]
