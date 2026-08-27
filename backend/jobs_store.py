"""
Saved Jobs store — weekly habit loop for contractors.

Identity (v1, matches Orders pattern):
- Primary: owner_email (from free trial)
- Secondary: owner_key (localStorage device id)

Storage: local JSON + optional Supabase ``saved_jobs`` table.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_LOCK = threading.RLock()
_MEMORY: Dict[str, Dict[str, Any]] = {}  # id -> job
_INDEX: Dict[str, List[str]] = {}  # email_lower -> [job ids]


def _store_dir() -> Path:
    base = Path(
        os.getenv("REG_GUARD_JOBS_DIR")
        or (Path(__file__).resolve().parent / "data" / "saved_jobs")
    )
    base.mkdir(parents=True, exist_ok=True)
    return base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime] = None) -> str:
    d = dt or _utcnow()
    return d.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _norm_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()


def _safe_id(raw: Optional[str] = None) -> str:
    if raw:
        cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "", raw.strip())[:64]
        if cleaned:
            return cleaned
    return f"job-{uuid.uuid4().hex[:12]}"


def _file_path(job_id: str) -> Path:
    return _store_dir() / f"{job_id}.json"


def _index_path() -> Path:
    return _store_dir() / "_email_index.json"


def _supabase_ok() -> bool:
    return bool((os.getenv("SUPABASE_URL") or "").strip() and (os.getenv("SUPABASE_KEY") or "").strip())


def _load_index() -> None:
    with _LOCK:
        if _INDEX:
            return
        path = _index_path()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, list):
                            _INDEX[k] = [str(x) for x in v]
            except Exception as e:
                logger.warning(f"Failed loading jobs index: {e}")


def _save_index() -> None:
    try:
        _index_path().write_text(json.dumps(_INDEX, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed writing jobs index: {e}")


def _index_add(email: str, job_id: str) -> None:
    _load_index()
    key = _norm_email(email)
    if not key:
        return
    with _LOCK:
        ids = _INDEX.setdefault(key, [])
        if job_id not in ids:
            ids.insert(0, job_id)
            _save_index()


def _index_remove(email: str, job_id: str) -> None:
    _load_index()
    key = _norm_email(email)
    with _LOCK:
        ids = _INDEX.get(key) or []
        if job_id in ids:
            _INDEX[key] = [i for i in ids if i != job_id]
            _save_index()


def _write_job(job: Dict[str, Any]) -> None:
    jid = job["id"]
    with _LOCK:
        _MEMORY[jid] = deepcopy(job)
        try:
            _file_path(jid).write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed writing job {jid}: {e}")
    _index_add(job.get("owner_email") or "", jid)
    _supabase_upsert(job)


def _read_job(job_id: str) -> Optional[Dict[str, Any]]:
    jid = _safe_id(job_id)
    with _LOCK:
        if jid in _MEMORY:
            return deepcopy(_MEMORY[jid])
    path = _file_path(jid)
    if path.exists():
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
            with _LOCK:
                _MEMORY[jid] = job
            return deepcopy(job)
        except Exception as e:
            logger.warning(f"Failed reading job {jid}: {e}")
    remote = _supabase_get(jid)
    if remote:
        with _LOCK:
            _MEMORY[jid] = remote
        return deepcopy(remote)
    return None


def _supabase_upsert(job: Dict[str, Any]) -> bool:
    if not _supabase_ok():
        return False
    try:
        from supabase import create_client

        sb = create_client(os.environ["SUPABASE_URL"].strip(), os.environ["SUPABASE_KEY"].strip())
        sb.table("saved_jobs").upsert(
            {
                "id": job["id"],
                "owner_email": job.get("owner_email"),
                "owner_key": job.get("owner_key"),
                "address": job.get("address"),
                "city": job.get("city"),
                "state": job.get("state"),
                "zip": job.get("zip"),
                "project_type": job.get("project_type"),
                "status": job.get("status") or "active",
                "last_research_id": job.get("last_research_id"),
                "share_url": job.get("share_url"),
                "last_run_at": job.get("last_run_at"),
                "summary_snapshot": job.get("summary_snapshot") or {},
                "notes": job.get("notes") or "",
                "created_at": job.get("created_at"),
                "updated_at": job.get("updated_at"),
            }
        ).execute()
        return True
    except Exception as e:
        logger.warning(f"Supabase saved_jobs upsert failed: {e}")
        return False


def _supabase_get(job_id: str) -> Optional[Dict[str, Any]]:
    if not _supabase_ok():
        return None
    try:
        from supabase import create_client

        sb = create_client(os.environ["SUPABASE_URL"].strip(), os.environ["SUPABASE_KEY"].strip())
        resp = sb.table("saved_jobs").select("*").eq("id", job_id).limit(1).execute()
        rows = resp.data or []
        return rows[0] if rows else None
    except Exception as e:
        logger.warning(f"Supabase saved_jobs get failed: {e}")
        return None


def _supabase_list(email: str) -> List[Dict[str, Any]]:
    if not _supabase_ok():
        return []
    try:
        from supabase import create_client

        sb = create_client(os.environ["SUPABASE_URL"].strip(), os.environ["SUPABASE_KEY"].strip())
        resp = (
            sb.table("saved_jobs")
            .select("*")
            .eq("owner_email", _norm_email(email))
            .order("updated_at", desc=True)
            .limit(100)
            .execute()
        )
        return list(resp.data or [])
    except Exception as e:
        logger.warning(f"Supabase saved_jobs list failed: {e}")
        return []


def _can_access(job: Dict[str, Any], email: Optional[str], owner_key: Optional[str]) -> bool:
    job_email = _norm_email(job.get("owner_email"))
    req_email = _norm_email(email)
    if job_email and req_email and job_email == req_email:
        return True
    job_key = (job.get("owner_key") or "").strip()
    req_key = (owner_key or "").strip()
    if job_key and req_key and job_key == req_key:
        return True
    return False


def upsert_job(
    *,
    owner_email: str,
    address: str,
    city: str = "",
    state: str = "",
    zip_code: str = "",
    project_type: str = "general",
    owner_key: Optional[str] = None,
    job_id: Optional[str] = None,
    last_research_id: Optional[str] = None,
    share_url: Optional[str] = None,
    summary_snapshot: Optional[Dict[str, Any]] = None,
    notes: str = "",
    status: str = "active",
    phone: str = "",
) -> Dict[str, Any]:
    """Create or update a job. Dedupes by email+address+zip when job_id omitted."""
    email = _norm_email(owner_email)
    if not email:
        raise ValueError("owner_email is required")
    if not (address or "").strip():
        raise ValueError("address is required")

    now = _iso()
    existing: Optional[Dict[str, Any]] = None

    if job_id:
        existing = _read_job(job_id)
        if existing and not _can_access(existing, email, owner_key):
            raise PermissionError("Not allowed to update this job")
    else:
        # Dedupe: same email + normalized address + zip
        for j in list_jobs(email=email, owner_key=owner_key):
            same_addr = (j.get("address") or "").strip().lower() == address.strip().lower()
            same_zip = (j.get("zip") or "").strip() == (zip_code or "").strip()
            if same_addr and (same_zip or not zip_code):
                existing = j
                break

    jid = (existing or {}).get("id") or _safe_id(job_id)
    job = {
        "id": jid,
        "owner_email": email,
        "owner_key": owner_key or (existing or {}).get("owner_key") or "",
        "address": address.strip(),
        "city": (city or "").strip(),
        "state": (
            (state or "").strip().upper()
            if state and len((state or "").strip()) <= 2
            else (state or "").strip() or (existing or {}).get("state") or ""
        ),
        "zip": (zip_code or "").strip(),
        "project_type": project_type or (existing or {}).get("project_type") or "general",
        "status": status or "active",
        "phone": (phone or "").strip() or (existing or {}).get("phone") or "",
        "last_research_id": last_research_id or (existing or {}).get("last_research_id"),
        "share_url": share_url or (existing or {}).get("share_url"),
        "last_run_at": now if last_research_id or not existing else (existing or {}).get("last_run_at"),
        "summary_snapshot": summary_snapshot
        if summary_snapshot is not None
        else (existing or {}).get("summary_snapshot") or {},
        "notes": notes if notes is not None else (existing or {}).get("notes") or "",
        "created_at": (existing or {}).get("created_at") or now,
        "updated_at": now,
    }
    if last_research_id:
        job["last_run_at"] = now
    _write_job(job)
    logger.info(f"Saved job {jid} for {email}")
    return deepcopy(job)


def list_jobs(
    *,
    email: Optional[str] = None,
    owner_key: Optional[str] = None,
    include_archived: bool = False,
) -> List[Dict[str, Any]]:
    email_n = _norm_email(email)
    jobs: List[Dict[str, Any]] = []
    seen = set()

    if email_n:
        _load_index()
        ids = list(_INDEX.get(email_n) or [])
        for jid in ids:
            job = _read_job(jid)
            if job and job["id"] not in seen:
                jobs.append(job)
                seen.add(job["id"])
        for remote in _supabase_list(email_n):
            if remote.get("id") not in seen:
                jobs.append(remote)
                seen.add(remote["id"])

    if owner_key:
        # Scan local files for owner_key matches (small v1 scale)
        for path in _store_dir().glob("job-*.json"):
            try:
                job = json.loads(path.read_text(encoding="utf-8"))
                if (job.get("owner_key") or "") == owner_key and job.get("id") not in seen:
                    if email_n and _norm_email(job.get("owner_email")) != email_n:
                        # if email provided, don't leak other emails via key alone when emails differ
                        # still allow key-only access when no email filter? allow if keys match
                        pass
                    jobs.append(job)
                    seen.add(job["id"])
            except Exception:
                continue

    out = []
    for job in jobs:
        if not _can_access(job, email, owner_key):
            continue
        if not include_archived and (job.get("status") or "active") == "archived":
            continue
        out.append(job)

    out.sort(key=lambda j: j.get("updated_at") or j.get("created_at") or "", reverse=True)
    return out


def get_job(job_id: str, *, email: Optional[str] = None, owner_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    job = _read_job(job_id)
    if not job:
        return None
    if not _can_access(job, email, owner_key):
        return None
    return job


def delete_job(job_id: str, *, email: Optional[str] = None, owner_key: Optional[str] = None) -> bool:
    job = get_job(job_id, email=email, owner_key=owner_key)
    if not job:
        return False
    jid = job["id"]
    with _LOCK:
        _MEMORY.pop(jid, None)
        path = _file_path(jid)
        if path.exists():
            path.unlink()
    _index_remove(job.get("owner_email") or "", jid)
    if _supabase_ok():
        try:
            from supabase import create_client

            sb = create_client(os.environ["SUPABASE_URL"].strip(), os.environ["SUPABASE_KEY"].strip())
            sb.table("saved_jobs").delete().eq("id", jid).execute()
        except Exception as e:
            logger.warning(f"Supabase job delete failed: {e}")
    return True



def list_emails_with_active_jobs() -> Dict[str, List[Dict[str, Any]]]:
    """Group active saved jobs by owner email (local index) for weekly digests."""
    _load_index()
    out: Dict[str, List[Dict[str, Any]]] = {}
    for email, ids in list(_INDEX.items()):
        email_n = _norm_email(email)
        if not email_n:
            continue
        jobs: List[Dict[str, Any]] = []
        for jid in ids:
            job = _read_job(jid)
            if not job:
                continue
            if (job.get("status") or "active") == "archived":
                continue
            jobs.append(job)
        if jobs:
            out[email_n] = jobs
    return out


def attach_research(
    job_id: str,
    *,
    research_id: str,
    share_url: Optional[str] = None,
    summary_snapshot: Optional[Dict[str, Any]] = None,
    email: Optional[str] = None,
    owner_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    job = get_job(job_id, email=email, owner_key=owner_key)
    if not job:
        return None
    return upsert_job(
        owner_email=job["owner_email"],
        address=job["address"],
        city=job.get("city") or "",
        state=job.get("state") or "",
        zip_code=job.get("zip") or "",
        project_type=job.get("project_type") or "general",
        owner_key=owner_key or job.get("owner_key"),
        job_id=job["id"],
        last_research_id=research_id,
        share_url=share_url or job.get("share_url"),
        summary_snapshot=summary_snapshot if summary_snapshot is not None else job.get("summary_snapshot"),
        notes=job.get("notes") or "",
        status=job.get("status") or "active",
    )
