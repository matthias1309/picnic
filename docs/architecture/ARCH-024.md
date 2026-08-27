# ARCH-024 — Product Categories and Spending by Category

**Status:** draft
**Created:** 2026-08-27
**Traces:** REQ-024
**Verified by:** TEST-024

## Summary

ARCH-024 gives every `Product` exactly one category. The category set and the
keyword rules that assign it are constants in a new
`backend/services/category_service.py`; two nullable/defaulted columns on
`products` store the result and remember whether a human set it. Categories are
applied where products are created (`receipt_service._get_or_create_product`)
and by a repeatable backfill script for existing data.

On top of that, `stats_service` gains one new aggregation
(`get_spending_by_category`) and an optional `category` filter on the two
existing product-level aggregations. The frontend adds a "Ausgaben nach
Kategorie" chart to the statistics page and a new "Artikel" page where a wrong
assignment can be corrected.

---

## Design

### Component Overview

```
┌────────────────────────────────────────────────────────────────────┐
│  frontend                                                           │
│   pages/Articles.tsx      → search + per-product category dropdown  │
│   Charts/CategorySpending.tsx → horizontal bar chart per category   │
│   Charts/PurchaseStats.tsx    → extended: category filter           │
│      ↓ hooks/useCategories.ts, useStats.ts, useProducts.ts          │
└────────────────────────────────────────────────────────────────────┘
                              ↓ HTTP
┌────────────────────────────────────────────────────────────────────┐
│  backend/api/routes.py            (api_router — authenticated)      │
│   GET /categories                                                    │
│   PUT /products/{product_id}/category                                │
│   GET /stats/by-category?from_date&to_date                           │
│   GET /stats/spending?category=…    (extended)                       │
│   GET /stats/top-items?category=…   (extended)                       │
└────────────────────────────────────────────────────────────────────┘
        ↓                                    ↓
┌────────────────────────────┐   ┌──────────────────────────────────┐
│ services/category_service  │   │ services/stats_service           │
│  CATEGORIES (fixed list)   │   │  get_spending_by_category(...)   │
│  CATEGORY_RULES (ordered)  │   │  get_spending_over_time(..., cat)│
│  categorize(name)          │   │  get_top_items(..., category)    │
│  set_product_category(...) │   └──────────────────────────────────┘
│  apply_rules(db)           │
└────────────────────────────┘
        ↑ called on product creation        ↑ called by backfill script
┌────────────────────────────┐   ┌──────────────────────────────────┐
│ services/receipt_service   │   │ scripts/categorize_products.py   │
│  _get_or_create_product    │   │  one-off / repeatable backfill   │
└────────────────────────────┘   └──────────────────────────────────┘
        ↓ reads/writes
┌────────────────────────────────────────────────────────────────────┐
│ models.Product — new: category_key, category_is_manual              │
└────────────────────────────────────────────────────────────────────┘
```

### Data Model

```python
class Product(Base):
    __tablename__ = "products"

    # … existing columns …
    category_key = Column(String(32), nullable=True, index=True)
    category_is_manual = Column(Boolean, nullable=False, default=False, server_default="0")
```

`category_key` is nullable: `NULL` means "not assigned yet" and is reported as
"Nicht zugeordnet", distinct from the explicitly chosen `other` ("Sonstiges").
No foreign key and no `categories` table — the valid keys are a code constant
(Key Decision 1).

**Schema change.** `Base.metadata.create_all` adds missing *tables*, not missing
*columns*, so an existing production database needs the documented manual step,
following the precedent of ARCH-014 (`delivery_date`):

```sql
ALTER TABLE products ADD COLUMN category_key VARCHAR(32);
ALTER TABLE products ADD COLUMN category_is_manual BOOLEAN NOT NULL DEFAULT 0;
CREATE INDEX IF NOT EXISTS ix_products_category_key ON products (category_key);
```

Per CLAUDE.md this migration is reviewed by a human before it runs in
production. It is additive and reversible in effect (both columns are ignored
by the pre-REQ-024 code path).

### Category Service — `backend/services/category_service.py`

