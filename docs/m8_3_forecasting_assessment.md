# M8.3 — Production Forecasting Architecture Assessment

## 1. Current Forecasting Capability
The system currently implements experimental forecasting pipelines (M5, M8.2-C) featuring Persistence, Groundwater-only ML, and Weather-Enhanced ML models. These exist purely as offline Python artifacts and evaluation scripts. There is currently no production serving layer (API or UI) exposing these forecasts.

## 2. M8.2-C Result Audit
Based on the strictly untouched validation-selected Test Set in `m8_2_c_experiment_results.md`, the actual results are:
- **Persistence:** MAE = 0.348 m, RMSE = 4.25 m, R² = 0.997
- **GW-Only ML:** MAE = 5.518 m (from ablation baseline)
- **Best Weather ML (GW + Precip + ET0):** MAE = 3.863 m, RMSE = 74.75 m, R² = 0.084

Weather features added incremental value over groundwater alone. However, Persistence utterly dominates all ML models.

## 3. Target Definition
The established target is the **next valid groundwater observation**. This is a scientifically honest formulation that avoids hallucinating or interpolating missing timestamps. However, because telemetry is irregular, this target represents an irregular horizon rather than a fixed operational window.

## 4. Horizon Analysis
The distribution of `time_delta_hours` is overwhelmingly skewed toward `<= 6h` (N=28,114) versus `> 48h` (N=1,732). Enforcing fixed horizons (e.g., 24h, 7 days) would require either predicting into gaps where no ground truth exists or heavy interpolation. We recommend keeping the target strictly as `H1` (next observation) rather than fixed horizons.

## 5. Maharashtra Suitability
Maharashtra data consists of high-frequency (approx. 6-hourly) telemetry. This dataset is structurally suited for short-term operational forecasting.

## 6. India Suitability
India data is historical and periodic (typically sampled 4 times a year). The next observation may be months away. Consequently, short-term operational forecasting is mechanically invalid for India. India should remain an analytics-only dataset focused on historical statistical conditions (M8.2-D) and long-term seasonal modeling. **Do not deploy short-term forecasting for India.**

## 7. Data Quality Strategy
Production training and evaluation must explicitly exclude observations flagged as `INVALID_OR_EMPTY`, `UNREALISTIC_WATER_LEVEL`, or `CONFLICTING_DUPLICATE`. However, at inference time, the model must be robust to extreme current observations. 

## 8. Weather Feature Strategy
Do not deploy weather features for operational forecasting. The M8.2-C evidence conclusively shows that the added complexity of weather features fails to beat a naive persistence baseline. 

## 9. Leakage Strategy
The golden rule must be strictly enforced:
`weather_end_timestamp <= prediction_cutoff < target_timestamp`
There can be zero future information included in the features. The cutoff must be aggressively validated.

## 10. Chronological Split Strategy
The strict **Target-Isolated Chronological Split** used in M8.2-C must remain the production standard. Random splitting is scientifically invalid for time-series forecasting. Train, validation, and test sets must remain chronologically sequenced.

## 11. Model Comparison
Persistence vs. HistGradientBoostingRegressor (ML). Persistence heavily outperforms ML in MAE (0.348m vs 3.863m) and avoids catastrophic failure on anomalies.

## 12. Persistence Baseline Decision
**Persistence must be adopted as the primary short-horizon (H1) production model.** Do not force ML into production simply for the sake of using AI. Persistence is scientifically justified, robust, computationally cheap, and highly accurate for Maharashtra telemetry.

## 13. Uncertainty Strategy
Prediction intervals (e.g., P10/P90) are not empirically validated in the current pipeline. Do not emit fabricated uncertainty bounds. Production should launch with point forecasts only until probabilistic calibration is rigorously tested.

## 14. Extreme-Value Strategy
Extreme anomalies (e.g., -1791m readings) completely break the ML RMSE (74.75m full vs 1.20m cleaned). However, these are real mechanical readings recorded in the telemetry. Persistence naturally handles these by carrying them forward (RMSE 4.25m). Do not delete extreme values to make the ML loss look better.

## 15. Production Architecture
The serving architecture must be static and decoupled:
`Offline Generation -> forecast.parquet -> DuckDB DAL -> FastAPI -> React`
Do not implement online inference or frontend computation.

## 16. Forecast Artifact Proposal
The offline `forecast.parquet` artifact should contain:
- `candidate_site_id`
- `prediction_timestamp`
- `target_timestamp`
- `forecast_horizon_hours`
- `predicted_water_level`
- `prediction_method` (e.g., "Persistence-H1")
- `model_version`

## 17. API Proposal
Add a read-only endpoint:
`GET /api/v1/maharashtra/candidate-sites/{candidate_site_id}/forecast`
Returning the latest predicted record from the artifact. Do not modify existing M7 or M8.2-E endpoints.

## 18. Frontend Proposal
Add a discrete `FORECAST` block to the Investigation Panel.
Hierarchy:
- GROUNDWATER CONDITION
- STATISTICAL ALERT
- FORECAST
Do not merge these into a combined "risk score".

## 19. Testing Plan
- Unit tests verifying target timestamp is strictly `> prediction_timestamp`.
- Integration tests ensuring API correctly handles missing `forecast.parquet`.
- Regression tests matching API response to offline Persistence baseline.
- Validation that India gracefully rejects forecast rendering.

## 20. Risks
- **Fault Propagation:** Persistence will confidently predict that a broken -1000m sensor reading will remain -1000m. 
- **Irregular Horizons:** H1 means users might see a forecast for 4 hours from now, or 40 hours from now, depending on sensor cadence.

## 21. Final Production Recommendation
**READY WITH PERSISTENCE-FIRST HYBRID.**
Deploy the offline artifact pipeline and API/UI to expose Persistence for Maharashtra. Abandon the weather-enhanced ML for short-horizon production, and exclude the India dataset from operational forecasting.
