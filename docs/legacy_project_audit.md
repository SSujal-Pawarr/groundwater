# Legacy Project Audit: "MINI PROJECT TE"

**Audit Date:** October 2026  
**Auditor:** Groundwater Intelligence Platform Senior Engineering & Technical Review Team  
**Scope:** In-depth technical, architectural, hydrogeological, and data audit of legacy repository `MINI PROJECT TE/`.

---

## 1. Executive Summary

The legacy project (`MINI PROJECT TE/`) is a prototype web application designed to visualize telemetry from 1,016 Digital Water Level Recorder (DWLR) stations across 34 districts of Maharashtra. It provides a Leaflet-based interactive dashboard, 6-hourly time-series drilldowns, an ML-based 24-hour regressor, a classification alert model, a hydrogeological "What-If" scenario simulator, and an Open-Meteo weather integration.

While the frontend visual presentation and user interface concepts are visually engaging, the engineering and scientific underpinnings suffer from severe technical deficiencies, including:
1. **Temporal data leakage** in machine learning evaluation (random train-test splits on time series).
2. **Fabricated multi-day forecasting** (mathematical power-law extrapolation masquerading as independent 15-day ML predictions).
3. **Circular classification** (a Random Forest classifier trained to reproduce deterministic rule-based labels created from its own input features).
4. **Hydrogeologically unvalidated simulation equations** (arbitrary linear multipliers for rainfall recharge and extraction depletion).
5. **Silent synthetic fallback data** (generating fake weather when the API fails rather than raising or reporting an error).
6. **Reference datum ambiguities** (conflating negative sensor readings with depth below ground level without datum proof).

---

## 2. Evidence Classification Framework

As required by project instructions, all observations in this audit are strictly categorized under:
- **FACT:** Directly observed in code, configuration, or data.
- **ASSUMPTION:** Assumed by the legacy implementation without empirical or scientific verification.
- **PROBLEM:** A technically incorrect, mathematically invalid, or scientifically unsound implementation.
- **REUSABLE:** A design pattern, visual asset, or component suitable for reuse.
- **REBUILD:** A component requiring complete architectural redesign.

---

## 3. Repository Structure & Artifacts

### FACT: Observed Folder Hierarchy
```text
MINI PROJECT TE/
├── __pycache__/
│   ├── app.cpython-314.pyc
│   ├── ml_engine.cpython-314.pyc
│   └── weather_service.cpython-314.pyc
├── app.py                                           # Flask REST API & static file server (191 lines)
├── gwl_tel_6_hourly_maharashtra_gw_mh_2026_2030 (1).csv # Raw 6-hourly telemetry CSV (218,791 rows, 29.2 MB)
├── ml_cache.pkl                                     # Serialized precomputed cache & scikit-learn models (21.1 MB)
├── ml_engine.py                                     # Core data processing, ML training, forecasting, simulator (432 lines)
├── weather_service.py                               # Open-Meteo weather client, synthetic fallback, alerts (491 lines)
└── static/
    ├── css/
    │   ├── landing.css                              # Landing page styling (31.4 KB)
    │   └── style.css                                # Dashboard styling (46.0 KB)
    ├── img/
    │   └── maharashtra_farm_bg.png                  # Background hero graphic (953.6 KB)
    ├── index.html                                   # Operations dashboard template (33.7 KB)
    ├── js/
    │   ├── app.js                                   # Dashboard frontend state, Leaflet & Chart.js logic (51.5 KB)
    │   └── landing.js                               # Landing page interaction script (15.0 KB)
    └── landing.html                                 # Product landing page ("SHIVAR") (31.2 KB)
```

---

## 4. Backend Architecture

### FACT: Direct Observations
- **Framework:** Python Flask (`Flask(__name__, static_folder='static', static_url_path='')`).
- **Server Execution:** `app.run(host='0.0.0.0', port=port, debug=False, threaded=True)`.
- **In-Memory Caching:** Two global singletons: `engine = MLEngine()` in `ml_engine.py` and `weather_service = WeatherService()` in `weather_service.py`.
- **Startup Lifecycle:**
  1. Calls `engine.load_and_preprocess(force_retrain=False)` on server launch.
  2. If `ml_cache.pkl` exists, loads all station metadata, district summaries, time-lapse snapshots, and trained scikit-learn models directly into memory.
  3. Initializes district centroids in `weather_service` using the station coordinates dictionary.

