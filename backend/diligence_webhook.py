"""Signed diligence webhook delivery for CRM / GIS / Airtable design partners."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

_BACKEND = Path(__file__).resolve().parent
_PATH = _BACKEND / "data" / "diligence_webhooks.json"
_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load() -> Dict[str, Any]:
    if not _PATH.is_file():
        return {"hooks": []}
    try:
        return json.loads(_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"hooks": []}


def _save(data: Dict[str, Any]) -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    _PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def signing_secret() -> str:
    return (os.getenv("DILIGENCE_WEBHOOK_SECRET") or os.getenv("ADMIN_SECRET") or "").strip()


def register_webhook(
    *,
    url: str,
    label: str = "",
    events: Optional[List[str]] = None,
) -> Dict[str, Any]:
    target = (url or "").strip()
    if not target.startswith("https://") and not target.startswith("http://127."):
        raise ValueError("webhook url must be https (or http://127. for local)")
    hook = {
        "id": f"wh-{uuid.uuid4().hex[:10]}",
        "url": target[:500],
        "label": (label or "")[:80],
        "events": events or ["diligence.export"],
        "created_at": _now(),
        "active": True,
    }
    with _LOCK:
        data = _load()
        hooks = list(data.get("hooks") or [])
        hooks.append(hook)
        data["hooks"] = hooks[-50:]
        _save(data)
    return hook


def list_webhooks() -> List[Dict[str, Any]]:
    return list(_load().get("hooks") or [])


def sign_body(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def deliver_payload(
    payload: Dict[str, Any],
    *,
    hook_id: Optional[str] = None,
    url: Optional[str] = None,
) -> Dict[str, Any]:
    secret = signing_secret()
    if not secret:
        raise ValueError("DILIGENCE_WEBHOOK_SECRET (or ADMIN_SECRET) not configured")

    targets: List[Dict[str, Any]] = []
    if url:
        targets.append({"id": "inline", "url": url})
    else:
        for h in list_webhooks():
            if not h.get("active"):
                continue
            if hook_id and h.get("id") != hook_id:
                continue
            targets.append(h)
    if not targets:
        raise ValueError("No webhook targets")

    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sig = sign_body(body, secret)
    headers = {
        "Content-Type": "application/json",
        "X-RegGuard-Signature": sig,
        "X-RegGuard-Event": "diligence.export",
        "User-Agent": "RegGuard-DiligenceWebhook/1.0",
    }
    results = []
    with httpx.Client(timeout=12.0) as client:
        for t in targets:
            try:
                resp = client.post(t["url"], content=body, headers=headers)
                results.append(
                    {
                        "hook_id": t.get("id"),
                        "url": t.get("url"),
                        "status_code": resp.status_code,
                        "ok": 200 <= resp.status_code < 300,
                    }
                )
            except Exception as e:
                logger.warning("webhook deliver failed %s: %s", t.get("url"), e)
                results.append(
                    {
                        "hook_id": t.get("id"),
                        "url": t.get("url"),
                        "ok": False,
                        "error": str(e)[:160],
                    }
                )
    return {"delivered_at": _now(), "results": results}
