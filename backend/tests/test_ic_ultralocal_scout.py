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


def test_alamo_heights_is_not_a_san_antonio_page():
    from ic_ultralocal_scout import _foreign_municipal_page

    assert _foreign_municipal_page(
        "Building and Misc Permits",
        "",
        "https://www.alamoheightstx.gov/services/development/building-and-misc-permits/",
        "San Antonio",
    )
    assert not _foreign_municipal_page(
        "FY 2027 Development Fee Schedule",
        "",
        "https://docsonline.sanantonio.gov/DSDUploads/CurrentFeeSchedule.pdf",
        "San Antonio",
    )


def test_receipt_blocks_the_houston_scrape_lines():
    from ic_ultralocal_scout import customer_line_blocked

    assert customer_line_blocked(
        "Permits / Inspection | South Houston, TX", "Houston"
    )
    assert customer_line_blocked(
        "Office of the County Engineer > Services > Permits > FAQ", "Houston"
    )
    assert customer_line_blocked(
        "[Skip to main content](https://www.houstontx.gov/) ![](https://www.google.com/images/cleardot.gif)",
        "Houston",
    )
    assert customer_line_blocked(
        "MANDATORY GOTCHA: For each local amendment in the digest, add explicit tasks.",
        "Houston",
    )
    assert not customer_line_blocked(
        "Commercial building permit — 2026 valuation table", "Houston"
    )


def test_public_share_drops_those_lines_and_softens_a_buffer_high():
    from research_store import redact_for_public_share

    out = redact_for_public_share(
        {
            "project_info": {"city": "Houston", "state": "TX", "zip": "77002"},
            "research_depth": "ic",
            "margin_killers": [
                {
                    "title": "[Local AHJ / fees] Permits / Inspection | South Houston, TX",
                    "detail": "1018 Dallas St.",
                    "priority": "MEDIUM",
                },
                {
                    "title": "Valuation is not a permit total",
                    "detail": "Plan review is extra.",
                    "priority": "HIGH",
                },
            ],
            "punch_list": {
                "punch_list": [
                    {
                        "task": "MANDATORY GOTCHA: For each local amendment in the digest that is stricter than base NEC, add explicit tasks.",
                        "priority": "HIGH",
                    },
                    {"task": "Confirm fees with Houston Permitting Center", "priority": "HIGH"},
                ]
            },
            "environmental_screening": {
                "risk_level": "HIGH",
                "findings": [
                    {
                        "category": "wetlands",
                        "risk_level": "HIGH",
                        "verified": True,
                        "description": "NWI wetlands feature intersects this map pin (or within ~120 m).",
                    },
                    {
                        "category": "flood_zones",
                        "risk_level": "LOW",
                        "verified": True,
                        "description": "FEMA NFHL at pin: zone X.",
                    },
                ],
            },
            "regguard_stamp": {"grade": "PASS", "drivers": []},
            "stamp_grade": "PASS",
            "coverage": {"tier": "full_pack", "badge": "Full city pack"},
        }
    )
    titles = [k["title"] for k in out["margin_killers"]]
    assert titles == ["Valuation is not a permit total"]
    tasks = [p["task"] for p in out["punch_list"]["punch_list"]]
    assert tasks == ["Confirm fees with Houston Permitting Center"]
    assert out["environmental_screening"]["risk_level"] == "MEDIUM"
    assert out["stamp_grade"] == "PASS"


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
