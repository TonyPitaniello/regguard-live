"""
Reg Guard — Universal Scout: Firecrawl **/v2/search** (web index) for URL discovery.

We use the **search** endpoint with ``sources=["web"]`` and **no** ``scrapeOptions`` so
Firecrawl returns SERP URLs and snippets only—no full-page crawl, no ``crawl_url``, and no
per-result markdown download. That keeps latency and credits low versus bundled
search+scrape or site mapping.

Depth / page limits in the user brief (``maxDepth``, ``exclude_external_links``) apply to
Firecrawl **crawl** jobs; this codebase does not call ``crawl()`` for Universal Scout.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple
from urllib.parse import urlparse

from dotenv import load_dotenv
from firecrawl import Firecrawl
from firecrawl.v2.types import ScrapeOptions, SearchData
from data_center_intel import state_energy_law_cues as _dc_state_energy_law_cues
from semantic_scout_cache import cache_get as _semantic_scout_cache_get
from semantic_scout_cache import cache_set as _semantic_scout_cache_set
from semantic_scout_cache import semantic_scout_cache_enabled

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

# -----------------------------------------------------------------------------
# Universal Scout — trusted domains (query operators + post-filter)
# -----------------------------------------------------------------------------

# Firecrawl / web search: restrict SERP to U.S. government and Municode (reduces unrelated-state noise).
SEARCH_DOMAIN_SCOPE = "(site:gov OR site:municode.com)"

# Residential zoning / setbacks: include **OpenGov**-style municipal transparency hosts (contractor-facing “OpenPublic” portals).
SEARCH_DOMAIN_SCOPE_ZONING = "(site:gov OR site:municode.com OR site:opengov.com)"

# Ordered keys on scout payloads that carry Firecrawl ``results`` (source URL harvesting, digests, Reality Capture).
SCOUT_SOURCE_STEP_KEYS: Tuple[str, ...] = (
    "step_jurisdiction",
    "step_building_permits",
    "step_building_codes",
    "step_residential_zoning",
    "step_federal_fast41",
    "step_data_center_water",
    "step_refrigerant_aim_act",
    "step_water_usage_effectiveness",
    "step_dc_state_energy",
    "step_dc_local_moratorium",
)

# City of Plano — product-targeted scout supplements (documented in ``main`` module docstring).
PLANO_SCOUT_AMENDMENTS_NEC = "Plano TX electrical amendments 2023 NEC"
PLANO_SCOUT_FEE_SCHEDULE = "Plano building fee schedule 2026"


def _is_plano_texas(city: str, state: str) -> bool:
    c = (city or "").strip().lower()
    s = (state or "").strip().upper()
    return c == "plano" and s in ("TX",)


def _is_austin_texas(city: str, state: str) -> bool:
    c = (city or "").strip().lower()
    s = (state or "").strip().upper()
    return c == "austin" and s in ("TX",)


def _is_dallas_texas(city: str, state: str) -> bool:
    c = (city or "").strip().lower()
    s = (state or "").strip().upper()
    return c == "dallas" and s in ("TX",)


AUSTIN_SCOUT_DEVELOPMENT_FEES_SURCHARGE = (
    "site:austintexas.gov development services fees safety surcharge electrical permit"
)
AUSTIN_SCOUT_DESIGN_CRITERIA_ELECTRICAL = (
    "Austin Texas design criteria electrical service 36 inch gas relief solar ready 225A 200A bus"
)


# Code-Change Monitoring Agent — SERP cues merged into the building-codes pass (trusted domains only).
CODE_CHANGE_SCOUT_UPCOMING_ADOPTION = (
    "upcoming building code adoption NEC NFPA 70 effective date transition council workshop"
)
CODE_CHANGE_SCOUT_ORDINANCE_MINUTES = (
    "city council agenda minutes ordinance building code amendment hearing first reading"
)


def _append_code_change_monitor_queries(
    codes_line: str,
    *,
    zip_tag: str,
    city: str,
    county: str,
    st: str,
    mode: str,
) -> str:
    """Augment Universal Scout 3 (codes) with localized adoption-cycle / minutes discovery."""
    city = (city or "").strip()
    county = (county or "").strip()
    st = (st or "").strip()
    m = (mode or "").strip().lower()
    if m == "county" or (not city and county):
        county_disp = f"{county} County" if county and not county.lower().endswith("county") else county
        loc = f"{county_disp}, {st}".strip().strip(",") if st else county_disp
        extra = (
            f"{loc} {CODE_CHANGE_SCOUT_UPCOMING_ADOPTION} — {zip_tag} | "
            f"{loc} {CODE_CHANGE_SCOUT_ORDINANCE_MINUTES} — {zip_tag}"
        )
        return f"{codes_line} | {extra}"
    city_disp = city or "municipality"
    loc_cs = f"{city_disp}, {st}".strip().strip(",") if st else city_disp
    extra = (
        f"{loc_cs} {CODE_CHANGE_SCOUT_UPCOMING_ADOPTION} — {zip_tag} | "
        f"{loc_cs} {CODE_CHANGE_SCOUT_ORDINANCE_MINUTES} — {zip_tag}"
    )
    return f"{codes_line} | {extra}"


def _locality_data_fence(
    city: str,
    county: str,
    st: str,
    mode: str,
    *,
    zip5: str = "",
    site_address: Optional[str] = None,
) -> str:
    """
    Append a **looser** locality cue on every scout line (still names City, ST or County, ST) so queries read like
    official permit/code discovery—not a harsh ``ONLY …`` filter that can zero-out SERP. Documented from ``main``.

    **Dallas vs Lake Dallas:** for Dallas County / Stemmons / ``752xx`` corridors, append **LOCALITY_STRICT** so SERP
    targets **City of Dallas**, not **Lake Dallas** (Denton County).
    """
    stx = (st or "").strip()
    if not stx:
        return ""
    c = (city or "").strip()
    co = (county or "").strip()
    if co:
        county_disp = f"{co} County" if not co.lower().endswith("county") else co
    else:
        county_disp = ""
    m = (mode or "").strip().lower()
    base = ""
    if county_disp and (m == "county" or not c):
        base = f" | LOCALITY_LOCK {county_disp}, {stx} official county building permits and adopted code"
    elif c:
        base = f" | LOCALITY_LOCK {c}, {stx} official city code and building permits"

    zd = "".join(ch for ch in (zip5 or "") if ch.isdigit())[:5]
    site_l = (site_address or "").lower()
    stemmons = any(
        x in site_l
        for x in (
            "stemmons",
            "n. stemmons",
            "north stemmons",
            "stemmons fwy",
            "stemmons freeway",
        )
    )
    ih_corridor = "ih-35" in site_l or "i-35" in site_l
    dallas_strict = ""
    if stx.upper() == "TX":
        co_l = co.lower()
        dallas_corridor = (
            _is_dallas_texas(c, stx)
            or (zd.startswith("752") and "dallas" in co_l)
            or zd == "75207"
            or stemmons
            or (ih_corridor and zd.startswith("752") and "dallas" in co_l)
        )
        if dallas_corridor:
            dallas_strict = (
                " | LOCALITY_STRICT City of Dallas Dallas County Texas "
                "NOT Lake Dallas Denton County municipal boundary"
            )
            if stemmons or zd == "75207":
                dallas_strict += " | Stemmons Freeway Dallas 752xx official city permits NOT Lake Dallas"

    return f"{base}{dallas_strict}"


def _normalize_scout_vertical(v: Optional[str]) -> str:
    x = (v or "").strip().lower().replace(" ", "_").replace("-", "_")
    if x in ("infrastructure", "infra", "critical_infrastructure"):
        return "infrastructure"
    if x in ("data_center", "datacenter", "dc", "colocation"):
        return "data_center"
    if x in ("ai_crypto_compute", "crypto", "crypto_mining", "mining", "asic", "compute_cluster"):
        return "ai_crypto_compute"
    if x in ("bess", "battery_storage", "battery_energy_storage", "lithium", "ess", "energy_storage"):
        return "bess"
    return "building"


_VALID_TRADE_TOKENS: frozenset[str] = frozenset(
    {
        "general_contractor",
        "electrician",
        "plumber",
        "hvac",
        "hvac_mechanical",
        "zoning_planning",
        "owner_builder",
    }
)


def _normalize_trade_tokens(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        parts = [p.strip().lower() for p in re.split(r"[,;\s]+", raw) if p.strip()]
    elif isinstance(raw, (list, tuple, set)):
        parts = [str(p).strip().lower() for p in raw if str(p).strip()]
    else:
        return []
    aliases = {
        "electrical": "electrician",
        "electric": "electrician",
        "mechanical": "hvac",
        "hvac/mechanical": "hvac_mechanical",
        "hvac_mechanical": "hvac_mechanical",
        "plumbing": "plumber",
        "gc": "general_contractor",
        "generalcontractor": "general_contractor",
        "zoning": "zoning_planning",
        "planning": "zoning_planning",
        "zoning_and_planning": "zoning_planning",
        "owner-builder": "owner_builder",
        "ownerbuilder": "owner_builder",
    }
    out: List[str] = []
    for p in parts:
        base = aliases.get(p, p.strip()).lower().strip()
        norm = (
            base.replace("&", " and ")
            .replace("/", " ")
            .replace("-", " ")
            .replace(",", " ")
        )
        q = aliases.get(norm, "_".join(norm.split()))
        while q in aliases:
            q = aliases[q]
        if q in _VALID_TRADE_TOKENS and q not in out:
            out.append(q)
    return out


def _effective_mep_trade_set(trades: List[str]) -> set[str]:
    """Treat ``hvac_mechanical`` like ``hvac`` for MEP / multi-trade coordination counts."""
    s: set[str] = set()
    for t in trades:
        if t == "hvac_mechanical":
            s.add("hvac")
        elif t in ("electrician", "plumber", "hvac"):
            s.add(t)
    return s


def _append_mep_trade_segments(
    juris: str,
    permits: str,
    codes: str,
    *,
    zip_tag: str,
    city: str,
    county: str,
    st: str,
    mode: str,
    trades: List[str],
    mission_critical_dc: bool,
    vertical: str,
) -> tuple[str, str, str]:
    """Augment scout lines for selected MEP trades, data-center mission-critical mode, and vertical."""
    if not trades and not mission_critical_dc and vertical not in ("infrastructure", "data_center"):
        return juris, permits, codes

    city = (city or "").strip()
    county = (county or "").strip()
    st = (st or "").strip()
    mode_l = (mode or "").strip().lower()
    if not (city or county or st):
        loc = f"US {zip_tag}"
    elif mode_l == "county" or (not city and county):
        county_disp = f"{county} County" if county and not county.lower().endswith("county") else county
        loc = f"{county_disp}, {st}".strip().strip(",") if st else county_disp
    else:
        city_disp = city or "municipality"
        loc = f"{city_disp}, {st}".strip().strip(",") if st else city_disp

    mep_eff = _effective_mep_trade_set(trades)

    chunks: List[str] = []
    if "general_contractor" in trades:
        chunks.append(
            f"{loc} general contractor superintendent IBC OSHA multi-trade permit sequencing inspection hold points — "
            f"{zip_tag}"
        )
    if "electrician" in trades:
        chunks.append(
            f"{loc} electrical subcontractor permit NEC NFPA 70 amendments utility coordination — {zip_tag}"
        )
    if "plumber" in trades:
        chunks.append(
            f"{loc} plumbing permit IPC UPC adopted amendments drainage water pipe sizing inspections — {zip_tag}"
        )
    if "hvac" in trades or "hvac_mechanical" in trades:
        chunks.append(
            f"{loc} HVAC mechanical permit IMC energy code Manual J ACCA adoption refrigerant commissioning — "
            f"{zip_tag}"
        )
    if "zoning_planning" in trades:
        chunks.append(
            f"{loc} zoning planning board subdivision FAR lot coverage duplex setbacks side yard driveway "
            f"minimum parking bicycle parking ordinance 2025 amendment — {zip_tag}"
        )
    if "owner_builder" in trades:
        chunks.append(
            f"{loc} owner builder affidavit owner-occupancy construction liability insurance affidavit "
            f"registered builder exceptions — {zip_tag}"
        )
    if len(mep_eff) >= 3:
        chunks.append(
            f"{loc} combined MEP multi-trade permitting mechanical electrical plumbing coordination — {zip_tag}"
        )

    if mission_critical_dc:
        chunks.append(
            f"{loc} data center Tier III Tier IV redundancy 2N N+1 concurrent maintainability "
            f"mission critical facility code adopted amendments — {zip_tag}"
        )
        chunks.append(
            f"{loc} liquid cooling containment CDU rear door heat exchanger data hall "
            f"fire code mechanical electrical safety adopted requirements — {zip_tag}"
        )

    if vertical == "data_center" and not mission_critical_dc:
        chunks.append(
            f"{loc} data center colocation facility mechanical electrical uptime staging "
            f"AHJ adopted codes — {zip_tag}"
        )
    if vertical == "infrastructure":
        chunks.append(
            f"{loc} infrastructure utility mission critical building mechanical electrical "
            f"permitting adopted code — {zip_tag}"
        )

    if not chunks:
        return juris, permits, codes

    segment = " | ".join(chunks)
    permits = f"{permits} | {segment}"
    codes = f"{codes} | {segment}"
    return juris, permits, codes


def _fast41_query_line(
    *,
    zip_tag: str,
    city: str,
    county: str,
    st: str,
    mode: str,
    site_address: Optional[str],
    vertical: str,
) -> str:
    site = (site_address or "").strip()
    loc_bits: List[str] = []
    if site:
        loc_bits.append(site)
    city = (city or "").strip()
    county = (county or "").strip()
    st = (st or "").strip()
    mode_l = (mode or "").strip().lower()
    if mode_l == "county" or (not city and county):
        county_disp = f"{county} County" if county and not county.lower().endswith("county") else county
        if county_disp and st:
            loc_bits.append(f"{county_disp}, {st}")
    elif city and st:
        loc_bits.append(f"{city}, {st}")
    loc = " ".join(loc_bits).strip()
    vlabel = "infrastructure" if vertical == "infrastructure" else "data center"
    core = (
        f"FAST-41 federal eligibility permitting Title 41 Permitting Council covered project status "
        f"{vlabel} environmental review milestone dashboard {loc} — {zip_tag}"
    )
    if vertical == "data_center":
        core += (
            " May 5 2026 presidential action rescinds EO 14141 FAST-41 Transparency Project "
            "Permitting Council transparency dashboard greater than 100 MW facility gate "
            "Virginia HB 1515 interconnection Ohio 2026 ballot initiative greater than 25 MW ban data center"
        )
    if (st or "").strip().upper() == "TX":
        core += (
            " ERCOT 2026 Batch Zero industrial substation transmission performance milestone "
            "large electric load interconnection agreement PUCT"
        )
    return core


def _scout_geo_phrase(
    *,
    zip_tag: str,
    city: str,
    county: str,
    st: str,
    mode: str,
    site_address: Optional[str],
) -> str:
    """Compact locality phrase for tiered scout lines (City/County, ST + optional street context)."""
    site = (site_address or "").strip()
    loc_bits: List[str] = []
    if site:
        loc_bits.append(site)
    city = (city or "").strip()
    county = (county or "").strip()
    st = (st or "").strip()
    mode_l = (mode or "").strip().lower()
    if mode_l == "county" or (not city and county):
        county_disp = f"{county} County" if county and not county.lower().endswith("county") else county
        if county_disp and st:
            loc_bits.append(f"{county_disp}, {st}")
    elif city and st:
        loc_bits.append(f"{city}, {st}")
    loc = " ".join(loc_bits).strip()
    return loc if loc else f"US {zip_tag}"


def _residential_zoning_setback_query_line(
    *,
    zip_tag: str,
    city: str,
    county: str,
    st: str,
    mode: str,
    site_address: Optional[str],
) -> str:
    """Municode / .gov / OpenGov discovery for residential lot line and yard setbacks (tier: building vertical)."""
    loc = _scout_geo_phrase(
        zip_tag=zip_tag,
        city=city,
        county=county,
        st=st,
        mode=mode,
        site_address=site_address,
    )
    return (
        f"{loc} zoning ordinance setback front yard side yard rear yard lot line "
        f"residential single-family R-1 Chapter 150 Municode codified GIS open data portal — {zip_tag}"
    )


def _dc_state_energy_query_line(
    *,
    zip_tag: str,
    city: str,
    county: str,
    st: str,
    mode: str,
    site_address: Optional[str],
) -> str:
    """Ratepayer protection / PSC rider / interconnect surcharge discovery (data-center vertical only)."""
    loc = _scout_geo_phrase(
        zip_tag=zip_tag,
        city=city,
        county=county,
        st=st,
        mode=mode,
        site_address=site_address,
    )
    stx = (st or "").strip().upper()
    cues = _dc_state_energy_law_cues(stx)
    cue_seg = (" ".join(cues[:2]) + " ") if cues else ""
    ercot_tx = ""
    if stx == "TX":
        ercot_tx = (
            " ERCOT 2026 Batch Zero industrial substation performance milestone transmission "
            "TDSP schedule large load PUCT"
        )
    return (
        f"{loc} data center {cue_seg}"
        f"ratepayer protection pledge utility commission tariff rider transmission allocation "
        f"large electric load interconnect deposit infrastructure surcharge network upgrade cost sharing "
        f"hyperscale facility — {zip_tag}{ercot_tx}"
    )


def _dc_local_moratorium_query_line(
    *,
    zip_tag: str,
    city: str,
    county: str,
    st: str,
    mode: str,
    site_address: Optional[str],
) -> str:
    """2026 township/county moratorium & pause language via trusted-domain SERP."""
    loc = _scout_geo_phrase(
        zip_tag=zip_tag,
        city=city,
        county=county,
        st=st,
        mode=mode,
        site_address=site_address,
    )
    stx = (st or "").strip().upper()
    bill_tail = ""
    if stx == "VA":
        bill_tail = " Virginia HB 1515 interconnection moratorium block "
    elif stx == "OH":
        bill_tail = " Ohio 2026 ballot initiative greater than 25 MW data center ban moratorium "
    elif stx == "NY":
        bill_tail = " New York state legislature data center moratorium bill session 2026 "
    elif stx == "OK":
        bill_tail = " Oklahoma legislature large electric load data center moratorium 2026 "
    elif stx == "GA":
        bill_tail = " Georgia PSC certificate necessity data center moratorium bill 2026 "
    prefix = f"{loc} {bill_tail}".strip()
    return (
        f"{prefix} "
        f"township county zoning moratorium 2026 data center pause ordinance interim ban "
        f"cooling tower moratorium AI infrastructure halt emergency ordinance High Alert — {zip_tag}"
    )


def _data_center_utility_water_query_line(
    *,
    zip_tag: str,
    city: str,
    county: str,
    st: str,
    mode: str,
    site_address: Optional[str],
    vertical: str,
) -> str:
    """
    Utility-scale / hyperscale cooling water: NPDES, Clean Water Act tie-ins, state utility commission cues
    (tier: data center / infrastructure vertical; complements FAST-41).
    """
    loc = _scout_geo_phrase(
        zip_tag=zip_tag,
        city=city,
        county=county,
        st=st,
        mode=mode,
        site_address=site_address,
    )
    vlabel = "data center" if vertical == "data_center" else "infrastructure"
    return (
        f"{loc} {vlabel} cooling water withdrawal consumptive use NPDES discharge permit "
        f"utility scale EPA state environmental quality commission drought management — {zip_tag}"
    )


def _refrigerant_aim_act_query_line(
    *,
    zip_tag: str,
    city: str,
    county: str,
    st: str,
    mode: str,
    site_address: Optional[str],
) -> str:
    """MEP / mechanical — AIM Act phasedown / HFC SNAP-class signals (trusted-domain SERP)."""
    loc = _scout_geo_phrase(
        zip_tag=zip_tag,
        city=city,
        county=county,
        st=st,
        mode=mode,
        site_address=site_address,
    )
    return (
        f"{loc} AIM Act hydrofluorocarbon refrigerant phasedown SNAP EPA rule HVAC mechanical chiller chilled water "
        f"facility code enforcement commissioning — {zip_tag}"
    )


def _water_usage_effectiveness_query_line(
    *,
    zip_tag: str,
    city: str,
    county: str,
    st: str,
    mode: str,
    site_address: Optional[str],
) -> str:
    """Data-center / infra — AHJ-facing Water Usage Effectiveness (WUE) and reclaimed-water overlays."""
    loc = _scout_geo_phrase(
        zip_tag=zip_tag,
        city=city,
        county=county,
        st=st,
        mode=mode,
        site_address=site_address,
    )
    return (
        f"{loc} data center Water Usage Effectiveness WUE municipal water ordinance conservation reuse "
        f"cooling tower blowdown reclaimed water discharge permit AHJ mandate — {zip_tag}"
    )


def _coerce_scout_profile(raw: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    r = dict(raw or {})
    trades = _normalize_trade_tokens(r.get("trades"))
    vert = _normalize_scout_vertical(str(r.get("vertical") or "building"))
    mc = r.get("mission_critical_dc")
    mc_bool = mc is True or (isinstance(mc, str) and mc.strip().lower() in ("1", "true", "yes", "on"))
    jf = r.get("job_fast41_eligible")
    job_fast41 = jf is True or (
        isinstance(jf, str)
        and jf.strip() != ""
        and jf.strip().lower() in ("1", "true", "yes", "on")
    )
    return {
        "trades": trades,
        "vertical": vert,
        "mission_critical_dc": mc_bool,
        "job_fast41_eligible": job_fast41,
        "light_scout": bool(r.get("light_scout")),
    }


def _reject_serp_for_project_state(blob: str, project_state: Optional[str]) -> bool:
    """Drop hits that clearly reference Washington State when the project is elsewhere (e.g. Texas)."""
    st = (project_state or "").strip().upper()
    if len(st) != 2:
        return False
    if st == "WA":
        return False
    b = (blob or "").lower()
    if re.search(r"\bwashington\s+state\b", b) or re.search(r"\bstate\s+of\s+washington\b", b):
        return True
    if ".wa.gov" in b:
        return True
    if st == "TX" and re.search(r"\bseattle\b", b):
        if not re.search(r"\b(texas|dallas|plano|fort\s+worth|houston|austin)\b", b) and not re.search(
            r"\btx\b", b
        ):
            return True
    return False


def _scout_queries_for_location(
    z: str,
    site_address: Optional[str],
    jurisdiction: Optional[Mapping[str, Any]],
    scout_profile: Optional[Mapping[str, Any]] = None,
) -> tuple[str, str, str]:
    """
    Build (jurisdiction, permits, codes) search lines for Universal Scout.

    Every line includes **explicit locality** (``City, ST`` or ``County, ST``) when geocoding
    provides it, plus ZIP where helpful. Queries are combined in ``_append_scope`` with
    ``(site:gov OR site:municode.com)``.

    ``scout_profile`` carries **Full MEP** trade selections, **mission-critical data-center** cues,
    and project **vertical** (building / infrastructure / data_center) for query augmentation.
    """
    prof = _coerce_scout_profile(scout_profile)
    addr = (site_address or "").strip()
    ju = jurisdiction
    if ju:
        addr = addr or str(ju.get("formatted_address") or "").strip() or f"ZIP {z}"

    zip_tag = f"ZIP {z}"

    if not ju or not addr:
        juris = f"US {zip_tag} municipality county jurisdiction AHJ building permits — {zip_tag}"
        permits = (
            f"US {zip_tag} building department permit applications electrical official — {zip_tag} | "
            f"US {zip_tag} official building permit fees 2026"
        )
        codes = (
            f"US {zip_tag} adopted building code amendments codified law official — {zip_tag} | "
            f"US {zip_tag} NEC 2023 amendments | "
            f"US {zip_tag} upcoming NEC code adoption ordinance council agenda minutes — {zip_tag}"
        )
        juris, permits, codes = _append_mep_trade_segments(
            juris,
            permits,
            codes,
            zip_tag=zip_tag,
            city="",
            county="",
            st="",
            mode="",
            trades=prof["trades"],
            mission_critical_dc=prof["mission_critical_dc"],
            vertical=prof["vertical"],
        )
        return (juris, permits, codes)

    mode = str(ju.get("mode") or "").strip().lower()
    city = str(ju.get("city") or "").strip()
    county = str(ju.get("county") or "").strip()
    st = str(ju.get("state") or "").strip()

    city_st = f"{city}, {st}".strip().strip(",") if city and st else ""
    if mode == "county" or (not city and county):
        county_disp = f"{county} County" if county and not county.lower().endswith("county") else county
        loc = f"{county_disp}, {st}".strip().strip(",") if st else county_disp
        prefix = f"{loc}: " if loc else ""
        juris = (
            f"{prefix}Job site {addr} — unincorporated or county-administered {county_disp}, {st} ({zip_tag}). "
            f"Confirm **county** is the AHJ for building permits (not a city department)."
        )
        permits = (
            f"{prefix}{county_disp} {st} building permits inspections development services "
            f"unincorporated official — {zip_tag}"
        )
        codes = (
            f"{prefix}Building codes adopted for {county_disp} {st}: county code amendments "
            f"IBC IRC — {zip_tag}"
        )
        fence = _locality_data_fence(city, county, st, mode, zip5=z, site_address=addr)
        juris, permits, codes = juris + fence, permits + fence, codes + fence
        fee_nec = (
            f"{county_disp}, {st} official building permit fees 2026",
            f"{county_disp}, {st} NEC 2023 amendments",
        )
        permits = f"{permits} | {fee_nec[0]}"
        codes = f"{codes} | {fee_nec[1]}"
        codes = _append_code_change_monitor_queries(
            codes,
            zip_tag=zip_tag,
            city=city,
            county=county,
            st=st,
            mode=mode,
        )
        juris, permits, codes = _append_mep_trade_segments(
            juris,
            permits,
            codes,
            zip_tag=zip_tag,
            city=city,
            county=county,
            st=st,
            mode=mode,
            trades=prof["trades"],
            mission_critical_dc=prof["mission_critical_dc"],
            vertical=prof["vertical"],
        )
        return (juris, permits, codes)

    city_disp = city or "the municipality"
    loc = city_st or (f"{city_disp}, {st}" if st else city_disp)
    prefix = f"{loc}: " if loc else ""
    juris = (
        f"{prefix}Job site {addr} — incorporated {city_disp}, {st} ({zip_tag}). "
        f"The **city** is typically the AHJ for building permits at this address."
    )
    permits = (
        f"{prefix}{city_disp} {st} building department permits plan check electrical official — {zip_tag}"
    )
    codes = (
        f"{prefix}Building codes adopted for {city_disp} {st}: municipal amendments IBC IRC — {zip_tag}"
    )
    fence = _locality_data_fence(city, county, st, mode, zip5=z, site_address=addr)
    juris, permits, codes = juris + fence, permits + fence, codes + fence
    fee_nec = (
        f"{city_disp}, {st} official building permit fees 2026",
        f"{city_disp}, {st} NEC 2023 amendments",
    )
    permits = f"{permits} | {fee_nec[0]}"
    codes = f"{codes} | {fee_nec[1]}"
    if _is_plano_texas(city, st):
        permits = f"{permits} | {PLANO_SCOUT_FEE_SCHEDULE}"
        codes = f"{codes} | {PLANO_SCOUT_AMENDMENTS_NEC}"
    if _is_austin_texas(city, st):
        permits = f"{permits} | {AUSTIN_SCOUT_DEVELOPMENT_FEES_SURCHARGE}"
        codes = f"{codes} | {AUSTIN_SCOUT_DESIGN_CRITERIA_ELECTRICAL}"
    # Catalog-driven extras (Dallas + any future metros)
    try:
        from ahj_catalog import scout_extras_for

        extras = scout_extras_for(city, st, zip_tag if isinstance(zip_tag, str) else "")
        for q in extras.get("permits") or []:
            if q and q not in permits:
                permits = f"{permits} | {q}"
        for q in extras.get("codes") or []:
            if q and q not in codes:
                codes = f"{codes} | {q}"
    except Exception:
        pass
    codes = _append_code_change_monitor_queries(
        codes,
        zip_tag=zip_tag,
        city=city,
        county=county,
        st=st,
        mode=mode,
    )
    juris, permits, codes = _append_mep_trade_segments(
        juris,
        permits,
        codes,
        zip_tag=zip_tag,
        city=city,
        county=county,
        st=st,
        mode=mode,
        trades=prof["trades"],
        mission_critical_dc=prof["mission_critical_dc"],
        vertical=prof["vertical"],
    )
    return (juris, permits, codes)

# Reuse cached scrapes where possible (24h) when single-page scrape is enabled elsewhere.
FIRECRAWL_MAX_AGE_MS = 86400000

# Optional: single-page /search bundled scrape (not used — kept for reference / future use).
# Firecrawl ``ScrapeOptions`` does not expose ``maxDepth`` or ``exclude_external_links``; those
# are **crawl** parameters. For bundled search+scrape, we minimize cost by markdown-only,
# ``fast_mode``, no ``links`` format (avoids expanding every on-page href), and stripping
# media/CSS tags from the DOM before extraction.
SEARCH_BUNDLED_SCRAPE_OPTIONS = ScrapeOptions(
    formats=["markdown"],
    only_main_content=True,
    max_age=FIRECRAWL_MAX_AGE_MS,
    fast_mode=True,
    remove_base64_images=True,
    block_ads=True,
    exclude_tags=[
        "img",
        "picture",
        "source",
        "video",
        "audio",
        "svg",
        "canvas",
        "iframe",
        "object",
        "embed",
        "style",
        "link",
        "noscript",
    ],
)

# Total SERP rows per scout query (permit checks: first few hits are enough).
_SEARCH_PAGE_LIMIT_MIN = 3
_SEARCH_PAGE_LIMIT_MAX = 5


def _effective_search_limit(user_limit: int) -> int:
    """Clamp Firecrawl /search ``limit`` to 3–5 pages per request."""
    u = max(1, int(user_limit))
    return min(_SEARCH_PAGE_LIMIT_MAX, max(_SEARCH_PAGE_LIMIT_MIN, min(u, _SEARCH_PAGE_LIMIT_MAX)))
def _require_firecrawl_key() -> str:
    key = (os.environ.get("FIRECRAWL_API_KEY") or "").strip()
    if not key:
        raise ValueError("FIRECRAWL_API_KEY is missing. Set it in the project .env file.")
    return key


def _get_client() -> Firecrawl:
    return Firecrawl(api_key=_require_firecrawl_key())


def normalize_us_zip(zip_code: str) -> str:
    """Return 5-digit US ZIP; accepts optional +4 (stored only 5 for queries)."""
    raw = (zip_code or "").strip()
    m = re.match(r"^(\d{5})(?:-(\d{4}))?$", re.sub(r"\s+", "", raw))
    if not m:
        raise ValueError("Invalid ZIP. Use 5 digits or ZIP+4 (e.g. 75001 or 75001-1234).")
    return m.group(1)


def clear_scout_run_caches() -> None:
    """
    Best-effort memory cleanup after a Universal Scout run.

    Universal Scout holds large Firecrawl payloads; nudging the cyclic GC helps release
    those graphs promptly on long-running uvicorn workers.
    """
    import gc

    try:
        from semantic_scout_cache import clear_semantic_scout_cache

        clear_semantic_scout_cache()
    except ImportError:
        pass
    try:
        from markdown_scraper import clear_markdown_scrape_cache

        clear_markdown_scrape_cache()
    except ImportError:
        pass
    gc.collect()


def _hostname(url: str) -> str:
    try:
        p = urlparse(url)
        host = (p.hostname or "").lower().rstrip(".")
        return host
    except (ValueError, TypeError):
        return ""


_STATE_SL_GOV_RE = re.compile(r"\.([a-z]{2})\.gov$", re.I)


def _host_conflicts_project_state(host: str, state_short: Optional[str]) -> bool:
    """True when host is a ``*.st.gov`` agency site and ``state_short`` is a different U.S. state."""
    st = (state_short or "").strip().lower()
    if len(st) != 2:
        return False
    m = _STATE_SL_GOV_RE.search(host)
    if not m:
        return False
    return m.group(1).lower() != st


def hostname_matches_trust_policy(host: str) -> bool:
    """
    Restrict to **.gov** (official government), **municode.com**, and **OpenGov** transparency hosts
    per product policy.

    Post-filter is defense-in-depth alongside ``SEARCH_DOMAIN_SCOPE`` in the query string.
    """
    if not host:
        return False
    host = host.lower().rstrip(".")
    if "municode" in host:
        return True
    if host.endswith(".gov"):
        return True
    if host.endswith(".opengov.com") or host == "opengov.com":
        return True
    return False


def url_matches_trust_policy(url: Optional[str]) -> bool:
    if not url:
        return False
    return hostname_matches_trust_policy(_hostname(str(url)))


def _append_scope(base: str, *, domain_scope: Optional[str] = None) -> str:
    scope = (domain_scope or SEARCH_DOMAIN_SCOPE).strip()
    b = (base or "").strip()
    if not b:
        return scope
    return f"{b} {scope}"


def _entry_to_dict(item: Any) -> Dict[str, Optional[str]]:
    url: Optional[str] = getattr(item, "url", None)
    title = getattr(item, "title", None)
    desc = getattr(item, "description", None)
    if desc is None:
        desc = getattr(item, "snippet", None)

    if url is None and isinstance(item, dict):
        url = item.get("url")
        title = item.get("title")
        desc = item.get("description") or item.get("snippet")

    # Search + scrape returns Document rows; URL lives on metadata.
    if url is None:
        md = getattr(item, "metadata", None)
        if md is not None:
            if isinstance(md, dict):
                url = md.get("url") or md.get("sourceURL") or md.get("source_url")
                if title is None:
                    title = md.get("title")
                if desc is None:
                    desc = md.get("description")
            else:
                url = getattr(md, "url", None) or getattr(md, "source_url", None)
                if title is None:
                    title = getattr(md, "title", None)
                if desc is None:
                    desc = getattr(md, "description", None)

    if url is None:
        return {}
    return {"url": str(url), "title": title, "description": desc}


def _web_hits_raw(data: Optional[SearchData]) -> List[Dict[str, Optional[str]]]:
    if not data or not data.web:
        return []
    out: List[Dict[str, Optional[str]]] = []
    for item in data.web:
        d = _entry_to_dict(item)
        if d:
            out.append(d)
    return out


def _filter_trusted(
    hits: List[Dict[str, Optional[str]]],
    limit: int,
    *,
    project_state: Optional[str] = None,
) -> List[Dict[str, Optional[str]]]:
    seen: set[str] = set()
    out: List[Dict[str, Optional[str]]] = []
    for h in hits:
        u = h.get("url")
        if not u or u in seen:
            continue
        host = _hostname(str(u))
        if not url_matches_trust_policy(u):
            continue
        if _host_conflicts_project_state(host, project_state):
            continue
        blob = f"{h.get('title') or ''} {h.get('description') or ''} {u}"
        if _reject_serp_for_project_state(blob, project_state):
            continue
        seen.add(u)
        out.append(h)
        if len(out) >= limit:
            break
    return out


def _with_context(base: str, ctx: Optional[str], max_len: int = 500) -> str:
    """Append contractor/site context to a search line without exceeding common API limits."""
    b = (base or "").strip()
    if not ctx or not str(ctx).strip():
        return b[:max_len]
    c = " ".join(str(ctx).split())
    sep = " | Site/job context: "
    room = max_len - len(b) - len(sep)
    if room < 24:
        return b[:max_len]
    if len(c) > room:
        c = c[: max(0, room - 1)] + "…"
    out = f"{b}{sep}{c}"
    return out[:max_len]


def _jurisdiction_spelling_hint(hits: List[Dict[str, Optional[str]]]) -> str:
    """Pull a few words from top hit titles to steer the follow-up local query."""
    for h in hits[:2]:
        t = h.get("title") or ""
        t = t.strip()
        if len(t) > 8:
            return t[:100]
    return ""


def _fallback_official_query(base: str) -> str:
    """
    Unscoped follow-up (no `site:`): bias toward the municipality's own official entry point.

    Ensures the keyword *official* and phrases that steer SERP to the city's government
    landing page (.gov or official portal), not blogs or listicles.
    """
    b = (base or "").strip()
    if not re.search(r"\bofficial\b", b, re.IGNORECASE):
        b = f"{b} official".strip()
    if not re.search(r"\blanding\s+page\b", b, re.IGNORECASE):
        b = f"{b} city government landing page".strip()
    return b


def _dedupe_take(
    hits: List[Dict[str, Optional[str]]],
    limit: int,
) -> List[Dict[str, Optional[str]]]:
    seen: set[str] = set()
    out: List[Dict[str, Optional[str]]] = []
    for h in hits:
        u = h.get("url")
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(h)
        if len(out) >= limit:
            break
    return out


def _scout_search(
    fc: Firecrawl,
    query: str,
    *,
    user_limit: int,
    project_state: Optional[str] = None,
    domain_scope: Optional[str] = None,
) -> tuple[List[Dict[str, Optional[str]]], Dict[str, Any]]:
    """
    Universal Scout: **/v2/search** with ``sources=['web']`` and **no** bundled scrape.

    Optionally could pass ``SEARCH_BUNDLED_SCRAPE_OPTIONS`` as ``scrape_options`` so each SERP URL
    is scraped as a single page (still not a multi-page crawl — no ``maxDepth`` path here).

    Duplicate scoped queries reuse **semantic cache** rows (see ``semantic_scout_cache``) to cut
    repeat Firecrawl search cost within TTL.
    """
    api_limit = _effective_search_limit(user_limit)
    scope = domain_scope or SEARCH_DOMAIN_SCOPE
    primary_q = _append_scope(query, domain_scope=scope)
    meta: Dict[str, Any] = {
        "primary_query": primary_q,
        "fallback_used": False,
        "fallback_query": None,
        "firecrawl_mode": "search_web_serp_only",
        "firecrawl_limit": api_limit,
        "semantic_cache_hit": False,
    }

    if semantic_scout_cache_enabled():
        cached = _semantic_scout_cache_get(primary_q, user_limit, project_state)
        if cached is not None:
            hits_c, meta_c = cached
            out_m = dict(meta_c)
            out_m["semantic_cache_hit"] = True
            out_m.setdefault("primary_query", primary_q)
            return hits_c, out_m

    r = fc.search(
        primary_q,
        limit=api_limit,
        sources=["web"],
        location="US",
        scrape_options=None,
    )
    trusted = _filter_trusted(_web_hits_raw(r), user_limit, project_state=project_state)
    if trusted:
        if semantic_scout_cache_enabled():
            _semantic_scout_cache_set(primary_q, user_limit, project_state, trusted, dict(meta))
        return trusted, meta
    # Do not cache empty primary results — the fallback query may still yield trusted URLs.
    fb_core = _fallback_official_query(query)
    fb = _append_scope(fb_core, domain_scope=scope)
    meta["fallback_used"] = True
    meta["fallback_query"] = fb

    if semantic_scout_cache_enabled():
        cached_fb = _semantic_scout_cache_get(fb, user_limit, project_state)
        if cached_fb is not None:
            hits_f, meta_f = cached_fb
            out_m = dict(meta_f)
            out_m["semantic_cache_hit"] = True
            out_m["fallback_used"] = True
            out_m["fallback_query"] = fb
            return hits_f, out_m

    r2 = fc.search(
        fb,
        limit=api_limit,
        sources=["web"],
        location="US",
        scrape_options=None,
    )
    trusted_fb = _filter_trusted(_web_hits_raw(r2), user_limit, project_state=project_state)
    if semantic_scout_cache_enabled():
        meta_fb = dict(meta)
        _semantic_scout_cache_set(fb, user_limit, project_state, trusted_fb, meta_fb)
    return trusted_fb, meta


def _step_result_dict(
    hits: List[Dict[str, Optional[str]]],
    scout_meta: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "query": scout_meta["primary_query"],
        "results": hits,
        "fallback_used": scout_meta.get("fallback_used", False),
        "fallback_query": scout_meta.get("fallback_query"),
        "firecrawl_mode": scout_meta.get("firecrawl_mode"),
        "firecrawl_limit": scout_meta.get("firecrawl_limit"),
    }


def _final_scout_response(
    z: str,
    ctx: Optional[str],
    hits1: List[Dict[str, Optional[str]]],
    meta1: Dict[str, Any],
    hits2: List[Dict[str, Optional[str]]],
    meta2: Dict[str, Any],
    hits3: List[Dict[str, Optional[str]]],
    meta3: Dict[str, Any],
    *,
    site_address: Optional[str] = None,
    jurisdiction: Optional[Mapping[str, Any]] = None,
    ahj_identification: Optional[Mapping[str, Any]] = None,
    scout_profile: Optional[Mapping[str, Any]] = None,
    fast41_hits: Optional[List[Dict[str, Optional[str]]]] = None,
    fast41_meta: Optional[Dict[str, Any]] = None,
    zoning_hits: Optional[List[Dict[str, Optional[str]]]] = None,
    zoning_meta: Optional[Dict[str, Any]] = None,
    water_hits: Optional[List[Dict[str, Optional[str]]]] = None,
    water_meta: Optional[Dict[str, Any]] = None,
    aim_hits: Optional[List[Dict[str, Optional[str]]]] = None,
    aim_meta: Optional[Dict[str, Any]] = None,
    wue_hits: Optional[List[Dict[str, Optional[str]]]] = None,
    wue_meta: Optional[Dict[str, Any]] = None,
    dc_energy_hits: Optional[List[Dict[str, Optional[str]]]] = None,
    dc_energy_meta: Optional[Dict[str, Any]] = None,
    moratorium_hits: Optional[List[Dict[str, Optional[str]]]] = None,
    moratorium_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    addr = (site_address or "").strip()
    ju = dict(jurisdiction) if jurisdiction else None
    ahj = dict(ahj_identification) if ahj_identification else None
    wf: List[str] = []
    if ahj:
        city = (ahj.get("city") or "").strip() or "—"
        county = (ahj.get("county") or "").strip() or "—"
        mode = (ahj.get("mode") or "").strip()
        steer = "municipal/city" if mode == "city" else "county/unincorporated"
        wf.append(
            f"AHJ identification — **City**: {city}; **County**: {county} ({steer} building-code steering, ZIP {z})."
        )
    elif ju and ju.get("label"):
        wf.append(
            f"Location — {ju['label']}. "
            "Universal Scout search lines target the city vs county building department accordingly."
        )
    wf.extend(
        [
            "Fallback — If a scoped step returns no trusted URLs: follow-up search **retains** the step’s "
            "**site:** scope (see ``scout.search_domain_scope`` / zoning ``OPENGOV`` extension) and adds "
            "*official* / *city government landing page*.",
            "Universal Scout 1 — Jurisdiction: city/county AHJ hints (trusted hosts).",
            "Universal Scout 2 — Permits: **city** or **county** building department (steered from address).",
            "Universal Scout 3 — Building codes: **city-specific** (incorporated) or **county-specific** "
            "(unincorporated) adopted codes and amendments, plus **Code-Change Monitoring** cues "
            "(upcoming adoptions / council minutes keywords).",
        ]
    )
    prof_snap = _coerce_scout_profile(scout_profile)
    trades_nice = ", ".join(prof_snap["trades"]) if prof_snap["trades"] else "none selected"
    wf.append(
        f"Scout profile — **Trades**: {trades_nice}; **vertical**: {prof_snap['vertical']}; "
        f"**mission-critical DC scout**: {'on' if prof_snap['mission_critical_dc'] else 'off'}; "
        f"**job FAST-41 gate**: {'on' if prof_snap.get('job_fast41_eligible') else 'off'}."
    )
    if zoning_meta is not None:
        wf.append(
            "**Intelligence tier — Residential / building vertical:** Municode / `.gov` / **OpenGov** portal discovery "
            "for **setbacks**, yard lines, and codified zoning chapters."
        )
    if fast41_meta is not None:
        wf.append(
            "**Intelligence tier — Infrastructure / data center:** **FAST-41** / Title 41 **Permitting Council** "
            "federal permitting status cues"
            + (
                " (data-center pass includes **May 2026 rescission / FAST-41 Transparency Project** + moratorium-bill keywords)."
                if prof_snap["vertical"] == "data_center"
                else "."
            )
        )
    if water_meta is not None:
        wf.append(
            "**Intelligence tier — Utility-scale water:** cooling-water **withdrawal**, **NPDES** / discharge, "
            "and state **environmental quality** or **utility commission** signals (cross-reference with FAST-41 context)."
        )
    if aim_meta is not None:
        wf.append(
            "**MEP / refrigerant scout — AIM Act phasedown:** trusted-domain cues for EPA **AIM Act**, **SNAP**, "
            "and HFC **phasedown** applicability to chillers / mechanical changeouts (**AHJ-enforceability verify**)."
        )
    if wue_meta is not None:
        wf.append(
            "**Water performance overlays:** municipal **Water Usage Effectiveness (WUE)** mandates, reclaimed-water "
            "/ discharge expectations for hyperscale cooling — **local rule verify**."
        )
    if dc_energy_meta is not None:
        wf.append(
            "**Data Center Intelligence — State energy / grid:** ratepayer-protection pledges, **PSC/PUC** riders, "
            "and **interconnect deposit / surcharge** proceedings (CA/OH/UT/VA emphasis when applicable)."
        )
    if moratorium_meta is not None:
        wf.append(
            "**Data Center Intelligence — Local moratorium scout:** trusted-domain cues for **2026** township/county "
            "**pause / freeze / moratorium** language targeting hyperscale or AI infrastructure."
        )
    out: Dict[str, Any] = {
        "zip": z,
        "site_address": addr or None,
        "jurisdiction": ju,
        "scout_profile": prof_snap,
        "scout": {
            "mode": "search_web",
            "search_domain_scope": SEARCH_DOMAIN_SCOPE,
            "search_domain_scope_zoning_residential": SEARCH_DOMAIN_SCOPE_ZONING,
            "trust_policy": (
                "hostname ends with .gov, hostname contains municode, or hostname under .opengov.com "
                "(SERP scoped per step)"
            ),
            "sources": ["web"],
            "scrape_options": None,
            "max_depth_note": (
                "N/A — Universal Scout does not call Firecrawl crawl/map; depth 1 crawl would "
                "use max_discovery_depth on /v2/crawl, not used here."
            ),
            "exclude_external_links_note": (
                "N/A for SERP-only search. For crawl, omit following off-domain links via "
                "allow_external_links=False."
            ),
            "page_limit_per_search": {"min": _SEARCH_PAGE_LIMIT_MIN, "max": _SEARCH_PAGE_LIMIT_MAX},
            "bundled_single_page_scrape_options": (
                "disabled — SERP snippets only; see SEARCH_BUNDLED_SCRAPE_OPTIONS if re-enabled "
                "(markdown only, fast_mode, no links format, exclude_tags strips media/CSS)."
            ),
            "fallback": (
                "If a scoped step returns zero trusted URLs, Universal Scout runs a follow-up search that still "
                "appends (site:gov OR site:municode.com) and biases keywords toward *official* / *city government* "
                "(no fully unscoped web search)."
            ),
        },
        "enhanced_context_used": bool(ctx),
        "agentic_workflow": wf,
        "step_jurisdiction": _step_result_dict(hits1, meta1),
        "step_building_permits": _step_result_dict(hits2, meta2),
        "step_building_codes": _step_result_dict(hits3, meta3),
    }
    if fast41_meta is not None:
        out["step_federal_fast41"] = _step_result_dict(fast41_hits or [], fast41_meta)
    if zoning_meta is not None:
        out["step_residential_zoning"] = _step_result_dict(zoning_hits or [], zoning_meta)
    if water_meta is not None:
        out["step_data_center_water"] = _step_result_dict(water_hits or [], water_meta)
    if aim_meta is not None:
        out["step_refrigerant_aim_act"] = _step_result_dict(aim_hits or [], aim_meta)
    if wue_meta is not None:
        out["step_water_usage_effectiveness"] = _step_result_dict(wue_hits or [], wue_meta)
    if dc_energy_meta is not None:
        out["step_dc_state_energy"] = _step_result_dict(dc_energy_hits or [], dc_energy_meta)
    if moratorium_meta is not None:
        out["step_dc_local_moratorium"] = _step_result_dict(moratorium_hits or [], moratorium_meta)
    if ahj:
        out["step_ahj_identification"] = ahj
    return out


_FUTURE_YEAR_RE = re.compile(r"\b20(2[6-9]|3[0-9])\b")


def _blob_future_code_signal(blob: str) -> bool:
    """Heuristic: upcoming cycle language + future-looking edition years on NEC / building codes."""
    if not _FUTURE_YEAR_RE.search(blob or ""):
        return False
    b = (blob or "").lower()
    code_ok = any(
        x in b
        for x in (
            "nec",
            "national electrical code",
            "nfpa 70",
            "nfpa-70",
            "electrical code",
            "building code",
            "ibc",
            "irc",
            "energy code",
            "ordinance",
        )
    )
    if not code_ok:
        return False
    proc_ok = any(
        x in b
        for x in (
            "adopt",
            "adoption",
            "effective",
            "implement",
            "transition",
            "propose",
            "proposed",
            "ordinance",
            "council",
            "commission",
            "hearing",
            "reading",
            "agenda",
            "minutes",
            "workshop",
            "upcoming",
            "schedule",
            "scheduled",
            "future",
            "amendment",
            "code change",
            "cycle",
        )
    )
    span_ok = bool(
        re.search(r"\b20(2[6-9]|3[0-9])\b\s*.{0,72}\b(nec|nfpa\s*70|electrical\s+code)\b", b, re.I)
        or re.search(r"\b(nec|nfpa\s*70)\b\s*.{0,72}\b20(2[6-9]|3[0-9])\b", b, re.I)
    )
    return proc_ok or span_ok


def future_risk_alerts_from_raw(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Scan trusted scout rows for newer NEC / adoption-cycle signals (Code-Change Monitoring Agent)."""
    seen: set[str] = set()
    hits_out: List[Dict[str, Any]] = []
    for step_key in ("step_jurisdiction", "step_building_permits", "step_building_codes"):
        if len(hits_out) >= 10:
            break
        block = raw.get(step_key)
        if not isinstance(block, dict):
            continue
        for item in block.get("results") or []:
            if len(hits_out) >= 10:
                break
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            title = str(item.get("title") or "")
            desc = str(item.get("description") or "")
            blob = f"{title} {desc}"
            if not _blob_future_code_signal(blob):
                continue
            dedupe = url or f"{title}|{desc[:80]}"
            if dedupe in seen:
                continue
            seen.add(dedupe)
            hits_out.append(
                {
                    "step": step_key,
                    "title": title or url or "(untitled)",
                    "url": url,
                    "snippet": (desc or "")[:360],
                }
            )
    active = bool(hits_out)
    return {
        "active": active,
        "banner": "FUTURE RISK ALERT",
        "severity": "future_code_cycle_signal" if active else "none",
        "hits": hits_out,
        "notes": (
            "Automated scan of Universal Scout titles/snippets on trusted domains only. "
            "Confirm council actions and effective dates with the AHJ."
        ),
    }


