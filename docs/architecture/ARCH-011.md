# ARCH-011 — Configure Monthly Budget

**Status:** draft
**Created:** 2026-06-15
**Traces:** REQ-011
**Verified by:** TEST-011

## Summary

ARCH-011 makes the monthly budget value editable from the dashboard. It adds
a single-row `budget_settings` table, a small `backend/services/budget_service.py`
module to read/write it, a new `PUT /picnic/api/settings/budget` endpoint
(mounted under the existing authenticated `api_router`), and updates
`GET /api/stats/budget` to read the persisted value (falling back to the
`.env` default if unset). On the frontend, `BudgetWidget.tsx` gains an
inline edit mode.

---

## Design

### Component Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  frontend/src/components/Budget/BudgetWidget.tsx                  │
│   "Edit budget" button                                             │
│     → shows input pre-filled with current budget (euros)           │
│     → "Save": useUpdateBudget().mutate(cents)                       │
│     → "Cancel": discard, close edit mode                            │
│     → on success: invalidate ["stats", "budget", month], close edit │
└──────────────────────────────────────────────────────────────────┘
                              ↓ calls
┌──────────────────────────────────────────────────────────────────┐
│  frontend/src/hooks/useStats.ts                                    │
│   useUpdateBudget() -> useMutation(putJson("/settings/budget", ...))│
└──────────────────────────────────────────────────────────────────┘
                              ↓ HTTP PUT
┌──────────────────────────────────────────────────────────────────┐
│  backend/api/routes.py                                             │
│   PUT /settings/budget  (api_router, requires get_current_user —   │
│   REQ-006)                                                          │
│   GET /stats/budget     (extended: reads persisted value)           │
└──────────────────────────────────────────────────────────────────┘
                              ↓ calls
┌──────────────────────────────────────────────────────────────────┐
│  backend/services/budget_service.py                                │
│   get_monthly_budget_cents(db) -> int                               │
│   set_monthly_budget_cents(db, cents) -> int                        │
└──────────────────────────────────────────────────────────────────┘
                              ↓ reads/writes
┌──────────────────────────────────────────────────────────────────┐
│  backend/models.py — BudgetSetting (table: budget_settings)        │
│   single row, id=1, monthly_budget_cents                            │
└──────────────────────────────────────────────────────────────────┘
```

### Endpoints

| Method | Path | Maps to | Request | Response |
|--------|------|---------|---------|----------|
| GET | `/picnic/api/stats/budget?month=YYYY-MM` | AC-004-04, AC-011-06 | — | `BudgetStatus` (unchanged shape, `budget_cents` now persisted) |
| PUT | `/picnic/api/settings/budget` | AC-011-03, AC-011-05, AC-011-06 | `BudgetSettingUpdate {monthly_budget_cents: int}` | `BudgetSettingOut {monthly_budget_cents: int}` |

### Data Model

```python
class BudgetSetting(Base):
    """Singleton row holding the configured monthly budget (AC-011-06)."""

    __tablename__ = "budget_settings"

    id = Column(Integer, primary_key=True)
    monthly_budget_cents = Column(Integer, nullable=False)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow,
        onupdate=datetime.utcnow, server_default=func.now(),
    )
```

A single row with `id = 1` (`BUDGET_SETTING_ID`) holds the current value.
Created automatically by `Base.metadata.create_all` (existing `init_db()`,
no Alembic migration needed — `create_all` only adds missing tables and does
not alter existing ones, so this is safe to deploy alongside existing data).

### Service — `backend/services/budget_service.py`

```python
BUDGET_SETTING_ID = 1

def get_monthly_budget_cents(db: Session) -> int:
    """Return the persisted monthly budget, or the .env default if unset."""
    row = db.get(BudgetSetting, BUDGET_SETTING_ID)
    if row is None:
        return settings.monthly_budget_cents
    return row.monthly_budget_cents

def set_monthly_budget_cents(db: Session, monthly_budget_cents: int) -> int:
    """Create or update the singleton budget row, returning the new value."""
    row = db.get(BudgetSetting, BUDGET_SETTING_ID)
    if row is None:
        row = BudgetSetting(id=BUDGET_SETTING_ID, monthly_budget_cents=monthly_budget_cents)
        db.add(row)
    else:
        row.monthly_budget_cents = monthly_budget_cents
    db.commit()
    return row.monthly_budget_cents
```

### Schemas (`backend/schemas.py`)

```python
class BudgetSettingUpdate(BaseModel):
    """Request body for PUT /api/settings/budget (AC-011-03, AC-011-05)."""

    monthly_budget_cents: int = Field(ge=0)


class BudgetSettingOut(BaseModel):
    """Response body for PUT /api/settings/budget (AC-011-03)."""

    monthly_budget_cents: int
```

`Field(ge=0)` rejects negative values with a `422` response (Pydantic v2
validation), satisfying the second half of AC-011-05 without manual checks.

### Routes (`backend/api/routes.py`)

```python
@api_router.get("/stats/budget", response_model=BudgetStatus)
def get_budget(month: str = Query(..., pattern=MONTH_PATTERN), db: Session = Depends(get_db)) -> BudgetStatus:
    spent_cents = stats_service.get_spent_for_month(db, month)
    budget_cents = budget_service.get_monthly_budget_cents(db)
    return BudgetStatus(
        month=month, budget_cents=budget_cents,
        spent_cents=spent_cents, remaining_cents=budget_cents - spent_cents,
    )


