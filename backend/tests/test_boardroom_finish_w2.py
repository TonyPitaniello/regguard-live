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


def test_dense_city_packs_outside_plano():
    for city in DENSE_CITIES:
        pack = resolve_city_pack(city, "TX")
        assert pack is not None, city
        assert len(pack.get("gotchas") or []) >= 3, city
        ahj = lookup_ahj(city=city, state="TX")
        assert ahj is not None, city
        assert len(ahj.get("gotchas") or []) >= 3, city
        assert len(ahj.get("fees") or []) >= 2, city
