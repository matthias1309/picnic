# ARCH-019 — Configurable URL Prefix and Frontend Base Path

**Status:** draft
**Created:** 2026-08-17
**Traces:** REQ-019
**Verified by:** TEST-019

## Summary

Today's `/picnic` (backend) and `/picnic-frontend/` (frontend) path segments
are hardcoded in application code, because both environments have always
shared the same path-based Uberspace routing scheme. Production is moving to
its own domain (`picnic.matt-maxx.de`) where those segments are unwanted.
This makes the three hardcoded values — backend router prefix, frontend Vite
`base`, frontend `API_BASE` — configurable via environment variables, each
defaulting to today's value, so dev/staging (which keeps the path-based
scheme) needs no configuration change at all. A fourth value, the frontend
build's publish directory in `scripts/deploy.sh`, becomes configurable for
the same reason (prod needs to publish into a domain-specific document root
instead of the shared `~/html/picnic-frontend`).

All four values are read from the per-host `.env` file, the mechanism this
project already uses for every other host-specific setting (`DATABASE_URL`,
`CORS_ORIGINS`, IMAP credentials — see `docs/DEPLOYMENT.md`). No change to
`.github/workflows/ci-cd.yml` or GitHub Environment secrets is needed.

## Design

### Backend: `URL_PREFIX` setting

`backend/config.py`'s `Settings` gets one new field:

```python
url_prefix: str = "/picnic"
```

`backend/main.py` extracts the router-wiring into a small pure function so
it's unit-testable at any prefix without touching the global `app` (which
carries scheduler/IMAP startup side effects), then calls it once at import
time with the real setting:

```python
def build_router(prefix: str) -> APIRouter:
    """Wire health/root/auth/api routes under the given prefix."""
    router = APIRouter(prefix=prefix)
    router.get("/health")(health)
    router.get("/")(root)
    router.include_router(auth_router, prefix="/api")
    router.include_router(api_router, dependencies=[Depends(get_current_user)])
    return router


app.include_router(build_router(settings.url_prefix))
```

FastAPI's `APIRouter` accepts `prefix=""` (root-mounted), so setting
`URL_PREFIX=` (empty) in prod's `.env` mounts `/health`, `/`, and
`/api/*` directly at the domain root; leaving `URL_PREFIX` unset in dev's
`.env` keeps every route under `/picnic/*`, unchanged.

### Frontend: `VITE_BASE_PATH` and `VITE_API_BASE`

Both resolution rules are extracted into small, pure, directly unit-testable
functions (same rationale as `build_router` on the backend — testing them
doesn't require running an actual Vite build or importing `import.meta.env`):

`frontend/src/config/basePath.ts` (new file):

```ts
export function resolveBasePath(env: Record<string, string | undefined>): string {
  return env.VITE_BASE_PATH ?? "/picnic-frontend/";
}
```

`frontend/vite.config.ts` currently hardcodes `base`; it calls the resolver
with Node's `process.env` (Vite config files execute in Node, so this is
available directly — no `.env.production` file needed):

```ts
base: command === "build" ? resolveBasePath(process.env) : "/",
```

`frontend/src/api/client.ts` currently hardcodes `API_BASE`; it gets the
same treatment:

```ts
export function resolveApiBase(env: Record<string, string | undefined>): string {
  return env.VITE_API_BASE ?? "/picnic/api";
}
const API_BASE = resolveApiBase(import.meta.env);
```

Vite exposes any `VITE_`-prefixed variable on `import.meta.env`, statically
replaced at build time. Both env vars must be present in the shell that
invokes `npm run build` — `scripts/deploy.sh` exports them (see below) after
reading them from `.env`.

`main.tsx`'s `BrowserRouter basename={import.meta.env.BASE_URL...}` already
derives the router's basename from Vite's `base` config
([frontend/src/main.tsx](../../frontend/src/main.tsx)) — no change needed
there; client-side routing automatically follows whatever `base` the build
used.

### `scripts/deploy_lib.sh`: shared `.env` reader

