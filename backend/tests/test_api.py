"""
Integration tests for the read-only REST API (receipts & products).

Traces: ARCH-003
Verifies: REQ-003 (AC-003-01, AC-003-02, AC-003-03, AC-003-04, AC-003-05, AC-003-06)
"""

from datetime import datetime

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


# TC-003-01: List receipts returns paginated, descending-by-date results
def test_list_receipts_returns_descending_by_date(client, db_session):
    """
    Given three parsed receipts exist with different received_date values
    When the client requests GET /picnic/api/receipts
    Then a 200 response is returned
    And the response contains an "items" list of all three receipts, newest first
    And each entry includes id, received_date, from_address, item_count, and total_cents
    And the response includes "total", "limit", and "offset"
    """
    # Arrange
    product = Product(name="Milch")
    r1 = _make_receipt("r1@picnic.app", datetime(2026, 1, 1, 10, 0))
    r2 = _make_receipt("r2@picnic.app", datetime(2026, 3, 1, 10, 0))
    r3 = _make_receipt("r3@picnic.app", datetime(2026, 6, 1, 10, 0))
    db_session.add_all([product, r1, r2, r3])
    db_session.add(_make_item(r2, product, quantity=2, unit_price_cents=100))
    db_session.commit()

    # Act
    response = client.get(f"{BASE}/receipts")

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == [r3.id, r2.id, r1.id]
    assert body["total"] == 3
    assert body["limit"] == 20
    assert body["offset"] == 0

    r2_entry = next(item for item in body["items"] if item["id"] == r2.id)
    assert r2_entry["from_address"] == "info@service.picnic.de"
    assert r2_entry["item_count"] == 1
    assert r2_entry["total_cents"] == 200

    r1_entry = next(item for item in body["items"] if item["id"] == r1.id)
    assert r1_entry["item_count"] == 0
    assert r1_entry["total_cents"] == 0


# TC-003-02: Get a single receipt with items
def test_get_receipt_returns_items(client, db_session):
    """
    Given a receipt with id X exists with 2 items
    When the client requests GET /picnic/api/receipts/{X}
    Then a 200 response is returned
    And the response includes id, received_date, from_address, total_cents
    And "items" contains 2 entries, each with product_name, quantity,
        unit_price_cents, and line_total_cents
    """
    # Arrange
    receipt = _make_receipt("r1@picnic.app", datetime(2026, 6, 1, 10, 0))
    milk = Product(name="Milch")
    bread = Product(name="Brot")
    db_session.add_all([receipt, milk, bread])
    db_session.add(_make_item(receipt, milk, quantity=2, unit_price_cents=100))
    db_session.add(_make_item(receipt, bread, quantity=1, unit_price_cents=250))
    db_session.commit()

    # Act
    response = client.get(f"{BASE}/receipts/{receipt.id}")

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == receipt.id
    assert body["from_address"] == "info@service.picnic.de"
    assert body["total_cents"] == 450

    items = sorted(body["items"], key=lambda item: item["product_name"])
    assert items[0] == {
        "product_name": "Brot",
        "quantity": 1,
        "unit_price_cents": 250,
        "line_total_cents": 250,
    }
    assert items[1] == {
        "product_name": "Milch",
        "quantity": 2,
        "unit_price_cents": 100,
        "line_total_cents": 200,
    }


# TC-003-03: Get a single receipt returns 404 when not found
def test_get_receipt_not_found_returns_404(client):
    """
    Given no receipt with id 999 exists
    When the client requests GET /picnic/api/receipts/999
    Then a 404 response is returned
    And the response body is {"detail": "Receipt not found"}
    """
    response = client.get(f"{BASE}/receipts/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Receipt not found"}


# TC-003-04: List products with purchase counts
def test_list_products_includes_purchase_counts(client, db_session):
    """
    Given two products exist, one purchased twice and one purchased once
    When the client requests GET /picnic/api/products
    Then a 200 response is returned
    And each product entry includes id, name, and purchase_count
    And purchase_count reflects the number of receipt_items referencing it
    And products are ordered by name ascending
    """
    # Arrange
    apple = Product(name="Apfel")
    banana = Product(name="Banane")
    receipt = _make_receipt("r1@picnic.app", datetime(2026, 6, 1, 10, 0))
    db_session.add_all([apple, banana, receipt])
    db_session.add(_make_item(receipt, apple, quantity=1, unit_price_cents=50))
    db_session.add(_make_item(receipt, apple, quantity=1, unit_price_cents=50))
    db_session.add(_make_item(receipt, banana, quantity=1, unit_price_cents=30))
    db_session.commit()

    # Act
    response = client.get(f"{BASE}/products")

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert [product["name"] for product in body] == ["Apfel", "Banane"]

    apple_entry = next(product for product in body if product["name"] == "Apfel")
    banana_entry = next(product for product in body if product["name"] == "Banane")
    assert apple_entry["id"] == apple.id
    assert apple_entry["purchase_count"] == 2
    assert banana_entry["purchase_count"] == 1