### PROBLEM: Backend Architecture Weaknesses
- **Monolithic State:** All preprocessed data for 1,016 stations and 218,791 rows is held permanently in memory in Python dictionaries (`stations_meta`, `station_latest`, `district_summary`). This architecture cannot scale India-wide to tens of thousands of stations across all states without memory exhaustion.
- **Pickle Security & Fragility:** Storing trained models and entire datasets in a 21MB pickle file (`ml_cache.pkl`) creates security risks, version incompatibility across Python/scikit-learn releases, and hinders incremental updates.
- **No Production WSGI:** Relies on the built-in Flask development server (`app.run`), which is unsuitable for production deployments.

---

## 5. Dataset & Schema Analysis

### FACT: Raw Telemetry Dataset Facts
- **Filename:** `gwl_tel_6_hourly_maharashtra_gw_mh_2026_2030 (1).csv`
- **File Size:** 29,176,353 bytes (~27.8 MB)
- **Total Rows:** 218,791 rows
- **Columns (21):**
  1. `SlNo` (`int64`): Sequential row identifier.
  2. `Station` (`object`): Station name (uppercase string, 1,016 unique stations).
  3. `Agency` (`object`): Source agency (observed: "Maharashtra GW").
  4. `State LGD Code` (`int64`): Local Government Directory code (27 for Maharashtra).
  5. `State` (`object`): State name ("Maharashtra").
  6. `District LGD Code` (`int64`): LGD code for district.
  7. `District` (`object`): District name (34 unique districts).
  8. `Tehsil` (`object`): Subdistrict name.
  9. `Block` (`object`): Populated predominantly with string `"-"`.
  10. `Village` (`object`): Populated predominantly with string `"-"`.
  11. `River` (`object`): Populated predominantly with `"-"`.
  12. `Basin` (`object`): Populated predominantly with `"-"`.
  13. `Tributary` (`object`): Populated predominantly with `"-"`.
  14. `Subtributary` (`object`): Populated predominantly with `"-"`.
  15. `SubSubtributary` (`object`): Populated predominantly with `"-"`.
  16. `Local River` (`object`): Populated predominantly with `"-"`.
  17. `Latitude` (`float64`): Station latitude (e.g. 20.402778).
  18. `Longitude` (`float64`): Station longitude (e.g. 76.845836).
  19. `RL_MSL` (`float64`): Reduced Level relative to Mean Sea Level (elevation datum).
  20. `Data Acquisition Time` (`object`): Formatted as `%d-%m-%Y %H:%M`.
  21. `Groundwater Level Telemetry 6 Hourly (meter)` (`float64`): Recorded telemetry values.
- **Observed Date Coverage:** From `01-01-2026 00:00` to `30-05-2026 00:00` (150 days of 6-hourly observations).
- **Groundwater Value Distribution:**
  - Range: Minimum `-1791.03 m`, Maximum `+213.318 m`.
  - Negative values: 201,211 rows (91.96%).
  - Positive values: 17,580 rows (8.04%).
  - Extreme values: 281 rows `< -100 m`, 608 rows `> +50 m`.

### ASSUMPTION: Unproven Datum Interpretation
- The legacy code assumes:
  ```python
  depth_bgl = round(abs(curr_gwl) if curr_gwl < 0 else 0.0, 3)
  ```
  It assumes that negative numbers represent meters below ground level (e.g., `-5.965` means `5.965 m bgl`), and positive numbers represent water above ground level or positive piezometric head.
- **However:** No official CGWB / GSDA metadata document is provided to verify whether the sensor is calibrated to ground level, well casing collar, top of sensor cable, or elevation head relative to MSL. Positive values (+213m) strongly suggest some stations record water table elevation or have distinct sensor reference offsets.

### PROBLEM: Data Cleaning & Quality Deficiencies
- The cleaning step is a single hardcoded filter:
  ```python
  df = raw_df[(raw_df[gw_col] > -100) & (raw_df[gw_col] < 50)].copy()
  ```
  This drops 889 anomalous observations without logging, station error tracking, or sensor drift diagnosis.
