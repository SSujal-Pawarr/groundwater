"""
Orchestration:
  1. Regression for every horizon  (XGBoost Regressor -> future water level)
  2. Horizon selection             (most accurate feasible horizon wins)
  3. Classification                (XGBoost Classifier on top of the regressor output -> future condition state)
  4. Final refit + live forecast artifact for the selected horizon

Run:  python -m src.forecasting.pipeline --region maharashtra
      python -m src.forecasting.pipeline --region india --horizons 1 6 12
"""
from __future__ import annotations
import argparse, gc, json, time
from datetime import datetime, timezone
import numpy as np
import pandas as pd

from . import FUTURE_FORECAST_VERSION
from .config import (CONFIGS, DEFAULT_HORIZONS, OUT_DIR, MODEL_DIR, DOCS_DIR, CONDITION_ORDER, XGBRegParams,
                     XGBClsParams, DatasetConfig)
from .data import load_observations, season_of_month_map
from .features import build_features, feature_columns, reference_percentile
from .pairs import build_pairs, assign_split, add_future_labels, state_from_percentile, state_to_id
from .models import (fit_regressor, used_rounds, evaluate_regression, regression_metrics, oof_regression_predictions,
                     fit_classifier, classification_metrics)
from .selection import select_best_horizon


def _log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def reg_params_for(cfg: DatasetConfig) -> XGBRegParams:
    if cfg.region == "maharashtra":   # only ~5 months of history: small, strongly regularised, no early stopping
        return XGBRegParams(n_estimators=300, max_depth=4, min_child_weight=20.0, learning_rate=0.05,
                            objective="reg:pseudohubererror", huber_slope=1.0)
    return XGBRegParams()


def _cap(df: pd.DataFrame, n):
    return df.sample(n, random_state=42) if n and len(df) > n else df


# ----------------------------------------------------------------------------- stage 1
def evaluate_horizon(cfg, feats, obs, h, feat_cols, rp):
    tol = cfg.tolerance_days[h]
    pairs = build_pairs(feats, obs, h, tol)
    out = {"horizon_months": h, "tolerance_days": tol, "n_pairs_total": int(len(pairs))}
    if len(pairs) == 0:
        out.update(feasible=False, reason=f"No observation exists within +/-{tol} days of origin + {h} month(s) "
                                          f"for any site (data cadence / coverage too short).")
        return out, None
    pairs["split"] = assign_split(pairs, cfg).values
    cnt = pairs["split"].value_counts().to_dict()
    out["pairs_by_split"] = {k: int(v) for k, v in cnt.items()}
    ntr, nte = cnt.get("train", 0), cnt.get("test", 0)
    if ntr < cfg.min_train_pairs or nte < cfg.min_test_pairs:
        out.update(feasible=False, reason=f"Insufficient chronological pairs after purged split "
                                          f"(train={ntr}<{cfg.min_train_pairs} or test={nte}<{cfg.min_test_pairs}).")
        return out, None

    tr = _cap(pairs[pairs.split == "train"], cfg.max_train_rows)
    va = _cap(pairs[pairs.split == "val"], 150_000)
    te = pairs[pairs.split == "test"]
    _log(f"h={h}m  train={len(tr):,} val={len(va):,} test={len(te):,}  fitting regressor")
    model = fit_regressor(tr[feat_cols], tr.target_delta.values,
                          va[feat_cols] if len(va) else None, va.target_delta.values if len(va) else None, rp)
    med = float(tr.target_delta.median())
    cur_te = te.cur.values.astype("float64")
    pred_te = cur_te + model.predict(te[feat_cols])
    test_m = evaluate_regression(te.target_value.values, pred_te, cur_te, med)
    trs = tr.sample(min(len(tr), 100_000), random_state=1)
    train_m = regression_metrics(trs.target_value.values, trs.cur.values.astype("float64") + model.predict(trs[feat_cols]),
                                 trs.cur.values.astype("float64"))
    resid = te.target_delta.values - (pred_te - cur_te)
    out.update(feasible=True, test=test_m, train_in_sample={"mae": train_m["mae"], "rmse": train_m["rmse"], "r2": train_m["r2"]},
               n_rounds=used_rounds(model),
               residual_change_quantiles={"q10": float(np.quantile(resid, 0.10)), "q90": float(np.quantile(resid, 0.90)),
                                          "empirical_coverage_80": float(np.mean((resid >= np.quantile(resid, .1)) & (resid <= np.quantile(resid, .9))))},
               test_window={"origin_from": str(te.date.min().date()), "origin_to": str(te.date.max().date()),
                            "target_to": str(te.target_date.max().date())})
    imp = pd.Series(model.feature_importances_, index=feat_cols).sort_values(ascending=False)
    out["top_features"] = {k: float(v) for k, v in imp.head(8).items()}
    return out, pairs


