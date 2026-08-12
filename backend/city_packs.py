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
    for name in ("plano", "dallas", "austin"):
        if name in text or name in c:
            return f"{name}, tx"
    if z.startswith("787"):
        return "austin, tx"
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
            "portal_url": "https://www.plano.gov/269/Building-Inspections",
            "fees_url": "https://www.plano.gov/269/Building-Inspections",
            "phone": "Confirm on plano.gov",
            "notes": "Confirm fees and filings with Plano Building Inspections before bid.",
        },
        "fees": [
            {
                "label": "Electrical permit (2026 sync note)",
                "amount_usd": 75,
                "detail": "$65 base + $10 laborer — confirm on official fee schedule",
                "verified": False,
                "source_url": "https://www.plano.gov/269/Building-Inspections",
                "source_label": "City of Plano Building Inspections",
            }
        ],
        "gotchas": [
            {
                "id": "plano_250_50",
                "title": "Plano Ord. 250.50 grounding",
                "detail": "Two 8-ft rods spaced 20 ft apart, bonded with 2/0 AWG (not generic 6-ft NEC narrative)",
                "severity": "CRITICAL",
                "source_url": "https://www.plano.gov/269/Building-Inspections",
                "source_label": "Plano AHJ / confirm ordinance text",
            }
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
            }
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
            "portal_url": "https://www.austintexas.gov/department/development-services",
            "fees_url": "https://www.austintexas.gov/development-services/fees",
            "phone": "Confirm on austintexas.gov",
            "notes": "Design Criteria can override generic NEC narratives — verify before bid.",
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
                "source_url": "https://www.austintexas.gov/department/development-services",
                "source_label": "Austin Design Criteria / DSD",
            },
            {
                "id": "austin_service_upgrade",
                "title": "Service upgrade bus pattern",
                "detail": "225A interior panel bus / 200A main / solar-ready pattern — verify current Design Criteria",
                "severity": "HIGH",
                "source_url": "https://www.austintexas.gov/department/development-services",
                "source_label": "Austin Design Criteria",
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
    """Outside beachhead — honest thin pack."""
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
            "notes": "Outside strongest citeable coverage (Dallas / Plano / Austin). Treat all items as Unverified until confirmed.",
        },
        "fees": [],
        "gotchas": [
            {
                "id": "verify_ahj",
                "title": "Confirm local AHJ requirements",
                "detail": "No curated city pack for this locality — verify fees, amendments, and submittals with the AHJ",
                "severity": "HIGH",
                "source_url": None,
                "source_label": "Unverified",
            }
        ],
        "documents": [
            "Single-line diagram",
            "Load calculations",
            "Cut sheets",
            "Contractor license / registration",
        ],
        "timeline_hint": "Confirm plan review and inspection windows with the local AHJ",
    }
