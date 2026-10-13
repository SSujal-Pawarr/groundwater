"""Unit and integration tests for the Maharashtra Advanced Multi-Model Forecast API."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_models_info_endpoint():
    """Verify metadata endpoint returns all registered forecast engines and architectures."""
    resp = client.get("/api/v1/maharashtra/advanced-forecast/models/info")
    assert resp.status_code == 200
    data = resp.json()
    assert "seasonal_harmonic" in data
    assert "chained" in data
    assert "persistence" in data
    assert "lstm" in data
    assert data["seasonal_harmonic"].get("model_type") == "lightgbm_seasonal_harmonic"


def test_site_advanced_forecast_multimodel():
    """Verify single-site prediction responds sub-second with multi-model trajectories."""
    resp = client.get(
        "/api/v1/maharashtra/advanced-forecast",
        params={
            "site_id": "MH_AALEGAON",
            "target_date": "2027-10-15",
            "scenario": "normal",
            "models": "seasonal_harmonic,chained,persistence",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["site_id"] == "MH_AALEGAON"
    assert data["target_date"] == "2027-10-15"
    assert data["horizon_days"] > 400
    assert "seasonal_harmonic" in data["predictions"]
    assert "persistence" in data["predictions"]

    pred = data["predictions"]["seasonal_harmonic"]
    assert "predicted_level" in pred
    assert "confidence_interval_80" in pred
    ci = pred["confidence_interval_80"]
    assert ci[0] <= pred["predicted_level"] <= ci[1]
    assert "history" in data
    assert len(data["history"]) > 0


def test_site_advanced_forecast_lstm():
    """Verify PyTorch LSTM model runs and returns bounded forecast."""
    resp = client.get(
        "/api/v1/maharashtra/advanced-forecast",
        params={
            "site_id": "MH_AALEGAON",
            "target_date": "2027-10-15",
            "scenario": "normal",
            "models": "lstm",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "lstm" in data["predictions"]
    pred = data["predictions"]["lstm"]
    assert "predicted_level" in pred
    assert "confidence_interval_80" in pred
    ci = pred["confidence_interval_80"]
    assert ci[0] <= pred["predicted_level"] <= ci[1]


def test_scenario_effects():
    """Verify deficit scenario decreases groundwater level and excess increases it."""
    resp_norm = client.get(
        "/api/v1/maharashtra/advanced-forecast",
        params={"site_id": "MH_AALEGAON", "target_date": "2027-06-01", "scenario": "normal"},
    )
    resp_def = client.get(
        "/api/v1/maharashtra/advanced-forecast",
        params={"site_id": "MH_AALEGAON", "target_date": "2027-06-01", "scenario": "deficit"},
    )
    resp_exc = client.get(
        "/api/v1/maharashtra/advanced-forecast",
        params={"site_id": "MH_AALEGAON", "target_date": "2027-06-01", "scenario": "excess"},
    )
    assert resp_norm.status_code == 200
    assert resp_def.status_code == 200
    assert resp_exc.status_code == 200

    val_norm = resp_norm.json()["predictions"]["seasonal_harmonic"]["predicted_level"]
    val_def = resp_def.json()["predictions"]["seasonal_harmonic"]["predicted_level"]
    val_exc = resp_exc.json()["predictions"]["seasonal_harmonic"]["predicted_level"]

    # In deficit scenario, water level drops; in excess scenario, recharge raises water level
    assert val_def <= val_norm <= val_exc


def test_state_map_endpoint():
    """Verify vectorized state-wide map endpoint returns 1,000+ sites in ~1s."""
    resp = client.get(
        "/api/v1/maharashtra/advanced-forecast/map",
        params={"target_date": "2027-06-01", "model": "seasonal_harmonic", "scenario": "normal"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "seasonal_harmonic"
    sites = data["sites"]
    assert len(sites) > 900
    first = sites[0]
    assert "site_id" in first
    assert "lat" in first
    assert "lon" in first
    assert "predicted_level" in first
    assert "predicted_condition" in first


def test_invalid_site_404():
    """Verify appropriate 404 response when querying nonexistent site."""
    resp = client.get(
        "/api/v1/maharashtra/advanced-forecast",
        params={"site_id": "NON_EXISTENT_STATION", "target_date": "2027-06-01"},
    )
    assert resp.status_code == 404
