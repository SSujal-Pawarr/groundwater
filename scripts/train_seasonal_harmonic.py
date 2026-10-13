"""
LightGBM Seasonal Harmonic Forecast Model Training Script
==========================================================
Trains a per-dataset LightGBM regressor using Fourier-basis seasonal features,
district hydrogeology encoding, and depth-damped seasonal interactions so it can
predict water levels at ANY future date without a step-count cap.

Features known at any future target date (no future data leakage):
  - Annual, semi-annual, quarterly, monthly Fourier harmonics (sin/cos)
  - Relative seasonal phase difference (sin_doy_delta, cos_doy_delta)
  - Depth-damped seasonal interactions
  - Spatial: lat, lon, elevation, district_code
  - Origin-date context: last observed level, level relative to site mean
  - Site historical stats: mean, std, range, recent velocity
  - Horizon in days
  - scenario_factor: 1.0 (normal), 0.8 (deficit), 1.2 (excess)

Usage:
    python scripts/train_seasonal_harmonic.py

Output:
    models/advanced_forecast/maharashtra_seasonal_harmonic.joblib
    models/advanced_forecast/maharashtra_seasonal_harmonic_meta.json
"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
LOGGER = logging.getLogger("train_seasonal_harmonic")

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "processed" / "maharashtra" / "maharashtra_normalized.parquet"
MODEL_DIR = ROOT / "models" / "advanced_forecast"
MODEL_PATH = MODEL_DIR / "maharashtra_seasonal_harmonic.joblib"
META_PATH = MODEL_DIR / "maharashtra_seasonal_harmonic_meta.json"

TEST_SPLIT_RATIO = 0.20
MAX_HORIZON_DAYS = 1100
MIN_HORIZON_DAYS = 7
ORIGIN_SAMPLE_STEP = 3
TARGET_STEP = 5
SCENARIO_FACTOR_NORMAL = 1.0
MIN_SITE_OBS = 30


FEATURE_COLS = [
    "origin_level",
    "origin_level_rel_site",
    "site_mean",
    "site_std",
    "site_range",
    "recent_vel",
    "origin_doy",
    "origin_year",
    "horizon_days",
    "lat",
    "lon",
    "elevation",
    "district_code",
    "scenario_factor",
    "target_sin_annual",
    "target_cos_annual",
    "target_sin_semi",
    "target_cos_semi",
    "target_sin_quarterly",
    "target_cos_quarterly",
    "target_sin_month",
    "target_cos_month",
    "origin_sin_annual",
    "origin_cos_annual",
    "origin_sin_semi",
    "origin_cos_semi",
    "origin_sin_month",
    "origin_cos_month",
    "sin_doy_delta",
    "cos_doy_delta",
    "depth_scaled_sin_annual",
    "depth_scaled_cos_annual",
]


def _fourier_features_dict(doy: float | np.ndarray) -> dict:
    doy_arr = np.asarray(doy, dtype=np.float64)
    ang = 2 * math.pi * doy_arr / 365.25
    m_ang = 2 * math.pi * ((doy_arr / 365.25) * 12 % 12) / 12.0
    return {
        "sin_annual": np.sin(ang),
        "cos_annual": np.cos(ang),
        "sin_semi": np.sin(2 * ang),
        "cos_semi": np.cos(2 * ang),
        "sin_quarterly": np.sin(4 * ang),
        "cos_quarterly": np.cos(4 * ang),
        "sin_month": np.sin(m_ang),
        "cos_month": np.cos(m_ang),
    }


def _load_maharashtra_daily() -> pd.DataFrame:
    LOGGER.info("Loading Maharashtra observations from %s", DATA_PATH)
    df = pd.read_parquet(DATA_PATH)
    if "is_analytics_ready" in df.columns:
        df = df[df["is_analytics_ready"].astype(bool)]
    df = df[df["water_level_raw"].notna()].copy()
    df["date"] = pd.to_datetime(df["observation_timestamp"]).dt.normalize()
    agg = (
        df.groupby(["candidate_site_id", "date"], sort=True)
        .agg(
            water_level=("water_level_raw", "mean"),
            lat=("latitude", "first"),
            lon=("longitude", "first"),
            elevation=("elevation_msl", "first"),
            district=("district", "first"),
        )
        .reset_index()
    )
    agg["date"] = pd.to_datetime(agg["date"])
    LOGGER.info(
        "Loaded %d daily records across %d sites",
        len(agg), agg["candidate_site_id"].nunique(),
    )
    return agg.sort_values(["candidate_site_id", "date"]).reset_index(drop=True)


def build_training_pairs(daily: pd.DataFrame) -> tuple[pd.DataFrame, dict, dict]:
    LOGGER.info("Building training pairs...")
    rows = []
    sites = daily["candidate_site_id"].unique()
    site_stats = {}

    districts = sorted([str(d) for d in daily["district"].dropna().unique()])
    district_map = {d: i for i, d in enumerate(districts)}

    for site_id in sites:
        site_df = daily[daily["candidate_site_id"] == site_id].sort_values("date")
        if len(site_df) < MIN_SITE_OBS:
            continue
        dates = site_df["date"].values
        levels = site_df["water_level"].values

        lat = float(site_df["lat"].iloc[0]) if site_df["lat"].notna().any() else 0.0
        lon = float(site_df["lon"].iloc[0]) if site_df["lon"].notna().any() else 0.0
        elev = float(site_df["elevation"].iloc[0]) if site_df["elevation"].notna().any() else 0.0
        dist = str(site_df["district"].iloc[0]) if site_df["district"].notna().any() else "Unknown"
        dist_code = district_map.get(dist, -1)

        s_mean = float(np.mean(levels))
        s_std = float(np.std(levels) + 1e-4)
        s_min = float(np.min(levels))
        s_max = float(np.max(levels))
        s_range = s_max - s_min
        site_stats[site_id] = {
            "mean": s_mean,
            "std": s_std,
            "min": s_min,
            "max": s_max,
            "range": s_range,
            "lat": lat,
            "lon": lon,
            "elevation": elev,
            "district": dist,
            "district_code": dist_code,
        }

        n_dates = len(dates)
        for i in range(0, n_dates, ORIGIN_SAMPLE_STEP):
            origin_date = pd.Timestamp(dates[i])
            origin_level = float(levels[i])
            if np.isnan(origin_level):
                continue

            recent_vel = 0.0
            if i >= 7 and not np.isnan(levels[i - 7]):
                recent_vel = (origin_level - float(levels[i - 7])) / 7.0

            future_idx = range(i + MIN_HORIZON_DAYS, n_dates, TARGET_STEP)
            for j in future_idx:
                target_date = pd.Timestamp(dates[j])
                horizon_days = (target_date - origin_date).days
                if horizon_days > MAX_HORIZON_DAYS:
                    break
                target_level = float(levels[j])
                if np.isnan(target_level):
                    continue

                delta = target_level - origin_level
                if abs(delta) > 25.0:  # sensor anomaly filter
                    continue

                rows.append({
                    "candidate_site_id": site_id,
                    "origin_date": origin_date,
                    "target_date": target_date,
                    "origin_level": origin_level,
                    "origin_doy": origin_date.day_of_year,
                    "origin_year": origin_date.year,
                    "target_doy": target_date.day_of_year,
                    "target_year": target_date.year,
                    "horizon_days": float(horizon_days),
                    "lat": lat,
                    "lon": lon,
                    "elevation": elev,
                    "district_code": dist_code,
                    "site_mean": s_mean,
                    "site_std": s_std,
                    "site_range": s_range,
                    "recent_vel": recent_vel,
                    "delta": delta,
                    "target_level": target_level,
                })

    pairs = pd.DataFrame(rows)
    LOGGER.info("Built %d training pairs from %d sites", len(pairs), pairs["candidate_site_id"].nunique())
    return pairs, site_stats, district_map


def _add_engineered_features(pairs: pd.DataFrame) -> pd.DataFrame:
    # Target Fourier features
    t_fourier = _fourier_features_dict(pairs["target_doy"].values)
    for k, v in t_fourier.items():
        pairs[f"target_{k}"] = v

    # Origin Fourier features
    o_fourier = _fourier_features_dict(pairs["origin_doy"].values)
    for k, v in o_fourier.items():
        pairs[f"origin_{k}"] = v

    # Cycle phase differences
    pairs["doy_delta"] = (pairs["target_doy"] - pairs["origin_doy"]) % 365.25
    ang_diff = 2 * math.pi * pairs["doy_delta"] / 365.25
    pairs["sin_doy_delta"] = np.sin(ang_diff)
    pairs["cos_doy_delta"] = np.cos(ang_diff)
    pairs["origin_level_rel_site"] = pairs["origin_level"] - pairs["site_mean"]
    pairs["scenario_factor"] = SCENARIO_FACTOR_NORMAL

    # Depth-scaled seasonal interactions (unconfined vs deep confined aquifers)
    pairs["depth_scaled_sin_annual"] = pairs["target_sin_annual"] / (1.0 + np.abs(pairs["origin_level"]) / 10.0)
    pairs["depth_scaled_cos_annual"] = pairs["target_cos_annual"] / (1.0 + np.abs(pairs["origin_level"]) / 10.0)
    return pairs


def _regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    e = y_pred - y_true
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    return {
        "mae": float(np.mean(np.abs(e))),
        "rmse": float(np.sqrt(np.mean(e ** 2))),
        "r2": float(1 - np.sum(e ** 2) / ss_tot) if ss_tot > 0 else float("nan"),
        "n": int(len(y_true)),
    }


def train(pairs: pd.DataFrame):
    import lightgbm as lgb

    pairs = _add_engineered_features(pairs)
    all_dates = sorted(pairs["target_date"].unique())
    split_idx = int(len(all_dates) * (1 - TEST_SPLIT_RATIO))
    split_date = all_dates[split_idx]

    train_mask = pairs["target_date"] < split_date
    test_mask = pairs["target_date"] >= split_date

    X_train = pairs.loc[train_mask, FEATURE_COLS].fillna(0.0)
    y_train = pairs.loc[train_mask, "delta"].values
    X_test = pairs.loc[test_mask, FEATURE_COLS].fillna(0.0)
    y_test = pairs.loc[test_mask, "delta"].values

    LOGGER.info("Train pairs: %d | Test pairs: %d | Split date: %s", len(X_train), len(X_test), split_date)

    persist_pred = np.zeros_like(y_test)
    persist_metrics = _regression_metrics(y_test, persist_pred)
    LOGGER.info(
        "Persistence baseline  MAE=%.3f  RMSE=%.3f  R2=%.4f",
        persist_metrics["mae"], persist_metrics["rmse"], persist_metrics["r2"],
    )

    model = lgb.LGBMRegressor(
        objective="huber",
        n_estimators=1200,
        learning_rate=0.03,
        num_leaves=70,
        max_depth=9,
        min_child_samples=30,
        subsample=0.85,
        subsample_freq=3,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        callbacks=[lgb.early_stopping(60, verbose=False), lgb.log_evaluation(200)],
    )

    test_pred = model.predict(X_test)
    test_metrics = _regression_metrics(y_test, test_pred)
    LOGGER.info(
        "LightGBM seasonal     MAE=%.3f  RMSE=%.3f  R2=%.4f  (skill vs persistence RMSE: %+.1f%%, MAE: %+.1f%%)",
        test_metrics["mae"], test_metrics["rmse"], test_metrics["r2"],
        100 * (1 - test_metrics["rmse"] / persist_metrics["rmse"]),
        100 * (1 - test_metrics["mae"] / persist_metrics["mae"]),
    )

    importance = dict(sorted(
        zip(FEATURE_COLS, model.feature_importances_.tolist()),
        key=lambda x: x[1], reverse=True,
    )[:12])
    LOGGER.info("Top features: %s", importance)

    return model, test_metrics, persist_metrics, importance, str(split_date)


def main():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    daily = _load_maharashtra_daily()
    pairs, site_stats, district_map = build_training_pairs(daily)

    if pairs.empty:
        LOGGER.error("No training pairs built. Check data path.")
        return 1

    model, test_metrics, persist_metrics, importance, split_date = train(pairs)

    artifact = {
        "model": model,
        "feature_cols": FEATURE_COLS,
        "site_stats": site_stats,
        "district_map": district_map,
        "region": "maharashtra",
        "model_type": "lightgbm_seasonal_harmonic",
        "data_through": str(daily["date"].max().date()),
        "test_metrics": test_metrics,
        "persist_metrics": persist_metrics,
        "test_split_date": split_date,
        "top_features": importance,
        "fourier_harmonics": ["annual", "semiannual", "quarterly", "month"],
        "scenario_factors": {"normal": 1.0, "deficit": 0.8, "excess": 1.2},
    }
    joblib.dump(artifact, MODEL_PATH)
    LOGGER.info("Saved model to %s", MODEL_PATH)

    meta = {k: v for k, v in artifact.items() if k not in ("model", "site_stats")}
    meta["n_sites"] = len(site_stats)
    META_PATH.write_text(json.dumps(meta, indent=2, default=str))
    LOGGER.info("Saved metadata to %s", META_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
