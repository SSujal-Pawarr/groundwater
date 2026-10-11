"""
NEW/src/features/anomaly.py - Standardized Anomaly / Index Features

Purpose:
- Investigate whether an SGI-like standardized index is scientifically justified.
- Implement a defensible seasonal_z_score as a simpler alternative.

Scientific Decision on SGI:
After analyzing the India dataset temporal structure:
- Observations occur in only 6 months: [1, 3, 4, 5, 8, 11]
- Month 3 (March) has very few observations (7,296 out of 1.5M).
- Observation frequency is irregular (not monthly).
- Many sites have incomplete seasonal coverage across years.
- The data does not support the standard SGI methodology which requires
  regular monthly observations with sufficient sample sizes per month.

CONCLUSION: SGI is NOT scientifically justified for this dataset.

Instead, a simpler `seasonal_z_score` is implemented:
  z = (observation - seasonal_mean) / seasonal_std
This is clearly documented as a statistical anomaly measure, NOT an
official drought or groundwater stress index.
"""

from typing import Optional
import numpy as np
import pandas as pd


# SGI rejection documentation
SGI_REJECTION_REASON = """
SGI (Standardized Groundwater Index) is NOT scientifically justified for this dataset.

Reasons:
1. TEMPORAL IRREGULARITY: Observations occur in only 6 months [1, 3, 4, 5, 8, 11],
   not the monthly frequency required by standard SGI methodology.
2. INSUFFICIENT MONTH 3 DATA: Only 7,296 observations in March (0.47% of total),
   making March seasonal statistics unreliable for many sites.
3. INCOMPLETE COVERAGE: Many sites lack observations for all seasons across all years,
   violating the assumption of comparable seasonal distributions needed for SGI.
4. UNKNOWN REFERENCE DATUM: Without confirmed physical meaning of the water level
   values, the standardized index cannot be reliably interpreted as a groundwater
   stress indicator.
5. MIXED OBSERVATION TYPES: Pre-monsoon vs monsoon vs post-monsoon observations
   represent fundamentally different hydrological states. SGI typically requires
   within-month standardization, not within-season standardization.

Alternative implemented: seasonal_z_score (simple standardized anomaly within
each location-season group), clearly documented as a statistical measure,
not a drought or stress index.
"""


def compute_seasonal_z_score(
    df: pd.DataFrame,
    site_col: str = "candidate_site_id",
    season_col: str = "analytical_season",
    value_col: str = "water_level_raw",
    min_observations: int = 5,
) -> pd.DataFrame:
    """
    Computes a seasonal z-score for each observation:

        z = (observation - location_season_mean) / location_season_std

    This is a simple standardized anomaly, NOT an official drought index.

    Requirements:
    - Only computed where the (site, season) group has >= min_observations.
    - Uses the FULL historical record for that (site, season). For true
      out-of-sample evaluation, use the baseline utilities in baselines.py.

    Parameters
    ----------
    df : pd.DataFrame
        Dataset with season labels and water level values.
    site_col : str
        Location identifier column.
    season_col : str
        Season label column.
    value_col : str
        Water level column.
    min_observations : int
        Minimum observations in (site, season) group. Default 5.

    Returns
    -------
    pd.DataFrame
        Copy of input with `seasonal_z_score` and `seasonal_z_score_available`
        columns added.
    """
    df_out = df.copy()

    # Compute group statistics
    group_stats = (
        df_out.groupby([site_col, season_col])[value_col]
        .agg(["mean", "std", "count"])
        .reset_index()
        .rename(columns={"mean": "_grp_mean", "std": "_grp_std", "count": "_grp_count"})
    )

    # Filter groups with sufficient observations
    group_stats["_sufficient"] = group_stats["_grp_count"] >= min_observations

    # Merge back
    df_out = df_out.merge(
        group_stats[[site_col, season_col, "_grp_mean", "_grp_std", "_grp_count", "_sufficient"]],
        on=[site_col, season_col],
        how="left",
    )

    # Compute z-score where sufficient data exists and std > 0
    can_compute = (
        df_out["_sufficient"].fillna(False)
        & df_out[value_col].notna()
        & df_out["_grp_std"].notna()
        & (df_out["_grp_std"] > 0)
    )

    df_out["seasonal_z_score"] = np.where(
        can_compute,
        (df_out[value_col] - df_out["_grp_mean"]) / df_out["_grp_std"],
        np.nan,
    )

    df_out["seasonal_z_score_available"] = can_compute

    # Clean up
    df_out = df_out.drop(columns=["_grp_mean", "_grp_std", "_grp_count", "_sufficient"])

    return df_out
