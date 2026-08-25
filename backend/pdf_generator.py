"""
PDF Generator: Professional branded PDFs for RegGuard reports
Generates:
1. Research Memo PDF (environmental findings)
2. Punch List PDF (formatted action items)
3. Permit Package PDFs (state-specific pre-filled)
"""

from fpdf import FPDF
from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)


class RegGuardPDF(FPDF):
    """Base PDF class with RegGuard branding"""
    
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.title = ""
        self.company_name = "RegGuard"
        self.company_tagline = "Site Diligence Intelligence"
        
        # Branding colors
        self.color_primary = (99, 102, 241)  # Indigo
        self.color_secondary = (139, 92, 246)  # Purple
        self.color_accent = (34, 197, 94)  # Green
        self.color_dark = (30, 30, 30)  # Dark gray
        self.color_light = (249, 250, 251)  # Light gray
    
    def add_header(self, title: str, subtitle: Optional[str] = None):
        """Add professional header with branding"""
        # Header background
        self.set_fill_color(*self.color_primary)
        self.rect(0, 0, 210, 40, 'F')
        
        # Company name
        self.set_font("Helvetica", "B", 24)
        self.set_text_color(255, 255, 255)
        self.set_xy(15, 8)
        self.cell(0, 8, self.company_name, ln=True)
        
        # Tagline
        self.set_font("Helvetica", "I", 10)
        self.set_text_color(200, 200, 200)
        self.set_xy(15, 18)
        self.cell(0, 5, self.company_tagline)
        
        # Title
        if title:
            self.set_font("Helvetica", "B", 16)
            self.set_text_color(*self.color_dark)
            self.set_xy(15, 48)
            self.cell(0, 10, title, ln=True)
        
        # Subtitle
        if subtitle:
            self.set_font("Helvetica", "", 11)
            self.set_text_color(100, 100, 100)
            self.set_xy(15, 60)
            self.multi_cell(180, 5, subtitle)
        
        # Line separator
        self.set_draw_color(*self.color_secondary)
        self.line(15, self.get_y() + 5, 195, self.get_y() + 5)
        self.ln(10)
    
    def add_footer(self):
        """Add professional footer"""
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(150, 150, 150)
        self.set_y(-20)
        
        # Page number
        self.set_x(15)
        page_text = f"Page {self.page_no()}"
        self.cell(0, 10, page_text, align="L")
        
        # Generated date
        date_text = f"Generated: {datetime.now().strftime('%B %d, %Y')}"
        self.set_x(95)
        self.cell(0, 10, date_text, align="C")
        
        # RegGuard footer
        self.set_x(140)
        self.cell(50, 10, "(c) 2026 RegGuard", align="R")
    
    def add_section_title(self, title: str):
        """Add section title with styling"""
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*self.color_primary)
        self.set_xy(15, self.get_y())
        self.cell(0, 10, title, ln=True)
        
        # Underline
        self.set_draw_color(*self.color_primary)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(5)
    
    def add_info_box(self, label: str, value: str):
        """Add info box with label and value"""
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(50, 7, label + ":", ln=False)
        
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*self.color_dark)
        self.cell(0, 7, value, ln=True)