- Missing values in textual columns (`Block`, `Village`, `River`) are left as literal hyphens `"-"` rather than normalized `NaN` or `None`.

---

## 6. Machine Learning Pipeline & Forecasting Logic

### FACT: Implemented Algorithms
- **Model 1:** `RandomForestRegressor(n_estimators=35, max_depth=12, random_state=42, n_jobs=-1)`
- **Model 2:** `RandomForestClassifier(n_estimators=35, max_depth=12, random_state=42, n_jobs=-1)`
- **Feature Set:** `['lag_1', 'lag_4', 'lag_28', 'rolling_mean_7d', 'rolling_std_7d', 'diff_24h', 'Latitude', 'Longitude', 'RL_MSL']`
- **Regression Target:** `target_next_24h = df.groupby('Station')[gw_col].shift(-4)` (predicting 4 steps ahead = 24 hours).
- **Reported Metrics in `ml_cache.pkl`:**
  - `r2_score`: 0.998+
  - `mae`: ~0.08 m
  - `accuracy`: ~98.5%

### PROBLEM: Fatal Methodological Errors

#### 1. Severe Temporal Data Leakage
The legacy project evaluates time-series forecasting using random splitting:
```python
X_train, X_test, y_reg_train, y_reg_test, y_clf_train, y_clf_test = train_test_split(
    X, y_reg, y_clf, test_size=0.2, random_state=42
)
```
- **Why this is invalid:** In time-series data with dense autoregressive lags (`lag_1` is 6 hours prior, `rolling_mean_7d` averages adjacent hours), randomly shuffling observations places t-1 in the training set and t in the test set. The model merely interpolates between known future and past points. The reported R² of 0.998 is an artifact of leakage and does not reflect true out-of-sample forecasting skill.

#### 2. Fabricated 7-Day and 15-Day Multi-Horizon Forecasts
While the frontend displays a 15-day forward forecast curve, the ML model was only trained on a single horizon (24 hours). The 7-day and 15-day points are computed using a hardcoded heuristic formula (`ml_engine.py` lines 201-214):
```python
for step in range(1, 16):
    step_val = curr_gwl + (pred_24h - curr_gwl) * (step ** 0.6) - (0.015 * step)
    conf_upper = round(step_val + 0.35 * (step ** 0.5), 3)
    conf_lower = round(step_val - 0.35 * (step ** 0.5), 3)
```
- **Why this is unacceptable:** This is a deterministic mathematical decay curve with arbitrary square-root confidence intervals. Presenting this to decision-makers as "ML predictions with statistical confidence bounds" violates Rule 8, Rule 10, and Rule 30 of `instruction.md`.

#### 3. Circular Classification Logic
The classifier is trained on synthetic labels derived directly from the regression target:
```python
y_clf = [compute_warning_label(g, d, s) for g, d, s in zip(ml_df['target_next_24h'], ml_df['target_diff_24h'].fillna(0), ml_df['sgi'])]
```
Where `compute_warning_label` uses hardcoded if-else thresholds on groundwater depth and difference.
- **Why this is redundant:** The model is learning to replicate an explicit deterministic Python function. A simple rule evaluation on the regressor output would be identical, faster, and 100% consistent.

#### 4. No Comparison Against Baselines
The system does not evaluate against standard baselines (e.g., persistence: $\hat{y}_{t+24} = y_t$). In groundwater hydrology, daily water levels often change by millimeters; a persistence baseline will trivially yield an $R^2 > 0.95$ without any learning.

---

## 7. Hydrogeological Index (SGI) and Alert Rules

### FACT: Implementation in Code
```python
# ml_engine.py lines 76-79
station_mean = df.groupby('Station')[gw_col].transform('mean')
station_std = df.groupby('Station')[gw_col].transform('std').replace(0, 1).fillna(1)
df['sgi'] = ((df[gw_col] - station_mean) / station_std).round(2)
```

### PROBLEM: Hydrogeologically Flawed SGI Calculation
- The Standardized Groundwater Index (SGI), formally defined by Bloomfield & Marchant (2013), requires long-term monthly historical records (typically 10-30 years) fitted to monthly parametric (Gamma, Weibull) or non-parametric normal score transform distributions to account for natural seasonal oscillation.
- Calculating SGI as a raw z-score across 5 non-monsoon months (Jan-May 2026) produces severe seasonal distortion: normal dry-season water table recessions are mislabeled as severe multi-sigma drought anomalies.

