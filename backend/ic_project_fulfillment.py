"""
IC Project Report fulfillment: after paid deep research, generate three PDFs,
attach them to the buyer's IC order, and email download links.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

IC_TIERS = frozenset({"ic_project", "ic_annual", "ic_consultant"})
PDF_TYPES = ("research_memo", "punch_list", "permits")

# order_id -> {pdf_type -> bytes}
_PDF_BYTES: Dict[str, Dict[str, bytes]] = {}
# In-flight / completed idempotency keys for IC fulfill (premortem F5)
_IC_IDEMPOTENCY: Dict[str, str] = {}
_IC_IN_FLIGHT: set[str] = set()


def _address_fingerprint(address: str) -> str:
    return " ".join((address or "").strip().lower().split())


def api_public_base() -> str:
    """
    Public base for PDF/download links in emails and order JSON.
    Prefer a custom API host — bare *.onrender.com URLs often trip Chrome
    Safe Browsing when opened via window.open in a new tab.
    """
    for key in (
        "BACKEND_PUBLIC_URL",
        "API_PUBLIC_BASE",
        "REG_GUARD_API_PUBLIC_URL",
        "API_BASE_URL",
    ):
        val = (os.getenv(key) or "").strip().rstrip("/")
        if val:
            return val
    return "https://api.regguardagent.com"


def rewrite_pdf_url_for_client(url: str) -> str:
    """Strip host so the SPA can download via backendUrl() / same-origin proxy."""
    raw = (url or "").strip()
    if not raw:
        return raw
    if raw.startswith("/"):
        return raw
    for marker in ("/orders/", "/bid-receipt/", "/bid-packet/", "/sample/"):
        idx = raw.find(marker)
        if idx >= 0:
            return raw[idx:]
    return raw


def is_ic_tier(tier: str) -> bool:
    from order_service import normalize_tier

    return normalize_tier(tier) in IC_TIERS


def pdfs_are_ready(pdfs: Optional[List[Dict[str, Any]]]) -> bool:
    if not pdfs:
        return False
    ready_count = 0
    for p in pdfs:
        name = str(p.get("name") or "").lower()
        url = str(p.get("url") or "")
        status = str(p.get("status") or "").lower()
        if "preparing" in name or status == "preparing" or "sample-report" in url:
            return False
        if p.get("type") not in PDF_TYPES:
            continue
        if not url or ("/orders/" not in url and "/pdfs/" not in url):
            return False
        ready_count += 1
    return ready_count >= 3


def _human_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n / (1024 * 1024):.1f} MB"


def _ascii_safe(text: Any, limit: int = 2000) -> str:
    s = str(text or "")
    # Helvetica core fonts are Latin-1; strip/replace common unicode
    replacements = {
        "\u2022": "-",
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u00a0": " ",
        "\u2713": "[x]",
        "\u00a9": "(c)",
    }
    for a, b in replacements.items():
        s = s.replace(a, b)
    s = s.encode("latin-1", errors="replace").decode("latin-1")
    return s[:limit]


def analysis_for_pdfs(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize Option A / pro-deep payload for pdf_generator classes."""
    data = dict(analysis or {})
    data["skip_upgrade_cta"] = True
    data["package"] = "ic_project"

    pi = dict(data.get("project_info") or {})
    if not pi.get("address"):
        loc = data.get("location") or {}
        if isinstance(loc, dict):
            pi["address"] = loc.get("address") or pi.get("address") or "Project site"
            pi.setdefault("city", loc.get("city") or "")
            pi.setdefault("state", loc.get("state") or "")
            pi.setdefault("zip", loc.get("zip") or loc.get("zip_code") or "")
    pi.setdefault("type", data.get("project_type") or "commercial")
    # Do NOT invent TX when state is missing — blank is safer than wrong RTO/AHJ
    if not str(pi.get("state") or "").strip():
        loc = data.get("location") or {}
        if isinstance(loc, dict) and loc.get("state"):
            pi["state"] = loc.get("state")
    data["project_info"] = pi

    try:
        from delivery_parity import prepare_analysis_for_delivery

        data = prepare_analysis_for_delivery(data)
        pi = data.get("project_info") or pi
    except Exception:
        pass

    env = dict(data.get("environmental_screening") or {})
    if not env.get("findings") and data.get("pro_summary_markdown"):
        env["findings"] = [
            {
                "category": "deep_research",
                "description": _ascii_safe(data["pro_summary_markdown"], 1200),
            }
        ]
    # Prefer action-plan memo as a dedicated finding when present
    if data.get("pro_summary_markdown") and not any(
        isinstance(f, dict) and f.get("category") == "contractor_action_plan"
        for f in (env.get("findings") or [])
    ):
        findings = list(env.get("findings") or [])
        findings.insert(
            0,
            {
                "category": "contractor_action_plan",
                "description": _ascii_safe(data["pro_summary_markdown"], 2500),
            },
        )
        env["findings"] = findings[:8]
    # Sanitize findings for Helvetica PDF fonts
    cleaned_findings = []
    for finding in env.get("findings") or []:
        if not isinstance(finding, dict):
            continue
        cleaned_findings.append(
            {
                **finding,
                "category": _ascii_safe(finding.get("category"), 80),
                "description": _ascii_safe(finding.get("description"), 1200),
            }
        )
    env["findings"] = cleaned_findings
    env.setdefault("risk_level", (data.get("summary") or {}).get("risk_level") or "MEDIUM")
    if not env.get("action_plan"):
        steps = data.get("next_steps") or []
        env["action_plan"] = [str(s) for s in steps[:5]] if steps else [
            "Review citeable punch list and AHJ sources before bid.",
            "Confirm permit fees and trade registrations with the local AHJ.",
            "Verify utility capacity and interconnection lead times for this site.",
        ]
    env["action_plan"] = [_ascii_safe(a, 400) for a in (env.get("action_plan") or [])[:8]]
    data["environmental_screening"] = env

    punch = dict(data.get("punch_list") or {})
    items = punch.get("punch_list") or punch.get("items") or []
    if not isinstance(items, list):
        items = []
    try:
        from punch_rank import strip_md_bold
        from delivery_parity import citation_label_for_item
    except Exception:
        def strip_md_bold(t: str) -> str:  # type: ignore
            return t or ""

        def citation_label_for_item(item: dict) -> str:  # type: ignore
            return "SOURCE" if item.get("verified") else "UNVERIFIED"

    safe_items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        safe_items.append(
            {
                **item,
                "task": _ascii_safe(strip_md_bold(item.get("task")), 220),
                "timeline": _ascii_safe(item.get("timeline"), 40),
                "notes": _ascii_safe(item.get("notes"), 300),
                "citation_label": citation_label_for_item(item),
            }
        )
    punch["punch_list"] = safe_items
    punch.setdefault("timeline_summary", "8-12 weeks (planning estimate)")
    punch["timeline_summary"] = _ascii_safe(punch.get("timeline_summary"), 80)
    punch.setdefault("estimated_total_cost", 0)
    data["punch_list"] = punch
    if data.get("pro_summary_markdown"):
        data["pro_summary_markdown"] = _ascii_safe(data["pro_summary_markdown"], 8000)
    data["skip_upgrade_cta"] = True
    return _deep_ascii_strings(data)


