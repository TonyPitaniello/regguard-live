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
_INDEX_MTIME: float = -1.0  # disk mtime of _email_index.json when last loaded


def _store_dir() -> Path:
    env_jobs = (os.getenv("REG_GUARD_JOBS_DIR") or "").strip()
    if env_jobs:
        base = Path(env_jobs)
    else:
        data = (os.getenv("REGGUARD_DATA_DIR") or "").strip()
        base = Path(data) / "saved_jobs" if data else Path(__file__).resolve().parent / "data" / "saved_jobs"
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


def _rebuild_index_from_files_locked() -> None:
    """Recover the email index from job files when disk outlives the in-memory map."""
    for path in _store_dir().glob("*.json"):
        if path.name.startswith("_"):
            continue
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(job, dict):
            continue
        email = _norm_email(job.get("owner_email"))
        jid = str(job.get("id") or "").strip()
        if not email or not jid:
            continue
        ids = _INDEX.setdefault(email, [])
        if jid not in ids:
            ids.append(jid)


def _load_index(*, force: bool = False) -> None:
    """
    Load email→job-id index from disk.

    Multi-instance: always re-read when the index file mtime advances so one
    Render worker does not serve a stale in-memory list while another wrote jobs.
    """
    global _INDEX_MTIME
    path = _index_path()
    try:
        mtime = path.stat().st_mtime if path.exists() else 0.0
    except OSError:
        mtime = 0.0
    with _LOCK:
        if not force and _INDEX and mtime <= _INDEX_MTIME:
            return
        _INDEX.clear()
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, list):
                            _INDEX[k] = [str(x) for x in v]
            except Exception as e:
                logger.warning(f"Failed loading jobs index: {e}")
        if not _INDEX:
            _rebuild_index_from_files_locked()
            if _INDEX:
                try:
                    path.write_text(json.dumps(_INDEX, ensure_ascii=False), encoding="utf-8")
                except Exception as e:
                    logger.warning(f"Failed writing jobs index: {e}")
        try:
            _INDEX_MTIME = path.stat().st_mtime if path.exists() else mtime
        except OSError:
            _INDEX_MTIME = mtime


def _save_index() -> None:
    global _INDEX_MTIME
    try:
        path = _index_path()
        path.write_text(json.dumps(_INDEX, ensure_ascii=False), encoding="utf-8")
        try:
            _INDEX_MTIME = path.stat().st_mtime
        except OSError:
            pass
    except Exception as e:
        logger.warning(f"Failed writing jobs index: {e}")


def _scan_job_ids_for_email(email_n: str) -> List[str]:
    """Reconcile from job files — index alone is not reliable across workers."""
    found: List[str] = []
    if not email_n:
        return found
    for path in _store_dir().glob("*.json"):
        if path.name.startswith("_"):
            continue
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(job, dict):
            continue
        if _norm_email(job.get("owner_email")) != email_n:
            continue
        jid = str(job.get("id") or "").strip()
        if jid and jid not in found:
            found.append(jid)
    return found


def _addrs_match(a: str, b: str) -> bool:
    return (a or "").strip().lower() == (b or "").strip().lower()


def _zips_compatible(existing_zip: str, new_zip: str) -> bool:
    """Same ZIP, or one side blank (legacy rows). Never match different ZIPs."""
    ez = (existing_zip or "").strip()
    nz = (new_zip or "").strip()
    if not ez or not nz:
        return True
    return ez == nz


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
        # Stale job_id from a prior site must not overwrite a different address
        if existing and not (
            _addrs_match(str(existing.get("address") or ""), address)
            and _zips_compatible(str(existing.get("zip") or ""), zip_code or "")
        ):
            logger.info(
                "Ignoring stale job_id %s (address changed %r → %r)",
                job_id,
                existing.get("address"),
                address,
            )
            existing = None
    else:
        # Dedupe: same email + normalized address + compatible zip
        for j in list_jobs(email=email, owner_key=owner_key):
            if _addrs_match(str(j.get("address") or ""), address) and _zips_compatible(
                str(j.get("zip") or ""), zip_code or ""
            ):
                existing = j
                break

    jid = (existing or {}).get("id") or _safe_id(None if not existing else job_id)
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
    snap = job.get("summary_snapshot") if isinstance(job.get("summary_snapshot"), dict) else {}
    stamp = snap.get("regguard_stamp") if isinstance(snap.get("regguard_stamp"), dict) else {}
    job["last_stamp_grade"] = str(
        stamp.get("grade") or snap.get("last_stamp_grade") or (existing or {}).get("last_stamp_grade") or ""
    )
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
        # Always reconcile from job files (index can lag across Render workers)
        for jid in _scan_job_ids_for_email(email_n):
            if jid not in ids:
                ids.append(jid)
                _index_add(email_n, jid)
        for jid in ids:
            job = _read_job(jid)
            if job and job["id"] not in seen:
                jobs.append(job)
                seen.add(job["id"])
        for remote in _supabase_list(email_n):
            rid = str(remote.get("id") or "")
            if rid and rid not in seen:
                jobs.append(remote)
                seen.add(rid)
                # Keep local durable copy so later file scans find it
                try:
                    if not _file_path(rid).exists():
                        _write_job(remote)
                except Exception:
                    pass

    if owner_key:
        # Scan local files for owner_key matches (small v1 scale)
        for path in _store_dir().glob("job-*.json"):
            try:
                job = json.loads(path.read_text(encoding="utf-8"))
                if (job.get("owner_key") or "") != owner_key:
                    continue
                jid = job.get("id")
                if not jid or jid in seen:
                    continue
                jobs.append(job)
                seen.add(jid)
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