```python
class CategoryKey(StrEnum):
    """The fixed set of product categories (AC-024-06)."""

    FRUIT = "fruit"
    VEGETABLES = "vegetables"
    DAIRY = "dairy"
    BAKERY = "bakery"
    MEAT = "meat"
    FISH = "fish"
    FROZEN = "frozen"
    READY_MEALS = "ready_meals"
    BEVERAGES = "beverages"
    PANTRY = "pantry"
    SWEETS = "sweets"
    PERSONAL_CARE = "personal_care"
    HOUSEHOLD = "household"
    OTHER = "other"


CATEGORY_LABELS: dict[CategoryKey, str] = {
    CategoryKey.FRUIT: "Obst",
    CategoryKey.VEGETABLES: "Gemüse",
    # … one German label per key, see REQ-024 …
}

# Ordered: the first matching keyword wins (Key Decision 3).
CATEGORY_RULES: tuple[tuple[str, CategoryKey], ...] = (
    ("kokosmilch", CategoryKey.PANTRY),
    ("hafermilch", CategoryKey.BEVERAGES),
    ("milch", CategoryKey.DAIRY),
    # …
)


def categorize(name: str) -> CategoryKey | None:
    """Return the first category whose keyword occurs in the product name."""
    haystack = name.casefold()
    for keyword, category in CATEGORY_RULES:
        if keyword in haystack:
            return category
    return None
```

`categorize` is a pure function over a string — directly unit-testable per rule
without touching the database, which is where the bulk of the test spec's rule
cases live.

State-changing helpers in the same module:

```python
def set_product_category(db: Session, product_id: int, category_key: CategoryKey) -> Product | None:
    """Assign a category by hand; marks it manual so rules never override it."""

def apply_rules(db: Session) -> int:
    """Categorize all products that have no manual assignment; returns the count changed."""
```

`apply_rules` filters on `Product.category_is_manual.is_(False)` — that single
predicate satisfies both AC-024-04 (manual wins) and AC-024-05 (idempotent: a
second run recomputes the same rule result and writes nothing new).

### Assignment on Parse — `receipt_service._get_or_create_product`

```python
def _get_or_create_product(db: Session, name: str) -> Product:
    product = db.query(Product).filter(Product.name == name).first()
    if product is None:
        product = Product(name=name, category_key=category_service.categorize(name))
        db.add(product)
        db.flush()
    return product
```

Only the *creation* path categorizes (AC-024-01, AC-024-02). An existing product
is never re-categorized during parsing — re-categorization is the backfill
script's job, so parsing stays a pure ingest concern and a manual correction can
never be undone by a later receipt containing the same article.

### Backfill — `backend/scripts/categorize_products.py`

A small CLI in the style of the existing `manage_users.py`: opens a session,
calls `category_service.apply_rules(db)`, prints how many products changed.
Run after the migration and again whenever `CATEGORY_RULES` is extended.

### Statistics — `backend/services/stats_service.py`

```python
def get_spending_by_category(
    db: Session,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[tuple[str | None, int]]:
    """Return total spend per category, highest first (AC-024-07, AC-024-08)."""
    total = func.sum(ReceiptItem.line_total_cents)
    query = (
        db.query(Product.category_key, total)
        .join(ReceiptItem, ReceiptItem.product_id == Product.id)
        .join(Receipt, ReceiptItem.receipt_id == Receipt.id)
    )
    # same effective-date filters as get_spending_over_time (REQ-018)
    return query.group_by(Product.category_key).order_by(total.desc()).all()
```

Grouping by `Product.category_key` puts uncategorised items in their own bucket
(`None`) for free, and because every `ReceiptItem` has exactly one product, the
buckets sum to the same total as `get_spending_over_time` over the same range
(AC-024-07, last clause).

The category filter on the two existing aggregations is one optional parameter
each:

```python
def get_spending_over_time(db, granularity, from_date=None, to_date=None, category=None):
    ...
    if category is not None:
        query = query.join(Product, ReceiptItem.product_id == Product.id).filter(
            Product.category_key == category
        )
```

