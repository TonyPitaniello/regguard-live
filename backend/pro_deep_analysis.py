"""
Contractor Pro / IC deep research path.

Runs Option A (modal-compatible punch list) plus the Universal Scout + contractor
action-plan path used by /research/static, then merges citeable sources into results.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_PROJECT_TO_VERTICAL = {
    "data-center": "data_center",
    "data_center": "data_center",
    "renewable": "infrastructure",
    "utility": "infrastructure",
    "industrial": "infrastructure",
    "commercial": "building",
    "other": "building",
}


def _http_urls(urls: List[Any]) -> List[str]:
    out: List[str] = []
    for u in urls or []:
        s = str(u or "").strip()
        if s.startswith("http://") or s.startswith("https://"):
            if s not in out:
                out.append(s)
    return out


def _checklist_tasks_from_markdown(summary: str, limit: int = 12) -> List[str]:
    tasks: List[str] = []
    for line in (summary or "").splitlines():
        m = re.match(r"\s*[-*]\s*\[[ xX]?\]\s*(.+)$", line)
        if m:
            task = m.group(1).strip()
            if task and task not in tasks:
                tasks.append(task)
        if len(tasks) >= limit:
            break
    return tasks


def _map_vertical(project_type: str) -> str:
    return _PROJECT_TO_VERTICAL.get((project_type or "").strip().lower(), "building")


def _run_research_static_sync(
    *,
    address: str,
    city: str,
    state: str,
    zip_code: str,
    project_type: str,
    scout_mode: str = "full",
) -> Dict[str, Any]:
    """Run non-streaming research pipeline (scout + action plan)."""
    # Lazy import avoids circular import at app startup
    from main import (
        _iter_research_sse_events,
        _parse_research_form,
        _research_static_collect,
    )

    site_line = f"{address}, {city}, {state} {zip_code}".strip()
    vertical = _map_vertical(project_type)
    light = (scout_mode or "").strip().lower() == "light"
    # Light Pro scout: keep vertical for memo context but force light_scout flag (3 passes only)
    jd = (
        f"{project_type} permitting and pre-bid diligence for {site_line}. "
        f"Focus on local AHJ fees, codes, inspections, and citeable punch-list actions."
    )
    trades = "electrician,general_contractor,zoning_planning"
    lim, jd_parsed, scout_profile_payload, jf_gate = _parse_research_form(
        zip_code=zip_code or "",
        client_city=city or "",
        job_description=jd,
        search_limit=5 if light else 8,
        site_address=site_line,
        bim_bridge_json="",
        scout_trades=trades,
        mission_critical_dc="true" if (vertical == "data_center" and not light) else "false",
        scout_vertical=vertical if not light else "building",
        site_line=site_line,
    )
    scout_profile_payload = dict(scout_profile_payload or {})
    scout_profile_payload["light_scout"] = light
    if light:
        scout_profile_payload["job_fast41_eligible"] = False
        scout_profile_payload["mission_critical_dc"] = False
    ctx: Dict[str, Any] = {
        "lim": lim,
        "jd": jd_parsed,
        "site_line": site_line,
        "zip_code": zip_code or "",
        "client_city": city or "",
        "bim_bridge_json": "",
        "bim_clash_report": None,
        "scout_profile_payload": scout_profile_payload,
        "image_bytes": None,
        "image_meta": (None, None),
        "has_image": False,
        "jf_gate": jf_gate,
        "scout_vertical": scout_profile_payload.get("vertical") or vertical,
    }
    out = _research_static_collect(_iter_research_sse_events(ctx))
    if isinstance(out, dict):
        out["scout_mode"] = "light" if light else "full"
    return out


def _drop_foreign_city_urls(summary: str, city: str) -> str:
    """A scout writeup can still name another city's permit page after the link list is filtered."""
    import re

    if not summary or not city:
        return summary
    from ic_ultralocal_scout import _foreign_municipal_page, _mentions_site_city

    def _keep(match: re.Match) -> str:
        url = match.group(0)
        if _mentions_site_city(url, city):
            return url
        if _foreign_municipal_page("", "", url, city):
            return ""
        return url

    cleaned = re.sub(r"https?://[^\s)>\]]+", _keep, summary)
    lines = [line for line in cleaned.splitlines() if not re.match(r"^\s*[-*]\s*$", line)]
    return "\n".join(lines)


