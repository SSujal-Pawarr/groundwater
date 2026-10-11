import numpy as np
import pandas as pd
from typing import Set
from scipy import stats

from features.drought_intelligence import (
    DEFICIT_P25,
    DEFICIT_P10
)

# Configuration / Thresholds
METHODOLOGY_VERSION = "M12-Stress-v1"
MIN_HISTORY_YEARS_STRESS = 5
PERSISTENCE_MIN_SEASONS_STRESS = 4
REGIONAL_COVERAGE_STRESS = 0.33

# States
STATE_NORMAL = "NORMAL"
STATE_WATCH = "WATCH"
STATE_MODERATE = "MODERATE_STRESS"
STATE_SEVERE = "SEVERE_STRESS"
STATE_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"

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


def _compute_expanding_percentile_stress(group_df: pd.DataFrame, val_col: str) -> pd.DataFrame:
    vals = group_df[val_col].values
    flags = group_df["quality_flags"].values if "quality_flags" in group_df.columns else np.full(len(vals), "")
    
    n = len(vals)
    percentiles = np.full(n, np.nan)
    counts = np.zeros(n, dtype=int)
    
    is_valid = np.array([not _has_quality_flags(f, DISQUALIFYING_FLAGS) for f in flags])
    valid_vals = np.where(is_valid, vals, np.nan)
    
    for i in range(n):
        ref = valid_vals[:i]
        valid_ref = ref[~np.isnan(ref)]
        n_valid = len(valid_ref)
        counts[i] = n_valid
        
        curr = vals[i]
        
        if n_valid >= MIN_HISTORY_YEARS_STRESS and is_valid[i] and not np.isnan(curr):
            less = np.sum(valid_ref > curr)
            equal = np.sum(valid_ref == curr)
            percentiles[i] = (less + 0.5 * equal) / n_valid * 100.0
            
    out_df = group_df.copy()
    out_df["groundwater_percentile"] = percentiles
    out_df["eligible_history_years"] = counts
    return out_df


def _calculate_persistence_stress(df: pd.DataFrame) -> pd.DataFrame:
    deficit_mask = df["groundwater_percentile"] < DEFICIT_P25
    deficit_mask = deficit_mask & (df["eligible_history_years"] >= MIN_HISTORY_YEARS_STRESS)
    
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


def _compute_expanding_trend(group_df: pd.DataFrame, val_col: str, date_col: str) -> pd.DataFrame:
    """
    Computes an expanding linear trend strictly backward-looking.
    For index i, reference distribution is [0, i-1].
    Group is assumed to be sorted chronologically by date.
    Returns slope_per_year.
    """
    vals = group_df[val_col].values
    dates = pd.to_datetime(group_df[date_col]).values
    flags = group_df["quality_flags"].values if "quality_flags" in group_df.columns else np.full(len(vals), "")
    
    n = len(vals)
    slopes = np.full(n, np.nan)
    
    is_valid = np.array([not _has_quality_flags(f, DISQUALIFYING_FLAGS) for f in flags])
    valid_vals = np.where(is_valid, vals, np.nan)
    
    # For dates, we can convert to days since start
    if n > 0:
        first_date = dates[0]
        # Calculate days difference safely
        # Note: dates is a numpy array of datetime64[ns]
        days = (dates - first_date).astype('timedelta64[D]').astype(float)
    else:
        days = np.zeros(n)

    for i in range(n):
        ref_vals = valid_vals[:i]
        ref_days = days[:i]
        
        # Filter NaNs
        mask = ~np.isnan(ref_vals)
        valid_ref_vals = ref_vals[mask]
        valid_ref_days = ref_days[mask]
        
        n_valid = len(valid_ref_vals)
        
        if n_valid >= MIN_HISTORY_YEARS_STRESS and is_valid[i] and not np.isnan(vals[i]):
            # Check year span
            year_span = (valid_ref_days[-1] - valid_ref_days[0]) / 365.25 if n_valid > 0 else 0
            if year_span >= MIN_HISTORY_YEARS_STRESS:
                # Calculate OLS slope
                # Note: valid_ref_days might have variance zero if all same, but year_span >= 5 prevents this
                try:
                    slope, _, _, _, _ = stats.linregress(valid_ref_days, valid_ref_vals)
                    slopes[i] = slope * 365.25 # slope per year
                except:
                    pass

    out_df = group_df.copy()
    out_df["long_term_trend_slope"] = slopes
    
    # Trend direction: positive slope = deeper water = declining condition
    # Negative slope = shallower water = improving condition
    def get_dir(s):
        if pd.isna(s):
            return "NOT_SIGNIFICANT"
        if s > 0:
            return "DECREASING" # Groundwater condition is decreasing/worsening
        elif s < 0:
            return "INCREASING" # Groundwater condition is increasing/improving
        return "STABLE"
        
    out_df["trend_direction"] = [get_dir(s) for s in slopes]
    return out_df


