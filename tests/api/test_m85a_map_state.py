import pytest
from fastapi.testclient import TestClient
import duckdb
from pathlib import Path
from unittest.mock import patch

from src.api.main import app
from src.api.dal import GroundwaterDAL

client = TestClient(app)

class TestM85AMapState:
    @classmethod
    def setup_class(cls):
        cls.dal = GroundwaterDAL()

    def test_1_india_candidate_sites_contains_condition_state(self):
        """1. India candidate-sites response contains condition_state."""
        res = client.get("/api/v1/india/candidate-sites?limit=10")
        assert res.status_code == 200
        data = res.json()
        assert len(data) > 0
        valid_states = {
            "EXTREMELY_LOW", "LOW", "NORMAL_RANGE", "HIGH", "EXTREMELY_HIGH", "INSUFFICIENT_HISTORY", None
        }
        for item in data:
            assert "condition_state" in item, "Missing condition_state in India candidate site"
            assert item["condition_state"] in valid_states, f"Invalid condition_state: {item['condition_state']}"

    def test_2_india_condition_state_from_persisted_artifact(self):
        """2. India condition_state comes from the persisted condition artifact."""
        res = client.get("/api/v1/india/candidate-sites?limit=5")
        assert res.status_code == 200
        data = res.json()
        
        # Verify against direct DuckDB query on the persisted parquet
        conn = duckdb.connect()
        cond_path = self.dal.india_m82d_path.as_posix()
        for site in data:
            site_id = site["candidate_site_id"]
            expected = conn.execute(f"""
                SELECT condition_state
                FROM '{cond_path}'
                WHERE candidate_site_id = ?
                ORDER BY observation_date DESC
                LIMIT 1
            """, [site_id]).fetchone()
            expected_state = expected[0] if expected else None
            assert site["condition_state"] == expected_state, f"Mismatch for site {site_id}: {site['condition_state']} vs {expected_state}"

    def test_3_maharashtra_candidate_sites_contains_alert_event_state(self):
        """3. Maharashtra candidate-sites response contains alert_event_state."""
        res = client.get("/api/v1/maharashtra/candidate-sites?limit=10")
        assert res.status_code == 200
        data = res.json()
        assert len(data) > 0
        valid_alert_states = {
            "NORMAL", "WATCH", "WARNING", "CRITICAL_STATISTICAL_DEVIATION", 
            "DATA_QUALITY_EVENT", "INSUFFICIENT_HISTORY", "SEQUENCE_GAPPED", None
        }
        for item in data:
            assert "alert_event_state" in item, "Missing alert_event_state in MH candidate site"
            assert item["alert_event_state"] in valid_alert_states, f"Invalid alert_event_state: {item['alert_event_state']}"

    def test_4_maharashtra_alert_event_state_from_persisted_artifact(self):
        """4. Maharashtra alert_event_state comes from the persisted M6 artifact."""
        res = client.get("/api/v1/maharashtra/candidate-sites?limit=5")
        assert res.status_code == 200
        data = res.json()
        
        conn = duckdb.connect()
        alert_path = self.dal.mh_m6_path.as_posix()
        for site in data:
            site_id = site["candidate_site_id"]
            expected = conn.execute(f"""
                SELECT alert_event_state
                FROM '{alert_path}'
                WHERE candidate_site_id = ?
                ORDER BY observation_timestamp DESC
                LIMIT 1
            """, [site_id]).fetchone()
            expected_state = expected[0] if expected else None
            assert site["alert_event_state"] == expected_state, f"Mismatch for site {site_id}: {site['alert_event_state']} vs {expected_state}"

    def test_5_no_scientific_recalculation_performed(self):
        """5. No scientific recalculation is performed in the API."""
        # Ensure no condition or alert engine computations occur during candidate-sites retrieval
        with patch("src.features.conditions.compute_india_conditions", side_effect=RuntimeError("Must not recalculate India conditions!")):
            with patch("src.features.conditions.compute_maharashtra_conditions", side_effect=RuntimeError("Must not recalculate MH conditions!")):
                with patch("src.alerting.engine.generate_maharashtra_alerts", side_effect=RuntimeError("Must not recalculate MH alerts!")):
                    with patch("src.alerting.engine.generate_india_alerts", side_effect=RuntimeError("Must not recalculate India alerts!")):
                        res_in = client.get("/api/v1/india/candidate-sites?limit=5")
                        assert res_in.status_code == 200
                        res_mh = client.get("/api/v1/maharashtra/candidate-sites?limit=5")
                        assert res_mh.status_code == 200

    def test_6_existing_candidate_site_fields_intact(self):
        """6. Existing candidate-site fields remain intact."""
        res_in = client.get("/api/v1/india/candidate-sites?limit=1").json()
        assert len(res_in) == 1
        expected_in_fields = {"candidate_site_id", "state", "district", "block", "village", "latitude", "longitude", "condition_state"}
        for f in expected_in_fields:
            assert f in res_in[0], f"Missing expected India field: {f}"

        res_mh = client.get("/api/v1/maharashtra/candidate-sites?limit=1").json()
        assert len(res_mh) == 1
        expected_mh_fields = {"candidate_site_id", "station_name", "state", "district", "subdistrict", "latitude", "longitude", "elevation_msl", "alert_event_state"}
        for f in expected_mh_fields:
            assert f in res_mh[0], f"Missing expected MH field: {f}"

    def test_7_existing_condition_endpoint_functional(self):
        """7. Existing condition endpoint remains functional."""
        site_in = client.get("/api/v1/india/candidate-sites?limit=1").json()[0]["candidate_site_id"]
        res_in = client.get(f"/api/v1/india/candidate-sites/{site_in}/condition")
        assert res_in.status_code == 200
        assert "condition_state" in res_in.json()
        assert res_in.json()["water_level_unit"] == "UNKNOWN"

        site_mh = client.get("/api/v1/maharashtra/candidate-sites?limit=1").json()[0]["candidate_site_id"]
        res_mh = client.get(f"/api/v1/maharashtra/candidate-sites/{site_mh}/condition")
        assert res_mh.status_code == 200
        assert "condition_state" in res_mh.json()
        assert res_mh.json()["water_level_unit"] == "meters"

    def test_8_existing_alert_endpoint_functional(self):
        """8. Existing alert endpoint remains functional."""
        site_in = client.get("/api/v1/india/candidate-sites?limit=1").json()[0]["candidate_site_id"]
        res_in = client.get(f"/api/v1/india/candidate-sites/{site_in}/alerts?limit=5")
        assert res_in.status_code == 200
        assert isinstance(res_in.json(), list)

        site_mh = client.get("/api/v1/maharashtra/candidate-sites?limit=1").json()[0]["candidate_site_id"]
        res_mh = client.get(f"/api/v1/maharashtra/candidate-sites/{site_mh}/alerts?limit=5")
        assert res_mh.status_code == 200
        assert isinstance(res_mh.json(), list)

    def test_9_existing_forecast_endpoint_functional(self):
        """9. Existing forecast endpoint remains functional."""
        site_mh = client.get("/api/v1/maharashtra/candidate-sites?limit=1").json()[0]["candidate_site_id"]
        res = client.get(f"/api/v1/maharashtra/candidate-sites/{site_mh}/forecast")
        assert res.status_code == 200
        data = res.json()
        assert data["forecast_type"] == "NEXT_VALID_OBSERVATION"
        assert data["forecast_method"] == "PERSISTENCE"
        assert data["latest_water_level"] == data["predicted_next_water_level"]

    def test_10_bbox_filtering_works(self):
        """10. Bbox filtering still works."""
        min_lat, max_lat = 18.0, 22.0
        min_lng, max_lng = 74.0, 78.0
        res = client.get(f"/api/v1/india/candidate-sites?min_lat={min_lat}&max_lat={max_lat}&min_lng={min_lng}&max_lng={max_lng}&limit=10")
        assert res.status_code == 200
        data = res.json()
        assert len(data) > 0
        for s in data:
            assert min_lat <= s["latitude"] <= max_lat
            assert min_lng <= s["longitude"] <= max_lng
            assert "condition_state" in s

    def test_11_pagination_limit_works(self):
        """11. Pagination/limit still works."""
        page1 = client.get("/api/v1/india/candidate-sites?limit=3&offset=0").json()
        page2 = client.get("/api/v1/india/candidate-sites?limit=3&offset=3").json()
        assert len(page1) == 3
        assert len(page2) == 3
        p1_ids = [s["candidate_site_id"] for s in page1]
        p2_ids = [s["candidate_site_id"] for s in page2]
        assert set(p1_ids).isdisjoint(set(p2_ids))

    def test_12_no_n_plus_one_behavior(self):
        """12. No N+1 API behavior exists (1 single query executed by DAL)."""
        dal = GroundwaterDAL()
        with patch.object(dal, '_query', wraps=dal._query) as mock_query:
            dal.get_india_candidate_sites(limit=50)
            assert mock_query.call_count == 1, f"Expected exactly 1 DAL query, got {mock_query.call_count}"

        with patch.object(dal, '_query', wraps=dal._query) as mock_query_mh:
            dal.get_mh_candidate_sites(limit=50)
            assert mock_query_mh.call_count == 1, f"Expected exactly 1 DAL query, got {mock_query_mh.call_count}"

    def test_13_missing_state_handled_safely(self):
        """13. Missing state is handled safely if artifact does not exist."""
        dal = GroundwaterDAL()
        # Mock non-existent artifact path
        with patch.object(dal, 'india_m82d_path', Path("/tmp/nonexistent_conditions.parquet")):
            sites = dal.get_india_candidate_sites(limit=5)
            assert len(sites) == 5
            for s in sites:
                assert s["condition_state"] is None

        with patch.object(dal, 'mh_m6_path', Path("/tmp/nonexistent_alerts.parquet")):
            sites_mh = dal.get_mh_candidate_sites(limit=5)
            assert len(sites_mh) == 5
            for s in sites_mh:
                assert s["alert_event_state"] is None

    def test_14_india_does_not_expose_maharashtra_alert_semantics(self):
        """14. India does not expose Maharashtra alert semantics."""
        res = client.get("/api/v1/india/candidate-sites?limit=5").json()
        for site in res:
            # We now expose alert_event_state for India via M16/M17 Analytics Integration, 
            # but we still don't expose instantaneous_state, deviation, etc. directly here.
            assert "instantaneous_state" not in site
            assert "deviation" not in site
            assert "standardized_score" not in site

    def test_15_maharashtra_does_not_expose_india_condition_semantics(self):
        """15. Maharashtra does not expose India condition semantics, nor combined risk fields."""
        res = client.get("/api/v1/maharashtra/candidate-sites?limit=5").json()
        forbidden_fields = {
            "percentile", "risk", "severity", "risk_score", 
            "status", "groundwater_risk", "flood_state"
        }
        for site in res:
            for forbidden in forbidden_fields:
                assert forbidden not in site, f"Forbidden field '{forbidden}' found in MH site response"

        # Also verify forbidden fields on India
        res_in = client.get("/api/v1/india/candidate-sites?limit=5").json()
        forbidden_in = {"risk", "severity", "risk_score", "status", "groundwater_risk", "flood_state"}
        for site in res_in:
            for forbidden in forbidden_in:
                assert forbidden not in site, f"Forbidden field '{forbidden}' found in India site response"
