"""
Option A MVP Integration: Real Environmental Screening + Punch List Generation
Integrates real_environmental_screening.py and punch_list_generator.py
into the free trial pipeline
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


async def run_option_a_analysis(
    address: str,
    city: str,
    state: str,
    zip_code: str,
    latitude: float,
    longitude: float,
    project_type: str = "data-center",
    utilities_involved: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Run Option A MVP Analysis:
    1. Real environmental screening
    2. AI punch list generation
    3. Combined results for display/email
    
    Returns comprehensive analysis that can be:
    - Displayed on results page
    - Sent via email
    - Eventually converted to PDF (Option B)
    """
    
    logger.info(f"🚀 Option A MVP Analysis: {project_type} in {city}, {state}")
    
    try:
        from geocode import is_null_island

        # Step 1: Run real environmental screening (skip parcel GIS on Null Island)
        from real_environmental_screening import get_environmental_screening_engine

        env_engine = get_environmental_screening_engine()
        if is_null_island(latitude, longitude):
            logger.warning(
                "Null Island / missing coords — skipping parcel GIS env queries for %s",
                address,
            )
            environmental_data = {
                "risk_level": "UNAVAILABLE",
                "findings": [],
                "total_research_cost": 0,
                "action_plan": [
                    "Address did not resolve to map coordinates — re-select the site from Places autocomplete before treating environmental findings as parcel-specific."
                ],
                "risk_score_hidden": True,
                "risk_honesty_note": (
                    "Environmental parcel checks skipped — coordinates missing or (0,0). "
                    "Federal/state checklist still applies."
                ),
            }
        else:
            environmental_data = await env_engine.screen_site(
                address=address,
                latitude=latitude,
                longitude=longitude,
                city=city,
                state=state,
                zip_code=zip_code,
            )
        
        logger.info(f"✅ Environmental screening complete")
        
        # Step 2: Generate AI-driven punch list
        from punch_list_generator import get_punch_list_generator
        
        punch_generator = get_punch_list_generator()
        punch_list_data = punch_generator.generate_punch_list(
            project_type=project_type,
            location=f"{city}, {state}",
            environmental_risks=environmental_data,
            utilities_involved=utilities_involved or [],
        )
        
        logger.info(f"✅ Punch list generated with {len(punch_list_data['punch_list'])} items")

        # Option A: risk verified when pin is real and flood/wetlands GIS returned verified hits.
        from honesty import apply_honesty_layer
        from geocode import is_null_island

        findings = environmental_data.get("findings") or []
        gis_cats = {
            "wetlands",
            "flood",
            "floodplain",
            "flood_zone",
            "flood_zones",
            "flood zones",
        }
        verified_gis = [
            f
            for f in findings
            if isinstance(f, dict)
            and f.get("verified") is True
            and str(f.get("category") or "").strip().lower() in gis_cats
        ]
        pin_ok = not is_null_island(latitude, longitude)
        risk_verified = bool(pin_ok and verified_gis)
        # Never leave PRELIMINARY overall when GIS parcel checks succeeded
        if risk_verified and str(environmental_data.get("risk_level") or "").upper() in (
            "PRELIMINARY",
            "UNAVAILABLE",
            "",
        ):
            levels = [str(f.get("risk_level") or "LOW").upper() for f in verified_gis]
            rank = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4, "UNKNOWN": 0}
            best = max((rank.get(lv, 0) for lv in levels), default=1)
            inv = {v: k for k, v in rank.items() if k != "UNKNOWN"}
            environmental_data["risk_level"] = inv.get(best, "LOW")
            environmental_data["risk_gis_verified"] = True

        combined_analysis = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "preview": True,
            "project_info": {
                "address": address,
                "city": city,
                "state": state,
                "zip": zip_code,
                "type": project_type,
                "coordinates": {"latitude": latitude, "longitude": longitude},
            },
            "environmental_screening": environmental_data,
            "punch_list": punch_list_data,
            "summary": {
                "total_environmental_risks": len(environmental_data.get("findings") or []),
                "high_risk_count": sum(
                    1
                    for f in (environmental_data.get("findings") or [])
                    if f.get("risk_level") in ["HIGH", "CRITICAL"]
                ),
                "total_punch_list_items": len(punch_list_data["punch_list"]),
                "estimated_timeline": punch_list_data["timeline_summary"],
                "estimated_total_cost": punch_list_data["estimated_total_cost"],
                "estimates_unverified": True,
            },
            "next_steps": [
                "1. Treat this as a preliminary checklist — risk scores are not parcel-verified"
                if not risk_verified
                else "1. Review GIS-verified flood/wetlands findings against your site plan",
                "2. Contact your local Authority Having Jurisdiction (AHJ) with your punch list",
                "3. Confirm every dollar and day estimate with the AHJ / utility before bidding",
                "4. Forward the Bid Risk Receipt before bid day — or open My Orders for IC PDFs if purchased",
            ],
        }

        stamped = apply_honesty_layer(
            combined_analysis,
            source="option_a",
            risk_verified=risk_verified,
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
        except Exception as ahj_err:
            logger.warning(f"AHJ enrich skipped: {ahj_err}")
        logger.info("✅ Option A analysis complete (honesty layer + AHJ catalog)")
        return stamped
        
    except Exception as e:
        logger.error(f"❌ Option A analysis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise


def format_analysis_for_email(analysis: Dict[str, Any]) -> str:
    """
    Format Option A analysis for email delivery
    Creates readable plaintext that can be sent immediately
    """
    
    lines = [
        "=" * 70,
        "REGGUARD FREE TRIAL - SITE DILIGENCE ANALYSIS",
        "=" * 70,
        "",
        f"Project Location: {analysis['project_info']['address']}",
        f"City: {analysis['project_info']['city']}, {analysis['project_info']['state']} {analysis['project_info']['zip']}",
        f"Project Type: {analysis['project_info']['type']}",
        f"Analysis Date: {analysis['timestamp']}",
        "",
    ]

    honesty = analysis.get("honesty") or {}
    if honesty or analysis.get("preview"):
        lines.extend(
            [
                "⚠ HONESTY NOTICE",
                honesty.get("labels", {}).get(
                    "risk",
                    "Environmental risk scores are unverified preview data — not for bidding.",
                ),
                honesty.get("labels", {}).get(
                    "cost",
                    "Cost and timeline figures are unverified estimates — confirm with AHJ.",
                ),
                "",
            ]
        )

    lines.extend(
        [
        "-" * 70,
        "ENVIRONMENTAL SCREENING SUMMARY",
        "-" * 70,
        ]
    )

    risk_level = analysis["environmental_screening"].get("risk_level", "UNAVAILABLE")
    if str(risk_level).upper() in ("UNAVAILABLE", "PRELIMINARY", "UNKNOWN") or not honesty.get(
        "risk_verified"
    ):
        lines.append("Overall Risk Level: UNAVAILABLE (not verified — do not use for bidding)")
    else:
        lines.append(f"Overall Risk Level: {risk_level}")

    lines.extend(
        [
        f"Total Issues Found: {analysis['summary']['total_environmental_risks']}",
        f"High/Critical Risk Count: {analysis['summary'].get('high_risk_count', 0)}",
        "",
        ]
    )
    
    # Add environmental findings
    for finding in analysis['environmental_screening']['findings']:
        lines.extend([
            f"📌 {finding['category'].upper()}",
            f"   Risk Level: {finding['risk_level']}",
            f"   Description: {finding['description']}",
            f"   Research Cost: ${finding['research_cost_usd']}",
            "",
        ])
    
    # Add punch list summary
    lines.extend([
        "-" * 70,
        "YOUR ACTION PLAN (PUNCH LIST)",
        "-" * 70,
        f"Total Action Items: {analysis['summary']['total_punch_list_items']}",
        f"Estimated Timeline: {analysis['summary']['estimated_timeline']} "
        f"{'(unverified)' if not (analysis.get('honesty') or {}).get('timeline_verified') else ''}",
        f"Estimated Total Cost: ${analysis['summary']['estimated_total_cost']:,.0f} "
        f"{'(unverified — not an AHJ quote)' if not (analysis.get('honesty') or {}).get('cost_verified') else ''}",
        "",
        "TOP PRIORITY ITEMS:",
        "",
    ])
    
    # Add top 5 critical path items (string or {task, verified, source_url})
    for i, task in enumerate(analysis['punch_list']['critical_path'][:5], 1):
        if isinstance(task, dict):
            label = task.get("task") or ""
            cite = " [sourced]" if task.get("verified") and task.get("source_url") else " [unverified]"
            lines.append(f"{i}. {label}{cite}")
        else:
            lines.append(f"{i}. {task} [unverified]")
    
    lines.extend([
        "",
        "FULL PUNCH LIST:",
        "See attached PDF or log into your account for complete details.",
        "",
        "-" * 70,
        "NEXT STEPS",
        "-" * 70,
    ])
    
    for step in analysis['next_steps']:
        lines.append(step)
    
    lines.extend([
        "",
        "NEXT STEPS IN THE PRODUCT",
        "• Open https://app.regguardagent.com/ for the shareable /r/ report",
        "• Contractor Pro: $149/mo for ongoing citeable pre-bid punch lists",
        "• IC Project Report: $1,500 one-time full packaged diligence",
        "• Do not treat free-trial env scores as parcel-verified GIS",
        "",
        "=" * 70,
        f"Generated by RegGuard {datetime.utcnow().strftime('%Y-%m-%d')}",
        "=" * 70,
    ])

    return "\n".join(lines)


def format_analysis_for_html(analysis: Dict[str, Any]) -> str:
    """
    Format Option A analysis for HTML display on results page
    """
    
    html = f"""
    <div class="analysis-results">
        <header class="results-header">
            <h1>Site Diligence Analysis Complete</h1>
            <p class="subtitle">{analysis['project_info']['address']}</p>
        </header>
        
        <section class="risk-summary">
            <h2>Environmental Risk Summary</h2>
            <div class="risk-level {analysis['environmental_screening']['risk_level'].lower()}">
                <strong>Overall Risk: {analysis['environmental_screening']['risk_level']}</strong>
            </div>
            <p>Found {analysis['summary']['high_risk_count']} high/critical risk items requiring immediate attention</p>
        </section>
        
        <section class="environmental-findings">
            <h2>Environmental Findings</h2>
            <div class="findings-list">
    """
    
    for finding in analysis['environmental_screening']['findings']:
        html += f"""
                <div class="finding-item {finding['risk_level'].lower()}">
                    <h3>{finding['category'].title()}</h3>
                    <p class="risk-badge">{finding['risk_level']} Risk</p>
                    <p class="description">{finding['description']}</p>
                    <div class="action-items">
                        <strong>Action Items:</strong>
                        <ul>
        """
        for action in finding['action_items']:
            html += f"<li>{action}</li>"
        
        html += f"""
                        </ul>
                    </div>
                    <p class="research-cost">Research Cost: ${finding['research_cost_usd']}</p>
                </div>
        """
    
    html += """
            </div>
        </section>
        
        <section class="punch-list-preview">
            <h2>Your Action Plan</h2>
            <p>Total Action Items: {count}</p>
            <p>Estimated Timeline: {timeline}</p>
            <p>Estimated Cost: ${cost:,.0f}</p>
            <div class="critical-path">
                <h3>Critical Path (Top Priority):</h3>
                <ol>
    """.format(
        count=analysis['summary']['total_punch_list_items'],
        timeline=analysis['summary']['estimated_timeline'],
        cost=analysis['summary']['estimated_total_cost'],
    )
    
    for task in analysis['punch_list']['critical_path'][:5]:
        if isinstance(task, dict):
            label = task.get("task") or ""
            if task.get("verified") and task.get("source_url"):
                html += (
                    f'<li>{label} '
                    f'<a href="{task["source_url"]}" target="_blank" rel="noopener noreferrer">source</a></li>'
                )
            else:
                html += f"<li>{label} <em>(unverified)</em></li>"
        else:
            html += f"<li>{task} <em>(unverified)</em></li>"
    
    html += """
                </ol>
            </div>
        </section>
        
        <section class="upgrade-cta">
            <h2>Keep going</h2>
            <p>This free lookup is a citeable starting punch list — not a parcel-verified risk score.</p>
            <p><strong>Contractor Pro ($149/mo)</strong> for ongoing pre-bid punch lists.
            <strong>IC Project Report ($1,500)</strong> for a full packaged diligence report.</p>
            <a class="upgrade-button" href="https://app.regguardagent.com/pricing">View pricing</a>
        </section>
    </div>
    """

    return html


# Placeholder for integration into free_trial_handler.py
def integrate_option_a_into_free_trial():
    """
    Integration instructions:
    
    1. In free_trial_handler.py, replace _run_environmental_screening with:
    
    async def _run_environmental_screening(address, project_type):
        from option_a_integration import run_option_a_analysis
        from jurisdiction import geocode_profile_from_address
        
        profile = geocode_profile_from_address(address)
        if not profile:
            return None
            
        analysis = await run_option_a_analysis(
            address=address,
            city=profile.city,
            state=profile.state_short,
            zip_code=profile.zip5,
            latitude=profile.latitude,
            longitude=profile.longitude,
            project_type=project_type,
        )
        return analysis
    
    2. In free_trial_handler.py, update _combine_memo_with_environmental to format 
       the analysis for email using format_analysis_for_email()
    
    3. Create new /results endpoint to display analysis:
    
    @app.post("/results")
    async def display_results(analysis_data: dict):
        html = format_analysis_for_html(analysis_data)
        return {"html": html}
    
    4. Frontend: After free trial submission, display results using
       format_analysis_for_html() output
    """
    pass
