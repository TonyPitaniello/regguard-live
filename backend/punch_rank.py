"""
Rank + clean punch lists for bid-desk desirability.

- Strip markdown bold
- Demote process-hygiene to MEDIUM
- Promote schedule killers (ERCOT / FAST-41 / parallel clocks) for data-center
- Cap CRITICAL ≤ 3 and HIGH ≤ 8
- Sort CRITICAL → HIGH → MEDIUM → LOW
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

_PRIORITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "NOTE": 4}

_HYGIENE_PHRASES = (
    "contact municipal",
    "request complete permit application checklist",
    "request complete permit",
    "file complete permit application",
    "obtain certificate of occupancy",
    "notify public of project",
    "attend public hearing",
    "schedule final inspection",
    "obtain final permit approval",
    "prepare site plans and engineering",
    "conduct geotechnical",
    "obtain surveys",
    "hire wetlands specialist",
    "budget for mitigation",
    "allow 4-6 weeks for permit review",
    "contact army corps",
    "conduct environmental site assessment",
)

_SCHEDULE_KILLER_PHRASES = (
    "ercot",
    "fast-41",
    "fast 41",
    "interconnect",
    "interconnection",
    "parallel",
    "utility / ercot",
    "tdsp",
    "batch zero",
    "verify ahj",
    "coordinate **ahj",
    "coordinate ahj",
)


def strip_md_bold(text: str) -> str:
    t = str(text or "")
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    return t.replace("**", "").strip()


def _pri(item: Dict[str, Any]) -> str:
    return str(item.get("priority") or "MEDIUM").strip().upper() or "MEDIUM"


def _task(item: Dict[str, Any]) -> str:
    return str(item.get("task") or item.get("action") or "").lower()


def _is_hygiene(item: Dict[str, Any]) -> bool:
    t = _task(item)
    return any(p in t for p in _HYGIENE_PHRASES)


def _is_schedule_killer(item: Dict[str, Any]) -> bool:
    t = _task(item)
    return any(p in t for p in _SCHEDULE_KILLER_PHRASES)


def normalize_punch_items(
    items: Sequence[Any],
    *,
    is_dc: bool = False,
    max_critical: int = 3,
    max_high: int = 8,
) -> List[Dict[str, Any]]:
    """Return cleaned, capped, sorted punch dicts."""
    out: List[Dict[str, Any]] = []
    for raw in items or []:
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        if item.get("task"):
            item["task"] = strip_md_bold(str(item["task"]))
        if item.get("action"):
            item["action"] = strip_md_bold(str(item["action"]))
        if item.get("notes"):
            item["notes"] = strip_md_bold(str(item["notes"]))
        pri = _pri(item)
        if pri not in _PRIORITY_RANK:
            pri = "MEDIUM"
        # Demote process hygiene out of CRITICAL/HIGH
        if _is_hygiene(item) and pri in ("CRITICAL", "HIGH"):
            pri = "MEDIUM"
        # Promote real schedule killers for DC / large-load
        if is_dc and _is_schedule_killer(item) and pri in ("MEDIUM", "LOW", "HIGH"):
            # Prefer CRITICAL only for interconnect / FAST-41 / ERCOT / verify AHJ
            t = _task(item)
            if any(
                k in t
                for k in (
                    "ercot",
                    "fast-41",
                    "fast 41",
                    "interconnect",
                    "verify ahj",
                    "coordinate ahj",
                    "coordinate **ahj",
                )
            ):
                pri = "CRITICAL"
            elif pri == "MEDIUM":
                pri = "HIGH"
        item["priority"] = pri
        out.append(item)

    def _count(level: str) -> int:
        return sum(1 for i in out if _pri(i) == level)

    # Cap CRITICAL — demote hygiene first, then trailing CRITICAL
    while _count("CRITICAL") > max_critical:
        demoted = False
        for i in reversed(out):
            if _pri(i) == "CRITICAL" and _is_hygiene(i):
                i["priority"] = "MEDIUM"
                demoted = True
                break
        if demoted:
            continue
        for i in reversed(out):
            if _pri(i) == "CRITICAL" and not _is_schedule_killer(i):
                i["priority"] = "HIGH"
                demoted = True
                break
        if demoted:
            continue
        for i in reversed(out):
            if _pri(i) == "CRITICAL":
                i["priority"] = "HIGH"
                break
        else:
            break

    while _count("HIGH") > max_high:
        demoted = False
        for i in reversed(out):
            if _pri(i) == "HIGH" and (_is_hygiene(i) or not _is_schedule_killer(i)):
                i["priority"] = "MEDIUM"
                demoted = True
                break
        if demoted:
            continue
        for i in reversed(out):
            if _pri(i) == "HIGH":
                i["priority"] = "MEDIUM"
                break
        else:
            break

    out.sort(key=lambda i: (_PRIORITY_RANK.get(_pri(i), 9), _task(i)[:40]))
    return out


def rebuild_critical_path(items: Sequence[Dict[str, Any]], *, limit: int = 5) -> List[Dict[str, Any]]:
    path: List[Dict[str, Any]] = []
    for item in items:
        if _pri(item) not in ("CRITICAL", "HIGH"):
            continue
        path.append(
            {
                "task": item.get("task"),
                "source_url": item.get("source_url"),
                "source_label": item.get("source_label"),
                "verified": bool(item.get("verified")),
                "cost_verified": bool(item.get("cost_verified")),
                "estimated_cost": item.get("estimated_cost"),
                "priority": item.get("priority"),
            }
        )
        if len(path) >= limit:
            break
    return path


def normalize_analysis_punch(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Mutate analysis punch_list in place; return analysis."""
    if not isinstance(analysis, dict):
        return analysis
    punch = dict(analysis.get("punch_list") or {})
    items = list(punch.get("punch_list") or [])
    pi = analysis.get("project_info") or {}
    ptype = str(pi.get("type") or analysis.get("project_type") or "").lower()
    is_dc = any(x in ptype.replace(" ", "_").replace("-", "_") for x in ("data_center", "datacenter", "dc", "colo"))
    ranked = normalize_punch_items(items, is_dc=is_dc)
    punch["punch_list"] = ranked
    punch["critical_path"] = rebuild_critical_path(ranked)
    punch["ranked"] = True
    analysis["punch_list"] = punch
    summary = dict(analysis.get("summary") or {})
    summary["total_punch_list_items"] = len(ranked)
    analysis["summary"] = summary
    return analysis
