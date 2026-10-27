"""IC Project is $1,500 per site — not unlimited runs per email."""

from __future__ import annotations

from ic_project_fulfillment import (
    counsel_site_label,
    evaluate_ic_site_access,
    order_site_fingerprint,
    pdfs_are_ready,
    site_fingerprint,
)


def _order(**kwargs):
    base = {
        "order_id": kwargs.get("order_id", "ord-1"),
        "tier": kwargs.get("tier", "ic_project"),
        "email": "buyer@example.com",
        "pdfs": kwargs.get("pdfs"),
        "site_address": kwargs.get("site_address", ""),
        "site_city": kwargs.get("site_city", ""),
        "site_state": kwargs.get("site_state", ""),
        "site_zip": kwargs.get("site_zip", ""),
        "site_label": kwargs.get("site_label", ""),
        "address": kwargs.get("address", ""),
    }
    return base


def test_site_fingerprint_stable():
    a = site_fingerprint(
        address="9999 Chapin School Road",
        city="Fort Worth",
        state="TX",
        zip_code="76126",
    )
    b = site_fingerprint(
        address="9999  Chapin School Road,",
        city="Ft Worth",
        state="tx",
        zip_code="76126-1234",
    )
    assert a == b


def test_unused_ic_project_binds_any_first_site(monkeypatch):
    orders = [_order(pdfs=[{"type": "ic_package", "name": "Preparing…", "url": "", "status": "preparing"}])]

    monkeypatch.setattr(
        "order_service.get_raw_orders_for_email",
        lambda email: orders,
    )
    access = evaluate_ic_site_access(
        "buyer@example.com",
        address="9999 Chapin School Road",
        city="Fort Worth",
        state="TX",
        zip_code="76126",
    )
    assert access["allowed"] is True
    assert access["mode"] == "bind_unused"


def test_fulfilled_ic_project_blocks_different_site(monkeypatch):
    ready_pdfs = [
        {
            "type": "ic_package",
            "name": "IC Diligence Package",
            "url": "https://api.regguardagent.com/orders/ord-1/pdfs/ic_package?email=x",
            "status": "ready",
        }
    ]
    orders = [
        _order(
            pdfs=ready_pdfs,
            site_address="9999 Chapin School Road",
            site_city="Fort Worth",
            site_state="TX",
            site_zip="76126",
            site_label="9999 Chapin School Road, Fort Worth, TX 76126",
        )
    ]
    assert pdfs_are_ready(ready_pdfs)
    monkeypatch.setattr("order_service.get_raw_orders_for_email", lambda email: orders)

    same = evaluate_ic_site_access(
        "buyer@example.com",
        address="9999 Chapin School Road",
        city="Fort Worth",
        state="TX",
        zip_code="76126",
    )
    assert same["allowed"] is True
    assert same["mode"] == "same_site_refresh"

    other = evaluate_ic_site_access(
        "buyer@example.com",
        address="100 Main Street",
        city="Plano",
        state="TX",
        zip_code="75074",
    )
    assert other["allowed"] is False
    assert other["mode"] == "need_purchase"


def test_ic_annual_allows_new_site(monkeypatch):
    orders = [
        _order(
            tier="ic_annual",
            pdfs=[
                {
                    "type": "ic_package",
                    "name": "IC Diligence Package",
                    "url": "https://api.regguardagent.com/orders/ord-1/pdfs/ic_package?email=x",
                    "status": "ready",
                }
            ],
            site_address="1 Old St",
            site_city="Dallas",
            site_state="TX",
            site_zip="75201",
        )
    ]
    monkeypatch.setattr("order_service.get_raw_orders_for_email", lambda email: orders)
    access = evaluate_ic_site_access(
        "buyer@example.com",
        address="100 Main Street",
        city="Plano",
        state="TX",
        zip_code="75074",
    )
    assert access["allowed"] is True
    assert access["mode"] == "annual"


def test_label_only_order_keeps_that_address(monkeypatch):
    """The address on the order is the site. A later address on the email does not move it."""
    ready_pdfs = [
        {
            "type": "ic_package",
            "name": "IC Diligence Package",
            "url": "https://api.example/orders/ord-1/pdfs/ic_package",
            "status": "ready",
        }
    ]
    orders = [
        _order(
            pdfs=ready_pdfs,
            site_zip="",
            site_label="2300 Chelsea Blvd, Allen, TX 75013",
            address="2300 Chelsea Blvd, Allen, TX 75013",
        )
    ]
    monkeypatch.setattr("order_service.get_raw_orders_for_email", lambda email: orders)
    access = evaluate_ic_site_access(
        "buyer@example.com",
        address="1000 Louisiana Street",
        city="Houston",
        state="TX",
        zip_code="77002",
    )
    assert access["allowed"] is False
    assert access["mode"] == "need_purchase"
    assert "75013" in str(access.get("bound_site") or "")


