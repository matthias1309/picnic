"""
Unit tests for statistics aggregation logic.

Traces: ARCH-004
Verifies: REQ-004 (AC-004-01, AC-004-05)
"""

from datetime import date, datetime

from backend.models import Product, Receipt, ReceiptItem
from backend.services import stats_service


def _make_receipt(message_id: str, received_date: datetime) -> Receipt:
    return Receipt(
        message_id=message_id,
        received_date=received_date,
        from_address="info@service.picnic.de",
        raw_email_text="raw",
        processed=True,
    )


def _make_item(
    receipt: Receipt, product: Product, quantity: int, unit_price_cents: int
) -> ReceiptItem:
    return ReceiptItem(
        receipt=receipt,
        product=product,
        quantity=quantity,
        unit_price_cents=unit_price_cents,
        line_total_cents=quantity * unit_price_cents,
    )


# TC-004-02: Spending grouped by week (ISO Monday boundary)
def test_spending_grouped_by_week_uses_iso_monday_boundary(db_session):
    """
    Given a receipt with items on Sunday 2026-01-04 and another on Monday 2026-01-05
    When get_spending_over_time(db, granularity="week") is called
    Then two buckets are returned
    And the first bucket's period is "2025-12-29" (the Monday of the week
        containing 2026-01-04)
    And the second bucket's period is "2026-01-05"
    """
    # Arrange
    product = Product(name="Milch")
    sunday_receipt = _make_receipt("r1@picnic.app", datetime(2026, 1, 4, 10, 0))
    monday_receipt = _make_receipt("r2@picnic.app", datetime(2026, 1, 5, 10, 0))
    db_session.add_all([product, sunday_receipt, monday_receipt])
    db_session.add(_make_item(sunday_receipt, product, quantity=1, unit_price_cents=100))
    db_session.add(_make_item(monday_receipt, product, quantity=1, unit_price_cents=200))
    db_session.commit()

    # Act
    buckets = stats_service.get_spending_over_time(db_session, granularity="week")

    # Assert
    assert [period for period, _ in buckets] == ["2025-12-29", "2026-01-05"]
    assert dict(buckets)["2025-12-29"] == 100
    assert dict(buckets)["2026-01-05"] == 200


# TC-014-06: A re-delivered receipt is counted in its delivery month
def test_spent_for_month_uses_delivery_date_over_email_date(db_session):
    """
    Given a receipt re-delivered by email on 2026-06-16 whose delivery_date is
        2026-05-15, with a single 500-cent item
    When get_spent_for_month is called for "2026-05" and "2026-06"
    Then the spend is counted in "2026-05" (the delivery month), not "2026-06"
    """
    # Arrange
    product = Product(name="Milch")
    receipt = _make_receipt("redelivered@picnic.app", datetime(2026, 6, 16, 10, 0))
    receipt.delivery_date = date(2026, 5, 15)
    db_session.add_all([product, receipt])
    db_session.add(_make_item(receipt, product, quantity=1, unit_price_cents=500))
    db_session.commit()

    # Act & Assert
    assert stats_service.get_spent_for_month(db_session, "2026-05") == 500
    assert stats_service.get_spent_for_month(db_session, "2026-06") == 0


# TC-004-10: Summary returns headline figures
def test_summary_returns_headline_figures(db_session):
    """
    Given 2 receipts exist: one in the current month totalling 1000 cents
        with 2 items, one in a previous month totalling 500 cents with 1 item
    And 2 distinct products exist across both receipts
    When get_summary(db, today=<date in the current month>) is called
    Then total_spend_cents is 1500
    And receipt_count is 2
    And distinct_product_count is 2
    And average_basket_cents is 750
    And current_month_spend_cents is 1000
    """
    # Arrange
    milk = Product(name="Milch")
    bread = Product(name="Brot")
    current_month_receipt = _make_receipt("r1@picnic.app", datetime(2026, 6, 10, 10, 0))
    previous_month_receipt = _make_receipt("r2@picnic.app", datetime(2026, 5, 10, 10, 0))
    db_session.add_all([milk, bread, current_month_receipt, previous_month_receipt])
    db_session.add(_make_item(current_month_receipt, milk, quantity=2, unit_price_cents=200))
    db_session.add(_make_item(current_month_receipt, bread, quantity=2, unit_price_cents=300))
    db_session.add(_make_item(previous_month_receipt, milk, quantity=1, unit_price_cents=500))
    db_session.commit()

    # Act
    summary = stats_service.get_summary(db_session, today=date(2026, 6, 15))

    # Assert
    assert summary.total_spend_cents == 1500
    assert summary.receipt_count == 2
    assert summary.distinct_product_count == 2
    assert summary.average_basket_cents == 750
    assert summary.current_month_spend_cents == 1000


# AC-004-06: empty-data handling at the service layer
def test_summary_on_empty_database_returns_zeroes(db_session):
    """
    Given no parsed receipts exist yet
    When get_summary(db, today=...) is called
    Then a well-formed result with all-zero fields is returned (not an error)
    """
    summary = stats_service.get_summary(db_session, today=date(2026, 6, 15))

    assert summary.total_spend_cents == 0
    assert summary.receipt_count == 0
    assert summary.distinct_product_count == 0
    assert summary.average_basket_cents == 0
    assert summary.current_month_spend_cents == 0


def test_spending_over_time_on_empty_database_returns_empty_list(db_session):
    """
    Given no parsed receipts exist yet
    When get_spending_over_time(db, granularity="month") is called
    Then an empty list is returned (not an error)
    """
    buckets = stats_service.get_spending_over_time(db_session, granularity="month")

    assert buckets == []
