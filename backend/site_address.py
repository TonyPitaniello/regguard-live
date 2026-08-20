"""Normalize site address strings so UI/PDF don't repeat city/state/ZIP."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple


def _norm_token(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def normalize_street_address(
    address: str = "",
    *,
    city: str = "",
    state: str = "",
    zip_code: str = "",
) -> str:
    """
    Return a street (or full-line) address without duplicated city/state/ZIP tails.

    Handles common client bugs like:
    \"7351 Meeting St, Bradenton, FL 34201, Bradenton, FL, 34201\"
    """
    raw = (address or "").strip()
    if not raw:
        return ""

    city_n = _norm_token(city)
    state_n = _norm_token(state)
    zip5 = "".join(c for c in (zip_code or "") if c.isdigit())[:5]

    # Split on commas and drop trailing place fragments that repeat city/state/zip
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if len(parts) <= 1:
        return raw

    kept = []
    seen_city = False
    seen_state = False
    seen_zip = False
    for i, part in enumerate(parts):
        pn = _norm_token(part)
        digits = "".join(c for c in part if c.isdigit())
        # Standalone ZIP
        if len(digits) >= 5 and _norm_token(re.sub(r"\d", "", part)) == "":
            if seen_zip or (zip5 and digits[:5] == zip5):
                continue
            if i > 0:
                seen_zip = True
                # Prefer attaching ZIP to previous place part instead of keeping bare
                continue
        # City-only fragment
        if city_n and pn == city_n:
            if seen_city:
                continue
            seen_city = True
            kept.append(part)
            continue
        # "Bradenton FL" / "FL 34201" / "Bradenton FL 34201"
        tokens = part.replace(",", " ").split()
        token_norms = [_norm_token(t) for t in tokens]
        if state_n and state_n in token_norms and len(tokens) <= 4:
            if seen_state and (not city_n or city_n in token_norms or seen_city):
                continue
            if city_n and city_n in token_norms and seen_city and seen_state:
                continue
            seen_state = True
            if city_n and city_n in token_norms:
                seen_city = True
            if zip5 and zip5 in digits:
                seen_zip = True
            kept.append(part)
            continue
        if zip5 and zip5 in digits and city_n and city_n in pn and seen_city:
            continue
        kept.append(part)

    cleaned = ", ".join(kept).strip(" ,")
    # Collapse "City, City" style leftovers
    cleaned = re.sub(r"\s*,\s*,+", ", ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,")
    return cleaned or raw


def compose_site_line(
    address: str = "",
    *,
    city: str = "",
    state: str = "",
    zip_code: str = "",
) -> str:
    """Single display line: street (+ place if not already embedded)."""
    street = normalize_street_address(address, city=city, state=state, zip_code=zip_code)
    city = (city or "").strip()
    state = (state or "").strip()
    zip5 = "".join(c for c in (zip_code or "") if c.isdigit())[:5]
    place = ", ".join(x for x in [city, f"{state} {zip5}".strip()] if x).strip(" ,")
    if not street:
        return place
    if not place:
        return street
    sn = _norm_token(street)
    if city and _norm_token(city) in sn and (not zip5 or zip5 in street):
        return street
    return f"{street}, {place}"


def clean_project_info_address(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Mutate analysis project_info.address to a non-duplicated street string."""
    if not isinstance(analysis, dict):
        return analysis
    pi = dict(analysis.get("project_info") or {})
    city = str(pi.get("city") or "")
    state = str(pi.get("state") or "")
    zip_code = str(pi.get("zip") or "")
    street = normalize_street_address(
        str(pi.get("address") or ""),
        city=city,
        state=state,
        zip_code=zip_code,
    )
    if street:
        pi["address"] = street
    analysis["project_info"] = pi
    return analysis


def display_address_parts(analysis: Dict[str, Any]) -> Tuple[str, str]:
    """Return (street_or_line, city_state_zip) for UI headers."""
    pi = (analysis or {}).get("project_info") or {}
    street = normalize_street_address(
        str(pi.get("address") or ""),
        city=str(pi.get("city") or ""),
        state=str(pi.get("state") or ""),
        zip_code=str(pi.get("zip") or ""),
    )
    place = ", ".join(
        x
        for x in [
            str(pi.get("city") or "").strip(),
            f"{str(pi.get('state') or '').strip()} {str(pi.get('zip') or '').strip()}".strip(),
        ]
        if x
    )
    return street, place
