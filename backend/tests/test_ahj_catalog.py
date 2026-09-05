"""AHJ catalog unit tests — lookup, fee lines, enrich, Lake Dallas fence."""

import json
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from ahj_catalog import (  # noqa: E402
    digest_ahj_block,
    enrich_analysis_with_ahj,
    load_ahj_catalog,
    lookup_ahj,
    scout_extras_for,
)
from research_memo import build_research_digest  # noqa: E402


def test_catalog_loads_beachhead_ahjs():
    load_ahj_catalog.cache_clear()
    cats = load_ahj_catalog()
    ids = {c["ahj_id"] for c in cats}
    assert {"plano_tx", "dallas_tx", "austin_tx", "frisco_tx", "fort_worth_tx", "round_rock_tx"} <= ids


def test_plano_zip_lookup_75():
    rec = lookup_ahj("Plano", "TX", "75074")
    assert rec and rec["ahj_id"] == "plano_tx"
    fee = rec["fees"][0]
    assert fee["amount_usd"] == 75.0
    block = digest_ahj_block("Plano", "TX", "75074")
    assert any("$75.00" in line for line in block["ahj_fee_lines"])
    assert any("250.50" in g.get("title", "") for g in block["ahj_gotchas"])
    assert len(block["ahj_inspection_sequence"]) >= 3


def test_dallas_min_trade_167():
    rec = lookup_ahj("Dallas", "TX", "75201")
    assert rec and rec["ahj_id"] == "dallas_tx"
    assert rec["fees"][0]["amount_usd"] == 167.0
    assert "7vsc-id2i" in (rec.get("open_data") or {}).get("socrata_url", "")
    block = digest_ahj_block("Dallas", "TX", "75201")
    assert any("$167.00" in line for line in block["ahj_fee_lines"])
    assert block["ahj_citation_required"] is True


def test_austin_requires_schedule_no_invented_dollars():
    rec = lookup_ahj("Austin", "TX", "78704")
    assert rec and rec["ahj_id"] == "austin_tx"
    fee = rec["fees"][0]
    assert fee.get("amount_requires_schedule") is True
    assert fee.get("amount_usd") is None
    block = digest_ahj_block("Austin", "TX", "78704")
    joined = " ".join(block["ahj_fee_lines"])
    assert "official schedule" in joined.lower() or "must be taken" in joined.lower()
    assert "75.00" not in joined and "167.00" not in joined
    assert block.get("ahj_design_criteria_url")
    assert "austintexas.gov" in block["ahj_design_criteria_url"]
    titles = " ".join(g.get("title", "") for g in block["ahj_gotchas"])
    assert "36" in titles or any("36-inch" in " ".join(g.get("checklist") or []) for g in block["ahj_gotchas"])


def test_lake_dallas_does_not_resolve_to_dallas():
    # Lake Dallas is a different AHJ — must not alias to City of Dallas
    assert lookup_ahj("Lake Dallas", "TX", "75065") is None
    assert lookup_ahj("Lake Dallas", "TX", "") is None
    assert digest_ahj_block("Lake Dallas", "TX", "75065") == {}
    # ZIP-first: a Dallas city label with a non-catalog ZIP still resolves by city
    # (correct for Dallas addresses); Lake Dallas city string must never hit that path.
    assert lookup_ahj("Dallas", "TX", "75201")["ahj_id"] == "dallas_tx"


def test_enrich_plano_marks_cost_verified():
    analysis = {
        "project_info": {"city": "Plano", "state": "TX", "zip": "75074"},
        "punch_list": {"punch_list": []},
        "summary": {},
        "honesty": {"cost_verified": False},
        "source_urls": [],
    }
    out = enrich_analysis_with_ahj(analysis)
    assert out["summary"]["ahj_id"] == "plano_tx"
    assert out["honesty"]["cost_verified"] is True
    assert out["summary"].get("ahj_verified_fee_total_usd") == 75.0
    assert any(i.get("estimated_cost") == 75.0 and i.get("cost_verified") for i in out["punch_list"]["punch_list"])
    assert len(out["punch_list"]["inspection_sequence"]) >= 3


