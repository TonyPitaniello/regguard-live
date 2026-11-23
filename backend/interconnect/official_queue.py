"""Official interconnection-queue pages. A position is printed only when the file states one."""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, Optional, Tuple

# Public report pages. A position is printed only when a fetched row states one.
OFFICIAL_QUEUE_PAGES = {
    "ERCOT": "https://www.ercot.com/mp/data-products/data-product-details?id=pg7-200-er",
    "PJM": "https://www.pjm.com/planning/services-requests/interconnection-queues",
    "MISO": "https://www.misoenergy.org/planning/generator-interconnection/GI_Queue/",
    "CAISO": "https://www.caiso.com/generation-transmission/generation/generator-interconnection",
    "SPP": "https://www.spp.org/engineering/generator-interconnection/",
    "NYISO": "https://www.nyiso.com/interconnections",
}

GIS_LIST_URL = (
    "https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=15933"
)
GIS_DOWNLOAD = "https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId={doc_id}"

NO_POSITION = (
    "No ordinal queue position is printed. "
    "The official queue file did not return a row for this id."
)
UNREAD = (
    "No ordinal queue position is printed. "
    "The official queue file could not be read from this desk. "
    "No row is printed."
)

_POSITION_HEADERS = {"queue position", "ordinal queue position", "queue rank"}
_STATED_FIELDS = (
    "Project Name",
    "County",
    "GIM Study Phase",
    "Capacity (MW)",
    "Projected COD",
    "Fuel",
    "POI Location",
    "Interconnecting Entity",
)
_MONTHS = (
    "January|February|March|April|May|June|July|August|"
    "September|October|November|December"
)
_CACHE_TTL_SEC = 12 * 60 * 60
_LOCK = threading.Lock()
_CACHE: Dict[str, Any] = {"at": 0.0, "payload": None}


class QueueFileError(Exception):
    """The official file was not read. No row is invented."""


def cited_queue_lookup(rto: str, queue_id: str) -> Dict[str, Any]:
    """Return the official page for this RTO. ERCOT rows come from the GIS workbook."""
    key = (rto or "").strip().upper()
    url: Optional[str] = OFFICIAL_QUEUE_PAGES.get(key)
    qid = (queue_id or "").strip()
    if not url:
        return {
            "rto": key or (rto or "").strip(),
            "queue_id": qid,
            "source_url": "",
            "queue_position": None,
            "project_name": None,
            "phase": None,
            "note": "No official queue file is on file for this RTO. No position is printed.",
        }
    if key != "ERCOT":
        return {
            "rto": key,
            "queue_id": qid,
            "source_url": url,
            "queue_position": None,
            "project_name": None,
            "phase": None,
            "note": f"{NO_POSITION} File: {url}",
        }
    try:
        loaded = _load_ercot_rows()
    except QueueFileError:
        return {
            "rto": key,
            "queue_id": qid,
            "source_url": url,
            "queue_position": None,
            "project_name": None,
            "phase": None,
            "note": f"{UNREAD} File: {url}",
        }
    rec = (loaded.get("rows") or {}).get(qid.upper())
    report_date = str(loaded.get("report_date") or "").strip()
    report_name = str(loaded.get("report_name") or "").strip()
    fresh = bool(loaded.get("fresh"))
    if not rec:
        dated = f" Report date printed in the file: {report_date}." if report_date else ""
        named = f" Report: {report_name}." if report_name else ""
        cached = "" if fresh else " This desk is using the last official file it read."
        return {
            "rto": key,
            "queue_id": qid,
            "source_url": url,
            "queue_position": None,
            "project_name": None,
            "phase": None,
            "note": f"{NO_POSITION}{dated}{named}{cached} File: {url}",
        }
    position = rec.get("queue_position")
    if not isinstance(position, int):
        position = None
    phase = _plain(rec.get("GIM Study Phase")) or None
    return {
        "rto": key,
        "queue_id": qid,
        "source_url": url,
        "queue_position": position,
        "project_name": _plain(rec.get("Project Name")) or None,
        "phase": phase,
        "note": _note_for_hit(rec, report_date, report_name, fresh, url),
    }


def parse_gis_workbook(data: bytes) -> Tuple[Dict[str, Dict[str, Any]], str]:
    """Index INR rows. The report date is a date the sheet itself prints."""
    import openpyxl

    wb = openpyxl.load_workbook(BytesIO(data), read_only=True, data_only=True)
    rows: Dict[str, Dict[str, Any]] = {}
    printed = ""
    try:
        for ws in wb.worksheets:
            header: Optional[Dict[str, int]] = None
            position_at: Optional[int] = None
            for raw in ws.iter_rows(max_col=48, values_only=True):
                if header is None:
                    if not printed:
                        printed = _date_in_row(raw)
                    labels = [_plain(cell) for cell in raw]
                    if "INR" not in labels:
                        continue
                    header = {}
                    for idx, label in enumerate(labels):
                        if not label:
                            continue
                        if label in _STATED_FIELDS or label == "INR":
                            header[label] = idx
                        if label.casefold() in _POSITION_HEADERS:
                            position_at = idx
                    continue
                inr_at = header.get("INR")
                if inr_at is None or inr_at >= len(raw):
                    continue
                inr = _plain(raw[inr_at]).upper()
                if not re.match(r"^[0-9]{2}INR[0-9A-Z]+$", inr):
                    continue
                if inr in rows:
                    continue
                rec: Dict[str, Any] = {}
                for name, idx in header.items():
                    if name == "INR" or idx >= len(raw):
                        continue
                    value = raw[idx]
                    if value is None or _plain(value) == "":
                        continue
                    rec[name] = value
                if position_at is not None and position_at < len(raw):
                    pos = raw[position_at]
                    if isinstance(pos, int) and not isinstance(pos, bool):
                        rec["queue_position"] = pos
                    elif isinstance(pos, float) and pos.is_integer():
                        rec["queue_position"] = int(pos)
                rows[inr] = rec
    finally:
        wb.close()
    return rows, printed


