"""
Free vs Estimator deliverable shape.

Same FinOps pack path feeds both — this stamp is what makes Estimator visibly
worth $79: full forwardable Receipt habit vs Free bid-or-walk preview.
"""

from __future__ import annotations

from typing import Any, Dict, List


FREE_RECEIPT_MODE = "free_preview"
ESTIMATOR_RECEIPT_MODE = "estimator_habit"

# Free preview Receipt shows this many clear risk flags; the rest stay locked copy.
FREE_RECEIPT_RISK_CLEAR = 1
# Estimator habit Receipt shows the full top-3 risk block.
ESTIMATOR_RECEIPT_RISK_CLEAR = 3


def _ensure_punch_habit_fields(punch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for raw in punch:
        if not isinstance(raw, dict):
            continue
        row = dict(raw)
        owner = (
            str(row.get("owner") or row.get("responsible_party") or "").strip()
            or "Estimator"
        )
        due = (
            str(row.get("due_window") or row.get("timeline") or "").strip() or "Pre-bid"
        )
        row["owner"] = owner
        row["responsible_party"] = row.get("responsible_party") or owner
        row["due_window"] = due
        row["timeline"] = row.get("timeline") or due
        out.append(row)
    return out


def shape_free_vs_estimator(analysis: Dict[str, Any], *, habit_paid: bool) -> Dict[str, Any]:
    """
    Stamp Free vs Estimator so analysis JSON + Bid Risk Receipt PDF are not twins.

    Free: bid-or-walk preview Receipt (contingency locked in PDF, thin risk block).
    Estimator: full forwardable habit Receipt (contingency on, full top risks, punch owners).
    Does not invent Pro desk dollars or counsel ZIP.
    """
    if not isinstance(analysis, dict):
        return analysis
    out = dict(analysis)

    punch_block = out.get("punch_list") if isinstance(out.get("punch_list"), dict) else {}
    punch = list(punch_block.get("punch_list") or [])
    punch = _ensure_punch_habit_fields([p for p in punch if isinstance(p, dict)])

    if habit_paid:
        out["research_depth"] = "partner"
        out["depth_tier"] = "partner"
        out["access_tier"] = "partner"
        out["entitlement_tiers"] = ["partner"]
        out["receipt_mode"] = ESTIMATOR_RECEIPT_MODE
        out["preview"] = False
        out["depth_claim_honest"] = True
        out["research_incomplete"] = False
        out["depth_badge"] = "Estimator / Permit Runner — Receipt habit · unlocked punch"
        out["depth_claim_note"] = (
            "Estimator habit Receipt — full contingency + unlocked punch you can forward. "
            "Contractor Pro adds the City Pack PDF, punch/fee CSV, and bid packet. "
            "Dollars only when the schedule states them."
        )
        out["soft_lock_contingency"] = False
        out["receipt_risk_clear"] = ESTIMATOR_RECEIPT_RISK_CLEAR
        out["punch_list"] = {
            **punch_block,
            "punch_list": punch,
            "habit_unlocked": True,
        }
        # Estimator upsell is Pro — never leave a Free→Estimator CTA on a partner run
        offer = out.get("upgrade_offer") if isinstance(out.get("upgrade_offer"), dict) else {}
        if str(offer.get("cta_tier") or "").lower() in ("", "partner", "free"):
            out.pop("upgrade_offer", None)
    else:
        out["research_depth"] = "free"
        out["depth_tier"] = "free"
        out["access_tier"] = "free"
        out["entitlement_tiers"] = []
        out["receipt_mode"] = FREE_RECEIPT_MODE
        out["preview"] = True
        out["depth_claim_honest"] = True
        out["research_incomplete"] = False
        out["depth_badge"] = "Free Lookups — bid-or-walk preview"
        out["depth_claim_note"] = (
            "Free preview — shape of risk only. Estimator / Permit Runner ($79/mo) unlocks the "
            "full Bid Risk Receipt, contingency band, and punch list you can forward."
        )
        out["soft_lock_contingency"] = True
        out["receipt_risk_clear"] = FREE_RECEIPT_RISK_CLEAR
        # Keep full punch in JSON so the in-app Free soft-lock can tease locked lines.
        out["punch_list"] = {
            **punch_block,
            "punch_list": punch,
            "habit_unlocked": False,
        }

    out["scout_mode"] = out.get("scout_mode") or "none"
    return out


def is_free_preview_receipt(analysis: Dict[str, Any] | None) -> bool:
    if not isinstance(analysis, dict):
        return True
    mode = str(analysis.get("receipt_mode") or "").strip().lower()
    if mode == ESTIMATOR_RECEIPT_MODE:
        return False
    if mode == FREE_RECEIPT_MODE:
        return True
    depth = str(analysis.get("research_depth") or analysis.get("depth_tier") or "").lower()
    if depth in ("partner", "estimator", "pro", "pro_partial", "pro_light", "pro_local", "ic", "ic_full"):
        return False
    if depth.startswith("pro_"):
        return False
    return True
