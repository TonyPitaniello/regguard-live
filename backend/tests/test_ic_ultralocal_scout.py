from ic_ultralocal_scout import _hit_to_killer, _query_lines, run_ic_local_ultralocal_scout


def test_query_lines_cover_local_and_ultralocal():
    qs = _query_lines("Plano", "TX", "75074", "1201 14th St")
    buckets = {b for b, _ in qs}
    assert "local_ahj" in buckets
    assert "ultralocal_hoa" in buckets
    assert "ultralocal_mud" in buckets


def test_hit_to_killer():
    k = _hit_to_killer(
        {"title": "MUD 1", "url": "https://example.com/mud", "snippet": "assessments"},
        "ultralocal_mud",
    )
    assert k is not None
    assert k["ultralocal_bucket"] == "ultralocal_mud"
    assert "MUD" in k["title"]


def test_run_disabled_passthrough(monkeypatch):
    monkeypatch.setenv("IC_ULTRALOCAL_SCOUT", "0")
    base = {"project_info": {"city": "Plano", "state": "TX", "zip": "75074"}, "margin_killers": []}
    out = run_ic_local_ultralocal_scout(base, city="Plano", state="TX", zip_code="75074")
    assert out.get("ultralocal_scout") is None or not out.get("ultralocal_scout", {}).get("enabled")
