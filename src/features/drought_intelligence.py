import numpy as np
import pandas as pd
from typing import Set

# Configuration / Thresholds
METHODOLOGY_VERSION = "M10-Drought-v1"
MIN_HISTORY_YEARS = 10
DEFICIT_P25 = 25.0
DEFICIT_P10 = 10.0
PERSISTENCE_MIN_SEASONS = 2

# Regional coverage thresholds (Project configurations, not regulatory)
REGIONAL_COVERAGE_MODERATE = 0.33
REGIONAL_COVERAGE_SEVERE = 0.50

# States
STATE_NORMAL = "NORMAL_TO_WET"
STATE_WATCH = "WATCH_DEFICIT"
STATE_MODERATE = "MODERATE_DEFICIT"
STATE_SEVERE = "SEVERE_DEFICIT"
STATE_INSUFFICIENT = "INSUFFICIENT_HISTORY"

DISQUALIFYING_FLAGS = {
    "INVALID_OR_EMPTY",
    "UNREALISTIC_WATER_LEVEL",
    "CONFLICTING_DUPLICATE"
}

def _has_quality_flags(flags: str, disqualifying: Set[str]) -> bool:
    if pd.isna(flags) or not flags:
        return False
    row_flags = set(str(flags).split(";"))
    return len(row_flags.intersection(disqualifying)) > 0

def _compute_expanding_percentile_drought(group_df: pd.DataFrame, val_col: str) -> pd.DataFrame:
    """
    Computes an expanding percentile strictly backward-looking.
    For index i, reference distribution is [0, i-1].
    Group is assumed to be sorted chronologically by season and year.
    
    IMPORTANT SCIENTIFIC NOTE: 
    Since `water_level_raw` represents Depth Below Ground Level (positive),
    a LARGER value indicates LESS water.
    To make percentiles intuitive (P10 = severe deficit/dry, P90 = wet),
    we INVERT the percentile rank calculation.
    `less` counts the historical observations that were DEEPER (greater value) than current.
    """
    vals = group_df[val_col].values
    flags = group_df["quality_flags"].values if "quality_flags" in group_df.columns else np.full(len(vals), "")
    
    n = len(vals)
    percentiles = np.full(n, np.nan)
    counts = np.zeros(n, dtype=int)
    
    # Pre-calculate validity
    is_valid = np.array([not _has_quality_flags(f, DISQUALIFYING_FLAGS) for f in flags])
    valid_vals = np.where(is_valid, vals, np.nan)
    
    for i in range(n):
        # Count strictly prior valid observations
        ref = valid_vals[:i]
        valid_ref = ref[~np.isnan(ref)]
        n_valid = len(valid_ref)
        counts[i] = n_valid
        
        curr = vals[i]
        
        # Only compute percentile if current value is valid, and we have enough history
        if n_valid >= MIN_HISTORY_YEARS and is_valid[i] and not np.isnan(curr):
            # INVERTED logic for depth: we want shallow (low depth) to be high percentile
            less = np.sum(valid_ref > curr)
            equal = np.sum(valid_ref == curr)
            percentiles[i] = (less + 0.5 * equal) / n_valid * 100.0
            
    out_df = group_df.copy()
    out_df["groundwater_percentile"] = percentiles
    out_df["eligible_history_years"] = counts
    return out_df


