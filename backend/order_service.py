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
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# session_id -> order dict
_ORDERS_BY_SESSION: Dict[str, Dict[str, Any]] = {}
# email(lower) -> list of session_ids (newest first)
_ORDERS_BY_EMAIL: Dict[str, List[str]] = {}
# email -> unix time of last Stripe recovery pass (throttle listing polls)
_STRIPE_RECOVERY_AT: Dict[str, float] = {}
_STRIPE_RECOVERY_GAP_SEC = 45.0

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

# Status values the orders table accepts include completed, failed, and refunded.
# A canceled subscription is failed plus an ended: subscription id so a later
# paid invoice cannot turn it back on. A denied renewal is failed with the
# subscription id left in place so a successful retry can restore it.
ACCESS_STATUSES = {"completed", "active", "paid", ""}
ENDED_STATUSES = {"failed", "refunded", "canceled", "cancelled", "past_due", "unpaid"}
SUBSCRIPTION_TIERS = {"partner", "contractor_pro", "ic_annual", "sponsor"}


def order_grants_access(order: Optional[Dict[str, Any]]) -> bool:
    """True when this order is still a paid seat. Ended, failed, and refunded are not."""
    if not isinstance(order, dict):
        return False
    status = str(order.get("status") or "").strip().lower()
    return status in ACCESS_STATUSES


def billing_state_for(order: Optional[Dict[str, Any]]) -> str:
    """UI state. status stays inside the orders-table check constraint."""
    if not isinstance(order, dict):
        return "pending"
    status = str(order.get("status") or "completed").strip().lower()
    sub = str(order.get("stripe_subscription_id") or "")
    if status == "refunded":
        return "refunded"
    if status == "failed" and sub.startswith("ended:"):
        return "canceled"
    if status == "failed" or status == "past_due":
        return "past_due"
    if status in ("canceled", "cancelled"):
        return "canceled"
    if status in ACCESS_STATUSES:
        return "active"
    return "pending"


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
                logger.warning(
                    "Supabase orders %s %s -> %s %s",
                    method,
                    path,
                    r.status_code,
                    r.text[:400],
                )
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
            "name": "Contractor Pro — City Pack, fee CSV, and bid packet",
            "size": "—",
            "url": f"{base}/",
            "icon": "✅",
            "status": "ready",
        }
    ]


def order_to_frontend(order: Dict[str, Any]) -> Dict[str, Any]:
    from ic_project_fulfillment import rewrite_pdf_url_for_client

    tier = order.get("tier") or "contractor_pro"
    order_id = order.get("order_id") or order.get("id") or "unknown"
    created = order.get("created_at") or _now_iso()
    try:
        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
    except Exception:
        created_dt = datetime.now(timezone.utc)
    tier_n = normalize_tier(str(tier))
    # Monthly plans bill again next month. A 365-day "access expires" date
    # made a $79 subscription look like a year of access.
    if tier_n in ("partner", "contractor_pro"):
        period_days = 31
    elif tier_n == "ic_annual":
        period_days = 365
    else:
        period_days = 365
    expires = order.get("expires_at") or (
        created_dt + timedelta(days=period_days)
    ).isoformat().replace("+00:00", "Z")
    amount = order.get("amount")
    if amount is None:
        amount = _TIER_AMOUNTS.get(normalize_tier(tier), 0)
    raw_pdfs = order.get("pdfs") or _pdfs_for_tier(tier, str(order_id))
    pdfs: List[Dict[str, Any]] = []
    for pdf in raw_pdfs:
        if not isinstance(pdf, dict):
            continue
        row = dict(pdf)
        if row.get("url"):
            row["url"] = rewrite_pdf_url_for_client(str(row["url"]))
        pdfs.append(row)
    # Frontend displays dollars in some places; keep cents as integer (OrdersPage uses amount)
    return {
        "order_id": order_id,
        "trial_id": order.get("trial_id") or "",
        "tier": tier,
        "status": order.get("status") or "completed",
        "created_at": created if isinstance(created, str) else _now_iso(),
        "amount": int(amount),
        "pdfs": pdfs,
        "expires_at": expires,
        "email": order.get("email") or "",
        "stripe_session_id": order.get("stripe_session_id") or "",
        "download_token": order.get("download_token") or "",
        "pdf_status": order.get("pdf_status")
        or ("ready" if order.get("analysis_json") else "preparing"),
        "coverage_note": order.get("coverage_note") or "",
        "address": order.get("address") or order.get("site_label") or "",
        "site_address": order.get("site_address") or "",
        "site_city": order.get("site_city") or "",
        "site_state": order.get("site_state") or "",
        "site_zip": order.get("site_zip") or "",
        "site_project_type": order.get("site_project_type") or "",
        "site_label": order.get("site_label")
        or order.get("address")
        or "",
        "research_id": order.get("research_id") or "",
        "share_url": order.get("share_url") or "",
        "billing_state": billing_state_for(order),
    }


