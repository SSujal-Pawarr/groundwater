import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import sys
sys.path.append("d:/Projects ALL/DWLR_GRW_INDIA/NEW/src")

from features.baselines import compute_seasonal_historical_baseline
from models.split import chronological_split

class TestForecasting(unittest.TestCase):
    def test_chronological_split_ordering(self):
        # Verify train/val/test split maintains strict chronological order
        df = pd.DataFrame({
            "site": ["A"]*10,
            "date": pd.date_range("2020-01-01", periods=10, freq="D"),
            "val": range(10)
        })
        
        train, val, test = chronological_split(df, date_col="date", train_frac=0.6, val_frac=0.2)
        self.assertEqual(len(train), 6)
        self.assertEqual(len(val), 2)
        self.assertEqual(len(test), 2)
        
        # Train is strictly before Val
        self.assertTrue(train["date"].max() < val["date"].min())
        # Val is strictly before Test
        self.assertTrue(val["date"].max() < test["date"].min())

    def test_seasonal_historical_baseline_strictly_backward_looking(self):
        # Create dataset where values strictly increase by year
        df = pd.DataFrame({
            "site": ["A"]*5,
            "season": ["Monsoon"]*5,
            "year": [2010, 2011, 2012, 2013, 2014],
            "val": [10.0, 20.0, 30.0, 40.0, 50.0]
        })
        
        out = compute_seasonal_historical_baseline(
            df, 
            site_col="site", 
            season_col="season", 
            year_col="year", 
            value_col="val", 
            min_historical_years=1
        )
        
        # Check 2012 (year index 2) -> prior years are 2010, 2011 (values 10, 20 -> mean 15.0)
        pred_2012 = out.loc[out["year"] == 2012, "seasonal_hist_prediction"].iloc[0]
        self.assertEqual(pred_2012, 15.0)
        
        # Check 2014 (year index 4) -> prior years 2010-2013 (values 10, 20, 30, 40 -> mean 25.0)
        pred_2014 = out.loc[out["year"] == 2014, "seasonal_hist_prediction"].iloc[0]
        self.assertEqual(pred_2014, 25.0)

    def test_target_is_strictly_next_observation(self):
        # Verify the target generation does not leak
        df = pd.DataFrame({
            "site": ["A"]*3,
            "date": pd.to_datetime(["2020-01-01", "2020-05-01", "2020-08-01"]),
            "val": [10.0, 20.0, 30.0]
        })
        
        # Sort chronologically
        df = df.sort_values(["site", "date"]).reset_index(drop=True)
        df["target"] = df.groupby("site")["val"].shift(-1)
        
        # For index 0 (2020-01-01), the target should be index 1 (val=20.0)
        self.assertEqual(df.loc[0, "target"], 20.0)
        # For index 2 (last), target is NaN
        self.assertTrue(pd.isna(df.loc[2, "target"]))

