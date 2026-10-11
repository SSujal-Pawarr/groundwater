"""
Chained ("rolled-forward") forecast to ANY target date, for when the data ends before "now".

  python -m src.forecasting.chain --region maharashtra                 # target = today + horizon
  python -m src.forecasting.chain --region india --target-date 2027-04-10

Why a dedicated "step model"?
  The direct models (pipeline.py) use inputs such as 7-day change or district rainfall that do NOT exist for a
  predicted future month, so they cannot be fed their own output. The step model uses ONLY inputs that can be
  rolled forward: the current level, the level 1..L steps ago, per-site history statistics (frozen at the last
  real reading) and, for India, the season. It is applied repeatedly: level(t+h) -> level(t+2h) -> ...

Honesty controls
  * Uncertainty at step k comes from a BACKTEST of the same chaining procedure on held-out origins.
    Beyond the number of steps the data can backtest, the width is extrapolated with sqrt(k/K) (an ASSUMPTION, flagged).
  * Every row is labelled ESTIMATED_WITHOUT_RECENT_DATA and carries n_steps and warnings
    (e.g. forecast period includes monsoon months that are absent from the training data).
  * Levels are clipped to the M3 plausibility range; clipped rows are flagged.
"""
from __future__ import annotations
import argparse, gc, json, time
from datetime import datetime, timezone
import numpy as np
import pandas as pd

from . import FUTURE_FORECAST_VERSION
from .config import CONFIGS, OUT_DIR, MODEL_DIR, DOCS_DIR, CONDITION_ORDER, XGBClsParams
from .data import load_observations, season_of_month_map
from .features import build_features, reference_percentile
from .models import fit_regressor, fit_classifier, oof_regression_predictions, used_rounds
from .pairs import state_from_percentile
from .pipeline import (evaluate_horizon, run_classification, reg_params_for, _stage2_frame, mask_unclassifiable,
                       _cap, _log)

N_LAGS = {"maharashtra": 2, "india": 4}
STEP_FEATURES = {
    "maharashtra": ["cur", "chg_s1", "chg_s2", "exp_mean", "exp_std", "exp_min", "exp_max", "cur_minus_exp_mean",
                    "cur_z", "n_hist", "lat", "lon", "elevation"],
    "india": ["cur", "chg_s1", "chg_s2", "chg_s3", "chg_s4", "exp_mean", "exp_std", "cur_minus_exp_mean", "n_hist",
              "grp_mean", "cur_minus_grp_mean", "origin_month", "lat", "lon"],
}
PLAUSIBLE = {"maharashtra": (-100.0, 50.0), "india": (0.0, 150.0)}       # M3 quality thresholds
BACKTEST_CUTOFF = {"maharashtra": "2026-03-15", "india": None}           # None -> cfg.test_start
BACKTEST_K = {"maharashtra": 2, "india": 4}
MAX_STEPS = {"maharashtra": 8, "india": 8}
BACKTEST_MAX_ORIGINS = 120_000
LABEL = "ESTIMATED_WITHOUT_RECENT_DATA"


# --------------------------------------------------------------------------- step features on real data
def _lookup_months(frame: pd.DataFrame, obs: pd.DataFrame, months: int, tol_days: int, direction_sign: int) -> np.ndarray:
    """Real observation closest to (origin +/- months) within tolerance; NaN if none. sign=-1 back, +1 forward."""
    key = frame["date"] + pd.DateOffset(months=direction_sign * months)
    left = pd.DataFrame({"candidate_site_id": frame["candidate_site_id"].values, "key": key.values,
                         "_i": np.arange(len(frame))}).sort_values("key")
    right = obs[["candidate_site_id", "date", "value"]].rename(columns={"date": "_rd", "value": "_rv"}).sort_values("_rd")
    m = pd.merge_asof(left, right, left_on="key", right_on="_rd", by="candidate_site_id",
                      tolerance=pd.Timedelta(days=tol_days), direction="nearest")
    out = np.full(len(frame), np.nan)
    out[m["_i"].values] = m["_rv"].values
    return out


def add_step_lags(feats: pd.DataFrame, obs: pd.DataFrame, region: str, h: int, tol_days: int) -> pd.DataFrame:
    for i in range(1, N_LAGS[region] + 1):
        lag = _lookup_months(feats, obs, h * i, tol_days, -1)
        feats[f"chg_s{i}"] = (feats["cur"].values.astype("float64") - lag).astype("float32")
    return feats


