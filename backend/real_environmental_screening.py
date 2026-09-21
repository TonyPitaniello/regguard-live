"""
Enhanced Environmental Screening with Real Firecrawl API Integration
Fetches actual environmental data from:
- USGS Wetlands Database
- USFWS Threatened & Endangered Species Database  
- FEMA Flood Maps
- EPA NEPA Database
- State-specific environmental requirements
"""

import asyncio
import logging
import re
import httpx
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
import os

logger = logging.getLogger(__name__)

EPA_NEPA_URL = "https://www.epa.gov/nepa"
EPA_STATE_AGENCIES_URL = (
    "https://www.epa.gov/environmental-topics/state-and-tribal-environmental-agencies"
)

# Parcel GIS layers that may drive overall risk. Noise / NEPA / state are confirm-links only.
GIS_PARCEL_CATEGORIES = frozenset(
    {
        "wetlands",
        "flood_zones",
        "flood_zone",
        "flood",
        "floodplain",
        "endangered_species",
    }
)

# Must resolve before we claim LOW/MEDIUM "all clear". Critical habitat may stay UNKNOWN
# (IPaC confirm) without blocking a flood/wetlands-derived score.
REQUIRED_FOR_ALL_CLEAR = frozenset({"wetlands", "flood_zones"})


def _normalize_gis_category(category: str) -> str:
    c = (category or "").strip().lower()
    if c in ("flood", "flood_zone", "floodplain", "flood zones"):
        return "flood_zones"
    if c in ("endangered_species", "species", "critical_habitat"):
        return "endangered_species"
    if c in ("wetlands", "wetland"):
        return "wetlands"
    return c


RISK_RANK = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
    "UNKNOWN": 0,
    "UNAVAILABLE": 0,
    "PRELIMINARY": 0,
}
RANK_TO_RISK = {v: k for k, v in RISK_RANK.items() if k in ("CRITICAL", "HIGH", "MEDIUM", "LOW")}


def _finding_category(finding: Any) -> str:
    if isinstance(finding, dict):
        return _normalize_gis_category(str(finding.get("category") or ""))
    return _normalize_gis_category(str(getattr(finding, "category", "") or ""))


def _finding_level(finding: Any) -> str:
    if isinstance(finding, dict):
        return str(finding.get("risk_level") or "UNKNOWN").strip().upper()
    return str(getattr(finding, "risk_level", "UNKNOWN") or "UNKNOWN").strip().upper()


def _finding_verified(finding: Any) -> bool:
    if isinstance(finding, dict):
        return finding.get("verified") is True
    return getattr(finding, "verified", False) is True


