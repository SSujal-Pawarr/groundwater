"""
NEW/src/features/flood_intelligence.py - Groundwater Flood Potential Engine (M11)

Implements a transparent, rules-based Multi-Evidence Potential Engine for 
Groundwater Flood Potential.

Scientific Constraints:
- Computes flood potential, not an official flood warning.
- High groundwater alone != Flood.
- Requires multiple independent evidence signals.
- Fully backward-looking, no future weather leakage.
"""

import pandas as pd
import numpy as np

# Configurable analytical thresholds
METHODOLOGY_VERSION = "M11-FloodPotential-v1"
GW_PERCENTILE_ELEVATED = 85.0  # 85th percentile (wettest 15%)
PRECIP_7D_THRESHOLD = 10.0  # 99th percentile of current dataset distribution
RISE_RATE_THRESHOLD = 0.5  # meters per day
SPATIAL_FRACTION_THRESHOLD = 0.25  # 25% of eligible sites in district

# States
STATE_LOW = "LOW"
STATE_WATCH = "WATCH"
STATE_ELEVATED = "ELEVATED"
STATE_HIGH = "HIGH"
STATE_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"

DISQUALIFYING_FLAGS = {
    "INVALID_OR_EMPTY",
    "UNREALISTIC_WATER_LEVEL",
    "CONFLICTING_DUPLICATE"
}

def _has_quality_flags(flags: str) -> bool:
    if pd.isna(flags) or not flags:
        return False
    row_flags = set(str(flags).split(";"))
    return len(row_flags.intersection(DISQUALIFYING_FLAGS)) > 0


def compute_maharashtra_flood_potential(
    mh_m3: pd.DataFrame, 
    mh_cond: pd.DataFrame, 
    mh_weather: pd.DataFrame
) -> pd.DataFrame:
    """
    Computes flood potential for Maharashtra data.
    """
    # 1. Prepare conditions with inverted percentile (higher = shallower/wetter)
    cond = mh_cond[['candidate_site_id', 'observation_timestamp', 'percentile']].copy()
    
    # Invert the M8.2-D percentile (where 100 meant deepest)
    # We want 100 to mean shallowest/wettest.
    cond['groundwater_percentile'] = 100.0 - cond['percentile']
    cond['groundwater_elevated_flag'] = cond['groundwater_percentile'] >= GW_PERCENTILE_ELEVATED
    
    # 2. Prepare weather (sort chronologically to compute rate of change)
    weath = mh_weather.copy()
    weath['observation_timestamp_dt'] = pd.to_datetime(weath['observation_timestamp'])
    weath = weath.sort_values(['candidate_site_id', 'observation_timestamp_dt'])
    
    # Calculate rise rate
    weath['lag_1_wl'] = weath.groupby('candidate_site_id')['water_level_raw'].shift(1)
    weath['lag_1_ts'] = weath.groupby('candidate_site_id')['observation_timestamp_dt'].shift(1)
    
    weath['time_delta_hours'] = (weath['observation_timestamp_dt'] - weath['lag_1_ts']).dt.total_seconds() / 3600.0
    
    # Rise = previous level - current level (since lower raw value means shallower water)
    weath['rise_m'] = weath['lag_1_wl'] - weath['water_level_raw']
    weath['groundwater_rise_rate'] = np.where(
        weath['time_delta_hours'] > 0, 
        weath['rise_m'] / (weath['time_delta_hours'] / 24.0), 
        0.0
    )
    weath['groundwater_rise_flag'] = weath['groundwater_rise_rate'] >= RISE_RATE_THRESHOLD
    weath['precipitation_trigger_flag'] = weath['precip_sum_7d'] >= PRECIP_7D_THRESHOLD
    
    # Merge datasets
    df = mh_m3[['candidate_site_id', 'observation_timestamp', 'district', 'quality_flags']].copy()
    df = df.merge(cond, on=['candidate_site_id', 'observation_timestamp'], how='left')
    df = df.merge(
        weath[['candidate_site_id', 'observation_timestamp', 'precip_sum_24h', 'precip_sum_3d', 'precip_sum_7d', 'precip_sum_14d', 'precip_sum_30d', 'precipitation_trigger_flag', 'groundwater_rise_rate', 'groundwater_rise_flag']],
        on=['candidate_site_id', 'observation_timestamp'], 
        how='left'
    )
    
    # Filter out invalid quality records from acting as valid evidence
    df['is_valid'] = ~df['quality_flags'].apply(_has_quality_flags)
    
    # Spatial Aggregation (per day, per district)
    df['obs_date'] = pd.to_datetime(df['observation_timestamp']).dt.date
    
    # District daily valid sites
    valid_df = df[df['is_valid']].copy()
    
    district_counts = valid_df.groupby(['district', 'obs_date'])['candidate_site_id'].nunique().rename("eligible_site_count")
    elevated_counts = valid_df[valid_df['groundwater_elevated_flag'] == True].groupby(['district', 'obs_date'])['candidate_site_id'].nunique().rename("elevated_site_count")
    
    spatial_df = pd.DataFrame(district_counts).join(elevated_counts, how='left').fillna(0)
    spatial_df['spatial_elevated_fraction'] = spatial_df['elevated_site_count'] / spatial_df['eligible_site_count']
    spatial_df['spatial_trigger_flag'] = spatial_df['spatial_elevated_fraction'] >= SPATIAL_FRACTION_THRESHOLD
    
    df = df.merge(spatial_df.reset_index(), on=['district', 'obs_date'], how='left')
    
    # State Engine
    df['weather_data_available'] = df['precip_sum_7d'].notna()
    
    def determine_state(row):
        if not row['is_valid'] or pd.isna(row['groundwater_percentile']):
            return STATE_INSUFFICIENT, 0
            
        if not row['weather_data_available']:
            return STATE_INSUFFICIENT, 0
            
        evidence_count = 0
        if row['groundwater_elevated_flag']:
            evidence_count += 1
            if row['precipitation_trigger_flag']:
                evidence_count += 1
                if row['groundwater_rise_flag'] and row['spatial_trigger_flag']:
                    evidence_count += 2
                    return STATE_HIGH, evidence_count
                return STATE_ELEVATED, evidence_count
            return STATE_WATCH, evidence_count
            
        return STATE_LOW, evidence_count

    state_results = df.apply(determine_state, axis=1)
    df['flood_potential_state'] = [res[0] for res in state_results]
    df['evidence_count'] = [res[1] for res in state_results]
    df['methodology_version'] = METHODOLOGY_VERSION
    
    out_cols = [
        'candidate_site_id', 'observation_timestamp', 'groundwater_percentile', 
        'groundwater_elevated_flag', 'groundwater_rise_rate', 'groundwater_rise_flag',
        'precip_sum_24h', 'precip_sum_3d', 'precip_sum_7d', 'precip_sum_14d', 'precip_sum_30d',
        'precipitation_trigger_flag', 'spatial_elevated_fraction', 'spatial_trigger_flag',
        'weather_data_available', 'evidence_count', 'flood_potential_state', 'methodology_version'
    ]
    return df[out_cols]


