"""Shared display titles and download filenames for Reg Guard artifacts.

Convention: ``{SITE ADDRESS} — {DOCUMENT TYPE}`` in ALL CAPS.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional


def _s(v: Any) -> str:
    return str(v or "").strip()


def site_line_from_analysis(analysis: Optional[Dict[str, Any]]) -> str:
    """Best-effort researched address for titles / filenames."""
    data = analysis if isinstance(analysis, dict) else {}
    pi = data.get("project_info") if isinstance(data.get("project_info"), dict) else {}
    loc = data.get("location") if isinstance(data.get("location"), dict) else {}
    site = data.get("site") if isinstance(data.get("site"), dict) else {}

    street = _s(pi.get("address") or loc.get("address") or site.get("address"))
    city = _s(pi.get("city") or loc.get("city") or site.get("city"))
    state = _s(pi.get("state") or loc.get("state") or site.get("state"))
    zip_code = _s(
        pi.get("zip")
        or pi.get("zip_code")
        or loc.get("zip")
        or loc.get("zip_code")
        or site.get("zip")
    )
    place = ", ".join(p for p in (city, state) if p)
    if zip_code:
        place = f"{place} {zip_code}".strip() if place else zip_code
    if street and place and place.lower() not in street.lower():
        return f"{street}, {place}"
    return street or place or "PROJECT SITE"


def document_display_title(site: str, doc_kind: str) -> str:
    """On-page / PDF metadata title: ADDRESS — DOC TYPE (ALL CAPS)."""
    site_u = re.sub(r"\s+", " ", _s(site) or "PROJECT SITE").upper()
    kind_u = re.sub(r"\s+", " ", _s(doc_kind) or "DOCUMENT").upper()
    # Prefer em dash for display; ASCII fallback happens in PDF writers
    return f"{site_u} — {kind_u}"


def document_download_filename(site: str, doc_kind: str, ext: str) -> str:
    """Filesystem-safe attachment name derived from address + doc type."""
    combined = f"{_s(site)}_{_s(doc_kind)}".upper()
    slug = re.sub(r"[^A-Z0-9]+", "_", combined).strip("_")
    if not slug:
        slug = "REGGUARD_DOCUMENT"
    slug = slug[:160].rstrip("_")
    e = (_s(ext) or "pdf").lstrip(".").lower() or "pdf"
    return f"{slug}.{e}"


def title_and_filename(
    analysis: Optional[Dict[str, Any]],
    doc_kind: str,
    *,
    ext: str = "pdf",
) -> tuple[str, str, str]:
    """Return (site_line, display_title, download_filename)."""
    site = site_line_from_analysis(analysis)
    title = document_display_title(site, doc_kind)
    filename = document_download_filename(site, doc_kind, ext)
    return site, title, filename
