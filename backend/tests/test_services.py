"""
Integration tests for the receipt parsing service.

Traces: ARCH-002
Verifies: REQ-002 (AC-002-01, AC-002-02, AC-002-03, AC-002-04, AC-002-05, AC-002-06)
"""

import logging
from datetime import date, datetime

from backend.config import settings
from backend.models import BudgetSetting, PriceHistory, Product, Receipt, ReceiptItem
from backend.services import budget_service
from backend.services.receipt_service import ParseSummary, delete_receipt, parse_pending_receipts

RECEIVED_DATE = datetime(2026, 6, 1, 20, 45)


def _make_pending_receipt(message_id: str, raw_email_text: str) -> Receipt:
    return Receipt(
        message_id=message_id,
        received_date=RECEIVED_DATE,
        from_address="info@service.picnic.de",
        raw_email_text=raw_email_text,
        processed=False,
    )


# TC-002-07: Parsing a pending receipt stores items, products, and price history
def test_parse_pending_receipts_stores_items_products_and_price_history(
    db_session, make_raw_email, picnic_receipt_html
):
    """
    Given a Receipt with processed=False and raw_email_text containing the invoice HTML
    When parse_pending_receipts(db) is called
    Then 5 receipt_items are created, linked to the receipt
    And a matching product is created for each distinct item name
    And a price_history row is recorded for each item with the receipt's received_date
    And the receipt's processed flag is set to True
    """
    # Arrange
    receipt = _make_pending_receipt("bon-1@picnic.app", make_raw_email(picnic_receipt_html))
    db_session.add(receipt)
    db_session.commit()

    # Act
    summary = parse_pending_receipts(db_session)

    # Assert
    assert summary == ParseSummary(parsed=1, failed=0, items=5)

    db_session.refresh(receipt)
    assert receipt.processed is True

    items = db_session.query(ReceiptItem).filter_by(receipt_id=receipt.id).all()
    assert len(items) == 5

    products = db_session.query(Product).all()
    assert len(products) == 5
    assert {product.name for product in products} == {item.product.name for item in items}

    price_history = db_session.query(PriceHistory).all()
    assert len(price_history) == 5
    assert all(entry.recorded_date == RECEIVED_DATE for entry in price_history)


# TC-013-03: Order numbers parsed from the invoice are persisted on receipt items
def test_parse_pending_receipts_persists_order_numbers(
    db_session, make_raw_email, picnic_receipt_current_html
):
    """
    Given a pending receipt in the current invoice format with two Bestellnr sections
    When parse_pending_receipts(db) is called
    Then each stored receipt_item carries its parsed order_number
    """
    # Arrange
    receipt = _make_pending_receipt(
        "bon-orders@picnic.app", make_raw_email(picnic_receipt_current_html)
    )
    db_session.add(receipt)
    db_session.commit()

    # Act
    parse_pending_receipts(db_session)

    # Assert
    order_by_name = {
        item.product.name: item.order_number
        for item in db_session.query(ReceiptItem).filter_by(receipt_id=receipt.id).all()
    }
    assert order_by_name["Testprodukt Eins"] == "209-521-1175"
    assert order_by_name["Testprodukt Zwei"] == "209-521-1175"
    assert order_by_name["Testprodukt Drei"] == "204-701-1435"


# TC-014-04: The parsed delivery date dates the receipt and its price history
def test_parse_pending_receipts_dates_by_delivery_date(
    db_session, make_raw_email, picnic_receipt_current_html
):
    """
    Given a pending receipt whose email Date header is 2026-06-01 and whose body
    states a delivery of "Freitag 15 Mai 2026"
    When parse_pending_receipts(db) runs
    Then Receipt.delivery_date == date(2026, 5, 15)
    And every PriceHistory.recorded_date for that receipt is 2026-05-15
    """
    # Arrange
    receipt = _make_pending_receipt(
        "bon-delivery@picnic.app", make_raw_email(picnic_receipt_current_html)
    )
    db_session.add(receipt)
    db_session.commit()

    # Act
    parse_pending_receipts(db_session)

    # Assert
    db_session.refresh(receipt)
    assert receipt.delivery_date == date(2026, 5, 15)

    price_history = db_session.query(PriceHistory).filter_by(receipt_id=receipt.id).all()
    assert price_history
    assert all(entry.recorded_date.date() == date(2026, 5, 15) for entry in price_history)


