# ARCH-006 — User Login & Authentication

**Status:** approved
**Created:** 2026-06-14
**Traces:** REQ-006
**Verified by:** TEST-006

## Summary

ARCH-006 adds a login-protected session for the two household accounts
(REQ-006). A new `users` table holds accounts with hashed passwords; a new
`sessions` table backs an opaque, httponly session cookie. A FastAPI
dependency (`get_current_user`) protects every existing `/picnic/api/*`
route (receipts, products, stats) except the new `/picnic/api/auth/*`
endpoints used for login/logout/session-check. The React SPA gains a
`/login` page and a `ProtectedRoute` wrapper that redirects to it whenever
`GET /picnic/api/auth/me` returns 401.

---

## Design

### Component Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│  FastAPI app (backend/main.py)                                         │
│   router = APIRouter(prefix="/picnic")                                 │
│     /health                       — unauthenticated (deploy healthcheck)│
│     auth_router (prefix=/api/auth) — login/logout public, me protected  │
│     api_router  (prefix=/api)      — receipts/products/stats, ALL routes│
│                                       behind Depends(get_current_user)  │  ← new
└──────────────────────────────────────────────────────────────────────┘
                              ↓ depends on
┌──────────────────────────────────────────────────────────────────────┐
│  backend/api/dependencies.py                                           │
│   get_db            (existing, re-export)                              │
│   get_current_user(request, db) -> User                                │  ← new
│     - reads "picnic_session" cookie                                     │
│     - looks up backend/auth/service.get_session(db, token)             │
│     - raises 401 if missing/expired                                     │
└──────────────────────────────────────────────────────────────────────┘
                              ↓ calls
┌──────────────────────────────────────────────────────────────────────┐
│  backend/auth/service.py                                                │  ← new
│   authenticate_user(db, username, password) -> User | None             │
│   create_session(db, user) -> token (sets 30-day expiry)                │
│   get_session(db, token) -> User | None  (None if missing/expired)      │
│   delete_session(db, token) -> None                                     │
└──────────────────────────────────────────────────────────────────────┘
                              ↓ uses
┌──────────────────────────────────────────────────────────────────────┐
│  backend/auth/security.py                                               │  ← new
│   hash_password(password) -> str   (PBKDF2-HMAC-SHA256, stdlib hashlib) │
│   verify_password(password, hash) -> bool                               │
│   generate_token() -> str          (secrets.token_urlsafe(32))          │
│   hash_token(token) -> str         (sha256, for DB storage)             │
└──────────────────────────────────────────────────────────────────────┘
                              ↓ persists to
