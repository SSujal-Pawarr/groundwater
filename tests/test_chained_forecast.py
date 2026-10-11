"""Tests for the chained (rolled-forward) forecast: src/forecasting/chain.py and its API routes."""
import json
import numpy as np
import pandas as pd
import pytest

from src.forecasting import chain
from src.forecasting.config import CONDITION_ORDER


# ----------------------------------------------------------------------------- method decision & intervals
def _bt(skill, q10=-1.0, q90=2.0, pq10=-3.0, pq90=4.0, steps=(1, 2)):
    return {k: {"evaluable": True, "months_ahead": k, "rmse_skill_vs_persistence": skill if np.isscalar(skill) else skill[k],
                "resid_q10": q10 * k, "resid_q90": q90 * k, "pers_resid_q10": pq10 * k, "pers_resid_q90": pq90 * k}
            for k in steps}


def test_method_uses_model_only_when_it_beats_persistence():
    assert chain.method_for_step(_bt(0.10), 1, 1)[0] == "chained_xgboost"
    assert chain.method_for_step(_bt(-0.05), 1, 1)[0] == "persistence_fallback"
    assert chain.method_for_step(_bt(0.0), 2, 1)[0] == "persistence_fallback"          # a tie is not skill


def test_method_beyond_backtested_steps_inherits_last_verdict():
    assert chain.method_for_step(_bt({1: 0.2, 2: -0.1}), 7, 1)[0] == "persistence_fallback"
    assert chain.method_for_step(_bt({1: -0.2, 2: 0.1}), 7, 1)[0] == "chained_xgboost"


def test_method_without_backtest_falls_back():
    assert chain.method_for_step({1: {"evaluable": False, "n": 3}}, 1, 1)[0] == "persistence_fallback"


def test_interval_measured_then_sqrt_extrapolated_and_method_specific():
    bt = _bt(0.1)
    lo, hi, basis = chain.interval_for_step(bt, 2, "chained_xgboost", 1)
    assert (lo, hi, basis) == (-2.0, 4.0, "backtest_measured")
    lo8, hi8, basis8 = chain.interval_for_step(bt, 8, "chained_xgboost", 1)
    assert lo8 == pytest.approx(-2.0 * np.sqrt(8 / 2)) and hi8 == pytest.approx(4.0 * np.sqrt(8 / 2))
    assert basis8.startswith("extrapolated_sqrt")
    plo, phi, _ = chain.interval_for_step(bt, 1, "persistence_fallback", 1)           # persistence uses its own residuals
    assert (plo, phi) == (-3.0, 4.0)


def test_interval_widens_with_steps():
    bt = _bt(0.1)
    w = [chain.interval_for_step(bt, k, "chained_xgboost", 1) for k in (1, 2, 4, 8)]
    widths = [hi - lo for lo, hi, _ in w]
    assert widths == sorted(widths) and widths[-1] > widths[0]


def test_method_matches_same_phase_of_annual_cycle():
    # India-like: 6-month steps; 12/24-month chains (even steps) lose to persistence, 6/18-month chains (odd) win
    bt = _bt({1: 0.20, 2: -0.10, 3: 0.30, 4: -0.20}, steps=(1, 2, 3, 4))
    assert chain.method_for_step(bt, 5, 6)[0] == "chained_xgboost"          # 30 months ~ phase of 6/18 months
    assert chain.method_for_step(bt, 6, 6)[0] == "persistence_fallback"     # 36 months ~ phase of 12/24 months
    assert chain.method_for_step(bt, 7, 6)[0] == "chained_xgboost"
    assert chain.method_for_step(bt, 8, 6)[0] == "persistence_fallback"
    lo, hi, basis = chain.interval_for_step(bt, 5, "chained_xgboost", 6)    # scaled from step 3, not step 4
    assert basis == "extrapolated_sqrt_from_3_steps" and lo == pytest.approx(-3.0 * np.sqrt(5 / 3))


# ----------------------------------------------------------------------------- roll-forward engine
class _ConstDelta:
    """Fake regressor: predicts a fixed change, or reads chg_s1 to prove lags are rolled forward."""
    def __init__(self, delta=1.0, use_chg_s1=False):
        self.delta, self.use = delta, use_chg_s1
    def predict(self, X):
        return (X["chg_s1"].fillna(0).values * 0 + self.delta) if not self.use else X["chg_s1"].fillna(0).values


def _frame(n=3, region="maharashtra"):
    cols = chain.STEP_FEATURES[region]
    d = {"candidate_site_id": [f"S{i}" for i in range(n)], "date": pd.Timestamp("2026-05-30"),
         "cur": np.array([-10.0, -5.0, 0.0], dtype="float32")[:n]}
    for i in range(1, chain.N_LAGS[region] + 1):
        d[f"chg_s{i}"] = np.float32(0.5 * i)
    for c in ["exp_mean", "exp_std", "exp_min", "exp_max", "n_hist", "lat", "lon", "elevation"]:
        d[c] = np.float32(1.0)
    return pd.DataFrame(d)


def test_roll_levels_accumulates_predicted_changes():
    f = _frame()
    lv, steps, clip = chain.roll_levels("maharashtra", f, 1, 4, _ConstDelta(1.0), pd.Series(dtype=float), {})
    assert np.allclose(lv[:, 4], f["cur"].values + 4.0)
    assert len(steps) == 4 and not clip.any()