@api_router.put("/settings/budget", response_model=BudgetSettingOut)
def update_budget(payload: BudgetSettingUpdate, db: Session = Depends(get_db)) -> BudgetSettingOut:
    monthly_budget_cents = budget_service.set_monthly_budget_cents(db, payload.monthly_budget_cents)
    return BudgetSettingOut(monthly_budget_cents=monthly_budget_cents)
```

### Frontend Flow — `BudgetWidget`

```
BudgetWidget (default: read-only view, AC-005-05 unchanged)
  "Edit budget" button
    → setIsEditing(true), local state initialized from data.budget_cents / 100
  Edit mode:
    <input type="number" min="0" step="0.01" value={draftEuros} />
    "Save" button
      → validate draftEuros >= 0 (else show inline error, AC-011-05)
      → updateBudget.mutate({ monthly_budget_cents: Math.round(draftEuros * 100) })
           mutationFn: () => putJson("/settings/budget", body)
           onSuccess:
             - queryClient.invalidateQueries({ queryKey: ["stats", "budget"] })
             - setIsEditing(false)
    "Cancel" button
      → setIsEditing(false), discard draft (no request, AC-011-04)
```

### Module Layout

```
backend/
  models.py                    # new: BudgetSetting
  schemas.py                   # new: BudgetSettingUpdate, BudgetSettingOut
  services/
    budget_service.py          # new: get/set_monthly_budget_cents
  api/
    routes.py                  # extended: PUT /settings/budget, GET /stats/budget reads DB

frontend/
  src/
    api/
      client.ts                # extended: putJson<T>(path, body) -> Promise<T>
    hooks/
      useStats.ts               # extended: useUpdateBudget()
    components/
      Budget/
        BudgetWidget.tsx         # extended: edit mode (input, Save/Cancel)
```

---

## Key Decisions

### 1. Single-row `budget_settings` table (singleton), not a generic key-value `settings` table

**Decision:** A dedicated table with one row (`id = 1`) holding
`monthly_budget_cents`, rather than a generic `settings(key, value)` table.

**Rationale:** YAGNI — there is exactly one configurable setting today. A
generic key-value store would need a serialization/typing layer for no
current benefit, and a typed column is simpler to query and validate. If
more settings are added later, a migration to a generic table (or additional
columns on this table) is straightforward.

### 2. `.env` `MONTHLY_BUDGET_CENTS` becomes the initial-seed fallback, not the source of truth

**Decision:** `budget_service.get_monthly_budget_cents` returns
`settings.monthly_budget_cents` only when no `budget_settings` row exists
yet. Once the user saves a value via the UI, the database row is the source
of truth and the `.env` value is ignored.

**Rationale:** Keeps AC-004-04 backward compatible for existing deployments
(no behavior change until the user explicitly configures a budget) while
satisfying AC-011-06 (persisted, restart-safe). No migration script is
needed to "copy" the `.env` value into the database — the fallback makes
that copy implicit and lazy.

### 3. New `PUT /settings/budget` endpoint, separate from `GET /stats/budget`

**Decision:** The mutation lives at `/settings/budget` (a configuration
resource) rather than `PUT /stats/budget?month=...` (a derived
statistics resource).

**Rationale:** `/stats/*` endpoints (REQ-004) are framed as read-only
derived views (spend vs. budget for a month); the budget *value* itself is
configuration, not a statistic. Separating the two keeps `GET /stats/budget`
semantics unchanged (still takes `month`, still returns `BudgetStatus`) and
gives the setting its own small, focused resource and schema pair
(`BudgetSettingUpdate` / `BudgetSettingOut`), consistent with Command-Query
Separation (`coding-style.md`).

### 4. No standalone `GET /settings/budget` endpoint

**Decision:** Only `PUT /settings/budget` is added; there is no
`GET /settings/budget`.

**Rationale:** YAGNI — `BudgetWidget` already fetches `budget_cents` via
`useBudget(month)` (`GET /stats/budget`) for the read-only display, and uses
that same value to pre-fill the edit form (AC-011-02). A second read endpoint
returning the identical number would duplicate `GET /stats/budget` for no
additional information.

### 5. Inline edit in `BudgetWidget`, no Settings page

**Decision:** Edit mode (button → input → Save/Cancel) lives directly in
`BudgetWidget.tsx`.

**Rationale:** Consistent with ARCH-005 Key Decision 6 — a Settings page was
explicitly deferred until a concrete requirement exists. This is the first
and only user-configurable setting; a single inline control is simpler than
introducing a new route, page, and nav entry (KISS/YAGNI).

### 6. Validation: `Field(ge=0)` on the backend, numeric input + inline check on the frontend

**Decision:** The Pydantic schema rejects negative values with `422`
(backend, authoritative). The frontend additionally validates the entered
value is `>= 0` before sending the request, showing an inline error and not
calling the API for invalid input (AC-011-05).

**Rationale:** Defense in depth at the system boundary (Pydantic) plus fast
user feedback (frontend) without a round-trip for an obviously invalid input.

---

## Out of Scope

- Per-category or per-month budgets — REQ-011 Notes / REQ-004 Out of Scope.
- A dedicated Settings page — Key Decision 5.
- `GET /settings/budget` — Key Decision 4.
- Alembic migration — `create_all` adds the new table without altering
  existing tables (see Data Model).
