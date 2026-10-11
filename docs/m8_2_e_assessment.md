# M8.2-E Pre-Implementation Assessment
**Condition / Forecast Integration**

## 1. Current API Architecture
The backend is a read-only FastAPI application serving as a Data Access Layer (DAL). It uses `duckdb` in-memory to execute SQL queries directly against static Parquet files located in `NEW/data/`. Current routes are strictly segmented by dataset (`india` and `maharashtra`), exposing candidate sites, telemetry (M3), and alerts (M6).

## 2. Current Frontend Architecture
The frontend is a React + TypeScript application (built with Vite) located in `NEW/frontend/`. It communicates with the API via `src/services/api.ts` and renders a dashboard with MapLibre GL JS, a sidebar for site selection, and observation/alert charts.

## 3. M8.2-D Artifact Audit
- **Status:** NO persisted Parquet artifact exists.
- **Current State:** The condition logic is fully implemented and tested in `NEW/src/features/conditions.py` (`compute_india_conditions`, `compute_maharashtra_conditions`), but there is no pipeline script that materializes these results into the `NEW/data/` directory.
- **Recommendation:** Do not compute conditions on the fly in the API. We must create an offline generation script to persist deterministic `india_conditions.parquet` and `maharashtra_conditions.parquet` artifacts.

## 4. M8.2-C Forecast Artifact Audit
- **Status:** NO production forecast artifact exists.
- **Current State:** M8.2-C correctly produced `m82c_experiment.py` and experiment metrics documenting that persistence generally outperforms ML baselines operationally. There is no serialized model, no inference pipeline, and no stored prediction Parquet file.
- **Recommendation:** DEFERRED. Forecast serving must remain entirely deferred. We will not fabricate or synthesize forecast values.

## 5. Recommended Data Flow
Offline Python Script (`generate_conditions.py`) -> Persists to `data/conditions/*.parquet` -> FastAPI DAL (DuckDB) -> React UI.

## 6. Recommended Condition Endpoint(s)
To maintain API symmetry, we should add:
- `GET /api/v1/india/candidate-sites/{candidate_site_id}/conditions`
- `GET /api/v1/maharashtra/candidate-sites/{candidate_site_id}/conditions`
These will return the historical sequence of M8.2-D condition states, percentiles, and reference sample counts.

## 7. Recommended Site-Summary Design
To prevent the frontend from making 4+ concurrent requests just to populate a high-level sidebar summary, we recommend a new endpoint:
- `GET /api/v1/{dataset}/candidate-sites/{candidate_site_id}/summary`
This endpoint will use DuckDB to quickly fetch just the **latest (most recent) row** from:
1. M3 Telemetry (Latest water level & date)
2. M6 Alerts (Latest alert event state)
3. M8.2-D Conditions (Latest statistical condition & percentile)
- **Forecast Availability:** Hardcoded to `False` / `Not Available`.

## 8. Alert Integration Design
- The existing `/alerts` endpoints will remain untouched and serve the full chronological history of statistical anomalies.
- The new `/summary` endpoint will only expose the *instantaneous* current alert state, strictly separating it from the new *condition* state.

## 9. Forecast Serving Decision
**Deferred.** The UI will explicitly render "FORECAST: NOT AVAILABLE" or simply omit the section. We will not serve experimental ML outputs.

## 10. India/Maharashtra API Semantics
- **India Summary:** Will return `observation_date` and `analytical_season`. Water level units will remain "Unknown Units".
- **Maharashtra Summary:** Will return `observation_timestamp` and `observation_month`. Water level units will be "Meters".

## 11. Frontend Integration Plan
- Update `api.ts` to include the new `/conditions` and `/summary` API bindings.
- In the site sidebar/investigation panel, add a distinct section titled **"Groundwater Condition"**.
- Render the neutral labels (`EXTREMELY_LOW`, `NORMAL_RANGE`, etc.) along with the historical percentile (e.g., "Percentile: 74.5").
- Render the alert state separately under **"Statistical Alert State"**.
- Absolutely NO use of "Drought" or "Flood" labels. 

## 12. Data Storage Plan
We will introduce a new directory:
`NEW/data/conditions/`
Containing:
- `india_conditions.parquet`
- `maharashtra_conditions.parquet`
Generated reproducibly by a new script, consuming the immutable normalized M3 data.

## 13. Performance Considerations
The `dal.py` DuckDB connection is highly efficient. The new `/summary` endpoint will require querying three separate Parquet files for the `ORDER BY time DESC LIMIT 1` row. DuckDB optimizes `LIMIT 1` operations extremely well via Parquet row group statistics, so performance should comfortably remain in the ~35ms range.

## 14. Security Considerations
- Parameterized SQL will continue to be used via `dal.py` (`self._query(sql, [site_id])`).
- No raw file paths will be exposed in API responses.
- No new external APIs (like Gemini or LangGraph) are being introduced, meaning no API keys or `.env` files are exposed.

## 15. Backend Test Plan
- Add API unit tests for `/summary` and `/conditions` endpoints ensuring 200 OK and 404 behavior.
- Ensure the condition response schema is perfectly typed and distinct from alert responses.

## 16. Frontend Test Plan
- Update `App.test.tsx` (if applicable) to mock the new `/summary` endpoint and verify the neutral condition labels render without "drought" terminology.

## 17. Backward Compatibility Plan
- Existing `dal.py` methods and `candidate_sites.py` routes will not be modified or removed.
- Existing frontend components will continue to function. The condition/summary integration is purely additive.

## 18. Exact Implementation Files Expected to Change
1. `NEW/src/features/generate_conditions.py` (NEW FILE - offline generation)
2. `NEW/src/api/dal.py` (Add methods for `get_conditions` and `get_summary`)
3. `NEW/src/api/routes/candidate_sites.py` (Add new routes)
4. `NEW/tests/api/test_api.py` (Add new tests)
5. `NEW/frontend/src/services/api.ts` (Add API client methods)
6. `NEW/frontend/src/App.tsx` (or related sidebar UI components)

## 19. Exact Files That Must NOT Be Changed
- `NEW/src/features/conditions.py` (Logic is fully approved)
- `NEW/src/alerting/*`
- `NEW/src/models/*`
- Raw and processed M3/M6 data files.

## 20. Implementation Sub-Milestones
1. **Offline Artifact Generation:** Write and execute script to generate `data/conditions/*.parquet`.
2. **DAL & API Extension:** Add DuckDB queries and FastAPI routes for Conditions and Summaries.
3. **Frontend Integration:** Update UI strictly adhering to semantic rules.

## 21. Risks and Unresolved Questions
- **UI Space:** The sidebar may become crowded with both Alerts and Conditions. We will use clean, minimalist typography to ensure separation without clutter.
