"""
PDF Generator: RegGuard-branded IC / delivery PDFs.

Visual language matches the app: slate dark background, emerald accents, purple rules.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fpdf import FPDF

from pdf_text import ascii_safe, cite_host, markdown_to_bullets, markdown_to_plain

logger = logging.getLogger(__name__)

# App palette: slate-900 / purple-500 / emerald-500 / amber
_BG = (15, 23, 42)  # slate-900
_CARD = (30, 41, 59)  # slate-800
_TEXT = (248, 250, 252)  # slate-50
_MUTED = (148, 163, 184)  # slate-400
_EMERALD = (16, 185, 129)
_PURPLE = (168, 85, 247)
_AMBER = (245, 158, 11)
_RED = (248, 113, 113)
_RULE = (71, 85, 105)  # slate-600


class RegGuardPDF(FPDF):
    """Base PDF — dark slate brand matching the contractor app."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(14, 14, 14)
        self.company_name = "RegGuard"
        self.company_tagline = "Site Diligence Intelligence"
        self._doc_title = ""
        # Back-compat aliases used by older helpers
        self.color_primary = _PURPLE
        self.color_secondary = _EMERALD
        self.color_accent = _EMERALD
        self.color_dark = _TEXT
        self.color_light = _CARD

    def header(self) -> None:  # type: ignore[override]
        self.set_fill_color(*_BG)
        self.rect(0, 0, self.w, self.h, "F")

    def footer(self) -> None:  # type: ignore[override]
        self.set_y(-14)
        self.set_draw_color(*_RULE)
        self.line(14, self.get_y(), self.w - 14, self.get_y())
        self.set_y(-12)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*_MUTED)
        self.cell(60, 8, f"Page {self.page_no()}", align="L")
        self.cell(70, 8, datetime.now().strftime("%b %d, %Y"), align="C")
        self.cell(0, 8, "(c) RegGuard - planning aid", align="R")

    def add_brand_banner(self, title: str, subtitle: Optional[str] = None) -> None:
        """Top brand strip + title (call after add_page)."""
        self.set_fill_color(88, 28, 135)  # purple-900-ish
        self.rect(0, 0, self.w, 28, "F")
        self.set_fill_color(*_EMERALD)
        self.rect(0, 28, self.w, 1.2, "F")

        self.set_xy(14, 6)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(255, 255, 255)
        self.cell(0, 7, self.company_name, ln=True)
        self.set_x(14)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(221, 214, 254)
        self.cell(0, 5, self.company_tagline, ln=True)

        self.set_xy(14, 34)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*_TEXT)
        self.multi_cell(self.epw, 6, ascii_safe(title, 120))
        if subtitle:
            self.set_font("Helvetica", "", 9)
            self.set_text_color(*_MUTED)
            self.set_x(14)
            self.multi_cell(self.epw, 4.5, ascii_safe(subtitle, 200))
        self.ln(3)
        self._doc_title = title

    def add_section_title(self, title: str) -> None:
        self.ln(2)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*_EMERALD)
        self.set_x(14)
        self.cell(0, 7, ascii_safe(title.upper(), 80), ln=True)
        y = self.get_y()
        self.set_draw_color(*_PURPLE)
        self.set_line_width(0.4)
        self.line(14, y, 14 + min(70, self.epw), y)
        self.ln(3)
        self.set_text_color(*_TEXT)

    def add_info_box(self, label: str, value: str) -> None:
        self.set_x(14)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*_MUTED)
        self.cell(42, 6, ascii_safe(label, 40) + ":", ln=False)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*_TEXT)
        self.multi_cell(self.epw - 42, 6, ascii_safe(value, 200))

    def add_muted_note(self, text: str) -> None:
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*_MUTED)
        self.set_x(14)
        self.multi_cell(self.epw, 4, ascii_safe(text, 500))
        self.set_text_color(*_TEXT)

    def add_bullet(self, text: str, *, bullet: str = "-") -> None:
        self.set_x(14)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*_TEXT)
        self.multi_cell(self.epw, 4.5, f"{bullet} {ascii_safe(text, 400)}")

    # Legacy name used by older call sites
    def add_header(self, title: str, subtitle: Optional[str] = None) -> None:
        self.add_brand_banner(title, subtitle)

    def add_footer(self) -> None:
        """No-op — real footer is drawn via footer()."""
        return


