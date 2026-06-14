# ARCH-005 — React Dashboard

**Status:** draft
**Created:** 2026-06-14
**Traces:** REQ-005
**Verified by:** TEST-005

## Summary

ARCH-005 sets up the `frontend/` Vite + React + TypeScript SPA and implements
the dashboard views consuming the read-only REST API from REQ-003/REQ-004
(`/picnic/api/...`). It covers three routed pages (Home, Stats, Receipts),
shared data-fetching hooks built on TanStack Query, a small Zustand store for
UI-only state (selected time ranges / aggregation period), and Recharts-based
visualizations. Resolves the three open questions from REQ-005:

- **Routing:** multi-route via React Router (`/`, `/stats`, `/receipts`, `/receipts/:id`).
- **API access in dev:** Vite dev-server proxy forwards `/picnic/*` to the
  FastAPI backend (`http://localhost:8000`), matching the `/picnic` prefix
  used in production (see `backend/main.py`). The frontend always calls
  relative paths under `/picnic/api`.
- **Theme:** Tailwind utility classes — green (`text-green-600` /
  `bg-green-50`) for under-budget / falling price, red (`text-red-600` /
  `bg-red-50`) for over-budget / rising price, gray for neutral/no-change.

---

## Design

### Component Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  frontend/ (Vite + React 18 + TypeScript)                             │
│                                                                        │
│  src/main.tsx                                                          │
│    -> QueryClientProvider (TanStack Query)                            │
│    -> BrowserRouter                                                    │
│       -> App.tsx (layout: nav + <Routes>)                              │
│          ├── "/"            -> pages/Home.tsx                          │
│          ├── "/stats"        -> pages/Stats.tsx                        │
│          └── "/receipts"     -> pages/Receipts.tsx                     │
│              "/receipts/:id"    (detail view within same page)         │
└──────────────────────────────────────────────────────────────────────┘
                              ↓ uses
┌──────────────────────────────────────────────────────────────────────┐
│  src/hooks/  (TanStack Query hooks, one per resource)                  │
│    useSummary()            -> GET /picnic/api/stats/summary            │
│    useBudget(month)        -> GET /picnic/api/stats/budget             │
│    useSpending(params)     -> GET /picnic/api/stats/spending           │
│    useTopItems(limit)      -> GET /picnic/api/stats/top-items          │
│    useProducts()           -> GET /picnic/api/products                 │
│    usePriceTrend(id, range)-> GET /picnic/api/stats/price-trend/{id}   │
│    useReceipts(page)       -> GET /picnic/api/receipts                 │
│    useReceiptDetail(id)    -> GET /picnic/api/receipts/{id}            │
└──────────────────────────────────────────────────────────────────────┘
                              ↓ calls
┌──────────────────────────────────────────────────────────────────────┐
│  src/api/client.ts                                                     │
│    fetchJson<T>(path, params?) -> Promise<T>                          │
│    Base path: "/picnic/api" (relative — proxied in dev, same-origin    │
│    reverse proxy in prod)                                              │
└──────────────────────────────────────────────────────────────────────┘
```

### Pages → Components → ACs

| Page | Components | ACs |
|---|---|---|
| `pages/Home.tsx` | `components/Dashboard.tsx` (summary cards), `components/Budget/BudgetWidget.tsx` | AC-005-01, AC-005-05, AC-005-06 |
| `pages/Stats.tsx` | `components/Charts/PurchaseStats.tsx` (top items + spending-over-time, period switch), `components/Charts/PriceHistory.tsx` (product selector + range switch) | AC-005-02, AC-005-03, AC-005-06 |
| `pages/Receipts.tsx` | `components/Receipts/ReceiptList.tsx`, `components/Receipts/ReceiptDetail.tsx` | AC-005-04, AC-005-06 |

Shared building blocks in `components/common/`:
`LoadingSpinner.tsx`, `ErrorMessage.tsx`, `EmptyState.tsx` — used by every
data-bound component to satisfy AC-005-06 consistently.

### Module Layout

```
frontend/
  src/
    api/
      client.ts            # fetchJson<T>() wrapper, base path "/picnic/api"
    types/
      index.ts              # TS interfaces mirroring backend/schemas.py
    hooks/
      useStats.ts            # useSummary, useBudget, useSpending, useTopItems, usePriceTrend
      useReceipts.ts         # useReceipts (paginated), useReceiptDetail
      useProducts.ts         # useProducts
    store/
      useUiStore.ts          # Zustand: priceHistory range, stats period
    components/
      Dashboard.tsx
      Budget/
        BudgetWidget.tsx
      Charts/
        PriceHistory.tsx
        PurchaseStats.tsx
      Receipts/
        ReceiptList.tsx
        ReceiptDetail.tsx
      common/
        LoadingSpinner.tsx
        ErrorMessage.tsx
        EmptyState.tsx
    pages/
      Home.tsx
      Stats.tsx
      Receipts.tsx
    App.tsx                  # router + nav layout
    main.tsx                 # entrypoint, QueryClientProvider + BrowserRouter
  tests/
    Dashboard.test.tsx
    Charts.test.tsx
    Receipts.test.tsx
    Budget.test.tsx
  vite.config.ts
  tsconfig.json
  tailwind.config.js
  package.json
