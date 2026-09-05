"""Forward receipt credits + partner portal."""

from __future__ import annotations

import uuid

from account_credits import get_balance_usd
from affiliate_store import register_affiliate
from forward_rewards import reward_forward, rewards_for_email
from product_events import stamp_funnel_stats, track_event


def test_forward_credits_forwarder_and_partner(tmp_path, monkeypatch):
    # Isolate credit + reward stores
    import account_credits
    import forward_rewards

    monkeypatch.setattr(account_credits, "_PATH", tmp_path / "credits.json")
    monkeypatch.setattr(forward_rewards, "_PATH", tmp_path / "fwd.json")

    aff = register_affiliate(email="partner@example.com", name="Pat", code=f"p{uuid.uuid4().hex[:6]}")
    code = aff["code"]
    rid = f"r-{uuid.uuid4().hex[:8]}"

    out = reward_forward(
        research_id=rid,
        email="buyer@example.com",
        referral_code=code,
        channel="whatsapp",
    )
    assert out.get("forwarder_credit")
    assert out.get("partner_credit")
    assert get_balance_usd("buyer@example.com") == 5.0
    assert get_balance_usd("partner@example.com") == 10.0

    # Idempotent
    out2 = reward_forward(
        research_id=rid,
        email="buyer@example.com",
        referral_code=code,
        channel="whatsapp",
    )
    assert out2.get("already_rewarded") or out2.get("forwarder_credit") is None
    assert get_balance_usd("buyer@example.com") == 5.0
    assert get_balance_usd("partner@example.com") == 10.0

    stats = rewards_for_email("partner@example.com")
    assert stats["partner_total_usd"] == 10.0


def test_funnel_ic_close_rate_in_stats(tmp_path, monkeypatch):
    import product_events

    monkeypatch.setattr(product_events, "_PATH", tmp_path / "events.jsonl")
    track_event("checkout_view", channel="ic_project", meta={"tier": "ic_project"})
    track_event("checkout_start", channel="ic_project", meta={"tier": "ic_project"})
    track_event("checkout_start", channel="ic_project", meta={"tier": "ic_project"})
    track_event("checkout_complete", channel="ic_project", meta={"tier": "ic_project"})
    stats = stamp_funnel_stats(hours=168)
    assert stats["funnel"]["ic_project"]["starts"] >= 2
    assert stats["funnel"]["ic_project"]["completes"] >= 1
    assert stats["funnel"]["ic_project"]["close_rate"] is not None
