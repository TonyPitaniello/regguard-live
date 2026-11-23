"""Official interconnection-queue pages. No ordinal position is invented."""

from typing import Any, Dict, Optional

# Public report pages. A position is printed only when a fetched row states one.
OFFICIAL_QUEUE_PAGES = {
    "ERCOT": "https://www.ercot.com/mp/data-products/data-product-details?id=pg7-200-er",
    "PJM": "https://www.pjm.com/planning/services-requests/interconnection-queues",
    "MISO": "https://www.misoenergy.org/planning/generator-interconnection/GI_Queue/",
    "CAISO": "https://www.caiso.com/generation-transmission/generation/generator-interconnection",
    "SPP": "https://www.spp.org/engineering/generator-interconnection/",
    "NYISO": "https://www.nyiso.com/interconnections",
}

NO_POSITION = (
    "No ordinal queue position is printed. "
    "The official queue file did not return a row for this id."
)


def cited_queue_lookup(rto: str, queue_id: str) -> Dict[str, Any]:
    """Return the official page for this RTO and no invented position."""
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
    return {
        "rto": key,
        "queue_id": qid,
        "source_url": url,
        "queue_position": None,
        "project_name": None,
        "phase": None,
        "note": f"{NO_POSITION} File: {url}",
    }