`get_top_items` already joins `Product`, so it only gains the `filter`.

### Endpoints

| Method | Path | Maps to | Request | Response |
|--------|------|---------|---------|----------|
| GET | `/api/categories` | AC-024-06 | — | `list[CategoryOut]` |
| PUT | `/api/products/{product_id}/category` | AC-024-03, AC-024-10 | `ProductCategoryUpdate {category_key: CategoryKey}` | `ProductOut` |
| GET | `/api/stats/by-category?from_date&to_date` | AC-024-07, AC-024-08 | — | `list[CategorySpending]` |
| GET | `/api/stats/spending?…&category=` | AC-024-09, AC-024-10 | — | `SpendingOverTime` (shape unchanged) |
| GET | `/api/stats/top-items?…&category=` | AC-024-09, AC-024-10 | — | `list[TopItem]` (shape unchanged) |

All are mounted on the authenticated `api_router` (REQ-006, AC-006-04).
`PUT /products/{product_id}/category` returns `404` for an unknown product,
mirroring `GET /products/{product_id}/price-history`.

### Schemas (`backend/schemas.py`)

```python
class CategoryOut(BaseModel):
    key: CategoryKey
    label: str


class ProductCategoryUpdate(BaseModel):
    category_key: CategoryKey


class CategorySpending(BaseModel):
    category_key: CategoryKey | None   # None = "Nicht zugeordnet"
    total_cents: int
```

`ProductOut` gains `category_key: CategoryKey | None`. Typing the field and the
`category` query parameter as `CategoryKey` makes FastAPI/Pydantic reject an
unknown key with `422` at the boundary — AC-024-10 needs no hand-written
validation, the same reasoning as ARCH-011 Key Decision 6.

### Frontend

```
frontend/src/
  types/index.ts                     # + Category, CategoryKey, CategorySpending
                                     #   ProductOut.category_key
  lib/chart-theme.ts                 # + CATEGORY_COLORS: one stable colour per key
  hooks/
    useCategories.ts                 # new: useCategories()
    useProducts.ts                   # + useUpdateProductCategory()
    useStats.ts                      # + useSpendingByCategory(), category args
  components/
    Charts/CategorySpending.tsx      # new: horizontal bar chart, sorted desc
    Charts/PurchaseStats.tsx         # + category filter control
    Products/ProductList.tsx         # new: search + category dropdown per row
  pages/
    Articles.tsx                     # new page, nav entry "Artikel"
  App.tsx                            # + route /articles, + NAV_LINKS entry
```

Labels come from `GET /api/categories` rather than a second hard-coded list in
the frontend; the null bucket renders as the constant "Nicht zugeordnet".

After a successful category change the mutation invalidates `["products"]` and
`["stats"]`, so the article list and every category-aware chart refetch without
a page reload (AC-024-03).

---

## Key Decisions

### 1. Categories are a code constant, not a table

**Decision:** `CategoryKey` (a `StrEnum`) plus a label map in
`category_service.py`; `products.category_key` is a plain string column with no
foreign key.

**Rationale:** REQ-024 fixes the set and explicitly rejects user-managed
categories. A table would buy referential integrity that a `StrEnum` already
provides at the API boundary, and cost a CRUD UI, delete/reassign rules, and a
seed migration. Adding a category later is a one-line code change plus a rerun
of the backfill. The trade-off accepted: *removing* a key later leaves orphaned
strings in `products.category_key`, which the backfill would have to clean up.

### 2. Two columns on `products`, not a separate assignment table

**Decision:** `category_key` and `category_is_manual` live on `products`.

**Rationale:** The relation is 1:1 with the product and REQ-024 rules out
multiple categories per product. A join table would add a query hop to every
statistic for no modelled cardinality. `category_is_manual` is a deliberate
second column rather than an inferred flag — without it, "was this a human
decision or a rule guess?" is unanswerable, and AC-024-04 (a rule must never
overwrite a manual choice) becomes unimplementable.

### 3. Ordered keyword rules, first match wins — product type beats storage form

