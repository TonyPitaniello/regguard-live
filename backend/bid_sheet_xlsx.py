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


def _as_rows_from_csv_sections(analysis: Dict[str, Any]) -> Tuple[List[Dict], List[Dict]]:
    """Build fee + punch row dicts (shared logic with CSV columns)."""
    share = str(analysis.get("share_url") or "").strip()
    url_to_ex = _exhibit_map(analysis)

    def _eid(url: str, existing: Any = "") -> str:
        if existing:
            return str(existing)
        return url_to_ex.get(str(url or "").strip(), "")

    fees: List[Dict[str, Any]] = []
    for fee in ((analysis.get("fee_card") or {}).get("fees")) or []:
        if not isinstance(fee, dict):
            continue
        src = str(fee.get("source_url") or "").strip()
        note = fee.get("detail") or ""
        if fee.get("amount_requires_schedule"):
            note = (str(note) + " | confirm on schedule").strip(" |")
        fees.append(
            {
                "trade": str(fee.get("trade") or "GENERAL").upper(),
                "owner": fee.get("owner") or "Estimator / Permit runner",
                "due_window": (analysis.get("fee_card") or {}).get("timeline") or "Pre-bid",
                "item": fee.get("label") or "Fee",
                "planning_usd": fee.get("amount_usd")
                if isinstance(fee.get("amount_usd"), (int, float))
                else None,
                "exhibit_id": _eid(src, fee.get("exhibit_id")),
                "source_url": src,
                "source_label": fee.get("source_label")
                or ("Source" if src else "Unverified — confirm with AHJ"),
                "verified": "yes" if fee.get("verified") else "planning",
                "notes": note or "Planning aid — not a quote; confirm with AHJ",
                "share_url": share,
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
                "trade": _trade_for_punch(item),
                "owner": _owner_for_punch(item),
                "due_window": _due_window(item),
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
                "share_url": share,
            }
        )

    for g in ((analysis.get("gotcha_watchlist") or {}).get("items")) or []:
        if not isinstance(g, dict):
            continue
        src = str(g.get("source_url") or "").strip()
        anti = "; ".join(g.get("anti_patterns") or [])
        punch.append(
            {
                "trade": str(g.get("trade") or "").upper(),
                "owner": g.get("owner") or "Estimator / PM",
                "due_window": g.get("due_window") or "Pre-bid",
                "priority": g.get("priority") or "HIGH",
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
                "share_url": share,
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
        ws.cell(row=header_row, column=i, value=h)
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
        "share_url": 36,
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
    }
    for i, h in enumerate(headers, 1):
        ws.column_dimensions[get_column_letter(i)].width = width_hints.get(h, 14)

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=min(6, len(headers)))
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=min(6, len(headers)))
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=min(8, len(headers)))


def analysis_to_fee_punch_evidence_xlsx(
    analysis: Dict[str, Any],
    *,
    binder: Optional[Dict[str, Any]] = None,
    site: str = "",
) -> bytes:
    """
    Return .xlsx bytes with sheets Fees, Punch, Evidence.
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
    # Fees
    ws_fees = wb.active
    ws_fees.title = "Fees"
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
        "share_url",
    ]
    _write_sheet(
        ws_fees,
        title="Fee schedule — estimator desk",
        site=site_line,
        headers=fee_headers,
        rows=fees,
        url_cols=("source_url", "share_url"),
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
        "share_url",
    ]
    _write_sheet(
        ws_punch,
        title="Punch list — trade · owner · due window",
        site=site_line,
        headers=punch_headers,
        rows=punch,
        url_cols=("source_url", "share_url"),
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

    buf = io.BytesIO()
    wb.save(buf)
    raw = buf.getvalue()
    if raw[:2] != b"PK":
        raise RuntimeError("Evidence index Excel generation failed")
    return raw
