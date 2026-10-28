"""Subscription end, denied renewal, refund, and no password signup."""

from pathlib import Path

import pytest


def _isolate(monkeypatch):
    monkeypatch.setattr("order_service._ORDERS_BY_EMAIL", {})
    monkeypatch.setattr("order_service._ORDERS_BY_SESSION", {})
    monkeypatch.setattr("order_service._supabase_rest", lambda *args, **kwargs: None)


def _order(**kwargs):
    from order_service import remember_order

    base = {
        "order_id": "ord-1",
        "tier": "contractor_pro",
        "status": "completed",
        "email": "payer@example.com",
        "stripe_session_id": "cs_test_pro",
        "stripe_subscription_id": "sub_pro",
        "stripe_payment_intent_id": "",
        "amount": 14900,
    }
    base.update(kwargs)
    return remember_order(base)


def test_subscription_deleted_ends_that_seat_only(monkeypatch):
    _isolate(monkeypatch)
    _order()
    _order(
        order_id="ord-ic",
        tier="ic_project",
        stripe_session_id="cs_test_ic",
        stripe_subscription_id="",
        stripe_payment_intent_id="pi_ic",
        amount=150000,
    )
    from billing_lifecycle import apply_stripe_event
    from entitlement import has_paid_access, has_pro_research_access
    from order_service import get_raw_orders_for_email

    result = apply_stripe_event(
        {
            "type": "customer.subscription.deleted",
            "data": {"object": {"id": "sub_pro", "object": "subscription", "metadata": {"tier": "contractor_pro", "email": "payer@example.com"}}},
        }
    )
    assert result["status"] == "canceled"
    rows = {o["order_id"]: o for o in get_raw_orders_for_email("payer@example.com")}
    assert rows["ord-1"]["status"] == "failed"
    assert str(rows["ord-1"]["stripe_subscription_id"]).startswith("ended:")
    assert rows["ord-ic"]["status"] == "completed"
    assert has_pro_research_access("payer@example.com") is True  # IC bundle still paid
    assert has_paid_access("payer@example.com") is True


def test_canceled_subscription_is_not_restored_by_a_later_invoice(monkeypatch):
    _isolate(monkeypatch)
    _order(email="only-pro@example.com", order_id="ord-pro")
    from billing_lifecycle import apply_stripe_event
    from entitlement import has_paid_access, has_pro_research_access

    apply_stripe_event(
        {"type": "customer.subscription.deleted", "data": {"object": {"id": "sub_pro", "object": "subscription"}}}
    )
    restored = apply_stripe_event(
        {
            "type": "invoice.payment_succeeded",
            "data": {"object": {"id": "in_1", "object": "invoice", "subscription": "sub_pro"}},
        }
    )
    assert restored["status"] == "unchanged"
    assert has_paid_access("only-pro@example.com") is False
    assert has_pro_research_access("only-pro@example.com") is False


def test_denied_renewal_ends_access_until_the_invoice_is_paid(monkeypatch):
    _isolate(monkeypatch)
    _order(email="renew@example.com")
    from billing_lifecycle import apply_stripe_event
    from entitlement import has_pro_research_access

    failed = apply_stripe_event(
        {
            "type": "invoice.payment_failed",
            "data": {"object": {"id": "in_fail", "object": "invoice", "subscription": "sub_pro"}},
        }
    )
    assert failed["status"] == "past_due"
    assert has_pro_research_access("renew@example.com") is False
    paid = apply_stripe_event(
        {
            "type": "invoice.payment_succeeded",
            "data": {"object": {"id": "in_ok", "object": "invoice", "subscription": "sub_pro"}},
        }
    )
    assert paid["status"] == "restored"
    assert has_pro_research_access("renew@example.com") is True