def test_roll_levels_feeds_predictions_back_as_lags():
    f = _frame()
    # model returns chg_s1 = (level now - level one step ago). Step 1 uses REAL lag (0.5); later steps use PREDICTED levels.
    lv, steps, _ = chain.roll_levels("maharashtra", f, 1, 3, _ConstDelta(use_chg_s1=True), pd.Series(dtype=float), {})
    x1 = steps[0][0]["chg_s1"].values
    assert np.allclose(x1, 0.5)                                    # real history at step 1
    d1 = steps[0][1]                                               # = 0.5
    assert np.allclose(lv[:, 1], f["cur"].values + 0.5)
    x2 = steps[1][0]["chg_s1"].values
    assert np.allclose(x2, lv[:, 1] - lv[:, 0])                    # now uses the predicted level
    assert np.allclose(steps[1][0]["chg_s2"].values, lv[:, 1] - (f["cur"].values - f["chg_s1"].values))  # mixes predicted + real


def test_roll_levels_persist_mask_keeps_level_unchanged():
    f = _frame()
    mask = np.array([True, False, True])
    lv, _, _ = chain.roll_levels("maharashtra", f, 1, 3, _ConstDelta(2.0), pd.Series(dtype=float), {}, persist_mask=mask)
    assert np.allclose(lv[mask, 3], f["cur"].values[mask])
    assert np.allclose(lv[~mask, 3], f["cur"].values[~mask] + 6.0)


def test_roll_levels_clips_to_plausible_range_and_flags():
    f = _frame()
    f["cur"] = np.float32(45.0)
    lv, _, clip = chain.roll_levels("maharashtra", f, 1, 3, _ConstDelta(4.0), pd.Series(dtype=float), {})
    assert lv.max() <= 50.0 and clip.all()


# ----------------------------------------------------------------------------- features: no leakage
def test_step_lags_use_only_past_observations():
    days = pd.date_range("2026-01-01", periods=120, freq="D")
    obs = pd.DataFrame({"candidate_site_id": "A", "date": days, "value": np.arange(120, dtype=float)})
    feats = pd.DataFrame({"candidate_site_id": "A", "date": [days[100]], "cur": np.float32(100.0)})
    out = chain.add_step_lags(feats, obs, "maharashtra", 1, 1)
    # one month before day-index 100 (2026-04-11) is 2026-03-11 = index 69 -> chg_s1 = 100 - 69
    assert out["chg_s1"].iloc[0] == pytest.approx(100 - 69)
    obs2 = obs.copy(); obs2.loc[obs2.date > days[100], "value"] = 9999.0       # corrupt the future
    out2 = chain.add_step_lags(feats.drop(columns=["chg_s1", "chg_s2"]), obs2, "maharashtra", 1, 1)
    assert out2["chg_s1"].iloc[0] == out["chg_s1"].iloc[0]


# ----------------------------------------------------------------------------- API
@pytest.fixture
def chain_client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from src.api.main import app
    from src.api.routes import future_forecast as ff
    ff._cache.clear()
    monkeypatch.setattr(ff, "OUT_DIR", tmp_path)
    row = {"candidate_site_id": "MH_X", "region": "maharashtra", "estimate_label": chain.LABEL, "origin_date": "2026-05-30",
           "origin_water_level": -10.0, "requested_target_date": "2026-11-10", "predicted_for_date": "2026-11-30",
           "n_steps": 6, "step_months": 1, "backtested_steps": 2, "data_gap_days": 184, "method": "persistence_fallback",
           "method_reason": "no skill", "predicted_water_level": -10.0, "predicted_change": 0.0,
           "predicted_lower_80": -14.0, "predicted_upper_80": -5.0, "interval_basis": "extrapolated_sqrt_from_2_steps",
           "predicted_percentile_vs_history": np.nan, "current_condition_state": "HIGH",
           "predicted_condition_state": "INSUFFICIENT_HISTORY", "predicted_state_confidence": np.nan,
           "lat": 18.0, "lon": 75.0, "warnings": "a; b", "path_levels": json.dumps([{"date": "2026-05-30", "level": -10.0}]),
           "state": "Maharashtra", "district": "Pune", "water_level_unit": "meters", "data_through": "2026-05-30"}
    for c in CONDITION_ORDER:
        row[f"prob_{c}"] = np.nan
    pd.DataFrame([row]).to_parquet(tmp_path / "maharashtra_chained_forecast.parquet", index=False)
    (tmp_path / "maharashtra_chain_summary.json").write_text(json.dumps({"label": chain.LABEL}))
    yield TestClient(app)
    ff._cache.clear()


def test_api_chained_site(chain_client):
    d = chain_client.get("/api/v1/maharashtra/candidate-sites/MH_X/chained-forecast").json()
    assert d["estimate_label"] == chain.LABEL and d["warnings"] == ["a", "b"]
    assert d["path_levels"][0]["level"] == -10.0 and d["predicted_state_confidence"] is None
    assert set(d["predicted_condition_probabilities"]) == set(CONDITION_ORDER)


def test_api_chained_list_summary_and_404(chain_client):
    lst = chain_client.get("/api/v1/maharashtra/chained-forecast").json()
    assert len(lst) == 1 and "path_levels" not in lst[0]
    assert chain_client.get("/api/v1/maharashtra/chained-forecast/summary").json()["label"] == chain.LABEL
    assert chain_client.get("/api/v1/maharashtra/candidate-sites/NOPE/chained-forecast").status_code == 404
    assert chain_client.get("/api/v1/india/candidate-sites/IND_X/chained-forecast").status_code == 404
