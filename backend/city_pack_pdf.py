"""Full city pack PDF — AHJ, fees, gotchas, inspections. Same dark canvas as Bid Packet."""
from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from pdf_stamp_helpers import short_host as short_host_safe

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
    PURPLE,
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
    prior_ahj = dict(analysis_data.get("ahj_card") or {})
    try:
        from delivery_parity import prepare_analysis_for_delivery

        analysis_data = prepare_analysis_for_delivery(analysis_data)
    except Exception:
        analysis_data = _ensure_arbitrage(analysis_data)
    from ic_buyer_brief import apply_cited_desk_links, apply_cited_schedule_fees

    analysis_data = apply_cited_desk_links(analysis_data)
    analysis_data = apply_cited_schedule_fees(analysis_data)
    ahj = dict(analysis_data.get("ahj_card") or {})
    city_name = str((analysis_data.get("project_info") or {}).get("city") or "").strip().lower()
    for key in ("portal_url", "apply_url"):
        current = str(ahj.get(key) or "")
        previous = str(prior_ahj.get(key) or "")
        if previous.startswith("https://") and not current.startswith("https://"):
            ahj[key] = previous
    previous_portal = str(prior_ahj.get("portal_url") or "")
    if (
        previous_portal.startswith("https://")
        and previous_portal != str(ahj.get("fees_url") or "")
        and str(ahj.get("portal_url") or "") == str(ahj.get("fees_url") or "")
    ):
        ahj["portal_url"] = previous_portal
    prior_name = str(prior_ahj.get("name") or "").strip()
    if prior_name and str(ahj.get("name") or "").strip().lower() in ("", city_name):
        ahj["name"] = prior_name
    analysis_data["ahj_card"] = ahj

    pi = analysis_data.get("project_info") or {}
    address = _ascii(str(pi.get("address") or "Site"))
    city = _ascii(str(pi.get("city") or ""))
    state = _ascii(str(pi.get("state") or ""))
    zip_code = _ascii(str(pi.get("zip") or ""))
    locality = ", ".join(p for p in (city, state) if p)
    if zip_code:
        locality = f"{locality} {zip_code}".strip()

    ahj = analysis_data.get("ahj_card") or {}

    from artifact_naming import document_display_title, site_line_from_analysis

    site_line = site_line_from_analysis(analysis_data)
    doc_title = document_display_title(site_line, "FULL CITY PACK")

    pdf = BidPacketPDF()
    pdf._footer_label = _ascii(doc_title)[:90]
    pdf._footer_line = "A dollar on this pack is a figure the cited schedule states."
    try:
        pdf.set_title(_ascii(doc_title)[:120])
        pdf.set_author("Reg Guard")
    except Exception:
        pass
    pdf.add_page()
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.set_y(MARGIN + 4)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*WHITE)
    pdf.multi_cell(CONTENT_W, 6, address)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(CONTENT_W, 5, locality)
    ahj_name = _ascii(str(ahj.get("name") or "Local AHJ"))
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*WHITE)
    pdf.multi_cell(CONTENT_W, 5, ahj_name)

    from bid_risk_receipt_pdf import _https_url, _schedule_url
    from pdf_stamp_helpers import paint_linked_block, stamp_display_grade

    fees_url = _schedule_url(str(ahj.get("fees_url") or ""))
    if not fees_url:
        for row in _fee_rows(analysis_data):
            fees_url = _schedule_url(str(row.get("source_url") or ""))
            if fees_url:
                break
    links = (
        ("Portal", _https_url(ahj.get("portal_url"))),
        ("Fees schedule", fees_url),
        ("Apply", _https_url(ahj.get("apply_url"))),
    )
    for kind, url in links:
        if not url:
            continue
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*EMERALD)
        paint_linked_block(
            pdf,
            _ascii(f"{kind}: {url}"),
            url,
            width=CONTENT_W,
            line_h=4.0,
        )

    rg = analysis_data.get("regguard_stamp") if isinstance(analysis_data.get("regguard_stamp"), dict) else {}
    if not rg.get("grade"):
        try:
            from regguard_stamp import apply_regguard_stamp

            analysis_data = apply_regguard_stamp(dict(analysis_data))
            rg = analysis_data.get("regguard_stamp") or {}
        except Exception:
            pass
    display = stamp_display_grade(rg.get("grade") or analysis_data.get("stamp_grade"))
    if display not in ("CLEAR", "CAUTION", "HOLD"):
        display = "HOLD"
    pdf.ln(1)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*(AMBER if display == "HOLD" else (AMBER_SOFT if display == "CAUTION" else EMERALD_SOFT)))
    pdf.cell(CONTENT_W, 6, _ascii(f"REGGUARD STAMP: {display}"), ln=1)

    from ic_buyer_brief import schedule_usd, stated_schedule_amount

    fees = _fee_rows(analysis_data)
    for row in fees:
        if pdf.get_y() > 250:
            pdf.add_page()
            pdf.set_y(MARGIN + 4)
        stated = stated_schedule_amount(row)
        label = str(row.get("label") or row.get("name") or "Fee")
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*WHITE)
        if stated is None:
            pdf.multi_cell(CONTENT_W, 4.4, _ascii(label))
            continue
        pdf.multi_cell(CONTENT_W, 4.4, _ascii(f"{label}: {schedule_usd(stated)}"))
        src = _schedule_url(str(row.get("source_url") or "")) or fees_url
        if src:
            pdf.set_x(MARGIN)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*EMERALD)
            paint_linked_block(pdf, _ascii(src), src, width=CONTENT_W, line_h=3.6)

    punch = analysis_data.get("punch_list") if isinstance(analysis_data.get("punch_list"), dict) else {}
    ranked = punch.get("ranked") if isinstance(punch.get("ranked"), list) else []
    if not ranked:
        ranked = punch.get("punch_list") if isinstance(punch.get("punch_list"), list) else []
    for item in ranked:
        if not isinstance(item, dict):
            continue
        if pdf.get_y() > 250:
            pdf.add_page()
            pdf.set_y(MARGIN + 4)
        task = str(item.get("task") or item.get("title") or item.get("label") or "Punch item")
        owner = str(item.get("owner") or item.get("responsible_party") or item.get("who") or "").strip()
        due = str(item.get("due_window") or item.get("due") or item.get("timeline") or item.get("timing") or "").strip()
        url = _https_url(item.get("source_url"))
        badge = "Source" if item.get("verified") is True and url else "Unverified"
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*WHITE)
        pdf.multi_cell(CONTENT_W, 4.2, _ascii(task))
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*EMERALD if badge == "Source" else AMBER_SOFT)
        pdf.multi_cell(CONTENT_W, 4.2, _ascii(" · ".join(bit for bit in (owner, due, badge) if bit)))
        if badge == "Source":
            pdf.set_x(MARGIN)
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*EMERALD)
            paint_linked_block(pdf, _ascii(url), url, width=CONTENT_W, line_h=3.6)

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
