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
    pdf = RegGuardPDF()
    pi = analysis.get("project_info") or {}
    address = pi.get("address") or "Project site"
    city = pi.get("city") or ""
    state = pi.get("state") or ""
    zip_code = pi.get("zip") or ""

    pdf.add_page()
    pdf.add_brand_banner(
        "Bid Sheet (planning)",
        f"{address}  |  Punch + fees + gotchas with source links",
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

    band = analysis.get("contingency_band") if isinstance(analysis.get("contingency_band"), dict) else {}
    if band.get("pct_low") is not None and band.get("pct_high") is not None:
        pdf.add_section_title("Contingency band (planning aid)")
        pdf.write_wrapped(
            f"+{band.get('pct_low')}% to +{band.get('pct_high')}% "
            f"(mid {band.get('pct_mid', 'n/a')}%) — not a quote",
            size=11,
            bold=True,
            color=_EMERALD,
            h=6,
        )
        if band.get("disclaimer"):
            pdf.write_wrapped(str(band.get("disclaimer")), size=8, color=_MUTED, h=4)

    punch = ((analysis.get("punch_list") or {}).get("punch_list")) or []
    items = [i for i in punch if isinstance(i, dict)]
    if items:
        pdf.add_section_title("Punch list lines")
        for i, item in enumerate(items[:40], 1):
            pri = str(item.get("priority") or "").upper()
            task = item.get("task") or item.get("title") or "Item"
            cost = item.get("estimated_cost")
            cost_s = f" — ${cost:,.0f}" if isinstance(cost, (int, float)) else ""
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
            amt = fee.get("amount_usd")
            amt_s = f"${amt:,.0f}" if isinstance(amt, (int, float)) else "confirm on schedule"
            trade = fee.get("trade") or "general"
            pdf.write_wrapped(f"[{trade}] {label}: {amt_s}", size=9, bold=True, h=5)
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
        "Bid Sheet PDF — planning aid with clickable sources. Not a quote. Confirm every fee and "
        "requirement with the AHJ before bid."
    )

    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(prefix="bid_sheet_", suffix=".pdf", delete=False)
        tmp.close()
        output_path = tmp.name
    pdf.output(output_path)
    data = Path(output_path).read_bytes()
    logger.info("Bid sheet PDF generated (%s bytes)", len(data))
    return data
