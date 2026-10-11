"""XGBoost regressor / classifier wrappers, baselines and metrics."""
from __future__ import annotations
from dataclasses import asdict
from typing import Dict, Optional, Sequence
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score)
from sklearn.model_selection import GroupKFold
from .config import XGBRegParams, XGBClsParams, CONDITION_ORDER


# ------------------------------------------------------------------ regression
def fit_regressor(X: pd.DataFrame, y: np.ndarray, Xv: Optional[pd.DataFrame] = None, yv: Optional[np.ndarray] = None,
                  params: XGBRegParams = XGBRegParams(), n_estimators: Optional[int] = None):
    kw = dict(n_estimators=n_estimators or params.n_estimators, learning_rate=params.learning_rate,
              max_depth=params.max_depth, subsample=params.subsample, colsample_bytree=params.colsample_bytree,
              min_child_weight=params.min_child_weight, reg_lambda=params.reg_lambda,
              tree_method="hist", random_state=params.random_state, n_jobs=-1, objective=params.objective)
    if params.objective == "reg:pseudohubererror":
        kw["huber_slope"] = params.huber_slope
    if Xv is not None and len(Xv) > 0 and n_estimators is None:
        model = xgb.XGBRegressor(early_stopping_rounds=params.early_stopping_rounds, **kw)
        model.fit(X, y, eval_set=[(Xv, yv)], verbose=False)
    else:
        model = xgb.XGBRegressor(**kw)
        model.fit(X, y, verbose=False)
    return model


def used_rounds(model) -> int:
    bi = getattr(model, "best_iteration", None)
    return int(bi) + 1 if bi is not None else int(model.get_params()["n_estimators"])


def regression_metrics(actual: np.ndarray, pred: np.ndarray, cur: np.ndarray) -> Dict[str, float]:
    err = pred - actual
    mae, rmse = float(np.mean(np.abs(err))), float(np.sqrt(np.mean(err ** 2)))
    ss_res, ss_tot = float(np.sum(err ** 2)), float(np.sum((actual - actual.mean()) ** 2))
    d_act, d_pred = actual - cur, pred - cur
    ss_res_d, ss_tot_d = float(np.sum((d_act - d_pred) ** 2)), float(np.sum((d_act - d_act.mean()) ** 2))
    return {"n": int(len(actual)), "mae": mae, "rmse": rmse,
            "r2": 1 - ss_res / ss_tot if ss_tot > 0 else float("nan"),
            "r2_change": 1 - ss_res_d / ss_tot_d if ss_tot_d > 0 else float("nan"),
            "bias": float(np.mean(err))}


def evaluate_regression(actual, pred, cur, train_median_delta: float) -> Dict[str, Dict[str, float]]:
    model = regression_metrics(actual, pred, cur)
    persistence = regression_metrics(actual, cur, cur)
    median_delta = regression_metrics(actual, cur + train_median_delta, cur)
    model["skill_rmse_vs_persistence"] = 1 - model["rmse"] / persistence["rmse"] if persistence["rmse"] > 0 else float("nan")
    model["skill_mae_vs_persistence"] = 1 - model["mae"] / persistence["mae"] if persistence["mae"] > 0 else float("nan")
    model["beats_persistence"] = bool(model["rmse"] < persistence["rmse"] and model["mae"] < persistence["mae"])
    return {"xgboost_regressor": model, "baseline_persistence": persistence, "baseline_median_change": median_delta}


# ------------------------------------------------------------------ classification
def oof_regression_predictions(X: pd.DataFrame, y: np.ndarray, groups: np.ndarray, n_rounds: int,
                               params: XGBRegParams, n_folds: int) -> np.ndarray:
    """Out-of-fold regressor output so the classifier never trains on in-sample (overfit) predictions."""
    oof = np.full(len(X), np.nan)
    gkf = GroupKFold(n_splits=n_folds)
    for tr, te in gkf.split(X, y, groups):
        m = fit_regressor(X.iloc[tr], y[tr], params=params, n_estimators=n_rounds)
        oof[te] = m.predict(X.iloc[te])
    return oof


def fit_classifier(X: pd.DataFrame, y: np.ndarray, Xv: Optional[pd.DataFrame] = None, yv: Optional[np.ndarray] = None,
                   params: XGBClsParams = XGBClsParams(), n_estimators: Optional[int] = None):
    kw = dict(n_estimators=n_estimators or params.n_estimators, learning_rate=params.learning_rate,
              max_depth=params.max_depth, subsample=params.subsample, colsample_bytree=params.colsample_bytree,
              min_child_weight=params.min_child_weight, reg_lambda=params.reg_lambda, tree_method="hist",
              random_state=params.random_state, n_jobs=-1, objective="multi:softprob", num_class=len(CONDITION_ORDER),
              eval_metric="mlogloss")
    if Xv is not None and len(Xv) > 0 and n_estimators is None:
        model = xgb.XGBClassifier(early_stopping_rounds=params.early_stopping_rounds, **kw)
        model.fit(X, y, eval_set=[(Xv, yv)], verbose=False)
    else:
        model = xgb.XGBClassifier(**kw)
        model.fit(X, y, verbose=False)
    return model


def classification_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
    labels = list(range(len(CONDITION_ORDER)))
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    f1_each = f1_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    return {
        "n": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)),
        "ordinal_mae_classes": float(np.mean(np.abs(y_true - y_pred))),
        "within_one_class": float(np.mean(np.abs(y_true - y_pred) <= 1)),
        "per_class_f1": {c: float(f) for c, f in zip(CONDITION_ORDER, f1_each)},
        "support": {c: int((y_true == i).sum()) for i, c in enumerate(CONDITION_ORDER)},
        "confusion_matrix_rows_true_cols_pred": cm.tolist(),
    }
