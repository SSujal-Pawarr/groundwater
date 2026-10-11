import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "dal_healthy" in data

def test_india_candidate_sites():
    response = client.get("/api/v1/india/candidate-sites?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5
    if len(data) > 0:
        assert "candidate_site_id" in data[0]

def test_india_telemetry():
    # Fetch a candidate site first
    sites = client.get("/api/v1/india/candidate-sites?limit=1").json()
    if not sites:
        pytest.skip("No India data to test")
    
    site_id = sites[0]["candidate_site_id"]
    response = client.get(f"/api/v1/india/candidate-sites/{site_id}/telemetry?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 5
    if len(data) > 0:
        assert "water_level_raw" in data[0]

def test_india_alerts():
    sites = client.get("/api/v1/india/candidate-sites?limit=1").json()
    if not sites:
        pytest.skip("No India data to test")
        
    site_id = sites[0]["candidate_site_id"]
    response = client.get(f"/api/v1/india/candidate-sites/{site_id}/alerts?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data) <= 5
    if len(data) > 0:
        assert "alert_event_state" in data[0]
        assert "instantaneous_state" in data[0]

def test_mh_candidate_sites():
    response = client.get("/api/v1/maharashtra/candidate-sites?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5
    if len(data) > 0:
        assert "candidate_site_id" in data[0]
        assert "station_name" in data[0]

def test_invalid_pagination():
    response = client.get("/api/v1/india/candidate-sites?limit=-1")
    assert response.status_code == 422
    
def test_nonexistent_site():
    response = client.get("/api/v1/india/candidate-sites/FAKE_SITE_999/telemetry")
    assert response.status_code == 404

def test_sql_injection():
    # DuckDB parameterized queries should safely handle this
    bad_id = "1 OR 1=1"
    response = client.get(f"/api/v1/india/candidate-sites/{bad_id}/telemetry")
    assert response.status_code == 404
