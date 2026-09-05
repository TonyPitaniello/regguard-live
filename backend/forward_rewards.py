"""Forward-receipt rewards — account credit for forwarders + partner affiliates."""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_BACKEND = Path(__file__).resolve().parent
_PATH = _BACKEND / "data" / "forward_rewards.json"
_LOCK = threading.Lock()

# Modest credits — high margin, enough to feel real
FORWARDER_CREDIT_USD = 5.0
PARTNER_FORWARD_CREDIT_USD = 10.0


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load() -> Dict[str, Any]:
    if not _PATH.is_file():
        return {"rewards": {}}
    try:
        return json.loads(_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"rewards": {}}


def _save(data: Dict[str, Any]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def reward_forward(
    *,
    research_id: str,
    email: str = "",
    referral_code: str = "",
    channel: str = "share",
) -> Dict[str, Any]:
    """
    On Bid Risk Receipt forward / share-unlock:
      - Forwarder email gets $5 account credit once per research_id
      - Affiliate (by referral_code or matching email) gets $10 once per research_id
    Idempotent per research_id + recipient.
    """
    rid = (research_id or "").strip()[:80]
    email_l = (email or "").strip().lower()
    code = (referral_code or "").strip().lower()
    if not rid:
        raise ValueError("research_id required")

    out: Dict[str, Any] = {
        "research_id": rid,
        "channel": (channel or "share")[:40],
        "forwarder_credit": None,
        "partner_credit": None,
        "already_rewarded": False,
    }

    with _LOCK:
        data = _load()
        rewards = dict(data.get("rewards") or {})
        key = rid
        row = dict(rewards.get(key) or {"research_id": rid, "forwarder": None, "partner": None})

        # --- Forwarder credit ---
        if email_l and not row.get("forwarder"):
            try:
                from account_credits import add_credit

                credit_row = add_credit(
                    email_l,
                    FORWARDER_CREDIT_USD,
                    reason=f"forward_receipt:{rid}:{channel}",
                )
                row["forwarder"] = {
                    "email": email_l,
                    "amount_usd": FORWARDER_CREDIT_USD,
                    "ts": _now(),
                    "channel": channel,
                }
                out["forwarder_credit"] = credit_row
            except Exception as e:
                logger.warning("forwarder credit failed: %s", e)
        elif email_l and row.get("forwarder"):
            out["already_rewarded"] = True

        # --- Partner / affiliate credit ---
        partner_email = ""
        partner_code = code
        try:
            from affiliate_store import get_affiliate, list_affiliates

            aff = get_affiliate(code) if code else None
            if not aff and email_l:
                aff = next(
                    (a for a in list_affiliates() if a.get("email") == email_l and a.get("active")),
                    None,
                )
            if aff:
                partner_email = str(aff.get("email") or "")
                partner_code = str(aff.get("code") or "")
        except Exception as e:
            logger.warning("affiliate resolve for forward failed: %s", e)

        if partner_email and not row.get("partner"):
            # Don't double-pay same email as both forwarder+partner on same event —
            # if same person, they already got forwarder credit; still grant partner bonus once.
            try:
                from account_credits import add_credit

                credit_row = add_credit(
                    partner_email,
                    PARTNER_FORWARD_CREDIT_USD,
                    reason=f"partner_forward:{rid}:{partner_code}",
                )
                row["partner"] = {
                    "email": partner_email,
                    "code": partner_code,
                    "amount_usd": PARTNER_FORWARD_CREDIT_USD,
                    "ts": _now(),
                    "channel": channel,
                }
                out["partner_credit"] = credit_row
            except Exception as e:
                logger.warning("partner forward credit failed: %s", e)

        rewards[key] = row
        data["rewards"] = rewards
        # Cap file growth
        if len(rewards) > 5000:
            keys = sorted(rewards.keys())
            for k in keys[: len(rewards) - 4000]:
                rewards.pop(k, None)
            data["rewards"] = rewards
        _save(data)

    return out


def rewards_for_email(email: str, limit: int = 50) -> Dict[str, Any]:
    email_l = (email or "").strip().lower()
    if not email_l:
        return {"email": "", "as_forwarder": [], "as_partner": []}
    data = _load()
    as_f = []
    as_p = []
    for row in (data.get("rewards") or {}).values():
        if not isinstance(row, dict):
            continue
        f = row.get("forwarder") or {}
        p = row.get("partner") or {}
        if f.get("email") == email_l:
            as_f.append({"research_id": row.get("research_id"), **f})
        if p.get("email") == email_l:
            as_p.append({"research_id": row.get("research_id"), **p})
    as_f = list(reversed(as_f))[:limit]
    as_p = list(reversed(as_p))[:limit]
    return {
        "email": email_l,
        "as_forwarder": as_f,
        "as_partner": as_p,
        "forwarder_total_usd": round(sum(float(x.get("amount_usd") or 0) for x in as_f), 2),
        "partner_total_usd": round(sum(float(x.get("amount_usd") or 0) for x in as_p), 2),
    }
