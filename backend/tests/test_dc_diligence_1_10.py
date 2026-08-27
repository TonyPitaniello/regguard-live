"""Smoke tests for DC must-haves 1–10 (diligence stamp, radar, war room, export)."""

from dc_diligence import (
    diligence_export_payload,
    load_moratorium_radar,
    radar_for_state,
    stamp_dc_diligence,
)
from war_room_store import add_comment, list_comments
from zip_watch import pack_fingerprint


def _dc_analysis():
    return {
        "project_info": {
            "type": "data_center",
            "address": "1 Server Farm Rd",
            "city": "Ashburn",
            "state": "VA",
            "zip": "20147",
            "notes": "150 MW hyperscale campus",
        },
        "ahj_card": {"name": "Loudoun County", "portal_url": "https://example.gov"},
        "community_friction": {
            "headline": "Elevated hearing risk",
            "band": "Elevated",
            "score": 7,
            "score_max": 12,
            "signals": [
                {
                    "id": "hearing",
                    "label": "Public hearing pattern",
                    "level": 3,
                    "detail": "Recent large-load hearings nearby",
                }
            ],
            "disclaimer": "Heuristic only",
        },
    }


def test_stamp_attaches_all_cards():
    out = stamp_dc_diligence(_dc_analysis())
    assert out.get("parallel_clocks", {}).get("clocks")
    assert out.get("moratorium_radar", {}).get("high_alert_state") is True
    assert out.get("power_path_card", {}).get("mw_hint") == 150.0
    assert out.get("water_cooling_card")
    assert out.get("opposition_card")
    assert out.get("fast41_card", {}).get("fast41_candidate") is True
    assert out.get("dc_diligence_version")


def test_moratorium_radar_seeded():
    data = load_moratorium_radar()
    assert len(data.get("metros") or []) >= 5
    va = radar_for_state("VA")
    assert any("Virginia" in str(m.get("metro") or "") for m in va)


def test_diligence_export_schema():
    payload = diligence_export_payload(_dc_analysis())
    assert payload["schema"] == "regguard.dc_diligence.v1"
    assert payload["power_path"]["mw_hint"] == 150.0
    assert payload["site"]["state"] == "VA"


def test_war_room_roundtrip():
    from war_room_store import ensure_write_token

    rid = "rg-test-war-room-1"
    token = ensure_write_token(rid)
    c = add_comment(
        rid, author="Alex", role="ic", text="Confirm utility study product", write_token=token
    )
    assert c["id"].startswith("wr-")
    listed = list_comments(rid)
    assert any(x["id"] == c["id"] for x in listed)


def test_zip_fingerprint_includes_dc_bits():
    fp, meta = pack_fingerprint("Ashburn", "VA", "20147")
    assert isinstance(fp, str) and len(fp) >= 10
    assert "dc_metro_count" in meta
