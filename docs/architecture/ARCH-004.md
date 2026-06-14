# ARCH-004 — Statistics and Spending Insights

**Status:** draft
**Created:** 2026-06-14
**Traces:** REQ-004
**Verified by:** TEST-004

## Summary

ARCH-004 adds aggregation/statistics endpoints under `/picnic/api/stats/*`,
built on top of the normalized data from REQ-002 and following the same
thin-routes-over-service pattern established by ARCH-003. All aggregation
logic lives in a new `backend/services/stats_service.py`; response shapes
are new Pydantic models in `backend/schemas.py`; routes are added to the
existing `api_router` in `backend/api/routes.py`.

---

## Design

### Component Overview

```
┌──────────────────────────────────────────────────────────────┐
│  FastAPI app (backend/main.py)                                │
│   router(prefix="/picnic") -> api_router(prefix="/api")       │
│       → /picnic/api/stats/spending                            │  ← new
│       → /picnic/api/stats/top-items                           │  ← new
│       → /picnic/api/stats/price-trend/{product_id}            │  ← new
│       → /picnic/api/stats/budget                              │  ← new
│       → /picnic/api/stats/summary                             │  ← new
└──────────────────────────────────────────────────────────────┘
                              ↓ calls
┌──────────────────────────────────────────────────────────────┐
│  backend/services/stats_service.py  (new)                     │
│   get_spending_over_time(db, granularity, from_date, to_date)  │
│     -> list[(period: str, total_cents: int)]                   │
│   get_top_items(db, limit)                                      │
│     -> list[(Product, total_quantity: int, total_spend_cents)] │
│   get_price_trend(db, product_id, from_date, to_date)           │
│     -> (Product, list[PriceHistory], min, max, avg) | None     │
│   get_budget_status(db, month, budget_cents)                    │
│     -> spent_cents: int                                         │
│   get_summary(db, today)                                        │
│     -> SummaryStats fields (tuple)                              │
└──────────────────────────────────────────────────────────────┘
                              ↓ maps to
┌──────────────────────────────────────────────────────────────┐
│  backend/schemas.py  (new response models)                     │
│   SpendingBucket, SpendingOverTime, TopItem,                    │
│   PriceTrendPoint, PriceTrend, BudgetStatus, SummaryStats       │
└──────────────────────────────────────────────────────────────┘
```

### Endpoints

| Method | Path | Maps to | Response |
|--------|------|---------|----------|
| GET | `/picnic/api/stats/spending` | AC-004-01, AC-004-06 | `SpendingOverTime` |
| GET | `/picnic/api/stats/top-items` | AC-004-02, AC-004-06 | `list[TopItem]` |
| GET | `/picnic/api/stats/price-trend/{product_id}` | AC-004-03, AC-004-06 | `PriceTrend` |
| GET | `/picnic/api/stats/budget` | AC-004-04, AC-004-06 | `BudgetStatus` |
| GET | `/picnic/api/stats/summary` | AC-004-05, AC-004-06 | `SummaryStats` |

### Data Flow — `GET /api/stats/spending`

```
GET /picnic/api/stats/spending?granularity=month&from_date=2026-01-01&to_date=2026-06-30
        ↓
routes.get_spending(granularity, from_date, to_date, db)
        ↓
stats_service.get_spending_over_time(db, granularity, from_date, to_date)
        ↓
  period_expr =
    "month" -> strftime('%Y-%m', received_date)             -> "2026-06"
    "week"  -> date(received_date, 'weekday 0', '-6 days')   -> "2026-06-08" (Monday)
  query = select(period_expr, sum(line_total_cents))
            join receipts -> receipt_items
            [optional date(received_date) BETWEEN from_date AND to_date]
            group by period_expr
            order by period_expr asc
        ↓
SpendingOverTime(
  granularity=granularity,
  buckets=[SpendingBucket(period=..., total_cents=...) ...],
)
```

### Data Flow — `GET /api/stats/top-items`

