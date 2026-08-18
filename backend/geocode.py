"""
Geocoding: reverse (lat/lon → U.S. ZIP) via BigDataCloud, and forward (U.S. address / ZIP)
via Google Geocoding for **city / county** resolution on the research path.
"""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import Any, List, Optional, Tuple

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

_RE_ZIP5 = re.compile(r"^(\d{5})")


def _first_us_zip5(postcode: Optional[str]) -> Optional[str]:
    if not postcode:
        return None
    t = str(postcode).strip()
    m = _RE_ZIP5.match(t)
    if m:
        return m.group(1)
    digits = re.sub(r"\D", "", t)
    return digits[:5] if len(digits) >= 5 else None


def _fetch_bigdata_client(lat: float, lon: float) -> dict[str, Any]:
    q = urllib.parse.urlencode(
        {
            "latitude": str(lat),
            "longitude": str(lon),
            "localityLanguage": "en",
        }
    )
    url = f"https://api.bigdatacloud.net/data/reverse-geocode-client?{q}"
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "RegGuard/1.0"},
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        if resp.status != 200:
            raise ValueError("geocode_http")
        return json.load(resp)


@lru_cache(maxsize=4096)
def lookup_us_zip_for_coordinates(lat: float, lon: float) -> str:
    """
    Return a 5-digit U.S. ZIP for the given WGS-84 coordinates.

    ``lat`` and ``lon`` must be pre-rounded (e.g. 5 decimals) so the cache
    key is stable. Raises ValueError with a user-facing message on failure.
    """
    data = _fetch_bigdata_client(lat, lon)
    code = (data.get("countryCode") or "").strip()
    if code and code != "US":
        raise ValueError(
            "This tool only auto-fills U.S. ZIP codes. That location is outside "
            "the United States — enter a ZIP on your own."
        )
    z = _first_us_zip5(str(data.get("postcode") or "").strip() or None)
    if not z:
        raise ValueError(
            "We could not resolve a 5-digit U.S. ZIP for this position. You can type "
            "your ZIP in the field above."
        )
    return z


def us_zip_from_lat_lon(lat: float, lon: float) -> str:
    """
    Public entry: round coordinates, then return cached 5-digit ZIP.
    Rounding (~1.1m at equator) groups nearby GPS samples into one cache key.
    """
    lat_r = round(float(lat), 5)
    lon_r = round(float(lon), 5)
    try:
        return lookup_us_zip_for_coordinates(lat_r, lon_r)
    except ValueError:
        raise
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ValueError(
            "Network error while looking up your ZIP. Try again or type it in."
        ) from e
    except Exception as e:  # noqa: BLE001 — surface as 400, do not crash the app
        raise ValueError("Could not look up a ZIP for this area. Type your ZIP manually.") from e


def require_google_maps_key() -> str:
    """Server-side key for Google Geocoding (city / county from formatted address or ZIP)."""
    key = (os.environ.get("GOOGLE_MAPS_API_KEY") or "").strip()
    if not key:
        raise ValueError(
            "GOOGLE_MAPS_API_KEY is missing. Set it in .env so addresses can be resolved to city and county."
        )
    return key


def _google_geocode_get(payload: dict[str, Any]) -> dict[str, Any]:
    """Server-side Geocoding Web Service (no HTTP Referer — use an unrestricted/API-key server credential)."""
    q = urllib.parse.urlencode(payload, quote_via=urllib.parse.quote)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?{q}"
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "RegGuard/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.status != 200:
                raise ValueError("Google Geocoding HTTP error.")
            return json.load(resp)
    except urllib.error.HTTPError as e:
        raise ValueError(f"Google Geocoding request failed: {e.code}") from e
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
        raise ValueError("Could not reach Google Geocoding. Try again.") from e


def _denied_hint(extra: str) -> str:
    if "REQUEST_DENIED" in extra.upper():
        return (
            " Browser keys restricted to Websites often block REST Geocoding. "
            "Use GOOGLE_MAPS_API_KEY in backend .env without HTTP referrer restriction "
            "(or restrict by IP only) and enable \"Geocoding API\" on the GCP project."
        )
    return ""