class ResearchMemoPDF(RegGuardPDF):
    """Research Memo PDF: Environmental findings summary"""
    
    def generate(self, analysis_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """Generate research memo PDF"""
        logger.info("🔵 Generating research memo PDF...")
        
        try:
            self.add_page()
            # Do NOT call add_footer() before content — that paints at y=-20 on an
            # empty page and commonly yields a blank first page in viewers.

            # Header
            project_info = analysis_data.get("project_info", {})
            address = project_info.get("address", "Unknown")
            self.add_header(
                "Site Diligence Research Memo",
                f"Location: {address}"
            )
            
            # Project info section
            self.add_section_title("PROJECT INFORMATION")
            city = project_info.get("city", "")
            state = project_info.get("state", "")
            zip_code = project_info.get("zip", "")
            
            self.add_info_box("Location", f"{city}, {state} {zip_code}")
            self.add_info_box("Project Type", project_info.get("type", "Data Center"))
            self.add_info_box("Analysis Date", datetime.now().strftime("%B %d, %Y"))
            self.ln(5)
            
            # Environmental summary
            self.add_section_title("ENVIRONMENTAL ASSESSMENT")
            env = analysis_data.get("environmental_screening", {})
            risk_level = env.get("risk_level", "UNKNOWN")
            
            self.set_font("Helvetica", "B", 11)
            color_map = {
                "LOW": (34, 197, 94),
                "MEDIUM": (234, 179, 8),
                "HIGH": (239, 68, 68),
                "CRITICAL": (220, 38, 38),
            }
            self.set_text_color(*color_map.get(risk_level, (100, 100, 100)))
            self.cell(0, 8, f"Overall Risk Level: {risk_level}", ln=True)
            self.ln(3)
            
            # Findings
            findings = env.get("findings", [])
            for finding in findings[:8]:  # Top findings (includes contractor action plan)
                self.set_font("Helvetica", "B", 10)
                self.set_text_color(*self.color_primary)
                category = finding.get("category", "").replace("_", " ").title()
                self.cell(0, 6, f"- {category}", ln=True)
                
                self.set_font("Helvetica", "", 9)
                self.set_text_color(50, 50, 50)
                desc = finding.get("description", "")
                self.multi_cell(170, 4, desc)
                
                self.ln(2)

            # Contingency band (parity with app Bid-time arbitrage)
            band = analysis_data.get("contingency_band") or {}
            if band.get("pct_low") is not None and band.get("pct_high") is not None:
                self.add_section_title("BID CONTINGENCY BAND (PLANNING AID)")
                self.set_font("Helvetica", "B", 12)
                self.set_text_color(*self.color_accent)
                self.multi_cell(
                    180,
                    6,
                    f"+{band.get('pct_low')}% to +{band.get('pct_high')}% "
                    f"(mid {band.get('pct_mid', 'n/a')}%) - not a quote",
                )
                self.ln(2)

            killers = [
                k for k in (analysis_data.get("margin_killers") or []) if isinstance(k, dict)
            ][:5]
            if killers:
                self.add_section_title("TOP MARGIN RISK FLAGS")
                for i, k in enumerate(killers, 1):
                    self.set_font("Helvetica", "B", 9)
                    self.set_text_color(*self.color_dark)
                    pri = str(k.get("priority") or "").upper()
                    title = str(k.get("title") or "")[:100]
                    self.multi_cell(180, 5, f"{i}. [{pri}] {title}")
                    detail = str(k.get("detail") or "").strip()
                    if detail:
                        self.set_font("Helvetica", "", 8)
                        self.set_text_color(80, 80, 80)
                        self.multi_cell(180, 4, detail[:220])
                    self.ln(1)
            
            # Action items summary
            self.add_section_title("RECOMMENDED NEXT STEPS")
            self.set_font("Helvetica", "", 10)
            self.set_text_color(50, 50, 50)
            
            action_plan = env.get("action_plan", [])[:5]  # Top 5 actions
            for i, action in enumerate(action_plan, 1):
                self.multi_cell(180, 5, f"{i}. {action}")
                self.ln(2)
            
            # Upgrade CTA (skip for paid IC Project packages)
            if not analysis_data.get("skip_upgrade_cta"):
                self.ln(10)
                self.set_fill_color(*self.color_accent)
                self.set_text_color(255, 255, 255)
                self.set_font("Helvetica", "B", 11)
                self.multi_cell(
                    180,
                    8,
                    "NEXT: Contractor Pro ($149/mo) or IC Project Report ($1,500) - confirm fees with the AHJ before bidding.",
                    align="C",
                    border=1,
                    fill=True
                )
            else:
                self.ln(8)
                self.set_font("Helvetica", "I", 9)
                self.set_text_color(100, 100, 100)
                self.multi_cell(
                    180,
                    5,
                    "IC Project Report - planning diligence package. Confirm all fees, codes, and filings with the local AHJ before bid or permit submittal.",
                )
            
            # Generate file
            if output_path is None:
                output_path = f"/tmp/research_memo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            self.output(output_path)
            logger.info(f"✅ Research memo PDF generated: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Failed to generate research memo PDF: {e}")
            raise


class PunchListPDF(RegGuardPDF):
    """Punch List PDF: Formatted action items table"""
    
    def generate(self, analysis_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """Generate punch list PDF"""
        logger.info("🔵 Generating punch list PDF...")
        
        try:
            self.add_page()
            # Header first — avoid blank page from footer-before-content
            project_info = analysis_data.get("project_info", {})
            address = project_info.get("address", "Unknown")
            self.add_header(
                "CONTRACTOR PUNCH LIST (Critical -> Low)",
                f"Ranked action items for: {address}"
            )
            
            # Summary stats
            self.add_section_title("PROJECT TIMELINE & COST")
            punch_data = analysis_data.get("punch_list", {})
            
            self.set_font("Helvetica", "", 10)
            self.set_text_color(50, 50, 50)
            
            timeline = punch_data.get("timeline_summary", "8-12 weeks")
            cost = punch_data.get("estimated_total_cost", 50000)
            item_count = len(punch_data.get("punch_list", []))
            
            self.cell(50, 7, f"Timeline: {timeline}")
            try:
                cost_f = float(cost or 0)
            except (TypeError, ValueError):
                cost_f = 0.0
            self.cell(0, 7, f"Est. Cost: ${cost_f:,.0f}", ln=True)
            self.cell(50, 7, f"Action Items: {item_count}")
            self.cell(0, 7, "Sorted Critical -> High -> Medium -> Low", ln=True)
            self.ln(5)
            
            # Punch list table
            self.add_section_title("DETAILED ACTION ITEMS")
            
            # Table header
            self.set_font("Helvetica", "B", 9)
            self.set_fill_color(*self.color_primary)
            self.set_text_color(255, 255, 255)
            self.cell(10, 8, "#")
            self.cell(95, 8, "Action Item")
            self.cell(28, 8, "Priority")
            self.cell(28, 8, "Citation")
            self.ln()
            
            # Table rows
            punch_list = punch_data.get("punch_list", [])
            for i, item in enumerate(punch_list[:40], 1):
                if self.get_y() > 250:
                    self.add_page()
                    self.add_footer()
                
                priority = str(item.get("priority", "MEDIUM")).upper()
                priority_color = {
                    "CRITICAL": (220, 38, 38),
                    "HIGH": (239, 68, 68),
                    "MEDIUM": (234, 179, 8),
                    "LOW": (34, 197, 94),
                }
                
                self.set_font("Helvetica", "", 8)
                self.set_text_color(*priority_color.get(priority, (100, 100, 100)))
                
                y0 = self.get_y()
                self.cell(10, 7, str(i))
                
                self.set_text_color(50, 50, 50)
                task = str(item.get("task", "") or "")[:120]
                # Use multi_cell for task; then place priority/citation on same row start
                x_task = self.get_x()
                self.multi_cell(95, 4.5, task)
                y1 = self.get_y()
                self.set_xy(15 + 10 + 95, y0)
                self.set_text_color(*priority_color.get(priority, (100, 100, 100)))
                self.cell(28, 7, priority)
                cite = str(item.get("citation_label") or item.get("source_label") or "")
                if not cite:
                    cite = "SOURCE" if item.get("verified") else "UNVERIFIED"
                self.set_text_color(80, 80, 80)
                self.cell(28, 7, cite[:12])
                self.set_y(max(y1, y0 + 7) + 1)
            
            # Generate file
            if output_path is None:
                output_path = f"/tmp/punch_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            self.output(output_path)
            logger.info(f"✅ Punch list PDF generated: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Failed to generate punch list PDF: {e}")
            raise


class PermitPackagePDF(RegGuardPDF):
    """Permit Package PDF: State-specific permit forms"""
    
    def generate(self, analysis_data: Dict[str, Any], state: str, output_path: Optional[str] = None) -> str:
        """Generate permit package PDF"""
        logger.info(f"🔵 Generating permit package PDF for {state}...")
        
        try:
            self.add_page()
            project_info = analysis_data.get("project_info", {})
            address = project_info.get("address", "Unknown")
            self.add_header(
                f"PERMIT PACKAGE: {state.upper()}",
                f"Ready-to-file permit applications for: {address}"
            )
            
            # Project info
            self.add_section_title("PROJECT INFORMATION (Pre-Filled)")
            
            self.set_font("Helvetica", "", 10)
            self.set_text_color(50, 50, 50)
            
            self.add_info_box("Address", address)
            city = project_info.get("city", "")
            self.add_info_box("City", city)
            self.add_info_box("State", state)
            self.add_info_box("ZIP", project_info.get("zip", ""))
            self.add_info_box("Project Type", project_info.get("type", "Data Center"))
            self.ln(5)
            
            # Permit requirements by state (placeholder - customize per state)
            self.add_section_title(f"{state} PERMIT REQUIREMENTS")
            
            state_permits = {
                "TX": [
                    "Electrical Permit (Local AHJ)",
                    "Environmental Permit (if applicable)",
                    "Utility Interconnection Agreement",
                    "Grounding Certificate",
                ],
                "CA": [
                    "California Building Code Compliance",
                    "Energy Commission Approval",
                    "Air Quality Permit",
                ],
                "NY": [
                    "New York State Building Permit",
                    "PSC Interconnection Agreement",
                    "Environmental Review",
                ],
            }
            
            permits = state_permits.get(state.upper(), ["Local permit application"])
            
            self.set_font("Helvetica", "", 10)
            self.set_text_color(50, 50, 50)
            
            for permit in permits:
                self.cell(10, 7, "[x]")
                self.cell(170, 7, permit, ln=True)
            
            self.ln(5)
            
            # Instructions
            self.add_section_title("SUBMISSION INSTRUCTIONS")
            
            self.set_font("Helvetica", "", 9)
            self.set_text_color(50, 50, 50)
            
            instructions = [
                "1. Review all pre-filled information for accuracy",
                "2. Sign and date permit applications (see signature section)",
                "3. Attach required supporting documents (electrical drawings, site plans, etc.)",
                "4. Submit to your local Authority Having Jurisdiction (AHJ)",
                "5. Track permit status using reference numbers provided",
                "6. Contact RegGuard support for questions about requirements",
            ]
            
            for instruction in instructions:
                self.multi_cell(180, 5, instruction)
            
            # Generate file
            if output_path is None:
                output_path = f"/tmp/permit_package_{state}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            self.output(output_path)
            logger.info(f"✅ Permit package PDF generated: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Failed to generate permit package PDF: {e}")
            raise


async def generate_all_pdfs(analysis_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate all three PDFs for a complete report
    
    Returns:
    {
        "research_memo": "/path/to/memo.pdf",
        "punch_list": "/path/to/punch_list.pdf",
        "permit_package": "/path/to/permits.pdf",
    }
    """
    logger.info("📄 Generating complete PDF package...")
    
    try:
        pdfs = {}
        
        # 1. Research memo
        memo = ResearchMemoPDF()
        pdfs["research_memo"] = memo.generate(analysis_data)
        
        # 2. Punch list
        punch = PunchListPDF()
        pdfs["punch_list"] = punch.generate(analysis_data)
        
        # 3. Permit package (default to TX, can be state-specific)
        state = analysis_data.get("project_info", {}).get("state", "TX")
        permits = PermitPackagePDF()
        pdfs["permit_package"] = permits.generate(analysis_data, state)
        
        logger.info(f"✅ Complete PDF package generated: {pdfs}")
        return pdfs
        
    except Exception as e:
        logger.error(f"❌ Failed to generate PDF package: {e}")
        raise
