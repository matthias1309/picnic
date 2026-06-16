# TEST-008 — Fix Price Extraction for Forwarded Invoice Emails

**Status:** approved
**Created:** 2026-06-14
**Traces:** ARCH-008
**Verifies:** REQ-008 (AC-008-01, AC-008-02)

---

## Test Cases

### TC-008-01 — Prices are extracted when price table rows are wrapped in `<tbody>`

**Maps to:** AC-008-01
**Type:** unit
**File:** `backend/tests/test_parser.py`

```gherkin
Given the HTML of a Picnic invoice where the price table's <tr> rows are
  wrapped in a <tbody> element (fixture: picnic_receipt_forwarded.html)
When ReceiptParser.parse() is called
Then "Max Premium Pistazien" has quantity=1, unit_price_cents=454 and
  line_total_cents=454 (same values as TC-002-03 for the non-wrapped HTML)
```

---

### TC-008-02 — "Gratis" items remain zero-priced with `<tbody>`-wrapped tables

**Maps to:** AC-008-01
**Type:** unit
**File:** `backend/tests/test_parser.py`

```gherkin
Given the HTML of a Picnic invoice where tables are wrapped in <tbody>
  elements (fixture: picnic_receipt_forwarded.html)
And one item is part of a "2+1 gratis" promotion with no price table rows
When ReceiptParser.parse() is called
Then that item has unit_price_cents=0 and line_total_cents=0
```

---

### TC-008-03 — No regression on the original (non-wrapped) invoice HTML

**Maps to:** AC-008-02
**Type:** unit
**File:** `backend/tests/test_parser.py`

```gherkin
Given the existing picnic_receipt.html fixture (no <tbody> wrapping)
When ReceiptParser.parse() is called
Then all 5 items are extracted with the same values as TC-002-03/TC-002-04
And the stated total is still 1320 (TC-002-06)
```

**Notes:** This is a regression check — it re-asserts the existing TC-002-03,
TC-002-04 and TC-002-06 expectations still hold after the `_extract_prices`
change. It does not need a new fixture; the existing tests in
`test_parser.py` already cover this and must continue to pass unchanged.

---

## Test Fixtures & Mocks

**New fixture (`backend/tests/fixtures/picnic_receipt_forwarded.html`):**

A small excerpt (2 items) reproducing the structure Gmail produces when
forwarding a "Dein Bon" email — every `<table>`'s `<tr>` children wrapped in
`<tbody>`:

- "Max Premium Pistazien" — discounted item (struck-through price 6,49€,
  discounted price 4,54€), quantity 1 → `line_total_cents = 454`
- "CORNY Müsliriegel Schoko Banane" — "2+1 gratis" item with an empty price
  table (no `<tr>` rows at all), quantity 2 → `line_total_cents = 0`

**New fixture fixture (`conftest.py`):**

- `picnic_receipt_forwarded_html`: loads `picnic_receipt_forwarded.html` as a
  string.

---

## Notes on Coverage

These test cases extend coverage of `backend/imap/parser.py`
(`_extract_prices` / new `_direct_rows` helper). No service-layer or API
changes are required — `_store_parsed_receipt` already stores whatever
`ParsedItem.line_total_cents` / `unit_price_cents` the parser returns.

**Out of scope:**
- Re-parsing of already-imported receipts (manual data step, see REQ-008).
