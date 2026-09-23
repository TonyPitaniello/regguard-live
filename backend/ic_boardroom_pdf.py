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
    """Break only when the next block cannot fit — keep pages dense."""
    footer_reserve = 20
    if pdf.get_y() + h > PAGE_H - footer_reserve:
        pdf.add_page()
        if pdf.page_no() > 1:
            pdf.set_y(15)


def _begin_section(pdf: BoardroomPDF, title: str, *, min_remain: float = 28) -> None:
    """
    Continue on the current page whenever the heading + first block fit.
    Avoid orphan section titles with almost-empty pages underneath.
    """
    footer_reserve = 20
    if pdf.page_no() >= 1 and pdf.get_y() > 18:
        if pdf.get_y() + min_remain <= PAGE_H - footer_reserve:
            pdf.ln(1.6)
        else:
            pdf.add_page()
            if pdf.page_no() > 1:
                pdf.set_y(15)
    _section_title(pdf, title, y_pad=0.6)


def _pri_colors(label: str) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    u = str(label or "").upper()
    if any(x in u for x in ("CRIT", "FAIL")):
        return BG, ROSE
    if "HOLD" in u:
        return BG, AMBER
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
    title_h = pdf.multi_cell(inner_w, 4.5, _ascii(title or " "), dry_run=True, output="HEIGHT") or 4.5
    body_h = 0.0
    pdf.set_font("Helvetica", "", 8)
    for ln in usable:
        body_h += pdf.multi_cell(inner_w, 3.8, _ascii(ln), dry_run=True, output="HEIGHT") or 3.8
    h = float(title_h) + float(body_h) + 4.5
    _need_space(pdf, h + 1.5)
    y0 = pdf.get_y()
    pdf.set_fill_color(*CARD)
    pdf.set_draw_color(*CARD_EDGE)
    pdf.rect(MARGIN, y0, CONTENT_W, h, "DF")
    pdf.set_fill_color(*accent)
    pdf.rect(MARGIN, y0, 2.6, h, "F")
    pdf.set_xy(MARGIN + 6, y0 + 2.0)
    pdf.set_font("Helvetica", "B", title_size)
    pdf.set_text_color(*accent)
    pdf.multi_cell(inner_w, 4.5, _ascii(title))
    for line in usable:
        pdf.set_x(MARGIN + 6)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(inner_w, 3.8, _ascii(line))
    pdf.set_y(y0 + h + 1.0)


def _hero_metric(pdf: BoardroomPDF, label: str, value: str, note: str = "") -> None:
    inner_w = CONTENT_W - 8
    pdf.set_font("Helvetica", "", 8)
    label_h = 4.0
    pdf.set_font("Helvetica", "B", 18)
    value_h = pdf.multi_cell(inner_w, 8, _ascii(value or " ")[:48], dry_run=True, output="HEIGHT") or 8
    note_h = 0.0
    if note:
        pdf.set_font("Helvetica", "", 7)
        note_h = pdf.multi_cell(inner_w, 3.3, _ascii(note)[:220], dry_run=True, output="HEIGHT") or 3.3
    h = 5.0 + float(label_h) + float(value_h) + float(note_h)
    _need_space(pdf, h + 2)
    cx, cy = _card_box(pdf, h)
    pdf.set_xy(cx, cy)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*MUTED)
    pdf.cell(inner_w, 4, _ascii(label.upper()), ln=1)
    pdf.set_x(cx)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*EMERALD_SOFT)
    pdf.multi_cell(inner_w, 8, _ascii(value)[:48])
    if note:
        pdf.set_x(cx)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(inner_w, 3.3, _ascii(note)[:220])
    pdf.set_y(cy + h + 1.0)


