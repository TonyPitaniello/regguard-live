"""
Vertical playbooks — address + construction type → cite-or-Confirm diligence tree.

Goal: maximize checklist completeness for Pro/IC with pack hits (cheap) and
honest Confirm blanks (no invented dollars). Planning aid only — not a guarantee.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# Tracks shared by Pro (local) and IC (federal/utility). IC-only tracks marked.
DATA_CENTER_PLAYBOOK: Dict[str, Any] = {
    "id": "data_center",
    "label": "Data center / large-load",
    "aliases": (
        "data_center",
        "data-center",
        "datacenter",
        "dc",
        "colocation",
        "colo",
        "ai_crypto_compute",
        "infrastructure",
    ),
    "disclaimer": (
        "Planning aid only. Checklist completeness ≠ guarantee. Confirm fees, "
        "permit type, utility interconnection, and counsel before bid or filing. "
        "Not a bond, insurance quote, legal opinion, or interconnection study."
    ),
    "tracks": [
        {
            "id": "ahj_permits",
            "label": "AHJ permits & fees",
            "tier": "pro",
            "items": [
                {
                    "id": "ahj_portal",
                    "priority": "CRITICAL",
                    "task": "Confirm building / trade permit path with local AHJ portal",
                    "fill": "ahj_portal",
                },
                {
                    "id": "ahj_fee_schedule",
                    "priority": "CRITICAL",
                    "task": "Pull live AHJ fee schedule before locking contingency",
                    "fill": "ahj_fees",
                },
                {
                    "id": "ahj_trade_type",
                    "priority": "HIGH",
                    "task": "Confirm electrical vs general building application type",
                    "fill": "ahj_gotcha",
                },
                {
                    "id": "ahj_inspection_seq",
                    "priority": "HIGH",
                    "task": "Map inspection sequence into bid contingency",
                    "fill": "ahj_inspection",
                },
            ],
        },
        {
            "id": "utility_interconnect",
            "label": "Utility / interconnection (parallel clock)",
            "tier": "pro",
            "items": [
                {
                    "id": "utility_parallel",
                    "priority": "CRITICAL",
                    "task": "Treat utility interconnection as parallel to AHJ permits — not a sub-step",
                    "fill": "utility_parallel",
                },
                {
                    "id": "tdsp_iso",
                    "priority": "CRITICAL",
                    "task": "Identify serving TDSP / ISO region and large-load study path (e.g. ERCOT in TX)",
                    "fill": "utility_region",
                },
                {
                    "id": "interconnect_materials",
                    "priority": "HIGH",
                    "task": "Confirm utility interconnection materials match this site address",
                    "fill": "confirm_only",
                },
            ],
        },
        {
            "id": "power_load",
            "label": "Power / large-load",
            "tier": "pro",
            "items": [
                {
                    "id": "load_calc",
                    "priority": "HIGH",
                    "task": "Confirm design load MW and whether >100 MW / FAST-41 gate applies",
                    "fill": "confirm_only",
                },
                {
                    "id": "sld_submittal",
                    "priority": "HIGH",
                    "task": "Prepare single-line diagram + load calculations for AHJ / utility",
                    "fill": "docs",
                },
            ],
        },
        {
            "id": "water_cooling",
            "label": "Water / cooling",
            "tier": "ic",
            "items": [
                {
                    "id": "water_withdrawal",
                    "priority": "HIGH",
                    "task": "Confirm cooling water withdrawal / consumptive use path with state EQ",
                    "fill": "confirm_only",
                },
                {
                    "id": "npdes",
                    "priority": "MEDIUM",
                    "task": "Check NPDES / discharge permit needs for data-center operations",
                    "fill": "confirm_only",
                },
            ],
        },
        {
            "id": "zoning_use",
            "label": "Zoning / use / setbacks",
            "tier": "pro",
            "items": [
                {
                    "id": "zoning_confirm",
                    "priority": "HIGH",
                    "task": "Confirm industrial / data-center use and setbacks with planning",
                    "fill": "confirm_only",
                },
            ],
        },
        {
            "id": "moratorium_federal",
            "label": "Moratorium + federal (IC depth)",
            "tier": "ic",
            "items": [
                {
                    "id": "moratorium_radar",
                    "priority": "CRITICAL",
                    "task": "Check local / metro moratorium or pause language for hyperscale / AI infra",
                    "fill": "moratorium",
                },
                {
                    "id": "fast41",
                    "priority": "HIGH",
                    "task": "FAST-41 / Permitting Council diligence when load/cost gates may apply",
                    "fill": "confirm_only",
                },
            ],
        },
    ],
}


def _norm_type(project_type: str = "") -> str:
    return (
        (project_type or "")
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def resolve_playbook(project_type: str = "") -> Optional[Dict[str, Any]]:
    t = _norm_type(project_type)
    if not t:
        return None
    aliases = DATA_CENTER_PLAYBOOK.get("aliases") or ()
    if t in aliases or "data_center" in t or t in ("dc", "colo", "colocation"):
        return DATA_CENTER_PLAYBOOK
    return None


def _is_dc_analysis(analysis: Dict[str, Any]) -> bool:
    pi = analysis.get("project_info") or {}
    t = _norm_type(str(pi.get("type") or ""))
    if resolve_playbook(t):
        return True
    if analysis.get("planning_exposure_summary", {}).get("data_center_mode"):
        return True
    if analysis.get("dc_positioning"):
        return True
    return False


def _ahj_bits(analysis: Dict[str, Any]) -> Dict[str, Any]:
    card = analysis.get("ahj_card") if isinstance(analysis.get("ahj_card"), dict) else {}
    ahj = analysis.get("ahj") if isinstance(analysis.get("ahj"), dict) else {}
    pack = analysis.get("local_pack") if isinstance(analysis.get("local_pack"), dict) else {}
    pack_ahj = pack.get("ahj") if isinstance(pack.get("ahj"), dict) else {}
    portal = (
        card.get("portal_url")
        or ahj.get("ahj_portal_url")
        or pack_ahj.get("portal_url")
        or ""
    )
    fees_url = card.get("fees_url") or pack_ahj.get("fees_url") or portal
    name = card.get("name") or pack_ahj.get("name") or ahj.get("ahj_id") or ""
    fees = list((analysis.get("fee_card") or {}).get("fees") or []) or list(pack.get("fees") or [])
    gotchas = list((analysis.get("gotcha_watchlist") or {}).get("items") or []) or list(
        pack.get("gotchas") or []
    )
    insp = list((analysis.get("inspection_sequence_card") or {}).get("steps") or [])
    citeable = bool(
        (analysis.get("fee_card") or {}).get("citeable_coverage")
        or (analysis.get("gotcha_watchlist") or {}).get("citeable_coverage")
        or pack.get("citeable")
    )
    return {
        "portal": str(portal or "").strip(),
        "fees_url": str(fees_url or "").strip(),
        "name": str(name or "").strip(),
        "fees": fees,
        "gotchas": gotchas,
        "inspection": insp,
        "citeable": citeable,
        "documents": list(pack.get("documents") or [])
        or list((analysis.get("document_checklist") or {}).get("items") or []),
    }


def _fill_item(
    item: Dict[str, Any],
    *,
    bits: Dict[str, Any],
    depth: str,
    state: str,
) -> Dict[str, Any]:
    """Return a checklist row: cited or Confirm."""
    fill = item.get("fill") or "confirm_only"
    priority = str(item.get("priority") or "HIGH")
    base_task = str(item.get("task") or "")
    status = "confirm"
    source_url = ""
    source_label = ""
    detail = ""
    verified = False

    if fill == "ahj_portal" and bits.get("portal"):
        status = "cited"
        source_url = bits["portal"]
        source_label = bits.get("name") or "AHJ portal"
        detail = f"Portal: {bits['portal']}"
        verified = bits.get("citeable")
        base_task = f"Confirm permit path via {source_label}"
    elif fill == "ahj_fees" and (bits.get("fees") or bits.get("fees_url")):
        status = "cited" if bits.get("fees") or bits.get("fees_url") else "confirm"
        fee0 = (bits.get("fees") or [None])[0]
        if isinstance(fee0, dict):
            source_url = str(fee0.get("source_url") or fee0.get("citation_url") or bits.get("fees_url") or "")
            source_label = str(fee0.get("source_label") or fee0.get("label") or "AHJ fees")
            amt = fee0.get("amount_usd")
            if amt is not None and not fee0.get("amount_requires_schedule"):
                detail = f"Planning aid fee line: ${float(amt):.2f} — confirm on schedule"
            else:
                detail = "Amount requires live schedule — do not invent dollars"
            verified = bool(fee0.get("verified") and bits.get("citeable") and source_url)
        else:
            source_url = bits.get("fees_url") or bits.get("portal") or ""
            source_label = "AHJ fee schedule"
            detail = "Pull live schedule before bid"
        base_task = "Pull live AHJ fee schedule before locking contingency"
    elif fill == "ahj_gotcha" and bits.get("gotchas"):
        g0 = bits["gotchas"][0] if bits["gotchas"] else {}
        if isinstance(g0, dict):
            status = "cited"
            source_url = str(g0.get("source_url") or g0.get("citation_url") or bits.get("portal") or "")
            source_label = str(g0.get("title") or "Local gotcha")
            detail = str(g0.get("detail") or "; ".join(g0.get("checklist") or []) or "")[:240]
            verified = bool(source_url and bits.get("citeable"))
            base_task = f"Local gotcha: {source_label}"
    elif fill == "ahj_inspection" and bits.get("inspection"):
        status = "cited"
        steps = bits["inspection"][:4]
        detail = " → ".join(str(s) for s in steps)
        source_url = bits.get("portal") or ""
        source_label = "Inspection sequence"
        verified = bool(bits.get("citeable") and source_url)
        base_task = "Map AHJ inspection sequence into bid contingency"
    elif fill == "utility_parallel":
        status = "cited" if bits.get("citeable") or bits.get("portal") else "confirm"
        source_url = bits.get("portal") or ""
        source_label = "AHJ + utility parallel"
        detail = (
            "AHJ permits and utility interconnection are parallel critical paths for large-load / DC."
        )
        verified = False  # always confirm utility track
    elif fill == "utility_region":
        st = (state or "").strip().upper()
        if st in ("TX", "TEXAS"):
            status = "cited"
            detail = "Texas: confirm ERCOT + serving TDSP large-load / interconnection path"
            source_label = "ERCOT / TDSP"
        else:
            status = "confirm"
            detail = "Confirm ISO / serving utility large-load path for this state"
            source_label = "Utility region"
        verified = False
    elif fill == "docs" and bits.get("documents"):
        status = "cited"
        docs = bits["documents"][:5]
        labels = []
        for d in docs:
            if isinstance(d, dict):
                labels.append(str(d.get("task") or d.get("label") or ""))
            else:
                labels.append(str(d))
        detail = "Typical submittals: " + "; ".join(x for x in labels if x)[:200]
        source_url = bits.get("portal") or ""
        source_label = "Document checklist"
        verified = False
    else:
        status = "confirm"
        detail = "Confirm with AHJ / utility / counsel — no automatic cite"
        source_label = "Confirm"

    # IC-only items stay Confirm on Pro depth unless already cited
    if item.get("_tier") == "ic" and depth != "ic" and status == "confirm":
        detail = (detail or "") + " (IC depth recommended)"

    return {
        "id": item.get("id"),
        "track": item.get("_track"),
        "priority": priority,
        "task": base_task,
        "status": status,  # cited | confirm
        "detail": detail,
        "source_url": source_url or None,
        "source_label": source_label or None,
        "verified": bool(verified and source_url),
        "responsible_party": "Contractor / permitting lead",
        "timeline": "Pre-bid",
        "notes": DATA_CENTER_PLAYBOOK["disclaimer"],
        "playbook_id": "data_center",
    }


def _moratorium_row(
    item: Dict[str, Any],
    track_id: str,
    *,
    analysis: Dict[str, Any],
    depth: str,
    disclaimer: str,
) -> Dict[str, Any]:
    radar = analysis.get("moratorium_radar") if isinstance(analysis.get("moratorium_radar"), dict) else {}
    tier = str(item.get("_tier") or "ic")
    row = {
        "id": item.get("id"),
        "track": track_id,
        "priority": item.get("priority") or "CRITICAL",
        "task": item.get("task"),
        "status": "cited" if radar.get("metros") or radar.get("high_alert") else "confirm",
        "detail": str(
            radar.get("stale_banner") or radar.get("summary") or "Confirm metro moratorium status"
        )[:240],
        "source_url": None,
        "source_label": "Moratorium radar",
        "verified": False,
        "responsible_party": "Contractor / counsel",
        "timeline": "Pre-bid",
        "notes": disclaimer,
        "playbook_id": "data_center",
    }
    if tier == "ic" and depth != "ic":
        row["detail"] = (row.get("detail") or "") + " (IC depth recommended)"
    return row


def fill_playbook(
    analysis: Dict[str, Any],
    *,
    depth: str = "pro",
) -> Dict[str, Any]:
    """
    Build vertical_playbook block + inject missing punch lines.
    depth: 'pro' | 'ic' — IC includes water/federal tracks as first-class.
    """
    if not isinstance(analysis, dict):
        return analysis
    if not _is_dc_analysis(analysis):
        return analysis

    playbook = DATA_CENTER_PLAYBOOK
    bits = _ahj_bits(analysis)
    pi = analysis.get("project_info") or {}
    state = str(pi.get("state") or "")
    depth_l = (depth or "pro").strip().lower()
    if analysis.get("research_depth") == "ic" or analysis.get("depth_tier") == "ic_full":
        depth_l = "ic"

    rows: List[Dict[str, Any]] = []
    for track in playbook.get("tracks") or []:
        tier = str(track.get("tier") or "pro")
        for it in track.get("items") or []:
            item = dict(it)
            item["_track"] = track.get("id")
            item["_tier"] = tier
            if item.get("fill") == "moratorium":
                rows.append(
                    _moratorium_row(
                        item,
                        str(track.get("id") or ""),
                        analysis=analysis,
                        depth=depth_l,
                        disclaimer=playbook["disclaimer"],
                    )
                )
            else:
                rows.append(_fill_item(item, bits=bits, depth=depth_l, state=state))

    cited = sum(1 for r in rows if r.get("status") == "cited")
    confirm = sum(1 for r in rows if r.get("status") == "confirm")
    total = len(rows) or 1
    completeness = round(cited / total, 3)

    analysis["vertical_playbook"] = {
        "id": playbook["id"],
        "label": playbook["label"],
        "depth": depth_l,
        "disclaimer": playbook["disclaimer"],
        "items": rows,
        "stats": {
            "total": len(rows),
            "cited": cited,
            "confirm": confirm,
            "completeness": completeness,
            "completeness_pct": int(round(completeness * 100)),
        },
        "beachhead_hint": (
            "Strongest citeable local depth: Dallas, Plano, Austin, Frisco, Fort Worth. "
            "Outside beachheads, expect more Confirm lines until packs deepen."
        ),
    }

    # Inject missing playbook tasks into punch list (dedupe by task substring)
    punch = dict(analysis.get("punch_list") or {})
    items = list(punch.get("punch_list") or [])
    existing = " ".join(str(i.get("task") or "").lower() for i in items if isinstance(i, dict))
    for r in rows:
        task = str(r.get("task") or "")
        key = task.lower()[:48]
        if not key or key in existing:
            continue
        # Prefer CRITICAL cited / confirm schedule killers
        if r.get("priority") not in ("CRITICAL", "HIGH"):
            continue
        items.insert(
            0,
            {
                "priority": r.get("priority"),
                "task": task,
                "responsible_party": r.get("responsible_party"),
                "timeline": r.get("timeline"),
                "estimated_cost": None,
                "notes": r.get("detail") or r.get("notes"),
                "source_url": r.get("source_url"),
                "source_label": r.get("source_label"),
                "verified": bool(r.get("verified")),
                "cost_verified": False,
                "playbook_id": "data_center",
                "playbook_status": r.get("status"),
            },
        )
        existing += " " + key

    punch["punch_list"] = items
    analysis["punch_list"] = punch

    # Honesty block for UI
    honesty = dict(analysis.get("honesty") or {})
    honesty["vertical_playbook"] = playbook["id"]
    honesty["playbook_completeness"] = completeness
    honesty["playbook_confirm_count"] = confirm
    honesty["disclaimer"] = playbook["disclaimer"]
    analysis["honesty"] = honesty
    return analysis


def apply_vertical_playbook(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Public entry — safe no-op when not a matching vertical."""
    try:
        return fill_playbook(analysis)
    except Exception:
        return analysis


def playbook_completeness(analysis: Dict[str, Any]) -> Tuple[float, int, int]:
    block = analysis.get("vertical_playbook") if isinstance(analysis, dict) else None
    if not isinstance(block, dict):
        return 0.0, 0, 0
    stats = block.get("stats") or {}
    return (
        float(stats.get("completeness") or 0.0),
        int(stats.get("cited") or 0),
        int(stats.get("confirm") or 0),
    )
