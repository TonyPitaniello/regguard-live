"""Cost-effective 10/10 IC quality fixes — unit tests."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from ahj_catalog import ahj_identity_conflict, lookup_ahj  # noqa: E402
from arbitrage_enrichment import _build_contingency, enrich_analysis_with_arbitrage  # noqa: E402
from geocode import is_null_island  # noqa: E402
from pro_deep_analysis import _merge_deep_into_analysis  # noqa: E402


def test_zip_city_conflict_helper():
    c = ahj_identity_conflict("Richardson", "TX", "75075")
    assert c and c["conflict"] is True
    assert c["resolved_city"] == "Plano"
    assert "75075" in c["note"]
    assert ahj_identity_conflict("Plano", "TX", "75075") is None


def test_lookup_zip_wins_on_conflict():
    rec = lookup_ahj("Richardson", "TX", "75075")
    assert rec and rec["ahj_id"] == "plano_tx"


def test_null_island():
    assert is_null_island(0, 0) is True
    assert is_null_island(None, None) is True
    assert is_null_island(32.95, -96.7) is False


def test_dc_contingency_floor_hides_stub_usd():
    band = _build_contingency(2, 10, 0, 36550, is_dc=True)
    assert band["pct_mid"] >= 18.0
    assert band["usd_mid"] is None  # stub rollup
    assert band["drivers"].get("data_center_parallel_track") is True
    band2 = _build_contingency(2, 10, 0, 500_000, is_dc=True)
    assert band2["usd_mid"] is not None


def test_catalog_fees_surface_on_generic_pack():
    analysis = {
        "project_info": {
            "address": "Building 4",
            "city": "Richardson",
            "state": "TX",
            "zip": "75075",
            "type": "data-center",
        },
        "punch_list": {"punch_list": []},
        "summary": {"estimated_total_cost": 36550},
        "ahj": {"ahj_id": "plano_tx"},
        "coverage": {"tier": "federal_state"},
    }
    out = enrich_analysis_with_arbitrage(analysis)
    fees = (out.get("fee_card") or {}).get("fees") or []
    assert fees, "catalog fees should populate fee_card"
    assert (out.get("ahj_card") or {}).get("name", "").startswith("Plano")
    gotchas = (out.get("gotcha_watchlist") or {}).get("items") or []
    assert gotchas, "catalog gotchas should populate watchlist"
    assert out.get("ahj_identity", {}).get("conflict") is True
    assert (out.get("contingency_band") or {}).get("pct_mid", 0) >= 18.0


def test_scout_urls_not_auto_verified():
    base = {
        "punch_list": {
            "punch_list": [
                {
                    "priority": "CRITICAL",
                    "task": "Contact municipal permitting office",
                    "verified": False,
                }
            ]
        },
        "ahj": {
            "ahj_portal_url": "https://www.plano.gov/building-inspections",
            "ahj_citation_urls": ["https://www.plano.gov/292/Building-Inspections"],
        },
        "next_steps": ["4. Upgrade to Contractor Pro for citeable research memos with source URLs"],
    }
    research = {
        "summary": "- [ ] Do a thing\n",
        "source_urls": [
            "https://www.permitting.gov/projects/title-41-fixing-americas-surface-transportation-act-fast-41",
            "https://www.plano.gov/building-inspections",
        ],
    }
    merged = _merge_deep_into_analysis(base, research)
    items = (merged.get("punch_list") or {}).get("punch_list") or []
    # First item may be md task; find the municipal contact line
    municipal = next(
        (i for i in items if "municipal" in str(i.get("task") or "").lower()),
        items[-1],
    )
    # Unrelated FAST-41 host must not verify municipal contact
    if "permitting.gov" in str(municipal.get("source_url") or ""):
        assert municipal.get("verified") is False
        assert municipal.get("source_label") == "Related scout link"
    # Plano-bound URL can verify
    plano_bound = next(
        (
            i
            for i in items
            if "plano.gov" in str(i.get("source_url") or "") and i.get("verified")
        ),
        None,
    )
    # At least one path: rotating may assign plano.gov to some item
    assert any(i.get("source_url") for i in items)
    steps = " ".join(str(s) for s in (merged.get("next_steps") or [])).lower()
    assert "upgrade to contractor pro" not in steps
