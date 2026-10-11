# M8.2-D Groundwater Condition Engine: Implementation Assessment

**STATUS:** ASSESSMENT COMPLETE — AWAITING EXPLICIT APPROVAL

## 1. Objective and Concept Separation
The objective of M8.2-D is to implement a scientifically defensible, purely statistical Groundwater Condition Engine that classifies the relative historical position of current groundwater observations. 

To ensure scientific integrity, the architecture must strictly distinguish between three concepts:
1. **Groundwater Condition (M8.2-D):** The absolute statistical position of an observation relative to historical norms (e.g., `EXTREMELY_LOW`, `NORMAL_RANGE`, `HIGH`).
2. **Alert State (M6 - Existing):** Sudden, unexpected deviations, prediction residuals, or data quality events (e.g., `CRITICAL_STATISTICAL_DEVIATION`, `DATA_QUALITY_EVENT`).
3. **Interpretative Resource Events (Out of Scope):** Physical and socio-economic interpretations (e.g., `DROUGHT`, `WATER_SCARCITY`). These cannot be inferred solely from water levels without socio-economic, demand, or authoritative agricultural context.

## 2. Current-State Inspection Summary
- **M4 Features (`seasonal.py`, `anomaly.py`):** Calculates analytical seasons for India, seasonal statistics, and standardized seasonal anomalies (Z-scores). SGI was explicitly rejected due to irregular sampling.
- **M6 Alerting (`engine.py`):** Calculates residual-based and deviation-based Z-scores, producing state machine alerts (`STATE_CRITICAL`, `STATE_WARNING`). 
- **M8.2-C ML Results:** ML struggles with the extreme outliers (e.g., mechanical -1791m probe failures) which massively inflate standard deviation and RMSE.

## 3. Candidate Methodologies

### A. Standardized Anomaly (Z-Score)
- **Method:** `(observation - historical_mean) / historical_std`
- **Assessment:** While useful for M6 forecasting error boundaries, Z-scores are extremely brittle for absolute condition classification because the DWLR dataset contains known, massive mechanical outliers. These outliers severely inflate the standard deviation, squashing the Z-scores of legitimate variations toward zero and masking true `LOW` or `HIGH` conditions.

### B. Historical Percentile Rank (Recommended)
- **Method:** Calculate the percentile rank of the current observation relative to the historical reference distribution for that site and season.
- **Assessment:** Percentiles are non-parametric and highly robust to extreme outliers. A -1791m mechanical failure simply registers as the 0th percentile. It does not stretch the variance or corrupt the `NORMAL_RANGE` (e.g., 25th-75th percentiles) for legitimate observations. 

## 4. Recommended Methodology
We recommend the **Historical Percentile Rank** methodology with the following deterministic bounds:
- **< 10th Percentile:** `EXTREMELY_LOW`
- **10th - 25th Percentile:** `LOW`
- **25th - 75th Percentile:** `NORMAL_RANGE`
- **75th - 90th Percentile:** `HIGH`
- **> 90th Percentile:** `EXTREMELY_HIGH`

These bounds are standard, statistically neutral definitions that do not claim physical interpretations like "Drought" or "Flood".

## 5. Dataset Semantics: India vs Maharashtra

### India (Periodic Observations)
- **Grouping:** By `candidate_site_id` and `analytical_season` (using the M4 mapping in `seasonal.py`). 
- **Rationale:** Comparing a pre-monsoon (dry) reading to an annual historical distribution containing post-monsoon (wet) readings will incorrectly classify all pre-monsoon readings as `LOW`. The reference distribution must be strictly intra-seasonal.

### Maharashtra (High-Frequency Telemetry)
- **Grouping:** By `station_name` and `observation_month`.
- **Rationale:** High-frequency daily telemetry allows for a much more granular monthly historical reference distribution, supporting operational, near real-time condition monitoring.

## 6. History and Data-Quality Requirements
- **Minimum History:** A minimum of **5 valid historical observations** in the specific reference group (season or month) is required to calculate meaningful quartile/decile percentiles.
- **Insufficient History:** If N < 5, the condition evaluates to `INSUFFICIENT_HISTORY`.
- **Data Quality:** Observations flagged by M3 with `CONFLICTING_DUPLICATE`, `INVALID_OR_EMPTY`, or other severe structural anomalies must be **excluded** from the historical reference distribution. 
- **Extreme Values:** Statistically extreme (but mechanically plausible) values are retained. Percentiles naturally contain their impact.

## 7. M8.2-C Interaction (Weather ML)
The M8.2-C ML model forecasts the *next* groundwater state. It does not classify the *current* condition. Therefore, the weather ML model will be **excluded entirely** from the deterministic Condition Engine. Combining a statistical percentile with a predictive weather model conflates current factual conditions with future predictive drivers, corrupting the scientific integrity of the condition label.

## 8. Proposed Output Schema
```json
{
  "site_id": "string",
  "observation_timestamp": "timestamp",
  "condition_state": "enum (EXTREMELY_LOW, LOW, NORMAL_RANGE, HIGH, EXTREMELY_HIGH, INSUFFICIENT_HISTORY, DATA_QUALITY_EXCLUDED)",
  "percentile_rank": "float (0.0 - 100.0, nullable)",
  "historical_reference_group": "string (e.g., 'PRE_MONSOON', 'MONTH_05')",
  "historical_sample_count": "integer",
  "condition_method_version": "string (e.g., 'Percentile_v1.0')"
}
```

## 9. API and Frontend Integration Plan
- **API (M7):** A new DuckDB view or FastAPI endpoint (`/api/v1/sites/{id}/condition`) will be exposed to serve the latest condition state alongside the M6 alerts.
- **Frontend (M8.1):** The React dashboard will require a dedicated "Current Condition" badge/indicator on the site detail pane. Condition should be visually separated from Alerts to prevent UX confusion between "Water is currently very low" (Condition) vs "Water dropped 2 meters yesterday unexpectedly" (Alert).
- **No Implementation Yet:** These integrations will NOT be implemented during M8.2-D.

## 10. Testing Plan
The implementation will require tests verifying:
1. **Percentile correctness:** Known synthetic array yields exact expected percentile bands.
2. **Seasonal segregation:** Pre-monsoon observations are never ranked against post-monsoon distributions.
3. **Minimum history:** Arrays with N=4 yield `INSUFFICIENT_HISTORY`.
4. **Data quality exclusion:** `CONFLICTING_DUPLICATE` records do not corrupt the reference distribution.
5. **No interpretive leakage:** Assert that strings like "DROUGHT" or "FLOOD" never appear in the output.

## 11. Exact Implementation Milestones
If approved, implementation will proceed linearly:
1. Write `test_conditions.py` defining the statistical bounds.
2. Implement `src/features/conditions.py` containing the core percentile logic for both dataset schemas.
3. Integrate the calculation into the `pipeline.py` / `implement_m82d.py` script to append conditions to the analytical parquet artifacts.
4. Final validation against the full dataset.

**ASSESSMENT COMPLETE — AWAITING EXPLICIT APPROVAL**
