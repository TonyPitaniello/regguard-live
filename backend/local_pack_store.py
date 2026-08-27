"""
Order-attached local packs + shared ZIP cache + promote + demand seed.

Tiers (never auto-promote to full_pack):
  order_draft / paid_local / portal_seed  — automated
  full_pack                               — human promote only

Storage under REGGUARD_DATA_DIR:
  local_packs/{zip5}.json     — durable draft packs (shared across orders)
  local_pack_hits.jsonl       — demand signal
  ahj_promoted/{ahj_id}.json  — citeable library (runtime, same schema as ahj_data/)
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()


def _data_root() -> Path:
    root = Path(os.getenv("REGGUARD_DATA_DIR") or "/tmp/regguard_data")
    root.mkdir(parents=True, exist_ok=True)
    return root


def packs_dir() -> Path:
    d = _data_root() / "local_packs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def promoted_dir() -> Path:
    d = _data_root() / "ahj_promoted"
    d.mkdir(parents=True, exist_ok=True)
    return d


def hits_path() -> Path:
    return _data_root() / "local_pack_hits.jsonl"


def _zip5(zip_code: str = "") -> str:
    digits = "".join(c for c in (zip_code or "") if c.isdigit())
    return digits[:5]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slug(city: str = "", state: str = "") -> str:
    c = re.sub(r"[^a-z0-9]+", "_", (city or "").strip().lower()).strip("_") or "city"
    s = re.sub(r"[^a-z0-9]+", "", (state or "").strip().lower())[:2] or "xx"
    return f"{c}_{s}"


def attach_local_pack_from_analysis(
    analysis: Dict[str, Any],
    *,
    city: str = "",
    state: str = "",
    zip_code: str = "",
    order_id: str = "",
    research_id: str = "",
    persist: bool = True,
    record_hit: bool = True,
) -> Dict[str, Any]:
    """
    Build/refresh analysis['local_pack'] from paid_local + cards + existing packs.
    Optionally persist to ZIP cache and log a demand hit.
    """
    if not isinstance(analysis, dict):
        return analysis

    pi = analysis.get("project_info") or {}
    city = (city or str(pi.get("city") or "")).strip()
    state = (state or str(pi.get("state") or "")).strip()
    zip_code = (zip_code or str(pi.get("zip") or "")).strip()
    z5 = _zip5(zip_code)

    # Prefer already-promoted / curated full pack
    promoted = load_promoted_record(city=city, state=state, zip_code=z5)
    if promoted:
        pack = _pack_from_ahj_record(promoted, tier="full_pack", source="promoted")
        analysis["local_pack"] = pack
        if record_hit:
            log_pack_hit(z5, city, state, tier="full_pack", order_id=order_id, research_id=research_id)
        return analysis

    # Existing curated city pack
    try:
        from city_packs import resolve_city_pack

        curated = resolve_city_pack(city, state, zip_code)
        if curated and curated.get("citeable"):
            pack = _normalize_runtime_pack(
                curated,
                tier="full_pack",
                city=city,
                state=state,
                zip_code=z5,
                source="city_packs",
            )
            analysis["local_pack"] = pack
            if record_hit:
                log_pack_hit(z5, city, state, tier="full_pack", order_id=order_id, research_id=research_id)
            return analysis
    except Exception:
        pass

    # Shared ZIP draft cache
    cached = load_zip_pack(z5) if z5 else None
    if cached and cached.get("tier") in ("paid_local", "portal_seed", "order_draft", "full_pack"):
        # Refresh fees from this analysis if richer
        pack = _merge_analysis_into_pack(cached, analysis, city=city, state=state, zip_code=z5)
        analysis["local_pack"] = pack
        if persist and z5:
            save_zip_pack(z5, pack)
        if record_hit:
            log_pack_hit(
                z5,
                city,
                state,
                tier=str(pack.get("tier") or "order_draft"),
                order_id=order_id,
                research_id=research_id,
                cache_hit=True,
            )
        return analysis

    pack = build_pack_from_analysis(analysis, city=city, state=state, zip_code=z5)
    analysis["local_pack"] = pack
    if persist and z5:
        save_zip_pack(z5, pack)
    if record_hit and z5:
        log_pack_hit(
            z5,
            city,
            state,
            tier=str(pack.get("tier") or "order_draft"),
            order_id=order_id,
            research_id=research_id,
            cache_hit=False,
        )
    return analysis


def build_pack_from_analysis(
    analysis: Dict[str, Any],
    *,
    city: str = "",
    state: str = "",
    zip_code: str = "",
) -> Dict[str, Any]:
    """Construct an order_draft / paid_local / portal_seed pack from analysis cards."""
    ahj_card = analysis.get("ahj_card") or {}
    fee_card = analysis.get("fee_card") or {}
    gotchas = (analysis.get("gotcha_watchlist") or {}).get("items") or []
    docs = (analysis.get("document_checklist") or {}).get("items") or []
    paid = analysis.get("paid_local") or {}
    coverage = analysis.get("coverage") or {}
    cov_tier = str(coverage.get("tier") or "").lower()

    portal = str(ahj_card.get("portal_url") or paid.get("portal_url") or "").strip()
    fees_url = str(ahj_card.get("fees_url") or portal).strip()
    fee_rows = list(fee_card.get("fees") or [])
    if not fee_rows and isinstance(paid.get("fee_rows"), list):
        fee_rows = list(paid.get("fee_rows") or [])

    # Infer tier — never full_pack here
    if cov_tier == "full_pack":
        tier = "full_pack"
        citeable = True
    elif paid.get("status") == "ok" and (fee_rows or portal):
        tier = "paid_local"
        citeable = False
    elif portal or cov_tier == "portal_seed":
        tier = "portal_seed"
        citeable = False
    else:
        tier = "order_draft"
        citeable = False

    doc_tasks: List[str] = []
    for d in docs:
        if isinstance(d, dict):
            t = str(d.get("task") or "").strip()
            if t:
                doc_tasks.append(t)
        elif d:
            doc_tasks.append(str(d))

    safe_fees: List[Dict[str, Any]] = []
    for row in fee_rows[:12]:
        if not isinstance(row, dict):
            continue
        safe_fees.append(
            {
                "label": str(row.get("label") or "Fee")[:120],
                "amount_usd": row.get("amount_usd") if (citeable or tier == "paid_local") else None,
                "detail": str(row.get("detail") or FEE_PLANNING)[:240],
                "source_url": str(row.get("source_url") or portal or "")[:300],
                "source_label": str(row.get("source_label") or "AHJ")[:80],
                "verified": bool(citeable and row.get("verified")),
            }
        )

    safe_gotchas: List[Dict[str, Any]] = []
    for g in gotchas[:12]:
        if not isinstance(g, dict):
            continue
        safe_gotchas.append(
            {
                "id": str(g.get("id") or "")[:80],
                "title": str(g.get("title") or "")[:120],
                "detail": str(g.get("detail") or "")[:300],
                "priority": str(g.get("priority") or "HIGH").upper(),
                "source_url": str(g.get("source_url") or portal or "")[:300],
                "source_label": str(g.get("source_label") or "AHJ")[:80],
            }
        )

    return {
        "tier": tier,
        "citeable": citeable,
        "pack_key": f"local:{_zip5(zip_code) or _slug(city, state)}",
        "city": city,
        "state": state,
        "zip": _zip5(zip_code),
        "ahj": {
            "name": str(ahj_card.get("name") or f"{city or 'Local'}, {state} AHJ").strip(),
            "portal_url": portal,
            "fees_url": fees_url,
            "phone": str(ahj_card.get("phone") or ""),
            "notes": str(ahj_card.get("notes") or "")[:400],
        },
        "fees": safe_fees,
        "gotchas": safe_gotchas,
        "documents": doc_tasks
        or [
            "Single-line diagram",
            "Load calculations",
            "Cut sheets",
            "Contractor license / registration",
        ],
        "timeline_hint": str(fee_card.get("timeline") or "Confirm with AHJ")[:120],
        "sources": [u for u in [portal, fees_url, str(paid.get("scraped_url") or "")] if u],
        "generated_at": _now_iso(),
        "paid_local_status": str(paid.get("status") or ""),
        "promote_candidate": bool(
            portal and (len(safe_fees) >= 1 or len(safe_gotchas) >= 1) and tier in ("paid_local", "portal_seed")
        ),
        "source": "analysis",
    }


FEE_PLANNING = "Planning aid — confirm on official AHJ schedule before bid."


def _normalize_runtime_pack(
    pack: Dict[str, Any],
    *,
    tier: str,
    city: str,
    state: str,
    zip_code: str,
    source: str,
) -> Dict[str, Any]:
    ahj = dict(pack.get("ahj") or {})
    return {
        "tier": tier,
        "citeable": bool(pack.get("citeable") or tier == "full_pack"),
        "pack_key": str(pack.get("pack_key") or f"local:{zip_code or _slug(city, state)}"),
        "city": pack.get("city") or city,
        "state": pack.get("state") or state,
        "zip": zip_code,
        "ahj": {
            "name": ahj.get("name") or f"{city}, {state} AHJ",
            "portal_url": ahj.get("portal_url") or "",
            "fees_url": ahj.get("fees_url") or ahj.get("portal_url") or "",
            "phone": ahj.get("phone") or "",
            "notes": ahj.get("notes") or "",
        },
        "fees": list(pack.get("fees") or []),
        "gotchas": list(pack.get("gotchas") or []),
        "documents": list(pack.get("documents") or []),
        "timeline_hint": pack.get("timeline_hint") or "Confirm with AHJ",
        "sources": list(pack.get("sources") or []),
        "generated_at": _now_iso(),
        "promote_candidate": False,
        "source": source,
    }


def _pack_from_ahj_record(rec: Dict[str, Any], *, tier: str, source: str) -> Dict[str, Any]:
    fees = []
    for fee in rec.get("fees") or []:
        fees.append(
            {
                "label": fee.get("label") or "Permit fee",
                "amount_usd": fee.get("amount_usd"),
                "trade": fee.get("trade") or "general",
                "detail": fee.get("citation_note") or FEE_PLANNING,
                "source_url": fee.get("citation_url") or rec.get("portal_url"),
                "source_label": rec.get("city") or "AHJ",
                "verified": bool(fee.get("verified")),
                "amount_requires_schedule": bool(fee.get("amount_requires_schedule")),
            }
        )
    gotchas = []
    for g in rec.get("gotchas") or []:
        gotchas.append(
            {
                "id": g.get("id"),
                "title": g.get("title"),
                "detail": "; ".join(g.get("checklist") or [])[:300],
                "priority": "HIGH",
                "source_url": g.get("citation_url") or rec.get("portal_url"),
                "source_label": rec.get("city") or "AHJ",
                "checklist": g.get("checklist") or [],
                "anti_patterns": g.get("anti_patterns") or [],
            }
        )
    return {
        "tier": tier,
        "citeable": True,
        "pack_key": str(rec.get("ahj_id") or ""),
        "city": rec.get("city") or "",
        "state": rec.get("state") or "",
        "zip": (rec.get("zips") or [""])[0] if rec.get("zips") else "",
        "ahj": {
            "name": f"{rec.get('city')}, {rec.get('state')} AHJ",
            "portal_url": rec.get("portal_url") or "",
            "fees_url": rec.get("fees_url") or rec.get("portal_url") or "",
            "apply_url": rec.get("apply_url") or "",
            "inspections_url": rec.get("inspections_url") or "",
            "phone": "",
            "notes": "Promoted / curated AHJ pack — still confirm dollars on the official schedule.",
            "last_verified": rec.get("last_verified") or "",
        },
        "fees": fees,
        "gotchas": gotchas,
        "documents": list(rec.get("inspection_sequence") or [])[:8]
        or [
            "Single-line diagram",
            "Load calculations",
            "Cut sheets",
            "Contractor license / registration",
        ],
        "inspection_sequence": list(rec.get("inspection_sequence") or [])[:10],
        "timeline_hint": "Confirm plan review windows with AHJ",
        "sources": [u for u in [rec.get("portal_url"), rec.get("fees_url")] if u],
        "generated_at": _now_iso(),
        "promote_candidate": False,
        "source": source,
        "ahj_id": rec.get("ahj_id"),
        "last_verified": rec.get("last_verified") or "",
    }


def _merge_analysis_into_pack(
    cached: Dict[str, Any],
    analysis: Dict[str, Any],
    *,
    city: str,
    state: str,
    zip_code: str,
) -> Dict[str, Any]:
    fresh = build_pack_from_analysis(analysis, city=city, state=state, zip_code=zip_code)
    out = dict(cached)
    # Prefer richer fees/gotchas/portal
    if len(fresh.get("fees") or []) > len(out.get("fees") or []):
        out["fees"] = fresh["fees"]
    if len(fresh.get("gotchas") or []) > len(out.get("gotchas") or []):
        out["gotchas"] = fresh["gotchas"]
    ahj = dict(out.get("ahj") or {})
    fahj = fresh.get("ahj") or {}
    if fahj.get("portal_url") and not ahj.get("portal_url"):
        ahj["portal_url"] = fahj["portal_url"]
        ahj["fees_url"] = fahj.get("fees_url") or fahj["portal_url"]
    if fahj.get("name"):
        ahj.setdefault("name", fahj["name"])
    out["ahj"] = ahj
    # Never downgrade full_pack; never upgrade to full_pack automatically
    if out.get("tier") != "full_pack":
        rank = {"order_draft": 0, "portal_seed": 1, "paid_local": 2, "full_pack": 3}
        if rank.get(str(fresh.get("tier")), 0) > rank.get(str(out.get("tier")), 0):
            out["tier"] = fresh["tier"]
            out["citeable"] = False
    out["promote_candidate"] = bool(fresh.get("promote_candidate"))
    out["updated_at"] = _now_iso()
    out["city"] = city or out.get("city")
    out["state"] = state or out.get("state")
    out["zip"] = zip_code or out.get("zip")
    return out


def load_zip_pack(zip_code: str) -> Optional[Dict[str, Any]]:
    z5 = _zip5(zip_code)
    if not z5:
        return None
    path = packs_dir() / f"{z5}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception as e:
        logger.warning("load_zip_pack %s failed: %s", z5, e)
        return None


def save_zip_pack(zip_code: str, pack: Dict[str, Any]) -> Path:
    z5 = _zip5(zip_code)
    path = packs_dir() / f"{z5}.json"
    prev: Optional[Dict[str, Any]] = None
    if path.is_file():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                prev = raw
        except Exception:
            prev = None
    payload = dict(pack)
    payload["zip"] = z5
    payload["saved_at"] = _now_iso()
    with _LOCK:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    try:
        from pack_storage_sync import push_pack_file

        push_pack_file(path, kind="local_packs")
    except Exception as e:
        logger.debug("pack sync skip: %s", e)
    # Rising-edge notify when pack becomes promote-ready
    if payload.get("promote_candidate") and not (prev or {}).get("promote_candidate"):
        try:
            from promote_notify import notify_promote_candidate

            notify_promote_candidate(payload, zip_code=z5)
        except Exception as e:
            logger.warning("promote notify failed: %s", e)
    return path


def log_pack_hit(
    zip_code: str,
    city: str = "",
    state: str = "",
    *,
    tier: str = "",
    order_id: str = "",
    research_id: str = "",
    cache_hit: bool = False,
) -> None:
    z5 = _zip5(zip_code)
    if not z5:
        return
    row = {
        "ts": _now_iso(),
        "zip": z5,
        "city": city,
        "state": state,
        "tier": tier,
        "order_id": order_id,
        "research_id": research_id,
        "cache_hit": bool(cache_hit),
    }
    try:
        with _LOCK:
            with hits_path().open("a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
    except Exception as e:
        logger.warning("log_pack_hit failed: %s", e)


def list_draft_packs(*, min_hits: int = 1, limit: int = 50) -> List[Dict[str, Any]]:
    """Queue for ops: ZIP drafts ranked by hit count, excluding full_pack."""
    ranks = rank_zips_by_demand(limit=200)
    out: List[Dict[str, Any]] = []
    for row in ranks:
        if int(row.get("hits") or 0) < min_hits:
            continue
        z5 = row["zip"]
        pack = load_zip_pack(z5) or {}
        if pack.get("tier") == "full_pack" or pack.get("citeable"):
            continue
        if load_promoted_record(zip_code=z5):
            continue
        try:
            from pack_quality import promote_readiness_score

            readiness = promote_readiness_score(pack)
        except Exception:
            readiness = 0.0
        out.append(
            {
                **row,
                "tier": pack.get("tier") or row.get("tier") or "missing",
                "fee_count": len(pack.get("fees") or []),
                "gotcha_count": len(pack.get("gotchas") or []),
                "portal_url": (pack.get("ahj") or {}).get("portal_url") or "",
                "promote_candidate": bool(pack.get("promote_candidate")),
                "readiness": readiness,
                "pack": pack or None,
            }
        )
        if len(out) >= limit:
            break
    return out


def rank_zips_by_demand(*, limit: int = 50, days: int = 90) -> List[Dict[str, Any]]:
    path = hits_path()
    if not path.is_file():
        return []
    cutoff = time.time() - max(1, days) * 86400
    counts: Dict[str, Dict[str, Any]] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    for line in lines[-20_000:]:
        try:
            row = json.loads(line)
        except Exception:
            continue
        z5 = _zip5(str(row.get("zip") or ""))
        if not z5:
            continue
        ts = str(row.get("ts") or "")
        # Soft age filter — ISO compare if parse fails keep row
        try:
            t = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
            if t < cutoff:
                continue
        except Exception:
            pass
        slot = counts.setdefault(
            z5,
            {
                "zip": z5,
                "hits": 0,
                "city": row.get("city") or "",
                "state": row.get("state") or "",
                "tier": row.get("tier") or "",
                "fee_bonus": 0,
            },
        )
        slot["hits"] += 1
        if row.get("city"):
            slot["city"] = row["city"]
        if row.get("state"):
            slot["state"] = row["state"]
        if row.get("tier"):
            slot["tier"] = row["tier"]
        pack = load_zip_pack(z5)
        if pack and (pack.get("fees") or []):
            slot["fee_bonus"] = 1

    scored = []
    for z5, slot in counts.items():
        score = float(slot["hits"]) * (1.0 if slot.get("fee_bonus") else 0.3)
        # Skip already full / promoted
        if load_promoted_record(zip_code=z5):
            continue
        pack = load_zip_pack(z5) or {}
        if pack.get("tier") == "full_pack":
            continue
        scored.append({**slot, "score": round(score, 2)})
    scored.sort(key=lambda r: (-r["score"], -r["hits"], r["zip"]))
    return scored[:limit]


def load_promoted_record(
    *,
    city: str = "",
    state: str = "",
    zip_code: str = "",
) -> Optional[Dict[str, Any]]:
    z5 = _zip5(zip_code)
    city_l = (city or "").strip().lower()
    state_u = (state or "").strip().upper()
    for path in sorted(promoted_dir().glob("*.json")):
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(rec, dict):
            continue
        if z5 and z5 in (rec.get("zips") or []):
            return rec
        if city_l and _city_matches(city_l, rec):
            st = (rec.get("state") or "").upper()
            if not state_u or state_u in (st, "TEXAS" if st == "TX" else st):
                return rec
    return None


def _city_matches(city_l: str, rec: Dict[str, Any]) -> bool:
    aliases = [a.lower() for a in (rec.get("aliases") or [])]
    return city_l == (rec.get("city") or "").lower() or city_l in aliases


def list_promoted() -> List[Dict[str, Any]]:
    out = []
    for path in sorted(promoted_dir().glob("*.json")):
        try:
            rec = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(rec, dict):
                out.append(rec)
        except Exception:
            continue
    return out


def draft_to_ahj_record(
    pack: Dict[str, Any],
    *,
    reviewer: str = "",
    edits: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Map runtime pack → ahj_data / plano.json schema."""
    edits = edits or {}
    city = str(edits.get("city") or pack.get("city") or "Unknown").strip()
    state = str(edits.get("state") or pack.get("state") or "").strip().upper()[:2]
    z5 = _zip5(str(edits.get("zip") or pack.get("zip") or ""))
    ahj_id = str(edits.get("ahj_id") or _slug(city, state))
    portal = str(
        edits.get("portal_url")
        or (pack.get("ahj") or {}).get("portal_url")
        or ""
    ).strip()

    fees_in = edits.get("fees") if isinstance(edits.get("fees"), list) else pack.get("fees") or []
    fees = []
    for i, fee in enumerate(fees_in):
        if not isinstance(fee, dict):
            continue
        fees.append(
            {
                "id": str(fee.get("id") or f"fee_{i+1}")[:80],
                "trade": fee.get("trade") or "electrical",
                "label": str(fee.get("label") or "Permit fee")[:120],
                "amount_usd": fee.get("amount_usd"),
                "citation_url": str(fee.get("source_url") or fee.get("citation_url") or portal)[:300],
                "citation_note": str(fee.get("detail") or fee.get("citation_note") or FEE_PLANNING)[:240],
                "verified": bool(fee.get("verified", True) if fee.get("amount_usd") is not None else False),
                "amount_requires_schedule": fee.get("amount_usd") is None,
            }
        )

    gotchas_in = edits.get("gotchas") if isinstance(edits.get("gotchas"), list) else pack.get("gotchas") or []
    gotchas = []
    for i, g in enumerate(gotchas_in):
        if not isinstance(g, dict):
            continue
        checklist = g.get("checklist")
        if not checklist:
            detail = str(g.get("detail") or "")
            checklist = [p.strip() for p in detail.split(";") if p.strip()][:6] or [detail[:120]]
        gotchas.append(
            {
                "id": str(g.get("id") or f"gotcha_{i+1}")[:80],
                "title": str(g.get("title") or "Local gotcha")[:120],
                "checklist": checklist,
                "anti_patterns": list(g.get("anti_patterns") or []),
                "citation_url": str(g.get("source_url") or g.get("citation_url") or portal)[:300],
            }
        )

    zips = list(edits.get("zips") or ([z5] if z5 else []))
    return {
        "ahj_id": ahj_id,
        "city": city,
        "state": state,
        "zips": zips,
        "aliases": list(edits.get("aliases") or [city.lower()]),
        "fees": fees,
        "gotchas": gotchas,
        "inspection_sequence": list(
            edits.get("inspection_sequence")
            or pack.get("documents")
            or [
                "Permit application / plan intake",
                "Rough electrical inspection",
                "Final electrical inspection",
            ]
        )[:10],
        "portal_url": portal,
        "fees_url": str(
            edits.get("fees_url")
            or (pack.get("ahj") or {}).get("fees_url")
            or portal
        ).strip(),
        "apply_url": str(edits.get("apply_url") or (pack.get("ahj") or {}).get("apply_url") or "").strip(),
        "inspections_url": str(
            edits.get("inspections_url") or (pack.get("ahj") or {}).get("inspections_url") or ""
        ).strip(),
        "last_verified": str(edits.get("last_verified") or pack.get("last_verified") or "")[:32],
        "promoted_at": _now_iso(),
        "promoted_by": reviewer or "ops",
        "source_pack_tier": pack.get("tier"),
        "citeable": True,
    }