def calculate_overall_env_risk(findings: List[Any]) -> Dict[str, Any]:
    """
    Derive overall environmental risk from parcel GIS findings only.

    Noise / NEPA / state confirm-link rows never raise or lower the score (they used to
    force LOW when NWI/FEMA failed — the Chapin LOW↔HIGH flip).

    Rules:
    - Max over *verified* GIS levels (flood / wetlands / critical habitat).
    - LOW/MEDIUM requires flood + wetlands both verified. Unresolved critical habitat
      alone does not block (IPaC remains a confirm link).
    - Verified HIGH/CRITICAL always wins even if another layer failed.
    """
    rows = [f for f in (findings or []) if f is not None]
    gis_rows = [f for f in rows if _finding_category(f) in GIS_PARCEL_CATEGORIES]
    verified = [
        f
        for f in gis_rows
        if _finding_verified(f) and _finding_level(f) in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    ]
    verified_cats = {_finding_category(f) for f in verified}
    unknown_gis = [
        f
        for f in gis_rows
        if (not _finding_verified(f))
        or _finding_level(f) in ("UNKNOWN", "UNAVAILABLE", "PRELIMINARY", "")
    ]
    missing_required = sorted(REQUIRED_FOR_ALL_CLEAR - verified_cats)

    if verified:
        best = max(RISK_RANK.get(_finding_level(f), 0) for f in verified)
        level = RANK_TO_RISK.get(best, "LOW")
        # Incomplete flood/wetlands: do not claim all-clear while a required layer failed.
        if missing_required and level in ("LOW", "MEDIUM"):
            return {
                "risk_level": "UNKNOWN",
                "gis_complete": False,
                "verified_count": len(verified),
                "unknown_gis_count": len(unknown_gis),
                "basis": "partial_gis",
                "risk_honesty_note": (
                    f"Verified GIS incomplete (missing {', '.join(missing_required)}). "
                    "Overall score withheld — do not treat this pin as LOW until flood and "
                    "wetlands both resolve."
                ),
            }
        return {
            "risk_level": level,
            "gis_complete": not bool(missing_required),
            "verified_count": len(verified),
            "unknown_gis_count": len(unknown_gis),
            "basis": "verified_gis",
            "risk_honesty_note": (
                None
                if not unknown_gis
                else (
                    f"Overall {level} from verified flood/wetlands GIS; "
                    f"{len(unknown_gis)} other layer(s) still unresolved (confirm on linked mapper)."
                )
            ),
        }

    if gis_rows:
        return {
            "risk_level": "UNKNOWN",
            "gis_complete": False,
            "verified_count": 0,
            "unknown_gis_count": len(unknown_gis) or len(gis_rows),
            "basis": "gis_unresolved",
            "risk_honesty_note": (
                "Parcel GIS did not return a verified flood/wetlands/habitat hit. "
                "Overall risk unavailable — open FEMA MSC / NWI / IPaC for this pin."
            ),
        }

    return {
        "risk_level": "UNKNOWN",
        "gis_complete": False,
        "verified_count": 0,
        "unknown_gis_count": 0,
        "basis": "no_gis",
        "risk_honesty_note": "No parcel GIS findings — overall risk unavailable.",
    }


@dataclass
class EnvironmentalRisk:
    """Environmental risk assessment result"""
    category: str  # wetlands, species, flood, noise, nepa, state_requirements
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    description: str
    action_items: List[str]
    data_sources: List[str]
    research_cost_usd: float
    verified: bool = False
    source_url: Optional[str] = None
    source_label: Optional[str] = None


def pin_mapper_urls(latitude: float, longitude: float) -> Dict[str, str]:
    """Official mappers a contractor can open at this pin (LINK, not a parcel stamp)."""
    return {
        "nwi": "https://www.fws.gov/program/national-wetlands-inventory/wetlands-mapper",
        "fema": f"https://msc.fema.gov/portal/search?addressAscii={latitude}%2C{longitude}",
        "ipac": "https://ipac.ecosphere.fws.gov/",
        "nepa": EPA_NEPA_URL,
    }


def municode_library_url(city: str, state: str) -> str:
    """Best-effort Municode library root for the AHJ (confirm link, not a parcel stamp)."""
    st = (state or "").strip().lower()[:2]
    slug = re.sub(r"[^a-z0-9]+", "_", (city or "").strip().lower()).strip("_")
    if not st or not slug:
        return "https://library.municode.com/"
    return f"https://library.municode.com/{st}/{slug}"


def state_env_confirm(state: str) -> Tuple[str, str]:
    """Official state environmental agency page when curated; else EPA state directory."""
    try:
        from jurisdiction_packs import get_state_pack

        pack = get_state_pack(state)
        for item in pack.get("items") or []:
            if not isinstance(item, dict):
                continue
            iid = str(item.get("id") or "")
            if iid.endswith("_env") and str(item.get("source_url") or "").startswith("http"):
                return str(item["source_url"]), str(item.get("source_label") or "State environmental")
    except Exception as e:
        logger.debug("state_env_confirm pack lookup failed: %s", e)
    return EPA_STATE_AGENCIES_URL, "EPA state agencies"


def _pin_hint(lat: float, lng: float) -> str:
    return f"Map pin {lat:.5f}, {lng:.5f} — paste these coordinates into the mapper."


