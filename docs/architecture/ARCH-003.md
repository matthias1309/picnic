# ARCH-003 — REST API for Receipt and Product Data

**Status:** draft
**Created:** 2026-06-14
**Traces:** REQ-003
**Verified by:** TEST-003

## Summary

ARCH-003 defines the read-only REST API that exposes the normalized data
produced by REQ-002 (`receipts`, `receipt_items`, `products`, `price_history`)
to the frontend (REQ-005). Routes are thin FastAPI wrappers around new query
functions in `backend/services/receipt_service.py`; response shapes are
documented as Pydantic models in `backend/schemas.py`. All endpoints are
mounted under `/picnic/api/...` (the existing `/picnic` prefix from
`backend/main.py`).

---

## Design

### Component Overview

```
┌──────────────────────────────────────────────────────────────┐
│  FastAPI app (backend/main.py)                                │
│   router = APIRouter(prefix="/picnic")                        │
│     includes api_router = APIRouter(prefix="/api")            │  ← new
│       → /picnic/api/receipts                                  │
│       → /picnic/api/receipts/{id}                             │
│       → /picnic/api/products                                  │
│       → /picnic/api/products/{id}/price-history               │
└──────────────────────────────────────────────────────────────┘
                              ↓ depends on
┌──────────────────────────────────────────────────────────────┐
│  backend/api/dependencies.py                                  │
│   get_db_session = Depends(database.get_db)                   │  (re-export)
└──────────────────────────────────────────────────────────────┘
                              ↓ calls
┌──────────────────────────────────────────────────────────────┐
│  backend/services/receipt_service.py  (new query functions)  │
│   list_receipts(db, limit, offset, from_date, to_date)        │
│     -> (items: list[ReceiptSummary], total: int)              │
│   get_receipt_with_items(db, receipt_id) -> Receipt | None     │
│   list_products(db) -> list[ProductWithCount]                  │
│   get_product_with_price_history(db, product_id)               │
│     -> Product | None                                          │
└──────────────────────────────────────────────────────────────┘
                              ↓ maps to
┌──────────────────────────────────────────────────────────────┐
│  backend/schemas.py  (Pydantic response models)               │
│   ReceiptSummary, ReceiptItemOut, ReceiptDetail,                │
│   PaginatedReceipts, ProductOut, PriceHistoryPoint,             │
│   ProductPriceHistory                                           │
└──────────────────────────────────────────────────────────────┘
```

### Endpoints

| Method | Path | Maps to | Response |
|--------|------|---------|----------|
| GET | `/picnic/api/receipts` | AC-003-01, AC-003-06 | `PaginatedReceipts` |
| GET | `/picnic/api/receipts/{receipt_id}` | AC-003-02 | `ReceiptDetail` |
| GET | `/picnic/api/products` | AC-003-03 | `list[ProductOut]` |
| GET | `/picnic/api/products/{product_id}/price-history` | AC-003-04 | `ProductPriceHistory` |

### Data Flow — `GET /api/receipts`

```
GET /picnic/api/receipts?limit=20&offset=0&from_date=2026-01-01&to_date=2026-06-30
        ↓
routes.list_receipts_endpoint(limit, offset, from_date, to_date, db)
        ↓
receipt_service.list_receipts(db, limit, offset, from_date, to_date)
        ↓
  query = select(Receipt)
  if from_date: filter received_date >= from_date
  if to_date:   filter received_date <= to_date
  total = count(*) over the filtered query
  rows  = query
            .order_by(Receipt.received_date.desc())
            .limit(limit).offset(offset)
  for each row: item_count = len(receipt.items)
                total_cents = sum(item.line_total_cents for item in receipt.items)
        ↓
PaginatedReceipts(items=[ReceiptSummary(...)], total=total, limit=limit, offset=offset)
```

### Data Flow — `GET /api/receipts/{id}`

```
receipt = db.get(Receipt, receipt_id)  (with items + product eagerly loaded)
if receipt is None: raise HTTPException(404, "Receipt not found")
ReceiptDetail(
  id, received_date, from_address,
  items=[ReceiptItemOut(product_name, quantity, unit_price_cents, line_total_cents) ...],
  total_cents=sum(item.line_total_cents for item in receipt.items),
)
```

### Data Flow — `GET /api/products`

```
SELECT products.*, COUNT(receipt_items.id) AS purchase_count
FROM products LEFT JOIN receipt_items ON receipt_items.product_id = products.id
GROUP BY products.id
ORDER BY products.name
        ↓
[ProductOut(id, name, purchase_count) ...]
```

### Data Flow — `GET /api/products/{id}/price-history`

```
product = db.get(Product, product_id)
if product is None: raise HTTPException(404, "Product not found")
points = db.query(PriceHistory)
           .filter(product_id == id)
           .order_by(PriceHistory.recorded_date.asc())
ProductPriceHistory(
  product_id, product_name,
  points=[PriceHistoryPoint(date, unit_price_cents, quantity) ...],
)
```

### Pagination & Filtering (AC-003-06)

