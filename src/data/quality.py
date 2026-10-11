"""
NEW/src/data/quality.py - Comprehensive Quality Flagging & Analytics Exclusion Engine

Governing Principles (instruction.md):
- Strictly non-destructive: Never silently drops, deletes, or alters raw observations.
- All quality defects are catalogued as explicit flags.
- Configurable, transparent thresholds with documented rationale.
- Records excluded from analytics are tracked with boolean `is_analytics_ready`.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional
import numpy as np
import pandas as pd


@dataclass
class QualityConfig:
    """
    DATA_QUALITY_SCREENING_THRESHOLD configuration.

    Important scientific note:
    These numerical thresholds are empirical data-quality screening cutoffs designed
    to identify records requiring human or domain review, NOT scientifically validated
    immutable groundwater physical limits. Observations exceeding these screening
    thresholds are NOT deleted or claimed to be definitively physically impossible, but
    are flagged and excluded from downstream analytics via `is_analytics_ready = False`.

    Screening Rules:
    - India Periodic Seasonal:
      Depths between 0.0m and 150.0m represent normal regional screening bounds across India.
      Depths < 0.0m or > 150.0m trigger EXTREME_WATER_LEVEL_REVIEW_REQUIRED.
      Depths > 500.0m (e.g., 53,943m typographical data entry anomaly) trigger
      SEVERE_EXTREME_WATER_LEVEL_REVIEW_REQUIRED.
    - Maharashtra Telemetry:
      Telemetry observations < -100.0m or > 50.0m trigger EXTREME_WATER_LEVEL_REVIEW_REQUIRED.
    """

    # India screening bounds (DATA_QUALITY_SCREENING_THRESHOLD)
    india_min_level: float = 0.0
    india_max_level: float = 150.0
    india_extreme_level: float = 500.0

    # Maharashtra telemetry screening bounds (DATA_QUALITY_SCREENING_THRESHOLD)
    maharashtra_min_level: float = -100.0
    maharashtra_max_level: float = 50.0

    # Geographic boundary box (India territorial extent WGS84)
    india_lat_min: float = 6.0
    india_lat_max: float = 38.0
    india_lng_min: float = 68.0
    india_lng_max: float = 98.0

    # Critical disqualifying flags for analytics readiness
    disqualifying_flags: Set[str] = field(
        default_factory=lambda: {
            "COORDINATE_OUT_OF_BOUNDS",
            "COORDINATE_MISSING",
            "EXTREME_WATER_LEVEL_REVIEW_REQUIRED",
            "SEVERE_EXTREME_WATER_LEVEL_REVIEW_REQUIRED",
            "EXACT_DUPLICATE",
            "CONFLICTING_DUPLICATE",
        }
    )


# Standard Quality Flags
FLAG_COORDINATE_INVERTED_CORRECTED = "COORDINATE_INVERTED_CORRECTED"
FLAG_COORDINATE_OUT_OF_BOUNDS = "COORDINATE_OUT_OF_BOUNDS"
FLAG_COORDINATE_MISSING = "COORDINATE_MISSING"
FLAG_MALFORMED_ADMIN_GEOGRAPHY = "MALFORMED_ADMIN_GEOGRAPHY"
FLAG_EXTREME_WATER_LEVEL_REVIEW_REQUIRED = "EXTREME_WATER_LEVEL_REVIEW_REQUIRED"
FLAG_SEVERE_EXTREME_WATER_LEVEL_REVIEW_REQUIRED = "SEVERE_EXTREME_WATER_LEVEL_REVIEW_REQUIRED"
FLAG_EXACT_DUPLICATE = "EXACT_DUPLICATE"
FLAG_CANDIDATE_SITE_DATE_DUPLICATE = "CANDIDATE_SITE_DATE_DUPLICATE"
FLAG_CONFLICTING_DUPLICATE = "CONFLICTING_DUPLICATE"
FLAG_LABEL_PROVENANCE_UNVERIFIED = "LABEL_PROVENANCE_UNVERIFIED"


def detect_malformed_admin_strings(state_series: pd.Series) -> pd.Series:
    """
    Identifies records where administrative fields appear concatenated
    into state (e.g., Dadra & Nagar Haveli strings containing fused district/block/village).
    """
    s = state_series.astype(str).str.strip()
    is_concatenated = (
        s.str.contains("Dadra And Nagar Haveli Dadra Nagar Haveli", na=False, regex=False)
        | s.str.contains("Daman Daman", na=False, regex=False)
        | s.str.contains("Diu Diu", na=False, regex=False)
        | (s.str.startswith("The Dadra And Nagar Haveli And Daman And Diu") & (s.str.len() > 45))
        | (s.str.len() > 60)  # Extreme string length for state
        | s.isin(["nan", "None", "", "UNKNOWN"])
    )
    return is_concatenated


def assess_india_quality(df: pd.DataFrame, config: Optional[QualityConfig] = None) -> pd.DataFrame:
    """
    Executes complete non-destructive quality assessment for normalized India records:
    1. Coordinate validity & bounds.
    2. Malformed administrative geography detection.
    3. Physically suspicious water level detection.
    4. Exact duplicate and conflicting duplicate detection.
    5. Synthetic status/trend label flagging.
    6. Determines `is_analytics_ready` without dropping records.
    """
    if config is None:
        config = QualityConfig()

    df_out = df.copy()
    num_rows = len(df_out)

    # Initialize quality flags as list of sets for fast vectorized row assignment
    flags_list: List[Set[str]] = [set() for _ in range(num_rows)]

    # 1. Coordinate Inversion Corrected Flag
    if "coordinate_inverted_corrected" in df_out.columns:
        inv_mask = df_out["coordinate_inverted_corrected"].fillna(False).values
        for i, is_inv in enumerate(inv_mask):
            if is_inv:
                flags_list[i].add(FLAG_COORDINATE_INVERTED_CORRECTED)

    # 2. Coordinate Quality (Missing or Out of Bounds)
    lat_vals = df_out["latitude"].values
    lng_vals = df_out["longitude"].values

    missing_coords = np.isnan(lat_vals) | np.isnan(lng_vals)
    for i, is_missing in enumerate(missing_coords):
        if is_missing:
            flags_list[i].add(FLAG_COORDINATE_MISSING)

    valid_coords = ~missing_coords
    out_of_bounds = valid_coords & (
        (lat_vals < config.india_lat_min)
        | (lat_vals > config.india_lat_max)
        | (lng_vals < config.india_lng_min)
        | (lng_vals > config.india_lng_max)
    )
    for i, is_oob in enumerate(out_of_bounds):
        if is_oob:
            flags_list[i].add(FLAG_COORDINATE_OUT_OF_BOUNDS)

    # 3. Malformed Geography
    malformed_geo = detect_malformed_admin_strings(df_out["state"]).values
    for i, is_malformed in enumerate(malformed_geo):
        if is_malformed:
            flags_list[i].add(FLAG_MALFORMED_ADMIN_GEOGRAPHY)

    # 4. Water Level Screening (DATA_QUALITY_SCREENING_THRESHOLD)
    wl_vals = df_out["water_level_raw"].values
    wl_missing = np.isnan(wl_vals)

    # Severe extreme screening (e.g. > 500m like the 53,943m error requiring review)
    wl_severe_extreme = (~wl_missing) & (wl_vals > config.india_extreme_level)
    for i, is_imp in enumerate(wl_severe_extreme):
        if is_imp:
            flags_list[i].add(FLAG_SEVERE_EXTREME_WATER_LEVEL_REVIEW_REQUIRED)

    # Extreme screening thresholds (< 0.0m or > 150.0m requiring review)
    wl_extreme = (~wl_missing) & (
        (wl_vals < config.india_min_level) | (wl_vals > config.india_max_level)
    ) & (~wl_severe_extreme)
    for i, is_susp in enumerate(wl_extreme):
        if is_susp:
            flags_list[i].add(FLAG_EXTREME_WATER_LEVEL_REVIEW_REQUIRED)

    # 5. Label Provenance Unverified Flag
    # Flag records containing status/trend fields whose provenance is unverified
    has_labels = (
        df_out["status_raw"].fillna("").astype(str).str.len() > 0
    ) | (
        df_out["trend_raw"].fillna("").astype(str).str.len() > 0
    )
    for i, has_lbl in enumerate(has_labels.values):
        if has_lbl:
            flags_list[i].add(FLAG_LABEL_PROVENANCE_UNVERIFIED)

    # 6. Duplicates Assessment
    # A. Exact duplicates (ignoring internal flags)
    # Check duplicate across raw inputs
    exact_dup_mask = df_out.duplicated(
        subset=["source_file", "state_raw", "district_raw", "village_raw", "source_lat", "source_lng", "date_raw", "water_level_raw"],
        keep="first",
    ).values
    for i, is_dup in enumerate(exact_dup_mask):
        if is_dup:
            flags_list[i].add(FLAG_EXACT_DUPLICATE)

    # B. Candidate Site + Date Duplicates
    site_date_subset = ["candidate_site_id", "observation_date"]
    dup_site_date_mask = df_out.duplicated(subset=site_date_subset, keep=False).values

    # Check for conflicting water levels on same candidate site and date
    if dup_site_date_mask.any():
        # Group by site+date and check number of unique water_level_raw values
        wl_std_per_group = df_out.groupby(site_date_subset)["water_level_raw"].transform("nunique")
        conflicting_mask = (wl_std_per_group > 1).values
        for i, is_conf in enumerate(conflicting_mask):
            if is_conf:
                flags_list[i].add(FLAG_CONFLICTING_DUPLICATE)
            elif dup_site_date_mask[i] and not exact_dup_mask[i]:
                flags_list[i].add(FLAG_CANDIDATE_SITE_DATE_DUPLICATE)

    # 7. Convert quality flags to standardized comma-separated string & array
    flags_formatted = [";".join(sorted(list(f))) for f in flags_list]
    df_out["quality_flags"] = flags_formatted

    # 8. Analytics Readiness: False if any disqualifying flag is present
    is_ready = [
        len(flags.intersection(config.disqualifying_flags)) == 0 for flags in flags_list
    ]
    df_out["is_analytics_ready"] = is_ready

    return df_out


def assess_maharashtra_quality(df: pd.DataFrame, config: Optional[QualityConfig] = None) -> pd.DataFrame:
    """
    Executes complete non-destructive quality assessment for normalized Maharashtra telemetry records:
    1. Coordinate validity.
    2. Telemetry sensor range sanity (-100m to +50m).
    3. Duplicate detection (exact and station+timestamp conflicts).
    4. Determines `is_analytics_ready` without dropping records.
    """
    if config is None:
        config = QualityConfig()

    df_out = df.copy()
    num_rows = len(df_out)
    flags_list: List[Set[str]] = [set() for _ in range(num_rows)]

    # 1. Coordinates
    lat_vals = df_out["latitude"].values
    lng_vals = df_out["longitude"].values
    missing_coords = np.isnan(lat_vals) | np.isnan(lng_vals)
    for i, is_missing in enumerate(missing_coords):
        if is_missing:
            flags_list[i].add(FLAG_COORDINATE_MISSING)

    valid_coords = ~missing_coords
    out_of_bounds = valid_coords & (
        (lat_vals < config.india_lat_min)
        | (lat_vals > config.india_lat_max)
        | (lng_vals < config.india_lng_min)
        | (lng_vals > config.india_lng_max)
    )
    for i, is_oob in enumerate(out_of_bounds):
        if is_oob:
            flags_list[i].add(FLAG_COORDINATE_OUT_OF_BOUNDS)

    # 2. Telemetry Water Level Screening (DATA_QUALITY_SCREENING_THRESHOLD: < -100m or > 50m)
    wl_vals = df_out["water_level_raw"].values
    wl_missing = np.isnan(wl_vals)
    wl_extreme = (~wl_missing) & (
        (wl_vals < config.maharashtra_min_level) | (wl_vals > config.maharashtra_max_level)
    )
    for i, is_susp in enumerate(wl_extreme):
        if is_susp:
            flags_list[i].add(FLAG_EXTREME_WATER_LEVEL_REVIEW_REQUIRED)

    # 3. Duplicate Detection
    exact_dup = df_out.duplicated(
        subset=["station_name", "data_acquisition_time_raw", "water_level_raw"],
        keep="first",
    ).values
    for i, is_dup in enumerate(exact_dup):
        if is_dup:
            flags_list[i].add(FLAG_EXACT_DUPLICATE)

    # Conflicting timestamp duplicates
    st_time_subset = ["station_name", "observation_timestamp"]
    dup_st_time = df_out.duplicated(subset=st_time_subset, keep=False).values
    if dup_st_time.any():
        wl_unique_per_group = df_out.groupby(st_time_subset)["water_level_raw"].transform("nunique")
        conflicting_mask = (wl_unique_per_group > 1).values
        for i, is_conf in enumerate(conflicting_mask):
            if is_conf:
                flags_list[i].add(FLAG_CONFLICTING_DUPLICATE)
            elif dup_st_time[i] and not exact_dup[i]:
                flags_list[i].add(FLAG_CANDIDATE_SITE_DATE_DUPLICATE)

    # Quality flags & Analytics readiness
    flags_formatted = [";".join(sorted(list(f))) for f in flags_list]
    df_out["quality_flags"] = flags_formatted
    is_ready = [
        len(flags.intersection(config.disqualifying_flags)) == 0 for flags in flags_list
    ]
    df_out["is_analytics_ready"] = is_ready

    return df_out
