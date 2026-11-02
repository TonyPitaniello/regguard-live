"""Six billing seats through the live webhook handler, plus the email-only gates.

Stripe stays in test mode. These events are unsigned only because the test
unsets STRIPE_WEBHOOK_SECRET. Production rejects that body with 401.
"""

from fastapi.testclient import TestClient


EMAIL = "buyer@example.com"


def _isolate(monkeypatch):
    monkeypatch.setattr("order_service._ORDERS_BY_EMAIL", {})
    monkeypatch.setattr("order_service._ORDERS_BY_SESSION", {})
    monkeypatch.setattr("order_service._supabase_rest", lambda *args, **kwargs: None)
    monkeypatch.setattr("order_service.recover_paid_checkouts_for_email", lambda *args, **kwargs: None)
    monkeypatch.setattr("order_service._load_orders_archive", lambda: None)
    monkeypatch.setattr("order_service._mirror_order_disk", lambda order: None)
    monkeypatch.setattr("email_service.get_email_service", lambda: None)
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)


def _post(client: TestClient, event: dict) -> dict:
    res = client.post("/auth/webhook/stripe", json=event)
    assert res.status_code == 200, res.text
    return res.json()


def _checkout(tier: str, session_id: str, **extra) -> dict:
    obj = {
        "id": session_id,
        "object": "checkout.session",
        "mode": "subscription" if tier != "ic_project" else "payment",
        "payment_status": "paid",
        "customer_email": EMAIL,
        "metadata": {"tier": tier, "email": EMAIL},
        "amount_total": {"partner": 7900, "contractor_pro": 14900, "ic_project": 150000}[tier],
        "currency": "usd",
    }
    obj.update(extra)
    return {"type": "checkout.session.completed", "data": {"object": obj}}


def _rows():
    from order_service import get_raw_orders_for_email

    out = {}
    for order in get_raw_orders_for_email(EMAIL):
        # Newest order for a tier wins. A later Pro purchase must not be hidden
        # behind the canceled one.
        out.setdefault(order["tier"], order)
    return out


