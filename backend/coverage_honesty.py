"""
Coverage honesty helpers — premortem kill-risk mitigations.

- coverage_tier badges (full_pack / portal_seed / federal_state)
- strip fee amounts outside full citeable packs
- score/filter generic .gov SERP hits
- daily cap for generic SERP
"""

from __future__ import annotations

import os
import re
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

_SERP_LOCK = threading.Lock()
_SERP_DAY = ""
_SERP_COUNT = 0


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name) or default)
    except ValueError:
        return default


def generic_serp_daily_cap() -> int:
    """Max generic .gov SERP discoveries per process per UTC day (0 = unlimited)."""
    return max(0, _env_int("FREE_TRIAL_GENERIC_SERP_DAILY_CAP", 200))


def generic_serp_budget_available() -> bool:
    cap = generic_serp_daily_cap()
    if cap <= 0:
        return True
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with _SERP_LOCK:
        global _SERP_DAY, _SERP_COUNT
        if _SERP_DAY != day:
            _SERP_DAY = day
            _SERP_COUNT = 0
        return _SERP_COUNT < cap


def record_generic_serp_use() -> None:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with _SERP_LOCK:
        global _SERP_DAY, _SERP_COUNT
        if _SERP_DAY != day:
            _SERP_DAY = day
            _SERP_COUNT = 0
        _SERP_COUNT += 1


def coverage_tier_for(
    *,
    citeable_local: bool = False,
    portal_only: bool = False,
    pack: Optional[Dict[str, Any]] = None,
) -> str:
    pack = pack or {}
    if citeable_local or bool(pack.get("citeable")):
        return "full_pack"
    if portal_only or bool(pack.get("portal_only")) or bool(pack.get("serp_discovered_portal")):
        return "portal_seed"
    return "federal_state"


COVERAGE_BADGES = {
    "full_pack": {
        "label": "Full city pack",
        "short": "Full pack",
        "tone": "success",
        "warning": (
            "Curated local fees/gotchas + federal/state. Still confirm dollar amounts on the "
            "official AHJ schedule before bid."
        ),
    },
    "portal_seed": {
        "label": "Portal seed — confirm fees",
        "short": "Portal seed",
        "tone": "warning",
        "warning": (
            "AHJ portal link only — not Plano-depth. No curated local fees or ordinance gotchas. "
            "Confirm all fees and amendments on the official schedule before bid."
        ),
    },
    "federal_state": {
        "label": "Federal / state only",
        "short": "Federal/state",
        "tone": "neutral",
        "warning": (
            "No curated local AHJ pack for this city. Federal (+ state when curated) lines only. "
            "Treat local requirements as Unverified until you confirm with the AHJ."
        ),
    },
}


def build_coverage_block(
    *,
    tier: str,
    coverage_note: str = "",
    pack_key: str = "",
    state_citeable: bool = False,
) -> Dict[str, Any]:
    meta = COVERAGE_BADGES.get(tier) or COVERAGE_BADGES["federal_state"]
    note = (coverage_note or "").strip() or meta["warning"]
    return {
        "tier": tier,
        "badge": meta["label"],
        "badge_short": meta["short"],
        "tone": meta["tone"],
        "warning": meta["warning"],
        "note": note,
        "pack_key": pack_key or None,
        "state_citeable": bool(state_citeable),
        "fees_allowed": tier == "full_pack",
        "depth_equals_beachhead": tier == "full_pack",
    }


