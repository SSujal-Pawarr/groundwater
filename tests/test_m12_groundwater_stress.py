import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from features.groundwater_stress import (
    compute_scarcity_intelligence,
    STATE_NORMAL,
    STATE_WATCH,
    STATE_MODERATE,
    STATE_SEVERE,
    STATE_INSUFFICIENT,
    MIN_HISTORY_YEARS_STRESS,
    PERSISTENCE_MIN_SEASONS_STRESS,
    REGIONAL_COVERAGE_STRESS,
    DEFICIT_P25,
    DEFICIT_P10
)

def _generate_synthetic_history(site_id, num_years, start_year=2000, deficit=False, severe=False, trend="stable", region="D1"):
    dates = []
    vals = []
    
    current_val = 5.0  # start depth
    
    for y in range(num_years):
        for season in [1, 4, 8, 11]: # approx months
            dates.append(f"{start_year+y}-{season:02d}-01")
            
            if deficit:
                if severe:
                    # very deep
                    vals.append(current_val + 10.0)
                else:
                    vals.append(current_val + 5.0)
            else:
                vals.append(current_val)
                
            if trend == "increasing_depth":
                current_val += 0.5  # structurally worsening
            elif trend == "decreasing_depth":
                current_val -= 0.5  # structurally improving
                
    df = pd.DataFrame({
        "candidate_site_id": [site_id] * len(dates),
        "district": [region] * len(dates),
        "analytical_season": [d.split("-")[1] for d in dates],
        "observation_date": dates,
        "water_level_raw": vals,
        "quality_flags": [""] * len(dates)
    })
    
    return df


def test_insufficient_history_exclusion():
    # Only 3 years of history, requires 5
    df = _generate_synthetic_history("s1", 3)
    res = compute_scarcity_intelligence(df, is_india=True, region_col="district")
    assert all(res["stress_state"] == STATE_INSUFFICIENT)


def test_demand_data_explicitly_false():
    df = _generate_synthetic_history("s1", 6)
    res = compute_scarcity_intelligence(df, is_india=True, region_col="district")
    assert all(res["demand_data_available"] == False)


def test_normal_state():
    # 6 years, stable, no deficit
    df = _generate_synthetic_history("s1", 6)
    res = compute_scarcity_intelligence(df, is_india=True, region_col="district")
    
    # First 5 years (20 obs) will be insufficient
    assert res.iloc[-1]["stress_state"] == STATE_NORMAL
    assert res.iloc[-1]["long_term_trend_slope"] <= 0  # not worsening


def test_watch_state():
    # To get watch: persistent deficit, but NO negative structural trend.
    # We will make a long strong improving trend (decreasing depth)
    df1 = _generate_synthetic_history("s1", 10, start_year=2000, trend="decreasing_depth") # Improving
    # Just a small jump for the last year so it falls below its own historical P25, but doesn't flip the trend.
    df2 = _generate_synthetic_history("s1", 2, start_year=2010, deficit=True, severe=False, trend="decreasing_depth")
    df = pd.concat([df1, df2]).reset_index(drop=True)
    
    res = compute_scarcity_intelligence(df, is_india=True, region_col="district")
    last_row = res.iloc[-1]
    
    assert last_row["consecutive_deficit_seasons"] >= PERSISTENCE_MIN_SEASONS_STRESS
    # The trend is negative (getting shallower overall because decreasing_depth means depth is shrinking)
    assert last_row["long_term_trend_slope"] < 0
    assert last_row["stress_state"] == STATE_WATCH


def test_moderate_stress_state():
    # Persistent deficit AND negative structural trend (worsening depth)
    df = _generate_synthetic_history("s1", 8, start_year=2000, deficit=True, trend="increasing_depth")
    res = compute_scarcity_intelligence(df, is_india=True, region_col="district")
    last_row = res.iloc[-1]
    
    assert last_row["consecutive_deficit_seasons"] >= PERSISTENCE_MIN_SEASONS_STRESS
    assert last_row["long_term_trend_slope"] > 0
    # Because only 1 site in district, spatial fraction is 1.0, but it might hit SEVERE if severe low.
    # We used deficit=True, severe=False, so percentile shouldn't be < P10
    
    # We force percentile calculation check
    assert last_row["stress_state"] in [STATE_MODERATE, STATE_SEVERE]


def test_spatial_aggregation_prevents_single_site_failure():
    # District D1 has 4 sites.
    # 3 are normal. 1 is severe stress.
    # Fraction = 0.25 < 0.33. Should only reach MODERATE, not SEVERE.
    
    df1 = _generate_synthetic_history("s1", 6, start_year=2000, deficit=True, severe=True, trend="increasing_depth")
    df2 = _generate_synthetic_history("s2", 6, start_year=2000, deficit=False)
    df3 = _generate_synthetic_history("s3", 6, start_year=2000, deficit=False)
    df4 = _generate_synthetic_history("s4", 6, start_year=2000, deficit=False)
    
    df = pd.concat([df1, df2, df3, df4]).reset_index(drop=True)
    res = compute_scarcity_intelligence(df, is_india=True, region_col="district")
    
    # Check last observation of s1
    s1_res = res[(res["candidate_site_id"] == "s1")].iloc[-1]
    assert s1_res["spatial_stress_fraction"] == 0.25
    assert s1_res["stress_state"] == STATE_MODERATE # downgraded from SEVERE because 0.25 < 0.33


def test_severe_stress():
    # District D1 has 4 sites.
    # 2 are severe stress. 2 are normal.
    # Fraction = 0.50 > 0.33. Should reach SEVERE.
    
    df1 = _generate_synthetic_history("s1", 8, start_year=2000, deficit=True, severe=True, trend="increasing_depth")
    df2 = _generate_synthetic_history("s2", 8, start_year=2000, deficit=True, severe=True, trend="increasing_depth")
    df3 = _generate_synthetic_history("s3", 8, start_year=2000, deficit=False)
    df4 = _generate_synthetic_history("s4", 8, start_year=2000, deficit=False)
    
    df = pd.concat([df1, df2, df3, df4]).reset_index(drop=True)
    res = compute_scarcity_intelligence(df, is_india=True, region_col="district")
    
    s1_res = res[(res["candidate_site_id"] == "s1")].iloc[-1]
    assert s1_res["spatial_stress_fraction"] == 0.50
    assert s1_res["stress_state"] == STATE_SEVERE


def test_maharashtra_short_history():
    # Maharashtra data comes in with short history
    # Even if we pretend it's 3 years, the threshold requires 5
    df = pd.DataFrame({
        "candidate_site_id": ["s1"] * 10,
        "district": ["D1"] * 10,
        "month": ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"],
        "observation_timestamp": [f"2023-{str(i).zfill(2)}-01 00:00:00" for i in range(1, 11)],
        "water_level_raw": [5.0] * 10,
        "quality_flags": [""] * 10
    })
    
    res = compute_scarcity_intelligence(df, is_india=False, region_col="district")
    assert all(res["stress_state"] == STATE_INSUFFICIENT)
    assert all(res["weather_context_available"] == True)