def google_reverse_geocode_us_latlng(lat: float, lon: float) -> Tuple[str, str, str]:
    """
    Reverse geocode WGS‑84 coords to formatted U.S. address + ZIP + locality (Geocoding API).
    """
    key = require_google_maps_key()
    lat_f = round(float(lat), 7)
    lon_f = round(float(lon), 7)
    payload = _google_geocode_get(
        {"latlng": f"{lat_f},{lon_f}", "key": key},
    )
    status = (payload.get("status") or "").strip()
    if status != "OK":
        msg = str(payload.get("error_message") or status or "UNKNOWN").strip()
        denied = _denied_hint(msg + " " + status)
        raise ValueError(
            f"Google Geocoding error: {msg}.{denied}" if denied else f"Google Geocoding error: {msg}",
        )

    results = payload.get("results") or []
    if not results:
        raise ValueError("Reverse geocode returned no addresses for this pin.")

    for top in results:
        components = top.get("address_components")
        if not isinstance(components, list):
            continue
        is_us = any(
            "country" in set(c.get("types") or [])
            and ((c.get("short_name") or "").upper() == "US")
            for c in components
        )
        if not is_us:
            continue
        formatted = str(top.get("formatted_address") or "").strip()
        postcode = ""
        for c in components:
            types = set(c.get("types") or [])
            if "postal_code" in types:
                postcode = str((c.get("short_name") or c.get("long_name") or "")).strip()
                break
        z = _first_us_zip5(postcode or None) or ""
        if len(z) < 5 and formatted:
            m = re.search(r"\b(\d{5})(?:-\d{4})?\b", formatted)
            if m:
                z = m.group(1)
        city_locality = ""
        locality = ""
        subloc = ""
        for c in components:
            types = set(c.get("types") or [])
            if "locality" in types:
                locality = str((c.get("long_name") or c.get("short_name") or "")).strip()
            if "sublocality" in types or "sublocality_level_1" in types:
                subloc = str((c.get("long_name") or c.get("short_name") or "")).strip()
        city_locality = (locality or subloc or "").strip()
        if formatted and len(z) == 5:
            return formatted, z, city_locality

    raise ValueError(
        "This location is outside the United States or has no postal code — pick an address manually."
    )


def google_geocode_us_address(
    address: str,
) -> Tuple[List[dict[str, Any]], str, Optional[float], Optional[float]]:
    """
    Forward geocode a U.S. postal address string (e.g. Places formatted_address).

    Returns ``(address_components, formatted_address, latitude, longitude)``.
    """
    raw = (address or "").strip()
    if not raw:
        raise ValueError("Address is required.")
    key = require_google_maps_key()
    payload = _google_geocode_get(
        {"address": raw, "components": "country:US", "key": key},
    )
    status = (payload.get("status") or "").strip()
    if status != "OK":
        msg = str(payload.get("error_message") or status or "UNKNOWN").strip()
        denied = _denied_hint(msg + " " + status)
        raise ValueError(
            f"Google Geocoding error: {msg}.{denied}" if denied else f"Google Geocoding error: {msg}",
        )

    results = payload.get("results") or []
    if not results:
        raise ValueError("Could not resolve that address. Try another selection.")

    top = results[0]
    components = top.get("address_components")
    if not isinstance(components, list):
        raise ValueError("Invalid Geocoding response (no address_components).")

    is_us = any(
        "country" in set(c.get("types") or []) and (c.get("short_name") or "").upper() == "US"
        for c in components
    )
    if not is_us:
        raise ValueError("Only U.S. addresses are supported.")

    formatted = str(top.get("formatted_address") or raw)
    loc = (top.get("geometry") or {}).get("location") or {}
    lat = loc.get("lat")
    lng = loc.get("lng")
    lat_f = float(lat) if isinstance(lat, (int, float)) else None
    lng_f = float(lng) if isinstance(lng, (int, float)) else None
    return components, formatted, lat_f, lng_f


def google_geocode_us_zip(
    zip5: str,
) -> Tuple[List[dict[str, Any]], str, Optional[float], Optional[float]]:
    """Geocode a 5-digit U.S. ZIP (centroid / area) for approximate city / county / lat/lng."""
    z = "".join(ch for ch in (zip5 or "") if ch.isdigit())[:5]
    if len(z) != 5:
        raise ValueError("A 5-digit U.S. ZIP is required for ZIP geocoding.")
    key = require_google_maps_key()
    payload = _google_geocode_get(
        {"components": f"country:US|postal_code:{z}", "key": key},
    )
    status = (payload.get("status") or "").strip()
    if status != "OK":
        msg = str(payload.get("error_message") or status or "UNKNOWN").strip()
        denied = _denied_hint(msg + " " + status)
        raise ValueError(
            f"Google Geocoding error: {msg}.{denied}" if denied else f"Google Geocoding error: {msg}",
        )

    results = payload.get("results") or []
    if not results:
        raise ValueError("Could not geocode that ZIP code.")

    top = results[0]
    components = top.get("address_components")
    if not isinstance(components, list):
        raise ValueError("Invalid Geocoding response (no address_components).")

    formatted = str(top.get("formatted_address") or f"ZIP {z}")
    loc = (top.get("geometry") or {}).get("location") or {}
    lat = loc.get("lat")
    lng = loc.get("lng")
    lat_f = float(lat) if isinstance(lat, (int, float)) else None
    lng_f = float(lng) if isinstance(lng, (int, float)) else None
    return components, formatted, lat_f, lng_f


def is_null_island(lat: Optional[float], lng: Optional[float]) -> bool:
    """True when coords are missing or Null Island (0,0) — do not run parcel GIS."""
    try:
        if lat is None or lng is None:
            return True
        return abs(float(lat)) < 1e-4 and abs(float(lng)) < 1e-4
    except (TypeError, ValueError):
        return True