def _deep_ascii_strings(obj: Any, *, _depth: int = 0) -> Any:
    """Helvetica-safe strings throughout the PDF payload (packs often use em dashes)."""
    if _depth > 12:
        return obj
    if isinstance(obj, dict):
        return {k: _deep_ascii_strings(v, _depth=_depth + 1) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_ascii_strings(v, _depth=_depth + 1) for v in obj]
    if isinstance(obj, str):
        return _ascii_safe(obj, 8000)
    return obj


def _read_file_bytes(path: str) -> bytes:
    return Path(path).read_bytes()


def generate_ic_pdf_bytes(analysis: Dict[str, Any]) -> Dict[str, bytes]:
    """Generate research_memo, punch_list, permits as PDF bytes."""
    from pdf_generator import ResearchMemoPDF, PunchListPDF, PermitPackagePDF
    from permit_package import build_permit_package_pdf

    shaped = analysis_for_pdfs(analysis)
    pi = shaped["project_info"]
    out: Dict[str, bytes] = {}

    with tempfile.TemporaryDirectory(prefix="ic_pdf_") as tmp:
        memo_path = os.path.join(tmp, "research_memo.pdf")
        punch_path = os.path.join(tmp, "punch_list.pdf")
        ResearchMemoPDF().generate(shaped, output_path=memo_path)
        PunchListPDF().generate(shaped, output_path=punch_path)
        out["research_memo"] = _read_file_bytes(memo_path)
        out["punch_list"] = _read_file_bytes(punch_path)

    # Prefer real AHJ worksheet for permits
    site = pi.get("address") or "Project site"
    city = pi.get("city") or ""
    state = pi.get("state") or ""
    zip_code = str(pi.get("zip") or "")
    scope_bits = [
        f"IC Project Report permit planning worksheet for {site}.",
        f"Project type: {pi.get('type') or 'commercial'}.",
        "Confirm all fees, trade licenses, and e-plan requirements with the AHJ before filing.",
    ]
    summary_md = shaped.get("pro_summary_markdown") or ""
    if summary_md:
        scope_bits.append(str(summary_md)[:2000])
    try:
        out["permits"] = build_permit_package_pdf(
            site_address=site,
            scope="\n\n".join(scope_bits),
            fee_summary="Confirm current AHJ fee schedule before payment.",
            trade="General contractor / electrical (confirm with AHJ)",
            zip_code=zip_code,
            city=city,
            county="",
            ahj_label=f"{city}, {state}".strip(", "),
        )
    except Exception as e:
        logger.warning("build_permit_package_pdf failed, falling back to PermitPackagePDF: %s", e)
        with tempfile.TemporaryDirectory(prefix="ic_permit_") as tmp:
            path = os.path.join(tmp, "permits.pdf")
            PermitPackagePDF().generate(shaped, state=state or "FL", output_path=path)
            out["permits"] = _read_file_bytes(path)

    return out


