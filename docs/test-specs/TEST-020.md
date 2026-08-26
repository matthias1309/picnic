# TEST-020 — German User Interface

**Status:** approved
**Created:** 2026-08-26
**Traces:** ARCH-020
**Verifies:** REQ-020 (AC-020-01 … AC-020-09)

---

## Strategy

REQ-020 replaces rendered text without moving markup, so the test work is
mostly *re-pointing existing assertions* at the German strings rather than
adding new test cases. That is deliberate: each existing test already proves a
behavior (pagination advances, budget saves, receipt deletes), and having it
match on the German label proves the translation and the behavior at the same
time. Only the genuinely new logic — `formatMonth()` — and the states no test
currently asserts on get new cases.

Per the TDD rule, every assertion below is changed to expect German **before**
the components are touched; the suite must be red first.

---

## Test Cases

### TC-020-01 — `formatMonth` renders an API month key as a German month

**Maps to:** AC-020-06
**Type:** unit (frontend)
**File:** `frontend/tests/format.test.ts`

```gherkin
Given the API month key "2026-08"
When formatMonth is called
Then it returns "August 2026"

Given the API month key "2026-01"
Then it returns "Januar 2026"

Given the API month key "2025-12"
Then it returns "Dezember 2025"
```

**Notes:** covers the year boundary and a month whose German and English
names differ, so the assertion cannot pass by accident on an untranslated
locale.

---

### TC-020-02 — Navigation and logout are German

**Maps to:** AC-020-01
**Type:** unit (frontend)
**File:** `frontend/tests/Auth.test.tsx`

```gherkin
Given the user is logged in and the app shell is rendered
When the header is inspected
Then links named "Übersicht", "Statistiken" and "Kassenbons" are present
And a button named "Abmelden" is present
And no element named "Home", "Stats", "Receipts" or "Logout" exists
```

**Notes:** the existing logout test at `Auth.test.tsx:94` re-points from
`/logout/i` to `/abmelden/i` and keeps asserting that the login screen
returns — proving AC-020-09 for the logout flow.

---

### TC-020-03 — Login screen is German, including the failure message

**Maps to:** AC-020-02
**Type:** unit (frontend)
**File:** `frontend/tests/Auth.test.tsx`

```gherkin
Given the user is not logged in
When the login screen renders
Then a textbox labelled "Benutzername" and a field labelled "Passwort" exist
And the submit button reads "Anmelden"
When credentials are submitted and the API rejects them
Then "Benutzername oder Passwort ist falsch." is displayed
```

---

### TC-020-04 — Dashboard cards are German

**Maps to:** AC-020-03
**Type:** unit (frontend)
**File:** `frontend/tests/Dashboard.test.tsx`

```gherkin
Given the summary fixture from TC-005-01
When the dashboard renders
Then the labels "Gesamtausgaben", "Kassenbons", "Verschiedene Artikel",
  "Durchschnittlicher Einkauf" and "Ausgaben diesen Monat" are displayed
And the existing value assertions (1.234,56 €, 42, 17, 29,40 €, 55,00 €)
  still hold
```

---

### TC-020-05 — Dashboard error state and retry are German

**Maps to:** AC-020-07
**Type:** unit (frontend)
**File:** `frontend/tests/Dashboard.test.tsx`

```gherkin
Given the summary request fails
When the error state renders
Then it reads "Zusammenfassung konnte nicht geladen werden."
And its button is named "Erneut versuchen"
When that button is clicked and the retry succeeds
Then the summary values render (existing retry behavior unchanged)
```

**Notes:** re-points the existing `name: /retry/i` lookup at
`Dashboard.test.tsx:72`, so the retry *behavior* assertion doubles as the
AC-020-09 regression check for this path.

---

### TC-020-06 — Statistics headings, period and range controls are German

**Maps to:** AC-020-04
**Type:** unit (frontend)
**File:** `frontend/tests/Charts.test.tsx`

```gherkin
Given the spending and top-items fixtures
When the statistics view renders
Then the headings "Ausgaben im Zeitverlauf" and "Meistgekaufte Artikel" are
  displayed
And buttons named "Woche" and "Monat" are present
When "Woche" is clicked
Then it is aria-pressed and /stats/spending is requested with
  granularity=week (existing behavior unchanged)

Given the price-history view with a selected product
Then the heading reads "Preisverlauf"
And the range group is labelled "Zeitraum" with buttons "3 Mon.", "6 Mon.",
  "12 Mon." and "Gesamt"
When "3 Mon." is clicked
Then it is aria-pressed and a from_date is sent (existing behavior unchanged)
And the summary line shows "Min.", "Max." and "Ø" with 0,99 / 1,09 / 1,04
```

**Notes:** the range buttons change label but not stored value — the
`from_date` assertion proves `rangeToFromDate()` still receives `"3m"`.

---

### TC-020-07 — Price-history empty and error states are German

**Maps to:** AC-020-04, AC-020-07
**Type:** unit (frontend)
**File:** `frontend/tests/Charts.test.tsx`

