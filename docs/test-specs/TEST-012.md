# TEST-012 — Robust Item-Row Detection for the Current Picnic Invoice Format

**Status:** approved
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

### TC-012-04 — End-to-end regression on a real production invoice email

**Maps to:** AC-012-01 (also exercises REQ-013 order grouping)
**Type:** unit
**File:** `backend/tests/test_parser.py`

```gherkin
Given the raw MIME of a real Picnic "Dein Bon" email, anonymized
  (fixture: picnic_receipt_original.html)
When ReceiptParser.extract_html() then parse() are called
Then all 33 line items are extracted
And the items are grouped under the two order numbers
  "209-521-1175" and "204-701-1435"
And the summed line totals equal 6542 cents
```

**Notes:** this is the exact email that previously failed to parse in
production. It locks in the current-template behavior against a real-world
sample, not a hand-built excerpt.

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

**New fixture (`backend/tests/fixtures/picnic_receipt_original.html`):**

A full raw MIME "Dein Bon" email straight from IMAP, anonymized (recipient
name, delivery address, email addresses and bounce/X-MSFBL tracking tokens
replaced; item rows untouched). 33 items across two `Bestellnr` sections.

**New fixtures (`conftest.py`):**

- `picnic_receipt_current_html`: loads the current-format excerpt as a string.
- `picnic_receipt_original_raw`: loads the raw anonymized email as a string.

---

## Notes on Coverage

Extends coverage of `backend/imap/parser.py` (`parse` row selection). No
service/API change for REQ-012.
