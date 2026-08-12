"""
Free Trial API Endpoint: /free-trial
Allows users to run RegGuard research for free and receive research memo via email
Includes environmental screening via Firecrawl + Gemini
"""

import asyncio
import logging
import traceback
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class FreeTrialRequest(BaseModel):
    """Request body for free trial"""
    address: str
    project_type: str
    email: str
    zip: Optional[str] = None
    phone: Optional[str] = None
    # Explicit opt-in: consume IC Project Report slot for this address
    generate_ic_report: Optional[bool] = False


class FreeTrialResponse(BaseModel):
    """Response for free trial request"""
    trial_id: str
    message: str
    status: str
    analysis_data: Optional[Dict[str, Any]] = None  # NEW: Immediate analysis results


async def handle_free_trial(request_data: FreeTrialRequest) -> FreeTrialResponse:
    """
    Handle free trial request:
    1. Create trial record in Supabase
    2. Run research asynchronously
    3. Send research memo via email
    4. Return trial_id for tracking
    """
    from free_trial_service import create_free_trial, mark_memo_sent
    from email_service import get_email_service

    try:
        # Step 1: Create trial record
        trial = create_free_trial(
            email=request_data.email,
            address=request_data.address,
            project_type=request_data.project_type,
        )

        if not trial:
            logger.error("Failed to create free trial record")
            return FreeTrialResponse(
                trial_id="",
                message="Failed to create trial record. Please try again.",
                status="error",
            )

        logger.info(f"Created free trial: {trial.id} for {request_data.email}")

        # Step 2: Run research asynchronously in background
        asyncio.create_task(
            _run_research_and_email(
                trial_id=trial.id,
                email=request_data.email,
                address=request_data.address,
                project_type=request_data.project_type,
            )
        )

        return FreeTrialResponse(
            trial_id=trial.id,
            message="Your research has been queued. Check your email in 24 hours for your research memo.",
            status="success",
        )

    except Exception as e:
        logger.error(f"Error handling free trial: {e}")
        return FreeTrialResponse(
            trial_id="",
            message="An error occurred. Please try again.",
            status="error",
        )


