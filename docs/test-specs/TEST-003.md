# TEST-003 — REST API for Receipt and Product Data Tests

**Status:** draft
**Created:** 2026-06-14
**Traces:** ARCH-003
**Verifies:** REQ-003 (AC-003-01, AC-003-02, AC-003-03, AC-003-04, AC-003-05, AC-003-06)

---

## Test Cases

### TC-003-01 — List receipts returns paginated, descending-by-date results

**Maps to:** AC-003-01
**Type:** integration (FastAPI TestClient + in-memory SQLite)
**File:** `backend/tests/test_api.py`

```gherkin
Given three parsed receipts exist with different received_date values
When the client requests GET /picnic/api/receipts
Then a 200 response is returned
And the response contains an "items" list of all three receipts, newest first
And each entry includes id, received_date, from_address, item_count, and total_cents
And the response includes "total", "limit", and "offset"
```

---

### TC-003-02 — Get a single receipt with items

**Maps to:** AC-003-02
**Type:** integration
**File:** `backend/tests/test_api.py`

```gherkin
Given a receipt with id X exists with 2 items
When the client requests GET /picnic/api/receipts/{X}
Then a 200 response is returned
And the response includes id, received_date, from_address, total_cents
And "items" contains 2 entries, each with product_name, quantity,
    unit_price_cents, and line_total_cents
```

---

### TC-003-03 — Get a single receipt returns 404 when not found

**Maps to:** AC-003-02
**Type:** integration
**File:** `backend/tests/test_api.py`

```gherkin
Given no receipt with id 999 exists
When the client requests GET /picnic/api/receipts/999
Then a 404 response is returned
And the response body is {"detail": "Receipt not found"}
```

---

### TC-003-04 — List products with purchase counts

**Maps to:** AC-003-03
**Type:** integration
**File:** `backend/tests/test_api.py`

```gherkin
Given two products exist, one purchased twice and one purchased once
When the client requests GET /picnic/api/products
Then a 200 response is returned
And each product entry includes id, name, and purchase_count
And purchase_count reflects the number of receipt_items referencing it
And products are ordered by name ascending
```

---

### TC-003-05 — Get product price history

**Maps to:** AC-003-04
**Type:** integration
**File:** `backend/tests/test_api.py`

```gherkin
Given a product with id Y has 2 price_history entries on different dates
When the client requests GET /picnic/api/products/{Y}/price-history
Then a 200 response is returned
And the response includes product_id and product_name
And "points" is a time-ordered list of {date, unit_price_cents, quantity}
    ascending by date
```

---

### TC-003-06 — Get product price history returns 404 when product not found

**Maps to:** AC-003-04
**Type:** integration
**File:** `backend/tests/test_api.py`

```gherkin
Given no product with id 999 exists
When the client requests GET /picnic/api/products/999/price-history
Then a 404 response is returned
And the response body is {"detail": "Product not found"}
```

---

### TC-003-07 — Receipt list pagination with limit and offset

**Maps to:** AC-003-06
**Type:** integration
**File:** `backend/tests/test_api.py`

```gherkin
Given 3 receipts exist
When the client requests GET /picnic/api/receipts?limit=1&offset=1
Then a 200 response is returned
And "items" contains exactly 1 receipt
And "total" is 3, "limit" is 1, "offset" is 1
And the returned receipt is the second-newest by received_date
```

---

### TC-003-08 — Receipt list date-range filtering

**Maps to:** AC-003-06
**Type:** integration
**File:** `backend/tests/test_api.py`

```gherkin
Given 3 receipts exist on 2026-01-01, 2026-03-01, and 2026-06-01
When the client requests
     GET /picnic/api/receipts?from_date=2026-02-01&to_date=2026-04-01
Then a 200 response is returned
And "items" contains exactly the receipt from 2026-03-01
And "total" is 1
```

---

### TC-003-09 — Receipt list rejects invalid limit

**Maps to:** AC-003-05, AC-003-06
**Type:** integration
**File:** `backend/tests/test_api.py`

```gherkin
Given any state of the database
When the client requests GET /picnic/api/receipts?limit=0
Then a 422 response is returned
And the response body has a "detail" field (FastAPI validation error contract)
```

---

### TC-003-10 — Empty receipts list

**Maps to:** AC-003-01
**Type:** integration
**File:** `backend/tests/test_api.py`

```gherkin
Given no receipts exist
When the client requests GET /picnic/api/receipts
Then a 200 response is returned
And "items" is an empty list and "total" is 0
```

---

## Test Fixtures & Mocks

**Fixtures needed (`conftest.py`):**
- `client`: FastAPI `TestClient` wired to a fresh in-memory SQLite database via
  dependency override of `get_db` (reuses the `db_session` fixture's engine
  pattern from TEST-001/TEST-002).
- Helper to seed `Receipt`, `Product`, `ReceiptItem`, `PriceHistory` rows
  directly via the ORM (no email parsing involved — REQ-003 is read-only over
  already-normalized data).

**Mocking strategy:**
- No real I/O beyond the in-memory SQLite database.
- Each test seeds exactly the rows it needs (no shared fixtures across tests).

---

## Notes on Coverage

These test cases aim for **80%+ coverage** on:
- `backend/api/routes.py` (all four endpoints, success and error paths)
- `backend/services/receipt_service.py` (new query functions:
  `list_receipts`, `get_receipt_with_items`, `list_products`,
  `get_product_with_price_history`)
- `backend/schemas.py` (response models exercised via serialization)

**Out of scope:**
- Statistics/aggregation endpoints → TEST-004
- Frontend tests → TEST-005
