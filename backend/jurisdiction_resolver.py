"""
ZIP / city / state → federal + state + local jurisdiction packs.

Every US ZIP gets federal + state (+ thin local if no curated city pack).
Does not live-scrape municipalities.
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from city_packs import generic_thin_pack, resolve_city_pack
from jurisdiction_packs import FEDERAL_PACK, get_state_pack
from metro_portal_seeds import resolve_metro_portal_pack

logger = logging.getLogger(__name__)

_DATA = Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=1)
def _zip3_to_state() -> Dict[str, str]:
    path = _DATA / "zip3_to_state.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("zip3_to_state load failed: %s", e)
        return {}


@lru_cache(maxsize=1)
def _zcta_seed() -> Dict[str, Dict[str, str]]:
    """National seed (includes TX) with city/county/state per ZIP."""
    out: Dict[str, Dict[str, str]] = {}
    for name in ("national_zcta_seed.json", "tx_zcta.json"):
        path = _DATA / name
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                out.update(data)
        except Exception as e:
            logger.warning("%s load failed: %s", name, e)
    return out


def normalize_zip(zip_code: str = "") -> str:
    z = "".join(c for c in (zip_code or "") if c.isdigit())
    return z[:5] if len(z) >= 5 else z


def state_from_zip(zip_code: str = "") -> str:
    z = normalize_zip(zip_code)
    if len(z) < 3:
        return ""
    return (_zip3_to_state().get(z[:3]) or "").upper()


def place_from_zip(zip_code: str = "") -> Dict[str, str]:
    """Return {city, county, state} from seed; state always from zip3 if possible."""
    z = normalize_zip(zip_code)
    row = dict(_zcta_seed().get(z) or {})
    st = (row.get("state") or state_from_zip(z) or "").upper()
    if st:
        row["state"] = st
    if z and "zip" not in row:
        row["zip"] = z
    return row


def _is_placeholder_locality(value: str = "") -> bool:
    v = (value or "").strip().lower()
    return (not v) or v in {
        "unknown",
        "n/a",
        "na",
        "none",
        "null",
        "us",
        "usa",
        "united states",
    }


def _normalize_state(state: str = "") -> str:
    s = (state or "").strip().upper()
    if _is_placeholder_locality(s):
        return ""
    aliases = {
        "TEXAS": "TX",
        "CALIFORNIA": "CA",
        "NEW YORK": "NY",
        "FLORIDA": "FL",
        "WASHINGTON": "WA",
        "COLORADO": "CO",
        "ARIZONA": "AZ",
        "ILLINOIS": "IL",
        "GEORGIA": "GA",
        "NORTH CAROLINA": "NC",
        "OHIO": "OH",
        "OREGON": "OR",
        "NEVADA": "NV",
        "UTAH": "UT",
        "NEW MEXICO": "NM",
        "TENNESSEE": "TN",
        "LOUISIANA": "LA",
        "OKLAHOMA": "OK",
        "MASSACHUSETTS": "MA",
        "PENNSYLVANIA": "PA",
        "MARYLAND": "MD",
        "VIRGINIA": "VA",
        "HAWAII": "HI",
        "ALASKA": "AK",
        "WYOMING": "WY",
        "MICHIGAN": "MI",
        "MINNESOTA": "MN",
        "WISCONSIN": "WI",
        "MISSOURI": "MO",
        "INDIANA": "IN",
        "DISTRICT OF COLUMBIA": "DC",
    }
    if s in aliases:
        return aliases[s]
    if len(s) == 2:
        return s
    return s[:2] if len(s) > 2 else s


def resolve_jurisdiction(
    zip_code: str = "",
    city: str = "",
    state: str = "",
) -> Dict[str, Any]:
    """
    Hierarchical resolve:
      federal (always) + state pack + local city pack or thin local.

    Prefer user-provided city/state over ZIP3/seed when present (avoids
    ZIP3 mis-state overriding a typed locality). Treat geocode placeholders
    like Unknown / US as missing so ZIP seed can fill.
    """
    z = normalize_zip(zip_code)
    place = place_from_zip(z) if z else {}
    user_city = "" if _is_placeholder_locality(city) else (city or "").strip()
    user_state = _normalize_state(state)

    city_out = user_city or (place.get("city") or "").strip()
    # User state wins; zip seed / zip3 only fill gaps
    state_out = user_state or _normalize_state(place.get("state") or "") or state_from_zip(z)
    zip3_state = state_from_zip(z)
    state_mismatch = bool(
        user_state and zip3_state and user_state != zip3_state
    )
    if state_mismatch:
        logger.info(
            "ZIP3 state %s overridden by user state %s for zip=%s",
            zip3_state,
            user_state,
            z,
        )

    local = resolve_city_pack(city_out, state_out, z)
    citeable_local = bool(local and local.get("citeable"))
    portal_only = False
    if not local:
        local = resolve_metro_portal_pack(city_out, state_out, z)
        if local:
            portal_only = True
    if not local:
        local = generic_thin_pack(city_out, state_out)
        # If seed knows a city name, surface it on thin pack
        if city_out and not (local.get("city") or "").strip():
            local = dict(local)
            local["city"] = city_out
            local["state"] = state_out
            local["ahj"] = dict(local.get("ahj") or {})
            label = f"{city_out}, {state_out}".strip(", ")
            local["ahj"]["name"] = f"{label} AHJ (confirm locally)"

    federal = dict(FEDERAL_PACK)
    state_pack = get_state_pack(state_out)

    if citeable_local:
        coverage_note = "Citeable local pack + federal/state layers."
    elif portal_only:
        coverage_note = (
            "Metro portal seed + federal/state layers — confirm fees on the official AHJ schedule "
            "(not a full curated fee/gotcha pack)."
        )
    elif state_pack.get("citeable"):
        coverage_note = (
            "Federal + curated state layer. Local AHJ fees/gotchas not curated for this city — "
            "confirm on the official portal when available."
        )
    else:
        coverage_note = (
            "Federal diligence always. State/local packs not curated for this place — "
            "confirm licensing and AHJ requirements before bid."
        )

    return {
        "zip": z,
        "city": city_out,
        "state": state_out,
        "county": place.get("county") or "",
        "federal": federal,
        "state_pack": state_pack,
        "local": local,
        "citeable_local": citeable_local,
        "portal_only_local": portal_only,
        "resolved_from_zip_seed": bool(place.get("city")) and not user_city,
        "user_state_preferred": bool(user_state),
        "zip3_state_mismatch": state_mismatch,
        "coverage_note": coverage_note,
    }


def jurisdiction_punch_items(
    resolved: Dict[str, Any],
    *,
    federal_cap: int = 2,
    state_cap: int = 2,
) -> list:
    """Federal + state items as punch rows (capped to reduce soft-lock noise)."""
    try:
        federal_cap = max(0, min(4, int(os.getenv("JURISDICTION_FEDERAL_PUNCH_CAP") or federal_cap)))
    except ValueError:
        federal_cap = 2
    try:
        state_cap = max(0, min(4, int(os.getenv("JURISDICTION_STATE_PUNCH_CAP") or state_cap)))
    except ValueError:
        state_cap = 2

    items = []
    for layer_key, label, cap in (
        ("federal", "Federal", federal_cap),
        ("state_pack", "State", state_cap),
    ):
        pack = resolved.get(layer_key) or {}
        citeable = bool(pack.get("citeable"))
        for g in (pack.get("items") or [])[:cap]:
            if not isinstance(g, dict):
                continue
            # Skip null-URL fillers — they dilute citeable punch ratios.
            if not (g.get("source_url") or "").strip():
                continue
            _ = citeable  # pack may still be citeable as a layer; rows are portal links
            items.append(
                {
                    "priority": str(g.get("priority") or "MEDIUM").upper(),
                    "task": f"[{label}] {g.get('title') or 'Check'}",
                    "responsible_party": "Estimator",
                    "timeline": "Before bid",
                    "estimated_cost": 0,
                    "notes": str(g.get("detail") or ""),
                    # Portal / catalog URL — LINK, not parcel-verified SOURCE
                    "verified": False,
                    "citation_tier": "link",
                    "cost_verified": False,
                    "source_url": g.get("source_url"),
                    "source_label": g.get("source_label") or "Portal link",
                    "jurisdiction_layer": pack.get("layer") or layer_key,
                }
            )
    return items


def attach_jurisdiction_cards(
    analysis: Dict[str, Any],
    resolved: Dict[str, Any],
) -> Dict[str, Any]:
    """Attach federal/state cards + prepend punch items; fill city/state from ZIP if empty."""
    if not isinstance(analysis, dict):
        return analysis

    pi = dict(analysis.get("project_info") or {})
    if resolved.get("city") and not pi.get("city"):
        pi["city"] = resolved["city"]
    if resolved.get("state") and not pi.get("state"):
        pi["state"] = resolved["state"]
    if resolved.get("zip") and not pi.get("zip"):
        pi["zip"] = resolved["zip"]
    analysis["project_info"] = pi

    analysis["federal_card"] = {
        "title": (resolved.get("federal") or {}).get("title") or "Federal",
        "items": (resolved.get("federal") or {}).get("items") or [],
        "citeable": True,
    }
    sp = resolved.get("state_pack") or {}
    analysis["state_card"] = {
        "title": sp.get("title") or "State",
        "state": sp.get("state"),
        "items": sp.get("items") or [],
        "citeable": bool(sp.get("citeable")),
        "pack_key": sp.get("pack_key"),
    }
    analysis["jurisdiction"] = {
        "zip": resolved.get("zip"),
        "city": resolved.get("city"),
        "state": resolved.get("state"),
        "county": resolved.get("county"),
        "citeable_local": resolved.get("citeable_local"),
        "portal_only_local": resolved.get("portal_only_local"),
        "local_pack_key": (resolved.get("local") or {}).get("pack_key"),
        "resolved_from_zip_seed": resolved.get("resolved_from_zip_seed"),
        "coverage_note": resolved.get("coverage_note"),
        "zip3_state_mismatch": resolved.get("zip3_state_mismatch"),
    }

    extra = jurisdiction_punch_items(resolved)
    punch = analysis.get("punch_list") or {}
    items = list(punch.get("punch_list") or [])
    # Prepend federal/state once (avoid dup on re-enrich)
    existing_tasks = {str(i.get("task") or "") for i in items if isinstance(i, dict)}
    for row in reversed(extra):
        if row["task"] not in existing_tasks:
            items.insert(0, row)
            existing_tasks.add(row["task"])
    punch["punch_list"] = items
    analysis["punch_list"] = punch

    # Merge state docs into document_checklist if thin
    docs_card = analysis.get("document_checklist") or {}
    doc_items = list(docs_card.get("items") or [])
    seen_docs = {
        str(d.get("task") if isinstance(d, dict) else d)[:80] for d in doc_items
    }
    for d in list((resolved.get("federal") or {}).get("documents") or []) + list(
        sp.get("documents") or []
    ):
        key = str(d)[:80]
        if key not in seen_docs:
            doc_items.append({"task": d, "done": False})
            seen_docs.add(key)
    if doc_items:
        docs_card["items"] = doc_items
        analysis["document_checklist"] = docs_card

    return analysis
