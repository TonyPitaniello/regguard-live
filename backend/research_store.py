"""
Persistent store for forwardable research reports.

Priority:
1. Supabase table ``research_reports`` when SUPABASE_URL/KEY are set
2. Local JSON files under ``data/research_reports/`` (works on Render disk / local)
3. Process-local memory cache for hot reads

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
    pairs = [
        (analysis.get("latitude"), analysis.get("longitude")),
        (analysis.get("lat"), analysis.get("lng")),
        (pi.get("latitude"), pi.get("longitude")),
        (pi.get("lat"), pi.get("lng")),
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
    instant = is_instant_preview_payload(analysis)
    coords_ok = has_usable_coords(analysis)

    if tier == "ic_full" and not instant:
        label = "IC Project — full federal / state / local scout"
    elif instant or (depth in ("pro", "pro_partial") and not coords_ok):
        label = "Instant preview — deep research incomplete (not full Pro)"
        # Keep entitlement unlock semantics, but surface honesty
        analysis["depth_claim_honest"] = False
    elif tier == "pro_light" or scout == "light":
        label = "Contractor Pro — local confirm + light scout"
        analysis["depth_claim_honest"] = True
    elif depth == "pro_partial" or tier == "pro_partial":
        label = "Contractor Pro — partial deep research"
        analysis["depth_claim_honest"] = True
    elif tier == "pro_local" or (depth == "pro" and scout in ("", "none")):
        label = "Contractor Pro — paid local confirm"
        analysis["depth_claim_honest"] = True
    elif depth == "pro":
        label = "Contractor Pro — deep research"
        analysis["depth_claim_honest"] = True
    else:
        label = "Free preview"
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
        if not analysis.get("depth_claim_note"):
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


def _file_path(research_id: str) -> Path:
    return _store_dir() / f"{research_id}.json"


def _supabase_available() -> bool:
    return bool((os.getenv("SUPABASE_URL") or "").strip() and (os.getenv("SUPABASE_KEY") or "").strip())


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
