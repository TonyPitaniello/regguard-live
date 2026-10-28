"""
Persistent store for forwardable research reports.

Priority:
1. Supabase table ``research_reports`` when SUPABASE_URL/KEY are set
2. A zero-dollar archive row on ``orders`` (survives a Render disk wipe)
3. Local JSON files under ``data/research_reports/``
4. A seed file shipped with the app for a receipt that must stay up
5. Process-local memory cache for hot reads

Public reports strip contact PII (email/phone) before return.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

_LOCK = threading.RLock()
_MEMORY: Dict[str, Dict[str, Any]] = {}
_DEFAULT_TTL_DAYS = int(os.getenv("REG_GUARD_REPORT_TTL_DAYS", "90"))

# Strip from public payloads
_PII_KEYS = {"email", "phone", "phone_number", "user_email", "user_phone", "contact_email"}


def _store_dir() -> Path:
    base = Path(os.getenv("REG_GUARD_REPORT_DIR") or (Path(__file__).resolve().parent / "data" / "research_reports"))
    base.mkdir(parents=True, exist_ok=True)
    return base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_research_id(research_id: Optional[str] = None) -> str:
    """Return a filesystem/URL-safe research id."""
    if research_id:
        cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "", research_id.strip())[:80]
        if cleaned:
            return cleaned
    return f"rg-{uuid.uuid4().hex[:16]}"


def app_base_url() -> str:
    return (os.getenv("REG_GUARD_APP_URL") or "https://app.regguardagent.com").rstrip("/")


def share_url_for(research_id: str) -> str:
    return f"{app_base_url()}/r/{research_id}"


def is_valid_forward_share_url(url: Optional[str]) -> bool:
    """True only for a real /r/{id} link — never bare homepage or utm landing."""
    u = (url or "").strip()
    if not u:
        return False
    low = u.lower()
    if "utm_source=bid_receipt" in low:
        return False
    if "/r/" not in low:
        return False
    if low.rstrip("/").endswith("/r"):
        return False
    # Must have something after /r/
    try:
        after = low.split("/r/", 1)[1]
    except IndexError:
        return False
    rid = after.split("?", 1)[0].split("#", 1)[0].strip("/")
    return bool(rid) and rid not in ("ephemeral",)


def resolve_forward_share_url(
    analysis: Optional[Dict[str, Any]] = None,
    *,
    share_url: Optional[str] = None,
    research_id: Optional[str] = None,
) -> str:
    """
    Canonical forwardable report URL for email + PDF CTAs.
    Never returns the marketing homepage (/ or /?utm...).
    """
    for candidate in (share_url, (analysis or {}).get("share_url")):
        if is_valid_forward_share_url(str(candidate or "")):
            return str(candidate).strip()

    rid = (research_id or (analysis or {}).get("research_id") or "").strip()
    if rid and not rid.startswith("ephemeral-") and rid.lower() not in ("preview", "unknown"):
        cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "", rid)[:80]
        if cleaned:
            return share_url_for(cleaned)
    return ""


def has_usable_coords(analysis: Optional[Dict[str, Any]]) -> bool:
    """True when project has real (non–Null Island) coordinates for GIS."""
    if not isinstance(analysis, dict):
        return False
    pi = analysis.get("project_info") or {}
    coords = pi.get("coordinates") if isinstance(pi.get("coordinates"), dict) else {}
    pairs = [
        (analysis.get("latitude"), analysis.get("longitude")),
        (analysis.get("lat"), analysis.get("lng")),
        (pi.get("latitude"), pi.get("longitude")),
        (pi.get("lat"), pi.get("lng")),
        (coords.get("latitude"), coords.get("longitude")),
        (coords.get("lat"), coords.get("lng")),
    ]
    for lat_raw, lng_raw in pairs:
        try:
            lat = float(lat_raw)
            lng = float(lng_raw)
        except (TypeError, ValueError):
            continue
        if abs(lat) < 1e-6 and abs(lng) < 1e-6:
            continue
        if -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0:
            return True
    return False


def is_instant_preview_payload(analysis: Optional[Dict[str, Any]]) -> bool:
    """True when results are still Instant Preview (not completed deep research)."""
    if not isinstance(analysis, dict):
        return True
    honesty = analysis.get("honesty") or {}
    src = str(honesty.get("source") or "").strip().lower()
    if src in ("instant", "preview", "delivery_summary"):
        return True
    # Paid timeout / fallback often stamps pro_partial + preview with no GIS pin
    if analysis.get("preview") and not has_usable_coords(analysis):
        return True
    return False


def stamp_depth_badge(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Honest depth badge for UI / share — never claim Pro when still instant."""
    if not isinstance(analysis, dict):
        return analysis
    depth = str(analysis.get("research_depth") or "").strip().lower()
    tier = str(analysis.get("depth_tier") or "").strip().lower()
    scout = str(analysis.get("scout_mode") or "").strip().lower()
    receipt_mode = str(analysis.get("receipt_mode") or "").strip().lower()
    access = str(analysis.get("access_tier") or "").strip().lower()
    instant = is_instant_preview_payload(analysis)
    coords_ok = has_usable_coords(analysis)
    # Habit ladder notes (Free vs Estimator) must survive badge stamping.
    habit_note = str(analysis.get("depth_claim_note") or "").strip()

    paid_ic = (
        tier == "ic_full"
        or depth in ("ic", "ic_full")
        or access in ("ic", "ic_project", "ic_consultant", "ic_annual", "sponsor")
        or analysis.get("ic_package") is True
    )
    paid_pro = access in ("contractor_pro", "pro") or (
        not instant
        and (
            depth in ("pro", "pro_partial", "pro_light", "pro_local")
            or depth.startswith("pro_")
            or tier in ("pro_light", "pro_partial", "pro_local", "pro")
            or scout in ("light", "full")
        )
    )

    # Estimator habit is a finished Free-pack product — never demote to Instant Preview.
    if (
        not paid_ic
        and not paid_pro
        and access not in ("contractor_pro", "ic", "ic_project", "sponsor")
        and (
            depth in ("partner", "estimator")
            or tier in ("partner", "estimator")
            or (receipt_mode == "estimator_habit" and access in ("", "partner", "free"))
        )
    ):
        label = "Estimator / Permit Runner — Receipt habit · unlocked punch"
        analysis["depth_claim_honest"] = True
        analysis["preview"] = False
        analysis["research_incomplete"] = False
        analysis["depth_tier"] = "partner"
        analysis["research_depth"] = "partner"
        analysis["receipt_mode"] = analysis.get("receipt_mode") or "estimator_habit"
    # Free Lookups is an intentional bid-or-walk preview — do not demote to Instant incomplete.
    elif (
        not paid_ic
        and not paid_pro
        and access in ("", "free")
        and (
            depth in ("free", "instant", "preview")
            or tier in ("free", "instant", "preview")
            or receipt_mode == "free_preview"
        )
    ):
        label = "Free Lookups — bid-or-walk preview"
        analysis["depth_claim_honest"] = True
        analysis["research_depth"] = "free"
        analysis["depth_tier"] = "free"
        analysis["receipt_mode"] = analysis.get("receipt_mode") or "free_preview"
    # Paid IC / Pro desk — keep ladder unlocks even when scout/geocode was partial.
    elif paid_ic:
        if str(analysis.get("scout_locality_depth") or "") == "local_ultralocal" or (
            isinstance(analysis.get("ultralocal_scout"), dict)
            and analysis.get("ultralocal_scout", {}).get("enabled")
        ):
            label = "IC Diligence Bundle — full federal / state / local + ultralocal scout"
        elif instant or not coords_ok:
            label = "IC Diligence Bundle — counsel package (scout partial — confirm pin)"
        else:
            label = "IC Diligence Bundle — full federal / state / local scout"
        analysis["depth_claim_honest"] = True
        analysis["preview"] = False
        analysis["research_incomplete"] = False
        analysis["depth_tier"] = analysis.get("depth_tier") or "ic_full"
        if depth not in ("ic", "ic_full"):
            analysis["research_depth"] = "ic"
        analysis["receipt_mode"] = analysis.get("receipt_mode") or "estimator_habit"
    elif paid_pro:
        if tier == "pro_light" or scout == "light":
            label = "Contractor Pro — local confirm + light scout"
        elif depth == "pro_partial" or tier == "pro_partial" or not coords_ok:
            label = "Contractor Pro — partial deep research"
        elif tier == "pro_local" or (depth == "pro" and scout in ("", "none")):
            label = "Contractor Pro — paid local confirm"
        else:
            label = "Contractor Pro — deep research"
        analysis["depth_claim_honest"] = True
        analysis["preview"] = False
        analysis["research_incomplete"] = False
        if not str(analysis.get("research_depth") or "").lower().startswith("pro"):
            analysis["research_depth"] = "pro_partial" if not coords_ok else "pro"
        analysis["receipt_mode"] = analysis.get("receipt_mode") or "estimator_habit"
    elif instant or (depth in ("pro", "pro_partial") and not coords_ok):
        label = "Instant preview — deep research incomplete (not full Pro)"
        # Keep entitlement unlock semantics, but surface honesty
        analysis["depth_claim_honest"] = False
    else:
        label = "Free Lookups — bid-or-walk preview"
        analysis["depth_claim_honest"] = True

    analysis["depth_badge"] = label
    if analysis.get("depth_claim_honest") is False:
        analysis["depth_claim_note"] = (
            "This run did not finish site-pinned deep research (missing map coordinates or still "
            "Instant Preview). Confirm the pin on the map and re-run before treating this as "
            "Contractor Pro / IC diligence you can forward to a GC."
        )
        analysis["research_incomplete"] = True
        # Soft-demote depth stamp so UIs don't unlock Pro-only chrome
        if str(analysis.get("honesty", {}).get("source") or "").lower() not in (
            "instant",
            "preview",
            "delivery_summary",
        ):
            honesty = dict(analysis.get("honesty") or {})
            honesty.setdefault("source", "instant")
            analysis["honesty"] = honesty
    else:
        analysis.pop("research_incomplete", None)
        if habit_note:
            analysis["depth_claim_note"] = habit_note
        elif not analysis.get("depth_claim_note"):
            analysis.pop("depth_claim_note", None)
    return analysis


