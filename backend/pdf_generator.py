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

        self.set_xy(self.l_margin, 34)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*_TEXT)
        self.multi_cell(self._content_width(), 6, ascii_safe(title, 120))
        if subtitle:
            self.set_font("Helvetica", "", 9)
            self.set_text_color(*_MUTED)
            self.set_x(self.l_margin)
            self.multi_cell(self._content_width(), 4.5, ascii_safe(subtitle, 200))
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

    def _content_width(self) -> float:
        return max(40.0, float(self.w - self.l_margin - self.r_margin))

    def write_wrapped(self, text: str, *, size: float = 9, bold: bool = False, color=_TEXT, h: float = 4.5) -> None:
        """Word-wrap inside page margins — never spill past the right edge."""
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "B" if bold else "", size)
        self.set_text_color(*color)
        # Prefer full wrap over mid-word truncation (was causing "off the page" cutoffs)
        self.multi_cell(self._content_width(), h, ascii_safe(text, 4000))

    def add_info_box(self, label: str, value: str) -> None:
        label_w = 40.0
        gap = 2.0
        y0 = self.get_y()
        self.set_xy(self.l_margin, y0)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*_MUTED)
        self.cell(label_w, 5.5, ascii_safe(label, 36) + ":", ln=0)
        self.set_xy(self.l_margin + label_w + gap, y0)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*_TEXT)
        val_w = max(30.0, self._content_width() - label_w - gap)
        self.multi_cell(val_w, 5.5, ascii_safe(value, 2000))

    def add_muted_note(self, text: str) -> None:
        self.write_wrapped(text, size=8, color=_MUTED, h=4)

    def add_bullet(self, text: str, *, bullet: str = "-") -> None:
        self.write_wrapped(f"{bullet} {text}", size=9, h=4.5)

    def add_link_line(self, label: str, url: str) -> None:
        """Clickable URL line (Helvetica cannot color-link easily — show URL + PDF link annot)."""
        u = (url or "").strip()
        if not u:
            return
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*_EMERALD)
        display = ascii_safe(f"{label}: {u}", 180)
        # Use remaining width from left margin
        x = self.get_x()
        y = self.get_y()
        w = self._content_width()
        self.cell(w, 4.5, display, link=u)
        self.ln(5)
        self.set_text_color(*_TEXT)

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
            pack = analysis_data.get("pdf_pack") if isinstance(analysis_data.get("pdf_pack"), dict) else {}
            self.add_brand_banner(
                "IC Research Memo",
                f"{address}  |  {pack.get('depth_badge') or 'Deep scout narrative + citeable fee/gotcha lines'}",
            )

            self.add_section_title("Project information")
            city = project_info.get("city", "")
            state = project_info.get("state", "")
            zip_code = project_info.get("zip", "")
            self.add_info_box("Location", f"{city}, {state} {zip_code}".strip())
            self.add_info_box("Project type", str(project_info.get("type", "commercial")))
            self.add_info_box("Analysis date", datetime.now().strftime("%B %d, %Y"))
            if pack.get("depth_badge"):
                self.add_info_box("Depth", str(pack.get("depth_badge")))
            if pack.get("ultralocal"):
                self.add_info_box("Locality", "Local + ultralocal scout enabled")

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

            punch_lines = list(pack.get("punch_lines") or [])
            if punch_lines:
                self.add_section_title("Punch list highlights (see Punch List PDF for full)")
                for line in punch_lines[:16]:
                    self.add_bullet(line)

            plan_lines = list(pack.get("plan_lines") or [])
            if plan_lines:
                self.add_section_title("Deep research action plan (excerpt)")
                for line in plan_lines[:20]:
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
                            self.write_wrapped(plain, size=9, h=4.5)
                    self.ln(1)

            band = analysis_data.get("contingency_band") or pack.get("contingency") or {}
            if band.get("pct_low") is not None and band.get("pct_high") is not None:
                self.add_section_title("Bid contingency band (planning aid)")
                self.write_wrapped(
                    f"+{band.get('pct_low')}% to +{band.get('pct_high')}% "
                    f"(mid {band.get('pct_mid', 'n/a')}%) - not a quote",
                    size=11,
                    bold=True,
                    color=_EMERALD,
                    h=6,
                )
                self.set_text_color(*_TEXT)

            killers = [
                k for k in (analysis_data.get("margin_killers") or []) if isinstance(k, dict)
            ][:6]
            if killers:
                self.add_section_title("Top margin risk flags")
                for i, k in enumerate(killers, 1):
                    pri = str(k.get("priority") or "").upper()
                    title = str(k.get("title") or "")
                    self.write_wrapped(
                        f"{i}. [{pri}] {title}",
                        size=9,
                        bold=True,
                        color=(_RED if pri in ("CRITICAL", "HIGH") else _AMBER),
                        h=5,
                    )
                    detail = markdown_to_plain(k.get("detail") or "", limit=800)
                    if detail:
                        self.write_wrapped(detail, size=8, color=_MUTED, h=4)
                    url = (k.get("source_url") or "").strip()
                    if url:
                        self.add_link_line("Source", url)
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
    """IC Permit Package — filing worksheet (distinct from Research Memo narrative)."""

    def generate(
        self, analysis_data: Dict[str, Any], state: str, output_path: Optional[str] = None
    ) -> str:
        logger.info("Generating permit package PDF for %s...", state)
        try:
            self.add_page()
            project_info = analysis_data.get("project_info", {}) or {}
            address = project_info.get("address", "Unknown")
            st = str(state or project_info.get("state") or "TX").upper()
            pack = analysis_data.get("pdf_pack") if isinstance(analysis_data.get("pdf_pack"), dict) else {}
            ahj = analysis_data.get("ahj_card") if isinstance(analysis_data.get("ahj_card"), dict) else {}
            self.add_brand_banner(
                f"IC Permit Package — {st} AHJ worksheet",
                f"Filing checklist for: {address} (not the Research Memo)",
            )

            self.add_section_title("Job site (pre-filled for AHJ intake)")
            self.add_info_box("Address", str(address))
            self.add_info_box("City", str(project_info.get("city") or ""))
            self.add_info_box("State", st)
            self.add_info_box("ZIP", str(project_info.get("zip") or ""))
            self.add_info_box("Project type", str(project_info.get("type") or "commercial"))
            self.add_info_box("Primary trade", "Confirm with AHJ (GC / electrical / mechanical)")

            self.add_section_title("Authority having jurisdiction")
            ahj_name = pack.get("ahj_name") or ahj.get("name") or f"{project_info.get('city') or ''}, {st}".strip(", ")
            self.add_info_box("AHJ", str(ahj_name))
            portal = (pack.get("portal_url") or ahj.get("portal_url") or "").strip()
            fees_u = (pack.get("fees_url") or ahj.get("fees_url") or "").strip()
            if portal:
                self.add_link_line("Building portal", portal)
            if fees_u:
                self.add_link_line("Fee schedule", fees_u)
            if not portal and not fees_u:
                self.add_bullet("Look up the city/county building portal for this ZIP before filing.")

            fee_lines = list(pack.get("fee_lines") or [])
            self.add_section_title("Permit fee planning lines (confirm on schedule)")
            if fee_lines:
                for line in fee_lines[:12]:
                    self.add_bullet(str(line))
            else:
                self.add_bullet("No citeable fee lines yet — pull the live AHJ fee schedule before payment.")

            fee_card = analysis_data.get("fee_card") if isinstance(analysis_data.get("fee_card"), dict) else {}
            fees = [f for f in (fee_card.get("fees") or []) if isinstance(f, dict)]
            if fees:
                self.add_section_title("Fee card (planning USD)")
                for f in fees[:10]:
                    label = f.get("label") or "Fee"
                    amt = f.get("amount_usd")
                    amt_s = f"${amt:,.0f}" if isinstance(amt, (int, float)) else "confirm on schedule"
                    self.add_bullet(f"{label}: {amt_s}")
                    if (f.get("source_url") or "").strip():
                        self.add_link_line("Source", str(f.get("source_url")))

            self.add_section_title("AHJ filing checklist")
            for line in (
                "Confirm application type on the official building portal",
                "Pull live fee schedule before payment — Reg Guard figures are planning only",
                "Upload single-line diagrams / load calcs if required by trade",
                "Confirm contractor registration / license before e-plan upload",
                "Treat utility interconnection as a parallel clock (large-load / DC)",
            ):
                self.add_bullet(line)

            seq = list(pack.get("inspection_sequence") or [])
            if seq:
                self.add_section_title("Inspection / intake sequence")
                for i, step in enumerate(seq[:10], 1):
                    self.add_bullet(str(step), bullet=f"{i}.")

            self.add_section_title("How to file (Reg Guard does not e-file)")
            for instruction in (
                "Review all pre-filled information for accuracy against the survey/plans",
                "Confirm fees and trade license requirements with the AHJ clerk or portal",
                "Attach drawings and cut sheets the jurisdiction requests",
                "File and pay only on the official AHJ portal",
            ):
                self.add_bullet(instruction)

            self.add_muted_note(
                "IC Permit Package worksheet — not an official permit application and not the Research Memo. "
                "Confirm every fee and form with the AHJ before bid or submittal."
            )

            if output_path is None:
                output_path = (
                    f"/tmp/permit_package_{st}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
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
