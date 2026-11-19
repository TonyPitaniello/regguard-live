"""
Sourced IC diligence facts for the DFW / Austin beachhead.

The bundle emitter calls this after city-pack enrichment so the memo,
boardroom, counsel doc, both workbooks, and both CSVs share one string
per fact. Dollars are transcribed from a document page or omitted.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_UNSTATED_DOLLAR = re.compile(r"\$\s*\d[\d,]*(?:\.\d+)?")


def note_without_unstated_dollars(note: str) -> str:
    """A confirm-on-schedule row prints no number, including inside the note."""
    cleaned = _UNSTATED_DOLLAR.sub("", note or "")
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r" +([,.;:])", r"\1", cleaned)
    return cleaned.strip(" ;,-")

DALLAS_FEE_PDF = (
    "https://dallascityhall.com/departments/sustainabledevelopment/"
    "buildinginspection/DCH%20documents/feesummary_725.pdf"
)
DALLAS_NOW = (
    "https://dallascityhall.com/departments/sustainabledevelopment/Pages/DallasNow.aspx"
)
DALLAS_APPLY = "https://aca-prod.accela.com/dallastx"
DALLAS_COMMERCIAL = (
    "https://dallascityhall.com/departments/sustainabledevelopment/"
    "buildinginspection/Pages/commercial_overview.aspx"
)
DALLAS_FEES_PAGE = (
    "https://dallascityhall.com/departments/sustainabledevelopment/"
    "buildinginspection/Pages/fees.aspx"
)
DALLAS_NEW_GUIDE = (
    "https://dallascityhall.com/departments/sustainabledevelopment/"
    "DCH%20documents/2.%20Applying%20for%20a%20Commercial%20New%20Construction%20Permit.pdf"
)
DALLAS_ENG = (
    "https://dallascityhall.com/departments/sustainabledevelopment/"
    "land-management/Pages/engineering-forms.aspx"
)
DALLAS_WW = (
    "https://dallascityhall.com/departments/sustainabledevelopment/"
    "land-management/DCH%20Documents/Application%20for%20Review%20of%20W-WW%20Design%20Plans.pdf"
)
DALLAS_ONCOR = (
    "https://www.oncor.com/outages/api/customerOutage/identifyLocation/address"
    "?term=1950%20N%20Stemmons&extraParams=75207"
)

PLANO_PORTAL = "https://www.plano.gov/building-permits"
PLANO_FEE_PDF = "https://content.civicplus.com/api/assets/465fd3b7-2f75-4bb6-9044-6a62da9fd3ba"
PLANO_APPLY = "https://tx-plano-onlineforms.app.transform.civicplus.com/forms/26643"
PLANO_DRAIN = "https://content.civicplus.com/api/assets/c6b9d1d8-4259-4f1c-96b3-02d96fbacfae"
PLANO_COORD = "https://content.civicplus.com/api/assets/tx-plano/97bdb925-12af-4545-91e6-684150ebb6d0"
PLANO_ONCOR = (
    "https://www.oncor.com/outages/api/customerOutage/identifyLocation/address"
    "?term=6565%20Headquarters&extraParams=75024"
)

AUSTIN_REVIEW = "https://www.austintexas.gov/development-services/commercial-plan-review"
AUSTIN_FEES = "https://www.austintexas.gov/development-services/fees"
AUSTIN_APPLY = "https://abc.austintexas.gov/citizenportal/app/"
AUSTIN_WATER = "https://www.austintexas.gov/water/divisions/utility-development-services"
AUSTIN_ENERGY = "https://austinenergy.com/contractors/Construction-Renovation/Forms"
AUSTIN_FEE_PDF = "https://austin.widen.net/s/jwhpzhhrnp/fees_commercial"
AUSTIN_AE_QUERY = (
    "https://maps.austintexas.gov/arcgis/rest/services/Shared/BoundariesGrids_2/"
    "MapServer/1/query?geometry=-97.72144%2C30.37134&geometryType=esriGeometryPoint"
    "&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=SERVICE_AREA"
    "&returnGeometry=false&f=json"
)

FW_COMMERCIAL = "https://www.fortworthtexas.gov/departments/development-services/permits/commercial"
FW_PACKET = (
    "https://www.fortworthtexas.gov/files/assets/public/v/8/development-services/"
    "documents/resources-applications-forms-videos/p/new-construction-packet-fillable-0522.pdf"
)
FW_APPLY = "https://aca-prod.accela.com/CFW"
FW_FEE = (
    "https://www.fortworthtexas.gov/files/assets/public/v/11/development-services/"
    "documents/resources-applications-forms-videos/f/fee-schedule-oct-2026.pdf"
)
FW_WATER = "https://www.fortworthtexas.gov/departments/water/developers/contact-numbers"
FW_ONCOR = (
    "https://www.oncor.com/outages/api/customerOutage/identifyLocation/address"
    "?term=13600%20Heritage&extraParams=76177"
)

ONCOR_INTAKE = "https://www.oncor.com/newconstructionportal/new-service/commercial-request"


def _city_key(data: Dict[str, Any]) -> str:
    pi = data.get("project_info") if isinstance(data.get("project_info"), dict) else {}
    city = str(pi.get("city") or "").strip().lower().replace(".", "")
    city = " ".join(city.split())
    if city in ("fort worth", "ft worth"):
        return "fort worth"
    if city in ("dallas", "plano", "austin"):
        return city
    return ""


def free_bid_or_walk(city: str) -> Optional[Dict[str, str]]:
    """One sequence a free preview can show. No dollars, no phone, no contingency."""
    key = " ".join(str(city or "").strip().lower().replace(".", "").split())
    if key in ("fort worth", "ft worth"):
        key = "fort worth"
    facts = {
        "dallas": {
            "title": "DallasNow record type is Commercial New Construction or an alteration",
            "detail": (
                "The September 11, 2025 guide says to open DallasNow, choose Commercial Permits, "
                "then Commercial New Construction Permit for a new building. A trade permit is a different record."
            ),
            "source_url": DALLAS_NEW_GUIDE,
            "source_label": "DallasNow commercial new-construction guide",
        },
        "plano": {
            "title": "Electronic submittal is only remodel, alteration, or interior finish",
            "detail": (
                "The Building Inspections form says it can be used only for commercial remodel, "
                "alteration, or interior finish. Other scopes are hard copy."
            ),
            "source_url": PLANO_APPLY,
            "source_label": "Plano Building Inspections electronic submittal form",
        },
        "austin": {
            "title": "File commercial plan review, not a residential service-upgrade sheet",
            "detail": (
                "Commercial work in Austin goes through commercial plan review. "
                "A residential service-upgrade sheet is a different record."
            ),
            "source_url": AUSTIN_REVIEW,
            "source_label": "Austin commercial plan review",
        },
        "fort worth": {
            "title": "The building permit is issued before a trade permit can be applied for",
            "detail": (
                "The commercial permitting page says the building permit must be obtained and issued "
                "before a trade permit application."
            ),
            "source_url": FW_COMMERCIAL,
            "source_label": "Fort Worth commercial permitting",
        },
    }
    return facts.get(key)


def _usd(amount: float) -> str:
    if float(amount).is_integer():
        return f"${float(amount):,.0f}"
    return f"${float(amount):,.2f}"


def _fee(
    *,
    label: str,
    trade: str,
    amount: Optional[float],
    note: str,
    url: str,
    source_label: str,
    status: str,
    owner: str,
) -> Dict[str, Any]:
    if amount is None:
        note = note_without_unstated_dollars(note)
        if "confirm-on-schedule" not in note:
            note = f"{note} confirm-on-schedule".strip()
    return {
        "label": label,
        "name": label,
        "trade": trade,
        "amount_usd": amount,
        "amount_requires_schedule": amount is None,
        "detail": note,
        "note": note,
        "source_url": url,
        "source_label": source_label,
        "verified": True if amount is not None else False,
        "status": status,
        "owner": owner,
    }


def _driver(priority: str, title: str, detail: str, url: str, source_label: str) -> Dict[str, Any]:
    return {
        "priority": priority,
        "severity": priority,
        "title": title,
        "detail": detail,
        "checklist": [],
        "anti_patterns": [],
        "confirm_step": detail,
        "source_url": url,
        "source_label": source_label,
        "owner": source_label,
    }


def _clock(name: str, detail: str, owner: str, track: str, url: str) -> Dict[str, str]:
    return {"name": name, "detail": detail, "owner": owner, "track": track, "url": url}


def _punch(priority: str, task: str, owner: str, url: str, source_label: str, notes: str) -> Dict[str, Any]:
    return {
        "priority": priority,
        "task": task,
        "timeline": "Before LOI call",
        "owner": owner,
        "responsible_party": owner,
        "trade": "GENERAL",
        "source_url": url,
        "source_label": source_label,
        "citation_label": source_label,
        "verified": bool(url),
        "notes": notes,
        "detail": notes,
    }


def _oncor_clock(match: str, lookup_url: str) -> Dict[str, str]:
    return _clock(
        "Oncor commercial new-service desk",
        (
            f"Oncor ESI ID lookup returns {match}. That places this address on the Oncor electric utility. "
            f"Commercial new-service intake, 888.313.6862, is {ONCOR_INTAKE}"
        ),
        "Oncor 888.313.6862",
        "UTILITY",
        lookup_url,
    )


def _dallas() -> Dict[str, Any]:
    fee_note_175 = (
        "Page 1. Commercial alterations or repairs, includes standalone trade permits. "
        "Minimum permit fee is $175. Effective July 1, 2025."
    )
    fee_note_125 = (
        "Page 1. Additional inspection service fee schedule, 1 trade, $125. "
        "This is the inspection-service line, not the permit minimum."
    )
    fee_note_new = (
        "Page 1 prices commercial alterations, including standalone trade permits, from the value of "
        "proposed work. It does not price a permit from floor area. DCAD account 00100100010020000 "
        "lists this address as a high-rise computer data center of 1,570,969 sqft, 7 stories, built 1983, "
        "and a parking garage of 325,601 sqft. The improvement value on that account is not the value of "
        "proposed work. confirm-on-schedule. "
        "https://www.dallascad.org/AcctDetailCom.aspx?ID=00100100010020000"
    )
    drivers = [
        _driver(
            "CRITICAL",
            "Standalone trade minimum is $175 on the July 1, 2025 summary",
            (
                "Page 1 states the commercial alteration minimum, including standalone trade permits, "
                "is $175. The $125 line on that page is the 1-trade additional inspection service fee, "
                "not the permit. Clears when the estimate uses $175 for that minimum. "
                "Desk: DallasNow call center 214.948.4480."
            ),
            DALLAS_FEE_PDF,
            "Dallas Building Inspection fee summary, page 1",
        ),
        _driver(
            "HIGH",
            "DallasNow record type is Commercial New Construction or an alteration",
            (
                "The September 11, 2025 guide says to open DallasNow, choose Commercial Permits, "
                "then Commercial New Construction Permit for a new building. A trade permit is a "
                "different record. Clears when the record type matches the scope. "
                "Desk: DallasNow call center 214.948.4480."
            ),
            DALLAS_NEW_GUIDE,
            "DallasNow commercial new-construction guide",
        ),
        _driver(
            "HIGH",
            "Commercial permit fees are collected at the end of pre-screen",
            (
                "The fees page states that as of October 2025 the common commercial permit fees "
                "are collected at the end of pre-screen, in one payment, not across three later "
                "collections. Clears when the schedule carries that single pre-screen payment. "
                "Desk: DallasNow call center 214.948.4480."
            ),
            DALLAS_FEES_PAGE,
            "Dallas Building Inspection fees page",
        ),
    ]
    fees = [
        _fee(
            label="Commercial alteration / standalone trade minimum permit fee",
            trade="building",
            amount=175,
            note=fee_note_175,
            url=DALLAS_FEE_PDF,
            source_label="Dallas fee summary page 1, effective July 1, 2025",
            status="effective 2025-07-01",
            owner="DallasNow call center 214.948.4480",
        ),
        _fee(
            label="Additional inspection service fee, 1 trade",
            trade="inspection",
            amount=125,
            note=fee_note_125,
            url=DALLAS_FEE_PDF,
            source_label="Dallas fee summary page 1, effective July 1, 2025",
            status="effective 2025-07-01",
            owner="DallasNow call center 214.948.4480",
        ),
        _fee(
            label="New commercial construction permit",
            trade="building",
            amount=None,
            note=fee_note_new,
            url=DALLAS_FEE_PDF,
            source_label="Dallas fee summary page 1, effective July 1, 2025",
            status="confirm-on-schedule",
            owner="DallasNow call center 214.948.4480",
        ),
        _fee(
            label="Water/wastewater design plan review, 100 LF of pipe or more",
            trade="water",
            amount=1500,
            note=(
                "Application page 1, Ver. 6/19. Review fee, check one: $1500, or $500 if less than "
                "100 LF of pipe. This is the water/wastewater design-plan review fee, not the building permit. "
                "Phone on the form: (214) 948-4607."
            ),
            url=DALLAS_WW,
            source_label="Dallas water/wastewater design plan application, page 1",
            status="form Ver. 6/19",
            owner="Water/Wastewater 214-948-4607",
        ),
        _fee(
            label="Water/wastewater design plan review, less than 100 LF of pipe",
            trade="water",
            amount=500,
            note=(
                "Application page 1, Ver. 6/19. Review fee, check one: $500 if less than 100 LF of pipe. "
                "This is the water/wastewater design-plan review fee, not the building permit. "
                "Phone on the form: (214) 948-4607."
            ),
            url=DALLAS_WW,
            source_label="Dallas water/wastewater design plan application, page 1",
            status="form Ver. 6/19",
            owner="Water/Wastewater 214-948-4607",
        ),
    ]
    clocks = [
        _clock(
            "DallasNow commercial permit intake",
            "Call center 214.948.4480. Apply in DallasNow. The fees page is not the application.",
            "DallasNow call center 214.948.4480",
            "AHJ",
            DALLAS_APPLY,
        ),
        _oncor_clock("premises at 1950 N STEMMONS FWY, DALLAS, TX", DALLAS_ONCOR),
        _clock(
            "Dallas Water/Wastewater and Paving/Drainage",
            (
                "Engineering forms page: project coordinator (214) 948-4205 Paving Drainage and "
                "(214) 948-4607 Water/Wastewater, Room 200, 320 E. Jefferson Blvd. "
                "Electronic engineering review is DallasNow. This is not the Building Inspection call center."
            ),
            "Water/Wastewater 214-948-4607",
            "WATER",
            DALLAS_ENG,
        ),
    ]
    punches = [
        _punch(
            "CRITICAL",
            "Call DallasNow at 214.948.4480 and price the standalone-trade minimum from page 1 ($175), not the 1-trade inspection line ($125).",
            "DallasNow call center 214.948.4480",
            DALLAS_FEE_PDF,
            "Dallas fee summary page 1",
            fee_note_175,
        ),
        _punch(
            "HIGH",
            "Call Oncor commercial new service at 888.313.6862. The ESI ID lookup returns premises at 1950 N STEMMONS FWY, DALLAS, TX.",
            "Oncor 888.313.6862",
            DALLAS_ONCOR,
            "Oncor ESI ID lookup",
            f"Commercial new-service intake, 888.313.6862, is {ONCOR_INTAKE}",
        ),
        _punch(
            "HIGH",
            "Call Water/Wastewater at 214-948-4607 or Paving/Drainage at 214-948-4205. Do not use the Building Inspection call center for this review.",
            "Water/Wastewater 214-948-4607",
            DALLAS_ENG,
            "Dallas engineering forms",
            "Paving/Drainage (214) 948-4205. Water/Wastewater (214) 948-4607. Room 200, 320 E. Jefferson Blvd.",
        ),
    ]
    return _pack(
        ahj_name="City of Dallas Building Inspection / DallasNow",
        portal=DALLAS_NOW,
        fees_url=DALLAS_FEE_PDF,
        apply_url=DALLAS_APPLY,
        inspections_url=DALLAS_COMMERCIAL,
        last_verified="2025-07-01",
        drivers=drivers,
        fees=fees,
        clocks=clocks,
        punches=punches,
        sequence=[
            "Create the application in DallasNow and select Commercial New Construction or Commercial Alteration.",
            "Pay the common commercial permit fees at the end of pre-screen.",
        ],
        headline=(
            "HOLD until the DallasNow record type is selected and the July 1, 2025 "
            "standalone-trade minimum ($175) is the number in the estimate."
        ),
        calls=[
            "Call DallasNow call center 214.948.4480. Ask for the record type and use page 1 of the July 1, 2025 fee summary.",
            "Call Oncor commercial new service 888.313.6862. The ESI ID lookup returns 1950 N STEMMONS FWY.",
            "Call Water/Wastewater at 214-948-4607. Paving/Drainage is 214-948-4205.",
        ],
    )


def _plano() -> Dict[str, Any]:
    area_rows = [
        ("0-3,000 sq ft", 70),
        ("3,001-10,000 sq ft", 90),
        ("10,001-100,000 sq ft", 110),
        ("Over 100,000 sq ft", 130),
    ]
    fees = []
    for band, dollars in area_rows:
        fees.append(
            _fee(
                label=f"Commercial electrical inspection, building floor area {band}",
                trade="electrical",
                amount=float(dollars),
                note=(
                    f"Ordinance 2025-11-4 Exhibit A, effective January 2, 2026. "
                    f"Building (electrical) commercial inspections, calculated by square footage "
                    f"of building floor area, {band}: ${dollars}. This is the inspection line for "
                    f"that area, not a campus total."
                    + (
                        " Denton CAD property 702406, 2027 preliminary, address 6565 HEADQUARTERS, "
                        "lists these main areas over 100,000 sqft: West Office 1 274,300; West Office 2 "
                        "161,656; West Office 3 161,656; West Office 4 187,352; Specialty Building 352,092; "
                        "East Office 1 274,300; East Office 2 187,352; East Office 3 161,656. Each uses this row. "
                        "https://www.dentoncad.com/property-detail/702406"
                        if dollars == 130
                        else ""
                    )
                ),
                url=PLANO_FEE_PDF,
                source_label="Plano Ordinance 2025-11-4 Exhibit A",
                status="effective 2026-01-02",
                owner="Plano Building Inspections",
            )
        )
    fees.append(
        _fee(
            label="First reinspection fee",
            trade="inspection",
            amount=75,
            note=(
                "Ordinance 2025-11-4 Exhibit A, effective January 2, 2026. "
                "Reinspection fees: first reinspection fee $75. This is not the electrical permit."
            ),
            url=PLANO_FEE_PDF,
            source_label="Plano Ordinance 2025-11-4 Exhibit A",
            status="effective 2026-01-02",
            owner="Plano Building Inspections",
        )
    )
    fees.append(
        _fee(
            label="Electrical permit total",
            trade="electrical",
            amount=None,
            note=(
                "Do not publish a single electrical permit total. Ordinance 2025-11-4 prices each "
                "building by its own floor area. Denton CAD property 702406 at this address is a campus, "
                "not one building. The office main areas over 100,000 sqft use the over-100,000 row. "
                "Smaller buildings on that account use a lower row. Name the building before a total is printed. "
                "confirm-on-schedule. https://www.dentoncad.com/property-detail/702406"
            ),
            url=PLANO_FEE_PDF,
            source_label="Plano Ordinance 2025-11-4 Exhibit A",
            status="confirm-on-schedule",
            owner="Plano Building Inspections",
        )
    )
    fees.append(
        _fee(
            label="Commercial building permit",
            trade="building",
            amount=None,
            note=(
                "Ordinance 2025-11-4 Exhibit A states separate building permit fees are required "
                "for fire, mechanical, electrical, plumbing, and water meters. Valuation follows "
                "Table 1. No permit total is printed. confirm-on-schedule."
            ),
            url=PLANO_FEE_PDF,
            source_label="Plano Ordinance 2025-11-4 Exhibit A",
            status="confirm-on-schedule",
            owner="Plano Building Inspections",
        )
    )
    drivers = [
        _driver(
            "CRITICAL",
            "Commercial electrical inspections are by floor area; $75 is the first reinspection",
            (
                "Ordinance 2025-11-4, effective January 2, 2026, Exhibit A prices commercial "
                "electrical inspections by building floor area ($70 / $90 / $110 / $130) and sets "
                "the first reinspection at $75. Clears when $75 is only the reinspection and the "
                "electrical line is the floor-area row that matches the building. "
                "Desk: Plano Building Inspections."
            ),
            PLANO_FEE_PDF,
            "Plano Ordinance 2025-11-4 Exhibit A",
        ),
        _driver(
            "HIGH",
            "Electronic submittal is only remodel, alteration, or interior finish",
            (
                "The Building Inspections electronic submittal form states it can be used only for "
                "commercial remodel, alteration, or interior finish. All other submittals are hard copy. "
                "Clears when the scope is checked against that sentence before upload. "
                "Desk: Plano Building Inspections."
            ),
            PLANO_APPLY,
            "Plano Building Inspections electronic submittal form",
        ),
    ]
    clocks = [
        _clock(
            "Plano Building Inspections permit intake",
            "Electronic submittal is limited to commercial remodel, alteration, or interior finish. Other scopes are hard copy.",
            "Plano Building Inspections",
            "AHJ",
            PLANO_APPLY,
        ),
        _oncor_clock("6565 HEADQUARTERS DR, PLANO, TX", PLANO_ONCOR),
        _clock(
            "Plano Engineering water and drainage review",
            (
                "Preliminary Drainage and Utility Plan Checklist, September 5, 2025, page 1: "
                "Engineering Department, 1520 K Avenue, Plano, TX 75074, 972.941.7152. "
                "The checklist covers drainage and water/wastewater utility plans. "
                f"The new-commercial coordination sheet sends civil plans to Engineering at 972-941-7152 and the pre-construction meeting to 972-941-7140: {PLANO_COORD}"
            ),
            "Plano Engineering 972.941.7152",
            "WATER",
            PLANO_DRAIN,
        ),
    ]
    punches = [
        _punch(
            "CRITICAL",
            "Call Plano Building Inspections. Use the Ordinance 2025-11-4 floor-area row for the electrical inspection and carry $75 only as the first reinspection.",
            "Plano Building Inspections",
            PLANO_FEE_PDF,
            "Plano Ordinance 2025-11-4 Exhibit A",
            "Do not publish a single electrical permit total.",
        ),
        _punch(
            "HIGH",
            "Call Oncor commercial new service at 888.313.6862. The ESI ID lookup returns 6565 HEADQUARTERS DR, PLANO, TX.",
            "Oncor 888.313.6862",
            PLANO_ONCOR,
            "Oncor ESI ID lookup",
            f"Commercial new-service intake, 888.313.6862, is {ONCOR_INTAKE}",
        ),
        _punch(
            "HIGH",
            "Call Plano Engineering at 972.941.7152 for the drainage and water/wastewater utility plan. Do not send that review to Building Inspections.",
            "Plano Engineering 972.941.7152",
            PLANO_DRAIN,
            "Plano preliminary drainage and utility checklist",
            "Engineering Department, 1520 K Avenue, 972.941.7152. Checklist dated September 5, 2025.",
        ),
    ]
    return _pack(
        ahj_name="City of Plano Building Inspections",
        portal=PLANO_PORTAL,
        fees_url=PLANO_FEE_PDF,
        apply_url=PLANO_APPLY,
        inspections_url="",
        last_verified="2026-01-02",
        drivers=drivers,
        fees=fees,
        clocks=clocks,
        punches=punches,
        sequence=[
            "If the scope is a commercial remodel, alteration, or interior finish, use the electronic submittal form.",
            "Any other submittal is hard copy at Building Inspections.",
        ],
        headline=(
            "HOLD until the electrical line is the Ordinance 2025-11-4 floor-area row "
            "and $75 is carried only as the first reinspection."
        ),
        calls=[
            "Call Plano Building Inspections. Read Ordinance 2025-11-4 Exhibit A with the measured floor area.",
            "Call Oncor commercial new service 888.313.6862. The ESI ID lookup returns 6565 HEADQUARTERS DR.",
            "Call Plano Engineering at 972.941.7152 for drainage and water/wastewater plans.",
        ],
    )


def _austin() -> Dict[str, Any]:
    fees = [
        _fee(
            label="Commercial plan review application processing fee",
            trade="building",
            amount=145.89,
            note=(
                "Page 1. Updated 10/12/2026, effective 10/01/2026. "
                "Commercial Building Plan Review Application Processing Fee $145.89. "
                "This is not the building permit."
            ),
            url=AUSTIN_FEE_PDF,
            source_label="Austin commercial fee schedule, page 1",
            status="effective 2026-10-01",
            owner="Austin Development Services",
        ),
        _fee(
            label="Fire building permit review, all occupancy groups",
            trade="fire",
            amount=250,
            note=(
                "Page 1. Fire Building Permit Review $250. Notation B applies this fee to all "
                "occupancy groups. This is not the building permit."
            ),
            url=AUSTIN_FEE_PDF,
            source_label="Austin commercial fee schedule, page 1",
            status="effective 2026-10-01",
            owner="Austin Development Services",
        ),
        _fee(
            label="Plan review base fee, occupancy A B E F I M R S or U",
            trade="building",
            amount=3204.30,
            note=(
                "Page 2. Initial submittal base fee $3,204.30 for occupancy A, B, E, F, I, M, R, S, or U. "
                "The area bands on that page add a per-square-foot amount. This is the base, not the permit total."
            ),
            url=AUSTIN_FEE_PDF,
            source_label="Austin commercial fee schedule, page 2",
            status="effective 2026-10-01",
            owner="Austin Development Services",
        ),
        _fee(
            label="New construction building base fee",
            trade="building",
            amount=247.77,
            note=(
                "Page 3. Occupancy groups A, B, E, F, H, I, M, S, and U. Building base fee $247.77. "
                "The area bands on that page add a per-square-foot amount. Payable at permit issuance. "
                "Not the permit total."
            ),
            url=AUSTIN_FEE_PDF,
            source_label="Austin commercial fee schedule, page 3",
            status="effective 2026-10-01",
            owner="Austin Development Services",
        ),
        _fee(
            label="New construction electrical base fee",
            trade="electrical",
            amount=339.52,
            note=(
                "Page 3. Same occupancy groups. Electrical base fee $339.52 before the area band. "
                "Not the permit total."
            ),
            url=AUSTIN_FEE_PDF,
            source_label="Austin commercial fee schedule, page 3",
            status="effective 2026-10-01",
            owner="Austin Development Services",
        ),
        _fee(
            label="New construction mechanical base fee",
            trade="mechanical",
            amount=276.16,
            note=(
                "Page 3. Same occupancy groups. Mechanical base fee $276.16 before the area band. "
                "Not the permit total."
            ),
            url=AUSTIN_FEE_PDF,
            source_label="Austin commercial fee schedule, page 3",
            status="effective 2026-10-01",
            owner="Austin Development Services",
        ),
        _fee(
            label="New construction plumbing base fee",
            trade="plumbing",
            amount=378.11,
            note=(
                "Page 3. Same occupancy groups. Plumbing base fee $378.11 before the area band. "
                "Not the permit total."
            ),
            url=AUSTIN_FEE_PDF,
            source_label="Austin commercial fee schedule, page 3",
            status="effective 2026-10-01",
            owner="Austin Development Services",
        ),
        _fee(
            label="New construction energy base fee",
            trade="energy",
            amount=70.98,
            note=(
                "Page 3. Same occupancy groups. Energy base fee $70.98 before the area band. "
                "Not the permit total."
            ),
            url=AUSTIN_FEE_PDF,
            source_label="Austin commercial fee schedule, page 3",
            status="effective 2026-10-01",
            owner="Austin Development Services",
        ),
        _fee(
            label="Reinspection fee, per inspection",
            trade="inspection",
            amount=70.98,
            note=(
                "Page 6. Reinspection fee per inspection $70.98. Notation C charges it for an "
                "additional scheduled inspection. Not the permit."
            ),
            url=AUSTIN_FEE_PDF,
            source_label="Austin commercial fee schedule, page 6",
            status="effective 2026-10-01",
            owner="Austin Development Services",
        ),
        _fee(
            label="Commercial permit total",
            trade="building",
            amount=None,
            note=(
                "Pages 2 and 3 price the permit by occupancy and square footage above the base lines "
                "already transcribed. The city address layer returns no point for 9020 Metric Blvd, so no "
                "building area is applied. confirm-on-schedule. "
                "https://maps.austintexas.gov/arcgis/rest/services/Shared/Property/MapServer/0/query?"
                "where=ADDRESS+%3D+9020+AND+STREET_NAME+%3D+%27METRIC%27&outFields=FULL_STREET_NAME"
                "&returnGeometry=false&f=json"
            ),
            url=AUSTIN_FEE_PDF,
            source_label="Austin commercial fee schedule, pages 2-3",
            status="confirm-on-schedule",
            owner="Austin Development Services",
        ),
    ]
    drivers = [
        _driver(
            "CRITICAL",
            "Application processing is $145.89, not the building permit",
            (
                "Page 1 states the commercial plan review application processing fee is $145.89. "
                "Page 3 states the new-construction building base fee is $247.77 before area, for "
                "occupancy groups A, B, E, F, H, I, M, S, and U. Page 2 states the plan-review base "
                "fee is $3,204.30 before area, for occupancy A, B, E, F, I, M, R, S, or U. "
                "Clears when $145.89 is only the application processing line. "
                "Desk: Austin Development Services commercial plan review."
            ),
            AUSTIN_FEE_PDF,
            "Austin commercial fee schedule, pages 1-3",
        ),
        _driver(
            "HIGH",
            "File commercial plan review, not a residential service-upgrade sheet",
            (
                "9020 Metric Blvd, 78758, is a commercial plan review. The city service-area layer "
                "returns Austin Energy Service Area for this address. Clears when the submittal is "
                "commercial plan review and the Electric Service Planning Application is filed with "
                "Austin Energy. Desk: Austin Development Services commercial plan review."
            ),
            AUSTIN_REVIEW,
            "Austin commercial plan review",
        ),
    ]
    clocks = [
        _clock(
            "Austin Development Services commercial plan review",
            "File in Austin Build + Connect. The application processing fee is separate from the permit.",
            "Austin Development Services",
            "AHJ",
            AUSTIN_APPLY,
        ),
        _clock(
            "Austin Energy electric utility",
            (
                "The city layer Austin Energy Utility Service Area returns SERVICE_AREA Austin Energy "
                "Service Area for the point of 9020 Metric Blvd. The Electric Service Planning Application "
                f"and the Austin Build + Connect intake are on {AUSTIN_ENERGY}. Customer Services on that page is 512-494-9400."
            ),
            "Austin Energy 512-494-9400",
            "UTILITY",
            AUSTIN_AE_QUERY,
        ),
        _clock(
            "Austin Water Utility Development Services",
            (
                "UDS reviews service extension requests and land-use plans for water and wastewater. "
                "The page gives AWUDS@austintexas.gov and appointments at the Permitting and Development Center, "
                "6310 Wilhelmina Delco Drive, Suite 3100. No phone is printed on that page."
            ),
            "Austin Water UDS",
            "WATER",
            AUSTIN_WATER,
        ),
    ]
    punches = [
        _punch(
            "CRITICAL",
            "Call Austin Development Services commercial plan review. Carry $145.89 only as the application processing fee.",
            "Austin Development Services",
            AUSTIN_FEE_PDF,
            "Austin commercial fee schedule, page 1",
            "Page 1 application processing fee is $145.89. The permit total is confirm-on-schedule.",
        ),
        _punch(
            "HIGH",
            "Call Austin Energy Customer Services at 512-494-9400 and file the Electric Service Planning Application. The city layer places this address in the Austin Energy Service Area.",
            "Austin Energy 512-494-9400",
            AUSTIN_AE_QUERY,
            "Austin Energy Utility Service Area layer",
            f"Intake forms and Customer Services 512-494-9400 are on {AUSTIN_ENERGY}",
        ),
        _punch(
            "HIGH",
            "Email Austin Water Utility Development Services at AWUDS@austintexas.gov for the service-extension review.",
            "Austin Water UDS",
            AUSTIN_WATER,
            "Austin Water Utility Development Services",
            "UDS reviews service extension requests and land-use plans. The page prints AWUDS@austintexas.gov.",
        ),
    ]
    return _pack(
        ahj_name="City of Austin Development Services",
        portal=AUSTIN_REVIEW,
        fees_url=AUSTIN_FEE_PDF,
        apply_url=AUSTIN_APPLY,
        inspections_url="",
        last_verified="2026-10-01",
        drivers=drivers,
        fees=fees,
        clocks=clocks,
        punches=punches,
        sequence=[
            "File commercial plan review in Austin Build + Connect.",
            "The application processing fee is paid apart from the permit, which is priced by occupancy and area.",
        ],
        headline=(
            "HOLD until $145.89 is only the application processing fee and the permit "
            "is priced from the occupancy-and-area table above the page 3 bases."
        ),
        calls=[
            "Call Austin Development Services commercial plan review. File in Austin Build + Connect. $145.89 is the application processing fee.",
            "Call Austin Energy Customer Services 512-494-9400. The city layer places 9020 Metric Blvd in the Austin Energy Service Area.",
            "Email Austin Water Utility Development Services at AWUDS@austintexas.gov.",
        ],
    )


def _fort_worth() -> Dict[str, Any]:
    ordinance = "Ordinance 26-28781, adopted September 15, 2026, effective October 1, 2026, Exhibit A."
    fees = [
        _fee(
            label="Plan review deposit, circulation required",
            trade="building",
            amount=291,
            note=(
                ordinance + " Table 1-B item 10, page 14. Plan Review Deposit, those requiring "
                "circulation: $291.00. Not the building-permit total."
            ),
            url=FW_FEE,
            source_label="Fort Worth Ordinance 26-28781, page 14",
            status="effective 2026-10-01",
            owner="Fort Worth Development Services",
        ),
        _fee(
            label="Plan review deposit, no circulation",
            trade="building",
            amount=113,
            note=(
                ordinance + " Table 1-B, page 15. Those without circulation: $113.00. "
                "Not the building-permit total."
            ),
            url=FW_FEE,
            source_label="Fort Worth Ordinance 26-28781, page 15",
            status="effective 2026-10-01",
            owner="Fort Worth Development Services",
        ),
        _fee(
            label="Permit application fee, excluding signs",
            trade="building",
            amount=33.08,
            note=(
                ordinance + " Table 1-B item 1, page 14. Permit Application Fee, applicable to all "
                "permit types, excluding signs: $33.08."
            ),
            url=FW_FEE,
            source_label="Fort Worth Ordinance 26-28781, page 14",
            status="effective 2026-10-01",
            owner="Fort Worth Development Services",
        ),
        _fee(
            label="Technology fee, all applications",
            trade="building",
            amount=16.87,
            note=(
                ordinance + " Table 1-B item 3, page 14. Technology Fee applicable to all "
                "applications and permits: $16.87."
            ),
            url=FW_FEE,
            source_label="Fort Worth Ordinance 26-28781, page 14",
            status="effective 2026-10-01",
            owner="Fort Worth Development Services",
        ),
        _fee(
            label="Table 1-C-1 new construction or addition at 60,404 sq ft",
            trade="building",
            amount=19026.04,
            note=(
                "TAD account 7059418 states gross building area 60,404 and says that figure is rounded. "
                "Site class is Office. Ordinance 26-28781 Table 1-C-1, pages 16-17, use groups A, B, E, H, I, "
                "and M: 8,001.00 for the first 18,000 square feet plus 0.26 for each additional square foot. "
                "60,404 minus 18,000 is 42,404. 42,404 times 0.26 is 11,025.04. "
                "8,001.00 plus 11,025.04 is $19,026.04. This is the new-construction or addition fee for that "
                "area in those use groups, before any third-party reduction. It is not an alteration permit. "
                "https://www.tad.org/property?account=7059418"
            ),
            url=FW_FEE,
            source_label="Fort Worth Ordinance 26-28781, Table 1-C-1, pages 16-17",
            status="effective 2026-10-01",
            owner="Fort Worth Development Services",
        ),
        _fee(
            label="Alteration permit",
            trade="building",
            amount=None,
            note=(
                "Table 1-A prices an alteration from the value of proposed work. The TAD market value is "
                "not that value. confirm-on-schedule."
            ),
            url=FW_FEE,
            source_label="Fort Worth Ordinance 26-28781, Table 1-A",
            status="confirm-on-schedule",
            owner="Fort Worth Development Services",
        ),
    ]
    drivers = [
        _driver(
            "CRITICAL",
            "Plan review deposit is $291 when circulation is required",
            (
            "Table 1-B states the plan review deposit is $291.00 when circulation is required and "
            "$113.00 without circulation. The application fee is $33.08 and the technology fee is "
            "$16.87. None of those lines is the building permit. Table 1-C-1 at the rounded TAD gross "
            "area of 60,404 square feet is $19,026.04 for new construction or an addition in use groups "
            "A, B, E, H, I, or M. Clears when the deposit lines stay on Table 1-B and a new building of "
            "that area uses $19,026.04. Desk: Fort Worth Development Services commercial permitting."
            ),
            FW_FEE,
            "Fort Worth Ordinance 26-28781, Table 1-B",
        ),
        _driver(
            "HIGH",
            "Building permit is issued before a trade permit can be applied for",
            (
                "The commercial permitting page states the building permit must be obtained and issued "
                "before a trade permit can be applied for. Clears when trade permits are scheduled after "
                "building-permit issuance. Desk: Fort Worth Development Services commercial permitting."
            ),
            FW_COMMERCIAL,
            "Fort Worth commercial permitting",
        ),
    ]
    clocks = [
        _clock(
            "Fort Worth Development Services commercial permitting",
            "Apply in Accela. The building permit is issued before a trade permit application.",
            "Fort Worth Development Services",
            "AHJ",
            FW_APPLY,
        ),
        _oncor_clock("13600 HERITAGE PKWY, FORT WORTH, TX", FW_ONCOR),
        _clock(
            "Fort Worth Water Applications",
            (
                "Developer contact page, row for tap fees, impact fees, fire line applications, "
                "meter deposit, and site plan review comments: Water Applications Section, 817-392-8250."
            ),
            "Water Applications 817-392-8250",
            "WATER",
            FW_WATER,
        ),
    ]
    punches = [
        _punch(
            "CRITICAL",
            "Call Fort Worth Development Services commercial permitting. Use the Table 1-B deposit of $291 when circulation is required.",
            "Fort Worth Development Services",
            FW_FEE,
            "Fort Worth Ordinance 26-28781, page 14",
            "Plan review deposit, circulation required, is $291.00. The building permit is confirm-on-schedule.",
        ),
        _punch(
            "HIGH",
            "Call Oncor commercial new service at 888.313.6862. The ESI ID lookup returns 13600 HERITAGE PKWY, FORT WORTH, TX.",
            "Oncor 888.313.6862",
            FW_ONCOR,
            "Oncor ESI ID lookup",
            f"Commercial new-service intake, 888.313.6862, is {ONCOR_INTAKE}",
        ),
        _punch(
            "HIGH",
            "Call Fort Worth Water Applications at 817-392-8250 for tap fees, impact fees, and site plan review.",
            "Water Applications 817-392-8250",
            FW_WATER,
            "Fort Worth water developer contacts",
            "Water Applications Section, 817-392-8250.",
        ),
    ]
    return _pack(
        ahj_name="City of Fort Worth Development Services",
        portal=FW_COMMERCIAL,
        fees_url=FW_FEE,
        apply_url=FW_APPLY,
        inspections_url="",
        last_verified="2026-10-01",
        drivers=drivers,
        fees=fees,
        clocks=clocks,
        punches=punches,
        sequence=[
            "Pay the Table 1-B application lines, then plan review.",
            "The building permit is issued before a trade permit can be applied for.",
        ],
        headline=(
            "HOLD until the Table 1-B deposit is $291 when circulation is required "
            "and the building permit stays on the use-and-area table."
        ),
        calls=[
            "Call Fort Worth Development Services commercial permitting. Table 1-B deposit is $291 when circulation is required.",
            "Call Oncor commercial new service 888.313.6862. The ESI ID lookup returns 13600 HERITAGE PKWY.",
            "Call Water Applications at 817-392-8250 for tap fees, impact fees, and site plan review.",
        ],
    )


def _pack(
    *,
    ahj_name: str,
    portal: str,
    fees_url: str,
    apply_url: str,
    inspections_url: str,
    last_verified: str,
    drivers: List[Dict[str, Any]],
    fees: List[Dict[str, Any]],
    clocks: List[Dict[str, str]],
    punches: List[Dict[str, Any]],
    sequence: List[str],
    headline: str,
    calls: List[str],
) -> Dict[str, Any]:
    return {
        "ahj_name": ahj_name,
        "portal": portal,
        "fees_url": fees_url,
        "apply_url": apply_url,
        "inspections_url": inspections_url,
        "last_verified": last_verified,
        "drivers": drivers,
        "fees": fees,
        "clocks": clocks,
        "punches": punches,
        "sequence": sequence,
        "headline": headline,
        "calls": calls,
    }


_BUILDERS = {
    "dallas": _dallas,
    "plano": _plano,
    "austin": _austin,
    "fort worth": _fort_worth,
}


def apply_ic_buyer_brief(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Replace unsourced beachhead filler with the transcribed city brief."""
    data = analysis
    key = _city_key(data)
    builder = _BUILDERS.get(key)
    if not builder:
        return data
    brief = builder()
    pi = data.get("project_info") if isinstance(data.get("project_info"), dict) else {}

    data["ic_buyer_brief"] = True
    data["buyer_headline"] = brief["headline"]
    data["next_steps"] = list(brief["calls"])
    data["margin_killers"] = list(brief["drivers"])
    data["gotcha_watchlist"] = {"items": []}
    data["punch_list"] = {
        "timeline_summary": "Three calls before the LOI",
        "punch_list": list(brief["punches"]),
        "items": list(brief["punches"]),
    }
    data["fee_card"] = {"fees": list(brief["fees"]), "timeline": "Before LOI call"}
    data["parallel_clocks"] = {"clocks": list(brief["clocks"])}
    data["contingency_band"] = {
        "label": "No contingency percent",
        "pct_low": None,
        "pct_mid": None,
        "pct_high": None,
        "suppress_percent": True,
        "drivers": {},
        "disclaimer": "",
        "verified": False,
    }
    data["regguard_stamp"] = {
        "grade": "HOLD",
        "headline": brief["headline"],
        "drivers": [],
        "plain": brief["headline"],
    }
    data["ahj_card"] = {
        "name": brief["ahj_name"],
        "portal_url": brief["portal"],
        "fees_url": brief["fees_url"],
        "apply_url": brief["apply_url"],
        "inspections_url": brief["inspections_url"],
        "last_verified": brief["last_verified"],
        "notes": "",
    }
    data["inspection_sequence_card"] = {"steps": list(brief["sequence"])}
    data["moratorium_radar"] = {}
    data["power_path"] = {}
    data["power_path_card"] = {}
    data["dc_positioning"] = {}
    data["ultralocal_scout"] = {}
    data["environmental_screening"] = {"risk_level": "", "findings": []}
    data["pro_summary_markdown"] = ""
    data["document_checklist"] = {"items": []}

    local = data.get("local_pack") if isinstance(data.get("local_pack"), dict) else {}
    data["local_pack"] = {
        **local,
        "gotchas": [],
        "fees": list(brief["fees"]),
        "inspection_sequence": list(brief["sequence"]),
        "ahj": data["ahj_card"],
    }
    ahj_block = data.get("ahj") if isinstance(data.get("ahj"), dict) else {}
    if ahj_block:
        ahj_block = dict(ahj_block)
        ahj_block["ahj_fee_table"] = []
        ahj_block["ahj_fee_lines"] = []
        data["ahj"] = ahj_block

    pdf_pack = data.get("pdf_pack") if isinstance(data.get("pdf_pack"), dict) else {}
    data["pdf_pack"] = {
        **pdf_pack,
        "ahj_name": brief["ahj_name"],
        "portal_url": brief["portal"],
        "fees_url": brief["fees_url"],
        "fee_lines": [
            (
                f"{f['label']}: {_usd(f['amount_usd'])}  |  {f['source_url']}"
                if isinstance(f.get("amount_usd"), (int, float))
                else f"{f['label']}: confirm-on-schedule  |  {f['source_url']}"
            )
            for f in brief["fees"]
        ],
        "gotcha_lines": [f"{d['priority']}: {d['title']}" for d in brief["drivers"]],
        "punch_lines": [p["task"] for p in brief["punches"]],
        "clock_lines": [f"{c['owner']}: {c['url'] or 'unconfirmed'}" for c in brief["clocks"]],
        "contingency": data["contingency_band"],
        "radar_headline": "",
        "power_headline": "",
        "inspection_sequence": list(brief["sequence"]),
    }
    # Keep the address the caller sent. The brief is the city record.
    if pi:
        data["project_info"] = pi
    return data


