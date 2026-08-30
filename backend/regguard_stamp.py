"""
RegGuard Stamp v2 — PASS / CAUTION / FAIL pre-bid rating.

Planning aid only — not a bond, insurance quote, legal opinion, or interconnection study.
Stamp goes stale when the local fingerprint (pack/radar/AHJ) moves or validity window expires.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

STAMP_VERSION = "2026-08-29"
DEFAULT_VALID_DAYS = 7


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime] = None) -> str:
    d = dt or _utcnow()
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pi(analysis: Dict[str, Any]) -> Dict[str, Any]:
    return analysis.get("project_info") or {}


def compute_ground_truth_fingerprint(analysis: Dict[str, Any]) -> str:
    """Stable hash of citeable local ground truth used to invalidate stamps."""
    pi = _pi(analysis)
    pack = analysis.get("local_pack") or {}
    ahj = analysis.get("ahj_card") or {}
    fee = analysis.get("fee_card") or {}
    cov = analysis.get("coverage") or {}
    radar = analysis.get("moratorium_radar") or {}
    snap = analysis.get("arbitrage_snapshot") or {}

    fees = []
    for f in fee.get("fees") or pack.get("fees") or []:
        if isinstance(f, dict):
            fees.append(
                f"{f.get('trade')}|{f.get('label')}|{f.get('amount_usd')}|{f.get('source_url') or f.get('citation_url')}"
            )
    gotchas = []
    for g in (pack.get("gotchas") or analysis.get("gotcha_watchlist", {}).get("items") or []):
        if isinstance(g, dict):
            gotchas.append(f"{g.get('id') or g.get('title')}|{g.get('source_url') or g.get('citation_url')}")

    blob = "|".join(
        [
            str(pi.get("zip") or "")[:5],
            str(pi.get("city") or ""),
            str(pi.get("state") or ""),
            str(ahj.get("name") or ""),
            str(ahj.get("portal_url") or ""),
            str(ahj.get("last_verified") or pack.get("last_verified") or ""),
            str(cov.get("tier") or ""),
            str(radar.get("updated") or ""),
            str(radar.get("high_alert_state")),
            str(snap.get("pack_key") or pack.get("pack_key") or ""),
            *sorted(fees)[:40],
            *sorted(gotchas)[:40],
        ]
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def fingerprint_for_zip_meta(meta: Dict[str, Any], *, zip_code: str = "") -> str:
    """Fingerprint slice aligned with zip_watch pack meta (for invalidation notices)."""
    blob = "|".join(
        [
            str(zip_code or "")[:5],
            str(meta.get("ahj_id") or ""),
            str(meta.get("last_verified") or ""),
            str(meta.get("portal") or ""),
            str(meta.get("fee_count") or ""),
            str(meta.get("gotcha_count") or ""),
            str(meta.get("dc_metro_count") or ""),
        ]
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def _drivers_and_grade(analysis: Dict[str, Any]) -> Tuple[str, List[Dict[str, str]], List[str]]:
    """
    Returns (grade, drivers[upto 3], reasons_all).
    FAIL / CAUTION / PASS
    """
    drivers: List[Dict[str, str]] = []
    reasons: List[str] = []
    fail = False
    caution = False

    killers = [k for k in (analysis.get("margin_killers") or []) if isinstance(k, dict)]
    crit = [k for k in killers if str(k.get("priority") or "").upper() in ("CRITICAL", "CRIT")]
    if len(crit) >= 2:
        fail = True
        reasons.append(f"{len(crit)} Critical margin killers")
        drivers.append(
            {
                "severity": "FAIL",
                "label": crit[0].get("title") or "Critical margin killer",
                "detail": (crit[0].get("detail") or "")[:160],
                "source_url": str(crit[0].get("source_url") or ""),
            }
        )
    elif len(crit) == 1:
        caution = True
        reasons.append("1 Critical margin killer")
        drivers.append(
            {
                "severity": "CAUTION",
                "label": crit[0].get("title") or "Critical margin killer",
                "detail": (crit[0].get("detail") or "")[:160],
                "source_url": str(crit[0].get("source_url") or ""),
            }
        )

    band = analysis.get("contingency_band") or {}
    mid = band.get("pct_mid")
    if isinstance(mid, (int, float)) and mid >= 15:
        fail = True
        reasons.append(f"Contingency mid {mid}%")
        drivers.append(
            {
                "severity": "FAIL",
                "label": f"High contingency band (mid {mid}%)",
                "detail": "Planning aid — confirm fees/timeline with AHJ before bid.",
                "source_url": "",
            }
        )
    elif isinstance(mid, (int, float)) and mid >= 10:
        caution = True
        reasons.append(f"Contingency mid {mid}%")
        if len(drivers) < 3:
            drivers.append(
                {
                    "severity": "CAUTION",
                    "label": f"Elevated contingency (mid {mid}%)",
                    "detail": str(band.get("disclaimer") or "")[:160],
                    "source_url": "",
                }
            )

    cov = analysis.get("coverage") or {}
    tier = str(cov.get("tier") or "").lower()
    if tier in ("federal_state", "thin", "unverified"):
        caution = True
        # Never allow PASS on thin / Unverified packs — that is clearance theater.
        reasons.append(f"Coverage tier: {tier or 'thin'}")
        if len(drivers) < 3:
            drivers.append(
                {
                    "severity": "CAUTION",
                    "label": cov.get("badge") or "Limited local pack depth",
                    "detail": (cov.get("warning") or cov.get("note") or "Pack depth insufficient for PASS.")[
                        :160
                    ],
                    "source_url": "",
                }
            )

    # Explicit coverage honesty: missing badge/tier still cannot be PASS.
    cov_badge = str(cov.get("badge") or "").lower()
    if "unverified" in cov_badge or "thin" in cov_badge or "federal" in cov_badge:
        caution = True
        if not any("pack depth" in (d.get("label") or "").lower() or "coverage" in (d.get("label") or "").lower() for d in drivers):
            if len(drivers) < 3:
                drivers.append(
                    {
                        "severity": "CAUTION",
                        "label": "Pack depth insufficient for PASS",
                        "detail": "Citeable local pack required before a PASS stamp.",
                        "source_url": "",
                    }
                )

    radar = analysis.get("moratorium_radar") or {}
    if radar.get("is_stale"):
        caution = True
        reasons.append("Moratorium radar stale")
        if len(drivers) < 3:
            drivers.append(
                {
                    "severity": "CAUTION",
                    "label": "Moratorium radar stale",
                    "detail": (radar.get("stale_banner") or "Re-verify before LOI.")[:160],
                    "source_url": "",
                }
            )
    if radar.get("high_alert_state"):
        fail = True
        reasons.append("Moratorium high alert")
        drivers.insert(
            0,
            {
                "severity": "FAIL",
                "label": radar.get("headline") or "Moratorium / pause high alert",
                "detail": "Verify bill/ordinance status with counsel before LOI.",
                "source_url": "",
            },
        )

    friction = analysis.get("community_friction") or analysis.get("opposition_card") or {}
    score = friction.get("score")
    band_f = str(friction.get("band") or "").lower()
    if (isinstance(score, (int, float)) and score >= 8) or "high" in band_f or "elevat" in band_f:
        caution = True
        reasons.append("Community friction elevated")
        if len(drivers) < 3:
            drivers.append(
                {
                    "severity": "CAUTION",
                    "label": friction.get("headline") or "Community friction elevated",
                    "detail": (friction.get("disclaimer") or "")[:160],
                    "source_url": "",
                }
            )

    clocks = analysis.get("parallel_clocks") or {}
    if clocks.get("clocks") and (analysis.get("dc_positioning") or {}).get("parallel_clocks"):
        caution = True
        reasons.append("DC parallel AHJ + utility clocks")
        if len(drivers) < 3:
            drivers.append(
                {
                    "severity": "CAUTION",
                    "label": "Parallel AHJ + utility clocks",
                    "detail": clocks.get("headline")
                    or "Municipal and interconnection paths often run separately.",
                    "source_url": "",
                }
            )

    # Dedupe drivers by label
    seen = set()
    uniq: List[Dict[str, str]] = []
    for d in drivers:
        key = d.get("label") or ""
        if key in seen:
            continue
        seen.add(key)
        uniq.append(d)
    drivers = uniq[:3]

    if fail:
        grade = "FAIL"
    elif caution:
        grade = "CAUTION"
    else:
        grade = "PASS"
        if not drivers:
            drivers = [
                {
                    "severity": "PASS",
                    "label": "No Critical killers on current pack",
                    "detail": "Still confirm fees on the official AHJ schedule before bid.",
                    "source_url": str((analysis.get("ahj_card") or {}).get("fees_url") or ""),
                }
            ]

    return grade, drivers, reasons


def build_regguard_stamp(
    analysis: Dict[str, Any],
    *,
    valid_days: int = DEFAULT_VALID_DAYS,
    flagged_by: str = "RegGuard",
) -> Dict[str, Any]:
    """Compute stamp dict (does not mutate analysis)."""
    now = _utcnow()
    expires = now + timedelta(days=max(1, int(valid_days)))
    grade, drivers, reasons = _drivers_and_grade(analysis)
    fp = compute_ground_truth_fingerprint(analysis)
    pi = _pi(analysis)
    return {
        "schema": "regguard.stamp.v2",
        "version": STAMP_VERSION,
        "grade": grade,
        "label": f"REGGUARD STAMP: {grade}",
        "headline": {
            "PASS": "No Critical local killers on current citeable pack — still confirm before bid",
            "CAUTION": "Material pre-bid risk — review drivers before locking a number",
            "FAIL": "Do not treat this site/bid as clear — resolve drivers before money moves",
        }.get(grade, grade),
        "drivers": drivers,
        "reasons": reasons[:8],
        "fingerprint": fp,
        "stamped_at": _iso(now),
        "valid_until": _iso(expires),
        "valid_days": int(valid_days),
        "flagged_by": (flagged_by or "RegGuard")[:80],
        "site": {
            "address": pi.get("address"),
            "city": pi.get("city"),
            "state": pi.get("state"),
            "zip": pi.get("zip"),
        },
        "is_stale": False,
        "stale_reason": "",
        "disclaimer": (
            "Planning aid for pre-bid / pre-LOI screening. Not a bond, insurance quote, "
            "legal opinion, or interconnection study. Stamp is invalid after valid_until "
            "or when local pack / AHJ / moratorium fingerprint changes."
        ),
    }


def apply_regguard_stamp(analysis: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    if not isinstance(analysis, dict):
        return analysis
    stamp = build_regguard_stamp(analysis, **kwargs)
    analysis["regguard_stamp"] = stamp
    # Convenience mirrors for share/PDF
    analysis["stamp_grade"] = stamp["grade"]
    analysis["stamp_label"] = stamp["label"]
    analysis["stamp_valid_until"] = stamp["valid_until"]
    analysis["stamp_fingerprint"] = stamp["fingerprint"]
    return analysis


def evaluate_stamp_freshness(
    stamp: Optional[Dict[str, Any]],
    *,
    current_fingerprint: Optional[str] = None,
    analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return stamp copy with is_stale / stale_reason updated."""
    if not isinstance(stamp, dict) or not stamp:
        return {
            "is_stale": True,
            "stale_reason": "No stamp on file — run diligence for a fresh RegGuard stamp.",
            "grade": None,
        }
    out = dict(stamp)
    now = _utcnow()
    reason = ""
    stale = False

    valid_until = str(stamp.get("valid_until") or "")
    try:
        if valid_until:
            exp = datetime.strptime(valid_until.replace("Z", ""), "%Y-%m-%dT%H:%M:%S").replace(
                tzinfo=timezone.utc
            )
            if now > exp:
                stale = True
                reason = f"Validity window ended ({valid_until}). Re-run for a fresh stamp."
    except Exception:
        pass

    fp_now = current_fingerprint
    if not fp_now and isinstance(analysis, dict):
        fp_now = compute_ground_truth_fingerprint(analysis)
    fp_old = str(stamp.get("fingerprint") or "")
    if fp_now and fp_old and fp_now != fp_old:
        stale = True
        reason = (
            "Local ground truth changed (pack / AHJ / moratorium fingerprint). "
            "Prior stamp is invalid — re-run diligence."
        )

    out["is_stale"] = stale
    out["stale_reason"] = reason
    out["checked_at"] = _iso(now)
    if fp_now:
        out["current_fingerprint"] = fp_now
    return out


def zip_watch_stamp_notice(change: Dict[str, Any]) -> str:
    """One-liner for email/SMS when a watched ZIP fingerprint moves."""
    z = change.get("zip") or ""
    return (
        f"RegGuard stamp for ZIP {z} is outdated — local diligence fingerprint changed. "
        f"Re-run the site for a fresh PASS/CAUTION/FAIL before bid or LOI."
    )