def strip_non_pack_fees(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    P1: Never show fee dollar amounts outside full citeable city packs.
    Portal seeds / federal-state keep portal links but empty fee_card.fees.
    """
    if not isinstance(analysis, dict):
        return analysis
    cov = analysis.get("coverage") or {}
    tier = cov.get("tier") or ""
    if not tier:
        # Infer from jurisdiction / free_confirm
        j = analysis.get("jurisdiction") or {}
        fc = analysis.get("free_confirm") or {}
        if j.get("citeable_local") or fc.get("citeable"):
            tier = "full_pack"
        elif j.get("portal_only_local") or fc.get("portal_only") or fc.get("generic_serp_portal"):
            tier = "portal_seed"
        else:
            tier = "federal_state"

    if tier == "full_pack":
        return analysis
    # Catalog-backed beachhead fees (ZIP AHJ) — keep when fee_card already citeable
    if (analysis.get("fee_card") or {}).get("citeable_coverage") and (
        (analysis.get("ahj") or {}).get("ahj_id")
        or (analysis.get("gotcha_watchlist") or {}).get("pack_key")
    ):
        return analysis
    # Paid local confirm grounded fees — keep them
    if tier == "paid_local" or (analysis.get("finops_mode") == "paid_local_confirm" and (
        (analysis.get("fee_card") or {}).get("paid_local_confirm")
        or (analysis.get("paid_local") or {}).get("fee_rows_extracted")
    )):
        return analysis

    fee_card = dict(analysis.get("fee_card") or {})
    if fee_card.get("fees"):
        fee_card["fees"] = []
        fee_card["fees_stripped"] = True
        fee_card["disclaimer"] = (
            "Fee amounts hidden — this lookup is not a full citeable city pack. "
            "Open the AHJ portal and confirm the official schedule before bid."
        )
        fee_card["citeable_coverage"] = False
        analysis["fee_card"] = fee_card

    # Drop punch lines that look like fee extracts with dollar amounts
    punch = analysis.get("punch_list") or {}
    items = list(punch.get("punch_list") or [])
    cleaned = []
    for row in items:
        if not isinstance(row, dict):
            cleaned.append(row)
            continue
        task = str(row.get("task") or "")
        if "fee extract" in task.lower() or (
            "confirm ahj fee" in task.lower() and "$" in task
        ):
            continue
        cleaned.append(row)
    punch["punch_list"] = cleaned
    analysis["punch_list"] = punch
    return analysis


_PERMIT_RE = re.compile(
    r"permit|building|development|inspection|planning|code\s*enforcement|dbi|sdci|ladbs",
    re.I,
)


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _city_tokens(city: str) -> List[str]:
    raw = re.sub(r"[^a-z0-9\s]", " ", (city or "").lower())
    parts = [p for p in raw.split() if len(p) >= 3 and p not in {"the", "city", "of", "and"}]
    if not parts and city:
        parts = [re.sub(r"[^a-z0-9]", "", city.lower())[:12]]
    return parts


def score_gov_serp_hit(
    hit: Dict[str, Any],
    *,
    city: str = "",
    state: str = "",
) -> int:
    """
    Higher is better. Prefer city-named hosts and permit/building titles.
    Reject (score < 0) weak / wrong-agency hits.
    """
    url = str(hit.get("url") or "")
    title = str(hit.get("title") or "")
    snippet = str(hit.get("snippet") or hit.get("description") or "")
    blob = f"{title} {snippet} {url}"
    host = _host(url)
    if not host:
        return -100

    score = 0
    if host.endswith(".gov") or ".gov." in host:
        score += 20
    elif any(x in host for x in (".us", "city", "county", "municip")):
        score += 8
    else:
        return -50

    if _PERMIT_RE.search(blob):
        score += 40
    else:
        # P3: require building/permit signal in title/url
        return -20

    tokens = _city_tokens(city)
    host_compact = host.replace("-", "").replace(".", "")
    for tok in tokens:
        if tok in host or tok in host_compact:
            score += 35
            break
    else:
        # Title/snippet city mention is weaker than host match
        if any(tok in blob.lower() for tok in tokens):
            score += 10
        else:
            score -= 15

    st = (state or "").strip().lower()
    if st and (f".{st}." in f".{host}." or host.endswith(f".{st}.gov") or f"{st}.gov" in host):
        score += 10

    # Penalize obvious state-wide or federal agencies when looking for city AHJ
    if any(
        x in host
        for x in (
            "epa.gov",
            "osha.gov",
            "fema.gov",
            "ada.gov",
            "census.gov",
            "usa.gov",
        )
    ):
        score -= 40

    return score


def filter_gov_serp_hits(
    hits: List[Dict[str, Any]],
    *,
    city: str = "",
    state: str = "",
    limit: int = 1,
    min_score: int = 30,
) -> List[Dict[str, Any]]:
    ranked: List[Tuple[int, Dict[str, Any]]] = []
    for h in hits:
        if not isinstance(h, dict) or not h.get("url"):
            continue
        sc = score_gov_serp_hit(h, city=city, state=state)
        if sc >= min_score:
            ranked.append((sc, h))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return [h for _, h in ranked[:limit]]


def apply_coverage_honesty(
    analysis: Dict[str, Any],
    *,
    resolved: Optional[Dict[str, Any]] = None,
    pack: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Attach coverage block + strip non-pack fees. Safe to call multiple times."""
    if not isinstance(analysis, dict):
        return analysis
    resolved = resolved or {}
    pack = pack or (resolved.get("local") if resolved else None) or {}
    j_existing = analysis.get("jurisdiction") or {}

    citeable_local = bool(
        resolved.get("citeable_local")
        if resolved
        else j_existing.get("citeable_local")
    )
    portal_only = bool(
        resolved.get("portal_only_local")
        if resolved
        else j_existing.get("portal_only_local")
    ) or bool(pack.get("portal_only")) or bool(
        (analysis.get("free_confirm") or {}).get("generic_serp_portal")
    )

    tier = coverage_tier_for(
        citeable_local=citeable_local,
        portal_only=portal_only,
        pack=pack,
    )
    state_pack = (resolved.get("state_pack") if resolved else None) or {}
    note = str(
        resolved.get("coverage_note")
        or j_existing.get("coverage_note")
        or (analysis.get("free_confirm") or {}).get("coverage_note")
        or ""
    )
    analysis["coverage"] = build_coverage_block(
        tier=tier,
        coverage_note=note,
        pack_key=str(pack.get("pack_key") or j_existing.get("local_pack_key") or ""),
        state_citeable=bool(state_pack.get("citeable") or (analysis.get("state_card") or {}).get("citeable")),
    )
    # Mirror onto jurisdiction for older clients
    j = dict(j_existing)
    j["coverage_tier"] = tier
    j["coverage_badge"] = analysis["coverage"]["badge"]
    j["coverage_note"] = analysis["coverage"]["note"]
    j["portal_only_local"] = portal_only or tier == "portal_seed"
    j["citeable_local"] = citeable_local or tier == "full_pack"
    analysis["jurisdiction"] = j

    return strip_non_pack_fees(analysis)
