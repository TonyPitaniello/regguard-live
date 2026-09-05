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
                "label": "Electrical permit (2026 sync note)",
                "amount_usd": 75,
                "detail": "$65 base + $10 laborer — confirm on official fee schedule",
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
            "fees_url": "https://www.friscotexas.gov/292/Building-Inspections",
            "phone": "Confirm on friscotexas.gov",
            "notes": (
                "Confirm fees and trade permit path with Frisco Building Inspections before bid. "
                "Do not copy Plano fee lines into a Frisco bid."
            ),
        },
        "fees": [
            {
                "label": "Trade / electrical permit fees",
                "amount_usd": None,
                "detail": "Confirm on Frisco Building Inspections fee schedule — amounts change",
                "verified": False,
                "source_url": "https://www.friscotexas.gov/292/Building-Inspections",
                "source_label": "Frisco Building Inspections",
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
            "fees_url": "https://www.roundrocktexas.gov/departments/planning-and-development-services/",
            "phone": "Confirm on roundrocktexas.gov",
            "notes": (
                "Austin-metro corridor. Confirm fees and permit path with Round Rock before bid. "
                "Do not copy Austin fee lines into a Round Rock bid."
            ),
        },
        "fees": [
            {
                "label": "Planning & Development Services fees",
                "amount_usd": None,
                "detail": "Confirm on Round Rock fee schedule — amounts change",
                "verified": False,
                "source_url": "https://www.roundrocktexas.gov/departments/planning-and-development-services/",
                "source_label": "Round Rock Planning & Development Services",
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


def generic_thin_pack(city: str = "", state: str = "") -> Dict[str, Any]:
    """Outside curated/portal coverage — honest thin pack (no null-URL punches)."""
    label = f"{(city or 'Local').strip()}, {(state or '').strip()}".strip(", ")
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
