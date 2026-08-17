"""
Paid FinOps mode: ``paid_local_confirm``

Bounded AHJ local confirm for Contractor Pro / paid free-trial deepen:
  portal resolve → cheap confirm → map ≤N pages → markdown scrape (cached) → grounded fees.

Caps (env):
  PAID_LOCAL_CONFIRM=1
  PAID_LOCAL_CONFIRM_MAX_PAGES=8
  PAID_LOCAL_CONFIRM_MAX_PER_DAY=25   (per email; 0 = unlimited)
  PAID_LOCAL_CONFIRM_CACHE_TTL_SEC=86400
  PAID_UNIVERSAL_SCOUT=0              (default off — set 1 for full scout on all paid)
  PAID_PRO_LIGHT_SCOUT=1              (default on — Pro runs 3-pass light Universal Scout)

Quota + result cache are file/in-process under REGGUARD_DATA_DIR (default /tmp).
Multi-instance: use a shared disk or set REDIS_URL later — single-instance sticky until then.

Never used on free ``pack_confirm`` path.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_RESULT_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_RESULT_CACHE_MAX = 256


def _env_on(name: str, default: str = "1") -> bool:
    return (os.getenv(name) or default).strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name) or default)
    except ValueError:
        return default


def paid_local_confirm_enabled() -> bool:
    return _env_on("PAID_LOCAL_CONFIRM", "1")


def paid_universal_scout_enabled() -> bool:
    """
    Full Universal Scout after local confirm (costly).
    Default OFF (premortem F2) — enable per-env or force for IC.
    """
    return _env_on("PAID_UNIVERSAL_SCOUT", "0")


def max_pages() -> int:
    return max(1, min(12, _env_int("PAID_LOCAL_CONFIRM_MAX_PAGES", 8)))


def max_lookups_per_day() -> int:
    """0 = unlimited. Default 25 (premortem F2 — tighter than 40)."""
    return max(0, _env_int("PAID_LOCAL_CONFIRM_MAX_PER_DAY", 25))


def cache_ttl_sec() -> float:
    try:
        return max(300.0, float(os.getenv("PAID_LOCAL_CONFIRM_CACHE_TTL_SEC") or "86400"))
    except ValueError:
        return 86400.0


def _norm_email(email: str = "") -> str:
    """Normalize email; strip +tags for quota (premortem F10)."""
    em = (email or "").strip().lower()
    if not em or "@" not in em:
        return em
    local, _, domain = em.partition("@")
    if "+" in local:
        local = local.split("+", 1)[0]
    # Gmail dots are optional — only collapse for gmail/googlemail
    if domain in ("gmail.com", "googlemail.com"):
        local = local.replace(".", "")
    return f"{local}@{domain}"


FEE_PLANNING_AID = (
    "Planning aid only — not an AHJ quote. Confirm on the official fee schedule before bid."
)


def _day_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _quota_path() -> Path:
    root = Path(os.getenv("REGGUARD_DATA_DIR") or "/tmp/regguard_data")
    root.mkdir(parents=True, exist_ok=True)
    return root / "paid_local_confirm_quota.json"


def get_paid_local_usage(email: str = "") -> Dict[str, Any]:
    em = _norm_email(email) or "_anonymous_"
    limit = max_lookups_per_day()
    day = _day_key()
    with _LOCK:
        data: Dict[str, Any] = {}
        path = _quota_path()
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        days = data.setdefault("days", {})
        bucket = days.setdefault(day, {})
        used = int(bucket.get(em) or 0)
    remaining = None if limit <= 0 else max(0, limit - used)
    return {
        "email": em if em != "_anonymous_" else "",
        "day": day,
        "used": used,
        "limit": limit if limit > 0 else None,
        "remaining": remaining,
        "allowed": limit <= 0 or used < limit,
        "finops_mode": "paid_local_confirm",
    }


def consume_paid_local_lookup(email: str = "") -> Tuple[bool, Dict[str, Any]]:
    """Atomically check+increment day quota. Returns (allowed, usage)."""
    em = _norm_email(email) or "_anonymous_"
    limit = max_lookups_per_day()
    day = _day_key()
    with _LOCK:
        path = _quota_path()
        data: Dict[str, Any] = {"days": {}}
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                data = {"days": {}}
        days = data.setdefault("days", {})
        # prune old days (keep 7)
        for old in list(days.keys()):
            if old < day and len(days) > 7:
                try:
                    if (datetime.strptime(day, "%Y-%m-%d") - datetime.strptime(old, "%Y-%m-%d")).days > 7:
                        del days[old]
                except Exception:
                    pass
        bucket = days.setdefault(day, {})
        used = int(bucket.get(em) or 0)
        if limit > 0 and used >= limit:
            usage = {
                "email": em if em != "_anonymous_" else "",
                "day": day,
                "used": used,
                "limit": limit,
                "remaining": 0,
                "allowed": False,
                "finops_mode": "paid_local_confirm",
                "capped": True,
            }
            return False, usage
        bucket[em] = used + 1
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("paid local quota save failed: %s", e)
        used = int(bucket[em])
    remaining = None if limit <= 0 else max(0, limit - used)
    return True, {
        "email": em if em != "_anonymous_" else "",
        "day": day,
        "used": used,
        "limit": limit if limit > 0 else None,
        "remaining": remaining,
        "allowed": True,
        "finops_mode": "paid_local_confirm",
        "capped": False,
    }


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _cache_key(city: str, state: str, zip_code: str, portal: str) -> str:
    raw = f"{(city or '').lower()}|{(state or '').upper()}|{(zip_code or '')[:5]}|{portal}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cache_get(key: str) -> Optional[Dict[str, Any]]:
    now = time.monotonic()
    with _LOCK:
        row = _RESULT_CACHE.get(key)
        if not row:
            return None
        ts, payload = row
        if now - ts > cache_ttl_sec():
            del _RESULT_CACHE[key]
            return None
        return dict(payload)


def _cache_set(key: str, payload: Dict[str, Any]) -> None:
    with _LOCK:
        while len(_RESULT_CACHE) >= _RESULT_CACHE_MAX:
            try:
                _RESULT_CACHE.pop(next(iter(_RESULT_CACHE)))
            except Exception:
                break
        _RESULT_CACHE[key] = (time.monotonic(), dict(payload))


def _score_mapped_url(url: str) -> int:
    """Prefer permit/building fee pages; reject parking/utility noise (F4)."""
    low = (url or "").lower()
    if any(
        x in low
        for x in (
            "parking",
            "meter",
            "utility-bill",
            "water-bill",
            "recreation",
            "library",
            "police",
            "court-fine",
            "animal",
        )
    ):
        return -100
    score = 0
    for token, pts in (
        ("fee", 25),
        ("permit", 30),
        ("building", 20),
        ("electrical", 25),
        ("inspection", 15),
        ("development", 10),
        ("schedule", 15),
    ):
        if token in low:
            score += pts
    return score


def _map_candidate_urls(portal_url: str, *, limit: int = 8) -> List[str]:
    try:
        from scraper import _get_client

        fc = _get_client()
    except Exception as e:
        logger.warning("Paid local confirm: no Firecrawl client: %s", e)
        return []

    urls: List[str] = []
    host = _host(portal_url)
    # Premortem F8: fewer map queries to cut latency
    for search in ("building permit fees", "electrical permit"):
        try:
            result = fc.map(portal_url, search=search, limit=limit)
        except TypeError:
            try:
                result = fc.map(portal_url, limit=limit)
            except Exception as e:
                logger.warning("Paid local map failed: %s", e)
                continue
        except Exception as e:
            logger.warning("Paid local map(%s) failed: %s", search, e)
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
            if _score_mapped_url(s) < 0:
                continue
            if s not in urls:
                urls.append(s)
        if len(urls) >= limit:
            break
    urls.sort(key=_score_mapped_url, reverse=True)
    return [u for u in urls if _score_mapped_url(u) >= 15][:limit]


def _extract_fee_rows(markdown: str, source_url: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    money = re.compile(
        r"(?P<label>.{0,80}?)\$\s*(?P<amt>[0-9][0-9,]*(?:\.[0-9]+)?)",
        re.IGNORECASE,
    )
    for line in (markdown or "").splitlines():
        line = line.strip()
        if not line or len(line) > 220:
            continue
        # Skip obvious non-permit money lines
        low = line.lower()
        if any(x in low for x in ("parking", "meter", "fine", "library", "recreation")):
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
        # Grounding: amount must appear in line (already does via regex)
        rows.append(
            {
                "label": label[:120],
                "amount_usd": amt,
                "detail": FEE_PLANNING_AID,
                "verified": True,  # source URL present; still planning aid
                "planning_aid": True,
                "cost_verified": False,
                "source_url": source_url,
                "source_label": "Paid local confirm (planning aid)",
            }
        )
        if len(rows) >= 8:
            break
    return rows


def _merge_fees_into_analysis(
    analysis: Dict[str, Any],
    fee_rows: List[Dict[str, Any]],
    *,
    scraped_url: str,
) -> Dict[str, Any]:
    if not fee_rows:
        return analysis
    # Ensure planning-aid flags on every row (F3)
    normalized = []
    for row in fee_rows:
        r = dict(row)
        r["planning_aid"] = True
        r["cost_verified"] = False
        r["detail"] = FEE_PLANNING_AID
        if "planning aid" not in str(r.get("source_label") or "").lower():
            r["source_label"] = f"{r.get('source_label') or 'Paid local confirm'} (planning aid)"
        normalized.append(r)
    fee_rows = normalized

    fee_card = dict(analysis.get("fee_card") or {})
    existing = list(fee_card.get("fees") or [])
    seen = {str(r.get("label") or "")[:40] for r in existing}
    for row in fee_rows:
        key = str(row.get("label") or "")[:40]
        if key not in seen:
            existing.insert(0, row)
            seen.add(key)
    fee_card["fees"] = existing[:12]
    fee_card["paid_local_confirm"] = True
    fee_card["citeable_coverage"] = True
    fee_card["planning_aid"] = True
    fee_card["disclaimer"] = FEE_PLANNING_AID
    analysis["fee_card"] = fee_card

    punch = analysis.get("punch_list") or {}
    items = list(punch.get("punch_list") or [])
    top = fee_rows[0]
    amt = top.get("amount_usd")
    task = (
        f"[Planning aid] Confirm on AHJ schedule: {top.get('label')} (~${amt:,.0f} on page)"
        if isinstance(amt, (int, float))
        else f"[Planning aid] Confirm on AHJ schedule: {top.get('label')}"
    )
    items.insert(
        0,
        {
            "priority": "HIGH",
            "task": task,
            "responsible_party": "Estimator",
            "timeline": "Before bid",
            "estimated_cost": amt if isinstance(amt, (int, float)) else 0,
            "notes": FEE_PLANNING_AID,
            "verified": True,
            "cost_verified": False,
            "planning_aid": True,
            "source_url": top.get("source_url") or scraped_url,
            "source_label": "Paid local confirm (planning aid)",
        },
    )
    punch["punch_list"] = items
    analysis["punch_list"] = punch
    return analysis


def run_paid_local_confirm(
    analysis: Dict[str, Any],
    *,
    city: str = "",
    state: str = "",
    zip_code: str = "",
    email: str = "",
) -> Dict[str, Any]:
    """
    Mutate analysis with bounded paid local AHJ confirm.
    Sets ``finops_mode=paid_local_confirm`` and ``paid_local`` block.
    """
    if not isinstance(analysis, dict) or not paid_local_confirm_enabled():
        return analysis

    from city_packs import generic_thin_pack, resolve_city_pack
    from free_pack_confirm import allowlisted_confirm_url
    from jurisdiction_resolver import attach_jurisdiction_cards, resolve_jurisdiction
    from metro_portal_seeds import resolve_metro_portal_pack

    pi = analysis.get("project_info") or {}
    city = city or str(pi.get("city") or "")
    state = state or str(pi.get("state") or "")
    zip_code = zip_code or str(pi.get("zip") or "")

    allowed, usage = consume_paid_local_lookup(email)
    analysis["finops_mode"] = "paid_local_confirm"
    analysis["paid_local_quota"] = usage

    # Always attach federal/state even when capped (F5/F9 — don't look like an outage)
    resolved = resolve_jurisdiction(zip_code=zip_code, city=city, state=state)
    city = str(resolved.get("city") or city)
    state = str(resolved.get("state") or state)
    zip_code = str(resolved.get("zip") or zip_code)
    analysis = attach_jurisdiction_cards(analysis, resolved)

    pack = (
        resolved.get("local")
        or resolve_city_pack(city, state, zip_code)
        or resolve_metro_portal_pack(city, state, zip_code)
        or generic_thin_pack(city, state)
    )

    if not allowed:
        analysis["paid_local"] = {
            "status": "capped",
            "reason": "daily_cap",
            "quota": usage,
            "max_pages": max_pages(),
            "user_message": (
                f"Daily paid scrape cap reached ({usage.get('used')}/{usage.get('limit')}). "
                "Showing federal/state + pack/cache layers. Try again tomorrow or use an IC Project for heavy research."
            ),
        }
        _apply_paid_coverage(analysis, resolved, pack, [])
        logger.info("Paid local confirm capped for email=%s used=%s", usage.get("email"), usage.get("used"))
        return analysis

    portal = allowlisted_confirm_url(pack)
    pack_urls = [
        str((pack.get("ahj") or {}).get("fees_url") or ""),
        str((pack.get("ahj") or {}).get("portal_url") or ""),
    ]
    pack_urls = [u for u in pack_urls if u]

    # F9: no portal → one filtered .gov SERP before skip
    if not portal:
        try:
            from free_pack_confirm import _one_generic_gov_search

            hits = _one_generic_gov_search(city=city, state=state, limit=1)
            if hits and hits[0].get("url"):
                portal = str(hits[0]["url"])
                pack = dict(pack)
                ahj = dict(pack.get("ahj") or {})
                ahj["portal_url"] = portal
                ahj["fees_url"] = portal
                ahj["notes"] = (
                    str(ahj.get("notes") or "")
                    + " Portal from filtered .gov search — confirm fees on schedule."
                ).strip()
                pack["ahj"] = ahj
                pack["portal_only"] = True
                pack["serp_discovered_portal"] = True
                pack_urls = [portal]
        except Exception as e:
            logger.info("Paid local SERP portal discover skipped: %s", e)

    if not portal:
        analysis["paid_local"] = {
            "status": "skipped",
            "reason": "no_portal",
            "pack_key": pack.get("pack_key"),
            "quota": usage,
            "user_message": (
                "No AHJ portal found for this city — federal/state layers still apply. "
                "Confirm local fees with the building department."
            ),
        }
        _apply_paid_coverage(analysis, resolved, pack, [])
        return analysis

    ck = _cache_key(city, state, zip_code, portal)
    cached = _cache_get(ck)
    if cached:
        fee_rows = list(cached.get("fee_rows") or [])
        analysis = _merge_fees_into_analysis(
            analysis, fee_rows, scraped_url=str(cached.get("scraped_url") or portal)
        )
        analysis["paid_local"] = {
            "status": "ok",
            "method": "result_cache",
            "cache_hit": True,
            "pack_key": pack.get("pack_key"),
            "portal_url": portal,
            "scraped_url": cached.get("scraped_url"),
            "pages_scraped": 0,
            "pages_cap": max_pages(),
            "fee_rows_extracted": len(fee_rows),
            "quota": usage,
        }
        analysis["smart_confirm"] = {
            "status": "ok",
            "method": "paid_local_confirm_cache",
            "pack_key": pack.get("pack_key"),
            "portal_url": portal,
            "fee_rows_extracted": len(fee_rows),
        }
        _apply_paid_coverage(analysis, resolved, pack, fee_rows)
        return analysis

    pages_cap = max_pages()
    pages_scraped = 0
    fee_rows: List[Dict[str, Any]] = []
    scraped_url = portal
    method = "none"
    mapped: List[str] = []

    # 1) Cheap confirm first (no Firecrawl scrape)
    try:
        from cheap_page_confirm import merge_cheap_confirm_into_analysis, run_cheap_page_confirm

        cheap = run_cheap_page_confirm(portal, pack_urls=pack_urls, use_llm=True)
        if cheap.get("status") == "ok" and (cheap.get("fees") or cheap.get("notes")):
            analysis = merge_cheap_confirm_into_analysis(analysis, cheap)
            fee_rows = list(cheap.get("fees") or [])
            # Stamp planning-aid on cheap path too (F3)
            if fee_rows:
                analysis = _merge_fees_into_analysis(analysis, fee_rows, scraped_url=portal)
                fee_rows = list((analysis.get("fee_card") or {}).get("fees") or [])[:8]
            else:
                fc = dict(analysis.get("fee_card") or {})
                fc["planning_aid"] = True
                fc["paid_local_confirm"] = True
                fc["disclaimer"] = FEE_PLANNING_AID
                analysis["fee_card"] = fc
            method = "cheap_page_confirm"
            analysis["paid_local"] = {
                "status": "ok",
                "method": method,
                "cache_hit": False,
                "pack_key": pack.get("pack_key"),
                "portal_url": portal,
                "scraped_url": portal,
                "pages_scraped": 0,
                "pages_cap": pages_cap,
                "fee_rows_extracted": len(fee_rows),
                "quota": usage,
            }
            analysis["smart_confirm"] = {
                "status": "ok",
                "method": method,
                "pack_key": pack.get("pack_key"),
                "portal_url": portal,
                "scraped_url": portal,
                "fee_rows_extracted": len(fee_rows),
                "markdown_chars": cheap.get("markdown_chars") or 0,
            }
            _cache_set(
                ck,
                {"fee_rows": fee_rows, "scraped_url": portal, "method": method},
            )
            _apply_paid_coverage(analysis, resolved, pack, fee_rows)
            from cost_tracking import log_api_usage

            log_api_usage(
                project_key="paid_local",
                route="paid_local_confirm",
                model="cheap",
                meta={"method": method, "fees": len(fee_rows), "pages": 0},
            )
            return analysis
    except Exception as e:
        logger.warning("Paid local cheap confirm failed: %s", e)

    # 2) Map + scrape up to pages_cap (scored; parking rejected)
    mapped = _map_candidate_urls(portal, limit=pages_cap)
    targets: List[str] = []
    for u in mapped:
        if u not in targets:
            targets.append(u)
    if portal not in targets:
        targets.insert(0, portal)
    targets = targets[:pages_cap]

    from markdown_scraper import fetch_trusted_url_markdown

    md_combined = ""
    for target in targets:
        md = fetch_trusted_url_markdown(target, max_chars=12_000, allow_rescrape=True)
        pages_scraped += 1
        if not md:
            try:
                from cheap_page_confirm import fetch_page_markdown

                md = fetch_page_markdown(target, pack_urls=pack_urls + mapped, max_chars=12_000)
            except Exception:
                md = None
        if not md:
            continue
        scraped_url = target
        md_combined += "\n" + md
        fee_rows.extend(_extract_fee_rows(md, target))
        # Stop early if we already have useful fees
        if len(fee_rows) >= 3:
            break
        if pages_scraped >= pages_cap:
            break

    # Dedupe fee labels
    deduped: List[Dict[str, Any]] = []
    seen_labels: set = set()
    for row in fee_rows:
        key = str(row.get("label") or "")[:40]
        if key in seen_labels:
            continue
        seen_labels.add(key)
        deduped.append(row)
    fee_rows = deduped[:12]

    method = "bounded_scrape" if pages_scraped else "no_markdown"
    analysis = _merge_fees_into_analysis(analysis, fee_rows, scraped_url=scraped_url)
    analysis["paid_local"] = {
        "status": "ok" if (fee_rows or md_combined) else "no_markdown",
        "method": method,
        "cache_hit": False,
        "pack_key": pack.get("pack_key"),
        "portal_url": portal,
        "scraped_url": scraped_url,
        "mapped_urls": mapped[: pages_cap],
        "pages_scraped": pages_scraped,
        "pages_cap": pages_cap,
        "fee_rows_extracted": len(fee_rows),
        "markdown_chars": len(md_combined),
        "quota": usage,
    }
    analysis["smart_confirm"] = {
        "status": analysis["paid_local"]["status"],
        "method": f"paid_local_confirm:{method}",
        "pack_key": pack.get("pack_key"),
        "portal_url": portal,
        "scraped_url": scraped_url,
        "mapped_urls": mapped[:6],
        "fee_rows_extracted": len(fee_rows),
        "markdown_chars": len(md_combined),
    }
    _cache_set(
        ck,
        {"fee_rows": fee_rows, "scraped_url": scraped_url, "method": method},
    )
    _apply_paid_coverage(analysis, resolved, pack, fee_rows)

    try:
        from cost_tracking import log_api_usage

        log_api_usage(
            project_key="paid_local",
            route="paid_local_confirm",
            model="firecrawl" if pages_scraped else "none",
            meta={
                "method": method,
                "fees": len(fee_rows),
                "pages": pages_scraped,
                "pages_cap": pages_cap,
            },
        )
    except Exception:
        pass

    logger.info(
        "Paid local confirm pack=%s pages=%s/%s fees=%s method=%s",
        pack.get("pack_key"),
        pages_scraped,
        pages_cap,
        len(fee_rows),
        method,
    )
    return analysis


def _apply_paid_coverage(
    analysis: Dict[str, Any],
    resolved: Dict[str, Any],
    pack: Dict[str, Any],
    fee_rows: List[Dict[str, Any]],
) -> None:
    """Badge: paid local confirm — fees allowed when scrape grounded them."""
    from coverage_honesty import build_coverage_block

    citeable = bool(pack.get("citeable"))
    portal_only = bool(pack.get("portal_only"))
    if citeable:
        tier = "full_pack"
    elif fee_rows:
        tier = "paid_local"
    elif portal_only:
        tier = "portal_seed"
    else:
        tier = "federal_state"

    note = str(resolved.get("coverage_note") or "")
    if tier == "paid_local":
        note = (
            "Paid local confirm — AHJ pages scraped within page cap. "
            "Fee extracts are planning aids; confirm on the official schedule."
        )
    analysis["coverage"] = build_coverage_block(
        tier=tier if tier != "paid_local" else "portal_seed",
        coverage_note=note,
        pack_key=str(pack.get("pack_key") or ""),
        state_citeable=bool((resolved.get("state_pack") or {}).get("citeable")),
    )
    # Override for paid_local: allow fees + distinct badge
    if tier == "paid_local":
        analysis["coverage"] = {
            "tier": "paid_local",
            "badge": "Paid local confirm",
            "badge_short": "Paid local",
            "tone": "success",
            "warning": (
                "Page-capped · cached · not a full city pack. Fee dollars are planning aids from "
                "page text — confirm on the official AHJ schedule before bid. Not unlimited crawl."
            ),
            "note": note,
            "pack_key": pack.get("pack_key"),
            "state_citeable": bool((resolved.get("state_pack") or {}).get("citeable")),
            "fees_allowed": True,
            "depth_equals_beachhead": False,
        }
    j = dict(analysis.get("jurisdiction") or {})
    j["coverage_tier"] = analysis["coverage"]["tier"]
    j["coverage_badge"] = analysis["coverage"]["badge"]
    j["coverage_note"] = analysis["coverage"]["note"]
    analysis["jurisdiction"] = j
