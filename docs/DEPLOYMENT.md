# Deployment Guide — Picnic Expense Tracker

## Overview

Picnic is deployed to Uberspace via GitHub Actions CI/CD pipeline:

```
git push to main
    ↓
[GitHub Actions]
    ├─ Test backend (pytest)
    ├─ Test frontend (vitest, build)
    ├─ Lint all code (ruff, eslint)
    └─ Deploy to Uberspace (via SSH)
```

---

## Prerequisites

1. **Uberspace Account** with SSH access
2. **GitHub Repository** with GitHub Actions enabled
3. **SSH Key Pair** for Uberspace authentication
4. **Domain/Reverse Proxy** configured on Uberspace

---

## Server Details

The pipeline deploys to two Uberspace instances — a development stage that runs
acceptance tests, and production (see **Staged Deployment Pipeline** below).

| Setting | Production | Development |
|---|---|---|
| Uberspace host | `giclas.uberspace.de` | `jarnsaxa.uberspace.de` |
| Uberspace user | `mattmaxx` | `mattdev` |
| App URL | `https://matt-maxx.de/picnic` | `https://mattdev.uber.space/picnic` |
| SSH port | `22` | `22` |
| Role | Production | Staging (acceptance-tested before prod) |

**Note:** Your personal SSH key (`~/.ssh/id_ed25519_uberspace`) is for *your* login.
For GitHub Actions, create a **separate, dedicated deploy key** — this way you can
revoke CI/CD access independently without affecting your own access.

---

## Setup Instructions

### Step 1: Generate a Dedicated Deploy Key for GitHub Actions

On your local machine, generate a new ed25519 keypair (do NOT reuse your personal key):

```bash
ssh-keygen -t ed25519 -C "github-actions-picnic-deploy" -f ~/.ssh/picnic_deploy_key -N ""
```

This creates:
- `~/.ssh/picnic_deploy_key` (private key) — goes into GitHub Secrets
- `~/.ssh/picnic_deploy_key.pub` (public key) — goes onto Uberspace

### Step 2: Add the Public Key to Uberspace

Copy the public key to Uberspace's `authorized_keys` (append, don't overwrite):

```bash
# From your local machine
ssh-copy-id -i ~/.ssh/picnic_deploy_key.pub -p 22 mattmaxx@giclas.uberspace.de

# Or manually:
cat ~/.ssh/picnic_deploy_key.pub | ssh -i ~/.ssh/id_ed25519_uberspace mattmaxx@giclas.uberspace.de \
  "cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

Verify the new key works:

```bash
ssh -i ~/.ssh/picnic_deploy_key mattmaxx@giclas.uberspace.de "echo OK"
```

### Step 3: Configure GitHub Environments & Secrets

The pipeline uses two **GitHub Environments** so each stage carries its own host
secrets under the **same names** (the deploy step is host-agnostic). Go to
**GitHub Repository → Settings → Environments** and create:

**Environment `development`** (used by the `deploy-dev` job):

| Secret Name | Value |
|---|---|
| `UBERSPACE_SSH_KEY` | Dev deploy private key (`~/.ssh/picnic_dev_deploy_key`) |
| `UBERSPACE_HOST` | `jarnsaxa.uberspace.de` |
| `UBERSPACE_USER` | `mattdev` |
| `UBERSPACE_SSH_PORT` | `22` |

**Environment `production`** (used by the `deploy-prod` job):

| Secret Name | Value |
|---|---|
| `UBERSPACE_SSH_KEY` | Prod deploy private key (`~/.ssh/picnic_deploy_key`) |
| `UBERSPACE_HOST` | `giclas.uberspace.de` |
| `UBERSPACE_USER` | `mattmaxx` |
| `UBERSPACE_SSH_PORT` | `22` |

On the **`production`** environment, add a **Required reviewers** protection rule
(yourself). This is the manual approval gate: after the dev acceptance tests pass,
the `deploy-prod` job pauses until you approve it (REQ-015, AC-015-04).

> Generate a **separate** deploy key for dev (Steps 1–2, but against
> `mattdev@jarnsaxa.uberspace.de`) so dev and prod access can be revoked
> independently.

**⚠️ Important:** Copy the **entire private key file** including `-----BEGIN OPENSSH PRIVATE KEY-----`
and `-----END OPENSSH PRIVATE KEY-----` lines.

```bash
cat ~/.ssh/picnic_deploy_key
```

`SLACK_WEBHOOK` is optional — only add it if you want Slack deployment notifications.
If not configured, that step is skipped automatically (`continue-on-error: true`).

### Step 4: Configure Uberspace Service (supervisord)

Uberspace manages long-running processes via **supervisord**, configured through
`.ini` files in `~/etc/services.d/`. SSH into Uberspace first:

```bash
ssh -i ~/.ssh/id_ed25519_uberspace mattmaxx@giclas.uberspace.de
```

Create `~/etc/services.d/picnic.ini`:

```ini
[program:picnic]
command=%(ENV_HOME)s/picnic/venv/bin/gunicorn
    --bind 0.0.0.0:8000
    --workers 2
    --timeout 60
    --worker-class uvicorn.workers.UvicornWorker
    --access-logfile %(ENV_HOME)s/logs/picnic/access.log
    --error-logfile %(ENV_HOME)s/logs/picnic/error.log
    backend.main:app
