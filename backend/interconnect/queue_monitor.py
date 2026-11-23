"""Phase 0.1: Interconnection Queue Monitoring"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class QueuePosition:
    rto: str
    queue_id: str
    project_name: str
    current_phase: str
    queue_position: Optional[int]
    phase_changed_date: Optional[datetime]
    expected_study_start: Optional[datetime]
    expected_study_end: Optional[datetime]
    next_milestone: Optional[str]
    next_milestone_date: Optional[datetime]
    study_deposit_due: Optional[datetime]
    study_deposit_amount: Optional[float]
    data_submission_window: Optional[Dict[str, datetime]]
    additional_data: Dict[str, Any]

class QueueMonitor:
    def __init__(self):
        self.rto_urls = {
            "PJM": "https://www.pjm.com/planning/services-requests/interconnection-queues",
            "MISO": "https://www.misoenergy.org/planning/generator-interconnection/queue-and-status/",
            "ERCOT": "https://www.ercot.com/services/comm/gen_queue/",
        }
    
    async def scrape_queue_position(self, rto: str, queue_id: str) -> Optional[QueuePosition]:
        from interconnect.official_queue import cited_queue_lookup

        row = cited_queue_lookup(rto, queue_id)
        logger.info("Queue lookup %s/%s source=%s", rto, queue_id, row.get("source_url"))
        return QueuePosition(
            rto=row["rto"],
            queue_id=queue_id,
            project_name=row.get("project_name") or "",
            current_phase=row.get("phase") or "Not on the cited file",
            queue_position=None,
            phase_changed_date=None,
            expected_study_start=None,
            expected_study_end=None,
            next_milestone=None,
            next_milestone_date=None,
            study_deposit_due=None,
            study_deposit_amount=None,
            data_submission_window=None,
            additional_data={"source_url": row.get("source_url") or "", "note": row.get("note") or ""},
        )
    
    async def track_project(self, rto: str, queue_id: str, project_name: str) -> Dict[str, Any]:
        position = await self.scrape_queue_position(rto, queue_id)
        if not position:
            raise ValueError(f"Could not find queue position: {rto}/{queue_id}")
        return {
            "tracking_id": f"{rto}_{queue_id}",
            "project_name": project_name,
            "rto": rto,
            "queue_id": queue_id,
            "initial_position": position.queue_position,
            "current_phase": position.current_phase,
            "tracking_started_at": datetime.now().isoformat(),
        }
    
    async def get_alerts_for_project(self, rto: str, queue_id: str) -> List[Dict[str, Any]]:
        alerts = []
        position = await self.scrape_queue_position(rto, queue_id)
        if not position:
            return alerts
        return alerts

def create_queue_monitor() -> QueueMonitor:
    return QueueMonitor()
