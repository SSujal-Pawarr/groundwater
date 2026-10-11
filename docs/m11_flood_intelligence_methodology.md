# M11: Groundwater Flood Potential Intelligence - Methodology

**Version:** M11-FloodPotential-v1

## 1. Core Scientific Principle

The M11 Groundwater Flood Potential engine strictly calculates **Analytical Flood Potential**. It is fundamentally constrained by the following principles:

1. **Not a Physical Flood Warning:** High groundwater levels do not automatically indicate physical surface flooding. Flood mapping requires high-resolution topographical data (DEM), floodplains, and river gauge data, none of which are present in this dataset.
2. **Multiple Evidence Engine:** A state of "HIGH" potential requires the simultaneous intersection of multiple causal criteria: historically elevated groundwater, extreme antecedent precipitation, steep acute groundwater rise, and regional spatial clustering.
3. **No Supervised Machine Learning:** There is no "ground-truth" flood label in the historical dataset. Training an XGBoost or Random Forest model to predict arbitrary high-water thresholds as "flooding" constitutes data fabrication.
4. **Strict Temporal Segregation:** Any climatic evidence used to evaluate groundwater at time $T$ must have occurred strictly before or exactly at $T$. Future rainfall cannot retroactively cause a flood.

## 2. Dataset Scope

### 2.1 Maharashtra (Primary Telemetry)
- **Feasibility:** Maharashtra telemetry provides high-frequency observations and is integrated with ERA5 precipitation data, allowing the detection of acute surface loading events. 
- **Limitation:** The baseline history is extremely short (~3 years). The percentiles used represent historical relative positions in a small statistical sample rather than deep climatological extremes.

### 2.2 India (Seasonal Data)
- **Feasibility:** India data consists of low-frequency (4x per year) seasonal observations without integrated precipitation data.
- **Implementation:** Acute rainfall-triggered flood potential is unsupportable. The engine explicitly returns `INSUFFICIENT_EVIDENCE` for all India records regarding acute flood potential.

## 3. Evidence Components & Analytical Thresholds

The following project-configured analytical thresholds are used to evaluate flood potential. These are transparent, configurable thresholds rather than universal scientific laws.

1. **Historically Elevated Groundwater Position:**
   - **Threshold:** `groundwater_percentile >= 85.0`
   - *Note:* The raw M8.2-D percentile logic computed higher percentiles for deeper water. For M11, this is analytically inverted so that `groundwater_percentile` has explicitly documented semantics: **higher value = historically wetter/shallower groundwater position**. `100.0` represents the shallowest (wettest) reading on record.

2. **Antecedent Precipitation:**
   - **Threshold:** `precip_sum_7d >= 10.0 mm`
   - *Justification:* This is exactly a **project-configured statistical threshold** derived from the observed Maharashtra dataset distribution (representing >99th percentile of this specific dataset). 
   - *Disclaimer:* It MUST NOT be interpreted as a universal intense-rainfall threshold, a regulatory threshold, or a meteorological standard.

3. **Groundwater Rise Rate:**
   - **Threshold:** `groundwater_rise_rate >= 0.5 meters/day`
   - *Justification:* Represents an acute, steep spike in the water table associated with intense recharge rather than slow seasonal drift.

4. **Regional Spatial Clustering:**
   - **Threshold:** `spatial_elevated_fraction >= 0.25`
   - *Justification:* At least 25% of valid active sites in the same district must exhibit elevated groundwater on the same day. This ensures a single broken sensor (e.g., a localized mechanical collapse) cannot trigger a regional flood state.

## 4. State Classification Engine

The transparent rules-based state machine escalates only when cascading evidence criteria are met:

- **LOW:** Base state. Insufficient evidence for elevated potential.
- **WATCH:** The aquifer is near capacity (`groundwater_percentile >= 85.0`).
- **ELEVATED:** The aquifer is near capacity AND there is intense antecedent rainfall (`precip_sum_7d >= 10.0`).
- **HIGH:** Multiple strong evidence components are active: aquifer near capacity, intense rainfall, steep groundwater rise (`rise_rate >= 0.5 m/d`), AND the event is regionally clustered (`spatial_elevated_fraction >= 0.25`).
- **INSUFFICIENT_EVIDENCE:** Essential evidence is unavailable, data is disqualified by quality flags, or the dataset is ineligible (e.g., India).

## 5. Output Schema

The engine explicitly exposes transparent intermediate evidence fields instead of an opaque black-box score:
- `flood_potential_state`
- `evidence_count`
- `groundwater_percentile`
- `groundwater_elevated_flag`
- `groundwater_rise_rate`
- `groundwater_rise_flag`
- `precipitation_trigger_flag`
- `spatial_elevated_fraction`
- `spatial_trigger_flag`
- `weather_data_available`

## 6. Scientific Limitations
- **Topography Missing:** "Elevated potential" does not guarantee water is above the ground surface.
- **Sensor Glitches:** Despite spatial clustering, extreme telemetry artifacts (e.g., `-1791m` mechanical errors) require ongoing dataset quality surveillance.
- **Retrospective Nature:** This intelligence serves as retrospective analytics. Without real-time weather integration, it cannot be used for forward-looking operational early warning.
