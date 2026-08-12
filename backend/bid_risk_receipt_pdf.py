"""
Bid Risk Receipt — forward-first one-pager.
Pattern: site+AHJ, big contingency %, 3 killers, Source/Unverified,
name stamp, CYA — not an ad, not a filing, not guaranteed savings.
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

CYA = (
    "PLANNING AID ONLY — not a quote, not guaranteed savings, "
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
        .encode("latin-1", "replace")
        .decode("latin-1")
    )


class BidRiskReceiptPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(110, 110, 110)
        self.multi_cell(0, 3.5, _ascii(CYA), align="C")


def generate_bid_risk_receipt_pdf(
    analysis_data: Dict[str, Any],
    output_path: Optional[str] = None,
    *,
    generated_for: Optional[str] = None,
    share_url: Optional[str] = None,
) -> str:
    """Write a strict 1-page forwardable Bid Risk Receipt; return path."""
    pi = analysis_data.get("project_info") or {}
    address = _ascii(str(pi.get("address") or "Site"))
    city = _ascii(str(pi.get("city") or ""))
    state = _ascii(str(pi.get("state") or ""))
    zip_code = _ascii(str(pi.get("zip") or ""))
    who = _ascii((generated_for or "").strip() or "Estimator")
    # Recipient CTA stays tiny — one line, no upgrade pitch
    cta = _ascii((share_url or f"{APP_URL}/?utm_source=bid_receipt").strip())

    killers = analysis_data.get("margin_killers")
    if not isinstance(killers, list) or not killers:
        killers = build_margin_killers(analysis_data, limit=3)

    band = analysis_data.get("contingency_band") or {}
    ahj = analysis_data.get("ahj_card") or {}
    dc = analysis_data.get("dc_positioning") or {}

    pdf = BidRiskReceiptPDF(format="Letter")
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    w = 190

    def line(text: str, size: int = 9, bold: bool = False, color=(35, 35, 35)) -> None:
        pdf.set_x(10)
        pdf.set_font("Helvetica", "B" if bold else "", size)
        pdf.set_text_color(*color)
        pdf.multi_cell(w, 4.2, _ascii(text))

    # --- Forward framing (CYA for the sender) ---
    line("FLAGGED BEFORE BID DAY", 11, True, (20, 90, 70))
    line(
        "I flagged risk on THIS site. Forward so the GC/owner sees it before bid.",
        9,
    )
    line("Reg Guard  |  Bid Risk Receipt", 8, False, (100, 100, 100))
    pdf.ln(2)

    # --- Site + AHJ first ---
    line("THIS SITE", 9, True, (20, 90, 70))
    line(address, 13, True)
    line(f"{city}, {state} {zip_code}".strip(), 10)
    line(
        f"AHJ: {_ascii(str(ahj.get('name') or 'Local AHJ'))}",
        9,
        True,
    )
    portal = str(ahj.get("portal_url") or "").strip()
    if portal:
        line(f"Portal: {_ascii(portal)}", 7, False, (80, 80, 80))
    if dc.get("headline"):
        line(
            "Note: AHJ + utility often run on parallel clocks (not an interconnect study).",
            7,
            False,
            (80, 80, 80),
        )
    pdf.ln(2)

    # --- BIG contingency (screenshot bait) ---
    low = band.get("pct_low")
    mid = band.get("pct_mid")
    high = band.get("pct_high")
    line("CONTINGENCY (screenshot this)", 9, True, (20, 90, 70))
    if low is not None and high is not None:
        line(f"+{low}%  to  +{high}%", 22, True, (20, 90, 70))
        line(f"mid {mid}%   |   planning aid — NOT a quote", 9)
    else:
        line("Set contingency after confirming Critical/High items with AHJ.", 10)
    pdf.ln(2)

    # --- Exactly 3 killers, short ---
    line("TOP 3 RISK FLAGS  (Source or Unverified)", 9, True, (20, 90, 70))
    for i, k in enumerate(list(killers)[:3], 1):
        if not isinstance(k, dict):
            continue
        ver = "Source" if k.get("verified") and k.get("source_url") else "Unverified"
        pri = str(k.get("priority") or "NOTE")
        title = _ascii(str(k.get("title") or "Item"))[:90]
        detail = _ascii(str(k.get("detail") or ""))[:110]
        line(f"{i}. [{pri}] [{ver}] {title}", 9, True)
        if detail:
            line(f"    {detail}", 7, False, (70, 70, 70))
        pe = k.get("planning_exposure") or {}
        if isinstance(pe, dict) and pe.get("usd_mid") is not None:
            line(
                f"    Exposure (planning only): ~${int(pe.get('usd_low') or 0):,}"
                f"-${int(pe.get('usd_high') or 0):,} — not guaranteed savings",
                7,
                False,
                (90, 90, 90),
            )
    pdf.ln(2)

    # --- Stamp ---
    stamp_date = datetime.utcnow().strftime("%Y-%m-%d")
    line("STAMP", 9, True, (20, 90, 70))
    line(
        f"Flagged by: {who}\n"
        f"Date: {stamp_date} UTC\n"
        "Re-check before bid — fees and portal asks move.",
        9,
    )
    pdf.ln(1)

    # --- Tiny recipient line (not an upgrade ad) ---
    line(
        f"Recipient: run your own address if needed — {cta}",
        7,
        False,
        (120, 120, 120),
    )

    if not output_path:
        out_dir = Path(os.getenv("REGGUARD_DATA_DIR") or "/tmp/regguard_data") / "bid_receipts"
        out_dir.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() else "_" for c in address)[:40]
        output_path = str(
            out_dir / f"bid_receipt_{safe}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        )

    pdf.output(output_path)
    logger.info("Bid Risk Receipt PDF (forwardable) -> %s", output_path)
    return output_path
