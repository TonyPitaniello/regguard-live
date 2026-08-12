"""
Forwardable Bid Packet PDF — punch + fees + gotchas + docs + contingency.
ASCII-only for Helvetica compatibility.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fpdf import FPDF

logger = logging.getLogger(__name__)


def _ascii(text: str) -> str:
    return (
        (text or "")
        .replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


class BidPacketPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(
            0,
            10,
            "Reg Guard Bid Packet - planning aid. Confirm with AHJ.",
            align="C",
        )


def generate_bid_packet_pdf(
    analysis_data: Dict[str, Any],
    output_path: Optional[str] = None,
) -> str:
    """Write bid packet PDF; return path."""
    pi = analysis_data.get("project_info") or {}
    address = _ascii(str(pi.get("address") or "Site"))
    city = _ascii(str(pi.get("city") or ""))
    state = _ascii(str(pi.get("state") or ""))

    pdf = BidPacketPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    w = 190

    def line(text: str, size: int = 9, bold: bool = False) -> None:
        pdf.set_x(10)
        pdf.set_font("Helvetica", "B" if bold else "", size)
        pdf.set_text_color(40, 40, 40)
        pdf.multi_cell(w, 5, _ascii(text))

    line("Reg Guard - Bid Packet", 16, True)
    line(
        f"Site: {address}\n"
        f"Locality: {city}, {state}\n"
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d')} UTC\n"
        "Forwardable pre-bid diligence. Not an official AHJ filing.",
        10,
    )
    pdf.ln(2)

    ahj = analysis_data.get("ahj_card") or {}
    line("AHJ portal & contact", 12, True)
    line(
        f"{ahj.get('name') or 'Local AHJ'}\n"
        f"Portal: {ahj.get('portal_url') or 'Confirm locally'}\n"
        f"Fees: {ahj.get('fees_url') or 'Confirm locally'}\n"
        f"{ahj.get('notes') or ''}",
        9,
    )
    pdf.ln(1)

    fee = analysis_data.get("fee_card") or {}
    line("Fee & timeline extract", 12, True)
    line(f"Timeline: {fee.get('timeline') or 'Confirm with AHJ'}", 9)
    for row in (fee.get("fees") or [])[:8]:
        amt = row.get("amount_usd")
        amt_s = f"${amt:,.0f}" if isinstance(amt, (int, float)) else "TBD"
        ver = "Source" if row.get("verified") else "Unverified"
        line(
            f"- [{ver}] {str(row.get('label') or 'Fee')[:70]}: {amt_s} - "
            f"{str(row.get('detail') or '')[:60]}",
            8,
        )
    pdf.ln(1)

    gotchas = (analysis_data.get("gotcha_watchlist") or {}).get("items") or []
    line("Local gotcha watchlist", 12, True)
    if not gotchas:
        line("No curated gotchas - verify with AHJ (Unverified).", 9)
    for g in gotchas[:10]:
        line(
            f"- [{g.get('priority') or 'NOTE'}] {g.get('title') or ''}: "
            f"{g.get('detail') or ''}",
            8,
        )
    pdf.ln(1)

    docs = (analysis_data.get("document_checklist") or {}).get("items") or []
    line("Document / submittal checklist", 12, True)
    for d in docs[:15]:
        task = d.get("task") if isinstance(d, dict) else str(d)
        line(f"[ ] {task}", 9)
    pdf.ln(1)

    band = analysis_data.get("contingency_band") or {}
    line("Suggested contingency band", 12, True)
    line(
        f"{band.get('pct_low')}% - {band.get('pct_high')}% (mid {band.get('pct_mid')}%)\n"
        f"{band.get('disclaimer') or ''}",
        9,
    )
    pdf.ln(1)

    punch = (analysis_data.get("punch_list") or {}).get("punch_list") or []
    line("Punch list (forwardable)", 12, True)
    for i, item in enumerate(punch[:20], 1):
        if pdf.get_y() > 260:
            pdf.add_page()
        task = (item.get("task") or "")[:90]
        pri = item.get("priority") or ""
        ver = "Source" if item.get("verified") and item.get("source_url") else "Unverified"
        line(f"{i}. [{pri}] [{ver}] {task}", 8)

    if not output_path:
        out_dir = Path(os.getenv("REGGUARD_DATA_DIR") or "/tmp/regguard_data") / "bid_packets"
        out_dir.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() else "_" for c in address)[:40]
        output_path = str(
            out_dir / f"bid_packet_{safe}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        )

    pdf.output(output_path)
    logger.info("Bid packet PDF -> %s", output_path)
    return output_path
