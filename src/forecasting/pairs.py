"""Origin -> target pair construction, chronological splitting and future-state labels."""
from __future__ import annotations
import numpy as np
import pandas as pd
from .config import DatasetConfig, CONDITION_ORDER, CLASS_TO_ID
from .features import reference_percentile


def state_from_percentile(p: np.ndarray) -> np.ndarray:
    """Same thresholds/names as src.features.conditions._assign_condition_state (P10/P25/P75/P90)."""
    p = np.asarray(p, dtype="float64")
    out = np.full(len(p), "INSUFFICIENT_HISTORY", dtype=object)
    ok = ~np.isnan(p)
    out[ok & (p < 10)] = "EXTREMELY_LOW"
    out[ok & (p >= 10) & (p < 25)] = "LOW"
    out[ok & (p >= 25) & (p <= 75)] = "NORMAL_RANGE"
    out[ok & (p > 75) & (p <= 90)] = "HIGH"
    out[ok & (p > 90)] = "EXTREMELY_HIGH"
    return out


def state_to_id(states: np.ndarray) -> np.ndarray:
    return np.array([CLASS_TO_ID.get(s, -1) for s in states], dtype="int64")


def build_pairs(feats: pd.DataFrame, obs: pd.DataFrame, h_months: int, tol_days: int) -> pd.DataFrame:
    """Match each origin to the real observation closest to origin + h calendar months (within tolerance)."""
    left = feats[["candidate_site_id", "date"]].copy()
    left["_i"] = np.arange(len(left))
    left["nominal"] = left["date"] + pd.DateOffset(months=h_months)
    left = left.sort_values("nominal")
    right = obs[["candidate_site_id", "date", "value", "group"]].rename(
        columns={"date": "target_date", "value": "target_value", "group": "target_group"}).sort_values("target_date")
    m = pd.merge_asof(left, right, left_on="nominal", right_on="target_date", by="candidate_site_id",
                      tolerance=pd.Timedelta(days=tol_days), direction="nearest")
    m = m.dropna(subset=["target_date"])
    # never let a pair "see" a target that is really just the origin / a too-near observation
    gap = (m["target_date"] - m["date"]).dt.days
    m = m[gap >= int(15 * h_months)]
    pairs = feats.iloc[m["_i"].values].reset_index(drop=True)
    pairs["target_date"] = m["target_date"].values
    pairs["target_value"] = m["target_value"].values.astype("float64")
    pairs["target_group"] = m["target_group"].values
    pairs["target_delta"] = pairs["target_value"] - pairs["cur"].astype("float64")
    return pairs


def assign_split(pairs: pd.DataFrame, cfg: DatasetConfig) -> pd.Series:
    test_start = pd.Timestamp(cfg.test_start)
    val_start = pd.Timestamp(cfg.val_start) if cfg.val_start else None
    split = pd.Series("purged", index=pairs.index, dtype=object)
    train_end = val_start if val_start is not None else test_start
    split[pairs["target_date"] < train_end] = "train"
    if val_start is not None:
        split[(pairs["date"] >= val_start) & (pairs["target_date"] < test_start)] = "val"
    split[pairs["date"] >= test_start] = "test"
    return split


def add_future_labels(pairs: pd.DataFrame, obs: pd.DataFrame, cfg: DatasetConfig) -> pd.DataFrame:
    """
    label_pct   : percentile of the ACTUAL target value vs the site's history known at the origin
                  (same-season history for India, all history for Maharashtra).
    cur_pct     : same, for the current value.
    """
    mr = cfg.min_reference_obs
    pairs["label_pct"] = reference_percentile(obs, pairs["candidate_site_id"].values, pairs["date"].values,
                                              pairs["target_group"].values, pairs["target_value"].values, mr)
    pairs["cur_pct"] = reference_percentile(obs, pairs["candidate_site_id"].values, pairs["date"].values,
                                            pairs["group_origin"].values, pairs["cur"].values, mr)
    pairs["label_state"] = state_from_percentile(pairs["label_pct"].values)
    pairs["cur_state"] = state_from_percentile(pairs["cur_pct"].values)
    pairs["label_id"] = state_to_id(pairs["label_state"].values)
    return pairs
