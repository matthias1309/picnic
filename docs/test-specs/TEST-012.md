# TEST-012 — Robust Item-Row Detection for the Current Picnic Invoice Format

**Status:** draft
**Created:** 2026-06-16
**Traces:** ARCH-012
**Verifies:** REQ-012 (AC-012-01, AC-012-02, AC-012-03)

---

## Test Cases

### TC-012-01 — Parse line items in the current invoice format

**Maps to:** AC-012-01
**Type:** unit
**File:** `backend/tests/test_parser.py`

```gherkin
Given the HTML of a Picnic invoice whose item rows use
  "border-bottom: 1px solid #EBEBEB" (fixture: picnic_receipt_current.html)
When ReceiptParser.parse() is called
Then 3 items are returned
And "Testprodukt Eins" has quantity=1 and line_total_cents=250
And "Testprodukt Zwei" has quantity=2 and line_total_cents=358
```

---

### TC-012-02 — Non-product summary rows are ignored

**Maps to:** AC-012-02
**Type:** unit
**File:** `backend/tests/test_parser.py`

```gherkin
Given an invoice (fixture: picnic_receipt_current.html) whose Pfand summary
  row carries the item-row border style but has no product image
When ReceiptParser.parse() is called
Then no parsed item is derived from that summary row
And parse() does not raise
```

**Notes:** asserted indirectly by the exact item count (3) in TC-012-01 plus an
explicit assertion that no parsed item name equals "Pfand".

---

### TC-012-03 — No regression on the original invoice format

**Maps to:** AC-012-03
**Type:** unit
**File:** `backend/tests/test_parser.py`

```gherkin
Given the existing picnic_receipt.html fixture (lowercase, no-space style)
When ReceiptParser.parse() is called
Then all 5 items and the stated total 1320 are extracted as before
```

**Notes:** the existing TC-002-03/04/06 and TC-008-01/02 already cover this and
must continue to pass unchanged after the `parse()` change.

---

## Test Fixtures & Mocks

**New fixture (`backend/tests/fixtures/picnic_receipt_current.html`):**

An anonymized excerpt reproducing Picnic's current template:

- Two `Bestellnr` sections (`209-521-1175`, `204-701-1435`).
- Item rows styled `border-bottom: 1px solid #EBEBEB` (space + uppercase hex).
- "Testprodukt Eins" — single price 2,50€, qty 1 → 250.
- "Testprodukt Zwei" — discounted (struck 4,00€ / final 3,58€), qty 2 → 358.
- "Testprodukt Drei" — single price 1,29€, qty 1 → 129.
- A `Pfand` summary row with the same border style but **no product image**.
- `Gesamtbetrag` 7,37€.

**New fixture (`conftest.py`):**

- `picnic_receipt_current_html`: loads the file as a string.

---

## Notes on Coverage

Extends coverage of `backend/imap/parser.py` (`parse` row selection). No
service/API change for REQ-012.
