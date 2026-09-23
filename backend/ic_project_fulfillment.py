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
# Primary boardroom package first; classic three remain as optional parts.
PDF_TYPES = ("ic_package", "research_memo", "punch_list", "permits")
CORE_PART_TYPES = ("research_memo", "punch_list", "permits")

# order_id -> {pdf_type -> bytes}
_PDF_BYTES: Dict[str, Dict[str, bytes]] = {}
# In-flight / completed idempotency keys for IC fulfill (premortem F5)
_IC_IDEMPOTENCY: Dict[str, str] = {}
_IC_IN_FLIGHT: set[str] = set()


def _address_fingerprint(address: str) -> str:
    return " ".join((address or "").strip().lower().split())


def site_fingerprint(
    *,
    address: str = "",
    city: str = "",
    state: str = "",
    zip_code: str = "",
) -> str:
    """
    Normalize a site key for IC Project one-site binding.
    Street + ZIP + state — city omitted to avoid Fort Worth vs Ft Worth mismatches.
    """
    street = _address_fingerprint(address)
    # If address already embeds "city, ST zip", keep street portion only when comma-separated
    if "," in street:
        street = street.split(",", 1)[0].strip()
    z = "".join(c for c in str(zip_code or "") if c.isdigit())[:5]
    st = (state or "").strip().lower()[:2]
    return f"{street}|{z}|{st}"


def order_site_fingerprint(order: Dict[str, Any]) -> str:
    if not isinstance(order, dict):
        return ""
    addr = str(order.get("site_address") or "").strip()
    city = str(order.get("site_city") or "").strip()
    state = str(order.get("site_state") or "").strip()
    zip_code = str(order.get("site_zip") or "").strip()
    if not addr:
        # Fulfill historically stored full line in order["address"]
        raw = str(order.get("address") or order.get("site_label") or "").strip()
        if raw:
            # Prefer parsing "street, city, ST ZIP"
            import re

            m = re.match(
                r"^(.+),\s*([^,]+),\s*([A-Za-z]{2})\s+(\d{5})",
                raw,
            )
            if m:
                return site_fingerprint(
                    address=m.group(1),
                    city=m.group(2),
                    state=m.group(3),
                    zip_code=m.group(4),
                )
            return site_fingerprint(address=raw)
    return site_fingerprint(address=addr, city=city, state=state, zip_code=zip_code)


