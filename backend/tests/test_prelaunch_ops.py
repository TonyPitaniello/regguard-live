"""Disk-wipe quota and the public health probe. No secrets in the probe."""

from __future__ import annotations

import json


def test_free_quota_survives_a_disk_wipe(tmp_path, monkeypatch):
    monkeypatch.setenv("REGGUARD_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("FREE_TRIAL_SCANS_PER_MONTH", "2")
    store: dict = {}

    import free_scan_quota as quota

    monkeypatch.setattr(quota, "_durable_load", lambda month: dict(store.get(month) or {}))

    def save(month, counts):
        store[month] = dict(counts)
        return True

    monkeypatch.setattr(quota, "_durable_save", save)

    assert quota.consume_free_scan("a@example.com")[0] is True
    assert quota.consume_free_scan("a@example.com")[0] is True
    (tmp_path / "free_scan_quota.json").unlink()

    allowed, usage = quota.consume_free_scan("a@example.com")
    assert allowed is False
    assert usage["used"] == 2
    assert usage["limit"] == 2
    assert store


def test_quota_row_is_not_a_customer_order():
    from order_service import get_order_by_session

    assert get_order_by_session("quota_2026-11") is None
    assert get_order_by_session("share_rg-sample") is None


def test_health_names_disk_and_webhook_without_secrets(monkeypatch):
    monkeypatch.delenv("REGGUARD_DATA_DIR", raising=False)
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)

    from main import health

    out = health()
    blob = json.dumps(out)
    assert out["ok"] is True
    assert out["webhook_signature_required"] is False
    assert "disk_ephemeral" in out["degraded"]
    assert "webhook_signature_off" in out["degraded"]
    assert "whsec_" not in blob
    assert "sk_live" not in blob
    assert "sk_test" not in blob
    assert "@" not in blob
