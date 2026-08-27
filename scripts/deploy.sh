#!/bin/bash
#
# Deploy script for Picnic Expense Tracker on Uberspace
# Called by GitHub Actions CI/CD pipeline
#
# Environment:
# - $HOME — user home directory on Uberspace
# - PICNIC_ROOT — where the app is deployed
#

set -e  # Exit on error

# Resolve the ref to deploy (DEPLOY_REF, default main). The logic lives in a
# separate file so it stays unit-testable without SSH (REQ-015). CI pipes
# deploy_lib.sh ahead of this script over the same SSH stdin stream (so
# resolve_deploy_ref is already defined before this line runs); a manual
# invocation from a checked-out repo has no such stream, so fall back to
# sourcing the file from disk next to this script.
if ! declare -F resolve_deploy_ref > /dev/null; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    # shellcheck source=scripts/deploy_lib.sh
    source "${SCRIPT_DIR}/deploy_lib.sh"
fi
DEPLOY_REF="$(resolve_deploy_ref)"

PICNIC_ROOT="${HOME}/picnic"
PICNIC_DB="${HOME}/data/picnic.db"
PICNIC_LOG="${HOME}/logs/picnic"
VENV="${PICNIC_ROOT}/venv"
FRONTEND_BUILD="${PICNIC_ROOT}/frontend/dist"
# Public URL is for log output only; the health check below uses the internal
# port, which is identical on both Uberspace hosts.
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://matt-maxx.de/picnic}"

# Per-host config (REQ-019): read from PICNIC_ROOT/.env, which already
# exists by this point (created once by hand per docs/DEPLOYMENT.md, before
# the first deploy). Defaults reproduce today's single hardcoded scheme, so
# a host whose .env has none of these lines behaves exactly as before.
URL_PREFIX="$(read_env_default URL_PREFIX /picnic "${PICNIC_ROOT}/.env")"
VITE_BASE_PATH="$(read_env_default VITE_BASE_PATH /picnic-frontend/ "${PICNIC_ROOT}/.env")"
VITE_API_BASE="$(read_env_default VITE_API_BASE /picnic/api "${PICNIC_ROOT}/.env")"
FRONTEND_PUBLISH_DIR="$(read_env_default FRONTEND_PUBLISH_DIR "$HOME/html/picnic-frontend" "${PICNIC_ROOT}/.env")"

echo "======================================"
echo "Picnic Expense Tracker - Deploy Script"
echo "======================================"
echo "Ref: $DEPLOY_REF"
echo "Public URL: $PUBLIC_BASE_URL"
echo "Root: $PICNIC_ROOT"
echo "Database: $PICNIC_DB"
echo "Logs: $PICNIC_LOG"

# ============================================================
# 1. Setup directories
# ============================================================
echo ""
echo "[1/6] Setting up directories..."
mkdir -p "$PICNIC_ROOT" "$HOME/data" "$PICNIC_LOG"

# ============================================================
# 2. Clone/Pull latest code
# ============================================================
echo "[2/6] Updating repository..."
if [ -d "$PICNIC_ROOT/.git" ]; then
    cd "$PICNIC_ROOT"
    git fetch origin "$DEPLOY_REF"
    git reset --hard "origin/${DEPLOY_REF}"
    echo "✓ Repository updated to origin/${DEPLOY_REF}"
else
    git clone https://github.com/matthias1309/picnic.git "$PICNIC_ROOT"
    cd "$PICNIC_ROOT"
    echo "✓ Repository cloned"
fi

# ============================================================
# 3. Install/Update Python dependencies
# ============================================================
echo "[3/6] Installing Python dependencies..."
if [ ! -d "$VENV" ]; then
    python3.12 -m venv "$VENV"
    echo "✓ Virtual environment created"
fi

source "$VENV/bin/activate"
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ Python dependencies installed"

# ============================================================
# 4. Setup database
# ============================================================
echo "[4/6] Setting up database..."
if [ ! -f "$PICNIC_DB" ]; then
    # Initialize database if it doesn't exist. create_all only ever adds
    # missing tables from current metadata, so a fresh database can never
    # be reported as drifting (REQ-025 AC-025-02).
    python -c "from backend.database import init_db; init_db()"
    echo "✓ Database initialized"
else
    echo "✓ Database already exists"
    # Fail fast if the existing database is missing a table or column the
    # models expect, printing the exact SQL to fix it (REQ-025). This must
    # stay ahead of the frontend build and the restart below: set -e turns
    # a non-zero exit here into an abort before either runs, so a drifted
    # database never gets new code restarted on top of it.
    python -m backend.schema_check
    echo "✓ Schema matches models, no drift"
fi

# ============================================================
# 5. Build frontend and publish to the web document root
# ============================================================
echo "[5/6] Building frontend..."
if command -v node &> /dev/null; then
    cd "$PICNIC_ROOT/frontend"
    npm ci --quiet
    VITE_BASE_PATH="$VITE_BASE_PATH" VITE_API_BASE="$VITE_API_BASE" npm run build --quiet
    echo "✓ Frontend built (base=$VITE_BASE_PATH, api=$VITE_API_BASE)"

    # Publish the built SPA to FRONTEND_PUBLISH_DIR (defaults to
    # ~/html/picnic-frontend, served at https://matt-maxx.de/picnic-frontend/;
    # prod points this at picnic.matt-maxx.de's own document root instead).
    rm -rf "$FRONTEND_PUBLISH_DIR"
    mkdir -p "$FRONTEND_PUBLISH_DIR"
    cp -r "$FRONTEND_BUILD"/. "$FRONTEND_PUBLISH_DIR/"

    # Written after the copy so the rm -rf/cp above cannot clobber it, and any
    # stale hand-written .htaccess is replaced (REQ-021).
    write_spa_fallback "$FRONTEND_PUBLISH_DIR" "$VITE_BASE_PATH"
    echo "✓ Frontend published to $FRONTEND_PUBLISH_DIR (SPA fallback written)"
else
    echo "⚠ Node.js not found, skipping frontend build"
    echo "  (Frontend must be pre-built by GitHub Actions)"
fi

# ============================================================
# 6. Restart backend service (Uberspace supervisord)
# ============================================================
echo "[6/6] Restarting backend service..."

# Uberspace manages daemons via supervisord with configs in ~/etc/services.d/*.ini
supervisorctl reread
supervisorctl update
supervisorctl restart picnic
echo "✓ Service restarted via supervisord"

# Wait for the app to come up before declaring the deployment successful
# (gunicorn workers need a moment to bind after a restart)
echo "Waiting for health check..."
for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -fs "http://127.0.0.1:8000${URL_PREFIX}/health" > /dev/null; then
        echo "✓ Health check passed"
        break
    fi
    if [ "$i" -eq 10 ]; then
        echo "✗ Health check failed after restart"
        supervisorctl status picnic
        exit 1
    fi
    sleep 2
done

echo ""
echo "======================================"
echo "✓ Deployment successful!"
echo "======================================"
echo "API URL:       $PUBLIC_BASE_URL"
echo "Logs: $PICNIC_LOG"
echo ""
echo "Next steps:"
echo "1. Check logs: tail -f $PICNIC_LOG/picnic.log"
echo "2. Test: curl $PUBLIC_BASE_URL/health"
echo ""
