# ARCH-023 — Deploy-Generated SPA Fallback for the Published Frontend

**Status:** approved
**Created:** 2026-08-27
**Traces:** REQ-023
**Verified by:** TEST-023

## Summary

The deploy gains one more responsibility: after copying the built SPA into
`FRONTEND_PUBLISH_DIR`, it writes an Apache `.htaccess` next to `index.html`
that rewrites every request without a matching file or directory to
`index.html`. That single file is what makes reload and back navigation work
on client-side routes.

No application code changes — the SPA, its router and the API are untouched.
This is purely about how the static bundle is served.

## Design

### `write_spa_fallback` in `scripts/deploy_lib.sh`

The generator lives in `deploy_lib.sh` (not inline in `deploy.sh`) for the
same reason `resolve_deploy_ref` and `read_env_default` do: it stays
unit-testable in a subprocess without SSH or a real Apache.

```
write_spa_fallback <publish_dir> <base_path>
```

writes `<publish_dir>/.htaccess` containing, wrapped in
`<IfModule mod_rewrite.c>`:

```
RewriteEngine On
RewriteBase <base_path>
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule . index.html [L]
```

The two `RewriteCond` lines are what satisfies AC-023-02: an existing asset
resolves to a real filename and is served directly; only genuinely
non-existent paths reach the rewrite.

`base_path` is the host's `VITE_BASE_PATH` (`/` on prod, `/picnic-frontend/`
on dev/staging — REQ-019), which is by construction the URL path the publish
directory is served at, so `RewriteBase` is always correct for the host
without introducing a second configuration value. The `<IfModule>` guard
means a host without `mod_rewrite` serves the app (minus deep links) instead
of returning a 500.

### Call site in `scripts/deploy.sh`

Invoked in step 5 directly after `cp -r "$FRONTEND_BUILD"/. "$FRONTEND_PUBLISH_DIR/"`.
Writing it *after* the copy is what satisfies AC-023-04 — the preceding
`rm -rf`/`cp` cannot clobber it, and any stale hand-written `.htaccess` is
replaced by the generated one.

## Alternatives Considered

- **`frontend/public/.htaccess` (checked into the repo, copied by Vite).**
  Rejected: `RewriteBase` would have to be hardcoded, so one file cannot
  serve both the root-mounted prod host and the `/picnic-frontend/` dev host,
  and it depends on Vite's dotfile-copy behaviour for `publicDir`.
- **Hash routing (`/#/stats`).** Rejected: changes every URL the user already
  has, and REQ-019 explicitly aimed at clean URLs.
- **Serving the SPA from FastAPI with a catch-all route.** Rejected: the
  static bundle is deliberately served by Apache/nginx, not through Gunicorn
  (CLAUDE.md deployment section); routing it through Python would be slower
  and a larger change than one config file.

## Consequences

- A request for a genuinely missing asset (e.g. a stale hashed bundle after a
  deploy) now returns `index.html` with status 200 instead of a 404. Accepted:
  the SPA renders its own not-found state, and the alternative (enumerating
  asset paths in the rewrite) adds configuration for a case that only occurs
  with a stale cached document.
- `docs/DEPLOYMENT.md` step 4 of the REQ-019 cutover no longer needs its
  manual `printf 'RewriteBase /' > .htaccess` line; the deploy owns that file
  now, and the doc is updated to say so.
