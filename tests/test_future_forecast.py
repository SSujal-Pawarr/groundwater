"""Tests for the multi-horizon future forecast package (src/forecasting) and its API routes."""
import json
import numpy as np
import pandas as pd
import pytest

from src.features.conditions import _assign_condition_state
from src.forecasting.config import DatasetConfig, CONDITION_ORDER
from src.forecasting.features import build_features_mh, build_features_india, reference_percentile, MH_FEATURES
from src.forecasting.pairs import build_pairs, assign_split, state_from_percentile
from src.forecasting.selection import select_best_horizon


# ----------------------------------------------------------------------------- helpers
def _mh_obs(n_sites=12, n_days=150, seed=0):
    rng = np.random.default_rng(seed)
    days = pd.date_range("2026-01-01", periods=n_days, freq="D")
    rows = []
    for s in range(n_sites):
        base = rng.uniform(-20, -5)
        trend = rng.uniform(-0.05, 0.01)
        for i, d in enumerate(days):
            rows.append(dict(candidate_site_id=f"S{s:02d}", date=d, value=base + trend * i + rng.normal(0, 0.2),
                             lat=18 + s * 0.01, lon=75 + s * 0.01, elevation=500.0,
                             state="Maharashtra", district="D1" if s % 2 else "D2", unit="meters", group="ALL"))
    return pd.DataFrame(rows)


def _india_obs(n_sites=6, years=range(2000, 2012), seed=1):
    rng = np.random.default_rng(seed)
    seasons = {1: "RABI_WINTER", 5: "PRE_MONSOON", 8: "MONSOON", 11: "POST_MONSOON"}
    rows = []
    for s in range(n_sites):
        base = rng.uniform(3, 10)
        for y in years:
            for m, g in seasons.items():
                seas = {1: 0.3, 5: 1.0, 8: -1.0, 11: -0.4}[m]
                rows.append(dict(candidate_site_id=f"I{s}", date=pd.Timestamp(year=y, month=m, day=15),
                                 value=base + seas + 0.05 * (y - 2000) + rng.normal(0, 0.1), lat=20.0, lon=77.0,
                                 state="X", district="D", unit="unknown", group=g))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- state mapping
@pytest.mark.parametrize("p", [0, 5, 9.99, 10, 24.9, 25, 50, 75, 75.1, 90, 90.1, 100])
def test_state_mapping_matches_condition_engine(p):
    assert state_from_percentile(np.array([p]))[0] == _assign_condition_state(p)


def test_state_mapping_nan_is_insufficient():
    assert state_from_percentile(np.array([np.nan]))[0] == "INSUFFICIENT_HISTORY"


# ----------------------------------------------------------------------------- percentile
def test_reference_percentile_uses_only_history_up_to_origin():
    obs = pd.DataFrame({"candidate_site_id": ["A"] * 6,
                        "date": pd.date_range("2020-01-01", periods=6, freq="D"),
                        "value": [1.0, 2.0, 3.0, 4.0, 5.0, 1000.0], "group": "ALL"})
    # query on day 5 (index 4): history = [1..5]; the huge day-6 value must be invisible
    p = reference_percentile(obs, ["A"], [obs.date.iloc[4]], ["ALL"], [3.0], min_ref=3)
    assert p[0] == pytest.approx((2 + 0.5 * 1) / 5 * 100)
    # too little history -> NaN
    p2 = reference_percentile(obs, ["A"], [obs.date.iloc[1]], ["ALL"], [3.0], min_ref=5)
    assert np.isnan(p2[0])


def test_reference_percentile_respects_group():
    obs = pd.DataFrame({"candidate_site_id": ["A"] * 4, "date": pd.date_range("2020-01-01", periods=4, freq="D"),
                        "value": [1.0, 2.0, 10.0, 20.0], "group": ["X", "X", "Y", "Y"]})
    p = reference_percentile(obs, ["A"], [obs.date.iloc[3]], ["X"], [1.5], min_ref=2)
    assert p[0] == pytest.approx(50.0)