# ----------------------------------------------------------------------------- stage 2
CLS_EXTRA = ["pred_delta", "pred_level", "pred_pct", "cur_pct"]


def _stage2_frame(df, pred_delta, obs, cfg, feat_cols, include_target_month):
    X = df[feat_cols].copy()
    X["pred_delta"] = pred_delta.astype("float32")
    pred_level = df["cur"].values.astype("float64") + pred_delta
    X["pred_level"] = pred_level.astype("float32")
    X["pred_pct"] = reference_percentile(obs, df["candidate_site_id"].values, df["date"].values,
                                         df["target_group"].values, pred_level, cfg.min_reference_obs).astype("float32")
    X["cur_pct"] = df["cur_pct"].values.astype("float32")
    if include_target_month:
        X["target_month"] = pd.to_datetime(df["target_date"]).dt.month.values.astype("float32")
    return X


def run_classification(cfg, pairs, obs, feat_cols, reg_rounds, rp, cp):
    inc_m = cfg.region == "india"
    pairs = add_future_labels(pairs, obs, cfg)
    lab = pairs[pairs.label_id >= 0]
    tr = _cap(lab[lab.split == "train"], cfg.max_train_rows)
    va = _cap(lab[lab.split == "val"], 150_000)
    te = lab[lab.split == "test"]
    _log(f"classification  train={len(tr):,} val={len(va):,} test={len(te):,}  (OOF regression, {cfg.n_oof_folds} folds)")

    oof = oof_regression_predictions(tr[feat_cols], tr.target_delta.values, tr.candidate_site_id.values,
                                     reg_rounds, rp, cfg.n_oof_folds)
    full_reg = fit_regressor(tr[feat_cols], tr.target_delta.values, params=rp, n_estimators=reg_rounds)
    Xtr = _stage2_frame(tr, oof, obs, cfg, feat_cols, inc_m)
    Xva = _stage2_frame(va, full_reg.predict(va[feat_cols]), obs, cfg, feat_cols, inc_m) if len(va) else None
    Xte = _stage2_frame(te, full_reg.predict(te[feat_cols]), obs, cfg, feat_cols, inc_m)
    clf = fit_classifier(Xtr, tr.label_id.values, Xva, va.label_id.values if len(va) else None, cp)
    p_te = clf.predict_proba(Xte)
    y = te.label_id.values
    metrics = {"xgboost_classifier": classification_metrics(y, p_te.argmax(1))}
    fb = lambda s: np.where(s < 0, 2, s)  # unknown current state -> NORMAL_RANGE
    metrics["baseline_persistence_state"] = classification_metrics(y, fb(state_to_id(te.cur_state.values)))
    metrics["baseline_rule_on_regressor_output"] = classification_metrics(y, fb(state_to_id(state_from_percentile(Xte.pred_pct.values))))
    majority = int(pd.Series(tr.label_id.values).mode().iloc[0])
    metrics["baseline_majority_class"] = classification_metrics(y, np.full(len(y), majority))
    metrics["baseline_majority_class"]["class"] = CONDITION_ORDER[majority]
    imp = pd.Series(clf.feature_importances_, index=Xtr.columns).sort_values(ascending=False)
    metrics["top_features"] = {k: float(v) for k, v in imp.head(8).items()}
    metrics["n_rounds"] = used_rounds(clf)
    metrics["label_definition"] = ("Condition state (P10/P25/P75/P90, same thresholds as M8.2-D) of the ACTUAL future value "
                                   "relative to the site's own history known at the forecast origin" +
                                   (" (same analytical season)." if cfg.region == "india" else "."))
    return metrics, pairs, used_rounds(clf)


