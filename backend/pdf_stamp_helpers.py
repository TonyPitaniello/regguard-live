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


_GENERIC_ORIGINS = {
    "source",
    "link",
    "portal",
    "portal link",
    "verified",
    "confirm",
    "unverified",
    "official",
    "ahj source",
}


def named_origin(label: Optional[str], url: Optional[str], *, max_len: int = 42) -> str:
    """Buyer-facing origin. Never the bare word Source when a host exists."""
    face = (label or "").strip()
    if face.lower() in _GENERIC_ORIGINS:
        face = ""
    clean = _ascii_face(face) if face else ""
    # A long fee title cut mid-word is worse than the host the buyer can open.
    if clean and len(clean) <= max_len:
        return clean
    if url:
        return short_host(url, max_len=max_len)
    if clean:
        return clean[:max_len].rsplit(" ", 1)[0] or clean[:max_len]
    return "Unverified"


def buyer_url_label(url: str, *, max_len: int = 78) -> str:
    """Visible URL that wraps on slashes instead of splitting a word."""
    raw = (url or "").strip()
    if not raw:
        return ""
    if len(raw) <= max_len:
        return _ascii_face(raw)
    try:
        parsed = urlparse(raw)
        host = (parsed.netloc or "").replace("www.", "")
        tail = (parsed.path or "").rstrip("/").rsplit("/", 1)[-1]
    except Exception:
        host, tail = "", ""
    if host and tail:
        return _ascii_face(f"{host} / {tail}"[:max_len])
    return short_host(raw, max_len=max_len)


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

    origin = named_origin(label, url, max_len=24)
    if tier == "verified" and url:
        return (f"SOURCE: {origin}"[:36], url)
    if tier == "verified" and origin != "Unverified":
        return (f"SOURCE: {origin}"[:36], None)
    if url:
        return (f"PORTAL: {origin}"[:36], url)
    return "UNVERIFIED", None


def paint_linked_block(pdf: Any, text: str, url: Optional[str], *, width: float, line_h: float = 3.4) -> None:
    """Draw text and put the clickable area on that text, not the line below it."""
    y0 = pdf.get_y()
    x0 = pdf.get_x()
    pdf.multi_cell(width, line_h, text)
    y1 = pdf.get_y()
    if url and y1 > y0 + 0.5:
        try:
            pdf.link(x0, y0, width, y1 - y0, url)
        except Exception:
            pass


def _blurred_band_png(band: str) -> Optional[bytes]:
    """
    Rasterize the real contingency band, then shrink it so the digits stay
    visible as a blur. The percentage is not selectable text.
    """
    try:
        import fitz
    except Exception:
        return None
    try:
        src = fitz.open()
        page = src.new_page(width=640, height=90)
        page.draw_rect(page.rect, color=None, fill=(30 / 255, 41 / 255, 59 / 255))
        page.insert_text(
            (12, 58),
            band,
            fontsize=36,
            fontname="helv",
            color=(251 / 255, 191 / 255, 36 / 255),
        )
        pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
        factor = 16
        w, h = max(8, pix.width // factor), max(4, pix.height // factor)
        samples = pix.samples
        n = pix.n
        sw = pix.width
        out = bytearray(w * h * 3)
        for y in range(h):
            for x in range(w):
                rs = gs = bs = count = 0
                for yy in range(factor):
                    sy = y * factor + yy
                    if sy >= pix.height:
                        continue
                    for xx in range(factor):
                        sx = x * factor + xx
                        if sx >= sw:
                            continue
                        i = (sy * sw + sx) * n
                        rs += samples[i]
                        gs += samples[i + 1]
                        bs += samples[i + 2]
                        count += 1
                if not count:
                    continue
                o = (y * w + x) * 3
                out[o] = rs // count
                out[o + 1] = gs // count
                out[o + 2] = bs // count
        small = fitz.Pixmap(fitz.csRGB, w, h, bytes(out), False)
        return small.tobytes("png")
    except Exception:
        return None


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
    Free Lookups: a blurred image of the real contingency band.

    The percentage is not PDF text, so a viewer cannot select or read it,
    and the mid % is not printed underneath.
    """
    band = f"+{low_s}%  to  +{high_s}%"
    png = _blurred_band_png(band)
    if png:
        import io

        pdf.image(io.BytesIO(png), x=x, y=y, w=min(w, 118), h=14)
    else:
        pdf.set_xy(x, y)
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(*amber_soft)
        pdf.cell(w, 10, "Contingency blurred", ln=1)
    pdf.set_xy(x, y + 15)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*amber_soft)
    pdf.multi_cell(
        w,
        3.8,
        _ascii_face(
            "Blurred on Free - Estimator unlocks the clear contingency band you can forward."
        ),
    )
