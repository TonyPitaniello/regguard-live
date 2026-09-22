"""
IC Diligence Package composer — structured boardroom sections from analysis.

Produces a versioned JSON contract consumed by ic_boardroom_pdf.py.
This is the product-shape source of truth for the $1,500 IC Project deliverable.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

PACKAGE_SCHEMA = "regguard.ic_package.v3"
PACKAGE_VERSION = 3


def _s(v: Any, limit: int = 2000) -> str:
    t = str(v or "").strip()
    return t[:limit]


def _url_host(url: str) -> str:
    try:
        from urllib.parse import urlparse

        return (urlparse(url).netloc or "").lower().removeprefix("www.")
    except Exception:
        return ""


def _ahj_trusted_hosts(analysis: Dict[str, Any]) -> set:
    """Hosts that may cite AHJ fee / portal / apply claims."""
    hosts: set = set()
    ahj = analysis.get("ahj_card") if isinstance(analysis.get("ahj_card"), dict) else {}
    ahj_block = analysis.get("ahj") if isinstance(analysis.get("ahj"), dict) else {}
    for u in list(ahj_block.get("ahj_citation_urls") or []) + [
        ahj.get("portal_url") or "",
        ahj.get("fees_url") or "",
        ahj.get("apply_url") or "",
        ahj.get("inspections_url") or "",
        ahj_block.get("ahj_portal_url") or "",
        ahj_block.get("ahj_design_criteria_url") or "",
        ((analysis.get("paid_local") or {}).get("portal_url") or ""),
    ]:
        h = _url_host(str(u))
        if h:
            hosts.add(h)
    ultra = analysis.get("ultralocal_scout") if isinstance(analysis.get("ultralocal_scout"), dict) else {}
    for pg in ultra.get("confirmed_pages") or []:
        if not isinstance(pg, dict):
            continue
        h = _url_host(str(pg.get("url") or pg.get("source_url") or ""))
        if h:
            hosts.add(h)
    # Always trust Accela-style apply hosts when present on apply_url
    apply_h = _url_host(str(ahj.get("apply_url") or ""))
    if apply_h:
        hosts.add(apply_h)
    return hosts


def _claim_url_allowed(url: str, label: str, ahj_hosts: set) -> bool:
    """
    Drop scout round-robin pollution (e.g. whitehouse.gov on a stormwater fee).
    AHJ hosts always OK; otherwise require topic ↔ host fit.
    Topic keywords are matched on the claim label only — never on the URL itself
    (otherwise a polluted Fast-41 press URL self-authorizes).
    """
    u = _s(url, 400)
    if not u.startswith("http"):
        return False
    host = _url_host(u)
    if not host:
        return False
    if any(host == h or host.endswith("." + h) for h in ahj_hosts):
        return True
    blob = _s(label, 400).lower()
    if any(k in blob for k in ("fast-41", "fast41", "permitting council", "nepa dashboard")):
        return host.endswith("permits.performance.gov") or host.endswith("permitting.gov")
    if any(k in blob for k in ("tdlr", "tabs", "contractor license")):
        return "tdlr.texas.gov" in host or host.endswith("texas.gov")
    if any(
        k in blob
        for k in (
            "flood",
            "fema",
            "wetland",
            "ipac",
            "species",
            "nwi",
            "nepa",
            "tceq",
            "npdes",
            "endangered",
        )
    ):
        return any(
            x in host
            for x in (
                "fema.gov",
                "fws.gov",
                "epa.gov",
                "tceq.texas.gov",
                "usgs.gov",
                "usace.army.mil",
                "ecos.fws.gov",
            )
        )
    if any(k in blob for k in ("ercot", "interconnect", "large-load", "large load", "tdsp", "utility power")):
        return any(x in host for x in ("ercot.com", "puc.texas.gov"))
    if any(
        k in blob
        for k in (
            "fee",
            "stormwater",
            "plan review",
            "intake",
            "building permit",
            "trade permit",
            "drainage study",
            "budget ",
        )
    ):
        # Fee dollars must come from AHJ / Accela — already checked above
        return False
    # Generic punch: allow civic hosts only (never news / whitehouse / random .com)
    if host.endswith(".gov") or host.endswith(".mil") or host.endswith(".us"):
        # Still block executive / press hosts commonly polluted onto fee rows
        if any(
            x in host
            for x in (
                "whitehouse.gov",
                "state.gov",
                "commerce.gov",
            )
        ):
            return False
        # Block press/newsroom paths even on otherwise-gov hosts
        path = u.lower()
        if "/newsroom/" in path or "/press-releases/" in path or "/releases/" in path:
            return False
        return True
    return False


def _sanitize_url(url: str, label: str, ahj_hosts: set) -> str:
    u = _s(url, 400)
    return u if _claim_url_allowed(u, label, ahj_hosts) else ""


def _resolve_fee_schedule_url(analysis: Dict[str, Any], ahj: Dict[str, Any]) -> str:
    """Prefer live fee-schedule PDF over generic department landing page."""
    current = _s(ahj.get("fees_url"), 400)
    portal = _s(ahj.get("portal_url"), 400)
    ultra = analysis.get("ultralocal_scout") if isinstance(analysis.get("ultralocal_scout"), dict) else {}
    for pg in ultra.get("confirmed_pages") or []:
        if not isinstance(pg, dict):
            continue
        title = _s(pg.get("title") or pg.get("label"), 200).lower()
        url = _s(pg.get("url") or pg.get("source_url"), 400)
        if "fee" in title and url.startswith("http") and (
            url.lower().endswith(".pdf") or "fee" in url.lower()
        ):
            return url
    # Catalog / ahj fee table PDF citations
    ahj_block = analysis.get("ahj") if isinstance(analysis.get("ahj"), dict) else {}
    for row in ahj_block.get("ahj_fee_table") or ahj_block.get("ahj_fee_lines") or []:
        if not isinstance(row, dict):
            continue
        url = _s(row.get("citation_url") or row.get("source_url"), 400)
        if url.lower().endswith(".pdf") and "fee" in url.lower():
            return url
        if url.lower().endswith(".pdf") and "schedule" in url.lower():
            return url
    if current and current != portal:
        return current
    return current or portal


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
    ahj_hosts = _ahj_trusted_hosts(analysis)
    out: List[Dict[str, str]] = []
    for k in analysis.get("margin_killers") or []:
        if not isinstance(k, dict):
            continue
        title = _s(k.get("title"), 160)
        src = _sanitize_url(_s(k.get("source_url"), 400), title, ahj_hosts)
        out.append(
            {
                "priority": _s(k.get("priority") or "NOTE", 20).upper(),
                "title": title,
                "detail": _s(k.get("detail"), 400),
                "source_url": src,
                "source_label": _s(
                    k.get("source_label") or ("Source" if src else "Unverified"),
                    80,
                ),
            }
        )
        if len(out) >= n:
            break
    return out


def _gotchas(analysis: Dict[str, Any], n: int = 6) -> List[Dict[str, str]]:
    ahj_hosts = _ahj_trusted_hosts(analysis)
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
        title = _s(g.get("title"), 160)
        src = _sanitize_url(_s(g.get("source_url"), 400), title, ahj_hosts)
        out.append(
            {
                "priority": _s(g.get("priority") or "WATCH", 20).upper(),
                "title": title,
                "detail": _s(g.get("detail"), 400),
                "confirm_step": _s(
                    g.get("confirm_step")
                    or g.get("action")
                    or "Confirm with AHJ / ordinance text before bid.",
                    240,
                ),
                "source_url": src,
                "source_label": _s(
                    g.get("source_label") or ("Source" if src else "Unverified"),
                    80,
                ),
            }
        )
    return out


def _punch(analysis: Dict[str, Any], n: int = 20) -> List[Dict[str, Any]]:
    ahj_hosts = _ahj_trusted_hosts(analysis)
    punch = analysis.get("punch_list") if isinstance(analysis.get("punch_list"), dict) else {}
    raw = punch.get("punch_list") or punch.get("items") or []
    out: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        task = _s(item.get("task") or item.get("action"), 280)
        if not task:
            continue
        url = _sanitize_url(
            _s(item.get("source_url") or item.get("citation_url"), 400),
            task,
            ahj_hosts,
        )
        out.append(
            {
                "priority": _s(item.get("priority") or "MEDIUM", 20).upper(),
                "task": task,
                "timeline": _s(item.get("timeline") or "Pre-bid", 40),
                "owner": _s(
                    item.get("owner") or item.get("responsible_party") or "Estimator / PM",
                    60,
                ),
                "trade": _s(item.get("trade"), 40),
                "estimated_cost": item.get("estimated_cost"),
                "source_url": url,
                "citation": _s(
                    item.get("citation_label")
                    or ("Source" if url else "Unverified — confirm with AHJ"),
                    80,
                ),
                "verified": bool(url and item.get("verified")),
            }
        )
        if len(out) >= n:
            break
    return out


def _fees(analysis: Dict[str, Any], n: int = 20) -> List[Dict[str, str]]:
    """Prefer citeable AHJ fee table / pack fees; strip polluted scout URLs."""
    ahj_hosts = _ahj_trusted_hosts(analysis)
    candidates: List[Dict[str, Any]] = []

    ahj_block = analysis.get("ahj") if isinstance(analysis.get("ahj"), dict) else {}
    for f in ahj_block.get("ahj_fee_table") or ahj_block.get("ahj_fee_lines") or []:
        if isinstance(f, dict):
            candidates.append(f)

    lp = analysis.get("local_pack") if isinstance(analysis.get("local_pack"), dict) else {}
    for f in lp.get("fees") or []:
        if isinstance(f, dict):
            candidates.append(f)

    fee_card = analysis.get("fee_card") if isinstance(analysis.get("fee_card"), dict) else {}
    for f in fee_card.get("fees") or []:
        if isinstance(f, dict):
            # Skip punch-extracted "Budget …" duplicates — catalog rows win
            name0 = _s(f.get("name") or f.get("label") or f.get("fee"), 120)
            if name0.lower().startswith("budget "):
                continue
            candidates.append(f)

    out: List[Dict[str, str]] = []
    seen: set = set()
    for f in candidates:
        name = _s(f.get("name") or f.get("label") or f.get("fee"), 120)
        if not name:
            continue
        key = name.lower()
        # Collapse "Budget X: $N" against catalog "X"
        key_norm = key
        if key_norm.startswith("budget "):
            key_norm = key_norm[7:].split(":")[0].strip()
        if key in seen or key_norm in seen:
            continue
        amt = f.get("amount_usd")
        if isinstance(amt, (int, float)):
            amount = f"${amt:,.0f}"
        elif f.get("amount_requires_schedule"):
            amount = "confirm on schedule"
        else:
            amount = _s(f.get("amount") or f.get("value") or f.get("range"), 80)
        src = _sanitize_url(
            _s(f.get("source_url") or f.get("citation_url"), 400),
            name,
            ahj_hosts,
        )
        if not src and not amount:
            continue
        # Do not keep fee rows whose only URL was pollution (cleared) when we already
        # have a citeable catalog fee with the same dollars
        if not src and name.lower().startswith("budget "):
            continue
        seen.add(key)
        seen.add(key_norm)
        out.append(
            {
                "name": name,
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
    ahj_hosts = _ahj_trusted_hosts(analysis)

    def add(url: Any, label: str = "") -> None:
        u = _s(url, 400)
        if not u or not u.startswith("http") or u in seen:
            return
        if not _claim_url_allowed(u, label or "Source", ahj_hosts):
            return
        seen.add(u)
        host = u.replace("https://", "").replace("http://", "")
        out.append({"url": u, "label": _s(label or host, 120)})

    for u in analysis.get("pro_source_urls") or []:
        add(u, "Scout source")
    ahj = analysis.get("ahj_card") if isinstance(analysis.get("ahj_card"), dict) else {}
    # Prefer resolved fee-schedule PDF when available
    fees_url = _resolve_fee_schedule_url(analysis, dict(ahj))
    add(ahj.get("portal_url"), _s(ahj.get("name") or "AHJ portal", 80))
    add(fees_url or ahj.get("fees_url"), "AHJ fees")
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
                "url": _s(c.get("url") or c.get("source_url"), 400),
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
            rows.append({"name": name, "detail": detail, "owner": owner, "track": track, "url": ""})

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
    return rows[:12]


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
        _claim(
            claim_type="parallel_clock",
            label=_s(c.get("name"), 80),
            detail=_s(c.get("detail"), 240),
            url=_s(c.get("url") or c.get("source_url"), 400),
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


def _compose_power_path(data: Dict[str, Any]) -> Dict[str, Any]:
    raw = data.get("power_path") if isinstance(data.get("power_path"), dict) else {}
    if not raw:
        raw = data.get("power_path_card") if isinstance(data.get("power_path_card"), dict) else {}
    if not raw:
        return {}
    checklist = [
        _s(x, 200) for x in (raw.get("checklist") or []) if _s(x, 200)
    ][:8]
    band = raw.get("surcharge_band") if isinstance(raw.get("surcharge_band"), dict) else {}
    notes_bits: List[str] = []
    base_notes = _s(raw.get("notes") or raw.get("detail") or raw.get("disclaimer"), 600)
    if base_notes:
        notes_bits.append(base_notes)
    if band.get("estimated_low_usd") is not None and band.get("estimated_high_usd") is not None:
        try:
            lo = int(float(band.get("estimated_low_usd")))
            hi = int(float(band.get("estimated_high_usd")))
            notes_bits.append(
                f"Illustrative reinforcement band ~${lo:,}–${hi:,} "
                "(planning proxy only — confirm with utility study / LGIA)."
            )
        except (TypeError, ValueError):
            pass
    if raw.get("federal_note"):
        notes_bits.append(_s(raw.get("federal_note"), 300))
    if checklist:
        notes_bits.append("Checklist: " + "; ".join(checklist[:4]))
    return {
        "headline": _s(raw.get("headline") or raw.get("title"), 240),
        "status": _s(raw.get("status") or ("FAST-41 candidate" if raw.get("fast41_candidate") else ""), 80),
        "notes": _s(" | ".join(notes_bits), 900),
        "source_url": _s(raw.get("source_url"), 400),
        "checklist": checklist,
        "disclaimer": _s(
            raw.get("disclaimer")
            or "NOT an interconnection study — screening / readiness only.",
            400,
        ),
        "mw_hint": raw.get("mw_hint"),
        "surcharge_band": band or None,
    }


def _compose_moratorium(data: Dict[str, Any], pi: Dict[str, Any]) -> Dict[str, Any]:
    raw = data.get("moratorium_radar") if isinstance(data.get("moratorium_radar"), dict) else {}
    if not raw:
        return {}
    city = _s(pi.get("city"), 40).lower()
    state = _s(pi.get("state"), 8).upper()
    metros_out: List[Dict[str, str]] = []
    best_url = _s(raw.get("source_url") or raw.get("citation_url"), 400)
    best_detail = _s(raw.get("detail") or raw.get("summary"), 600)
    for m in raw.get("metros") or []:
        if not isinstance(m, dict):
            continue
        name = _s(m.get("name") or m.get("metro"), 80)
        url = _s(m.get("citation_url") or m.get("source_url") or m.get("url"), 400)
        status = _s(m.get("status") or m.get("note") or m.get("tags"), 200)
        metros_out.append({"name": name, "status": status, "citation_url": url})
        # Prefer metro near site city / DFW for Fort Worth
        name_l = name.lower()
        if city and city in name_l:
            if url:
                best_url = url
            if status:
                best_detail = f"{name}: {status}"
        elif state == "TX" and ("dfw" in name_l or "north texas" in name_l or "fort worth" in name_l):
            if url and not best_url:
                best_url = url
            if status and (not best_detail or "austin" in (best_detail or "").lower()):
                best_detail = f"{name}: {status}"
    return {
        "status": _s(raw.get("status") or ("HIGH" if raw.get("high_alert_state") else ""), 80),
        "headline": _s(raw.get("headline"), 240),
        "detail": best_detail or _s(raw.get("detail") or raw.get("summary"), 600),
        "source_url": best_url,
        "metros": metros_out[:6],
        "disclaimer": _s(raw.get("disclaimer"), 300),
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
    ahj = dict(ahj)
    fee_pdf = _resolve_fee_schedule_url(data, ahj)
    if fee_pdf:
        ahj["fees_url"] = fee_pdf
    coverage = data.get("coverage") if isinstance(data.get("coverage"), dict) else {}
    env = data.get("environmental_screening") if isinstance(data.get("environmental_screening"), dict) else {}
    clocks = data.get("parallel_clocks") if isinstance(data.get("parallel_clocks"), dict) else {}
    share = _s(share_url or data.get("share_url"), 300)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Alias power_path_card → power_path so Bundle surfaces DC planning depth
    if not isinstance(data.get("power_path"), dict) and isinstance(data.get("power_path_card"), dict):
        data["power_path"] = data["power_path_card"]

    killers = _killers(data, 12)
    gotchas = _gotchas(data, 16)
    punch = _punch(data, 80)
    fees = _fees(data, 40)
    sources = _sources(data, 120)
    actions = _next_actions(data, 12)
    contingency = _contingency_block(data)
    clock_rows = _parallel_clock_rows(data, pi, killers)
    inspection_steps = _inspection_steps(data, 25)
    doc_checklist = _document_checklist(data, 30)
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
            "primary": (
                "IC Diligence Bundle ZIP — decision memo + boardroom PDF + counsel DOCX "
                "(evidence binder + parallel clocks) + fee/punch CSV + evidence index"
            ),
            "working_set": "Decision memo · Boardroom PDF · Counsel DOCX · Fee/punch CSV · Evidence index",
            "forward_artifact": "Bid Risk Receipt / decision memo PDF (1-page stamp)",
            "price_positioning": "$1,500 IC Project — counsel-ready Diligence Bundle for one site",
        },
        "cover": {
            "product": f"RegGuard IC Diligence Bundle — {site_line}",
            "price_positioning": (
                "$1,500 IC Project — decision memo + boardroom PDF + counsel DOCX + fee/punch CSV + evidence binder"
            ),
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
            "top_risks": killers,
            "local_gotchas": gotchas,
            "next_actions": actions,
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
            "gotcha_cards": _gotcha_cards(data, 16),
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
                for f in (env.get("findings") or [])[:20]
                if isinstance(f, dict)
            ],
            "parallel_clocks": clock_rows,
            "power_path": _compose_power_path(data),
            "moratorium_radar": _compose_moratorium(data, pi),
            "ultralocal": (
                {
                    "enabled": bool((data.get("ultralocal_scout") or {}).get("enabled")),
                    "depth": _s(data.get("scout_locality_depth"), 40),
                    "summary": _s(
                        (data.get("ultralocal_scout") or {}).get("summary")
                        or (data.get("ultralocal_scout") or {}).get("headline"),
                        600,
                    ),
                    "confirmed_pages": [
                        {
                            "title": _s(pg.get("title") or pg.get("label"), 160),
                            "url": _s(pg.get("url") or pg.get("source_url"), 400),
                        }
                        for pg in (
                            (data.get("ultralocal_scout") or {}).get("confirmed_pages") or []
                        )[:8]
                        if isinstance(pg, dict)
                        and _s(pg.get("url") or pg.get("source_url"), 400).startswith("http")
                    ],
                }
                if isinstance(data.get("ultralocal_scout"), dict)
                else {}
            ),
        },
        "parallel_clocks_track": {
            "enabled": is_dc or len(clock_rows) >= 2,
            "title": "Interconnection consultant parallel clocks",
            "headline": (
                "AHJ permits, utility interconnection / large-load, and water/NPDES run as independent "
                "clocks — schedule risk stacks when any one slips. IC / interconnection consultants "
                "should keep these tracks separate in the LOI narrative."
            ),
            "clocks": clock_rows,
        },
        "punch_list": {
            "timeline_summary": _s(punch_obj.get("timeline_summary"), 80),
            "items": punch,
        },
        "evidence_binder": binder,
        "action_plan_summary": actions,
        "action_plan_excerpt": _s(
            (data.get("pro_summary_markdown") or data.get("executive_summary_markdown") or "")[:8000],
            8000,
        ),
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
