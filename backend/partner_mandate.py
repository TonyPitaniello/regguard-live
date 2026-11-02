"""Partner mandate kit expansion — templates + day0/day7 + dual-write."""
from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_BACKEND = Path(__file__).resolve().parent
_PATH = _BACKEND / "data" / "partner_mandate_outreach.jsonl"
_LOCK = threading.Lock()

MANDATE_ONE_LINER = (
    "No HOLD stamp, no bid attach. Citeable DFW–Austin pre-bid diligence. "
    "Source or Unverified. Not a quote."
)

MANDATE_SCRIPT = """Subject / opener (text or email):

Quick ask for bid week — RegGuard stamp.

When a sub or peer sends a number for a site, reply:

"Attach the Reg Guard Bid Risk Receipt for that address or I can't review it.
HOLD / CAUTION / CLEAR — Source or Unverified. Not a quote, sealed bid, Phase I ESA, or interconnection study."

Then forward ONE real receipt PDF from a live job this week so they see the artifact.

Day-0: stamp in the bid thread.
Day-7: if zip-watch says stamp outdated, re-run before LOI.

Privacy / product: https://app.regguardagent.com/
Sample: share your latest /r/{research_id} link.

— Reg Guard referral kit. Planning aid for DFW–Austin commercial–industrial work. Not an AHJ filing.
"""

MANDATE_EMAIL = """Subject: RegGuard stamp (optional for bid week)

Hi {partner_name},

I'm asking for a simple bid-week habit. When a contractor or peer sends a site number, reply:

Attach the RegGuard Bid Risk Receipt / stamp for that address or I can't review it.
HOLD / CAUTION / CLEAR — Source or Unverified. Not a quote, sealed bid, Phase I ESA, or interconnection study.

Then forward ONE real receipt PDF from a live job this week so they see the artifact.

Day-0: stamp in the bid thread.
Day-7: if zip-watch says stamp outdated, re-run before LOI.

Product: https://app.regguardagent.com/
Sample: share your latest /r/{research_id} link.

— Reg Guard referral kit. Planning aid. Not a quote or an AHJ filing.

"""

MANDATE_SMS = """Hi {partner_name} — bid-week ask: when a site number arrives, say \"attach the Reg Guard HOLD receipt or I won't review.\" Forward one real receipt. DFW–Austin diligence. Not a quote. {app_url}
"""

MANDATE_DAY0 = """Day-0 (before bid): attach the Reg Guard Bid Risk Receipt. No HOLD stamp, no attach.
"""

MANDATE_DAY7 = """Day-7: if the stamp is outdated, re-run for a fresh HOLD / CAUTION / CLEAR before LOI.
"""


def kit() -> Dict[str, Any]:
    return {
        "schema": "regguard.partner_mandate.v1",
        "one_liner": MANDATE_ONE_LINER,
        "script": MANDATE_SCRIPT.strip(),
        "templates": {
            "email": MANDATE_EMAIL.strip(),
            "sms": MANDATE_SMS.strip(),
        },
        "day0": MANDATE_DAY0.strip(),
        "day7": MANDATE_DAY7.strip(),
        "talking_points": [
            "Borrow their authority: estimators listen to permit runners / GCs, not ads.",
            "One real receipt forward beats a demo — use a live beachhead address.",
            "Stamp is a checklist item like insurance certs — not a Moody's rating.",
            "If Twilio/SMS is live: zip-watch texts when stamp goes stale; still confirm via email.",
            "Start with DFW–Austin commercial–industrial and DC-adjacent sites. Do not claim nationwide coverage.",
        ],
        "success_signal": (
            "They use stamp language in their own threads without you prompting."
        ),
        "disclaimer": (
            "Planning aid for pre-bid diligence. Not a bond, insurance quote, legal opinion, "
            "or interconnection study."
        ),
        "urls": {
            "product": "https://app.regguardagent.com/",
            "evidence": "https://app.regguardagent.com/a2p-evidence",
            "mandate": "https://app.regguardagent.com/partner/mandate",
        },
    }


def log_outreach(
    *,
    partner_name: str,
    partner_email: str = "",
    partner_phone: str = "",
    metro: str = "",
    note: str = "",
    receipt_research_id: str = "",
    logged_by: str = "",
) -> Dict[str, Any]:
    name = (partner_name or "").strip()[:120]
    if not name:
        raise ValueError("partner_name required")
    row = {
        "id": f"pm-{uuid.uuid4().hex[:10]}",
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "partner_name": name,
        "partner_email": (partner_email or "").strip().lower()[:120],
        "partner_phone": (partner_phone or "").strip()[:40],
        "metro": (metro or "").strip()[:80],
        "note": (note or "").strip()[:500],
        "receipt_research_id": (receipt_research_id or "").strip()[:80],
        "logged_by": (logged_by or "").strip()[:120],
        "status": "outreach_logged",
    }
    with _LOCK:
        _PATH.parent.mkdir(parents=True, exist_ok=True)
        with _PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def recent(limit: int = 50) -> List[Dict[str, Any]]:
    if not _PATH.is_file():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        for line in _PATH.read_text(encoding="utf-8").splitlines()[-500:]:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    except Exception:
        return []
    return list(reversed(rows[-limit:]))
