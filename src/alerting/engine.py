"""
NEW/src/alerting/engine.py - Causal Early-Warning Alert Engine

Implements strictly backward-looking early-warning state generation and operational state machine.
"""

import numpy as np
import pandas as pd
from typing import Optional
from .config import AlertConfig

def _has_quality_flags(flags: str, disqualifying_flags: set) -> bool:
    if pd.isna(flags) or not flags:
        return False
    row_flags = set(flags.split(";"))
    return len(row_flags.intersection(disqualifying_flags)) > 0

def _apply_state_machine(states: np.ndarray, config: AlertConfig) -> np.ndarray:
    """
    Applies the operational state machine over a chronological array of instantaneous states.
    Handles escalations and cooldown recoveries.
    """
    out_states = np.empty_like(states, dtype=object)
    current_active_state = config.STATE_NORMAL
    cooldown_counter = 0
    
    non_operational = {config.STATE_INSUFFICIENT_HISTORY, config.STATE_GAPPED, config.STATE_DATA_QUALITY}
    
    for i, inst_state in enumerate(states):
        # Pass-through non-operational instantaneous states (like quality issues or gaps)
        # They do not clear the underlying active state, but they mask it for this row.
        if inst_state in non_operational:
            out_states[i] = inst_state
            continue
            
        inst_rank = config.SEVERITY_RANK.get(inst_state, 0)
        curr_rank = config.SEVERITY_RANK.get(current_active_state, 0)
        
        if inst_rank > curr_rank:
            # Immediate escalation
            current_active_state = inst_state
            cooldown_counter = 0
        elif inst_rank > 0 and inst_rank <= curr_rank:
            # Still in an anomalous state, reset cooldown, keep current highest state (or maybe degrade? Policy: only degrade on NORMAL cooldown)
            cooldown_counter = 0
        elif inst_rank == 0 and curr_rank > 0:
            # Instantaneous is NORMAL, but we are in an active alert
            cooldown_counter += 1
            if cooldown_counter >= config.recovery_cooldown_periods:
                current_active_state = config.STATE_NORMAL
                cooldown_counter = 0
        
        out_states[i] = current_active_state
        
    return out_states

def generate_india_alerts(
    df: pd.DataFrame, 
    config: Optional[AlertConfig] = None
) -> pd.DataFrame:
    """
    Generates causal alerts for India periodic dataset.
    Uses strictly backward-looking seasonal statistics and applies state machine.
    """
    if config is None:
        config = AlertConfig()
        
    df_out = df.copy()
    
    site_col = "candidate_site_id"
    season_col = "analytical_season"
    year_col = "observation_year"
    val_col = "water_level_raw"
    date_col = "observation_date"
    
    df_out[year_col] = pd.to_numeric(df_out[year_col], errors="coerce")
    df_out = df_out.sort_values([site_col, season_col, year_col]).reset_index(drop=True)
    
    annual_seasonal = df_out.groupby([site_col, season_col, year_col], as_index=False)[val_col].mean()
    annual_seasonal = annual_seasonal.sort_values([site_col, season_col, year_col])
    
    annual_seasonal["hist_sum"] = annual_seasonal.groupby([site_col, season_col])[val_col].cumsum() - annual_seasonal[val_col]
    annual_seasonal["hist_count"] = annual_seasonal.groupby([site_col, season_col]).cumcount()
    
    annual_seasonal["val_sq"] = annual_seasonal[val_col] ** 2
    annual_seasonal["hist_sq_sum"] = annual_seasonal.groupby([site_col, season_col])["val_sq"].cumsum() - annual_seasonal["val_sq"]
    
    annual_seasonal["historical_reference"] = annual_seasonal["hist_sum"] / annual_seasonal["hist_count"]
    
    annual_seasonal["historical_var"] = (
        annual_seasonal["hist_sq_sum"] - (annual_seasonal["hist_sum"] ** 2 / annual_seasonal["hist_count"])
    ) / (annual_seasonal["hist_count"] - 1)
    
    annual_seasonal["historical_std"] = np.sqrt(np.maximum(0, annual_seasonal["historical_var"]))
    
    df_out = df_out.merge(
        annual_seasonal[[site_col, season_col, year_col, "historical_reference", "historical_std", "hist_count"]],
        on=[site_col, season_col, year_col],
        how="left"
    )
    
    df_out["historical_sample_count"] = df_out["hist_count"].fillna(0).astype(int)
    df_out["deviation"] = df_out[val_col] - df_out["historical_reference"]
    
    df_out["standardized_score"] = np.where(
        df_out["historical_std"] > 1e-6,
        df_out["deviation"] / df_out["historical_std"],
        np.nan
    )
    
    def determine_inst_state(row):
        if not row.get("is_analytics_ready", True) or _has_quality_flags(row.get("quality_flags", ""), config.disqualifying_flags):
            return config.STATE_DATA_QUALITY
        if row["historical_sample_count"] < config.india_min_historical_years:
            return config.STATE_INSUFFICIENT_HISTORY
        z = row["standardized_score"]
        if pd.isna(z):
            return config.STATE_INSUFFICIENT_HISTORY
        abs_z = abs(z)
        if abs_z >= config.india_z_critical:
            return config.STATE_CRITICAL
        elif abs_z >= config.india_z_warning:
            return config.STATE_WARNING
        elif abs_z >= config.india_z_watch:
            return config.STATE_WATCH
        return config.STATE_NORMAL
            
    df_out["instantaneous_state"] = df_out.apply(determine_inst_state, axis=1)
    
    # Sort strictly chronologically for the state machine
    df_out["_parsed_date"] = pd.to_datetime(df_out[date_col], errors="coerce")
    df_out = df_out.sort_values([site_col, "_parsed_date"]).reset_index(drop=True)
    df_out["time_since_previous_obs_days"] = df_out.groupby(site_col)["_parsed_date"].diff().dt.days
    
    # Apply State Machine per site
    df_out["alert_event_state"] = df_out.groupby(site_col)["instantaneous_state"].transform(
        lambda s: _apply_state_machine(s.values, config)
    )
    
    df_out = df_out.drop(columns=["_parsed_date", "hist_count"])
    df_out["detector_version"] = "India_Seasonal_Causal_v2.0"
    
    return df_out