# TC-003-05: Get product price history
def test_get_product_price_history_is_time_ordered(client, db_session):
    """
    Given a product with id Y has 2 price_history entries on different dates
    When the client requests GET /picnic/api/products/{Y}/price-history
    Then a 200 response is returned
    And the response includes product_id and product_name
    And "points" is a time-ordered list of {date, unit_price_cents, quantity}
        ascending by date
    """
    # Arrange
    product = Product(name="Milch")
    receipt1 = _make_receipt("r1@picnic.app", datetime(2026, 1, 1, 10, 0))
    receipt2 = _make_receipt("r2@picnic.app", datetime(2026, 3, 1, 10, 0))
    db_session.add_all([product, receipt1, receipt2])
    db_session.flush()
    db_session.add(
        PriceHistory(
            product=product,
            receipt_id=receipt1.id,
            unit_price_cents=100,
            quantity=1,
            recorded_date=datetime(2026, 3, 1, 10, 0),
        )
    )
    db_session.add(
        PriceHistory(
            product=product,
            receipt_id=receipt2.id,
            unit_price_cents=110,
            quantity=2,
            recorded_date=datetime(2026, 1, 1, 10, 0),
        )
    )
    db_session.commit()

    # Act
    response = client.get(f"{BASE}/products/{product.id}/price-history")

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["product_id"] == product.id
    assert body["product_name"] == "Milch"
    assert len(body["points"]) == 2
    assert body["points"][0]["unit_price_cents"] == 110
    assert body["points"][0]["quantity"] == 2
    assert body["points"][1]["unit_price_cents"] == 100
    assert body["points"][0]["date"] < body["points"][1]["date"]


# TC-003-06: Get product price history returns 404 when product not found
def test_get_product_price_history_not_found_returns_404(client):
    """
    Given no product with id 999 exists
    When the client requests GET /picnic/api/products/999/price-history
    Then a 404 response is returned
    And the response body is {"detail": "Product not found"}
    """
    response = client.get(f"{BASE}/products/999/price-history")

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


# TC-003-07: Receipt list pagination with limit and offset
def test_list_receipts_pagination(client, db_session):
    """
    Given 3 receipts exist
    When the client requests GET /picnic/api/receipts?limit=1&offset=1
    Then a 200 response is returned
    And "items" contains exactly 1 receipt
    And "total" is 3, "limit" is 1, "offset" is 1
    And the returned receipt is the second-newest by received_date
    """
    # Arrange
    r1 = _make_receipt("r1@picnic.app", datetime(2026, 1, 1, 10, 0))
    r2 = _make_receipt("r2@picnic.app", datetime(2026, 3, 1, 10, 0))
    r3 = _make_receipt("r3@picnic.app", datetime(2026, 6, 1, 10, 0))
    db_session.add_all([r1, r2, r3])
    db_session.commit()

    # Act
    response = client.get(f"{BASE}/receipts?limit=1&offset=1")

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["total"] == 3
    assert body["limit"] == 1
    assert body["offset"] == 1
    assert body["items"][0]["id"] == r2.id


# TC-003-08: Receipt list date-range filtering
def test_list_receipts_date_range_filter(client, db_session):
    """
    Given 3 receipts exist on 2026-01-01, 2026-03-01, and 2026-06-01
    When the client requests
         GET /picnic/api/receipts?from_date=2026-02-01&to_date=2026-04-01
    Then a 200 response is returned
    And "items" contains exactly the receipt from 2026-03-01
    And "total" is 1
    """
    # Arrange
    r1 = _make_receipt("r1@picnic.app", datetime(2026, 1, 1, 10, 0))
    r2 = _make_receipt("r2@picnic.app", datetime(2026, 3, 1, 10, 0))
    r3 = _make_receipt("r3@picnic.app", datetime(2026, 6, 1, 10, 0))
    db_session.add_all([r1, r2, r3])
    db_session.commit()

    # Act
    response = client.get(f"{BASE}/receipts?from_date=2026-02-01&to_date=2026-04-01")

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert [item["id"] for item in body["items"]] == [r2.id]


# TC-003-09: Receipt list rejects invalid limit
def test_list_receipts_rejects_invalid_limit(client):
    """
    Given any state of the database
    When the client requests GET /picnic/api/receipts?limit=0
    Then a 422 response is returned
    And the response body has a "detail" field (FastAPI validation error contract)
    """
    response = client.get(f"{BASE}/receipts?limit=0")

    assert response.status_code == 422
    assert "detail" in response.json()


# TC-003-10: Empty receipts list
def test_list_receipts_empty(client):
    """
    Given no receipts exist
    When the client requests GET /picnic/api/receipts
    Then a 200 response is returned
    And "items" is an empty list and "total" is 0
    """
    response = client.get(f"{BASE}/receipts")

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
