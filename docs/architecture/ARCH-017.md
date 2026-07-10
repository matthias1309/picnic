# ARCH-017 — Budget History Grid (Last 12 Months)

**Status:** draft
**Created:** 2026-07-10
**Traces:** REQ-017
**Verified by:** TEST-017

## Summary

Extend the home dashboard so that, below the existing editable current-month `BudgetWidget`, a
list of 12 read-only budget boxes is rendered — one per preceding month. No backend change is
needed: `GET /api/stats/budget?month=YYYY-MM` already accepts an arbitrary month and computes
`spent_cents` per month from `Receipt.effective_date`; `budget_cents` is a global singleton and is
simply repeated across all months.

## Design

**New helper** — `frontend/src/lib/format.ts`:

```ts
export function getPastMonths(n: number, today: Date = new Date()): string[]
```

Returns the `n` months immediately preceding the month of `today`, most-recent first, as
`YYYY-MM` strings (e.g. for `today = 2026-07-10`, `getPastMonths(3)` → `["2026-06", "2026-05",
"2026-04"]`).

**Extracted presentational component** — `frontend/src/components/Budget/BudgetStatusCard.tsx`:

The display markup currently inlined in `BudgetWidget` (spend/budget line, progress bar,
over/under-budget text and color) is extracted into a presentational component:

```ts
interface BudgetStatusCardProps {
  data: BudgetStatus;
  action?: ReactNode;      // optional header control, e.g. "Edit budget" button
  testId?: string;         // defaults to "budget-widget" for back-compat with existing tests
}
```

`BudgetWidget` renders `<BudgetStatusCard data={data} action={editButtonOrNothing} />` for the
current month, unchanged in behavior. `BudgetWidget`'s edit-mode form stays in `BudgetWidget`
itself (only the read-only display fragment is extracted).

**New component** — `frontend/src/components/Budget/BudgetHistory.tsx`:

- Computes `months = getPastMonths(12)`.
- Uses TanStack Query's `useQueries` (v5) to fire one `/stats/budget?month=...` request per month,
  reusing the same `queryFn` shape as `useBudget` (same query key prefix `["stats", "budget",
  month]` so cache entries are shared with `BudgetWidget` when months overlap, e.g. after a
  month rolls over).
- Renders one `<BudgetStatusCard data={...} testId="budget-history-card" />` per resolved month
  (no `action` prop → no edit control), each independently showing its own loading/error state
  inline (skip a month's card while its query is loading; show a minimal inline error for a card
  whose query failed, without blocking the other 11).

**Home page** — `frontend/src/pages/Home.tsx`:

```tsx
<Dashboard />
<BudgetWidget />
<BudgetHistory />
```

```
Home
 ├─ Dashboard            (existing)
 ├─ BudgetWidget          (current month, editable)
 │   └─ BudgetStatusCard  (extracted display fragment)
 └─ BudgetHistory         (new)
     └─ BudgetStatusCard × 12  (read-only)
```

## Key Decisions

- **No backend change.** The existing `/stats/budget` endpoint already supports arbitrary months
  and computes real per-month spend; only the frontend needs to call it 12 more times. Adding a
  historical per-month budget table is explicitly out of scope (see REQ-017 Notes).
- **Extract `BudgetStatusCard` rather than duplicate JSX.** Keeps the visual style (DRY per
  project coding-style rules) identical between the current-month and historical boxes by
  construction, instead of copy-pasting the progress-bar/coloring markup.
- **`useQueries` over a loop of `useBudget` calls.** Hooks cannot be called in a loop/array
  directly; `useQueries` is the React-Query-idiomatic way to fire a dynamic number of parallel
  queries from one array of month strings.
- **Distinct `testId` for history cards** (`budget-history-card` vs. `budget-widget`) so existing
  `BudgetWidget` tests (which query `getByTestId("budget-widget")` expecting a single match) keep
  passing once both components render together on the real `Home` page.

## Out of Scope

- Per-month historical budget amounts (would require a new `budget_history` table + service +
  route changes).
- Pagination/lazy-loading beyond 12 months, and any "load more" UI.
- Editing a historical month's budget.

## Open Questions

None — existing API and data model are sufficient for this story.