def test_six_billing_states_through_the_webhook(monkeypatch):
    _isolate(monkeypatch)
    from entitlement import has_paid_access, has_pro_research_access
    from ic_project_fulfillment import evaluate_ic_site_access
    from main import app
    from order_service import stripe_object_id

    client = TestClient(app)

    # 1) $79 Estimator. Expanded subscription object must still store the id.
    first = _post(
        client,
        _checkout(
            "partner",
            "cs_test_est",
            subscription={"id": "sub_est", "object": "subscription"},
        ),
    )
    assert first["tier"] == "partner"
    assert stripe_object_id({"id": "sub_est"}) == "sub_est"
    assert _rows()["partner"]["stripe_subscription_id"] == "sub_est"
    assert _rows()["partner"]["status"] == "completed"
    assert has_paid_access(EMAIL) is True
    assert has_pro_research_access(EMAIL) is False

    # 2) Also-buy Pro. Estimator stays until that subscription is the one deleted.
    _post(
        client,
        _checkout("contractor_pro", "cs_test_pro", subscription="sub_pro"),
    )
    assert _rows()["partner"]["status"] == "completed"
    assert _rows()["contractor_pro"]["status"] == "completed"
    assert has_pro_research_access(EMAIL) is True
    # A Pro cancel with no tier must not close the Estimator seat.
    deleted = _post(
        client,
        {
            "type": "customer.subscription.deleted",
            "data": {"object": {"id": "sub_pro", "object": "subscription", "customer_email": EMAIL}},
        },
    )
    assert deleted["status"] == "canceled"
    assert _rows()["partner"]["status"] == "completed"
    assert _rows()["contractor_pro"]["status"] == "failed"
    assert str(_rows()["contractor_pro"]["stripe_subscription_id"]).startswith("ended:")
    assert has_paid_access(EMAIL) is True
    assert has_pro_research_access(EMAIL) is False

    # Buy Pro again so the desk is open for the past_due / refund cases below.
    _post(client, _checkout("contractor_pro", "cs_test_pro2", subscription="sub_pro2"))
    assert has_pro_research_access(EMAIL) is True

    # 4) Denied renewal closes the Pro desk until that invoice is paid.
    # Estimator stays. This runs before the IC bundle, which is its own seat.
    failed = _post(
        client,
        {
            "type": "invoice.payment_failed",
            "data": {"object": {"id": "in_fail", "object": "invoice", "subscription": "sub_pro2"}},
        },
    )
    assert failed["status"] == "past_due"
    assert _rows()["contractor_pro"]["status"] == "failed"
    assert _rows()["partner"]["status"] == "completed"
    assert has_pro_research_access(EMAIL) is False
    assert has_paid_access(EMAIL) is True
    paid = _post(
        client,
        {
            "type": "invoice.paid",
            "data": {"object": {"id": "in_ok", "object": "invoice", "subscription": "sub_pro2"}},
        },
    )
    assert paid["status"] == "restored"
    assert has_pro_research_access(EMAIL) is True

    # 3) IC bundle binds one site. A second address is a new purchase.
    _post(
        client,
        _checkout(
            "ic_project",
            "cs_test_ic",
            payment_intent="pi_ic",
            metadata={
                "tier": "ic_project",
                "email": EMAIL,
                "site_address": "100 Main St",
                "site_city": "Plano",
                "site_state": "TX",
                "site_zip": "75024",
            },
        ),
    )
    same = evaluate_ic_site_access(
        EMAIL, address="100 Main St", city="Plano", state="TX", zip_code="75024"
    )
    other = evaluate_ic_site_access(
        EMAIL, address="200 Other St", city="Austin", state="TX", zip_code="78701"
    )
    assert same["allowed"] is True
    assert same["mode"] == "same_site_refresh"
    assert other["allowed"] is False
    assert other["mode"] == "need_purchase"

    # 5) Canceled stays closed. A later paid invoice must not revive it.
    _post(
        client,
        {
            "type": "customer.subscription.deleted",
            "data": {"object": {"id": "sub_pro2", "object": "subscription", "status": "canceled"}},
        },
    )
    revived = _post(
        client,
        {
            "type": "invoice.payment_succeeded",
            "data": {"object": {"id": "in_late", "object": "invoice", "subscription": "sub_pro2"}},
        },
    )
    assert revived["status"] == "unchanged"
    assert _rows()["contractor_pro"]["status"] == "failed"
    # IC is still a paid research seat. Canceling Pro must not close it.
    assert has_pro_research_access(EMAIL) is True
    assert has_paid_access(EMAIL) is True

    # 6) Partial refund keeps the charge. Full refund of Pro's old charge does not
    # touch the IC payment intent. Refunding pi_ic ends only the bundle.
    partial = _post(
        client,
        {
            "type": "charge.refunded",
            "data": {
                "object": {
                    "id": "ch_ic_part",
                    "payment_intent": "pi_ic",
                    "amount": 150000,
                    "amount_refunded": 500,
                    "refunded": False,
                }
            },
        },
    )
    assert partial["status"] == "partial_refund_kept"
    assert _rows()["ic_project"]["status"] == "completed"
    # Estimator has no payment intent on the subscription checkout; a different charge
    # must not refund it. Full refund of the IC charge ends the bundle only.
    full = _post(
        client,
        {
            "type": "charge.refunded",
            "data": {
                "object": {
                    "id": "ch_ic_full",
                    "payment_intent": "pi_ic",
                    "amount": 150000,
                    "amount_refunded": 150000,
                    "refunded": True,
                }
            },
        },
    )
    assert full["status"] == "refunded"
    assert _rows()["ic_project"]["status"] == "refunded"
    assert _rows()["partner"]["status"] == "completed"
    assert has_paid_access(EMAIL) is True
    assert has_pro_research_access(EMAIL) is False


