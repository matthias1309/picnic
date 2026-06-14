"""
Integration tests for the statistics REST API.

Traces: ARCH-004
Verifies: REQ-004 (AC-004-01, AC-004-02, AC-004-03, AC-004-04, AC-004-05, AC-004-06)
"""

from datetime import datetime

import pytest

from backend.config import settings
from backend.models import PriceHistory, Product, Receipt, ReceiptItem

BASE = "/picnic/api"


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


# TC-004-01: Spending grouped by month
def test_spending_grouped_by_month(client, db_session):
    """
    Given receipts with items exist in January, March, and March of 2026
    When the client requests GET /picnic/api/stats/spending?granularity=month
    Then a 200 response is returned
    And "buckets" contains one entry per month with "period" as "YYYY-MM"
    And the March bucket's total_cents is the sum of both March receipts' items
    And buckets are ordered ascending by period
    """
    # Arrange
    product = Product(name="Milch")
    jan_receipt = _make_receipt("r1@picnic.app", datetime(2026, 1, 15, 10, 0))
    march_receipt_1 = _make_receipt("r2@picnic.app", datetime(2026, 3, 5, 10, 0))
    march_receipt_2 = _make_receipt("r3@picnic.app", datetime(2026, 3, 20, 10, 0))
    db_session.add_all([product, jan_receipt, march_receipt_1, march_receipt_2])
    db_session.add(_make_item(jan_receipt, product, quantity=1, unit_price_cents=100))
    db_session.add(_make_item(march_receipt_1, product, quantity=1, unit_price_cents=200))
    db_session.add(_make_item(march_receipt_2, product, quantity=1, unit_price_cents=300))
    db_session.commit()

    # Act
    response = client.get(f"{BASE}/stats/spending?granularity=month")

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["granularity"] == "month"
    periods = [bucket["period"] for bucket in body["buckets"]]
    assert periods == ["2026-01", "2026-03"]

    march_bucket = next(bucket for bucket in body["buckets"] if bucket["period"] == "2026-03")
    assert march_bucket["total_cents"] == 500


# TC-004-03: Spending date-range filter
def test_spending_date_range_filter(client, db_session):
    """
    Given receipts with items exist on 2026-01-15, 2026-03-15, and 2026-06-15
    When the client requests
         GET /picnic/api/stats/spending?granularity=month&from_date=2026-02-01&to_date=2026-04-01
    Then a 200 response is returned
    And "buckets" contains exactly one entry for "2026-03"
    """
    # Arrange
    product = Product(name="Milch")
    r1 = _make_receipt("r1@picnic.app", datetime(2026, 1, 15, 10, 0))
    r2 = _make_receipt("r2@picnic.app", datetime(2026, 3, 15, 10, 0))
    r3 = _make_receipt("r3@picnic.app", datetime(2026, 6, 15, 10, 0))
    db_session.add_all([product, r1, r2, r3])
    db_session.add(_make_item(r1, product, quantity=1, unit_price_cents=100))
    db_session.add(_make_item(r2, product, quantity=1, unit_price_cents=200))
    db_session.add(_make_item(r3, product, quantity=1, unit_price_cents=300))
    db_session.commit()

    # Act
    response = client.get(
        f"{BASE}/stats/spending?granularity=month&from_date=2026-02-01&to_date=2026-04-01"
    )

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert [bucket["period"] for bucket in body["buckets"]] == ["2026-03"]


# TC-004-04: Top items ranked by quantity descending
def test_top_items_ranked_by_quantity(client, db_session):
    """
    Given "Milch" was bought 5 times total (across receipts) and "Brot" was bought 2 times
    When the client requests GET /picnic/api/stats/top-items
    Then a 200 response is returned
    And the first entry is "Milch" with total_quantity 5
    And the second entry is "Brot" with total_quantity 2
    And each entry includes product_id, product_name, total_quantity, total_spend_cents
    """
    # Arrange
    milk = Product(name="Milch")
    bread = Product(name="Brot")
    r1 = _make_receipt("r1@picnic.app", datetime(2026, 6, 1, 10, 0))
    r2 = _make_receipt("r2@picnic.app", datetime(2026, 6, 2, 10, 0))
    db_session.add_all([milk, bread, r1, r2])
    db_session.add(_make_item(r1, milk, quantity=3, unit_price_cents=100))
    db_session.add(_make_item(r2, milk, quantity=2, unit_price_cents=100))
    db_session.add(_make_item(r1, bread, quantity=2, unit_price_cents=250))
    db_session.commit()

    # Act
    response = client.get(f"{BASE}/stats/top-items")

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body[0]["product_name"] == "Milch"
    assert body[0]["total_quantity"] == 5
    assert body[0]["total_spend_cents"] == 500
    assert "product_id" in body[0]

    assert body[1]["product_name"] == "Brot"
    assert body[1]["total_quantity"] == 2
    assert body[1]["total_spend_cents"] == 500


# TC-004-05: Top items respects the limit parameter
def test_top_items_respects_limit(client, db_session):
    """
    Given 3 distinct products have been purchased
    When the client requests GET /picnic/api/stats/top-items?limit=2
    Then a 200 response is returned
    And exactly 2 entries are returned
    """
    # Arrange
    products = [Product(name=name) for name in ("Milch", "Brot", "Butter")]
    receipt = _make_receipt("r1@picnic.app", datetime(2026, 6, 1, 10, 0))
    db_session.add_all([*products, receipt])
    for product in products:
        db_session.add(_make_item(receipt, product, quantity=1, unit_price_cents=100))
    db_session.commit()

    # Act
    response = client.get(f"{BASE}/stats/top-items?limit=2")

    # Assert
    assert response.status_code == 200
    assert len(response.json()) == 2


