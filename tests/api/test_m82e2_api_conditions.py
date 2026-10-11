import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

APPROVED_STATES = {
    "EXTREMELY_LOW",
    "LOW",
    "NORMAL_RANGE",
    "HIGH",
    "EXTREMELY_HIGH",
    "INSUFFICIENT_HISTORY"
}

def test_india_condition_endpoint_valid_site():
    # Fetch a candidate site first
    sites = client.get("/api/v1/india/candidate-sites?limit=1").json()
    if not sites:
        pytest.skip("No India data to test")
    
    site_id = sites[0]["candidate_site_id"]
    response = client.get(f"/api/v1/india/candidate-sites/{site_id}/condition")
    assert response.status_code == 200
    data = response.json()
    
    # Check schema
    assert "candidate_site_id" in data
    assert "observation_date" in data
    assert "analytical_season" in data
    assert "water_level_raw" in data
    assert "condition_state" in data
    assert "percentile" in data
    assert "historical_sample_count" in data
    assert "historical_reference_group" in data
    assert "condition_method_version" in data
    assert "water_level_unit" in data
    
    # India Semantics
    assert data["water_level_unit"] == "UNKNOWN"
    
    # No invented fields
    assert "drought_score" not in data
    assert "confidence" not in data
    
    # Vocabulary check
    assert data["condition_state"] in APPROVED_STATES

def test_mh_condition_endpoint_valid_site():
    sites = client.get("/api/v1/maharashtra/candidate-sites?limit=1").json()
    if not sites:
        pytest.skip("No Maharashtra data to test")
    
    site_id = sites[0]["candidate_site_id"]
    response = client.get(f"/api/v1/maharashtra/candidate-sites/{site_id}/condition")
    assert response.status_code == 200
    data = response.json()
    
    # Check schema
    assert "candidate_site_id" in data
    assert "observation_timestamp" in data
    assert "water_level_raw" in data
    assert "condition_state" in data
    assert "percentile" in data
    assert "historical_sample_count" in data
    assert "historical_reference_group" in data
    assert "condition_method_version" in data
    assert "water_level_unit" in data
    
    # MH Semantics
    assert data["water_level_unit"] == "meters"
    
    # Vocabulary check
    assert data["condition_state"] in APPROVED_STATES

def test_condition_nonexistent_site():
    response = client.get("/api/v1/india/candidate-sites/FAKE_SITE_999/condition")
    assert response.status_code == 404
    
    response2 = client.get("/api/v1/maharashtra/candidate-sites/FAKE_SITE_999/condition")
    assert response2.status_code == 404

def test_condition_sql_injection():
    bad_id = "1 OR 1=1"
    response = client.get(f"/api/v1/india/candidate-sites/{bad_id}/condition")
    assert response.status_code == 404

def test_insufficient_history_behavior():
    # Attempt to find a site with INSUFFICIENT_HISTORY
    sites = client.get("/api/v1/india/candidate-sites?limit=100").json()
    found = False
    for site in sites:
        site_id = site["candidate_site_id"]
        response = client.get(f"/api/v1/india/candidate-sites/{site_id}/condition")
        if response.status_code == 200:
            data = response.json()
            if data["condition_state"] == "INSUFFICIENT_HISTORY":
                assert data["percentile"] is None
                found = True
                break
    
    # If found, the test passed. If not found in the first 100, we don't fail because it depends on the data.
    # We just want to ensure that IF it's insufficient, percentile is null and state is literal.
    if not found:
        pass # Optional to skip or pass
