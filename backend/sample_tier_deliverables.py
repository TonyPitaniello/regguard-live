"""
SAMPLE multi-tier deliverables for Pricing / Sample Report.

One Fort Worth DC-adjacent site, four honest tiers:
  Free → Estimator/Permit Runner → Contractor Pro → IC Diligence Bundle

Artifacts are generated from the same fixture using production PDF/Excel/ZIP builders.
"""

from __future__ import annotations

import io
import logging
import zipfile
from typing import Dict, Tuple

from fpdf import FPDF

from sample_dc_fixture import SAMPLE_SITE_LINE, analysis_for_tier

logger = logging.getLogger(__name__)

BG = (15, 23, 42)
EMERALD = (16, 185, 129)
EMERALD_SOFT = (52, 211, 153)
AMBER = (245, 158, 11)
WHITE = (248, 250, 252)
MUTED = (148, 163, 184)
DIM = (100, 116, 139)
CARD = (30, 41, 59)

PAGE_W = 215.9
PAGE_H = 279.4
MARGIN = 14
CONTENT_W = PAGE_W - (MARGIN * 2)


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


class _LadderPDF(FPDF):
    def header(self) -> None:
        self.set_fill_color(*BG)
        self.rect(0, 0, PAGE_W, PAGE_H, "F")

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 6.5)
        self.set_text_color(*DIM)
        self.multi_cell(
            0,
            3,
            _ascii(
                "LABELED SAMPLE — Fort Worth DC-adjacent screening pattern. "
                "Planning aid only — not a quote, sealed bid, interconnect study, or AHJ filing. "
                f"Page {self.page_no()}"
            ),
            align="C",
        )


def _section(pdf: _LadderPDF, title: str) -> None:
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*EMERALD_SOFT)
    pdf.cell(CONTENT_W, 7, _ascii(title), ln=1)
    pdf.ln(1)


def _body(pdf: _LadderPDF, text: str, *, bold: bool = False, size: int = 9) -> None:
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B" if bold else "", size)
    pdf.set_text_color(*WHITE if bold else MUTED)
    pdf.multi_cell(CONTENT_W, 4.2, _ascii(text))


def _bullet(pdf: _LadderPDF, text: str) -> None:
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*WHITE)
    pdf.multi_cell(CONTENT_W, 4.2, _ascii(f"- {text}"))


