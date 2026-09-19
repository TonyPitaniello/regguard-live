"""Citation honesty: SOURCE (parcel/scout verified) vs LINK (portal URL) vs Unverified."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

FAST41_COVERED = "https://www.permits.performance.gov/projects/fast-41-covered"
FAST41_TRANSPARENCY = "https://www.permits.performance.gov/projects/transparency-projects"
ERCOT_LOAD = "https://www.ercot.com/mktrules/guides/loadinterconnection"
ERCOT_QUEUE = "https://www.ercot.com/services/informational/ercot-ic-queue/"
NWI_MAPPER = "https://www.fws.gov/program/national-wetlands-inventory/wetlands-mapper"
IPAC = "https://ipac.ecosphere.fws.gov/"
FEMA_MSC_HOME = "https://msc.fema.gov/portal/home"
EPA_NEPA = "https://www.epa.gov/nepa"
EPA_NPDES = "https://www.epa.gov/npdes"
TCEQ = "https://www.tceq.texas.gov/"


def _http(url: Optional[str]) -> str:
    u = str(url or "").strip()
    return u if u.lower().startswith("http") else ""


def _pi_coords(analysis: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    pi = analysis.get("project_info") if isinstance(analysis.get("project_info"), dict) else {}
    nested = pi.get("coordinates") if isinstance(pi.get("coordinates"), dict) else {}
    pairs = [
        (analysis.get("latitude"), analysis.get("longitude")),
        (analysis.get("lat"), analysis.get("lng")),
        (pi.get("lat"), pi.get("lng")),
        (pi.get("latitude"), pi.get("longitude")),
        (nested.get("latitude"), nested.get("longitude")),
        (nested.get("lat"), nested.get("lng")),
    ]
    for la, ln in pairs:
        try:
            lat = float(la)
            lng = float(ln)
        except (TypeError, ValueError):
            continue
        if abs(lat) < 1e-6 and abs(lng) < 1e-6:
            continue
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            return lat, lng
    return None, None


def fema_msc_pin_url(lat: Optional[float], lng: Optional[float]) -> str:
    if lat is None or lng is None:
        return FEMA_MSC_HOME
    return f"https://msc.fema.gov/portal/search?addressAscii={lat}%2C{lng}"


def _ahj_portal(analysis: Dict[str, Any]) -> Tuple[str, str]:
    card = analysis.get("ahj_card") if isinstance(analysis.get("ahj_card"), dict) else {}
    ahj = analysis.get("ahj") if isinstance(analysis.get("ahj"), dict) else {}
    url = _http(card.get("portal_url") or ahj.get("ahj_portal_url") or (analysis.get("paid_local") or {}).get("portal_url"))
    name = str(card.get("name") or ahj.get("name") or "AHJ portal").strip() or "AHJ portal"
    return url, name


def confirm_link_for_task(
    task: str,
    *,
    analysis: Dict[str, Any],
    existing_url: str = "",
) -> Optional[Tuple[str, str]]:
    """Official page to confirm an Unverified line. Never a SOURCE claim."""
    if _http(existing_url):
        return None
    t = (task or "").lower()
    pi = analysis.get("project_info") if isinstance(analysis.get("project_info"), dict) else {}
    st = str(pi.get("state") or "").strip().upper()
    lat, lng = _pi_coords(analysis)
    portal, portal_name = _ahj_portal(analysis)

    if "fast-41" in t or "fast 41" in t or "permitting council" in t:
        return FAST41_COVERED if "100 mw" in t or "gate" in t else FAST41_TRANSPARENCY, (
            "FAST-41 covered projects" if "100 mw" in t or "gate" in t else "Permitting Council Transparency Projects"
        )
    if any(k in t for k in ("interconnection", "tdsp", "ercot", "large-load", "large load", "iso")):
        if st in ("TX", "TEXAS"):
            return ERCOT_LOAD if "large" in t or "tdsp" in t or "iso" in t else ERCOT_QUEUE, (
                "ERCOT large-load interconnection" if "large" in t or "tdsp" in t else "ERCOT interconnection queue"
            )
        return FAST41_TRANSPARENCY, "Permitting Council (federal screen)"
    if any(k in t for k in ("wetland", "nwi")):
        return NWI_MAPPER, "NWI Wetlands Mapper"
    if any(k in t for k in ("flood", "firm", "sfha", "fema")):
        return fema_msc_pin_url(lat, lng), "FEMA MSC"
    if any(k in t for k in ("endangered", "species", "ipac", "habitat")):
        return IPAC, "USFWS IPaC"
    if "nepa" in t:
        return EPA_NEPA, "EPA NEPA"
    if "npdes" in t or "stormwater" in t:
        return EPA_NPDES, "EPA NPDES"
    if any(k in t for k in ("water withdrawal", "consumptive", "tceq")) and st in ("TX", "TEXAS"):
        return TCEQ, "TCEQ"
    if portal and any(k in t for k in ("permit", "ahj", "municipal", "inspection", "fee", "application")):
        return portal, portal_name
    return None


def attach_confirm_links(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Give Unverified punch/killer rows an official confirm URL when we have one."""
    if not isinstance(analysis, dict):
        return analysis
    punch = dict(analysis.get("punch_list") or {})
    items: List[Any] = list(punch.get("punch_list") or [])
    out_items = []
    for it in items:
        if not isinstance(it, dict):
            out_items.append(it)
            continue
        row = dict(it)
        hit = confirm_link_for_task(str(row.get("task") or row.get("title") or ""), analysis=analysis, existing_url=str(row.get("source_url") or ""))
        if hit:
            url, label = hit
            row["source_url"] = url
            if str(row.get("source_label") or "").lower() in ("", "confirm", "unverified"):
                row["source_label"] = label
            row["citation_tier"] = "link"
            row["verified"] = False
            note = str(row.get("notes") or "")
            hint = "Open the official page and confirm for this site — linked, not GIS/parcel verified."
            if hint.lower() not in note.lower():
                row["notes"] = f"{note} {hint}".strip() if note else hint
        out_items.append(row)
    punch["punch_list"] = out_items
    analysis["punch_list"] = punch

    killers = analysis.get("margin_killers")
    if isinstance(killers, list):
        out_k = []
        for k in killers:
            if not isinstance(k, dict):
                out_k.append(k)
                continue
            row = dict(k)
            hit = confirm_link_for_task(str(row.get("title") or row.get("task") or ""), analysis=analysis, existing_url=str(row.get("source_url") or ""))
            if hit:
                url, label = hit
                row["source_url"] = url
                if str(row.get("source_label") or "").lower() in ("", "confirm", "unverified"):
                    row["source_label"] = label
                row["citation_tier"] = "link"
                row["verified"] = False
            out_k.append(row)
        analysis["margin_killers"] = out_k
    return analysis