```
GET /picnic/api/stats/top-items?limit=10
        ↓
stats_service.get_top_items(db, limit)
        ↓
  SELECT products.*, SUM(receipt_items.quantity) AS total_quantity,
         SUM(receipt_items.line_total_cents) AS total_spend_cents
  FROM products JOIN receipt_items ON receipt_items.product_id = products.id
  GROUP BY products.id
  ORDER BY total_quantity DESC, total_spend_cents DESC
  LIMIT :limit
        ↓
[TopItem(product_id, product_name, total_quantity, total_spend_cents) ...]
```

### Data Flow — `GET /api/stats/price-trend/{product_id}`

```
product = db.get(Product, product_id)
if product is None: raise HTTPException(404, "Product not found")

points = SELECT * FROM price_history
         WHERE product_id = :id
         [AND date(recorded_date) BETWEEN from_date AND to_date]
         ORDER BY recorded_date ASC

min_price_cents = min(p.unit_price_cents for p in points) or 0
max_price_cents = max(p.unit_price_cents for p in points) or 0
avg_price_cents = round(mean(p.unit_price_cents for p in points)) or 0
        ↓
PriceTrend(
  product_id, product_name,
  points=[PriceTrendPoint(date, unit_price_cents, quantity) ...],
  min_price_cents, max_price_cents, avg_price_cents,
)
```

### Data Flow — `GET /api/stats/budget`

```
GET /picnic/api/stats/budget?month=2026-06
        ↓
spent_cents = SELECT COALESCE(SUM(receipt_items.line_total_cents), 0)
              FROM receipt_items JOIN receipts ON receipt_items.receipt_id = receipts.id
              WHERE strftime('%Y-%m', receipts.received_date) = :month

budget_cents = settings.monthly_budget_cents
        ↓
BudgetStatus(
  month=month,
  budget_cents=budget_cents,
  spent_cents=spent_cents,
  remaining_cents=budget_cents - spent_cents,
)
```

### Data Flow — `GET /api/stats/summary`

```
total_spend_cents       = COALESCE(SUM(receipt_items.line_total_cents), 0)
receipt_count           = COUNT(receipts.id)
distinct_product_count  = COUNT(products.id)
average_basket_cents    = round(total_spend_cents / receipt_count) if receipt_count else 0
current_month_spend_cents =
  COALESCE(SUM(receipt_items.line_total_cents), 0)
  WHERE strftime('%Y-%m', receipts.received_date) = strftime('%Y-%m', :today)
        ↓
SummaryStats(total_spend_cents, receipt_count, distinct_product_count,
              average_basket_cents, current_month_spend_cents)
```

`:today` defaults to `date.today()` but is an injectable parameter of
`get_summary()` so tests can pass a fixed reference date (FIRST: tests must
not depend on wall-clock time).

### Query Parameters

| Endpoint | Param | Default | Constraint |
|----------|-------|---------|------------|
| `/stats/spending` | `granularity` | `month` | `"week"` or `"month"` |
| `/stats/spending` | `from_date`/`to_date` | none | inclusive bounds on `received_date` (ISO date) |
| `/stats/top-items` | `limit` | 10 | `1 <= limit <= 100` |
| `/stats/price-trend/{id}` | `from_date`/`to_date` | none | inclusive bounds on `recorded_date` (ISO date) |
| `/stats/budget` | `month` | required | `^\d{4}-\d{2}$` (e.g. `2026-06`) |

`TOP_ITEMS_DEFAULT_LIMIT = 10` and reuse of `MAX_PAGE_SIZE = 100` (from
ARCH-003) live in `backend/api/routes.py`.

### Error Contract

Consistent with ARCH-003:
- `/stats/price-trend/{id}` → `HTTPException(404, "Product not found")` if
  the product does not exist.
- Invalid `granularity` or malformed `month`/date params → HTTP 422 via
  FastAPI/Pydantic validation (`Literal["week", "month"]`,
  `pattern=r"^\d{4}-\d{2}$"`).
- All other endpoints never error on empty data (AC-004-06): they return
  zeroed/empty `response_model` instances with HTTP 200.

### Module Layout

```
backend/
  config.py                  # extended: monthly_budget_cents setting
  schemas.py                 # extended: stats response models (this REQ)
  api/
    routes.py                 # extended: /stats/* endpoints on api_router
  services/
    stats_service.py          # new: all aggregation queries
```