# ----------------------------------------------------------------------------- features: no leakage
def test_mh_features_do_not_use_future_values():
    obs = _mh_obs(n_sites=4, n_days=60)
    f1 = build_features_mh(obs)
    obs2 = obs.copy()
    cutoff = pd.Timestamp("2026-02-15")
    obs2.loc[obs2.date > cutoff, "value"] += 999.0     # corrupt the FUTURE
    f2 = build_features_mh(obs2)
    a = f1[f1.date <= cutoff].reset_index(drop=True)
    b = f2[f2.date <= cutoff].reset_index(drop=True)
    pd.testing.assert_frame_equal(a[MH_FEATURES], b[MH_FEATURES])


def test_india_features_do_not_use_future_values():
    obs = _india_obs()
    f1 = build_features_india(obs).sort_values(["candidate_site_id", "date"]).reset_index(drop=True)
    cutoff = pd.Timestamp("2008-12-31")
    obs2 = obs.copy()
    obs2.loc[obs2.date > cutoff, "value"] += 50.0
    f2 = build_features_india(obs2).sort_values(["candidate_site_id", "date"]).reset_index(drop=True)
    cols = [c for c in f1.columns if c not in ("candidate_site_id", "date", "group_origin", "district_chg_ly")]
    a, b = f1[f1.date <= cutoff], f2[f2.date <= cutoff]
    pd.testing.assert_frame_equal(a[cols].reset_index(drop=True), b[cols].reset_index(drop=True))


# ----------------------------------------------------------------------------- pairs & split
def test_pairs_target_is_h_months_ahead_within_tolerance():
    obs = _mh_obs(n_sites=3, n_days=150)
    f = build_features_mh(obs)
    p = build_pairs(f, obs, 1, 1)
    gap = (p.target_date - p.date).dt.days
    assert gap.between(28, 32).all()
    # target value really is the observed value at target_date
    chk = p.merge(obs[["candidate_site_id", "date", "value"]], left_on=["candidate_site_id", "target_date"],
                  right_on=["candidate_site_id", "date"], suffixes=("", "_t"))
    assert np.allclose(chk.target_value, chk.value)


def test_pairs_infeasible_horizon_is_empty():
    obs = _mh_obs(n_sites=3, n_days=150)
    f = build_features_mh(obs)
    assert len(build_pairs(f, obs, 6, 15)) == 0
    assert len(build_pairs(f, obs, 12, 15)) == 0


def test_india_one_month_has_no_pairs_but_six_and_twelve_do():
    obs = _india_obs()
    f = build_features_india(obs)
    assert len(build_pairs(f, obs, 1, 7)) == 0
    assert len(build_pairs(f, obs, 6, 45)) > 0
    assert len(build_pairs(f, obs, 12, 45)) > 0


def _cfg(**kw):
    base = dict(region="maharashtra", source_files=[], time_col="observation_timestamp", unit_default="meters",
                tolerance_days={1: 1}, test_start="2026-04-01", val_start=None, min_train_pairs=10, min_test_pairs=10,
                min_reference_obs=5, max_origin_age_days=7, max_train_rows=None, n_oof_folds=3)
    base.update(kw)
    return DatasetConfig(**base)


def test_split_is_chronological_and_purged():
    obs = _mh_obs(n_sites=3, n_days=150)
    p = build_pairs(build_features_mh(obs), obs, 1, 1)
    p["split"] = assign_split(p, _cfg()).values
    tr, te = p[p.split == "train"], p[p.split == "test"]
    assert len(tr) and len(te)
    assert tr.target_date.max() < te.date.min()          # no label of train is at/after any test origin
    purged = p[p.split == "purged"]
    assert ((purged.date < pd.Timestamp("2026-04-01")) & (purged.target_date >= pd.Timestamp("2026-04-01"))).all()


# ----------------------------------------------------------------------------- horizon selection
def _res(r2, feasible=True):
    return {"feasible": feasible, "test": {"xgboost_regressor": {"r2": r2, "rmse": 1 - r2, "mae": 1 - r2, "r2_change": r2}}}


def test_selection_prefers_one_month_when_more_accurate():
    s = select_best_horizon({1: _res(0.95), 6: _res(0.90), 12: _res(0.85)})
    assert s["selected_horizon_months"] == 1


def test_selection_prefers_six_months_when_one_month_less_accurate():
    s = select_best_horizon({1: _res(0.80), 6: _res(0.90), 12: _res(0.85)})
    assert s["selected_horizon_months"] == 6


