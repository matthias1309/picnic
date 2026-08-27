# TEST-024 — Product Categories and Spending by Category Tests

**Status:** draft
**Created:** 2026-08-27
**Traces:** ARCH-024
**Verifies:** REQ-024 (AC-024-01, AC-024-02, AC-024-03, AC-024-04, AC-024-05,
AC-024-06, AC-024-07, AC-024-08, AC-024-09, AC-024-10, AC-024-11, AC-024-12)

---

## Test Cases

### TC-024-01 — A new product is categorised by rule on creation

**Maps to:** AC-024-01
**Type:** unit (in-memory SQLite)
**File:** `backend/tests/test_categories.py`

```gherkin
Given no product named "Bio Vollmilch 3,8% 1L" exists
And a keyword rule maps "milch" to the category "dairy"
When a receipt containing "Bio Vollmilch 3,8% 1L" is parsed
Then the created product has category_key "dairy"
And the assignment is marked as rule-based, not manual
```

**Notes:** Drives the product through `receipt_service._get_or_create_product`
rather than constructing `Product` directly — the AC is about the parse path.
Asserts `category_is_manual is False`, not just the key.

---

### TC-024-02 — A product without a matching rule stays uncategorised

**Maps to:** AC-024-02
**Type:** unit (in-memory SQLite)
**File:** `backend/tests/test_categories.py`

```gherkin
Given no keyword rule matches the product name "Ahoi-Brause Sortiment"
When a receipt containing that article is parsed
Then the created product has category_key None
```

**Notes:** The fixture name must be one no rule can match; if a later rule
addition claims it, this test fails loudly, which is the intent.

---

### TC-024-03 — `categorize` is case- and position-insensitive

**Maps to:** AC-024-01
**Type:** unit (pure function, no DB)
**File:** `backend/tests/test_categories.py`

```gherkin
Given the rule ("milch", "dairy")
When categorize is called with "MILCH 1L", "Bio Vollmilch" and "vollmilch bio"
Then every call returns CategoryKey.DAIRY
```

**Notes:** `categorize` is pure, so the rule table gets cheap per-rule coverage
here rather than through the database.

---

### TC-024-04 — Rule order resolves false friends and overlaps

**Maps to:** AC-024-01 (ARCH-024 Key Decision 3)
**Type:** unit (pure function, no DB)
**File:** `backend/tests/test_categories.py`

```gherkin
Given the ordered rule table
When categorize is called with "Kokosmilch 400ml"
Then it returns CategoryKey.PANTRY, not DAIRY

When categorize is called with "Tiefkühl-Pizza Margherita"
Then it returns CategoryKey.READY_MEALS, not FROZEN

When categorize is called with "TK-Erbsen 750g"
Then it returns CategoryKey.VEGETABLES, not FROZEN
```

**Notes:** This is the executable form of Key Decision 3 (product type beats
storage form). Each case pins one ordering constraint in `CATEGORY_RULES`;
reordering the table must break this test.

---

### TC-024-05 — A category can be assigned by hand

**Maps to:** AC-024-03
**Type:** unit (in-memory SQLite)
**File:** `backend/tests/test_categories.py`

```gherkin
Given the product "Ahoi-Brause Sortiment" is uncategorised
When category_service.set_product_category(db, product.id, CategoryKey.SWEETS) is called
Then the product has category_key "sweets"
And category_is_manual is True
```

---

### TC-024-06 — A manual assignment is never overwritten by a rule

**Maps to:** AC-024-04
**Type:** unit (in-memory SQLite)
**File:** `backend/tests/test_categories.py`

```gherkin
Given the product "Kokosmilch 400ml" was manually assigned to "pantry"
When category_service.apply_rules(db) runs
Then the product still has category_key "pantry"
And category_is_manual is still True
```

**Notes:** Uses a product name that a rule *would* claim, so the test fails if
`apply_rules` forgets the `category_is_manual` predicate.

---

### TC-024-07 — The backfill categorises existing products

**Maps to:** AC-024-05
**Type:** unit (in-memory SQLite)
**File:** `backend/tests/test_categories.py`

```gherkin
Given products exist with category_key None
When category_service.apply_rules(db) runs
Then every product whose name matches a rule receives that category
And the number of changed products is returned
```

---

### TC-024-08 — The backfill is idempotent

**Maps to:** AC-024-05
**Type:** unit (in-memory SQLite)
**File:** `backend/tests/test_categories.py`

```gherkin
Given category_service.apply_rules(db) has already run
When it runs a second time
Then it reports 0 changed products
And no product's category_key or category_is_manual differs from the first run
```

---

### TC-024-09 — `GET /api/categories` serves the fixed list

**Maps to:** AC-024-06
**Type:** integration (FastAPI TestClient)
**File:** `backend/tests/test_api.py`

```gherkin
Given the client is authenticated
When it requests GET /picnic/api/categories
Then a 200 response is returned
And the body contains one entry per CategoryKey
And every entry has a non-empty "key" and a non-empty German "label"
```

**Notes:** Asserts against `list(CategoryKey)` rather than a hard-coded count,
so adding a category does not require editing this test.

---

### TC-024-10 — `PUT /api/products/{id}/category` persists a manual assignment

**Maps to:** AC-024-03
**Type:** integration (FastAPI TestClient)
**File:** `backend/tests/test_api.py`

