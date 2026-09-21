"""
IC Diligence Package — counsel-ready DOCX for IC / sponsor / lender buyers.

Structure (professional deliverable, not a longer PDF):
  A. Document control + cover
  B. One-page decision memo (HOLD/CLEAR + contingency + top 3 drivers + exhibit refs)
  C. Parallel clocks track (AHJ / interconnect / water-NPDES) when data-center / large-load
  D. Fee & punch schedule summary (full CSV ships in the ZIP bundle)
  E. Evidence binder — numbered exhibits with live hyperlinks
  F. Disclaimers

Planning aid only — not a filing, quote, interconnection study, or AHJ approval.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List

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
    u = (url or "").strip()
    label = _ascii(text or u)[:140]
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


def _body(doc: Document, text: str, *, bold: bool = False, size: int = 11) -> None:
    p = doc.add_paragraph()
    run = p.add_run(_ascii(text))
    run.bold = bold
    run.font.size = Pt(size)


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


def _exhibit_ref(exhibit_id: str) -> str:
    eid = (exhibit_id or "").strip()
    return f"[{eid}]" if eid else "[Unverified]"


def generate_ic_boardroom_docx_bytes(
    analysis: Dict[str, Any],
    *,
    generated_for: str = "",
    share_url: str = "",
) -> bytes:
    from artifact_naming import document_display_title
    from ic_package_composer import compose_ic_package

    package = compose_ic_package(
        analysis,
        generated_for=generated_for,
        share_url=share_url,
    )
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.85)
    section.right_margin = Inches(0.85)

    cover = package.get("cover") or {}
    site = _ascii(cover.get("site") or "Project site")
    doc_title = document_display_title(site, "IC DILIGENCE PACKAGE")
    memo = package.get("decision_memo") or {}
    stamp = (memo.get("stamp") or (package.get("executive_summary") or {}).get("stamp") or {})
    raw_display = str(stamp.get("display") or stamp.get("grade") or "-").upper()
    display = {"FAIL": "HOLD", "PASS": "CLEAR"}.get(raw_display, raw_display)
    band = memo.get("contingency") or ((package.get("executive_summary") or {}).get("contingency") or {})
    binder = package.get("evidence_binder") or {}
    clocks_track = package.get("parallel_clocks_track") or {}
    findings = package.get("site_findings") or {}
    punch = package.get("punch_list") or {}

    core = doc.core_properties
    core.title = doc_title[:200]
    core.author = "Reg Guard"
    core.comments = "IC Diligence Package — planning aid for counsel / IC / lender review"

    # ----- Cover / document control -----
    _heading(doc, doc_title, 0)
    _body(doc, "REG GUARD  |  IC PROJECT DELIVERABLE", bold=True, size=12)
    _body(doc, site, bold=True)
    _muted(
        doc,
        "Counsel-ready diligence package for IC / sponsor / lender review. "
        "Planning aid only — not a quote, sealed bid, interconnection study, geotech report, "
        "or AHJ filing. Confirm every fee and timeline with the AHJ before bid.",
    )
    deliverable = package.get("deliverable") or {}
    if deliverable.get("primary"):
        _muted(doc, f"Primary paid deliverable: {deliverable.get('primary')}")
    _muted(
        doc,
        f"Generated {package.get('generated_at') or '-'}  |  "
        f"Prepared for {package.get('generated_for') or 'Authorized recipient'}  |  "
        f"AHJ: {cover.get('ahj_name') or 'Local AHJ'}",
    )
    share = str(package.get("share_url") or share_url or "").strip()
    if share:
        _link_line(doc, "Interactive share / re-download", share)

    _heading(doc, "Contents", 1)
    _body(doc, "A. One-page decision memo (HOLD/CLEAR + contingency + top drivers)")
    _body(doc, "B. Parallel clocks track (AHJ / interconnect / water-NPDES) — when applicable")
    _body(doc, "C. Fee & punch schedule summary (full CSV in ZIP bundle)")
    _body(doc, "D. Evidence binder — numbered exhibits with live source hyperlinks")
    _body(doc, "E. Disclaimers")

    # ----- A. Decision memo -----
    _heading(doc, f"A. One-page decision memo — {site}", 1)
    stamp_label = str(stamp.get("label") or f"REGGUARD STAMP: {display}").replace("FAIL", "HOLD")
    _body(doc, stamp_label, bold=True, size=14)
    if memo.get("recommendation"):
        _body(doc, str(memo.get("recommendation")).replace("FAIL", "HOLD"), bold=True)
    if stamp.get("plain") or stamp.get("headline") or memo.get("headline"):
        _body(
            doc,
            str(memo.get("headline") or stamp.get("plain") or stamp.get("headline")).replace(
                "FAIL", "HOLD"
            ),
        )
    if stamp.get("valid_until"):
        _muted(doc, f"Valid until {str(stamp.get('valid_until'))[:10]} — re-run before bid / LOI.")

    if band and band.get("pct_low") is not None:
        _heading(doc, "Suggested contingency", 2)
        _body(
            doc,
            f"+{band.get('pct_low')}% – +{band.get('pct_high')}%  (mid {band.get('pct_mid')}%)",
            bold=True,
            size=12,
        )
        if band.get("plain"):
            _muted(doc, str(band.get("plain")))

    _heading(doc, "Top 3 drivers (resolve or carry cushion)", 2)
    drivers = memo.get("top_drivers") or (package.get("executive_summary") or {}).get("top_risks") or []
    for i, k in enumerate(drivers[:3], start=1):
        pri = str(k.get("priority") or "NOTE").upper().replace("FAIL", "HOLD")
        ref = _exhibit_ref(str(k.get("exhibit_id") or ""))
        _body(doc, f"{i}. [{pri}] {k.get('title') or 'Driver'}  {ref}", bold=True)
        if k.get("detail"):
            _muted(doc, str(k.get("detail")))
        if k.get("source_url"):
            _link_line(doc, "Source", str(k.get("source_url")))

    # ----- B. Parallel clocks -----
    if clocks_track.get("enabled") or clocks_track.get("clocks") or findings.get("parallel_clocks"):
        _heading(doc, f"B. Parallel clocks track — {site}", 1)
        _body(
            doc,
            str(
                clocks_track.get("headline")
                or "AHJ, interconnection, and water/NPDES can slip independently — treat as parallel clocks."
            ),
            bold=True,
        )
        for c in clocks_track.get("clocks") or findings.get("parallel_clocks") or []:
            track = str(c.get("track") or "").upper()
            name = c.get("name") or "Clock"
            label = f"[{track}] {name}" if track else str(name)
            _body(doc, label, bold=True)
            if c.get("detail"):
                _muted(doc, str(c.get("detail")))
            if c.get("owner"):
                _muted(doc, f"Owner: {c.get('owner')}")

    # ----- C. Fee & punch summary -----
    _heading(doc, f"C. Fee & punch schedule summary — {site}", 1)
    _muted(
        doc,
        "Full estimator schedule (trade / owner / due window / source_url / exhibit_id) ships as CSV "
        "in the IC Diligence ZIP bundle. Below is the boardroom extract.",
    )
    ahj = findings.get("ahj") or {}
    if ahj.get("name"):
        _body(doc, str(ahj.get("name")), bold=True)
        for label, key in (
            ("Portal", "portal_url"),
            ("Fees", "fees_url"),
            ("Apply", "apply_url"),
            ("Inspections", "inspections_url"),
        ):
            if ahj.get(key):
                _link_line(doc, label, str(ahj.get(key)))

    _heading(doc, "Fee planning rows", 2)
    for f in (findings.get("fees") or [])[:15]:
        title = str(f.get("name") or "Fee")
        if f.get("trade"):
            title = f"[{str(f.get('trade')).upper()}] {title}"
        if f.get("amount"):
            title = f"{title} — {f.get('amount')}"
        ref = _exhibit_ref(str(f.get("exhibit_id") or ""))
        _body(doc, f"{title}  {ref}", bold=True)
        if f.get("note"):
            _muted(doc, str(f.get("note")))
        if f.get("source_url"):
            _link_line(doc, "Source", str(f.get("source_url")))

    _heading(doc, "Critical-path punch", 2)
    if punch.get("timeline_summary"):
        _muted(doc, f"Timeline: {punch.get('timeline_summary')}")
    for item in (punch.get("items") or [])[:25]:
        pri = str(item.get("priority") or "NOTE").upper().replace("FAIL", "HOLD")
        cost = item.get("estimated_cost")
        cost_s = f"  ·  est ${cost:,.0f}" if isinstance(cost, (int, float)) and cost else ""
        ref = _exhibit_ref(str(item.get("exhibit_id") or ""))
        _body(doc, f"[{pri}] {item.get('task')}{cost_s}  {ref}", bold=True)
        bits = []
        if item.get("timeline"):
            bits.append(f"Due: {item.get('timeline')}")
        owner = item.get("owner") or item.get("responsible_party")
        if owner:
            bits.append(f"Owner: {owner}")
        if item.get("trade"):
            bits.append(f"Trade: {str(item.get('trade')).upper()}")
        if bits:
            _muted(doc, "  |  ".join(bits))
        if item.get("source_url"):
            _link_line(doc, "Source", str(item.get("source_url")))

    # ----- D. Evidence binder -----
    _heading(doc, f"D. Evidence binder — {site}", 1)
    summary = binder.get("summary") or {}
    _muted(
        doc,
        f"{summary.get('exhibit_count', 0)} numbered exhibits  |  "
        f"{summary.get('exhibited_claims', 0)} claims with sources  |  "
        f"{summary.get('unverified_claims', 0)} unverified (confirm before reliance).",
    )
    _body(doc, "Exhibits (live hyperlinks)", bold=True)
    for ex in binder.get("exhibits") or []:
        p = doc.add_paragraph()
        p.add_run(_ascii(f"{ex.get('id')} — {ex.get('title') or 'Source'}")).bold = True
        if ex.get("url"):
            p2 = doc.add_paragraph()
            _add_hyperlink(p2, str(ex.get("url")), str(ex.get("url")))

    _body(doc, "Claim → exhibit map", bold=True)
    for c in binder.get("claims") or []:
        status = c.get("status") or "UNVERIFIED"
        eid = c.get("exhibit_id") or "—"
        pri = str(c.get("priority") or "").upper()
        prefix = f"[{pri}] " if pri else ""
        _body(
            doc,
            f"{eid}  |  {status}  |  {c.get('claim_type')}  |  {prefix}{c.get('label')}",
            bold=False,
            size=10,
        )
        if c.get("source_url") and not c.get("exhibit_id"):
            _link_line(doc, "Confirm", str(c.get("source_url")))

    # ----- E. Next actions + disclaimers -----
    _heading(doc, f"E. Recommended next actions — {site}", 1)
    for a in package.get("action_plan_summary") or []:
        _body(doc, f"- {a}")

    _heading(doc, "Disclaimers", 1)
    for d in package.get("disclaimers") or []:
        _muted(doc, f"• {d}")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
