"""
Cheap page confirm — KDnuggets-style HTML → Markdown → small LLM extract.

Bypasses Firecrawl page scrapes: requests + BeautifulSoup + markdownify + Haiku/nano.
Only allowlisted trusted URLs (.gov / Municode / pack portal hosts).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_MD_CACHE: dict[str, tuple[float, str]] = {}
_RESULT_CACHE: dict[str, tuple[float, Dict[str, Any]]] = {}
_MD_MAX = 256

UA = "RegGuardCheapConfirm/1.0 (+https://app.regguardagent.com)"


def _env_on(name: str, default: str = "1") -> bool:
    return (os.getenv(name) or default).strip().lower() in ("1", "true", "yes", "on")


def cheap_confirm_enabled() -> bool:
    """Free-path cheap confirm (default on)."""
    return _env_on("FREE_TRIAL_CHEAP_CONFIRM", "1")


def cheap_confirm_model() -> str:
    return (os.getenv("CHEAP_CONFIRM_MODEL") or "claude-3-5-haiku-latest").strip()


def _cache_ttl_sec() -> float:
    try:
        return max(300.0, float(os.getenv("CHEAP_CONFIRM_CACHE_TTL_SEC") or "604800"))
    except ValueError:
        return 604800.0


def _timeout_sec() -> float:
    try:
        return max(3.0, min(12.0, float(os.getenv("CHEAP_CONFIRM_TIMEOUT_SEC") or "8")))
    except ValueError:
        return 8.0


def _max_md_chars() -> int:
    try:
        return max(2000, min(20_000, int(os.getenv("CHEAP_CONFIRM_MAX_CHARS") or "10000")))
    except ValueError:
        return 10_000


def _key(url: str) -> str:
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def url_allowed_for_cheap_confirm(
    url: str,
    *,
    pack_urls: Optional[List[str]] = None,
) -> bool:
    """Trust policy OR same host as a curated pack portal/fees URL."""
    if not url:
        return False
    try:
        from scraper import url_matches_trust_policy

        if url_matches_trust_policy(url):
            return True
    except Exception:
        pass
    host = _host(url)
    if not host:
        return False
    for pu in pack_urls or []:
        ph = _host(str(pu or ""))
        if ph and (host == ph or host.endswith("." + ph) or ph.endswith("." + host)):
            return True
    return False


def fetch_page(url: str, *, timeout: Optional[float] = None) -> str:
    """Download raw HTML."""
    t = timeout if timeout is not None else _timeout_sec()
    resp = requests.get(
        url,
        headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"},
        timeout=t,
        allow_redirects=True,
    )
    resp.raise_for_status()
    return resp.text or ""


def clean_html(html: str) -> str:
    try:
        from bs4 import BeautifulSoup, Comment
        from ftfy import fix_text
    except ImportError as e:
        raise RuntimeError("beautifulsoup4 and ftfy required for cheap_page_confirm") from e

    html = fix_text(html or "")
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "img",
            "iframe",
            "nav",
            "header",
            "footer",
            "aside",
            "form",
            "button",
        ]
    ):
        tag.decompose()
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()

    noise_words = [
        "cursor",
        "modal",
        "popup",
        "floating",
        "signup",
        "login",
        "cookie",
        "banner",
        "navbar",
        "menu",
        "footer",
        "header",
        "subscribe",
        "newsletter",
        "loading",
        "auth",
        "w-nav",
        "w-form",
    ]
    to_remove = []
    for tag in soup.find_all(True):
        if tag.attrs is None:
            continue
        class_value = tag.get("class", [])
        id_value = tag.get("id", "")
        class_text = (
            " ".join(class_value).lower()
            if isinstance(class_value, list)
            else str(class_value).lower()
        )
        id_text = str(id_value).lower()
        if any(word in class_text or word in id_text for word in noise_words):
            to_remove.append(tag)
    for tag in to_remove:
        tag.decompose()

    body = soup.body if soup.body else soup
    return str(body)


def html_to_markdown(html: str, *, max_chars: Optional[int] = None) -> str:
    try:
        from ftfy import fix_text
        from markdownify import markdownify as markdownify_html
    except ImportError as e:
        raise RuntimeError("markdownify and ftfy required for cheap_page_confirm") from e

    md = markdownify_html(html or "", heading_style="ATX", bullets="-")
    md = fix_text(md)
    md = re.sub(r"!\[.*?\]\(.*?\)", "", md)
    md = re.sub(r"[ \t]+", " ", md)
    md = re.sub(r"\n{3,}", "\n\n", md)

    skip = {
        "click to try",
        "wait...",
        "product",
        "resources",
        "company",
        "skip to main content",
        "share this page",
    }
    lines = []
    for line in md.splitlines():
        line = line.strip()
        if not line or line.lower() in skip:
            continue
        lines.append(line)
    out = "\n".join(lines)
    cap = max_chars if max_chars is not None else _max_md_chars()
    if len(out) > cap:
        out = out[: cap - 40] + "\n\n[truncated for cheap confirm]"
    return out


def fetch_page_markdown(
    url: str,
    *,
    pack_urls: Optional[List[str]] = None,
    max_chars: Optional[int] = None,
) -> Optional[str]:
    """Trusted fetch → clean → markdown, with TTL cache."""
    if not url_allowed_for_cheap_confirm(url, pack_urls=pack_urls):
        return None
    k = _key(url)
    now = time.time()
    with _LOCK:
        hit = _MD_CACHE.get(k)
        if hit and hit[0] > now:
            return hit[1]

    try:
        raw = fetch_page(url)
        cleaned = clean_html(raw)
        md = html_to_markdown(cleaned, max_chars=max_chars)
    except Exception as e:
        logger.warning("Cheap confirm fetch failed for %s: %s", url, e)
        return None

    if not md or len(md) < 40:
        return None

    ttl = _cache_ttl_sec()
    with _LOCK:
        if len(_MD_CACHE) >= _MD_MAX:
            # Drop oldest roughly
            oldest = sorted(_MD_CACHE.items(), key=lambda kv: kv[1][0])[:64]
            for ok, _ in oldest:
                _MD_CACHE.pop(ok, None)
        _MD_CACHE[k] = (now + ttl, md)
    return md


def _regex_fee_rows(markdown: str, source_url: str) -> List[Dict[str, Any]]:
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
                "source_label": "Cheap page confirm",
            }
        )
        if len(rows) >= 8:
            break
    return rows


def _llm_extract(markdown_text: str, source_url: str) -> Dict[str, Any]:
    """
    Small Anthropic extract. On missing key / failure, returns empty fees
    (caller still has regex fallback).
    """
    from anthropic import Anthropic

    key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        return {"fees": [], "notes": [], "verified": False, "llm": False}

    prompt = f"""You are a pre-bid diligence assistant for contractors.