def promote_zip_pack(
    zip_code: str,
    *,
    reviewer: str = "",
    edits: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Human promote: write ahj_promoted record + upgrade ZIP cache to full_pack."""
    from pack_quality import validate_pack_for_promote, validate_promoted_record

    z5 = _zip5(zip_code)
    pack = load_zip_pack(z5)
    if not pack:
        raise ValueError(f"No draft pack for ZIP {z5}")
    edits = edits or {}
    ok, errors = validate_pack_for_promote(pack, edits=edits)
    if not ok:
        raise ValueError("; ".join(errors))

    rec = draft_to_ahj_record(pack, reviewer=reviewer, edits=edits)
    ok_rec, rec_errors = validate_promoted_record(rec)
    if not ok_rec:
        raise ValueError("Promoted record schema: " + "; ".join(rec_errors))

    path = promoted_dir() / f"{rec['ahj_id']}.json"
    with _LOCK:
        path.write_text(json.dumps(rec, indent=2), encoding="utf-8")
        # Invalidate catalog LRU if present
        try:
            from ahj_catalog import load_ahj_catalog

            load_ahj_catalog.cache_clear()
        except Exception:
            pass

    try:
        from pack_storage_sync import push_pack_file

        push_pack_file(path, kind="ahj_promoted")
    except Exception as e:
        logger.debug("promoted pack sync skip: %s", e)

    # Upgrade ZIP cache
    runtime = _pack_from_ahj_record(rec, tier="full_pack", source="promoted")
    save_zip_pack(z5, runtime)
    return {"status": "ok", "path": str(path), "record": rec, "local_pack": runtime}


def seed_top_zips(
    *,
    limit: int = 10,
    max_pages: Optional[int] = None,
    service_email: str = "seed@regguardagent.com",
) -> Dict[str, Any]:
    """
    Demand-driven seed: for top unpaid ZIPs missing a useful draft, run paid_local_confirm.
    Caps via SEED_MAX_PER_DAY env (default 10).
    """
    max_day = int(os.getenv("SEED_MAX_PER_DAY") or "10")
    limit = max(1, min(limit, max_day))
    ranked = rank_zips_by_demand(limit=80)
    # Also include drafts that exist but are thin (no portal)
    candidates: List[Dict[str, Any]] = []
    for row in ranked:
        z5 = row["zip"]
        if load_promoted_record(zip_code=z5):
            continue
        pack = load_zip_pack(z5)
        portal = ((pack or {}).get("ahj") or {}).get("portal_url") if pack else ""
        fees = (pack or {}).get("fees") or []
        if pack and portal and fees:
            continue  # already useful draft
        candidates.append(row)
        if len(candidates) >= limit:
            break

    results: List[Dict[str, Any]] = []
    if not candidates:
        return {"status": "ok", "seeded": 0, "results": [], "note": "No seed candidates"}

    from paid_local_confirm import run_paid_local_confirm

    for row in candidates:
        z5 = row["zip"]
        city = str(row.get("city") or "")
        state = str(row.get("state") or "")
        analysis: Dict[str, Any] = {
            "project_info": {
                "address": f"ZIP {z5}",
                "city": city,
                "state": state,
                "zip": z5,
                "type": "commercial",
            },
            "summary": {},
            "punch_list": {"punch_list": []},
        }
        try:
            # Temporarily tighten pages if requested
            prev = os.environ.get("PAID_LOCAL_CONFIRM_MAX_PAGES")
            if max_pages is not None:
                os.environ["PAID_LOCAL_CONFIRM_MAX_PAGES"] = str(max(1, min(8, max_pages)))
            try:
                analysis = run_paid_local_confirm(
                    analysis,
                    city=city,
                    state=state,
                    zip_code=z5,
                    email=service_email,
                    skip_quota=True,
                )
            finally:
                if max_pages is not None:
                    if prev is None:
                        os.environ.pop("PAID_LOCAL_CONFIRM_MAX_PAGES", None)
                    else:
                        os.environ["PAID_LOCAL_CONFIRM_MAX_PAGES"] = prev

            analysis = attach_local_pack_from_analysis(
                analysis,
                city=city,
                state=state,
                zip_code=z5,
                order_id="seed",
                persist=True,
                record_hit=True,
            )
            lp = analysis.get("local_pack") or {}
            results.append(
                {
                    "zip": z5,
                    "status": "ok",
                    "tier": lp.get("tier"),
                    "fee_count": len(lp.get("fees") or []),
                    "portal": (lp.get("ahj") or {}).get("portal_url"),
                }
            )
        except Exception as e:
            logger.warning("seed zip %s failed: %s", z5, e)
            results.append({"zip": z5, "status": "error", "error": str(e)[:160]})

    return {"status": "ok", "seeded": len(results), "results": results}


def apply_local_pack_to_cards(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Merge analysis.local_pack into ahj_card / fee_card / gotcha_watchlist when richer."""
    if not isinstance(analysis, dict):
        return analysis
    pack = analysis.get("local_pack")
    if not isinstance(pack, dict):
        return analysis

    ahj = dict(analysis.get("ahj_card") or {})
    pahj = pack.get("ahj") or {}
    if pahj.get("portal_url") and not ahj.get("portal_url"):
        ahj["portal_url"] = pahj["portal_url"]
    if pahj.get("fees_url"):
        ahj.setdefault("fees_url", pahj["fees_url"])
    if pahj.get("name"):
        ahj.setdefault("name", pahj["name"])
    if pahj.get("phone"):
        ahj.setdefault("phone", pahj["phone"])
    if pahj.get("notes"):
        ahj.setdefault("notes", pahj["notes"])
    analysis["ahj_card"] = ahj

    fee_card = dict(analysis.get("fee_card") or {})
    if (pack.get("fees") or []) and not (fee_card.get("fees") or []):
        fee_card["fees"] = list(pack["fees"])
    if pack.get("timeline_hint"):
        fee_card.setdefault("timeline", pack["timeline_hint"])
    fee_card["local_pack_tier"] = pack.get("tier")
    analysis["fee_card"] = fee_card

    gw = dict(analysis.get("gotcha_watchlist") or {})
    if (pack.get("gotchas") or []) and not (gw.get("items") or []):
        gw["items"] = list(pack["gotchas"])
        analysis["gotcha_watchlist"] = gw

    docs = dict(analysis.get("document_checklist") or {})
    if (pack.get("documents") or []) and not (docs.get("items") or []):
        docs["items"] = [{"task": t} for t in pack["documents"]]
        analysis["document_checklist"] = docs

    return analysis
