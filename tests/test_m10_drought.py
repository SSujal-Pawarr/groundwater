import unittest
import pandas as pd
import numpy as np
from datetime import datetime
from src.features.drought_intelligence import (
    compute_drought_intelligence,
    METHODOLOGY_VERSION,
    STATE_NORMAL,
    STATE_WATCH,
    STATE_MODERATE,
    STATE_SEVERE,
    STATE_INSUFFICIENT,
    MIN_HISTORY_YEARS,
    DEFICIT_P25,
    DEFICIT_P10
)

class TestDroughtIntelligence(unittest.TestCase):
    def setUp(self):
        np.random.seed(42)
        
        # 12 years of data for 3 sites in 1 district
        # 10 years historical + 2 test years
        years = list(range(1999, 2011))
        
        data = []
        for site in ["S1", "S2", "S3"]:
            for yr in years:
                # Pre-monsoon and post-monsoon
                for season, month in [("PRE_MONSOON", 5), ("POST_MONSOON", 11)]:
                    # Normal depth is ~10m
                    depth = np.random.uniform(8, 12)
                    data.append({
                        "candidate_site_id": site,
                        "district": "D1",
                        "observation_date": f"{yr}-{month:02d}-01",
                        "analytical_season": season,
                        "water_level_raw": depth,
                        "quality_flags": ""
                    })
        
        self.df = pd.DataFrame(data)

    def test_min_history_requirement(self):
        # Site with only 9 years
        df_short = self.df[self.df["observation_date"] < "2009-01-01"].copy()
        res = compute_drought_intelligence(df_short)
        
        # All statuses should be INSUFFICIENT_HISTORY
        unique_statuses = res["drought_status"].unique()
        self.assertEqual(len(unique_statuses), 1)
        self.assertEqual(unique_statuses[0], STATE_INSUFFICIENT)

    def test_current_and_future_excluded(self):
        res = compute_drought_intelligence(self.df)
        # Check year 2009 for S1
        obs = res[(res["candidate_site_id"] == "S1") & (res["observation_date"] == "2009-05-01")].iloc[0]
        # Reference should strictly be 1999-2008 (10 years)
        self.assertEqual(obs["eligible_history_years"], 10)

    def test_seasonal_grouping(self):
        res = compute_drought_intelligence(self.df)
        pre_obs = res[(res["candidate_site_id"] == "S1") & (res["analytical_season"] == "PRE_MONSOON")]
        post_obs = res[(res["candidate_site_id"] == "S1") & (res["analytical_season"] == "POST_MONSOON")]
        
        # They should be grouped separately, so eligible history for pre_monsoon 2010 is 11,
        # post_monsoon 2010 is also 11, not 22.
        self.assertEqual(pre_obs.iloc[-1]["eligible_history_years"], 11)
        self.assertEqual(post_obs.iloc[-1]["eligible_history_years"], 11)

    def test_quality_filtering(self):
        df_q = self.df.copy()
        # Mark all 2008 records as invalid
        df_q.loc[df_q["observation_date"].str.startswith("2008"), "quality_flags"] = "INVALID_OR_EMPTY"
        res = compute_drought_intelligence(df_q)
        
        obs_2009 = res[(res["candidate_site_id"] == "S1") & (res["observation_date"] == "2009-05-01")].iloc[0]
        # Valid history is now 9 years (1999-2007), so it fails the 10-year test
        self.assertEqual(obs_2009["eligible_history_years"], 9)
        self.assertEqual(obs_2009["drought_status"], STATE_INSUFFICIENT)

    def test_persistence_logic(self):
        df_p = self.df.copy()
        # Make S1 have a massive depth (very dry) in 2009 POST_MONSOON and 2010 PRE_MONSOON
        
        # Reset in 2009-05-01
        mask0 = (df_p["candidate_site_id"] == "S1") & (df_p["observation_date"] == "2009-05-01")
        df_p.loc[mask0, "water_level_raw"] = 1.0
        
        mask1 = (df_p["candidate_site_id"] == "S1") & (df_p["observation_date"] == "2009-11-01")
        df_p.loc[mask1, "water_level_raw"] = 100.0 # Extreme depth
        
        mask2 = (df_p["candidate_site_id"] == "S1") & (df_p["observation_date"] == "2010-05-01")
        df_p.loc[mask2, "water_level_raw"] = 100.0 # Extreme depth
        
        res = compute_drought_intelligence(df_p)
        
        s1 = res[res["candidate_site_id"] == "S1"].sort_values("observation_date").reset_index(drop=True)
        
        # 2009-11-01 is index 21
        obs_1 = s1[s1["observation_date"] == "2009-11-01"].iloc[0]
        # First deficit season, persistence should be 1
        self.assertEqual(obs_1["consecutive_deficit_seasons"], 1)
        self.assertTrue(obs_1["groundwater_deficit_signal"])
        
        # 2010-05-01 is index 20
        obs_2 = s1[s1["observation_date"] == "2010-05-01"].iloc[0]
        # Second consecutive deficit season, persistence should be 2
        self.assertEqual(obs_2["consecutive_deficit_seasons"], 2)
        
        # Regional aggregation should pick this up as a WATCH or MODERATE depending on coverage
        # S1 is 1 out of 3 sites in D1 (33% coverage)
        # Moderate threshold is 33%, so 1/3 is exactly 0.333 > 0.33. It should be MODERATE_DEFICIT
        self.assertEqual(obs_2["drought_status"], STATE_MODERATE)

    def test_persistence_reset(self):
        df_p = self.df.copy()
        # Make S1 dry in 2009 PRE_MONSOON, wet in 2009 POST_MONSOON, dry in 2010 PRE_MONSOON
        mask1 = (df_p["candidate_site_id"] == "S1") & (df_p["observation_date"] == "2009-05-01")
        df_p.loc[mask1, "water_level_raw"] = 100.0
        
        mask2 = (df_p["candidate_site_id"] == "S1") & (df_p["observation_date"] == "2009-11-01")
        df_p.loc[mask2, "water_level_raw"] = 1.0 # Very shallow (wet)
        
        mask3 = (df_p["candidate_site_id"] == "S1") & (df_p["observation_date"] == "2010-05-01")
        df_p.loc[mask3, "water_level_raw"] = 100.0
        
        res = compute_drought_intelligence(df_p)
        s1 = res[res["candidate_site_id"] == "S1"].sort_values("observation_date")
        
        obs1 = s1[s1["observation_date"] == "2009-05-01"].iloc[0]
        self.assertEqual(obs1["consecutive_deficit_seasons"], 1)
        
        obs2 = s1[s1["observation_date"] == "2009-11-01"].iloc[0]
        self.assertEqual(obs2["consecutive_deficit_seasons"], 0) # Reset!
        
        obs3 = s1[s1["observation_date"] == "2010-05-01"].iloc[0]
        self.assertEqual(obs3["consecutive_deficit_seasons"], 1) # Started over
        
        # Status should NOT be MODERATE because it didn't hit persistence=2
        # Regional coverage for deficit=2 is 0. So NORMAL_TO_WET or WATCH
        self.assertEqual(obs3["drought_status"], STATE_NORMAL)

    def test_spatial_aggregation(self):
        df_s = self.df.copy()
        # 2010-05-01: make S1, S2, and S3 all extremely dry for 2 consecutive seasons
        for site in ["S1", "S2"]:
            mask1 = (df_s["candidate_site_id"] == site) & (df_s["observation_date"] == "2009-11-01")
            df_s.loc[mask1, "water_level_raw"] = 200.0
            mask2 = (df_s["candidate_site_id"] == site) & (df_s["observation_date"] == "2010-05-01")
            df_s.loc[mask2, "water_level_raw"] = 200.0
            
        res = compute_drought_intelligence(df_s)
        
        # 2/3 sites = 66% severe coverage
        # Severe threshold is 0.50
        obs = res[(res["candidate_site_id"] == "S1") & (res["observation_date"] == "2010-05-01")].iloc[0]
        self.assertTrue(obs["spatial_coverage_ratio"] > 0.6)
        self.assertEqual(obs["drought_status"], STATE_SEVERE)

    def test_missing_geography_handling(self):
        df_m = self.df.copy()
        # No district column provided
        df_m = df_m.drop(columns=["district"])
        
        # State used as region instead
        res = compute_drought_intelligence(df_m, region_col="candidate_site_id")
        self.assertIn("candidate_site_id", res.columns)

    def test_deterministic_output(self):
        res1 = compute_drought_intelligence(self.df)
        res2 = compute_drought_intelligence(self.df.sample(frac=1.0, random_state=42))
        
        res1 = res1.sort_values(["candidate_site_id", "observation_date"]).reset_index(drop=True)
        res2 = res2.sort_values(["candidate_site_id", "observation_date"]).reset_index(drop=True)
        
        pd.testing.assert_frame_equal(res1, res2)

    def test_no_fabricated_meteorological_context(self):
        res = compute_drought_intelligence(self.df)
        self.assertIn("meteorological_context_available", res.columns)
        self.assertFalse(res["meteorological_context_available"].iloc[0])

if __name__ == '__main__':
    unittest.main()
