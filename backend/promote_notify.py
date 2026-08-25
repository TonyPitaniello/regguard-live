"""Notify ops when a draft pack becomes a promote candidate."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


def notify_promote_candidate(
    pack: Dict[str, Any],
    *,
    zip_code: str = "",
    research_id: str = "",
) -> Dict[str, Any]:
    """Best-effort Slack webhook and/or Resend email to OPS_NOTIFY_EMAIL."""
    if not isinstance(pack, dict) or not pack.get("promote_candidate"):
        return {"status": "skipped", "reason": "not_candidate"}

    z5 = zip_code or str(pack.get("zip") or "")
    city = pack.get("city") or ""
    state = pack.get("state") or ""
    portal = (pack.get("ahj") or {}).get("portal_url") or ""
    fees = len(pack.get("fees") or [])
    gotchas = len(pack.get("gotchas") or [])
    text = (
        f"Reg Guard promote candidate: {city}, {state} {z5}\n"
        f"tier={pack.get('tier')} fees={fees} gotchas={gotchas}\n"
        f"portal={portal}\n"
        f"research_id={research_id or 'n/a'}\n"
        f"Promote: POST /admin/local-packs/{z5}/promote"
    )

    out: Dict[str, Any] = {"slack": False, "email": False, "status": "logged"}

    slack_url = (os.getenv("OPS_SLACK_WEBHOOK_URL") or "").strip()
    if slack_url:
        try:
            import httpx

            r = httpx.post(slack_url, json={"text": text}, timeout=10.0)
            out["slack"] = r.status_code < 300
        except Exception as e:
            logger.warning("ops slack notify failed: %s", e)

    ops_email = (os.getenv("OPS_NOTIFY_EMAIL") or "").strip()
    resend_key = (os.getenv("RESEND_API_KEY") or "").strip()
    if ops_email and resend_key:
        try:
            import httpx

            from_addr = (
                os.getenv("RESEND_FROM_EMAIL") or "noreply@regguardagent.com"
            ).strip()
            r = httpx.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_key}"},
                json={
                    "from": from_addr,
                    "to": [ops_email],
                    "subject": f"Promote candidate {z5} — {city}, {state}",
                    "text": text,
                },
                timeout=15.0,
            )
            out["email"] = r.status_code < 300
        except Exception as e:
            logger.warning("ops email notify failed: %s", e)

    if out["slack"] or out["email"]:
        out["status"] = "ok"
    else:
        logger.info("promote candidate (no OPS webhook/email): %s", text.replace("\n", " | "))
    return out