def _strip_pii(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k.lower() in _PII_KEYS:
                continue
            out[k] = _strip_pii(v)
        return out
    if isinstance(obj, list):
        return [_strip_pii(x) for x in obj]
    return obj


def public_analysis(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Copy analysis safe for public share pages and emails forwarded to GCs."""
    return _strip_pii(deepcopy(analysis or {}))


def share_ladder_tier(analysis: Optional[Dict[str, Any]]) -> str:
    """What a forwarded link may reveal. More pay ⇒ more on the public page."""
    if not isinstance(analysis, dict):
        return "free"
    depth = str(analysis.get("research_depth") or "").strip().lower()
    mode = str(analysis.get("receipt_mode") or "").strip().lower()
    tier = str(analysis.get("depth_tier") or "").strip().lower()
    if depth in ("ic", "ic_full") or tier == "ic_full" or analysis.get("ic_package") is True:
        return "ic"
    if depth.startswith("pro") or tier.startswith("pro"):
        return "pro"
    if depth in ("partner", "estimator") or mode == "estimator_habit" or tier in ("partner", "estimator"):
        return "partner"
    return "free"


def _scrub_buyer_fail(text: Any) -> str:
    raw = str(text or "")
    return raw.replace("FAIL", "HOLD").replace("Fail", "Hold")


def redact_for_public_share(analysis: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Payload for /r/{id}, OG unfurls, and forwarded email.

    Free: HOLD + top risks only. Contingency % and fee dollars stay off the link
    (Estimator / Pro paid for those). Never print FAIL.
    """
    out = public_analysis(analysis or {})
    try:
        from depth_ladder import clear_foreign_site_bundle_copy

        out = clear_foreign_site_bundle_copy(out)
    except Exception:
        pass
    tier = share_ladder_tier(out)
    out["share_tier"] = tier
    _drop_receipt_debris(out)
    try:
        from real_environmental_screening import soften_buffer_only_high

        env = out.get("environmental_screening")
        if isinstance(env, dict):
            out["environmental_screening"] = soften_buffer_only_high(env)
    except Exception:
        pass

    rg = out.get("regguard_stamp")
    env_level = str((out.get("environmental_screening") or {}).get("risk_level") or "").upper()
    if isinstance(rg, dict) and env_level in ("HIGH", "CRITICAL"):
        grade_now = str(rg.get("grade") or out.get("stamp_grade") or "").upper()
        if grade_now in ("", "PASS", "CLEAR"):
            rg["grade"] = "CAUTION"
            rg["display_grade"] = "CAUTION"
            rg["headline"] = (
                "Parcel GIS risk is high at this pin — confirm the polygon before you treat the site as clear."
            )
            rg["label"] = "REGGUARD STAMP: CAUTION — review before bid"
            drivers = [d for d in (rg.get("drivers") or []) if isinstance(d, dict)]
            drivers.insert(
                0,
                {
                    "severity": "CAUTION",
                    "label": "Parcel GIS risk is high at this pin",
                    "detail": "A verified flood, wetlands, or habitat polygon hits the pin.",
                },
            )
            rg["drivers"] = drivers[:3]
            out["stamp_grade"] = "CAUTION"
            out["stamp_label"] = rg["label"]
    if isinstance(rg, dict):
        grade = str(rg.get("grade") or "").upper()
        if grade == "FAIL":
            rg["display_grade"] = "HOLD"
        elif grade == "PASS":
            rg["display_grade"] = "CLEAR"
        elif grade:
            rg["display_grade"] = grade
        for key in ("headline", "label", "plain"):
            if rg.get(key):
                rg[key] = _scrub_buyer_fail(rg.get(key))
        drivers = rg.get("drivers")
        if isinstance(drivers, list):
            for d in drivers:
                if isinstance(d, dict) and str(d.get("severity") or "").upper() == "FAIL":
                    d["severity"] = "HOLD"

    if str(out.get("stamp_grade") or "").upper() == "FAIL":
        out["stamp_grade"] = "HOLD"
    if out.get("stamp_label"):
        out["stamp_label"] = _scrub_buyer_fail(out.get("stamp_label"))

    band = out.get("contingency_band")
    if isinstance(band, dict) and tier == "free":
        band["share_frosted"] = True
        band["pct_low"] = None
        band["pct_mid"] = None
        band["pct_high"] = None

    if tier in ("free", "partner"):
        fee = out.get("fee_card")
        if isinstance(fee, dict) and isinstance(fee.get("fees"), list):
            stripped = []
            for row in fee["fees"]:
                if not isinstance(row, dict):
                    continue
                row = dict(row)
                label = str(row.get("label") or "")
                if _share_line_is_debris(label):
                    continue
                row.pop("amount_usd", None)
                row["amount_redacted"] = True
                stripped.append(row)
            # Free share stays thin — labels only, not a fee desk
            fee["fees"] = stripped[:3] if tier == "free" else stripped
            fee["amounts_redacted"] = True

    punch = out.get("punch_list")
    if isinstance(punch, dict) and isinstance(punch.get("punch_list"), list):
        kept_items = []
        for item in punch["punch_list"]:
            if not isinstance(item, dict):
                kept_items.append(item)
                continue
            task = str(item.get("task") or "")
            if _share_line_is_debris(task):
                continue
            kept_items.append(item)
        punch["punch_list"] = kept_items
        if tier == "free":
            punch["punch_list"] = punch["punch_list"][:5]
            punch["habit_unlocked"] = False
    return out


def _drop_receipt_debris(out: Dict[str, Any]) -> None:
    """Wrong-city scrapes and prompt lines never stay on a forwarded receipt."""
    try:
        from ic_ultralocal_scout import customer_line_blocked
    except Exception:
        return
    pi = out.get("project_info") if isinstance(out.get("project_info"), dict) else {}
    city = str(pi.get("city") or "")

    def _blocked(text: Any) -> bool:
        return customer_line_blocked(str(text or ""), city)

    killers = out.get("margin_killers")
    if isinstance(killers, list):
        out["margin_killers"] = [
            k
            for k in killers
            if isinstance(k, dict)
            and not _blocked(k.get("title"))
            and not _blocked(k.get("detail"))
        ]
    gotcha = out.get("gotcha_watchlist")
    if isinstance(gotcha, dict) and isinstance(gotcha.get("items"), list):
        gotcha["items"] = [
            g
            for g in gotcha["items"]
            if isinstance(g, dict)
            and not _blocked(g.get("title"))
            and not _blocked(g.get("detail"))
        ]
    punch = out.get("punch_list")
    if isinstance(punch, dict) and isinstance(punch.get("punch_list"), list):
        punch["punch_list"] = [
            item
            for item in punch["punch_list"]
            if not isinstance(item, dict) or not _blocked(item.get("task"))
        ]


def _share_line_is_debris(label: str) -> bool:
    """True when a line is PDF bytes, including a readable prefix glued to a stray $7."""
    raw = label or ""
    weird = sum(1 for c in raw if ord(c) > 126)
    if weird >= 3:
        return True
    if "$" not in raw:
        return False
    try:
        from cheap_page_confirm import _readable_fee_label

        return not _readable_fee_label(raw)
    except Exception:
        return False


def _file_path(research_id: str) -> Path:
    return _store_dir() / f"{research_id}.json"


def _supabase_available() -> bool:
    return bool((os.getenv("SUPABASE_URL") or "").strip() and (os.getenv("SUPABASE_KEY") or "").strip())


def _seed_analysis(research_id: str) -> Optional[Dict[str, Any]]:
    """A receipt shipped with the app. The deploy image keeps it when the disk is wiped."""
    path = Path(__file__).resolve().parent / "data" / "research_seeds" / f"{research_id}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Research seed read failed for %s: %s", research_id, e)
        return None
    if isinstance(data, dict) and isinstance(data.get("analysis"), dict):
        return data["analysis"]
    return data if isinstance(data, dict) else None


def _share_archive_session(research_id: str) -> str:
    return f"share_{research_id}"


def _durable_upsert(record: Dict[str, Any]) -> bool:
    """Copy the receipt onto the orders table, which survives a Render restart."""
    try:
        from urllib.parse import quote

        from order_service import _supabase_rest, email_to_user_uuid
    except Exception as e:
        logger.warning("Durable report store unavailable: %s", e)
        return False
    rid = str(record.get("id") or "")
    if not rid:
        return False
    archive_email = "share-archive@regguard.invalid"
    sid = _share_archive_session(rid)
    sid_q = quote(sid, safe="-_")
    address = str(record.get("project_address") or "")[:500]
    patch = {
        "analysis_json": record,
        "address": address,
        "email": archive_email,
        "pdf_status": "share",
    }
    existing = _supabase_rest(
        f"orders?stripe_session_id=eq.{sid_q}&select=id&limit=1",
        method="GET",
    )
    if isinstance(existing, list) and existing:
        result = _supabase_rest(
            f"orders?stripe_session_id=eq.{sid_q}",
            method="PATCH",
            json_body=patch,
            prefer="return=minimal",
        )
        return result is not None
    row = {
        "user_id": email_to_user_uuid(archive_email),
        "stripe_session_id": sid,
        "amount": 0,
        "currency": "usd",
        "status": "completed",
        "tier": "contractor_pro",
        "email": archive_email,
        "address": address,
        "project_type": "commercial",
        "analysis_json": record,
        "pdf_status": "share",
    }
    result = _supabase_rest("orders", method="POST", json_body=row, prefer="return=minimal")
    if result is None:
        logger.warning("Durable report copy failed for %s", rid)
        return False
    return True


def _durable_get(research_id: str) -> Optional[Dict[str, Any]]:
    try:
        from urllib.parse import quote

        from order_service import _supabase_rest
    except Exception:
        return None
    sid = quote(_share_archive_session(research_id), safe="-_")
    rows = _supabase_rest(
        f"orders?stripe_session_id=eq.{sid}&select=analysis_json&limit=1",
        method="GET",
    )
    if not isinstance(rows, list) or not rows:
        return None
    stored = rows[0].get("analysis_json") if isinstance(rows[0], dict) else None
    if isinstance(stored, dict) and isinstance(stored.get("analysis"), dict):
        stored.setdefault("share_url", share_url_for(research_id))
        return stored
    return None


def _supabase_upsert(record: Dict[str, Any]) -> bool:
    if not _supabase_available():
        return False
    try:
        from supabase import create_client

        sb = create_client(os.environ["SUPABASE_URL"].strip(), os.environ["SUPABASE_KEY"].strip())
        sb.table("research_reports").upsert(
            {
                "id": record["id"],
                "analysis": record["analysis"],
                "project_address": record.get("project_address"),
                "project_city": record.get("project_city"),
                "project_state": record.get("project_state"),
                "project_zip": record.get("project_zip"),
                "preview": bool(record.get("preview")),
                "created_at": record.get("created_at"),
                "expires_at": record.get("expires_at"),
                "updated_at": record.get("updated_at") or _iso(_utcnow()),
            }
        ).execute()
        return True
    except Exception as e:
        logger.warning(f"Supabase research_reports upsert failed (local store still used): {e}")
        return False


def _supabase_get(research_id: str) -> Optional[Dict[str, Any]]:
    if not _supabase_available():
        return None
    try:
        from supabase import create_client

        sb = create_client(os.environ["SUPABASE_URL"].strip(), os.environ["SUPABASE_KEY"].strip())
        resp = sb.table("research_reports").select("*").eq("id", research_id).limit(1).execute()
        rows = resp.data or []
        if not rows:
            return None
        row = rows[0]
        return {
            "id": row["id"],
            "analysis": row.get("analysis") or {},
            "project_address": row.get("project_address"),
            "project_city": row.get("project_city"),
            "project_state": row.get("project_state"),
            "project_zip": row.get("project_zip"),
            "preview": row.get("preview"),
            "created_at": row.get("created_at"),
            "expires_at": row.get("expires_at"),
            "share_url": share_url_for(row["id"]),
        }
    except Exception as e:
        logger.warning(f"Supabase research_reports get failed: {e}")
        return None


def save_research(
    analysis: Dict[str, Any],
    *,
    research_id: Optional[str] = None,
    ttl_days: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Persist analysis and return metadata including share_url.
    Always writes local file + memory; best-effort Supabase.
    """
    rid = normalize_research_id(research_id or analysis.get("research_id"))
    now = _utcnow()
    ttl = ttl_days if ttl_days is not None else _DEFAULT_TTL_DAYS
    expires = now + timedelta(days=max(1, ttl))

    try:
        from regguard_stamp import apply_regguard_stamp

        if not (analysis.get("regguard_stamp") or {}).get("grade"):
            analysis = apply_regguard_stamp(analysis)
        else:
            # Stable refresh: same fingerprint keeps grade; else rebuild
            analysis = apply_regguard_stamp(analysis)
    except Exception as e:
        logger.warning("RegGuard stamp on save failed: %s", e)

    # Auto zip-watch so stamp invalidation can page email/SMS (Twilio assumed live)
    try:
        from zip_watch import register_stamp_watch

        pi = analysis.get("project_info") or {}
        rg = analysis.get("regguard_stamp") or {}
        email = (
            str(analysis.get("owner_email") or analysis.get("generated_for") or "")
            .strip()
            .lower()
        )
        phone = str(analysis.get("owner_phone") or analysis.get("phone") or "").strip()
        register_stamp_watch(
            zip_code=str(pi.get("zip") or ""),
            city=str(pi.get("city") or ""),
            state=str(pi.get("state") or ""),
            email=email,
            phone=phone,
            research_id=rid,
            stamp_fingerprint=str(rg.get("fingerprint") or ""),
            stamp_grade=str(rg.get("grade") or ""),
        )
    except Exception as e:
        logger.warning("stamp zip-watch register failed: %s", e)

    # Funnel: same-ZIP re-run signal when research_id rotates for same ZIP
    try:
        from product_events import track_event

        pi = analysis.get("project_info") or {}
        rg = analysis.get("regguard_stamp") or {}
        track_event(
            "research_rerun_same_zip",
            research_id=rid,
            zip_code=str(pi.get("zip") or ""),
            stamp_grade=str(rg.get("grade") or ""),
            stamp_fingerprint=str(rg.get("fingerprint") or ""),
            meta={"source": "save_research"},
        )
    except Exception:
        pass

    clean = public_analysis(analysis)
    clean["research_id"] = rid

    project = clean.get("project_info") or {}
    record = {
        "id": rid,
        "analysis": clean,
        "project_address": project.get("address"),
        "project_city": project.get("city"),
        "project_state": project.get("state"),
        "project_zip": project.get("zip"),
        "preview": bool(clean.get("preview")),
        "created_at": _iso(now),
        "expires_at": _iso(expires),
        "updated_at": _iso(now),
        "share_url": share_url_for(rid),
    }

    with _LOCK:
        _MEMORY[rid] = record
        try:
            _file_path(rid).write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed writing local research report {rid}: {e}")

    _supabase_upsert(record)
    _durable_upsert(record)
    logger.info(f"Persisted research report {rid} → {record['share_url']}")
    return {
        "research_id": rid,
        "share_url": record["share_url"],
        "created_at": record["created_at"],
        "expires_at": record["expires_at"],
        "preview": record["preview"],
    }


def _expired(record: Dict[str, Any]) -> bool:
    expires = record.get("expires_at")
    if not expires:
        return False
    try:
        exp = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
        return _utcnow() > exp
    except Exception:
        return False


def get_research(research_id: str) -> Optional[Dict[str, Any]]:
    """Return stored record or None. Skips expired records."""
    rid = normalize_research_id(research_id)
    with _LOCK:
        mem = _MEMORY.get(rid)
        if mem and not _expired(mem):
            return deepcopy(mem)
        if mem and _expired(mem):
            _MEMORY.pop(rid, None)

    # Local file
    path = _file_path(rid)
    if path.exists():
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            if _expired(record):
                return None
            with _LOCK:
                _MEMORY[rid] = record
            return deepcopy(record)
        except Exception as e:
            logger.warning(f"Failed reading local report {rid}: {e}")

    remote = _supabase_get(rid)
    if remote:
        if _expired(remote):
            return None
        with _LOCK:
            _MEMORY[rid] = remote
        return deepcopy(remote)

    archived = _durable_get(rid)
    if archived:
        if _expired(archived):
            return None
        with _LOCK:
            _MEMORY[rid] = archived
        return deepcopy(archived)

    seed = _seed_analysis(rid)
    if seed:
        try:
            save_research(seed, research_id=rid)
        except Exception as e:
            logger.warning("Research seed restore failed for %s: %s", rid, e)
            return None
        with _LOCK:
            restored = _MEMORY.get(rid)
        return deepcopy(restored) if restored else None
    return None


def get_analysis(research_id: str) -> Optional[Dict[str, Any]]:
    record = get_research(research_id)
    if not record:
        return None
    analysis = record.get("analysis") or {}
    analysis["research_id"] = record.get("id") or research_id
    analysis["share_url"] = record.get("share_url") or share_url_for(research_id)
    return analysis


def extract_sources(analysis: Dict[str, Any]) -> list:
    """Collect citeable source URLs / labels from analysis payload."""
    sources = []
    seen = set()

    def add(label: str, url: str = ""):
        key = (label or "").strip().lower() + "|" + (url or "").strip().lower()
        if key in seen or (not label and not url):
            return
        seen.add(key)
        sources.append({"label": label or url, "url": url or ""})

    for url in analysis.get("source_urls") or []:
        if isinstance(url, str):
            add(url, url)
        elif isinstance(url, dict):
            add(url.get("title") or url.get("label") or url.get("url") or "", url.get("url") or "")

    env = analysis.get("environmental_screening") or {}
    for finding in env.get("findings") or []:
        if not isinstance(finding, dict):
            continue
        for src in finding.get("data_sources") or []:
            if isinstance(src, str):
                add(src, src if src.startswith("http") else "")
            elif isinstance(src, dict):
                add(src.get("label") or src.get("title") or "", src.get("url") or "")

    for item in (analysis.get("punch_list") or {}).get("punch_list") or []:
        if isinstance(item, dict) and item.get("source_url"):
            add(item.get("source_label") or item.get("task") or "Source", item.get("source_url"))

    return sources[:40]