def test_selection_ignores_infeasible_and_handles_none():
    assert select_best_horizon({1: _res(0.5), 6: _res(0.99, feasible=False)})["selected_horizon_months"] == 1
    assert select_best_horizon({1: _res(0.5, feasible=False)})["selected_horizon_months"] is None


def test_selection_tie_goes_to_shorter_horizon():
    assert select_best_horizon({6: _res(0.9), 1: _res(0.9)})["selected_horizon_months"] == 1


def test_selection_error_metrics_lower_is_better():
    r = {1: _res(0.9), 6: _res(0.8)}
    assert select_best_horizon(r, metric="rmse")["selected_horizon_months"] == 1


# ----------------------------------------------------------------------------- end-to-end (small)
def test_stage1_and_stage2_end_to_end_small():
    from src.forecasting.pipeline import evaluate_horizon, run_classification, reg_params_for
    from src.forecasting.config import XGBClsParams, XGBRegParams
    obs = _mh_obs(n_sites=40, n_days=150, seed=3)
    cfg = _cfg(min_train_pairs=100, min_test_pairs=100)
    feats = build_features_mh(obs)
    rp = XGBRegParams(n_estimators=40, max_depth=3)
    res, pairs = evaluate_horizon(cfg, feats, obs, 1, MH_FEATURES, rp)
    assert res["feasible"] and res["test"]["xgboost_regressor"]["n"] > 100
    assert {"mae", "rmse", "r2"} <= set(res["test"]["xgboost_regressor"])
    assert "baseline_persistence" in res["test"]
    cm, labelled, rounds = run_classification(cfg, pairs, obs, MH_FEATURES, res["n_rounds"], rp,
                                               XGBClsParams(n_estimators=30, max_depth=3))
    assert 0.0 <= cm["xgboost_classifier"]["accuracy"] <= 1.0
    assert {"baseline_persistence_state", "baseline_rule_on_regressor_output", "baseline_majority_class"} <= set(cm)


# ----------------------------------------------------------------------------- API
@pytest.fixture
def api_client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from src.api.main import app
    from src.api.routes import future_forecast as ff
    ff._cache.clear()
    monkeypatch.setattr(ff, "OUT_DIR", tmp_path)
    row = {"candidate_site_id": "MH_X", "region": "maharashtra", "origin_date": "2026-05-30", "origin_water_level": -10.0,
           "horizon_months": 1, "target_date": "2026-06-30", "predicted_water_level": -10.5, "predicted_change": -0.5,
           "predicted_lower_80": -12.0, "predicted_upper_80": -9.0, "predicted_percentile_vs_history": 80.0,
           "current_condition_state": "HIGH", "predicted_condition_state": "EXTREMELY_HIGH",
           "predicted_state_confidence": 0.6, "state": "Maharashtra", "district": "Pune", "lat": 18.5, "lon": 73.8,
           "water_level_unit": "meters", "model_version": "t", "data_through": "2026-05-30"}
    for i, c in enumerate(CONDITION_ORDER):
        row[f"prob_{c}"] = 0.1 if c != "EXTREMELY_HIGH" else 0.6
    row2 = dict(row, candidate_site_id="MH_Y", district="Nashik", predicted_condition_state="LOW", predicted_percentile_vs_history=np.nan)
    pd.DataFrame([row, row2]).to_parquet(tmp_path / "maharashtra_future_forecast.parquet", index=False)
    chained_row = {
        "candidate_site_id": "MH_CHAIN",
        "region": "maharashtra",
        "estimate_label": "ESTIMATED_WITHOUT_RECENT_DATA",
        "origin_date": "2026-05-30",
        "origin_water_level": -10.0,
        "requested_target_date": "2026-11-10",
        "predicted_for_date": "2026-11-30",
        "n_steps": 6,
        "step_months": 1,
        "months_to_target": 5.4,
        "backtested_steps": 2,
        "data_gap_days": 184,
        "method": "persistence_fallback",
        "method_reason": "chained model did not beat persistence",
        "predicted_water_level": -10.0,
        "predicted_change": 0.0,
        "predicted_lower_80": -14.0,
        "predicted_upper_80": -5.0,
        "interval_basis": "extrapolated_sqrt_from_2_steps",
        "predicted_percentile_vs_history": np.nan,
        "current_condition_state": "HIGH",
        "predicted_condition_state": "INSUFFICIENT_HISTORY",
        "predicted_state_confidence": np.nan,
        "warnings": "monsoon data unavailable; interval extrapolated",
        "path_levels": json.dumps([{"date": "2026-05-30", "level": -10.0}]),
        "state": "Maharashtra",
        "district": "Akola",
        "lat": 20.4,
        "lon": 76.8,
        "water_level_unit": "meters",
        "model_version": "M17-FutureForecast-v1-chain",
        "data_through": "2026-05-30",
    }
    for condition in CONDITION_ORDER:
        chained_row[f"prob_{condition}"] = np.nan
    pd.DataFrame([chained_row]).to_parquet(tmp_path / "maharashtra_chained_forecast.parquet", index=False)
    (tmp_path / "maharashtra_summary.json").write_text(json.dumps({"selection": {"selected_horizon_months": 1}}))
    yield TestClient(app)
    ff._cache.clear()


