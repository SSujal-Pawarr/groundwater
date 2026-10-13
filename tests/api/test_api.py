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
    if response.status_code == 503:
        assert "Dataset unavailable" in response.json()["detail"]
        return
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5
    if len(data) > 0:
        assert "candidate_site_id" in data[0]

def test_india_telemetry():
    # Fetch a candidate site first
    sites_response = client.get("/api/v1/india/candidate-sites?limit=1")
    if sites_response.status_code == 503:
        pytest.skip("India dataset is not installed")
    sites = sites_response.json()
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
    sites_response = client.get("/api/v1/india/candidate-sites?limit=1")
    if sites_response.status_code == 503:
        pytest.skip("India dataset is not installed")
    sites = sites_response.json()
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
    if response.status_code == 503:
        assert "Dataset unavailable" in response.json()["detail"]
        return
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5
    if len(data) > 0:
        assert "candidate_site_id" in data[0]
        assert "station_name" in data[0]

def test_candidate_sites_reports_missing_dataset(monkeypatch):
    from src.api.routes import candidate_sites

    missing_path = candidate_sites.dal.project_root / "data" / "processed" / "test_missing" / "india_normalized.parquet"
    monkeypatch.setattr(candidate_sites.dal, "india_m3_path", missing_path)

    response = client.get("/api/v1/india/candidate-sites")

    assert response.status_code == 503
    assert "india_normalized.parquet" in response.json()["detail"]
    assert "rebuild_processed_from_alerts.py" in response.json()["detail"]

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
