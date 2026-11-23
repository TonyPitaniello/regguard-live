"""
Scrape the site-finder shortlist. One page, no crawl, no new URLs.

Free and Estimator never scrape. Pro stops at the Pro page cap.
An IC bound site, including a new Annual site, uses the IC page cap.
A lookup stops before it can pass the Prompt 0 credit ceiling.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_PAGE_CACHE: Dict[str, Dict[str, Any]] = {}
_RUNS: Dict[str, str] = {}

PDF_PAGE_CAP = 15
SEARCH_CREDITS = 2
PRO_CREDIT_CEILING = 400  # $2 at the dearest published $0.005 credit
IC_CREDIT_CEILING = 3000  # $15 at that same rate

Scraper = Callable[[str], Dict[str, Any]]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _day(moment: Optional[datetime] = None) -> str:
    return (moment or _now()).strftime("%Y-%m-%d")


def clear_shortlist_cache() -> None:
    with _LOCK:
        _PAGE_CACHE.clear()
        _RUNS.clear()


def _run_key(urls: List[str], rung: str) -> str:
    return rung + "\n" + "\n".join(urls)


def _shortlist(analysis: Dict[str, Any]) -> List[str]:
    finder = analysis.get("site_finder") if isinstance(analysis.get("site_finder"), dict) else {}
    urls: List[str] = []
    for row in finder.get("rows") or []:
        if not isinstance(row, dict):
            continue
        url = str(row.get("url") or "").strip()
        if url.startswith("https://") and url not in urls:
            urls.append(url)
    return urls


def _rung(analysis: Dict[str, Any], rung: str) -> str:
    key = str(rung or "").strip().lower()
    if key in ("free", "estimator", "partner"):
        return "estimator" if key in ("estimator", "partner") else "free"
    if key in ("pro", "contractor_pro"):
        return "pro"
    if key in ("ic", "ic_full", "ic_project", "ic_annual"):
        return "ic"
    depth = str(analysis.get("research_depth") or "").strip().lower()
    if depth in ("ic", "ic_full"):
        return "ic"
    if depth.startswith("pro") or str(analysis.get("access_tier") or "") == "contractor_pro":
        return "pro"
    return key or "free"


def _may_scrape(rung: str) -> bool:
    return rung in ("pro", "ic")


def _ceiling(rung: str) -> int:
    return IC_CREDIT_CEILING if rung == "ic" else PRO_CREDIT_CEILING


def _reserve(url: str) -> int:
    path = (urlparse(url).path or "").lower()
    return PDF_PAGE_CAP if path.endswith(".pdf") else 1


def _age_days(record: Dict[str, Any], moment: datetime) -> int:
    raw = str(record.get("cached_at") or "")
    try:
        then = datetime.fromisoformat(raw)
    except ValueError:
        return 99
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    return (moment.date() - then.astimezone(timezone.utc).date()).days


def _cached(url: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        row = _PAGE_CACHE.get(url)
    return dict(row) if isinstance(row, dict) else None


def cached_markdown(url: str) -> str:
    """Read a page already stored today. Does not scrape."""
    row = _cached(url)
    return str((row or {}).get("markdown") or "")


def _store(url: str, record: Dict[str, Any]) -> None:
    with _LOCK:
        _PAGE_CACHE[url] = dict(record)


def _status_from_error(exc: Exception) -> int:
    text = str(exc).lower()
    if "403" in text:
        return 403
    if "timeout" in text or "timed out" in text:
        return 0
    return 0


def _default_scraper(url: str) -> Dict[str, Any]:
    from scraper import FIRECRAWL_MAX_AGE_MS, _get_client

    fc = _get_client()
    parsers = None
    if url.lower().split("?", 1)[0].endswith(".pdf"):
        from firecrawl.v2.types import PDFParser

        parsers = [PDFParser(type="pdf", max_pages=PDF_PAGE_CAP)]
    doc = fc.scrape(
        url,
        formats=["markdown"],
        only_main_content=True,
        parsers=parsers,
        max_age=FIRECRAWL_MAX_AGE_MS,
        timeout=20000,
    )
    text = getattr(doc, "markdown", None) if doc is not None else None
    status = int(getattr(doc, "status_code", None) or getattr(doc, "status", None) or 200)
    return {"markdown": str(text or ""), "status": status, "url": url}


def _scrape_once(url: str, scraper: Scraper) -> Dict[str, Any]:
    """One request, then one retry. A 403 is not retried and the host does not change."""
    attempts = 0
    last_status = 0
    while attempts < 2:
        attempts += 1
        try:
            result = scraper(url) or {}
        except Exception as exc:
            last_status = _status_from_error(exc)
            if last_status == 403 or attempts >= 2:
                return {"markdown": "", "status": last_status or 403, "url": url}
            continue
        status = int(result.get("status") or 0)
        if status == 403:
            return {"markdown": "", "status": 403, "url": url}
        return {
            "markdown": str(result.get("markdown") or ""),
            "status": status or 200,
            "url": str(result.get("url") or url),
        }
    return {"markdown": "", "status": last_status, "url": url}


def _page_record(url: str, *, markdown: str, status: int, moment: datetime, cache_hit: bool) -> Dict[str, Any]:
    verified = bool(markdown.strip()) and status not in (0, 403)
    return {
        "url": url,
        "retrieved_url": url,
        "host": (urlparse(url).hostname or "").lower(),
        "markdown": markdown if verified else "",
        "status": status,
        "verified": "Source" if verified else "Unverified",
        "cached_at": moment.isoformat(),
        "day": _day(moment),
        "cache_hit": cache_hit,
    }


def scrape_finder_shortlist(
    analysis: Dict[str, Any],
    *,
    rung: str,
    city: str = "",
    state: str = "",
    zip_code: str = "",
    recheck: bool = False,
    scraper: Optional[Scraper] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Scrape only shortlist URLs. Estimator and Free return with zero scrapes.
    Recheck scrapes a URL only when its cache is seven days old or older,
    and the caller must not write a new fee from that markdown.
    """
    moment = now or _now()
    rung_key = _rung(analysis, rung)
    finder = analysis.get("site_finder") if isinstance(analysis.get("site_finder"), dict) else {}
    searches = int(finder.get("searches") or 0)
    credits = searches * SEARCH_CREDITS
    pages: List[Dict[str, Any]] = []
    scrapes = 0
    cache_hits = 0
    stopped = False
    cap = 0
    if _may_scrape(rung_key):
        from paid_local_confirm import max_pages

        cap = max_pages(ic_deepen=rung_key == "ic")
    ceiling = _ceiling(rung_key)
    fetch = scraper or _default_scraper

    urls = _shortlist(analysis)
    if not _may_scrape(rung_key):
        analysis["shortlist_pages"] = []
        analysis["firecrawl_credits"] = {
            "searches": searches,
            "scrapes": 0,
            "cache_hits": 0,
            "credits": credits,
            "stopped_for_ceiling": False,
        }
        return analysis

    # A second lookup the same UTC day reads the cache. It does not spend the cap again.
    run_key = _run_key(urls, rung_key)
    if not recheck:
        with _LOCK:
            already = _RUNS.get(run_key) == _day(moment)
        if already:
            pages = []
            for url in urls:
                existing = _cached(url)
                if not existing:
                    continue
                hit = dict(existing)
                hit["cache_hit"] = True
                pages.append(hit)
                cache_hits += 1
            analysis["shortlist_pages"] = pages
            analysis["firecrawl_credits"] = {
                "searches": searches,
                "scrapes": 0,
                "cache_hits": cache_hits,
                "credits": credits,
                "stopped_for_ceiling": False,
            }
            return analysis

    for url in urls:
        existing = _cached(url)
        fresh_today = bool(existing and not recheck and existing.get("day") == _day(moment))
        fresh_recheck = bool(existing and recheck and _age_days(existing, moment) < 7)
        if fresh_today or fresh_recheck:
            hit = dict(existing or {})
            hit["cache_hit"] = True
            pages.append(hit)
            cache_hits += 1
            continue
        if scrapes >= cap:
            if existing:
                hit = dict(existing)
                hit["cache_hit"] = True
                pages.append(hit)
                cache_hits += 1
            continue
        reserve = _reserve(url)
        if credits + reserve > ceiling:
            stopped = True
            if existing:
                hit = dict(existing)
                hit["cache_hit"] = True
                pages.append(hit)
                cache_hits += 1
            break
        result = _scrape_once(url, fetch)
        scrapes += 1
        credits += reserve
        record = _page_record(
            url,
            markdown=str(result.get("markdown") or ""),
            status=int(result.get("status") or 0),
            moment=moment,
            cache_hit=False,
        )
        _store(url, record)
        pages.append(record)
        if scrapes >= cap:
            break

    if not recheck:
        with _LOCK:
            _RUNS[run_key] = _day(moment)

    analysis["shortlist_pages"] = pages
    analysis["firecrawl_credits"] = {
        "searches": searches,
        "scrapes": scrapes,
        "cache_hits": cache_hits,
        "credits": credits,
        "stopped_for_ceiling": stopped,
    }
    zip5 = "".join(c for c in str(zip_code or "") if c.isdigit())[:5]
    if len(zip5) == 5 and scrapes:
        try:
            from research_cache_interceptor import cache_firecrawl_result

            cache_firecrawl_result(
                zip5,
                city,
                state,
                {
                    "source": "shortlist",
                    "pages": [
                        {
                            "url": p.get("url"),
                            "status": p.get("status"),
                            "verified": p.get("verified"),
                        }
                        for p in pages
                    ],
                    "credits": analysis["firecrawl_credits"],
                },
            )
        except Exception as exc:
            logger.warning("shortlist cache_firecrawl_result failed: %s", exc)
    return analysis
