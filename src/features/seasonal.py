"""
NEW/src/features/seasonal.py - Seasonal Feature Engineering for India Groundwater Data

Purpose:
- Assign seasonal labels based on actual observation months.
- Compute seasonal statistics (mean, median, std, min, max) per location.
- Compute seasonal anomalies from location-specific historical baselines.
- Compute year-over-year seasonal changes.

Scientific Constraints:
- Seasonal labels are derived from observation months, NOT assumed to be
  physically meaningful without documentation.
- Only months actually observed are used: [1, 3, 4, 5, 8, 11].
- If a feature requires complete seasonal coverage, the function documents
  how much data satisfies that requirement.
- Do not treat seasonal labels as official CGWB season codes without
  authoritative documentation.

Seasonal Mapping (based on observed months and standard Indian groundwater practice):
  Month 1  (January)  -> RABI_WINTER (post-monsoon / winter recharge period)
  Month 3  (March)    -> PRE_MONSOON_EARLY (limited data, early pre-monsoon)
  Month 4  (April)    -> PRE_MONSOON (dry season, lowest water tables)
  Month 5  (May)      -> PRE_MONSOON (dry season, lowest water tables)
  Month 8  (August)   -> MONSOON (peak recharge period)
  Month 11 (November) -> POST_MONSOON (post-monsoon, high water tables)

NOTE: This mapping is an analytical convenience label based on Indian
meteorological conventions. It is NOT an official CGWB seasonal classification
until provenance is established.
"""

from typing import Dict, Any, Optional, List
import numpy as np
import pandas as pd


# Analytical season mapping based on observed months and Indian meteorological conventions
INDIA_MONTH_TO_SEASON: Dict[int, str] = {
    1: "RABI_WINTER",
    3: "PRE_MONSOON_EARLY",
    4: "PRE_MONSOON",
    5: "PRE_MONSOON",
    8: "MONSOON",
    11: "POST_MONSOON",
}


def assign_india_season(df: pd.DataFrame) -> pd.DataFrame:
    """
    Assigns analytical season labels to India periodic observations based on
    observation_month.

    Parameters
    ----------
    df : pd.DataFrame
        Normalized India dataset with `observation_month`.

    Returns
    -------
    pd.DataFrame
        Copy with `analytical_season` column added.
        Months not in the mapping receive `UNMAPPED_MONTH`.
    """
    df_out = df.copy()
    df_out["analytical_season"] = (
        df_out["observation_month"]
        .map(INDIA_MONTH_TO_SEASON)
        .fillna("UNMAPPED_MONTH")
    )
    df_out["season_is_analytical_label"] = True
    return df_out


def compute_seasonal_statistics(
    df: pd.DataFrame,
    site_col: str = "candidate_site_id",
    season_col: str = "analytical_season",
    value_col: str = "water_level_raw",
    min_observations: int = 3,
) -> pd.DataFrame:
    """
    Computes per-site, per-season summary statistics.

    For each (site, season) group with at least `min_observations`:
    - mean, median, std, min, max
    - count of observations
    - count of unique years contributing

    Parameters
    ----------
    df : pd.DataFrame
        Dataset with season labels assigned.
    site_col : str
        Column for location grouping.
    season_col : str
        Column with season labels.
    value_col : str
        Water level column.
    min_observations : int
        Minimum observations required to compute statistics. Default 3.

    Returns
    -------
    pd.DataFrame
        One row per (site, season) with summary statistics.
        Only groups meeting min_observations are included.
    """
    work = df.dropna(subset=[value_col]).copy()

    grouped = work.groupby([site_col, season_col]).agg(
        seasonal_mean=(value_col, "mean"),
        seasonal_median=(value_col, "median"),
        seasonal_std=(value_col, "std"),
        seasonal_min=(value_col, "min"),
        seasonal_max=(value_col, "max"),
        seasonal_obs_count=(value_col, "count"),
        seasonal_unique_years=("observation_year", "nunique"),
    ).reset_index()

    # Filter by minimum observations
    result = grouped[grouped["seasonal_obs_count"] >= min_observations].copy()
    result["min_observations_threshold"] = min_observations

    return result


