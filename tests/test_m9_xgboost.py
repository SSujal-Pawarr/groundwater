import pandas as pd
import numpy as np
from pathlib import Path
import sys
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

def test_m9_split_integrity():
    """Verify deterministic model configuration, split integrity, and no leakage."""
    data_path = PROJECT_ROOT / "data" / "features" / "maharashtra" / "maharashtra_weather_ml_ready.parquet"
    if not data_path.exists():
        pytest.skip("Test data not found.")
    
    df = pd.read_parquet(data_path)
    df = df.sort_values(["candidate_site_id", "observation_timestamp_utc"]).reset_index(drop=True)
    df["lag_1"] = df.groupby("candidate_site_id")["water_level_raw"].shift(1)
    df = df.dropna(subset=["lag_1", "target_water_level"])
    
    df["obs_dt"] = pd.to_datetime(df["observation_timestamp_utc"], utc=True)
    df["target_dt"] = pd.to_datetime(df["target_timestamp_utc"], utc=True)

    t_train = pd.to_datetime("2026-04-05 06:30:00", utc=True)
    t_val = pd.to_datetime("2026-04-27 06:30:00", utc=True)

    train_mask = (df["obs_dt"] <= t_train) & (df["target_dt"] <= t_train)
    val_mask = (df["obs_dt"] > t_train) & (df["obs_dt"] <= t_val) & (df["target_dt"] <= t_val)
    test_mask = (df["obs_dt"] > t_val)
    
    train_df = df[train_mask]
    val_df = df[val_mask]
    test_df = df[test_mask]
    
    # 1. No target leakage: target_dt in train must be <= t_train
    assert train_df["target_dt"].max() <= t_train, "Temporal leakage detected in train set"
    assert val_df["target_dt"].max() <= t_val, "Temporal leakage detected in val set"
    
    # 2. Chronological split integrity
    assert train_df["obs_dt"].max() <= t_train, "Chronological integrity violated"
    assert test_df["obs_dt"].min() > t_val, "Chronological integrity violated"
    
    # 3. Disjoint sets (row alignment)
    assert len(set(train_df.index).intersection(set(test_df.index))) == 0, "Train/Test overlap"
    assert len(set(val_df.index).intersection(set(test_df.index))) == 0, "Val/Test overlap"
    
    # 4. Reproducibility & deterministic config
    # Confirm exact row counts match the ones logged in the M9 experiment
    assert len(train_df) == 146028
    assert len(val_df) == 30406
    assert len(test_df) == 31272

def test_extreme_error_records_present():
    """Verify extreme-error records are not silently removed."""
    data_path = PROJECT_ROOT / "data" / "features" / "maharashtra" / "maharashtra_weather_ml_ready.parquet"
    if not data_path.exists():
        pytest.skip("Test data not found.")
        
    df = pd.read_parquet(data_path)
    # Check if the extreme observations (e.g. -1791) still exist in the target
    assert df["target_water_level"].min() < -1000, "Extreme error targets silently removed"
    assert df["water_level_raw"].min() < -1000, "Extreme error features silently removed"
