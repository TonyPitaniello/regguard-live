"""Fixture tests for cheap page confirm + ZIP jurisdiction resolver."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE_HTML = """
<html><head><title>Fees</title></head>
<body>
<nav class="navbar">Home</nav>
<main>
  <h1>Building Permit Fees</h1>
  <p>Electrical permit base fee $75.00 for standard residential.</p>
  <p>Plan review fee $150 for commercial projects.</p>
  <p>Confirm all fees on the official schedule before bidding.</p>
</main>
<footer class="footer">Copyright</footer>
<script>alert('x')</script>
</body></html>
"""


def test_clean_and_markdown_extract_fees():
    from cheap_page_confirm import clean_html, html_to_markdown, _regex_fee_rows

    cleaned = clean_html(FIXTURE_HTML)
    assert "script" not in cleaned.lower() or "<script" not in cleaned.lower()
    assert "navbar" not in cleaned.lower() or "Home" not in cleaned  # nav removed
    md = html_to_markdown(cleaned)
    assert "Electrical permit" in md or "75" in md
    rows = _regex_fee_rows(md, "https://example.gov/fees")
    assert rows, "expected at least one fee row from fixture"
    assert any(r.get("amount_usd") == 75.0 for r in rows)


def test_url_allowlist_pack_host():
    from cheap_page_confirm import url_allowed_for_cheap_confirm

    # Non-.gov but pack portal host should be allowed
    assert url_allowed_for_cheap_confirm(
        "https://dallascityhall.com/building",
        pack_urls=[
            "https://dallascityhall.com/departments/sustainabledevelopment/buildinginspection/Pages/default.aspx"
        ],
    )
    assert not url_allowed_for_cheap_confirm(
        "https://random-blog.com/fees",
        pack_urls=["https://www.plano.gov/269/Building-Inspections"],
    )


def test_zip_resolves_plano_citeable():
    from jurisdiction_resolver import resolve_jurisdiction

    r = resolve_jurisdiction(zip_code="75074")
    assert r["state"] == "TX"
    assert r["city"] == "Plano"
    assert r["citeable_local"] is True
    assert (r["local"] or {}).get("pack_key") == "plano, tx"
    assert r["federal"]["pack_key"] == "federal"
    assert (r["state_pack"] or {}).get("state") == "TX"


def test_zip_unknown_still_federal_state():
    from jurisdiction_resolver import resolve_jurisdiction

    # 90210 is CA (Beverly Hills area) — may not be in seed city list
    r = resolve_jurisdiction(zip_code="90210")
    assert r["state"] == "CA"
    assert r["federal"]["pack_key"] == "federal"
    assert r["citeable_local"] is False
    assert (r["local"] or {}).get("citeable") is False


def test_national_zip3_coverage():
    from jurisdiction_resolver import state_from_zip

    assert state_from_zip("10001") == "NY"
    assert state_from_zip("78701") == "TX"
    assert state_from_zip("98101") == "WA"


def test_attach_jurisdiction_cards_prepends_punch():
    from jurisdiction_resolver import attach_jurisdiction_cards, resolve_jurisdiction

    resolved = resolve_jurisdiction(zip_code="60601")
    analysis = {
        "project_info": {"zip": "60601"},
        "punch_list": {"punch_list": [{"task": "Local only", "priority": "LOW"}]},
    }
    out = attach_jurisdiction_cards(analysis, resolved)
    assert out.get("federal_card")
    assert out.get("state_card")
    tasks = [i.get("task") for i in out["punch_list"]["punch_list"]]
    fed = [t for t in tasks if t and t.startswith("[Federal]")]
    state = [t for t in tasks if t and t.startswith("[State]")]
    assert 1 <= len(fed) <= 2
    assert 1 <= len(state) <= 2
    assert out["project_info"].get("city") == "Chicago"
    assert out["project_info"].get("state") == "IL"


def test_user_state_overrides_zip3():
    from jurisdiction_resolver import resolve_jurisdiction

    r = resolve_jurisdiction(zip_code="75074", city="Seattle", state="WA")
    assert r["state"] == "WA"
    assert r["city"] == "Seattle"
    assert r["zip3_state_mismatch"] is True
    assert r["citeable_local"] is False


def test_placeholder_city_falls_back_to_zip_seed():
    from jurisdiction_resolver import resolve_jurisdiction

    r = resolve_jurisdiction(zip_code="75074", city="Unknown", state="US")
    assert r["city"] == "Plano"
    assert r["state"] == "TX"
    assert r["citeable_local"] is True
    assert (r["local"] or {}).get("pack_key") == "plano, tx"

def test_llm_amount_must_appear_on_page():
    from cheap_page_confirm import _amount_appears_in_markdown

    md = "Electrical permit base fee $75.00 for standard residential."
    assert _amount_appears_in_markdown(md, 75.0)
    assert not _amount_appears_in_markdown(md, 9999.0)


def test_cheap_confirm_timeout_fail_open(monkeypatch):
    import cheap_page_confirm as cpc

    def slow(*_a, **_k):
        import time

        time.sleep(2.0)
        return {"status": "ok", "fees": [], "notes": [], "verified": False}

    monkeypatch.setattr(cpc, "_run_cheap_page_confirm_inner", slow)
    out = cpc.run_cheap_page_confirm(
        "https://www.plano.gov/fees",
        pack_urls=["https://www.plano.gov/fees"],
        use_llm=False,
        deadline_sec=0.2,
    )
    assert out.get("status") == "timeout"


def test_free_pack_confirm_unknown_zip_no_firecrawl_md(monkeypatch):
    """Unknown ZIP still builds analysis with federal/state; cheap confirm skipped (no portal)."""
    import free_pack_confirm as fpc

    monkeypatch.setenv("FREE_TRIAL_ALLOWLIST_SEARCH", "0")
    monkeypatch.setenv("FREE_TRIAL_CHEAP_CONFIRM", "1")
    monkeypatch.setenv("FREE_TRIAL_MARKDOWN_CONFIRM", "0")

    analysis = fpc.build_free_pack_confirm_analysis(
        address="1 Main St",
        city="",
        state="",
        zip_code="98101",
        project_type="commercial",
    )
    assert analysis["finops_mode"] == "pack_confirm"
    assert analysis.get("federal_card")
    assert analysis.get("jurisdiction", {}).get("state") == "WA"
    assert analysis["free_confirm"].get("markdown_rescrape") is False
    punch = analysis["punch_list"]["punch_list"]
    assert any(str(i.get("task", "")).startswith("[Federal]") for i in punch)


def test_merge_cheap_confirm_into_analysis():
    from cheap_page_confirm import merge_cheap_confirm_into_analysis

    analysis = {"punch_list": {"punch_list": []}, "fee_card": {"fees": []}}
    confirm = {
        "status": "ok",
        "source_url": "https://www.plano.gov/fees",
        "fees": [
            {
                "label": "Electrical permit",
                "amount_usd": 75.0,
                "detail": "test",
                "verified": True,
                "source_url": "https://www.plano.gov/fees",
                "source_label": "Cheap page confirm",
            }
        ],
        "notes": ["Confirm before bid"],
        "markdown_chars": 100,
        "llm_used": False,
    }
    out = merge_cheap_confirm_into_analysis(analysis, confirm)
    assert out["cheap_confirm"]["status"] == "ok"
    assert out["fee_card"]["fees"][0]["amount_usd"] == 75.0
    assert out["punch_list"]["punch_list"]


def test_data_files_exist():
    root = Path(__file__).resolve().parents[1] / "data"
    assert (root / "zip3_to_state.json").is_file()
    assert (root / "tx_zcta.json").is_file()
    assert (root / "national_zcta_seed.json").is_file()
    zip3 = json.loads((root / "zip3_to_state.json").read_text())
    assert zip3.get("750") == "TX"
    assert zip3.get("100") == "NY"


def test_thin_page_status(monkeypatch):
    import cheap_page_confirm as cpc
    monkeypatch.setattr(cpc, "fetch_page_markdown", lambda *a, **k: "short shell only")
    out = cpc._run_cheap_page_confirm_inner(
        "https://www.plano.gov/350/Building-Inspections-Permits",
        pack_urls=["https://www.plano.gov/350/Building-Inspections-Permits"],
        use_llm=False,
    )
    assert out.get("status") == "thin_page"