def _apply_saved_site(mapped: Dict[str, Any], row: Optional[Dict[str, Any]] = None) -> None:
    """Copy the address stored on this order. A previous research blob is not the site."""
    src = row or {}
    for key in ("site_address", "site_city", "site_state", "site_zip", "site_label"):
        if src.get(key) and not mapped.get(key):
            mapped[key] = src.get(key)


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


def _orders_archive_path() -> Path:
    root = Path(os.getenv("REGGUARD_DATA_DIR") or "/tmp/regguard_data")
    return root / "orders_archive.json"


def _mirror_order_disk(order: Dict[str, Any]) -> None:
    """Local mirror so a warm instance can reload after a soft restart."""
    sid = str(order.get("stripe_session_id") or "").strip()
    if not sid or sid.startswith(("share_", "local_")):
        return
    try:
        path = _orders_archive_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        blob: Dict[str, Any] = {}
        if path.is_file():
            try:
                blob = __import__("json").loads(path.read_text(encoding="utf-8") or "{}")
            except Exception:
                blob = {}
        if not isinstance(blob, dict):
            blob = {}
        slim = {
            k: order.get(k)
            for k in (
                "order_id",
                "tier",
                "status",
                "created_at",
                "amount",
                "currency",
                "email",
                "stripe_session_id",
                "stripe_payment_intent_id",
                "stripe_subscription_id",
                "download_token",
                "pdf_status",
                "address",
                "site_address",
                "site_city",
                "site_state",
                "site_zip",
                "site_label",
                "site_project_type",
                "user_id",
                "name",
                "referral_code",
                "coverage_note",
            )
            if order.get(k) not in (None, "")
        }
        blob[sid] = slim
        tmp = path.with_suffix(".tmp")
        tmp.write_text(__import__("json").dumps(blob, default=str), encoding="utf-8")
        tmp.replace(path)
    except Exception as e:
        logger.warning("Order disk mirror failed: %s", e)


def _load_orders_archive() -> None:
    """Hydrate memory from the local archive (best-effort)."""
    try:
        path = _orders_archive_path()
        if not path.is_file():
            return
        blob = __import__("json").loads(path.read_text(encoding="utf-8") or "{}")
        if not isinstance(blob, dict):
            return
        for sid, row in blob.items():
            if not isinstance(row, dict):
                continue
            if sid in _ORDERS_BY_SESSION:
                continue
            remember_order({**row, "stripe_session_id": sid})
    except Exception as e:
        logger.warning("Order archive load failed: %s", e)


def _app_tier_from_db_row(tier: Any, amount: Any) -> str:
    """Map a database tier (+ amount) back to the app tier name."""
    t = str(tier or "contractor_pro").strip().lower()
    amt = int(amount or 0)
    if t == "ic_consultant":
        return "ic_annual" if amt >= 1_000_000 else "ic_project"
    # Compatibility: older DBs rejected `partner` — those rows landed as contractor_pro @ $79.
    if t == "contractor_pro" and amt == _TIER_AMOUNTS["partner"]:
        return "partner"
    return t or "contractor_pro"


def _persist_core_row(order: Dict[str, Any], *, tier_for_db: str) -> Dict[str, Any]:
    email = (order.get("email") or "").strip().lower()
    tier = normalize_tier(order.get("tier") or "contractor_pro")
    status = str(order.get("status") or "completed").strip().lower()
    if status not in ("pending", "completed", "failed", "refunded"):
        status = "completed"
    user_id = order.get("user_id") or email_to_user_uuid(email or "anonymous")
    row: Dict[str, Any] = {
        "user_id": user_id,
        "stripe_session_id": order.get("stripe_session_id"),
        "amount": int(order.get("amount") or _TIER_AMOUNTS.get(tier, 0)),
        "currency": order.get("currency") or "usd",
        "status": status,
        "tier": tier_for_db,
        "email": email or None,
    }
    for key in ("stripe_payment_intent_id", "stripe_subscription_id"):
        val = order.get(key)
        if val:
            row[key] = val
    return row