# ----------------------------------------------------------------------------- stage 3

def mask_unclassifiable(out: pd.DataFrame) -> pd.DataFrame:
    """
    The classifier is only trained on rows whose future percentile is defined (>= min reference observations).
    Where the reference history is too short the percentile feature is NaN -> inputs are out-of-distribution and any
    class would be spurious. Report INSUFFICIENT_HISTORY instead (same convention as M8.2-D); the regression
    forecast of the water level itself is kept.
    """
    m = out["predicted_percentile_vs_history"].isna()
    out.loc[m, "predicted_condition_state"] = "INSUFFICIENT_HISTORY"
    out.loc[m, "predicted_state_confidence"] = np.nan
    for c in CONDITION_ORDER:
        out.loc[m, f"prob_{c}"] = np.nan
    return out

def final_forecast(cfg, obs, feats, pairs, h, feat_cols, reg_rounds, cls_rounds, rp, cp, season_map, resid_q, tag):
    inc_m = cfg.region == "india"
    lab = _cap(pairs[pairs.label_id >= 0], int(cfg.max_train_rows * 1.3) if cfg.max_train_rows else None).copy()
    del pairs; gc.collect()
    _log(f"final refit on {len(lab):,} pairs (all periods)")
    reg = fit_regressor(lab[feat_cols], lab.target_delta.values, params=rp, n_estimators=max(int(reg_rounds * 1.1), 50))
    oof = oof_regression_predictions(lab[feat_cols], lab.target_delta.values, lab.candidate_site_id.values,
                                     max(int(reg_rounds * 1.1), 50), rp, cfg.n_oof_folds)
    _log("final: OOF done, fitting final classifier")
    clf = fit_classifier(_stage2_frame(lab, oof, obs, cfg, feat_cols, inc_m), lab.label_id.values, params=cp,
                         n_estimators=max(int(cls_rounds * 1.1), 30))
    del lab; gc.collect()
    _log("final: classifier fitted")

    data_end = obs["date"].max()
    latest = feats.sort_values("date").groupby("candidate_site_id", sort=False).tail(1).copy()
    age = (data_end - latest["date"]).dt.days
    n_all = len(latest)
    latest = latest[age <= cfg.max_origin_age_days].copy()
    latest["target_date"] = latest["date"] + pd.DateOffset(months=h)
    # "Now" = the latest date in the dataset. A forecast must be about the FUTURE of that date:
    # drop sites whose target date is not after the data end (their last reading is too old to forecast from).
    latest = latest[latest["target_date"] > data_end].copy()
    _log(f"live forecast origins: {len(latest):,} of {n_all:,} sites (origin within {cfg.max_origin_age_days}d of data end "
         f"{data_end.date()} and target date after it)")
    latest["target_group"] = ("ALL" if cfg.region == "maharashtra"
                              else latest["target_date"].dt.month.map(season_map).fillna("UNKNOWN"))
    latest["cur_pct"] = reference_percentile(obs, latest.candidate_site_id.values, latest.date.values,
                                             latest.group_origin.values, latest.cur.values.astype("float64"), cfg.min_reference_obs)
    latest["cur_state"] = state_from_percentile(latest["cur_pct"].values)
    pd_ = reg.predict(latest[feat_cols])
    X2 = _stage2_frame(latest, pd_, obs, cfg, feat_cols, inc_m)
    proba = clf.predict_proba(X2)
    cls_id = proba.argmax(1)

    meta = obs.groupby("candidate_site_id").agg(state=("state", "last"), district=("district", "last"),
                                                unit=("unit", "last")).reset_index()
    out = pd.DataFrame({
        "candidate_site_id": latest.candidate_site_id.values,
        "region": cfg.region,
        "origin_date": latest.date.dt.strftime("%Y-%m-%d").values,
        "origin_water_level": latest.cur.values.astype("float64"),
        "horizon_months": h,
        "target_date": latest.target_date.dt.strftime("%Y-%m-%d").values,
        "predicted_water_level": latest.cur.values.astype("float64") + pd_,
        "predicted_change": pd_.astype("float64"),
        "predicted_lower_80": latest.cur.values.astype("float64") + pd_ + resid_q["q10"],
        "predicted_upper_80": latest.cur.values.astype("float64") + pd_ + resid_q["q90"],
        "predicted_percentile_vs_history": X2["pred_percentile"].values if "pred_percentile" in X2 else X2["pred_pct"].values,
        "current_condition_state": latest.cur_state.values,
        "predicted_condition_state": [CONDITION_ORDER[i] for i in cls_id],
        "predicted_state_confidence": proba.max(1).astype("float64"),
        "telemetry_latest_date": latest.date.dt.strftime("%Y-%m-%d").values,
        "origin_age_days": (data_end - latest.date).dt.days.values,
    })
    for i, c in enumerate(CONDITION_ORDER):
        out[f"prob_{c}"] = proba[:, i].astype("float64")
    out["lat"], out["lon"] = latest.lat.values, latest.lon.values
    out = out.merge(meta, on="candidate_site_id", how="left").rename(columns={"unit": "water_level_unit"})
    out = mask_unclassifiable(out)
    out["model_version"] = FUTURE_FORECAST_VERSION
    out["data_through"] = str(data_end.date())
    out["generated_on"] = str(pd.Timestamp.now().date())   # informational only; forecasts are relative to the data, not the clock
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    reg.save_model(str(MODEL_DIR / f"{cfg.region}_h{h}_regressor.json"))
    clf.save_model(str(MODEL_DIR / f"{cfg.region}_h{h}_classifier.json"))
    return out, {"origins_forecast": int(len(out)), "origins_total_sites": int(n_all),
                 "stale_sites_skipped": int(n_all - len(out)), "data_through": str(data_end.date()),
                 "max_origin_age_days": cfg.max_origin_age_days,
                 "state_not_classified_insufficient_history": int((out.predicted_condition_state == "INSUFFICIENT_HISTORY").sum()),
                 "current_state_distribution": out.current_condition_state.value_counts().to_dict()}


