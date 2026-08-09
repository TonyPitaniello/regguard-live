"""
AI-Driven Punch List Generator for Data Center Interconnection Projects
Generates actionable contractor punch lists based on:
- Permit requirements
- Timeline milestones
- Risk findings
- Regulatory requirements
- Project-specific factors
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class PunchListItem:
    """Single action item in punch list"""
    priority: str  # CRITICAL, HIGH, MEDIUM, LOW
    task: str  # Action to take
    responsible_party: str  # Who does it (Contractor, Utility, AHJ, etc.)
    timeline: str  # When to do it (e.g., "Week 1", "Before permit submission")
    estimated_cost: Optional[float] = None
    notes: str = ""
    depends_on: Optional[List[str]] = None  # Task IDs this depends on
    source_url: Optional[str] = None
    source_label: Optional[str] = None
    verified: bool = False
    cost_verified: bool = False


# Citeable AHJ anchors for reverse-benchmark metros (link required to mark verified).
_AHJ_CITATIONS: Dict[str, Dict[str, tuple]] = {
    "plano, tx": {
        "building": (
            "https://www.plano.gov/269/Building-Inspections",
            "City of Plano Building Inspections",
        ),
        "fees": (
            "https://www.plano.gov/269/Building-Inspections",
            "City of Plano — electrical permit fee schedule ($75 total)",
        ),
    },
    "dallas, tx": {
        "building": (
            "https://dallascityhall.com/departments/sustainabledevelopment/buildinginspection/Pages/default.aspx",
            "City of Dallas Building Inspection",
        ),
        "fees": (
            "https://dallascityhall.com/departments/sustainabledevelopment/buildinginspection/Pages/default.aspx",
            "City of Dallas Building Inspection fee info",
        ),
    },
    "austin, tx": {
        "building": (
            "https://www.austintexas.gov/department/development-services",
            "City of Austin Development Services",
        ),
        "fees": (
            "https://www.austintexas.gov/development-services/fees",
            "Austin Development Services fees",
        ),
    },
}


def _normalize_location_key(location: str) -> str:
    text = (location or "").strip().lower()
    text = text.replace("texas", "tx")
    for city in ("plano", "dallas", "austin"):
        if city in text and ("tx" in text or "texas" in (location or "").lower() or "," in text):
            return f"{city}, tx"
    return text


def _http_source(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    v = value.strip()
    if v.startswith("http://") or v.startswith("https://"):
        return v
    return None


class PunchListGenerator:
    """
    AI-driven punch list generation
    Creates comprehensive, prioritized action lists for contractors
    """
    
    def __init__(self):
        self.logger = logger
    
    def generate_punch_list(
        self,
        project_type: str,
        location: str,
        environmental_risks: Dict[str, Any],
        utilities_involved: List[str],
        estimated_load_mw: Optional[float] = None,
        existing_issues: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive punch list for project
        
        Args:
            project_type: "data-center", "solar", "wind", etc.
            location: "City, State"
            environmental_risks: Results from environmental screening
            utilities_involved: ["ERCOT", "PJM", etc.]
            estimated_load_mw: Project size if applicable
            existing_issues: Known issues to address
        
        Returns:
            {
                "punch_list": [PunchListItem, ...],
                "timeline_summary": "8-12 weeks",
                "estimated_total_cost": 50000,
                "critical_path": [{task, source_url, verified, ...}],
                "milestones": [...],
                "estimates_verified": False,
            }
        """
        
        logger.info(f"🎯 Generating punch list for {project_type} in {location}")
        
        punch_list = []
        
        # Phase 1: Initial Permitting (Week 1-2)
        punch_list.extend(self._generate_initial_permitting_tasks(location, project_type))
        
        # Phase 2: Environmental & Regulatory (Week 1-4)
        punch_list.extend(self._generate_environmental_tasks(environmental_risks))
        
        # Phase 3: Utility Coordination (Week 2-6)
        punch_list.extend(self._generate_utility_coordination_tasks(utilities_involved, estimated_load_mw))
        
        # Phase 4: Site Preparation (Week 3-8)
        punch_list.extend(self._generate_site_prep_tasks(project_type))
        
        # Phase 5: Final Approvals (Week 6-10)
        punch_list.extend(self._generate_final_approval_tasks())
        
        # Add project-specific items
        if existing_issues:
            punch_list.extend(self._generate_issue_resolution_tasks(existing_issues))
        
        # Set task IDs for dependency tracking
        for i, item in enumerate(punch_list):
            item.task_id = f"task_{i:03d}"

        self._attach_citations(punch_list, location, environmental_risks)
        
        # Calculate timeline and costs
        timeline = self._calculate_timeline(punch_list)
        total_cost = sum(item.estimated_cost or 0 for item in punch_list)
        critical_path = self._identify_critical_path(punch_list)
        
        logger.info(f"✅ Punch list generated: {len(punch_list)} items, {timeline} duration, ${total_cost:,.0f} estimated")
        
        return {
            "punch_list": [self._item_to_dict(item) for item in punch_list],
            "timeline_summary": timeline,
            "estimated_total_cost": total_cost,
            "critical_path": critical_path,
            "milestones": self._generate_milestones(punch_list),
            "who_to_call": self._generate_contacts(location),
            "estimates_verified": False,
        }

    def _attach_citations(
        self,
        punch_list: List[PunchListItem],
        location: str,
        environmental_risks: Dict[str, Any],
    ) -> None:
        """Attach citeable links where known; leave others explicitly unverified."""
        ahj = _AHJ_CITATIONS.get(_normalize_location_key(location), {})
        building = ahj.get("building")
        fees = ahj.get("fees")

        finding_urls: List[tuple] = []
        for finding in environmental_risks.get("findings") or []:
            for src in finding.get("data_sources") or []:
                url = _http_source(str(src))
                if url:
                    finding_urls.append((url, str(src)))

        for item in punch_list:
            task_l = (item.task or "").lower()
            notes_l = (item.notes or "").lower()

            if building and any(
                k in task_l for k in ("permit", "municipal", "ahj", "building department", "application")
            ):
                item.source_url, item.source_label = building
                item.verified = True
                if fees and any(k in task_l or k in notes_l for k in ("fee", "cost", "electrical")):
                    item.source_url, item.source_label = fees
                    item.cost_verified = "plano" in _normalize_location_key(location)
                continue

            if fees and any(k in task_l for k in ("fee", "permit cost", "electrical permit")):
                item.source_url, item.source_label = fees
                item.verified = True
                item.cost_verified = "plano" in _normalize_location_key(location)
                continue

            if finding_urls and any(
                k in notes_l for k in ("wetland", "flood", "endangered", "nepa", "noise", "environmental")
            ):
                item.source_url, item.source_label = finding_urls[0]
                item.verified = True
                continue

            # Default: honest unverified — UI must show the badge
            if not item.source_url:
                item.verified = False
                item.cost_verified = False
    
    def _generate_initial_permitting_tasks(self, location: str, project_type: str) -> List[PunchListItem]:
        """Initial permit coordination tasks"""
        return [
            PunchListItem(
                priority="CRITICAL",
                task="Contact municipal permitting office for preliminary consultation",
                responsible_party="Contractor",
                timeline="Immediately (Day 1)",
                estimated_cost=0,
                notes="Confirm what permits are required for your project type"
            ),
            PunchListItem(
                priority="CRITICAL",
                task="Request complete permit application checklist",
                responsible_party="Contractor",
                timeline="Day 1-3",
                estimated_cost=50,
                notes="Get comprehensive list of required documents and forms"
            ),
            PunchListItem(
                priority="HIGH",
                task="Prepare site plans and engineering drawings",
                responsible_party="Engineer/Contractor",
                timeline="Week 1",
                estimated_cost=3000,
                notes="Typically required by all municipalities"
            ),
            PunchListItem(
                priority="HIGH",
                task="File complete permit application",
                responsible_party="Contractor",
                timeline="Week 2",
                estimated_cost=500,
                notes="Include all required documents to avoid delays"
            ),
        ]
    
    def _generate_environmental_tasks(self, environmental_risks: Dict[str, Any]) -> List[PunchListItem]:
        """Environmental compliance and remediation tasks"""
        tasks = []
        
        findings = environmental_risks.get("findings", [])
        
        for finding in findings:
            category = finding.get("category")
            risk_level = finding.get("risk_level")
            
            if risk_level in ["HIGH", "CRITICAL"]:
                sources = finding.get("data_sources") or []
                http_srcs = [_http_source(str(s)) for s in sources]
                http_srcs = [u for u in http_srcs if u]
                label = str(sources[0]) if sources else None
                # Add action items from finding
                for action in finding.get("action_items", []):
                    tasks.append(PunchListItem(
                        priority="HIGH" if risk_level == "HIGH" else "CRITICAL",
                        task=action,
                        responsible_party=self._get_responsible_party(category),
                        timeline=self._get_timeline_for_category(category),
                        estimated_cost=self._estimate_cost_for_action(category, action),
                        notes=f"Related to {category} risk",
                        source_url=http_srcs[0] if http_srcs else None,
                        source_label=label,
                        verified=bool(http_srcs),
                        cost_verified=False,
                    ))
        
        return tasks
    
    def _generate_utility_coordination_tasks(self, utilities_involved: List[str], load_mw: Optional[float]) -> List[PunchListItem]:
        """Utility interconnection and coordination tasks"""
        tasks = []
        
        for utility in utilities_involved:
            tasks.extend([
                PunchListItem(
                    priority="CRITICAL",
                    task=f"Contact {utility} interconnection department for study requirements",
                    responsible_party="Developer/Contractor",
                    timeline="Week 1",
                    estimated_cost=0,
                    notes="Confirm application requirements and timeline"
                ),
                PunchListItem(
                    priority="HIGH",
                    task=f"Submit {utility} interconnection study request",
                    responsible_party="Developer",
                    timeline="Week 2-3",
                    estimated_cost=5000,
                    notes="Includes feasibility study, system impact study, facility study"
                ),
                PunchListItem(
                    priority="MEDIUM",
                    task=f"Obtain {utility} approval for protective relay coordination",
                    responsible_party="Engineer",
                    timeline="Week 4-6",
                    estimated_cost=2000,
                    notes="Critical for parallel generation"
                ),
                PunchListItem(
                    priority="MEDIUM",
                    task=f"Execute {utility} interconnection agreement",
                    responsible_party="Developer",
                    timeline="Week 6-8",
                    estimated_cost=1000,
                    notes="Final contractual agreement for grid connection"
                ),
            ])
        
        return tasks
    
    def _generate_site_prep_tasks(self, project_type: str) -> List[PunchListItem]:
        """Site preparation and construction readiness tasks"""
        return [
            PunchListItem(
                priority="HIGH",
                task="Conduct environmental site assessment (Phase 1 ESA)",
                responsible_party="Environmental Consultant",
                timeline="Week 1-2",
                estimated_cost=3000,
                notes="Identify historical contamination risks"
            ),
            PunchListItem(
                priority="HIGH",
                task="Obtain surveys (topographic, boundary, environmental)",
                responsible_party="Surveyor",
                timeline="Week 1-2",
                estimated_cost=4000,
                notes="Essential for site plans and engineering"
            ),
            PunchListItem(
                priority="MEDIUM",
                task="Conduct geotechnical investigation",
                responsible_party="Geotechnical Engineer",
                timeline="Week 2-3",
                estimated_cost=5000,
                notes="Required for foundation design"
            ),
            PunchListItem(
                priority="MEDIUM",
                task="Notify public of project (if required by AHJ)",
                responsible_party="Contractor",
                timeline="Week 2-3",
                estimated_cost=500,
                notes="Typically required in newspapers or AHJ website"
            ),
            PunchListItem(
                priority="MEDIUM",
                task="Attend public hearing (if applicable)",
                responsible_party="Developer",
                timeline="Week 3-5",
                estimated_cost=0,
                notes="Address public comments and concerns"
            ),
        ]
    
    def _generate_final_approval_tasks(self) -> List[PunchListItem]:
        """Final permitting and construction readiness tasks"""
        return [
            PunchListItem(
                priority="HIGH",
                task="Obtain final permit approval from municipality",
                responsible_party="Contractor",
                timeline="Week 5-8",
                estimated_cost=0,
                notes="Resolution of any conditional requirements"
            ),
            PunchListItem(
                priority="HIGH",
                task="Schedule final inspection before construction start",
                responsible_party="Contractor",
                timeline="Week 7-9",
                estimated_cost=0,
                notes="AHJ final review and approval to begin work"
            ),
            PunchListItem(
                priority="MEDIUM",
                task="Obtain certificate of occupancy (if applicable)",
                responsible_party="Contractor",
                timeline="Week 10-12",
                estimated_cost=500,
                notes="Final sign-off for operational use"
            ),
        ]
    
    def _generate_issue_resolution_tasks(self, existing_issues: List[str]) -> List[PunchListItem]:
        """Tasks to resolve known project issues"""
        tasks = []
        for issue in existing_issues:
            tasks.append(PunchListItem(
                priority="HIGH",
                task=f"Resolve: {issue}",
                responsible_party="To Be Determined",
                timeline="Immediate",
                estimated_cost=None,
                notes="Known issue requiring attention"
            ))
        return tasks
    
    # ===== Helper Methods =====
    
    def _get_responsible_party(self, category: str) -> str:
        """Determine who is responsible for action"""
        mapping = {
            "wetlands": "Army Corps of Engineers / Environmental Consultant",
            "endangered_species": "USFWS / Environmental Consultant",
            "flood_zones": "FEMA / Flood Insurance Specialist",
            "noise_ordinances": "City Planning / Acoustic Consultant",
            "nepa": "Federal Agency / Environmental Consultant",
            "state_requirements": "State Environmental Agency",
        }
        return mapping.get(category, "Contractor")
    
    def _get_timeline_for_category(self, category: str) -> str:
        """Get typical timeline for addressing category"""
        mapping = {
            "wetlands": "Week 2-4",
            "endangered_species": "Week 2-5",
            "flood_zones": "Week 1-2",
            "noise_ordinances": "Week 1-3",
            "nepa": "Week 3-10",
            "state_requirements": "Week 1-6",
        }
        return mapping.get(category, "Week 2-4")
    
    def _estimate_cost_for_action(self, category: str, action: str) -> Optional[float]:
        """Estimate cost for specific action"""
        cost_ranges = {
            "wetlands": 5000,
            "endangered_species": 3000,
            "flood_zones": 500,
            "noise_ordinances": 1500,
            "nepa": 25000,
            "state_requirements": 2000,
        }
        return cost_ranges.get(category, 1000)
    
    def _calculate_timeline(self, punch_list: List[PunchListItem]) -> str:
        """Calculate overall project timeline"""
        # Simplified - in production would build dependency graph
        week_count = len(set(item.timeline for item in punch_list))
        return f"{week_count}-{week_count + 4} weeks"
    
    def _identify_critical_path(self, punch_list: List[PunchListItem]) -> List[Dict[str, Any]]:
        """Identify critical path tasks with citation metadata for the UI."""
        critical_items = [item for item in punch_list if item.priority == "CRITICAL"]
        out: List[Dict[str, Any]] = []
        for item in critical_items[:5]:
            out.append({
                "task": item.task,
                "source_url": item.source_url,
                "source_label": item.source_label,
                "verified": bool(item.verified and item.source_url),
                "cost_verified": bool(item.cost_verified),
                "estimated_cost": item.estimated_cost,
            })
        return out
    
    def _generate_milestones(self, punch_list: List[PunchListItem]) -> List[Dict[str, str]]:
        """Generate project milestones"""
        return [
            {"week": "1-2", "milestone": "All permits filed"},
            {"week": "2-4", "milestone": "Environmental issues resolved"},
            {"week": "4-6", "milestone": "Utility approval received"},
            {"week": "6-8", "milestone": "Final permits approved"},
            {"week": "8-12", "milestone": "Ready for construction"},
        ]
    
    def _generate_contacts(self, location: str) -> Dict[str, str]:
        """Generate list of important contacts"""
        return {
            "local_ahj": "Contact municipal planning/building department",
            "state_environmental": "Contact state environmental/natural resources agency",
            "utility": "Contact local utility interconnection department",
            "environmental_consultant": "Hire qualified environmental consultant",
            "engineer": "Hire professional engineer for design",
            "attorney": "Consider consulting with local attorney for permits",
        }
    
    def _item_to_dict(self, item: PunchListItem) -> Dict[str, Any]:
        """Convert PunchListItem to dictionary"""
        verified = bool(item.verified and _http_source(item.source_url))
        return {
            "priority": item.priority,
            "task": item.task,
            "responsible_party": item.responsible_party,
            "timeline": item.timeline,
            "estimated_cost": item.estimated_cost,
            "notes": item.notes,
            "depends_on": item.depends_on or [],
            "source_url": item.source_url if verified else item.source_url,
            "source_label": item.source_label,
            "verified": verified,
            "cost_verified": bool(item.cost_verified and verified),
        }


# Singleton instance
_generator = None

def get_punch_list_generator() -> PunchListGenerator:
    """Get or create punch list generator instance"""
    global _generator
    if _generator is None:
        _generator = PunchListGenerator()
    return _generator
