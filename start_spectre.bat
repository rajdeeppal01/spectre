@echo off
title SPECTRE Antigravity Command Center
cd /d "%~dp0"
echo ===================================================
echo   SPECTRE -- Antigravity Command Center Launcher
echo ===================================================
echo Checking Ollama container status...
docker compose -f infrastructure\docker-compose.yml up -d ollama >nul 2>&1

echo Starting dashboard server on http://127.0.0.1:5050...
python scripts\spectre_dashboard.py --port 5050
pause
