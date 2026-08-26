# TEST-021 — Searchable Article Picker for the Price History

**Status:** approved
**Created:** 2026-08-26
**Traces:** ARCH-021
**Verifies:** REQ-021 (AC-021-01 … AC-021-09)

---

## Strategy

Split in two, matching ARCH-021's split: the matching/ranking rules are tested
directly against `searchProducts()` with no DOM (fast, exhaustive on edge
cases), and the interaction rules are tested through the rendered combobox
with `userEvent` (real keyboard and pointer events, no implementation
details). Nothing asserts on internal state such as `highlightedIndex` — only
on what the user and assistive technology can observe.

---

## Test Cases

### TC-021-01 — `searchProducts` filters by substring

**Maps to:** AC-021-01
**Type:** unit (frontend)
**File:** `frontend/tests/product-search.test.ts`

```gherkin
Given products "Bananen", "Bio-Bananen" and "Milch"
When searchProducts is called with "banan"
Then it returns "Bananen" and "Bio-Bananen"
And it does not return "Milch"
```

---

### TC-021-02 — `searchProducts` ignores case and diacritics

**Maps to:** AC-021-02
**Type:** unit (frontend)
**File:** `frontend/tests/product-search.test.ts`

```gherkin
Given a product named "Äpfel"
When searchProducts is called with "apfel"
Then "Äpfel" is returned

Given a product named "Bananen"
When searchProducts is called with "BANANEN"
Then "Bananen" is returned

Given a product named "Müsli"
When searchProducts is called with "musli"
Then "Müsli" is returned
```

**Notes:** "Müsli"/"musli" is the case a naive `toLowerCase()` alone fails —
it proves the NFD-fold is actually applied, not just case folding.

---

### TC-021-03 — `searchProducts` ranks most-bought first, then by name

**Maps to:** AC-021-03
**Type:** unit (frontend)
**File:** `frontend/tests/product-search.test.ts`

```gherkin
Given "Bio-Bananen" (purchase_count 2) and "Bananen" (purchase_count 30),
  supplied in that order
When searchProducts is called with "banan"
Then "Bananen" is first and "Bio-Bananen" second

Given two matching products with equal purchase_count, "Zucker" and "Apfel"
When searchProducts is called
Then they are ordered "Apfel" then "Zucker"
```

**Notes:** the input order in the first case is deliberately the reverse of
the expected output, so the assertion cannot pass on an unsorted pass-through.
The tie case pins the ordering as stable rather than input-dependent.

---

### TC-021-04 — `searchProducts` returns nothing for an empty query

**Maps to:** AC-021-01
**Type:** unit (frontend)
**File:** `frontend/tests/product-search.test.ts`

```gherkin
Given a non-empty product list
When searchProducts is called with "" or with "   "
Then it returns an empty array (the picker must not dump the full list)
```

---

### TC-021-05 — Typing filters the rendered suggestions

**Maps to:** AC-021-01, AC-021-03
**Type:** unit (frontend)
**File:** `frontend/tests/ProductCombobox.test.tsx`

```gherkin
Given the article picker with "Bananen", "Bio-Bananen" and "Milch"
When the user types "banan"
Then options "Bananen" and "Bio-Bananen" are shown, in that order
And no option "Milch" is shown
And each option shows its purchase count
```

---

### TC-021-06 — Selecting a suggestion reports the product and closes the list

**Maps to:** AC-021-04
**Type:** unit (frontend)
**File:** `frontend/tests/ProductCombobox.test.tsx`

```gherkin
Given suggestions are shown for "banan"
When the user clicks "Bananen"
Then onSelect is called with that product's id
And the input's value is "Bananen"
And no listbox is shown
```

---

### TC-021-07 — Arrow keys and Enter select without the mouse

**Maps to:** AC-021-05
**Type:** unit (frontend)
**File:** `frontend/tests/ProductCombobox.test.tsx`

