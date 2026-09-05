"""
Reg Guard — AHJ-facing permit application worksheet (PDF).

Maps research context (address, scope, fees, trade) into a structured intake document.
Dallas-specific notices (722 Munger, minimum trade permit line) apply only when the job site
resolves to Dallas, TX from the caller-supplied address fields.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from fpdf import FPDF  # fpdf2 on PyPI — ``import fpdf`` is the supported entry point

from calculations import permit_draft_calculation_response

# Dallas Building Inspection — minimum trade permit (incl. admin); rendered via fpdf2 below.
# Kept in sync with ``frontend/src/App.tsx`` (REG_GUARD_DALLAS_MIN_TRADE_PERMIT_USD) and ``main`` digest prompts.
DALLAS_MIN_TRADE_PERMIT_USD = 167.00

# Long action-plan excerpts slow regex in ``permit_draft_calculation_response`` — cap input for the NEC snapshot only.
_CALC_SCOPE_CHAR_MAX = 8192

_MARGIN_L = 18.0
_MARGIN_T = 20.0
_MARGIN_R = 18.0
_MARGIN_B = 22.0
_BODY_LINE_H = 6.0
_SECTION_GAP = 4.0


def _trade_is_hvac_mechanical(trade: str) -> bool:
    t = (trade or "").lower()
    return "hvac" in t or "mechanical" in t


def _ascii_pdf_text(s: str) -> str:
    """fpdf core fonts are latin-1; strip/replace characters NEC strings may contain."""
    if not s:
        return ""
    t = (
        s.replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2212", "-")
        .replace("\u00b0", " deg ")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )
    return t.encode("latin-1", errors="replace").decode("latin-1")


def _location_blob(*, city: str, site_address: str, ahj_label: str, zip_code: str) -> str:
    return " ".join(
        p
        for p in [(city or "").strip(), (site_address or "").strip(), (ahj_label or "").strip(), (zip_code or "").strip()]
        if p
    ).lower()


def _is_dallas_texas(*, city: str, site_address: str, ahj_label: str, zip_code: str) -> bool:
    blob = _location_blob(city=city, site_address=site_address, ahj_label=ahj_label, zip_code=zip_code)
    if "dallas" not in blob:
        return False
    return "tx" in blob or "texas" in blob or ", dallas" in blob or "dallas," in blob


def _worksheet_header_lines(
    *, city: str, county: str, ahj_label: str, site_address: str
) -> Tuple[str, str]:
    ahj = (ahj_label or "").strip()
    c = (city or "").strip()
    if ahj:
        primary = ahj.split("—")[0].strip() or ahj
        if len(primary) > 72:
            primary = primary[:69] + "..."
        return primary, "Building permit application worksheet"
    if c:
        county_bit = f", {(county or '').strip()}" if (county or "").strip() else ""
        return f"{c}{county_bit}", "Building permit application worksheet"
    addr = (site_address or "").strip()
    if addr:
        parts = [p.strip() for p in addr.split(",") if p.strip()]
        if len(parts) >= 2:
            return parts[-2] if len(parts) >= 3 else parts[0], "Building permit application worksheet"
    return "Municipal permit application worksheet", "Reg Guard intake — verify AHJ with selected address"


def is_722_munger_ave(site_address: str) -> bool:
    """Site-specific notices for 722 Munger Ave, Dallas (Deep Ellum / downtown edge)."""
    s = (site_address or "").lower()
    if "munger" not in s:
        return False
    return bool(re.search(r"\b722\b", s))


# Match app + Research Memo / Punch List PDFs (slate-900 / emerald / purple).
_THEME_BG = (15, 23, 42)  # slate-900
_THEME_TEXT = (248, 250, 252)
_THEME_MUTED = (148, 163, 184)
_THEME_RULE = (168, 85, 247)  # purple accent
_THEME_AMBER = (245, 158, 11)
_THEME_EMERALD = (16, 185, 129)


class _DallasPermitPdf(FPDF):
    def header(self) -> None:  # type: ignore[override]
        # Paint the dark brand background across the full page (every page, incl. auto-breaks).
        self.set_fill_color(*_THEME_BG)
        self.rect(0, 0, self.w, self.h, style="F")
        self.set_text_color(*_THEME_TEXT)
        self.set_xy(self.l_margin, self.t_margin)

    def footer(self) -> None:  # type: ignore[override]
        self.set_y(-16)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*_THEME_MUTED)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        self.multi_cell(
            0,
            6,
            _ascii_pdf_text(f"Page {self.page_no()}/{{nb}} - Reg Guard permit worksheet - {ts}"),
            align="C",
        )


def _ensure_vertical_space(pdf: FPDF, needed_mm: float) -> None:
    bottom = pdf.h - _MARGIN_B
    if pdf.get_y() + needed_mm > bottom:
        pdf.add_page()


def _section_header(pdf: FPDF, title: str, *, font_size: float = 11.5) -> None:
    col_w = pdf.epw
    _ensure_vertical_space(pdf, 14)
    pdf.ln(_SECTION_GAP)
    pdf.set_font("Helvetica", "B", font_size)
    pdf.set_text_color(*_THEME_TEXT)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(col_w, 7, _ascii_pdf_text(title), align="L")
    y = pdf.get_y()
    pdf.set_draw_color(*_THEME_RULE)
    pdf.set_line_width(0.55)
    pdf.line(pdf.l_margin, y + 0.5, pdf.l_margin + col_w, y + 0.5)
    pdf.ln(3)
    pdf.set_text_color(*_THEME_TEXT)


def _body_block(pdf: FPDF, text: str, *, max_chars: int = 12_000) -> None:
    col_w = pdf.epw
    pdf.set_font("Helvetica", "", 9)
    chunk = _ascii_pdf_text((text or "").strip()[:max_chars])
    if not chunk:
        chunk = "(none provided)"
    _ensure_vertical_space(pdf, 12)
    # Reset to the left margin + force left-aligned wrapping so rows never bleed past the right edge.
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(col_w, _BODY_LINE_H, chunk, align="L")
    pdf.ln(2)


def build_permit_package_pdf(
    *,
    site_address: str,
    scope: str,
    fee_summary: str,
    trade: str,
    zip_code: str = "",
    city: str = "",
    county: str = "",
    ahj_label: str = "",
) -> bytes:
    jd = (scope or "").strip()
    jd_calc = jd if len(jd) <= _CALC_SCOPE_CHAR_MAX else jd[:_CALC_SCOPE_CHAR_MAX]
    calc: Dict[str, Any] = permit_draft_calculation_response(jd_calc)
    a220: Dict[str, Any] = calc["article_220"]
    a310: Dict[str, Any] = calc["article_310"]

    dallas_site = _is_dallas_texas(
        city=city, site_address=site_address, ahj_label=ahj_label, zip_code=zip_code
    )
    title_primary, title_sub = _worksheet_header_lines(
        city=city, county=county, ahj_label=ahj_label, site_address=site_address
    )

    from pdf_text import markdown_to_plain

    jd = markdown_to_plain(jd, limit=6000)

    pdf = _DallasPermitPdf()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=_MARGIN_B)
    pdf.set_margins(_MARGIN_L, _MARGIN_T, _MARGIN_R)
    pdf.add_page()
    col_w = pdf.epw

    # Brand strip (matches Research Memo / Punch List)
    pdf.set_fill_color(88, 28, 135)
    pdf.rect(0, 0, pdf.w, 22, style="F")
    pdf.set_fill_color(*_THEME_EMERALD)
    pdf.rect(0, 22, pdf.w, 1.2, style="F")
    pdf.set_xy(pdf.l_margin, 6)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 6, "RegGuard", ln=True)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(221, 214, 254)
    pdf.cell(0, 5, "Site Diligence Intelligence  |  IC Permit Worksheet", ln=True)
    pdf.set_xy(pdf.l_margin, 28)

    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*_THEME_TEXT)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(col_w, 7, _ascii_pdf_text(title_primary), align="L")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*_THEME_EMERALD)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(col_w, 6, _ascii_pdf_text(title_sub), align="L")
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*_THEME_MUTED)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(
        col_w,
        4.5,
        _ascii_pdf_text(
            "Reg Guard intake aligned with common municipal permit fields. "
            "Official filing, e-plan uploads, contractor registration, and payment stay on the AHJ portal."
        ),
        align="L",
    )
    pdf.ln(2)
    pdf.set_text_color(*_THEME_TEXT)

    addr = (site_address or "").strip() or "_______________________________"
    loc_bits = [x for x in [city.strip() if city else "", county.strip() if county else ""] if x]
    loc_suffix = ", ".join(loc_bits)
    zip_part = f"ZIP {zip_code.strip()}" if (zip_code or "").strip() else ""

    _section_header(pdf, "PROPERTY / JOB SITE", font_size=12)
    _body_block(pdf, f"Address: {addr}")
    line2 = " | ".join(p for p in [loc_suffix, zip_part] if p)
    if line2:
        _body_block(pdf, line2)
    elif ahj_label.strip():
        _body_block(pdf, f"Jurisdiction: {ahj_label.strip()}")

    _section_header(pdf, "DESCRIPTION OF WORK (scope)")
    _body_block(pdf, jd or "(no scope text provided)")

    _section_header(pdf, "PERMIT TYPE / PRIMARY TRADE")
    _body_block(pdf, (trade or "_________________________________________").strip())

    _section_header(pdf, "PERMIT FEES (planning figures - confirm with AHJ)")
    if dallas_site:
        fee_line = (
            f"City of Dallas minimum trade permit (Reg Guard 2026 planning sync): USD ${DALLAS_MIN_TRADE_PERMIT_USD:.2f}. "
            "Confirm line items, tiers, and surcharges on the official City of Dallas Development Services / "
            "Building Inspection fee schedule before posting payment."
        )
        _body_block(pdf, fee_line)
    else:
        _body_block(
            pdf,
            "Use the fee schedule and permit fee calculator published by the Authority Having Jurisdiction "
            "for this address. Figures in the Reg Guard action plan (below) are planning estimates only.",
        )
    if (fee_summary or "").strip():
        _body_block(pdf, fee_summary.strip())
    if dallas_site and _trade_is_hvac_mechanical(trade):
        _body_block(
            pdf,
            "HVAC / mechanical (Dallas): confirm mechanical trade permit, plan review, and IMC-related "
            "fee line items on the official City of Dallas Development Services fee schedule. Reg Guard "
            f"still anchors to the USD ${DALLAS_MIN_TRADE_PERMIT_USD:.2f} "
            "trade-permit planning floor until the AHJ itemizes mechanical adders.",
        )

    _section_header(pdf, "AUTHORITY HAVING JURISDICTION")
    ahj_display = (ahj_label or "").strip()
    if not ahj_display:
        if city.strip():
            ahj_display = f"{city.strip()} — verify current subdivision / inspection area with the local building department"
        else:
            ahj_display = "Verify Authority Having Jurisdiction using the job site address above"
    _body_block(pdf, ahj_display)

    if dallas_site and is_722_munger_ave(site_address):
        _section_header(pdf, "722 MUNGER AVE INTELLIGENCE — DALLAS, TX (REG GUARD)", font_size=11)
        pdf.set_text_color(*_THEME_AMBER)
        _body_block(
            pdf,
            "Setback alert (rear yard / BDA variance risk): A 3 ft rear setback likely fails the more typical "
            "5 ft rear-yard building line expectation for many Dallas residential-style lots (verify exact zoning "
            "district, Form District, and adopted yard tables). If the improvement does not comply, a Board of "
            "Adjustment (BDA) variance or other zoning relief may be required before CO or final release.",
        )
        _body_block(
            pdf,
            "Parking reform victory (May 2025): Dallas reforms exempt many small projects from legacy stall minima — "
            "developments with 20 dwelling units or fewer (including typical ADU scenarios) generally have no minimum "
            "off-street parking. Confirm applicability against zoning, PD overlays, and TIF/overlay conditions with "
            "Dallas Planning before omitting stalls on cover sheets.",
        )
        _body_block(
            pdf,
            "Oncor Electric Delivery — WARNING: Before any service disconnect, meter seal release, temporary service, "
            "service upgrade, or line-side work, coordinate with Oncor Electric Delivery. A Dallas building permit does "
            "not replace Oncor clearance or field scheduling.",
        )
        _body_block(
            pdf,
            "Land use / zoning clearance: Use standards, PD overlays, and neighborhood-specific walk-overs can still "
            "require administrative or Board of Adjustment relief even when building permits issue.",
        )
        pdf.set_text_color(*_THEME_TEXT)

    _section_header(pdf, "ELECTRICAL PLANNING MEMO (Reg Guard NEC snapshot)", font_size=12)
    pdf.set_font("Helvetica", "I", 8)
    _ensure_vertical_space(pdf, 10)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(col_w, 4.5, _ascii_pdf_text(str(calc.get("nec_edition_note", ""))), align="L")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9)
    _body_block(
        pdf,
        f"Total calculated VA: {a220['total_calculated_va']} | Feeder @ 240 V: {a220['feeder_amps_at_240v']} A | "
        f"Main frame (planning): {a220['main_breaker_frame_a']} A",
    )
    cond = str(a310.get("selected_conductor_display", ""))
    tab = str(a310.get("table_ref", ""))
    _body_block(pdf, f"Service conductors (planning): {cond} ({tab})")
    pdf.ln(1)
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(*_THEME_MUTED)
    _ensure_vertical_space(pdf, 16)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(col_w, 4, _ascii_pdf_text(str(calc.get("disclaimer", ""))), align="L")

    raw = pdf.output(dest="S")
    if isinstance(raw, bytearray):
        return bytes(raw)
    if isinstance(raw, bytes):
        return raw
    return str(raw).encode("latin-1", errors="replace")
