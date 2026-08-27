"""
Data-center diligence cards — stamp onto analysis for Results / Receipt / export.

Planning aids only — not interconnection studies, tariff quotes, or protest forecasts.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

_BACKEND = Path(__file__).resolve().parent
_RADAR_PATH = _BACKEND / "moratorium_radar.json"


def _is_dc(analysis: Dict[str, Any]) -> bool:
    pi = analysis.get("project_info") or {}
    t = str(pi.get("type") or "").lower().replace(" ", "_").replace("-", "_")
    blob = f"{t} {pi.get('label') or ''} {analysis.get('project_type') or ''}".lower()
    return any(
        k in blob
        for k in (
            "data_center",
            "datacenter",
            "colocation",
            "colo",
            "hyperscale",
            "ai_crypto",
            "large_load",
        )
    ) or bool(analysis.get("dc_positioning"))


def _state(analysis: Dict[str, Any]) -> str:
    pi = analysis.get("project_info") or {}
    return str(pi.get("state") or "").strip().upper()[:2]


def _city(analysis: Dict[str, Any]) -> str:
    return str((analysis.get("project_info") or {}).get("city") or "").strip()


def _zip(analysis: Dict[str, Any]) -> str:
    return "".join(c for c in str((analysis.get("project_info") or {}).get("zip") or "") if c.isdigit())[:5]


def _scout_step(analysis: Dict[str, Any], key: str) -> Dict[str, Any]:
    for container in (
        analysis.get("universal_scout") or {},
        analysis.get("scout") or {},
        analysis.get("research_steps") or {},
        analysis,
    ):
        if isinstance(container, dict) and isinstance(container.get(key), dict):
            return container[key]
    steps = analysis.get("scout_steps") or analysis.get("steps") or []
    if isinstance(steps, list):
        for s in steps:
            if isinstance(s, dict) and (s.get("key") or s.get("step") or s.get("id")) == key:
                return s
    return {}


def _step_hits(step: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    out = []
    for r in (step.get("results") or [])[:limit]:
        if not isinstance(r, dict):
            continue
        out.append(
            {
                "title": r.get("title") or r.get("name") or "Source",
                "url": r.get("url") or r.get("link") or "",
                "snippet": (r.get("description") or r.get("snippet") or "")[:240],
            }
        )
    return out


def load_moratorium_radar() -> Dict[str, Any]:
    if not _RADAR_PATH.is_file():
        return {"updated": "", "metros": []}
    try:
        return json.loads(_RADAR_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"updated": "", "metros": []}


def radar_stale_meta(
    data: Optional[Dict[str, Any]] = None,
    *,
    stale_after_days: int = 14,
) -> Dict[str, Any]:
    """Compute staleness from radar ``updated`` date (YYYY-MM-DD)."""
    from datetime import datetime, timezone

    payload = data if isinstance(data, dict) else load_moratorium_radar()
    updated = str(payload.get("updated") or "").strip()[:10]
    days = None
    is_stale = True
    try:
        if updated:
            dt = datetime.strptime(updated, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            days = max(0, int((datetime.now(timezone.utc) - dt).total_seconds() // 86400))
            is_stale = days > int(stale_after_days)
    except Exception:
        is_stale = True
        days = None
    return {
        "updated": updated,
        "stale_after_days": int(stale_after_days),
        "age_days": days,
        "is_stale": is_stale,
        "stale_banner": (
            f"Radar last verified {updated or 'unknown'} "
            f"({days if days is not None else '?'} days ago) — "
            "do not treat as current law. Verify with counsel."
            if is_stale
            else ""
        ),
    }


def save_moratorium_radar(
    metros: List[Dict[str, Any]],
    *,
    updated: Optional[str] = None,
    disclaimer: Optional[str] = None,
) -> Dict[str, Any]:
    from datetime import datetime, timezone

    existing = load_moratorium_radar()
    clean = [m for m in (metros or []) if isinstance(m, dict) and m.get("metro")]
    if not clean:
        raise ValueError("metros required")
    stamp = (updated or "").strip()[:10] or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = {
        "updated": stamp,
        "disclaimer": disclaimer
        or existing.get("disclaimer")
        or (
            "Seeded planning radar — verify ordinance/bill status with counsel. "
            "Not a live legislative API."
        ),
        "metros": clean,
    }
    _RADAR_PATH.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out


def radar_for_state(state: str) -> List[Dict[str, Any]]:
    st = (state or "").strip().upper()[:2]
    data = load_moratorium_radar()
    metros = []
    for m in data.get("metros") or []:
        if not isinstance(m, dict):
            continue
        if st and str(m.get("state") or "").upper()[:2] != st:
            continue
        metros.append(m)
    return metros


def build_parallel_clocks(analysis: Dict[str, Any]) -> Dict[str, Any]:
    ahj = analysis.get("ahj_card") or {}
    return {
        "title": "Parallel clocks — AHJ vs utility / RTO",
        "headline": "Municipal permits and interconnection often run on separate clocks",
        "clocks": [
            {
                "track": "ahj",
                "label": "AHJ / building / land use",
                "owner": ahj.get("name") or "Local AHJ",
                "status": "Confirm portal + hearings before bid",
                "url": ahj.get("portal_url") or ahj.get("apply_url") or "",
            },
            {
                "track": "utility",
                "label": "Utility interconnection / large-load",
                "owner": "Serving utility / TDSP (confirm)",
                "status": "Study path is NOT run by RegGuard — flag parallel schedule risk",
                "url": "",
            },
            {
                "track": "federal",
                "label": "Federal / FAST-41 (if scale qualifies)",
                "owner": "Permitting Council / federal agencies",
                "status": "See FAST-41 card when >100 MW hints present",
                "url": "https://www.permits.performance.gov/",
            },
        ],
        "disclaimer": (
            "Planning aid — does not file AHJ applications or run interconnection studies."
        ),
    }


def build_moratorium_radar_card(analysis: Dict[str, Any]) -> Dict[str, Any]:
    from data_center_intel import (
        bill_specific_conflict_notes,
        moratorium_high_alert_for_state,
        normalize_us_state,
    )

    st = normalize_us_state(_state(analysis))
    city = _city(analysis)
    scout = _scout_step(analysis, "step_dc_local_moratorium")
    hits = _step_hits(scout)
    metros = radar_for_state(st)
    # Prefer metros matching city name
    city_l = city.lower()
    local = [m for m in metros if city_l and city_l in str(m.get("metro") or "").lower()]
    show = local or metros[:6]
    high = moratorium_high_alert_for_state(st)
    bills = bill_specific_conflict_notes(st)
    stale = radar_stale_meta()
    # Suppress HIGH ALERT styling when radar seed is stale
    effective_high = bool(high) and not stale.get("is_stale")
    return {
        "title": "Moratorium / pause radar",
        "headline": (
            f"HIGH ALERT — {st} tracked for moratorium / session risk"
            if effective_high
            else (
                f"STALE RADAR — re-verify before LOI ({st or 'site'})"
                if stale.get("is_stale") and high
                else f"Monitor township/county pauses near {city or st or 'site'}"
            )
        ),
        "high_alert_state": effective_high,
        "high_alert_suppressed_stale": bool(high) and bool(stale.get("is_stale")),
        "state": st,
        "metros": show,
        "scout_hits": hits,
        "bill_notes": list(bills.values()),
        "updated": stale.get("updated"),
        "age_days": stale.get("age_days"),
        "is_stale": stale.get("is_stale"),
        "stale_banner": stale.get("stale_banner") or "",
        "disclaimer": (
            "Seeded planning radar + SERP hits — verify bill/ordinance status with counsel. "
            "Not a live legislative feed."
        ),
    }


def build_power_path_card(analysis: Dict[str, Any]) -> Dict[str, Any]:
    from data_center_intel import (
        estimate_infrastructure_surcharge_band_usd,
        fast41_transparency_project_candidate,
        federal_permitting_post_proclamation_note,
        parse_dc_scale_from_text,
    )

    pi = analysis.get("project_info") or {}
    blob = " ".join(
        str(x)
        for x in (
            pi.get("address"),
            pi.get("notes"),
            analysis.get("user_notes"),
            analysis.get("voice_context"),
            json.dumps(analysis.get("summary") or {})[:400],
        )
        if x
    )
    mw, capex = parse_dc_scale_from_text(blob)
    st = _state(analysis)
    band = estimate_infrastructure_surcharge_band_usd(st, mw=mw, capex_usd=capex)
    fast41 = fast41_transparency_project_candidate(mw)
    energy = _step_hits(_scout_step(analysis, "step_dc_state_energy"))
    return {
        "title": "Power path honesty",
        "headline": "Utility / large-load path — NOT an interconnection study",
        "mw_hint": mw,
        "capex_hint_usd": capex,
        "fast41_candidate": fast41,
        "federal_note": federal_permitting_post_proclamation_note(),
        "surcharge_band": band,
        "state_energy_hits": energy,
        "checklist": [
            "Confirm serving utility / TDSP for this parcel",
            "Ask utility which study product applies (FS / SIS / LGIA — names vary)",
            "Treat surcharge band as planning only — tariff filings control",
            "Do not claim MW available without utility written study",
        ],
        "disclaimer": (
            "RegGuard does not estimate feeder capacity or queue position. "
            "Use this card to avoid fake 'we have power' narratives before LOI."
        ),
    }


def build_water_cooling_card(analysis: Dict[str, Any]) -> Dict[str, Any]:
    water = _step_hits(_scout_step(analysis, "step_data_center_water"))
    wue = _step_hits(_scout_step(analysis, "step_water_usage_effectiveness"))
    return {
        "title": "Water & cooling constraints",
        "headline": "Withdrawal / drought / discharge diligence (citeable SERP)",
        "water_hits": water,
        "wue_hits": wue,
        "checklist": [
            "Confirm water source (municipal / groundwater / reuse) with utility + AHJ",
            "Check drought contingency / large-user restrictions",
            "Discharge / wastewater capacity for cooling blowdown",
            "WUE / liquid cooling narrative — verify against design criteria",
        ],
        "disclaimer": (
            "Not water-rights certainty. Confirm with water authority and counsel."
        ),
    }


def build_opposition_card(analysis: Dict[str, Any]) -> Dict[str, Any]:
    friction = analysis.get("community_friction") or {}
    signals = list(friction.get("signals") or [])
    # Promote elevated signals
    hot = [s for s in signals if isinstance(s, dict) and int(s.get("level") or 0) >= 2]
    ahj = analysis.get("ahj_card") or {}
    return {
        "title": "Community opposition early-warning",
        "headline": friction.get("headline") or "Heuristic friction index",
        "band": friction.get("band"),
        "score": friction.get("score"),
        "score_max": friction.get("score_max") or 12,
        "hot_signals": hot or signals[:4],
        "actions": [
            {
                "label": "Open AHJ portal / agenda",
                "url": ahj.get("portal_url") or "",
            },
            {
                "label": "EPA EJScreen at pin",
                "url": "https://ejscreen.epa.gov/mapper/",
            },
        ],
        "disclaimer": friction.get("disclaimer")
        or "Signals only — not a protest prediction. Confirm hearings on official agendas.",
    }


def build_fast41_card(analysis: Dict[str, Any]) -> Dict[str, Any]:
    from data_center_intel import (
        fast41_transparency_project_candidate,
        federal_permitting_post_proclamation_note,
        parse_dc_scale_from_text,
        permit_conflict_alert,
    )

    pi = analysis.get("project_info") or {}
    mw, capex = parse_dc_scale_from_text(
        str(pi.get("notes") or ""),
        str(analysis.get("user_notes") or ""),
        str(analysis.get("voice_context") or ""),
    )
    st = _state(analysis)
    candidate = fast41_transparency_project_candidate(mw)
    scout_m = _scout_step(analysis, "step_dc_local_moratorium")
    hit_count = len(scout_m.get("results") or [])
    active, rationale = permit_conflict_alert(
        vertical="data_center",
        transparency_candidate=candidate,
        state=st,
        moratorium_hit_count=hit_count,
    )
    fed = _step_hits(_scout_step(analysis, "step_federal_fast41"))
    return {
        "title": "FAST-41 / federal gate",
        "headline": (
            "Transparency Project candidate (>100 MW hint)"
            if candidate
            else "Federal diligence — confirm scale gates"
        ),
        "fast41_candidate": candidate,
        "mw_hint": mw,
        "federal_note": federal_permitting_post_proclamation_note(),
        "conflict": {"active": active, "note": rationale},
        "scout_hits": fed,
        "portal": "https://www.permits.performance.gov/",
        "disclaimer": "Verify against official Permitting Council / Federal Register text.",
    }


def stamp_dc_diligence(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Attach all DC cards when project is data-center / large-load."""
    if not isinstance(analysis, dict) or not _is_dc(analysis):
        return analysis
    out = analysis
    out["dc_positioning"] = {
        "headline": "Parallel-track Bid Risk Receipt for data center / large-load sites",
        "pitch": (
            "AHJ permits, utility interconnection, and large-load diligence often run "
            "on separate clocks. This receipt surfaces that risk before bid — it does "
            "not run interconnection studies or file AHJ applications."
        ),
        "buyer": "IC consultants, electrical PMs, GC bid leads, site selection teams",
        "parallel_clocks": True,
    }
    out["parallel_clocks"] = build_parallel_clocks(out)
    out["moratorium_radar"] = build_moratorium_radar_card(out)
    out["power_path_card"] = build_power_path_card(out)
    out["water_cooling_card"] = build_water_cooling_card(out)
    # opposition needs community_friction first
    if not out.get("community_friction"):
        try:
            from community_friction import build_community_friction

            out["community_friction"] = build_community_friction(out)
        except Exception:
            pass
    out["opposition_card"] = build_opposition_card(out)
    out["fast41_card"] = build_fast41_card(out)
    out["dc_diligence_version"] = "2026-08-26"
    return out


def diligence_export_payload(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """JSON export for CRM / GIS / Airtable ingestion."""
    stamped = stamp_dc_diligence(dict(analysis) if isinstance(analysis, dict) else {})
    pi = stamped.get("project_info") or {}
    return {
        "schema": "regguard.dc_diligence.v1",
        "site": {
            "address": pi.get("address"),
            "city": pi.get("city"),
            "state": pi.get("state"),
            "zip": pi.get("zip"),
            "project_type": pi.get("type"),
        },
        "parallel_clocks": stamped.get("parallel_clocks"),
        "moratorium_radar": stamped.get("moratorium_radar"),
        "power_path": stamped.get("power_path_card"),
        "water_cooling": stamped.get("water_cooling_card"),
        "opposition": stamped.get("opposition_card"),
        "fast41": stamped.get("fast41_card"),
        "ahj": stamped.get("ahj_card"),
        "contingency_band": stamped.get("contingency_band"),
        "margin_killers": stamped.get("margin_killers"),
        "share_url": stamped.get("share_url"),
        "research_id": stamped.get("research_id"),
        "disclaimer": (
            "Planning aid for pre-bid / pre-LOI screening. Not an interconnection study, "
            "engineering report, or legal opinion."
        ),
    }
