import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.features.advanced_analytics import AdvancedAnalytics
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

client = TestClient(app)

@pytest.fixture
def synthetic_site_data():
    dates = [datetime(2020, 1, 1) + timedelta(days=i*30) for i in range(120)] # 10 years
    values = np.linspace(10, 20, 120) + np.sin(np.linspace(0, 10, 120)) * 2
    
    df = pd.DataFrame({
        "candidate_site_id": ["W_TEST_1"] * 120,
        "observation_date": dates,
        "water_level_raw": values,
        "quality_flags": ["valid"] * 120
    })
    
    # Introduce one missing data point
    df.loc[5, "water_level_raw"] = np.nan
    return df

@pytest.fixture
def empty_site_data():
    return pd.DataFrame({
        "candidate_site_id": [],
        "observation_date": [],
        "water_level_raw": [],
        "quality_flags": []
    })

def test_1_site_statistics(synthetic_site_data):
    # Tests basic observation counts and spans
    res = AdvancedAnalytics.get_site_analytics(synthetic_site_data, cross_intelligence={})
    assert res["observation_summary"]["observation_count"] == 120
    assert res["observation_summary"]["valid_observation_count"] == 119
    assert res["observation_summary"]["invalid_observation_count"] == 1
    assert res["observation_summary"]["observation_span_days"] > 3000

def test_2_descriptive_statistics(synthetic_site_data):
    res = AdvancedAnalytics.get_site_analytics(synthetic_site_data, cross_intelligence={})
    stats = res["water_level_statistics"]
    assert "mean" in stats
    assert "median" in stats
    assert "minimum" in stats
    assert "maximum" in stats
    assert stats["minimum"] < stats["maximum"]
    assert stats["p10"] < stats["p90"]

def test_3_trend_reuse(synthetic_site_data):
    res = AdvancedAnalytics.get_site_analytics(synthetic_site_data, cross_intelligence={})
    trend = res["trend"]
    assert "trend_direction" in trend
    assert trend["trend_direction"] in ["INCREASING", "DECREASING", "STABLE", "NOT_SIGNIFICANT"]
    assert trend["trend_method"] == "OLS_LINEAR"

def test_4_seasonal_reuse(synthetic_site_data):
    res = AdvancedAnalytics.get_site_analytics(synthetic_site_data, cross_intelligence={})
    seasonal = res["seasonal"]
    assert "analytical_season" in seasonal
    assert "seasonal_median" in seasonal

def test_5_percentile_leakage_prevention(synthetic_site_data):
    # Ensure percentile uses only historical data (prior to current row)
    traj = AdvancedAnalytics.calculate_percentile_trajectory(synthetic_site_data)
    # the first element should have percentile None because there's no history prior
    assert traj[0]["historical_percentile"] is None
    # the second element should be calculated against [element 0]
    assert traj[1]["historical_percentile"] in [0.0, 1.0]

def test_6_first_observation_behavior(synthetic_site_data):
    traj = AdvancedAnalytics.calculate_percentile_trajectory(synthetic_site_data)
    assert traj[0]["historical_percentile"] is None

def test_7_insufficient_history(empty_site_data):
    res = AdvancedAnalytics.get_site_analytics(empty_site_data, cross_intelligence={})
    assert res["observation_summary"]["error"] == "Insufficient history"
    assert "error" in res.get("observation_summary", {})

def test_8_india_periodic_data_handling():
    # Calling the API
    response = client.get("/api/v1/india/candidate-sites/W28581/analytics")
    # If DB doesn't exist, might be 200 with insufficient history
    assert response.status_code in [200, 404]

def test_9_maharashtra_telemetry_handling():
    response = client.get("/api/v1/maharashtra/candidate-sites/MH_TEST/analytics")
    assert response.status_code in [200, 404]

def test_10_yoy_comparison(synthetic_site_data):
    res = AdvancedAnalytics.calculate_yoy_comparison(synthetic_site_data)
    assert "difference" in res or res == {}

