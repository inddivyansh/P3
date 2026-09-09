# 🚀 Running the Defence & Geopolitical Intelligence Platform

A complete operational reference for configuring, running the 11-stage intelligence pipeline, seeding reference databases, launching the FastAPI backend, starting the React dashboard, and executing automated tests.

---

## 📋 Table of Contents
1. [Quick Start (One-Click Runners)](#-quick-start-one-click-runners)
2. [Step-by-Step Manual Setup](#-step-by-step-manual-setup)
3. [Environment Configuration (.env)](#-environment-configuration-env)
4. [Running the 11-Stage Data Pipeline](#-running-the-11-stage-data-pipeline)
5. [Running the Backend API Server](#-running-the-backend-api-server)
6. [Running the Frontend React Dashboard](#-running-the-frontend-react-dashboard)
7. [Running the Automated Test Suite](#-running-the-automated-test-suite)
8. [Running Sub-modules & Individual Stages](#-running-sub-modules--individual-stages)
9. [Windows & PowerShell Troubleshooting](#-windows--powershell-troubleshooting)

---

## ⚡ Quick Start (One-Click Runners)

The platform includes convenient interactive launchers for both Windows Command Prompt and PowerShell:

### Option A: Windows Command Prompt (`run_project.bat`)
Double-click `run_project.bat` or run from cmd:
```cmd
run_project.bat
```
Or run directly by task name:
```cmd
run_project.bat pipeline       # Full 11-stage pipeline with AI
run_project.bat p2-only        # Stage 0 multi-source ingestion only
run_project.bat seed-db        # Seed Strategic Intelligence Reference DB
run_project.bat api            # Launch FastAPI backend on port 8000
run_project.bat frontend       # Launch React dashboard on port 5173
run_project.bat test           # Run 57 automated tests
run_project.bat test-p2        # Run P2 integration tests
```

### Option B: Windows PowerShell (`run_project.ps1`)
Run the interactive menu:
```powershell
.\run_project.ps1
```
Or invoke directly with `-Action`:
```powershell
.\run_project.ps1 -Action pipeline
.\run_project.ps1 -Action p2-only
.\run_project.ps1 -Action seed-db
.\run_project.ps1 -Action api
.\run_project.ps1 -Action frontend
.\run_project.ps1 -Action test
```

---

## 🛠️ Step-by-Step Manual Setup

### Step 1: Virtual Environment Activation
Open your terminal in the repository root directory:

**PowerShell (Windows):**
```powershell
.\.venv\Scripts\Activate.ps1
```
*(If script execution is disabled, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first).*

**Command Prompt (cmd.exe):**
```cmd
.venv\Scripts\activate.bat
```

**Linux / macOS:**
```bash
source .venv/bin/activate
```

---

### Step 2: Dependencies & NLP Model Download
```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

---

### Step 3: Seed the Strategic Intelligence Reference DB
Seed the initial reference tables (countries of interest, threat taxonomies, border flashpoints, defence assets):
```bash
python scripts/p2_seed_intelligence_db.py
```

---

### Step 4: Choose What to Run

| Goal | Command | Endpoint / Output |
| :--- | :--- | :--- |
| **Run Full 11-Stage Pipeline** | `python -m src.pipeline` | `data/database/news_pipeline.db`, `outputs/digests/` |
| **Run Pipeline (Offline / Skip AI)**| `python -m src.pipeline --skip-ai` | Fast run without Gemini API calls |
| **Run Multi-Source Ingestion Only**| `python -m src.pipeline --p2-only` | `data/p2_raw_store/unified_store.sqlite` |
| **Run NLP Stages Only** | `python -m src.pipeline --nlp-only` | Enrich local records without re-ingesting |
| **Start FastAPI Backend Server** | `python -m uvicorn src.api.main:app --reload --port 8000` | [http://localhost:8000/docs](http://localhost:8000/docs) |
| **Start React Frontend Dashboard** | `cd frontend && npm.cmd run dev` | [http://localhost:5173](http://localhost:5173) |
| **Run Automated Test Suite** | `pytest -v` | **58 test cases** passing |

---

## 🔑 Environment Configuration (`.env`)

Create or update `.env` in the repository root:

```env
# Google Gemini API Key (Required for AI Summaries, Threat Analysis, & RAG Chat)
GEMINI_API_KEY=your_gemini_api_key_here

# SQLite Database Path (Defaults to data/database/news_pipeline.db)
DATABASE_URL=sqlite:///data/database/news_pipeline.db

# Ingestion Logging Level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

> **Tip:** If you do not have a Gemini API key yet, the pipeline can run completely offline with `--skip-ai`. All ingestion, parsing, cleaning, semantic deduplication, BART classification, and NER will operate normally.

---

## 🔄 Running the 11-Stage Data Pipeline

The platform orchestrates 11 sequential, modular stages:

```
Stage 0: D-P2-21 Multi-Source Ingestion (GDELT CSV + WorldBank REST + SQL DB + RSS JSON)
   ↓
Stage 1: Feed Ingestion (Combined RSS feeds + Stage 0 records)
   ↓
Stage 2: Full-Text Article Extraction (trafilatura)
   ↓
Stage 3: Text Cleaning & Normalization (regex, boilerplate stripping)
   ↓
Stage 4: Semantic Deduplication (sentence-transformers / MiniLM cosine clustering)
   ↓
Stage 5: Multi-label Taxonomy Classification (BART Zero-Shot)
   ↓
Stage 6: NER & Location Intelligence (spaCy en_core_web_sm + Geo/Military Gazetteers)
   ↓
Stage 7: AI Executive Summarization (Google Gemini / TextRank fallback)
   ↓
Stage 8: Threat & Strategic Impact Assessment (0.0 to 1.0 Threat Scoring)
   ↓
Stage 9: Sentiment & Geopolitical Stance Analysis (BART)
   ↓
Stage 10: Relational Storage & ChromaDB Vector Indexing + Digest Generation
```

### Pipeline CLI Execution Flags:

#### 1. Full 11-Stage Pipeline (Recommended):
```bash
python -m src.pipeline
```

#### 2. Offline / Local-Only Mode (Skips external Gemini API quota):
```bash
python -m src.pipeline --skip-ai
```

#### 3. Ingestion Only (D-P2-21 Stage 0):
```bash
python -m src.pipeline --p2-only
```
*Pulls GDELT events, WorldBank economic data, SQL reference tables, and defence feeds into `data/p2_raw_store/unified_store.sqlite` and stops.*

#### 4. Filter Specific Ingestion Source:
```bash
python -m src.pipeline --p2-source gdelt        # Ingest GDELT CSV events only
python -m src.pipeline --p2-source worldbank    # Ingest World Bank indicators only
python -m src.pipeline --p2-source rss          # Ingest curated defence feeds only
python -m src.pipeline --p2-source sql          # Ingest Strategic Intel DB only
```

#### 5. Fast NLP-Only Mode:
```bash
python -m src.pipeline --nlp-only
```
*Processes previously ingested and deduplicated articles through classification, NER, and location extraction without re-fetching feeds.*

#### 6. Resume Pipeline from Specific Stage:
```bash
python -m src.pipeline --from-stage 6           # Start directly from NER & Location stage
```

#### 7. Custom Declarative Sources File:
```bash
python -m src.pipeline --sources-config config/sources.yaml
```

---

## 🌐 Running the Backend API Server

The backend is built with **FastAPI** and **Uvicorn**, providing async REST endpoints and OpenAPI documentation.

### Start the API server:
```bash
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Documentation & Health Endpoints:
- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc UI**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### Primary Endpoint Catalog:

| Category | Endpoint | Method | Description |
| :--- | :--- | :--- | :--- |
| **System** | `/health` | GET | Operational health check & uptime status |
| **Intelligence** | `/intelligence/kpis` | GET | High-level intelligence metrics, threat distribution, source stats |
| **Intelligence** | `/intelligence/articles` | GET | Filtered article feed (by threat level, category, country, source) |
| **Intelligence** | `/intelligence/threats` | GET | High & Critical threat articles with analytical disclaimers |
| **Intelligence** | `/intelligence/monitoring` | GET | Army monitoring queue sorted by strategic priority |
| **Intelligence** | `/intelligence/review` | GET | Articles flagged for human analyst verification |
| **Intelligence** | `/intelligence/locations` | GET | Geographic hotspots, disputed border alerts, state breakdown |
| **Intelligence** | `/intelligence/entities` | GET | Military entities, weapon systems, naval vessels, commanders |
| **Intelligence** | `/intelligence/map` | GET | Coordinates and threat severities for map visualization |
| **Intelligence** | `/intelligence/trends` | GET | Temporal topic volume trends and category distribution |
| **AI Briefs** | `/intelligence/brief/daily` | GET | AI-generated executive intelligence briefing |
| **AI Briefs** | `/intelligence/brief/situation/{topic}` | GET | Focused situation brief for a given defence topic |
| **AI Briefs** | `/intelligence/brief/country/{pair}` | GET | Bilateral strategic assessment (e.g. `India-China`) |
| **Conversational** | `/chat/query` | POST | RAG conversational Q&A with verified source citations |
| **D-P2-21** | `/api/ingestion/config` | GET | Declarative multi-source ingestion configuration & registry |
| **D-P2-21** | `/api/ingestion/sources` | GET | Connector status & record counts in unified raw store |
| **D-P2-21** | `/api/ingestion/dlq` | GET | Dead Letter Queue inspection (quarantined records) |

---

## 💻 Running the Frontend React Dashboard

The frontend is a modern **React 19** application powered by **Vite**, **Lucide Icons**, and **Recharts**.

### 1. Navigate to frontend directory:
```bash
cd frontend
```

### 2. Install dependencies (First run only):
On Windows PowerShell:
```powershell
npm.cmd install
```
*(Or `npm install` in bash).*

### 3. Start development server:
```powershell
npm.cmd run dev
```

### 4. Open in browser:
Navigate to: **[http://localhost:5173](http://localhost:5173)**

### 📱 11 Specialized Analyst Views:
1. **Executive Overview** (`/`): High-level KPI metrics, threat distributions, priority alerts, and recent activity.
2. **Live Feed** (`/live-feed`): Real-time multi-source intelligence feed with multi-criteria filtering.
3. **Priority Threats** (`/threats`): Critical threat matrix, army monitoring alerts, and human review queue.
4. **Situations** (`/situations`): Situation briefs and thematic defence dossiers.
5. **Location Intelligence** (`/locations`): Geographic distribution of defence events, border tracking, and state hotspots.
6. **Entity Intelligence** (`/entities`): Weapon systems, military platforms, sovereign organizations, and key decision-makers.
7. **Trends & Analytics** (`/trends`): Category volume trajectories, sentiment curves, and temporal trends.
8. **Strategic Map** (`/map`): Interactive geopolitical hotspot map with severity markers.
9. **AI Analyst Workspace** (`/analyst`): Conversational RAG assistant with grounded citations and context exploration.
10. **Data Sources** (`/sources`): D-P2-21 connector health, ingestion telemetry, and Dead Letter Queue inspections.
11. **Reports & Digests** (`/reports`): Daily intelligence bulletins and exportable executive digests.

---

## 🧪 Running the Automated Test Suite

The test suite contains **58 test cases** verifying all components:

### Run all tests:
```bash
pytest -v
```

### Run specific test suites:
```bash
# 1. FastAPI endpoint tests (10 tests)
pytest tests/test_api_endpoints.py -v

# 2. NLP & intelligence extraction tests (9 tests)
pytest tests/test_intelligence.py -v

# 3. D-P2-21 Multi-Source Ingestion integration tests (38 tests)
pytest tests/test_p2_integration.py -v

# 4. Smoke test
pytest tests/test_smoke.py -v
```

### Run tests with code coverage analysis:
```bash
pytest --cov=src --cov-report=term-missing
```

---

## 🛠️ Running Sub-modules & Individual Stages

You can test individual sub-modules directly in Python:

```bash
# 1. Multi-Source Ingestion Engine (P2 Stage 0)
python -c "from src.ingestion.feed_reader import run_p2_ingestion; run_p2_ingestion()"

# 2. Traditional RSS Feed Ingestion (Stage 1)
python -c "from src.ingestion.feed_reader import run_ingestion; run_ingestion()"

# 3. Full-Text Article Extraction (Stage 2)
python -c "from src.ingestion.article_fetcher import run_article_extraction; run_article_extraction()"

# 4. Text Sanitization & Cleaning (Stage 3)
python -c "from src.processing.cleaner import run_cleaning; run_cleaning()"

# 5. Semantic Deduplication (Stage 4)
python -c "from src.processing.deduplicator import run_deduplication; run_deduplication()"

# 6. Standalone Daily Digest Generation (Stage 10b)
python -c "from src.digest.generator import run_digest_generation; run_digest_generation()"

# 7. Test RAG Chat Query Engine
python scripts/test_chat.py
```

---

## 🔧 Windows & PowerShell Troubleshooting

### 1. `Execution of scripts is disabled on this system` (PowerShell)
**Cause**: Default Windows PowerShell script execution policy.  
**Fix**: Run this in PowerShell before activating `.venv`:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 2. `npm.ps1 cannot be loaded`
**Cause**: PowerShell restricts executing npm's `.ps1` wrapper.  
**Fix**: Call `npm.cmd` explicitly:
```powershell
npm.cmd run dev
```
*(The provided `run_project.bat` and `run_project.ps1` already handle this automatically).*

### 3. `[WinError 32] The process cannot access the file`
**Cause**: Background Python processes locking SQLite database or `.venv` files.  
**Fix**: Terminate lingering Python instances in PowerShell:
```powershell
Get-Process python, py -ErrorAction SilentlyContinue | Stop-Process -Force
```

### 4. Missing SpaCy Model (`OSError: [E050] Can't find model 'en_core_web_sm'`)
**Fix**: Download the language model into your virtual environment:
```bash
python -m spacy download en_core_web_sm
```

---

<div align="center">
  <b>Defence & Geopolitical Intelligence Platform</b><br/>
  <i>Operational Guide & Reference</i>
</div>
