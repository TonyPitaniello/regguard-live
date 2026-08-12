"""
Cached **markdown-only** Firecrawl scrape for trusted URLs (``.gov`` / Municode).

Use for cheap follow-up text when SERP snippets are insufficient — avoids repeat
scrapes of the same AHJ page within TTL. Disable with ``REG_GUARD_MARKDOWN_SCRAPER_CACHE=0``.
"""
from __future__ import annotations

import hashlib
import os
import threading
import time
from typing import Optional

from scraper import FIRECRAWL_MAX_AGE_MS, _get_client, url_matches_trust_policy

_LOCK = threading.Lock()
_MD_CACHE: dict[str, tuple[float, str]] = {}
_MD_MAX = 256


def markdown_scraper_cache_enabled() -> bool:
    v = (os.environ.get("REG_GUARD_MARKDOWN_SCRAPER_CACHE") or "1").strip().lower()
    return v not in ("0", "false", "no", "off")


def clear_markdown_scrape_cache() -> None:
    with _LOCK:
        _MD_CACHE.clear()


def _cache_ttl_sec() -> float:
    try:
        return max(120.0, float(os.environ.get("REG_GUARD_MARKDOWN_SCRAPER_TTL_SEC", "86400")))
    except ValueError:
        return 86400.0


def _key(url: str) -> str:
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()


def fetch_trusted_url_markdown(
    url: str,
    *,
    max_chars: int = 15_000,
    allow_rescrape: bool = True,
) -> Optional[str]:
    """
    Return main-content markdown for ``url`` if it passes trust policy; otherwise ``None``.

    On Firecrawl or import errors, returns ``None`` (callers should tolerate miss).

    Free FinOps path should pass ``allow_rescrape=False`` or keep
    ``FREE_TRIAL_MARKDOWN_CONFIRM=0`` so free never pays for page scrapes.
    Global kill: ``REG_GUARD_ALLOW_MARKDOWN_RESCRAPE=0``.
    """
    if not allow_rescrape:
        return None
    global_flag = (os.environ.get("REG_GUARD_ALLOW_MARKDOWN_RESCRAPE") or "1").strip().lower()
    if global_flag in ("0", "false", "no", "off"):
        return None

    u = (url or "").strip()
    if not u or not url_matches_trust_policy(u):
        return None

    if markdown_scraper_cache_enabled():
        k = _key(u)
        now = time.monotonic()
        with _LOCK:
            row = _MD_CACHE.get(k)
            if row:
                ts, text = row
                if now - ts <= _cache_ttl_sec():
                    return text

    try:
        fc = _get_client()
    except ValueError:
        return None

    try:
        doc = fc.scrape(
            u,
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
    except Exception:
        return None

    text: Optional[str] = None
    if doc is not None:
        text = getattr(doc, "markdown", None)
        if text is None and hasattr(doc, "model_dump"):
            d = doc.model_dump()
            if isinstance(d, dict):
                text = d.get("markdown")

    if not text or not str(text).strip():
        return None
    out = str(text).strip()
    if len(out) > max_chars:
        out = out[: max(0, max_chars - 1)] + "…"

    if markdown_scraper_cache_enabled():
        k = _key(u)
        with _LOCK:
            while len(_MD_CACHE) >= _MD_MAX:
                try:
                    drop = next(iter(_MD_CACHE.keys()))
                    del _MD_CACHE[drop]
                except StopIteration:
                    break
            _MD_CACHE[k] = (time.monotonic(), out)

    return out