directory=%(ENV_HOME)s/picnic
environment=PATH="%(ENV_HOME)s/picnic/venv/bin"
autostart=true
autorestart=true
```

> Note: `gunicorn` needs the `uvicorn.workers.UvicornWorker` worker class to serve
> a FastAPI (ASGI) app. This is included via `uvicorn[standard]` in `requirements.txt`.

> Note: Bind to `0.0.0.0`, not `127.0.0.1`. Uberspace's reverse proxy runs in a
> separate container and connects via the host network, not localhost — binding
> to `127.0.0.1` causes `uberspace web backend list` to report
> "wrong interface" and the path returns a 502.

Apply the config and start the service:

```bash
mkdir -p ~/logs/picnic
supervisorctl reread
supervisorctl update
supervisorctl start picnic
supervisorctl status picnic
```

### Step 5: Route the Domain Path to the Backend

Uberspace provides a built-in command to route a URL path to a local port —
no manual nginx config needed:

```bash
uberspace web backend set /picnic --http --port 8000
```

Verify the routing:

```bash
uberspace web backend list
```

For the **frontend** (static SPA build), Uberspace serves files directly from
`~/html/`. Serve the built frontend under `/picnic` by either:

- Building into `~/html/picnic/` (set Vite's `base: '/picnic/'` and output there), or
- Routing `/picnic` entirely to the backend and having FastAPI serve the built
  SPA as static files (simplest for a single-path deployment).

For MVP, the deploy script focuses on the backend API. Frontend static hosting
can be wired up once the dashboard (REQ-003) is implemented.

#### Provisioning the Dev Uberspace (one-time)

The development instance (`mattdev@jarnsaxa.uberspace.de`) needs the **same**
one-time setup as production — repeat Steps 1–2 (a dedicated dev deploy key),
Step 4 (the `picnic` supervisord service), and Step 5 (`uberspace web backend set
/picnic --http --port 8000`) while SSH'd into the dev host, and place a dev `.env`
(its own empty SQLite DB; IMAP credentials optional for a pure smoke-test stage).
Once provisioned, the `deploy-dev` job deploys each `main` candidate to it
automatically (staging) before production. Verify with:

```bash
curl https://mattdev.uber.space/picnic/health   # → {"status": "ok"}
```

### Step 6: Test Deployment

Push to main and watch GitHub Actions:

```bash
git push origin main
```

**Check status:**
- GitHub Actions: https://github.com/matthias1309/picnic/actions
- Live app: https://matt-maxx.de/picnic
- Health check: https://matt-maxx.de/picnic/health (should return `{"status": "ok"}`)

---

## Staged Deployment Pipeline

A push to `main` runs the whole chain in **one** pipeline: the candidate is
deployed to the dev (staging) Uberspace, acceptance-tested there, and only then
promoted to production (REQ-015):

```
push to main → backend-test + frontend-test ─┐
                                             ├─→ deploy-dev ──→ acceptance ──→ deploy-prod
                                             ┘   (staging)     (vs dev URL)    (manual approval)
```

- **`deploy-dev`** deploys the `main` commit to `mattdev@jarnsaxa`
  (`DEPLOY_REF=main`) and publishes to `https://mattdev.uber.space/picnic`.
- **`acceptance`** runs `pytest -m acceptance` against the live dev deployment
  (`BASE_URL=https://mattdev.uber.space/picnic`). A red run blocks promotion.
