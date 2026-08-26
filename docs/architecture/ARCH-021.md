# ARCH-021 — Searchable Article Picker for the Price History

**Status:** approved
**Created:** 2026-08-26
**Traces:** REQ-021
**Verified by:** TEST-021

## Summary

Replaces the `<select>` in `PriceHistory.tsx` with a new reusable
`ProductCombobox` component: a text input plus a filtered, ranked listbox
following the WAI-ARIA combobox pattern. Filtering and ranking are pure
functions in `lib/product-search.ts`, unit-testable without rendering.

Nothing else changes. The selected product still lives in `useUiStore` as
`selectedProductId`, `usePriceTrend` is called exactly as before, and the
range buttons, summary line and chart are untouched.

## Design

### No combobox library (decision)

Headless UI, Downshift, `react-select` and Radix's combobox were considered
and rejected. CLAUDE.md requires discussing new dependencies, and the case is
weak here: this is one input over an in-memory array, the ARIA pattern needed
is small and fully specified, and the alternative pulls a runtime dependency
(plus, for Radix/Headless UI, a styling model) into a project that currently
has five frontend dependencies. Hand-rolling costs ~90 lines and keeps the
bundle and the styling under our control (REQ-022 restyles this component
right after).

### `lib/product-search.ts` — the searchable logic, extracted

Kept out of the component so ranking and matching can be tested directly,
without a DOM, per `testing-practices.md` ("test behavior… fast, no I/O").

```typescript
import type { ProductOut } from "../types";

/** Case- and diacritic-insensitive form for substring matching ("Äpfel" → "apfel"). */
function foldForSearch(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

/**
 * Products whose name contains `query`, most-bought first.
 *
 * Ranking is by purchase_count rather than by match position: the article a
 * user searches for is overwhelmingly one they buy often, so "Bananen" must
 * outrank "Bio-Bananen" for the query "banan" (AC-021-03). Ties fall back to
 * name order so the list is stable across renders.
 */
export function searchProducts(products: ProductOut[], query: string): ProductOut[] {
  const folded = foldForSearch(query.trim());
  if (folded === "") {
    return [];
  }
  return products
    .filter((product) => foldForSearch(product.name).includes(folded))
    .sort(
      (a, b) =>
        b.purchase_count - a.purchase_count || a.name.localeCompare(b.name, "de"),
    );
}
```

`\p{Diacritic}` with the `u` flag needs ES2018 regex property escapes —
available in every browser this app targets and in the `jsdom` test
environment; `tsconfig` already targets ES2020.

An empty query returns no suggestions rather than the full list: the whole
point of REQ-021 is not to render hundreds of rows. The list opens on typing.

### `components/Charts/ProductCombobox.tsx` — the control

Presentational and controlled — it owns only the transient query and
highlight state; the *selection* stays in `useUiStore`, so `PriceHistory`'s
data flow is unchanged.

```tsx
interface ProductComboboxProps {
  products: ProductOut[];
  selectedProductId: number | null;
  onSelect: (productId: number | null) => void;
}
```

Internal state: `query: string`, `isOpen: boolean`, `highlightedIndex: number`
(`-1` = nothing highlighted). Suggestions are `useMemo(() =>
searchProducts(products, query), [products, query])`, capped at
`MAX_SUGGESTIONS = 8` so the panel never becomes the scrolling column it
replaces.

ARIA wiring (AC-021-06), the WAI-ARIA 1.2 combobox pattern:

- input: `role="combobox"`, `aria-expanded`, `aria-controls`,
  `aria-autocomplete="list"`, `aria-activedescendant` pointing at the
  highlighted option's id, and `aria-label="Artikel"`.
- list: `role="listbox"` with `role="option"` children carrying
  `aria-selected`.

Keyboard handling (AC-021-05) on the input's `onKeyDown`:

| Key | Behavior |
|---|---|
| `ArrowDown` | open if closed; move highlight down, clamped at the last suggestion |
| `ArrowUp` | move highlight up, clamped at the first |
| `Enter` | select the highlighted suggestion (no-op if none) |
| `Escape` | close the list, leave the selection untouched |

Selecting sets the query to the product name, closes the list and calls
`onSelect(product.id)`. Clearing the input calls `onSelect(null)`
(AC-021-08), which drives `PriceHistory` back to its existing empty state.

Blur closes the list via `onBlur` with a `relatedTarget` check, so clicking an
option is not swallowed by the input losing focus first.

Each suggestion renders its name and `purchase_count` (`{count}×`
gekauft) — AC-021-03's "shows how often it was bought", using data already on
the wire and previously discarded.

An empty suggestion list with a non-empty query renders "Kein Artikel
gefunden." inside the panel (AC-021-07). Note this replaces only the
*suggestions*, never the chart: `PriceHistory` keys the chart off
`selectedProductId`, which a failed search does not touch.

### `PriceHistory.tsx` — the swap

The `<select>` block (lines 36–50) is replaced by:

```tsx
<ProductCombobox
  products={products.data ?? []}
  selectedProductId={selectedProductId}
  onSelect={setSelectedProductId}
/>
```

Everything else in the file — range buttons, `usePriceTrend`, the min/max/Ø
line, the `ResponsiveContainer` chart, all four states — is untouched, which
is what AC-021-09 asserts.

`useProducts()` is unchanged: the same single `GET /products`, cached by
TanStack Query. Filtering is client-side over that cached array, so typing
issues no requests.

## Out of Scope

- Multi-select / comparison charts, fuzzy matching, server-side search
  (REQ-021 Notes).
- Visual styling beyond what is needed to make the panel usable — REQ-022
  restyles it.
