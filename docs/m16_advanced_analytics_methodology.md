# M16 Advanced Groundwater Analytics Methodology

## Overview
The M16 Advanced Analytics layer provides deterministic statistical and historical views over the Groundwater Intelligence project's generated artifacts. It does not introduce new machine learning models, composite risk scores, or re-calculations of existing module thresholds (M10 drought, M11 flood, M12 stress).

## Site Analytics
Calculates deterministic observation counts, first/last observation dates, missing data proportions, and descriptive statistics (mean, median, standard deviation, and key percentiles: p10, p25, p50, p75, p90) directly from validated telemetry.

## Percentile Trajectory
To strictly avoid target leakage (data from the future influencing the past), the historical percentile of each observation is computed solely against the distribution of observations that strictly precede it. The first observation has a percentile of `None`.

## Trend Methodology
Uses the existing `compute_location_trend` method via Ordinary Least Squares (OLS) regression over days since the first observation. Requires a minimum of 10 observations spanning at least 3 years. It outputs the slope (trend rate), $R^2$, and p-value. The direction is expressed using neutral terminology (e.g. INCREASING, DECREASING, STABLE).

## Seasonal Analytics
Relies on `compute_analytical_season` from M4 spatial/temporal boundaries. Groups data by analytical season (e.g., PRE_MONSOON, MONSOON, POST_MONSOON) to provide seasonal medians and inter-annual comparisons.

## Year-Over-Year (YoY) Methodology
Calculates the difference between the most recent observation and the observation from the exact same analytical season in the immediately preceding year. Ensures comparisons are apples-to-apples despite periodic sampling frequencies.

## District Aggregation
Calculates proportional distributions of condition states (NORMAL_RANGE, LOW, etc.), alert states, and intelligence states (Drought, Flood, Stress) across all candidate sites within a specific district. Does not mathematically average distinct sites' water levels to avoid spurious physical interpretations. 

## Data-Quality Handling
Highlights valid vs. invalid observation counts. Data flagged as invalid by upstream QA/QC processes (M5) are dropped before computing descriptive statistics or trends, but counted for diagnostic visibility.

## India vs Maharashtra Temporal Differences
- **India Dataset**: Represents periodic, historical, and highly seasonal data. Expected cadences are generally 4 times a year. YoY analytics rely on analytical season matching rather than exact calendar dates.
- **Maharashtra Dataset**: Provides higher-frequency telemetry (hourly or daily). Support rate-of-change per day.
Do not imply equivalent temporal resolution or force them onto a single shared temporal interpolation grid.

## Limitations
- Analytics are only calculated where data history is sufficient. 
- Units are `meters` for Maharashtra. For India, the absolute unit (mbgl vs msl) is treated as UNKNOWN strictly unless established otherwise.
- There is no composite "risk score" as different intelligence outputs measure fundamentally different phenomenologies (e.g., condition vs drought).