def _calculate_persistence(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates consecutive seasonal observations showing a deficit.
    Requires dataframe to be sorted chronologically per site across all seasons.
    """
    deficit_mask = df["groundwater_percentile"] < DEFICIT_P25
    deficit_mask = deficit_mask & (df["eligible_history_years"] >= MIN_HISTORY_YEARS)
    
    consecutive = np.zeros(len(df), dtype=int)
    current_streak = 0
    
    site_ids = df["candidate_site_id"].values
    def_vals = deficit_mask.values
    
    prev_site = None
    for i in range(len(df)):
        site = site_ids[i]
        if site != prev_site:
            current_streak = 0
            prev_site = site
            
        if def_vals[i]:
            current_streak += 1
        else:
            current_streak = 0
            
        consecutive[i] = current_streak

    df_out = df.copy()
    df_out["consecutive_deficit_seasons"] = consecutive
    return df_out


def compute_drought_intelligence(df: pd.DataFrame, region_col: str = "district") -> pd.DataFrame:
    """
    Computes Seasonal Groundwater Drought Intelligence Index.
    """
    df_out = df.copy()
    site_col = "candidate_site_id"
    season_col = "analytical_season"
    val_col = "water_level_raw"
    date_col = "observation_date"
    
    df_out["_orig_index"] = df_out.index
    df_out["_parsed_date"] = pd.to_datetime(df_out[date_col], errors="coerce")
    
    # 1. Calculate historical percentiles (grouped by site and season)
    df_out = df_out.sort_values([site_col, season_col, "_parsed_date"]).reset_index(drop=True)
    
    processed = pd.concat(
        [
            _compute_expanding_percentile_drought(group, val_col=val_col)
            for _, group in df_out.groupby([site_col, season_col], sort=False, dropna=False)
        ]
    ).sort_index()
    
    processed["groundwater_deficit_signal"] = np.where(
        processed["groundwater_percentile"] < DEFICIT_P25, True, False
    )
    
    # 2. Calculate persistence (grouped by site, sorted by date across all seasons)
    processed = processed.sort_values([site_col, "_parsed_date"]).reset_index(drop=True)
    processed = _calculate_persistence(processed)
    
    # 3. Spatial Aggregation (grouped by region, year, season)
    processed["observation_year"] = processed["_parsed_date"].dt.year
    processed["_is_eligible"] = processed["eligible_history_years"] >= MIN_HISTORY_YEARS
    
    processed["_is_deficit_site"] = (processed["groundwater_percentile"] < DEFICIT_P25) & \
                                    (processed["consecutive_deficit_seasons"] >= PERSISTENCE_MIN_SEASONS)
                                    
    processed["_is_severe_site"] = (processed["groundwater_percentile"] < DEFICIT_P10) & \
                                   (processed["consecutive_deficit_seasons"] >= PERSISTENCE_MIN_SEASONS)
    
    region_stats = processed.groupby([region_col, "observation_year", season_col]).agg(
        eligible_site_count=("_is_eligible", "sum"),
        deficit_site_count=("_is_deficit_site", "sum"),
        severe_site_count=("_is_severe_site", "sum"),
        median_groundwater_percentile=("groundwater_percentile", "median")
    ).reset_index()
    
    region_stats["spatial_coverage_ratio"] = np.where(
        region_stats["eligible_site_count"] > 0,
        region_stats["deficit_site_count"] / region_stats["eligible_site_count"],
        np.nan
    )
    
    region_stats["severe_coverage_ratio"] = np.where(
        region_stats["eligible_site_count"] > 0,
        region_stats["severe_site_count"] / region_stats["eligible_site_count"],
        np.nan
    )
    
    def assign_regional_status(row):
        if row["eligible_site_count"] == 0 or pd.isna(row["spatial_coverage_ratio"]):
            return STATE_INSUFFICIENT
            
        if row["severe_coverage_ratio"] >= REGIONAL_COVERAGE_SEVERE:
            return STATE_SEVERE
        elif row["spatial_coverage_ratio"] >= REGIONAL_COVERAGE_MODERATE:
            return STATE_MODERATE
        elif row["spatial_coverage_ratio"] > 0:
            return STATE_WATCH
        else:
            return STATE_NORMAL
            
    region_stats["regional_drought_status"] = region_stats.apply(assign_regional_status, axis=1)
    
    processed = processed.merge(
        region_stats[[region_col, "observation_year", season_col, 
                      "eligible_site_count", "deficit_site_count", 
                      "spatial_coverage_ratio", "regional_drought_status"]],
        on=[region_col, "observation_year", season_col],
        how="left"
    )
    
    processed["drought_status"] = np.where(
        processed["eligible_history_years"] < MIN_HISTORY_YEARS,
        STATE_INSUFFICIENT,
        processed["regional_drought_status"]
    )
    
    processed["methodology_version"] = METHODOLOGY_VERSION
    processed["meteorological_context_available"] = False
    processed["drought_data_quality_state"] = np.where(
        processed["quality_flags"].notna() & (processed["quality_flags"] != ""),
        "FLAGGED",
        "CLEAN"
    )
    
    processed = processed.sort_values("_orig_index").set_index("_orig_index")
    processed.index.name = None
    
    final_cols = [
        site_col,
        "observation_date",
        season_col,
        "drought_status",
        "groundwater_percentile",
        "groundwater_deficit_signal",
        "eligible_history_years",
        "consecutive_deficit_seasons",
        "eligible_site_count",
        "deficit_site_count",
        "spatial_coverage_ratio",
        "methodology_version",
        "drought_data_quality_state",
        "meteorological_context_available"
    ]
    
    if region_col not in final_cols:
        final_cols.insert(1, region_col)
        
    return processed[final_cols]
