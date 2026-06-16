# ARCH-007 — Login Rate Limiting

**Status:** approved
**Created:** 2026-06-14
**Traces:** REQ-007
**Verified by:** TEST-007

## Summary

ARCH-007 adds a per-username lockout to `POST /picnic/api/auth/login`
(REQ-007). A new `login_attempts` table tracks failed-attempt counts and an
optional `locked_until` timestamp per username. A new
`backend/auth/rate_limit.py` module exposes three small functions used by
`auth_routes.login` to check, record, and reset this state. Because
lockout state lives in the database, it is shared correctly across the 2
Gunicorn workers used in production (see `docs/DEPLOYMENT.md`).

---

## Design

### Component Overview

```
POST /picnic/api/auth/login
        ↓
auth_routes.login(credentials, response, db)
        ↓
rate_limit.is_locked_out(db, username) -> bool          ← new, checked first
  - True  -> raise HTTPException(429, "Too many login attempts...")  (AC-007-01, AC-007-03)
  - False -> continue
        ↓
auth_service.authenticate_user(db, username, password)
  - None    -> rate_limit.record_failed_attempt(db, username)          (AC-007-01)
                raise HTTPException(401, "Invalid username or password")
  - User    -> rate_limit.reset_attempts(db, username)                  (AC-007-02)
                create_session(...) as before                            (AC-007-04)
```

### Data Model

```
backend/models.py
  LoginAttempt                                              ← new
    username: str (primary key)
    failed_count: int
    first_failed_at: datetime
    locked_until: datetime | None
```

`username` is the primary key (not a foreign key to `users.id`) so attempts
against unknown usernames (AC-007-03) can be tracked too, without creating a
`User` row.

### Module: `backend/auth/rate_limit.py`

```python
MAX_FAILED_ATTEMPTS = 5
ATTEMPT_WINDOW = timedelta(minutes=15)
LOCKOUT_DURATION = timedelta(minutes=15)

def is_locked_out(db: Session, username: str) -> bool:
    """True if `username` is currently within an active lockout."""
    # SELECT LoginAttempt WHERE username = ?
    # locked_until is not None and locked_until > now()

def record_failed_attempt(db: Session, username: str) -> None:
    """Record a failed login attempt, locking the account if the
    threshold is reached within the attempt window."""
    # get_or_create LoginAttempt(username)
    # if first_failed_at is None or now - first_failed_at > ATTEMPT_WINDOW:
    #     failed_count = 1; first_failed_at = now
    # else:
    #     failed_count += 1
    # if failed_count >= MAX_FAILED_ATTEMPTS:
    #     locked_until = now + LOCKOUT_DURATION
    # commit

def reset_attempts(db: Session, username: str) -> None:
    """Clear any tracked failed attempts for `username` (successful login)."""
    # DELETE LoginAttempt WHERE username = ?
    # commit
```

### Data Flow — Login with rate limiting (AC-007-01 .. AC-007-04)

```
POST /picnic/api/auth/login  {username, password}
        ↓
if rate_limit.is_locked_out(db, username):
    raise HTTPException(429, "Too many login attempts. Try again later.")  (AC-007-01, AC-007-03)
        ↓
user = authenticate_user(db, username, password)
        ↓
if user is None:
    rate_limit.record_failed_attempt(db, username)                          (AC-007-01)
    raise HTTPException(401, "Invalid username or password")                (unchanged, AC-006-02)
        ↓
rate_limit.reset_attempts(db, username)                                      (AC-007-02)
token = create_session(db, user)
... set cookie, return UserOut ...                                          (AC-007-04, once lockout has expired)
```

### Module Layout

```
backend/
  models.py                   # + LoginAttempt
  auth/
    rate_limit.py              # is_locked_out, record_failed_attempt, reset_attempts  ← new
  api/
    auth_routes.py             # login() calls rate_limit.* around authenticate_user
```

---

## Key Decisions

### 1. Database-backed lockout state, not in-memory

**Decision:** Lockout counters live in a new `login_attempts` table, written
via the existing SQLAlchemy session.

**Rationale:** Production runs 2 Gunicorn workers (`docs/DEPLOYMENT.md`); an
in-memory dict per worker would let an attacker get ~2x the attempt budget
by chance of worker assignment, and would reset on every deploy/restart. A
DB table is simple (one small table, created automatically via
`Base.metadata.create_all` like the existing `sessions`/`users` tables) and
correct across workers and restarts.

### 2. Lockout keyed by username, not IP

**Decision:** `LoginAttempt.username` is the lookup key.

**Rationale:** Per REQ-007 notes — two known household accounts, IP-based
limiting adds complexity (proxy/`X-Forwarded-For` handling on Uberspace) for
no real benefit here, and a username-keyed lock cannot be bypassed by
rotating source IPs.

### 3. Lockout returns 429, distinct from the existing 401

**Decision:** `is_locked_out` short-circuits *before* `authenticate_user` is
called, returning `HTTPException(429, "Too many login attempts. Try again
later.")` — even for usernames that don't exist (AC-007-03), and even if the
correct password is supplied (AC-007-01).

**Rationale:** A distinct status code lets the frontend show a different,
more helpful message ("try again in a few minutes") without changing the
existing AC-006-02 behavior (401 + generic message) for ordinary wrong
passwords. Checking lockout before authentication means a locked-out
attacker learns nothing about whether their guessed password was correct.

### 4. Sliding window via `first_failed_at`, reset on success or window expiry

**Decision:** `record_failed_attempt` resets `failed_count` to 1 and
`first_failed_at` to now whenever the previous failure was outside
`ATTEMPT_WINDOW` (15 min). A successful login deletes the row entirely.

**Rationale:** Keeps the table tiny (one row per username with recent
failures) and the logic simple — no background cleanup job needed. A user
who mistypes their password once or twice, then logs in correctly, is never
affected (AC-007-02).

### 5. Thresholds as module constants

**Decision:** `MAX_FAILED_ATTEMPTS = 5`, `ATTEMPT_WINDOW = 15 min`,
`LOCKOUT_DURATION = 15 min`, defined in `backend/auth/rate_limit.py`.

**Rationale:** Simple named constants per `coding-style.md` ("no magic
numbers"); easy to tune later without touching call sites. Not made
configurable via `.env` — YAGNI for a 2-account MVP.

---

## Out of Scope

- IP-based rate limiting / `X-Forwarded-For` handling.
- CAPTCHA or other interactive challenges.
- Notifying the account owner of lockouts (e.g. email alert).
- Admin tooling to manually clear a lockout (can be done via direct DB
  access if ever needed — two-account MVP).

---

## Open Questions

None.
