"""
IC Diligence Package composer — structured boardroom sections from analysis.

Produces a versioned JSON contract consumed by ic_boardroom_pdf.py.
This is the product-shape source of truth for the $1,500 IC Project deliverable.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

PACKAGE_SCHEMA = "regguard.ic_package.v2"
PACKAGE_VERSION = 2


def _s(v: Any, limit: int = 2000) -> str:
    t = str(v or "").strip()
    return t[:limit]


def _pi(analysis: Dict[str, Any]) -> Dict[str, Any]:
    pi = analysis.get("project_info") if isinstance(analysis.get("project_info"), dict) else {}
    if not pi.get("address"):
        loc = analysis.get("location") if isinstance(analysis.get("location"), dict) else {}
        return {
            "address": _s(loc.get("address") or "Project site", 200),
            "city": _s(loc.get("city"), 80),
            "state": _s(loc.get("state"), 8),
            "zip": _s(loc.get("zip") or loc.get("zip_code"), 16),
            "type": _s(analysis.get("project_type") or "commercial", 40),
        }
    return {
        "address": _s(pi.get("address"), 200),
        "city": _s(pi.get("city"), 80),
        "state": _s(pi.get("state"), 8),
        "zip": _s(pi.get("zip"), 16),
        "type": _s(pi.get("type") or analysis.get("project_type") or "commercial", 40),
    }


def _stamp_plain(grade: str) -> Dict[str, str]:
    g = (grade or "").upper()
    if g == "FAIL":
        return {
            "grade": "FAIL",
            "display": "HOLD",
            "label": "REGGUARD STAMP: HOLD — high pre-bid risk",
            "plain": (
                "HOLD means elevated pre-bid risk — not that the project is invalid or unplanned. "
                "Resolve the drivers below before locking a bid number or treating the site as clear."
            ),
        }
    if g == "CAUTION":
        return {
            "grade": "CAUTION",
            "display": "CAUTION",
            "label": "REGGUARD STAMP: CAUTION — review before bid",
            "plain": (
                "Material pre-bid risk remains. Review the drivers below before locking a number."
            ),
        }
    if g == "PASS":
        return {
            "grade": "PASS",
            "display": "CLEAR",
            "label": "REGGUARD STAMP: CLEAR",
            "plain": (
                "No Critical items on the current local pack. Still confirm fees and portal "
                "requirements with the AHJ before bid."
            ),
        }
    return {
        "grade": g or "UNKNOWN",
        "display": g or "UNKNOWN",
        "label": f"REGGUARD STAMP: {g or 'UNKNOWN'}",
        "plain": "Stamp grade unavailable — review findings before bid.",
    }


def _site_line(pi: Dict[str, Any]) -> str:
    street = _s(pi.get("address"))
    place = ", ".join(x for x in [_s(pi.get("city")), _s(pi.get("state")), _s(pi.get("zip"))] if x)
    if place and place.lower() not in street.lower():
        return f"{street} · {place}" if street else place
    return street or place or "Project site"


def _killers(analysis: Dict[str, Any], n: int = 5) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for k in analysis.get("margin_killers") or []:
        if not isinstance(k, dict):
            continue
        out.append(
            {
                "priority": _s(k.get("priority") or "NOTE", 20).upper(),
                "title": _s(k.get("title"), 160),
                "detail": _s(k.get("detail"), 400),
                "source_url": _s(k.get("source_url"), 400),
                "source_label": _s(
                    k.get("source_label") or ("Source" if k.get("source_url") else "Unverified"),
                    80,
                ),
            }
        )
        if len(out) >= n:
            break
    return out


def _gotchas(analysis: Dict[str, Any], n: int = 6) -> List[Dict[str, str]]:
    items: List[Dict[str, Any]] = []
    wl = analysis.get("gotcha_watchlist") if isinstance(analysis.get("gotcha_watchlist"), dict) else {}
    for g in wl.get("items") or []:
        if isinstance(g, dict):
            items.append(g)
    if not items:
        for g in analysis.get("margin_killers") or []:
            if isinstance(g, dict):
                items.append(g)
    out: List[Dict[str, str]] = []
    for g in items[:n]:
        out.append(
            {
                "priority": _s(g.get("priority") or "WATCH", 20).upper(),
                "title": _s(g.get("title"), 160),
                "detail": _s(g.get("detail"), 400),
                "confirm_step": _s(
                    g.get("confirm_step")
                    or g.get("action")
                    or "Confirm with AHJ / ordinance text before bid.",
                    240,
                ),
                "source_url": _s(g.get("source_url"), 400),
                "source_label": _s(
                    g.get("source_label") or ("Source" if g.get("source_url") else "Unverified"),
                    80,
                ),
            }
        )
    return out


def _punch(analysis: Dict[str, Any], n: int = 20) -> List[Dict[str, Any]]:
    punch = analysis.get("punch_list") if isinstance(analysis.get("punch_list"), dict) else {}
    raw = punch.get("punch_list") or punch.get("items") or []
    out: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        url = _s(item.get("source_url") or item.get("citation_url"), 400)
        out.append(
            {
                "priority": _s(item.get("priority") or "MEDIUM", 20).upper(),
                "task": _s(item.get("task") or item.get("action"), 280),
                "timeline": _s(item.get("timeline") or "Pre-bid", 40),
                "estimated_cost": item.get("estimated_cost"),
                "source_url": url,
                "citation": _s(
                    item.get("citation_label") or ("Source" if url else "Unverified"),
                    80,
                ),
            }
        )
        if len(out) >= n:
            break
    return out


def _fees(analysis: Dict[str, Any], n: int = 20) -> List[Dict[str, str]]:
    fee_card = analysis.get("fee_card") if isinstance(analysis.get("fee_card"), dict) else {}
    fees = fee_card.get("fees") or []
    out: List[Dict[str, str]] = []
    for f in fees:
        if not isinstance(f, dict):
            continue
        amt = f.get("amount_usd")
        if isinstance(amt, (int, float)):
            amount = f"${amt:,.0f}"
        elif f.get("amount_requires_schedule"):
            amount = "confirm on schedule"
        else:
            amount = _s(f.get("amount") or f.get("value") or f.get("range"), 80)
        src = _s(f.get("source_url") or f.get("citation_url"), 400)
        out.append(
            {
                "name": _s(f.get("name") or f.get("label") or f.get("fee"), 120),
                "amount": amount,
                "trade": _s(f.get("trade"), 40),
                "source_url": src,
                "source_label": _s(
                    f.get("source_label")
                    or f.get("citation_note")
                    or ("Source" if src else "Unverified — confirm with AHJ"),
                    80,
                ),
                "note": _s(
                    f.get("note")
                    or f.get("detail")
                    or "Planning aid — confirm on AHJ schedule",
                    200,
                ),
            }
        )
        if len(out) >= n:
            break
    return out


def _inspection_steps(analysis: Dict[str, Any], n: int = 15) -> List[str]:
    card = (
        analysis.get("inspection_sequence_card")
        if isinstance(analysis.get("inspection_sequence_card"), dict)
        else {}
    )
    steps: List[str] = []
    for s in card.get("steps") or []:
        t = _s(s, 220)
        if t:
            steps.append(t)
        if len(steps) >= n:
            break
    return steps


def _document_checklist(analysis: Dict[str, Any], n: int = 20) -> List[Dict[str, str]]:
    dc = (
        analysis.get("document_checklist")
        if isinstance(analysis.get("document_checklist"), dict)
        else {}
    )
    out: List[Dict[str, str]] = []
    for d in dc.get("items") or []:
        if isinstance(d, dict):
            task = _s(d.get("task") or d.get("item") or d.get("title"), 220)
            if not task:
                continue
            out.append(
                {
                    "task": task,
                    "note": _s(d.get("note") or d.get("detail"), 160),
                }
            )
        else:
            task = _s(d, 220)
            if task:
                out.append({"task": task, "note": ""})
        if len(out) >= n:
            break
    return out


def _sources(analysis: Dict[str, Any], limit: int = 60) -> List[Dict[str, str]]:
    seen = set()
    out: List[Dict[str, str]] = []

    def add(url: Any, label: str = "") -> None:
        u = _s(url, 400)
        if not u or not u.startswith("http") or u in seen:
            return
        seen.add(u)
        host = u.replace("https://", "").replace("http://", "")
        out.append({"url": u, "label": _s(label or host, 120)})

    for u in analysis.get("pro_source_urls") or []:
        add(u, "Scout source")
    ahj = analysis.get("ahj_card") if isinstance(analysis.get("ahj_card"), dict) else {}
    add(ahj.get("portal_url"), _s(ahj.get("name") or "AHJ portal", 80))
    add(ahj.get("fees_url"), "AHJ fees")
    add(ahj.get("apply_url"), "AHJ apply")
    add(ahj.get("inspections_url"), "AHJ inspections")
    for k in analysis.get("margin_killers") or []:
        if isinstance(k, dict):
            add(k.get("source_url"), _s(k.get("source_label") or k.get("title"), 80))
    wl = analysis.get("gotcha_watchlist") if isinstance(analysis.get("gotcha_watchlist"), dict) else {}
    for g in wl.get("items") or []:
        if isinstance(g, dict):
            add(g.get("source_url"), _s(g.get("source_label") or g.get("title"), 80))
    punch = analysis.get("punch_list") if isinstance(analysis.get("punch_list"), dict) else {}
    for item in punch.get("punch_list") or []:
        if isinstance(item, dict):
            add(item.get("source_url") or item.get("citation_url"), _s(item.get("task"), 80))
    fee_card = analysis.get("fee_card") if isinstance(analysis.get("fee_card"), dict) else {}
    for f in fee_card.get("fees") or []:
        if isinstance(f, dict):
            add(
                f.get("source_url") or f.get("citation_url"),
                _s(f.get("source_label") or f.get("label") or "Fee source", 80),
            )
    return out[:limit]


def _next_actions(analysis: Dict[str, Any], n: int = 5) -> List[str]:
    pi = _pi(analysis)
    ahj = analysis.get("ahj_card") if isinstance(analysis.get("ahj_card"), dict) else {}
    ahj_name = _s(ahj.get("name") or (f"City of {pi.get('city')}" if pi.get("city") else "the local AHJ"), 80)
    actions: List[str] = []
    for k in _killers(analysis, 3):
        title = k.get("title") or "priority risk"
        actions.append(f"Confirm and close out: {title} — document the AHJ or utility response in the bid file.")
    for g in _gotchas(analysis, 2):
        step = _s(g.get("confirm_step") or g.get("title"), 200)
        if step and step not in actions:
            if not step.lower().startswith(("confirm", "verify", "pull", "treat", "schedule")):
                step = f"Confirm with {ahj_name}: {step}"
            actions.append(step)
    env = analysis.get("environmental_screening") if isinstance(analysis.get("environmental_screening"), dict) else {}
    for a in env.get("action_plan") or []:
        s = _s(a, 200)
        if s and s not in actions:
            actions.append(s)
    for s in analysis.get("next_steps") or []:
        t = _s(s, 200)
        if t and t not in actions:
            actions.append(t)
    if not actions:
        actions = [
            f"Confirm permit fees and trade registrations with {ahj_name}.",
            "Review punch-list HIGH and CRITICAL lines before bid day.",
            "Verify utility / interconnection lead times for this site.",
        ]
    return actions[:n]


def _contingency_driver_table(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """What pushes low / mid / high ends of the contingency band."""
    rows: List[Dict[str, str]] = []
    low_d: List[str] = []
    mid_d: List[str] = []
    high_d: List[str] = []

    coverage = analysis.get("coverage") if isinstance(analysis.get("coverage"), dict) else {}
    tier = _s(coverage.get("tier") or analysis.get("depth_tier"), 40).lower()
    fee_n = len(_fees(analysis, 20))
    killers = _killers(analysis, 5)
    gotchas = _gotchas(analysis, 6)
    env = analysis.get("environmental_screening") if isinstance(analysis.get("environmental_screening"), dict) else {}
    clocks = analysis.get("parallel_clocks") if isinstance(analysis.get("parallel_clocks"), dict) else {}
    clock_n = len(clocks.get("clocks") or [])

    # Base fee / schedule uncertainty
    mid_d.append("AHJ fee schedule still requires live confirm")
    rows.append(
        {
            "driver": "AHJ fee / schedule confirm",
            "band": "MID",
            "impact": "+2 to +4 pts typical until schedule confirm",
            "owner": "Estimator",
        }
    )
    if fee_n == 0 or tier in ("portal_seed", "federal_state"):
        high_d.append("Thin/portal-only local fee coverage")
        rows.append(
            {
                "driver": "Portal-only or thin local fee coverage",
                "band": "HIGH",
                "impact": "Push toward top of band until citeable fees confirmed",
                "owner": "Estimator / IC",
            }
        )
    else:
        low_d.append("Citeable local fee/gotcha pack available")

    for k in killers:
        pri = (k.get("priority") or "").upper()
        title = k.get("title") or "Risk flag"
        if pri in ("CRITICAL", "HIGH"):
            high_d.append(title)
            rows.append(
                {
                    "driver": f"[{pri}] {title}",
                    "band": "HIGH",
                    "impact": "Material pre-bid exposure — resolve or carry cushion",
                    "owner": "PM / Estimator",
                }
            )
        else:
            mid_d.append(title)
            rows.append(
                {
                    "driver": f"[{pri or 'NOTE'}] {title}",
                    "band": "MID",
                    "impact": "Watch item — confirm before lock",
                    "owner": "Estimator",
                }
            )

    for g in gotchas[:3]:
        title = g.get("title") or "Local gotcha"
        if title in high_d or title in mid_d:
            continue
        mid_d.append(title)
        rows.append(
            {
                "driver": f"[GOTCHA] {title}",
                "band": "MID",
                "impact": "Local ordinance / process risk",
                "owner": "Field / Estimator",
            }
        )

    env_risk = _s(env.get("risk_level"), 20).upper()
    if env_risk in ("HIGH", "CRITICAL"):
        high_d.append(f"Environmental risk {env_risk}")
        rows.append(
            {
                "driver": f"Environmental screening {env_risk}",
                "band": "HIGH",
                "impact": "Parcel/env uncertainty until verified",
                "owner": "IC / Env",
            }
        )
    elif env_risk:
        mid_d.append(f"Environmental risk {env_risk}")

    if clock_n >= 2:
        high_d.append("Parallel AHJ + utility clocks")
        rows.append(
            {
                "driver": "Parallel AHJ + utility clocks",
                "band": "HIGH",
                "impact": "Two independent timelines — slip risk stacks",
                "owner": "PM",
            }
        )

    if not low_d:
        low_d.append("No Critical killers cleared yet — low end only if drivers resolve")

    return {
        "low_end": low_d[:5],
        "mid_band": mid_d[:5],
        "high_end": high_d[:5],
        "rows": rows[:10],
    }


def _gotcha_cards(analysis: Dict[str, Any], n: int = 6) -> List[Dict[str, Any]]:
    """Boardroom gotcha cards: ordinance -> risk -> confirm -> owner."""
    cards: List[Dict[str, Any]] = []
    # Prefer AHJ library gotchas with checklists when enrichment attached them
    candidates: List[Dict[str, Any]] = []
    wl = analysis.get("gotcha_watchlist") if isinstance(analysis.get("gotcha_watchlist"), dict) else {}
    for g in wl.get("items") or []:
        if isinstance(g, dict):
            candidates.append(g)
    # From city pack / local_pack
    for key in ("local_pack", "pdf_pack"):
        pack = analysis.get(key) if isinstance(analysis.get(key), dict) else {}
        for g in pack.get("gotchas") or []:
            if isinstance(g, dict):
                candidates.append(g)
    # Fallback killers
    if len(candidates) < 2:
        for k in analysis.get("margin_killers") or []:
            if isinstance(k, dict):
                candidates.append(k)

    seen = set()
    for g in candidates:
        title = _s(g.get("title"), 160)
        if not title or title.lower() in seen:
            continue
        seen.add(title.lower())
        checklist = g.get("checklist") if isinstance(g.get("checklist"), list) else []
        anti = g.get("anti_patterns") if isinstance(g.get("anti_patterns"), list) else []
        confirm = _s(
            g.get("confirm_step")
            or g.get("action")
            or (checklist[0] if checklist else "Confirm with AHJ / ordinance text before bid."),
            240,
        )
        cards.append(
            {
                "priority": _s(g.get("priority") or "WATCH", 20).upper(),
                "title": title,
                "detail": _s(g.get("detail"), 400),
                "checklist": [_s(c, 160) for c in checklist[:4]],
                "anti_patterns": [_s(a, 160) for a in anti[:3]],
                "confirm_step": confirm,
                "owner": _s(g.get("owner") or "Estimator / PM", 40),
                "source_url": _s(g.get("source_url") or g.get("citation_url"), 400),
                "source_label": _s(
                    g.get("source_label")
                    or ("Source" if (g.get("source_url") or g.get("citation_url")) else "Unverified"),
                    80,
                ),
            }
        )
        if len(cards) >= n:
            break
    return cards


def _contingency_block(analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    band = analysis.get("contingency_band") if isinstance(analysis.get("contingency_band"), dict) else None
    if not band or band.get("pct_low") is None or band.get("pct_high") is None:
        return None
    low, mid, high = band.get("pct_low"), band.get("pct_mid"), band.get("pct_high")
    table = _contingency_driver_table(analysis)
    drivers = [f"{k['priority']}: {k['title']}" for k in _killers(analysis, 3)]
    if not drivers:
        drivers = list(table.get("high_end") or table.get("mid_band") or ["Portal confirm still required"])
    return {
        "pct_low": low,
        "pct_mid": mid,
        "pct_high": high,
        "label": _s(band.get("label") or "Suggested bid contingency cushion", 120),
        "plain": (
            f"Plan a {low}%–{high}% cushion on your base estimate for local fees, "
            f"review timing, and site risk (midpoint {mid}%). "
            "This is a planning aid — not a quote or guarantee. Confirm final dollars with the AHJ."
        ),
        "drivers": drivers,
        "driver_table": table,
        "disclaimer": _s(
            band.get("disclaimer") or "Confirm dollars on the official AHJ schedule before bid.",
            300,
        ),
    }


def _parallel_clock_rows(
    analysis: Dict[str, Any],
    pi: Dict[str, Any],
    killers: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    """AHJ + interconnect + water/NPDES clocks for large-load / data-center sites."""
    clocks = analysis.get("parallel_clocks") if isinstance(analysis.get("parallel_clocks"), dict) else {}
    rows: List[Dict[str, str]] = []
    for c in clocks.get("clocks") or []:
        if not isinstance(c, dict):
            continue
        rows.append(
            {
                "name": _s(c.get("name") or c.get("label"), 80),
                "detail": _s(c.get("detail") or c.get("note") or c.get("status"), 240),
                "owner": _s(c.get("owner") or c.get("responsible") or "PM", 40),
                "track": _s(c.get("track") or "", 40),
            }
        )
    blob = " ".join(
        [
            _s(pi.get("type")),
            _s(analysis.get("project_type")),
            " ".join(_s(k.get("title")) + " " + _s(k.get("detail")) for k in killers),
            _s((analysis.get("dc_positioning") or {}).get("headline") if isinstance(analysis.get("dc_positioning"), dict) else ""),
        ]
    ).lower()
    large = any(
        x in blob
        for x in (
            "data-center",
            "data center",
            "large-load",
            "large load",
            "interconnect",
            "mission-critical",
            "colo",
            "hyperscale",
        )
    )
    if large:
        city = _s(pi.get("city") or "Local", 40)
        st = _s(pi.get("state"), 8).upper()
        have = " ".join(r["name"].lower() + " " + r["detail"].lower() for r in rows)

        def _ensure(name: str, detail: str, track: str, owner: str) -> None:
            key = name.lower().split()[0]
            if any(key in (r.get("name") or "").lower() or key in (r.get("detail") or "").lower() for r in rows):
                return
            if any(t in have for t in track.lower().split("/") if len(t) > 3):
                # still add if track keyword missing from names
                pass
            rows.append({"name": name, "detail": detail, "owner": owner, "track": track})

        if "ahj" not in have and "permit" not in have and "municipal" not in have:
            _ensure(
                f"{city} AHJ permits",
                "Municipal plan review / trade permits run on the city clock — independent of utility.",
                "AHJ",
                "Permit runner / Estimator",
            )
        if "utility" not in have and "interconnect" not in have and "tdsp" not in have and "ercot" not in have:
            util = (
                "ERCOT / TDSP large-load interconnection (Texas)"
                if st in ("TX", "TEXAS")
                else "Serving utility / ISO interconnection"
            )
            _ensure(
                util,
                "Interconnection / large-load study often runs parallel to AHJ permits — slip stacks.",
                "INTERCONNECT",
                "Owner / Utility lead",
            )
        if "npdes" not in have and "water" not in have and "cooling" not in have and "stormwater" not in have:
            _ensure(
                "Water / NPDES / cooling path",
                "Consumptive use, discharge, and construction stormwater (NPDES/CGP) can gate schedule "
                "independently of building permits — confirm early for cooling-heavy loads.",
                "WATER_NPDES",
                "Env / Civil",
            )
    # Normalize missing fields on existing rows
    for r in rows:
        r.setdefault("owner", "PM")
        r.setdefault("track", "")
    return rows[:8]


def build_evidence_binder(
    *,
    killers: List[Dict[str, str]],
    fees: List[Dict[str, str]],
    punch: List[Dict[str, Any]],
    gotchas: List[Dict[str, str]],
    sources: List[Dict[str, str]],
    ahj: Dict[str, Any],
    clocks: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    Numbered exhibits mapped to HOLD / fee / punch claims.

    Exhibit IDs are stable for this package generation (EX-001…). Claims without a
    URL are listed as Unverified and do not receive an exhibit number.
    """
    exhibits: List[Dict[str, Any]] = []
    by_url: Dict[str, str] = {}
    claims: List[Dict[str, Any]] = []

    def _exhibit_for(url: str, title: str, kind: str) -> Optional[str]:
        u = _s(url, 400)
        if not u.startswith("http"):
            return None
        if u in by_url:
            return by_url[u]
        eid = f"EX-{len(exhibits) + 1:03d}"
        by_url[u] = eid
        exhibits.append(
            {
                "id": eid,
                "title": _s(title, 160) or f"Exhibit {eid}",
                "kind": kind,
                "url": u,
            }
        )
        return eid

    def _claim(
        *,
        claim_type: str,
        label: str,
        detail: str = "",
        url: str = "",
        priority: str = "",
        trade: str = "",
        owner: str = "",
    ) -> None:
        eid = _exhibit_for(url, label, claim_type)
        claims.append(
            {
                "claim_type": claim_type,
                "label": _s(label, 200),
                "detail": _s(detail, 400),
                "priority": _s(priority, 20).upper(),
                "trade": _s(trade, 40).upper(),
                "owner": _s(owner, 60),
                "exhibit_id": eid or "",
                "source_url": _s(url, 400),
                "status": "EXHIBITED" if eid else "UNVERIFIED",
            }
        )

    # AHJ portals first (foundation exhibits)
    if ahj.get("portal_url"):
        _claim(
            claim_type="ahj",
            label=f"AHJ portal — {_s(ahj.get('name') or 'Local AHJ', 80)}",
            url=_s(ahj.get("portal_url"), 400),
            owner="Permit runner",
        )
    if ahj.get("fees_url") and _s(ahj.get("fees_url")) != _s(ahj.get("portal_url")):
        _claim(
            claim_type="ahj_fees",
            label="AHJ fee schedule",
            url=_s(ahj.get("fees_url"), 400),
            owner="Estimator",
        )

    for k in killers:
        _claim(
            claim_type="hold_driver",
            label=_s(k.get("title"), 160),
            detail=_s(k.get("detail"), 400),
            url=_s(k.get("source_url"), 400),
            priority=_s(k.get("priority"), 20),
            owner="IC / Estimator",
        )

    for g in gotchas:
        _claim(
            claim_type="gotcha",
            label=_s(g.get("title"), 160),
            detail=_s(g.get("detail"), 400),
            url=_s(g.get("source_url"), 400),
            priority=_s(g.get("priority"), 20),
            owner=_s(g.get("owner") or "Estimator / PM", 60),
        )

    for f in fees:
        _claim(
            claim_type="fee",
            label=_s(f.get("name"), 120),
            detail=_s(f.get("note") or f.get("amount"), 200),
            url=_s(f.get("source_url"), 400),
            trade=_s(f.get("trade"), 40),
            owner="Estimator / Permit runner",
        )

    for item in punch:
        _claim(
            claim_type="punch",
            label=_s(item.get("task"), 200),
            detail=_s(item.get("timeline"), 80),
            url=_s(item.get("source_url"), 400),
            priority=_s(item.get("priority"), 20),
            trade=_s(item.get("trade"), 40),
            owner=_s(item.get("owner") or item.get("responsible_party") or "Estimator / PM", 60),
        )

    for c in clocks:
        # Clocks rarely have URLs; still list as claims for the track
        _claim(
            claim_type="parallel_clock",
            label=_s(c.get("name"), 80),
            detail=_s(c.get("detail"), 240),
            url="",
            owner=_s(c.get("owner") or "PM", 60),
        )

    # Orphan scout sources not yet claimed
    claimed_urls = {e["url"] for e in exhibits}
    for src in sources:
        u = _s(src.get("url"), 400)
        if u.startswith("http") and u not in claimed_urls:
            _exhibit_for(u, _s(src.get("label") or "Scout source", 120), "source")

    exhibited = sum(1 for c in claims if c.get("exhibit_id"))
    unverified = sum(1 for c in claims if not c.get("exhibit_id"))
    return {
        "exhibits": exhibits,
        "claims": claims,
        "summary": {
            "exhibit_count": len(exhibits),
            "claim_count": len(claims),
            "exhibited_claims": exhibited,
            "unverified_claims": unverified,
        },
    }