def test_unready_order_keeps_its_address(monkeypatch):
    orders = [
        _order(
            pdfs=[{"type": "ic_package", "name": "Preparing", "url": "", "status": "preparing"}],
            site_address="1000 Louisiana Street",
            site_city="Houston",
            site_state="TX",
            site_zip="77002",
            site_label="1000 Louisiana Street, Houston, TX 77002",
        )
    ]
    monkeypatch.setattr("order_service.get_raw_orders_for_email", lambda email: orders)
    other = evaluate_ic_site_access(
        "buyer@example.com",
        address="112 E Pecan Street",
        city="San Antonio",
        state="TX",
        zip_code="78205",
    )
    assert other["allowed"] is False
    assert other["mode"] == "need_purchase"
    same = evaluate_ic_site_access(
        "buyer@example.com",
        address="1000 Louisiana Street",
        city="Houston",
        state="TX",
        zip_code="77002",
    )
    assert same["allowed"] is True
    assert same["mode"] == "same_site_refresh"


def test_each_order_matches_only_its_address(monkeypatch):
    ready = [{"type": "ic_package", "name": "IC", "url": "https://api.example/orders/x/pdfs/ic_package", "status": "ready"}]
    orders = [
        _order(
            order_id="hou",
            pdfs=ready,
            site_address="1000 Louisiana Street",
            site_city="Houston",
            site_state="TX",
            site_zip="77002",
            site_label="1000 Louisiana Street, Houston, TX 77002",
        ),
        _order(
            order_id="sa",
            pdfs=ready,
            site_address="112 E Pecan Street",
            site_city="San Antonio",
            site_state="TX",
            site_zip="78205",
            site_label="112 E Pecan Street, San Antonio, TX 78205",
        ),
    ]
    monkeypatch.setattr("order_service.get_raw_orders_for_email", lambda email: orders)
    pecan = evaluate_ic_site_access(
        "buyer@example.com",
        address="112 E Pecan Street",
        city="San Antonio",
        state="TX",
        zip_code="78205",
    )
    assert pecan["order_id"] == "sa"
    louisiana = evaluate_ic_site_access(
        "buyer@example.com",
        address="1000 Louisiana Street",
        city="Houston",
        state="TX",
        zip_code="77002",
    )
    assert louisiana["order_id"] == "hou"


def test_stored_site_zip_still_blocks_a_different_zip(monkeypatch):
    ready_pdfs = [
        {
            "type": "ic_package",
            "name": "IC Diligence Package",
            "url": "https://api.example/orders/ord-1/pdfs/ic_package",
            "status": "ready",
        }
    ]
    orders = [
        _order(
            pdfs=ready_pdfs,
            site_address="1000 Louisiana Street",
            site_city="Houston",
            site_state="TX",
            site_zip="77002",
            site_label="1000 Louisiana Street, Houston, TX 77002",
        )
    ]
    monkeypatch.setattr("order_service.get_raw_orders_for_email", lambda email: orders)
    other = evaluate_ic_site_access(
        "buyer@example.com",
        address="2300 Chelsea Blvd",
        city="Allen",
        state="TX",
        zip_code="75013",
    )
    assert other["allowed"] is False
    assert other["mode"] == "need_purchase"


def test_fingerprint_uses_stored_site_zip_not_stale_label():
    o = _order(
        site_address="1000 Louisiana Street",
        site_city="Houston",
        site_state="TX",
        site_zip="77002",
        site_label="2300 Chelsea Blvd, Allen, TX 75013",
        address="2300 Chelsea Blvd, Allen, TX 75013",
    )
    fp = order_site_fingerprint(o)
    assert "77002" in fp
    assert "75013" not in fp


def test_saved_research_zip_blocks_a_different_site_after_restart(monkeypatch):
    """The address line on the order is the site. A research blob on the email is not."""
    ready_pdfs = [
        {
            "type": "ic_package",
            "name": "IC Diligence Package",
            "url": "https://api.example/orders/ord-1/pdfs/ic_package",
            "status": "ready",
        }
    ]
    orders = [
        _order(
            pdfs=ready_pdfs,
            site_zip="",
            address="1000 Louisiana Street, Houston, TX 77002",
            site_label="1000 Louisiana Street, Houston, TX 77002",
        )
    ]
    orders[0]["analysis_json"] = {
        "project_info": {
            "address": "112 E Pecan Street",
            "city": "San Antonio",
            "state": "TX",
            "zip": "78205",
        }
    }
    monkeypatch.setattr("order_service.get_raw_orders_for_email", lambda email: orders)
    access = evaluate_ic_site_access(
        "buyer@example.com",
        address="112 E Pecan Street",
        city="San Antonio",
        state="TX",
        zip_code="78205",
    )
    assert access["allowed"] is False
    assert access["mode"] == "need_purchase"
    assert "77002" in str(access.get("bound_site") or "") or "Louisiana" in str(access.get("bound_site") or "")


def test_counsel_site_label_keeps_the_entered_zip_once():
    label = counsel_site_label(
        "1000 Louisiana Street, Houston, TX 77002",
        "Houston",
        "TX",
        "77002",
    )
    assert label == "1000 Louisiana Street, Houston, TX 77002"
    assert label.count("77002") == 1


def test_order_site_fingerprint_from_address_line():
    o = _order(address="9999 Chapin School Road, Fort Worth, TX 76126")
    fp = order_site_fingerprint(o)
    assert "76126" in fp
    assert "chapin" in fp
