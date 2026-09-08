"""
IC Diligence Package composer — structured boardroom sections from analysis.

Produces a versioned JSON contract consumed by ic_boardroom_pdf.py.
This is the product-shape source of truth for the $1,500 IC Project deliverable.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

PACKAGE_SCHEMA = "regguard.ic_package.v1"
PACKAGE_VERSION = 1


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
                "High pre-bid risk on this site. Not a rejection of the job — "
                "resolve the drivers below before treating the bid as clear."
            ),
        }
    if g == "CAUTION":
        return {
            "grade": "CAUTION",
            "display": "CAUTION",
            "label": "REGGUARD STAMP: CAUTION — review before bid",
            "plain": "Material pre-bid risk — review drivers before locking a number.",
        }
    if g == "PASS":
        return {
            "grade": "PASS",
            "display": "CLEAR",
            "label": "REGGUARD STAMP: CLEAR",
            "plain": (
                "No Critical killers on the current citeable pack — still confirm "
                "fees and portal asks with the AHJ before bid."
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


def _fees(analysis: Dict[str, Any], n: int = 10) -> List[Dict[str, str]]:
    fee_card = analysis.get("fee_card") if isinstance(analysis.get("fee_card"), dict) else {}
    fees = fee_card.get("fees") or []
    out: List[Dict[str, str]] = []
    for f in fees:
        if not isinstance(f, dict):
            continue
        out.append(
            {
                "name": _s(f.get("name") or f.get("label") or f.get("fee"), 120),
                "amount": _s(f.get("amount") or f.get("value") or f.get("range"), 80),
                "note": _s(
                    f.get("note") or f.get("detail") or "Planning aid — confirm on AHJ schedule",
                    200,
                ),
            }
        )
        if len(out) >= n:
            break
    return out


def _sources(analysis: Dict[str, Any], limit: int = 40) -> List[Dict[str, str]]:
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
    return out[:limit]


def _next_actions(analysis: Dict[str, Any], n: int = 5) -> List[str]:
    actions: List[str] = []
    for k in _killers(analysis, 3):
        actions.append(f"Resolve: {k['title']}")
    for g in _gotchas(analysis, 2):
        step = g.get("confirm_step") or g["title"]
        if step not in actions:
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
            "Confirm permit fees and trade registrations with the local AHJ.",
            "Review punch list HIGH/CRITICAL lines before bid day.",
            "Verify utility / interconnection lead times for this site.",
        ]
    return actions[:n]


def _contingency_block(analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    band = analysis.get("contingency_band") if isinstance(analysis.get("contingency_band"), dict) else None
    if not band or band.get("pct_low") is None or band.get("pct_high") is None:
        return None
    low, mid, high = band.get("pct_low"), band.get("pct_mid"), band.get("pct_high")
    drivers = [f"{k['priority']}: {k['title']}" for k in _killers(analysis, 3)]
    if not drivers:
        drivers = ["Local AHJ fee / timeline uncertainty", "Portal confirm still required"]
    return {
        "pct_low": low,
        "pct_mid": mid,
        "pct_high": high,
        "label": _s(band.get("label") or "Suggested bid contingency cushion", 120),
        "plain": (
            f"Add about {low}%-{high}% on top of your base estimate for AHJ fee, "
            f"timeline, and local-risk exposure on this site (mid {mid}%). "
            "Planning aid - not a quote or guarantee."
        ),
        "drivers": drivers,
        "disclaimer": _s(
            band.get("disclaimer") or "Confirm dollars on the official AHJ schedule before bid.",
            300,
        ),
    }


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
    gotchas = _gotchas(data, 6)
    punch = _punch(data, 25)
    fees = _fees(data, 12)
    sources = _sources(data, 40)
    actions = _next_actions(data, 5)
    contingency = _contingency_block(data)

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

    return {
        "schema": PACKAGE_SCHEMA,
        "version": PACKAGE_VERSION,
        "generated_at": now,
        "generated_for": _s(generated_for, 120).lower(),
        "share_url": share,
        "cover": {
            "product": "RegGuard IC Project Diligence Package",
            "price_positioning": "$1,500 IC Project Report - bound site diligence",
            "site": _site_line(pi),
            "address": pi.get("address"),
            "city": pi.get("city"),
            "state": pi.get("state"),
            "zip": pi.get("zip"),
            "project_type": pi.get("type"),
            "ahj_name": _s(ahj.get("name") or f"{pi.get('city') or 'Local'} AHJ", 120),
            "depth_badge": depth,
            "coverage_badge": _s(coverage.get("badge") or coverage.get("badge_short"), 80),
            "research_id": _s(data.get("research_id"), 80),
        },
        "executive_summary": {
            "headline": "What matters before you bid",
            "stamp": stamp,
            "contingency": contingency,
            "top_risks": killers[:3],
            "local_gotchas": gotchas[:3],
            "next_actions": actions[:3],
            "env_risk": _s(env.get("risk_level"), 40),
        },
        "bid_risk_receipt": {
            "title": "Bid Risk Receipt - forward to GC / owner",
            "stamp": stamp,
            "contingency": contingency,
            "killers": killers[:3],
            "share_url": share,
            "disclaimer": (
                "Planning aid for pre-bid / pre-LOI screening only. "
                "NOT a bond, insurance quote, legal opinion, AHJ approval, or interconnection study."
            ),
        },
        "site_findings": {
            "ahj": {
                "name": _s(ahj.get("name"), 120),
                "portal_url": _s(ahj.get("portal_url"), 400),
                "fees_url": _s(ahj.get("fees_url"), 400),
                "last_verified": _s(ahj.get("last_verified"), 40),
            },
            "coverage_note": _s(coverage.get("warning") or coverage.get("note"), 400),
            "fees": fees,
            "gotchas": gotchas,
            "env_risk": _s(env.get("risk_level"), 40),
            "env_findings": [
                {
                    "category": _s(f.get("category"), 80),
                    "description": _s(f.get("description"), 400),
                }
                for f in (env.get("findings") or [])[:6]
                if isinstance(f, dict)
            ],
            "parallel_clocks": [
                {
                    "name": _s(c.get("name") or c.get("label"), 80),
                    "detail": _s(c.get("detail") or c.get("note") or c.get("status"), 240),
                }
                for c in (clocks.get("clocks") or [])[:6]
                if isinstance(c, dict)
            ],
        },
        "punch_list": {
            "timeline_summary": _s(punch_obj.get("timeline_summary"), 80),
            "items": punch,
        },
        "action_plan_summary": actions,
        "action_plan_excerpt": _s((data.get("pro_summary_markdown") or "")[:2500], 2500),
        "sources": sources,
        "disclaimers": [
            "Planning aid only - confirm all fees, timelines, and portal asks with the AHJ.",
            "Stamp CLEAR / CAUTION / HOLD is a pre-bid risk signal, not a credit rating or AHJ rejection.",
            "Dollar and day figures are planning aids unless marked citeable and still require live confirm.",
            "Package bound to the site address shown on the cover at generation time.",
        ],
    }
