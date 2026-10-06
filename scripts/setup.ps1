# SPECTRE Setup Script — Windows PowerShell
# Run this once to set up the entire SPECTRE workspace
# Usage: .\scripts\setup.ps1

param(
    [switch]$SkipDocker,
    [switch]$SkipOllama,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
$SPECTRE_DIR = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "  ██████  ██████  ███████  ██████ ████████ ██████  ███████ " -ForegroundColor Cyan
Write-Host " ██      ██   ██ ██      ██         ██    ██   ██ ██      " -ForegroundColor Cyan
Write-Host "  █████  ██████  █████   ██         ██    ██████  █████   " -ForegroundColor Cyan
Write-Host "      ██ ██      ██      ██         ██    ██   ██ ██      " -ForegroundColor Cyan
Write-Host " ██████  ██      ███████  ██████    ██    ██   ██ ███████ " -ForegroundColor Cyan
Write-Host ""
Write-Host " Self-hosted Private AI Workspace v1.0" -ForegroundColor Gray
Write-Host " ─────────────────────────────────────" -ForegroundColor Gray
Write-Host ""

# ── Step 1: Check prerequisites ──────────────────────────────
Write-Host "[1/6] Checking prerequisites..." -ForegroundColor Yellow

# Check Docker
try {
    $dockerVersion = docker --version 2>&1
    Write-Host "  ✓ Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Docker not found. Please install Docker Desktop from https://docker.com" -ForegroundColor Red
    exit 1
}

# Check Docker Compose
try {
    $composeVersion = docker compose version 2>&1
    Write-Host "  ✓ Docker Compose found: $composeVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Docker Compose not found. Update Docker Desktop to get it." -ForegroundColor Red
    exit 1
}

# Check Ollama
try {
    $ollamaVersion = ollama --version 2>&1
    Write-Host "  ✓ Ollama found: $ollamaVersion" -ForegroundColor Green
} catch {
    Write-Host "  ! Ollama not found locally. It will run inside Docker instead." -ForegroundColor Yellow
}

# Check NVIDIA GPU
try {
    $gpuInfo = nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>&1
    Write-Host "  ✓ NVIDIA GPU detected: $gpuInfo" -ForegroundColor Green
} catch {
    Write-Host "  ! No NVIDIA GPU detected. Models will run on CPU (slower)." -ForegroundColor Yellow
    Write-Host "    Edit docker-compose.yml and remove the 'deploy.resources' section." -ForegroundColor Gray
}

# ── Step 2: Environment configuration ────────────────────────
Write-Host ""
Write-Host "[2/6] Setting up environment..." -ForegroundColor Yellow

$envFile = Join-Path $SPECTRE_DIR "infrastructure\.env"
$envExample = Join-Path $SPECTRE_DIR "infrastructure\.env.example"

if (-not (Test-Path $envFile)) {
    Copy-Item $envExample $envFile
    Write-Host "  ✓ Created infrastructure\.env from template" -ForegroundColor Green
    Write-Host ""
    Write-Host "  ⚠ ACTION REQUIRED: Open infrastructure\.env and add your Gemini API key" -ForegroundColor Yellow
    Write-Host "    Get your key from: https://aistudio.google.com/" -ForegroundColor Gray
    Write-Host ""
    $continue = Read-Host "  Press ENTER after adding your API key to continue (or type 'skip' to continue without Gemini)"
} else {
    Write-Host "  ✓ infrastructure\.env already exists" -ForegroundColor Green
}

# Validate API key is set
$envContent = Get-Content $envFile
$apiKeyLine = $envContent | Where-Object { $_ -match "^GEMINI_API_KEY=" }
if ($apiKeyLine -match "your_gemini_api_key_here" -or $apiKeyLine -match "GEMINI_API_KEY=$") {
    Write-Host "  ! Gemini API key not set — cloud models will be unavailable." -ForegroundColor Yellow
    Write-Host "    Local models (ATLAS, SPECTRE, ARCHITECT, ORACLE) will still work." -ForegroundColor Gray
} else {
    Write-Host "  ✓ Gemini API key detected" -ForegroundColor Green
}

# ── Step 3: Start Docker services ────────────────────────────
Write-Host ""
Write-Host "[3/6] Starting SPECTRE services via Docker Compose..." -ForegroundColor Yellow

if (-not $SkipDocker) {
    Set-Location (Join-Path $SPECTRE_DIR "infrastructure")
    docker compose up -d
    Write-Host "  ✓ Services started" -ForegroundColor Green
} else {
    Write-Host "  Skipped (--SkipDocker flag set)" -ForegroundColor Gray
}

# ── Step 4: Wait for Ollama to be ready ──────────────────────
Write-Host ""
Write-Host "[4/6] Waiting for Ollama to initialise..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
do {
    Start-Sleep -Seconds 2
    $attempt++
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "  ✓ Ollama is ready" -ForegroundColor Green
            break
        }
    } catch {}
    Write-Host "  Waiting... ($attempt/$maxAttempts)" -ForegroundColor Gray
} while ($attempt -lt $maxAttempts)

