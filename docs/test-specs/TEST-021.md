# TEST-021 — Deep Links Survive Browser Reload and Back Navigation

**Status:** approved
**Created:** 2026-08-27
**Traces:** ARCH-021
**Verifies:** REQ-021 (AC-021-01, AC-021-02, AC-021-03, AC-021-04)

## Test Cases

### TC-021-01 — The published directory gets a fallback to index.html

**Maps to:** AC-021-01
**Type:** unit
**File:** `backend/tests/test_deploy_spa_fallback.py`

```gherkin
Given an empty temp directory standing in for FRONTEND_PUBLISH_DIR
When write_spa_fallback <dir> / is invoked
Then <dir>/.htaccess exists
And it enables the rewrite engine and rewrites unmatched paths to index.html
```

**Notes:** Sources `deploy_lib.sh` in a subprocess and calls the function
directly, like `test_deploy_env.py` / `test_deploy_ref.py` — no SSH, no
Apache, milliseconds per test.

---

### TC-021-02 — Existing files are excluded from the rewrite

**Maps to:** AC-021-02
**Type:** unit
**File:** `backend/tests/test_deploy_spa_fallback.py`

```gherkin
Given write_spa_fallback has written the fallback configuration
When the generated rules are inspected
Then the rewrite is guarded by "not an existing file" and "not an existing
  directory" conditions
```

**Notes:** The guard is asserted at the configuration level. Actually
resolving a request through Apache is out of scope for a unit test; the
served behaviour is verified once manually after deploy (AC-021-01/02 in
`docs/DEPLOYMENT.md`).

---

### TC-021-03 — RewriteBase follows the host's frontend base path

**Maps to:** AC-021-03
**Type:** unit
**File:** `backend/tests/test_deploy_spa_fallback.py`

```gherkin
Given the two base paths the project deploys with
When write_spa_fallback is invoked with "/" and with "/picnic-frontend/"
Then the generated configuration bases the rewrite at exactly that path
```

---

### TC-021-04 — A stale hand-written configuration is replaced

**Maps to:** AC-021-04
**Type:** unit
**File:** `backend/tests/test_deploy_spa_fallback.py`

```gherkin
Given a publish directory that already contains an .htaccess without a
  fallback rule (the hand-written "RewriteBase /" from the REQ-019 cutover)
When write_spa_fallback is invoked for that directory
Then the file is overwritten with the generated configuration
```

**Notes:** Covers the deploy-order half of AC-021-04 at the unit level. That
`scripts/deploy.sh` calls the function after the `rm -rf` + `cp` publish step
is verified by reading the script during code review (CR-021), not by
executing a full deploy in the test suite.
