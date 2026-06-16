# TEST-013 — Group Receipt Line Items by Picnic Order Number

**Status:** approved
**Created:** 2026-06-16
**Traces:** ARCH-013
**Verifies:** REQ-013 (AC-013-01, AC-013-02, AC-013-03, AC-013-04, AC-013-05)

---

## Test Cases

### TC-013-01 — Parser assigns each item its order number

**Maps to:** AC-013-01
**Type:** unit
**File:** `backend/tests/test_parser.py`

```gherkin
Given the HTML of an invoice with two Bestellnr sections
  (fixture: picnic_receipt_current.html)
When ReceiptParser.parse() is called
Then "Testprodukt Eins" and "Testprodukt Zwei" have order_number "209-521-1175"
And "Testprodukt Drei" has order_number "204-701-1435"
```

---

### TC-013-02 — Single-order invoice assigns its order number to every item

**Maps to:** AC-013-01
**Type:** unit
**File:** `backend/tests/test_parser.py`

```gherkin
Given the existing picnic_receipt.html fixture (single Bestellnr 102-651-1311)
When ReceiptParser.parse() is called
Then every parsed item has order_number "102-651-1311"
```

---

### TC-013-03 — Order number is persisted with each receipt item

**Maps to:** AC-013-03
**Type:** integration
**File:** `backend/tests/test_services.py`

```gherkin
Given a stored raw receipt in the current invoice format
When parse_pending_receipts runs
Then the persisted receipt_items carry the parsed order_number values
```

---

### TC-013-04 — API exposes the order number per item

**Maps to:** AC-013-04
**Type:** integration
**File:** `backend/tests/test_api.py`

```gherkin
Given a stored receipt whose items have order numbers
When GET /api/receipts/{id} is called
Then each returned item includes its order_number
```

---

### TC-013-05 — Receipt detail groups items by order number

**Maps to:** AC-013-05
**Type:** component (frontend)
**File:** `frontend/tests/Receipts.test.tsx`

```gherkin
Given a receipt whose items belong to two order numbers
When ReceiptDetail is rendered
Then the items appear grouped under their order-number headings
```

---

## Test Fixtures & Mocks

- Reuses `picnic_receipt_current.html` (TEST-012) for the two-order case and the
  existing `picnic_receipt.html` for the single-order case.
- Service/API tests build a `Receipt` from the current-format raw email via the
  existing `make_raw_email` helper.
- Frontend test extends the existing receipt-detail test data with
  `order_number` values.

---

## Notes on Coverage

Covers `parser.py` (order extraction), `receipt_service.py` (persistence),
`schemas.py` / `routes.py` (exposure) and `ReceiptDetail.tsx` (grouping).

**Out of scope:** statistics by order number; backfilling existing receipts.