def persist_order_supabase(order: Dict[str, Any]) -> bool:
    """Insert or update public.orders. Returns True if Supabase accepted the row."""
    sid = str(order.get("stripe_session_id") or "").strip()
    if not sid or sid.startswith(("share_", "disk_", "local_")):
        return False
    _mirror_order_disk(order)

    tier = normalize_tier(order.get("tier") or "contractor_pro")
    tier_candidates = [db_tier(tier)]
    # Older live DBs may still reject `partner` until migration 015 is applied.
    if tier == "partner" and "contractor_pro" not in tier_candidates:
        tier_candidates.append("contractor_pro")

    from urllib.parse import quote

    existing = _supabase_rest(
        f"orders?stripe_session_id=eq.{quote(sid, safe='')}&limit=1",
        method="GET",
    )
    already = isinstance(existing, list) and bool(existing)

    extras: Dict[str, Any] = {}
    if order.get("pdfs") is not None:
        extras["pdfs"] = order["pdfs"]
    if order.get("address"):
        extras["address"] = order["address"]
    if order.get("download_token"):
        extras["download_token"] = order["download_token"]
    if order.get("pdf_status"):
        extras["pdf_status"] = order["pdf_status"]
    for key in ("site_address", "site_city", "site_state", "site_zip", "site_label"):
        if order.get(key):
            extras[key] = order[key]

    for tier_for_db in tier_candidates:
        core = _persist_core_row(order, tier_for_db=tier_for_db)
        path = f"orders?stripe_session_id=eq.{quote(sid, safe='')}"
        if already:
            patch_body = {**core, **extras}
            patch_body.pop("stripe_session_id", None)
            result = _supabase_rest(path, method="PATCH", json_body=patch_body, prefer="return=minimal")
            if result is not None:
                order["_supabase_persisted"] = True
                return True
            # Retry without optional columns (schema lag).
            result = _supabase_rest(path, method="PATCH", json_body=core, prefer="return=minimal")
            if result is not None:
                order["_supabase_persisted"] = True
                return True
            continue

        full = {**core, **extras}
        result = _supabase_rest("orders", method="POST", json_body=full, prefer="return=representation")
        if result is not None:
            order["_supabase_persisted"] = True
            return True
        result = _supabase_rest("orders", method="POST", json_body=core, prefer="return=representation")
        if result is not None:
            order["_supabase_persisted"] = True
            if extras:
                _supabase_rest(path, method="PATCH", json_body=extras, prefer="return=minimal")
            return True

    logger.warning(
        "Supabase persist failed for session=%s tier=%s email=%s",
        sid,
        tier,
        (order.get("email") or "")[:80],
    )
    return False


def recover_paid_checkouts_for_email(email: str) -> int:
    """
    Re-create any paid Stripe Checkout sessions that never landed in Supabase.
    Render free instances forget in-memory orders on every deploy; Stripe is the source of truth.
    """
    import time

    email_l = (email or "").strip().lower()
    if not email_l or "@" not in email_l:
        return 0
    now = time.time()
    last = _STRIPE_RECOVERY_AT.get(email_l, 0.0)
    if now - last < _STRIPE_RECOVERY_GAP_SEC:
        return 0
    _STRIPE_RECOVERY_AT[email_l] = now

    key = (os.getenv("STRIPE_SECRET_KEY") or "").strip()
    if not key:
        return 0
    try:
        import stripe
    except Exception:
        return 0

    stripe.api_key = key
    recovered = 0
    sessions: List[Dict[str, Any]] = []
    try:
        customers = stripe.Customer.list(email=email_l, limit=10)
        for cust in list(customers.data or [])[:10]:
            listed = stripe.checkout.Session.list(customer=cust.id, limit=25, status="complete")
            for sess in listed.data or []:
                sessions.append(sess.to_dict() if hasattr(sess, "to_dict") else dict(sess))
    except Exception as e:
        logger.warning("Stripe customer session list failed for %s: %s", email_l, e)

    # Also scan recent complete sessions for customer_email / metadata.email matches.
    # Caps the walk so listing My Orders stays cheap.
    try:
        recent = stripe.checkout.Session.list(limit=40, status="complete")
        for sess in recent.data or []:
            raw = sess.to_dict() if hasattr(sess, "to_dict") else dict(sess)
            details = raw.get("customer_details") if isinstance(raw.get("customer_details"), dict) else {}
            md = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
            sess_email = (
                (details.get("email") or raw.get("customer_email") or md.get("email") or "")
                .strip()
                .lower()
            )
            if sess_email == email_l:
                sessions.append(raw)
    except Exception as e:
        logger.warning("Stripe recent session scan failed: %s", e)

    seen_sids: set[str] = set()
    for raw in sessions:
        sid = str(raw.get("id") or "").strip()
        if not sid or sid in seen_sids:
            continue
        seen_sids.add(sid)
        if get_order_by_session(sid):
            # Ensure a memory-only hit is also written to Supabase.
            mem = _ORDERS_BY_SESSION.get(sid)
            if mem and not mem.get("_supabase_persisted"):
                if persist_order_supabase(mem):
                    recovered += 1
            continue
        md = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
        if not md.get("tier"):
            continue
        payment_status = raw.get("payment_status")
        if payment_status not in ("paid", "no_payment_required") and raw.get("status") != "complete":
            continue
        try:
            order = build_order_from_checkout_session(raw)
            remember_order(order)
            if persist_order_supabase(order):
                recovered += 1
            else:
                # Still keep it in memory for this instance.
                recovered += 1
            logger.info(
                "Recovered checkout %s tier=%s email=%s supabase=%s",
                sid,
                order.get("tier"),
                email_l,
                bool(order.get("_supabase_persisted")),
            )
        except Exception as e:
            logger.warning("Recover session %s failed: %s", sid, e)
    return recovered