def generate_tier_ladder_pdf_bytes() -> bytes:
    """Multi-page SAMPLE: what you get at Free / $79 / $149 / $1,500 on the same site."""
    pdf = _LadderPDF(format="Letter", unit="mm")
    pdf.set_auto_page_break(auto=True, margin=16)

    # Cover
    pdf.add_page()
    pdf.set_fill_color(*EMERALD)
    pdf.rect(0, 0, PAGE_W, 3.2, "F")
    pdf.set_xy(MARGIN, 16)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*AMBER)
    pdf.cell(CONTENT_W, 5, "LABELED SAMPLE  |  SAME SITE AT EVERY TIER", ln=1)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*WHITE)
    pdf.multi_cell(CONTENT_W, 8, _ascii("Reg Guard — what you get by tier"))
    pdf.ln(2)
    _body(pdf, SAMPLE_SITE_LINE, bold=True, size=12)
    _body(
        pdf,
        "Fort Worth large-load / data-center-adjacent parcel. AHJ cites from the live "
        "Fort Worth Development Services pack (portal, Accela, Master Fee Schedule). "
        "This SAMPLE shows Free vs Estimator/Permit Runner vs Contractor Pro vs IC Diligence Bundle.",
    )
    pdf.ln(3)
    _section(pdf, "Stamp (SAMPLE)")
    _body(pdf, "REGGUARD STAMP: HOLD", bold=True, size=14)
    _body(
        pdf,
        "HOLD means elevate pre-bid risk on parallel clocks (AHJ vs interconnect vs water) — "
        "not that the site is invalid. Contingency band: +21% to +26% (mid 23%).",
    )
    pdf.ln(3)
    _section(pdf, "Download the real SAMPLE files")
    for line in (
        "Free preview PDF — soft-locked Bid Risk Receipt structure",
        "Estimator / Permit Runner PDF — full forwardable Bid Risk Receipt + unlocked punch",
        "Contractor Pro ZIP — Receipt + fee/punch CSV + city pack PDF",
        "IC Diligence Bundle ZIP — memo + boardroom PDF + counsel DOCX + Excel workbooks (+ optional CSVs)",
    ):
        _bullet(pdf, line)
    pdf.ln(2)
    _body(
        pdf,
        "Pricing promises these exact artifacts. Re-run any live address with the matching plan "
        "to get a current pack — SAMPLE cites can age.",
        bold=True,
    )

    # Free
    pdf.add_page()
    _section(pdf, "01  FREE LOOKUPS — $0")
    _body(pdf, "Lead magnet. Soft-locked preview of the Bid Risk Receipt structure.", bold=True)
    pdf.ln(1)
    for line in (
        "Site lookup on a US address (DFW / Austin strongest citeable coverage)",
        "Top punch-list actions (soft-locked preview — top ~5 lines)",
        "Source or Unverified on every visible line",
        "Forward (SMS / email / copy) to unlock the rest of the free punch list",
        "Text or email results",
        "NOT included: full Receipt PDF habit desk, fee/punch CSV, city pack, counsel ZIP",
    ):
        _bullet(pdf, line)
    pdf.ln(2)
    _body(
        pdf,
        "SAMPLE Free on this site: you see HOLD + contingency + first 5 punch lines "
        "(fee schedule pull, ERCOT parallel clock, Accela type, stormwater, plan-review deposit). "
        "Remaining punch stays locked until forward or upgrade.",
    )

    # Partner
    pdf.add_page()
    _section(pdf, "02  ESTIMATOR / PERMIT RUNNER — $79/mo")
    _body(pdf, "Client-site screening habit. Full forwardable Bid Risk Receipt.", bold=True)
    pdf.ln(1)
    for line in (
        "Full Bid Risk Receipt PDF — forward to GC / owner / client",
        "Unlocked punch list (owner · due window · Source or Unverified)",
        "Saved Jobs + weekly email reminders for client pipeline",
        "In-app city pack slice for beachhead AHJs",
        "More monthly lookups than Free",
        "NOT included: fee/punch CSV, full city pack PDF, bid packet, deep scout every lookup, IC ZIP",
    ):
        _bullet(pdf, line)
    pdf.ln(2)
    _body(
        pdf,
        "SAMPLE Partner file: full 1-page HOLD stamp for Chapin / Fort Worth with AHJ links, "
        "parallel clocks, contingency screenshot band, top risk flags, and unlocked punch.",
    )

    # Pro
    pdf.add_page()
    _section(pdf, "03  CONTRACTOR PRO — $149/mo")
    _body(pdf, "Your bid-week desk. Everything in Estimator / Permit Runner, plus Pro exports.", bold=True)
    pdf.ln(1)
    for line in (
        "Everything in Estimator / Permit Runner",
        "Deep scout / paid local confirm on lookups",
        "Fee / punch CSV — trade · owner · due window · exhibit_id · source_url (paste into Excel/Sheets)",
        "Full city pack PDF + bid sheet PDF + bid packet",
        "Day-7 re-check habit for live bids",
        "NOT included: counsel DOCX, evidence binder Excel, IC Diligence Bundle ZIP, parallel-clocks war room as primary",
    ):
        _bullet(pdf, line)
    pdf.ln(2)
    _body(
        pdf,
        "SAMPLE Pro ZIP: Bid Risk Receipt PDF + fee/punch CSV built from the Fort Worth pack + "
        "city pack PDF for this site.",
    )

    # IC
    pdf.add_page()
    _section(pdf, "04  IC PROJECT REPORT — $1,500 one-time / site")
    _body(pdf, "Counsel-ready Diligence Bundle ZIP for one site.", bold=True)
    pdf.ln(1)
    for line in (
        "01 Decision memo PDF — 1-page HOLD/CLEAR Bid Risk Receipt stamp",
        "02 Boardroom PDF — full brief (stamp, clocks, punch, exhibits)",
        "03 Counsel DOCX — editable Word with live hyperlinks + evidence binder",
        "04 Fee / punch / evidence Excel — Cover · Fees · Punch · Evidence",
        "05 Evidence index Excel — Cover · Exhibits · Claims · Index",
        "optional/ CSV paste exports of the same schedule + evidence",
        "DC parallel clocks inside boardroom PDF + counsel DOCX (AHJ · interconnect · water/NPDES)",
        "NOT a quote, sealed bid, interconnection study, geotech, Phase I ESA, or AHJ filing",
    ):
        _bullet(pdf, line)
    pdf.ln(2)
    _body(
        pdf,
        "SAMPLE IC ZIP matches Pricing “What’s in the ZIP” exactly — same member names "
        "as a paid IC Project run on this address.",
        bold=True,
    )

    raw = pdf.output()
    return bytes(raw)

