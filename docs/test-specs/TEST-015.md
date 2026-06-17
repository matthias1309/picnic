# TEST-015 — Staged Deployment with a Dev Acceptance Gate

**Status:** approved
**Created:** 2026-06-17
**Traces:** ARCH-015
**Verifies:** REQ-015 (AC-015-01, AC-015-02, AC-015-03, AC-015-04, AC-015-05, AC-015-06)

---

## Test Cases

### TC-015-01 — Dev deploy job is bound to develop and the development environment

**Maps to:** AC-015-01
**Type:** unit (workflow structure)
**File:** `backend/tests/test_pipeline_wiring.py`

```gherkin
Given the parsed .github/workflows/ci-cd.yml
When the deploy-dev job is inspected
Then its environment name is "development"
And its `if` condition requires github.ref == 'refs/heads/develop'
And it needs both backend-test and frontend-test
```

---

### TC-015-02 — Acceptance job runs after dev deploy against the dev URL

**Maps to:** AC-015-02
**Type:** unit (workflow structure)
**File:** `backend/tests/test_pipeline_wiring.py`

```gherkin
Given the parsed ci-cd.yml
When the acceptance job is inspected
Then it needs deploy-dev
And it runs `pytest` with the acceptance marker
And BASE_URL is set to https://mattdev.uber.space/picnic
```

---

### TC-015-03 — Production deploy depends on the acceptance job

**Maps to:** AC-015-03
**Type:** unit (workflow structure)
**File:** `backend/tests/test_pipeline_wiring.py`

```gherkin
Given the parsed ci-cd.yml
When the deploy-prod job is inspected
Then deploy-prod.needs includes "acceptance"
So a failed/absent acceptance job prevents the production deploy
```

---

### TC-015-04 — Production deploy is gated on main and the production environment

**Maps to:** AC-015-04
**Type:** unit (workflow structure)
**File:** `backend/tests/test_pipeline_wiring.py`

```gherkin
Given the parsed ci-cd.yml
When the deploy-prod job is inspected
Then its environment name is "production"
And its `if` condition requires github.ref == 'refs/heads/main'
```

> The manual-approval requirement of AC-015-04 is a GitHub environment protection
> rule (required reviewer), configured outside the repository; it is verified by
> the operator runbook in `docs/DEPLOYMENT.md`, not by an automated test.

---

### TC-015-05 — Deploy ref resolves from DEPLOY_REF, defaulting to main

**Maps to:** AC-015-05
**Type:** unit
**File:** `backend/tests/test_deploy_ref.py`

```gherkin
Given the resolve_deploy_ref helper in scripts/deploy_lib.sh
When DEPLOY_REF="develop" is set
Then it resolves to "develop"
And when DEPLOY_REF is unset
Then it resolves to "main"
```

---

### TC-015-06 — Acceptance suite asserts health and the auth contract

**Maps to:** AC-015-02, AC-015-06
**Type:** acceptance (live HTTP)
**File:** `backend/tests/acceptance/test_smoke.py`

```gherkin
Given BASE_URL points at a running deployment
When GET <BASE_URL>/health is requested
Then the status is 200 and the body is {"status": "ok"}
When GET a protected /api route is requested without a session
Then the status is 401 (app up, auth wired), not 5xx or a connection error

Given BASE_URL is unset
When the acceptance suite is collected
Then every acceptance test is skipped (no network in the unit job)
```

---

## Test Fixtures & Mocks

- TC-015-01..04 parse `ci-cd.yml` with PyYAML and assert on the `jobs` graph
  (`needs`, `if`, `environment.name`, and the acceptance step's `BASE_URL`/marker).
  No network, no Docker — pure structural assertions.
- TC-015-05 invokes the sourced shell helper via `subprocess` (or re-implements
  the trivial default-resolution in the test) with `DEPLOY_REF` set/unset in the
  child env.
- TC-015-06 uses `requests` against `BASE_URL`. A `base_url` fixture in
  `backend/tests/acceptance/conftest.py` returns `os.environ["BASE_URL"]` or calls
  `pytest.skip()` when unset, guaranteeing the unit job never makes network calls.
- The protected route used is an existing `/picnic/api/*` endpoint that requires a
  session (REQ-006); any authenticated route returning 401 unauthenticated works.

---

## Notes on Coverage

Covers the pipeline wiring (`ci-cd.yml` job graph and environment bindings), the
deploy-ref resolution (`scripts/deploy_lib.sh`), and the live acceptance contract
(`backend/tests/acceptance/`). The acceptance suite is environment-agnostic and is
run in CI against the dev deployment.

**Out of scope:** the GitHub manual-approval protection rule (settings, verified by
runbook); identical-artifact promotion; seeded dev data; browser/E2E acceptance;
rollback automation.
