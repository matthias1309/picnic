# ARCH-022 — Consistent Visual Design and Layout

**Status:** approved
**Created:** 2026-08-26
**Traces:** REQ-022
**Verified by:** TEST-022

## Summary

Introduces a small design system — theme tokens in `tailwind.config.js` plus
four presentational primitives under `src/components/ui/` — and re-expresses
every existing screen in terms of it. No new dependency, no data-flow change,
no wording change.

The primitives are deliberately few. The goal is to delete duplication that
already exists (nine ad-hoc button declarations, two identical toggle groups,
two hardcoded chart colours), not to build a component library.

## Design

### No UI library (decision)

shadcn/ui, Radix and Headless UI were considered. CLAUDE.md requires
discussing dependencies first, and the user chose Tailwind-level polish over
adopting a library. The concrete case against: the app needs four primitives
(surface, button, toggle group, section header), all of which are pure markup
with no behavior worth importing — the one interactive control that *does*
have behavior, the combobox, already exists from REQ-021. A library would add
runtime weight and a second styling idiom for markup we can write in 120
lines.

### Theme tokens (`tailwind.config.js`)

`theme.extend` gains a named palette so no component carries a hex value
(AC-022-02):

```javascript
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef6ff",
          100: "#d9ebff",
          500: "#2f6fdb",
          600: "#2559b4",
          700: "#1d478f",
        },
        surface: { DEFAULT: "#ffffff", muted: "#f6f7f9", border: "#e5e7eb" },
        positive: { 50: "#ecfdf3", 600: "#0f9d58", 700: "#0b7a44" },
        negative: { 50: "#fef2f2", 600: "#dc2626", 700: "#b91c1c" },
      },
      boxShadow: {
        card: "0 1px 2px rgba(16, 24, 40, 0.05), 0 1px 3px rgba(16, 24, 40, 0.06)",
      },
      borderRadius: { card: "0.75rem" },
    },
  },
};
```

`brand` is a muted blue rather than Picnic's own red: the charts and the
"positive/negative" budget states already claim green and red, and a red brand
accent would collide with the over-budget signal — the one colour in this app
that must mean exactly one thing.

Charts read tokens through a small exported constant rather than Tailwind
classes, because Recharts takes colours as props, not `className`:

`src/lib/chart-theme.ts`
```typescript
/** Recharts takes colors as props, so the token values are mirrored here. */
export const CHART_COLORS = {
  series: "#2f6fdb",   // brand.500
  grid: "#e5e7eb",     // surface.border
  axis: "#6b7280",
} as const;
```

This is the one place a hex is repeated, and it is deliberate and commented —
the alternative (reading CSS custom properties at runtime) buys nothing for a
single fixed theme. AC-022-03 is satisfied by no hex appearing in the *chart
components*.

### Primitives (`src/components/ui/`)

**`Card.tsx`** — the shared surface (AC-022-01).

```tsx
interface CardProps {
  children: ReactNode;
  className?: string;
  testId?: string;
}
```
Renders `rounded-card border border-surface-border bg-surface p-5 shadow-card`.
`className` is appended so the budget cards can tint themselves without
forking the component.

**`Button.tsx`** — one declaration, named variants (AC-022-04).

```tsx
type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
```
Wraps a native `<button>`, forwarding every native prop, so `type`,
`disabled`, `onClick` and `aria-*` keep working at all nine existing call
sites. Every variant carries
`focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500`
(AC-022-10), which none of the current inline buttons have.

**`ToggleGroup.tsx`** — replaces the duplicated toggle markup (AC-022-05).

```tsx
interface ToggleGroupProps<T extends string> {
  label: string;
  options: readonly { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
}
```
Generic over the value type, so `PriceHistory` keeps `PriceHistoryRange` and
`PurchaseStats` keeps `SpendingGranularity` — no widening to `string`. It
renders the same `role="group"` + `aria-pressed` structure both components use
today, which is what lets the existing TC-020-06 assertions keep passing
untouched.

**`SectionHeader.tsx`** — heading plus optional right-aligned controls
(AC-022-07). Every section currently hand-rolls a `flex items-center
justify-between` wrapper around an `<h2>`; this collapses those.

### Applying it

- **`App.tsx`** — nav becomes a sticky header with the product name and a
  horizontally scrollable link row on narrow screens (AC-022-08); links get
  hover and focus states; `main` gains `max-w-6xl` and responsive padding.
- **`Dashboard.tsx`** — cards move into `Card`; grid becomes
  `sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5` so five metrics reflow
  instead of squeezing (AC-022-08); the value gets `text-2xl font-semibold
  tabular-nums`, the label `text-sm text-gray-500` (AC-022-07).
- **`BudgetStatusCard.tsx`** — keeps its red/green tinting but through
  `positive`/`negative` tokens on a `Card`; gains a `compact` prop that
  renders a single row (month, spent/budget, bar) for history use.
- **`BudgetHistory.tsx`** — wraps the twelve months in one `Card` under a
  "Frühere Monate" heading using `compact` cards (AC-022-09), so the current
  month's full-size widget dominates.
- **`PurchaseStats.tsx` / `PriceHistory.tsx`** — each section becomes a
  `Card` with a `SectionHeader`; toggles become `ToggleGroup`; chart colours
  come from `CHART_COLORS`; the top-items list gains rank numbers and
  right-aligned `tabular-nums` figures (AC-022-06).
- **`ReceiptList.tsx` / `ReceiptDetail.tsx`** — rows move from
  `justify-between` to an explicit grid (`grid-cols-[1fr_auto_auto]` and
  `grid-cols-[1fr_auto_auto_auto]`) so columns align across rows, with
  numerics `text-right tabular-nums` (AC-022-06).
- **`ProductCombobox.tsx`** — panel restyled onto the token set; the
  highlighted option uses `brand-50`.
- **`EmptyState` / `ErrorMessage` / `LoadingSpinner`** — token colours, and
  `ErrorMessage`'s retry button becomes a `Button variant="danger"`.
- **`Login.tsx`** — centred `Card`, branded submit button.

### What must not change

The restyle touches `className` and wrapping markup only. Specifically
preserved, because the existing suite asserts on them: every German string
from REQ-020, every `data-testid`, every `role`, `aria-label`, `aria-pressed`
and `aria-expanded`, and the `budget-widget` card's red/green class signal
(`Budget.test.tsx` asserts `widget.className` does *not* contain "red" when
under budget — so the negative tint must keep the substring "red" in its class
name, which `bg-negative-50` does not provide).

That last point is a real trap: `BudgetStatusCard` currently switches on
`bg-red-50` / `bg-green-50`, and `Budget.test.tsx:50` asserts on the literal
substring `"red"`. Renaming to `negative` would make that assertion silently
vacuous — it would pass for the wrong reason. TEST-022 therefore replaces that
class-substring assertion with a semantic one before the rename.

## Out of Scope

- Dark mode, new dependencies, wording changes, new data (REQ-022 Notes).
