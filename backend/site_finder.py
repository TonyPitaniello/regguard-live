"""
Official-page finder. One Firecrawl search at most. No scrape, map, or crawl.

Beachhead cities use the URLs already stored in ic_buyer_brief.py.
A department homepage is never the fee schedule.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_DAY_CACHE: Dict[str, Dict[str, Any]] = {}

JOBS = (
    "fee_schedule",
    "ordinance",
    "permit_application",
    "water_desk",
    "electric_utility",
)

_REJECT_HOST_BITS = (
    "blog",
    "news",
    "zillow",
    "realtor",
    "redfin",
    "apartments",
    "wikipedia",
    "medium.com",
    "facebook.",
    "linkedin.",
)

_NEIGHBOR_CITY_TOKENS = ("dallas", "plano", "austin", "fortworth", "fort worth")


def _day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _city_key(city: str) -> str:
    key = " ".join(str(city or "").strip().lower().replace(".", "").split())
    if key in ("fort worth", "ft worth"):
        return "fort worth"
    return key


def _cache_key(address: str, city: str, state: str, zip_code: str) -> str:
    return "|".join(
        (
            " ".join(str(address or "").lower().split()),
            _city_key(city),
            str(state or "").strip().lower(),
            "".join(c for c in str(zip_code or "") if c.isdigit())[:5],
        )
    )


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _is_homepage(url: str) -> bool:
    path = (urlparse(url).path or "").strip("/")
    if not path:
        return True
    low = path.lower()
    if low.endswith(".pdf"):
        return False
    if any(bit in low for bit in ("fee", "ordinance", "permit", "apply", "form", "schedule")):
        return False
    return path.count("/") <= 1


def _row(job: str, url: str, why: str) -> Dict[str, str]:
    clean = str(url or "").strip()
    if clean and not clean.startswith("https://"):
        clean = ""
        why = "No official https page."
    return {
        "job": job,
        "url": clean,
        "host": _host(clean),
        "why": why,
        "status": "Source" if clean else "Unverified",
    }


def _unverified(job: str, why: str = "No official page for this city.") -> Dict[str, str]:
    return _row(job, "", why)


def beachhead_rows(city: str) -> Optional[List[Dict[str, str]]]:
    """URLs already transcribed. None when this city is not one of the four."""
    key = _city_key(city)
    try:
        from ic_buyer_brief import (
            AUSTIN_APPLY,
            AUSTIN_ENERGY,
            AUSTIN_FEE_PDF,
            AUSTIN_WATER,
            DALLAS_APPLY,
            DALLAS_FEE_PDF,
            DALLAS_WW,
            FW_APPLY,
            FW_FEE,
            FW_WATER,
            ONCOR_INTAKE,
            PLANO_APPLY,
            PLANO_DRAIN,
            PLANO_FEE_PDF,
        )
    except Exception:
        return None
    table = {
        "dallas": [
            ("fee_schedule", DALLAS_FEE_PDF, "July 1, 2025 fee summary stored for Dallas."),
            ("ordinance", DALLAS_FEE_PDF, "That summary is the table that states the commercial lines."),
            ("permit_application", DALLAS_APPLY, "DallasNow application stored for Dallas."),
            ("water_desk", DALLAS_WW, "Water and wastewater design-plan form stored for Dallas."),
            ("electric_utility", ONCOR_INTAKE, "Oncor commercial intake stored for Dallas. No ESI ID."),
        ],
        "plano": [
            ("fee_schedule", PLANO_FEE_PDF, "Ordinance 2025-11-4 fee PDF stored for Plano."),
            ("ordinance", PLANO_FEE_PDF, "That PDF is Ordinance 2025-11-4 Exhibit A."),
            ("permit_application", PLANO_APPLY, "Electronic submittal form stored for Plano."),
            ("water_desk", PLANO_DRAIN, "Drainage checklist stored for Plano."),
            ("electric_utility", ONCOR_INTAKE, "Oncor commercial intake stored for Plano. No ESI ID."),
        ],
        "austin": [
            ("fee_schedule", AUSTIN_FEE_PDF, "Commercial fee PDF stored for Austin."),
            ("ordinance", AUSTIN_FEE_PDF, "That PDF is the commercial fee table."),
            ("permit_application", AUSTIN_APPLY, "Citizen portal application stored for Austin."),
            ("water_desk", AUSTIN_WATER, "Austin Water utility development page stored for Austin."),
            ("electric_utility", AUSTIN_ENERGY, "Austin Energy contractor forms stored for Austin."),
        ],
        "fort worth": [
            ("fee_schedule", FW_FEE, "October 1, 2026 fee schedule stored for Fort Worth."),
            ("ordinance", FW_FEE, "That ordinance PDF is the fee table."),
            ("permit_application", FW_APPLY, "Accela application stored for Fort Worth."),
            ("water_desk", FW_WATER, "Water Applications contact page stored for Fort Worth."),
            ("electric_utility", ONCOR_INTAKE, "Oncor commercial intake stored for Fort Worth. No ESI ID."),
        ],
    }
    rows = table.get(key)
    if not rows:
        return None
    return [_row(job, url, why) for job, url, why in rows]


def _stored_hosts(city: str, state: str) -> set:
    hosts = set()
    for row in beachhead_rows(city) or []:
        if row.get("host"):
            hosts.add(row["host"])
    try:
        from ahj_catalog import lookup_ahj

        rec = lookup_ahj(city, state, "")
        if rec:
            for key in ("portal_url", "fees_url", "apply_url"):
                host = _host(str(rec.get(key) or ""))
                if host:
                    hosts.add(host)
    except Exception:
        pass
    return hosts


def _official(url: str, *, city: str, state: str, stored: set) -> bool:
    if not str(url or "").startswith("https://"):
        return False
    host = _host(url)
    if not host:
        return False
    blob = f"{host} {url}".lower()
    if any(bit in blob for bit in _REJECT_HOST_BITS):
        return False
    if "esi" in url.lower():
        return False
    st = str(state or "").strip().lower()
    official = (
        host.endswith(".gov")
        or host.endswith(".us")
        or "municode.com" in host
        or "civicplus.com" in host
        or "accela.com" in host
        or host in stored
    )
    if st and (host.endswith(f".{st}.us") or f".{st}." in host):
        official = True
    if not official:
        return False
    return not _names_neighbor(url, city)


def _names_neighbor(url: str, city: str) -> bool:
    low = url.lower()
    here = _city_key(city).replace(" ", "")
    for token in _NEIGHBOR_CITY_TOKENS:
        compact = token.replace(" ", "")
        if compact and compact != here and compact in low.replace(" ", ""):
            if here and here in low.replace(" ", ""):
                continue
            return True
    return False


def _names_this_city(url: str, title: str, city: str) -> bool:
    token = _city_key(city).replace(" ", "")
    if not token:
        return False
    blob = f"{url} {title}".lower().replace(" ", "")
    return token in blob


def _score(job: str, url: str, title: str) -> int:
    blob = f"{title} {url}".lower()
    if _is_homepage(url):
        return 1 if job != "fee_schedule" else -1
    score = 0
    if job == "fee_schedule":
        if url.lower().endswith(".pdf"):
            score += 50
        if "fee" in blob and ("schedule" in blob or "pdf" in blob):
            score += 40
        if "ordinance" in blob:
            score += 10
    elif job == "ordinance":
        if "ordinance" in blob or "exhibit" in blob or "fee" in blob:
            score += 40
        if url.lower().endswith(".pdf"):
            score += 20
    elif job == "permit_application":
        if any(bit in blob for bit in ("accela", "apply", "application", "citizenportal", "submittal")):
            score += 40
        if "permit" in blob:
            score += 15
    elif job == "water_desk":
        if any(bit in blob for bit in ("water", "drainage", "wastewater", "storm")):
            score += 40
    elif job == "electric_utility":
        if any(bit in blob for bit in ("electric", "utility", "energy", "power", "oncor")):
            score += 40
    return score


def _assign(hits: List[Dict[str, str]], *, city: str, state: str, jobs: tuple) -> List[Dict[str, str]]:
    stored = _stored_hosts(city, state)
    ranked: List[tuple] = []
    for hit in hits:
        url = str(hit.get("url") or "").strip()
        title = str(hit.get("title") or "")
        if not _official(url, city=city, state=state, stored=stored):
            continue
        if not _names_this_city(url, title, city):
            continue
        ranked.append((url, title))
    rows = []
    used = set()
    for job in jobs:
        best_url = ""
        best_title = ""
        best_score = 0
        for url, title in ranked:
            if url in used:
                continue
            score = _score(job, url, title)
            if job == "fee_schedule" and (_is_homepage(url) or score < 10):
                continue
            if score > best_score:
                best_score = score
                best_url = url
                best_title = title
        if not best_url:
            rows.append(_unverified(job))
            continue
        used.add(best_url)
        why = best_title.strip() or "Official page names this job."
        if job == "fee_schedule":
            why = f"Fee schedule: {why}"[:180]
        rows.append(_row(job, best_url, why[:180]))
    return rows


def _default_search(query: str) -> List[Dict[str, str]]:
    """One /search. scrape_options stays unset so this cannot scrape."""
    try:
        from scraper import _get_client, _web_hits_raw
    except Exception as exc:
        logger.warning("site finder has no search client: %s", exc)
        return []
    try:
        fc = _get_client()
        result = fc.search(query, limit=5, sources=["web"], location="US")
    except Exception as exc:
        logger.warning("site finder search failed: %s", exc)
        return []
    hits = _web_hits_raw(result)
    out = []
    for hit in hits:
        url = str((hit or {}).get("url") or "").strip()
        if url:
            out.append({"url": url, "title": str((hit or {}).get("title") or "")})
    return out


def _jobs_for_rung(rung: str) -> tuple:
    if rung == "estimator":
        return ("fee_schedule",)
    if rung in ("pro", "ic"):
        return JOBS
    return tuple()


def _cap_open(email: str, rung: str) -> bool:
    if rung != "pro":
        return True
    try:
        from paid_local_confirm import get_paid_local_usage

        usage = get_paid_local_usage(email)
        return bool(usage.get("allowed", True))
    except Exception:
        return True


def find_official_sites(
    *,
    address: str,
    city: str,
    state: str,
    zip_code: str = "",
    county: str = "",
    rung: str,
    email: str = "",
    searcher: Optional[Callable[[str], List[Dict[str, str]]]] = None,
) -> Dict[str, Any]:
    """
    Return at most five rows. Searches is 0 or 1.
    Free never searches. Estimator searches only the fee-schedule job.
    """
    rung_key = str(rung or "").strip().lower()
    jobs = _jobs_for_rung(rung_key)
    base = {
        "address": address,
        "city": city,
        "county": county,
        "state": state,
        "zip": zip_code,
        "rung": rung_key,
        "searches": 0,
        "scrapes": 0,
        "maps": 0,
        "crawls": 0,
        "cache_hit": False,
        "rows": [],
    }
    if not jobs:
        return base

    stored = beachhead_rows(city)
    if stored is not None:
        wanted = [row for row in stored if row["job"] in jobs]
        base["rows"] = wanted
        base["cache_hit"] = True
        return base

    key = _cache_key(address, city, state, zip_code)
    with _LOCK:
        cached = _DAY_CACHE.get(key)
    fresh = cached if cached and cached.get("day") == _day() else None
    by_job = {row["job"]: row for row in (fresh or {}).get("rows") or []}

    if fresh and all(job in by_job for job in jobs):
        base["rows"] = [by_job[job] for job in jobs]
        base["cache_hit"] = True
        return base

    hits: List[Dict[str, str]] = []
    if _cap_open(email, rung_key):
        missing = [job for job in jobs if job not in by_job]
        if missing:
            query_job = missing[0].replace("_", " ")
            query = (
                f"{city} {state} {query_job} commercial building permit "
                "fee schedule ordinance"
            )
            finder = searcher or _default_search
            try:
                hits = list(finder(query) or [])
            except Exception as exc:
                logger.warning("site finder searcher failed: %s", exc)
                hits = []
            base["searches"] = 1

    assigned = {row["job"]: row for row in (_assign(hits, city=city, state=state, jobs=jobs) if hits else [])}
    rows = []
    for job in jobs:
        if job in by_job:
            rows.append(by_job[job])
        elif job in assigned and assigned[job].get("url"):
            rows.append(assigned[job])
        else:
            rows.append(_unverified(job))
    base["rows"] = rows[:5]
    if base["searches"]:
        with _LOCK:
            _DAY_CACHE[key] = {"day": _day(), "rows": rows}
    return base
