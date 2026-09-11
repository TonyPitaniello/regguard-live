"""
IC Boardroom Diligence Package PDF — print-first Letter letterhead.

Palette aligned to the Reg Guard app (midnight navy + emerald + amber alerts).
Every page titles with the site address.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

from fpdf import FPDF

# App-aligned palette (App.css / results UI)
NAVY = (10, 20, 41)  # #0a1429
NAVY_MID = (15, 29, 56)  # #0f1d38
NAVY_DEEP = (6, 12, 28)
EMERALD = (16, 185, 129)  # #10b981
EMERALD_SOFT = (209, 250, 229)  # #d1fae5
AMBER = (245, 158, 11)  # #f59e0b
AMBER_SOFT = (254, 243, 199)  # #fef3c7
ROSE = (225, 29, 72)  # #e11d48
ROSE_SOFT = (255, 228, 230)
SKY = (14, 165, 233)
MUTED = (100, 116, 139)
RULE = (203, 213, 225)
SOFT = (241, 245, 249)
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
        self._control_line = ""

    def header(self) -> None:  # type: ignore[override]
        if self.page_no() == 1:
            return
        self.set_fill_color(*NAVY)
        self.rect(0, 0, PAGE_W, 12, "F")
        self.set_fill_color(*EMERALD)
        self.rect(0, 12, PAGE_W, 0.8, "F")
        self.set_xy(MARGIN, 3)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*WHITE)
        self.cell(42, 6, _ascii("RegGuard"), align="L")
        self.set_font("Helvetica", "", 7.5)
        self.cell(CONTENT_W - 42, 6, _ascii(self._doc_subtitle)[:78], align="R")
        self.set_y(16)

    def footer(self) -> None:  # type: ignore[override]
        self.set_y(-16)
        self.set_draw_color(*RULE)
        self.line(MARGIN, self.get_y(), PAGE_W - MARGIN, self.get_y())
        self.set_y(-13)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MUTED)
        left = "CONFIDENTIAL - Planning aid only - confirm with AHJ"
        right = f"Page {self.page_no()}  |  (c) RegGuard"
        self.cell(CONTENT_W * 0.62, 5, _ascii(left), align="L")
        self.cell(CONTENT_W * 0.38, 5, _ascii(right), align="R")
        if self._control_line:
            self.set_y(-9)
            self.set_font("Helvetica", "", 6.5)
            self.cell(CONTENT_W, 4, _ascii(self._control_line)[:110], align="C")


def _need_space(pdf: BoardroomPDF, h: float) -> None:
    if pdf.get_y() + h > PAGE_H - 22:
        pdf.add_page()


def _h1(pdf: BoardroomPDF, text: str) -> None:
    _need_space(pdf, 18)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*NAVY)
    pdf.multi_cell(CONTENT_W, 7.5, _ascii(text))
    y = pdf.get_y()
    pdf.set_fill_color(*EMERALD)
    pdf.rect(MARGIN, y + 0.5, 28, 1.4, "F")
    pdf.set_fill_color(*RULE)
    pdf.rect(MARGIN + 30, y + 0.8, CONTENT_W - 30, 0.6, "F")
    pdf.ln(5)


def _h2(pdf: BoardroomPDF, text: str) -> None:
    _need_space(pdf, 12)
    pdf.set_x(MARGIN)
    pdf.set_fill_color(*EMERALD)
    y = pdf.get_y()
    pdf.rect(MARGIN, y + 1.2, 2.4, 6.0, "F")
    pdf.set_xy(MARGIN + 5, y)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*NAVY)
    pdf.cell(CONTENT_W - 5, 8, _ascii(text), ln=1)
    pdf.ln(0.5)


def _body(pdf: BoardroomPDF, text: str, *, size: int = 10, color: Tuple[int, int, int] = INK) -> None:
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "", size)
    pdf.set_text_color(*color)
    pdf.multi_cell(CONTENT_W, 4.8, _ascii(text))


def _muted(pdf: BoardroomPDF, text: str, size: int = 9) -> None:
    _body(pdf, text, size=size, color=MUTED)


def _severity_color(label: str) -> Tuple[int, int, int]:
    u = str(label or "").upper()
    if any(x in u for x in ("CRIT", "FAIL", "HOLD", "HIGH")):
        return ROSE
    if any(x in u for x in ("WARN", "CAUTION", "MED", "MODERATE")):
        return AMBER
    return EMERALD


def _bullet(pdf: BoardroomPDF, text: str, *, indent: float = 4) -> None:
    _need_space(pdf, 8)
    pdf.set_x(MARGIN + indent)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*INK)
    pdf.multi_cell(CONTENT_W - indent, 4.4, _ascii(f"- {text}"))


def _severity_bullet(pdf: BoardroomPDF, severity: str, text: str) -> None:
    _need_space(pdf, 9)
    tone = _severity_color(severity)
    pdf.set_x(MARGIN + 2)
    pdf.set_fill_color(*tone)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 7)
    tag = _ascii(str(severity or "NOTE").upper())[:12]
    pdf.cell(22, 5, tag, border=0, fill=True, align="C")
    pdf.set_xy(MARGIN + 26, pdf.get_y())
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*INK)
    pdf.multi_cell(CONTENT_W - 26, 4.4, _ascii(text))
    pdf.ln(1)


def _card(pdf: BoardroomPDF, title: str, lines: List[str], *, accent: Tuple[int, int, int] = EMERALD) -> None:
    usable = [ln for ln in lines if ln]
    # Prefit: title + body lines
    est = 10 + max(1, len(usable)) * 5 + 6
    _need_space(pdf, est)
    y0 = pdf.get_y()
    pdf.set_xy(MARGIN + 6, y0 + 3.5)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*accent)
    pdf.multi_cell(CONTENT_W - 10, 5, _ascii(title))
    for line in usable:
        pdf.set_x(MARGIN + 6)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*INK)
        pdf.multi_cell(CONTENT_W - 10, 4.4, _ascii(line))
    y1 = pdf.get_y() + 3.5
    h = max(10, y1 - y0)
    # Paint panel behind by redrawing fill then re-emitting is awkward in FPDF;
    # use outline + accent rail for a clean boardroom card.
    pdf.set_draw_color(*RULE)
    pdf.set_line_width(0.35)
    pdf.rect(MARGIN, y0, CONTENT_W, h, "D")
    pdf.set_fill_color(*accent)
    pdf.rect(MARGIN, y0, 2.6, h, "F")
    pdf.set_line_width(0.2)
    pdf.set_y(y0 + h + 3)

def _metric_box(
    pdf: BoardroomPDF,
    label: str,
    value: str,
    *,
    accent: Tuple[int, int, int] = EMERALD,
) -> None:
    _need_space(pdf, 22)
    y0 = pdf.get_y()
    pdf.set_fill_color(*NAVY)
    pdf.rect(MARGIN, y0, CONTENT_W, 18, "F")
    pdf.set_fill_color(*accent)
    pdf.rect(MARGIN, y0, 3.2, 18, "F")
    pdf.set_xy(MARGIN + 8, y0 + 2.5)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(180, 190, 210)
    pdf.cell(CONTENT_W - 12, 4, _ascii(label.upper()), ln=1)
    pdf.set_x(MARGIN + 8)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*WHITE)
    pdf.cell(CONTENT_W - 12, 8, _ascii(value)[:90], ln=1)
    pdf.set_y(y0 + 20)


def _stamp_banner(pdf: BoardroomPDF, label: str, plain: str, *, hold: bool) -> None:
    _need_space(pdf, 28)
    tone = AMBER if hold else EMERALD
    soft = AMBER_SOFT if hold else EMERALD_SOFT
    y0 = pdf.get_y()
    pdf.set_fill_color(*soft)
    pdf.rect(MARGIN, y0, CONTENT_W, 24, "F")
    pdf.set_fill_color(*tone)
    pdf.rect(MARGIN, y0, 4, 24, "F")
    pdf.set_xy(MARGIN + 8, y0 + 3)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*NAVY)
    pdf.multi_cell(CONTENT_W - 12, 5.5, _ascii(label))
    pdf.set_x(MARGIN + 8)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*INK)
    pdf.multi_cell(CONTENT_W - 12, 4.2, _ascii(plain)[:280])
    pdf.set_y(y0 + 26)


def _table_header(pdf: BoardroomPDF, cols: List[Tuple[str, float]]) -> None:
    _need_space(pdf, 10)
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_x(MARGIN)
    for label, w in cols:
        pdf.cell(w, 7.5, _ascii(label), border=0, fill=True, align="L")
    pdf.ln(7.5)
    pdf.set_fill_color(*EMERALD)
    pdf.rect(MARGIN, pdf.get_y(), CONTENT_W, 0.7, "F")
    pdf.ln(1.2)


def _table_row(pdf: BoardroomPDF, cols: List[Tuple[str, float]], *, alt: bool = False) -> None:
    _need_space(pdf, 12)
    if alt:
        pdf.set_fill_color(*SOFT)
    else:
        pdf.set_fill_color(*WHITE)
    pdf.set_text_color(*INK)
    pdf.set_font("Helvetica", "", 8)
    x0 = MARGIN
    y0 = pdf.get_y()
    heights = []
    for text, w in cols:
        heights.append(max(6, 4.2 * (1 + len(_ascii(text)) // max(12, int(w)))))
    h = min(16, max(heights))
    pdf.set_xy(x0, y0)
    for text, w in cols:
        pdf.set_xy(x0, y0)
        pdf.cell(w, h, "", border=0, fill=True)
        pdf.set_xy(x0 + 1, y0 + 1)
        pdf.multi_cell(w - 2, 3.8, _ascii(text)[:180])
        x0 += w
    pdf.set_draw_color(*RULE)
    pdf.line(MARGIN, y0 + h, MARGIN + CONTENT_W, y0 + h)
    pdf.set_y(y0 + h)

def render_boardroom_pdf(package: Dict[str, Any], output_path: str) -> str:
    pdf = BoardroomPDF()
    cover = package.get("cover") or {}
    qa = package.get("boardroom_qa") or {}
    site = _ascii(cover.get("site") or "Project site")
    title_line = _ascii(f"IC Diligence Package — {site}")[:95]
    pdf._doc_subtitle = title_line[:78]
    pdf._control_line = _ascii(
        f"Generated {package.get('generated_at') or '-'}  |  "
        f"Research {cover.get('research_id') or '-'}  |  "
        f"Boardroom QA {qa.get('pct', '—')}%"
    )
    try:
        pdf.set_title(title_line)
        pdf.set_author("RegGuard")
    except Exception:
        pass

    # ---- Cover ----
    pdf.add_page()
    pdf.set_fill_color(*NAVY_DEEP)
    pdf.rect(0, 0, PAGE_W, 58, "F")
    pdf.set_fill_color(*EMERALD)
    pdf.rect(0, 58, PAGE_W, 2.4, "F")
    pdf.set_fill_color(*AMBER)
    pdf.rect(0, 60.4, PAGE_W, 0.7, "F")
    pdf.set_xy(MARGIN, 10)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*EMERALD)
    pdf.cell(CONTENT_W, 5, _ascii("REGGUARD  ·  IC PROJECT"), ln=1)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*WHITE)
    pdf.cell(CONTENT_W, 10, _ascii("Diligence Package"), ln=1)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(200, 210, 230)
    pdf.multi_cell(CONTENT_W, 5.5, title_line)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(160, 175, 200)
    pdf.cell(CONTENT_W, 5, _ascii("$1,500 boardroom deliverable — bound site diligence"), ln=1)

    pdf.set_y(68)
    # Document control
    pdf.set_fill_color(*SOFT)
    pdf.set_draw_color(*RULE)
    y0 = pdf.get_y()
    pdf.rect(MARGIN, y0, CONTENT_W, 40, "FD")
    pdf.set_fill_color(*EMERALD)
    pdf.rect(MARGIN, y0, 2.4, 40, "F")
    pdf.set_xy(MARGIN + 5, y0 + 2.5)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*EMERALD)
    pdf.cell(CONTENT_W - 8, 4, _ascii("DOCUMENT CONTROL"), ln=1)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*INK)
    for line in [
        f"Site: {site}",
        f"AHJ: {cover.get('ahj_name') or '-'}",
        f"Depth: {cover.get('depth_badge') or cover.get('coverage_badge') or '-'}",
        f"Prepared for: {package.get('generated_for') or 'Authorized recipient'}",
        f"Generated (UTC): {package.get('generated_at') or '-'}",
        f"Share link: {package.get('share_url') or cover.get('research_id') or '-'}",
    ]:
        pdf.set_x(MARGIN + 5)
        pdf.cell(CONTENT_W - 8, 4.8, _ascii(line)[:100], ln=1)
    pdf.set_y(y0 + 42)

    if qa:
        tone = EMERALD if qa.get("pass") else AMBER
        gc = qa.get("gc_forward") or {}
        gc_lines = []
        for item in gc.get("items") or []:
            if item.get("agentic"):
                mark = "PASS" if item.get("ok") else "FAIL"
                gc_lines.append(f"{item.get('id')} [{mark}] {item.get('question')}")
            else:
                gc_lines.append(f"{item.get('id')} [HUMAN] {item.get('question')}")
        _card(
            pdf,
            f"Boardroom QA: {qa.get('pct', 0)}% ({'PASS' if qa.get('pass') else 'GAPS'})"
            + (f"  |  GC forward {'OK' if qa.get('gc_forward_pass') else 'BLOCKED'}"),
            [
                "Automated Q2-Q5 gate. Q1 (forward without apology) remains a human spot-audit.",
                ("Gaps: " + "; ".join(qa.get("gaps") or []))
                if qa.get("gaps")
                else "Structural + GC Q2-Q5 passed.",
                *gc_lines[:6],
            ],
            accent=tone,
        )

    pdf.ln(1)
    _h2(pdf, "Contents")
    for i, title in enumerate(
        [
            "Executive summary",
            "Bid Risk Receipt",
            "Site findings + gotcha confirm cards",
            "Ranked punch list",
            "Next actions",
            "Source appendix + disclaimers",
        ],
        start=1,
    ):
        _bullet(pdf, f"{i}. {title}")
    _muted(
        pdf,
        "This bound package is the primary IC Project deliverable. "
        "Optional worksheets (memo / punch / permits) may be exported separately.",
    )

    # ---- Executive summary ----
    pdf.add_page()
    ex = package.get("executive_summary") or {}
    stamp = ex.get("stamp") or {}
    _h1(pdf, f"1. Executive summary — {site}")
    _body(pdf, ex.get("headline") or "What matters before you bid", size=11)
    pdf.ln(2)

    display = stamp.get("display") or stamp.get("grade") or "-"
    hold = str(display).upper() in ("HOLD", "CAUTION", "FAIL", "HIGH RISK")
    stamp_plain = str(stamp.get("plain") or stamp.get("headline") or "").strip()
    stamp_meta = f"Valid until: {stamp.get('valid_until') or '-'}" + (
        f"  ·  fp {stamp.get('fingerprint')}" if stamp.get("fingerprint") else ""
    )
    _stamp_banner(
        pdf,
        stamp.get("label") or f"REGGUARD STAMP: {display}",
        f"{stamp_plain}  |  {stamp_meta}" if stamp_plain else stamp_meta,
        hold=hold,
    )
    for d in stamp.get("drivers") or []:
        _severity_bullet(
            pdf,
            str(d.get("severity") or "NOTE"),
            f"{d.get('label')}" + (f" — {d.get('detail')}" if d.get("detail") else ""),
        )

    band = ex.get("contingency")
    if isinstance(band, dict):
        pdf.ln(2)
        _h2(pdf, "Suggested bid contingency")
        _metric_box(
            pdf,
            "Suggested contingency band",
            f"+{band.get('pct_low')}% – +{band.get('pct_high')}%  (mid {band.get('pct_mid')}%)",
            accent=AMBER if hold else EMERALD,
        )
        _body(pdf, band.get("plain") or "")
        table = band.get("driver_table") if isinstance(band.get("driver_table"), dict) else {}
        if table.get("rows"):
            pdf.ln(2)
            _h2(pdf, "What drives this band")
            cols = [("Driver", 72.0), ("Band", 18.0), ("Impact / owner", 93.9)]
            _table_header(pdf, cols)
            for i, row in enumerate(table.get("rows") or []):
                _table_row(
                    pdf,
                    [
                        (str(row.get("driver") or ""), 72.0),
                        (str(row.get("band") or ""), 18.0),
                        (f"{row.get('impact') or ''} ({row.get('owner') or ''})", 93.9),
                    ],
                    alt=i % 2 == 1,
                )
            pdf.ln(1)

    if ex.get("env_risk"):
        pdf.ln(1)
        _card(
            pdf,
            "Environmental screening",
            [f"Risk level: {ex.get('env_risk')}"],
            accent=SKY,
        )

    pdf.ln(2)
    _h2(pdf, "Priority items before bid")
    for k in ex.get("top_risks") or []:
        _severity_bullet(
            pdf,
            str(k.get("priority") or "NOTE"),
            f"{k.get('title')}" + (f" — {k.get('detail')}" if k.get("detail") else ""),
        )
    for g in ex.get("local_gotchas") or []:
        _severity_bullet(
            pdf,
            str(g.get("priority") or "NOTE"),
            f"{g.get('title')}" + (f" — {g.get('detail')}" if g.get("detail") else ""),
        )
    if not (ex.get("top_risks") or []) and not (ex.get("local_gotchas") or []):
        _muted(pdf, "No high-priority risk flags in this package payload.")

    pdf.ln(1)
    _h2(pdf, "Recommended next actions")
    for a in ex.get("next_actions") or []:
        _bullet(pdf, a)
    _muted(
        pdf,
        "Stamp legend: CLEAR = no Critical items on current pack · "
        "CAUTION = material risk · HOLD = resolve drivers before treating the bid as clear.",
    )

    # ---- Bid Risk Receipt ----
    pdf.add_page()
    receipt = package.get("bid_risk_receipt") or {}
    _h1(pdf, f"2. Bid Risk Receipt — {site}")
    _body(pdf, "Forward this page to the GC or owner as a one-page risk brief.", size=10)
    pdf.ln(2)
    st = receipt.get("stamp") or stamp
    st_display = st.get("display") or st.get("grade") or display
    st_hold = str(st_display).upper() in ("HOLD", "CAUTION", "FAIL", "HIGH RISK")
    _stamp_banner(
        pdf,
        st.get("label") or f"REGGUARD STAMP: {st_display}",
        st.get("plain") or st.get("headline") or "",
        hold=st_hold,
    )
    band = receipt.get("contingency") or band
    if isinstance(band, dict):
        pdf.ln(1)
        _metric_box(
            pdf,
            "Contingency",
            f"+{band.get('pct_low')}% – +{band.get('pct_high')}% (mid {band.get('pct_mid')}%)",
            accent=AMBER if st_hold else EMERALD,
        )
        _muted(pdf, band.get("plain") or "")
    pdf.ln(2)
    _h2(pdf, "Three risk flags")
    for k in receipt.get("killers") or []:
        _severity_bullet(
            pdf,
            str(k.get("priority") or "NOTE"),
            f"{k.get('title')}" + (f" — {k.get('detail')}" if k.get("detail") else ""),
        )
    if receipt.get("share_url"):
        pdf.ln(2)
        _muted(pdf, f"Interactive share link: {receipt.get('share_url')}")
    pdf.ln(2)
    _muted(pdf, receipt.get("disclaimer") or "")

    # ---- Site findings ----
    pdf.add_page()
    findings = package.get("site_findings") or {}
    _h1(pdf, f"3. Site findings — {site}")
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
                line += f" — {f.get('amount')}"
            _bullet(pdf, line)
            if f.get("note"):
                _muted(pdf, f"  {f.get('note')}")

    cards = findings.get("gotcha_cards") or findings.get("gotchas") or []
    if cards:
        pdf.ln(2)
        _h2(pdf, "Gotcha confirm cards")
        for g in cards:
            _need_space(pdf, 28)
            _body(pdf, f"[{g.get('priority') or 'WATCH'}] {g.get('title')}", size=10)
            if g.get("detail"):
                _muted(pdf, g.get("detail"))
            for c in g.get("checklist") or []:
                _bullet(pdf, c, indent=6)
            if g.get("confirm_step"):
                _body(pdf, f"Confirm: {g.get('confirm_step')}", size=9)
            _muted(
                pdf,
                f"Owner: {g.get('owner') or 'Estimator / PM'} · Citation: {g.get('source_label') or 'Unverified'}",
            )
            for a in g.get("anti_patterns") or []:
                _muted(pdf, f"Don't: {a}")
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

    # ---- Punch ----
    pdf.add_page()
    punch = package.get("punch_list") or {}
    _h1(pdf, f"4. Ranked punch list — {site}")
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

    # ---- Next actions (was action plan / code dump) ----
    pdf.add_page()
    _h1(pdf, f"5. Next actions — {site}")
    _muted(
        pdf,
        "Boardroom next steps drawn from high-priority risks and confirm cards. "
        "The ranked punch list is the full operational checklist.",
    )
    pdf.ln(1)
    for a in package.get("action_plan_summary") or []:
        _bullet(pdf, a)
    excerpt = (package.get("action_plan_excerpt") or "").strip()
    if excerpt:
        pdf.ln(2)
        _h2(pdf, "Research memo excerpt")
        _body(pdf, excerpt[:1600], size=9)

    # ---- Sources ----
    pdf.add_page()
    _h1(pdf, f"6. Source appendix — {site}")
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
