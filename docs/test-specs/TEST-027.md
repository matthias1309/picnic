# TEST-027 — Keyword Rule Gaps Tests

**Status:** draft
**Created:** 2026-10-10
**Traces:** ARCH-027
**Verifies:** REQ-027 (AC-027-01, AC-027-02, AC-027-03, AC-027-04, AC-027-05,
AC-027-06)

---

## Test Cases

All cases are unit tests in `backend/tests/test_categories.py`, parametrized
over `category_service.categorize(name)`.

### TC-027-01 — Preserved tomato, olive and pickle products are canned goods

**Maps to:** AC-027-01
**Type:** unit, parametrized

```gherkin
Scenario Outline:
When category_service.categorize("<name>") is called
Then it returns "canned"

Examples: the 8 rows of AC-027-01
```

---

### TC-027-02 — False friends of general keywords no longer win

**Maps to:** AC-027-02
**Type:** unit, parametrized

```gherkin
Scenario Outline:
When category_service.categorize("<name>") is called
Then it returns "<category>"

Examples: the 6 rows of AC-027-02
```

---

### TC-027-03 — Previously unmatched or misfiled foods reach their category

**Maps to:** AC-027-03
**Type:** unit, parametrized

```gherkin
Scenario Outline:
When category_service.categorize("<name>") is called
Then it returns "<category>"

Examples: the 6 rows of AC-027-03
```

---

### TC-027-04 — Non-food products leave the food categories

**Maps to:** AC-027-04
**Type:** unit, parametrized

```gherkin
Scenario Outline:
When category_service.categorize("<name>") is called
Then it returns "<category>"

Examples: the 7 rows of AC-027-04
```

---

### TC-027-05 — Products the old rules handled correctly keep their category

**Maps to:** AC-027-05
**Type:** unit, parametrized

```gherkin
Scenario Outline:
When category_service.categorize("<name>") is called
Then it returns "<category>"

Examples: the 15 rows of AC-027-05
```

**Notes:** These rows guard the moved keywords (`sardine`, `thunfisch`, `tee`),
the `olivenöl`/`oliven` pair and the `gurke` split. They pass on the old rules
as well; a failure after the change means a new rule is too greedy.

---

### TC-027-06 — The rule-table invariants still hold

**Maps to:** AC-027-06
**Type:** unit (existing tests)
**File:** `backend/tests/test_categories.py`

```gherkin
Given the extended CATEGORY_RULES
Then TC-026-11 (no shadowed rule) and TC-026-12 (no duplicate keyword) pass
```

**Notes:** No new test code. The two existing tests are the check; they run
against the extended table. Listed here so the coverage matrix is complete.

---

## Coverage Matrix

| AC | Test Cases |
|---|---|
| AC-027-01 | TC-027-01 |
| AC-027-02 | TC-027-02 |
| AC-027-03 | TC-027-03 |
| AC-027-04 | TC-027-04 |
| AC-027-05 | TC-027-05 |
| AC-027-06 | TC-027-06 (= TC-026-11, TC-026-12) |
