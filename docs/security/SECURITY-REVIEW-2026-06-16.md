# Security Review — Picnic Expense Tracker

**Date:** 2026-06-16
**Scope:** Full codebase scan (backend Python/FastAPI, frontend React/TS, CI/CD, deploy, config)
**Reviewer:** Claude Code (automated security audit)
**Commit/Branch:** `claude/stoic-meitner-beczqx`

---

## Executive Summary

The codebase is in **good security shape for an MVP**. The most important
fundamentals are done correctly: all database access goes through the SQLAlchemy
ORM (no SQL injection surface), passwords are hashed with PBKDF2-HMAC-SHA256
(260k iterations) and compared in constant time, session tokens are
high-entropy and stored hashed, session cookies are `HttpOnly` + `SameSite=Lax`
+ `Secure` (in production), and no secrets are committed to the repository.

No **Critical** issues were found. The findings below are mostly **Medium/Low**
hardening opportunities. The two most worthwhile to address are the
**username-enumeration timing side-channel** on login and the
**missing HTTP security headers**.

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High     | 0 |
| Medium   | 4 |
| Low      | 6 |
| Info     | 3 |

---

## Findings

### M-1 (Medium) — Username enumeration via login timing side-channel
**Location:** `backend/auth/service.py:17-22`

```python
def authenticate_user(db, username, password):
    user = db.query(User).filter_by(username=username).first()
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user
```

When the username does not exist, `verify_password` (which runs 260,000 PBKDF2
iterations) is **never called**, so the response returns measurably faster than
for a valid username with a wrong password. An attacker can use this timing
difference to enumerate valid usernames, even though the error message itself is
generic.

**Recommendation:** When the user is not found, still perform a dummy PBKDF2
verification against a constant fake hash so the work — and therefore the
response time — is the same in both branches.

---

### M-2 (Medium) — Login rate limiting is per-username only (lockout DoS + spraying)
**Location:** `backend/auth/rate_limit.py`, `backend/api/auth_routes.py:26-34`

Rate limiting is keyed solely on `username`. Two consequences:

1. **Targeted account-lockout DoS:** anyone who knows (or guesses) the single
   user's username can deliberately send 5 bad passwords and lock the real user
   out for 15 minutes, repeatedly.
2. **Password spraying:** because the limit is per-username, an attacker trying
   one password across many guessed usernames is never throttled at the IP
   level.

**Recommendation:** Add an IP-based throttle in addition to the per-username
lockout (e.g. limit failed attempts per source IP). For a single-user app the
lockout-DoS risk is modest, but an IP limit closes both gaps cheaply.

---

### M-3 (Medium) — Missing HTTP security headers (clickjacking, MIME sniffing, HSTS)
**Location:** `backend/main.py` (no security-header middleware); not set in repo nginx config either

The app sets no `X-Frame-Options`/`Content-Security-Policy` (clickjacking
protection), `X-Content-Type-Options: nosniff`, `Referrer-Policy`, or
`Strict-Transport-Security`. The dashboard could be framed by a malicious site,
and browsers may MIME-sniff responses.

**Recommendation:** Add a small middleware (or set these in the nginx reverse
proxy that fronts the app on Uberspace) emitting at minimum:
`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` (or a `frame-ancestors`
CSP), `Referrer-Policy: no-referrer`, and `Strict-Transport-Security` over HTTPS.

---

### M-4 (Medium) — No password strength / length policy
**Location:** `backend/schemas.py:12-16` (`LoginRequest`), `backend/scripts/manage_users.py`

There is no minimum length or complexity check when creating/setting a password
(`manage_users.py`) nor any constraint on the login schema. A trivially weak
password ("1234") is accepted. Combined with M-2, weak credentials are the most
realistic path to compromise.

**Recommendation:** Enforce a minimum length (e.g. ≥ 12 chars) in
`manage_users.py` when setting passwords. Since this is an admin CLI for a
single user, a length check there is sufficient.

---

### L-1 (Low) — `DEBUG=true` is the default and drives SQL query echo
**Location:** `backend/config.py:33`, `backend/database.py:17`

`debug` defaults to `True`, and `create_engine(..., echo=settings.debug)` logs
every SQL statement. If a production deployment sets `ENVIRONMENT=production`
but forgets to set `DEBUG=false`, the logs will contain verbose SQL (and the
`.env.example` ships `DEBUG=true`). Security-sensitive behavior is correctly
gated on `is_production` instead of `debug` (good), but log verbosity is not.

**Recommendation:** Default `debug` to `False`, or derive SQL echo from
`not is_production`. Ensure the production `.env` sets `DEBUG=false`.

---

### L-2 (Low) — Expired sessions and login-attempt rows are never purged
**Location:** `backend/auth/service.py` (sessions), `backend/auth/rate_limit.py`

Expired `UserSession` rows are ignored at read time but never deleted, and
`LoginAttempt` rows accumulate. Not exploitable, but the session table grows
unbounded and a stale-but-unexpired token remains valid for the full 30 days
with no rotation or idle timeout.

**Recommendation:** Periodically delete expired sessions (a small APScheduler
job already exists for polling — add a cleanup job). Consider a shorter idle
timeout or token rotation on use.

---

