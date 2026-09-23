"""
Estimator-ready Excel workbook for the IC Diligence Bundle.

Sheets: Fees | Punch | Evidence
Professional layout: freeze header, auto-filter, USD format, live hyperlinks.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional, Sequence, Tuple

from bid_sheet_export import (
    _due_window,
    _exhibit_map,
    _owner_for_punch,
    _trade_for_punch,
)


# Slate / emerald — matches Bid Risk Receipt branding without looking generic-purple
_HEADER_FILL = "0F172A"
_HEADER_FONT = "F8FAFC"
_ACCENT = "10B981"
_ALT_ROW = "F1F5F9"
_TAB_FEES = "059669"
_TAB_PUNCH = "D97706"
_TAB_EVIDENCE = "0284C7"


def _site_line(analysis: Dict[str, Any]) -> str:
    pi = analysis.get("project_info") or {}
    return " ".join(
        str(pi.get(k) or "").strip()
        for k in ("address", "city", "state", "zip")
        if pi.get(k)
    ).strip() or "Site"


_HEADER_DISPLAY = {
    "trade": "Trade",
    "owner": "Owner",
    "due_window": "Due window",
    "priority": "Priority",
    "item": "Item",
    "cost_code": "Cost code",
    "qty": "Qty",
    "unit": "Unit",
    "crew_rate": "Crew rate",
    "planning_usd": "Planning USD",
    "timeline": "Timeline",
    "exhibit_id": "Exhibit ID",
    "source_url": "Source URL",
    "source_label": "Source label",
    "verified": "Verified",
    "notes": "Notes",
    "row_type": "Row type",
    "claim_type": "Claim type",
    "label": "Label",
    "detail": "Detail",
    "status": "Status",
    "site": "Site",
    "kind": "Kind",
    "title": "Title",
}


def _display_header(key: str) -> str:
    return _HEADER_DISPLAY.get(key, key.replace("_", " ").title())


def _fee_planning_usd(fee: Dict[str, Any]) -> Optional[float]:
    amt = fee.get("amount_usd")
    if isinstance(amt, (int, float)):
        return float(amt)
    return None


def _as_rows_from_csv_sections(analysis: Dict[str, Any]) -> Tuple[List[Dict], List[Dict]]:
    """Build fee + punch row dicts (shared logic with CSV columns)."""
    url_to_ex = _exhibit_map(analysis)
    ahj = analysis.get("ahj_card") if isinstance(analysis.get("ahj_card"), dict) else {}
    default_fee_url = str(ahj.get("fees_url") or ahj.get("portal_url") or "").strip()

    def _eid(url: str, existing: Any = "") -> str:
        if existing:
            return str(existing)
        return url_to_ex.get(str(url or "").strip(), "")

    fees: List[Dict[str, Any]] = []
    for fee in ((analysis.get("fee_card") or {}).get("fees")) or []:
        if not isinstance(fee, dict):
            continue
        src = str(fee.get("source_url") or "").strip() or default_fee_url
        note = str(fee.get("detail") or fee.get("note") or fee.get("amount") or "").strip()
        if fee.get("amount_requires_schedule") or _fee_planning_usd(fee) is None:
            if "confirm" not in note.lower():
                note = (note + " | Confirm on AHJ schedule").strip(" |")
        fees.append(
            {
                "trade": str(fee.get("trade") or "GENERAL").upper(),
                "owner": fee.get("owner") or "Estimator / Permit runner",
                "due_window": (analysis.get("fee_card") or {}).get("timeline") or "Pre-bid",
                "item": fee.get("label") or fee.get("name") or "Fee",
                "planning_usd": _fee_planning_usd(fee),
                "exhibit_id": _eid(src, fee.get("exhibit_id")),
                "source_url": src,
                "source_label": fee.get("source_label")
                or ("Source" if src else "Unverified — confirm with AHJ"),
                "verified": "yes" if fee.get("verified") else "planning",
                "notes": note or "Planning aid — not a quote; confirm with AHJ",
            }
        )

    punch: List[Dict[str, Any]] = []
    for item in ((analysis.get("punch_list") or {}).get("punch_list")) or []:
        if not isinstance(item, dict):
            continue
        src = str(item.get("source_url") or "").strip()
        cost = item.get("estimated_cost")
        punch.append(
            {
                "trade": _trade_for_punch(item) or "GENERAL",
                "owner": _owner_for_punch(item),
                "due_window": _due_window(item) or item.get("timeline") or "Pre-bid",
                "priority": str(item.get("priority") or "").upper(),
                "item": item.get("task") or item.get("title") or "",
                "cost_code": item.get("cost_code") or "",
                "qty": item.get("qty") or item.get("quantity") or "",
                "unit": item.get("unit") or "",
                "crew_rate": item.get("crew_rate") or "",
                "planning_usd": cost if isinstance(cost, (int, float)) else None,
                "timeline": item.get("timeline") or "",
                "exhibit_id": _eid(src, item.get("exhibit_id")),
                "source_url": src,
                "source_label": item.get("source_label") or ("Source" if src else "Unverified"),
                "verified": "yes" if item.get("verified") else "Unverified",
                "notes": "Planning aid — fill qty/crew rates; not a quote.",
            }
        )

    for g in ((analysis.get("gotcha_watchlist") or {}).get("items")) or []:
        if not isinstance(g, dict):
            continue
        src = str(g.get("source_url") or "").strip()
        anti = "; ".join(g.get("anti_patterns") or [])
        punch.append(
            {
                "trade": str(g.get("trade") or "").upper() or "GENERAL",
                "owner": g.get("owner") or "Estimator / PM",
                "due_window": g.get("due_window") or "Pre-bid",
                "priority": str(g.get("priority") or "HIGH").upper(),
                "item": g.get("title") or "",
                "cost_code": g.get("cost_code") or "",
                "qty": "",
                "unit": "",
                "crew_rate": "",
                "planning_usd": None,
                "timeline": "",
                "exhibit_id": _eid(src, g.get("exhibit_id")),
                "source_url": src,
                "source_label": g.get("source_label") or ("Source" if src else "Unverified"),
                "verified": "yes" if src else "Unverified",
                "notes": (g.get("detail") or "") + (f" | Don't: {anti}" if anti else ""),
            }
        )
    return fees, punch



def _evidence_rows(binder: Dict[str, Any], *, site: str = "") -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for ex in binder.get("exhibits") or []:
        if not isinstance(ex, dict):
            continue
        rows.append(
            {
                "row_type": "exhibit",
                "exhibit_id": ex.get("id") or "",
                "claim_type": ex.get("kind") or "",
                "priority": "",
                "trade": "",
                "owner": "",
                "label": ex.get("title") or "",
                "detail": "",
                "status": "EXHIBIT",
                "source_url": ex.get("url") or "",
                "site": site,
            }
        )
    for c in binder.get("claims") or []:
        if not isinstance(c, dict):
            continue
        rows.append(
            {
                "row_type": "claim",
                "exhibit_id": c.get("exhibit_id") or "",
                "claim_type": c.get("claim_type") or "",
                "priority": c.get("priority") or "",
                "trade": c.get("trade") or "",
                "owner": c.get("owner") or "",
                "label": c.get("label") or "",
                "detail": c.get("detail") or "",
                "status": c.get("status") or "",
                "source_url": c.get("source_url") or "",
                "site": site,
            }
        )
    return rows


def _style_header(ws, row: int, cols: int) -> None:
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side

    fill = PatternFill("solid", fgColor=_HEADER_FILL)
    font = Font(name="Calibri", bold=True, color=_HEADER_FONT, size=11)
    thin = Border(
        bottom=Side(style="thin", color=_ACCENT),
    )
    for col in range(1, cols + 1):
        cell = ws.cell(row=row, column=col)
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = thin
    ws.row_dimensions[row].height = 22


def _write_sheet(
    ws,
    *,
    title: str,
    site: str,
    headers: Sequence[str],
    rows: Sequence[Dict[str, Any]],
    url_cols: Sequence[str],
    usd_cols: Sequence[str],
    tab_color: str,
) -> None:
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    ws.sheet_properties.tabColor = tab_color
    ws["A1"] = title
    ws["A1"].font = Font(name="Calibri", bold=True, size=14, color=_HEADER_FILL)
    ws["A2"] = site
    ws["A2"].font = Font(name="Calibri", size=10, color="64748B")
    ws["A3"] = (
        "Planning aid — citeable pre-bid diligence. Not a quote, sealed bid, "
        "interconnection study, or AHJ filing. Confirm fees with the AHJ."
    )
    ws["A3"].font = Font(name="Calibri", italic=True, size=9, color="94A3B8")

    header_row = 5
    for i, h in enumerate(headers, 1):
        ws.cell(row=header_row, column=i, value=_display_header(h))
    _style_header(ws, header_row, len(headers))

    alt = PatternFill("solid", fgColor=_ALT_ROW)
    body_font = Font(name="Calibri", size=10)
    link_font = Font(name="Calibri", size=10, color="0563C1", underline="single")

    for r_i, row in enumerate(rows):
        excel_r = header_row + 1 + r_i
        for c_i, key in enumerate(headers, 1):
            val = row.get(key)
            cell = ws.cell(row=excel_r, column=c_i)
            cell.font = body_font
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            if r_i % 2 == 1:
                cell.fill = alt
            if key in usd_cols and isinstance(val, (int, float)):
                cell.value = float(val)
                cell.number_format = '"$"#,##0'
            elif key in url_cols and val:
                url = str(val).strip()
                cell.value = url
                if url.startswith("http"):
                    cell.hyperlink = url
                    cell.font = link_font
            else:
                cell.value = "" if val is None else val

    # Freeze below title + header
    ws.freeze_panes = f"A{header_row + 1}"
    ws.auto_filter.ref = (
        f"A{header_row}:{get_column_letter(len(headers))}{header_row + max(len(rows), 1)}"
    )

    # Sensible column widths
    width_hints = {
        "trade": 14,
        "owner": 22,
        "due_window": 16,
        "priority": 10,
        "item": 42,
        "label": 36,
        "detail": 40,
        "notes": 36,
        "source_url": 42,
        "exhibit_id": 12,
        "source_label": 22,
        "verified": 12,
        "status": 12,
        "claim_type": 14,
        "row_type": 10,
        "cost_code": 12,
        "qty": 8,
        "unit": 8,
        "crew_rate": 10,
        "planning_usd": 14,
        "timeline": 14,
        "site": 28,
        "kind": 12,
        "title": 40,
    }
    for i, h in enumerate(headers, 1):
        ws.column_dimensions[get_column_letter(i)].width = width_hints.get(h, 14)

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=min(6, len(headers)))
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=min(6, len(headers)))
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=min(8, len(headers)))


def _write_cover(
    wb,
    *,
    workbook_title: str,
    site: str,
    analysis: Dict[str, Any],
    sheet_guide: Sequence[Tuple[str, str]],
) -> None:
    """First-tab briefing — the forward moment for estimators."""
    from openpyxl.styles import Alignment, Font, PatternFill

    ws = wb.create_sheet("Cover", 0)
    ws.sheet_properties.tabColor = _ACCENT
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 72

    rg = analysis.get("regguard_stamp") if isinstance(analysis.get("regguard_stamp"), dict) else {}
    grade = str(rg.get("grade") or analysis.get("stamp_grade") or "").upper()
    stamp = {"FAIL": "HOLD", "PASS": "CLEAR"}.get(grade, grade or "—")
    band = analysis.get("contingency_band") if isinstance(analysis.get("contingency_band"), dict) else {}
    ahj = analysis.get("ahj_card") if isinstance(analysis.get("ahj_card"), dict) else {}
    share = str(analysis.get("share_url") or "").strip()

    low = band.get("pct_low")
    high = band.get("pct_high")
    mid = band.get("pct_mid")
    contingency = ""
    if low is not None and high is not None:
        contingency = f"+{low}% to +{high}%" + (f" (mid {mid}%)" if mid is not None else "")

    title_font = Font(name="Calibri", bold=True, size=16, color=_HEADER_FILL)
    label_font = Font(name="Calibri", bold=True, size=11, color=_HEADER_FILL)
    body = Font(name="Calibri", size=11, color="334155")
    accent = Font(name="Calibri", bold=True, size=14, color=_ACCENT)
    warn = Font(name="Calibri", bold=True, size=11, color="B45309")

    ws["A1"] = workbook_title
    ws["A1"].font = title_font
    ws["B1"] = site
    ws["B1"].font = Font(name="Calibri", size=12, color="64748B")

    ws["A3"] = "RegGuard stamp"
    ws["A3"].font = label_font
    ws["B3"] = stamp
    ws["B3"].font = accent

    ws["A4"] = "Contingency (screenshot / text this)"
    ws["A4"].font = label_font
    ws["B4"] = contingency or "Set after confirming Critical/High items with AHJ"
    ws["B4"].font = accent

    ws["A5"] = "AHJ"
    ws["A5"].font = label_font
    ws["B5"] = str(ahj.get("name") or "Local AHJ")
    ws["B5"].font = body

    ws["A6"] = "Full shareable report"
    ws["A6"].font = label_font
    ws["B6"] = share or "Re-open results in Reg Guard"
    ws["B6"].font = body
    if share.startswith("http"):
        ws["B6"].hyperlink = share
        ws["B6"].font = Font(name="Calibri", size=11, color="0563C1", underline="single")

    ws["A8"] = "How to use (30 seconds)"
    ws["A8"].font = label_font
    ws.merge_cells("B8:B10")
    ws["B8"] = (
        "1) Open Cover — confirm stamp + contingency match the Bid Risk Receipt PDF. "
        "2) Filter Fees / Punch by Trade or Due window. "
        "3) Click Source URL before you lock a number. "
        "4) Forward this file to your estimator or GC — they already live in Excel."
    )
    ws["B8"].font = body
    ws["B8"].alignment = Alignment(wrap_text=True, vertical="top")

    ws["A12"] = "Sheets in this workbook"
    ws["A12"].font = label_font
    r = 13
    for name, blurb in sheet_guide:
        ws.cell(row=r, column=1, value=name).font = Font(name="Calibri", bold=True, size=11, color=_ACCENT)
        ws.cell(row=r, column=2, value=blurb).font = body
        r += 1

    ws.cell(row=r + 1, column=1, value="Honesty").font = label_font
    ws.cell(
        row=r + 1,
        column=2,
        value=(
            "Planning aid — citeable pre-bid diligence. Not a quote, sealed bid, "
            "interconnection study, geotech, or AHJ filing. Unverified lines need confirm-with-AHJ."
        ),
    ).font = warn
    ws.cell(row=r + 1, column=2).alignment = Alignment(wrap_text=True)
    ws.row_dimensions[r + 1].height = 36

    # Light banner fill on stamp row
    fill = PatternFill("solid", fgColor="ECFDF5")
    for col in ("A", "B"):
        ws[f"{col}3"].fill = fill
        ws[f"{col}4"].fill = fill


def analysis_to_fee_punch_evidence_xlsx(
    analysis: Dict[str, Any],
    *,
    binder: Optional[Dict[str, Any]] = None,
    site: str = "",
) -> bytes:
    """
    Return .xlsx bytes with sheets Cover | Fees | Punch | Evidence.
    """
    from openpyxl import Workbook

    data = dict(analysis or {})
    site_line = site or _site_line(data)
    fees, punch = _as_rows_from_csv_sections(data)

    if binder is None:
        try:
            from ic_package_composer import compose_ic_package

            binder = (compose_ic_package(data).get("evidence_binder")) or {}
        except Exception:
            binder = {}

    evidence = _evidence_rows(binder or {}, site=site_line)

    wb = Workbook()
    # Placeholder sheet replaced after Cover is inserted
    default = wb.active
    default.title = "Fees"

    fee_headers = [
        "trade",
        "owner",
        "due_window",
        "item",
        "planning_usd",
        "exhibit_id",
        "source_url",
        "source_label",
        "verified",
        "notes",
    ]
    _write_sheet(
        default,
        title="Fee schedule — estimator desk",
        site=site_line,
        headers=fee_headers,
        rows=fees,
        url_cols=("source_url",),
        usd_cols=("planning_usd",),
        tab_color=_TAB_FEES,
    )

    ws_punch = wb.create_sheet("Punch")
    punch_headers = [
        "trade",
        "owner",
        "due_window",
        "priority",
        "item",
        "cost_code",
        "qty",
        "unit",
        "crew_rate",
        "planning_usd",
        "timeline",
        "exhibit_id",
        "source_url",
        "source_label",
        "verified",
        "notes",
    ]
    _write_sheet(
        ws_punch,
        title="Punch list — trade · owner · due window",
        site=site_line,
        headers=punch_headers,
        rows=punch,
        url_cols=("source_url",),
        usd_cols=("planning_usd",),
        tab_color=_TAB_PUNCH,
    )

    ws_ev = wb.create_sheet("Evidence")
    ev_headers = [
        "row_type",
        "exhibit_id",
        "claim_type",
        "priority",
        "trade",
        "owner",
        "label",
        "detail",
        "status",
        "source_url",
        "site",
    ]
    _write_sheet(
        ws_ev,
        title="Evidence index — claim → exhibit → source",
        site=site_line,
        headers=ev_headers,
        rows=evidence,
        url_cols=("source_url",),
        usd_cols=(),
        tab_color=_TAB_EVIDENCE,
    )

    _write_cover(
        wb,
        workbook_title="Reg Guard — Fee / Punch / Evidence",
        site=site_line,
        analysis=data,
        sheet_guide=[
            ("Fees", "Permit / tap / impact fee types with Source URL and Exhibit ID"),
            ("Punch", "Trade · owner · due window checklist your estimator filters in seconds"),
            ("Evidence", "Every claim mapped to EX-00N + source URL — no orphan screenshots"),
        ],
    )

    buf = io.BytesIO()
    wb.save(buf)
    raw = buf.getvalue()
    if raw[:2] != b"PK":
        raise RuntimeError("Excel workbook generation failed")
    return raw


_EV_HEADERS = (
    "row_type",
    "exhibit_id",
    "claim_type",
    "priority",
    "trade",
    "owner",
    "label",
    "detail",
    "status",
    "source_url",
    "site",
)


def analysis_to_evidence_index_xlsx(
    analysis: Dict[str, Any],
    *,
    binder: Optional[Dict[str, Any]] = None,
    site: str = "",
) -> bytes:
    """
    Standalone evidence-index workbook.

    Sheets:
      Exhibits — numbered exhibit map (EX-00N → source URL)
      Claims   — every cited claim → exhibit_id → source
    """
    from openpyxl import Workbook

    data = dict(analysis or {})
    site_line = site or _site_line(data)

    if binder is None:
        try:
            from ic_package_composer import compose_ic_package

            binder = (compose_ic_package(data).get("evidence_binder")) or {}
        except Exception:
            binder = {}

    binder = binder or {}
    exhibits = [
        {
            "exhibit_id": ex.get("id") or "",
            "kind": ex.get("kind") or "",
            "title": ex.get("title") or "",
            "source_url": ex.get("url") or "",
            "site": site_line,
        }
        for ex in (binder.get("exhibits") or [])
        if isinstance(ex, dict)
    ]
    claims = [
        {
            "exhibit_id": c.get("exhibit_id") or "",
            "claim_type": c.get("claim_type") or "",
            "priority": c.get("priority") or "",
            "trade": c.get("trade") or "",
            "owner": c.get("owner") or "",
            "label": c.get("label") or "",
            "detail": c.get("detail") or "",
            "status": c.get("status") or "",
            "source_url": c.get("source_url") or "",
            "site": site_line,
        }
        for c in (binder.get("claims") or [])
        if isinstance(c, dict)
    ]
    # Combined index (same shape as CSV / Fees workbook Evidence sheet)
    combined = _evidence_rows(binder, site=site_line)

    wb = Workbook()
    ws_ex = wb.active
    ws_ex.title = "Exhibits"
    _write_sheet(
        ws_ex,
        title="Exhibits — numbered source map",
        site=site_line,
        headers=("exhibit_id", "kind", "title", "source_url", "site"),
        rows=exhibits,
        url_cols=("source_url",),
        usd_cols=(),
        tab_color=_TAB_EVIDENCE,
    )

    ws_cl = wb.create_sheet("Claims")
    _write_sheet(
        ws_cl,
        title="Claims — claim → exhibit → source",
        site=site_line,
        headers=(
            "exhibit_id",
            "claim_type",
            "priority",
            "trade",
            "owner",
            "label",
            "detail",
            "status",
            "source_url",
            "site",
        ),
        rows=claims,
        url_cols=("source_url",),
        usd_cols=(),
        tab_color="7C3AED",
    )

    ws_all = wb.create_sheet("Index")
    _write_sheet(
        ws_all,
        title="Full evidence index (exhibits + claims)",
        site=site_line,
        headers=_EV_HEADERS,
        rows=combined,
        url_cols=("source_url",),
        usd_cols=(),
        tab_color="0F172A",
    )

    _write_cover(
        wb,
        workbook_title="Reg Guard — Evidence Index",
        site=site_line,
        analysis=data,
        sheet_guide=[
            ("Exhibits", "Numbered EX-00N map — every source URL counsel can open"),
            ("Claims", "Each claim → exhibit ID → source — no orphan screenshots"),
            ("Index", "Combined exhibits + claims for filter / paste"),
        ],
    )

    buf = io.BytesIO()
    wb.save(buf)
    raw = buf.getvalue()
    if raw[:2] != b"PK":
        raise RuntimeError("Evidence index Excel generation failed")
    return raw
