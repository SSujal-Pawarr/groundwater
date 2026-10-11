# M8.3.1 — Maharashtra Persistence Forecast Artifact

## 1. Description
This document details the generation of the production persistence forecast artifact for Maharashtra. **This is a next-valid-observation persistence forecast, not a fixed-horizon forecast.** The model simply predicts that the water level at the next valid observation will be equal to the current valid observation's water level.

## 2. Configuration & Policy
- **Source Dataset**: `data/processed/maharashtra/maharashtra_normalized.parquet`
- **Quality Policy**: Excludes observations where `is_analytics_ready == False` (which safely encapsulates `INVALID_OR_EMPTY`, `UNREALISTIC_WATER_LEVEL`, and `CONFLICTING_DUPLICATE` removal). Terminal observations for each site are also safely dropped from evaluation pairs.
- **Target Definition**: Next valid observation (`T_target`).
- **Persistence Formula**: `predicted_water_level = observed_water_level` (at `T_current`).
- **Model Version**: `persistence-v1`
- **Artifact Path**: `data/forecasts/maharashtra_persistence_forecast.parquet`

## 3. Artifact Schema
| Field | Type | Description |
|---|---|---|
| `candidate_site_id` | String | Unique site identifier |
| `prediction_timestamp` | Timestamp | Timestamp of the current valid observation (`T_current`) |
| `target_timestamp` | Timestamp | Timestamp of the next valid observation (`T_target`) |
| `forecast_horizon_hours` | Float | Hours between `T_current` and `T_target` |
| `observed_water_level` | Float | The water level at `T_current` |
| `predicted_water_level` | Float | The forecasted water level (equals `observed_water_level`) |
| `actual_water_level` | Float | The true ground truth water level at `T_target` (for evaluation) |
| `model_name` | String | Fixed to `"persistence"` |
| `model_version` | String | Fixed to `"persistence-v1"` |

## 4. Descriptive Statistics
- **Site Count**: 1,008
- **Row Count**: 209,658 forecast pairs

### Horizon Distribution
The forecast horizon (`time_delta_hours`) is purely dictated by telemetry cadence:
- **Median (P50)**: 6.0 hours
- **P25**: 6.0 hours
- **P75**: 6.0 hours
- **P90**: 24.0 hours
- **P95**: 48.0 hours
- **Max**: 2,160.0 hours

## 5. Evaluation Metrics
Metrics are computed over the full normalized dataset consisting of 209,658 valid chronological forecast pairs.
- **MAE**: 0.323 m
- **RMSE**: 1.489 m
- **MedAE (Median Absolute Error)**: 0.040 m
- **R²**: 0.986

*Note: The earlier M8.2-C experimental RMSE of ~4.25m was evaluated over a strict 31,279-row chronological test subset. The metric of 1.489m RMSE presented here evaluates the entire population of the dataset and retains all weather-independent samples, producing a highly comprehensive measurement of baseline system accuracy.*

## 6. Limitations
- **Fault Propagation**: If a mechanical fault causes a sensor to emit a bad value (and it somehow escapes the quality filters), Persistence will propagate that exact bad value into the forecast.
- **Irregular Horizons**: Because this predicts the "next observation", the operational horizon is unpredictable. While the vast majority (75%+) are exactly 6 hours, some telemetry gaps mean the forecast might span weeks.
- **No Interpolation**: We deliberately avoided synthetic data interpolation, meaning forecasting a strict fixed-time window (e.g. exactly 24.0 hours from now) is not possible unless telemetry falls strictly on that mark.

## 7. Reproducibility
The artifact generation pipeline is 100% deterministic and contains no learned parameters, future data leakage, or randomness. Re-running `src/models/persistence_forecast.py` on the exact `maharashtra_normalized.parquet` source will identically reproduce all predictions. There is strictly no India forecast artifact generated per the M8.3 assessment.
