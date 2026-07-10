# TEST-017 — Budget History Grid (Last 12 Months)

**Status:** draft
**Created:** 2026-07-10
**Traces:** ARCH-017
**Verifies:** REQ-017 (AC-017-01, AC-017-02, AC-017-03)

## Test Cases

### TC-017-01 — Historical boxes are shown for the preceding 12 months, most recent first

**Maps to:** AC-017-01
**Type:** unit
**File:** `frontend/tests/lib/format.test.ts`

```gherkin
Given today is 2026-07-10
When getPastMonths(12, today) is called
Then it returns 12 months, most recent first, starting with "2026-06" and ending with "2025-07"
```

**Notes:** Pure function test, no mocks. Also cover a December-rollover case (e.g. today in
2026-01) to check year-boundary arithmetic.

---

### TC-017-02 — BudgetHistory renders one read-only card per historical month

**Maps to:** AC-017-01, AC-017-03
**Type:** unit
**File:** `frontend/tests/BudgetHistory.test.tsx`

```gherkin
Given the API returns a budget status for each of the last 12 months
When the user views the BudgetHistory component
Then 12 budget cards are rendered, one for each preceding month
And none of them shows an "Edit budget" control
```

**Notes:** Mock `apiClient.fetchJson` to resolve based on the requested `month` query param.

---

### TC-017-03 — Historical card reuses the over-budget visual style

**Maps to:** AC-017-02
**Type:** unit
**File:** `frontend/tests/BudgetHistory.test.tsx`

```gherkin
Given a historical month's spend exceeds its budget
When its card is rendered
Then the card shows the over-budget color and "Over budget by" text
```

**Notes:** Reuse the same fixture shape as `Budget.test.tsx`'s `OVER_BUDGET_FIXTURE`.

---

### TC-017-04 — Historical card reuses the under-budget visual style

**Maps to:** AC-017-02
**Type:** unit
**File:** `frontend/tests/BudgetHistory.test.tsx`

```gherkin
Given a historical month's spend is within budget
When its card is rendered
Then the card shows the under-budget color and "Remaining" text
```

**Notes:** Reuse the same fixture shape as `Budget.test.tsx`'s `UNDER_BUDGET_FIXTURE`.

---

### TC-017-05 — Current month's box remains editable; historical boxes are not

**Maps to:** AC-017-03
**Type:** unit
**File:** `frontend/tests/BudgetHistory.test.tsx`

```gherkin
Given the Home page renders BudgetWidget and BudgetHistory together
When the page has loaded
Then exactly one "Edit budget" button is present on the page
```

**Notes:** Render `<BudgetWidget />` and `<BudgetHistory />` together (as `Home.tsx` does) to
verify the two components compose without colliding `data-testid`s.