def _prepend_pack_gotchas(
    analysis: Dict[str, Any],
    items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """City-pack rules stay on the paid punch. Generic scout lines do not bury them."""
    from city_packs import resolve_city_pack

    pi = analysis.get("project_info") if isinstance(analysis.get("project_info"), dict) else {}
    pack = resolve_city_pack(
        str(pi.get("city") or ""),
        str(pi.get("state") or ""),
        str(pi.get("zip") or ""),
    )
    if not pack:
        return items
    existing = {
        str(i.get("task") or "").strip().lower()
        for i in items
        if isinstance(i, dict)
    }
    front: List[Dict[str, Any]] = []
    ahj = pack.get("ahj") if isinstance(pack.get("ahj"), dict) else {}
    confirm_url = str(ahj.get("fees_url") or ahj.get("portal_url") or "").strip()
    confirm_task = f"Confirm fees & intake with {ahj.get('name') or 'the city building department'}"
    if confirm_url and confirm_task.strip().lower() not in existing:
        front.append(
            {
                "priority": "CRITICAL",
                "task": confirm_task,
                "responsible_party": "Estimator / permit runner",
                "timeline": "Before bid",
                "estimated_cost": None,
                "notes": "Paid desk keeps the city intake line. Fee dollars print only when the schedule states them.",
                "verified": True,
                "cost_verified": False,
                "source_url": confirm_url,
                "source_label": ahj.get("name") or "City pack",
                "priority_locked": True,
            }
        )
    for g in list(pack.get("gotchas") or [])[:4]:
        if not isinstance(g, dict) or not (g.get("source_url") or "").strip():
            continue
        task = str(g.get("title") or "Local gotcha")
        if task.strip().lower() in existing:
            continue
        front.append(
            {
                "priority": str(g.get("priority") or "HIGH").upper(),
                "task": task,
                "responsible_party": "Field / estimator",
                "timeline": "Before bid",
                "estimated_cost": None,
                "notes": str(g.get("detail") or ""),
                "verified": True,
                "cost_verified": False,
                "source_url": g.get("source_url"),
                "source_label": g.get("source_label") or "City pack",
                "priority_locked": True,
            }
        )
    return front + items


def _merge_deep_into_analysis(
    base: Dict[str, Any],
    research_payload: Dict[str, Any],
) -> Dict[str, Any]:
    summary = (
        research_payload.get("summary")
        or research_payload.get("action_plan")
        or ""
    )
    if not isinstance(summary, str):
        summary = str(summary or "")

    source_urls = _http_urls(
        list(research_payload.get("source_urls") or [])
        + list(research_payload.get("unique_source_urls") or [])
    )
    pi_city = str((base.get("project_info") or {}).get("city") or "")
    if pi_city and source_urls:
        from ic_ultralocal_scout import _foreign_municipal_page

        source_urls = [
            u
            for u in source_urls
            if not _foreign_municipal_page("", "", u, pi_city)
        ]
    # complete envelope sometimes nests fields
    if not source_urls and isinstance(research_payload.get("complete"), dict):
        source_urls = _http_urls(research_payload["complete"].get("source_urls") or [])
        summary = summary or research_payload["complete"].get("summary") or ""

    analysis = dict(base)
    analysis["research_depth"] = "pro"
    analysis["preview"] = False
    analysis["pro_summary_markdown"] = _drop_foreign_city_urls(summary[:12000], pi_city) if summary else ""
    analysis["pro_source_urls"] = source_urls

    punch = dict(analysis.get("punch_list") or {})
    items = list(punch.get("punch_list") or [])
    md_tasks = _checklist_tasks_from_markdown(summary, limit=10)

    # Attach scout URLs as related links — never auto-verify (kills SOURCE theater).
    # verified=True only when URL host matches AHJ portal / fee citation hosts.
    from urllib.parse import urlparse

    def _host(u: str) -> str:
        try:
            return (urlparse(u).netloc or "").lower().removeprefix("www.")
        except Exception:
            return ""

    ahj_hosts: set = set()
    ahj_block = analysis.get("ahj") if isinstance(analysis.get("ahj"), dict) else {}
    for u in list(ahj_block.get("ahj_citation_urls") or []) + [
        ahj_block.get("ahj_portal_url") or "",
        ((analysis.get("ahj_card") or {}).get("portal_url") or ""),
        ((analysis.get("paid_local") or {}).get("portal_url") or ""),
    ]:
        h = _host(str(u))
        if h:
            ahj_hosts.add(h)

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        if source_urls and not item.get("verified") and not item.get("source_url"):
            task = str(item.get("task") or item.get("action") or "")
            # Topic-match scout URLs — never round-robin unrelated hosts onto punch rows
            chosen = ""
            for url in source_urls:
                host = _host(url)
                if host and host in ahj_hosts:
                    chosen = url
                    break
            if not chosen:
                # Keyword overlap between task and URL path/host
                task_l = task.lower()
                for url in source_urls:
                    ul = url.lower()
                    if any(
                        k in task_l and k in ul
                        for k in (
                            "fee",
                            "permit",
                            "flood",
                            "fema",
                            "ercot",
                            "tdlr",
                            "fast-41",
                            "wetland",
                            "npdes",
                        )
                    ):
                        chosen = url
                        break
            if not chosen:
                continue
            item = dict(item)
            item["source_url"] = chosen
            host = _host(chosen)
            bound = bool(host and host in ahj_hosts)
            item["verified"] = bound
            item["source_label"] = "AHJ source" if bound else "Topic-matched scout link"
            items[i] = item

    # Prepend deep checklist tasks not already present
    existing_tasks = {(i.get("task") or "").strip().lower() for i in items if isinstance(i, dict)}
    for task in md_tasks:
        if task.lower() in existing_tasks:
            continue
        # Prefer AHJ-bound URL for new tasks; else leave blank (Unverified)
        url = None
        for candidate in source_urls:
            host = _host(candidate)
            if host and host in ahj_hosts:
                url = candidate
                break
        host = _host(url or "")
        bound = bool(url and host and host in ahj_hosts)
        items.insert(
            0,
            {
                "priority": "HIGH",
                "task": task,
                "responsible_party": "Contractor / AHJ",
                "timeline": "Pre-bid",
                "estimated_cost": None,
                "notes": "From Contractor Pro deep research",
                "source_url": url,
                "source_label": "Deep research action plan" if url else None,
                "verified": bound,
                "cost_verified": False,
            },
        )
        existing_tasks.add(task.lower())

    from punch_rank import normalize_punch_items, rebuild_critical_path

    items = _prepend_pack_gotchas(analysis, items)
    pi = analysis.get("project_info") or {}
    ptype = str(pi.get("type") or "").lower().replace(" ", "_").replace("-", "_")
    is_dc = any(x in ptype for x in ("data_center", "datacenter", "dc", "colo"))
    items = normalize_punch_items(items, is_dc=is_dc)
    critical = rebuild_critical_path(items)

    punch["punch_list"] = items
    if critical:
        punch["critical_path"] = critical
    punch["ranked"] = True
    analysis["punch_list"] = punch

    summary_block = dict(analysis.get("summary") or {})
    summary_block["total_punch_list_items"] = len(items)
    summary_block["research_depth"] = "pro"
    analysis["summary"] = summary_block

    next_steps = list(analysis.get("next_steps") or [])
    # Drop stale free→Pro upgrade pitches for paid/deep runs
    next_steps = [
        s
        for s in next_steps
        if "upgrade to contractor pro" not in str(s).lower()
    ]
    if analysis.get("research_depth") == "ic" or analysis.get("depth_tier") == "ic_full":
        next_steps.insert(
            0,
            "IC Diligence Bundle ready — download the counsel ZIP from My Orders.",
        )
    else:
        next_steps.insert(
            0,
            "Contractor Pro deep research complete — review ranked punch list + sources first.",
        )
    analysis["next_steps"] = next_steps[:8]
    return analysis


def scout_mode_for_paid_run(
    *,
    force_scout: bool,
    local_status: str,
    universal_on: bool,
    light_on: bool,
) -> str:
    """
    IC Diligence Bundle (force_scout) always gets full Universal Scout.
    The Pro daily cap does not apply to that run. Pro stays light unless
    the legacy universal flag is on.
    """
    if force_scout:
        return "full"
    if (local_status or "") == "capped":
        return "none"
    if universal_on:
        return "full"
    if light_on:
        return "light"
    return "none"


async def run_pro_deep_analysis(
    *,
    address: str,
    city: str,
    state: str,
    zip_code: str,
    latitude: float,
    longitude: float,
    project_type: str = "commercial",
    email: str = "",
    force_scout: bool = False,
) -> Dict[str, Any]:
    """
    Deep path for paid users:
      1) Option A structure
      2) Paid local confirm FinOps (bounded scrape + day/page caps + cache) — always first
      3) Scout:
         - force_scout (IC) → full Universal Scout
         - else Pro → light scout (3 core passes) when PAID_PRO_LIGHT_SCOUT=1 (default)
         - PAID_UNIVERSAL_SCOUT=1 → full for all paid (legacy)
         - day-capped → local only
    """
    from option_a_integration import run_option_a_analysis
    from paid_local_confirm import (
        paid_universal_scout_enabled,
        run_paid_local_confirm,
        _env_on,
    )
    from depth_ladder import (
        DEPTH_IC_FULL,
        DEPTH_PRO_LIGHT,
        DEPTH_PRO_LOCAL,
        DEPTH_PRO_PARTIAL,
        stamp_pro_delta,
        stamp_upgrade_offer,
    )

    base = await asyncio.wait_for(
        run_option_a_analysis(
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            latitude=latitude,
            longitude=longitude,
            project_type=project_type,
        ),
        timeout=45.0,
    )

    # Paid local confirm FinOps first (bounded, cached, day-capped) — return-ready (F8)
    # IC (force_scout): never skip local deepen due to Pro daily cap — buyer paid $1.5k.
    try:
        loop = asyncio.get_event_loop()
        base = await loop.run_in_executor(
            None,
            lambda: run_paid_local_confirm(
                dict(base),
                city=city,
                state=state,
                zip_code=zip_code,
                email=email,
                skip_quota=bool(force_scout),
            ),
        )
    except Exception as sc_err:
        logger.warning("Paid local confirm failed: %s", sc_err)
        base = dict(base)
        base["finops_mode"] = "paid_local_confirm"
        base["paid_local"] = {"status": "error", "error": str(sc_err)}

    pl = base.get("paid_local") or {}
    scout_mode = scout_mode_for_paid_run(
        force_scout=bool(force_scout),
        local_status=str(pl.get("status") or ""),
        universal_on=bool(paid_universal_scout_enabled()),
        light_on=bool(_env_on("PAID_PRO_LIGHT_SCOUT", "1")),
    )
    if scout_mode == "none" and str(pl.get("status") or "") == "capped":
        logger.info("Skipping scout — paid local daily cap reached")
    elif scout_mode == "full" and force_scout:
        logger.info("IC Diligence Bundle — full Universal Scout (Pro daily cap does not apply)")

    if scout_mode == "none":
        out = dict(base)
        out["research_depth"] = out.get("research_depth") or "pro"
        out["preview"] = False
        out["finops_mode"] = "paid_local_confirm"
        out["scout_mode"] = "none"
        if not out.get("pro_summary_markdown"):
            out["pro_summary_markdown"] = (
                "## Paid local confirm\n\n"
                "Bounded AHJ scrape completed (page-capped, cached). "
                "Fee extracts are **planning aids** — confirm on the official schedule. "
                "Light / full Universal Scout was off or day-capped for this run.\n"
            )
        stamp_upgrade_offer(out, depth_tier=DEPTH_PRO_LOCAL)
        stamp_pro_delta(out)
        logger.info(
            "Pro path local-confirm only: finops=%s paid_local=%s",
            out.get("finops_mode"),
            pl.get("status"),
        )
        return out

    try:
        loop = asyncio.get_event_loop()
        timeout = 150.0 if (scout_mode == "full" and force_scout) else (110.0 if scout_mode == "full" else 70.0)
        research_payload = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: _run_research_static_sync(
                    address=address,
                    city=city,
                    state=state,
                    zip_code=zip_code,
                    project_type=project_type,
                    scout_mode=scout_mode,
                ),
            ),
            timeout=timeout,
        )
        if not isinstance(research_payload, dict):
            research_payload = {}
        merged = _merge_deep_into_analysis(base, research_payload)
        merged["finops_mode"] = "paid_local_confirm"
        merged["scout_mode"] = scout_mode
        if base.get("paid_local"):
            merged["paid_local"] = base.get("paid_local")
        if base.get("paid_local_quota"):
            merged["paid_local_quota"] = base.get("paid_local_quota")
        if base.get("coverage"):
            merged["coverage"] = base["coverage"]
        if base.get("fee_card") and (base.get("fee_card") or {}).get("fees"):
            fc = dict(merged.get("fee_card") or {})
            existing = list(fc.get("fees") or [])
            seen = {str(r.get("label") or "")[:40] for r in existing}
            for row in list((base.get("fee_card") or {}).get("fees") or []):
                key = str(row.get("label") or "")[:40]
                if key not in seen:
                    existing.insert(0, row)
                    seen.add(key)
            fc["fees"] = existing[:12]
            fc["paid_local_confirm"] = True
            fc["planning_aid"] = True
            fc["disclaimer"] = (
                "Planning aid only — not an AHJ quote. Confirm on the official fee schedule before bid."
            )
            merged["fee_card"] = fc
        if scout_mode == "full" and force_scout:
            stamp_upgrade_offer(merged, depth_tier=DEPTH_IC_FULL)
            merged["preview"] = False
            # IC local + ultralocal deepen (HOA/MUD/township + AHJ/fees SERP)
            try:
                from ic_ultralocal_scout import run_ic_local_ultralocal_scout

                merged = run_ic_local_ultralocal_scout(
                    merged,
                    address=address,
                    city=city,
                    state=state,
                    zip_code=zip_code,
                )
            except Exception as ultra_err:
                logger.warning("IC ultralocal scout failed (non-blocking): %s", ultra_err)
            next_steps = [
                s
                for s in list(merged.get("next_steps") or [])
                if "upgrade to contractor pro" not in str(s).lower()
                and "pro light scout" not in str(s).lower()
            ]
            next_steps.insert(
                0,
                "IC scout complete — download the Diligence Bundle ZIP from My Orders.",
            )
            merged["next_steps"] = next_steps[:8]
        else:
            stamp_upgrade_offer(merged, depth_tier=DEPTH_PRO_LIGHT)
        stamp_pro_delta(merged)
        # Clarify notes for light vs full
        if scout_mode == "light":
            next_steps = list(merged.get("next_steps") or [])
            next_steps.insert(
                0,
                "Pro light scout complete (AHJ / permits / codes). IC adds full federal/vertical passes + PDFs.",
            )
            merged["next_steps"] = next_steps[:8]
        try:
            from vertical_playbooks import apply_vertical_playbook

            merged = apply_vertical_playbook(merged)
        except Exception:
            pass
        logger.info(
            "Pro deep research merged: sources=%s punch=%s scout_mode=%s local=%s",
            len(merged.get("pro_source_urls") or []),
            len((merged.get("punch_list") or {}).get("punch_list") or []),
            scout_mode,
            (merged.get("paid_local") or {}).get("status"),
        )
        return merged
    except Exception as e:
        logger.warning("Pro deep research scout failed — returning local confirm: %s", e)
        base = dict(base)
        base["research_depth"] = "pro_partial"
        base["preview"] = False
        base["finops_mode"] = "paid_local_confirm"
        base["scout_mode"] = "full_incomplete" if force_scout else scout_mode
        base["pro_summary_markdown"] = base.get("pro_summary_markdown") or ""
        base["pro_source_urls"] = list(base.get("pro_source_urls") or [])
        base["pro_deep_error"] = str(e)[:240]
        if force_scout:
            try:
                from ic_ultralocal_scout import run_ic_local_ultralocal_scout

                base = run_ic_local_ultralocal_scout(
                    base,
                    address=address,
                    city=city,
                    state=state,
                    zip_code=zip_code,
                )
            except Exception as ultra_err:
                logger.warning("IC ultralocal scout failed after full scout error: %s", ultra_err)
        stamp_upgrade_offer(base, depth_tier=DEPTH_PRO_PARTIAL)
        stamp_pro_delta(base)
        return base
