"""
Evaluation metrics for groundwater forecasting models.
"""
from typing import Dict, Any, List
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, median_absolute_error

def evaluate_forecast(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    model_name: str = "model"
) -> Dict[str, Any]:
    """
    Computes standard evaluation metrics for forecasting regression.
    
    Parameters
    ----------
    y_true : np.ndarray
        True target values.
    y_pred : np.ndarray
        Predicted values.
    model_name : str
        Name of the model.
        
    Returns
    -------
    Dict[str, Any]
        Dictionary of metrics.
    """
    # Remove NaNs from both if they exist (though forecasts shouldn't have NaNs)
    mask = ~np.isnan(y_true) & ~np.isnan(y_pred)
    y_true_clean = y_true[mask]
    y_pred_clean = y_pred[mask]
    
    if len(y_true_clean) == 0:
        return {
            "model": model_name,
            "samples": 0,
            "mae": None,
            "rmse": None,
            "r2": None,
            "median_ae": None
        }
        
    mae = mean_absolute_error(y_true_clean, y_pred_clean)
    rmse = np.sqrt(mean_squared_error(y_true_clean, y_pred_clean))
    r2 = r2_score(y_true_clean, y_pred_clean)
    medae = median_absolute_error(y_true_clean, y_pred_clean)
    
    return {
        "model": model_name,
        "samples": len(y_true_clean),
        "mae": round(float(mae), 4),
        "rmse": round(float(rmse), 4),
        "r2": round(float(r2), 4),
        "median_ae": round(float(medae), 4)
    }

def compare_models(results: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Converts a list of metric dictionaries into a comparison DataFrame.
    """
    df = pd.DataFrame(results)
    # Reorder columns for readability
    cols = ["model", "samples", "mae", "rmse", "r2", "median_ae"]
    # Only keep columns that exist
    cols = [c for c in cols if c in df.columns]
    # Add any other columns that were passed in
    other_cols = [c for c in df.columns if c not in cols]
    return df[cols + other_cols]
