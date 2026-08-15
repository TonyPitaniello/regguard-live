"""
Federal + state diligence packs (static). Local packs stay in city_packs.py /
metro_portal_seeds.py.
"""

from __future__ import annotations

from typing import Any, Dict


def _state_item(
    *,
    id: str,
    title: str,
    detail: str,
    priority: str,
    source_url: str,
    source_label: str,
) -> Dict[str, Any]:
    return {
        "id": id,
        "title": title,
        "detail": detail,
        "priority": priority,
        "source_url": source_url,
        "source_label": source_label,
    }


def _make_state_pack(
    *,
    state: str,
    title: str,
    license_name: str,
    license_url: str,
    license_label: str,
    sos_url: str,
    sos_label: str,
    env_name: str,
    env_url: str,
    env_label: str,
    portal_notes: str,
) -> Dict[str, Any]:
    st = state.upper()
    return {
        "pack_key": f"state:{st.lower()}",
        "layer": "state",
        "state": st,
        "citeable": True,
        "title": title,
        "ahj": {
            "name": f"{st} — state overlays (not a city AHJ)",
            "portal_url": license_url,
            "fees_url": license_url,
            "notes": portal_notes,
        },
        "items": [
            _state_item(
                id=f"{st.lower()}_license",
                title=f"Confirm {license_name}",
                detail="Verify trade licensing and any state registration before bid",
                priority="HIGH",
                source_url=license_url,
                source_label=license_label,
            ),
            _state_item(
                id=f"{st.lower()}_sos",
                title="Confirm business / SOS filings if needed for entity",
                detail="Entity good standing is separate from AHJ trade permit",
                priority="LOW",
                source_url=sos_url,
                source_label=sos_label,
            ),
            _state_item(
                id=f"{st.lower()}_env",
                title=f"Screen {env_name} triggers for industrial / large sites",
                detail="Not every job — confirm when stormwater, air, or industrial waste apply",
                priority="MEDIUM",
                source_url=env_url,
                source_label=env_label,
            ),
        ],
        "documents": [
            "Contractor / trade license credentials",
            "Proof of insurance as AHJ requires",
        ],
        "timeline_hint": "State overlays run parallel to city permits — confirm both clocks",
    }


FEDERAL_PACK: Dict[str, Any] = {
    "pack_key": "federal",
    "layer": "federal",
    "citeable": True,
    "title": "Federal diligence (all US ZIPs)",
    "items": [
        {
            "id": "fema_flood",
            "title": "Check FEMA flood hazard (Flood Map Service Center)",
            "detail": "Confirm SFHA / flood zone for the site before bid contingency",
            "priority": "HIGH",
            "source_url": "https://msc.fema.gov/portal/home",
            "source_label": "FEMA MSC",
        },
        {
            "id": "epa_nepa",
            "title": "Screen federal environmental / NEPA triggers if federal nexus",
            "detail": "Only when federal funding, permits, or land are in play — confirm scope",
            "priority": "MEDIUM",
            "source_url": "https://www.epa.gov/nepa",
            "source_label": "EPA NEPA",
        },
        {
            "id": "osha",
            "title": "OSHA construction / electrical safety baseline",
            "detail": "Jobsite safety is federal floor — not a substitute for AHJ electrical rules",
            "priority": "MEDIUM",
            "source_url": "https://www.osha.gov/construction",
            "source_label": "OSHA Construction",
        },
        {
            "id": "ada_aba",
            "title": "Screen ADA / accessibility path of travel if public-facing work",
            "detail": "Federal civil-rights baseline — confirm with owner/architect when applicable",
            "priority": "MEDIUM",
            "source_url": "https://www.ada.gov/",
            "source_label": "ADA.gov",
        },
        {
            "id": "epa_npdes",
            "title": "Screen EPA construction stormwater (NPDES/CGP) if disturbing land",
            "detail": "Federal floor for eligible sites — state/local may run the permit",
            "priority": "MEDIUM",
            "source_url": "https://www.epa.gov/npdes/stormwater-discharges-construction-activities",
            "source_label": "EPA NPDES Construction",
        },
    ],
    "documents": [
        "Flood zone determination (if lender/owner requires)",
        "Any federal permit nexus checklist (if applicable)",
    ],
}