# ── Step 5: Pull models ────────────────────────────────────────
Write-Host ""
Write-Host "[5/6] Pulling local AI models (this may take 20–40 minutes on first run)..." -ForegroundColor Yellow
Write-Host "  Models are downloaded once and cached permanently." -ForegroundColor Gray

if (-not $SkipOllama) {
    $models = @(
        @{ Name = "ATLAS (Qwen2.5 7B)";     Tag = "qwen2.5:7b-instruct-q4_K_M" },
        @{ Name = "SPECTRE (WhiteRabbitNeo)"; Tag = "whiterabbitneo2:8b-q4_K_M" },
        @{ Name = "ARCHITECT (Devstral)";     Tag = "devstral:7b-q4_K_M" },
        @{ Name = "ORACLE (Llama 3.1 8B)";   Tag = "llama3.1:8b-instruct-q4_K_M" },
        @{ Name = "nomic-embed-text (RAG)";   Tag = "nomic-embed-text" }
    )

    foreach ($model in $models) {
        Write-Host "  Pulling $($model.Name)..." -ForegroundColor Cyan
        docker exec spectre-ollama ollama pull $model.Tag
        Write-Host "  ✓ $($model.Name) downloaded" -ForegroundColor Green
    }

    # Apply custom Modelfiles
    Write-Host ""
    Write-Host "  Applying custom SPECTRE personas..." -ForegroundColor Cyan
    $modelfiles = @("atlas", "spectre", "architect", "oracle")
    foreach ($m in $modelfiles) {
        $modelfilePath = Join-Path $SPECTRE_DIR "infrastructure\modelfiles\$m.Modelfile"
        docker exec -i spectre-ollama ollama create $m -f - < $modelfilePath
        Write-Host "  ✓ $m persona applied" -ForegroundColor Green
    }
}

# ── Step 6: Final status ──────────────────────────────────────
Write-Host ""
Write-Host "[6/6] SPECTRE is ready!" -ForegroundColor Green
Write-Host ""
Write-Host " ┌──────────────────────────────────────────────┐" -ForegroundColor Cyan
Write-Host " │  ACCESS YOUR SPECTRE WORKSPACE               │" -ForegroundColor Cyan
Write-Host " │                                              │" -ForegroundColor Cyan
Write-Host " │  Chat UI:      http://localhost:3000         │" -ForegroundColor Cyan
Write-Host " │  LiteLLM API:  http://localhost:4000         │" -ForegroundColor Cyan
Write-Host " │  Ollama API:   http://localhost:11434        │" -ForegroundColor Cyan
Write-Host " │  Search:       http://localhost:8088         │" -ForegroundColor Cyan
Write-Host " │                                              │" -ForegroundColor Cyan
Write-Host " │  Next step: Open http://localhost:3000       │" -ForegroundColor Cyan
Write-Host " │  and create your admin account              │" -ForegroundColor Cyan
Write-Host " └──────────────────────────────────────────────┘" -ForegroundColor Cyan
Write-Host ""
