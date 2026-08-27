"""ZIP watch — alert when Saved Job ZIPs' local pack fingerprint changes."""
from __future__ import annotations

import hashlib
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parent
_STATE_PATH = _BACKEND_DIR / "data" / "zip_watch_state.json"
_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_state() -> Dict[str, Any]:
    if not _STATE_PATH.is_file():
        return {"zips": {}, "alerts": []}
    try:
        return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"zips": {}, "alerts": []}


def _save_state(state: Dict[str, Any]) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def pack_fingerprint(city: str, state: str, zip_code: str) -> Tuple[str, Dict[str, Any]]:
    """Stable fingerprint of citeable/local intel for a ZIP."""
    from ahj_catalog import lookup_ahj
    from local_pack_store import load_zip_pack
    from metro_portal_seeds import resolve_metro_portal_pack
    from scraper import normalize_us_zip

    z = normalize_us_zip(zip_code) if zip_code else ""
    rec = lookup_ahj(city, state, z) if (city or z) else None
    pack = None
    if z:
        try:
            pack = load_zip_pack(z)
        except Exception:
            pack = None
    if not pack:
        pack = resolve_metro_portal_pack(city, state, z) or {}

    fees = []
    gotchas = []
    if rec:
        fees = [
            f"{f.get('trade')}|{f.get('label')}|{f.get('amount_usd')}|{f.get('citation_url')}"
            for f in (rec.get("fees") or [])
            if isinstance(f, dict)
        ]
        gotchas = [
            f"{g.get('title')}|{g.get('citation_url')}"
            for g in (rec.get("gotchas") or [])
            if isinstance(g, dict)
        ]
        meta = {
            "source": "ahj_catalog",
            "ahj_id": rec.get("ahj_id"),
            "last_verified": rec.get("last_verified") or "",
            "fee_count": len(fees),
            "gotcha_count": len(gotchas),
            "portal": rec.get("portal_url") or "",
        }
        blob = "|".join(
            [
                str(rec.get("ahj_id")),
                str(rec.get("last_verified")),
                str(rec.get("portal_url")),
                *fees,
                *gotchas,
                *[str(s) for s in (rec.get("inspection_sequence") or [])],
            ]
        )
    else:
        ahj = (pack or {}).get("ahj") or {}
        fees = [
            f"{f.get('label')}|{f.get('amount_usd')}|{f.get('source_url')}"
            for f in ((pack or {}).get("fees") or [])
            if isinstance(f, dict)
        ]
        gotchas = [
            f"{g.get('title')}|{g.get('source_url')}"
            for g in ((pack or {}).get("gotchas") or [])
            if isinstance(g, dict)
        ]
        meta = {
            "source": (pack or {}).get("tier") or "portal",
            "ahj_id": (pack or {}).get("pack_key"),
            "last_verified": (pack or {}).get("last_verified") or ahj.get("last_verified") or "",
            "fee_count": len(fees),
            "gotcha_count": len(gotchas),
            "portal": ahj.get("portal_url") or "",
        }
        blob = "|".join(
            [
                str(meta["ahj_id"]),
                str(meta["last_verified"]),
                str(meta["portal"]),
                *fees,
                *gotchas,
            ]
        )
    fp = hashlib.sha256(blob.encode("utf-8")).hexdigest()[:20]
    return fp, meta


def run_zip_watch(*, dry_run: bool = False) -> Dict[str, Any]:
    """
    Compare fingerprints for ZIPs on active Saved Jobs.
    Returns changes list; updates state unless dry_run.
    """
    from jobs_store import list_emails_with_active_jobs

    grouped = list_emails_with_active_jobs()
    state = _load_state()
    zips_state: Dict[str, Any] = dict(state.get("zips") or {})
    changes: List[Dict[str, Any]] = []
    checked = 0

    # Unique ZIP + city/state from jobs
    watch: Dict[str, Dict[str, Any]] = {}
    for email, jobs in grouped.items():
        for job in jobs:
            z = str(job.get("zip") or "").strip()[:5]
            if len(z) < 5:
                continue
            entry = watch.setdefault(
                z,
                {
                    "zip": z,
                    "city": job.get("city") or "",
                    "state": job.get("state") or "",
                    "emails": set(),
                    "phones": set(),
                    "jobs": [],
                },
            )
            entry["emails"].add(email)
            phone = str(job.get("phone") or "").strip()
            if phone:
                entry["phones"].add(phone)
            if job.get("city"):
                entry["city"] = job.get("city")
            if job.get("state"):
                entry["state"] = job.get("state")
            entry["jobs"].append(
                {
                    "id": job.get("id"),
                    "address": job.get("address"),
                    "share_url": job.get("share_url"),
                }
            )

    for z, entry in watch.items():
        checked += 1
        try:
            fp, meta = pack_fingerprint(entry["city"], entry["state"], z)
        except Exception as e:
            logger.warning("zip watch fingerprint failed %s: %s", z, e)
            continue
        prev = zips_state.get(z) or {}
        prev_fp = prev.get("fingerprint")
        if prev_fp and prev_fp != fp:
            change = {
                "zip": z,
                "city": entry["city"],
                "state": entry["state"],
                "emails": sorted(entry["emails"]),
                "phones": sorted(entry.get("phones") or []),
                "jobs": entry["jobs"][:8],
                "before": prev.get("meta") or {},
                "after": meta,
                "ts": _now(),
            }
            changes.append(change)
        zips_state[z] = {"fingerprint": fp, "meta": meta, "updated_at": _now()}

    if not dry_run:
        with _LOCK:
            st = _load_state()
            st["zips"] = zips_state
            alerts = list(st.get("alerts") or [])
            for c in changes:
                alerts.append(
                    {
                        "ts": c["ts"],
                        "zip": c["zip"],
                        "emails": c["emails"],
                        "after": c["after"],
                    }
                )
            st["alerts"] = alerts[-200:]
            st["last_run_at"] = _now()
            _save_state(st)

    return {
        "status": "ok",
        "checked": checked,
        "changes": len(changes),
        "change_list": [
            {
                **{k: v for k, v in c.items() if k not in ("emails", "phones")},
                "email_count": len(c["emails"]),
                "emails": c["emails"],
                "phones": c.get("phones") or [],
            }
            for c in changes
        ],
    }