# Curated state packs (TX + top demand states). Others use thin_state_pack (card only).
STATE_PACKS: Dict[str, Dict[str, Any]] = {
    "TX": _make_state_pack(
        state="TX",
        title="Texas state layer",
        license_name="TDLR / contractor license path",
        license_url="https://www.tdlr.texas.gov/",
        license_label="TDLR",
        sos_url="https://www.sos.state.tx.us/",
        sos_label="Texas SOS",
        env_name="TCEQ environmental",
        env_url="https://www.tceq.texas.gov/",
        env_label="TCEQ",
        portal_notes="State contractor licensing / TDLR; city AHJ still governs local permits.",
    ),
    "CA": _make_state_pack(
        state="CA",
        title="California state layer",
        license_name="CSLB contractor license path",
        license_url="https://www.cslb.ca.gov/",
        license_label="CSLB",
        sos_url="https://www.sos.ca.gov/",
        sos_label="California SOS",
        env_name="CalEPA / water board",
        env_url="https://calepa.ca.gov/",
        env_label="CalEPA",
        portal_notes="CSLB licensing is state; city/county AHJ still governs local permits.",
    ),
    "FL": _make_state_pack(
        state="FL",
        title="Florida state layer",
        license_name="DBPR / contractor license path",
        license_url="https://www.myfloridalicense.com/",
        license_label="FL DBPR",
        sos_url="https://dos.fl.gov/",
        sos_label="Florida DOS",
        env_name="FDEP environmental",
        env_url="https://floridadep.gov/",
        env_label="FDEP",
        portal_notes="DBPR licensing is state; local AHJ still governs building permits.",
    ),
    "NY": _make_state_pack(
        state="NY",
        title="New York state layer",
        license_name="NY DOS / trade license path",
        license_url="https://dos.ny.gov/",
        license_label="NY DOS",
        sos_url="https://dos.ny.gov/corporation-and-business-entity",
        sos_label="NY DOS Corporations",
        env_name="NYS DEC environmental",
        env_url="https://www.dec.ny.gov/",
        env_label="NYS DEC",
        portal_notes="State licensing overlays; NYC and other AHJs still govern local permits.",
    ),
    "WA": _make_state_pack(
        state="WA",
        title="Washington state layer",
        license_name="L&I contractor registration path",
        license_url="https://lni.wa.gov/",
        license_label="WA L&I",
        sos_url="https://www.sos.wa.gov/",
        sos_label="Washington SOS",
        env_name="Ecology environmental",
        env_url="https://ecology.wa.gov/",
        env_label="WA Ecology",
        portal_notes="L&I contractor registration is state; city/county AHJ still governs permits.",
    ),
    "AZ": _make_state_pack(
        state="AZ",
        title="Arizona state layer",
        license_name="ROC contractor license path",
        license_url="https://roc.az.gov/",
        license_label="AZ ROC",
        sos_url="https://azsos.gov/",
        sos_label="Arizona SOS",
        env_name="ADEQ environmental",
        env_url="https://www.azdeq.gov/",
        env_label="ADEQ",
        portal_notes="ROC licensing is state; local AHJ still governs building permits.",
    ),
    "CO": _make_state_pack(
        state="CO",
        title="Colorado state layer",
        license_name="DORA / trade license path",
        license_url="https://dpo.colorado.gov/",
        license_label="CO DORA/DPO",
        sos_url="https://www.sos.state.co.us/",
        sos_label="Colorado SOS",
        env_name="CDPHE environmental",
        env_url="https://cdphe.colorado.gov/",
        env_label="CDPHE",
        portal_notes="State licensing overlays; local AHJ still governs building permits.",
    ),
    "GA": _make_state_pack(
        state="GA",
        title="Georgia state layer",
        license_name="GA SOS / contractor license path",
        license_url="https://sos.ga.gov/",
        license_label="Georgia SOS",
        sos_url="https://sos.ga.gov/",
        sos_label="Georgia SOS",
        env_name="EPD environmental",
        env_url="https://epd.georgia.gov/",
        env_label="GA EPD",
        portal_notes="State licensing overlays; local AHJ still governs building permits.",
    ),
    "NC": _make_state_pack(
        state="NC",
        title="North Carolina state layer",
        license_name="NCLBGC / licensing board path",
        license_url="https://www.nclbgc.org/",
        license_label="NCLBGC",
        sos_url="https://www.sosnc.gov/",
        sos_label="North Carolina SOS",
        env_name="DEQ environmental",
        env_url="https://www.deq.nc.gov/",
        env_label="NC DEQ",
        portal_notes="State licensing overlays; local AHJ still governs building permits.",
    ),
    "IL": _make_state_pack(
        state="IL",
        title="Illinois state layer",
        license_name="IDFPR license path",
        license_url="https://idfpr.illinois.gov/",
        license_label="IDFPR",
        sos_url="https://www.ilsos.gov/",
        sos_label="Illinois SOS",
        env_name="Illinois EPA environmental",
        env_url="https://epa.illinois.gov/",
        env_label="Illinois EPA",
        portal_notes="State licensing overlays; Chicago/local AHJ still governs building permits.",
    ),
    "OH": _make_state_pack(
        state="OH",
        title="Ohio state layer",
        license_name="Ohio Industrial Compliance / license path",
        license_url="https://com.ohio.gov/divisions-and-programs/industrial-compliance",
        license_label="Ohio COM/IC",
        sos_url="https://www.ohiosos.gov/",
        sos_label="Ohio SOS",
        env_name="Ohio EPA environmental",
        env_url="https://epa.ohio.gov/",
        env_label="Ohio EPA",
        portal_notes="State licensing overlays; local AHJ still governs building permits.",
    ),
}


