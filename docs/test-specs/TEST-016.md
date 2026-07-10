# TEST-016 — Idempotent Receipt Parsing Under Concurrent Workers

**Status:** approved
**Created:** 2026-07-10
**Traces:** ARCH-016
**Verifies:** REQ-016 (AC-016-01, AC-016-02, AC-016-03)

---

## Test Cases

### TC-016-01 — Only one of two concurrent sessions claims a pending receipt

**Maps to:** AC-016-01
**Type:** unit
**File:** `backend/tests/test_services.py`

```gherkin
Given a receipt with processed=False, persisted to a file-backed SQLite
  database (not :memory:, so two independent sessions genuinely share state,
  as two Gunicorn worker processes would)
And two independent Session objects open on that same database file
When _claim_receipt_for_processing(db, receipt_id) is called from the first
  session
And then from the second session, for the same receipt_id
Then the first call returns True
And the second call returns False
And the receipt's processed column is True (claimed exactly once)
```

**Notes:** the in-memory `db_session` fixture (StaticPool, single shared
connection) cannot exercise this — it would only prove one session can update
a row, not that a second, independent connection is correctly locked out. This
test builds its own file-backed engine/session pair via `tmp_path`.

---

### TC-016-02 — parse_pending_receipts skips a receipt claimed elsewhere

**Maps to:** AC-016-01
**Type:** unit
**File:** `backend/tests/test_services.py`

```gherkin
Given a pending receipt with valid invoice HTML
And the receipt is claimed by another session immediately before
  parse_pending_receipts(db) runs (simulating the losing side of the race)
When parse_pending_receipts(db) is called
Then no receipt_items or price_history rows are stored for that receipt
And ParseSummary reports parsed=0, failed=0, items=0
```

**Notes:** this is the regression test for the production bug — it proves
`parse_pending_receipts` itself (not just the claim helper in isolation) skips
a receipt it loses the race for, instead of storing a duplicate copy.

---

### TC-016-03 — A failed parse releases the receipt for retry

**Maps to:** AC-016-02
**Type:** unit
**File:** `backend/tests/test_services.py`

```gherkin
Given a pending receipt with malformed HTML (no item rows)
When parse_pending_receipts(db) is called
Then the receipt ends with processed=False
And a second call to parse_pending_receipts(db) still attempts to parse it
  again (it is not permanently stuck claimed)
```

**Notes:** extends the existing TC-002-09 assertion (`malformed_receipt.processed
is False`) with an explicit second run, since the claim-before-parse change is
exactly the kind of thing that could accidentally leave a receipt claimed
forever on failure.

---

### TC-016-04 — No regression on the existing parse_pending_receipts suite

**Maps to:** AC-016-03
**Type:** unit (existing tests, re-run unchanged)
**File:** `backend/tests/test_services.py`

```gherkin
Given the existing tests TC-002-07, TC-002-08, TC-002-09, TC-002-10,
  TC-002-11, TC-013-03, TC-014-04, TC-014-05
When parse_pending_receipts(db) is called under normal, single-caller
  conditions (as all of those tests do)
Then all of them continue to pass without modification
```

**Notes:** no new fixtures or edits to these tests; they are the regression
guard for the refactor. Listed explicitly so the CR can check them off.

---

## Test Fixtures & Mocks

No new fixture files. TC-016-01 and TC-016-02 build a short-lived file-backed
SQLite database directly in the test body via `tmp_path`, `create_engine`, and
`sessionmaker`, mirroring how two Gunicorn workers each hold their own
connection to the same on-disk `picnic.db`. `Base.metadata.create_all` is
called against that engine the same way `db_session` does for the in-memory
case.

## Notes on Coverage

Extends coverage of `backend/services/receipt_service.py`
(`parse_pending_receipts`, new `_claim_receipt_for_processing`). No parser,
API, or schema change for REQ-016.
