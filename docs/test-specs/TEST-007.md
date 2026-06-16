# TEST-007 — Login Rate Limiting Tests

**Status:** approved
**Created:** 2026-06-14
**Traces:** ARCH-007
**Verifies:** REQ-007 (AC-007-01, AC-007-02, AC-007-03, AC-007-04)

---

## Test Cases

### TC-007-01 — Lockout after 5 failed attempts rejects the next attempt with 429

**Maps to:** AC-007-01
**Type:** integration (FastAPI TestClient + in-memory SQLite)
**File:** `backend/tests/test_login_rate_limit.py`

```gherkin
Given a registered user "alice" with password "correct-password"
When the client POSTs /picnic/api/auth/login with the wrong password 5 times
And then POSTs /picnic/api/auth/login with the correct password
Then the 6th response is 429 Too Many Requests
And no "picnic_session" cookie is set
```

---

### TC-007-02 — Successful login resets the failed-attempt counter

**Maps to:** AC-007-02
**Type:** integration
**File:** `backend/tests/test_login_rate_limit.py`

```gherkin
Given a registered user "alice" with password "correct-password"
When the client POSTs /picnic/api/auth/login with the wrong password 3 times
And then POSTs /picnic/api/auth/login with the correct password
Then that response is 200 with a "picnic_session" cookie
When the client then POSTs /picnic/api/auth/login with the wrong password once more
Then that response is 401 (not 429) — the earlier failures were cleared
```

---

### TC-007-03 — Lockout applies equally to unknown usernames

**Maps to:** AC-007-03
**Type:** integration
**File:** `backend/tests/test_login_rate_limit.py`

```gherkin
Given no user "ghost" exists
When the client POSTs /picnic/api/auth/login with username "ghost" 5 times
     (any password)
And then POSTs /picnic/api/auth/login with username "ghost" again
Then the 6th response is 429 Too Many Requests, the same as for a locked-out
     real account
```

---

### TC-007-04 — An expired lockout no longer blocks login

**Maps to:** AC-007-04
**Type:** integration
**File:** `backend/tests/test_login_rate_limit.py`

```gherkin
Given a registered user "alice" with password "correct-password"
And a LoginAttempt row for "alice" with locked_until in the past
When the client POSTs /picnic/api/auth/login with the correct password
Then the response is 200 with a "picnic_session" cookie
```

---

### TC-007-05 — A single failed attempt does not trigger a lockout

**Maps to:** AC-007-01 (boundary)
**Type:** integration
**File:** `backend/tests/test_login_rate_limit.py`

```gherkin
Given a registered user "alice" with password "correct-password"
When the client POSTs /picnic/api/auth/login with the wrong password once
Then the response is 401 (not 429)
```

---

## Test Fixtures & Mocks

**Backend (`backend/tests/conftest.py`):**

- Reuses the existing `unauthenticated_client`, `db_session`, and `test_user`
  fixtures (added for TEST-006) — no new fixtures required.
- TC-007-04 inserts a `LoginAttempt` row directly via `db_session`, following
  the same pattern as TC-006-07 (expired session) — set `locked_until` to a
  timestamp in the past.

---

## Notes on Coverage

These test cases target **80%+ coverage** on:
- `backend/auth/rate_limit.py` (`is_locked_out`, `record_failed_attempt`,
  `reset_attempts`)
- The rate-limiting branch added to `backend/api/auth_routes.py` (`login`)

**Out of scope:**
- `LoginAttempt` ORM model itself — trivial declarative mapping, covered
  indirectly by the integration tests above (per
  `.claude/rules/testing-practices.md`, "What Not to Test").