No changes to `backend/main.py` — `api_router` is already mounted.

---

## Key Decisions

### 1. Week buckets use ISO weeks (Monday-Sun), labeled by the Monday date

**Decision:** For `granularity=week`, the bucket label is the ISO date
(`YYYY-MM-DD`) of the Monday starting that week, computed in SQLite as
`date(received_date, 'weekday 0', '-6 days')`. For `granularity=month`, the
label is `YYYY-MM` via `strftime('%Y-%m', received_date)`.

**Rationale:** Resolves the "Week definition" open question from REQ-004.
SQLite's `'weekday 0'` modifier moves a date forward to the next Sunday;
subtracting 6 days yields the Monday of that ISO week — a standard idiom
that works correctly across year boundaries (verified for 2025-12-29 /
2026-01-01 etc.). A single ISO-date label format keeps both granularities
sortable as plain strings.

### 2. Top items ranked by total quantity, with spend as a secondary key

**Decision:** `top-items` orders by `SUM(quantity) DESC, SUM(line_total_cents)
DESC`.

**Rationale:** AC-004-02 asks for "most frequently bought products" —
frequency maps to purchase quantity, not spend. Total spend is still returned
per item for the dashboard, and used as a tiebreaker for deterministic
ordering when quantities are equal.

### 3. Price trend uses `unit_price_cents` (per-unit), not line totals

**Decision:** `price-trend` time series and min/max/avg are computed over
`price_history.unit_price_cents`.

**Rationale:** Resolves the "per unit price or per line total" open question.
`price_history` (per CLAUDE.md) already stores per-purchase unit prices
specifically for charting; line totals would conflate price changes with
quantity changes, which is not what a "price trend" chart should show.

### 4. Budget value comes from `Settings.monthly_budget_cents` (.env)

**Decision:** A new `monthly_budget_cents: int = 0` setting is added to
`backend/config.py` / `.env.example`. `/stats/budget` reads it directly; no
database table is introduced.

**Rationale:** Resolves the "where does the budget value live" open
question. Matches REQ-004's note ("Budget value sourced from config/.env for
MVP, no per-user storage yet") and CLAUDE.md's single-user MVP assumption.
A settings table would be premature (YAGNI) until multi-budget support
(Phase 2, out of scope).

### 5. Empty-data handling via zeroed/empty responses, not error branches

**Decision:** Every `stats_service` function returns a well-formed empty
result (`[]`, `0`, or `None` for "no product") when there is no matching
data — never raises for "no rows". Routes only raise `HTTPException(404)`
when a path parameter (`product_id`) refers to a resource that does not
exist at all.

**Rationale:** Directly implements AC-004-06. SQL aggregates (`SUM`,
`AVG`) return `NULL` on empty input; `COALESCE(..., 0)` at the query level
avoids `None`-handling branches in Python (KISS).

### 6. Aggregation logic isolated in `stats_service.py`

**Decision:** No aggregation logic in routes or `receipt_service.py`; all
five queries live in the new `backend/services/stats_service.py`, called by
thin route handlers that only map results to Pydantic schemas.

**Rationale:** Matches REQ-004's explicit module placement and ARCH-003's
"routes are thin wrappers" precedent (Single Responsibility).

---

## Out of Scope

- Per-category budgets, multiple budgets, budget persistence in DB → Phase 2+
  (per REQ-004 "Out of Scope").
- ML-based recommendations, clustering, forecasting → Phase 2+.
- CSV/PDF export of statistics → Phase 2+.
- Fuzzy product matching for `top-items`/`price-trend` → products are matched
  by exact name only (CLAUDE.md, unchanged from REQ-002/003).

---

## Open Questions

All three "Questions / Decisions Pending" from REQ-004 are resolved by Key
Decisions above:

1. Budget value location → `Settings.monthly_budget_cents` via `.env`
   (Decision 4).
2. Week definition → ISO weeks (Mon-Sun), labeled by the Monday date
   (Decision 1).
3. Price trend basis → per-unit price (`unit_price_cents`) (Decision 3).
