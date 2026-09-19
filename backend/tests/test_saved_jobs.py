"""Saved Jobs store + API helpers."""

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


@pytest.fixture
def jobs_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("REG_GUARD_JOBS_DIR", str(tmp_path))
    # Reset module singletons
    import jobs_store as js

    js._MEMORY.clear()
    js._INDEX.clear()
    return tmp_path


def test_upsert_list_get_delete(jobs_dir):
    from jobs_store import delete_job, get_job, list_jobs, upsert_job

    job = upsert_job(
        owner_email="gc@example.com",
        address="100 Main St",
        city="Plano",
        state="TX",
        zip_code="75074",
        project_type="electrical",
        owner_key="own-test-1",
        last_research_id="rg-abc",
        share_url="https://app.regguardagent.com/r/rg-abc",
        summary_snapshot={"estimated_total_cost": 1000, "preview": True},
    )
    assert job["id"].startswith("job-")
    assert job["owner_email"] == "gc@example.com"

    listed = list_jobs(email="gc@example.com")
    assert len(listed) == 1
    assert listed[0]["address"] == "100 Main St"

    # Dedupe same address
    job2 = upsert_job(
        owner_email="gc@example.com",
        address="100 Main St",
        city="Plano",
        state="TX",
        zip_code="75074",
        last_research_id="rg-def",
        share_url="https://app.regguardagent.com/r/rg-def",
    )
    assert job2["id"] == job["id"]
    assert job2["last_research_id"] == "rg-def"
    assert len(list_jobs(email="gc@example.com")) == 1

    got = get_job(job["id"], email="gc@example.com")
    assert got is not None

    # Wrong email cannot access
    assert get_job(job["id"], email="other@example.com") is None

    assert delete_job(job["id"], email="gc@example.com") is True
    assert list_jobs(email="gc@example.com") == []


def test_owner_key_access(jobs_dir):
    from jobs_store import get_job, list_jobs, upsert_job

    job = upsert_job(
        owner_email="a@example.com",
        address="9 Oak",
        owner_key="device-xyz",
    )
    listed = list_jobs(owner_key="device-xyz")
    assert any(j["id"] == job["id"] for j in listed)
    assert get_job(job["id"], owner_key="device-xyz") is not None


def test_stale_job_id_does_not_overwrite_other_address(jobs_dir):
    from jobs_store import list_jobs, upsert_job

    first = upsert_job(
        owner_email="gc@example.com",
        address="100 Main St",
        city="Plano",
        state="TX",
        zip_code="75074",
    )
    second = upsert_job(
        owner_email="gc@example.com",
        address="200 Oak Ave",
        city="Dallas",
        state="TX",
        zip_code="75201",
        job_id=first["id"],  # stale id from prior site
    )
    assert second["id"] != first["id"]
    assert second["address"] == "200 Oak Ave"
    listed = list_jobs(email="gc@example.com")
    assert len(listed) == 2
    addrs = {j["address"] for j in listed}
    assert addrs == {"100 Main St", "200 Oak Ave"}


def test_list_reconciles_jobs_missing_from_stale_index(jobs_dir):
    """Simulate multi-worker: job file on disk but email index omitted the id."""
    import jobs_store as js
    from jobs_store import list_jobs, upsert_job

    job = upsert_job(
        owner_email="multi@example.com",
        address="9 Index Gap",
        city="Austin",
        state="TX",
        zip_code="78701",
    )
    # Corrupt in-memory + on-disk index (as if another worker wrote the job file only)
    js._INDEX.clear()
    js._INDEX_MTIME = -1.0
    js._index_path().write_text("{}", encoding="utf-8")
    js._MEMORY.clear()

    listed = list_jobs(email="multi@example.com")
    assert len(listed) == 1
    assert listed[0]["id"] == job["id"]