A new helper, alongside the existing `resolve_deploy_ref`, kept in
`deploy_lib.sh` so it stays unit-testable without SSH (same rationale as
REQ-015's `resolve_deploy_ref`):

```bash
# Echo the value of KEY from a dotenv-style file, or DEFAULT_VALUE if KEY is
# not present as a line in the file at all. A line present with an empty
# value (KEY=) is honored as an explicit override — this is what lets prod's
# .env set URL_PREFIX= to mean "no prefix" while a dev .env with no
# URL_PREFIX line at all keeps defaulting to /picnic.
read_env_default() {
    local key="$1" default_value="$2" env_file="$3"
    if [ -f "$env_file" ] && grep -qE "^${key}=" "$env_file"; then
        grep -E "^${key}=" "$env_file" | tail -1 | cut -d= -f2-
    else
        echo "$default_value"
    fi
}
```

### `scripts/deploy.sh`: read config, apply it

```bash
URL_PREFIX="$(read_env_default URL_PREFIX /picnic "${PICNIC_ROOT}/.env")"
VITE_BASE_PATH="$(read_env_default VITE_BASE_PATH /picnic-frontend/ "${PICNIC_ROOT}/.env")"
VITE_API_BASE="$(read_env_default VITE_API_BASE /picnic/api "${PICNIC_ROOT}/.env")"
FRONTEND_PUBLISH_DIR="$(read_env_default FRONTEND_PUBLISH_DIR "$HOME/html/picnic-frontend" "${PICNIC_ROOT}/.env")"
```

read right after `PICNIC_ROOT` is defined (the `.env` file already exists by
this point in a real deploy — it's created once by hand per
`docs/DEPLOYMENT.md`'s "Environment Variables" section, before the first
deploy).

- **Frontend build step:** export `VITE_BASE_PATH` and `VITE_API_BASE`
  before `npm run build`; publish to `FRONTEND_PUBLISH_DIR` instead of the
  hardcoded `$HOME/html/picnic-frontend`.
- **Health check step:** poll
  `http://127.0.0.1:8000${URL_PREFIX}/health` instead of the hardcoded
  `.../picnic/health`.

### Per-host `.env` (operational, not committed)

| Variable | Dev `.env` (`mattdev@jarnsaxa`) | Prod `.env` (`mattmaxx@giclas`) |
|---|---|---|
| `URL_PREFIX` | _(unset → `/picnic`)_ | `URL_PREFIX=` (empty) |
| `VITE_BASE_PATH` | _(unset → `/picnic-frontend/`)_ | `VITE_BASE_PATH=/` |
| `VITE_API_BASE` | _(unset → `/picnic/api`)_ | `VITE_API_BASE=/api` |
| `FRONTEND_PUBLISH_DIR` | _(unset → `~/html/picnic-frontend`)_ | `FRONTEND_PUBLISH_DIR=/var/www/virtual/mattmaxx/picnic.matt-maxx.de` |
| `PUBLIC_BASE_URL` (already exists, passed by CI, unrelated to this REQ) | `https://mattdev.uber.space/picnic` | `https://picnic.matt-maxx.de` |

Setting these four lines in prod's `.env`, plus the Uberspace-side domain
and routing setup (REQ-019 Notes, out of scope for code), is the full
cutover — no further deploy needed beyond the next regular one once `.env`
is updated.

## Key Decisions

- **Env vars sourced from `.env`, not passed through CI/SSH command
  arguments.** `PUBLIC_BASE_URL` and `DEPLOY_REF` are today passed inline in
  the SSH command (`ci-cd.yml`) because they vary *per pipeline run*. These
  four values vary *per host*, permanently — exactly what `.env` already
  exists for. Keeping them there means zero changes to `ci-cd.yml` or GitHub
  Environment secrets, and one less place a value has to be kept in sync.
- **"Present but empty" vs. "absent" distinction in `read_env_default`.**
  Bash's `${VAR:-default}` treats empty and unset identically, which would
  make `URL_PREFIX=` in prod's `.env` silently fall back to `/picnic` — the
  opposite of what's needed. `read_env_default` checks line presence with
  `grep` first, so an explicit empty override is honored.
- **`APIRouter(prefix="")` over restructuring the route tree.** FastAPI
  already supports an empty prefix natively; no route needs to move or be
  redefined, only the one `prefix=` argument.
- **Vite `base` read from `process.env` directly, no `.env.production`
  file.** Vite config files run in Node before any Vite-specific env
  loading happens; reading `process.env.VITE_BASE_PATH` (set by
  `deploy.sh`'s `export` before invoking `npm run build`) is simpler than
  introducing a second, Vite-specific env-file mechanism alongside the
  project's existing single `.env` convention.
- **Rejected: dual-mounting the backend router at both `/picnic` and `""`
  simultaneously.** Would keep old prod URLs alive, but the user confirmed
  old prod URLs are retired, so the added permanent complexity (two mounted
  routers, two sets of docs, double the route count in `/docs`) buys
  nothing.

## Out of Scope

- DNS records for `picnic.matt-maxx.de`.
- `uberspace web domain add` / `uberspace web backend set` on the prod host.
- Creating the domain-specific document root directory
  (`/var/www/virtual/mattmaxx/picnic.matt-maxx.de`) and its `.htaccess` —
  manual one-time Uberspace provisioning, tracked as an ops step, not code.
- Writing the actual prod `.env` file on the server (manual, per
  `docs/DEPLOYMENT.md`'s existing "Environment Variables" process — this
  ARCH only defines which keys it reads).
- Retiring/redirecting the old `matt-maxx.de/picnic*` URLs — once prod's
  `.env` switches to the new values, those paths simply 404 (the running
  process no longer registers them); no explicit redirect is implemented.

## Open Questions

None — the one open design question (keep old prod URLs alive vs. retire
them) was resolved with the user before this REQ was written (REQ-019
Notes).
