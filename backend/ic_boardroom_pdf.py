"""
IC Diligence Package PDF — same dark slate canvas as Bid Packet / Bid Sheet.

Full-page slate-950, emerald rails, compact cards, white/muted type.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

from bid_packet_pdf import (
    AMBER,
    AMBER_SOFT,
    BG,
    CARD,
    CARD_EDGE,
    CONTENT_W,
    DIM,
    EMERALD,
    EMERALD_SOFT,
    MARGIN,
    MUTED,
    PAGE_H,
    PAGE_W,
    PURPLE,
    WHITE,
    BidPacketPDF,
    _ascii,
    _badge,
    _body,
    _card_box,
    _muted,
    _section_title,
)

ROSE = (239, 68, 68)
SKY = (56, 189, 248)


class BoardroomPDF(BidPacketPDF):
    def __init__(self) -> None:
        super().__init__()
        self._footer_label = "Reg Guard IC Diligence"
        self._doc_subtitle = "IC Diligence"
        self._control_line = ""

    def header(self) -> None:  # type: ignore[override]
        self.set_fill_color(*BG)
        self.rect(0, 0, PAGE_W, PAGE_H, "F")
        self.set_fill_color(*EMERALD)
        self.rect(0, 0, PAGE_W, 3.2, "F")
        if self.page_no() == 1:
            return
        self.set_xy(MARGIN, 6)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*WHITE)
        self.cell(48, 6, "REG GUARD", align="L")
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*EMERALD_SOFT)
        self.cell(CONTENT_W - 48, 6, _ascii(self._doc_subtitle)[:78], align="R")
        self.set_y(14)

    def footer(self) -> None:  # type: ignore[override]
        self.set_y(-16)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*DIM)
        self.cell(
            0,
            4,
            _ascii(
                f"{self._footer_label}  |  Planning aid only - confirm with AHJ  |  "
                f"Page {self.page_no()}"
            ),
            align="C",
        )
        if self._control_line:
            self.set_y(-11)
            self.set_font("Helvetica", "", 6.5)
            self.set_text_color(*DIM)
            self.cell(0, 4, _ascii(self._control_line)[:110], align="C")


def _need_space(pdf: BoardroomPDF, h: float) -> None:
    if pdf.get_y() + h > PAGE_H - 24:
        pdf.add_page()
        if pdf.page_no() > 1:
            pdf.set_y(16)


def _pri_colors(label: str) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    u = str(label or "").upper()
    if any(x in u for x in ("CRIT", "FAIL", "HOLD")):
        return BG, ROSE
    if any(x in u for x in ("HIGH", "WARN", "CAUTION")):
        return BG, AMBER
    if any(x in u for x in ("MED", "MODERATE")):
        return WHITE, CARD_EDGE
    return BG, EMERALD


def _link_line(pdf: BoardroomPDF, label: str, url: str) -> None:
    u = str(url or "").strip()
    if not u:
        return
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*EMERALD)
    pdf.multi_cell(CONTENT_W, 4.0, _ascii(f"{label}: {u}"))


def _accent_card(
    pdf: BoardroomPDF,
    title: str,
    lines: List[str],
    *,
    accent: Tuple[int, int, int] = EMERALD,
    title_size: int = 10,
) -> None:
    usable = [ln for ln in lines if ln]
    inner_w = CONTENT_W - 14
    pdf.set_font("Helvetica", "B", title_size)
    title_h = pdf.multi_cell(inner_w, 5, _ascii(title or " "), dry_run=True, output="HEIGHT") or 5
    body_h = 0.0
    pdf.set_font("Helvetica", "", 8)
    for ln in usable:
        body_h += pdf.multi_cell(inner_w, 4.0, _ascii(ln), dry_run=True, output="HEIGHT") or 4
    h = float(title_h) + float(body_h) + 8
    _need_space(pdf, h + 3)
    y0 = pdf.get_y()
    pdf.set_fill_color(*CARD)
    pdf.set_draw_color(*CARD_EDGE)
    pdf.rect(MARGIN, y0, CONTENT_W, h, "DF")
    pdf.set_fill_color(*accent)
    pdf.rect(MARGIN, y0, 2.6, h, "F")
    pdf.set_xy(MARGIN + 6, y0 + 3)
    pdf.set_font("Helvetica", "B", title_size)
    pdf.set_text_color(*accent)
    pdf.multi_cell(inner_w, 5, _ascii(title))
    for line in usable:
        pdf.set_x(MARGIN + 6)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(inner_w, 4.0, _ascii(line))
    pdf.set_y(y0 + h + 2.5)


def _hero_metric(pdf: BoardroomPDF, label: str, value: str, note: str = "") -> None:
    h = 28 if note else 22
    _need_space(pdf, h + 4)
    cx, cy = _card_box(pdf, h)
    pdf.set_xy(cx, cy)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*MUTED)
    pdf.cell(CONTENT_W - 8, 4, _ascii(label.upper()), ln=1)
    pdf.set_x(cx)
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(*EMERALD_SOFT)
    pdf.cell(CONTENT_W - 8, 11, _ascii(value)[:48], ln=1)
    if note:
        pdf.set_x(cx)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(CONTENT_W - 8, 3.5, _ascii(note)[:220])
    pdf.set_y(cy + h + 2)


def _flag_card(pdf: BoardroomPDF, priority: str, title: str, detail: str = "") -> None:
    box_h = 16 + (8 if detail else 0)
    _need_space(pdf, box_h + 3)
    bx, by = _card_box(pdf, box_h)
    fg, bg = _pri_colors(priority)
    tag = _ascii(str(priority or "NOTE").upper())[:12]
    _badge(pdf, tag, fg=fg, bg=bg, x=bx, y=by)
    pdf.set_xy(bx, by + 6.5)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*WHITE)
    pdf.multi_cell(CONTENT_W - 12, 4, _ascii(title)[:140])
    if detail:
        pdf.set_x(bx)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(CONTENT_W - 12, 3.5, _ascii(detail)[:240])
    pdf.set_y(by + box_h + 2)


def _site_card(pdf: BoardroomPDF, site: str, lines: List[str]) -> None:
    h = 18
    _need_space(pdf, h + 3)
    y0 = pdf.get_y()
    pdf.set_fill_color(*CARD)
    pdf.set_draw_color(*EMERALD)
    pdf.rect(MARGIN, y0, CONTENT_W, h, "DF")
    pdf.set_xy(MARGIN + 4, y0 + 3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*WHITE)
    pdf.cell(CONTENT_W - 8, 5, _ascii(site)[:90], ln=1)
    shown = [x for x in lines if x]
    pdf.set_x(MARGIN + 4)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*MUTED)
    pdf.cell(CONTENT_W - 8, 4, _ascii(shown[0] if shown else "")[:110], ln=1)
    pdf.set_x(MARGIN + 4)
    pdf.set_text_color(*DIM)
    pdf.cell(CONTENT_W - 8, 4, _ascii("  |  ".join(shown[1:]))[:110], ln=1)
    pdf.set_y(y0 + h + 2)


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

    ex = package.get("executive_summary") or {}
    stamp = ex.get("stamp") or {}
    display = str(stamp.get("display") or stamp.get("grade") or "-")
    hold = display.upper() in ("HOLD", "CAUTION", "FAIL", "HIGH RISK")
    band = ex.get("contingency") if isinstance(ex.get("contingency"), dict) else {}

    # ---- Cover (Bid Packet brand bar + hero) ----
    pdf.add_page()
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.set_y(8)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*WHITE)
    pdf.cell(CONTENT_W * 0.55, 8, "REG GUARD", ln=0)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*EMERALD_SOFT)
    pdf.cell(CONTENT_W * 0.45, 8, "IC DILIGENCE", align="R", ln=1)
    _muted(
        pdf,
        "$1,500 boardroom deliverable  |  Bound site diligence  |  Planning aid - not a quote, not a filing",
        8,
    )
    _muted(
        pdf,
        _ascii(
            f"{cover.get('depth_badge') or cover.get('coverage_badge') or 'IC Project'}"
            f"  |  {cover.get('ahj_name') or 'Local AHJ'}"
        ),
        8,
    )

    pdf.ln(1)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 16)
    if hold:
        pdf.set_text_color(*ROSE)
    else:
        pdf.set_text_color(*EMERALD_SOFT)
    stamp_label = _ascii(stamp.get("label") or f"REGGUARD STAMP: {display}")
    pdf.multi_cell(CONTENT_W, 7, stamp_label)
    if stamp.get("plain") or stamp.get("headline"):
        _muted(pdf, str(stamp.get("plain") or stamp.get("headline"))[:220], 8)
    if stamp.get("valid_until"):
        _muted(
            pdf,
            f"Valid until {stamp.get('valid_until')}"
            + (f"  |  fp {stamp.get('fingerprint')}" if stamp.get("fingerprint") else ""),
            7,
        )

    pdf.ln(1)
    _site_card(
        pdf,
        site,
        [
            str(cover.get("ahj_name") or "Local AHJ"),
            str(cover.get("depth_badge") or cover.get("coverage_badge") or "IC Project"),
            f"Generated {package.get('generated_at') or '-'}",
        ],
    )

    if band.get("pct_low") is not None:
        _section_title(pdf, "Contingency band (screenshot this)")
        _hero_metric(
            pdf,
            "Suggested bid contingency",
            f"+{band.get('pct_low')}%  -  +{band.get('pct_high')}%   (mid {band.get('pct_mid')}%)",
            str(band.get("plain") or "Planning aid - not a quote. Confirm dollars with the AHJ.")[:220],
        )

    killers = list(ex.get("top_risks") or [])[:3]
    if killers:
        _section_title(pdf, "Top risk flags")
        for k in killers:
            _flag_card(
                pdf,
                str(k.get("priority") or "NOTE"),
                str(k.get("title") or "Item"),
                str(k.get("detail") or ""),
            )

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
        _accent_card(
            pdf,
            f"Boardroom QA  {qa.get('pct', 0)}%  |  "
            f"{'PASS' if qa.get('pass') else 'GAPS'}  |  "
            f"GC forward {'OK' if qa.get('gc_forward_pass') else 'BLOCKED'}",
            [
                "Automated Q2-Q5 gate. Q1 (forward without apology) remains a human spot-audit.",
                ("Gaps: " + "; ".join(qa.get("gaps") or []))
                if qa.get("gaps")
                else "Structural + GC Q2-Q5 passed.",
                *gc_lines[:6],
            ],
            accent=tone,
        )

    _accent_card(
        pdf,
        "Document control",
        [
            f"Site: {site}",
            f"AHJ: {cover.get('ahj_name') or '-'}",
            f"Prepared for: {package.get('generated_for') or 'Authorized recipient'}",
            f"Share: {package.get('share_url') or cover.get('research_id') or '-'}",
        ],
        accent=EMERALD,
    )

    # ---- Executive recommendation ----
    pdf.add_page()
    pdf.set_y(16)
    _section_title(pdf, f"1. Executive recommendation — {site}")
    _body(pdf, ex.get("headline") or "What matters before you bid", 10)
    pdf.ln(1)
    for d in stamp.get("drivers") or []:
        _flag_card(
            pdf,
            str(d.get("severity") or "NOTE"),
            str(d.get("label") or ""),
            str(d.get("detail") or ""),
        )

    table = band.get("driver_table") if isinstance(band.get("driver_table"), dict) else {}
    if table.get("rows"):
        _section_title(pdf, "What drives this band")
        for row in table.get("rows") or []:
            _accent_card(
                pdf,
                f"{row.get('driver') or 'Driver'}  [{row.get('band') or ''}]",
                [f"{row.get('impact') or ''} ({row.get('owner') or ''})".strip()],
                accent=AMBER if str(row.get("band") or "").upper() in ("HIGH", "CRIT") else EMERALD,
            )

    if ex.get("env_risk"):
        _accent_card(pdf, "Environmental screening", [f"Risk level: {ex.get('env_risk')}"], accent=SKY)

    _section_title(pdf, "Priority items before bid")
    for k in ex.get("top_risks") or []:
        _flag_card(pdf, str(k.get("priority") or "NOTE"), str(k.get("title") or ""), str(k.get("detail") or ""))
    for g in ex.get("local_gotchas") or []:
        _flag_card(pdf, str(g.get("priority") or "NOTE"), str(g.get("title") or ""), str(g.get("detail") or ""))
    if not (ex.get("top_risks") or []) and not (ex.get("local_gotchas") or []):
        _muted(pdf, "No high-priority risk flags in this package payload.")

    _section_title(pdf, "Recommended next actions")
    for a in ex.get("next_actions") or []:
        _body(pdf, f"- {a}", 9)
    _muted(
        pdf,
        "Stamp legend: CLEAR = no Critical items  |  CAUTION = material risk  |  "
        "HOLD = resolve drivers before treating the bid as clear.",
    )

    # ---- Risk stamp page ----
    pdf.add_page()
    pdf.set_y(16)
    receipt = package.get("bid_risk_receipt") or {}
    _section_title(pdf, f"2. Risk stamp & contingency — {site}")
    _muted(pdf, "One-page risk brief for GC / owner / IC war-room. Planning aid - not a quote.")
    st = receipt.get("stamp") or stamp
    st_display = str(st.get("display") or st.get("grade") or display)
    pdf.ln(1)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(
        *ROSE if st_display.upper() in ("HOLD", "CAUTION", "FAIL", "HIGH RISK") else EMERALD_SOFT
    )
    pdf.multi_cell(CONTENT_W, 7, _ascii(st.get("label") or f"REGGUARD STAMP: {st_display}"))
    _muted(pdf, str(st.get("plain") or st.get("headline") or ""), 8)

    rband = receipt.get("contingency") or band
    if isinstance(rband, dict) and rband.get("pct_low") is not None:
        _hero_metric(
            pdf,
            "Contingency",
            f"+{rband.get('pct_low')}%  -  +{rband.get('pct_high')}%   (mid {rband.get('pct_mid')}%)",
            str(rband.get("plain") or "")[:220],
        )

    _section_title(pdf, "Three risk flags")
    for k in receipt.get("killers") or []:
        _flag_card(pdf, str(k.get("priority") or "NOTE"), str(k.get("title") or ""), str(k.get("detail") or ""))
    if receipt.get("share_url"):
        _link_line(pdf, "Interactive share", str(receipt.get("share_url")))
    pdf.ln(1)
    _accent_card(
        pdf,
        "PLANNING AID ONLY",
        [str(receipt.get("disclaimer") or "Citeable pre-bid diligence - not a quote or sealed bid.")],
        accent=EMERALD,
    )

    # ---- Jurisdiction ----
    pdf.add_page()
    pdf.set_y(16)
    findings = package.get("site_findings") or {}
    _section_title(pdf, f"3. Parallel path schedule & jurisdiction — {site}")
    clocks = findings.get("parallel_clocks") or []
    if clocks:
        _muted(
            pdf,
            "Data-center / large-load sites typically run municipal AHJ permits and utility "
            "interconnection on independent clocks. Slip on either path moves bid risk.",
        )
        for c in clocks[:8]:
            if not isinstance(c, dict):
                continue
            _accent_card(
                pdf,
                str(c.get("name") or c.get("label") or "Path"),
                [str(c.get("detail") or c.get("note") or "")],
                accent=PURPLE,
            )

    ahj = findings.get("ahj") or {}
    _section_title(pdf, "Authority having jurisdiction")
    ahj_lines = [str(ahj.get("name") or cover.get("ahj_name") or "Local AHJ")]
    if ahj.get("last_verified"):
        ahj_lines.append(f"Last verified: {ahj.get('last_verified')}")
    if ahj.get("notes"):
        ahj_lines.append(str(ahj.get("notes")))
    if findings.get("coverage_note"):
        ahj_lines.append(str(findings.get("coverage_note")))
    _accent_card(pdf, ahj_lines[0], ahj_lines[1:], accent=EMERALD)
    if ahj.get("portal_url"):
        _link_line(pdf, "Portal", ahj.get("portal_url"))
    if ahj.get("fees_url"):
        _link_line(pdf, "Fees", ahj.get("fees_url"))
    if ahj.get("apply_url"):
        _link_line(pdf, "Apply", ahj.get("apply_url"))
    if ahj.get("inspections_url"):
        _link_line(pdf, "Inspections", ahj.get("inspections_url"))

    fees = findings.get("fees") or []
    if fees:
        _section_title(pdf, "Fee & timeline extracts (confirm on schedule)")
        for f in fees:
            amt = f.get("amount")
            title = str(f.get("name") or "Fee")
            if f.get("trade"):
                title = f"[{f.get('trade')}] {title}"
            if amt:
                title = f"{title}  —  {amt}"
            cite = f.get("source_label") or ("Source" if f.get("source_url") else "Unverified - confirm with AHJ")
            _accent_card(pdf, title, [str(f.get("note") or ""), cite], accent=AMBER_SOFT)
            if f.get("source_url"):
                _link_line(pdf, "Source", f.get("source_url"))

    insp = findings.get("inspection_sequence") or []
    if insp:
        _section_title(pdf, "Inspection sequence")
        _accent_card(
            pdf,
            "From live city pack",
            [f"{i}. {step}" for i, step in enumerate(insp, start=1)],
            accent=EMERALD,
        )

    docs = findings.get("document_checklist") or []
    if docs:
        _section_title(pdf, "Document checklist")
        lines = []
        for d in docs:
            if isinstance(d, dict):
                task = d.get("task") or "Document"
                note = d.get("note") or ""
                lines.append(f"[ ] {task}" + (f" - {note}" if note else ""))
            else:
                lines.append(f"[ ] {d}")
        _accent_card(pdf, "Submittals to confirm with AHJ", lines, accent=EMERALD)

    cards = findings.get("gotcha_cards") or findings.get("gotchas") or []
    if cards:
        _section_title(pdf, "Local gotcha confirm cards")
        for g in cards:
            bits = [str(g.get("detail") or "")]
            if g.get("confirm_step"):
                bits.append(f"Confirm: {g.get('confirm_step')}")
            bits.append(
                f"Owner: {g.get('owner') or 'Estimator / PM'}  |  "
                f"Citation: {g.get('source_label') or 'Unverified'}"
            )
            for a in g.get("anti_patterns") or []:
                bits.append(f"Don't: {a}")
            pri = str(g.get("priority") or "WATCH")
            fg, bgc = _pri_colors(pri)
            _accent_card(
                pdf,
                f"[{pri}] {g.get('title') or 'Watch item'}",
                bits,
                accent=bgc if bgc != CARD_EDGE else AMBER,
            )

    if findings.get("env_risk") or findings.get("env_findings"):
        env_lines = []
        if findings.get("env_risk"):
            env_lines.append(f"Risk level: {findings.get('env_risk')}")
        for f in findings.get("env_findings") or []:
            env_lines.append(f"{f.get('category')}: {f.get('description')}")
        _accent_card(pdf, "Environmental screening", env_lines, accent=SKY)

    # ---- Punch ----
    pdf.add_page()
    pdf.set_y(16)
    punch = package.get("punch_list") or {}
    _section_title(pdf, f"4. Critical-path punch list — {site}")
    if punch.get("timeline_summary"):
        _muted(pdf, f"Timeline summary: {punch.get('timeline_summary')}")
    items = punch.get("items") or []
    if not items:
        _muted(pdf, "No punch-list items in this package payload.")
    for item in items:
        cost = item.get("estimated_cost")
        cost_s = f"  ·  est ${cost:,.0f}" if isinstance(cost, (int, float)) and cost else ""
        _flag_card(
            pdf,
            str(item.get("priority") or "NOTE"),
            f"{item.get('task')}{cost_s}",
            f"Timing: {item.get('timeline') or 'Pre-bid'}  |  {item.get('citation') or 'Unverified'}",
        )

    # ---- Next actions ----
    pdf.add_page()
    pdf.set_y(16)
    _section_title(pdf, f"5. Next actions — {site}")
    _muted(
        pdf,
        "Boardroom next steps drawn from high-priority risks and confirm cards. "
        "The ranked punch list is the full operational checklist.",
    )
    for a in package.get("action_plan_summary") or []:
        _body(pdf, f"- {a}", 9)
    excerpt = (package.get("action_plan_excerpt") or "").strip()
    if excerpt:
        _section_title(pdf, "Research memo excerpt")
        _accent_card(pdf, "Planning excerpt (not a filing)", [excerpt[:1600]], accent=CARD_EDGE)

    # ---- Sources ----
    pdf.add_page()
    pdf.set_y(16)
    _section_title(pdf, f"6. Source appendix — {site}")
    _muted(pdf, "Every forwardable claim should resolve to a URL below or be treated as Unverified.")
    sources = package.get("sources") or []
    if not sources:
        _muted(pdf, "No http(s) sources were attached to this analysis.")
    for i, src in enumerate(sources, start=1):
        _accent_card(
            pdf,
            f"{i}. {src.get('label') or 'Source'}",
            [str(src.get("url") or "")],
            accent=EMERALD,
        )

    pdf.ln(2)
    _accent_card(
        pdf,
        "Disclaimers",
        [str(d) for d in (package.get("disclaimers") or [])],
        accent=AMBER,
    )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    pdf.output(output_path)
    return output_path


def generate_ic_boardroom_pdf_bytes(
    analysis: Dict[str, Any],
    *,
    generated_for: str = "",
    share_url: str = "",
) -> bytes:
    raw, _qa = generate_ic_boardroom_pdf_with_qa(
        analysis,
        generated_for=generated_for,
        share_url=share_url,
    )
    return raw


def generate_ic_boardroom_pdf_with_qa(
    analysis: Dict[str, Any],
    *,
    generated_for: str = "",
    share_url: str = "",
) -> tuple:
    """Return (pdf_bytes, boardroom_qa dict)."""
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
    return raw, (package.get("boardroom_qa") or {})