def evidence_index_to_csv(binder: Dict[str, Any], *, site: str = "") -> str:
    """CSV index of exhibits + claim→exhibit map for Excel."""
    import csv
    import io

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
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
    )
    for ex in binder.get("exhibits") or []:
        w.writerow(
            [
                "exhibit",
                ex.get("id"),
                ex.get("kind"),
                "",
                "",
                "",
                ex.get("title"),
                "",
                "EXHIBIT",
                ex.get("url"),
                site,
            ]
        )
    for c in binder.get("claims") or []:
        w.writerow(
            [
                "claim",
                c.get("exhibit_id") or "",
                c.get("claim_type"),
                c.get("priority"),
                c.get("trade"),
                c.get("owner"),
                c.get("label"),
                c.get("detail"),
                c.get("status"),
                c.get("source_url"),
                site,
            ]
        )
    return buf.getvalue()


def compose_ic_package(
    analysis: Dict[str, Any],
    *,
    generated_for: str = "",
    share_url: str = "",
) -> Dict[str, Any]:
    """Build the boardroom package contract from live analysis."""
    data = dict(analysis or {})
    try:
        from delivery_parity import prepare_analysis_for_delivery

        data = prepare_analysis_for_delivery(data)
    except Exception:
        pass
    try:
        from ic_pdf_enrichment import enrich_analysis_for_ic_pdfs

        data = enrich_analysis_for_ic_pdfs(data)
    except Exception:
        pass

    pi = _pi(data)
    stamp_raw = data.get("regguard_stamp") if isinstance(data.get("regguard_stamp"), dict) else {}
    grade = _s(stamp_raw.get("grade") or data.get("stamp_grade"), 16)
    stamp = _stamp_plain(grade)
    stamp["headline"] = _s(stamp_raw.get("headline") or stamp["plain"], 400)
    stamp["drivers"] = []
    for d in stamp_raw.get("drivers") or []:
        if not isinstance(d, dict):
            continue
        sev = _s(d.get("severity"), 20).upper()
        if sev == "FAIL":
            sev = "HOLD"
        stamp["drivers"].append(
            {
                "severity": sev,
                "label": _s(d.get("label"), 160),
                "detail": _s(d.get("detail"), 300),
            }
        )
    stamp["valid_until"] = _s(stamp_raw.get("valid_until") or data.get("stamp_valid_until"), 64)
    stamp["fingerprint"] = _s(stamp_raw.get("fingerprint") or data.get("stamp_fingerprint"), 64)

    ahj = data.get("ahj_card") if isinstance(data.get("ahj_card"), dict) else {}
    coverage = data.get("coverage") if isinstance(data.get("coverage"), dict) else {}
    env = data.get("environmental_screening") if isinstance(data.get("environmental_screening"), dict) else {}
    clocks = data.get("parallel_clocks") if isinstance(data.get("parallel_clocks"), dict) else {}
    share = _s(share_url or data.get("share_url"), 300)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    killers = _killers(data, 5)
    gotchas = _gotchas(data, 8)
    punch = _punch(data, 35)
    fees = _fees(data, 20)
    sources = _sources(data, 60)
    actions = _next_actions(data, 6)
    contingency = _contingency_block(data)
    clock_rows = _parallel_clock_rows(data, pi, killers)
    inspection_steps = _inspection_steps(data, 15)
    doc_checklist = _document_checklist(data, 20)
    binder = build_evidence_binder(
        killers=killers,
        fees=fees,
        punch=punch,
        gotchas=gotchas,
        sources=sources,
        ahj=ahj,
        clocks=clock_rows,
    )
    # Stamp exhibit IDs onto punch / fee / killer rows for DOCX + CSV consumers
    url_to_ex = {e["url"]: e["id"] for e in binder.get("exhibits") or [] if e.get("url")}
    for k in killers:
        u = _s(k.get("source_url"), 400)
        if u in url_to_ex:
            k["exhibit_id"] = url_to_ex[u]
    for f in fees:
        u = _s(f.get("source_url"), 400)
        if u in url_to_ex:
            f["exhibit_id"] = url_to_ex[u]
    for item in punch:
        u = _s(item.get("source_url"), 400)
        if u in url_to_ex:
            item["exhibit_id"] = url_to_ex[u]

    depth = _s(
        data.get("depth_badge")
        or coverage.get("badge")
        or (
            "IC Project - full scout"
            if data.get("ic_package") or data.get("depth_tier") == "ic_full"
            else ""
        ),
        120,
    )

    punch_obj = data.get("punch_list") if isinstance(data.get("punch_list"), dict) else {}
    site_line = _site_line(pi)
    ahj_name = _s(ahj.get("name") or f"City of {pi.get('city') or 'Local'}", 120)
    if stamp.get("display") == "HOLD":
        headline = (
            f"{site_line} carries elevated pre-bid risk under {ahj_name}. "
            "Treat municipal permits and utility interconnection as separate clocks until both are confirmed."
        )
    elif stamp.get("display") == "CAUTION":
        headline = (
            f"{site_line} has material pre-bid items under {ahj_name} "
            "that should be cleared before you lock a number."
        )
    else:
        headline = (
            f"{site_line}: review the contingency band and priority items below, "
            f"then confirm dollars on the {ahj_name} fee schedule before bid."
        )

    top3 = killers[:3]
    decision_memo = {
        "title": "One-page decision memo",
        "stamp": stamp,
        "contingency": contingency,
        "top_drivers": [
            {
                **k,
                "exhibit_id": k.get("exhibit_id") or "",
            }
            for k in top3
        ],
        "headline": headline,
        "recommendation": (
            f"REGGUARD STAMP: {stamp.get('display') or grade or 'UNKNOWN'} — "
            + (
                f"carry +{contingency.get('pct_low')}% to +{contingency.get('pct_high')}% contingency"
                if contingency and contingency.get("pct_low") is not None
                else "confirm contingency with estimator"
            )
        ),
    }

    is_dc = any(
        x in " ".join([_s(pi.get("type")), _s(data.get("project_type"))]).lower()
        for x in ("data-center", "data center", "colo", "large-load", "large load", "hyperscale")
    ) or bool(data.get("dc_positioning")) or len(clock_rows) >= 2

    pkg = {
        "schema": PACKAGE_SCHEMA,
        "version": PACKAGE_VERSION,
        "generated_at": now,
        "generated_for": _s(generated_for, 120).lower(),
        "share_url": share,
        "deliverable": {
            "primary": "IC Diligence Bundle (DOCX + CSV schedule + evidence index + decision memo PDF)",
            "forward_artifact": "Bid Risk Receipt PDF (1-page stamp / contingency / top drivers)",
            "price_positioning": "$1,500 IC Project — counsel-ready diligence package for one site",
        },
        "cover": {
            "product": f"RegGuard IC Diligence Package — {site_line}",
            "price_positioning": "$1,500 IC Project — decision memo + counsel DOCX + fee/punch CSV + evidence binder",
            "site": site_line,
            "address": pi.get("address"),
            "city": pi.get("city"),
            "state": pi.get("state"),
            "zip": pi.get("zip"),
            "project_type": pi.get("type"),
            "ahj_name": ahj_name,
            "depth_badge": depth,
            "coverage_badge": _s(coverage.get("badge") or coverage.get("badge_short"), 80),
            "research_id": _s(data.get("research_id"), 80),
            "is_data_center_track": is_dc,
        },
        "decision_memo": decision_memo,
        "executive_summary": {
            "headline": headline,
            "stamp": stamp,
            "contingency": contingency,
            "top_risks": top3,
            "local_gotchas": gotchas[:3],
            "next_actions": actions[:3],
            "env_risk": _s(env.get("risk_level"), 40),
        },
        "bid_risk_receipt": {
            "title": "Bid Risk Receipt - forward to GC / owner",
            "stamp": stamp,
            "contingency": contingency,
            "killers": top3,
            "share_url": share,
            "disclaimer": (
                "Planning aid for citeable pre-bid / pre-LOI screening only. "
                "NOT a quote, sealed bid, bond, insurance quote, legal opinion, "
                "AHJ approval, interconnection study, or geotech report."
            ),
        },
        "site_findings": {
            "ahj": {
                "name": _s(ahj.get("name"), 120),
                "portal_url": _s(ahj.get("portal_url"), 400),
                "fees_url": _s(ahj.get("fees_url"), 400),
                "apply_url": _s(ahj.get("apply_url"), 400),
                "inspections_url": _s(ahj.get("inspections_url"), 400),
                "last_verified": _s(ahj.get("last_verified"), 40),
                "notes": _s(ahj.get("notes"), 400),
            },
            "coverage_note": _s(coverage.get("warning") or coverage.get("note"), 400),
            "fees": fees,
            "gotchas": gotchas,
            "gotcha_cards": _gotcha_cards(data, 8),
            "inspection_sequence": inspection_steps,
            "document_checklist": doc_checklist,
            "env_risk": _s(env.get("risk_level"), 40),
            "env_findings": [
                {
                    "category": _s(f.get("category"), 80),
                    "description": _s(f.get("description"), 400),
                    "source_url": _s(f.get("source_url"), 400),
                    "risk_level": _s(f.get("risk_level"), 20),
                }
                for f in (env.get("findings") or [])[:8]
                if isinstance(f, dict)
            ],
            "parallel_clocks": clock_rows,
        },
        "parallel_clocks_track": {
            "enabled": is_dc or len(clock_rows) >= 2,
            "title": "Data-center / large-load parallel clocks",
            "headline": (
                "AHJ permits, interconnection, and water/NPDES run as independent clocks — "
                "schedule risk stacks when any one slips."
            ),
            "clocks": clock_rows,
        },
        "punch_list": {
            "timeline_summary": _s(punch_obj.get("timeline_summary"), 80),
            "items": punch,
        },
        "evidence_binder": binder,
        "action_plan_summary": actions,
        "action_plan_excerpt": _s((data.get("pro_summary_markdown") or "")[:2500], 2500),
        "sources": sources,
        "disclaimers": [
            "Planning aid only — citeable pre-bid diligence, not a quote or sealed bid.",
            "Unverified lines and fee dollars require confirm-with-AHJ on the official schedule.",
            "NOT an interconnection study, geotech report, power study, or AHJ approval.",
            "Stamp CLEAR / CAUTION / HOLD is a pre-bid risk signal, not a credit rating or AHJ rejection.",
            "Dollar and day figures are planning aids unless marked citeable and still require live confirm.",
            "Evidence exhibits are hyperlinks to official sources — counsel should verify currency before reliance.",
            "Payments are handled by Stripe Checkout — Reg Guard does not store card numbers.",
            "Package bound to the site address shown on the cover at generation time.",
        ],
    }
    try:
        from ic_package_qa import score_boardroom_package

        pkg["boardroom_qa"] = score_boardroom_package(pkg)
    except Exception:
        pkg["boardroom_qa"] = {"score": 0, "pass": False, "gaps": ["qa_unavailable"]}
    return pkg