def _flag_card(pdf: BoardroomPDF, priority: str, title: str, detail: str = "") -> None:
    pri = str(priority or "NOTE").upper()
    if pri == "FAIL":
        pri = "HOLD"
    # Measure real wrap height so we don't reserve unused blank in the card
    inner_w = CONTENT_W - 12
    pdf.set_font("Helvetica", "B", 9)
    title_h = pdf.multi_cell(inner_w, 3.8, _ascii(str(title or "")[:160]), dry_run=True, output="HEIGHT") or 3.8
    detail_h = 0.0
    if detail:
        pdf.set_font("Helvetica", "", 7.5)
        detail_h = pdf.multi_cell(inner_w, 3.3, _ascii(str(detail)[:240]), dry_run=True, output="HEIGHT") or 3.3
    box_h = 7.0 + float(title_h) + float(detail_h) + 1.5
    _need_space(pdf, box_h + 1.5)
    bx, by = _card_box(pdf, box_h)
    fg, bg = _pri_colors(pri)
    tag = _ascii(pri)[:12]
    _badge(pdf, tag, fg=fg, bg=bg, x=bx, y=by)
    pdf.set_xy(bx, by + 5.8)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*WHITE)
    pdf.multi_cell(inner_w, 3.8, _ascii(str(title)[:160]))
    if detail:
        pdf.set_x(bx)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(inner_w, 3.3, _ascii(str(detail)[:240]))
    pdf.set_y(by + box_h + 1.0)


def _site_card(pdf: BoardroomPDF, site: str, lines: List[str]) -> None:
    h = 16
    _need_space(pdf, h + 2)
    y0 = pdf.get_y()
    pdf.set_fill_color(*CARD)
    pdf.set_draw_color(*EMERALD)
    pdf.rect(MARGIN, y0, CONTENT_W, h, "DF")
    pdf.set_xy(MARGIN + 4, y0 + 2.5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*WHITE)
    pdf.cell(CONTENT_W - 8, 5, _ascii(site)[:90], ln=1)
    shown = [x for x in lines if x]
    pdf.set_x(MARGIN + 4)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*MUTED)
    pdf.cell(CONTENT_W - 8, 3.5, _ascii(shown[0] if shown else "")[:110], ln=1)
    pdf.set_x(MARGIN + 4)
    pdf.set_text_color(*DIM)
    pdf.cell(CONTENT_W - 8, 3.5, _ascii("  |  ".join(shown[1:]))[:110], ln=1)
    pdf.set_y(y0 + h + 1.5)