async def _run_research_and_email(
    trial_id: str,
    email: str,
    address: str,
    project_type: str,
) -> None:
    """
    Background task: Run research (including environmental screening) and send email.
    This runs asynchronously after the endpoint returns.
    """
    from free_trial_service import mark_memo_sent
    from email_service import get_email_service
    import traceback

    try:
        logger.info(f"🟢 Starting research for trial {trial_id}: {address}")

        # COGS control: free background email is a light tip memo by default.
        # Full digest + Option A already ran (or will run) on the /free-trial
        # response path for the in-app UI — do not pay for them twice.
        import os

        heavy = (os.getenv("FREE_TRIAL_HEAVY_EMAIL") or "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
        if heavy:
            research_memo = await _generate_research_memo(
                address=address,
                project_type=project_type,
            )
            if not research_memo:
                logger.error(f"❌ Failed to generate research memo for trial {trial_id}")
                return
            try:
                environmental_screening = await _run_environmental_screening(
                    address, project_type
                )
            except Exception as env_error:
                logger.error(f"⚠️  Environmental screening failed (non-critical): {env_error}")
                environmental_screening = None
            combined_memo = _combine_memo_with_environmental(
                research_memo, environmental_screening
            )
        else:
            app_url = (
                os.getenv("FRONTEND_APP_URL") or "https://app.regguardagent.com"
            ).rstrip("/")
            combined_memo = (
                f"FREE PRE-BID PREVIEW — {address}\n"
                f"{'─' * 48}\n\n"
                f"Your site lookup for {project_type or 'general'} is ready in the app.\n"
                f"Open: {app_url}/?email={email}\n\n"
            )
            pt = (project_type or "").strip().lower().replace("_", "-")
            if pt in ("data-center", "datacenter", "dc", "colocation"):
                combined_memo += (
                    "Data center / large-load tip:\n"
                    "- Forward the Bid Risk Receipt — it flags AHJ + utility parallel-track risk.\n"
                    "- Planning exposure on killers is heuristic only (not guaranteed savings).\n"
                    "- Reg Guard does not run interconnection studies or file AHJ applications.\n"
                    "- Strongest citeable coverage: Dallas / Plano / Austin TX.\n"
                    "- IC Project Report ($1,500) is the high-touch diligence package for colo sites.\n\n"
                )
            else:
                combined_memo += (
                    "Tips for DFW / Austin bids:\n"
                    "- Forward the Bid Risk Receipt (contingency + top killers) — that's the share object.\n"
                    "- Planning exposure on killers is heuristic only — not guaranteed savings.\n"
                    "- Every punch line shows a Source link or Unverified — forward only what you can defend.\n"
                    "- Share the receipt to unlock the full free preview.\n"
                    "- Save the job, then re-check before you bid (Saved Jobs → weekly reminder).\n"
                    "- Partner $79/mo or Contractor Pro $149/mo unlocks deeper Universal Scout.\n"
                    "- IC Project Report ($1,500) adds memo + punch + permit worksheet PDFs "
                    "(planning diligence — not an official AHJ filing).\n\n"
                    "Strongest citeable coverage today: Dallas / Plano / Austin TX.\n"
                )
            logger.info(
                "Free trial light email (set FREE_TRIAL_HEAVY_EMAIL=1 for full digest path)"
            )

        email_service = get_email_service()
        if not email_service:
            logger.error("❌ Email service not configured")
            return

        logger.info(f"📧 Sending research memo to {email} (memo size: {len(combined_memo)} chars)...")
        success = await email_service.send_research_memo(
            to_email=email,
            address=address,
            research_memo=combined_memo,
            trial_id=trial_id,
        )

        if success:
            # Step 4: Mark memo as sent in database
            logger.info(f"💾 Marking memo as sent in database...")
            mark_memo_sent(trial_id)
            logger.info(f"✅ Successfully sent research memo to {email} for trial {trial_id}")
        else:
            logger.error(f"❌ Failed to send research memo to {email}")

    except Exception as e:
        logger.error(f"❌ Error in research/email background task: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")


async def _generate_research_memo(
    address: str,
    project_type: str,
) -> Optional[str]:
    """
    Generate research memo for free trial.
    Returns plaintext memo (PDF generation is premium feature).
    """
    try:
        # Import research functions from existing backend
        from research_memo import build_research_digest
        from jurisdiction import geocode_profile_from_address
        import traceback

        logger.info(f"🔵 Generating research memo for: {address} ({project_type})")

        # Geocode address to get jurisdiction profile
        profile = geocode_profile_from_address(address)

        if not profile:
            logger.warning(f"⚠️  Could not geocode address: {address}")
            return "Could not geocode address. Please verify the address and try again."

        logger.info(f"✅ Geocoded: {profile.city}, {profile.state_short} (ZIP: {profile.zip5})")

        # Build research digest (this calls all the research modules)
        # profile is a JurisdictionProfile dataclass - convert to dict for compatibility
        profile_dict = {
            "jurisdiction": {
                "state": profile.state_short,
                "state_long": profile.state_long,
                "city": profile.city,
                "county": profile.county,
            },
            "scout_profile": {"vertical": "data-center"},  # Default for free tier
        }
        
        logger.info(f"📋 Calling build_research_digest with profile: {profile.city}, {profile.state_short}")
        
        digest = build_research_digest(
            raw=profile_dict,
            source_urls=[],
            enhanced_query=f"Free trial research for {project_type} at {address}",
            job_description=f"Free trial research for {address}",
        )

        if not digest:
            logger.error(f"❌ build_research_digest returned None")
            return "Could not generate research. Please try again."

        logger.info(f"✅ Research digest generated ({len(str(digest))} chars)")

        # Extract plaintext from digest (strip HTML/markdown if needed)
        memo = _format_memo_plaintext(digest, address, project_type)

        logger.info(f"✅ Formatted memo completed ({len(memo)} chars)")
        return memo

    except Exception as e:
        logger.error(f"❌ Error generating research memo: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None


def _format_memo_plaintext(
    research_digest: str,
    address: str,
    project_type: str,
) -> str:
    """Format research digest into clean, actionable plaintext memo"""
    import json
    
    # Parse the JSON digest
    try:
        digest_data = json.loads(research_digest) if isinstance(research_digest, str) else research_digest
    except (json.JSONDecodeError, TypeError):
        digest_data = {}
    
    # Extract jurisdiction info
    jurisdiction = digest_data.get("jurisdiction", {})
    city = jurisdiction.get("city", "Unknown")
    state = jurisdiction.get("state", "Unknown")
    county = jurisdiction.get("county", "Unknown")
    
    # Build clean memo
    memo = f"""SITE DILIGENCE RESEARCH MEMO
{'=' * 60}

PROJECT LOCATION
{address}
{city}, {state}

PRELIMINARY FINDINGS
{'─' * 60}

"""
    
    # Add jurisdiction-specific costs and requirements
    if city.lower() == "plano":
        memo += f"""PERMIT INFORMATION (Plano, TX)
• Electrical Permit Cost: $75.00 total ($65 base + $10 laborer)
• Key Regulation: Plano Ordinance 250.50 (Grounding Requirements)
  - Must use two 8-foot grounding rods
  - Spaced 20 feet apart
  - Connected by 2/0 AWG conductor

"""
    
    # Add research recommendations
    targets = digest_data.get("universal_expert_scout_targets", {})
    if targets:
        memo += """RECOMMENDED NEXT STEPS
To prepare for your permit application:
"""
        for key, target in targets.items():
            memo += f"• {target}\n"
        memo += "\n"
    
    # Add scout results if any
    scout_steps = digest_data.get("scout_steps", [])
    if scout_steps and any(step.get("hits") for step in scout_steps):
        memo += "RESOURCES FOUND\n"
        for step in scout_steps:
            if step.get("hits"):
                hits = step.get("hits", [])
                memo += f"• {step.get('query')}: {len(hits)} source(s) found\n"
        memo += "\n"
    
    # Add environmental note
    memo += """ENVIRONMENTAL ASSESSMENT
This preliminary scan covers regulatory and permitting research.
A full environmental assessment (premium feature) includes:
• Wetlands analysis
• Endangered species check
• Flood zone mapping
• Noise zone review
• State-specific requirements

"""
    
    # Call to action
    memo += """NEXT STEP: UPGRADE TO FULL REPORT ($15,000)
────────────────────────────────────────────────────────────

The premium report includes:
✓ Complete permit package (ready to file)
✓ Actionable punch list (what to do now)
✓ Full environmental assessment
✓ Same-day delivery via PDF

This memo gives you research direction. The full report saves you
weeks of work and helps avoid costly mistakes.

Ready? Upgrade now to get your complete analysis.
"""
    
    return memo.strip()


async def _run_environmental_screening(address: str, project_type: str) -> Optional[dict]:
    """
    Option A MVP: Run real environmental screening + punch list generation
    Integrates real Firecrawl API for actual data (replaces template/cached data)
    Returns comprehensive environmental + punch list analysis for display/email
    """
    import traceback
    try:
        from jurisdiction import geocode_profile_from_address
        from option_a_integration import run_option_a_analysis
        import os

        logger.info(f"🌍 Option A: Starting real environmental screening for: {address}")
        
        # Geocode to get lat/lon
        profile = geocode_profile_from_address(address)

        if not profile:
            logger.warning(f"❌ Could not geocode {address}")
            return None

        logger.info(f"📍 Geocoded: {profile.city}, {profile.state_short} ZIP: {profile.zip5}")

        # Run Option A analysis (real environmental screening + punch list)
        analysis = await run_option_a_analysis(
            address=address,
            city=profile.city,
            state=profile.state_short,
            zip_code=profile.zip5,
            latitude=profile.latitude,
            longitude=profile.longitude,
            project_type=project_type,
            utilities_involved=[],  # Would be populated in premium tier
        )
        
        logger.info(f"✅ Option A analysis complete: {analysis['summary']['total_environmental_risks']} risks found")
        return analysis

    except Exception as e:
        logger.error(f"❌ Option A analysis failed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None


def _combine_memo_with_environmental(research_memo: str, analysis_data: Optional[dict]) -> str:
    """
    Option A MVP: Combine research memo with Option A analysis results
    Formats environmental + punch list for email delivery
    """
    if not analysis_data or analysis_data.get("error"):
        return research_memo

    try:
        from option_a_integration import format_analysis_for_email
        
        logger.info(f"📧 Formatting Option A analysis for email")
        # Format the full analysis for email
        formatted_email = format_analysis_for_email(analysis_data)
        
        return formatted_email

    except Exception as e:
        logger.error(f"❌ Failed to format analysis for email: {e}")
        return research_memo
        
        # If no actual data, don't append environmental section
        if not has_data:
            return research_memo
        
        # If we do have data, format it nicely
        findings_text = "\n".join(env_findings) if env_findings else "No specific constraints identified"

        environmental_section = f"""

ENVIRONMENTAL ASSESSMENT
{'─' * 60}

Risk Level: {risk_level}

Key Findings:
{findings_text}

Note: This is a preliminary scan. The full premium report includes
comprehensive analysis of wetlands, endangered species, flood zones,
noise restrictions, NEPA compliance, and state requirements.
"""
        return research_memo + environmental_section

    except Exception as e:
        logger.error(f"❌ Error combining memo with environmental data: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return research_memo