### PROBLEM: Arbitrary Static Alert Thresholds
Alerts are determined by static depth cutoffs:
- `gwl >= -2.0 m` or `diff_24h >= 1.5 m` or `sgi >= 1.8` $\rightarrow$ `FLOOD_WATERLOGGING_RISK`
- `gwl < -15.0 m` or `sgi <= -1.5` $\rightarrow$ `CRITICAL_DROUGHT`
- `gwl < -10.0 m` or `sgi <= -1.0` $\rightarrow$ `MODERATE_SCARCITY`
- Otherwise $\rightarrow$ `SAFE_NORMAL`
- **Why this is problematic:** Groundwater hydrology across Maharashtra varies drastically between deep alluvial aquifers (Tapi, Purna valleys) and shallow unconfined weathered Deccan basalt. In alluvium, 15m depth is often normal; in hard rock basalt with 8m weathered zone thickness, 15m means complete dryout. Applying uniform static thresholds statewide lacks scientific credibility.

---

## 8. What-If Climate & Extraction Simulation

### FACT: Observed Simulation Code
```python
# ml_engine.py lines 388-391
recharge_delta = (rainfall_pct / 100.0) * 3.5  # up to +3.5m rise
depletion_delta = (dry_spell_days / 30.0) * 1.8 + (extraction_pct / 100.0) * 2.2
sim_gwl = base_gwl + recharge_delta - depletion_delta
```

### PROBLEM: Arbitrary Heuristics
- The simulation assumes that a 100% rainfall increase universally causes a 3.5m water level rise, 30 days of dry spell universally causes a 1.8m drop, and a 100% extraction increase causes a 2.2m drop across every single aquifer, station, soil type, and topography in Maharashtra.
- As highlighted in `instruction.md` Rule 13, this is an arbitrary formula masquerading as hydrogeological science.

---

## 9. Weather Integration & Hydro-Meteorological Alerts

### FACT: Implementation
- **Provider:** Open-Meteo REST API (`https://api.open-meteo.com/v1/forecast`).
- Fetches temperature, relative humidity, precipitation, wind speed, WMO weather codes, and FAO-56 evapotranspiration ($ET_0$).
- Multi-threaded district weather fetching via `ThreadPoolExecutor(max_workers=12)`.
- 15-minute in-memory caching.

### PROBLEM: Silent Synthetic Fallback
In `weather_service.py` (`_generate_synthetic_fallback` lines 136-188):
```python
def _generate_synthetic_fallback(self, lat: float, lon: float, location_name: str) -> Dict[str, Any]:
    """Generates realistic seasonal meteorological data if network/API is unreachable."""
    ...
```
- If the Open-Meteo API fails or network access is down, the service generates fake temperatures (28-33.5°C), synthetic rain amounts (8.5mm), and fake WMO weather codes and serves them to the caller as if they were valid readings.
- This directly violates Rule 1, Rule 2, and Rule 5 of `instruction.md`. Service failures must be explicitly surfaced.

### PROBLEM: Temporal Misalignment
- The DWLR telemetry dataset spans January to May 2026.
- The weather service calls live real-time Open-Meteo weather forecasts (for the current calendar date) and pairs them with static historic station readings from May 2026. This violates Rule 12 (`instruction.md`).

---

## 10. Frontend Architecture & API Consumption

### FACT: Frontend Stack
- HTML5, Vanilla JavaScript (`app.js`, `landing.js`), Vanilla CSS (`style.css`, `landing.css`).
- External Libraries via CDN:
  - Leaflet 1.9.4 (Map base)
  - Leaflet.markercluster 1.5.3 (Marker clustering)
  - Leaflet.heat 0.2.0 (Heatmap density layer)
  - Chart.js 4.4.1 (Time-series and forecast charts)
  - Lucide Icons
  - Google Fonts (Inter, Outfit, JetBrains Mono)
