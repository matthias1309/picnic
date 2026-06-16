# TEST-011 — Configure Monthly Budget Tests

**Status:** approved
**Created:** 2026-06-15
**Traces:** ARCH-011
**Verifies:** REQ-011 (AC-011-01, AC-011-02, AC-011-03, AC-011-04, AC-011-05, AC-011-06)

---

## Test Cases

### TC-011-01 — `get_monthly_budget_cents` falls back to the `.env` default when unset

**Maps to:** AC-011-06 (backward compatibility)
**Type:** unit (in-memory SQLite)
**File:** `backend/tests/test_services.py`

```gherkin
Given no budget_settings row exists
And settings.monthly_budget_cents is 30000
When budget_service.get_monthly_budget_cents(db) is called
Then it returns 30000
```

---

### TC-011-02 — `set_monthly_budget_cents` persists a new value

**Maps to:** AC-011-06
**Type:** unit (in-memory SQLite)
**File:** `backend/tests/test_services.py`

```gherkin
Given no budget_settings row exists
When budget_service.set_monthly_budget_cents(db, 35000) is called
Then it returns 35000
And budget_service.get_monthly_budget_cents(db) subsequently returns 35000
  (independent of settings.monthly_budget_cents)
```

---

### TC-011-03 — `set_monthly_budget_cents` updates an existing value

**Maps to:** AC-011-06
**Type:** unit (in-memory SQLite)
**File:** `backend/tests/test_services.py`

```gherkin
Given budget_service.set_monthly_budget_cents(db, 35000) was already called
When budget_service.set_monthly_budget_cents(db, 40000) is called
Then it returns 40000
And budget_service.get_monthly_budget_cents(db) returns 40000
And only one row exists in budget_settings
```

---

### TC-011-04 — `PUT /api/settings/budget` updates the budget and returns it

**Maps to:** AC-011-03, AC-011-06
**Type:** integration (FastAPI TestClient + in-memory SQLite)
**File:** `backend/tests/test_api.py`

```gherkin
Given the client is authenticated
When the client sends PUT /picnic/api/settings/budget
  with body {"monthly_budget_cents": 35000}
Then a 200 response is returned
And the response body is {"monthly_budget_cents": 35000}
And a subsequent GET /picnic/api/stats/budget?month=2026-06
  returns budget_cents = 35000
```

---

### TC-011-05 — `PUT /api/settings/budget` rejects a negative value

**Maps to:** AC-011-05
**Type:** integration
**File:** `backend/tests/test_api.py`

```gherkin
Given the client is authenticated
And the configured budget is currently 30000
When the client sends PUT /picnic/api/settings/budget
  with body {"monthly_budget_cents": -1}
Then a 422 response is returned
And a subsequent GET /picnic/api/stats/budget?month=2026-06
  still returns budget_cents = 30000 (unchanged)
```

---

### TC-011-06 — `GET /api/stats/budget` reflects the persisted value across months

**Maps to:** AC-011-06
**Type:** integration
**File:** `backend/tests/test_api.py`

```gherkin
Given the client has set the budget to 35000 via PUT /api/settings/budget
When the client requests GET /picnic/api/stats/budget?month=2026-01
  and GET /picnic/api/stats/budget?month=2026-06
Then both responses have budget_cents = 35000
```

---

### TC-011-07 — Edit control is visible and opens a pre-filled form

**Maps to:** AC-011-01, AC-011-02
**Type:** component (Vitest + React Testing Library)
**File:** `frontend/tests/Budget.test.tsx`

```gherkin
Given the budget widget shows a configured budget of 300.00 €
When the page has loaded
Then an "Edit budget" button is visible
When the user clicks "Edit budget"
Then an input field is shown with value "300"
And "Save" and "Cancel" buttons are shown
```

---

### TC-011-08 — Saving sends a PUT request and updates the displayed budget

**Maps to:** AC-011-03
**Type:** component (Vitest + React Testing Library)
**File:** `frontend/tests/Budget.test.tsx`

```gherkin
Given the budget widget is in edit mode showing "300"
And apiClient.putJson is mocked to resolve {"monthly_budget_cents": 35000}
When the user changes the input to "350" and clicks "Save"
Then apiClient.putJson is called with
  ("/settings/budget", { monthly_budget_cents: 35000 })
And the edit form is closed
And the widget displays the updated budget (350,00 €)
```

---

### TC-011-09 — Cancelling discards changes without sending a request

**Maps to:** AC-011-04
**Type:** component (Vitest + React Testing Library)
**File:** `frontend/tests/Budget.test.tsx`

```gherkin
Given the budget widget is in edit mode showing "300"
And apiClient.putJson is mocked
When the user changes the input to "350" and clicks "Cancel"
Then apiClient.putJson is not called
And the edit form is closed
And the widget still displays the original budget (300,00 €)
```

---

### TC-011-10 — Negative input is rejected client-side

**Maps to:** AC-011-05
**Type:** component (Vitest + React Testing Library)
**File:** `frontend/tests/Budget.test.tsx`

```gherkin
Given the budget widget is in edit mode
And apiClient.putJson is mocked
When the user changes the input to "-10" and clicks "Save"
Then apiClient.putJson is not called
And a validation message is shown
And the edit form remains open
```

---

## Test Fixtures & Mocks

**Backend:**
- Reuses `client`, `db_session` fixtures from `conftest.py` (authenticated
  TestClient + in-memory SQLite, as used by TEST-004/TEST-009).
- TC-011-01..03 use `db_session` directly against
  `backend/services/budget_service.py`; `monkeypatch.setattr(settings,
  "monthly_budget_cents", ...)` sets the `.env` fallback for TC-011-01.

**Frontend:**
- Reuses `renderWithProviders` and `UNDER_BUDGET_FIXTURE` /
  `OVER_BUDGET_FIXTURE` from the existing `Budget.test.tsx` (TEST-005).
- `apiClient.fetchJson` is mocked via `vi.spyOn` for the initial
  `GET /stats/budget` (as today).
- `apiClient.putJson` is mocked via `vi.spyOn(apiClient, "putJson")` for the
  new save flow.
- User interaction (clicking buttons, typing into the input) via
  `@testing-library/user-event`, consistent with other interactive
  component tests in this project.

---

## Notes on Coverage

These test cases aim for **80%+ coverage** on:
- `backend/services/budget_service.py` — both functions, unset/set/update
  paths
- `backend/api/routes.py` — new `PUT /settings/budget` (success + validation
  error), and `GET /stats/budget` reading the persisted value
- `frontend/src/components/Budget/BudgetWidget.tsx` — edit mode, save,
  cancel, client-side validation
- `frontend/src/hooks/useStats.ts::useUpdateBudget`
- `frontend/src/api/client.ts::putJson`

**Out of scope:**
- Re-testing authentication on `/api/*` routes — already covered by TEST-006
  (AC-006-04), which applies to all `api_router` routes including the new
  endpoint.
- Re-testing the existing read-only budget display (under/over-budget
  styling) — already covered by TEST-005 (TC-005-05) and unchanged by this
  feature.