def generate_free_preview_pdf_bytes() -> bytes:
    from bid_risk_receipt_pdf import generate_bid_risk_receipt_pdf_bytes

    data = analysis_for_tier("free")
    return generate_bid_risk_receipt_pdf_bytes(
        data,
        generated_for="SAMPLE Free preview",
        share_url=data.get("share_url"),
    )


def generate_partner_receipt_pdf_bytes() -> bytes:
    from bid_risk_receipt_pdf import generate_bid_risk_receipt_pdf_bytes

    data = analysis_for_tier("partner")
    return generate_bid_risk_receipt_pdf_bytes(
        data,
        generated_for="SAMPLE Estimator / Permit Runner",
        share_url=data.get("share_url"),
    )


def generate_pro_desk_zip_bytes() -> Tuple[bytes, str]:
    """Pro SAMPLE ZIP: receipt + fee/punch CSV + city pack PDF."""
    from bid_risk_receipt_pdf import generate_bid_risk_receipt_pdf_bytes
    from bid_sheet_export import analysis_to_bid_csv
    from city_pack_pdf import generate_city_pack_pdf_bytes

    data = analysis_for_tier("pro")
    receipt = generate_bid_risk_receipt_pdf_bytes(
        data,
        generated_for="SAMPLE Contractor Pro",
        share_url=data.get("share_url"),
    )
    csv_text = analysis_to_bid_csv(data)
    try:
        city = generate_city_pack_pdf_bytes(data)
    except Exception as exc:
        logger.warning("SAMPLE city pack failed: %s", exc)
        city = b""

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("01_BID_RISK_RECEIPT_SAMPLE.pdf", receipt)
        zf.writestr("02_FEE_PUNCH_SCHEDULE_SAMPLE.csv", csv_text.encode("utf-8"))
        if city and city[:4] == b"%PDF":
            zf.writestr("03_CITY_PACK_SAMPLE.pdf", city)
        zf.writestr(
            "README_SAMPLE.txt",
            (
                "LABELED SAMPLE — Contractor Pro desk exports for "
                f"{SAMPLE_SITE_LINE}\n"
                "Includes: Bid Risk Receipt PDF, fee/punch CSV, city pack PDF (when available).\n"
                "IC Diligence Bundle (Excel + counsel DOCX + boardroom) is a separate $1,500 ZIP.\n"
            ),
        )
    return buf.getvalue(), "RegGuard_Chapin_FW_Contractor_Pro_SAMPLE.zip"


def generate_ic_bundle_sample_zip_bytes() -> Tuple[bytes, str]:
    from ic_diligence_bundle import build_ic_diligence_bundle_zip

    data = analysis_for_tier("ic")
    raw, filename = build_ic_diligence_bundle_zip(
        data,
        generated_for="SAMPLE IC Project",
        share_url=str(data.get("share_url") or ""),
    )
    # Force SAMPLE in filename for marketing clarity
    safe = "9999_CHAPIN_SCHOOL_ROAD_FORT_WORTH_TX_76126_IC_DILIGENCE_BUNDLE_SAMPLE.zip"
    return raw, safe


def generate_all_sample_artifacts() -> Dict[str, Tuple[bytes, str, str]]:
    """
    Return map of artifact_key -> (bytes, download_filename, media_type).
    """
    ladder = generate_tier_ladder_pdf_bytes()
    free = generate_free_preview_pdf_bytes()
    partner = generate_partner_receipt_pdf_bytes()
    pro_raw, pro_name = generate_pro_desk_zip_bytes()
    ic_raw, ic_name = generate_ic_bundle_sample_zip_bytes()
    return {
        "ladder": (
            ladder,
            "RegGuard_Chapin_FW_Tier_Ladder_SAMPLE.pdf",
            "application/pdf",
        ),
        "free": (
            free,
            "RegGuard_Chapin_FW_Free_Preview_SAMPLE.pdf",
            "application/pdf",
        ),
        "partner": (
            partner,
            "RegGuard_Chapin_FW_Estimator_Receipt_SAMPLE.pdf",
            "application/pdf",
        ),
        "pro": (pro_raw, pro_name, "application/zip"),
        "ic": (ic_raw, ic_name, "application/zip"),
        # Back-compat alias used by Pricing / geo landings
        "plano_alias": (
            partner,
            "RegGuard_Plano_Punch_List_SAMPLE.pdf",
            "application/pdf",
        ),
    }
