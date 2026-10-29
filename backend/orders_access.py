"""
Signed access to My Orders.

The payer is the email on the order. Anyone who types that email can see the
plan, but the IC access code and the download links only open with a key that
was sent to that inbox or handed back by a completed checkout.

Key format: <expires_unix>.<hmac>. Valid for 30 days. No database.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

KEY_TTL_SECONDS = 30 * 24 * 3600
_SEND_GAP_SECONDS = 60
_LAST_SENT: Dict[str, float] = {}
_LOCK = threading.Lock()


def _secret() -> bytes:
    for name in ("ORDERS_KEY_SECRET", "STRIPE_WEBHOOK_SECRET", "ADMIN_SECRET", "SUPABASE_KEY"):
        value = (os.getenv(name) or "").strip()
        if value:
            return hashlib.sha256(f"orders-access:{value}".encode("utf-8")).digest()
    return hashlib.sha256(b"orders-access:regguard-dev").digest()


def _normalize(email: str) -> str:
    return (email or "").strip().lower()


def _sign(email_l: str, expires: int) -> str:
    msg = f"{email_l}|{expires}".encode("utf-8")
    return hmac.new(_secret(), msg, hashlib.sha256).hexdigest()[:40]


def make_orders_key(email: str, ttl_seconds: int = KEY_TTL_SECONDS) -> str:
    email_l = _normalize(email)
    if "@" not in email_l:
        return ""
    expires = int(time.time()) + int(ttl_seconds)
    return f"{expires}.{_sign(email_l, expires)}"


def verify_orders_key(email: str, key: Optional[str]) -> bool:
    email_l = _normalize(email)
    raw = (key or "").strip()
    if "@" not in email_l or "." not in raw:
        return False
    exp_s, _, sig = raw.partition(".")
    try:
        expires = int(exp_s)
    except ValueError:
        return False
    if expires < int(time.time()):
        return False
    return hmac.compare_digest(_sign(email_l, expires), sig)


def orders_link(email: str, key: Optional[str] = None) -> str:
    email_l = _normalize(email)
    app_url = os.getenv("FRONTEND_APP_URL", "https://app.regguardagent.com").rstrip("/")
    k = key or make_orders_key(email_l)
    return f"{app_url}/orders?email={quote(email_l)}&key={quote(k, safe='.')}"


def _strip_token_from_url(url: str) -> str:
    if not url:
        return ""
    base, _, query = url.partition("?")
    if not query:
        return url
    kept = [part for part in query.split("&") if part and not part.startswith("token=")]
    return base + ("?" + "&".join(kept) if kept else "")


def lock_orders(orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Plan and status stay visible. Access codes and download links do not."""
    out: List[Dict[str, Any]] = []
    for order in orders:
        row = dict(order)
        row["download_token"] = ""
        pdfs = []
        for pdf in row.get("pdfs") or []:
            if not isinstance(pdf, dict):
                continue
            p = dict(pdf)
            p["url"] = _strip_token_from_url(str(p.get("url") or ""))
            p["locked"] = True
            pdfs.append(p)
        row["pdfs"] = pdfs
        row["locked"] = True
        out.append(row)
    return out


def _link_html(url: str) -> str:
    return f"""
<!DOCTYPE html>
<html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f5f5;padding:24px;">
  <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:8px;padding:28px;">
    <h1 style="margin:0 0 8px;color:#111;font-size:22px;">Your Reg Guard orders</h1>
    <p style="color:#555;font-size:14px;line-height:1.5;">
      This link opens My Orders on any device: your plan, IC access code, and downloads.
      It works for 30 days. Nobody else should have it.
    </p>
    <p style="margin:20px 0;">
      <a href="{url}" style="display:inline-block;background:#059669;color:#fff;padding:12px 20px;border-radius:6px;text-decoration:none;font-weight:600;">
        Open My Orders
      </a>
    </p>
    <p style="color:#888;font-size:12px;line-height:1.5;">
      If you did not ask for this, ignore it. Nothing changes until the link is opened.
    </p>
    <p style="margin-top:28px;font-size:12px;color:#888;">Reg Guard · support@regguardagent.com</p>
  </div>
</body></html>
"""


def _send_html(to_email: str, subject: str, html: str) -> bool:
    api_key = (os.getenv("RESEND_API_KEY") or "").strip()
    sender = os.getenv("RESEND_FROM_EMAIL", "noreply@regguardagent.com")
    if api_key:
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"from": sender, "to": [to_email], "subject": subject, "html": html},
                )
            if 200 <= r.status_code < 300:
                return True
            logger.warning("Orders link email rejected: %s %s", r.status_code, r.text[:200])
        except Exception as e:
            logger.warning("Orders link email failed: %s", e)
    try:
        from email_service import get_email_service

        svc = get_email_service()
        sg = getattr(svc, "sg", None)
        mail_cls = getattr(svc, "Mail", None)
        if sg and mail_cls:
            message = mail_cls(from_email=sender, to_emails=to_email, subject=subject, html_content=html)
            response = sg.send(message)
            return 200 <= response.status_code < 300
    except Exception as e:
        logger.warning("Orders link fallback email failed: %s", e)
    return False


def send_orders_link(email: str) -> Dict[str, Any]:
    """Email the signed My Orders link. Same reply whether or not the email has orders."""
    email_l = _normalize(email)
    if "@" not in email_l:
        return {"status": "sent"}
    now = time.time()
    with _LOCK:
        last = _LAST_SENT.get(email_l, 0.0)
        if now - last < _SEND_GAP_SECONDS:
            return {"status": "sent", "throttled": True}
        _LAST_SENT[email_l] = now
    try:
        from order_service import list_orders_for_email

        has_orders = bool(list_orders_for_email(email_l))
    except Exception as e:
        logger.warning("Orders lookup for link failed: %s", e)
        has_orders = False
    if not has_orders:
        logger.info("Orders link requested for an email with no orders")
        return {"status": "sent"}
    ok = _send_html(email_l, "Your Reg Guard orders link", _link_html(orders_link(email_l)))
    if not ok:
        logger.error("Orders link email did not send")
    return {"status": "sent"}
