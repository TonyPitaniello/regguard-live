"""
Resolve a U.S. postal address (Geocoding API or Place Details) into city vs county
(unincorporated) heuristic for steering Universal Scout toward the right building department.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from geocode import google_geocode_us_address, google_geocode_us_zip, require_google_maps_key

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


@dataclass(frozen=True)
class JurisdictionProfile:
    """Enough structure to steer Firecrawl queries + show in the memo."""

    mode: str  # "city" | "county"
    zip5: str
    street_line: str
    city: str
    county: str
    state_short: str
    state_long: str
    formatted_address: str
    label: str  # one-line human summary for logs / UI
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    def to_scout_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "zip": self.zip5,
            "street_line": self.street_line,
            "city": self.city,
            "county": self.county,
            "state": self.state_short,
            "state_long": self.state_long,
            "formatted_address": self.formatted_address,
            "label": self.label,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


def _first_long(components: List[Dict[str, Any]], *types: str) -> str:
    want = set(types)
    for c in components:
        tset = set(c.get("types") or [])
        if want & tset:
            name = (c.get("long_name") or "").strip()
            if name:
                return name
    return ""


def _first_short(components: List[Dict[str, Any]], *types: str) -> str:
    want = set(types)
    for c in components:
        tset = set(c.get("types") or [])
        if want & tset:
            name = (c.get("short_name") or "").strip()
            if name:
                return name
    return ""


def _county_base_name(admin2: str) -> str:
    t = (admin2 or "").strip()
    low = t.lower()
    if low.endswith(" county"):
        return t[: -len(" county")].strip() or t
    return t


def build_profile_from_components(
    components: List[Dict[str, Any]],
    formatted_address: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> JurisdictionProfile:
    street_num = _first_long(components, "street_number")
    route = _first_long(components, "route")
    street_line = f"{street_num} {route}".strip()
    locality = _first_long(components, "locality")
    subloc = _first_long(components, "sublocality", "sublocality_level_1")
    neighborhood = _first_long(components, "neighborhood")
    admin2 = _first_long(components, "administrative_area_level_2")
    state_long = _first_long(components, "administrative_area_level_1")
    state_short = _first_short(components, "administrative_area_level_1")
    postal = _first_long(components, "postal_code")

    z = "".join(ch for ch in postal if ch.isdigit())[:5]
    if len(z) != 5:
        raise ValueError("Place did not include a 5-digit U.S. postal code.")

    county_full = admin2 or ""
    county_base = _county_base_name(county_full)

    # Incorporated vs unincorporated heuristic:
    # If Google returns a city-style locality (or common sublocality fallback), steer to city BD.
    # Otherwise treat as county-governed (typical unincorporated / county-AHJ pattern).
    city_like = (locality or subloc or "").strip()
    if not city_like and neighborhood and not locality:
        city_like = neighborhood.strip()

    # **City of Dallas** (Dallas County, 752xx — e.g. Stemmons / IH-35E) is often mis-labeled
    # **Lake Dallas** (Denton County). Anchor Dallas proper ZIPs to the **Dallas** municipal AHJ.
    if (
        state_short == "TX"
        and city_like.strip().lower() == "lake dallas"
        and z.startswith("752")
    ):
        city_like = "Dallas"

    if city_like:
        mode = "city"
        city = city_like
        label = f"Incorporated / municipal — {city}, {state_short} {z} (city building department)"
    else:
        mode = "county"
        city = ""
        cname = county_base or county_full or "County"
        label = f"Unincorporated / county-AHJ — {cname} County, {state_short} {z} (county building department)"

    return JurisdictionProfile(
        mode=mode,
        zip5=z,
        street_line=street_line,
        city=city,
        county=county_base or county_full,
        state_short=state_short or state_long[:2] if state_long else "",
        state_long=state_long,
        formatted_address=(formatted_address or "").strip(),
        label=label,
        latitude=latitude,
        longitude=longitude,
    )


def fetch_place_profile(place_id: str) -> JurisdictionProfile:
    """Call Google Place Details for address_components + classification."""
    pid = (place_id or "").strip()
    if not pid:
        raise ValueError("place_id is required.")
    key = require_google_maps_key()
    fields = "address_components,formatted_address"
    q = urllib.parse.urlencode(
        {"place_id": pid, "fields": fields, "key": key},
        quote_via=urllib.parse.quote,
    )
    url = f"https://maps.googleapis.com/maps/api/place/details/json?{q}"
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "RegGuard/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.status != 200:
                raise ValueError("Google Places HTTP error.")
            payload = json.load(resp)
    except urllib.error.HTTPError as e:
        raise ValueError(f"Google Places request failed: {e.code}") from e
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        raise ValueError("Could not reach Google Places. Try again or use ZIP-only research.") from e

    status = (payload.get("status") or "").strip()
    if status != "OK":
        msg = payload.get("error_message") or status or "UNKNOWN"
        raise ValueError(f"Google Places error: {msg}")

    result = payload.get("result") or {}
    components = result.get("address_components")
    if not isinstance(components, list):
        raise ValueError("Invalid Places response (no address_components).")

    formatted = str(result.get("formatted_address") or "")
    return build_profile_from_components(components, formatted)


def geocode_profile_from_address(address: str) -> JurisdictionProfile:
    """Resolve city / county / ZIP / lat/lng via ``geocode.google_geocode_us_address``."""
    components, formatted, lat, lng = google_geocode_us_address(address)
    return build_profile_from_components(components, formatted, lat, lng)


def geocode_profile_from_zip(zip5: str) -> JurisdictionProfile:
    """Approximate city / county / lat/lng for a U.S. ZIP via ``geocode.google_geocode_us_zip``."""
    components, formatted, lat, lng = google_geocode_us_zip(zip5)
    return build_profile_from_components(components, formatted, lat, lng)
