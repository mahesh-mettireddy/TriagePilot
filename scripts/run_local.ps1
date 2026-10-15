# ==============================================================================
# scripts/run_local.ps1
# One-click script to run TriagePilot locally on Windows
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Starting TriagePilot — Autonomous Initial Analyst Cockpit" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check Python
$pythonCmd = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $pythonCmd) {
    Write-Error "Python not found in PATH. Please install Python 3.11+."
    exit 1
}

# 2. Check UI Build
$uiDistPath = Join-Path $PSScriptRoot "..\ui\dist"
if (-not (Test-Path $uiDistPath)) {
    Write-Host "[*] UI dist not found. Building React Cockpit..." -ForegroundColor Yellow
    Push-Location (Join-Path $PSScriptRoot "..\ui")
    try {
        if (-not (Test-Path "node_modules")) {
            Write-Host "[*] Installing Node dependencies..." -ForegroundColor Yellow
            npm install
        }
        npm run build
        Write-Host "[+] React Cockpit built successfully!" -ForegroundColor Green
    } finally {
        Pop-Location
    }
} else {
    Write-Host "[+] UI distribution found at $uiDistPath" -ForegroundColor Green
}

# 3. Launch Server
$port = if ($env:PORT) { $env:PORT } else { "8080" }
Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  TriagePilot is live and listening on: http://localhost:$port" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop the server." -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""

python -m uvicorn api.main:app --host 0.0.0.0 --port $port
