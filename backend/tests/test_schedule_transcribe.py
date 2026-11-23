"""Scraped markdown becomes the fee rows the pack already prints."""

from habit_ladder_shape import estimator_forward_punch
from ic_buyer_brief import DALLAS_FEE_PDF
from schedule_transcribe import apply_transcribed_schedule, transcribe_page


PHOENIX = "https://www.phoenix.gov/development/fees/commercial-fee-schedule.pdf"
HOME = "https://www.phoenix.gov/"


def test_base_is_kept_and_the_area_total_is_blank():
    text = "\n".join(
        [
            "Application processing fee $40.50",
            "The building permit total depends on building area.",
            "Building permit total is priced from square feet.",
        ]
    )
    rows = transcribe_page(text, PHOENIX, city="Phoenix")
    stated = [row for row in rows if row["amount_usd"] is not None]
    blank = [row for row in rows if row["amount_usd"] is None]
    assert stated[0]["amount_usd"] == 40.50
    assert blank
    assert "$" not in blank[0]["note"]
    assert blank[0]["status"] == "confirm-on-schedule"
    assert all(row["amount_usd"] != 40.50 or "total" not in row["label"].lower() for row in rows)


def test_deposits_are_not_added_into_a_permit_total():
    text = "\n".join(
        [
            "Plan review deposit, circulation required $291",
            "Plan review deposit, no circulation $113",
            "Application fee $33.08",
        ]
    )
    rows = transcribe_page(text, PHOENIX, city="Phoenix")
    amounts = [row["amount_usd"] for row in rows]
    assert 33.08 in amounts
    assert 291 in amounts
    assert 113 in amounts
    assert 291 + 113 + 33.08 not in amounts
    assert not any("total" in str(row["label"]).lower() and row["amount_usd"] for row in rows)


def test_a_rate_is_not_a_permit_total():
    rows = transcribe_page(
        "Building permit is $0.26 per square foot of building area.",
        PHOENIX,
        city="Phoenix",
    )
    assert all(row["amount_usd"] is None for row in rows)


def test_a_beachhead_fee_document_does_not_price_another_city():
    rows = transcribe_page(
        "Commercial alteration minimum permit fee is $175. Additional inspection $125.",
        DALLAS_FEE_PDF,
        city="Phoenix",
    )
    assert rows == []


def test_homepage_prints_no_dollar():
    rows = transcribe_page("Permit fee $500", HOME, city="Phoenix")
    assert rows == []


def test_no_figure_leaves_a_blank_line_and_the_full_pdf_url():
    analysis = {
        "project_info": {"city": "Phoenix", "state": "AZ"},
        "site_finder": {
            "rows": [
                {"job": "fee_schedule", "url": PHOENIX},
                {"job": "permit_application", "url": "https://www.phoenix.gov/development/apply"},
            ]
        },
        "shortlist_pages": [
            {
                "url": "https://www.phoenix.gov/development/apply",
                "markdown": "File the commercial building permit at the building permit desk. Call 602-262-7811.",
            }
        ],
    }
    assert apply_transcribed_schedule(analysis, city="Phoenix") is True
    fees = analysis["fee_card"]["fees"]
    assert fees[0]["amount_usd"] is None
    assert "$" not in fees[0]["note"]
    assert "A blank line has no dollar." in fees[0]["note"]
    assert analysis["ahj_card"]["fees_url"] == PHOENIX
    assert " / " not in analysis["ahj_card"]["fees_url"]
    owners = [clock["owner"] for clock in analysis["parallel_clocks"]["clocks"]]
    assert any("602-262-7811" in owner for owner in owners)
    assert all("555" not in owner for owner in owners)


def test_estimator_uses_the_permit_sentence_and_no_dollar():
    analysis = {
        "project_info": {"city": "Phoenix", "state": "AZ"},
        "shortlist_pages": [
            {
                "url": "https://www.phoenix.gov/development/commercial-permits",
                "markdown": "The building permit is issued before a trade permit can be applied for. Fee $40.",
            }
        ],
    }
    punch = estimator_forward_punch(analysis)[0]
    assert "issued before a trade" in punch["task"].lower()
    assert "$" not in punch["task"]
    assert punch["source_url"].startswith("https://")
    assert punch["owner"] == "Permit runner"


def test_estimator_without_a_sequence_says_none_is_on_file():
    analysis = {"project_info": {"city": "Phoenix", "state": "AZ"}}
    punch = estimator_forward_punch(analysis)[0]
    assert punch["task"].startswith("No permit sequence is on file")
    assert punch["source_url"] if False else punch["verified"] is False


def test_beachhead_schedule_is_not_replaced():
    analysis = {"fee_card": {"fees": [{"label": "kept", "amount_usd": 175}]}}
    assert apply_transcribed_schedule(analysis, city="Dallas") is False
    assert analysis["fee_card"]["fees"][0]["label"] == "kept"