Extract ONLY factual fee / permit / timeline info from the webpage Markdown.
Do not invent amounts or rules that are not on the page.
If nothing useful, return empty arrays.

Return ONLY valid JSON with this shape:
{{
  "fees": [{{"label": "...", "amount_usd": number_or_null, "detail": "..."}}],
  "notes": ["short planning notes from the page"],
  "timeline_hint": "short string or empty"
}}

Source URL: {source_url}

Webpage Markdown:
{markdown_text[:9000]}
"""
    try:
        client = Anthropic(api_key=key)
        msg = client.messages.create(
            model=cheap_confirm_model(),
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        text = ""
        for block in msg.content or []:
            t = getattr(block, "text", None)
            if t:
                text += t
        text = (text or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        data = json.loads(text)
        if not isinstance(data, dict):
            return {"fees": [], "notes": [], "verified": False, "llm": True}
        fees_out: List[Dict[str, Any]] = []
        for row in list(data.get("fees") or [])[:8]:
            if not isinstance(row, dict):
                continue
            amt = row.get("amount_usd")
            if amt is not None:
                try:
                    amt = float(amt)
                except (TypeError, ValueError):
                    amt = None
            fees_out.append(
                {
                    "label": str(row.get("label") or "Fee")[:120],
                    "amount_usd": amt,
                    "detail": str(row.get("detail") or "From page extract — confirm on schedule")[
                        :200
                    ],
                    "verified": True,
                    "source_url": source_url,
                    "source_label": "Cheap page confirm (LLM)",
                }
            )
        notes = [str(n)[:200] for n in list(data.get("notes") or [])[:5] if n]
        return {
            "fees": fees_out,
            "notes": notes,
            "timeline_hint": str(data.get("timeline_hint") or "")[:160],
            "verified": bool(fees_out or notes),
            "llm": True,
        }
    except Exception as e:
        logger.warning("Cheap confirm LLM extract failed: %s", e)
        return {"fees": [], "notes": [], "verified": False, "llm": False}


def run_cheap_page_confirm(
    url: str,
    *,
    pack_urls: Optional[List[str]] = None,
    use_llm: bool = True,
) -> Dict[str, Any]:
    """
    One cheap confirm: fetch+markdown (+ optional LLM), merge regex fees.
    Returns structured dict for punch/fee_card merge.
    """
    empty = {
        "status": "skipped",
        "source_url": url,
        "fees": [],
        "notes": [],
        "timeline_hint": "",
        "verified": False,
        "markdown_chars": 0,
    }
    if not url:
        return empty

    cache_k = _key(f"{url}|llm={int(use_llm)}")
    now = time.time()
    with _LOCK:
        hit = _RESULT_CACHE.get(cache_k)
        if hit and hit[0] > now:
            return dict(hit[1])

    if not url_allowed_for_cheap_confirm(url, pack_urls=pack_urls):
        out = {**empty, "status": "blocked_trust", "reason": "url_not_allowlisted"}
        return out

    md = fetch_page_markdown(url, pack_urls=pack_urls)
    if not md:
        return {**empty, "status": "no_markdown"}

    regex_fees = _regex_fee_rows(md, url)
    llm_part: Dict[str, Any] = {"fees": [], "notes": [], "timeline_hint": "", "llm": False}
    if use_llm:
        llm_part = _llm_extract(md, url)

    # Prefer LLM fees when present; else regex
    fees = list(llm_part.get("fees") or []) or regex_fees
    if llm_part.get("fees") and regex_fees:
        seen: Set[str] = {str(f.get("label") or "")[:40] for f in fees}
        for row in regex_fees:
            key = str(row.get("label") or "")[:40]
            if key not in seen:
                fees.append(row)
                seen.add(key)

    out = {
        "status": "ok",
        "source_url": url,
        "fees": fees[:10],
        "notes": list(llm_part.get("notes") or [])[:5],
        "timeline_hint": str(llm_part.get("timeline_hint") or ""),
        "verified": bool(fees),
        "markdown_chars": len(md),
        "llm_used": bool(llm_part.get("llm")),
    }
    ttl = _cache_ttl_sec()
    with _LOCK:
        _RESULT_CACHE[cache_k] = (now + ttl, dict(out))
    return out


def merge_cheap_confirm_into_analysis(
    analysis: Dict[str, Any],
    confirm: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge fee rows + notes into analysis fee_card / punch_list."""
    if not isinstance(analysis, dict) or not isinstance(confirm, dict):
        return analysis
    if confirm.get("status") != "ok":
        analysis["cheap_confirm"] = {
            "status": confirm.get("status"),
            "source_url": confirm.get("source_url"),
            "reason": confirm.get("reason"),
        }
        return analysis

    fees = list(confirm.get("fees") or [])
    if fees:
        fee_card = dict(analysis.get("fee_card") or {})
        existing = list(fee_card.get("fees") or [])
        seen = {str(r.get("label") or "")[:40] for r in existing}
        for row in fees:
            key = str(row.get("label") or "")[:40]
            if key not in seen:
                existing.insert(0, row)
                seen.add(key)
        fee_card["fees"] = existing[:12]
        fee_card["cheap_confirm"] = True
        if confirm.get("timeline_hint"):
            fee_card["timeline"] = confirm["timeline_hint"]
        analysis["fee_card"] = fee_card

        punch = analysis.get("punch_list") or {}
        items = list(punch.get("punch_list") or [])
        top = fees[0]
        amt = top.get("amount_usd")
        task = (
            f"Confirm AHJ fee extract: {top.get('label')} (~${amt:,.0f})"
            if isinstance(amt, (int, float))
            else f"Confirm AHJ fee extract: {top.get('label')}"
        )
        items.insert(
            0,
            {
                "priority": "HIGH",
                "task": task,
                "responsible_party": "Estimator",
                "timeline": "Before bid",
                "estimated_cost": amt if isinstance(amt, (int, float)) else 0,
                "notes": "From cheap page confirm — verify on official schedule",
                "verified": True,
                "cost_verified": False,
                "source_url": top.get("source_url") or confirm.get("source_url"),
                "source_label": "Cheap page confirm",
            },
        )
        for note in list(confirm.get("notes") or [])[:2]:
            items.append(
                {
                    "priority": "MEDIUM",
                    "task": str(note)[:120],
                    "responsible_party": "Estimator",
                    "timeline": "Before bid",
                    "estimated_cost": 0,
                    "notes": "Note from cheap page confirm",
                    "verified": True,
                    "cost_verified": False,
                    "source_url": confirm.get("source_url"),
                    "source_label": "Cheap page confirm",
                }
            )
        punch["punch_list"] = items
        analysis["punch_list"] = punch

    analysis["cheap_confirm"] = {
        "status": "ok",
        "source_url": confirm.get("source_url"),
        "fee_rows": len(fees),
        "markdown_chars": confirm.get("markdown_chars"),
        "llm_used": confirm.get("llm_used"),
    }
    return analysis
