"""Customer copy stays inside the beachhead and the honesty ceiling."""

from email_service import build_research_result_html
from honesty import permit_total_line
from partner_mandate import MANDATE_EMAIL, MANDATE_ONE_LINER, MANDATE_SCRIPT
from report_email import build_forwardable_plaintext, build_forwardable_result_html


def _priced():
    return {
        "project_info": {"address": "1 Main", "city": "Plano", "state": "TX", "zip": "75024"},
        "summary": {
            "high_risk_count": 2,
            "total_environmental_risks": 2,
            "estimated_timeline": "45 days",
            "estimated_total_cost": 125000,
            "total_punch_list_items": 1,
        },
        "punch_list": {"punch_list": [{"task": "Confirm the fee schedule", "priority": "HIGH"}]},
        "environmental_screening": {"risk_level": "HIGH"},
    }


def test_emails_do_not_print_an_unstated_permit_total():
    data = _priced()
    html = build_research_result_html(data)
    forward = build_forwardable_result_html(data)
    plain = build_forwardable_plaintext(data)
    for body in (html, forward, plain):
        assert "$125,000" not in body
        assert "125,000" not in body
        assert "No permit total" in body
        assert "Risk score" not in body
    assert "Phase I ESA" in html
    assert "DFW" in html
    assert permit_total_line(data["summary"], {}) .startswith("No permit total")


def test_stated_total_requires_a_real_schedule_url():
    summary = {"estimated_total_cost": 75}
    bare = permit_total_line(summary, {"permit_total_stated": True})
    assert bare.startswith("No permit total")
    stated = permit_total_line(
        summary,
        {
            "permit_total_stated": True,
            "permit_total_source_url": "https://www.plano.gov/fees",
        },
    )
    assert stated == "Permit total on the schedule: $75"


def test_referral_kit_does_not_say_partner_or_fail_stamp():
    blob = "\n".join((MANDATE_ONE_LINER, MANDATE_SCRIPT, MANDATE_EMAIL))
    assert "Partner" not in blob
    assert "PASS" not in blob
    assert "FAIL" not in blob
    assert "HOLD" in blob
    assert "DFW" in blob