```

### Data Flow — Home page (AC-005-01, AC-005-05)

```
Home.tsx mounts
  -> useSummary() -> GET /picnic/api/stats/summary -> SummaryStats
  -> useBudget(currentMonth) -> GET /picnic/api/stats/budget?month=YYYY-MM -> BudgetStatus
While loading: <LoadingSpinner />
On error: <ErrorMessage onRetry={refetch} />
On success:
  Dashboard.tsx renders summary cards (total spend, receipt count,
    distinct products, avg basket, current month spend)
  BudgetWidget.tsx renders spent vs. budget bar;
    remaining_cents < 0 -> "over budget" styling (red), else green
```

### Data Flow — Stats page (AC-005-02, AC-005-03)

```
Stats.tsx mounts
  -> useUiStore: aggregationPeriod ("week" | "month"), default "month"
  -> useSpending({granularity: aggregationPeriod}) -> SpendingOverTime
  -> useTopItems(10) -> TopItem[]
  -> useProducts() -> ProductOut[] (for price-history product selector)

PurchaseStats.tsx
  - renders top items as a horizontal bar chart (Recharts BarChart)
  - renders spending-over-time as a line/bar chart (Recharts)
  - period toggle (week/month) updates useUiStore -> refetches useSpending

PriceHistory.tsx
  - product <select> (from useProducts())
  - range toggle: 3m / 6m / 12m / all -> computed from_date/to_date in
    useUiStore, passed to usePriceTrend(productId, {from_date, to_date})
  - renders Recharts LineChart of unit_price_cents over date
  - shows min/max/avg from PriceTrend response
```

### Data Flow — Receipts page (AC-005-04)

```
Receipts.tsx
  -> useUiStore: receiptsPage (offset), pageSize = 20
  -> useReceipts({limit, offset}) -> PaginatedReceipts, sorted by
     received_date desc (already guaranteed by backend)
  -> ReceiptList.tsx renders rows + pagination controls (prev/next using
     total/limit/offset)
  -> on row click: navigate("/receipts/:id")
  -> Receipts.tsx (detail route) -> useReceiptDetail(id) -> ReceiptDetail
  -> ReceiptDetail.tsx renders line items (product, quantity, unit price,
     line total) + receipt total
```

### Server State & Resilience (AC-005-06)

- Single shared `QueryClient` (in `main.tsx`) with defaults:
  `staleTime: 60_000`, `retry: 1`.
- Every hook returns `{ data, isLoading, isError, error, refetch }` from
  `useQuery` — no custom wrapping.
- `ErrorMessage` component takes a `message` and `onRetry` callback; used
  uniformly so failed requests degrade gracefully instead of crashing.
- `EmptyState` component renders when a successful response contains no
  items (empty receipts list, no price history points, etc.).

### TypeScript Types (`src/types/index.ts`)

Mirror `backend/schemas.py` 1:1 (same field names, `snake_case` to match
JSON payloads — no client-side renaming):

```typescript
export interface SummaryStats {
  total_spend_cents: number;
  receipt_count: number;
  distinct_product_count: number;
  average_basket_cents: number;
  current_month_spend_cents: number;
}

export interface BudgetStatus {
  month: string;
  budget_cents: number;
  spent_cents: number;
  remaining_cents: number;
}

export interface SpendingBucket {
  period: string;
  total_cents: number;
}

export interface SpendingOverTime {
  granularity: "week" | "month";
  buckets: SpendingBucket[];
}

