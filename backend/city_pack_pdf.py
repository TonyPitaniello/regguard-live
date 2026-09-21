"""Full city pack PDF — AHJ, fees, gotchas, inspections. Same dark canvas as Bid Packet."""
from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from bid_packet_pdf import (
    AMBER,
    AMBER_SOFT,
    CARD,
    CARD_EDGE,
    CONTENT_W,
    EMERALD,
    EMERALD_SOFT,
    MARGIN,
    MUTED,
    PAGE_W,
    WHITE,
    BidPacketPDF,
    _ascii,
    _body,
    _card_box,
    _ensure_arbitrage,
    _fmt_pct,
    _muted,
    _section_title,
)

logger = logging.getLogger(__name__)


def _fee_rows(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    card = analysis.get("fee_card") if isinstance(analysis.get("fee_card"), dict) else {}
    rows = card.get("fees") or []
    if isinstance(rows, list) and rows:
        return [r for r in rows if isinstance(r, dict)]
    local = analysis.get("local_pack") if isinstance(analysis.get("local_pack"), dict) else {}
    raw = local.get("fees") or []
    out = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        out.append(
            {
                "label": r.get("label") or r.get("name") or "Fee line",
                "detail": r.get("detail") or "",
                "amount_usd": r.get("amount_usd"),
                "verified": r.get("verified"),
                "source_url": r.get("source_url") or r.get("citation_url"),
                "source_label": r.get("source_label") or r.get("citation_note"),
                "trade": r.get("trade"),
            }
        )
    return out


def _gotcha_rows(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    watch = analysis.get("gotcha_watchlist") if isinstance(analysis.get("gotcha_watchlist"), dict) else {}
    items = watch.get("items") or []
    if isinstance(items, list) and items:
        return [g for g in items if isinstance(g, dict)]
    local = analysis.get("local_pack") if isinstance(analysis.get("local_pack"), dict) else {}
    raw = local.get("gotchas") or local.get("items") or []
    return [g for g in raw if isinstance(g, dict)]


def generate_city_pack_pdf(analysis_data: Dict[str, Any], output_path: str | None = None) -> str:
    try:
        from delivery_parity import prepare_analysis_for_delivery

        analysis_data = prepare_analysis_for_delivery(analysis_data)
    except Exception:
        analysis_data = _ensure_arbitrage(analysis_data)

    pi = analysis_data.get("project_info") or {}
    address = _ascii(str(pi.get("address") or "Site"))
    city = _ascii(str(pi.get("city") or ""))
    state = _ascii(str(pi.get("state") or ""))
    zip_code = _ascii(str(pi.get("zip") or ""))
    locality = ", ".join(p for p in (city, state) if p)
    if zip_code:
        locality = f"{locality} {zip_code}".strip()

    band = analysis_data.get("contingency_band") or {}
    ahj = analysis_data.get("ahj_card") or {}
    fee = analysis_data.get("fee_card") or {}
    coverage = analysis_data.get("coverage") or {}
    local_pack = analysis_data.get("local_pack") or {}
    insp = analysis_data.get("inspection_sequence_card") or {}

    low_s = _fmt_pct(band.get("pct_low"))
    mid_s = _fmt_pct(band.get("pct_mid"))
    high_s = _fmt_pct(band.get("pct_high"))

    from artifact_naming import document_display_title, site_line_from_analysis

    site_line = site_line_from_analysis(analysis_data)
    doc_title = document_display_title(site_line, "FULL CITY PACK")

    pdf = BidPacketPDF()
    pdf._footer_label = _ascii(doc_title)[:90]
    try:
        pdf.set_title(_ascii(doc_title)[:120])
        pdf.set_author("Reg Guard")
    except Exception:
        pass
    pdf.add_page()
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.set_y(MARGIN)

    pdf.set_fill_color(*EMERALD)
    pdf.rect(0, 0, PAGE_W, 3.2, "F")
    pdf.set_y(8)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*WHITE)
    pdf.cell(CONTENT_W, 8, "REG GUARD", ln=1)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*EMERALD_SOFT)
    pdf.multi_cell(CONTENT_W, 4, _ascii(doc_title))
    _muted(
        pdf,
        "Curated local pack  |  Fees, gotchas, AHJ, inspections  |  Planning aid - not a quote",
        8,
    )
    cov_bits = [
        str(coverage.get("badge") or coverage.get("label") or "").strip(),
        str(local_pack.get("tier") or "").replace("_", " ").strip(),
    ]
    cov_line = "  |  ".join(b for b in cov_bits if b)
    if cov_line:
        _muted(pdf, cov_line, 8)

    y0 = pdf.get_y() + 1.5
    pdf.set_fill_color(*CARD)
    pdf.set_draw_color(*EMERALD)
    pdf.rect(MARGIN, y0, CONTENT_W, 18, "DF")
    pdf.set_xy(MARGIN + 4, y0 + 3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*WHITE)
    pdf.cell(CONTENT_W - 8, 5, address[:90], ln=1)
    pdf.set_x(MARGIN + 4)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*MUTED)
    ahj_name = _ascii(str(ahj.get("name") or "Local AHJ (confirm locally)"))
    pdf.cell(CONTENT_W - 8, 4, _ascii(f"{locality}  |  AHJ: {ahj_name}"), ln=1)
    pdf.set_x(MARGIN + 4)
    pdf.set_text_color(*MUTED)
    pdf.cell(
        CONTENT_W - 8,
        4,
        _ascii(f"Generated {datetime.utcnow().strftime('%Y-%m-%d')} UTC"),
        ln=1,
    )
    pdf.set_y(y0 + 20)

    _section_title(pdf, "Contingency band (planning aid)")
    hero_h = 24 if low_s and high_s else 14
    cx, cy = _card_box(pdf, hero_h)
    pdf.set_xy(cx, cy)
    if low_s and high_s:
        pdf.set_font("Helvetica", "B", 22)
        pdf.set_text_color(*EMERALD_SOFT)
        pdf.cell(CONTENT_W - 8, 10, f"+{low_s}%  -  +{high_s}%", ln=1)
        pdf.set_x(cx)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*EMERALD)
        pdf.cell(CONTENT_W - 8, 5, _ascii(f"mid {mid_s}%  -  planning aid - not a quote"), ln=1)
        if band.get("disclaimer"):
            pdf.set_x(cx)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*MUTED)
            pdf.multi_cell(CONTENT_W - 8, 3.5, _ascii(str(band.get("disclaimer"))[:220]))
    else:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*AMBER_SOFT)
        pdf.multi_cell(CONTENT_W - 8, 5, _ascii("Confirm contingency with the AHJ before bid."))
    pdf.set_y(cy + hero_h + 2)

    _section_title(pdf, "AHJ portal & contact")
    _body(pdf, ahj_name, 10, bold=True)
    if ahj.get("portal_url"):
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*EMERALD)
        pdf.multi_cell(CONTENT_W, 4.0, _ascii(f"Portal: {ahj.get('portal_url')}"))
    if ahj.get("fees_url"):
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*EMERALD)
        pdf.multi_cell(CONTENT_W, 4.0, _ascii(f"Fees: {ahj.get('fees_url')}"))
    if ahj.get("phone"):
        _muted(pdf, f"Phone: {ahj.get('phone')}", 8)
    if ahj.get("notes"):
        _muted(pdf, str(ahj.get("notes"))[:240], 8)
    if ahj.get("last_verified"):
        _muted(pdf, f"Last verified: {ahj.get('last_verified')}", 8)

    fees = _fee_rows(analysis_data)
    _section_title(pdf, "Fee & timeline extract")
    timeline = str(fee.get("timeline") or (analysis_data.get("summary") or {}).get("estimated_timeline") or "Confirm with AHJ")
    _body(pdf, f"Timeline: {timeline}", 9, bold=True)
    if not fees:
        _muted(pdf, "No fee rows in this pack - confirm on the official AHJ fee schedule.")
    for row in fees[:16]:
        if pdf.get_y() > 255:
            pdf.add_page()
            pdf.set_y(MARGIN + 4)
        amt = row.get("amount_usd")
        amt_s = f"${amt:,.0f}" if isinstance(amt, (int, float)) else "confirm on schedule"
        ver = "Source" if row.get("verified") or row.get("source_url") else "Unverified"
        label = str(row.get("label") or "Fee")[:80]
        trade = str(row.get("trade") or "").strip()
        prefix = f"[{trade}] " if trade else ""
        color = EMERALD if ver == "Source" else AMBER_SOFT
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*color)
        pdf.cell(24, 4.2, f"[{ver}]", ln=0)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*WHITE)
        pdf.multi_cell(CONTENT_W - 24, 4.2, _ascii(f"{prefix}{label}: {amt_s}"))
        url = str(row.get("source_url") or "").strip()
        if url:
            pdf.set_x(MARGIN + 24)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*EMERALD)
            pdf.multi_cell(CONTENT_W - 24, 3.5, _ascii(url))

    gotchas = _gotcha_rows(analysis_data)
    _section_title(pdf, "Local gotcha watchlist")
    if not gotchas:
        _muted(pdf, "No curated gotchas in this pack - verify with AHJ.")
    for g in gotchas[:12]:
        if pdf.get_y() > 250:
            pdf.add_page()
            pdf.set_y(MARGIN + 4)
        pri = str(g.get("priority") or "WATCH").upper()
        title = str(g.get("title") or "")
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*AMBER if pri in ("HIGH", "CRITICAL", "HOLD") else WHITE)
        pdf.cell(22, 4.4, f"[{pri}]", ln=0)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*WHITE)
        pdf.multi_cell(CONTENT_W - 22, 4.4, _ascii(title))
        if g.get("detail"):
            _muted(pdf, str(g.get("detail"))[:280], 8)
        url = str(g.get("source_url") or "").strip()
        if url:
            pdf.set_x(MARGIN)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*EMERALD)
            pdf.multi_cell(CONTENT_W, 3.5, _ascii(url))

    steps = insp.get("steps") if isinstance(insp, dict) else None
    if isinstance(steps, list) and steps:
        _section_title(pdf, insp.get("title") or "Inspection sequence")
        for i, step in enumerate(steps[:16], 1):
            _body(pdf, f"{i}. {step}", 9)

    pdf.ln(3)
    pdf.set_fill_color(*CARD)
    pdf.set_draw_color(*CARD_EDGE)
    yb = pdf.get_y()
    pdf.rect(MARGIN, yb, CONTENT_W, 16, "DF")
    pdf.set_xy(MARGIN + 4, yb + 3)
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
            "Full city pack is citeable local diligence - not a quote or sealed bid. "
            "Confirm every fee and Unverified line with the AHJ before bid. "
            "app.regguardagent.com"
        ),
    )

    if not output_path:
        out_dir = Path(os.getenv("REGGUARD_DATA_DIR") or "/tmp/regguard_data") / "city_packs"
        out_dir.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() else "_" for c in address)[:40]
        output_path = str(
            out_dir / f"city_pack_{safe}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    pdf.output(output_path)
    logger.info("Full city pack PDF -> %s", output_path)
    return output_path


def generate_city_pack_pdf_bytes(analysis: Dict[str, Any]) -> bytes:
    with tempfile.TemporaryDirectory(prefix="city_pack_") as tmp:
        path = os.path.join(tmp, "RegGuard_Full_City_Pack.pdf")
        generate_city_pack_pdf(analysis, output_path=path)
        raw = Path(path).read_bytes()
    if raw[:4] != b"%PDF":
        raise RuntimeError("City pack PDF generation failed")
    return raw
