# Milestone M10: Groundwater Drought Intelligence Engine

## Objective
To implement an Analytical Groundwater Drought Intelligence Engine based on historical groundwater deficit without conflating this index with official meteorological, agricultural, or government-declared drought statuses (such as the CGWB GWDI).

## Scientific Scope & Limitations

1. **Analytical Intelligence Signal ONLY:** This is an analytical tool mapping deep percentiles into deficit classifications. It is **NOT** an official government drought declaration.
2. **Independent of Climatological Drought:** This engine operates purely on groundwater observations. It does not ingest precipitation, temperature, or evapo-transpiration metrics.
3. **Regional Aggregation Requirement:** A groundwater deficit signal at a single point (borewell) can be driven by hyper-local factors (e.g., a broken sensor, intense localized pumping, well collapse). True drought signals are regionally coherent. Therefore, this engine aggregates deficits at the **District** level.
4. **Temporal Persistence Requirement:** Groundwater is a slow-reacting reservoir. A single seasonal deficit could indicate a delayed monsoon or localized anomaly. To qualify as a drought signal, the deficit must persist for **at least 2 consecutive analytical seasons**.
5. **Historical Constraint:** The CGWB explicitly requires 10 years of history for structural groundwater deficit (GWDI). This engine enforces a strict **10-year historical baseline** (e.g. at least 10 prior observations for the same season) at each site. Observations without this history are marked as `INSUFFICIENT_HISTORY`.
6. **Maharashtra Exclusion:** Based on the M10 Audit, Maharashtra telemetry data lacks the necessary 10-year historical baseline and is functionally excluded from drought characterization (automatically receiving `INSUFFICIENT_HISTORY`).

## Deficit Thresholds

- **P25 (25th Percentile):** Standard deficit boundary. Depths below this rank (meaning the water level is historically deeper than 75% of previous observations) contribute to the deficit count.
- **P10 (10th Percentile):** Extreme deficit boundary. Used in internal logging but the primary persistence trigger relies on P25.
*Note: Because raw water levels are measured as "Depth Below Ground Level" (BGL), a structurally larger number represents a deeper (drier) water table. The percentile calculation correctly inverts this relationship such that a "higher" raw number gets a "lower" percentile.*

## Spatial Aggregation and Statuses

The final drought intelligence statuses are applied based on the percentage of eligible sites in a district that are actively signaling consecutive deficits (>= 2 seasons):

- `MODERATE_DEFICIT`: > 33% (1/3) of eligible sites in the district show persistent deficit.
- `SEVERE_DEFICIT`: > 50% (1/2) of eligible sites in the district show persistent deficit.
- `WATCH`: A site is signaling persistent deficit, but the district-wide threshold (33%) has not been met.
- `NORMAL_TO_WET`: Normal conditions; no persistence requirement met.
- `INSUFFICIENT_HISTORY`: Site does not possess the 10 years of required historical reference for the observed season.

## Chronological Integrity
To strictly prevent data leakage (a core requirement of M3–M9), the engine calculates historical percentiles dynamically. For any given observation at time `t`, the engine ONLY considers data from time `t_0` to `t - 1`. Future values are strictly isolated and never pollute the statistical baseline.

## Extensibility
The engine exposes its computations gracefully to downstream ML models. It outputs `spatial_coverage_ratio`, `consecutive_deficit_seasons`, and boolean `groundwater_deficit_signal` flags which can be used as raw features for future time-series forecasting.