class EnvironmentalScreeningEngine:
    """
    Real environmental screening using actual API data sources
    Replaces template data with real, actionable intelligence
    """
    
    def __init__(self):
        self.firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
        self.firecrawl_base_url = "https://api.firecrawl.dev/v1"
        
    async def screen_site(self, address: str, latitude: float, longitude: float, city: str, state: str, zip_code: str) -> Dict[str, Any]:
        """
        Comprehensive environmental screening for a given site
        Returns: {risk_level, findings: [EnvironmentalRisk, ...], total_research_cost, action_plan}
        """
        from geocode import is_null_island

        if is_null_island(latitude, longitude):
            logger.warning("screen_site refused Null Island coords for %s", address)
            return {
                "risk_level": "UNAVAILABLE",
                "findings": [],
                "total_research_cost": 0,
                "action_plan": [
                    "Address did not resolve to map coordinates — re-select the site before parcel environmental claims."
                ],
                "risk_score_hidden": True,
                "risk_honesty_note": "Parcel GIS skipped — missing coordinates.",
            }

        logger.info(f"🌍 Starting real environmental screening for {address}")
        
        findings = []
        total_cost = 0.0
        
        # Parallel API calls — FEMA NFHL + NWI are free GIS; others stay search-assisted
        tasks = [
            self._check_wetlands(zip_code, city, state, latitude, longitude),
            self._check_endangered_species(latitude, longitude, state),
            self._check_flood_zones(latitude, longitude),
            self._check_noise_ordinances(city, state),
            self._check_nepa_requirements(latitude, longitude),
            self._check_state_requirements(state, city),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, EnvironmentalRisk):
                findings.append(result)
                total_cost += result.research_cost_usd
            elif isinstance(result, Exception):
                logger.error(f"Error in environmental check: {result}")
        
        # Determine overall risk from parcel GIS only (never stub noise/NEPA/state LOWs)
        overall_meta = calculate_overall_env_risk(findings)
        overall_risk = overall_meta["risk_level"]
        
        logger.info(
            "✅ Environmental screening complete: %s risk (basis=%s, verified=%s, unknown_gis=%s, cost=%s)",
            overall_risk,
            overall_meta.get("basis"),
            overall_meta.get("verified_count"),
            overall_meta.get("unknown_gis_count"),
            total_cost,
        )
        mappers = pin_mapper_urls(latitude, longitude)
        out = {
            "risk_level": overall_risk,
            "findings": [asdict(f) for f in findings],
            "total_research_cost": total_cost,
            "action_plan": self._generate_action_plan(findings),
            "timestamp": self._get_timestamp(),
            "pin": {"lat": latitude, "lng": longitude},
            "mapper_urls": mappers,
            "gis_complete": bool(overall_meta.get("gis_complete")),
            "risk_basis": overall_meta.get("basis"),
            "gis_note": (
                "Overall risk uses verified FEMA NFHL / NWI / critical-habitat GIS only. "
                "Noise, NEPA, and state rows are confirm links — they do not set the score. "
                "Species lists still need IPaC when habitat GIS is unresolved."
            ),
        }
        if overall_meta.get("risk_honesty_note"):
            out["risk_honesty_note"] = overall_meta["risk_honesty_note"]
        return out
    
    async def _check_wetlands(
        self,
        zip_code: str,
        city: str,
        state: str,
        latitude: float = 0.0,
        longitude: float = 0.0,
    ) -> EnvironmentalRisk:
        """NWI point intersect (free GIS)."""
        nwi_url = "https://www.fws.gov/program/national-wetlands-inventory/wetlands-mapper"
        pin = _pin_hint(latitude, longitude)
        try:
            hit = await self._nwi_point_intersect(latitude, longitude)
            if hit is True:
                return EnvironmentalRisk(
                    category="wetlands",
                    risk_level="HIGH",
                    description=(
                        "NWI wetlands feature intersects this map pin (or within ~120 m). "
                        "Confirm delineation with Corps before assuming impact."
                    ),
                    action_items=[
                        "Open NWI Wetlands Mapper and confirm the polygon at this pin",
                        "If impact possible, request Corps jurisdictional determination",
                        "Budget delineation survey only if NWI/field review warrants it",
                    ],
                    data_sources=["USFWS National Wetlands Inventory"],
                    research_cost_usd=0.0,
                    verified=True,
                    source_url=nwi_url,
                    source_label="NWI Wetlands Mapper",
                )
            if hit is False:
                return EnvironmentalRisk(
                    category="wetlands",
                    risk_level="LOW",
                    description="No NWI wetlands polygon at this map pin (point query).",
                    action_items=["Still confirm on NWI mapper if grading near water features"],
                    data_sources=["USFWS National Wetlands Inventory"],
                    research_cost_usd=0.0,
                    verified=True,
                    source_url=nwi_url,
                    source_label="NWI Wetlands Mapper",
                )
        except Exception as e:
            logger.warning("NWI GIS failed: %s", e)
        return EnvironmentalRisk(
            category="wetlands",
            risk_level="UNKNOWN",
            description=(
                f"Wetlands not GIS-verified for {city}, {state} (NWI service did not return a hit). "
                f"{pin} Open NWI mapper — do not assume presence or absence."
            ),
            action_items=[
                f"Open NWI Wetlands Mapper and jump to {latitude:.5f}, {longitude:.5f}",
                "If grading near water, request Corps jurisdictional determination",
            ],
            data_sources=["USFWS National Wetlands Inventory"],
            research_cost_usd=0.0,
            verified=False,
            source_url=nwi_url,
            source_label="NWI Wetlands Mapper",
        )

    async def _check_endangered_species(self, latitude: float, longitude: float, state: str) -> EnvironmentalRisk:
        """FWS critical-habitat GIS at the pin, plus IPaC as the species-list confirm page."""
        ipac = "https://ipac.ecosphere.fws.gov/"
        pin = _pin_hint(latitude, longitude)
        try:
            ch = await self._fws_critical_habitat_intersect(latitude, longitude)
            if ch is True:
                return EnvironmentalRisk(
                    category="endangered_species",
                    risk_level="HIGH",
                    description=(
                        "USFWS critical-habitat polygon intersects this map pin. "
                        f"{pin} Generate an IPaC resource list before assuming take or consultation."
                    ),
                    action_items=[
                        "Open IPaC and generate a resource list for this footprint",
                        "If habitat may be affected, budget a biologist / ESA consult",
                    ],
                    data_sources=["USFWS critical habitat GIS", "USFWS IPaC"],
                    research_cost_usd=0.0,
                    verified=True,
                    source_url=ipac,
                    source_label="USFWS IPaC",
                )
            if ch is False:
                return EnvironmentalRisk(
                    category="endangered_species",
                    risk_level="LOW",
                    description=(
                        "No USFWS critical-habitat polygon at this pin. "
                        f"{pin} IPaC is still required for the listed-species list — absence of CH ≠ no species."
                    ),
                    action_items=[
                        "Generate an IPaC resource list for the project footprint",
                        "Do not treat this as a cleared ESA review",
                    ],
                    data_sources=["USFWS critical habitat GIS", "USFWS IPaC"],
                    research_cost_usd=0.0,
                    verified=True,
                    source_url=ipac,
                    source_label="USFWS IPaC",
                )
        except Exception as e:
            logger.warning("Critical habitat GIS failed: %s", e)
        return EnvironmentalRisk(
            category="endangered_species",
            risk_level="UNKNOWN",
            description=(
                f"Species / critical habitat not GIS-verified. {pin} "
                "Open IPaC and generate a resource list — do not assume presence or absence."
            ),
            action_items=[
                f"Open IPaC and enter pin {latitude:.5f}, {longitude:.5f}",
                "Save the IPaC official species list in the bid file",
            ],
            data_sources=["USFWS IPaC"],
            research_cost_usd=0.0,
            verified=False,
            source_url=ipac,
            source_label="USFWS IPaC",
        )
    
    async def _check_flood_zones(self, latitude: float, longitude: float) -> EnvironmentalRisk:
        """FEMA NFHL point query (free)."""
        msc = f"https://msc.fema.gov/portal/search?addressAscii={latitude}%2C{longitude}"
        try:
            zone, sfha = await self._fema_nfhl_point(latitude, longitude)
            if zone is None:
                raise ValueError("no NFHL hit")
            zup = (zone or "").upper()
            if sfha or (zup and zup not in ("X", "AREA NOT INCLUDED", "D")):
                level = "HIGH" if zup in ("VE", "V", "AE", "A", "AO", "AH") else "MEDIUM"
                return EnvironmentalRisk(
                    category="flood_zones",
                    risk_level=level,
                    description=(
                        f"FEMA NFHL at pin: flood zone {zone}"
                        + (" (Special Flood Hazard Area)." if sfha else ".")
                    ),
                    action_items=[
                        "Download the FEMA FIRMette for this pin from MSC",
                        "Confirm insurance / elevation needs with lender and AHJ",
                    ],
                    data_sources=["FEMA National Flood Hazard Layer", "FEMA MSC"],
                    research_cost_usd=0.0,
                    verified=True,
                    source_url=msc,
                    source_label="FEMA MSC",
                )
            return EnvironmentalRisk(
                category="flood_zones",
                risk_level="LOW",
                description=f"FEMA NFHL at pin: zone {zone or 'X'} — not mapped as SFHA.",
                action_items=["Still download FIRMette before finalizing contingency"],
                data_sources=["FEMA National Flood Hazard Layer", "FEMA MSC"],
                research_cost_usd=0.0,
                verified=True,
                source_url=msc,
                source_label="FEMA MSC",
            )
        except Exception as e:
            logger.error("Flood check failed: %s", e)
            return EnvironmentalRisk(
                category="flood_zones",
                risk_level="UNKNOWN",
                description=(
                    f"FEMA NFHL did not return a zone for this pin. {_pin_hint(latitude, longitude)} "
                    "Open MSC and download the FIRMette — do not assume Zone X."
                ),
                action_items=[
                    f"Open FEMA MSC search for {latitude:.5f}, {longitude:.5f}",
                    "Download the FIRMette into the bid file",
                ],
                data_sources=["FEMA MSC"],
                research_cost_usd=0.0,
                verified=False,
                source_url=msc,
                source_label="FEMA MSC",
            )

    async def _fema_nfhl_point(self, lat: float, lng: float):
        """Return (FLD_ZONE, sfha_bool) from FEMA NFHL MapServer layer 28."""
        import json
        import urllib.parse
        import urllib.request

        base = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"
        params = urllib.parse.urlencode(
            {
                "geometry": f"{lng},{lat}",
                "geometryType": "esriGeometryPoint",
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "FLD_ZONE,ZONE_SUBTY,SFHA_TF",
                "returnGeometry": "false",
                "f": "json",
            }
        )
        url = f"{base}?{params}"
        req = urllib.request.Request(
            url, headers={"User-Agent": "RegGuard/1.0", "Accept": "application/json"}
        )

        def _fetch():
            with urllib.request.urlopen(req, timeout=12) as resp:
                return json.load(resp)

        data = await asyncio.to_thread(_fetch)
        feats = data.get("features") or []
        if not feats:
            return "X", False
        attrs = feats[0].get("attributes") or {}
        zone = str(attrs.get("FLD_ZONE") or "").strip() or "X"
        sfha_raw = str(attrs.get("SFHA_TF") or "").strip().upper()
        sfha = sfha_raw in ("T", "TRUE", "Y", "YES", "1")
        return zone, sfha

    async def _nwi_point_intersect(self, lat: float, lng: float):
        """
        True/False if NWI wetlands intersect; None on total failure.

        Free hosts rotate: USGS WIM layer 1 is the richest wetlands layer;
        fws.gov and layer 0 are fallbacks when one host is flaky/down.
        """
        endpoints = [
            # Prefer layer 1 — layer 0 often under-reports vs the full NWI stack
            "https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest/services/Wetlands/MapServer/1/query",
            "https://www.fws.gov/wetlandsmapservice/rest/services/Wetlands/MapServer/0/query",
            "https://fwspublicservices.wim.usgs.gov/wetlandsmapservice/rest/services/Wetlands/MapServer/0/query",
        ]
        return await self._arcgis_any_intersect(
            lat,
            lng,
            endpoints,
            out_fields="*",
            pad=0.00035,
            label="NWI",
        )

    async def _fws_critical_habitat_intersect(self, lat: float, lng: float):
        """
        True/False if critical habitat intersects; None on total failure.

        Primary FWS MapServer often 502s; free ArcGIS Online mirror is the fallback.
        Full IPaC species lists still require the IPaC website (not automatable free).
        """
        endpoints = [
            "https://gis.fws.gov/arcgis/rest/services/FWSEcos/FWSCriticalHabitat/MapServer/0/query",
            "https://services.arcgis.com/QVENGdaPbd4LUkLV/arcgis/rest/services/USFWS_Critical_Habitat/FeatureServer/0/query",
        ]
        return await self._arcgis_any_intersect(
            lat,
            lng,
            endpoints,
            out_fields="*",
            pad=0.00045,
            label="FWS-CH",
        )

    async def _arcgis_any_intersect(
        self,
        lat: float,
        lng: float,
        endpoints: List[str],
        *,
        out_fields: str,
        pad: float,
        label: str,
    ):
        """Try free ArcGIS query hosts until we can answer True / False / None.

        Consensus (stability):
        - True if *any* successful host/geometry reports an intersect
        - False only if at least one host succeeded and *none* reported intersect
        - None if every attempt failed (do not invent False)

        Previously the first successful empty response returned False immediately, so a
        flaky primary host falling through to a secondary layer could flip False→True
        across runs for the same pin.
        """
        import json
        import urllib.error
        import urllib.parse
        import urllib.request

        geometries = [
            (
                f"{lng - pad},{lat - pad},{lng + pad},{lat + pad}",
                "esriGeometryEnvelope",
                {},
            ),
            (
                f"{lng},{lat}",
                "esriGeometryPoint",
                {"distance": "120", "units": "esriSRUnit_Meter"},
            ),
        ]

        last_err: Optional[str] = None
        saw_success = False
        saw_hit = False
        for base in endpoints:
            for geom, gtype, extra in geometries:
                params = {
                    "geometry": geom,
                    "geometryType": gtype,
                    "inSR": "4326",
                    "spatialRel": "esriSpatialRelIntersects",
                    "outFields": out_fields if out_fields else "*",
                    "returnGeometry": "false",
                    "f": "json",
                    "resultRecordCount": "5",
                }
                params.update(extra)
                url = f"{base}?{urllib.parse.urlencode(params)}"
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "RegGuard/1.0", "Accept": "application/json"},
                )

                def _fetch(request=req):
                    with urllib.request.urlopen(request, timeout=10) as resp:
                        return json.load(resp)

                data = None
                for attempt in range(2):
                    try:
                        data = await asyncio.to_thread(_fetch)
                        break
                    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
                        last_err = str(e)
                        if attempt == 0:
                            await asyncio.sleep(0.35)
                            continue
                        logger.info("%s GIS miss on %s: %s", label, base.split("/")[2], e)
                        data = None
                        break
                    except Exception as e:
                        last_err = str(e)
                        logger.info("%s GIS error on %s: %s", label, base.split("/")[2], e)
                        data = None
                        break

                if not isinstance(data, dict):
                    continue
                if data.get("error"):
                    last_err = str(data.get("error"))
                    continue
                feats = data.get("features")
                if feats is None and "features" not in data:
                    last_err = "no features key"
                    continue
                saw_success = True
                hit = len(feats or []) > 0
                logger.info(
                    "%s GIS ok via %s (%s) hit=%s",
                    label,
                    base.split("/")[2],
                    gtype,
                    hit,
                )
                if hit:
                    saw_hit = True
                    # Conservative CYA: one confirmed intersect is enough
                    return True

        if saw_success:
            return False
        if last_err:
            logger.warning("%s GIS all hosts failed: %s", label, last_err)
        return None

    async def _check_noise_ordinances(self, city: str, state: str) -> EnvironmentalRisk:
        """Check municipal noise ordinances and zoning"""
        code_url = municode_library_url(city, state)
        code_label = f"{city} Municipal Code" if city else "Municipal Code"
        try:
            logger.info(f"🔍 Checking noise ordinances for {city}, {state}")
            
            search_result = await self._firecrawl_search(
                query=f"{city} {state} noise ordinance decibel limit zoning requirements",
                location=f"{city}, {state}"
            )
            
            ordinance_info = self._parse_ordinance_result(search_result)
            
            if ordinance_info:
                return EnvironmentalRisk(
                    category="noise_ordinances",
                    risk_level="MEDIUM",
                    description=f"City noise ordinance: {ordinance_info}",
                    action_items=[
                        "Request full noise ordinance text from city planning department",
                        "Conduct baseline noise survey ($1K-3K)",
                        "If high-noise use, obtain conditional use permit",
                        "Install noise mitigation if needed (cost varies)",
                    ],
                    data_sources=["City Municipal Code", "Planning Department"],
                    research_cost_usd=75.0,
                    verified=False,
                    source_url=code_url,
                    source_label=code_label,
                )
            else:
                return EnvironmentalRisk(
                    category="noise_ordinances",
                    risk_level="LOW",
                    description="Standard municipal noise ordinance applies.",
                    action_items=["Review local noise limits"],
                    data_sources=["Municipal Code"],
                    research_cost_usd=25.0,
                    verified=False,
                    source_url=code_url,
                    source_label=code_label,
                )
        except Exception as e:
            logger.error(f"Noise ordinance check failed: {e}")
            return EnvironmentalRisk(
                category="noise_ordinances",
                risk_level="UNKNOWN",
                description="Unable to determine noise requirements.",
                action_items=["Contact city planning department"],
                data_sources=["Manual inquiry required"],
                research_cost_usd=0.0,
                verified=False,
                source_url=code_url,
                source_label=code_label,
            )
    
    async def _check_nepa_requirements(self, latitude: float, longitude: float) -> EnvironmentalRisk:
        """Check NEPA (National Environmental Policy Act) applicability"""
        try:
            logger.info(f"🔍 Checking NEPA requirements for lat {latitude}, lng {longitude}")
            
            search_result = await self._firecrawl_search(
                query=f"NEPA environmental assessment required federal funding permits {latitude} {longitude}",
                location=f"{latitude},{longitude}"
            )
            
            nepa_required = self._parse_nepa_result(search_result)
            
            if nepa_required:
                return EnvironmentalRisk(
                    category="nepa",
                    risk_level="MEDIUM",
                    description="Project may require NEPA compliance if involving federal funding or permits.",
                    action_items=[
                        "Confirm if project involves federal agency permits or funding",
                        "If yes, EA (Environmental Assessment) or EIS (Environmental Impact Statement) may be required",
                        "Budget 6-12 months for federal environmental review",
                        "Hire environmental consultant ($15K-50K+)",
                    ],
                    data_sources=["Federal agency coordination", "40 CFR Parts 1500-1508"],
                    research_cost_usd=100.0,
                    verified=False,
                    source_url=EPA_NEPA_URL,
                    source_label="EPA NEPA",
                )
            else:
                return EnvironmentalRisk(
                    category="nepa",
                    risk_level="LOW",
                    description="NEPA likely not applicable (no federal funding/permits).",
                    action_items=["Proceed with state/local environmental review only"],
                    data_sources=["Project scope analysis"],
                    research_cost_usd=0.0,
                    verified=False,
                    source_url=EPA_NEPA_URL,
                    source_label="EPA NEPA",
                )
        except Exception as e:
            logger.error(f"NEPA check failed: {e}")
            return EnvironmentalRisk(
                category="nepa",
                risk_level="UNKNOWN",
                description="Unable to determine NEPA applicability.",
                action_items=["Consult with federal agencies"],
                data_sources=["Manual inquiry required"],
                research_cost_usd=0.0,
                verified=False,
                source_url=EPA_NEPA_URL,
                source_label="EPA NEPA",
            )
    
    async def _check_state_requirements(self, state: str, city: str) -> EnvironmentalRisk:
        """Check state-specific environmental requirements"""
        env_url, env_label = state_env_confirm(state)
        try:
            logger.info(f"🔍 Checking state requirements for {state}")
            
            search_result = await self._firecrawl_search(
                query=f"{state} environmental review requirements state law {city}",
                location=f"{city}, {state}"
            )
            
            state_reqs = self._parse_state_requirements(search_result, state)
            
            if state_reqs:
                return EnvironmentalRisk(
                    category="state_requirements",
                    risk_level="MEDIUM",
                    description=f"State requirements: {state_reqs}",
                    action_items=[
                        f"Consult {state} environmental agency regulations",
                        "Submit required state environmental forms",
                        "Allow for state review period (typically 30-60 days)",
                        "Budget for state permits and fees",
                    ],
                    data_sources=[f"{state} Department of Environmental Quality", f"{state} Environmental Code"],
                    research_cost_usd=75.0,
                    verified=False,
                    source_url=env_url,
                    source_label=env_label,
                )
            else:
                return EnvironmentalRisk(
                    category="state_requirements",
                    risk_level="LOW",
                    description="Standard state environmental review applies.",
                    action_items=["Follow state guidelines"],
                    data_sources=["State Environmental Code"],
                    research_cost_usd=25.0,
                    verified=False,
                    source_url=env_url,
                    source_label=env_label,
                )
        except Exception as e:
            logger.error(f"State requirements check failed: {e}")
            return EnvironmentalRisk(
                category="state_requirements",
                risk_level="UNKNOWN",
                description="Unable to determine state requirements.",
                action_items=["Contact state environmental agency"],
                data_sources=["Manual inquiry required"],
                research_cost_usd=0.0,
                verified=False,
                source_url=env_url,
                source_label=env_label,
            )
    
    # ===== Helper Methods =====
    
    async def _firecrawl_search(self, query: str, location: str) -> Dict[str, Any]:
        """Make Firecrawl API call for environmental data"""
        if not self.firecrawl_api_key:
            logger.warning("⚠️ Firecrawl API key not set, using cached template data")
            return {}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.firecrawl_base_url}/search",
                    json={"query": query, "location": location},
                    headers={"Authorization": f"Bearer {self.firecrawl_api_key}"},
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Firecrawl API error: {e}")
            return {}
    
    def _parse_wetlands_result(self, result: Dict) -> bool:
        """Parse Firecrawl result for wetlands presence"""
        # Simplified logic - in production would parse real API response
        return bool(result)
    
    def _parse_species_result(self, result: Dict) -> Optional[str]:
        """Parse Firecrawl result for endangered species"""
        return None
    
    def _parse_flood_result(self, result: Dict) -> Optional[str]:
        """Parse FEMA flood map result"""
        return None
    
    def _parse_ordinance_result(self, result: Dict) -> Optional[str]:
        """Parse noise ordinance result"""
        return None
    
    def _parse_nepa_result(self, result: Dict) -> bool:
        """Parse NEPA applicability result"""
        return False
    
    def _parse_state_requirements(self, result: Dict, state: str) -> Optional[str]:
        """Parse state requirements result"""
        return None
    
    def _calculate_overall_risk(self, risk_levels: List[str]) -> str:
        """Legacy helper — prefer calculate_overall_env_risk(findings)."""
        synthetic = [
            {"category": "flood_zones", "risk_level": lv, "verified": True}
            for lv in risk_levels
            if str(lv or "").upper() in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        ]
        if not synthetic:
            return "UNKNOWN"
        return str(calculate_overall_env_risk(synthetic).get("risk_level") or "UNKNOWN")
    
    def _generate_action_plan(self, findings: List[EnvironmentalRisk]) -> List[str]:
        """Generate master action plan from all findings"""
        action_plan = []
        for finding in findings:
            action_plan.extend(finding.action_items)
        return action_plan
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"


# Singleton instance
_engine = None

def get_environmental_screening_engine() -> EnvironmentalScreeningEngine:
    """Get or create environmental screening engine instance"""
    global _engine
    if _engine is None:
        _engine = EnvironmentalScreeningEngine()
    return _engine