# --------------------------------------------------------------------------- the roll-forward engine
def _group_of_month(region, months, season_map):
    if region == "maharashtra":
        return np.array(["ALL"] * len(months))
    return pd.Series(months).map(season_map).fillna("UNKNOWN").values


def roll_levels(region, frame, h, K, reg, grp_tbl, season_map, persist_mask=None):
    """
    frame: one row per origin with step features at the real origin (+ frozen history stats).
    Returns levels[n, K+1] (index 0 = real origin level) and, per step, the feature frame X_j and predicted delta d_j.
    """
    n, L = len(frame), N_LAGS[region]
    cols = STEP_FEATURES[region]
    lo, hi = PLAUSIBLE[region]
    cur0 = frame["cur"].values.astype("float64")
    back = {m: cur0 - frame[f"chg_s{m}"].values.astype("float64") for m in range(1, L + 1)}
    levels = np.full((n, K + 1), np.nan)
    levels[:, 0] = cur0
    clipped = np.zeros(n, dtype=bool)
    steps = []
    sites = frame["candidate_site_id"].values
    for j in range(1, K + 1):
        t = j - 1
        cur_t = levels[:, t]
        X = pd.DataFrame({"cur": cur_t})
        for i in range(1, L + 1):
            idx = t - i
            lag = levels[:, idx] if idx >= 0 else back[-idx]
            X[f"chg_s{i}"] = cur_t - lag
        for c in cols:                         # frozen (real-history) features
            if c not in X.columns and c in frame.columns and c not in ("cur_minus_exp_mean", "cur_z", "grp_mean",
                                                                          "cur_minus_grp_mean", "origin_month"):
                X[c] = frame[c].values
        X["cur_minus_exp_mean"] = cur_t - frame["exp_mean"].values
        if region == "maharashtra":
            es = frame["exp_std"].values.astype("float64")
            X["cur_z"] = np.where(es > 1e-9, (cur_t - frame["exp_mean"].values) / np.where(es > 1e-9, es, 1), np.nan)
        else:
            o_dates = frame["date"] + pd.DateOffset(months=h * t)
            mon = o_dates.dt.month.values
            X["origin_month"] = mon
            grp = _group_of_month(region, mon, season_map)
            gm = grp_tbl.reindex(pd.MultiIndex.from_arrays([sites, grp])).values
            X["grp_mean"] = gm
            X["cur_minus_grp_mean"] = cur_t - gm
        X = X[cols].astype("float32")
        d = reg.predict(X).astype("float64")
        if persist_mask is not None:            # persistence fallback: level stays unchanged at every step
            d = np.where(persist_mask, 0.0, d)
        new = cur_t + d
        c_flag = (new < lo) | (new > hi)
        clipped |= c_flag
        levels[:, j] = np.clip(new, lo, hi)
        steps.append((X, d))
    return levels, steps, clipped


# --------------------------------------------------------------------------- backtest of the chaining procedure
def _regress_metrics(actual, pred, cur):
    e = pred - actual
    ss_tot = float(np.sum((actual - actual.mean()) ** 2))
    return {"n": int(len(actual)), "mae": float(np.mean(np.abs(e))), "rmse": float(np.sqrt(np.mean(e ** 2))),
            "r2": float(1 - np.sum(e ** 2) / ss_tot) if ss_tot > 0 else float("nan"), "bias": float(np.mean(e))}


def backtest_chain(cfg, region, h, feats, obs, reg_bt, grp_tbl, season_map, cutoff):
    K = BACKTEST_K[region]
    fr = feats[feats["date"] >= pd.Timestamp(cutoff)]
    fr = fr.sample(min(len(fr), BACKTEST_MAX_ORIGINS), random_state=7).reset_index(drop=True)
    levels, _, _ = roll_levels(region, fr, h, K, reg_bt, grp_tbl, season_map)
    out = {}
    for k in range(1, K + 1):
        actual = _lookup_months(fr, obs, h * k, cfg.tolerance_days[h], +1)
        ok = ~np.isnan(actual) & ~np.isnan(levels[:, k])
        if ok.sum() < 200:
            out[k] = {"n": int(ok.sum()), "evaluable": False}
            continue
        a, p, c = actual[ok], levels[ok, k], levels[ok, 0]
        chain, pers = _regress_metrics(a, p, c), _regress_metrics(a, c, c)
        resid = a - p
        out[k] = {"evaluable": True, "months_ahead": h * k, "chain": chain, "persistence": pers,
                  "rmse_skill_vs_persistence": float(1 - chain["rmse"] / pers["rmse"]),
                  "resid_q10": float(np.quantile(resid, 0.10)), "resid_q90": float(np.quantile(resid, 0.90)),
                  "pers_resid_q10": float(np.quantile(a - c, 0.10)), "pers_resid_q90": float(np.quantile(a - c, 0.90))}
    return out