def test_blank_subscription_ids_do_not_cancel_every_seat(monkeypatch):
    _isolate(monkeypatch)
    from order_service import remember_order
    from billing_lifecycle import apply_stripe_event

    remember_order(
        {
            "order_id": "ord-est",
            "tier": "partner",
            "status": "completed",
            "email": EMAIL,
            "stripe_session_id": "cs_test_blank_est",
            "stripe_subscription_id": "",
            "amount": 7900,
        }
    )
    remember_order(
        {
            "order_id": "ord-pro",
            "tier": "contractor_pro",
            "status": "completed",
            "email": EMAIL,
            "stripe_session_id": "cs_test_blank_pro",
            "stripe_subscription_id": "",
            "amount": 14900,
        }
    )
    result = apply_stripe_event(
        {
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "id": "sub_pro",
                    "object": "subscription",
                    "metadata": {"tier": "contractor_pro", "email": EMAIL},
                }
            },
        }
    )
    assert result["status"] == "canceled"
    from order_service import get_raw_orders_for_email

    rows = {o["tier"]: o for o in get_raw_orders_for_email(EMAIL)}
    assert rows["partner"]["status"] == "completed"
    assert rows["contractor_pro"]["status"] == "failed"


def test_email_alone_does_not_open_paid_files_or_portals(monkeypatch):
    _isolate(monkeypatch)
    from order_service import remember_order
    from main import app

    remember_order(
        {
            "order_id": "ord-ic-file",
            "tier": "ic_project",
            "status": "completed",
            "email": EMAIL,
            "stripe_session_id": "cs_test_ic_file",
            "download_token": "secret-token",
            "amount": 150000,
            "site_address": "100 Main St",
            "site_city": "Plano",
            "site_state": "TX",
            "site_zip": "75024",
            "site_label": "100 Main St, Plano, TX 75024",
            "address": "100 Main St, Plano, TX 75024",
        }
    )
    client = TestClient(app)
    orders = client.get("/orders", params={"email": EMAIL})
    assert orders.status_code == 200
    assert orders.json()["locked"] is True
    assert orders.json()["orders"][0]["download_token"] == ""
    assert "100 Main St" not in orders.text
    pdf = client.get("/orders/ord-ic-file/pdfs/research_memo", params={"email": EMAIL})
    assert pdf.status_code == 403
    portal = client.post("/billing/portal", json={"email": EMAIL})
    assert portal.status_code == 401
    assert client.get("/partner/portal", params={"email": EMAIL}).status_code == 401
    assert client.get("/affiliates/me", params={"email": EMAIL}).status_code == 401
    other_site = client.post(
        "/ic-package/bundle",
        json={
            "email": EMAIL,
            "analysis_data": {
                "research_depth": "ic_full",
                "depth_tier": "ic_full",
                "project_info": {
                    "address": "200 Other St",
                    "city": "Austin",
                    "state": "TX",
                    "zip": "78701",
                },
            },
        },
    )
    assert other_site.status_code == 403
    stranger = client.post(
        "/ic-package/bundle",
        json={
            "email": "stranger@example.com",
            "analysis_data": {
                "research_depth": "ic_full",
                "depth_tier": "ic_full",
                "project_info": {
                    "address": "100 Main St",
                    "city": "Plano",
                    "state": "TX",
                    "zip": "75024",
                },
            },
        },
    )
    assert stranger.status_code == 403


def test_cron_and_unsigned_webhook_status(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "cron-test")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_only")
    from main import app

    client = TestClient(app)
    assert client.post("/cron/zip-watch").status_code == 401
    assert client.post("/cron/nurture-drip").status_code == 401
    unsigned = client.post(
        "/auth/webhook/stripe",
        json={"type": "customer.subscription.deleted", "data": {"object": {}}},
    )
    assert unsigned.status_code == 401
