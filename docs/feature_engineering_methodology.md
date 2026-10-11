# Feature Engineering & Baseline Analytics Methodology

**Document Version:** 1.0  
**Milestone:** Milestone 4 (Hydrogeological Feature Engineering, Spatial/Temporal Structure & Baseline Analytics)  
**Date:** October 2026  
**Governing Standard:** [instruction.md](file:///d:/Projects%20ALL/DWLR_GRW_INDIA/instruction.md) (Rules 1, 2, 4, 5, 6, 9, 10, 17, 18)

---

## 1. Core Principles

All feature engineering adheres to:

1. **No Fabrication:** Every derived feature uses only real observations from normalized data. No synthetic wells, hydrogeological units, or physical thresholds are fabricated.
2. **No Future Leakage:** Information from time T+1 or later cannot enter a feature used at time T. All temporal features are strictly backward-looking.
3. **No ML Training:** This milestone establishes baselines and features only. No model training, hyperparameter tuning, or forecasting is performed.
4. **Provenance Preserved:** Every derived column is explicitly documented with its computation method and assumptions.
5. **Raw Immutability:** Source data is never modified. All features are computed on copies.
6. **Dataset-Specific Logic:** India (periodic, seasonal) and Maharashtra (continuous, 6-hourly) require different analytical approaches.

---

## 2. Module Architecture

```text
NEW/src/features/
├── __init__.py         # Package exports
├── spatial.py          # Analytical site IDs, location consistency, clustering evaluation
├── temporal.py         # Temporal profiles, observation gaps, coverage metrics
├── seasonal.py         # Season assignment, seasonal statistics, anomalies, YoY changes
├── trends.py           # Location-specific linear trends, rate of change
├── anomaly.py          # SGI rejection documentation, seasonal z-score
└── baselines.py        # Persistence, seasonal historical, and Maharashtra baselines
```

---

## 3. Spatial/Location Analysis (`spatial.py`)

### 3.1 Analytical Site ID

The India dataset lacks an official station ID. The `candidate_site_id` from normalization (SHA-256 hash of state+district+block+village+lat_4dp+lng_4dp) is promoted as `analytical_site_id`.

**Key properties:**
- Deterministic: same inputs → same output
- Coordinate precision: ~11.1 meters (4 decimal places)
- Explicitly flagged as an analytical construct, NOT an official station ID

### 3.2 Clustering Evaluation

Spatial clustering was **evaluated and rejected** for this dataset:
- The candidate_site_id already captures locations at ~11m precision
- Clustering at coarser radii risks merging distinct monitoring wells
- Without authoritative station metadata, clustering introduces unverifiable assumptions

### 3.3 Location Consistency

Analyzed:
- Unique (lat, lon) pairs per candidate_site_id
- Coordinate precision distribution
- Administrative field completeness
- Near-duplicate locations (same admin fields, different coordinates)

---

## 4. Temporal Structure Analysis (`temporal.py`)

### 4.1 India Temporal Profile

- **Date range:** ~1994 to 2024 (~30 years)
- **Months observed:** [1, 3, 4, 5, 8, 11] (NOT monthly)
- **Observation frequency:** Periodic, ~quarterly (4 main seasons/year)
- **Per-site coverage:** Varies widely (1 to 30+ years)

### 4.2 Maharashtra Temporal Profile

- **Timestamp range:** January to May 2026 (~5 months)
- **Observation frequency:** 6-hourly telemetry
- **Consistency:** ~95%+ of intervals are exactly 6 hours

### 4.3 Observation Gaps

Per-site gap analysis computing min/max/mean/median gap durations in days.

---

## 5. Seasonal Features (`seasonal.py`)

### 5.1 Season Assignment

Analytical season labels based on observed months and Indian meteorological conventions:

| Month | Season Label | Description |
|-------|-------------|-------------|
| 1 (January) | RABI_WINTER | Post-monsoon / winter recharge period |
| 3 (March) | PRE_MONSOON_EARLY | Limited data, early pre-monsoon |
| 4 (April) | PRE_MONSOON | Dry season, lowest water tables |
| 5 (May) | PRE_MONSOON | Dry season, lowest water tables |
| 8 (August) | MONSOON | Peak recharge period |
| 11 (November) | POST_MONSOON | Post-monsoon, high water tables |

**Disclaimer:** These are analytical convenience labels, NOT official CGWB season codes.

### 5.2 Seasonal Statistics

Per (site, season) group statistics: mean, median, std, min, max, observation count, unique years. Only computed for groups with ≥ `min_observations` (default: 3).

### 5.3 Seasonal Anomaly

$$\text{anomaly} = \text{observation} - \text{historical\_seasonal\_mean}$$

### 5.4 Year-over-Year Seasonal Change

$$\text{yoy\_change}_y = \text{seasonal\_mean}_y - \text{seasonal\_mean}_{y-1}$$

Strictly backward-looking: each year references only the immediately preceding year.

---

## 6. Trend Analysis (`trends.py`)

### 6.1 Location Trend (OLS Linear Regression)

For sites with ≥ `min_observations` (default: 10) spanning ≥ `min_years_span` (default: 3):

$$\text{water\_level} = \beta_0 + \beta_1 \cdot \text{days\_since\_first\_obs}$$

Reported: slope (per day and per year), intercept, R², p-value, standard error.

**Direction labels (neutral):**
- INCREASING (slope > 0, p < 0.05)
- DECREASING (slope < 0, p < 0.05)
- STABLE (slope ≈ 0, p < 0.05)
- NOT_SIGNIFICANT (p ≥ 0.05)

**No physical interpretation** (e.g., "groundwater depletion") is applied because the reference datum is UNKNOWN and water-level unit semantics are not confirmed.

### 6.2 Rate of Change

Per-observation backward-looking rate:
$$\text{rate\_per\_day} = \frac{\text{value}_t - \text{value}_{t-1}}{\text{days}_t - \text{days}_{t-1}}$$

---

## 7. Statistical Anomaly/Index (`anomaly.py`)

### 7.1 SGI Decision: **REJECTED**

The Standardized Groundwater Index (SGI) is NOT scientifically justified for this dataset:

1. **Temporal irregularity:** Observations in only 6 months, not monthly
2. **Insufficient March data:** Only ~7,300 observations (0.47% of total)
3. **Incomplete coverage:** Many sites lack all seasons across all years
4. **Unknown reference datum:** Cannot interpret as physical stress indicator
5. **Mixed observation types:** Different seasons represent different hydrological states

### 7.2 Seasonal Z-Score (Alternative)

$$z = \frac{\text{observation} - \mu_{\text{site,season}}}{\sigma_{\text{site,season}}}$$

Only computed for (site, season) groups with ≥ `min_observations` (default: 5).

This is a **statistical anomaly measure**, NOT a drought or stress index.

---

## 8. Baseline Analytics (`baselines.py`)

### 8.1 India Persistence Baseline

$$\hat{y}_t = y_{t-1} \text{ (at the same site)}$$

The simplest possible baseline. No seasonal or trend information used.

### 8.2 India Seasonal Historical Baseline

$$\hat{y}_{t,s} = \frac{1}{|\{y_{<t,s}\}|} \sum y_{<t,s}$$

Mean of all PREVIOUS years' observations at the same site and same season. **Strictly backward-looking**: for year Y, only observations from years < Y are used. Requires ≥ `min_historical_years` (default: 3) of prior data.

### 8.3 Maharashtra Persistence Baseline

Same as India persistence but using station_name and observation_timestamp. For 6-hourly telemetry, the "previous observation" is typically 6 hours prior.

### 8.4 Evaluation Metrics

For all baselines, standard metrics computed on residuals (actual − predicted):
- **MAE:** Mean Absolute Error
- **RMSE:** Root Mean Squared Error
- **MedAE:** Median Absolute Error
- **Bias:** Mean Error (signed)

---

## 9. Data Leakage Prevention

Every temporal feature guarantees no future leakage:

| Feature | Information Available at Prediction Time |
|---------|------------------------------------------|
| Persistence prediction | Most recent prior observation at same site |
| Seasonal historical baseline | All prior years' same-season observations |
| Rate of change | Current and immediately preceding observation |
| YoY seasonal change | Current and previous year's seasonal mean |
| Seasonal z-score | Full historical record for characterization |

The first observation per site/season always has NaN for lag-based features (no prior data available).

---

## 10. Unresolved Scientific Uncertainties

| Uncertainty | Impact | Resolution |
|-------------|--------|------------|
| India water-level unit UNKNOWN | Cannot interpret trend slopes physically | Await authoritative metadata |
| Reference datum UNKNOWN | Cannot determine if "increasing" means rising/falling water table | Await official documentation |
| `status_raw` / `trend_raw` provenance unverified | Cannot use as ground truth labels | Quarantined from ML features |
| `candidate_site_id` is analytical, not official | May merge or split real monitoring locations | Document as analytical construct |
| Seasonal labels are analytical convention | May not match official CGWB seasonal windows | Document provenance explicitly |

---

## 11. Test Coverage

The test suite (`NEW/tests/test_features.py`) validates:

1. **Deterministic analytical site IDs** — same input → same output
2. **No modification of source observations** — original DataFrames unchanged
3. **Correct chronological ordering** — features sorted by date/timestamp
4. **No future leakage** in lag features — first obs per site has NaN
5. **Rolling features use only historical/current information**
6. **Missing observations handled explicitly** — NaN propagated correctly
7. **Seasonal grouping correctness** — month-to-season mapping validated
8. **Trend calculation handles insufficient observations** — graceful degradation
9. **Anomaly/index handles insufficient history** — NaN when too few obs
10. **Baseline calculations do not access future observations** — verified by independent computation
11. **Ambiguous spatial records flagged** — clustering necessity evaluated and rejected
