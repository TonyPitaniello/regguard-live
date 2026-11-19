"""
Enrich IC PDF payloads so $1,500 packages include beachhead pack depth,
not just markdown action plans.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from pdf_text import ascii_safe, markdown_to_bullets, markdown_to_plain

# Bump when PDF layout/content contract changes — forces regen on download.
PDF_FORMAT_VERSION = 13


def _library_record(city: str, state: str) -> Dict[str, Any]:
    """Curated AHJ library (checklists, fee-schedule URLs). Empty when this city has no file."""
    if (state or "").strip().upper() not in ("", "TX", "TEXAS"):
        return {}
    slug = re.sub(r"[^a-z0-9]+", "_", (city or "").strip().lower()).strip("_")
    if not slug:
        return {}
    path = Path(__file__).resolve().parent / "ahj_data" / f"{slug}.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _norm_gotcha(raw: Dict[str, Any]) -> Dict[str, Any]:
    url = str(raw.get("source_url") or raw.get("citation_url") or "").strip()
    priority = str(raw.get("priority") or raw.get("severity") or "HIGH").strip().upper()
    checklist = [str(x).strip() for x in (raw.get("checklist") or []) if str(x).strip()]
    anti = [str(x).strip() for x in (raw.get("anti_patterns") or []) if str(x).strip()]
    detail = str(raw.get("detail") or raw.get("citation_note") or "").strip()
    if not detail and checklist:
        detail = " ".join(checklist[:3])
    return {
        "id": raw.get("id") or "",
        "title": str(raw.get("title") or "").strip(),
        "detail": detail,
        "priority": priority or "HIGH",
        "checklist": checklist[:4],
        "anti_patterns": anti[:3],
        "source_url": url,
        "source_label": str(raw.get("source_label") or ("Source" if url else "Unverified")).strip(),
    }


def _merge_gotchas(pack_rows: List[Any], library_rows: List[Any]) -> List[Dict[str, Any]]:
    """Pack titles stay. Library rows add the ordinance checklist and any missing cite."""
    merged: List[Dict[str, Any]] = []
    seen = set()
    library = [_norm_gotcha(g) for g in library_rows if isinstance(g, dict)]
    for raw in pack_rows:
        if not isinstance(raw, dict):
            continue
        row = _norm_gotcha(raw)
        if not row["title"] or not row["source_url"]:
            continue
        key = row["title"].lower()
        if key in seen:
            continue
        for lib in library:
            if not lib["title"]:
                continue
            same = lib["title"].lower() == key or (
                lib.get("id") and raw.get("id") and str(lib.get("id")) == str(raw.get("id"))
            )
            if not same:
                continue
            if lib["checklist"] and not row["checklist"]:
                row["checklist"] = lib["checklist"]
            if lib["anti_patterns"] and not row["anti_patterns"]:
                row["anti_patterns"] = lib["anti_patterns"]
            if lib["detail"] and len(lib["detail"]) > len(row["detail"]):
                row["detail"] = lib["detail"]
            break
        seen.add(key)
        merged.append(row)
    for lib in library:
        key = lib["title"].lower()
        if not lib["title"] or not lib["source_url"] or key in seen:
            continue
        seen.add(key)
        merged.append(lib)
        if len(merged) >= 8:
            break
    return merged[:8]


def _same_topic(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    ta = str(a.get("title") or "").lower()
    tb = str(b.get("title") or "").lower()
    if not ta or not tb:
        return False
    if ta == tb:
        return True
    ida, idb = str(a.get("id") or ""), str(b.get("id") or "")
    if ida and idb and ida == idb:
        return True
    nums_a = set(re.findall(r"\d+\.\d+", ta))
    nums_b = set(re.findall(r"\d+\.\d+", tb))
    if nums_a and nums_a & nums_b:
        return True
    return "ground" in ta and "ground" in tb


def _overlay_gotchas(existing: List[Any], library_rows: List[Any]) -> List[Dict[str, Any]]:
    """Keep the pack titles. Pull ordinance checklists and CRITICAL severity off the library."""
    libs = [_norm_gotcha(g) for g in library_rows if isinstance(g, dict)]
    used: set = set()
    out: List[Dict[str, Any]] = []
    for raw in existing:
        if not isinstance(raw, dict):
            continue
        row = dict(raw)
        if not row.get("priority") and row.get("severity"):
            row["priority"] = str(row.get("severity")).strip().upper()
        for i, lib in enumerate(libs):
            if not _same_topic(row, lib):
                continue
            if lib["checklist"] and not row.get("checklist"):
                row["checklist"] = lib["checklist"]
            if lib["anti_patterns"] and not row.get("anti_patterns"):
                row["anti_patterns"] = lib["anti_patterns"]
            pri = str(row.get("priority") or "").upper()
            if lib["priority"] == "CRITICAL" and pri != "CRITICAL":
                row["priority"] = "CRITICAL"
            elif not pri:
                row["priority"] = lib["priority"]
            if lib["source_url"] and "municode" in lib["source_url"]:
                row["source_url"] = lib["source_url"]
                row["source_label"] = lib["source_label"] or "Source"
            if lib["detail"] and len(lib["detail"]) > len(str(row.get("detail") or "")):
                row["detail"] = lib["detail"]
            used.add(i)
            break
        out.append(row)
    for i, lib in enumerate(libs):
        if i in used or not lib["title"] or not lib["source_url"]:
            continue
        if any(_same_topic(row, lib) for row in out):
            continue
        out.append(lib)
        if len(out) >= 8:
            break
    return out[:8]


def _fee_rows(fees: List[Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for fee in fees:
        if not isinstance(fee, dict):
            continue
        url = str(fee.get("source_url") or fee.get("citation_url") or "").strip()
        label = str(fee.get("label") or fee.get("name") or "").strip()
        if not label or not url:
            continue
        rows.append(
            {
                "label": label,
                "trade": fee.get("trade") or "",
                "amount_usd": fee.get("amount_usd"),
                "amount_requires_schedule": bool(fee.get("amount_requires_schedule"))
                or fee.get("amount_usd") in (None, ""),
                "detail": str(fee.get("detail") or fee.get("citation_note") or "Confirm on the official schedule."),
                "source_url": url,
                "source_label": fee.get("source_label") or "Source",
                "verified": bool(fee.get("verified")),
            }
        )
    return rows


def _refresh_stale_contingency(data: Dict[str, Any], items: List[Any]) -> None:
    """
    The delivery prep band can be computed before city CRITICAL rows are visible.
    Recompute from those rows with the existing planning-aid formula. No dollar total.
    A band that did not come from that formula is left alone.
    """
    crit = sum(
        1
        for g in items
        if isinstance(g, dict) and str(g.get("priority") or g.get("severity") or "").upper() == "CRITICAL"
    )
    high = sum(
        1
        for g in items
        if isinstance(g, dict) and str(g.get("priority") or g.get("severity") or "").upper() == "HIGH"
    )
    band = data.get("contingency_band") if isinstance(data.get("contingency_band"), dict) else {}
    drivers = band.get("drivers") if isinstance(band.get("drivers"), dict) else {}
    if not crit or "critical_items" not in drivers:
        return
    if crit <= int(drivers.get("critical_items") or 0):
        return
    from arbitrage_enrichment import _build_contingency, _project_is_data_center

    data["contingency_band"] = _build_contingency(
        crit,
        high,
        int(drivers.get("unverified_items") or 0),
        0.0,
        is_dc=_project_is_data_center(data),
        cost_verified=False,
    )


def _attach_beachhead_depth(data: Dict[str, Any], pack: Dict[str, Any]) -> None:
    """
    Put the curated city pack on the fields the $1,500 boardroom actually reads.

    A live scout that already brought gotchas, fees, or a stamp is left in place.
    Library rows add the ordinance checklist when the pack line does not have one.
    No permit total is invented here. A stale planning-aid percent is recomputed
    from the Critical count; a band the formula did not write is left alone.
    """
    pi = data.get("project_info") if isinstance(data.get("project_info"), dict) else {}
    library = _library_record(str(pi.get("city") or ""), str(pi.get("state") or ""))
    library_gotchas = list(library.get("gotchas") or [])
    gotchas = _merge_gotchas(list(pack.get("gotchas") or []), library_gotchas)

    local = data.get("local_pack") if isinstance(data.get("local_pack"), dict) else {}
    if local.get("gotchas") and library_gotchas:
        data["local_pack"] = {**local, "gotchas": _overlay_gotchas(local.get("gotchas") or [], library_gotchas)}
        local = data["local_pack"]
    elif gotchas and not local.get("gotchas"):
        data["local_pack"] = {
            **local,
            "gotchas": gotchas,
            "fees": local.get("fees") or pack.get("fees") or [],
            "documents": local.get("documents") or pack.get("documents") or [],
            "inspection_sequence": local.get("inspection_sequence") or pack.get("inspection_sequence") or [],
            "ahj": local.get("ahj") or pack.get("ahj") or {},
            "timeline_hint": local.get("timeline_hint") or pack.get("timeline_hint") or "",
        }
        local = data["local_pack"]

    watch = data.get("gotcha_watchlist") if isinstance(data.get("gotcha_watchlist"), dict) else {}
    if watch.get("items") and library_gotchas:
        data["gotcha_watchlist"] = {**watch, "items": _overlay_gotchas(watch.get("items") or [], library_gotchas)}
    elif gotchas and not watch.get("items"):
        data["gotcha_watchlist"] = {"items": gotchas}
    watch_items = (data.get("gotcha_watchlist") or {}).get("items") or gotchas
    if not isinstance(watch_items, list):
        watch_items = []
    _refresh_stale_contingency(data, watch_items)

    upgraded: List[Dict[str, Any]] = []
    for killer in data.get("margin_killers") or []:
        if not isinstance(killer, dict):
            continue
        if "no critical" in str(killer.get("title") or "").lower():
            continue
        row = dict(killer)
        for item in watch_items:
            if not isinstance(item, dict) or not _same_topic(row, item):
                continue
            pri = str(item.get("priority") or item.get("severity") or "").upper()
            if pri == "CRITICAL" or not row.get("priority"):
                row["priority"] = pri or row.get("priority")
            if item.get("checklist") and not row.get("checklist"):
                row["checklist"] = item.get("checklist")
            if item.get("anti_patterns") and not row.get("anti_patterns"):
                row["anti_patterns"] = item.get("anti_patterns")
            if item.get("source_url") and "municode" in str(item.get("source_url")):
                row["source_url"] = item.get("source_url")
                row["source_label"] = item.get("source_label") or row.get("source_label")
            if item.get("detail") and len(str(item.get("detail"))) > len(str(row.get("detail") or "")):
                row["detail"] = item.get("detail")
            break
        upgraded.append(row)
    for item in watch_items:
        if not isinstance(item, dict):
            continue
        pri = str(item.get("priority") or item.get("severity") or "").upper()
        if pri not in ("CRITICAL", "HIGH"):
            continue
        if any(_same_topic(row, item) for row in upgraded):
            continue
        upgraded.append(
            {
                "title": item.get("title"),
                "detail": item.get("detail"),
                "priority": pri,
                "checklist": item.get("checklist") or [],
                "anti_patterns": item.get("anti_patterns") or [],
                "source_url": item.get("source_url"),
                "source_label": item.get("source_label"),
            }
        )
        if len(upgraded) >= 8:
            break
    if upgraded:
        data["margin_killers"] = upgraded

    has_critical = any(
        str(g.get("priority") or g.get("severity") or "").upper() == "CRITICAL"
        for g in watch_items
        if isinstance(g, dict)
    ) or any(g.get("priority") == "CRITICAL" for g in gotchas)

    fee_card = data.get("fee_card") if isinstance(data.get("fee_card"), dict) else {}
    library_fees = [f for f in (library.get("fees") or []) if isinstance(f, dict)]
    pack_fees = [f for f in (pack.get("fees") or []) if isinstance(f, dict)]
    lib_rows = _fee_rows(library_fees)
    existing_fees = [f for f in (fee_card.get("fees") or []) if isinstance(f, dict)]
    if not existing_fees:
        existing_fees = [f for f in ((data.get("local_pack") or {}).get("fees") or pack_fees) if isinstance(f, dict)]
    have = {str(f.get("label") or f.get("name") or "").strip().lower() for f in existing_fees}
    extra = [row for row in lib_rows if row["label"].lower() not in have]
    rows = (existing_fees + extra)[:8] if existing_fees else lib_rows[:8]
    # Library citation notes win when the same label is already on the card with a thinner note.
    by_label = {row["label"].lower(): row for row in lib_rows}
    filled: List[Dict[str, Any]] = []
    for fee in rows:
        label = str(fee.get("label") or fee.get("name") or "")
        lib = by_label.get(label.lower())
        if lib and len(lib.get("detail") or "") > len(str(fee.get("detail") or fee.get("citation_note") or "")):
            fee = {**fee, "detail": lib["detail"], "amount_usd": fee.get("amount_usd", lib.get("amount_usd"))}
        filled.append(fee)
    if filled:
        data["fee_card"] = {**fee_card, "fees": filled}
        local_now = data.get("local_pack") if isinstance(data.get("local_pack"), dict) else {}
        data["local_pack"] = {**local_now, "fees": filled}

    insp = data.get("inspection_sequence_card") if isinstance(data.get("inspection_sequence_card"), dict) else {}
    steps = list(insp.get("steps") or []) or list(
        (data.get("local_pack") or {}).get("inspection_sequence") or pack.get("inspection_sequence") or []
    )
    if steps and not insp.get("steps"):
        data["inspection_sequence_card"] = {"steps": [str(s) for s in steps[:8]]}

    docs = data.get("document_checklist") if isinstance(data.get("document_checklist"), dict) else {}
    doc_items = list(docs.get("items") or [])
    if not doc_items:
        raw_docs = (data.get("local_pack") or {}).get("documents") or pack.get("documents") or []
        doc_items = [{"task": str(d), "note": "Confirm the exact list with the AHJ"} for d in raw_docs[:8] if str(d).strip()]
        if doc_items:
            data["document_checklist"] = {"items": doc_items}

    ahj_card = data.get("ahj_card") if isinstance(data.get("ahj_card"), dict) else {}
    pack_ahj = pack.get("ahj") if isinstance(pack.get("ahj"), dict) else {}
    if pack_ahj and not ahj_card.get("portal_url"):
        data["ahj_card"] = {
            **pack_ahj,
            **{k: v for k, v in ahj_card.items() if v},
            "fees_url": ahj_card.get("fees_url") or library.get("fees_url") or pack_ahj.get("fees_url") or "",
            "portal_url": ahj_card.get("portal_url") or library.get("portal_url") or pack_ahj.get("portal_url") or "",
        }
        ahj_card = data["ahj_card"]
    lib_fees_url = str(library.get("fees_url") or "")
    current_fees_url = str(ahj_card.get("fees_url") or "")
    if lib_fees_url.endswith(".pdf") and not current_fees_url.endswith(".pdf"):
        data["ahj_card"] = {**ahj_card, "fees_url": lib_fees_url}

    stamp = data.get("regguard_stamp") if isinstance(data.get("regguard_stamp"), dict) else {}
    incoming_grade = str(stamp.get("grade") or data.get("stamp_grade") or "").upper()
    if data.get("margin_killers") and has_critical and incoming_grade in ("", "PASS", "CLEAR", "CAUTION"):
        data["regguard_stamp"] = {
            "grade": "FAIL",
            "headline": (
                "HOLD — elevated pre-bid risk. This is not a rejection of the site. "
                "Clear the sourced drivers below before locking a number."
            ),
            "drivers": [
                {
                    "severity": "HOLD",
                    "label": k.get("title"),
                    "detail": k.get("detail"),
                    "source_url": k.get("source_url"),
                }
                for k in (data.get("margin_killers") or [])[:3]
                if isinstance(k, dict)
            ],
        }
        data["stamp_grade"] = "FAIL"


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

    if pack:
        _attach_beachhead_depth(data, pack)

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
    # Append IC ultralocal killers that aren't already present
    ultra = data.get("ultralocal_scout") if isinstance(data.get("ultralocal_scout"), dict) else {}
    if ultra.get("enabled"):
        existing_titles = {str(g.get("title") or "").lower() for g in gotchas}
        for k in data.get("margin_killers") or []:
            if not isinstance(k, dict):
                continue
            if not k.get("ultralocal_bucket"):
                continue
            t = str(k.get("title") or "").lower()
            if t and t not in existing_titles:
                gotchas.append(k)
                existing_titles.add(t)

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

    # Also pull live gotcha_watchlist (often richer than city-pack gotchas)
    watch = data.get("gotcha_watchlist") if isinstance(data.get("gotcha_watchlist"), dict) else {}
    existing = {x.split(":")[0].lower() for x in gotcha_lines}
    for g in (watch.get("items") or [])[:12]:
        if not isinstance(g, dict):
            continue
        title = ascii_safe(g.get("title") or "Gotcha", 100)
        key = f"[{str(g.get('priority') or '').upper()}] {title}".lower()
        if key in existing or title.lower() in existing:
            continue
        detail = markdown_to_plain(g.get("detail") or "", limit=220)
        cite = ascii_safe(g.get("source_url") or portal, 90)
        pri = str(g.get("priority") or "").upper()
        gotcha_lines.append(f"[{pri}] {title}: {detail}  |  {cite}" if pri else f"{title}: {detail}  |  {cite}")
        existing.add(key)

    # Punch lines for Research Memo (app shows these; PDF was missing them)
    punch_lines: List[str] = []
    for item in ((data.get("punch_list") or {}).get("punch_list") or [])[:20]:
        if not isinstance(item, dict):
            continue
        task = markdown_to_plain(item.get("task") or item.get("title") or "", limit=160)
        if not task:
            continue
        pri = str(item.get("priority") or "").upper()
        url = ascii_safe(item.get("source_url") or "", 90)
        punch_lines.append(f"[{pri}] {task}" + (f"  |  {url}" if url else ""))

    # Deep plan bullets (pro_summary_markdown) — truncated for PDF
    plan_lines: List[str] = []
    summary_md = data.get("pro_summary_markdown") or ""
    if summary_md:
        plan_lines = markdown_to_bullets(summary_md, limit=24)

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
        "ultralocal": bool(ultra.get("enabled")) if isinstance(ultra, dict) else bool((data.get("scout_locality_depth") or "") == "local_ultralocal"),
        "pack_key": pack.get("pack_key") or "",
        "stamp_grade": stamp.get("grade") or "",
        "fee_lines": fee_lines,
        "gotcha_lines": gotcha_lines,
        "punch_lines": punch_lines,
        "plan_lines": plan_lines,
        "depth_badge": ascii_safe(data.get("depth_badge") or "", 120),
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
    # Always attach a human-readable radar card for IC results (not raw JSON API).
    if not isinstance(data.get("moratorium_radar"), dict) or not data["moratorium_radar"].get("metros"):
        try:
            from dc_diligence import build_moratorium_radar_card

            data["moratorium_radar"] = build_moratorium_radar_card(data)
        except Exception:
            pass
    try:
        from ic_buyer_brief import apply_ic_buyer_brief

        data = apply_ic_buyer_brief(data)
    except Exception:
        pass
    return data
