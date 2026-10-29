"""My Orders: the email sees the plan; only the signed key sees downloads."""

import time

import pytest
from fastapi.testclient import TestClient


def _isolate(monkeypatch):
    monkeypatch.setattr("order_service._ORDERS_BY_EMAIL", {})
    monkeypatch.setattr("order_service._ORDERS_BY_SESSION", {})
    monkeypatch.setattr("order_service._supabase_rest", lambda *args, **kwargs: None)


def _ic_order(email="payer@example.com"):
    from order_service import remember_order

    return remember_order(
        {
            "order_id": "ord-ic",
            "tier": "ic_project",
            "status": "completed",
            "email": email,
            "stripe_session_id": "cs_test_ic",
            "download_token": "secret-token",
            "amount": 150000,
            "pdfs": [
                {
                    "type": "research_memo",
                    "name": "Research Memo",
                    "size": "1 KB",
                    "url": "https://api.example/orders/ord-ic/pdfs/research_memo?email=payer%40example.com&token=secret-token",
                    "icon": "x",
                    "status": "ready",
                }
            ],
        }
    )


def test_key_round_trip_and_expiry():
    from orders_access import make_orders_key, verify_orders_key

    key = make_orders_key("Payer@Example.com")
    assert verify_orders_key("payer@example.com", key) is True
    assert verify_orders_key("other@example.com", key) is False
    assert verify_orders_key("payer@example.com", key + "x") is False
    expired = make_orders_key("payer@example.com", ttl_seconds=-5)
    assert verify_orders_key("payer@example.com", expired) is False


def test_orders_by_email_alone_hides_token_and_links(monkeypatch):
    _isolate(monkeypatch)
    _ic_order()
    from main import app

    client = TestClient(app)
    res = client.get("/orders", params={"email": "payer@example.com"})
    assert res.status_code == 200
    body = res.json()
    assert body["locked"] is True
    order = body["orders"][0]
    assert order["tier"] == "ic_project"
    assert order["download_token"] == ""
    assert "secret-token" not in res.text
    assert order["pdfs"][0]["locked"] is True


def test_signed_key_unlocks_downloads(monkeypatch):
    _isolate(monkeypatch)
    _ic_order()
    from main import app
    from orders_access import make_orders_key

    client = TestClient(app)
    res = client.get(
        "/orders",
        params={"email": "payer@example.com", "key": make_orders_key("payer@example.com")},
    )
    body = res.json()
    assert body["locked"] is False
    assert body["orders"][0]["download_token"] == "secret-token"
    assert "token=secret-token" in body["orders"][0]["pdfs"][0]["url"]


def test_send_link_only_mails_when_orders_exist(monkeypatch):
    _isolate(monkeypatch)
    sent = []
    monkeypatch.setattr("orders_access._send_html", lambda to, subject, html: sent.append((to, html)) or True)
    monkeypatch.setattr("orders_access._LAST_SENT", {})
    from orders_access import send_orders_link

    assert send_orders_link("nobody@example.com") == {"status": "sent"}
    assert sent == []
    _ic_order()
    assert send_orders_link("payer@example.com")["status"] == "sent"
    assert len(sent) == 1
    to, html = sent[0]
    assert to == "payer@example.com"
    assert "/orders?email=payer%40example.com&key=" in html
    # Second request inside the gap does not mail again.
    assert send_orders_link("payer@example.com").get("throttled") is True
    assert len(sent) == 1


def test_debug_routes_need_admin_secret(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "op-secret")
    from main import app

    client = TestClient(app)
    assert client.get("/debug/env").status_code == 404
    ok = client.get("/debug/env", headers={"x-admin-secret": "op-secret"})
    assert ok.status_code == 200
    assert "SUPABASE_URL" not in ok.json()
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/docs").status_code == 404


def test_no_admin_secret_means_debug_is_closed(monkeypatch):
    monkeypatch.delenv("ADMIN_SECRET", raising=False)
    from main import app

    client = TestClient(app)
    assert client.get("/debug/dns", headers={"x-admin-secret": ""}).status_code == 404
