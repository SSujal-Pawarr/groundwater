from datetime import date, timedelta
import json

import joblib
import pandas as pd
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes import forecasts


class ConstantLevelModel:
    def predict(self, features):
        return [12.5] * len(features)


client = TestClient(app)


@pytest.fixture
def configured_forecast_artifacts(tmp_path, monkeypatch):
    start = date(2026, 1, 1)
    rows = []
    for site_id, station, district, base in [
        ("MH_TEST_A", "TEST STATION A", "Nashik", 10.0),
        ("MH_TEST_B", "TEST STATION B", "Pune", 14.0),
    ]:
        for offset in range(45):
            observation_day = start + timedelta(days=offset)
            rows.append({
                "candidate_site_id": site_id,
                "station_name": station,
                "state": "Maharashtra",
                "district": district,
                "latitude": 19.0,
                "longitude": 74.0,
                "elevation_msl": 500.0,
                "observation_timestamp": f"{observation_day.isoformat()}T06:00:00",
                "water_level_raw": base + offset * 0.01,
                "is_analytics_ready": True,
            })

    data_path = tmp_path / "maharashtra_normalized.parquet"
    pd.DataFrame(rows).to_parquet(data_path, index=False)

    target_date = date(2026, 2, 19)
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    model_path = model_dir / "maharashtra_level_h5.joblib"
    joblib.dump({
        "model": ConstantLevelModel(),
        "feature_columns": forecasts.FEATURE_COLUMNS,
        "target_date": target_date.isoformat(),
        "data_through": "2026-02-14",
        "horizon_days": 5,
        "metrics": {"model_metrics": {"mae": 1.0}, "persistence_metrics": {"mae": 2.0}},
    }, model_path)

    monkeypatch.setattr(forecasts, "MODEL_DIR", model_dir)
    monkeypatch.setattr(forecasts, "DATA_PATH", data_path)
    monkeypatch.setattr(forecasts, "_model_cache", None)
    monkeypatch.setattr(forecasts, "_daily_cache", None)
    daily = forecasts.aggregate_daily(forecasts.load_observations(data_path))
    chain_rows = []
    for site_id, station, district, base in [
        ("MH_TEST_A", "TEST STATION A", "Nashik", 10.0),
        ("MH_TEST_B", "TEST STATION B", "Pune", 14.0),
    ]:
        chain_rows.append({
            "candidate_site_id": site_id,
            "station_name": station,
            "state": "Maharashtra",
            "district": district,
            "lat": 19.0,
            "lon": 74.0,
            "water_level_unit": "meters",
            "origin_date": "2026-02-14",
            "origin_water_level": base + 0.44,
            "requested_target_date": target_date.isoformat(),
            "predicted_for_date": target_date.isoformat(),
            "predicted_water_level": 12.5,
            "predicted_change": 2.06,
            "predicted_lower_80": 8.0,
            "predicted_upper_80": 16.0,
            "interval_basis": "backtest_measured",
            "method": "chained_xgboost",
            "method_reason": "backtest skill over persistence",
            "n_steps": 1,
            "step_months": 1,
            "backtested_steps": 2,
            "data_gap_days": 5,
            "predicted_condition_state": "NORMAL_RANGE",
            "predicted_state_confidence": 0.7,
            "trained_regression_water_level": None,
            "direct_m17_water_level": None,
            "warnings": "",
            "path_levels": json.dumps([
                {"date": "2026-02-14", "level": base + 0.44},
                {"date": target_date.isoformat(), "level": 12.5},
            ]),
            "prob_EXTREMELY_LOW": 0.1,
            "prob_LOW": 0.1,
            "prob_NORMAL_RANGE": 0.7,
            "prob_HIGH": 0.05,
            "prob_EXTREMELY_HIGH": 0.05,
        })

    def fake_chain(requested_date):
        if requested_date > target_date + timedelta(days=2):
            raise HTTPException(status_code=422, detail="No sites are eligible beyond the supported target range.")
        frame = pd.DataFrame(chain_rows).copy()
        frame["requested_target_date"] = requested_date.isoformat()
        frame["predicted_for_date"] = requested_date.isoformat()
        frame["path_levels"] = frame["path_levels"].apply(lambda value: json.dumps([
            {"date": "2026-02-14", "level": 10.44},
            {"date": requested_date.isoformat(), "level": 12.5},
        ]))
        return frame, daily, {"chain_backtest": {"by_steps": {"1": {"evaluable": True}}}}

    monkeypatch.setattr(forecasts, "_run_chained_forecast", fake_chain)
    monkeypatch.setattr(forecasts, "_load_chain_context", lambda: {
        "step_months": 1,
        "observations": pd.DataFrame({"date": pd.to_datetime(["2026-02-14"])}),
    })
    monkeypatch.setattr(forecasts, "_load_direct_m17", lambda _requested: {})
    return target_date


def test_regression_forecast_lists_sites_and_rejects_unsupported_risk(configured_forecast_artifacts):
    response = client.get("/api/forecast/maharashtra")

    assert response.status_code == 200
    body = response.json()
    assert body["target_date"] == configured_forecast_artifacts.isoformat()
    assert len(body["locations"]) == 2
    assert body["locations"][0]["predicted_water_level"] == 12.5
    assert body["selected_location"] is None
    assert body["models"]["chained_m17"]["available"] is True
    assert body["models"]["trained_gradient_boosting"]["available"] is True
    assert "no observed flood ground-truth labels" in body["unsupported_targets"]["flood_probability"]


def test_regression_forecast_includes_selected_site_history(configured_forecast_artifacts):
    response = client.get(
        "/api/forecast/maharashtra",
        params={"candidate_site_id": "MH_TEST_A"},
    )

    assert response.status_code == 200
    selected = response.json()["selected_location"]
    assert selected["candidate_site_id"] == "MH_TEST_A"
    assert selected["station_name"] == "TEST STATION A"
    assert selected["target_date"] == configured_forecast_artifacts.isoformat()
    assert selected["predicted_water_level"] == 12.5
    assert len(selected["history"]) == 45


def test_regression_forecast_accepts_other_supported_target_date(configured_forecast_artifacts):
    response = client.get(
        "/api/forecast/maharashtra",
        params={"target_date": "2026-02-20"},
    )

    assert response.status_code == 200
    assert response.json()["target_date"] == "2026-02-20"
    assert response.json()["locations"][0]["requested_target_date"] == "2026-02-20"


def test_regression_forecast_rejects_date_beyond_chain_limit(configured_forecast_artifacts):
    response = client.get(
        "/api/forecast/maharashtra",
        params={"target_date": "2026-03-01"},
    )

    assert response.status_code == 422
    assert "supported target range" in response.json()["detail"]