def format_future_risk_markdown(fr: Dict[str, Any]) -> str:
    """Markdown block prepended to the Contractor Action Plan so PDF exports retain watchdog output."""
    if not fr.get("active"):
        return ""
    lines = [
        "### FUTURE RISK ALERT",
        "",
        "**Watchdog — Code-change monitoring:** Scout hits reference a **future code edition or adoption-cycle signal** "
        "(for example **2026 NEC** or a later cycle). Verify the **effective NEC edition** and **local amendments** with "
        "the AHJ before locking specifications or inspection expectations.",
        "",
        "**Automated source flags (review live pages):**",
        "",
    ]
    for h in fr.get("hits") or []:
        title = str(h.get("title") or "Source").strip()
        url = str(h.get("url") or "").strip()
        lines.append(f"- **{title}** — {url}" if url else f"- **{title}**")
    lines.extend(
        [
            "",
            "- [ ] **Mandatory:** Confirm jurisdiction **code adoption schedule** (readings, ordinance numbers, effective date) "
            "and whether **2026 NEC** (or newer) is pending vs currently enforced.",
            "",
        ]
    )
    return "\n".join(lines)


def iter_universal_scout(
    zip_code: str,
    *,
    search_limit: int,
    enhanced_context: str = "",
    site_address: Optional[str] = None,
    jurisdiction: Optional[Mapping[str, Any]] = None,
    ahj_identification: Optional[Mapping[str, Any]] = None,
    scout_profile: Optional[Mapping[str, Any]] = None,
):
    """
    Yield one event dict per Universal Scout step, then a terminal ``complete`` event.

    Events:
      - ``{"event": "step", "step": "<key>", "data": {...}}``
      - ``{"event": "complete", "raw": <full scout dict>}``

    When ``jurisdiction`` is present (from geocoding), Universal Scout search lines name the
    resolved **city** or **county** for permits and **building codes**. Optional
    ``ahj_identification`` is echoed into the final payload for the memo.

    ``scout_profile`` enables **Full MEP** trade scoping, **mission-critical data-center** code
    discovery, project **vertical**, **residential zoning** (building vertical), optional **FAST-41** tier
    when vertical is infra/DC **or** ``job_fast41_eligible`` is true (**>**100 MW / **>**$500 M data-center cues),
    **utility-scale water**, **EPA AIM Act phasedown** refrigerant scout, **WUE / water-use** overlays, plus
    (data_center vertical only) state energy rider and moratorium passes.
    """
    z = normalize_us_zip(zip_code)
    ctx = (enhanced_context or "").strip() or None
    fc = _get_client()
    addr = (site_address or "").strip() or None
    ju: Optional[Mapping[str, Any]] = jurisdiction if jurisdiction else None
    ahj_snap: Optional[Mapping[str, Any]] = ahj_identification if ahj_identification else None
    prof = _coerce_scout_profile(scout_profile)
    infra_tier = prof["vertical"] in ("infrastructure", "data_center") or bool(prof.get("job_fast41_eligible"))

    st_for_filter: Optional[str] = None
    if ju:
        st_for_filter = str(ju.get("state") or ju.get("state_short") or "").strip() or None

    q1_core, q2_core, q3_core = _scout_queries_for_location(z, addr, ju, scout_profile=prof)
    q1 = _with_context(q1_core, ctx)
    hits1, meta1 = _scout_search(fc, q1, user_limit=search_limit, project_state=st_for_filter)
    yield {"event": "step", "step": "step_jurisdiction", "data": _step_result_dict(hits1, meta1)}
    hint = _jurisdiction_spelling_hint(hits1)

    if hint:
        q2 = _with_context(f"{q2_core} Context from web: {hint}", ctx)
    else:
        q2 = _with_context(q2_core, ctx)
    hits2, meta2 = _scout_search(fc, q2, user_limit=search_limit, project_state=st_for_filter)
    yield {"event": "step", "step": "step_building_permits", "data": _step_result_dict(hits2, meta2)}

    q3 = _with_context(q3_core, ctx)
    hits3, meta3 = _scout_search(fc, q3, user_limit=search_limit, project_state=st_for_filter)
    yield {"event": "step", "step": "step_building_codes", "data": _step_result_dict(hits3, meta3)}

    # Pro light scout: core 3 passes only (AHJ / permits / codes) — skip zoning + infra/DC tiers
    if prof.get("light_scout"):
        full = _final_scout_response(
            z,
            ctx,
            hits1,
            meta1,
            hits2,
            meta2,
            hits3,
            meta3,
            site_address=addr,
            jurisdiction=ju,
            ahj_identification=ahj_snap,
            scout_profile=prof,
        )
        if isinstance(full, dict):
            full["light_scout"] = True
            full["scout_mode"] = "light"
        yield {"event": "complete", "raw": full}
        return

    zip_tag = f"ZIP {z}"
    city_j = str(ju.get("city") or "") if ju else ""
    county_j = str(ju.get("county") or "") if ju else ""
    st_j = str(ju.get("state") or ju.get("state_short") or "") if ju else ""
    mode_j = str(ju.get("mode") or "") if ju else ""

    zoning_hits: Optional[List[Dict[str, Optional[str]]]] = None
    zoning_meta: Optional[Dict[str, Any]] = None
    if prof["vertical"] == "building":
        qz_core = _residential_zoning_setback_query_line(
            zip_tag=zip_tag,
            city=city_j,
            county=county_j,
            st=st_j,
            mode=mode_j,
            site_address=addr,
        )
        qz = _with_context(qz_core, ctx)
        zoning_hits, zoning_meta = _scout_search(
            fc,
            qz,
            user_limit=search_limit,
            project_state=st_for_filter,
            domain_scope=SEARCH_DOMAIN_SCOPE_ZONING,
        )
        yield {"event": "step", "step": "step_residential_zoning", "data": _step_result_dict(zoning_hits, zoning_meta)}

    fast41_hits: Optional[List[Dict[str, Optional[str]]]] = None
    fast41_meta: Optional[Dict[str, Any]] = None
    water_hits: Optional[List[Dict[str, Optional[str]]]] = None
    water_meta: Optional[Dict[str, Any]] = None
    aim_hits: Optional[List[Dict[str, Optional[str]]]] = None
    aim_meta: Optional[Dict[str, Any]] = None
    wue_hits: Optional[List[Dict[str, Optional[str]]]] = None
    wue_meta: Optional[Dict[str, Any]] = None
    if infra_tier:
        q4_core = _fast41_query_line(
            zip_tag=zip_tag,
            city=city_j,
            county=county_j,
            st=st_j,
            mode=mode_j,
            site_address=addr,
            vertical=prof["vertical"],
        )
        q4 = _with_context(q4_core, ctx)
        fast41_hits, fast41_meta = _scout_search(
            fc, q4, user_limit=search_limit, project_state=st_for_filter
        )
        yield {"event": "step", "step": "step_federal_fast41", "data": _step_result_dict(fast41_hits, fast41_meta)}

        qw_core = _data_center_utility_water_query_line(
            zip_tag=zip_tag,
            city=city_j,
            county=county_j,
            st=st_j,
            mode=mode_j,
            site_address=addr,
            vertical=prof["vertical"],
        )
        qw = _with_context(qw_core, ctx)
        water_hits, water_meta = _scout_search(
            fc, qw, user_limit=search_limit, project_state=st_for_filter
        )
        yield {"event": "step", "step": "step_data_center_water", "data": _step_result_dict(water_hits, water_meta)}

        qa_core = _refrigerant_aim_act_query_line(
            zip_tag=zip_tag,
            city=city_j,
            county=county_j,
            st=st_j,
            mode=mode_j,
            site_address=addr,
        )
        qa = _with_context(qa_core, ctx)
        aim_hits, aim_meta = _scout_search(fc, qa, user_limit=search_limit, project_state=st_for_filter)
        yield {"event": "step", "step": "step_refrigerant_aim_act", "data": _step_result_dict(aim_hits, aim_meta)}

        qwue_core = _water_usage_effectiveness_query_line(
            zip_tag=zip_tag,
            city=city_j,
            county=county_j,
            st=st_j,
            mode=mode_j,
            site_address=addr,
        )
        qwue = _with_context(qwue_core, ctx)
        wue_hits, wue_meta = _scout_search(fc, qwue, user_limit=search_limit, project_state=st_for_filter)
        yield {"event": "step", "step": "step_water_usage_effectiveness", "data": _step_result_dict(wue_hits, wue_meta)}

    dc_energy_hits: Optional[List[Dict[str, Optional[str]]]] = None
    dc_energy_meta: Optional[Dict[str, Any]] = None
    moratorium_hits: Optional[List[Dict[str, Optional[str]]]] = None
    moratorium_meta: Optional[Dict[str, Any]] = None
    if prof["vertical"] == "data_center":
        qe_core = _dc_state_energy_query_line(
            zip_tag=zip_tag,
            city=city_j,
            county=county_j,
            st=st_j,
            mode=mode_j,
            site_address=addr,
        )
        qe = _with_context(qe_core, ctx)
        dc_energy_hits, dc_energy_meta = _scout_search(
            fc, qe, user_limit=search_limit, project_state=st_for_filter
        )
        yield {"event": "step", "step": "step_dc_state_energy", "data": _step_result_dict(dc_energy_hits, dc_energy_meta)}

        qm_core = _dc_local_moratorium_query_line(
            zip_tag=zip_tag,
            city=city_j,
            county=county_j,
            st=st_j,
            mode=mode_j,
            site_address=addr,
        )
        qm = _with_context(qm_core, ctx)
        moratorium_hits, moratorium_meta = _scout_search(
            fc, qm, user_limit=search_limit, project_state=st_for_filter
        )
        yield {"event": "step", "step": "step_dc_local_moratorium", "data": _step_result_dict(moratorium_hits, moratorium_meta)}

    full = _final_scout_response(
        z,
        ctx,
        hits1,
        meta1,
        hits2,
        meta2,
        hits3,
        meta3,
        site_address=addr,
        jurisdiction=ju,
        ahj_identification=ahj_snap,
        scout_profile=prof,
        fast41_hits=fast41_hits,
        fast41_meta=fast41_meta,
        zoning_hits=zoning_hits,
        zoning_meta=zoning_meta,
        water_hits=water_hits,
        water_meta=water_meta,
        aim_hits=aim_hits,
        aim_meta=aim_meta,
        wue_hits=wue_hits,
        wue_meta=wue_meta,
        dc_energy_hits=dc_energy_hits,
        dc_energy_meta=dc_energy_meta,
        moratorium_hits=moratorium_hits,
        moratorium_meta=moratorium_meta,
    )
    yield {"event": "complete", "raw": full}


def search_local_building_codes_by_zip(
    zip_code: str,
    *,
    search_limit: int = 5,
    enhanced_context: str = "",
    scout_profile: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Universal Scout workflow (ZIP-centric — three core passes plus vertical intelligence tiers):

    1. Jurisdiction hints for the ZIP (trusted domains only).
    2. Building department / permits for that area.
    3. Adopted codes and amendments.
    4. **Building** vertical: **step_residential_zoning** (Municode / .gov / OpenGov setbacks & yard lines).
    5. **Infrastructure / data center** vertical: **step_federal_fast41** and **step_data_center_water**
       (utility-scale cooling-water / NPDES / state environmental cues).

    Each step uses Firecrawl **/v2/search** (``web`` source only): URL + snippet discovery
    without bundled full-page scrape; capped at a few SERP rows per query.
    """
    for ev in iter_universal_scout(
        zip_code,
        search_limit=search_limit,
        enhanced_context=enhanced_context,
        scout_profile=scout_profile,
    ):
        if ev.get("event") == "complete":
            return ev["raw"]
    raise RuntimeError("Universal Scout completed without a terminal event")