export interface TopItem {
  product_id: number;
  product_name: string;
  total_quantity: number;
  total_spend_cents: number;
}

export interface PriceTrendPoint {
  date: string;
  unit_price_cents: number;
  quantity: number;
}

export interface PriceTrend {
  product_id: number;
  product_name: string;
  points: PriceTrendPoint[];
  min_price_cents: number;
  max_price_cents: number;
  avg_price_cents: number;
}

export interface ProductOut {
  id: number;
  name: string;
  purchase_count: number;
}

export interface ReceiptSummary {
  id: number;
  received_date: string;
  from_address: string;
  item_count: number;
  total_cents: number;
}

export interface PaginatedReceipts {
  items: ReceiptSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface ReceiptItemOut {
  product_name: string;
  quantity: number;
  unit_price_cents: number;
  line_total_cents: number;
}

export interface ReceiptDetail {
  id: number;
  received_date: string;
  from_address: string;
  items: ReceiptItemOut[];
  total_cents: number;
}
```

---

## Key Decisions

1. **Multi-route layout (React Router)** over a single tabbed page — pages
   map directly to the `pages/` files already named in CLAUDE.md
   (`Home.tsx`, `Stats.tsx`), and deep-linking to `/receipts/:id` is useful
   for a receipt detail view. React Router is a standard, lightweight
   addition consistent with "Vite + React 18 + TS" — no new state-management
   pattern introduced.

2. **Vite dev proxy to `/picnic`** — the production deployment already
   reverse-proxies `/picnic/*` to the backend (see `backend/main.py`
   comment). Using the same relative base path in dev (via
   `vite.config.ts` `server.proxy`) means `src/api/client.ts` needs no
   environment-specific base URL logic, and CORS does not need to be
   configured for the dev server.

3. **`snake_case` TypeScript interfaces** mirroring Pydantic schemas exactly
   — avoids a mapping/transform layer (YAGNI); the API is internal and
   stable (REQ-003/004 already shipped). Money stays as integer `_cents`
   fields end-to-end; formatting to currency strings happens only at render
   time via a small `formatCents()` helper.

4. **One hook per endpoint, returning the raw TanStack Query result** —
   keeps hooks thin and testable (mock `fetchJson`, assert hook behavior),
   avoids a custom state-management layer duplicating what TanStack Query
   already provides.

5. **Zustand only for UI-only state** (selected period/range/pagination
   offset) — no server data is ever duplicated into Zustand, avoiding cache
   inconsistency between TanStack Query and Zustand.

6. **Settings page is not part of this architecture** — REQ-005 explicitly
   marks IMAP credential UI as Phase 2 / out of scope, and there is no other
   user-configurable setting in the MVP (budget is read from backend
   config). `pages/Settings.tsx` is deferred until a concrete requirement
   exists.

7. **Production base path `/picnic-frontend/`** — the built SPA is served
   by Uberspace as static files under `https://matt-maxx.de/picnic-frontend/`
   (document root `~/html/picnic-frontend/`), separate from the backend's
   `/picnic/api/*` path-based proxy (see `backend/main.py`). Both live under
   the same origin (`matt-maxx.de`), so `src/api/client.ts`'s relative
   `/picnic/api` base path works unchanged regardless of where the page
   itself is served from.
   - `vite.config.ts` sets `base: "/picnic-frontend/"` only for `vite build`
     (the dev server keeps `base: "/"` so `npm run dev` needs no prefix).
   - `main.tsx` passes `import.meta.env.BASE_URL` (Vite's reflection of
     `base`) as the React Router `basename`, so routing works under both
     the dev root and the production sub-path without per-environment code.
   - `scripts/deploy.sh` copies `frontend/dist` to `~/html/picnic-frontend/`
     after `npm run build`. This is a deployment-script change with no
     testable application logic — covered by the existing build/lint/test
     gates in CI, not by new unit tests (TDD exception per
     `.claude/rules/v-model.md`: "provably untestable... one-off
     migration/deployment script").

---

## Out of Scope

- Authentication / login.
- IMAP credential management UI (`Settings/IMAPConfig.tsx`).
- Real-time updates / websockets — TanStack Query refetch/staleTime only.
- Server-side rendering.
- Editing/mutating data — the API and this UI are read-only.

---

## Open Questions

None — all three pending questions from REQ-005 are resolved above (see
Summary and Key Decisions).
