"""
Bid Risk Receipt — forward-first one-pager, branded to match the Reg Guard app.
Dark slate canvas, big emerald contingency %, amber HIGH / Unverified badges.
ASCII-only for Helvetica compatibility.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fpdf import FPDF

from arbitrage_enrichment import build_margin_killers, enrich_analysis_with_arbitrage

logger = logging.getLogger(__name__)

APP_URL = os.getenv("FRONTEND_APP_URL", "https://app.regguardagent.com").rstrip("/")

BG = (15, 23, 42)
CARD = (30, 41, 59)
CARD_EDGE = (51, 65, 85)
EMERALD = (16, 185, 129)
EMERALD_SOFT = (52, 211, 153)
AMBER = (245, 158, 11)
AMBER_SOFT = (251, 191, 36)
WHITE = (248, 250, 252)
MUTED = (148, 163, 184)
DIM = (100, 116, 139)

PAGE_W = 215.9
PAGE_H = 279.4
MARGIN = 12
CONTENT_W = PAGE_W - (MARGIN * 2)

CYA = (
    "PLANNING AID ONLY - not a quote, not guaranteed savings, "
    "not an official AHJ filing. Confirm with AHJ before bid."
)


def _ascii(text: str) -> str:
    return (
        (text or "")
        .replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2022", "-")
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


def _fmt_pct(v: Any) -> Optional[str]:
    if v is None:
        return None
    try:
        return f"{float(v):.1f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return None


def _badge(
    pdf: FPDF,
    label: str,
    *,
    fg: Tuple[int, int, int],
    bg: Tuple[int, int, int],
    x: float,
    y: float,
) -> float:
    pdf.set_font("Helvetica", "B", 7)
    w = pdf.get_string_width(_ascii(label)) + 4
    pdf.set_fill_color(*bg)
    pdf.set_text_color(*fg)
    pdf.set_xy(x, y)
    pdf.cell(w, 5, _ascii(label), fill=True, align="C")
    return w


class BidRiskReceiptPDF(FPDF):
    def __init__(self) -> None:
        super().__init__(format="Letter", unit="mm")
        self.set_auto_page_break(auto=False)

    def header(self) -> None:
        self.set_fill_color(*BG)
        self.rect(0, 0, PAGE_W, PAGE_H, "F")

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*DIM)
        self.multi_cell(0, 3.5, _ascii(CYA), align="C")


def generate_bid_risk_receipt_pdf(
    analysis_data: Dict[str, Any],
    output_path: Optional[str] = None,
    *,
    generated_for: Optional[str] = None,
    share_url: Optional[str] = None,
) -> str:
    """Write a branded 1-page forwardable Bid Risk Receipt; return path."""
    data = dict(analysis_data or {})
    band = data.get("contingency_band") or {}
    if (
        not band
        or band.get("pct_low") is None
        or band.get("pct_high") is None
        or not data.get("margin_killers")
        or not data.get("ahj_card")
    ):
        data = enrich_analysis_with_arbitrage(data)

    pi = data.get("project_info") or {}
    address = _ascii(str(pi.get("address") or "Site"))
    city = _ascii(str(pi.get("city") or ""))
    state = _ascii(str(pi.get("state") or ""))
    zip_code = _ascii(str(pi.get("zip") or ""))
    who = _ascii((generated_for or "").strip() or "Estimator")
    cta = _ascii((share_url or f"{APP_URL}/?utm_source=bid_receipt").strip())

    killers = data.get("margin_killers")
    if not isinstance(killers, list) or not killers:
        killers = build_margin_killers(data, limit=3)

    band = data.get("contingency_band") or {}
    ahj = data.get("ahj_card") or {}
    dc = data.get("dc_positioning") or {}

    low_s = _fmt_pct(band.get("pct_low"))
    mid_s = _fmt_pct(band.get("pct_mid"))
    high_s = _fmt_pct(band.get("pct_high"))

    pdf = BidRiskReceiptPDF()
    pdf.add_page()
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.set_y(8)

    # Brand bar
    pdf.set_fill_color(*EMERALD)
    pdf.rect(0, 0, PAGE_W, 3.2, "F")

    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*EMERALD_SOFT)
    pdf.cell(CONTENT_W, 6, "FLAGGED BEFORE BID DAY", ln=1)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*WHITE)
    pdf.multi_cell(
        CONTENT_W,
        4,
        _ascii("I flagged risk on THIS site. Forward so the GC/owner sees it before bid."),
    )
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*MUTED)
    pdf.cell(CONTENT_W, 4, "REG GUARD  |  Bid Risk Receipt", ln=1)
    pdf.ln(2)

    # Site card
    y0 = pdf.get_y()
    pdf.set_fill_color(*CARD)
    pdf.set_draw_color(*EMERALD)
    pdf.rect(MARGIN, y0, CONTENT_W, 22, "DF")
    pdf.set_xy(MARGIN + 4, y0 + 2.5)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*EMERALD)
    pdf.cell(CONTENT_W - 8, 4, "THIS SITE", ln=1)
    pdf.set_x(MARGIN + 4)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*WHITE)
    pdf.cell(CONTENT_W - 8, 6, address[:88], ln=1)
    pdf.set_x(MARGIN + 4)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(CONTENT_W - 8, 4, f"{city}, {state} {zip_code}".strip(), ln=1)
    pdf.set_x(MARGIN + 4)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*WHITE)
    pdf.cell(
        CONTENT_W - 8,
        4,
        _ascii(f"AHJ: {str(ahj.get('name') or 'Local AHJ')}"),
        ln=1,
    )
    identity = data.get("ahj_identity") or {}
    if identity.get("conflict") and identity.get("note"):
        pdf.set_x(MARGIN + 4)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*AMBER)
        pdf.multi_cell(CONTENT_W - 8, 3.2, _ascii(str(identity.get("note"))[:160]))
    pdf.set_y(y0 + 24)

    portal = str(ahj.get("portal_url") or "").strip()
    if portal:
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*DIM)
        pdf.cell(CONTENT_W, 3.5, _ascii(f"Portal: {portal}"), ln=1)
    if dc.get("headline"):
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*DIM)
        pdf.multi_cell(
            CONTENT_W,
            3.5,
            _ascii(
                "Note: AHJ + utility often run on parallel clocks (not an interconnect study)."
            ),
        )
    pdf.ln(2)

    # BIG contingency
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*EMERALD)
    pdf.cell(CONTENT_W, 5, "CONTINGENCY (screenshot this)", ln=1)

    y1 = pdf.get_y()
    pdf.set_fill_color(*CARD)
    pdf.set_draw_color(*EMERALD)
    pdf.rect(MARGIN, y1, CONTENT_W, 24, "DF")
    pdf.set_xy(MARGIN + 4, y1 + 3)
    if low_s and high_s:
        pdf.set_font("Helvetica", "B", 26)
        pdf.set_text_color(*EMERALD_SOFT)
        pdf.cell(CONTENT_W - 8, 11, f"+{low_s}%  to  +{high_s}%", ln=1)
        pdf.set_x(MARGIN + 4)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*EMERALD)
        pdf.cell(
            CONTENT_W - 8,
            5,
            _ascii(f"mid {mid_s}%   |   planning aid - NOT a quote"),
            ln=1,
        )
    else:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*AMBER_SOFT)
        pdf.multi_cell(
            CONTENT_W - 8,
            5,
            _ascii("Set contingency after confirming Critical/High items with AHJ."),
        )
    pdf.set_y(y1 + 26)

    # Top 3 killers
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*EMERALD)
    pdf.cell(CONTENT_W, 5, "TOP 3 RISK FLAGS  (Source or Unverified)", ln=1)

    for i, k in enumerate(list(killers)[:3], 1):
        if not isinstance(k, dict):
            continue
        ver = "SOURCE" if k.get("verified") and k.get("source_url") else "UNVERIFIED"
        pri = str(k.get("priority") or "NOTE").upper()
        title = _ascii(str(k.get("title") or "Item"))[:90]
        detail = _ascii(str(k.get("detail") or ""))[:110]
        pe = k.get("planning_exposure") or {}

        box_h = 16 + (3.5 if detail else 0)
        if isinstance(pe, dict) and pe.get("usd_mid") is not None:
            box_h += 3.5
        y = pdf.get_y()
        if y + box_h > 250:
            break
        pdf.set_fill_color(*CARD)
        pdf.set_draw_color(*CARD_EDGE)
        pdf.rect(MARGIN, y, CONTENT_W, box_h, "DF")
        bx, by = MARGIN + 4, y + 2.5

        pdf.set_xy(bx, by)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*WHITE)
        pdf.cell(8, 5, f"{i}.", ln=0)
        bx2 = bx + 8
        if pri in ("CRITICAL", "HIGH"):
            bx2 += _badge(
                pdf,
                pri,
                fg=BG,
                bg=AMBER if pri == "HIGH" else (239, 68, 68),
                x=bx2,
                y=by,
            )
        else:
            bx2 += _badge(pdf, pri, fg=WHITE, bg=CARD_EDGE, x=bx2, y=by)
        bx2 += 2
        if ver == "UNVERIFIED":
            _badge(pdf, ver, fg=BG, bg=AMBER_SOFT, x=bx2, y=by)
        else:
            _badge(pdf, ver, fg=BG, bg=EMERALD, x=bx2, y=by)

        pdf.set_xy(bx, by + 5.5)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*WHITE)
        pdf.multi_cell(CONTENT_W - 12, 4, title)
        if detail:
            pdf.set_x(bx)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*MUTED)
            pdf.multi_cell(CONTENT_W - 12, 3.2, detail)
        if isinstance(pe, dict) and pe.get("usd_mid") is not None:
            pdf.set_x(bx)
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_text_color(*EMERALD_SOFT)
            pdf.multi_cell(
                CONTENT_W - 12,
                3.2,
                _ascii(
                    f"Planning exposure - ${int(pe.get('usd_low') or 0):,}"
                    f"-${int(pe.get('usd_high') or 0):,} - not guaranteed savings"
                ),
            )
        pdf.set_y(y + box_h + 2)

    # Stamp
    pdf.ln(1)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*EMERALD)
    pdf.cell(CONTENT_W, 5, "STAMP", ln=1)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*WHITE)
    stamp_date = datetime.utcnow().strftime("%Y-%m-%d")
    pdf.multi_cell(
        CONTENT_W,
        4,
        _ascii(
            f"Flagged by: {who}\n"
            f"Date: {stamp_date} UTC\n"
            "Re-check before bid - fees and portal asks move."
        ),
    )
    pdf.ln(1)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*DIM)
    pdf.multi_cell(CONTENT_W, 3.5, _ascii(f"Recipient: run your own address if needed - {cta}"))

    if not output_path:
        out_dir = Path(os.getenv("REGGUARD_DATA_DIR") or "/tmp/regguard_data") / "bid_receipts"
        out_dir.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() else "_" for c in address)[:40]
        output_path = str(
            out_dir / f"bid_receipt_{safe}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        )

    pdf.output(output_path)
    logger.info("Bid Risk Receipt PDF (branded) -> %s", output_path)
    return output_path
