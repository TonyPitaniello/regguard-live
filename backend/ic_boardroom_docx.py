"""
IC Diligence Package as editable DOCX (counsel / IC redlines).

Keeps source URLs as clickable hyperlinks. Planning aid — not a filing or quote.
"""

from __future__ import annotations

import io
import re
from typing import Any, Dict, List, Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


def _ascii(s: Any) -> str:
    text = str(s or "")
    return (
        text.replace("—", "-")
        .replace("–", "-")
        .replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
    )


def _add_hyperlink(paragraph, text: str, url: str) -> None:
    """Add a clickable hyperlink run to a paragraph."""
    u = (url or "").strip()
    label = _ascii(text or u)[:120]
    if not u.startswith("http"):
        paragraph.add_run(label)
        return
    part = paragraph.part
    from docx.opc.constants import RELATIONSHIP_TYPE as RT

    r_id = part.relate_to(u, RT.HYPERLINK, is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)
    new_run = OxmlElement("w:r")
    rPr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "0563C1")
    rPr.append(color)
    u_el = OxmlElement("w:u")
    u_el.set(qn("w:val"), "single")
    rPr.append(u_el)
    new_run.append(rPr)
    text_el = OxmlElement("w:t")
    text_el.text = label
    new_run.append(text_el)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)


def _heading(doc: Document, text: str, level: int = 1) -> None:
    p = doc.add_heading(_ascii(text), level=level)
    for run in p.runs:
        run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)


def _body(doc: Document, text: str, *, bold: bool = False) -> None:
    p = doc.add_paragraph()
    run = p.add_run(_ascii(text))
    run.bold = bold
    run.font.size = Pt(11)


def _muted(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    run = p.add_run(_ascii(text))
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)


def _link_line(doc: Document, label: str, url: str) -> None:
    u = (url or "").strip()
    if not u:
        return
    p = doc.add_paragraph()
    p.add_run(_ascii(f"{label}: ")).bold = True
    _add_hyperlink(p, u, u)


