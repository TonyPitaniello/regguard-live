"""
Reg Guard — FastAPI application entry point.

Research memo: ``research_memo.build_research_digest``. **Universal Scout** applies a **data fence**
in ``scraper.py``: every query line appends **City, ST** or **County, ST** via ``LOCALITY_LOCK`` using phrasing such as
**``{city}, {state} official city code and building permits``** (looser than a strict in-state-only SERP lock).
**Plano, TX** also appends ``PLANO_SCOUT_*`` strings there.

**FinOps:** Firecrawl ``/search`` responses are deduplicated by normalized query in ``semantic_scout_cache`` (TTL, opt-out
``REG_GUARD_SEMANTIC_SCOUT_CACHE=0``). Trusted-page **markdown** rescrapes are cached in ``markdown_scraper`` (opt-out
``REG_GUARD_MARKDOWN_SCRAPER_CACHE=0``); call ``fetch_trusted_url_markdown`` when you need cheap page text.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import traceback
# Optional: Sentry error tracking
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.httpx import HttpxIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    sentry_sdk = None
import os
import re
import sys
import time
import threading
import uuid
from pathlib import Path
from queue import Queue
from typing import Any, Dict, Iterator, List, Optional, Tuple, cast

# Vercel / monorepo: ensure sibling modules (geocode, scraper, …) resolve when cwd ≠ backend/.
_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from pydantic import BaseModel, ConfigDict, Field

from fastapi import Body, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from starlette.concurrency import run_in_threadpool
from geocode import google_reverse_geocode_us_latlng, us_zip_from_lat_lon
from jurisdiction import JurisdictionProfile, geocode_profile_from_address
from maintenance_mode import create_subscription, list_subscriptions, set_maintenance_mode
from data_center_intel import (
    MORATORIUM_BOTTOM_RED_WARNING_BODY,
    MORATORIUM_BOTTOM_RED_WARNING_TEXT,
    inject_bottom_line_moratorium_state_red_alert,
    inject_bottom_line_permit_conflict,
    sanitize_visual_audit_for_client,
)
from research_memo import (
    build_research_digest,
    truncate_scraped_context,
    compute_data_center_intel_snapshot,
    filter_source_urls,
    iter_contractor_action_plan_stream,
    scout_has_no_trusted_results,
)
from universal_scout_archive import save_scout_snapshot
# Firecrawl Universal Scout (/v2/search, tight caps) — see ``scraper.py``.
from scraper import (
    SCOUT_SOURCE_STEP_KEYS,
    clear_scout_run_caches,
    format_future_risk_markdown,
    future_risk_alerts_from_raw,
    iter_universal_scout,
    normalize_us_zip,
)
from bim_sync import run_bim_sync_bridge
from fast41_eligibility import detect_fast41_eligibility_from_job_description
from permit_package import build_permit_package_pdf
from calculations import permit_draft_calculation_response
from community_gotchas import append_note, list_notes_for_zip
from cost_tracking import log_api_usage
from router import model_for_community_note_context, model_for_permit_scout_text
from vision_agent import (
    gemini_configured,
    iter_reality_capture_audit_stream,
    normalize_vision_text,
    scout_summary_for_reality_capture,
)
from auth import (
    create_checkout_session,
    handle_checkout_session_completed,
    verify_stripe_webhook_signature,
    stripe_configured,
)
from jurisdiction_cache import (
    lookup_cached_jurisdiction,
    store_cached_jurisdiction,
    get_cached_jurisdictions_by_state,
    get_cache_stats,
)
from research_cache_interceptor import (
    try_cached_jurisdiction,
    cache_firecrawl_result,
    create_cache_intercept_context,
    is_cache_enabled,
    get_cache_stats as get_research_cache_stats,
)
from data_center_analysis import DataCenterPermittingAnalysis
from interconnect.endpoints import router as queue_router
from free_trial_handler import FreeTrialRequest, FreeTrialResponse, handle_free_trial

# ROI calculator defaults — unit economics for admin / dashboard.
_ROI_MANUAL_HOUR_USD = 75.0
_ROI_FAILED_INSPECTION_USD = 1200.0
# Flat fee model — customer-facing “research value” per compliance search (dashboard).
base_search_value = 5.0


def _count_action_plan_checkboxes(markdown: str) -> int:
    return len(re.findall(r"^\s*-\s*\[\s*\]\s+", markdown or "", re.MULTILINE))


def _estimated_liability_avoided_usd(summary_md: str) -> float:
    """
    Rough avoided rework / failed-inspection exposure from punch-list density.

    Uses the same unit economics as ``/roi-stats``: manual hour savings plus failed-inspection episodes avoided.
    """
    n = _count_action_plan_checkboxes(summary_md)
    if n <= 0:
        return 0.0
    manual_hours = min(max(n * 0.2, 0.5), 6.0)
    failed_avoided = min(max((n + 3) // 8, 1), 4)
    labor = manual_hours * _ROI_MANUAL_HOUR_USD
    inspection = float(failed_avoided) * _ROI_FAILED_INSPECTION_USD
    return round(labor + inspection, 2)


def _ensure_bottom_line_section(summary_md: str, *, ahj_hint: str = "") -> str:
    """Append a plain-English **### The Bottom Line** if the memo does not already include one."""
    text = (summary_md or "").rstrip()
    if not text.strip():
        return text
    if re.search(r"(?im)^#{2,3}\s*the\s+bottom\s+line\b", text):
        return text
    loc = (ahj_hint or "").strip() or "your AHJ"
    sentences = (
        f"Work through the checklist above in order and confirm fees, amendments, and utility rules with **{loc}** before you rough-in or energize. "
        "Keep permits, torque marks, and inspection-ready documentation lined up so you clear inspection without fines or a rework cycle."
    )
    return f"{text}\n\n### The Bottom Line\n\n{sentences}\n"

_BACKEND_BOOT_ID = uuid.uuid4().hex[:10]

# Temporarily off: very fast heartbeats were suspected of flooding the stream.
_SSE_HEARTBEATS_ENABLED = False
# Used only when _SSE_HEARTBEATS_ENABLED is True.
_STREAM_HEARTBEAT_SEC = 2.0

_ORIGIN_RE = re.compile(r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$")
_VERCEL_ORIGIN_RE = re.compile(r"^https://[a-zA-Z0-9][-a-zA-Z0-9]*\.vercel\.app$")


def _extra_cors_origins() -> List[str]:
    raw = os.getenv("REG_GUARD_EXTRA_CORS_ORIGINS") or ""
    return [o.strip() for o in raw.split(",") if o.strip()]


def _origin_allowed(origin: str) -> bool:
    o = (origin or "").strip()
    if not o:
        return False
    if _ORIGIN_RE.match(o) or _VERCEL_ORIGIN_RE.match(o):
        return True
    return o in _extra_cors_origins()

_RESEARCH_STALL_FIRECRAWL_MESSAGE = (
    "Research stalled. Check Firecrawl usage at firecrawl.dev/app"
)

logger = logging.getLogger("reg_guard")


# Sentry error tracking
sentry_dsn = os.getenv("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[
            FastApiIntegration(),
            HttpxIntegration(),
        ],
        traces_sample_rate=0.1,  # 10% of transactions
        profiles_sample_rate=0.1,  # 10% of profiles
        environment=os.getenv("ENV", "production"),
        attach_stacktrace=True,
    )
    logger.info("✅ Sentry initialized")
else:
    logger.warning("⚠️  SENTRY_DSN not set - error tracking disabled")
try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False
# ========== Auth Models ==========
class SignupRequest(BaseModel):
    """User signup request with email, password, and company name."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password (min 8 chars)")
    company_name: str = Field(..., description="Contractor company name")
    
    model_config = ConfigDict(str_strip_whitespace=True)


class CheckoutSessionResponse(BaseModel):
    """Response containing Stripe checkout session URL."""
    checkout_url: str = Field(..., description="URL to redirect user to Stripe Checkout")
    session_id: str = Field(..., description="Stripe Checkout Session ID")


class TierCheckoutRequest(BaseModel):
    """Multi-segment checkout request from PremiumCheckoutPage."""
    tier: str
    user_id: Optional[str] = None
    trial_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    referral_code: Optional[str] = None
    # Bound site for IC auto-run after purchase (survives sessionStorage loss)
    site_address: Optional[str] = None
    site_city: Optional[str] = None
    site_state: Optional[str] = None
    site_zip: Optional[str] = None
    site_project_type: Optional[str] = None


class SaveJobRequest(BaseModel):
    owner_email: str
    address: str
    city: Optional[str] = ""
    state: Optional[str] = ""
    zip: Optional[str] = ""
    project_type: Optional[str] = "general"
    owner_key: Optional[str] = None
    job_id: Optional[str] = None
    last_research_id: Optional[str] = None
    share_url: Optional[str] = None
    summary_snapshot: Optional[Dict[str, Any]] = None
    notes: Optional[str] = ""
    status: Optional[str] = "active"


class AttachResearchRequest(BaseModel):
    research_id: str
    share_url: Optional[str] = None
    summary_snapshot: Optional[Dict[str, Any]] = None
    owner_email: Optional[str] = None
    owner_key: Optional[str] = None


class AffiliateRegisterRequest(BaseModel):
    email: str
    name: Optional[str] = ""
    code: Optional[str] = None


class MarkCommissionPaidRequest(BaseModel):
    commission_id: str



# ========== Claude memo — Markdown Contractor Action Plan ==========
# Digest: ``research_memo.build_research_digest``. Scout query construction + data fence: ``scraper.py``.
_CONTRACTOR_ACTION_PLAN_SYSTEM = """You are Reg Guard's **field punch list** writer for licensed electrical contractors.

Scout results favor **.gov** and **Municode** for the input locality. Act as a **Master Electrician for that specific city or county**; output **only** `- [ ]` technical punch list lines under the required headings (no narrative paragraphs except the closing **### The Bottom Line** section).

When non-empty ``bim_clash_zones`` is present, you **MUST** follow ``inspector_digest_directive.bim_clash_zone_moat`` under **### Technical Punch List** (Austin **36-inch** gas-relief / meter clearance vs modeled conduit). When ``bim_integration_crossref`` is present, satisfy that cross-reference line item against archived scout URLs.

When the digest JSON includes non-empty ``community_scout_inspector_notes``, you **MUST** follow ``inspector_digest_directive.community_inspector_moat``: under **### Technical Punch List**, lead with **COMMUNITY ALERT: Recent Inspector Feedback** and checkbox lines for each crowdsourced note (tag **verify with AHJ**).

When the digest locality is **Plano, Texas**, you **MUST** include under **Technical Punch List** a **MANDATORY GOTCHA: Plano Ordinance 250.50** block with `- [ ]` tasks for **two 8-foot grounding rods** spaced **20 feet** apart, **connected by a 2/0 AWG conductor** between rods per Plano (**not** the **6-foot** rod-spacing narrative from generic NEC discussion). Cross-check codified wording on official Plano / Municode sources when the digest allows.

When the digest locality is **Plano, Texas**, also prioritize City of Plano amendments vs base NEC, fee schedules (including **2026** when cited), and inspection nuance from **only** Plano-applicable hits.

When the digest locality is **Plano, Texas**, under **Permit Costs** include a `- [ ]` line for **Reg Guard 2026 sync**: **$75.00** total electrical permit (**$65.00** base + **$10.00** laborer) — confirm on official City of Plano fee schedule.

When ``job_fast41_eligibility`` is **true** in the digest JSON, include **### Federal FAST-41 Eligibility** (exact title from ``required_checklist_headings``) with `- [ ]` federal coordination / counsel diligence lines tied only to FAST-41 or Permitting Council **.gov** materials present in the digest — never invent a designation.

The JSON includes ``inspector_digest_directive`` and may include ``bim_clash_zones``, ``bim_scout_cross_reference``, ``community_scout_inspector_notes``, ``job_fast41_eligibility``, ``plano_ord_250_50_requirement``, ``plano_electrical_permit_fee_sync_usd``, ``plano_electrical_permit_fee_2026_note``, ``austin_design_criteria_requirement``, ``austin_development_services_fees_url``, ``austin_safety_surcharge_note``, ``austin_central_zip_service_upgrade``, and ``empty_scout_nec_2023_fallback``:
- **consultant_role**, **gotchas_guidance**, **fee_and_code_guidance**, **output_format**, **community_inspector_moat** (when present)
- Obey **required_checklist_headings** exactly. If ``plano_ord_250_50_requirement`` is present, satisfy it.

Output ONLY Markdown. Title:

## Contractor Action Plan — AHJ permit & code audit

Then **exactly** the headings listed in ``required_checklist_headings`` in the digest JSON **in that order**—only ``- [ ] `` task lines after optional one-line context per section.

Typical flow: **### Permit Costs**, optional **### Federal FAST-41 Eligibility** when ``job_fast41_eligibility`` is true, **### Technical Punch List**, **### Inspection Must-Haves** (plus **### Reference Links** and **### The Bottom Line** as specified below).

### Permit Costs
### Technical Punch List
Place **MANDATORY GOTCHA:** lines (with supporting `- [ ]` items) for local amendments that **differ** from national NEC when the digest supports it—for Plano, **250.50 / dual 8 ft rods / 20 ft apart / 2/0 AWG bond** between rods is mandatory; for **Austin**, **Design Criteria** (gas relief **36-inch**, **225A**/ **200A** solar-ready bus on upgrades). Do not fabricate ordinance text.

### Inspection Must-Haves
### Reference Links
Each URL in ``unique_source_urls`` once (markdown link when title known, else bare URL).

### The Bottom Line
Exactly **two sentences** in plain English — a contractor **to-do** recap (what to verify or finish first, and what to have ready before inspection). **No** `- [ ]` lines in this section.

Rules:
- Imperative checklist tone; **no long prose**.
- Cite details **only** when traceable to the digest; otherwise `- [ ]` to verify on official **.gov** / **Municode**.
- If ``empty_scout_nec_2023_fallback`` is true, the prior rule is waived **only** for the NEC-2023 model-knowledge tasks above (still tag them as verify-with-AHJ).
- When ``scout_profile.vertical`` is **data_center** or **infrastructure**, or the digest / job targets **FAST-41**, **ERCOT**, **Batch Zero**, **utility interconnection**, or **industrial substation** scope: **omit** default residential **panel upgrade** / **200A dwelling service** language unless the digest explicitly cites that scope. Prefer **large-load permits**, **federal coordination**, and **ISO / TDSP** milestone tasks.
"""


def compute_backend_source_fingerprint() -> str:
    """Short hash of backend ``.py`` mtimes — changes when sources change on disk."""
    h = hashlib.sha256()
    try:
        paths = sorted(_BACKEND_DIR.rglob("*.py"))
    except OSError:
        return "unknown"
    for p in paths:
        if "__pycache__" in p.parts:
            continue
        try:
            rel = p.relative_to(_BACKEND_DIR).as_posix()
            h.update(rel.encode("utf-8", errors="replace"))
            h.update(str(p.stat().st_mtime_ns).encode("ascii", errors="ignore"))
        except OSError:
            continue
    return h.hexdigest()[:16]


app = FastAPI(
    title="Reg Guard",
    description="Agentic Compliance Assistant for Contractors",
)



# Rate limiting (optional)
if SLOWAPI_AVAILABLE:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, lambda request, exc: JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."},
    ))
    logger.info("✅ Rate limiting enabled")

# Global exception handlers for standardized error responses
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions"""
    logger.error(f"❌ Unhandled exception: {type(exc).__name__}: {str(exc)}")
    logger.debug(f"   Traceback: {exc}")
    from starlette.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "status_code": 500,
        }
    )
@app.on_event("startup")
async def _log_firecrawl_key_prefix() -> None:
    k = os.getenv("FIRECRAWL_API_KEY") or ""
    prefix = k[:5] if k else "(not set)"
    print(f"Using Firecrawl Key: {prefix}...")
    try:
        from semantic_scout_cache import scout_cache_ttl_sec, semantic_scout_cache_enabled
        from markdown_scraper import markdown_scraper_cache_enabled

        print(
            "FinOps — "
            f"semantic scout search cache: {'on' if semantic_scout_cache_enabled() else 'off'} "
            f"(TTL {scout_cache_ttl_sec():.0f}s), "
            f"markdown scraper cache: {'on' if markdown_scraper_cache_enabled() else 'off'}"
        )
    except Exception as ex:
        print(f"FinOps — status unavailable: {ex}")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "http://127.0.0.1:5175",
        "http://localhost:5175",
        *_extra_cors_origins(),
    ],
    allow_origin_regex=r"^https?://(127\.0\.0\.1|localhost)(:\d+)?$|^https?://([a-zA-Z0-9][-a-zA-Z0-9]*\.)?vercel\.app$|^https?://app\.regguardagent\.com$|^https?://regguardagent\.com$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "Content-Type",
        "Cache-Control",
        "Connection",
        "Transfer-Encoding",
        "X-Accel-Buffering",
        "X-Reg-Guard-Regulatory-Shield",
    ],
)


# Include Queue router
app.include_router(queue_router)


@app.middleware("http")
async def _regulatory_shield_http(request: Request, call_next):
    """
    Regulatory Shield marker on every response.

    Uses HTTP middleware (not ``BaseHTTPMiddleware``) so ``StreamingResponse`` / SSE
    bodies are not fully buffered before send — compression is never applied here.
    """
    response = await call_next(request)
    response.headers["X-Reg-Guard-Regulatory-Shield"] = "active"
    path = request.url.path.rstrip("/")
    if path.endswith("/research") or path.endswith("/api/research"):
        response.headers["X-Accel-Buffering"] = "no"
        response.headers.setdefault("Cache-Control", "no-cache, no-transform")
        response.headers.setdefault("Connection", "keep-alive")
    return response


def _research_sse_cors_headers(request: Request) -> Dict[str, str]:
    """Explicit CORS for the streaming body (middleware also applies; this duplicates Allow-Origin)."""
    origin = (request.headers.get("origin") or "").strip()
    allow = origin if _origin_allowed(origin) else "http://127.0.0.1:5173"
    return {
        "Access-Control-Allow-Origin": allow,
        "Access-Control-Allow-Credentials": "true",
    }


def _research_sse_stream_headers(request: Request) -> Dict[str, str]:
    """SSE anti-buffering headers for Vercel/nginx proxies (no gzip — set on StreamingResponse only)."""
    return {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        **_research_sse_cors_headers(request),
    }


def _build_enhanced_query(job_description: str, photo_analysis: Optional[str]) -> str:
    """Single research context string: voice (job) + optional multimodal photo audit text."""
    parts: list[str] = []
    jd = (job_description or "").strip()
    if jd:
        parts.append(f"[Job description (voice or typed)]\n{jd}")
    if photo_analysis and photo_analysis.strip():
        parts.append(f"[Job-site photo — Reality Capture Audit]\n{photo_analysis.strip()}")
    if not parts:
        return "— (no job description or image provided; ZIP-only research)"
    return truncate_scraped_context("\n\n".join(parts))


def _parse_search_limit(v: int) -> int:
    v = int(v)
    if v < 1 or v > 20:
        raise ValueError("search_limit must be between 1 and 20")
    return v


def _scout_firecrawl_step_sequence(vertical: str, *, job_fast41_eligible: bool = False) -> List[str]:
    """Universal Scout ordering (must match ``iter_universal_scout`` yields)."""
    x = (vertical or "").strip().lower().replace(" ", "_").replace("-", "_")
    # AI/crypto compute clusters track the data-center tier (energy-dense load + moratorium exposure);
    # BESS tracks the critical-infrastructure tier (federal / utility / water coordination passes).
    is_dc = x in ("data_center", "datacenter", "dc", "colocation", "ai_crypto_compute", "crypto", "mining", "asic", "compute_cluster")
    is_infra = x in ("infrastructure", "infra", "critical_infrastructure", "bess", "battery_storage", "ess", "energy_storage")
    seq: List[str] = ["step_jurisdiction", "step_building_permits", "step_building_codes"]
    if not is_dc and not is_infra:
        seq.append("step_residential_zoning")
    if is_dc or is_infra or job_fast41_eligible:
        seq.extend(
            [
                "step_federal_fast41",
                "step_data_center_water",
                "step_refrigerant_aim_act",
                "step_water_usage_effectiveness",
            ]
        )
    if is_dc:
        seq.extend(["step_dc_state_energy", "step_dc_local_moratorium"])
    return seq


