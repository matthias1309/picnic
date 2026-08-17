# TEST-019 — Configurable URL Prefix and Frontend Base Path

**Status:** approved
**Created:** 2026-08-17
**Traces:** ARCH-019
**Verifies:** REQ-019 (AC-019-01, AC-019-02, AC-019-03, AC-019-04, AC-019-05, AC-019-06, AC-019-07)

## Test Cases

### TC-019-01 — Empty URL_PREFIX mounts routes at the domain root

**Maps to:** AC-019-01
**Type:** unit
**File:** `backend/tests/test_url_prefix.py`

```gherkin
Given the backend router is built via build_router("")
When a client requests GET /health, GET /, or GET /api/stats/budget
  (authenticated) against a test app mounting that router
Then each responds with 200 at its unprefixed path
And GET /picnic/health returns 404 against that same test app
```

**Notes:** Build a throwaway `FastAPI()` test app per test
(`app.include_router(build_router(""))`), not the real module-level `app` —
keeps this a fast unit test with no scheduler/IMAP startup involved. Reuse
existing auth fixtures/dependency overrides from `conftest.py` for the
authenticated `/api` call.

---

### TC-019-02 — Default URL_PREFIX keeps today's /picnic-prefixed behavior

**Maps to:** AC-019-02
**Type:** unit
**File:** `backend/tests/test_url_prefix.py`

```gherkin
Given the backend router is built via build_router("/picnic")
  (the default when URL_PREFIX is unset)
When a client requests GET /picnic/health and GET /picnic/api/stats/budget
  (authenticated) against a test app mounting that router
Then each responds exactly as it does today (200, same payload shape)
And GET /health (no prefix) returns 404 against that same test app
```

**Notes:** Mirrors TC-019-01 with the opposite prefix; confirms the default
argument value reproduces current production behavior byte-for-byte.

---

### TC-019-03 — Frontend resolvers produce root-relative values for prod config

**Maps to:** AC-019-03
**Type:** unit
**File:** `frontend/tests/UrlConfig.test.ts`

```gherkin
Given VITE_BASE_PATH="/" and VITE_API_BASE="/api" in the env object
When resolveBasePath(env) and resolveApiBase(env) are called
Then resolveBasePath returns "/" and resolveApiBase returns "/api"
```

**Notes:** Unit-level proxy for the full AC — verifies the resolver
functions Vite's config and the API client call at build time. The full
built-bundle claim ("no reference to /picnic-frontend/ or /picnic/api
appears in the output") is verified manually once during the prod cutover
deploy (`docs/DEPLOYMENT.md` checklist), not by an automated test — building
a real bundle per test run is out of proportion to what's being verified
here (two string constants).

---

### TC-019-04 — Frontend resolvers keep today's dev defaults when unset

**Maps to:** AC-019-04
**Type:** unit
**File:** `frontend/tests/UrlConfig.test.ts`

```gherkin
Given an empty env object (VITE_BASE_PATH and VITE_API_BASE both unset)
When resolveBasePath(env) and resolveApiBase(env) are called
Then resolveBasePath returns "/picnic-frontend/" and resolveApiBase
  returns "/picnic/api" — today's hardcoded values, unchanged
```

**Notes:** Directly guards the backward-compatibility contract dev/staging
depends on.

---

### TC-019-05 — read_env_default resolves URL_PREFIX with empty-override semantics

**Maps to:** AC-019-05
**Type:** unit
**File:** `backend/tests/test_deploy_env.py`

```gherkin
Given a temp .env file containing the line "URL_PREFIX="
When read_env_default URL_PREFIX /picnic <that file> is invoked
Then it echoes "" (the explicit empty override, not the /picnic default)

Given a temp .env file with no URL_PREFIX line at all
When read_env_default URL_PREFIX /picnic <that file> is invoked
Then it echoes "/picnic" (the default)
```

**Notes:** Same subprocess-sourcing pattern as
`backend/tests/test_deploy_ref.py`'s `_resolve` helper (source
`deploy_lib.sh`, invoke the function, capture stdout) — no SSH, no real
deploy. `scripts/deploy.sh`'s actual `curl http://127.0.0.1:8000${URL_PREFIX}/health`
line is not separately integration-tested; it's a one-line consumer of an
already-tested pure function, verified by code review, matching this
project's existing convention for `deploy.sh` (see TC-015-05 in
`TEST-015.md`, which tests `resolve_deploy_ref` the same way).

---

### TC-019-06 — read_env_default resolves FRONTEND_PUBLISH_DIR with the same semantics

**Maps to:** AC-019-06
**Type:** unit
**File:** `backend/tests/test_deploy_env.py`

```gherkin
Given a temp .env file containing
  "FRONTEND_PUBLISH_DIR=/var/www/virtual/mattmaxx/picnic.matt-maxx.de"
When read_env_default FRONTEND_PUBLISH_DIR $HOME/html/picnic-frontend
  <that file> is invoked
Then it echoes "/var/www/virtual/mattmaxx/picnic.matt-maxx.de"

Given a temp .env file with no FRONTEND_PUBLISH_DIR line at all
When read_env_default FRONTEND_PUBLISH_DIR $HOME/html/picnic-frontend
  <that file> is invoked
Then it echoes "$HOME/html/picnic-frontend" (today's hardcoded default)
```

**Notes:** Confirms `read_env_default` is a general-purpose helper, not
`URL_PREFIX`-specific — same function, second key, second pair of cases.

---

### TC-019-07 — No regression on existing suites

**Maps to:** AC-019-07
**Type:** n/a (regression gate, not a new test)
**File:** n/a

**Notes:** Satisfied by running the existing `pytest` and `npm test` suites
unmodified after implementation — both must stay green. No new test case;
listed here only so the AC has a traceable verification method.
