# TEST-022 — Consistent Visual Design and Layout

**Status:** approved
**Created:** 2026-08-26
**Traces:** ARCH-022
**Verifies:** REQ-022 (AC-022-01 … AC-022-11)

---

## Strategy

Most of REQ-022 is visual, and `testing-practices.md` warns against tests that
pin implementation details — asserting "this div has class `p-5`" is exactly
that: it breaks on every restyle and proves nothing about behavior. So the
suite is split three ways:

1. **Behavior of the new primitives** — variants, focus, toggle semantics.
   Tested through rendered output and `userEvent`, not class strings.
2. **Semantic signals that replace visual ones** — the budget over/within
   state is currently asserted via a colour class substring, which the token
   rename would make vacuous. It gets a real `data-state` attribute first.
3. **Regression** — the existing 58 tests must pass untouched, which is the
   bulk of the evidence for AC-022-11.

Purely aesthetic ACs (AC-022-01 surfaces, AC-022-07 typography) are verified
by review against ARCH-022 and by the browser check recorded in CR-022, not by
brittle class assertions. This is stated so the gap is deliberate and visible
rather than an oversight.

---

## Test Cases

### TC-022-01 — Button renders its variants and forwards native props

**Maps to:** AC-022-04
**Type:** unit (frontend)
**File:** `frontend/tests/ui.test.tsx`

```gherkin
Given a Button with variant "primary" and a label
When it renders
Then it is a button element exposing that accessible name
And it carries a visible focus-ring class for keyboard users

Given a Button with type="submit" and disabled
When it renders
Then both native attributes are applied (props are forwarded, not swallowed)

Given a Button with an onClick handler
When the user clicks it
Then the handler is called once
```

**Notes:** the forwarding case is the one that matters — nine existing call
sites pass `type`, `disabled` and `onClick`, and a wrapper that drops them
would break receipt deletion and budget saving in ways the visual review
would not catch.

---

### TC-022-02 — ToggleGroup exposes the group and pressed state

**Maps to:** AC-022-05
**Type:** unit (frontend)
**File:** `frontend/tests/ui.test.tsx`

```gherkin
Given a ToggleGroup labelled "Zeitraum" with options "Woche" and "Monat",
  value "monat"
When it renders
Then a group labelled "Zeitraum" contains both options
And "Monat" is aria-pressed and "Woche" is not
When the user clicks "Woche"
Then onChange is called with that option's value
```

**Notes:** pins the exact ARIA contract the two call sites already rely on, so
swapping their hand-rolled markup for this component cannot silently change
what TC-020-06 and TC-005-03 assert.

---

### TC-022-03 — Card renders its children and forwards a test id

**Maps to:** AC-022-01
**Type:** unit (frontend)
**File:** `frontend/tests/ui.test.tsx`

```gherkin
Given a Card with a testId and children
When it renders
Then the children are visible inside the element carrying that test id
And an extra className passed by the caller is applied alongside the base
  surface classes (so budget tinting composes rather than forks)
```

---

### TC-022-04 — Budget state is exposed semantically, not only by colour

**Maps to:** AC-022-11
**Type:** unit (frontend)
**File:** `frontend/tests/Budget.test.tsx`, `frontend/tests/BudgetHistory.test.tsx`

```gherkin
Given spending of 120,00 € against a 300,00 € budget
When the budget widget renders
Then its data-state is "within"

Given spending of 350,00 € against a 300,00 € budget
Then its data-state is "over"

Given a historical month over its budget
Then that month's card data-state is "over"

Given a historical month within its budget
Then that month's card data-state is "within"
```

**Notes:** **these must be written and passing before the colour tokens are
renamed.** Three existing assertions test the budget state by matching the
literal substring `"red"` against a `className`:

| File | Assertion |
|---|---|
| `Budget.test.tsx:50` | `expect(widget.className).not.toContain("red")` |
| `Budget.test.tsx:82` | `expect(widget.className).toContain("red")` |
| `BudgetHistory.test.tsx:59` | `expect(cards[0].className).toContain("red")` |
| `BudgetHistory.test.tsx:78` | `expect(cards[0].className).not.toContain("red")` |