def generate_maharashtra_alerts(
    df: pd.DataFrame,
    config: Optional[AlertConfig] = None
) -> pd.DataFrame:
    """
    Generates causal alerts for Maharashtra continuous telemetry.
    Uses strictly backward-looking normalized persistence residuals and applies state machine.
    """
    if config is None:
        config = AlertConfig()
        
    df_out = df.copy()
    
    station_col = "station_name"
    ts_col = "observation_timestamp"
    val_col = "water_level_raw"
    
    df_out["_parsed_ts"] = pd.to_datetime(df_out[ts_col], errors="coerce")
    df_out = df_out.sort_values([station_col, "_parsed_ts"]).reset_index(drop=True)
    
    df_out["time_since_previous_obs_hours"] = df_out.groupby(station_col)["_parsed_ts"].diff().dt.total_seconds() / 3600
    
    # Strictly prior reference
    df_out["historical_reference"] = df_out.groupby(station_col)[val_col].shift(1)
    df_out["deviation"] = df_out[val_col] - df_out["historical_reference"]
    
    # Strictly backward-looking robust scale (using rolling std on prior deviations over 30 observations max)
    # We use expanding variance but bounded by a window, shifted by 1 to ensure no leakage from the current row.
    
    # To compute causal historical std of the *residual*, we group by station
    # and take a rolling std of the deviation, shifted by 1.
    df_out["_prev_deviation"] = df_out.groupby(station_col)["deviation"].shift(1)
    # Window of 120 observations (approx 30 days at 4 obs/day)
    df_out["historical_std"] = df_out.groupby(station_col)["_prev_deviation"].transform(
        lambda x: x.rolling(window=120, min_periods=config.mh_min_historical_obs).std()
    )
    
    df_out["standardized_score"] = np.where(
        df_out["historical_std"] > 1e-6,
        df_out["deviation"] / df_out["historical_std"],
        np.nan
    )
    
    def determine_inst_state(row):
        if not row.get("is_analytics_ready", True) or _has_quality_flags(row.get("quality_flags", ""), config.disqualifying_flags):
            return config.STATE_DATA_QUALITY
            
        gap = row["time_since_previous_obs_hours"]
        if pd.isna(gap):
            return config.STATE_INSUFFICIENT_HISTORY
        if gap > config.mh_max_gap_hours:
            return config.STATE_GAPPED
            
        z = row["standardized_score"]
        if pd.isna(z):
            return config.STATE_INSUFFICIENT_HISTORY
            
        abs_z = abs(z)
        if abs_z >= config.mh_z_critical:
            return config.STATE_CRITICAL
        elif abs_z >= config.mh_z_warning:
            return config.STATE_WARNING
        elif abs_z >= config.mh_z_watch:
            return config.STATE_WATCH
        return config.STATE_NORMAL

    df_out["instantaneous_state"] = df_out.apply(determine_inst_state, axis=1)
    
    # Apply State Machine per station
    df_out["alert_event_state"] = df_out.groupby(station_col)["instantaneous_state"].transform(
        lambda s: _apply_state_machine(s.values, config)
    )
    
    df_out["detector_version"] = "MH_Telemetry_Residual_Causal_v2.0"
    
    df_out = df_out.drop(columns=["_parsed_ts", "_prev_deviation"])
    return df_out
