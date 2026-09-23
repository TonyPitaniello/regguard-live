"""IC Project is $1,500 per site — not unlimited runs per email."""

from __future__ import annotations

from ic_project_fulfillment import (
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


def test_order_site_fingerprint_from_address_line():
    o = _order(address="9999 Chapin School Road, Fort Worth, TX 76126")
    fp = order_site_fingerprint(o)
    assert "76126" in fp
    assert "chapin" in fp
