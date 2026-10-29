"""Paid checkouts must survive a Render redeploy via Supabase + Stripe recovery."""

from __future__ import annotations


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr("order_service._ORDERS_BY_EMAIL", {})
    monkeypatch.setattr("order_service._ORDERS_BY_SESSION", {})
    monkeypatch.setattr("order_service._STRIPE_RECOVERY_AT", {})
    monkeypatch.setenv("REGGUARD_DATA_DIR", str(tmp_path))


def test_persist_patches_existing_then_retries_core(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    calls = []

    def fake_rest(path, method="GET", json_body=None, prefer=""):
        calls.append((method, path, json_body))
        if method == "GET":
            return [{"id": "db-1", "stripe_session_id": "cs_test_1"}]
        if method == "PATCH" and json_body and "pdfs" in json_body:
            return None  # optional columns rejected
        if method == "PATCH":
            return []
        return None

    monkeypatch.setattr("order_service._supabase_rest", fake_rest)
    from order_service import persist_order_supabase

    ok = persist_order_supabase(
        {
            "order_id": "o1",
            "tier": "partner",
            "email": "buyer@example.com",
            "stripe_session_id": "cs_test_1",
            "amount": 7900,
            "status": "completed",
            "download_token": "tok",
            "pdfs": [{"type": "punch_list"}],
        }
    )
    assert ok is True
    assert any(m == "PATCH" for m, _, _ in calls)


def test_partner_falls_back_when_tier_check_rejects(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    posted = []

    def fake_rest(path, method="GET", json_body=None, prefer=""):
        if method == "GET":
            return []
        if method == "POST":
            posted.append(json_body or {})
            if (json_body or {}).get("tier") == "partner":
                return None
            return [{"id": "db-2"}]
        return None

    monkeypatch.setattr("order_service._supabase_rest", fake_rest)
    from order_service import persist_order_supabase

    ok = persist_order_supabase(
        {
            "order_id": "o2",
            "tier": "partner",
            "email": "buyer@example.com",
            "stripe_session_id": "cs_test_partner",
            "amount": 7900,
            "status": "completed",
        }
    )
    assert ok is True
    assert posted[-1]["tier"] == "contractor_pro"
    assert posted[-1]["amount"] == 7900


def test_app_tier_from_db_row_recovers_partner_amount():
    from order_service import _app_tier_from_db_row

    assert _app_tier_from_db_row("contractor_pro", 7900) == "partner"
    assert _app_tier_from_db_row("contractor_pro", 14900) == "contractor_pro"
    assert _app_tier_from_db_row("ic_consultant", 150000) == "ic_project"
    assert _app_tier_from_db_row("ic_consultant", 1500000) == "ic_annual"


def test_stripe_recovery_rehydrates_missing_sessions(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_x")

    class FakeSession:
        def __init__(self, data):
            self._data = data

        def to_dict(self):
            return dict(self._data)

    class FakeList:
        def __init__(self, data):
            self.data = data

    class FakeStripe:
        class Customer:
            @staticmethod
            def list(email=None, limit=10):
                return FakeList([])

        class checkout:
            class Session:
                @staticmethod
                def list(limit=40, status="complete", customer=None):
                    return FakeList(
                        [
                            FakeSession(
                                {
                                    "id": "cs_test_recovered_pro",
                                    "status": "complete",
                                    "payment_status": "paid",
                                    "amount_total": 14900,
                                    "currency": "usd",
                                    "customer_email": "buyer@example.com",
                                    "metadata": {
                                        "tier": "contractor_pro",
                                        "email": "buyer@example.com",
                                    },
                                }
                            )
                        ]
                    )

    import sys
    import types

    fake_mod = types.ModuleType("stripe")
    fake_mod.api_key = None
    fake_mod.Customer = FakeStripe.Customer
    fake_mod.checkout = FakeStripe.checkout
    monkeypatch.setitem(sys.modules, "stripe", fake_mod)

    persisted = []

    def fake_rest(path, method="GET", json_body=None, prefer=""):
        if method == "GET" and "stripe_session_id" in path:
            return []
        if method == "GET" and "email=" in path:
            return []
        if method == "POST":
            persisted.append(json_body)
            return [{"id": "db-new"}]
        return []

    monkeypatch.setattr("order_service._supabase_rest", fake_rest)
    from order_service import list_orders_for_email

    rows = list_orders_for_email("buyer@example.com")
    tiers = {r["tier"] for r in rows}
    assert "contractor_pro" in tiers
    assert any((p or {}).get("stripe_session_id") == "cs_test_recovered_pro" for p in persisted)


def test_fulfill_retries_persist_on_memory_hit(monkeypatch, tmp_path):
    import asyncio

    _isolate(monkeypatch, tmp_path)
    from order_service import remember_order

    remember_order(
        {
            "order_id": "o3",
            "tier": "contractor_pro",
            "email": "buyer@example.com",
            "stripe_session_id": "cs_test_retry",
            "amount": 14900,
            "status": "completed",
            "download_token": "tok",
        }
    )
    tries = {"n": 0}

    def fake_rest(path, method="GET", json_body=None, prefer=""):
        if method == "GET":
            return []
        tries["n"] += 1
        return [{"id": "db"}]

    monkeypatch.setattr("order_service._supabase_rest", fake_rest)
    from order_service import fulfill_checkout_session

    out = asyncio.get_event_loop().run_until_complete(
        fulfill_checkout_session({"id": "cs_test_retry", "metadata": {"tier": "contractor_pro"}})
    )
    assert out["tier"] == "contractor_pro"
    assert tries["n"] >= 1