def _merge_db_billing(mem: Dict[str, Any], row: Dict[str, Any]) -> None:
    """Copy Stripe ids onto an in-memory order. An ended database row wins."""
    db_sub = str(row.get("stripe_subscription_id") or "")
    mem_sub = str(mem.get("stripe_subscription_id") or "")
    if db_sub.startswith("ended:") or not mem_sub:
        if db_sub:
            mem["stripe_subscription_id"] = db_sub
    db_pi = str(row.get("stripe_payment_intent_id") or "")
    if db_pi and not mem.get("stripe_payment_intent_id"):
        mem["stripe_payment_intent_id"] = db_pi
    db_state = billing_state_for(
        {"status": row.get("status"), "stripe_subscription_id": db_sub}
    )
    mem_state = billing_state_for(mem)
    if db_state in ("canceled", "refunded") or (
        db_state == "past_due" and mem_state == "active"
    ):
        mem["status"] = "refunded" if db_state == "refunded" else "failed"
        if db_state == "canceled" and db_sub:
            mem["stripe_subscription_id"] = db_sub if db_sub.startswith("ended:") else f"ended:{db_sub}"


def _sync_listed_billing(sid: str, row: Dict[str, Any], out: List[Dict[str, Any]]) -> None:
    mem = _ORDERS_BY_SESSION.get(sid)
    if mem is not None:
        _merge_db_billing(mem, row)
        state = billing_state_for(mem)
        status = mem.get("status")
    else:
        state = billing_state_for(row)
        status = row.get("status")
    if state == "active":
        return
    for item in out:
        if item.get("stripe_session_id") == sid or item.get("order_id") == row.get("id"):
            item["status"] = status
            item["billing_state"] = state
            break