def build_pdf_meta(
    order_id: str,
    email: str,
    byte_map: Dict[str, bytes],
    *,
    download_token: str = "",
) -> List[Dict[str, Any]]:
    base = api_public_base()
    email_q = (email or "").strip().lower()
    token_q = (download_token or "").strip()
    icons = {"research_memo": "📄", "punch_list": "✅", "permits": "📋"}
    names = {
        "research_memo": "Research Memo",
        "punch_list": "Contractor Punch List",
        "permits": "Permit Package Worksheet",
    }
    meta: List[Dict[str, Any]] = []
    for ptype in PDF_TYPES:
        raw = byte_map.get(ptype) or b""
        qs = f"email={email_q}"
        if token_q:
            qs += f"&token={token_q}"
        meta.append(
            {
                "type": ptype,
                "name": names[ptype],
                "size": _human_size(len(raw)) if raw else "—",
                "url": f"{base}/orders/{order_id}/pdfs/{ptype}?{qs}",
                "icon": icons[ptype],
                "status": "ready",
            }
        )
    return meta


def find_open_ic_order(email: str) -> Optional[Dict[str, Any]]:
    """Newest IC-tier order for email that still needs PDFs (or any IC order)."""
    from order_service import get_raw_orders_for_email, normalize_tier

    email_l = (email or "").strip().lower()
    if not email_l:
        return None
    orders = get_raw_orders_for_email(email_l)
    ic_orders = [o for o in orders if is_ic_tier(str(o.get("tier") or ""))]
    if not ic_orders:
        return None
    # Prefer order without ready PDFs
    for o in ic_orders:
        if not pdfs_are_ready(o.get("pdfs")):
            return o
    return ic_orders[0]