### L-3 (Low) — Full raw email (`raw_email_text`) retained indefinitely
**Location:** `backend/models.py:41`, `backend/main.py:95`

The complete raw MIME message (`msg.as_string()`) is stored permanently in
SQLite. This may include PII (delivery address, names) beyond what the app
needs. A DB leak exposes more than the parsed line items.

**Recommendation:** Consider dropping `raw_email_text` once a receipt is
successfully parsed, or document the retention as intentional (it is currently
used by `scripts/reprocess_receipt.py`).

---

### L-4 (Low) — Aging, pinned dependencies not audited for CVEs
**Location:** `requirements.txt`, `frontend/package.json`

Dependencies are pinned (good for reproducibility) but several are aging
(`fastapi==0.104.1`, `lxml==4.9.3`, `starlette` transitively). No automated
vulnerability scanning is present in CI.

**Recommendation:** Add `pip-audit` (Python) and `npm audit`/Dependabot to the
CI pipeline so known CVEs surface automatically. Per project rules, discuss any
version bumps before applying.

---

### L-5 (Low) — Email body parsed by BeautifulSoup without size limits
**Location:** `backend/imap/parser.py`, `backend/main.py:91-101`

Each fetched email is fully read into memory (`as_string()`) and parsed with
BeautifulSoup. A maliciously large or deeply nested HTML email could cause high
memory/CPU usage during the polling task. Risk is low because the source is a
filtered Picnic mailbox, not arbitrary internet input.

**Recommendation:** Cap the size of fetched messages and skip oversized ones,
to keep the background worker resilient.

---

### L-6 (Low) — CORS allows all methods/headers with credentials
**Location:** `backend/main.py:194-200`

`allow_credentials=True` together with `allow_methods=["*"]` and
`allow_headers=["*"]`. This is **safe today** because `allow_origins` is an
explicit allow-list (not `*`), but the wildcard methods/headers are broader than
needed.

**Recommendation:** Narrow to the methods actually used (`GET, POST, PUT,
DELETE, OPTIONS`) and required headers. Ensure the production `CORS_ORIGINS`
env var is set to the real frontend origin only.

---

### I-1 (Info) — CSRF protection relies on `SameSite=Lax`
**Location:** `backend/api/auth_routes.py:36-44`

State-changing endpoints (`PUT /settings/budget`, `DELETE /receipts/{id}`)
authenticate via the session cookie. `SameSite=Lax` blocks cross-site
`POST/PUT/DELETE`, which is adequate for this MVP, but there is no anti-CSRF
token as defense-in-depth. Acceptable; note for Phase 2.

---

### I-2 (Info) — Root endpoint advertises `/docs`
**Location:** `backend/main.py:217-224`

`GET /picnic/` returns `{"docs": "/docs"}` even in production, where the docs are
disabled. Cosmetic only — the link 404s in prod. Consider gating the hint on
`is_production`.

---

### I-3 (Info) — Message-ID-based dedup trusts an attacker-controllable header
**Location:** `backend/imap/client.py:138-167`, `backend/main.py:69-73`

Receipt deduplication keys on the email `Message-ID`. Since this is read from a
trusted, subject-filtered Picnic mailbox the risk is negligible, but a spoofed
email with a colliding `Message-ID` could suppress ingestion of a real receipt.
Noted for completeness.

---

## Security Strengths (done right)

- **No SQL injection surface** — every query uses the SQLAlchemy ORM with bound
  parameters; no raw SQL, string-formatted queries, or `text()` in app code.
- **Strong password hashing** — PBKDF2-HMAC-SHA256, 260k iterations, per-password
  random salt, constant-time comparison via `hmac.compare_digest`.
- **Sound session handling** — 256-bit random tokens (`secrets.token_urlsafe`),
  stored **hashed** (SHA-256) so a DB leak doesn't expose live sessions;
  cookies are `HttpOnly`, `SameSite=Lax`, and `Secure` in production.
- **No command/template injection** — no `os.system`, `subprocess`, `eval`,
  `pickle`, or `yaml.load`; no `dangerouslySetInnerHTML`/`eval` in the frontend
  (React auto-escapes all rendered values).
- **Secrets hygiene** — no credentials in the repo; `.env` is gitignored,
  `.env.example` ships placeholders, CI uses GitHub Secrets, the SSH deploy key
  is written with `chmod 600`.
- **Generic auth errors + rate limiting** — login returns a generic "Invalid
  username or password" and enforces a lockout after repeated failures.
- **Reduced prod attack surface** — interactive docs and the OpenAPI schema are
  disabled when `ENVIRONMENT=production`.
- **TLS by default for IMAP** — `imap_use_ssl` defaults to `True` (port 993).

---

## Prioritized Remediation Plan

1. **M-1** — Add constant-time dummy hash on unknown username (small, high value).
2. **M-3** — Add security-header middleware / nginx headers.
3. **M-4** — Enforce a password length minimum in `manage_users.py`.
4. **M-2** — Add IP-based login throttling alongside the per-username lockout.
5. **L-1 / L-2** — Default `debug=False`; add an expired-session cleanup job.
6. **L-4** — Wire `pip-audit` + `npm audit` into CI.

*Each fix should follow the V-Model flow (REQ → ARCH → TEST-SPEC → tests →
implementation) per `.claude/rules/v-model.md`.*
