"""When STRIPE_WEBHOOK_SECRET is set, unsigned and bad-signature webhooks are rejected."""

from fastapi.testclient import TestClient


def test_missing_signature_rejected_when_secret_set(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_live_secret")
    from main import app

    client = TestClient(app)
    res = client.post(
        "/auth/webhook/stripe",
        content=b'{"type":"customer.subscription.deleted","data":{"object":{}}}',
        headers={"content-type": "application/json"},
    )
    assert res.status_code == 401
    assert "signature" in res.json()["detail"].lower()


def test_bad_signature_rejected_when_secret_set(monkeypatch):
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test_live_secret")
    from main import app

    client = TestClient(app)
    res = client.post(
        "/auth/webhook/stripe",
        content=b'{"type":"customer.subscription.deleted","data":{"object":{}}}',
        headers={
            "content-type": "application/json",
            "stripe-signature": "t=1,v1=deadbeef",
        },
    )
    assert res.status_code == 401


def test_unsigned_allowed_only_without_secret(monkeypatch):
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    from main import app

    client = TestClient(app)
    res = client.post(
        "/auth/webhook/stripe",
        content=b'{"type":"customer.subscription.deleted","data":{"object":{}}}',
        headers={"content-type": "application/json"},
    )
    assert res.status_code == 200
