"""Bid Sheet PDF — punch + fees + gotchas with clickable source hyperlinks."""
from __future__ import annotations

import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from pdf_generator import RegGuardPDF, _EMERALD, _MUTED, _TEXT
from pdf_text import ascii_safe

logger = logging.getLogger(__name__)


def analysis_to_bid_sheet_pdf(analysis: Dict[str, Any], output_path: Optional[str] = None) -> bytes:
    """Build a branded Bid Sheet PDF with hyperlinks (companion to CSV export)."""
    from artifact_naming import document_display_title, site_line_from_analysis

    from ic_buyer_brief import apply_cited_schedule_fees, schedule_usd, stated_schedule_amount

    analysis = apply_cited_schedule_fees(analysis)
    pdf = RegGuardPDF()
    pi = analysis.get("project_info") or {}
    address = pi.get("address") or "Project site"
    city = pi.get("city") or ""
    state = pi.get("state") or ""
    zip_code = pi.get("zip") or ""
    site_line = site_line_from_analysis(analysis)
    doc_title = document_display_title(site_line, "BID SHEET")

    pdf.add_page()
    try:
        pdf.set_title(ascii_safe(doc_title)[:120])
        pdf.set_author("Reg Guard")
    except Exception:
        pass
    pdf.add_brand_banner(
        ascii_safe(doc_title),
        "Punch + fees + gotchas with source links  |  Planning aid - not a quote",
    )

    pdf.add_section_title("Site")
    pdf.add_info_box("Address", str(address))
    pdf.add_info_box("Locality", f"{city}, {state} {zip_code}".strip())

    ahj = analysis.get("ahj_card") if isinstance(analysis.get("ahj_card"), dict) else {}
    if ahj.get("name"):
        pdf.add_section_title("Authority having jurisdiction")
        pdf.add_info_box("AHJ", str(ahj.get("name")))
        if ahj.get("portal_url"):
            pdf.add_link_line("Portal", str(ahj.get("portal_url")))
        if ahj.get("fees_url"):
            pdf.add_link_line("Fees", str(ahj.get("fees_url")))

    pdf.add_section_title("Contingency")
    pdf.write_wrapped(
        "No schedule states a contingency percent for this address.",
        size=11,
        bold=True,
        color=_EMERALD,
        h=6,
    )

    punch = ((analysis.get("punch_list") or {}).get("punch_list")) or []
    items = [i for i in punch if isinstance(i, dict)]
    if items:
        pdf.add_section_title("Punch list lines")
        for i, item in enumerate(items[:40], 1):
            pri = str(item.get("priority") or "").upper()
            task = item.get("task") or item.get("title") or "Item"
            cost = stated_schedule_amount(
                {
                    "amount_usd": item.get("estimated_cost"),
                    "verified": item.get("verified"),
                    "source_url": item.get("source_url"),
                }
            )
            cost_s = f" — {schedule_usd(cost)}" if cost is not None else ""
            pdf.write_wrapped(
                f"{i}. [{pri}] {task}{cost_s}",
                size=9,
                bold=True,
                color=_TEXT,
                h=5,
            )
            bits = []
            if item.get("timeline"):
                bits.append(f"Timeline: {item.get('timeline')}")
            if item.get("responsible_party"):
                bits.append(f"Owner: {item.get('responsible_party')}")
            if bits:
                pdf.write_wrapped(" | ".join(bits), size=8, color=_MUTED, h=4)
            url = (item.get("source_url") or "").strip()
            if url:
                pdf.add_link_line(item.get("source_label") or "Source", url)
            pdf.ln(1)

    fees = ((analysis.get("fee_card") or {}).get("fees")) or []
    fee_rows = [f for f in fees if isinstance(f, dict)]
    if fee_rows:
        pdf.add_section_title("Fee planning rows")
        for fee in fee_rows[:20]:
            label = fee.get("label") or "Fee"
            stated = stated_schedule_amount(fee)
            amt_s = schedule_usd(stated) if stated is not None else ""
            trade = str(fee.get("trade") or "general").strip().upper() or "GENERAL"
            head = f"[{trade}] {label}: {amt_s}" if amt_s else f"[{trade}] {label}"
            pdf.write_wrapped(head, size=9, bold=True, h=5)
            if fee.get("detail"):
                pdf.write_wrapped(str(fee.get("detail")), size=8, color=_MUTED, h=4)
            url = (fee.get("source_url") or "").strip()
            if url:
                pdf.add_link_line("Source", url)
            pdf.ln(0.5)

    gotchas = ((analysis.get("gotcha_watchlist") or {}).get("items")) or []
    g_rows = [g for g in gotchas if isinstance(g, dict)]
    if g_rows:
        pdf.add_section_title("Gotcha watchlist")
        for g in g_rows[:15]:
            pri = g.get("priority") or "HIGH"
            pdf.write_wrapped(f"[{pri}] {g.get('title') or ''}", size=9, bold=True, h=5)
            if g.get("detail"):
                pdf.write_wrapped(ascii_safe(str(g.get("detail")), 600), size=8, color=_MUTED, h=4)
            url = (g.get("source_url") or "").strip()
            if url:
                pdf.add_link_line("Source", url)
            pdf.ln(0.5)

    pdf.add_muted_note(
        "A dollar on this sheet is a figure the cited schedule states. "
        "Not a quote, a permit total, or a filing."
    )

    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(prefix="bid_sheet_", suffix=".pdf", delete=False)
        tmp.close()
        output_path = tmp.name
    pdf.output(output_path)
    data = Path(output_path).read_bytes()
    logger.info("Bid sheet PDF generated (%s bytes)", len(data))
    return data