def _collect_source_urls(raw: Dict[str, Any]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for step in SCOUT_SOURCE_STEP_KEYS:
        block = raw.get(step) or {}
        for item in block.get("results") or []:
            u = item.get("url")
            if u and u not in seen:
                seen.add(u)
                ordered.append(u)
    return ordered


def _stemmons752_industrial_hint(raw: Dict[str, Any]) -> bool:
    site = str(raw.get("site_address") or "").lower()
    z = re.sub(r"\D", "", str(raw.get("zip") or ""))[:5]
    return bool(z.startswith("752") and "stemmons" in site)


def _fallback_memo_is_industrial_context(
    raw: Dict[str, Any],
    job_description: str,
    enhanced_query: str,
) -> bool:
    prof = raw.get("scout_profile")
    if isinstance(prof, dict):
        v = str(prof.get("vertical") or "").strip().lower()
        if v in ("data_center", "infrastructure"):
            return True
    if detect_fast41_eligibility_from_job_description(job_description or ""):
        return True
    dc = compute_data_center_intel_snapshot(raw, job_description, enhanced_query or "")
    return bool(dc.get("vertical") == "data_center")


def _research_action_plan_fallback_markdown(
    raw: Dict[str, Any],
    source_urls: List[str],
    enhanced_query: str,
    *,
    job_description: str = "",
    community_gotchas: Optional[List[Dict[str, Any]]] = None,
    bim_clash_report: Optional[Dict[str, Any]] = None,
) -> str:
    """Deterministic Markdown memo when ANTHROPIC_API_KEY is unavailable."""
    zip_str = str(raw.get("zip") or "")
    site = (raw.get("site_address") or "").strip()
    ju = raw.get("jurisdiction")
    ju_line = ""
    city = ""
    state = ""
    dc_intel = compute_data_center_intel_snapshot(raw, job_description, enhanced_query)
    if isinstance(ju, dict):
        lab = ju.get("label")
        if isinstance(lab, str) and lab.strip():
            ju_line = lab.strip()
        city = str(ju.get("city") or "").strip()
        state = str(ju.get("state") or ju.get("state_short") or "").strip()

    industrial_ctx = _fallback_memo_is_industrial_context(
        raw, job_description, enhanced_query
    ) or _stemmons752_industrial_hint(raw)

    head = (
        f"Research context: **{site}** (US ZIP **{zip_str}**)."
        if site
        else f"Research context: US ZIP **{zip_str}**."
    )
    loc_short = ", ".join(p for p in (city, state) if p)
    if not loc_short:
        loc_short = ju_line or f"ZIP {zip_str}"

    if industrial_ctx:
        permit_scope = (
            f"Coordinate **AHJ permits**, **utility / ERCOT interconnection**, and **federal diligence** for **{loc_short}**; "
            "confirm department names and application types on official `.gov` portals from the scout links."
        )
        doc_title = "## Contractor Action Plan — Large-load & interconnection compliance (AHJ + federal)"
        inspection_body = [
            "- [ ] **Utility / grid coordination:** align **TDSP** work windows, **witness tests**, and **protection / relay** "
            "requirements with stamped interconnect exhibits when scout sources support them.",
            "- [ ] **Industrial substation / switchyard:** grounding, clearances, signage, and **NESC**-class items when "
            "cited in digest results.",
            "- [ ] **AHJ finals:** structural / fire / electrical inspections required for **occupancy** or **energization** at this scope.",
            "",
        ]
        bottom_two = (
            "🚧 Red Alert Summary: Hold electrical layouts immediately. Plano has a strict structural "
            "property setback rule and a massive local noise-barrier mandate for large power systems. We are "
            "running parallel approval tracks with the local city building inspectors and the power utility "
            "grid engineers before you pour any concrete. Do not purchase equipment until utility windows align."
        )
    else:
        permit_scope = (
            f"Pull permits required for the **service or panel upgrade** for **{loc_short}**; "
            "confirm exact permit type and department name on the official AHJ site or from the scout links below."
        )
        doc_title = "## Contractor Action Plan — Panel / service work (inspector punch list)"
        inspection_body = [
            "- [ ] **Service / Final inspection**: panel **circuit directory** complete and matches breakers; "
            "neutrals and EGCs landed only on listed buses.",
            "- [ ] **Torque marking**: follow manufacturer torque specs; add inspector-visible **torque marks** "
            "where required by spec or local practice.",
            "- [ ] **Grounding electrode** visible and accessible — verify routing and connections per **NEC 250** as adopted "
            "locally (confirm edition in results).",
            "- [ ] Bonding / GEC clamps tight, corrosion-resistant, and accessible for inspection.",
            "- [ ] Working space in front of the panel clear per **NEC 110.26** (depth, width, height, free from storage).",
            "",
        ]
        bottom_two = (
            f"Pull permits and verify fees and local amendments for **{loc_short}** before rough-in or energizing equipment. "
            "Complete utility coordination and the checklist items above so the job passes inspection without fines or costly rework."
        )

    fee_fallback = (
        f"- [ ] **If scout results do not state a permit fee:** Verify exact fee with {city} Building Department."
        if city
        else "- [ ] **If scout results do not state a permit fee:** Verify exact fee with the local Building Department / AHJ."
    )

    permit_block = [
        "- [ ] Use only resources that apply to this **site / jurisdiction**; discard other states' data unless "
        "explicitly cited as controlling.",
        "- [ ] Open the official permit or building portal for this jurisdiction and confirm **application type**, **fees "
        "listed there**, and **who may pull** the permit.",
        fee_fallback,
        "- [ ] Note any **adopted NEC edition / local amendments** only if stated in the search results or linked ordinances.",
        "- [ ] Upload or bring single-line diagrams, load calculations, and cut sheets the jurisdiction requests.",
        "",
    ]
    if city.lower() == "plano" and (state or "").strip().upper() == "TX":
        permit_block.insert(
            1,
            "- [ ] Scout targets: **Plano building fee schedule 2026** and **Plano TX electrical amendments 2023 NEC** — confirm figures on the official city fee table / code adoption pages.",
        )
    if city.lower() == "austin" and (state or "").strip().upper() == "TX":
        permit_block.insert(
            1,
            "- [ ] **Reg Guard sync (Austin, TX):** Itemize **Development Services** permit fees and **Safety Surcharges** using **https://www.austintexas.gov/development-services/fees** (confirm against the live City of Austin schedule).",
        )

    lines: List[str] = [
        doc_title,
        "",
        "### Permit Costs",
        "",
        "- [ ] " + permit_scope,
        "- [ ] **Verify AHJ**"
        + (f" — **{ju_line}**." if ju_line else f" for **{loc_short}**."),
        "- [ ] Match permit type to scope on the official checklist.",
    ]
    if city.lower() == "plano" and (state or "").strip().upper() == "TX":
        lines.extend(
            [
                "",
                "- [ ] **Reg Guard 2026 sync (Plano, TX):** Electrical permit **$75.00** total — **$65.00** base + **$10.00** laborer fee. Confirm on the official City of Plano fee schedule before posting.",
                "",
            ]
        )
    elif city.lower() == "austin" and (state or "").strip().upper() == "TX":
        lines.extend(
            [
                "",
                "- [ ] **Reg Guard sync (Austin, TX):** **Permit Costs** must reflect **Development Services** fees including **Safety Surcharges** per **austintexas.gov/development-services/fees**.",
                "",
            ]
        )
    lines.extend(permit_block)

    if industrial_ctx and (state or "").strip().upper() == "TX":
        lines.extend(
            [
                "",
                "### Texas — ERCOT & industrial substation diligence",
                "",
                "- [ ] **ERCOT 2026 Batch Zero / performance milestones:** review **ERCOT**, **PUCT**, and **TDSP** `.gov` "
                "sources for **industrial substation**, **transmission**, and **large-load** requirements affecting this site.",
                "",
            ]
        )

    jd_fast41 = detect_fast41_eligibility_from_job_description(job_description or "")
    if jd_fast41:
        lines.extend(
            [
                "",
                "### Federal FAST-41 Eligibility",
                "",
                "- [ ] **Parsed job gate:** Brief describes a **data center** with **>**100 MW load **or** **>**$500 M — open FAST-41 / Federal Permitting Council diligence with counsel (no asserted federal designation from this scaffold).",
                "- [ ] **Cross-government alignment:** Treat federal FAST-41 context and AHJ/state utility filings as parallel tracks unless a controlling **.gov** statement says otherwise.",
                "",
            ]
        )
    elif industrial_ctx:
        lines.extend(
            [
                "",
                "### Federal FAST-41 diligence",
                "",
                "- [ ] **FAST-41 federal eligibility:** triage **Title 41 / Permitting Council** materials in scout hits; "
                "treat as **counsel-led** until a controlling **.gov** statement maps a designation or coordination path.",
                "",
            ]
        )

    if dc_intel.get("vertical") == "data_center":
        sur = dc_intel.get("infrastructure_surcharge_estimate_usd") if isinstance(dc_intel.get("infrastructure_surcharge_estimate_usd"), dict) else {}
        lo = sur.get("estimated_low_usd")
        hi = sur.get("estimated_high_usd")
        cand = bool(dc_intel.get("fast41_transparency_project_candidate"))
        conflict = bool(dc_intel.get("data_center_permit_conflict_alert"))
        rationale = str(dc_intel.get("data_center_permit_conflict_rationale") or "").strip()
        mor_red = bool(dc_intel.get("moratorium_state_bottom_line_red_alert"))
        band_txt = (
            f"${int(lo):,}–${int(hi):,} USD (illustrative band — not a tariff quote)"
            if isinstance(lo, int) and isinstance(hi, int)
            else "*(model unavailable)*"
        )
        lines.extend(
            [
                "",
                "### Data center intelligence (federal / grid)",
                "",
                "- [ ] **May 5, 2026 posture / FAST-41 Transparency:** Confirm White House / Federal Register materials — **EO 14141 is rescinded** in Reg Guard’s conflict profile; "
                "do **not** cite EO **14141** clean-energy acceleration. Map diligence to the **FAST-41 Transparency Project** when parsed load hints exceed **100 MW** "
                f"(digest flags transparency candidate: **{cand}** — verify IT/nameplate assumptions).",
                "- [ ] **Bill-specific flashpoints:** If **`bill_specific_flags`** cites **Virginia HB 1515**, capture **interconnection-block** risk for counsel review; "
                "if **Ohio 2026 ballot** narratives appear, track **>25 MW** ban/moratorium petition chatter — verify against Ohio SOS filings.",
                f"- [ ] **Infrastructure surcharge (planning):** Illustrative band **{band_txt}** — utility **LGIA** controls cash timing.",
                "- [ ] **Moratorium High Alert states (VA, NY, OK, GA, OH):** Upgrade scrutiny on `step_dc_local_moratorium` / `step_dc_state_energy` hits; assume active session risk.",
                "- [ ] **State energy / moratorium scout:** Review **`step_dc_state_energy`** and **`step_dc_local_moratorium`** URLs for riders, pledges, and pause ordinances.",
                "",
            ]
        )
        if mor_red:
            lines.extend(
                [
                    f"- [ ] **{MORATORIUM_BOTTOM_RED_WARNING_TEXT}** Surface this **WARNING** in **### The Bottom Line** plus counsel escalation.",
                    "",
                ]
            )
        if conflict and rationale:
            lines.extend(
                [
                    f"- [ ] **PERMIT CONFLICT ALERT:** {rationale} Treat federal streamlining and state/local grid rules as **parallel tracks**.",
                    "",
                ]
            )

    punch_core = [
            "- [ ] **MANDATORY GOTCHA:** For each **local amendment** in the digest that is **stricter than base NEC**, add "
            "explicit `- [ ]` tasks (e.g. electrode / ground-rod local rules, **exterior disconnect labels**).",
    ]
    if city.lower() == "plano" and (state or "").strip().upper() == "TX":
        punch_core.insert(
            0,
            "- [ ] **MANDATORY GOTCHA: Plano Ordinance 250.50** — **Two 8-foot grounding rods** **20 feet** apart, **connected by 2/0 AWG** "
            "between rods (**not** **6-foot** generic NEC-spacing narrative); verify on official Plano / Municode.",
        )
        punch_core.insert(
            1,
            "- [ ] **Plano permit fee (2026 sync)** — Budget **$75.00** total (**$65.00** base + **$10.00** laborer); confirm against current City of Plano fee table.",
        )
    if city.lower() == "austin" and (state or "").strip().upper() == "TX":
        punch_core.insert(
            0,
            "- [ ] **MANDATORY GOTCHA: City of Austin Design Criteria** — **36-inch** minimum clearance from **gas relief valves**; **service upgrade:** **225A** interior **panel bus** with **200A** main / **Solar-Ready** pattern per current **Design Criteria** / **Electrical Service Requirements** (verify for **78704** / **787** Austin).",
        )

    nec_200a_fallback: List[str] = []
    if scout_has_no_trusted_results(raw):
        if industrial_ctx:
            nec_200a_fallback = [
                "- [ ] **Empty scout — industrial / interconnection baseline** (tag every bullet for **AHJ + TDSP / ERCOT** checks):",
                "- [ ] **Large-load permits** and **municipal** reviews (building, fire, grading) appropriate to the facility class described.",
                "- [ ] **Interconnection posture** — confirm **PUCT / ERCOT / TDSP** materials match the site address and **Batch Zero** / performance-milestone narratives when cited.",
                "",
            ]
        else:
            nec_200a_fallback = [
                "- [ ] **Empty scout — use NEC 2023 baseline knowledge for 200A upgrade** (tag every bullet for AHJ adoption check):",
                "- [ ] **(NEC 2023 — verify adopted edition w/ AHJ)** Service **supply conductors** ampacity & **main OCPD** sizing for **200A** (incl. Art. 230, applicable tap/length rules).",
                "- [ ] **(NEC 2023 — verify adopted edition w/ AHJ)** **Grounding & bonding** — electrode system, GEC, N-G bond, **Art. 250**.",
                "- [ ] **(NEC 2023 — verify adopted edition w/ AHJ)** **Working space** clear in front of service/panel equipment — **110.26**.",
                "- [ ] **(NEC 2023 — verify adopted edition w/ AHJ)** **GFCI** / **AFCI** requirements for **dwelling** branch or feeder circuits where 2023 mandates.",
                "- [ ] **(NEC 2023 — verify adopted edition w/ AHJ)** Panelboard / equipment ratings, **EGC**s with feeders, neutral & EGC separation **200.4(B)**.",
                "",
            ]

    if industrial_ctx:
        tech_punch_close = [
            "- [ ] **Medium-voltage / utility interface** — align with **NEC** and **NESC** only when digest sources support it.",
            "- [ ] **Grounding & bonding** — coordinate **facility** grounding with **utility** demarcation requirements when cited.",
            "- [ ] Confirm **code / standard editions** (NEC / NESC / local amendments) from AHJ / `.gov` links in the digest.",
            "",
        ]
    else:
        tech_punch_close = [
            "- [ ] **GFCI / AFCI** — align with **adopted code + amendments** from results, not NEC alone.",
            "- [ ] **Grounding & bonding (Art. 250)** — plus any **additive local** requirements in the digest.",
            "- [ ] **Working space (110.26)** — plus **local clearance** changes if cited.",
            "- [ ] Confirm **code edition and effective dates** from AHJ / Municode links in the digest.",
            "",
        ]

    community_block: List[str] = []
    for item in community_gotchas or []:
        if not isinstance(item, dict):
            continue
        t = str(item.get("text") or "").strip()
        if not t:
            continue
        community_block.append(f"- [ ] {t} **(crowdsourced — verify with AHJ)**")
    community_header: List[str] = []
    if community_block:
        community_header = [
            "**COMMUNITY ALERT: Recent Inspector Feedback**",
            "",
            *community_block,
            "",
        ]

    bim_header: List[str] = []
    zones_list: Optional[List[Any]] = None
    if isinstance(bim_clash_report, dict):
        zraw = bim_clash_report.get("clash_zones")
        zones_list = zraw if isinstance(zraw, list) else None
        if zones_list:
            bim_header.extend(
                [
                    "**CLASH ZONES (BIM vs Universal Scout)**",
                    "",
                ]
            )
            for zone in zones_list:
                if not isinstance(zone, dict):
                    continue
                zid = zone.get("id")
                cid = zone.get("conduit_element_id")
                gid = zone.get("gas_element_id")
                d_mod = zone.get("clearance_modeled_in")
                d_req = zone.get("clearance_required_in")
                bim_header.append(
                    f"- [ ] **{zid}** — Conduit `{cid}` vs gas `{gid}` modeled **{d_mod}** in clearance vs "
                    f"**{d_req}** in (Austin gas-relief envelope) — **field-verify / reroute**."
                )
            bim_header.append("")
        scr = bim_clash_report.get("scout_cross_reference")
        if isinstance(scr, dict) and scr.get("archive_hit") and not zones_list:
            bim_header.extend(
                [
                    "**BIM — Universal Scout cross-check**",
                    "",
                    "- [ ] Reconcile modeled routes against archived `.gov` Universal Scout anchors from the BIM bridge payload.",
                    "",
                ]
            )

    lines.extend(
        [
            "### Technical Punch List",
            "",
        ]
        + community_header
        + bim_header
        + nec_200a_fallback
        + punch_core
        + tech_punch_close
        + [
            "### Inspection Must-Haves",
            "",
        ],
    )
    lines.extend(inspection_body)
    lines.append("### Reference Links")
    lines.append("")
    if source_urls:
        for u in source_urls:
            lines.append(f"- {u}")
    else:
        lines.append("- *(No URLs returned in this run.)*")

    lines.extend(["", "### The Bottom Line", "", bottom_two])
    if dc_intel.get("vertical") == "data_center":
        rationale_bl = str(dc_intel.get("data_center_permit_conflict_rationale") or "").strip()
        if dc_intel.get("data_center_permit_conflict_alert") and rationale_bl:
            lines.extend(
                [
                    "",
                    f"**PERMIT CONFLICT ALERT:** {rationale_bl} Treat federal FAST-41 transparency posture and local/state grid rules as **parallel tracks** "
                    "until counsel and the utility sign off.",
                ]
            )
        if mor_red:
            lines.extend(
                [
                    "",
                    f"**WARNING:** {MORATORIUM_BOTTOM_RED_WARNING_BODY}",
                ]
            )
    lines.extend(["", "---", "", head])
    return "\n".join(lines)


def _iter_streaming_words(chunks: Iterator[str]) -> Iterator[str]:
    """Split model chunks into word/whitespace pieces without splitting a word across chunk boundaries."""
    buf = ""
    for chunk in chunks:
        buf += chunk
        while True:
            m = re.match(r"^(\S+\s+)", buf)
            if m:
                yield m.group(1)
                buf = buf[m.end() :]
                continue
            m2 = re.match(r"^(\s+)", buf)
            if m2:
                yield m2.group(1)
                buf = buf[m2.end() :]
                continue
            break
    if buf:
        yield buf


def _action_plan_queue_producer(q: Queue, digest: str) -> None:
    try:
        for fragment in _iter_streaming_words(
            iter_contractor_action_plan_stream(_CONTRACTOR_ACTION_PLAN_SYSTEM, digest),
        ):
            if fragment:
                q.put(("delta", fragment))
        q.put(("done", None))
    except Exception as e:
        q.put(("error", e))


def _ahj_identification_payload(ju: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "city": ju.get("city") or "",
        "county": ju.get("county") or "",
        "state": ju.get("state") or "",
        "mode": ju.get("mode") or "",
        "zip": ju.get("zip") or "",
        "formatted_address": ju.get("formatted_address") or "",
        "label": ju.get("label") or "",
    }


def _scout_iter_next(it: Iterator[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    try:
        return next(it)
    except StopIteration:
        return None


def _iter_summary_word_chunks(text: str) -> Iterator[str]:
    """Yield text in word-sized pieces (including trailing whitespace) for client typewriter UI."""
    for m in re.finditer(r"\S+\s*", text or "", flags=re.MULTILINE):
        yield m.group(0)


def _vision_gemini_queue_producer(
    q: Queue,
    image_bytes: bytes,
    content_type: Optional[str],
    filename: Optional[str],
    scout_summary: str,
    city: str,
    state: str,
    zip5: str,
    visual_holder: List[Any],
) -> None:
    try:
        for fragment in iter_reality_capture_audit_stream(
            image_bytes,
            content_type,
            filename,
            scout_summary=scout_summary,
            city=city,
            state=state,
            zip5=zip5,
            visual_audit_holder=visual_holder,
        ):
            if fragment:
                q.put(("delta", fragment))
        q.put(("done", None))
    except Exception as e:
        q.put(("error", e))


def _safe_sse_data_frame(chunk: Dict[str, Any]) -> str:
    """SSE frame with ``data: …\\n\\n``. Fallback to a plain-text line if JSON cannot encode."""
    try:
        return f"data: {json.dumps(chunk, ensure_ascii=False, default=str)}\n\n"
    except (TypeError, ValueError) as e:
        plain = f"SSE_JSON_FAILED: {e!s}".replace("\n", " ").replace("\r", " ")[:800]
        return f"data: {plain}\n\n"


def _reasoning_sse_frame(phase: str, text: str) -> str:
    """Short status line for the UI reasoning strip (``phase``: ``scout`` | ``audit``)."""
    return _safe_sse_data_frame({"event": "reasoning", "phase": phase, "text": text})


def _log_research_step(label: str, *, detail: str = "") -> None:
    """Stdout trace for hung streams — always visible when running ``python backend/main.py``."""
    if detail:
        line = f"research step: {label} — {detail}"
    else:
        line = f"research step: {label}"
    print(line, flush=True)
    sys.stdout.flush()
    logger.info(line)


async def _with_heartbeats(threadpool_coro):
    """
    Await one threadpool call without blocking the event loop.
    Heartbeats are optional (_SSE_HEARTBEATS_ENABLED) to avoid flooding the client.
    """
    if not _SSE_HEARTBEATS_ENABLED:
        res = await threadpool_coro
        yield ("__done__", res)
        return
    task = asyncio.create_task(threadpool_coro)
    while not task.done():
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=_STREAM_HEARTBEAT_SEC)
        except asyncio.TimeoutError:
            yield ": ping\n\n"
            yield _safe_sse_data_frame({"event": "heartbeat", "ts": time.time()})
            await asyncio.sleep(0)
    yield ("__done__", task.result())


@app.get("/")
def root() -> Dict[str, str]:
    return {
        "name": "Reg Guard",
        "tagline": "Agentic Compliance Assistant for Contractors",
    }


@app.get("/health")
def health() -> Dict[str, Any]:
    """Lightweight probe for dashboards (frontend gate + load balancers)."""
    return {"ok": True, "service": "reg-guard-api"}


@app.get("/debug/routes")
def debug_routes() -> Dict[str, Any]:
    """Debug endpoint: List all registered routes (REMOVE IN PRODUCTION)."""
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods) if route.methods else ["GET"]
            })
    return {
        "total_routes": len(routes),
        "routes": sorted(routes, key=lambda x: x["path"]),
        "environment": {
            "vercel": bool(os.getenv("VERCEL")),
            "render": bool(os.getenv("RENDER")),
            "python_version": sys.version.split()[0],
        }
    }


