"""Build CSV bid-sheet export from analysis (punch + planning $)."""
from __future__ import annotations

import csv
import io
from typing import Any, Dict, List


def analysis_to_bid_csv(analysis: Dict[str, Any]) -> str:
    """Return CSV text: punch lines + fee planning rows."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "section",
            "priority_or_trade",
            "item",
            "planning_usd",
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
            f"{pi.get('address') or ''} {pi.get('city') or ''} {pi.get('state') or ''} {pi.get('zip') or ''}".strip(),
            "",
            "",
            "",
            "",
            "",
            analysis.get("coverage", {}).get("badge")
            or (analysis.get("jurisdiction") or {}).get("coverage_badge")
            or "",
        ]
    )
    ahj = analysis.get("ahj_card") or {}
    if ahj.get("name"):
        w.writerow(
            [
                "ahj",
                "",
                ahj.get("name"),
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
        w.writerow(
            [
                "punch",
                (item.get("priority") or "").upper(),
                item.get("task") or item.get("title") or "",
                cost if isinstance(cost, (int, float)) else "",
                item.get("timeline") or "",
                item.get("responsible_party") or "",
                item.get("source_url") or "",
                "yes" if item.get("verified") else "no",
                item.get("source_label") or "",
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
        w.writerow(
            [
                "fee",
                fee.get("trade") or "general",
                fee.get("label") or "Fee",
                amt if isinstance(amt, (int, float)) else "",
                (analysis.get("fee_card") or {}).get("timeline") or "",
                "",
                fee.get("source_url") or "",
                "yes" if fee.get("verified") else "planning",
                note,
            ]
        )
    for g in ((analysis.get("gotcha_watchlist") or {}).get("items")) or []:
        if not isinstance(g, dict):
            continue
        anti = "; ".join(g.get("anti_patterns") or [])
        w.writerow(
            [
                "gotcha",
                g.get("priority") or "HIGH",
                g.get("title") or "",
                "",
                "",
                "",
                g.get("source_url") or "",
                "yes" if g.get("source_url") else "no",
                (g.get("detail") or "") + (f" | Don't: {anti}" if anti else ""),
            ]
        )
    band = analysis.get("contingency_band") or {}
    if band.get("pct_mid") is not None:
        w.writerow(
            [
                "contingency",
                "planning",
                band.get("label") or "Suggested contingency",
                band.get("usd_mid") if isinstance(band.get("usd_mid"), (int, float)) else "",
                f"{band.get('pct_low')}%-{band.get('pct_high')}% (mid {band.get('pct_mid')}%)",
                "",
                "",
                "heuristic",
                band.get("disclaimer") or "Planning aid — not a quote",
            ]
        )
    return buf.getvalue()
