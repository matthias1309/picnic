# TEST-025 — Schema Drift Check Before Deploy Restart

**Status:** draft
**Created:** 2026-08-27
**Traces:** ARCH-025
**Verifies:** REQ-025 (AC-025-01, AC-025-02, AC-025-03, AC-025-04, AC-025-05,
AC-025-06, AC-025-07, AC-025-08)

---

## Strategy

Split by the boundary ARCH-025 draws:

- The comparison logic (`check_schema_drift`) and the CLI it powers are pure
  Python against real SQLite engines (in-memory or `tmp_path` files) — no
  mocks, no network, exercised directly and via `subprocess` for the CLI
  entry point.
- The `deploy.sh` integration point (ordering relative to `set -e` and
  `supervisorctl restart`) is a structural/text assertion on the script
  itself, mirroring `test_deploy_spa_fallback.py` and
  `test_pipeline_wiring.py`: no SSH, no real deploy, just verifying the
  script is wired the way ARCH-025 requires.
- The CI gate (AC-025-08) is verified by extending the existing structural
  guard in `test_pipeline_wiring.py` (TEST-015) rather than duplicating it —
  that file already pins `acceptance`'s and `deploy-prod`'s `needs:` chain;
  this REQ only adds the missing half: that the `deploy-dev` SSH step itself
  cannot silently swallow a non-zero `deploy.sh` exit.

## Test Cases

### TC-025-01 — A schema matching the models reports no drift

**Maps to:** AC-025-01
**Type:** unit
**File:** `backend/tests/test_schema_check.py`

```gherkin
Given an in-memory database created from Base.metadata (matches the models)
When check_schema_drift is called against it
Then the report has no drift
And missing_tables and missing_columns are both empty
```

---

### TC-025-02 — A freshly initialized database reports no drift

**Maps to:** AC-025-02
**Type:** integration
**File:** `backend/tests/test_schema_check.py`

```gherkin
Given no database file exists at a tmp_path location
When init_db() is run against that path
Then check_schema_drift reports no drift
```

**Notes:** proves the fresh-database path deploy.sh already takes
(`init_db()` via `Base.metadata.create_all`) can never be flagged as
drifting — it's the "given" AC-025-02 requires, checked end to end through
a real file-backed engine rather than `:memory:`.

---

### TC-025-03 — A missing column is reported with the exact ALTER TABLE statement

**Maps to:** AC-025-03
**Type:** unit
**File:** `backend/tests/test_schema_check.py`

```gherkin
Given a database whose products table has every column except category_key
When check_schema_drift is called against it
Then the report has drift
And one missing column names table "products" and column "category_key"
And its alter_statement is
  "ALTER TABLE products ADD COLUMN category_key VARCHAR(32)"
```

**Notes:** build the incomplete table with a hand-written `CREATE TABLE`
(not `Base.metadata`), so the test fails for the right reason if the
production code ever starts comparing against something other than the live
DB schema.

---

### TC-025-04 — The schema check runs, unguarded, before the service restart

**Maps to:** AC-025-04
**Type:** unit (structural)
**File:** `backend/tests/test_deploy_schema_check.py`

```gherkin
Given the text of scripts/deploy.sh
Then "set -e" appears near the top of the file, unconditionally
And the schema-check invocation ("backend.schema_check") appears earlier in
  the file than "supervisorctl restart"
And the schema-check invocation is not wrapped in "set +e", "|| true", or
  any construct that discards its exit status
```

**Notes:** this is what makes AC-025-04 hold without a bespoke error-handling
mechanism: `set -e` plus "check before restart" ordering is sufficient, and
this test is what would fail if a future edit reordered the steps or added
an exit-code-swallowing guard around the check.

---

### TC-025-05 — Every difference is reported from a single run

**Maps to:** AC-025-05
**Type:** unit
**File:** `backend/tests/test_schema_check.py`

