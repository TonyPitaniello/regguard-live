"""Overall environmental risk: GIS-only, consistent across runs."""

from real_environmental_screening import calculate_overall_env_risk


def _f(cat, level, verified=True):
    return {
        "category": cat,
        "risk_level": level,
        "verified": verified,
        "source_url": "https://example.com" if verified else None,
    }


def test_stubs_cannot_force_low_when_wetlands_unknown():
    """Chapin flip: FEMA Zone X + stub LOWs must not yield overall LOW if NWI failed."""
    meta = calculate_overall_env_risk(
        [
            _f("flood_zones", "LOW", True),
            _f("wetlands", "UNKNOWN", False),
            _f("noise_ordinances", "LOW", False),
            _f("nepa", "LOW", False),
            _f("state_requirements", "LOW", False),
        ]
    )
    assert meta["risk_level"] == "UNKNOWN"
    assert meta["basis"] == "partial_gis"


def test_wetlands_high_wins_over_flood_low():
    meta = calculate_overall_env_risk(
        [
            _f("flood_zones", "LOW", True),
            _f("wetlands", "HIGH", True),
            _f("noise_ordinances", "LOW", False),
        ]
    )
    assert meta["risk_level"] == "HIGH"
    assert meta["basis"] == "verified_gis"


def test_flood_and_wetlands_low_is_low():
    meta = calculate_overall_env_risk(
        [
            _f("flood_zones", "LOW", True),
            _f("wetlands", "LOW", True),
            _f("endangered_species", "UNKNOWN", False),
            _f("nepa", "LOW", False),
        ]
    )
    assert meta["risk_level"] == "LOW"
    assert meta["gis_complete"] is True


def test_species_unknown_does_not_block_high():
    meta = calculate_overall_env_risk(
        [
            _f("flood_zones", "LOW", True),
            _f("wetlands", "HIGH", True),
            _f("endangered_species", "UNKNOWN", False),
        ]
    )
    assert meta["risk_level"] == "HIGH"


def test_only_stubs_is_unknown():
    meta = calculate_overall_env_risk(
        [
            _f("noise_ordinances", "LOW", False),
            _f("nepa", "MEDIUM", False),
        ]
    )
    assert meta["risk_level"] == "UNKNOWN"
