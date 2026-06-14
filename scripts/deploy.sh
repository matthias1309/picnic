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

PICNIC_ROOT="${HOME}/picnic"
PICNIC_DB="${HOME}/data/picnic.db"
PICNIC_LOG="${HOME}/logs/picnic"
VENV="${PICNIC_ROOT}/venv"
FRONTEND_BUILD="${PICNIC_ROOT}/frontend/dist"

echo "======================================"
echo "Picnic Expense Tracker - Deploy Script"
echo "======================================"
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
    git fetch origin main
    git reset --hard origin/main
    echo "✓ Repository updated"
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
    # Initialize database if it doesn't exist
    python -c "from backend.database import init_db; init_db()"
    echo "✓ Database initialized"
else
    echo "✓ Database already exists"
fi

# ============================================================
# 5. Build frontend and publish to the web document root
# ============================================================
echo "[5/6] Building frontend..."
if command -v node &> /dev/null; then
    cd "$PICNIC_ROOT/frontend"
    npm ci --quiet
    npm run build --quiet
    echo "✓ Frontend built"

    # Publish the built SPA so it's served at https://matt-maxx.de/picnic-frontend/
    # (Uberspace serves static files from ~/html)
    rm -rf "$HOME/html/picnic-frontend"
    mkdir -p "$HOME/html/picnic-frontend"
    cp -r "$FRONTEND_BUILD"/. "$HOME/html/picnic-frontend/"
    echo "✓ Frontend published to ~/html/picnic-frontend"
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
    if curl -fs http://127.0.0.1:8000/picnic/health > /dev/null; then
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
echo "API URL:       https://matt-maxx.de/picnic"
echo "Dashboard URL: https://matt-maxx.de/picnic-frontend/"
echo "Logs: $PICNIC_LOG"
echo ""
echo "Next steps:"
echo "1. Check logs: tail -f $PICNIC_LOG/picnic.log"
echo "2. Test: curl https://matt-maxx.de/picnic/health"
echo "3. Open: https://matt-maxx.de/picnic-frontend/"
echo ""