**Decision:** `CATEGORY_RULES` is an ordered tuple scanned top to bottom, with
specific keywords placed before general ones. Where `frozen` competes with a
type category, the type wins: "Tiefkühl-Pizza" → `ready_meals`, "TK-Erbsen" →
`vegetables`, "Eiscreme" → `sweets`.

**Rationale:** REQ-024 left this open for the test spec; it is settled here
because it shapes the rule table itself, not just its tests. Spending analysis
asks "what did I buy", not "which shelf was it on" — `Fleisch` including the
frozen chicken is a more useful answer than a `Tiefkühl` bucket that mixes peas,
pizza, and ice cream. Ordering is deterministic and each rule is a one-line test
case. See Open Questions for the consequence this has for `frozen`.

### 4. Categorize on product creation, re-categorize only via the backfill

**Decision:** The parse path assigns a category only when it creates a new
product; the backfill script is the only thing that revisits existing products.

**Rationale:** Keeps ingest idempotent and cheap (REQ-016 concurrency
properties are untouched — no additional writes to existing rows during
parsing), and guarantees that a manual correction cannot be silently reverted by
the next delivery containing that article.

### 5. Horizontal bar chart, not a pie

**Decision:** "Ausgaben nach Kategorie" renders as a horizontal bar chart sorted
by spend, descending.

**Rationale:** With up to 14 categories plus the uncategorised bucket, a pie
chart produces slivers that cannot be labelled or compared; ranked bars answer
the actual question ("where does the money go, most first") and reuse the
existing Recharts/`Card`/`SectionHeader` idiom from `PurchaseStats` (REQ-022).

### 6. A categorical palette is added to `chart-theme.ts`

**Decision:** `CATEGORY_COLORS` maps every `CategoryKey` (plus the null bucket)
to a fixed colour, alongside the existing single `series` colour.

**Rationale:** `CHART_COLORS.series` is one colour, sufficient for today's
single-series charts. A breakdown needs a stable colour *per category* so that a
category keeps its identity across periods and across the two charts that show
categories. Fixing the mapping in the theme — rather than indexing into a
palette by array position — prevents colours from shifting when the sort order
changes between periods.

### 7. Category is corrected on a dedicated "Artikel" page

**Decision:** A new route and nav entry listing all products with a search field
and a per-row category dropdown.

**Rationale:** Per REQ-024, correcting inline in the receipt detail would force
the same article to be fixed once per receipt. The article list is also the only
place that can show what is still uncategorised after the backfill, which is the
work the user actually needs to finish. This is the second exception to
ARCH-005 Key Decision 6 ("no new page without a concrete requirement") and is
justified by AC-024-12. The existing `lib/product-search.ts` (REQ-021) is reused
for the search field rather than a second matching implementation.

---

## Out of Scope

- Per-category budgets and threshold warnings — REQ-024 Out of Scope, candidate
  for a follow-up REQ.
- Learning rules from manual corrections, fuzzy matching, sub-categories, or
  more than one category per product — REQ-024 Out of Scope.
- A `categories` CRUD API or settings UI — Key Decision 1.
- Categorising deposit ("Pfand") rows — they are a parser-level topic
  (REQ-012 follow-up), not a categorisation one.
- Alembic — the schema change is a documented manual `ALTER TABLE`, consistent
  with ARCH-013 and ARCH-014.

## Open Questions

1. **Does `frozen` still earn its place?** Under Key Decision 3 nearly every
   frozen article resolves to a type category, so `frozen` degenerates into a
   fallback for items whose type no keyword identifies. It is kept for now
   because REQ-024 lists it, but if the backfill leaves it empty on the real
   data, dropping it (and mapping those products to `other`) is the cleaner
   outcome. Decide after the first backfill run against production data.
2. **Initial rule coverage.** The concrete keyword list is written against the
   product names actually present in the database. How many of them stay
   uncategorised after the first run is unknown until the backfill runs; if the
   share is large, the article list carries the remainder, which is exactly what
   AC-024-12 provides for. No acceptance criterion depends on a coverage
   percentage — deliberately, since it would be untestable against fixtures.
