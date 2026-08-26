# ARCH-020 — German User Interface

**Status:** approved
**Created:** 2026-08-26
**Traces:** REQ-020
**Verified by:** TEST-020

## Summary

A text-only change across the frontend: every rendered English string is
replaced by its German equivalent in place. No component structure, props,
routing, data flow, or API contract changes. One new pure helper —
`formatMonth()` in `lib/format.ts` — converts the API's `"2026-08"` month key
into `"August 2026"` (AC-020-06), because that conversion is needed in two
components and is the only piece of the translation with actual logic.

## Design

### No i18n framework (decision)

A translation library (`react-i18next`, `formatjs`, …) or even a hand-rolled
`t("nav.home")` lookup table was considered and rejected:

- The app is single-user and German-only. There is no second locale, no
  language switcher in scope, and no plan for one (REQ-020 Out of Scope).
- A key-lookup indirection makes every component harder to read (`t("nav.home")`
  instead of `Übersicht`) and moves the text away from where it renders — cost
  with no benefit while there is exactly one locale (YAGNI, KISS).
- It would add a dependency, which CLAUDE.md requires discussing first.

German strings are therefore written inline, exactly where the English ones
are today. If a second locale is ever required, extracting inline literals is
mechanical and can be done then, with real requirements to design against.

Note the asymmetry this creates and why it is correct: **rendered text is
German, everything else stays English.** Identifiers, comments, test names,
`data-testid` values, commit messages and these documents remain English per
CLAUDE.md ("All repository content is written in English"). REQ-020 changes
what the app *says*, not what the repository *is written in*.

### `formatMonth()` — the one piece with logic

`frontend/src/lib/format.ts`:

```typescript
/** Formats an API month key ("2026-08") as a German month name ("August 2026"). */
export function formatMonth(month: string): string {
  const [year, monthNumber] = month.split("-").map(Number);
  return new Date(year, monthNumber - 1, 1).toLocaleDateString("de-DE", {
    month: "long",
    year: "numeric",
  });
}
```

Built on `Intl` via `toLocaleDateString`, consistent with the existing
`formatCents`/`toLocaleDateString("de-DE")` usage — no hardcoded month-name
array to keep in sync. Used by `BudgetStatusCard` and by `BudgetWidget`'s
editing branch, which renders its own copy of the same header.