def test_full_refund_ends_that_charge_only(monkeypatch):
    _isolate(monkeypatch)
    _order(email="refund@example.com", stripe_subscription_id="", stripe_payment_intent_id="pi_pro", tier="contractor_pro")
    _order(
        order_id="ord-ic",
        email="refund@example.com",
        tier="ic_project",
        stripe_session_id="cs_test_ic",
        stripe_subscription_id="",
        stripe_payment_intent_id="pi_ic",
        amount=150000,
    )
    from billing_lifecycle import apply_stripe_event
    from order_service import get_raw_orders_for_email

    partial = apply_stripe_event(
        {
            "type": "charge.refunded",
            "data": {"object": {"id": "ch_1", "payment_intent": "pi_pro", "amount": 14900, "amount_refunded": 100, "refunded": False}},
        }
    )
    assert partial["status"] == "partial_refund_kept"
    full = apply_stripe_event(
        {
            "type": "charge.refunded",
            "data": {"object": {"id": "ch_1", "payment_intent": "pi_pro", "amount": 14900, "amount_refunded": 14900, "refunded": True}},
        }
    )
    assert full["status"] == "refunded"
    rows = {o["stripe_payment_intent_id"]: o for o in get_raw_orders_for_email("refund@example.com")}
    assert rows["pi_pro"]["status"] == "refunded"
    assert rows["pi_ic"]["status"] == "completed"


def test_ended_order_does_not_come_back_from_stripe(monkeypatch):
    _isolate(monkeypatch)
    _order(email="ended@example.com", status="failed", stripe_subscription_id="ended:sub_pro")
    monkeypatch.setattr("entitlement._stripe_paid_for_email", lambda _email: True)
    from entitlement import has_paid_access

    assert has_paid_access("ended@example.com") is False


def test_refunded_order_does_not_download(monkeypatch):
    _isolate(monkeypatch)
    _order(
        order_id="ord-dl",
        email="dl@example.com",
        tier="ic_project",
        status="refunded",
        download_token="tok",
        stripe_session_id="cs_test_dl",
        stripe_payment_intent_id="pi_dl",
    )
    from ic_project_fulfillment import ensure_pdf_bytes

    data, err = ensure_pdf_bytes("ord-dl", "research_memo", token="tok")
    assert data is None
    assert err == "This order has ended"


def test_canceled_annual_does_not_cover_another_site(monkeypatch):
    _isolate(monkeypatch)
    _order(
        order_id="ord-annual",
        email="annual@example.com",
        tier="ic_annual",
        status="failed",
        stripe_subscription_id="ended:sub_annual",
        stripe_session_id="cs_test_annual",
        amount=1500000,
    )
    from ic_project_fulfillment import evaluate_ic_site_access

    access = evaluate_ic_site_access(
        "annual@example.com",
        address="100 Main",
        city="Austin",
        state="TX",
        zip_code="78701",
    )
    assert access["allowed"] is False
    assert access["mode"] == "need_purchase"


@pytest.mark.asyncio
async def test_subscription_checkout_carries_tier_and_no_password(monkeypatch):
    monkeypatch.setattr("stripe_service.is_stripe_configured", lambda: True)
    monkeypatch.setattr("stripe_service._find_or_create_stripe_customer", lambda *args, **kwargs: "cus_1")
    captured = {}

    class Session:
        id = "cs_test_1"
        url = "https://checkout.stripe.com/c/pay/cs_test_1"

    def create(**kwargs):
        captured.update(kwargs)
        return Session()

    monkeypatch.setattr("stripe_service.stripe.checkout.Session.create", create)
    from stripe_service import create_checkout_session

    await create_checkout_session(user_id="u1", tier="contractor_pro", email="buyer@example.com")
    assert captured["mode"] == "subscription"
    assert captured["subscription_data"]["metadata"]["tier"] == "contractor_pro"
    assert captured["subscription_data"]["metadata"]["email"] == "buyer@example.com"
    assert "password" not in str(captured)


def test_legacy_signup_module_has_no_password():
    text = (Path(__file__).resolve().parents[1] / "auth.py").read_text(encoding="utf-8")
    assert "password_hash" not in text
    assert "sign_up" not in text


def test_billing_portal_returns_stripe_url(monkeypatch):
    import billing_lifecycle

    class Customer:
        id = "cus_1"

    class CustomerList:
        data = [Customer()]

    class PortalSession:
        url = "https://billing.stripe.com/p/session/test_session"

    monkeypatch.setattr(billing_lifecycle, "_stripe_client", lambda: billing_lifecycle.stripe)
    monkeypatch.setattr(billing_lifecycle.stripe.Customer, "list", lambda **kwargs: CustomerList())
    monkeypatch.setattr(
        billing_lifecycle.stripe.billing_portal.Session,
        "create",
        lambda **kwargs: PortalSession(),
    )
    url = billing_lifecycle.create_billing_portal_url("payer@example.com")
    assert url.startswith("https://billing.stripe.com/")
