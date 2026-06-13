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

| Setting | Value |
|---|---|
| Uberspace host | `giclas.uberspace.de` |
| Uberspace user | `mattmaxx` |
| App URL | `https://matt-maxx.de/picnic` |
| SSH port | `22` |

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

### Step 3: Configure GitHub Secrets

Go to **GitHub Repository → Settings → Secrets and variables → Actions**

Add these secrets:

| Secret Name | Value |
|---|---|
| `UBERSPACE_SSH_KEY` | Contents of `~/.ssh/picnic_deploy_key` (private key, entire file) |
| `UBERSPACE_HOST` | `giclas.uberspace.de` |
| `UBERSPACE_USER` | `mattmaxx` |
| `UBERSPACE_SSH_PORT` | `22` |

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
    --bind 127.0.0.1:8000
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

## Deployment Workflow

### Automatic Deployment (on push to main)

```bash
git commit -m "feat: add new feature"
git push origin main  # Triggers CI/CD automatically
```

1. GitHub Actions runs tests on all commits
2. If all tests pass, deployment to Uberspace begins
3. `scripts/deploy.sh` pulls latest code, rebuilds, restarts service
4. App is live at https://matt-maxx.de/picnic

### Manual Deployment

To deploy manually (without pushing to main):

```bash
# SSH into Uberspace
ssh -i ~/.ssh/id_ed25519_uberspace mattmaxx@giclas.uberspace.de

# Run deploy script
bash ~/picnic/scripts/deploy.sh
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
CORS_ORIGINS=["https://matt-maxx.de"]
```

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
