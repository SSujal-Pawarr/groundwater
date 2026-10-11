"""
Chronological data splitting for ML evaluation.
Prevents future leakage by enforcing strict time-based splits.
"""
from typing import Tuple
import pandas as pd

def chronological_split(
    df: pd.DataFrame,
    date_col: str,
    train_frac: float = 0.7,
    val_frac: float = 0.15,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Splits a DataFrame chronologically into train, validation, and test sets.
    
    Parameters
    ----------
    df : pd.DataFrame
        The data to split.
    date_col : str
        The column to sort by. Must be a datetime or sortable date string.
    train_frac : float
        Fraction of data for training.
    val_frac : float
        Fraction of data for validation.
        
    Returns
    -------
    Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
        Train, validation, and test DataFrames.
    """
    assert 0 < train_frac < 1, "train_frac must be between 0 and 1"
    assert 0 <= val_frac < 1, "val_frac must be between 0 and 1"
    assert train_frac + val_frac < 1, "train_frac + val_frac must be less than 1"
    
    # Sort data strictly by time to prevent future leakage
    df_sorted = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_sorted[date_col]):
        df_sorted["_split_date"] = pd.to_datetime(df_sorted[date_col], errors="coerce")
        df_sorted = df_sorted.sort_values("_split_date").reset_index(drop=True)
        df_sorted = df_sorted.drop(columns=["_split_date"])
    else:
        df_sorted = df_sorted.sort_values(date_col).reset_index(drop=True)
        
    n = len(df_sorted)
    train_end = int(n * train_frac)
    val_end = int(n * (train_frac + val_frac))
    
    train = df_sorted.iloc[:train_end].copy()
    val = df_sorted.iloc[train_end:val_end].copy()
    test = df_sorted.iloc[val_end:].copy()
    
    return train, val, test

def print_split_summary(train: pd.DataFrame, val: pd.DataFrame, test: pd.DataFrame, date_col: str) -> None:
    """
    Prints a summary of the chronological split.
    """
    print("--- Chronological Split Summary ---")
    print(f"Train:      {len(train):>6} rows | {train[date_col].min()} to {train[date_col].max()}")
    if len(val) > 0:
        print(f"Validation: {len(val):>6} rows | {val[date_col].min()} to {val[date_col].max()}")
    print(f"Test:       {len(test):>6} rows | {test[date_col].min()} to {test[date_col].max()}")
    print("-" * 35)
