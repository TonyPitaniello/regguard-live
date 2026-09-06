"""
IC-only local + ultralocal scout deepen.

Runs after Universal Scout (full) on generate_ic_report paths:
  - Local: deepen AHJ / fee / inspection / code amendment SERP + optional page confirm
  - Ultralocal: HOA / CID / MUD / PID / township / subdivision / neighborhood covenants

Findings merge into margin_killers, gotcha_watchlist, and ultralocal_scout for PDFs.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _env_on(name: str, default: str = "1") -> bool:
    return (os.getenv(name) or default).strip().lower() in ("1", "true", "yes", "on")


def _query_lines(city: str, state: str, zip_code: str, address: str) -> List[Tuple[str, str]]:
    """(bucket, query) pairs for IC local + ultralocal."""
    loc = f"{city} {state} {zip_code}".strip()
    street = (address or "").split(",")[0].strip() or loc
    return [
        (
            "local_ahj",
            f"{loc} building permit fees inspection schedule official site",
        ),
        (
            "local_codes",
            f"{loc} local amendments IBC NEC electrical permit requirements",
        ),
        (
            "ultralocal_hoa",
            f"{street} {loc} HOA covenants deed restrictions architectural review",
        ),
        (
            "ultralocal_mud",
            f"{loc} MUD PID CID municipal utility district assessment fees",
        ),
        (
            "ultralocal_township",
            f"{loc} township special district overlay zoning floodplain parcel",
        ),
        (
            "ultralocal_neighborhood",
            f"{street} {city} {state} neighborhood association building restrictions",
        ),
    ]


def _hit_to_killer(hit: Dict[str, Any], bucket: str) -> Optional[Dict[str, Any]]:
    title = str(hit.get("title") or hit.get("name") or "").strip()
    url = str(hit.get("url") or hit.get("link") or hit.get("source_url") or "").strip()
    snippet = str(hit.get("description") or hit.get("snippet") or hit.get("markdown") or "").strip()
    if not title and not url:
        return None
    label = {
        "local_ahj": "Local AHJ / fees",
        "local_codes": "Local code amendments",
        "ultralocal_hoa": "HOA / covenants",
        "ultralocal_mud": "MUD / PID / CID",
        "ultralocal_township": "Township / overlay",
        "ultralocal_neighborhood": "Neighborhood restrictions",
    }.get(bucket, "Ultralocal")
    detail = (snippet[:220] + "…") if len(snippet) > 220 else snippet
    return {
        "title": f"[{label}] {title or url}"[:160],
        "detail": detail,
        "priority": "HIGH" if bucket.startswith("ultralocal") else "MEDIUM",
        "verified": bool(url.startswith("http")),
        "source_url": url or None,
        "source_label": label,
        "citation_tier": "link" if url.startswith("http") else "unverified",
        "ultralocal_bucket": bucket,
    }


def _search_bucket(query: str, limit: int = 4) -> List[Dict[str, Any]]:
    """Best-effort Firecrawl / scout search; soft-fail to []."""
    try:
        from scraper import _get_client, _scout_search

        fc = _get_client()
        hits, _meta = _scout_search(fc, query, user_limit=limit, project_state=None)
        return [h for h in (hits or []) if isinstance(h, dict)]
    except Exception as e:
        logger.warning("IC ultralocal search failed for %r: %s", query[:80], e)
        return []


def _confirm_top_urls(hits: List[Dict[str, Any]], max_pages: int = 2) -> List[Dict[str, Any]]:
    """Optional cheap markdown confirm on top URLs (IC only)."""
    out: List[Dict[str, Any]] = []
    if not _env_on("IC_ULTRALOCAL_PAGE_CONFIRM", "1"):
        return out
    try:
        from cheap_page_confirm import fetch_page_markdown
    except Exception:
        return out
    seen = set()
    for hit in hits:
        url = str(hit.get("url") or hit.get("link") or "").strip()
        if not url.startswith("http") or url in seen:
            continue
        seen.add(url)
        try:
            md = fetch_page_markdown(url, pack_urls=[], max_chars=6_000) or ""
        except Exception:
            md = ""
        if not md or len(md) < 80:
            continue
        out.append(
            {
                "url": url,
                "title": str(hit.get("title") or url)[:120],
                "markdown_chars": len(md),
                "excerpt": md[:400],
            }
        )
        if len(out) >= max_pages:
            break
    return out


def run_ic_local_ultralocal_scout(
    analysis: Dict[str, Any],
    *,
    address: str = "",
    city: str = "",
    state: str = "",
    zip_code: str = "",
) -> Dict[str, Any]:
    """
    Deepen IC analysis with local + ultralocal scout hits.
    Safe to call on any paid path; intended for force_scout / IC only.
    """
    if not _env_on("IC_ULTRALOCAL_SCOUT", "1"):
        return analysis

    out = dict(analysis or {})
    pi = out.get("project_info") or {}
    city = (city or str(pi.get("city") or "")).strip()
    state = (state or str(pi.get("state") or "")).strip()
    zip_code = (zip_code or str(pi.get("zip") or "")).strip()
    address = (address or str(pi.get("address") or "")).strip()
    if not (city or zip_code):
        return out

    buckets: Dict[str, List[Dict[str, Any]]] = {}
    killers: List[Dict[str, Any]] = []
    all_hits: List[Dict[str, Any]] = []

    for bucket, query in _query_lines(city, state, zip_code, address):
        hits = _search_bucket(query, limit=4)
        buckets[bucket] = hits
        all_hits.extend(hits)
        for h in hits[:3]:
            k = _hit_to_killer(h, bucket)
            if k:
                killers.append(k)

    confirmed = _confirm_top_urls(all_hits, max_pages=2)

    existing = [k for k in (out.get("margin_killers") or []) if isinstance(k, dict)]
    # Prefer new ultralocal flags first, keep prior killers
    merged_killers = killers[:8] + existing
    # Dedupe by title
    seen_t = set()
    deduped: List[Dict[str, Any]] = []
    for k in merged_killers:
        t = str(k.get("title") or "").lower()
        if not t or t in seen_t:
            continue
        seen_t.add(t)
        deduped.append(k)
    out["margin_killers"] = deduped[:12]

    gotcha = out.get("gotcha_watchlist") if isinstance(out.get("gotcha_watchlist"), dict) else {}
    items = [i for i in (gotcha.get("items") or []) if isinstance(i, dict)]
    for k in killers[:6]:
        items.append(
            {
                "title": k.get("title"),
                "detail": k.get("detail"),
                "severity": k.get("priority") or "HIGH",
                "source_url": k.get("source_url"),
                "verified": k.get("verified"),
            }
        )
    out["gotcha_watchlist"] = {
        **gotcha,
        "title": gotcha.get("title") or "Local + ultralocal gotcha watchlist",
        "items": items[:16],
    }

    out["ultralocal_scout"] = {
        "enabled": True,
        "city": city,
        "state": state,
        "zip": zip_code,
        "buckets": {k: len(v) for k, v in buckets.items()},
        "hit_count": sum(len(v) for v in buckets.values()),
        "confirmed_pages": confirmed,
        "killers_added": len(killers),
    }
    out["scout_locality_depth"] = "local_ultralocal"
    # Surface on depth badge note
    note = str(out.get("depth_claim_note") or "").strip()
    add = (
        f"IC local + ultralocal scout: {sum(len(v) for v in buckets.values())} sources "
        f"across AHJ/fees, codes, HOA/MUD/township overlays."
    )
    if add not in note:
        out["depth_claim_note"] = f"{note} {add}".strip() if note else add

    # Feed local_pack gotchas when thin
    local = out.get("local_pack") if isinstance(out.get("local_pack"), dict) else {}
    local_gotchas = [g for g in (local.get("gotchas") or []) if isinstance(g, dict)]
    if len(local_gotchas) < 3:
        for k in killers[:5]:
            local_gotchas.append(
                {
                    "title": k.get("title"),
                    "detail": k.get("detail"),
                    "source_url": k.get("source_url"),
                    "verified": k.get("verified"),
                }
            )
        local = dict(local)
        local["gotchas"] = local_gotchas[:12]
        local["ultralocal"] = True
        out["local_pack"] = local

    logger.info(
        "IC local/ultralocal scout city=%s zip=%s hits=%s killers=%s confirmed=%s",
        city,
        zip_code,
        sum(len(v) for v in buckets.values()),
        len(killers),
        len(confirmed),
    )
    return out
