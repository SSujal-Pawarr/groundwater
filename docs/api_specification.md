# Milestone 7: India Groundwater Intelligence API Specification

## Overview
This API provides read-only access to the M1-M6 analytical outputs for the India Groundwater Intelligence Platform. It strictly acts as a serving layer and does not recalculate or modify scientific data. 

All endpoints use `GET` requests and return JSON.

## Dataset and Identifier Semantics
- **India Dataset:** Uses `candidate_site_id` as an analytical site identifier because no verified physical station IDs exist.
- **Maharashtra Dataset:** Uses both `candidate_site_id` and `station_name`.
- **Warning:** A `candidate_site_id` represents an analytical grouping, NOT a verified ground-truth asset.

## General Parameters
All paginated endpoints accept:
- `limit` (integer, default: 100, max: 1000): Number of results to return.
- `offset` (integer, default: 0): Number of results to skip.

## Endpoints

### 1. System Health
`GET /health`
Returns basic API readiness and connection to the DuckDB Data Access Layer (DAL).
**Response:**
```json
{
  "status": "ok",
  "dal_healthy": true
}
```

### 2. India Candidate Sites
`GET /api/v1/india/candidate-sites`
Lists unique candidate sites for India.
**Query Parameters:**
- `state` (optional): Filter by state name.
**Response:** Array of candidate site objects containing location and metadata.

### 3. India Telemetry
`GET /api/v1/india/candidate-sites/{candidate_site_id}/telemetry`
Returns the historical periodic water level observations for a specific site.
**Response:** Array of periodic measurements, including `observation_date` and `water_level_raw`.

### 4. India Alerts
`GET /api/v1/india/candidate-sites/{candidate_site_id}/alerts`
Returns the generated causal alert states for a specific site, detailing statistical deviations from the seasonal baseline.
**Response:** Array of alerts, including `alert_event_state` (e.g., NORMAL, WATCH, WARNING, CRITICAL_STATISTICAL_DEVIATION, SEQUENCE_GAPPED, DATA_QUALITY_EVENT).

### 5. India Condition (M8.2-E)
`GET /api/v1/india/candidate-sites/{candidate_site_id}/condition`
Returns the latest statistical groundwater condition state for a specific site, using strictly backward-looking historical percentiles.
**Response:** A single JSON object representing the latest condition.
- `candidate_site_id`: Analytical site identifier.
- `observation_date`: ISO 8601 string of the latest observation.
- `analytical_season`: Grouping season.
- `condition_state`: Enum of `EXTREMELY_LOW`, `LOW`, `NORMAL_RANGE`, `HIGH`, `EXTREMELY_HIGH`, `INSUFFICIENT_HISTORY`.
- `water_level_unit`: Hardcoded as `UNKNOWN`.
- `percentile`, `historical_sample_count`, `historical_reference_group`, `condition_method_version`.
**Errors**:
- `404 Not Found`: Candidate site doesn't exist or has no condition generated.

### 5. Maharashtra Candidate Sites
`GET /api/v1/maharashtra/candidate-sites`
Lists unique candidate sites and station names for Maharashtra telemetry.
**Query Parameters:**
- `district` (optional): Filter by district.
**Response:** Array of candidate site objects.

### 6. Maharashtra Telemetry
`GET /api/v1/maharashtra/candidate-sites/{candidate_site_id}/telemetry`
Returns continuous 6-hourly telemetry data.
**Response:** Array of telemetry records.

### 8. Maharashtra Alerts
`GET /api/v1/maharashtra/candidate-sites/{candidate_site_id}/alerts`
Returns the causal alert states for the Maharashtra continuous telemetry.
**Response:** Array of alerts.

### 9. Maharashtra Condition (M8.2-E)
`GET /api/v1/maharashtra/candidate-sites/{candidate_site_id}/condition`
Returns the latest statistical groundwater condition state for a specific site, using strictly backward-looking historical percentiles.
**Response:** A single JSON object representing the latest condition.
- `candidate_site_id`: Analytical site identifier.
- `observation_timestamp`: ISO 8601 string of the latest observation.
- `condition_state`: Enum of `EXTREMELY_LOW`, `LOW`, `NORMAL_RANGE`, `HIGH`, `EXTREMELY_HIGH`, `INSUFFICIENT_HISTORY`.
- `water_level_unit`: Hardcoded as `meters`.
- `percentile`, `historical_sample_count`, `historical_reference_group`, `condition_method_version`.
**Errors**:
- `404 Not Found`: Candidate site doesn't exist or has no condition generated.

### 10. Maharashtra Latest Forecast (M8.3.2)
`GET /api/v1/maharashtra/candidate-sites/{candidate_site_id}/forecast`
Returns the latest next-valid-observation persistence forecast for a specific site. 
The forecast is a persistence baseline: the latest valid groundwater level is used as the prediction for the next valid groundwater observation.
**Note**: The target timestamp is unavailable at prediction time because there is no fixed horizon; the prediction is purely for the next valid telemetry ping.
**Response:** A single JSON object representing the forecast.
- `candidate_site_id`: Analytical site identifier.
- `latest_observation_timestamp`: ISO 8601 string of the absolute latest analytics-ready observation.
- `latest_water_level`: The water level at the latest valid observation.
- `predicted_next_water_level`: The forecasted water level (equals `latest_water_level`).
- `water_level_unit`: Hardcoded as `meters`.
- `forecast_type`: Hardcoded as `NEXT_VALID_OBSERVATION`.
- `forecast_method`: Hardcoded as `PERSISTENCE`.
- `model_version`: Hardcoded as `persistence-v1`.
**Errors**:
- `404 Not Found`: Candidate site doesn't exist or has no valid analytics-ready observation available.

## Serialization Rules
- Missing or `NaN` numeric values are serialized as JSON `null`.
- Timestamps are returned as ISO 8601 strings (e.g., `2026-10-03T00:00:00Z`).

## Running Locally
From the `NEW` project root:
```bash
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```
Swagger UI will be available at `http://localhost:8000/docs`.