def schedule_usd(amount: float) -> str:
    if float(amount).is_integer():
        return f"${float(amount):,.0f}"
    return f"${float(amount):,.2f}"


def stated_schedule_amount(row: Dict[str, Any]) -> Optional[float]:
    """A dollar the cited schedule states. Homepages and blank rows stay empty."""
    if not isinstance(row, dict) or row.get("verified") is not True:
        return None
    amt = row.get("amount_usd")
    if not isinstance(amt, (int, float)):
        return None
    url = str(row.get("source_url") or "")
    if not url.startswith("http") or "default.aspx" in url.lower():
        return None
    return float(amt)


def _site_blob(analysis: Dict[str, Any]) -> str:
    pi = analysis.get("project_info") if isinstance(analysis.get("project_info"), dict) else {}
    return " ".join(
        str(pi.get(key) or "") for key in ("address", "city", "zip")
    ).lower()


def _desk_city(analysis: Dict[str, Any]) -> str:
    pi = analysis.get("project_info") if isinstance(analysis.get("project_info"), dict) else {}
    city = " ".join(str(pi.get("city") or "").strip().lower().replace(".", "").split())
    if city in ("ft worth", "fort worth"):
        return "fort worth"
    return city


def _blank_note(row: Dict[str, Any], note: str) -> Dict[str, Any]:
    out = dict(row)
    cleaned = note_without_unstated_dollars(note)
    if "confirm-on-schedule" not in cleaned:
        cleaned = f"{cleaned} confirm-on-schedule".strip()
    out["detail"] = cleaned
    out["note"] = cleaned
    out["amount_usd"] = None
    out["verified"] = False
    out["amount_requires_schedule"] = True
    return out


