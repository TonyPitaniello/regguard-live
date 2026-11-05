"""
Honesty layer for free-trial / preview analysis.

Contract:
- Never present stub environmental risk as LOW/MEDIUM/HIGH truth.
- Mark costs and timelines as unverified unless explicitly verified.
- Stamp every analysis with an ``honesty`` block consumers can trust.
- Overall env risk uses parcel GIS only (see calculate_overall_env_risk).
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, Dict, Optional

UNAVAILABLE = "UNAVAILABLE"
PRELIMINARY = "PRELIMINARY"

RISK_LABEL = (
    "Flood and wetlands stay Unverified until a FEMA or NWI page is attached. "
    "This is not a 0–100 score. Do not bid from it."
)
COST_LABEL = (
    "No permit total. When the city uses a valuation or floor-area table, "
    "confirm that table with the AHJ."
)
TIMELINE_LABEL = "Timeline is Unverified — confirm with the AHJ. This is not a filing date."
NO_PERMIT_TOTAL = COST_LABEL


_LOCKED_FEE_DOLLAR = re.compile(
    r"\s*\([^)]{0,80}\$\s?\d[\d,]*(?:\.\d+)?[^)]*\)|\$\s?\d[\d,]*(?:\.\d+)?"
)


def hide_locked_fee_dollars(text: str) -> str:
    """Drop fee amounts from a line that Free or Estimator is allowed to forward."""
    cleaned = _LOCKED_FEE_DOLLAR.sub("", text or "")
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
    return cleaned.strip()


def fee_dollars_unlocked(analysis: Optional[Dict[str, Any]]) -> bool:
    """Contractor Pro and the IC ZIP may print a schedule line. Free and Estimator may not."""
    if not isinstance(analysis, dict):
        return False
    depth = str(analysis.get("research_depth") or "").strip().lower()
    tier = str(analysis.get("depth_tier") or analysis.get("access_tier") or "").strip().lower()
    if analysis.get("ic_package") is True:
        return True
    if depth in ("ic", "ic_full") or tier in ("ic", "ic_full", "ic_project"):
        return True
    if depth.startswith("pro") or tier.startswith("pro") or tier == "contractor_pro":
        return True
    return False


def sourced_schedule_amounts(
    exposure: Any,
    *,
    source_url: str = "",
) -> Optional[tuple]:
    """A low/high pair only when this exposure is a cited schedule line."""
    if not isinstance(exposure, dict):
        return None
    if exposure.get("verified") is not True or exposure.get("basis") != "schedule_line":
        return None
    url = str(exposure.get("source_url") or source_url or "")
    if not url.startswith("http"):
        return None
    try:
        mid = float(exposure.get("usd_mid"))
    except (TypeError, ValueError):
        return None
    if mid <= 0:
        return None
    try:
        low = int(float(exposure.get("usd_low") if exposure.get("usd_low") is not None else mid))
        high = int(float(exposure.get("usd_high") if exposure.get("usd_high") is not None else mid))
    except (TypeError, ValueError):
        return None
    return low, high


def permit_total_line(summary: Optional[Dict[str, Any]], honesty: Optional[Dict[str, Any]] = None) -> str:
    """A single permit total prints only when a schedule page states that number."""
    honesty = honesty or {}
    summary = summary or {}
    if honesty.get("permit_total_stated") is not True:
        return NO_PERMIT_TOTAL
    try:
        cost = float(summary.get("estimated_total_cost") or 0)
    except (TypeError, ValueError):
        cost = 0.0
    url = str(honesty.get("permit_total_source_url") or "")
    if cost <= 0 or not url.startswith("http"):
        return NO_PERMIT_TOTAL
    return f"Permit total on the schedule: ${cost:,.0f}"


def is_ic_demo_enabled() -> bool:
    """IC queue demo APIs/UI are off unless REG_GUARD_IC_DEMO=1."""
    import os

    return os.getenv("REG_GUARD_IC_DEMO", "0").strip() == "1"


def honesty_block(
    *,
    risk_verified: bool = False,
    cost_verified: bool = False,
    timeline_verified: bool = False,
    source: str = "preview",
) -> Dict[str, Any]:
    return {
        "risk_verified": risk_verified,
        "cost_verified": cost_verified,
        "timeline_verified": timeline_verified,
        "source": source,
        "labels": {
            "risk": RISK_LABEL
            if not risk_verified
            else (
                "Flood and wetlands lines on this run have a mapper page. "
                "This is not a 0–100 score."
            ),
            "cost": COST_LABEL if not cost_verified else "Cost tied to cited fee schedule / source.",
            "timeline": TIMELINE_LABEL if not timeline_verified else "Timeline grounded in cited sources.",
        },
    }


def apply_honesty_layer(
    analysis: Dict[str, Any],
    *,
    source: str = "preview",
    risk_verified: bool = False,
    cost_verified: bool = False,
    timeline_verified: bool = False,
    hide_stub_risk: bool = True,
) -> Dict[str, Any]:
    """
    Return a deep-copied analysis stamped with honesty metadata.

    When risk is not verified, overall risk_level becomes UNAVAILABLE and
    per-finding LOW/MEDIUM/HIGH badges are rewritten to PRELIMINARY so UI
    never shows a confident stub score (GIS-verified findings keep their levels).
    """
    out = deepcopy(analysis) if analysis else {}
    out["preview"] = True if source in ("preview", "instant", "option_a", "client") else bool(
        out.get("preview", False)
    )
    if not risk_verified and hide_stub_risk:
        out["preview"] = True

    honesty = honesty_block(
        risk_verified=risk_verified,
        cost_verified=cost_verified,
        timeline_verified=timeline_verified,
        source=source,
    )
    out["honesty"] = honesty

    env = out.setdefault("environmental_screening", {})
    findings = env.get("findings") or []

    # Always recompute overall from GIS-only rules when findings exist
    try:
        from real_environmental_screening import calculate_overall_env_risk

        if findings:
            meta = calculate_overall_env_risk(findings)
            env["risk_level"] = meta["risk_level"]
            env["gis_complete"] = bool(meta.get("gis_complete"))
            env["risk_basis"] = meta.get("basis")
            if meta.get("risk_honesty_note"):
                env["risk_honesty_note"] = meta["risk_honesty_note"]
    except Exception:
        pass

    if not risk_verified and hide_stub_risk:
        env["risk_level"] = UNAVAILABLE
        env["risk_score_hidden"] = True
        env["risk_honesty_note"] = env.get("risk_honesty_note") or RISK_LABEL
        for finding in findings:
            if isinstance(finding, dict):
                # Preserve GIS-backed findings (FEMA NFHL / NWI) — do not strip to PRELIMINARY
                if finding.get("verified") and finding.get("source_url"):
                    finding["risk_level"] = finding.get("risk_level_raw") or finding.get("risk_level")
                    continue
                lvl = str(finding.get("risk_level", "")).upper()
                if lvl in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
                    finding["risk_level_raw"] = finding.get("risk_level")
                    finding["risk_level"] = PRELIMINARY
                    finding["verified"] = False

        verified_n = sum(
            1
            for f in findings
            if isinstance(f, dict) and f.get("verified") and f.get("source_url")
        )
        if verified_n:
            env["risk_honesty_note"] = env.get("risk_honesty_note") or (
                f"{verified_n} finding(s) cite FEMA or NWI. "
                "Flood and wetlands both have to resolve before this screen is Source. Not a 0–100 score."
            )
            honesty["labels"]["risk"] = env["risk_honesty_note"]

        summary = out.setdefault("summary", {})
        summary["high_risk_count"] = sum(
            1
            for f in findings
            if isinstance(f, dict)
            and f.get("verified")
            and str(f.get("risk_level") or "").upper() in ("HIGH", "CRITICAL")
        )
        summary["risk_level_display"] = UNAVAILABLE
        summary["estimates_unverified"] = True
    else:
        summary = out.setdefault("summary", {})
        summary["high_risk_count"] = sum(
            1
            for f in findings
            if isinstance(f, dict)
            and f.get("verified")
            and str(f.get("risk_level") or "").upper() in ("HIGH", "CRITICAL")
        )
        level = str(env.get("risk_level") or "UNKNOWN").upper()
        summary["risk_level_display"] = level
        env["risk_score_hidden"] = level in ("UNKNOWN", "UNAVAILABLE", "PRELIMINARY", "")
        if env.get("risk_honesty_note"):
            honesty["labels"]["risk"] = env["risk_honesty_note"]

    punch = out.get("punch_list") or {}
    if isinstance(punch, dict) and not cost_verified:
        punch["cost_verified"] = False
        punch["estimates_unverified"] = True
        for item in punch.get("punch_list") or []:
            if isinstance(item, dict):
                item["cost_verified"] = False
                item["estimates_unverified"] = True
        out["punch_list"] = punch

    summary = out.setdefault("summary", {})
    summary["cost_verified"] = cost_verified
    summary["timeline_verified"] = timeline_verified
    summary["risk_verified"] = risk_verified
    if not cost_verified or not timeline_verified:
        summary["estimates_unverified"] = True

    timeline = summary.get("estimated_timeline")
    if timeline and not timeline_verified:
        tl = str(timeline)
        if "unverified" not in tl.lower():
            summary["estimated_timeline"] = f"{tl} (unverified)"

    return out


def analysis_shows_risk_score(analysis: Optional[Dict[str, Any]]) -> bool:
    if not analysis:
        return False
    honesty = analysis.get("honesty") or {}
    if honesty.get("risk_verified") is True:
        env = analysis.get("environmental_screening") or {}
        level = str(env.get("risk_level", "")).upper()
        # Incomplete GIS must not display as a confident score
        if level in (UNAVAILABLE, PRELIMINARY, "UNKNOWN", ""):
            return False
        if env.get("risk_score_hidden"):
            return False
        return level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    env = analysis.get("environmental_screening") or {}
    level = str(env.get("risk_level", "")).upper()
    if level in (UNAVAILABLE, PRELIMINARY, "UNKNOWN", ""):
        return False
    if analysis.get("preview") and not honesty.get("risk_verified"):
        return False
    if env.get("risk_score_hidden"):
        return False
    return level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
