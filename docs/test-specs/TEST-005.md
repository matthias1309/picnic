# TEST-005 — React Dashboard

**Status:** approved
**Created:** 2026-06-14
**Traces:** ARCH-005
**Verifies:** REQ-005 (AC-005-01, AC-005-02, AC-005-03, AC-005-04, AC-005-05, AC-005-06)

## Test Cases

### TC-005-01 — Dashboard overview page

**Maps to:** AC-005-01
**Type:** unit (component)
**File:** `frontend/tests/Dashboard.test.tsx`

```gherkin
Given the API is reachable
When the user opens the dashboard home page
Then headline statistics from /api/stats/summary are displayed
And loading and error states are shown while data is fetched
```

**Notes:** Mock `useSummary` (TanStack Query hook) via a mocked `fetchJson`.
Cases: loading state shows `LoadingSpinner`; success state renders all five
`SummaryStats` fields formatted as currency/numbers; error state renders
`ErrorMessage`.

---

### TC-005-02 — Price history chart

**Maps to:** AC-005-02
**Type:** unit (component)
**File:** `frontend/tests/Charts.test.tsx`

```gherkin
Given a product with price history is selected
When the user views the price history chart
Then a Recharts line chart renders price over time
And the time range is configurable (e.g. 3m / 6m / 12m / all)
```

**Notes:** Mock `usePriceTrend` to return a `PriceTrend` fixture. Assert the
chart container renders (`data-testid="price-history-chart"`) with one point
per `points` entry, and min/max/avg are displayed. Assert range buttons
(3m/6m/12m/all) exist and clicking one updates the selected range in the
Zustand store (assert via the hook call args / re-render).

---

### TC-005-03 — Purchase statistics view

**Maps to:** AC-005-03
**Type:** unit (component)
**File:** `frontend/tests/Charts.test.tsx`

```gherkin
Given parsed data exists
When the user opens the statistics view
Then top purchased items and spending-over-time are visualized
And the user can switch the aggregation period (week/month)
```

**Notes:** Mock `useTopItems` and `useSpending` hooks. Assert top items are
rendered (one row per `TopItem`) and the spending-over-time chart renders one
bucket per `SpendingBucket`. Assert a week/month toggle exists and switching
it changes the `granularity` argument passed to `useSpending`.

---

### TC-005-04 — Receipt list and detail

**Maps to:** AC-005-04
**Type:** unit (component)
**File:** `frontend/tests/Receipts.test.tsx`

```gherkin
Given receipts exist
When the user opens the receipts list
Then receipts are shown paginated, sorted by date descending
And selecting a receipt shows its line items with quantities and prices
```

**Notes:** Mock `useReceipts` to return a `PaginatedReceipts` fixture (3
items) and `useReceiptDetail` to return a `ReceiptDetail` fixture. Assert
list renders rows in the given (already-descending) order with pagination
controls reflecting `total`/`limit`/`offset`. Assert selecting a receipt
(simulated route param) renders its `items` with product name, quantity,
unit price, and line total, plus the receipt total.

---

### TC-005-05 — Budget tracking display

**Maps to:** AC-005-05
**Type:** unit (component)
**File:** `frontend/tests/Budget.test.tsx`

```gherkin
Given a budget is configured in the backend
When the user views the budget widget
Then actual spend versus budget for the current month is displayed
And an over-budget state is visually distinct
```

**Notes:** Mock `useBudget` with two fixtures: (1) `remaining_cents > 0`
(under budget) and (2) `remaining_cents < 0` (over budget). Assert both
`spent_cents` and `budget_cents` are displayed in both cases, and that the
over-budget case applies the red/over-budget styling (e.g.
`data-testid="budget-widget"` has class containing `red`) while the
under-budget case does not.

---

### TC-005-06 — Server state management and resilience

**Maps to:** AC-005-06
**Type:** unit (component)
**File:** `frontend/tests/Dashboard.test.tsx`

```gherkin
Given the dashboard fetches data from the API
When requests are in flight, succeed, or fail
Then TanStack Query handles caching, loading, and error states
And the UI degrades gracefully (empty states, retry) without crashing
```

**Notes:** Render `Home` page with a `QueryClientProvider` (retry disabled
for test speed). Simulate a rejected `fetchJson` call: assert
`ErrorMessage` renders with a "Retry" button, clicking it triggers a refetch
(mock call count increases). Simulate an empty/zero-value `SummaryStats`
response: assert the page renders without throwing (no crash) and shows the
zero values rather than an empty/blank screen.

