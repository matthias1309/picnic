# TEST-009 — Delete a Receipt Tests

**Status:** draft
**Created:** 2026-06-15
**Traces:** ARCH-009
**Verifies:** REQ-009 (AC-009-01, AC-009-02, AC-009-03, AC-009-04, AC-009-05)

---

## Test Cases

### TC-009-01 — `delete_receipt` removes a receipt, its items, and its price history

**Maps to:** AC-009-04
**Type:** unit/integration (in-memory SQLite)
**File:** `backend/tests/test_services.py`

```gherkin
Given a receipt exists with 2 line items and 2 price_history entries
When receipt_service.delete_receipt(db, receipt_id) is called
Then it returns True
And the receipt no longer exists in the database
And its receipt_items no longer exist
And its price_history entries no longer exist
And the referenced products are not deleted
```

---

### TC-009-02 — `delete_receipt` returns `False` for a non-existent receipt

**Maps to:** AC-009-05
**Type:** unit (in-memory SQLite)
**File:** `backend/tests/test_services.py`

```gherkin
Given no receipt with id 999 exists
When receipt_service.delete_receipt(db, 999) is called
Then it returns False
And no rows are deleted
```

---

### TC-009-03 — `DELETE /api/receipts/{id}` removes a receipt and returns 204

**Maps to:** AC-009-04
**Type:** integration (FastAPI TestClient + in-memory SQLite)
**File:** `backend/tests/test_api.py`

```gherkin
Given a receipt with id X exists with 1 item and 1 price_history entry
When the client sends DELETE /picnic/api/receipts/{X}
Then a 204 response is returned with an empty body
And GET /picnic/api/receipts/{X} subsequently returns 404
And GET /picnic/api/receipts no longer lists receipt X
```

---

### TC-009-04 — `DELETE /api/receipts/{id}` returns 404 for a non-existent receipt

**Maps to:** AC-009-05
**Type:** integration
**File:** `backend/tests/test_api.py`

```gherkin
Given no receipt with id 999 exists
When the client sends DELETE /picnic/api/receipts/999
Then a 404 response is returned
And the response body is {"detail": "Receipt not found"}
```

---

### TC-009-05 — Delete button is visible on the receipt detail page

**Maps to:** AC-009-01
**Type:** component (Vitest + React Testing Library)
**File:** `frontend/tests/Receipts.test.tsx`

```gherkin
Given the user is viewing a receipt's detail page
When the page is rendered
Then a button labeled "Delete receipt" is visible
```

---

### TC-009-06 — Confirming deletion sends a DELETE request and navigates to the list

**Maps to:** AC-009-04
**Type:** component (Vitest + React Testing Library)
**File:** `frontend/tests/Receipts.test.tsx`

```gherkin
Given the user is viewing a receipt's detail page
And window.confirm is mocked to return true
When they click "Delete receipt"
Then a DELETE request is sent to /receipts/{id}
And the user is navigated to /receipts
```

---

### TC-009-07 — Cancelling the confirmation sends no request

**Maps to:** AC-009-02, AC-009-03
**Type:** component (Vitest + React Testing Library)
**File:** `frontend/tests/Receipts.test.tsx`

```gherkin
Given the user is viewing a receipt's detail page
And window.confirm is mocked to return false
When they click "Delete receipt"
Then no DELETE request is sent
And the receipt detail remains visible
```

---

## Test Fixtures & Mocks

**Backend:**
- Reuses `client`, `db_session` fixtures from `conftest.py` (authenticated
  TestClient + in-memory SQLite, as used by TEST-003).
- `_make_receipt`, `_make_item` helpers from `test_api.py` (TEST-003) are
  reused; a `PriceHistory` row is added directly via the ORM for TC-009-01
  and TC-009-03.

**Frontend:**
- Reuses `renderWithProviders` and the `RECEIPT_DETAIL_FIXTURE` from
  `Receipts.test.tsx` (TEST-005).
- `apiClient.deleteJson` is mocked via `vi.spyOn(apiClient, "deleteJson")`.
- `window.confirm` is mocked via `vi.spyOn(window, "confirm")`.
- Navigation is asserted via the rendered route (e.g. asserting
  `receipt-list` becomes visible after navigation to `/receipts`), consistent
  with how `renderWithProviders` sets up `MemoryRouter`/`Routes` in existing
  tests.

---

## Notes on Coverage

These test cases aim for **80%+ coverage** on:
- `backend/services/receipt_service.py::delete_receipt`
- `backend/api/routes.py` — new `DELETE /receipts/{receipt_id}` endpoint
  (success and 404 paths)
- `frontend/src/components/Receipts/ReceiptDetail.tsx` — delete button,
  confirm/cancel branches
- `frontend/src/hooks/useReceipts.ts::useDeleteReceipt`
- `frontend/src/api/client.ts::deleteJson`

**Out of scope:**
- Re-testing authentication on `/api/*` routes — already covered by TEST-006
  (AC-006-04), which applies to all `api_router` routes including the new
  endpoint.
</content>