class ResearchMemoPDF(RegGuardPDF):
    """Research Memo — site summary + action plan (no raw markdown)."""

    def generate(self, analysis_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
        logger.info("Generating research memo PDF...")
        try:
            self.add_page()
            project_info = analysis_data.get("project_info", {}) or {}
            address = project_info.get("address", "Unknown")
            self.add_brand_banner(
                "Site Diligence Research Memo",
                f"{address}  |  IC Project Report",
            )

            self.add_section_title("Project information")
            city = project_info.get("city", "")
            state = project_info.get("state", "")
            zip_code = project_info.get("zip", "")
            self.add_info_box("Location", f"{city}, {state} {zip_code}".strip())
            self.add_info_box("Project type", str(project_info.get("type", "commercial")))
            self.add_info_box("Analysis date", datetime.now().strftime("%B %d, %Y"))

            pack = analysis_data.get("pdf_pack") if isinstance(analysis_data.get("pdf_pack"), dict) else {}
            if pack.get("ahj_name"):
                self.add_section_title("Authority having jurisdiction")
                self.add_info_box("AHJ", str(pack.get("ahj_name") or ""))
                if pack.get("portal_url"):
                    self.add_info_box("Portal", str(pack.get("portal_url")))
                if pack.get("fees_url"):
                    self.add_info_box("Fees URL", str(pack.get("fees_url")))
                if pack.get("stamp_grade"):
                    self.add_info_box("RegGuard stamp", str(pack.get("stamp_grade")))
                if pack.get("beachhead"):
                    self.add_muted_note(
                        f"Beachhead pack: {pack.get('pack_key') or 'curated'} - citeable local fees/gotchas included below."
                    )

            env = analysis_data.get("environmental_screening", {}) or {}
            risk_level = str(env.get("risk_level", "UNKNOWN")).upper()
            self.add_section_title("Risk snapshot")
            risk_color = {
                "LOW": _EMERALD,
                "MEDIUM": _AMBER,
                "HIGH": _RED,
                "CRITICAL": _RED,
            }.get(risk_level, _MUTED)
            self.set_font("Helvetica", "B", 12)
            self.set_text_color(*risk_color)
            self.set_x(14)
            self.cell(0, 8, f"Overall risk: {risk_level}", ln=True)
            self.set_text_color(*_TEXT)

            fee_lines = list(pack.get("fee_lines") or [])
            if fee_lines:
                self.add_section_title("Citeable fee planning lines")
                for line in fee_lines:
                    self.add_bullet(line)

            gotcha_lines = list(pack.get("gotcha_lines") or [])
            if gotcha_lines:
                self.add_section_title("Local gotchas (CRITICAL first)")
                for line in gotcha_lines:
                    self.add_bullet(line)

            clock_lines = list(pack.get("clock_lines") or [])
            if clock_lines:
                self.add_section_title("Parallel clocks - AHJ vs utility vs federal")
                for line in clock_lines:
                    self.add_bullet(line)

            if pack.get("radar_headline") or pack.get("power_headline"):
                self.add_section_title("Data-center / large-load overlay")
                if pack.get("radar_headline"):
                    self.add_bullet(str(pack["radar_headline"]))
                if pack.get("power_headline"):
                    self.add_bullet(str(pack["power_headline"]))
                for line in (pack.get("vertical_lines") or [])[:10]:
                    self.add_bullet(line)

            seq = list(pack.get("inspection_sequence") or [])
            if seq:
                self.add_section_title("Inspection / intake sequence")
                for i, step in enumerate(seq, 1):
                    self.add_bullet(str(step), bullet=f"{i}.")

            # Findings — expand markdown action plans into bullets
            findings = [f for f in (env.get("findings") or []) if isinstance(f, dict)]
            if findings:
                self.add_section_title("Key findings & contractor action plan")
                for finding in findings[:6]:
                    category = str(finding.get("category") or "Finding").replace("_", " ").title()
                    self.set_font("Helvetica", "B", 9)
                    self.set_text_color(*_PURPLE)
                    self.set_x(14)
                    self.cell(0, 6, ascii_safe(category, 80), ln=True)
                    desc = finding.get("description") or ""
                    bullets = markdown_to_bullets(desc, limit=18)
                    if bullets:
                        for b in bullets:
                            self.add_bullet(b)
                    else:
                        plain = markdown_to_plain(desc, limit=900)
                        if plain:
                            self.set_font("Helvetica", "", 9)
                            self.set_text_color(*_TEXT)
                            self.set_x(14)
                            self.multi_cell(self.epw, 4.5, plain)
                    self.ln(1)

            band = analysis_data.get("contingency_band") or pack.get("contingency") or {}
            if band.get("pct_low") is not None and band.get("pct_high") is not None:
                self.add_section_title("Bid contingency band (planning aid)")
                self.set_font("Helvetica", "B", 11)
                self.set_text_color(*_EMERALD)
                self.set_x(14)
                self.multi_cell(
                    self.epw,
                    6,
                    ascii_safe(
                        f"+{band.get('pct_low')}% to +{band.get('pct_high')}% "
                        f"(mid {band.get('pct_mid', 'n/a')}%) - not a quote",
                        160,
                    ),
                )
                self.set_text_color(*_TEXT)

            killers = [
                k for k in (analysis_data.get("margin_killers") or []) if isinstance(k, dict)
            ][:6]
            if killers:
                self.add_section_title("Top margin risk flags")
                for i, k in enumerate(killers, 1):
                    pri = str(k.get("priority") or "").upper()
                    title = ascii_safe(k.get("title"), 120)
                    self.set_font("Helvetica", "B", 9)
                    self.set_text_color(*(_RED if pri in ("CRITICAL", "HIGH") else _AMBER))
                    self.set_x(14)
                    self.multi_cell(self.epw, 5, f"{i}. [{pri}] {title}")
                    detail = markdown_to_plain(k.get("detail") or "", limit=280)
                    if detail:
                        self.set_font("Helvetica", "", 8)
                        self.set_text_color(*_MUTED)
                        self.set_x(14)
                        self.multi_cell(self.epw, 4, detail)
                    self.ln(1)

            sources = list(pack.get("source_lines") or [])
            if sources:
                self.add_section_title("Scout / citeable sources")
                for s in sources[:10]:
                    self.add_bullet(s)

            self.add_section_title("Recommended next steps")
            action_plan = env.get("action_plan") or []
            for i, action in enumerate(action_plan[:8], 1):
                self.add_bullet(markdown_to_plain(action, limit=300), bullet=f"{i}.")

            self.ln(4)
            self.add_muted_note(
                "IC Project Report - planning diligence package. Confirm all fees, codes, "
                "and filings with the local AHJ before bid or permit submittal."
            )

            if output_path is None:
                output_path = f"/tmp/research_memo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            self.output(output_path)
            logger.info("Research memo PDF generated: %s", output_path)
            return output_path
        except Exception as e:
            logger.error("Failed to generate research memo PDF: %s", e)
            raise


class PunchListPDF(RegGuardPDF):
    """Punch list as ranked cards - Critical -> Low."""

    def generate(self, analysis_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
        logger.info("Generating punch list PDF...")
        try:
            self.add_page()
            project_info = analysis_data.get("project_info", {}) or {}
            address = project_info.get("address", "Unknown")
            self.add_brand_banner(
                "Contractor Punch List",
                f"Ranked Critical -> Low  |  {address}",
            )

            punch_data = analysis_data.get("punch_list", {}) or {}
            punch_list: List[Dict[str, Any]] = [
                i for i in (punch_data.get("punch_list") or []) if isinstance(i, dict)
            ]

            self.add_section_title("Project timeline & cost")
            timeline = punch_data.get("timeline_summary", "8-12 weeks")
            cost = punch_data.get("estimated_total_cost", 0)
            try:
                cost_f = float(cost or 0)
            except (TypeError, ValueError):
                cost_f = 0.0
            self.add_info_box("Timeline", str(timeline))
            self.add_info_box("Est. cost (planning)", f"${cost_f:,.0f}")
            self.add_info_box("Action items", str(len(punch_list)))

            self.add_section_title("Detailed action items")
            priority_color = {
                "CRITICAL": _RED,
                "HIGH": (251, 146, 60),
                "MEDIUM": _AMBER,
                "LOW": _EMERALD,
            }

            for i, item in enumerate(punch_list[:45], 1):
                if self.get_y() > 250:
                    self.add_page()
                    self.set_xy(14, 16)

                priority = str(item.get("priority") or "MEDIUM").upper()
                task = markdown_to_plain(
                    item.get("task") or item.get("action") or "",
                    limit=280,
                )
                url = str(item.get("source_url") or item.get("citation_url") or "")
                cite = cite_host(
                    url,
                    label=str(
                        item.get("citation_label")
                        or item.get("source_label")
                        or ""
                    ),
                )

                # Card background
                y0 = self.get_y()
                self.set_fill_color(*_CARD)
                # Estimate height after we know task wraps — paint after measuring
                self.set_font("Helvetica", "B", 8)
                self.set_text_color(*priority_color.get(priority, _MUTED))
                self.set_x(14)
                self.cell(22, 5, priority, ln=False)
                self.set_text_color(*_MUTED)
                self.set_font("Helvetica", "", 8)
                self.cell(12, 5, f"#{i}", ln=False)
                self.set_text_color(*_EMERALD)
                self.cell(0, 5, cite, ln=True)

                self.set_font("Helvetica", "", 9)
                self.set_text_color(*_TEXT)
                self.set_x(14)
                self.multi_cell(self.epw, 4.5, task)
                if url.startswith("http"):
                    self.set_font("Helvetica", "", 7)
                    self.set_text_color(*_MUTED)
                    self.set_x(14)
                    self.multi_cell(self.epw, 3.5, ascii_safe(url, 120))
                self.ln(2)
                # Subtle rule under card
                self.set_draw_color(*_RULE)
                self.line(14, self.get_y(), self.w - 14, self.get_y())
                self.ln(2)
                _ = y0  # keep layout stable

            self.ln(2)
            self.add_muted_note(
                "Citations are planning aids. Confirm every fee and filing on the official AHJ portal."
            )

            if output_path is None:
                output_path = f"/tmp/punch_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            self.output(output_path)
            logger.info("Punch list PDF generated: %s", output_path)
            return output_path
        except Exception as e:
            logger.error("Failed to generate punch list PDF: %s", e)
            raise


class PermitPackagePDF(RegGuardPDF):
    """Fallback permit worksheet when build_permit_package_pdf is unavailable."""

    def generate(
        self, analysis_data: Dict[str, Any], state: str, output_path: Optional[str] = None
    ) -> str:
        logger.info("Generating permit package PDF for %s...", state)
        try:
            self.add_page()
            project_info = analysis_data.get("project_info", {}) or {}
            address = project_info.get("address", "Unknown")
            self.add_brand_banner(
                f"Permit Package Worksheet - {str(state or '').upper()}",
                f"Planning intake for: {address}",
            )

            self.add_section_title("Project information (pre-filled)")
            self.add_info_box("Address", str(address))
            self.add_info_box("City", str(project_info.get("city") or ""))
            self.add_info_box("State", str(state))
            self.add_info_box("ZIP", str(project_info.get("zip") or ""))
            self.add_info_box("Project type", str(project_info.get("type") or "commercial"))

            self.add_section_title("AHJ checklist")
            for line in (
                "Confirm application type on the official building portal",
                "Pull live fee schedule before payment",
                "Upload single-line diagrams / load calcs if required",
                "Treat utility interconnection as a parallel clock (if large-load)",
            ):
                self.add_bullet(line)

            self.add_section_title("Submission instructions")
            for instruction in (
                "1. Review all pre-filled information for accuracy",
                "2. Confirm fees and trade license requirements with the AHJ",
                "3. Attach drawings and cut sheets the jurisdiction requests",
                "4. File on the official AHJ portal - RegGuard does not e-file",
            ):
                self.add_bullet(instruction, bullet="")

            self.add_muted_note(
                "This is a planning worksheet, not an official permit application."
            )

            if output_path is None:
                output_path = (
                    f"/tmp/permit_package_{state}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                )
            self.output(output_path)
            logger.info("Permit package PDF generated: %s", output_path)
            return output_path
        except Exception as e:
            logger.error("Failed to generate permit package PDF: %s", e)
            raise


async def generate_all_pdfs(analysis_data: Dict[str, Any]) -> Dict[str, str]:
    """Generate all three PDFs; return paths."""
    paths: Dict[str, str] = {}
    memo = ResearchMemoPDF()
    paths["research_memo"] = memo.generate(analysis_data)
    punch = PunchListPDF()
    paths["punch_list"] = punch.generate(analysis_data)
    state = str((analysis_data.get("project_info") or {}).get("state") or "TX")
    permit = PermitPackagePDF()
    paths["permits"] = permit.generate(analysis_data, state=state)
    return paths