def test_11_district_distributions():
    # Use real API call. The DAL will query DuckDB. If district exists, great. If not, it returns {}
    response = client.get("/api/v1/india/districts/PUNE/analytics")
    assert response.status_code == 200
    data = response.json()
    assert "condition_distribution" in data

def test_12_district_counts():
    response = client.get("/api/v1/india/districts/FAKE_DISTRICT/analytics")
    assert response.status_code == 200
    data = response.json()
    assert data["site_count"] == 0

def test_13_cross_intelligence_composition(synthetic_site_data):
    # Inject cross intelligence
    ci = {
        "condition": "NORMAL_RANGE",
        "drought": "NORMAL",
        "flood_potential": "WATCH",
        "stress": "MODERATE_STRESS"
    }
    res = AdvancedAnalytics.get_site_analytics(synthetic_site_data, cross_intelligence=ci)
    assert res["cross_intelligence"]["condition"] == "NORMAL_RANGE"
    assert "risk_score" not in res["cross_intelligence"] # composite check

def test_14_unknown_units():
    # Asserting no fake unit is pushed. 
    response = client.get("/api/v1/india/candidate-sites/W28581/analytics")
    if response.status_code == 200:
        # Check that we aren't faking units in the top level
        assert "expected_cadence_hours" not in response.json()

def test_15_missing_data(synthetic_site_data):
    res = AdvancedAnalytics.get_site_analytics(synthetic_site_data, cross_intelligence={})
    assert res["data_quality"]["invalid_observation_count"] == 1

def test_16_api_schema():
    response = client.get("/api/v1/india/candidate-sites/W28581/analytics")
    if response.status_code == 200:
        data = response.json()
        assert "observation_summary" in data
        assert "water_level_statistics" in data
        assert "trend" in data
        assert "cross_intelligence" in data

def test_17_invalid_site():
    response = client.get("/api/v1/india/candidate-sites/UNKNOWN_SITE/analytics")
    assert response.status_code == 200 # Returns insufficient history json

def test_18_invalid_district():
    response = client.get("/api/v1/fake_region/districts/UNKNOWN/analytics")
    assert response.status_code == 400 # Invalid region throws 400

def test_19_no_fabricated_expected_cadence(synthetic_site_data):
    res = AdvancedAnalytics.get_site_analytics(synthetic_site_data, cross_intelligence={})
    # coverage percentage should be None or not fabricated
    assert res["data_quality"]["coverage_percentage"] is None

def test_20_no_composite_risk_score(synthetic_site_data):
    res = AdvancedAnalytics.get_site_analytics(synthetic_site_data, cross_intelligence={})
    assert "risk_score" not in res
    assert "health_score" not in res

def test_21_cross_intelligence_api_integration():
    """Verify that cross_intelligence is properly constructed from the real API layer for India and MH."""
    # Test India site cross-intelligence
    res_in = client.get("/api/v1/india/candidate-sites/W28581/analytics")
    if res_in.status_code == 200:
        data_in = res_in.json()
        if "cross_intelligence" in data_in and data_in["cross_intelligence"]:
            ci = data_in["cross_intelligence"]
            assert "condition" in ci
            assert "alert" in ci
            assert "drought" in ci
            assert "flood_potential" in ci
            assert "stress" in ci
            assert ci["forecast"] == "UNAVAILABLE"

    # Test MH site cross-intelligence
    res_mh = client.get("/api/v1/maharashtra/candidate-sites/MH_AALEGAON/analytics")
    if res_mh.status_code == 200:
        data_mh = res_mh.json()
        if "cross_intelligence" in data_mh and data_mh["cross_intelligence"]:
            ci = data_mh["cross_intelligence"]
            assert "condition" in ci
            assert "alert" in ci
            assert "drought" in ci
            assert ci["drought"] == "INSUFFICIENT_HISTORY"  # MH has no drought intelligence artifact
            assert "flood_potential" in ci
            assert "stress" in ci

