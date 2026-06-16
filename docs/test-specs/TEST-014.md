# TEST-014 — Parse the Delivery Date from the Invoice HTML

**Status:** draft
**Created:** 2026-06-16
**Traces:** ARCH-014
**Verifies:** REQ-014 (AC-014-01, AC-014-02, AC-014-03, AC-014-04, AC-014-05, AC-014-06)

---

## Test Cases

### TC-014-01 — Parser extracts the delivery date from the invoice body

**Maps to:** AC-014-01
**Type:** unit
**File:** `backend/tests/test_parser.py`

```gherkin
Given an invoice whose body states
  "hier ist der Bon zu deiner Lieferung von Freitag 15 Mai 2026"
  (fixture: picnic_receipt_current.html)
When ReceiptParser.parse() is called
Then ParsedReceipt.delivery_date == date(2026, 5, 15)
```

---

### TC-014-02 — All German month names are recognised

**Maps to:** AC-014-02
**Type:** unit
**File:** `backend/tests/test_parser.py`

```gherkin
Given the delivery sentence rendered with each German month name
  (Januar … Dezember, including "März")
When ReceiptParser.parse() is called for each
Then delivery_date.month equals the corresponding 1..12 value
```

---

### TC-014-03 — Missing or unparseable delivery date yields None

**Maps to:** AC-014-03
**Type:** unit
**File:** `backend/tests/test_parser.py`

```gherkin
Given an invoice with no "Lieferung von <weekday> <day> <month> <year>" sentence
  (fixture: picnic_receipt.html)
When ReceiptParser.parse() is called
Then delivery_date is None
And the items and stated total are still extracted (no regression)
```

---

### TC-014-04 — Delivery date dates the stored receipt and its price history

**Maps to:** AC-014-04
**Type:** integration
**File:** `backend/tests/test_services.py`

```gherkin
Given a pending receipt whose email Date header is 2026-06-01
  and whose body states a delivery of "Freitag 15 Mai 2026"
When parse_pending_receipts(db) runs
Then Receipt.delivery_date == date(2026, 5, 15)
And every PriceHistory.recorded_date for that receipt is 2026-05-15
```

---

### TC-014-05 — Fallback to the email date when no delivery date is parsed

**Maps to:** AC-014-05
**Type:** integration
**File:** `backend/tests/test_services.py`

```gherkin
Given a pending receipt whose body has no delivery sentence (picnic_receipt.html)
  and whose email Date header is 2026-06-01
When parse_pending_receipts(db) runs
Then Receipt.delivery_date is None
And every PriceHistory.recorded_date falls back to the received_date 2026-06-01
```

---

### TC-014-06 — Statistics count a re-delivered receipt in its delivery month

**Maps to:** AC-014-06
**Type:** unit
**File:** `backend/tests/test_stats_service.py`

```gherkin
Given a receipt with received_date 2026-06-16 and delivery_date 2026-05-15
When get_spent_for_month(db, "2026-05") and (db, "2026-06") are called
Then the receipt's spend is counted in "2026-05", not "2026-06"
```

---

## Test Fixtures & Mocks

- `picnic_receipt_current.html` gains an intro line containing
  "hier ist der Bon zu deiner Lieferung von Freitag 15 Mai 2026"; existing item
  and total assertions are unaffected (the line carries no item-row style and no
  product image).
- TC-014-02 reuses that fixture, substituting the month name per case.
- TC-014-03/05 reuse `picnic_receipt.html`, which has no delivery sentence.
- Service tests build receipts from raw emails via the existing `make_raw_email`
  helper (email `Date` header = 2026-06-01).
- TC-014-06 constructs a `Receipt` with `delivery_date` set directly.

---

## Notes on Coverage

Covers `parser.py` (delivery-date extraction + German month mapping),
`receipt_service.py` (persisting the date and dating price history by
`effective_date`), and `stats_service.py` (month aggregation by
`effective_date`).

**Out of scope:** re-dating existing receipts; forwarded-email dedup; non-German
wordings.