def _load_ercot_rows() -> Dict[str, Any]:
    now = time.time()
    with _LOCK:
        cached = _CACHE.get("payload")
        if cached and now - float(_CACHE.get("at") or 0) < _CACHE_TTL_SEC:
            return dict(cached)
    try:
        payload = _fetch_ercot_rows()
        payload["fresh"] = True
    except QueueFileError:
        with _LOCK:
            cached = _CACHE.get("payload")
        if not cached:
            raise
        stale = dict(cached)
        stale["fresh"] = False
        return stale
    with _LOCK:
        _CACHE["at"] = now
        _CACHE["payload"] = payload
    return dict(payload)


def _fetch_ercot_rows() -> Dict[str, Any]:
    listing = _get_bytes(GIS_LIST_URL)
    if listing[:1] in (b"<", b"{"):
        if listing[:1] == b"<":
            raise QueueFileError("document list was not JSON")
    try:
        parsed = json.loads(listing.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise QueueFileError("document list was not JSON") from exc
    doc = _pick_gis_document(parsed)
    if not doc:
        raise QueueFileError("document list had no GIS report")
    doc_id = str(doc.get("DocID") or "").strip()
    if not doc_id:
        raise QueueFileError("GIS report had no document id")
    blob = _get_bytes(GIS_DOWNLOAD.format(doc_id=doc_id))
    if not blob.startswith(b"PK"):
        raise QueueFileError("GIS download was not a workbook")
    rows, printed = parse_gis_workbook(blob)
    if not rows:
        raise QueueFileError("GIS workbook had no INR rows")
    published = _plain(doc.get("PublishDate"))
    report_date = printed or published
    return {
        "rows": rows,
        "report_date": report_date,
        "report_name": _plain(doc.get("FriendlyName")),
        "published": published,
        "fresh": True,
    }


def _pick_gis_document(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    block = (payload.get("ListDocsByRptTypeRes") or {}).get("DocumentList")
    if isinstance(block, dict):
        block = [block]
    if not isinstance(block, list):
        return None
    docs = []
    for item in block:
        if not isinstance(item, dict):
            continue
        doc = item.get("Document") if isinstance(item.get("Document"), dict) else item
        name = _plain(doc.get("FriendlyName"))
        if "GIS" not in name.upper():
            continue
        docs.append(doc)
    if not docs:
        return None

    def _key(doc: Dict[str, Any]) -> str:
        return _plain(doc.get("PublishDate"))

    return max(docs, key=_key)


def _get_bytes(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, */*",
            "Referer": OFFICIAL_QUEUE_PAGES["ERCOT"],
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            data = res.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise QueueFileError(str(exc)) from exc
    head = data[:800].lower()
    if b"access denied" in head or b"incapsula" in head:
        raise QueueFileError("official file denied the download")
    return data


def _note_for_hit(
    rec: Dict[str, Any],
    report_date: str,
    report_name: str,
    fresh: bool,
    url: str,
) -> str:
    position = rec.get("queue_position")
    if isinstance(position, int):
        parts = [f"The GIS report states queue position {position} for this INR."]
    else:
        parts = [
            "The GIS report states this INR.",
            "It does not state an ordinal queue position.",
        ]
    project = _plain(rec.get("Project Name"))
    county = _plain(rec.get("County"))
    phase = _plain(rec.get("GIM Study Phase"))
    if project:
        parts.append(f"Project: {project}.")
    if county:
        parts.append(f"County: {county}.")
    if phase:
        parts.append(f"GIM study phase: {phase}.")
    capacity = _number_text(rec.get("Capacity (MW)"))
    if capacity:
        parts.append(f"Capacity (MW) stated on the file: {capacity}.")
    cod = _plain(rec.get("Projected COD"))
    if cod:
        parts.append(f"Projected COD stated on the file: {cod}.")
    if report_date:
        parts.append(f"Report date printed in the file: {report_date}.")
    elif report_name:
        parts.append(f"Report: {report_name}.")
    if not fresh:
        parts.append("This desk is using the last official file it read.")
    parts.append(f"File: {url}")
    return " ".join(parts)


def _number_text(value: Any) -> str:
    if isinstance(value, bool) or value is None:
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value != value:
            return ""
        if value.is_integer():
            return str(int(value))
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return ""


def _plain(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.date().isoformat()
        return value.astimezone(timezone.utc).date().isoformat()
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text[:180]


def _date_in_row(row: Tuple[Any, ...]) -> str:
    for cell in row:
        if isinstance(cell, datetime):
            return cell.date().isoformat()
        text = _plain(cell)
        match = re.search(rf"(?:{_MONTHS})\s+\d{{4}}", text)
        if match:
            return match.group(0)
        match = re.search(r"\d{1,2}/\d{1,2}/\d{4}", text)
        if match:
            return match.group(0)
    return ""