- **`deploy-prod`** `needs: acceptance`, deploys `main` to `mattmaxx@giclas`, and
  **waits for manual approval** on the `production` environment before running.

The acceptance gate is enforced in-run by the `needs` edges (`deploy-prod` →
`acceptance` → `deploy-dev`): production can never deploy unless the dev deploy and
acceptance tests both passed in the same pipeline. No branch-protection rule is
required for the gate itself. Feature work flows through PRs into `main`; the test
jobs run on every push/PR, and only the deploy chain is gated on `main`.

## Deployment Workflow

### Normal flow (PR → main)

```bash
# 1. Open a PR with your feature branch → main (tests run on the PR)
# 2. Merge the PR into main → the full chain runs:
#    deploy-dev → acceptance → deploy-prod (waits for your approval)
```

1. GitHub Actions runs tests on every push/PR.
2. On a push to `main`: deploy the commit to dev, run acceptance against the dev
   URL.
3. If acceptance is green, `deploy-prod` pauses for manual approval, then
   `scripts/deploy.sh` pulls `main`, rebuilds, and restarts the service.
4. App is live at https://matt-maxx.de/picnic

### Manual Deployment

To deploy manually (without pushing to main):

```bash
# SSH into Uberspace
ssh -i ~/.ssh/id_ed25519_uberspace mattmaxx@giclas.uberspace.de

# Run deploy script (defaults to DEPLOY_REF=main; override to deploy another ref)
bash ~/picnic/scripts/deploy.sh

# On the dev host, set the public URL for correct log output:
PUBLIC_BASE_URL=https://mattdev.uber.space/picnic bash ~/picnic/scripts/deploy.sh
```

### Rollback

To rollback to a previous version:

```bash
cd ~/picnic
git log --oneline | head -5  # See recent commits
git reset --hard <commit-hash>

# Restart service
supervisorctl restart picnic
```

---

## Environment Variables

Create `~/picnic/.env` on Uberspace (NOT committed to git):

```bash
# IMAP Configuration
IMAP_HOST=localhost
IMAP_PORT=993
IMAP_USERNAME=user@example.com
IMAP_PASSWORD=your-app-password
IMAP_MAILBOX=INBOX

# Database
DATABASE_URL=sqlite:////home/mattmaxx/data/picnic.db

# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# CORS
CORS_ORIGINS=https://matt-maxx.de

# URL scheme (REQ-019) — see "Cutting Over to a Dedicated Domain" below.
# Leave unset on a host still using path-based routing.
# URL_PREFIX=
# VITE_BASE_PATH=/
# VITE_API_BASE=/api
# FRONTEND_PUBLISH_DIR=/var/www/virtual/mattmaxx/picnic.matt-maxx.de
```

---

## Cutting Over Production to a Dedicated Domain (REQ-019)