# ----------------------------------------------------------------------------- driver
def run_region(region, horizons, select_metric="r2", do_final=True, max_train_rows=None):
    cfg = CONFIGS[region]
    if max_train_rows is not None:
        cfg.max_train_rows = max_train_rows
    t0 = time.time()
    rp, cp = reg_params_for(cfg), XGBClsParams()
    _log(f"=== {region}: loading observations")
    obs = load_observations(cfg)
    _log(f"{len(obs):,} valid observations, {obs.candidate_site_id.nunique():,} sites, {obs.date.min().date()} -> {obs.date.max().date()}")
    feats = build_features(region, obs)
    feat_cols = feature_columns(region)
    _log(f"features built: {len(feats):,} origins x {len(feat_cols)} features")

    results = {}
    for h in horizons:
        res, pairs = evaluate_horizon(cfg, feats, obs, h, feat_cols, rp)
        results[h] = res
        del pairs   # keep only metrics: pair tables are large (memory); the selected horizon is rebuilt below
        gc.collect()
        if res["feasible"]:
            m = res["test"]["xgboost_regressor"]; b = res["test"]["baseline_persistence"]
            _log(f"h={h}m TEST  MAE={m['mae']:.3f} RMSE={m['rmse']:.3f} R2={m['r2']:.4f} | persistence RMSE={b['rmse']:.3f} R2={b['r2']:.4f}")
        else:
            _log(f"h={h}m NOT FEASIBLE: {res['reason']}")
    sel = select_best_horizon(results, select_metric)
    _log(f"SELECTED horizon: {sel['selected_horizon_months']} month(s) — {sel['reason']}")

    summary = {"version": FUTURE_FORECAST_VERSION, "region": region, "generated_at_utc": datetime.now(timezone.utc).isoformat(),
               "data_through": str(obs.date.max().date()), "n_sites": int(obs.candidate_site_id.nunique()),
               "n_observations_used": int(len(obs)), "water_level_unit": str(obs.unit.mode().iloc[0]),
               "requested_horizons_months": horizons, "selection": sel,
               "horizon_results": {str(h): r for h, r in results.items()},
               "split": {"test_start": cfg.test_start, "val_start": cfg.val_start,
                         "rule": "train targets < val/test start; test origins >= test_start; pairs straddling the boundary are purged"},
               "model_params": {"regressor": rp.__dict__, "classifier": cp.__dict__}}
    h = sel["selected_horizon_months"]
    if h is not None:
        pairs = build_pairs(feats, obs, h, cfg.tolerance_days[h])
        pairs["split"] = assign_split(pairs, cfg).values
        cmetrics, pairs, cls_rounds = run_classification(cfg, pairs, obs, feat_cols, results[h]["n_rounds"], rp, cp)
        summary["classification"] = {"horizon_months": h, **cmetrics}
        a = cmetrics["xgboost_classifier"]; r = cmetrics["baseline_rule_on_regressor_output"]; p = cmetrics["baseline_persistence_state"]
        _log(f"CLASSIFIER TEST acc={a['accuracy']:.3f} macroF1={a['macro_f1']:.3f} | rule acc={r['accuracy']:.3f} | persistence acc={p['accuracy']:.3f}")
        if do_final:
            season_map = season_of_month_map(obs)
            out, info = final_forecast(cfg, obs, feats, pairs, h, feat_cols, results[h]["n_rounds"], cls_rounds, rp, cp,
                                       season_map, results[h]["residual_change_quantiles"], "final")
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            out.to_parquet(OUT_DIR / f"{region}_future_forecast.parquet", index=False)
            summary["forecast_artifact"] = {"file": f"data/future_forecast/{region}_future_forecast.parquet", "horizon_months": h,
                                            **info, "predicted_state_distribution": out.predicted_condition_state.value_counts().to_dict()}
            _log(f"wrote {len(out):,} site forecasts")
    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / f"future_forecast_results_{region}.json").write_text(json.dumps(summary, indent=2, default=float))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{region}_summary.json").write_text(json.dumps(summary, indent=2, default=float))
    _log(f"done in {time.time()-t0:.0f}s")
    return summary


def main():
    ap = argparse.ArgumentParser(description="Multi-horizon XGBoost regression + future-state classification")
    ap.add_argument("--region", choices=["maharashtra", "india", "all"], default="maharashtra")
    ap.add_argument("--horizons", type=int, nargs="+", default=DEFAULT_HORIZONS, help="horizons in months (default 1 6 12)")
    ap.add_argument("--select-metric", choices=["r2", "rmse", "mae", "r2_change"], default="r2")
    ap.add_argument("--no-final", action="store_true", help="skip final refit + live forecast artifact")
    ap.add_argument("--max-train-rows", type=int, default=None)
    a = ap.parse_args()
    for r in (["maharashtra", "india"] if a.region == "all" else [a.region]):
        run_region(r, sorted(a.horizons), a.select_metric, not a.no_final, a.max_train_rows)


if __name__ == "__main__":
    main()
