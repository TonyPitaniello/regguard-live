"""
Bid Risk Receipt — single-page forwardable arbitrage artifact.
Site + AHJ, contingency band, top 3 margin killers, share CTA.
ASCII-only for Helvetica compatibility.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fpdf import FPDF

from arbitrage_enrichment import build_margin_killers

logger = logging.getLogger(__name__)

APP_URL = os.getenv("FRONTEND_APP_URL", "https://app.regguardagent.com").rstrip("/")


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


class BidRiskReceiptPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(110, 110, 110)
        self.cell(
            0,
            8,
            "Reg Guard Bid Risk Receipt - planning aid. Confirm with AHJ before bid.",
            align="C",
        )


def generate_bid_risk_receipt_pdf(
    analysis_data: Dict[str, Any],
    output_path: Optional[str] = None,
    *,
    generated_for: Optional[str] = None,
    share_url: Optional[str] = None,
) -> str:
    """Write a strict 1-page Bid Risk Receipt PDF; return path."""
    pi = analysis_data.get("project_info") or {}
    address = _ascii(str(pi.get("address") or "Site"))
    city = _ascii(str(pi.get("city") or ""))
    state = _ascii(str(pi.get("state") or ""))
    zip_code = _ascii(str(pi.get("zip") or ""))
    who = _ascii((generated_for or "").strip() or "Anonymous lookup")
    cta = _ascii((share_url or f"{APP_URL}/?utm_source=bid_receipt").strip())

    killers = analysis_data.get("margin_killers")
    if not isinstance(killers, list) or not killers:
        killers = build_margin_killers(analysis_data, limit=3)

    band = analysis_data.get("contingency_band") or {}
    ahj = analysis_data.get("ahj_card") or {}
    fee = analysis_data.get("fee_card") or {}

    pdf = BidRiskReceiptPDF(format="Letter")
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    w = 190

    def line(text: str, size: int = 9, bold: bool = False, color=(35, 35, 35)) -> None:
        pdf.set_x(10)
        pdf.set_font("Helvetica", "B" if bold else "", size)
        pdf.set_text_color(*color)
        pdf.multi_cell(w, 4.5, _ascii(text))

    # Header
    line("REG GUARD", 18, True, (20, 90, 70))
    line("BID RISK RECEIPT", 14, True)
    line(
        "One-page pre-bid arbitrage stamp. Not an official AHJ filing.",
        8,
        False,
        (90, 90, 90),
    )
    pdf.ln(2)

    line("SITE / AHJ", 10, True, (20, 90, 70))
    line(f"{address}", 11, True)
    line(f"{city}, {state} {zip_code}".strip(), 9)
    line(
        f"AHJ: {_ascii(str(ahj.get('name') or 'Local AHJ'))}\n"
        f"Portal: {_ascii(str(ahj.get('portal_url') or 'Confirm locally'))}\n"
        f"Timeline hint: {_ascii(str(fee.get('timeline') or 'Confirm with AHJ'))}",
        8,
    )
    pdf.ln(2)

    # Contingency — the number people screenshot
    low = band.get("pct_low")
    mid = band.get("pct_mid")
    high = band.get("pct_high")
    usd_mid = band.get("usd_mid")
    line("SUGGESTED CONTINGENCY BAND", 10, True, (20, 90, 70))
    if low is not None and high is not None:
        band_line = f"Plan +{low}% to +{high}% (mid {mid}%)"
        if isinstance(usd_mid, (int, float)) and usd_mid:
            band_line += f"  |  ~${int(usd_mid):,} mid on current rollup"
        line(band_line, 12, True)
    else:
        line("Confirm Critical/High items before setting contingency.", 10)
    line(
        _ascii(
            str(
                band.get("disclaimer")
                or "Planning aid only — not a quote. Re-check before bid day."
            )
        ),
        7,
        False,
        (100, 100, 100),
    )
    pdf.ln(2)

    line("TOP 3 MARGIN KILLERS", 10, True, (20, 90, 70))
    for i, k in enumerate(killers[:3], 1):
        if not isinstance(k, dict):
            continue
        ver = "Source" if k.get("verified") and k.get("source_url") else "Unverified"
        pri = str(k.get("priority") or "NOTE")
        title = _ascii(str(k.get("title") or "Item"))
        detail = _ascii(str(k.get("detail") or ""))
        line(f"{i}. [{pri}] [{ver}] {title}", 9, True)
        if detail:
            line(f"   {detail}", 8, False, (70, 70, 70))
    pdf.ln(2)

    line("STAMP", 10, True, (20, 90, 70))
    stamp_date = datetime.utcnow().strftime("%Y-%m-%d")
    line(
        f"Generated for: {who}\n"
        f"Date: {stamp_date} UTC\n"
        "Re-check this site before bid — fees and portal asks move.",
        9,
    )
    pdf.ln(2)

    line("SHARE / NEXT SITE", 10, True, (20, 90, 70))
    line(
        "Forward this receipt to your GC, estimator, or permit runner.\n"
        f"Run YOUR address free: {cta}",
        9,
    )
    line(
        "Full punch list + deep scout available in Reg Guard after unlock / upgrade.",
        7,
        False,
        (110, 110, 110),
    )

    if not output_path:
        out_dir = Path(os.getenv("REGGUARD_DATA_DIR") or "/tmp/regguard_data") / "bid_receipts"
        out_dir.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() else "_" for c in address)[:40]
        output_path = str(
            out_dir / f"bid_receipt_{safe}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        )

    pdf.output(output_path)
    logger.info("Bid Risk Receipt PDF -> %s", output_path)
    return output_path
