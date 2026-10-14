"""Full city pack PDF — AHJ, fees, gotchas, inspections. Same dark canvas as Bid Packet."""
from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from pdf_stamp_helpers import short_host as short_host_safe

from bid_packet_pdf import (
    AMBER,
    AMBER_SOFT,
    CARD,
    CARD_EDGE,
    CONTENT_W,
    EMERALD,
    EMERALD_SOFT,
    MARGIN,
    MUTED,
    PAGE_W,
    PURPLE,
    WHITE,
    BidPacketPDF,
    _ascii,
    _body,
    _card_box,
    _ensure_arbitrage,
    _fmt_pct,
    _muted,
    _section_title,
)

logger = logging.getLogger(__name__)


def _fee_rows(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    card = analysis.get("fee_card") if isinstance(analysis.get("fee_card"), dict) else {}
    rows = card.get("fees") or []
    if isinstance(rows, list) and rows:
        return [r for r in rows if isinstance(r, dict)]
    local = analysis.get("local_pack") if isinstance(analysis.get("local_pack"), dict) else {}
    raw = local.get("fees") or []
    out = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        out.append(
            {
                "label": r.get("label") or r.get("name") or "Fee line",
                "detail": r.get("detail") or "",
                "amount_usd": r.get("amount_usd"),
                "verified": r.get("verified"),
                "source_url": r.get("source_url") or r.get("citation_url"),
                "source_label": r.get("source_label") or r.get("citation_note"),
                "trade": r.get("trade"),
            }
        )
    return out


def _gotcha_rows(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    watch = analysis.get("gotcha_watchlist") if isinstance(analysis.get("gotcha_watchlist"), dict) else {}
    items = watch.get("items") or []
    if isinstance(items, list) and items:
        return [g for g in items if isinstance(g, dict)]
    local = analysis.get("local_pack") if isinstance(analysis.get("local_pack"), dict) else {}
    raw = local.get("gotchas") or local.get("items") or []
    return [g for g in raw if isinstance(g, dict)]


def generate_city_pack_pdf(analysis_data: Dict[str, Any], output_path: str | None = None) -> str:
    try:
        from delivery_parity import prepare_analysis_for_delivery

        analysis_data = prepare_analysis_for_delivery(analysis_data)
    except Exception:
        analysis_data = _ensure_arbitrage(analysis_data)

    pi = analysis_data.get("project_info") or {}
    address = _ascii(str(pi.get("address") or "Site"))
    city = _ascii(str(pi.get("city") or ""))
    state = _ascii(str(pi.get("state") or ""))
    zip_code = _ascii(str(pi.get("zip") or ""))
    locality = ", ".join(p for p in (city, state) if p)
    if zip_code:
        locality = f"{locality} {zip_code}".strip()

    band = analysis_data.get("contingency_band") or {}
    ahj = analysis_data.get("ahj_card") or {}
    fee = analysis_data.get("fee_card") or {}
    coverage = analysis_data.get("coverage") or {}
    local_pack = analysis_data.get("local_pack") or {}
    insp = analysis_data.get("inspection_sequence_card") or {}

    low_s = _fmt_pct(band.get("pct_low"))
    mid_s = _fmt_pct(band.get("pct_mid"))
    high_s = _fmt_pct(band.get("pct_high"))

    from artifact_naming import document_display_title, site_line_from_analysis

    site_line = site_line_from_analysis(analysis_data)
    doc_title = document_display_title(site_line, "FULL CITY PACK")

    pdf = BidPacketPDF()
    pdf._footer_label = _ascii(doc_title)[:90]
    try:
        pdf.set_title(_ascii(doc_title)[:120])
        pdf.set_author("Reg Guard")
    except Exception:
        pass
    pdf.add_page()
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.set_y(MARGIN)

    pdf.set_fill_color(*EMERALD)
    pdf.rect(0, 0, PAGE_W, 3.2, "F")
    pdf.set_y(8)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*WHITE)
    pdf.cell(CONTENT_W, 8, "REG GUARD", ln=1)
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*EMERALD_SOFT)
    pdf.multi_cell(CONTENT_W, 4, _ascii(doc_title))
    _muted(
        pdf,
        "Curated local pack  |  Fees, gotchas, AHJ, inspections  |  Planning aid - not a quote",
        8,
    )
    cov_bits = [
        str(coverage.get("badge") or coverage.get("label") or "").strip(),
        str(local_pack.get("tier") or "").replace("_", " ").strip(),
    ]
    cov_line = "  |  ".join(b for b in cov_bits if b)
    if cov_line:
        _muted(pdf, cov_line, 8)

    y0 = pdf.get_y() + 1.5
    pdf.set_fill_color(*CARD)
    pdf.set_draw_color(*EMERALD)
    pdf.rect(MARGIN, y0, CONTENT_W, 18, "DF")
    pdf.set_xy(MARGIN + 4, y0 + 3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*WHITE)
    pdf.cell(CONTENT_W - 8, 5, address[:90], ln=1)
    pdf.set_x(MARGIN + 4)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*MUTED)
    ahj_name = _ascii(str(ahj.get("name") or "Local AHJ (confirm locally)"))
    pdf.cell(CONTENT_W - 8, 4, _ascii(f"{locality}  |  AHJ: {ahj_name}"), ln=1)
    pdf.set_x(MARGIN + 4)
    pdf.set_text_color(*MUTED)
    pdf.cell(
        CONTENT_W - 8,
        4,
        _ascii(f"Generated {datetime.utcnow().strftime('%Y-%m-%d')} UTC"),
        ln=1,
    )
    pdf.set_y(y0 + 20)

    _section_title(pdf, "Contingency band (planning aid)")
    hero_h = 24 if low_s and high_s else 14
    cx, cy = _card_box(pdf, hero_h)
    pdf.set_xy(cx, cy)
    if low_s and high_s:
        pdf.set_font("Helvetica", "B", 22)
        pdf.set_text_color(*EMERALD_SOFT)
        pdf.cell(CONTENT_W - 8, 10, f"+{low_s}%  -  +{high_s}%", ln=1)
        pdf.set_x(cx)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*EMERALD)
        pdf.cell(CONTENT_W - 8, 5, _ascii(f"mid {mid_s}%  -  planning aid - not a quote"), ln=1)
        if band.get("disclaimer"):
            pdf.set_x(cx)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*MUTED)
            pdf.multi_cell(CONTENT_W - 8, 3.5, _ascii(str(band.get("disclaimer"))[:220]))
    else:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*AMBER_SOFT)
        pdf.multi_cell(CONTENT_W - 8, 5, _ascii("Confirm contingency with the AHJ before bid."))
    pdf.set_y(cy + hero_h + 2)

    _section_title(pdf, "AHJ portal & contact")
    _body(pdf, ahj_name, 10, bold=True)
    for kind, key in (("Portal", "portal_url"), ("Fees schedule", "fees_url"), ("Apply", "apply_url")):
        url = str(ahj.get(key) or "").strip()
        if not url:
            continue
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*EMERALD)
        from pdf_stamp_helpers import paint_linked_block

        paint_linked_block(pdf, _ascii(f"{kind}: {url}"), url, width=CONTENT_W, line_h=4.0)
    if ahj.get("phone"):
        _muted(pdf, f"Phone: {ahj.get('phone')}", 8)
    if ahj.get("notes"):
        _muted(pdf, str(ahj.get("notes"))[:240], 8)
    if ahj.get("last_verified"):
        _muted(pdf, f"Last verified: {ahj.get('last_verified')}", 8)

    from pdf_stamp_helpers import (
        citation_badge_and_url,
        stamp_display_grade,
        stamp_plain_text,
    )

    # Stamp — same HOLD language as Bid Packet (never FAIL)
    rg = analysis_data.get("regguard_stamp") if isinstance(analysis_data.get("regguard_stamp"), dict) else {}
    if not rg.get("grade"):
        try:
            from regguard_stamp import apply_regguard_stamp

            analysis_data = apply_regguard_stamp(dict(analysis_data))
            rg = analysis_data.get("regguard_stamp") or {}
        except Exception:
            pass
    grade_raw = str(rg.get("grade") or analysis_data.get("stamp_grade") or "").upper()
    display = stamp_display_grade(grade_raw)
    if display in ("CLEAR", "CAUTION", "HOLD"):
        pdf.ln(0.5)
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*(AMBER if display == "HOLD" else (AMBER_SOFT if display == "CAUTION" else EMERALD_SOFT)))
        pdf.cell(CONTENT_W, 6, _ascii(f"REGGUARD STAMP: {display}"), ln=1)
        plain = stamp_plain_text(rg, grade=grade_raw)
        if plain:
            _muted(pdf, plain[:220], 8)

    # Document checklist — Pro city pack should not feel empty
    docs = (analysis_data.get("document_checklist") or {}).get("items") or []
    if isinstance(docs, list) and docs:
        _section_title(pdf, "Document / submittal checklist")
        for d in docs[:12]:
            task = d.get("task") if isinstance(d, dict) else str(d)
            _body(pdf, f"[ ] {task}", 8)

    fees = _fee_rows(analysis_data)
    # Also merge AHJ fee table + punch-list fee lines so the pack is not scant
    ahj_block = analysis_data.get("ahj") if isinstance(analysis_data.get("ahj"), dict) else {}
    for r in ahj_block.get("ahj_fee_table") or []:
        if isinstance(r, dict) and r not in fees:
            fees.append(r)
    punch = analysis_data.get("punch_list") if isinstance(analysis_data.get("punch_list"), dict) else {}
    for r in punch.get("ahj_fee_lines") or []:
        if not isinstance(r, dict):
            continue
        fees.append(
            {
                "label": r.get("label") or r.get("name") or r.get("task") or "AHJ fee line",
                "amount_usd": r.get("amount_usd") or r.get("usd"),
                "detail": r.get("detail") or "",
                "verified": r.get("verified"),
                "source_url": r.get("source_url") or r.get("citation_url"),
                "source_label": r.get("source_label") or r.get("citation_note"),
                "trade": r.get("trade"),
            }
        )
    _section_title(pdf, "Fee & timeline extract")
    timeline = str(fee.get("timeline") or (analysis_data.get("summary") or {}).get("estimated_timeline") or "Confirm with AHJ")
    _body(pdf, f"Timeline: {timeline}", 9, bold=True)
    if not fees:
        _muted(pdf, "No fee rows in this pack - confirm on the official AHJ fee schedule.")
    for row in fees[:18]:
        if not isinstance(row, dict):
            continue
        if pdf.get_y() > 255:
            pdf.add_page()
            pdf.set_y(MARGIN + 4)
        amt = row.get("amount_usd")
        amt_s = f"${amt:,.0f}" if isinstance(amt, (int, float)) else "confirm on schedule"
        ver, cite_url = citation_badge_and_url(row)
        label = str(row.get("label") or row.get("name") or "Fee")[:80]
        trade = str(row.get("trade") or "").strip()
        prefix = f"[{trade}] " if trade else ""
        color = EMERALD if ver.startswith("SOURCE") else (PURPLE if cite_url else AMBER_SOFT)
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*color)
        badge = f"[{ver}]"
        bw = min(48, pdf.get_string_width(badge) + 3)
        pdf.cell(bw, 4.2, _ascii(badge), ln=0)
        if cite_url:
            try:
                pdf.link(MARGIN, pdf.get_y(), bw, 4.2, cite_url)
            except Exception:
                pass
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*WHITE)
        pdf.multi_cell(CONTENT_W - bw, 4.2, _ascii(f"{prefix}{label}: {amt_s}"))
        # Always name the source — never a bare [Source] with nothing after
        src_name = str(row.get("source_label") or row.get("citation_note") or "").strip()
        if cite_url or src_name:
            pdf.set_x(MARGIN + 4)
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*EMERALD)
            line = src_name if src_name else "Official schedule / portal"
            if cite_url:
                line = f"{line} — {cite_url}"
            from pdf_stamp_helpers import paint_linked_block

            paint_linked_block(
                pdf,
                _ascii(line[:160]),
                cite_url or None,
                width=CONTENT_W - 8,
                line_h=3.3,
            )

    gotchas = _gotcha_rows(analysis_data)
    killers = [k for k in (analysis_data.get("margin_killers") or []) if isinstance(k, dict)]
    _section_title(pdf, "Local gotcha watchlist")
    if not gotchas and killers:
        gotchas = killers
    if not gotchas:
        _muted(pdf, "No curated gotchas in this pack - verify with AHJ.")
    for g in gotchas[:14]:
        if pdf.get_y() > 250:
            pdf.add_page()
            pdf.set_y(MARGIN + 4)
        pri = str(g.get("priority") or "WATCH").upper()
        title = str(g.get("title") or "")
        ver, cite_url = citation_badge_and_url(g)
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*AMBER if pri in ("HIGH", "CRITICAL", "HOLD") else WHITE)
        pdf.cell(22, 4.4, f"[{pri}]", ln=0)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*WHITE)
        pdf.multi_cell(CONTENT_W - 22, 4.4, _ascii(title))
        if g.get("detail"):
            _muted(pdf, str(g.get("detail"))[:280], 8)
        src_name = str(g.get("source_label") or "").strip()
        if cite_url or src_name or ver != "UNVERIFIED":
            pdf.set_x(MARGIN)
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_text_color(*EMERALD if cite_url else AMBER_SOFT)
            badge = f"[{ver}]"
            pdf.cell(min(48, pdf.get_string_width(badge) + 2), 3.5, _ascii(badge), ln=0)
            if cite_url:
                try:
                    pdf.link(MARGIN, pdf.get_y(), 48, 3.5, cite_url)
                except Exception:
                    pass
            pdf.set_font("Helvetica", "", 7)
            pdf.set_text_color(*EMERALD if cite_url else MUTED)
            line = src_name or (cite_url[:100] if cite_url else "Confirm with AHJ")
            if cite_url and src_name:
                line = f"{src_name} — {cite_url[:90]}"
            from pdf_stamp_helpers import paint_linked_block

            paint_linked_block(
                pdf,
                _ascii(line),
                cite_url or None,
                width=CONTENT_W - 50,
                line_h=3.5,
            )

    steps = insp.get("steps") if isinstance(insp, dict) else None
    if isinstance(steps, list) and steps:
        _section_title(pdf, insp.get("title") or "Inspection sequence")
        for i, step in enumerate(steps[:16], 1):
            _body(pdf, f"{i}. {step}", 9)

    # Punch ranked / critical path — denser Pro desk
    ranked = punch.get("ranked") if isinstance(punch.get("ranked"), list) else []
    if not ranked:
        ranked = punch.get("punch_list") if isinstance(punch.get("punch_list"), list) else []
    if ranked:
        _section_title(pdf, "Punch / critical path (city desk)")
        for item in ranked[:10]:
            if pdf.get_y() > 250:
                pdf.add_page()
                pdf.set_y(MARGIN + 4)
            if not isinstance(item, dict):
                _body(pdf, f"- {item}", 8)
                continue
            title = str(item.get("task") or item.get("title") or item.get("label") or "Punch item")
            pri = str(item.get("priority") or item.get("severity") or "").upper().replace("FAIL", "HOLD")
            owner = str(item.get("owner") or item.get("who") or "").strip()
            due = str(item.get("due") or item.get("timing") or "").strip()
            bit = f"[{pri}] {title}" if pri else title
            if owner:
                bit += f"  |  owner: {owner}"
            if due:
                bit += f"  |  {due}"
            _body(pdf, bit, 8)
            ver, cite_url = citation_badge_and_url(item)
            src_name = str(item.get("source_label") or item.get("citation_note") or "").strip()
            if cite_url or src_name or ver != "UNVERIFIED":
                pdf.set_x(MARGIN + 4)
                pdf.set_font("Helvetica", "", 7)
                pdf.set_text_color(*EMERALD if cite_url else MUTED)
                line = src_name or (short_host_safe(cite_url) if cite_url else ver)
                if cite_url and src_name:
                    line = f"{src_name} - {cite_url[:90]}"
                elif cite_url and not src_name:
                    line = f"{ver} - {cite_url[:100]}"
                pdf.multi_cell(CONTENT_W - 8, 3.2, _ascii(line))
                if cite_url:
                    try:
                        pdf.link(MARGIN + 4, pdf.get_y() - 3.2, CONTENT_W - 8, 3.2, cite_url)
                    except Exception:
                        pass

    who_call = punch.get("who_to_call") if isinstance(punch.get("who_to_call"), list) else []
    if who_call:
        _section_title(pdf, "Who to call")
        for row in who_call[:8]:
            if isinstance(row, dict):
                name = row.get("name") or row.get("role") or row.get("agency") or "Contact"
                phone = row.get("phone") or row.get("tel") or ""
                note = row.get("note") or row.get("detail") or ""
                line = f"{name}"
                if phone:
                    line += f"  |  {phone}"
                if note:
                    line += f"  -  {str(note)[:80]}"
                _body(pdf, line, 8)
            else:
                _body(pdf, str(row), 8)

    env = analysis_data.get("environmental_screening")
    if isinstance(env, dict) and any(env.get(k) for k in ("findings", "risks", "summary", "flags", "layers")):
        _section_title(pdf, "Environmental screening (planning aid)")
        summary = env.get("summary") or env.get("headline") or env.get("note")
        if summary:
            _body(pdf, str(summary)[:280], 8)
        findings = env.get("findings") or env.get("risks") or env.get("flags") or env.get("layers") or []
        if isinstance(findings, list):
            for f in findings[:8]:
                if isinstance(f, dict):
                    _body(pdf, f"- {f.get('title') or f.get('name') or f.get('layer') or f}", 8)
                    if f.get("detail"):
                        _muted(pdf, str(f.get("detail"))[:180], 7)
                else:
                    _body(pdf, f"- {f}", 8)

    fed = analysis_data.get("federal_card") if isinstance(analysis_data.get("federal_card"), dict) else {}
    if fed:
        _section_title(pdf, fed.get("title") or "Federal / overlay notes")
        for key in ("summary", "note", "detail", "headline"):
            if fed.get(key):
                _body(pdf, str(fed.get(key))[:280], 8)
                break
        for item in (fed.get("items") or fed.get("flags") or [])[:6]:
            if isinstance(item, dict):
                _body(pdf, f"- {item.get('title') or item.get('label') or item}", 8)
            else:
                _body(pdf, f"- {item}", 8)

    friction = analysis_data.get("community_friction")
    if isinstance(friction, dict) and (friction.get("summary") or friction.get("items") or friction.get("score") is not None):
        _section_title(pdf, "Community / political friction")
        if friction.get("summary"):
            _body(pdf, str(friction.get("summary"))[:280], 8)
        for item in (friction.get("items") or friction.get("flags") or [])[:6]:
            if isinstance(item, dict):
                _body(pdf, f"- {item.get('title') or item.get('label') or item}", 8)
            else:
                _body(pdf, f"- {item}", 8)

    next_steps = analysis_data.get("next_steps")
    if isinstance(next_steps, list) and next_steps:
        _section_title(pdf, "Next steps before bid")
        for i, step in enumerate(next_steps[:10], 1):
            if isinstance(step, dict):
                _body(pdf, f"{i}. {step.get('task') or step.get('title') or step.get('step') or step}", 8)
            else:
                _body(pdf, f"{i}. {step}", 8)
    elif isinstance(next_steps, dict) and next_steps.get("items"):
        _section_title(pdf, "Next steps before bid")
        for i, step in enumerate(next_steps.get("items")[:10], 1):
            _body(pdf, f"{i}. {step if not isinstance(step, dict) else step.get('task') or step}", 8)

    # Named sources index — never bare [Source]
    sources: List[Any] = []
    for s in local_pack.get("sources") or []:
        sources.append(s)
    su = analysis_data.get("source_urls")
    if isinstance(su, list):
        sources.extend(su)
    elif isinstance(su, dict):
        sources.extend([{"label": k, "url": v} for k, v in su.items()])
    if sources:
        _section_title(pdf, "Source index (named)")
        seen = set()
        for s in sources[:16]:
            if pdf.get_y() > 255:
                pdf.add_page()
                pdf.set_y(MARGIN + 4)
            if isinstance(s, dict):
                label = str(s.get("label") or s.get("name") or s.get("title") or "Official source").strip()
                url = str(s.get("url") or s.get("source_url") or "").strip()
            else:
                label, url = "Official source", str(s).strip()
                if url.startswith("http"):
                    label = short_host_safe(url)
            key = (label, url)
            if key in seen:
                continue
            seen.add(key)
            pdf.set_x(MARGIN)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*WHITE)
            pdf.multi_cell(CONTENT_W, 3.8, _ascii(label[:100]))
            if url:
                pdf.set_x(MARGIN)
                pdf.set_font("Helvetica", "", 7)
                pdf.set_text_color(*EMERALD)
                from pdf_stamp_helpers import paint_linked_block

                paint_linked_block(pdf, _ascii(url[:140]), url, width=CONTENT_W, line_h=3.3)

    pdf.ln(3)
    pdf.set_fill_color(*CARD)
    pdf.set_draw_color(*CARD_EDGE)
    yb = pdf.get_y()
    pdf.rect(MARGIN, yb, CONTENT_W, 16, "DF")
    pdf.set_xy(MARGIN + 4, yb + 3)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*EMERALD_SOFT)
    pdf.cell(CONTENT_W - 8, 4, "PLANNING AID ONLY", ln=1)
    pdf.set_x(MARGIN + 4)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(
        CONTENT_W - 8,
        3.5,
        _ascii(
            "Full city pack is citeable local diligence - not a quote or sealed bid. "
            "Confirm every fee and Unverified line with the AHJ before bid. "
            "app.regguardagent.com"
        ),
    )

    if not output_path:
        out_dir = Path(os.getenv("REGGUARD_DATA_DIR") or "/tmp/regguard_data") / "city_packs"
        out_dir.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() else "_" for c in address)[:40]
        output_path = str(
            out_dir / f"city_pack_{safe}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    pdf.output(output_path)
    logger.info("Full city pack PDF -> %s", output_path)
    return output_path


def generate_city_pack_pdf_bytes(analysis: Dict[str, Any]) -> bytes:
    with tempfile.TemporaryDirectory(prefix="city_pack_") as tmp:
        path = os.path.join(tmp, "RegGuard_Full_City_Pack.pdf")
        generate_city_pack_pdf(analysis, output_path=path)
        raw = Path(path).read_bytes()
    if raw[:4] != b"%PDF":
        raise RuntimeError("City pack PDF generation failed")
    return raw