def test_api_site_forecast(api_client):
    r = api_client.get("/api/v1/maharashtra/candidate-sites/MH_X/future-forecast")
    assert r.status_code == 200
    d = r.json()
    assert d["predicted_condition_state"] == "EXTREMELY_HIGH"
    assert set(d["predicted_condition_probabilities"]) == set(CONDITION_ORDER)
    assert not any(k.startswith("prob_") for k in d)


def test_api_site_forecast_falls_back_to_chain_when_direct_row_is_missing(api_client):
    response = api_client.get("/api/v1/maharashtra/candidate-sites/MH_CHAIN/future-forecast")

    assert response.status_code == 200
    body = response.json()
    assert body["forecast_source"] == "chained_fallback"
    assert body["target_date"] == "2026-11-30"
    assert body["forecast_method"] == "persistence_fallback"
    assert body["warnings"] == ["monsoon data unavailable", "interval extrapolated"]


def test_api_nan_becomes_null_and_filters_work(api_client):
    d = api_client.get("/api/v1/maharashtra/future-forecast?district=Nashik").json()
    assert len(d) == 1 and d[0]["predicted_percentile_vs_history"] is None
    assert len(api_client.get("/api/v1/maharashtra/future-forecast").json()) == 2


def test_api_unknown_site_and_missing_region_artifact(api_client):
    assert api_client.get("/api/v1/maharashtra/candidate-sites/NOPE/future-forecast").status_code == 404
    assert api_client.get("/api/v1/india/candidate-sites/IND_X/future-forecast").status_code == 404
    assert api_client.get("/api/v1/mars/future-forecast").status_code == 422


def test_api_summary(api_client):
    assert api_client.get("/api/v1/maharashtra/future-forecast/summary").json()["selection"]["selected_horizon_months"] == 1


def test_sql_like_site_id_is_inert(api_client):
    assert api_client.get("/api/v1/maharashtra/candidate-sites/x'%20OR%20'1'='1/future-forecast").status_code == 404


def test_existing_routes_still_registered(api_client):
    paths = set(api_client.get("/openapi.json").json()["paths"])
    for p in ["/health", "/api/v1/india/candidate-sites", "/api/v1/maharashtra/candidate-sites",
              "/api/v1/{region}/candidate-sites/{candidate_site_id}/analytics",
              "/api/v1/{region}/future-forecast", "/api/v1/{region}/future-forecast/summary",
              "/api/v1/{region}/candidate-sites/{candidate_site_id}/future-forecast"]:
        assert p in paths, p


def test_unclassifiable_rows_become_insufficient_history():
    from src.forecasting.pipeline import mask_unclassifiable
    out = pd.DataFrame({"predicted_percentile_vs_history": [np.nan, 40.0],
                        "predicted_condition_state": ["EXTREMELY_HIGH", "NORMAL_RANGE"],
                        "predicted_state_confidence": [0.9, 0.7]})
    for c in CONDITION_ORDER:
        out[f"prob_{c}"] = 0.2
    r = mask_unclassifiable(out)
    assert r.loc[0, "predicted_condition_state"] == "INSUFFICIENT_HISTORY"
    assert np.isnan(r.loc[0, "predicted_state_confidence"]) and np.isnan(r.loc[0, "prob_LOW"])
    assert r.loc[1, "predicted_condition_state"] == "NORMAL_RANGE" and r.loc[1, "prob_LOW"] == 0.2