def evaluate_ic_site_access(
    email: str,
    *,
    address: str = "",
    city: str = "",
    state: str = "",
    zip_code: str = "",
) -> Dict[str, Any]:
    """
    IC Project is $1,500 per site. IC Annual may cover additional sites.

    Modes:
      annual            — subscription may generate for this address
      bind_unused       — paid IC Project not yet bound / PDFs not ready (one-shot)
      same_site_refresh — paid IC Project already bound to this exact site
      need_purchase     — must buy another IC Project for this address
    """
    from order_service import get_raw_orders_for_email, normalize_tier

    email_l = (email or "").strip().lower()
    fp = site_fingerprint(address=address, city=city, state=state, zip_code=zip_code)
    site_label = ", ".join(
        p for p in [(address or "").strip(), f"{(city or '').strip()} {(state or '').strip()} {(zip_code or '').strip()}".strip()] if p
    )
    empty = {
        "allowed": False,
        "mode": "need_purchase",
        "order_id": None,
        "bound_site": "",
        "site_fingerprint": fp,
        "message": (
            "IC Project is $1,500 per site. Purchase unlocks the Diligence Bundle ZIP "
            "for one address only."
        ),
    }
    if not email_l or "@" not in email_l:
        return empty

    orders = [o for o in get_raw_orders_for_email(email_l) if is_ic_tier(str(o.get("tier") or ""))]
    if not orders:
        return empty

    # Active IC Annual → additional sites allowed under subscription
    for o in orders:
        if normalize_tier(str(o.get("tier") or "")) == "ic_annual":
            return {
                "allowed": True,
                "mode": "annual",
                "order_id": str(o.get("order_id") or o.get("id") or "") or None,
                "bound_site": order_site_fingerprint(o) and str(o.get("site_label") or o.get("address") or ""),
                "site_fingerprint": fp,
                "message": (
                    "Your email has IC Annual access. OK creates/updates the Diligence Bundle "
                    f"ZIP for this address under that subscription:\n\n{site_label}\n\n"
                    "Cancel researches without the paid package."
                ),
            }

    # Unused IC Project (PDFs not ready) — bind this address once
    for o in orders:
        tier = normalize_tier(str(o.get("tier") or ""))
        if tier not in ("ic_project", "ic_consultant"):
            continue
        if not pdfs_are_ready(o.get("pdfs")):
            return {
                "allowed": True,
                "mode": "bind_unused",
                "order_id": str(o.get("order_id") or o.get("id") or "") or None,
                "bound_site": "",
                "site_fingerprint": fp,
                "message": (
                    f"OK uses your $1,500 IC Project purchase for THIS address only:\n\n{site_label}\n\n"
                    "Additional sites require a new $1,500 purchase. Cancel researches without "
                    "the counsel ZIP. Reg Guard does not store your credit card."
                ),
            }

    # Same-site refresh
    if fp and fp != "||":
        for o in orders:
            tier = normalize_tier(str(o.get("tier") or ""))
            if tier not in ("ic_project", "ic_consultant"):
                continue
            ofp = order_site_fingerprint(o)
            if ofp and ofp == fp:
                bound = str(o.get("site_label") or o.get("address") or site_label)
                return {
                    "allowed": True,
                    "mode": "same_site_refresh",
                    "order_id": str(o.get("order_id") or o.get("id") or "") or None,
                    "bound_site": bound,
                    "site_fingerprint": fp,
                    "message": (
                        f"OK refreshes the Diligence Bundle for this paid site (no new charge):\n\n{bound}\n\n"
                        "A different address requires a new $1,500 IC Project purchase. "
                        "Cancel researches without regenerating the counsel ZIP."
                    ),
                }

    # Has IC purchase(s) but for other site(s)
    prior = []
    for o in orders:
        label = str(o.get("site_label") or o.get("address") or o.get("site_address") or "").strip()
        if label:
            prior.append(label)
    prior_s = prior[0] if prior else "another address"
    return {
        "allowed": False,
        "mode": "need_purchase",
        "order_id": None,
        "bound_site": prior_s,
        "site_fingerprint": fp,
        "message": (
            f"IC Project is $1,500 per site. Your prior purchase is bound to:\n\n{prior_s}\n\n"
            f"This run is a different site:\n\n{site_label}\n\n"
            "OK opens Checkout for a new $1,500 IC Project for this address. "
            "Cancel researches without the counsel ZIP."
        ),
    }


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
    by_type = {}
    for p in pdfs:
        name = str(p.get("name") or "").lower()
        url = str(p.get("url") or "")
        status = str(p.get("status") or "").lower()
        if "preparing" in name or status == "preparing" or "sample-report" in url:
            return False
        ptype = p.get("type")
        if ptype not in PDF_TYPES:
            continue
        if not url or ("/orders/" not in url and "/pdfs/" not in url):
            continue
        by_type[ptype] = p
    # Boardroom package alone is enough for "ready"; classic trio still counts for older orders
    if "ic_package" in by_type:
        return True
    return all(t in by_type for t in CORE_PART_TYPES)


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
        from pdf_text import markdown_to_plain as _md_plain

        findings = list(env.get("findings") or [])
        findings.insert(
            0,
            {
                "category": "contractor_action_plan",
                "description": _md_plain(data["pro_summary_markdown"], limit=3500),
            },
        )
        env["findings"] = findings[:8]
    # Sanitize findings for Helvetica PDF fonts (strip markdown artifacts)
    from pdf_text import markdown_to_plain as _md_plain2

    cleaned_findings = []
    for finding in env.get("findings") or []:
        if not isinstance(finding, dict):
            continue
        cleaned_findings.append(
            {
                **finding,
                "category": _ascii_safe(finding.get("category"), 80),
                "description": _md_plain2(finding.get("description"), limit=2500),
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
        from delivery_parity import citation_label_for_item
    except Exception:
        def citation_label_for_item(item: dict) -> str:  # type: ignore
            return "SOURCE" if item.get("verified") else "UNVERIFIED"

    from pdf_text import cite_host, markdown_to_plain as _md_task

    safe_items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        url = str(item.get("source_url") or item.get("citation_url") or "")
        label = citation_label_for_item(item)
        safe_items.append(
            {
                **item,
                "task": _md_task(item.get("task") or item.get("action"), limit=280),
                "timeline": _ascii_safe(item.get("timeline"), 40),
                "notes": _ascii_safe(item.get("notes"), 300),
                "citation_label": cite_host(url, label=label),
                "source_url": url,
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
    data = _deep_ascii_strings(data)
    try:
        from ic_pdf_enrichment import enrich_analysis_for_ic_pdfs

        data = enrich_analysis_for_ic_pdfs(data)
    except Exception as e:
        logger.warning("IC PDF enrichment skipped: %s", e)
    return data


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
    """Generate boardroom package + research_memo, punch_list, permits."""
    from pdf_generator import ResearchMemoPDF, PunchListPDF, PermitPackagePDF
    from ic_boardroom_pdf import generate_ic_boardroom_pdf_bytes

    shaped = analysis_for_pdfs(analysis)
    pi = shaped["project_info"]
    state = str(pi.get("state") or "TX")
    out: Dict[str, bytes] = {}

    # Primary $1,500 deliverable
    try:
        out["ic_package"] = generate_ic_boardroom_pdf_bytes(
            shaped,
            generated_for=str(shaped.get("generated_for") or ""),
            share_url=str(shaped.get("share_url") or ""),
        )
    except Exception as e:
        logger.exception("IC boardroom package failed: %s", e)
        raise

    with tempfile.TemporaryDirectory(prefix="ic_pdf_") as tmp:
        memo_path = os.path.join(tmp, "research_memo.pdf")
        punch_path = os.path.join(tmp, "punch_list.pdf")
        permit_path = os.path.join(tmp, "permits.pdf")
        ResearchMemoPDF().generate(shaped, output_path=memo_path)
        PunchListPDF().generate(shaped, output_path=punch_path)
        PermitPackagePDF().generate(shaped, state=state, output_path=permit_path)
        out["research_memo"] = _read_file_bytes(memo_path)
        out["punch_list"] = _read_file_bytes(punch_path)
        out["permits"] = _read_file_bytes(permit_path)

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
    icons = {
        "ic_package": "📦",
        "research_memo": "📄",
        "punch_list": "✅",
        "permits": "📋",
    }
    names = {
        "ic_package": "IC Diligence Package (full)",
        "research_memo": "Research Memo",
        "punch_list": "Contractor Punch List",
        "permits": "Permit Package Worksheet",
    }
    meta: List[Dict[str, Any]] = []
    for ptype in PDF_TYPES:
        raw = byte_map.get(ptype) or b""
        if not raw and ptype == "ic_package":
            continue
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
                "primary": ptype == "ic_package",
            }
        )
    return meta


def find_open_ic_order(email: str) -> Optional[Dict[str, Any]]:
    """Newest IC-tier order for email that still needs PDFs (or any IC order)."""
    from order_service import get_raw_orders_for_email

    email_l = (email or "").strip().lower()
    if not email_l:
        return None
    orders = get_raw_orders_for_email(email_l)
    ic_orders = [o for o in orders if is_ic_tier(str(o.get("tier") or ""))]
    if not ic_orders:
        return None
    for o in ic_orders:
        if not pdfs_are_ready(o.get("pdfs")):
            return o
    return ic_orders[0]


def resolve_ic_order_for_site(
    email: str,
    *,
    address: str = "",
    city: str = "",
    state: str = "",
    zip_code: str = "",
) -> Optional[Dict[str, Any]]:
    """Pick the IC order that may fulfill THIS site (or None if a new purchase is required)."""
    from order_service import get_raw_orders_for_email, normalize_tier

    access = evaluate_ic_site_access(
        email, address=address, city=city, state=state, zip_code=zip_code
    )
    if not access.get("allowed"):
        return None
    oid = str(access.get("order_id") or "").strip()
    if oid:
        for o in get_raw_orders_for_email(email):
            if str(o.get("order_id") or o.get("id") or "") == oid:
                return o
    # Annual / fallback: prefer unfulfilled, else newest annual, else matching site
    email_l = (email or "").strip().lower()
    orders = [o for o in get_raw_orders_for_email(email_l) if is_ic_tier(str(o.get("tier") or ""))]
    mode = str(access.get("mode") or "")
    if mode == "annual":
        for o in orders:
            if normalize_tier(str(o.get("tier") or "")) == "ic_annual":
                return o
    for o in orders:
        if not pdfs_are_ready(o.get("pdfs")):
            return o
    fp = site_fingerprint(address=address, city=city, state=state, zip_code=zip_code)
    for o in orders:
        if order_site_fingerprint(o) == fp:
            return o
    return orders[0] if orders else None


async def fulfill_ic_project_artifacts(
    email: str,
    analysis: Dict[str, Any],
    *,
    force: bool = False,
    idempotency_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Generate IC PDFs for an IC order that may cover THIS site.

    IC Project ($1,500): one site only — same-site refresh OK; new address requires new purchase.
    IC Annual: may regenerate for additional sites.
    """
    from order_service import normalize_tier, update_order_artifacts

    email_l = (email or "").strip().lower()
    if not email_l or not isinstance(analysis, dict):
        return None

    pi = analysis.get("project_info") if isinstance(analysis.get("project_info"), dict) else {}
    site_addr = str(pi.get("address") or "").strip()
    site_city = str(pi.get("city") or "").strip()
    site_state = str(pi.get("state") or "").strip()
    site_zip = str(pi.get("zip") or "").strip()

    access = evaluate_ic_site_access(
        email_l,
        address=site_addr,
        city=site_city,
        state=site_state,
        zip_code=site_zip,
    )
    if not access.get("allowed"):
        logger.info(
            "IC fulfill blocked — need_purchase email=%s site=%s bound=%s",
            email_l,
            access.get("site_fingerprint"),
            access.get("bound_site"),
        )
        return None

    order = resolve_ic_order_for_site(
        email_l,
        address=site_addr,
        city=site_city,
        state=site_state,
        zip_code=site_zip,
    )
    if not order:
        logger.info("IC fulfill skipped — no resolvable IC order for %s", email_l)
        return None

    order_id = str(order.get("order_id") or order.get("id") or "")
    if not order_id:
        return None

    tier_ic = normalize_tier(str(order.get("tier") or ""))
    mode = str(access.get("mode") or "")
    already = pdfs_are_ready(order.get("pdfs"))

    # Hard rule: ic_project cannot jump to a different site after PDFs are ready
    if already and mode == "need_purchase":
        return None
    if already and tier_ic in ("ic_project", "ic_consultant") and mode not in (
        "same_site_refresh",
        "bind_unused",
    ):
        if mode != "annual":
            logger.info(
                "IC fulfill blocked cross-site reuse order=%s mode=%s",
                order_id,
                mode,
            )
            return None

    idem = (idempotency_key or "").strip()
    if idem:
        prior = _IC_IDEMPOTENCY.get(idem)
        if prior == order_id and already and order_id in _PDF_BYTES:
            logger.info("IC fulfill idempotent hit key=%s order=%s", idem, order_id)
            return order
        if idem in _IC_IN_FLIGHT:
            logger.info("IC fulfill skipped — in flight for key=%s", idem)
            return order

    allow_regen = mode in ("same_site_refresh", "annual", "bind_unused") or (
        force and mode == "same_site_refresh"
    )
    if already and not allow_regen and order_id in _PDF_BYTES:
        logger.info("IC fulfill skipped — PDFs already ready for order %s", order_id)
        if idem:
            _IC_IDEMPOTENCY[idem] = order_id
        return order

    if already and allow_regen:
        logger.info(
            "IC regenerate order=%s mode=%s tier=%s force=%s",
            order_id,
            mode,
            tier_ic,
            force,
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
    site_label = ", ".join(
        p
        for p in [
            site_addr,
            f"{site_city}, {site_state} {site_zip}".strip(" ,"),
        ]
        if p
    )

    # Bind site on the order (IC Project one-site lock)
    order["site_address"] = site_addr
    order["site_city"] = site_city
    order["site_state"] = site_state
    order["site_zip"] = site_zip
    order["site_label"] = site_label
    order["project_type"] = str(pi.get("type") or order.get("site_project_type") or "")
    if order.get("project_type"):
        order["site_project_type"] = order["project_type"]

    shaped = analysis_for_pdfs(analysis)
    shaped["preview"] = False
    shaped["depth_tier"] = "ic_full"
    shaped["research_depth"] = "ic"
    shaped.pop("research_id", None)
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

    order["pdf_status"] = "ready"
    if share_meta.get("share_url"):
        order["share_url"] = share_meta["share_url"]
    if share_meta.get("research_id"):
        order["research_id"] = share_meta["research_id"]
    updated = update_order_artifacts(
        order_id,
        pdfs=pdfs,
        analysis_json=shaped,
        address=site_label or site_addr,
        share_url=share_meta.get("share_url"),
        research_id=share_meta.get("research_id"),
        site_address=site_addr,
        site_city=site_city,
        site_state=site_state,
        site_zip=site_zip,
        site_label=site_label,
        site_project_type=str(pi.get("type") or ""),
    )
    logger.info(
        "✅ IC Project PDFs ready order=%s email=%s mode=%s site=%s sizes=%s share=%s",
        order_id,
        email_l,
        mode,
        site_label,
        {k: len(v) for k, v in byte_map.items()},
        share_meta.get("share_url") or "n/a",
    )

    if idem:
        _IC_IDEMPOTENCY[idem] = order_id
        _IC_IN_FLIGHT.discard(idem)

    await _notify_ic_emails_ready(
        email_l,
        order_id,
        pdfs,
        share_url=str(share_meta.get("share_url") or ""),
        site_label=str(site_label or site_addr or ""),
        analysis=shaped,
    )

    out = dict(updated or order or {})
    if share_meta.get("share_url"):
        out["share_url"] = share_meta["share_url"]
    if share_meta.get("research_id"):
        out["research_id"] = share_meta["research_id"]
    return out


async def _notify_ic_emails_ready(
    email_l: str,
    order_id: str,
    pdfs: list,
    *,
    share_url: str = "",
    site_label: str = "",
    analysis: Optional[Dict[str, Any]] = None,
) -> None:
    """Send IC PDF-ready + results emails. Logs hard failures; never raises."""
    from email_service import get_email_service

    svc = get_email_service()
    if not svc:
        logger.error("IC emails skipped — email service not configured (set RESEND_API_KEY)")
        return

    # Prefer app Orders page links in email (Chrome Safe Browsing often flags bare *.onrender.com PDF URLs)
    app = (os.getenv("FRONTEND_APP_URL") or "https://app.regguardagent.com").rstrip("/")
    email_pdfs = []
    for p in pdfs or []:
        if not isinstance(p, dict):
            continue
        row = dict(p)
        name = row.get("name") or row.get("type") or "PDF"
        # Point CTA at My Orders (authenticated by email lookup) — still include API url as secondary
        row["url"] = f"{app}/orders?email={email_l}"
        row["name"] = name
        email_pdfs.append(row)
    if not email_pdfs:
        email_pdfs = [
            {"name": "Research Memo", "url": f"{app}/orders?email={email_l}"},
            {"name": "Punch List", "url": f"{app}/orders?email={email_l}"},
            {"name": "Permit Package", "url": f"{app}/orders?email={email_l}"},
        ]

    # One IC delivery email only (PDF-ready + share). Do NOT also send Bid Risk Receipt
    # here — that caused triple "Bid Risk Receipt" mail when the client also auto-sent.
    try:
        if hasattr(svc, "send_order_pdfs_ready"):
            ok = await svc.send_order_pdfs_ready(
                email_l,
                order_id,
                email_pdfs,
                share_url=share_url or "",
                site_label=site_label or "",
            )
            if ok:
                logger.info("IC PDF-ready email OK order=%s to=%s", order_id, email_l)
            else:
                logger.error("IC PDF-ready email returned False order=%s to=%s", order_id, email_l)
        else:
            logger.error("send_order_pdfs_ready missing on email service")
    except Exception as e:
        logger.exception("IC PDF-ready email failed: %s", e)


def get_cached_pdf_bytes(order_id: str, pdf_type: str) -> Optional[bytes]:
    return (_PDF_BYTES.get(order_id) or {}).get(pdf_type)


def ensure_pdf_bytes(
    order_id: str,
    pdf_type: str,
    *,
    email: str = "",
    token: str = "",
    force_refresh: bool = False,
) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Return PDF bytes for download, regenerating from stored analysis if needed.
    Requires matching download_token when the order has one set.
    Returns (bytes, error_message).
    """
    if pdf_type not in PDF_TYPES:
        return None, "Invalid PDF type"

    from order_service import get_raw_order_by_id

    try:
        from ic_pdf_enrichment import PDF_FORMAT_VERSION
    except Exception:
        PDF_FORMAT_VERSION = 5

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

    analysis = order.get("analysis_json")
    stored_ver = 0
    if isinstance(analysis, dict):
        try:
            stored_ver = int(analysis.get("pdf_format_version") or 0)
        except (TypeError, ValueError):
            stored_ver = 0

    # Always regenerate when format bumped, or caller requests refresh
    need_regen = force_refresh or stored_ver < PDF_FORMAT_VERSION
    if need_regen and order_id in _PDF_BYTES:
        _PDF_BYTES.pop(order_id, None)

    cached = get_cached_pdf_bytes(order_id, pdf_type)
    if cached and not need_regen:
        return cached, None

    if not isinstance(analysis, dict) or not analysis:
        return None, "PDFs not ready — run a site lookup after purchase to generate your report"

    try:
        byte_map = generate_ic_pdf_bytes(analysis)
        _PDF_BYTES[order_id] = byte_map
        from order_service import update_order_artifacts

        # Stamp format version so next download can skip unless bumped again
        analysis = dict(analysis)
        analysis["pdf_format_version"] = PDF_FORMAT_VERSION
        update_order_artifacts(
            order_id,
            pdfs=build_pdf_meta(
                order_id,
                order_email or email_l,
                byte_map,
                download_token=order_token,
            ),
            analysis_json=analysis,
        )
        return byte_map.get(pdf_type), None
    except Exception as e:
        logger.exception("Regenerate IC PDF failed: %s", e)
        return None, "Failed to regenerate PDF"
