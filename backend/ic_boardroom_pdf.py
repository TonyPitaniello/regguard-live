"""
IC Boardroom Diligence Package PDF — print-first Letter layout.

White paper, navy/emerald accents (not app-dark UI). Consumes compose_ic_package().
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fpdf import FPDF

logger = logging.getLogger(__name__)

NAVY = (15, 23, 42)
EMERALD = (4, 120, 87)
AMBER = (180, 83, 9)
MUTED = (100, 116, 139)
RULE = (226, 232, 240)
WHITE = (255, 255, 255)
INK = (15, 23, 42)

PAGE_W = 215.9
PAGE_H = 279.4
MARGIN = 16
CONTENT_W = PAGE_W - (MARGIN * 2)


def _ascii(text: Any) -> str:
    s = str(text or "")
    for a, b in (
        ("\u2014", "-"),
        ("\u2013", "-"),
        ("\u2018", "'"),
        ("\u2019", "'"),
        ("\u201c", '"'),
        ("\u201d", '"'),
        ("\u2022", "-"),
        ("\u2026", "..."),
        ("\u00a0", " "),
        ("\u00a9", "(c)"),
    ):
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


class BoardroomPDF(FPDF):
    def __init__(self) -> None:
        super().__init__(format="Letter", unit="mm")
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self._doc_subtitle = "IC Project Diligence Package"

    def header(self) -> None:  # type: ignore[override]
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*MUTED)
        self.set_xy(MARGIN, 8)
        self.cell(CONTENT_W * 0.55, 5, _ascii("RegGuard · IC Diligence Package"), align="L")
        self.cell(CONTENT_W * 0.45, 5, _ascii(self._doc_subtitle)[:60], align="R")
        self.set_draw_color(*RULE)
        self.line(MARGIN, 14, PAGE_W - MARGIN, 14)
        self.set_y(18)

    def footer(self) -> None:  # type: ignore[override]
        self.set_y(-14)
        self.set_draw_color(*RULE)
        self.line(MARGIN, self.get_y(), PAGE_W - MARGIN, self.get_y())
        self.set_y(-11)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MUTED)
        self.cell(
            CONTENT_W,
            5,
            _ascii(
                f"Planning aid only - confirm with AHJ  |  Page {self.page_no()}  |  (c) RegGuard"
            ),
            align="C",
        )


def _need_space(pdf: BoardroomPDF, h: float) -> None:
    if pdf.get_y() + h > PAGE_H - 22:
        pdf.add_page()


def _h1(pdf: BoardroomPDF, text: str) -> None:
    _need_space(pdf, 14)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*NAVY)
    pdf.multi_cell(CONTENT_W, 8, _ascii(text))
    pdf.ln(2)


def _h2(pdf: BoardroomPDF, text: str) -> None:
    _need_space(pdf, 12)
    pdf.set_x(MARGIN)
    pdf.set_fill_color(*EMERALD)
    y = pdf.get_y()
    pdf.rect(MARGIN, y + 1.5, 2.0, 5.5, "F")
    pdf.set_xy(MARGIN + 4, y)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*NAVY)
    pdf.cell(CONTENT_W - 4, 8, _ascii(text), ln=1)
    pdf.ln(1)


def _body(pdf: BoardroomPDF, text: str, *, size: int = 10, color: Tuple[int, int, int] = INK) -> None:
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "", size)
    pdf.set_text_color(*color)
    pdf.multi_cell(CONTENT_W, 5, _ascii(text))


def _muted(pdf: BoardroomPDF, text: str, size: int = 9) -> None:
    _body(pdf, text, size=size, color=MUTED)


def _bullet(pdf: BoardroomPDF, text: str, *, indent: float = 4) -> None:
    _need_space(pdf, 8)
    pdf.set_x(MARGIN + indent)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*INK)
    pdf.multi_cell(CONTENT_W - indent, 4.5, _ascii(f"- {text}"))


def _card(pdf: BoardroomPDF, title: str, lines: List[str], *, accent: Tuple[int, int, int] = EMERALD) -> None:
    _need_space(pdf, 7 + len(lines) * 5 + 6)
    y0 = pdf.get_y()
    pdf.set_xy(MARGIN, y0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*accent)
    pdf.multi_cell(CONTENT_W, 5, _ascii(title))
    for line in lines:
        if not line:
            continue
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*INK)
        pdf.multi_cell(CONTENT_W, 4.5, _ascii(line))
    pdf.ln(2)
    pdf.set_draw_color(*accent)
    pdf.set_line_width(0.4)
    pdf.line(MARGIN, y0 - 1, MARGIN, pdf.get_y() - 1)
    pdf.set_line_width(0.2)


def render_boardroom_pdf(package: Dict[str, Any], output_path: str) -> str:
    pdf = BoardroomPDF()
    cover = package.get("cover") or {}
    pdf._doc_subtitle = _ascii(cover.get("site") or "Site diligence")[:70]

    pdf.add_page()
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, PAGE_W, 42, "F")
    pdf.set_fill_color(*EMERALD)
    pdf.rect(0, 42, PAGE_W, 1.5, "F")
    pdf.set_xy(MARGIN, 14)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*WHITE)
    pdf.cell(CONTENT_W, 10, _ascii("RegGuard"), ln=1)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(CONTENT_W, 6, _ascii("IC Project Diligence Package"), ln=1)

    pdf.set_y(52)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*NAVY)
    pdf.multi_cell(CONTENT_W, 9, _ascii(cover.get("product") or "IC Diligence Package"))
    pdf.ln(2)
    _muted(pdf, cover.get("price_positioning") or "$1,500 IC Project Report")
    pdf.ln(4)
    _h2(pdf, "Engagement")
    _body(pdf, f"Site: {cover.get('site') or '-'}", size=11)
    _body(pdf, f"AHJ: {cover.get('ahj_name') or '-'}")
    if cover.get("depth_badge"):
        _body(pdf, f"Depth: {cover.get('depth_badge')}")
    if cover.get("coverage_badge"):
        _body(pdf, f"Coverage: {cover.get('coverage_badge')}")
    if package.get("generated_for"):
        _body(pdf, f"Prepared for: {package.get('generated_for')}")
    _body(pdf, f"Generated: {package.get('generated_at') or '-'}")
    if cover.get("research_id"):
        _muted(pdf, f"Research id: {cover.get('research_id')}")
    pdf.ln(4)
    _muted(
        pdf,
        "This bound package is the primary IC Project deliverable. "
        "Supporting memo / punch / permit worksheets may be exported separately.",
    )
    pdf.ln(6)
    _h2(pdf, "Contents")
    for i, title in enumerate(
        [
            "Executive summary",
            "Bid Risk Receipt",
            "Site findings (AHJ, fees, gotchas, clocks)",
            "Ranked punch list",
            "Action plan highlights",
            "Source appendix",
        ],
        start=1,
    ):
        _bullet(pdf, f"{i}. {title}")

    pdf.add_page()
    ex = package.get("executive_summary") or {}
    stamp = ex.get("stamp") or {}
    _h1(pdf, "1. Executive summary")
    _body(pdf, ex.get("headline") or "What matters before you bid", size=12)
    pdf.ln(2)

    display = stamp.get("display") or stamp.get("grade") or "-"
    _card(
        pdf,
        stamp.get("label") or f"REGGUARD STAMP: {display}",
        [
            stamp.get("plain") or stamp.get("headline") or "",
            "CLEAR = no Critical killers on current pack · CAUTION = material risk · "
            "HOLD = resolve drivers before treating the bid as clear.",
            f"Valid until: {stamp.get('valid_until') or '-'}"
            + (f"  |  fp {stamp.get('fingerprint')}" if stamp.get("fingerprint") else ""),
        ],
        accent=AMBER if display in ("HOLD", "CAUTION", "FAIL") else EMERALD,
    )
    for d in stamp.get("drivers") or []:
        _bullet(
            pdf,
            f"[{d.get('severity')}] {d.get('label')}"
            + (f" - {d.get('detail')}" if d.get("detail") else ""),
        )

    band = ex.get("contingency")
    if isinstance(band, dict):
        pdf.ln(2)
        _h2(pdf, "Suggested bid contingency cushion")
        _body(
            pdf,
            f"+{band.get('pct_low')}% - +{band.get('pct_high')}%  (mid {band.get('pct_mid')}%)",
            size=14,
        )
        _body(pdf, band.get("plain") or "")
        pdf.ln(1)
        _muted(pdf, "What pushes this band:")
        for drv in band.get("drivers") or []:
            _bullet(pdf, drv)

    if ex.get("env_risk"):
        pdf.ln(1)
        _body(pdf, f"Environmental screening risk: {ex.get('env_risk')}")

    pdf.ln(2)
    _h2(pdf, "Top risk flags")
    for k in ex.get("top_risks") or []:
        _bullet(
            pdf,
            f"[{k.get('priority')}] {k.get('title')}"
            + (f" - {k.get('detail')}" if k.get("detail") else ""),
        )
    if not (ex.get("top_risks") or []):
        _muted(pdf, "No high-priority margin killers in this package payload.")

    pdf.ln(1)
    _h2(pdf, "Local gotchas")
    for g in ex.get("local_gotchas") or []:
        _bullet(pdf, f"[{g.get('priority')}] {g.get('title')}")
    if not (ex.get("local_gotchas") or []):
        _muted(pdf, "No local gotcha items listed.")

    pdf.ln(1)
    _h2(pdf, "Next actions")
    for a in ex.get("next_actions") or []:
        _bullet(pdf, a)

    pdf.add_page()
    receipt = package.get("bid_risk_receipt") or {}
    _h1(pdf, "2. Bid Risk Receipt")
    _body(pdf, receipt.get("title") or "Forward to GC / owner", size=11)
    pdf.ln(2)
    st = receipt.get("stamp") or stamp
    _body(pdf, st.get("label") or "", size=12)
    _body(pdf, st.get("headline") or st.get("plain") or "")
    band = receipt.get("contingency") or band
    if isinstance(band, dict):
        pdf.ln(2)
        _body(
            pdf,
            f"Contingency: +{band.get('pct_low')}% - +{band.get('pct_high')}% (mid {band.get('pct_mid')}%)",
            size=13,
        )
        _muted(pdf, band.get("plain") or "")
    pdf.ln(2)
    _h2(pdf, "Three risk flags")
    for k in receipt.get("killers") or []:
        _bullet(
            pdf,
            f"[{k.get('priority')}] {k.get('title')}"
            + (f" - {k.get('detail')}" if k.get("detail") else ""),
        )
    if receipt.get("share_url"):
        pdf.ln(2)
        _muted(pdf, f"Interactive share link: {receipt.get('share_url')}")
    pdf.ln(2)
    _muted(pdf, receipt.get("disclaimer") or "")

    pdf.add_page()
    findings = package.get("site_findings") or {}
    _h1(pdf, "3. Site findings")
    ahj = findings.get("ahj") or {}
    _h2(pdf, "Authority having jurisdiction")
    _body(pdf, ahj.get("name") or cover.get("ahj_name") or "Local AHJ")
    if ahj.get("portal_url"):
        _muted(pdf, f"Portal: {ahj.get('portal_url')}")
    if ahj.get("fees_url"):
        _muted(pdf, f"Fees: {ahj.get('fees_url')}")
    if ahj.get("last_verified"):
        _muted(pdf, f"Last verified: {ahj.get('last_verified')}")
    if findings.get("coverage_note"):
        pdf.ln(1)
        _body(pdf, findings.get("coverage_note"))

    fees = findings.get("fees") or []
    if fees:
        pdf.ln(2)
        _h2(pdf, "Fee & timeline extracts (planning aids)")
        for f in fees:
            line = f.get("name") or "Fee"
            if f.get("amount"):
                line += f" - {f.get('amount')}"
            _bullet(pdf, line)
            if f.get("note"):
                _muted(pdf, f"  {f.get('note')}")

    gotchas = findings.get("gotchas") or []
    if gotchas:
        pdf.ln(2)
        _h2(pdf, "Local gotcha watchlist")
        for g in gotchas:
            _need_space(pdf, 18)
            _body(pdf, f"[{g.get('priority')}] {g.get('title')}", size=10)
            if g.get("detail"):
                _muted(pdf, g.get("detail"))
            if g.get("confirm_step"):
                _body(pdf, f"Confirm: {g.get('confirm_step')}", size=9)
            _muted(pdf, f"Citation: {g.get('source_label') or 'Unverified'}")
            pdf.ln(1)

    if findings.get("env_risk") or findings.get("env_findings"):
        _h2(pdf, "Environmental screening")
        if findings.get("env_risk"):
            _body(pdf, f"Risk level: {findings.get('env_risk')}")
        for f in findings.get("env_findings") or []:
            _bullet(pdf, f"{f.get('category')}: {f.get('description')}")

    clocks = findings.get("parallel_clocks") or []
    if clocks:
        pdf.ln(1)
        _h2(pdf, "Parallel clocks (AHJ + utility)")
        for c in clocks:
            _bullet(pdf, f"{c.get('name')}: {c.get('detail')}")

    pdf.add_page()
    punch = package.get("punch_list") or {}
    _h1(pdf, "4. Ranked punch list")
    if punch.get("timeline_summary"):
        _muted(pdf, f"Timeline summary: {punch.get('timeline_summary')}")
        pdf.ln(1)
    items = punch.get("items") or []
    if not items:
        _muted(pdf, "No punch-list items in this package payload.")
    for item in items:
        _need_space(pdf, 14)
        cost = item.get("estimated_cost")
        cost_s = f" · est ${cost:,.0f}" if isinstance(cost, (int, float)) and cost else ""
        _body(pdf, f"[{item.get('priority')}] {item.get('task')}{cost_s}", size=9)
        _muted(pdf, f"Timing: {item.get('timeline') or 'Pre-bid'} · {item.get('citation') or 'Unverified'}")

    pdf.add_page()
    _h1(pdf, "5. Action plan highlights")
    for a in package.get("action_plan_summary") or []:
        _bullet(pdf, a)
    excerpt = (package.get("action_plan_excerpt") or "").strip()
    if excerpt:
        pdf.ln(3)
        _h2(pdf, "Deep research excerpt")
        _body(pdf, excerpt[:2200], size=8)

    pdf.add_page()
    _h1(pdf, "6. Source appendix")
    _muted(
        pdf,
        "Every forwardable claim should resolve to a URL below or be treated as Unverified.",
    )
    pdf.ln(2)
    sources = package.get("sources") or []
    if not sources:
        _muted(pdf, "No http(s) sources were attached to this analysis.")
    for i, src in enumerate(sources, start=1):
        _bullet(pdf, f"{i}. {src.get('label') or 'Source'}")
        _muted(pdf, f"   {src.get('url')}")

    pdf.ln(4)
    _h2(pdf, "Disclaimers")
    for d in package.get("disclaimers") or []:
        _bullet(pdf, d)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    pdf.output(output_path)
    return output_path


def generate_ic_boardroom_pdf_bytes(
    analysis: Dict[str, Any],
    *,
    generated_for: str = "",
    share_url: str = "",
) -> bytes:
    from ic_package_composer import compose_ic_package

    package = compose_ic_package(
        analysis,
        generated_for=generated_for,
        share_url=share_url,
    )
    with tempfile.TemporaryDirectory(prefix="ic_boardroom_") as tmp:
        path = os.path.join(tmp, "RegGuard_IC_Diligence_Package.pdf")
        render_boardroom_pdf(package, path)
        raw = Path(path).read_bytes()
    if raw[:4] != b"%PDF":
        raise RuntimeError("Boardroom PDF generation failed")
    return raw
