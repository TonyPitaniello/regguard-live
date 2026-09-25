"""Entitlement: Estimator habit vs Pro research split (value ladder premortem)."""

from entitlement import (
    PAID_TIERS,
    PRO_RESEARCH_TIERS,
    has_paid_access,
    has_pro_research_access,
)


def test_partner_not_in_pro_research_tiers():
    assert "partner" in PAID_TIERS
    assert "partner" not in PRO_RESEARCH_TIERS
    assert "contractor_pro" in PRO_RESEARCH_TIERS


def test_unknown_email_has_no_access():
    assert has_paid_access("nobody-premortem@example.invalid") is False
    assert has_pro_research_access("nobody-premortem@example.invalid") is False