def test_enrich_austin_does_not_verify_invented_cost():
    analysis = {
        "project_info": {"city": "Austin", "state": "TX", "zip": "78704"},
        "punch_list": {"punch_list": []},
        "summary": {},
        "honesty": {"cost_verified": False},
        "source_urls": [],
    }
    out = enrich_analysis_with_ahj(analysis)
    assert out["summary"]["ahj_id"] == "austin_tx"
    # No verified dollar total — schedule pull only
    assert out["summary"].get("ahj_verified_fee_total_usd") in (None, 0)
    assert out["honesty"].get("cost_verified") is not True
    tasks = " ".join(i.get("task", "") for i in out["punch_list"]["punch_list"])
    assert "fee schedule" in tasks.lower() or "Pull live" in tasks


def test_scout_extras_dallas():
    extras = scout_extras_for("Dallas", "TX", "75201")
    assert extras["permits"]
    assert any("Dallas" in q for q in extras["permits"])


def test_digest_includes_citation_required_fees():
    raw = {
        "zip": "75074",
        "site_address": "100 Main St, Plano, TX 75074",
        "jurisdiction": {"city": "Plano", "state": "TX", "zip": "75074"},
        "agentic_workflow": [],
        "scout_steps": [],
    }
    digest = json.loads(build_research_digest(raw, [], ""))
    assert digest["ahj_id"] == "plano_tx"
    assert digest["ahj_citation_required"] is True
    assert digest["plano_electrical_permit_fee_sync_usd"] == 75.0
    assert "250.50" in digest["plano_ord_250_50_requirement"]
    assert any("$75.00" in line for line in digest["ahj_fee_lines"])


def test_digest_dallas_167_and_open_data():
    raw = {
        "zip": "75201",
        "site_address": "722 Munger Ave, Dallas, TX 75201",
        "jurisdiction": {"city": "Dallas", "state": "TX", "zip": "75201"},
        "agentic_workflow": [],
        "scout_steps": [],
        "dallas_open_data": {
            "source": "dallas_open_data_fixture",
            "socrata_url": "https://www.dallascityhall.com/resource/7vsc-id2i.json",
            "count": 1,
            "note": "fixture",
            "permits": [{"address": "722 MUNGER AVE"}],
        },
    }
    digest = json.loads(build_research_digest(raw, [], ""))
    assert digest["ahj_id"] == "dallas_tx"
    assert digest["dallas_min_trade_permit_usd"] == 167.0
    assert "167" in digest["dallas_min_trade_permit_note"]
    assert digest["dallas_open_data"]["socrata_url"].endswith("7vsc-id2i.json")
    assert any("7vsc-id2i" in u for u in digest["unique_source_urls"])


def test_digest_austin_no_invented_fee_dollars():
    raw = {
        "zip": "78704",
        "site_address": "100 Congress Ave, Austin, TX 78704",
        "jurisdiction": {"city": "Austin", "state": "TX", "zip": "78704"},
        "agentic_workflow": [],
        "scout_steps": [],
    }
    digest = json.loads(build_research_digest(raw, [], ""))
    assert digest["ahj_id"] == "austin_tx"
    assert "do not invent" in digest["austin_safety_surcharge_note"].lower()
    assert "36-inch" in digest["austin_design_criteria_requirement"]
    assert digest.get("ahj_design_criteria_url")
    fee_blob = json.dumps(digest["ahj_fee_table"])
    assert "null" in fee_blob or '"amount_usd": null' in fee_blob.replace(" ", "")


@pytest.mark.parametrize(
    "city,state,zip_code,ahj_id",
    [
        ("Plano", "TX", "75023", "plano_tx"),
        ("Dallas", "TX", "75226", "dallas_tx"),
        ("Austin", "TX", "78701", "austin_tx"),
    ],
)
def test_zip_aliases(city, state, zip_code, ahj_id):
    assert lookup_ahj(city, state, zip_code)["ahj_id"] == ahj_id
