from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "future_forecast"
MODEL_DIR = ROOT / "models" / "future_forecast"
DOCS_DIR = ROOT / "docs"

CONDITION_ORDER = ["EXTREMELY_LOW", "LOW", "NORMAL_RANGE", "HIGH", "EXTREMELY_HIGH"]
CLASS_TO_ID = {c: i for i, c in enumerate(CONDITION_ORDER)}

DEFAULT_HORIZONS = [1, 6]   # Compare 1-month vs 6-month; best accuracy wins (sir's requirement)


@dataclass
class DatasetConfig:
    region: str
    # Candidate source files, first existing one wins (processed first, alerts as fallback).
    source_files: List[str]
    time_col: str
    unit_default: str
    # Calendar tolerance (days) used to match "origin + h months" to a real observation.
    tolerance_days: Dict[int, int]
    # Chronological split. Train pairs need target_date < val_start (or test_start if no val).
    test_start: str
    val_start: Optional[str]
    # Minimum pairs for a horizon to be called feasible.
    min_train_pairs: int
    min_test_pairs: int
    # Min prior observations required to define a percentile / condition state.
    min_reference_obs: int
    # Latest origin must be at most this old (vs dataset end) to issue a live forecast.
    max_origin_age_days: int
    # Cap on training rows (1-CPU friendly); None = no cap.
    max_train_rows: Optional[int]
    n_oof_folds: int


MAHARASHTRA = DatasetConfig(
    region="maharashtra",
    source_files=["data/processed/maharashtra/maharashtra_normalized.parquet", "data/alerts/maharashtra_alerts.parquet"],
    time_col="observation_timestamp",
    unit_default="meters",
    tolerance_days={1: 7, 6: 15, 12: 15},
    test_start="2026-04-01",
    val_start=None,
    min_train_pairs=2000,
    min_test_pairs=1000,
    min_reference_obs=14,
    max_origin_age_days=7,
    max_train_rows=None,
    n_oof_folds=5,
)

INDIA = DatasetConfig(
    region="india",
    source_files=["data/processed/india/india_normalized.parquet", "data/alerts/india_alerts.parquet"],
    time_col="observation_date",
    unit_default="unknown",
    tolerance_days={1: 7, 6: 45, 12: 45},
    test_start="2020-01-01",
    val_start="2017-01-01",
    min_train_pairs=5000,
    min_test_pairs=2000,
    min_reference_obs=5,
    max_origin_age_days=180,
    max_train_rows=350_000,
    n_oof_folds=4,
)

CONFIGS = {"maharashtra": MAHARASHTRA, "india": INDIA}


@dataclass
class XGBRegParams:
    n_estimators: int = 400
    learning_rate: float = 0.05
    max_depth: int = 6
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    min_child_weight: float = 5.0
    reg_lambda: float = 2.0
    early_stopping_rounds: int = 30
    random_state: int = 42
    objective: str = "reg:squarederror"   # or reg:pseudohubererror (robust to heavy-tailed monthly jumps)
    huber_slope: float = 1.0


@dataclass
class XGBClsParams:
    n_estimators: int = 250
    learning_rate: float = 0.08
    max_depth: int = 5
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    min_child_weight: float = 3.0
    reg_lambda: float = 2.0
    early_stopping_rounds: int = 25
    random_state: int = 42
