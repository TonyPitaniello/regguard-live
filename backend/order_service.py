"""
Order persistence for Stripe tier checkouts (Contractor Pro, IC Project, etc.).

Uses an in-process store (always works) plus best-effort Supabase REST upsert
so orders survive across requests on the same Render instance and can persist
when the `orders` table is available.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# session_id -> order dict
_ORDERS_BY_SESSION: Dict[str, Dict[str, Any]] = {}
# email(lower) -> list of session_ids (newest first)
_ORDERS_BY_EMAIL: Dict[str, List[str]] = {}

# DB CHECK in 008_orders_table uses ic_consultant; app tiers use ic_project / ic_annual
_TIER_DB_MAP = {
    "partner": "partner",
    "contractor_pro": "contractor_pro",
    "ic_project": "ic_consultant",
    "ic_annual": "ic_consultant",
    "sponsor": "sponsor",
    "free": "free",
    "ic_consultant": "ic_consultant",
}

_TIER_AMOUNTS = {
    "partner": 7900,
    "contractor_pro": 14900,
    "ic_project": 150000,
    "ic_annual": 1500000,
    "sponsor": 150000,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def email_to_user_uuid(email: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, (email or "anonymous").strip().lower()))


def normalize_tier(tier: str) -> str:
    t = (tier or "").strip().lower()
    return t if t in _TIER_DB_MAP or t in _TIER_AMOUNTS else t


def db_tier(tier: str) -> str:
    return _TIER_DB_MAP.get(normalize_tier(tier), "contractor_pro")


def _supabase_rest(path: str, method: str = "GET", json_body: Any = None, prefer: str = "") -> Optional[Any]:
    url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    key = os.getenv("SUPABASE_KEY") or ""
    if not url or not key:
        return None
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    try:
        with httpx.Client(timeout=8.0) as client:
            full = f"{url}/rest/v1/{path}"
            if method == "GET":
                r = client.get(full, headers=headers)
            elif method == "POST":
                r = client.post(full, headers=headers, json=json_body)
            elif method == "PATCH":
                r = client.patch(full, headers=headers, json=json_body)
            else:
                return None
            if r.status_code >= 400:
                logger.warning("Supabase orders %s %s -> %s %s", method, path, r.status_code, r.text[:200])
                return None
            if not r.content:
                return []
            return r.json()
    except Exception as e:
        logger.warning("Supabase orders request failed: %s", e)
        return None


def _pdfs_for_tier(tier: str, order_id: str) -> List[Dict[str, Any]]:
    """Placeholder deliverable links until PDF generation is wired.

    Placeholders intentionally have empty urls — never point at a sample report
    (buyers must not mistake a template for their paid deliverable).
    """
    base = os.getenv("FRONTEND_APP_URL", "https://app.regguardagent.com").rstrip("/")
    if normalize_tier(tier) in ("ic_project", "ic_annual", "ic_consultant"):
        return [
            {
                "type": "research_memo",
                "name": "Research Memo (preparing)",
                "size": "—",
                "url": "",
                "icon": "📄",
                "status": "preparing",
            },
            {
                "type": "punch_list",
                "name": "Contractor Punch List (preparing)",
                "size": "—",
                "url": "",
                "icon": "✅",
                "status": "preparing",
            },
            {
                "type": "permits",
                "name": "Permit Package Worksheet (preparing)",
                "size": "—",
                "url": "",
                "icon": "📋",
                "status": "preparing",
            },
        ]
    return [
        {
            "type": "punch_list",
            "name": "Contractor Pro access — run unlimited lookups",
            "size": "—",
            "url": f"{base}/",
            "icon": "✅",
            "status": "ready",
        }
    ]


def order_to_frontend(order: Dict[str, Any]) -> Dict[str, Any]:
    tier = order.get("tier") or "contractor_pro"
    order_id = order.get("order_id") or order.get("id") or "unknown"
    created = order.get("created_at") or _now_iso()
    try:
        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
    except Exception:
        created_dt = datetime.now(timezone.utc)
    expires = order.get("expires_at") or (created_dt + timedelta(days=365)).isoformat().replace("+00:00", "Z")
    amount = order.get("amount")
    if amount is None:
        amount = _TIER_AMOUNTS.get(normalize_tier(tier), 0)
    # Frontend displays dollars in some places; keep cents as integer (OrdersPage uses amount)
    return {
        "order_id": order_id,
        "trial_id": order.get("trial_id") or "",
        "tier": tier,
        "status": order.get("status") or "completed",
        "created_at": created if isinstance(created, str) else _now_iso(),
        "amount": int(amount),
        "pdfs": order.get("pdfs") or _pdfs_for_tier(tier, str(order_id)),
        "expires_at": expires,
        "email": order.get("email") or "",
        "stripe_session_id": order.get("stripe_session_id") or "",
        "download_token": order.get("download_token") or "",
        "pdf_status": order.get("pdf_status")
        or ("ready" if order.get("analysis_json") else "preparing"),
        "coverage_note": order.get("coverage_note") or "",
    }


def remember_order(order: Dict[str, Any]) -> Dict[str, Any]:
    session_id = (order.get("stripe_session_id") or "").strip()
    email = (order.get("email") or "").strip().lower()
    if not session_id:
        session_id = f"local_{uuid.uuid4().hex[:12]}"
        order["stripe_session_id"] = session_id
    if not order.get("order_id"):
        order["order_id"] = str(uuid.uuid4())
    if not order.get("created_at"):
        order["created_at"] = _now_iso()
    if not order.get("download_token"):
        order["download_token"] = uuid.uuid4().hex
    order["status"] = order.get("status") or "completed"
    _ORDERS_BY_SESSION[session_id] = order
    if email:
        lst = _ORDERS_BY_EMAIL.setdefault(email, [])
        if session_id in lst:
            lst.remove(session_id)
        lst.insert(0, session_id)
    return order


def persist_order_supabase(order: Dict[str, Any]) -> bool:
    """Best-effort insert into public.orders. Returns True if accepted."""
    email = (order.get("email") or "").strip().lower()
    tier = normalize_tier(order.get("tier") or "contractor_pro")
    user_id = order.get("user_id") or email_to_user_uuid(email or "anonymous")
    row = {
        "user_id": user_id,
        "stripe_session_id": order.get("stripe_session_id"),
        "stripe_payment_intent_id": order.get("stripe_payment_intent_id"),
        "stripe_subscription_id": order.get("stripe_subscription_id"),
        "amount": int(order.get("amount") or _TIER_AMOUNTS.get(tier, 0)),
        "currency": order.get("currency") or "usd",
        "status": "completed",
        "tier": db_tier(tier),
        "email": email or None,
    }
    if order.get("pdfs") is not None:
        row["pdfs"] = order["pdfs"]
    if order.get("address"):
        row["address"] = order["address"]
    if order.get("download_token"):
        row["download_token"] = order["download_token"]
    if order.get("pdf_status"):
        row["pdf_status"] = order["pdf_status"]
    # Prefer upsert by session id when supported
    result = _supabase_rest(
        "orders?on_conflict=stripe_session_id",
        method="POST",
        json_body=row,
        prefer="resolution=merge-duplicates,return=representation",
    )
    if result is not None:
        return True
    # Plain insert fallback
    result = _supabase_rest("orders", method="POST", json_body=row, prefer="return=representation")
    return result is not None


def list_orders_for_email(email: str) -> List[Dict[str, Any]]:
    email_l = (email or "").strip().lower()
    # Defensive: strip accidental "?session_id=..." glued onto email from bad success URLs
    if "?" in email_l:
        email_l = email_l.split("?", 1)[0]
    out: List[Dict[str, Any]] = []
    seen = set()

    for sid in _ORDERS_BY_EMAIL.get(email_l, []):
        order = _ORDERS_BY_SESSION.get(sid)
        if order and sid not in seen:
            out.append(order_to_frontend(order))
            seen.add(sid)

    def _ingest_rows(rows: Any) -> None:
        if not isinstance(rows, list):
            return
        for row in rows:
            sid = row.get("stripe_session_id") or row.get("id")
            if not sid or sid in seen:
                continue
            tier = row.get("tier") or "contractor_pro"
            if str(tier).lower() == "ic_consultant":
                amt = int(row.get("amount") or 0)
                tier = "ic_annual" if amt >= 1_000_000 else "ic_project"
            mapped = {
                "order_id": row.get("id"),
                "tier": tier,
                "status": row.get("status"),
                "created_at": row.get("created_at"),
                "amount": row.get("amount"),
                "stripe_session_id": row.get("stripe_session_id"),
                "email": (row.get("email") or email_l).strip().lower(),
                "trial_id": "",
                "pdfs": row.get("pdfs"),
                "address": row.get("address"),
                "analysis_json": row.get("analysis_json"),
                "download_token": row.get("download_token"),
                "pdf_status": row.get("pdf_status"),
            }
            mem = _ORDERS_BY_SESSION.get(row.get("stripe_session_id") or "")
            if mem and mem.get("tier"):
                mapped["tier"] = mem["tier"]
            if mem and mem.get("pdfs"):
                mapped["pdfs"] = mem["pdfs"]
            if mem and mem.get("analysis_json"):
                mapped["analysis_json"] = mem["analysis_json"]
            if row.get("stripe_session_id"):
                remember_order({**mapped, "order_id": mapped["order_id"]})
            out.append(order_to_frontend(mapped))
            seen.add(sid)

    user_id = email_to_user_uuid(email_l) if email_l else None
    if user_id:
        _ingest_rows(
            _supabase_rest(
                f"orders?user_id=eq.{user_id}&order=created_at.desc&limit=50",
                method="GET",
            )
        )
    if email_l:
        from urllib.parse import quote

        _ingest_rows(
            _supabase_rest(
                f"orders?email=eq.{quote(email_l)}&order=created_at.desc&limit=50",
                method="GET",
            )
        )

    return out


def get_order_by_session(session_id: str) -> Optional[Dict[str, Any]]:
    sid = (session_id or "").strip()
    if not sid:
        return None
    order = _ORDERS_BY_SESSION.get(sid)
    if order:
        return order_to_frontend(order)
    rows = _supabase_rest(
        f"orders?stripe_session_id=eq.{sid}&limit=1",
        method="GET",
    )
    if isinstance(rows, list) and rows:
        row = rows[0]
        tier = row.get("tier") or "contractor_pro"
        if str(tier).lower() == "ic_consultant":
            amt = int(row.get("amount") or 0)
            tier = "ic_annual" if amt >= 1_000_000 else "ic_project"
        hydrated = {
            "order_id": row.get("id") or str(uuid.uuid4()),
            "tier": tier,
            "status": row.get("status") or "completed",
            "created_at": row.get("created_at"),
            "amount": row.get("amount"),
            "stripe_session_id": sid,
            "email": (row.get("email") or "").strip().lower(),
            "pdfs": row.get("pdfs"),
            "address": row.get("address"),
            "analysis_json": row.get("analysis_json"),
            "download_token": row.get("download_token"),
            "pdf_status": row.get("pdf_status"),
        }
        remember_order(hydrated)
        return order_to_frontend(hydrated)
    return None


def get_raw_order_by_id(order_id: str) -> Optional[Dict[str, Any]]:
    oid = (order_id or "").strip()
    if not oid:
        return None
    for order in _ORDERS_BY_SESSION.values():
        if str(order.get("order_id") or "") == oid or str(order.get("id") or "") == oid:
            return order
    # Best-effort hydrate from Supabase after process restart
    rows = _supabase_rest(f"orders?id=eq.{oid}&limit=1", method="GET")
    if isinstance(rows, list) and rows:
        row = rows[0]
        hydrated = {
            "order_id": row.get("id") or oid,
            "tier": row.get("tier"),
            "status": row.get("status"),
            "created_at": row.get("created_at"),
            "amount": row.get("amount"),
            "stripe_session_id": row.get("stripe_session_id") or f"db_{oid}",
            "email": (row.get("email") or "").strip().lower(),
            "pdfs": row.get("pdfs"),
            "address": row.get("address"),
            "analysis_json": row.get("analysis_json"),
            "download_token": row.get("download_token"),
            "pdf_status": row.get("pdf_status"),
        }
        remember_order(hydrated)
        return hydrated
    return None


def get_raw_orders_for_email(email: str) -> List[Dict[str, Any]]:
    """Raw in-memory orders for email, newest first."""
    email_l = (email or "").strip().lower()
    out: List[Dict[str, Any]] = []
    for sid in _ORDERS_BY_EMAIL.get(email_l, []):
        order = _ORDERS_BY_SESSION.get(sid)
        if order:
            out.append(order)
    return out


def update_order_artifacts(
    order_id: str,
    *,
    pdfs: Optional[List[Dict[str, Any]]] = None,
    analysis_json: Optional[Dict[str, Any]] = None,
    address: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Update in-memory order PDFs/analysis; best-effort Supabase PATCH."""
    order = get_raw_order_by_id(order_id)
    if not order:
        return None
    if pdfs is not None:
        order["pdfs"] = pdfs
        # Mark ready when real download URLs are present
        if any("/orders/" in str(p.get("url") or "") for p in pdfs):
            order["pdf_status"] = "ready"
    if analysis_json is not None:
        order["analysis_json"] = analysis_json
    if address is not None:
        order["address"] = address
    remember_order(order)
    _persist_order_artifacts_supabase(order)
    return order_to_frontend(order)


