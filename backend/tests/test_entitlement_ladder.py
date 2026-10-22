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


def test_client_mode_cannot_grant_estimator_or_pro(monkeypatch):
    monkeypatch.setattr("entitlement.has_paid_access", lambda _email: False)
    monkeypatch.setattr("entitlement.has_pro_research_access", lambda _email: False)
    monkeypatch.setattr("entitlement.has_ic_access", lambda _email: False)
    from entitlement import resolve_run_access

    unpaid = "unpaid-premortem@example.invalid"
    partner = resolve_run_access(unpaid, research_mode="partner")
    assert partner["habit_paid"] is False
    assert partner["pro_research"] is False
    ic = resolve_run_access(unpaid, research_mode="ic", generate_ic_report=True)
    assert ic["pro_research"] is False
    assert ic["force_scout"] is False
    pro = resolve_run_access(unpaid, research_mode="pro")
    assert pro["habit_paid"] is False
    assert pro["pro_research"] is False


def test_paid_email_keeps_the_path_it_already_owns(monkeypatch):
    monkeypatch.setattr("entitlement.has_paid_access", lambda _email: True)
    monkeypatch.setattr("entitlement.has_pro_research_access", lambda _email: True)
    monkeypatch.setattr("entitlement.has_ic_access", lambda _email: False)
    from entitlement import resolve_run_access

    email = "pro-premortem@example.invalid"
    habit = resolve_run_access(email, research_mode="partner")
    assert habit["habit_paid"] is True
    assert habit["pro_research"] is False
    deep = resolve_run_access(email, research_mode="pro")
    assert deep["habit_paid"] is True
    assert deep["pro_research"] is True
    assert deep["force_scout"] is False
    free = resolve_run_access(email, research_mode="free")
    assert free["habit_paid"] is False
    assert free["pro_research"] is False
