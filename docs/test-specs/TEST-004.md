# TEST-004 — Statistics and Spending Insights Tests

**Status:** draft
**Created:** 2026-06-14
**Traces:** ARCH-004
**Verifies:** REQ-004 (AC-004-01, AC-004-02, AC-004-03, AC-004-04, AC-004-05, AC-004-06)

---

## Test Cases

### TC-004-01 — Spending grouped by month

**Maps to:** AC-004-01
**Type:** integration (FastAPI TestClient + in-memory SQLite)
**File:** `backend/tests/test_stats_api.py`

```gherkin
Given receipts with items exist in January, March, and March of 2026
When the client requests GET /picnic/api/stats/spending?granularity=month
Then a 200 response is returned
And "buckets" contains one entry per month with "period" as "YYYY-MM"
And the March bucket's total_cents is the sum of both March receipts' items
And buckets are ordered ascending by period
```

---

### TC-004-02 — Spending grouped by week (ISO Monday boundary)

**Maps to:** AC-004-01
**Type:** unit (stats_service)
**File:** `backend/tests/test_stats_service.py`

```gherkin
Given a receipt with items on Sunday 2026-01-04 and another on Monday 2026-01-05
When get_spending_over_time(db, granularity="week") is called
Then two buckets are returned
And the first bucket's period is "2025-12-29" (the Monday of the week
    containing 2026-01-04)
And the second bucket's period is "2026-01-05"
```

---

### TC-004-03 — Spending date-range filter

**Maps to:** AC-004-01
**Type:** integration
**File:** `backend/tests/test_stats_api.py`

```gherkin
Given receipts with items exist on 2026-01-15, 2026-03-15, and 2026-06-15
When the client requests
     GET /picnic/api/stats/spending?granularity=month&from_date=2026-02-01&to_date=2026-04-01
Then a 200 response is returned
And "buckets" contains exactly one entry for "2026-03"
```

---

### TC-004-04 — Top items ranked by quantity descending

**Maps to:** AC-004-02
**Type:** integration
**File:** `backend/tests/test_stats_api.py`

```gherkin
Given "Milch" was bought 5 times total (across receipts) and "Brot" was bought 2 times
When the client requests GET /picnic/api/stats/top-items
Then a 200 response is returned
And the first entry is "Milch" with total_quantity 5
And the second entry is "Brot" with total_quantity 2
And each entry includes product_id, product_name, total_quantity, total_spend_cents
```

---

### TC-004-05 — Top items respects the limit parameter

**Maps to:** AC-004-02
**Type:** integration
**File:** `backend/tests/test_stats_api.py`

```gherkin
Given 3 distinct products have been purchased
When the client requests GET /picnic/api/stats/top-items?limit=2
Then a 200 response is returned
And exactly 2 entries are returned
```

---

### TC-004-06 — Price trend returns time series with min/max/avg

**Maps to:** AC-004-03
**Type:** integration
**File:** `backend/tests/test_stats_api.py`

```gherkin
Given a product has price_history entries of 100, 120, and 110 cents
    on three different dates
When the client requests GET /picnic/api/stats/price-trend/{product_id}
Then a 200 response is returned
And "points" is a time-ordered list of {date, unit_price_cents, quantity}
And min_price_cents is 100, max_price_cents is 120, avg_price_cents is 110
```

---

### TC-004-07 — Price trend returns 404 for unknown product

**Maps to:** AC-004-03
**Type:** integration
**File:** `backend/tests/test_stats_api.py`

```gherkin
Given no product with id 999 exists
When the client requests GET /picnic/api/stats/price-trend/999
Then a 404 response is returned
And the response body is {"detail": "Product not found"}
```

---

### TC-004-08 — Budget tracking for a given month

**Maps to:** AC-004-04
**Type:** integration
**File:** `backend/tests/test_stats_api.py`

```gherkin
Given MONTHLY_BUDGET_CENTS is configured to 30000
And receipts with items totalling 12000 cents exist in June 2026
When the client requests GET /picnic/api/stats/budget?month=2026-06
Then a 200 response is returned
And budget_cents is 30000, spent_cents is 12000, remaining_cents is 18000
```

---

### TC-004-09 — Budget rejects a malformed month parameter

**Maps to:** AC-004-04
**Type:** integration
**File:** `backend/tests/test_stats_api.py`

```gherkin
Given any state of the database
When the client requests GET /picnic/api/stats/budget?month=not-a-month
Then a 422 response is returned
And the response body has a "detail" field
```

---

### TC-004-10 — Summary returns headline figures

**Maps to:** AC-004-05
**Type:** unit (stats_service)
**File:** `backend/tests/test_stats_service.py`

```gherkin
Given 2 receipts exist: one in the current month totalling 1000 cents
    with 2 items, one in a previous month totalling 500 cents with 1 item
And 2 distinct products exist across both receipts
When get_summary(db, today=<date in the current month>) is called
Then total_spend_cents is 1500
And receipt_count is 2
And distinct_product_count is 2
And average_basket_cents is 750
And current_month_spend_cents is 1000
```

---

### TC-004-11 — Empty-data handling across all statistics endpoints

**Maps to:** AC-004-06
**Type:** integration
**File:** `backend/tests/test_stats_api.py`

```gherkin
Given no parsed receipts, products, or price history exist
When the client requests:
  - GET /picnic/api/stats/spending
  - GET /picnic/api/stats/top-items
  - GET /picnic/api/stats/budget?month=2026-06
  - GET /picnic/api/stats/summary
Then each request returns a 200 response
And /stats/spending returns an empty "buckets" list
And /stats/top-items returns an empty list
And /stats/budget returns spent_cents=0 and remaining_cents=budget_cents
And /stats/summary returns all zero counts/totals
```

---

## Test Fixtures & Mocks

**Fixtures needed:**
- Reuses `client` and `db_session` fixtures from `conftest.py` (TEST-003).
- Helpers `_make_receipt` / `_make_item` from `test_api.py` are duplicated
  (or imported) into `test_stats_api.py` to seed receipts, products, and
  receipt items directly via the ORM.
- TC-004-08 sets `MONTHLY_BUDGET_CENTS` via `backend.config.settings`
  override (monkeypatch), restored after the test.

**Mocking strategy:**
- No real I/O beyond the in-memory SQLite database.
- TC-004-10 (current-month logic) passes an explicit `today` argument to
  `get_summary()` instead of relying on `date.today()`, keeping the test
  deterministic (FIRST principles).

---

## Notes on Coverage

These test cases aim for **80%+ coverage** on:
- `backend/services/stats_service.py` (all five aggregation functions,
  including empty-data branches)
- `backend/api/routes.py` (all five new `/stats/*` endpoints, success and
  error paths)
- `backend/schemas.py` (new stats response models exercised via
  serialization)

**Out of scope:**
- Frontend stats charts/components → REQ-005 and its TEST-SPEC.
