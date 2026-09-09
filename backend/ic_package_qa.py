"""Boardroom package quality gate — GC-forward readiness score."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

BOARDROOM_PASS_SCORE = 80


def score_boardroom_package(package: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score a compose_ic_package() payload for $1,500 boardroom bar.
    Returns {score, max_score, pass, gaps, checklist}.
    """
    checks: List[Tuple[str, bool, int]] = []
    cover = package.get("cover") or {}
    ex = package.get("executive_summary") or {}
    stamp = ex.get("stamp") or {}
    band = ex.get("contingency") if isinstance(ex.get("contingency"), dict) else None
    findings = package.get("site_findings") or {}
    punch = (package.get("punch_list") or {}).get("items") or []
    sources = package.get("sources") or []
    gotcha_cards = findings.get("gotcha_cards") or findings.get("gotchas") or []

    checks.append(("Cover has site + AHJ", bool(cover.get("site") and cover.get("ahj_name")), 10))
    checks.append(("Stamp CLEAR/CAUTION/HOLD present", bool(stamp.get("display") or stamp.get("grade")), 10))
    checks.append(("Stamp plain-English explanation", bool(stamp.get("plain") or stamp.get("headline")), 5))
    checks.append(("Contingency band present", bool(band and band.get("pct_low") is not None), 10))
    checks.append(
        (
            "Contingency driver table (low/mid/high)",
            bool(band and (band.get("driver_table") or {}).get("rows")),
            15,
        )
    )
    checks.append(("Top risks or gotchas (>=2)", len(ex.get("top_risks") or []) + len(ex.get("local_gotchas") or []) >= 2, 10))
    checks.append(("Gotcha confirm cards (>=2)", len(gotcha_cards) >= 2, 10))
    checks.append(("Punch list or actions (>=3)", len(punch) >= 3 or len(package.get("action_plan_summary") or []) >= 3, 10))
    checks.append(("Source appendix (>=3 http)", len(sources) >= 3, 10))
    checks.append(("Disclaimers present", len(package.get("disclaimers") or []) >= 2, 5))
    checks.append(("Prepared-for or research id", bool(package.get("generated_for") or cover.get("research_id")), 5))

    score = sum(w for _, ok, w in checks if ok)
    max_score = sum(w for _, _, w in checks)
    gaps = [name for name, ok, _ in checks if not ok]
    checklist = [{"item": name, "ok": ok, "weight": w} for name, ok, w in checks]
    return {
        "score": score,
        "max_score": max_score,
        "pct": round(100.0 * score / max_score) if max_score else 0,
        "pass": score >= BOARDROOM_PASS_SCORE,
        "gaps": gaps,
        "checklist": checklist,
    }