`BudgetHistory`'s error path (`Budget für {month} konnte nicht geladen
werden.`) reuses it too, so a failed month reads the same way as a loaded one.

### String map

Applied literally, file by file. No other edits in these files.

**`frontend/index.html`** — `lang="en"` → `lang="de"`, title → `Picnic
Ausgaben-Tracker` (AC-020-08).

**`src/App.tsx`** — `NAV_LINKS` labels → `Übersicht` / `Statistiken` /
`Kassenbons`; logout button → `Abmelden`.

**`src/pages/Login.tsx`** — `Username` → `Benutzername`, `Password` →
`Passwort`, `Log in` → `Anmelden`, `Logging in…` → `Wird angemeldet…`,
`Invalid username or password.` → `Benutzername oder Passwort ist falsch.`
The `<h1>` stays `Picnic Ausgaben-Tracker` (the product name, matching the
document title).

**`src/components/Dashboard.tsx`** — card labels → `Gesamtausgaben`,
`Kassenbons`, `Verschiedene Artikel`, `Durchschnittlicher Einkauf`,
`Ausgaben diesen Monat`; error → `Zusammenfassung konnte nicht geladen
werden.`

**`src/components/Charts/PurchaseStats.tsx`** — `Spending over time` →
`Ausgaben im Zeitverlauf`; `Top purchased items` → `Meistgekaufte Artikel`;
period buttons → `Woche` / `Monat`; `aria-label="Aggregation period"` →
`Zeitraum`; errors → `Ausgabendaten konnten nicht geladen werden.` /
`Meistgekaufte Artikel konnten nicht geladen werden.`; empty states → `Noch
keine Ausgabendaten vorhanden.` / `Noch keine Einkäufe erfasst.`

**`src/components/Charts/PriceHistory.tsx`** — `Price history` →
`Preisverlauf`; `aria-label="Select product"` → `Artikel auswählen`;
`Select a product` → `Artikel auswählen`; `aria-label="Time range"` →
`Zeitraum`; empty → `Wähle einen Artikel, um seinen Preisverlauf zu sehen.` /
`Für diesen Artikel liegt kein Preisverlauf vor.`; error → `Preisverlauf
konnte nicht geladen werden.`; `Min:` / `Max:` / `Avg:` → `Min.` / `Max.` /
`Ø`.

The range buttons get German labels while the store values stay the API's
`3m` / `6m` / `12m` / `all` — a presentation map, so `PriceHistoryRange` and
`rangeToFromDate()` are untouched:

```tsx
const RANGE_LABELS: Record<PriceHistoryRange, string> = {
  "3m": "3 Mon.",
  "6m": "6 Mon.",
  "12m": "12 Mon.",
  all: "Gesamt",
};
```

**`src/components/Receipts/ReceiptList.tsx`** — `{n} items` → `{n} Artikel`;
`Previous`/`Next` → `Zurück`/`Weiter`; `{a}-{b} of {c}` → `{a}–{b} von {c}`
(en dash); error → `Kassenbons konnten nicht geladen werden.`; empty →
`Keine Kassenbons gefunden.`

**`src/components/Receipts/ReceiptDetail.tsx`** — heading `Receipt from` →
`Kassenbon vom`; `Delete receipt` → `Kassenbon löschen`; the
`window.confirm` text → `Diesen Kassenbon löschen? Das kann nicht rückgängig
gemacht werden.`; `Total:` → `Gesamt:`; error → `Kassenbon konnte nicht
geladen werden.` The existing `Bestellnr` heading is already German and
stays.

**`src/components/Budget/BudgetStatusCard.tsx`** — header → `Budget für
{formatMonth(data.month)}`; `Over budget by X` → `X über Budget`;
`Remaining: X` → `Verbleibend: X`.

**`src/components/Budget/BudgetWidget.tsx`** — same header via
`formatMonth`; `Edit budget` → `Budget bearbeiten`; `Monthly budget (€)` →
`Monatsbudget (€)`; `Save`/`Cancel` → `Speichern`/`Abbrechen`; validation →
`Bitte gib ein Budget von 0 oder mehr ein.`; error → `Budgetstatus konnte
nicht geladen werden.`

**`src/components/Budget/BudgetHistory.tsx`** — error → `Budget für
{formatMonth(month)} konnte nicht geladen werden.`

**`src/components/common/ErrorMessage.tsx`** — default message → `Etwas ist
schiefgelaufen.`; `Retry` → `Erneut versuchen`.

**`src/components/common/LoadingSpinner.tsx`** — `aria-label="Loading"` →
`Lädt`. This is announced to the user, so it is UI text and is translated;
`role="status"` is unchanged.

### Test impact

Roughly 30 assertions across `frontend/tests/` match on English UI text
(`getByRole("button", { name: /logout/i })`, `toHaveTextContent("Over
budget")`, `getByText(/choose a product/i)`, …). Per the TDD rule these
assertions are updated to the German strings **first**, which turns the suite
red, and the implementation then makes it green. Test *names*, `describe`
blocks and TC comments stay English — only the matched strings change.

`data-testid` values (`budget-widget`, `price-history-chart`,
`top-items-list`, …) are code identifiers, not UI text, and are unchanged —
which is what keeps the structural assertions in the suite meaningful proof
of AC-020-09 (no behavioral regression).

## Out of Scope

- The searchable product picker (REQ-021) and the visual polish (REQ-022) —
  separate requirements, separate changes. This one moves no markup.
- Backend text of any kind.
