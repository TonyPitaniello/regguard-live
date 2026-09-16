from fee_kind import KIND_IMPACT, KIND_OTHER, KIND_PERMIT, KIND_TAP, classify_fee_kind


def test_permit_vs_tap_vs_impact():
    assert classify_fee_kind("Electrical permit") == KIND_PERMIT
    assert classify_fee_kind("Water tap fee") == KIND_TAP
    assert classify_fee_kind("Roadway impact fee") == KIND_IMPACT
    assert classify_fee_kind("Misc AHJ charge") == KIND_OTHER
