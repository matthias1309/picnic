# TEST-018 — Receipt List and Detail Show the Effective (Delivery) Date

**Status:** approved
**Created:** 2026-08-16
**Traces:** ARCH-018
**Verifies:** REQ-018 (AC-018-01, AC-018-02, AC-018-03, AC-018-04)

---

## Test Cases

### TC-018-01 — GET /receipts exposes effective_date, distinct from received_date

**Maps to:** AC-018-01
**Type:** integration
**File:** `backend/tests/test_api.py`

```gherkin
Given a receipt with delivery_date = 2026-04-15 and received_date =
  2026-06-17 10:00 (simulating a receipt reprocessed long after its real
  delivery, as happened in production on 2026-06-16/17)
When the client requests GET /picnic/api/receipts
Then the entry's effective_date is 2026-04-15
And the entry's received_date is still 2026-06-17 10:00 (unchanged, both
  fields present)
```

---

### TC-018-02 — GET /receipts/{id} exposes effective_date, distinct from received_date

**Maps to:** AC-018-02
**Type:** integration
**File:** `backend/tests/test_api.py`

```gherkin
Given the same receipt as TC-018-01
When the client requests GET /picnic/api/receipts/{id}
Then the response's effective_date is 2026-04-15
And the response's received_date is still 2026-06-17 10:00
```

---

### TC-018-03 — effective_date falls back to received_date when delivery_date is unset

**Maps to:** AC-018-03
**Type:** integration
**File:** `backend/tests/test_api.py`

```gherkin
Given a receipt with delivery_date = None and received_date = 2026-06-15
  18:50
When the client requests GET /picnic/api/receipts and GET
  /picnic/api/receipts/{id}
Then both responses' effective_date equals the received_date, 2026-06-15
  18:50
```

---

### TC-018-04 — Receipt list renders the effective date, not received_date

**Maps to:** AC-018-01
**Type:** unit (frontend)
**File:** `frontend/tests/Receipts.test.tsx`

```gherkin
Given a receipts list response where one entry has received_date
  "2026-06-17T04:57:53Z" (a reprocessing timestamp) and effective_date
  "2026-04-15T00:00:00Z" (the real delivery date)
When the user opens the receipts list
Then that entry displays "15.4.2026"
And it does not display "17.6.2026"
```

---

### TC-018-05 — Receipt detail heading renders the effective date, not received_date

**Maps to:** AC-018-02
**Type:** unit (frontend)
**File:** `frontend/tests/Receipts.test.tsx`

```gherkin
Given a receipt detail response with received_date "2026-06-17T04:57:53Z"
  and effective_date "2026-04-15T00:00:00Z"
When the user opens that receipt's detail page
Then the heading reads "Receipt from 15.4.2026"
```

---

### TC-018-06 — No regression on the existing receipts test suite

**Maps to:** AC-018-04
**Type:** integration + unit (existing tests, re-run largely unchanged)
**File:** `backend/tests/test_api.py`, `frontend/tests/Receipts.test.tsx`

```gherkin
Given the existing tests TC-003-01, TC-003-02, TC-005-04, TC-009-05,
  TC-009-06, TC-009-07, TC-013-05
When the change is applied
Then all of them continue to pass (fixtures gain an effective_date field
  where the frontend fixtures build ReceiptSummary/ReceiptDetail objects
  directly; no assertion changes needed since none of these tests assert on
  received_date/effective_date display)
```

**Notes:** the existing frontend fixtures (`RECEIPTS_FIXTURE`,
`RECEIPT_DETAIL_FIXTURE`, `GROUPED_RECEIPT_DETAIL_FIXTURE` in
`Receipts.test.tsx`) construct `ReceiptSummary`/`ReceiptDetail` object
literals directly against the TypeScript interfaces, so adding the required
`effective_date` field to those interfaces will fail to compile until the
fixtures are updated — this is the expected TDD-red state for the frontend
side of REQ-018.

## Test Fixtures & Mocks

No new fixture files. TC-018-01 through TC-018-03 use the existing
`_make_receipt` helper in `backend/tests/test_api.py`, extended with an
optional `delivery_date` parameter. TC-018-04/05 extend the existing
`RECEIPTS_FIXTURE` / `RECEIPT_DETAIL_FIXTURE` in `frontend/tests/Receipts.test.tsx`
with a divergent `effective_date` on one entry so the assertion is meaningful
(proves the component reads the new field, not just that both happen to
agree).

## Notes on Coverage

Extends coverage of `backend/schemas.py` (`ReceiptSummary`, `ReceiptDetail`),
`backend/api/routes.py` (`list_receipts`, `get_receipt`),
`frontend/src/components/Receipts/ReceiptList.tsx`, and
`frontend/src/components/Receipts/ReceiptDetail.tsx`. No parser or
`receipt_service` change — `Receipt.effective_date` and its sort usage
already exist and are unchanged.
