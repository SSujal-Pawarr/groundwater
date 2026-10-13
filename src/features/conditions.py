"""
NEW/src/features/conditions.py - Groundwater Condition Engine (M8.2-D)

Implements statistically defensible, backward-looking absolute condition states
using Historical Percentile Ranking.

Scientific constraints:
- Condition states represent statistical positions, NOT physical interpretations 
  like 'Drought' or 'Flood'.
- Strictly backward-looking to prevent data leakage.
- Excludes records flagged with invalid quality flags.
- Requires a minimum historical sample size.
"""

from typing import Optional, Dict
import numpy as np
import pandas as pd

# M8.2-D Approved Configuration
CONDITION_VERSION = "M8.2-D-v1"

STATE_EXTREMELY_LOW = "EXTREMELY_LOW"
STATE_LOW = "LOW"
STATE_NORMAL = "NORMAL_RANGE"
STATE_HIGH = "HIGH"
STATE_EXTREMELY_HIGH = "EXTREMELY_HIGH"
STATE_INSUFFICIENT = "INSUFFICIENT_HISTORY"

DEFAULT_MIN_HISTORY = 5

DISQUALIFYING_FLAGS = {
    "INVALID_OR_EMPTY",
    "UNREALISTIC_WATER_LEVEL",
    "CONFLICTING_DUPLICATE"
}

def _has_quality_flags(flags: str, disqualifying: set) -> bool:
    if pd.isna(flags) or not flags:
        return False
    row_flags = set(flags.split(";"))
    return len(row_flags.intersection(disqualifying)) > 0


def _compute_expanding_percentile(group_df: pd.DataFrame, val_col: str, min_history: int) -> pd.DataFrame:
    """
    Computes an expanding percentile strictly backward-looking.
    For index i, reference distribution is [0, i-1].
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
        if n_valid >= min_history and is_valid[i] and not np.isnan(curr):
            less = np.sum(valid_ref < curr)
            equal = np.sum(valid_ref == curr)
            # Scipy kind='mean' logic
            percentiles[i] = (less + 0.5 * equal) / n_valid * 100.0
            
    out_df = group_df.copy()
    out_df["percentile"] = percentiles
    out_df["historical_sample_count"] = counts
    return out_df


def _compute_grouped_percentiles(
    df: pd.DataFrame,
    group_columns: list[str],
    val_col: str,
    min_history: int,
) -> pd.DataFrame:
    """Apply the expanding calculation per group while retaining group columns.

    Iterating groups avoids pandas-version changes to ``groupby.apply`` that can
    remove grouping columns from the returned frame.
    """
    results = [
        _compute_expanding_percentile(group, val_col=val_col, min_history=min_history)
        for _, group in df.groupby(group_columns, sort=False, dropna=False)
    ]
    if not results:
        return df.assign(percentile=np.nan, historical_sample_count=0)
    return pd.concat(results).sort_index()


def _assign_condition_state(percentile: float) -> str:
    """
    Maps a percentile [0.0, 100.0] to a neutral statistical condition state.
    """
    if pd.isna(percentile):
        return STATE_INSUFFICIENT
    
    if percentile < 10.0:
        return STATE_EXTREMELY_LOW
    elif percentile < 25.0:
        return STATE_LOW
    elif percentile <= 75.0:
        return STATE_NORMAL
    elif percentile <= 90.0:
        return STATE_HIGH
    else:
        return STATE_EXTREMELY_HIGH


def compute_india_conditions(df: pd.DataFrame, min_history: int = DEFAULT_MIN_HISTORY) -> pd.DataFrame:
    """
    Computes condition states for India periodic data.
    Grouped strictly by location and analytical season to prevent dry vs wet season leakage.
    """
    df_out = df.copy()
    site_col = "candidate_site_id"
    season_col = "analytical_season"
    val_col = "water_level_raw"
    date_col = "observation_date"
    
    df_out["_orig_index"] = df_out.index
    
    # Must sort chronologically
    df_out["_parsed_date"] = pd.to_datetime(df_out[date_col], errors="coerce")
    df_out = df_out.sort_values([site_col, season_col, "_parsed_date"]).reset_index(drop=True)
    
    # Compute percentiles
    processed = _compute_grouped_percentiles(
        df_out,
        group_columns=[site_col, season_col],
        val_col=val_col,
        min_history=min_history,
    )
    
    processed["condition_state"] = processed["percentile"].apply(_assign_condition_state)
    processed["historical_reference_group"] = processed[season_col]
    processed["condition_method_version"] = CONDITION_VERSION
    
    # Re-sort to original input order
    processed = processed.sort_values("_orig_index").set_index("_orig_index")
    processed.index.name = None
    processed = processed.drop(columns=["_parsed_date"])
    
    return processed


def compute_maharashtra_conditions(df: pd.DataFrame, min_history: int = DEFAULT_MIN_HISTORY) -> pd.DataFrame:
    """
    Computes condition states for Maharashtra telemetry data.
    Grouped strictly by location and observation month for fine-grained operational monitoring.
    """
    df_out = df.copy()
    site_col = "candidate_site_id"
    val_col = "water_level_raw"
    ts_col = "observation_timestamp"
    
    df_out["_orig_index"] = df_out.index
    df_out["_parsed_ts"] = pd.to_datetime(df_out[ts_col], errors="coerce")
    df_out["_month"] = df_out["_parsed_ts"].dt.month.fillna(0).astype(int)
    df_out["historical_reference_group"] = "MONTH_" + df_out["_month"].astype(str).str.zfill(2)
    
    # Must sort chronologically
    df_out = df_out.sort_values([site_col, "_month", "_parsed_ts"]).reset_index(drop=True)
    
    processed = _compute_grouped_percentiles(
        df_out,
        group_columns=[site_col, "_month"],
        val_col=val_col,
        min_history=min_history,
    )
    
    processed["condition_state"] = processed["percentile"].apply(_assign_condition_state)
    processed["condition_method_version"] = CONDITION_VERSION
    
    # Re-sort to original input order
    processed = processed.sort_values("_orig_index").set_index("_orig_index")
    processed.index.name = None
    processed = processed.drop(columns=["_parsed_ts", "_month"])
    
    return processed
