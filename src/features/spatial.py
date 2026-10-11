"""
NEW/src/features/spatial.py - Spatial/Location Analysis for India Groundwater Data

Purpose:
- Analyze repeated monitoring locations using available fields.
- Build defensible analytical site identifiers (NOT official station IDs).
- Quantify coordinate consistency and location ambiguity.
- Flag ambiguous cluster assignments rather than silently forcing them.

Scientific Constraints:
- The India dataset lacks a trustworthy official station ID.
- The `candidate_site_id` from normalization uses a SHA-256 hash of
  (state, district, block, village, lat_4dp, lng_4dp).
- This module investigates whether that identifier reliably represents
  repeated physical monitoring locations.
- No clustering is forced if it would introduce more uncertainty than value.
"""

from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd


def build_analytical_site_id(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validates and promotes the existing `candidate_site_id` as the
    `analytical_site_id` for India periodic data.

    The analytical_site_id is explicitly documented as an analytical construct,
    NOT an official station identifier. It is deterministic: same inputs
    always produce the same ID.

    This function:
    1. Copies candidate_site_id as analytical_site_id.
    2. Adds a boolean flag `site_id_is_analytical` = True to every row.
    3. Does NOT modify any source observations.

    Parameters
    ----------
    df : pd.DataFrame
        Normalized India dataset with `candidate_site_id` column.

    Returns
    -------
    pd.DataFrame
        Copy of input with `analytical_site_id` and `site_id_is_analytical` added.
    """
    if "candidate_site_id" not in df.columns:
        raise ValueError("Input DataFrame must contain 'candidate_site_id' column.")

    df_out = df.copy()
    df_out["analytical_site_id"] = df_out["candidate_site_id"]
    df_out["site_id_is_analytical"] = True
    return df_out


def analyze_location_consistency(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Investigates coordinate precision and consistency for India monitoring locations.

    Analyzes:
    - How many unique (lat, lon) pairs exist per candidate_site_id.
    - Coordinate precision (decimal places).
    - Whether the same physical location appears with slightly different coordinates.
    - Ambiguous locations where administrative fields match but coordinates differ.

    Parameters
    ----------
    df : pd.DataFrame
        Normalized India dataset (analytics-ready subset recommended).

    Returns
    -------
    Dict[str, Any]
        Dictionary with consistency analysis results.
    """
    if "candidate_site_id" not in df.columns:
        raise ValueError("Input DataFrame must contain 'candidate_site_id' column.")

    result: Dict[str, Any] = {}

    # Total unique sites
    total_sites = df["candidate_site_id"].nunique()
    result["total_unique_candidate_sites"] = total_sites

    # Coordinate precision analysis
    lat_valid = df["latitude"].dropna()
    lng_valid = df["longitude"].dropna()

    if len(lat_valid) > 0:
        # Count decimal places
        lat_decimals = lat_valid.apply(lambda x: len(str(x).split(".")[-1]) if "." in str(x) else 0)
        result["latitude_decimal_places"] = {
            "min": int(lat_decimals.min()),
            "max": int(lat_decimals.max()),
            "median": float(lat_decimals.median()),
            "mode": int(lat_decimals.mode().iloc[0]) if len(lat_decimals.mode()) > 0 else None,
        }

    if len(lng_valid) > 0:
        lng_decimals = lng_valid.apply(lambda x: len(str(x).split(".")[-1]) if "." in str(x) else 0)
        result["longitude_decimal_places"] = {
            "min": int(lng_decimals.min()),
            "max": int(lng_decimals.max()),
            "median": float(lng_decimals.median()),
            "mode": int(lng_decimals.mode().iloc[0]) if len(lng_decimals.mode()) > 0 else None,
        }

    # Unique (lat, lon) pairs per candidate_site_id
    # Since candidate_site_id includes lat_4dp and lng_4dp, each ID should map
    # to exactly one coordinate pair at 4-decimal precision
    site_coord_counts = (
        df.groupby("candidate_site_id")[["latitude", "longitude"]]
        .apply(lambda g: g.drop_duplicates().shape[0])
    )
    result["sites_with_single_coord_pair"] = int((site_coord_counts == 1).sum())
    result["sites_with_multiple_coord_pairs"] = int((site_coord_counts > 1).sum())

    # Observations per site distribution
    obs_per_site = df.groupby("candidate_site_id").size()
    result["observations_per_site"] = {
        "min": int(obs_per_site.min()),
        "max": int(obs_per_site.max()),
        "mean": round(float(obs_per_site.mean()), 1),
        "median": float(obs_per_site.median()),
        "std": round(float(obs_per_site.std()), 1),
        "sites_with_1_obs": int((obs_per_site == 1).sum()),
        "sites_with_2_to_5_obs": int(((obs_per_site >= 2) & (obs_per_site <= 5)).sum()),
        "sites_with_6_to_20_obs": int(((obs_per_site >= 6) & (obs_per_site <= 20)).sum()),
        "sites_with_21_plus_obs": int((obs_per_site >= 21).sum()),
    }

    # Administrative field completeness
    result["admin_field_completeness"] = {
        "state_non_null": int(df["state"].notna().sum()),
        "district_non_null": int(df["district"].notna().sum()),
        "block_non_null": int(df["block"].notna().sum()),
        "village_non_null": int(df["village"].notna().sum()),
        "total_rows": len(df),
    }

    # Check for near-duplicate locations:
    # Same (state, district, block, village) but different coordinates
    admin_cols = ["state", "district", "block", "village"]
    admin_available = [c for c in admin_cols if c in df.columns]
    if len(admin_available) == 4:
        admin_groups = df.groupby(admin_available, dropna=False)
        multi_coord_admin = 0
        for _, group in admin_groups:
            unique_coords = group[["latitude", "longitude"]].drop_duplicates()
            if len(unique_coords) > 1:
                multi_coord_admin += 1
        result["admin_groups_with_multiple_coordinates"] = multi_coord_admin

    return result


def compute_site_observation_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes per-site summary statistics for the India dataset.

    For each analytical site, calculates:
    - total observation count
    - date range (min/max observation_date)
    - number of unique years
    - number of unique months
    - mean water level (with count of non-null)

    Parameters
    ----------
    df : pd.DataFrame
        Normalized India dataset with candidate_site_id and observation_date.

    Returns
    -------
    pd.DataFrame
        One row per candidate_site_id with summary statistics.
    """
    if "candidate_site_id" not in df.columns:
        raise ValueError("Input must contain 'candidate_site_id'.")

    grouped = df.groupby("candidate_site_id").agg(
        total_observations=("observation_date", "count"),
        first_observation=("observation_date", "min"),
        last_observation=("observation_date", "max"),
        unique_years=("observation_year", "nunique"),
        unique_months=("observation_month", "nunique"),
        mean_water_level=("water_level_raw", "mean"),
        water_level_obs_count=("water_level_raw", "count"),
        latitude=("latitude", "first"),
        longitude=("longitude", "first"),
        state=("state", "first"),
        district=("district", "first"),
    ).reset_index()

    return grouped


def evaluate_spatial_clustering_necessity(
    df: pd.DataFrame,
    radius_meters: float = 100.0,
) -> Dict[str, Any]:
    """
    Evaluates whether spatial clustering would add value or introduce uncertainty.

    Because the candidate_site_id already incorporates lat/lon at 4 decimal places
    (~11m precision), clustering at coarser radii risks merging distinct wells.

    This function documents the analysis rather than automatically performing clustering.

    Parameters
    ----------
    df : pd.DataFrame
        Normalized India dataset with latitude and longitude.
    radius_meters : float
        Candidate clustering radius in meters. Default 100m.

    Returns
    -------
    Dict[str, Any]
        Assessment of whether clustering is justified.
    """
    result: Dict[str, Any] = {}

    coords = df[["latitude", "longitude"]].dropna().drop_duplicates()
    result["unique_coordinate_pairs"] = len(coords)
    result["candidate_site_ids"] = df["candidate_site_id"].nunique()

    # The candidate_site_id uses 4 decimal places for coordinates.
    # 4 decimal places of latitude ≈ 11.1 meters precision.
    # This means two wells within ~11m would share the same candidate_site_id.
    result["coordinate_precision_meters"] = 11.1  # approximate for 4 decimal places

    # Assessment
    if radius_meters <= result["coordinate_precision_meters"]:
        result["clustering_justified"] = False
        result["reason"] = (
            f"Requested clustering radius ({radius_meters}m) is at or below the "
            f"coordinate precision ({result['coordinate_precision_meters']}m). "
            f"The candidate_site_id already captures locations at this resolution. "
            f"Additional clustering would not provide meaningful grouping."
        )
    else:
        # Clustering at coarser radii risks merging distinct monitoring wells.
        # Without authoritative station metadata to validate merges, this
        # introduces more uncertainty than value.
        result["clustering_justified"] = False
        result["reason"] = (
            f"Clustering at {radius_meters}m radius would merge distinct monitoring "
            f"locations that may represent different wells in the same village/block. "
            f"Without authoritative station metadata to confirm which wells are "
            f"the same physical monitoring point, clustering would introduce "
            f"unverifiable assumptions. The candidate_site_id provides a safer "
            f"analytical location key at ~11m coordinate precision."
        )

    result["recommendation"] = (
        "Use candidate_site_id (promoted as analytical_site_id) as the primary "
        "location identifier. It is deterministic, reproducible, and does not "
        "require unverifiable clustering assumptions. Clearly document that it "
        "is an analytical identifier, not an official station ID."
    )

    return result