def compute_seasonal_anomaly(
    df: pd.DataFrame,
    seasonal_stats: pd.DataFrame,
    site_col: str = "candidate_site_id",
    season_col: str = "analytical_season",
    value_col: str = "water_level_raw",
) -> pd.DataFrame:
    """
    Computes seasonal anomaly as the deviation of each observation from its
    location-specific historical seasonal mean.

    anomaly = observation - historical_seasonal_mean

    Only observations that have a corresponding seasonal baseline are annotated.
    The historical baseline uses ALL available historical observations for that
    site and season (no future leakage since the baseline is computed from the
    full historical record, not from future years of data).

    NOTE ON LEAKAGE: For true out-of-sample evaluation, the baseline should
    exclude the target year. This function computes the overall historical
    baseline for characterization purposes. For prediction evaluation, use
    the baseline utilities in baselines.py instead.

    Parameters
    ----------
    df : pd.DataFrame
        Dataset with season labels.
    seasonal_stats : pd.DataFrame
        Output of compute_seasonal_statistics().
    site_col : str
        Location column.
    season_col : str
        Season column.
    value_col : str
        Water level column.

    Returns
    -------
    pd.DataFrame
        Copy of input with `seasonal_anomaly` and `seasonal_anomaly_pct` added.
    """
    df_out = df.copy()

    # Merge seasonal means
    baseline = seasonal_stats[[site_col, season_col, "seasonal_mean", "seasonal_std"]].copy()
    baseline = baseline.rename(columns={
        "seasonal_mean": "_hist_seasonal_mean",
        "seasonal_std": "_hist_seasonal_std",
    })

    df_out = df_out.merge(baseline, on=[site_col, season_col], how="left")

    # Compute anomaly only where we have both a value and a baseline
    has_both = df_out[value_col].notna() & df_out["_hist_seasonal_mean"].notna()
    df_out["seasonal_anomaly"] = np.where(
        has_both,
        df_out[value_col] - df_out["_hist_seasonal_mean"],
        np.nan,
    )

    # Percentage anomaly relative to mean
    safe_mean = df_out["_hist_seasonal_mean"].replace(0, np.nan)
    df_out["seasonal_anomaly_pct"] = np.where(
        has_both & safe_mean.notna(),
        (df_out[value_col] - df_out["_hist_seasonal_mean"]) / safe_mean * 100,
        np.nan,
    )

    # Drop internal merge columns
    df_out = df_out.drop(columns=["_hist_seasonal_mean", "_hist_seasonal_std"])

    return df_out


def compute_yoy_seasonal_change(
    df: pd.DataFrame,
    site_col: str = "candidate_site_id",
    season_col: str = "analytical_season",
    value_col: str = "water_level_raw",
    year_col: str = "observation_year",
) -> pd.DataFrame:
    """
    Computes year-over-year change in seasonal water level for each site.

    For each (site, season, year), computes the mean water level, then
    calculates the difference from the previous year's mean for the same
    site and season.

    This is strictly backward-looking: each year's change references only
    the immediately preceding year.

    Parameters
    ----------
    df : pd.DataFrame
        Dataset with season labels and year.
    site_col, season_col, value_col, year_col : str
        Column names.

    Returns
    -------
    pd.DataFrame
        Per (site, season, year): yearly_mean, yoy_change, yoy_change_pct.
    """
    work = df.dropna(subset=[value_col, year_col]).copy()
    work[year_col] = work[year_col].astype(int)

    # Annual seasonal means
    annual_seasonal = (
        work.groupby([site_col, season_col, year_col])[value_col]
        .mean()
        .reset_index()
        .rename(columns={value_col: "yearly_seasonal_mean"})
    )
    annual_seasonal = annual_seasonal.sort_values([site_col, season_col, year_col])

    # YoY change (backward-looking: current - previous year)
    annual_seasonal["yoy_change"] = (
        annual_seasonal
        .groupby([site_col, season_col])["yearly_seasonal_mean"]
        .diff(1)
    )

    # YoY change percentage
    prev_year_mean = (
        annual_seasonal
        .groupby([site_col, season_col])["yearly_seasonal_mean"]
        .shift(1)
    )
    annual_seasonal["yoy_change_pct"] = np.where(
        prev_year_mean.notna() & (prev_year_mean != 0),
        annual_seasonal["yoy_change"] / prev_year_mean * 100,
        np.nan,
    )

    return annual_seasonal
