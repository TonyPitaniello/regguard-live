"""
RegGuard Queue API endpoints - Phase 0 & Phase 1 features.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, UploadFile, File
from pydantic import BaseModel
import base64
import json
import os
import logging

from interconnect.auto_filler import auto_fill_form
from interconnect.pdf_generator import InterconnectionFormPDF
from interconnect.queue_monitor import create_queue_monitor
from interconnect.study_translator import create_study_translator
from interconnect.timeline_predictor import create_timeline_predictor
from interconnect.compliance_checker import create_compliance_checker

logger = logging.getLogger(__name__)


def _require_ic_demo_enabled() -> None:
    """IC queue endpoints are demo stubs — off in prod unless REG_GUARD_IC_DEMO=1."""
    from honesty import is_ic_demo_enabled

    if not is_ic_demo_enabled():
        raise HTTPException(
            status_code=403,
            detail=(
                "IC Queue demo is disabled in production. "
                "Set REG_GUARD_IC_DEMO=1 only for intentional demo environments. "
                "These endpoints return synthetic queue data, not live RTO filings."
            ),
        )


class FERCAutoFillRequest(BaseModel):
    form_type: str
    project_text: str
    user_email: Optional[str] = None
    user_overrides: Optional[Dict[str, str]] = None

class FERCAutoFillResponse(BaseModel):
    submission_id: str
    form_type: str
    filled_form: Dict[str, Any]
    accuracy_report: Dict[str, Any]
    pdf_url: Optional[str] = None
    pdf_format: str
    ferc_compliant: bool
    filing_instructions: str
    ready_for_export: bool
    created_at: str

router = APIRouter(prefix="/queue", tags=["Queue"])

@router.post("/auto-fill", response_model=FERCAutoFillResponse)
async def auto_fill_ferc_form(
    req: FERCAutoFillRequest,
    request: Request,
) -> FERCAutoFillResponse:
    """Draft fields only. Does not invent an applicant, a megawatt, or a queue position."""
    raise HTTPException(
        status_code=422,
        detail=(
            "No field is filled from this desk. "
            "A queue position is printed only when the official queue file states that id. "
            "File on the RTO portal."
        ),
    )

@router.get("/history")
async def get_user_submissions(request: Request, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
    _require_ic_demo_enabled()
    return {"submissions": [], "total": 0, "limit": limit, "offset": offset, "demo": True}

@router.get("/status/{submission_id}")
async def get_submission_status(submission_id: str, request: Request) -> Dict[str, Any]:
    _require_ic_demo_enabled()
    return {
        "submission_id": submission_id,
        "status": "draft",
        "created_at": datetime.now().isoformat(),
        "demo": True,
    }

@router.get("/stats")
async def get_queue_stats(request: Request) -> Dict[str, Any]:
    _require_ic_demo_enabled()
    return {
        "total_submissions": 0,
        "successful_fills": 0,
        "average_accuracy": 0.0,
        "forms_pending_submission": 0,
        "demo": True,
    }

# ─── Phase 0.1: Queue Monitoring ───────────────────────────────────────────

class QueueMonitorRequest(BaseModel):
    rto: str
    queue_id: str
    project_name: str

class QueueMonitorResponse(BaseModel):
    tracking_id: str
    project_name: str
    rto: str
    current_phase: str
    queue_position: Optional[int] = None
    source_url: str = ""
    alerts: list

@router.post("/monitor-queue", response_model=QueueMonitorResponse)
async def monitor_queue(req: QueueMonitorRequest, request: Request) -> QueueMonitorResponse:
    """Look up an id on the official queue page. No ordinal position is invented."""
    from interconnect.official_queue import cited_queue_lookup

    row = cited_queue_lookup(req.rto, req.queue_id)
    return QueueMonitorResponse(
        tracking_id=f"{row['rto']}_{row['queue_id']}",
        project_name=req.project_name,
        rto=row["rto"] or req.rto,
        current_phase=row.get("phase") or "Not on the cited file",
        queue_position=row.get("queue_position") if isinstance(row.get("queue_position"), int) else None,
        source_url=row.get("source_url") or "",
        alerts=[
            {
                "type": "source",
                "priority": "low",
                "title": "Official queue file",
                "description": row.get("note") or "",
            }
        ],
    )

# ─── Phase 0.2: Study Translator ───────────────────────────────────────────

class StudyTranslatorRequest(BaseModel):
    rto: str
    study_file: Optional[str] = None

class StudyTranslatorResponse(BaseModel):
    study_id: str
    rto: str
    key_findings: Dict[str, Any]
    summary: str
    financial_impact: Dict[str, Any]

@router.post("/translate-study", response_model=StudyTranslatorResponse)
async def translate_study(req: StudyTranslatorRequest, request: Request) -> StudyTranslatorResponse:
    """No study dollar or upgrade is printed unless the attached study states it."""
    return StudyTranslatorResponse(
        study_id="",
        rto=req.rto,
        key_findings={},
        summary="No study file was read. No upgrade and no dollar are printed.",
        financial_impact={},
    )

# ─── Phase 0.3: Timeline Predictor ───────────────────────────────────────────

class TimelinePredictionRequest(BaseModel):
    rto: str
    capacity_mw: float
    queue_position: int

class TimelinePredictionResponse(BaseModel):
    prediction_id: str
    rto: str
    estimated_days: Optional[int] = None
    confidence_percent: Optional[float] = None
    timeline_phases: list
    comparable_projects: list
    note: str = ""
    source_url: str = ""

@router.post("/predict-timeline", response_model=TimelinePredictionResponse)
async def predict_timeline(rto: str = "ERCOT") -> TimelinePredictionResponse:
    """The official file does not state an energization date. No date is estimated."""
    from interconnect.official_queue import OFFICIAL_QUEUE_PAGES

    url = OFFICIAL_QUEUE_PAGES.get((rto or "").strip().upper(), "")
    return TimelinePredictionResponse(
        prediction_id="",
        rto=rto,
        estimated_days=None,
        confidence_percent=None,
        timeline_phases=[],
        comparable_projects=[],
        note="The official queue file does not state an energization date. No date is estimated.",
        source_url=url,
    )

# ─── Phase 0.4: Site Compliance Checklist ───────────────────────────────────

class ComplianceChecklistRequest(BaseModel):
    rto: str
    state: str
    county: str
    project_type: str

class ComplianceChecklistResponse(BaseModel):
    checklist_id: str
    rto: str
    compliance_items: list
    overall_compliance_percent: Optional[float] = None
    critical_items: list
    summary: str

@router.post("/compliance-checklist", response_model=ComplianceChecklistResponse)
async def generate_compliance_checklist(req: ComplianceChecklistRequest, request: Request) -> ComplianceChecklistResponse:
    """No compliance percent is printed. The official queue file does not state one."""
    return ComplianceChecklistResponse(
        checklist_id="",
        rto=req.rto,
        compliance_items=[],
        overall_compliance_percent=None,
        critical_items=[],
        summary="No compliance percent is on the cited queue file. No percent is printed.",
    )