```gherkin
Given the user has typed "banan" and two suggestions are shown
When the user presses ArrowDown
Then the first option is the active descendant
When the user presses ArrowDown again
Then the second option is the active descendant
When the user presses Enter
Then onSelect is called with the second option's product id
```

---

### TC-021-08 — Escape closes the list without changing the selection

**Maps to:** AC-021-05
**Type:** unit (frontend)
**File:** `frontend/tests/ProductCombobox.test.tsx`

```gherkin
Given the user has typed "banan" and suggestions are shown
When the user presses Escape
Then no listbox is shown
And onSelect has not been called
```

---

### TC-021-09 — The combobox exposes its ARIA contract

**Maps to:** AC-021-06
**Type:** unit (frontend)
**File:** `frontend/tests/ProductCombobox.test.tsx`

```gherkin
Given the article picker is rendered
Then an element with role "combobox" labelled "Artikel" exists
And its aria-expanded is "false"
When the user types "banan"
Then its aria-expanded is "true"
And a listbox with option children is present
```

---

### TC-021-10 — A query with no matches reports it

**Maps to:** AC-021-07
**Type:** unit (frontend)
**File:** `frontend/tests/ProductCombobox.test.tsx`

```gherkin
Given the article picker
When the user types "xyzzy"
Then "Kein Artikel gefunden." is shown
And no option is shown
And onSelect has not been called
```

---

### TC-021-11 — Clearing the input clears the selection

**Maps to:** AC-021-08
**Type:** unit (frontend)
**File:** `frontend/tests/ProductCombobox.test.tsx`

```gherkin
Given "Bananen" is selected
When the user clears the input
Then onSelect is called with null
```

---

### TC-021-12 — Price history loads through the new picker

**Maps to:** AC-021-04, AC-021-09
**Type:** unit (frontend)
**File:** `frontend/tests/Charts.test.tsx`

```gherkin
Given the price-history view and the products fixture
When the user types "banan" and selects "Bananas"
Then /stats/price-trend/1 is requested
And the chart renders with Min. 0,99 / Max. 1,09 / Ø 1,04
```

**Notes:** replaces the `selectOptions` interaction in the two existing
PriceHistory tests (`Charts.test.tsx:66, 86`) and in TC-020-07's empty-trend
test — the `<select>` those drive no longer exists. Their assertions are
otherwise unchanged, which is the AC-021-09 evidence.

---

### TC-021-13 — Range buttons and states still work through the new picker

**Maps to:** AC-021-09
**Type:** unit (frontend)
**File:** `frontend/tests/Charts.test.tsx`

```gherkin
Given an article has been selected via the combobox
When the user clicks "3 Mon."
Then it is aria-pressed and /stats/price-trend/1 is requested with a
  from_date (existing behavior unchanged)
Given no article is selected
Then "Wähle einen Artikel, um seinen Preisverlauf zu sehen." is shown
Given the selected article's trend has no points
Then "Für diesen Artikel liegt kein Preisverlauf vor." is shown
```

## Test Fixtures & Mocks

`product-search.test.ts` builds plain `ProductOut` literals inline — no API,
no mocks, no DOM.

`ProductCombobox.test.tsx` renders the component directly with a `products`
array and a `vi.fn()` `onSelect`, so the interaction tests never touch the
network. This is the dependency-injection boundary
`testing-practices.md` asks for: the combobox takes its data as a prop, so
only `Charts.test.tsx` needs `fetchJson` mocked.

`Charts.test.tsx` keeps its existing `PRODUCTS_FIXTURE`
(`{ id: 1, name: "Bananas", purchase_count: 5 }`) and `PRICE_TREND_FIXTURE`
unchanged.

## Notes on Coverage

Covers the new `src/lib/product-search.ts` and
`src/components/Charts/ProductCombobox.tsx`, plus the changed selection path
in `src/components/Charts/PriceHistory.tsx`. No backend coverage — `GET
/products` is called exactly as before.
