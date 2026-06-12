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

## Setup Instructions

### Step 1: Generate SSH Key (if you don't have one)

On your local machine or Uberspace:

```bash
ssh-keygen -t ed25519 -C "github-actions-picnic" -f ~/.ssh/github_deploy_key
```

This creates:
- `~/.ssh/github_deploy_key` (private key) — for GitHub Secrets
- `~/.ssh/github_deploy_key.pub` (public key) — add to Uberspace

### Step 2: Add Public Key to Uberspace

On Uberspace, add the public key to `~/.ssh/authorized_keys`:

```bash
cat ~/.ssh/github_deploy_key.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### Step 3: Configure GitHub Secrets

Go to **GitHub Repository → Settings → Secrets and variables → Actions**

Add these secrets:

| Secret Name | Value | Example |
|---|---|---|
| `UBERSPACE_SSH_KEY` | Private key (entire file contents) | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `UBERSPACE_HOST` | Uberspace hostname | `matt-maxx.de` |
| `UBERSPACE_USER` | Uberspace username | `matthias1309` |
| `UBERSPACE_SSH_PORT` | SSH port (usually 22) | `22` |
| `SLACK_WEBHOOK` | (Optional) Slack webhook for notifications | `https://hooks.slack.com/...` |

**⚠️ Important:** Copy the **entire private key file** including `-----BEGIN` and `-----END` lines.

### Step 4: Configure Uberspace Service

Create a systemd user service or supervisord config:

#### Option A: Systemd (Modern Uberspace)

Create `~/.config/systemd/user/picnic.service`:

```ini
[Unit]
Description=Picnic Expense Tracker
After=network.target

[Service]
Type=notify
WorkingDirectory=%h/picnic
ExecStart=%h/picnic/venv/bin/gunicorn \
    --bind 127.0.0.1:8000 \
    --workers 2 \
    --timeout 60 \
    --access-logfile %h/logs/picnic/access.log \
    --error-logfile %h/logs/picnic/error.log \
    backend.main:app

Restart=always
RestartSec=10

# Environment variables
EnvironmentFile=%h/picnic/.env

[Install]
WantedBy=default.target
```

Enable and start:

```bash
systemctl --user daemon-reload
systemctl --user enable picnic
systemctl --user start picnic
```

#### Option B: Supervisord (Legacy)

Create `/etc/supervisor/conf.d/picnic.conf`:

```ini
[program:picnic]
directory = /home/matthias1309/picnic
command = /home/matthias1309/picnic/venv/bin/gunicorn \
    --bind 127.0.0.1:8000 \
    --workers 2 \
    --timeout 60 \
    backend.main:app
user = matthias1309
autostart = true
autorestart = true
stdout_logfile = /home/matthias1309/logs/picnic/gunicorn.log
stderr_logfile = /home/matthias1309/logs/picnic/gunicorn.error.log
environment = PATH="/home/matthias1309/picnic/venv/bin"
```

Then:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start picnic
```

### Step 5: Configure Nginx Reverse Proxy

On Uberspace, configure nginx to reverse proxy to localhost:8000:

In your Uberspace reverse proxy config (ask Uberspace support if unclear):

```nginx
location /picnic {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
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
ssh matthias1309@matt-maxx.de

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
systemctl --user restart picnic  # or supervisorctl restart picnic
```

---

## Environment Variables

Create `.env` file on Uberspace (NOT committed to git):

```bash
# IMAP Configuration
IMAP_HOST=localhost
IMAP_PORT=993
IMAP_USERNAME=user@example.com
IMAP_PASSWORD=your-app-password
IMAP_MAILBOX=INBOX

# Database
DATABASE_URL=sqlite:////home/matthias1309/data/picnic.db

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

- **Application logs:** `tail -f ~/logs/picnic/gunicorn.log`
- **Systemd logs:** `journalctl --user -u picnic -f`
- **Error logs:** `tail -f ~/logs/picnic/gunicorn.error.log`

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
- SSH key has correct permissions: `chmod 600 ~/.ssh/id_rsa`
- Uberspace host/port/user are correct

### App doesn't start after deployment

**Check:**
- Service status: `systemctl --user status picnic` or `supervisorctl status picnic`
- Logs: `journalctl --user -u picnic -n 50`
- `.env` file exists: `ls -la ~/picnic/.env`
- Database exists: `ls -la ~/data/picnic.db`
- Port is not in use: `lsof -i :8000`

### IMAP Polling not working

**Check:**
- `.env` has correct IMAP credentials
- IMAP credentials are valid (test with: `python -c "from backend.imap.client import IMAPClient; IMAPClient(...).connect()"`)
- Firewall allows outgoing IMAP (port 993)

### Nginx reverse proxy not working

**Check:**
- App is running: `curl http://127.0.0.1:8000/health`
- Nginx is configured: `cat /etc/nginx/sites-enabled/YOUR_DOMAIN | grep picnic`
- Nginx is reloaded: `sudo nginx -t && sudo systemctl reload nginx`

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
