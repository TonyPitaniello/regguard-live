"""
Honesty layer for free-trial / preview analysis.

Contract:
- Never present stub environmental risk as LOW/MEDIUM/HIGH truth.
- Mark costs and timelines as unverified unless explicitly verified.
- Stamp every analysis with an ``honesty`` block consumers can trust.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

UNAVAILABLE = "UNAVAILABLE"
PRELIMINARY = "PRELIMINARY"

RISK_LABEL = (
    "Environmental risk score unavailable — not verified against parcel GIS data "
    "(FEMA/NWI/IPaC). Do not use for bidding."
)
COST_LABEL = "Unverified estimate — not an AHJ fee quote. Confirm with the local AHJ."
TIMELINE_LABEL = "Unverified estimate — confirm with AHJ / utility study track."


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
            "risk": RISK_LABEL if not risk_verified else "Risk score grounded in verified site data.",
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
    never shows a confident stub score.
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
    if not risk_verified and hide_stub_risk:
        env["risk_level"] = UNAVAILABLE
        env["risk_score_hidden"] = True
        env["risk_honesty_note"] = RISK_LABEL
        findings = env.get("findings") or []
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

        # Overall score stays UNAVAILABLE until full parcel suite is verified;
        # partial GIS (flood/wetlands) still shows per-finding verified badges.
        verified_n = sum(
            1
            for f in findings
            if isinstance(f, dict) and f.get("verified") and f.get("source_url")
        )
        if verified_n:
            env["risk_honesty_note"] = (
                f"{verified_n} finding(s) GIS-verified (FEMA/NWI). "
                "Overall risk score still unavailable until remaining layers are parcel-verified."
            )
            honesty["labels"]["risk"] = env["risk_honesty_note"]

        summary = out.setdefault("summary", {})
        # Count only verified HIGH/CRITICAL toward high_risk_count
        summary["high_risk_count"] = sum(
            1
            for f in findings
            if isinstance(f, dict)
            and f.get("verified")
            and str(f.get("risk_level") or "").upper() in ("HIGH", "CRITICAL")
        )
        summary["risk_level_display"] = UNAVAILABLE
        summary["estimates_unverified"] = True

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

    # Prefix timeline copy so SMS/email stay honest even without UI
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
        return True
    env = analysis.get("environmental_screening") or {}
    level = str(env.get("risk_level", "")).upper()
    if level in (UNAVAILABLE, PRELIMINARY, "UNKNOWN", ""):
        return False
    if analysis.get("preview") and not honesty.get("risk_verified"):
        return False
    if env.get("risk_score_hidden"):
        return False
    return level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
