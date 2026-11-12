"""Public checkout refuses Sponsor and off-site return URLs."""

from fastapi.testclient import TestClient


def _post(client: TestClient, **extra):
    body = {
        "tier": "partner",
        "email": "audit-checkout-guard@example.com",
        "name": "Audit Nobody",
        "success_url": "https://app.regguardagent.com/checkout/success",
        "cancel_url": "https://app.regguardagent.com/checkout/partner",
    }
    body.update(extra)
    return client.post("/checkout", json=body)


def test_sponsor_checkout_is_rejected():
    from main import app

    res = _post(TestClient(app), tier="sponsor")
    assert res.status_code == 400
    assert "Sponsor is not sold" in res.text


def test_return_url_must_be_the_app_host():
    from main import app

    client = TestClient(app)
    offsite = _post(client, success_url="https://evil.example/checkout/success")
    assert offsite.status_code == 400
    assert "app.regguardagent.com" in offsite.text

    localhost = _post(client, cancel_url="http://localhost:5173/checkout/partner")
    assert localhost.status_code == 400

    other_product = _post(client, success_url="https://app.regguard.com/checkout/success")
    assert other_product.status_code == 400


def test_health_card_checkout_is_test_or_live():
    from main import app

    res = TestClient(app).get("/health")
    assert res.status_code == 200
    assert res.json()["card_checkout"] in ("test", "live")
