"""Tests for punch ranking + community friction (5-lens 10/10 path)."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from community_friction import build_community_friction  # noqa: E402
from punch_rank import normalize_punch_items, strip_md_bold  # noqa: E402


def test_strip_md():
    assert strip_md_bold("**FAST-41** triage") == "FAST-41 triage"


def test_rank_caps_and_order():
    items = [
        {"priority": "HIGH", "task": "Contact municipal permitting office for preliminary consultation"},
        {"priority": "CRITICAL", "task": "Request complete permit application checklist"},
        {"priority": "HIGH", "task": "**ERCOT 2026 Batch Zero** review"},
        {"priority": "HIGH", "task": "FAST-41 federal eligibility triage"},
        {"priority": "HIGH", "task": "Verify AHJ — Dallas building department"},
        {"priority": "HIGH", "task": "Budget Electrical permit"},
        {"priority": "HIGH", "task": "Upload single-line diagrams"},
        {"priority": "HIGH", "task": "Match permit type to scope"},
        {"priority": "HIGH", "task": "Open the official permit portal"},
        {"priority": "HIGH", "task": "Note adopted NEC edition"},
        {"priority": "HIGH", "task": "Use only resources that apply"},
        {"priority": "HIGH", "task": "File complete permit application"},
        {"priority": "LOW", "task": "Confirm SOS filings"},
        {"priority": "MEDIUM", "task": "Screen NEPA if federal nexus"},
    ]
    ranked = normalize_punch_items(items, is_dc=True, max_critical=3, max_high=8)
    pris = [i["priority"] for i in ranked]
    assert pris == sorted(pris, key=lambda p: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}[p])
    assert pris.count("CRITICAL") <= 3
    assert pris.count("HIGH") <= 8
    # Hygiene demoted
    municipal = next(i for i in ranked if "municipal" in i["task"].lower())
    assert municipal["priority"] == "MEDIUM"
    # No markdown
    assert "**" not in ranked[0]["task"]
    # Schedule killers promoted
    assert any("ERCOT" in i["task"] and i["priority"] == "CRITICAL" for i in ranked)


def test_community_friction_airport_dc():
    analysis = {
        "project_info": {
            "city": "Dallas",
            "state": "TX",
            "zip": "75261",
            "type": "data-center",
        },
        "ahj_card": {"portal_url": "https://example.com"},
    }
    fr = build_community_friction(analysis)
    assert fr["score"] >= 4
    assert fr["band"] in ("Moderate", "Elevated")
    assert any(s["id"] == "airport_adjacency" and s["level"] == 3 for s in fr["signals"])
    assert fr["verified"] is False