| Param | Default | Constraint |
|-------|---------|------------|
| `limit` | 20 | `1 <= limit <= 100` (validated by FastAPI/Pydantic via `Query(...)`) |
| `offset` | 0 | `offset >= 0` |
| `from_date` | none | inclusive lower bound on `received_date` (ISO date) |
| `to_date` | none | inclusive upper bound on `received_date` (ISO date) |

Constants `DEFAULT_PAGE_SIZE = 20` and `MAX_PAGE_SIZE = 100` live in
`backend/api/routes.py`.

### Error Contract (AC-003-05)

FastAPI's built-in exception handling is used as-is:
- `HTTPException(status_code=404, detail="Receipt not found")` /
  `"Product not found"` → `{"detail": "Receipt not found"}` with HTTP 404.
- Invalid query params (e.g. `limit=0`, malformed `from_date`) → HTTP 422 with
  FastAPI's standard `{"detail": [...]}` validation error body.
- All success responses are typed via `response_model=...` so the OpenAPI
  schema (`/docs`) documents the contract, satisfying "documented Pydantic
  response schema".

No custom exception handlers are introduced — FastAPI's default `{"detail":
...}` shape is already consistent and documented in the OpenAPI schema.

### Module Layout

```
backend/
  schemas.py                 # new: Pydantic response models (this REQ)
  api/
    dependencies.py          # new: get_db dependency re-export
    routes.py                 # new: receipts/products/price-history routers
  services/
    receipt_service.py        # extended: list_receipts, get_receipt_with_items,
                               #           list_products, get_product_with_price_history
```

`backend/main.py` mounts the new router:

```python
from backend.api.routes import api_router
router.include_router(api_router)  # router already has prefix="/picnic"
```

---

## Key Decisions

### 1. Amounts stay as integer cents in API responses

**Decision:** `unit_price_cents`, `line_total_cents`, `total_cents` are
returned as integers (cents), matching internal storage (per ARCH-002 and
CLAUDE.md decision to avoid float rounding).

**Rationale:** Single source of truth for currency formatting — the frontend
(REQ-005) decides display formatting (`€3.49`). Avoids float precision issues
crossing the API boundary. Field names carry the `_cents` suffix to make the
unit unambiguous in the OpenAPI schema.

### 2. Pagination: `limit`/`offset` with fixed bounds

**Decision:** `limit` defaults to 20, capped at 100; `offset` defaults to 0.
Both validated via FastAPI `Query(..., ge=..., le=...)`.

**Rationale:** Simple, well-understood pattern; matches AC-003-06 example
(`?limit=20&offset=40`) directly. A hard cap of 100 prevents accidentally
expensive full-table responses without adding cursor-based complexity (YAGNI
for a single-user MVP with low data volume).

### 3. Read-only query functions live in `receipt_service.py`

**Decision:** No new service module; `list_receipts`, `get_receipt_with_items`,
`list_products`, `get_product_with_price_history` are added to the existing
`backend/services/receipt_service.py`.

**Rationale:** These are read accessors over the same `Receipt`/`Product`
aggregate already owned by `receipt_service.py` (per ARCH-002). Splitting into
a separate `product_service.py` for four query functions would be premature
(YAGNI); `stats_service.py` (REQ-004) remains the place for aggregation logic.

### 4. `total_cents` is computed, not stored

**Decision:** A receipt's total is computed as
`sum(item.line_total_cents for item in receipt.items)` at query time (in SQL
via aggregation for the list endpoint, in Python for the single-receipt
endpoint where items are already loaded).

**Rationale:** Avoids a denormalized, potentially stale `receipts.total_cents`
column. Receipt item counts are small (a handful per receipt), so summing in
Python for the detail endpoint is negligible; the list endpoint uses a SQL
`GROUP BY`/aggregate join to avoid N+1 queries.

### 5. Eager loading to avoid N+1 queries

**Decision:** `list_receipts` and `get_receipt_with_items` use SQLAlchemy
`selectinload`/`joinedload` for `Receipt.items` and `ReceiptItem.product`.

**Rationale:** Each receipt has multiple items, each referencing a product
(for `product_name`). Without eager loading, listing N receipts would trigger
N additional queries. `selectinload` keeps this at O(1) extra queries.

---

## Out of Scope

- **Authentication / authorization** → single-user MVP (CLAUDE.md).
- **Write endpoints** (create/update/delete receipts or products) → Phase 2+.
- **Statistics/aggregation endpoints** (`/api/stats/*`) → REQ-004.
- **Rate limiting / response caching headers** → Phase 2+.
- **Cursor-based pagination** → `limit`/`offset` sufficient for MVP data volume.

---

## Open Questions

All three "Questions / Decisions Pending" from REQ-003 are resolved by
Key Decisions 1 and 2 above:

1. Default/max page size → 20 / 100 (Decision 2).
2. Totals format → integer cents (Decision 1).
3. CORS origins → already configurable via `CORS_ORIGINS` in `.env`
   (`backend/config.py`); no change needed for this REQ.
