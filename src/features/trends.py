"""
NEW/src/features/trends.py - Trend Analysis for Groundwater Data

Purpose:
- Compute location-specific trends using transparent statistical methods.
- Rate of change calculations.
- No unsupported physical interpretations (e.g., "groundwater depletion").

Scientific Constraints:
- Use neutral terminology: "declining observed water-level trend" not
  "groundwater level is falling by X meters."
- Reference datum is UNKNOWN for both datasets, so absolute physical
  interpretations are not supported.
- Document minimum observations required for each method.
- Handle missing values explicitly.
- Handle insufficient data gracefully.
"""

from typing import Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats


def compute_location_trend(
    df: pd.DataFrame,
    site_col: str = "candidate_site_id",
    date_col: str = "observation_date",
    value_col: str = "water_level_raw",
    min_observations: int = 10,
    min_years_span: int = 3,
) -> pd.DataFrame:
    """
    Computes linear trend per monitoring location using ordinary least squares.

    Method:
    - Fits a simple linear regression of water_level_raw ~ days_since_first_obs.
    - Reports slope (units per day), p-value, R-squared, and standard error.
    - Only computes trends for locations with >= min_observations spanning
      >= min_years_span years.

    Limitations:
    - OLS assumes approximately linear trend, which may not hold for all sites.
    - Missing values are excluded from fit.
    - Duplicate/conflicting observations on the same date are included
      (filtered by quality flags upstream).
    - Slope sign depends on water_level_raw semantics, which are UNKNOWN.

    Parameters
    ----------
    df : pd.DataFrame
        Normalized dataset with site, date, and value columns.
    site_col : str
        Location identifier column.
    date_col : str
        Date column (string, parsed to datetime internally).
    value_col : str
        Water level column.
    min_observations : int
        Minimum non-null observations required. Default 10.
    min_years_span : int
        Minimum years between first and last observation. Default 3.

    Returns
    -------
    pd.DataFrame
        One row per site: slope_per_day, slope_per_year, intercept,
        r_squared, p_value, std_error, obs_count, year_span,
        trend_direction.
    """
    work = df[[site_col, date_col, value_col]].copy()
    work["_date"] = pd.to_datetime(work[date_col], errors="coerce")
    work = work.dropna(subset=["_date", value_col])

    records = []
    for site, group in work.groupby(site_col):
        if len(group) < min_observations:
            continue

        sorted_g = group.sort_values("_date")
        date_range = sorted_g["_date"].max() - sorted_g["_date"].min()
        year_span = date_range.days / 365.25

        if year_span < min_years_span:
            continue

        # Convert dates to numeric (days since first observation)
        first_date = sorted_g["_date"].min()
        x = (sorted_g["_date"] - first_date).dt.total_seconds() / 86400  # days
        y = sorted_g[value_col].values

        # OLS linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        # Direction (neutral terminology)
        if p_value < 0.05:
            if slope > 0:
                direction = "INCREASING"
            elif slope < 0:
                direction = "DECREASING"
            else:
                direction = "STABLE"
        else:
            direction = "NOT_SIGNIFICANT"

        records.append({
            site_col: site,
            "slope_per_day": round(float(slope), 8),
            "slope_per_year": round(float(slope * 365.25), 6),
            "intercept": round(float(intercept), 4),
            "r_squared": round(float(r_value ** 2), 4),
            "p_value": round(float(p_value), 6),
            "std_error": round(float(std_err), 8),
            "obs_count": len(group),
            "year_span": round(float(year_span), 1),
            "trend_direction": direction,
            "method": "OLS_LINEAR",
            "min_observations_used": min_observations,
            "min_years_span_used": min_years_span,
        })

    return pd.DataFrame(records)


def compute_rate_of_change(
    df: pd.DataFrame,
    site_col: str = "candidate_site_id",
    date_col: str = "observation_date",
    value_col: str = "water_level_raw",
) -> pd.DataFrame:
    """
    Computes observation-to-observation rate of change for each site.

    For each site, sorts observations chronologically and computes:
    - change = current_value - previous_value
    - days_between = days between current and previous observation
    - rate_per_day = change / days_between

    This is strictly backward-looking: each observation references only
    the immediately preceding observation at the same site.

    Parameters
    ----------
    df : pd.DataFrame
        Normalized dataset with site, date, and value columns.
    site_col : str
        Location identifier column.
    date_col : str
        Date column.
    value_col : str
        Water level column.

    Returns
    -------
    pd.DataFrame
        Copy of input with `wl_change`, `days_since_prev`, `rate_per_day` added.
        First observation per site has NaN for these fields.
    """
    df_out = df.copy()
    df_out["_parsed_date"] = pd.to_datetime(df_out[date_col], errors="coerce")

    # Sort by site and date
    df_out = df_out.sort_values([site_col, "_parsed_date"]).reset_index(drop=True)

    # Within each site, compute differences
    df_out["wl_change"] = df_out.groupby(site_col)[value_col].diff()
    df_out["days_since_prev"] = (
        df_out.groupby(site_col)["_parsed_date"]
        .diff()
        .dt.total_seconds() / 86400
    )

    # Rate per day (avoid division by zero)
    safe_days = df_out["days_since_prev"].replace(0, np.nan)
    df_out["rate_per_day"] = df_out["wl_change"] / safe_days

    # Clean up
    df_out = df_out.drop(columns=["_parsed_date"])

    return df_out
