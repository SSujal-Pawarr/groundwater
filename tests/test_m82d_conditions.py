import unittest
import pandas as pd
import numpy as np
from datetime import datetime

from features.conditions import (
    compute_india_conditions,
    compute_maharashtra_conditions,
    STATE_EXTREMELY_LOW,
    STATE_LOW,
    STATE_NORMAL,
    STATE_HIGH,
    STATE_EXTREMELY_HIGH,
    STATE_INSUFFICIENT,
    CONDITION_VERSION
)

class TestM82DConditions(unittest.TestCase):

    def setUp(self):
        # A simple synthetic dataset mimicking India periodic data
        self.india_data = pd.DataFrame({
            "candidate_site_id": ["SITE_A"] * 20,
            "analytical_season": ["PRE_MONSOON"] * 10 + ["POST_MONSOON"] * 10,
            "observation_date": [f"20{10+i}-05-01" for i in range(10)] + [f"20{10+i}-11-01" for i in range(10)],
            "water_level_raw": [
                1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, # Pre-monsoon: increasing trend
                100, 100, 100, 100, 100, 100, 100, 100, 100, 100  # Post-monsoon: stable high
            ],
            "quality_flags": [""] * 20
        })
        
        # A simple synthetic dataset mimicking Maharashtra telemetry data
        self.mh_data = pd.DataFrame({
            "candidate_site_id": ["SITE_B"] * 20,
            "observation_timestamp": [f"20{10+i}-01-15 12:00:00" for i in range(10)] + [f"20{10+i}-02-15 12:00:00" for i in range(10)],
            "water_level_raw": np.arange(1, 21),
            "quality_flags": [""] * 20
        })

    def test_schema_integrity_and_version(self):
        res = compute_india_conditions(self.india_data, min_history=3)
        self.assertIn("condition_state", res.columns)
        self.assertIn("percentile", res.columns)
        self.assertIn("historical_reference_group", res.columns)
        self.assertIn("historical_sample_count", res.columns)
        self.assertIn("condition_method_version", res.columns)
        
        # Verify version
        self.assertEqual(res["condition_method_version"].iloc[0], CONDITION_VERSION)

    def test_insufficient_history(self):
        # With min_history=5, the first 5 records (0, 1, 2, 3, 4) in each group have 0-4 priors.
        res = compute_india_conditions(self.india_data, min_history=5)
        
        pre_monsoon = res[res["analytical_season"] == "PRE_MONSOON"].sort_values("observation_date").reset_index(drop=True)
        # i=0 to i=4 should be insufficient
        for i in range(5):
            self.assertEqual(pre_monsoon.loc[i, "condition_state"], STATE_INSUFFICIENT)
            self.assertTrue(pd.isna(pre_monsoon.loc[i, "percentile"]))
            self.assertEqual(pre_monsoon.loc[i, "historical_sample_count"], i)
            
        # i=5 has exactly 5 prior samples
        self.assertNotEqual(pre_monsoon.loc[5, "condition_state"], STATE_INSUFFICIENT)
        self.assertFalse(pd.isna(pre_monsoon.loc[5, "percentile"]))

    def test_percentile_calculation_and_boundaries(self):
        res = compute_india_conditions(self.india_data, min_history=1)
        pre_monsoon = res[res["analytical_season"] == "PRE_MONSOON"].sort_values("observation_date").reset_index(drop=True)
        
        # At i=1 (value=2.0), reference is [1.0]. 2.0 > 1.0, so percentile = 100.0 (EXTREMELY HIGH)
        self.assertEqual(pre_monsoon.loc[1, "percentile"], 100.0)
        self.assertEqual(pre_monsoon.loc[1, "condition_state"], STATE_EXTREMELY_HIGH)
        
        # Let's create a custom scenario for boundaries
        data = pd.DataFrame({
            "candidate_site_id": ["TEST"] * 101,
            "analytical_season": ["TEST_SEASON"] * 101,
            "observation_date": [f"2000-01-{str(i+1).zfill(2)}" if i < 30 else f"2000-02-{str(i-29).zfill(2)}" if i < 58 else f"2000-03-{str(i-57).zfill(2)}" for i in range(101)],
            "water_level_raw": list(range(100)) + [0],
            "quality_flags": [""] * 101
        })
        
        # We need to test the boundary thresholds using a constructed reference of 100 values (0..99).
        # We'll vary the 101st value to hit the exact percentiles.
        boundaries = [
            (5, STATE_EXTREMELY_LOW),  # 5th percentile (< 10)
            (10, STATE_LOW),           # 10.5 percentile (< 25)
            (25, STATE_NORMAL),        # 25.5 percentile (<= 75)
            (74, STATE_NORMAL),        # 74.5 percentile (<= 75)
            (75, STATE_HIGH),          # 75.5 percentile (<= 90)
            (89, STATE_HIGH),          # 89.5 percentile (<= 90)
            (95, STATE_EXTREMELY_HIGH) # 95.5 percentile (> 90)
        ]
        
        for val, expected_state in boundaries:
            test_df = data.copy()
            test_df.loc[100, "water_level_raw"] = val
            res = compute_india_conditions(test_df, min_history=100)
            obs = res.iloc[-1] # The 101st observation
            
            # (less + 0.5 * equal) / 100 * 100
            # If val=10, less=10 (0..9), equal=1 (10). Percentile = 10.5
            # Wait, our percentiles logic:
            # For val=10, less=10, equal=1 -> 10.5.
            # 10.5 < 25 -> LOW
            self.assertEqual(obs["condition_state"], expected_state, f"Failed at val {val} with percentile {obs['percentile']}")

    def test_future_leakage_mandatory(self):
        # A dataset where a massive extreme value occurs at the end.
        # If there is leakage, the percentiles of earlier values would be affected.
        df1 = self.india_data.copy()
        res1 = compute_india_conditions(df1, min_history=3)
        
        df2 = self.india_data.copy()
        # Add a massive future outlier
        df2.loc[20] = ["SITE_A", "PRE_MONSOON", "2050-01-01", -9999.0, ""]
        res2 = compute_india_conditions(df2, min_history=3)
        
        # Verify the first 20 records remain exactly identical in their percentiles and states
        for i in range(20):
            p1 = res1.loc[i, "percentile"]
            p2 = res2.loc[i, "percentile"]
            if pd.isna(p1):
                self.assertTrue(pd.isna(p2))
            else:
                self.assertEqual(p1, p2)
                
    def test_invalid_quality_record_handling(self):
        # Insert conflicting duplicate or invalid quality flag
        df = self.india_data.copy()
        # The 1st and 2nd record are valid.
        # Record 2 is valid.
        # Record 3 is INVALID.
        df.loc[3, "quality_flags"] = "INVALID_OR_EMPTY;CONFLICTING_DUPLICATE"
        
        res = compute_india_conditions(df, min_history=1)
        
        # Record 3 should have NO percentile (nan) because it's invalid.
        # Wait, if we exclude it from reference, we also shouldn't compute a state for it?
        # The logic says: if not is_valid[i], condition is INSUFFICIENT (because nan percentile).
        invalid_obs = res.loc[3]
        self.assertEqual(invalid_obs["condition_state"], STATE_INSUFFICIENT)
        self.assertTrue(pd.isna(invalid_obs["percentile"]))
        
        # Ensure Record 3 is NOT in the reference count for Record 4.
        # Record 0, 1, 2 are valid. So Record 4 should have historical_sample_count = 3
        valid_obs = res.loc[4]
        self.assertEqual(valid_obs["historical_sample_count"], 3)
        self.assertEqual(valid_obs["historical_sample_count"], 3)

    def test_extreme_but_valid_observations(self):
        df = self.india_data.copy()
        # A wildly extreme, but VALID reading.
        df.loc[5, "water_level_raw"] = -1791.0 
        
        res = compute_india_conditions(df, min_history=1)
        obs = res.loc[5]
        # Should be evaluated
        self.assertEqual(obs["condition_state"], STATE_EXTREMELY_LOW)
        self.assertEqual(obs["percentile"], 0.0)
        
        # The next valid reading should include it in its reference
        next_obs = res.loc[6]
        self.assertEqual(next_obs["historical_sample_count"], 6)

    def test_missing_values(self):
        df = self.india_data.copy()
        df.loc[2, "water_level_raw"] = np.nan
        
        res = compute_india_conditions(df, min_history=1)
        self.assertTrue(pd.isna(res.loc[2, "percentile"]))
        
        # Next row should have 1 less in sample count
        self.assertEqual(res.loc[3, "historical_sample_count"], 2) # Only 0 and 1 were valid

    def test_india_analytical_season_grouping(self):
        res = compute_india_conditions(self.india_data, min_history=1)
        # PRE_MONSOON and POST_MONSOON should be fully independent.
        # Record 10 is the first POST_MONSOON. Its reference should be empty/zero.
        post_obs = res.iloc[10]
        self.assertEqual(post_obs["historical_reference_group"], "POST_MONSOON")
        self.assertEqual(post_obs["historical_sample_count"], 0)

    def test_maharashtra_monthly_grouping(self):
        res = compute_maharashtra_conditions(self.mh_data, min_history=1)
        # Jan and Feb should be independent.
        # First Feb record is at index 10.
        feb_obs = res.iloc[10]
        self.assertEqual(feb_obs["historical_reference_group"], "MONTH_02")
        self.assertEqual(feb_obs["historical_sample_count"], 0)

    def test_deterministic_output(self):
        res1 = compute_india_conditions(self.india_data, min_history=5)
        res2 = compute_india_conditions(self.india_data.sample(frac=1.0, random_state=42), min_history=5)
        # Since it sorts internally, res2 should match res1 exactly (if we sort res2 back to original order)
        res1 = res1.sort_values(["candidate_site_id", "observation_date"]).reset_index(drop=True)
        res2 = res2.sort_values(["candidate_site_id", "observation_date"]).reset_index(drop=True)
        pd.testing.assert_frame_equal(res1, res2)

    def test_no_interpretive_labels(self):
        res = compute_india_conditions(self.india_data, min_history=1)
        unique_states = res["condition_state"].unique()
        for s in unique_states:
            self.assertNotIn("DROUGHT", s.upper())
            self.assertNotIn("FLOOD", s.upper())
            self.assertNotIn("SCARCITY", s.upper())

    def test_condition_state_not_alert_state(self):
        res = compute_india_conditions(self.india_data, min_history=1)
        unique_states = res["condition_state"].unique()
        for s in unique_states:
            self.assertNotIn("CRITICAL", s.upper())
            self.assertNotIn("WARNING", s.upper())
            self.assertNotIn("WATCH", s.upper())

if __name__ == '__main__':
    unittest.main()