def citation_tier_for(item: Optional[Dict[str, Any]]) -> str:
    """
    verified — site/scout confirmed claim with URL
    link — catalog / portal URL present but not parcel-verified
    unverified — no defendable URL
    """
    if not isinstance(item, dict):
        return "unverified"
    explicit = str(item.get("citation_tier") or "").strip().lower()
    if explicit in ("verified", "link", "unverified", "source"):
        return "verified" if explicit == "source" else explicit

    url = str(item.get("source_url") or "").strip()
    if not url.lower().startswith("http"):
        return "unverified"

    layer = str(item.get("jurisdiction_layer") or item.get("layer") or "").lower()
    if layer in ("federal", "state", "state_pack", "portal", "catalog"):
        return "link"

    task = str(item.get("task") or item.get("title") or "")
    if task.startswith("[Federal]") or task.startswith("[State]"):
        return "link"

    if item.get("verified") is True:
        return "verified"
    return "link"


def citation_badge_label(tier: str) -> str:
    t = (tier or "").lower()
    if t == "verified":
        return "SOURCE"
    if t == "link":
        return "LINK"
    return "UNVERIFIED"


def apply_citation_honesty(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Stamp citation_tier on punch + margin killers; demote portal 'verified' theater."""
    if not isinstance(analysis, dict):
        return analysis

    analysis = attach_confirm_links(analysis)

    punch = dict(analysis.get("punch_list") or {})
    items: List[Any] = list(punch.get("punch_list") or [])
    cleaned_items = []
    for it in items:
        if not isinstance(it, dict):
            cleaned_items.append(it)
            continue
        row = dict(it)
        tier = citation_tier_for(row)
        row["citation_tier"] = tier
        if tier == "link":
            row["verified"] = False
            if not row.get("source_label") or str(row.get("source_label")).lower() in (
                "source",
                "verified",
            ):
                row["source_label"] = "Portal link"
        elif tier == "verified":
            row["verified"] = True
            row.setdefault("source_label", "Source")
        else:
            row["verified"] = False
            row.setdefault("source_label", "Unverified")
        cleaned_items.append(row)
    punch["punch_list"] = cleaned_items
    analysis["punch_list"] = punch

    killers = analysis.get("margin_killers")
    if isinstance(killers, list):
        out_k = []
        for k in killers:
            if not isinstance(k, dict):
                out_k.append(k)
                continue
            row = dict(k)
            tier = citation_tier_for(row)
            row["citation_tier"] = tier
            if tier == "link":
                row["verified"] = False
                row["source_label"] = row.get("source_label") or "Portal link"
            elif tier == "verified":
                row["verified"] = True
                row["source_label"] = row.get("source_label") or "Source"
            else:
                row["verified"] = False
                row["source_label"] = "Unverified"
            out_k.append(row)
        analysis["margin_killers"] = out_k

    return analysis
