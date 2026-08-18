"""
Community friction signals — planning aid, not a protest prediction.

Cheap stack: adjacency heuristics + beachhead notes + official portal links.
No social listening. Always Unverified unless a citeable agenda/news URL is attached.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# Airport / sensitive adjacency ZIPs (TX beachhead examples)
_AIRPORT_ZIPS = {
    "75261",  # DFW
    "75235",  # Love Field vicinity
    "78719",  # Austin-Bergstrom
    "78101",  # SAT area
}

_METRO_DC_FRICTION_NOTES = {
    "dallas": "DFW has seen organized pushback on large-load / data-center siting in some suburbs — check city council and planning agendas.",
    "plano": "North Texas cities often route large projects through planning commission — confirm hearing calendar.",
    "austin": "Austin-area large loads frequently face public comment on water, power, and land use.",
    "richardson": "Confirm whether site is Richardson or Plano AHJ before treating community process as settled.",
}


def _project_is_dc(analysis: Dict[str, Any]) -> bool:
    pi = analysis.get("project_info") or {}
    t = str(pi.get("type") or "").lower().replace(" ", "_").replace("-", "_")
    return t in ("data_center", "datacenter", "dc", "colocation", "colo", "ai_crypto_compute")


def build_community_friction(analysis: Dict[str, Any]) -> Dict[str, Any]:
    pi = analysis.get("project_info") or {}
    city = str(pi.get("city") or "").strip()
    state = str(pi.get("state") or "").strip()
    zip_code = "".join(c for c in str(pi.get("zip") or "") if c.isdigit())[:5]
    is_dc = _project_is_dc(analysis)

    signals: List[Dict[str, Any]] = []
    score = 0  # 0–12 heuristic

    # Adjacency: airport
    if zip_code in _AIRPORT_ZIPS:
        signals.append(
            {
                "id": "airport_adjacency",
                "label": "Airport / airside adjacency",
                "level": 3,
                "detail": (
                    f"ZIP {zip_code} is airport-adjacent. Expect extra land-use, "
                    "height, and stakeholder scrutiny — confirm with AHJ/airport authority."
                ),
                "verified": False,
                "source_url": None,
            }
        )
        score += 3
    else:
        signals.append(
            {
                "id": "airport_adjacency",
                "label": "Airport adjacency",
                "level": 0,
                "detail": "No curated airport-ZIP flag for this postal code.",
                "verified": False,
                "source_url": None,
            }
        )

    # Project-type hearing heat
    if is_dc:
        signals.append(
            {
                "id": "project_type_heat",
                "label": "Large-load / data-center hearing heat",
                "level": 2,
                "detail": (
                    "Data-center and large-load projects often trigger planning hearings "
                    "and public comment. Check the AHJ agenda before bid week."
                ),
                "verified": False,
                "source_url": (analysis.get("ahj_card") or {}).get("portal_url") or None,
            }
        )
        score += 2
    else:
        signals.append(
            {
                "id": "project_type_heat",
                "label": "Project-type hearing heat",
                "level": 1,
                "detail": "Standard commercial hearing risk — confirm if CUP/zoning change is required.",
                "verified": False,
                "source_url": None,
            }
        )
        score += 1

    # Metro pattern note
    city_l = city.lower()
    metro_note = None
    for key, note in _METRO_DC_FRICTION_NOTES.items():
        if key in city_l:
            metro_note = note
            break
    if metro_note and is_dc:
        signals.append(
            {
                "id": "metro_pattern",
                "label": "Metro pattern (not this parcel)",
                "level": 2,
                "detail": metro_note,
                "verified": False,
                "source_url": None,
            }
        )
        score += 2

    # AHJ identity conflict raises process friction
    identity = analysis.get("ahj_identity") or {}
    if identity.get("conflict"):
        signals.append(
            {
                "id": "ahj_identity_conflict",
                "label": "AHJ city / ZIP conflict",
                "level": 3,
                "detail": str(identity.get("note") or "Typed city does not match ZIP catalog AHJ."),
                "verified": True,
                "source_url": None,
            }
        )
        score += 3

    # EJ placeholder — link only, no fake percentile without API
    signals.append(
        {
            "id": "ej_screen",
            "label": "EPA EJScreen (run at pin)",
            "level": 1 if is_dc else 0,
            "detail": (
                "Open EJScreen at the site pin for cumulative burden context. "
                "Not a protest forecast."
            ),
            "verified": False,
            "source_url": "https://ejscreen.epa.gov/mapper/",
        }
    )
    if is_dc:
        score += 1

    score = max(0, min(12, score))
    if score >= 8:
        band = "Elevated"
    elif score >= 4:
        band = "Moderate"
    else:
        band = "Lower"

    return {
        "title": "Community friction signals",
        "headline": f"{band} community-friction index (heuristic)",
        "score": score,
        "score_max": 12,
        "band": band,
        "signals": signals,
        "verified": False,
        "disclaimer": (
            "Planning aid only — signals, not a prediction that protests will occur. "
            "Confirm hearings on the official AHJ agenda and local counsel before bid."
        ),
        "city": city,
        "state": state,
        "zip": zip_code,
    }
