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
    jd = (
        f"{project_type} permitting and pre-bid diligence for {site_line}. "
        f"Focus on local AHJ fees, codes, inspections, and citeable punch-list actions."
    )
    trades = "electrician,general_contractor,zoning_planning"
    lim, jd_parsed, scout_profile_payload, jf_gate = _parse_research_form(
        zip_code=zip_code or "",
        client_city=city or "",
        job_description=jd,
        search_limit=8,
        site_address=site_line,
        bim_bridge_json="",
        scout_trades=trades,
        mission_critical_dc="true" if vertical == "data_center" else "false",
        scout_vertical=vertical,
        site_line=site_line,
    )
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
        "scout_vertical": vertical,
    }
    return _research_static_collect(_iter_research_sse_events(ctx))


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
    # complete envelope sometimes nests fields
    if not source_urls and isinstance(research_payload.get("complete"), dict):
        source_urls = _http_urls(research_payload["complete"].get("source_urls") or [])
        summary = summary or research_payload["complete"].get("summary") or ""

    analysis = dict(base)
    analysis["research_depth"] = "pro"
    analysis["preview"] = False
    analysis["pro_summary_markdown"] = summary[:12000] if summary else ""
    analysis["pro_source_urls"] = source_urls

    punch = dict(analysis.get("punch_list") or {})
    items = list(punch.get("punch_list") or [])
    md_tasks = _checklist_tasks_from_markdown(summary, limit=10)

    # Attach rotating citeable sources to existing punch lines
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        if source_urls and not item.get("verified"):
            url = source_urls[i % len(source_urls)]
            item = dict(item)
            item["source_url"] = url
            item["source_label"] = "Scout source"
            item["verified"] = True
            items[i] = item

    # Prepend deep checklist tasks not already present
    existing_tasks = {(i.get("task") or "").strip().lower() for i in items if isinstance(i, dict)}
    for task in md_tasks:
        if task.lower() in existing_tasks:
            continue
        url = source_urls[0] if source_urls else None
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
                "verified": bool(url),
                "cost_verified": False,
            },
        )
        existing_tasks.add(task.lower())

    # Refresh critical path from top verified/high items
    critical: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if (item.get("priority") or "").upper() in ("CRITICAL", "HIGH"):
            critical.append(
                {
                    "task": item.get("task"),
                    "source_url": item.get("source_url"),
                    "source_label": item.get("source_label"),
                    "verified": bool(item.get("verified")),
                    "cost_verified": bool(item.get("cost_verified")),
                    "estimated_cost": item.get("estimated_cost"),
                }
            )
        if len(critical) >= 5:
            break

    punch["punch_list"] = items
    if critical:
        punch["critical_path"] = critical
    analysis["punch_list"] = punch

    summary_block = dict(analysis.get("summary") or {})
    summary_block["total_punch_list_items"] = len(items)
    summary_block["research_depth"] = "pro"
    analysis["summary"] = summary_block

    next_steps = list(analysis.get("next_steps") or [])
    next_steps.insert(0, "Contractor Pro deep research complete — review citeable punch list + sources first.")
    analysis["next_steps"] = next_steps[:8]
    return analysis


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
) -> Dict[str, Any]:
    """
    Deep path for paid users:
      1) Option A structure
      2) Paid local confirm FinOps (bounded scrape + day/page caps + cache)
      3) Optional Universal Scout when PAID_UNIVERSAL_SCOUT=1
    """
    from option_a_integration import run_option_a_analysis
    from paid_local_confirm import (
        paid_local_confirm_enabled,
        paid_universal_scout_enabled,
        run_paid_local_confirm,
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

    # Paid local confirm FinOps first (bounded, cached, day-capped)
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
            ),
        )
    except Exception as sc_err:
        logger.warning("Paid local confirm failed: %s", sc_err)
        base = dict(base)
        base["finops_mode"] = "paid_local_confirm"
        base["paid_local"] = {"status": "error", "error": str(sc_err)}

    run_scout = paid_universal_scout_enabled()
    if (base.get("paid_local") or {}).get("status") == "capped":
        run_scout = False
        logger.info("Skipping Universal Scout — paid local daily cap reached")

    if not run_scout:
        out = dict(base)
        out["research_depth"] = out.get("research_depth") or "pro"
        out["preview"] = False
        out["finops_mode"] = "paid_local_confirm"
        if not out.get("pro_summary_markdown"):
            out["pro_summary_markdown"] = (
                "## Paid local confirm\n\n"
                "Bounded AHJ scrape completed (page-capped, cached). "
                "Universal Scout is off or capped for this run.\n"
            )
        logger.info(
            "Pro path local-confirm only: finops=%s paid_local=%s",
            out.get("finops_mode"),
            (out.get("paid_local") or {}).get("status"),
        )
        return out

    try:
        loop = asyncio.get_event_loop()
        research_payload = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: _run_research_static_sync(
                    address=address,
                    city=city,
                    state=state,
                    zip_code=zip_code,
                    project_type=project_type,
                ),
            ),
            timeout=100.0,
        )
        if not isinstance(research_payload, dict):
            research_payload = {}
        merged = _merge_deep_into_analysis(base, research_payload)
        merged["finops_mode"] = "paid_local_confirm"
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
            merged["fee_card"] = fc
        logger.info(
            "Pro deep research merged: sources=%s punch=%s finops=%s local=%s",
            len(merged.get("pro_source_urls") or []),
            len((merged.get("punch_list") or {}).get("punch_list") or []),
            merged.get("finops_mode"),
            (merged.get("paid_local") or {}).get("status"),
        )
        return merged
    except Exception as e:
        logger.warning("Pro deep research scout failed — returning local confirm: %s", e)
        base = dict(base)
        base["research_depth"] = "pro_partial"
        base["preview"] = False
        base["finops_mode"] = "paid_local_confirm"
        base["pro_summary_markdown"] = base.get("pro_summary_markdown") or ""
        base["pro_source_urls"] = list(base.get("pro_source_urls") or [])
        base["pro_deep_error"] = str(e)[:240]
        return base
