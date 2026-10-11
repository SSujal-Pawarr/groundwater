# M8.2-D Groundwater Condition Engine: Implementation Results

**STATUS:** IMPLEMENTATION COMPLETE

## 1. Implementation Files
- **Logic:** `NEW/src/features/conditions.py`
- **Tests:** `NEW/tests/test_m82d_conditions.py`

## 2. Methodology
The engine calculates absolute statistical groundwater conditions based on the **Historical Percentile Rank** methodology approved in the M8.2-D assessment. 

The implementation uses an expanding window (strictly backward-looking) to calculate the percentile rank. For any given observation at time *t*, the reference distribution is constructed strictly from observations occurring *before t*. This completely eliminates future data leakage.

### Percentile Thresholds
The following statistical classification boundaries were implemented strictly as requested:
- `< 10th percentile:` `EXTREMELY_LOW`
- `10th - 25th percentile:` `LOW`
- `25th - 75th percentile:` `NORMAL_RANGE`
- `75th - 90th percentile:` `HIGH`
- `> 90th percentile:` `EXTREMELY_HIGH`

**Important Scientific Note:** These are neutral statistical labels describing historical relative distribution. They are NOT synonymous with "Drought", "Flood", or "Scarcity", which require external socio-economic context not present in the dataset.

## 3. Dataset Semantics

### India (Periodic Observations)
- **Grouping:** `candidate_site_id` + `analytical_season`
- **Rationale:** Ensures that PRE_MONSOON observations are only ranked against historical PRE_MONSOON observations, preventing the dry season from being structurally classified as `LOW` when compared to annual data.

### Maharashtra (Telemetry)
- **Grouping:** `candidate_site_id` + `observation_month` (e.g. `MONTH_05` for May).
- **Rationale:** High-frequency telemetry provides sufficient data density to create a distinct historical distribution for every calendar month, enabling granular, near real-time condition tracking.

## 4. Eligibility and Data Quality Handling
- **Minimum History:** A threshold of `min_history=5` valid historical observations was implemented. Observations with `<5` prior valid references evaluate to `INSUFFICIENT_HISTORY`.
- **Quality Gates:** Records flagged with `INVALID_OR_EMPTY`, `UNREALISTIC_WATER_LEVEL`, or `CONFLICTING_DUPLICATE` are strictly excluded from the historical reference distribution. They will not skew the percentiles.
- **Statistically Extreme Valid Records:** Plausible but extremely large variations (e.g. valid -1791m readings) are kept in the distribution. Due to the non-parametric nature of percentiles, these extremes do not distort the `NORMAL_RANGE` for typical readings.

## 5. Output Schema
The implementation computes the following deterministic fields:
1. `condition_state`: Enum (e.g., `NORMAL_RANGE`, `INSUFFICIENT_HISTORY`)
2. `percentile`: Float [0.0 - 100.0] representing exact historical rank.
3. `historical_reference_group`: Grouping key (e.g., `PRE_MONSOON` or `MONTH_11`).
4. `historical_sample_count`: Integer count of strictly prior, valid observations used.
5. `condition_method_version`: Locked to `M8.2-D-v1`.

## 6. Testing and Regression Validation
- **New Tests (`test_m82d_conditions.py`):** 12 dedicated unit tests were written covering precise boundaries, India vs Maharashtra semantics, data quality masking, missing values, deterministic execution, and a strict **anti-leakage** test verifying that inserting a massive future outlier does not alter the historical percentiles.
- **Full Project Regression:** All 71 `NEW/tests/` completed with a 100% pass rate. 
- M3, M4, M5, M6, and M7 remain untouched and fully functioning.

## 7. Limitations and Future Work
- The condition engine operates independently of the M8.2-C Weather ML forecasting model. ML models predict the *future* state, whereas the condition engine classifies the *current* factual state. They must not be conflated.
- The condition engine currently outputs raw dataset values and statistical distributions. If the business desires interpretative labels ("Drought"), a separate M8.2-E rule engine (requiring socio-economic parameters) will be required. 

**M8.2-D IMPLEMENTATION COMPLETE**
