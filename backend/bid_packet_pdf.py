"""
Forwardable Bid Packet PDF — branded to match the Reg Guard app.
Dark slate canvas, emerald contingency %, amber HIGH / Unverified badges.
Includes receipt hero + AHJ + fees + gotchas + docs + punch list.
ASCII-safe for Helvetica.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fpdf import FPDF

logger = logging.getLogger(__name__)

# App-matched palette
BG = (15, 23, 42)  # slate-950
CARD = (30, 41, 59)  # slate-800
CARD_EDGE = (51, 65, 85)  # slate-700
EMERALD = (16, 185, 129)  # emerald-500
EMERALD_SOFT = (52, 211, 153)  # emerald-400
AMBER = (245, 158, 11)
AMBER_SOFT = (251, 191, 36)
WHITE = (248, 250, 252)
MUTED = (148, 163, 184)
DIM = (100, 116, 139)
PURPLE = (129, 140, 248)

PAGE_W = 215.9  # Letter mm
PAGE_H = 279.4
MARGIN = 12
CONTENT_W = PAGE_W - (MARGIN * 2)


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


def _ensure_arbitrage(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """Guarantee contingency_band + margin_killers exist for the PDF."""
    need = (
        not analysis_data.get("contingency_band")
        or not analysis_data.get("margin_killers")
        or not analysis_data.get("fee_card")
        or not analysis_data.get("ahj_card")
    )
    if not need:
        band = analysis_data.get("contingency_band") or {}
        if band.get("pct_low") is None or band.get("pct_high") is None:
            need = True
    if need:
        from arbitrage_enrichment import enrich_analysis_with_arbitrage

        return enrich_analysis_with_arbitrage(dict(analysis_data))
    return analysis_data


class BidPacketPDF(FPDF):
    def __init__(self) -> None:
        super().__init__(format="Letter", unit="mm")
        self.set_auto_page_break(auto=True, margin=20)

    def header(self) -> None:
        # Paint full page background on every page
        self.set_fill_color(*BG)
        self.rect(0, 0, PAGE_W, PAGE_H, "F")

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*DIM)
        self.cell(
            0,
            5,
            _ascii(
                "Reg Guard Bid Packet  |  Planning aid only - confirm with AHJ  |  "
                f"Page {self.page_no()}"
            ),
            align="C",
        )


def _section_title(pdf: BidPacketPDF, title: str, y_pad: float = 2.0) -> None:
    pdf.ln(y_pad)
    pdf.set_x(MARGIN)
    pdf.set_fill_color(*EMERALD)
    pdf.rect(MARGIN, pdf.get_y() + 1.2, 2.2, 5.5, "F")
    pdf.set_x(MARGIN + 5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*WHITE)
    pdf.cell(CONTENT_W - 5, 8, _ascii(title), ln=1)


def _muted(pdf: BidPacketPDF, text: str, size: int = 8) -> None:
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "", size)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(CONTENT_W, 4.0, _ascii(text))


def _body(pdf: BidPacketPDF, text: str, size: int = 9, bold: bool = False) -> None:
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B" if bold else "", size)
    pdf.set_text_color(*WHITE)
    pdf.multi_cell(CONTENT_W, 4.4, _ascii(text))


def _badge(
    pdf: BidPacketPDF,
    label: str,
    *,
    fg: Tuple[int, int, int],
    bg: Tuple[int, int, int],
    x: float,
    y: float,
) -> float:
    """Draw a small badge; return width used."""
    pdf.set_font("Helvetica", "B", 7)
    w = pdf.get_string_width(_ascii(label)) + 4
    pdf.set_fill_color(*bg)
    pdf.set_text_color(*fg)
    pdf.set_xy(x, y)
    pdf.cell(w, 5, _ascii(label), fill=True, align="C")
    return w


def _card_box(pdf: BidPacketPDF, height: float) -> Tuple[float, float]:
    """Draw card background from current Y; return (x, y) content start."""
    x, y = MARGIN, pdf.get_y()
    pdf.set_fill_color(*CARD)
    pdf.set_draw_color(*CARD_EDGE)
    pdf.rect(x, y, CONTENT_W, height, "DF")
    return x + 4, y + 3.5


def generate_bid_packet_pdf(
    analysis_data: Dict[str, Any],
    output_path: Optional[str] = None,
) -> str:
    """Write branded bid packet PDF; return path."""
    try:
        from delivery_parity import prepare_analysis_for_delivery, citation_label_for_item

        analysis_data = prepare_analysis_for_delivery(analysis_data)
    except Exception:
        analysis_data = _ensure_arbitrage(analysis_data)
        citation_label_for_item = None  # type: ignore

    analysis_data = _ensure_arbitrage(analysis_data)

    try:
        from punch_rank import strip_md_bold
    except Exception:
        def strip_md_bold(t: str) -> str:  # type: ignore
            return t or ""

    pi = analysis_data.get("project_info") or {}
    address = _ascii(str(pi.get("address") or "Site"))
    city = _ascii(str(pi.get("city") or ""))
    state = _ascii(str(pi.get("state") or ""))
    zip_code = _ascii(str(pi.get("zip") or ""))
    ptype = _ascii(str(pi.get("type") or "commercial"))
    locality = ", ".join(p for p in (city, state) if p)
    if zip_code:
        locality = f"{locality} {zip_code}".strip()

    band = analysis_data.get("contingency_band") or {}
    ahj = analysis_data.get("ahj_card") or {}
    fee = analysis_data.get("fee_card") or {}
    killers: List[Dict[str, Any]] = [
        k for k in (analysis_data.get("margin_killers") or []) if isinstance(k, dict)
    ]
    gotchas = (analysis_data.get("gotcha_watchlist") or {}).get("items") or []
    docs = (analysis_data.get("document_checklist") or {}).get("items") or []
    punch = (analysis_data.get("punch_list") or {}).get("punch_list") or []
    dc = analysis_data.get("dc_positioning") or {}
    summary = analysis_data.get("summary") or {}
    honesty = analysis_data.get("honesty") or {}
    depth = str(
        analysis_data.get("research_depth")
        or honesty.get("depth")
        or honesty.get("source")
        or ""
    ).strip()
    coverage = str(
        (analysis_data.get("coverage") or {}).get("label")
        or honesty.get("coverage_label")
        or ""
    ).strip()

    low_s = _fmt_pct(band.get("pct_low"))
    mid_s = _fmt_pct(band.get("pct_mid"))
    high_s = _fmt_pct(band.get("pct_high"))

    pdf = BidPacketPDF()
    pdf.add_page()
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.set_y(MARGIN)

    # --- Brand bar ---
    pdf.set_fill_color(*EMERALD)
    pdf.rect(0, 0, PAGE_W, 3.2, "F")
    pdf.set_y(8)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*WHITE)
    pdf.cell(CONTENT_W * 0.55, 8, "REG GUARD", ln=0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*EMERALD_SOFT)
    pdf.cell(CONTENT_W * 0.45, 8, "BID PACKET", align="R", ln=1)
    _muted(
        pdf,
        "Forwardable pre-bid diligence  |  Site-specific CYA stamp  |  Not a quote, not a filing",
        8,
    )
    if depth or coverage:
        bits = [b for b in (depth.replace("_", " ").title(), coverage) if b]
        _muted(pdf, "  |  ".join(bits), 8)
    lp = analysis_data.get("local_pack") or {}
    if lp.get("tier"):
        _muted(
            pdf,
            f"Local pack: {lp.get('tier')}  |  "
            f"{'citeable' if lp.get('citeable') else 'planning aid — confirm with AHJ'}",
            8,
        )
    pdf.ln(1)

    # --- Site line ---
    pdf.set_fill_color(*CARD)
    pdf.set_draw_color(*EMERALD)
    y0 = pdf.get_y()
    pdf.rect(MARGIN, y0, CONTENT_W, 18, "DF")
    pdf.set_xy(MARGIN + 4, y0 + 3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*WHITE)
    pdf.cell(CONTENT_W - 8, 5, address[:90], ln=1)
    pdf.set_x(MARGIN + 4)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*MUTED)
    ahj_name = _ascii(str(ahj.get("name") or "Local AHJ (confirm locally)"))
    pdf.cell(
        CONTENT_W - 8,
        4,
        _ascii(f"{locality}  |  {ptype}  |  AHJ: {ahj_name}"),
        ln=1,
    )
    pdf.set_x(MARGIN + 4)
    pdf.set_text_color(*DIM)
    pdf.cell(
        CONTENT_W - 8,
        4,
        _ascii(f"Generated {datetime.utcnow().strftime('%Y-%m-%d')} UTC"),
        ln=1,
    )
    pdf.set_y(y0 + 20)

    # --- BIG CONTINGENCY (hero) ---
    _section_title(pdf, "Contingency band (screenshot this)")
    hero_h = 28 if low_s and high_s else 18
    cx, cy = _card_box(pdf, hero_h)
    pdf.set_xy(cx, cy)
    if low_s and high_s:
        pdf.set_font("Helvetica", "B", 28)
        pdf.set_text_color(*EMERALD_SOFT)
        pdf.cell(CONTENT_W - 8, 12, f"+{low_s}%  -  +{high_s}%", ln=1)
        pdf.set_x(cx)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*EMERALD)
        mid_line = f"mid {mid_s}%  -  planning aid - not a quote"
        pdf.cell(CONTENT_W - 8, 5, _ascii(mid_line), ln=1)
        usd_bits = []
        if isinstance(band.get("usd_low"), (int, float)) and isinstance(
            band.get("usd_high"), (int, float)
        ):
            usd_bits.append(
                f"~${int(band['usd_low']):,} - ${int(band['usd_high']):,} on current rollup"
            )
        if band.get("disclaimer"):
            usd_bits.append(str(band.get("disclaimer"))[:120])
        if usd_bits:
            pdf.set_x(cx)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*MUTED)
            pdf.multi_cell(CONTENT_W - 8, 3.5, _ascii("  |  ".join(usd_bits)))
    else:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*AMBER_SOFT)
        pdf.multi_cell(
            CONTENT_W - 8,
            5,
            _ascii("Set contingency after confirming Critical/High items with AHJ."),
        )
    pdf.set_y(cy + hero_h + 2)

    # --- Top 3 risk flags ---
    _section_title(pdf, "Top 3 risk flags")
    if not killers:
        _muted(pdf, "No high-confidence killers extracted - confirm Critical/High with AHJ.")
    for i, k in enumerate(killers[:5], 1):
        if pdf.get_y() > 240:
            pdf.add_page()
            pdf.set_y(MARGIN + 4)
        pri = str(k.get("priority") or "NOTE").upper()
        if citation_label_for_item:
            ver = citation_label_for_item(k)
        else:
            ver = "SOURCE" if k.get("verified") and k.get("source_url") else "UNVERIFIED"
        title = _ascii(strip_md_bold(str(k.get("title") or "Item")))[:88]
        detail = _ascii(strip_md_bold(str(k.get("detail") or "")))[:140]

        box_h = 18 + (4 if detail else 0)
        pe = k.get("planning_exposure") or {}
        if isinstance(pe, dict) and pe.get("usd_mid") is not None:
            box_h += 4
        bx, by = _card_box(pdf, box_h)

        # Number + priority badge
        pdf.set_xy(bx, by)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*WHITE)
        pdf.cell(8, 5, f"{i}.", ln=0)
        badge_x = bx + 8
        if pri in ("CRITICAL", "HIGH"):
            badge_x += _badge(
                pdf, pri, fg=BG, bg=AMBER if pri == "HIGH" else (239, 68, 68), x=badge_x, y=by
            )
        else:
            badge_x += _badge(pdf, pri, fg=WHITE, bg=CARD_EDGE, x=badge_x, y=by)
        badge_x += 2
        if ver == "UNVERIFIED":
            _badge(pdf, ver, fg=BG, bg=AMBER_SOFT, x=badge_x, y=by)
        elif ver == "LINK":
            _badge(pdf, ver, fg=WHITE, bg=PURPLE, x=badge_x, y=by)
        else:
            _badge(pdf, ver, fg=BG, bg=EMERALD, x=badge_x, y=by)

        pdf.set_xy(bx, by + 6)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*WHITE)
        pdf.multi_cell(CONTENT_W - 12, 4, title)
        if detail:
            pdf.set_x(bx)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*MUTED)
            pdf.multi_cell(CONTENT_W - 12, 3.5, detail)
        if isinstance(pe, dict) and pe.get("usd_mid") is not None:
            pdf.set_x(bx)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*EMERALD_SOFT)
            pdf.multi_cell(
                CONTENT_W - 12,
                3.5,
                _ascii(
                    f"Planning exposure - ${int(pe.get('usd_low') or 0):,}"
                    f"-${int(pe.get('usd_high') or 0):,} - not guaranteed savings"
                ),
            )
        pdf.set_y(by + box_h + 2)

    if dc.get("headline"):
        pdf.ln(1)
        _muted(
            pdf,
            "Note: AHJ + utility often run on parallel clocks (not an interconnect study).",
            8,
        )

    # --- AHJ ---
    if pdf.get_y() > 220:
        pdf.add_page()
        pdf.set_y(MARGIN + 4)
    _section_title(pdf, "AHJ portal & contact")
    portal = str(ahj.get("portal_url") or "Confirm locally").strip()
    fees_url = str(ahj.get("fees_url") or "Confirm locally").strip()
    phone = str(ahj.get("phone") or "").strip()
    notes = str(ahj.get("notes") or "").strip()
    ahj_lines = [
        f"{ahj.get('name') or 'Local AHJ'}",
        f"Portal: {portal}",
        f"Fees schedule: {fees_url}",
    ]
    if phone:
        ahj_lines.append(f"Phone: {phone}")
    if notes:
        ahj_lines.append(notes[:160])
    _body(pdf, "\n".join(ahj_lines), 9)

    # --- Fees ---
    _section_title(pdf, "Fee & timeline extract")
    timeline = str(fee.get("timeline") or summary.get("estimated_timeline") or "Confirm with AHJ")
    _body(pdf, f"Timeline: {timeline}", 9, bold=True)
    fees = fee.get("fees") or []
    if not fees:
        _muted(pdf, "No fee rows extracted - confirm on AHJ fee schedule (Unverified).")
    for row in fees[:10]:
        if pdf.get_y() > 255:
            pdf.add_page()
            pdf.set_y(MARGIN + 4)
        amt = row.get("amount_usd")
        amt_s = f"${amt:,.0f}" if isinstance(amt, (int, float)) else "TBD"
        ver = "Source" if row.get("verified") else "Unverified"
        label = str(row.get("label") or "Fee")[:70]
        detail = str(row.get("detail") or "")[:70]
        color = EMERALD if ver == "Source" else AMBER_SOFT
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*color)
        pdf.cell(22, 4.2, f"[{ver}]", ln=0)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*WHITE)
        pdf.multi_cell(CONTENT_W - 22, 4.2, _ascii(f"{label}: {amt_s} - {detail}"))

    # --- Gotchas ---
    if pdf.get_y() > 230:
        pdf.add_page()
        pdf.set_y(MARGIN + 4)
    _section_title(pdf, "Local gotcha watchlist")
    if not gotchas:
        _muted(pdf, "No curated gotchas - verify with AHJ (Unverified).")
    for g in gotchas[:10]:
        if pdf.get_y() > 255:
            pdf.add_page()
            pdf.set_y(MARGIN + 4)
        pri = str(g.get("priority") or "NOTE").upper()
        title = str(g.get("title") or "")[:70]
        detail = str(g.get("detail") or "")[:100]
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*AMBER if pri in ("HIGH", "CRITICAL") else MUTED)
        pdf.cell(18, 4.2, f"[{pri}]", ln=0)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*WHITE)
        pdf.multi_cell(CONTENT_W - 18, 4.2, _ascii(f"{title}: {detail}"))

    # --- Docs ---
    if pdf.get_y() > 230:
        pdf.add_page()
        pdf.set_y(MARGIN + 4)
    _section_title(pdf, "Document / submittal checklist")
    if not docs:
        _muted(pdf, "Confirm exact submittal list with AHJ for this permit type.")
    for d in docs[:15]:
        if pdf.get_y() > 255:
            pdf.add_page()
            pdf.set_y(MARGIN + 4)
        task = d.get("task") if isinstance(d, dict) else str(d)
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*EMERALD_SOFT)
        pdf.cell(6, 4.5, "[ ]", ln=0)
        pdf.set_text_color(*WHITE)
        pdf.multi_cell(CONTENT_W - 6, 4.5, _ascii(str(task)[:110]))

    # --- Punch list ---
    if pdf.get_y() > 220:
        pdf.add_page()
        pdf.set_y(MARGIN + 4)
    _section_title(pdf, "Punch list (Critical -> Low)")
    _muted(
        pdf,
        "Ranked to match the app. SOURCE = parcel-backed; LINK = portal URL; UNVERIFIED = confirm with AHJ.",
    )
    if not punch:
        _muted(pdf, "No punch lines in this run.")
    for i, item in enumerate(punch[:40], 1):
        if pdf.get_y() > 255:
            pdf.add_page()
            pdf.set_y(MARGIN + 4)
        if not isinstance(item, dict):
            continue
        task = strip_md_bold(str(item.get("task") or ""))[:110]
        pri = str(item.get("priority") or "").upper()
        if citation_label_for_item:
            ver = citation_label_for_item(item)
        else:
            ver = "Source" if item.get("verified") and item.get("source_url") else "Unverified"
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(
            *(239, 68, 68)
            if pri == "CRITICAL"
            else AMBER
            if pri == "HIGH"
            else MUTED
        )
        pdf.cell(10, 4.2, f"{i}.", ln=0)
        pdf.set_text_color(
            *AMBER_SOFT if ver.upper() == "UNVERIFIED" else PURPLE if ver.upper() == "LINK" else EMERALD
        )
        pdf.cell(36, 4.2, f"[{pri}] [{ver}]", ln=0)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*WHITE)
        pdf.multi_cell(CONTENT_W - 46, 4.2, _ascii(task))

    # --- Closing CYA ---
    pdf.ln(4)
    pdf.set_fill_color(*CARD)
    pdf.set_draw_color(*EMERALD)
    y = pdf.get_y()
    if y > 250:
        pdf.add_page()
        pdf.set_y(MARGIN + 4)
        y = pdf.get_y()
    pdf.rect(MARGIN, y, CONTENT_W, 16, "DF")
    pdf.set_xy(MARGIN + 4, y + 3)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*EMERALD_SOFT)
    pdf.cell(CONTENT_W - 8, 4, "PLANNING AID ONLY", ln=1)
    pdf.set_x(MARGIN + 4)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(
        CONTENT_W - 8,
        3.5,
        _ascii(
            "Not a quote, not guaranteed savings, not an official AHJ filing. "
            "Confirm fees, forms, and timeline with the AHJ before bid. "
            "app.regguardagent.com"
        ),
    )

    if not output_path:
        out_dir = Path(os.getenv("REGGUARD_DATA_DIR") or "/tmp/regguard_data") / "bid_packets"
        out_dir.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() else "_" for c in address)[:40]
        output_path = str(
            out_dir / f"bid_packet_{safe}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        )

    pdf.output(output_path)
    logger.info("Bid packet PDF (branded) -> %s", output_path)
    return output_path