async def fulfill_ic_project_artifacts(
    email: str,
    analysis: Dict[str, Any],
    *,
    force: bool = False,
    idempotency_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Generate IC PDFs for the buyer's open IC order and update order.pdfs.
    Idempotent unless force=True (or address changed).
    """
    from order_service import update_order_artifacts

    email_l = (email or "").strip().lower()
    if not email_l or not isinstance(analysis, dict):
        return None

    order = find_open_ic_order(email_l)
    if not order:
        logger.info("IC fulfill skipped — no IC order for %s", email_l)
        return None

    order_id = str(order.get("order_id") or order.get("id") or "")
    if not order_id:
        return None

    idem = (idempotency_key or "").strip()
    if idem:
        prior = _IC_IDEMPOTENCY.get(idem)
        if prior == order_id and pdfs_are_ready(order.get("pdfs")) and order_id in _PDF_BYTES:
            logger.info("IC fulfill idempotent hit key=%s order=%s", idem, order_id)
            return order
        if idem in _IC_IN_FLIGHT:
            logger.info("IC fulfill skipped — in flight for key=%s", idem)
            return order

    new_address = str((analysis.get("project_info") or {}).get("address") or "").strip().lower()
    old_address = str(order.get("address") or "").strip().lower()
    address_changed = bool(
        new_address
        and old_address
        and _address_fingerprint(new_address) != _address_fingerprint(old_address)
    )

    if pdfs_are_ready(order.get("pdfs")) and not force and not address_changed and order_id in _PDF_BYTES:
        logger.info("IC fulfill skipped — PDFs already ready for order %s", order_id)
        if idem:
            _IC_IDEMPOTENCY[idem] = order_id
        return order

    # Allow regenerate when caller forces, or buyer researched a different site
    if pdfs_are_ready(order.get("pdfs")) and (force or address_changed):
        logger.info(
            "IC regenerate order=%s force=%s address_changed=%s",
            order_id,
            force,
            address_changed,
        )

    if idem:
        _IC_IN_FLIGHT.add(idem)
    try:
        byte_map = generate_ic_pdf_bytes(analysis)
    except Exception as e:
        logger.exception("IC PDF generation failed for order %s: %s", order_id, e)
        if idem:
            _IC_IN_FLIGHT.discard(idem)
        return None

    _PDF_BYTES[order_id] = byte_map
    token = str(order.get("download_token") or "")
    pdfs = build_pdf_meta(order_id, email_l, byte_map, download_token=token)
    address = (analysis.get("project_info") or {}).get("address") or ""

    # Persist a fresh shareable research record so email/forward ≠ Instant Preview
    shaped = analysis_for_pdfs(analysis)
    shaped["preview"] = False
    shaped["depth_tier"] = "ic_full"
    shaped["research_depth"] = "ic"
    shaped.pop("research_id", None)  # force new id
    shaped.pop("share_url", None)
    share_meta: Dict[str, Any] = {}
    try:
        from research_store import save_research, stamp_depth_badge

        shaped = stamp_depth_badge(shaped)
        share_meta = save_research(shaped)
        shaped["research_id"] = share_meta.get("research_id")
        shaped["share_url"] = share_meta.get("share_url")
    except Exception as e:
        logger.warning("IC share refresh failed: %s", e)
        shaped = analysis_for_pdfs(analysis)

    # Update pdf_status on raw order before artifact patch
    order["pdf_status"] = "ready"
    if share_meta.get("share_url"):
        order["share_url"] = share_meta["share_url"]
    if share_meta.get("research_id"):
        order["research_id"] = share_meta["research_id"]
    updated = update_order_artifacts(
        order_id,
        pdfs=pdfs,
        analysis_json=shaped,
        address=str(address),
        share_url=share_meta.get("share_url"),
        research_id=share_meta.get("research_id"),
    )
    logger.info(
        "✅ IC Project PDFs ready order=%s email=%s sizes=%s share=%s",
        order_id,
        email_l,
        {k: len(v) for k, v in byte_map.items()},
        share_meta.get("share_url") or "n/a",
    )

    if idem:
        _IC_IDEMPOTENCY[idem] = order_id
        _IC_IN_FLIGHT.discard(idem)

    # Best-effort email with download links
    try:
        from email_service import get_email_service

        svc = get_email_service()
        if svc and hasattr(svc, "send_order_pdfs_ready"):
            await svc.send_order_pdfs_ready(email_l, order_id, pdfs)
    except Exception as e:
        logger.warning("IC PDF ready email failed: %s", e)

    return updated


def get_cached_pdf_bytes(order_id: str, pdf_type: str) -> Optional[bytes]:
    return (_PDF_BYTES.get(order_id) or {}).get(pdf_type)


def ensure_pdf_bytes(
    order_id: str,
    pdf_type: str,
    *,
    email: str = "",
    token: str = "",
) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Return PDF bytes for download, regenerating from stored analysis if needed.
    Requires matching download_token when the order has one set.
    Returns (bytes, error_message).
    """
    if pdf_type not in PDF_TYPES:
        return None, "Invalid PDF type"

    from order_service import get_raw_order_by_id

    order = get_raw_order_by_id(order_id)
    if not order:
        return None, "Order not found"

    order_token = (order.get("download_token") or "").strip()
    provided_token = (token or "").strip()
    email_l = (email or "").strip().lower()
    order_email = (order.get("email") or "").strip().lower()

    # Prefer token auth; fall back to email match only when order has no token
    if order_token:
        if not provided_token or provided_token != order_token:
            return None, "Invalid or missing download token"
    elif email_l and order_email and email_l != order_email:
        return None, "Email does not match order"

    cached = get_cached_pdf_bytes(order_id, pdf_type)
    if cached:
        return cached, None

    analysis = order.get("analysis_json")
    if not isinstance(analysis, dict) or not analysis:
        return None, "PDFs not ready — run a site lookup after purchase to generate your report"

    try:
        byte_map = generate_ic_pdf_bytes(analysis)
        _PDF_BYTES[order_id] = byte_map
        from order_service import update_order_artifacts

        update_order_artifacts(
            order_id,
            pdfs=build_pdf_meta(
                order_id,
                order_email or email_l,
                byte_map,
                download_token=order_token,
            ),
        )
        return byte_map.get(pdf_type), None
    except Exception as e:
        logger.exception("Regenerate IC PDF failed: %s", e)
        return None, "Failed to regenerate PDF"