def _ref_step(bt, k, h):
    """
    Backtested step used to judge / size step k. If k itself was backtested use it; otherwise use the largest
    backtested step in the SAME PHASE OF THE ANNUAL CYCLE ((k*h) mod 12), because skill depends strongly on it
    (after 12/24 months a site is back in the same season, where 'unchanged' is already a strong baseline).
    If no step shares the phase, fall back to the largest backtested step.
    """
    ev = sorted(s_ for s_, v in bt.items() if v.get("evaluable"))
    if not ev:
        return None, None
    if k in ev:
        return k, ev[-1]
    same = [s_ for s_ in ev if (s_ * h) % 12 == (k * h) % 12]
    return (max(same) if same else ev[-1]), ev[-1]


def method_for_step(bt, k, h):
    """'chained_xgboost' only if the backtest shows it beats persistence (RMSE) at a comparable step count."""
    ref, _ = _ref_step(bt, k, h)
    if ref is None:
        return "persistence_fallback", "no evaluable backtest"
    sk = bt[ref]["rmse_skill_vs_persistence"]
    if sk > 0:
        return "chained_xgboost", f"backtest RMSE skill vs persistence = {sk*100:+.1f}% at {ref} step(s) ({ref*h} months)"
    return "persistence_fallback", (f"chained model did not beat persistence in the backtest "
                                    f"(RMSE skill {sk*100:+.1f}% at {ref} step(s) = {ref*h} months)")


def interval_for_step(bt, k, method, h):
    """(q10, q90, basis). Measured if step k was backtested, else scaled from the comparable step by sqrt(k/ref) (assumption)."""
    ref, _ = _ref_step(bt, k, h)
    if ref is None:
        return None
    kq10, kq90 = ("resid_q10", "resid_q90") if method == "chained_xgboost" else ("pers_resid_q10", "pers_resid_q90")
    if k == ref:
        return bt[ref][kq10], bt[ref][kq90], "backtest_measured"
    f = np.sqrt(k / ref)
    return bt[ref][kq10] * f, bt[ref][kq90] * f, f"extrapolated_sqrt_from_{ref}_steps"


# --------------------------------------------------------------------------- final models
def fit_final_models(cfg, pairs, obs, cols, reg_rounds, cls_rounds, rp, cp):
    inc_m = cfg.region == "india"
    lab = _cap(pairs[pairs.label_id >= 0], int(cfg.max_train_rows * 1.3) if cfg.max_train_rows else None).copy()
    rounds = max(int(reg_rounds * 1.1), 50)
    reg = fit_regressor(lab[cols], lab.target_delta.values, params=rp, n_estimators=rounds)
    oof = oof_regression_predictions(lab[cols], lab.target_delta.values, lab.candidate_site_id.values, rounds, rp,
                                     cfg.n_oof_folds)
    clf = fit_classifier(_stage2_frame(lab, oof, obs, cfg, cols, inc_m), lab.label_id.values, params=cp,
                         n_estimators=max(int(cls_rounds * 1.1), 30))
    return reg, clf