```gherkin
Given an uncategorised product exists
When the client sends PUT /picnic/api/products/{id}/category
  with body {"category_key": "sweets"}
Then a 200 response is returned
And the response body has category_key "sweets"
And the stored product has category_is_manual True
```

---

### TC-024-11 — Unknown product returns 404

**Maps to:** AC-024-03
**Type:** integration (FastAPI TestClient)
**File:** `backend/tests/test_api.py`

```gherkin
Given no product with id 9999 exists
When the client sends PUT /picnic/api/products/9999/category
  with body {"category_key": "sweets"}
Then a 404 response is returned
```

---

### TC-024-12 — Unknown category key is rejected

**Maps to:** AC-024-10
**Type:** integration (FastAPI TestClient)
**File:** `backend/tests/test_api.py`

```gherkin
Given a product exists with category_key None
When the client sends PUT /picnic/api/products/{id}/category
  with body {"category_key": "nonsense"}
Then a 422 response is returned
And the product's category_key is still None

When the client requests GET /picnic/api/stats/spending?category=nonsense
Then a 422 response is returned
```

**Notes:** Both halves come from typing the field and the query parameter as
`CategoryKey` (ARCH-024) — the test guards that the typing is actually applied,
not that hand-written validation exists.

---

### TC-024-13 — Spending is reported per category, highest first

**Maps to:** AC-024-07
**Type:** unit (in-memory SQLite)
**File:** `backend/tests/test_stats_service.py`

```gherkin
Given receipts exist with items in "beverages" (10,00 €) and "dairy" (25,00 €)
When stats_service.get_spending_by_category(db) is called
Then two buckets are returned
And the first bucket is ("dairy", 2500)
And the second bucket is ("beverages", 1000)
```

---

### TC-024-14 — Uncategorised items get their own bucket

**Maps to:** AC-024-07
**Type:** unit (in-memory SQLite)
**File:** `backend/tests/test_stats_service.py`

```gherkin
Given receipts exist with items of a product whose category_key is None
When stats_service.get_spending_by_category(db) is called
Then one bucket has category_key None
And its total_cents is the sum of those items' line totals
```

---

### TC-024-15 — The buckets sum to the overall spend

**Maps to:** AC-024-07
**Type:** unit (in-memory SQLite)
**File:** `backend/tests/test_stats_service.py`

```gherkin
Given receipts exist across several categories, including uncategorised items
When stats_service.get_spending_by_category(db) is called
Then the sum of all bucket totals equals the sum of all buckets from
  stats_service.get_spending_over_time(db, "month")
```

**Notes:** The cross-check that matters: it catches a join that silently drops
or duplicates line items, which a per-bucket assertion would not.

---

### TC-024-16 — The breakdown respects the requested period

**Maps to:** AC-024-08
**Type:** unit (in-memory SQLite)
**File:** `backend/tests/test_stats_service.py`

```gherkin
Given a receipt with an effective date in 2026-05 and one in 2026-06
When get_spending_by_category(db, from_date=2026-06-01, to_date=2026-06-30) is called
Then only the June receipt's items are counted
```

**Notes:** Uses `delivery_date` to set the effective date, matching REQ-018
semantics — a receipt whose `received_date` and `delivery_date` fall in
different months makes the test meaningful.

---

### TC-024-17 — `get_spending_over_time` can be filtered by category

**Maps to:** AC-024-09
**Type:** unit (in-memory SQLite)
**File:** `backend/tests/test_stats_service.py`

```gherkin
Given a month contains items in "beverages" (10,00 €) and "dairy" (25,00 €)
When get_spending_over_time(db, "month", category=CategoryKey.BEVERAGES) is called
Then the month's bucket total is 1000
```

---

### TC-024-18 — `get_top_items` can be filtered by category

**Maps to:** AC-024-09
**Type:** unit (in-memory SQLite)
**File:** `backend/tests/test_stats_service.py`

```gherkin
Given products exist in several categories
When get_top_items(db, limit=10, category=CategoryKey.BEVERAGES) is called
Then only products of the "beverages" category are returned
```

---

### TC-024-19 — The statistics page shows the category breakdown

**Maps to:** AC-024-11
**Type:** integration (Vitest + React Testing Library)
**File:** `frontend/tests/Categories.test.tsx`

```gherkin
Given the API returns category spending buckets
When the "Statistiken" page is rendered
Then a "Ausgaben nach Kategorie" heading is shown
And each returned category's German label is shown

Given the API returns no buckets
When the page is rendered
Then the empty state is shown
```

**Notes:** Follows `Charts.test.tsx`: fetch is mocked at the module boundary,
the chart itself is not asserted pixel-wise — labels and empty state are the
observable behaviour.

---

### TC-024-20 — The article list is searchable and the category editable

**Maps to:** AC-024-12
**Type:** integration (Vitest + React Testing Library)
**File:** `frontend/tests/Categories.test.tsx`

```gherkin
Given the API returns three products with different categories
When the "Artikel" page is rendered
Then all three products are listed with their category

When the user types a product name fragment into the search field
Then only matching products remain listed

When the user selects a different category for a product
Then PUT /api/products/{id}/category is sent with the chosen key
And the row shows the new category without a page reload
```

---
