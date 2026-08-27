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


def _project_is_data_center(analysis: Dict[str, Any]) -> bool:
    pi = analysis.get("project_info") or {}
    t = str(pi.get("type") or "").strip().lower().replace(" ", "_").replace("-", "_")
    return t in (
        "data_center",
        "datacenter",
        "dc",
        "colocation",
        "colo",
        "ai_crypto_compute",
    )


def _planning_exposure_for_killer(
    *,
    title: str,
    detail: str,
    kind: str,
    priority: str,
    fee_amount: Optional[float] = None,
    estimated_total: float = 0.0,
    is_dc: bool = False,
) -> Dict[str, Any]:
    """
    Honest planning exposure band for bid discussion — NOT guaranteed savings.
    Prefer real fee $ when present; otherwise conservative priority heuristics.
    """
    disclaimer = (
        "Planning exposure only — not a quote and not guaranteed savings. "
        "Use for contingency talk; confirm fees/schedule with AHJ and utility."
    )
    pri = (priority or "NOTE").upper()
    blob = f"{title} {detail}".lower()

    # 1) Known fee extract → exposure ≈ fee itself (most honest)
    if isinstance(fee_amount, (int, float)) and fee_amount > 0:
        mid = int(fee_amount)
        return {
            "label": "Planning exposure (fee line)",
            "usd_low": max(0, int(mid * 0.8)),
            "usd_mid": mid,
            "usd_high": int(mid * 1.25),
            "basis": "fee_extract",
            "verified": False,
            "disclaimer": disclaimer,
        }

    # 2) DC / interconnect / large-load language on THIS killer → wider planning band
    killer_dc = any(
        k in blob
        for k in (
            "data center",
            "large-load",
            "large load",
            "ercot",
            "interconnect",
            "tdsp",
            "fast-41",
            "fast 41",
            "colo",
            "utility interconnection",
            "parallel track",
            "parallel-track",
            "mission-critical",
            "mission critical",
        )
    )
    if killer_dc and pri in ("CRITICAL", "HIGH"):
        # Schedule miss on DC is often >> permit fee; keep labeled as planning only
        if pri == "CRITICAL":
            low, mid, high = 15000, 40000, 120000
        else:
            low, mid, high = 8000, 25000, 75000
        # Soft-cap vs rollup if we have one
        if estimated_total and estimated_total > 0:
            high = min(high, int(estimated_total * 0.15))
            mid = min(mid, int(estimated_total * 0.08))
            low = min(low, int(estimated_total * 0.03))
        return {
            "label": "Planning exposure (schedule / parallel-track)",
            "usd_low": low,
            "usd_mid": mid,
            "usd_high": high,
            "basis": "dc_schedule_heuristic",
            "verified": False,
            "disclaimer": disclaimer
            + " Large-load delay risk is order-of-magnitude only.",
        }

    # 3) Generic priority heuristic (trade / AHJ gotcha)
    # Slightly wider on data-center projects for Critical only (still not savings)
    if is_dc and pri == "CRITICAL":
        low, mid, high = 4000, 12000, 30000
    elif pri == "CRITICAL":
        low, mid, high = 2500, 8000, 20000
    elif pri == "HIGH":
        low, mid, high = 1000, 4000, 12000
    else:
        low, mid, high = 500, 1500, 5000

    if estimated_total and estimated_total > 0:
        # Cap heuristics to a small slice of known rollup
        high = min(high, max(1000, int(estimated_total * 0.08)))
        mid = min(mid, max(500, int(estimated_total * 0.04)))
        low = min(low, max(250, int(estimated_total * 0.015)))

    return {
        "label": "Planning exposure (heuristic)",
        "usd_low": low,
        "usd_mid": mid,
        "usd_high": high,
        "basis": "priority_heuristic",
        "verified": False,
        "disclaimer": disclaimer,
    }


