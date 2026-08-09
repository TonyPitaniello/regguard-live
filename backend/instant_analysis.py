"""
Instant analysis fallback for free-trial when deep screening is unavailable.
Always returns a ResultsViewerModal-compatible payload so the UI can open immediately.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import re

from honesty import apply_honesty_layer


def _parse_address(address: str, zip_hint: str = "") -> Dict[str, str]:
    city, state, zip_code = "Unknown", "US", zip_hint or ""
    parts = [p.strip() for p in address.split(",") if p.strip()]
    if len(parts) >= 3:
        city = parts[-2] if len(parts) >= 2 else city
        state_zip = parts[-1]
        m = re.match(r"([A-Za-z]{2})\s*(\d{5})?", state_zip)
        if m:
            state = m.group(1).upper()
            if m.group(2):
                zip_code = m.group(2)
        else:
            # "Dallas TX 75074" style in last segment
            tokens = state_zip.split()
            for t in tokens:
                if re.fullmatch(r"[A-Za-z]{2}", t):
                    state = t.upper()
                elif re.fullmatch(r"\d{5}", t):
                    zip_code = t
            if len(parts) >= 2:
                city = parts[-2]
    elif zip_hint:
        zip_code = zip_hint
    if not zip_code:
        m = re.search(r"\b(\d{5})\b", address)
        if m:
            zip_code = m.group(1)
    return {"city": city, "state": state, "zip": zip_code or "00000"}


def build_instant_fallback_analysis(
    address: str,
    project_type: str = "data-center",
    zip_code: str = "",
    city: Optional[str] = None,
    state: Optional[str] = None,
    latitude: float = 0.0,
    longitude: float = 0.0,
) -> Dict[str, Any]:
    """Deterministic analysis payload — never raises."""
    parsed = _parse_address(address, zip_code)
    city = city or parsed["city"]
    state = state or parsed["state"]
    zip_code = zip_code or parsed["zip"]

    findings = [
        {
            "category": "electrical_interconnection",
            "risk_level": "MEDIUM",
            "description": (
                f"Preliminary scan for {city}, {state} {zip_code}: confirm utility "
                f"interconnection queue rules and AHJ electrical permit path for {project_type}."
            ),
            "action_items": [
                "Identify serving utility and interconnection application portal",
                "Confirm NEC / local amendments for DER or load interconnection",
                "Request preliminary load / generation study timeline from utility",
            ],
            "data_sources": ["RegGuard Instant Preview", "Jurisdiction heuristics"],
            "research_cost_usd": 0,
        },
        {
            "category": "permitting",
            "risk_level": "MEDIUM",
            "description": (
                f"Local permitting for {project_type} typically requires building/electrical "
                "permits plus utility coordination. Verify zoning and any temporary moratoriums."
            ),
            "action_items": [
                "Call AHJ planning desk with parcel/address",
                "Confirm required permit package documents",
                "Check floodplain / environmental overlays for the parcel",
            ],
            "data_sources": ["RegGuard Instant Preview"],
            "research_cost_usd": 0,
        },
        {
            "category": "timeline_cost",
            "risk_level": "LOW",
            "description": (
                "Instant preview estimates only. Full Firecrawl + AI diligence may refine "
                "timeline and cost once deep research completes."
            ),
            "action_items": [
                "Budget 30–180 days depending on utility study track",
                "Upgrade to IC Project Report for same-day PDF package",
            ],
            "data_sources": ["RegGuard Instant Preview"],
            "research_cost_usd": 0,
        },
    ]

    punch_items = [
        {
            "priority": "HIGH",
            "task": f"Confirm AHJ contact and permit intake for {city}, {state}",
            "responsible_party": "Project owner / permitting lead",
            "timeline": "Week 1",
            "estimated_cost": 500,
            "cost_verified": False,
            "notes": "Instant preview — deepen with full research package",
            "verified": False,
            "cost_verified": False,
            "source_label": "Instant preview",
        },
        {
            "priority": "HIGH",
            "task": "Identify utility interconnection application + queue position",
            "responsible_party": "Electrical / IC consultant",
            "timeline": "Week 1–2",
            "estimated_cost": 1500,
            "cost_verified": False,
            "notes": f"Project type: {project_type}",
            "verified": False,
            "cost_verified": False,
            "source_label": "Instant preview",
        },
        {
            "priority": "MEDIUM",
            "task": "Assemble site plan, one-line diagram, and load/generation summary",
            "responsible_party": "Design engineer",
            "timeline": "Week 2–4",
            "estimated_cost": 5000,
            "cost_verified": False,
            "notes": "Required for most utility + AHJ packages",
            "verified": False,
            "cost_verified": False,
            "source_label": "Instant preview",
        },
        {
            "priority": "MEDIUM",
            "task": "Screen environmental overlays (flood, wetlands, species)",
            "responsible_party": "Environmental consultant",
            "timeline": "Week 2–6",
            "estimated_cost": 3000,
            "cost_verified": False,
            "notes": "Upgrade for full screening detail",
            "verified": False,
            "cost_verified": False,
            "source_label": "Instant preview",
        },
    ]

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "preview": True,
        "project_info": {
            "address": address,
            "city": city,
            "state": state,
            "zip": zip_code,
            "type": project_type,
            "coordinates": {"latitude": latitude, "longitude": longitude},
        },
        "environmental_screening": {
            "risk_level": "UNAVAILABLE",
            "findings": findings,
            "total_research_cost": 0,
            "action_plan": [a for f in findings for a in f["action_items"][:1]],
        },
        "punch_list": {
            "punch_list": punch_items,
            "timeline_summary": "30–120 days (instant estimate)",
            "estimated_total_cost": sum(i.get("estimated_cost", 0) for i in punch_items),
            "estimates_unverified": True,
            "critical_path": [
                {
                    "task": i["task"],
                    "verified": False,
                    "cost_verified": False,
                    "source_label": "Instant preview",
                    "estimated_cost": i.get("estimated_cost"),
                }
                for i in punch_items
                if i["priority"] == "HIGH"
            ],
            "estimates_verified": False,
            "milestones": [
                {"week": "1", "milestone": "AHJ + utility contacts confirmed"},
                {"week": "4", "milestone": "Application package drafted"},
                {"week": "8–16", "milestone": "Studies / permits in progress"},
            ],
            "who_to_call": {
                "AHJ": f"{city} building/permitting department",
                "Utility": "Serving electric utility interconnection desk",
            },
        },
        "summary": {
            "total_environmental_risks": len(findings),
            "high_risk_count": 0,
            "total_punch_list_items": len(punch_items),
            "estimated_timeline": "30–120 days (instant estimate)",
            "estimated_total_cost": sum(i.get("estimated_cost", 0) for i in punch_items),
            "estimates_unverified": True,
        },
        "next_steps": [
            "Review the findings in this window (preview — not verified parcel risk)",
            "Text or email yourself a copy from the form below",
            "Upgrade to Contractor Pro ($149/mo) or IC Project Report ($1,500) for full PDF package",
        ],
    }
    stamped = apply_honesty_layer(
        payload,
        source="instant",
        risk_verified=False,
        cost_verified=False,
        timeline_verified=False,
    )
    try:
        from ahj_catalog import enrich_analysis_with_ahj

        stamped = enrich_analysis_with_ahj(
            stamped,
            city=city,
            state=state,
            zip_code=zip_code,
        )
    except Exception:
        pass
    return stamped
