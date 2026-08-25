"""
Optional remote sync for local packs / ahj_promoted.

Env:
  PACK_SYNC_BACKEND=none|s3|supabase  (default none)
  PACK_SYNC_S3_BUCKET=
  PACK_SYNC_S3_PREFIX=regguard-packs/
  AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_DEFAULT_REGION
  SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY  (table: pack_blobs key, body jsonb)
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def sync_backend() -> str:
    return (os.getenv("PACK_SYNC_BACKEND") or "none").strip().lower()


def push_pack_file(local_path: Path, *, kind: str = "local_packs") -> bool:
    """Best-effort upload of a JSON pack file. Returns True if synced or sync off."""
    mode = sync_backend()
    if mode in ("", "none", "off", "0"):
        return True
    if not local_path.is_file():
        return False
    try:
        body = local_path.read_text(encoding="utf-8")
        key = f"{kind}/{local_path.name}"
        if mode == "s3":
            return _push_s3(key, body)
        if mode == "supabase":
            return _push_supabase(key, body)
        logger.warning("Unknown PACK_SYNC_BACKEND=%s", mode)
        return False
    except Exception as e:
        logger.warning("pack sync push failed: %s", e)
        return False


def pull_missing_packs(*, kinds: Optional[list] = None) -> Dict[str, Any]:
    """Best-effort hydrate local disk from remote (startup / cron)."""
    mode = sync_backend()
    if mode in ("", "none", "off", "0"):
        return {"status": "skipped", "mode": mode or "none"}
    kinds = kinds or ["local_packs", "ahj_promoted"]
    if mode == "s3":
        return _pull_s3(kinds)
    if mode == "supabase":
        return _pull_supabase(kinds)
    return {"status": "error", "error": f"unknown backend {mode}"}


def _push_s3(key: str, body: str) -> bool:
    bucket = (os.getenv("PACK_SYNC_S3_BUCKET") or "").strip()
    if not bucket:
        logger.warning("PACK_SYNC_S3_BUCKET not set")
        return False
    prefix = (os.getenv("PACK_SYNC_S3_PREFIX") or "regguard-packs/").strip()
    full_key = f"{prefix.rstrip('/')}/{key.lstrip('/')}"
    import boto3  # type: ignore

    client = boto3.client("s3")
    client.put_object(
        Bucket=bucket,
        Key=full_key,
        Body=body.encode("utf-8"),
        ContentType="application/json",
    )
    logger.info("pack sync S3 put s3://%s/%s", bucket, full_key)
    return True


def _pull_s3(kinds: list) -> Dict[str, Any]:
    bucket = (os.getenv("PACK_SYNC_S3_BUCKET") or "").strip()
    if not bucket:
        return {"status": "error", "error": "PACK_SYNC_S3_BUCKET missing"}
    prefix = (os.getenv("PACK_SYNC_S3_PREFIX") or "regguard-packs/").strip().rstrip("/") + "/"
    import boto3  # type: ignore
    from local_pack_store import packs_dir, promoted_dir

    client = boto3.client("s3")
    written = 0
    for kind in kinds:
        dest = packs_dir() if kind == "local_packs" else promoted_dir()
        resp = client.list_objects_v2(Bucket=bucket, Prefix=f"{prefix}{kind}/")
        for obj in resp.get("Contents") or []:
            key = obj.get("Key") or ""
            name = key.rsplit("/", 1)[-1]
            if not name.endswith(".json"):
                continue
            path = dest / name
            if path.is_file():
                continue
            data = client.get_object(Bucket=bucket, Key=key)["Body"].read()
            path.write_bytes(data)
            written += 1
    return {"status": "ok", "mode": "s3", "written": written}


def _push_supabase(key: str, body: str) -> bool:
    url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    key_svc = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
    if not url or not key_svc:
        logger.warning("Supabase pack sync missing SUPABASE_URL / service key")
        return False
    import httpx

    payload = {"key": key, "body": json.loads(body), "updated_at": _iso()}
    # upsert on key
    r = httpx.post(
        f"{url}/rest/v1/pack_blobs",
        headers={
            "apikey": key_svc,
            "Authorization": f"Bearer {key_svc}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        },
        json=payload,
        timeout=20.0,
    )
    if r.status_code >= 300:
        logger.warning("Supabase pack sync %s: %s", r.status_code, r.text[:200])
        return False
    return True


def _pull_supabase(kinds: list) -> Dict[str, Any]:
    url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    key_svc = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or ""
    if not url or not key_svc:
        return {"status": "error", "error": "supabase env missing"}
    import httpx
    from local_pack_store import packs_dir, promoted_dir

    written = 0
    r = httpx.get(
        f"{url}/rest/v1/pack_blobs?select=key,body",
        headers={"apikey": key_svc, "Authorization": f"Bearer {key_svc}"},
        timeout=30.0,
    )
    if r.status_code >= 300:
        return {"status": "error", "error": r.text[:200]}
    for row in r.json() or []:
        key = str(row.get("key") or "")
        body = row.get("body")
        if not key.endswith(".json") or body is None:
            continue
        kind = key.split("/", 1)[0]
        if kind not in kinds:
            continue
        dest = packs_dir() if kind == "local_packs" else promoted_dir()
        name = key.rsplit("/", 1)[-1]
        path = dest / name
        if path.is_file():
            continue
        path.write_text(json.dumps(body, indent=2), encoding="utf-8")
        written += 1
    return {"status": "ok", "mode": "supabase", "written": written}


def _iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
