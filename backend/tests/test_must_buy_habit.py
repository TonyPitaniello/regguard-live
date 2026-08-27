"""Smoke tests for must-buy exports / unlock / credits."""

from bid_sheet_export import analysis_to_bid_csv
from share_unlock_store import grant_unlock, is_unlocked
from account_credits import add_credit, consume_credit, get_balance_usd
from gotcha_credit_store import approve_credit, record_pending_credit


def test_bid_sheet_csv_has_punch_and_fee():
    csv = analysis_to_bid_csv(
        {
            "project_info": {"address": "1 Main", "city": "Dallas", "state": "TX", "zip": "75201"},
            "punch_list": {
                "punch_list": [
                    {
                        "priority": "CRITICAL",
                        "task": "Confirm electrical fee",
                        "estimated_cost": 167,
                        "source_url": "https://example.com",
                        "verified": True,
                    }
                ]
            },
            "fee_card": {
                "fees": [
                    {
                        "trade": "electrical",
                        "label": "Min trade",
                        "amount_usd": 167,
                        "source_url": "https://example.com",
                        "verified": True,
                    }
                ]
            },
        }
    )
    assert "punch" in csv
    assert "fee" in csv
    assert "167" in csv


def test_share_unlock_roundtrip():
    rid = "rg-test-unlock-1"
    grant_unlock(rid, email="ops@example.com", channel="test")
    assert is_unlocked(rid, "ops@example.com") is True
    assert is_unlocked(rid, "other@example.com") is True  # research-level unlock


def test_gotcha_credit_approve_adds_balance():
    row = record_pending_credit(
        email="partner@example.com",
        zip_code="75074",
        note_text="Plano rejects X before Y",
        partner_tier="partner",
    )
    before = get_balance_usd("partner@example.com")
    approved = approve_credit(row["id"], reviewer="test")
    assert approved["status"] == "approved"
    after = get_balance_usd("partner@example.com")
    assert after >= before + 19
    took = consume_credit("partner@example.com", 5, reason="test")
    assert took == 5
