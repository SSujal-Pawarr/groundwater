import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
import sys
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from models.evaluation import evaluate_forecast, compare_models

def main():
    # 1. Load Data
    data_path = PROJECT_ROOT / "data" / "features" / "maharashtra" / "maharashtra_weather_ml_ready.parquet"
    print(f"Loading data from {data_path}...")
    df = pd.read_parquet(data_path)

    # 2. Feature Engineering (GW)
    print("Generating features...")
    df = df.sort_values(["candidate_site_id", "observation_timestamp_utc"]).reset_index(drop=True)
    df["lag_1"] = df.groupby("candidate_site_id")["water_level_raw"].shift(1)
    df["hour"] = pd.to_datetime(df["observation_timestamp_utc"]).dt.hour

    # 3. Clean nulls
    # Drop first observation per site which lacks lag_1
    df = df.dropna(subset=["lag_1", "target_water_level"])

    # 4. Strict Chronological Split
    print("Applying target-isolated chronological split...")
    df["obs_dt"] = pd.to_datetime(df["observation_timestamp_utc"], utc=True)
    df["target_dt"] = pd.to_datetime(df["target_timestamp_utc"], utc=True)

    t_train = pd.to_datetime("2026-04-05 06:30:00", utc=True)
    t_val = pd.to_datetime("2026-04-27 06:30:00", utc=True)

    # Train: obs_dt <= t_train AND target_dt <= t_train
    train_mask = (df["obs_dt"] <= t_train) & (df["target_dt"] <= t_train)

    # Val: obs_dt > t_train AND obs_dt <= t_val AND target_dt <= t_val
    val_mask = (df["obs_dt"] > t_train) & (df["obs_dt"] <= t_val) & (df["target_dt"] <= t_val)

    # Test: obs_dt > t_val
    test_mask = (df["obs_dt"] > t_val)

    train_df = df[train_mask].copy()
    val_df = df[val_mask].copy()
    test_df = df[test_mask].copy()

    print(f"Train: {len(train_df)}")
    print(f"Val: {len(val_df)}")
    print(f"Test: {len(test_df)}")

    # 5. Features
    features = [
        "water_level_raw", "lag_1", "hour",
        "precip_sum_24h", "precip_sum_3d", "precip_sum_7d", "precip_sum_14d", "precip_sum_30d",
        "et0_sum_24h", "et0_sum_7d", "et0_sum_30d"
    ]
    
    print(f"Using features: {features}")

    X_train = train_df[features]
    y_train = train_df["target_water_level"]

    X_test = test_df[features]
    y_test = test_df["target_water_level"]

    results = []

    # Model A: Persistence
    test_df["pred_persistence"] = test_df["water_level_raw"]
    res_pers = evaluate_forecast(y_test.values, test_df["pred_persistence"].values, "Persistence")
    results.append(res_pers)

    # Model B: HistGradientBoostingRegressor
    print("Training HistGradientBoosting...")
    model_hgb = HistGradientBoostingRegressor(random_state=42)
    model_hgb.fit(X_train, y_train)
    test_df["pred_hgb"] = model_hgb.predict(X_test)
    res_hgb = evaluate_forecast(y_test.values, test_df["pred_hgb"].values, "HGB (GW+Precip+ET0)")
    results.append(res_hgb)

    # Model C: XGBoost
    print("Training XGBoost...")
    model_xgb = XGBRegressor(random_state=42, n_estimators=100, max_depth=6, learning_rate=0.1)
    model_xgb.fit(X_train, y_train)
    test_df["pred_xgb"] = model_xgb.predict(X_test)
    res_xgb = evaluate_forecast(y_test.values, test_df["pred_xgb"].values, "M9 XGBoost")
    results.append(res_xgb)

    print("\n--- Overall Test Set Performance ---")
    print(compare_models(results).to_string())

    # 6. Horizon Analysis
    print("\n--- Horizon Analysis (XGBoost vs Persistence) ---")
    horizons = [
        ("<= 6h", test_df["time_delta_hours"] <= 6),
        (">6h to <= 24h", (test_df["time_delta_hours"] > 6) & (test_df["time_delta_hours"] <= 24)),
        (">24h to <= 48h", (test_df["time_delta_hours"] > 24) & (test_df["time_delta_hours"] <= 48)),
        ("> 48h", test_df["time_delta_hours"] > 48)
    ]

    for name, mask in horizons:
        subset = test_df[mask]
        if len(subset) == 0:
            continue
        print(f"\nHorizon: {name} (N={len(subset)})")
        sub_res = [
            evaluate_forecast(subset["target_water_level"].values, subset["pred_persistence"].values, "Persistence"),
            evaluate_forecast(subset["target_water_level"].values, subset["pred_hgb"].values, "HGB"),
            evaluate_forecast(subset["target_water_level"].values, subset["pred_xgb"].values, "M9 XGBoost")
        ]
        print(compare_models(sub_res).to_string())

    # 7. Extreme-Error Audit for XGBoost
    print("\n--- Extreme-Error Audit (XGBoost) ---")
    test_df["error_xgb_abs"] = (test_df["target_water_level"] - test_df["pred_xgb"]).abs()
    max_err = test_df["error_xgb_abs"].max()
    err_gt_10 = (test_df["error_xgb_abs"] > 10).sum()
    print(f"Max Absolute Error: {max_err:.2f} m")
    print(f"Errors > 10m: {err_gt_10}")

    mask_clean = test_df["error_xgb_abs"] <= 10
    rmse_clean = np.sqrt(((test_df.loc[mask_clean, "target_water_level"] - test_df.loc[mask_clean, "pred_xgb"])**2).mean())
    print(f"RMSE excluding >10m errors: {rmse_clean:.2f} m")

if __name__ == "__main__":
    main()
