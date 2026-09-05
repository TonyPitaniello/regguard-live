"""
Enrich IC PDF payloads so $1,500 packages include beachhead pack depth,
not just markdown action plans.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pdf_text import ascii_safe, markdown_to_plain

# Bump when PDF layout/content contract changes — forces regen on download.
PDF_FORMAT_VERSION = 3


def enrich_analysis_for_ic_pdfs(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Attach pdf_pack / pdf_sections used by ResearchMemo + Punch List."""
    data = dict(analysis or {})
    pi = data.get("project_info") or {}
    city = str(pi.get("city") or "")
    state = str(pi.get("state") or "")
    zip_code = str(pi.get("zip") or "")

    pack: Dict[str, Any] = {}
    try:
        from city_packs import resolve_city_pack

        resolved = resolve_city_pack(city, state, zip_code)
        if resolved:
            pack = resolved
    except Exception:
        pack = {}

    # Prefer live local_pack / fee_card when present
    local = data.get("local_pack") if isinstance(data.get("local_pack"), dict) else {}
    fee_card = data.get("fee_card") if isinstance(data.get("fee_card"), dict) else {}
    ahj_card = data.get("ahj_card") if isinstance(data.get("ahj_card"), dict) else {}

    fees: List[Dict[str, Any]] = []
    for src in (
        local.get("fees"),
        fee_card.get("fees"),
        pack.get("fees"),
        (data.get("paid_local") or {}).get("fees"),
    ):
        if isinstance(src, list) and src:
            fees = [f for f in src if isinstance(f, dict)]
            break

    gotchas: List[Dict[str, Any]] = []
    for src in (local.get("gotchas"), pack.get("gotchas"), data.get("margin_killers")):
        if isinstance(src, list) and src:
            gotchas = [g for g in src if isinstance(g, dict)]
            break

    ahj = pack.get("ahj") if isinstance(pack.get("ahj"), dict) else {}
    local_ahj = local.get("ahj") if isinstance(local.get("ahj"), dict) else {}
    portal = str(
        ahj_card.get("portal_url")
        or ahj.get("portal_url")
        or local_ahj.get("portal_url")
        or ""
    )
    fees_url = str(
        ahj_card.get("fees_url")
        or ahj.get("fees_url")
        or local_ahj.get("fees_url")
        or ""
    )
    ahj_name = (
        ahj_card.get("name")
        or ahj.get("name")
        or f"{city}, {state}".strip(", ")
        or "Local AHJ"
    )

    stamp = data.get("regguard_stamp") if isinstance(data.get("regguard_stamp"), dict) else {}
    band = data.get("contingency_band") if isinstance(data.get("contingency_band"), dict) else {}
    parallel = data.get("parallel_clocks") if isinstance(data.get("parallel_clocks"), dict) else {}
    radar = data.get("moratorium_radar") if isinstance(data.get("moratorium_radar"), dict) else {}
    power = data.get("power_path") if isinstance(data.get("power_path"), dict) else {}
    vertical = data.get("vertical_playbook") if isinstance(data.get("vertical_playbook"), dict) else {}
    sources = list(data.get("pro_source_urls") or [])[:12]

    fee_lines: List[str] = []
    for f in fees[:8]:
        label = ascii_safe(f.get("label") or "Fee", 80)
        amt = f.get("amount_usd")
        cite = ascii_safe(f.get("citation_url") or f.get("source_url") or fees_url or portal, 90)
        if amt is not None:
            try:
                fee_lines.append(f"{label}: ${float(amt):,.2f}  |  {cite}")
            except (TypeError, ValueError):
                fee_lines.append(f"{label}: confirm schedule  |  {cite}")
        else:
            fee_lines.append(f"{label}: confirm on official schedule  |  {cite}")

    gotcha_lines: List[str] = []
    for g in gotchas[:10]:
        title = ascii_safe(g.get("title") or "Gotcha", 100)
        pri = str(g.get("priority") or "").upper()
        detail = markdown_to_plain(
            g.get("detail") or " ".join(str(x) for x in (g.get("checklist") or [])[:3]),
            limit=220,
        )
        cite = ascii_safe(g.get("citation_url") or g.get("source_url") or portal, 90)
        prefix = f"[{pri}] " if pri else ""
        gotcha_lines.append(f"{prefix}{title}: {detail}  |  {cite}")

    clock_lines: List[str] = []
    for c in (parallel.get("clocks") or [])[:5]:
        if not isinstance(c, dict):
            continue
        clock_lines.append(
            ascii_safe(
                f"{c.get('label') or c.get('track')}: {c.get('status') or ''} ({c.get('owner') or ''})",
                200,
            )
        )

    vertical_lines: List[str] = []
    for it in (vertical.get("items") or [])[:12]:
        if not isinstance(it, dict):
            continue
        status = str(it.get("status") or it.get("state") or "confirm")
        vertical_lines.append(
            ascii_safe(f"[{status}] {it.get('label') or it.get('title') or 'Item'}", 180)
        )

    source_lines = [ascii_safe(u, 120) for u in sources if u]

    data["pdf_format_version"] = PDF_FORMAT_VERSION
    data["pdf_pack"] = {
        "ahj_name": ascii_safe(ahj_name, 80),
        "portal_url": ascii_safe(portal, 120),
        "fees_url": ascii_safe(fees_url, 120),
        "beachhead": bool(pack),
        "pack_key": pack.get("pack_key") or "",
        "stamp_grade": stamp.get("grade") or "",
        "fee_lines": fee_lines,
        "gotcha_lines": gotcha_lines,
        "clock_lines": clock_lines or [
            "AHJ / building permits: confirm portal + hearings before bid",
            "Utility interconnection / large-load: parallel clock (not run by RegGuard)",
            "Federal / FAST-41: counsel-led if scale qualifies",
        ],
        "vertical_lines": vertical_lines,
        "source_lines": source_lines,
        "radar_headline": ascii_safe(radar.get("headline") or "", 160),
        "power_headline": ascii_safe(power.get("headline") or "", 160),
        "contingency": band,
        "inspection_sequence": list(
            pack.get("inspection_sequence")
            or local.get("inspection_sequence")
            or []
        )[:8],
    }
    return data
