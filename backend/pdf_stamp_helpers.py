"""
Shared PDF stamp + citation helpers for Bid Risk Receipt, Bid Packet, City Pack.

Buyer-facing rule (counsel / GC):
  Internal grade FAIL → display HOLD (not a rejection)
  Internal grade PASS → display CLEAR
Never print orphan LINK badges — either a clickable portal with a host label, or UNVERIFIED.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse


def stamp_display_grade(grade: Any) -> str:
    g = str(grade or "").strip().upper()
    return {
        "FAIL": "HOLD",
        "PASS": "CLEAR",
        "HOLD": "HOLD",
        "CLEAR": "CLEAR",
        "CAUTION": "CAUTION",
    }.get(g, g or "—")


def stamp_plain_text(rg: Dict[str, Any] | None, *, grade: Any = None) -> str:
    """Buyer-facing stamp body — never leave the word FAIL in the PDF."""
    rg = rg if isinstance(rg, dict) else {}
    display = stamp_display_grade(grade if grade is not None else rg.get("grade"))
    raw = str(rg.get("plain") or rg.get("headline") or rg.get("label") or "").strip()
    raw = raw.replace("FAIL", "HOLD").replace("Fail", "Hold")
    if not raw:
        if display == "HOLD":
            return (
                "High pre-bid risk on this site. This is not a rejection of the job - "
                "it means resolve the drivers below before treating the bid as clear."
            )
        if display == "CLEAR":
            return "No Critical/High drivers elevated on this run — still confirm fees with the AHJ."
        if display == "CAUTION":
            return "Review drivers below before treating the bid as clear."
    return raw


def _ascii_face(text: str) -> str:
    return (
        (text or "")
        .replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2019", "'")
        .replace("\u00b7", "-")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


def short_host(url: str, *, max_len: int = 36) -> str:
    try:
        host = (urlparse(url).netloc or "").replace("www.", "")
    except Exception:
        host = ""
    if not host:
        return "official portal"
    return _ascii_face(host[:max_len])


def citation_badge_and_url(item: Dict[str, Any] | None) -> Tuple[str, Optional[str]]:
    """
    Return (badge_text, url_or_none).

    - SOURCE + label when parcel/scout verified
    - PORTAL + host when only a confirm URL exists (never a dead 'LINK' chip)
    - UNVERIFIED when nothing citeable
    """
    if not isinstance(item, dict):
        return "UNVERIFIED", None
    url = str(
        item.get("source_url")
        or item.get("citation_url")
        or item.get("portal_url")
        or item.get("fees_url")
        or ""
    ).strip()
    label = str(
        item.get("source_label")
        or item.get("citation_note")
        or item.get("citation_label")
        or ""
    ).strip()
    verified = item.get("verified") is True or str(item.get("citation_tier") or "").lower() in (
        "verified",
        "source",
    )

    # Prefer shared honesty tier when present
    try:
        from citation_honesty import citation_tier_for

        tier = citation_tier_for(item)
    except Exception:
        if verified and url:
            tier = "verified"
        elif url:
            tier = "link"
        else:
            tier = "unverified"

    if tier == "verified" and url:
        face = _ascii_face(label or short_host(url))
        return (f"SOURCE: {face}"[:28], url)
    if tier == "verified" and label:
        return (f"SOURCE: {_ascii_face(label)}"[:28], None)
    if url:
        face = _ascii_face(label or short_host(url))
        return (f"PORTAL: {face}"[:28], url)
    return "UNVERIFIED", None


def draw_frosted_contingency(
    pdf: Any,
    *,
    x: float,
    y: float,
    w: float,
    h: float,
    low_s: str,
    high_s: str,
    mid_s: str | None,
    card_rgb: Tuple[int, int, int],
    amber_soft: Tuple[int, int, int],
    muted: Tuple[int, int, int],
) -> None:
    """
    Free Lookups: real contingency % as a frosted silhouette (not +##% placeholders).

    fpdf opacity is unreliable across viewers, so we draw a near-card ghost of the
    real band, then opaque frost bars that leave only a blurred amber silhouette.
    """
    band = f"+{low_s}%  to  +{high_s}%"
    # Ghost underlay — real band, barely lifted off the card so shape remains
    ghost = tuple(min(255, int(c) + 28) for c in card_rgb)
    pdf.set_xy(x, y)
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(*ghost)
    pdf.cell(w, 11, band, ln=1)

    # Opaque frost wash (no opacity API) — keeps the silhouette but blocks reading
    frost = tuple(min(255, int(c) + 8) for c in card_rgb)
    pdf.set_fill_color(*frost)
    pdf.rect(x - 1, y - 0.3, w + 2, 11.2, "F")

    # Amber hash stripes — reads as "blurred %" not empty or ##
    pdf.set_fill_color(*amber_soft)
    stripe_y = y + 1.2
    while stripe_y < y + 10.2:
        # Alternating short/long bars suggest digit shapes under frost
        pdf.rect(x + 2, stripe_y, w * 0.42, 1.0, "F")
        pdf.rect(x + w * 0.48, stripe_y + 0.35, w * 0.46, 0.85, "F")
        stripe_y += 2.2

    # Soft edge vignette so it doesn't look like a solid block
    pdf.set_fill_color(*card_rgb)
    pdf.rect(x - 1, y - 0.3, 3.5, 11.2, "F")
    pdf.rect(x + w - 2.5, y - 0.3, 4.5, 11.2, "F")

    pdf.set_xy(x, y + 11.5)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*amber_soft)
    mid_bit = f"mid ~{mid_s}% - " if mid_s else ""
    msg = (
        f"{mid_bit}Blurred on Free - Estimator unlocks the clear contingency band you can forward."
    )
    msg = _ascii_face(msg)
    pdf.multi_cell(w, 3.8, msg)
