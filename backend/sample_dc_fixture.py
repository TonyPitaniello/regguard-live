"""
SAMPLE fixture: Fort Worth data-center-adjacent site diligence.

Site: 9999 Chapin School Road, Fort Worth, TX 76126
Why this site: large-load / DC-adjacent corridor already screened with Reg Guard
IC Diligence Bundle patterns; AHJ cites come from the live Fort Worth city pack
(portal, Accela apply, Master Fee Schedule PDF).

Labeled SAMPLE everywhere — marketing deliverable, not a sealed bid or interconnect study.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

# Real Fort Worth Development Services cites (from ahj_data/fort_worth.json)
FW_PORTAL = "https://www.fortworthtexas.gov/departments/development-services"
FW_FEES = (
    "https://www.fortworthtexas.gov/files/assets/public/v/9/development-services/"
    "documents/resources-applications-forms-videos/f/development-fees-schedule.pdf"
)
FW_APPLY = "https://aca-prod.accela.com/CFW"
FW_NEW_CONSTRUCTION_PACKET = (
    "https://www.fortworthtexas.gov/files/assets/public/v/8/development-services/"
    "documents/resources-applications-forms-videos/p/new-construction-packet-fillable-0522.pdf"
)
FW_STORMWATER = (
    "https://www.fortworthtexas.gov/files/assets/public/v/1/development-services/"
    "all-deactivated-pdfs/development-fee-schedule-preview.pdf"
)

SAMPLE_SHARE = "https://app.regguardagent.com/sample/dc-chapin"
SAMPLE_SITE_LINE = "9999 Chapin School Road, Fort Worth, TX 76126"


def build_sample_dc_analysis(*, generated_for: str = "SAMPLE buyer") -> Dict[str, Any]:
    """Rich IC-depth analysis for sample tier deliverables."""
    now = datetime.now(timezone.utc)
    valid = now + timedelta(days=7)
    return {
        "project_info": {
            "address": "9999 Chapin School Road",
            "city": "Fort Worth",
            "state": "TX",
            "zip": "76126",
            "type": "data-center",
        },
        "project_type": "data-center",
        "depth_tier": "ic_full",
        "research_depth": "ic",
        "ic_package": True,
        "depth_badge": "IC PROJECT (SAMPLE)",
        "coverage": {
            "badge": "Full city pack",
            "tier": "full_pack",
            "warning": "SAMPLE — confirm every fee on the live Fort Worth schedule before bid.",
        },
        "share_url": SAMPLE_SHARE,
        "research_id": "rg-sample-chapin-fw",
        "regguard_stamp": {
            "schema": "regguard.stamp.v2",
            "grade": "FAIL",
            "label": "REGGUARD STAMP: HOLD — high pre-bid risk",
            "headline": (
                "High pre-bid risk on this site. This is not a rejection of the job — "
                "it means resolve the drivers below before treating the bid as clear."
            ),
            "drivers": [
                {
                    "severity": "FAIL",
                    "label": "ERCOT / TDSP large-load timing",
                    "detail": (
                        "Data center or industrial large load: treat ERCOT/TDSP interconnection "
                        "as parallel to City of Fort Worth permits"
                    ),
                    "source_url": FW_PORTAL,
                },
                {
                    "severity": "FAIL",
                    "label": "High contingency band (mid 23%)",
                    "detail": "Planning aid — confirm fees/timeline with AHJ before bid.",
                },
                {
                    "severity": "CAUTION",
                    "label": "Fee schedule is not a fixed number",
                    "detail": "Recheck Fort Worth Master Fee Schedule before locking contingency.",
                    "source_url": FW_FEES,
                },
            ],
            "fingerprint": "sample-chapin-fw",
            "stamped_at": now.isoformat().replace("+00:00", "Z"),
            "valid_until": valid.isoformat().replace("+00:00", "Z"),
            "valid_days": 7,
            "flagged_by": generated_for,
            "is_stale": False,
            "disclaimer": (
                "SAMPLE planning aid for pre-bid / pre-LOI screening only. "
                "NOT a bond, insurance quote, legal opinion, AHJ approval, or interconnection study."
            ),
        },
        "stamp_grade": "FAIL",
        "contingency_band": {
            "pct_low": 21.0,
            "pct_mid": 23.0,
            "pct_high": 26.0,
            "label": "Suggested contingency (SAMPLE)",
            "disclaimer": "Planning aid — not a quote or sealed bid; confirm with AHJ",
        },
        "ahj_card": {
            "name": "Fort Worth, TX AHJ",
            "portal_url": FW_PORTAL,
            "fees_url": FW_FEES,
            "apply_url": FW_APPLY,
            "last_verified": "2026-09-09",
        },
        "dc_positioning": {
            "headline": "Large-load / ERCOT path — Fort Worth Development Services + utility clocks",
        },
        "parallel_clocks": {
            "clocks": [
                {
                    "name": "AHJ / building / land use",
                    "label": "AHJ / building / land use",
                    "owner": "Fort Worth Development Services",
                    "status": "Confirm portal + Accela path before bid",
                    "detail": "Confirm portal + Accela path before bid",
                },
                {
                    "name": "Utility interconnection / large-load",
                    "label": "Utility interconnection / large-load",
                    "owner": "Serving utility / TDSP (confirm)",
                    "status": "Study path is NOT run by RegGuard — flag parallel schedule risk",
                    "detail": "Study path is NOT run by RegGuard — flag parallel schedule risk",
                },
                {
                    "name": "Water / NPDES",
                    "label": "Water / NPDES",
                    "owner": "TCEQ / utility",
                    "status": "Independent environmental clock — do not collapse into AHJ date",
                    "detail": "Independent environmental clock — do not collapse into AHJ date",
                },
            ]
        },
        "power_path_card": {
            "headline": "ERCOT / TDSP large-load path (planning only)",
            "fast41_candidate": False,
        },
        "inspection_sequence_card": {
            "steps": [
                "Permit application / intake",
                "Rough MEP inspections",
                "Final building / electrical inspection",
            ]
        },
        "margin_killers": [
            {
                "priority": "CRITICAL",
                "title": "ERCOT / TDSP large-load timing",
                "detail": (
                    "Data center or industrial large load: treat ERCOT/TDSP interconnection "
                    "as parallel to City of Fort Worth permits"
                ),
                "source_url": FW_PORTAL,
                "verified": True,
                "citation_tier": "verified",
                "planning_exposure": {"usd_low": 946, "usd_mid": 2800, "usd_high": 4732},
            },
            {
                "priority": "CRITICAL",
                "title": "Fee schedule is not a fixed number — recheck before bid",
                "detail": (
                    "Fort Worth fee pages are planning aids. Confirm on the official "
                    "Master Fee Schedule before locking contingency."
                ),
                "source_url": FW_FEES,
                "verified": True,
                "citation_tier": "verified",
                "planning_exposure": {"usd_low": 473, "usd_mid": 1500, "usd_high": 2524},
            },
            {
                "priority": "HIGH",
                "title": "Confirm trade application type early",
                "detail": "Wrong application type stalls review — verify electrical vs general building path",
                "source_url": FW_APPLY,
                "verified": True,
                "citation_tier": "link",
                "planning_exposure": {"usd_low": 473, "usd_mid": 1200, "usd_high": 2524},
            },
        ],
        "fee_card": {
            "timeline": "Pre-bid",
            "fees": [
                {
                    "label": "New commercial construction — plan review deposit + application + technology fee (intake)",
                    "trade": "BUILDING",
                    "amount_usd": 289,
                    "detail": "Plan review deposit $246 + application $28 + technology $15",
                    "source_url": FW_NEW_CONSTRUCTION_PACKET,
                    "source_label": "Fort Worth new construction packet",
                    "verified": True,
                    "owner": "Estimator / Permit runner",
                },
                {
                    "label": "Building permit balance — valuation-based (confirm Master Fee Schedule)",
                    "trade": "BUILDING",
                    "amount_usd": None,
                    "detail": "Confirm on live Fort Worth fee schedule",
                    "source_url": FW_FEES,
                    "source_label": "Fort Worth Master Fee Schedule",
                    "verified": True,
                    "amount_requires_schedule": True,
                    "owner": "Estimator / Permit runner",
                },
                {
                    "label": "Electrical / trade permit — confirm Fort Worth schedule",
                    "trade": "ELECTRICAL",
                    "amount_usd": None,
                    "detail": "Amount requires live Fort Worth fee schedule",
                    "source_url": FW_FEES,
                    "verified": True,
                    "amount_requires_schedule": True,
                    "owner": "Electrical estimator",
                },
                {
                    "label": "Stormwater drainage study review (base)",
                    "trade": "CIVIL",
                    "amount_usd": 1406.25,
                    "detail": "Plus per acre over 1 acre — reconfirm effective date",
                    "source_url": FW_STORMWATER,
                    "verified": True,
                    "owner": "Civil / Estimator",
                },
            ],
        },
        "gotcha_watchlist": {
            "items": [
                {
                    "priority": "CRITICAL",
                    "title": "Do not use Dallas/Plano fees for Fort Worth",
                    "detail": "Confirm trade fees on Fort Worth official schedule only",
                    "source_url": FW_PORTAL,
                    "owner": "Estimator",
                    "due_window": "Pre-bid",
                    "anti_patterns": ["Assuming DFW metros share electrical permit fees"],
                },
                {
                    "priority": "HIGH",
                    "title": "Fort Worth rough → service → final sequence",
                    "detail": "Schedule rough MEP before cover; hold final until AHJ checklist closed",
                    "source_url": FW_PORTAL,
                    "owner": "GC / Permit runner",
                    "due_window": "Construction",
                },
            ]
        },
        "punch_list": {
            "timeline_summary": "AHJ intake weeks run parallel to utility interconnect — do not collapse clocks",
            "punch_list": [
                {
                    "priority": "CRITICAL",
                    "task": "Pull live Fort Worth Master Fee Schedule before bid lock",
                    "owner": "Estimator",
                    "due_window": "Week 1",
                    "timeline": "Week 1",
                    "trade": "GENERAL",
                    "estimated_cost": 0,
                    "source_url": FW_FEES,
                    "verified": True,
                    "source_label": "Fort Worth fee schedule PDF",
                },
                {
                    "priority": "CRITICAL",
                    "task": "Flag ERCOT/TDSP large-load interconnect as a parallel clock (not city permit)",
                    "owner": "Owner’s rep / IC",
                    "due_window": "Week 1",
                    "timeline": "Week 1",
                    "trade": "ELECTRICAL",
                    "source_url": FW_PORTAL,
                    "verified": True,
                },
                {
                    "priority": "HIGH",
                    "task": "Confirm Accela application type (electrical vs general building)",
                    "owner": "Permit runner",
                    "due_window": "Week 1",
                    "timeline": "Week 1",
                    "trade": "ELECTRICAL",
                    "source_url": FW_APPLY,
                    "verified": True,
                },
                {
                    "priority": "HIGH",
                    "task": "Price stormwater drainage study review ($1,406.25 base) + acreage adder",
                    "owner": "Civil estimator",
                    "due_window": "Week 2",
                    "timeline": "Week 2",
                    "trade": "CIVIL",
                    "estimated_cost": 1406.25,
                    "source_url": FW_STORMWATER,
                    "verified": True,
                },
                {
                    "priority": "HIGH",
                    "task": "Document plan-review deposit path from new-construction packet ($289 intake)",
                    "owner": "Permit runner",
                    "due_window": "Week 1",
                    "timeline": "Week 1",
                    "trade": "BUILDING",
                    "estimated_cost": 289,
                    "source_url": FW_NEW_CONSTRUCTION_PACKET,
                    "verified": True,
                },
                {
                    "priority": "MEDIUM",
                    "task": "Book rough MEP inspection window after permit issuance",
                    "owner": "GC / Permit runner",
                    "due_window": "Post-permit",
                    "timeline": "Post-permit",
                    "trade": "GENERAL",
                    "source_url": FW_PORTAL,
                    "verified": True,
                },
                {
                    "priority": "MEDIUM",
                    "task": "Confirm water / NPDES track owner for site civil (independent of AHJ date)",
                    "owner": "Civil / Environmental",
                    "due_window": "Pre-bid",
                    "timeline": "Pre-bid",
                    "trade": "CIVIL",
                    "source_url": "",
                    "verified": False,
                },
                {
                    "priority": "MEDIUM",
                    "task": "Capture AHJ contact + plan-review turnaround in the bid file",
                    "owner": "Estimator / PM",
                    "due_window": "Week 1",
                    "timeline": "Week 1",
                    "trade": "GENERAL",
                    "verified": False,
                },
            ],
        },
        "pro_source_urls": [FW_PORTAL, FW_FEES, FW_APPLY, FW_NEW_CONSTRUCTION_PACKET],
        "pro_summary_markdown": (
            "- Confirm Fort Worth Master Fee Schedule before bid\n"
            "- Treat ERCOT/TDSP interconnect as a parallel clock\n"
            "- Use Accela CFW for application type\n"
        ),
        "sample_meta": {
            "labeled_sample": True,
            "site_story": (
                "Fort Worth large-load / data-center-adjacent parcel already screened with "
                "Reg Guard IC Diligence patterns. SAMPLE for buyers — re-run a live address for current cites."
            ),
        },
    }


def analysis_for_tier(tier: str) -> Dict[str, Any]:
    """
    Shape the same site for Free / partner / pro / ic depth badges.
    Content richness is tiered for honesty in the sample ladder.
    """
    base = build_sample_dc_analysis()
    t = (tier or "ic").strip().lower()
    out = deepcopy(base)
    if t in ("free", "free_preview"):
        out["depth_tier"] = "free"
        out["research_depth"] = "free"
        out["ic_package"] = False
        out["depth_badge"] = "Free preview (SAMPLE)"
        # Soft-lock honesty: free shows structure; full punch lives behind forward / paid
        punch = (out.get("punch_list") or {}).get("punch_list") or []
        out["punch_list"] = {
            **(out.get("punch_list") or {}),
            "punch_list": punch[:5],
            "soft_locked": True,
            "soft_lock_note": "SAMPLE Free preview — top 5 punch lines; forward or upgrade unlocks the rest on a live run.",
        }
    elif t in ("partner", "estimator", "permit_runner"):
        out["depth_tier"] = "pro_light"
        out["research_depth"] = "partner"
        out["ic_package"] = False
        out["depth_badge"] = "Estimator / Permit Runner (SAMPLE)"
    elif t in ("pro", "contractor_pro", "contractor"):
        out["depth_tier"] = "pro_local"
        out["research_depth"] = "pro"
        out["ic_package"] = False
        out["depth_badge"] = "Contractor Pro (SAMPLE)"
    else:
        out["depth_tier"] = "ic_full"
        out["research_depth"] = "ic"
        out["ic_package"] = True
        out["depth_badge"] = "IC PROJECT (SAMPLE)"
    return out
