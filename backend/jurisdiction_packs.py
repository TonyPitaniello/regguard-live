"""
Federal + state diligence packs (static). Local packs stay in city_packs.py.
"""

from __future__ import annotations

from typing import Any, Dict

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
    ],
    "documents": [
        "Flood zone determination (if lender/owner requires)",
        "Any federal permit nexus checklist (if applicable)",
    ],
}


# Thin state packs — start with TX detail; others are honest stubs.
STATE_PACKS: Dict[str, Dict[str, Any]] = {
    "TX": {
        "pack_key": "state:tx",
        "layer": "state",
        "state": "TX",
        "citeable": True,
        "title": "Texas state layer",
        "ahj": {
            "name": "Texas — state overlays (not a city AHJ)",
            "portal_url": "https://www.tdlr.texas.gov/",
            "fees_url": "https://www.tdlr.texas.gov/",
            "notes": "State contractor licensing / TDLR; city AHJ still governs local permits.",
        },
        "items": [
            {
                "id": "tx_tdlr",
                "title": "Confirm TDLR / contractor license path",
                "detail": "Verify trade licensing and any state registration before bid",
                "priority": "HIGH",
                "source_url": "https://www.tdlr.texas.gov/",
                "source_label": "TDLR",
            },
            {
                "id": "tx_sos",
                "title": "Confirm business / SOS filings if needed for entity",
                "detail": "Entity good standing is separate from AHJ trade permit",
                "priority": "LOW",
                "source_url": "https://www.sos.state.tx.us/",
                "source_label": "Texas SOS",
            },
            {
                "id": "tx_tceq",
                "title": "Screen TCEQ environmental triggers for industrial / large sites",
                "detail": "Not every job — confirm when stormwater, air, or industrial waste apply",
                "priority": "MEDIUM",
                "source_url": "https://www.tceq.texas.gov/",
                "source_label": "TCEQ",
            },
        ],
        "documents": [
            "Contractor license / TDLR credentials",
            "Proof of insurance as AHJ requires",
        ],
        "timeline_hint": "State overlays run parallel to city permits — confirm both clocks",
    },
}


def thin_state_pack(state: str) -> Dict[str, Any]:
    """Honest stub for states without a curated pack."""
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
            "notes": "Thin state pack — confirm contractor licensing and state environmental triggers.",
        },
        "items": [
            {
                "id": f"{st.lower()}_license",
                "title": f"Confirm {st} contractor / trade license requirements",
                "detail": "No curated state pack yet — verify with the state licensing board",
                "priority": "HIGH",
                "source_url": None,
                "source_label": "Unverified",
            },
            {
                "id": f"{st.lower()}_env",
                "title": f"Screen {st} environmental triggers for the project type",
                "detail": "Unverified thin state note — confirm with state env agency if industrial/large",
                "priority": "MEDIUM",
                "source_url": None,
                "source_label": "Unverified",
            },
        ],
        "documents": [
            "State contractor license proof",
            "Insurance certificates",
        ],
        "timeline_hint": "Confirm state vs local permit clocks before bid",
    }


def get_state_pack(state: str) -> Dict[str, Any]:
    st = (state or "").strip().upper()
    # Normalize common names
    aliases = {
        "TEXAS": "TX",
        "CALIFORNIA": "CA",
        "NEW YORK": "NY",
        "FLORIDA": "FL",
    }
    st = aliases.get(st, st)
    if len(st) > 2:
        # try first 2 if weird
        st = st[:2]
    pack = STATE_PACKS.get(st)
    if pack:
        out = dict(pack)
        out["citeable"] = True
        return out
    return thin_state_pack(st or "US")