```gherkin
Given no product is selected
Then "Wähle einen Artikel, um seinen Preisverlauf zu sehen." is displayed

Given a product is selected whose trend has no points
Then "Für diesen Artikel liegt kein Preisverlauf vor." is displayed
```

---

### TC-020-08 — Receipt list text and pager are German

**Maps to:** AC-020-05
**Type:** unit (frontend)
**File:** `frontend/tests/Receipts.test.tsx`

```gherkin
Given the three-receipt fixture
When the list renders
Then an entry shows its item count as "12 Artikel"
And the pager reads "1–3 von 3"
And buttons named "Zurück" and "Weiter" are present
And the existing date assertions (10.6.2026, 3.6.2026, 27.5.2026) still hold
```

**Notes:** the pager separator becomes an en dash ("1–3"), so the assertion
must use the en dash literal — a hyphen would be a false negative.

---

### TC-020-09 — Receipt detail heading, delete control and total are German

**Maps to:** AC-020-05
**Type:** unit (frontend)
**File:** `frontend/tests/Receipts.test.tsx`

```gherkin
Given the receipt-detail fixture with effective_date 2026-04-15
When the detail renders
Then the heading reads "Kassenbon vom 15.4.2026"
And a button named "Kassenbon löschen" is present
And the sum line reads "Gesamt: 3,07 €"
When that button is clicked and the confirmation is accepted
Then DELETE is issued and the app navigates back (existing behavior
  unchanged)
```

**Notes:** re-points the three `name: "Delete receipt"` lookups
(`Receipts.test.tsx:297, 326, 357`), including the cancel-confirmation case
that asserts *no* DELETE is issued.

---

### TC-020-10 — Budget card header shows a German month, not the API key

**Maps to:** AC-020-06
**Type:** unit (frontend)
**File:** `frontend/tests/Budget.test.tsx`

```gherkin
Given a budget response for month "2026-08"
When the budget widget renders
Then the card reads "Budget für August 2026"
And it does not contain the raw key "2026-08"
```

**Notes:** the negative assertion is what makes this test meaningful — it
fails if `formatMonth` is skipped and the raw key is interpolated.

---

### TC-020-11 — Budget over/under lines and edit controls are German

**Maps to:** AC-020-06
**Type:** unit (frontend)
**File:** `frontend/tests/Budget.test.tsx`, `frontend/tests/BudgetHistory.test.tsx`

```gherkin
Given spending of 350,00 € against a 300,00 € budget
Then the card reads "50,00 € über Budget"

Given spending of 120,00 € against a 300,00 € budget
Then the card reads "Verbleibend: 180,00 €"

When the user clicks "Budget bearbeiten"
Then the field is labelled "Monatsbudget (€)" with buttons "Speichern" and
  "Abbrechen"
When a negative value is saved
Then "Bitte gib ein Budget von 0 oder mehr ein." is displayed and the widget
  stays in edit mode
When a valid value is saved
Then the card shows the new amount (existing behavior unchanged)
```

**Notes:** re-points the six `name: "Edit budget"` / `"Save"` / `"Cancel"`
lookups in `Budget.test.tsx` and the two `/edit budget/i` lookups in
`BudgetHistory.test.tsx` — including `BudgetHistory.test.tsx:101`, which
asserts exactly one edit control exists across current month + history.

---

### TC-020-12 — The loading spinner is announced in German

**Maps to:** AC-020-07
**Type:** unit (frontend)
**File:** `frontend/tests/Dashboard.test.tsx`

```gherkin
Given a summary request that has not resolved
When the loading state renders
Then a status element with the accessible name "Lädt" is present
```

**Notes:** re-points `Dashboard.test.tsx:30` (`name: /loading/i`).

---

### TC-020-13 — No behavioral regression across the suite

**Maps to:** AC-020-09
**Type:** unit (frontend, existing tests)
**File:** all of `frontend/tests/`

```gherkin
Given the existing test cases TC-005-01 … TC-005-04, TC-009-*, TC-013-*,
  TC-018-04, TC-018-05
When only rendered strings have changed
Then every one of them still passes
And no data-testid, role, or API-path assertion required a change
```

**Notes:** the last clause is the real check. If translating a string forced a
`data-testid` or a route assertion to move, the change went beyond REQ-020
and the diff should be re-examined.

## Test Fixtures & Mocks

No new fixture files and no fixture *data* changes — the existing
`SUMMARY_FIXTURE`, `RECEIPTS_FIXTURE`, `BUDGET_FIXTURE`, `PRICE_TREND_FIXTURE`
etc. already carry the values these assertions check. TC-020-07's
empty-trend case adds one inline fixture variant with `points: []`.

## Notes on Coverage

Covers `frontend/index.html` and every component under `src/components/`,
`src/pages/` and `src/App.tsx`, plus the new `formatMonth()` in
`src/lib/format.ts`. No backend coverage — REQ-020 touches no backend file.