Production can be moved off the shared path-based scheme
(`matt-maxx.de/picnic` + `/picnic-frontend/`) onto its own subdomain (e.g.
`picnic.matt-maxx.de`), serving the frontend at the domain root and the API
under `/api`. This is a one-time cutover on the **production** Uberspace
host only — dev/staging keeps the path-based scheme unchanged (it has no
`URL_PREFIX`/`VITE_*`/`FRONTEND_PUBLISH_DIR` lines in its `.env`, so
`scripts/deploy.sh` keeps defaulting to today's values).

1. **DNS:** add `A`/`AAAA` records for the new domain, pointing at the same
   IPs the production host already resolves to
   (`dig +short giclas.uberspace.de`).
2. **Register the domain on Uberspace** (production host only), once DNS has
   propagated:
   ```bash
   ssh -i ~/.ssh/id_ed25519_uberspace mattmaxx@giclas.uberspace.de
   uberspace web domain add picnic.matt-maxx.de
   ```
3. **Route `/api` and `/health` to the backend**, leaving the domain root on
   the default Apache/static backend:
   ```bash
   uberspace web backend set picnic.matt-maxx.de/api --http --port 8000
   uberspace web backend set picnic.matt-maxx.de/health --http --port 8000
   ```
4. **Create the domain's document root** for the static frontend build
   (must live outside `/home`, per Uberspace's DocumentRoot rules):
   ```bash
   mkdir -p /var/www/virtual/mattmaxx/picnic.matt-maxx.de
   printf 'RewriteBase /\n' > /var/www/virtual/mattmaxx/picnic.matt-maxx.de/.htaccess
   ```
5. **Add the four lines** shown in the `.env` example above to
   `~/picnic/.env` on the production host, then run a normal deploy
   (`bash ~/picnic/scripts/deploy.sh`, or push to `main`).
6. **Verify:**
   ```bash
   curl https://picnic.matt-maxx.de/health         # → {"status":"ok"}
   curl https://picnic.matt-maxx.de/api/stats/summary  # → 401 (unauthenticated, expected)
   ```
   and open `https://picnic.matt-maxx.de/` in a browser.

Once this is done, `https://matt-maxx.de/picnic` and `/picnic-frontend/`
stop working (the running backend no longer registers those paths, and the
frontend build's URLs are no longer path-prefixed) — this is intentional,
not a regression; see REQ-019.

---

## Monitoring

### Logs

- **Application logs:** `tail -f ~/logs/picnic/access.log`
- **Error logs:** `tail -f ~/logs/picnic/error.log`
- **Supervisord status:** `supervisorctl status picnic`
- **Supervisord tail:** `supervisorctl tail -f picnic`

### Health Check

```bash
curl https://matt-maxx.de/picnic/health
# Expected: {"status": "ok"}
```

### Database

```bash
sqlite3 ~/data/picnic.db "SELECT COUNT(*) FROM receipts;"
```

---

## Troubleshooting

### Deployment fails in GitHub Actions

**Check:**
- SSH secrets are configured correctly (GitHub Settings → Secrets)
- The dedicated deploy key's public half is in `~/.ssh/authorized_keys` on Uberspace
- `UBERSPACE_HOST=giclas.uberspace.de`, `UBERSPACE_USER=mattmaxx`, `UBERSPACE_SSH_PORT=22`
- Test the key manually: `ssh -i ~/.ssh/picnic_deploy_key mattmaxx@giclas.uberspace.de "echo OK"`

### App doesn't start after deployment

**Check:**
- Service status: `supervisorctl status picnic`
- Logs: `supervisorctl tail -f picnic` or `tail -f ~/logs/picnic/error.log`
- `.env` file exists: `ls -la ~/picnic/.env`
- Database exists: `ls -la ~/data/picnic.db`
- Port is not in use: `lsof -i :8000`

### IMAP Polling not working

**Check:**
- `.env` has correct IMAP credentials
- IMAP credentials are valid (test with: `python -c "from backend.imap.client import IMAPClient; IMAPClient(...).connect()"`)
- Firewall allows outgoing IMAP (port 993)

### Path routing (`/picnic`) not working

**Check:**
- App is running: `curl http://127.0.0.1:8000/health`
- Backend routing is set: `uberspace web backend list` (should show `/picnic -> port 8000`)
- Re-set if missing: `uberspace web backend set /picnic --http --port 8000`

---

## CI/CD Pipeline Details

### GitHub Actions Workflow (`.github/workflows/ci-cd.yml`)

**Triggers:**
- `push` to `main`, `develop`, `claude/**` branches
- `pull_request` to `main`, `develop`

**Jobs:**
1. `backend-test`: Python 3.11 + 3.12, pytest, ruff
2. `frontend-test`: Node.js 18 + 20, npm test, build
3. `deploy`: SSH to Uberspace, run `scripts/deploy.sh` (only on main push)

**Deployment Script** (`.github/workflows/ci-cd.yml` → `scripts/deploy.sh`):
1. Setup directories
2. Pull latest code from main
3. Install Python dependencies
4. Initialize database (if needed)
5. Build frontend (npm run build)
6. Restart service (systemd or supervisord)

---

## Security Considerations

- ✅ SSH keys stored in GitHub Secrets (encrypted)
- ✅ No credentials in code (all in `.env`, gitignored)
- ✅ Deployment requires push to main (controlled access)
- ✅ CORS configured to only allow your domain
- ✅ Database is local (no cloud exposure)

---

## Next Steps

1. **Test deployment:** Push to main and monitor GitHub Actions
2. **Configure monitoring:** Set up log aggregation or Slack alerts
3. **Plan backups:** Regular backup of SQLite database
4. **Phase 2 features:** Email parsing, dashboard, API

---

*Last updated: 2026-06-12*
