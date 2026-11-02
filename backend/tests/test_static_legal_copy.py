"""Static /terms and /privacy must match the honesty ceiling (Vercel serves public/ over the SPA)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "frontend" / "public"
TERMS = ROOT / "terms" / "index.html"
PRIVACY = ROOT / "privacy" / "index.html"


def test_static_terms_match_beachhead_and_honesty():
    text = TERMS.read_text(encoding="utf-8")
    assert "November 2, 2026" in text
    assert "DFW" in text or "DFW–Austin" in text or "DFW-Austin" in text
    assert "Phase I ESA" in text
    assert "0–100" in text or "0-100" in text
    assert "Estimator / Permit Runner" in text
    assert "IC Diligence Bundle" in text
    assert "planning aids" in text.lower() or "planning aid" in text.lower()
    assert "September 4, 2026" not in text
    assert "Partner" not in text
    assert "ic_consultant" not in text


def test_static_privacy_matches_beachhead_date():
    text = PRIVACY.read_text(encoding="utf-8")
    assert "November 2, 2026" in text
    assert "DFW" in text
    assert "September 4, 2026" not in text
    assert "app.regguardagent.com" in text
