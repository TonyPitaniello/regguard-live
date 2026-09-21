"""Build CSV bid-sheet export from analysis (punch + fees + owner/trade + source URLs)."""
from __future__ import annotations

import csv
import io
from typing import Any, Dict


def _owner_for_punch(item: Dict[str, Any]) -> str:
    return str(
        item.get("owner")
        or item.get("responsible_party")
        or item.get("responsible")
        or "Estimator / PM"
    ).strip()


def _trade_for_punch(item: Dict[str, Any]) -> str:
    raw = item.get("trade") or item.get("discipline") or ""
    if raw:
        return str(raw).upper()
    pri = str(item.get("priority") or "").upper()
    if pri in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "HOLD", "NOTE", "WATCH"):
        return ""
    return pri


def _due_window(item: Dict[str, Any]) -> str:
    return str(item.get("due_window") or item.get("timeline") or item.get("timing") or "").strip()


def _exhibit_map(analysis: Dict[str, Any]) -> Dict[str, str]:
    """URL → EX-00N from evidence binder when available."""
    try:
        from ic_package_composer import compose_ic_package

        pkg = compose_ic_package(analysis)
        binder = pkg.get("evidence_binder") or {}
        return {
            str(e.get("url")): str(e.get("id"))
            for e in (binder.get("exhibits") or [])
            if e.get("url") and e.get("id")
        }
    except Exception:
        return {}


def analysis_to_bid_csv(analysis: Dict[str, Any]) -> str:
    """
    Return CSV text for estimator paste.

    Columns include exhibit_id (Evidence Binder cross-ref) and source_url hyperlinks
    for Excel / Sheets.
    """
    buf = io.StringIO()
    w = csv.writer(buf)
    headers = [
        "section",
        "trade",
        "owner",
        "due_window",
        "cost_code",
        "priority",
        "item",
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
    w.writerow(headers)
    share = str(analysis.get("share_url") or "").strip()
    url_to_ex = _exhibit_map(analysis)
    pi = analysis.get("project_info") or {}

    def _eid(url: str, existing: Any = "") -> str:
        if existing:
            return str(existing)
        return url_to_ex.get(str(url or "").strip(), "")

    w.writerow(
        [
            "site",
            "",
            "",
            "",
            "",
            "",
            f"{pi.get('address') or ''} {pi.get('city') or ''} {pi.get('state') or ''} {pi.get('zip') or ''}".strip(),
            "",
            "",
            "",
            "",
            "",
            "",
            share,
            "Full shareable report",
            "",
            analysis.get("coverage", {}).get("badge")
            or (analysis.get("jurisdiction") or {}).get("coverage_badge")
            or "Citeable pre-bid diligence — not a sealed bid",
            share,
        ]
    )
    ahj = analysis.get("ahj_card") or {}
    if ahj.get("name"):
        portal = ahj.get("fees_url") or ahj.get("portal_url") or ""
        w.writerow(
            [
                "ahj",
                "",
                "AHJ / Permit runner",
                "",
                "",
                "",
                ahj.get("name"),
                "",
                "",
                "",
                "",
                ahj.get("last_verified") or "",
                _eid(portal),
                portal,
                "AHJ portal / fees",
                ahj.get("last_verified") or "",
                "Confirm fees on official schedule",
                share,
            ]
        )
    punch = ((analysis.get("punch_list") or {}).get("punch_list")) or []
    for item in punch:
        if not isinstance(item, dict):
            continue
        cost = item.get("estimated_cost")
        trade = _trade_for_punch(item)
        task = item.get("task") or item.get("title") or ""
        src = str(item.get("source_url") or "").strip()
        w.writerow(
            [
                "punch",
                trade,
                _owner_for_punch(item),
                _due_window(item),
                item.get("cost_code") or "",
                str(item.get("priority") or "").upper(),
                task,
                item.get("qty") or item.get("quantity") or "",
                item.get("unit") or "",
                item.get("crew_rate") or "",
                cost if isinstance(cost, (int, float)) else "",
                item.get("timeline") or "",
                _eid(src, item.get("exhibit_id")),
                src,
                item.get("source_label") or ("Source" if src else "Unverified"),
                "yes" if item.get("verified") else "Unverified",
                "Planning aid — fill qty/crew rates; not a quote. Keep source_url as hyperlink.",
                share,
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
        trade = str(fee.get("trade") or "GENERAL").upper()
        src = str(fee.get("source_url") or "").strip()
        w.writerow(
            [
                "fee",
                trade,
                fee.get("owner") or "Estimator / Permit runner",
                (analysis.get("fee_card") or {}).get("timeline") or "Pre-bid",
                fee.get("cost_code") or "",
                "",
                label,
                "",
                "",
                "",
                amt if isinstance(amt, (int, float)) else "",
                (analysis.get("fee_card") or {}).get("timeline") or "",
                _eid(src, fee.get("exhibit_id")),
                src,
                fee.get("source_label") or ("Source" if src else "Unverified — confirm with AHJ"),
                "yes" if fee.get("verified") else "planning",
                note or "Planning aid — not a quote; confirm with AHJ",
                share,
            ]
        )
    for g in ((analysis.get("gotcha_watchlist") or {}).get("items")) or []:
        if not isinstance(g, dict):
            continue
        anti = "; ".join(g.get("anti_patterns") or [])
        title = g.get("title") or ""
        src = str(g.get("source_url") or "").strip()
        w.writerow(
            [
                "gotcha",
                str(g.get("trade") or "").upper(),
                g.get("owner") or "Estimator / PM",
                g.get("due_window") or "Pre-bid",
                g.get("cost_code") or "",
                g.get("priority") or "HIGH",
                title,
                "",
                "",
                "",
                "",
                "",
                _eid(src, g.get("exhibit_id")),
                src,
                g.get("source_label") or ("Source" if src else "Unverified"),
                "yes" if src else "Unverified",
                (g.get("detail") or "") + (f" | Don't: {anti}" if anti else ""),
                share,
            ]
        )
    band = analysis.get("contingency_band") or {}
    if band.get("pct_mid") is not None:
        w.writerow(
            [
                "contingency",
                "PLANNING",
                "Estimator",
                "Before bid lock",
                "",
                "",
                band.get("label") or "Suggested contingency",
                "",
                "",
                "",
                band.get("usd_mid") if isinstance(band.get("usd_mid"), (int, float)) else "",
                f"{band.get('pct_low')}%-{band.get('pct_high')}% (mid {band.get('pct_mid')}%)",
                "",
                share,
                "Bid Risk Receipt",
                "heuristic",
                band.get("disclaimer")
                or "Planning aid — not a quote or sealed bid; confirm with AHJ",
                share,
            ]
        )
    w.writerow(
        [
            "estimator_fill",
            "YOUR_TRADE",
            "YOUR_OWNER",
            "YOUR_DUE_WINDOW",
            "YOUR_COST_CODE",
            "",
            "Labor / material takeoff line (fill in your workbook)",
            "qty",
            "unit",
            "crew_rate",
            "",
            "",
            "",
            "",
            "",
            "",
            "Reg Guard does not invent takeoff — citeable pre-bid diligence only",
            share,
        ]
    )
    return buf.getvalue()