┌──────────────────────────────────────────────────────────────────────┐
│  backend/models.py                                                      │
│   User(id, username, password_hash, created_at)                         │  ← new
│   UserSession(token_hash, user_id, expires_at, created_at)              │  ← new
└──────────────────────────────────────────────────────────────────────┘
```

```
┌──────────────────────────────────────────────────────────────────────┐
│  frontend/src/                                                          │
│   pages/Login.tsx               — username/password form               │  ← new
│   components/ProtectedRoute.tsx — wraps protected <Route> elements      │  ← new
│   hooks/useAuth.ts               — useCurrentUser, useLogin, useLogout  │  ← new
│   api/client.ts                  — fetch(..., { credentials: "include" })│
│   App.tsx                         — adds "/login" route + Logout button │
└──────────────────────────────────────────────────────────────────────┘
```

### Endpoints

| Method | Path | Auth required | Maps to |
|--------|------|----------------|---------|
| POST | `/picnic/api/auth/login` | no | AC-006-01, AC-006-02 |
| POST | `/picnic/api/auth/logout` | no (clears cookie if present) | AC-006-06 |
| GET | `/picnic/api/auth/me` | yes | AC-006-03, AC-006-04, AC-006-05 |
| GET/POST/... | all existing `/picnic/api/*` routes | yes | AC-006-04 |
| GET | `/picnic/health` | no (unchanged) | — |

### Data Flow — Login (AC-006-01, AC-006-02)

```
POST /picnic/api/auth/login  {username, password}
        ↓
auth_routes.login(body, db)
        ↓
auth_service.authenticate_user(db, username, password)
  - look up User by username
  - security.verify_password(password, user.password_hash)
  - return user, or None
        ↓
if None: raise HTTPException(401, "Invalid username or password")  (AC-006-02)
else:
  token = auth_service.create_session(db, user)   # stores hash_token(token), expires_at = now + 30d
  response.set_cookie(
    "picnic_session", token,
    httponly=True, secure=(not settings.debug), samesite="lax",
    max_age=30 * 24 * 3600, path="/picnic",
  )
  return UserOut(id=user.id, username=user.username)            (AC-006-01)
```

### Data Flow — Session check / protected routes (AC-006-03, AC-006-04, AC-006-05)

```
Any request to /picnic/api/* (except /api/auth/login)
        ↓
get_current_user(request, db = Depends(get_db))
  token = request.cookies.get("picnic_session")
  if token is None: raise HTTPException(401, "Not authenticated")
  user = auth_service.get_session(db, token)   # joins sessions -> users, checks expires_at > now
  if user is None: raise HTTPException(401, "Not authenticated")
  return user
        ↓
route handler runs as before, receives `current_user: User = Depends(get_current_user)`
  (unused by existing routes — both accounts see the same shared household data)
```

Frontend `ProtectedRoute`:

```
ProtectedRoute renders
  -> useCurrentUser() -> GET /picnic/api/auth/me   (cookie sent automatically)
  -> isLoading        -> <LoadingSpinner />
  -> isError (401)    -> <Navigate to="/login" replace />
  -> success          -> render the wrapped route's children
```

### Data Flow — Logout (AC-006-06)

```
POST /picnic/api/auth/logout
        ↓
auth_routes.logout(request, response, db)
  token = request.cookies.get("picnic_session")
  if token: auth_service.delete_session(db, token)
  response.delete_cookie("picnic_session", path="/picnic")
        ↓
frontend: queryClient.removeQueries() (auth + data) -> navigate("/login")
```

### Module Layout

```
backend/
  models.py                  # + User, UserSession
  schemas.py                  # + LoginRequest, UserOut
  auth/
    __init__.py
    security.py               # hash_password, verify_password, generate_token, hash_token
    service.py                  # authenticate_user, create_session, get_session, delete_session
  api/
    auth_routes.py              # auth_router: /auth/login, /auth/logout, /auth/me
    dependencies.py              # + get_current_user
  main.py                       # mounts auth_router; api_router gets
                                  #   dependencies=[Depends(get_current_user)]
  scripts/
    manage_users.py              # CLI: create/update the two accounts (admin tool)

frontend/src/
  pages/Login.tsx
  components/ProtectedRoute.tsx
  hooks/useAuth.ts               # useCurrentUser, useLogin, useLogout
  types/index.ts                 # + User
  api/client.ts                  # fetchJson adds credentials: "include"
  App.tsx                         # "/login" route (public) + ProtectedRoute
                                   #   wrapping "/", "/stats", "/receipts*";
                                   #   nav shows Logout when authenticated
```

---

## Key Decisions

### 1. Opaque DB-backed session tokens in an httponly cookie, not JWT

**Decision:** Login issues a random token (`secrets.token_urlsafe(32)`),
stored hashed in a new `sessions` table with `expires_at`. The raw token is
set as an `httponly`, `samesite=lax` cookie (`secure` in production).

**Rationale:** Avoids adding a JWT library (`python-jose`/`PyJWT`) — per
CLAUDE.md, new dependencies need discussion, and a 2-user MVP has no need for
stateless tokens. DB-backed sessions make logout (AC-006-06) trivial (delete
the row) and let a session be revoked server-side if needed. The cookie
itself never needs to be parsed/decoded by the frontend.

### 2. Password hashing via stdlib `hashlib.pbkdf2_hmac`, no new dependency

**Decision:** `backend/auth/security.py` implements PBKDF2-HMAC-SHA256
(260,000 iterations, random 16-byte salt per user) using only `hashlib` and
`secrets` from the standard library, storing `pbkdf2_sha256$<iterations>$<salt>$<hash>`
in `users.password_hash`.

**Rationale:** `bcrypt`/`passlib` would be nicer APIs but are new
dependencies; PBKDF2 via stdlib is a recognized, adequate algorithm for a
2-account personal app and keeps `requirements.txt` unchanged.

### 3. Single auth mechanism protects both frontend and API (cookie-based)

**Decision:** The same `picnic_session` cookie (path `/picnic`) is checked by
`get_current_user` for every `/picnic/api/*` request. The frontend never
stores or reads the token in JS — `fetchJson` adds `credentials: "include"`
and relies on the browser to attach the cookie.

**Rationale:** Satisfies AC-006-04 (API rejects unauthenticated requests)
without a separate token-storage mechanism in the SPA (avoiding
`localStorage`-based JWT, which is more XSS-exposed). Same-origin deployment
(`matt-maxx.de`) means no cross-site cookie issues; the Vite dev proxy keeps
dev same-origin too (per ARCH-005 decision 2).

**Note:** the static SPA bundle itself (`/picnic-frontend/*`) remains
publicly downloadable — only the data (`/picnic/api/*`) and the in-app routes
(via `ProtectedRoute`) are gated. The JS/CSS bundle contains no secrets, so
this is acceptable for the MVP (see Out of Scope).

### 4. `get_current_user` applied at router-inclusion level

**Decision:** In `backend/main.py`,
`router.include_router(api_router, dependencies=[Depends(get_current_user)])`
protects every route already defined in `backend/api/routes.py` without
modifying that file. `auth_router` is included separately (unprotected
`/login`, `/logout`; `/me` declares its own `Depends(get_current_user)`).

**Rationale:** Minimal, centralized change — new routes added to
`routes.py` in the future are automatically protected; no per-route
boilerplate.

### 5. No self-registration — `backend/scripts/manage_users.py` CLI

**Decision:** A small script using `auth.security.hash_password` and the
existing `SessionLocal`/`User` model lets the developer create or update the
two accounts from the command line (`python -m backend.scripts.manage_users
create <username>`, prompts for password via `getpass`).

**Rationale:** Matches REQ-006's "no self-registration" note. This is a
one-off admin utility with no business logic to unit-test beyond
`security.hash_password`/`verify_password` (which ARE covered by TEST-006) —
TDD exception per `.claude/rules/v-model.md` for the CLI wrapper itself.

### 6. Frontend auth state lives in TanStack Query, not Zustand

**Decision:** `useCurrentUser()` (`GET /picnic/api/auth/me`) is the single
source of truth for "is logged in". `useLogin`/`useLogout` mutations
invalidate/reset this query on success.

**Rationale:** Consistent with ARCH-005 decision 5 (no server state
duplicated into Zustand); `ProtectedRoute` and the nav's Logout button both
read the same query result.

---

## Out of Scope

- Password reset / change-password UI (REQ-006 notes: developer updates via
  `manage_users.py`).
- Role-based permissions — both accounts have identical access to the shared
  household data.
- Rate limiting / brute-force lockout on `/auth/login` — acceptable risk for
  a personal, low-traffic MVP; revisit if exposed beyond the household.
- Multi-factor authentication, "remember this device", refresh-token
  rotation.
- Restricting access to the static SPA bundle itself (see Key Decision 3).

---

## Open Questions

None — REQ-006's open items (account storage, scope, session length) were
resolved with the developer before writing this document (DB-backed users
table, frontend + API both protected, 30-day sessions).
