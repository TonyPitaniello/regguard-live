"""
Curated city packs for DFW / Austin bid-time arbitrage.
Used by arbitrage_enrichment — not a full code library.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def _norm_city_state(city: str = "", state: str = "", zip_code: str = "") -> str:
    c = (city or "").strip().lower()
    s = (state or "").strip().lower().replace("texas", "tx")
    z = (zip_code or "").strip()
    text = f"{c}, {s}" if s else c
    text = text.replace("texas", "tx")
    c_compact = c.replace(" ", "").replace(".", "")
    if "frisco" in text or "frisco" in c:
        return "frisco, tx"
    if "fortworth" in c_compact or "ftworth" in c_compact or "fort worth" in text:
        return "fort worth, tx"
    if "roundrock" in c_compact or "round rock" in text:
        return "round rock, tx"
    if "arlington" in text or "arlington" in c:
        return "arlington, tx"
    if "irving" in text or "irving" in c:
        return "irving, tx"
    if "garland" in text or "garland" in c:
        return "garland, tx"
    if "mckinney" in c_compact or "mc kinney" in text or "mckinney" in text:
        return "mckinney, tx"
    if "richardson" in text or "richardson" in c:
        return "richardson, tx"
    if "carrollton" in text or "carrollton" in c:
        return "carrollton, tx"
    if "san antonio" in text or "sanantonio" in c_compact:
        return "san antonio, tx"
    if c == "houston":
        return "houston, tx"
    for name in ("plano", "dallas", "austin"):
        if name in text or name in c:
            return f"{name}, tx"
    if z.startswith("787"):
        return "austin, tx"
    if z[:5] in ("75033", "75034", "75035", "75036"):
        return "frisco, tx"
    if z.startswith("761"):
        return "fort worth, tx"
    if z[:5] in ("78664", "78665", "78681"):
        return "round rock, tx"
    if z[:5] in ("76010", "76011", "76012", "76013", "76014", "76015", "76016", "76017", "76018"):
        return "arlington, tx"
    if z[:5] in ("75038", "75039", "75060", "75061", "75062", "75063"):
        return "irving, tx"
    if z[:5] in ("75040", "75041", "75042", "75043", "75044"):
        return "garland, tx"
    if z[:5] in ("75069", "75070", "75071", "75072"):
        return "mckinney, tx"
    if z[:5] in ("75080", "75081", "75082", "75083"):
        return "richardson, tx"
    if z[:5] in ("75006", "75007", "75010"):
        return "carrollton, tx"
    if z.startswith("782") and not c:
        return "san antonio, tx"
    if z.startswith("770") and not c:
        return "houston, tx"
    if z.startswith("750") and not c:
        return "plano, tx"
    if (z.startswith("752") or z.startswith("751")) and not c:
        return "dallas, tx"
    return text.strip(", ")


CITY_PACKS: Dict[str, Dict[str, Any]] = {
    "plano, tx": {
        "city": "Plano",
        "state": "TX",
        "ahj": {
            "name": "City of Plano Building Inspections",
            "portal_url": "https://www.plano.gov/350/Building-Inspections-Permits",
            "fees_url": "https://www.plano.gov/1648/Development-Services",
            "phone": "972-941-7140",
            "notes": (
                "Confirm fees with Plano Building Inspections / Development Services before bid. "
                "Online permits: trakit.plano.gov. Many plano.gov pages are JS-rendered — "
                "use pack fees as planning aids until confirmed on the official schedule."
            ),
        },
        "fees": [
            {
                "label": "Electrical permit — confirm on the Jan 2, 2026 schedule",
                "amount_usd": None,
                "detail": (
                    "Ordinance 2025-11-4. Commercial electrical inspections are by floor area. "
                    "$75 on that schedule is the first reinspection, not a permit total."
                ),
                "verified": False,
                "source_url": "https://www.plano.gov/350/Building-Inspections-Permits",
                "source_label": "City of Plano Building Inspections",
            }
        ],
        "gotchas": [
            {
                "id": "plano_250_50",
                "title": "Plano Ord. 250.50 grounding",
                "detail": "Two 8-ft rods spaced 20 ft apart, bonded with 2/0 AWG (not generic 6-ft NEC narrative)",
                "severity": "CRITICAL",
                "source_url": "https://www.plano.gov/350/Building-Inspections-Permits",
                "source_label": "Plano AHJ / confirm ordinance text",
            },
            {
                "id": "plano_dc_large_load",
                "title": "Data center / large-load path",
                "detail": "Mission-critical or large electrical load may need zoning/use confirmation + utility interconnection in parallel with building permits — not a standard trade permit only",
                "priority": "HIGH",
                "source_url": "https://www.plano.gov/350/Building-Inspections-Permits",
                "source_label": "Confirm with Plano Development / Building Inspections",
            },
            {
                "id": "plano_permit_fee_path",
                "title": "Fees + permit path must be reconfirmed before bid",
                "detail": "Plano fee pages are planning aids — verify with Building Inspections / Development Services before locking bid contingency. Online permits: trakit.plano.gov.",
                "severity": "CRITICAL",
                "source_url": "https://www.plano.gov/1648/Development-Services",
                "source_label": "Plano Development Services",
            },
            {
                "id": "plano_trade_application",
                "title": "Confirm trade application type early",
                "detail": "Wrong application type stalls review — electrical vs general building path. Bid risk: not a quote until confirmed.",
                "severity": "HIGH",
                "source_url": "https://www.plano.gov/350/Building-Inspections-Permits",
                "source_label": "Plano Building Inspections",
            },
        ],
        "documents": [
            "Single-line diagram",
            "Load calculations",
            "Panel schedule",
            "Equipment cut sheets",
            "Contractor license / registration",
        ],
        "timeline_hint": "Confirm plan review + inspection windows with Plano before bid",
    },
    "dallas, tx": {
        "city": "Dallas",
        "state": "TX",
        "ahj": {
            "name": "City of Dallas Building Inspection",
            "portal_url": "https://dallascityhall.com/departments/sustainabledevelopment/buildinginspection/Pages/default.aspx",
            "fees_url": "https://dallascityhall.com/departments/sustainabledevelopment/buildinginspection/Pages/default.aspx",
            "phone": "Confirm on dallascityhall.com",
            "notes": "Confirm trade permit path and fees with Dallas Building Inspection.",
        },
        "fees": [
            {
                "label": "Trade / electrical permit fees",
                "amount_usd": None,
                "detail": "Look up current Dallas Building Inspection fee schedule — amounts change",
                "verified": False,
                "source_url": "https://dallascityhall.com/departments/sustainabledevelopment/buildinginspection/Pages/default.aspx",
                "source_label": "Dallas Building Inspection",
            }
        ],
        "gotchas": [
            {
                "id": "dallas_confirm_trade",
                "title": "Confirm trade permit type early",
                "detail": "Wrong application type stalls review — verify electrical vs general building path",
                "severity": "HIGH",
                "source_url": "https://dallascityhall.com/departments/sustainabledevelopment/buildinginspection/Pages/default.aspx",
                "source_label": "Dallas Building Inspection",
            },
            {
                "id": "dallas_dc_ercot",
                "title": "ERCOT / TDSP large-load timing",
                "detail": "Data center or industrial large load: treat ERCOT/TDSP interconnection studies as a parallel critical path to City of Dallas permits — schedule contingency early",
                "priority": "CRITICAL",
                "source_url": "https://dallascityhall.com/departments/sustainabledevelopment/buildinginspection/Pages/default.aspx",
                "source_label": "Confirm utility + Dallas AHJ tracks",
            },
            {
                "id": "dallas_fee_schedule_recheck",
                "title": "Fee schedule is not a fixed number — recheck before bid",
                "detail": "Dallas Building Inspection fee schedules change. Planning aids only. Confirm on the official fee schedule before locking contingency.",
                "severity": "CRITICAL",
                "source_url": "https://dallascityhall.com/departments/sustainabledevelopment/buildinginspection/Pages/default.aspx",
                "source_label": "Dallas Building Inspection",
            },
            {
                "id": "dallas_permit_fee_path",
                "title": "Trade application + city inspection timing",
                "detail": "Confirm inspection wait into bid contingency. Do not assume plan-review windows from a generic NEC narrative.",
                "severity": "HIGH",
                "source_url": "https://dallascityhall.com/departments/sustainabledevelopment/buildinginspection/Pages/default.aspx",
                "source_label": "Dallas Building Inspection",
            },
        ],
        "documents": [
            "Single-line diagram",
            "Load calculations",
            "Site plan / floor plan as required",
            "Contractor registration",
            "Cut sheets for major gear",
        ],
        "timeline_hint": "Build inspection wait into bid contingency",
    },
    "austin, tx": {
        "city": "Austin",
        "state": "TX",
        "ahj": {
            "name": "City of Austin Development Services",
            "portal_url": "https://www.austintexas.gov/development-services",
            "fees_url": "https://www.austintexas.gov/development-services/fees",
            "phone": "Confirm on austintexas.gov",
            "notes": "Design Criteria can override generic NEC narratives — verify before bid. Fee schedule page is scrape-friendly for cheap confirm.",
        },
        "fees": [
            {
                "label": "Development Services fees",
                "amount_usd": None,
                "detail": "Confirm on Austin Development Services fee schedule",
                "verified": False,
                "source_url": "https://www.austintexas.gov/development-services/fees",
                "source_label": "Austin Development Services fees",
            }
        ],
        "gotchas": [
            {
                "id": "austin_gas_36",
                "title": "Austin gas relief clearance",
                "detail": "36-inch minimum clearance from gas relief valves per Design Criteria (verify for job)",
                "severity": "CRITICAL",
                "source_url": "https://www.austintexas.gov/development-services",
                "source_label": "Austin Design Criteria / DSD",
            },
            {
                "id": "austin_service_upgrade",
                "title": "Service upgrade bus pattern",
                "detail": "225A interior panel bus / 200A main / solar-ready pattern — verify current Design Criteria",
                "severity": "HIGH",
                "source_url": "https://www.austintexas.gov/development-services",
                "source_label": "Austin Design Criteria",
            },
            {
                "id": "austin_dc_parallel",
                "title": "Data center: AHJ + utility parallel tracks",
                "detail": "Large-load / colo sites: Austin Development Services permits and utility interconnection are parallel — Bid Risk Receipt contingency should cover both, not only building fees",
                "priority": "CRITICAL",
                "source_url": "https://www.austintexas.gov/development-services",
                "source_label": "Austin DSD + serving utility",
            },
            {
                "id": "austin_fee_schedule_recheck",
                "title": "Fee schedule is not a fixed number — recheck before bid",
                "detail": "Austin Development Services fee pages are planning aids. Confirm on the official fee schedule before locking contingency.",
                "severity": "CRITICAL",
                "source_url": "https://www.austintexas.gov/development-services/fees",
                "source_label": "Austin Development Services fees",
            },
            {
                "id": "austin_permit_fee_path",
                "title": "Permit type + Design Criteria override",
                "detail": "Design Criteria can override generic NEC narratives. Confirm before bid. Fee and design path are separate from AHJ status.",
                "severity": "HIGH",
                "source_url": "https://www.austintexas.gov/development-services",
                "source_label": "Austin DSD",
            },
        ],
        "documents": [
            "Single-line diagram",
            "Load calculations",
            "Energy / solar-ready docs if applicable",
            "Cut sheets",
            "Contractor registration",
        ],
        "timeline_hint": "Austin review cycles vary — confirm before locking bid date",
    },
    "frisco, tx": {
        "city": "Frisco",
        "state": "TX",
        "ahj": {
            "name": "City of Frisco Building Inspections",
            "portal_url": "https://www.friscotexas.gov/292/Building-Inspections",
            "fees_url": "https://www.friscotexas.gov/DocumentCenter/View/864/Permit-Fee-Schedule-PDF",
            "phone": "Confirm on friscotexas.gov",
            "notes": (
                "Confirm fees and trade permit path with Frisco Building Inspections before bid. "
                "Do not copy Plano fee lines into a Frisco bid."
            ),
        },
        "fees": [
            {
                "label": "Commercial building permit — valuation table",
                "amount_usd": None,
                "detail": (
                    "City of Frisco consolidated fee schedule, effective Oct 1, 2026. "
                    "Commercial building permit is 80% of Table 1-A (valuation). "
                    "$300 is the nonrefundable application fee. "
                    "$75 is the commercial reinspection, not the permit total."
                ),
                "verified": False,
                "source_url": "https://www.friscotexas.gov/DocumentCenter/View/864/Permit-Fee-Schedule-PDF",
                "source_label": "Frisco consolidated fee schedule",
            }
        ],
        "gotchas": [
            {
                "id": "frisco_fee_schedule_recheck",
                "title": "Fee schedule is not a fixed number — recheck before bid",
                "detail": "Frisco fee pages are planning aids. Confirm on the official schedule before locking contingency.",
                "priority": "CRITICAL",
                "source_url": "https://www.friscotexas.gov/292/Building-Inspections",
                "source_label": "Frisco Building Inspections",
            },
            {
                "id": "frisco_dc_parallel",
                "title": "Data center: AHJ + utility parallel tracks",
                "detail": "Large-load sites: Frisco permits and utility interconnection are parallel — contingency should cover both",
                "priority": "CRITICAL",
                "source_url": "https://www.friscotexas.gov/292/Building-Inspections",
                "source_label": "Frisco AHJ + serving utility",
            },
            {
                "id": "frisco_trade_type",
                "title": "Confirm trade application type early",
                "detail": "Wrong application type stalls review — electrical vs general building path",
                "priority": "HIGH",
                "source_url": "https://www.friscotexas.gov/292/Building-Inspections",
                "source_label": "Frisco Building Inspections",
            },
        ],
        "documents": [
            "Single-line diagram",
            "Load calculations",
            "Panel schedule",
            "Equipment cut sheets",
            "Contractor registration",
        ],
        "timeline_hint": "Confirm plan review + inspection windows with Frisco before bid",
        "inspection_sequence": [
            "Permit application / plan intake",
            "Rough electrical inspection",
            "Service / meter equipment inspection (if applicable)",
            "Final electrical inspection",
        ],
    },
    "fort worth, tx": {
        "city": "Fort Worth",
        "state": "TX",
        "ahj": {
            "name": "City of Fort Worth Development Services",
            "portal_url": "https://www.fortworthtexas.gov/departments/development-services",
            "fees_url": "https://www.fortworthtexas.gov/departments/development-services",
            "phone": "Confirm on fortworthtexas.gov",
            "notes": (
                "Confirm trade permit path and fees with Fort Worth Development Services. "
                "Large-load / industrial sites: utility interconnection is a parallel clock."
            ),
        },
        "fees": [
            {
                "label": "Development Services / trade permit fees",
                "amount_usd": None,
                "detail": "Confirm on Fort Worth Development Services fee schedule",
                "verified": False,
                "source_url": "https://www.fortworthtexas.gov/departments/development-services",
                "source_label": "Fort Worth Development Services",
            }
        ],
        "gotchas": [
            {
                "id": "fw_fee_schedule_recheck",
                "title": "Fee schedule is not a fixed number — recheck before bid",
                "detail": "Fort Worth fee pages are planning aids. Confirm on the official schedule before locking contingency.",
                "priority": "CRITICAL",
                "source_url": "https://www.fortworthtexas.gov/departments/development-services",
                "source_label": "Fort Worth Development Services",
            },
            {
                "id": "fw_dc_ercot",
                "title": "ERCOT / TDSP large-load timing",
                "detail": "Data center or industrial large load: treat ERCOT/TDSP interconnection as parallel to City of Fort Worth permits",
                "priority": "CRITICAL",
                "source_url": "https://www.fortworthtexas.gov/departments/development-services",
                "source_label": "Confirm utility + Fort Worth AHJ tracks",
            },
            {
                "id": "fw_trade_type",
                "title": "Confirm trade application type early",
                "detail": "Wrong application type stalls review — verify electrical vs general building path",
                "priority": "HIGH",
                "source_url": "https://www.fortworthtexas.gov/departments/development-services",
                "source_label": "Fort Worth Development Services",
            },
        ],
        "documents": [
            "Single-line diagram",
            "Load calculations",
            "Site plan / floor plan as required",
            "Contractor registration",
            "Cut sheets for major gear",
        ],
        "timeline_hint": "Build Development Services wait into bid contingency",
        "inspection_sequence": [
            "Permit application / intake",
            "Rough MEP inspections",
            "Final building / electrical inspection",
        ],
    },
    "round rock, tx": {
        "city": "Round Rock",
        "state": "TX",
        "ahj": {
            "name": "City of Round Rock Planning & Development Services",
            "portal_url": "https://www.roundrocktexas.gov/departments/planning-and-development-services/",
            "fees_url": "https://www.roundrocktexas.gov/wp-content/uploads/2025/11/pds-fees-summary.pdf",
            "phone": "Confirm on roundrocktexas.gov",
            "notes": (
                "Austin-metro corridor. Confirm fees and permit path with Round Rock before bid. "
                "Do not copy Austin fee lines into a Round Rock bid."
            ),
        },
        "fees": [
            {
                "label": "Remodel, finish-out, and addition permits — valuation table",
                "amount_usd": None,
                "detail": (
                    "Planning & Development Fees Summary, updated August 2023, still the file the city hosts. "
                    "Those permits follow the valuation table. Re-inspection on that summary is $75. "
                    "The summary's worked example does not match its own table, so no permit total is stated."
                ),
                "verified": False,
                "source_url": "https://www.roundrocktexas.gov/wp-content/uploads/2025/11/pds-fees-summary.pdf",
                "source_label": "Round Rock Planning & Development Fees Summary",
            }
        ],
        "gotchas": [
            {
                "id": "rr_fee_schedule_recheck",
                "title": "Fee schedule is not a fixed number — recheck before bid",
                "detail": "Round Rock fee pages are planning aids. Confirm on the official schedule before locking contingency.",
                "priority": "CRITICAL",
                "source_url": "https://www.roundrocktexas.gov/departments/planning-and-development-services/",
                "source_label": "Round Rock Planning & Development Services",
            },
            {
                "id": "rr_dc_parallel",
                "title": "Data center: AHJ + utility parallel tracks",
                "detail": "Large-load / colo: Round Rock permits and utility interconnection are parallel — contingency should cover both",
                "priority": "CRITICAL",
                "source_url": "https://www.roundrocktexas.gov/departments/planning-and-development-services/",
                "source_label": "Round Rock AHJ + serving utility",
            },
            {
                "id": "rr_not_austin",
                "title": "Do not assume Austin Design Criteria",
                "detail": "Round Rock is a separate AHJ — verify local amendments; do not bid Austin Design Criteria as Round Rock",
                "priority": "HIGH",
                "source_url": "https://www.roundrocktexas.gov/departments/planning-and-development-services/",
                "source_label": "Round Rock Planning & Development Services",
            },
        ],
        "documents": [
            "Single-line diagram",
            "Load calculations",
            "Cut sheets",
            "Contractor registration",
        ],
        "timeline_hint": "Confirm Round Rock review cycles before locking bid date",
        "inspection_sequence": [
            "Permit application / intake",
            "Rough electrical inspection",
            "Final electrical inspection",
        ],
    },
    "arlington, tx": {
        "city": "Arlington",
        "state": "TX",
        "ahj": {
            "name": "City of Arlington Planning & Development Services",
            "portal_url": "https://www.arlingtontx.gov/city_hall/departments/planning_and_development_services",
            "fees_url": "https://www.arlingtontx.gov/city_hall/departments/planning_and_development_services",
            "phone": "Confirm on arlingtontx.gov",
            "notes": "Confirm fees with Arlington PDS. Do not copy Dallas/Plano fee lines.",
        },
        "fees": [
            {
                "label": "Commercial building permit and plan review",
                "amount_usd": None,
                "detail": (
                    "Phase 2 of the Planning and Development Services fee update took effect Oct 1, 2025 "
                    "and covers commercial building permits and plan review. "
                    "The current schedule is the PDF linked from the city permits page. "
                    "This page does not state a permit total."
                ),
                "verified": False,
                "source_url": "https://www.arlingtontx.gov/News-Articles/2025/September/Arlington-Implementing-Phased-Permit-Fee-Adjustments-in-2025",
                "source_label": "Arlington PDS",
            }
        ],
        "gotchas": [
            {
                "id": "arlington_fee_schedule_recheck",
                "title": "Fee schedule is not a fixed number — recheck before bid",
                "detail": "Confirm Arlington fee schedule before locking contingency.",
                "priority": "CRITICAL",
                "source_url": "https://www.arlingtontx.gov/city_hall/departments/planning_and_development_services",
                "source_label": "Arlington PDS",
            },
            {
                "id": "arlington_sister_city",
                "title": "Do not use sister-city fees for Arlington",
                "detail": "Dallas/Plano fee lines are not Arlington fees",
                "priority": "CRITICAL",
                "source_url": "https://www.arlingtontx.gov/city_hall/departments/planning_and_development_services",
                "source_label": "Arlington PDS",
            },
            {
                "id": "arlington_dc_parallel",
                "title": "Large-load: AHJ + utility parallel clocks",
                "detail": "Utility interconnection runs parallel to Arlington permits",
                "priority": "CRITICAL",
                "source_url": "https://www.arlingtontx.gov/city_hall/departments/planning_and_development_services",
                "source_label": "Arlington AHJ + serving utility",
            },
        ],
        "documents": ["Single-line diagram", "Load calculations", "Contractor registration"],
        "timeline_hint": "Confirm Arlington PDS review windows before bid",
        "inspection_sequence": [
            "Permit application / plan intake",
            "Rough MEP inspections",
            "Final building / electrical inspection",
        ],
    },
    "irving, tx": {
        "city": "Irving",
        "state": "TX",
        "ahj": {
            "name": "City of Irving Building Inspections",
            "portal_url": "https://www.cityofirving.org/353/Building-Inspections",
            "fees_url": "https://irvingtx.gov/gov-rates-fees",
            "phone": "Confirm on cityofirving.org",
            "notes": "Confirm fees with Irving Building Inspections. Do not copy Dallas/Plano fees.",
        },
        "fees": [
            {
                "label": "Commercial building permit — per square foot",
                "amount_usd": None,
                "detail": (
                    "City rates page, Ordinances 2025-11146 and 2025-11165. "
                    "Commercial building permit is $0.45 per square foot of the area of work, $1,200 minimum. "
                    "Plan review is additional. That rate is not a permit total."
                ),
                "verified": False,
                "source_url": "https://irvingtx.gov/gov-rates-fees",
                "source_label": "Irving rates and fees",
            }
        ],
        "gotchas": [
            {
                "id": "irving_fee_schedule_recheck",
                "title": "Fee schedule is not a fixed number — recheck before bid",
                "detail": "Confirm Irving fee schedule before locking contingency.",
                "priority": "CRITICAL",
                "source_url": "https://www.cityofirving.org/353/Building-Inspections",
                "source_label": "Irving Building Inspections",
            },
            {
                "id": "irving_sister_city",
                "title": "Do not use sister-city fees for Irving",
                "detail": "Dallas/Plano fee lines are not Irving fees",
                "priority": "CRITICAL",
                "source_url": "https://www.cityofirving.org/353/Building-Inspections",
                "source_label": "Irving Building Inspections",
            },
            {
                "id": "irving_dc_parallel",
                "title": "Large-load: AHJ + utility parallel clocks",
                "detail": "Utility interconnection runs parallel to Irving permits",
                "priority": "CRITICAL",
                "source_url": "https://www.cityofirving.org/353/Building-Inspections",
                "source_label": "Irving AHJ + serving utility",
            },
        ],
        "documents": ["Single-line diagram", "Load calculations", "Contractor registration"],
        "timeline_hint": "Confirm Irving inspection windows before bid",
        "inspection_sequence": [
            "Permit application / plan intake",
            "Rough MEP inspections",
            "Final building / electrical inspection",
        ],
    },
    "garland, tx": {
        "city": "Garland",
        "state": "TX",
        "ahj": {
            "name": "City of Garland Building Inspection",
            "portal_url": "https://www.garlandtx.gov/353/Building-Inspection",
            "fees_url": "https://www.garlandtx.gov/2152/Building-Permit",
            "phone": "Confirm on garlandtx.gov",
            "notes": "Confirm fees with Garland Building Inspection. Do not copy Dallas fees.",
        },
        "fees": [
            {
                "label": "Commercial building permit — percent of valuation",
                "amount_usd": None,
                "detail": (
                    "City of Garland Building Permit page. The permit fee is a percent of project valuation. "
                    "Plan review is 40% of the permit fee, due at submittal. "
                    "Building Inspections permits also carry a 4.5% technology surcharge. "
                    "This page does not state a permit total."
                ),
                "verified": False,
                "source_url": "https://www.garlandtx.gov/2152/Building-Permit",
                "source_label": "Garland Building Inspection",
            }
        ],
        "gotchas": [
            {
                "id": "garland_fee_schedule_recheck",
                "title": "Fee schedule is not a fixed number — recheck before bid",
                "detail": "Confirm Garland fee schedule before locking contingency.",
                "priority": "CRITICAL",
                "source_url": "https://www.garlandtx.gov/353/Building-Inspection",
                "source_label": "Garland Building Inspection",
            },
            {
                "id": "garland_sister_city",
                "title": "Do not use sister-city fees for Garland",
                "detail": "Dallas/Plano fee lines are not Garland fees",
                "priority": "CRITICAL",
                "source_url": "https://www.garlandtx.gov/353/Building-Inspection",
                "source_label": "Garland Building Inspection",
            },
            {
                "id": "garland_dc_parallel",
                "title": "Large-load: AHJ + utility parallel clocks",
                "detail": "Utility interconnection runs parallel to Garland permits",
                "priority": "CRITICAL",
                "source_url": "https://www.garlandtx.gov/353/Building-Inspection",
                "source_label": "Garland AHJ + serving utility",
            },
        ],
        "documents": ["Single-line diagram", "Load calculations", "Contractor registration"],
        "timeline_hint": "Confirm Garland inspection windows before bid",
        "inspection_sequence": [
            "Permit application / plan intake",
            "Rough MEP inspections",
            "Final building / electrical inspection",
        ],
    },
    "mckinney, tx": {
        "city": "McKinney",
        "state": "TX",
        "ahj": {
            "name": "City of McKinney Building Inspections",
            "portal_url": "https://www.mckinneytexas.org/149/Building-Inspections",
            "fees_url": "https://www.mckinneytexas.org/258/Fee-Schedule",
            "phone": "Confirm on mckinneytexas.org",
            "notes": "Confirm fees with McKinney Building Inspections. Do not copy Plano/Frisco fees.",
        },
        "fees": [
            {
                "label": "Commercial permit fees",
                "amount_usd": None,
                "detail": (
                    "Commercial permit fees are on the Permit Fees PDF linked from the city Fee Schedule page. "
                    "This page does not state a permit total."
                ),
                "verified": False,
                "source_url": "https://www.mckinneytexas.org/258/Fee-Schedule",
                "source_label": "McKinney Building Inspections",
            }
        ],
        "gotchas": [
            {
                "id": "mckinney_fee_schedule_recheck",
                "title": "Fee schedule is not a fixed number — recheck before bid",
                "detail": "Confirm McKinney fee schedule before locking contingency.",
                "priority": "CRITICAL",
                "source_url": "https://www.mckinneytexas.org/149/Building-Inspections",
                "source_label": "McKinney Building Inspections",
            },
            {
                "id": "mckinney_sister_city",
                "title": "Do not use sister-city fees for McKinney",
                "detail": "Plano/Frisco fee lines are not McKinney fees",
                "priority": "CRITICAL",
                "source_url": "https://www.mckinneytexas.org/149/Building-Inspections",
                "source_label": "McKinney Building Inspections",
            },
            {
                "id": "mckinney_dc_parallel",
                "title": "Large-load: AHJ + utility parallel clocks",
                "detail": "Utility interconnection runs parallel to McKinney permits",
                "priority": "CRITICAL",
                "source_url": "https://www.mckinneytexas.org/149/Building-Inspections",
                "source_label": "McKinney AHJ + serving utility",
            },
        ],
        "documents": ["Single-line diagram", "Load calculations", "Contractor registration"],
        "timeline_hint": "Confirm McKinney inspection windows before bid",
        "inspection_sequence": [
            "Permit application / plan intake",
            "Rough MEP inspections",
            "Final building / electrical inspection",
        ],
    },
    "richardson, tx": {
        "city": "Richardson",
        "state": "TX",
        "ahj": {
            "name": "City of Richardson Building Inspection",
            "portal_url": "https://www.cor.net/departments/development-services/building-inspection",
            "fees_url": "https://www.cor.net/departments/building-inspection/pdf-forms",
            "phone": "Confirm on cor.net",
            "notes": "Confirm fees with Richardson Building Inspection. Do not copy Plano/Dallas fees.",
        },
        "fees": [
            {
                "label": "Permit fee schedule",
                "amount_usd": None,
                "detail": (
                    "The permit fee schedule is linked from the Building Inspection PDF forms page. "
                    "This page does not state a permit total."
                ),
                "verified": False,
                "source_url": "https://www.cor.net/departments/building-inspection/pdf-forms",
                "source_label": "Richardson Building Inspection",
            }
        ],
        "gotchas": [
            {
                "id": "richardson_fee_schedule_recheck",
                "title": "Fee schedule is not a fixed number — recheck before bid",
                "detail": "Confirm Richardson fee schedule before locking contingency.",
                "priority": "CRITICAL",
                "source_url": "https://www.cor.net/departments/development-services/building-inspection",
                "source_label": "Richardson Building Inspection",
            },
            {
                "id": "richardson_sister_city",
                "title": "Do not use sister-city fees for Richardson",
                "detail": "Plano/Dallas fee lines are not Richardson fees",
                "priority": "CRITICAL",
                "source_url": "https://www.cor.net/departments/development-services/building-inspection",
                "source_label": "Richardson Building Inspection",
            },
            {
                "id": "richardson_dc_parallel",
                "title": "Large-load: AHJ + utility parallel clocks",
                "detail": "Utility interconnection runs parallel to Richardson permits",
                "priority": "CRITICAL",
                "source_url": "https://www.cor.net/departments/development-services/building-inspection",
                "source_label": "Richardson AHJ + serving utility",
            },
        ],
        "documents": ["Single-line diagram", "Load calculations", "Contractor registration"],
        "timeline_hint": "Confirm Richardson inspection windows before bid",
        "inspection_sequence": [
            "Permit application / plan intake",
            "Rough MEP inspections",
            "Final building / electrical inspection",
        ],
    },
    "carrollton, tx": {
        "city": "Carrollton",
        "state": "TX",
        "ahj": {
            "name": "City of Carrollton Building Inspection",
            "portal_url": "https://www.cityofcarrollton.com/departments/departments-a-f/building-inspection",
            "fees_url": "https://www.cityofcarrollton.com/departments/departments-a-f/building-inspection/fees",
            "phone": "Confirm on cityofcarrollton.com",
            "notes": "Confirm fees with Carrollton Building Inspection. Do not copy Plano/Dallas fees.",
        },
        "fees": [
            {
                "label": "New commercial permit — per $1,000 of value",
                "amount_usd": None,
                "detail": (
                    "On the Building Inspection fees page, new commercial work, apartments, accessory additions, "
                    "remodels, and finish-outs are $6 per $1,000 of value, $125 minimum. "
                    "$125 is the nonrefundable application processing fee. "
                    "$50 is the re-inspection, not the permit total. Impact fees are separate. "
                    "The page says it is not the comprehensive fee schedule."
                ),
                "verified": False,
                "source_url": "https://www.cityofcarrollton.com/departments/departments-a-f/building-inspection/fees",
                "source_label": "Carrollton Building Inspection fees",
            }
        ],
        "gotchas": [
            {
                "id": "carrollton_fee_schedule_recheck",
                "title": "Fee schedule is not a fixed number — recheck before bid",
                "detail": "Confirm Carrollton fee schedule before locking contingency.",
                "priority": "CRITICAL",
                "source_url": "https://www.cityofcarrollton.com/departments/departments-a-f/building-inspection",
                "source_label": "Carrollton Building Inspection",
            },
            {
                "id": "carrollton_sister_city",
                "title": "Do not use sister-city fees for Carrollton",
                "detail": "Plano/Dallas fee lines are not Carrollton fees",
                "priority": "CRITICAL",
                "source_url": "https://www.cityofcarrollton.com/departments/departments-a-f/building-inspection",
                "source_label": "Carrollton Building Inspection",
            },
            {
                "id": "carrollton_dc_parallel",
                "title": "Large-load: AHJ + utility parallel clocks",
                "detail": "Utility interconnection runs parallel to Carrollton permits",
                "priority": "CRITICAL",
                "source_url": "https://www.cityofcarrollton.com/departments/departments-a-f/building-inspection",
                "source_label": "Carrollton AHJ + serving utility",
            },
        ],
        "documents": ["Single-line diagram", "Load calculations", "Contractor registration"],
        "timeline_hint": "Confirm Carrollton inspection windows before bid",
        "inspection_sequence": [
            "Permit application / plan intake",
            "Rough MEP inspections",
            "Final building / electrical inspection",
        ],
    },
    "houston, tx": {
        "city": "Houston",
        "state": "TX",
        "ahj": {
            "name": "Houston Permitting Center",
            "portal_url": "https://www.houstonpermittingcenter.org/",
            "fees_url": "https://www.houstonpermittingcenter.org/media/2636/download",
            "phone": "Confirm on houstonpermittingcenter.org",
            "notes": (
                "City of Houston only. Pasadena, Sugar Land, and The Woodlands are different schedules. "
                "Do not copy a Dallas or Fort Worth fee line onto a Houston bid."
            ),
        },
        "fees": [
            {
                "label": "Commercial building permit — 2026 valuation table",
                "amount_usd": None,
                "detail": (
                    "2026 Building Code Enforcement permit fee schedule. "
                    "Commercial building permit follows the valuation table. "
                    "Plan review is 25% of the estimated building permit fee and is non-refundable. "
                    "A minimum permit fee and an administrative fee are separate lines on that schedule. "
                    "This page does not state a permit total."
                ),
                "verified": False,
                "source_url": "https://www.houstonpermittingcenter.org/media/2636/download",
                "source_label": "Houston Permitting Center 2026 fee schedule",
            }
        ],
        "gotchas": [
            {
                "id": "houston_not_the_metro",
                "title": "City of Houston is not the metro",
                "detail": "Pasadena, Sugar Land, and The Woodlands publish their own schedules. Do not use this table for those cities.",
                "priority": "NOTE",
                "source_url": "https://www.houstonpermittingcenter.org/media/2636/download",
                "source_label": "Houston Permitting Center",
            },
            {
                "id": "houston_valuation",
                "title": "Valuation is not a permit total",
                "detail": "The commercial permit fee depends on project valuation. Plan review is extra.",
                "priority": "HIGH",
                "source_url": "https://www.houstonpermittingcenter.org/media/2636/download",
                "source_label": "Houston Permitting Center 2026 fee schedule",
            },
        ],
        "documents": ["Single-line diagram", "Load calculations", "Contractor registration"],
        "timeline_hint": "Confirm Houston plan review and inspection windows before bid",
        "inspection_sequence": [
            "Permit application / plan intake",
            "Rough MEP inspections",
            "Final building / electrical inspection",
        ],
    },
    "san antonio, tx": {
        "city": "San Antonio",
        "state": "TX",
        "ahj": {
            "name": "City of San Antonio Development Services",
            "portal_url": "https://www.sanantonio.gov/DSD",
            "fees_url": "https://docsonline.sanantonio.gov/DSDUploads/CurrentFeeSchedule.pdf",
            "phone": "Confirm on sanantonio.gov",
            "notes": (
                "Confirm the job against the FY 2027 Development Fee Schedule. "
                "Do not copy an Austin fee line onto a San Antonio bid."
            ),
        },
        "fees": [
            {
                "label": "Commercial plan review and permit — valuation tables",
                "amount_usd": None,
                "detail": (
                    "FY 2027 Development Fee Schedule, revised October 2026. "
                    "Commercial plan review and commercial permit fees follow valuation tables. "
                    "Unless a line says otherwise, fees are subject to a 4% technological improvement surcharge "
                    "and a 4% Development Services surcharge. This page does not state a permit total."
                ),
                "verified": False,
                "source_url": "https://docsonline.sanantonio.gov/DSDUploads/CurrentFeeSchedule.pdf",
                "source_label": "San Antonio FY 2027 Development Fee Schedule",
            }
        ],
        "gotchas": [
            {
                "id": "san_antonio_valuation",
                "title": "Commercial fees follow valuation, not a flat total",
                "detail": "New residential fees in the same PDF are by square foot. Do not use that residential table on a commercial bid.",
                "priority": "CRITICAL",
                "source_url": "https://docsonline.sanantonio.gov/DSDUploads/CurrentFeeSchedule.pdf",
                "source_label": "San Antonio FY 2027 Development Fee Schedule",
            },
            {
                "id": "san_antonio_saws",
                "title": "SAWS fees are a separate section",
                "detail": "San Antonio Water System fees are listed apart from the building permit and are not included in the building valuation table.",
                "priority": "HIGH",
                "source_url": "https://docsonline.sanantonio.gov/DSDUploads/CurrentFeeSchedule.pdf",
                "source_label": "San Antonio FY 2027 Development Fee Schedule",
            },
        ],
        "documents": ["Single-line diagram", "Load calculations", "Contractor registration"],
        "timeline_hint": "Confirm San Antonio review windows before bid",
        "inspection_sequence": [
            "Permit application / plan intake",
            "Rough MEP inspections",
            "Final building / electrical inspection",
        ],
    },
}


def resolve_city_pack(
    city: str = "",
    state: str = "",
    zip_code: str = "",
) -> Optional[Dict[str, Any]]:
    key = _norm_city_state(city, state, zip_code)
    pack = CITY_PACKS.get(key)
    if not pack:
        return None
    out = dict(pack)
    out["pack_key"] = key
    out["citeable"] = True
    return out


def generic_thin_pack(city: str = "", state: str = "", county: str = "") -> Dict[str, Any]:
    """Outside curated/portal coverage — honest thin pack (no null-URL punches)."""
    county_label = (county or "").strip()
    if (city or "").strip():
        label = f"{city.strip()}, {(state or '').strip()}".strip(", ")
    elif county_label:
        label = f"{county_label}, {(state or '').strip()}".strip(", ")
    else:
        label = (state or "Local").strip() or "Local"
    return {
        "pack_key": "generic",
        "citeable": False,
        "city": city or "",
        "state": state or "",
        "ahj": {
            "name": f"{label} AHJ (confirm locally)",
            "portal_url": "",
            "fees_url": "",
            "phone": "",
            "notes": (
                "No curated city pack or metro portal seed for this locality. "
                "Federal + state layers still apply. Confirm local fees and amendments with the AHJ."
            ),
        },
        "fees": [],
        "gotchas": [],
        "documents": [
            "Single-line diagram",
            "Load calculations",
            "Cut sheets",
            "Contractor license / registration",
        ],
        "timeline_hint": "Confirm plan review and inspection windows with the local AHJ",
    }