# --------------------------------------------------------------------------- live chained forecast
def chained_forecast(cfg, region, h, feats, obs, reg, clf, grp_tbl, season_map, bt, target_date, max_steps):
    data_end = obs["date"].max()
    cols = STEP_FEATURES[region]
    inc_m = region == "india"
    latest = feats.sort_values("date").groupby("candidate_site_id", sort=False).tail(1).copy().reset_index(drop=True)
    n_all = len(latest)
    months_gap = (target_date - latest["date"]).dt.days.values / 30.4375
    k = np.maximum(np.rint(months_gap / h).astype(int), 1)
    keep = k <= max_steps
    latest, k = latest[keep].reset_index(drop=True), k[keep]
    k_exact = np.maximum(months_gap[keep] / h, 1e-6)      # exact distance to the target, in steps (fractional)
    _log(f"{region}: {len(latest):,} of {n_all:,} sites within {max_steps} steps of target {target_date.date()}")
    Kmax = int(k.max())
    meth = {int(kk): method_for_step(bt, int(kk), h) for kk in np.unique(k)}
    persist = np.array([meth[int(kk)][0] == "persistence_fallback" for kk in k])
    levels, steps, clipped_any = roll_levels(region, latest, h, Kmax, reg, grp_tbl, season_map, persist_mask=persist)

    n = len(latest)
    idx = np.arange(n)
    pred_level = levels[idx, k]
    origin_level = levels[:, 0]
    # step-wise clip flag and path
    final = {c: np.full(n, np.nan) for c in ["pct", "conf"] + [f"p_{c}" for c in CONDITION_ORDER]}
    state = np.array(["INSUFFICIENT_HISTORY"] * n, dtype=object)
    cur_state = np.array(["INSUFFICIENT_HISTORY"] * n, dtype=object)
    for j in range(1, Kmax + 1):
        sel = np.flatnonzero(k == j)
        if len(sel) == 0:
            continue
        X, d = steps[j - 1]
        t = j - 1
        o_dates = latest["date"].iloc[sel] + pd.DateOffset(months=h * t)
        t_dates = latest["date"].iloc[sel] + pd.DateOffset(months=h * j)
        o_grp = _group_of_month(region, o_dates.dt.month.values, season_map)
        t_grp = _group_of_month(region, t_dates.dt.month.values, season_map)
        df = X.iloc[sel].copy().reset_index(drop=True)
        df["candidate_site_id"] = latest["candidate_site_id"].values[sel]
        df["date"] = o_dates.values
        df["target_date"] = t_dates.values
        df["target_group"] = t_grp
        cur_pct = reference_percentile(obs, df.candidate_site_id.values, df.date.values, o_grp,
                                       df["cur"].values.astype("float64"), cfg.min_reference_obs)
        df["cur_pct"] = cur_pct
        cur_state[sel] = state_from_percentile(cur_pct)
        X2 = _stage2_frame(df, d[sel], obs, cfg, cols, inc_m)
        proba = clf.predict_proba(X2)
        cid = proba.argmax(1)
        state[sel] = [CONDITION_ORDER[i] for i in cid]
        final["pct"][sel] = X2["pred_pct"].values
        final["conf"][sel] = proba.max(1)
        for i, c in enumerate(CONDITION_ORDER):
            final[f"p_{c}"][sel] = proba[:, i]

    # intervals
    # Sites on the "level unchanged" method do not move with the date, so they are reported EXACTLY at the requested
    # target date and their uncertainty is sized from the exact time gap. Model-driven sites end on a whole step.
    lo_w, hi_w, basis = np.full(n, np.nan), np.full(n, np.nan), np.array([""] * n, dtype=object)
    for i in range(n):
        k_eff = float(k_exact[i]) if persist[i] else int(k[i])
        iv = interval_for_step(bt, k_eff, meth[int(k[i])][0], h)
        if iv is not None:
            lo_w[i], hi_w[i], basis[i] = iv[0], iv[1], iv[2]
    pred_dates = pd.Series([target_date if persist[i] else latest["date"].iloc[i] + pd.DateOffset(months=int(h * k[i]))
                            for i in range(n)])
    K_bt = max([s for s, v in bt.items() if v.get("evaluable")] or [0])
    obs_months = obs["date"].dt.month.value_counts(normalize=True)
    monsoon_seen = any(obs_months.get(m, 0) >= 0.02 for m in (6, 7, 8, 9))
    warn = []
    for i in range(n):
        w = []
        if k[i] > K_bt:
            w.append(f"{int(k[i])} chained steps exceed the {K_bt} step(s) that could be backtested; interval width is extrapolated")
        if not monsoon_seen:
            path_months = {(latest['date'].iloc[i] + pd.DateOffset(months=int(h * s))).month for s in range(1, int(k[i]) + 1)}
            if path_months & {6, 7, 8, 9}:
                w.append("forecast path crosses monsoon months (Jun-Sep) that are absent from the training data; "
                         "monsoon recharge cannot be anticipated")
        if persist[i]:
            w.append("chained model showed no skill over 'level unchanged' in the backtest, so the last known level is used")
        if clipped_any[i]:
            w.append("level clipped to plausible range")
        warn.append("; ".join(w))

    path = [json.dumps([{"date": (latest["date"].iloc[i] + pd.DateOffset(months=int(h * s))).strftime("%Y-%m-%d"),
                         "level": round(float(levels[i, s]), 3)} for s in range(0, int(k[i]) + 1)]) for i in range(n)]
    meta = obs.groupby("candidate_site_id").agg(state=("state", "last"), district=("district", "last"),
                                                unit=("unit", "last")).reset_index()
    out = pd.DataFrame({
        "candidate_site_id": latest["candidate_site_id"].values, "region": region,
        "estimate_label": LABEL,
        "origin_date": latest["date"].dt.strftime("%Y-%m-%d").values, "origin_water_level": origin_level,
        "requested_target_date": str(target_date.date()),
        "predicted_for_date": pred_dates.dt.strftime("%Y-%m-%d").values,
        "n_steps": k, "step_months": h, "backtested_steps": K_bt,
        "months_to_target": np.round(np.where(persist, k_exact * h, k * h), 2),
        "method": np.where(persist, "persistence_fallback", "chained_xgboost"),
        "method_reason": [meth[int(x)][1] for x in k],
        "data_gap_days": (pred_dates - data_end).dt.days.values,
        "predicted_water_level": pred_level, "predicted_change": pred_level - origin_level,
        "predicted_lower_80": pred_level + lo_w, "predicted_upper_80": pred_level + hi_w, "interval_basis": basis,
        "predicted_percentile_vs_history": final["pct"],
        "current_condition_state": cur_state,
        "predicted_condition_state": state, "predicted_state_confidence": final["conf"],
    })
    for c in CONDITION_ORDER:
        out[f"prob_{c}"] = final[f"p_{c}"]
    out["lat"], out["lon"] = latest["lat"].values, latest["lon"].values
    out["warnings"] = warn
    out["path_levels"] = path
    out = out.merge(meta, on="candidate_site_id", how="left").rename(columns={"unit": "water_level_unit"})
    out = mask_unclassifiable(out)
    out["model_version"] = FUTURE_FORECAST_VERSION + "-chain"
    out["data_through"] = str(data_end.date())
    out["generated_on"] = str(pd.Timestamp.now().date())
    return out, {"sites_total": int(n_all), "sites_forecast": int(n), "sites_excluded_too_many_steps": int(n_all - n),
                 "steps_distribution": {str(s): int(c) for s, c in zip(*np.unique(k, return_counts=True))},
                 "method_counts": {"chained_xgboost": int((~persist).sum()), "persistence_fallback": int(persist.sum())},
                 "method_by_steps": {str(a): b for a, b in meth.items()},
                 "monsoon_months_in_training_data": bool(monsoon_seen)}


