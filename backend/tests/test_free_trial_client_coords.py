"""Client lat/lng on FreeTrialRequest preferred over Null Island profile."""

from free_trial_handler import FreeTrialRequest


def test_free_trial_request_accepts_coords():
    req = FreeTrialRequest(
        address="7351 Meeting St",
        project_type="data-center",
        email="a@b.com",
        city="Bradenton",
        state="FL",
        zip="34201",
        latitude=27.498,
        longitude=-82.574,
    )
    assert req.latitude == 27.498
    assert req.longitude == -82.574
