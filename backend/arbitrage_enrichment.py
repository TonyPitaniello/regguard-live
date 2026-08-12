"""
Bid-time arbitrage enrichment: fee card, AHJ card, docs, gotchas, contingency.
Pure post-process on analysis dict — no extra Firecrawl calls.
"""

from __future__ import annotations

import logging
import re
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from city_packs import generic_thin_pack, resolve_city_pack

logger = logging.getLogger(__name__)


def _project_locale(analysis: Dict[str, Any]) -> Tuple[str, str, str]:
    pi = analysis.get("project_info") or {}
    return (
        str(pi.get("city") or ""),
        str(pi.get("state") or ""),
        str(pi.get("zip") or ""),
    )


def _punch_items(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    pl = analysis.get("punch_list") or {}
    items = pl.get("punch_list") or []
    return [i for i in items if isinstance(i, dict)]


def _count_priorities(items: List[Dict[str, Any]]) -> Tuple[int, int, int]:
    crit = high = unverified = 0
    for it in items:
        p = str(it.get("priority") or "").upper()
        if p == "CRITICAL":
            crit += 1
        elif p == "HIGH":
            high += 1
        verified = bool(it.get("verified")) and bool(it.get("source_url"))
        if not verified:
            unverified += 1
    return crit, high, unverified


def _extract_fees_from_punch(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Pull $ mentions from punch tasks into fee_card rows."""
    out: List[Dict[str, Any]] = []
    money = re.compile(r"\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)")
    for it in items:
        task = str(it.get("task") or "")
        m = money.search(task)
        if not m:
            continue
        try:
            amt = float(m.group(1).replace(",", ""))
        except ValueError:
            amt = None
        out.append(
            {
                "label": task[:120],
                "amount_usd": amt,
                "detail": "Extracted from punch list — confirm with AHJ",
                "verified": bool(it.get("verified")) and bool(it.get("source_url")),
                "source_url": it.get("source_url"),
                "source_label": it.get("source_label") or "Punch list",
            }
        )
    return out[:8]


def build_margin_killers(analysis: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
    """
    Top bid-risk killers for the 1-page Bid Risk Receipt / share text.
    Prefer curated gotchas, then Critical/High punch, then fee extracts.
    """
    killers: List[Dict[str, Any]] = []
    seen: set = set()

    def _add(
        title: str,
        detail: str,
        *,
        kind: str,
        priority: str = "NOTE",
        verified: bool = False,
        source_url: Optional[str] = None,
        source_label: Optional[str] = None,
    ) -> None:
        key = (title or "")[:60].lower()
        if not title or key in seen or len(killers) >= limit:
            return
        seen.add(key)
        killers.append(
            {
                "title": str(title)[:120],
                "detail": str(detail or "")[:200],
                "kind": kind,
                "priority": str(priority or "NOTE").upper(),
                "verified": bool(verified) and bool(source_url),
                "source_url": source_url,
                "source_label": source_label
                or ("Source" if verified and source_url else "Unverified"),
            }
        )

    gotchas = (analysis.get("gotcha_watchlist") or {}).get("items") or []
    # CRITICAL gotchas first, then any remaining by listed order
    for g in sorted(
        [x for x in gotchas if isinstance(x, dict)],
        key=lambda x: 0 if str(x.get("priority") or "").upper() == "CRITICAL" else 1,
    ):
        _add(
            str(g.get("title") or ""),
            str(g.get("detail") or ""),
            kind="gotcha",
            priority=str(g.get("priority") or "HIGH"),
            verified=bool(g.get("source_url")),
            source_url=g.get("source_url"),
            source_label=g.get("source_label"),
        )

    items = _punch_items(analysis)
    for pri in ("CRITICAL", "HIGH"):
        for it in items:
            if str(it.get("priority") or "").upper() != pri:
                continue
            _add(
                str(it.get("task") or "")[:120],
                str(it.get("notes") or it.get("timeline") or "Confirm before bid"),
                kind="punch",
                priority=pri,
                verified=bool(it.get("verified")) and bool(it.get("source_url")),
                source_url=it.get("source_url"),
                source_label=it.get("source_label"),
            )

    for row in (analysis.get("fee_card") or {}).get("fees") or []:
        if not isinstance(row, dict):
            continue
        amt = row.get("amount_usd")
        amt_s = f"${amt:,.0f}" if isinstance(amt, (int, float)) else "TBD"
        label = str(row.get("label") or "Fee")
        _add(
            f"Fee risk: {label[:90]}",
            f"{amt_s} — {str(row.get('detail') or 'Confirm on AHJ schedule')[:120]}",
            kind="fee",
            priority="HIGH",
            verified=bool(row.get("verified")) and bool(row.get("source_url")),
            source_url=row.get("source_url"),
            source_label=row.get("source_label"),
        )

    if not killers:
        ahj = analysis.get("ahj_card") or {}
        _add(
            "Confirm fees, forms, and timeline with AHJ before bid",
            f"{ahj.get('name') or 'Local AHJ'} — no high-confidence killers extracted yet.",
            kind="fallback",
            priority="NOTE",
            verified=False,
        )
    return killers[:limit]


def _build_contingency(
    crit: int,
    high: int,
    unverified: int,
    estimated_total: float,
) -> Dict[str, Any]:
    """
    Heuristic contingency band for bid — labeled estimate, not a quote.
    Base 3% + 1.5% per Critical + 0.75% per High + 0.5% per Unverified line (capped).
    """
    pct = 3.0 + (crit * 1.5) + (high * 0.75) + (min(unverified, 20) * 0.5)
    pct = max(3.0, min(pct, 25.0))
    low_pct = max(2.0, pct - 2.0)
    high_pct = min(30.0, pct + 3.0)
    base = max(0.0, float(estimated_total or 0))
    return {
        "label": "Suggested bid contingency band",
        "pct_low": round(low_pct, 1),
        "pct_mid": round(pct, 1),
        "pct_high": round(high_pct, 1),
        "usd_low": int(base * low_pct / 100) if base else None,
        "usd_mid": int(base * pct / 100) if base else None,
        "usd_high": int(base * high_pct / 100) if base else None,
        "drivers": {
            "critical_items": crit,
            "high_items": high,
            "unverified_items": unverified,
            "estimated_total_cost": base or None,
        },
        "disclaimer": (
            "Planning aid only — not a quote. Based on Critical/High/Unverified "
            "punch counts. Confirm fees and scope with the AHJ before bid."
        ),
        "verified": False,
    }


def enrich_analysis_with_arbitrage(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Add fee_card, ahj_card, document_checklist, gotcha_watchlist, contingency_band."""
    if not isinstance(analysis, dict):
        return analysis

    out = analysis  # mutate in place for pipeline simplicity
    city, state, zip_code = _project_locale(out)
    pack = resolve_city_pack(city, state, zip_code) or generic_thin_pack(city, state)

    items = _punch_items(out)
    crit, high, unverified = _count_priorities(items)
    summary = out.get("summary") or {}
    est = float(summary.get("estimated_total_cost") or 0)
    punch = out.get("punch_list") or {}
    if not est:
        est = float(punch.get("estimated_total_cost") or 0)

    fee_rows = list(pack.get("fees") or [])
    # Prefer punch-extracted $ when present; keep pack fees first
    extracted = _extract_fees_from_punch(items)
    seen = {str(r.get("label") or "")[:40] for r in fee_rows}
    for row in extracted:
        key = str(row.get("label") or "")[:40]
        if key not in seen:
            fee_rows.append(row)
            seen.add(key)

    timeline = (
        summary.get("estimated_timeline")
        or punch.get("timeline_summary")
        or pack.get("timeline_hint")
        or "Confirm with AHJ"
    )

    out["fee_card"] = {
        "title": "Fee & timeline extract",
        "timeline": timeline,
        "timeline_hint": pack.get("timeline_hint") or "",
        "fees": fee_rows,
        "citeable_coverage": bool(pack.get("citeable")),
        "disclaimer": "Confirm all fees on the official AHJ schedule before bid or filing.",
    }

    ahj = pack.get("ahj") or {}
    who = (punch.get("who_to_call") or {}) if isinstance(punch.get("who_to_call"), dict) else {}
    out["ahj_card"] = {
        "title": "AHJ portal & contact",
        "name": ahj.get("name") or who.get("building_department") or "Local AHJ",
        "portal_url": ahj.get("portal_url") or "",
        "fees_url": ahj.get("fees_url") or "",
        "phone": ahj.get("phone") or who.get("phone") or "",
        "notes": ahj.get("notes") or "",
        "citeable_coverage": bool(pack.get("citeable")),
        "extra_contacts": who,
    }

    out["gotcha_watchlist"] = {
        "title": "Local gotcha watchlist",
        "items": list(pack.get("gotchas") or []),
        "citeable_coverage": bool(pack.get("citeable")),
        "pack_key": pack.get("pack_key"),
    }

    docs = list(pack.get("documents") or [])
    out["document_checklist"] = {
        "title": "Document / submittal checklist",
        "items": [{"task": d, "done": False} for d in docs],
        "disclaimer": "Typical AHJ asks — confirm exact submittal list for this permit type.",
        "citeable_coverage": bool(pack.get("citeable")),
    }

    out["contingency_band"] = _build_contingency(crit, high, unverified, est)
    out["margin_killers"] = build_margin_killers(out, limit=3)

    # Snapshot for job recheck diffs
    out["arbitrage_snapshot"] = {
        "critical": crit,
        "high": high,
        "unverified": unverified,
        "punch_count": len(items),
        "fee_labels": [str(f.get("label") or "")[:80] for f in fee_rows[:10]],
        "gotcha_ids": [str(g.get("id") or "") for g in (pack.get("gotchas") or [])],
        "pack_key": pack.get("pack_key"),
        "timeline": str(timeline)[:120],
        "estimated_total_cost": est or None,
        "killer_titles": [str(k.get("title") or "")[:80] for k in out["margin_killers"]],
    }

    logger.info(
        "Arbitrage enriched pack=%s crit=%s high=%s unverified=%s",
        pack.get("pack_key"),
        crit,
        high,
        unverified,
    )
    return out


def diff_arbitrage_snapshots(
    previous: Optional[Dict[str, Any]],
    current: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compare two arbitrage_snapshot dicts for recheck UI/email."""
    prev = previous or {}
    cur = current or {}
    changes: List[str] = []

    def _i(d: Dict, k: str) -> int:
        try:
            return int(d.get(k) or 0)
        except (TypeError, ValueError):
            return 0

    for key, label in (
        ("critical", "Critical items"),
        ("high", "High items"),
        ("unverified", "Unverified items"),
        ("punch_count", "Punch list size"),
    ):
        a, b = _i(prev, key), _i(cur, key)
        if a != b:
            changes.append(f"{label}: {a} → {b}")

    prev_fees = set(prev.get("fee_labels") or [])
    cur_fees = set(cur.get("fee_labels") or [])
    added_fees = cur_fees - prev_fees
    removed_fees = prev_fees - cur_fees
    for f in list(added_fees)[:5]:
        changes.append(f"New fee/extract: {f}")
    for f in list(removed_fees)[:3]:
        changes.append(f"Removed fee/extract: {f}")

    if (prev.get("timeline") or "") != (cur.get("timeline") or ""):
        changes.append(
            f"Timeline: {prev.get('timeline') or '—'} → {cur.get('timeline') or '—'}"
        )

    prev_cost = prev.get("estimated_total_cost")
    cur_cost = cur.get("estimated_total_cost")
    if prev_cost != cur_cost and (prev_cost or cur_cost):
        changes.append(f"Est. cost: {prev_cost} → {cur_cost}")

    return {
        "change_count": len(changes),
        "changes": changes,
        "previous": prev,
        "current": cur,
    }
