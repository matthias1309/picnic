# TEST-006 — User Login & Authentication Tests

**Status:** draft
**Created:** 2026-06-14
**Traces:** ARCH-006
**Verifies:** REQ-006 (AC-006-01, AC-006-02, AC-006-03, AC-006-04, AC-006-05, AC-006-06)

---

## Test Cases

### TC-006-01 — Successful login returns the user and sets a session cookie

**Maps to:** AC-006-01
**Type:** integration (FastAPI TestClient + in-memory SQLite)
**File:** `backend/tests/test_auth.py`

```gherkin
Given a registered user "alice" with password "correct-password"
When the client POSTs /picnic/api/auth/login with
     {"username": "alice", "password": "correct-password"}
Then a 200 response is returned with {"id": ..., "username": "alice"}
And the response sets an httponly "picnic_session" cookie
```

---

### TC-006-02 — Login with the wrong password is rejected

**Maps to:** AC-006-02
**Type:** integration
**File:** `backend/tests/test_auth.py`

```gherkin
Given a registered user "alice" with password "correct-password"
When the client POSTs /picnic/api/auth/login with
     {"username": "alice", "password": "wrong-password"}
Then a 401 response is returned with {"detail": "Invalid username or password"}
And no "picnic_session" cookie is set
```

---

### TC-006-03 — Login with an unknown username is rejected

**Maps to:** AC-006-02
**Type:** integration
**File:** `backend/tests/test_auth.py`

```gherkin
Given no user "ghost" exists
When the client POSTs /picnic/api/auth/login with
     {"username": "ghost", "password": "anything"}
Then a 401 response is returned with {"detail": "Invalid username or password"}
```

---

### TC-006-04 — `GET /auth/me` without a session returns 401

**Maps to:** AC-006-04
**Type:** integration
**File:** `backend/tests/test_auth.py`

```gherkin
Given no "picnic_session" cookie is sent
When the client requests GET /picnic/api/auth/me
Then a 401 response is returned with {"detail": "Not authenticated"}
```

---

### TC-006-05 — `GET /auth/me` with a valid session returns the current user

**Maps to:** AC-006-01, AC-006-05
**Type:** integration
**File:** `backend/tests/test_auth.py`

```gherkin
Given a registered user "alice" has logged in via POST /auth/login
When the client requests GET /picnic/api/auth/me using the returned session cookie
Then a 200 response is returned with {"id": ..., "username": "alice"}
```

---

### TC-006-06 — A protected data endpoint rejects requests without a session

**Maps to:** AC-006-04
**Type:** integration
**File:** `backend/tests/test_auth.py`

```gherkin
Given no "picnic_session" cookie is sent
When the client requests GET /picnic/api/receipts
Then a 401 response is returned with {"detail": "Not authenticated"}
```

---

### TC-006-07 — An expired session is rejected

**Maps to:** AC-006-05
**Type:** integration
**File:** `backend/tests/test_auth.py`

```gherkin
Given a registered user "alice" has a session whose expires_at is in the past
When the client requests GET /picnic/api/auth/me using that session's cookie
Then a 401 response is returned with {"detail": "Not authenticated"}
```

---

### TC-006-08 — Logout invalidates the session

**Maps to:** AC-006-06
**Type:** integration
**File:** `backend/tests/test_auth.py`

```gherkin
Given a registered user "alice" has logged in via POST /auth/login
When the client POSTs /picnic/api/auth/logout using the session cookie
Then a 200 response is returned and the "picnic_session" cookie is cleared
And a subsequent GET /picnic/api/auth/me using the same (old) cookie value
    returns 401
```

---

### TC-006-09 — Unauthenticated dashboard access redirects to `/login`

**Maps to:** AC-006-03
**Type:** unit (React Testing Library, `fetchJson` mocked)
**File:** `frontend/tests/Auth.test.tsx`

```gherkin
Given GET /picnic/api/auth/me responds with 401 (not authenticated)
When the app renders a protected route ("/") inside <ProtectedRoute>
Then the user is redirected to "/login"
And the Login page (username/password form) is shown
```

---

### TC-006-10 — Authenticated user sees the protected page and can log out

**Maps to:** AC-006-03, AC-006-06
**Type:** unit (React Testing Library, `fetchJson` mocked)
**File:** `frontend/tests/Auth.test.tsx`

```gherkin
Given GET /picnic/api/auth/me responds with 200 {"id": 1, "username": "alice"}
When the app renders a protected route ("/") inside <ProtectedRoute>
Then the wrapped page content is shown (no redirect to "/login")
When the user clicks the "Logout" control
Then POST /picnic/api/auth/logout is called
And the user is redirected to "/login"
```

---

## Test Fixtures & Mocks

**Backend (`backend/tests/conftest.py`):**

- `test_user` (new): creates a `User` row (`username="alice"`,
  `password_hash=security.hash_password("correct-password")`) in
  `db_session` and returns it together with the plaintext password.
- `client` (modified): in addition to overriding `get_db`, overrides
  `get_current_user` to return `test_user` by default. This keeps all
  existing TEST-001..005 integration tests (which assume an authenticated
  request) working unchanged.
- `unauthenticated_client` (new): same `TestClient`/`db_session` wiring as
  `client`, but does **not** override `get_current_user` — used to exercise
  the real login/session/401 behavior in TC-006-01..08.

**Frontend (`frontend/tests/Auth.test.tsx`):**

- `fetchJson` (from `src/api/client`) is mocked with `vi.mock` per test to
  return either a 401 `ApiError` (unauthenticated) or a `User` object
  (authenticated), matching the existing pattern in `Dashboard.test.tsx`.
- `renderWithProviders` (existing `tests/test-utils.tsx`) wraps the rendered
  tree in `QueryClientProvider` + `MemoryRouter`; tests render `<App />` (or
  a minimal route tree containing `<ProtectedRoute>`) and assert on the
  resulting location/content.

---

## Notes on Coverage

These test cases target **80%+ coverage** on:
- `backend/auth/security.py` (`hash_password`, `verify_password`,
  `generate_token`, `hash_token`)
- `backend/auth/service.py` (`authenticate_user`, `create_session`,
  `get_session`, `delete_session`)
- `backend/api/auth_routes.py` (`/auth/login`, `/auth/logout`, `/auth/me`)
- `backend/api/dependencies.py` (`get_current_user`)
- `frontend/src/components/ProtectedRoute.tsx`
- `frontend/src/hooks/useAuth.ts`
- `frontend/src/pages/Login.tsx`

**Out of scope:**
- `backend/scripts/manage_users.py` — one-off admin CLI, TDD exception per
  `.claude/rules/v-model.md` (see ARCH-006 Key Decision 5).
- Existing TEST-001..005 suites are unaffected beyond the `client` fixture
  change described above.
