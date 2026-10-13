# Groundwater Intelligence & Early Warning Platform

A data-driven groundwater intelligence, monitoring, and predictive analysis platform for India and Maharashtra. The platform brings together data normalization, quality auditing, temporal and spatial analytics, deterministic condition classification, statistical anomaly alerts, multi-horizon machine learning forecasting, and an interactive geospatial dashboard.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-19-blue?logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue?logo=typescript&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-Analytical_Engine-FFF000?logo=duckdb&logoColor=black)
![PyTorch](https://img.shields.io/badge/PyTorch-2.x-EE4C2C?logo=pytorch&logoColor=white)
![LightGBM](https://img.shields.io/badge/LightGBM-4.x-brightgreen)
![MapLibre](https://img.shields.io/badge/MapLibre_GL-6.x-blue?logo=maplibre&logoColor=white)
![ECharts](https://img.shields.io/badge/Apache_ECharts-6.x-red?logo=apacheecharts&logoColor=white)

An analytical data-access and forecasting platform providing reproducible hydrological intelligence without reliance on opaque generative shortcuts.

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Core Objectives](#core-objectives)
- [System Architecture](#system-architecture)
- [End-to-End Data Flow](#end-to-end-data-flow)
- [Software Architecture](#software-architecture)
- [Frontend Architecture & Interactive Modules](#frontend-architecture--interactive-modules)
  - [1. Overview Command Center](#1-overview-command-center)
  - [2. Geospatial Map Explorer](#2-geospatial-map-explorer)
  - [3. Predictive Analytics Suite](#3-predictive-analytics-suite)
  - [4. Advanced Forecast Module](#4-advanced-forecast-module)
  - [5. Methodology & Model Deep-Dive](#5-methodology--model-deep-dive)
- [Dataset Architecture (India vs Maharashtra)](#dataset-architecture-india-vs-maharashtra)
- [Intelligence & Modeling Engines](#intelligence--modeling-engines)
  - [1. Data Normalization & Quality Control](#1-data-normalization--quality-control)
  - [2. Deterministic Condition Classification](#2-deterministic-condition-classification)
  - [3. Statistical Anomaly & Alert Engine](#3-statistical-anomaly--alert-engine)
  - [4. Multi-Model Predictive Forecasting Suite](#4-multi-model-predictive-forecasting-suite)
  - [5. Hydrogeological Diagnostics & Sparse-Data Calibrated Fallback](#5-hydrogeological-diagnostics--sparse-data-calibrated-fallback)
  - [6. Drought, Flood, and Stress Intelligence](#6-drought-flood-and-stress-intelligence)
- [Technology Stack](#technology-stack)
- [Repository Structure](#repository-structure)
- [Step-by-Step Setup Guide (For Cloners)](#step-by-step-setup-guide-for-cloners)
  - [1. System Prerequisites](#1-system-prerequisites)
  - [2. Clone the Repository](#2-clone-the-repository)
  - [3. Backend Setup (Python & FastAPI)](#3-backend-setup-python--fastapi)
  - [4. Data Initialization (Rebuilding Normalized Parquet)](#4-data-initialization-rebuilding-normalized-parquet)
  - [5. Frontend Setup (React & Vite)](#5-frontend-setup-react--vite)
  - [6. Running the Platform](#6-running-the-platform)
  - [7. Automated Testing Suite](#7-automated-testing-suite)
  - [8. Model Training Pipelines](#8-model-training-pipelines)
- [API Reference](#api-reference)
  - [System Endpoints](#system-endpoints)
  - [Monitoring Stations & Telemetry](#monitoring-stations--telemetry)
  - [Temporal & Spatial Analytics](#temporal--spatial-analytics)
  - [Predictive Forecasting & Benchmarks](#predictive-forecasting--benchmarks)
- [Scientific Limitations](#scientific-limitations)
- [Authors & License](#authors--license)

## Overview

The Groundwater Intelligence & Early Warning Platform is an analytical platform designed to monitor, evaluate, and forecast groundwater table dynamics across Indian monitoring wells. The platform ingests heterogeneous observations, standardizes schemas, handles outliers, builds historical seasonal baselines, and runs parallel statistical and machine learning models to forecast future water level trajectories under varying monsoon recharge scenarios.

## Problem Statement

Groundwater modeling faces several practical challenges:
- **Heterogeneous Observations**: Data collection frequencies differ widely between historical manual records and modern telemetry sensors.
- **Diverging Semantic Contexts**: Long-term national records are periodic and sparse, whereas Maharashtra Digital Water Level Recorder (DWLR) stations provide high-frequency continuous telemetry.
- **Sensor Spikes and Missing Datums**: Sensor malfunctions, irregular battery drops, and unknown surface datums complicate standard time-series routines.
- **Deceptive Metrics in Hydrology**: Naive global accuracy or R² often rewards flat persistence predictions because water levels move slowly week-to-week, failing to provide meaningful drought or flood advance warnings.
- **Fragmented Workflows**: Decision makers frequently lack a single platform that ties together temporal trends, spatial maps, multi-model forward horizons, and explicit data diagnostics.

Note: This system provides academic and engineering decision-support intelligence. It does not replace official statutory publications issued by the Central Ground Water Board (CGWB) or State Ground Water Surveys and Development Agencies (GSDA).

## Core Objectives

1. Maintain an immutable raw data pipeline that preserves source records.
2. Standardize heterogeneous telemetry and periodic well data into normalized Parquet files.
3. Compute seasonal percentiles and multi-year empirical baselines.
4. Detect statistical deviations and generate automated monitoring alerts.
5. Provide continuous forward trajectories using Fourier seasonal harmonics, deep recurrent sequences, and autoregressive models.
6. Provide interactive climate scenario toggles (Normal, Deficit, and Excess Monsoon recharge).
7. Transparently diagnose sparse observations and compute calibrated harmonic fallbacks.
8. Expose all analytical models through a high-performance, asynchronous FastAPI backend backed by in-memory DuckDB queries.
9. Deliver an interactive dashboard with MapLibre GL geospatial clustering, ECharts continuous trajectory visualizations, and drawer inspection workflows.

## System Architecture

```mermaid
flowchart TB
    RAW_DATA[Raw Groundwater & Weather Observations] --> INGESTION[Data Ingestion & Normalization]
    INGESTION --> QUALITY[Quality Control & Physical Plausibility Filters]
    QUALITY --> PROCESSED[Canonical Processed Parquet Tables]
    PROCESSED --> FEATURES[Feature Engineering & Temporal Baselines]
    
    FEATURES --> AE_SUB
    
    subgraph AE_SUB [Analytical & Intelligence Engines]
        direction TB
        TEMP[Temporal & Seasonal Analytics]
        SPATIAL[Spatial Analytics & Coordinate Clustering]
        BASE[Historical Empirical Baselines]
        COND[Percentile Condition Classification]
        ALERT[Statistical Anomaly & Alert Engine]
        HARM[Fourier Seasonal Harmonic Forecasting]
        LSTM[Deep Recurrent Sequence LSTM]
        AR[Autoregressive Horizon Chained Forecaster]
        SCENARIO[Climate & Monsoon Recharge Scenarios]
        PERSIST[Baseline Persistence Reference]
        DROUGHT[Drought Deficit Intelligence]
        FLOOD[Flood Potential Multi-Signal Classifier]
        STRESS[Aquifer Stress & Chronic Drawdown Analytics]
    end
    
    AE_SUB --> ARTIFACTS[Persisted Parquet Artifacts & Model Cache]
    ARTIFACTS --> DUCKDB[DuckDB High-Performance Query Layer]
    DUCKDB --> FASTAPI[FastAPI Asynchronous REST Endpoints]
    FASTAPI --> REACT[React 19 + TypeScript Analytical Dashboard]
    
    REACT --> MAP[MapLibre GL Interactive Geospatial Map]
    REACT --> CHARTS[Apache ECharts Predictive Trajectories & Hydrographs]
```

## End-to-End Data Flow

```mermaid
flowchart LR
    Obs[Raw Observations] --> Norm[Schema Normalization]
    Norm --> Sites[Candidate-Site ID & Spatial Clustering]
    Sites --> QA[Quality Filtering & Outlier Removal]
    QA --> Eng[Feature Generation & Lag Variables]
    Eng --> Intel[Predictive & Anomaly Engines]
    Intel --> Parquet[Normalized Parquet Tables]
    Parquet --> DuckDB[DuckDB In-Memory Query Layer]
    DuckDB --> API[FastAPI Asynchronous Endpoints]
    API --> UI[React 19 Interactive Dashboard]
```

## Software Architecture

```mermaid
flowchart TD
    subgraph Client ["Client Application (React 19 + TypeScript)"]
        UI_Dash[Overview Dashboard & Alert Radar]
        UI_Map[Geospatial MapLibre GL Explorer]
        UI_Pred[Predictive Analytics Suite]
        UI_Adv[Advanced Forecast Statewide Module]
        UI_Meth[Methodology & Model Deep-Dive]
        UI_Site[Station Drawer & ECharts Hydrographs]
        UI_Diag[Data Diagnostics & Sparsity Audit Popover]
    end

    subgraph Service ["API Service Layer (FastAPI Asynchronous)"]
        API_Sites["/candidate-sites Endpoints"]
        API_Telem["/telemetry Endpoints"]
        API_Alerts["/alerts Endpoints"]
        API_Cond["/condition Endpoints"]
        API_Anly["/analytics & /timeline Endpoints"]
        API_Fore["/advanced-forecast Multi-Model Suite"]
        API_Bench["/advanced-forecast/models Benchmark"]
        API_Chain["/chained-forecast Endpoints"]
    end

    subgraph DataAccess ["Data Access Layer (DuckDB In-Memory Engine)"]
        DAL_Engine[DuckDB SQL Interface]
        Cache_Site[Site Metadata & Coordinate Index]
        Cache_Telem[Historical Telemetry Cache]
        Cache_Alert[Anomaly Alert Record Cache]
    end

    subgraph Pipeline ["Analytical & Predictive Processing Pipeline"]
        PIPE_Norm[scripts/rebuild_processed_from_alerts.py]
        PIPE_Harm[src/forecasting/seasonal_harmonic.py]
        PIPE_LSTM[src/forecasting/lstm_forecaster.py]
        PIPE_Chain[src/forecasting/chain.py]
        PIPE_Alert[src/alerting/causal_alert_engine.py]
        PIPE_Feat[src/features/advanced_analytics.py]
    end

    subgraph Storage ["Persisted Storage Layer (Apache Parquet)"]
        DS_Raw["data/raw/ (Raw Source Telemetry)"]
        DS_Norm["data/processed/ (Normalized Parquet)"]
        DS_Alert["data/alerts/ (Precomputed Alert Artifacts)"]
        DS_Cond["data/conditions/ (Empirical Baselines)"]
        DS_Model["models/advanced_forecast/ (Trained Weights)"]
    end

    UI_Dash --> API_Sites
    UI_Dash --> API_Alerts
    UI_Map --> API_Sites
    UI_Map --> UI_Site
    UI_Pred --> API_Fore
    UI_Pred --> UI_Diag
    UI_Adv --> API_Fore
    UI_Adv --> API_Bench
    UI_Site --> API_Telem
    UI_Site --> API_Alerts
    UI_Site --> API_Cond
    UI_Site --> API_Anly

    API_Sites --> Cache_Site
    API_Telem --> Cache_Telem
    API_Alerts --> Cache_Alert
    API_Cond --> DAL_Engine
    API_Anly --> DAL_Engine
    API_Fore --> PIPE_Harm
    API_Fore --> PIPE_LSTM
    API_Fore --> PIPE_Chain
    API_Chain --> PIPE_Chain

    DAL_Engine --> DS_Norm
    DAL_Engine --> DS_Alert
    DAL_Engine --> DS_Cond
    PIPE_Harm --> DS_Model
    PIPE_LSTM --> DS_Model
    PIPE_Norm --> DS_Raw
    PIPE_Norm --> DS_Norm
```

## Frontend Architecture & Interactive Modules

The user interface is built with React 19, TypeScript, Tailwind CSS, MapLibre GL, and Apache ECharts, organized across five primary workflows:

### 1. Overview Command Center
- **State & Regional Aggregations**: Displays top-level indicators including total active stations, historical observation volume, critical alerts, and percentile health distribution.
- **Alert Radar & Rapid Response**: Categorizes anomalies by severity (`CRITICAL_STATISTICAL_DEVIATION`, `WARNING`, `WATCH`).
- **Interactive Station Handoff**: Selecting any critical alert record immediately transitions the view to the Geospatial Map tab, filters by district, and opens the station drawer inspector. Deep-linking via query parameters (`?tab=map&site=SITE_ID&district=DISTRICT`) enables direct external sharing.

### 2. Geospatial Map Explorer
- **Vector-Rendered Map**: Hardware-accelerated rendering powered by MapLibre GL JS with marker clustering and zoom transitions.
- **Filtering & Search**: Dynamic filtering by dataset region (India vs Maharashtra), administrative district, and free-text station search.
- **Slide-Out Station Drawer**: Detailed site inspection containing historical water-level hydrograph, current percentile classification badge, anomaly residual movement logs, and geographic coordinates.

### 3. Predictive Analytics Suite
- **Continuous Multi-Model Hydrograph**: Renders parallel model projections on a single unified timeline comparing Seasonal Harmonic, Deep LSTM, Autoregressive Horizon, and Baseline Persistence.
- **Monsoon Scenario Simulation**: Toggles between Baseline (1.0x recharge), Deficit (-20% recharge stress), and Excess (+20% surplus recharge) scenarios to project aquifer resilience.
- **Multi-Model Interpretation Cards**: Side-by-side analytical cards explaining the physical reasoning, seasonal turning points, and confidence bounds for each active model.
- **Hydrogeological Diagnostics Popover**: Interactive sparsity audit displaying total record counts, observation spans, and explanation of calibrated regional harmonic fallbacks when historical telemetry is limited.

### 4. Advanced Forecast Module
- **Statewide Predictive Mapping**: Aggregates predicted water table shifts across all Maharashtra monitoring stations.
- **Multi-Station Comparison**: Side-by-side hydrographs and drawdown rates across contrasting agro-climatic zones.
- **Empirical Model Benchmarks**: Displays formal test-set validation metrics, including Directional Trend Precision, Mean Absolute Error (MAE in meters), and 80% Confidence Interval empirical coverage.

### 5. Methodology & Model Deep-Dive
- **Mathematical Formulations**: Comprehensive documentation of Fourier harmonic equations, Huber loss regression parameters, LSTM recurrence units, and DBSCAN spatial parameters.
- **Hydrological Alignment**: Explanation of CGWB and GSDA classification criteria and percentile computation methodologies.
- **Limitations & Boundaries**: Transparent declaration of system capabilities, data sparsity challenges, and decision-support operational context.

## Dataset Architecture (India vs Maharashtra)

The platform isolates national periodic observations from state telemetry to maintain semantic accuracy:

| Dimension | India Dataset | Maharashtra Dataset |
|---|---|---|
| **Observation Cadence** | Historical, periodic (seasonal / annual) | High-frequency telemetry (DWLR) |
| **Primary Metric** | Relative depth / head to local datum | Depth to water table in meters below ground level (m bgl) |
| **Observation Count** | Multi-decade historical samples | 1,000+ telemetry stations with daily/weekly records |
| **Forecasting Scope** | Historical condition & long-term trend | Multi-model continuous forward trajectories (up to 2 years) |
| **Primary Analytical Role** | Regional baselines & historical stress | Real-time alerts, seasonal turnaround, and predictive modeling |

## Intelligence & Modeling Engines

### 1. Data Normalization & Quality Control
- Raw readings are validated against physical plausibility filters (extreme sensor spikes where delta exceeds 25 meters are isolated).
- Observation timestamps are parsed to Indian Standard Time (IST) ISO-8601 strings.
- Non-destructive processing ensures source records remain untouched.

### 2. Deterministic Condition Classification
- Water levels are ranked against site-specific historical seasonal percentiles:
  - `EXTREMELY_LOW` (P < 10th percentile)
  - `LOW` (10th <= P < 25th percentile)
  - `NORMAL_RANGE` (25th <= P <= 75th percentile)
  - `HIGH` (75th < P <= 90th percentile)
  - `EXTREMELY_HIGH` (P > 90th percentile)
  - `INSUFFICIENT_HISTORY` (fewer than 15 baseline samples)

### 3. Statistical Anomaly & Alert Engine
- Evaluates recent observation residual movements against rolling historical variance:
  - `NORMAL`: Within expected seasonal variance envelope.
  - `WATCH`: 1 to 2 standard deviations from baseline.
  - `WARNING`: Exceeding 2 standard deviations.
  - `CRITICAL_STATISTICAL_DEVIATION`: Severe statistical outlier requiring immediate field inspection.

### 4. Multi-Model Predictive Forecasting Suite
The platform implements parallel forecasting engines running on verified telemetry:
- **Seasonal Harmonic Model**: Uses annual, semi-annual, and quarterly Fourier decomposition ($\sin/\cos$ terms) with Huber loss regression ($\delta=1.35$) to project seasonal drawdown and monsoon turnaround trajectories.
- **Deep Recurrent Sequence Model**: A 2-layer LSTM network with LayerNorm and spatial conditioning, trained on 30-day sliding observation windows.
- **Autoregressive Horizon Model**: A multi-step chained recursive model rolled forward across user-selected horizons.
- **Baseline Persistence Reference**: The non-parametric benchmark assuming future levels equal the latest validated measurement.
- **Monsoon Climate Scenarios**: Simulates impacts of Normal ($1.0\times$ baseline recharge), Deficit ($-20\%$ drought stress), and Excess ($+20\%$ surplus infiltration).
- **Evaluation Standards**: Evaluated on Directional Trend Precision, Physical Mean Absolute Error (MAE in meters), and 80% Confidence Interval empirical coverage.

### 5. Hydrogeological Diagnostics & Sparse-Data Calibrated Fallback
- Replaces generic missing data errors with a detailed diagnostic audit covering sample count, observation span, and threshold criteria.
- Stations with sparse records automatically engage regional seasonal Fourier harmonics with widened empirical uncertainty bounds ($\pm 1.8\text{ m}$) instead of throwing errors.

### 6. Drought, Flood, and Stress Intelligence
- **Drought Intelligence**: Evaluates consecutive deficit quarters and spatial coverage.
- **Flood Potential**: Retrospective multi-signal classification combining sharp hydraulic head rises with localized rainfall indicators.
- **Aquifer Stress**: Identifies multi-year chronic depletion trends independent of single-season monsoon fluctuations.

## Technology Stack

- **Backend Language**: Python 3.10+
- **API Framework**: FastAPI 0.115 with Uvicorn
- **Analytical Storage**: DuckDB, PyArrow, Apache Parquet
- **Machine Learning**: LightGBM, PyTorch, Scikit-learn, NumPy, Pandas, Scipy
- **Frontend Framework**: React 19, TypeScript 5.x, Vite
- **Mapping & Geospatial**: MapLibre GL JS, React-Map-GL
- **Data Visualization**: Apache ECharts (`echarts-for-react`)
- **Icons & Styling**: Tailwind CSS, Lucide React

## Repository Structure

```text
groundwater/
├── data/                       # Local datasets (Parquet binaries excluded from git)
│   ├── alerts/                 # Precomputed causal alert artifacts
│   ├── conditions/             # Baseline condition Parquet files
│   ├── processed/              # Normalized observation records
│   └── raw/                    # Raw source telemetry and survey files
├── docs/                       # Technical methodologies and documentation
├── frontend/                   # React + TypeScript single-page application
│   ├── src/
│   │   ├── components/         # Dashboard tabs, map views, charts, and drawer panels
│   │   ├── services/           # Typed API client functions
│   │   ├── utils/              # Color schemes, formatters, and alert configurations
│   │   ├── App.tsx             # Root dashboard controller and routing
│   │   └── index.css           # Design tokens, variables, and typography
│   ├── package.json
│   └── vite.config.ts
├── models/                     # Trained forecasting weights and metadata JSONs
│   ├── advanced_forecast/      # Harmonic weights and LSTM checkpoints
│   └── groundwater_forecast/   # LightGBM chained horizon models
├── scripts/                    # Training and data processing utilities
│   ├── rebuild_processed_from_alerts.py
│   ├── train_forecast_model.py
│   ├── train_lstm_forecast.py
│   └── train_seasonal_harmonic.py
├── src/                        # Core Python backend package
│   ├── alerting/               # Statistical anomaly detection
│   ├── api/                    # FastAPI routes and DuckDB Data Access Layer
│   │   ├── routes/             # Candidate sites, forecasts, analytics
│   │   ├── dal.py              # In-memory DuckDB query layer
│   │   └── main.py             # FastAPI entry point
│   ├── data/                   # Data loaders and schema normalizers
│   ├── features/               # Spatial DBSCAN and temporal engineering
│   └── forecasting/            # Chained step forecaster and harmonic suites
├── tests/                      # Pytest suite
│   ├── api/                    # API integration tests
│   └── *.py                    # Pipeline, features, and model tests
├── pytest.ini                  # Pytest configuration
├── requirements.txt            # Python dependencies
└── README.md
```

## Step-by-Step Setup Guide (For Cloners)

Follow these exact steps to clone, configure, and launch the platform locally.

### 1. System Prerequisites
Ensure your machine has the following tools installed:
- **Git**: `git --version`
- **Python**: Version 3.10 or higher (`python3 --version` or `python --version`)
- **Node.js**: Version 18 or higher (`node --version`) and npm (`npm --version`)

If working on Windows, Windows Subsystem for Linux (WSL), PowerShell, or Git Bash can be used.

### 2. Clone the Repository
```bash
git clone https://github.com/SSujal-Pawarr/groundwater.git
cd groundwater
```

### 3. Backend Setup (Python & FastAPI)

Create and activate a clean Python virtual environment:

On Linux / macOS / WSL:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the required Python libraries:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Data Initialization (Rebuilding Normalized Parquet)
Because large raw datasets and normalized Parquet files are excluded from Git to prevent repository bloat, rebuild the normalized analytical tables from the included alert artifacts:

```bash
python scripts/rebuild_processed_from_alerts.py
```

This script will verify your directories and populate `data/processed/maharashtra/maharashtra_normalized.parquet` and related reference tables without modifying any existing files.

### 5. Frontend Setup (React & Vite)

Open a new terminal window or tab, navigate to the `frontend` folder, and install dependencies:

```bash
cd frontend
npm install
```

### 6. Running the Platform

#### Terminal 1: Launch Backend API
In the project root with your virtual environment active:
```bash
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```
The API server will start on `http://127.0.0.1:8000`. You can inspect the interactive OpenAPI documentation by opening `http://127.0.0.1:8000/docs` in your browser.

#### Terminal 2: Launch Frontend Development Server
In the `frontend` directory:
```bash
npm run dev
```
The Vite development server will start on `http://localhost:5173`.

Open your browser to **`http://localhost:5173`** to access the dashboard.

### 7. Automated Testing Suite

To run the complete test suite and verify system integrity:

#### Run Backend Unit and Integration Tests:
```bash
pytest
```

To run API-specific tests with verbose output:
```bash
pytest tests/api/ -v
```

#### Run Frontend Component Tests:
In the `frontend/` directory:
```bash
npm test
```

To run frontend code quality linting:
```bash
npm run lint
```

### 8. Model Training Pipelines

Pre-trained model artifacts are included in the repository. If you wish to retrain or update the machine learning models on new observations:

- **Train Seasonal Harmonic Models**:
  ```bash
  python scripts/train_seasonal_harmonic.py
  ```
- **Train Deep Learning LSTM Network**:
  ```bash
  python scripts/train_lstm_forecast.py
  ```
- **Train Autoregressive Chained Horizon Models**:
  ```bash
  python scripts/train_forecast_model.py
  ```

## API Reference

The backend exposes read-only analytical endpoints over HTTP:

### System Endpoints
| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check confirming database connectivity, active caches, and DuckDB initialization. |
| `/docs` | GET | Interactive Swagger UI API documentation and parameter schemas. |

### Monitoring Stations & Telemetry
| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/{region}/candidate-sites` | GET | List monitoring stations with coordinates, condition states, and anomaly alert levels. Supports bounding-box and district filtering. |
| `/api/v1/{region}/candidate-sites/{id}/telemetry` | GET | Chronological historical telemetry observations for a specific station. |
| `/api/v1/{region}/candidate-sites/{id}/alerts` | GET | Anomaly alert history and standardized residual deviation scores. |
| `/api/v1/{region}/candidate-sites/{id}/condition` | GET | Latest percentile condition classification and historical sample count. |
| `/api/v1/maharashtra/candidate-sites/{id}/forecast` | GET | Baseline persistence forecast record for the station. |

### Temporal & Spatial Analytics
| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/{region}/candidate-sites/{id}/analytics` | GET | Station-level summary statistics, seasonal drawdown profile, and cross-intelligence synthesis. |
| `/api/v1/{region}/candidate-sites/{id}/timeline` | GET | Unified chronological timeline with water levels, daily rate of change, condition states, and alerts. |
| `/api/v1/{region}/candidate-sites/{id}/percentile-trajectory` | GET | Empirical historical percentile movements across observation cycles. |
| `/api/v1/{region}/districts/{district}/analytics` | GET | District-wide spatial aggregation of station water level dynamics. |

### Predictive Forecasting & Benchmarks
| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/maharashtra/advanced-forecast` | GET | Parallel multi-model forward predictions (Harmonic, LSTM, Autoregressive, Persistence) with scenario toggles and data diagnostics. |
| `/api/v1/maharashtra/advanced-forecast/map` | GET | Statewide predicted water level conditions across all stations for geospatial mapping. |
| `/api/v1/maharashtra/advanced-forecast/models/info` | GET | Formal validation metrics (Directional Precision, Physical MAE, 80% CI coverage) and architecture details. |
| `/api/v1/{region}/future-forecast` | GET | Direct horizon predictions for candidate sites. |
| `/api/v1/{region}/chained-forecast` | GET | Multi-step chained regression projections across horizons. |

Supported `{region}` path parameters are `india` and `maharashtra`.

## Scientific Limitations

To ensure transparency and academic integrity, this system maintains the following boundaries:
1. **Not a Statutory Authority**: The platform does not issue official CGWB groundwater categorizations (Safe, Semi-Critical, Critical, Over-Exploited).
2. **Proxy Flood Potential**: Flood potential assessments are derived from groundwater level rates of rise combined with weather proxies; they do not replace surface hydraulic flood models or local civil protection warnings.
3. **No Demand-Side Extrapolation**: Groundwater stress metrics reflect observed physical drawdown and deficit persistence; they do not measure volumetric domestic or industrial water consumption.
4. **Analytical Groupings for India**: National candidate sites represent spatial-analytical coordinate clusters, as verified physical well metadata is not standardized across all historical records.
5. **Deterministic Auditability**: Forecasts provide bounded projections based on verified trends; they should be interpreted as scientific estimates subject to ongoing telemetry updates.

## Authors & License

This project was developed as an engineering initiative focused on groundwater monitoring, predictive modeling, and hydrogeological analytics.

Repository: [https://github.com/SSujal-Pawarr/groundwater](https://github.com/SSujal-Pawarr/groundwater)
