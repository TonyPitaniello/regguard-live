"""
AHJ catalog for DFW + Austin — citeable fees, gotchas, inspection sequences.

Single source of truth loaded from ``ahj_data/*.json``.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent / "ahj_data"


@lru_cache(maxsize=1)
def load_ahj_catalog() -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if not _DATA_DIR.exists():
        return records
    for path in sorted(_DATA_DIR.glob("*.json")):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception as e:
            logger.warning(f"Failed loading AHJ data {path}: {e}")
    # Runtime promotes (ops) — same schema as ahj_data/
    try:
        from local_pack_store import list_promoted

        for rec in list_promoted():
            if not isinstance(rec, dict) or not rec.get("ahj_id"):
                continue
            # Prefer git-committed over promote on same ahj_id
            if any(r.get("ahj_id") == rec.get("ahj_id") for r in records):
                continue
            records.append(rec)
    except Exception as e:
        logger.warning("promoted AHJ load failed: %s", e)
    return records


def _city_matches_record(city: str, rec: Dict[str, Any]) -> bool:
    c = (city or "").strip().lower()
    if not c:
        return False
    aliases = [a.lower() for a in (rec.get("aliases") or [])]
    return c == (rec.get("city") or "").lower() or c in aliases


def lookup_ahj(
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Resolve AHJ record by ZIP or city+state.

    When typed city conflicts with ZIP catalog city (e.g. Richardson + 75075),
    prefer the ZIP beachhead record — ZIP is authoritative for curated packs —
    and callers should stamp an identity warning for the receipt/UI.
    """
    z = (zip_code or "").strip()
    c = (city or "").strip().lower()
    s = (state or "").strip().upper()
    catalog = load_ahj_catalog()

    zip_hit: Optional[Dict[str, Any]] = None
    if len(z) >= 5:
        z5 = z[:5]
        for rec in catalog:
            if z5 in (rec.get("zips") or []):
                zip_hit = rec
                break

    city_hit: Optional[Dict[str, Any]] = None
    if c and s in ("TX", "TEXAS", ""):
        for rec in catalog:
            if _city_matches_record(c, rec):
                if not s or s in ("TX", "TEXAS") or s == (rec.get("state") or "").upper():
                    city_hit = rec
                    break

    if zip_hit and city_hit:
        if zip_hit.get("ahj_id") == city_hit.get("ahj_id"):
            return zip_hit
        # Conflict: ZIP wins for beachhead citeable fees (identity stamped elsewhere)
        return zip_hit
    if zip_hit:
        return zip_hit
    if city_hit:
        return city_hit
    return None


