"""Bradenton / Sarasota metro portal seeds for FL Gulf coverage."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_bradenton_metro_portal_resolves():
    from metro_portal_seeds import resolve_metro_portal_pack

    pack = resolve_metro_portal_pack("Bradenton", "FL", "34201")
    assert pack is not None
    assert pack.get("portal_only") is True
    assert pack.get("citeable") is False
    assert "bradenton" in str((pack.get("ahj") or {}).get("portal_url") or "").lower()
    assert (pack.get("ahj") or {}).get("phone")


def test_incomplete_depth_badge_note():
    from research_store import stamp_depth_badge

    analysis = {
        "research_depth": "pro_partial",
        "preview": True,
        "honesty": {"source": "instant"},
        "project_info": {"address": "7351 Meeting St", "city": "Bradenton", "state": "FL", "zip": "34201"},
    }
    out = stamp_depth_badge(analysis)
    assert "incomplete" in (out.get("depth_badge") or "").lower() or "Instant preview" in (
        out.get("depth_badge") or ""
    )
    assert out.get("depth_claim_honest") is False
    assert out.get("research_incomplete") is True
    assert out.get("depth_claim_note")