# --------------------------------------------------------------------------- driver
def run_chain(region, horizon=None, target_date=None, max_steps=None, max_train_rows=None):
    cfg = CONFIGS[region]
    if max_train_rows is not None:
        cfg.max_train_rows = max_train_rows
    if horizon is None:
        sj = OUT_DIR / f"{region}_summary.json"
        if not sj.exists():
            raise SystemExit(f"Run `python -m src.forecasting.pipeline --region {region}` first (or pass --horizon).")
        horizon = json.loads(sj.read_text())["selection"]["selected_horizon_months"]
    h = int(horizon)
    t0 = time.time()
    rp, cp = reg_params_for(cfg), XGBClsParams()
    obs = load_observations(cfg)
    data_end = obs["date"].max()
    target = pd.Timestamp(target_date) if target_date else (pd.Timestamp.now().normalize() + pd.DateOffset(months=h))
    if target <= data_end:
        raise SystemExit(f"Target date {target.date()} must be after the data end {data_end.date()}; use the direct forecast instead.")
    _log(f"=== chained forecast {region}: step={h} month(s), data ends {data_end.date()}, target {target.date()}")
    feats = build_features(region, obs)
    feats = add_step_lags(feats, obs, region, h, cfg.tolerance_days[h])
    cols = STEP_FEATURES[region]
    season_map = season_of_month_map(obs)
    grp_tbl = obs.groupby(["candidate_site_id", "group"])["value"].mean()

    # 1) step model, standard chronological evaluation (also gives pairs)
    res, pairs = evaluate_horizon(cfg, feats, obs, h, cols, rp)
    if not res["feasible"]:
        raise SystemExit(f"Step model not feasible: {res['reason']}")
    m = res["test"]["xgboost_regressor"]; b = res["test"]["baseline_persistence"]
    _log(f"step model (1 step) TEST  R2={m['r2']:.4f} MAE={m['mae']:.3f} RMSE={m['rmse']:.3f} | persistence R2={b['r2']:.4f} RMSE={b['rmse']:.3f}")

    # 2) classifier on the step model (also gives labelled pairs)
    cmetrics, pairs, cls_rounds = run_classification(cfg, pairs, obs, cols, res["n_rounds"], rp, cp)
    a = cmetrics["xgboost_classifier"]
    _log(f"step classifier TEST acc={a['accuracy']:.3f} macroF1={a['macro_f1']:.3f} | persistence acc={cmetrics['baseline_persistence_state']['accuracy']:.3f}")

    # 3) backtest of the CHAINING procedure with a model that never saw the backtest period
    cutoff = BACKTEST_CUTOFF[region] or cfg.test_start
    tr = _cap(pairs[pairs["target_date"] < pd.Timestamp(cutoff)], cfg.max_train_rows)
    reg_bt = fit_regressor(tr[cols], tr.target_delta.values, params=rp, n_estimators=res["n_rounds"])
    bt = backtest_chain(cfg, region, h, feats, obs, reg_bt, grp_tbl, season_map, cutoff)
    for kk, v in bt.items():
        if v.get("evaluable"):
            _log(f"backtest {kk} step(s) = {v['months_ahead']}m: n={v['chain']['n']:,} chain RMSE={v['chain']['rmse']:.3f} "
                 f"R2={v['chain']['r2']:.4f} | persistence RMSE={v['persistence']['rmse']:.3f} | 80% resid [{v['resid_q10']:.2f},{v['resid_q90']:.2f}]")
        else:
            _log(f"backtest {kk} step(s): not enough evaluable origins (n={v['n']})")
    del reg_bt; gc.collect()

    # 4) final models + live chained forecast
    reg, clf = fit_final_models(cfg, pairs, obs, cols, res["n_rounds"], cls_rounds, rp, cp)
    del pairs; gc.collect()
    out, info = chained_forecast(cfg, region, h, feats, obs, reg, clf, grp_tbl, season_map, bt, target,
                                 max_steps or MAX_STEPS[region])
    OUT_DIR.mkdir(parents=True, exist_ok=True); MODEL_DIR.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT_DIR / f"{region}_chained_forecast.parquet", index=False)
    reg.save_model(str(MODEL_DIR / f"{region}_step{h}_regressor.json"))
    clf.save_model(str(MODEL_DIR / f"{region}_step{h}_classifier.json"))
    summary = {
        "version": FUTURE_FORECAST_VERSION + "-chain", "region": region, "label": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(), "data_through": str(data_end.date()),
        "requested_target_date": str(target.date()), "step_months": h,
        "data_gap_months": round((target - data_end).days / 30.4375, 1),
        "step_model_single_step_test": {"regression": res["test"], "n_rounds": res["n_rounds"],
                                        "top_features": res["top_features"]},
        "step_model_classification": cmetrics,
        "chain_backtest": {"cutoff": cutoff, "max_backtested_steps": BACKTEST_K[region],
                           "by_steps": {str(k): v for k, v in bt.items()},
                           "note": ("Backtest trains on data before the cutoff and chains forward from origins after it; "
                                    "interval widths beyond the backtested steps are extrapolated with sqrt(k/K) (assumption).")},
        "forecast_artifact": {"file": f"data/future_forecast/{region}_chained_forecast.parquet", **info,
                              "predicted_state_distribution": out.predicted_condition_state.value_counts().to_dict()},
        "caveats": [
            "Rough estimate produced by feeding the model its own predictions; errors compound with every step.",
            "No information after the data end (rainfall, pumping, recharge) is used.",
            "Probabilities/classes are computed on the point forecast of the last step and understate multi-step uncertainty.",
        ],
    }
    (OUT_DIR / f"{region}_chain_summary.json").write_text(json.dumps(summary, indent=2, default=float))
    (DOCS_DIR / f"future_forecast_chain_results_{region}.json").write_text(json.dumps(summary, indent=2, default=float))
    _log(f"wrote {len(out):,} chained forecasts in {time.time()-t0:.0f}s")
    return summary


def main():
    ap = argparse.ArgumentParser(description="Chained (recursive) forecast to any target date")
    ap.add_argument("--region", choices=["maharashtra", "india", "all"], default="maharashtra")
    ap.add_argument("--horizon", type=int, default=None, help="step length in months (default: selected horizon)")
    ap.add_argument("--target-date", default=None, help="YYYY-MM-DD (default: today + horizon)")
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--max-train-rows", type=int, default=None)
    a = ap.parse_args()
    for r in (["maharashtra", "india"] if a.region == "all" else [a.region]):
        run_chain(r, a.horizon, a.target_date, a.max_steps, a.max_train_rows)


if __name__ == "__main__":
    main()
