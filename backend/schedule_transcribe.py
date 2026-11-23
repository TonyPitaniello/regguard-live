"""
Turn shortlist markdown into the fee rows the pack and the CSV already print.

A number is kept only when that line states it. A homepage is not a fee source.
Beachhead cities keep the rows in ic_buyer_brief.py.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from ic_buyer_brief import (
    AUSTIN_FEE_PDF,
    DALLAS_FEE_PDF,
    FW_FEE,
    PLANO_FEE_PDF,
    note_without_unstated_dollars,
)

_MONEY = re.compile(r"\$\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?|\d+(?:\.[0-9]+)?)")
_RATE = re.compile(
    r"per\s+(?:square\s+foot|sq\.?\s*ft)|%\s*of|percent of|valuation|appraisal|market value",
    re.I,
)
_DEPENDS = re.compile(
    r"square feet|sq\.?\s*ft|valuation|appraisal|market value|building area|named building|per building",
    re.I,
)
_TOTAL = re.compile(r"\b(permit total|total permit|building permit)\b", re.I)
_PHONE = re.compile(r"\(?\d{3}\)?[.\-\s]\d{3}[.\-\s]\d{4}")
_EMAIL = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)
_SEQUENCE = re.compile(
    r"([^.!\n]{0,80}(issued before|before a trade|file commercial|electronic submittal|commercial plan review)[^.!\n]{0,120})",
    re.I,
)

_BEACHHEAD_FEES = {
    "dallas": DALLAS_FEE_PDF,
    "plano": PLANO_FEE_PDF,
    "austin": AUSTIN_FEE_PDF,
    "fort worth": FW_FEE,
}
_BLANK = "A blank line has no dollar."


def _city_key(city: str) -> str:
    key = " ".join(str(city or "").strip().lower().replace(".", "").split())
    if key in ("ft worth", "fort worth"):
        return "fort worth"
    return key


def is_beachhead_city(city: str) -> bool:
    return _city_key(city) in _BEACHHEAD_FEES


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


def _amount(raw: str) -> float:
    return float(raw.replace(",", ""))


def _effective_iso(text: str) -> str:
    """A date the page states as effective. Empty when the page states none."""
    named = re.search(
        r"effective\s+(January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+(\d{1,2}),\s+(\d{4})",
        text or "",
        re.I,
    )
    months = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }
    if named:
        month = months[named.group(1).lower()]
        return f"{int(named.group(3)):04d}-{month:02d}-{int(named.group(2)):02d}"
    iso = re.search(r"effective\s+(\d{4}-\d{2}-\d{2})", text or "", re.I)
    if iso:
        return iso.group(1)
    slash = re.search(r"effective\s+(\d{1,2})/(\d{1,2})/(\d{4})", text or "", re.I)
    if slash:
        return f"{int(slash.group(3)):04d}-{int(slash.group(1)):02d}-{int(slash.group(2)):02d}"
    return ""


def _blank_row(label: str, url: str) -> Dict[str, Any]:
    note = note_without_unstated_dollars(f"{_BLANK} confirm-on-schedule.")
    return {
        "label": label,
        "amount_usd": None,
        "detail": note,
        "note": note,
        "verified": False,
        "amount_requires_schedule": True,
        "status": "confirm-on-schedule",
        "source_url": url if str(url).startswith("https://") and not _is_homepage(url) else "",
        "source_label": "Source" if url.startswith("https://") else "Unverified",
        "trade": "GENERAL",
    }


def _stated_row(label: str, amount: float, url: str) -> Dict[str, Any]:
    return {
        "label": label[:120] or "Fee line",
        "amount_usd": amount,
        "detail": "",
        "note": "",
        "verified": True,
        "amount_requires_schedule": False,
        "status": "",
        "source_url": url,
        "source_label": "Source",
        "trade": "GENERAL",
    }


def _foreign_beachhead_source(url: str, city: str) -> bool:
    """A Dallas, Plano, Austin, or Fort Worth fee document does not price another city."""
    here = _city_key(city)
    for name, fee_url in _BEACHHEAD_FEES.items():
        if name == here:
            continue
        if fee_url and fee_url in url:
            return True
    return False


def transcribe_page(markdown: str, url: str, *, city: str) -> List[Dict[str, Any]]:
    """Fee rows from one page. No summed total and no rate turned into a permit."""
    if not str(url or "").startswith("https://") or _is_homepage(url):
        return []
    if _foreign_beachhead_source(url, city):
        return []
    text = markdown or ""
    depends = bool(_DEPENDS.search(text))
    effective = _effective_iso(text)
    rows: List[Dict[str, Any]] = []
    seen = set()
    for line in text.splitlines():
        raw = line.strip()
        if not raw or len(raw) > 240:
            continue
        source_line = raw
        if _RATE.search(raw):
            source_line = _RATE.split(raw)[0]
            if re.search(r"\$\s*[\d,.]+\s*$", source_line.strip()):
                continue
        match = _MONEY.search(source_line)
        if not match:
            continue
        amount = _amount(match.group(1))
        if amount <= 0 or amount > 5_000_000:
            continue
        label = re.sub(r"[#*_`>|]+", "", raw[: match.start()]).strip(" :-") or "Fee line"
        label = re.sub(r"\s+", " ", label)[:120]
        if depends and _TOTAL.search(label) and "base" not in label.lower():
            continue
        key = (label.lower(), amount)
        if key in seen:
            continue
        seen.add(key)
        row = _stated_row(label, amount, url)
        if effective:
            row["status"] = f"effective {effective}"
        rows.append(row)
        if len(rows) >= 12:
            break
    if depends:
        rows.append(_blank_row("Commercial permit total", url))
    return rows


def _fee_source(analysis: Dict[str, Any]) -> str:
    finder = analysis.get("site_finder") if isinstance(analysis.get("site_finder"), dict) else {}
    for job in ("fee_schedule", "ordinance"):
        for row in finder.get("rows") or []:
            if isinstance(row, dict) and row.get("job") == job:
                url = str(row.get("url") or "").strip()
                if url.startswith("https://") and not _is_homepage(url):
                    return url
    return ""


def _pages(analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    found: List[Dict[str, str]] = []
    seen = set()
    for page in analysis.get("shortlist_pages") or []:
        if not isinstance(page, dict):
            continue
        url = str(page.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        found.append({"url": url, "markdown": str(page.get("markdown") or "")})
    if found:
        return found
    try:
        from shortlist_scrape import cached_markdown
    except Exception:
        return found
    finder = analysis.get("site_finder") if isinstance(analysis.get("site_finder"), dict) else {}
    for row in finder.get("rows") or []:
        if not isinstance(row, dict):
            continue
        url = str(row.get("url") or "").strip()
        if not url.startswith("https://") or url in seen:
            continue
        text = cached_markdown(url)
        if not text:
            continue
        seen.add(url)
        found.append({"url": url, "markdown": text})
    return found


def _contact(text: str) -> str:
    phone = _PHONE.search(text or "")
    email = _EMAIL.search(text or "")
    bits = []
    if phone:
        bits.append(phone.group(0))
    if email:
        bits.append(email.group(0))
    return " ".join(bits)


def _clocks(pages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    desks = (
        ("building permit", ("building permit", "building department", "permit desk"), "AHJ"),
        ("electric utility", ("electric", "utility", "power"), "UTILITY"),
        ("water or drainage", ("water", "drainage", "wastewater"), "WATER"),
    )
    clocks = []
    for name, needles, track in desks:
        for page in pages:
            text = page.get("markdown") or ""
            low = text.lower()
            if not any(needle in low for needle in needles):
                continue
            contact = _contact(text)
            owner = name if not contact else f"{name} {contact}"
            clocks.append(
                {
                    "name": name,
                    "detail": "The call stays with the buyer.",
                    "owner": owner[:80],
                    "track": track,
                    "url": page["url"],
                }
            )
            break
    return clocks


def sequence_sentence(analysis: Dict[str, Any], *, city: str) -> Optional[Dict[str, str]]:
    """One sequence fact from a commercial permit page. No dollar."""
    if is_beachhead_city(city):
        return None
    for page in _pages(analysis):
        text = page.get("markdown") or ""
        # A fee line that mentions plan review is not the permit sequence.
        for match in _SEQUENCE.finditer(text):
            raw = match.group(1)
            if "$" in raw:
                continue
            sentence = note_without_unstated_dollars(re.sub(r"\s+", " ", raw).strip(" -"))
            if not sentence or "$" in sentence:
                continue
            return {
                "task": sentence[:180],
                "source_url": page["url"],
                "source_label": "Source",
            }
    return None


def apply_transcribed_schedule(analysis: Dict[str, Any], *, city: str, portal: str = "") -> bool:
    """
    Replace the fee card for a city outside the four beachheads.
    Returns False when the beachhead brief stays in charge.
    """
    if is_beachhead_city(city):
        return False
    pages = _pages(analysis)
    fees: List[Dict[str, Any]] = []
    for page in pages:
        fees.extend(transcribe_page(page["markdown"], page["url"], city=city))
    fee_url = _fee_source(analysis) or ""
    if not fee_url:
        for page in pages:
            if page["url"].lower().split("?", 1)[0].endswith(".pdf") and not _is_homepage(page["url"]):
                fee_url = page["url"]
                break
    if not fees:
        fees = [_blank_row("Commercial permit fee", fee_url or portal)]
    # Drop a duplicate blank total when every stated row was rejected.
    stated = [row for row in fees if row.get("amount_usd") is not None]
    if not stated:
        fees = [_blank_row("Commercial permit fee", fee_url or portal)]
    card = dict(analysis.get("fee_card") or {})
    card["fees"] = fees[:12]
    card["timeline"] = "Unverified. This is not a filing date."
    card["disclaimer"] = (
        "A dollar on this card is a figure the cited schedule states. A blank line has no dollar."
        if stated
        else _BLANK
    )
    analysis["fee_card"] = card
    ahj = dict(analysis.get("ahj_card") or {})
    if fee_url:
        ahj["fees_url"] = fee_url
        if not str(ahj.get("portal_url") or "").startswith("https://") or _is_homepage(str(ahj.get("portal_url") or "")):
            ahj["portal_url"] = fee_url
    elif portal.startswith("https://") and not _is_homepage(portal):
        ahj["fees_url"] = portal
    if city and not ahj.get("name"):
        ahj["name"] = city
    if ahj:
        analysis["ahj_card"] = ahj
    # The pack keeps a stated dollar only when the local pack is citeable.
    analysis["coverage"] = {"tier": "full_pack"}
    analysis["gotcha_watchlist"] = {
        "items": [
            {
                "title": "Commercial permit total",
                "detail": _BLANK,
                "priority": "HIGH",
                "source_url": fee_url,
                "source_label": "Source",
            }
        ]
    }
    clocks = _clocks(pages)
    if clocks:
        analysis["parallel_clocks"] = {"clocks": clocks}
    return True
