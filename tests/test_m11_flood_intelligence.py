import pytest
import pandas as pd
import numpy as np

from features.flood_intelligence import (
    compute_maharashtra_flood_potential, 
    compute_india_flood_potential,
    STATE_LOW,
    STATE_WATCH,
    STATE_ELEVATED,
    STATE_HIGH,
    STATE_INSUFFICIENT,
    METHODOLOGY_VERSION
)

def test_india_returns_insufficient_evidence():
    india_m3 = pd.DataFrame({
        'candidate_site_id': ['s1', 's2'],
        'observation_date': ['2023-01-01', '2023-05-01'],
        'quality_flags': ['', '']
    })
    
    india_cond = pd.DataFrame({
        'candidate_site_id': ['s1', 's2'],
        'observation_date': ['2023-01-01', '2023-05-01'],
        'percentile': [10.0, 90.0]  # Raw M8.2-D percentile
    })
    
    res = compute_india_flood_potential(india_m3, india_cond)
    
    assert len(res) == 2
    assert all(res['flood_potential_state'] == STATE_INSUFFICIENT)
    assert all(res['weather_data_available'] == False)
    assert all(res['evidence_count'] == 0)
    assert all(res['precipitation_trigger_flag'] == False)
    # Check that percentile was correctly inverted
    assert res.loc[0, 'groundwater_percentile'] == 90.0  # 100 - 10
    assert res.loc[1, 'groundwater_percentile'] == 10.0  # 100 - 90


def test_maharashtra_state_engine_low_and_watch():
    # Setup data where sites have no precip, or low percentile
    mh_m3 = pd.DataFrame({
        'candidate_site_id': ['s1', 's2'],
        'observation_timestamp': ['2023-01-01 00:00:00', '2023-01-01 00:00:00'],
        'district': ['D1', 'D1'],
        'quality_flags': ['', '']
    })
    
    mh_cond = pd.DataFrame({
        'candidate_site_id': ['s1', 's2'],
        'observation_timestamp': ['2023-01-01 00:00:00', '2023-01-01 00:00:00'],
        'percentile': [50.0, 10.0]  # Inverts to 50.0 (LOW) and 90.0 (WATCH)
    })
    
    mh_weath = pd.DataFrame({
        'candidate_site_id': ['s1', 's2'],
        'observation_timestamp': ['2023-01-01 00:00:00', '2023-01-01 00:00:00'],
        'water_level_raw': [10.0, 5.0],
        'precip_sum_7d': [0.0, 0.0],  # No precipitation trigger
        'precip_sum_24h': [0.0, 0.0],
        'precip_sum_3d': [0.0, 0.0],
        'precip_sum_14d': [0.0, 0.0],
        'precip_sum_30d': [0.0, 0.0]
    })
    
    res = compute_maharashtra_flood_potential(mh_m3, mh_cond, mh_weath)
    
    s1 = res[res['candidate_site_id'] == 's1'].iloc[0]
    s2 = res[res['candidate_site_id'] == 's2'].iloc[0]
    
    assert s1['flood_potential_state'] == STATE_LOW
    assert s1['groundwater_elevated_flag'] == False
    
    assert s2['flood_potential_state'] == STATE_WATCH
    assert s2['groundwater_elevated_flag'] == True
    assert s2['evidence_count'] == 1


def test_maharashtra_state_engine_high_requires_all_evidence():
    # Site 1 has high water, high precip, high rise, and is the ONLY valid site in district (100% spatial)
    mh_m3 = pd.DataFrame({
        'candidate_site_id': ['s1', 's1'],
        'observation_timestamp': ['2023-01-01 00:00:00', '2023-01-02 00:00:00'],
        'district': ['D1', 'D1'],
        'quality_flags': ['', '']
    })
    
    mh_cond = pd.DataFrame({
        'candidate_site_id': ['s1', 's1'],
        'observation_timestamp': ['2023-01-01 00:00:00', '2023-01-02 00:00:00'],
        'percentile': [10.0, 5.0]  # Inverts to 90.0, 95.0
    })
    
    mh_weath = pd.DataFrame({
        'candidate_site_id': ['s1', 's1'],
        'observation_timestamp': ['2023-01-01 00:00:00', '2023-01-02 00:00:00'],
        'water_level_raw': [10.0, 9.0],  # Rose by 1.0 meter
        'precip_sum_7d': [12.0, 15.0],  # > 10.0 mm
        'precip_sum_24h': [0.0, 0.0],
        'precip_sum_3d': [0.0, 0.0],
        'precip_sum_14d': [0.0, 0.0],
        'precip_sum_30d': [0.0, 0.0]
    })
    
    res = compute_maharashtra_flood_potential(mh_m3, mh_cond, mh_weath)
    
    day2 = res[res['observation_timestamp'] == '2023-01-02 00:00:00'].iloc[0]
    
    assert day2['groundwater_elevated_flag'] == True
    assert day2['precipitation_trigger_flag'] == True
    assert day2['groundwater_rise_rate'] == 1.0  # (10 - 9) / 1 day
    assert day2['groundwater_rise_flag'] == True
    assert day2['spatial_elevated_fraction'] == 1.0
    assert day2['spatial_trigger_flag'] == True
    assert day2['flood_potential_state'] == STATE_HIGH
    assert day2['evidence_count'] == 4
    assert day2['methodology_version'] == METHODOLOGY_VERSION