# TC-004-06: Price trend returns time series with min/max/avg
def test_price_trend_returns_time_series_with_min_max_avg(client, db_session):
    """
    Given a product has price_history entries of 100, 120, and 110 cents
        on three different dates
    When the client requests GET /picnic/api/stats/price-trend/{product_id}
    Then a 200 response is returned
    And "points" is a time-ordered list of {date, unit_price_cents, quantity}
    And min_price_cents is 100, max_price_cents is 120, avg_price_cents is 110
    """
    # Arrange
    product = Product(name="Milch")
    receipt = _make_receipt("r1@picnic.app", datetime(2026, 1, 1, 10, 0))
    db_session.add_all([product, receipt])
    db_session.flush()
    db_session.add_all(
        [
            PriceHistory(
                product=product,
                receipt_id=receipt.id,
                unit_price_cents=100,
                quantity=1,
                recorded_date=datetime(2026, 1, 1, 10, 0),
            ),
            PriceHistory(
                product=product,
                receipt_id=receipt.id,
                unit_price_cents=120,
                quantity=1,
                recorded_date=datetime(2026, 2, 1, 10, 0),
            ),
            PriceHistory(
                product=product,
                receipt_id=receipt.id,
                unit_price_cents=110,
                quantity=1,
                recorded_date=datetime(2026, 3, 1, 10, 0),
            ),
        ]
    )
    db_session.commit()

    # Act
    response = client.get(f"{BASE}/stats/price-trend/{product.id}")

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert [point["unit_price_cents"] for point in body["points"]] == [100, 120, 110]
    assert body["min_price_cents"] == 100
    assert body["max_price_cents"] == 120
    assert body["avg_price_cents"] == 110


# TC-004-07: Price trend returns 404 for unknown product
def test_price_trend_not_found_returns_404(client):
    """
    Given no product with id 999 exists
    When the client requests GET /picnic/api/stats/price-trend/999
    Then a 404 response is returned
    And the response body is {"detail": "Product not found"}
    """
    response = client.get(f"{BASE}/stats/price-trend/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


# TC-004-08: Budget tracking for a given month
def test_budget_tracking_for_month(client, db_session, monkeypatch):
    """
    Given MONTHLY_BUDGET_CENTS is configured to 30000
    And receipts with items totalling 12000 cents exist in June 2026
    When the client requests GET /picnic/api/stats/budget?month=2026-06
    Then a 200 response is returned
    And budget_cents is 30000, spent_cents is 12000, remaining_cents is 18000
    """
    # Arrange
    monkeypatch.setattr(settings, "monthly_budget_cents", 30000)
    product = Product(name="Milch")
    receipt = _make_receipt("r1@picnic.app", datetime(2026, 6, 10, 10, 0))
    db_session.add_all([product, receipt])
    db_session.add(_make_item(receipt, product, quantity=1, unit_price_cents=12000))
    db_session.commit()

    # Act
    response = client.get(f"{BASE}/stats/budget?month=2026-06")

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "month": "2026-06",
        "budget_cents": 30000,
        "spent_cents": 12000,
        "remaining_cents": 18000,
    }


# TC-004-09: Budget rejects a malformed month parameter
def test_budget_rejects_malformed_month(client):
    """
    Given any state of the database
    When the client requests GET /picnic/api/stats/budget?month=not-a-month
    Then a 422 response is returned
    And the response body has a "detail" field
    """
    response = client.get(f"{BASE}/stats/budget?month=not-a-month")

    assert response.status_code == 422
    assert "detail" in response.json()


# TC-004-11: Empty-data handling across all statistics endpoints
@pytest.mark.parametrize(
    "path",
    [
        "/stats/spending",
        "/stats/top-items",
        "/stats/budget?month=2026-06",
        "/stats/summary",
    ],
)
def test_empty_database_returns_well_formed_results(client, path):
    """
    Given no parsed receipts, products, or price history exist
    When any statistics endpoint is called
    Then a 200 response is returned with a well-formed empty/zeroed result
    """
    response = client.get(f"{BASE}{path}")

    assert response.status_code == 200


def test_empty_database_spending_has_no_buckets(client):
    response = client.get(f"{BASE}/stats/spending")
    assert response.json()["buckets"] == []


def test_empty_database_top_items_is_empty_list(client):
    response = client.get(f"{BASE}/stats/top-items")
    assert response.json() == []


def test_empty_database_budget_has_zero_spend(client, monkeypatch):
    monkeypatch.setattr(settings, "monthly_budget_cents", 30000)
    response = client.get(f"{BASE}/stats/budget?month=2026-06")
    body = response.json()
    assert body["spent_cents"] == 0
    assert body["remaining_cents"] == 30000


def test_empty_database_summary_is_all_zero(client):
    response = client.get(f"{BASE}/stats/summary")
    body = response.json()
    assert body == {
        "total_spend_cents": 0,
        "receipt_count": 0,
        "distinct_product_count": 0,
        "average_basket_cents": 0,
        "current_month_spend_cents": 0,
    }
