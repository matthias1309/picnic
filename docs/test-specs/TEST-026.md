# TEST-026 — Finer Shelf-Stable Categories and Shadow-Free Keyword Rules Tests

**Status:** draft
**Created:** 2026-10-10
**Traces:** ARCH-026
**Verifies:** REQ-026 (AC-026-01, AC-026-02, AC-026-03, AC-026-04, AC-026-05,
AC-026-06, AC-026-07, AC-026-08)

---

## Test Cases

### TC-026-01 — The category list contains the new categories

**Maps to:** AC-026-01
**Type:** integration (TestClient, in-memory SQLite)
**File:** `backend/tests/test_api.py`

```gherkin
Given the client is authenticated
When it requests GET /picnic/api/categories
Then the body contains the entries
  grains "Nudeln, Reis & Getreide", breakfast "Frühstück & Aufstriche",
  baking "Backzutaten", condiments "Gewürze, Öle & Saucen",
  canned "Konserven", snacks "Snacks & Nüsse"
And the entry with key "pantry" has the label "Sonstige Trockenware"
```

**Notes:** TC-024-09 keeps checking "one entry per `CategoryKey`"; this case
pins the concrete new keys and labels.

---

### TC-026-02 — New products are categorised into the finer categories

**Maps to:** AC-026-02
**Type:** unit (in-memory SQLite), parametrized
**File:** `backend/tests/test_categories.py`

```gherkin
Scenario Outline:
Given no product named "<name>" exists
When receipt_service._get_or_create_product(db, "<name>") is called
Then the created product has category_key "<category>"
And category_is_manual is False

Examples: the 18 rows of AC-026-02
```

**Notes:** Goes through the product-creation path (not just `categorize()`)
so the "rule-based, not manual" half of the AC is covered for every row.

---

### TC-026-03 — Short keywords no longer misclassify unrelated products

**Maps to:** AC-026-03
**Type:** unit, parametrized
**File:** `backend/tests/test_categories.py`

```gherkin
Scenario Outline:
When category_service.categorize("<name>") is called
Then it returns "<category>"

Examples: the 10 rows of AC-026-03
  (Ölsardinen, Preiselbeeren, Milchreis, Kaffeebohnen, Kichererbsen,
   Apfelessig, Rinderbrühe, Nektarinen, Wassereis, Zahnpasta)
```

**Notes:** Covers the multi-word collisions that the generic shadowing test
(TC-026-11) cannot see. **TC-024-04 must be updated in the same change:** its
expectations "Kokosmilch" → `pantry`, "Basmati Reis" → `pantry`,
"Speiseöl" → `pantry` and "Erdbeermarmelade" → `pantry` become `canned`,
`grains`, `condiments` and `breakfast`.

---

### TC-026-04 — Manual assignments survive the split

**Maps to:** AC-026-04
**Type:** unit (in-memory SQLite)
**File:** `backend/tests/test_categories.py`

```gherkin
Given the product "Bio Dinkelgrieß" was manually assigned to "pantry"
When category_service.apply_rules(db) runs
Then the product still has category_key "pantry"
And category_is_manual is still True
And CATEGORY_LABELS[CategoryKey.PANTRY] is "Sonstige Trockenware"
```

**Notes:** "Bio Dinkelgrieß" matches the new `grains` rule (`grieß`), so the
test proves the manual flag — not a missing rule — keeps it in `pantry`.

---

### TC-026-05 — The backfill re-categorises existing rule-based products

**Maps to:** AC-026-05
**Type:** unit (in-memory SQLite)
**File:** `backend/tests/test_categories.py`

```gherkin
Given rule-based products stored with their pre-REQ-026 categories:
  | name              | category_key |
  | Barilla Spaghetti | pantry       |
  | Paprika Chips     | sweets       |
  | Passierte Tomaten | vegetables   |
When category_service.apply_rules(db) runs
Then it returns 3
And "Barilla Spaghetti" has category_key "grains"
And "Paprika Chips" has category_key "snacks"
And "Passierte Tomaten" has category_key "canned"
And every product still has category_is_manual False
```