- APIs Consumed:
  - `GET /api/overview`
  - `GET /api/stations?district=...&warning=...`
  - `GET /api/station/<name>`
  - `GET /api/districts`
  - `GET /api/timelapse`
  - `POST /api/simulate`
  - `GET /api/model_info`
  - `GET /api/weather/station/<name>`
  - `GET /api/weather/district/<name>`
  - `GET /api/weather/districts`
  - `GET /api/weather/alerts`

### REUSABLE: Frontend Strengths
- The UI styling in `style.css` provides a modern dark-mode aesthetic with good visual hierarchy.
- The use of Leaflet marker clustering and heatmaps provides smooth interaction for 1,000+ points.
- The station detail modal effectively combines historical telemetry charts, forecast curves, and key statistics.

---

## 11. Configuration & Dependency Management

### FACT: Findings
- **No `requirements.txt`:** The legacy repository lacks any dependency specification file. Dependencies had to be deduced from Python import statements (`flask`, `pandas`, `numpy`, `scikit-learn`).
- **No Environment Management:** There is no `.env` or `.env.example`. Configuration parameters (such as port 5000) are handled by basic `os.environ.get('PORT', 5000)`.
- **Hardcoded Strings:**
  - `last_updated: 'May 2026 Telemetry'` hardcoded in `ml_engine.py:333`.
  - Hardcoded district fallback coordinates dictionary `MAHARASHTRA_DISTRICT_COORDS` with 36 entries.
  - Hardcoded elevation fallback `rl_msl = 400.0`.

---

## 12. Component Categorization Matrix

| Component / Subsystem | Status | Classification | Key Audit Finding |
| :--- | :--- | :--- | :--- |
| **Raw CSV Data** | Exists | **FACT / REUSABLE** | Real 6-hourly DWLR data for 1,016 stations; immutable source file. |
| **Datum Interpretation** | Flawed | **ASSUMPTION / REBUILD** | Unverified assumption that negative values equal depth bgl. |
| **Data Cleaning** | Primitive | **PROBLEM / REBUILD** | Hardcoded cutoff `(-100, 50)`; drops data silently without error flags. |
| **SGI Computation** | Flawed | **PROBLEM / REBUILD** | Simple z-score across 5 dry-season months; lacks seasonal fitting. |
| **ML Regressor (t+24h)** | Leaked | **PROBLEM / REBUILD** | Random train_test_split on time series creates massive temporal leakage. |
| **15-Day Forecasting** | Fabricated | **PROBLEM / REBUILD** | Power-law heuristic decay curve masquerading as multi-day ML model. |
| **ML Classifier** | Circular | **PROBLEM / REBUILD** | Random Forest trained to reproduce its own deterministic rule labels. |
| **What-If Simulator** | Unscientific | **PROBLEM / REBUILD** | Arbitrary linear constants (+3.5m recharge, -1.8m dry spell) lack physical backing. |
| **Weather Client** | Useful | **REUSABLE** | Open-Meteo coordinate-based queries without API keys are efficient. |
| **Weather Fallback** | Prohibited | **PROBLEM / REBUILD** | Silent generation of synthetic weather records violates core rules. |
| **UI Design & Theme** | High Quality | **REUSABLE** | Dark-mode dashboard, Leaflet mapping, Chart.js components are well designed. |
| **API Architecture** | Monolithic | **REBUILD** | In-memory singleton state cannot scale India-wide; needs modular service architecture. |

---

## 13. Strategic Recommendations for New Project (`NEW/`)

1. **Keep Raw Data Pristine:** Move the raw Maharashtra CSV to `NEW/data/raw/maharashtra/` without modification.
2. **Design an Auditable Data Ingestion Pipeline:** Implement validation checks, flag anomalies (rather than dropping rows), and verify the reference datum against official CGWB documentation.
3. **Implement Rigorous Time-Series ML:**
   - Establish a simple persistence baseline first.
   - Use strict chronological train/validation/test splitting (e.g., Train on Jan-March, Test on April-May).
   - Only claim forecasts for horizons genuinely predicted by the model.
4. **Replace Heuristics with Calibrated or Physical Logic:**
   - Clearly document assumptions for scenario simulations.
   - Never present an arbitrary formula as a validated prediction.
5. **Decouple and Modularize Architecture:**
   - Build separate modular layers: ingestion, validation, feature engineering, modeling, alerts, and API.
   - Avoid global in-memory state so the system can ingest national India-wide datasets.
