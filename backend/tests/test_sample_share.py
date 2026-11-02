"""Labeled Chapin samples must open on /r/ with a stamp that is not already expired."""

from datetime import datetime, timezone


def test_sample_share_ids_resolve_with_fresh_stamp():
    from research_store import get_research

    rec = get_research("rg-sample-chapin-free")
    assert rec is not None
    assert rec["id"] == "rg-sample-chapin-free"
    analysis = rec["analysis"]
    assert analysis.get("preview") is True
    assert "/r/rg-sample-chapin-free" in (analysis.get("share_url") or "")
    until = str((analysis.get("regguard_stamp") or {}).get("valid_until") or "")
    exp = datetime.strptime(until.replace("Z", ""), "%Y-%m-%dT%H:%M:%S.%f")
    if "." not in until:
        exp = datetime.strptime(until.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
    assert exp.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)


def test_unknown_id_is_not_a_sample():
    from sample_dc_fixture import sample_share_record

    assert sample_share_record("rg-not-a-sample") is None
