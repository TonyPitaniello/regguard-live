"""
Paid-only smarter AHJ confirm: map (search within site) + one markdown scrape,
then regex/schema-ish fee extract. Never used on free FinOps path.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _env_on(name: str, default: str = "1") -> bool:
    return (os.getenv(name) or default).strip().lower() in ("1", "true", "yes", "on")


def paid_smart_confirm_enabled() -> bool:
    return _env_on("PAID_AHJ_SMART_CONFIRM", "1")


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _extract_fee_rows(markdown: str, source_url: str) -> List[Dict[str, Any]]:
    """Pull simple $ lines from AHJ page markdown — planning aid, not a quote."""
    rows: List[Dict[str, Any]] = []
    money = re.compile(
        r"(?P<label>.{0,80}?)\$\s*(?P<amt>[0-9][0-9,]*(?:\.[0-9]+)?)",
        re.IGNORECASE,
    )
    for line in (markdown or "").splitlines():
        line = line.strip()
        if not line or len(line) > 220:
            continue
        m = money.search(line)
        if not m:
            continue
        try:
            amt = float(m.group("amt").replace(",", ""))
        except ValueError:
            continue
        label = re.sub(r"[#*_`]+", "", m.group("label")).strip(" :-|") or "Fee line"
        if amt <= 0 or amt > 5_000_000:
            continue
        rows.append(
            {
                "label": label[:120],
                "amount_usd": amt,
                "detail": "Extracted from allowlisted AHJ page — confirm on official schedule",
                "verified": True,
                "source_url": source_url,
                "source_label": "AHJ smart confirm scrape",
            }
        )
        if len(rows) >= 8:
            break
    return rows


def _map_candidate_urls(portal_url: str, *, limit: int = 8) -> List[str]:
    """Firecrawl map with search=fees|permit to find better pages on same host."""
    try:
        from scraper import _get_client

        fc = _get_client()
    except Exception as e:
        logger.warning("Smart confirm: no Firecrawl client: %s", e)
        return []

    urls: List[str] = []
    host = _host(portal_url)
    for search in ("fees", "permit", "building inspection"):
        try:
            result = fc.map(portal_url, search=search, limit=limit)
        except TypeError:
            try:
                result = fc.map(portal_url, limit=limit)
            except Exception as e:
                logger.warning("Smart confirm map failed: %s", e)
                continue
        except Exception as e:
            logger.warning("Smart confirm map(%s) failed: %s", search, e)
            continue

        links = getattr(result, "links", None)
        if links is None and isinstance(result, dict):
            links = result.get("links") or result.get("urls") or []
        for item in list(links or [])[:limit]:
            u = item if isinstance(item, str) else getattr(item, "url", None) or (
                item.get("url") if isinstance(item, dict) else None
            )
            if not u:
                continue
            if host and host not in _host(str(u)):
                continue
            s = str(u)
            if s not in urls:
                urls.append(s)
        if urls:
            break
    return urls[:limit]


def run_paid_ahj_smart_confirm(
    analysis: Dict[str, Any],
    *,
    city: str = "",
    state: str = "",
    zip_code: str = "",
) -> Dict[str, Any]:
    """
    Mutate/return analysis with smart_confirm block + fee rows merged into fee_card.
    Paid path only. Prefers cheap page confirm first; Firecrawl scrape on miss.
    """
    if not isinstance(analysis, dict) or not paid_smart_confirm_enabled():
        return analysis

    from city_packs import generic_thin_pack, resolve_city_pack
    from free_pack_confirm import allowlisted_confirm_url
    from jurisdiction_resolver import attach_jurisdiction_cards, resolve_jurisdiction
    from markdown_scraper import fetch_trusted_url_markdown

    pi = analysis.get("project_info") or {}
    city = city or str(pi.get("city") or "")
    state = state or str(pi.get("state") or "")
    zip_code = zip_code or str(pi.get("zip") or "")

    resolved = resolve_jurisdiction(zip_code=zip_code, city=city, state=state)
    city = resolved.get("city") or city
    state = resolved.get("state") or state
    zip_code = resolved.get("zip") or zip_code
    analysis = attach_jurisdiction_cards(analysis, resolved)

    pack = resolved.get("local") or resolve_city_pack(city, state, zip_code) or generic_thin_pack(
        city, state
    )
    portal = allowlisted_confirm_url(pack)
    pack_urls = [
        str((pack.get("ahj") or {}).get("portal_url") or ""),
        str((pack.get("ahj") or {}).get("fees_url") or ""),
    ]
    if not portal:
        analysis["smart_confirm"] = {
            "status": "skipped",
            "reason": "no_allowlisted_portal",
            "pack_key": pack.get("pack_key"),
        }
        return analysis

    # Prefer cheap confirm (no Firecrawl scrape) first
    try:
        from cheap_page_confirm import merge_cheap_confirm_into_analysis, run_cheap_page_confirm

        cheap = run_cheap_page_confirm(portal, pack_urls=pack_urls, use_llm=True)
        if cheap.get("status") == "ok" and (cheap.get("fees") or cheap.get("notes")):
            analysis = merge_cheap_confirm_into_analysis(analysis, cheap)
            analysis["smart_confirm"] = {
                "status": "ok",
                "method": "cheap_page_confirm",
                "pack_key": pack.get("pack_key"),
                "portal_url": portal,
                "scraped_url": portal,
                "fee_rows_extracted": len(cheap.get("fees") or []),
                "markdown_chars": cheap.get("markdown_chars") or 0,
            }
            logger.info(
                "Paid AHJ smart confirm via cheap path pack=%s fees=%s",
                pack.get("pack_key"),
                len(cheap.get("fees") or []),
            )
            return analysis
    except Exception as e:
        logger.warning("Paid cheap confirm failed, falling back to Firecrawl: %s", e)

    mapped = _map_candidate_urls(portal, limit=6)
    # Prefer fee-ish URLs, else portal
    target = portal
    for u in mapped:
        low = u.lower()
        if any(k in low for k in ("fee", "permit", "inspection", "building")):
            target = u
            break
    if mapped and target == portal:
        target = mapped[0]

    md = fetch_trusted_url_markdown(target, max_chars=12_000, allow_rescrape=True)
    # Dallas dallascityhall.com may fail trust (.gov) — try cheap confirm on mapped URL hosts via pack
    if not md and target != portal:
        md = fetch_trusted_url_markdown(portal, max_chars=12_000, allow_rescrape=True)
        target = portal
    if not md:
        try:
            from cheap_page_confirm import fetch_page_markdown

            md = fetch_page_markdown(target, pack_urls=pack_urls + mapped, max_chars=12_000)
        except Exception:
            md = None

    fee_rows = _extract_fee_rows(md or "", target) if md else []

    analysis["smart_confirm"] = {
        "status": "ok" if md else "no_markdown",
        "method": "firecrawl_or_cheap_markdown",
        "pack_key": pack.get("pack_key"),
        "portal_url": portal,
        "scraped_url": target,
        "mapped_urls": mapped[:6],
        "fee_rows_extracted": len(fee_rows),
        "markdown_chars": len(md or ""),
    }

    if fee_rows:
        fee_card = dict(analysis.get("fee_card") or {})
        existing = list(fee_card.get("fees") or [])
        seen = {str(r.get("label") or "")[:40] for r in existing}
        for row in fee_rows:
            key = str(row.get("label") or "")[:40]
            if key not in seen:
                existing.insert(0, row)
                seen.add(key)
        fee_card["fees"] = existing[:12]
        fee_card["smart_confirm"] = True
        analysis["fee_card"] = fee_card

        # Surface top extract as a punch line
        punch = analysis.get("punch_list") or {}
        items = list(punch.get("punch_list") or [])
        top = fee_rows[0]
        items.insert(
            0,
            {
                "priority": "HIGH",
                "task": f"Confirm AHJ fee extract: {top.get('label')} (~${top.get('amount_usd'):,.0f})"
                if isinstance(top.get("amount_usd"), (int, float))
                else f"Confirm AHJ fee extract: {top.get('label')}",
                "responsible_party": "Estimator",
                "timeline": "Before bid",
                "estimated_cost": top.get("amount_usd")
                if isinstance(top.get("amount_usd"), (int, float))
                else 0,
                "notes": "From paid AHJ smart confirm — verify on official schedule",
                "verified": True,
                "cost_verified": False,
                "source_url": top.get("source_url"),
                "source_label": "AHJ smart confirm",
            },
        )
        punch["punch_list"] = items
        analysis["punch_list"] = punch

    logger.info(
        "Paid AHJ smart confirm pack=%s scraped=%s fees=%s",
        pack.get("pack_key"),
        target,
        len(fee_rows),
    )
    return analysis
