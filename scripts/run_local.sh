#!/usr/bin/env bash
# ==============================================================================
# scripts/run_local.sh
# One-click script to run TriagePilot locally on Linux / macOS
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================================="
echo "  Starting TriagePilot — Autonomous Initial Analyst Cockpit"
echo "=========================================================="

# Check Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "Error: Python 3.11+ is required but not found in PATH." >&2
    exit 1
fi

PYTHON_CMD=$(command -v python3 || command -v python)

# Check UI Build
if [ ! -d "$REPO_ROOT/ui/dist" ]; then
    echo "[*] UI dist not found. Building React Cockpit..."
    cd "$REPO_ROOT/ui"
    if [ ! -d "node_modules" ]; then
        echo "[*] Installing Node dependencies..."
        npm install
    fi
    npm run build
    echo "[+] React Cockpit built successfully!"
    cd "$REPO_ROOT"
else
    echo "[+] UI distribution found at $REPO_ROOT/ui/dist"
fi

# Launch Server
PORT="${PORT:-8080}"
echo ""
echo "=========================================================="
echo "  TriagePilot is live and listening on: http://localhost:${PORT}"
echo "  Press Ctrl+C to stop the server."
echo "=========================================================="
echo ""

cd "$REPO_ROOT"
exec "$PYTHON_CMD" -m uvicorn api.main:app --host 0.0.0.0 --port "${PORT}"