def build_margin_killers(analysis: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
    """
    Top bid-risk killers for the 1-page Bid Risk Receipt / share text.
    Prefer curated gotchas, then Critical/High punch, then fee extracts.
    For data-center projects, prefer DC / interconnect gotchas first.
    """
    killers: List[Dict[str, Any]] = []
    seen: set = set()
    is_dc = _project_is_data_center(analysis)
    summary = analysis.get("summary") or {}
    punch = analysis.get("punch_list") or {}
    est = float(summary.get("estimated_total_cost") or punch.get("estimated_total_cost") or 0)

    def _add(
        title: str,
        detail: str,
        *,
        kind: str,
        priority: str = "NOTE",
        verified: bool = False,
        source_url: Optional[str] = None,
        source_label: Optional[str] = None,
        fee_amount: Optional[float] = None,
    ) -> None:
        key = (title or "")[:60].lower()
        if not title or key in seen or len(killers) >= limit:
            return
        seen.add(key)
        exposure = _planning_exposure_for_killer(
            title=title,
            detail=detail or "",
            kind=kind,
            priority=priority,
            fee_amount=fee_amount,
            estimated_total=est,
            is_dc=is_dc,
        )
        from citation_honesty import citation_badge_label, citation_tier_for

        draft = {
            "title": str(title)[:120],
            "detail": str(detail or "")[:200],
            "kind": kind,
            "priority": str(priority or "NOTE").upper(),
            "verified": bool(verified) and bool(source_url),
            "source_url": source_url,
            "source_label": source_label,
            "jurisdiction_layer": None,
            "planning_exposure": exposure,
        }
        # Prefer explicit portal-link honesty over "verified because URL exists"
        if kind in ("gotcha", "punch") and source_url and not verified:
            draft["citation_tier"] = "link"
            draft["verified"] = False
        tier = citation_tier_for(draft)
        draft["citation_tier"] = tier
        if tier != "verified":
            draft["verified"] = False
        draft["source_label"] = source_label or citation_badge_label(tier).title().replace(
            "Source", "Source"
        )
        if tier == "link" and not source_label:
            draft["source_label"] = "Portal link"
        elif tier == "unverified":
            draft["source_label"] = "Unverified"
        elif tier == "verified" and not source_label:
            draft["source_label"] = "Source"
        killers.append(draft)

    gotchas = (analysis.get("gotcha_watchlist") or {}).get("items") or []

    def _gotcha_rank(g: Dict[str, Any]) -> Tuple[int, int]:
        pri = str(g.get("priority") or "").upper()
        pri_rank = 0 if pri == "CRITICAL" else 1 if pri == "HIGH" else 2
        gid = str(g.get("id") or "")
        title = str(g.get("title") or "").lower()
        dc_boost = 0
        if is_dc and (
            "_dc_" in gid
            or "data center" in title
            or "ercot" in title
            or "large-load" in title
            or "interconnect" in title
        ):
            dc_boost = -1  # sort earlier
        return (dc_boost, pri_rank)

    for g in sorted([x for x in gotchas if isinstance(x, dict)], key=_gotcha_rank):
        _add(
            str(g.get("title") or ""),
            str(g.get("detail") or ""),
            kind="gotcha",
            priority=str(g.get("priority") or "HIGH"),
            verified=bool(g.get("verified")) and bool(g.get("source_url")),
            source_url=g.get("source_url"),
            source_label=g.get("source_label"),
        )

    items = _punch_items(analysis)
    for pri in ("CRITICAL", "HIGH"):
        for it in items:
            if str(it.get("priority") or "").upper() != pri:
                continue
            fee_amt = it.get("estimated_cost")
            if not isinstance(fee_amt, (int, float)):
                fee_amt = None
            _add(
                str(it.get("task") or "")[:120],
                str(it.get("notes") or it.get("timeline") or "Confirm before bid"),
                kind="punch",
                priority=pri,
                verified=bool(it.get("verified")) and bool(it.get("source_url")),
                source_url=it.get("source_url"),
                source_label=it.get("source_label"),
                fee_amount=float(fee_amt) if fee_amt else None,
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
            fee_amount=float(amt) if isinstance(amt, (int, float)) else None,
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
    *,
    is_dc: bool = False,
) -> Dict[str, Any]:
    """
    Heuristic contingency band for bid — labeled estimate, not a quote.
    Base 3% + 1.5% per Critical + 0.75% per High + 0.5% per Unverified line (capped).
    Data-center / large-load: floor at 18% mid for parallel-track schedule risk;
    hide laughable USD when rollup is a stub (<$100k).
    """
    pct = 3.0 + (crit * 1.5) + (high * 0.75) + (min(unverified, 20) * 0.5)
    pct = max(3.0, min(pct, 25.0))
    if is_dc:
        pct = max(pct, 18.0)
        pct = min(pct, 28.0)
    low_pct = max(2.0, pct - 2.0)
    high_pct = min(35.0 if is_dc else 30.0, pct + 3.0)
    base = max(0.0, float(estimated_total or 0))
    # Stub rollups understate interconnect — show % only for DC when base is tiny
    show_usd = base >= 100_000 or not is_dc
    drivers: Dict[str, Any] = {
        "critical_items": crit,
        "high_items": high,
        "unverified_items": unverified,
        "estimated_total_cost": base or None,
    }
    if is_dc:
        drivers["data_center_parallel_track"] = True
    disclaimer = (
        "Planning aid only — not a quote. Based on Critical/High/Unverified "
        "punch counts. Confirm fees and scope with the AHJ before bid."
    )
    if is_dc:
        disclaimer = (
            "Planning aid only — not a quote. Data-center / large-load sites often "
            "run AHJ + utility/ERCOT + federal diligence on parallel clocks. "
            "Percent band is schedule-risk planning; confirm interconnect exposure "
            "with utility/RTO before bid. Dollar rollup may understate large-load costs."
        )
    return {
        "label": (
            "Suggested bid contingency band (parallel-track)"
            if is_dc
            else "Suggested bid contingency band"
        ),
        "pct_low": round(low_pct, 1),
        "pct_mid": round(pct, 1),
        "pct_high": round(high_pct, 1),
        "usd_low": int(base * low_pct / 100) if show_usd and base else None,
        "usd_mid": int(base * pct / 100) if show_usd and base else None,
        "usd_high": int(base * high_pct / 100) if show_usd and base else None,
        "drivers": drivers,
        "disclaimer": disclaimer,
        "verified": False,
    }


def enrich_analysis_with_arbitrage(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Add fee_card, ahj_card, document_checklist, gotcha_watchlist, contingency_band."""
    if not isinstance(analysis, dict):
        return analysis

    out = analysis  # mutate in place for pipeline simplicity
    city, state, zip_code = _project_locale(out)
    try:
        from jurisdiction_resolver import attach_jurisdiction_cards, resolve_jurisdiction

        resolved = resolve_jurisdiction(zip_code=zip_code, city=city, state=state)
        city = resolved.get("city") or city
        state = resolved.get("state") or state
        zip_code = resolved.get("zip") or zip_code
        pack = resolved.get("local") or generic_thin_pack(city, state)
        out = attach_jurisdiction_cards(out, resolved)
    except Exception:
        pack = resolve_city_pack(city, state, zip_code) or generic_thin_pack(city, state)

    # Prefer order-attached / ZIP-cache / promoted local_pack when present
    try:
        from local_pack_store import (
            attach_local_pack_from_analysis,
            apply_local_pack_to_cards,
            load_zip_pack,
        )

        if not out.get("local_pack"):
            cached = load_zip_pack(str(zip_code or ""))
            if cached:
                out["local_pack"] = cached
            else:
                out = attach_local_pack_from_analysis(
                    out,
                    city=city,
                    state=state,
                    zip_code=str(zip_code or ""),
                    persist=False,
                    record_hit=False,
                )
        out = apply_local_pack_to_cards(out)
        lp = out.get("local_pack") or {}
        if lp.get("citeable") or lp.get("tier") in ("paid_local", "portal_seed", "full_pack"):
            # Overlay pack for fee/gotcha enrichment below
            pack = {
                **pack,
                "citeable": bool(lp.get("citeable")),
                "portal_only": lp.get("tier") == "portal_seed",
                "fees": lp.get("fees") or pack.get("fees") or [],
                "gotchas": lp.get("gotchas") or pack.get("gotchas") or [],
                "documents": lp.get("documents") or pack.get("documents") or [],
                "timeline_hint": lp.get("timeline_hint") or pack.get("timeline_hint"),
                "ahj": lp.get("ahj") or pack.get("ahj") or {},
                "pack_key": lp.get("pack_key") or pack.get("pack_key"),
            }
    except Exception as e:
        logger.warning("local_pack enrich overlay failed: %s", e)

    items = _punch_items(out)
    crit, high, unverified = _count_priorities(items)
    summary = out.get("summary") or {}
    est = float(summary.get("estimated_total_cost") or 0)
    punch = out.get("punch_list") or {}
    if not est:
        est = float(punch.get("estimated_total_cost") or 0)

    fee_rows = list(pack.get("fees") or [])
    # Prefer punch-extracted $ when present; keep pack fees first
    # P1: never surface fee dollars for portal-only / non-citeable packs
    # Exception: paid_local / order local_pack may keep planning-aid fee rows (amounts OK as aids)
    lp_tier = str((out.get("local_pack") or {}).get("tier") or "")
    allow_aid_fees = lp_tier in ("paid_local", "full_pack") or bool(pack.get("citeable"))
    if pack.get("citeable") and not pack.get("portal_only"):
        extracted = _extract_fees_from_punch(items)
        seen = {str(r.get("label") or "")[:40] for r in fee_rows}
        for row in extracted:
            key = str(row.get("label") or "")[:40]
            if key not in seen:
                fee_rows.append(row)
                seen.add(key)
    elif allow_aid_fees and fee_rows:
        # Keep scraped planning-aid fees; strip verified theater
        cleaned = []
        for row in fee_rows:
            if not isinstance(row, dict):
                continue
            r = dict(row)
            r["verified"] = bool(pack.get("citeable") and r.get("verified"))
            r.setdefault("detail", (r.get("detail") or "") + " (planning aid)")
            cleaned.append(r)
        fee_rows = cleaned
    else:
        fee_rows = []

    # Catalog-backed fees/gotchas when city pack is generic but AHJ catalog hit (ZIP beachhead)
    catalog_citeable = False
    catalog_gotchas: list = []
    try:
        from ahj_catalog import ahj_identity_conflict, lookup_ahj

        rec = lookup_ahj(city, state, zip_code)
        conflict = ahj_identity_conflict(city, state, zip_code)
        if conflict:
            out["ahj_identity"] = conflict
        if rec:
            catalog_citeable = True
            if not fee_rows:
                for fee in rec.get("fees") or []:
                    fee_rows.append(
                        {
                            "label": fee.get("label") or "Permit fee",
                            "amount_usd": fee.get("amount_usd"),
                            "trade": fee.get("trade") or "general",
                            "detail": fee.get("citation_note") or "Confirm on official schedule",
                            "source_url": fee.get("citation_url") or rec.get("portal_url"),
                            "source_label": rec.get("city") or "AHJ catalog",
                            "verified": bool(
                                fee.get("verified")
                                and fee.get("amount_usd") is not None
                                and not fee.get("amount_requires_schedule")
                            ),
                            "amount_requires_schedule": bool(fee.get("amount_requires_schedule")),
                        }
                    )
            for g in rec.get("gotchas") or []:
                catalog_gotchas.append(
                    {
                        "id": g.get("id"),
                        "title": g.get("title"),
                        "detail": "; ".join(g.get("checklist") or [])[:240],
                        "priority": "HIGH",
                        "source_url": g.get("citation_url") or rec.get("portal_url"),
                        "source_label": rec.get("city") or "AHJ catalog",
                        "verified": bool(g.get("citation_url") or rec.get("portal_url")),
                        "checklist": g.get("checklist") or [],
                        "anti_patterns": g.get("anti_patterns") or [],
                    }
                )
    except Exception:
        rec = None

    timeline = (
        summary.get("estimated_timeline")
        or punch.get("timeline_summary")
        or pack.get("timeline_hint")
        or "Confirm with AHJ"
    )

    citeable = bool(pack.get("citeable")) or catalog_citeable
    out["fee_card"] = {
        "title": "Fee & timeline extract",
        "timeline": timeline,
        "timeline_hint": pack.get("timeline_hint") or "",
        "fees": fee_rows,
        "citeable_coverage": citeable,
        "disclaimer": (
            "Confirm all fees on the official AHJ schedule before bid or filing."
            if citeable
            else (
                "Fee amounts hidden — portal seed / federal-state coverage only. "
                "Confirm the official AHJ schedule before bid."
            )
        ),
    }

    ahj = pack.get("ahj") or {}
    who = (punch.get("who_to_call") or {}) if isinstance(punch.get("who_to_call"), dict) else {}
    # Prefer catalog portal/name when ZIP beachhead resolves (AHJ identity lock)
    cat_name = None
    cat_portal = None
    cat_fees_url = None
    cat_apply = None
    cat_insp = None
    cat_verified = None
    cat_inspection_seq: list = []
    if rec:
        cat_name = f"{rec.get('city')}, {rec.get('state') or 'TX'} AHJ"
        cat_portal = rec.get("portal_url") or ""
        cat_fees_url = rec.get("fees_url") or cat_portal
        cat_apply = rec.get("apply_url") or ""
        cat_insp = rec.get("inspections_url") or ""
        cat_verified = rec.get("last_verified") or ""
        cat_inspection_seq = list(rec.get("inspection_sequence") or [])[:10]
    identity_note = ""
    if isinstance(out.get("ahj_identity"), dict) and out["ahj_identity"].get("note"):
        identity_note = str(out["ahj_identity"]["note"])
    pack_insp = list(pack.get("inspection_sequence") or pack.get("documents") or [])[:10]
    out["ahj_card"] = {
        "title": "AHJ portal & contact",
        "name": cat_name or ahj.get("name") or who.get("building_department") or "Local AHJ",
        "portal_url": cat_portal or ahj.get("portal_url") or "",
        "fees_url": cat_fees_url or ahj.get("fees_url") or "",
        "apply_url": cat_apply or ahj.get("apply_url") or "",
        "inspections_url": cat_insp or ahj.get("inspections_url") or "",
        "phone": ahj.get("phone") or who.get("phone") or "",
        "notes": identity_note or ahj.get("notes") or "",
        "citeable_coverage": citeable,
        "last_verified": cat_verified or pack.get("last_verified") or ahj.get("last_verified") or "",
        "extra_contacts": who,
    }
    out["inspection_sequence_card"] = {
        "title": "Inspection sequence",
        "steps": cat_inspection_seq or pack_insp,
        "citeable_coverage": citeable,
    }

    gotcha_items = list(pack.get("gotchas") or []) or catalog_gotchas
    out["gotcha_watchlist"] = {
        "title": "Local gotcha watchlist",
        "items": gotcha_items,
        "citeable_coverage": citeable,
        "pack_key": (rec or {}).get("ahj_id") if rec else pack.get("pack_key"),
    }

    docs = list(pack.get("documents") or [])
    out["document_checklist"] = {
        "title": "Document / submittal checklist",
        "items": [{"task": d, "done": False} for d in docs],
        "disclaimer": "Typical AHJ asks — confirm exact submittal list for this permit type.",
        "citeable_coverage": citeable,
    }

    is_dc = _project_is_data_center(out)
    out["contingency_band"] = _build_contingency(crit, high, unverified, est, is_dc=is_dc)
    out["margin_killers"] = build_margin_killers(out, limit=3)

    try:
        from site_address import clean_project_info_address

        out = clean_project_info_address(out)
    except Exception:
        pass
    try:
        from citation_honesty import apply_citation_honesty

        out = apply_citation_honesty(out)
        # Rebuild killers after punch citation demotion so badges match
        out["margin_killers"] = build_margin_killers(out, limit=3)
        out = apply_citation_honesty(out)
    except Exception:
        pass

    # Roll up planning exposure (sum of mid bands) — still not guaranteed savings
    exp_mids = []
    for k in out["margin_killers"]:
        pe = (k or {}).get("planning_exposure") or {}
        if isinstance(pe.get("usd_mid"), (int, float)):
            exp_mids.append(int(pe["usd_mid"]))
    out["planning_exposure_summary"] = {
        "label": "Sum of killer planning-exposure mids",
        "usd_mid_total": sum(exp_mids) if exp_mids else None,
        "killer_count": len(out["margin_killers"]),
        "verified": False,
        "disclaimer": (
            "Sum of heuristic planning-exposure midpoints for top killers — "
            "not guaranteed savings and not a quote. Confirm with AHJ/utility."
        ),
        "data_center_mode": _project_is_data_center(out),
    }
    if _project_is_data_center(out):
        out["dc_positioning"] = {
            "headline": "Parallel-track Bid Risk Receipt for data center / large-load sites",
            "pitch": (
                "AHJ permits, utility interconnection, and large-load diligence often run "
                "on separate clocks. This receipt surfaces that risk before bid — it does "
                "not run interconnection studies or file AHJ applications."
            ),
            "buyer": "IC consultants, electrical PMs, GC bid leads (TX beachhead)",
        }

    # Rank punch list + community friction (presentation / completeness)
    try:
        from punch_rank import normalize_analysis_punch

        out = normalize_analysis_punch(out)
        items = _punch_items(out)
        crit, high, unverified = _count_priorities(items)
        out["margin_killers"] = build_margin_killers(out, limit=3)
        out["contingency_band"] = _build_contingency(crit, high, unverified, est, is_dc=is_dc)
        exp_mids = []
        for k in out["margin_killers"]:
            pe = (k or {}).get("planning_exposure") or {}
            if isinstance(pe.get("usd_mid"), (int, float)):
                exp_mids.append(int(pe["usd_mid"]))
        out["planning_exposure_summary"] = {
            "label": "Sum of killer planning-exposure mids",
            "usd_mid_total": sum(exp_mids) if exp_mids else None,
            "killer_count": len(out["margin_killers"]),
            "verified": False,
            "disclaimer": (
                "Sum of heuristic planning-exposure midpoints for top killers — "
                "not guaranteed savings and not a quote. Confirm with AHJ/utility."
            ),
            "data_center_mode": is_dc,
        }
    except Exception:
        pass
    try:
        from community_friction import build_community_friction

        out["community_friction"] = build_community_friction(out)
    except Exception:
        pass

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
        "planning_exposure_mid_total": out["planning_exposure_summary"].get("usd_mid_total"),
    }

    logger.info(
        "Arbitrage enriched pack=%s crit=%s high=%s unverified=%s",
        pack.get("pack_key"),
        crit,
        high,
        unverified,
    )
    try:
        from coverage_honesty import apply_coverage_honesty

        out = apply_coverage_honesty(out, pack=pack)
    except Exception as e:
        logger.warning("coverage honesty apply failed: %s", e)
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
