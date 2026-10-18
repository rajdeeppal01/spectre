# SPECTRE -- Antigravity Command Center Launcher
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  SPECTRE -- Antigravity Command Center Launcher" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "Starting dashboard server on http://127.0.0.1:5050..." -ForegroundColor Green
python scripts\spectre_dashboard.py --port 5050