def compute_india_flood_potential(india_m3: pd.DataFrame, india_cond: pd.DataFrame) -> pd.DataFrame:
    """
    Computes flood potential for India data.
    Since India data has seasonal frequency and no weather data, it always 
    returns INSUFFICIENT_EVIDENCE for acute flood potential.
    """
    cond = india_cond[['candidate_site_id', 'observation_date', 'percentile']].copy()
    
    # Invert percentile
    cond['groundwater_percentile'] = 100.0 - cond['percentile']
    cond['groundwater_elevated_flag'] = cond['groundwater_percentile'] >= GW_PERCENTILE_ELEVATED
    
    df = india_m3[['candidate_site_id', 'observation_date', 'quality_flags']].copy()
    df = df.merge(cond, on=['candidate_site_id', 'observation_date'], how='left')
    
    # Fill missing fields with NaNs/defaults to match schema
    df['groundwater_rise_rate'] = np.nan
    df['groundwater_rise_flag'] = False
    for col in ['precip_sum_24h', 'precip_sum_3d', 'precip_sum_7d', 'precip_sum_14d', 'precip_sum_30d']:
        df[col] = np.nan
    df['precipitation_trigger_flag'] = False
    df['spatial_elevated_fraction'] = np.nan
    df['spatial_trigger_flag'] = False
    
    df['weather_data_available'] = False
    df['evidence_count'] = 0
    df['flood_potential_state'] = STATE_INSUFFICIENT
    df['methodology_version'] = METHODOLOGY_VERSION
    
    # Ensure columns match (using observation_date as observation_timestamp for schema match)
    df = df.rename(columns={'observation_date': 'observation_timestamp'})
    
    out_cols = [
        'candidate_site_id', 'observation_timestamp', 'groundwater_percentile', 
        'groundwater_elevated_flag', 'groundwater_rise_rate', 'groundwater_rise_flag',
        'precip_sum_24h', 'precip_sum_3d', 'precip_sum_7d', 'precip_sum_14d', 'precip_sum_30d',
        'precipitation_trigger_flag', 'spatial_elevated_fraction', 'spatial_trigger_flag',
        'weather_data_available', 'evidence_count', 'flood_potential_state', 'methodology_version'
    ]
    return df[out_cols]
