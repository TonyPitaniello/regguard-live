"""
Labeled SAMPLE Plano punch-list PDF for pricing / landing pages.
Fictional address - not a real site diligence deliverable.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fpdf import FPDF

logger = logging.getLogger(__name__)

SAMPLE_ADDRESS = "2100 Legacy Dr (SAMPLE), Plano, TX 75024"


class SamplePlanoPunchPDF(FPDF):
    def header(self) -> None:
        # Large SAMPLE watermark (compatible with fpdf / fpdf2)
        self.set_font("Helvetica", "B", 48)
        self.set_text_color(230, 230, 230)
        try:
            self.rotate(30, x=105, y=140)
            self.text(40, 150, "SAMPLE")
            self.rotate(0)
        except Exception:
            self.set_xy(20, 130)
            self.cell(0, 16, "SAMPLE", align="C")

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(
            0,
            10,
            "SAMPLE ONLY - Fictional Plano example for Reg Guard marketing. Not AHJ advice.",
            align="C",
        )


def _sample_analysis() -> Dict[str, Any]:
    return {
        "project_info": {
            "address": SAMPLE_ADDRESS,
            "city": "Plano",
            "state": "TX",
            "zip": "75024",
            "type": "commercial_electrical",
        },
        "punch_list": {
            "timeline_summary": "6-10 weeks (illustrative)",
            "estimated_total_cost": 18500,
            "punch_list": [
                {
                    "task": "Confirm Plano Ord. 250.50 two 8-ft rods @ 20 ft with 2/0 bond",
                    "priority": "CRITICAL",
                    "timeline": "Week 1",
                    "estimated_cost": 1200,
                },
                {
                    "task": "Pull City of Plano 2026 electrical permit fee schedule ($75 sync)",
                    "priority": "HIGH",
                    "timeline": "Week 1",
                    "estimated_cost": 75,
                },
                {
                    "task": "Verify panel schedule vs Plano amendments (not base NEC alone)",
                    "priority": "HIGH",
                    "timeline": "Week 2",
                    "estimated_cost": 0,
                },
                {
                    "task": "Schedule rough-in inspection window with Plano Building Inspections",
                    "priority": "MEDIUM",
                    "timeline": "Week 4",
                    "estimated_cost": 0,
                },
                {
                    "task": "Document AHJ contact + plan review turnaround for bid file",
                    "priority": "MEDIUM",
                    "timeline": "Week 1",
                    "estimated_cost": 0,
                },
            ],
        },
    }


def generate_sample_plano_punch_pdf(output_path: Optional[str] = None) -> str:
    """Write SAMPLE Plano punch list PDF; return absolute path."""
    analysis = _sample_analysis()
    pdf = SamplePlanoPunchPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 10, "Reg Guard - SAMPLE Contractor Punch List", ln=True)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(180, 40, 40)
    pdf.cell(0, 8, "LABELED SAMPLE - Not a live site report", ln=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(50, 50, 50)
    pdf.multi_cell(
        0,
        6,
        f"Site (fictional): {SAMPLE_ADDRESS}\n"
        "Coverage demo: Plano, TX citeable path. Real lookups show Source or Unverified.\n"
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d')} UTC",
    )
    pdf.ln(4)

    punch = analysis["punch_list"]
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Project timeline & cost (illustrative)", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Timeline: {punch['timeline_summary']}", ln=True)
    pdf.cell(0, 6, f"Est. cost: ${punch['estimated_total_cost']:,.0f}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Action items", ln=True)

    # Table header
    pdf.set_fill_color(99, 102, 241)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(10, 8, "#", fill=True)
    pdf.cell(95, 8, "Action item", fill=True)
    pdf.cell(25, 8, "Priority", fill=True)
    pdf.cell(25, 8, "When", fill=True)
    pdf.cell(25, 8, "Est.", fill=True)
    pdf.ln()

    pdf.set_text_color(40, 40, 40)
    for i, item in enumerate(punch["punch_list"], 1):
        pdf.set_font("Helvetica", "", 8)
        y0 = pdf.get_y()
        if y0 > 250:
            pdf.add_page()
        task = (item.get("task") or "")[:72]
        cost = item.get("estimated_cost") or 0
        pdf.cell(10, 7, str(i))
        pdf.cell(95, 7, task)
        pdf.cell(25, 7, item.get("priority") or "")
        pdf.cell(25, 7, item.get("timeline") or "")
        pdf.cell(25, 7, f"${cost:,.0f}" if cost else "TBD")
        pdf.ln()

    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(
        0,
        5,
        "This PDF is a marketing sample. Purchase Contractor Pro or an IC Project Report "
        "for a live address lookup with Source / Unverified labeling.",
    )

    if not output_path:
        out_dir = Path(os.getenv("REGGUARD_DATA_DIR") or "/tmp/regguard_data") / "samples"
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(out_dir / "plano_punch_list_SAMPLE.pdf")

    pdf.output(output_path)
    logger.info("Wrote SAMPLE Plano PDF -> %s", output_path)
    return output_path
