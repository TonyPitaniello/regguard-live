"""Build CSV bid-sheet export from analysis (punch + planning $)."""
from __future__ import annotations

import csv
import io
from typing import Any, Dict, List


def _cost_code_hint(section: str, trade: str = "", item: str = "") -> str:
    """Blank column for your estimate workbook — never invent real cost codes."""
    blob = f"{section} {trade} {item}".lower()
    if section == "fee":
        return ""  # leave blank for estimator mapping
    if section == "punch":
        return ""
    if section == "gotcha":
        return ""
    if section == "contingency":
        return ""
    if "electrical" in blob or "elec" in blob:
        return ""
    return ""


def analysis_to_bid_csv(analysis: Dict[str, Any]) -> str:
    """Return CSV text: punch lines + fee planning rows + cost_code placeholders."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "section",
            "cost_code",
            "priority_or_trade",
            "item",
            "qty",
            "unit",
            "crew_rate",
            "planning_usd",
            "tax",
            "bond_allowance",
            "timeline",
            "responsible",
            "source_url",
            "verified",
            "notes",
        ]
    )
    pi = analysis.get("project_info") or {}
    w.writerow(
        [
            "site",
            "",
            "",
            f"{pi.get('address') or ''} {pi.get('city') or ''} {pi.get('state') or ''} {pi.get('zip') or ''}".strip(),
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            analysis.get("coverage", {}).get("badge")
            or (analysis.get("jurisdiction") or {}).get("coverage_badge")
            or "Citeable pre-bid diligence — not a sealed bid",
        ]
    )
    ahj = analysis.get("ahj_card") or {}
    if ahj.get("name"):
        w.writerow(
            [
                "ahj",
                "",
                "",
                ahj.get("name"),
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                ahj.get("fees_url") or ahj.get("portal_url") or "",
                ahj.get("last_verified") or "",
                "Confirm fees on official schedule",
            ]
        )
    punch = ((analysis.get("punch_list") or {}).get("punch_list")) or []
    for item in punch:
        if not isinstance(item, dict):
            continue
        cost = item.get("estimated_cost")
        trade = (item.get("trade") or item.get("priority") or "").upper()
        task = item.get("task") or item.get("title") or ""
        w.writerow(
            [
                "punch",
                item.get("cost_code") or _cost_code_hint("punch", trade, task),
                trade,
                task,
                item.get("qty") or item.get("quantity") or "",
                item.get("unit") or "",
                item.get("crew_rate") or "",
                cost if isinstance(cost, (int, float)) else "",
                item.get("tax") or "",
                item.get("bond_allowance") or "",
                item.get("timeline") or "",
                item.get("responsible_party") or "",
                item.get("source_url") or "",
                "yes" if item.get("verified") else "Unverified",
                item.get("source_label")
                or "Planning aid — fill qty/crew rates; not a quote",
            ]
        )
    fees = ((analysis.get("fee_card") or {}).get("fees")) or []
    for fee in fees:
        if not isinstance(fee, dict):
            continue
        amt = fee.get("amount_usd")
        note = fee.get("detail") or ""
        if fee.get("amount_requires_schedule"):
            note = (note + " | confirm on schedule").strip(" |")
        label = fee.get("label") or "Fee"
        trade = fee.get("trade") or "general"
        w.writerow(
            [
                "fee",
                fee.get("cost_code") or _cost_code_hint("fee", trade, label),
                trade,
                label,
                "",
                "",
                "",
                amt if isinstance(amt, (int, float)) else "",
                "",
                "",
                (analysis.get("fee_card") or {}).get("timeline") or "",
                "",
                fee.get("source_url") or "",
                "yes" if fee.get("verified") else "planning",
                note or "Planning aid — not a quote; confirm with AHJ",
            ]
        )
    for g in ((analysis.get("gotcha_watchlist") or {}).get("items")) or []:
        if not isinstance(g, dict):
            continue
        anti = "; ".join(g.get("anti_patterns") or [])
        title = g.get("title") or ""
        w.writerow(
            [
                "gotcha",
                g.get("cost_code") or "",
                g.get("priority") or "HIGH",
                title,
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                g.get("source_url") or "",
                "yes" if g.get("source_url") else "Unverified",
                (g.get("detail") or "") + (f" | Don't: {anti}" if anti else ""),
            ]
        )
    band = analysis.get("contingency_band") or {}
    if band.get("pct_mid") is not None:
        w.writerow(
            [
                "contingency",
                "",
                "planning",
                band.get("label") or "Suggested contingency",
                "",
                "",
                "",
                band.get("usd_mid") if isinstance(band.get("usd_mid"), (int, float)) else "",
                "",
                "",
                f"{band.get('pct_low')}%-{band.get('pct_high')}% (mid {band.get('pct_mid')}%)",
                "",
                "",
                "heuristic",
                band.get("disclaimer")
                or "Planning aid — not a quote or sealed bid; confirm with AHJ",
            ]
        )
    # Explicit blank mapping rows so estimators see columns to fill
    w.writerow(
        [
            "estimator_fill",
            "YOUR_COST_CODE",
            "trade",
            "Labor / material takeoff line (fill in your workbook)",
            "qty",
            "unit",
            "crew_rate",
            "",
            "tax",
            "bond",
            "",
            "",
            "",
            "",
            "Reg Guard does not invent takeoff — citeable pre-bid diligence only",
        ]
    )
    return buf.getvalue()
