from ic_ultralocal_scout import _hit_to_killer, _query_lines, run_ic_local_ultralocal_scout


def test_houston_coverage_note_is_not_a_stamp_driver():
    from city_packs import resolve_city_pack

    pack = resolve_city_pack("Houston", "TX", "77002")
    note = next(g for g in pack["gotchas"] if g["id"] == "houston_not_the_metro")
    assert note["priority"] == "NOTE"


def test_query_lines_cover_local_and_ultralocal():
    qs = _query_lines("Plano", "TX", "75074", "1201 14th St")
    buckets = {b for b, _ in qs}
    assert "local_ahj" in buckets
    assert "ultralocal_hoa" in buckets
    assert "ultralocal_mud" in buckets


def test_hit_to_killer():
    k = _hit_to_killer(
        {"title": "MUD 1", "url": "https://example.com/mud", "snippet": "assessments"},
        "ultralocal_mud",
    )
    assert k is not None
    assert k["ultralocal_bucket"] == "ultralocal_mud"
    assert "MUD" in k["title"]


def test_fort_worth_electrical_code_is_not_an_allen_finding():
    """The Chelsea IC packet filed Fort Worth's NEC page as an Allen amendment."""
    hit = {
        "title": "Building & Energy Codes - the City of Fort Worth",
        "url": "https://www.fortworthtexas.gov/departments/development-services/building-energy-codes",
        "snippet": (
            "The adopted electrical code is the 2026 National Electrical Code. "
            "Allen TX 75013 local amendments."
        ),
    }
    assert _hit_to_killer(hit, "local_codes", city="Allen") is None


def test_allen_ordinance_page_stays():
    k = _hit_to_killer(
        {
            "title": "Codes & Ordinances | Allen, TX",
            "url": "https://library.municode.com/tx/allen/codes/code_of_ordinances",
            "snippet": "View permits and contractor forms.",
        },
        "local_codes",
        city="Allen",
    )
    assert k is not None
    assert "Allen" in (k.get("title") or "")


def test_fort_worth_keeps_its_own_electrical_code_page():
    k = _hit_to_killer(
        {
            "title": "Building & Energy Codes - the City of Fort Worth",
            "url": "https://www.fortworthtexas.gov/departments/development-services/building-energy-codes",
            "snippet": "The adopted electrical code is the 2026 National Electrical Code.",
        },
        "local_codes",
        city="Fort Worth",
    )
    assert k is not None


def test_south_houston_is_not_houston():
    hit = {
        "title": "Permits / Inspection | South Houston, TX",
        "url": "https://www.southhoustontx.gov/permits",
        "snippet": "1018 Dallas St. Inspection department.",
    }
    assert _hit_to_killer(hit, "local_ahj", city="Houston") is None


def test_harris_county_engineer_is_not_the_houston_building_department():
    hit = {
        "title": "Office of the County Engineer > Services > Permits > FAQ",
        "url": "https://oce.harriscountytx.gov/Services/Permits/FAQ",
        "snippet": "Plans need to be dropped off at 1111 Fannin Street.",
    }
    assert _hit_to_killer(hit, "local_ahj", city="Houston") is None


def test_page_chrome_is_not_a_risk():
    hit = {
        "title": "Houston Business Portal",
        "url": "https://www.houstontx.gov/business/plan/permits-inspections.html",
        "snippet": "[Skip to main content](https://www.houstontx.gov/business/plan/permits-inspections.html#mainskip) ![](https://www.google.com/images/cleardot.gif)",
    }
    assert _hit_to_killer(hit, "local_ahj", city="Houston") is None


def test_houston_permitting_center_stays():
    k = _hit_to_killer(
        {
            "title": "Houston Permitting Center",
            "url": "https://www.houstonpermittingcenter.org/",
            "snippet": "Commercial building permits and inspections.",
        },
        "local_ahj",
        city="Houston",
    )
    assert k is not None


def test_run_disabled_passthrough(monkeypatch):
    monkeypatch.setenv("IC_ULTRALOCAL_SCOUT", "0")
    base = {"project_info": {"city": "Plano", "state": "TX", "zip": "75074"}, "margin_killers": []}
    out = run_ic_local_ultralocal_scout(base, city="Plano", state="TX", zip_code="75074")
    assert out.get("ultralocal_scout") is None or not out.get("ultralocal_scout", {}).get("enabled")
