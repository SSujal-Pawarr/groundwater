"""
NEW/src/features/temporal.py - Temporal Structure Analysis

Purpose:
- Characterize actual temporal structure for India periodic and Maharashtra telemetry data.
- Compute observation frequency, gaps, coverage, and continuity metrics.
- Dataset-specific logic: India (periodic/seasonal) vs Maharashtra (continuous 6-hourly).

Scientific Constraints:
- Do not assume every location has every season.
- Do not assume uniform temporal spacing.
- Preserve chronological ordering.
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd


def compute_india_temporal_profile(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Characterizes the temporal structure of India periodic groundwater data.

    Analyzes:
    - Observation date distribution
    - Observations per year
    - Observations per month
    - Temporal coverage span
    - Seasonal availability per location
    - Year coverage per location

    Parameters
    ----------
    df : pd.DataFrame
        Normalized India dataset (analytics-ready subset recommended).

    Returns
    -------
    Dict[str, Any]
        Temporal profile statistics.
    """
    result: Dict[str, Any] = {}

    # Parse dates
    dates = pd.to_datetime(df["observation_date"], errors="coerce")
    valid_dates = dates.dropna()

    result["total_observations"] = len(df)
    result["observations_with_valid_date"] = len(valid_dates)

    if len(valid_dates) == 0:
        return result

    result["date_range"] = {
        "min": str(valid_dates.min().date()),
        "max": str(valid_dates.max().date()),
        "span_days": int((valid_dates.max() - valid_dates.min()).days),
    }

    # Year distribution
    years = df["observation_year"].dropna().astype(int)
    year_counts = years.value_counts().sort_index()
    result["year_distribution"] = {
        "unique_years": int(years.nunique()),
        "min_year": int(years.min()),
        "max_year": int(years.max()),
        "observations_per_year": year_counts.to_dict(),
    }

    # Month distribution
    months = df["observation_month"].dropna().astype(int)
    month_counts = months.value_counts().sort_index()
    result["month_distribution"] = {
        "unique_months": sorted(months.unique().tolist()),
        "observations_per_month": month_counts.to_dict(),
    }

    # Per-site temporal coverage
    site_year_coverage = df.groupby("candidate_site_id")["observation_year"].nunique()
    site_month_coverage = df.groupby("candidate_site_id")["observation_month"].nunique()

    result["per_site_year_coverage"] = {
        "min_years": int(site_year_coverage.min()),
        "max_years": int(site_year_coverage.max()),
        "mean_years": round(float(site_year_coverage.mean()), 1),
        "median_years": float(site_year_coverage.median()),
    }

    result["per_site_month_coverage"] = {
        "min_months": int(site_month_coverage.min()),
        "max_months": int(site_month_coverage.max()),
        "mean_months": round(float(site_month_coverage.mean()), 1),
        "median_months": float(site_month_coverage.median()),
    }

    return result


def compute_maharashtra_temporal_profile(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Characterizes the temporal structure of Maharashtra continuous telemetry data.

    Analyzes:
    - Timestamp range and coverage
    - Observations per station
    - Telemetry interval (expected 6-hourly)
    - Gaps and continuity

    Parameters
    ----------
    df : pd.DataFrame
        Normalized Maharashtra dataset (analytics-ready subset recommended).

    Returns
    -------
    Dict[str, Any]
        Temporal profile statistics.
    """
    result: Dict[str, Any] = {}

    # Parse timestamps
    ts = pd.to_datetime(df["observation_timestamp"], errors="coerce")
    valid_ts = ts.dropna()

    result["total_observations"] = len(df)
    result["observations_with_valid_timestamp"] = len(valid_ts)

    if len(valid_ts) == 0:
        return result

    result["timestamp_range"] = {
        "min": str(valid_ts.min()),
        "max": str(valid_ts.max()),
        "span_days": int((valid_ts.max() - valid_ts.min()).days),
    }

    # Per-station observation counts
    station_obs = df.groupby("station_name").size()
    result["observations_per_station"] = {
        "min": int(station_obs.min()),
        "max": int(station_obs.max()),
        "mean": round(float(station_obs.mean()), 1),
        "median": float(station_obs.median()),
        "total_stations": int(len(station_obs)),
    }

    # Telemetry interval analysis (sample top stations for efficiency)
    top_stations = station_obs.nlargest(min(50, len(station_obs))).index.tolist()
    interval_hours_all = []

    for stn in top_stations:
        stn_df = df[df["station_name"] == stn].copy()
        stn_ts = pd.to_datetime(stn_df["observation_timestamp"], errors="coerce").dropna().sort_values()
        if len(stn_ts) > 1:
            gaps_hours = stn_ts.diff().dt.total_seconds().dropna() / 3600
            interval_hours_all.extend(gaps_hours.tolist())

    if interval_hours_all:
        arr = np.array(interval_hours_all)
        result["telemetry_interval_hours"] = {
            "min": round(float(arr.min()), 1),
            "max": round(float(arr.max()), 1),
            "mean": round(float(arr.mean()), 1),
            "median": round(float(np.median(arr)), 1),
            "pct_6_hourly": round(float(np.mean(np.abs(arr - 6.0) < 0.5) * 100), 1),
            "stations_sampled": len(top_stations),
        }

    return result


def compute_observation_gaps(
    df: pd.DataFrame,
    site_col: str = "candidate_site_id",
    date_col: str = "observation_date",
    timestamp_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    Computes gaps between consecutive observations for each site/station.

    For India periodic data: uses observation_date (daily resolution).
    For Maharashtra telemetry: uses observation_timestamp (sub-daily resolution).

    Parameters
    ----------
    df : pd.DataFrame
        Normalized dataset.
    site_col : str
        Column identifying monitoring locations.
    date_col : str
        Date column for gap calculation (India).
    timestamp_col : Optional[str]
        Timestamp column for gap calculation (Maharashtra). If provided, takes
        precedence over date_col.

    Returns
    -------
    pd.DataFrame
        Per-site gap statistics: site_col, obs_count, min_gap_days,
        max_gap_days, mean_gap_days, median_gap_days.
    """
    time_col = timestamp_col if timestamp_col else date_col
    df_work = df[[site_col, time_col]].copy()
    df_work["_parsed_time"] = pd.to_datetime(df_work[time_col], errors="coerce")
    df_work = df_work.dropna(subset=["_parsed_time"])

    records = []
    for site, group in df_work.groupby(site_col):
        sorted_times = group["_parsed_time"].sort_values()
        obs_count = len(sorted_times)
        if obs_count < 2:
            records.append({
                site_col: site,
                "obs_count": obs_count,
                "min_gap_days": None,
                "max_gap_days": None,
                "mean_gap_days": None,
                "median_gap_days": None,
            })
            continue

        gaps = sorted_times.diff().dt.total_seconds().dropna() / 86400  # days
        records.append({
            site_col: site,
            "obs_count": obs_count,
            "min_gap_days": round(float(gaps.min()), 2),
            "max_gap_days": round(float(gaps.max()), 2),
            "mean_gap_days": round(float(gaps.mean()), 2),
            "median_gap_days": round(float(gaps.median()), 2),
        })

    return pd.DataFrame(records)
