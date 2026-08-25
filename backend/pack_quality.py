"""Pack quality gate before promote-to-library (aligned with ahj_data/plano.json)."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

# Required top-level keys on promoted AHJ records (see plano.json).
PROMOTED_REQUIRED_KEYS = (
    "ahj_id",
    "city",
    "state",
    "portal_url",
    "fees",
    "gotchas",
)


def validate_pack_for_promote(
    pack: Dict[str, Any],
    *,
    edits: Dict[str, Any] | None = None,
) -> Tuple[bool, List[str]]:
    """
    Return (ok, errors). Promote requires:
    - portal_url (pack or edits)
    - at least one fee OR gotcha
    - citation URL for fee amounts and gotchas (portal may serve as citation)
    - city + state
    """
    edits = edits or {}
    errors: List[str] = []
    if not isinstance(pack, dict):
        return False, ["Pack missing"]

    portal = str(
        edits.get("portal_url")
        or (pack.get("ahj") or {}).get("portal_url")
        or pack.get("portal_url")
        or ""
    ).strip()
    if not portal.lower().startswith("http"):
        errors.append("portal_url required (http/https)")

    fees = edits.get("fees") if isinstance(edits.get("fees"), list) else pack.get("fees") or []
    gotchas = (
        edits.get("gotchas") if isinstance(edits.get("gotchas"), list) else pack.get("gotchas") or []
    )
    fees = [f for f in fees if isinstance(f, dict)]
    gotchas = [g for g in gotchas if isinstance(g, dict)]
    if not fees and not gotchas:
        errors.append("Need at least one fee or gotcha before promote")

    for i, fee in enumerate(fees):
        label = str(fee.get("label") or "").strip()
        if not label:
            errors.append(f"fees[{i}] missing label")
        cite = str(fee.get("source_url") or fee.get("citation_url") or portal or "").strip()
        if fee.get("amount_usd") is not None and not cite.lower().startswith("http"):
            errors.append(f"fees[{i}] has amount but no citation URL")

    for i, g in enumerate(gotchas):
        title = str(g.get("title") or "").strip()
        if not title:
            errors.append(f"gotchas[{i}] missing title")
        cite = str(g.get("source_url") or g.get("citation_url") or portal or "").strip()
        if not cite.lower().startswith("http"):
            errors.append(f"gotchas[{i}] missing citation URL")

    city = str(edits.get("city") or pack.get("city") or "").strip()
    state = str(edits.get("state") or pack.get("state") or "").strip()
    if not city or not state:
        errors.append("city and state required")

    return (len(errors) == 0, errors)


def validate_promoted_record(rec: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Schema check vs plano.json-shaped promoted library records."""
    errors: List[str] = []
    if not isinstance(rec, dict):
        return False, ["Record missing"]
    for key in PROMOTED_REQUIRED_KEYS:
        if key not in rec:
            errors.append(f"missing key {key}")
    if rec.get("portal_url") and not str(rec["portal_url"]).lower().startswith("http"):
        errors.append("portal_url must be http(s)")
    fees = rec.get("fees") if isinstance(rec.get("fees"), list) else []
    gotchas = rec.get("gotchas") if isinstance(rec.get("gotchas"), list) else []
    if not fees and not gotchas:
        errors.append("promoted record needs fees or gotchas")
    for i, fee in enumerate(fees):
        if not isinstance(fee, dict):
            errors.append(f"fees[{i}] not an object")
            continue
        if not fee.get("label"):
            errors.append(f"fees[{i}] missing label")
        cite = str(fee.get("citation_url") or "").strip()
        if fee.get("amount_usd") is not None and not cite.lower().startswith("http"):
            errors.append(f"fees[{i}] amount needs citation_url")
    for i, g in enumerate(gotchas):
        if not isinstance(g, dict):
            errors.append(f"gotchas[{i}] not an object")
            continue
        if not g.get("title"):
            errors.append(f"gotchas[{i}] missing title")
        cite = str(g.get("citation_url") or "").strip()
        if not cite.lower().startswith("http"):
            errors.append(f"gotchas[{i}] missing citation_url")
    return (len(errors) == 0, errors)


def promote_readiness_score(pack: Dict[str, Any]) -> float:
    """0–1 heuristic for ops queue sorting."""
    if not isinstance(pack, dict):
        return 0.0
    score = 0.0
    portal = str((pack.get("ahj") or {}).get("portal_url") or "")
    if portal.startswith("http"):
        score += 0.4
    fees = pack.get("fees") or []
    gotchas = pack.get("gotchas") or []
    if fees:
        score += min(0.3, 0.1 * len(fees))
    if gotchas:
        score += min(0.2, 0.1 * len(gotchas))
    if pack.get("promote_candidate"):
        score += 0.1
    return round(min(1.0, score), 2)
