"""Unauthenticated reads of customer data and unsigned webhooks fail closed."""

from fastapi.testclient import TestClient


def test_debug_config_and_routes_are_closed(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "op-secret")
    from main import app

    client = TestClient(app)
    assert client.get("/debug/config").status_code == 404
    assert client.get("/debug/routes").status_code == 404
    assert client.get("/debug/config", headers={"x-admin-secret": "op-secret"}).status_code == 200


def test_leads_and_maintenance_need_admin(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "op-secret")
    from main import app

    client = TestClient(app)
    assert client.get("/data-center-analysis/leads").status_code == 401
    assert client.get("/maintenance/subscriptions").status_code == 401
    opened = client.get("/maintenance/subscriptions", headers={"x-admin-secret": "op-secret"})
    assert opened.status_code == 200
    assert opened.json()["subscriptions"] == [] or isinstance(opened.json()["subscriptions"], list)


def test_billing_portal_needs_orders_key():
    from main import app

    client = TestClient(app)
    res = client.post("/billing/portal", json={"email": "payer@example.com"})
    assert res.status_code == 401


def test_partner_portal_and_affiliate_need_orders_key():
    from main import app

    client = TestClient(app)
    assert client.get("/partner/portal", params={"email": "payer@example.com"}).status_code == 401
    assert client.get("/affiliates/me", params={"email": "payer@example.com"}).status_code == 401


def test_entitlement_hides_bound_site_without_key(monkeypatch):
    monkeypatch.setattr(
        "entitlement.access_summary",
        lambda *args, **kwargs: {
            "paid": True,
            "ic_site": {
                "allowed": False,
                "mode": "address_required",
                "order_id": "ord-secret",
                "bound_site": "999 Secret Road",
                "site_fingerprint": "abc",
                "message": "bound to 999 Secret Road",
            },
        },
    )
    from main import app
    from orders_access import make_orders_key

    client = TestClient(app)
    hidden = client.get("/entitlement", params={"email": "payer@example.com"})
    assert hidden.status_code == 200
    assert hidden.json()["ic_site"]["bound_site"] == ""
    assert "999 Secret Road" not in hidden.text
    opened = client.get(
        "/entitlement",
        params={"email": "payer@example.com", "key": make_orders_key("payer@example.com")},
    )
    assert opened.json()["ic_site"]["bound_site"] == "999 Secret Road"


def test_jobs_email_alone_does_not_return_the_address(monkeypatch, tmp_path):
    monkeypatch.setenv("REG_GUARD_JOBS_DIR", str(tmp_path))
    import jobs_store as js

    js._MEMORY.clear()
    js._INDEX.clear()
    from jobs_store import upsert_job
    from main import app

    job = upsert_job(
        owner_email="gc@example.com",
        address="100 Secret St",
        city="Plano",
        state="TX",
        zip_code="75024",
        owner_key="device-1",
    )
    client = TestClient(app)
    by_email = client.get("/jobs", params={"email": "gc@example.com"})
    assert by_email.status_code == 200
    assert by_email.json()["count"] == 0
    assert "100 Secret St" not in by_email.text
    by_device = client.get("/jobs", params={"email": "gc@example.com", "owner_key": "device-1"})
    assert by_device.json()["count"] == 1
    assert by_device.json()["jobs"][0]["id"] == job["id"]


def test_pdf_download_rejects_email_without_token(monkeypatch):
    monkeypatch.setattr("order_service._ORDERS_BY_EMAIL", {})
    monkeypatch.setattr("order_service._ORDERS_BY_SESSION", {})
    monkeypatch.setattr("order_service._supabase_rest", lambda *args, **kwargs: None)
    from order_service import remember_order
    from main import app

    remember_order(
        {
            "order_id": "ord-pdf",
            "tier": "ic_project",
            "status": "completed",
            "email": "payer@example.com",
            "stripe_session_id": "cs_test_pdf",
            "download_token": "secret-token",
            "amount": 150000,
        }
    )
    client = TestClient(app)
    res = client.get(
        "/orders/ord-pdf/pdfs/research_memo",
        params={"email": "payer@example.com"},
    )
    assert res.status_code == 403


def test_twilio_webhook_fails_closed(monkeypatch):
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    from main import app

    client = TestClient(app)
    missing = client.post("/webhooks/twilio/sms-status", data={"MessageStatus": "delivered"})
    assert missing.status_code == 401
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "twilio-test-token")
    bad = client.post(
        "/webhooks/twilio/sms-status",
        data={"MessageStatus": "delivered"},
        headers={"x-twilio-signature": "not-a-signature"},
    )
    assert bad.status_code == 401


def test_cron_missing_header_is_401(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "cron-test")
    from main import app

    client = TestClient(app)
    assert client.post("/cron/weekly-job-reminders").status_code == 401
    assert client.post("/cron/zip-watch").status_code == 401