def cited_schedule_fees(analysis: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """
    Fee rows for the Pro desk. The CSV and the City Pack read this same list.
    Address-specific table math stays on the address it was measured for.
    """
    if not isinstance(analysis, dict):
        return None
    city = _desk_city(analysis)
    blob = _site_blob(analysis)
    builders = {
        "dallas": _dallas,
        "plano": _plano,
        "austin": _austin,
        "fort worth": _fort_worth,
    }
    build = builders.get(city)
    if build is None:
        return None
    rows = [dict(row) for row in build().get("fees") or [] if isinstance(row, dict)]
    if city == "dallas" and "stemmons" not in blob:
        rows = [
            _blank_note(
                row,
                "Page 1 prices a new commercial permit from the value of proposed work. "
                "It does not price that permit from floor area or from an appraisal account. "
                "confirm-on-schedule.",
            )
            if "new commercial" in str(row.get("label") or "").lower()
            else row
            for row in rows
        ]
    if city == "plano" and "headquarters" not in blob and "6565" not in blob:
        cleaned = []
        for row in rows:
            note = str(row.get("note") or row.get("detail") or "")
            if "702406" in note or "Denton CAD" in note:
                if stated_schedule_amount(row) == 130:
                    row = dict(row)
                    row["note"] = row["detail"] = (
                        "Ordinance 2025-11-4 Exhibit A, effective January 2, 2026. "
                        "Building (electrical) commercial inspections, calculated by square footage "
                        "of building floor area, Over 100,000 sq ft: $130. "
                        "This is the inspection line for that area, not a campus total."
                    )
                else:
                    row = _blank_note(
                        row,
                        "Do not publish a single electrical permit total. Ordinance 2025-11-4 "
                        "prices each building by its own floor area. Name the building before a "
                        "total is printed. confirm-on-schedule.",
                    )
            cleaned.append(row)
        rows = cleaned
    if city == "austin" and "9020" not in blob and "metric" not in blob:
        rows = [
            _blank_note(
                row,
                "Pages 2 and 3 price the permit by occupancy and square footage above the "
                "base lines already transcribed. No building area is applied on this row. "
                "confirm-on-schedule.",
            )
            if "permit total" in str(row.get("label") or "").lower()
            else row
            for row in rows
        ]
    if city == "fort worth" and "heritage" not in blob and "13600" not in blob:
        rows = [
            row
            for row in rows
            if "60,404" not in str(row.get("label") or "")
            and stated_schedule_amount(row) != 19026.04
        ]
    return rows


def apply_cited_desk_links(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Point the receipt at the cited schedule. Dollar rows stay locked until Pro."""
    if not isinstance(analysis, dict):
        return analysis
    build = {
        "dallas": _dallas,
        "plano": _plano,
        "austin": _austin,
        "fort worth": _fort_worth,
    }.get(_desk_city(analysis))
    if build is None:
        return analysis
    brief = build()
    ahj = dict(analysis.get("ahj_card") or {})
    ahj["portal_url"] = brief.get("portal") or ahj.get("portal_url") or ""
    ahj["fees_url"] = brief.get("fees_url") or ahj.get("fees_url") or ""
    ahj["apply_url"] = brief.get("apply_url") or ahj.get("apply_url") or ""
    analysis["ahj_card"] = ahj
    return analysis


def apply_cited_schedule_fees(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Replace the Pro fee card with the cited schedule. Estimator stays off this list."""
    if not isinstance(analysis, dict):
        return analysis
    try:
        from honesty import fee_dollars_unlocked
    except Exception:
        return analysis
    if not fee_dollars_unlocked(analysis):
        return analysis
    rows = cited_schedule_fees(analysis)
    if not rows:
        return analysis
    out = dict(analysis)
    card = dict(out.get("fee_card") or {})
    card["fees"] = rows
    out["fee_card"] = card
    ahj = dict(out.get("ahj_card") or {})
    fees_url = str(rows[0].get("source_url") or "").strip()
    if fees_url:
        ahj["fees_url"] = fees_url
    out["ahj_card"] = ahj
    stated = {round(stated_schedule_amount(row) or -1, 2) for row in rows}
    punch = dict(out.get("punch_list") or {})
    cleaned_items = []
    for item in punch.get("punch_list") or []:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        cost = row.get("estimated_cost")
        if isinstance(cost, (int, float)) and round(float(cost), 2) not in stated:
            row["estimated_cost"] = None
        task = note_without_unstated_dollars(str(row.get("task") or ""))
        row["task"] = re.sub(r"\(\s*base\s*\)", "", task).strip()
        cleaned_items.append(row)
    if cleaned_items:
        punch["punch_list"] = cleaned_items
        out["punch_list"] = punch
    watch = dict(out.get("gotcha_watchlist") or {})
    gotchas = []
    for item in watch.get("items") or []:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        url = str(row.get("source_url") or "")
        if "default.aspx" in url.lower():
            row["source_url"] = ""
        row["title"] = note_without_unstated_dollars(str(row.get("title") or ""))
        row["detail"] = note_without_unstated_dollars(str(row.get("detail") or ""))
        gotchas.append(row)
    if gotchas:
        watch["items"] = gotchas
        out["gotcha_watchlist"] = watch
    return out