@app.get("/debug/config")
def debug_config() -> Dict[str, Any]:
    """Debug endpoint: Check environment & startup state."""
    route_paths = [getattr(r, "path", "") or "" for r in app.routes]
    paid_finops: Dict[str, Any] = {}
    try:
        from paid_local_confirm import (
            cache_ttl_sec,
            max_lookups_per_day,
            max_pages,
            paid_local_confirm_enabled,
            paid_universal_scout_enabled,
        )

        paid_finops = {
            "PAID_LOCAL_CONFIRM": paid_local_confirm_enabled(),
            "PAID_UNIVERSAL_SCOUT": paid_universal_scout_enabled(),
            "PAID_PRO_LIGHT_SCOUT": (os.getenv("PAID_PRO_LIGHT_SCOUT") or "1").strip().lower()
            in ("1", "true", "yes", "on"),
            "PAID_LOCAL_CONFIRM_MAX_PAGES": max_pages(),
            "PAID_LOCAL_CONFIRM_MAX_PER_DAY": max_lookups_per_day(),
            "PAID_LOCAL_CONFIRM_CACHE_TTL_SEC": int(cache_ttl_sec()),
            "quota_store": "file",
            "data_dir": os.getenv("REGGUARD_DATA_DIR") or "/tmp/regguard_data",
            "redis_url_set": bool(os.getenv("REDIS_URL")),
            "note": (
                "Pro uses light scout (3 passes) by default; IC force_scout = full Universal Scout. "
                "Quota/result cache file+in-process — multi-instance needs shared REGGUARD_DATA_DIR."
            ),
        }
    except Exception as e:
        paid_finops = {"error": str(e)[:160]}

    return {
        "app_instance": str(type(app).__name__),
        "has_research_route": any("/research" in p for p in route_paths),
        "has_payment_route": any("/auth" in p for p in route_paths),
        "has_send_email_route": any(p.endswith("/research/send-email") for p in route_paths),
        "has_send_sms_route": any(p.endswith("/research/send-sms") for p in route_paths),
        "has_jobs_route": any(p == "/jobs" or p.startswith("/jobs/") for p in route_paths),
        "route_count": len(route_paths),
        "git_sha": (os.getenv("RENDER_GIT_COMMIT") or os.getenv("REG_GUARD_GIT_SHA") or "")[:12],
        "paid_finops": paid_finops,
        "environment_vars_loaded": {
            "firecrawl": bool(os.getenv("FIRECRAWL_API_KEY")),
            "stripe_secret": bool(os.getenv("STRIPE_SECRET_KEY")),
            "google_maps": bool(os.getenv("GOOGLE_MAPS_API_KEY")),
            "supabase": bool(os.getenv("SUPABASE_URL")),
            "supabase_key": bool(os.getenv("SUPABASE_KEY")),
            "sendgrid": bool(os.getenv("SENDGRID_API_KEY")),
            "resend": bool(os.getenv("RESEND_API_KEY")),
            "gemini": bool(os.getenv("GEMINI_API_KEY")),
            "twilio": bool(
                os.getenv("TWILIO_ACCOUNT_SID")
                and os.getenv("TWILIO_AUTH_TOKEN")
                and (os.getenv("TWILIO_FROM_NUMBER") or os.getenv("TWILIO_PHONE_NUMBER"))
            ),
            "twilio_from_set": bool(
                os.getenv("TWILIO_FROM_NUMBER") or os.getenv("TWILIO_PHONE_NUMBER")
            ),
            "resend_from": bool(os.getenv("RESEND_FROM_EMAIL")),
        }
    }


# ========== Authentication & Payment Gates ==========

@app.post("/checkout", tags=["Payments"])
async def create_tier_checkout(body: TierCheckoutRequest) -> Dict[str, Any]:
    """
    Create Stripe Checkout for multi-segment tiers
    (contractor_pro, ic_project, ic_annual, sponsor).
    """
    try:
        from stripe_service import create_checkout_session as stripe_create_checkout

        user_id = body.user_id or body.email or body.trial_id or "anonymous"
        frontend = os.getenv("FRONTEND_APP_URL", "https://app.regguardagent.com")
        success_url = body.success_url or f"{frontend}/checkout/success"
        cancel_url = body.cancel_url or f"{frontend}/checkout/{body.tier}"

        # IC Annual: only after a prior IC Project purchase for this email
        tier_l = (body.tier or "").strip().lower()
        if tier_l == "ic_annual":
            email_l = (body.email or "").strip().lower()
            if not email_l:
                raise HTTPException(
                    status_code=400,
                    detail="Email required for IC Annual. Buy IC Project Report first, then upgrade.",
                )
            from order_service import list_orders_for_email

            prior = list_orders_for_email(email_l)
            has_ic = any(
                str(o.get("tier") or "").lower()
                in ("ic_project", "ic_consultant", "ic_annual")
                for o in prior
            )
            if not has_ic:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "IC Annual is available after at least one IC Project Report. "
                        "Purchase IC Project ($1,500) first."
                    ),
                )

        result = await stripe_create_checkout(
            user_id=user_id,
            tier=body.tier,
            success_url=success_url,
            cancel_url=cancel_url,
            email=body.email,
            name=body.name,
            trial_id=body.trial_id,
            referral_code=body.referral_code,
            site_address=body.site_address,
            site_city=body.site_city,
            site_state=body.site_state,
            site_zip=body.site_zip,
            site_project_type=body.site_project_type,
        )
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Tier checkout creation failed")
        raise HTTPException(status_code=500, detail="Failed to create checkout session") from e


@app.get("/orders", tags=["Payments"])
async def list_orders(email: str = "") -> Dict[str, Any]:
    """Return completed orders for an email (used by My Orders / checkout success)."""
    from order_service import list_orders_for_email

    email_clean = (email or "").strip().lower()
    if not email_clean:
        return {"orders": []}
    return {"orders": list_orders_for_email(email_clean)}


@app.get("/orders/{order_id}/pdfs/{pdf_type}", tags=["Payments"])
async def download_order_pdf(
    order_id: str,
    pdf_type: str,
    email: str = "",
    token: str = "",
) -> Response:
    """Stream an IC Project PDF; regenerates from stored analysis if cache was wiped."""
    from ic_project_fulfillment import PDF_TYPES, ensure_pdf_bytes

    oid = (order_id or "").strip()
    ptype = (pdf_type or "").strip().lower()
    if not oid:
        raise HTTPException(status_code=400, detail="order_id is required")
    if ptype not in PDF_TYPES:
        raise HTTPException(status_code=400, detail=f"pdf_type must be one of {list(PDF_TYPES)}")

    data, err = ensure_pdf_bytes(
        oid,
        ptype,
        email=(email or "").strip().lower(),
        token=(token or "").strip(),
    )
    if err == "Order not found":
        raise HTTPException(status_code=404, detail=err)
    if err in ("Email does not match order", "Invalid or missing download token"):
        raise HTTPException(status_code=403, detail=err)
    if err or not data:
        raise HTTPException(status_code=404, detail=err or "PDF not available")

    filename = f"regguard_{ptype}_{oid[:8]}.pdf"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "private, max-age=300",
        },
    )


