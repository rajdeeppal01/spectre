# pull_models.ps1
# Pulls the 4 base quantized models via Ollama, then builds the
# SPECTRE-tuned variants (ATLAS/SPECTRE/ARCHITECT/ORACLE) from the
# Modelfiles in infrastructure/modelfiles/, plus the embedding model.

$ErrorActionPreference = "Stop"
$ModelfileDir = Join-Path $PSScriptRoot "..\infrastructure\modelfiles"

Write-Host "==> Pulling base models (this will take a while on first run)..." -ForegroundColor Cyan

$baseModels = @(
    "qwen2.5:7b-instruct-q4_K_M",
    "whiterabbitneo2:8b-q4_K_M",
    "devstral:7b-q4_K_M",
    "llama3.1:8b-instruct-q4_K_M",
    "nomic-embed-text"
)

foreach ($model in $baseModels) {
    Write-Host "  Pulling $model ..." -ForegroundColor Yellow
    docker exec spectre-ollama ollama pull $model
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  FAILED to pull $model — check the name exists in the Ollama library." -ForegroundColor Red
        exit 1
    }
}

Write-Host "==> Building tuned custom models from Modelfiles..." -ForegroundColor Cyan

$customModels = @{
    "atlas"     = "Modelfile.atlas"
    "spectre"   = "Modelfile.spectre"
    "architect" = "Modelfile.architect"
    "oracle"    = "Modelfile.oracle"
}

foreach ($name in $customModels.Keys) {
    $mf = $customModels[$name]
    Write-Host "  Building $name from $mf ..." -ForegroundColor Yellow
    docker exec spectre-ollama ollama create $name -f "/modelfiles/$mf"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  FAILED to build $name" -ForegroundColor Red
        exit 1
    }
}

Write-Host "==> Done. Verify with: docker exec spectre-ollama ollama list" -ForegroundColor Green
