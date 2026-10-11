"""
NEW/src/features/baselines.py - Baseline Analytics for Future ML Evaluation

Purpose:
- Establish transparent, simple baselines BEFORE any ML forecasting.
- Persistence baseline: next value = previous value.
- Seasonal historical baseline for India: prediction = historical seasonal mean.
- Maharashtra persistence baseline based on telemetry structure.

Scientific Constraints:
- NO ML model training in this milestone.
- NO random train/test splitting.
- Chronological ordering strictly preserved.
- Baselines are backward-looking only (no future information).
- Baselines document what they predict, what is available at prediction time,
  and their limitations.
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd


def compute_persistence_baseline(
    df: pd.DataFrame,
    site_col: str = "candidate_site_id",
    date_col: str = "observation_date",
    value_col: str = "water_level_raw",
) -> pd.DataFrame:
    """
    Persistence baseline for India periodic data:
        predicted_value = previous observation at the same site.

    This is the simplest possible baseline. For periodic data with irregular
    temporal spacing, the "previous observation" may be weeks or months old.

    Information available at prediction time:
    - All observations at the same site with dates strictly before the target date.
    - The most recent such observation is used as the prediction.

    Limitations:
    - Does not account for seasonal patterns.
    - Temporal gap between prediction and most recent observation varies widely
      (median ~78-92 days for well-monitored sites).
    - Performance degrades for sites with very few observations.

    Parameters
    ----------
    df : pd.DataFrame
        Normalized dataset sorted chronologically per site.
    site_col : str
        Location identifier.
    date_col : str
        Date column.
    value_col : str
        Water level column.

    Returns
    -------
    pd.DataFrame
        Copy of input with `persistence_prediction` and
        `persistence_residual` added. First observation per site
        has NaN prediction (no prior observation available).
    """
    df_out = df.copy()
    df_out["_parsed_date"] = pd.to_datetime(df_out[date_col], errors="coerce")

    # Sort chronologically within each site
    df_out = df_out.sort_values([site_col, "_parsed_date"]).reset_index(drop=True)

    # Persistence: prediction = previous value at same site
    df_out["persistence_prediction"] = df_out.groupby(site_col)[value_col].shift(1)

    # Residual: actual - predicted
    df_out["persistence_residual"] = (
        df_out[value_col] - df_out["persistence_prediction"]
    )

    df_out = df_out.drop(columns=["_parsed_date"])
    return df_out


def compute_seasonal_historical_baseline(
    df: pd.DataFrame,
    site_col: str = "candidate_site_id",
    season_col: str = "analytical_season",
    year_col: str = "observation_year",
    value_col: str = "water_level_raw",
    min_historical_years: int = 3,
) -> pd.DataFrame:
    """
    Seasonal historical baseline for India periodic data:
        predicted_value = mean of all PREVIOUS years' observations
                          at the same site and season.

    This baseline is strictly backward-looking:
    - For year Y, the baseline uses only observations from years < Y.
    - This prevents future leakage.

    Information available at prediction time:
    - Historical observations at the same site in the same season from
      all previous years.

    Limitations:
    - Requires >= min_historical_years of prior seasonal data.
    - Assumes stationarity of seasonal patterns (may not hold for
      locations with long-term trends).
    - Performance depends on seasonal consistency.

    Parameters
    ----------
    df : pd.DataFrame
        Dataset with season labels and year.
    site_col, season_col, year_col, value_col : str
        Column names.
    min_historical_years : int
        Minimum number of prior years required. Default 3.

    Returns
    -------
    pd.DataFrame
        Copy of input with `seasonal_hist_prediction`, `seasonal_hist_residual`,
        `seasonal_hist_years_used`, and `seasonal_hist_available` added.
    """
    df_out = df.copy()
    df_out[year_col] = pd.to_numeric(df_out[year_col], errors="coerce")

    # Vectorized computation
    df_out = df_out.sort_values([site_col, season_col, year_col]).reset_index(drop=True)

    # Calculate average value per year to ensure equal weighting and proper year-based shifting
    annual_seasonal = df_out.groupby([site_col, season_col, year_col], as_index=False)[value_col].mean()
    annual_seasonal = annual_seasonal.sort_values([site_col, season_col, year_col])

    # Compute expanding sum and count over strictly prior years (shifted by 1)
    # Using cumsum() and cumcount() is magnitudes faster than apply()
    annual_seasonal["hist_sum"] = annual_seasonal.groupby([site_col, season_col])[value_col].cumsum() - annual_seasonal[value_col]
    annual_seasonal["hist_count"] = annual_seasonal.groupby([site_col, season_col]).cumcount()


    annual_seasonal["seasonal_hist_prediction"] = annual_seasonal["hist_sum"] / annual_seasonal["hist_count"]
    annual_seasonal["seasonal_hist_years_used"] = annual_seasonal["hist_count"].fillna(0).astype(int)

    # Merge back to original granularity
    df_out = df_out.merge(
        annual_seasonal[[site_col, season_col, year_col, "seasonal_hist_prediction", "seasonal_hist_years_used"]],
        on=[site_col, season_col, year_col],
        how="left"
    )

    df_out["seasonal_hist_available"] = df_out["seasonal_hist_years_used"] >= min_historical_years
    df_out.loc[~df_out["seasonal_hist_available"], "seasonal_hist_prediction"] = np.nan
    df_out["seasonal_hist_residual"] = np.where(
        df_out["seasonal_hist_available"],
        df_out[value_col] - df_out["seasonal_hist_prediction"],
        np.nan,
    )

    return df_out


def compute_maharashtra_persistence_baseline(
    df: pd.DataFrame,
    station_col: str = "station_name",
    timestamp_col: str = "observation_timestamp",
    value_col: str = "water_level_raw",
) -> pd.DataFrame:
    """
    Persistence baseline for Maharashtra telemetry data:
        predicted_value = previous observation at the same station.

    For continuous 6-hourly telemetry, the "previous observation" is typically
    6 hours prior (when data is continuous).

    Information available at prediction time:
    - The most recent prior observation at the same station.

    Limitations:
    - Gaps in telemetry may mean the "previous" observation is significantly older.
    - Simple persistence does not capture diurnal or multi-day patterns.

    Parameters
    ----------
    df : pd.DataFrame
        Normalized Maharashtra dataset.
    station_col : str
        Station identifier column.
    timestamp_col : str
        Timestamp column.
    value_col : str
        Water level column.

    Returns
    -------
    pd.DataFrame
        Copy of input with `persistence_prediction` and
        `persistence_residual` added.
    """
    df_out = df.copy()
    df_out["_parsed_ts"] = pd.to_datetime(df_out[timestamp_col], errors="coerce")

    # Sort chronologically per station
    df_out = df_out.sort_values([station_col, "_parsed_ts"]).reset_index(drop=True)

    # Persistence prediction
    df_out["persistence_prediction"] = df_out.groupby(station_col)[value_col].shift(1)
    df_out["persistence_residual"] = (
        df_out[value_col] - df_out["persistence_prediction"]
    )

    df_out = df_out.drop(columns=["_parsed_ts"])
    return df_out


def compute_baseline_evaluation_metrics(
    residuals: pd.Series,
    baseline_name: str = "baseline",
) -> Dict[str, Any]:
    """
    Computes standard evaluation metrics from baseline residuals.

    Metrics:
    - MAE (Mean Absolute Error)
    - RMSE (Root Mean Squared Error)
    - MedAE (Median Absolute Error)
    - Bias (Mean Error, signed)
    - Count of evaluable observations

    Parameters
    ----------
    residuals : pd.Series
        Residual series (actual - predicted). NaN values are excluded.
    baseline_name : str
        Name for reporting.

    Returns
    -------
    Dict[str, Any]
        Evaluation metrics.
    """
    valid = residuals.dropna()
    if len(valid) == 0:
        return {
            "baseline": baseline_name,
            "evaluable_observations": 0,
            "mae": None,
            "rmse": None,
            "median_ae": None,
            "bias": None,
        }

    abs_errors = valid.abs()
    return {
        "baseline": baseline_name,
        "evaluable_observations": int(len(valid)),
        "mae": round(float(abs_errors.mean()), 4),
        "rmse": round(float(np.sqrt((valid ** 2).mean())), 4),
        "median_ae": round(float(abs_errors.median()), 4),
        "bias": round(float(valid.mean()), 4),
    }