**Notes:** Products are inserted with `category_key` set directly and
`category_is_manual=False`, simulating data written by the REQ-024 rules.

---

### TC-026-06 — The re-categorising backfill is idempotent

**Maps to:** AC-026-05
**Type:** unit (in-memory SQLite)
**File:** `backend/tests/test_categories.py`

```gherkin
Given the products from TC-026-05
And category_service.apply_rules(db) has already run once
When it runs a second time
Then it returns 0
```

---

### TC-026-07 — Spending is reported separately for new categories

**Maps to:** AC-026-06
**Type:** unit (in-memory SQLite)
**File:** `backend/tests/test_stats_service.py`

```gherkin
Given a receipt with items of a "grains" product (3,00 €) and a "snacks" product (2,00 €)
When stats_service.get_spending_by_category(db) is called
Then the buckets are [("grains", 300), ("snacks", 200)]
```

---

### TC-026-08 — The spending filter accepts a new category

**Maps to:** AC-026-06
**Type:** integration (TestClient, in-memory SQLite)
**File:** `backend/tests/test_api.py`

```gherkin
Given a receipt with items of a "snacks" product (2,00 €) and a "grains" product (3,00 €)
When the client requests GET /picnic/api/stats/spending?granularity=month&category=snacks
Then a 200 response is returned
And the only bucket's total_cents is 200
```

**Notes:** Proves `CategoryKey` validation on the query parameter accepts the
new values (before the change this returns 422).

---

### TC-026-09 — The article dropdown offers the new categories

**Maps to:** AC-026-06
**Type:** unit (Vitest + RTL)
**File:** `frontend/tests/Categories.test.tsx`

```gherkin
Given the API returns the categories including "snacks" (Snacks & Nüsse)
And a product "Paprika Chips" with category_key "snacks"
When the "Artikel" page is rendered
Then the product's dropdown has the value "snacks"
And it offers the option "Snacks & Nüsse"
```

**Notes:** At runtime the dropdown renders whatever the API returns; the part
that fails before the change is the `CategoryKey` union in
`frontend/src/types/index.ts` (`npm run lint` / `tsc` rejects `"snacks"`).

---

### TC-026-10 — Every category has its own chart colour

**Maps to:** AC-026-07
**Type:** unit (Vitest)
**File:** `frontend/tests/ChartTheme.test.ts`

```gherkin
Given CATEGORY_COLORS from chart-theme.ts
Then it has an entry for grains, breakfast, baking, condiments, canned and snacks
And no two entries share a colour value (case-insensitive)
```

**Notes:** Completeness for all keys is already enforced by the
`Record<CategoryKey | "uncategorized", string>` type; this test adds the
distinctness check a type cannot express. Contrast in light/dark mode is
checked with the dataviz validator during implementation, not here.

---

### TC-026-11 — No keyword rule is shadowed by an earlier rule

**Maps to:** AC-026-08
**Type:** unit
**File:** `backend/tests/test_categories.py`

```gherkin
Given CATEGORY_RULES
When categorize(keyword) is called for every (keyword, category) rule
Then every call returns that rule's own category
```

**Notes:** The failure message lists every shadowed keyword with the category
it actually resolved to. Expected to fail today for `nektarine`, `wassereis`,
`zahnpasta`, `passierte tomaten`.

---

### TC-026-12 — No keyword appears twice

**Maps to:** AC-026-08
**Type:** unit
**File:** `backend/tests/test_categories.py`

```gherkin
Given CATEGORY_RULES
Then every keyword occurs exactly once
```

**Notes:** Expected to fail today for `saft`, `joghurt`, `quark`, `skyr`,
`marmelade`.

---

## Coverage Matrix

| AC | Test Cases |
|---|---|
| AC-026-01 | TC-026-01 |
| AC-026-02 | TC-026-02 |
| AC-026-03 | TC-026-03 |
| AC-026-04 | TC-026-04 |
| AC-026-05 | TC-026-05, TC-026-06 |
| AC-026-06 | TC-026-07, TC-026-08, TC-026-09 |
| AC-026-07 | TC-026-10 |
| AC-026-08 | TC-026-11, TC-026-12 |
