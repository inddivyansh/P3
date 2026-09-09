<#
.SYNOPSIS
    Defence & Geopolitical Intelligence Platform - PowerShell Control Script (.ps1)

.DESCRIPTION
    Convenient wrapper to run pipeline stages, seed the intelligence database,
    launch the FastAPI backend, start the React dashboard, or execute test suites.

.EXAMPLE
    .\run_project.ps1 -Action pipeline
    .\run_project.ps1 -Action pipeline-skip-ai
    .\run_project.ps1 -Action p2-only
    .\run_project.ps1 -Action nlp-only
    .\run_project.ps1 -Action seed-db
    .\run_project.ps1 -Action api
    .\run_project.ps1 -Action frontend
    .\run_project.ps1 -Action test
    .\run_project.ps1 -Action test-p2
    .\run_project.ps1 -Action spacy
#>

param(
    [ValidateSet("pipeline", "pipeline-skip-ai", "p2-only", "nlp-only", "seed-db", "api", "frontend", "test", "test-p2", "spacy", "menu")]
    [string]$Action = "menu"
)

$VenvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Error "[ERROR] Virtual environment not found at $VenvPython."
    Write-Host "Please set up .venv first:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv"
    Write-Host "  .\.venv\Scripts\pip.exe install -r requirements.txt"
    Write-Host "  .\.venv\Scripts\python.exe -m spacy download en_core_web_sm"
    exit 1
}

function Show-Menu {
    Clear-Host
    Write-Host "===========================================================================" -ForegroundColor Cyan
    Write-Host "  Defence & Geopolitical Intelligence Platform - Control Center" -ForegroundColor Yellow
    Write-Host "===========================================================================" -ForegroundColor Cyan
    Write-Host "  1. Run Full 11-Stage Pipeline (Multi-Source Ingestion + NLP + Gemini AI)"
    Write-Host "  2. Run Pipeline (Skip Gemini AI - Offline Mode)"
    Write-Host "  3. Run Ingestion Only (D-P2-21 Stage 0: GDELT + WorldBank + SQL + RSS)"
    Write-Host "  4. Run NLP Stages Only (Fast Local Processing on Ingested Articles)"
    Write-Host "  5. Seed Strategic Intelligence Reference DB (countries, threats, borders)"
    Write-Host "  6. Start FastAPI Backend Server (Port 8000)"
    Write-Host "  7. Start React Frontend Dashboard (Port 5173)"
    Write-Host "  8. Run Full Automated Test Suite (58 pytest test cases)"
    Write-Host "  9. Run P2 Ingestion Integration Tests (tests/test_p2_integration.py)"
    Write-Host "  10. Download SpaCy Language Model (en_core_web_sm)"
    Write-Host "  11. Exit"
    Write-Host "===========================================================================" -ForegroundColor Cyan
    $choice = Read-Host "Enter option (1-11)"

    switch ($choice) {
        "1"  { Run-Pipeline -Mode "full" }
        "2"  { Run-Pipeline -Mode "skip-ai" }
        "3"  { Run-Pipeline -Mode "p2-only" }
        "4"  { Run-Pipeline -Mode "nlp-only" }
        "5"  { Seed-Database }
        "6"  { Run-Api }
        "7"  { Run-Frontend }
        "8"  { Run-Tests -Target "all" }
        "9"  { Run-Tests -Target "p2" }
        "10" { Download-Spacy }
        "11" { exit 0 }
        default { Show-Menu }
    }
}

function Run-Pipeline([string]$Mode) {
    Write-Host "`n[INFO] Starting data pipeline (Mode: $Mode)..." -ForegroundColor Green
    switch ($Mode) {
        "skip-ai" {
            & $VenvPython -m src.pipeline --skip-ai
        }
        "p2-only" {
            & $VenvPython -m src.pipeline --p2-only
        }
        "nlp-only" {
            & $VenvPython -m src.pipeline --nlp-only
        }
        default {
            & $VenvPython -m src.pipeline
        }
    }
}

function Seed-Database {
    Write-Host "`n[INFO] Seeding Strategic Intelligence Reference Database..." -ForegroundColor Green
    & $VenvPython scripts/p2_seed_intelligence_db.py
}

function Run-Api {
    Write-Host "`n[INFO] Starting FastAPI Backend on http://localhost:8000..." -ForegroundColor Green
    Write-Host "[INFO] Interactive Swagger Docs: http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host "[INFO] Press CTRL+C to terminate the server." -ForegroundColor Yellow
    & $VenvPython -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
}

function Run-Frontend {
    Write-Host "`n[INFO] Starting React Frontend Dashboard on http://localhost:5173..." -ForegroundColor Green
    Write-Host "[INFO] Press CTRL+C to stop Vite dev server." -ForegroundColor Yellow
    Push-Location (Join-Path $PSScriptRoot "frontend")
    try {
        cmd.exe /c "npm.cmd run dev"
    } finally {
        Pop-Location
    }
}

function Run-Tests([string]$Target) {
    if ($Target -eq "p2") {
        Write-Host "`n[INFO] Running P2 Multi-Source Ingestion Integration Tests..." -ForegroundColor Green
        & $VenvPython -m pytest tests/test_p2_integration.py -v
    } else {
        Write-Host "`n[INFO] Executing Full PyTest test suite (58 test cases)..." -ForegroundColor Green
        & $VenvPython -m pytest -v
    }
}

function Download-Spacy {
    Write-Host "`n[INFO] Downloading SpaCy en_core_web_sm model..." -ForegroundColor Green
    & $VenvPython -m spacy download en_core_web_sm
}

switch ($Action) {
    "pipeline"         { Run-Pipeline -Mode "full" }
    "pipeline-skip-ai" { Run-Pipeline -Mode "skip-ai" }
    "p2-only"          { Run-Pipeline -Mode "p2-only" }
    "nlp-only"         { Run-Pipeline -Mode "nlp-only" }
    "seed-db"          { Seed-Database }
    "api"              { Run-Api }
    "frontend"         { Run-Frontend }
    "test"             { Run-Tests -Target "all" }
    "test-p2"          { Run-Tests -Target "p2" }
    "spacy"            { Download-Spacy }
    default            { Show-Menu }
}