# TC-014-05: Without a delivery sentence, the email date is used as fallback
def test_parse_pending_receipts_falls_back_to_email_date(
    db_session, make_raw_email, picnic_receipt_html
):
    """
    Given a pending receipt whose body has no delivery sentence and whose email
    Date header is 2026-06-01
    When parse_pending_receipts(db) runs
    Then Receipt.delivery_date is None
    And every PriceHistory.recorded_date falls back to the received_date
    """
    # Arrange
    receipt = _make_pending_receipt("bon-fallback@picnic.app", make_raw_email(picnic_receipt_html))
    db_session.add(receipt)
    db_session.commit()

    # Act
    parse_pending_receipts(db_session)

    # Assert
    db_session.refresh(receipt)
    assert receipt.delivery_date is None

    price_history = db_session.query(PriceHistory).filter_by(receipt_id=receipt.id).all()
    assert price_history
    assert all(entry.recorded_date == RECEIVED_DATE for entry in price_history)


# TC-002-08: Existing products are reused by exact name
def test_parse_pending_receipts_reuses_existing_product_by_name(
    db_session, make_raw_email, picnic_receipt_html
):
    """
    Given a Product "Max Premium Pistazien" already exists
    And a pending receipt contains an item with that exact name
    When parse_pending_receipts(db) is called
    Then no duplicate Product row is created
    And the new receipt_item references the existing product
    """
    # Arrange
    existing_product = Product(name="Max Premium Pistazien")
    db_session.add(existing_product)
    db_session.commit()

    receipt = _make_pending_receipt("bon-2@picnic.app", make_raw_email(picnic_receipt_html))
    db_session.add(receipt)
    db_session.commit()

    # Act
    parse_pending_receipts(db_session)

    # Assert
    products = db_session.query(Product).filter_by(name="Max Premium Pistazien").all()
    assert len(products) == 1

    pistazien_item = (
        db_session.query(ReceiptItem)
        .join(Product)
        .filter(Product.name == "Max Premium Pistazien")
        .one()
    )
    assert pistazien_item.product_id == existing_product.id


# TC-002-09: A malformed receipt is skipped without affecting others
def test_parse_pending_receipts_skips_malformed_receipt(
    db_session, make_raw_email, picnic_receipt_html, picnic_receipt_malformed_html, caplog
):
    """
    Given two pending receipts: one with valid invoice HTML, one with malformed HTML
    When parse_pending_receipts(db) is called
    Then the valid receipt is parsed, stored, and marked processed=True
    And the malformed receipt remains processed=False
    And the parse failure is logged with the receipt id
    And ParseSummary reports parsed=1, failed=1
    """
    # Arrange
    valid_receipt = _make_pending_receipt("bon-3@picnic.app", make_raw_email(picnic_receipt_html))
    malformed_receipt = _make_pending_receipt(
        "bon-4@picnic.app", make_raw_email(picnic_receipt_malformed_html)
    )
    db_session.add_all([valid_receipt, malformed_receipt])
    db_session.commit()

    # Act
    with caplog.at_level(logging.ERROR):
        summary = parse_pending_receipts(db_session)

    # Assert
    assert summary == ParseSummary(parsed=1, failed=1, items=5)

    db_session.refresh(valid_receipt)
    db_session.refresh(malformed_receipt)
    assert valid_receipt.processed is True
    assert malformed_receipt.processed is False

    assert any(str(malformed_receipt.id) in record.message for record in caplog.records)


# TC-002-10: Reconciliation warning on total mismatch
def test_parse_pending_receipts_warns_on_total_mismatch(
    db_session, make_raw_email, picnic_receipt_html, caplog
):
    """
    Given a pending receipt whose computed line-item sum differs from the stated total
    When parse_pending_receipts(db) is called
    Then a warning is logged containing the receipt id, computed total, and stated total
    And the receipt is still marked processed=True (reconciliation is informational only)
    """
    # Arrange
    mismatched_html = picnic_receipt_html.replace(
        "<strong>13</strong><br>", "<strong>99</strong><br>"
    )
    receipt = _make_pending_receipt("bon-5@picnic.app", make_raw_email(mismatched_html))
    db_session.add(receipt)
    db_session.commit()

    # Act
    with caplog.at_level(logging.WARNING):
        summary = parse_pending_receipts(db_session)

    # Assert
    assert summary == ParseSummary(parsed=1, failed=0, items=5)

    db_session.refresh(receipt)
    assert receipt.processed is True

    warning_messages = [record.message for record in caplog.records]
    assert any(
        str(receipt.id) in message and "1320" in message and "9920" in message
        for message in warning_messages
    )


# TC-002-11: No pending receipts is a no-op
def test_parse_pending_receipts_is_noop_when_nothing_pending(db_session):
    """
    Given no receipts with processed=False exist
    When parse_pending_receipts(db) is called
    Then ParseSummary(parsed=0, failed=0, items=0) is returned
    And no exception is raised
    """
    # Act
    summary = parse_pending_receipts(db_session)

    # Assert
    assert summary == ParseSummary(parsed=0, failed=0, items=0)


