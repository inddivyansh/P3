@echo off
REM ===========================================================================
REM Defence & Geopolitical Intelligence Platform - Windows Quick Launcher (.bat)
REM ===========================================================================

SET VENV_PYTHON=.venv\Scripts\python.exe
SET VENV_UVICORN=.venv\Scripts\uvicorn.exe
SET VENV_PYTEST=.venv\Scripts\pytest.exe

IF NOT EXIST "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment not found at .venv\Scripts\python.exe
    echo Please create the virtual environment and install requirements first:
    echo   python -m venv .venv
    echo   .\.venv\Scripts\pip.exe install -r requirements.txt
    echo   .\.venv\Scripts\python.exe -m spacy download en_core_web_sm
    exit /b 1
)

IF "%1"=="" GOTO MENU
IF /I "%1"=="pipeline" GOTO PIPELINE
IF /I "%1"=="pipeline-skip-ai" GOTO PIPELINE_SKIP_AI
IF /I "%1"=="p2-only" GOTO P2_ONLY
IF /I "%1"=="nlp-only" GOTO NLP_ONLY
IF /I "%1"=="seed-db" GOTO SEED_DB
IF /I "%1"=="api" GOTO API
IF /I "%1"=="frontend" GOTO FRONTEND
IF /I "%1"=="test" GOTO TEST
IF /I "%1"=="test-p2" GOTO TEST_P2
IF /I "%1"=="spacy" GOTO SPACY
GOTO USAGE

:MENU
cls
echo ===========================================================================
echo   Defence ^& Geopolitical Intelligence Platform - Control Center
echo ===========================================================================
echo   1. Run Full 11-Stage Pipeline (Multi-Source Ingestion + NLP + Gemini AI)
echo   2. Run Pipeline (Skip Gemini AI - Offline Mode)
echo   3. Run Ingestion Only (D-P2-21 Stage 0: GDELT + WorldBank + SQL + RSS)
echo   4. Run NLP Stages Only (Fast Local Processing on Ingested Articles)
echo   5. Seed Strategic Intelligence Reference DB (countries, threats, borders)
echo   6. Start FastAPI Backend Server (Port 8000)
echo   7. Start React Frontend Dashboard (Port 5173)
echo   8. Run Full Automated Test Suite (58 pytest test cases)
echo   9. Run P2 Ingestion Integration Tests (tests/test_p2_integration.py)
echo  10. Download SpaCy Language Model (en_core_web_sm)
echo  11. Exit
echo ===========================================================================
set /p choice="Enter option (1-11): "

IF "%choice%"=="1" GOTO PIPELINE
IF "%choice%"=="2" GOTO PIPELINE_SKIP_AI
IF "%choice%"=="3" GOTO P2_ONLY
IF "%choice%"=="4" GOTO NLP_ONLY
IF "%choice%"=="5" GOTO SEED_DB
IF "%choice%"=="6" GOTO API
IF "%choice%"=="7" GOTO FRONTEND
IF "%choice%"=="8" GOTO TEST
IF "%choice%"=="9" GOTO TEST_P2
IF "%choice%"=="10" GOTO SPACY
IF "%choice%"=="11" exit /b 0
GOTO MENU

:PIPELINE
echo.
echo [INFO] Running full 11-stage intelligence pipeline...
"%VENV_PYTHON%" -m src.pipeline
pause
GOTO MENU

:PIPELINE_SKIP_AI
echo.
echo [INFO] Running pipeline (Skipping Gemini AI - Offline Mode)...
"%VENV_PYTHON%" -m src.pipeline --skip-ai
pause
GOTO MENU

:P2_ONLY
echo.
echo [INFO] Running Stage 0 multi-source ingestion only (GDELT, WorldBank, SQL, RSS)...
"%VENV_PYTHON%" -m src.pipeline --p2-only
pause
GOTO MENU

:NLP_ONLY
echo.
echo [INFO] Running NLP intelligence stages only on existing ingested records...
"%VENV_PYTHON%" -m src.pipeline --nlp-only
pause
GOTO MENU

:SEED_DB
echo.
echo [INFO] Seeding Strategic Intelligence Reference Database...
"%VENV_PYTHON%" scripts/p2_seed_intelligence_db.py
pause
GOTO MENU

:API
echo.
echo [INFO] Starting FastAPI Backend on http://localhost:8000...
echo [INFO] Interactive Swagger Documentation: http://localhost:8000/docs
echo [INFO] Press CTRL+C to stop the server.
"%VENV_PYTHON%" -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
pause
GOTO MENU

:FRONTEND
echo.
echo [INFO] Starting React Frontend Dashboard on http://localhost:5173...
echo [INFO] Press CTRL+C to stop the development server.
cd frontend
call npm.cmd run dev
cd ..
pause
GOTO MENU

:TEST
echo.
echo [INFO] Running full PyTest test suite (58 test cases)...
"%VENV_PYTHON%" -m pytest -v
pause
GOTO MENU

:TEST_P2
echo.
echo [INFO] Running P2 Multi-Source Ingestion Integration Tests...
"%VENV_PYTHON%" -m pytest tests/test_p2_integration.py -v
pause
GOTO MENU

:SPACY
echo.
echo [INFO] Downloading en_core_web_sm spaCy model...
"%VENV_PYTHON%" -m spacy download en_core_web_sm
pause
GOTO MENU

:USAGE
echo.
echo Usage: run_project.bat [COMMAND]
echo.
echo Available Commands:
echo   pipeline         Run full 11-stage pipeline (Stage 0 to Stage 10)
echo   pipeline-skip-ai Run pipeline without Gemini AI API calls
echo   p2-only          Run Stage 0 multi-source ingestion only
echo   nlp-only         Run NLP enrichment stages only
echo   seed-db          Seed Strategic Intelligence SQLite Reference DB
echo   api              Start FastAPI backend server (port 8000)
echo   frontend         Start React frontend dashboard (port 5173)
echo   test             Run complete 58-test pytest suite
echo   test-p2          Run P2 integration test suite
echo   spacy            Download required spaCy language model
echo.
exit /b 1