def thin_state_pack(state: str) -> Dict[str, Any]:
    """
    Honest stub for states without a curated pack.

    No punch items here — null-URL fillers dilute citeable ratios.
    Coverage lives on the state_card + coverage_note only.
    """
    st = (state or "").strip().upper() or "US"
    return {
        "pack_key": f"state:{st.lower() or 'unknown'}",
        "layer": "state",
        "state": st,
        "citeable": False,
        "title": f"{st} state layer (thin)",
        "ahj": {
            "name": f"{st} state agencies (confirm locally)",
            "portal_url": "",
            "fees_url": "",
            "notes": (
                "No curated state pack yet — confirm contractor licensing and "
                "state environmental triggers before bid. Federal layer still applies."
            ),
        },
        "items": [],
        "documents": [
            "State contractor license proof",
            "Insurance certificates",
        ],
        "timeline_hint": "Confirm state vs local permit clocks before bid",
    }


_STATE_ALIASES = {
    "TEXAS": "TX",
    "CALIFORNIA": "CA",
    "NEW YORK": "NY",
    "FLORIDA": "FL",
    "WASHINGTON": "WA",
    "ARIZONA": "AZ",
    "COLORADO": "CO",
    "GEORGIA": "GA",
    "NORTH CAROLINA": "NC",
    "ILLINOIS": "IL",
    "OHIO": "OH",
}


def get_state_pack(state: str) -> Dict[str, Any]:
    st = (state or "").strip().upper()
    st = _STATE_ALIASES.get(st, st)
    if len(st) > 2:
        st = st[:2]
    pack = STATE_PACKS.get(st)
    if pack:
        out = dict(pack)
        out["citeable"] = True
        return out
    return thin_state_pack(st or "US")
