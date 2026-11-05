"""Research-id and session-id lookups must not leak stored customer fields."""

from fastapi.testclient import TestClient


def _analysis(address: str, email: str) -> dict:
    return {
        "project_info": {
            "address": address,
            "city": "Plano",
            "state": "TX",
            "zip": "75074",
        },
        "owner_email": email,
        "research_depth": "free",
        "regguard_stamp": {"grade": "HOLD", "fingerprint": "fp-audit"},
    }


def test_share_unlock_does_not_return_forwarder_emails():
    from main import app

    client = TestClient(app)
    rid = "audit-share-unlock-01"
    first = client.post(
        f"/research/{rid}/share-unlock",
        json={"email": "first-forwarder@example.com", "channel": "share"},
    )
    second = client.post(
        f"/research/{rid}/share-unlock",
        json={"email": "audit-nobody@example.com", "channel": "share"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    body = second.json()
    assert "emails" not in body
    assert "first-forwarder@example.com" not in second.text
    assert body["unlocked"] is False


def test_persist_does_not_overwrite_an_existing_report():
    from research_store import get_analysis, save_research
    from main import app

    rid = "audit-persist-keep-01"
    save_research(_analysis("1201 14th St", "owner@example.com"), research_id=rid)
    client = TestClient(app)
    res = client.post(
        "/research/persist",
        json={
            "research_id": rid,
            "analysis": _analysis("999 Replaced Ave", "intruder@example.com"),
        },
    )
    assert res.status_code == 200
    assert res.json().get("existed") is True
    kept = get_analysis(rid) or {}
    assert (kept.get("project_info") or {}).get("address") == "1201 14th St"
    assert "999 Replaced Ave" not in str(kept)


def test_stamp_by_research_id_does_not_return_the_stored_report():
    from research_store import save_research
    from main import app

    rid = "audit-stamp-redact-01"
    save_research(_analysis("1201 14th St", "owner@example.com"), research_id=rid)
    client = TestClient(app)
    res = client.post("/stamp", json={"research_id": rid})
    assert res.status_code == 200
    body = res.json()
    assert "analysis" not in body
    assert "owner@example.com" not in res.text
    assert body.get("stamp")


def test_id_only_delivery_uses_the_public_share_not_the_stored_email():
    from research_store import save_research
    from main import _resolve_research_data

    rid = "audit-delivery-public-01"
    save_research(_analysis("1201 14th St", "owner@example.com"), research_id=rid)
    data = _resolve_research_data(rid, None, None)
    assert data.get("owner_email") in (None, "")
    assert "owner@example.com" not in str(data)


def test_send_does_not_replace_a_saved_report():
    from research_store import get_analysis, save_research
    from main import _resolve_research_data

    rid = "audit-delivery-keep-01"
    save_research(_analysis("1201 14th St", "owner@example.com"), research_id=rid)
    _resolve_research_data(
        rid,
        None,
        _analysis("999 Replaced Ave", "intruder@example.com"),
    )
    kept = get_analysis(rid) or {}
    assert (kept.get("project_info") or {}).get("address") == "1201 14th St"


def test_garbage_checkout_session_does_not_call_stripe(monkeypatch):
    called = {"n": 0}

    async def _boom(_sid):
        called["n"] += 1
        raise AssertionError("stripe retrieve")

    monkeypatch.setattr("order_service.confirm_stripe_session", _boom)
    from main import app

    client = TestClient(app)
    res = client.get("/checkout/confirm", params={"session_id": "1"})
    assert res.status_code == 400
    assert called["n"] == 0


def test_research_id_does_not_mint_or_freeze_the_war_room(monkeypatch):
    monkeypatch.setenv("ADMIN_SECRET", "op-secret")
    from uuid import uuid4

    from research_store import save_research
    from main import app

    rid = f"audit-war-room-{uuid4().hex[:10]}"
    fresh = f"audit-war-room-{uuid4().hex[:10]}"
    save_research(_analysis("1201 14th St", "owner@example.com"), research_id=rid)
    client = TestClient(app)

    minted = client.post(f"/research/{rid}/war-room/token")
    assert minted.status_code == 404

    frozen = client.post(f"/research/{rid}/war-room/freeze")
    assert frozen.status_code == 401

    created = client.post(
        "/research/persist",
        json={"research_id": fresh, "analysis": _analysis("800 Audit Ln", "owner@example.com")},
    )
    assert created.status_code == 200
    token = str(created.json().get("write_token") or "")
    assert len(token) > 8
    report = client.get(f"/research/{fresh}/report")
    assert report.status_code == 200
    assert token not in report.text
    again = client.post(
        "/research/persist",
        json={"research_id": fresh, "analysis": _analysis("800 Audit Ln", "owner@example.com")},
    )
    assert again.status_code == 200
    assert "write_token" not in again.json()

    locked = client.post(
        f"/research/{fresh}/war-room/freeze",
        headers={"X-War-Room-Token": token},
    )
    assert locked.status_code == 200
    stranger = client.post(f"/research/{fresh}/war-room/token")
    assert stranger.status_code == 404
    admin = client.post(
        f"/research/{rid}/war-room/freeze",
        headers={"X-Admin-Secret": "op-secret"},
    )
    assert admin.status_code == 200


def test_attach_receipt_list_omits_requester_email(tmp_path, monkeypatch):
    import receipt_attach

    monkeypatch.setattr(receipt_attach, "_PATH", tmp_path / "receipt_attachments.json")
    from main import app

    client = TestClient(app)
    posted = client.post(
        "/integrations/attach-receipt",
        json={
            "research_id": "audit-attach-01",
            "external_system": "procore",
            "external_project_id": "p-1",
            "requester_email": "buyer@example.com",
        },
    )
    assert posted.status_code == 200
    assert "buyer@example.com" not in posted.text
    listed = client.get("/integrations/attach-receipt/audit-attach-01")
    assert listed.status_code == 200
    assert "buyer@example.com" not in listed.text
    assert listed.json()["count"] == 1