@app.get("/checkout/confirm", tags=["Payments"])
async def confirm_checkout(session_id: str = "") -> Dict[str, Any]:
    """
    Confirm a Stripe Checkout session after redirect and record the order.
    Idempotent — safe to call from the success page.
    """
    from order_service import confirm_stripe_session

    sid = (session_id or "").strip()
    if not sid:
        raise HTTPException(status_code=400, detail="session_id is required")
    try:
        return await confirm_stripe_session(sid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Checkout confirm failed")
        raise HTTPException(status_code=500, detail="Failed to confirm checkout session") from e


@app.post("/auth/create-checkout-session")
async def create_checkout_session_endpoint(request: SignupRequest) -> CheckoutSessionResponse:
    """
    Create a Stripe Checkout Session for the 14-day free trial.
    
    Accepts email, password, and company_name. Returns a checkout URL
    to redirect the user to Stripe.
    """
    if not stripe_configured():
        raise HTTPException(
            status_code=503,
            detail="Payment processing is not configured. Contact support.",
        )
    
    try:
        result = await create_checkout_session(
            email=request.email,
            password=request.password,
            company_name=request.company_name,
        )
        return CheckoutSessionResponse(
            checkout_url=result["checkout_url"],
            session_id=result["session_id"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Checkout session creation failed")
        raise HTTPException(
            status_code=500,
            detail="Failed to create checkout session. Please try again.",
        ) from e


@app.post("/auth/webhook/stripe")
async def stripe_webhook(request: Request) -> Dict[str, str]:
    """
    Handle Stripe webhook events, specifically 'checkout.session.completed'.
    
    On successful event:
    1. Verify signature
    2. Retrieve session metadata
    3. Create Supabase user + profile
    4. Return 200 OK
    """
    # Get raw body for signature verification
    body = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    
    # Verify webhook signature
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if webhook_secret and sig_header:
        try:
            # Parse signature header: t=timestamp,v1=signature
            sig_parts = {}
            for part in sig_header.split(','):
                if '=' in part:
                    key, value = part.split('=', 1)
                    sig_parts[key] = value
            
            if 't' in sig_parts and 'v1' in sig_parts:
                timestamp = sig_parts['t']
                signature = sig_parts['v1']
                signed_content = f"{timestamp}.{body.decode('utf-8')}"
                
                expected_signature = hmac.new(
                    webhook_secret.encode('utf-8'),
                    signed_content.encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
                
                if not hmac.compare_digest(signature, expected_signature):
                    logger.error("❌ Webhook signature mismatch")
                    raise HTTPException(status_code=401, detail="Invalid signature")
                
                logger.info("✅ Webhook signature verified")
        except Exception as e:
            logger.error(f"❌ Webhook verification error: {e}")
            raise HTTPException(status_code=401, detail="Webhook verification failed")
    else:
        logger.warning("⚠️  No webhook secret or signature header - skipping verification")
    
    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    # Handle checkout.session.completed event
    if event.get("type") == "checkout.session.completed":
        session_obj = event.get("data", {}).get("object", {}) or {}
        session_id = session_obj.get("id")
        if not session_id:
            raise HTTPException(status_code=400, detail="No session ID in event")

        metadata = session_obj.get("metadata") or {}
        tier = (metadata.get("tier") or "").strip()

        # Tier checkout (Contractor Pro / IC Project / etc.) — persist order
        if tier:
            try:
                from order_service import fulfill_checkout_session

                order = await fulfill_checkout_session(session_obj)
                logger.info(
                    "Checkout completed for tier=%s email=%s order=%s",
                    tier,
                    order.get("email"),
                    order.get("order_id"),
                )
                return {
                    "status": "success",
                    "tier": tier,
                    "order_id": order.get("order_id"),
                    "email": order.get("email") or "",
                }
            except Exception as e:
                logger.exception("Tier order fulfillment failed")
                raise HTTPException(status_code=500, detail="Webhook processing failed") from e

        # Legacy signup checkout (email + company_name metadata)
        try:
            result = await handle_checkout_session_completed(session_id)
            logger.info(f"Checkout completed for {result['email']}")
            return {"status": "success", "user_id": result["user_id"]}
        except ValueError as e:
            logger.error(f"Checkout handling failed: {e}")
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            logger.exception("Stripe webhook handler failed")
            raise HTTPException(status_code=500, detail="Webhook processing failed") from e
    
    # Acknowledge other event types
    return {"status": "acknowledged"}


# ========== Free Trial Endpoint ==========

@app.get("/debug/env")
async def debug_env() -> Dict[str, Any]:
    """Show environment variables (sanitized)"""
    return {
        "SUPABASE_URL": os.getenv("SUPABASE_URL", "NOT SET"),
        "SUPABASE_KEY_PREFIX": os.getenv("SUPABASE_KEY", "NOT SET")[:20] + "...",
        "RESEND_API_KEY_SET": bool(os.getenv("RESEND_API_KEY")),
    }

@app.get("/debug/dns")
async def debug_dns() -> Dict[str, Any]:
    """Test DNS resolution from Render"""
    import socket
    try:
        hostname = "cuksjdvlydzxiqnjdaw.supabase.co"
        ip = socket.gethostbyname(hostname)
        return {"hostname": hostname, "ip": ip, "resolved": True}
    except socket.gaierror as e:
        return {"hostname": hostname, "error": str(e), "resolved": False}
    except Exception as e:
        return {"error": str(e), "resolved": False}

@app.get("/debug/test-supabase")
async def test_supabase() -> Dict[str, Any]:
    """Test Supabase connection and email service"""
    import httpx
    try:
        from email_service import get_email_service
        
        # Test Supabase REST API connection
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        supabase_ok = False
        supabase_error = None
        if url and key:
            try:
                logger.info(f"🔍 Supabase URL: {url}")
                logger.info(f"🔍 Supabase Key: {key[:20]}...")
                # Try a simple query first
                supabase_api_url = f"{url}/rest/v1/free_trials?limit=1"
                headers = {"apikey": key}
                with httpx.Client() as client:
                    response = client.get(supabase_api_url, headers=headers, timeout=5.0)
                    supabase_ok = response.status_code in [200, 206]
                    if not supabase_ok:
                        supabase_error = f"GET failed: {response.status_code}"
                    else:
                        # Now try an insert
                        from datetime import datetime, timezone
                        insert_url = f"{url}/rest/v1/free_trials"
                        insert_headers = {"apikey": key, "Content-Type": "application/json", "Prefer": "return=representation"}
                        insert_payload = {
                            "email": "test@debug.com",
                            "address": "Test Address",
                            "project_type": "data-center",
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "memo_sent": False,
                            "converted_to_paid": False,
                            "paid_order_id": None,
                        }
                        insert_response = client.post(insert_url, json=insert_payload, headers=insert_headers, timeout=5.0)
                        if insert_response.status_code not in [200, 201]:
                            supabase_error = f"INSERT failed: {insert_response.status_code} - {insert_response.text[:200]}"
                            supabase_ok = False
            except Exception as e:
                supabase_ok = False
                supabase_error = str(e)
        
        email_service = get_email_service()
        
        return {
            "supabase_connected": supabase_ok,
            "supabase_url_set": bool(url),
            "supabase_key_set": bool(key),
            "supabase_error": supabase_error,
            "email_service_available": email_service is not None,
            "email_service_type": type(email_service).__name__ if email_service else None,
        }
    except Exception as e:
        return {
            "error": str(e),
            "supabase_connected": False,
            "email_service_available": False,
        }

@app.get("/entitlement", tags=["Payments"])
async def get_entitlement(email: str = "") -> Dict[str, Any]:
    """Return whether an email has paid access (Contractor Pro / IC deep research)."""
    from entitlement import access_summary

    return access_summary(email)


@app.post("/free-trial")
async def free_trial(request_body: FreeTrialRequest) -> Dict[str, Any]:
    """
    Free trial: create trial record, return IMMEDIATE analysis for in-app modal,
    and queue email in background. Never blocks the UI on email/DB failure.
    Always returns analysis_data (instant fallback if deep screen fails/times out).

    Free FinOps: city pack + optional 1 allowlisted SERP confirm (no markdown rescrape,
    no Option A 6x env searches, no Universal Scout).
    Paid emails (Contractor Pro / IC) run paid_local_confirm first; Universal Scout only
    when PAID_UNIVERSAL_SCOUT=1 or generate_ic_report (force_scout).
    """
    from free_trial_handler import handle_free_trial
    from free_pack_confirm import run_free_pack_confirm
    from instant_analysis import build_instant_fallback_analysis
    from jurisdiction import geocode_profile_from_address
    from entitlement import has_paid_access

    trial_id = ""
    status = "success"
    message = "Analysis ready — results are displayed in the app."
    paid = has_paid_access(getattr(request_body, "email", None))
    research_depth = "pro" if paid else "free"

    # Free monthly scan cap (paid bypasses)
    free_quota: Optional[Dict[str, Any]] = None
    if not paid:
        from free_scan_quota import consume_free_scan, get_free_scan_usage

        allowed, free_quota = consume_free_scan(getattr(request_body, "email", None) or "")
        if not allowed:
            usage = free_quota or get_free_scan_usage(getattr(request_body, "email", None) or "")
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Free scan limit reached ({usage.get('used')}/{usage.get('limit')} "
                    f"this month). Upgrade to Partner ($79/mo) or Contractor Pro ($149/mo) "
                    f"for deeper Universal Scout — or wait until next month."
                ),
            )

    # Step 1: Best-effort trial record + background email (never block results)
    try:
        response = await handle_free_trial(request_body)
        trial_id = response.trial_id or ""
        if response.status == "error" and not trial_id:
            logger.warning(f"Trial record issue (non-blocking): {response.message}")
            # Keep success path for UI — email record failure must not stop results
            status = "success"
            message = "Analysis ready — results are displayed in the app."
        else:
            message = response.message or message
            status = "success"
    except Exception as trial_err:
        logger.error(f"handle_free_trial failed (continuing with analysis): {trial_err}")

    # Step 2: Always produce analysis_data for the in-app modal
    analysis: Optional[Dict[str, Any]] = None
    try:
        profile = geocode_profile_from_address(request_body.address)

        def _clean_loc(val: Optional[str]) -> str:
            v = (val or "").strip()
            if not v or v.lower() in ("unknown", "n/a", "na", "us", "usa", "united states"):
                return ""
            return v

        req_city = _clean_loc(getattr(request_body, "city", None))
        req_state = _clean_loc(getattr(request_body, "state", None))
        req_zip = "".join(c for c in str(getattr(request_body, "zip", None) or "") if c.isdigit())[:5]
        geo_city = _clean_loc(getattr(profile, "city", None) if profile else None)
        geo_state = _clean_loc(getattr(profile, "state_short", None) if profile else None)
        geo_zip = "".join(
            c for c in str(getattr(profile, "zip5", None) if profile else "") if c.isdigit()
        )[:5]
        city = req_city or geo_city
        state = req_state or geo_state
        zip_code = req_zip or geo_zip
        lat = float(getattr(profile, "latitude", 0.0) or 0.0) if profile else 0.0
        lng = float(getattr(profile, "longitude", 0.0) or 0.0) if profile else 0.0
        try:
            from geocode import is_null_island

            if is_null_island(lat, lng):
                lat, lng = 0.0, 0.0
        except Exception:
            pass
        # Prefer ZIP catalog city for paid AHJ resolve when typed city conflicts
        city_for_ahj = city
        try:
            from ahj_catalog import ahj_identity_conflict

            _conflict = ahj_identity_conflict(city, state, zip_code)
            if _conflict and _conflict.get("resolved_city"):
                city_for_ahj = str(_conflict["resolved_city"])
        except Exception:
            pass

        if paid:
            from pro_deep_analysis import run_pro_deep_analysis

            # IC Project opt-in → force Universal Scout (premortem F2/F8)
            force_scout = bool(getattr(request_body, "generate_ic_report", False))
            logger.info(
                "Paid entitlement — local confirm first (force_scout=%s)",
                force_scout,
            )
            # IC force_scout can exceed 120s; give more headroom (premortem F4)
            paid_timeout = 150.0 if force_scout else 120.0
            analysis = await asyncio.wait_for(
                run_pro_deep_analysis(
                    address=request_body.address,
                    city=city_for_ahj,
                    state=state,
                    zip_code=zip_code,
                    latitude=lat,
                    longitude=lng,
                    project_type=request_body.project_type,
                    email=getattr(request_body, "email", None) or "",
                    force_scout=force_scout,
                ),
                timeout=paid_timeout,
            )
            message = "Contractor Pro — paid local confirm ready."
            if (analysis or {}).get("finops_mode") == "paid_local_confirm":
                pl = (analysis or {}).get("paid_local") or {}
                if pl.get("status") == "capped":
                    message = str(
                        pl.get("user_message")
                        or "Contractor Pro — daily scrape cap reached; federal/state + pack/cache only."
                    )
                elif pl.get("cache_hit"):
                    message = "Contractor Pro — paid local confirm (cached AHJ scrape)."
                elif isinstance(pl.get("pages_scraped"), int):
                    message = (
                        f"Contractor Pro — paid local confirm "
                        f"({pl.get('pages_scraped', 0)}/{pl.get('pages_cap', 8)} pages)."
                    )
            research_depth = analysis.get("research_depth") or "pro"
        else:
            # Free FinOps: pack + cheap confirm; allow enough time for confirm deadline
            free_timeout = float(os.getenv("FREE_TRIAL_ANALYSIS_TIMEOUT_SEC") or "14")
            logger.info(
                "Free FinOps — pack + cheap confirm (timeout=%ss) city=%s state=%s zip=%s",
                max(8.0, free_timeout),
                city,
                state,
                zip_code,
            )
            analysis = await asyncio.wait_for(
                run_free_pack_confirm(
                    address=request_body.address,
                    city=city_for_ahj,
                    state=state,
                    zip_code=zip_code,
                    latitude=lat,
                    longitude=lng,
                    project_type=request_body.project_type or "general",
                ),
                timeout=max(8.0, free_timeout),
            )
            message = (
                "Free Bid Risk preview ready — city pack"
                + (
                    " + cheap confirm."
                    if (analysis or {}).get("free_confirm", {}).get("cheap_confirm") == "ok"
                    else (
                        " + allowlisted confirm."
                        if (analysis or {}).get("free_confirm", {}).get("search_hits")
                        else "."
                    )
                )
                + " Upgrade for full Universal Scout."
            )
        status = "success"
    except asyncio.TimeoutError:
        logger.warning("Deep analysis timed out — using instant fallback")
        analysis = None
    except Exception as analysis_error:
        logger.error(f"Deep analysis failed, using instant fallback: {analysis_error}")
        logger.error(traceback.format_exc())

    if not analysis:
        zip_hint = getattr(request_body, "zip", None) or ""
        analysis = build_instant_fallback_analysis(
            address=request_body.address,
            project_type=request_body.project_type,
            zip_code=zip_hint if isinstance(zip_hint, str) else "",
            city=getattr(request_body, "city", None),
            state=getattr(request_body, "state", None),
        )
        message = "Instant preview ready in the app. Deeper research continues in the background."
        status = "success"
        if paid:
            analysis["research_depth"] = "pro_partial"

    # Absolute guarantee: never return without analysis_data
    if not analysis or not isinstance(analysis, dict):
        analysis = build_instant_fallback_analysis(
            address=request_body.address,
            project_type=request_body.project_type,
            zip_code=getattr(request_body, "zip", None) or "",
        )

    # Honesty safety net: free-trial never returns confident stub risk scores
    from honesty import apply_honesty_layer
    from research_store import save_research

    if not (analysis.get("honesty") or {}).get("risk_verified"):
        analysis = apply_honesty_layer(
            analysis,
            source=analysis.get("honesty", {}).get("source") or ("option_a" if analysis.get("preview") else "preview"),
            risk_verified=False,
            cost_verified=bool((analysis.get("honesty") or {}).get("cost_verified")),
            timeline_verified=bool((analysis.get("honesty") or {}).get("timeline_verified")),
        )

    # Persist so shareable /r/{id} works even if the client never calls /research/persist
    research_id = trial_id or analysis.get("research_id") or analysis.get("timestamp", "preview")
    try:
        meta = save_research(analysis, research_id=str(research_id))
        analysis["research_id"] = meta["research_id"]
        analysis["share_url"] = meta["share_url"]
        research_id = meta["research_id"]
    except Exception as persist_err:
        logger.warning(f"Free-trial persist failed (non-blocking): {persist_err}")

    # Bid-time arbitrage cards (fees, AHJ, gotchas, docs, contingency)
    try:
        from arbitrage_enrichment import enrich_analysis_with_arbitrage

        if isinstance(analysis, dict):
            # Preserve typed-city vs ZIP catalog conflict even when resolve used catalog city
            try:
                from ahj_catalog import ahj_identity_conflict

                typed = (getattr(request_body, "city", None) or "").strip()
                pi = analysis.get("project_info") or {}
                conflict = ahj_identity_conflict(
                    typed or pi.get("city"),
                    getattr(request_body, "state", None) or pi.get("state"),
                    getattr(request_body, "zip", None) or pi.get("zip"),
                )
                if conflict:
                    analysis["ahj_identity"] = conflict
            except Exception:
                pass
            analysis = enrich_analysis_with_arbitrage(analysis)
    except Exception as arb_err:
        logger.warning("Arbitrage enrichment failed (non-blocking): %s", arb_err)

    # Auto-save Saved Job for weekly habit (non-blocking)
    job_id = None
    try:
        from jobs_store import upsert_job

        project = analysis.get("project_info") or {}
        summary = analysis.get("summary") or {}
        email = getattr(request_body, "email", None) or ""
        if email and (project.get("address") or request_body.address):
            job = upsert_job(
                owner_email=str(email),
                address=str(project.get("address") or request_body.address),
                city=str(project.get("city") or ""),
                state=str(project.get("state") or ""),
                zip_code=str(project.get("zip") or getattr(request_body, "zip", "") or ""),
                project_type=str(project.get("type") or request_body.project_type or "general"),
                last_research_id=str(research_id),
                share_url=analysis.get("share_url"),
                summary_snapshot={
                    "estimated_timeline": summary.get("estimated_timeline"),
                    "estimated_total_cost": summary.get("estimated_total_cost"),
                    "risk_level": (analysis.get("environmental_screening") or {}).get("risk_level"),
                    "preview": bool(analysis.get("preview")),
                    "punch_count": summary.get("total_punch_list_items"),
                    "arbitrage_snapshot": (analysis.get("arbitrage_snapshot") if analysis else None) or {},
                },
            )
            job_id = job.get("id")
            analysis["job_id"] = job_id
    except Exception as job_err:
        logger.warning(f"Free-trial auto-save job failed (non-blocking): {job_err}")

    # IC Project: only after deep research + explicit generate_ic_report opt-in
    ic_pdfs_ready = False
    ic_pending = False
    if paid and isinstance(analysis, dict):
        try:
            from ic_project_fulfillment import fulfill_ic_project_artifacts, find_open_ic_order

            email_for_ic = (getattr(request_body, "email", None) or "").strip().lower()
            open_ic = find_open_ic_order(email_for_ic) if email_for_ic else None
            if open_ic:
                want_ic = bool(getattr(request_body, "generate_ic_report", False))
                depth = str(analysis.get("research_depth") or research_depth or "")
                is_preview = bool(analysis.get("preview"))
                deep_ok = depth == "pro" and not is_preview
                if want_ic and analysis:
                    from ic_project_fulfillment import pdfs_are_ready as _pdfs_ready

                    already = _pdfs_ready(open_ic.get("pdfs"))
                    tier_ic = str(open_ic.get("tier") or "").lower()
                    # ic_annual (and replace on ic_project) may regenerate for a new address
                    force = already and tier_ic in (
                        "ic_annual",
                        "ic_project",
                        "ic_consultant",
                    )
                    idem = (getattr(request_body, "ic_idempotency_key", None) or "").strip() or None
                    fulfilled = await fulfill_ic_project_artifacts(
                        email_for_ic,
                        analysis,
                        force=force,
                        idempotency_key=idem,
                    )
                    ic_pdfs_ready = bool(fulfilled and fulfilled.get("pdfs"))
                    if ic_pdfs_ready:
                        message = (
                            "IC Project Report PDFs ready — download Research Memo, "
                            "Punch List, and Permit Package from My Orders."
                        )
                        if not deep_ok:
                            message += (
                                " (Generated from best-available research — retry for a fuller deep scout.)"
                            )
                    else:
                        ic_pending = True
                        message = (
                            "Deep research did not fully complete — IC PDFs were not generated yet. "
                            "Retry the site lookup to produce your Project Report package."
                        )
                else:
                    ic_pending = True
                    # Lookup ran without consuming the one-shot IC slot
                    if "IC Project" not in (message or ""):
                        message = (
                            (message or "Analysis ready.")
                            + " IC Project PDFs were not generated (confirm Generate IC Report on the form)."
                        )
        except Exception as ic_err:
            logger.warning("IC Project PDF fulfillment failed (non-blocking): %s", ic_err)

    # Depth ladder upgrade offer (Free → Pro light → IC full)
    if isinstance(analysis, dict):
        try:
            from depth_ladder import (
                DEPTH_FREE,
                DEPTH_IC_FULL,
                DEPTH_PRO_LIGHT,
                DEPTH_PRO_LOCAL,
                DEPTH_PRO_PARTIAL,
                infer_depth_tier,
                stamp_upgrade_offer,
            )

            if ic_pdfs_ready or (
                paid and bool(getattr(request_body, "generate_ic_report", False))
                and str(analysis.get("scout_mode") or "") == "full"
            ):
                stamp_upgrade_offer(analysis, depth_tier=DEPTH_IC_FULL, ic_pending=ic_pending)
            elif not analysis.get("upgrade_offer"):
                tier = infer_depth_tier(
                    analysis,
                    paid=paid,
                    force_scout=bool(getattr(request_body, "generate_ic_report", False)),
                    scout_mode=str(analysis.get("scout_mode") or ""),
                )
                if not paid:
                    tier = DEPTH_FREE
                stamp_upgrade_offer(analysis, depth_tier=tier, ic_pending=ic_pending)
            elif ic_pending:
                stamp_upgrade_offer(
                    analysis,
                    depth_tier=str(analysis.get("depth_tier") or DEPTH_PRO_LIGHT),
                    ic_pending=True,
                )
        except Exception as ladder_err:
            logger.warning("Depth ladder stamp failed: %s", ladder_err)

    return {
        "trial_id": trial_id,
        "status": status,
        "message": message,
        "analysis_data": analysis,
        "research_id": research_id,
        "share_url": analysis.get("share_url"),
        "job_id": job_id,
        "research_depth": research_depth,
        "paid": paid,
        "ic_pdfs_ready": ic_pdfs_ready,
        "ic_pending": ic_pending,
        "free_scan_quota": free_quota,
        "depth_tier": (analysis or {}).get("depth_tier") if isinstance(analysis, dict) else None,
        "upgrade_offer": (analysis or {}).get("upgrade_offer") if isinstance(analysis, dict) else None,
    }


# ========== Results Display Endpoint (Option A MVP) ==========

@app.post("/results/display")
async def display_results(analysis_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Option A MVP: Display comprehensive analysis results on frontend
    
    Takes full environmental + punch list analysis and formats for HTML display.
    Used after free trial completion to show results before upgrade CTA.
    
    Args:
        analysis_data: Full analysis dict from Option A screening
        
    Returns:
        HTML formatted results ready for frontend display
    """
    try:
        from option_a_integration import format_analysis_for_html
        
        logger.info(f"📊 Formatting analysis results for display")
        
        html = format_analysis_for_html(analysis_data)
        
        return {
            "status": "success",
            "html": html,
            "analysis_data": analysis_data,  # Also return raw data for frontend state management
        }
    except Exception as e:
        logger.error(f"❌ Failed to format results: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": "Failed to format analysis results",
        }


@app.get("/results/sample")
async def get_sample_report() -> Dict[str, Any]:
    """
    Return a sample/anonymized report showing what the full premium report looks like
    Used as social proof on marketing pages
    """
    try:
        logger.info(f"📋 Returning sample report (cached)")
        
        # Return a static sample report for instant load on marketing pages
        sample_report = {
            "address": "1601 Vontress Street, Plano, Texas",
            "zip_code": "75074",
            "project_type": "data-center",
            "status": "Sample Report - Premium Features",
            "environmental_summary": {
                "floodplain": "Not in FEMA floodplain (verified via FEMA Map)",
                "wetlands": "No jurisdictional wetlands detected within 0.5 miles",
                "contamination": "No Phase I ESA on file; no CERCLIS sites detected",
                "endangered_species": "Northern Long-eared Bat habitat possible - verify with USFWS",
            },
            "permit_requirements": {
                "electric": "City of Plano electrical permit required ($75 fee)",
                "structural": "Structural permit required ($150-300 fee)",
                "environmental": "Phase II ESA recommended for data center projects",
            },
            "contractor_action_plan": """## Contractor Action Plan — AHJ permit & code audit

### Mandatory Gotchas — Plano

- [ ] Verify Site Plan Review with City of Plano Development Services (required for data center)
- [ ] Check utility easements and underground utility locate requirements
- [ ] Northern Long-eared Bat habitat - submit USFWS consultation letter if required

### Permit Costs
- [ ] Electrical permit: $75.00 (base $65.00 + laborer $10.00)
- [ ] Site plan review: $150-200 (estimate)
- [ ] Structural engineering review: $300-500 (estimate)

### Technical Punch List
- [ ] Grounding rods: Two 8-foot rods spaced 20 feet apart (Plano Ord. 250.50)
- [ ] 2/0 AWG copper conductor between grounding rods
- [ ] Underground utility locate completed (Call 811)
- [ ] Verify 3-phase power availability at site

### The Bottom Line
**Estimated Permit Timeline:** 4-6 weeks
**Total Estimated Fees:** $600-800
**Key Risk:** USFWS consultation could extend timeline if bat habitat confirmed""",
            "next_steps": [
                "Contact City of Plano Development Services for Site Plan Review",
                "Engage surveyor to verify utility easements",
                "Submit Phase II ESA if contamination history found",
                "Coordinate with USFWS if Northern Long-eared Bat habitat confirmed",
            ],
            "is_sample": True,
        }
        
        return {
            "status": "success",
            "sample_report": sample_report,
        }
    except Exception as e:
        logger.error(f"❌ Failed to generate sample: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": "Failed to generate sample report",
        }


# ========== Jurisdiction Cache Endpoints ==========

@app.get("/cache/jurisdiction/{zip_code}")
def get_cached_jurisdiction(zip_code: str) -> Dict[str, Any]:
    """
    Look up a cached jurisdiction by ZIP code.
    
    **Multi-tenant benefit:** All users read from the global cache,
    eliminating redundant Firecrawl API calls.
    
    Args:
        zip_code: 5-digit US ZIP code (e.g., "75074")
    
    Returns:
        Cached jurisdiction data or 404 if not found
    """
    result = lookup_cached_jurisdiction(zip_code)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No cached jurisdiction found for ZIP {zip_code}",
        )
    return result


@app.get("/cache/jurisdictions/state/{state}")
def get_jurisdictions_by_state(state: str) -> Dict[str, Any]:
    """
    Get all cached jurisdictions for a given state.
    
    Args:
        state: 2-letter state abbreviation (e.g., "TX")
    
    Returns:
        List of jurisdiction records for that state
    """
    results = get_cached_jurisdictions_by_state(state)
    return {
        "state": state.upper(),
        "count": len(results),
        "jurisdictions": results,
    }


@app.get("/cache/stats")
def get_jurisdiction_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics for monitoring and optimization.
    
    Returns cache size, coverage, and age information.
    """
    return get_cache_stats()


@app.post("/cache/jurisdiction")
async def cache_jurisdiction(
    zip_code: str,
    city: str,
    state: str,
    firecrawl_payload: Dict[str, Any] = None,
) -> Dict[str, str]:
    """
    Store or update a jurisdiction in the cache.
    
    Requires admin or service role authentication.
    
    Args:
        zip_code: 5-digit US ZIP code
        city: City name
        state: 2-letter state abbreviation
        firecrawl_payload: JSONB payload from Firecrawl /search
    
    Returns:
        Success or error message
    """
    success = store_cached_jurisdiction(
        zip_code=zip_code,
        city=city,
        state=state,
        firecrawl_payload=firecrawl_payload or {},
    )
    
    if success:
        return {"status": "success", "message": f"Cached jurisdiction for ZIP {zip_code}"}
    
    raise HTTPException(
        status_code=500,
        detail=f"Failed to cache jurisdiction for ZIP {zip_code}",
    )


@app.get("/permit-draft-calculations")
def permit_draft_calculations(job_description: str = "") -> Dict[str, Any]:
    """
    NEC Article 220 / 310 illustrative snapshot for **200 A upgrade** permit drafts.

    Drives the frontend **Permit Submittal Package** PDF section (load VA, feeder amps, copper size).
    """
    return permit_draft_calculation_response(job_description)


class _PermitPackagePayload(BaseModel):
    """POST body for AHJ-facing permit worksheet PDF from research context."""

    model_config = ConfigDict(populate_by_name=True)

    site_address: str = ""
    scope: str = ""
    fee_summary: str = ""
    trade: str = ""
    zip_code: str = Field(default="", alias="zip")
    city: str = ""
    county: str = ""
    ahj_label: str = ""


_PERMIT_PACKAGE_BUILD_TIMEOUT_SEC = 45.0


def _permit_package_sync_build(body: _PermitPackagePayload) -> bytes:
    return build_permit_package_pdf(
        site_address=body.site_address,
        scope=body.scope,
        fee_summary=body.fee_summary,
        trade=body.trade,
        zip_code=body.zip_code,
        city=body.city,
        county=body.county,
        ahj_label=body.ahj_label,
    )


@app.post("/permit-package")
async def permit_package_pdf(body: _PermitPackagePayload) -> Response:
    """
    Build a municipality-style permit worksheet PDF from research context (address, scope, fee summary text, trade).

    Rendered with **fpdf2** via ``permit_package.build_permit_package_pdf``; **fee line items come from UI/scout-derived**
    ``fee_summary``, not geography hard-coded fallbacks.

    Runs the PDF builder in a thread pool so the async event loop is not blocked (avoids dev-proxy / UI stalls).
    Returns **504** if generation exceeds ``_PERMIT_PACKAGE_BUILD_TIMEOUT_SEC``.
    """
    try:
        pdf_bytes = await asyncio.wait_for(
            run_in_threadpool(_permit_package_sync_build, body),
            timeout=_PERMIT_PACKAGE_BUILD_TIMEOUT_SEC,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "permit_package timed out after %.1fs (site=%s)",
            _PERMIT_PACKAGE_BUILD_TIMEOUT_SEC,
            (body.site_address or "")[:80],
        )
        raise HTTPException(
            status_code=504,
            detail=(
                "Permit package generation timed out. Try again, or shorten the action plan excerpt sent from the UI."
            ),
        ) from None
    except Exception as e:
        logger.exception("permit_package build failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Permit package build failed. Check backend logs.",
        ) from e
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="RegGuard-permit-application-package.pdf"',
        },
    )


@app.get("/finops-cache")
def finops_cache_status() -> Dict[str, Any]:
    """
    Profit / FinOps: whether in-process Firecrawl **search** semantic cache and **markdown** scrape cache are enabled.
    Opt-out via ``REG_GUARD_SEMANTIC_SCOUT_CACHE=0`` and ``REG_GUARD_MARKDOWN_SCRAPER_CACHE=0``.
    """
    from markdown_scraper import markdown_scraper_cache_enabled
    from semantic_scout_cache import scout_cache_ttl_sec, semantic_scout_cache_enabled

    return {
        "semantic_scout_cache_enabled": semantic_scout_cache_enabled(),
        "semantic_scout_cache_ttl_sec": scout_cache_ttl_sec(),
        "markdown_scraper_cache_enabled": markdown_scraper_cache_enabled(),
    }


@app.get("/dashboard-revision")
def dashboard_revision() -> Dict[str, str]:
    """
    Lightweight JSON for dashboard polling. ``version`` is static (env); ``revision`` changes
    when this process restarts or backend sources change on disk.
    """
    app_version = (os.environ.get("REG_GUARD_APP_VERSION") or "1.0.0").strip() or "1.0.0"
    explicit_rev = (os.environ.get("REG_GUARD_REVISION") or "").strip()
    revision = explicit_rev or f"{_BACKEND_BOOT_ID}-{compute_backend_source_fingerprint()}"
    return {
        "version": app_version,
        "revision": revision,
    }


@app.get("/roi-stats")
def roi_stats(
    manual_hours_saved: float = 0,
    failed_inspections_avoided: float = 0,
) -> Dict[str, Any]:
    """
    Unit economics snapshot: ``(manual_hours_saved * $75) + (failed_inspections_avoided * $1200)``.
    """
    mh = float(manual_hours_saved)
    fi = float(failed_inspections_avoided)
    labor = mh * _ROI_MANUAL_HOUR_USD
    inspection = fi * _ROI_FAILED_INSPECTION_USD
    total = labor + inspection
    return {
        "manual_hours_saved": mh,
        "failed_inspections_avoided": fi,
        "dollars_per_manual_hour": _ROI_MANUAL_HOUR_USD,
        "dollars_per_failed_inspection_avoided": _ROI_FAILED_INSPECTION_USD,
        "labor_savings_usd": round(labor, 2),
        "inspection_risk_savings_usd": round(inspection, 2),
        "total_savings_usd": round(total, 2),
        "base_search_value_usd": round(float(base_search_value), 2),
    }


@app.get("/geocode-zip")
def geocode_zip(latitude: float, longitude: float) -> Dict[str, str]:
    """
    Reverse geocode a position to a 5-digit U.S. ZIP (in-memory @lru_cache for repeats).
    """
    try:
        z = us_zip_from_lat_lon(latitude, longitude)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"zip": z}


@app.post("/community-gotchas")
def post_community_gotcha(
    zip_code: str = Form(..., description="5-digit U.S. ZIP for this inspector note"),
    text: str = Form(..., description="Short crowdsourced field tip for contractors in this ZIP"),
) -> Dict[str, Any]:
    """Append one crowdsourced inspector note for a ZIP (Community Scout Moat JSON store)."""
    try:
        note = append_note(zip_code, text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    z = normalize_us_zip(zip_code)
    log_api_usage(
        project_key=z,
        route="community_note_write",
        model=model_for_community_note_context(),
        meta={"action": "append"},
    )
    return {"ok": True, "zip": z, "note": note}


@app.post("/bim/import")
def bim_import(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Ingest a Revit-style JSON export, cross-reference archived Universal Scout, and flag Austin gas/conduit clash zones."""
    try:
        return run_bim_sync_bridge(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# Critical-infrastructure keyword map → Reg Guard Agent vertical + suggested trade chip.
_BIM_KEYWORD_RULES: List[Tuple[str, str, str]] = [
    ("generator", "data_center", "electrician"),
    ("high-voltage", "data_center", "electrician"),
    ("high voltage", "data_center", "electrician"),
    ("switchgear", "data_center", "electrician"),
    ("transformer", "infrastructure", "electrician"),
    ("substation", "infrastructure", "electrician"),
    ("cooling", "data_center", "hvac"),
    ("chiller", "data_center", "hvac"),
    ("crac", "data_center", "hvac"),
    ("hvac", "building", "hvac"),
    ("plumbing", "building", "plumber"),
    ("electrical", "building", "electrician"),
]


@app.post("/v1/bim/extract-metadata")
async def bim_extract_metadata(
    upload_file: UploadFile = File(..., description="Revit (.rvt) or IFC (.ifc) model export"),
) -> Dict[str, Any]:
    """
    Lightweight BIM/IFC metadata probe for the frontend dropzone.

    Reads the uploaded model stream, derives basic geometry metrics (name, size, a simulated
    bounding box), and scans for critical-infrastructure keywords (``generator``, ``cooling``,
    ``high-voltage``, …). Returns a payload in the exact schema the Reg Guard Agent pipeline
    consumes: ``jobDescription``, ``vertical``, ``suggestedTrade``.
    """
    if upload_file is None:
        raise HTTPException(status_code=400, detail="No upload_file provided.")

    filename = (getattr(upload_file, "filename", None) or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Uploaded file is missing a filename.")

    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    if ext not in (".rvt", ".ifc"):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type — upload a Revit .rvt or IFC .ifc model.",
        )

    try:
        raw = await upload_file.read()
    except Exception as e:  # noqa: BLE001 — never bubble a raw read fault to the client
        raise HTTPException(status_code=400, detail=f"Could not read upload stream: {e}") from e
    finally:
        try:
            await upload_file.close()
        except Exception:  # noqa: BLE001
            pass

    size_bytes = len(raw or b"")
    if size_bytes == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")

    # --- Lightweight IFC-style parse (best-effort text decode of the model stream) ---
    text_blob = ""
    try:
        text_blob = (raw[: 2_000_000]).decode("utf-8", errors="ignore").lower()
    except Exception:  # noqa: BLE001
        text_blob = ""

    matched_keywords: List[str] = []
    detected_vertical = "building"
    suggested_trade = "general_contractor"
    for needle, vertical_hint, trade_hint in _BIM_KEYWORD_RULES:
        if needle in text_blob:
            matched_keywords.append(needle)
            # First data_center hit wins the vertical; otherwise keep the strongest non-building.
            if detected_vertical == "building" or vertical_hint == "data_center":
                detected_vertical = vertical_hint
            if suggested_trade == "general_contractor":
                suggested_trade = trade_hint

    # Simulated bounding-box geometry metrics derived deterministically from the byte stream.
    span = max(size_bytes, 1)
    bounding_box = {
        "length_m": round(8.0 + (span % 4096) / 256.0, 2),
        "width_m": round(6.0 + (span % 2048) / 256.0, 2),
        "height_m": round(3.0 + (span % 512) / 256.0, 2),
        "element_estimate": max(1, span // 1024),
    }

    kw_phrase = ", ".join(matched_keywords) if matched_keywords else "no critical-infrastructure tags"
    job_description = (
        f"BIM model import: {filename} ({size_bytes:,} bytes). "
        f"Approx. footprint {bounding_box['length_m']}m x {bounding_box['width_m']}m x "
        f"{bounding_box['height_m']}m, ~{bounding_box['element_estimate']:,} elements. "
        f"Detected scope cues: {kw_phrase}. "
        "Generate the permit/code action plan for this scope."
    )

    return {
        "jobDescription": job_description,
        "vertical": detected_vertical,
        "suggestedTrade": suggested_trade,
        "bim": {
            "fileName": filename,
            "fileSizeBytes": size_bytes,
            "boundingBox": bounding_box,
            "criticalKeywords": matched_keywords,
        },
    }


@app.get("/maintenance/subscriptions")
def maintenance_list() -> Dict[str, Any]:
    """Dashboard: list Maintenance Mode sensor-alert subscriptions for completed projects."""
    return {"subscriptions": list_subscriptions()}


@app.post("/maintenance/subscriptions")
def maintenance_create(
    project_name: str = Form(...),
    zip_code: str = Form(...),
    site_address: str = Form(""),
    sensor_profile: str = Form("thermal_vibration"),
    alert_threshold_note: str = Form(""),
    maintenance_mode_enabled: bool = Form(True),
) -> Dict[str, Any]:
    try:
        return create_subscription(
            project_name=project_name,
            zip_code=zip_code,
            site_address=site_address,
            sensor_profile=sensor_profile,
            alert_threshold_note=alert_threshold_note,
            maintenance_mode_enabled=maintenance_mode_enabled,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.patch("/maintenance/subscriptions/{subscription_id}")
def maintenance_patch(
    subscription_id: str,
    body: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    if "maintenance_mode_enabled" not in body:
        raise HTTPException(status_code=400, detail="maintenance_mode_enabled is required")
    try:
        return set_maintenance_mode(subscription_id, bool(body["maintenance_mode_enabled"]))
    except ValueError as e:
        msg = str(e)
        code = 404 if "Unknown" in msg else 400
        raise HTTPException(status_code=code, detail=msg) from e


@app.get("/reverse-geocode-address")
def reverse_geocode_address(latitude: float, longitude: float) -> Dict[str, str]:
    """
    Server-side reverse geocode (Google Geocoding API, no HTTP Referer) for Locate Me UX.

    On any failure (missing ``GOOGLE_MAPS_API_KEY``, blocked credential, or unresolved location)
    this returns a clean HTTP 400 with a clear message, so the frontend can fall back to its
    manual-entry toast instead of receiving fabricated address data.
    """
    try:
        formatted, zip5, city = google_reverse_geocode_us_latlng(latitude, longitude)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001 — surface as 400, never a 500, so the UI can recover.
        raise HTTPException(
            status_code=400,
            detail="Reverse geocoding is unavailable right now — enter the site address manually.",
        ) from e
    return {"formatted_address": formatted, "zip": zip5, "city": city or ""}


def _normalize_research_image_upload(
    image: Optional[UploadFile],
    raw_bytes: Optional[bytes],
) -> Tuple[Optional[bytes], Tuple[Optional[str], Optional[str]], bool]:
    """
    Treat missing, blank-filename, or zero-byte uploads as no photo so the scout pipeline
    never enters the deferred photo-audit branch without real image bytes.
    """
    if image is None:
        return None, (None, None), False
    filename = (getattr(image, "filename", None) or "").strip()
    if not filename:
        return None, (None, None), False
    data = raw_bytes if raw_bytes is not None else b""
    if not data:
        return None, (None, None), False
    content_type = getattr(image, "content_type", None) or None
    return data, (content_type, filename), True


async def _async_read_research_image(
    image: Optional[UploadFile],
) -> Tuple[Optional[bytes], Tuple[Optional[str], Optional[str]], bool]:
    if image is None or not (getattr(image, "filename", None) or "").strip():
        return None, (None, None), False
    try:
        raw = await image.read()
    except Exception as ex:
        logger.warning("Research image read failed — treating as no upload: %s", ex)
        return None, (None, None), False
    return _normalize_research_image_upload(image, raw)


def _sync_read_research_image(
    image: Optional[UploadFile],
) -> Tuple[Optional[bytes], Tuple[Optional[str], Optional[str]], bool]:
    if image is None or not (getattr(image, "filename", None) or "").strip():
        return None, (None, None), False
    try:
        raw = image.file.read()
    except Exception as ex:
        logger.warning("Research image read failed — treating as no upload: %s", ex)
        return None, (None, None), False
    return _normalize_research_image_upload(image, raw)


def _is_json_form_placeholder(raw: str) -> bool:
    """Detect textarea placeholders like ``{ … }`` / ``{...}`` — not valid BIM payloads."""
    s = (raw or "").strip()
    if not s:
        return True
    lowered = s.lower()
    if lowered in ("{...}", "{ … }", "{…}", "...", "…", "{}", "null", "none"):
        return True
    if "..." in s or "…" in s:
        return True
    if re.match(r"^\{\s*(\.{3}|…)+\s*\}$", s):
        return True
    return False


def _parse_optional_form_json(raw: str) -> Optional[Dict[str, Any]]:
    """
    Safely decode optional multipart JSON text (e.g. ``bim_bridge_json``).
    Returns ``None`` on empty input, placeholders, or any decode failure.
    """
    s = (raw or "").strip()
    if _is_json_form_placeholder(s):
        return None
    try:
        parsed = json.loads(s)
    except (json.JSONDecodeError, TypeError, ValueError) as ex:
        logger.warning("Optional form JSON parse failed — using empty: %s", ex)
        return None
    return parsed if isinstance(parsed, dict) else None


def _sse_data_json_from_frame(frame: str) -> Optional[Dict[str, Any]]:
    for line in (frame or "").splitlines():
        if not line.startswith("data:"):
            continue
        raw = line[5:].strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _coalesce_form_text(*parts: Optional[str]) -> str:
    """First non-empty multipart string (supports snake_case and camelCase duplicates)."""
    for p in parts:
        s = (p or "").strip()
        if s:
            return s
    return ""


def _parse_research_form(
    *,
    zip_code: str,
    client_city: str,
    job_description: str,
    search_limit: int,
    site_address: str,
    bim_bridge_json: str,
    scout_trades: str,
    mission_critical_dc: str,
    scout_vertical: str,
    site_line: str,
) -> Tuple[int, str, Dict[str, Any], bool]:
    try:
        lim = _parse_search_limit(search_limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    jd = (job_description or "").strip()
    jf_gate = detect_fast41_eligibility_from_job_description(jd)
    scout_profile_payload: Dict[str, Any] = {
        "trades": (scout_trades or "").strip(),
        "mission_critical_dc": str(mission_critical_dc or "").strip().lower() in ("1", "true", "yes", "on"),
        "vertical": (scout_vertical or "").strip() or "building",
        "job_fast41_eligible": jf_gate,
    }
    if not site_line:
        raise HTTPException(
            status_code=400,
            detail="Select a U.S. job site address from the address search field.",
        )
    return lim, jd, scout_profile_payload, jf_gate


def _research_static_collect(gen: Iterator[str]) -> Dict[str, Any]:
    complete: Optional[Dict[str, Any]] = None
    scout_steps: Dict[str, Any] = {}
    for frame in gen:
        obj = _sse_data_json_from_frame(frame)
        if not obj:
            continue
        ev = obj.get("event")
        if ev == "error":
            raise HTTPException(status_code=400, detail=str(obj.get("message") or "Research error"))
        if ev == "step" and obj.get("step"):
            scout_steps[str(obj["step"])] = obj.get("data")
        if ev == "complete":
            complete = obj
    if not complete:
        raise HTTPException(
            status_code=500,
            detail="Research static route finished without complete payload.",
        )
    out = dict(complete)
    if scout_steps:
        out["scout_steps"] = scout_steps
    return out


@app.post("/research")
async def research(
    request: Request,
    zip_code: str = Form(
        "",
        description="5-digit ZIP from address selection (cross-check with geocode.py)",
    ),
    zipCode: str = Form(""),
    client_city: str = Form(
        "",
        description="Google Places locality — aligns scout queries when forward-geocode differs slightly",
    ),
    clientCity: str = Form(""),
    job_description: str = Form(""),
    jd: str = Form(""),
    text: str = Form(""),
    jobDescription: str = Form(""),
    search_limit: int = Form(5),
    site_address: str = Form(
        "",
        description="Google Places formatted_address — city/county via geocode.py",
    ),
    siteAddress: str = Form(""),
    bim_bridge_json: str = Form(
        "",
        description="Optional JSON from POST /bim/import (RegGuard BIM bridge) — merged into digest for clash-zone routing",
    ),
    scout_trades: str = Form(
        "",
        description=(
            "Comma-separated trade toggles: general_contractor, electrician, plumber, hvac, zoning_planning, "
            "owner_builder (Universal Scout augment — HVAC/MEP + entitlement cues)"
        ),
    ),
    mission_critical_dc: str = Form(
        "false",
        description="When true, scout adds Tier III/IV redundancy + liquid-cooling containment code cues",
    ),
    scout_vertical: str = Form(
        "building",
        description=(
            "building | infrastructure | data_center — infrastructure/data_center tiers add FAST‑41/water/AIM‑Act/WUE passes; "
            "job descriptions can also unlock the FAST‑41 tier for building vertical when **data center** + **>**100 MW "
            "**or** **>**$500 M cues parse true"
        ),
    ),
    image: Optional[UploadFile] = File(default=None),
):
    """
    Multipart research streamed as **Server-Sent Events** (``text/event-stream``).

    The response body is an **async generator** of many ``data:`` SSE frames
    (``data: <json>\\n\\n``), including incremental ``summary_delta`` chunks, not one final string only.

    Each event's ``data`` field is one JSON object (same schema as the former NDJSON lines).

    Emits immediately to avoid proxy/client JSON timeouts, then runs Universal Scout, then **Gemini**
    Reality Capture photo audit after scout when an image is included (requires API keys).
    Streams word-sized chunks of the Contractor Action Plan.

    Events include: ``open``, ``heartbeat`` (during slow Firecrawl/vision work), ``reasoning``,
    ``vision_delta``,
    ``visual_audit`` (Gemini Reality Capture bounding boxes; requires ``GEMINI_API_KEY`` / ``GOOGLE_API_KEY`` when a photo is sent),
    ``context``, ``jurisdiction`` (when geocoded),
    ``step`` (scout:
    ``step_jurisdiction``, ``step_building_permits``, ``step_building_codes``;
    ``step_residential_zoning`` for **building** vertical (blank-slate setbacks — Municode / .gov / OpenGov);
    **infrastructure**, **data_center**, or parsed **FAST-41 job gate** (**data center** + **>**100 MW **or** **>**$500 M
    cues in ``job_description``) add ``step_federal_fast41``, ``step_data_center_water``,
    ``step_refrigerant_aim_act`` (EPA **AIM Act** / HFC phasedown / SNAP), ``step_water_usage_effectiveness``
    (**WUE** / reclaimed-water overlays); **data_center** alone also adds ``step_dc_state_energy`` and ``step_dc_local_moratorium``),
    ``future_risk_alert``, ``community_inspector_feedback`` (ZIP-indexed crowdsourced inspector notes when present),
    ``summary_delta``, ``complete``.

    Multipart fields **scout_trades** (comma list: general_contractor, electrician, plumber, hvac, zoning_planning, owner_builder),
    **mission_critical_dc**, and
    **scout_vertical** (building | infrastructure | data_center) steer Universal Scout MEP augmentation and FAST-41.

    Job text accepts **job_description**, **jobDescription**, **jd**, or **text**. Address/ZIP accept snake_case or camelCase.
    """
    site_line = _coalesce_form_text(site_address, siteAddress)
    zip_merged = _coalesce_form_text(zip_code, zipCode)
    city_merged = _coalesce_form_text(client_city, clientCity)
    jd_merged = _coalesce_form_text(job_description, jobDescription, jd, text)
    lim, jd_parsed, scout_profile_payload, jf_gate = _parse_research_form(
        zip_code=zip_merged,
        client_city=city_merged,
        job_description=jd_merged,
        search_limit=search_limit,
        site_address=site_line,
        bim_bridge_json=bim_bridge_json,
        scout_trades=scout_trades,
        mission_critical_dc=mission_critical_dc,
        scout_vertical=scout_vertical,
        site_line=site_line,
    )

    image_bytes, image_meta, has_image = await _async_read_research_image(image)
    bim_clash_report = _parse_optional_form_json(bim_bridge_json)

    ctx: Dict[str, Any] = {
        "lim": lim,
        "jd": jd_parsed,
        "site_line": site_line,
        "zip_code": zip_merged,
        "client_city": city_merged,
        "bim_bridge_json": bim_bridge_json,
        "bim_clash_report": bim_clash_report,
        "scout_profile_payload": scout_profile_payload,
        "image_bytes": image_bytes,
        "image_meta": image_meta,
        "has_image": has_image,
        "jf_gate": jf_gate,
        "scout_vertical": scout_vertical,
    }

    return StreamingResponse(
        _iter_research_sse_events(ctx),
        headers=_research_sse_stream_headers(request),
    )


def _iter_research_sse_events(ctx: Dict[str, Any]) -> Iterator[str]:
    lim = int(ctx["lim"])
    jd = str(ctx["jd"])
    site_line = str(ctx["site_line"])
    zip_code = str(ctx.get("zip_code") or "")
    client_city = str(ctx.get("client_city") or "")
    bim_bridge_json = str(ctx.get("bim_bridge_json") or "")
    bim_clash_report = cast(Optional[Dict[str, Any]], ctx.get("bim_clash_report"))
    scout_profile_payload = cast(Dict[str, Any], ctx["scout_profile_payload"])
    image_bytes = cast(Optional[bytes], ctx.get("image_bytes"))
    image_meta = cast(Tuple[Optional[str], Optional[str]], ctx.get("image_meta") or (None, None))
    has_image = bool(ctx.get("has_image")) and bool(image_bytes)
    jf_gate = bool(ctx.get("jf_gate"))
    scout_vertical = str(ctx.get("scout_vertical") or "building")

    def research_sse_sync():
        try:
            yield _safe_sse_data_frame({"event": "open"})
            _log_research_step("open", detail="SSE stream started")

            try:
                profile: JurisdictionProfile = geocode_profile_from_address(site_line)
            except ValueError as e:
                yield _safe_sse_data_frame({"event": "error", "message": str(e)})
                return

            zip_for_scout = profile.zip5
            if (zip_code or "").strip():
                try:
                    client_z = normalize_us_zip(zip_code)
                except ValueError as e:
                    yield _safe_sse_data_frame({"event": "error", "message": str(e)})
                    return
                if client_z != profile.zip5:
                    yield _safe_sse_data_frame(
                        {
                            "event": "warning",
                            "code": "zip_corrected",
                            "message": (
                                f"ZIP {client_z} did not match the selected address ({profile.zip5}); "
                                "using the geocoded ZIP for Universal Scout."
                            ),
                            "client_zip": client_z,
                            "zip_used": profile.zip5,
                        }
                    )
                    _log_research_step(
                        "zip",
                        detail=f"client ZIP {client_z} corrected to geocode {profile.zip5}",
                    )
            scout_jurisdiction = profile.to_scout_dict()
            cc = (client_city or "").strip()
            if cc and str(scout_jurisdiction.get("mode")) == "city":
                gc_city = str(scout_jurisdiction.get("city") or "").strip()
                if not gc_city or gc_city.lower() != cc.lower():
                    scout_jurisdiction = {**scout_jurisdiction, "city": cc}
            scout_site = profile.formatted_address or site_line

            photo_analysis: Optional[str] = None
            visual_audit_payload: Optional[Dict[str, Any]] = None

            if image_bytes and not gemini_configured():
                yield _safe_sse_data_frame(
                    {
                        "event": "error",
                        "message": (
                            "Photo audit requires GEMINI_API_KEY or GOOGLE_API_KEY on the API "
                            "(google-generativeai). Claude image analysis has been removed."
                        ),
                    }
                )
                return

            pending_photo_audit = has_image

            scout_enhanced_query = _build_enhanced_query(jd, None)
            enhanced_query: Optional[str] = scout_enhanced_query if not pending_photo_audit else None

            if not pending_photo_audit:
                yield _safe_sse_data_frame(
                    {
                        "event": "context",
                        "enhanced_query": enhanced_query,
                        "job_description": jd,
                        "photo_analysis": photo_analysis,
                    }
                )
                _log_research_step("context", detail="enhanced query ready for scout")
            
            # ========== CACHE INTERCEPTOR: Try to serve from cached_jurisdictions ==========
            cache_context = None
            use_cached_scout = False
            final_raw: Optional[Dict[str, Any]] = None
            
            if is_cache_enabled() and not image_bytes:
                # Attempt cache lookup (no image analysis; cache is fast path only)
                _log_research_step(
                    "cache",
                    detail=f"Checking cached_jurisdictions for ZIP {zip_for_scout}...",
                )
                cache_context = create_cache_intercept_context(
                    zip_for_scout,
                    scout_jurisdiction.get("city", ""),
                    scout_jurisdiction.get("state", ""),
                )
                
                if cache_context.get("use_cache") and cache_context.get("cached_payload"):
                    use_cached_scout = True
                    final_raw = cache_context["cached_payload"]
                    cache_age = cache_context.get("cache_age_seconds", 0)
                    
                    yield _safe_sse_data_frame(
                        {
                            "event": "reasoning",
                            "phase": "cache",
                            "text": f"✓ Cache hit for ZIP {zip_for_scout} (age: {cache_age}s). "
                                   f"Bypassing Firecrawl — serving cached scout results."
                        }
                    )
                    _log_research_step(
                        "cache",
                        detail=f"Cache hit for ZIP {zip_for_scout} — skipping Firecrawl",
                    )
                    
                    # Emit cached scout steps to client
                    for step_key in ("step_jurisdiction", "step_building_permits", "step_building_codes",
                                     "step_residential_zoning", "step_federal_fast41", "step_data_center_water",
                                     "step_refrigerant_aim_act", "step_water_usage_effectiveness",
                                     "step_dc_state_energy", "step_dc_local_moratorium"):
                        if step_key in final_raw:
                            yield _safe_sse_data_frame(
                                {
                                    "event": "step",
                                    "step": step_key,
                                    "data": final_raw[step_key],
                                }
                            )
            
            # If cache miss or disabled, run full Firecrawl pipeline
            if not use_cached_scout:
                yield _reasoning_sse_frame(
                    "scout",
                    "Scout — Packaging job context for jurisdiction-scoped discovery (gov & code publishers)…",
                )

                if scout_jurisdiction and scout_site:
                    yield _safe_sse_data_frame(
                        {
                            "event": "jurisdiction",
                            "site_address": scout_site,
                            "profile": scout_jurisdiction,
                        }
                    )
                    _log_research_step("jurisdiction", detail="geocoded profile emitted to client")

                ahj_for_scout: Optional[Dict[str, Any]] = None
                if scout_jurisdiction:
                    ahj_for_scout = _ahj_identification_payload(scout_jurisdiction)
                    _log_research_step(
                        "AHJ identification",
                        detail="city/county/state from geocode (before Universal Scout)",
                    )
                    yield _safe_sse_data_frame(
                        {
                            "event": "step",
                            "step": "step_ahj_identification",
                            "data": {
                                "query": "Identify city and county from formatted address (geocode.py → Google Geocoding API)",
                                "results": [],
                                **ahj_for_scout,
                            },
                        }
                    )

                try:
                    _log_research_step(
                        "Universal Scout",
                        detail="Firecrawl /search — multi-tier sequential passes (see backend scraper)",
                    )
                    # Universal Scout: each query line includes ``City, ST`` / county + ``(site:gov OR site:municode.com)`` — see ``scraper.py``.
                    it = iter(
                        iter_universal_scout(
                            zip_for_scout,
                            search_limit=lim,
                            enhanced_context=scout_enhanced_query,
                            site_address=scout_site,
                            jurisdiction=scout_jurisdiction,
                            ahj_identification=ahj_for_scout,
                            scout_profile=scout_profile_payload,
                        )
                    )
                    _seq = _scout_firecrawl_step_sequence(scout_vertical, job_fast41_eligible=jf_gate)
                    _pass_total = len(_seq)
                    _scout_labels: Dict[str, str] = {}
                    for _i, _key in enumerate(_seq, start=1):
                        if _key == "step_jurisdiction":
                            _scout_labels[_key] = f"pass {_i}/{_pass_total} — jurisdiction & AHJ hints (Firecrawl)"
                        elif _key == "step_building_permits":
                            _scout_labels[_key] = f"pass {_i}/{_pass_total} — building permits (Firecrawl)"
                        elif _key == "step_building_codes":
                            _scout_labels[_key] = f"pass {_i}/{_pass_total} — adopted codes (Firecrawl)"
                        elif _key == "step_residential_zoning":
                            _scout_labels[_key] = (
                                f"pass {_i}/{_pass_total} — residential zoning & setbacks — Municode / .gov / OpenGov (Firecrawl)"
                            )
                        elif _key == "step_federal_fast41":
                            _scout_labels[_key] = f"pass {_i}/{_pass_total} — FAST-41 federal permitting (Firecrawl)"
                        elif _key == "step_data_center_water":
                            _scout_labels[_key] = (
                                f"pass {_i}/{_pass_total} — utility-scale cooling water / NPDES / state environmental (Firecrawl)"
                            )
                        elif _key == "step_refrigerant_aim_act":
                            _scout_labels[_key] = (
                                f"pass {_i}/{_pass_total} — AIM Act refrigerant phasedown / EPA SNAP scout (Firecrawl)"
                            )
                        elif _key == "step_water_usage_effectiveness":
                            _scout_labels[_key] = (
                                f"pass {_i}/{_pass_total} — Water Usage Effectiveness (WUE) / reclaimed-water overlays (Firecrawl)"
                            )
                        elif _key == "step_dc_state_energy":
                            _scout_labels[_key] = (
                                f"pass {_i}/{_pass_total} — state energy riders / ratepayer pledges / grid surcharge (Firecrawl)"
                            )
                        elif _key == "step_dc_local_moratorium":
                            _scout_labels[_key] = (
                                f"pass {_i}/{_pass_total} — 2026 data center moratorium / township pause scout (Firecrawl)"
                            )
                    _city_label = str((scout_jurisdiction or {}).get("city") or "").strip() or "local"
                    _scout_reasoning: Dict[str, str] = {
                        "step_jurisdiction": f"Scouting {_city_label} jurisdiction, AHJ hints, and trusted .gov anchors…",
                        "step_building_permits": f"Scouting {_city_label} Building Dept — fee schedules and permit portals…",
                        "step_building_codes": f"Cross-referencing {_city_label} adopted codes and NEC 2023 amendment deltas…",
                        "step_residential_zoning": (
                            f"Residential tier — Municode / codified setbacks and yard lines for {_city_label} "
                            f"(OpenGov portal cues where published)…"
                        ),
                        "step_federal_fast41": (
                            f"Data-center / infra tier — FAST-41 / Permitting Council federal status cues for "
                            f"{_city_label} ({scout_profile_payload.get('vertical') or 'vertical'}) scope…"
                        ),
                        "step_data_center_water": (
                            f"Data-center / infra tier — cross-referencing utility-scale cooling-water / NPDES / "
                            f"state EQ commission signals for {_city_label}…"
                        ),
                        "step_refrigerant_aim_act": (
                            f"MEP scout — AIM Act / HFC phasedown and mechanical refrigerant-compliance cues for {_city_label}…"
                        ),
                        "step_water_usage_effectiveness": (
                            f"MEP scout — AHJ-facing **Water Usage Effectiveness** and reclaimed-water / conservation overlays "
                            f"for {_city_label}…"
                        ),
                        "step_dc_state_energy": (
                            f"Data-center tier — scanning PSC/PUC riders, **ratepayer protection** cues, and interconnect surcharge signals "
                            f"for {_city_label}…"
                        ),
                        "step_dc_local_moratorium": (
                            f"Data-center tier — hunting trusted-domain cues for **2026** township/county **moratorium** or **pause** "
                            f"language affecting hyperscale / AI sites near {_city_label}…"
                        ),
                    }
                    yield _reasoning_sse_frame(
                        "scout",
                        "Scout — Running multi-tier Firecrawl passes (jurisdiction → permits → codes → vertical intelligence)…",
                    )
                    while True:
                        ev: Optional[Dict[str, Any]] = _scout_iter_next(it)
                        if ev is None:
                            break
                        if ev.get("event") == "complete":
                            final_raw = ev["raw"]
                            _log_research_step("Universal Scout", detail="all search passes complete")
                            break
                        if ev.get("event") == "step":
                            key = str(ev.get("step") or "step")
                            _log_research_step(
                                "Universal Scout",
                                detail=_scout_labels.get(key, key),
                            )
                            rtxt = _scout_reasoning.get(key)
                            if rtxt:
                                yield _reasoning_sse_frame("scout", rtxt)
                        yield _safe_sse_data_frame(ev)
                        if ev.get("event") == "step" and str(ev.get("step") or "") in (
                            "step_jurisdiction",
                            "step_building_permits",
                            "step_building_codes",
                            "step_residential_zoning",
                            "step_federal_fast41",
                            "step_data_center_water",
                            "step_refrigerant_aim_act",
                            "step_water_usage_effectiveness",
                            "step_dc_state_energy",
                            "step_dc_local_moratorium",
                        ):
                            time.sleep(0.5)
                    
                    # ========== CACHE WRITE: Store successful Firecrawl result ==========
                    if final_raw and is_cache_enabled() and not image_bytes:
                        _cache_success = cache_firecrawl_result(
                            zip_code=zip_for_scout,
                            city=scout_jurisdiction.get("city", ""),
                            state=scout_jurisdiction.get("state", ""),
                            firecrawl_payload=final_raw,
                        )
                        if _cache_success:
                            yield _safe_sse_data_frame(
                                {
                                    "event": "reasoning",
                                    "phase": "cache",
                                    "text": f"✓ Cached Firecrawl results for ZIP {zip_for_scout} "
                                           f"(instant multi-tenant reuse for next user)."
                                }
                            )
                
                except Exception:
                    logger.exception("Firecrawl / Universal Scout crawl failed")
                    yield _safe_sse_data_frame({"event": "error", "message": _RESEARCH_STALL_FIRECRAWL_MESSAGE})
                    return

            if final_raw is None:
                yield _safe_sse_data_frame(
                    {"event": "error", "message": "Research finished without complete payload."}
                )
                return

            raw = final_raw
            # Dallas Open Data attach when AHJ is City of Dallas
            try:
                jblob_od = raw.get("jurisdiction") if isinstance(raw.get("jurisdiction"), dict) else {}
                city_for_od = str(jblob_od.get("city") or raw.get("city") or "")
                state_for_od = str(jblob_od.get("state") or raw.get("state") or "")
                if city_for_od.strip().lower() == "dallas" and state_for_od.strip().upper() in ("TX", "TEXAS", ""):
                    from dallas_open_data import fetch_dallas_commercial_permits

                    addr_hint = str(raw.get("site_address") or raw.get("address") or "")
                    dallas_od = fetch_dallas_commercial_permits(address_hint=addr_hint)
                    raw["dallas_open_data"] = dallas_od
                    yield _safe_sse_data_frame(
                        {
                            "event": "dallas_open_data",
                            "source": dallas_od.get("source"),
                            "count": dallas_od.get("count"),
                            "socrata_url": dallas_od.get("socrata_url"),
                        }
                    )
            except Exception as od_err:
                logger.warning(f"Dallas Open Data attach skipped: {od_err}")

            source_urls = filter_source_urls(_collect_source_urls(raw))
            try:
                from ahj_catalog import citation_urls, lookup_ahj

                jblob = raw.get("jurisdiction") if isinstance(raw.get("jurisdiction"), dict) else {}
                ahj = lookup_ahj(
                    str(jblob.get("city") or raw.get("city") or ""),
                    str(jblob.get("state") or raw.get("state") or ""),
                    str(zip_for_scout or ""),
                )
                if ahj:
                    for u in citation_urls(ahj):
                        if u not in source_urls:
                            source_urls.append(u)
                od_url = (raw.get("dallas_open_data") or {}).get("socrata_url")
                if od_url and od_url not in source_urls:
                    source_urls.append(od_url)
            except Exception as cite_err:
                logger.warning(f"AHJ citation merge skipped: {cite_err}")
            try:
                save_scout_snapshot(str(raw.get("zip") or zip_for_scout), raw)
            except (ValueError, OSError) as ex:
                logger.warning("Universal Scout archive write skipped: %s", ex)
            future_risk_snapshot = future_risk_alerts_from_raw(raw)
            yield _safe_sse_data_frame({"event": "future_risk_alert", "payload": future_risk_snapshot})

            _community_notes = list_notes_for_zip(zip_for_scout)
            if _community_notes:
                yield _safe_sse_data_frame(
                    {
                        "event": "community_inspector_feedback",
                        "zip": zip_for_scout,
                        "notes": _community_notes,
                    }
                )
            log_api_usage(
                project_key=zip_for_scout,
                route="community_note_retrieval",
                model=model_for_community_note_context(),
                meta={"note_count": len(_community_notes)},
            )
            log_api_usage(
                project_key=zip_for_scout,
                route="permit_fee_scout",
                model=model_for_permit_scout_text(),
                meta={"phase": "universal_scout_complete", "has_image": bool(image_bytes)},
            )

            if image_bytes:
                content_type, filename = image_meta
                scout_text = scout_summary_for_reality_capture(raw)
                city_j = str((scout_jurisdiction or {}).get("city") or "")
                state_j = str((scout_jurisdiction or {}).get("state") or "")
                visual_holder: List[Any] = []
                q_vis: Queue = Queue()
                thread_vis = threading.Thread(
                    target=_vision_gemini_queue_producer,
                    args=(
                        q_vis,
                        image_bytes,
                        content_type,
                        filename,
                        scout_text,
                        city_j,
                        state_j,
                        zip_for_scout,
                        visual_holder,
                    ),
                    daemon=True,
                )
                _log_research_step(
                    "vision",
                    detail="Gemini Reality Capture Audit — multimodal vs scout hits",
                )
                yield _reasoning_sse_frame(
                    "audit",
                    "Reality Capture — Auditing site photo against scout hits (Gemini multimodal)…",
                )
                thread_vis.start()
                raw_vis_parts: List[str] = []
                while True:
                    kind_v: str
                    val_v: Any
                    kind_v, val_v = q_vis.get()
                    if kind_v == "delta":
                        raw_vis_parts.append(cast(str, val_v))
                        yield _safe_sse_data_frame({"event": "vision_delta", "text": cast(str, val_v)})
                    elif kind_v == "done":
                        break
                    else:
                        err_v = cast(Exception, val_v)
                        yield _safe_sse_data_frame({"event": "error", "message": str(err_v)})
                        return
                photo_analysis = normalize_vision_text("".join(raw_vis_parts))
                visual_audit_payload = visual_holder[0] if visual_holder else None
                _log_research_step("vision", detail="Gemini Reality Capture Audit — done")
                yield _safe_sse_data_frame(
                    {"event": "visual_audit", "payload": sanitize_visual_audit_for_client(visual_audit_payload)}
                )
                enhanced_query = _build_enhanced_query(jd, photo_analysis)
                yield _safe_sse_data_frame(
                    {
                        "event": "context",
                        "enhanced_query": enhanced_query,
                        "job_description": jd,
                        "photo_analysis": photo_analysis,
                    }
                )
                _log_research_step("context", detail="enhanced query + Reality Capture ready for digest")

            if enhanced_query is None:
                enhanced_query = scout_enhanced_query or _build_enhanced_query(jd, photo_analysis)
            if not (enhanced_query or "").strip():
                yield _safe_sse_data_frame(
                    {"event": "error", "message": "Research digest missing enhanced query context."}
                )
                return

            _log_research_step("digest", detail="building structured research digest")
            yield _reasoning_sse_frame(
                "scout",
                "Scout complete — normalizing URLs and building a structured research digest…",
            )
            bim_digest: Optional[Dict[str, Any]] = bim_clash_report
            if bim_digest is None and (bim_bridge_json or "").strip():
                bim_digest = _parse_optional_form_json(bim_bridge_json)
            digest = build_research_digest(
                raw,
                source_urls,
                enhanced_query,
                future_risk=future_risk_snapshot,
                community_scout_notes=_community_notes,
                bim_clash_report=bim_digest,
                job_description=jd,
            )

            summary: str
            if (os.getenv("ANTHROPIC_API_KEY") or "").strip():
                yield _reasoning_sse_frame(
                    "audit",
                    "Audit — Synthesizing contractor action plan from the digest (fees, technical gates, inspections)…",
                )
                q_plan: Queue = Queue()
                thread_plan = threading.Thread(
                    target=_action_plan_queue_producer,
                    args=(q_plan, digest),
                    daemon=True,
                )
                _log_research_step("action plan", detail="Claude — Contractor Action Plan streaming")
                thread_plan.start()
                raw_parts: List[str] = []
                while True:
                    kind: str
                    val: Any
                    kind, val = q_plan.get()
                    if kind == "delta":
                        raw_parts.append(cast(str, val))
                        yield _safe_sse_data_frame({"event": "summary_delta", "text": cast(str, val)})
                    elif kind == "done":
                        summary = "".join(raw_parts)
                        break
                    else:
                        err = cast(Exception, val)
                        yield _reasoning_sse_frame(
                            "audit",
                            "Audit — Recovering with structured fallback memo after synthesis error…",
                        )
                        stub = _research_action_plan_fallback_markdown(
                            raw,
                            source_urls,
                            enhanced_query,
                            job_description=jd,
                            community_gotchas=_community_notes,
                            bim_clash_report=bim_digest,
                        )
                        logger.warning("Contractor Action Plan Claude error — using fallback: %s", err)
                        for chunk in _iter_summary_word_chunks(stub):
                            yield _safe_sse_data_frame({"event": "summary_delta", "text": chunk})
                        summary = stub
                        _log_research_step("action plan", detail="fallback memo (Claude error)")
                        break
            else:
                yield _reasoning_sse_frame(
                    "audit",
                    "Audit — Building structured fallback action memo (no live synthesis key)…",
                )
                _log_research_step("action plan", detail="structured fallback memo — no ANTHROPIC_API_KEY")
                summary = _research_action_plan_fallback_markdown(
                    raw,
                    source_urls,
                    enhanced_query,
                    job_description=jd,
                    community_gotchas=_community_notes,
                    bim_clash_report=bim_digest,
                )
                for chunk in _iter_summary_word_chunks(summary):
                    yield _safe_sse_data_frame({"event": "summary_delta", "text": chunk})

            fr_md = format_future_risk_markdown(future_risk_snapshot)
            if fr_md:
                summary = fr_md + "\n\n" + summary

            ju_complete = scout_jurisdiction or {}
            ahj_bl = str(ju_complete.get("label") or ju_complete.get("city") or "").strip()
            summary = _ensure_bottom_line_section(summary, ahj_hint=ahj_bl)
            _dc_intel_run = compute_data_center_intel_snapshot(raw, jd, enhanced_query or "")
            summary = inject_bottom_line_permit_conflict(
                summary,
                alert_on=bool(_dc_intel_run.get("data_center_permit_conflict_alert")),
                rationale=str(_dc_intel_run.get("data_center_permit_conflict_rationale") or ""),
            )
            summary = inject_bottom_line_moratorium_state_red_alert(
                summary,
                active=bool(_dc_intel_run.get("moratorium_state_bottom_line_red_alert")),
            )

            liability_est = _estimated_liability_avoided_usd(summary)
            value_metrics = {
                "research_value_usd": round(float(base_search_value), 2),
                "estimated_liability_avoided_usd": liability_est,
            }

            _moratorium_sse_alert = {
                "active": bool(_dc_intel_run.get("moratorium_state_bottom_line_red_alert")),
                "text": MORATORIUM_BOTTOM_RED_WARNING_TEXT,
            }

            _log_research_step("complete", detail="streaming final payload to client")
            yield _safe_sse_data_frame(
                {
                    "event": "complete",
                    "zip": raw["zip"],
                    "site_address": raw.get("site_address"),
                    "city": ju_complete.get("city") or None,
                    "county": ju_complete.get("county") or None,
                    "ahj_label": ju_complete.get("label") or None,
                    "jurisdiction": raw.get("jurisdiction"),
                    "summary": summary,
                    "source_urls": source_urls,
                    "enhanced_query": enhanced_query,
                    "job_description": jd,
                    "photo_analysis": photo_analysis,
                    "visual_audit": sanitize_visual_audit_for_client(visual_audit_payload),
                    "future_risk_alert": future_risk_snapshot,
                    "community_inspector_feedback": _community_notes,
                    "value_metrics": value_metrics,
                    "moratorium_state_alert": _moratorium_sse_alert,
                }
            )
        except Exception as e:
            logger.exception("Research SSE pipeline failed")
            yield _safe_sse_data_frame(
                {
                    "event": "error",
                    "message": str(e) or "Research pipeline failed unexpectedly.",
                }
            )
        finally:
            clear_scout_run_caches()

    yield from research_sse_sync()


@app.post("/research/static")
def research_static(
    request: Request,
    zip_code: str = Form(""),
    zipCode: str = Form(""),
    client_city: str = Form(""),
    clientCity: str = Form(""),
    job_description: str = Form(""),
    jd: str = Form(""),
    text: str = Form(""),
    jobDescription: str = Form(""),
    search_limit: int = Form(5),
    site_address: str = Form(""),
    siteAddress: str = Form(""),
    bim_bridge_json: str = Form(""),
    scout_trades: str = Form(""),
    mission_critical_dc: str = Form("false"),
    scout_vertical: str = Form("building"),
    image: Optional[UploadFile] = File(default=None),
):
    """
    Non-streaming research fallback — returns the finalized ``complete`` JSON envelope
    (summary, value_metrics, jurisdiction fields, optional ``scout_steps`` map).
    """
    site_line = _coalesce_form_text(site_address, siteAddress)
    zip_merged = _coalesce_form_text(zip_code, zipCode)
    city_merged = _coalesce_form_text(client_city, clientCity)
    jd_merged = _coalesce_form_text(job_description, jobDescription, jd, text)
    lim, jd_parsed, scout_profile_payload, jf_gate = _parse_research_form(
        zip_code=zip_merged,
        client_city=city_merged,
        job_description=jd_merged,
        search_limit=search_limit,
        site_address=site_line,
        bim_bridge_json=bim_bridge_json,
        scout_trades=scout_trades,
        mission_critical_dc=mission_critical_dc,
        scout_vertical=scout_vertical,
        site_line=site_line,
    )
    image_bytes, image_meta, has_image = _sync_read_research_image(image)
    bim_clash_report = _parse_optional_form_json(bim_bridge_json)
    ctx: Dict[str, Any] = {
        "lim": lim,
        "jd": jd_parsed,
        "site_line": site_line,
        "zip_code": zip_merged,
        "client_city": city_merged,
        "bim_bridge_json": bim_bridge_json,
        "bim_clash_report": bim_clash_report,
        "scout_profile_payload": scout_profile_payload,
        "image_bytes": image_bytes,
        "image_meta": image_meta,
        "has_image": has_image,
        "jf_gate": jf_gate,
        "scout_vertical": scout_vertical,
    }
    payload = _research_static_collect(_iter_research_sse_events(ctx))
    return JSONResponse(payload, headers=_research_sse_cors_headers(request))


# ============================================================================
# DATA CENTER PERMITTING ANALYSIS (B2B)
# ============================================================================


class DataCenterAnalysisRequest(BaseModel):
    """Request for data center site permitting analysis."""
    address: str = Field(..., description="Street address")
    city: str = Field(..., description="City name")
    state: str = Field(..., description="State (e.g., TX, CA)")
    projected_mw: int = Field(..., description="Projected power draw in megawatts")
    requester_name: str = Field(..., description="Person requesting analysis")
    requester_email: str = Field(..., description="Email address")
    requester_phone: Optional[str] = Field(None, description="Phone number")
    company_name: str = Field(..., description="Company/Developer name")
    role: Optional[str] = Field(None, description="Role (Developer, Consultant, Contractor)")
    expected_timeline_months: Optional[int] = Field(None, description="Expected project timeline")


class DataCenterAnalysisResponse(BaseModel):
    """Data center permitting analysis result."""
    address: str
    city: str
    state: str
    projected_mw: int
    permitting_risk_score: int
    risk_level: str
    estimated_timeline_months: int
    critical_blockers: List[str]
    political_risk_alerts: List[str]
    environmental_concerns: List[str]
    utility_capacity_check: Dict[str, Any]
    labor_availability: Dict[str, Any]
    estimated_audit_value_usd: int
    recommendations: List[str]
    analysis_timestamp: str


@app.post("/data-center-analysis/request", tags=["Data Center"])
async def request_data_center_analysis(req: DataCenterAnalysisRequest) -> Dict[str, Any]:
    """
    Request a data center permitting analysis.
    
    This is the B2B entry point for data center developers and consultants
    seeking permitting risk assessment for a specific site.
    """
    try:
        # Run the analysis
        analyzer = DataCenterPermittingAnalysis()
        analysis = analyzer.analyze_site(
            address=req.address,
            city=req.city,
            state=req.state,
            projected_mw=req.projected_mw,
        )

        # Store lead in Supabase
        try:
            from supabase import create_client
            sb = create_client(
                os.environ.get("SUPABASE_URL"),
                os.environ.get("SUPABASE_KEY"),
            )
            
            lead_data = {
                "requester_name": req.requester_name,
                "requester_email": req.requester_email,
                "requester_phone": req.requester_phone,
                "company_name": req.company_name,
                "role": req.role,
                "project_address": req.address,
                "project_city": req.city,
                "project_state": req.state,
                "projected_mw": req.projected_mw,
                "expected_timeline_months": req.expected_timeline_months,
                "risk_score": analysis["permitting_risk_score"],
                "risk_level": analysis["risk_level"],
                "estimated_timeline_months": analysis["estimated_timeline_months"],
                "critical_blockers": analysis["critical_blockers"],
                "recommendations": analysis["recommendations"],
                "analysis_result": analysis,
                "status": "new",
            }
            
            sb.table("data_center_leads").insert(lead_data).execute()
            logger.info(f"Data center lead created: {req.requester_email}")
        except Exception as e:
            logger.error(f"Failed to store lead: {e}")
            # Non-blocking; analysis still returns

        return {
            "status": "success",
            "analysis": analysis,
            "message": "Analysis complete. A RegGuard analyst will contact you within 24 hours.",
        }

    except Exception as e:
        logger.error(f"Data center analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/data-center-analysis/leads", tags=["Data Center"])
async def list_data_center_leads(request: Request) -> Dict[str, Any]:
    """
    List all data center analysis leads (admin only).
    
    Requires authentication + admin role.
    """
    try:
        from supabase import create_client
        sb = create_client(
            os.environ.get("SUPABASE_URL"),
            os.environ.get("SUPABASE_KEY"),
        )
        
        response = sb.table("data_center_leads").select("*").order("created_at", desc=True).execute()
        
        return {
            "status": "success",
            "leads": response.data,
            "count": len(response.data),
        }
    except Exception as e:
        logger.error(f"Failed to fetch leads: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# RESULT DELIVERY ENDPOINTS (SMS & EMAIL)
# ==========================================

class ResearchDeliverySummary(BaseModel):
    """Lightweight summary for free-trial results not yet persisted in DB."""
    zip: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    risk_level: Optional[str] = None
    risk_unavailable: Optional[bool] = None
    timeline: Optional[str] = None
    cost: Optional[float] = None
    address: Optional[str] = None
    estimates_unverified: Optional[bool] = None
    preview: Optional[bool] = None


class SendSmsRequest(BaseModel):
    phone_number: str
    summary: Optional[ResearchDeliverySummary] = None
    analysis: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    research_id: Optional[str] = None


class SendEmailRequest(BaseModel):
    email: Optional[str] = None
    email_address: Optional[str] = None
    summary: Optional[ResearchDeliverySummary] = None
    analysis: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    research_id: Optional[str] = None


def _research_data_from_summary(summary: ResearchDeliverySummary) -> Dict[str, Any]:
    """Convert a free-trial summary payload into delivery-service research_data shape."""
    from honesty import apply_honesty_layer, UNAVAILABLE

    unverified = bool(summary.estimates_unverified or summary.preview or summary.risk_unavailable)
    risk_raw = (summary.risk_level or "").upper()
    if summary.risk_unavailable or unverified or risk_raw in ("", "UNKNOWN", UNAVAILABLE, "PRELIMINARY"):
        risk = UNAVAILABLE
        high_risk = 0
    else:
        risk = risk_raw
        high_risk = 1 if risk in ("HIGH", "CRITICAL") else 0
    cost = float(summary.cost or 0)
    timeline = summary.timeline or "TBD"
    payload = {
        "preview": bool(summary.preview or unverified),
        "project_info": {
            "zip": summary.zip or "",
            "city": summary.city or "",
            "state": summary.state or "",
            "address": summary.address or "",
        },
        "summary": {
            "high_risk_count": high_risk,
            "estimated_total_cost": cost,
            "estimated_timeline": timeline,
            "total_environmental_risks": high_risk,
            "total_punch_list_items": 0,
            "estimates_unverified": unverified,
        },
        "punch_list": {
            "punch_list": [],
            "critical_path": [],
            "estimated_total_cost": cost,
            "timeline_summary": timeline,
            "estimates_unverified": unverified,
        },
        "environmental_screening": {
            "risk_level": risk,
            "findings": [],
            "risk_score_hidden": risk == UNAVAILABLE,
        },
    }
    if unverified or risk == UNAVAILABLE:
        return apply_honesty_layer(
            payload,
            source="delivery_summary",
            risk_verified=False,
            cost_verified=False,
            timeline_verified=False,
        )
    return payload


def _resolve_research_data(
    research_id: Optional[str],
    summary: Optional[ResearchDeliverySummary],
    analysis: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Prefer full analysis (persist it), then stored report, then lightweight summary."""
    from research_store import save_research, share_url_for

    if analysis and isinstance(analysis, dict):
        meta = save_research(analysis, research_id=research_id or analysis.get("research_id"))
        data = dict(analysis)
        data["research_id"] = meta["research_id"]
        data["share_url"] = meta["share_url"]
        return data

    if research_id:
        stored = _get_research_data(research_id)
        if stored:
            stored.setdefault("share_url", share_url_for(research_id))
            return stored

    if summary is not None:
        data = _research_data_from_summary(summary)
        if research_id:
            data["research_id"] = research_id
            data["share_url"] = share_url_for(research_id)
        return data

    raise HTTPException(
        status_code=404,
        detail="Research result not found. Provide analysis or summary for free-trial delivery.",
    )


@app.post("/research/send-sms", tags=["Results"])
async def send_result_sms_standalone(
    request: Request,
    body: SendSmsRequest,
) -> Dict[str, Any]:
    """
    Send research summary via SMS without requiring a persisted research record.
    Accepts optional summary for free-trial modal delivery.
    """
    try:
        user_id = body.user_id or request.headers.get("X-User-ID") or "anonymous"
        research_id = body.research_id or f"ephemeral-{user_id}"
        research_data = _resolve_research_data(body.research_id, body.summary, body.analysis)

        from result_delivery_service import get_delivery_service
        delivery_service = get_delivery_service(db_pool=None)

        result = await delivery_service.send_sms(
            phone_number=body.phone_number,
            research_data=research_data,
            user_id=user_id,
            research_id=research_id,
        )

        if result["status"] == "failed":
            err = result.get("error", "Failed to send SMS")
            if "rate limit" in str(err).lower():
                raise HTTPException(status_code=429, detail=str(err))
            if "not configured" in str(err).lower() or "twilio" in str(err).lower():
                raise HTTPException(status_code=503, detail=str(err))
            raise HTTPException(status_code=400, detail=err)

        return {
            "status": "sent",
            "message_id": result.get("message_id"),
            "phone": result.get("phone"),
            "delivery_id": result.get("delivery_id"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending SMS: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send SMS: {str(e)}")


@app.post("/research/send-email", tags=["Results"])
async def send_result_email_standalone(
    request: Request,
    body: SendEmailRequest,
) -> Dict[str, Any]:
    """
    Send research summary via email without requiring a persisted research record.
    Accepts optional summary for free-trial modal delivery.
    """
    try:
        email_address = body.email_address or body.email
        if not email_address:
            raise HTTPException(status_code=400, detail="email or email_address is required")

        user_id = body.user_id or request.headers.get("X-User-ID") or "anonymous"
        research_id = body.research_id or f"ephemeral-{user_id}"
        research_data = _resolve_research_data(body.research_id, body.summary, body.analysis)

        from result_delivery_service import get_delivery_service
        delivery_service = get_delivery_service(db_pool=None)

        result = await delivery_service.send_email(
            email_address=email_address,
            research_data=research_data,
            user_id=user_id,
            research_id=research_id,
        )

        if result["status"] == "failed":
            err = result.get("error", "Failed to send email")
            if "rate limit" in str(err).lower():
                raise HTTPException(status_code=429, detail=str(err))
            # Clear signal for frontend mailto fallback when Resend/SendGrid missing
            if "not configured" in str(err).lower() or "resend" in str(err).lower() or "testing email" in str(err).lower() or "sendgrid" in str(err).lower():
                raise HTTPException(status_code=503, detail=str(err))
            raise HTTPException(status_code=400, detail=err)

        return {
            "status": "sent",
            "email_id": result.get("email_id"),
            "email": result.get("email"),
            "delivery_id": result.get("delivery_id"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


@app.post("/research/{research_id}/send-sms", tags=["Results"])
async def send_result_sms(
    request: Request,
    research_id: str,
    body: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """
    Send research result via SMS (Twilio).
    Accepts phone_number plus optional summary for free-trial results.
    """
    try:
        phone_number = body.get("phone_number")
        if not phone_number:
            raise HTTPException(status_code=400, detail="phone_number is required")

        user_id = body.get("user_id") or request.headers.get("X-User-ID") or "anonymous"
        summary_raw = body.get("summary")
        summary = ResearchDeliverySummary(**summary_raw) if isinstance(summary_raw, dict) else None
        analysis = body.get("analysis") if isinstance(body.get("analysis"), dict) else None
        research_data = _resolve_research_data(research_id, summary, analysis)

        from result_delivery_service import get_delivery_service
        delivery_service = get_delivery_service(db_pool=None)

        result = await delivery_service.send_sms(
            phone_number=phone_number,
            research_data=research_data,
            user_id=user_id,
            research_id=research_id,
        )

        if result["status"] == "failed":
            err = result.get("error", "Failed to send SMS")
            if "rate limit" in str(err).lower():
                raise HTTPException(status_code=429, detail=str(err))
            if "not configured" in str(err).lower() or "twilio" in str(err).lower():
                raise HTTPException(status_code=503, detail=str(err))
            raise HTTPException(status_code=400, detail=err)

        return {
            "status": "sent",
            "message_id": result.get("message_id"),
            "phone": result.get("phone"),
            "delivery_id": result.get("delivery_id"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending SMS: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send SMS: {str(e)}")


@app.post("/research/{research_id}/send-email", tags=["Results"])
async def send_result_email(
    request: Request,
    research_id: str,
    body: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """
    Send research result via email (SendGrid/Resend).
    Accepts email/email_address plus optional summary for free-trial results.
    """
    try:
        email_address = body.get("email_address") or body.get("email")
        if not email_address:
            raise HTTPException(status_code=400, detail="email or email_address is required")

        user_id = body.get("user_id") or request.headers.get("X-User-ID") or "anonymous"
        summary_raw = body.get("summary")
        summary = ResearchDeliverySummary(**summary_raw) if isinstance(summary_raw, dict) else None
        analysis = body.get("analysis") if isinstance(body.get("analysis"), dict) else None
        research_data = _resolve_research_data(research_id, summary, analysis)

        from result_delivery_service import get_delivery_service
        delivery_service = get_delivery_service(db_pool=None)

        result = await delivery_service.send_email(
            email_address=email_address,
            research_data=research_data,
            user_id=user_id,
            research_id=research_id,
        )

        if result["status"] == "failed":
            err = result.get("error", "Failed to send email")
            if "rate limit" in str(err).lower():
                raise HTTPException(status_code=429, detail=str(err))
            if (
                "not configured" in str(err).lower()
                or "resend" in str(err).lower()
                or "testing email" in str(err).lower()
                or "sendgrid" in str(err).lower()
            ):
                raise HTTPException(status_code=503, detail=str(err))
            raise HTTPException(status_code=400, detail=err)

        return {
            "status": "sent",
            "email_id": result.get("email_id"),
            "email": result.get("email"),
            "delivery_id": result.get("delivery_id"),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


def _get_research_data(research_id: str) -> Optional[Dict[str, Any]]:
    """Fetch persisted research analysis by ID (local store + optional Supabase)."""
    try:
        from research_store import get_analysis

        return get_analysis(research_id)
    except Exception as e:
        logger.warning(f"_get_research_data failed for {research_id}: {e}")
        return None


class PersistResearchRequest(BaseModel):
    analysis: Dict[str, Any]
    research_id: Optional[str] = None


@app.post("/research/persist", tags=["Results"])
async def persist_research_report(body: PersistResearchRequest) -> Dict[str, Any]:
    """
    Persist free-trial / research analysis and return a shareable /r/{id} URL.
    Safe to call repeatedly for the same research_id (upsert).
    """
    from research_store import save_research

    if not body.analysis or not isinstance(body.analysis, dict):
        raise HTTPException(status_code=400, detail="analysis object is required")
    meta = save_research(body.analysis, research_id=body.research_id)
    return {"status": "ok", **meta}


@app.get("/research/{research_id}/report", tags=["Results"])
async def get_research_report(research_id: str) -> Dict[str, Any]:
    """Public JSON for shareable report page /r/{id}."""
    from research_store import extract_sources, get_research, share_url_for

    record = get_research(research_id)
    if not record:
        raise HTTPException(status_code=404, detail="Report not found or expired")
    analysis = record.get("analysis") or {}
    return {
        "research_id": record["id"],
        "share_url": record.get("share_url") or share_url_for(record["id"]),
        "created_at": record.get("created_at"),
        "expires_at": record.get("expires_at"),
        "preview": record.get("preview"),
        "analysis": analysis,
        "sources": extract_sources(analysis),
    }


@app.get("/r/{research_id}", tags=["Results"])
async def get_research_report_short(research_id: str) -> Dict[str, Any]:
    """Alias for /research/{id}/report (API clients / curl). Frontend uses SPA /r/:id."""
    return await get_research_report(research_id)


# ========== Saved Jobs (weekly habit) ==========

@app.post("/jobs", tags=["Jobs"])
async def create_or_update_job(body: SaveJobRequest) -> Dict[str, Any]:
    """Create or upsert a saved job (deduped by email + address)."""
    from jobs_store import upsert_job

    try:
        job = upsert_job(
            owner_email=body.owner_email,
            address=body.address,
            city=body.city or "",
            state=body.state or "",
            zip_code=body.zip or "",
            project_type=body.project_type or "general",
            owner_key=body.owner_key,
            job_id=body.job_id,
            last_research_id=body.last_research_id,
            share_url=body.share_url,
            summary_snapshot=body.summary_snapshot,
            notes=body.notes or "",
            status=body.status or "active",
        )
        return {"status": "ok", "job": job}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.get("/jobs", tags=["Jobs"])
async def list_saved_jobs(
    email: str = "",
    owner_key: str = "",
    include_archived: bool = False,
) -> Dict[str, Any]:
    """List jobs for an email and/or owner_key (device id)."""
    from jobs_store import list_jobs

    if not email and not owner_key:
        raise HTTPException(status_code=400, detail="email or owner_key is required")
    jobs = list_jobs(email=email or None, owner_key=owner_key or None, include_archived=include_archived)
    return {"jobs": jobs, "count": len(jobs)}


@app.get("/jobs/{job_id}", tags=["Jobs"])
async def get_saved_job(
    job_id: str,
    email: str = "",
    owner_key: str = "",
) -> Dict[str, Any]:
    from jobs_store import get_job

    job = get_job(job_id, email=email or None, owner_key=owner_key or None)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job": job}


@app.delete("/jobs/{job_id}", tags=["Jobs"])
async def delete_saved_job(
    job_id: str,
    email: str = "",
    owner_key: str = "",
) -> Dict[str, Any]:
    from jobs_store import delete_job

    ok = delete_job(job_id, email=email or None, owner_key=owner_key or None)
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": "deleted", "job_id": job_id}


@app.post("/jobs/{job_id}/attach-research", tags=["Jobs"])
async def attach_research_to_job(job_id: str, body: AttachResearchRequest) -> Dict[str, Any]:
    from jobs_store import attach_research

    job = attach_research(
        job_id,
        research_id=body.research_id,
        share_url=body.share_url,
        summary_snapshot=body.summary_snapshot,
        email=body.owner_email,
        owner_key=body.owner_key,
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": "ok", "job": job}


def _require_cron_secret(x_cron_secret: Optional[str] = None) -> None:
    expected = (os.getenv("CRON_SECRET") or "").strip()
    if not expected or (x_cron_secret or "").strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid cron secret")


def _require_admin_secret(x_admin_secret: Optional[str] = None) -> None:
    expected = (os.getenv("ADMIN_SECRET") or "").strip()
    if not expected or (x_admin_secret or "").strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid admin secret")


@app.post("/jobs", tags=["Jobs"])
async def create_or_update_job(body: SaveJobRequest) -> Dict[str, Any]:
    """Create or upsert a saved job (deduped by email + address)."""
    from jobs_store import upsert_job

    try:
        job = upsert_job(
            owner_email=body.owner_email,
            address=body.address,
            city=body.city or "",
            state=body.state or "",
            zip_code=body.zip or "",
            project_type=body.project_type or "general",
            owner_key=body.owner_key,
            job_id=body.job_id,
            last_research_id=body.last_research_id,
            share_url=body.share_url,
            summary_snapshot=body.summary_snapshot,
            notes=body.notes or "",
            status=body.status or "active",
        )
        return {"status": "ok", "job": job}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.get("/jobs", tags=["Jobs"])
async def list_saved_jobs(
    email: str = "",
    owner_key: str = "",
    include_archived: bool = False,
) -> Dict[str, Any]:
    """List jobs for an email and/or owner_key (device id)."""
    from jobs_store import list_jobs

    if not email and not owner_key:
        raise HTTPException(status_code=400, detail="email or owner_key is required")
    jobs = list_jobs(
        email=email or None,
        owner_key=owner_key or None,
        include_archived=include_archived,
    )
    return {"jobs": jobs, "count": len(jobs)}


@app.get("/jobs/{job_id}", tags=["Jobs"])
async def get_saved_job(
    job_id: str,
    email: str = "",
    owner_key: str = "",
) -> Dict[str, Any]:
    from jobs_store import get_job

    job = get_job(job_id, email=email or None, owner_key=owner_key or None)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job": job}


@app.delete("/jobs/{job_id}", tags=["Jobs"])
async def delete_saved_job(
    job_id: str,
    email: str = "",
    owner_key: str = "",
) -> Dict[str, Any]:
    from jobs_store import delete_job

    ok = delete_job(job_id, email=email or None, owner_key=owner_key or None)
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": "deleted", "job_id": job_id}


@app.post("/jobs/{job_id}/attach-research", tags=["Jobs"])
async def attach_research_to_job(job_id: str, body: AttachResearchRequest) -> Dict[str, Any]:
    from jobs_store import attach_research

    job = attach_research(
        job_id,
        research_id=body.research_id,
        share_url=body.share_url,
        summary_snapshot=body.summary_snapshot,
        email=body.owner_email,
        owner_key=body.owner_key,
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": "ok", "job": job}


class RecheckJobRequest(BaseModel):
    owner_email: str
    owner_key: Optional[str] = None


@app.post("/jobs/{job_id}/recheck", tags=["Jobs"])
async def recheck_saved_job(job_id: str, body: RecheckJobRequest) -> Dict[str, Any]:
    """
    Re-run diligence for a Saved Job and return arbitrage diff vs last snapshot.
    """
    from arbitrage_enrichment import diff_arbitrage_snapshots, enrich_analysis_with_arbitrage
    from entitlement import has_paid_access
    from free_pack_confirm import run_free_pack_confirm
    from instant_analysis import build_instant_fallback_analysis
    from jobs_store import get_job, upsert_job
    from jurisdiction import geocode_profile_from_address

    job = get_job(job_id, email=body.owner_email, owner_key=body.owner_key)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    prev_snap = ((job.get("summary_snapshot") or {}).get("arbitrage_snapshot")) or {}
    paid = has_paid_access(body.owner_email)
    address = job.get("address") or ""
    analysis: Optional[Dict[str, Any]] = None
    try:
        profile = geocode_profile_from_address(address)
        if profile and paid:
            from pro_deep_analysis import run_pro_deep_analysis

            analysis = await asyncio.wait_for(
                run_pro_deep_analysis(
                    address=address,
                    city=profile.city,
                    state=profile.state_short,
                    zip_code=profile.zip5,
                    latitude=profile.latitude,
                    longitude=profile.longitude,
                    project_type=job.get("project_type") or "general",
                    email=body.owner_email or "",
                ),
                timeout=120.0,
            )
        elif profile:
            free_timeout = float(os.getenv("FREE_TRIAL_ANALYSIS_TIMEOUT_SEC") or "10")
            analysis = await asyncio.wait_for(
                run_free_pack_confirm(
                    address=address,
                    city=profile.city,
                    state=profile.state_short,
                    zip_code=profile.zip5,
                    latitude=profile.latitude,
                    longitude=profile.longitude,
                    project_type=job.get("project_type") or "general",
                ),
                timeout=max(5.0, free_timeout),
            )
    except Exception as e:
        logger.warning("Job recheck analysis failed: %s", e)
        analysis = None

    if not analysis:
        analysis = build_instant_fallback_analysis(
            address=address,
            project_type=job.get("project_type") or "general",
            zip_code=job.get("zip") or "",
        )

    analysis = enrich_analysis_with_arbitrage(analysis)
    cur_snap = analysis.get("arbitrage_snapshot") or {}
    diff = diff_arbitrage_snapshots(prev_snap, cur_snap)
    summary = analysis.get("summary") or {}
    research_id = str(
        analysis.get("research_id") or analysis.get("timestamp") or f"recheck-{job_id}"
    )

    updated = upsert_job(
        owner_email=body.owner_email,
        address=address,
        city=job.get("city") or "",
        state=job.get("state") or "",
        zip_code=job.get("zip") or "",
        project_type=job.get("project_type") or "general",
        owner_key=body.owner_key or job.get("owner_key"),
        job_id=job_id,
        last_research_id=research_id,
        share_url=analysis.get("share_url") or job.get("share_url"),
        summary_snapshot={
            "estimated_timeline": summary.get("estimated_timeline"),
            "estimated_total_cost": summary.get("estimated_total_cost"),
            "risk_level": (analysis.get("environmental_screening") or {}).get("risk_level"),
            "preview": bool(analysis.get("preview")),
            "punch_count": summary.get("total_punch_list_items"),
            "arbitrage_snapshot": cur_snap,
            "last_diff": diff,
        },
    )
    analysis["job_id"] = job_id
    return {
        "status": "ok",
        "job": updated,
        "diff": diff,
        "analysis_data": analysis,
        "research_id": research_id,
        "paid": paid,
    }


_BID_PACKET_CACHE: Dict[str, str] = {}
_BID_RECEIPT_CACHE: Dict[str, str] = {}


def _unwrap_analysis_body(body: Dict[str, Any]) -> tuple:
    """Return (analysis_dict, generated_for, share_url, mode)."""
    data = body if isinstance(body, dict) else {}
    generated_for = data.get("generated_for") or data.get("email") or None
    share_url = data.get("share_url") or None
    mode = str(data.get("mode") or "receipt").lower().strip()
    if "analysis_data" in data and isinstance(data["analysis_data"], dict):
        data = data["analysis_data"]
    return data, generated_for, share_url, mode


@app.post("/bid-receipt/pdf", tags=["Samples"])
async def create_bid_receipt_pdf(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Generate the 1-page Bid Risk Receipt (default forwardable share object):
    contingency band + top 3 margin killers + share CTA.
    """
    from arbitrage_enrichment import enrich_analysis_with_arbitrage
    from bid_risk_receipt_pdf import generate_bid_risk_receipt_pdf

    data, generated_for, share_url, _mode = _unwrap_analysis_body(body)
    if not data.get("fee_card") or not data.get("margin_killers"):
        data = enrich_analysis_with_arbitrage(data)
    path = generate_bid_risk_receipt_pdf(
        data,
        generated_for=str(generated_for) if generated_for else None,
        share_url=str(share_url) if share_url else None,
    )
    token = hashlib.sha256(path.encode("utf-8")).hexdigest()[:24]
    _BID_RECEIPT_CACHE[token] = path
    api = os.getenv("BACKEND_URL", "https://regguard-api.onrender.com").rstrip("/")
    return {
        "status": "ok",
        "download_url": f"{api}/bid-receipt/pdf/{token}",
        "filename": "RegGuard_Bid_Risk_Receipt.pdf",
        "artifact": "bid_risk_receipt",
    }


@app.get("/bid-receipt/pdf/{token}", tags=["Samples"])
async def download_bid_receipt_pdf(token: str):
    from fastapi.responses import FileResponse

    path = _BID_RECEIPT_CACHE.get((token or "").strip())
    if not path or not os.path.isfile(path):
        raise HTTPException(
            status_code=404, detail="Bid Risk Receipt expired or not found — regenerate"
        )
    return FileResponse(
        path,
        media_type="application/pdf",
        filename="RegGuard_Bid_Risk_Receipt.pdf",
    )


@app.post("/bid-packet/pdf", tags=["Samples"])
async def create_bid_packet_pdf(analysis_data: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Generate a forwardable PDF. Default mode=receipt (1-page Bid Risk Receipt).
    Pass mode=full for the longer bid packet (fees, docs, full punch).
    """
    from arbitrage_enrichment import enrich_analysis_with_arbitrage
    from bid_packet_pdf import generate_bid_packet_pdf
    from bid_risk_receipt_pdf import generate_bid_risk_receipt_pdf

    data, generated_for, share_url, mode = _unwrap_analysis_body(analysis_data)
    band = data.get("contingency_band") or {}
    if (
        not data.get("fee_card")
        or not data.get("margin_killers")
        or not band
        or band.get("pct_low") is None
        or band.get("pct_high") is None
    ):
        data = enrich_analysis_with_arbitrage(data)

    api = os.getenv("BACKEND_URL", "https://regguard-api.onrender.com").rstrip("/")
    if mode in ("full", "packet", "bid_packet"):
        path = generate_bid_packet_pdf(data)
        token = hashlib.sha256(path.encode("utf-8")).hexdigest()[:24]
        _BID_PACKET_CACHE[token] = path
        return {
            "status": "ok",
            "download_url": f"{api}/bid-packet/pdf/{token}",
            "filename": "RegGuard_Bid_Packet.pdf",
            "artifact": "bid_packet",
        }

    path = generate_bid_risk_receipt_pdf(
        data,
        generated_for=str(generated_for) if generated_for else None,
        share_url=str(share_url) if share_url else None,
    )
    token = hashlib.sha256(path.encode("utf-8")).hexdigest()[:24]
    _BID_RECEIPT_CACHE[token] = path
    return {
        "status": "ok",
        "download_url": f"{api}/bid-receipt/pdf/{token}",
        "filename": "RegGuard_Bid_Risk_Receipt.pdf",
        "artifact": "bid_risk_receipt",
    }


@app.get("/bid-packet/pdf/{token}", tags=["Samples"])
async def download_bid_packet_pdf(token: str):
    from fastapi.responses import FileResponse

    path = _BID_PACKET_CACHE.get((token or "").strip()) or _BID_RECEIPT_CACHE.get(
        (token or "").strip()
    )
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Bid packet expired or not found — regenerate")
    name = (
        "RegGuard_Bid_Risk_Receipt.pdf"
        if "bid_receipt" in path
        else "RegGuard_Bid_Packet.pdf"
    )
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=name,
    )


@app.post("/cron/weekly-job-reminders", tags=["Cron"])
async def cron_weekly_job_reminders(
    x_cron_secret: Optional[str] = Header(default=None, alias="X-Cron-Secret"),
) -> Dict[str, Any]:
    """
    Send weekly Saved Jobs digest emails.
    Schedule externally (e.g. cron-job.org) → Render:
      POST /cron/weekly-job-reminders
      Header: X-Cron-Secret: $CRON_SECRET
    """
    _require_cron_secret(x_cron_secret)
    from email_service import get_email_service
    from jobs_store import list_emails_with_active_jobs

    svc = get_email_service()
    if not svc or not hasattr(svc, "send_weekly_job_reminder"):
        raise HTTPException(status_code=503, detail="Email service not configured")

    grouped = list_emails_with_active_jobs()
    sent = 0
    failed = 0
    for email, jobs in grouped.items():
        try:
            ok = await svc.send_weekly_job_reminder(email, jobs)
            if ok:
                sent += 1
            else:
                failed += 1
        except Exception as e:
            logger.warning("Weekly reminder failed for %s: %s", email, e)
            failed += 1
    return {
        "status": "ok",
        "recipients": len(grouped),
        "sent": sent,
        "failed": failed,
    }


@app.post("/cron/day7-win-emails", tags=["Cron"])
async def cron_day7_win_emails(
    x_cron_secret: Optional[str] = Header(default=None, alias="X-Cron-Secret"),
) -> Dict[str, Any]:
    """
    Send Day-7 Partner/Pro habit emails.
    Schedule daily: POST /cron/day7-win-emails with X-Cron-Secret.
    """
    _require_cron_secret(x_cron_secret)
    from email_service import get_email_service
    from nurture_store import due_day7_wins, mark_sent

    svc = get_email_service()
    if not svc or not hasattr(svc, "send_plan_win_email"):
        raise HTTPException(status_code=503, detail="Email service not configured")

    due = due_day7_wins()
    sent = 0
    failed = 0
    for item in due:
        try:
            ok = await svc.send_plan_win_email(
                item["email"], item.get("tier") or "contractor_pro", day7=True
            )
            if ok:
                mark_sent(item["id"])
                sent += 1
            else:
                failed += 1
        except Exception as e:
            logger.warning("Day7 win failed for %s: %s", item.get("email"), e)
            failed += 1
    return {"status": "ok", "due": len(due), "sent": sent, "failed": failed}


@app.get("/sample/plano-punch-list.pdf", tags=["Samples"])
async def download_sample_plano_pdf():
    """Labeled SAMPLE Plano punch-list PDF for pricing / landing."""
    from fastapi.responses import FileResponse

    from sample_plano_pdf import generate_sample_plano_punch_pdf

    path = generate_sample_plano_punch_pdf()
    return FileResponse(
        path,
        media_type="application/pdf",
        filename="RegGuard_Plano_Punch_List_SAMPLE.pdf",
    )


@app.post("/affiliates/register", tags=["Affiliates"])
async def register_affiliate_endpoint(body: AffiliateRegisterRequest) -> Dict[str, Any]:
    from affiliate_store import frontend_referral_url, register_affiliate

    try:
        aff = register_affiliate(email=body.email, name=body.name or "", code=body.code)
        return {
            "status": "ok",
            "affiliate": aff,
            "referral_url": frontend_referral_url(aff["code"]),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/affiliates/click", tags=["Affiliates"])
async def affiliate_click(code: str = "") -> Dict[str, Any]:
    from affiliate_store import record_click

    ok = record_click(code)
    return {"status": "ok" if ok else "unknown", "code": (code or "").strip().lower()}


@app.get("/affiliates/me", tags=["Affiliates"])
async def affiliate_me(email: str = "") -> Dict[str, Any]:
    from affiliate_store import frontend_referral_url, list_affiliates, list_commissions

    email_n = (email or "").strip().lower()
    if not email_n:
        raise HTTPException(status_code=400, detail="email is required")
    aff = next((a for a in list_affiliates() if a.get("email") == email_n), None)
    if not aff:
        raise HTTPException(status_code=404, detail="No affiliate for this email")
    commissions = [c for c in list_commissions() if c.get("affiliate_email") == email_n]
    unpaid = sum(int(c.get("commission_cents") or 0) for c in commissions if not c.get("paid"))
    return {
        "affiliate": aff,
        "referral_url": frontend_referral_url(aff["code"]),
        "commissions": commissions,
        "unpaid_cents": unpaid,
    }


@app.get("/admin/affiliates", tags=["Admin"])
async def admin_list_affiliates(
    x_admin_secret: Optional[str] = Header(default=None, alias="X-Admin-Secret"),
) -> Dict[str, Any]:
    _require_admin_secret(x_admin_secret)
    from affiliate_store import list_affiliates, list_commissions

    return {
        "affiliates": list_affiliates(),
        "commissions": list_commissions(),
        "unpaid": list_commissions(unpaid_only=True),
    }


@app.post("/admin/affiliates/mark-paid", tags=["Admin"])
async def admin_mark_commission_paid(
    body: MarkCommissionPaidRequest,
    x_admin_secret: Optional[str] = Header(default=None, alias="X-Admin-Secret"),
) -> Dict[str, Any]:
    _require_admin_secret(x_admin_secret)
    from affiliate_store import mark_commission_paid

    row = mark_commission_paid(body.commission_id)
    if not row:
        raise HTTPException(status_code=404, detail="Commission not found")
    return {"status": "ok", "commission": row}



def _running_on_vercel() -> bool:
    return bool(
        os.environ.get("VERCEL")
        or os.environ.get("VERCEL_ENV")
        or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
    )


# Vercel serverless (root vercel.json): expose routes under /api/* → backend handlers.
_backend_app = app
if _running_on_vercel():
    _vercel_gateway = FastAPI(title="Reg Guard")
    _vercel_gateway.mount("/api", _backend_app)
    app = _vercel_gateway

# @vercel/python ASGI entry (Mangum when available).
try:
    from mangum import Mangum

    handler = Mangum(app, lifespan="off", api_gateway_base_path="/api")
except ImportError:
    handler = app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(_backend_app, host="127.0.0.1", port=8000)
