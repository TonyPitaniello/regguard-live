"""
IC-only local + ultralocal scout deepen.

Runs after Universal Scout (full) on generate_ic_report paths:
  - Local: deepen AHJ / fee / inspection / code amendment SERP + optional page confirm
  - Ultralocal: HOA / CID / MUD / PID / township / subdivision / neighborhood covenants

On-city pages are stored on ultralocal_scout.pages. They do not replace the city-pack risks.
"""

from __future__ import annotations

import logging
import os
import re
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
            f"{loc} city county special district overlay zoning floodplain parcel",
        ),
        (
            "ultralocal_neighborhood",
            f"{street} {city} {state} neighborhood association building restrictions",
        ),
    ]


def _city_tokens(city: str) -> List[str]:
    return [t for t in re.split(r"[^a-z0-9]+", (city or "").lower()) if t]


def _mentions_site_city(text: str, city: str) -> bool:
    """True when text names this city, including cityofallen and fortworthtexas.gov."""
    words = _city_tokens(city)
    if not words:
        return False
    tokens = _city_tokens(text)
    glued = "".join(words)
    n = len(words)
    for i in range(0, max(0, len(tokens) - n + 1)):
        if tokens[i : i + n] == words:
            return True
    for token in tokens:
        if token in (glued, f"cityof{glued}", f"{glued}texas", f"{glued}tx"):
            return True
    return False


_PLACE_QUALIFIERS = {"south", "north", "east", "west", "port", "lake"}


def _qualified_other_city(text: str, city: str) -> bool:
    """South Houston is not Houston. The extra word is a different city."""
    words = _city_tokens(city)
    if len(words) != 1:
        return False
    tokens = _city_tokens(text)
    target = words[0]
    for i, token in enumerate(tokens):
        if token == target and i > 0 and tokens[i - 1] in _PLACE_QUALIFIERS:
            return True
    return False


_PROMPT_LEAKS = (
    "for each local amendment",
    "in the digest",
    "if scout results",
    "use only resources that apply",
    "add explicit",
    "search results",
    "county engineer",
)


def customer_line_blocked(text: str, city: str = "") -> bool:
    """Scraped chrome, another city, or a prompt line does not belong on a receipt."""
    raw = text or ""
    if _excerpt_is_page_chrome(raw):
        return True
    low = raw.lower()
    if any(marker in low for marker in _PROMPT_LEAKS):
        return True
    if city and _qualified_other_city(raw, city):
        return True
    return False


def _excerpt_is_page_chrome(text: str) -> bool:
    raw = text or ""
    low = raw.lower()
    if "skip to main content" in low or "![](" in raw or "](http" in raw:
        return True
    return raw.count("](") >= 2


def _foreign_municipal_page(title: str, snippet: str, url: str, city: str) -> bool:
    """
    The Allen code query ranks City of Fort Worth's electrical-code page, because
    that page is the strong DFW hit for "NEC" and "local amendments." The search
    result is copied in with no check that the page is this city's code.

    Drop it when the title or the URL is another municipality. A snippet that
    merely echoes the query ("Allen") does not make a Fort Worth page local.
    """
    if not (city or "").strip():
        return False
    identity = f"{title} {url}"
    if _qualified_other_city(identity, city):
        return True
    if "county engineer" in identity.lower():
        return True
    if _mentions_site_city(identity, city):
        return False
    if re.search(r"\bcity of\b", (title or "").lower()):
        return True
    hostpath = (url or "").lower()
    if any(marker in hostpath for marker in ("texas.gov", "cityof", "municode.com/tx/")):
        return True
    if re.search(r"\bcity of\b", (snippet or "").lower()) and not _mentions_site_city(snippet, city):
        return True
    return False


def _hit_to_killer(hit: Dict[str, Any], bucket: str, *, city: str = "") -> Optional[Dict[str, Any]]:
    title = str(hit.get("title") or hit.get("name") or "").strip()
    url = str(hit.get("url") or hit.get("link") or hit.get("source_url") or "").strip()
    snippet = str(hit.get("description") or hit.get("snippet") or hit.get("markdown") or "").strip()
    if not title and not url:
        return None
    if _excerpt_is_page_chrome(title) or _excerpt_is_page_chrome(snippet):
        return None
    if _foreign_municipal_page(title, snippet, url, city):
        return None
    label = {
        "local_ahj": "Local AHJ / fees",
        "local_codes": "Local code amendments",
        "ultralocal_hoa": "HOA / covenants",
        "ultralocal_mud": "MUD / PID / CID",
        "ultralocal_township": "Overlay / special district",
        "ultralocal_neighborhood": "Neighborhood restrictions",
    }.get(bucket, "Ultralocal")
    detail = (snippet[:220] + "…") if len(snippet) > 220 else snippet
    blob = f"{title} {snippet}".lower()
    directory = any(
        needle in blob
        for needle in ("business hours", "hours of", "get permits", "a.m.", "p.m.")
    )
    residential_rate = bucket == "ultralocal_mud" and (
        "per month" in blob or "residents" in blob
    )
    if directory or residential_rate:
        return None
    priority = "HIGH" if bucket.startswith("ultralocal") else "MEDIUM"
    return {
        "title": f"[{label}] {title or url}"[:160],
        "detail": detail,
        "priority": priority,
        "verified": False,
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
        hits = [
            h
            for h in _search_bucket(query, limit=4)
            if not _foreign_municipal_page(
                str(h.get("title") or h.get("name") or ""),
                str(h.get("description") or h.get("snippet") or h.get("markdown") or ""),
                str(h.get("url") or h.get("link") or h.get("source_url") or ""),
                city,
            )
        ]
        buckets[bucket] = hits
        all_hits.extend(hits)
        for h in hits[:3]:
            k = _hit_to_killer(h, bucket, city=city)
            if k:
                killers.append(k)

    confirmed = _confirm_top_urls(all_hits, max_pages=2)
    pages: List[Dict[str, str]] = []
    seen_urls = set()
    for k in killers:
        url = str(k.get("source_url") or "").strip()
        title = str(k.get("title") or "").strip()
        if not url.startswith("http") or url in seen_urls:
            continue
        if _excerpt_is_page_chrome(title) or _excerpt_is_page_chrome(str(k.get("detail") or "")):
            continue
        seen_urls.add(url)
        pages.append({"title": title[:140], "url": url})

    out["ultralocal_scout"] = {
        "enabled": True,
        "city": city,
        "state": state,
        "zip": zip_code,
        "buckets": {k: len(v) for k, v in buckets.items()},
        "hit_count": sum(len(v) for v in buckets.values()),
        "confirmed_pages": confirmed,
        "pages": pages[:8],
        "killers_added": 0,
    }
    out["scout_locality_depth"] = "local_ultralocal"
    note = str(out.get("depth_claim_note") or "").strip()
    add = (
        f"IC scout kept {len(pages)} on-city pages. "
        "HOA, MUD, and neighborhood pages are listed only when the page names this city."
    )
    if add not in note:
        out["depth_claim_note"] = f"{note} {add}".strip() if note else add

    logger.info(
        "IC local/ultralocal scout city=%s zip=%s hits=%s killers=%s confirmed=%s",
        city,
        zip_code,
        sum(len(v) for v in buckets.values()),
        len(killers),
        len(confirmed),
    )
    return out
