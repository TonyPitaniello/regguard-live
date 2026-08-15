"""
ZIP / city / state → federal + state + local jurisdiction packs.

Every US ZIP gets federal + state (+ thin local if no curated city pack).
Does not live-scrape municipalities.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from city_packs import generic_thin_pack, resolve_city_pack
from jurisdiction_packs import FEDERAL_PACK, get_state_pack

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


def resolve_jurisdiction(
    zip_code: str = "",
    city: str = "",
    state: str = "",
) -> Dict[str, Any]:
    """
    Hierarchical resolve:
      federal (always) + state pack + local city pack or thin local.
    """
    z = normalize_zip(zip_code)
    place = place_from_zip(z) if z else {}
    city_out = (city or place.get("city") or "").strip()
    state_out = (state or place.get("state") or state_from_zip(z) or "").strip().upper()
    if state_out.lower() in ("texas",):
        state_out = "TX"

    local = resolve_city_pack(city_out, state_out, z)
    citeable_local = bool(local and local.get("citeable"))
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

    return {
        "zip": z,
        "city": city_out,
        "state": state_out,
        "county": place.get("county") or "",
        "federal": federal,
        "state_pack": state_pack,
        "local": local,
        "citeable_local": citeable_local,
        "resolved_from_zip_seed": bool(place.get("city")),
    }


def jurisdiction_punch_items(resolved: Dict[str, Any]) -> list:
    """Federal + state items as punch rows (prepended by callers)."""
    items = []
    for layer_key, label in (("federal", "Federal"), ("state_pack", "State")):
        pack = resolved.get(layer_key) or {}
        citeable = bool(pack.get("citeable"))
        for g in (pack.get("items") or [])[:4]:
            if not isinstance(g, dict):
                continue
            items.append(
                {
                    "priority": str(g.get("priority") or "MEDIUM").upper(),
                    "task": f"[{label}] {g.get('title') or 'Check'}",
                    "responsible_party": "Estimator",
                    "timeline": "Before bid",
                    "estimated_cost": 0,
                    "notes": str(g.get("detail") or ""),
                    "verified": bool(g.get("source_url")) and citeable,
                    "cost_verified": False,
                    "source_url": g.get("source_url"),
                    "source_label": g.get("source_label")
                    or ("Source" if citeable else "Unverified"),
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
        "local_pack_key": (resolved.get("local") or {}).get("pack_key"),
        "resolved_from_zip_seed": resolved.get("resolved_from_zip_seed"),
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