Once the tint becomes `bg-negative-50`, none of these can ever see "red" —
the two negative assertions pass vacuously and the two positive ones fail. A
silently vacuous test is worse than a deleted one, so all four are replaced by
`data-state` assertions, which cannot rot when the palette changes again.

This is the exception referenced in TC-022-07, and it is larger than a single
assertion: the class-substring idiom appears four times, not once.

---

### TC-022-05 — Budget history renders compact cards under a heading

**Maps to:** AC-022-09
**Type:** unit (frontend)
**File:** `frontend/tests/BudgetHistory.test.tsx`

```gherkin
Given budget responses for the last twelve months
When the history renders
Then a heading "Frühere Monate" is present
And twelve budget-history cards are rendered
And none of them offers a "Budget bearbeiten" control
```

**Notes:** extends the existing TC-017-02 rather than replacing it — the
twelve-card count and the no-edit-control rule are unchanged requirements from
REQ-017 and must survive the visual regrouping.

---

### TC-022-06 — Chart components carry no hardcoded colour

**Maps to:** AC-022-03
**Type:** unit (static assertion)
**File:** `frontend/tests/ui.test.tsx`

```gherkin
Given the source of PriceHistory.tsx and PurchaseStats.tsx
When they are read
Then neither contains a hex colour literal
```

**Notes:** a source-level assertion is unusual and justified narrowly here:
Recharts colours are props, so they render into SVG attributes that jsdom
reports inconsistently, and the actual requirement ("no hardcoded hex in the
chart components") is a property of the source, not of the DOM. Kept to the
two chart files so it cannot become a project-wide style police.

---

### TC-022-07 — No regression across the existing suite

**Maps to:** AC-022-11
**Type:** unit (frontend, existing tests)
**File:** all of `frontend/tests/`

```gherkin
Given all 58 tests passing after REQ-021
When the restyle is applied
Then all of them still pass
And the only edits to existing tests are the four class-substring assertions
  superseded by TC-022-04
```

**Notes:** the second clause is the real gate. If restyling forces any other
existing assertion to change, a German string, a test id, a role or a data
flow moved — which is outside REQ-022 — and the diff must be re-examined
rather than the test relaxed.

This gate did its job during implementation. The first draft of the compact
budget-history card dropped the "Verbleibend" / "über Budget" line, and
TC-017-03 and TC-017-04 failed on the *text*, not the class. That was a real
content regression — REQ-017 requires the history to state each month's
outcome — and the card was fixed to keep the line rather than the test
relaxed. Likewise, a first pass restyled the price summary into a `<dl>`,
splitting "Min. 0,99 €" across `<dt>`/`<dd>`; TC-020-06 caught it and the
markup was reverted to single text nodes.

---

### TC-022-08 — Responsive layout check

**Maps to:** AC-022-08
**Type:** manual (browser, recorded in CR-022)
**File:** —

```gherkin
Given the app at a 375px-wide viewport
When each page is opened
Then no page scrolls horizontally
And the navigation is reachable
And the dashboard metric cards reflow to fewer columns
```

**Notes:** jsdom has no layout engine — it reports every width as 0 — so a
viewport assertion in vitest would be theatre. This is verified in a real
browser and the result recorded in CR-022 with a screenshot reference.

## Test Fixtures & Mocks

`ui.test.tsx` renders the primitives directly with inline props and `vi.fn()`
handlers — no providers, no network. TC-022-06 reads the two chart files from
disk with `node:fs`.

All other test cases reuse the existing fixtures unchanged.

## Notes on Coverage

Covers the new `src/components/ui/*` primitives and the semantic budget state.
The restyle of the remaining components is covered *indirectly* but strongly:
58 existing tests exercise them through roles, test ids and German strings, so
any structural damage from the restyle surfaces there. No backend coverage —
REQ-022 touches no backend file.