def set_order_billing(
    order: Dict[str, Any],
    *,
    status: str,
    stripe_subscription_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Update access status in memory and on the orders row."""
    order["status"] = status
    if stripe_subscription_id is not None:
        order["stripe_subscription_id"] = stripe_subscription_id
    remember_order(order)
    sid = str(order.get("stripe_session_id") or "").strip()
    if not sid or sid.startswith(("share_", "disk_", "local_")):
        return order
    from urllib.parse import quote

    path = f"orders?stripe_session_id=eq.{quote(sid, safe='')}"
    body: Dict[str, Any] = {"status": status}
    if stripe_subscription_id is not None:
        body["stripe_subscription_id"] = stripe_subscription_id
    result = _supabase_rest(path, method="PATCH", json_body=body, prefer="return=minimal")
    if result is None and stripe_subscription_id is not None:
        _supabase_rest(path, method="PATCH", json_body={"status": status}, prefer="return=minimal")
    return order


def _order_from_billing_row(row: Dict[str, Any]) -> Dict[str, Any]:
    tier = row.get("tier") or "contractor_pro"
    amount = row.get("amount")
    if amount is None:
        amount = row.get("amount_cents")
    if str(tier).lower() == "ic_consultant":
        amt = int(amount or 0)
        tier = "ic_annual" if amt >= 1_000_000 else "ic_project"
    return {
        "order_id": row.get("id") or row.get("order_id"),
        "tier": tier,
        "status": row.get("status") or "completed",
        "created_at": row.get("created_at"),
        "amount": amount,
        "stripe_session_id": row.get("stripe_session_id"),
        "stripe_subscription_id": row.get("stripe_subscription_id") or "",
        "stripe_payment_intent_id": row.get("stripe_payment_intent_id") or "",
        "email": (row.get("email") or "").strip().lower(),
        "address": row.get("address") or "",
        "download_token": row.get("download_token") or "",
        "pdf_status": row.get("pdf_status"),
    }


def find_orders_by_stripe_field(field: str, value: str) -> List[Dict[str, Any]]:
    """Orders whose Stripe subscription or payment intent matches."""
    if field not in ("stripe_subscription_id", "stripe_payment_intent_id"):
        return []
    value = (value or "").strip()
    if not value:
        return []
    found: Dict[str, Dict[str, Any]] = {}
    for order in list(_ORDERS_BY_SESSION.values()):
        if str(order.get(field) or "") == value:
            key = str(order.get("stripe_session_id") or order.get("order_id") or "")
            if key:
                found[key] = order
    from urllib.parse import quote

    rows = _supabase_rest(
        f"orders?{field}=eq.{quote(value, safe='')}&limit=20",
        method="GET",
    )
    if isinstance(rows, list):
        for row in rows:
            sid = str(row.get("stripe_session_id") or "")
            if sid.startswith("share_"):
                continue
            if sid and sid in found:
                _merge_db_billing(found[sid], row)
                continue
            hydrated = _order_from_billing_row(row)
            if sid:
                remember_order(hydrated)
                found[sid] = _ORDERS_BY_SESSION.get(sid, hydrated)
            else:
                found[str(row.get("id") or id(row))] = hydrated
    return list(found.values())


def list_orders_for_email(email: str) -> List[Dict[str, Any]]:
    email_l = (email or "").strip().lower()
    # Defensive: strip accidental "?session_id=..." glued onto email from bad success URLs
    if "?" in email_l:
        email_l = email_l.split("?", 1)[0]
    _load_orders_archive()
    if email_l:
        try:
            recover_paid_checkouts_for_email(email_l)
        except Exception as e:
            logger.warning("Stripe order recovery failed for %s: %s", email_l, e)

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
            if not sid:
                continue
            if str(row.get("stripe_session_id") or "").startswith("share_"):
                continue
            if sid in seen:
                _sync_listed_billing(str(row.get("stripe_session_id") or sid), row, out)
                continue
            tier = _app_tier_from_db_row(row.get("tier"), row.get("amount"))
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
                "stripe_subscription_id": row.get("stripe_subscription_id") or "",
                "stripe_payment_intent_id": row.get("stripe_payment_intent_id") or "",
            }
            mem = _ORDERS_BY_SESSION.get(row.get("stripe_session_id") or "")
            if mem and mem.get("tier"):
                mapped["tier"] = mem["tier"]
            if mem and billing_state_for(mem) in ("canceled", "refunded", "past_due"):
                if billing_state_for(mapped) == "active":
                    mapped["status"] = mem.get("status")
                    mapped["stripe_subscription_id"] = mem.get("stripe_subscription_id") or mapped.get(
                        "stripe_subscription_id"
                    )
            if mem and mem.get("pdfs"):
                mapped["pdfs"] = mem["pdfs"]
            if mem and mem.get("analysis_json"):
                mapped["analysis_json"] = mem["analysis_json"]
            _apply_saved_site(mapped, row)
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
    if not sid or sid.startswith("share_"):
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
        hydrated = {
            "order_id": row.get("id") or str(uuid.uuid4()),
            "tier": _app_tier_from_db_row(row.get("tier"), row.get("amount")),
            "status": row.get("status") or "completed",
            "created_at": row.get("created_at"),
            "amount": row.get("amount"),
            "stripe_session_id": sid,
            "stripe_subscription_id": row.get("stripe_subscription_id") or "",
            "stripe_payment_intent_id": row.get("stripe_payment_intent_id") or "",
            "email": (row.get("email") or "").strip().lower(),
            "pdfs": row.get("pdfs"),
            "address": row.get("address"),
            "analysis_json": row.get("analysis_json"),
            "download_token": row.get("download_token"),
            "pdf_status": row.get("pdf_status"),
            "_supabase_persisted": True,
        }
        _apply_saved_site(hydrated, row)
        remember_order(hydrated)
        return order_to_frontend(hydrated)
    return None


def _load_disk_analysis(order_id: str) -> Optional[Dict[str, Any]]:
    oid = (order_id or "").strip()
    if not oid:
        return None
    try:
        data_dir = os.getenv("REGGUARD_DATA_DIR") or "/tmp/regguard_data"
        path = Path(data_dir) / "order_analysis" / f"{oid}.json"
        if not path.is_file():
            return None
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def get_raw_order_by_id(order_id: str) -> Optional[Dict[str, Any]]:
    oid = (order_id or "").strip()
    if not oid:
        return None
    for order in _ORDERS_BY_SESSION.values():
        if str(order.get("order_id") or "") == oid or str(order.get("id") or "") == oid:
            if not order.get("analysis_json"):
                disk = _load_disk_analysis(oid)
                if disk:
                    order["analysis_json"] = disk
            return order
    # Best-effort hydrate from Supabase after process restart
    rows = _supabase_rest(f"orders?id=eq.{oid}&limit=1", method="GET")
    if isinstance(rows, list) and rows:
        row = rows[0]
        analysis = row.get("analysis_json")
        if not isinstance(analysis, dict):
            analysis = _load_disk_analysis(oid)
        hydrated = {
            "order_id": row.get("id") or oid,
            "tier": row.get("tier"),
            "status": row.get("status"),
            "created_at": row.get("created_at"),
            "amount": row.get("amount"),
            "stripe_session_id": row.get("stripe_session_id") or f"db_{oid}",
            "stripe_subscription_id": row.get("stripe_subscription_id") or "",
            "stripe_payment_intent_id": row.get("stripe_payment_intent_id") or "",
            "email": (row.get("email") or "").strip().lower(),
            "pdfs": row.get("pdfs"),
            "address": row.get("address"),
            "analysis_json": analysis,
            "download_token": row.get("download_token"),
            "pdf_status": row.get("pdf_status"),
            "share_url": row.get("share_url") or "",
            "research_id": row.get("research_id") or "",
        }
        _apply_saved_site(hydrated, row)
        remember_order(hydrated)
        return hydrated
    # Last resort: disk-only analysis after hard wipe
    disk = _load_disk_analysis(oid)
    if disk:
        hydrated = {
            "order_id": oid,
            "tier": "ic_project",
            "status": "completed",
            "stripe_session_id": f"disk_{oid}",
            "email": "",
            "pdfs": None,
            "analysis_json": disk,
            "pdf_status": "ready",
            "address": (disk.get("project_info") or {}).get("address") or "",
        }
        remember_order(hydrated)
        return hydrated
    return None


def get_raw_orders_for_email(email: str) -> List[Dict[str, Any]]:
    """
    Raw orders for email, newest first.

    Warm memory from Supabase first (same hydrate path as list_orders_for_email)
    so IC fulfillment survives Render restarts.
    """
    email_l = (email or "").strip().lower()
    if "?" in email_l:
        email_l = email_l.split("?", 1)[0]
    if email_l:
        try:
            list_orders_for_email(email_l)
        except Exception:
            pass
    out: List[Dict[str, Any]] = []
    seen = set()
    for sid in _ORDERS_BY_EMAIL.get(email_l, []):
        order = _ORDERS_BY_SESSION.get(sid)
        if order and sid not in seen:
            out.append(order)
            seen.add(sid)
    return out


def update_order_artifacts(
    order_id: str,
    *,
    pdfs: Optional[List[Dict[str, Any]]] = None,
    analysis_json: Optional[Dict[str, Any]] = None,
    address: Optional[str] = None,
    share_url: Optional[str] = None,
    research_id: Optional[str] = None,
    site_address: Optional[str] = None,
    site_city: Optional[str] = None,
    site_state: Optional[str] = None,
    site_zip: Optional[str] = None,
    site_label: Optional[str] = None,
    site_project_type: Optional[str] = None,
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
    if share_url:
        order["share_url"] = share_url
    if research_id:
        order["research_id"] = research_id
    if site_address is not None:
        order["site_address"] = site_address
    if site_city is not None:
        order["site_city"] = site_city
    if site_state is not None:
        order["site_state"] = site_state
    if site_zip is not None:
        order["site_zip"] = site_zip
    if site_label is not None:
        order["site_label"] = site_label
    if site_project_type is not None:
        order["site_project_type"] = site_project_type
    remember_order(order)
    _persist_order_artifacts_supabase(order)
    return order_to_frontend(order)


def _persist_order_artifacts_supabase(order: Dict[str, Any]) -> bool:
    """
    Persist PDF metadata + analysis to Supabase.
    Only patches columns that exist on orders (unknown columns abort the whole PATCH).
    Returns True on best-effort success.
    """
    sid = (order.get("stripe_session_id") or "").strip()
    oid = (order.get("order_id") or "").strip()

    # Core columns from migration 014 — always safe
    core: Dict[str, Any] = {}
    if order.get("pdfs") is not None:
        core["pdfs"] = order["pdfs"]
    if order.get("analysis_json") is not None:
        # Bound size: drop huge markdown blobs that can break REST payloads
        aj = order["analysis_json"]
        if isinstance(aj, dict):
            slim = dict(aj)
            for heavy in (
                "pro_summary_markdown",
                "research_memo",
                "raw_scout",
                "page_texts",
                "firecrawl_pages",
            ):
                if heavy in slim and isinstance(slim[heavy], str) and len(slim[heavy]) > 8000:
                    slim[heavy] = slim[heavy][:8000] + "…"
            core["analysis_json"] = slim
        else:
            core["analysis_json"] = aj
    if order.get("address"):
        core["address"] = order["address"]
    if order.get("email"):
        core["email"] = order["email"]
    if order.get("download_token"):
        core["download_token"] = order["download_token"]
    if order.get("pdf_status"):
        core["pdf_status"] = order["pdf_status"]

    # Optional columns from migration 015 — patch separately so missing cols don't kill core
    optional: Dict[str, Any] = {}
    if order.get("share_url"):
        optional["share_url"] = order["share_url"]
    if order.get("research_id"):
        optional["research_id"] = order["research_id"]

    if not core and not optional:
        return False

    def _patch(body: Dict[str, Any]) -> bool:
        if not body:
            return False
        if sid and not sid.startswith("db_"):
            result = _supabase_rest(
                f"orders?stripe_session_id=eq.{sid}",
                method="PATCH",
                json_body=body,
                prefer="return=minimal",
            )
            # _supabase_rest returns None on failure; [] or {} can mean ok with return=minimal
            return result is not None
        if oid:
            result = _supabase_rest(
                f"orders?id=eq.{oid}",
                method="PATCH",
                json_body=body,
                prefer="return=minimal",
            )
            return result is not None
        return False

    ok_core = True
    if core:
        ok_core = _patch(core)
        if not ok_core:
            logger.error(
                "Supabase order artifact PATCH failed order=%s sid=%s keys=%s",
                oid,
                sid[:20] if sid else "",
                list(core.keys()),
            )
        else:
            logger.info(
                "Supabase order artifacts saved order=%s pdf_status=%s pdfs=%s",
                oid,
                core.get("pdf_status"),
                len(core.get("pdfs") or []) if isinstance(core.get("pdfs"), list) else 0,
            )

    if optional:
        ok_opt = _patch(optional)
        if not ok_opt:
            logger.warning(
                "Supabase optional share/research PATCH failed order=%s "
                "(run migration 015_orders_share_research.sql if columns missing)",
                oid,
            )

    site_body: Dict[str, Any] = {}
    for key in ("site_address", "site_city", "site_state", "site_zip", "site_label"):
        if order.get(key):
            site_body[key] = order.get(key)
    if site_body and not _patch(site_body):
        logger.warning(
            "Supabase site-column PATCH failed order=%s (counsel ZIP remains on the address line)",
            oid,
        )

    # Also mirror analysis to disk so PDFs can regenerate after restart even if Supabase lags
    if isinstance(order.get("analysis_json"), dict) and oid:
        try:
            data_dir = os.getenv("REGGUARD_DATA_DIR") or "/tmp/regguard_data"
            path = Path(data_dir) / "order_analysis" / f"{oid}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                __import__("json").dumps(order["analysis_json"], default=str)[:2_000_000],
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("Disk analysis mirror failed order=%s: %s", oid, e)

    return ok_core


def build_order_from_checkout_session(session: Dict[str, Any]) -> Dict[str, Any]:
    """Build the in-memory order dict from a Stripe Checkout Session (no side effects)."""
    session_id = session.get("id") or ""
    metadata = session.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
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

    order: Dict[str, Any] = {
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
            "Strongest citeable coverage today: Dallas / Plano / Austin / Fort Worth. "
            "Outside those AHJs, items may show as Unverified — confirm with the local AHJ."
            if normalize_tier(tier)
            in ("ic_project", "ic_annual", "ic_consultant", "contractor_pro", "partner")
            else ""
        ),
        "referral_code": (metadata.get("referral_code") or "").strip().lower(),
    }

    site_address = (metadata.get("site_address") or "").strip()
    site_city = (metadata.get("site_city") or "").strip()
    site_state = (metadata.get("site_state") or "").strip()
    site_zip = (metadata.get("site_zip") or "").strip()
    site_project_type = (metadata.get("site_project_type") or "").strip()
    site_label = (metadata.get("site_label") or "").strip()
    if not site_label and site_address and site_city and site_state and site_zip:
        z = "".join(c for c in site_zip if c.isdigit())[:5]
        if z and z in site_address:
            site_label = site_address
        else:
            site_label = f"{site_address}, {site_city}, {site_state} {site_zip}"
    if site_address:
        order["site_address"] = site_address
    if site_city:
        order["site_city"] = site_city
    if site_state:
        order["site_state"] = site_state
    if site_zip:
        order["site_zip"] = site_zip
    if site_project_type:
        order["site_project_type"] = site_project_type
    if site_label:
        order["site_label"] = site_label
        order["address"] = site_label
    return order


async def fulfill_checkout_session(session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create/remember an order from a Stripe Checkout Session object (dict).
    Idempotent on stripe_session_id. Always retries Supabase persist.
    """
    session_id = session.get("id") or ""
    if session_id and session_id in _ORDERS_BY_SESSION:
        existing = _ORDERS_BY_SESSION[session_id]
        if not existing.get("_supabase_persisted"):
            persist_order_supabase(existing)
        return order_to_frontend(existing)

    # Already durable in Supabase (e.g. after a Render redeploy wiped memory).
    prior = get_order_by_session(session_id) if session_id else None
    if prior:
        mem = _ORDERS_BY_SESSION.get(session_id)
        if mem and not mem.get("_supabase_persisted"):
            mem["_supabase_persisted"] = True
        return prior

    order = build_order_from_checkout_session(session)
    email = (order.get("email") or "").strip().lower()

    remember_order(order)
    persisted = persist_order_supabase(order)
    if not persisted:
        logger.warning(
            "Order %s fulfilled in-memory but Supabase persist failed — will retry on My Orders / confirm",
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

    try:
        from product_events import track_event

        track_event(
            "checkout_complete",
            channel=str(order.get("tier") or "")[:40],
            meta={
                "tier": str(order.get("tier") or ""),
                "order_id": str(order.get("order_id") or "")[:40],
                "amount_cents": int(order.get("amount") or 0),
            },
        )
    except Exception:
        pass

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
            try:
                from nurture_store import cancel_free_run_for_email

                cancel_free_run_for_email(email)
            except Exception:
                pass
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

    def _site_payload(order: Dict[str, Any]) -> Dict[str, str]:
        return {
            "address": str(order.get("site_address") or ""),
            "city": str(order.get("site_city") or ""),
            "state": str(order.get("site_state") or ""),
            "zip": str(order.get("site_zip") or ""),
            "project_type": str(order.get("site_project_type") or ""),
            "label": str(order.get("site_label") or order.get("address") or ""),
        }

    existing = get_order_by_session(session_id)
    if existing:
        # Prefer live Stripe metadata if order was fulfilled before site binding existed
        site = _site_payload(existing)
        if not site.get("address"):
            try:
                key = os.getenv("STRIPE_SECRET_KEY")
                if key:
                    stripe.api_key = key
                    session = stripe.checkout.Session.retrieve(session_id)
                    session_dict = session.to_dict() if hasattr(session, "to_dict") else dict(session)
                    md = session_dict.get("metadata") or {}
                    site = {
                        "address": str(md.get("site_address") or ""),
                        "city": str(md.get("site_city") or ""),
                        "state": str(md.get("site_state") or ""),
                        "zip": str(md.get("site_zip") or ""),
                        "project_type": str(md.get("site_project_type") or ""),
                        "label": str(md.get("site_label") or ""),
                    }
            except Exception:
                pass
        return {
            "status": "ok",
            "order": existing,
            "email": existing.get("email") or "",
            "site": site,
        }

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
    return {
        "status": "ok",
        "order": order,
        "email": order.get("email") or "",
        "site": _site_payload(order),
    }
