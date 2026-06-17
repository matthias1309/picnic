# ARCH-015 — Staged Deployment with a Dev Acceptance Gate

**Status:** approved
**Created:** 2026-06-17
**Traces:** REQ-015
**Verified by:** TEST-015

## Summary

The single-stage pipeline (test → deploy to production on `main`) is replaced by a
linear three-stage flow that runs in **one** pipeline on a push to `main`:
**test → deploy the candidate to the dev (staging) Uberspace → acceptance tests
against that dev deployment → deploy to production**. Production deploys only after
the acceptance stage is green (it `needs: acceptance`) and only after a manual
approval on the `production` GitHub environment. The deploy script is parametrised
so the same script deploys any ref to either host. A new HTTP-level acceptance
suite, driven by `BASE_URL`, is the executable gate.

## Design

### Pipeline shape (`.github/workflows/ci-cd.yml`)

```
backend-test ─┐
              ├─→ deploy-dev ──→ acceptance ──→ deploy-prod
frontend-test ┘   (staging)     (vs dev URL)    (manual approval)
                  ── all gated on push to main, one linear run ──
```

- `deploy-dev`
  - `needs: [backend-test, frontend-test]`
  - `if: github.event_name == 'push' && github.ref == 'refs/heads/main'`
  - `environment: { name: development, url: https://mattdev.uber.space/picnic }`
  - SSH-deploys the candidate with `DEPLOY_REF=main` to the dev host.
- `acceptance`
  - `needs: deploy-dev`
  - Sets `BASE_URL=https://mattdev.uber.space/picnic`, installs dev deps, runs
    `pytest -m acceptance`.
- `deploy-prod`
  - `needs: acceptance`
  - `if: github.event_name == 'push' && github.ref == 'refs/heads/main'`
  - `environment: { name: production, url: https://matt-maxx.de/picnic }`
  - SSH-deploys with `DEPLOY_REF=main`.

A push to `main` runs the full chain in a single pipeline. The `needs: deploy-dev`
and `needs: acceptance` edges form a hard, in-run gate: if the dev deploy or the
acceptance tests fail, `deploy-prod` is skipped. The dev host therefore acts as a
staging environment for the exact commit about to be promoted to production.

> **Why not `develop → dev, main → prod`:** that model runs dev/acceptance and
> prod in *separate* pipeline runs (one per branch), so a direct merge to `main`
> that bypasses `develop` would reach production without acceptance ever running.
> The linear single-branch model removes that footgun: acceptance is always in the
> same run, immediately before prod, enforced by `needs`. Feature work still flows
> through PRs into `main`; the test jobs run on every push/PR, only the deploy
> chain is gated on `main`.

### Environments & secrets

Two GitHub environments hold per-host secrets under the **same names**, so the
deploy step is host-agnostic:

| Secret | `development` | `production` |
|---|---|---|
| `UBERSPACE_HOST` | `jarnsaxa.uberspace.de` | `giclas.uberspace.de` |
| `UBERSPACE_USER` | `mattdev` | `mattmaxx` |
| `UBERSPACE_SSH_PORT` | `22` | `22` |
| `UBERSPACE_SSH_KEY` | dev deploy private key | prod deploy private key |

The **manual production gate** is a `production` environment protection rule
(required reviewer) configured in GitHub settings — not workflow YAML. This is the
mechanism behind AC-015-04 and cannot be bypassed by editing the workflow alone.

### Deploy script parametrisation (`scripts/deploy.sh`)

The hard-coded ref is replaced by an env-driven one (AC-015-05):

```bash
DEPLOY_REF="${DEPLOY_REF:-main}"   # production-safe default
...
git fetch origin "$DEPLOY_REF"
git reset --hard "origin/${DEPLOY_REF}"
```

Everything else is unchanged: `$HOME`-relative paths already differ per user, the
supervisord app is `picnic` on both hosts, and the internal health check
`http://127.0.0.1:8000/picnic/health` is identical on dev and prod. The public
URL is only used for human-readable log output and is derived from an optional
`PUBLIC_BASE_URL` (defaulting to the prod URL) so dev logs are not misleading.

The ref-resolution rule (`DEPLOY_REF` or default `main`) is extracted into a tiny
pure helper so it is unit-testable without SSH:

`scripts/deploy_lib.sh` → `resolve_deploy_ref()` echoes `"$DEPLOY_REF"` when set,
else `main`. `deploy.sh` sources it. This keeps AC-015-05 a fast, hermetic test.

### Acceptance suite (`backend/tests/acceptance/`)

- `conftest.py` (or a small `base_url` fixture) reads `BASE_URL`; if unset, the
  suite is **skipped**, so the normal unit-test job (which never sets it) is
  unaffected and a developer running `pytest` locally does not hit the network.
- `test_smoke.py`, marked `@pytest.mark.acceptance`:
  - `GET <BASE_URL>/health` → `200`, body `{"status": "ok"}` (AC-015-06).
  - `GET <BASE_URL>/api/<protected>` without a session → `401` (app is up and
    auth middleware is wired, not a 5xx / connection error) (AC-015-06).
- A `pytest` marker `acceptance` is registered in `pyproject.toml`; the unit job
  runs `pytest backend/tests/ -m "not acceptance"` so live tests never run there.
- HTTP is done with `requests` (already a transitive dep via the stack; if not
  present it is added to `requirements-dev.txt` only — never to runtime
  `requirements.txt`).

### Workflow-wiring guard (`backend/tests/test_pipeline_wiring.py`)

A lightweight test parses `ci-cd.yml` (PyYAML) and asserts the gate cannot be
silently removed (AC-015-01/03/04):

- `deploy-dev` is bound to `environment.name == development` and gated on the
  `main` ref.
- `acceptance.needs` includes `deploy-dev`.
- `deploy-prod.needs` includes `acceptance`, is bound to `production`, and gated
  on the `main` ref.

This is structural verification, not a live deploy, and runs in the normal job.

## Out of Scope

- Provisioning the dev Uberspace (supervisord `picnic` service, `uberspace web
  backend set /picnic --http --port 8000`, deploy key install, dev `.env`) — a
  one-time manual operator runbook in `docs/DEPLOYMENT.md`.
- Identical-artifact promotion dev→prod (each env builds from its ref).
- Seeded dev data, browser/E2E acceptance, blue/green, automated rollback.
- Identical-artifact promotion dev→prod — dev and prod each run `deploy.sh` on the
  same `main` commit, but rebuild independently rather than promoting one artifact.