def compute_scarcity_intelligence(df: pd.DataFrame, is_india: bool = True, region_col: str = "district") -> pd.DataFrame:
    """
    Computes Groundwater Stress Intelligence (M12).
    """
    df_out = df.copy()
    site_col = "candidate_site_id"
    season_col = "analytical_season" if is_india else "month"
    val_col = "water_level_raw"
    date_col = "observation_date" if is_india else "observation_timestamp"
    
    if len(df_out) == 0:
        return df_out
        
    df_out["_orig_index"] = df_out.index
    df_out["_parsed_date"] = pd.to_datetime(df_out[date_col], errors="coerce")
    
    # 1. Calculate historical percentiles (grouped by site and season)
    # Reusing M10 drought logic for expanding percentile
    df_out = df_out.sort_values([site_col, season_col, "_parsed_date"]).reset_index(drop=True)
    
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter(action='ignore', category=FutureWarning)
        processed = df_out.groupby([site_col, season_col], group_keys=False).apply(
            _compute_expanding_percentile_stress, val_col=val_col
        )
        
    # 2. Calculate persistence (grouped by site, sorted by date across all seasons)
    processed = processed.sort_values([site_col, "_parsed_date"]).reset_index(drop=True)
    processed = _calculate_persistence_stress(processed) # Adds consecutive_deficit_seasons
    
    # 3. Calculate expanding trend strictly backward-looking
    with warnings.catch_warnings():
        warnings.simplefilter(action='ignore', category=FutureWarning)
        processed = processed.groupby(site_col, group_keys=False).apply(
            _compute_expanding_trend, val_col=val_col, date_col="_parsed_date"
        )
    
    # 4. Spatial Aggregation (grouped by region, year, season)
    processed["observation_year"] = processed["_parsed_date"].dt.year
    
    # Eligibility for stress: requires >= 5 years history for both percentile and trend
    processed["_is_eligible"] = (processed["eligible_history_years"] >= MIN_HISTORY_YEARS_STRESS) & \
                                (~processed["long_term_trend_slope"].isna())
    
    processed["_is_stressed_site"] = (processed["groundwater_percentile"] < DEFICIT_P25) & \
                                     (processed["consecutive_deficit_seasons"] >= PERSISTENCE_MIN_SEASONS_STRESS) & \
                                     (processed["long_term_trend_slope"] > 0)
    
    region_stats = processed.groupby([region_col, "observation_year", season_col]).agg(
        eligible_site_count=("_is_eligible", "sum"),
        stressed_site_count=("_is_stressed_site", "sum")
    ).reset_index()
    
    region_stats["spatial_stress_fraction"] = np.where(
        region_stats["eligible_site_count"] > 0,
        region_stats["stressed_site_count"] / region_stats["eligible_site_count"],
        np.nan
    )
    
    processed = processed.merge(
        region_stats[[region_col, "observation_year", season_col, 
                      "spatial_stress_fraction"]],
        on=[region_col, "observation_year", season_col],
        how="left"
    )
    
    # Determine State
    def determine_state(row):
        if not row["_is_eligible"] or pd.isna(row["spatial_stress_fraction"]):
            return STATE_INSUFFICIENT
            
        persistent_low = (row["consecutive_deficit_seasons"] >= PERSISTENCE_MIN_SEASONS_STRESS)
        negative_trend = (row["long_term_trend_slope"] > 0)
        severe_low = (row["groundwater_percentile"] < DEFICIT_P10)
        regional_clustering = (row["spatial_stress_fraction"] >= REGIONAL_COVERAGE_STRESS)
        
        if severe_low and persistent_low and negative_trend and regional_clustering:
            return STATE_SEVERE
        elif persistent_low and negative_trend:
            return STATE_MODERATE
        elif persistent_low:
            return STATE_WATCH
        else:
            return STATE_NORMAL
            
    processed["stress_state"] = processed.apply(determine_state, axis=1)
    
    # Calculate evidence count for valid eligible rows
    def count_evidence(row):
        if not row["_is_eligible"]:
            return 0
        c = 0
        if row["consecutive_deficit_seasons"] >= PERSISTENCE_MIN_SEASONS_STRESS:
            c += 1
        if row["long_term_trend_slope"] > 0:
            c += 1
        if row["groundwater_percentile"] < DEFICIT_P10:
            c += 1
        if row["spatial_stress_fraction"] >= REGIONAL_COVERAGE_STRESS:
            c += 1
        return c
        
    processed["evidence_count"] = processed.apply(count_evidence, axis=1)
    
    processed["weather_context_available"] = not is_india
    processed["demand_data_available"] = False
    processed["methodology_version"] = METHODOLOGY_VERSION
    
    # Sort back to original
    processed = processed.sort_values("_orig_index").reset_index(drop=True)
    
    output_cols = [
        site_col,
        date_col,
        "groundwater_percentile",
        "consecutive_deficit_seasons",
        "long_term_trend_slope",
        "trend_direction",
        "spatial_stress_fraction",
        "weather_context_available",
        "demand_data_available",
        "evidence_count",
        "stress_state",
        "methodology_version"
    ]
    
    return processed[output_cols]
