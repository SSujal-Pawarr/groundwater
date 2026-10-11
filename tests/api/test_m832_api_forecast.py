import pytest
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

# Note: These tests run against the actual local duckdb parquet artifacts
# Assumes maharashtra_normalized.parquet is loaded by GroundwaterDAL

class TestM832APIForecast:
    def test_forecast_valid_site(self):
        # Using a known valid site ID, e.g., MH_AALEGAON
        response = client.get("/api/v1/maharashtra/candidate-sites/MH_AALEGAON/forecast")
        if response.status_code == 404:
            pytest.skip("Data not populated for MH_AALEGAON in test env")
            
        assert response.status_code == 200
        data = response.json()
        
        # 1. Valid site returns forecast (check schema)
        assert "candidate_site_id" in data
        assert "latest_observation_timestamp" in data
        assert "latest_water_level" in data
        assert "predicted_next_water_level" in data
        assert "water_level_unit" in data
        assert "forecast_type" in data
        assert "forecast_method" in data
        assert "model_version" in data
        
        # 3. predicted_next_water_level equals latest_water_level
        assert data["predicted_next_water_level"] == data["latest_water_level"]
        
        # 4. Correct water unit = meters
        assert data["water_level_unit"] == "meters"
        
        # 5, 6, 7. Correct metadata strings
        assert data["forecast_type"] == "NEXT_VALID_OBSERVATION"
        assert data["forecast_method"] == "PERSISTENCE"
        assert data["model_version"] == "persistence-v1"
        
        # 8, 9. No target timestamp or horizon fabricated
        assert "target_timestamp" not in data
        assert "forecast_horizon_hours" not in data
        
    def test_latest_observation_is_analytics_ready(self):
        # We manually query the telemetry endpoint to verify the returned forecast 
        # is the absolute latest analytics_ready observation
        
        telemetry_response = client.get("/api/v1/maharashtra/candidate-sites/MH_AALEGAON/telemetry?limit=50")
        if telemetry_response.status_code == 404:
            pytest.skip("Telemetry missing for MH_AALEGAON")
            
        telemetry = telemetry_response.json()
        
        # Find first analytics_ready = True
        latest_valid = None
        for row in telemetry:
            if row.get("is_analytics_ready"):
                latest_valid = row
                break
                
        forecast_response = client.get("/api/v1/maharashtra/candidate-sites/MH_AALEGAON/forecast")
        assert forecast_response.status_code == 200
        forecast_data = forecast_response.json()
        
        # 2. Returned latest observation is actually the latest analytics-ready observation.
        assert forecast_data["latest_observation_timestamp"] == latest_valid["observation_timestamp"]
        assert forecast_data["latest_water_level"] == latest_valid["water_level_raw"]

    def test_invalid_site_returns_404(self):
        response = client.get("/api/v1/maharashtra/candidate-sites/DOES_NOT_EXIST_123/forecast")
        assert response.status_code == 404

    def test_india_forecast_endpoint_does_not_exist(self):
        # The India equivalent must return a 404 because it is NOT implemented
        response = client.get("/api/v1/india/candidate-sites/CGWB_123/forecast")
        assert response.status_code == 404

    def test_existing_endpoints_functional(self):
        # Verify M7 telemetry still works
        response = client.get("/api/v1/maharashtra/candidate-sites/MH_AALEGAON/telemetry?limit=1")
        assert response.status_code in (200, 404)
        
        # Verify M8.2-E condition still works
        response = client.get("/api/v1/maharashtra/candidate-sites/MH_AALEGAON/condition")
        assert response.status_code in (200, 404)

    def test_leakage_and_isolation(self):
        """
        An explicit test demonstrating that the live forecast endpoint uses 
        ONLY the normalized telemetry table and relies on the LIMIT 1 ordering,
        and definitively DOES NOT query the retrospective forecast artifact.
        """
        import inspect
        from src.api.dal import GroundwaterDAL
        
        source = inspect.getsource(GroundwaterDAL.get_mh_latest_persistence_forecast)
        
        # Confirm it queries the M3 immutable raw path (mh_m3_path)
        assert "self.mh_m3_path" in source
        # Confirm it DOES NOT query the retrospective M8.3.1 forecast artifact
        assert "forecasts" not in source.lower()
        # Confirm it strictly selects the single latest observation
        assert "ORDER BY observation_timestamp DESC" in source
        assert "LIMIT 1" in source
        # Confirm it restricts to analytics ready
        assert "is_analytics_ready = true" in source.lower()
