# M12: Groundwater Stress Intelligence - Methodology

**Version:** M12-Stress-v1

## 1. Objective
The M12 module implements a transparent, multiple-evidence rules-based engine to measure **Structural Groundwater Stress** across multi-year baselines. It identifies long-term decline and persistent deficits that are unlikely to be corrected by a single wet season.

## 2. Stress vs. Scarcity
- **Scarcity** inherently requires evaluating demand vs. supply.
- **Stress** evaluates structural stability and availability in the physical resource.
- Because demand-side data (e.g., pumping, irrigation, population) is entirely absent from this project, this module explicitly produces a *Stress* signal, not a *Scarcity* signal.

## 3. Demand Data Limitation
The absence of demand-side and extraction data prevents direct inference of supply-demand scarcity or the physical cause of observed groundwater decline. The engine strictly hardcodes `demand_data_available = False`. 

## 4. Available Project Data
- **India Dataset:** Seasonal (4x/year) observations dating back to 1994. Includes `groundwater_percentile`, persistence counters, and enables multi-year trend calculation.
- **Maharashtra Dataset:** High-frequency telemetry (6-hourly) starting in 2023. Includes precipitation.

## 5. India Feasibility
The India dataset is highly feasible for structural stress analysis due to its 31-year depth, allowing valid OLS trend derivations and detection of persistent climatological shifts.

## 6. Maharashtra Limitation
The Maharashtra telemetry dataset has a baseline of ~3 years. Structural multi-year trend extraction and 4-season persistence logic cannot be statistically validated within this short window. Thus, Maharashtra observations are treated as having `INSUFFICIENT_EVIDENCE` for long-term structural stress.

## 7. Groundwater Percentile Methodology
The engine reuses the percentile logic from M10 (Drought), where low percentiles (e.g., P10, P25) mathematically map to historically deep (drier) water observations. This represents a relative historical deficit.

## 8. Persistent Deficit Methodology
To declare stress, the aquifer must exhibit a prolonged failure to recover. The requirement is configured to at least 4 consecutive analytical seasonal observations in deficit (P25).

## 9. Trend Methodology
Structural stress requires an underlying multi-year negative trend. The engine fits an Ordinary Least Squares (OLS) linear regression line across historical observations. 

## 10. Trend Orientation
Because `water_level_raw` represents depth below ground level (larger values = deeper water), a structurally declining/worsening aquifer exhibits a positive trend slope. The implementation maps `slope_per_year > 0` to a `DECREASING` condition (worsening stress).

## 11. District Aggregation
To filter out single-sensor mechanical failures, structural stress must exhibit spatial clustering. The engine computes the fraction of eligible sensors in the same district that are simultaneously exhibiting stress.

## 12. Spatial Threshold
The required district stress fraction is configured at `0.33` (approximately one-third). This is a project-configured analytical threshold, not a universal hydrological standard.

## 13. State Definitions
- **NORMAL:** Sufficient evidence exists, and the site does not meet stress criteria.
- **WATCH:** Persistent low groundwater condition (>= 4 seasons), but lacks a negative structural trend.
- **MODERATE_STRESS:** Persistent low groundwater condition AND a negative structural trend.
- **SEVERE_STRESS:** Severe persistent low groundwater (P10) AND a negative structural trend AND regional spatial clustering (>= 0.33).
- **INSUFFICIENT_EVIDENCE:** Insufficient valid history (< 5 years) to compute trend or persistence.

## 14. Weather-Context Separation
Weather data (e.g., rainfall) does not dictate stress. Structural stress can occur during normal rainfall due to extraction. Weather presence is reported as a metadata context flag only.

## 15. Leakage Prevention
Both percentiles and structural trends are computed using strictly expanding/backward-looking windows. The current observation is specifically excluded from its own reference baseline.

## 16. Quality Filtering
Observations flagged with `INVALID_OR_EMPTY`, `UNREALISTIC_WATER_LEVEL`, or `CONFLICTING_DUPLICATE` are excluded from the reference baselines for computing percentiles and trends.

## 17. Threshold Provenance
The boundaries `P25`, `P10`, and `0.33` are project-configured analytical thresholds. They are NOT regulatory thresholds, official groundwater limits, CGWB declarations, or universal hydrological thresholds.

## 18. Scientific Limitations
- Lack of pumping data means we cannot distinguish between natural climate shifts and human over-extraction.
- "Stress" represents a relative historical position, not an absolute volumetric measurement of remaining water.

## 19. Explicit Non-Claims
M12 provides project-specific analytical groundwater stress intelligence. It does not declare official water scarcity, drinking-water shortage, irrigation shortage, administrative drought, or regulatory groundwater status.
