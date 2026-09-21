"""
Labeled SAMPLE Plano PDF for pricing / landing pages.

Designed for Estimator / Permit Runner + Contractor Pro buyers:
  - Looks like the Bid Risk Receipt (dark slate + emerald), not a white office form
  - Shows Source / Unverified honesty
  - Owner + due window on punch lines
  - Explicit SAMPLE / planning-aid labeling (not a quote)

Fictional address — not a live site diligence deliverable.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from fpdf import FPDF

logger = logging.getLogger(__name__)

SAMPLE_ADDRESS = "2100 Legacy Dr (SAMPLE), Plano, TX 75024"
AHJ = "City of Plano Building Inspections"

# Match bid_risk_receipt_pdf / app canvas
BG = (15, 23, 42)  # slate-900
CARD = (30, 41, 59)  # slate-800
CARD_EDGE = (51, 65, 85)  # slate-700
EMERALD = (16, 185, 129)
EMERALD_SOFT = (52, 211, 153)
AMBER = (245, 158, 11)
WHITE = (248, 250, 252)
MUTED = (148, 163, 184)
DIM = (100, 116, 139)
CRIT = (248, 113, 113)
HIGH = (251, 191, 36)

PAGE_W = 215.9
PAGE_H = 279.4
MARGIN = 12
CONTENT_W = PAGE_W - (MARGIN * 2)

PUNCH = [
    {
        "task": "Confirm Plano grounding: Ord. 250.50 — two 8-ft rods @ 20 ft with 2/0 bond",
        "priority": "CRITICAL",
        "owner": "Electrical / Permit runner",
        "when": "Week 1",
        "citation": "SOURCE",
        "source": "Plano Ord. 250.50 (SAMPLE cite)",
    },
    {
        "task": "Pull City of Plano electrical permit fee schedule before bid (sync / trade fees)",
        "priority": "HIGH",
        "owner": "Estimator",
        "when": "Week 1",
        "citation": "SOURCE",
        "source": "Plano fee schedule portal (SAMPLE)",
    },
    {
        "task": "Verify panel schedule vs Plano amendments — do not price base NEC alone",
        "priority": "HIGH",
        "owner": "Electrical estimator",
        "when": "Week 2",
        "citation": "UNVERIFIED",
        "source": "Confirm with Plano plan review",
    },
    {
        "task": "Book rough-in inspection window with Plano Building Inspections",
        "priority": "MEDIUM",
        "owner": "GC / Permit runner",
        "when": "Week 4",
        "citation": "SOURCE",
        "source": "Plano Building Inspections (SAMPLE)",
    },
    {
        "task": "Document AHJ contact + plan-review turnaround in the bid file",
        "priority": "MEDIUM",
        "owner": "Estimator / PM",
        "when": "Week 1",
        "citation": "UNVERIFIED",
        "source": "Confirm current turnaround with AHJ",
    },
]


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


class SamplePlanoPDF(FPDF):
    def header(self) -> None:
        self.set_fill_color(*BG)
        self.rect(0, 0, PAGE_W, PAGE_H, "F")
        # Watermark
        self.set_font("Helvetica", "B", 54)
        self.set_text_color(30, 41, 59)
        try:
            self.rotate(28, x=105, y=150)
            self.text(28, 160, "SAMPLE")
            self.rotate(0)
        except Exception:
            pass

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*DIM)
        self.cell(
            0,
            8,
            _ascii(
                "SAMPLE ONLY - Fictional Plano marketing example. Planning aid, not AHJ advice, "
                "not a quote or sealed bid."
            ),
            align="C",
        )


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
    w = pdf.get_string_width(_ascii(label)) + 5
    pdf.set_fill_color(*bg)
    pdf.set_draw_color(*fg)
    pdf.rect(x, y, w, 5.5, "FD")
    pdf.set_xy(x, y + 0.6)
    pdf.set_text_color(*fg)
    pdf.cell(w, 4, _ascii(label), align="C")
    return x + w + 2


def generate_sample_plano_punch_pdf(output_path: Optional[str] = None) -> str:
    """Write SAMPLE Plano Bid Risk Receipt-style punch PDF; return absolute path."""
    pdf = SamplePlanoPDF(format="Letter")
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.add_page()

    y = MARGIN

    # Brand bar
    pdf.set_fill_color(*EMERALD)
    pdf.rect(MARGIN, y, 3, 14, "F")
    pdf.set_xy(MARGIN + 6, y)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*EMERALD_SOFT)
    pdf.cell(0, 5, "REG GUARD", ln=1)
    pdf.set_x(MARGIN + 6)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 7, "SAMPLE Bid Risk Receipt + Punch", ln=1)
    y = pdf.get_y() + 2

    x = MARGIN
    x = _badge(pdf, "LABELED SAMPLE", fg=AMBER, bg=(69, 26, 3), x=x, y=y)
    x = _badge(pdf, "NOT A LIVE SITE", fg=AMBER, bg=(69, 26, 3), x=x, y=y)
    x = _badge(pdf, "PLANO TX BEACHHEAD", fg=EMERALD, bg=(6, 78, 59), x=x, y=y)
    pdf.set_y(y + 8)

    # Site card
    pdf.set_fill_color(*CARD)
    pdf.set_draw_color(*CARD_EDGE)
    card_top = pdf.get_y()
    pdf.rect(MARGIN, card_top, CONTENT_W, 28, "FD")
    pdf.set_xy(MARGIN + 4, card_top + 3)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 4, "FICTIONAL SITE (marketing demo)", ln=1)
    pdf.set_x(MARGIN + 4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 6, _ascii(SAMPLE_ADDRESS), ln=1)
    pdf.set_x(MARGIN + 4)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 5, _ascii(f"AHJ: {AHJ}  |  Generated: {datetime.utcnow().strftime('%Y-%m-%d')} UTC"), ln=1)
    pdf.set_x(MARGIN + 4)
    pdf.set_text_color(*EMERALD_SOFT)
    pdf.cell(0, 5, "Real lookups: every line shows SOURCE or UNVERIFIED with confirm path", ln=1)
    pdf.set_y(card_top + 30)

    # Stamp strip (what $79 / Pro buyers forward)
    pdf.set_fill_color(*CARD)
    stamp_top = pdf.get_y()
    pdf.rect(MARGIN, stamp_top, CONTENT_W, 22, "FD")
    pdf.set_xy(MARGIN + 4, stamp_top + 3)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*MUTED)
    pdf.cell(60, 4, "STAMP (SAMPLE)", ln=0)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*AMBER)
    pdf.cell(40, 6, "CAUTION", ln=0)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*EMERALD_SOFT)
    pdf.cell(0, 6, "Contingency +2% to +5% (illustrative)", ln=1)
    pdf.set_x(MARGIN + 4)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(
        CONTENT_W - 8,
        4,
        _ascii(
            "Forwardable CYA for GC / owner / client. Planning aid only — not a bid quote. "
            "This is the habit artifact Estimator / Permit Runner ($79) and Contractor Pro ($149) live on."
        ),
    )
    pdf.set_y(stamp_top + 24)

    # Why this sample
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 6, "Why this sample matches Plano buyers", ln=1)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(
        CONTENT_W,
        4,
        _ascii(
            "Beachhead AHJ (Plano), local ordinance + fee-schedule confirm, owner/due window, "
            "and honest Unverified lines. Estimators confirm local permit rates; permit runners "
            "need a forwardable stamp — not a white generic punch form."
        ),
    )
    pdf.ln(2)

    # Punch header
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 6, "Punch list (SAMPLE)", ln=1)

    # Column header
    pdf.set_fill_color(6, 78, 59)  # emerald-900
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 7)
    row_h = 6
    pdf.cell(8, row_h, "#", fill=True)
    pdf.cell(78, row_h, "Action", fill=True)
    pdf.cell(18, row_h, "Priority", fill=True)
    pdf.cell(28, row_h, "Owner", fill=True)
    pdf.cell(16, row_h, "When", fill=True)
    pdf.cell(22, row_h, "Citation", fill=True)
    pdf.ln()

    for i, item in enumerate(PUNCH, 1):
        if pdf.get_y() > 240:
            pdf.add_page()
        # zebra
        if i % 2 == 0:
            pdf.set_fill_color(30, 41, 59)
        else:
            pdf.set_fill_color(22, 32, 52)
        y0 = pdf.get_y()
        pdf.rect(MARGIN, y0, CONTENT_W, 14, "F")

        pri = item["priority"]
        if pri == "CRITICAL":
            pdf.set_text_color(*CRIT)
        elif pri == "HIGH":
            pdf.set_text_color(*HIGH)
        else:
            pdf.set_text_color(*MUTED)

        pdf.set_xy(MARGIN, y0 + 1)
        pdf.set_font("Helvetica", "B", 7)
        pdf.cell(8, 4, str(i))
        pdf.set_text_color(*WHITE)
        pdf.set_font("Helvetica", "", 7)
        pdf.cell(78, 4, _ascii(item["task"][:62]))
        pdf.set_font("Helvetica", "B", 7)
        pdf.cell(18, 4, pri[:8])
        pdf.set_font("Helvetica", "", 6)
        pdf.set_text_color(*MUTED)
        pdf.cell(28, 4, _ascii(item["owner"][:22]))
        pdf.cell(16, 4, item["when"])
        cite = item["citation"]
        if cite == "SOURCE":
            pdf.set_text_color(*EMERALD_SOFT)
        else:
            pdf.set_text_color(*AMBER)
        pdf.set_font("Helvetica", "B", 7)
        pdf.cell(22, 4, cite)
        pdf.ln(5)
        pdf.set_x(MARGIN + 8)
        pdf.set_font("Helvetica", "I", 6)
        pdf.set_text_color(*DIM)
        pdf.cell(0, 4, _ascii(f"Confirm: {item['source']}"), ln=1)
        pdf.set_y(y0 + 14)

    pdf.ln(3)
    pdf.set_fill_color(*CARD)
    note_top = pdf.get_y()
    pdf.rect(MARGIN, note_top, CONTENT_W, 28, "FD")
    pdf.set_xy(MARGIN + 4, note_top + 3)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*EMERALD_SOFT)
    pdf.cell(0, 4, "What paid tiers add on a LIVE address", ln=1)
    pdf.set_x(MARGIN + 4)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(
        CONTENT_W - 8,
        3.5,
        _ascii(
            "Estimator / Permit Runner ($79): full forwardable Receipt + unlocked punch + Saved Jobs.\n"
            "Contractor Pro ($149): deep scout + fee/punch CSV + full city pack PDF for your bid desk.\n"
            "IC Diligence Bundle ($1,500): counsel DOCX + evidence binder + exhibit_id ZIP for one site.\n"
            "This PDF is SAMPLE marketing only — run a free lookup on a real address to see live labeling."
        ),
    )

    if not output_path:
        out_dir = Path(os.getenv("REGGUARD_DATA_DIR") or "/tmp/regguard_data") / "samples"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(out_dir / "plano_punch_list_SAMPLE.pdf")

    pdf.output(output_path)
    logger.info("Wrote SAMPLE Plano PDF -> %s", output_path)
    return output_path