def ahj_identity_conflict(
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """If typed city ≠ ZIP catalog city, return a warning payload for UI/receipt."""
    z = (zip_code or "").strip()
    c = (city or "").strip()
    if len(z) < 5 or not c:
        return None
    catalog = load_ahj_catalog()
    z5 = z[:5]
    zip_hit = None
    for rec in catalog:
        if z5 in (rec.get("zips") or []):
            zip_hit = rec
            break
    if not zip_hit:
        return None
    if _city_matches_record(c, zip_hit):
        return None
    return {
        "conflict": True,
        "typed_city": c,
        "resolved_city": zip_hit.get("city"),
        "resolved_ahj_id": zip_hit.get("ahj_id"),
        "zip": z5,
        "note": (
            f"ZIP {z5} maps to {zip_hit.get('city')} AHJ citeable fees/gotchas. "
            f"Typed city was {c}. Confirm which building department owns this site before bid."
        ),
    }


def format_fee_lines(record: Dict[str, Any]) -> List[str]:
    """Human lines for digests / prompts — every fee cites a URL."""
    lines: List[str] = []
    for fee in record.get("fees") or []:
        label = fee.get("label") or "Permit fee"
        url = fee.get("citation_url") or record.get("portal_url") or ""
        note = fee.get("citation_note") or "Confirm with AHJ."
        amount = fee.get("amount_usd")
        if amount is None or fee.get("amount_requires_schedule"):
            lines.append(
                f"- **{label}:** amount must be taken from official schedule — cite {url}. {note}"
            )
        else:
            comps = fee.get("components") or []
            comp_bit = ""
            if comps:
                parts = [f"${float(c['amount_usd']):.2f} {c.get('label', '')}".strip() for c in comps]
                comp_bit = " (" + " + ".join(parts) + ")"
            lines.append(
                f"- **{label}:** **${float(amount):.2f}**{comp_bit} — source: {url}. {note}"
            )
    return lines


def format_gotcha_lines(record: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    for g in record.get("gotchas") or []:
        title = g.get("title") or g.get("id")
        url = g.get("citation_url") or ""
        checks = "; ".join(g.get("checklist") or [])
        anti = "; ".join(g.get("anti_patterns") or [])
        bit = f"- **MANDATORY GOTCHA: {title}** — {checks}"
        if anti:
            bit += f" Avoid: {anti}."
        if url:
            bit += f" Cite: {url}."
        lines.append(bit)
    return lines


def format_inspection_sequence(record: Dict[str, Any]) -> List[str]:
    return [str(x) for x in (record.get("inspection_sequence") or [])]


def citation_urls(record: Dict[str, Any]) -> List[str]:
    urls: List[str] = []
    seen = set()
    for fee in record.get("fees") or []:
        u = (fee.get("citation_url") or "").strip()
        if u and u not in seen:
            urls.append(u)
            seen.add(u)
    for g in record.get("gotchas") or []:
        u = (g.get("citation_url") or "").strip()
        if u and u not in seen:
            urls.append(u)
            seen.add(u)
    portal = (record.get("portal_url") or "").strip()
    if portal and portal not in seen:
        urls.append(portal)
    od = record.get("open_data") or {}
    if od.get("socrata_url") and od["socrata_url"] not in seen:
        urls.append(od["socrata_url"])
    return urls


def digest_ahj_block(
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Structured block for research_memo digest + Claude citation requirements."""
    rec = lookup_ahj(city, state, zip_code)
    if not rec:
        return {}
    fees = rec.get("fees") or []
    verified_amounts = [
        f for f in fees if f.get("verified") and f.get("amount_usd") is not None and not f.get("amount_requires_schedule")
    ]
    return {
        "ahj_id": rec.get("ahj_id"),
        "ahj_city": rec.get("city"),
        "ahj_state": rec.get("state"),
        "ahj_fee_table": fees,
        "ahj_fee_lines": format_fee_lines(rec),
        "ahj_gotchas": rec.get("gotchas") or [],
        "ahj_gotcha_lines": format_gotcha_lines(rec),
        "ahj_inspection_sequence": format_inspection_sequence(rec),
        "ahj_citation_urls": citation_urls(rec),
        "ahj_portal_url": rec.get("portal_url"),
        "ahj_design_criteria_url": rec.get("design_criteria_url"),
        "ahj_citation_required": True,
        "ahj_verified_fee_count": len(verified_amounts),
        "ahj_fee_rule": (
            "CITATION REQUIRED: Under **### Permit Costs**, list every fee from ``ahj_fee_lines`` "
            "with the dollar amount (when provided) AND the citation URL. "
            "Do not invent AHJ fees that are not in ``ahj_fee_table``. "
            "If amount_requires_schedule is true, tell the contractor to pull the live schedule from the URL — do not invent dollars."
        ),
    }


def enrich_analysis_with_ahj(
    analysis: Dict[str, Any],
    *,
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Attach AHJ fee/inspection data to free-trial style analysis payloads.
    Marks cost_verified True only when catalog has a concrete verified amount.
    """
    project = analysis.get("project_info") or {}
    city = city or project.get("city")
    state = state or project.get("state")
    zip_code = zip_code or project.get("zip")
    block = digest_ahj_block(city, state, zip_code)
    if not block:
        return analysis

    analysis = dict(analysis)
    analysis["ahj"] = block
    analysis["source_urls"] = list(
        dict.fromkeys((analysis.get("source_urls") or []) + (block.get("ahj_citation_urls") or []))
    )

    # Inject citeable punch items for verified fees
    punch = dict(analysis.get("punch_list") or {})
    items = list(punch.get("punch_list") or [])
    rec = lookup_ahj(city, state, zip_code)
    if rec:
        for fee in rec.get("fees") or []:
            if fee.get("amount_usd") is None or fee.get("amount_requires_schedule"):
                items.insert(
                    0,
                    {
                        "priority": "HIGH",
                        "task": f"Pull live fee schedule: {fee.get('label')} — {fee.get('citation_url')}",
                        "responsible_party": "Project owner / permitting lead",
                        "timeline": "Week 1",
                        "estimated_cost": None,
                        "cost_verified": False,
                        "source_url": fee.get("citation_url"),
                        "source_label": fee.get("label"),
                        "notes": fee.get("citation_note") or "Citation required — do not invent dollars",
                    },
                )
            else:
                items.insert(
                    0,
                    {
                        "priority": "HIGH",
                        "task": f"Budget {fee.get('label')}: ${float(fee['amount_usd']):.2f}",
                        "responsible_party": "Project owner / permitting lead",
                        "timeline": "Week 1",
                        "estimated_cost": float(fee["amount_usd"]),
                        "cost_verified": True,
                        "source_url": fee.get("citation_url"),
                        "source_label": fee.get("label"),
                        "notes": fee.get("citation_note") or "",
                    },
                )
        punch["punch_list"] = items
        punch["inspection_sequence"] = format_inspection_sequence(rec)
        punch["ahj_fee_lines"] = format_fee_lines(rec)
        # Recompute cost if we added verified fees
        verified_total = sum(
            float(i["estimated_cost"])
            for i in items
            if isinstance(i.get("estimated_cost"), (int, float)) and i.get("cost_verified")
        )
        if verified_total:
            punch["estimated_total_cost"] = verified_total + sum(
                float(i.get("estimated_cost") or 0)
                for i in items
                if not i.get("cost_verified") and isinstance(i.get("estimated_cost"), (int, float))
            )
            # Prefer verified catalog total for summary when present
            analysis.setdefault("summary", {})
            analysis["summary"]["ahj_verified_fee_total_usd"] = verified_total
            analysis["summary"]["cost_verified"] = True
            # Keep honesty: only catalog portion verified; overall still may be mixed
            honesty = dict(analysis.get("honesty") or {})
            honesty["cost_verified"] = bool(verified_total)
            honesty["ahj_catalog"] = block.get("ahj_id")
            analysis["honesty"] = honesty
        analysis["punch_list"] = punch

    analysis.setdefault("summary", {})["ahj_id"] = block.get("ahj_id")
    analysis["summary"]["inspection_sequence"] = block.get("ahj_inspection_sequence")
    return analysis


def scout_extras_for(city: str, state: str, zip_code: str = "") -> Dict[str, List[str]]:
    rec = lookup_ahj(city, state, zip_code)
    if not rec:
        return {"permits": [], "codes": []}
    extras = rec.get("scout_query_extras") or {}
    return {
        "permits": list(extras.get("permits") or []),
        "codes": list(extras.get("codes") or []),
    }
