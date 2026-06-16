# TEST-002 — HTML Email Parsing and Structured Receipt Storage Tests

**Status:** approved  
**Created:** 2026-06-13  
**Traces:** ARCH-002  
**Verifies:** REQ-002 (AC-002-01, AC-002-02, AC-002-03, AC-002-04, AC-002-05, AC-002-06)

---

## Test Cases

### TC-002-01 — Extract the text/html part from a raw MIME email

**Maps to:** AC-002-01 (prerequisite)  
**Type:** unit  
**File:** `backend/tests/test_parser.py`

```gherkin
Given a raw MIME email with a text/html part containing the invoice
When ReceiptParser.extract_html() is called
Then the HTML body of the text/html part is returned
```

**Notes:**
- Build a multipart `EmailMessage` with `add_alternative(html, subtype="html")`.
- Verify the returned string contains a known marker from the HTML fixture.

---

### TC-002-02 — extract_html() raises ParseError when no HTML part exists

**Maps to:** AC-002-05  
**Type:** unit  
**File:** `backend/tests/test_parser.py`

```gherkin
Given a raw MIME email with only a text/plain part
When ReceiptParser.extract_html() is called
Then ParseError is raised
```

---

### TC-002-03 — Parse line items from an invoice email

**Maps to:** AC-002-01  
**Type:** unit  
**File:** `backend/tests/test_parser.py`

```gherkin
Given the HTML of a Picnic invoice (fixture: picnic_receipt.html)
When ReceiptParser.parse() is called
Then 5 items are returned
And each item has name, quantity, unit_price_cents, and line_total_cents
And "Max Premium Pistazien" has quantity=1 and line_total_cents=454 (discounted price)
```

**Notes:**
- Fixture is a trimmed, anonymized excerpt of a real "Dein Bon" email,
  covering: a percentage discount, a "X+Y gratis" free item (no price shown),
  a "X+Y gratis" bundled item (discounted price), a "jetzt X€" promo, and a
  plain item with no promotion.

---

### TC-002-04 — Free ("gratis") items are parsed with zero price

**Maps to:** AC-002-01  
**Type:** unit  
**File:** `backend/tests/test_parser.py`

```gherkin
Given an invoice item that is part of a "2+1 gratis" promotion and shows no price
When ReceiptParser.parse() is called
Then the item "CORNY Müsliriegel Schoko Banane" has unit_price_cents=0 and line_total_cents=0
```

---

### TC-002-05 — parse() raises ParseError on malformed invoice HTML

**Maps to:** AC-002-05  
**Type:** unit  
**File:** `backend/tests/test_parser.py`

```gherkin
Given HTML that does not contain any Picnic item rows (fixture: picnic_receipt_malformed.html)
When ReceiptParser.parse() is called
Then ParseError is raised
```

---

### TC-002-06 — Extract the stated order total ("Gesamtbetrag")

**Maps to:** AC-002-06 (prerequisite)  
**Type:** unit  
**File:** `backend/tests/test_parser.py`

```gherkin
Given the HTML of a Picnic invoice containing a "Gesamtbetrag" total of 13,20€
When ReceiptParser.parse() is called
Then ParsedReceipt.stated_total_cents == 1320
```

---

### TC-002-07 — Parsing a pending receipt stores items, products, and price history

**Maps to:** AC-002-01, AC-002-02, AC-002-03, AC-002-04  
**Type:** integration (in-memory SQLite)  
**File:** `backend/tests/test_services.py`

```gherkin
Given a Receipt with processed=False and raw_email_text containing the invoice HTML
When parse_pending_receipts(db) is called
Then 5 receipt_items are created, linked to the receipt
And a matching product is created for each distinct item name
And a price_history row is recorded for each item with the receipt's received_date
And the receipt's processed flag is set to True
```

---

### TC-002-08 — Existing products are reused by exact name

**Maps to:** AC-002-02  
**Type:** integration  
**File:** `backend/tests/test_services.py`

```gherkin
Given a Product "Max Premium Pistazien" already exists
And a pending receipt contains an item with that exact name
When parse_pending_receipts(db) is called
Then no duplicate Product row is created
And the new receipt_item references the existing product
```

---

### TC-002-09 — A malformed receipt is skipped without affecting others

**Maps to:** AC-002-05  
**Type:** integration  
**File:** `backend/tests/test_services.py`

```gherkin
Given two pending receipts: one with valid invoice HTML, one with malformed HTML
When parse_pending_receipts(db) is called
Then the valid receipt is parsed, stored, and marked processed=True
And the malformed receipt remains processed=False
And the parse failure is logged with the receipt id
And ParseSummary reports parsed=1, failed=1
```

---

### TC-002-10 — Reconciliation warning on total mismatch

**Maps to:** AC-002-06  
**Type:** integration  
**File:** `backend/tests/test_services.py`

```gherkin
Given a pending receipt whose computed line-item sum differs from the stated total
When parse_pending_receipts(db) is called
Then a warning is logged containing the receipt id, computed total, and stated total
And the receipt is still marked processed=True (reconciliation is informational only)
```

---

### TC-002-11 — No pending receipts is a no-op

**Maps to:** AC-002-04 (idempotency)  
**Type:** integration  
**File:** `backend/tests/test_services.py`

```gherkin
Given no receipts with processed=False exist
When parse_pending_receipts(db) is called
Then ParseSummary(parsed=0, failed=0, items=0) is returned
And no exception is raised
```

---

## Test Fixtures & Mocks

**Fixtures needed (`backend/tests/fixtures/`):**
- `picnic_receipt.html` — anonymized excerpt of a real "Dein Bon" invoice
  (5 items: percentage discount, free gratis item, bundled gratis item,
  "jetzt X€" promo, plain item; includes a "Gesamtbetrag" total of 13,20€)
- `picnic_receipt_malformed.html` — HTML with no recognizable item rows

**Fixtures needed (`conftest.py`):**
- `picnic_receipt_html`: loads `picnic_receipt.html` as a string
- `picnic_receipt_malformed_html`: loads `picnic_receipt_malformed.html` as a string
- `make_raw_email`: builds a raw MIME string (`EmailMessage`) with a given HTML body,
  used to construct `Receipt.raw_email_text`

**Mocking strategy:**
- No real I/O: parser tests operate purely on in-memory strings.
- Service tests use the `db_session` in-memory SQLite fixture (from TEST-001).

---

## Notes on Coverage

These test cases aim for **80%+ coverage** on:
- `backend/imap/parser.py` (extract_html, parse, price extraction, total extraction)
- `backend/services/receipt_service.py` (parse_pending_receipts, get_or_create_product, reconciliation)
- `backend/models.py` (Product, ReceiptItem, PriceHistory relationships)

**Out of scope:**
- REST API exposure of parsed data → TEST-003
- Statistics/aggregation → TEST-004
- Frontend tests → TEST-005
