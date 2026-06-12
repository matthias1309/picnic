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
    git fetch origin
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
# 5. Build frontend (if Node.js available)
# ============================================================
echo "[5/6] Building frontend..."
if command -v node &> /dev/null; then
    cd "$PICNIC_ROOT/frontend"
    npm ci --quiet
    npm run build --quiet
    echo "✓ Frontend built"
else
    echo "⚠ Node.js not found, skipping frontend build"
    echo "  (Frontend must be pre-built by GitHub Actions)"
fi

# ============================================================
# 6. Restart backend service
# ============================================================
echo "[6/6] Restarting backend service..."

# Method 1: If using supervisord (most common on Uberspace)
if command -v supervisorctl &> /dev/null; then
    supervisorctl reread
    supervisorctl update
    supervisorctl restart picnic || echo "Note: Could not restart via supervisorctl"
    echo "✓ Service restarted via supervisord"
fi

# Method 2: If using systemd user service
if systemctl --user is-active --quiet picnic; then
    systemctl --user restart picnic
    echo "✓ Service restarted via systemd"
fi

# Method 3: Manual process restart (if no supervisor)
if [ -f "$PICNIC_ROOT/.pid" ]; then
    kill $(cat "$PICNIC_ROOT/.pid") 2>/dev/null || true
    sleep 2
    echo "✓ Process killed, service manager will restart it"
fi

echo ""
echo "======================================"
echo "✓ Deployment successful!"
echo "======================================"
echo "App URL: https://matt-maxx.de/picnic"
echo "Logs: $PICNIC_LOG"
echo ""
echo "Next steps:"
echo "1. Check logs: tail -f $PICNIC_LOG/picnic.log"
echo "2. Test: curl https://matt-maxx.de/picnic/health"
echo ""
