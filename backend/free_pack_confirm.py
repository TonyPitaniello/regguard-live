"""
Free-tier FinOps path: ZIP jurisdiction packs + city pack + optional cheap page
confirm + optional 1 allowlisted SERP confirm.
No Universal Scout, no Option A 6x env searches, no Firecrawl markdown rescrape
(unless FREE_TRIAL_MARKDOWN_CONFIRM=1).
Paid path stays pro_deep_analysis / full scout.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from city_packs import generic_thin_pack, resolve_city_pack

logger = logging.getLogger(__name__)


def _env_truthy(name: str, default: str = "0") -> bool:
    return (os.getenv(name) or default).strip().lower() in ("1", "true", "yes", "on")


def free_search_limit() -> int:
    try:
        return max(1, min(3, int(os.getenv("FREE_TRIAL_SEARCH_LIMIT") or "2")))
    except ValueError:
        return 2


def free_markdown_confirm_enabled() -> bool:
    """Default off — free path never markdown-rescrapes."""
    return _env_truthy("FREE_TRIAL_MARKDOWN_CONFIRM", "0")


def free_allowlist_search_enabled() -> bool:
    """One cheap Firecrawl /search against allowlisted AHJ host (default on)."""
    return _env_truthy("FREE_TRIAL_ALLOWLIST_SEARCH", "1")


def free_generic_serp_enabled() -> bool:
    """When no portal URL, one .gov SERP to discover an AHJ link (default on)."""
    return _env_truthy("FREE_TRIAL_GENERIC_SERP", "1")


def free_cheap_confirm_enabled() -> bool:
    """requests+markdown+LLM confirm (no Firecrawl scrape). Default on."""
    return _env_truthy("FREE_TRIAL_CHEAP_CONFIRM", "1")


def allowlisted_confirm_url(pack: Dict[str, Any]) -> str:
    ahj = pack.get("ahj") or {}
    return str(ahj.get("fees_url") or ahj.get("portal_url") or "").strip()


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _one_allowlisted_search(
    *,
    city: str,
    state: str,
    confirm_url: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """
    Single Firecrawl SERP call (no scrape_options / no markdown).
    Scoped to allowlisted host when possible.
    """
    if not confirm_url or not free_allowlist_search_enabled():
        return []
    api_key = (os.getenv("FIRECRAWL_API_KEY") or "").strip()
    if not api_key:
        return []

    host = _host(confirm_url)
    locality = f"{city}, {state}".strip(", ")
    if host:
        query = f"{locality} building permit fees site:{host}"
    else:
        query = f"{locality} building permit fees site:gov"

    try:
        from scraper import _get_client

        fc = _get_client()
        # SERP only — never bundle markdown scrape on free
        result = fc.search(
            query,
            limit=limit,
            sources=["web"],
            location="US",
            scrape_options=None,
        )
    except Exception as e:
        logger.warning("Free allowlist confirm search failed: %s", e)
        return []

    web = getattr(result, "web", None)
    if web is None and isinstance(result, dict):
        data = result.get("data") or result
        web = data.get("web") if isinstance(data, dict) else None
    if not web:
        return []

    out: List[Dict[str, Any]] = []
    for item in list(web)[:limit]:
        url = getattr(item, "url", None)
        title = getattr(item, "title", None)
        desc = getattr(item, "description", None) or getattr(item, "snippet", None)
        if isinstance(item, dict):
            url = url or item.get("url")
            title = title or item.get("title")
            desc = desc or item.get("description") or item.get("snippet")
        if not url:
            continue
        # Prefer hits on allowlisted host; still keep if .gov
        item_host = _host(str(url))
        if host and item_host and host not in item_host and not item_host.endswith(".gov"):
            continue
        out.append(
            {
                "url": str(url),
                "title": str(title or "AHJ confirm hit")[:160],
                "snippet": str(desc or "")[:240],
            }
        )
    return out


def _one_generic_gov_search(
    *,
    city: str,
    state: str,
    limit: int = 1,
) -> List[Dict[str, Any]]:
    """
    Single Firecrawl SERP to discover a .gov building-permit portal when we have
    no curated/metro URL. Cached via semantic scout cache when available.
    """
    if not free_generic_serp_enabled():
        return []
    from coverage_honesty import generic_serp_budget_available

    if not generic_serp_budget_available():
        logger.info("Generic .gov SERP skipped — daily cap reached")
        return []
    locality = f"{(city or '').strip()}, {(state or '').strip()}".strip(", ")
    if not locality or locality.lower() in ("local", ","):
        return []
    api_key = (os.getenv("FIRECRAWL_API_KEY") or "").strip()
    if not api_key:
        return []

    query = (
        f'{locality} ("building permit" OR "building department" OR '
        f'"development services" OR "building inspections") site:.gov'
    )
    try:
        from semantic_scout_cache import cache_get, cache_set

        cached = cache_get(query, limit, state)
        if cached:
            hits, _meta = cached
            return [
                {
                    "url": str(h.get("url") or ""),
                    "title": str(h.get("title") or "AHJ portal hit")[:160],
                    "snippet": str(h.get("snippet") or h.get("description") or "")[:240],
                }
                for h in hits
                if h.get("url")
            ][:limit]
    except Exception:
        pass

    try:
        from scraper import _get_client

        fc = _get_client()
        result = fc.search(
            query,
            limit=max(1, min(3, limit)),
            sources=["web"],
            location="US",
            scrape_options=None,
        )
    except Exception as e:
        logger.warning("Free generic .gov SERP failed: %s", e)
        return []

    web = getattr(result, "web", None)
    if web is None and isinstance(result, dict):
        data = result.get("data") or result
        web = data.get("web") if isinstance(data, dict) else None
    if not web:
        return []

    out: List[Dict[str, Any]] = []
    cache_rows: List[Dict[str, Optional[str]]] = []
    raw_hits: List[Dict[str, Any]] = []
    for item in list(web)[: max(3, min(5, limit * 3))]:
        url = getattr(item, "url", None)
        title = getattr(item, "title", None)
        desc = getattr(item, "description", None) or getattr(item, "snippet", None)
        if isinstance(item, dict):
            url = url or item.get("url")
            title = title or item.get("title")
            desc = desc or item.get("description") or item.get("snippet")
        if not url:
            continue
        raw_hits.append(
            {
                "url": str(url),
                "title": str(title or "AHJ portal hit")[:160],
                "snippet": str(desc or "")[:240],
            }
        )

    from coverage_honesty import filter_gov_serp_hits, record_generic_serp_use

    out = filter_gov_serp_hits(raw_hits, city=city, state=state, limit=limit, min_score=30)
    for row in out:
        cache_rows.append(
            {
                "url": row["url"],
                "title": row["title"],
                "snippet": row.get("snippet") or "",
                "description": row.get("snippet") or "",
            }
        )
    if out:
        record_generic_serp_use()
    if cache_rows:
        try:
            from semantic_scout_cache import cache_set

            cache_set(query, limit, state, cache_rows, {"source": "free_generic_gov_serp"})
        except Exception:
            pass
    return out[:limit]


def _punch_from_pack(
    pack: Dict[str, Any],
    *,
    city: str,
    state: str,
    confirm_hits: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    ahj = pack.get("ahj") or {}
    confirm_url = allowlisted_confirm_url(pack)
    citeable = bool(pack.get("citeable"))
    portal_only = bool(pack.get("portal_only"))

    # CRITICAL confirm line only when we have a real URL (pack, portal seed, or SERP).
    if confirm_url:
        items.append(
            {
                "priority": "CRITICAL",
                "task": f"Confirm fees & intake with {ahj.get('name') or f'{city} AHJ'}",
                "responsible_party": "Estimator / permit runner",
                "timeline": "Before bid",
                "estimated_cost": 0,
                "notes": ahj.get("notes")
                or (
                    "Portal seed — confirm fees on the official schedule."
                    if portal_only
                    else "Free pack path — upgrade for deep Universal Scout."
                ),
                # Full city packs: verified+citeable. Portal seeds: URL present, fees not curated.
                "verified": bool(confirm_url) and (citeable or portal_only),
                "cost_verified": False,
                "source_url": confirm_url,
                "source_label": ahj.get("name")
                or ("Portal seed" if portal_only else ("Source" if citeable else "AHJ portal")),
            }
        )

    for g in (pack.get("gotchas") or [])[:4]:
        if not isinstance(g, dict):
            continue
        # Never emit gotchas without a source URL.
        if not (g.get("source_url") or "").strip():
            continue
        items.append(
            {
                "priority": str(g.get("priority") or "HIGH").upper(),
                "task": str(g.get("title") or "Local gotcha"),
                "responsible_party": "Field / estimator",
                "timeline": "Before bid",
                "estimated_cost": 0,
                "notes": str(g.get("detail") or ""),
                "verified": bool(g.get("source_url")) and citeable,
                "cost_verified": False,
                "source_url": g.get("source_url"),
                "source_label": g.get("source_label") or ("Source" if citeable else "Unverified"),
            }
        )

    # Document checklist punches only when we have a confirm URL (avoids null-URL noise).
    if confirm_url and citeable:
        for d in (pack.get("documents") or [])[:5]:
            items.append(
                {
                    "priority": "MEDIUM",
                    "task": f"Have ready: {d}",
                    "responsible_party": "Permit package lead",
                    "timeline": "Submittal",
                    "estimated_cost": 0,
                    "notes": "Typical AHJ ask — confirm exact list",
                    "verified": True,
                    "cost_verified": False,
                    "source_url": confirm_url,
                    "source_label": "City pack document checklist",
                }
            )

    for hit in confirm_hits[:2]:
        if not hit.get("url"):
            continue
        items.append(
            {
                "priority": "HIGH",
                "task": f"Review confirm hit: {hit.get('title')}",
                "responsible_party": "Estimator",
                "timeline": "Before bid",
                "estimated_cost": 0,
                "notes": hit.get("snippet") or "Allowlisted / .gov SERP confirm (no page rescrape)",
                "verified": True,
                "cost_verified": False,
                "source_url": hit.get("url"),
                "source_label": "Allowlisted confirm search",
            }
        )

    # Coverage honesty lives on coverage_note / AHJ notes — not as Unverified punches.
    return items


def build_free_pack_confirm_analysis(
    *,
    address: str,
    city: str,
    state: str,
    zip_code: str,
    latitude: float = 0.0,
    longitude: float = 0.0,
    project_type: str = "general",
) -> Dict[str, Any]:
    """
    Synchronous free analysis: ZIP jurisdiction packs + local pack + optional
    cheap page confirm + at most one allowlisted SERP confirm.
    Never Firecrawl markdown-rescrapes unless FREE_TRIAL_MARKDOWN_CONFIRM=1.
    Never runs Universal Scout / Option A env screen.
    """
    from jurisdiction_resolver import attach_jurisdiction_cards, resolve_jurisdiction

    resolved = resolve_jurisdiction(zip_code=zip_code, city=city, state=state)
    city = (resolved.get("city") or city or "").strip()
    state = (resolved.get("state") or state or "").strip()
    zip_code = (resolved.get("zip") or zip_code or "").strip()

    pack = resolved.get("local") or resolve_city_pack(city, state, zip_code) or generic_thin_pack(
        city, state
    )
    # Prefer fees_url when present (often denser than portal landing shells)
    confirm_url = allowlisted_confirm_url(pack)
    pack_urls = [
        str((pack.get("ahj") or {}).get("fees_url") or ""),
        str((pack.get("ahj") or {}).get("portal_url") or ""),
    ]
    pack_urls = [u for u in pack_urls if u]
    # Try fees_url first for cheap confirm
    cheap_target = pack_urls[0] if pack_urls else confirm_url
    portal_only = bool(pack.get("portal_only"))
    citeable_pack = bool(pack.get("citeable"))

    # Cheap confirm FIRST — but NEVER for portal-only seeds (P1: fee quote risk).
    # Full citeable packs only. Fail-open on timeout/thin SPA.
    cheap_result: Optional[Dict[str, Any]] = None
    if free_cheap_confirm_enabled() and cheap_target and citeable_pack and not portal_only:
        try:
            from cheap_page_confirm import run_cheap_page_confirm

            cheap_result = run_cheap_page_confirm(
                cheap_target,
                pack_urls=pack_urls,
                use_llm=True,
            )
            # If primary URL is a JS shell, try the other pack URL once
            if (
                cheap_result.get("status") in ("thin_page", "no_markdown")
                and len(pack_urls) > 1
                and pack_urls[1] != cheap_target
            ):
                alt = run_cheap_page_confirm(
                    pack_urls[1],
                    pack_urls=pack_urls,
                    use_llm=True,
                )
                if alt.get("status") == "ok" and (
                    alt.get("fees") or alt.get("notes") or int(alt.get("markdown_chars") or 0) >= 400
                ):
                    cheap_result = alt
                    confirm_url = pack_urls[1]
            # P2: 404 / hard fetch failure → rediscover via generic .gov SERP once
            if cheap_result.get("status") in ("error", "http_error", "not_found", "404"):
                rediscovered = _one_generic_gov_search(city=city, state=state, limit=1)
                if rediscovered and rediscovered[0].get("url"):
                    confirm_url = str(rediscovered[0]["url"])
                    pack = dict(pack)
                    ahj_fix = dict(pack.get("ahj") or {})
                    ahj_fix["portal_url"] = confirm_url
                    ahj_fix["fees_url"] = confirm_url
                    ahj_fix["notes"] = (
                        str(ahj_fix.get("notes") or "")
                        + " Portal URL refreshed after seed link failed — confirm fees on schedule."
                    ).strip()
                    pack["ahj"] = ahj_fix
                    pack["portal_rediscovered"] = True
                    pack_urls = [confirm_url]
                    confirm_hits_seed = rediscovered[:1]
                else:
                    confirm_hits_seed = []
            else:
                confirm_hits_seed = []
        except Exception as e:
            logger.warning("Free cheap confirm failed: %s", e)
            cheap_result = {"status": "error", "error": str(e)}
            confirm_hits_seed = []
    else:
        confirm_hits_seed = []
        # Portal seed / thin: HEAD/GET check optional — on missing URL use SERP below.
        if confirm_url and portal_only:
            try:
                import requests

                probe = requests.get(
                    confirm_url,
                    timeout=6,
                    allow_redirects=True,
                    headers={"User-Agent": "RegGuardPortalCheck/1.0"},
                )
                if probe.status_code == 404:
                    rediscovered = _one_generic_gov_search(city=city, state=state, limit=1)
                    if rediscovered and rediscovered[0].get("url"):
                        confirm_url = str(rediscovered[0]["url"])
                        pack = dict(pack)
                        ahj_fix = dict(pack.get("ahj") or {})
                        ahj_fix["portal_url"] = confirm_url
                        ahj_fix["fees_url"] = confirm_url
                        ahj_fix["notes"] = (
                            str(ahj_fix.get("notes") or "")
                            + " Portal URL refreshed after 404 — confirm fees on schedule."
                        ).strip()
                        pack["ahj"] = ahj_fix
                        pack["portal_rediscovered"] = True
                        pack_urls = [confirm_url]
                        confirm_hits_seed = rediscovered[:1]
            except Exception as e:
                logger.info("Portal seed probe skipped/failed: %s", e)

    cheap_ok = bool(
        cheap_result
        and cheap_result.get("status") == "ok"
        and (
            cheap_result.get("fees")
            or cheap_result.get("notes")
            or int(cheap_result.get("markdown_chars") or 0) >= 400
        )
    )

    confirm_hits: List[Dict[str, Any]] = list(confirm_hits_seed)
    generic_serp_used = bool(pack.get("portal_rediscovered"))
    # No portal yet → one cached .gov SERP to discover an AHJ link (cheap long-tail).
    if not confirm_url and free_generic_serp_enabled():
        discovered = _one_generic_gov_search(city=city, state=state, limit=1)
        if discovered and discovered[0].get("url"):
            generic_serp_used = True
            confirm_url = str(discovered[0]["url"])
            pack = dict(pack)
            ahj_upd = dict(pack.get("ahj") or {})
            ahj_upd["portal_url"] = confirm_url
            ahj_upd["fees_url"] = ahj_upd.get("fees_url") or confirm_url
            if not ahj_upd.get("name") or "confirm locally" in str(ahj_upd.get("name") or "").lower():
                ahj_upd["name"] = (
                    f"{city}, {state} AHJ".strip(", ")
                    + f" ({discovered[0].get('title') or 'portal'})"
                )
            ahj_upd["notes"] = (
                str(ahj_upd.get("notes") or "")
                + " Portal discovered via filtered .gov search — confirm fees on the official schedule."
            ).strip()
            pack["ahj"] = ahj_upd
            pack["serp_discovered_portal"] = True
            pack["portal_only"] = True
            pack_urls = [confirm_url]
            confirm_hits = discovered[:1]

    # Cost premortem: do not double-spend SERP when cheap confirm already useful
    if (
        confirm_url
        and free_allowlist_search_enabled()
        and not cheap_ok
        and not generic_serp_used
        and citeable_pack
    ):
        confirm_hits = _one_allowlisted_search(
            city=city,
            state=state,
            confirm_url=confirm_url,
            limit=free_search_limit(),
        )

    # Hard guard: free never Firecrawl markdown-rescrapes unless explicitly enabled.
    markdown_note = None
    if free_markdown_confirm_enabled() and confirm_url:
        try:
            from markdown_scraper import fetch_trusted_url_markdown

            markdown_note = fetch_trusted_url_markdown(
                confirm_url, max_chars=4_000, allow_rescrape=True
            )
        except TypeError:
            markdown_note = None
        except Exception:
            markdown_note = None

    punch_items = _punch_from_pack(
        pack, city=city, state=state, confirm_hits=confirm_hits
    )
    ahj = pack.get("ahj") or {}
    timeline = str(pack.get("timeline_hint") or "Confirm with AHJ before bid")
    citeable = bool(pack.get("citeable"))
    coverage_note = str(
        resolved.get("coverage_note")
        or (
            "Federal + state always; citeable local is beachhead-first — not every city hall scraped."
        )
    )

    findings = [
        {
            "category": "permitting",
            "risk_level": "HIGH" if citeable else "MEDIUM",
            "description": (
                f"Free FinOps path for {city}, {state}: federal+state+local packs"
                + (" + cheap page confirm" if cheap_ok else "")
                + (" + 1 allowlisted confirm search" if confirm_hits else "")
                + ". No deep Universal Scout. "
                + coverage_note
            ),
            "action_items": [
                f"Open AHJ portal: {confirm_url or 'confirm locally'}",
                "Forward Bid Risk Receipt before bid day",
                "Upgrade for full Firecrawl scout + deeper citations",
            ],
            "data_sources": [
                f"city_pack:{pack.get('pack_key')}",
                "jurisdiction:federal+state",
                *(["cheap_page_confirm"] if cheap_ok else []),
                *(["allowlisted_confirm_search"] if confirm_hits else []),
            ],
            "research_cost_usd": 0,
        }
    ]
    if markdown_note:
        findings[0]["action_items"].insert(
            1, "Markdown confirm fetched (FREE_TRIAL_MARKDOWN_CONFIRM=1)"
        )

    high_punch = [i for i in punch_items if i.get("priority") in ("CRITICAL", "HIGH")]

    analysis: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "preview": True,
        "research_depth": "free",
        "finops_mode": "pack_confirm",
        "project_info": {
            "address": address,
            "city": city,
            "state": state,
            "zip": zip_code,
            "type": project_type,
            "coordinates": {"latitude": latitude, "longitude": longitude},
        },
        "environmental_screening": {
            "risk_level": "MEDIUM",
            "findings": findings,
            "total_research_cost": 0,
            "action_plan": findings[0]["action_items"][:3],
        },
        "punch_list": {
            "punch_list": punch_items,
            "timeline_summary": timeline,
            "estimated_total_cost": 0,
            "critical_path": [
                {
                    "task": i["task"],
                    "verified": i.get("verified"),
                    "cost_verified": False,
                    "source_url": i.get("source_url"),
                    "source_label": i.get("source_label"),
                    "estimated_cost": 0,
                }
                for i in high_punch[:5]
            ],
            "estimates_verified": False,
            "milestones": [
                {"week": "0", "milestone": "Confirm AHJ fees/portal from pack"},
                {"week": "bid", "milestone": "Re-check site before submit"},
            ],
            "who_to_call": {
                "building_department": ahj.get("name") or f"{city} AHJ",
                "phone": ahj.get("phone") or "Confirm on portal",
            },
        },
        "summary": {
            "total_environmental_risks": len(findings),
            "high_risk_count": 1 if citeable else 0,
            "total_punch_list_items": len(punch_items),
            "estimated_timeline": timeline,
            "estimated_total_cost": 0,
        },
        "next_steps": [
            "Export / forward the Bid Risk Receipt",
            "Confirm fees on the AHJ schedule before bid",
            "Upgrade to Partner or Contractor Pro for full Universal Scout",
        ],
        "free_confirm": {
            "pack_key": pack.get("pack_key"),
            "citeable": citeable,
            "portal_only": bool(pack.get("portal_only")),
            "confirm_url": confirm_url or None,
            "search_hits": len(confirm_hits),
            "markdown_rescrape": bool(markdown_note),
            "cheap_confirm": (cheap_result or {}).get("status"),
            "serp_skipped_after_cheap": bool(cheap_ok and not confirm_hits),
            "generic_serp_portal": bool(pack.get("serp_discovered_portal")),
            "search_limit": free_search_limit(),
            "coverage_note": coverage_note,
        },
    }

    analysis = attach_jurisdiction_cards(analysis, resolved)

    if cheap_result and citeable and not bool(pack.get("portal_only")):
        from cheap_page_confirm import merge_cheap_confirm_into_analysis

        analysis = merge_cheap_confirm_into_analysis(analysis, cheap_result)

    from coverage_honesty import apply_coverage_honesty

    analysis = apply_coverage_honesty(analysis, resolved=resolved, pack=pack)

    # Refresh counts after jurisdiction + cheap merges
    punch_n = len((analysis.get("punch_list") or {}).get("punch_list") or [])
    if analysis.get("summary"):
        analysis["summary"]["total_punch_list_items"] = punch_n

    from depth_ladder import DEPTH_FREE, stamp_upgrade_offer

    stamp_upgrade_offer(analysis, depth_tier=DEPTH_FREE)
    return analysis


async def run_free_pack_confirm(
    *,
    address: str,
    city: str,
    state: str,
    zip_code: str,
    latitude: float = 0.0,
    longitude: float = 0.0,
    project_type: str = "general",
) -> Dict[str, Any]:
    """Async wrapper for free-trial / recheck free branch."""
    import asyncio

    return await asyncio.to_thread(
        build_free_pack_confirm_analysis,
        address=address,
        city=city,
        state=state,
        zip_code=zip_code,
        latitude=latitude,
        longitude=longitude,
        project_type=project_type,
    )