```gherkin
Given a database missing two columns (in two different tables) and missing
  one whole table relative to Base.metadata
When check_schema_drift is called once
Then the report's missing_columns has exactly those two entries
And missing_tables has exactly that one entry
And no second call was needed to discover any of them
```

---

### TC-025-06 — A column the models no longer declare is not reported

**Maps to:** AC-025-06
**Type:** unit
**File:** `backend/tests/test_schema_check.py`

```gherkin
Given a database that has every model column plus one extra column
  ("legacy_note") that no model declares
When check_schema_drift is called against it
Then the report has no drift
```

---

### TC-025-07 — The standalone CLI reports drift and exits non-zero

**Maps to:** AC-025-07
**Type:** unit
**File:** `backend/tests/test_schema_check.py`

```gherkin
Given a database file missing the products.category_key column
When main(["--database-url", <that file's URL>]) is called
Then it returns 1
And the printed report contains "products", "category_key", and
  "ALTER TABLE"
```

---

### TC-025-08 — The standalone CLI reports no drift and exits zero

**Maps to:** AC-025-07
**Type:** unit
**File:** `backend/tests/test_schema_check.py`

```gherkin
Given a database file initialized from the current models
When main(["--database-url", <that file's URL>]) is called
Then it returns 0
```

**Notes:** TC-025-07 and TC-025-08 together are AC-025-07's "same report,
exit status reflects whether drift was found" — one CLI path, both
outcomes. `main()` is called in-process (via `capsys` for its printed
output) rather than through `subprocess` + `python -m`: it takes an
explicit `argv` and returns the exit code instead of calling `sys.exit`
itself, so the module-invocation wiring (`python -m backend.schema_check`,
covered by a one-line `if __name__ == "__main__"` guard) stays outside the
test — matching `testing-practices.md`'s "don't test framework/interpreter
plumbing" guidance — while still exercising the exact code path that
standalone invocation runs.

---

### TC-025-09 — The dev deploy step cannot swallow a failing deploy.sh

**Maps to:** AC-025-08
**Type:** unit (structural)
**File:** `backend/tests/test_pipeline_wiring.py`

```gherkin
Given the "Deploy candidate to Dev Uberspace" step in the deploy-dev job
Then it has no continue-on-error: true
```

**Notes:** the rest of AC-025-08 (that a failed `deploy-dev` blocks
`acceptance` and `deploy-prod`) is already covered by
`test_deploy_dev_is_bound_to_main_and_development_environment` (TC-015-01)
and `test_prod_deploy_depends_on_acceptance` (TC-015-03) in this same file —
those pin the `needs:` chain this AC relies on. This test case adds the one
piece specific to REQ-025: confirming nothing suppresses the SSH step's own
exit code before GitHub Actions ever sees it.

## Test Fixtures & Mocks

`test_schema_check.py` builds its own SQLite engines per test — either
`sqlite:///:memory:` for pure comparison tests, or a `tmp_path` file for
tests that also exercise `init_db()` or the CLI subprocess (a subprocess
can't share an in-process `:memory:` connection). Incomplete/extra-column
schemas are built with hand-written `CREATE TABLE`/`ALTER TABLE` SQL via
`engine.connect()`, never through `Base.metadata`, so the tests stay
independent of the production comparison code.

`test_deploy_schema_check.py` reads `scripts/deploy.sh` as plain text — no
subprocess, no SSH, matching `test_pipeline_wiring.py`'s approach to
`ci-cd.yml`.

`test_pipeline_wiring.py`'s existing `jobs` fixture (module-scoped, parses
`ci-cd.yml` once) is reused for TC-025-09.

## Notes on Coverage

Covers the new `backend/schema_check.py` module (comparison logic + CLI),
the new schema-check step inside `scripts/deploy.sh`'s step 4, and confirms
(without changing) the CI job graph that already gates `acceptance` and
`deploy-prod` behind `deploy-dev`. No frontend coverage — this REQ has no
user-facing surface.