def generate_ic_boardroom_docx_bytes(
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
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(0.85)
    section.right_margin = Inches(0.85)

    cover = package.get("cover") or {}
    site = _ascii(cover.get("site") or "Project site")
    ex = package.get("executive_summary") or {}
    stamp = ex.get("stamp") or {}
    raw_display = str(stamp.get("display") or stamp.get("grade") or "-").upper()
    display = {"FAIL": "HOLD", "PASS": "CLEAR"}.get(raw_display, raw_display)
    band = ex.get("contingency") if isinstance(ex.get("contingency"), dict) else {}

    _heading(doc, "Reg Guard — IC Diligence Package", 0)
    _body(doc, site, bold=True)
    _muted(
        doc,
        "Planning aid only — not a quote, sealed bid, interconnection study, geotech report, or AHJ filing. "
        "Confirm every fee and timeline with the AHJ before bid.",
    )
    if package.get("generated_at"):
        _muted(doc, f"Generated {package.get('generated_at')}  |  Prepared for {package.get('generated_for') or 'Authorized recipient'}")
    share = str(package.get("share_url") or share_url or "").strip()
    if share:
        _link_line(doc, "Interactive share / re-download", share)

    _heading(doc, f"1. Executive recommendation — {site}", 1)
    stamp_label = str(stamp.get("label") or f"REGGUARD STAMP: {display}").replace("FAIL", "HOLD")
    _body(doc, stamp_label, bold=True)
    if stamp.get("plain") or stamp.get("headline"):
        _body(doc, str(stamp.get("plain") or stamp.get("headline")).replace("FAIL", "HOLD"))
    if stamp.get("valid_until"):
        _muted(doc, f"Valid until {str(stamp.get('valid_until'))[:10]} — re-run before bid submittal.")
    if band.get("pct_low") is not None:
        _body(
            doc,
            f"Suggested contingency: +{band.get('pct_low')}% – +{band.get('pct_high')}% (mid {band.get('pct_mid')}%)",
            bold=True,
        )
        if band.get("plain"):
            _muted(doc, str(band.get("plain")))

    _heading(doc, "Top risk flags", 2)
    for k in (ex.get("top_risks") or [])[:8]:
        pri = str(k.get("priority") or "NOTE").upper().replace("FAIL", "HOLD")
        _body(doc, f"[{pri}] {k.get('title') or 'Item'}", bold=True)
        if k.get("detail"):
            _muted(doc, str(k.get("detail")))
        if k.get("source_url"):
            _link_line(doc, "Source", str(k.get("source_url")))

    receipt = package.get("bid_risk_receipt") or {}
    _heading(doc, f"2. Risk stamp & contingency — {site}", 1)
    _muted(doc, "One-page risk brief for GC / owner / IC war-room.")
    for k in (receipt.get("killers") or [])[:5]:
        pri = str(k.get("priority") or "NOTE").upper().replace("FAIL", "HOLD")
        _body(doc, f"[{pri}] {k.get('title') or ''}", bold=True)
        if k.get("detail"):
            _muted(doc, str(k.get("detail")))
        if k.get("source_url"):
            _link_line(doc, "Source", str(k.get("source_url")))
    if receipt.get("share_url"):
        _link_line(doc, "Interactive share", str(receipt.get("share_url")))

    findings = package.get("site_findings") or {}
    _heading(doc, f"3. Jurisdiction & parallel path — {site}", 1)
    ahj = findings.get("ahj") or {}
    _body(doc, str(ahj.get("name") or cover.get("ahj_name") or "Local AHJ"), bold=True)
    for label, key in (
        ("Portal", "portal_url"),
        ("Fees", "fees_url"),
        ("Apply", "apply_url"),
        ("Inspections", "inspections_url"),
    ):
        if ahj.get(key):
            _link_line(doc, label, str(ahj.get(key)))
    for f in findings.get("fees") or []:
        title = str(f.get("name") or "Fee")
        if f.get("trade"):
            title = f"[{str(f.get('trade')).upper()}] {title}"
        if f.get("amount"):
            title = f"{title} — {f.get('amount')}"
        _body(doc, title, bold=True)
        if f.get("note"):
            _muted(doc, str(f.get("note")))
        cite = f.get("source_label") or "Unverified — confirm with AHJ"
        _muted(doc, str(cite))
        if f.get("source_url"):
            _link_line(doc, "Source", str(f.get("source_url")))

    punch = package.get("punch_list") or {}
    _heading(doc, f"4. Critical-path punch list — {site}", 1)
    if punch.get("timeline_summary"):
        _muted(doc, f"Timeline: {punch.get('timeline_summary')}")
    for item in punch.get("items") or []:
        pri = str(item.get("priority") or "NOTE").upper().replace("FAIL", "HOLD")
        cost = item.get("estimated_cost")
        cost_s = f"  ·  est ${cost:,.0f}" if isinstance(cost, (int, float)) and cost else ""
        _body(doc, f"[{pri}] {item.get('task')}{cost_s}", bold=True)
        owner = item.get("owner") or item.get("responsible_party") or ""
        timing = item.get("timeline") or "Pre-bid"
        bits = [f"Timing: {timing}"]
        if owner:
            bits.append(f"Owner: {owner}")
        if item.get("trade"):
            bits.append(f"Trade: {str(item.get('trade')).upper()}")
        cite = item.get("citation") or item.get("source_label") or "Unverified"
        bits.append(str(cite))
        _muted(doc, "  |  ".join(bits))
        if item.get("source_url"):
            _link_line(doc, "Source", str(item.get("source_url")))

    _heading(doc, f"5. Next actions — {site}", 1)
    for a in package.get("action_plan_summary") or []:
        _body(doc, f"- {a}")

    _heading(doc, f"6. Source appendix — {site}", 1)
    _muted(doc, "Every forwardable claim should resolve to a URL below or be treated as Unverified.")
    for i, src in enumerate(package.get("sources") or [], start=1):
        label = f"{i}. {src.get('label') or 'Source'}"
        p = doc.add_paragraph()
        p.add_run(_ascii(label)).bold = True
        if src.get("url"):
            p2 = doc.add_paragraph()
            _add_hyperlink(p2, str(src.get("url")), str(src.get("url")))

    _heading(doc, "Disclaimers", 1)
    for d in package.get("disclaimers") or []:
        _muted(doc, f"• {d}")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
