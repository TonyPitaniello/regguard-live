"""Week 2–4 boardroom finish: driver table, QA gate, denser city packs."""

from __future__ import annotations

from ahj_catalog import lookup_ahj
from city_packs import resolve_city_pack
from ic_boardroom_pdf import generate_ic_boardroom_pdf_bytes
from ic_package_composer import compose_ic_package
from ic_package_qa import BOARDROOM_PASS_SCORE, score_boardroom_package
from tests.test_ic_package_composer import RICH


DENSE_CITIES = [
    "Arlington",
    "Irving",
    "Garland",
    "McKinney",
    "Richardson",
    "Carrollton",
    "Fort Worth",
    "Frisco",
    "Dallas",
    "Austin",
    "Plano",
]


def test_contingency_driver_table_present():
    pkg = compose_ic_package(RICH, generated_for="gc@example.com")
    table = pkg["executive_summary"]["contingency"]["driver_table"]
    assert table["rows"]
    assert table["high_end"] or table["mid_band"]


def test_gotcha_confirm_cards():
    pkg = compose_ic_package(RICH, generated_for="gc@example.com")
    cards = pkg["site_findings"]["gotcha_cards"]
    assert len(cards) >= 2
    assert cards[0].get("confirm_step")
    assert cards[0].get("owner")


def test_boardroom_qa_pass():
    pkg = compose_ic_package(RICH, generated_for="gc@example.com")
    qa = pkg["boardroom_qa"]
    assert qa["pass"] is True
    assert qa["score"] >= BOARDROOM_PASS_SCORE
    scored = score_boardroom_package(pkg)
    assert scored["pct"] == qa["pct"]


def test_boardroom_pdf_includes_letterhead_bytes():
    raw = generate_ic_boardroom_pdf_bytes(RICH, generated_for="gc@example.com")
    assert raw[:4] == b"%PDF"
    assert len(raw) > 8000


def test_gc_forward_q2_to_q5_pass_on_rich():
    pkg = compose_ic_package(RICH, generated_for="gc@example.com")
    gc = pkg["boardroom_qa"]["gc_forward"]
    assert gc["all_agentic_ok"] is True
    assert gc["failed"] == []
    by_id = {i["id"]: i for i in gc["items"]}
    assert by_id["Q2"]["ok"] is True
    assert by_id["Q3"]["ok"] is True
    assert by_id["Q4"]["ok"] is True
    assert by_id["Q5"]["ok"] is True
    assert by_id["Q1"]["agentic"] is False
    assert by_id["Q1"]["ok"] is None


def test_gc_q2_fails_on_firm_quote_language():
    from ic_package_qa import score_gc_forward_checks

    pkg = compose_ic_package(RICH, generated_for="gc@example.com")
    pkg["executive_summary"]["contingency"]["plain"] = (
        "This is a firm quote and guaranteed price for permit fees."
    )
    pkg["executive_summary"]["contingency"]["disclaimer"] = "Firm quote"
    gc = score_gc_forward_checks(pkg)
    assert gc["all_agentic_ok"] is False
    assert "Q2" in gc["failed"]


def test_gc_q5_requires_clocks_for_data_center():
    from ic_package_qa import score_gc_forward_checks

    pkg = compose_ic_package(RICH, generated_for="gc@example.com")
    pkg["site_findings"]["parallel_clocks"] = []
    gc = score_gc_forward_checks(pkg)
    assert "Q5" in gc["failed"]


def test_gc_q4_requires_sister_city_on_beachhead():
    from ic_package_qa import score_gc_forward_checks

    pkg = compose_ic_package(RICH, generated_for="gc@example.com")
    pkg["site_findings"]["gotcha_cards"] = [
        {"title": "Generic watch", "detail": "Something local", "priority": "HIGH", "confirm_step": "Call AHJ"}
    ]
    pkg["site_findings"]["gotchas"] = []
    pkg["executive_summary"]["local_gotchas"] = []
    gc = score_gc_forward_checks(pkg)
    assert "Q4" in gc["failed"]