def test_invalid_observations_cannot_trigger_flood():
    mh_m3 = pd.DataFrame({
        'candidate_site_id': ['s1', 's1'],
        'observation_timestamp': ['2023-01-01 00:00:00', '2023-01-02 00:00:00'],
        'district': ['D1', 'D1'],
        'quality_flags': ['', 'INVALID_OR_EMPTY']  # Second day is invalid
    })
    
    mh_cond = pd.DataFrame({
        'candidate_site_id': ['s1', 's1'],
        'observation_timestamp': ['2023-01-01 00:00:00', '2023-01-02 00:00:00'],
        'percentile': [10.0, 5.0]
    })
    
    mh_weath = pd.DataFrame({
        'candidate_site_id': ['s1', 's1'],
        'observation_timestamp': ['2023-01-01 00:00:00', '2023-01-02 00:00:00'],
        'water_level_raw': [10.0, 9.0],
        'precip_sum_7d': [12.0, 15.0],
        'precip_sum_24h': [0.0, 0.0],
        'precip_sum_3d': [0.0, 0.0],
        'precip_sum_14d': [0.0, 0.0],
        'precip_sum_30d': [0.0, 0.0]
    })
    
    res = compute_maharashtra_flood_potential(mh_m3, mh_cond, mh_weath)
    
    day2 = res[res['observation_timestamp'] == '2023-01-02 00:00:00'].iloc[0]
    
    assert day2['flood_potential_state'] == STATE_INSUFFICIENT


def test_spatial_fraction_calculated_correctly():
    # 4 sites in district D1 on same day. 
    # Only 1 is elevated.
    # Fraction = 0.25 (which triggers True)
    
    mh_m3 = pd.DataFrame({
        'candidate_site_id': ['s1', 's2', 's3', 's4'],
        'observation_timestamp': ['2023-01-01 00:00:00'] * 4,
        'district': ['D1'] * 4,
        'quality_flags': [''] * 4
    })
    
    mh_cond = pd.DataFrame({
        'candidate_site_id': ['s1', 's2', 's3', 's4'],
        'observation_timestamp': ['2023-01-01 00:00:00'] * 4,
        'percentile': [5.0, 50.0, 60.0, 70.0]  # Only s1 is elevated
    })
    
    mh_weath = pd.DataFrame({
        'candidate_site_id': ['s1', 's2', 's3', 's4'],
        'observation_timestamp': ['2023-01-01 00:00:00'] * 4,
        'water_level_raw': [10.0, 10.0, 10.0, 10.0],
        'precip_sum_7d': [0.0] * 4,
        'precip_sum_24h': [0.0] * 4,
        'precip_sum_3d': [0.0] * 4,
        'precip_sum_14d': [0.0] * 4,
        'precip_sum_30d': [0.0] * 4
    })
    
    res = compute_maharashtra_flood_potential(mh_m3, mh_cond, mh_weath)
    
    s1 = res[res['candidate_site_id'] == 's1'].iloc[0]
    
    assert s1['spatial_elevated_fraction'] == 0.25
    assert s1['spatial_trigger_flag'] == True
    
    # What if 5 sites, 1 elevated -> 0.20 -> False
    mh_m3.loc[4] = ['s5', '2023-01-01 00:00:00', 'D1', '']
    mh_cond.loc[4] = ['s5', '2023-01-01 00:00:00', 80.0]
    mh_weath.loc[4] = ['s5', '2023-01-01 00:00:00', 10.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    
    res2 = compute_maharashtra_flood_potential(mh_m3, mh_cond, mh_weath)
    s1_res2 = res2[res2['candidate_site_id'] == 's1'].iloc[0]
    assert s1_res2['spatial_elevated_fraction'] == 0.2
    assert s1_res2['spatial_trigger_flag'] == False


def test_groundwater_percentile_orientation():
    # M8.2-D semantics: higher percentile = deeper water (e.g., 90 = very deep, dry)
    # M11 semantics: higher percentile = shallower water (e.g., 90 = very shallow, wet, flood potential)
    # This test proves the inversion: M11 percentile = 100 - M8.2-D percentile
    
    mh_m3 = pd.DataFrame({
        'candidate_site_id': ['s1', 's2'],
        'observation_timestamp': ['2023-01-01 00:00:00', '2023-01-02 00:00:00'],
        'district': ['D1', 'D1'],
        'quality_flags': ['', '']
    })
    
    mh_cond = pd.DataFrame({
        'candidate_site_id': ['s1', 's2'],
        'observation_timestamp': ['2023-01-01 00:00:00', '2023-01-02 00:00:00'],
        'percentile': [80.0, 10.0]  # s1 is deep/dry (80), s2 is shallow/wet (10)
    })
    
    mh_weath = pd.DataFrame({
        'candidate_site_id': ['s1', 's2'],
        'observation_timestamp': ['2023-01-01 00:00:00', '2023-01-02 00:00:00'],
        'water_level_raw': [10.0, 5.0],
        'precip_sum_7d': [0.0, 0.0],
        'precip_sum_24h': [0.0, 0.0],
        'precip_sum_3d': [0.0, 0.0],
        'precip_sum_14d': [0.0, 0.0],
        'precip_sum_30d': [0.0, 0.0]
    })
    
    res = compute_maharashtra_flood_potential(mh_m3, mh_cond, mh_weath)
    
    s1_res = res[res['candidate_site_id'] == 's1'].iloc[0]
    s2_res = res[res['candidate_site_id'] == 's2'].iloc[0]
    
    # s1 was deep (80 in M8.2-D). In M11 it should be low/dry (20).
    assert s1_res['groundwater_percentile'] == 20.0
    
    # s2 was shallow (10 in M8.2-D). In M11 it should be high/wet (90).
    assert s2_res['groundwater_percentile'] == 90.0
    
    # Prove that higher value = wetter/shallower groundwater position
    assert s2_res['groundwater_percentile'] > s1_res['groundwater_percentile']

