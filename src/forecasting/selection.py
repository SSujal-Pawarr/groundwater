"""Horizon selection: keep the horizon whose regressor is the most accurate on held-out data."""
from __future__ import annotations
from typing import Dict, Optional

HIGHER_IS_BETTER = {"r2": True, "r2_change": True, "rmse": False, "mae": False}


def select_best_horizon(results: Dict[int, dict], metric: str = "r2") -> Dict:
    """
    results[h] = {"feasible": bool, "test": {"xgboost_regressor": {...metrics...}}, ...}

    Sir's rule (as specified):
      - Evaluate XGBoost Regressor accuracy for 1-month AND 6-month ahead.
      - If accuracy(1 month) > accuracy(6 months)  → use 1 month  (Ex 2 from sir)
      - If accuracy(1 month) < accuracy(6 months)  → use 6 months (Ex 1 from sir)
      - The classifier (XGBoost Classifier) then runs on top of the WINNING regressor output.
      - Ties break to the SHORTER horizon (prefer more frequent forecast if equal).

    Generalised to any set of feasible horizons — best metric on held-out test set wins.
    """
    if metric not in HIGHER_IS_BETTER:
        raise ValueError(f"Unknown selection metric {metric}")
    feasible = {h: r for h, r in results.items() if r.get("feasible")}
    if not feasible:
        return {"selected_horizon_months": None, "metric": metric, "reason": "No feasible horizon for this dataset.",
                "ranking": []}
    ranking = []
    for h, r in feasible.items():
        ranking.append({"horizon_months": h, metric: r["test"]["xgboost_regressor"][metric]})
    sign = 1 if HIGHER_IS_BETTER[metric] else -1
    ranking.sort(key=lambda x: (-sign * x[metric], x["horizon_months"]))
    best = ranking[0]
    if len(ranking) == 1:
        reason = (f"Only {best['horizon_months']}-month horizon is feasible with the available data coverage, "
                  f"so it is selected by default.")
    else:
        others = ", ".join(f"{x['horizon_months']}m {metric}={x[metric]:.4f}" for x in ranking[1:])
        reason = (
            f"Sir's rule applied — {best['horizon_months']}-month horizon wins: "
            f"{metric}={best[metric]:.4f} (best) vs {others}. "
            f"XGBoost Regressor predicts the water level {best['horizon_months']} month(s) ahead; "
            f"XGBoost Classifier then classifies the future condition state from that prediction."
        )
    return {"selected_horizon_months": best["horizon_months"], "metric": metric, "reason": reason, "ranking": ranking}

