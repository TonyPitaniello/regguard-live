"""Account credit balance (USD) — e.g. approved Partner gotcha credits."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

_BACKEND_DIR = Path(__file__).resolve().parent
_PATH = _BACKEND_DIR / "data" / "account_credits.json"
_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load() -> Dict[str, Any]:
    if not _PATH.is_file():
        return {"balances": {}, "ledger": []}
    try:
        return json.loads(_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"balances": {}, "ledger": []}


def _save(data: Dict[str, Any]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_balance_usd(email: str) -> float:
    email_l = (email or "").strip().lower()
    if not email_l:
        return 0.0
    with _LOCK:
        data = _load()
        return float((data.get("balances") or {}).get(email_l) or 0)


def add_credit(email: str, amount_usd: float, *, reason: str = "") -> Dict[str, Any]:
    email_l = (email or "").strip().lower()
    if not email_l or amount_usd <= 0:
        raise ValueError("email and positive amount required")
    with _LOCK:
        data = _load()
        bal = float((data.get("balances") or {}).get(email_l) or 0) + float(amount_usd)
        data.setdefault("balances", {})[email_l] = round(bal, 2)
        ledger = list(data.get("ledger") or [])
        row = {
            "ts": _now(),
            "email": email_l,
            "delta_usd": round(float(amount_usd), 2),
            "balance_usd": round(bal, 2),
            "reason": reason or "credit",
        }
        ledger.append(row)
        data["ledger"] = ledger[-500:]
        _save(data)
        return row


def consume_credit(email: str, amount_usd: float, *, reason: str = "checkout") -> float:
    """Consume up to amount_usd; return amount actually consumed."""
    email_l = (email or "").strip().lower()
    want = max(0.0, float(amount_usd))
    if not email_l or want <= 0:
        return 0.0
    with _LOCK:
        data = _load()
        bal = float((data.get("balances") or {}).get(email_l) or 0)
        take = min(bal, want)
        if take <= 0:
            return 0.0
        data.setdefault("balances", {})[email_l] = round(bal - take, 2)
        ledger = list(data.get("ledger") or [])
        ledger.append(
            {
                "ts": _now(),
                "email": email_l,
                "delta_usd": round(-take, 2),
                "balance_usd": round(bal - take, 2),
                "reason": reason,
            }
        )
        data["ledger"] = ledger[-500:]
        _save(data)
        return round(take, 2)