def _persist_order_artifacts_supabase(order: Dict[str, Any]) -> None:
    sid = (order.get("stripe_session_id") or "").strip()
    oid = (order.get("order_id") or "").strip()
    patch: Dict[str, Any] = {}
    if order.get("pdfs") is not None:
        patch["pdfs"] = order["pdfs"]
    if order.get("analysis_json") is not None:
        # Keep payload bounded for REST
        patch["analysis_json"] = order["analysis_json"]
    if order.get("address"):
        patch["address"] = order["address"]
    if order.get("email"):
        patch["email"] = order["email"]
    if order.get("download_token"):
        patch["download_token"] = order["download_token"]
    if order.get("pdf_status"):
        patch["pdf_status"] = order["pdf_status"]
    if not patch:
        return
    if sid:
        _supabase_rest(
            f"orders?stripe_session_id=eq.{sid}",
            method="PATCH",
            json_body=patch,
            prefer="return=minimal",
        )
    elif oid:
        _supabase_rest(
            f"orders?id=eq.{oid}",
            method="PATCH",
            json_body=patch,
            prefer="return=minimal",
        )


async def fulfill_checkout_session(session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create/remember an order from a Stripe Checkout Session object (dict).
    Idempotent on stripe_session_id.
    """
    session_id = session.get("id") or ""
    if session_id and session_id in _ORDERS_BY_SESSION:
        return order_to_frontend(_ORDERS_BY_SESSION[session_id])

    metadata = session.get("metadata") or {}
    tier = normalize_tier(metadata.get("tier") or "")
    details = session.get("customer_details") if isinstance(session.get("customer_details"), dict) else {}
    email = (
        metadata.get("email")
        or details.get("email")
        or session.get("customer_email")
        or ""
    )
    if not email and isinstance(metadata.get("user_id"), str) and "@" in metadata["user_id"]:
        email = metadata["user_id"]
    email = (email or "").strip().lower()

    amount = session.get("amount_total")
    if amount is None:
        amount = _TIER_AMOUNTS.get(tier, 0)

    order = {
        "order_id": str(uuid.uuid4()),
        "trial_id": metadata.get("trial_id") or "",
        "tier": tier or "contractor_pro",
        "status": "completed",
        "created_at": _now_iso(),
        "amount": int(amount or 0),
        "currency": (session.get("currency") or "usd").lower(),
        "email": email,
        "user_id": email_to_user_uuid(email) if email else metadata.get("user_id"),
        "stripe_session_id": session_id,
        "stripe_payment_intent_id": session.get("payment_intent")
        if isinstance(session.get("payment_intent"), str)
        else None,
        "stripe_subscription_id": session.get("subscription")
        if isinstance(session.get("subscription"), str)
        else None,
        "name": metadata.get("name") or "",
        "download_token": uuid.uuid4().hex,
        "pdf_status": "preparing"
        if normalize_tier(tier) in ("ic_project", "ic_annual", "ic_consultant")
        else "n/a",
        "coverage_note": (
            "Strongest citeable coverage today: Dallas / Plano / Austin TX. "
            "Outside those AHJs, items may show as Unverified — confirm with the local AHJ."
            if normalize_tier(tier)
            in ("ic_project", "ic_annual", "ic_consultant", "contractor_pro", "partner")
            else ""
        ),
        "referral_code": (metadata.get("referral_code") or "").strip().lower(),
    }
    remember_order(order)
    persisted = persist_order_supabase(order)
    if not persisted:
        logger.warning(
            "Order %s fulfilled in-memory but Supabase persist failed — regenerate depends on this instance",
            order["order_id"],
        )
    logger.info(
        "✅ Fulfilled order %s tier=%s email=%s session=%s supabase=%s",
        order["order_id"],
        order["tier"],
        email or "(none)",
        session_id,
        persisted,
    )

    # Affiliate attribution (non-blocking)
    ref = order.get("referral_code") or ""
    if ref:
        try:
            from affiliate_store import attribute_sale

            attribute_sale(
                referral_code=ref,
                order_id=order["order_id"],
                customer_email=email,
                amount_cents=int(order.get("amount") or 0),
                tier=order.get("tier") or "",
            )
        except Exception as aff_err:
            logger.warning("Affiliate attribution failed: %s", aff_err)

    # IC: email next-step so buyers don't stall on "preparing"
    if email and normalize_tier(order["tier"]) in ("ic_project", "ic_annual", "ic_consultant"):
        try:
            from email_service import get_email_service

            svc = get_email_service()
            if svc and hasattr(svc, "send_ic_next_step"):
                await svc.send_ic_next_step(
                    email,
                    order["order_id"],
                    order["download_token"],
                )
        except Exception as e:
            logger.warning("IC next-step email failed: %s", e)

    # Partner / Pro: welcome win email + schedule Day-7 habit nudge
    tier_n = normalize_tier(order["tier"])
    if email and tier_n in ("partner", "contractor_pro"):
        try:
            from email_service import get_email_service
            from nurture_store import schedule_day7_win

            svc = get_email_service()
            if svc and hasattr(svc, "send_plan_win_email"):
                await svc.send_plan_win_email(email, tier_n, day7=False)
            schedule_day7_win(
                email=email,
                tier=tier_n,
                order_id=order["order_id"],
                days=7,
            )
        except Exception as e:
            logger.warning("Plan win / day7 schedule failed: %s", e)

    return order_to_frontend(order)


async def confirm_stripe_session(session_id: str) -> Dict[str, Any]:
    """Retrieve session from Stripe and fulfill if paid/complete."""
    import stripe

    existing = get_order_by_session(session_id)
    if existing:
        return {"status": "ok", "order": existing, "email": existing.get("email") or ""}

    key = os.getenv("STRIPE_SECRET_KEY")
    if not key:
        raise ValueError("Stripe is not configured")
    stripe.api_key = key
    session = stripe.checkout.Session.retrieve(session_id)
    session_dict = session.to_dict() if hasattr(session, "to_dict") else dict(session)

    payment_status = session_dict.get("payment_status")
    status = session_dict.get("status")
    if payment_status not in ("paid", "no_payment_required") and status != "complete":
        raise ValueError(f"Checkout session not complete (payment_status={payment_status})")

    order = await fulfill_checkout_session(session_dict)
    return {"status": "ok", "order": order, "email": order.get("email") or ""}