def render_boardroom_pdf(package: Dict[str, Any], output_path: str) -> str:
    from artifact_naming import document_display_title

    pdf = BoardroomPDF()
    cover = package.get("cover") or {}
    site = _ascii(cover.get("site") or "Project site")
    title_line = _ascii(document_display_title(site, "IC DILIGENCE PACKAGE"))
    pdf._doc_subtitle = title_line[:90]
    pdf._footer_label = title_line[:90]
    pdf._control_line = _ascii(
        f"{site}  |  Generated {package.get('generated_at') or '-'}  |  "
        f"Planning aid - confirm with AHJ"
    )
    try:
        pdf.set_title(title_line[:120])
        pdf.set_author("Reg Guard")
    except Exception:
        pass

    ex = package.get("executive_summary") or {}
    stamp = ex.get("stamp") or {}
    raw_display = str(stamp.get("display") or stamp.get("grade") or "-")
    display = {"FAIL": "HOLD", "PASS": "CLEAR", "HOLD": "HOLD", "CLEAR": "CLEAR", "CAUTION": "CAUTION"}.get(
        raw_display.upper(), raw_display.upper()
    )
    hold = display in ("HOLD", "CAUTION")
    stamp_color = AMBER if hold else EMERALD_SOFT
    band = ex.get("contingency") if isinstance(ex.get("contingency"), dict) else {}

    # ---- Cover (dark slate + emerald rail, contractor-facing) ----
    pdf.add_page()
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.set_y(8)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*WHITE)
    pdf.cell(CONTENT_W, 8, "REG GUARD", ln=1)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*EMERALD_SOFT)
    pdf.multi_cell(CONTENT_W, 4.5, title_line)
    _muted(
        pdf,
        "Bound site diligence  |  Planning aid - not a quote, not a filing",
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
    pdf.set_text_color(*stamp_color)
    stamp_label = str(stamp.get("label") or f"REGGUARD STAMP: {display}")
    stamp_label = stamp_label.replace("FAIL", "HOLD")
    pdf.multi_cell(CONTENT_W, 7, _ascii(stamp_label))
    if stamp.get("plain") or stamp.get("headline"):
        _muted(pdf, str(stamp.get("plain") or stamp.get("headline")).replace("FAIL", "HOLD")[:220], 8)
    if stamp.get("valid_until"):
        _muted(pdf, f"Valid until {str(stamp.get('valid_until'))[:10]}  |  Re-run before bid submittal.", 7)

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

    killers = list(ex.get("top_risks") or [])[:5]
    if killers:
        _section_title(pdf, "Top risk flags")
        for k in killers:
            _flag_card(
                pdf,
                str(k.get("priority") or "NOTE"),
                str(k.get("title") or "Item"),
                str(k.get("detail") or ""),
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
        title_size=9,
    )

    deliv = package.get("deliverable") if isinstance(package.get("deliverable"), dict) else {}
    _accent_card(
        pdf,
        "What this package includes",
        [
            str(
                deliv.get("primary")
                or "Full IC Diligence Package PDF for IC / interconnection / owner’s-rep review"
            ),
            "1. Executive recommendation & stamp  |  2. Contingency drivers  |  "
            "3. Parallel clocks (AHJ · interconnect · water)",
            "4. Jurisdiction, fees, gotchas, env  |  5. Full critical-path punch list",
            "6. Evidence binder (EX-00N)  |  7. Next actions  |  8. Source appendix",
            str(deliv.get("working_set") or "Companion: counsel DOCX · estimator Excel · optional CSV · 1-page memo"),
        ],
        accent=EMERALD,
        title_size=9,
    )

    # ---- Body sections flow continuously; page-break only when a section won't fit ----
    _begin_section(pdf, f"1. Executive recommendation — {site}", min_remain=32)
    _body(pdf, ex.get("headline") or "What matters before you bid", 10)
    pdf.ln(0.5)
    for d in stamp.get("drivers") or []:
        _flag_card(
            pdf,
            str(d.get("severity") or "NOTE"),
            str(d.get("label") or ""),
            str(d.get("detail") or ""),
        )

    table = band.get("driver_table") if isinstance(band.get("driver_table"), dict) else {}
    if table.get("rows"):
        _section_title(pdf, "What drives this band", y_pad=1.0)
        for row in table.get("rows") or []:
            _accent_card(
                pdf,
                f"{row.get('driver') or 'Driver'}  [{row.get('band') or ''}]",
                [f"{row.get('impact') or ''} ({row.get('owner') or ''})".strip()],
                accent=AMBER if str(row.get("band") or "").upper() in ("HIGH", "CRIT") else EMERALD,
                title_size=9,
            )

    if ex.get("env_risk"):
        _accent_card(pdf, "Environmental screening", [f"Risk level: {ex.get('env_risk')}"], accent=SKY, title_size=9)

    _section_title(pdf, "Priority items before bid", y_pad=1.0)
    for k in ex.get("top_risks") or []:
        _flag_card(pdf, str(k.get("priority") or "NOTE"), str(k.get("title") or ""), str(k.get("detail") or ""))
    for g in ex.get("local_gotchas") or []:
        _flag_card(pdf, str(g.get("priority") or "NOTE"), str(g.get("title") or ""), str(g.get("detail") or ""))
    if not (ex.get("top_risks") or []) and not (ex.get("local_gotchas") or []):
        _muted(pdf, "No high-priority risk flags in this package payload.")

    _section_title(pdf, "Recommended next actions", y_pad=1.0)
    for a in ex.get("next_actions") or []:
        _body(pdf, f"- {a}", 9)
    _muted(
        pdf,
        "Stamp legend: CLEAR = no Critical items  |  CAUTION = material risk  |  "
        "HOLD = resolve drivers before treating the bid as clear.",
    )

    # ---- Risk stamp (continue on same page when room) ----
    receipt = package.get("bid_risk_receipt") or {}
    _begin_section(pdf, f"2. Risk stamp & contingency — {site}", min_remain=36)
    _muted(pdf, "One-page risk brief for GC / owner / IC war-room. Planning aid - not a quote.")
    st = receipt.get("stamp") or stamp
    st_display = str(st.get("display") or st.get("grade") or display)
    pdf.ln(0.5)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 14)
    st_face = {"FAIL": "HOLD", "PASS": "CLEAR", "HOLD": "HOLD", "CLEAR": "CLEAR", "CAUTION": "CAUTION"}.get(
        st_display.upper(), st_display.upper()
    )
    pdf.set_text_color(*AMBER if st_face in ("HOLD", "CAUTION") else EMERALD_SOFT)
    pdf.multi_cell(
        CONTENT_W,
        6,
        _ascii((st.get("label") or f"REGGUARD STAMP: {st_face}").replace("FAIL", "HOLD")),
    )
    _muted(pdf, str(st.get("plain") or st.get("headline") or "").replace("FAIL", "HOLD"), 8)

    rband = receipt.get("contingency") or band
    if isinstance(rband, dict) and rband.get("pct_low") is not None:
        _hero_metric(
            pdf,
            "Contingency",
            f"+{rband.get('pct_low')}%  -  +{rband.get('pct_high')}%   (mid {rband.get('pct_mid')}%)",
            str(rband.get("plain") or "")[:220],
        )

    _section_title(pdf, "Three risk flags", y_pad=1.0)
    for k in receipt.get("killers") or []:
        _flag_card(pdf, str(k.get("priority") or "NOTE"), str(k.get("title") or ""), str(k.get("detail") or ""))
    if receipt.get("share_url"):
        _link_line(pdf, "Interactive share", str(receipt.get("share_url")))
    pdf.ln(0.5)
    _accent_card(
        pdf,
        "PLANNING AID ONLY",
        [str(receipt.get("disclaimer") or "Citeable pre-bid diligence - not a quote or sealed bid.")],
        accent=EMERALD,
        title_size=9,
    )

    # ---- Jurisdiction + parallel clocks (IC / interconnection consultant core) ----
    findings = package.get("site_findings") or {}
    clocks_track = package.get("parallel_clocks_track") or {}
    _begin_section(pdf, f"3. Parallel clocks & jurisdiction — {site}", min_remain=32)
    if clocks_track.get("enabled") or clocks_track.get("clocks") or findings.get("parallel_clocks"):
        _muted(
            pdf,
            str(
                clocks_track.get("headline")
                or (
                    "AHJ permits, utility interconnection / large-load, and water/NPDES run as "
                    "independent clocks. Slip on any path moves bid / LOI risk."
                )
            ),
        )
        for c in clocks_track.get("clocks") or findings.get("parallel_clocks") or []:
            if not isinstance(c, dict):
                continue
            track = str(c.get("track") or "").strip()
            name = str(c.get("name") or c.get("label") or "Path")
            title = f"[{track}] {name}" if track else name
            bits = [str(c.get("detail") or c.get("note") or "")]
            if c.get("owner"):
                bits.append(f"Owner: {c.get('owner')}")
            _accent_card(pdf, title, bits, accent=PURPLE, title_size=9)
    else:
        clocks = findings.get("parallel_clocks") or []
        if clocks:
            _muted(
                pdf,
                "Municipal AHJ permits and utility interconnection often run on independent clocks. "
                "Slip on either path moves bid risk.",
            )
            for c in clocks:
                if not isinstance(c, dict):
                    continue
                _accent_card(
                    pdf,
                    str(c.get("name") or c.get("label") or "Path"),
                    [str(c.get("detail") or c.get("note") or "")],
                    accent=PURPLE,
                    title_size=9,
                )

    power = findings.get("power_path") if isinstance(findings.get("power_path"), dict) else {}
    if power.get("headline") or power.get("notes") or power.get("status") or power.get("checklist"):
        _section_title(pdf, "Power / interconnection path", y_pad=1.0)
        bits = []
        if power.get("status"):
            bits.append(f"Status: {power.get('status')}")
        if power.get("headline"):
            bits.append(str(power.get("headline")))
        if power.get("notes"):
            bits.append(str(power.get("notes")))
        for item in (power.get("checklist") or [])[:6]:
            bits.append(f"• {item}")
        if power.get("disclaimer"):
            bits.append(str(power.get("disclaimer")))
        _accent_card(pdf, "Power path (confirm with utility / TDSP)", bits, accent=SKY, title_size=9)
        if power.get("source_url"):
            _link_line(pdf, "Source", str(power.get("source_url")))

    mora = findings.get("moratorium_radar") if isinstance(findings.get("moratorium_radar"), dict) else {}
    if mora.get("headline") or mora.get("detail") or mora.get("status") or mora.get("metros"):
        _section_title(pdf, "Moratorium / pause radar", y_pad=1.0)
        bits = []
        if mora.get("status"):
            bits.append(f"Status: {mora.get('status')}")
        if mora.get("headline"):
            bits.append(str(mora.get("headline")))
        if mora.get("detail"):
            bits.append(str(mora.get("detail")))
        for m in (mora.get("metros") or [])[:4]:
            if isinstance(m, dict):
                bits.append(f"{m.get('name') or 'Metro'}: {m.get('status') or ''}".strip(": "))
        if mora.get("disclaimer"):
            bits.append(str(mora.get("disclaimer")))
        _accent_card(pdf, "Moratorium radar", bits, accent=AMBER, title_size=9)
        if mora.get("source_url"):
            _link_line(pdf, "Source", str(mora.get("source_url")))
        for m in (mora.get("metros") or [])[:3]:
            if isinstance(m, dict) and m.get("citation_url"):
                _link_line(pdf, str(m.get("name") or "Metro"), str(m.get("citation_url")))

    ultra = findings.get("ultralocal") if isinstance(findings.get("ultralocal"), dict) else {}
    if ultra.get("enabled") or ultra.get("summary") or ultra.get("confirmed_pages"):
        _section_title(pdf, "Ultralocal scout (HOA / MUD / township)", y_pad=1.0)
        bits = []
        if ultra.get("depth"):
            bits.append(f"Depth: {ultra.get('depth')}")
        if ultra.get("summary"):
            bits.append(str(ultra.get("summary")))
        _accent_card(
            pdf,
            "Local + ultralocal overlays merged into killers",
            bits or ["Ultralocal scout enabled for this site."],
            accent=EMERALD,
            title_size=9,
        )
        for pg in (ultra.get("confirmed_pages") or [])[:4]:
            if isinstance(pg, dict) and pg.get("url"):
                _link_line(pdf, str(pg.get("title") or "Confirmed page"), str(pg.get("url")))

    ahj = findings.get("ahj") or {}
    _section_title(pdf, "Authority having jurisdiction", y_pad=1.0)
    ahj_lines = [str(ahj.get("name") or cover.get("ahj_name") or "Local AHJ")]
    if ahj.get("last_verified"):
        ahj_lines.append(f"Last verified: {ahj.get('last_verified')}")
    if ahj.get("notes"):
        ahj_lines.append(str(ahj.get("notes")))
    if findings.get("coverage_note"):
        ahj_lines.append(str(findings.get("coverage_note")))
    _accent_card(pdf, ahj_lines[0], ahj_lines[1:], accent=EMERALD, title_size=9)
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
        _section_title(pdf, "Fee & timeline extracts (confirm on schedule)", y_pad=1.0)
        for f in fees:
            amt = f.get("amount")
            title = str(f.get("name") or "Fee")
            if f.get("trade"):
                title = f"[{str(f.get('trade')).upper()}] {title}"
            if amt:
                title = f"{title}  -  {amt}"
            if f.get("exhibit_id"):
                title = f"{title}  [{f.get('exhibit_id')}]"
            cite = f.get("source_label") or ("Source" if f.get("source_url") else "Unverified - confirm with AHJ")
            _accent_card(pdf, title, [str(f.get("note") or ""), cite], accent=AMBER_SOFT, title_size=9)
            if f.get("source_url"):
                _link_line(pdf, "Source", f.get("source_url"))

    insp = findings.get("inspection_sequence") or []
    if insp:
        _section_title(pdf, "Inspection sequence", y_pad=1.0)
        _accent_card(
            pdf,
            "From live city pack",
            [f"{i}. {step}" for i, step in enumerate(insp, start=1)],
            accent=EMERALD,
            title_size=9,
        )

    docs = findings.get("document_checklist") or []
    if docs:
        _section_title(pdf, "Document checklist", y_pad=1.0)
        lines = []
        for d in docs:
            if isinstance(d, dict):
                task = d.get("task") or "Document"
                note = d.get("note") or ""
                lines.append(f"[ ] {task}" + (f" - {note}" if note else ""))
            else:
                lines.append(f"[ ] {d}")
        _accent_card(pdf, "Submittals to confirm with AHJ", lines, accent=EMERALD, title_size=9)

    cards = findings.get("gotcha_cards") or findings.get("gotchas") or []
    if cards:
        _section_title(pdf, "Local gotcha confirm cards", y_pad=1.0)
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
                title_size=9,
            )

    if findings.get("env_risk") or findings.get("env_findings"):
        env_lines = []
        if findings.get("env_risk"):
            env_lines.append(f"Risk level: {findings.get('env_risk')}")
        for f in findings.get("env_findings") or []:
            line = f"{f.get('category')}: {f.get('description')}"
            if f.get("risk_level"):
                line = f"[{f.get('risk_level')}] {line}"
            env_lines.append(line)
        _accent_card(pdf, "Environmental screening", env_lines, accent=SKY, title_size=9)
        for f in findings.get("env_findings") or []:
            if isinstance(f, dict) and f.get("source_url"):
                _link_line(pdf, str(f.get("category") or "Env source"), str(f.get("source_url")))

    # ---- Punch ----
    punch = package.get("punch_list") or {}
    _begin_section(pdf, f"4. Critical-path punch list — {site}", min_remain=28)
    if punch.get("timeline_summary"):
        _muted(pdf, f"Timeline summary: {punch.get('timeline_summary')}")
    items = punch.get("items") or []
    if not items:
        _muted(pdf, "No punch-list items in this package payload.")
    _muted(pdf, f"{len(items)} punch-list line(s) — full operational checklist for this site.")
    for item in items:
        cost = item.get("estimated_cost")
        cost_s = f"  ·  est ${cost:,.0f}" if isinstance(cost, (int, float)) and cost else ""
        ex_id = f"  [{item.get('exhibit_id')}]" if item.get("exhibit_id") else ""
        _flag_card(
            pdf,
            str(item.get("priority") or "NOTE"),
            f"{item.get('task')}{cost_s}{ex_id}",
            f"Timing: {item.get('timeline') or 'Pre-bid'}  |  {item.get('citation') or 'Unverified'}",
        )
        if item.get("source_url"):
            _link_line(pdf, "Source", str(item.get("source_url")))

    # ---- Evidence binder ----
    binder = package.get("evidence_binder") if isinstance(package.get("evidence_binder"), dict) else {}
    exhibits = binder.get("exhibits") or []
    claims = binder.get("claims") or []
    summary = binder.get("summary") if isinstance(binder.get("summary"), dict) else {}
    _begin_section(pdf, f"5. Evidence binder — {site}", min_remain=28)
    _muted(
        pdf,
        "Numbered exhibits map each citeable claim to a live source URL. "
        "Unverified claims have no exhibit ID — confirm before reliance.",
    )
    if summary:
        _accent_card(
            pdf,
            "Binder summary",
            [
                f"Exhibits: {summary.get('exhibit_count', len(exhibits))}",
                f"Cited claims: {summary.get('exhibited_claims', 0)}",
                f"Unverified claims: {summary.get('unverified_claims', 0)}",
            ],
            accent=EMERALD,
            title_size=9,
        )
    if exhibits:
        _section_title(pdf, "Numbered exhibits", y_pad=1.0)
        for ex_row in exhibits:
            if not isinstance(ex_row, dict):
                continue
            eid = str(ex_row.get("id") or "")
            title = str(ex_row.get("title") or "Exhibit")
            kind = str(ex_row.get("kind") or "")
            _accent_card(
                pdf,
                f"{eid}  ·  {title}",
                [f"Kind: {kind}" if kind else ""],
                accent=EMERALD,
                title_size=9,
            )
            if ex_row.get("url"):
                _link_line(pdf, "URL", str(ex_row.get("url")))
    if claims:
        _section_title(pdf, "Claim → exhibit map (excerpt)", y_pad=1.0)
        for cl in claims[:60]:
            if not isinstance(cl, dict):
                continue
            eid = str(cl.get("exhibit_id") or "UNVERIFIED")
            claim = str(cl.get("label") or cl.get("claim") or cl.get("title") or "Claim")
            status = str(cl.get("status") or "")
            _body(pdf, f"[{eid}] {claim}" + (f"  ({status})" if status else ""), 8)
            if cl.get("source_url"):
                _link_line(pdf, "  ", str(cl.get("source_url")))

    # ---- Next actions ----
    _begin_section(pdf, f"6. Next actions — {site}", min_remain=24)
    _muted(
        pdf,
        "Boardroom next steps for IC / interconnection consultants and owner’s reps. "
        "The ranked punch list above is the full operational checklist.",
    )
    for a in package.get("action_plan_summary") or []:
        _body(pdf, f"- {a}", 9)
    excerpt = (package.get("action_plan_excerpt") or "").strip()
    if excerpt:
        _section_title(pdf, "Research memo excerpt", y_pad=1.0)
        # Chunk long memo into readable cards
        chunk = excerpt[:4500]
        _accent_card(pdf, "Planning excerpt (not a filing)", [chunk], accent=CARD_EDGE, title_size=9)

    # ---- Sources ----
    _begin_section(pdf, f"7. Source appendix — {site}", min_remain=24)
    _muted(pdf, "Every forwardable claim should resolve to a URL below or be treated as Unverified.")
    sources = package.get("sources") or []
    if not sources:
        _muted(pdf, "No http(s) sources were attached to this analysis.")
    for i, src in enumerate(sources, start=1):
        label = _ascii(f"{i}. {src.get('label') or 'Source'}")[:110]
        url = _ascii(str(src.get("url") or ""))[:140]
        line_h = 8.5 if url else 5.0
        _need_space(pdf, line_h + 1)
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*WHITE)
        pdf.multi_cell(CONTENT_W, 3.6, label)
        if url:
            pdf.set_x(MARGIN)
            pdf.set_font("Helvetica", "", 7.5)
            pdf.set_text_color(*EMERALD)
            pdf.multi_cell(CONTENT_W, 3.4, url)
        pdf.ln(0.4)

    pdf.ln(1.0)
    _accent_card(
        pdf,
        "Disclaimers",
        [str(d) for d in (package.get("disclaimers") or [])],
        accent=AMBER,
        title_size=9,
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