# TC-009-01: delete_receipt removes a receipt, its items, and its price history
def test_delete_receipt_removes_receipt_items_and_price_history(db_session):
    """
    Given a receipt exists with 2 line items and 2 price_history entries
    When receipt_service.delete_receipt(db, receipt_id) is called
    Then it returns True
    And the receipt no longer exists in the database
    And its receipt_items no longer exist
    And its price_history entries no longer exist
    And the referenced products are not deleted
    """
    # Arrange
    milk = Product(name="Milch")
    bread = Product(name="Brot")
    receipt = Receipt(
        message_id="bon-1@picnic.app",
        received_date=RECEIVED_DATE,
        from_address="info@service.picnic.de",
        raw_email_text="raw",
        processed=True,
    )
    db_session.add_all([milk, bread, receipt])
    db_session.flush()
    db_session.add_all(
        [
            ReceiptItem(
                receipt=receipt,
                product=milk,
                quantity=2,
                unit_price_cents=100,
                line_total_cents=200,
            ),
            ReceiptItem(
                receipt=receipt,
                product=bread,
                quantity=1,
                unit_price_cents=250,
                line_total_cents=250,
            ),
            PriceHistory(
                product=milk,
                receipt_id=receipt.id,
                unit_price_cents=100,
                quantity=2,
                recorded_date=RECEIVED_DATE,
            ),
            PriceHistory(
                product=bread,
                receipt_id=receipt.id,
                unit_price_cents=250,
                quantity=1,
                recorded_date=RECEIVED_DATE,
            ),
        ]
    )
    db_session.commit()
    receipt_id = receipt.id

    # Act
    result = delete_receipt(db_session, receipt_id)

    # Assert
    assert result is True
    assert db_session.query(Receipt).filter_by(id=receipt_id).first() is None
    assert db_session.query(ReceiptItem).filter_by(receipt_id=receipt_id).count() == 0
    assert db_session.query(PriceHistory).filter_by(receipt_id=receipt_id).count() == 0
    assert db_session.query(Product).filter(Product.id.in_([milk.id, bread.id])).count() == 2


# TC-009-02: delete_receipt returns False for a non-existent receipt
def test_delete_receipt_returns_false_when_not_found(db_session):
    """
    Given no receipt with id 999 exists
    When receipt_service.delete_receipt(db, 999) is called
    Then it returns False
    And no rows are deleted
    """
    # Act
    result = delete_receipt(db_session, 999)

    # Assert
    assert result is False


# TC-011-01: get_monthly_budget_cents falls back to the .env default when unset
def test_get_monthly_budget_cents_falls_back_to_env_default(db_session, monkeypatch):
    """
    Given no budget_settings row exists
    And settings.monthly_budget_cents is 30000
    When budget_service.get_monthly_budget_cents(db) is called
    Then it returns 30000
    """
    # Arrange
    monkeypatch.setattr(settings, "monthly_budget_cents", 30000)

    # Act
    result = budget_service.get_monthly_budget_cents(db_session)

    # Assert
    assert result == 30000


# TC-011-02: set_monthly_budget_cents persists a new value
def test_set_monthly_budget_cents_persists_new_value(db_session, monkeypatch):
    """
    Given no budget_settings row exists
    When budget_service.set_monthly_budget_cents(db, 35000) is called
    Then it returns 35000
    And budget_service.get_monthly_budget_cents(db) subsequently returns 35000
      (independent of settings.monthly_budget_cents)
    """
    # Arrange
    monkeypatch.setattr(settings, "monthly_budget_cents", 30000)

    # Act
    result = budget_service.set_monthly_budget_cents(db_session, 35000)

    # Assert
    assert result == 35000
    assert budget_service.get_monthly_budget_cents(db_session) == 35000


# TC-011-03: set_monthly_budget_cents updates an existing value
def test_set_monthly_budget_cents_updates_existing_value(db_session):
    """
    Given budget_service.set_monthly_budget_cents(db, 35000) was already called
    When budget_service.set_monthly_budget_cents(db, 40000) is called
    Then it returns 40000
    And budget_service.get_monthly_budget_cents(db) returns 40000
    And only one row exists in budget_settings
    """
    # Arrange
    budget_service.set_monthly_budget_cents(db_session, 35000)

    # Act
    result = budget_service.set_monthly_budget_cents(db_session, 40000)

    # Assert
    assert result == 40000
    assert budget_service.get_monthly_budget_cents(db_session) == 40000
    assert db_session.query(BudgetSetting).count() == 1
